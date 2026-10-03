"""RE-1 version finale (décision du porteur du 2026-10-03, après EXP-D03.1) : RE-1 gelée et un stop catastrophe à
4 ATR14(t) greffé sur tous les trades.

- Candidats : ceux de RE-1 gelée (`optimization.candidates` aux seuils BTC gelés, frontière 0,85, R0 = 100 dans
  l'atlas) ;
- Stops : F2b, le stop catastrophe seul, open[t + 1] − sens · 4 · ATR14(t) (SL-A de C02) ; F3, le plus proche de
  l'entrée entre SL-B (extremum du segment, δ = 0, plancher 0,25 ATR) et le stop catastrophe
  (`envelope.stress.nearest_levels`) ;
- Exécution : noyau `optimization.run_trades`, H = 26, verrou 26 (= H), entrée à open[t + 1], sortie à open[t + 27] ou
  au stop (intrabarre ; ouverture au-delà en cas de gap) ; une position à la fois. Le stop ne change pas le verrou :
  mêmes entrées que RE-1 gelée.

Sur BTC 2015-2025 et SOL, redonne trade par trade la série « Stop catastrophe 4 ATR » d'EXP-D03.1 (contrôle bloquant
d'EXP-D04). Non exporté par `strategy/__init__` (`optimization` importe `strategy`) : `from strategy.final import …`.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from envelope import atr_stop_levels
from envelope.stress import nearest_levels
from optimization import candidates, run_trades
from strategy.re1 import F3_BOUNDARY, H, LEG_ATR_P50_BTC, NIS_Z100_P75_BTC

K_CAT = 4.0
BPS = 1e4


def final_levels(bars: pd.DataFrame, signal_bar, side, level, atr_bps, k: float = K_CAT) -> np.ndarray:
    """Niveaux de la version finale : le plus proche de l'entrée entre `level` (SL-B de F3 ; NaN pour F2b) et le stop
    catastrophe à k · ATR14(t). `atr_bps` : ATR14 en bps du close, un par barre de la série."""
    t = np.asarray(signal_bar, dtype=np.int64)
    atr_px = np.asarray(atr_bps, dtype=float)[t] * bars.close.to_numpy(dtype=float)[t] / BPS
    return nearest_levels(side, level, atr_stop_levels(bars, t, side, atr_px, k))


def run_final(bars: pd.DataFrame, tab, atr_bps, start: pd.Timestamp | None = None, end: pd.Timestamp | None = None,
              k: float = K_CAT) -> tuple[pd.DataFrame, tuple, pd.Series]:
    """Trades de la version finale sur les signaux de [start, end) ; (t, sens, SL-B, niveaux finaux) des candidats ;
    famille de chaque candidat (F2b sans SL-B, F3 avec)."""
    t, s, lv = candidates(tab, LEG_ATR_P50_BTC, NIS_Z100_P75_BTC, F3_BOUNDARY, start, end)
    lvl = final_levels(bars, t, s, lv, atr_bps, k)
    trades = run_trades(bars, t, s, H, lvl)
    return trades, (t, s, lv, lvl), pd.Series(np.where(np.isnan(lv), "F2b", "F3"), index=t)
