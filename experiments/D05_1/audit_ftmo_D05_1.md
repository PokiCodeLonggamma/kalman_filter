# Vérification des données FTMO (D05.1)

*Généré par `audit_ftmo_D05_1.py` le 2026-10-06 00:27 UTC ; fiches : `export_2026-10-06_v2/ftmo_symboles_fiches.csv` ; 196 symboles actifs sur le compte.*

## 1. Bougies M30

| Actif | Symbole | Barres | Première | Dernière | Trous | Plus long (h) | Motif le plus fréquent | Plates |
|---|---|---|---|---|---|---|---|---|
| US100 | US100.cash | 69756 | 2020-11-08 23:30 | 2026-10-05 22:30 | 1532 | 76,5 | Tue 21:00 UTC : 199 fois, médiane 1.0 h | 11 |
| US30 | US30.cash | 69756 | 2020-11-08 23:00 | 2026-10-05 22:30 | 1529 | 76,5 | Tue 21:00 UTC : 199 fois, médiane 1.0 h | 15 |
| GER40 | GER40.cash | 68683 | 2020-11-08 23:00 | 2026-10-05 22:30 | 1507 | 122,0 | Tue 21:00 UTC : 199 fois, médiane 1.0 h | 18 |
| GBPJPY | GBPJPY | 81041 | 2020-04-01 18:00 | 2026-10-05 22:30 | 346 | 72,0 | Fri 21:00 UTC : 214 fois, médiane 48.0 h | 2 |
| WTI | USOIL.cash | 69796 | 2020-11-08 23:00 | 2026-10-05 22:30 | 1529 | 76,0 | Tue 21:00 UTC : 199 fois, médiane 1.0 h | 20 |
| BRENT | UKOIL.cash | 63808 | 2020-11-08 23:00 | 2026-10-05 20:00 | 1525 | 77,0 | Tue 21:00 UTC : 199 fois, médiane 3.0 h | 16 |
| XAU | XAUUSD | 75774 | 2020-05-06 15:00 | 2026-10-05 22:30 | 1673 | 77,0 | Wed 21:00 UTC : 213 fois, médiane 1.0 h | 31 |
| SAN | SAN | absent | | | | | | |
| BTC | BTCUSD | 103486 | 2020-07-08 07:30 | 2026-10-05 22:30 | 369 | 57,0 | Sat 17:00 UTC : 83 fois, médiane 4.0 h | 37 |
| ETH | ETHUSD | 103410 | 2020-07-08 07:30 | 2026-10-05 22:30 | 368 | 57,0 | Sat 17:00 UTC : 83 fois, médiane 4.0 h | 60 |
| SOL | SOLUSD | 24595 | 2025-04-17 09:00 | 2026-10-05 22:30 | 76 | 34,5 | Sat 05:00 UTC : 14 fois, médiane 14.0 h | 1 |
| AVAX | AVAUSD | absent | | | | | | |
| XRP | XRPUSD | 103292 | 2020-07-13 14:30 | 2026-10-05 22:30 | 367 | 50,0 | Sat 17:00 UTC : 83 fois, médiane 4.0 h | 30 |

## 2. Écarts (ticks, ouverture des barres, bps du milieu)

| Actif | Période | Barres | Médiane | Moyenne | P90 | Max | Semaine | Week-end |
|---|---|---|---|---|---|---|---|---|
| US100 | 2026-09-27 → 2026-10-05 | 271 | 0,50 | 0,53 | 0,64 | 0,7 | 0,50 | 0,48 |
| US30 | 2026-09-27 → 2026-10-05 | 271 | 0,48 | 0,47 | 0,52 | 0,6 | 0,48 | 0,50 |
| GER40 | 2026-09-27 → 2026-10-05 | 269 | 0,84 | 0,89 | 1,38 | 1,5 | 0,80 | 1,33 |
| GBPJPY | 2026-09-27 → 2026-10-05 | 290 | 1,01 | 1,29 | 1,39 | 14,6 | 1,01 | 1,32 |
| WTI | 2026-09-27 → 2026-10-05 | 271 | 8,61 | 8,58 | 9,45 | 9,9 | 8,64 | 7,49 |
| BRENT | 2026-09-28 → 2026-10-05 | 245 | 7,09 | 7,02 | 7,66 | 7,9 | 7,09 | — |
| XAU | 2026-09-27 → 2026-10-05 | 271 | 0,99 | 1,01 | 1,11 | 1,2 | 0,99 | 1,17 |
| BTC | 2026-09-25 → 2026-10-05 | 435 | 0,12 | 0,12 | 0,12 | 0,4 | 0,12 | 0,12 |
| ETH | 2026-09-25 → 2026-10-05 | 435 | 2,23 | 2,23 | 2,25 | 2,5 | 2,23 | 2,23 |
| SOL | 2026-09-25 → 2026-10-05 | 435 | 2,50 | 2,50 | 2,54 | 2,6 | 2,52 | 2,47 |
| XRP | 2026-09-25 → 2026-10-05 | 435 | 9,99 | 9,96 | 10,10 | 10,2 | 10,01 | 9,90 |

## 3. Fiches : swaps et commission (bps du notionnel au dernier prix ; coût positif)

| Actif | Description | Swap (type) | Long / nuit | Short / nuit | Triple | Commission (type) | Commission / côté | Levier |
|---|---|---|---|---|---|---|---|---|
| US100 | NASDAQ 100 Index, Spot CFD | Pips (-6.9638 / 0.3417) | +2,24 | −0,11 | Friday | UsdPerOneLot (0.0) | 0,00 | 1000000:15 |
| US30 | Dow Jones Industrial Average Index, Spot CFD | Pips (-1.7655 / -9.2392) | +0,34 | +1,80 | Friday | UsdPerOneLot (0.0) | 0,00 | 1000000:15 |
| GER40 | German 40 Index, Spot CFD | Pips (-4.5178 / -0.0456) | +1,78 | +0,02 | Friday | UsdPerOneLot (0.0) | 0,00 | 1000000:15 |
| GBPJPY | Great Britain Pound vs Japanese Yen | Pips (0.317 / -2.179) | −0,15 | +1,04 | Wednesday | UsdPerOneLot (2.5) | 0,19 | 1000000:30 |
| WTI | West Texas Intermediate Crude Oil, Spot CFD | Pips (0.0497 / -0.2253) | −5,48 | +24,83 | Friday | UsdPerOneLot (0.0) | 0,00 | 1000000:15 |
| BRENT | Crude Oil Brent, Spot CFD | Pips (0.061 / -0.2758) | −5,82 | +26,32 | Friday | UsdPerOneLot (0.0) | 0,00 | 1000000:15 |
| XAU | Gold vs US Dollar, Spot CFD | Pips (-0.649 / -0.042) | +1,57 | +0,10 | Wednesday | PercentageOfTradingVolume (0.0007) | 0,07 | 1000000:15 |
| BTC | Bitcoin vs US Dollar, Spot CFD | Percentage (-30.0 / -30.0) | +8,33 | +8,33 | Friday | PercentageOfTradingVolume (0.0325) | 3,25 | 1000000:1 |
| ETH | Ethereum vs US Dollar, Spot CFD | Percentage (-30.0 / -30.0) | +8,33 | +8,33 | Friday | PercentageOfTradingVolume (0.0325) | 3,25 | 1000000:1 |
| SOL | Solana vs US Dollar, Spot CFD | Percentage (-30.0 / -30.0) | +8,33 | +8,33 | Friday | PercentageOfTradingVolume (0.0325) | 3,25 | 1000000:1 |
| XRP | Ripple vs US Dollar, Spot CFD | Percentage (-30.0 / -30.0) | +8,33 | +8,33 | Friday | PercentageOfTradingVolume (0.0325) | 3,25 | 1000000:1 |

## 4. Recoupement avec les séries du dépôt (barres communes)

| Actif | Référence | Barres communes | Corrélation 30 min | Décalage du max | Niveau médian (bps) | P1 ; P99 (bps) |
|---|---|---|---|---|---|---|
| US100 | Saxo CFD US Tech 100 (bid) | 60169 | 0,9963 | 0 | +1,2 | −3,5 ; +9,8 |
| US30 | Saxo CFD US 30 (bid) | 60107 | 0,9980 | 0 | +1,1 | −5,3 ; +9,0 |
| GER40 | Saxo CFD Germany 40 (bid) | 53502 | 0,9975 | 0 | +0,9 | −6,7 ; +8,9 |
| GBPJPY | Saxo GBPJPY (bid) | 71580 | 0,9935 | 0 | +0,9 | −1,1 ; +3,6 |
| WTI | Saxo CFD OILUScont (bid, raccordé à l'échéance) | 60668 | 0,9262 | 0 | +2,3 | −231,3 ; +134,9 |
| XAU | HistData XAUUSD (bid) | 73833 | 0,9977 | 0 | +0,5 | −2,1 ; +2,3 |
| BTC | Bitstamp BTC/USD | 103276 | 0,9922 | 0 | −4,0 | −29,9 ; +14,4 |
| ETH | Bitstamp ETH/USD | 103200 | 0,9914 | 0 | −7,1 | −44,2 ; +13,5 |
| SOL | Coinbase SOL/USD | 24362 | 0,9806 | 0 | −5,0 | −16,3 ; +10,4 |
| XRP | Bitstamp XRP/USD | 103082 | 0,9840 | 0 | −17,7 | −70,7 ; +9,0 |
