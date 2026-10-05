"""EXP-D05.1 — `profil.grille` (mesure descriptive de la grille, sans RE-1 ni coût) : fenêtres disjointes de 26 barres,
mouvement z26 de l'ouverture de t + 1 à celle de t + 27 en ATR14(t) (causal), fréquences des deux sens, repère
gaussien, ratio de variance, efficacité, état calme causal, gaps aux coupures, part des gaps, saison horaire, clôtures
quotidiennes, indépendance, profil complet."""
import math

import numpy as np
import pandas as pd
import pytest

from profil import grille


def barres(close, open_=None, temps=None, ecart=0.0):
    close = np.asarray(close, dtype=float)
    open_ = np.concatenate(([close[0]], close[:-1])) if open_ is None else np.asarray(open_, dtype=float)
    temps = pd.date_range("2024-01-01", periods=len(close), freq="30min", tz="UTC") if temps is None else temps
    return pd.DataFrame({"time": temps, "open": open_, "high": np.maximum(open_, close) + ecart,
                         "low": np.minimum(open_, close) - ecart, "close": close})


def marche(n=400, graine=1, ecart=0.2):
    rng = np.random.default_rng(graine)
    return barres(100 + np.cumsum(rng.normal(0, 0.5, n)), ecart=ecart)


def test_fenetres_disjointes_de_26_barres_apres_l_amorce():
    t = grille.fenetres(300)
    assert t[0] == 100 and np.all(np.diff(t) == 26)
    assert t[-1] + 27 <= 299 and t[-1] + 26 + 27 > 299


def test_z26_de_l_ouverture_de_t_plus_1_a_celle_de_t_plus_27_en_atr_de_t():
    b = marche()
    atr = grille.atr(b)
    t = grille.fenetres(len(b))
    z = grille.z_fenetres(b, atr, t)
    k = 3
    tk = t[k]
    assert z[k] == pytest.approx((b.open.iat[tk + 27] - b.open.iat[tk + 1]) / atr[tk])
    apres = b.copy()
    apres.loc[tk + 28:, ["open", "high", "low", "close"]] += 50.0      # après la sortie : z[k] inchangé
    assert grille.z_fenetres(apres, grille.atr(apres), t)[k] == pytest.approx(z[k])
    dedans = b.copy()
    dedans.loc[tk + 1:tk + 26, "high"] += 30.0                          # dans la fenêtre : ATR(t) inchangé
    assert grille.atr(dedans)[tk] == pytest.approx(atr[tk])


def test_frequences_des_deux_sens_par_an_et_pour_mille_fenetres():
    z = np.array([12, -11, 3, -2, 16, 0.5, -21, 4, 9.9, 10])
    f = grille.frequences(z, ans=2.0, seuils=(10, 15, 20))
    assert (f["haut_10"], f["bas_10"]) == (3, 2)
    assert f["pour_mille_10"] == pytest.approx(500.0) and f["par_an_10"] == pytest.approx(2.5)
    assert (f["haut_20"], f["bas_20"]) == (0, 1)


def test_repere_gaussien_pour_mille_fenetres():
    s = math.sqrt(26) / (2 * math.sqrt(2 / math.pi))
    assert grille.repere_gaussien(10) == pytest.approx(1000 * math.erfc(10 / s / math.sqrt(2)))
    assert grille.repere_gaussien(10) == pytest.approx(1.75, abs=0.05)
    assert grille.repere_gaussien(5) == pytest.approx(117.6, abs=1.0)
    assert grille.repere_gaussien(15) < 0.01


def test_ratio_de_variance_d_une_serie_alternee_et_d_une_serie_sans_autocorrelation_d_ordre_1():
    alternee = 1000 + np.tile([0.0, 1.0], 500)
    assert grille.variance_ratio(alternee, 2) == pytest.approx(0.0, abs=0.01)
    paliers = 1000 + np.tile([0.0, 1.0, 2.0, 1.0], 250)                 # +, +, −, − : ρ1 = 0
    assert grille.variance_ratio(paliers, 2) == pytest.approx(1.0, abs=0.02)


def test_efficacite_d_une_droite_et_d_un_aller_retour():
    droite = np.arange(100, 400, 1.0)
    t = grille.fenetres(len(droite))
    assert np.allclose(grille.efficacite(droite, t), 1.0)
    periode = np.concatenate([np.arange(100, 113), np.arange(113, 100, -1)]).astype(float)   # 26 barres
    aller_retour = np.tile(periode, 15)
    assert np.allclose(grille.efficacite(aller_retour, grille.fenetres(len(aller_retour))), 0.0)


def test_etat_calme_causal_sous_la_mediane_glissante():
    temps = pd.date_range("2024-01-01", periods=200, freq="D", tz="UTC")
    monte = np.arange(1.0, 201.0)
    assert not grille.sous_mediane(monte, temps, "30D")[1:].any()
    assert grille.sous_mediane(monte[::-1].copy(), temps, "30D")[1:].all()
    futur = monte.copy()
    futur[150:] = 0.0                                                   # changer le futur ne change pas le passé
    assert (grille.sous_mediane(futur, temps, "30D")[:150] == grille.sous_mediane(monte, temps, "30D")[:150]).all()


def test_gaps_aux_coupures_en_atr_de_la_barre_precedente():
    t1 = pd.date_range("2024-01-01", periods=200, freq="30min", tz="UTC")
    temps = t1.append(pd.date_range(t1[-1] + pd.Timedelta("2h"), periods=200, freq="30min", tz="UTC"))
    close = np.full(400, 100.0)
    open_ = close.copy()
    open_[200] = 103.0
    b = barres(close, open_=open_, temps=temps, ecart=0.5)
    atr = grille.atr(b)
    g = grille.gaps(b, atr)
    assert len(g) == 1 and g.time.iat[0] == temps[200]
    assert g.taille.iat[0] == pytest.approx(3.0 / atr[199])


def test_part_des_gaps_dans_la_variation_absolue():
    b = barres(np.arange(100, 200, 1.0))                                # ouverture = clôture précédente
    assert grille.part_gaps(b) == pytest.approx(0.0)
    b.loc[50, "open"] = b.close.iat[49] + 10.0                          # gap de 10, corps de 9 au lieu de 1
    assert grille.part_gaps(b) == pytest.approx(10.0 / (10.0 + 98.0 + 9.0))


def test_saison_par_heure_utc():
    temps = pd.date_range("2024-01-01", periods=48 * 10, freq="30min", tz="UTC")
    a = (temps.hour.to_numpy() + 1) / 100.0
    b = pd.DataFrame({"time": temps, "open": 100.0, "high": 100.0 + a, "low": 100.0 - a, "close": 100.0})
    s = grille.saison(b)
    assert list(s.index) == list(range(24))
    assert s.iloc[0] == pytest.approx(2.0) and s.iloc[23] == pytest.approx(48.0)


def test_quotidien_garde_la_derniere_cloture_de_chaque_jour_utc():
    temps = pd.date_range("2024-01-01T22:00", periods=8, freq="30min", tz="UTC")
    q = grille.quotidien(barres(np.arange(1.0, 9.0), temps=temps))
    assert list(q.index) == [pd.Timestamp("2024-01-01", tz="UTC"), pd.Timestamp("2024-01-02", tz="UTC")]
    assert list(q) == [4.0, 8.0]


def test_independance_correlations_et_jours_extremes_communs():
    idx = pd.date_range("2024-01-01", periods=400, freq="D", tz="UTC")
    rng = np.random.default_rng(2)
    ref = pd.Series(100 * np.exp(np.cumsum(rng.normal(0, 0.02, 400))), index=idx)
    r = grille.independance(ref.copy(), ref)
    assert r["corr_abs"] == pytest.approx(1.0) and r["jours_extremes_communs"] == pytest.approx(1.0)
    autre = pd.Series(100 * np.exp(np.cumsum(rng.normal(0, 0.02, 400))), index=idx)
    assert abs(grille.independance(autre, ref)["corr_abs"]) < 0.3


def test_profil_complet_d_une_serie_continue():
    b = marche(n=48 * 7 * 40, graine=3)                                 # 40 semaines continues
    p = grille.profil(b, creux=(b.time.iat[3000], b.time.iat[6000]))
    assert p["heures_par_semaine"] == pytest.approx(168.0)
    assert p["fenetres_coupees"] == 0.0 and p["gaps_par_an"] == 0.0
    for k in ("atr_bps_p50", "pour_mille_5", "vr_26", "efficacite_p50", "expansion_p50", "saison_max_min",
              "z_p99", "calme_tous"):
        assert np.isfinite(p[k]), k
