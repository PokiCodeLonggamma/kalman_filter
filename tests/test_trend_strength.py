"""Tests unitaires de l'oscillateur."""
import numpy as np

from indicator.trend_strength import OscParams, local_amplitude, pine_wma, trend_strength


def test_wma_poids_pine():
    assert pine_wma(np.array([1.0, 2.0, 3.0]), 3)[-1] == (1 + 4 + 9) / 6
    assert np.isnan(pine_wma(np.array([1.0, np.nan, 3.0, 4.0]), 3)).tolist() == [True, True, True, True]


def test_ratio_aveugle_a_l_amplitude():
    """P0 §4.4 : le même profil à deux échelles donne le même ratio."""
    x1 = np.array([0, 0, 0, 0, 20, 18, 14, 9, 4, 0], dtype=float)
    for s in (1.0, 0.01):
        r = trend_strength(x1 * s).ratio.to_numpy()
        assert np.isnan(r[:4]).all()
        assert np.allclose(r[4:], [100, 90, 70, 45, 20, 0])


def test_A_buffer_incomplet_et_plancher():
    A = local_amplitude(np.zeros(8), 5)
    assert np.isnan(A[:4]).all() and np.all(A[4:] == 1.0)


def test_premiere_valeur_de_ts():
    ts = trend_strength(np.linspace(1, 50, 50)).ts.to_numpy()
    assert np.isnan(ts[:6]).all() and not np.isnan(ts[6])     # N2 - 1 + R2 - 1 = 6


def test_R1_ne_touche_que_la_courbe_affichee():
    rng = np.random.default_rng(3)
    x1 = np.cumsum(rng.normal(0, 1, 500))
    a, b = trend_strength(x1, OscParams(R1=3)), trend_strength(x1, OscParams(R1=20))
    assert np.array_equal(a.ts.to_numpy(), b.ts.to_numpy(), equal_nan=True)
    assert not np.array_equal(a.ts_plot.to_numpy(), b.ts_plot.to_numpy(), equal_nan=True)


def test_ratio_symetrique_x1_negatif():
    x1 = -np.array([0, 0, 0, 0, 20, 18, 14, 9, 4, 0], dtype=float)
    assert np.allclose(trend_strength(x1).ratio.to_numpy()[4:], [-100, -90, -70, -45, -20, 0])


def test_parametres_oscillateur_hors_bornes():
    import pytest
    for bad in (dict(N2=1), dict(R2=1), dict(R1=0)):
        with pytest.raises(ValueError):
            OscParams(**bad)
