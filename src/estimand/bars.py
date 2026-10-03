"""Données de P6.5 (D43) : barres et événements de développement, réserve 2026 exclue dès la lecture.

- `load_bars_dev` : barres BTC 30 min du fichier brut, tronquées **avant 2026-01-01** immédiatement après la lecture ;
  la position d'une barre reste celle du fichier complet (les indices `entry_bar` / `exit_bar` des événements restent
  valides, la troncature ne retire que la fin) ;
- `load_events_dev` : événements de développement du dataset ML1 `B-1.0`, avec les filtres de `ml.prepare_dev`
  (censure filtrée, entrée ou sortie en 2026 exclue) réécrits ici pour ne pas importer le paquet `ml` (qui importe
  sklearn) ; l'équivalence avec `ml.load_dev_dataset` est testée ;
- `check_no_holdout` : lève une erreur si une barre ou un événement touche 2026 (sauf levée explicite de la
  réserve, `reserve.levee`, EXP-D04).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from config import DATA_RAW, ML1_DATASET_CSV, ML_HOLDOUT_START
from reserve import scellee

HOLDOUT = pd.Timestamp(ML_HOLDOUT_START, tz="UTC")


def check_no_holdout(df: pd.DataFrame, cols=("time",)) -> None:
    """Erreur si une date ≥ 2026-01-01 apparaît, sauf dans un bloc `reserve.levee` (EXP-D04)."""
    if not scellee():
        return
    for c in cols:
        if c in df.columns and len(df) and (pd.to_datetime(df[c], utc=True) >= HOLDOUT).any():
            raise ValueError(f"réserve 2026 : la colonne {c} contient une date ≥ {HOLDOUT.date()} (D43)")


def load_bars_dev(path=DATA_RAW) -> pd.DataFrame:
    """Barres `time, open, high, low, close` < 2026-01-01, indexées par position (= `bar_index` du pipeline)."""
    from utils.data_loader import load_ohlc
    b = load_ohlc(path)
    b = b.loc[b["time"] < HOLDOUT, ["time", "open", "high", "low", "close"]].reset_index(drop=True)
    check_no_holdout(b)
    if not b["time"].is_monotonic_increasing:
        raise ValueError("barres non triées")
    return b


def load_events_dev(path=ML1_DATASET_CSV) -> pd.DataFrame:
    """Événements de développement (mêmes filtres et même tri que `ml.prepare_dev`)."""
    df = pd.read_csv(path, float_precision="round_trip")
    d = df[~df["censored"].astype(bool)].copy()
    for c in ("time", "entry_time", "exit_time"):
        d[c] = pd.to_datetime(d[c], utc=True)
    d = d[(d["entry_time"] < HOLDOUT) & (d["exit_time"] < HOLDOUT)].copy()
    for c in ("entry_bar", "exit_bar", "bar_index", "side", "duration_bars", "run_rank"):
        d[c] = d[c].astype(np.int64)
    d = d.sort_values(["entry_time", "asset", "bar_index"], kind="stable").reset_index(drop=True)
    check_no_holdout(d, ("time", "entry_time", "exit_time"))
    return d
