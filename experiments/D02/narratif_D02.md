# EXP-D02 — Walk-forward de RE-1 : adaptation dynamique de H, R0 et de la frontière F2b/F3 (BTC, SOL, AVAX, or)

- **Date :** 2026-10-01. **Étape :** D, D02. Protocole écrit par le porteur, audité, arbitré par lui en deux temps
  (GO pour le code et Gate 0, puis second GO pour la grille).
- **Nature :** mesure hors échantillon de la valeur ajoutée d'un recalibrage semestriel, contre RE-1 gelée et contre une
  calibration statique. RE-1 n'est pas modifiée sur la base de ces résultats sans décision du porteur.
- **Données :**
  - BTC/USD Bitstamp 2013-2025, panne de janvier 2015 retirée (215 barres, convention de D02.0) ;
  - SOL/USD Coinbase dès le 2021-06-17 ; AVAX/USD Coinbase dès le 2021-09-30 ;
  - CFD or XAU/USD HistData dès le 2009-03-15 ;
  - barres de 30 min jusqu'au 2025-12-31, empreintes égales aux audits ; ni 2026, ni ETH, ni XRP ne sont lus.
- **Code :** `src/optimization/` (noyau Numba identique à RE-1 au bit près, fenêtres, seuils par IS, règle de choix,
  séries, statistiques appariées) ; `experiments/D02/run_D02.py` (`--gate0`, `--grille`, `--rapport`).

## 0. Cadrage (validé par le porteur)

- **QUESTION :** recalibrer chaque semestre H, R0 ou la frontière F2b/F3, un à un puis ensemble, apporte-t-il hors
  échantillon une valeur nette face à RE-1 gelée et à une calibration statique ?
- **PERTINENCE AKF :** R0 est le seul axe sensible du moteur sous le reset de P ; H fixe le moment où le jugement
  cinématique est encaissé ; la frontière ne change pas la population, elle décide quels trades portent le stop SL-B.
  D02.0 a montré que l'avantage de RE-1 dépend de la période.
- **DONNÉES :** ci-dessus ; 60 semestres hors échantillon (BTC 22 de 2015 à 2025, or 29 du S2 2011 à 2025, SOL 5 du
  S2 2023 à 2025, AVAX 4 de 2024 à 2025).
- **MÉTHODE :**
  - fenêtres semestrielles calendaires, apprentissage (IS) = les 24 mois qui précèdent chaque semestre de test (OOS) ;
  - un atlas par R0 ∈ {10, 50, 100, 200, 500} ; seuils de population (P50 de `leg_atr`, P75 de `nis_z_100`) réestimés sur
    les signaux de chaque IS, pour chaque R0, puis gelés pour le semestre suivant ;
  - grille exhaustive de 700 configurations par IS (H de 6 à 60 au pas de 2, cooldown = H ; R0 ; frontière de 0,75 à
    0,95), soit 42 000 évaluations ; branches OFAT = axes de la grille passant par RE-1 (100, 26, 0,85) ;
  - choix en IS (règle du porteur) : la plus grande zone connexe de configurations admissibles (E[ATR] net > 0,
    MDD < 0) à Calmar net > 0 (0,25 %/ATR), puis la configuration la plus proche de son centre géométrique ; repli sur
    RE-1 si aucune ;
  - 10 séries hors échantillon par actif, en une course continue chacune, sur les mêmes dates : RE-1 gelée (seuils BTC
    gelés), Contrôle (paramètres de RE-1, seuils réestimés seuls), puis Statique (choix de l'IS du premier semestre) et
    WFO (choix de chaque IS) pour H, R0, la frontière et la conjointe ;
  - étanchéité : un trade d'IS est clos à la dernière barre de son IS ; une position à cheval sur deux semestres garde
    ses règles ; un trade ouvert le 2025-12-31 est clos à la dernière barre de 2025.
- **CRITÈRE DE LECTURE :** écarts appariés par mois (mêmes tirages, 2 000, graine fixe) ; « tangible » = IC 95 %
  entièrement au-dessus de 0.
  - « surpasse RE-1 gelée » : espérance (ATR et bps) et rendement tangibles, MDD non dégradé (plage des chemins pas
    entièrement défavorable) ;
  - « WFO retenu face à son Statique » : espérance tangible, Calmar en hausse sur toute la plage des chemins, MDD non
    dégradé ; sinon Statique ;
  - conjointe : règle « surpasse » face à la meilleure variante 1D ;
  - sans variante qui surpasse RE-1 gelée, absence de valeur ajoutée démontrée et RE-1 inchangée.
- **CE QUE ÇA NE PERMET PAS DE CONCLURE :**
  - BTC 2020-2025 a servi à construire RE-1 : aucun de ses semestres n'est vierge ;
  - avant 2020, RE-1 gelée porte des seuils estimés sur 2020-2025 : c'est une référence fixe, pas une stratégie causale ;
  - SOL et AVAX : 4 à 5 semestres, puissance faible ;
  - environ 90 comparaisons au coût principal : quelques « significatives » sont attendues par hasard ;
  - ni portage ni glissement au-delà des frais ; hold-out non lu.

## 1. Décisions du porteur et contrôles

- **Arbitrages (2026-10-01) :** noyau Numba (VectorBT abandonné) ; grille exhaustive ; règle de la zone connexe et de
  son centre (l'option « voisin absent = 0 », qui postulait une falaise au-delà de la grille, est rejetée) ; Calmar
  indéfini jamais choisi ; écarts appariés par mois ; sensibilités de BTC (panne gardée ; lecture dès 2016) ; stress de
  coût à 10 bps sur la crypto et à 6 bps sur l'or.
- **Gate 0 (avant la grille) :** le noyau redonne les 1 080 trades de RE-1 au bit près, la parité tient hors du point de
  RE-1 et à chaque frontière de semestre, et les ancres de D01 et D02.0 sont reproduites (`gate0_D02.md`). Ses
  contrôles bloquants (données, 1 080 trades) sont repassés en tête de la grille.

## 2. Résultats nets hors échantillon (8 métriques, coût principal)

Six séries sur dix par actif ; les dix sont dans les annexes A1 à A4. Capital continu sur toute la période hors
échantillon de l'actif (BTC 2015-2025, SOL S2 2023-2025, AVAX 2024-2025, or S2 2011-2025).

| Actif · variante (coût) | PnL : 0,25 %/ATR ; 1x ; bps (1x) | PF (1x) | WR | Espérance ATR [IC] ; bps | MDD : 0,25 %/ATR ; 1x | Trades (/mois) | Durée médiane | Part des frais (1x) ; brut ; frais (ATR) | Calmar 0,25 %/ATR |
|---|---|---|---|---|---|---|---|---|---|
| BTC · RE-1 gelée (5) | +159 % ; +396 % ; +21 149 | 1,15 | 43,9 % | +0,218 [+0,032 ; +0,401] ; +10,2 | −28,4 % ; −53,0 % | 2 075 (15,7) | 26 b ; 13 h | 33 % ; +0,34 ; 0,12 | 0,32 |
| BTC · Contrôle (5) | +114 % ; +221 % ; +16 162 | 1,12 | 43,0 % | +0,194 [+0,000 ; +0,399] ; +8,5 | −27,9 % ; −48,4 % | 1 909 (14,5) | 26 b ; 13 h | 37 % ; +0,32 ; 0,13 | 0,26 |
| BTC · WFO-R0 (5) | +214 % ; +478 % ; +22 133 | 1,18 | 43,6 % | +0,291 [+0,088 ; +0,499] ; +12,1 | −15,8 % ; −40,6 % | 1 836 (13,9) | 26 b ; 13 h | 29 % ; +0,42 ; 0,13 | 0,69 |
| BTC · WFO-H (5) | −2 % ; −20 % ; +2 260 | 1,02 | 42,4 % | +0,019 [−0,202 ; +0,244] ; +1,2 | −46,0 % ; −69,8 % | 1 847 (14,0) | 26 b ; 13 h | 80 % ; +0,14 ; 0,13 | −0,00 |
| BTC · Statique-conjointe (5) | +33 % ; −42 % ; −338 | 1,00 | 40,0 % | +0,104 [−0,164 ; +0,366] ; −0,2 | −40,2 % ; −72,9 % | 1 423 (10,8) | 36 b ; 18 h | 105 % ; +0,23 ; 0,13 | 0,07 |
| BTC · WFO-conjointe (5) | +11 % ; −39 % ; +191 | 1,00 | 41,2 % | +0,049 [−0,190 ; +0,284] ; +0,1 | −34,0 % ; −60,9 % | 1 591 (12,1) | 32 b ; 16 h | 98 % ; +0,17 ; 0,12 | 0,03 |
| SOL · RE-1 gelée (5) | +27 % ; +114 % ; +9 443 | 1,25 | 45,2 % | +0,252 [−0,191 ; +0,712] ; +23,3 | −13,1 % ; −42,3 % | 405 (13,5) | 26 b ; 13 h | 18 % ; +0,32 ; 0,07 | 0,76 |
| SOL · Contrôle (5) | +31 % ; +129 % ; +10 152 | 1,26 | 45,3 % | +0,272 [−0,172 ; +0,734] ; +24,2 | −13,1 % ; −42,3 % | 419 (14,0) | 26 b ; 13 h | 17 % ; +0,34 ; 0,07 | 0,86 |
| SOL · WFO-R0 (5) | +31 % ; +129 % ; +10 152 | 1,26 | 45,3 % | +0,272 [−0,172 ; +0,734] ; +24,2 | −13,1 % ; −42,3 % | 419 (14,0) | 26 b ; 13 h | 17 % ; +0,34 ; 0,07 | 0,86 |
| SOL · WFO-H (5) | +30 % ; +92 % ; +8 155 | 1,21 | 47,6 % | +0,241 [−0,133 ; +0,640] ; +17,8 | −11,8 % ; −38,7 % | 458 (15,3) | 18 b ; 9 h | 22 % ; +0,31 ; 0,07 | 0,93 |
| SOL · Statique-conjointe (5) | +1 % ; −26 % ; −1 786 | 0,94 | 44,3 % | +0,035 [−0,504 ; +0,597] ; −6,8 | −20,0 % ; −61,4 % | 264 (8,8) | 32 b ; 16 h | brut ≤ 0 ; +0,10 ; 0,07 | 0,02 |
| SOL · WFO-conjointe (5) | +26 % ; +78 % ; +7 539 | 1,20 | 48,2 % | +0,261 [−0,199 ; +0,731] ; +19,7 | −19,1 % ; −59,1 % | 382 (12,7) | 26 b ; 13 h | 20 % ; +0,33 ; 0,07 | 0,51 |
| AVAX · RE-1 gelée (5) | +5 % ; −17 % ; −536 | 0,99 | 42,6 % | +0,074 [−0,301 ; +0,431] ; −1,6 | −16,5 % ; −52,9 % | 329 (13,7) | 26 b ; 13 h | 148 % ; +0,14 ; 0,06 | 0,15 |
| AVAX · Contrôle (5) | +1 % ; −28 % ; −1 905 | 0,95 | 42,1 % | +0,021 [−0,332 ; +0,382] ; −5,4 | −20,6 % ; −57,9 % | 354 (14,8) | 26 b ; 13 h | brut ≤ 0 ; +0,08 ; 0,06 | 0,01 |
| AVAX · WFO-R0 (5) | −22 % ; −60 % ; −7 811 | 0,80 | 38,0 % | −0,289 [−0,626 ; +0,062] ; −24,0 | −24,3 % ; −62,5 % | 326 (13,6) | 26 b ; 13 h | brut ≤ 0 ; −0,23 ; 0,06 | −0,48 |
| AVAX · WFO-H (5) | −4 % ; −33 % ; −2 861 | 0,92 | 44,2 % | −0,031 [−0,315 ; +0,254] ; −7,5 | −17,9 % ; −53,0 % | 380 (15,8) | 20 b ; 10 h | brut ≤ 0 ; +0,03 ; 0,06 | −0,11 |
| AVAX · Statique-conjointe (5) | +1 % ; −28 % ; −1 905 | 0,95 | 42,1 % | +0,021 [−0,332 ; +0,382] ; −5,4 | −20,6 % ; −57,9 % | 354 (14,8) | 26 b ; 13 h | brut ≤ 0 ; +0,08 ; 0,06 | 0,01 |
| AVAX · WFO-conjointe (5) | −18 % ; −48 % ; −5 166 | 0,87 | 39,4 % | −0,238 [−0,615 ; +0,163] ; −16,0 | −23,3 % ; −61,2 % | 322 (13,4) | 30 b ; 15 h | brut ≤ 0 ; −0,17 ; 0,06 | −0,42 |
| XAU · RE-1 gelée (4) | −10 % ; −7 % ; −388 | 0,99 | 41,4 % | −0,045 [−0,273 ; +0,177] ; −0,2 | −31,9 % ; −32,1 % | 1 637 (9,4) | 26 b ; 13 h | 106 % ; +0,24 ; 0,29 | −0,02 |
| XAU · Contrôle (4) | −9 % ; −4 % ; −31 | 1,00 | 41,5 % | −0,046 [−0,285 ; +0,184] ; −0,0 | −32,7 % ; −32,9 % | 1 656 (9,5) | 26 b ; 13 h | 100 % ; +0,24 ; 0,29 | −0,02 |
| XAU · WFO-R0 (4) | −32 % ; −29 % ; −3 046 | 0,93 | 40,1 % | −0,196 [−0,432 ; +0,036] ; −1,9 | −46,7 % ; −43,6 % | 1 598 (9,2) | 26 b ; 13 h | 191 % ; +0,09 ; 0,29 | −0,06 |
| XAU · WFO-H (4) | −24 % ; −21 % ; −1 903 | 0,95 | 41,6 % | −0,110 [−0,394 ; +0,149] ; −1,2 | −39,2 % ; −36,7 % | 1 565 (9,0) | 26 b ; 13 h | 144 % ; +0,18 ; 0,29 | −0,05 |
| XAU · Statique-conjointe (4) | −16 % ; −15 % ; −1 149 | 0,97 | 42,2 % | −0,084 [−0,377 ; +0,180] ; −0,8 | −31,1 % ; −30,3 % | 1 519 (8,7) | 36 b ; 18 h | 123 % ; +0,20 ; 0,29 | −0,04 |
| XAU · WFO-conjointe (4) | −14 % ; −15 % ; −1 151 | 0,97 | 40,9 % | −0,067 [−0,377 ; +0,232] ; −0,9 | −24,6 % ; −24,7 % | 1 322 (7,6) | 38 b ; 20 h | 128 % ; +0,22 ; 0,29 | −0,04 |

**Stress de coût (paramètres choisis au coût principal, sans réoptimisation) : espérance ATR [IC] ; PnL à 0,25 %/ATR**

| Actif (coût) | RE-1 gelée | Contrôle | WFO-R0 | WFO-H | Statique-conjointe | WFO-conjointe |
|---|---|---|---|---|---|---|
| BTC (10 bps) | +0,093 [−0,094 ; +0,277] ; +43 % | +0,066 [−0,128 ; +0,269] ; +23 % | +0,165 [−0,043 ; +0,373] ; +85 % | −0,106 [−0,328 ; +0,120] ; −42 % | −0,023 [−0,292 ; +0,239] ; −11 % | −0,072 [−0,313 ; +0,170] ; −29 % |
| SOL (10 bps) | +0,185 [−0,262 ; +0,647] ; +18 % | +0,204 [−0,240 ; +0,669] ; +22 % | +0,204 [−0,240 ; +0,669] ; +22 % | +0,173 [−0,203 ; +0,575] ; +20 % | −0,032 [−0,567 ; +0,531] ; −3 % | +0,194 [−0,262 ; +0,666] ; +18 % |
| AVAX (10 bps) | +0,011 [−0,367 ; +0,370] ; −0 % | −0,043 [−0,394 ; +0,320] ; −5 % | −0,352 [−0,689 ; +0,001] ; −26 % | −0,095 [−0,379 ; +0,187] ; −10 % | −0,043 [−0,394 ; +0,320] ; −5 % | −0,303 [−0,681 ; +0,097] ; −23 % |
| XAU (6 bps) | −0,189 [−0,418 ; +0,035] ; −35 % | −0,189 [−0,431 ; +0,040] ; −34 % | −0,339 [−0,576 ; −0,107] ; −51 % | −0,253 [−0,537 ; +0,007] ; −44 % | −0,228 [−0,519 ; +0,039] ; −38 % | −0,212 [−0,521 ; +0,088] ; −34 % |

## 3. Comparaisons appariées (mêmes mois, 2 000 tirages)

| Actif · A contre B | Δ espérance ATR [IC] | Δ espérance bps [IC] | Δ rendement annuel [IC] | Δ MDD sorties [plage] | Δ Calmar [plage] ; part A mieux | Verdict |
|---|---|---|---|---|---|---|
| BTC · WFO-R0 / RE-1 gelée | +0,074 [−0,067 ; +0,225] | +1,9 [−7,7 ; +12,4] | +1,9 % [−4,7 % ; +9,0 %] | +11,8 % [−10,0 % ; +17,7 %] | +0,38 [−0,33 ; +0,72] ; 72 % | non |
| BTC · WFO-R0 / Contrôle | +0,098 [−0,030 ; +0,232] | +3,6 [−4,3 ; +12,2] | +3,8 % [−2,0 % ; +9,8 %] | +11,3 % [−6,9 % ; +19,5 %] | +0,44 [−0,15 ; +0,79] ; 90 % | non |
| BTC · WFO-R0 / Statique-R0 | +0,266 [+0,028 ; +0,503] | +12,4 [−1,2 ; +26,6] | +9,8 % [+0,4 % ; +19,5 %] | +21,1 % [−9,6 % ; +33,8 %] | +0,68 [−0,03 ; +1,22] ; 97 % | Statique préféré |
| BTC · WFO-H / Statique-H | −0,174 [−0,276 ; −0,074] | −7,2 [−11,9 ; −2,4] | −7,4 % [−11,2 % ; −3,4 %] | −18,3 % [−34,4 % ; −0,4 %] | −0,27 [−0,64 ; −0,08] ; 0 % | Statique préféré |
| BTC · WFO-conjointe / RE-1 gelée | −0,168 [−0,412 ; +0,076] | −10,1 [−23,7 ; +2,8] | −8,1 % [−17,5 % ; +1,5 %] | −6,4 % [−39,5 % ; +9,3 %] | −0,30 [−0,91 ; +0,07] ; 6 % | non |
| BTC · Contrôle / RE-1 gelée | −0,024 [−0,093 ; +0,049] | −1,7 [−6,3 ; +3,0] | −1,9 % [−5,1 % ; +1,5 %] | +0,5 % [−11,8 % ; +6,8 %] | −0,06 [−0,38 ; +0,13] ; 19 % | non |
| BTC 2016-2025 · WFO-R0 / RE-1 gelée | +0,004 [−0,114 ; +0,134] | −1,7 [−10,3 ; +6,8] | −1,4 % [−7,2 % ; +5,0 %] | −0,9 % [−12,4 % ; +10,7 %] | −0,13 [−0,62 ; +0,46] ; 38 % | non |
| SOL · WFO-conjointe / RE-1 gelée | +0,010 [−0,359 ; +0,419] | −3,6 [−36,0 ; +28,9] | −0,2 % [−16,4 % ; +16,7 %] | −5,5 % [−11,6 % ; +13,3 %] | −0,25 [−2,02 ; +2,39] ; 52 % | non |
| SOL · WFO-H / Statique-H | −0,031 [−0,202 ; +0,163] | −6,4 [−21,0 ; +9,6] | −0,3 % [−8,7 % ; +8,8 %] | +1,5 % [−5,1 % ; +7,9 %] | +0,09 [−1,08 ; +1,21] ; 46 % | Statique préféré |
| AVAX · WFO-R0 / RE-1 gelée | −0,363 [−0,756 ; +0,026] | −22,3 [−53,1 ; +10,2] | −14,1 % [−29,9 % ; +0,8 %] | −7,5 % [−25,7 % ; +3,3 %] | −0,64 [−2,58 ; +0,07] ; 4 % | non |
| XAU · WFO-R0 / Contrôle | −0,150 [−0,294 ; −0,021] | −1,9 [−3,8 ; −0,2] | −2,0 % [−4,0 % ; −0,2 %] | −14,1 % [−24,5 % ; +1,9 %] | −0,04 [−0,18 ; −0,00] ; 2 % | non |
| XAU · WFO-conjointe / RE-1 gelée | −0,022 [−0,335 ; +0,282] | −0,6 [−5,2 ; +3,7] | −0,3 % [−4,6 % ; +3,8 %] | +7,2 % [−27,5 % ; +19,4 %] | −0,02 [−0,19 ; +0,15] ; 45 % | non |

- `[OBS]` **Aucune variante ne surpasse RE-1 gelée, sur aucun actif.** Sur 92 comparaisons au coût principal :
  - aucun gain d'espérance tangible en ATR et en bps à la fois ;
  - un seul gain de rendement tangible : WFO-R0 contre Statique-R0 sur BTC ;
  - aucun WFO retenu face à son Statique.
- `[OBS]` **Le recalibrage dégrade plus souvent qu'il n'améliore.** Huit écarts d'espérance sont significativement
  négatifs en ATR, pour un seul positif : BTC WFO-H (contre RE-1, le Contrôle et Statique-H), BTC WFO conjoint contre
  WFO-R0, AVAX Statique-frontière, or WFO-R0 (trois fois). Le positif est WFO-R0 contre Statique-R0 sur BTC, +0,266 ATR
  [+0,028 ; +0,503], dont l'IC en bps contient 0.
- `[OBS]` **Seuils réestimés seuls (Contrôle) :** sans effet mesurable. BTC −0,024 ATR [−0,093 ; +0,049], SOL +0,020,
  AVAX −0,053, or −0,000 face à RE-1 gelée.

## 4. Mécanique

### 4.1 BTC : le gain de WFO-R0 tient à 2015-2018

- `[OBS]` **R0 choisi :** 200 du S1 2015 au S1 2017, 50 du S2 2017 au S1 2018, puis 100 jusqu'à la fin. Dès le S2 2018,
  WFO-R0 et le Contrôle prennent les mêmes trades.
- `[OBS]` Espérance par année (ATR, 5 bps) :

  | Variante | 2015 | 2016 | 2017 | 2018 | 2019 | 2020-2025 (moyenne) |
  |---|---|---|---|---|---|---|
  | RE-1 gelée | −0,272 | −0,002 | +0,469 | +0,062 | +0,098 | +0,357 (6/6) |
  | Contrôle | −0,221 | −0,113 | +0,268 | +0,197 | −0,074 | +0,355 (6/6) |
  | WFO-R0 | **+0,535** | +0,063 | +0,076 | **+0,482** | −0,074 | +0,355 (6/6) |
  | Statique-R0 (R0 = 200) | +0,535 | +0,063 | +0,140 | +0,117 | +0,692 | **−0,191** (1/6) |

- `[OBS]` **Par période,** moyennes par trade (ATR, 5 bps) :

  | Variante | 2015-2019 | 2020-2025 |
  |---|---|---|
  | RE-1 gelée | +0,064 | +0,357 |
  | Contrôle | −0,005 | +0,355 |
  | WFO-R0 | +0,205 | +0,355 |
  | Statique-R0 | +0,301 | −0,191 |
  | Statique-conjointe | +0,337 | −0,077 |

- `[OBS]` **Lecture dès 2016 :** WFO-R0 +0,272 contre RE-1 gelée +0,267 ; écart +0,004 [−0,114 ; +0,134], Calmar
  0,64 contre 0,76. Le gain sur 2015-2025 (+0,074, non significatif) vient pour l'essentiel de 2015.

### 4.2 Les autres branches

- `[OBS]` **H (BTC) :** le choix varie de 12 à 50 barres d'un semestre à l'autre (12, 12, 50, 32, 32, 18, 46, 44, 18…),
  avec 4 replis sur RE-1 sur 22. Sur les mêmes entrées que le Contrôle, l'horizon choisi ne change rien : −0,008 ATR
  [−0,121 ; +0,116]. La perte de WFO-H (−0,174 contre Statique-H) vient donc du calendrier : changer H change les
  trades pris en course séquentielle (I-M16, K9).
- `[OBS]` **Statiques de BTC :** l'IS 2013-2014 n'a aucune configuration admissible à Calmar > 0 sur les axes H et
  frontière (R0 = 100) ; Statique-H et Statique-frontière y sont donc des replis sur RE-1 et valent le Contrôle.
- `[OBS]` **Frontière :** 0,85 dans 21 semestres sur 22 sur BTC. Quand tout l'axe est positif, le centre de la zone
  tombe sur 0,85. La branche est inerte ; WFO-frontière = Contrôle à ±0,001 ATR près.
- `[OBS]` **Conjointe :** R0 change souvent d'un semestre à l'autre (de 10 à 500) ; H va de 30 à 44 sur BTC et de 32 à 56 sur
  l'or, au-dessus de 26.
- `[OBS]` **Replis sur RE-1** (aucune configuration admissible à Calmar > 0 dans l'IS) : nombreux sur l'or (H 9, R0 11,
  frontière 14 sur 29 semestres). Sur BTC : 4 pour H et 6 pour la frontière, tous sur les premiers semestres, dont les
  IS (2013 à mi-2017) perdaient à R0 = 100.
- `[OBS]` **Or :** toutes les variantes perdent, de −0,045 (RE-1 gelée) à −0,196 ATR (WFO-R0). Le brut reste de +0,09 à
  +0,24 ATR pour 0,29 ATR de frais. WFO-R0 est significativement pire que le Contrôle (−0,150 [−0,294 ; −0,021]).
- `[OBS]` **SOL et AVAX :** sur 4 à 5 semestres, les écarts tiennent dans des IC de ±0,4 à ±0,7 ATR. Sur SOL, R0 et la
  frontière restent aux valeurs de RE-1 : six séries sur dix sont identiques au Contrôle.
- `[OBS]` **Sensibilités :** la panne de 2015 ne change rien (écarts ≤ 0,002 ATR).

## 5. Lecture de rentabilité

- **Brut et net :** sur BTC 2015-2025, RE-1 gelée fait +0,34 ATR brut et +0,218 net à 5 bps (IC > 0), mais seulement
  +0,093 [−0,094 ; +0,277] à 10 bps. WFO-R0 fait +0,42 brut, +0,291 net à 5 bps et +0,165 [−0,043 ; +0,373] à 10 bps. Sur
  l'or, 4 bps coûtent 0,29 ATR, autant que le brut.
- **Rendement et risque :** à 0,25 %/ATR, RE-1 gelée fait +159 % en 11 ans (MDD −28,4 %, Calmar 0,32) et WFO-R0 +214 %
  (MDD −15,8 %, Calmar 0,69). À 1x, les MDD vont de −41 à −73 % sur BTC.
- **Queues :** partout, médiane de −0,2 à −1,4 ATR. Les trades du décile supérieur valent +6 à +11 ATR en moyenne,
  soit +0,6 à +1,1 ATR par trade de la série, plus que l'espérance totale. Le profil de RE-1 ne change pas : quelques
  grands gagnants portent tout.
- **Plausibilité :** sur BTC, 2020-2025 a servi à construire RE-1. Le seul hors échantillon propre, 2015-2019, donne
  +0,064 ATR à RE-1 gelée et +0,205 à WFO-R0, sur 5 années dont deux portent l'écart (2015, 2018).

## 6. Hypothèses et pistes

- `[HYP]` **Sur BTC, les réglages valent pour une époque.** Les paramètres tirés de 2013-2014 (R0 = 200, H = 36)
  gagnent sur 2015-2019 et perdent sur 2020-2025 ; ceux de RE-1, tirés de 2020-2025, font l'inverse (D02.0). Le
  recalibrage semestriel sur 24 mois ne suit pas ce basculement de façon fiable : WFO-R0 a basculé vers 100 en
  2017-2018, mais a manqué 2019 (R0 = 200 : +0,692 ; WFO : −0,074).
- `[HYP]` **H se recalibre mal :** l'effet de sortie est nul sur entrées figées ; le recalibrage ne fait que déplacer le
  calendrier des trades, au détriment de BTC.
- `[HYP]` **En trois dimensions, la règle de la zone et de son centre ramène le choix vers le centre de la grille.** Les
  zones conjointes retenues sont très grandes : sur BTC, 107 à 559 cases sur 700 (médiane 280). L'axe H compte 28 pas
  contre 5 pour R0 et la frontière, si bien que le centre de ces zones tombe vers H = 30-44, autour du centre de la
  grille (H ≈ 33). C'est un effet de la géométrie de la grille, pas une mesure du marché.
- `[HYP]` **Coût :** à 10 bps, plus rien n'est significatif sur BTC ; la rente de RE-1 suppose un coût d'exécution de
  l'ordre de 5 bps.
- `[PISTE]` **Hold-out (phase 7) :** RE-1 inchangée, telle qu'elle est figée, sous réserve que le hold-out n'est pas
  vierge.
- `[PISTE]` **R0 seul, IS plus long ou ancré :** à cadrer si le porteur le souhaite. Le seul signal du WFO porte sur
  R0, mais il tient à deux années.

## 7. Décision (proposée au porteur)

- **Verdict du protocole :** aucune variante ne surpasse RE-1 gelée ; aucun WFO n'est retenu face à son Statique.
  Avec ce protocole, la valeur ajoutée du walk-forward n'est pas démontrée, ni par actif, ni conjointement. RE-1 reste
  inchangée.
- La suite est à trancher par le porteur.
