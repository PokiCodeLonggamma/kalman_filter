"""EXP-D03 — mesures de compression lues à la clôture de chaque barre, sans lookahead (`context.volatility`) :
bandes de Bollinger (moyenne mobile simple, écart-type de population comme TradingView), quantile et rang glissants
sur une fenêtre de temps fermée à droite, indéfinis tant que l'historique ne couvre pas la durée minimale."""
import numpy as np
import pandas as pd

from context.volatility import bollinger, trailing_quantile, trailing_rank


def test_bollinger_definition():
    close = np.array([10.0, 11.0, 12.0, 11.0, 13.0, 14.0, 12.0, 15.0])
    pctb, bw = bollinger(close, n=4, k=2.0)
    assert np.isnan(pctb[:3]).all() and np.isnan(bw[:3]).all()
    for i in range(3, len(close)):
        w = close[i - 3:i + 1]
        m, sd = w.mean(), w.std(ddof=0)
        lo, hi = m - 2.0 * sd, m + 2.0 * sd
        assert np.isclose(pctb[i], (close[i] - lo) / (hi - lo), rtol=1e-12)
        assert np.isclose(bw[i], (hi - lo) / m, rtol=1e-12)


def test_bollinger_ne_lit_aucune_cloture_future():
    rng = np.random.default_rng(0)
    close = 100.0 * np.exp(np.cumsum(rng.normal(0, 0.01, 300)))
    pctb, bw = bollinger(close)
    other = close.copy()
    other[200:] *= 1.5
    p2, b2 = bollinger(other)
    assert np.array_equal(pctb[:200], p2[:200], equal_nan=True) and np.array_equal(bw[:200], b2[:200], equal_nan=True)


def test_bollinger_serie_plate_sans_largeur():
    pctb, bw = bollinger(np.full(30, 5.0))
    assert np.isnan(pctb[19:]).all() and (bw[19:] == 0.0).all()


def _serie(n=3000, seed=1):
    rng = np.random.default_rng(seed)
    times = pd.date_range("2021-01-01", periods=n, freq="30min", tz="UTC")
    return times, rng.lognormal(3.5, 0.4, n)


def test_quantile_glissant_egal_au_quantile_de_la_fenetre():
    times, v = _serie()
    q = trailing_quantile(times, v, 0.6, window="10D", min_span="9D")
    for i in (500, 1200, 2999):
        sel = (times > times[i] - pd.Timedelta("10D")) & (times <= times[i])
        assert np.isclose(q[i], np.quantile(v[sel], 0.6), rtol=1e-12)
    assert np.isnan(q[times - times[0] < pd.Timedelta("9D")]).all()
    assert np.isfinite(q[times - times[0] >= pd.Timedelta("9D")]).all()


def test_rang_glissant_part_des_valeurs_inferieures_ou_egales():
    times, v = _serie(seed=2)
    r = trailing_rank(times, v, window="10D", min_span="9D")
    for i in (600, 2500):
        sel = (times > times[i] - pd.Timedelta("10D")) & (times <= times[i])
        assert np.isclose(r[i], np.mean(v[sel] <= v[i]), rtol=1e-12)
    assert np.isnan(r[times - times[0] < pd.Timedelta("9D")]).all()


def test_quantile_et_rang_glissants_causaux():
    times, v = _serie(seed=3)
    q, r = trailing_quantile(times, v, 0.6, window="10D", min_span="9D"), trailing_rank(times, v, "10D", "9D")
    w = v.copy()
    w[2000:] *= 3.0
    assert np.array_equal(q[:2000], trailing_quantile(times, w, 0.6, "10D", "9D")[:2000], equal_nan=True)
    assert np.array_equal(r[:2000], trailing_rank(times, w, "10D", "9D")[:2000], equal_nan=True)
