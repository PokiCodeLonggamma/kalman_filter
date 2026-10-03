"""EXP-D04 — pertes journalières du capital valorisé (`envelope.daily`) : mêmes points qu'`equity_curve_sized`,
journée UTC ]J 00:00, J + 1 00:00], référence = capital valorisé à 00:00, extrêmes défavorables en option."""
import numpy as np
import pandas as pd

from envelope import equity_curve_sized, risk_weights
from envelope.daily import daily_losses, marked_equity
from optimization import run_trades


def test_memes_points_que_equity_curve_sized(barres_synthetiques, signaux_synthetiques):
    bars = barres_synthetiques(1500, seed=4)
    t, s, level = signaux_synthetiques(bars, 200, seed=5)
    tr = run_trades(bars, t, s, 26, level)
    w = risk_weights(np.random.default_rng(0).uniform(20, 80, len(tr)), 25.0)
    ref = equity_curve_sized(bars, tr, 5.0, w)
    got = marked_equity(bars, tr, 5.0, w)
    assert got.index.equals(ref.index) and np.allclose(got.to_numpy(), ref.to_numpy(), rtol=1e-15, atol=0)
    ext = marked_equity(bars, tr, 5.0, w, extremes=True)
    assert len(ext) == len(ref) + int((tr.exit_bar - tr.entry_bar).sum())
    d0, d1 = daily_losses(bars, tr, 5.0, w), daily_losses(bars, tr, 5.0, w, extremes=True)
    assert d0.index.equals(d1.index) and (d1.perte <= d0.perte + 1e-15).all()
    assert np.allclose(d0.fin.to_numpy(), d1.fin.to_numpy(), rtol=1e-15, atol=0)   # fin de journée : clôture ou sortie
    assert np.isclose(d0.fin.iat[-1], ref.iat[-1])


def test_journee_utc_et_reference_a_minuit_a_la_main():
    t = pd.date_range("2026-03-01 22:00", periods=8, freq="30min", tz="UTC")       # 22:00 → 01:30
    o = np.array([100.0, 100.0, 99.0, 98.0, 97.0, 96.0, 99.0, 100.0])
    c = np.array([100.0, 99.0, 98.0, 97.0, 96.0, 99.0, 100.0, 100.0])
    bars = pd.DataFrame({"time": t, "open": o, "high": np.maximum(o, c) + 1.0, "low": np.minimum(o, c) - 2.0,
                         "close": c})
    tr = pd.DataFrame({"signal_bar": [0], "entry_bar": [1], "exit_bar": [7], "side": [1], "entry_price": [100.0],
                       "exit_price": [100.0], "ret_gross_bps": [0.0], "stop": [False], "gap": [False]})
    d = daily_losses(bars, tr, 0.0, [0.5])
    # J = 1er mars : clôtures de 22:30 à 00:00 (99, 98, 97) ; 2 mars : 96 (00:30), 99 (01:00), 100 (01:30), sortie
    assert list(d.index.strftime("%m-%d")) == ["03-01", "03-02"]
    assert np.isclose(d.perte.iat[0], 0.5 * (97 / 100 - 1))                       # référence 1 avant le trade
    assert np.isclose(d.debut.iat[1], 1 + 0.5 * (97 / 100 - 1))                   # capital valorisé à minuit
    assert np.isclose(d.perte.iat[1], (1 + 0.5 * (96 / 100 - 1)) / d.debut.iat[1] - 1)
    e = daily_losses(bars, tr, 0.0, [0.5], extremes=True)
    assert np.isclose(e.perte.iat[1], (1 + 0.5 * (94 / 100 - 1)) / d.debut.iat[1] - 1)  # plus bas 94 (00:00-00:30)
    assert daily_losses(bars, tr.iloc[:0], 0.0, []).empty
