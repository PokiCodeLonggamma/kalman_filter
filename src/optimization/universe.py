"""EXP-D02 — signaux d'un atlas (un atlas par valeur de R0), seuils de population par fenêtre, candidats de RE-1.

- `signal_table` : colonnes causales de RE-1 pour chaque signal de l'atlas, et le niveau SL-B (extremum du segment,
  δ = 0, plancher 0,25 ATR14(t), `envelope.structural_stop_levels`) calculé une fois pour tout signal qui peut devenir
  candidat (x1 retourné, retracement ≥ 0,50), quels que soient les seuils de la fenêtre.
- `window_thresholds` : médiane de `leg_atr` et P75 linéaire de `nis_z_100` des signaux d'une période [début, fin),
  définition des seuils gelés de RE-1 (`np.median`, `np.quantile`), NaN écartés. Aucune autre ligne n'est lue.
- `candidates` : univers de RE-1 aux seuils donnés (`strategy.frozen_masks`) : petite jambe (`leg_atr` < P50),
  retracement ≥ 0,50, x1 retourné, `nis_z_100` ≤ P75 (NaN exclu). La frontière ne change pas cet univers : elle route
  le stop, SL-B pour un retracement ≥ frontière, aucun stop en dessous (à 0,85 : F3 et F2b de RE-1).
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from categorization import add_derived
from envelope import structural_stop_levels
from optimization.windows import in_period
from strategy import FLOOR
from strategy.re1 import RETRACE_MIN


@dataclass(frozen=True)
class SignalTable:
    t: np.ndarray            # barre du signal (bar_index), triée
    s: np.ndarray            # sens
    time: pd.DatetimeIndex   # heure d'ouverture de la barre du signal
    leg_atr: np.ndarray
    nis: np.ndarray          # nis_z_100
    retrace: np.ndarray      # retrace_ratio
    x1: np.ndarray           # x1 déjà retourné à t
    slb: np.ndarray          # niveau SL-B (NaN hors des signaux qui peuvent devenir candidats)
    atr_bps: np.ndarray      # ATR14(t) en bps du close


def signal_table(bars: pd.DataFrame, atlas: pd.DataFrame, atr) -> SignalTable:
    d = add_derived(atlas)
    t = atlas.bar_index.to_numpy(dtype=np.int64)
    if len(t) and not (np.diff(t) > 0).all():
        raise ValueError("signal_table : signaux non triés ou dupliqués")
    time = pd.DatetimeIndex(atlas.timestamp)
    if not time.equals(pd.DatetimeIndex(bars.time.iloc[t])):
        raise ValueError("signal_table : atlas et barres désalignés")
    s = atlas.direction.to_numpy(dtype=np.int64)
    r = d.retrace_ratio.to_numpy(dtype=float)
    x1 = atlas.x1_already_flipped_at_t.to_numpy(dtype=bool)
    with np.errstate(invalid="ignore"):
        pool = x1 & (r >= RETRACE_MIN)
    slb = np.full(len(t), np.nan)
    if pool.any():
        slb[pool] = structural_stop_levels(bars, t[pool], s[pool], np.asarray(atr, dtype=float)[t[pool]],
                                           atlas.prev_seg_len.to_numpy()[pool], 0.0, FLOOR)
    return SignalTable(t, s, time, d.leg_atr.to_numpy(dtype=float), d.nis_z_100.to_numpy(dtype=float), r, x1, slb,
                       atlas.atr14_bps.to_numpy(dtype=float))


def window_thresholds(tab: SignalTable, start: pd.Timestamp, end: pd.Timestamp) -> tuple[float, float, int]:
    """(P50 de `leg_atr`, P75 de `nis_z_100`, nombre de signaux) des signaux de [start, end)."""
    sel = in_period(tab.time, start, end)
    leg, nis = tab.leg_atr[sel], tab.nis[sel]
    leg, nis = leg[~np.isnan(leg)], nis[~np.isnan(nis)]
    if not len(leg) or not len(nis):
        raise ValueError(f"window_thresholds : aucun signal dans [{start}, {end})")
    return float(np.median(leg)), float(np.quantile(nis, 0.75)), int(sel.sum())


def candidates(tab: SignalTable, leg_p50: float, nis_p75: float, frontier: float,
               start: pd.Timestamp | None = None, end: pd.Timestamp | None = None):
    """(barres, sens, niveaux de stop) des candidats de RE-1 aux seuils donnés, éventuellement restreints aux signaux
    de [start, end) ; niveau NaN : sans stop (retracement < frontière)."""
    with np.errstate(invalid="ignore"):
        r2 = ~(tab.leg_atr >= leg_p50) & (tab.retrace >= RETRACE_MIN) & tab.x1 & (tab.nis <= nis_p75)
        if start is not None:
            r2 &= in_period(tab.time, start, end)
        f3 = tab.retrace[r2] >= frontier
    return tab.t[r2], tab.s[r2], np.where(f3, tab.slb[r2], np.nan)
