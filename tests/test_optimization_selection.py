"""EXP-D02 — règles de choix en IS (`optimization.selection`).

- Règle retenue par le porteur (second GO, 2026-10-01), `select_plateau` : plus grande zone connexe (±1 pas sur un axe)
  de configurations admissibles (E[ATR] net > 0, MDD < 0) à Calmar net > 0, puis la case la plus proche de son centre
  géométrique ; égalités : distance à RE-1, puis ordre ; aucune zone : repli sur RE-1. Calmar indéfini : jamais choisi.
- Lecture littérale du score de voisinage (`select`), non retenue ; l'option « voisin absent = 0 » est rejetée."""
import numpy as np

from optimization.selection import neighbour_mean, plateau_zones, select, select_plateau


def test_score_de_voisinage_en_une_dimension():
    assert np.allclose(neighbour_mean(np.array([1.0, 2.0, 3.0, 10.0])), [1.5, 2.0, 5.0, 6.5])


def test_score_de_voisinage_en_trois_dimensions():
    v = np.arange(27, dtype=float).reshape(3, 3, 3)
    sc = neighbour_mean(v)
    assert sc[0, 0, 0] == (v[0, 0, 0] + v[1, 0, 0] + v[0, 1, 0] + v[0, 0, 1]) / 4
    centre = v[1, 1, 1] + v[0, 1, 1] + v[2, 1, 1] + v[1, 0, 1] + v[1, 2, 1] + v[1, 1, 0] + v[1, 1, 2]
    assert sc[1, 1, 1] == centre / 7


def test_calmar_indefini_compte_zero_dans_le_score():
    assert np.allclose(neighbour_mean(np.array([np.nan, 3.0, 3.0])), [1.5, 2.0, 3.0])


def test_bord_de_grille_moyenne_des_voisins_existants():
    assert np.allclose(neighbour_mean(np.array([1.0, 3.0])), [2.0, 2.0])


def test_un_pic_isole_perd_contre_un_plateau():
    calmar = np.array([-2.0, 5.0, -2.0, 1.5, 1.6, 1.5, 0.2])
    idx, info = select(np.full(7, 0.1), calmar, np.full(7, -0.1), ref=(1,))
    assert idx == (4,) and not info["repli"]


def test_effet_de_bord_de_la_lecture_litterale_corrige_par_la_zone_connexe():
    """Plateau au bord : la lecture littérale choisit la case du bord ; la règle retenue, le centre de la zone."""
    calmar = np.array([-2.0, 5.0, -2.0, 1.5, 1.6, 1.5])
    e, mdd = np.full(6, 0.1), np.full(6, -0.1)
    assert select(e, calmar, mdd, ref=(1,))[0] == (5,)
    idx, info = select_plateau(e, calmar, mdd, ref=(1,))
    assert idx == (4,) and info["zone"] == 3 and info["n_zones"] == 2


def test_inadmissible_jamais_choisi_mais_compte_comme_voisin():
    calmar = np.array([0.25, 0.5, 8.0, 0.5, 0.25])
    e = np.array([0.1, 0.1, -0.01, 0.1, 0.1])                 # le pic est inadmissible (espérance ≤ 0)
    idx, info = select(e, calmar, np.full(5, -0.1), ref=(4,))
    assert idx == (3,) and info["n_admissibles"] == 4         # ses voisins en profitent ; égalité : proche de RE-1


def test_mdd_nul_rend_inadmissible():
    idx, _ = select(np.full(3, 0.2), np.array([1.0, 2.0, 1.0]), np.array([-0.1, 0.0, -0.1]), ref=(0,))
    assert idx == (0,)


def test_egalite_departagee_par_la_distance_a_re1_puis_l_ordre():
    e = np.full((3, 3), 0.1)
    e[1, 1] = -0.1                                            # RE-1 inadmissible, tous les scores égaux
    idx, _ = select(e, np.ones((3, 3)), np.full((3, 3), -0.1), ref=(1, 1))
    assert idx == (0, 1)                                      # quatre cases à distance 1 : ordre lexicographique


def test_repli_sur_re1_sans_configuration_admissible():
    idx, info = select(np.array([-0.1, 0.0, np.nan]), np.array([1.0, 2.0, 3.0]), np.full(3, -0.1), ref=(1,))
    assert idx == (1,) and info["repli"] and info["n_admissibles"] == 0


# ── Règle retenue : zone connexe à Calmar > 0 et son centre ─────────────────────
def test_zones_connexes_par_faces():
    m = np.zeros((3, 3), dtype=bool)
    m[0, 0] = m[0, 1] = m[1, 1] = True                    # une zone de trois cases
    m[2, 2] = True                                         # une case isolée (diagonale non connexe)
    zones = plateau_zones(m)
    assert sorted(len(z) for z in zones) == [1, 3]
    assert {tuple(c) for z in zones if len(z) == 3 for c in z} == {(0, 0), (0, 1), (1, 1)}


def test_plus_grande_zone_puis_case_la_plus_proche_du_centre():
    calmar = np.array([1.0, 1.0, 1.0, 0.5, -1.0, 9.0])     # zone {0..3} (4 cases), pic isolé {5}
    e, mdd = np.full(6, 0.1), np.full(6, -0.1)
    idx, info = select_plateau(e, calmar, mdd, ref=(5,))
    assert idx == (2,) and info["zone"] == 4                # centre 1,5 : cases 1 et 2 à égalité, 2 plus proche de RE-1
    assert np.isclose(info["centre"][0], 1.5)


def test_zone_restreinte_aux_cases_admissibles_a_calmar_positif():
    calmar = np.array([2.0, 2.0, 2.0, 2.0, 2.0])
    e = np.array([0.1, 0.1, -0.1, 0.1, 0.1])                # case 2 inadmissible : elle coupe la zone
    mdd = np.array([-0.1, -0.1, -0.1, -0.1, 0.0])           # case 4 sans drawdown : Calmar indéfini, exclue
    idx, info = select_plateau(e, calmar, mdd, ref=(4,))
    assert info["zone"] == 2 and idx == (1,) and info["n_zones"] == 2   # zones {0, 1} et {3} ; centre 0,5 : 1, vers RE-1
    neg = select_plateau(np.full(3, 0.1), np.array([-1.0, np.nan, 0.0]), np.full(3, -0.1), ref=(1,))
    assert neg[0] == (1,) and neg[1]["repli"]


def test_egalite_de_taille_departagee_par_le_calmar_moyen():
    calmar = np.array([1.0, 1.0, -1.0, 2.0, 2.0])
    idx, info = select_plateau(np.full(5, 0.1), calmar, np.full(5, -0.1), ref=(0,))
    assert idx in {(3,), (4,)} and info["calmar_zone"] == 2.0


def test_zone_en_trois_dimensions():
    c = np.full((3, 3, 3), -1.0)
    c[:2, :2, :2] = 1.0                                     # bloc de 8 cases contre un coin
    c[2, 2, 2] = 50.0                                       # pic isolé
    idx, info = select_plateau(np.full(c.shape, 0.1), c, np.full(c.shape, -0.1), ref=(1, 1, 1))
    assert info["zone"] == 8 and idx == (1, 1, 1)           # 8 cases à égale distance du centre : RE-1 l'emporte


# ── EXP-D02.1 : inertie (porteur, 2026-10-03) ── égalité au centre : la case la plus proche du paramètre de la fenêtre
# précédente (première fenêtre : meilleur Calmar IS) ; aucune zone : paramètre précédent (première : meilleur Calmar).

def _carte(calmar):
    c = np.asarray(calmar, dtype=float)
    return np.full(c.shape, 0.1), c, np.full(c.shape, -0.1)


def test_inertie_egalite_au_centre_departagee_par_le_parametre_precedent():
    e, c, m = _carte([-1.0, 2.0, 3.0, -1.0, -1.0])           # zone {1, 2}, centre 1,5 : égalité
    assert select_plateau(e, c, m, ref=(0,))[0] == (1,)       # D02 : la plus proche de RE-1
    idx, info = select_plateau(e, c, m, ref=(0,), prev=(4,), inertie=True)
    assert idx == (2,) and info["inertie"] == "egalite" and not info["repli"]
    assert select_plateau(e, c, m, ref=(4,), prev=(0,), inertie=True)[0] == (1,)
    assert select_plateau(e, c, m, ref=(0,), prev=(2,), inertie=True)[0] == (2,)


def test_inertie_premiere_fenetre_egalite_au_meilleur_calmar():
    e, c, m = _carte([-1.0, 2.0, 3.0, -1.0, -1.0])
    idx, info = select_plateau(e, c, m, ref=(0,), prev=None, inertie=True)
    assert idx == (2,) and info["inertie"] == "egalite"


def test_inertie_sans_zone_garde_le_parametre_precedent():
    e, c, m = _carte([-1.0, -0.5, -2.0, -0.1])
    idx, info = select_plateau(e, c, m, ref=(0,), prev=(2,), inertie=True)
    assert idx == (2,) and info["repli"] and info["inertie"] == "aucune zone"


def test_inertie_sans_zone_premiere_fenetre_au_meilleur_calmar_defini():
    e, c, m = _carte([-1.0, -0.5, np.nan, -0.1])
    idx, info = select_plateau(e, c, m, ref=(0,), prev=None, inertie=True)
    assert idx == (3,) and info["repli"] and info["inertie"] == "aucune zone"
    e, c, m = _carte([np.nan, np.nan])
    assert select_plateau(e, c, m, ref=(1,), prev=None, inertie=True)[0] == (1,)


def test_inertie_sans_effet_hors_egalite():
    e, c, m = _carte([-1.0, 2.0, 3.0, 1.0, -1.0])            # zone {1, 2, 3} : centre 2
    for prev in (None, (0,), (4,)):
        idx, info = select_plateau(e, c, m, ref=(0,), prev=prev, inertie=True)
        assert idx == (2,) and info["inertie"] is None


def test_sans_inertie_la_regle_de_d02_ignore_le_precedent():
    e, c, m = _carte([-1.0, 2.0, 3.0, -1.0, -1.0])
    assert select_plateau(e, c, m, ref=(0,), prev=(4,))[0] == (1,)
    e, c, m = _carte([-1.0, -0.5])
    idx, info = select_plateau(e, c, m, ref=(0,), prev=(1,))
    assert idx == (0,) and info["repli"] and info["inertie"] is None
