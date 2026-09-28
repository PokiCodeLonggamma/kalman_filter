"""Tests de `estimand.stoploss` repris à l'identique de #KAKALMAN `tests/test_estimand_p65d.py` (P6.5d, D48).

Les 11 tests sur données construites sont copiés sans modification. Les 4 tests du script `strategie_stop.py` ne sont
pas repris : ce script importe des modules non copiés (`estimand.payoff`, `estimand.strata`, `estimand.exit_rule`,
`estimand_audit`) et le dataset ML1. L'ancre P6.5d sur données réelles est contrôlée dans `tests/test_envelope.py`.
Empreinte du fichier d'origine : experiments/C01/manifest_copie_C01_sha256.txt.
"""
import numpy as np
import pandas as pd
import pytest

from config import P65D_COST_BPS, P65D_STOP
from estimand.stoploss import apply_stop, drawdown_stats, equity_curve, simulate_strategy

T0 = pd.Timestamp("2021-01-01", tz="UTC")


def _bars(o, h=None, l=None, c=None):
    o = np.asarray(o, float)
    return pd.DataFrame({"time": T0 + pd.to_timedelta(np.arange(len(o)) * 30, unit="min"), "open": o,
                         "high": o + 0.5 if h is None else np.asarray(h, float),
                         "low": o - 0.5 if l is None else np.asarray(l, float),
                         "close": o if c is None else np.asarray(c, float)})


def test_config_pre_enregistree():
    assert P65D_STOP == 0.025 and P65D_COST_BPS == 5.0


def test_stop_long_et_short_niveau_gap_et_barre_d_entree():
    o = [100, 100, 99, 96, 101, 102, 103]
    lo = [99.5, 98.0, 97.0, 95.0, 100, 101, 102]
    hi = [100.5, 100.5, 99.5, 97, 102, 103, 104]
    b = _bars(o, hi, lo)
    r = apply_stop(b, [1, 1, 4], [6, 6, 6], [1, 1, -1], P65D_STOP)
    assert r.stop.tolist() == [True, True, False]
    assert r.exit_bar.iat[0] == 2 and r.exit_price.iat[0] == pytest.approx(97.5) and not r.gap.iat[0]
    assert r.ret_gross_bps.iat[0] == pytest.approx(-250.0)
    g = apply_stop(_bars([100, 100, 96, 101], [100.5, 100.5, 97, 102], [99.5, 99.0, 95, 100]), [1], [3], [1], 0.025)
    assert g.stop.iat[0] and g.gap.iat[0] and g.exit_price.iat[0] == 96 and g.ret_gross_bps.iat[0] == pytest.approx(-400)
    e = apply_stop(_bars([100, 100, 101], [100.5, 100.5, 102], [99.5, 97.0, 100]), [1], [2], [1], 0.025)
    assert e.stop.iat[0] and e.exit_bar.iat[0] == 1 and e.exit_price.iat[0] == pytest.approx(97.5)   # barre d'entrée
    s = apply_stop(_bars([100, 100, 104, 99], [100.5, 101, 105, 100], [99.5, 99.5, 103, 98]), [1, 1], [3, 3], [-1, -1],
                   0.025)
    assert s.stop.all() and s.gap.all() and s.exit_price.iat[0] == 104 and s.ret_gross_bps.iat[0] == pytest.approx(-400)
    assert r.ret_gross_bps.iat[2] == pytest.approx(-(103 / 101 - 1) * 1e4)        # pas de stop : sortie à open[6]


def test_stop_prioritaire_sur_la_barre_du_signal_oppose_et_jamais_mieux_que_le_niveau():
    b = _bars([100, 100, 101, 99, 100], [100.5, 101, 102, 99.5, 101], [99.5, 99.8, 100, 97.0, 99])
    r = apply_stop(b, [1], [4], [1], 0.025)                         # signal opposé à la clôture de 3, sortie open[4]
    assert r.stop.iat[0] and r.exit_bar.iat[0] == 3 and r.exit_price.iat[0] == pytest.approx(97.5)
    rng = np.random.default_rng(0)
    o = 100 * np.exp(np.cumsum(rng.normal(0, 0.01, 800)))
    c = np.r_[o[1:], o[-1]]
    bb = _bars(o, np.maximum(o, c) * 1.003, np.minimum(o, c) * 0.997, c)
    e = rng.integers(0, 600, 300)
    s = rng.choice([-1, 1], 300)
    t = apply_stop(bb, e, e + rng.integers(7, 150, 300), s, 0.025)
    assert t.stop.any() and (t.ret_gross_bps[t.stop] <= -250 + 1e-9).all()
    np.testing.assert_allclose(t.ret_gross_bps[t.stop & ~t.gap], -250.0)


def test_sans_stop_rendement_de_la_cible_b():
    rng = np.random.default_rng(1)
    o = 100 * np.exp(np.cumsum(rng.normal(0, 0.01, 300)))
    b = _bars(o)
    e = rng.integers(0, 200, 50)
    x = e + rng.integers(1, 90, 50)
    s = rng.choice([-1, 1], 50)
    r = apply_stop(b, e, x, s, None)
    np.testing.assert_array_equal(r.ret_gross_bps.to_numpy(), s * (o[x] / o[e] - 1.0) * 1e4)
    assert not r.stop.any() and (r.exit_bar.to_numpy() == x).all()


def _sig(t, s):
    return pd.DataFrame({"bar_index": np.asarray(t, np.int64), "side": np.asarray(s, np.int64)})


def test_simulation_sans_stop_retournement_et_pyramiding_0():
    b = _bars(np.linspace(100, 110, 60))
    tr, ouvert = simulate_strategy(b, _sig([5, 8, 12, 20, 25, 40], [1, 1, -1, -1, 1, -1]), None)
    assert tr[["entry_bar", "exit_bar", "side"]].values.tolist() == [[6, 13, 1], [13, 26, -1], [26, 41, 1]]
    assert ouvert == {"entry_bar": 41, "side": -1, "signal_bar": 40}         # aucun signal opposé avant la fin


def test_simulation_avec_stop_a_plat_puis_prochain_signal_de_tout_sens():
    o = np.full(60, 100.0)
    lo = o - 0.5
    lo[9] = 97.0                                                    # stop du Long entré en 6
    b = _bars(o, o + 0.5, lo)
    tr, _ = simulate_strategy(b, _sig([5, 8, 12, 20, 30], [1, 1, 1, -1, 1]), 0.025)
    assert tr[["entry_bar", "exit_bar", "side", "stop"]].values.tolist() == [
        [6, 9, 1, True], [13, 21, 1, False], [21, 31, -1, False]]   # le signal 8 (déjà en position) est ignoré
    lo2 = o - 0.5
    lo2[12] = 97.0                                                  # stop pendant la barre du signal 12
    tr2, _ = simulate_strategy(_bars(o, o + 0.5, lo2), _sig([5, 12, 20], [1, 1, -1]), 0.025)
    assert tr2[["entry_bar", "exit_bar", "stop"]].values.tolist()[:2] == [[6, 12, True], [13, 21, False]]


def test_capital_compose_et_drawdown():
    o = np.array([100, 100, 110, 110, 99, 99, 99, 108.9, 108.9, 108.9])
    b = _bars(o, c=o)
    tr = pd.DataFrame({"entry_bar": [1, 4], "exit_bar": [3, 7], "side": [1, 1], "entry_price": [100.0, 99.0],
                       "ret_gross_bps": [1000.0, 1000.0]})
    tr["stop"] = False
    eq = equity_curve(b, tr, 0.0)
    assert eq.tolist() == pytest.approx([1.0, 1.0, 1.1, 1.1, 1.0 * 1.1, 1.1, 1.1, 1.21])
    assert eq.index[0] == b.time[1] and eq.index[3] == b.time[3]                       # sortie à l'ouverture de 3
    d = drawdown_stats(pd.Series([1.0, 1.2, 0.9, 1.0, 1.3], index=pd.date_range("2021", periods=5)))
    assert d["max_drawdown"] == pytest.approx(0.9 / 1.2 - 1) and d["plus_longue_periode_sous_le_pic_jours"] == 3
    eqc = equity_curve(b, tr, 50.0)
    assert eqc.iloc[-1] == pytest.approx(1.095 * 1.095)


def test_stop_sur_la_derniere_barre_sans_sortie_dans_l_echantillon():
    o = np.full(8, 100.0)
    lo = o - 0.5
    lo[7] = 97.0                                                    # dernière barre de l'échantillon
    tr, ouvert = simulate_strategy(_bars(o, o + 0.5, lo), _sig([3], [1]), 0.025)
    assert ouvert is None and tr[["entry_bar", "exit_bar", "stop"]].values.tolist() == [[4, 7, True]]
    tr2, ouvert2 = simulate_strategy(_bars(o, o + 0.5, o - 0.5), _sig([3], [1]), 0.025)
    assert len(tr2) == 0 and ouvert2 == {"entry_bar": 4, "side": 1, "signal_bar": 3}


def test_stop_au_niveau_exact_et_reentree_de_sens_oppose():
    o = np.full(40, 100.0)
    lo, hi = o - 0.5, o + 0.5
    lo[8] = 97.5                                                    # exactement au niveau : stop (conservateur)
    tr, _ = simulate_strategy(_bars(o, hi, lo), _sig([5, 10, 20], [1, -1, 1]), 0.025)
    assert tr[["entry_bar", "exit_bar", "side", "stop"]].values.tolist()[:2] == [[6, 8, 1, True], [11, 21, -1, False]]
    assert tr.exit_price.iat[0] == pytest.approx(97.5)
    hi2 = o + 0.5
    hi2[13] = 102.5
    s = apply_stop(_bars(o, hi2, lo), [11], [21], [-1], 0.025)
    assert s.stop.iat[0] and s.exit_price.iat[0] == pytest.approx(102.5)


def test_stop_sur_la_barre_du_signal_oppose_puis_entree_opposee():
    o = np.full(40, 100.0)
    lo = o - 0.5
    lo[12] = 97.0                                                   # signal Short à la clôture de 12
    tr, _ = simulate_strategy(_bars(o, o + 0.5, lo), _sig([5, 12, 25], [1, -1, 1]), 0.025)
    assert tr[["entry_bar", "exit_bar", "side", "stop"]].values.tolist()[:2] == [[6, 12, 1, True], [13, 26, -1, False]]


def test_capital_au_retournement_et_valorisation_short():
    o = np.array([100.0, 100, 100, 100, 90, 90, 90, 90])
    c = np.array([100.0, 100, 100, 95, 85, 88, 90, 90])
    b = _bars(o, c=c)
    tr = pd.DataFrame({"entry_bar": [1, 4], "exit_bar": [4, 6], "side": [1, -1], "entry_price": [100.0, 90.0],
                       "ret_gross_bps": [-1000.0, 0.0], "stop": [False, False]})
    eq = equity_curve(b, tr, 0.0)
    assert eq.tolist() == pytest.approx([1.0, 1.0, 1.0, 0.95, 0.9, 0.9 * (1 - (85 / 90 - 1)), 0.9 * (1 - (88 / 90 - 1)),
                                         0.9])
    assert drawdown_stats(eq)["max_drawdown"] == pytest.approx(-0.1)              # le creux réalisé est vu
