"""Barres natives de 30 min de Bitstamp (API publique v2, sans clé) : BTC/USD depuis 2013 (EXP-D02.0, rétro-test de
RE-1 figée ; décision du porteur du 2026-10-01).

- Point d'accès : GET https://www.bitstamp.net/api/v2/ohlc/<paire>/?step=1800&limit=1000&start=<s>
  Réponse : {"data": {"pair", "ohlc": [{"timestamp", "open", "high", "low", "close", "volume"}, …]}}, au plus 1 000
  barres dans l'ordre chronologique à partir de `start` ; timestamp = ouverture de la barre, en secondes UTC ; prix et
  volumes en chaînes.
- Bitstamp sert une barre à chaque pas, y compris sans transaction (barre plate au dernier prix, volume nul) : ces
  barres sont gardées telles que servies et comptées par année dans le méta ; rien n'est comblé ni supprimé.
- Même requête et même schéma que le téléchargeur d'origine de la série BTC 2020-2026 du dépôt
  (#KAKALMAN/src/utils/download_ohlc.py) : sur la période commune, les valeurs doivent être identiques.
- Cache : un CSV par année civile ; le méta consigne l'empreinte de chacun. Une dernière année partielle (`end`) a
  son propre fichier, suffixé par sa date de fin exclue.
- Sémantique de fenêtre (constatée le 2026-10-03, EXP-D04) : l'API sert les barres de [start, start + 999 pas], pas
  les 1 000 premières barres ≥ start (ETH/USD, pas d'une journée depuis le 2016-09-27 : 677 bougies, du 2017-08-16,
  première cotation, au 2019-06-23, fin de la fenêtre). Une page vide est donc une fenêtre sans barre : la fenêtre
  suivante est demandée, sans perte ; une année antérieure à la cotation est vide. Rien n'est comblé.
- Réserve 2026 : aucune barre ≥ 2026-01-01 n'est demandée ni écrite, sauf dans un bloc `reserve.levee` (EXP-D04 :
  ETH/USD, XRP/USD et 2026 de BTC/USD, décision du porteur du 2026-10-03).
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Callable

import pandas as pd

from marketdata.coinbase import http_get_json
from reserve import exiger_levee, motif
from utils.data_loader import meta_path

API = "https://www.bitstamp.net/api/v2/ohlc/{pair}/"
HOLDOUT = pd.Timestamp("2026-01-01", tz="UTC")
STEP = 1800
LIMIT = 1000
CSV_COLUMNS = ["time", "timestamp", "open", "high", "low", "close", "volume"]


def _utc(t) -> pd.Timestamp:
    t = pd.Timestamp(t)
    return t.tz_localize("UTC") if t.tzinfo is None else t.tz_convert("UTC")


def _sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def parse_ohlc(payload) -> pd.DataFrame:
    """Réponse Bitstamp → barres triées au schéma de `load_ohlc` (time = ouverture de la barre, UTC)."""
    rows = payload["data"]["ohlc"]
    df = pd.DataFrame({"timestamp": pd.Series([int(r["timestamp"]) for r in rows], dtype="int64")})
    for c in ("open", "high", "low", "close", "volume"):
        df[c] = pd.Series([float(r[c]) for r in rows], dtype=float)
    df.insert(0, "time", pd.to_datetime(df.timestamp, unit="s", utc=True))
    return df.sort_values("time").reset_index(drop=True)


def fetch_ohlc(pair: str, first, last, step: int = STEP,
               fetch: Callable[[str], object] = http_get_json) -> pd.DataFrame:
    """Barres d'ouverture dans [first, last), pages de 1 000 barres ; doublons identiques fusionnés, sinon erreur."""
    t0, t1 = _utc(first), _utc(last)
    if t1 > HOLDOUT:
        exiger_levee(f"fin demandée {t1} postérieure au 2026-01-01")
    a, end, frames = int(t0.timestamp()), int(t1.timestamp()), []
    while a < end:
        df = parse_ohlc(fetch(f"{API.format(pair=pair)}?step={step}&limit={LIMIT}&start={a}"))
        if df.empty:                                  # fenêtre [a, a + 999 pas] sans barre : fenêtre suivante
            a += LIMIT * step
            continue
        frames.append(df[(df.timestamp >= a) & (df.timestamp < end)])
        nxt = int(df.timestamp.iat[-1]) + step
        if nxt <= a:
            raise RuntimeError(f"Bitstamp {pair} : la pagination n'avance plus ({a})")
        a = nxt
    if not frames:
        return parse_ohlc({"data": {"ohlc": []}})
    out = pd.concat(frames, ignore_index=True).sort_values("time", kind="stable")
    dup = out.time.duplicated(keep=False)
    if dup.any():
        if out[dup].groupby("time").nunique().gt(1).any().any():
            raise ValueError(f"Bitstamp {pair} : barres dupliquées de valeurs différentes")
        out = out.drop_duplicates("time")
    return out.reset_index(drop=True)


def build_bitstamp_csv(pair: str, first_year: int, last_year: int, out_csv: Path, cache: Path,
                       meta_extra: dict | None = None, fetch: Callable[[str], object] = http_get_json,
                       end=None) -> dict:
    """Années civiles [first_year, last_year] (un CSV en cache par année), la dernière arrêtée à `end` exclu si donné ;
    écrit le CSV au schéma de `load_ohlc` et son `.meta.json`. Renvoie le méta."""
    if last_year >= HOLDOUT.year:
        exiger_levee(f"l'année {last_year} n'est pas téléchargeable")
    stop_at = _utc(f"{last_year + 1}-01-01") if end is None else _utc(end)
    if not _utc(f"{last_year}-01-01") < stop_at <= _utc(f"{last_year + 1}-01-01"):
        raise ValueError(f"Bitstamp {pair} : fin {stop_at} hors de l'année {last_year}")
    if stop_at > pd.Timestamp.now(tz="UTC"):
        raise ValueError(f"Bitstamp {pair} : fin {stop_at} dans le futur (année incomplète)")
    cache = Path(cache)
    cache.mkdir(parents=True, exist_ok=True)
    frames, files = [], []
    for y in range(first_year, last_year + 1):
        y1 = min(_utc(f"{y + 1}-01-01"), stop_at)
        partial = y1 < _utc(f"{y + 1}-01-01")
        path = cache / (f"bitstamp_{pair}_{STEP}s_{y}_avant_{y1:%Y%m%d}.csv" if partial
                        else f"bitstamp_{pair}_{STEP}s_{y}.csv")
        if path.exists():
            b = pd.read_csv(path, parse_dates=["time"])
        else:
            b = fetch_ohlc(pair, f"{y}-01-01", y1, STEP, fetch)
            b[CSV_COLUMNS].to_csv(path, index=False)
        frames.append(b)
        files.append({"annee": y, "barres": len(b), "sha256": _sha256(path)})
    bars = pd.concat([f for f in frames if len(f)], ignore_index=True).sort_values("time").reset_index(drop=True)
    if bars.time.duplicated().any():
        raise ValueError(f"Bitstamp {pair} : barres dupliquées entre années")
    if (bars.time >= HOLDOUT).any():
        exiger_levee("barre ≥ 2026-01-01")
    if (bars.time >= stop_at).any():
        raise ValueError(f"Bitstamp {pair} : barre au-delà de la fin {stop_at}")
    out_csv = Path(out_csv)
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    bars[CSV_COLUMNS].to_csv(out_csv, index=False)
    year = bars.time.dt.year
    meta = {"source": "bitstamp", "url": API.format(pair=pair), "pair": pair, "step_s": STEP,
            "extracted_at_utc": pd.Timestamp.now(tz="UTC").isoformat(),
            "extracted_at_origin": ("heure du téléchargement (années civiles complètes, antérieures à 2026)"
                                    if end is None else f"heure du téléchargement (fin exclue : {stop_at})"),
            "fin_exclue": str(stop_at), "reserve_levee": motif() if (bars.time >= HOLDOUT).any() else None,
            "n_rows": len(bars), "first": str(bars.time.iat[0]), "last": str(bars.time.iat[-1]),
            "barres_volume_nul_par_an": {int(k): int(v) for k, v in (bars.volume <= 0).groupby(year).sum().items()},
            "barres_plates_par_an": {int(k): int(v) for k, v in (bars.high == bars.low).groupby(year).sum().items()},
            "sha256": _sha256(out_csv), "fichiers_annuels": files, **(meta_extra or {})}
    meta_path(out_csv).write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
    return meta
