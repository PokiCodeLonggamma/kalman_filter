"""EXP-D04 — pertes journalières du capital valorisé (lecture « survie » ; limite de perte journalière d'un compte).

Pour une série de trades (une position à la fois) et la fraction du capital engagée par trade (`risk_weights`) :
- `marked_equity` : capital valorisé comme `envelope.equity_curve_sized` (clôture de chaque barre détenue, puis sortie,
  frais déduits) ; avec `extremes`, aussi à l'extrême défavorable de chaque barre détenue (plus bas pour un achat, plus
  haut pour une vente), daté de la clôture de la barre et placé avant elle : borne pessimiste d'une valorisation en
  continu ;
- `daily_losses` : journée UTC J = points datés de ]J 00:00, J + 1 00:00] (la clôture de la barre de 23:30 appartient
  à J) ; perte du jour = plus bas du capital valorisé de la journée / capital valorisé à J 00:00 − 1 (1 avant le
  premier trade). Une journée sans position n'a aucun point, donc aucune perte.
Aucun prix hors des barres détenues n'est lu.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from estimand.excursions import BPS

HALF = pd.Timedelta(minutes=30)


def marked_equity(bars: pd.DataFrame, trades: pd.DataFrame, cost_bps: float, weight,
                  extremes: bool = False) -> pd.Series:
    """Capital valorisé, points dans l'ordre chronologique ; sans `extremes`, les points d'`equity_curve_sized`."""
    close = bars["close"].to_numpy(dtype=float)
    low, high = bars["low"].to_numpy(dtype=float), bars["high"].to_numpy(dtype=float)
    t = pd.DatetimeIndex(bars["time"]).asi8                       # ns UTC
    half = HALF.value
    w = np.broadcast_to(np.asarray(weight, dtype=float), (len(trades),))
    if not len(trades):
        return pd.Series(dtype=float)
    times, values = [np.array([t[int(trades.entry_bar.iloc[0])]])], [np.array([1.0])]
    capital = 1.0
    for wi, tr in zip(w, trades.itertuples(index=False)):
        a, b = int(tr.entry_bar), int(tr.exit_bar)
        held = t[a:b] + half
        mark = capital * (1.0 + wi * tr.side * (close[a:b] / tr.entry_price - 1.0))
        if extremes:
            adv = low[a:b] if tr.side == 1 else high[a:b]
            worst = capital * (1.0 + wi * tr.side * (adv / tr.entry_price - 1.0))
            times.append(np.repeat(held, 2))
            values.append(np.column_stack([worst, mark]).ravel())
        else:
            times.append(held)
            values.append(mark)
        capital *= 1.0 + wi * (tr.ret_gross_bps - cost_bps) / BPS
        times.append(np.array([t[b] + half if tr.stop else t[b]]))
        values.append(np.array([capital]))
    return pd.Series(np.concatenate(values), index=pd.to_datetime(np.concatenate(times), utc=True))


def daily_from_paths(equity: pd.Series, low: pd.Series | None = None,
                     reference: pd.Series | None = None) -> pd.DataFrame:
    """EXP-D04.1 — journées UTC ]J 00:00, J + 1 00:00] d'un capital daté (points chronologiques) : référence = dernière
    valeur de `reference` (défaut : `equity`) datée au plus tard de J 00:00, 1 avant le premier point ; plus bas =
    minimum de `low` (défaut : `equity`) dans la journée ; perte = plus bas / référence − 1. `low` et `reference`
    doivent couvrir les mêmes journées que `equity` (par exemple les colonnes de `portfolio_paths`)."""
    low = equity if low is None else low
    reference = equity if reference is None else reference

    def by_day(s: pd.Series):
        return pd.Series(s.to_numpy(), index=(s.index - pd.Timedelta(1, "ns")).normalize()).groupby(level=0, sort=True)

    lo, end, fin = by_day(low).min(), by_day(reference).last(), by_day(equity).last()
    if not (lo.index.equals(end.index) and lo.index.equals(fin.index)):
        raise ValueError("daily_from_paths : séries sur des journées différentes")
    start = end.shift(1).fillna(1.0)
    if len(start):
        start.iloc[0] = 1.0
    out = pd.DataFrame({"debut": start, "plus_bas": lo, "fin": fin})
    out["perte"] = out.plus_bas / out.debut - 1.0
    out.index.name = "jour"
    return out


def daily_losses(bars: pd.DataFrame, trades: pd.DataFrame, cost_bps: float, weight,
                 extremes: bool = False) -> pd.DataFrame:
    """Une ligne par journée UTC avec position : capital à 00:00, plus bas, capital en fin de journée, perte du jour."""
    eq = marked_equity(bars, trades, cost_bps, weight, extremes)
    if eq.empty:
        return pd.DataFrame(columns=["debut", "plus_bas", "fin", "perte"])
    day = (eq.index - pd.Timedelta(1, "ns")).normalize()
    g = pd.Series(eq.to_numpy(), index=day).groupby(level=0, sort=True)
    low, end = g.min(), g.last()
    start = end.shift(1).fillna(1.0)
    start.iloc[0] = 1.0
    out = pd.DataFrame({"debut": start, "plus_bas": low, "fin": end})
    out["perte"] = out.plus_bas / out.debut - 1.0
    out.index.name = "jour"
    return out
