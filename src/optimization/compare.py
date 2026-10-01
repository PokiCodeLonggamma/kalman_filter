"""EXP-D02 — statistiques de comparaison de deux séries hors échantillon (règle de lecture validée par le porteur).

- Grappes : mois civils de la période hors échantillon commune, mois sans trade compris ; ils sont tirés avec remise,
  avec les mêmes tirages pour les deux séries (générateur et ordre de `envelope.metrics._cluster_counts`, graine 0,
  2 000 tirages). Un trade appartient au mois de son entrée.
- Écart d'espérance (A − B) en ATR14(t) et en bps : différence des moyennes par trade sur chaque tirage ; IC 95 %.
- Écart de rendement annualisé composé à 0,25 % du capital par ATR (CAGR des mois tirés) ; IC 95 %.
- Chemins réordonnés (`RESEARCH_INSIGHTS.md` I-M10) : capital composé aux sorties des trades des mois tirés, dans
  l'ordre du tirage ; MDD aux sorties (formule de `summarize_sized`, `mdd_sorties`) et Calmar = CAGR / |MDD| ; écart
  observé sur le chemin réel, plage P2,5-P97,5 de l'écart sur les chemins (pas un IC) et part des chemins où A fait
  mieux (MDD moins profond, Calmar plus élevé).
- « Statistiquement tangible » : IC 95 % entièrement au-dessus de 0 (espérance en ATR et en bps ; rendement).
- `frozen_entries` : mêmes entrées qu'une série de référence, autre horizon par trade, même stop, sans sélection
  séquentielle ; avec `envelope.effect_ci`, lecture d'un changement d'horizon sur entrées figées (I-M16).
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from numba import njit

from envelope import risk_weights, stop_distance
from estimand.excursions import BPS
from estimand.stoploss import TRADE_COLUMNS, apply_stop
from strategy.re1 import N_BOOT, RISK_BPS


@dataclass(frozen=True)
class SeriesStats:
    month: np.ndarray      # mois d'entrée de chaque trade (0 … g − 1), trades dans l'ordre chronologique
    net_atr: np.ndarray
    net_bps: np.ndarray
    r: np.ndarray          # rendement du capital à 0,25 %/ATR : poids · (brut − frais) / 10⁴
    g: int                 # mois civils de la période commune


def month_index(times, start: pd.Timestamp, end: pd.Timestamp) -> tuple[np.ndarray, int]:
    """(mois de chaque horodatage, nombre de mois) de la période [start, end), alignée sur des débuts de mois."""
    t = pd.DatetimeIndex(times)
    g = (end.year - start.year) * 12 + (end.month - start.month)
    idx = np.asarray((t.year - start.year) * 12 + (t.month - start.month), dtype=np.int64)
    if len(idx) and ((idx < 0).any() or (idx >= g).any()):
        raise ValueError("month_index : horodatage hors de la période")
    return idx, int(g)


def month_draws(g: int, n_boot: int = N_BOOT, seed: int = 0) -> np.ndarray:
    """Tirages de mois avec remise, mêmes appels au générateur que `_cluster_counts` : (n_boot, g)."""
    rng = np.random.default_rng(seed)
    return np.array([rng.integers(0, g, g) for _ in range(n_boot)], dtype=np.int64).reshape(n_boot, g)


def series_stats(trades: pd.DataFrame, bars: pd.DataFrame, atr_bps, fee: float, start: pd.Timestamp,
                 end: pd.Timestamp, risk_bps: float = RISK_BPS) -> SeriesStats:
    """Trades d'une série hors échantillon ; `atr_bps` : ATR14 en bps par barre (position)."""
    month, g = month_index(bars.time.iloc[trades.entry_bar.to_numpy()], start, end)
    if len(month) and not (np.diff(month) >= 0).all():
        raise ValueError("series_stats : trades non chronologiques")
    atr = np.asarray(atr_bps, dtype=float)[trades.signal_bar.to_numpy(dtype=np.int64)]
    net = trades.ret_gross_bps.to_numpy(dtype=float) - fee
    return SeriesStats(month, net / atr, net, risk_weights(atr, risk_bps) * net / BPS, g)


def mdd_exits(r: np.ndarray) -> float:
    """MDD du capital composé aux sorties (formule de `summarize_sized`, `mdd_sorties`)."""
    if not len(r):
        return 0.0
    c = np.cumprod(1.0 + r)
    return float(min(0.0, (c / np.maximum.accumulate(np.r_[1.0, c])[1:] - 1.0).min()))


@njit(cache=True)
def _paths(r, ptr, draws):
    nb = draws.shape[0]
    mdd = np.zeros(nb)
    logs = np.zeros(nb)
    for j in range(nb):
        cap, peak, low, ls = 1.0, 1.0, 0.0, 0.0
        for mo in draws[j]:
            for i in range(ptr[mo], ptr[mo + 1]):
                cap = cap * (1.0 + r[i])
                if cap > peak:
                    peak = cap
                dd = cap / peak - 1.0
                if dd < low:
                    low = dd
                ls += np.log1p(r[i])
        mdd[j] = low
        logs[j] = ls
    return mdd, logs


def _cagr(logs, n_years: float):
    return np.expm1(np.asarray(logs, dtype=float) / n_years)


def _calmar(cagr, mdd):
    with np.errstate(invalid="ignore", divide="ignore"):
        return np.where(np.asarray(mdd) < 0, cagr / np.abs(mdd), np.nan)


def _ci(x) -> tuple[float, float]:
    x = np.asarray(x, dtype=float)
    if not np.isfinite(x).any():
        return np.nan, np.nan
    lo, hi = np.nanpercentile(x, [2.5, 97.5])
    return float(lo), float(hi)


def paired_comparison(a: SeriesStats, b: SeriesStats, n_boot: int = N_BOOT, seed: int = 0) -> dict:
    """Écarts A − B (espérance, rendement, chemins) sur les mêmes tirages de mois."""
    if a.g != b.g:
        raise ValueError("paired_comparison : périodes différentes")
    g, ny = a.g, a.g / 12.0
    draws = month_draws(g, n_boot, seed)
    w = np.array([np.bincount(d, minlength=g) for d in draws], dtype=float)
    out = {"n_a": len(a.r), "n_b": len(b.r), "mois": g}
    for unit in ("atr", "bps"):
        va, vb = getattr(a, f"net_{unit}"), getattr(b, f"net_{unit}")
        pa = float(va.mean()) if len(va) else np.nan
        pb = float(vb.mean()) if len(vb) else np.nan
        with np.errstate(invalid="ignore", divide="ignore"):
            ea = (w @ np.bincount(a.month, weights=va, minlength=g)) / (w @ np.bincount(a.month, minlength=g))
            eb = (w @ np.bincount(b.month, weights=vb, minlength=g)) / (w @ np.bincount(b.month, minlength=g))
        out[f"d_esperance_{unit}"] = pa - pb
        out[f"d_esperance_{unit}_lo"], out[f"d_esperance_{unit}_hi"] = _ci(ea - eb)
    ptr_a = np.searchsorted(a.month, np.arange(g + 1)).astype(np.int64)
    ptr_b = np.searchsorted(b.month, np.arange(g + 1)).astype(np.int64)
    mdd_a, log_a = _paths(a.r, ptr_a, draws)
    mdd_b, log_b = _paths(b.r, ptr_b, draws)
    ca, cb = _cagr(log_a, ny), _cagr(log_b, ny)
    ra, rb = float(_cagr(np.log1p(a.r).sum(), ny)), float(_cagr(np.log1p(b.r).sum(), ny))
    out["d_rendement_annuel"] = ra - rb
    out["d_rendement_annuel_lo"], out["d_rendement_annuel_hi"] = _ci(ca - cb)
    ma, mb = mdd_exits(a.r), mdd_exits(b.r)
    out["d_mdd_sorties"] = ma - mb
    out["d_mdd_sorties_lo"], out["d_mdd_sorties_hi"] = _ci(mdd_a - mdd_b)
    out["part_mdd_meilleur"] = float(((mdd_a - mdd_b) > 0).mean())
    ka, kb = float(_calmar(ra, ma)), float(_calmar(rb, mb))
    out["d_calmar_sorties"] = ka - kb
    dk = _calmar(ca, mdd_a) - _calmar(cb, mdd_b)
    out["d_calmar_sorties_lo"], out["d_calmar_sorties_hi"] = _ci(dk)
    with np.errstate(invalid="ignore"):
        out["part_calmar_meilleur"] = float((dk > 0).mean())
    out["esperance_tangible"] = bool(out["d_esperance_atr_lo"] > 0 and out["d_esperance_bps_lo"] > 0)
    out["rendement_tangible"] = bool(out["d_rendement_annuel_lo"] > 0)
    return out


def frozen_entries(bars: pd.DataFrame, ref: pd.DataFrame, horizon, level=None, last: int | None = None) -> pd.DataFrame:
    """Trades aux entrées de `ref` (signal, sens), sortie à min(t + 1 + h, last) et stop au `level` de chaque trade
    (NaN ou None : sans stop), joués un par un (aucune sélection séquentielle) : colonnes de `TRADE_COLUMNS`."""
    t = ref.signal_bar.to_numpy(dtype=np.int64)
    s = ref.side.to_numpy(dtype=np.int64)
    h = np.broadcast_to(np.asarray(horizon, dtype=np.int64), t.shape)
    if (h < 1).any():
        raise ValueError("frozen_entries : horizon ≥ 1 exigé")
    last = len(bars) - 1 if last is None else int(last)
    e, x = t + 1, np.minimum(t + 1 + h, last)
    dist = None if level is None else stop_distance(bars, t, s, np.asarray(level, dtype=float))
    with np.errstate(invalid="ignore"):
        out = apply_stop(bars, e, x, s, dist)
    out["signal_bar"] = t
    return out[TRADE_COLUMNS]
