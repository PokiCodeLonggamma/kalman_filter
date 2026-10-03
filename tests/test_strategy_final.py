"""RE-1 version finale (`strategy.final`) : RE-1 gelée et stop catastrophe de 4 ATR14(t) greffé sur tous les trades
(décision du porteur du 2026-10-03). Niveaux causaux, composition avec SL-B, mêmes entrées que RE-1 gelée."""
import numpy as np
import pandas as pd

from envelope.stress import nearest_levels
from optimization import candidates, run_trades, signal_table
from strategy import F3_BOUNDARY, LEG_ATR_P50_BTC, NIS_Z100_P75_BTC
from strategy.final import K_CAT, final_levels, run_final


def _universe(barres_synthetiques, atlas_synthetique, seed=0):
    bars = barres_synthetiques(4000, seed=seed)
    atlas, atr = atlas_synthetique(bars, 600, seed=seed + 1)
    tab = signal_table(bars, atlas, atr)
    return bars, tab, atr / bars.close.to_numpy() * 1e4


def test_niveaux_f2b_au_stop_catastrophe_f3_au_plus_proche(barres_synthetiques, atlas_synthetique):
    bars, tab, atr_bps = _universe(barres_synthetiques, atlas_synthetique)
    t, s, lv = candidates(tab, LEG_ATR_P50_BTC, NIS_Z100_P75_BTC, F3_BOUNDARY)
    got = final_levels(bars, t, s, lv, atr_bps)
    p0 = bars.open.to_numpy()[t + 1]
    atr_px = atr_bps[t] * bars.close.to_numpy()[t] / 1e4
    cat = p0 - s * K_CAT * atr_px
    f2b = np.isnan(lv)
    assert f2b.sum() > 20 and (~f2b).sum() > 20
    assert np.allclose(got[f2b], cat[f2b], rtol=0, atol=1e-9)
    assert np.array_equal(got[~f2b], nearest_levels(s[~f2b], lv[~f2b], cat[~f2b]))
    dist = s * (p0 - got) / atr_px                                  # distance à l'entrée, en ATR, côté perte
    assert (dist > 0).all() and (dist <= K_CAT + 1e-9).all()


def test_stop_infini_redonne_re1_gelee_et_memes_entrees(barres_synthetiques, atlas_synthetique):
    bars, tab, atr_bps = _universe(barres_synthetiques, atlas_synthetique, seed=3)
    t, s, lv = candidates(tab, LEG_ATR_P50_BTC, NIS_Z100_P75_BTC, F3_BOUNDARY)
    base = run_trades(bars, t, s, 26, lv)
    far, _, _ = run_final(bars, tab, atr_bps, k=1e6)
    assert far.equals(base)
    tr, (t2, s2, lv2, lvl), fam = run_final(bars, tab, atr_bps)
    assert np.array_equal(t2, t) and np.array_equal(lv2, lv, equal_nan=True)
    assert tr.equals(run_trades(bars, t, s, 26, final_levels(bars, t, s, lv, atr_bps)))
    assert tr.signal_bar.tolist() == base.signal_bar.tolist()       # le stop ne change pas le verrou : mêmes entrées
    assert (fam.reindex(t).to_numpy() == np.where(np.isnan(lv), "F2b", "F3")).all()
    assert tr.stop.sum() > base.stop.sum()


def test_niveaux_causaux(barres_synthetiques, atlas_synthetique):
    bars, tab, atr_bps = _universe(barres_synthetiques, atlas_synthetique, seed=5)
    t, s, lv = candidates(tab, LEG_ATR_P50_BTC, NIS_Z100_P75_BTC, F3_BOUNDARY)
    ref = final_levels(bars, t, s, lv, atr_bps)
    k = len(t) // 2
    cut = t[k] + 1                                                  # barres après l'entrée du k-ième candidat
    b2 = bars.copy()
    rng = np.random.default_rng(9)
    for c in ("open", "high", "low", "close"):
        b2.loc[cut + 1:, c] = b2.loc[cut + 1:, c].to_numpy() * rng.uniform(0.5, 1.5, len(b2) - cut - 1)
    a2 = atr_bps.copy()
    a2[cut + 1:] = rng.uniform(5, 500, len(a2) - cut - 1)
    got = final_levels(b2, t[:k + 1], s[:k + 1], lv[:k + 1], a2)
    assert np.array_equal(got, ref[:k + 1], equal_nan=True)
    assert isinstance(run_final(bars, tab, atr_bps, start=pd.Timestamp(bars.time.iat[1000]),
                                end=pd.Timestamp(bars.time.iat[2000]))[0], pd.DataFrame)
