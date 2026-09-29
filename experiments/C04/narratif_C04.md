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
