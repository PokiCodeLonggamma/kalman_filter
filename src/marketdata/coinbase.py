"""Chandelles Coinbase Exchange (API publique, sans clé) agrégées en barres de 30 min (EXP-D01 : SOL/USD).

- Point d'accès : GET https://api.exchange.coinbase.com/products/<PRODUIT>/candles?granularity=900&start=…&end=…
  Réponse : au plus 300 bougies [time, low, high, open, close, volume], de la plus récente à la plus ancienne ;
  time = début de la bougie, en secondes UTC. Une bougie sans transaction est absente de la réponse.
- L'API n'a pas de pas de 30 min (granularités 60, 300, 900, 3 600, 21 600 et 86 400 s). Les barres de 30 min sont
  agrégées exactement depuis les bougies natives de 15 min, alignées sur :00 et :30 UTC : open de la première, plus
  haut des high, plus bas des low, close de la dernière, somme des volumes (`marketdata.bars.aggregate_30m`). Une
  barre dont un seul quart d'heure a des transactions est gardée ; une barre sans aucune bougie est un trou.
- Sortie : schéma de `utils.data_loader.load_ohlc` et `.meta.json` (provenance, construction, empreintes des
  fichiers mensuels de bougies de 15 min mis en cache).
- Réserve 2026 : aucune bougie ≥ 2026-01-01 n'est demandée ni écrite.
"""
from __future__ import annotations

import hashlib
import json
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Callable

import numpy as np
import pandas as pd

from marketdata.bars import aggregate_30m
from utils.data_loader import meta_path

API = "https://api.exchange.coinbase.com/products/{product}/candles"
HOLDOUT = pd.Timestamp("2026-01-01", tz="UTC")
GRANULARITY = 900
MAX_CANDLES = 300
USER_AGENT = "akf-tso-research (historique public)"
CANDLE_COLUMNS = ["time", "open", "high", "low", "close", "volume"]
CSV_COLUMNS = ["time", "timestamp", "open", "high", "low", "close", "volume"]


def http_get_json(url: str, timeout: float = 60.0, tries: int = 6, pause: float = 0.25):
    """GET JSON ; au plus 4 requêtes par seconde (limite publique de Coinbase : 10) ; nouvel essai après 429 ou 5xx."""
    for k in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                data = json.loads(r.read())
            time.sleep(pause)
            return data
        except urllib.error.HTTPError as e:
            if (e.code != 429 and e.code < 500) or k == tries - 1:
                raise
        except OSError:
            if k == tries - 1:
                raise
        time.sleep(2.0 * (k + 1))
    raise RuntimeError("inaccessible")


def _iso(t: pd.Timestamp) -> str:
    return t.strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_candles(rows) -> pd.DataFrame:
    """Réponse Coinbase [time, low, high, open, close, volume] → bougies triées (time = début, UTC)."""
    a = np.asarray(rows, dtype=float).reshape(-1, 6)
    df = pd.DataFrame({"time": pd.to_datetime(a[:, 0].astype("int64"), unit="s", utc=True), "open": a[:, 3],
                       "high": a[:, 2], "low": a[:, 1], "close": a[:, 4], "volume": a[:, 5]})
    return df.sort_values("time").reset_index(drop=True)


def fetch_candles(product: str, first, last, granularity: int = GRANULARITY,
                  fetch: Callable[[str], object] = http_get_json) -> pd.DataFrame:
    """Bougies de début dans [first, last), fenêtres de 300 bougies ; doublons identiques fusionnés, sinon erreur."""
    t0, t1 = pd.Timestamp(first), pd.Timestamp(last)
    t0 = t0.tz_localize("UTC") if t0.tzinfo is None else t0
    t1 = t1.tz_localize("UTC") if t1.tzinfo is None else t1
    if t1 > HOLDOUT:
        raise ValueError(f"réserve 2026 : fin demandée {t1} postérieure au 2026-01-01")
    step = pd.Timedelta(seconds=granularity)
    frames, a = [], t0
    while a < t1:
        b = min(a + (MAX_CANDLES - 1) * step, t1 - step)
        url = f"{API.format(product=product)}?granularity={granularity}&start={_iso(a)}&end={_iso(b)}"
        df = parse_candles(fetch(url))
        frames.append(df[(df.time >= a) & (df.time <= b)])
        a = b + step
    out = pd.concat(frames, ignore_index=True).sort_values("time", kind="stable")
    dup = out.time.duplicated(keep=False)
    if dup.any():
        if out[dup].groupby("time").nunique().gt(1).any().any():
            raise ValueError(f"{product} : bougies dupliquées de valeurs différentes")
        out = out.drop_duplicates("time")
    return out.reset_index(drop=True)


def _sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def build_coinbase_csv(product: str, first: str, last: str, out_csv: Path, cache: Path,
                       meta_extra: dict | None = None, fetch: Callable[[str], object] = http_get_json) -> dict:
    """Bougies de 15 min des mois [first, last] (« AAAA-MM », un CSV en cache par mois), agrégées en 30 min ; écrit le
    CSV au schéma de `load_ohlc` et son `.meta.json`. Renvoie le méta."""
    months = pd.period_range(pd.Period(first, "M"), pd.Period(last, "M"), freq="M")
    if months[-1].end_time.tz_localize("UTC") >= HOLDOUT:
        raise ValueError(f"réserve 2026 : le mois {months[-1]} n'est pas téléchargeable")
    cache = Path(cache)
    cache.mkdir(parents=True, exist_ok=True)
    frames, files = [], []
    for p in months:
        path = cache / f"{product}_{GRANULARITY}s_{p}.csv"
        if path.exists():
            c = pd.read_csv(path, parse_dates=["time"])
        else:
            c = fetch_candles(product, p.start_time, (p + 1).start_time, GRANULARITY, fetch)
            c.to_csv(path, index=False)
        frames.append(c)
        files.append({"mois": str(p), "bougies_15m": len(c), "sha256": _sha256(path)})
    c15 = pd.concat([f for f in frames if len(f)], ignore_index=True).sort_values("time").reset_index(drop=True)
    if c15.time.duplicated().any():
        raise ValueError(f"{product} : bougies dupliquées entre mois")
    bars = aggregate_30m(c15)
    if (bars.time >= HOLDOUT).any():
        raise ValueError("réserve 2026 : barre ≥ 2026-01-01")
    out_csv = Path(out_csv)
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    bars[CSV_COLUMNS].to_csv(out_csv, index=False)
    meta = {"source": "coinbase", "url": API.format(product=product), "product": product,
            "pair": product.replace("-", "").lower(), "granularite_source_s": GRANULARITY, "step_s": 1800,
            "extracted_at_utc": pd.Timestamp.now(tz="UTC").isoformat(),
            "extracted_at_origin": "heure du téléchargement (mois civils complets, antérieurs à 2026)",
            "n_rows": len(bars), "first": str(bars.time.iat[0]), "last": str(bars.time.iat[-1]),
            "n_barres_un_seul_quart_d_heure": int((bars.n_sub == 1).sum()),
            "sha256": _sha256(out_csv), "fichiers_15m": files, **(meta_extra or {})}
    meta_path(out_csv).write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
    return meta
