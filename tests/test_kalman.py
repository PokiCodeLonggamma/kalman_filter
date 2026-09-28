"""Tests unitaires du filtre (données synthétiques, rapides)."""
import numpy as np
import pytest

from indicator.kalman import KalmanParams, adaptive_R, run_kalman


@pytest.fixture(scope="module")
def walk():
    rng = np.random.default_rng(7)
    return 30000 + np.cumsum(rng.normal(0, 60, 3000))


def test_premiere_barre_etat_initial(walk):
    k = run_kalman(walk)
    assert k.x0.iat[0] == walk[0] and k.x1.iat[0] == 0.0 and k.innov.iat[0] == 0.0


def test_reset_de_P_diag_a_chaque_barre(walk):
    """E1 : P00 = P11 = 1 avant la prédiction -> P⁻11 = 1 + Q11 à chaque barre."""
    k = run_kalman(walk)
    assert np.allclose(k.Ppred11, 1.01, rtol=0, atol=1e-15)


def test_sans_reset_le_filtre_est_un_autre_filtre(walk):
    on = run_kalman(walk, KalmanParams(gamma=0.0))
    off = run_kalman(walk, KalmanParams(gamma=0.0, reset_P_diag=False))
    assert on.K1.iat[-1] == pytest.approx(0.0659, abs=5e-4)     # mission 2, R constant
    assert off.K1.iat[-1] == pytest.approx(0.0093, abs=5e-4)
    assert (off.Ppred00 * off.Ppred11 - off.Ppred01 ** 2).iloc[100:].min() > 0   # covariance valide sans reset


def test_R_vaut_R0_tant_que_la_sma_de_vol_n_existe_pas(walk):
    R = adaptive_R(walk)
    first = 20 - 1 + 100 - 1                                     # 1re SMA100 de stdev20
    assert np.all(R[:first] == 100.0) and not np.all(R[first:] == 100.0)
    assert np.all(adaptive_R(walk, KalmanParams(gamma=0.0)) == 100.0)


def test_gains_independants_du_niveau_de_prix(walk):
    """Invariance d'échelle (P0, mission 1) : K ne dépend que du ratio de vol sans dimension."""
    a, b = run_kalman(walk), run_kalman(walk * 1000.0)
    assert np.allclose(a.K0, b.K0, rtol=1e-9) and np.allclose(a.K1, b.K1, rtol=1e-9)
    assert np.allclose(b.x1, a.x1 * 1000.0, rtol=1e-6)


def test_Q_hors_diagonale_premiere_barre(walk):
    """P initial = I, Q = [[0.01, 1e-4], [1e-4, 0.01]] -> P⁻ = F I Fᵀ + Q à la 1re barre."""
    k = run_kalman(walk[:10])
    assert (k.Ppred00.iat[0], k.Ppred01.iat[0], k.Ppred11.iat[0]) == (2.01, 1.0001, 1.01)


def test_R_de_la_boucle_est_R_adaptatif_de_la_meme_barre(walk):
    k = run_kalman(walk)
    assert np.array_equal(k.R.to_numpy(), adaptive_R(walk))
    assert np.allclose(k.S, k.Ppred00 + k.R, rtol=0, atol=1e-9)


@pytest.mark.parametrize("bad", [dict(R0=0.5), dict(q1=0.0), dict(q_scale=0.0), dict(gamma=-0.1), dict(gamma=3.5),
                                 dict(vol_lookback=4), dict(vol_lookback=20.5)])
def test_parametres_hors_bornes_du_pine(bad):
    with pytest.raises(ValueError):
        KalmanParams(**bad)
