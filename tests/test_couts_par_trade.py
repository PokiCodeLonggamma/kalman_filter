"""EXP-D05.1 — frais propres à chaque trade (écart à l'heure du trade, commission, swaps) dans `envelope.portfolio`,
`propfirm.simuler` et `propfirm.blocs`. Un frais scalaire reste accepté ; un tableau constant redonne le scalaire."""
import numpy as np
import pandas as pd
import pytest

from envelope import risk_weights, stop_trades
from envelope.portfolio import Leg, leg_costs, portfolio_equity, portfolio_paths
from estimand.stoploss import TRADE_COLUMNS
from propfirm import Fixe, Regles, departs_minuit, simuler
from propfirm.blocs import histoire, semaines


def _jambe(barres_synthetiques, signaux_synthetiques, seed, cost, n=4000, start="2021-01-04 00:00"):
    bars = barres_synthetiques(n, seed=seed, start=start)
    t, s, level = signaux_synthetiques(bars, 400, seed=seed + 1)
    tr = stop_trades(bars, t, s, 26, level, dynamic=False)
    atr = np.random.default_rng(seed).uniform(15.0, 90.0, len(bars))[tr.signal_bar.to_numpy()]
    c = cost(len(tr)) if callable(cost) else cost
    return Leg(f"A{seed}", bars, tr, risk_weights(atr, 25.0), c), atr


def _main(prix, specs, cost, start="2021-01-04 08:00"):
    p = np.asarray(prix, dtype=float)
    bars = pd.DataFrame({"time": pd.date_range(start, periods=len(p), freq="30min", tz="UTC"), "open": p, "high": p,
                         "low": p, "close": p})
    rows = [{"entry_bar": e, "exit_bar": x, "side": 1, "entry_price": p[e], "exit_price": p[x], "stop": False,
             "gap": False, "ret_gross_bps": (p[x] / p[e] - 1.0) * 1e4, "signal_bar": e - 1} for e, x in specs]
    tr = pd.DataFrame(rows)[TRADE_COLUMNS]
    return Leg("A", bars, tr, np.ones(len(tr)), cost)


def test_leg_costs_scalaire_ou_un_frais_par_trade():
    leg = _main([100.0] * 12, [(1, 3), (5, 9)], 5.0)
    assert np.array_equal(leg_costs(leg), [5.0, 5.0])
    leg.cost = np.array([2.0, 7.0])
    assert np.array_equal(leg_costs(leg), [2.0, 7.0])
    leg.cost = np.array([2.0, 7.0, 1.0])
    with pytest.raises(ValueError, match="un frais par trade"):
        leg_costs(leg)


def test_tableau_constant_redonne_le_scalaire(barres_synthetiques, signaux_synthetiques):
    a, atr_a = _jambe(barres_synthetiques, signaux_synthetiques, 3, 5.0)
    b, _ = _jambe(barres_synthetiques, signaux_synthetiques, 3, lambda n: np.full(n, 5.0))
    ea, ra = portfolio_equity([a])
    eb, rb = portfolio_equity([b])
    assert ea.equals(eb) and ra == rb
    assert portfolio_paths([a]).equals(portfolio_paths([b]))
    dep = departs_minuit("2021-01-04", "2021-03-01", "Europe/Prague")
    sa = simuler([a], dep, taille=Fixe(25.0), atr=[atr_a])
    sb = simuler([b], dep, taille=Fixe(25.0), atr=[atr_a])
    for k in range(len(sa.t_objectif)):
        assert np.array_equal(sa.t_objectif[k], sb.t_objectif[k])
    for m in sa.t_perte_max:
        assert np.array_equal(sa.t_perte_max[m], sb.t_perte_max[m])
    for k in sa.t_perte_jour:
        assert np.array_equal(sa.t_perte_jour[k], sb.t_perte_jour[k])


def test_frais_preleves_trade_par_trade():
    prix = [100.0] * 4 + [100.0, 100.0, 101.0, 102.0, 102.0, 103.0, 103.0, 103.0]
    leg = _main(prix, [(1, 3), (5, 9)], np.array([10.0, 40.0]))
    _, r = portfolio_equity([leg])
    k0 = 1.0 - 10.0 / 1e4                                    # trade 0 : brut nul, 10 bps de frais
    assert r["pnl"] == pytest.approx(k0 * (1.0 + (300.0 - 40.0) / 1e4) - 1.0, rel=1e-12)
    pp = portfolio_paths([leg])
    assert pp.solde_realise.iat[-1] == pytest.approx(1.0 + r["pnl"], rel=1e-12)


def test_frais_de_sortie_du_trade_ouvert_dans_l_objectif():
    """L'objectif retire les frais de sortie du trade ouvert : ceux du trade 1, pas ceux du trade 0."""
    prix = [100.0] * 5 + [100.0, 101.0, 102.1, 102.4, 103.0, 103.0, 103.0]
    regles = Regles(objectifs=(0.02, 0.01), perte_jour=0.05, perte_max=0.10, jours_min=1)
    t = pd.date_range("2021-01-04 08:00", periods=len(prix), freq="30min", tz="UTC").asi8
    dep = np.array([t[0]])
    sans = simuler([_main(prix, [(1, 3), (5, 9)], np.array([0.0, 0.0]))], dep, regles)
    avec = simuler([_main(prix, [(1, 3), (5, 9)], np.array([0.0, 50.0]))], dep, regles)
    assert sans.t_objectif[0][0] == t[7] + 30 * 60 * 10**9     # clôture de la barre 7 : 1,021 ≥ 1,02
    assert avec.t_objectif[0][0] == t[9]                        # 1,021 − 0,005 < 1,02 : atteint à la sortie (1,025)


def test_histoire_garde_le_frais_de_chaque_trade(barres_synthetiques, signaux_synthetiques):
    leg, atr = _jambe(barres_synthetiques, signaux_synthetiques, 5, lambda n: np.arange(n, dtype=float))
    b = semaines("2021-01-04", "2021-03-01")
    t = pd.DatetimeIndex(leg.bars.time).asi8[leg.trades.entry_bar.to_numpy()]
    out, _ = histoire([leg], [atr], b, np.arange(len(b) - 1))
    m = (t >= b[0]) & (t < b[-1])
    assert np.array_equal(np.concatenate([leg_costs(x) for x in out]), np.flatnonzero(m).astype(float))
