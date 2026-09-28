"""Features intrinsèques Kalman 30 min (P3/P4) — docs/P3_features_kalman.md.

Toutes les grandeurs sont calculées à partir des colonnes produites par `run_indicator` (parité P2) : aucune
réimplémentation du filtre, du l'oscillateur ni des segments. Toutes sont causales au close t (fenêtres
glissantes arrière uniquement) et sans dimension (invariantes à un changement d'échelle des prix).

Corrections actées vs le script P3 `antigravity/` (D33) :
  - `vol_bps` : `ffill` strictement causal (l'ancien `bfill` recopiait une volatilité future vers le passé) ;
  - `innov_autocorr_48` : vraie corrélation glissante lag 1 sur 48 barres de z = innov/√S (l'ancienne formule
    mélangeait deux moyennes glissantes décalées, fenêtre effective ≈ 96 barres, valeurs > 1 avant écrêtage) ;
  - `peak_bps_vol` : pic |x1| du segment quitté suivi barre à barre (l'ancien découpage par `prev_seg_len`
    n'était correct qu'aux barres de signal) ;
  - ajout de `log_R_rel` (Q-I), `prev_seg_extreme_abs` et `A_close` (D18).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from config import (AUTOCORR_WINDOW, CHOP_WINDOW, FEATURE_VOL_LOOKBACK, NIS_Z_WINDOW, SATURATION_TH,
                    SHORT_SEG_BARS)
from indicator import KalmanParams

BPS = 1e4

#: Top 12 canonique P3, gelé (D27).
TOP12 = ["trend_strength", "x1_bps", "x1_1h_bps", "macro_align_1h", "innov_rel", "nis_z_100",
         "peak_bps_vol", "A_vol", "prev_seg_len", "n_short_seg_48", "bars_since_last_direct_jump",
         "is_saturated"]
#: Features ML1 actives hors Top 12 (Q-I).
ACTIVE_OUT_OF_TOP12 = ["log_R_rel"]
#: Features secondaires archivées pour ablation (D18, D27).
SECONDARY = ["dist_k_bps", "dx1_bps", "n_zone_changes_48", "innov_autocorr_48",
             "prev_seg_extreme_abs", "A_close"]
#: Features signées : leur signe s'inverse entre Long et Short (alignement f·dir pour la baseline linéaire).
SIGNED = ["trend_strength", "x1_bps", "x1_1h_bps", "innov_rel", "dist_k_bps", "dx1_bps"]


def vol_bps(close: np.ndarray, lookback: int = FEATURE_VOL_LOOKBACK) -> np.ndarray:
    """Volatilité locale : écart-type (ddof = 0) des log-rendements sur `lookback` barres, en points de base.

    Causal : les valeurs nulles (barres plates) sont reportées depuis le passé (`ffill`), jamais depuis le futur ;
    les NaN initiaux restent NaN (D33).
    """
    if lookback < 2:
        raise ValueError("lookback doit être >= 2")
    c = pd.Series(np.asarray(close, dtype=float))
    lr = np.log(c / c.shift(1))
    v = lr.rolling(lookback).std(ddof=0) * BPS
    return v.replace(0.0, np.nan).ffill().to_numpy()


def rolling_z(x: np.ndarray, window: int = NIS_Z_WINDOW) -> np.ndarray:
    """Z-score glissant causal sur [t−window+1, t] (ddof = 0, D20)."""
    s = pd.Series(np.asarray(x, dtype=float))
    return ((s - s.rolling(window).mean()) / s.rolling(window).std(ddof=0)).to_numpy()


def rolling_autocorr1(z: np.ndarray, window: int = AUTOCORR_WINDOW) -> np.ndarray:
    """Autocorrélation lag 1 de z sur une fenêtre glissante de `window` barres (D33).

    Corrélation de Pearson entre z et z décalé d'une barre, sur la fenêtre [t−window+1, t] : bornée dans
    [−1, 1] par construction, première valeur définie à l'indice `window`.
    """
    s = pd.Series(np.asarray(z, dtype=float))
    return s.rolling(window).corr(s.shift(1)).to_numpy()


def log_R_rel(R: np.ndarray, R0: float) -> np.ndarray:
    """log(R_used / R0) = γ·log(σ₂₀ / SMA₁₀₀(σ₂₀)) : régime de volatilité interne au filtre (Q-I).

    Sans dimension, invariante à un changement d'échelle comme à un décalage des prix. R_used = 0 (vol_lookback
    barres strictement plates) rend la feature indéfinie : NaN, jamais −inf.
    """
    with np.errstate(divide="ignore", invalid="ignore"):
        v = np.log(np.asarray(R, dtype=float) / R0)
    return np.where(np.isfinite(v), v, np.nan)


def prev_seg_peak_abs_x1(zone: np.ndarray, x1: np.ndarray) -> np.ndarray:
    """Pic de |x1| du segment de zone **quitté**, connu à l'entrée dans le nouveau segment.

    Même machine à états que `indicator.segments.zones_and_signals` (une barre à zone NaN ne met pas l'état
    à jour), mais l'extrême suivi est |x1| au lieu de |ts|.
    """
    z = np.asarray(zone, dtype=float)
    a = np.abs(np.asarray(x1, dtype=float))
    n = len(z)
    out = np.zeros(n)
    seg_zone, peak, prev_peak = 0, 0.0, 0.0
    for i in range(n):
        if not np.isnan(z[i]):
            zi = int(z[i])
            if zi == seg_zone:
                peak = max(peak, a[i])
            else:
                prev_peak = peak
                seg_zone, peak = zi, a[i]
        out[i] = prev_peak
    return out


def bars_since_last_direct_jump(zone: np.ndarray) -> np.ndarray:
    """Barres écoulées depuis le dernier saut direct vert <-> rouge (zone_t · zone_{t−1} = −1, D24).

    NaN tant qu'aucun saut n'a eu lieu (censure à gauche, conservée telle quelle).
    """
    z = np.asarray(zone, dtype=float)
    n = len(z)
    ok = ~np.isnan(z)
    jump = np.zeros(n, dtype=bool)
    jump[1:] = ok[1:] & ok[:-1] & (z[1:] * z[:-1] == -1)
    out = np.full(n, np.nan)
    last = -1
    for i in range(n):
        if jump[i]:
            last = i
        if last >= 0:
            out[i] = i - last
    return out


def _segment_ends(ind: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    """(changement de zone à t, fin d'un segment de tendance court connue à t) — indicatrices causales (D23)."""
    z = ind.zone.to_numpy(dtype=float)
    ok = ~np.isnan(z)
    chg = np.zeros(len(z), dtype=bool)
    chg[1:] = ok[1:] & ok[:-1] & (z[1:] != z[:-1])
    prev_zone = ind.prev_seg_zone.to_numpy()
    prev_len = ind.prev_seg_len.to_numpy()
    short_end = chg & (prev_zone != 0) & (prev_len < SHORT_SEG_BARS)
    return chg.astype(float), short_end.astype(float)


def kalman_features(ind: pd.DataFrame, kalman: KalmanParams = KalmanParams(),
                    vol_lookback: int = FEATURE_VOL_LOOKBACK) -> pd.DataFrame:
    """Features 30 min, une ligne par barre, à partir de la sortie de `run_indicator`."""
    close = ind.close.to_numpy(dtype=float)
    v = vol_bps(close, vol_lookback)
    chg, short_end = _segment_ends(ind)
    z_innov = ind.innov.to_numpy() / np.sqrt(ind.S.to_numpy())
    peak = prev_seg_peak_abs_x1(ind.zone.to_numpy(), ind.x1.to_numpy())
    a_close = ind.A.to_numpy() / close * BPS

    return pd.DataFrame({
        # ── Top 12 (hors features 1 h, ajoutées par features.build_features) ──
        "trend_strength": ind.ts.to_numpy(),
        "x1_bps": ind.x1.to_numpy() / close * BPS,
        "innov_rel": ind.innov.to_numpy() / close,
        "nis_z_100": rolling_z(ind.nis.to_numpy()),
        "peak_bps_vol": peak / close * BPS / v,
        "A_vol": a_close / v,
        "prev_seg_len": ind.prev_seg_len.to_numpy().astype(float),
        "n_short_seg_48": pd.Series(short_end).rolling(CHOP_WINDOW, min_periods=CHOP_WINDOW).sum().to_numpy(),
        "bars_since_last_direct_jump": bars_since_last_direct_jump(ind.zone.to_numpy()),
        "is_saturated": (ind.prev_seg_extreme_abs.to_numpy() >= SATURATION_TH).astype(float),
        # ── Active hors Top 12 (Q-I) ──
        "log_R_rel": log_R_rel(ind.R.to_numpy(), kalman.R0),
        # ── Secondaires (D18, D27) ──
        "dist_k_bps": (close - ind.x0.to_numpy()) / close * BPS,
        "dx1_bps": np.diff(ind.x1.to_numpy(), prepend=np.nan) / close * BPS,
        "n_zone_changes_48": pd.Series(chg).rolling(CHOP_WINDOW, min_periods=CHOP_WINDOW).sum().to_numpy(),
        "innov_autocorr_48": rolling_autocorr1(z_innov),
        "prev_seg_extreme_abs": ind.prev_seg_extreme_abs.to_numpy(),
        "A_close": a_close,
        # ── Intermédiaire conservé (diagnostic, jamais une feature ML1) ──
        "vol_bps": v,
    })
