"""EXP-D02 — règle de choix en IS (`optimization.selection`, validée par le porteur) : admissibilité (E[ATR] net > 0,
MDD < 0), score = moyenne du Calmar de la configuration et de ses voisins immédiats (±1 pas sur un axe), voisin
inadmissible compté pour sa valeur, Calmar indéfini compté 0, égalité départagée par la distance à RE-1 puis l'ordre,
repli sur RE-1. Bord de grille : voisins existants (défaut, lecture littérale) ou voisin absent compté 0 (option)."""
import numpy as np
import pytest

from optimization.selection import neighbour_mean, select


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


def test_bord_de_grille_voisins_existants_ou_zero():
    assert np.allclose(neighbour_mean(np.array([1.0, 3.0])), [2.0, 2.0])
    assert np.allclose(neighbour_mean(np.array([1.0, 3.0]), edge="zero"), [4 / 3, 4 / 3])
    v = np.ones((3, 3, 3))
    assert neighbour_mean(v, edge="zero")[0, 0, 0] == 4 / 7 and neighbour_mean(v, edge="zero")[1, 1, 1] == 1.0
    with pytest.raises(ValueError, match="bord"):
        neighbour_mean(v, edge="miroir")


def test_un_pic_isole_perd_contre_un_plateau():
    calmar = np.array([-2.0, 5.0, -2.0, 1.5, 1.6, 1.5, 0.2])
    idx, info = select(np.full(7, 0.1), calmar, np.full(7, -0.1), ref=(1,))
    assert idx == (4,) and not info["repli"]


def test_effet_de_bord_de_la_lecture_litterale():
    """Plateau au bord de la grille : la case du bord, moins entourée, l'emporte ; voisin absent = 0, le centre."""
    calmar = np.array([-2.0, 5.0, -2.0, 1.5, 1.6, 1.5])
    e, mdd = np.full(6, 0.1), np.full(6, -0.1)
    assert select(e, calmar, mdd, ref=(1,))[0] == (5,)
    assert select(e, calmar, mdd, ref=(1,), edge="zero")[0] == (4,)


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
