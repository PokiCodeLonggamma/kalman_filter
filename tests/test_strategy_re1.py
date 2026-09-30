"""EXP-D01 — RE-1 figée (`strategy.re1`) : seuils BTC gelés, reproduction trade par trade de C02bis (bloquant),
seuils jamais recalculés sur un autre actif, causalité par troncature, réserve 2026, absence de lookahead."""
import importlib.util
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from config import DATA_RAW, ROOT
from strategy import (LEG_ATR_P50_BTC, NIS_Z100_P75_BTC, frozen_masks, load_asset, metrics, run_re1,
                      sample_years)
from utils.data_loader import sha256_file

C02BIS = ROOT / "experiments" / "C02bis"


def _c02bis():
    spec = importlib.util.spec_from_file_location("run_C02bis_test", C02BIS / "run_C02bis.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def btc():
    if not DATA_RAW.exists():
        pytest.skip("data/raw/bitstamp_btcusd_30m.csv absent (hors dépôt)")
    from anatomy import build_atlas
    df, bars = load_asset(DATA_RAW)
    atlas, _, _, atr = build_atlas(df)
    return df, bars, atlas, atr


@pytest.mark.data
def test_seuils_geles_egaux_aux_statistiques_de_l_atlas_btc(btc):
    from categorization import add_derived
    d = add_derived(btc[2])
    assert LEG_ATR_P50_BTC == float(np.median(d.leg_atr))
    assert NIS_Z100_P75_BTC == float(np.quantile(d.nis_z_100, 0.75))


@pytest.mark.data
def test_familles_et_univers_de_c02bis(btc):
    atlas = btc[2]
    fam, m = frozen_masks(atlas)
    ref = pd.read_csv(ROOT / "experiments" / "B01" / "excursions_signaux.csv", usecols=["bar_index", "famille"])
    assert np.array_equal(ref.bar_index, atlas.bar_index) and np.array_equal(ref.famille, fam)
    assert (int(m["R2"].sum()), int(m["F2b"].sum()), int(m["F3"].sum())) == (1452, 741, 711)
    assert int(m["R2_avant_nis"].sum()) == 1874 and not (m["R2"] & m["nis_exclus"]).any()
    assert not (m["R1"] & m["R2_avant_nis"]).any() and not (m["R3"] & m["R2_avant_nis"]).any()


@pytest.mark.data
def test_re1_btc_trade_par_trade_et_metriques_de_c02bis(btc):
    """Contrôle bloquant de D01 : même moteur, même chaîne, mêmes 1 080 trades et mêmes métriques que C02bis."""
    _, bars, atlas, atr = btc
    _, m = frozen_masks(atlas)
    tr, fam = run_re1(bars, atlas, atr, m)
    c2b = _c02bis()
    eng = c2b.Engine(bars, atlas, atr, c2b.full_masks(atlas))
    ref, ref_fam = eng.run("R2", {"F2b": None, "F3": ("SL-B", 0.0)}, 26, False)
    assert len(tr) == 1080 and tr.equals(ref) and fam.equals(ref_fam)
    assert sample_years(bars) == 6.0
    atr_bps = pd.Series(atlas.atr14_bps.to_numpy(), index=atlas.bar_index.to_numpy())
    res = pd.read_csv(C02BIS / "resultats_C02bis.csv")
    for fee in (5.0, 10.0):
        got, _ = metrics(tr, bars, atr_bps, fee, int(m["R2"].sum()), fam, sample_years(bars))
        g = res[(res.variante_seuils == c2b.ENTIER) & (res.configuration == "RE-1") & (res.H == 26)
                & (res["mode"] == "cooldown") & (res.frais_bps == fee)].iloc[0]
        for c in ("n_trades", "esperance_bps", "esperance_bps_lo", "esperance_bps_hi", "esperance_atr",
                  "esperance_atr_lo", "esperance_atr_hi", "pnl_compose", "mdd_valorise", "pf", "wr",
                  "pnl_compose_r25", "mdd_valorise_r25", "calmar_r25", "timing_atr_lo", "part_stop", "n_F3",
                  "esperance_atr_F3", "annees_atr_pos"):
            assert np.isclose(got[c], g[c], rtol=1e-5, atol=1e-9), c


def _atlas_synthetique(leg, nis, retrace, x1):
    leg = np.asarray(leg, dtype=float)
    n = len(leg)
    return pd.DataFrame({"bar_index": np.arange(n) * 100 + 400, "direction": np.where(np.arange(n) % 2, 1, -1),
                         "prev_seg_len": np.full(n, 8), "leg_atr": leg, "obs_dist_seg_atr": leg * np.asarray(retrace),
                         "obs_dist_cycle_atr": leg * np.asarray(retrace), "A_vol": np.ones(n),
                         "peak_bps_vol": np.ones(n), "x1_already_flipped_at_t": np.asarray(x1, dtype=bool),
                         "nis_z_100": np.asarray(nis, dtype=float)})


def test_seuils_btc_jamais_recalcules_sur_un_autre_actif():
    """Un actif dont les distributions diffèrent garde les seuils numériques de BTC (option (a), zero-shot)."""
    leg = [1.0, 2.0, 2.8, 2.9, 5.0, 6.0]                    # médiane locale 2,85 ≠ 2,8233 de BTC
    nis = [0.5, 1.2, 1.3, 0.0, 3.0, np.nan]
    a = _atlas_synthetique(leg, nis, [0.6, 0.9, 0.6, 0.6, 0.9, 0.6], [True] * 6)
    fam, m = frozen_masks(a)
    assert list(fam) == ["F2b", "F3", "F2b", "F2a", "F4", "F2a"]            # 2,9 ≥ 2,8233 : jambe ample
    assert m["R2"].tolist() == [True, True, False, False, False, False]    # nis 1,3 > 1,2245 : exclu ; NaN exclu
    assert m["nis_exclus"].tolist() == [False, False, True, False, False, False]
    assert m["R3"].tolist() == [False, False, False, True, True, True]
    b = _atlas_synthetique(leg, np.asarray(nis) + 10.0, [0.6] * 6, [True] * 6)
    assert not frozen_masks(b)[1]["R2"].any()                              # tout au-dessus du P75 de BTC


def test_annualisation_sur_la_duree_propre_a_l_actif():
    t = pd.date_range("2020-01-01", periods=3, freq="30min", tz="UTC")
    assert sample_years(pd.DataFrame({"time": t})) == 6.0
    t = pd.date_range("2020-08-11 06:00", periods=3, freq="30min", tz="UTC")
    assert np.isclose(sample_years(pd.DataFrame({"time": t})), 6.0 - 223.25 / 365.25)


def test_reserve_2026_tronquee_au_chargement_et_refusee_a_l_execution(tmp_path):
    t = pd.date_range("2025-12-31 20:00", "2026-01-01 04:00", freq="30min", tz="UTC")
    c = np.linspace(100.0, 101.0, len(t))
    p = tmp_path / "x_30m.csv"
    pd.DataFrame({"time": t, "timestamp": t.asi8 // 10**9, "open": c, "high": c + 0.5, "low": c - 0.5, "close": c,
                  "volume": 1.0}).to_csv(p, index=False)
    p.with_name("x_30m.meta.json").write_text(json.dumps({"sha256": sha256_file(p),
                                                          "extracted_at_utc": "2026-09-30T00:00:00+00:00"}))
    _, bars = load_asset(p)
    assert bars.time.max() < pd.Timestamp("2026-01-01", tz="UTC") and len(bars) == 8
    full = pd.DataFrame({"time": t, "open": c, "high": c + 0.5, "low": c - 0.5, "close": c})
    atlas = pd.DataFrame({"bar_index": [1], "direction": [1], "prev_seg_len": [2]})
    m = {"R2": np.array([True]), "F3": np.array([False])}
    with pytest.raises(ValueError, match="réserve 2026"):
        run_re1(full, atlas, np.ones(len(t)), m)


@pytest.mark.data
def test_re1_causal_par_troncature(btc):
    """Les trades clos bien avant une coupe sont identiques avec ou sans les barres postérieures à la coupe."""
    from anatomy import build_atlas
    df, bars, atlas, atr = btc
    _, m = frozen_masks(atlas)
    full, _ = run_re1(bars, atlas, atr, m)
    cut = int(np.searchsorted(bars.time, pd.Timestamp("2023-06-30", tz="UTC")))
    df_c, bars_c = df.iloc[:cut].reset_index(drop=True), bars.iloc[:cut].reset_index(drop=True)
    atlas_c, _, _, atr_c = build_atlas(df_c)
    _, m_c = frozen_masks(atlas_c)
    trunc, _ = run_re1(bars_c, atlas_c, atr_c, m_c)
    early = full[full.exit_bar < cut - 500].reset_index(drop=True)
    assert len(early) > 500 and trunc.iloc[:len(early)].reset_index(drop=True).equals(early)


def test_aucun_decalage_vers_le_futur_dans_les_nouveaux_modules():
    for p in list((ROOT / "src" / "strategy").glob("*.py")) + list((ROOT / "src" / "marketdata").glob("*.py")):
        assert "shift(-" not in Path(p).read_text(encoding="utf-8"), p.name
