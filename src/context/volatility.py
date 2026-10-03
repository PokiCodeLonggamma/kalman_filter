"""EXP-D03 — mesures de compression lues à la clôture de chaque barre 30 min, sans lookahead.

- `bollinger(close, n, k)` : %B = (clôture − bande basse) / (bande haute − bande basse) et largeur relative
  (bande haute − bande basse) / moyenne. Moyenne mobile simple et écart-type de population des `n` dernières clôtures,
  barre courante comprise (convention TradingView `ta.bb`). Indéfinis avant `n` barres ; %B indéfini si la largeur est
  nulle.
- `trailing_quantile(times, values, q, window, min_span)` : quantile `q` (interpolation linéaire) des valeurs de la
  fenêtre de temps ]t − window, t], barre courante comprise ; indéfini tant que t − première barre < `min_span`.
- `trailing_rank(times, values, window, min_span)` : part des valeurs de la même fenêtre inférieures ou égales à la
  valeur courante ; mêmes règles.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def bollinger(close, n: int = 20, k: float = 2.0) -> tuple[np.ndarray, np.ndarray]:
    """(%B, largeur relative) des bandes de Bollinger (n, k), barre par barre."""
    c = pd.Series(np.asarray(close, dtype=float))
    m = c.rolling(int(n)).mean().to_numpy()
    sd = c.rolling(int(n)).std(ddof=0).to_numpy()
    lo, width = m - k * sd, 2.0 * k * sd
    with np.errstate(invalid="ignore", divide="ignore"):
        pctb = np.where(width > 0, (c.to_numpy() - lo) / width, np.nan)
        bw = width / m
    return pctb, bw


def _defined(times, min_span: str) -> np.ndarray:
    t = pd.DatetimeIndex(times)
    return np.asarray(t - t[0] >= pd.Timedelta(min_span))


def trailing_quantile(times, values, q: float, window: str = "730D", min_span: str = "700D") -> np.ndarray:
    """Quantile glissant causal (fenêtre de temps fermée à droite)."""
    s = pd.Series(np.asarray(values, dtype=float), index=pd.DatetimeIndex(times))
    out = s.rolling(window).quantile(q).to_numpy()
    out[~_defined(times, min_span)] = np.nan
    return out


def trailing_rank(times, values, window: str = "730D", min_span: str = "700D") -> np.ndarray:
    """Rang glissant causal : part des valeurs de la fenêtre ≤ la valeur courante."""
    s = pd.Series(np.asarray(values, dtype=float), index=pd.DatetimeIndex(times))
    out = s.rolling(window).rank(method="max", pct=True).to_numpy()
    out[~_defined(times, min_span)] = np.nan
    return out
