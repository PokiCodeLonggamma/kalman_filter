"""EXP-D02 — règle de choix en apprentissage (IS), fixée par le porteur avant toute mesure (2026-10-01).

- Admissible : espérance nette en ATR > 0 et MDD valorisé < 0 sur l'IS (Calmar défini).
- Score : moyenne du Calmar net de la configuration et de ses voisins immédiats dans la grille (±1 pas sur un seul
  axe ; R0 par rang). Un voisin inadmissible compte pour sa propre valeur ; un Calmar indéfini compte pour 0.
- Choix : score maximal parmi les admissibles ; à égalité, le plus proche du point de référence (RE-1) en pas de
  grille (distance L1), puis l'ordre lexicographique des indices ; aucun admissible : repli sur la référence.
- Bord de grille (`edge`) : « voisins_existants », lecture littérale, moyenne des seuls voisins qui existent ; « zero »,
  voisin absent compté 0 (le bord est pénalisé). Choix à trancher par le porteur avant la grille (rapport de Gate 0).
"""
from __future__ import annotations

import numpy as np

EDGES = ("voisins_existants", "zero")


def neighbour_mean(values, edge: str = "voisins_existants") -> np.ndarray:
    """Score de voisinage de chaque case d'une grille de Calmar (1 à 3 dimensions)."""
    if edge not in EDGES:
        raise ValueError(f"neighbour_mean : bord de grille inconnu {edge!r}")
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
    return tot / cnt if edge == "voisins_existants" else tot / (1 + 2 * v.ndim)


def select(esperance, calmar, mdd, ref, edge: str = "voisins_existants") -> tuple[tuple[int, ...], dict]:
    """(indices de la configuration choisie, informations) sur des grilles de même forme."""
    e, c, m = (np.asarray(x, dtype=float) for x in (esperance, calmar, mdd))
    ref = tuple(int(i) for i in ref)
    with np.errstate(invalid="ignore"):
        ok = (e > 0) & (m < 0) & np.isfinite(c)
    if not ok.any():
        return ref, {"repli": True, "n_admissibles": 0, "score": np.nan}
    score = neighbour_mean(c, edge)
    best = score[ok].max()
    cand = np.argwhere(ok & (score == best))
    pick = cand[int(np.argmin(np.abs(cand - np.asarray(ref)).sum(axis=1)))]
    return tuple(int(i) for i in pick), {"repli": False, "n_admissibles": int(ok.sum()), "score": float(best)}
