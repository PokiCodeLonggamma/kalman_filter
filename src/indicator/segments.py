"""Zones, segments, signaux et exécution d'AKF-TSO v2.1 (Pine l. 174-192, 238-263).

Zone : +1 si ts > up_th, −1 si ts < down_th, 0 sinon (inégalités strictes) ; NaN tant que ts est indéfini
  (convention P1 §7.3 ; l'oracle P0 met 0).
Segment : barres consécutives de même zone ; à chaque changement, archivage dans prev_seg_* puis seg_len = 1.
Signal ONE-SHOT (D24) : 1re barre neutre (seg_len == 1) après un segment rouge (Long) ou vert (Short)
  de longueur ≥ min_trend_bars et d'extrême ≥ min_trend_strength (filtre fantôme aux défauts, D18).
Exécution : stop-and-reverse, pyramiding = 0 (un signal de même sens que la position est ignoré).
  fill_price = "open_next" (D25, défaut) : décision au close t, remplissage à l'open t+1.
  fill_price = "close" : remplissage au close t, comme `process_orders_on_close=true` (parité TradingView uniquement).
  warmup_bars (D22) : aucune décision avant cette barre ; 0 pour la parité. Les colonnes de signal restent
  brutes avant le warm-up : tout consommateur filtre `valid`.
Équivalence TradingView : signaux, décisions et sens de position (1 unité). Les margin calls éventuels du broker
  émulé (capital 100 000, prix > 100 000 depuis 2024-12) ne sont pas modélisés.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import numpy as np
import pandas as pd

from indicator._bounds import check_range

FillPrice = Literal["open_next", "close"]


@dataclass(frozen=True)
class SignalParams:
    up_th: float = 30.0
    down_th: float = -30.0
    min_trend_bars: int = 6
    min_trend_strength: float = 60.0
    use_strength_cond: bool = True

    def __post_init__(self):                                   # minval / maxval l. 27-30
        check_range("up_th", self.up_th, lo=0.0, hi=100.0)
        check_range("down_th", self.down_th, lo=-100.0, hi=0.0)
        check_range("min_trend_bars", self.min_trend_bars, lo=1, hi=100, integer=True)
        check_range("min_trend_strength", self.min_trend_strength, lo=0.0, hi=100.0)


def zones_and_signals(ts: np.ndarray, p: SignalParams = SignalParams()) -> pd.DataFrame:
    ts = np.asarray(ts, dtype=float)
    n = len(ts)
    zone = np.full(n, np.nan)
    cols = {k: np.zeros(n) for k in ["seg_zone", "seg_len", "seg_extreme_abs",
                                     "prev_seg_zone", "prev_seg_len", "prev_seg_extreme_abs"]}
    long_sig = np.zeros(n, dtype=bool)
    short_sig = np.zeros(n, dtype=bool)
    seg_zone, seg_len, seg_ext = 0, 0, 0.0          # var int / var float du Pine
    prev_zone, prev_len, prev_ext = 0, 0, 0.0
    for i in range(n):
        t = ts[i]
        if not np.isnan(t):
            z = 1 if t > p.up_th else (-1 if t < p.down_th else 0)
            zone[i] = z
            if z == seg_zone:
                seg_len += 1
                seg_ext = max(seg_ext, abs(t))
            else:
                prev_zone, prev_len, prev_ext = seg_zone, seg_len, seg_ext
                seg_zone, seg_len, seg_ext = z, 1, abs(t)
        # Setups évalués à chaque barre sur l'état courant (l. 241-254)
        strong = (not p.use_strength_cond) or prev_ext >= p.min_trend_strength
        entered_neutral = seg_zone == 0 and seg_len == 1
        long_sig[i] = entered_neutral and prev_zone == -1 and prev_len >= p.min_trend_bars and strong
        short_sig[i] = entered_neutral and prev_zone == 1 and prev_len >= p.min_trend_bars and strong
        for k, v in zip(cols, (seg_zone, seg_len, seg_ext, prev_zone, prev_len, prev_ext)):
            cols[k][i] = v
    out = pd.DataFrame({"zone": zone, **cols, "long_signal": long_sig, "short_signal": short_sig})
    for k in ["seg_zone", "seg_len", "prev_seg_zone", "prev_seg_len"]:
        out[k] = out[k].astype(int)
    return out


def execute(long_signal: np.ndarray, short_signal: np.ndarray, open_: np.ndarray, close: np.ndarray,
            fill_price: FillPrice = "open_next", warmup_bars: int = 0) -> pd.DataFrame:
    """Colonnes par barre :
    signal   : +1 / −1 / 0 (signal brut)
    decision : signal retenu (position opposée ou plate), ignored : signal de même sens que la position visée
    fill     : sens rempli à cette barre (0 sinon) ; fill_px : prix de remplissage
    position : position détenue en fin de barre, après les remplissages de la barre
    """
    if fill_price not in ("open_next", "close"):
        raise ValueError(f"fill_price inconnu : {fill_price!r}")
    long_signal = np.asarray(long_signal, dtype=bool)
    short_signal = np.asarray(short_signal, dtype=bool)
    o, c = np.asarray(open_, dtype=float), np.asarray(close, dtype=float)
    n = len(c)
    if not (len(long_signal) == len(short_signal) == len(o) == n):
        raise ValueError("long_signal, short_signal, open_ et close doivent avoir la même longueur")
    check_range("warmup_bars", warmup_bars, lo=0, integer=True)
    sig = np.where(long_signal, 1, np.where(short_signal, -1, 0))
    decision = np.zeros(n, dtype=bool)
    ignored = np.zeros(n, dtype=bool)
    fill = np.zeros(n, dtype=int)
    fill_px = np.full(n, np.nan)
    position = np.zeros(n, dtype=int)
    target, held = 0, 0
    for i in range(n):
        if fill_price == "open_next" and i > 0 and fill[i] != 0:
            held = fill[i]                               # ordre de la barre i−1 rempli à l'open i
        d = sig[i] if i >= warmup_bars else 0
        if d != 0:
            if d != target:
                decision[i], target = True, d
                if fill_price == "close":
                    fill[i], fill_px[i], held = d, c[i], d
                elif i + 1 < n:
                    fill[i + 1], fill_px[i + 1] = d, o[i + 1]
            else:
                ignored[i] = True
        position[i] = held
    return pd.DataFrame({"signal": sig, "decision": decision, "ignored": ignored,
                         "fill": fill, "fill_px": fill_px, "position": position})


def trades(ex: pd.DataFrame, time: pd.Series | None = None) -> pd.DataFrame:
    """Liste des trades à partir des remplissages : entrée, sortie (remplissage opposé suivant), sens, prix.
    Le dernier trade reste ouvert (exit NaN). Aucun résultat financier calculé ici.
    attrs["pending_side"] : sens d'une décision prise sans remplissage (open_next à la dernière barre), 0 sinon.
    Colonnes ex post : ne jamais les utiliser comme feature à la barre de décision."""
    fill = ex.fill.to_numpy()
    idx = np.flatnonzero(fill != 0)
    rows = []
    for k, i in enumerate(idx):
        j = idx[k + 1] if k + 1 < len(idx) else None
        rows.append({"side": int(fill[i]), "entry_bar": int(i), "entry_px": float(ex.fill_px.iat[i]),
                     "exit_bar": int(j) if j is not None else pd.NA,
                     "exit_px": float(ex.fill_px.iat[j]) if j is not None else np.nan})
    t = pd.DataFrame(rows, columns=["side", "entry_bar", "entry_px", "exit_bar", "exit_px"])
    t["exit_bar"] = t.exit_bar.astype("Int64")
    if time is not None and len(t):
        tv = pd.Series(time).reset_index(drop=True)
        t["entry_time"] = tv.iloc[t.entry_bar].to_numpy()
        t["exit_time"] = [tv.iat[int(j)] if pd.notna(j) else pd.NaT for j in t.exit_bar]
    dec = np.flatnonzero(ex.decision.to_numpy())
    pending = 0
    if len(dec):
        last = dec[-1]
        if fill[last] == 0 and (last + 1 >= len(fill) or fill[last + 1] == 0):
            pending = int(ex.signal.iat[last])
    t.attrs["pending_side"] = pending
    return t
