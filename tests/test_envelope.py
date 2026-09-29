"""EXP-C01 — enveloppe séquentielle : sortie à horizon fixe, pyramiding 0, frais, continuation, réserve 2026, causalité
par troncature, métriques ; ancre P6.5d (sans stop et stop 2,5 %) reproduite sur BTC.
EXP-C02 — stop-loss en prix : SL-A (k · ATR14(t)) et SL-B (extremum du segment qualifiant), mèche et gap, entrées
figées contre séquentiel dynamique, causalité des niveaux, IC en bps et en ATR, effet apparié."""
import json

import numpy as np
import pandas as pd
import pytest

from categorization import cluster_bootstrap, timing_drift
from config import DATA_RAW, ROOT
from envelope import (atr_stop_levels, by_year, dev_signals, effect_ci, equity_curve_sized, mean_ci, risk_weights,
                      segment_extremum, stop_trades, structural_stop_levels, summarize, summarize_sized,
                      time_stop_trades)
from estimand.stoploss import apply_stop, equity_curve, simulate_strategy

T0 = pd.Timestamp("2021-01-01", tz="UTC")
HOLDOUT = pd.Timestamp("2026-01-01", tz="UTC")


def _bars(o, t0=T0):
    o = np.asarray(o, float)
    return pd.DataFrame({"time": t0 + pd.to_timedelta(np.arange(len(o)) * 30, unit="min"), "open": o,
                         "high": o + 0.5, "low": o - 0.5, "close": o})


def _marche(n, seed):
    return _bars(100 * np.exp(np.cumsum(np.random.default_rng(seed).normal(0, 0.01, n))))


def _atr(n, v=50.0):
    return pd.Series(v, index=np.arange(n))


# ── Règle de sortie et pyramiding 0 ─────────────────────────────────────────────
def test_sortie_a_horizon_fixe_et_signaux_ignores_en_position():
    b = _bars(np.linspace(100, 110, 60))
    tr = time_stop_trades(b, [5, 8, 12, 20, 21, 40], [1, 1, -1, -1, 1, -1], horizon=6)
    assert tr[["entry_bar", "exit_bar", "side", "signal_bar"]].values.tolist() == [
        [6, 12, 1, 5], [13, 19, -1, 12], [21, 27, -1, 20], [41, 47, -1, 40]]     # 8 et 21 : en position, ignorés
    o = b.open.to_numpy()
    np.testing.assert_allclose(tr.ret_gross_bps, tr.side * (o[tr.exit_bar] / o[tr.entry_bar] - 1) * 1e4)
    enchaine = time_stop_trades(b, [5, 11], [1, -1], horizon=6)                   # signal à la clôture de la barre 11
    assert enchaine[["entry_bar", "exit_bar"]].values.tolist() == [[6, 12], [12, 18]]   # entre à open[12], la sortie


def test_jamais_deux_positions_et_chaque_signal_ignore_l_est_en_position():
    b = _marche(3000, 3)
    rng = np.random.default_rng(4)
    t = np.sort(rng.choice(np.arange(10, 2990), 600, replace=False))
    for h in (6, 13, 26, 48):
        tr = time_stop_trades(b, t, rng.choice([-1, 1], len(t)), horizon=h)
        e, x, sb = tr.entry_bar.to_numpy(), tr.exit_bar.to_numpy(), tr.signal_bar.to_numpy()
        assert (e[1:] >= x[:-1]).all() and ((x - e)[:-1] == h).all()
        for ti in t[~np.isin(t, sb)]:
            k = np.searchsorted(sb, ti) - 1                                        # dernier trade ouvert avant ti
            assert k >= 0 and sb[k] < ti < x[k] - 1


def test_mode_continuation_inverse_le_sens_sans_changer_les_barres():
    b = _marche(500, 5)
    rng = np.random.default_rng(6)
    t = np.sort(rng.choice(np.arange(5, 480), 60, replace=False))
    s = rng.choice([-1, 1], 60)
    a, c = time_stop_trades(b, t, s, 13), time_stop_trades(b, t, s, 13, mode=-1)
    assert a[["entry_bar", "exit_bar", "signal_bar"]].equals(c[["entry_bar", "exit_bar", "signal_bar"]])
    assert (c.side == -a.side).all() and np.allclose(c.ret_gross_bps, -a.ret_gross_bps)


# ── Réserve 2026 et causalité ───────────────────────────────────────────────────
def test_sortie_ramenee_a_la_derniere_barre_et_2026_refuse():
    b = _bars(np.linspace(100, 101, 30))
    tr = time_stop_trades(b, [20, 27], [1, 1], horizon=26)
    assert tr[["entry_bar", "exit_bar"]].values.tolist() == [[21, 29]]           # sortie ramenée ; 27 en position
    assert len(time_stop_trades(b, [28], [1], horizon=6)) == 0                    # aucune barre détenue possible
    b26 = _bars(np.linspace(100, 101, 30), t0=pd.Timestamp("2025-12-31 20:00", tz="UTC"))
    with pytest.raises(ValueError, match="2026"):
        time_stop_trades(b26, [2], [1], horizon=6)


def test_troncature_ne_change_pas_les_trades_clos_avant_la_coupe():
    b = _marche(2000, 9)
    rng = np.random.default_rng(10)
    t = np.sort(rng.choice(np.arange(5, 1990), 300, replace=False))
    s = rng.choice([-1, 1], 300)
    full = time_stop_trades(b, t, s, 26)
    for cut in (700, 1234, 1800):
        part = time_stop_trades(b.iloc[:cut], t[t < cut], s[t < cut], 26)
        clos = full[full.exit_bar <= cut - 1].reset_index(drop=True)
        pd.testing.assert_frame_equal(part.iloc[:len(clos)].reset_index(drop=True), clos)


# ── Frais et métriques ──────────────────────────────────────────────────────────
def test_frais_5_et_10_bps():
    b = _bars([100, 100, 101, 102, 101, 100, 99, 100, 99, 102, 103, 104])
    tr = time_stop_trades(b, [0, 4], [1, 1], horizon=3)                            # +100 bps puis −100 bps bruts
    assert tr.ret_gross_bps.round(9).tolist() == [100.0, -100.0]
    m5, m10 = (summarize(tr, b, _atr(len(b)), c, n_candidates=2) for c in (5.0, 10.0))
    assert m5["esperance_bps"] == pytest.approx(-5) and m10["esperance_bps"] == pytest.approx(-10)
    assert m5["pf"] == pytest.approx(95 / 105) and m10["pf"] == pytest.approx(90 / 110) and m5["wr"] == 0.5
    assert m10["pnl_compose"] == pytest.approx(1.009 * 0.989 - 1) and m10["pnl_bps"] == pytest.approx(-20)
    assert m5["frais_cumules_bps"] == 10 and m10["part_frais"] == np.inf                   # brut cumulé nul
    assert m5["esperance_atr"] == pytest.approx(-5 / 50) and m5["mdd_bps"] == pytest.approx(-105)


def test_decomposition_long_short_timing_et_annees():
    b = _bars([100, 100, 105, 110, 100, 95, 90, 90, 90, 90, 90])
    tr = time_stop_trades(b, [0, 3, 6], [1, -1, -1], horizon=2)                    # Long +1 000 ; Short +1 000 et 0
    m = summarize(tr, b, _atr(len(b)), 0.0, n_candidates=3)
    assert (m["long_bps"], m["short_bps"]) == pytest.approx((1000, 500))
    assert (m["timing_bps"], m["derive_bps"]) == pytest.approx((750, 250))
    assert (m["long_atr"], m["timing_atr"]) == pytest.approx((20, 15))
    y = by_year(tr, b, _atr(len(b)), 0.0)
    assert y.annee.tolist() == [2021] and y.timing_bps.iat[0] == pytest.approx(750)



def test_capital_a_risque_constant():
    b = _marche(400, 13)
    tr = time_stop_trades(b, [10, 60, 150, 300], [1, -1, 1, -1], horizon=26)
    pd.testing.assert_series_equal(equity_curve_sized(b, tr, 5.0, 1.0), equity_curve(b, tr, 5.0))   # w = 1 : identique
    net = tr.ret_gross_bps.to_numpy() - 5.0
    assert equity_curve_sized(b, tr, 5.0, 0.5).iloc[-1] == pytest.approx(np.prod(1 + 0.5 * net / 1e4))
    np.testing.assert_allclose(risk_weights([20.0, 50.0, 200.0], 25.0), [1.0, 0.5, 0.125])     # plafond à 1x
    atr = pd.Series([20.0, 50.0, 100.0, 200.0], index=tr.signal_bar.to_numpy())
    s = summarize_sized(tr, b, atr, 5.0, 25.0)
    w = np.array([1.0, 0.5, 0.25, 0.125])
    assert s["pnl_compose"] == pytest.approx(np.prod(1 + w * net / 1e4) - 1)
    assert s["exposition_moyenne"] == pytest.approx(w.mean()) and s["part_plafonnee"] == 0.25
    assert s["mdd_valorise"] <= s["mdd_sorties"] + 1e-12
    assert s["pf"] == np.inf                                                         # 4 trades gagnants
    tr2 = tr.assign(ret_gross_bps=tr.ret_gross_bps * np.array([1, -1, 1, -1]))       # PnL pondérés (EXP-C02)
    s2, g2 = summarize_sized(tr2, b, atr, 5.0, 25.0), tr2.ret_gross_bps.to_numpy()
    pw = w * (g2 - 5.0)                                                              # +787, −342, +29, −54 bps
    assert s2["pf"] == pytest.approx(pw[pw > 0].sum() / -pw[pw < 0].sum())
    assert s2["part_frais"] == pytest.approx((w * 5.0).sum() / abs((w * g2).sum()))


# ── EXP-C02 : stop-loss en prix ─────────────────────────────────────────────────
def _plat(n=30):
    return _bars(np.full(n, 100.0))                                  # open = close = 100, high 100,5, low 99,5


def test_stop_atr_meche_et_gap():
    b = _plat()
    b.loc[6, "low"] = 97.9                                           # mèche sous le stop 98, ouverture à 100
    b.loc[13, ["open", "low"]] = [97.0, 96.5]                        # ouverture en gap sous le stop 98
    lvl = atr_stop_levels(b, [2, 10], [1, 1], [1.0, 1.0], k=2.0)
    assert lvl.tolist() == [98.0, 98.0]                               # open[t + 1] − 2 · ATR14(t)
    tr = stop_trades(b, [2, 10], [1, 1], horizon=6, level=lvl)
    assert tr[["entry_bar", "exit_bar", "stop", "gap"]].values.tolist() == [[3, 6, True, False], [11, 13, True, True]]
    np.testing.assert_allclose(tr.exit_price, [98.0, 97.0])           # niveau du stop ; ouverture du gap
    np.testing.assert_allclose(tr.ret_gross_bps, [-200.0, -300.0])
    s = _plat()
    s.loc[5, "high"] = 102.1                                          # Short : mèche au-dessus du stop 102
    tr = stop_trades(s, [2], [-1], horizon=6, level=atr_stop_levels(s, [2], [-1], [1.0], k=2.0))
    assert tr[["exit_bar", "stop", "gap"]].values.tolist() == [[5, True, False]]
    np.testing.assert_allclose(tr.ret_gross_bps, [-200.0])
    s.loc[3, "high"] = 102.1                                          # touché pendant la barre d'entrée elle-même
    tr = stop_trades(s, [2], [-1], horizon=6, level=atr_stop_levels(s, [2], [-1], [1.0], k=2.0))
    assert tr[["entry_bar", "exit_bar", "stop", "gap"]].values.tolist() == [[3, 3, True, False]]


def test_stop_structurel_extremum_marge_et_plancher():
    b = _plat()
    b.loc[3, "low"], b.loc[4, "low"] = 94.0, 95.0                     # segment qualifiant [3, 5], signal en 6
    assert segment_extremum(b, [6], [1], [3]).tolist() == [94.0]      # fenêtre [t − prev_seg_len, t], bornes incluses
    assert segment_extremum(b, [6], [1], [2]).tolist() == [95.0]      # la barre t − prev_seg_len compte
    lvl = structural_stop_levels(b, [6], [1], [2.0], [3], delta=0.5)
    assert lvl.tolist() == [93.0]                                     # 94 − 0,5 · 2
    b.loc[7, "open"] = 93.5                                           # entrée en gap sous l'extremum
    assert structural_stop_levels(b, [6], [1], [2.0], [3], delta=0.0).tolist() == [93.0]   # plancher 93,5 − 0,25 · 2
    b.loc[6, "low"] = 92.0                                            # la barre du signal compte aussi
    assert segment_extremum(b, [6], [1], [3]).tolist() == [92.0]
    s = _plat()
    s.loc[3, "high"] = 106.0
    assert structural_stop_levels(s, [6], [-1], [2.0], [3], delta=1.0).tolist() == [108.0]  # Short : 106 + 1 · 2
    assert structural_stop_levels(s, [6], [-1], [2.0], [1], delta=0.0).tolist() == [100.5]  # plancher : 100 + 0,5


def test_stop_vectoriel_egal_aux_appels_unitaires():
    b = _marche(3000, 31)
    rng = np.random.default_rng(32)
    e = np.sort(rng.choice(np.arange(5, 2900), 200, replace=False))
    x, s, d = e + rng.integers(1, 49, 200), rng.choice([-1, 1], 200), rng.uniform(0.002, 0.03, 200)
    vec = apply_stop(b, e, x, s, d)
    one = pd.concat([apply_stop(b, [ei], [xi], [si], float(di)) for ei, xi, si, di in zip(e, x, s, d)],
                    ignore_index=True)
    pd.testing.assert_frame_equal(vec, one)
    assert vec.stop.any() and (~vec.stop).any() and vec.gap.any()


def test_sans_stop_ou_stop_jamais_touche_redonne_time_stop_trades():
    b = _marche(3000, 33)
    rng = np.random.default_rng(34)
    t = np.sort(rng.choice(np.arange(5, 2995), 500, replace=False))
    s = rng.choice([-1, 1], 500)
    loin = atr_stop_levels(b, t, s, np.full(500, 1e6), k=1.0)       # à 10⁶ unités de prix : jamais touché
    for h in (6, 26):
        ref = time_stop_trades(b, t, s, h)
        for dyn in (True, False):
            pd.testing.assert_frame_equal(stop_trades(b, t, s, h, None, dyn), ref)
            pd.testing.assert_frame_equal(stop_trades(b, t, s, h, loin, dyn), ref)


def test_liberation_anticipee_dynamique_contre_entrees_figees():
    b = _plat(25)
    b.loc[5, "low"] = 98.8                                            # stop à 99 du premier trade, touché en barre 5
    t, s = [2, 4, 5, 7, 12], [1, 1, 1, 1, 1]
    lvl = np.array([99.0, 50.0, 50.0, 50.0, 50.0])
    dyn = stop_trades(b, t, s, horizon=8, level=lvl, dynamic=True)
    fig = stop_trades(b, t, s, horizon=8, level=lvl, dynamic=False)
    assert dyn[["signal_bar", "entry_bar", "exit_bar", "stop"]].values.tolist() == [[2, 3, 5, True], [5, 6, 14, False]]
    assert fig[["signal_bar", "entry_bar", "exit_bar", "stop"]].values.tolist() == [[2, 3, 5, True], [12, 13, 21, False]]
    # dynamique : le signal de la clôture de la barre du stop (5) entre ; 4 est ignoré (position encore ouverte)
    # figé : les entrées de la course sans stop (2 puis 12), seule la sortie du premier trade change


def test_niveau_de_stop_causal_par_troncature():
    b = _marche(3000, 35)
    rng = np.random.default_rng(36)
    t = np.sort(rng.choice(np.arange(60, 2990), 40, replace=False))
    s, a, n = rng.choice([-1, 1], 40), rng.uniform(0.5, 2.0, 40), rng.integers(1, 50, 40)
    la, lb = atr_stop_levels(b, t, s, a, 2.5), structural_stop_levels(b, t, s, a, n, 0.25)
    for i, ti in enumerate(t):
        cut = b.iloc[:ti + 2]                                         # dernière barre lue : t + 1 (prix d'entrée)
        assert atr_stop_levels(cut, [ti], [s[i]], [a[i]], 2.5)[0] == la[i]
        assert structural_stop_levels(cut, [ti], [s[i]], [a[i]], [n[i]], 0.25)[0] == lb[i]


def test_ic_en_bps_et_en_atr_egaux_au_bootstrap_de_grappes():
    b = _marche(20000, 41)                                            # ≈ 14 mois de barres 30 min
    rng = np.random.default_rng(42)
    t = np.sort(rng.choice(np.arange(10, 19900), 1500, replace=False))
    tr = time_stop_trades(b, t, rng.choice([-1, 1], 1500), 13)
    atr = pd.Series(rng.uniform(20, 80, len(b)), index=np.arange(len(b)))
    ci = mean_ci(tr, b, 5.0, n_boot=300, seed=3, atr_bps=atr)
    assert set(ci) == {f"{m}_{u}_{k}" for m in ("esperance", "timing") for u in ("bps", "atr") for k in ("lo", "hi")}
    net = tr.ret_gross_bps.to_numpy() - 5.0
    na = net / atr.reindex(tr.signal_bar.to_numpy()).to_numpy()
    sd = tr.side.to_numpy()
    tt = b.time.iloc[tr.entry_bar.to_numpy()]
    month = (tt.dt.year * 12 + tt.dt.month).to_numpy()

    def stat(pos):                                                    # implémentation de C01, étendue à l'ATR
        return [net[pos].mean(), timing_drift(net[pos], sd[pos], "mean")[0],
                na[pos].mean(), timing_drift(na[pos], sd[pos], "mean")[0]]

    lo, hi = np.nanpercentile(cluster_bootstrap(stat, month, 300, 3), [2.5, 97.5], axis=0)
    keys = ["esperance_bps", "timing_bps", "esperance_atr", "timing_atr"]
    np.testing.assert_allclose([ci[f"{k}_lo"] for k in keys], lo, rtol=0, atol=1e-9)
    np.testing.assert_allclose([ci[f"{k}_hi"] for k in keys], hi, rtol=0, atol=1e-9)
    assert mean_ci(tr, b, 5.0, n_boot=300, seed=3) == {k: v for k, v in ci.items() if "_bps_" in k}


def test_effet_apparie_du_stop_sur_les_entrees_figees():
    b = _marche(20000, 51)
    rng = np.random.default_rng(52)
    t = np.sort(rng.choice(np.arange(10, 19900), 800, replace=False))
    s = rng.choice([-1, 1], 800)
    lvl = atr_stop_levels(b, t, s, np.full(800, 1.0), k=1.0)
    ctrl, fig = stop_trades(b, t, s, 26), stop_trades(b, t, s, 26, lvl, dynamic=False)
    atr = pd.Series(50.0, index=np.arange(len(b)))
    eff = effect_ci(fig, ctrl, b, atr, n_boot=200)
    d = fig.ret_gross_bps.to_numpy() - ctrl.ret_gross_bps.to_numpy()
    assert eff["effet_bps"] == pytest.approx(d.mean()) and eff["effet_atr"] == pytest.approx(d.mean() / 50)
    assert eff["effet_bps_lo"] < eff["effet_bps"] < eff["effet_bps_hi"] and fig.stop.mean() > 0.2
    with pytest.raises(ValueError, match="entrées"):
        effect_ci(stop_trades(b, t, s, 26, lvl, dynamic=True), ctrl, b, atr)

# ── Données réelles ─────────────────────────────────────────────────────────────
@pytest.fixture(scope="module")
def dev():
    if not DATA_RAW.exists():
        pytest.skip("données absentes")
    from anatomy import load_dev_bars
    from anatomy.causal import atr_wilder
    from estimand import load_bars_dev
    from features import build_features
    df, bars = load_dev_bars(), load_bars_dev()
    assert np.array_equal(df[["open", "high", "low", "close"]].to_numpy(), bars[["open", "high", "low", "close"]].to_numpy())
    f = build_features(df)
    atr_bps = pd.Series(atr_wilder(f.high, f.low, f.close) / f.close.to_numpy() * 1e4, index=np.arange(len(f)))
    return bars, f, atr_bps


@pytest.mark.data
@pytest.mark.parametrize("variante, stop", [("sans_stop", None), ("stop_2_5", 0.025)])
def test_ancre_p65d_reproduite(dev, variante, stop):
    bars, f, atr_bps = dev
    sig = dev_signals(f)
    assert len(sig) == 7297 and sig.bar_index.iat[-1] == 105211
    tr, ouvert = simulate_strategy(bars, sig, stop)
    ref = pd.read_csv(ROOT / "experiments" / "p6_5" / "strategie_stop_trades.csv")
    ref = ref[ref.variante == variante].reset_index(drop=True)
    for c in ("entry_bar", "exit_bar", "side", "signal_bar", "stop", "gap"):
        assert np.array_equal(tr[c].to_numpy(), ref[c].to_numpy()), c
    a_la_precision_du_fichier = np.array([float(f"{v:.10g}") for v in tr.ret_gross_bps])
    assert np.array_equal(a_la_precision_du_fichier, ref.ret_gross_bps.to_numpy())
    js = json.loads((ROOT / "experiments" / "p6_5" / "strategie_stop.json").read_text(encoding="utf-8"))
    js = js["strategie"][variante]
    m = summarize(tr, bars, atr_bps, 5.0, n_candidates=len(sig), n_open=1)
    assert m["n_trades"] == js["n_trades"] and ouvert == js["trade_ouvert_fin_2025"]
    cap = js["capital"]["net"]
    for k, v in [("esperance_bps", js["net"]["moyenne"]), ("pnl_bps", js["somme_nette_bps"]),
                 ("wr", js["taux_de_reussite_net"]), ("pnl_compose", cap["rendement_compose"]),
                 ("mdd_valorise", cap["max_drawdown_valorise"]["max_drawdown"]),
                 ("mdd_sorties", cap["max_drawdown_aux_sorties"]), ("duree_mediane", js["duree_mediane_barres"])]:
        assert m[k] == pytest.approx(v, abs=1e-6), k
    g = js["gagnants_perdants_net"]
    pf = g["part_gagnants"] * g["gain_moyen"] / ((1 - g["part_gagnants"]) * -g["perte_moyenne"])
    assert m["pf"] == pytest.approx(pf, rel=1e-4)


@pytest.mark.data
def test_extremum_du_segment_sur_btc_est_celui_de_retrace_ratio(dev):
    from anatomy import dev_universe
    from anatomy.causal import atr_wilder, causal_table
    bars, f, _ = dev
    idx = dev_universe(f)
    atr = atr_wilder(f.high, f.low, f.close)
    ct = causal_table(f, idx, atr)
    sig = f.signal.to_numpy()[idx].astype(int)
    ext = segment_extremum(bars, idx, sig, ct.prev_seg_len.to_numpy())
    dist = np.abs(bars.close.to_numpy()[idx] - ext) / atr[idx]
    np.testing.assert_allclose(dist, ct.obs_dist_seg_atr.to_numpy(), rtol=0, atol=1e-9)
    for d in (0.0, 1.0):
        lvl = structural_stop_levels(bars, idx, sig, atr[idx], ct.prev_seg_len.to_numpy(), d)
        p0 = bars.open.to_numpy()[idx + 1]
        assert (sig * (p0 - lvl) >= 0.25 * atr[idx] - 1e-9).all()      # jamais à moins de 0,25 ATR de l'entrée


@pytest.mark.data
def test_sortie_a_horizon_fixe_sur_btc(dev):
    from anatomy import dev_universe
    bars, f, _ = dev
    idx = dev_universe(f)
    sig = f.signal.to_numpy()[idx].astype(int)
    for h in (6, 48):
        for mode in (1, -1):
            tr = time_stop_trades(bars, idx, sig, h, mode)
            assert (tr.entry_bar.to_numpy()[1:] >= tr.exit_bar.to_numpy()[:-1]).all()
            assert ((tr.exit_bar - tr.entry_bar) <= h).all() and (bars.time.iloc[tr.exit_bar] < HOLDOUT).all()
