"""Oscillateur `trend_strength` d'AKF-TSO v2.1 (Pine l. 162-172, 209-210).

A_t     = max(|x1_t|, …, |x1_{t−N2+1}|), défini dès que le buffer contient N2 valeurs ; A := 1 si A ≤ 1e−10
ratio_t = 100 · x1_t / A_t ∈ [−100, 100]
ts_t    = WMA_R2(ratio)                     -> variable du SIGNAL
ts_plot = WMA_R1(ts)                        -> courbe AFFICHÉE uniquement, n'entre jamais dans le signal
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from numpy.lib.stride_tricks import sliding_window_view

from indicator._bounds import check_range


@dataclass(frozen=True)
class OscParams:
    N2: int = 5    # Trend Lookback
    R2: int = 3    # Strength Smoothness (signal)
    R1: int = 3    # Osc Smoothness (affichage)

    def __post_init__(self):
        for name in ("N2", "R2", "R1"):
            check_range(name, getattr(self, name), lo=2, integer=True)   # minval 2 (l. 11-13)


def pine_wma(x: np.ndarray, n: int) -> np.ndarray:
    """ta.wma : poids 1..n (le plus récent pèse n). NaN si la fenêtre contient un NaN."""
    x = np.asarray(x, dtype=float)
    out = np.full(len(x), np.nan)
    if len(x) < n:
        return out
    w = np.arange(1, n + 1, dtype=float)
    win = sliding_window_view(x, n)
    vals = (win * w).sum(axis=1) / w.sum()
    vals[np.isnan(win).any(axis=1)] = np.nan
    out[n - 1:] = vals
    return out


def local_amplitude(x1: np.ndarray, N2: int = 5) -> np.ndarray:
    """A = max|x1| sur N2 barres (barre courante incluse), NaN tant que le buffer est incomplet."""
    a = np.abs(np.asarray(x1, dtype=float))
    A = np.full(len(a), np.nan)
    if len(a) >= N2:
        A[N2 - 1:] = sliding_window_view(a, N2).max(axis=1)
    return np.where(A > 1e-10, A, np.where(np.isnan(A), np.nan, 1.0))


def trend_strength(x1: np.ndarray, p: OscParams = OscParams()) -> pd.DataFrame:
    x1 = np.asarray(x1, dtype=float)
    A = local_amplitude(x1, p.N2)
    ratio = x1 / A * 100
    ts = pine_wma(ratio, p.R2)
    return pd.DataFrame({"A": A, "ratio": ratio, "ts": ts, "ts_plot": pine_wma(ts, p.R1)})
