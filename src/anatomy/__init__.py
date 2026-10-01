"""EXP-A01 — anatomie du signal brut AKF-TSO v2.1 (Étape A, strictement descriptive : aucun PnL, aucun seuil).

    from anatomy import load_dev_bars, build_atlas
    df = load_dev_bars()                    # BTC/USD 30 min, 2020-01-01 → 2025-12-31 23:30 UTC
    atlas, f, idx, atr = build_atlas(df)    # une ligne par signal de développement (7 296)

Tout part de `features.build_features` (moteur certifié `indicator.run_indicator`) : le Kalman, l'oscillateur et
les segments ne sont jamais recalculés ici. Colonnes causales : `anatomy.causal`. Colonnes a posteriori (`post_`,
jamais utilisables comme filtre) et profils : `anatomy.posterior`.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from anatomy.causal import ATR_LEN, atr_wilder, causal_table
from anatomy.posterior import TAUS, event_profiles, posterior_table
from config import WARMUP_BARS
from features import _run_rank, build_features
from indicator import KalmanParams
from utils.data_loader import load_ohlc

__all__ = ["DEV_END", "ID_COLUMNS", "load_dev_bars", "dev_universe", "build_atlas", "event_profiles", "TAUS"]

DEV_END = pd.Timestamp("2026-01-01", tz="UTC")     # réserve 2026 : aucune barre lue à partir de cette date

ID_COLUMNS = ["signal_id", "timestamp", "bar_index", "year", "direction", "is_flip", "run_rank", "is_warmup"]


def load_dev_bars() -> pd.DataFrame:
    """Barres 30 min antérieures à DEV_END (empreinte SHA-256 du CSV vérifiée par `load_ohlc`)."""
    df = load_ohlc()
    return df[df.time < DEV_END].reset_index(drop=True)


def dev_universe(f: pd.DataFrame) -> np.ndarray:
    """Indices des signaux de développement #KAKALMAN (P5 : 7 296 sur 2020-2025, réserve D43).

    Signal brut sur une barre `valid_features` (warm-up : 300 barres 30 min et 300 bougies 1 h), dont l'entrée
    (open t+1) et la sortie native (open suivant le premier signal opposé à partir de t+1) existent dans
    l'échantillon tronqué à DEV_END. Ce filtre de sortie n'est qu'une convention d'appariement à l'ancre : il exclut
    le signal de fin 2025 dont la sortie native tombe en 2026. Aucune variable n'en dépend.
    """
    sig = f.signal.to_numpy().astype(int)
    n = len(sig)
    pos = {d: np.flatnonzero(sig == d) for d in (1, -1)}
    keep = []
    for t in np.flatnonzero((sig != 0) & f.valid_features.to_numpy(dtype=bool)):
        opp = pos[-sig[t]]
        k = np.searchsorted(opp, t + 1)
        if t + 1 <= n - 1 and k < len(opp) and opp[k] + 1 <= n - 1:
            keep.append(t)
    return np.asarray(keep, dtype=int)


def build_atlas(df: pd.DataFrame, kalman: KalmanParams = KalmanParams()
                ) -> tuple[pd.DataFrame, pd.DataFrame, np.ndarray, np.ndarray]:
    """Atlas des signaux : identification, variables a posteriori (`post_`), variables causales. `kalman` : réglages
    du moteur certifié (EXP-D02 : R0 seul varie), transmis tels quels à `features.build_features`."""
    f = build_features(df, kalman)
    atr = atr_wilder(f.high, f.low, f.close, ATR_LEN)
    idx = dev_universe(f)
    sig = f.signal.to_numpy().astype(int)
    ids = pd.DataFrame({
        "signal_id": np.arange(len(idx)),
        "timestamp": f.time.iloc[idx].reset_index(drop=True),
        "bar_index": idx,
        "year": f.time.iloc[idx].dt.year.to_numpy(),
        "direction": sig[idx],
        "is_flip": f.decision.to_numpy(dtype=bool)[idx],
        "run_rank": _run_rank(sig)[idx],
        "is_warmup": idx < WARMUP_BARS,
    })
    atlas = pd.concat([ids, posterior_table(f, idx, atr), causal_table(f, idx, atr)], axis=1)
    return atlas, f, idx, atr
