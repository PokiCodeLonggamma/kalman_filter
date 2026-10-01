"""EXP-D02 — métriques d'une évaluation d'apprentissage (IS), à risque constant de 0,25 % du capital par ATR14(t).

Mêmes définitions, mêmes opérations dans le même ordre que le dépôt (résultats identiques, testés) :
- espérance nette en ATR14(t) : moyenne de (brut − frais) / ATR14(t) en bps (`envelope.trade_frame`) ;
- PnL composé et MDD valorisé à 0,25 %/ATR (`envelope.summarize_sized`, `equity_curve_sized`, `drawdown_stats`) :
  capital valorisé à chaque clôture de barre détenue et à chaque sortie, poids min(1, 25 / ATR14 en bps) ;
- Calmar = CAGR / |MDD valorisé| (`strategy.re1.metrics`), indéfini (NaN) sans drawdown, donc aussi sans trade.
"""
from __future__ import annotations

import numpy as np
from numba import njit

from envelope import risk_weights
from estimand.excursions import BPS
from strategy.re1 import RISK_BPS, cagr


@njit(cache=True)
def _sized_path(close, entry_bar, exit_bar, side, entry_price, ret, w, cost):
    capital = 1.0
    peak = 1.0
    mdd = 0.0
    for i in range(entry_bar.shape[0]):
        ws = w[i] * side[i]
        for j in range(entry_bar[i], exit_bar[i]):
            v = capital * (1.0 + ws * (close[j] / entry_price[i] - 1.0))
            if v > peak:
                peak = v
            dd = v / peak - 1.0
            if dd < mdd:
                mdd = dd
        capital = capital * (1.0 + w[i] * (ret[i] - cost) / BPS)
        if capital > peak:
            peak = capital
        dd = capital / peak - 1.0
        if dd < mdd:
            mdd = dd
    return capital - 1.0, mdd


def is_metrics(trades, close: np.ndarray, atr_bps: np.ndarray, fee: float, risk_bps: float = RISK_BPS,
               n_years: float = 2.0) -> dict:
    """`trades` : tableau de trades ou tableaux de `engine.simulate` (colonnes de `TRADE_COLUMNS`), dans l'ordre
    chronologique ; `close`, `atr_bps` : par barre (position) ; `fee` : frais aller-retour en bps."""
    sb = np.asarray(trades["signal_bar"], dtype=np.int64)
    n = len(sb)
    if not n:
        return {"n_trades": 0, "esperance_atr": np.nan, "pnl_r25": 0.0, "mdd_r25": 0.0, "calmar_r25": np.nan}
    atr = np.asarray(atr_bps, dtype=float)[sb]
    ret = np.asarray(trades["ret_gross_bps"], dtype=float)
    w = risk_weights(atr, risk_bps)
    pnl, mdd = _sized_path(np.asarray(close, dtype=float), np.asarray(trades["entry_bar"], dtype=np.int64),
                           np.asarray(trades["exit_bar"], dtype=np.int64), np.asarray(trades["side"], dtype=np.int64),
                           np.asarray(trades["entry_price"], dtype=float), ret, w, float(fee))
    pnl = np.float64(pnl)
    calmar = cagr(pnl, n_years) / abs(mdd) if mdd < 0 else np.nan
    return {"n_trades": n, "esperance_atr": float(np.mean((ret - fee) / atr)), "pnl_r25": float(pnl),
            "mdd_r25": float(mdd), "calmar_r25": float(calmar)}
