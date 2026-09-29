"""EXP-C04 — tendance de contexte : EMA et Kalman v2.1 sur bougies 4 h. Égalité à un calcul direct, cohérence avec
l'agrégation 1 h certifiée (D32), lecture d'une bougie seulement une fois close, causalité par troncature, veto."""
import numpy as np
import pandas as pd

from context import counter_trend, ema, ema_trend, htf_bars, htf_kalman_trend
from features import aggregate_1h, features_1h
from indicator import KalmanParams, run_kalman


def _marche(n, seed, start="2024-01-01"):
    c = 30000 * np.exp(np.cumsum(np.random.default_rng(seed).normal(0, 0.004, n)))
    return pd.DataFrame({"time": pd.date_range(start, periods=n, freq="30min", tz="UTC"), "open": np.r_[c[0], c[:-1]],
                         "high": c * 1.001, "low": c * 0.999, "close": c})


def test_ema_et_tendance_egales_a_la_recurrence_directe():
    c = _marche(3000, 1).close.to_numpy()
    for span in (50, 200):
        a, ref = 2.0 / (span + 1), np.empty(len(c))
        ref[0] = c[0]
        for i in range(1, len(c)):
            ref[i] = a * c[i] + (1 - a) * ref[i - 1]
        np.testing.assert_allclose(ema(c, span), ref, rtol=1e-12)
        np.testing.assert_array_equal(ema_trend(c, span), np.where(c > ref, 1, -1))


def test_bougies_1h_identiques_a_l_agregation_certifiee():
    b = _marche(2000, 2)
    h, ref = htf_bars(b, 1), aggregate_1h(b)
    for c in ("open", "high", "low", "close", "n_bars"):
        np.testing.assert_array_equal(h[c].to_numpy(), ref[c].to_numpy())
    np.testing.assert_array_equal(h.close_time.to_numpy(), ref.close_time_1h.to_numpy())
    k = htf_kalman_trend(b, hours=1, warmup=300)
    f = features_1h(b)
    np.testing.assert_array_equal(k.x1_htf.to_numpy(), f.x1_1h.to_numpy())      # même jonction causale que D32
    np.testing.assert_array_equal(k.valid.to_numpy(), f.valid_1h.to_numpy())


def test_bougie_4h_lue_seulement_une_fois_close():
    b = _marche(400, 3)
    k, h = htf_kalman_trend(b, hours=4, warmup=0), htf_bars(b, 4)
    x1 = run_kalman(h.close.to_numpy(), KalmanParams()).x1.to_numpy()        # moteur de parité, aucune réécriture
    close_t = pd.to_datetime(b.time) + pd.Timedelta(minutes=30)
    for i in range(len(b)):
        j = np.flatnonzero((h.close_time <= close_t.iloc[i]).to_numpy())
        if len(j):
            assert k.x1_htf.iat[i] == x1[j[-1]] and k.n_htf_closed.iat[i] == j[-1] + 1
        else:
            assert np.isnan(k.x1_htf.iat[i]) and k.trend.iat[i] == 0
    assert (k.n_htf_closed.to_numpy()[7::8] == np.arange(1, len(b) // 8 + 1)).all()   # 8e barre : sa bougie est close
    assert (k.n_htf_closed.to_numpy()[6::8] == np.arange(0, len(b) // 8)).all()       # 7e barre : pas encore


def test_tendances_causales_par_troncature():
    b = _marche(3200, 4)
    e200, e50 = ema_trend(b.close, 200), ema_trend(b.close, 50)
    k = htf_kalman_trend(b, hours=4, warmup=100)
    for t in np.random.default_rng(5).choice(np.arange(10, len(b)), 60, replace=False):
        cut = b.iloc[:t + 1]
        assert ema_trend(cut.close, 200)[-1] == e200[t] and ema_trend(cut.close, 50)[-1] == e50[t]
        kc = htf_kalman_trend(cut, hours=4, warmup=100)
        assert kc.trend.iat[-1] == k.trend.iat[t] and kc.n_htf_closed.iat[-1] == k.n_htf_closed.iat[t]
        assert (np.isnan(kc.x1_htf.iat[-1]) and np.isnan(k.x1_htf.iat[t])) or kc.x1_htf.iat[-1] == k.x1_htf.iat[t]


def test_warm_up_et_veto_contre_tendance():
    b = _marche(3000, 6)
    k = htf_kalman_trend(b, hours=4)                                          # 300 bougies 4 h = 2 400 barres
    assert (k.trend.to_numpy()[k.n_htf_closed.to_numpy() < 300] == 0).all()
    assert set(np.unique(k.trend.to_numpy()[k.valid.to_numpy()])) <= {-1, 1} and k.valid.any()
    side, trend = np.array([1, 1, -1, -1, 1, -1]), np.array([1, -1, 1, -1, 0, 0])
    np.testing.assert_array_equal(counter_trend(side, trend), [False, True, True, False, False, False])
