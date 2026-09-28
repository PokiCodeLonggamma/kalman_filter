"""Feature Store ML1 (P4 étape 1) — docs/P3_features_kalman.md, décisions D27 à D33.

    from features import build_features, build_events
    f = build_features(df)          # une ligne par barre 30 min
    ev = build_events(f)            # une ligne par SIGNAL BRUT (univers ML1, option A)

Conventions
-----------
- Tout part de `indicator.run_indicator` (parité P2) : le Kalman, l'oscillateur et les segments ne sont jamais
  réimplémentés ici.
- Univers événementiel ML1 (Q-G option A, D28) : **tous** les signaux bruts (`long_signal | short_signal`),
  y compris ceux qu'un moteur stop-and-reverse ignorerait, puisque le système peut être à plat après un rejet
  de ML1. `build_events` ne passe donc pas par `execute()`. Les colonnes `baseline_decision`,
  `baseline_ignored` et `run_rank` sont des **métadonnées de reporting**, jamais des features :
  `run_rank == 1` reconstitue l'univers des décisions exécutables de la baseline.
- Aucune colonne ex post (remplissage, prix d'entrée, position, trades, résultat) ne sort d'ici. Le prix
  d'entrée `open_{t+1}` (D25) est traité au labeling (étape 3).
- Warm-up (D22, D32) : `valid_features = valid (>= 300 barres 30 min) & valid_1h (>= 300 bougies 1 h closes)`.
  Les colonnes restent brutes avant le warm-up ; `build_events` filtre.
- Alignement Long/Short : les features brutes sont conservées intactes ; les versions `*_al = f · side` sont
  ajoutées au niveau événement pour la baseline logistique (la direction n'existe qu'au signal).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from config import DEFAULT_ASSET, FEATURE_VOL_LOOKBACK, WARMUP_BARS, WARMUP_BARS_1H
from features.kalman_intrinsic import (ACTIVE_OUT_OF_TOP12, BPS, SECONDARY, SIGNED, TOP12, bars_since_last_direct_jump,
                                       kalman_features, log_R_rel, prev_seg_peak_abs_x1, rolling_autocorr1,
                                       rolling_z, vol_bps)
from features.multi_tf import Anchor, aggregate_1h, features_1h
from indicator import KalmanParams, OscParams, SignalParams, run_indicator

__all__ = ["build_features", "build_events", "FEATURE_GROUPS", "FEATURE_COLUMNS", "ALIGNED_FEATURES",
           "EVENT_META_COLUMNS", "TOP12", "ACTIVE_OUT_OF_TOP12", "SECONDARY", "SIGNED",
           "kalman_features", "features_1h", "aggregate_1h", "vol_bps", "rolling_z", "rolling_autocorr1", "log_R_rel",
           "prev_seg_peak_abs_x1", "bars_since_last_direct_jump"]

#: Groupes de features du store (D27, D31, D33).
FEATURE_GROUPS = {"top12": TOP12, "active_hors_top12": ACTIVE_OUT_OF_TOP12, "secondaire": SECONDARY}
FEATURE_COLUMNS = TOP12 + ACTIVE_OUT_OF_TOP12 + SECONDARY
#: Versions alignées sur la direction du signal, pour les modèles linéaires (macro_align_1h l'est déjà).
ALIGNED_FEATURES = [f"{c}_al" for c in SIGNED]
#: Colonnes de contexte des événements : reporting et labeling, jamais des features.
EVENT_META_COLUMNS = ["time", "close_time", "asset", "bar_index", "side", "entry_bar", "entry_time",
                      "baseline_decision", "baseline_ignored", "run_rank"]

#: État du signal repris de `run_indicator` (`prev_seg_len` est déjà une feature du Top 12, non dupliquée ici).
_STATE_COLUMNS = ["open", "high", "low", "close", "zone", "seg_len", "prev_seg_zone",
                  "long_signal", "short_signal", "signal", "decision", "ignored", "valid"]


def build_features(df: pd.DataFrame, kalman: KalmanParams = KalmanParams(), osc: OscParams = OscParams(),
                   signal: SignalParams = SignalParams(), warmup_bars: int = WARMUP_BARS,
                   warmup_bars_1h: int = WARMUP_BARS_1H, vol_lookback: int = FEATURE_VOL_LOOKBACK,
                   anchor_1h: Anchor = "utc_hour", session_id: np.ndarray | pd.Series | None = None,
                   asset: str = DEFAULT_ASSET) -> pd.DataFrame:
    """Une ligne par barre 30 min : état du signal, features 30 min et 1 h, masques de warm-up.

    `macro_align_1h` n'est pas définie ici : elle dépend de la direction du signal et n'existe donc qu'au
    niveau événement (`build_events`). Le signe de la vitesse 1 h est exposé via `sign_x1_1h`.
    """
    ind = run_indicator(df, kalman, osc, signal, warmup_bars=warmup_bars)
    f30 = kalman_features(ind, kalman, vol_lookback)
    f1h = features_1h(df, kalman, anchor=anchor_1h, session_id=session_id, warmup_bars_1h=warmup_bars_1h)

    close = ind.close.to_numpy(dtype=float)
    x1_1h = f1h.x1_1h.to_numpy(dtype=float)
    out = pd.DataFrame({"time": ind.time.to_numpy(), "close_time": f1h.close_time.to_numpy(),
                        "bar_index": np.arange(len(ind)), "asset": asset})
    out = pd.concat([out, ind[_STATE_COLUMNS], f1h[["close_time_1h", "n_1h_closed", "valid_1h"]], f30], axis=1)
    out["x1_1h_bps"] = x1_1h / close * BPS
    out["sign_x1_1h"] = np.sign(x1_1h)
    out["valid_features"] = out.valid.to_numpy() & out.valid_1h.to_numpy()
    ordered = (["time", "close_time", "bar_index", "asset"] + _STATE_COLUMNS
               + ["close_time_1h", "n_1h_closed", "valid_1h", "valid_features"]
               + FEATURE_COLUMNS + ["sign_x1_1h", "vol_bps"])
    return out[[c for c in ordered if c != "macro_align_1h"]]


def _run_rank(signal: np.ndarray) -> np.ndarray:
    """Rang d'un signal brut dans sa série consécutive de même sens (1 = décision de la baseline)."""
    sig = np.asarray(signal)
    out = np.zeros(len(sig), dtype=int)
    rank, last = 0, 0
    for i in np.flatnonzero(sig != 0):
        rank = rank + 1 if sig[i] == last else 1
        out[i], last = rank, sig[i]
    return out


def build_events(features: pd.DataFrame) -> pd.DataFrame:
    """Une ligne par signal brut retenu : univers d'apprentissage de ML1 (option A, D28).

    Filtres : `valid_features` (warm-up 30 min et 1 h) et existence de la barre d'entrée `t+1` (D25).
    Les événements dont la sortie dépendrait de données absentes en fin d'échantillon sont censurés au
    labeling (étape 3, `labeling.label_events`, D34), jamais ici.
    """
    f = features.reset_index(drop=True)
    n = len(f)
    sig = f.signal.to_numpy()
    rank = _run_rank(sig)
    keep = (sig != 0) & f.valid_features.to_numpy() & (f.bar_index.to_numpy() + 1 <= n - 1)
    idx = np.flatnonzero(keep)

    side = sig[idx].astype(int)
    ev = pd.DataFrame({
        "time": f.time.to_numpy()[idx], "close_time": f.close_time.to_numpy()[idx],
        "asset": f.asset.to_numpy()[idx], "bar_index": f.bar_index.to_numpy()[idx], "side": side,
        "entry_bar": f.bar_index.to_numpy()[idx] + 1, "entry_time": f.time.to_numpy()[idx + 1],
        "baseline_decision": f.decision.to_numpy()[idx], "baseline_ignored": f.ignored.to_numpy()[idx],
        "run_rank": rank[idx],
    })
    for c in FEATURE_COLUMNS:
        if c == "macro_align_1h":
            ev[c] = side * f.sign_x1_1h.to_numpy()[idx]
        else:
            ev[c] = f[c].to_numpy()[idx]
    for c in SIGNED:
        ev[f"{c}_al"] = ev[c].to_numpy() * side
    return ev.reset_index(drop=True)
