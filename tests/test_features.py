"""Feature Store ML1 (P4 étape 1) : définitions, univers événementiel, alignement, invariances, non-régression.

Causalité et fuite : tests/test_no_leakage.py. Multi-TF 1 h : tests/test_multi_tf.py.
"""
import numpy as np
import pandas as pd
import pytest

from config import FEATURES_CSV, ROOT, SATURATION_TH, WARMUP_BARS, WARMUP_BARS_1H
from features import (ACTIVE_OUT_OF_TOP12, ALIGNED_FEATURES, EVENT_META_COLUMNS, FEATURE_COLUMNS,
                      FEATURE_GROUPS, SECONDARY, SIGNED, TOP12, bars_since_last_direct_jump, build_events,
                      build_features, prev_seg_peak_abs_x1, rolling_autocorr1, rolling_z, vol_bps)

P3_CSV = ROOT / "data" / "processed" / "kalman_features.csv"


def _sinus(n=1200, period=40, amp=500, level=30000.0):
    c = level + amp * np.sin(2 * np.pi * np.arange(n) / period)
    return pd.DataFrame({"time": pd.date_range("2024-01-01", periods=n, freq="30min", tz="UTC"),
                         "open": np.r_[c[0], c[:-1]], "high": c + 1, "low": c - 1, "close": c})


def _repetitions(n=2400, poussee=20, pause=10, bloc=25):
    """Tendances entrecoupées de pauses : produit des signaux répétés de même sens (ignorés par la baseline)."""
    c, sens, k = [30000.0], -1, 0
    while len(c) < n:
        k += 1
        if k % bloc == 0:
            sens = -sens
        c += [c[-1] * (1 + sens * 0.002) ** (i + 1) for i in range(poussee)]
        c += [c[-1]] * pause
    c = np.array(c[:n])
    return pd.DataFrame({"time": pd.date_range("2024-01-01", periods=n, freq="30min", tz="UTC"),
                         "open": np.r_[c[0], c[:-1]], "high": c * 1.001, "low": c * 0.999, "close": c})


# ── Briques élémentaires ────────────────────────────────────────────────────────
def test_vol_bps_reporte_le_passe_jamais_le_futur():
    """Barres plates : la volatilité nulle est remplacée par la dernière valeur PASSÉE (ffill, D33)."""
    c = np.r_[np.linspace(100.0, 110.0, 60), np.full(30, 110.0), np.linspace(110.0, 130.0, 60)]
    v = vol_bps(c, lookback=20)
    plateau = slice(80, 90)                                  # 20 barres après le début du plat : vol = 0
    assert np.isnan(v[:20]).all() and not np.isnan(v[20:]).any()
    assert np.allclose(v[plateau], v[79])                    # valeur figée d'avant le plat
    assert not np.isclose(v[85], v[120])                     # un bfill aurait recopié la valeur d'après


def test_vol_bps_refuse_un_lookback_degenere():
    with pytest.raises(ValueError):
        vol_bps(np.arange(10.0), lookback=1)


def test_rolling_z_fenetre_causale():
    x = np.arange(300.0) ** 1.5
    z = rolling_z(x, 100)
    assert np.isnan(z[:99]).all()
    w = x[100:200]
    assert z[199] == pytest.approx((x[199] - w.mean()) / w.std(ddof=0))


def test_rolling_autocorr1_est_une_correlation_lag1():
    rng = np.random.default_rng(0)
    z = rng.normal(size=500).cumsum() / 10
    a = rolling_autocorr1(z, 48)
    assert np.isnan(a[:48]).all() and not np.isnan(a[48:]).any()
    assert np.nanmax(np.abs(a)) <= 1.0                       # borne stricte : l'ancienne formule dépassait 1
    w, wl = z[200 - 47:201], z[200 - 48:200]
    assert a[200] == pytest.approx(np.corrcoef(w, wl)[0, 1])


def test_prev_seg_peak_suit_le_segment_quitte():
    zone = np.array([np.nan, 1, 1, 1, 0, 0, -1, -1, 0])
    x1 = np.array([9.0, 1, 5, 2, 0.5, 0.1, -7, -3, 0.2])
    peak = prev_seg_peak_abs_x1(zone, x1)
    assert peak[3] == 0.0                                    # aucun segment quitté encore archivé
    assert peak[4] == 5.0 and peak[5] == 5.0                 # pic du segment vert
    assert peak[6] == 0.5                                    # pic du segment neutre quitté
    assert peak[8] == 7.0                                    # pic du segment rouge quitté


def test_log_R_rel_indefinie_si_R_nul():
    from features import log_R_rel
    v = log_R_rel(np.array([100.0, 50.0, 0.0]), 100.0)
    assert v[0] == 0.0 and v[1] == pytest.approx(np.log(0.5)) and np.isnan(v[2])


def test_bars_since_last_direct_jump_censure_a_gauche():
    zone = np.array([0, 1, 1, -1, -1, 0, 1])                 # saut direct vert -> rouge à l'indice 3
    b = bars_since_last_direct_jump(zone)
    assert np.isnan(b[:3]).all()
    assert list(b[3:]) == [0.0, 1.0, 2.0, 3.0]


# ── Schéma du store ─────────────────────────────────────────────────────────────
def test_top12_gele_et_groupes_disjoints():
    assert TOP12 == ["trend_strength", "x1_bps", "x1_1h_bps", "macro_align_1h", "innov_rel", "nis_z_100",
                     "peak_bps_vol", "A_vol", "prev_seg_len", "n_short_seg_48",
                     "bars_since_last_direct_jump", "is_saturated"]
    assert ACTIVE_OUT_OF_TOP12 == ["log_R_rel"]
    assert set(SECONDARY) == {"dist_k_bps", "dx1_bps", "n_zone_changes_48", "innov_autocorr_48",
                              "prev_seg_extreme_abs", "A_close"}
    assert len(FEATURE_COLUMNS) == len(set(FEATURE_COLUMNS)) == 19
    assert set(FEATURE_GROUPS) == {"top12", "active_hors_top12", "secondaire"}
    assert set(SIGNED) <= set(FEATURE_COLUMNS) and ALIGNED_FEATURES == [f"{c}_al" for c in SIGNED]


def test_colonnes_par_barre_et_par_evenement():
    f = build_features(_sinus())
    ev = build_events(f)
    assert "macro_align_1h" not in f.columns and "sign_x1_1h" in f.columns   # la direction n'existe qu'au signal
    assert set(FEATURE_COLUMNS) - {"macro_align_1h"} <= set(f.columns)
    assert list(ev.columns) == EVENT_META_COLUMNS + FEATURE_COLUMNS + ALIGNED_FEATURES
    assert not ({"fill", "fill_px", "position"} & set(f.columns))            # aucune colonne ex post (D25)
    assert not ({"fill", "fill_px", "position"} & set(ev.columns))


def test_is_saturated_applique_le_seuil():
    f = build_features(_sinus(), warmup_bars_1h=0)
    ext = f.prev_seg_extreme_abs.to_numpy()
    assert np.array_equal(f.is_saturated.to_numpy(), (ext >= SATURATION_TH).astype(float))


# ── Univers événementiel (Q-G option A, D28) ───────────────────────────────────
def test_univers_option_A_tous_les_signaux_bruts():
    f = build_features(_repetitions(), warmup_bars=WARMUP_BARS, warmup_bars_1h=0)
    ev = build_events(f)
    attendu = f[(f.signal != 0) & f.valid_features & (f.bar_index + 1 <= len(f) - 1)]
    assert len(ev) == len(attendu) > 0
    assert ev.baseline_ignored.any()                                  # les ignorés font partie de l'univers
    assert np.array_equal(ev.run_rank.eq(1).to_numpy(), ev.baseline_decision.to_numpy())
    assert np.array_equal(ev.entry_bar.to_numpy(), ev.bar_index.to_numpy() + 1)
    assert (ev.entry_time.to_numpy() == f.time.to_numpy()[ev.entry_bar.to_numpy()]).all()


def test_signal_sur_la_derniere_barre_exclu():
    f = build_features(_repetitions(), warmup_bars_1h=0)
    last = int(np.flatnonzero((f.signal != 0) & f.valid_features)[-1])
    tronque = f.iloc[:last + 1].copy()
    assert build_events(tronque).bar_index.max() < last               # pas de barre d'entrée t+1


def test_alignement_sur_la_direction():
    ev = build_events(build_features(_repetitions(), warmup_bars_1h=0))
    side = ev.side.to_numpy()
    for c in SIGNED:
        assert np.allclose(ev[f"{c}_al"].to_numpy(), ev[c].to_numpy() * side, equal_nan=True)
    assert np.array_equal(ev.macro_align_1h.to_numpy(), side * np.sign(ev.x1_1h_bps.to_numpy()))
    assert not [c for c in ev.columns if c.endswith("_al") and c[:-3] not in SIGNED]


# ── Invariances ────────────────────────────────────────────────────────────────
@pytest.mark.parametrize("k", [0.001, 1000.0])
def test_invariance_d_echelle_des_features(k):
    df = _sinus()
    a = build_features(df, warmup_bars_1h=0)
    d = df.copy()
    d[["open", "high", "low", "close"]] *= k
    b = build_features(d, warmup_bars_1h=0)
    assert np.array_equal(a.signal.to_numpy(), b.signal.to_numpy())
    for c in [*FEATURE_COLUMNS, "vol_bps"]:
        if c == "macro_align_1h":
            continue
        x, y = a[c].to_numpy(dtype=float), b[c].to_numpy(dtype=float)
        assert np.allclose(x, y, rtol=1e-9, atol=1e-9, equal_nan=True), c


def test_decalage_additif_non_neutre_sur_les_features(recwarn):
    """Verrou de la règle Q-E : un back-adjustment ADDITIF laisse le signal intact mais fausse les features
    rapportées au close. Seul un ajustement multiplicatif est admissible."""
    df = _sinus()
    a = build_features(df, warmup_bars_1h=0)
    d = df.copy()
    d[["open", "high", "low", "close"]] += 20000.0
    b = build_features(d, warmup_bars_1h=0)
    assert np.array_equal(a.signal.to_numpy(), b.signal.to_numpy())
    assert np.allclose(a.trend_strength.to_numpy(), b.trend_strength.to_numpy(), atol=1e-8, equal_nan=True)
    assert np.allclose(a.log_R_rel.to_numpy(), b.log_R_rel.to_numpy(), atol=1e-8, equal_nan=True)
    for c in ["x1_bps", "innov_rel", "dist_k_bps", "A_close", "vol_bps"]:
        x, y = a[c].to_numpy(), b[c].to_numpy()
        m = ~np.isnan(x) & ~np.isnan(y)
        assert np.nanmax(np.abs(x[m] - y[m])) > 1e-6, c


def test_build_features_est_deterministe():
    df = _sinus()
    pd.testing.assert_frame_equal(build_features(df), build_features(df), check_exact=True)


# ── Données réelles ─────────────────────────────────────────────────────────────
@pytest.mark.data
def test_masques_de_warmup(features_full):
    f = features_full
    assert not f.valid.iloc[:WARMUP_BARS].any() and f.valid.iloc[WARMUP_BARS:].all()
    assert np.array_equal(f.valid_1h.to_numpy(), f.n_1h_closed.to_numpy() >= WARMUP_BARS_1H)
    premiere = int(np.flatnonzero(f.valid_1h.to_numpy())[0])
    assert f.n_1h_closed.iat[premiere] == WARMUP_BARS_1H
    assert np.array_equal(f.valid_features.to_numpy(), (f.valid & f.valid_1h).to_numpy())


@pytest.mark.data
def test_univers_reel_et_sous_ensemble_baseline(events_full, features_full):
    ev, f = events_full, features_full
    bruts = int(((f.signal != 0) & f.valid_features).sum())
    assert len(ev) == bruts                                            # aucun signal valide perdu
    assert np.array_equal(ev.run_rank.eq(1).to_numpy(), ev.baseline_decision.to_numpy())
    assert int(ev.baseline_decision.sum()) < len(ev)                   # les ignorés sont bien inclus
    assert ev.side.isin([-1, 1]).all() and ev.time.is_monotonic_increasing


@pytest.mark.data
def test_non_regression_contre_le_dataset_p3(events_full):
    """Toutes les colonnes non corrigées reproduisent le CSV P3 aux erreurs d'arrondi ; seule
    innov_autocorr_48 change (redéfinition D33), et les 15 événements écartés par le warm-up 1 h manquent."""
    if not P3_CSV.exists():
        pytest.skip("data/processed/kalman_features.csv (P3) absent")
    p3 = pd.read_csv(P3_CSV, parse_dates=["time"])
    dec = events_full[events_full.baseline_decision]
    j = p3.merge(dec, on="time", suffixes=("_p3", "_v2"), validate="1:1")
    assert len(j) == len(dec) and len(p3) - len(j) == 15
    for c in [c for c in TOP12 + ["dist_k_bps", "dx1_bps", "n_zone_changes_48"] if c in p3.columns]:
        d = np.abs(j[f"{c}_p3"].to_numpy() - j[f"{c}_v2"].to_numpy())
        assert np.nanmax(d) < 1e-9, c
    d_ac = np.abs(j.innov_autocorr_48_p3.to_numpy() - j.innov_autocorr_48_v2.to_numpy())
    assert np.nanmax(d_ac) > 1e-3                                      # ancienne formule ≠ corrélation lag 1
    assert np.nanmax(np.abs(j.innov_autocorr_48_v2.to_numpy())) <= 1.0


@pytest.mark.data
def test_export_csv_si_present():
    """Le dataset exporté par experiments/p3/build_features.py, s'il existe, a le schéma attendu."""
    if not FEATURES_CSV.exists():
        pytest.skip("kalman_features_v2.csv non généré")
    ev = pd.read_csv(FEATURES_CSV, parse_dates=["time", "entry_time"])
    assert list(ev.columns) == EVENT_META_COLUMNS + FEATURE_COLUMNS + ALIGNED_FEATURES
    assert ev.asset.nunique() == 1 and len(ev) > 8000
