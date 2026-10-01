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
  étroit, ère Mt. Gox, avant les dérivés et les ETF). 2026, scellé, reste le seul hors échantillon vierge de BTC.
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
