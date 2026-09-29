"""EXP-C02 — stop-loss en prix sur l'enveloppe à horizon fixe, en exécution séquentielle.

Le niveau du stop est fixé à l'entrée ; il ne lit que les barres ≤ t et open[t + 1], le prix d'entrée :
- SL-A : open[t + 1] − side · k · ATR14(t) ;
- SL-B : extremum du segment qualifiant (plus bas des `low` pour un Long, plus haut des `high` pour un Short) sur
  l'horizon segment [t − prev_seg_len, t] d'`anatomy.causal`, celui de `obs_dist_seg_atr` et donc de `retrace_ratio`,
  écarté de delta · ATR14(t) ; jamais à moins de `floor` · ATR14(t) de open[t + 1] (entrée en gap au-delà de
  l'extremum).

Exécution : `estimand.stoploss.apply_stop` (copie certifiée #KAKALMAN), inchangé. Il reçoit pour chaque trade la
distance relative side · (open[t + 1] − niveau) / open[t + 1] et reconstruit niveau = P0 · (1 − side · distance),
élément par élément. Le stop est testé sur les barres détenues [t + 1, t + H], barre d'entrée comprise ; sortie au
niveau du stop, ou à l'ouverture d'une barre qui ouvre au-delà (gap) ; sinon sortie à open[t + 1 + H], comme
`time_stop_trades`.

Deux lectures séquentielles (`stop_trades`) :
- entrées figées (`dynamic=False`) : les trades de la course sans stop ; seule leur sortie change. C'est une règle
  causale de cooldown : après un stop, la position reste à plat jusqu'à la sortie prévue t + 1 + H ;
- séquentiel dynamique (`dynamic=True`) : un stop touché pendant la barre b libère la position ; le premier signal
  admissible est celui de la clôture de b (convention de `simulate_strategy` après un stop). Une sortie à horizon
  libère la position à la clôture de t + H, comme dans `time_stop_trades`.

Moteur de régimes (EXP-C02bis) : `route_levels` donne à chaque signal le niveau de stop de l'enveloppe de sa
sous-famille, connue à t (`rule_levels` : None = sans stop, ("SL-A", k), ("SL-B", delta)). Un niveau NaN signifie
« sans stop » pour ce signal ; `apply_stop` ne le touche jamais (comparaisons IEEE fausses).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from estimand.bars import check_no_holdout
from estimand.stoploss import TRADE_COLUMNS, apply_stop


def _entry_open(bars: pd.DataFrame, signal_bar) -> np.ndarray:
    return bars["open"].to_numpy(dtype=float)[np.asarray(signal_bar, dtype=np.int64) + 1]


def atr_stop_levels(bars: pd.DataFrame, signal_bar, side, atr, k: float) -> np.ndarray:
    """SL-A : open[t + 1] − side · k · ATR14(t). `atr` : ATR14(t) en prix, un par signal."""
    s = np.asarray(side, dtype=np.int64)
    return _entry_open(bars, signal_bar) - s * float(k) * np.asarray(atr, dtype=float)


def segment_extremum(bars: pd.DataFrame, signal_bar, side, seg_len) -> np.ndarray:
    """Plus bas des `low` (Long) ou plus haut des `high` (Short) sur [t − seg_len, t], bornes incluses."""
    lo, hi = bars["low"].to_numpy(dtype=float), bars["high"].to_numpy(dtype=float)
    t = np.asarray(signal_bar, dtype=np.int64)
    s = np.asarray(side, dtype=np.int64)
    n = np.asarray(seg_len, dtype=np.int64)
    if (n < 0).any() or (t - n < 0).any() or (t >= len(lo)).any():
        raise ValueError("segment_extremum : segment hors des barres")
    return np.array([lo[a - m:a + 1].min() if d == 1 else hi[a - m:a + 1].max() for a, d, m in zip(t, s, n)],
                    dtype=float)


def structural_stop_levels(bars: pd.DataFrame, signal_bar, side, atr, seg_len, delta: float,
                           floor: float = 0.25) -> np.ndarray:
    """SL-B : extremum du segment qualifiant ∓ delta · ATR14(t), au moins à `floor` · ATR14(t) de open[t + 1]."""
    s = np.asarray(side, dtype=np.int64)
    a = np.asarray(atr, dtype=float)
    p0 = _entry_open(bars, signal_bar)
    level = segment_extremum(bars, signal_bar, side, seg_len) - s * float(delta) * a
    return np.where(s == 1, np.minimum(level, p0 - floor * a), np.maximum(level, p0 + floor * a))


def stop_distance(bars: pd.DataFrame, signal_bar, side, level) -> np.ndarray:
    """Distance relative side · (open[t + 1] − niveau) / open[t + 1] : argument `stop` d'`apply_stop`."""
    p0 = _entry_open(bars, signal_bar)
    return np.asarray(side, dtype=np.int64) * (p0 - np.asarray(level, dtype=float)) / p0


def rule_levels(bars: pd.DataFrame, signal_bar, side, atr, seg_len, rule, floor: float = 0.25) -> np.ndarray:
    """Niveau de stop d'une règle pour chaque signal : None (sans stop : NaN), ("SL-A", k) ou ("SL-B", delta)."""
    if rule is None:
        return np.full(len(np.asarray(signal_bar)), np.nan)
    kind, p = rule
    if kind == "SL-A":
        return atr_stop_levels(bars, signal_bar, side, atr, p)
    if kind == "SL-B":
        return structural_stop_levels(bars, signal_bar, side, atr, seg_len, p, floor)
    raise ValueError(f"rule_levels : règle inconnue {rule!r}")


def route_levels(bars: pd.DataFrame, signal_bar, side, atr, seg_len, family, rules: dict,
                 floor: float = 0.25) -> np.ndarray:
    """Moteur de régimes : chaque signal reçoit le niveau de stop de l'enveloppe de sa sous-famille (`rules` :
    sous-famille → règle de `rule_levels`). Une sous-famille sans enveloppe déclarée est une erreur."""
    family = np.asarray(family)
    missing = sorted(set(np.unique(family)) - set(rules))
    if missing:
        raise ValueError(f"route_levels : sous-familles sans enveloppe {missing}")
    t, s, a, n = (np.asarray(v) for v in (signal_bar, side, atr, seg_len))
    out = np.full(len(family), np.nan)
    for fam, rule in rules.items():
        sel = family == fam
        if sel.any():
            out[sel] = rule_levels(bars, t[sel], s[sel], a[sel], n[sel], rule, floor)
    return out


def stop_trades(bars: pd.DataFrame, signal_bar, side, horizon: int, level=None, dynamic: bool = True) -> pd.DataFrame:
    """Trades exécutés un à la fois, sortie à horizon fixe `horizon`, stop au `level` de chaque signal candidat (prix,
    aligné sur `signal_bar` ; None : sans stop ; NaN : sans stop pour ce signal). `dynamic` : lecture séquentielle (en
    tête de module). Chaque candidat est exécuté une fois, trade par trade ; la sélection séquentielle vient ensuite."""
    check_no_holdout(bars)
    if int(horizon) < 1:
        raise ValueError("stop_trades : horizon ≥ 1 exigé")
    t = np.asarray(signal_bar, dtype=np.int64)
    s = np.asarray(side, dtype=np.int64)
    if len(t) and not (np.diff(t) > 0).all():
        raise ValueError("stop_trades : signaux non triés ou dupliqués")
    last = len(bars) - 1
    ok = t + 1 < last                                         # au moins une barre détenue avant la fin de 2025
    t, s = t[ok], s[ok]
    if not len(t):
        return pd.DataFrame({c: pd.Series(dtype=float) for c in TRADE_COLUMNS})
    e, x = t + 1, np.minimum(t + 1 + int(horizon), last)
    dist = None
    if level is not None:
        dist = stop_distance(bars, t, s, np.asarray(level, dtype=float)[ok])
        if not (dist[~np.isnan(dist)] > 0).all():
            raise ValueError("stop_trades : niveau du stop à l'entrée ou du mauvais côté")
    with np.errstate(invalid="ignore"):
        out = apply_stop(bars, e, x, s, dist)
    stopped = out["stop"].to_numpy(dtype=bool) & bool(dynamic)
    libre_apres = np.where(stopped, out["exit_bar"].to_numpy(), x - 1)   # première barre de signal admissible
    keep, libre = [], -1
    for i, ti in enumerate(t):
        if ti < libre:
            continue                                          # position ouverte : signal ignoré
        keep.append(i)
        libre = libre_apres[i]
    res = out.iloc[keep].reset_index(drop=True)
    res["signal_bar"] = t[keep]
    return res[TRADE_COLUMNS]
