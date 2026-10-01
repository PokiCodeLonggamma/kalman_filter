"""EXP-D02 — walk-forward de RE-1 : grille du protocole, évaluation d'un IS, choix par branche, calendriers Statique et
WFO, séries hors échantillon (protocole du porteur, 2026-10-01).

- Grille : R0 ∈ {10, 50, 100, 200, 500}, H de 6 à 60 au pas de 2 (cooldown = H), frontière de 0,75 à 0,95 au pas de
  0,05 ; 700 combinaisons. Les branches OFAT sont les axes de cette grille passant par RE-1 (100, 26, 0,85).
- Évaluation d'un IS (`evaluate_is`) : pour chaque R0, seuils de population réestimés sur les signaux de l'IS ;
  candidats de l'IS ; trades clos au plus tard à l'ouverture de la dernière barre de l'IS (aucune barre postérieure) ;
  métriques de `objective.is_metrics` au coût de l'actif, annualisées sur la durée de l'IS.
- Choix (`branch_choice`) : règle de `selection.select` sur la grille de la branche, référence RE-1.
- Calendriers (`variant_schedule`) : RE-1 gelée et Contrôle aux paramètres de RE-1 (seuils BTC gelés ou réestimés) ;
  Statique = choix de l'IS du premier semestre, gardé sur tout l'OOS ; WFO = choix de chaque IS.
- Hors échantillon (`oos_candidates`, `run_oos`) : candidats de chaque semestre aux paramètres et aux seuils de ce
  semestre, réunis en une seule course (capital continu) ; une position à cheval sur deux semestres garde l'horizon
  et le stop de son signal ; un trade ouvert le 2025-12-31 est clos à la dernière barre de 2025.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from estimand.bars import check_no_holdout
from optimization.engine import prepare_inputs, run_trades, simulate
from optimization.objective import is_metrics
from optimization.selection import select
from optimization.universe import candidates, window_thresholds
from optimization.windows import Window, bar_span
from strategy import LEG_ATR_P50_BTC, NIS_Z100_P75_BTC, RISK_BPS

GRID_R0 = (10.0, 50.0, 100.0, 200.0, 500.0)
GRID_H = tuple(range(6, 61, 2))
GRID_F = (0.75, 0.80, 0.85, 0.90, 0.95)
GRID = (GRID_R0, GRID_H, GRID_F)
RE1_POINT = (100.0, 26, 0.85)
RE1_INDEX = (GRID_R0.index(100.0), GRID_H.index(26), GRID_F.index(0.85))
METRICS = ("n_trades", "esperance_atr", "pnl_r25", "mdd_r25", "calmar_r25")
THRESHOLDS = ("fenetre", "geles")

#: nom → (branche, mode, seuils) ; « fenetre » : seuils réestimés sur l'IS de chaque semestre ; « geles » : BTC.
VARIANTS = {
    "RE-1 gelée": ("re1", "fixe", "geles"),
    "Contrôle": ("re1", "fixe", "fenetre"),
    "Statique-H": ("H", "statique", "fenetre"),
    "WFO-H": ("H", "wfo", "fenetre"),
    "Statique-R0": ("R0", "statique", "fenetre"),
    "WFO-R0": ("R0", "wfo", "fenetre"),
    "Statique-frontière": ("frontiere", "statique", "fenetre"),
    "WFO-frontière": ("frontiere", "wfo", "fenetre"),
    "Statique-conjointe": ("conjointe", "statique", "fenetre"),
    "WFO-conjointe": ("conjointe", "wfo", "fenetre"),
}


@dataclass(frozen=True)
class Params:
    r0: float
    h: int
    frontier: float


@dataclass
class AssetData:
    """Un actif : barres (réserve 2026 vérifiée), une table de signaux par R0, ATR14 en bps par barre, coût."""
    name: str
    bars: pd.DataFrame
    tabs: dict
    atr_bps: np.ndarray
    fee: float

    def __post_init__(self):
        check_no_holdout(self.bars)
        if len(self.atr_bps) != len(self.bars):
            raise ValueError("AssetData : ATR et barres de longueurs différentes")


def _is_years(w: Window) -> float:
    return ((w.is_end.year - w.is_start.year) * 12 + (w.is_end.month - w.is_start.month)) / 12.0


def evaluate_is(data: AssetData, w: Window, grid=GRID, risk_bps: float = RISK_BPS) -> dict[str, np.ndarray]:
    """Métriques de chaque configuration (R0, H, frontière) de la grille sur l'IS de la fenêtre `w`, et seuils de
    population de l'IS pour chaque R0."""
    r0s, hs, fs = grid
    shape = (len(r0s), len(hs), len(fs))
    out = {k: np.full(shape, np.nan) for k in METRICS}
    out.update({k: np.full(len(r0s), np.nan) for k in ("leg_p50", "nis_p75", "n_signaux")})
    _, last = bar_span(data.bars.time, w.is_start, w.is_end)
    close = data.bars.close.to_numpy(dtype=float)
    ny = _is_years(w)
    for i, r0 in enumerate(r0s):
        tab = data.tabs[r0]
        leg, nis, nsig = window_thresholds(tab, w.is_start, w.is_end)
        out["leg_p50"][i], out["nis_p75"][i], out["n_signaux"][i] = leg, nis, nsig
        for k, f in enumerate(fs):
            t, s, lv = candidates(tab, leg, nis, f, w.is_start, w.is_end)
            op, hi, lo, t, s, _, lv, last_ = prepare_inputs(data.bars, t, s, 1, lv, last, check_bars=False)
            for j, h in enumerate(hs):
                res = simulate(op, hi, lo, t, s, np.full(len(t), h, dtype=np.int64), lv, last_)
                m = is_metrics(res, close, data.atr_bps, data.fee, risk_bps, ny)
                for key in METRICS:
                    out[key][i, j, k] = m[key]
    return out


def _view(branch: str):
    i0, j0, k0 = RE1_INDEX
    views = {"H": ((i0, slice(None), k0), (j0,), 1), "R0": ((slice(None), j0, k0), (i0,), 0),
             "frontiere": ((i0, j0, slice(None)), (k0,), 2), "conjointe": ((slice(None),) * 3, RE1_INDEX, None)}
    if branch not in views:
        raise ValueError(f"branche inconnue {branch!r}")
    return views[branch]


def branch_choice(ev: dict, branch: str, edge: str = "voisins_existants") -> tuple[Params, dict]:
    """Configuration choisie sur la grille d'une branche (« H », « R0 », « frontiere », « conjointe »)."""
    sl, ref, axis = _view(branch)
    idx, info = select(ev["esperance_atr"][sl], ev["calmar_r25"][sl], ev["mdd_r25"][sl], ref, edge)
    full = list(RE1_INDEX)
    if axis is None:
        full = list(idx)
    else:
        full[axis] = idx[0]
    return Params(GRID_R0[full[0]], GRID_H[full[1]], GRID_F[full[2]]), dict(info, index=tuple(full))


def variant_schedule(evs: list[dict], name: str, edge: str = "voisins_existants") -> tuple[list[Params], str]:
    """(paramètres de chaque semestre, politique de seuils) d'une des 10 séries comparées."""
    branch, mode, thresholds = VARIANTS[name]
    n = len(evs)
    if branch == "re1":
        return [Params(*RE1_POINT)] * n, thresholds
    if mode == "statique":
        return [branch_choice(evs[0], branch, edge)[0]] * n, thresholds
    return [branch_choice(ev, branch, edge)[0] for ev in evs], thresholds


def oos_candidates(data: AssetData, windows: list[Window], schedule: list[Params], thresholds: str):
    """(barres, sens, horizons, niveaux de stop, semestre) des candidats hors échantillon, triés."""
    if thresholds not in THRESHOLDS:
        raise ValueError(f"oos_candidates : politique de seuils inconnue {thresholds!r}")
    parts = []
    for w, p in zip(windows, schedule, strict=True):
        tab = data.tabs[p.r0]
        if thresholds == "fenetre":
            leg, nis, _ = window_thresholds(tab, w.is_start, w.is_end)
        else:
            leg, nis = LEG_ATR_P50_BTC, NIS_Z100_P75_BTC
        t, s, lv = candidates(tab, leg, nis, p.frontier, w.oos_start, w.oos_end)
        parts.append((t, s, np.full(len(t), p.h, dtype=np.int64), lv, np.full(len(t), w.k, dtype=np.int64)))
    t, s, h, lv, k = (np.concatenate(c) for c in zip(*parts))
    if len(t) and not (np.diff(t) > 0).all():
        raise ValueError("oos_candidates : signaux non triés ou dupliqués")
    return t, s, h, lv, k


def run_oos(data: AssetData, cands) -> pd.DataFrame:
    """Une seule course hors échantillon (capital continu) ; colonne `semestre` : fenêtre du signal."""
    t, s, h, lv, k = cands
    tr = run_trades(data.bars, t, s, h, lv)
    tr["semestre"] = pd.Series(k, index=t).reindex(tr.signal_bar.to_numpy()).to_numpy()
    return tr
