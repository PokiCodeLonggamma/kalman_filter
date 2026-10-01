"""EXP-A01 — anatomie du signal : étiquettes sur séries synthétiques (V, Λ, pause), causalité par troncature, ancres."""
import re

import numpy as np
import pandas as pd
import pytest

from anatomy import DEV_END, build_atlas, load_dev_bars
from anatomy.causal import STORE_COLUMNS, atr_wilder, causal_table, first_extreme
from anatomy.posterior import posterior_table
from config import DATA_RAW, ROOT
from features import build_features

N = 40
ATR = np.full(N, 2.0)


def _frame(close, zone, signals, psl_at, x1, ts=None):
    """Trame minimale au format de `features.build_features`. signals : {barre: sens}, psl_at : {barre: prev_seg_len}."""
    close = np.asarray(close, dtype=float)
    sig, psl = np.zeros(N, dtype=int), np.zeros(N, dtype=int)
    for b, d in signals.items():
        sig[b] = d
    for b, n in psl_at.items():
        psl[b] = n
    f = pd.DataFrame({"close": close, "low": close - 0.5, "high": close + 0.5, "zone": np.asarray(zone, dtype=float),
                      "signal": sig, "prev_seg_len": psl, "x1_bps": np.asarray(x1, dtype=float),
                      "trend_strength": np.full(N, -50.0) if ts is None else ts})
    for c in STORE_COLUMNS:
        f[c] = 0.0
    return f


def _v(d=1):
    """V (Long, d = +1) ou Λ (Short, d = −1) : extremum au close 100 en barre 20 ; signal en 24 après un segment
    qualifiant [14, 23] ; signal opposé précédent en 5, signal suivant en 35 ; x1 prend le sens du signal en 27."""
    i = np.arange(N)
    base = np.where(i <= 20, 120 - i, 100 + (i - 20)).astype(float)
    close = base if d == 1 else 200.0 - base
    zone = np.zeros(N)
    zone[14:24] = -d
    x1 = np.where(i >= 27, d, -d).astype(float)
    ts = np.where((i >= 14) & (i <= 18), -100.0 * d, -50.0 * d)
    return _frame(close, zone, {5: -d, 24: d, 35: -d}, {24: 10}, x1, ts)


# ── Briques ─────────────────────────────────────────────────────────────────────
def test_atr_wilder_amorce_et_rma():
    h = np.array([10.0, 11, 12, 11, 13, 12])
    lo = np.array([9.0, 10, 10, 9, 11, 11])
    c = np.array([9.5, 10.5, 11, 10, 12.5, 11.5])
    tr = [1.0, 1.5, 2.0, 2.0, 3.0, 1.5]
    a = atr_wilder(h, lo, c, n=3)
    assert np.isnan(a[:2]).all()
    assert a[2] == pytest.approx(np.mean(tr[:3]))
    for i in range(3, 6):
        assert a[i] == pytest.approx((a[i - 1] * 2 + tr[i]) / 3)


def test_first_extreme_premiere_occurrence():
    v = np.array([5.0, 3, 4, 3, 6, 6])
    assert first_extreme(v, 0, 5, 1) == 1
    assert first_extreme(v, 2, 5, 1) == 3
    assert first_extreme(v, 0, 5, -1) == 4


def test_aucun_decalage_negatif_dans_le_module_causal():
    src = (ROOT / "src" / "anatomy" / "causal.py").read_text(encoding="utf-8")
    assert not re.search(r"shift\(\s*-", src)


# ── Séries synthétiques ─────────────────────────────────────────────────────────
@pytest.mark.parametrize("d", [1, -1], ids=["V_long", "Lambda_short"])
def test_v_et_lambda(d):
    f = _v(d)
    post = posterior_table(f, np.array([24]), ATR).iloc[0]
    assert post.post_lag_bars == 4 and post.post_dist_atr == pytest.approx(2.25)
    assert not post.post_is_right_censored and post.post_x1_crossed_zero
    assert (post.post_lag_filter_bars, post.post_lag_osc_bars) == (7, -3)
    obs = causal_table(f, np.array([24]), ATR).iloc[0]
    assert obs.obs_lag_seg_bars == 4 and obs.obs_dist_seg_atr == pytest.approx(2.25)
    assert obs.obs_lag_cycle_bars == 4 and obs.obs_dist_cycle_atr == pytest.approx(2.25)
    assert not obs.x1_already_flipped_at_t
    assert obs.saturation == pytest.approx(0.5) and obs.leg_atr == pytest.approx(3.5)
    assert (obs.gap_prev_any_bars, obs.gap_prev_opp_bars) == (19, 19) and np.isnan(obs.gap_prev_same_bars)


def test_pause_de_tendance_sans_passage_a_zero_de_x1():
    """Baisse, pause plate de 4 barres (signal Long en 18), reprise de la baisse jusqu'à la barre 30, remontée."""
    i = np.arange(N)
    close = np.select([i <= 15, i <= 19, i <= 30], [130.0 - i, 115.0, 115.0 - (i - 19)], 104.0 + (i - 30))
    zone = np.zeros(N)
    zone[10:18] = -1
    zone[25:33] = -1
    f = _frame(close, zone, {18: 1, 33: 1}, {18: 8, 33: 8}, np.full(N, -1.0))
    post = posterior_table(f, np.array([18]), ATR).iloc[0]
    assert post.post_lag_bars == 18 - 30 and not post.post_is_right_censored
    assert not post.post_x1_crossed_zero
    assert np.isnan(post.post_lag_filter_bars) and np.isnan(post.post_lag_osc_bars)
    obs = causal_table(f, np.array([18]), ATR).iloc[0]
    assert obs.obs_lag_seg_bars == 3 and obs.obs_dist_seg_atr == pytest.approx(0.25)
    assert not obs.x1_already_flipped_at_t and np.isnan(obs.obs_lag_cycle_bars)


def test_extremum_en_bord_droit_est_censure():
    zone = np.zeros(N)
    zone[10:18] = -1
    f = _frame(130.0 - np.arange(N), zone, {18: 1, 30: 1}, {18: 8}, np.full(N, -1.0))
    post = posterior_table(f, np.array([18]), ATR).iloc[0]
    assert post.post_lag_bars == 18 - 30 and post.post_is_right_censored


def test_x1_deja_du_sens_du_signal_a_l_extremum():
    f = _v(1)
    f["x1_bps"] = np.where(np.arange(N) >= 18, 1.0, -1.0)
    post = posterior_table(f, np.array([24]), ATR).iloc[0]
    assert post.post_x1_crossed_zero and (post.post_lag_filter_bars, post.post_lag_osc_bars) == (0, 4)
    assert causal_table(f, np.array([24]), ATR).iloc[0].x1_already_flipped_at_t


def test_segment_qualifiant_incoherent_leve_une_erreur():
    f = _v(1)
    f.loc[24, "prev_seg_len"] = 9          # le segment [15, 23] serait précédé d'une barre de même zone
    with pytest.raises(ValueError):
        causal_table(f, np.array([24]), ATR)


# ── Données réelles ─────────────────────────────────────────────────────────────
@pytest.mark.data
def test_causalite_par_troncature(df_full):
    """50 coupes juste après une barre de signal : les variables causales ne changent pas quand le futur disparaît."""
    d = df_full.iloc[:15000].reset_index(drop=True)
    f = build_features(d)
    idx = np.flatnonzero((f.signal.to_numpy() != 0) & f.valid_features.to_numpy(dtype=bool))
    full = causal_table(f, idx, atr_wilder(f.high, f.low, f.close))
    for c in np.sort(np.random.default_rng(20260928).choice(idx, size=50, replace=False)):
        fc = build_features(d.iloc[:c + 1].reset_index(drop=True))
        ic = np.flatnonzero((fc.signal.to_numpy() != 0) & fc.valid_features.to_numpy(dtype=bool))
        assert np.array_equal(ic, idx[idx <= c])
        part = causal_table(fc, ic, atr_wilder(fc.high, fc.low, fc.close))
        pd.testing.assert_frame_equal(part, full.iloc[:len(ic)].reset_index(drop=True), check_exact=True,
                                      obj=f"coupe {c}")


@pytest.fixture(scope="module")
def atlas_dev():
    if not DATA_RAW.exists():
        pytest.skip("data/raw/bitstamp_btcusd_30m.csv absent (hors dépôt)")
    return build_atlas(load_dev_bars())[0]


@pytest.mark.data
def test_ancres_7296_signaux_et_6037_flips(atlas_dev):
    assert len(atlas_dev) == 7296
    assert int(atlas_dev.is_flip.sum()) == 6037
    assert (atlas_dev.timestamp < DEV_END).all() and not atlas_dev.is_warmup.any()


@pytest.mark.data
def test_run_rank_1_equivaut_a_is_flip(atlas_dev):
    assert ((atlas_dev.run_rank == 1) == atlas_dev.is_flip).all()


@pytest.mark.data
def test_coherence_des_retards(atlas_dev):
    a = atlas_dev
    past = a.post_lag_bars >= 0
    assert (a.post_lag_bars[past] == a.obs_lag_seg_bars[past]).all()
    c = a.post_x1_crossed_zero
    assert (a.post_lag_filter_bars[c] + a.post_lag_osc_bars[c] == a.post_lag_bars[c]).all()
    assert a.loc[~c, ["post_lag_filter_bars", "post_lag_osc_bars"]].isna().all().all()


@pytest.mark.data
def test_build_atlas_transmet_les_parametres_du_kalman():
    """EXP-D02 : R0 se règle par `KalmanParams` (moteur certifié intouché) ; par défaut, l'atlas est inchangé."""
    if not DATA_RAW.exists():
        pytest.skip("data/raw/bitstamp_btcusd_30m.csv absent (hors dépôt)")
    from indicator import KalmanParams
    df = load_dev_bars().iloc[:12000].reset_index(drop=True)
    ref = build_atlas(df)[0]
    assert build_atlas(df, kalman=KalmanParams())[0].equals(ref)
    assert build_atlas(df, kalman=KalmanParams(R0=100.0))[0].equals(ref)
    reactive = build_atlas(df, kalman=KalmanParams(R0=10.0))[0]
    assert not reactive.bar_index.equals(ref.bar_index)   # R0 transmis : les signaux changent (sens non monotone)
