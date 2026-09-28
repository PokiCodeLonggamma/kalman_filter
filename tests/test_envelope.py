"""EXP-C01 — enveloppe séquentielle : sortie à horizon fixe, pyramiding 0, frais, continuation, réserve 2026, causalité
par troncature, métriques ; ancre P6.5d (sans stop et stop 2,5 %) reproduite sur BTC."""
import json

import numpy as np
import pandas as pd
import pytest

from config import DATA_RAW, ROOT
from envelope import (by_year, dev_signals, equity_curve_sized, risk_weights, summarize, summarize_sized,
                      time_stop_trades)
from estimand.stoploss import equity_curve, simulate_strategy

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
