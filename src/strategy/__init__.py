"""Étape D — stratégie cœur RE-1 figée, applicable à n'importe quel OHLC de 30 min (`strategy.re1`)."""
from strategy.re1 import (F3_BOUNDARY, FLOOR, H, LEG_ATR_P50_BTC, NIS_Z100_P75_BTC, RETRACE_MIN, RISK_BPS, RULES,
                          frozen_masks, load_asset, metrics, run_re1, sample_years)

__all__ = ["F3_BOUNDARY", "FLOOR", "H", "LEG_ATR_P50_BTC", "NIS_Z100_P75_BTC", "RETRACE_MIN", "RISK_BPS", "RULES",
           "frozen_masks", "load_asset", "metrics", "run_re1", "sample_years"]
