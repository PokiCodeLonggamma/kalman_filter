"""EXP-D05.1 — fichiers du cBot AkfExportFtmo (compte FTMO sur cTrader, `experiments/D05_1/cbot`) : bougies M30, ticks
bid/ask, fiches des symboles ; écart de chaque barre à son ouverture et profil par demi-heure locale.

- Bougies : `time` (UTC, ouverture), OHLC au bid (convention de cTrader), `tick_volume` ; la bougie en cours est exclue
  par le cBot. Lecture tronquée au 2026-01-01 hors `reserve.levee`, comme `strategy.load_asset`.
- Ticks : `time` (UTC, ms), `bid`, `ask` ; tous datés de 2026 : lecture refusée hors `reserve.levee`.
- Écart en bps du milieu : (ask − bid) / ((ask + bid) / 2).
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

import reserve

BPS = 1e4
OHLC = ["open", "high", "low", "close"]


def _ordre(time: pd.Series, nom: str) -> None:
    if not time.is_monotonic_increasing or time.duplicated().any():
        raise ValueError(f"{nom} : horodatages hors d'ordre ou dupliqués")


def lire_bougies(path: str | Path, fin=None) -> pd.DataFrame:
    """Bougies M30 du cBot, colonnes `time, open, high, low, close, volume` (volume en ticks), avant `fin` (2026-01-01
    par défaut hors levée de la réserve)."""
    path = Path(path)
    df = pd.read_csv(path)
    df["time"] = pd.to_datetime(df.time, utc=True)
    _ordre(df.time, path.name)
    p = df[OHLC].to_numpy(dtype=float)
    if not np.isfinite(p).all() or (p <= 0).any():
        raise ValueError(f"{path.name} : prix manquants ou non positifs")
    if ((df.high < df[["open", "close"]].max(axis=1)) | (df.low > df[["open", "close"]].min(axis=1))).any():
        raise ValueError(f"{path.name} : bougie incohérente (plus haut ou plus bas hors de l'ouverture et de la clôture)")
    if fin is None and reserve.scellee():
        fin = reserve.DEBUT
    if fin is not None:
        df = df[df.time < pd.Timestamp(fin)]
    return df.rename(columns={"tick_volume": "volume"})[["time", *OHLC, "volume"]].reset_index(drop=True)


def lire_ticks(path: str | Path) -> pd.DataFrame:
    """Ticks bid/ask du cBot ; ceux de 2026 exigent la levée de la réserve."""
    path = Path(path)
    df = pd.read_csv(path)
    df["time"] = pd.to_datetime(df.time, utc=True, format="ISO8601")
    if (df.time >= reserve.DEBUT).any():
        reserve.exiger_levee(f"ticks {path.name}")
    if not df.time.is_monotonic_increasing:
        raise ValueError(f"{path.name} : ticks hors d'ordre")
    if (df.ask < df.bid).any():
        raise ValueError(f"{path.name} : ask sous le bid")
    return df[["time", "bid", "ask"]].reset_index(drop=True)


def lire_fiches(path: str | Path) -> pd.DataFrame:
    """Fiches des symboles, indexées par nom exact."""
    return pd.read_csv(path).set_index("nom")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def ecrire_serie(bougies: pd.DataFrame, out_csv: str | Path, meta: dict, extrait: str) -> dict:
    """Série au schéma de `load_ohlc` (time, timestamp, open, high, low, close, volume) et son .meta.json (empreinte
    SHA-256, heure d'extraction `extrait`)."""
    out_csv = Path(out_csv)
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    out = bougies[["time", *OHLC, "volume"]].copy()
    out.insert(1, "timestamp", out.time.astype("int64") // 10**9)
    out["time"] = out.time.dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    out.to_csv(out_csv, index=False, lineterminator="\n")
    full = {**meta, "prix": "bid (bougies cTrader)", "timezone": "UTC (ouverture de la barre)", "n_rows": len(out),
            "first": out.time.iat[0] if len(out) else None, "last": out.time.iat[-1] if len(out) else None,
            "extracted_at_utc": extrait, "sha256": _sha256(out_csv)}
    out_csv.with_name(out_csv.stem + ".meta.json").write_text(json.dumps(full, ensure_ascii=False, indent=1),
                                                               encoding="utf-8")
    return full


def ecarts_ticks(ticks: pd.DataFrame) -> pd.Series:
    """Écart de chaque tick, en bps du milieu, indexé par l'heure du tick."""
    bid, ask = ticks.bid.to_numpy(dtype=float), ticks.ask.to_numpy(dtype=float)
    return pd.Series((ask - bid) / ((ask + bid) / 2.0) * BPS, index=pd.DatetimeIndex(ticks.time))


def ecarts_barres(ticks: pd.DataFrame, ouvertures: pd.DatetimeIndex, fenetre: str = "5min",
                  vieux: str = "30min") -> pd.Series:
    """Écart à l'ouverture de chaque barre : médiane des ticks de [ouverture, ouverture + `fenetre`) ; à défaut, dernier
    tick d'avant l'ouverture s'il a moins de `vieux` ; sinon NaN."""
    e = ecarts_ticks(ticks)
    t = e.index.asi8
    v = e.to_numpy()
    o = pd.DatetimeIndex(ouvertures).asi8
    w, old = pd.Timedelta(fenetre).value, pd.Timedelta(vieux).value
    a, b = np.searchsorted(t, o, side="left"), np.searchsorted(t, o + w, side="left")
    out = np.full(len(o), np.nan)
    for i in range(len(o)):
        if b[i] > a[i]:
            out[i] = np.median(v[a[i]:b[i]])
        elif a[i] > 0 and o[i] - t[a[i] - 1] < old:
            out[i] = v[a[i] - 1]
    return pd.Series(out, index=pd.DatetimeIndex(ouvertures))


def demi_heure(times, fuseau: str) -> np.ndarray:
    """Demi-heure locale (0 à 47) de chaque instant."""
    loc = pd.DatetimeIndex(times).tz_convert(fuseau)
    return (loc.hour * 2 + loc.minute // 30).to_numpy()


def profil_ecarts(ecarts: pd.Series, fuseau: str) -> pd.DataFrame:
    """Médiane, moyenne, P90 et nombre d'écarts (une valeur par barre) par demi-heure locale, 48 lignes."""
    e = ecarts.dropna()
    g = pd.Series(e.to_numpy(), index=demi_heure(e.index, fuseau)).groupby(level=0)
    p = pd.DataFrame({"mediane": g.median(), "moyenne": g.mean(), "p90": g.quantile(0.9), "n": g.size()})
    p = p.reindex(range(48))
    p["n"] = p.n.fillna(0).astype(int)
    return p
