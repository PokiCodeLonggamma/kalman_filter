"""Étape C — enveloppe mécanique séquentielle (EXP-C01 : sortie à horizon fixe ; EXP-C02 : stop-loss en prix ;
EXP-C02bis : moteur de régimes, une enveloppe par sous-famille).

    from envelope import dev_signals, time_stop_trades, summarize, by_year
    trades = time_stop_trades(bars, signal_bar, side, horizon=26, mode=1)     # une position à la fois
    m = summarize(trades, bars, atr_bps, cost_bps=5.0, n_candidates=len(signal_bar))

    from envelope import atr_stop_levels, stop_trades
    level = atr_stop_levels(bars, signal_bar, side, atr, k=2.0)               # SL-A, niveau en prix par signal
    trades = stop_trades(bars, signal_bar, side, horizon=26, level=level, dynamic=True)

    from envelope import route_levels                                           # moteur de régimes
    level = route_levels(bars, signal_bar, side, atr, seg_len, family, {"F2b": None, "F3": ("SL-B", 0.0)})
    trades = stop_trades(bars, signal_bar, side, horizon=26, level=level, dynamic=False)   # cooldown

L'exécution d'un trade, la stratégie native (ancre P6.5d), le capital et le drawdown viennent de `estimand.stoploss`
(#KAKALMAN, copie certifiée) ; les frais de `labeling.costs`. Rien n'y est réécrit.
"""
from envelope.metrics import (DEV_MONTHS, by_year, effect_ci, equity_curve_sized, mean_ci, risk_weights, summarize,
                              summarize_sized, trade_frame)
from envelope.sequential import dev_signals, time_stop_trades
from envelope.stops import (atr_stop_levels, route_levels, rule_levels, segment_extremum, stop_distance, stop_trades,
                            structural_stop_levels)

__all__ = ["dev_signals", "time_stop_trades", "summarize", "mean_ci", "by_year", "trade_frame", "DEV_MONTHS",
           "risk_weights", "equity_curve_sized", "summarize_sized", "effect_ci", "atr_stop_levels",
           "segment_extremum", "structural_stop_levels", "stop_distance", "stop_trades", "rule_levels",
           "route_levels"]
