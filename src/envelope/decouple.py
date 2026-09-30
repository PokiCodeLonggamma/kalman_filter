"""EXP-D01.6 — découplage de la sortie et du verrouillage ; sortie forcée en fin de séance.

Deux variantes de `stop_trades(..., dynamic=False)`, l'exécution de RE-1, qui n'est pas modifiée :
- `lock_trades` : la sortie reste à `horizon` barres ou au stop, mais la position suivante ne s'ouvre que sur un signal
  ≥ t + `lock`. Le verrouillage est compté depuis le signal, comme le cooldown de RE-1 : `lock == horizon` redonne
  `stop_trades(..., dynamic=False)` trade par trade ; `lock < horizon` est refusé (deux positions à la fois).
- `session_close_trades` : une position encore ouverte à la clôture de la dernière barre de sa séance sort au close de
  cette barre, avant l'écart d'ouverture suivant. Dernière barre de séance = barre suivie d'un intervalle de plus de
  30 min (nuit, week-end, fête), ou dernière barre de la série ; définition de `session_first` de D01 bis. Le stop reste
  testé sur les barres détenues, barre d'entrée comprise, par `apply_stop`.
  Convention des colonnes pour une sortie de fin de séance : `exit_bar` = barre suivante (première barre de la séance
  suivante), comme une sortie à horizon exécutée à son ouverture, et `exit_price` = close de la dernière barre de
  séance ; `session_exit` = True. Les métriques existantes (durée, capital valorisé, drawdown) s'appliquent telles
  quelles ; la durée calendaire se lit sur la clôture de la dernière barre (`exit_bar − 1`).
  Verrouillage : `release="lock"` garde les entrées de RE-1 (position verrouillée jusqu'à t + horizon, lecture sur
  entrées figées) ; `release="session"` libère la position à la clôture de la séance, après une sortie de fin de séance
  comme après un stop : le signal de la dernière barre est admissible (entrée à l'ouverture de la séance suivante).
Candidats et exécution identiques à `stop_trades` (`_candidates`, `estimand.stoploss.apply_stop`).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from envelope.stops import _candidates, _sequential
from estimand.excursions import BPS
from estimand.stoploss import TRADE_COLUMNS, apply_stop

SESSION_COLUMNS = TRADE_COLUMNS + ["session_exit"]


def _empty(columns) -> pd.DataFrame:
    return pd.DataFrame({c: pd.Series(dtype=float) for c in columns})


def lock_trades(bars: pd.DataFrame, signal_bar, side, horizon: int, lock: int, level=None) -> pd.DataFrame:
    """Trades de `stop_trades(..., dynamic=False)` avec un verrouillage `lock` distinct de l'horizon de sortie : après un
    signal exécuté en t, le signal suivant n'est admissible qu'à partir de t + `lock` (sortie inchangée)."""
    if int(lock) < int(horizon):
        raise ValueError("lock_trades : verrouillage plus court que l'horizon (deux positions à la fois)")
    ok, t, s, e, x, dist = _candidates(bars, signal_bar, side, horizon, level, "lock_trades")
    if not len(t):
        return _empty(TRADE_COLUMNS)
    with np.errstate(invalid="ignore"):
        out = apply_stop(bars, e, x, s, dist)
    keep = _sequential(t, np.minimum(t + int(lock), len(bars) - 2))      # lock == horizon : x − 1 de stop_trades
    res = out.iloc[keep].reset_index(drop=True)
    res["signal_bar"] = t[keep]
    return res[TRADE_COLUMNS]


def session_last_bar(bars: pd.DataFrame) -> np.ndarray:
    """Pour chaque barre, l'indice de la dernière barre de sa séance (barre suivie d'un intervalle de plus de 30 min, ou
    dernière barre de la série)."""
    step = bars.time.diff().to_numpy()
    first = np.r_[False, step[1:] > np.timedelta64(30, "m")]
    ends = np.r_[np.flatnonzero(first) - 1, len(bars) - 1]
    return ends[np.searchsorted(ends, np.arange(len(bars)))]


def session_close_trades(bars: pd.DataFrame, signal_bar, side, horizon: int, level=None,
                         release: str = "lock") -> pd.DataFrame:
    """Trades de `stop_trades(..., dynamic=False)`, avec sortie forcée au close de la dernière barre de la séance
    d'entrée quand la sortie prévue tomberait au-delà (règle et conventions en tête de module)."""
    if release not in ("lock", "session"):
        raise ValueError(f"session_close_trades : release inconnu {release!r}")
    ok, t, s, e, x, dist = _candidates(bars, signal_bar, side, horizon, level, "session_close_trades")
    if not len(t):
        return _empty(SESSION_COLUMNS)
    end = session_last_bar(bars)[e]                                   # dernière barre de la séance d'entrée
    forced = x > end                                                  # sortie prévue après la clôture de la séance
    with np.errstate(invalid="ignore"):
        out = apply_stop(bars, e, np.where(forced, end + 1, x), s, dist)   # stop testé sur [e, fin de séance]
    sess = forced & ~out["stop"].to_numpy(dtype=bool)
    if sess.any():
        px = bars["close"].to_numpy(dtype=float)[end[sess]]
        out.loc[sess, "exit_price"] = px
        out.loc[sess, "ret_gross_bps"] = s[sess] * (px / out["entry_price"].to_numpy(dtype=float)[sess] - 1.0) * BPS
    out["session_exit"] = sess
    libre_apres = x - 1 if release == "lock" else np.minimum(x - 1, end)
    keep = _sequential(t, libre_apres)
    res = out.iloc[keep].reset_index(drop=True)
    res["signal_bar"] = t[keep]
    return res[SESSION_COLUMNS]
