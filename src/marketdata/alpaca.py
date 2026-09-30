"""Barres de 30 min d'actions et d'ETF américains, API de données Alpaca v2, séance régulière seulement
(EXP-D01 bis : SPY et XLE).

- Point d'accès : GET https://data.alpaca.markets/v2/stocks/{symbole}/bars?timeframe=30Min&start=…&end=…&feed=sip
  &adjustment=…&limit=10000&page_token=… ; réponse {"bars": [{"t", "o", "h", "l", "c", "v", "n", "vw"}, …],
  "next_page_token": …}. t = début de la barre, en UTC. Flux SIP : toutes les places américaines consolidées.
- Authentification : clés du porteur lues dans les variables d'environnement APCA_API_KEY_ID et APCA_API_SECRET_KEY.
  Elles ne sont ni affichées, ni écrites, ni versionnées.
- Séance régulière : barres dont le début est dans [09:30 ; 16:00[ heure de New York, [09:30 ; 13:00[ les 12 jours de
  clôture anticipée du NYSE de 2020 à 2025 (13 barres par séance, 7 ces jours-là). Les barres pré- et post-marché sont
  écartées et comptées. Calendrier des clôtures anticipées vérifié sur les données (effondrement du volume après
  13:00). L'enchère de clôture, horodatée à 16:00:00 (13:00:00), tombe dans la barre suivante, écartée : le close de la
  dernière barre est la dernière transaction de la séance continue.
- Ajustement : « all » (fractionnements et dividendes, ajustement d'Alpaca) pour la série mesurée ; la série brute
  (« raw ») est écrite à part pour identifier les écarts d'ouverture dus aux détachements de dividendes.
- Réserve 2026 : fin demandée ≤ 2025-12-31 ; aucune barre ≥ 2026-01-01 n'est écrite.
"""
from __future__ import annotations

import hashlib
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Callable

import numpy as np
import pandas as pd

from utils.data_loader import meta_path

API = "https://data.alpaca.markets/v2/stocks/{symbol}/bars"
HOLDOUT = pd.Timestamp("2026-01-01", tz="UTC")
NY = "America/New_York"
OPEN, CLOSE, EARLY_CLOSE = pd.Timedelta(hours=9, minutes=30), pd.Timedelta(hours=16), pd.Timedelta(hours=13)
#: Clôtures anticipées du NYSE (13:00 heure de New York), 2020-2025.
NYSE_EARLY_CLOSE = {"2020-11-27", "2020-12-24", "2021-11-26", "2022-11-25", "2023-07-03", "2023-11-24", "2024-07-03",
                    "2024-11-29", "2024-12-24", "2025-07-03", "2025-11-28", "2025-12-24"}
CSV_COLUMNS = ["time", "timestamp", "open", "high", "low", "close", "volume"]
ENV_KEYS = ("APCA_API_KEY_ID", "APCA_API_SECRET_KEY")


def auth_headers(env=None) -> dict:
    """En-têtes d'authentification depuis l'environnement ; erreur explicite, sans valeur, si une clé manque."""
    env = os.environ if env is None else env
    missing = [k for k in ENV_KEYS if not env.get(k)]
    if missing:
        raise SystemExit(f"variables d'environnement absentes : {', '.join(missing)} (clés Alpaca du porteur)")
    return {"APCA-API-KEY-ID": env[ENV_KEYS[0]], "APCA-API-SECRET-KEY": env[ENV_KEYS[1]]}


def http_get_json(url: str, headers: dict, tries: int = 6, pause: float = 0.35):
    """GET JSON, au plus environ 3 requêtes par seconde (limite gratuite : 200 par minute) ; nouvel essai après 429 ou
    5xx. Une erreur d'authentification remonte sans afficher les en-têtes."""
    for k in range(tries):
        try:
            req = urllib.request.Request(url, headers={**headers, "Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=60) as r:
                data = json.loads(r.read())
            time.sleep(pause)
            return data
        except urllib.error.HTTPError as e:
            if e.code in (401, 403):
                raise SystemExit(f"Alpaca refuse la requête (HTTP {e.code}) : clés invalides ou flux SIP non autorisé")
            if (e.code != 429 and e.code < 500) or k == tries - 1:
                raise
        except OSError:
            if k == tries - 1:
                raise
        time.sleep(2.0 * (k + 1))
    raise RuntimeError("inaccessible")


def parse_bars(rows: list[dict]) -> pd.DataFrame:
    df = pd.DataFrame(rows, columns=["t", "o", "h", "l", "c", "v", "n", "vw"])
    return pd.DataFrame({"time": pd.to_datetime(df.t, utc=True), "open": df.o.astype(float),
                         "high": df.h.astype(float), "low": df.l.astype(float), "close": df.c.astype(float),
                         "volume": df.v.astype(float), "n_trades": df.n})


def fetch_bars(symbol: str, start: str, end: str, adjustment: str, headers: dict,
               get: Callable = http_get_json) -> pd.DataFrame:
    """Toutes les pages de barres de 30 min de [start, end] (dates UTC, fin incluse jusqu'à 23:59:59)."""
    t_end = pd.Timestamp(end, tz="UTC") + pd.Timedelta(hours=23, minutes=59, seconds=59)
    if t_end >= HOLDOUT:
        raise ValueError(f"réserve 2026 : fin demandée {end} non téléchargeable")
    q = {"timeframe": "30Min", "start": pd.Timestamp(start, tz="UTC").strftime("%Y-%m-%dT%H:%M:%SZ"),
         "end": t_end.strftime("%Y-%m-%dT%H:%M:%SZ"), "adjustment": adjustment, "feed": "sip", "limit": 10000,
         "sort": "asc"}
    rows, token, pages = [], None, 0
    while True:
        params = {**q, **({"page_token": token} if token else {})}
        data = get(f"{API.format(symbol=symbol)}?{urllib.parse.urlencode(params)}", headers)
        rows += data.get("bars") or []
        pages += 1
        token = data.get("next_page_token")
        if not token:
            break
    df = parse_bars(rows).sort_values("time").reset_index(drop=True)
    if df.time.duplicated().any():
        raise ValueError(f"{symbol} : barres dupliquées entre pages")
    df.attrs["pages"] = pages
    return df


def regular_session(df: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    """Barres dont le début est dans [09:30 ; 16:00[ heure de New York ([09:30 ; 13:00[ les jours de clôture anticipée) ;
    renvoie aussi le nombre de barres écartées."""
    local = df.time.dt.tz_convert(NY)
    tod = local - local.dt.normalize()
    early = local.dt.strftime("%Y-%m-%d").isin(NYSE_EARLY_CLOSE).to_numpy()
    close = pd.to_timedelta(np.where(early, EARLY_CLOSE.value, CLOSE.value))
    keep = ((tod >= OPEN).to_numpy() & (tod.to_numpy() < close.to_numpy()))
    return df[keep].reset_index(drop=True), int((~keep).sum())


def refilter_csv(csv: Path) -> dict:
    """Réapplique `regular_session` à une série déjà écrite (sans nouveau téléchargement) et met son méta à jour."""
    csv = Path(csv)
    mp = meta_path(csv)
    meta = json.loads(mp.read_text(encoding="utf-8"))
    if meta.get("sha256") != hashlib.sha256(csv.read_bytes()).hexdigest():
        raise ValueError(f"{csv.name} : empreinte différente du méta")
    df = pd.read_csv(csv, parse_dates=["time"])
    rth, dropped = regular_session(df)
    meta.update({"barres_cloture_anticipee_ecartees": dropped,
                 "barres_hors_seance_ecartees": meta.get("barres_hors_seance_ecartees", 0) + dropped,
                 "seance": "régulière : début de barre dans [09:30 ; 16:00[ heure de New York, [09:30 ; 13:00[ les jours "
                           "de clôture anticipée du NYSE"})
    return _write(rth[["time", "open", "high", "low", "close", "volume"]], csv, meta)


def _write(bars: pd.DataFrame, out_csv: Path, meta: dict) -> dict:
    out = bars.copy()
    out["timestamp"] = out.time.map(lambda t: int(t.timestamp())).astype("int64")
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    out[CSV_COLUMNS].to_csv(out_csv, index=False)
    meta = {**meta, "n_rows": len(out), "first": str(out.time.iat[0]), "last": str(out.time.iat[-1]),
            "sha256": hashlib.sha256(out_csv.read_bytes()).hexdigest()}
    meta_path(out_csv).write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
    return meta


def build_alpaca_csv(symbol: str, start: str, end: str, out_csv: Path, meta_extra: dict | None = None,
                     headers: dict | None = None, get: Callable = http_get_json) -> dict:
    """Séries ajustée (« all », mesurée) et brute (« raw », audit des dividendes), séance régulière, CSV au schéma de
    `load_ohlc` et `.meta.json` chacune. Renvoie le méta de la série ajustée."""
    headers = auth_headers() if headers is None else headers
    out_csv = Path(out_csv)
    common = {"source": "alpaca", "url": API.format(symbol=symbol), "symbol": symbol, "pair": symbol.lower(),
              "feed": "sip", "timeframe": "30Min", "step_s": 1800,
              "seance": "régulière : début de barre dans [09:30 ; 16:00[ heure de New York, [09:30 ; 13:00[ les jours "
                        "de clôture anticipée du NYSE",
              "extracted_at_utc": pd.Timestamp.now(tz="UTC").isoformat(),
              "extracted_at_origin": "heure du téléchargement (barres antérieures à 2026)"}
    metas = {}
    for adj, path in (("all", out_csv), ("raw", out_csv.with_name(out_csv.stem + "_brut.csv"))):
        full = fetch_bars(symbol, start, end, adj, headers, get)
        rth, dropped = regular_session(full[full.time < HOLDOUT])
        metas[adj] = _write(rth[["time", "open", "high", "low", "close", "volume"]], path,
                            {**common, "adjustment": adj, "pages": full.attrs.get("pages"),
                             "barres_hors_seance_ecartees": dropped, **(meta_extra or {})})
    metas["all"]["serie_brute"] = {"fichier": out_csv.stem + "_brut.csv", "sha256": metas["raw"]["sha256"]}
    meta_path(out_csv).write_text(json.dumps(metas["all"], ensure_ascii=False, indent=1), encoding="utf-8")
    return metas["all"]
