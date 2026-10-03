# EXP-D03 — Profilage des extrêmes, filtre de compression (ATR) et portefeuille BTC + SOL

*Demande du porteur du 2026-10-03, après ses décisions : WFO abandonné, RE-1 gelée version finale du moteur, exploitation
en fonds propres (`RESEARCH_LOG.md`, entrée EXP-D03). Calcul : `python experiments/D03/run_D03.py --calcul` (41 s).
RE-1 gelée (seuils BTC gelés, R0 = 100, frontière 0,85, H = 26, verrou 26), 5 bps (10 bps en lecture), 0,25 % du capital
par ATR14(t). Aucune optimisation. Annexes générées en fin de document.*

## Verdict

- **Action 1 : le « calme » des grands gagnants est surtout un effet de la mesure.**
  - Classés par rendement net en ATR, les 5 % meilleurs trades naissent à ATR plus bas que les autres : médiane 37 bps
    contre 48 ; 69 % sous la médiane de l'Usure.
  - Classés en bps, ils naissent à ATR plus haut : médiane 75 bps, 21 % seulement sous la médiane de l'Usure. Les deux
    classements n'ont que 53 trades en commun sur 104.
  - Avec un risque de 0,25 % par ATR, un trade ouvert à ATR bas engage plus de notionnel : c'est la taille de position,
    pas le marché, qui fait peser les états calmes dans le capital.
  - %B, écart à l'EMA 200 et `leg_atr` ne séparent pas les groupes.
- **Action 2 : le filtre ATR ≤ P60 glissant réduit l'exposition sans améliorer le Calmar.**
  - Il garde les 21 trades du top 1 % et 92 des 104 trades Alpha. Il retire 557 trades d'Usure (−0,091 ATR en moyenne),
    mais aussi 12 trades Alpha : l'ensemble retiré gagnait +0,111 ATR en moyenne.
  - Calmar 0,34 contre 0,32 ; écart apparié +0,03, Calmar meilleur sur 43 % seulement des chemins réordonnés. PnL +125 %
    contre +159 %, MDD −22,3 % contre −28,4 %.
  - Le gain d'espérance ne vient que de 2020-2025, la période de construction de RE-1 ; il ne se retrouve ni en
    2015-2019, ni sur SOL.
- **Action 3 : le portefeuille BTC + SOL améliore le rendement par unité de drawdown.**
  - De juillet 2021 à 2025 : Calmar 1,58 contre 1,18 pour BTC seul et 0,59 pour SOL seul ; PnL +163 % pour un MDD de
    −15,2 %.
  - Les rendements mensuels des deux actifs ne sont pas corrélés (−0,04).
  - La plus longue période sous le pic n'est pas raccourcie (238 jours contre 224 pour BTC seul).
  - Le gain repose sur l'avantage de SOL, dont l'IC contient 0 (+0,190 ATR [−0,079 ; +0,484]).

## 1. Contrôles bloquants (passés)

- Empreintes des séries BTC et SOL conformes ; réserve 2026 tronquée ; panne de 215 barres retirée sur BTC.
- RE-1 gelée BTC 2015-2025 identique aux 2 075 trades de D02.
- RE-1 gelée SOL identique à `run_re1`, métriques de D01 à 10⁻⁵ près (769 trades, 5 et 10 bps).
- Le portefeuille d'une seule jambe redonne le PnL et le MDD du capital valorisé du dépôt (10⁻¹⁰).

## 2. Action 1 — profil à t des trades Alpha (5 %) et Usure (95 %), BTC 2015-2025

- `[OBS]` **Concentration :** les 104 trades Alpha (classés en ATR) font 266 % de la somme nette en ATR et 226 % de la
  somme en bps ; les 104 meilleurs en bps font 305 % de la somme en bps.
- `[OBS]` **Volatilité au signal** (médiane [P25 ; P75]) :

| Variable | Usure | Alpha classé en ATR | Alpha classé en bps |
|---|---|---|---|
| ATR14 (bps) | 47,8 [32,8 ; 70,5] | 36,9 [26,6 ; 50,1] | 74,9 [49,6 ; 117,1] |
| ATR14, rang sur 24 mois | 0,34 [0,14 ; 0,64] | 0,23 [0,08 ; 0,39] | 0,62 [0,32 ; 0,85] |
| Largeur de Bollinger, rang sur 24 mois | 0,28 [0,11 ; 0,51] | 0,17 [0,07 ; 0,35] | 0,46 [0,24 ; 0,73] |
| Largeur de Bollinger (%) | 1,22 [0,77 ; 2,01] | 0,91 [0,67 ; 1,36] | 2,02 [1,26 ; 3,35] |

- `[OBS]` **Par quintile du rang d'ATR** (bas → haut), espérance par trade :
  - en ATR : +0,297, +0,202, +0,340, +0,090, +0,159 ;
  - en bps : +4,8, +7,4, +15,0, +2,6, +21,2.
  - Le quintile le plus volatil porte 42 % de la somme en bps, mais 15 % de la somme en ATR et aucun trade du top 1 %.
- `[OBS]` **Aucune séparation** sur le %B orienté (médianes 0,62 contre 0,64), l'écart à l'EMA 200 orienté (+1,6 contre
  +0,8 ATR, quintiles non monotones) ou `leg_atr` / P50 local (0,77 contre 0,79).
- `[OBS]` **Heure UTC de l'entrée** (lecture descriptive, 6 blocs, aucun IC) :
  - 04-08 h : +0,689 ATR et +26,8 bps sur 391 trades, avec 29 trades Alpha et 6 du top 1 % ;
  - 16-20 h : −0,205 ATR et −16,3 bps sur 240 trades, avec 5 trades Alpha.

## 3. Action 2 — filtre ATR14 ≤ P60 glissant sur 24 mois

**BTC 2015-2025, 5 bps**

| Variante | PnL : 0,25 %/ATR ; 1x ; bps (1x) | PF (1x) | WR | Espérance ATR [IC] ; bps | MDD : 0,25 %/ATR ; 1x | Trades (/mois) | Durée médiane | Part des frais (1x) ; brut ; frais (ATR) | Calmar 0,25 %/ATR |
|---|---|---|---|---|---|---|---|---|---|
| RE-1 gelée | +159 % ; +396 % ; +21 149 | 1,15 | 43,9 % | +0,218 [+0,032 ; +0,401] ; +10,2 | −28,4 % ; −53,0 % | 2 075 (15,7) | 26 b ; 13 h | 33 % ; +0,34 ; 0,12 | 0,32 |
| RE-1 + filtre ATR (entrées figées) | +125 % ; +205 % ; +13 454 | 1,17 | 43,2 % | +0,258 [+0,024 ; +0,486] ; +8,9 | −22,3 % ; −40,2 % | 1 506 (11,4) | 26 b ; 13 h | 36 % ; +0,41 ; 0,15 | 0,34 |
| RE-1 + filtre ATR (séquentiel) | +102 % ; +175 % ; +12 519 | 1,15 | 42,8 % | +0,224 [−0,010 ; +0,446] ; +8,1 | −23,7 % ; −38,4 % | 1 545 (11,7) | 26 b ; 13 h | 38 % ; +0,37 ; 0,15 | 0,28 |

- `[OBS]` **Écarts appariés face à RE-1 gelée** (entrées figées) :
  - espérance +0,040 ATR [−0,056 ; +0,131] mais −1,3 bps [−9,8 ; +6,5] ;
  - rendement −1,4 point par an [−5,4 ; +2,1] ;
  - MDD +6,1 points, moins profond sur 71 % des chemins réordonnés ;
  - Calmar +0,03, meilleur sur 43 % des chemins.
  - En séquentiel : +0,006 ATR ; les 51 trades libérés du verrou font −0,221 ATR en moyenne.
- `[OBS]` **Ce que le filtre retire :**
  - 569 trades (27 %) : 557 d'Usure, à −0,091 ATR de moyenne, et 12 trades Alpha ; l'ensemble retiré gagnait +0,111 ATR ;
  - il garde les 21 trades du top 1 % et 92 des 104 trades Alpha.
- `[OBS]` **Par période** (entrées figées) :
  - 2015-2019 : +0,029 contre +0,064 ATR ;
  - 2020-2025 : +0,456 contre +0,357, MDD à 1x −22,0 % contre −43,9 %, Calmar 1,11 contre 1,12.
- `[OBS]` **À 10 bps :** Calmar 0,09 dans les deux cas.
- `[OBS]` **SOL, hors de l'échantillon de l'idée** (entrées du S2 2023 à 2025) : +0,243 contre +0,252 ATR ; Calmar 0,57
  contre 0,76.

## 4. Action 3 — portefeuille RE-1 gelée BTC + SOL, entrées du 2021-07-01 au 2025-12-31

**5 bps, 0,25 %/ATR par trade sur chaque actif (entre parenthèses : 1x par position)**

| Série | PnL | PF (1x) | WR | Espérance bps | MDD | Trades (/mois) | Durée médiane | Part des frais | Calmar | Plus longue période sous le pic | Mois positifs |
|---|---|---|---|---|---|---|---|---|---|---|---|
| BTC seul | +90 % (+118 %) | 1,20 | 43,1 % | +11,3 | −12,9 % (−29,9 %) | 806 (14,9) | 26 b | 31 % | 1,18 | 224 j | 54 % |
| SOL seul | +39 % (+173 %) | 1,17 | 44,1 % | +19,2 | −13,1 % (−42,3 %) | 769 (14,2) | 26 b | 21 % | 0,59 | 567 j | 56 % |
| Portefeuille BTC + SOL | +163 % (+478 %) | 1,18 | 43,6 % | +15,1 | −15,2 % (−40,1 %) | 1 575 (29,1) | 26 b | 25 % | 1,58 | 238 j | 59 % |

- `[OBS]` **Diversification :** les rendements mensuels de BTC et de SOL ne sont pas corrélés (−0,04). Le portefeuille
  est en position 37 % du temps, avec les deux positions ouvertes 7 % du temps.
- `[OBS]` **Exposition :** exposition brute maximale 2,0 à 0,25 %/ATR et 2,3 à 1x par position.
- `[OBS]` **À 10 bps :** PnL +80 %, MDD −18,1 %, Calmar 0,77, contre 0,59 pour BTC seul et 0,32 pour SOL seul.
- `[OBS]` **Espérance de SOL seul** sur la période : +0,190 ATR [−0,079 ; +0,484], brut +0,25 et frais 0,06 ATR. Celle
  de BTC : +0,370 [+0,050 ; +0,686], mais 2021-2025 est dans la période de construction de RE-1.

## 5. Lecture

- `[HYP]` **Taille de position.** Le risque de 0,25 % par ATR concentre le capital sur les trades ouverts à ATR bas. En
  bps, les plus gros gains de RE-1 viennent au contraire des marchés agités. Un filtre de compression trie donc surtout
  les trades selon leur taille de position, pas selon leur qualité.
- `[HYP]` **Le filtre ATR revient à désendetter.** Moins de trades, un drawdown moins profond, un PnL plus faible, et un
  Calmar inchangé, comme le break-even de C03.
- `[HYP]` **Le seul levier mesuré qui améliore le rapport rendement / drawdown est la diversification.** Il ne vaut que
  si l'avantage de chaque actif est réel ; celui de SOL n'est pas établi à 95 %.

## 6. Pistes (à cadrer par le porteur, rien de lancé)

1. **Filtre ATR :** non retenu. Aucun gain de Calmar ; avec l'Usure, il retire 12 trades Alpha et l'ensemble retiré
   gagnait en moyenne ; son gain se limite à 2020-2025 et ne se retrouve pas sur SOL.
2. **Portefeuille :** confirmer l'avantage de SOL avant d'y engager du capital, par une période jamais lue (2026, si le
   porteur lève la réserve) ou par un suivi sans argent réel.
3. **Heure UTC :** le contraste 04-08 h / 16-20 h est descriptif ; il demanderait une lecture sur des données non vues
   (SOL, BTC 2013-2014) avant toute règle.
