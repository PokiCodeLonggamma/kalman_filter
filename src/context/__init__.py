"""Contexte de marché pour les filtres d'entrée (EXP-C04 : tendance macro, EMA et Kalman lent sur bougies 4 h).

    from context import ema_trend, htf_kalman_trend, counter_trend
    trend = ema_trend(bars.close, 200)                         # +1 / −1 à la clôture de chaque barre 30 min
    k4 = htf_kalman_trend(bars, hours=4)                        # x1 du filtre v2.1 sur bougies 4 h closes
    veto = counter_trend(side, trend[signal_bar])              # signal contre la tendance : ignoré

EXP-D03 : compression (`bollinger`, %B et largeur relative) et quantile / rang glissants causaux sur une fenêtre de
temps (`trailing_quantile`, `trailing_rank`).
"""
from context.trend import BAR, WARMUP_HTF, counter_trend, ema, ema_trend, htf_bars, htf_kalman_trend
from context.volatility import bollinger, trailing_quantile, trailing_rank

__all__ = ["ema", "ema_trend", "htf_bars", "htf_kalman_trend", "counter_trend", "BAR", "WARMUP_HTF", "bollinger", "trailing_quantile",
           "trailing_rank"]
