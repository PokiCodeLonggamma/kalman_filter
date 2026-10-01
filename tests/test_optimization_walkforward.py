"""EXP-D02 — orchestration du walk-forward (`optimization.walkforward`) : grille du protocole, évaluation d'un IS sans
aucune donnée postérieure, branches OFAT = axes de la grille conjointe, calendriers Statique / WFO, candidats hors
échantillon aux paramètres et seuils de leur semestre, position à cheval sur deux semestres, 10 séries comparées."""
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from config import ROOT
from optimization.engine import run_trades
from optimization.objective import is_metrics
from optimization.universe import candidates, signal_table, window_thresholds
from optimization.walkforward import (GRID_F, GRID_H, GRID_R0, RE1_INDEX, RE1_POINT, VARIANTS, AssetData, Params,
                                      branch_choice, evaluate_is, oos_candidates, run_oos, variant_schedule)
from optimization.windows import bar_span, walk_forward_windows
from strategy import LEG_ATR_P50_BTC, NIS_Z100_P75_BTC

UTC = "UTC"
PETITE = (GRID_R0[1:4], (6, 26, 40), (0.80, 0.85, 0.90))       # grille réduite pour les tests synthétiques


def _asset(barres_synthetiques, atlas_synthetique, n=36000, m=2500, seed=0, fee=5.0):
    """Série synthétique du 2021-01-01 au 2023-01-21 environ ; une table par R0 (atlas décalés pour les distinguer)."""
    bars = barres_synthetiques(n, seed=seed)
    tabs = {}
    for i, r0 in enumerate(GRID_R0):
        atlas, atr = atlas_synthetique(bars, m, seed=seed + 10 + i)
        tabs[r0] = signal_table(bars, atlas, atr)
    atr_bps = atr / bars.close.to_numpy() * 1e4
    return AssetData("synthétique", bars, tabs, atr_bps, fee)


def _windows(data):
    return walk_forward_windows(data.bars.time.iat[0], end=pd.Timestamp("2023-01-01", tz=UTC), is_semesters=2)


def test_grille_du_protocole():
    assert GRID_R0 == (10.0, 50.0, 100.0, 200.0, 500.0)
    assert GRID_H == tuple(range(6, 61, 2)) and len(GRID_H) == 28
    assert GRID_F == (0.75, 0.80, 0.85, 0.90, 0.95)
    assert len(GRID_R0) * len(GRID_H) * len(GRID_F) == 700
    assert (GRID_R0[RE1_INDEX[0]], GRID_H[RE1_INDEX[1]], GRID_F[RE1_INDEX[2]]) == RE1_POINT == (100.0, 26, 0.85)
    assert list(VARIANTS) == ["RE-1 gelée", "Contrôle", "Statique-H", "WFO-H", "Statique-R0", "WFO-R0",
                              "Statique-frontière", "WFO-frontière", "Statique-conjointe", "WFO-conjointe"]


def test_evaluation_is_egale_le_moteur_de_reference(barres_synthetiques, atlas_synthetique):
    data = _asset(barres_synthetiques, atlas_synthetique)
    w = _windows(data)[0]
    ev = evaluate_is(data, w, grid=PETITE)
    assert ev["calmar_r25"].shape == (3, 3, 3)
    first, last = bar_span(data.bars.time, w.is_start, w.is_end)
    for i, j, k in ((0, 0, 0), (1, 1, 1), (2, 2, 2)):
        r0, h, f = PETITE[0][i], PETITE[1][j], PETITE[2][k]
        tab = data.tabs[r0]
        leg, nis, _ = window_thresholds(tab, w.is_start, w.is_end)
        t, s, lv = candidates(tab, leg, nis, f, w.is_start, w.is_end)
        tr = run_trades(data.bars, t, s, h, lv, last=last)
        m = is_metrics(tr, data.bars.close.to_numpy(), data.atr_bps, 5.0, n_years=1.0)
        assert m["n_trades"] > 20 and (tr.exit_bar <= last).all()
        for key in ("n_trades", "esperance_atr", "calmar_r25", "mdd_r25", "pnl_r25"):
            assert ev[key][i, j, k] == m[key], key
        assert ev["leg_p50"][i] == leg and ev["nis_p75"][i] == nis


def test_evaluation_is_ne_lit_aucune_donnee_posterieure_a_l_is(barres_synthetiques, atlas_synthetique):
    data = _asset(barres_synthetiques, atlas_synthetique, seed=1)
    w = _windows(data)[0]
    ev = evaluate_is(data, w, grid=PETITE)
    bars = data.bars.copy()
    after = (bars.time >= w.is_end).to_numpy()
    bars.loc[after, ["open", "high", "low", "close"]] *= 1.3
    tabs = {}
    for r0, tab in data.tabs.items():                         # signaux postérieurs à l'IS altérés
        late = tab.time >= w.is_end
        leg, nis = tab.leg_atr.copy(), tab.nis.copy()
        leg[late] *= 3.0
        nis[late] -= 2.0
        tabs[r0] = type(tab)(tab.t, tab.s, tab.time, leg, nis, tab.retrace, tab.x1, tab.slb, tab.atr_bps)
    atr_bps = data.atr_bps.copy()
    atr_bps[after] *= 2.0
    other = evaluate_is(AssetData("altérée", bars, tabs, atr_bps, 5.0), w, grid=PETITE)
    for key, v in ev.items():
        assert np.array_equal(v, other[key], equal_nan=True), key


def test_branches_ofat_sont_les_axes_de_la_grille_conjointe():
    rng = np.random.default_rng(0)
    shape = (len(GRID_R0), len(GRID_H), len(GRID_F))
    ev = {"esperance_atr": rng.normal(0.1, 0.2, shape), "calmar_r25": rng.normal(0.5, 1.0, shape),
          "mdd_r25": -rng.uniform(0.01, 0.2, shape)}
    i0, j0, k0 = RE1_INDEX
    p, _ = branch_choice(ev, "H")
    assert (p.r0, p.frontier) == (100.0, 0.85)
    from optimization.selection import select
    j, _ = select(ev["esperance_atr"][i0, :, k0], ev["calmar_r25"][i0, :, k0], ev["mdd_r25"][i0, :, k0], (j0,))
    assert p.h == GRID_H[j[0]]
    p, _ = branch_choice(ev, "R0")
    assert (p.h, p.frontier) == (26, 0.85)
    p, _ = branch_choice(ev, "frontiere")
    assert (p.r0, p.h) == (100.0, 26)
    p, _ = branch_choice(ev, "conjointe")
    idx, _ = select(ev["esperance_atr"], ev["calmar_r25"], ev["mdd_r25"], RE1_INDEX)
    assert (p.r0, p.h, p.frontier) == (GRID_R0[idx[0]], GRID_H[idx[1]], GRID_F[idx[2]])


def test_calendriers_statique_wfo_et_references():
    rng = np.random.default_rng(1)
    shape = (len(GRID_R0), len(GRID_H), len(GRID_F))
    evs = [{"esperance_atr": rng.normal(0.1, 0.2, shape), "calmar_r25": rng.normal(0.5, 1.0, shape),
            "mdd_r25": -rng.uniform(0.01, 0.2, shape)} for _ in range(4)]
    re1 = Params(*RE1_POINT)
    for name in ("RE-1 gelée", "Contrôle"):
        sched, thr = variant_schedule(evs, name)
        assert sched == [re1] * 4
    assert variant_schedule(evs, "RE-1 gelée")[1] == "geles" and variant_schedule(evs, "Contrôle")[1] == "fenetre"
    wfo, thr = variant_schedule(evs, "WFO-conjointe")
    assert thr == "fenetre" and wfo == [branch_choice(ev, "conjointe")[0] for ev in evs]
    stat, _ = variant_schedule(evs, "Statique-conjointe")
    assert stat == [wfo[0]] * 4


def test_candidats_oos_aux_parametres_et_seuils_de_leur_semestre(barres_synthetiques, atlas_synthetique):
    data = _asset(barres_synthetiques, atlas_synthetique, seed=2)
    ws = _windows(data)
    assert len(ws) == 2
    sched = [Params(50.0, 40, 0.80), Params(200.0, 6, 0.90)]
    t, s, h, lv, k = oos_candidates(data, ws, sched, "fenetre")
    assert (np.diff(t) > 0).all()
    for w, p in zip(ws, sched):
        sel = k == w.k
        tab = data.tabs[p.r0]
        leg, nis, _ = window_thresholds(tab, w.is_start, w.is_end)
        tt, ss, ll = candidates(tab, leg, nis, p.frontier, w.oos_start, w.oos_end)
        assert np.array_equal(t[sel], tt) and np.array_equal(s[sel], ss) and np.array_equal(lv[sel], ll, equal_nan=True)
        assert (h[sel] == p.h).all()
    t2, _, h2, _, k2 = oos_candidates(data, ws, sched, "geles")    # seuils BTC gelés (RE-1 gelée)
    for w, p in zip(ws, sched):
        tt, _, _ = candidates(data.tabs[p.r0], LEG_ATR_P50_BTC, NIS_Z100_P75_BTC, p.frontier, w.oos_start, w.oos_end)
        assert np.array_equal(t2[k2 == w.k], tt) and (h2[k2 == w.k] == p.h).all()
    with pytest.raises(ValueError, match="seuils"):
        oos_candidates(data, ws, sched, "historique")


def test_une_position_a_cheval_garde_les_regles_de_son_entree(barres_synthetiques):
    """Signal à la fin du semestre A (H = 40) : la position déborde sur B (H = 6), dont les signaux attendent sa
    sortie prévue ; le premier trade de B garde ensuite son propre horizon."""
    bars = barres_synthetiques(40000, seed=5)
    ws = walk_forward_windows(bars.time.iat[0], end=pd.Timestamp("2023-01-01", tz=UTC), is_semesters=2)
    b_start = int(bars.time.searchsorted(ws[1].oos_start))
    t = np.array([b_start - 3, b_start + 5, b_start + 30, b_start + 60], dtype=np.int64)
    n = len(t)
    atlas = pd.DataFrame({"bar_index": t, "timestamp": bars.time.iloc[t].to_numpy(), "direction": np.ones(n, int),
                          "prev_seg_len": np.full(n, 5), "leg_atr": np.full(n, 1.0), "obs_dist_seg_atr": np.full(n, 0.6),
                          "obs_dist_cycle_atr": np.full(n, 0.6), "A_vol": np.ones(n), "peak_bps_vol": np.ones(n),
                          "x1_already_flipped_at_t": np.ones(n, bool), "nis_z_100": np.zeros(n),
                          "atr14_bps": np.full(n, 30.0)})
    atr = bars.close.to_numpy() * 30.0 / 1e4
    tab = signal_table(bars, atlas, atr)
    data = AssetData("synthétique", bars, {r0: tab for r0 in GRID_R0}, atr / bars.close.to_numpy() * 1e4, 5.0)
    sched = [Params(100.0, 40, 0.85), Params(100.0, 6, 0.85)]
    cands = oos_candidates(data, ws, sched, "geles")
    tr = run_oos(data, cands)
    first = tr.iloc[0]
    assert first.signal_bar == b_start - 3 and first.exit_bar - first.entry_bar == 40 and not first.stop
    assert tr.signal_bar.tolist() == [b_start - 3, b_start + 60]            # b + 5 et b + 30 attendent la sortie
    assert tr.iloc[1].exit_bar - tr.iloc[1].entry_bar == 6 and tr.semestre.tolist() == [0, 1]


def test_aucun_decalage_vers_le_futur_dans_optimization():
    for p in (ROOT / "src" / "optimization").glob("*.py"):
        assert "shift(-" not in Path(p).read_text(encoding="utf-8"), p.name
