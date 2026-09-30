"""EXP-D01 — acquisition et audit des séries de marché des actifs de transfert (hors BTC Bitstamp).

- `coinbase` : bougies publiques de 15 min de Coinbase Exchange (sans clé) : SOL/USD ;
- `histdata` : bougies d'une minute de HistData.com (gratuites, bid, EST sans heure d'été) : CFD or et WTI ;
- `bars` : agrégation exacte de sous-barres en barres de 30 min alignées sur :00 et :30 UTC ;
- `fred` : série quotidienne publique de FRED, référence externe de l'audit (spot WTI de l'EIA) ;
- `audit` : contrôle descriptif d'une série de barres 30 min (trous, cohérence OHLC, séances, sauts extrêmes).

Toute série écrite suit le schéma de `utils.data_loader.load_ohlc` (time = ouverture de la barre en UTC, timestamp,
open, high, low, close, volume) et porte un `.meta.json` versionné (provenance, instrument, empreintes). La réserve
2026 n'est jamais téléchargée.
"""
from marketdata.audit import audit_bars
from marketdata.bars import aggregate_30m
from marketdata.coinbase import build_coinbase_csv, fetch_candles, parse_candles
from marketdata.fred import build_fred_csv, parse_fred
from marketdata.histdata import build_histdata_csv, form_fields, parse_m1

__all__ = ["aggregate_30m", "audit_bars", "build_coinbase_csv", "build_fred_csv", "build_histdata_csv",
           "fetch_candles", "form_fields", "parse_candles", "parse_fred", "parse_m1"]
