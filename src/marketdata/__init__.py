"""EXP-D01 — acquisition et audit des séries de marché des actifs de transfert (hors BTC Bitstamp).

- `coinbase` : bougies publiques de 15 min de Coinbase Exchange (sans clé) : SOL/USD, AVAX/USD (D02.0) ;
- `bitstamp` : barres natives de 30 min de Bitstamp (sans clé) : BTC/USD depuis 2013 (D02.0 ; import direct) ;
- `histdata` : bougies d'une minute de HistData.com (gratuites, bid ; horloge EET/EEST − 7 h convertie en UTC) : CFD or ;
- `bars` : agrégation exacte de sous-barres en barres de 30 min alignées sur :00 et :30 UTC ;
- `alpaca` : barres de 30 min d'actions et d'ETF américains (API Alpaca v2, flux SIP), séance régulière : SPY, XLE ;
- `fred` : série quotidienne publique de FRED, référence externe de l'audit (spot WTI de l'EIA) ;
- `audit` : contrôle descriptif d'une série de barres 30 min (trous, cohérence OHLC, séances, sauts extrêmes) ;
- `saxo` (D01.7) et `ctrader` (D05.1, compte FTMO, JSON sur WebSocket) : API à OAuth 2, importés à part.

Toute série écrite suit le schéma de `utils.data_loader.load_ohlc` (time = ouverture de la barre en UTC, timestamp,
open, high, low, close, volume) et porte un `.meta.json` versionné (provenance, instrument, empreintes). Aucune barre
de la réserve 2026 n'est écrite hors d'une levée explicite (`reserve.levee`).
"""
from marketdata.alpaca import build_alpaca_csv, fetch_bars, regular_session
from marketdata.audit import audit_bars
from marketdata.bars import aggregate_30m
from marketdata.coinbase import build_coinbase_csv, fetch_candles, parse_candles
from marketdata.fred import build_fred_csv, parse_fred
from marketdata.histdata import build_histdata_csv, form_fields, parse_m1

__all__ = ["aggregate_30m", "audit_bars", "build_alpaca_csv", "build_coinbase_csv", "build_fred_csv",
           "build_histdata_csv", "fetch_bars", "fetch_candles", "form_fields", "parse_candles", "parse_fred", "parse_m1",
           "regular_session"]
