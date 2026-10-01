"""EXP-D02 — règles de choix en apprentissage (IS).

Règle retenue par le porteur (second GO, 2026-10-01), `select_plateau` :
- cases candidates : configurations admissibles (espérance nette en ATR > 0 et MDD valorisé < 0 sur l'IS) dont le
  Calmar net est > 0 ; un Calmar indéfini (aucun trade, aucun drawdown) n'est jamais choisi ;
- zone : composante connexe de ces cases dans la grille, voisins à ±1 pas sur un seul axe (R0 par rang) ; on retient la
  plus grande (nombre de cases), à égalité celle de plus fort Calmar moyen, puis celle dont la première case vient en
  premier dans l'ordre lexicographique ;
- choix : la case de la zone la plus proche de son centre géométrique (moyenne des indices ; distance euclidienne en pas
  de grille) ; à égalité (à 1e-12 près), la plus proche du point de référence (RE-1) en distance L1, puis l'ordre
  lexicographique ; aucune case candidate : repli sur la référence (paramètres de RE-1, seuils de la fenêtre).
- Pas de bord fictif : rien n'est supposé au-delà de la grille (l'option « voisin absent = 0 » a été rejetée).

Lecture littérale du score de voisinage (`neighbour_mean`, `select`), non retenue : moyenne du Calmar de la case et de
ses voisins immédiats existants, Calmar indéfini compté 0 ; elle favorise une case de bord, moins entourée.
"""
from __future__ import annotations

from collections import deque

import numpy as np


def neighbour_mean(values) -> np.ndarray:
    """Score de voisinage (lecture littérale) : moyenne de la case et de ses voisins existants, NaN compté 0."""
    v = np.asarray(values, dtype=float)
    v = np.where(np.isfinite(v), v, 0.0)
    tot, cnt = v.copy(), np.ones(v.shape)
    for ax in range(v.ndim):
        n = v.shape[ax]
        if n < 2:
            continue
        lo, hi = [slice(None)] * v.ndim, [slice(None)] * v.ndim
        lo[ax], hi[ax] = slice(0, n - 1), slice(1, n)
        lo, hi = tuple(lo), tuple(hi)
        tot[lo] += v[hi]
        cnt[lo] += 1
        tot[hi] += v[lo]
        cnt[hi] += 1
    return tot / cnt


def _admissible(e, c, m) -> np.ndarray:
    with np.errstate(invalid="ignore"):
        return (e > 0) & (m < 0) & np.isfinite(c)


def _closest(cells: np.ndarray, ref: tuple) -> np.ndarray:
    return cells[int(np.argmin(np.abs(cells - np.asarray(ref)).sum(axis=1)))]


def select(esperance, calmar, mdd, ref) -> tuple[tuple[int, ...], dict]:
    """Lecture littérale (non retenue) : score de voisinage maximal parmi les admissibles."""
    e, c, m = (np.asarray(x, dtype=float) for x in (esperance, calmar, mdd))
    ref = tuple(int(i) for i in ref)
    ok = _admissible(e, c, m)
    if not ok.any():
        return ref, {"repli": True, "n_admissibles": 0, "score": np.nan}
    score = neighbour_mean(c)
    best = score[ok].max()
    pick = _closest(np.argwhere(ok & (score == best)), ref)
    return tuple(int(i) for i in pick), {"repli": False, "n_admissibles": int(ok.sum()), "score": float(best)}


def plateau_zones(mask) -> list[np.ndarray]:
    """Composantes connexes (voisins à ±1 pas sur un axe) des cases vraies de `mask`, chacune en tableau d'indices
    (une ligne par case), dans l'ordre de leur première case."""
    mask = np.asarray(mask, dtype=bool)
    seen = np.zeros(mask.shape, dtype=bool)
    zones = []
    for start in map(tuple, np.argwhere(mask)):
        if seen[start]:
            continue
        seen[start] = True
        queue, cells = deque([start]), []
        while queue:
            cur = queue.popleft()
            cells.append(cur)
            for ax in range(mask.ndim):
                for step in (-1, 1):
                    nb = list(cur)
                    nb[ax] += step
                    nb = tuple(nb)
                    if 0 <= nb[ax] < mask.shape[ax] and mask[nb] and not seen[nb]:
                        seen[nb] = True
                        queue.append(nb)
        zones.append(np.array(sorted(cells), dtype=np.int64).reshape(len(cells), mask.ndim))
    return zones


def select_plateau(esperance, calmar, mdd, ref) -> tuple[tuple[int, ...], dict]:
    """Règle retenue : centre de la plus grande zone connexe de cases admissibles à Calmar net > 0."""
    e, c, m = (np.asarray(x, dtype=float) for x in (esperance, calmar, mdd))
    ref = tuple(int(i) for i in ref)
    with np.errstate(invalid="ignore"):
        ok = _admissible(e, c, m) & (c > 0)
    zones = plateau_zones(ok)
    if not zones:
        return ref, {"repli": True, "zone": 0, "n_zones": 0, "n_candidates": 0, "centre": None,
                     "calmar_zone": np.nan}
    means = [float(np.mean(c[tuple(z.T)])) for z in zones]
    best = min(range(len(zones)), key=lambda i: (-len(zones[i]), -means[i], tuple(zones[i][0])))
    z = zones[best]
    centre = z.mean(axis=0)
    d2 = ((z - centre) ** 2).sum(axis=1)
    pick = _closest(z[d2 <= d2.min() + 1e-12], ref)
    return tuple(int(i) for i in pick), {"repli": False, "zone": int(len(z)), "n_zones": len(zones),
                                         "n_candidates": int(ok.sum()), "centre": [float(x) for x in centre],
                                         "calmar_zone": means[best]}
