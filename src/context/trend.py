"""EXP-C04 — tendance de contexte (filtre macro), lue à la clôture de chaque barre 30 min, sans lookahead.

- `ema_trend(close, span)` : +1 si close[t] > EMA(close, span)[t], −1 sinon. EMA récursive, α = 2 / (span + 1),
  amorcée sur la première clôture (pandas `ewm(adjust=False)`).
- `htf_bars(bars, hours)` : bougies de `hours` heures ancrées sur les multiples UTC (00 h, 04 h, … pour 4 h), avec
  l'instant où chacune est entièrement clôturée (`close_time`).
- `htf_kalman_trend(bars, hours, params)` : signe de la vitesse x1 du filtre v2.1 (`indicator.run_kalman`, module de
  parité, aucune réimplémentation) calculé sur ces bougies. Au close d'une barre 30 min, seule une bougie entièrement
  clôturée est lue : jonction `merge_asof` arrière sur les heures de clôture, même règle que `features.multi_tf`
  (D32). Tendance valide à partir de `warmup` bougies closes (300, convention D32) ; avant, elle vaut 0 (indéfinie).
- `counter_trend(side, trend)` : vrai si le signal va contre une tendance définie (veto de C04) ; une tendance
  indéfinie (0) ne met jamais de veto.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from indicator import KalmanParams, run_kalman

BAR = pd.Timedelta(minutes=30)
WARMUP_HTF = 300


def ema(close, span: int) -> np.ndarray:
    return pd.Series(np.asarray(close, dtype=float)).ewm(span=int(span), adjust=False).mean().to_numpy()


def ema_trend(close, span: int) -> np.ndarray:
    """+1 (haussier) si close > EMA(close, span), −1 sinon, barre par barre."""
    c = np.asarray(close, dtype=float)
    return np.where(c > ema(c, span), 1, -1).astype(np.int64)


def htf_bars(bars: pd.DataFrame, hours: int) -> pd.DataFrame:
    """Bougies de `hours` heures (ouverture, OHLC, nombre de barres, instant de clôture complète), ancrées UTC."""
    if int(hours) < 1 or 24 % int(hours):
        raise ValueError("htf_bars : hours doit diviser 24")
    t = pd.to_datetime(bars.time)
    g = pd.DataFrame({"start": t.dt.floor(f"{int(hours)}h"), "open": bars.open.to_numpy(), "high": bars.high.to_numpy(),
                      "low": bars.low.to_numpy(), "close": bars.close.to_numpy()})
    out = g.groupby("start", sort=True).agg(open=("open", "first"), high=("high", "max"), low=("low", "min"),
                                            close=("close", "last"), n_bars=("close", "size")).reset_index()
    out["close_time"] = out.start + pd.Timedelta(hours=int(hours))
    return out


def htf_kalman_trend(bars: pd.DataFrame, hours: int = 4, params: KalmanParams = KalmanParams(),
                     warmup: int = WARMUP_HTF) -> pd.DataFrame:
    """Une ligne par barre 30 min : x1 de la dernière bougie `hours` h entièrement clôturée au close de la barre,
    nombre de bougies closes, validité (≥ `warmup`) et tendance (+1, −1 ; 0 avant le warm-up)."""
    h = htf_bars(bars, hours)
    h["x1"] = run_kalman(h.close.to_numpy(), params).x1.to_numpy()
    h["n_closed"] = np.arange(1, len(h) + 1)
    left = pd.DataFrame({"close_time": pd.to_datetime(bars.time) + BAR})
    m = pd.merge_asof(left, h[["close_time", "x1", "n_closed"]].rename(columns={"close_time": "close_time_htf"}),
                      left_on="close_time", right_on="close_time_htf", direction="backward")
    n = m.n_closed.fillna(0).astype(np.int64).to_numpy()
    x1 = m.x1.to_numpy(dtype=float)
    valid = n >= max(int(warmup), 1)                           # au moins une bougie close : x1 défini
    trend = np.where(valid, np.where(x1 > 0, 1, -1), 0).astype(np.int64)
    return pd.DataFrame({"x1_htf": x1, "close_time_htf": m.close_time_htf, "n_htf_closed": n, "valid": valid,
                         "trend": trend})


def counter_trend(side, trend) -> np.ndarray:
    """Veto : sens du signal opposé à une tendance définie (±1). Tendance 0 : aucun veto."""
    s, tr = np.asarray(side, dtype=np.int64), np.asarray(trend, dtype=np.int64)
    return (tr != 0) & (s != tr)
