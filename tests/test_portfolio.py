"""EXP-D03 — capital valorisé d'un portefeuille de plusieurs actifs sur un capital commun (`envelope.portfolio`) :
une jambe seule redonne `equity_curve_sized` et `drawdown_stats` ; chaque trade engage une fraction du capital valorisé
à son entrée (positions ouvertes des autres actifs comprises) ; frais à la sortie ; aucun prix futur lu."""
import numpy as np
import pandas as pd
import pytest

from envelope import equity_curve_sized, risk_weights, stop_trades
from envelope.portfolio import Leg, portfolio_equity
from estimand.stoploss import TRADE_COLUMNS, drawdown_stats


def _jambe(barres_synthetiques, signaux_synthetiques, seed, n=4000, start="2021-01-01", cost=5.0):
    bars = barres_synthetiques(n, seed=seed, start=start)
    t, s, level = signaux_synthetiques(bars, 400, seed=seed + 1)
    tr = stop_trades(bars, t, s, 26, level, dynamic=False)
    atr = np.random.default_rng(seed).uniform(15.0, 90.0, len(bars))
    return Leg(f"A{seed}", bars, tr, risk_weights(atr[tr.signal_bar.to_numpy()], 25.0), cost)


def test_une_jambe_redonne_le_capital_valorise_du_depot(barres_synthetiques, signaux_synthetiques):
    leg = _jambe(barres_synthetiques, signaux_synthetiques, seed=3)
    eq, info = portfolio_equity([leg])
    ref = equity_curve_sized(leg.bars, leg.trades, leg.cost, leg.weight)
    assert len(leg.trades) > 50 and leg.trades.stop.any()
    assert np.isclose(info["pnl"], ref.iloc[-1] - 1.0, rtol=1e-12)
    a, b = drawdown_stats(eq), drawdown_stats(ref)
    assert np.isclose(a["max_drawdown"], b["max_drawdown"], rtol=1e-12)
    assert a["plus_longue_periode_sous_le_pic_jours"] == b["plus_longue_periode_sous_le_pic_jours"]
    assert info["part_temps_deux_positions"] == 0.0 and 0.0 < info["part_temps_en_position"] < 1.0
    assert info["exposition_max"] > 0.0                       # valeur de marché / capital : > poids si le short perd


def test_deux_jambes_sans_chevauchement_composent_le_capital(barres_synthetiques, signaux_synthetiques):
    a = _jambe(barres_synthetiques, signaux_synthetiques, seed=5, n=3000, start="2021-01-01")
    b = _jambe(barres_synthetiques, signaux_synthetiques, seed=7, n=3000, start="2021-04-01")
    assert pd.Timestamp(a.bars.time.iat[-1]) < pd.Timestamp(b.bars.time.iat[0])
    pa, pb = portfolio_equity([a])[1]["pnl"], portfolio_equity([b])[1]["pnl"]
    assert np.isclose(portfolio_equity([a, b])[1]["pnl"], (1.0 + pa) * (1.0 + pb) - 1.0, rtol=1e-12)


def _barres(prix, start="2021-01-01"):
    p = np.asarray(prix, dtype=float)
    return pd.DataFrame({"time": pd.date_range(start, periods=len(p), freq="30min", tz="UTC"), "open": p, "high": p,
                         "low": p, "close": p})


def _trade(bars, e, x, side):
    p0, p1 = bars.open.iat[e], bars.open.iat[x]
    return pd.DataFrame([{"entry_bar": e, "exit_bar": x, "side": side, "entry_price": p0, "exit_price": p1,
                          "stop": False, "gap": False, "ret_gross_bps": side * (p1 / p0 - 1.0) * 1e4,
                          "signal_bar": e - 1}])[TRADE_COLUMNS]


def test_positions_simultanees_taille_sur_le_capital_valorise():
    """B entre pendant que A est ouverte : son notionnel vaut sa fraction du capital valorisé à l'entrée."""
    ba = _barres([100, 100, 110, 120, 120, 120, 120, 120])
    bb = _barres([50, 50, 50, 50, 40, 40, 40, 40])
    ta, tb = _trade(ba, 1, 5, 1), _trade(bb, 3, 6, -1)
    eq, info = portfolio_equity([Leg("A", ba, ta, np.array([0.5]), 0.0), Leg("B", bb, tb, np.array([0.5]), 0.0)])
    e_b = 1.0 + 0.5 * (110 / 100 - 1.0)                     # A valorisée à la clôture de la barre 2 (= ouverture 3)
    n_b = 0.5 * e_b
    final = 1.0 + 0.5 * (120 / 100 - 1.0) + n_b * (1.0 - 40 / 50)
    assert np.isclose(info["pnl"], final - 1.0, rtol=1e-12)
    assert np.isclose(eq.iloc[-1], final, rtol=1e-12)
    assert info["part_temps_deux_positions"] > 0.0
    with pytest.raises(ValueError, match="chevauch"):
        portfolio_equity([Leg("A", ba, pd.concat([ta, _trade(ba, 3, 6, 1)], ignore_index=True), np.array([0.5, 0.5]),
                              0.0)])


def test_frais_preleves_a_la_sortie_sur_le_notionnel():
    ba = _barres([100, 100, 110, 110])
    eq, info = portfolio_equity([Leg("A", ba, _trade(ba, 1, 3, 1), np.array([0.5]), 10.0)])
    assert np.isclose(info["pnl"], 0.5 * (0.10 - 10.0 / 1e4), rtol=1e-12)


def test_portefeuille_ne_lit_aucun_prix_futur(barres_synthetiques, signaux_synthetiques):
    a = _jambe(barres_synthetiques, signaux_synthetiques, seed=9)
    b = _jambe(barres_synthetiques, signaux_synthetiques, seed=11)
    eq, _ = portfolio_equity([a, b])
    cut = pd.Timestamp(b.bars.time.iat[2500])
    bars = b.bars.copy()
    bars.loc[2500:, "close"] *= 1.7
    eq2, _ = portfolio_equity([a, Leg(b.name, bars, b.trades, b.weight, b.cost)])
    before = eq.index < cut
    assert before.sum() > 1000 and np.array_equal(eq.to_numpy()[before], eq2.to_numpy()[before])


def test_chemins_du_portefeuille_redonnent_portfolio_equity(barres_synthetiques, signaux_synthetiques):
    """EXP-D04.1 : un état par instant ; capital valorisé = dernière valeur de `portfolio_equity` à chaque instant ;
    solde réalisé, borne pessimiste ≤ capital valorisé, résultats par jambe sommés = capital − 1."""
    from envelope.portfolio import portfolio_paths
    a = _jambe(barres_synthetiques, signaux_synthetiques, seed=9)
    b = _jambe(barres_synthetiques, signaux_synthetiques, seed=11)
    eq, info = portfolio_equity([a, b])
    p = portfolio_paths([a, b])
    ref, got = eq.groupby(level=0).last(), p.capital_valorise.groupby(level=0).last()
    assert got.index.equals(ref.index) and np.allclose(got.to_numpy(), ref.to_numpy(), rtol=1e-12, atol=0)
    assert np.isclose(p.solde_realise.iat[-1], 1.0 + info["pnl"], rtol=1e-12)
    assert (p.capital_pessimiste <= p.capital_valorise + 1e-12).all() and (p.capital_pessimiste < p.capital_valorise).any()
    assert np.allclose(p[[f"pnl_{a.name}", f"pnl_{b.name}"]].sum(axis=1).to_numpy(), p.capital_valorise.to_numpy() - 1.0,
                       rtol=0, atol=1e-12)
    assert p.exposition_brute.max() <= info["exposition_max"] + 1e-12 and p.exposition_brute.max() > 1.0
    flat = p.exposition_brute == 0.0
    assert flat.any() and np.allclose(p.solde_realise[flat], p.capital_valorise[flat], rtol=1e-12)


def test_borne_pessimiste_a_la_main():
    """Deux achats ouverts ensemble : à la clôture de la barre, chaque jambe est valorisée à son plus bas."""
    from envelope.portfolio import portfolio_paths
    t = pd.date_range("2021-01-01", periods=5, freq="30min", tz="UTC")
    ba = pd.DataFrame({"time": t, "open": [100.0] * 5, "high": [101.0] * 5, "low": [100, 100, 90, 100, 100.0],
                       "close": [100, 100, 98, 100, 100.0]})
    bb = pd.DataFrame({"time": t, "open": [50.0] * 5, "high": [51.0] * 5, "low": [50, 50, 40, 50, 50.0],
                       "close": [50, 50, 49, 50, 50.0]})
    ta, tb = _trade(ba, 1, 4, 1), _trade(bb, 1, 4, 1)
    p = portfolio_paths([Leg("A", ba, ta, np.array([0.5]), 0.0), Leg("B", bb, tb, np.array([0.5]), 0.0)])
    at = t[2] + pd.Timedelta(minutes=30)                      # clôture de la barre 2
    assert np.isclose(p.capital_valorise[at], 1 + 0.5 * (98 / 100 - 1) + 0.5 * (49 / 50 - 1))
    assert np.isclose(p.capital_pessimiste[at], 1 + 0.5 * (90 / 100 - 1) + 0.5 * (40 / 50 - 1))
    assert np.isclose(p.solde_realise[at], 1.0) and np.isclose(p.exposition_brute[at], (0.5 * 0.98 + 0.5 * 0.98)
                                                                / p.capital_valorise[at])


def test_une_jambe_journees_identiques_a_daily_losses(barres_synthetiques, signaux_synthetiques):
    """Une jambe : mêmes pertes journalières (valeurs ≤ 0) que `envelope.daily.daily_losses`, clôtures et extrêmes. Le
    point de l'instant d'entrée, au capital réalisé, ramène à 0 une « perte » positive ; les journées en plus (instant
    d'entrée seul) ont une perte nulle."""
    from envelope.daily import daily_from_paths, daily_losses
    from envelope.portfolio import portfolio_paths
    leg = _jambe(barres_synthetiques, signaux_synthetiques, seed=13)
    p = portfolio_paths([leg])
    for ext in (False, True):
        a = daily_from_paths(p.capital_valorise, low=p.capital_pessimiste if ext else None)
        b = daily_losses(leg.bars, leg.trades, leg.cost, leg.weight, extremes=ext)
        common = a.index.intersection(b.index)
        la, lb = np.minimum(a.perte[common], 0.0), np.minimum(b.perte[common], 0.0)    # pertes (≤ 0) seulement :
        assert len(common) == len(b) and np.allclose(la, lb, rtol=1e-12, atol=1e-15)      # l'instant d'entrée vaut le
        assert (a.perte.drop(common).abs() < 1e-15).all()                                 # capital de minuit
