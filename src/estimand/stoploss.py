"""P6.5d (D48) — stratégie AKF-TSO v2.1 gelée, avec ou sans stop-loss fixe, en rendements bruts et nets.

Conventions (sans lookahead, conservatrices) :
- entrée à `open[b + 1]` (D25) ; stop à `P0 · (1 − side · stop)` (Long : sous l'entrée ; Short : au-dessus) ;
- le stop est testé sur les high / low des barres détenues `[entrée, sortie − 1]`, barre d'entrée comprise ; le signal
  opposé n'existe qu'à la clôture de sa barre et s'exécute à l'ouverture suivante : un stop touché pendant la barre
  du signal opposé précède donc ce signal et s'exécute en premier ;
- gap : si une barre ouvre au-delà du stop, l'exécution se fait à cette ouverture (plus défavorable que le niveau du
  stop) ; aucune exécution meilleure que le niveau du stop n'est jamais supposée ;
- sortie normale au signal opposé : `open[t_opp + 1]`, comme la cible B.

- `apply_stop` : trade par trade (les 7 296 événements, chevauchements compris, comme la cible B) ;
- `simulate_strategy` : exécution séquentielle, sémantique Pine validée par Aymeric : toujours un seul trade ;
  en position, retournement au signal opposé et signal de même sens ignoré (pyramiding 0) ; après un stop, à plat
  jusqu'au prochain signal, quel que soit son sens ; sans stop, elle reproduit les décisions `run_rank == 1` ;
- `equity_curve`, `drawdown_stats` : capital composé (réinvestissement intégral, 1 unité de notionnel), partant de
  1, valorisé à chaque clôture de barre pendant les trades et à chaque sortie réalisée.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from estimand.bars import check_no_holdout
from estimand.excursions import BPS

TRADE_COLUMNS = ["entry_bar", "exit_bar", "side", "entry_price", "exit_price", "stop", "gap", "ret_gross_bps",
                 "signal_bar"]


def apply_stop(bars: pd.DataFrame, entry, exit_, side, stop: float | None, inclure_sortie: bool = False) -> pd.DataFrame:
    """Une ligne par trade : sortie effective (barre du stop ou `exit_`), prix, drapeaux `stop` / `gap`, rendement brut.
    `exit_bar` = barre pendant laquelle le stop s'exécute, ou barre dont l'ouverture exécute la sortie normale.
    `inclure_sortie` : le stop est aussi testé pendant la barre `exit_` (trade sans sortie avant la fin de
    l'échantillon : `exit_` est alors la dernière barre et n'est qu'une borne)."""
    op = bars["open"].to_numpy(dtype=float)
    hi = bars["high"].to_numpy(dtype=float)
    lo = bars["low"].to_numpy(dtype=float)
    e = np.asarray(entry, dtype=np.int64)
    x = np.asarray(exit_, dtype=np.int64)
    s = np.asarray(side, dtype=np.int64)
    if (x <= e).any() or (x >= len(op)).any() or not np.isin(s, (-1, 1)).all():
        raise ValueError("apply_stop : sortie invalide ou hors des barres de développement")
    p0 = op[e]
    sortie, prix = x.copy(), op[x].copy()
    touche, gap = np.zeros(len(e), bool), np.zeros(len(e), bool)
    if stop is not None:
        niveau = p0 * (1.0 - s * stop)
        largeur = x - e + int(inclure_sortie)
        k = np.arange(int(largeur.max()))
        valide = k[None, :] < largeur[:, None]
        idx = np.where(valide, e[:, None] + k[None, :], e[:, None])
        longue = (s == 1)[:, None]
        n = niveau[:, None]
        hit = valide & np.where(longue, lo[idx] <= n, hi[idx] >= n)
        a = hit.any(axis=1)
        j = hit.argmax(axis=1)
        kb = e + j
        ouvre_au_dela = np.where(s == 1, op[kb] <= niveau, op[kb] >= niveau) & (j > 0)
        touche = a
        gap = a & ouvre_au_dela
        sortie = np.where(a, kb, x)
        prix = np.where(a, np.where(gap, op[kb], niveau), op[x])
    ret = s * (prix / p0 - 1.0) * BPS
    return pd.DataFrame({"entry_bar": e, "exit_bar": sortie, "side": s, "entry_price": p0, "exit_price": prix,
                         "stop": touche, "gap": gap, "ret_gross_bps": ret})


def simulate_strategy(bars: pd.DataFrame, signals: pd.DataFrame, stop: float | None) -> tuple[pd.DataFrame, dict]:
    """(trades clos, dernier trade ouvert ou None). Les signaux sont ceux de `load_signals_dev` (triés, barres uniques)."""
    check_no_holdout(bars)
    n = len(bars)
    t = signals["bar_index"].to_numpy(dtype=np.int64)
    sd = signals["side"].to_numpy(dtype=np.int64)
    if not (np.diff(t) > 0).all():
        raise ValueError("simulate_strategy : signaux non triés ou dupliqués")
    prochain_oppose = {sens: np.flatnonzero(sd == -sens) for sens in (1, -1)}
    trades, ouvert, k = [], None, 0
    while k < len(t):
        e, s = t[k] + 1, sd[k]
        if e > n - 1:
            break
        cand = prochain_oppose[s]
        j = cand[np.searchsorted(t[cand], e, side="left")] if (t[cand] >= e).any() else -1
        x = t[j] + 1 if j >= 0 and t[j] + 1 <= n - 1 else -1
        fin = x if x > 0 else n - 1
        if fin <= e:
            ouvert = {"entry_bar": int(e), "side": int(s), "signal_bar": int(t[k])}
            break
        tr = apply_stop(bars, [e], [fin], [s], stop, inclure_sortie=x < 0).iloc[0].to_dict()
        if not tr["stop"] and x < 0:                               # ni stop ni signal opposé avant la fin de 2025
            ouvert = {"entry_bar": int(e), "side": int(s), "signal_bar": int(t[k])}
            break
        tr["signal_bar"] = int(t[k])
        trades.append(tr)
        if tr["stop"]:
            suivants = np.flatnonzero(t >= tr["exit_bar"])        # signal à la clôture de la barre du stop ou après
            if not len(suivants):
                break
            k = int(suivants[0])
        else:
            k = int(j)                                              # retournement : le signal opposé devient l'entrée
    out = pd.DataFrame(trades, columns=TRADE_COLUMNS)
    for c in ("entry_bar", "exit_bar", "side", "signal_bar"):
        out[c] = out[c].astype(np.int64)
    out["stop"] = out["stop"].astype(bool)
    out["gap"] = out["gap"].astype(bool)
    return out, ouvert


def equity_curve(bars: pd.DataFrame, trades: pd.DataFrame, cost_bps: float) -> pd.Series:
    """Capital composé, suite de points datés dans l'ordre chronologique : capital initial 1 à l'ouverture de la
    première entrée ; pendant un trade, valorisation à la clôture de chaque barre détenue avant la barre de sortie
    (horodatée à la fin de la barre) ; à chaque sortie, capital réalisé net du coût (sortie au signal opposé : ouverture
    de la barre ; stop : fin de la barre du stop). Les périodes à plat n'ajoutent aucun point."""
    close = bars["close"].to_numpy(dtype=float)
    t = pd.DatetimeIndex(bars["time"])
    demi = pd.Timedelta(minutes=30)
    temps, valeurs = [t[int(trades.entry_bar.iloc[0])]], [1.0]
    capital = 1.0
    for tr in trades.itertuples(index=False):
        a, b = int(tr.entry_bar), int(tr.exit_bar)
        temps.extend(t[a:b] + demi)
        valeurs.extend(capital * (1.0 + tr.side * (close[a:b] / tr.entry_price - 1.0)))
        capital *= 1.0 + (tr.ret_gross_bps - cost_bps) / BPS
        temps.append(t[b] + demi if tr.stop else t[b])
        valeurs.append(capital)
    return pd.Series(np.asarray(valeurs, dtype=float), index=pd.DatetimeIndex(temps))


def drawdown_stats(equity: pd.Series) -> dict:
    """Max drawdown sur la suite de points (le premier point sert de référence initiale) et plus longue période sous
    le pic : du dernier pic au premier point qui le regagne, ou à la fin de la série, en jours."""
    v = equity.to_numpy(dtype=float)
    temps = pd.DatetimeIndex(equity.index)
    pic = np.maximum.accumulate(v)
    dd = v / pic - 1.0
    i = int(np.argmin(dd))
    j = int(np.argmax(v[:i + 1])) if i > 0 else 0
    plus_long, debut = pd.Timedelta(0), None
    for k in range(len(v)):
        if dd[k] < 0 and debut is None:
            debut = temps[int(np.argmax(v[:k + 1]))]                # dernier pic avant la baisse
        if dd[k] >= 0 and debut is not None:
            plus_long, debut = max(plus_long, temps[k] - debut), None
    if debut is not None:
        plus_long = max(plus_long, temps[-1] - debut)
    return {"max_drawdown": float(dd[i]), "debut_drawdown": str(temps[j]), "creux": str(temps[i]),
            "plus_longue_periode_sous_le_pic_jours": plus_long / pd.Timedelta(days=1)}
