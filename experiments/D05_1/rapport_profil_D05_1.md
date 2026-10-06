# RE-1 sur les actifs hors crypto, données et frictions FTMO (D05.1, étape 2)

*2026-10-06. `run_profil_D05_1.py` (cadrage dans l'en-tête du script). Stratégie : RE-1 version finale, figée (stop
catastrophe à 4 ATR), sur les barres M30 FTMO, de la première barre disponible au 2026-10-01. Frictions FTMO trade par
trade : écart à l'heure du trade, commission, swaps. SAN absent : il n'a pas été exporté. Sorties :
`profil_tradfi_D05_1.csv`, `anatomie_tradfi_D05_1.csv`, `annees_tradfi_D05_1.csv`, `correlations_tradfi_D05_1.csv`,
`trades_tradfi_D05_1.csv.gz`. Repère crypto recalculé avec l'écart réel d'AVAX (export v3).*

## 1. Tableau des 8 métriques (frictions FTMO complètes)

| Actif (depuis) | PnL net : 0,25 %/ATR ; 1x ; bps (1x) | PF | WR | Espérance : ATR ; bps | MDD : 0,25 %/ATR ; 1x | Trades (/mois) | Durée médiane | Part des frais |
|---|---|---|---|---|---|---|---|---|
| Or (2020-05) | +8,6 % ; +12,3 % ; +1 341 | 1,07 | 41,7 % | +0,019 ; +1,9 | −18,1 % ; −18,3 % | 713 (9,3) | 26 b ; 13 h | 50 % |
| US100 (2020-11) | +2,3 % ; +5,1 % ; +720 | 1,04 | 37,7 % | −0,038 ; +1,1 | −16,1 % ; −21,2 % | 674 (9,5) | 24 b ; 12,5 h | 55 % |
| US30 (2020-11) | −8,1 % ; −11,8 % ; −1 133 | 0,92 | 35,6 % | −0,108 ; −1,6 | −13,0 % ; −16,2 % | 700 (9,9) | 22 b ; 11,5 h | brut < 0 |
| GER40 (2020-11) | +3,2 % ; −4,9 % ; −373 | 0,98 | 38,8 % | +0,086 ; −0,6 | −11,4 % ; −14,1 % | 619 (8,8) | 26 b ; 13 h | 169 % |
| GBPJPY (2020-04) | +3,9 % ; +4,3 % ; +474 | 1,05 | 42,2 % | +0,006 ; +0,6 | −7,5 % ; −7,5 % | 759 (9,7) | 26 b ; 13 h | 75 % |
| WTI (2020-11) | −40,2 % ; −49,5 % ; −6 089 | 0,85 | 36,5 % | −0,311 ; −9,5 | −41,3 % ; −51,1 % | 641 (9,1) | 26 b ; 13 h | 372 % |
| Brent (2020-11) | −41,3 % ; −45,4 % ; −5 424 | 0,84 | 35,6 % | −0,394 ; −9,9 | −45,4 % ; −53,2 % | 548 (7,7) | 24 b ; 13 h | 370 % |

- **Sans les swaps** (l'unité des swaps du pétrole n'est pas vérifiée), espérance en ATR :

  | Actif | Or | US100 | US30 | GER40 | GBPJPY | WTI | Brent |
  |---|---|---|---|---|---|---|---|
  | Espérance sans swaps (ATR) | +0,061 | +0,005 | −0,072 | +0,120 | +0,025 | −0,204 | −0,222 |

- **Frictions moyennes par trade**, en ATR et en bps :

  | Actif | Total (ATR) | Écart | Commission | Swap | Total (bps) |
  |---|---|---|---|---|---|
  | Or | 0,116 | 0,065 | 0,009 | 0,042 | 1,9 |
  | US100 | 0,075 | 0,033 | 0 | 0,042 | 1,3 |
  | US30 | 0,079 | 0,043 | 0 | 0,036 | 0,9 |
  | GER40 | 0,099 | 0,064 | 0 | 0,034 | 1,5 |
  | GBPJPY | 0,193 | 0,126 | 0,048 | 0,019 | 1,8 |
  | WTI | 0,365 | 0,257 | 0 | 0,107 | 13,0 |
  | Brent | 0,386 | 0,214 | 0 | 0,172 | 13,6 |

## 2. Anatomie du net par trade (ATR)

| Actif | Brut moyen | Net moyen | Net médian | P99 | Max | Net total | Sans les 1 % meilleurs | Sans les 5 % meilleurs | ≥ 3 ATR / an | ≥ 5 ATR / an | ≥ 10 ATR / an | ≤ −3 ATR / an |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Or | +0,135 | +0,019 | −1,32 | 12,9 | 21,9 | +13,9 | −94,8 | −362,3 | 20,9 | 11,4 | 2,2 | 21,7 |
| US100 | +0,038 | −0,038 | −1,57 | 11,3 | 15,0 | −25,3 | −115,4 | −372,3 | 23,2 | 14,6 | 2,9 | 23,2 |
| US30 | −0,029 | −0,108 | −1,58 | 14,9 | 30,4 | −75,6 | −217,5 | −504,6 | 21,4 | 12,6 | 3,6 | 25,4 |
| GER40 | +0,185 | +0,086 | −1,37 | 12,1 | 17,2 | +53,3 | −32,6 | −278,9 | 20,2 | 12,4 | 3,2 | 17,5 |
| GBPJPY | +0,199 | +0,006 | −1,02 | 11,8 | 22,9 | +4,3 | −116,8 | −374,4 | 20,8 | 9,8 | 2,3 | 18,3 |
| WTI | +0,054 | −0,311 | −1,71 | 11,6 | 20,4 | −199,2 | −282,9 | −511,3 | 21,2 | 11,4 | 1,9 | 23,8 |
| Brent | −0,009 | −0,394 | −1,80 | 9,7 | 15,0 | −216,1 | −283,0 | −458,2 | 16,8 | 8,5 | 1,0 | 17,6 |
| *BTC (repère, fenêtre D05)* | +0,399 | +0,135 | −0,87 | 14,0 | 32,5 | +112,5 | −32,8 | −392,2 | 30,4 | 17,8 | 5,8 | 27,0 |
| *Panier crypto (repère)* | +0,318 | +0,035 | −1,01 | 12,3 | 246,7 | +139,4 | −860,2 | −2 285 | 135,0 | 72,0 | 16,4 | 131,2 |

- [OBS] **La forme est celle de BTC, mais en plus petit.** Un corps perdant : médiane de −1,0 à −1,8 ATR, et 17 à 25
  trades par an sous −3 ATR. Une queue droite qui porte tout : sans les 1 % meilleurs trades, tous les actifs sont
  négatifs, BTC compris.
- [OBS] **Les grands trades sont presque aussi fréquents que sur BTC, mais moins grands.**
  - Trades nets de +5 ATR ou plus : 8,5 à 14,6 par an hors crypto, contre 17,8 pour BTC.
  - Trades de +10 ATR ou plus : 1,0 à 3,6 par an, contre 5,8 pour BTC.
  - P99 : 9,7 à 14,9 ATR, contre 14,0 pour BTC.
- [OBS] **Brut moyen :** GBPJPY +0,20 et GER40 +0,19 ATR, les plus hauts hors crypto ; or +0,14. BTC est à +0,40.
  US30 et Brent sont négatifs ou nuls avant frais.
- [OBS] **Le pétrole perd surtout par l'écart.** Écart de 7,1 à 8,6 bps, soit 0,21 à 0,26 ATR. Sans les swaps, il reste
  à −0,20 et −0,22 ATR.
- [OBS] **Le repère du panier crypto contient le trade XRP du 2023-07-13** (jugement Ripple contre la SEC, +71 % en
  13 h, soit 247 ATR). C'est un vrai cygne noir, déjà dans les données de D05.

## 3. Années (net total en ATR) et lien avec le panier crypto

| Année | Or | US100 | US30 | GER40 | GBPJPY | WTI | Brent |
|---|---|---|---|---|---|---|---|
| 2020 (partielle) | +7,7 | −9,6 | −24,0 | −4,8 | +7,1 | −21,4 | −28,8 |
| 2021 | −11,0 | −13,2 | +35,2 | +10,7 | +1,9 | −76,0 | −64,1 |
| 2022 | +69,5 | +9,5 | −14,8 | +51,7 | +0,1 | +26,2 | +0,1 |
| 2023 | −70,8 | +0,9 | +47,5 | −20,4 | −4,8 | −52,6 | −72,9 |
| 2024 | −10,4 | −30,0 | −17,4 | +50,8 | +46,0 | −49,7 | −53,0 |
| 2025 | −40,4 | −0,9 | −68,6 | +7,2 | −37,5 | +5,1 | +4,9 |
| 2026 (9 mois) | +69,2 | +18,0 | −33,6 | −41,9 | −8,6 | −30,8 | −2,3 |

**Mois 2021-10 → 2026-09 (60 mois, dont 33 où le panier crypto perd) ; net en ATR × 0,25 %, sans composition :**

| Actif | Corrélation mensuelle avec le panier crypto | Net des mois où le panier perd | Net des mois où il gagne | Part de mois positifs quand le panier perd |
|---|---|---|---|---|
| Or | −0,01 | −7,1 % | +9,7 % | 49 % |
| US100 | +0,11 | −4,7 % | +2,3 % | 49 % |
| US30 | −0,08 | +10,2 % | −24,2 % | 39 % |
| GER40 | −0,15 | +8,1 % | −3,2 % | 52 % |
| GBPJPY | +0,02 | +3,9 % | +6,0 % | 49 % |
| WTI | −0,43 | +2,0 % | −30,0 % | 52 % |
| Brent | +0,06 | −34,2 % | +2,4 % | 30 % |

- [OBS] **Corrélation mensuelle avec le panier crypto :** proche de zéro partout (−0,15 à +0,11), sauf le WTI (−0,43).
- [OBS] **Quand le panier crypto perd :** US30 et GER40 gagnent (+10,2 % et +8,1 %), mais US30 perd ensuite davantage
  quand il gagne (−24,2 %).
- [HYP] Ce sont des pistes pour l'étape 3, pas des conclusions : 60 mois, gain total voisin de zéro hors pétrole.

## 4. Limites

- [HYP] **Swaps du pétrole pris à la lettre de la fiche :** 25 bps par nuit en short. Unité à vérifier ; l'espérance
  sans swaps est donnée au §1.
- **Écarts :** mesurés sur dix jours de 2026, appliqués à 2020-2026.
- **Rollover :** pris à 17:00 New York.
- **Seuils de RE-1 :** gelés sur BTC (transposition sans réglage).
- **Historiques :** de moins de six ans, depuis le 2020-11 pour les indices et le pétrole.
- **Données :** déjà lues, sur Saxo 2020-2025 en D01.7 et D05.1 ; 2026 inclus.
- **Or :** sur les barres FTMO, son brut est plus faible que sur HistData (fenêtre D05 : +0,14 contre +0,36 ATR par
  trade). L'écart est à comprendre avant l'inclusion.
- **SAN :** non mesuré, il n'a pas été exporté.
