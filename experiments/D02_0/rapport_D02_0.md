# EXP-D02.0 — Rétro-test de RE-1 figée : BTC/USD 2013-2019 et CFD or 2009-2019

- **Date :** 2026-10-01. **Étape :** D, préalable de D02 (aucune optimisation).
- **Nature : descriptive.** RE-1 est strictement gelée : moteur v2.1 par défaut, seuils BTC 2020-2025 (médiane de
  `leg_atr` 2,8233, P75 de `nis_z_100` 1,2245), H = 26, F2b sans stop, F3 SL-B, cooldown. Aucune modification de RE-1
  sur la base de ces résultats (consigne du porteur).
- **Données, validées par le porteur avant le calcul** (`audit_donnees_D02_0.md`) :
  - BTC/USD Bitstamp, 30 min natives, 2013-01-01 → 2019-12-31, retéléchargé par notre script ; identique au bit près à
    la série du dépôt sur 2020-2025 (105 216 barres) ;
  - CFD or XAU/USD HistData, 2009-03-15 → 2019-12-31, même chaîne que D01 ; identique à la série de D01 sur 2020-2025 ;
    horloge vérifiée sur 2009-2018 par l'ouverture du dimanche, la dernière barre du vendredi et le pic des annonces de
    08:30 (la pause de 17:00 New York y est en partie cotée) ;
  - aucune barre de 2020 ni de 2026 lue.
- **Code :** `experiments/D02_0/run_D02_0.py`, qui réutilise la chaîne de D01 (`strategy.run_re1`, `metrics`,
  `diagnostics`) ; données : `donnees_D02_0.py`, `src/marketdata/bitstamp.py`.

## 0. Cadrage (validé par le porteur)

- **QUESTION :** RE-1 figée garde-t-elle une espérance nette sur des périodes qu'elle n'a jamais vues : BTC 2013-2019 et
  l'or de mars 2009 à 2019 ?
- **PERTINENCE AKF :** les seuils et la géométrie R2 viennent de BTC 2020-2025. Des régimes plus anciens testent leur
  stabilité dans le temps, sans aucune adaptation. C'est la référence figée contre laquelle le gain du walk-forward de
  D02 sera mesuré.
- **CE QUE ÇA MESURE :** les 8 métriques nettes (BTC 5 bps et 10 bps, or 4 bps) à 0,25 %/ATR et à 1x, l'espérance en
  ATR et en bps avec IC par grappes mensuelles, les années, Long/Short, F2b/F3, l'écart des populations aux seuils gelés,
  les frais en ATR par année ; pour BTC, la panne de 2015, le marché étroit de 2013 et une lecture hors 2013.
- **CE QUE ÇA NE PERMET PAS DE CONCLURE :** rien sur 2026 (scellé) ; coûts actuels appliqués à des années où les vrais
  coûts étaient plus élevés (convention du porteur) ; aucun critère de réussite ni comparaison statistique avec
  2020-2025 ; aucune modification de RE-1 ; structure de marché différente (BTC avant 2017, courtier HistData avant 2019).

## 1. Décisions du porteur et contrôles

- **Panne de Bitstamp (5-9 janvier 2015) :** données brutes intactes ; période non négociable dans le backtest
  principal. Les 215 barres plates sans transaction (2015-01-05 09:30 → 2015-01-09 20:30 UTC) sont retirées de la série
  vue par RE-1, comme une fermeture de marché, après vérification qu'elles forment exactement la suite repérée par
  l'audit. Sensibilité : la même chaîne sur la série brute.
- **Coûts actuels** sur les années anciennes : BTC 5 bps en lecture principale et 10 bps ; or 4 bps.
- **Contrôles bloquants passés :** RE-1 redonne les 1 080 trades de C02bis sur BTC 2020-2025 (40 métriques, écart
  relatif ≤ 4,5·10⁻⁶) ; empreintes des CSV égales à celles de l'audit validé.
- **Écart au cadrage, sans effet :** j'avais écrit qu'un signal dont la sortie tomberait après le 31/12/2019 serait
  écarté ; le moteur de C02bis clôt en fait ce trade à la dernière barre (convention de fin 2025). Aucun trade concerné
  ici (0 sur BTC comme sur l'or).

## 2. Résultats nets

| Lecture (coût) | PnL net : 0,25 %/ATR ; 1x ; bps cumulés (1x) | PF (1x) | WR | Espérance ATR [IC] ; bps [IC] | MDD : 0,25 %/ATR ; 1x | Trades (/mois) | Durée médiane | Part des frais (1x) ; brut ATR ; frais ATR |
|---|---|---|---|---|---|---|---|---|
| **BTC 2013-2019 (5)** | −20 % ; −63 % ; −3 298 | 0,97 | 42,3 % | **−0,045 [−0,244 ; +0,157]** ; −2,4 [−19,5 ; +15,4] | −48,5 % ; −91,6 % | 1 357 (16,2) | 26 barres ; 13 h | 195 % ; +0,056 ; 0,101 |
| BTC 2013-2019 (10) | −42 % ; −81 % ; −10 083 | 0,92 | 41,0 % | −0,146 [−0,346 ; +0,057] ; −7,4 [−24,5 ; +10,4] | −56,7 % ; −94,2 % | 1 357 (16,2) | 13 h | 389 % |
| BTC 2014-2019 (5) | −22 % ; −43 % ; −2 190 | 0,98 | 42,5 % | −0,065 [−0,278 ; +0,152] ; −1,9 [−16,2 ; +15,2] | −47,4 % ; −84,5 % | 1 180 (16,4) | 13 h | 159 % |
| BTC brut, panne gardée (5) | −20 % ; −64 % ; −3 437 | 0,97 | 42,2 % | −0,047 [−0,247 ; +0,156] ; −2,5 | −48,8 % ; −91,7 % | 1 357 (16,2) | 13 h | 203 % |
| **Or 2009-2019 (4)** | −3 % ; −5 % ; −272 | 0,99 | 41,7 % | **+0,011 [−0,246 ; +0,258]** ; −0,2 [−3,8 ; +3,1] | −29,1 % ; −29,3 % | 1 253 (9,7) | 26 barres ; 13 h | 106 % ; +0,304 ; 0,293 |
| *BTC 2020-2025 (5), réf.* | +138 % ; +204 % ; +13 320 | 1,20 | 44,3 % | +0,369 [+0,098 ; +0,645] ; +12,3 [+0,2 ; +24,4] | −13,5 % ; −43,9 % | 1 080 (15,0) | 13 h | 29 % ; +0,504 ; 0,136 |
| *Or 2020-2025 (4), réf.* | +1 % ; +5 % ; +697 | 1,04 | 42,5 % | −0,019 [−0,362 ; +0,349] ; +1,1 | −13,6 % ; −13,3 % | 651 (9,0) | 13 h | 79 % ; +0,239 ; 0,257 |

**Années (espérance nette en ATR, coût principal) :**

| | 2009 | 2010 | 2011 | 2012 | 2013 | 2014 | 2015 | 2016 | 2017 | 2018 | 2019 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| BTC (5) | — | — | — | — | +0,090 | **−0,740** | −0,272 | −0,002 | +0,469 | +0,062 | +0,109 |
| BTC brut ATR | — | — | — | — | +0,16 | −0,67 | −0,16 | +0,15 | +0,55 | +0,16 | +0,22 |
| Or (4) | +0,087 | +0,146 | +0,456 | +0,560 | +0,454 | +0,145 | +0,456 | **−0,828** | −0,394 | −0,323 | −0,805 |
| Or brut ATR ; frais ATR | +0,30 ; 0,22 | +0,41 ; 0,26 | +0,69 ; 0,24 | +0,85 ; 0,29 | +0,70 ; 0,25 | +0,45 ; 0,30 | +0,74 ; 0,29 | −0,57 ; 0,26 | −0,04 ; 0,36 | +0,05 ; 0,37 | −0,43 ; 0,37 |

Références 2020-2025 : BTC +0,514, +0,024, +0,305, +0,504, +0,334, +0,550 (6/6) ; or +0,056, −0,155, +0,476, −0,210,
−0,129, −0,251 (2/6).

## 3. Lecture

### BTC 2013-2019

- `[OBS]` **L'espérance de 2020-2025 ne se retrouve pas.** −0,045 ATR [−0,244 ; +0,157] à 5 bps, contre +0,369
  [+0,098 ; +0,645] ; −0,146 à 10 bps. MDD de −48,5 % à 0,25 %/ATR (−13,5 % en 2020-2025).
- `[OBS]` **C'est le brut qui manque, pas le coût.** Brut +0,056 ATR contre +0,504 ; les frais ne coûtent que 0,10 ATR
  (0,14 en 2020-2025), parce que l'ATR de 30 min y est plus large (P50 63,5 bps contre 49,7).
- `[OBS]` **Deux années portent l'écart :** 2014 (−0,740 ; brut −0,67, Long −0,84 et Short −0,61) et 2015 (−0,272). 2017
  (+0,469) est la meilleure année ; 4 années positives sur 7, contre 6 sur 6 en 2020-2025.
- `[OBS]` **La composante de timing disparaît.** Long +0,128 / Short −0,249 ; timing (moyenne des deux sens) −0,061
  [−0,259 ; +0,141], contre +0,362 [+0,089 ; +0,638] en 2020-2025.
- `[OBS]` **F2b, cœur de RE-1 en 2020-2025, perd :** F2b −0,224 [−0,492 ; +0,036] (765 trades), F3 +0,185 [−0,100 ;
  +0,467] (592) ; en 2020-2025, +0,459 et +0,267. Le stop de F3 ne change rien de significatif (−0,128 [−0,368 ; +0,095]).
- `[OBS]` **Les populations restent proches des seuils gelés :** même cadence de signaux (101 par mois) ; médiane locale
  de `leg_atr` 2,59 (57,6 % des signaux sous le seuil BTC, contre 50 %) ; P75 local de `nis_z_100` 1,135 (contre
  1,225). L'échec ne vient pas d'un transfert de seuils grossièrement faux.
- `[OBS]` **Bandes de `nis_z_100` (trades isolés, descriptif) :** la bande > P90, écartée par le veto de RE-1, gagne
  +0,60 ATR [+0,20 ; +1,03] sur 256 trades, alors qu'elle perdait en 2020-2025 (−0,40 [−0,93 ; +0,17]) ; la bande ≤ P70
  passe de +0,17 à −0,06. Six bandes, trades isolés : fait à consigner, rien à en tirer pour l'exécution.
- `[OBS]` **Panne de janvier 2015 :** sans effet. Aucun trade créé sur les barres plates ni à cheval sur la panne dans la
  série brute ; un seul trade diffère (le 2015-01-11 : +0,58 ATR dans la lecture principale, −1,93 dans la série brute) ;
  espérance −0,045 contre −0,047.
- `[OBS]` **Marché étroit de 2013 :** un seul trade touche une suite d'au moins 4 h sans transaction. La lecture hors 2013
  (−0,065 [−0,278 ; +0,152]) n'est pas meilleure : 2013 n'explique pas l'écart.

### Or 2009-2019

- `[OBS]` **Même structure qu'en 2020-2025 :** brut +0,304 ATR (en log +0,305 [+0,053 ; +0,551], IC > 0), absorbé par
  0,293 ATR de frais à 4 bps ; net +0,011 [−0,246 ; +0,258]. Le brut se réalise en séance (+0,292), pas dans les écarts
  d'ouverture (+0,013).
- `[OBS]` **Deux régimes nets :** 2009-2015, 7 années positives sur 7 (brut +0,30 à +0,85 ATR, ATR de 13,5 à 19 bps) ;
  2016-2019, 4 négatives sur 4 (brut −0,57 à +0,05 ; frais montés à 0,36-0,37 ATR quand l'ATR tombe vers 11 bps). Depuis
  2016, seules 2020 et 2022 sont positives (2 années sur 10).
- `[OBS]` **Les sous-familles changent de signe d'une période à l'autre :** F2b +0,183 / F3 −0,200 ici, contre −0,304 /
  +0,313 en 2020-2025.
- `[OBS]` À 0,25 %/ATR, 93 % des trades sont plafonnés à 1x (ATR < 25 bps) : les deux conventions de capital coïncident.

### Hypothèses

- `[HYP]` **Sur BTC, l'avantage de RE-1 n'est pas stationnaire dans le temps.** Deux explications, que ce test ne sépare
  pas : (a) RE-1 a été construite sur 2020-2025 au fil d'une quinzaine d'expériences (A01 → C05), et une part de son
  espérance en échantillon peut tenir à ces choix ; (b) un changement de régime du marché (BTC 2013-2019 : marché spot
  étroit, ère Mt. Gox, avant les dérivés et les ETF). 2026, scellé, reste le seul hors échantillon de BTC, mais il
  n'est pas vierge : d'anciens projets l'ont vu (`passation.md` §2.1 ; correction du 2026-10-01).
- `[HYP]` **Sur l'or, le brut de +0,25 à +0,30 ATR persiste sur 17 ans** ; la rentabilité nette dépend du rapport brut /
  frais en ATR (K11) et du régime (2009-2015 contre 2016-2025).
- `[HYP]` **Pour D02 :** la référence figée dépend de la période. Ces périodes antérieures entrent dans le jeu de données
  du walk-forward, qui devra montrer un gain sur elles aussi. L'inversion de la bande > P90 désigne les seuils de
  population comme l'endroit où la non-stationnarité se manifeste (options (b) et (c) du point 2 du §13.2 de
  `passation.md`).

## 4. Décision

- **TERMINÉ (descriptif).** BTC 2013-2019 : pas d'espérance nette (IC contient 0, estimation négative) ; or 2009-2019 :
  net nul, brut positif. RE-1 inchangée.
- **Univers de D02 (porteur, 2026-10-01) :** AVAX/USD (Coinbase, depuis le 2021-09-30) ajouté ; LINK et LTC non
  ajoutés ; ETH et XRP strictement réservés au hold-out.

---

# Annexes chiffrées (générées par `run_D02_0.py`)

## A. Contrôles bloquants et conventions

- RE-1 sur BTC 2020-2025 par la chaîne de D01 : 1 080 trades identiques à C02bis ; 40 métriques comparées, écart relatif maximal 4,5·10⁻⁶ ; ancre P6.5d reproduite.
- Seuils gelés : médiane de leg_atr 2,8233, P75 de nis_z_100 1,2245 (atlas BTC 2020-2025), jamais recalculés.
- Empreintes des deux CSV égales à celles de l'audit validé ; aucune barre de 2020 ni de 2026 lue.
- Capital : 0,25 % par ATR14(t) (poids min(1 ; 25 bps / ATR14 en bps), levier ≤ 1x) et notionnel 1x. IC 95 % par bootstrap de grappes de mois d'entrée, 2 000 tirages. Annualisation sur la durée propre de chaque période.

| Lecture | Barres lues (UTC) | Barres | Années | Trades / candidats | Trades clos à la dernière barre |
|---|---|---|---|---|---|
| BTC 2013-2019 | 2013-01-01 00:00 → 2019-12-31 23:30 | 122 473 ; 215 barres de panne retirées | 7,00 | 1 357 / 1 835 | 0 |
| XAU 2009-2019 | 2009-03-15 22:00 → 2019-12-31 21:30 | 129 314 | 10,80 | 1 253 / 1 589 | 0 |
| BTC brut | 2013-01-01 00:00 → 2019-12-31 23:30 | 122 688 | 7,00 | 1 357 / 1 834 | 0 |

## B. Tableau standard (8 métriques nettes)

| Actif, frais | PnL net : 0,25 %/ATR ; 1x ; bps cumulés (1x) | PF : 1x ; pondéré | WR | Espérance : bps [IC] ; ATR [IC] | MDD valorisé : 0,25 %/ATR ; 1x | Trades (par mois) ; stoppés | Durée médiane : barres ; calendaire | Part des frais : 1x ; pondérée |
|---|---|---|---|---|---|---|---|---|
| BTC 2013-2019 5 bps | −20 % ; −63 % ; −3298 | 0,97 ; 0,96 | 42,3 % | −2,4 [−19,5 ; +15,4] ; −0,045 [−0,244 ; +0,157] | −48,5 % ; −91,6 % | 1 357 (16,2) ; 23 % | 26 ; 13,0 h | 195 % ; 190 % |
| BTC 2013-2019 10 bps | −42 % ; −81 % ; −10083 | 0,92 ; 0,89 | 41,0 % | −7,4 [−24,5 ; +10,4] ; −0,146 [−0,346 ; +0,057] | −56,7 % ; −94,2 % | 1 357 (16,2) ; 23 % | 26 ; 13,0 h | 389 % ; 379 % |
| BTC 2014-2019 5 bps | −22 % ; −43 % ; −2190 | 0,98 ; 0,95 | 42,5 % | −1,9 [−16,2 ; +15,2] ; −0,065 [−0,278 ; +0,152] | −47,4 % ; −84,5 % | 1 180 (16,4) ; 22 % | 26 ; 13,0 h | 159 % ; 282 % |
| BTC 2014-2019 10 bps | −42 % ; −68 % ; −8090 | 0,92 ; 0,88 | 41,4 % | −6,9 [−21,2 ; +10,2] ; −0,171 [−0,383 ; +0,048] | −55,1 % ; −88,5 % | 1 180 (16,4) ; 22 % | 26 ; 13,0 h | 318 % ; 565 % |
| XAU 2009-2019 4 bps | −3 % ; −5 % ; −272 | 0,99 ; 1,00 | 41,7 % | −0,2 [−3,8 ; +3,1] ; +0,011 [−0,246 ; +0,258] | −29,1 % ; −29,3 % | 1 253 (9,7) ; 26 % | 26 ; 13,0 h | 106 % ; 102 % |
| BTC brut 5 bps | −20 % ; −64 % ; −3437 | 0,97 ; 0,96 | 42,2 % | −2,5 [−19,6 ; +15,1] ; −0,047 [−0,247 ; +0,156] | −48,8 % ; −91,7 % | 1 357 (16,2) ; 23 % | 26 ; 13,0 h | 203 % ; 197 % |
| BTC brut 10 bps | −43 % ; −82 % ; −10222 | 0,92 ; 0,89 | 41,0 % | −7,5 [−24,6 ; +10,1] ; −0,148 [−0,350 ; +0,056] | −57,0 % ; −94,3 % | 1 357 (16,2) ; 23 % | 26 ; 13,0 h | 405 % ; 393 % |
| BTC 2020-2025 (réf.) 5 bps | +138 % ; +204 % ; +13320 | 1,20 ; 1,28 | 44,3 % | +12,3 [+0,2 ; +24,4] ; +0,369 [+0,098 ; +0,645] | −13,5 % ; −43,9 % | 1 080 (15,0) ; 24 % | 26 ; 13,0 h | 29 % ; 26 % |
| BTC 2020-2025 (réf.) 10 bps | +72 % ; +77 % ; +7920 | 1,11 ; 1,17 | 42,8 % | +7,3 [−4,8 ; +19,4] ; +0,233 [−0,041 ; +0,511] | −15,9 % ; −48,0 % | 1 080 (15,0) ; 24 % | 26 ; 13,0 h | 58 % ; 52 % |
| XAU 2020-2025 (réf.) 4 bps | +1 % ; +5 % ; +697 | 1,04 ; 1,01 | 42,5 % | +1,1 [−4,9 ; +7,5] ; −0,019 [−0,362 ; +0,349] | −13,6 % ; −13,3 % | 651 (9,0) ; 26 % | 26 ; 13,0 h | 79 % ; 92 % |

## C. Risque, sens, timing et sous-familles

| Actif, frais | Années | 0,25 %/ATR : CAGR ; Calmar | 1x : CAGR ; Calmar | Exposition moyenne ; trades plafonnés à 1x | Long / Short (ATR) | Timing ATR [IC] | Timing bps [IC] | F2b : n ; ATR | F3 : n ; ATR |
|---|---|---|---|---|---|---|---|---|---|
| BTC 2013-2019 5 bps | 7,00 | −3,1 % ; −0,06 | −13,4 % ; −0,15 | 49 % ; 7 % | +0,128 / −0,249 | −0,061 [−0,259 ; +0,141] | −3,9 [−21,1 ; +14,2] | 765 ; −0,224 | 592 ; +0,185 |
| BTC 2013-2019 10 bps | 7,00 | −7,6 % ; −0,13 | −21,4 % ; −0,23 | 49 % ; 7 % | +0,027 / −0,350 | −0,161 [−0,359 ; +0,044] | −8,9 [−26,1 ; +9,2] | 765 ; −0,324 | 592 ; +0,084 |
| BTC 2014-2019 5 bps | 6,00 | −4,0 % ; −0,08 | −8,9 % ; −0,10 | 51 % ; 8 % | +0,043 / −0,192 | −0,074 [−0,285 ; +0,146] | −2,7 [−17,0 ; +14,1] | 677 ; −0,203 | 503 ; +0,120 |
| BTC 2014-2019 10 bps | 6,00 | −8,7 % ; −0,16 | −17,4 % ; −0,20 | 51 % ; 8 % | −0,063 / −0,296 | −0,179 [−0,389 ; +0,037] | −7,7 [−22,0 ; +9,1] | 677 ; −0,308 | 503 ; +0,014 |
| XAU 2009-2019 4 bps | 10,80 | −0,3 % ; −0,01 | −0,5 % ; −0,02 | 99 % ; 93 % | −0,009 / +0,031 | +0,011 [−0,247 ; +0,254] | −0,2 [−3,8 ; +3,2] | 691 ; +0,183 | 562 ; −0,200 |
| BTC brut 5 bps | 7,00 | −3,2 % ; −0,07 | −13,6 % ; −0,15 | 49 % ; 7 % | +0,124 / −0,249 | −0,062 [−0,261 ; +0,140] | −4,0 [−21,3 ; +14,1] | 764 ; −0,225 | 593 ; +0,182 |
| BTC brut 10 bps | 7,00 | −7,7 % ; −0,13 | −21,6 % ; −0,23 | 49 % ; 7 % | +0,023 / −0,350 | −0,163 [−0,364 ; +0,044] | −9,0 [−26,3 ; +9,1] | 764 ; −0,325 | 593 ; +0,080 |
| BTC 2020-2025 (réf.) 5 bps | 6,00 | +15,6 % ; 1,16 | +20,3 % ; 0,46 | 60 % ; 16 % | +0,457 / +0,266 | +0,362 [+0,089 ; +0,638] | +12,3 [+0,2 ; +24,5] | 573 ; +0,459 | 507 ; +0,267 |
| BTC 2020-2025 (réf.) 10 bps | 6,00 | +9,5 % ; 0,60 | +10,0 % ; 0,21 | 60 % ; 16 % | +0,320 / +0,131 | +0,226 [−0,050 ; +0,507] | +7,3 [−4,8 ; +19,5] | 573 ; +0,326 | 507 ; +0,127 |
| XAU 2020-2025 (réf.) 4 bps | 6,00 | +0,1 % ; 0,01 | +0,9 % ; 0,07 | 98 % ; 89 % | +0,329 / −0,431 | −0,051 [−0,399 ; +0,306] | +0,5 [−5,2 ; +6,9] | 350 ; −0,304 | 301 ; +0,313 |

## D. Populations face aux seuils gelés (descriptif, tous les signaux de l'atlas)

| Période | Signaux (par mois) | leg_atr : médiane locale ; part < 2,823 | nis_z_100 : P75 local ; part > 1,225 : tous ; dans R2 | R2 avant nis → univers RE-1 (F2b ; F3) | ATR14 bps P50 [P10 ; P90] |
|---|---|---|---|---|---|
| BTC 2013-2019 | 8 481 (101,0) | 2,588 ; 57,6 % | 1,135 ; 23,5 % ; 24,5 % | 2 431 → 1 835 (1 009 ; 826) | 63,5 [30,2 ; 152,1] |
| BTC 2020-2025 (réf.) | 7 296 (101,3) | 2,823 ; 50,0 % | 1,225 ; 25,0 % ; 22,5 % | 1 874 → 1 452 (741 ; 711) | 49,7 [23,3 ; 99,4] |
| XAU 2009-2019 | 8 735 (67,4) | 2,888 ; 48,0 % | 1,146 ; 23,8 % ; 23,2 % | 2 069 → 1 589 (831 ; 758) | 15,8 [10,0 ; 26,8] |
| XAU 2020-2025 (réf.) | 4 649 (64,6) | 2,901 ; 47,7 % | 1,217 ; 24,9 % ; 24,7 % | 1 128 → 849 (447 ; 402) | 17,2 [11,8 ; 28,5] |

## E. Années (année d'entrée, frais de lecture principale)

| Lecture | Année | Trades | Espérance nette ATR | Espérance nette bps | Brut ATR ; frais ATR | ATR14 bps (P50) | PnL 0,25 %/ATR | PnL 1x | Long / Short ATR |
|---|---|---|---|---|---|---|---|---|---|
| BTC 2013-2019 5 bps | 2013 | 177 | +0,090 | −6,3 | +0,161 ; 0,071 | 76,2 | +2,7 % | −36,2 % | +0,67 / −0,65 |
| BTC 2013-2019 5 bps | 2014 | 193 | −0,740 | −55,5 | −0,667 ; 0,073 | 71,6 | −30,4 % | −67,4 % | −0,84 / −0,61 |
| BTC 2013-2019 5 bps | 2015 | 191 | −0,272 | −15,4 | −0,163 ; 0,109 | 47,6 | −13,3 % | −29,1 % | −0,24 / −0,32 |
| BTC 2013-2019 5 bps | 2016 | 242 | −0,002 | −5,7 | +0,148 ; 0,149 | 34,3 | −2,3 % | −15,3 % | +0,20 / −0,25 |
| BTC 2013-2019 5 bps | 2017 | 184 | +0,469 | +49,1 | +0,546 ; 0,077 | 73,8 | +21,9 % | +125,8 % | +1,04 / −0,28 |
| BTC 2013-2019 5 bps | 2018 | 183 | +0,062 | −0,4 | +0,160 ; 0,098 | 68,2 | +3,3 % | −7,5 % | +0,08 / +0,05 |
| BTC 2013-2019 5 bps | 2019 | 187 | +0,109 | +20,8 | +0,222 ; 0,113 | 47,3 | +5,2 % | +40,1 % | +0,03 / +0,18 |
| XAU 2009-2019 4 bps | 2009 | 90 | +0,087 | +2,4 | +0,302 ; 0,215 | 19,2 | +2,1 % | +1,9 % | +0,42 / −0,37 |
| XAU 2009-2019 4 bps | 2010 | 113 | +0,146 | +0,3 | +0,407 ; 0,262 | 15,9 | +0,5 % | +0,0 % | +0,56 / −0,26 |
| XAU 2009-2019 4 bps | 2011 | 116 | +0,456 | +4,6 | +0,694 ; 0,238 | 17,9 | +7,4 % | +5,1 % | +0,58 / +0,33 |
| XAU 2009-2019 4 bps | 2012 | 120 | +0,560 | +6,7 | +0,852 ; 0,292 | 14,0 | +7,9 % | +8,0 % | +0,33 / +0,79 |
| XAU 2009-2019 4 bps | 2013 | 123 | +0,454 | +4,2 | +0,704 ; 0,250 | 17,5 | +4,2 % | +4,9 % | −0,73 / +1,16 |
| XAU 2009-2019 4 bps | 2014 | 133 | +0,145 | +1,2 | +0,447 ; 0,302 | 13,5 | +1,1 % | +1,4 % | −0,08 / +0,42 |
| XAU 2009-2019 4 bps | 2015 | 122 | +0,456 | +5,4 | +0,741 ; 0,285 | 14,4 | +6,6 % | +6,6 % | +0,33 / +0,57 |
| XAU 2009-2019 4 bps | 2016 | 101 | −0,828 | −10,9 | −0,570 ; 0,258 | 16,2 | −10,5 % | −10,6 % | −0,80 / −0,86 |
| XAU 2009-2019 4 bps | 2017 | 98 | −0,394 | −5,1 | −0,038 ; 0,356 | 11,2 | −5,0 % | −5,0 % | +0,42 / −1,28 |
| XAU 2009-2019 4 bps | 2018 | 108 | −0,323 | −3,1 | +0,051 ; 0,374 | 10,9 | −3,4 % | −3,4 % | −0,01 / −0,64 |
| XAU 2009-2019 4 bps | 2019 | 129 | −0,805 | −9,8 | −0,434 ; 0,371 | 10,5 | −11,9 % | −12,0 % | −1,07 / −0,53 |
| BTC brut 5 bps | 2013 | 177 | +0,090 | −6,3 | +0,161 ; 0,071 | 76,2 | +2,7 % | −36,2 % | +0,67 / −0,65 |
| BTC brut 5 bps | 2014 | 193 | −0,740 | −55,5 | −0,667 ; 0,073 | 71,6 | −30,4 % | −67,4 % | −0,84 / −0,61 |
| BTC brut 5 bps | 2015 | 191 | −0,285 | −16,1 | −0,176 ; 0,109 | 47,6 | −13,9 % | −30,1 % | −0,26 / −0,32 |
| BTC brut 5 bps | 2016 | 242 | −0,002 | −5,7 | +0,148 ; 0,149 | 34,3 | −2,3 % | −15,3 % | +0,20 / −0,25 |
| BTC brut 5 bps | 2017 | 184 | +0,469 | +49,1 | +0,546 ; 0,077 | 73,8 | +21,9 % | +125,8 % | +1,04 / −0,28 |
| BTC brut 5 bps | 2018 | 183 | +0,062 | −0,4 | +0,160 ; 0,098 | 68,2 | +3,3 % | −7,5 % | +0,08 / +0,05 |
| BTC brut 5 bps | 2019 | 187 | +0,109 | +20,8 | +0,222 ; 0,113 | 47,3 | +5,2 % | +40,1 % | +0,03 / +0,18 |

## F. Sens × sous-famille (espérance nette par trade, ATR [IC] ; contribution à l'espérance totale)

| Actif | Famille | Sens | n | Espérance ATR [IC] | Espérance bps | Contribution ATR |
|---|---|---|---|---|---|---|
| BTC 2013-2019 5 bps | F2b | Long | 361 | −0,107 [−0,450 ; +0,260] | −5,0 | −0,028 |
| BTC 2013-2019 5 bps | F2b | Short | 404 | −0,328 [−0,727 ; +0,061] | −19,4 | −0,098 |
| BTC 2013-2019 5 bps | F2b | tous | 765 | −0,224 [−0,492 ; +0,036] | −12,6 | −0,126 |
| BTC 2013-2019 5 bps | F3 | Long | 373 | +0,354 [−0,037 ; +0,737] | +32,2 | +0,097 |
| BTC 2013-2019 5 bps | F3 | Short | 219 | −0,102 [−0,477 ; +0,291] | −25,9 | −0,017 |
| BTC 2013-2019 5 bps | F3 | tous | 592 | +0,185 [−0,100 ; +0,467] | +10,7 | +0,081 |
| BTC 2013-2019 5 bps | tous | Long | 734 | +0,128 [−0,158 ; +0,412] | +13,9 | +0,069 |
| BTC 2013-2019 5 bps | tous | Short | 623 | −0,249 [−0,550 ; +0,034] | −21,6 | −0,114 |
| BTC 2013-2019 5 bps | tous | tous | 1 357 | −0,045 [−0,244 ; +0,157] | −2,4 | −0,045 |
| XAU 2009-2019 4 bps | F2b | Long | 337 | +0,228 [−0,390 ; +0,788] | +2,8 | +0,061 |
| XAU 2009-2019 4 bps | F2b | Short | 354 | +0,139 [−0,444 ; +0,712] | +0,5 | +0,039 |
| XAU 2009-2019 4 bps | F2b | tous | 691 | +0,183 [−0,211 ; +0,587] | +1,6 | +0,101 |
| XAU 2009-2019 4 bps | F3 | Long | 290 | −0,284 [−0,646 ; +0,095] | −4,0 | −0,066 |
| XAU 2009-2019 4 bps | F3 | Short | 272 | −0,109 [−0,543 ; +0,341] | −0,8 | −0,024 |
| XAU 2009-2019 4 bps | F3 | tous | 562 | −0,200 [−0,487 ; +0,092] | −2,4 | −0,090 |
| XAU 2009-2019 4 bps | tous | Long | 627 | −0,009 [−0,376 ; +0,329] | −0,4 | −0,004 |
| XAU 2009-2019 4 bps | tous | Short | 626 | +0,031 [−0,364 ; +0,430] | −0,1 | +0,016 |
| XAU 2009-2019 4 bps | tous | tous | 1 253 | +0,011 [−0,246 ; +0,258] | −0,2 | +0,011 |

## G. Stops de F3 (SL-B à l'extremum) : fréquence et contribution

| Actif | Stoppés / F3 | Espérance ATR : stoppés ; F3 non stoppés | Contribution des stoppés (ATR) | Effet apparié du stop sur F3 (ATR [IC]) | MDD 0,25 %/ATR : RE-1 contre sans stop | Calmar : RE-1 contre sans stop | MDD 1x : RE-1 contre sans stop |
|---|---|---|---|---|---|---|---|
| BTC 2013-2019 5 bps | 309 / 592 (52 %) | −1,87 ; +2,43 | −0,426 | −0,128 [−0,368 ; +0,095] | −48,5 % contre −44,5 % | −0,06 contre −0,01 | −91,6 % contre −86,8 % |
| XAU 2009-2019 4 bps | 324 / 562 (58 %) | −2,31 ; +2,68 | −0,598 | +0,003 [−0,258 ; +0,288] | −29,1 % contre −29,7 % | −0,01 contre −0,04 | −29,3 % contre −29,2 % |

## H. Distribution des trades (espérance nette en ATR, frais de lecture principale)

| Actif | P10 ; P25 ; P50 ; P75 ; P90 | Moyenne ; winsorisée P1/P99 | Apport du décile supérieur par trade (part du total) | Durée calendaire (h) : médiane ; P90 ; part > 24 h |
|---|---|---|---|---|
| BTC 2013-2019 5 bps | −3,11 ; −1,94 ; −0,49 ; +1,31 ; +3,83 | −0,045 ; −0,034 | +0,817 (espérance totale ≈ 0 ou négative) | 13,0 ; 13,0 ; 0 % |
| XAU 2009-2019 4 bps | −3,65 ; −2,43 ; −0,88 ; +1,92 ; +5,21 | +0,011 ; +0,016 | +0,934 (espérance totale ≈ 0 ou négative) | 13,0 ; 14,0 ; 7 % |

## I. Régimes de volatilité (terciles de l'ATR14(t) en bps des trades de l'actif)

| Actif | Tercile | ATR14 (bps) | n | Espérance ATR [IC] | Espérance bps [IC] | WR | Stoppés |
|---|---|---|---|---|---|---|---|
| BTC 2013-2019 5 bps | T1 calme | 7,6 – 44,1 | 452 | −0,133 [−0,630 ; +0,333] | −6,1 [−22,6 ; +9,2] | 40,3 % | 25 % |
| BTC 2013-2019 5 bps | T2 | 44,1 – 73,9 | 452 | −0,002 [−0,335 ; +0,346] | −0,6 [−20,1 ; +19,2] | 41,6 % | 22 % |
| BTC 2013-2019 5 bps | T3 agité | 74,1 – 1639,7 | 453 | −0,001 [−0,357 ; +0,322] | −0,5 [−49,1 ; +45,2] | 45,0 % | 21 % |
| XAU 2009-2019 4 bps | T1 calme | 5,2 – 12,1 | 418 | +0,079 [−0,494 ; +0,673] | +1,4 [−4,5 ; +7,6] | 39,2 % | 31 % |
| XAU 2009-2019 4 bps | T2 | 12,1 – 16,8 | 417 | −0,063 [−0,437 ; +0,281] | −1,5 [−6,8 ; +3,4] | 41,7 % | 24 % |
| XAU 2009-2019 4 bps | T3 agité | 16,8 – 48,5 | 418 | +0,018 [−0,345 ; +0,341] | −0,6 [−7,8 ; +6,3] | 44,3 % | 22 % |

## J. nis_z_100 : bandes de l'univers R2 avant exclusion (trades isolés, bornes aux quantiles de l'atlas BTC)

Descriptif : chaque signal R2 joué seul avec l'enveloppe de RE-1, sans sélection séquentielle. Rien n'en est tiré pour l'exécution.

| Actif | ≤ P70 (BTC) | P70–P75 (BTC) | P75–P80 (BTC) | P80–P85 (BTC) | P85–P90 (BTC) | > P90 (BTC) |
|---|---|---|---|---|---|---|
| BTC 2013-2019 5 bps | 1 650 : −0,06 [−0,24 ; +0,11] | 185 : +0,22 [−0,32 ; +0,82] | 142 : +0,19 [−0,28 ; +0,68] | 93 : +0,03 [−0,51 ; +0,60] | 105 : +0,10 [−0,44 ; +0,64] | 256 : +0,60 [+0,20 ; +1,03] |
| XAU 2009-2019 4 bps | 1 470 : −0,02 [−0,26 ; +0,21] | 119 : −0,30 [−0,75 ; +0,22] | 115 : −0,55 [−1,13 ; +0,11] | 113 : +0,04 [−0,69 ; +0,85] | 79 : −0,56 [−1,23 ; +0,24] | 173 : +0,22 [−0,36 ; +0,84] |

## L. Panne de Bitstamp de janvier 2015 : lecture principale (période non négociable) contre série brute

**5 bps** : 1 357 trades contre 1 357 sur la série brute ; 1 356 communs (même entrée, même sens) ; divergence du 2015-01-11 01:30 au 2015-01-11 11:30 ; somme des espérances nettes −61,34 ATR contre −63,84.

**10 bps** : 1 357 trades contre 1 357 sur la série brute ; 1 356 communs (même entrée, même sens) ; divergence du 2015-01-11 01:30 au 2015-01-11 11:30 ; somme des espérances nettes −198,07 ATR contre −200,61.

- trades de la série brute nés d'un signal sur les barres plates : aucun
- trades de la série brute ouverts avant la panne et la traversant : aucun
- trades de la lecture principale traversant le trou de la panne : aucun
- trades propres à la lecture principale : entrée 2015-01-11 01:30, sortie 2015-01-11 14:30, +0,58 ATR
- trades propres à la série brute : entrée 2015-01-11 11:30, sortie 2015-01-11 15:30, −1,93 ATR

## M. Marché étroit de 2013 : trades touchant une suite d'au moins 4 h sans transaction

7 suites hors panne ; 1 trades touchés, espérance nette −0,465 ATR contre −0,045 pour les autres (5 bps).

## N. Or : écarts d'ouverture traversés (définitions de D01)

Écarts traversés par trade (P50) 0 ; trades concernés 31 % ; brut (log) +0,305 [+0,053 ; +0,551] ATR, dont écarts +0,013 [−0,013 ; +0,036], dont séance +0,292 [+0,043 ; +0,533] ; stops en gap 0 / 324.

Figure : `figures/D02_0.png`.
