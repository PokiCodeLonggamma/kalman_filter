"""EXP-D02 — table des signaux, seuils de population par fenêtre et candidats (`optimization.universe`) : identiques
aux masques et aux niveaux de RE-1 à la frontière 0,85 ; seuils lus sur les seuls signaux de l'IS ; la frontière ne
fait que router le stop. Données réelles : Gate 0 (1 080 trades de RE-1 sur BTC) et parité hors du point de RE-1."""
import numpy as np
import pandas as pd
import pytest

from config import DATA_RAW
from envelope import route_levels
from optimization.engine import run_trades
from optimization.universe import candidates, signal_table, window_thresholds
from strategy import FLOOR, LEG_ATR_P50_BTC, NIS_Z100_P75_BTC, RULES, frozen_masks, load_asset, run_re1

UTC = "UTC"
FRONTIERES = (0.75, 0.80, 0.85, 0.90, 0.95)


def _universe(barres_synthetiques, atlas_synthetique, seed=0):
    bars = barres_synthetiques(4000, seed=seed)
    atlas, atr = atlas_synthetique(bars, 600, seed=seed + 1)
    return bars, atlas, atr, signal_table(bars, atlas, atr)


def test_candidats_a_la_frontiere_085_egaux_a_re1(barres_synthetiques, atlas_synthetique):
    bars, atlas, atr, tab = _universe(barres_synthetiques, atlas_synthetique)
    leg, nis = 2.8, 1.0
    t, s, level = candidates(tab, leg, nis, 0.85)
    _, m = frozen_masks(atlas, leg, nis)
    r2 = m["R2"]
    assert r2.sum() > 50 and np.array_equal(t, atlas.bar_index.to_numpy()[r2])
    assert np.array_equal(s, atlas.direction.to_numpy()[r2])
    fam = np.where(m["F3"][r2], "F3", "F2b")
    ref = route_levels(bars, t, s, atr[t], atlas.prev_seg_len.to_numpy()[r2], fam, RULES, FLOOR)
    assert np.array_equal(level, ref, equal_nan=True) and np.isnan(level).any() and (~np.isnan(level)).any()


def test_la_frontiere_ne_fait_que_router_le_stop(barres_synthetiques, atlas_synthetique):
    _, _, _, tab = _universe(barres_synthetiques, atlas_synthetique)
    t0, s0, l0 = candidates(tab, 2.8, 1.0, 0.85)
    r = pd.Series(tab.retrace, index=tab.t).reindex(t0).to_numpy()
    for f in FRONTIERES:
        t, s, level = candidates(tab, 2.8, 1.0, f)
        assert np.array_equal(t, t0) and np.array_equal(s, s0)
        assert np.array_equal(np.isnan(level), r < f)
        both = ~np.isnan(level) & ~np.isnan(l0)
        assert np.array_equal(level[both], l0[both])      # même niveau SL-B, quelle que soit la frontière


def test_candidats_restreints_a_une_periode(barres_synthetiques, atlas_synthetique):
    bars, _, _, tab = _universe(barres_synthetiques, atlas_synthetique)
    a, b = bars.time.iat[1000], bars.time.iat[2500]
    t, _, _ = candidates(tab, 2.8, 1.0, 0.85, start=a, end=b)
    times = bars.time.iloc[t]
    assert len(t) > 10 and (times >= a).all() and (times < b).all()


def test_seuils_lus_sur_les_seuls_signaux_de_la_fenetre(barres_synthetiques, atlas_synthetique):
    bars, atlas, atr, tab = _universe(barres_synthetiques, atlas_synthetique)
    a, b = bars.time.iat[1000], bars.time.iat[2500]
    inside = ((atlas.timestamp >= a) & (atlas.timestamp < b)).to_numpy()
    leg, nis, n = window_thresholds(tab, a, b)
    assert n == inside.sum()
    assert leg == float(np.median(atlas.leg_atr[inside])) and nis == float(np.quantile(atlas.nis_z_100[inside], 0.75))
    other = atlas.copy()
    other.loc[~inside, "leg_atr"] *= 10.0
    other.loc[~inside, "nis_z_100"] += 5.0
    assert window_thresholds(signal_table(bars, other, atr), a, b) == (leg, nis, n)


def test_seuils_ignorent_les_nan(barres_synthetiques, atlas_synthetique):
    bars, atlas, atr, _ = _universe(barres_synthetiques, atlas_synthetique)
    atlas.loc[atlas.index[::7], "nis_z_100"] = np.nan
    a, b = bars.time.iat[0], bars.time.iat[-1]
    _, nis, _ = window_thresholds(signal_table(bars, atlas, atr), a, b)
    sel = (atlas.timestamp >= a) & (atlas.timestamp < b) & atlas.nis_z_100.notna()
    assert nis == float(np.quantile(atlas.nis_z_100[sel], 0.75))


# ── Données réelles (BTC/USD 30 min 2020-2025) ──────────────────────────────────
@pytest.fixture(scope="module")
def btc():
    if not DATA_RAW.exists():
        pytest.skip("data/raw/bitstamp_btcusd_30m.csv absent (hors dépôt)")
    from anatomy import build_atlas
    df, bars = load_asset(DATA_RAW)
    atlas, _, _, atr = build_atlas(df)
    return df, bars, atlas, atr, signal_table(bars, atlas, atr)


@pytest.mark.data
def test_gate0_le_noyau_redonne_les_1080_trades_de_re1(btc):
    _, bars, atlas, atr, tab = btc
    t, s, level = candidates(tab, LEG_ATR_P50_BTC, NIS_Z100_P75_BTC, 0.85)
    got = run_trades(bars, t, s, 26, level)
    ref, _ = run_re1(bars, atlas, atr, frozen_masks(atlas)[1])
    assert len(got) == 1080 and got.equals(ref)


@pytest.mark.data
def test_seuils_de_la_fenetre_2020_2025_egaux_aux_seuils_geles(btc):
    tab = btc[4]
    leg, nis, n = window_thresholds(tab, pd.Timestamp("2020-01-01", tz=UTC), pd.Timestamp("2026-01-01", tz=UTC))
    assert (leg, nis, n) == (LEG_ATR_P50_BTC, NIS_Z100_P75_BTC, 7296)


@pytest.mark.data
def test_parite_hors_du_point_de_re1_horizon_et_frontiere(btc):
    _, bars, atlas, atr, tab = btc
    _, m = frozen_masks(atlas)
    for h in (6, 60):
        t, s, level = candidates(tab, LEG_ATR_P50_BTC, NIS_Z100_P75_BTC, 0.85)
        assert run_trades(bars, t, s, h, level).equals(run_re1(bars, atlas, atr, m, horizon=h)[0])
    from categorization import add_derived
    r = add_derived(atlas).retrace_ratio.to_numpy()
    for f in (0.75, 0.95):
        mf = dict(m, F3=m["R2"] & (r >= f))
        t, s, level = candidates(tab, LEG_ATR_P50_BTC, NIS_Z100_P75_BTC, f)
        assert run_trades(bars, t, s, 26, level).equals(run_re1(bars, atlas, atr, mf)[0])
