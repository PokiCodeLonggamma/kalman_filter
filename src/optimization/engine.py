"""EXP-D02 — noyau d'exécution de RE-1 compilé (Numba), identique à `envelope.stop_trades(..., dynamic=False)`.

Mêmes conventions que `stop_trades` et `estimand.stoploss.apply_stop`, dont il reprend les opérations dans le même
ordre (résultats identiques au bit près, contrôle bloquant Gate 0) :
- candidat exécutable si t + 1 < last ; entrée à open[t + 1] ; sortie prévue x = min(t + 1 + h, last) ;
- stop testé sur les barres détenues [t + 1, x − 1], barre d'entrée comprise : niveau = P0 · (1 − side · distance),
  distance = side · (P0 − niveau demandé) / P0 ; exécution au niveau, ou à l'ouverture d'une barre (autre que celle de
  l'entrée) qui ouvre au-delà (gap) ; sinon sortie à open[x] ; niveau NaN : sans stop ;
- une position à la fois ; après une sortie prévue en x, le premier signal admissible est celui de la clôture de
  x − 1, stop touché ou non (cooldown jusqu'à la sortie prévue).

Deux ajouts pour le walk-forward, sans changer ces règles :
- `h` peut varier d'un signal à l'autre : un trade garde jusqu'à sa clôture l'horizon et le stop de son signal ;
- `last` borne la série : fin d'un IS, où tout trade encore ouvert est clos à l'ouverture de la barre `last`.

EXP-D02.1 (porteur, 2026-10-03) — verrou (cooldown) distinct de l'horizon, `lock` :
- après un signal exécuté en t, le suivant n'est admissible qu'à partir de t + `lock`, sortie et stop ignorés ; les
  entrées ne dépendent donc que des signaux et du verrou ; `lock` absent : `lock = h`, règle de D02 ci-dessus ;
- option C du porteur : si l'entrée suivante tombe avant la sortie prévue (h > verrou), elle clôt la position encore
  ouverte à la même ouverture (une position à la fois, levier ≤ 1x) ; le stop est testé jusqu'à cette sortie.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from numba import njit

from estimand.bars import check_no_holdout
from estimand.excursions import BPS
from estimand.stoploss import TRADE_COLUMNS


@njit(cache=True)
def _simulate(op, hi, lo, t, s, h, level, last, lock):
    n = t.shape[0]
    adm = np.empty(n, np.int64)                               # signaux exécutés : verrou seul, sorties ignorées
    m = 0
    libre = -1
    for i in range(n):
        if t[i] < libre:
            continue                                          # verrou : signal ignoré
        adm[m] = i
        m += 1
        libre = t[i] + lock[i]
    sig = np.empty(n, np.int64)
    ent = np.empty(n, np.int64)
    ext = np.empty(n, np.int64)
    side = np.empty(n, np.int64)
    p_in = np.empty(n, np.float64)
    p_out = np.empty(n, np.float64)
    stop = np.zeros(n, np.bool_)
    gap = np.zeros(n, np.bool_)
    ret = np.empty(n, np.float64)
    for k in range(m):
        i = adm[k]
        ti = t[i]
        si = s[i]
        e = ti + 1
        x = ti + 1 + h[i]
        if x > last:
            x = last
        if k + 1 < m and t[adm[k + 1]] + 1 < x:
            x = t[adm[k + 1]] + 1                             # option C : l'entrée suivante clôt la position
        p0 = op[e]
        sortie = x
        prix = op[x]
        touche = False
        au_dela = False
        lv = level[i]
        if lv == lv:                                          # niveau défini (NaN : sans stop)
            dist = si * (p0 - lv) / p0
            niveau = p0 * (1.0 - si * dist)
            for b in range(e, x):
                if (si == 1 and lo[b] <= niveau) or (si == -1 and hi[b] >= niveau):
                    touche = True
                    sortie = b
                    break
            if touche:
                if sortie > e and ((si == 1 and op[sortie] <= niveau) or (si == -1 and op[sortie] >= niveau)):
                    au_dela = True
                    prix = op[sortie]
                else:
                    prix = niveau
        sig[k] = ti
        ent[k] = e
        ext[k] = sortie
        side[k] = si
        p_in[k] = p0
        p_out[k] = prix
        stop[k] = touche
        gap[k] = au_dela
        ret[k] = si * (prix / p0 - 1.0) * BPS
    return sig[:m], ent[:m], ext[:m], side[:m], p_in[:m], p_out[:m], stop[:m], gap[:m], ret[:m]


def prepare_inputs(bars: pd.DataFrame, signal_bar, side, horizon, level=None, last: int | None = None,
                   check_bars: bool = True):
    """Contrôles et filtre de `envelope.stops._candidates`, généralisés : (op, hi, lo, t, s, h, level, last) prêts
    pour `simulate`, restreints aux candidats exécutables (t + 1 < last). `check_bars=False` : réserve 2026 déjà
    vérifiée sur ces barres par l'appelant (boucle de grille)."""
    if check_bars:
        check_no_holdout(bars)
    t = np.asarray(signal_bar, dtype=np.int64)
    s = np.asarray(side, dtype=np.int64)
    h = np.broadcast_to(np.asarray(horizon, dtype=np.int64), t.shape).copy()
    if (h < 1).any():
        raise ValueError("run_trades : horizon ≥ 1 exigé")
    if len(t) and not (np.diff(t) > 0).all():
        raise ValueError("run_trades : signaux non triés ou dupliqués")
    n = len(bars)
    last = n - 1 if last is None else int(last)
    if not 0 < last <= n - 1:
        raise ValueError("run_trades : last hors des barres")
    lv = np.full(len(t), np.nan) if level is None else np.asarray(level, dtype=float)
    ok = t + 1 < last
    t, s, h, lv = t[ok], s[ok], h[ok], lv[ok]
    op = bars["open"].to_numpy(dtype=float)
    if len(t):
        p0 = op[t + 1]
        dist = s * (p0 - lv) / p0
        if not (dist[~np.isnan(dist)] > 0).all():
            raise ValueError("run_trades : niveau du stop à l'entrée ou du mauvais côté")
    return (op, bars["high"].to_numpy(dtype=float), bars["low"].to_numpy(dtype=float),
            np.ascontiguousarray(t), np.ascontiguousarray(s), np.ascontiguousarray(h), np.ascontiguousarray(lv), last)


def _lock(h: np.ndarray, lock) -> np.ndarray:
    if lock is None:
        return h
    if int(lock) != lock or int(lock) < 1:
        raise ValueError("run_trades : verrou entier ≥ 1 exigé")
    return np.full(h.shape, int(lock), dtype=np.int64)


def simulate(op, hi, lo, t, s, h, level, last, lock: int | None = None) -> dict[str, np.ndarray]:
    """Trades d'entrées déjà contrôlées (`prepare_inputs`), sous forme de tableaux, colonnes de `TRADE_COLUMNS` ;
    `lock` : verrou en barres (défaut : l'horizon de chaque signal, règle de D02)."""
    out = _simulate(op, hi, lo, t, s, h, level, last, _lock(h, lock))
    return dict(zip(["signal_bar", "entry_bar", "exit_bar", "side", "entry_price", "exit_price", "stop", "gap",
                     "ret_gross_bps"], out))


def run_trades(bars: pd.DataFrame, signal_bar, side, horizon, level=None, last: int | None = None,
               lock: int | None = None) -> pd.DataFrame:
    """`envelope.stop_trades(bars, signal_bar, side, horizon, level, dynamic=False)`, avec `horizon` scalaire ou un
    par signal, une fin de série `last` (défaut : dernière barre) et un verrou `lock` distinct de l'horizon (défaut :
    l'horizon). Même tableau, mêmes types."""
    args = prepare_inputs(bars, signal_bar, side, horizon, level, last)
    if not len(args[3]):
        _lock(args[5], lock)
        return pd.DataFrame({c: pd.Series(dtype=float) for c in TRADE_COLUMNS})
    return pd.DataFrame(simulate(*args, lock=lock))[TRADE_COLUMNS]


def superseded(trades: pd.DataFrame, horizon) -> np.ndarray:
    """Trades clos par l'entrée suivante (option C) : ni stop ni sortie prévue, sortie à l'ouverture où entre le trade
    suivant. `horizon` : scalaire ou un par trade. Une fin de série (`last`) n'est pas une coupure."""
    tr = trades.reset_index(drop=True)
    h = np.broadcast_to(np.asarray(horizon, dtype=np.int64), (len(tr),))
    x = tr.exit_bar.to_numpy(dtype=np.int64)
    nxt = np.r_[tr.entry_bar.to_numpy(dtype=np.int64)[1:], -1]
    early = x < tr.signal_bar.to_numpy(dtype=np.int64) + 1 + h
    return early & ~tr.stop.to_numpy(dtype=bool) & (x == nxt)
