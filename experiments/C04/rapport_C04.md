# EXP-C04 — Filtre de contexte macro : tendance et alignement

- **Date :** 2026-09-29.
- **Étape :** C Enveloppe. Dernier facteur prévu : le filtre de tendance macro. Test OFAT sur RE-1.
- **Actif et période :** BTC/USD Bitstamp 30 min, 2020-01 → 2025-12. 2026, ETH et XRP ne sont pas lus.
- **Frais :** 5 et 10 bps, présentés séparément. Capital à 0,25 % par ATR14(t) ; 1x en référence.
- **Contrôle :** RE-1 pur :
  - R2 hors `nis_z_100` Q4 ;
  - F2b sans stop, F3 SL-B à l'extremum ;
  - H = 26, cooldown, pyramiding 0.

  H = 24 et 28 servent au contrôle de plateau.
- **Code, commité à part (eb8949f) :** `src/context/trend.py` et 5 tests.
- **Analyse :** `experiments/C04/run_C04.py`.

## 0. Cadrage

- **QUESTION :** un signal de RE-1 (F2b ou F3) a-t-il une espérance asymétrique selon qu'il est aligné ou opposé à la tendance de fond ?
  - Un veto des signaux contre-tendance élimine-t-il un bruit toxique, ou retire-t-il les grands retournements en V de la queue droite ?
- **PERTINENCE POUR LE FILTRE AKF :**
  - Le déclencheur est un retournement de la vitesse du Kalman. Un filtre de tendance plus lente pourrait séparer les vrais retournements des contre-mouvements.
  - Avant de figer la stratégie cœur pour C05 (sensibilité) et l'Étape D, il faut savoir si ce contexte ajoute de l'information.
- **CE QUE LE PROTOCOLE MESURE RÉELLEMENT :**
  - l'espérance des trades de RE-1 alignés et contre-tendance, et leur écart, sur les mêmes tirages de mois ;
  - la part de la queue droite retirée ;
  - les 8 métriques en deux lectures :
    - séquentielle : le signal vétoé n'existe pas ;
    - figée : RE-1 moins les trades vétoés ;
  - la décomposition vétoés, perdus, ajoutés ;
  - le risque de chemin, l'équivalent en taille, le plateau et les années ;
  - l'asymétrie F2b / F3.
- **CE QU'IL NE PERMET PAS DE CONCLURE :**
  - une validation hors échantillon ;
  - l'effet d'une tendance à d'autres échelles (EMA quotidienne, hebdomadaire) ou d'un filtre de régime non directionnel (volatilité, pente), non testés ;
  - un réglage des paramètres de tendance, exclu par principe (standards 200, 50, filtre v2.1 sur 4 h).

## Règle de décision (fixée avant le calcul)

Traduction opérationnelle de la règle du porteur :

- **Rejet (RE-1 reste pur)** si l'une des conditions tient :
  - **R1 :** les trades contre-tendance contiennent une part du décile supérieur de RE-1 au moins égale à leur part des trades. Le filtre ne vise pas le bruit.
  - **R2 :** l'espérance en ATR de la stratégie filtrée est inférieure à celle de RE-1 (lecture séquentielle, 5 bps).
  - **R3 :** à MDD égal, la stratégie filtrée ne fait pas mieux qu'un RE-1 réduit en taille (I-M11).
- **Adoption** si toutes les conditions tiennent :
  - **A1 :** les trades contre-tendance ont une espérance négative à 5 bps, et l'écart aligné − contre-tendance a un IC 95 % qui exclut 0.
  - **A2 :** à 10 bps, espérance et Calmar sont supérieurs à ceux de RE-1.
  - **A3 :** le Calmar est supérieur à H24, H26 et H28, aux deux niveaux de frais. Il est meilleur sur les chemins réordonnés (plage P2,5-P97,5 excluant 0) et meilleur que RE-1 réduit à MDD égal.
  - **A4 :** l'IC de l'espérance reste > 0 à 5 bps, ce qui garantit que la fréquence n'est pas tuée.

## 1. [CODE] Implémentation et contrôles

**Tendances, lues à la clôture de la barre du signal :**

| Variante | Définition |
|---|---|
| V1 | close > EMA(close, 200), barres 30 min |
| V2 | close > EMA(close, 50) |
| V3 | signe de x1 du filtre v2.1 (`run_kalman`, module de parité, aucune réécriture) sur des bougies 4 h entièrement closes |

- Pour V3, une bougie n'est lue qu'une fois close : jonction `merge_asof` arrière, comme en D32.
- V3 est valide après 300 bougies (convention D32) : 27 signaux de janvier-février 2020 ne sont pas filtrés.

**Choix de V3 à la conception, avant tout résultat :** R0 = 1 000 sur 30 min a été écarté. Ses régimes de x1 durent 19 barres en médiane, contre 11 pour le filtre de base : ce n'est pas un horizon macro. Le filtre v2.1 sur 4 h donne des régimes de 88 barres (44 h).

**Veto :** un Long n'est autorisé que si la tendance est haussière, un Short que si elle est baissière.

**Deux lectures :**
- **Séquentielle (principale).** Le signal vétoé est ignoré et la position reste libre.
- **Figée.** Un signal vétoé impose le cooldown qu'il aurait eu : c'est l'effet pur du veto sur les trades de RE-1, sans effet de chaîne.

**Tests et contrôles :**
- 5 tests nouveaux : récurrence directe de l'EMA, bougies 1 h identiques à l'agrégation certifiée D32, bougie 4 h lue seulement close, causalité par troncature, warm-up et veto. Suite complète : 200 réussis.
- Contrôles bloquants passés :
  - ancre P6.5d ;
  - RE-1 identique à C02bis trade par trade (H24, 26, 28), avec 6 lignes de métriques identiques ;
  - décomposition séquentielle refermée à 10⁻⁹ près.

**Calcul :** 42 lignes en 45 s.

## 2. [OBS] Mesures

### 2.1 Les trades contre-tendance de RE-1 ne sont pas toxiques

Le cœur de la question. H26, 5 bps, espérance nette par trade en ATR [IC 95 %] :

| Tendance | Trades contre-tendance | Alignés | Contre-tendance | Écart aligné − contre |
|---|---|---|---|---|
| V1, EMA 200 | 478 (44 %) | +0,352 [−0,006 ; +0,744] | +0,389 [+0,045 ; +0,767] | −0,037 [−0,563 ; +0,474] |
| V2, EMA 50 | 376 (35 %) | +0,353 [+0,011 ; +0,723] | +0,398 [−0,039 ; +0,858] | −0,045 [−0,650 ; +0,584] |
| V3, Kalman 4 h | 512 (47 %) | +0,317 [−0,011 ; +0,675] | +0,426 [+0,071 ; +0,776] | −0,109 [−0,537 ; +0,318] |

- **Aucune asymétrie en faveur de l'alignement.** Les trades contre-tendance valent autant, voire plus, que les alignés, pour les trois définitions. Aucun écart n'est significatif.
- **Ils portent les grands retournements :**

  | Tendance | Décile supérieur de RE-1 contre-tendance | Gagnants ≥ +3 ATR | 20 meilleurs trades |
  |---|---|---|---|
  | V1 | 46/108 (42,6 %) | 47 % | 5 |
  | V2 | 36/108 (33,3 %) | 35 % | 4 |
  | V3 | 52/108 (48,1 %) | 53 % | 9 |

  Leur distribution recouvre celle de RE-1 jusque dans la queue.
- **Les retournements en V sont du côté contre-tendance.** Les Long contre la tendance Kalman 4 h font +0,640 ATR [+0,171 ; +1,083], contre +0,292 pour les Long alignés.

### 2.2 Asymétrie F2b / F3

- **F2b contre-tendance est le meilleur groupe :**
  - V1 : +0,523 contre +0,405 pour F2b aligné ;
  - V3 : +0,583 [+0,099 ; +1,070] contre +0,361.
- **Pour F3, contre-tendance et aligné se valent** (+0,23 à +0,30 dans les deux cas).
- **Le filtre prive donc surtout F2b de ses meilleurs trades.** En séquentiel, F2b tombe de +0,459 à +0,241 (V1) et +0,306 (V3) ; F3 de +0,267 à +0,191 et +0,151.

### 2.3 Huit métriques à H26 (lecture séquentielle, 5 bps)

| Configuration | PnL : 0,25 %/ATR ; 1x ; bps | PF | WR | Espérance : bps [IC] ; ATR [IC] | MDD | Trades (/mois) | Durée méd. | Part des frais | Calmar |
|---|---|---|---|---|---|---|---|---|---|
| RE-1 | +138 % ; +204 % ; +13 320 | 1,20 | 44,3 % | +12,3 [+0,2 ; +24,4] ; +0,369 [+0,098 ; +0,645] | −13,5 % | 1 080 (15,0) | 26 | 29 % | 1,16 |
| V1, EMA 200 | +46 % ; +45 % ; +5 196 | 1,12 | 40,9 % | +7,5 [−8,2 ; +23,7] ; +0,216 [−0,099 ; +0,548] | −13,3 % | 696 (9,7) | 26 | 40 % | 0,49 |
| V2, EMA 50 | +55 % ; +16 % ; +3 094 | 1,06 | 41,3 % | +4,0 [−11,6 ; +20,7] ; +0,260 [−0,036 ; +0,590] | −17,1 % | 774 (10,8) | 26 | 56 % | 0,44 |
| V3, Kalman 4 h | +38 % ; +59 % ; +6 311 | 1,14 | 42,5 % | +9,5 [−5,0 ; +24,8] ; +0,237 [−0,045 ; +0,533] | −13,6 % | 663 (9,2) | 26 | 34 % | 0,41 |

**Lecture figée (effet pur du veto), 5 bps :**

| Configuration | Espérance ATR | PnL | MDD | Trades par mois | Calmar |
|---|---|---|---|---|---|
| V1 | +0,352 | +58 % | −10,8 % | 8,4 | 0,74 |
| V2 | +0,353 | +70 % | −14,9 % | 9,8 | 0,62 |
| V3 | +0,317 | +42 % | −11,6 % | 7,9 | 0,52 |

**À 10 bps (séquentiel) :**

| Configuration | Espérance ATR | PnL | MDD | Calmar |
|---|---|---|---|---|
| RE-1 | +0,233 [−0,041 ; +0,511] | +72 % | −15,9 % | 0,60 |
| V1 | +0,078 | +18 % | −16,8 % | 0,17 |
| V2 | +0,119 | +22 % | −17,6 % | 0,19 |
| V3 | +0,095 | +13 % | −16,0 % | 0,13 |

### 2.4 Lecture séquentielle : le veto retire de bons trades et en ajoute de mauvais

| Tendance | Vétoés | Perdus par chaîne | Ajoutés |
|---|---|---|---|
| V1 | 478 à +0,389 | 14 | 108 à **−0,484** |
| V2 | 376 à +0,398 | 13 | 83 à **−0,376** |
| V3 | 512 à +0,426 | 9 | 104 à −0,050 |

5 bps, espérance en ATR.

- **Les ajoutés sont les signaux alignés qui tombent pendant la fenêtre d'un trade vétoé.** RE-1 les ignorait, car sa position était occupée, et ils perdent.
- **C'est le même phénomène que le cooldown de C02bis :** les signaux qui suivent dans la même structure sont mauvais.
- La lecture figée, qui les écarte, fait donc moins mal que la séquentielle.

### 2.5 Risque, taille, plateau, années

- **Risque et taille (H26, 5 bps) :**
  - Le MDD ne baisse vraiment qu'en lecture figée : −10,8 % pour V1, −11,6 % pour V3, avec moitié moins de trades.
  - Sur les chemins réordonnés, le Calmar n'est meilleur que dans 5 à 8 % des cas en séquentiel, 6 à 15 % en figé.
  - À MDD égal, un RE-1 simplement réduit en taille fait mieux :
    - de 8,9 à 10,8 points par an en séquentiel ;
    - de 4,2 à 7,5 points en figé.
- **Plateau :** chaque variante fait moins bien que RE-1 à H24, H26 et H28, aux deux niveaux de frais (annexe G).
- **Années :** V1 et V3 font passer 2022 en négatif (−0,14 et −0,27 ATR, contre +0,30 pour RE-1). En année baissière, les Long contre-tendance vétoés étaient des rebonds gagnants.

## 3. [HYP] Lectures

- **L'information du déclencheur est indépendante de la tendance lente.** Le retournement de x1 dans R2 hors Q4 anticipe déjà le changement de régime. Un filtre plus lent n'arrive qu'après, et interdit précisément les trades où le Kalman voit le tournant avant la tendance : les V de la queue droite.
- **Un signal consommé doit bloquer sa fenêtre, même s'il n'est pas pris.** Les signaux qui arrivent pendant la fenêtre d'un signal précédent perdent. Le cooldown de RE-1 et la lecture figée les écartent tous les deux.

## 4. [DECISION] Proposée : filtre macro rejeté, RE-1 reste pur

| Critère | V1, EMA 200 | V2, EMA 50 | V3, Kalman 4 h |
|---|---|---|---|
| R1 : queue droite retirée au moins en proportion | non (42,6 % du décile pour 44,3 % des trades), mais 47 % des gagnants ≥ +3 ATR | non (33,3 % pour 34,8 %) | **oui** (48,1 % pour 47,4 % ; 9 des 20 meilleurs trades) |
| R2 : espérance dégradée | **oui** (+0,369 → +0,216) | **oui** (→ +0,260) | **oui** (→ +0,237) |
| R3 : pas mieux qu'une réduction de taille | **oui** (−8,9 pt/an) | **oui** (−10,8) | **oui** (−10,2) |
| A1 : bruit contre-tendance évident | non (contre-tendance +0,389) | non (+0,398) | non (+0,426) |
| A2 : meilleur à 10 bps | non | non | non |
| A3 : Calmar robuste | non (0,49 contre 1,16) | non | non |
| A4 : IC > 0 à 5 bps | non | non | non |

- [x] **REJETÉ pour les trois définitions.**
  - Le filtre élimine des trades aussi bons que les autres, dont une part des grands retournements, et fait entrer en séquentiel des signaux perdants.
  - Il dégrade l'espérance, le PnL et le Calmar à 5 et 10 bps, aux trois horizons.
  - **RE-1 reste pur.**
- **Conséquence pour la suite :**
  - L'Étape C a testé ses quatre facteurs : sortie à horizon, stop par sous-famille, break-even, filtre macro. RE-1 est la stratégie cœur.
  - Le porteur annonce C05 (sensibilité), puis l'Étape D (portabilité multi-actifs).

---

# Annexes chiffrées (générées par `run_C04.py`)

## A. Contrôles bloquants

| Contrôle | Résultat |
|---|---|
| Ancre P6.5d | 6 037 et 6 589 trades identiques |
| RE-1 = RE-1 de C02bis | trades identiques à H24, 26 et 28 ; 6 lignes de métriques identiques à resultats_C02bis.csv (écart relatif max 4,5·10⁻⁶) |
| Décomposition séquentielle | filtrée = RE-1 − vétoés − perdus par chaîne + ajoutés, refermée à 10⁻⁹ près pour chaque variante, chaque horizon et chaque niveau de frais |
| Causalité des tendances | EMA récursive et Kalman 4 h lus à la clôture de la barre du signal ; bougie 4 h lue seulement une fois close ; tests de troncature (tests/test_context.py) |
| Période | 2020-01 → 2025-12 ; aucune barre de 2026 lue ; ETH et XRP non lus |

## B. Définitions de tendance

Durées des régimes en barres de 30 min, de la barre du premier signal à fin 2025 (tendance définie). Signaux : les 1 452 candidats de RE-1 (R2 hors Q4).

| Tendance | Régime médian | Régime moyen | Part haussière | Signaux sans tendance (pas de veto) | Signaux vétoés |
|---|---|---|---|---|---|
| V1 — EMA 200 | 4 | 27,5 | 52,9 % | 0 | 644 (44,4 %) : 307 Long, 337 Short |
| V2 — EMA 50 | 3 | 11,7 | 52,6 % | 0 | 505 (34,8 %) : 239 Long, 266 Short |
| V3 — Kalman 4 h | 88 | 90,0 | 50,9 % | 27 | 687 (47,3 %) : 364 Long, 323 Short |

## C. Trades de RE-1 contre la tendance (H = 26, cooldown)

Contre-tendance : trades de RE-1 dont le signal serait vétoé. Espérance nette par trade en ATR [IC 95 % par grappes mensuelles] ; écart aligné − contre-tendance sur les mêmes tirages.

**5 bps**

| Tendance | Groupe | Trades : alignés ; contre | Alignés | Contre-tendance | Écart aligné − contre |
|---|---|---|---|---|---|
| V1 — EMA 200 | tous | 602 ; 478 | +0,352 [−0,006 ; +0,744] | +0,389 [+0,045 ; +0,767] | −0,037 [−0,563 ; +0,474] |
| V1 — EMA 200 | F2b | 313 ; 260 | +0,405 [−0,053 ; +0,880] | +0,523 [−0,015 ; +1,086] | −0,118 [−0,858 ; +0,609] |
| V1 — EMA 200 | F3 | 289 ; 218 | +0,295 [−0,187 ; +0,805] | +0,230 [−0,201 ; +0,689] | +0,065 [−0,593 ; +0,704] |
| V1 — EMA 200 | Long | 351 ; 229 | +0,498 [+0,048 ; +0,953] | +0,393 [−0,069 ; +0,870] | +0,105 [−0,473 ; +0,687] |
| V1 — EMA 200 | Short | 251 ; 249 | +0,148 [−0,309 ; +0,668] | +0,386 [−0,215 ; +1,043] | −0,238 [−1,127 ; +0,614] |
| V2 — EMA 50 | tous | 704 ; 376 | +0,353 [+0,011 ; +0,723] | +0,398 [−0,039 ; +0,858] | −0,045 [−0,650 ; +0,584] |
| V2 — EMA 50 | F2b | 348 ; 225 | +0,444 [−0,007 ; +0,905] | +0,482 [−0,162 ; +1,152] | −0,038 [−0,870 ; +0,802] |
| V2 — EMA 50 | F3 | 356 ; 151 | +0,264 [−0,169 ; +0,746] | +0,273 [−0,257 ; +0,837] | −0,009 [−0,755 ; +0,751] |
| V2 — EMA 50 | Long | 401 ; 179 | +0,402 [−0,048 ; +0,854] | +0,580 [+0,055 ; +1,178] | −0,178 [−0,901 ; +0,525] |
| V2 — EMA 50 | Short | 303 ; 197 | +0,288 [−0,118 ; +0,764] | +0,233 [−0,523 ; +1,021] | +0,055 [−0,922 ; +0,999] |
| V3 — Kalman 4 h | tous | 568 ; 512 | +0,317 [−0,011 ; +0,675] | +0,426 [+0,071 ; +0,776] | −0,109 [−0,537 ; +0,318] |
| V3 — Kalman 4 h | F2b | 320 ; 253 | +0,361 [−0,129 ; +0,896] | +0,583 [+0,099 ; +1,070] | −0,222 [−0,936 ; +0,520] |
| V3 — Kalman 4 h | F3 | 248 ; 259 | +0,260 [−0,159 ; +0,717] | +0,273 [−0,189 ; +0,760] | −0,013 [−0,625 ; +0,579] |
| V3 — Kalman 4 h | Long | 306 ; 274 | +0,292 [−0,142 ; +0,722] | +0,640 [+0,171 ; +1,083] | −0,348 [−0,907 ; +0,204] |
| V3 — Kalman 4 h | Short | 262 ; 238 | +0,345 [−0,108 ; +0,840] | +0,179 [−0,386 ; +0,718] | +0,166 [−0,576 ; +0,948] |

**10 bps**

| Tendance | Groupe | Trades : alignés ; contre | Alignés | Contre-tendance | Écart aligné − contre |
|---|---|---|---|---|---|
| V1 — EMA 200 | tous | 602 ; 478 | +0,217 [−0,140 ; +0,613] | +0,253 [−0,094 ; +0,635] | −0,036 [−0,557 ; +0,475] |
| V1 — EMA 200 | F2b | 313 ; 260 | +0,277 [−0,186 ; +0,752] | +0,385 [−0,154 ; +0,951] | −0,108 [−0,842 ; +0,618] |
| V1 — EMA 200 | F3 | 289 ; 218 | +0,152 [−0,339 ; +0,669] | +0,095 [−0,337 ; +0,567] | +0,056 [−0,602 ; +0,697] |
| V1 — EMA 200 | Long | 351 ; 229 | +0,365 [−0,085 ; +0,814] | +0,252 [−0,216 ; +0,729] | +0,113 [−0,468 ; +0,702] |
| V1 — EMA 200 | Short | 251 ; 249 | +0,010 [−0,458 ; +0,534] | +0,254 [−0,348 ; +0,917] | −0,244 [−1,132 ; +0,605] |
| V2 — EMA 50 | tous | 704 ; 376 | +0,214 [−0,127 ; +0,588] | +0,268 [−0,176 ; +0,724] | −0,055 [−0,655 ; +0,572] |
| V2 — EMA 50 | F2b | 348 ; 225 | +0,310 [−0,138 ; +0,767] | +0,352 [−0,295 ; +1,012] | −0,042 [−0,873 ; +0,801] |
| V2 — EMA 50 | F3 | 356 ; 151 | +0,120 [−0,317 ; +0,608] | +0,144 [−0,388 ; +0,709] | −0,024 [−0,770 ; +0,731] |
| V2 — EMA 50 | Long | 401 ; 179 | +0,263 [−0,185 ; +0,721] | +0,448 [−0,076 ; +1,036] | −0,184 [−0,904 ; +0,522] |
| V2 — EMA 50 | Short | 303 ; 197 | +0,148 [−0,262 ; +0,623] | +0,105 [−0,655 ; +0,891] | +0,043 [−0,929 ; +0,982] |
| V3 — Kalman 4 h | tous | 568 ; 512 | +0,177 [−0,148 ; +0,534] | +0,295 [−0,065 ; +0,648] | −0,118 [−0,547 ; +0,314] |
| V3 — Kalman 4 h | F2b | 320 ; 253 | +0,226 [−0,264 ; +0,758] | +0,453 [−0,033 ; +0,945] | −0,227 [−0,941 ; +0,520] |
| V3 — Kalman 4 h | F3 | 248 ; 259 | +0,114 [−0,317 ; +0,577] | +0,140 [−0,326 ; +0,629] | −0,026 [−0,651 ; +0,570] |
| V3 — Kalman 4 h | Long | 306 ; 274 | +0,152 [−0,287 ; +0,582] | +0,508 [+0,034 ; +0,949] | −0,356 [−0,912 ; +0,203] |
| V3 — Kalman 4 h | Short | 262 ; 238 | +0,206 [−0,246 ; +0,716] | +0,049 [−0,525 ; +0,592] | +0,156 [−0,590 ; +0,939] |

**Queue droite** — gros gagnants de RE-1 (5 bps) parmi les trades contre-tendance ; distribution P10 / médiane / P90 du résultat net (ATR).

| Tendance | Trades contre-tendance (part) | Décile supérieur de RE-1 contre-tendance | Gagnants ≥ +3 ATR contre-tendance | 20 meilleurs trades contre-tendance | Contre : P10 / méd. / P90 | Alignés : P10 / méd. / P90 |
|---|---|---|---|---|---|---|
| V1 — EMA 200 | 478 (44,3 %) | 46/108 (42,6 %) ; 40,8 % de leur contribution | 99/209 (47,4 %) | 5/20 | −2,80 / −0,28 / +5,40 | −2,92 / −0,59 / +5,59 |
| V2 — EMA 50 | 376 (34,8 %) | 36/108 (33,3 %) ; 32,2 % de leur contribution | 74/209 (35,4 %) | 4/20 | −2,82 / −0,19 / +5,42 | −2,89 / −0,57 / +5,58 |
| V3 — Kalman 4 h | 512 (47,4 %) | 52/108 (48,1 %) ; 45,5 % de leur contribution | 110/209 (52,6 %) | 9/20 | −2,81 / −0,47 / +5,56 | −3,03 / −0,41 / +5,42 |

## D. Huit métriques à H = 26

Lecture séquentielle : un signal vétoé n'existe pas, la position reste libre (lecture principale). Lecture figée : les trades de RE-1 moins les trades vétoés (un signal vétoé impose le même cooldown que s'il avait été pris).

**5 bps — 8 métriques**

| Configuration | PnL : 0,25 %/ATR ; 1x ; bps (1x) | PF : 1x ; pondéré | WR | Espérance : bps [IC] ; ATR [IC] | MDD valorisé : 0,25 %/ATR ; 1x | Trades (/mois) ; stoppés | Durée méd. | Part des frais ; brut/trade |
|---|---|---|---|---|---|---|---|---|
| RE-1 (contrôle) | +138 % ; +204 % ; +13320 | 1,20 ; 1,28 | 44,3 % | +12,3 [+0,2 ; +24,4] ; +0,369 [+0,098 ; +0,645] | −13,5 % ; −44 % | 1 080 (15,0) ; 24 % | 26 | 29 % ; +17,3 |
| V1 — EMA 200 | +46 % ; +45 % ; +5196 | 1,12 ; 1,19 | 40,9 % | +7,5 [−8,2 ; +23,7] ; +0,216 [−0,099 ; +0,548] | −13,3 % ; −37 % | 696 (9,7) ; 26 % | 26 | 40 % ; +12,5 |
| V1 — EMA 200 (figée) | +58 % ; +49 % ; +5177 | 1,13 ; 1,26 | 42,5 % | +8,6 [−8,5 ; +26,4] ; +0,352 [−0,006 ; +0,744] | −10,8 % ; −34 % | 602 (8,4) ; 25 % | 26 | 37 % ; +13,6 |
| V2 — EMA 50 | +55 % ; +16 % ; +3094 | 1,06 ; 1,20 | 41,3 % | +4,0 [−11,6 ; +20,7] ; +0,260 [−0,036 ; +0,590] | −17,1 % ; −50 % | 774 (10,8) ; 26 % | 26 | 56 % ; +9,0 |
| V2 — EMA 50 (figée) | +70 % ; +48 % ; +5402 | 1,12 ; 1,26 | 42,3 % | +7,7 [−8,9 ; +25,6] ; +0,353 [+0,011 ; +0,723] | −14,9 % ; −44 % | 704 (9,8) ; 26 % | 26 | 39 % ; +12,7 |
| V3 — Kalman 4 h | +38 % ; +59 % ; +6311 | 1,14 ; 1,17 | 42,5 % | +9,5 [−5,0 ; +24,8] ; +0,237 [−0,045 ; +0,533] | −13,6 % ; −29 % | 663 (9,2) ; 23 % | 26 | 34 % ; +14,5 |
| V3 — Kalman 4 h (figée) | +42 % ; +44 % ; +4927 | 1,13 ; 1,22 | 43,3 % | +8,7 [−6,7 ; +23,9] ; +0,317 [−0,011 ; +0,675] | −11,6 % ; −31 % | 568 (7,9) ; 22 % | 26 | 37 % ; +13,7 |

**5 bps — sens, sous-familles, régularité**

| Configuration | Long / Short (ATR) | F2b : n ; esp. ATR | F3 : n ; esp. ATR | Années > 0 : ATR ; PnL | PnL annualisé ; Calmar |
|---|---|---|---|---|---|
| RE-1 (contrôle) | +0,46 / +0,27 | 573 ; +0,459 | 507 ; +0,267 | 6/6 ; 6/6 | +15,6 % ; 1,16 |
| V1 — EMA 200 | +0,33 / +0,07 | 353 ; +0,241 | 343 ; +0,191 | 5/6 ; 5/6 | +6,5 % ; 0,49 |
| V1 — EMA 200 (figée) | +0,50 / +0,15 | 313 ; +0,405 | 289 ; +0,295 | 5/6 ; 5/6 | +8,0 % ; 0,74 |
| V2 — EMA 50 | +0,32 / +0,19 | 381 ; +0,349 | 393 ; +0,174 | 6/6 ; 5/6 | +7,6 % ; 0,44 |
| V2 — EMA 50 (figée) | +0,40 / +0,29 | 348 ; +0,444 | 356 ; +0,264 | 5/6 ; 5/6 | +9,3 % ; 0,62 |
| V3 — Kalman 4 h | +0,23 / +0,24 | 370 ; +0,306 | 293 ; +0,151 | 5/6 ; 5/6 | +5,6 % ; 0,41 |
| V3 — Kalman 4 h (figée) | +0,29 / +0,35 | 320 ; +0,361 | 248 ; +0,260 | 5/6 ; 5/6 | +6,0 % ; 0,52 |

**10 bps — 8 métriques**

| Configuration | PnL : 0,25 %/ATR ; 1x ; bps (1x) | PF : 1x ; pondéré | WR | Espérance : bps [IC] ; ATR [IC] | MDD valorisé : 0,25 %/ATR ; 1x | Trades (/mois) ; stoppés | Durée méd. | Part des frais ; brut/trade |
|---|---|---|---|---|---|---|---|---|
| RE-1 (contrôle) | +72 % ; +77 % ; +7920 | 1,11 ; 1,17 | 42,8 % | +7,3 [−4,8 ; +19,4] ; +0,233 [−0,041 ; +0,511] | −15,9 % ; −48 % | 1 080 (15,0) ; 24 % | 26 | 58 % ; +17,3 |
| V1 — EMA 200 | +18 % ; +2 % ; +1716 | 1,04 ; 1,09 | 39,4 % | +2,5 [−13,2 ; +18,7] ; +0,078 [−0,239 ; +0,414] | −16,8 % ; −44 % | 696 (9,7) ; 26 % | 26 | 80 % ; +12,5 |
| V1 — EMA 200 (figée) | +32 % ; +10 % ; +2167 | 1,05 ; 1,16 | 40,9 % | +3,6 [−13,5 ; +21,4] ; +0,217 [−0,140 ; +0,613] | −11,5 % ; −36 % | 602 (8,4) ; 25 % | 26 | 74 % ; +13,6 |
| V2 — EMA 50 | +22 % ; −21 % ; −776 | 0,99 ; 1,09 | 39,5 % | −1,0 [−16,6 ; +15,7] ; +0,119 [−0,181 ; +0,450] | −17,6 % ; −51 % | 774 (10,8) ; 26 % | 26 | 111 % ; +9,0 |
| V2 — EMA 50 (figée) | +38 % ; +4 % ; +1882 | 1,04 ; 1,16 | 40,8 % | +2,7 [−13,9 ; +20,6] ; +0,214 [−0,127 ; +0,588] | −15,5 % ; −45 % | 704 (9,8) ; 26 % | 26 | 79 % ; +12,7 |
| V3 — Kalman 4 h | +13 % ; +14 % ; +2996 | 1,07 ; 1,07 | 40,9 % | +4,5 [−10,0 ; +19,8] ; +0,095 [−0,190 ; +0,395] | −16,0 % ; −34 % | 663 (9,2) ; 23 % | 26 | 69 % ; +14,5 |
| V3 — Kalman 4 h (figée) | +20 % ; +8 % ; +2087 | 1,05 ; 1,11 | 42,1 % | +3,7 [−11,7 ; +18,9] ; +0,177 [−0,148 ; +0,534] | −13,4 % ; −32 % | 568 (7,9) ; 22 % | 26 | 73 % ; +13,7 |

**10 bps — sens, sous-familles, régularité**

| Configuration | Long / Short (ATR) | F2b : n ; esp. ATR | F3 : n ; esp. ATR | Années > 0 : ATR ; PnL | PnL annualisé ; Calmar |
|---|---|---|---|---|---|
| RE-1 (contrôle) | +0,32 / +0,13 | 573 ; +0,326 | 507 ; +0,127 | 5/6 ; 5/6 | +9,5 % ; 0,60 |
| V1 — EMA 200 | +0,19 / −0,08 | 353 ; +0,108 | 343 ; +0,047 | 5/6 ; 5/6 | +2,8 % ; 0,17 |
| V1 — EMA 200 (figée) | +0,36 / +0,01 | 313 ; +0,277 | 289 ; +0,152 | 5/6 ; 5/6 | +4,8 % ; 0,41 |
| V2 — EMA 50 | +0,17 / +0,05 | 381 ; +0,211 | 393 ; +0,030 | 5/6 ; 5/6 | +3,4 % ; 0,19 |
| V2 — EMA 50 (figée) | +0,26 / +0,15 | 348 ; +0,310 | 356 ; +0,120 | 5/6 ; 5/6 | +5,5 % ; 0,35 |
| V3 — Kalman 4 h | +0,09 / +0,10 | 370 ; +0,168 | 293 ; +0,003 | 5/6 ; 5/6 | +2,1 % ; 0,13 |
| V3 — Kalman 4 h (figée) | +0,15 / +0,21 | 320 ; +0,226 | 248 ; +0,114 | 5/6 ; 5/6 | +3,1 % ; 0,23 |

## E. Lecture séquentielle : décomposition contre RE-1 (H = 26)

Vétoés : trades de RE-1 retirés ; perdus : trades alignés de RE-1 absents de la variante (un trade ajouté occupe leur place) ; ajoutés : signaux alignés que RE-1 ignorait (position occupée par un trade vétoé). n ; espérance nette par trade (ATR).

| Tendance | Frais | Vétoés | Perdus par chaîne | Ajoutés | Trades ; espérance ATR : RE-1 → variante |
|---|---|---|---|---|---|
| V1 — EMA 200 | 5 bps | 478 ; +0,389 | 14 ; +0,649 | 108 ; −0,484 | 1 080 → 696 ; +0,369 → +0,216 |
| V1 — EMA 200 | 10 bps | 478 ; +0,253 | 14 ; +0,489 | 108 ; −0,645 | 1 080 → 696 ; +0,233 → +0,078 |
| V2 — EMA 50 | 5 bps | 376 ; +0,398 | 13 ; +1,215 | 83 ; −0,376 | 1 080 → 774 ; +0,369 → +0,260 |
| V2 — EMA 50 | 10 bps | 376 ; +0,268 | 13 ; +1,050 | 83 ; −0,537 | 1 080 → 774 ; +0,233 → +0,119 |
| V3 — Kalman 4 h | 5 bps | 512 ; +0,426 | 9 ; +1,931 | 104 ; −0,050 | 1 080 → 663 ; +0,369 → +0,237 |
| V3 — Kalman 4 h | 10 bps | 512 ; +0,295 | 9 ; +1,742 | 104 ; −0,208 | 1 080 → 663 ; +0,233 → +0,095 |

## F. Risque (H = 26) : chemin réel, chemins réordonnés, taille

MDD valorisé et Calmar du chemin réel (RE-1 → variante). Chemins : 2 000 tirages des mois d'entrée avec remise, mêmes mois pour RE-1 et la variante ; écart observé [P2,5 ; P97,5] ; part des chemins où la variante fait mieux (MDD aux sorties). Taille : écart de PnL annualisé entre la variante et RE-1 réduit au même MDD valorisé (risque par ATR de RE-1 réduit).

| Configuration | Frais | MDD : RE-1 → variante | Calmar : RE-1 → variante | Écart de MDD (points) ; chemins | Écart de Calmar ; chemins | À MDD égal, face à RE-1 réduit |
|---|---|---|---|---|---|---|
| V1 — EMA 200 | 5 bps | −13,5 % → −13,3 % | 1,16 → 0,49 | +0,3 [−11,4 ; +9,8] ; 52 % | −0,69 [−1,59 ; +0,18] ; 6 % | −8,9 pt (0,248 %) |
| V1 — EMA 200 | 10 bps | −15,9 % → −16,8 % | 0,60 → 0,17 | −0,8 [−13,7 ; +11,7] ; 50 % | −0,44 [−1,08 ; +0,16] ; 8 % | −7,1 pt (0,266 %) |
| V1 — EMA 200 (figée) | 5 bps | −13,5 % → −10,8 % | 1,16 → 0,74 | +2,2 [−8,3 ; +10,1] ; 65 % | −0,46 [−1,39 ; +0,32] ; 11 % | −4,2 pt (0,186 %) |
| V1 — EMA 200 (figée) | 10 bps | −15,9 % → −11,5 % | 0,60 → 0,41 | +4,1 [−9,1 ; +12,6] ; 68 % | −0,19 [−0,86 ; +0,29] ; 19 % | −1,8 pt (0,161 %) |
| V2 — EMA 50 | 5 bps | −13,5 % → −17,1 % | 1,16 → 0,44 | −3,7 [−13,2 ; +8,4] ; 44 % | −0,75 [−1,58 ; +0,22] ; 8 % | −10,8 pt (0,319 %) |
| V2 — EMA 50 | 10 bps | −15,9 % → −17,6 % | 0,60 → 0,19 | −1,9 [−15,3 ; +10,1] ; 41 % | −0,42 [−1,05 ; +0,16] ; 10 % | −6,8 pt (0,279 %) |
| V2 — EMA 50 (figée) | 5 bps | −13,5 % → −14,9 % | 1,16 → 0,62 | −1,9 [−10,3 ; +8,8] ; 55 % | −0,58 [−1,31 ; +0,38] ; 15 % | −7,5 pt (0,277 %) |
| V2 — EMA 50 (figée) | 10 bps | −15,9 % → −15,5 % | 0,60 → 0,35 | −0,1 [−11,1 ; +10,9] ; 57 % | −0,26 [−0,84 ; +0,34] ; 23 % | −3,8 pt (0,243 %) |
| V3 — Kalman 4 h | 5 bps | −13,5 % → −13,6 % | 1,16 → 0,41 | +0,1 [−9,5 ; +11,2] ; 64 % | −0,78 [−1,70 ; +0,09] ; 5 % | −10,2 pt (0,253 %) |
| V3 — Kalman 4 h | 10 bps | −15,9 % → −16,0 % | 0,60 → 0,13 | +0,2 [−11,7 ; +12,6] ; 62 % | −0,48 [−1,22 ; +0,09] ; 6 % | −7,5 pt (0,251 %) |
| V3 — Kalman 4 h (figée) | 5 bps | −13,5 % → −11,6 % | 1,16 → 0,52 | +1,7 [−8,8 ; +11,1] ; 68 % | −0,67 [−1,60 ; +0,14] ; 6 % | −7,3 pt (0,208 %) |
| V3 — Kalman 4 h (figée) | 10 bps | −15,9 % → −13,4 % | 0,60 → 0,23 | +2,8 [−8,5 ; +13,1] ; 71 % | −0,37 [−1,06 ; +0,16] ; 10 % | −5,2 pt (0,209 %) |

## G. Plateau d'horizon (lecture séquentielle)

Cellule : espérance ATR ; MDD ; Calmar.

| Configuration | 5 bps, H = 24 | 5 bps, H = 26 | 5 bps, H = 28 | 10 bps, H = 24 | 10 bps, H = 26 | 10 bps, H = 28 |
|---|---|---|---|---|---|---|
| RE-1 (contrôle) | +0,328 ; −14,2 % ; 0,94 | +0,369 ; −13,5 % ; 1,16 | +0,371 ; −16,2 % ; 0,92 | +0,194 ; −16,7 % ; 0,43 | +0,233 ; −15,9 % ; 0,60 | +0,235 ; −18,4 % ; 0,48 |
| V1 — EMA 200 | +0,181 ; −12,7 % ; 0,44 | +0,216 ; −13,3 % ; 0,49 | +0,214 ; −15,5 % ; 0,40 | +0,043 ; −18,6 % ; 0,10 | +0,078 ; −16,8 % ; 0,17 | +0,075 ; −18,8 % ; 0,14 |
| V2 — EMA 50 | +0,260 ; −15,9 % ; 0,46 | +0,260 ; −17,1 % ; 0,44 | +0,245 ; −15,9 % ; 0,41 | +0,121 ; −16,5 % ; 0,18 | +0,119 ; −17,6 % ; 0,19 | +0,104 ; −16,5 % ; 0,15 |
| V3 — Kalman 4 h | +0,208 ; −16,6 % ; 0,27 | +0,237 ; −13,6 % ; 0,41 | +0,310 ; −12,5 % ; 0,57 | +0,066 ; −21,8 % ; 0,05 | +0,095 ; −16,0 % ; 0,13 | +0,168 ; −14,8 % ; 0,25 |

## H. Stabilité annuelle (H = 26, 5 bps)

Cellule : espérance nette par trade en ATR (trades) ; dernière colonne : PnL composé par année à 0,25 % par ATR.

| Configuration | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 | PnL par année |
|---|---|---|---|---|---|---|---|
| RE-1 (contrôle) | +0,51 (189) | +0,02 (192) | +0,30 (173) | +0,50 (188) | +0,33 (171) | +0,55 (167) | +25 % ; +0 % ; +12 % ; +25 % ; +15 % ; +18 % |
| V1 — EMA 200 | +0,29 (121) | +0,33 (109) | −0,14 (123) | +0,29 (124) | +0,35 (113) | +0,20 (106) | +8 % ; +9 % ; −4 % ; +9 % ; +11 % ; +6 % |
| V1 — EMA 200 (figée) | +0,42 (103) | +0,27 (98) | −0,02 (106) | +0,47 (102) | +0,52 (101) | +0,48 (92) | +10 % ; +6 % ; −0 % ; +10 % ; +13 % ; +8 % |
| V2 — EMA 50 | +0,29 (134) | +0,00 (127) | +0,54 (131) | +0,24 (139) | +0,20 (124) | +0,29 (119) | +9 % ; −0 % ; +16 % ; +8 % ; +7 % ; +7 % |
| V2 — EMA 50 (figée) | +0,36 (122) | −0,00 (117) | +0,74 (121) | +0,44 (122) | +0,16 (112) | +0,38 (110) | +10 % ; −1 % ; +23 % ; +13 % ; +5 % ; +7 % |
| V3 — Kalman 4 h | +0,31 (120) | +0,20 (111) | −0,27 (109) | +0,36 (120) | +0,29 (101) | +0,54 (102) | +9 % ; +5 % ; −8 % ; +10 % ; +8 % ; +10 % |
| V3 — Kalman 4 h (figée) | +0,47 (105) | +0,12 (101) | −0,14 (89) | +0,55 (96) | +0,30 (88) | +0,59 (89) | +12 % ; +2 % ; −4 % ; +10 % ; +6 % ; +9 % |
