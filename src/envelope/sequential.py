"""EXP-C01 — exécution séquentielle de l'Étape C : une seule position à la fois, sortie à horizon fixe.

Réutilise tel quel `estimand.stoploss` (#KAKALMAN P6.5d, copie certifiée) : `apply_stop` exécute chaque trade (entrée à
open[e], sortie à open[x], rendement brut en bps) ; `simulate_strategy` joue la stratégie native stop-and-reverse.

Conventions de la sortie à horizon fixe (`time_stop_trades`) :
- entrée à open[t + 1] pour un signal lu à la clôture de t, seulement si aucune position n'est ouverte (pyramiding 0) ;
- sortie à open[t + 1 + H] : la position est détenue pendant les H barres t + 1 … t + H ; open[t + 1 + H] suit
  immédiatement close[t + H], prix de sortie des excursions de B01 ;
- un signal dont la clôture précède la barre de sortie est ignoré (ni renforcement, ni retournement anticipé) ; un
  signal à la clôture de t + H entre à open[t + 1 + H], à l'instant même de la sortie, comme un retournement natif :
  deux trades ne partagent jamais une barre détenue ;
- une sortie qui tomberait après la dernière barre de 2025 est ramenée à l'ouverture de cette barre : 2026 n'est
  jamais lu ;
- mode continuation (`mode = −1`) : le trade prend le sens opposé au signal.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from estimand.bars import check_no_holdout
from estimand.stoploss import TRADE_COLUMNS, apply_stop


def dev_signals(f: pd.DataFrame) -> pd.DataFrame:
    """Signaux bruts sur barre `valid_features` de l'échantillon de développement : les 7 296 signaux de l'univers
    A01, plus celui de fin 2025 dont la sortie native tombe en 2026. C'est l'entrée de `simulate_strategy` (ancre)."""
    sig = f.signal.to_numpy().astype(np.int64)
    t = np.flatnonzero((sig != 0) & f.valid_features.to_numpy(dtype=bool))
    return pd.DataFrame({"bar_index": t.astype(np.int64), "side": sig[t]})


def time_stop_trades(bars: pd.DataFrame, signal_bar, side, horizon: int, mode: int = 1) -> pd.DataFrame:
    """Trades exécutés, un à la fois, sortie à horizon fixe `horizon` (conventions en tête de module).
    `signal_bar`, `side` : signaux candidats, triés ; `mode` : 1 (sens du signal) ou −1 (continuation)."""
    check_no_holdout(bars)
    if int(horizon) < 1 or mode not in (1, -1):
        raise ValueError("time_stop_trades : horizon ≥ 1 et mode ∈ {1, −1} exigés")
    t = np.asarray(signal_bar, dtype=np.int64)
    s = np.asarray(side, dtype=np.int64)
    if len(t) and not (np.diff(t) > 0).all():
        raise ValueError("time_stop_trades : signaux non triés ou dupliqués")
    last = len(bars) - 1
    rows, libre = [], -1                                     # libre : première barre de signal admissible
    for ti, si in zip(t, s):
        if ti < libre:
            continue                                         # position ouverte : signal ignoré
        e, x = ti + 1, min(ti + 1 + int(horizon), last)
        if x <= e:
            break                                            # plus de barre détenue possible avant la fin de 2025
        rows.append((e, x, mode * si, ti))
        libre = x - 1                                        # un signal à la clôture de x − 1 entre à open[x]
    if not rows:
        return pd.DataFrame({c: pd.Series(dtype=float) for c in TRADE_COLUMNS})
    e, x, sd, sb = (np.asarray(c, dtype=np.int64) for c in zip(*rows))
    out = apply_stop(bars, e, x, sd, None)
    out["signal_bar"] = sb
    return out[TRADE_COLUMNS]
