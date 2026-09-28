"""EXP-C01 — tableau des 8 métriques (CLAUDE.md §2.2) et décomposition Long / Short / timing, nets de frais.

- Frais : `labeling.net_label`, net = brut − coût aller-retour (convention #KAKALMAN D36).
- Capital composé (réinvestissement intégral, notionnel 1x, sans levier) et drawdown valorisé à chaque clôture de
  barre détenue : `estimand.stoploss.equity_curve` et `drawdown_stats`.
- Unités : bps nets, et bps nets rapportés à l'ATR14 du signal (`atr14_bps(t)`), qui neutralisent le poids des
  années de forte volatilité.
- Timing et dérive (`RESEARCH_INSIGHTS.md` I-M7) : (moyenne Long ± moyenne Short) / 2 des rendements nets.
- Incertitude (I-M6) : IC 95 % de l'espérance et du timing par bootstrap de grappes (mois civils d'entrée).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from categorization import cluster_bootstrap, timing_drift
from estimand.excursions import BPS
from estimand.stoploss import drawdown_stats, equity_curve
from labeling import net_label

DEV_MONTHS = 72                                             # 2020-01 → 2025-12


def trade_frame(trades: pd.DataFrame, bars: pd.DataFrame, atr_bps: pd.Series, cost_bps: float) -> pd.DataFrame:
    """Une ligne par trade : sens, année d'entrée, durée, brut et net en bps, net en ATR14(t) du signal.
    `atr_bps` : ATR14 en bps du close, indexé par barre de signal."""
    gross = trades.ret_gross_bps.to_numpy(dtype=float)
    net, win = net_label(gross, cost_bps)
    atr = atr_bps.reindex(trades.signal_bar.to_numpy()).to_numpy(dtype=float)
    return pd.DataFrame({"side": trades.side.to_numpy(dtype=np.int64),
                         "year": bars.time.iloc[trades.entry_bar.to_numpy()].dt.year.to_numpy(),
                         "duration": (trades.exit_bar - trades.entry_bar + trades.stop.astype(int)).to_numpy(),
                         "gross_bps": gross, "net_bps": net, "win": win, "net_atr": net / atr})


def _sides(tf: pd.DataFrame) -> dict:
    out = {}
    for unit in ("bps", "atr"):
        v = tf[f"net_{unit}"].to_numpy()
        out[f"long_{unit}"] = float(v[tf.side == 1].mean()) if (tf.side == 1).any() else np.nan
        out[f"short_{unit}"] = float(v[tf.side == -1].mean()) if (tf.side == -1).any() else np.nan
        out[f"timing_{unit}"], out[f"derive_{unit}"] = timing_drift(v, tf.side.to_numpy(), "mean")
    return out


def summarize(trades: pd.DataFrame, bars: pd.DataFrame, atr_bps: pd.Series, cost_bps: float, n_candidates: int,
              n_open: int = 0) -> dict:
    """Les 8 métriques nettes et la décomposition par sens. `n_candidates` : signaux candidats de la configuration ;
    `n_open` : trade resté ouvert fin 2025 (ancre native), exclu des trades comme dans P6.5d."""
    tf = trade_frame(trades, bars, atr_bps, cost_bps)
    net, gross = tf.net_bps.to_numpy(), tf.gross_bps.to_numpy()
    cap = np.cumprod(1.0 + net / BPS)
    cum = np.cumsum(net)
    gains, pertes = net[net > 0].sum(), -net[net < 0].sum()
    return {"n_candidats": int(n_candidates), "n_trades": len(tf),
            "part_ignores": (n_candidates - len(tf) - n_open) / n_candidates,
            "trades_par_mois": len(tf) / DEV_MONTHS,
            "pnl_compose": float(cap[-1] - 1.0), "pnl_bps": float(cum[-1]),
            "pf": float(gains / pertes) if pertes > 0 else np.inf,
            "wr": float(tf.win.mean()),
            "esperance_bps": float(net.mean()), "esperance_atr": float(tf.net_atr.mean()),
            "mdd_valorise": drawdown_stats(equity_curve(bars, trades, cost_bps))["max_drawdown"],
            "mdd_sorties": float(min(0.0, (cap / np.maximum.accumulate(np.r_[1.0, cap])[1:] - 1.0).min())),
            "mdd_bps": float(min(0.0, (cum - np.maximum.accumulate(np.r_[0.0, cum])[1:]).min())),
            "duree_mediane": float(np.median(tf.duration)),
            "brut_bps": float(gross.sum()), "frais_cumules_bps": float(len(tf) * cost_bps),
            "part_frais": float(len(tf) * cost_bps / abs(gross.sum())) if gross.sum() != 0 else np.inf,
            "n_long": int((tf.side == 1).sum()), "n_short": int((tf.side == -1).sum()), **_sides(tf)}


def mean_ci(trades: pd.DataFrame, bars: pd.DataFrame, cost_bps: float, n_boot: int = 1000, seed: int = 0) -> dict:
    """IC 95 % de l'espérance nette et du timing net (bps) : bootstrap de grappes, les mois civils d'entrée étant
    tirés avec remise avec tous leurs trades."""
    net, _ = net_label(trades.ret_gross_bps.to_numpy(dtype=float), cost_bps)
    side = trades.side.to_numpy(dtype=np.int64)
    t = bars.time.iloc[trades.entry_bar.to_numpy()]
    month = (t.dt.year * 12 + t.dt.month).to_numpy()

    def stat(pos):
        return [net[pos].mean(), timing_drift(net[pos], side[pos], "mean")[0]]

    lo, hi = np.nanpercentile(cluster_bootstrap(stat, month, n_boot, seed), [2.5, 97.5], axis=0)
    return {"esperance_bps_lo": float(lo[0]), "esperance_bps_hi": float(hi[0]),
            "timing_bps_lo": float(lo[1]), "timing_bps_hi": float(hi[1])}


def risk_weights(atr_bps, risk_bps: float, cap: float = 1.0) -> np.ndarray:
    """Fraction du capital engagée dans chaque trade pour qu'un mouvement d'un ATR14(t) vaille `risk_bps` du capital
    (100 bps : 1 ATR = 1 % du capital), plafonnée à `cap` (levier 1× par défaut)."""
    return np.minimum(cap, risk_bps / np.asarray(atr_bps, dtype=float))


def equity_curve_sized(bars: pd.DataFrame, trades: pd.DataFrame, cost_bps: float, weight) -> pd.Series:
    """`estimand.stoploss.equity_curve`, avec une fraction `weight` du capital engagée dans chaque trade : mêmes points
    datés (clôtures des barres détenues, sorties), frais proportionnels au notionnel. `weight = 1` redonne
    `equity_curve`."""
    close = bars["close"].to_numpy(dtype=float)
    t = pd.DatetimeIndex(bars["time"])
    demi = pd.Timedelta(minutes=30)
    w = np.broadcast_to(np.asarray(weight, dtype=float), (len(trades),))
    temps, valeurs = [t[int(trades.entry_bar.iloc[0])]], [1.0]
    capital = 1.0
    for wi, tr in zip(w, trades.itertuples(index=False)):
        a, b = int(tr.entry_bar), int(tr.exit_bar)
        temps.extend(t[a:b] + demi)
        valeurs.extend(capital * (1.0 + wi * tr.side * (close[a:b] / tr.entry_price - 1.0)))
        capital *= 1.0 + wi * (tr.ret_gross_bps - cost_bps) / BPS
        temps.append(t[b] + demi if tr.stop else t[b])
        valeurs.append(capital)
    return pd.Series(np.asarray(valeurs, dtype=float), index=pd.DatetimeIndex(temps))


def summarize_sized(trades: pd.DataFrame, bars: pd.DataFrame, atr_bps: pd.Series, cost_bps: float, risk_bps: float,
                    cap: float = 1.0) -> dict:
    """PnL composé et drawdowns à risque constant par trade (`risk_weights`), exposition moyenne et part des trades
    dont la taille est plafonnée."""
    atr = atr_bps.reindex(trades.signal_bar.to_numpy()).to_numpy(dtype=float)
    w = risk_weights(atr, risk_bps, cap)
    net, _ = net_label(trades.ret_gross_bps.to_numpy(dtype=float), cost_bps)
    capital = np.cumprod(1.0 + w * net / BPS)
    return {"pnl_compose": float(capital[-1] - 1.0),
            "mdd_valorise": drawdown_stats(equity_curve_sized(bars, trades, cost_bps, w))["max_drawdown"],
            "mdd_sorties": float(min(0.0, (capital / np.maximum.accumulate(np.r_[1.0, capital])[1:] - 1.0).min())),
            "exposition_moyenne": float(w.mean()), "part_plafonnee": float((risk_bps / atr >= cap).mean())}


def by_year(trades: pd.DataFrame, bars: pd.DataFrame, atr_bps: pd.Series, cost_bps: float) -> pd.DataFrame:
    """Une ligne par année d'entrée : trades, PnL net (bps cumulés et composé), espérance, Long, Short, timing."""
    tf = trade_frame(trades, bars, atr_bps, cost_bps)
    rows = []
    for y, g in tf.groupby("year"):
        net = g.net_bps.to_numpy()
        rows.append({"annee": int(y), "n_trades": len(g), "pnl_bps": float(net.sum()),
                     "pnl_compose": float(np.prod(1.0 + net / BPS) - 1.0), "esperance_bps": float(net.mean()),
                     "esperance_atr": float(g.net_atr.mean()), **_sides(g)})
    return pd.DataFrame(rows)
