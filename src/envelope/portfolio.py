"""EXP-D03 — capital valorisé d'un portefeuille de plusieurs actifs sur un capital commun.

Généralise `envelope.metrics.equity_curve_sized` (une jambe seule le redonne, mêmes points, même drawdown) :
- une jambe = un actif, ses trades (une position à la fois, colonnes de `TRADE_COLUMNS`), la fraction du capital
  engagée par trade (`risk_weights`) et ses frais aller-retour en bps ;
- à l'entrée (ouverture de la barre d'entrée), le notionnel vaut sa fraction du capital valorisé à cet instant : capital
  réalisé plus la valeur latente des positions ouvertes sur les autres actifs, chacune à sa dernière clôture connue ;
- le capital est valorisé à chaque clôture de barre détenue ; à la sortie (ouverture de la barre de sortie, ou clôture
  de la barre du stop), le trade réalise notionnel · (brut − frais) / 10⁴ ;
- à instant égal : clôtures, puis sorties, puis entrées. Aucun prix postérieur à l'instant valorisé n'est lu.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from estimand.excursions import BPS

HALF = pd.Timedelta(minutes=30)
MARK, EXIT, ENTRY = 0, 1, 2


@dataclass
class Leg:
    name: str
    bars: pd.DataFrame
    trades: pd.DataFrame
    weight: np.ndarray
    cost: float


def _events(li: int, leg: Leg) -> list[tuple]:
    tr = leg.trades.reset_index(drop=True)
    if len(leg.weight) != len(tr):
        raise ValueError(f"portfolio_equity : {leg.name}, un poids par trade exigé")
    e, x = tr.entry_bar.to_numpy(dtype=np.int64), tr.exit_bar.to_numpy(dtype=np.int64)
    stop = tr.stop.to_numpy(dtype=bool)
    if len(tr) > 1 and not np.where(stop[:-1], x[:-1] < e[1:], x[:-1] <= e[1:]).all():
        raise ValueError(f"portfolio_equity : {leg.name}, trades qui se chevauchent sur un même actif")
    t = pd.DatetimeIndex(leg.bars.time).asi8
    half = HALF.value
    close = leg.bars.close.to_numpy(dtype=float)
    ev = []
    for j in range(len(tr)):
        ev.append((t[e[j]], ENTRY, li, j, np.nan))
        ev.extend((t[k] + half, MARK, li, j, close[k]) for k in range(e[j], x[j]))
        ev.append((t[x[j]] + half if stop[j] else t[x[j]], EXIT, li, j, np.nan))
    return ev


def portfolio_equity(legs: list[Leg]) -> tuple[pd.Series, dict]:
    """(capital valorisé à chaque événement, résumé : PnL composé, exposition brute maximale, part du temps avec au
    moins une puis deux positions ouvertes)."""
    ev = sorted((e for li, leg in enumerate(legs) for e in _events(li, leg)), key=lambda r: (r[0], r[1]))
    if not ev:
        return pd.Series(dtype=float), {"pnl": 0.0, "exposition_max": 0.0, "part_temps_en_position": 0.0,
                                        "part_temps_deux_positions": 0.0}
    data = [(leg.trades.reset_index(drop=True), np.asarray(leg.weight, dtype=float), float(leg.cost)) for leg in legs]
    capital = 1.0
    pos: dict[tuple[int, int], list] = {}                    # (jambe, trade) → [notionnel, sens, prix d'entrée, dernier]
    times, values = np.empty(len(ev), np.int64), np.empty(len(ev))
    gross_max, t_one, t_two = 0.0, 0, 0
    for i, (tm, kind, li, j, price) in enumerate(ev):
        if i and len(pos):
            dt = tm - ev[i - 1][0]
            t_one += dt
            t_two += dt if len(pos) >= 2 else 0
        if kind == ENTRY:
            tr, w, _ = data[li]
            equity = capital + sum(n * s * (last / p0 - 1.0) for n, s, p0, last in pos.values())
            p0 = float(tr.entry_price.iat[j])
            pos[(li, j)] = [w[j] * equity, int(tr.side.iat[j]), p0, p0]
        elif kind == MARK:
            pos[(li, j)][3] = price
        else:
            tr, _, cost = data[li]
            n, _, _, _ = pos.pop((li, j))
            capital += n * (float(tr.ret_gross_bps.iat[j]) - cost) / BPS
        equity = capital + sum(n * s * (last / p0 - 1.0) for n, s, p0, last in pos.values())
        if pos:
            gross_max = max(gross_max, sum(n * last / p0 for n, _, p0, last in pos.values()) / equity)
        times[i], values[i] = tm, equity
    span = ev[-1][0] - ev[0][0]
    eq = pd.Series(values, index=pd.to_datetime(times, utc=True))
    return eq, {"pnl": float(capital - 1.0), "exposition_max": float(gross_max),
                "part_temps_en_position": float(t_one / span) if span else 0.0,
                "part_temps_deux_positions": float(t_two / span) if span else 0.0}
