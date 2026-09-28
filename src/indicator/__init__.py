"""Module P2 : implémentation Python du baseline AKF-TSO v2.1 (docs/P2_parite.md).

Usage production (D22, D25) :
    out = run_indicator(df)                                   # fill_price="open_next", warmup_bars=300
Usage parité TradingView / oracle P0 :
    out = run_indicator(df, fill_price="close", warmup_bars=0)
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from config import FILL_PRICE_DEFAULT, WARMUP_BARS
from indicator.kalman import KALMAN_COLUMNS, KalmanParams, adaptive_R, run_kalman
from indicator.segments import FillPrice, SignalParams, execute, trades, zones_and_signals
from indicator.trend_strength import OscParams, local_amplitude, pine_wma, trend_strength

__all__ = ["run_indicator", "KalmanParams", "OscParams", "SignalParams", "run_kalman", "adaptive_R",
           "trend_strength", "local_amplitude", "pine_wma", "zones_and_signals", "execute", "trades",
           "KALMAN_COLUMNS"]


def run_indicator(df: pd.DataFrame, kalman: KalmanParams = KalmanParams(), osc: OscParams = OscParams(),
                  signal: SignalParams = SignalParams(), fill_price: FillPrice = FILL_PRICE_DEFAULT,
                  warmup_bars: int = WARMUP_BARS) -> pd.DataFrame:
    """df : colonnes time, open, high, low, close, barres clôturées uniquement, triées, une seule source/actif.
    Renvoie une ligne par barre : OHLC, état Kalman, oscillateur, zones/segments/signaux, exécution, `valid` (après warm-up)."""
    need = {"time", "open", "high", "low", "close"}
    if not need <= set(df.columns):
        raise ValueError(f"colonnes manquantes : {sorted(need - set(df.columns))}")
    d = df.reset_index(drop=True)
    if not (d.time.is_monotonic_increasing and d.time.is_unique):
        raise ValueError("time doit être strictement croissant (trié, sans doublon)")
    k = run_kalman(d.close.to_numpy(), kalman)
    o = trend_strength(k.x1.to_numpy(), osc)
    s = zones_and_signals(o.ts.to_numpy(), signal)
    e = execute(s.long_signal, s.short_signal, d.open.to_numpy(), d.close.to_numpy(), fill_price, warmup_bars)
    out = pd.concat([d[["time", "open", "high", "low", "close"]], k, o, s, e], axis=1)
    out["valid"] = np.arange(len(out)) >= warmup_bars
    return out
