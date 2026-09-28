"""Chargement OHLC (schéma de download_ohlc.py : time UTC, timestamp, open, high, low, close, volume).

Barres non clôturées : exclues d'après l'heure d'extraction, lue dans `<fichier>.meta.json` (écrit par download_ohlc.py),
sinon passée explicitement (`extracted_at`), sinon repli sur la date de modification du fichier avec avertissement
(fragile : une copie qui ne conserve pas cette date garderait une barre partielle).
Contrôles : doublons et NaN OHLC -> ValueError ; trous signalés dans `df.attrs["gaps"]` + avertissement, jamais comblés (D12).
"""
from __future__ import annotations

import hashlib
import json
import os
import warnings
from pathlib import Path

import pandas as pd

from config import DATA_RAW


def meta_path(path: str | Path) -> Path:
    path = Path(path)
    return path.with_name(path.stem + ".meta.json")


def sha256_file(path: str | Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_ohlc(path: str | Path = DATA_RAW, start: str | None = None, bar: str = "30min",
              extracted_at: pd.Timestamp | None = None) -> pd.DataFrame:
    path = Path(path)
    mp = meta_path(path)
    if extracted_at is None and mp.exists():
        meta = json.loads(mp.read_text(encoding="utf-8"))
        if meta.get("sha256") and meta["sha256"] != sha256_file(path):
            raise ValueError(f"{path.name} ne correspond pas à {mp.name} (sha256 différent)")
        extracted_at = pd.Timestamp(meta["extracted_at_utc"])
    if extracted_at is None:
        warnings.warn(f"{mp.name} absent : heure d'extraction prise sur la date de modification du fichier (fragile)")
        extracted_at = pd.Timestamp(os.path.getmtime(path), unit="s", tz="UTC")

    df = pd.read_csv(path, parse_dates=["time"])
    if df.time.duplicated().any():
        raise ValueError(f"{path.name} : horodatages dupliqués")
    if df[["open", "high", "low", "close"]].isna().any().any():
        raise ValueError(f"{path.name} : valeurs OHLC manquantes")
    df = df.sort_values("time")
    df = df[df.time + pd.Timedelta(bar) <= extracted_at]
    if start is not None:
        df = df[df.time >= pd.Timestamp(start, tz="UTC")]
    df = df.reset_index(drop=True)

    step = df.time.diff()
    holes = step > pd.Timedelta(bar)
    df.attrs["gaps"] = [(str(df.time.iat[i - 1]), str(df.time.iat[i]), int(step.iat[i] / pd.Timedelta(bar)) - 1)
                        for i in holes[holes].index]
    df.attrs["extracted_at_utc"] = str(extracted_at)
    if df.attrs["gaps"]:
        warnings.warn(f"{path.name} : {len(df.attrs['gaps'])} trou(s) de données, non comblés (df.attrs['gaps'])")
    return df
