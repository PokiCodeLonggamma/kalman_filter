"""P2 — parité des modules src/indicator avec l'oracle P0 (vérifié sur TradingView) et conventions D22 / D25.

Mode parité : run_indicator(df, fill_price="close", warmup_bars=0). Tolérance numérique absolue : PARITY_ABS_TOL (1e-5).
Mesures de référence : experiments/p2/parity_report.py -> parity_report.json.
"""
import hashlib
import json

import numpy as np
import pandas as pd
import pytest

from config import (BASELINE_PINE, BASELINE_SHA256, ORACLE, ORACLE_SHA256, PARITY_ABS_TOL, ROOT, WARMUP_BARS)
from indicator import run_indicator

pytestmark = pytest.mark.data

FLOAT_COLS = {c: c for c in ["x0", "x1", "x0_pred", "x1_pred", "innov", "S", "nis", "K0", "K1", "P00", "P01", "P11",
                             "Ppred00", "Ppred01", "Ppred11", "R", "A", "ratio", "ts", "ts_plot"]}
FLOAT_COLS.update({"seg_extreme_abs": "seg_ext", "prev_seg_extreme_abs": "prev_ext"})
DISCRETE_COLS = {"seg_zone": "seg_zone", "seg_len": "seg_len", "prev_seg_zone": "prev_zone",
                 "prev_seg_len": "prev_len", "long_signal": "long", "short_signal": "short"}


# ── Intégrité des références ─────────────────────────────────────────────────────
def _sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_baseline_pine_inchangee():
    assert _sha(BASELINE_PINE) == BASELINE_SHA256


def test_oracle_p0_inchange():
    assert _sha(ORACLE) == ORACLE_SHA256


# ── Parité barre par barre sur tout l'historique ────────────────────────────────
@pytest.mark.parametrize("col", sorted(FLOAT_COLS))
def test_parite_continue(ind_close, oracle_full, col):
    a, b = ind_close[col].to_numpy(float), oracle_full[FLOAT_COLS[col]].to_numpy(float)
    assert np.array_equal(np.isnan(a), np.isnan(b)), "motif de NaN différent"
    m = ~np.isnan(a)
    assert np.max(np.abs(a[m] - b[m]), initial=0.0) <= PARITY_ABS_TOL


@pytest.mark.parametrize("col", sorted(DISCRETE_COLS))
def test_parite_discrete_exacte(ind_close, oracle_full, col):
    assert np.array_equal(ind_close[col].to_numpy(int), oracle_full[DISCRETE_COLS[col]].to_numpy(int))


def test_parite_zone(ind_close, oracle_full):
    """L'oracle met zone = 0 tant que ts est indéfini ; le module met NaN (D23). Égalité une fois NaN -> 0."""
    z = ind_close.zone.to_numpy(float)
    assert np.isnan(z).sum() == 6
    assert np.array_equal(np.nan_to_num(z, nan=0.0), oracle_full.zone.to_numpy(float))


# ── Ancres TradingView ──────────────────────────────────────────────────────────
@pytest.mark.parametrize("start", ["2025-06-01", None], ids=["depart_2025-06", "depart_2020"])
def test_fixture_data_window_2026_09_15(df_full, start):
    fx = json.loads((ROOT / "tests" / "fixtures" / "tv_datawindow_2026-09-15.json").read_text(encoding="utf-8"))
    d = df_full if start is None else df_full[df_full.time >= pd.Timestamp(start, tz="UTC")].reset_index(drop=True)
    r = run_indicator(d, fill_price="close", warmup_bars=0)
    row = r[r.time == pd.Timestamp(fx["bar_time_utc"])].iloc[0]
    got = {"kalman_x0": round(row.x0), "ts_plot": round(row.ts_plot), "R_used": round(row.R),
           "innovation": round(row.innov), "nis": round(row.nis), "table_ts": round(row.ts)}
    assert got == fx["values"]


def test_carnet_p0_20_signaux(ind_close):
    cas = pd.read_csv(ROOT / "experiments" / "p0" / "p0_20_cas_tradingview.csv")
    tc = pd.to_datetime(cas.paris, format="%d/%m/%Y %H:%M").dt.tz_localize("Europe/Paris").dt.tz_convert("UTC")
    s = ind_close.set_index("time")
    for t, d in zip(tc, cas.dir):
        col = "long_signal" if d.startswith("Long") else "short_signal"
        assert s.at[t, col], f"signal {d} absent le {t}"


def test_compteurs_2026_p0(ind_close):
    y = ind_close[ind_close.time.dt.year == 2026]
    assert ((y.signal != 0).sum(), y.decision.sum(), y.ignored.sum()) == (864, 720, 144)


# ── Convention d'exécution D25 ──────────────────────────────────────────────────
@pytest.fixture(scope="module")
def ind_open_next(df_full):
    return run_indicator(df_full, fill_price="open_next", warmup_bars=0)


def test_open_next_memes_decisions_que_close(ind_close, ind_open_next):
    assert np.array_equal(ind_close.decision.to_numpy(), ind_open_next.decision.to_numpy())


def test_open_next_remplit_a_l_open_suivant(df_full, ind_open_next):
    dec = np.flatnonzero(ind_open_next.decision)
    fil = np.flatnonzero(ind_open_next.fill.to_numpy() != 0)
    assert np.array_equal(fil, dec[dec + 1 < len(df_full)] + 1)
    assert np.array_equal(ind_open_next.fill_px.to_numpy()[fil], df_full.open.to_numpy()[fil])
    assert np.array_equal(ind_open_next.fill.to_numpy()[fil], ind_open_next.signal.to_numpy()[fil - 1])


def test_close_remplit_au_close_de_la_barre_signal(df_full, ind_close):
    dec = np.flatnonzero(ind_close.decision)
    assert np.array_equal(np.flatnonzero(ind_close.fill.to_numpy() != 0), dec)
    assert np.array_equal(ind_close.fill_px.to_numpy()[dec], df_full.close.to_numpy()[dec])


# ── Warm-up D22 ─────────────────────────────────────────────────────────────────
def test_warmup_300_production(df_full, ind_open_next):
    w = run_indicator(df_full)                                   # défauts : open_next, 300 barres
    assert WARMUP_BARS == 300
    assert (~w.valid.iloc[:300]).all() and w.valid.iloc[300:].all()
    dw, dn = np.flatnonzero(w.decision), np.flatnonzero(ind_open_next.decision)
    assert dw.min() >= 300
    assert np.array_equal(dw[1:], dn[dn > dw[0]])                # identique au flux complet après la 1re décision


@pytest.mark.parametrize("k", [1000, 35040, 87600])
def test_independance_au_depart_apres_warmup(df_full, ind_close, k):
    """Après 300 barres, signaux et zones identiques à la série complète ; ts converge sous 1e-4 (critère D22)."""
    r = run_indicator(df_full.iloc[k:].reset_index(drop=True), fill_price="close", warmup_bars=0)
    ref = ind_close.iloc[k:].reset_index(drop=True)
    sl = slice(WARMUP_BARS, None)
    assert np.array_equal(r.signal.to_numpy()[sl], ref.signal.to_numpy()[sl])
    assert np.array_equal(np.nan_to_num(r.zone.to_numpy()[sl]), np.nan_to_num(ref.zone.to_numpy()[sl]))
    assert np.nanmax(np.abs(r.ts.to_numpy()[sl] - ref.ts.to_numpy()[sl])) < 1e-4


# ── Invariants ──────────────────────────────────────────────────────────────────
def test_invariance_d_echelle(df_full, ind_close):
    d = df_full.copy()
    d[["open", "high", "low", "close"]] *= 0.001
    r = run_indicator(d, fill_price="close", warmup_bars=0)
    assert np.array_equal(r.signal.to_numpy(), ind_close.signal.to_numpy())
    assert np.array_equal(r.decision.to_numpy(), ind_close.decision.to_numpy())


def test_causalite_par_troncature(df_full):
    """Le préfixe [0, t] calculé sur l'historique [0, t] est identique au calcul sur un historique plus long,
    aux barres de décision, de remplissage et de signal ignoré comprises (toutes les colonnes)."""
    n = 12000
    full = run_indicator(df_full.iloc[:n], fill_price="open_next", warmup_bars=WARMUP_BARS)
    dec = np.flatnonzero(full.decision)
    ign = np.flatnonzero(full.ignored)
    points = sorted({0, 6, 299, 300, *dec[:3].tolist(), *(dec[:3] + 1).tolist(), *ign[:2].tolist(), n - 2})
    for t in points:
        part = run_indicator(df_full.iloc[:t + 1], fill_price="open_next", warmup_bars=WARMUP_BARS)
        pd.testing.assert_frame_equal(part, full.iloc[:t + 1], check_exact=True, obj=f"préfixe [0, {t}]")
