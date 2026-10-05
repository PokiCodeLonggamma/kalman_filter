"""EXP-D05.7 — tirage par blocs de semaines (`propfirm.blocs`) : bornes des semaines, tirage, histoires recomposées."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from envelope import risk_weights, stop_trades
from envelope.portfolio import Leg
from estimand.stoploss import TRADE_COLUMNS
from propfirm import Fixe, Regles, departs_minuit, simuler
from propfirm.blocs import histoire, semaines, tirage

SERRE = Regles(objectifs=(0.02, 0.01), perte_jour=0.01, perte_max=0.02, jours_min=2)
SEMAINE = 7 * 86_400 * 10**9


def _jambe(barres_synthetiques, signaux_synthetiques, seed, n=4000, start="2021-01-03 23:00"):
    bars = barres_synthetiques(n, seed=seed, start=start)
    t, s, level = signaux_synthetiques(bars, 300, seed=seed + 1)
    tr = stop_trades(bars, t, s, 26, level, dynamic=False)
    atr = np.random.default_rng(seed).uniform(15.0, 90.0, len(bars))[tr.signal_bar.to_numpy()]
    return Leg(f"A{seed}", bars, tr, risk_weights(atr, 25.0), 5.0), atr


def _main(prix, specs, start="2021-01-03 23:00"):
    p = np.asarray(prix, dtype=float)
    bars = pd.DataFrame({"time": pd.date_range(start, periods=len(p), freq="30min", tz="UTC"), "open": p, "high": p,
                         "low": p, "close": p})
    rows = [{"entry_bar": e, "exit_bar": x, "side": 1, "entry_price": p[e], "exit_price": p[x], "stop": False,
             "gap": False, "ret_gross_bps": (p[x] / p[e] - 1.0) * 1e4, "signal_bar": e - 1} for e, x in specs]
    tr = pd.DataFrame(rows)[TRADE_COLUMNS]
    return Leg("A", bars, tr, np.ones(len(tr)), 0.0), np.full(len(tr), 50.0)


def _dans(leg: Leg, atr, debut: int, fin: int):
    """La jambe réduite aux trades entrés dans [debut, fin[."""
    t = pd.DatetimeIndex(leg.bars.time).asi8[leg.trades.entry_bar.to_numpy()]
    m = (t >= debut) & (t < fin)
    return Leg(leg.name, leg.bars, leg.trades[m].reset_index(drop=True), leg.weight[m], leg.cost), atr[m]


def test_semaines_du_lundi_minuit_local_cet_cest():
    b = semaines("2021-10-04", "2021-11-08")
    assert len(b) == 6                                        # 5 semaines entières, 6 bornes
    assert b[0] == pd.Timestamp("2021-10-03 22:00", tz="UTC").value      # lundi 00:00 CEST
    assert b[-1] == pd.Timestamp("2021-11-07 23:00", tz="UTC").value     # lundi 00:00 CET
    with pytest.raises(ValueError):
        semaines("2021-10-05", "2021-11-08")                  # pas un lundi


def test_tirage_par_blocs_de_semaines_consecutives_tronque_a_la_longueur_de_l_histoire():
    src = tirage(10, 4, np.random.default_rng(3))
    assert len(src) == 10 and src.min() >= 0 and src.max() <= 9
    for k in (0, 4, 8):                                       # chaque bloc : semaines consécutives
        bloc = src[k:k + 4]
        assert np.array_equal(bloc, bloc[0] + np.arange(len(bloc)))
    assert np.array_equal(tirage(10, 1, np.random.default_rng(5)), tirage(10, 1, np.random.default_rng(5)))


def test_histoire_identite_redonne_la_simulation_des_trades_de_la_fenetre(barres_synthetiques, signaux_synthetiques):
    (a, xa), (b, xb) = (_jambe(barres_synthetiques, signaux_synthetiques, seed=s) for s in (21, 23))
    bornes = semaines("2021-01-04", "2021-03-15")             # 10 semaines
    lg, atr = histoire([a, b], [xa, xb], bornes, np.arange(10))
    assert len(lg) == 2                                       # aucun chevauchement : une jambe par actif
    (a2, xa2), (b2, xb2) = _dans(a, xa, bornes[0], bornes[-1]), _dans(b, xb, bornes[0], bornes[-1])
    dep = departs_minuit("2021-01-04", "2021-03-15")
    kw = dict(levier={a.name: 2.0, b.name: 2.0}, plafonner=True, taille=Fixe(25.0))
    ref = simuler([a2, b2], dep, SERRE, atr=[xa2, xb2], **kw)
    sim = simuler(lg, dep, SERRE, atr=atr, **kw)
    for k in range(2):
        assert np.array_equal(ref.t_objectif[k], sim.t_objectif[k])
    for m in ref.t_perte_max:
        assert np.array_equal(ref.t_perte_max[m], sim.t_perte_max[m])
    for key in ref.t_perte_jour:
        assert np.array_equal(ref.t_perte_jour[key], sim.t_perte_jour[key])


def test_histoire_deplace_chaque_trade_avec_son_chemin_et_son_atr(barres_synthetiques, signaux_synthetiques):
    a, xa = _jambe(barres_synthetiques, signaux_synthetiques, seed=31)
    bornes = semaines("2021-01-04", "2021-02-01")             # 4 semaines
    src = np.array([2, 0, 2, 1])
    (h,), (xh,) = histoire([a], [xa], bornes, src)
    t0 = pd.DatetimeIndex(a.bars.time).asi8
    sem = np.searchsorted(bornes, t0[a.trades.entry_bar.to_numpy()], side="right") - 1
    th = pd.DatetimeIndex(h.bars.time).asi8
    attendus = [(k, j) for k, w in enumerate(src) for j in np.flatnonzero(sem == w)]
    assert len(h.trades) == len(attendus)
    for i, (k, j) in enumerate(attendus):
        o, n = a.trades.iloc[j], h.trades.iloc[i]
        dec = bornes[k] - bornes[src[k]]
        assert th[n.entry_bar] == t0[o.entry_bar] + dec and th[n.exit_bar] == t0[o.exit_bar] + dec
        assert n.exit_bar - n.entry_bar == o.exit_bar - o.entry_bar
        seg_h = h.bars.close.to_numpy()[n.entry_bar:n.exit_bar + 1]
        seg_o = a.bars.close.to_numpy()[o.entry_bar:o.exit_bar + 1]
        assert np.array_equal(seg_h, seg_o)
        assert (n.side, n.entry_price, n.ret_gross_bps, n.stop) == (o.side, o.entry_price, o.ret_gross_bps, o.stop)
        assert xh[i] == xa[j]


def test_histoire_ouvre_une_jambe_de_debordement_si_un_trade_deborde_sur_le_suivant():
    # semaine source 0 : B lundi 02:00 → 15:00 ; A dimanche 20:00 → lundi 09:00 de la semaine suivante (débordement)
    lg0, x0 = _main(100.0 + np.arange(702) * 0.01, [(4, 30), (328, 354)])
    bornes = semaines("2021-01-04", "2021-01-18")
    lg, atr = histoire([lg0], [x0], bornes, np.array([0, 0]))
    assert [leg.name for leg in lg] == ["A", "A"] and [len(leg.trades) for leg in lg] == [3, 1]
    for leg in lg:                                            # aucun chevauchement dans une jambe
        t = pd.DatetimeIndex(leg.bars.time).asi8
        e, x = t[leg.trades.entry_bar.to_numpy()], t[leg.trades.exit_bar.to_numpy()]
        assert (x[:-1] <= e[1:]).all()
    t1 = pd.DatetimeIndex(lg[1].bars.time).asi8
    assert t1[lg[1].trades.entry_bar.iat[0]] == pd.Timestamp("2021-01-11 01:00", tz="UTC").value   # B, semaine 1
    assert [len(a) for a in atr] == [3, 1]
