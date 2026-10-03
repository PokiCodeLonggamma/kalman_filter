"""EXP-D03.1 — viabilité et sécurité de RE-1 (porteur, 2026-10-03), sans toucher au moteur :

- `nearest_levels(side, *levels)` : parmi plusieurs niveaux de stop d'un même trade, le plus proche de l'entrée (le plus
  haut pour un Long, le plus bas pour un Short) ; un niveau NaN est ignoré, tous NaN : sans stop. Sert à greffer un stop
  catastrophe (SL-A k · ATR) sur les règles de RE-1 : le premier touché sort.
- `slip_stops(trades, atr_bps, k, mask)` : les trades sortis sur stop sont exécutés k · ATR14(t) plus loin ; rendement
  brut et prix de sortie dégradés d'autant, les autres trades inchangés ; `mask` restreint aux trades choisis.
- `delayed_trades(bars, signal_bar, side, horizon, level, delay)` : chaque signal exécuté `delay` barres plus tard
  (entrée à open[t + 1 + delay], même horizon, même niveau de stop, même verrou relatif : la population de RE-1 est
  gardée). Si le niveau est déjà franchi à la nouvelle ouverture, le trade sort aussitôt à son prix d'entrée (brut nul,
  `stop` et `gap` vrais). `signal_bar` reste la barre du signal t (taille et ATR lus à t).
"""
from __future__ import annotations

import warnings

import numpy as np
import pandas as pd

from estimand.excursions import BPS
from optimization.engine import run_trades


def nearest_levels(side, *levels) -> np.ndarray:
    """Niveau de stop le plus proche de l'entrée parmi `levels` (prix, un par trade)."""
    s = np.asarray(side, dtype=np.int64)
    stack = np.vstack([np.asarray(lv, dtype=float) for lv in levels])
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)          # colonne entièrement NaN : sans stop
        return np.where(s == 1, np.nanmax(stack, axis=0), np.nanmin(stack, axis=0))


def slip_stops(trades: pd.DataFrame, atr_bps, k: float, mask=None) -> pd.DataFrame:
    """Trades sortis sur stop exécutés `k` · ATR14(t) plus loin (en bps du prix d'entrée)."""
    tr = trades.copy()
    hit = tr.stop.to_numpy(dtype=bool).copy()
    if mask is not None:
        hit &= np.asarray(mask, dtype=bool)
    if not hit.any() or k == 0:
        return tr
    a = np.asarray(atr_bps, dtype=float)[tr.signal_bar.to_numpy(dtype=np.int64)]
    ret = tr.ret_gross_bps.to_numpy(dtype=float).copy()
    ret[hit] -= float(k) * a[hit]
    p0, side = tr.entry_price.to_numpy(dtype=float), tr.side.to_numpy(dtype=np.int64)
    out = tr.exit_price.to_numpy(dtype=float).copy()
    out[hit] = p0[hit] * (1.0 + side[hit] * ret[hit] / BPS)
    tr["ret_gross_bps"], tr["exit_price"] = ret, out
    return tr


def delayed_trades(bars: pd.DataFrame, signal_bar, side, horizon, level=None, delay: int = 1,
                   last: int | None = None) -> pd.DataFrame:
    """Trades de RE-1 dont l'entrée est retardée de `delay` barres (règles en tête de module)."""
    d = int(delay)
    if d < 0:
        raise ValueError("delayed_trades : retard ≥ 0 exigé")
    t = np.asarray(signal_bar, dtype=np.int64)
    s = np.asarray(side, dtype=np.int64)
    h = np.broadcast_to(np.asarray(horizon, dtype=np.int64), t.shape).copy()
    lv = np.full(len(t), np.nan) if level is None else np.asarray(level, dtype=float).copy()
    if d == 0:
        return run_trades(bars, t, s, h, lv, last)
    n_last = len(bars) - 1 if last is None else int(last)
    ok = t + d + 1 < n_last
    ts, s, h, lv = t[ok] + d, s[ok], h[ok], lv[ok]
    p0 = bars.open.to_numpy(dtype=float)[ts + 1]
    with np.errstate(invalid="ignore"):
        crossed = np.isfinite(lv) & (s * (p0 - lv) / p0 <= 0)    # niveau déjà franchi à l'entrée retardée
    tr = run_trades(bars, ts, s, h, np.where(crossed, np.nan, lv), last)
    hit = np.isin(tr.signal_bar.to_numpy(dtype=np.int64), ts[crossed])
    if hit.any():
        tr.loc[hit, "exit_bar"] = tr.loc[hit, "entry_bar"]
        tr.loc[hit, "exit_price"] = tr.loc[hit, "entry_price"]
        tr.loc[hit, "ret_gross_bps"] = 0.0
        tr.loc[hit, "stop"] = True
        tr.loc[hit, "gap"] = True
    tr["signal_bar"] = tr.signal_bar.to_numpy(dtype=np.int64) - d
    return tr
