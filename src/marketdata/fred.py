"""Série quotidienne publique de FRED (fichier fredgraph.csv, sans clé), référence externe de l'audit des données
(EXP-D01 : prix spot du WTI à Cushing publié par l'EIA, série DCOILWTICO, pour caractériser le CFD WTI)."""
from __future__ import annotations

import hashlib
import io
import json
import urllib.request
from pathlib import Path
from typing import Callable

import pandas as pd

from utils.data_loader import meta_path

URL = "https://fred.stlouisfed.org/graph/fredgraph.csv?id={sid}"     # série entière, filtrée ensuite
HOLDOUT = pd.Timestamp("2026-01-01")


def http_get(url: str, timeout: float = 60.0) -> bytes:
    with urllib.request.urlopen(url, timeout=timeout) as r:
        return r.read()


def parse_fred(text: str, sid: str) -> pd.DataFrame:
    """CSV FRED (colonne de date « observation_date » ou « DATE ») → date, valeur ; « . » (jour sans cotation) → NaN."""
    df = pd.read_csv(io.StringIO(text), na_values=["."])
    date_col = df.columns[0]
    if sid not in df.columns:
        raise ValueError(f"FRED : colonne {sid} absente ({list(df.columns)})")
    return pd.DataFrame({"date": pd.to_datetime(df[date_col]), "valeur": df[sid].astype(float)})


def build_fred_csv(sid: str, first: str, last: str, out_csv: Path, meta_extra: dict | None = None,
                   fetch: Callable[[str], bytes] = http_get) -> dict:
    if pd.Timestamp(last) >= HOLDOUT:
        raise ValueError(f"réserve 2026 : fin {last} non téléchargeable")
    url = URL.format(sid=sid)
    df = parse_fred(fetch(url).decode("utf-8"), sid)
    df = df[(df.date >= pd.Timestamp(first)) & (df.date <= pd.Timestamp(last)) & (df.date < HOLDOUT)]
    df = df.reset_index(drop=True)
    out_csv = Path(out_csv)
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_csv, index=False)
    meta = {"source": "FRED (Federal Reserve Bank of St. Louis)", "url": url, "serie": sid, "periode": [first, last],
            "extracted_at_utc": pd.Timestamp.now(tz="UTC").isoformat(), "n_rows": len(df),
            "n_valeurs": int(df.valeur.notna().sum()), "first": str(df.date.iat[0].date()),
            "last": str(df.date.iat[-1].date()), "sha256": hashlib.sha256(out_csv.read_bytes()).hexdigest(),
            **(meta_extra or {})}
    meta_path(out_csv).write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
    return meta
