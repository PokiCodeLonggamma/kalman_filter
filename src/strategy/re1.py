"""RE-1 figée pour n'importe quel OHLC de 30 min : transfert sans réglage (EXP-D01, option (a) du porteur, 2026-09-30).

RE-1 (EXP-C02bis, stratégie cœur, inchangée) :
- signaux : déclencheur natif v2.1 (`anatomy.build_atlas`, moteur certifié, réglages par défaut : R0 = 100,
  q1 = q2 = 0,01, γ = 0,5 ; oscillateur N2 = 5, R2 = 3 ; warm-up 300 barres de 30 min et 300 bougies de 1 h) ;
- familles de B01 (`categorization.assign_families`) avec la médiane de `leg_atr` gelée à sa valeur BTC :
  R1 = (F1 | F5) & ~x1 déjà retourné ; R2 = (F2b | F3) & x1 déjà retourné ; R3 = (F1 & x1 déjà retourné) | F2a | F4 ;
- univers de RE-1 : R2 hors `nis_z_100` > P75 de BTC (valeur gelée ; NaN exclu) ;
- routage connu à t : F2b (0,50 ≤ retrace_ratio < 0,85) sans stop ; F3 (≥ 0,85) SL-B à l'extremum du segment
  [t − prev_seg_len, t], δ = 0, jamais à moins de 0,25 ATR14(t) de open[t + 1] ;
- exécution : entrée à open[t + 1], sortie à open[t + 1 + 26] ou au stop (intrabarre, gap à l'ouverture) ; une
  position à la fois ; cooldown après un stop (`stop_trades(..., dynamic=False)`) ; H compté en barres de la série.

Les deux seuils de population sont ceux de l'atlas BTC/USD 30 min 2020-2025 (7 296 signaux) : médiane de `leg_atr`
et P75 linéaire de `nis_z_100`, gelés à la précision machine. Ils ne sont jamais recalculés sur un autre actif. Sur
BTC, la chaîne redonne trade par trade les 1 080 trades de C02bis (tests bloquants).

Métriques (`metrics`) : celles de C02bis (8 métriques, IC par grappes mensuelles, capital à 0,25 % par ATR14(t) et
notionnel 1x), annualisées sur la durée propre à chaque actif (`sample_years`), plus le Calmar à 1x.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from anatomy import DEV_END
from categorization import add_derived, assign_families
from envelope import (by_year, mean_ci, risk_weights, route_levels, stop_trades, summarize, summarize_sized,
                      trade_frame)
from estimand.bars import check_no_holdout
from estimand.excursions import BPS
from utils.data_loader import load_ohlc

#: Seuils de population de RE-1, atlas BTC 2020-2025 : np.median(leg_atr) et np.quantile(nis_z_100, 0,75).
LEG_ATR_P50_BTC = 2.823322693433984
NIS_Z100_P75_BTC = 1.2245041356145911
RETRACE_MIN, F3_BOUNDARY = 0.50, 0.85                   # seuils physiques de B01 (ceux d'`assign_families`)
H = 26
FLOOR = 0.25
RULES = {"F2b": None, "F3": ("SL-B", 0.0)}
RISK_BPS = 25.0                                         # 1 ATR14(t) = 0,25 % du capital
N_BOOT = 2000
T0 = pd.Timestamp("2020-01-01", tz="UTC")
N_YEARS_DEV = 6.0                                       # 2020-01-01 → 2025-12-31 (convention de C02bis)


def load_asset(path: str | Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    """(barres pour `build_atlas`, barres `time, open, high, low, close` pour l'exécution), tronquées avant 2026 ;
    empreinte SHA-256 du `.meta.json` vérifiée par `load_ohlc`, trous signalés et jamais comblés."""
    df = load_ohlc(path)
    df = df[df.time < DEV_END].reset_index(drop=True)
    bars = df[["time", "open", "high", "low", "close"]].copy()
    check_no_holdout(bars)
    if not bars.time.is_monotonic_increasing:
        raise ValueError("barres non triées")
    return df, bars


def frozen_masks(atlas: pd.DataFrame, leg_p50: float = LEG_ATR_P50_BTC,
                 nis_p75: float = NIS_Z100_P75_BTC) -> tuple[np.ndarray, dict[str, np.ndarray]]:
    """(famille F1…F5 de chaque signal, masques) aux seuils gelés : régimes R1, R2 avant l'exclusion de nis_z_100,
    R3 ; signaux écartés par nis_z_100 ; univers de RE-1 (R2) et ses sous-familles F2b et F3."""
    d = add_derived(atlas)
    fam = assign_families(d, leg_p50)
    x1 = d.x1_already_flipped_at_t.to_numpy(dtype=bool)
    with np.errstate(invalid="ignore"):
        keep = d.nis_z_100.to_numpy(dtype=float) <= nis_p75
    m = {"R1": np.isin(fam, ("F1", "F5")) & ~x1,
         "R2_avant_nis": np.isin(fam, ("F2b", "F3")) & x1,
         "R3": ((fam == "F1") & x1) | (fam == "F2a") | (fam == "F4")}
    m["nis_exclus"] = m["R2_avant_nis"] & ~keep
    m["F2b"] = (fam == "F2b") & x1 & keep
    m["F3"] = (fam == "F3") & x1 & keep
    m["R2"] = m["F2b"] | m["F3"]
    return fam, m


def run_re1(bars: pd.DataFrame, atlas: pd.DataFrame, atr, masks: dict[str, np.ndarray],
            rules: dict = RULES, horizon: int = H) -> tuple[pd.DataFrame, pd.Series]:
    """Trades de RE-1 (cooldown, une position à la fois) et sous-famille de chaque signal candidat."""
    m = masks["R2"]
    t, s, n = (atlas[c].to_numpy()[m] for c in ("bar_index", "direction", "prev_seg_len"))
    fam = np.where(masks["F3"][m], "F3", "F2b")
    level = None
    if any(r is not None for r in rules.values()):
        level = route_levels(bars, t, s, np.asarray(atr, dtype=float)[t], n, fam, rules, FLOOR)
    return stop_trades(bars, t, s, horizon, level, dynamic=False), pd.Series(fam, index=t)


def sample_years(bars: pd.DataFrame) -> float:
    """Durée d'annualisation (convention de C02bis) : 6 ans pour 2020-01-01 → 2025-12-31, moins le temps écoulé entre
    le 1er janvier 2020 et la première barre de la série (SOL/USDT ouvre le 2020-08-11)."""
    late = max(pd.Timedelta(0), pd.Timestamp(bars.time.iat[0]) - T0)
    return N_YEARS_DEV - late / pd.Timedelta(days=365.25)


def cagr(pnl: float, n_years: float) -> float:
    return float((1.0 + pnl) ** (1.0 / n_years) - 1.0)


def metrics(tr: pd.DataFrame, bars: pd.DataFrame, atr_bps: pd.Series, fee: float, n_cand: int, fam: pd.Series,
            n_years: float, n_boot: int = N_BOOT) -> tuple[dict, pd.DataFrame]:
    """Les métriques de C02bis (`run_C02bis.metrics`, mêmes fonctions, mêmes tirages) sur `n_years`, et le Calmar à 1x.
    Suffixe `_r25` : capital à 0,25 % par ATR14(t) ; sans suffixe : notionnel 1x. Renvoie aussi le tableau annuel."""
    m = summarize(tr, bars, atr_bps, fee, n_candidates=n_cand)
    m["trades_par_mois"] = m["n_trades"] / (12.0 * n_years)
    m.update(mean_ci(tr, bars, fee, n_boot, atr_bps=atr_bps))
    m.update({f"{k}_r25": v for k, v in summarize_sized(tr, bars, atr_bps, fee, RISK_BPS).items()})
    m["annees"] = n_years
    m["cagr_r25"] = cagr(m["pnl_compose_r25"], n_years)
    m["calmar_r25"] = m["cagr_r25"] / abs(m["mdd_valorise_r25"]) if m["mdd_valorise_r25"] < 0 else np.nan
    m["cagr_1x"] = cagr(m["pnl_compose"], n_years)
    m["calmar_1x"] = m["cagr_1x"] / abs(m["mdd_valorise"]) if m["mdd_valorise"] < 0 else np.nan
    m["part_stop"] = float(tr.stop.mean())
    tf = trade_frame(tr, bars, atr_bps, fee)
    f = fam.reindex(tr.signal_bar.to_numpy()).to_numpy()
    for k in ("F2b", "F3"):
        sel = f == k
        m[f"n_{k}"] = int(sel.sum())
        m[f"esperance_atr_{k}"] = float(tf.net_atr[sel].mean()) if sel.any() else np.nan
        m[f"esperance_bps_{k}"] = float(tf.net_bps[sel].mean()) if sel.any() else np.nan
    y = by_year(tr, bars, atr_bps, fee)
    w = risk_weights(atr_bps.reindex(tr.signal_bar.to_numpy()).to_numpy(dtype=float), RISK_BPS)
    lg = pd.Series(np.log1p(w * tf.net_bps.to_numpy() / BPS)).groupby(tf.year.to_numpy()).sum()
    y["pnl_compose_r25"] = np.expm1(lg.reindex(y.annee.to_numpy()).to_numpy())
    m["annees_atr_pos"] = int((y.esperance_atr > 0).sum())
    m["annees_pnl_r25_pos"] = int((y.pnl_compose_r25 > 0).sum())
    return m, y
