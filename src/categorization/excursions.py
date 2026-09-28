"""EXP-B01 — excursions futures depuis l'entrée exécutable open[t+1], normalisées par ATR14(t).

Grandeurs a posteriori (elles lisent des barres > t) : elles caractérisent les familles de signaux et ne deviennent
jamais des filtres. Fenêtre d'un horizon H : barres k ∈ [t+1, t+H], bornes incluses (la barre d'entrée compte).
Aucune barre au-delà de l'échantillon (tronqué avant 2026) n'est lue : la fenêtre incomplète donne NaN ou `censored`.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

HORIZONS = (6, 13, 26, 48)
BARRIERS = (1.0, 1.5, 2.0)
BARRIER_HORIZON = 48
OUTCOMES = ("win", "loss", "ambiguous", "timeout", "censored")


def barrier_key(b: float) -> str:
    """1.5 -> '1p5' (nom de colonne)."""
    return f"{b:.1f}".replace(".", "p")


def _arrays(open_, high, low, close, idx, direction, atr):
    o, h, lo, c = (np.asarray(x, dtype=float) for x in (open_, high, low, close))
    return o, h, lo, c, np.asarray(idx, dtype=int), np.asarray(direction, dtype=int), np.asarray(atr, dtype=float)


def excursion_table(open_, high, low, close, idx, direction, atr, horizons=HORIZONS) -> pd.DataFrame:
    """Par signal : entry_price = open[t+1] ; pour chaque H, MFE et MAE (grandeurs ≥ 0), rendement signé
    close[t+H], asymétrie MFE − MAE et indicateur MFE > MAE, en ATR14(t). NaN si t + H dépasse l'échantillon."""
    o, h, lo, c, idx, d, a = _arrays(open_, high, low, close, idx, direction, atr)
    n, m = len(c), len(idx)
    entry = np.where(idx + 1 <= n - 1, o[np.minimum(idx + 1, n - 1)], np.nan)
    out = {"entry_price": entry}
    at = a[idx]
    for H in horizons:
        mfe, mae, ret = np.full(m, np.nan), np.full(m, np.nan), np.full(m, np.nan)
        for i in range(m):
            t = idx[i]
            if t + H > n - 1:
                continue
            e, w = o[t + 1], slice(t + 1, t + H + 1)
            up, dn = h[w].max(), lo[w].min()
            if d[i] == 1:
                mfe[i], mae[i], ret[i] = up - e, e - dn, c[t + H] - e
            else:
                mfe[i], mae[i], ret[i] = e - dn, up - e, e - c[t + H]
        out[f"mfe_{H}_atr"] = mfe / at
        out[f"mae_{H}_atr"] = mae / at
        out[f"ret_{H}_atr"] = ret / at
        out[f"asym_{H}_atr"] = (mfe - mae) / at
        out[f"mfe_gt_mae_{H}"] = np.where(np.isnan(mfe), np.nan, (mfe > mae).astype(float))
    return pd.DataFrame(out)


def barrier_table(open_, high, low, idx, direction, atr, barriers=BARRIERS, horizon: int = BARRIER_HORIZON) -> pd.DataFrame:
    """Premier passage sur ±b·ATR14(t) autour de open[t+1], barres [t+1, t+horizon].

    win : seule la barrière favorable est touchée en premier ; loss : la barrière adverse ; ambiguous : les deux dans
    la même barre (compté comme échec dans le taux strict) ; timeout : aucune à t+horizon ; censored : échantillon
    terminé avant t+horizon sans contact. `barrier_<b>_bars` = k − t à la barre de contact.
    """
    o, h, lo, _, idx, d, a = _arrays(open_, high, low, high, idx, direction, atr)
    n, m = len(o), len(idx)
    out = {}
    for b in barriers:
        outcome = np.empty(m, dtype=object)
        bars = np.full(m, np.nan)
        for i in range(m):
            t = idx[i]
            e, dist = o[t + 1], b * a[t]
            end = min(t + horizon, n - 1)
            hh, ll = h[t + 1:end + 1], lo[t + 1:end + 1]
            up, dn = hh >= e + dist, ll <= e - dist
            fav, adv = (up, dn) if d[i] == 1 else (dn, up)
            kf = int(np.argmax(fav)) if fav.any() else None
            ka = int(np.argmax(adv)) if adv.any() else None
            if kf is None and ka is None:
                outcome[i] = "timeout" if t + horizon <= n - 1 else "censored"
            elif ka is None or (kf is not None and kf < ka):
                outcome[i], bars[i] = "win", kf + 1
            elif kf is None or ka < kf:
                outcome[i], bars[i] = "loss", ka + 1
            else:
                outcome[i], bars[i] = "ambiguous", kf + 1
        key = barrier_key(b)
        out[f"barrier_{key}_outcome"] = outcome
        out[f"barrier_{key}_bars"] = bars
    return pd.DataFrame(out)
