"""Features multi-TF 1 h pour ML1 (D32).

Règle causale : au close d'une barre 30 min t, seule une bougie 1 h **entièrement clôturée** à cet instant
est accessible (`close_time_1h <= close_time_t`). La jonction se fait par `pd.merge_asof(direction="backward")`
sur les heures de clôture, jamais par index.

Ancrage des bougies 1 h :
  - `anchor="utc_hour"` (défaut, actifs 24/7) : groupes = heure UTC pleine, clôture = début du groupe + 1 h ;
  - `anchor="session"` : groupes = tranches d'une heure comptées depuis l'ouverture de séance (`session_id`),
    clôture = min(début du groupe + 1 h, dernière clôture 30 min de la séance) — une séance ouvrant à :30
    ou une demi-séance ne produit donc pas de bougie fantôme. Le calendrier de séances viendra de P4 étape 2 ;
    ici `session_id` est fourni par l'appelant (une valeur constante par séance).

Warm-up (D32) : `valid_1h` est vrai à partir de la 300e bougie 1 h entièrement clôturée, jamais à partir d'un
compte fixe de barres 30 min (sur BTC 24/7 les deux coïncident : 300 bougies 1 h = 600 barres 30 min).
Le Kalman 1 h utilise les paramètres v2.1 par défaut (D32) et `run_kalman` du module de parité P2 : aucune
réimplémentation du filtre.
"""
from __future__ import annotations

from typing import Literal

import numpy as np
import pandas as pd

from config import WARMUP_BARS_1H
from indicator import KalmanParams, run_kalman

Anchor = Literal["utc_hour", "session"]


def aggregate_1h(df: pd.DataFrame, anchor: Anchor = "utc_hour",
                 session_id: np.ndarray | pd.Series | None = None,
                 bar: pd.Timedelta = pd.Timedelta(minutes=30)) -> pd.DataFrame:
    """Agrège des barres 30 min en bougies 1 h.

    df : colonnes time (ouverture de barre, triée, unique), open, high, low, close.
    Renvoie une ligne par bougie 1 h : time (ouverture), open/high/low/close, n_bars (barres agrégées),
    close_time_1h (instant où la bougie est entièrement clôturée).
    """
    if anchor not in ("utc_hour", "session"):
        raise ValueError(f"anchor inconnu : {anchor!r}")
    d = df.reset_index(drop=True)
    t = pd.to_datetime(d.time)
    close_time = t + bar
    if anchor == "utc_hour":
        group_start = t.dt.floor("1h")
        key = group_start
        nominal_end = group_start + pd.Timedelta(hours=1)
        session_end = pd.Series(pd.NaT, index=d.index)
    else:
        if session_id is None:
            raise ValueError("anchor='session' exige session_id (une valeur constante par séance)")
        sid = pd.Series(np.asarray(session_id), index=d.index)
        if len(sid) != len(d):
            raise ValueError("session_id doit avoir la longueur de df")
        open_ = t.groupby(sid).transform("min")
        k = ((t - open_) // pd.Timedelta(hours=1)).astype("int64")
        group_start = open_ + k * pd.Timedelta(hours=1)
        key = pd.Series(list(zip(sid, k)), index=d.index)
        nominal_end = group_start + pd.Timedelta(hours=1)
        session_end = close_time.groupby(sid).transform("max")

    end = nominal_end if anchor == "utc_hour" else nominal_end.where(nominal_end <= session_end, session_end)
    g = pd.DataFrame({"key": key, "time": group_start, "open": d.open.to_numpy(), "high": d.high.to_numpy(),
                      "low": d.low.to_numpy(), "close": d.close.to_numpy(), "close_time_1h": end})
    out = g.groupby("key", sort=False).agg(time=("time", "first"), open=("open", "first"), high=("high", "max"),
                                           low=("low", "min"), close=("close", "last"), n_bars=("close", "size"),
                                           close_time_1h=("close_time_1h", "max")).reset_index(drop=True)
    return out.sort_values("close_time_1h").reset_index(drop=True)


def features_1h(df: pd.DataFrame, kalman: KalmanParams = KalmanParams(), anchor: Anchor = "utc_hour",
                session_id: np.ndarray | pd.Series | None = None, warmup_bars_1h: int = WARMUP_BARS_1H,
                bar: pd.Timedelta = pd.Timedelta(minutes=30)) -> pd.DataFrame:
    """Une ligne par barre 30 min : état 1 h causal rattaché à chaque close 30 min.

    Colonnes : close_time (du 30 min), x1_1h, close_time_1h (bougie 1 h utilisée), n_1h_closed
    (nombre de bougies 1 h entièrement clôturées au close t), valid_1h (>= warmup_bars_1h).
    """
    if warmup_bars_1h < 0:
        raise ValueError("warmup_bars_1h doit être >= 0")
    d = df.reset_index(drop=True)
    h1 = aggregate_1h(d, anchor=anchor, session_id=session_id, bar=bar)
    h1["x1_1h"] = run_kalman(h1.close.to_numpy(), kalman).x1.to_numpy()
    h1["n_1h_closed"] = np.arange(1, len(h1) + 1)                    # bougies closes à close_time_1h incluse

    left = pd.DataFrame({"close_time": pd.to_datetime(d.time) + bar})
    merged = pd.merge_asof(left.sort_values("close_time"),
                           h1[["close_time_1h", "x1_1h", "n_1h_closed"]],
                           left_on="close_time", right_on="close_time_1h", direction="backward")
    merged["n_1h_closed"] = merged.n_1h_closed.fillna(0).astype(int)
    merged["valid_1h"] = merged.n_1h_closed >= warmup_bars_1h
    return merged.reset_index(drop=True)
