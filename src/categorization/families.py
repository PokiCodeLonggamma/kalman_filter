"""EXP-B01 — descripteurs causaux dérivés, découpages (quartiles à bornes fixes ou modalités), familles cinématiques
et résumés d'excursion. Aucun seuil n'est optimisé : quartiles de l'univers, médiane de `leg_atr`, seuils physiques
0,50 / 0,85 / 1,00 de `retrace_ratio` fixés avant le calcul (RESEARCH_INSIGHTS.md, §3).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from categorization.excursions import BARRIERS, HORIZONS, barrier_key

#: Les 15 descripteurs causaux de B01 (liste révisée d'A01 + retrace_ratio).
DESCRIPTORS = ["retrace_ratio", "obs_dist_seg_atr", "obs_lag_seg_bars", "x1_already_flipped_at_t", "nis_z_100",
               "nis_z_100_seg_max", "cycle_seg_div_atr", "A_vol", "decel_ratio", "log_R_rel", "leg_atr",
               "prev_seg_len", "saturation", "n_short_seg_48", "run_rank"]

FAMILY_LABELS = {
    "F1": "F1 Essoufflement d'une tendance ample (leg ≥ P50, retrace < 0,50)",
    "F2a": "F2a Retournement intermédiaire, jambe ample (0,50 ≤ retrace < 0,85, leg ≥ P50)",
    "F2b": "F2b Retournement intermédiaire, jambe courte (0,50 ≤ retrace < 0,85, leg < P50)",
    "F3": "F3 Sortie de range (leg < P50, retrace ≥ 0,85)",
    "F4": "F4 Climax, grand segment ravalé (leg ≥ P50, retrace ≥ 0,85)",
    "F5": "F5 Résidu : jambe courte peu retracée (leg < P50, retrace < 0,50)",
}


def add_derived(a: pd.DataFrame) -> pd.DataFrame:
    """Ajoute `retrace_ratio`, `cycle_seg_div_atr` et `decel_ratio`, fonctions des seules colonnes causales d'A01."""
    out = a.copy()
    out["retrace_ratio"] = a.obs_dist_seg_atr / a.leg_atr
    out["cycle_seg_div_atr"] = a.obs_dist_cycle_atr - a.obs_dist_seg_atr
    out["decel_ratio"] = a.A_vol / a.peak_bps_vol
    return out


def bin_descriptor(x: pd.Series, name: str) -> tuple[np.ndarray, list[str], dict[str, str]]:
    """(classe de chaque signal, ordre des classes, bornes lisibles). Quartiles à bornes fixes sur l'univers ;
    modalités pour les descripteurs binaires, discrets ou massés en 0."""
    x = pd.Series(x).reset_index(drop=True)
    if name == "x1_already_flipped_at_t":
        v = x.astype(bool).to_numpy()
        return np.where(v, "Vrai", "Faux"), ["Faux", "Vrai"], {"Faux": "x1 encore opposé", "Vrai": "x1 déjà retourné"}
    if name == "run_rank":
        return np.where(x > 1, ">1", "1"), ["1", ">1"], {"1": "rang 1 (flip)", ">1": "répétition"}
    if name == "n_short_seg_48":
        return np.where(x >= 1, "≥1", "0"), ["0", "≥1"], {"0": "aucun segment court", "≥1": "au moins un"}
    if name == "cycle_seg_div_atr":
        return np.where(x > 1e-12, ">0", "0"), ["0", ">0"], {"0": "le segment porte l'extremum du cycle",
                                                             ">0": "plus bas plus haut / plus haut plus bas"}
    q, edges = pd.qcut(x, 4, labels=False, retbins=True, duplicates="drop")
    order = [f"Q{i + 1}" for i in range(len(edges) - 1)]
    lab = np.array([order[int(v)] for v in q])
    bounds = {order[i]: f"[{edges[i]:.3g} ; {edges[i + 1]:.3g}]" for i in range(len(order))}
    return lab, order, bounds


def assign_families(d: pd.DataFrame, leg_p50: float) -> np.ndarray:
    """Partition exhaustive et exclusive F1 … F5 sur `leg_atr` (coupé à leg_p50) et `retrace_ratio`."""
    r, big = d.retrace_ratio.to_numpy(), d.leg_atr.to_numpy() >= leg_p50
    fam = np.full(len(d), "F5", dtype=object)
    fam[big & (r < 0.5)] = "F1"
    fam[big & (r >= 0.5) & (r < 0.85)] = "F2a"
    fam[~big & (r >= 0.5) & (r < 0.85)] = "F2b"
    fam[~big & (r >= 0.85)] = "F3"
    fam[big & (r >= 0.85)] = "F4"
    return fam


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """Intervalle de Wilson à 95 % d'une proportion k / n (NaN si n = 0)."""
    if n == 0:
        return np.nan, np.nan
    p = k / n
    den = 1 + z * z / n
    mid = (p + z * z / (2 * n)) / den
    half = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return mid - half, mid + half


def summarize(ex: pd.DataFrame, mask: np.ndarray) -> dict:
    """Résumé d'excursion d'un sous-ensemble : médianes par horizon, part MFE > MAE, taux aux barrières."""
    mask = np.asarray(mask, dtype=bool)
    out = {"n": int(mask.sum())}
    for H in HORIZONS:
        mfe = ex[f"mfe_{H}_atr"].to_numpy()[mask]
        ok = ~np.isnan(mfe)
        out[f"n_{H}"] = int(ok.sum())
        for k in ("mfe", "mae", "asym", "ret"):
            v = ex[f"{k}_{H}_atr"].to_numpy()[mask][ok]
            out[f"{k}_{H}_p50"] = float(np.median(v)) if len(v) else np.nan
        g = ex[f"mfe_gt_mae_{H}"].to_numpy()[mask][ok]
        out[f"pct_mfe_gt_mae_{H}"] = float(g.mean()) if len(g) else np.nan
        out[f"pct_mfe_gt_mae_{H}_lo"], out[f"pct_mfe_gt_mae_{H}_hi"] = wilson(int(g.sum()), len(g))
    for b in BARRIERS:
        key = barrier_key(b)
        o = ex[f"barrier_{key}_outcome"].to_numpy()[mask]
        win, loss, amb, to = ((o == s).sum() for s in ("win", "loss", "ambiguous", "timeout"))
        res, tot = win + loss + amb, win + loss + amb + to
        out[f"win_strict_{key}"] = win / res if res else np.nan
        out[f"win_strict_{key}_lo"], out[f"win_strict_{key}_hi"] = wilson(int(win), int(res))
        out[f"win_all_{key}"] = win / tot if tot else np.nan
        out[f"amb_{key}"] = amb / tot if tot else np.nan
        out[f"timeout_{key}"] = to / tot if tot else np.nan
    return out


def timing_drift(ret, direction, stat: str = "median") -> tuple[float, float]:
    """Décomposition sans placebo d'un rendement orienté `ret` (> 0 : dans le sens du signal). Avec m_L et m_S sa médiane
    (`stat="median"`) ou sa moyenne (`stat="mean"`) après les Long et après les Short : timing = (m_L + m_S) / 2,
    dérive = (m_L − m_S) / 2. NaN ignorés ; (NaN, NaN) si un sens est vide."""
    agg = {"median": np.nanmedian, "mean": np.nanmean}[stat]
    ret, direction = np.asarray(ret, dtype=float), np.asarray(direction)
    long_, short = ret[direction == 1], ret[direction == -1]
    if np.isnan(long_).all() or np.isnan(short).all():
        return np.nan, np.nan
    m_l, m_s = agg(long_), agg(short)
    return float((m_l + m_s) / 2), float((m_l - m_s) / 2)


def tail_sum(v, q: float = 10) -> float:
    """P(100 − q) + P(q), NaN ignorés : > 0 quand la queue droite s'étend plus loin que la queue gauche."""
    v = np.asarray(v, dtype=float)
    v = v[~np.isnan(v)]
    return float(np.percentile(v, 100 - q) + np.percentile(v, q)) if len(v) else np.nan


def cluster_bootstrap(stat, clusters, n_boot: int = 2000, seed: int = 0) -> np.ndarray:
    """Tirages bootstrap de `stat(positions)`. Les grappes (ex. mois civils) sont tirées avec remise, chacune avec toutes
    ses observations : la dépendance entre fenêtres qui se chevauchent dans une même grappe est conservée.
    Renvoie un tableau (n_boot, k) quand `stat` renvoie k valeurs."""
    clusters = np.asarray(clusters)
    groups = [np.flatnonzero(clusters == c) for c in np.unique(clusters)]
    rng = np.random.default_rng(seed)
    return np.array([stat(np.concatenate([groups[i] for i in rng.integers(0, len(groups), len(groups))]))
                     for _ in range(n_boot)])
