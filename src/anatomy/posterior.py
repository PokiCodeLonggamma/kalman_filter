"""EXP-A01 — variables a posteriori (préfixe `post_`) et profils autour du signal.

Elles lisent des barres postérieures à t : elles décrivent la géométrie du moteur et ne doivent JAMAIS servir de filtre.

- Fenêtre de l'extremum de référence : [t − prev_seg_len, t_next], bornes incluses, t_next = premier signal brut
  (tous sens) après t, ou dernière barre de l'échantillon s'il n'y en a pas.
- t* = première occurrence du plus bas `low` (Long) ou du plus haut `high` (Short) de la fenêtre.
- post_lag_bars = t − t* (> 0 : extremum passé au signal ; < 0 : extremum encore à venir).
- post_x1_crossed_zero : x1 prend le signe du signal sur [t*, t_next]. t_zero = première barre où c'est le cas ;
  post_lag_filter_bars = t_zero − t*, post_lag_osc_bars = t − t_zero (NaN si x1 ne franchit pas zéro).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from anatomy.causal import BPS, first_extreme

TAUS = np.arange(-48, 49)


def posterior_table(f: pd.DataFrame, idx: np.ndarray, atr: np.ndarray) -> pd.DataFrame:
    """Une ligne par signal `idx` (indices de barres de `f`, sortie de `features.build_features`)."""
    sig = f.signal.to_numpy().astype(int)
    n = len(sig)
    low, high, close = (f[c].to_numpy(dtype=float) for c in ("low", "high", "close"))
    x1 = f.x1_bps.to_numpy(dtype=float)
    psl = f.prev_seg_len.to_numpy()
    atr = np.asarray(atr, dtype=float)
    all_sig = np.flatnonzero(sig != 0)

    rows = []
    for t in np.asarray(idx, dtype=int):
        d = sig[t]
        s = t - int(psl[t])
        k = np.searchsorted(all_sig, t + 1)
        e = int(all_sig[k]) if k < len(all_sig) else n - 1
        ext = low if d == 1 else high
        t_star = first_extreme(ext, s, e, d)
        turned = d * x1[t_star:e + 1] > 0
        if turned.any():
            t_zero = t_star + int(np.argmax(turned))
            crossed, lag_f, lag_o = True, t_zero - t_star, t - t_zero
        else:
            crossed, lag_f, lag_o = False, np.nan, np.nan
        rows.append({
            "post_lag_bars": t - t_star,
            "post_dist_atr": abs(close[t] - ext[t_star]) / atr[t],
            "post_is_right_censored": bool(t_star == e),
            "post_x1_crossed_zero": crossed,
            "post_lag_filter_bars": lag_f,
            "post_lag_osc_bars": lag_o,
        })
    return pd.DataFrame(rows)


def event_profiles(f: pd.DataFrame, idx: np.ndarray, atr: np.ndarray, taus: np.ndarray = TAUS) -> dict[str, np.ndarray]:
    """Trajectoires autour de chaque signal, une ligne par signal et une colonne par décalage τ (NaN hors échantillon).

    price_atr       : d · (close[t+τ] − close[t]) / ATR14(t), excursion signée dans le sens du signal ;
    ts_oriented     : d · trend_strength[t+τ] ;
    x1_atr_oriented : d · x1[t+τ] / ATR14(t), vitesse du filtre en ATR par barre ;
    nis_z_100       : z-score du NIS (non orienté).
    """
    sig = f.signal.to_numpy().astype(int)
    n = len(sig)
    close = f.close.to_numpy(dtype=float)
    ts = f.trend_strength.to_numpy(dtype=float)
    x1 = f.x1_bps.to_numpy(dtype=float) * close / BPS       # x1 en unités de prix par barre
    nis_z = f.nis_z_100.to_numpy(dtype=float)
    idx = np.asarray(idx, dtype=int)
    pos = idx[:, None] + np.asarray(taus)[None, :]
    ok = (pos >= 0) & (pos < n)
    p = np.clip(pos, 0, n - 1)
    d = sig[idx][:, None].astype(float)
    a = np.asarray(atr, dtype=float)[idx][:, None]

    def mask(x):
        return np.where(ok, x, np.nan)

    return {"price_atr": mask(d * (close[p] - close[idx][:, None]) / a),
            "ts_oriented": mask(d * ts[p]),
            "x1_atr_oriented": mask(d * x1[p] / a),
            "nis_z_100": mask(nis_z[p])}
