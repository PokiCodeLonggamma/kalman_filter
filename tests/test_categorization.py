"""EXP-B01 — excursions depuis open[t+1], barrières de premier passage, descripteurs dérivés, familles."""
import numpy as np
import pandas as pd
import pytest

from anatomy.causal import atr_wilder, causal_table
from categorization import (BARRIERS, HORIZONS, add_derived, assign_families, barrier_key, barrier_table,
                            bin_descriptor, cluster_bootstrap, excursion_table, summarize, tail_sum, timing_drift)
from features import build_features

# ── Série synthétique : signal en t = 2, entrée open[3] = 101 (écart avec close[2] = 100), ATR14(t) = 2 ──────
#            open   high   low    close
BARS = [(100.0, 100.5, 99.5, 100.0),
        (100.0, 100.5, 99.5, 100.0),
        (100.0, 100.5, 99.5, 100.0),     # t = 2 : barre du signal
        (101.0, 102.0, 100.5, 101.5),    # t+1 : entrée à l'open
        (101.5, 101.5, 99.0, 100.0),     # plus bas de la fenêtre H = 6
        (100.0, 104.0, 100.0, 103.0),    # plus haut de la fenêtre H = 6
        (103.0, 103.5, 102.0, 102.5),
        (102.5, 103.0, 101.5, 102.0),
        (102.0, 102.5, 101.5, 102.0),    # t+6 : close = 102
        (102.0, 102.5, 101.5, 102.0),
        (102.0, 102.5, 101.5, 102.0),
        (102.0, 102.5, 101.5, 102.0)]
O, H_, L, C = (np.array(c) for c in zip(*BARS))
ATR = np.full(len(C), 2.0)


def _flat(n=60, wick_at=None):
    o = np.full(n, 100.0)
    h, lo = o + 0.5, o - 0.5
    if wick_at is not None:
        h[wick_at], lo[wick_at] = 110.0, 90.0
    return o, h, lo, o.copy()


# ── Excursions ──────────────────────────────────────────────────────────────────
def test_excursions_long_depuis_open_t_plus_1():
    e = excursion_table(O, H_, L, C, [2], [1], ATR).iloc[0]
    assert e.entry_price == 101.0
    assert (e.mfe_6_atr, e.mae_6_atr, e.ret_6_atr, e.asym_6_atr, e.mfe_gt_mae_6) == (1.5, 1.0, 0.5, 0.5, 1.0)
    assert np.isnan(e.mfe_13_atr) and np.isnan(e.mfe_gt_mae_13)          # t + 13 hors échantillon


def test_excursions_short_miroir():
    e = excursion_table(O, H_, L, C, [2], [-1], ATR).iloc[0]
    assert (e.mfe_6_atr, e.mae_6_atr, e.ret_6_atr, e.asym_6_atr, e.mfe_gt_mae_6) == (1.0, 1.5, -0.5, -0.5, 0.0)


# ── Barrières ───────────────────────────────────────────────────────────────────
def test_barrieres_long_et_short():
    lg = barrier_table(O, H_, L, [2], [1], ATR).iloc[0]
    sh = barrier_table(O, H_, L, [2], [-1], ATR).iloc[0]
    assert (lg.barrier_1p0_outcome, lg.barrier_1p0_bars) == ("loss", 2)     # plus bas 99 = 101 − 2 en t+2
    assert (sh.barrier_1p0_outcome, sh.barrier_1p0_bars) == ("win", 2)
    assert (lg.barrier_1p5_outcome, lg.barrier_1p5_bars) == ("win", 3)      # plus haut 104 = 101 + 3 en t+3
    assert (sh.barrier_1p5_outcome, sh.barrier_1p5_bars) == ("loss", 3)
    assert lg.barrier_2p0_outcome == "censored" and np.isnan(lg.barrier_2p0_bars)   # fin d'échantillon avant t+48


def test_meche_touchant_les_deux_barrieres_est_ambigue():
    o, h, lo, c = _flat(wick_at=4)
    for d in (1, -1):
        r = barrier_table(o, h, lo, [2], [d], np.full(60, 2.0), barriers=(1.0,)).iloc[0]
        assert (r.barrier_1p0_outcome, r.barrier_1p0_bars) == ("ambiguous", 2)


def test_timeout_si_aucune_barriere_a_t_plus_48():
    o, h, lo, c = _flat()
    r = barrier_table(o, h, lo, [2], [1], np.full(60, 2.0), barriers=(1.0,)).iloc[0]
    assert r.barrier_1p0_outcome == "timeout"


# ── Résumés, découpages, familles ──────────────────────────────────────────────
def test_taux_strict_exclut_les_timeouts_et_compte_l_ambiguite_en_echec():
    n = 4
    ex = pd.DataFrame({f"{k}_{H}_atr": np.ones(n) for H in HORIZONS for k in ("mfe", "mae", "ret", "asym")})
    for H in HORIZONS:
        ex[f"mfe_gt_mae_{H}"] = [1.0, 0.0, 1.0, 0.0]
    for b in BARRIERS:
        ex[f"barrier_{barrier_key(b)}_outcome"] = ["win", "loss", "ambiguous", "timeout"]
    s = summarize(ex, np.ones(n, dtype=bool))
    assert s["win_strict_1p5"] == pytest.approx(1 / 3) and s["win_all_1p5"] == pytest.approx(1 / 4)
    assert s["amb_1p5"] == pytest.approx(1 / 4) and s["timeout_1p5"] == pytest.approx(1 / 4)
    assert s["pct_mfe_gt_mae_26"] == pytest.approx(0.5)


def test_quartiles_et_modalites():
    lab, order, _ = bin_descriptor(pd.Series(np.arange(100.0)), "A_vol")
    assert order == ["Q1", "Q2", "Q3", "Q4"] and all((lab == q).sum() == 25 for q in order)
    lab, order, _ = bin_descriptor(pd.Series([1, 2, 1, 3]), "run_rank")
    assert order == ["1", ">1"] and list(lab) == ["1", ">1", "1", ">1"]
    lab, _, _ = bin_descriptor(pd.Series([0.0, 0.2, 0.0]), "cycle_seg_div_atr")
    assert list(lab) == ["0", ">0", "0"]


def test_familles_partition_exclusive_et_exhaustive():
    d = pd.DataFrame({"retrace_ratio": [0.3, 0.6, 0.6, 0.9, 1.2, 0.3, 0.9],
                      "leg_atr":       [4.0, 4.0, 2.0, 2.0, 2.0, 2.0, 4.0]})
    assert list(assign_families(d, leg_p50=2.82)) == ["F1", "F2a", "F2b", "F3", "F3", "F5", "F4"]


# ── Relecture : timing / dérive, queues, bootstrap de grappes ───────────────────
def test_timing_derive_mediane_et_moyenne():
    # Long : médiane 0, moyenne 1 (queue droite) ; Short : médiane 0, moyenne 0 (NaN ignoré)
    ret = np.array([0.0, 0.0, 3.0, -1.0, 1.0, np.nan])
    dirn = np.array([1, 1, 1, -1, -1, -1])
    assert timing_drift(ret, dirn, "median") == (0.0, 0.0)
    assert timing_drift(ret, dirn, "mean") == pytest.approx((0.5, 0.5))
    # Même définition que l'annexe H : ΔL, ΔS = variation médiane du prix (non orientée) après les Long, les Short
    ret2 = np.array([1.0, 2.0, 4.0, 0.5, -3.0, 2.0])
    d_l, d_s = np.median(ret2[:3]), np.median(-ret2[3:])
    assert timing_drift(ret2, dirn) == pytest.approx(((d_l - d_s) / 2, (d_l + d_s) / 2))
    assert np.isnan(timing_drift(ret[:3], dirn[:3])[0])


def test_somme_des_queues():
    v = np.arange(-10.0, 11.0)
    assert tail_sum(v) == pytest.approx(0.0)
    assert tail_sum(np.r_[v, 50.0, 60.0, 70.0]) > 0 > tail_sum(np.r_[v, -50.0, -60.0, -70.0])
    assert np.isnan(tail_sum([np.nan]))


def test_bootstrap_tire_des_grappes_entieres():
    clusters = np.array([0, 0, 1, 1, 2, 2])
    values = np.array([1.0, 1.0, 5.0, 5.0, 9.0, 9.0])

    def stat(ii):
        return [values[ii].mean(), len(ii)]

    draws = cluster_bootstrap(stat, clusters, n_boot=200, seed=1)
    assert draws.shape == (200, 2) and set(draws[:, 1]) == {6}
    # chaque tirage réunit 3 grappes entières : la somme vaut 3, 7, …, 27 (valeurs de grappe 1, 5 ou 9)
    assert np.isin(np.round(3 * draws[:, 0]), np.arange(3, 28, 4)).all()
    assert np.array_equal(draws, cluster_bootstrap(stat, clusters, n_boot=200, seed=1))


# ── Données réelles ─────────────────────────────────────────────────────────────
@pytest.mark.data
def test_descripteurs_derives_causaux_par_troncature(df_full):
    """20 coupes juste après une barre de signal : retrace_ratio, cycle_seg_div_atr, decel_ratio inchangés."""
    cols = ["retrace_ratio", "cycle_seg_div_atr", "decel_ratio"]
    d = df_full.iloc[:15000].reset_index(drop=True)
    f = build_features(d)
    idx = np.flatnonzero((f.signal.to_numpy() != 0) & f.valid_features.to_numpy(dtype=bool))
    full = add_derived(causal_table(f, idx, atr_wilder(f.high, f.low, f.close)))[cols]
    for c in np.sort(np.random.default_rng(20260929).choice(idx, size=20, replace=False)):
        fc = build_features(d.iloc[:c + 1].reset_index(drop=True))
        ic = np.flatnonzero((fc.signal.to_numpy() != 0) & fc.valid_features.to_numpy(dtype=bool))
        part = add_derived(causal_table(fc, ic, atr_wilder(fc.high, fc.low, fc.close)))[cols]
        pd.testing.assert_frame_equal(part, full.iloc[:len(ic)].reset_index(drop=True), check_exact=True,
                                      obj=f"coupe {c}")
