"""EXP-A01 — variables causales : connues à la clôture de la barre du signal t (aucune barre d'indice > t n'est lue).

Conventions (RESEARCH_LOG.md, EXP-A01) :
- sens d = +1 (Long) / −1 (Short) ; extrêmes lus sur `low` pour un Long, sur `high` pour un Short ;
- segment qualifiant : segment de zone −d achevé en t − 1, soit les barres [t − prev_seg_len, t − 1] ;
- horizon segment [t − prev_seg_len, t] ; horizon cycle [dernier signal brut de sens opposé, t] (NaN s'il n'existe pas) ;
- ATR14 de Wilder, identique à `ta.atr(14)` du Pine ;
- en cas d'égalité, l'extrême retenu est la première occurrence.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from config import SATURATION_TH

ATR_LEN = 14
BPS = 1e4

#: Variables reprises telles quelles du Feature Store #KAKALMAN (`features.kalman_intrinsic`).
STORE_COLUMNS = ["prev_seg_extreme_abs", "peak_bps_vol", "nis_z_100", "A_vol", "log_R_rel", "n_short_seg_48"]


def atr_wilder(high, low, close, n: int = ATR_LEN) -> np.ndarray:
    """ATR de Wilder (`ta.atr(n)` du Pine) : TR_0 = high − low, amorce = moyenne des n premiers TR, puis RMA."""
    h, lo, c = (np.asarray(a, dtype=float) for a in (high, low, close))
    prev_c = np.concatenate(([np.nan], c[:-1]))
    tr = np.fmax(h - lo, np.fmax(np.abs(h - prev_c), np.abs(lo - prev_c)))   # fmax ignore le NaN de la barre 0
    out = np.full(len(tr), np.nan)
    if len(tr) >= n:
        out[n - 1] = tr[:n].mean()
        for i in range(n, len(tr)):
            out[i] = (out[i - 1] * (n - 1) + tr[i]) / n
    return out


def first_extreme(values: np.ndarray, start: int, end: int, d: int) -> int:
    """Indice de la première occurrence du minimum (d = +1) ou du maximum (d = −1) de values[start..end], bornes incluses."""
    w = values[start:end + 1]
    return start + int(np.argmin(w) if d == 1 else np.argmax(w))


def _nanmax(x: np.ndarray) -> float:
    return float(np.max(x[~np.isnan(x)])) if np.any(~np.isnan(x)) else np.nan


def causal_table(f: pd.DataFrame, idx: np.ndarray, atr: np.ndarray) -> pd.DataFrame:
    """Une ligne par signal `idx` (indices de barres de `f`, sortie de `features.build_features`)."""
    sig = f.signal.to_numpy().astype(int)
    zone = f.zone.to_numpy(dtype=float)
    low, high, close = (f[c].to_numpy(dtype=float) for c in ("low", "high", "close"))
    ts = f.trend_strength.to_numpy(dtype=float)
    x1 = f.x1_bps.to_numpy(dtype=float)                     # même signe que la vitesse x1
    psl = f.prev_seg_len.to_numpy()
    store = {c: f[c].to_numpy(dtype=float) for c in STORE_COLUMNS}
    atr = np.asarray(atr, dtype=float)
    idx = np.asarray(idx, dtype=int)

    # Cadence : dernier signal brut (tous sens, même sens, sens opposé) strictement antérieur à t.
    wanted = set(idx.tolist())
    last_any, last_dir, prev = -1, {1: -1, -1: -1}, {}
    for i in np.flatnonzero(sig != 0):
        if i in wanted:
            prev[i] = (last_any, last_dir[sig[i]], last_dir[-sig[i]])
        last_any, last_dir[sig[i]] = i, i

    def gap(t, j):
        return t - j if j >= 0 else np.nan

    rows = []
    for t in idx:
        d = sig[t]
        if d == 0:
            raise ValueError(f"barre {t} : aucun signal")
        s = t - int(psl[t])
        if s < 0 or not np.all(zone[s:t] == -d) or (s > 0 and zone[s - 1] == -d):
            raise ValueError(f"barre {t} : segment qualifiant incohérent")
        ext = low if d == 1 else high
        k_seg = first_extreme(ext, s, t, d)
        p_any, p_same, p_opp = prev[t]
        if p_opp >= 0:
            k_cyc = first_extreme(ext, p_opp, t, d)
            lag_cyc, dist_cyc = t - k_cyc, abs(close[t] - ext[k_cyc]) / atr[t]
        else:
            lag_cyc, dist_cyc = np.nan, np.nan
        seg = slice(s, t)                                     # segment qualifiant [s, t − 1]
        rows.append({
            "obs_lag_seg_bars": t - k_seg,
            "obs_dist_seg_atr": abs(close[t] - ext[k_seg]) / atr[t],
            "obs_lag_cycle_bars": lag_cyc,
            "obs_dist_cycle_atr": dist_cyc,
            "x1_already_flipped_at_t": bool(d * x1[t] > 0),
            "prev_seg_len": int(psl[t]),
            "prev_seg_extreme_abs": store["prev_seg_extreme_abs"][t],
            "saturation": float(np.mean(np.abs(ts[seg]) >= SATURATION_TH)),
            "leg_atr": (high[seg].max() - low[seg].min()) / atr[t],
            "peak_bps_vol": store["peak_bps_vol"][t],
            "nis_z_100": store["nis_z_100"][t],
            "nis_z_100_seg_max": _nanmax(store["nis_z_100"][seg]),
            "A_vol": store["A_vol"][t],
            "log_R_rel": store["log_R_rel"][t],
            "n_short_seg_48": store["n_short_seg_48"][t],
            "gap_prev_any_bars": gap(t, p_any),
            "gap_prev_same_bars": gap(t, p_same),
            "gap_prev_opp_bars": gap(t, p_opp),
            "atr14_bps": atr[t] / close[t] * BPS,
        })
    return pd.DataFrame(rows)
