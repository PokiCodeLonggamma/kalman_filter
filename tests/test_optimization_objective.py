"""EXP-D02 — métriques d'apprentissage (`optimization.objective`) : identiques aux fonctions du dépôt
(`envelope.trade_frame`, `envelope.summarize_sized`, Calmar de `strategy.metrics`) ; Calmar indéfini sans trade ni
drawdown."""
import numpy as np
import pandas as pd

from envelope import stop_trades, summarize_sized, trade_frame
from optimization.engine import prepare_inputs, simulate
from optimization.objective import is_metrics
from strategy.re1 import cagr


def _cas(barres_synthetiques, signaux_synthetiques, seed=0):
    bars = barres_synthetiques(3000, seed=seed)
    t, s, level = signaux_synthetiques(bars, 400, seed=seed + 1)
    tr = stop_trades(bars, t, s, 26, level, dynamic=False)
    atr_bps = pd.Series(np.random.default_rng(seed).uniform(15.0, 90.0, len(bars)), index=np.arange(len(bars)))
    return bars, t, s, level, tr, atr_bps


def test_metriques_egales_aux_fonctions_du_depot(barres_synthetiques, signaux_synthetiques):
    bars, _, _, _, tr, atr_bps = _cas(barres_synthetiques, signaux_synthetiques)
    for fee in (0.0, 5.0, 10.0):
        m = is_metrics(tr, bars.close.to_numpy(), atr_bps.to_numpy(), fee, n_years=2.0)
        sized = summarize_sized(tr, bars, atr_bps, fee, 25.0)
        tf = trade_frame(tr, bars, atr_bps, fee)
        assert m["n_trades"] == len(tr) > 50
        assert np.isclose(m["esperance_atr"], tf.net_atr.mean(), rtol=1e-12, atol=0.0)
        assert m["pnl_r25"] == sized["pnl_compose"] and m["mdd_r25"] == sized["mdd_valorise"] < 0
        assert m["calmar_r25"] == cagr(sized["pnl_compose"], 2.0) / abs(sized["mdd_valorise"])


def test_metriques_des_tableaux_du_noyau(barres_synthetiques, signaux_synthetiques):
    """Même résultat à partir des tableaux de `simulate` (chemin rapide de la grille) que du tableau de trades."""
    bars, t, s, level, tr, atr_bps = _cas(barres_synthetiques, signaux_synthetiques, seed=3)
    arrays = simulate(*prepare_inputs(bars, t, s, 26, level))
    a = is_metrics(arrays, bars.close.to_numpy(), atr_bps.to_numpy(), 5.0, n_years=2.0)
    b = is_metrics(tr, bars.close.to_numpy(), atr_bps.to_numpy(), 5.0, n_years=2.0)
    assert a == b


def test_calmar_indefini_sans_trade_ni_drawdown():
    t = pd.date_range("2021-01-01", periods=8, freq="30min", tz="UTC")
    c = np.array([100.0, 100.0, 101.0, 102.0, 103.0, 104.0, 105.0, 106.0])
    bars = pd.DataFrame({"time": t, "open": c, "high": c + 0.5, "low": c - 0.5, "close": c + 0.5})
    atr = np.full(len(c), 30.0)
    empty = stop_trades(bars, np.array([6]), np.array([1]), 26, None, dynamic=False)
    m = is_metrics(empty, bars.close.to_numpy(), atr, 5.0, n_years=2.0)
    assert m["n_trades"] == 0 and np.isnan(m["esperance_atr"]) and np.isnan(m["calmar_r25"])
    assert m["pnl_r25"] == 0.0 and m["mdd_r25"] == 0.0
    up = stop_trades(bars, np.array([0]), np.array([1]), 4, None, dynamic=False)   # Long sur une hausse régulière
    m = is_metrics(up, bars.close.to_numpy(), atr, 0.0, n_years=2.0)
    assert m["n_trades"] == 1 and m["pnl_r25"] > 0 and m["mdd_r25"] == 0.0 and np.isnan(m["calmar_r25"])
