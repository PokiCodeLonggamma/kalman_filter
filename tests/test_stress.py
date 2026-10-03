"""EXP-D03.1 — viabilité et sécurité de RE-1 sans modifier le moteur (`envelope.stress`) : stop le plus proche de
plusieurs règles (stop catastrophe greffé sur SL-B), glissement des sorties sur stop, entrées retardées d'une barre
avec le même verrou relatif (niveau déjà franchi : sortie immédiate, brut nul)."""
import numpy as np
import pandas as pd
import pytest

from envelope.stress import delayed_trades, nearest_levels, slip_stops
from optimization.engine import run_trades


def test_stop_le_plus_proche_de_l_entree():
    side = np.array([1, 1, -1, -1, 1])
    slb = np.array([100.0, 90.0, 110.0, 120.0, np.nan])
    cat = np.array([95.0, 95.0, 115.0, 115.0, 80.0])
    assert np.array_equal(nearest_levels(side, slb, cat), [100.0, 95.0, 110.0, 115.0, 80.0])
    assert np.isnan(nearest_levels(np.array([1]), np.array([np.nan]), np.array([np.nan]))[0])


def _trades(barres_synthetiques, signaux_synthetiques, seed=0):
    bars = barres_synthetiques(1500, seed=seed)
    t, s, level = signaux_synthetiques(bars, 250, seed=seed + 1)
    atr = np.random.default_rng(seed).uniform(20.0, 80.0, len(bars))
    return bars, t, s, level, atr, run_trades(bars, t, s, 26, level)


def test_glissement_sur_les_seuls_trades_stoppes(barres_synthetiques, signaux_synthetiques):
    bars, t, s, level, atr, tr = _trades(barres_synthetiques, signaux_synthetiques)
    got = slip_stops(tr, atr, 0.5)
    hit = tr.stop.to_numpy()
    assert hit.sum() > 10 and (~hit).sum() > 10
    a = atr[tr.signal_bar.to_numpy()]
    assert np.allclose(got.ret_gross_bps.to_numpy()[hit], tr.ret_gross_bps.to_numpy()[hit] - 0.5 * a[hit], rtol=1e-12)
    assert got[~hit].equals(tr[~hit])
    p = got.entry_price.to_numpy() * (1.0 + got.side.to_numpy() * got.ret_gross_bps.to_numpy() / 1e4)
    assert np.allclose(got.exit_price.to_numpy()[hit], p[hit], rtol=1e-12)
    assert slip_stops(tr, atr, 0.0).equals(tr)
    mask = np.zeros(len(tr), bool)
    assert slip_stops(tr, atr, 0.5, mask).equals(tr)


def test_retard_nul_redonne_le_noyau(barres_synthetiques, signaux_synthetiques):
    bars, t, s, level, atr, tr = _trades(barres_synthetiques, signaux_synthetiques, seed=2)
    assert delayed_trades(bars, t, s, 26, level, delay=0).equals(tr)


def test_retard_d_une_barre_garde_les_signaux_et_decale_l_entree(barres_synthetiques, signaux_synthetiques):
    bars, t, s, level, atr, tr = _trades(barres_synthetiques, signaux_synthetiques, seed=4)
    got = delayed_trades(bars, t, s, 26, level, delay=1)
    assert got.signal_bar.tolist() == tr.signal_bar.tolist()                  # même population, même verrou
    assert (got.entry_bar.to_numpy() == got.signal_bar.to_numpy() + 2).all()
    x = got.exit_bar.to_numpy()
    timed = (x > got.entry_bar.to_numpy()) & ~got.stop.to_numpy() & (x < len(bars) - 1)    # hors fin de série
    assert np.array_equal(got.entry_price.to_numpy(), bars.open.to_numpy()[got.entry_bar.to_numpy()])
    assert timed.sum() > 10 and (x[timed] == got.signal_bar.to_numpy()[timed] + 28).all()


def test_niveau_deja_franchi_a_l_entree_retardee_sortie_immediate():
    p = np.array([100.0] * 5 + [100.0, 101.0, 95.0, 96.0] + [96.0] * 40)
    bars = pd.DataFrame({"time": pd.date_range("2021-01-01", periods=len(p), freq="30min", tz="UTC"), "open": p,
                         "high": p + 0.5, "low": p - 0.5, "close": p})
    t, s = np.array([5]), np.array([1])
    level = np.array([97.0])                                   # sous l'entrée normale (101), au-dessus de 95
    base = run_trades(bars, t, s, 26, level)
    assert base.stop.iat[0] and base.entry_bar.iat[0] == 6
    got = delayed_trades(bars, t, s, 26, level, delay=1)
    assert got.entry_bar.iat[0] == got.exit_bar.iat[0] == 7 and got.signal_bar.iat[0] == 5
    assert got.ret_gross_bps.iat[0] == 0.0 and got.stop.iat[0] and got.exit_price.iat[0] == got.entry_price.iat[0] == 95.0
    with pytest.raises(ValueError, match="retard"):
        delayed_trades(bars, t, s, 26, level, delay=-1)
