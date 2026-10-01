"""EXP-D02 — fenêtres du walk-forward : semestres calendaires (1er janvier, 1er juillet, 00:00 UTC).

- OOS : un semestre ; IS : les `is_semesters` semestres qui le précèdent immédiatement (4, soit 24 mois pour 6 : 80/20).
- Premier OOS : le premier semestre dont l'IS commence à la première barre de la série ou après. Le préchauffage du
  moteur (300 barres de 30 min et 300 bougies d'1 h) peut mordre sur le début du premier IS : BTC (première barre le
  2013-01-01 00:00) a ainsi son premier OOS au S1 2015, comme le prévoit le protocole.
- Dernier OOS : le dernier semestre achevé au plus tard le 2026-01-01 ; la réserve 2026 n'est jamais incluse.
- Périodes demi-ouvertes [début, fin) sur l'heure d'ouverture des barres : un signal appartient à la période de sa barre.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from anatomy import DEV_END

SEMESTRE = pd.DateOffset(months=6)


@dataclass(frozen=True)
class Window:
    k: int
    is_start: pd.Timestamp
    is_end: pd.Timestamp
    oos_start: pd.Timestamp
    oos_end: pd.Timestamp


def semester_ceil(ts: pd.Timestamp) -> pd.Timestamp:
    """Première frontière de semestre (1er janvier ou 1er juillet, 00:00 UTC) postérieure ou égale à `ts`."""
    ts = pd.Timestamp(ts).tz_convert("UTC")
    floor = pd.Timestamp(year=ts.year, month=1 if ts.month <= 6 else 7, day=1, tz="UTC")
    return floor if floor == ts else floor + SEMESTRE


def walk_forward_windows(first_bar: pd.Timestamp, end: pd.Timestamp = DEV_END,
                         is_semesters: int = 4) -> list[Window]:
    """Fenêtres (IS, OOS) d'une série dont la première barre est `first_bar`, OOS jusqu'à `end` exclu."""
    end = pd.Timestamp(end).tz_convert("UTC")
    if end > DEV_END:
        raise ValueError("walk_forward_windows : fin au-delà de la réserve 2026")
    oos = semester_ceil(first_bar) + is_semesters * SEMESTRE
    out = []
    while oos + SEMESTRE <= end:
        out.append(Window(len(out), oos - is_semesters * SEMESTRE, oos, oos, oos + SEMESTRE))
        oos = oos + SEMESTRE
    return out


def bar_span(times, start: pd.Timestamp, end: pd.Timestamp) -> tuple[int, int]:
    """(première, dernière) position des barres d'heure d'ouverture dans [start, end) ; séries triées."""
    t = pd.DatetimeIndex(times)
    first, stop = int(t.searchsorted(start, side="left")), int(t.searchsorted(end, side="left"))
    if stop <= first:
        raise ValueError(f"bar_span : aucune barre dans [{start}, {end})")
    return first, stop - 1


def in_period(times, start: pd.Timestamp, end: pd.Timestamp) -> np.ndarray:
    """Masque des horodatages dans [start, end)."""
    t = pd.DatetimeIndex(times)
    return np.asarray((t >= start) & (t < end))
