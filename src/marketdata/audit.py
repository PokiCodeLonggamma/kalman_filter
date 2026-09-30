"""Audit descriptif d'une série de barres 30 min, avant tout calcul de signal ou de PnL (EXP-D01, contrôle D4).

Mesure sans rien corriger ni combler :
- couverture : première et dernière barre, barres par année, part des barres d'une cotation continue 24/7 ;
- intégrité : doublons, désordre, prix non positifs, incohérences OHLC (high < max(open, close), low > min(open, close),
  high < low) ;
- activité : barres à volume nul, barres plates (high = low) ;
- trous : intervalles entre barres consécutives supérieurs au pas, classés par durée (≤ 2 h, ≤ 3 jours, > 3 jours) ;
  les plus longs sont listés ;
- séances : barres par heure UTC et par jour de la semaine ;
- sauts : |log(open_t / close_t−1)| (écart d'ouverture) et |log(close_t / close_t−1)|, en bps : quantiles et plus
  grandes valeurs datées.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

BPS = 1e4
GAP_CLASSES = (("<= 2 h", pd.Timedelta(hours=2)), ("<= 3 jours", pd.Timedelta(days=3)), ("> 3 jours", None))


def _q(x: np.ndarray, ps=(50, 90, 99, 99.9, 100)) -> dict:
    x = x[np.isfinite(x)]
    return {f"P{p:g}": float(np.percentile(x, p)) for p in ps} if len(x) else {}


def _top(times: pd.Series, v: np.ndarray, top: int) -> list[dict]:
    ok = np.flatnonzero(np.isfinite(v))
    order = ok[np.argsort(-v[ok], kind="stable")[:top]]
    return [{"time": str(times.iat[i]), "bps": float(v[i])} for i in order]


def audit_bars(df: pd.DataFrame, bar: pd.Timedelta = pd.Timedelta(minutes=30), top: int = 10) -> dict:
    """Résumé JSON-sérialisable d'une série `time, open, high, low, close[, volume]` (time = ouverture, UTC)."""
    t = pd.to_datetime(df["time"], utc=True).reset_index(drop=True)
    o, h, lo, c = (df[k].to_numpy(dtype=float) for k in ("open", "high", "low", "close"))
    n = len(df)
    step = t.diff()
    out: dict = {"n_barres": n, "premiere": str(t.iat[0]) if n else None, "derniere": str(t.iat[-1]) if n else None,
                 "doublons": int(t.duplicated().sum()), "desordre": int((step < pd.Timedelta(0)).sum())}
    if n:
        theo = int((t.iat[-1] - t.iat[0]) / bar) + 1
        out["part_barres_24_7"] = n / theo
        out["barres_par_annee"] = {int(y): int(k) for y, k in t.dt.year.value_counts().sort_index().items()}
    out["prix_non_positifs"] = int(((o <= 0) | (h <= 0) | (lo <= 0) | (c <= 0)).sum())
    out["incoherences_ohlc"] = int(((h < np.maximum(o, c)) | (lo > np.minimum(o, c)) | (h < lo)).sum())
    out["barres_plates"] = int((h == lo).sum())
    if "volume" in df.columns:
        out["barres_volume_nul"] = int((df["volume"].to_numpy(dtype=float) <= 0).sum())

    holes = np.flatnonzero((step > bar).to_numpy())
    dur = pd.to_timedelta(step.iloc[holes].to_numpy()) - bar           # durée sans barre (au-delà du pas)
    classes, prev = {}, pd.Timedelta(0)
    for name, lim in GAP_CLASSES:
        sel = np.asarray(dur > prev) & (np.asarray(dur <= lim) if lim is not None else True)
        classes[name] = {"n": int(sel.sum()), "barres_manquantes": int(round(float(np.sum(dur[sel] / bar))))}
        prev = lim if lim is not None else prev
    longest = np.argsort(-dur.to_numpy().astype("int64"), kind="stable")[:top]
    out["trous"] = {"n": len(holes), "barres_manquantes": int(round(float(np.sum(dur / bar)))),
                    "classes": classes,
                    "plus_longs": [{"apres": str(t.iat[holes[i] - 1]), "reprise": str(t.iat[holes[i]]),
                                    "duree_h": float(dur[i] / pd.Timedelta(hours=1))} for i in longest]}
    out["barres_par_heure_utc"] = {int(k): int(v) for k, v in t.dt.hour.value_counts().sort_index().items()}
    out["barres_par_jour"] = {int(k): int(v) for k, v in t.dt.dayofweek.value_counts().sort_index().items()}

    prev_c = np.r_[np.nan, c[:-1]]
    with np.errstate(divide="ignore", invalid="ignore"):
        gap_open = np.abs(np.log(o / prev_c)) * BPS
        ret = np.abs(np.log(c / prev_c)) * BPS
    after_hole = np.zeros(n, dtype=bool)
    after_hole[holes] = True
    out["sauts"] = {"ecart_ouverture_bps": _q(gap_open), "ecart_ouverture_apres_trou_bps": _q(gap_open[after_hole]),
                    "rendement_close_bps": _q(ret),
                    "plus_grands_ecarts_ouverture": _top(t, gap_open, top),
                    "plus_grands_rendements": _top(t, ret, top)}
    return out
