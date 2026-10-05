"""EXP-D05.4 — simulateur de challenge de prop firm (`propfirm`).

Un départ = un compte à plat qui ne prend que les trades entrés à partir de lui. Sans plafond de marge ni correction du
stop, le départ qui voit tous les trades redonne `envelope.portfolio_paths`. Marge plafonnée au prorata des entrées
simultanées, libérée par les sorties du même instant. Règles : objectif après 4 jours de trading, perte du jour depuis
le solde (ou le maximum du solde et de l'équité) de minuit CET/CEST, perte totale statique, borne pessimiste. Aucun prix
futur lu."""
import numpy as np
import pandas as pd

from envelope import risk_weights, stop_trades
from envelope.portfolio import Leg, portfolio_paths
from estimand.stoploss import TRADE_COLUMNS
from propfirm import (EN_COURS, INF, PERTE_JOUR, Regles, Simulation, challenge, departs_minuit, issue_phase, resume,
                      simuler)

H = pd.Timedelta(minutes=30)
COLS = ["capital_valorise", "solde_realise", "capital_pessimiste", "exposition_brute", "positions"]
SERRE = Regles(objectifs=(0.02, 0.01), perte_jour=0.01, perte_max=0.02, jours_min=2)   # seuils serrés : des événements


def _jambe(barres_synthetiques, signaux_synthetiques, seed, n=4000, start="2021-01-01", cost=5.0):
    bars = barres_synthetiques(n, seed=seed, start=start)
    t, s, level = signaux_synthetiques(bars, 400, seed=seed + 1)
    tr = stop_trades(bars, t, s, 26, level, dynamic=False)
    atr = np.random.default_rng(seed).uniform(15.0, 90.0, len(bars))
    return Leg(f"A{seed}", bars, tr, risk_weights(atr[tr.signal_bar.to_numpy()], 25.0), cost)


def _barres(prix, start, low=None):
    p = np.asarray(prix, dtype=float)
    return pd.DataFrame({"time": pd.date_range(start, periods=len(p), freq="30min", tz="UTC"), "open": p, "high": p,
                         "low": p if low is None else np.asarray(low, dtype=float), "close": p})


def _trades(bars, specs):
    """specs : (entrée, sortie, sens) — sortie à l'ouverture de la barre de sortie — ou (entrée, barre du stop, sens,
    prix du stop)."""
    rows = []
    for sp in specs:
        e, x, side = sp[:3]
        p0 = bars.open.iat[e]
        stop = len(sp) > 3
        p1 = sp[3] if stop else bars.open.iat[x]
        rows.append({"entry_bar": e, "exit_bar": x, "side": side, "entry_price": p0, "exit_price": p1, "stop": stop,
                     "gap": False, "ret_gross_bps": side * (p1 / p0 - 1.0) * 1e4, "signal_bar": e - 1})
    return pd.DataFrame(rows)[TRADE_COLUMNS]


def _ns(x) -> int:
    return pd.Timestamp(x).value


def _temps(sim, i):
    """Tous les instants d'événement du départ i."""
    out = [sim.t_objectif[k][i] for k in range(len(sim.t_objectif))]
    out += [sim.t_perte_max[m][i] for m in sorted(sim.t_perte_max)]
    out += [sim.t_perte_jour[k][i] for k in sorted(sim.t_perte_jour)]
    return out


def test_sans_plafond_ni_correction_le_depart_qui_voit_tout_redonne_portfolio_paths(barres_synthetiques,
                                                                                     signaux_synthetiques):
    a = _jambe(barres_synthetiques, signaux_synthetiques, seed=9)
    b = _jambe(barres_synthetiques, signaux_synthetiques, seed=11)
    sim = simuler([a, b], [_ns("2020-12-31 23:00+00:00")], correction_stop=False, suivi=0)
    ref = portfolio_paths([a, b])
    assert sim.chemin.index.equals(ref.index)
    assert np.allclose(sim.chemin[COLS].to_numpy(float), ref[COLS].to_numpy(float), rtol=1e-12, atol=1e-15)


def test_chaque_depart_vaut_un_calcul_seul_et_ignore_les_trades_anterieurs(barres_synthetiques, signaux_synthetiques):
    """Le calcul vectorisé redonne, départ par départ, un calcul seul ; retirer les trades entrés avant le départ ne
    change rien (compte à plat)."""
    a = _jambe(barres_synthetiques, signaux_synthetiques, seed=9)
    b = _jambe(barres_synthetiques, signaux_synthetiques, seed=11)
    dep = departs_minuit("2021-01-01", "2021-03-01")
    lev = {a.name: 2.0, b.name: 2.0}
    multi = simuler([a, b], dep, SERRE, levier=lev, plafonner=True)
    assert (multi.t_objectif < INF).any() and (multi.t_perte_jour[("solde", "pessimiste")] < INF).any()
    for i in (0, 7, 23, 40):
        seul = simuler([a, b], dep[i:i + 1], SERRE, levier=lev, plafonner=True)
        assert _temps(multi, i) == _temps(seul, 0)

    def apres(leg, t0):
        keep = pd.DatetimeIndex(leg.bars.time).asi8[leg.trades.entry_bar.to_numpy()] >= t0
        return Leg(leg.name, leg.bars, leg.trades[keep].reset_index(drop=True), np.asarray(leg.weight)[keep], leg.cost)

    i = 23
    filtre = simuler([apres(a, dep[i]), apres(b, dep[i])], dep[i:i + 1], SERRE, levier=lev, plafonner=True)
    assert _temps(multi, i) == _temps(filtre, 0)


def test_plafond_de_marge_au_prorata_des_entrees_simultanees():
    bars = _barres([100.0] * 6, "2021-01-04 09:00")
    legs = [Leg(n, bars, _trades(bars, [(1, 4, 1)]), np.array([0.8]), 0.0) for n in ("A", "B", "C")]
    dep, lev = [_ns("2021-01-03 23:00+00:00")], {"A": 2.0, "B": 2.0, "C": 2.0}
    sim = simuler(legs, dep, levier=lev, plafonner=True, suivi=0)
    assert np.allclose(sim.tailles.demande, 0.8) and np.allclose(sim.tailles.obtenu, 0.8 / 1.2)
    assert np.isclose(sim.chemin.marge.max(), 1.0)
    libre = simuler(legs, dep, levier=lev, plafonner=False, suivi=0)
    assert np.allclose(libre.tailles.obtenu, 0.8) and np.isclose(libre.chemin.marge.max(), 1.2)


def test_plafond_de_marge_libere_par_les_sorties_du_meme_instant():
    bars = _barres([100.0] * 8, "2021-01-04 09:00")
    a = Leg("A", bars, _trades(bars, [(1, 4, 1)]), np.array([1.0]), 0.0)
    b = Leg("B", bars, _trades(bars, [(1, 6, 1)]), np.array([1.0]), 0.0)
    c = Leg("C", bars, _trades(bars, [(2, 3, 1), (4, 6, -1)]), np.array([1.0, 1.0]), 0.0)
    sim = simuler([a, b, c], [_ns("2021-01-03 23:00+00:00")], levier={"A": 2.0, "B": 2.0, "C": 2.0}, plafonner=True,
                  suivi=0)
    t = sim.tailles.set_index(["jambe", "trade"]).obtenu
    assert np.isclose(t["A", 0], 1.0) and np.isclose(t["B", 0], 1.0)
    assert t["C", 0] == 0.0                                   # A et B prennent toute la marge : trade sauté
    assert np.isclose(t["C", 1], 1.0)                         # A sort à l'ouverture de la barre 4, avant l'entrée de C


def test_perte_du_jour_depuis_le_solde_ou_le_maximum_de_minuit():
    """Gain latent de 6 % à minuit CET, rendu le lendemain : perte du jour pour la référence « max(solde, équité) »,
    pas pour la référence « solde » (FTMO). L'état daté de minuit appartient à la veille."""
    bars = _barres([100, 100, 102, 104, 105, 106, 100.5, 100.5, 100.5, 100.5], "2021-01-04 20:00")
    leg = Leg("A", bars, _trades(bars, [(1, 8, 1)]), np.array([1.0]), 0.0)    # clôture de la barre 5 : minuit CET
    sim = simuler([leg], [_ns("2021-01-03 23:00+00:00")])
    for mode in ("pessimiste", "valorise"):
        assert sim.t_perte_jour[("max", mode)][0] == _ns("2021-01-04 23:30+00:00")   # premier état du lendemain
        assert sim.t_perte_jour[("solde", mode)][0] == INF
        assert sim.t_perte_max[mode][0] == INF


def test_objectif_atteint_apres_quatre_jours_de_trading():
    bars = _barres(np.r_[np.full(5, 100.0), np.full(195, 110.0)], "2021-01-04 23:00")   # barre 0 : minuit CET
    tr = _trades(bars, [(2, 10, 1), (50, 52, 1), (98, 100, 1), (146, 148, 1)])          # un trade par jour local
    leg = Leg("A", bars, tr, np.ones(4), 0.0)
    dep, t = [_ns("2021-01-04 23:00+00:00")], pd.DatetimeIndex(bars.time).asi8
    un = simuler([leg], dep, Regles(objectifs=(0.09, 0.05), jours_min=1))
    quatre = simuler([leg], dep, Regles(objectifs=(0.09, 0.05), jours_min=4))
    assert un.t_objectif[0][0] == t[5] + H.value              # +10 % à la clôture de la barre 5, premier jour
    assert quatre.t_objectif[0][0] == t[146] and quatre.t_objectif[1][0] == t[146]   # entrée du quatrième jour


def test_perte_totale_sur_la_borne_pessimiste_et_cause_au_plancher_le_plus_haut():
    bars = _barres([100.0, 100.0, 96.0, 96.0, 96.0], "2021-01-04 09:00", low=[100.0, 100.0, 89.0, 96.0, 96.0])
    leg = Leg("A", bars, _trades(bars, [(1, 4, 1)]), np.array([1.0]), 0.0)
    sim = simuler([leg], [_ns("2021-01-03 23:00+00:00")])
    t2 = pd.DatetimeIndex(bars.time).asi8[2] + H.value
    assert sim.t_perte_max["pessimiste"][0] == t2 and sim.t_perte_max["valorise"][0] == INF
    assert sim.t_perte_jour[("solde", "pessimiste")][0] == t2 and sim.t_perte_jour[("solde", "valorise")][0] == INF
    issue, t = issue_phase(sim, 0, "solde", "pessimiste")
    assert issue[0] == PERTE_JOUR and t[0] == t2              # le plancher du jour (0,95) est franchi avant 0,90
    issue, _ = issue_phase(sim, 0, "solde", "valorise")
    assert issue[0] == EN_COURS


def test_correction_du_stop_cumule_sa_perte_et_l_extreme_des_autres():
    t0 = "2021-01-04 09:00"
    ba = _barres([100.0, 100.0, 97.0, 97.0], t0, low=[100.0, 100.0, 90.0, 97.0])
    bb = _barres([50.0, 50.0, 49.0, 49.0], t0, low=[50.0, 50.0, 40.0, 49.0])
    a = Leg("A", ba, _trades(ba, [(1, 2, 1, 95.0)]), np.array([0.5]), 0.0)       # stoppé à 95 pendant la barre 2
    b = Leg("B", bb, _trades(bb, [(1, 3, 1)]), np.array([0.5]), 0.0)
    dep, at = [_ns("2021-01-03 23:00+00:00")], pd.Timestamp(ba.time.iat[2]) + H     # clôture de la barre 2
    sans = simuler([a, b], dep, correction_stop=False, suivi=0).chemin
    avec = simuler([a, b], dep, correction_stop=True, suivi=0).chemin
    assert np.isclose(sans.capital_pessimiste[at].min(), 1 + 0.5 * (40 / 50 - 1))   # A à sa clôture précédente
    assert np.isclose(avec.capital_pessimiste[at].min(), 1 + 0.5 * (95 / 100 - 1) + 0.5 * (40 / 50 - 1))
    assert np.isclose(avec.capital_valorise[at].iloc[-1], sans.capital_valorise[at].iloc[-1])   # même état ensuite


def test_departs_aux_minuits_cet_cest():
    d = pd.to_datetime(departs_minuit("2021-03-26", "2021-03-30"), utc=True)
    assert list(d.strftime("%Y-%m-%d %H:%M")) == ["2021-03-25 23:00", "2021-03-26 23:00", "2021-03-27 23:00",
                                                  "2021-03-28 22:00"]          # heure d'été le 28 mars à 02:00
    e = pd.to_datetime(departs_minuit("2021-10-31", "2021-11-02"), utc=True)
    assert list(e.strftime("%H:%M")) == ["22:00", "23:00"]                     # heure d'hiver le 31 octobre à 03:00


def test_le_simulateur_ne_lit_aucun_prix_futur(barres_synthetiques, signaux_synthetiques):
    a = _jambe(barres_synthetiques, signaux_synthetiques, seed=9)
    b = _jambe(barres_synthetiques, signaux_synthetiques, seed=11)
    dep, lev = departs_minuit("2021-01-01", "2021-03-01"), {a.name: 2.0, b.name: 2.0}
    ref = simuler([a, b], dep, SERRE, levier=lev, plafonner=True, suivi=0)
    cut = pd.Timestamp(b.bars.time.iat[2500])
    bars = b.bars.copy()
    bars.loc[2500:, ["close", "low", "high"]] *= 1.7
    mod = simuler([a, Leg(b.name, bars, b.trades, b.weight, b.cost)], dep, SERRE, levier=lev, plafonner=True, suivi=0)
    c = cut.value
    for x, y in zip([ref.t_objectif[k] for k in range(2)] + [ref.t_perte_max[m] for m in ref.t_perte_max]
                    + [ref.t_perte_jour[k] for k in ref.t_perte_jour],
                    [mod.t_objectif[k] for k in range(2)] + [mod.t_perte_max[m] for m in ref.t_perte_max]
                    + [mod.t_perte_jour[k] for k in ref.t_perte_jour]):
        assert np.array_equal(np.where(x < c, x, -1), np.where(y < c, y, -1))
    before = ref.chemin.index < cut
    assert before.sum() > 1000 and np.array_equal(ref.chemin[before].to_numpy(float), mod.chemin[before].to_numpy(float),
                                                  equal_nan=True)


def _simulation(departs, t_objectif):
    s = len(departs)
    modes, refs = ("pessimiste", "valorise"), ("solde", "max")
    return Simulation(departs=np.asarray(departs, dtype=np.int64), regles=Regles(),
                      t_objectif=np.asarray(t_objectif, dtype=np.int64),
                      t_perte_max={m: np.full(s, INF, dtype=np.int64) for m in modes},
                      t_perte_jour={(r, m): np.full(s, INF, dtype=np.int64) for r in refs for m in modes},
                      ref_breche={(r, m): np.full(s, np.nan) for r in refs for m in modes}, chemin=None, tailles=None)


def test_challenge_enchaine_p2_au_minuit_suivant_et_censure_apres_la_coupure():
    h = 3_600 * 10**9
    d = departs_minuit("2021-01-04", "2021-01-08")            # 4 minuits CET
    t_obj = np.full((2, 4), INF, dtype=np.int64)
    t_obj[0, 0] = d[1] + 5 * h                                # départ 0 : P1 réussie le 2e jour → P2 = départ 2
    t_obj[1, 2] = d[3] + h                                    # objectif de P2 atteint par le départ 2
    t_obj[0, 3] = d[3] + h                                    # départ 3 : P1 réussie, plus aucun minuit ensuite
    sim = _simulation(d, t_obj)
    sim.t_perte_jour[("solde", "pessimiste")][1] = d[1] + 2 * h          # départ 1 : perte du jour
    sim.ref_breche[("solde", "pessimiste")][1] = 1.0
    out = challenge(sim)
    assert list(out.issue) == ["reussite", "echec_p1_jour", "en_cours_p1", "en_cours_p2"]
    assert np.isclose(out.jours_p1.iat[0], 1 + 5 / 24) and np.isclose(out.jours_total.iat[0], 3 + 1 / 24)
    assert np.isclose(out.jours_p1.iat[1], 2 / 24)
    coupe = challenge(sim, coupure=d[3])                      # événements après la coupure non observés
    assert list(coupe.issue) == ["en_cours_p2", "echec_p1_jour", "en_cours_p1"]


def test_resume_parts_delais_et_intervalle():
    out = pd.DataFrame({"depart": pd.date_range("2021-01-01", periods=6, freq="20D", tz="Europe/Prague"),
                        "issue_p1": ["reussite", "reussite", "perte_jour", "reussite", "en_cours", "reussite"],
                        "jours_p1": [4.0, 9.0, 2.0, 3.0, np.nan, 8.0],
                        "issue": ["reussite", "reussite", "echec_p1_jour", "echec_p2_max", "en_cours_p1", "reussite"],
                        "jours_total": [10.0, 30.0, np.nan, 5.0, np.nan, 20.0]})
    r = resume(out, n_boot=200, seed=1)
    parts = ["reussite", "echec_p1_jour", "echec_p1_max", "echec_p2_jour", "echec_p2_max", "en_cours_p1",
             "en_cours_p2"]
    assert r["n_departs"] == 6 and np.isclose(r["p_reussite"], 0.5) and np.isclose(r["p_reussite_p1"], 4 / 6)
    assert np.isclose(sum(r[f"p_{k}"] for k in parts), 1.0)
    assert r["jours_total_med"] == 20.0 and r["jours_p1_med"] == 6.0      # parmi les réussites
    assert r["ic_bas"] <= r["p_reussite"] <= r["ic_haut"]
