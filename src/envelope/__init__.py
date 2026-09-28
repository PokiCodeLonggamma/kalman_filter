"""Étape C — enveloppe mécanique séquentielle (EXP-C01 : sortie à horizon fixe, sans stop ni take-profit).

    from envelope import dev_signals, time_stop_trades, summarize, by_year
    trades = time_stop_trades(bars, signal_bar, side, horizon=26, mode=1)     # une position à la fois
    m = summarize(trades, bars, atr_bps, cost_bps=5.0, n_candidates=len(signal_bar))

L'exécution d'un trade, la stratégie native (ancre P6.5d), le capital et le drawdown viennent de `estimand.stoploss`
(#KAKALMAN, copie certifiée) ; les frais de `labeling.costs`. Rien n'y est réécrit.
"""
from envelope.metrics import DEV_MONTHS, by_year, mean_ci, summarize, trade_frame
from envelope.sequential import dev_signals, time_stop_trades

__all__ = ["dev_signals", "time_stop_trades", "summarize", "mean_ci", "by_year", "trade_frame", "DEV_MONTHS"]
