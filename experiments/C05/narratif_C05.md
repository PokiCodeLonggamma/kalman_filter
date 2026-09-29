# EXP-C05 — Sensibilité globale de la stratégie cœur (RE-1)

- **Date :** 2026-09-29.
- **Étape :** C Enveloppe, dernière expérience avant l'Étape D. Diagnostic de robustesse, sans nouvelle règle.
- **Actif et période :** BTC/USD Bitstamp 30 min, 2020-01 → 2025-12. 2026, ETH et XRP ne sont pas lus.
- **Frais :** 5 et 10 bps, présentés séparément. Capital à 0,25 % par ATR14(t) ; 1x en référence.
- **Contrôle :** RE-1 :
  - R2 hors `nis_z_100` Q4 ;
  - F2b sans stop, F3 SL-B à l'extremum ;
  - H = 26, cooldown, pyramiding 0.
- **Analyse :** `experiments/C05/run_C05.py`. Aucun module de `src/` n'est modifié : le script paramètre des fonctions certifiées (`route_levels`, SL-B δ, quantile de B01).

## 0. Cadrage

- **QUESTION :** les trois seuils durs de RE-1 reposent-ils sur des plateaux, ou sur des crêtes que l'Étape D risquerait de ne pas retrouver ? Les trois seuils sont :
  - la frontière F2b / F3 à 0,85 de `retrace_ratio` ;
  - la marge δ = 0 du stop de F3 ;
  - l'exclusion de `nis_z_100` au-delà de P75.
- **PERTINENCE POUR LE FILTRE AKF :**
  - Chacun de ces seuils traduit une lecture physique du moteur : la position dans le range, l'invalidation du breakout, le choc d'innovation.
  - S'ils sont physiques, la performance doit varier doucement autour d'eux. Une crête signalerait un ajustement au bruit de BTC 2020-2025 avant la portabilité.
- **CE QUE LE PROTOCOLE MESURE RÉELLEMENT :**
  - la sensibilité locale, un seuil à la fois, de l'espérance [IC], du PnL, du MDD et du Calmar, à 5 et 10 bps ;
  - l'écart à RE-1 :
    - apparié trade par trade pour A et B, qui gardent les entrées de RE-1 ;
    - sur les mêmes mois tirés pour C, qui change l'univers ;
  - le risque de chemin et l'équivalent en taille ;
  - les mécanismes :
    - effet du stop par bande de retracement ;
    - décomposition de C en trades retirés, perdus, nouveaux et libérés ;
    - espérance par bande de `nis_z_100`.
- **CE QU'IL NE PERMET PAS DE CONCLURE :**
  - une validation hors échantillon (Étape D) ;
  - les interactions entre seuils (OFAT, aucune grille croisée) ;
  - la sensibilité des seuils non testés : coupure de `leg_atr` à la médiane, borne 0,50 de `retrace_ratio`, veto R3 (H l'a été en C02bis : plateau H20-32) ;
  - un meilleur réglage : aucun point de grille n'est adopté a posteriori.

## Règle de lecture (fixée avant le calcul, dans l'en-tête du script)

- **Voisins immédiats de RE-1 :** A 0,80 et 0,90 ; B −0,25 et +0,25 ; C P70 et P80.
- **Un voisin se dégrade nettement si l'une des trois conditions est remplie :**
  - (d1) son écart d'espérance à RE-1 est ≤ −20 % de l'espérance de RE-1, avec un IC 95 % entièrement négatif ;
  - (d2) son espérance ou son Calmar est inférieur à la moitié de ceux de RE-1 ;
  - (d3) son MDD valorisé est plus profond que 1,5 fois celui de RE-1.
- **Verdict :**
  - plateau : aucun voisin en dégradation nette ;
  - falaise : un seul ;
  - crête : les deux.
- **Signalement :** falaise et crête sont signalées formellement avant l'Étape D.
- **Lecture principale :** 5 bps ; 10 bps en contrôle.
- **Points extrêmes :** ils décrivent la pente sans entrer dans le verdict.
- **Voisin meilleur :** un voisin significativement meilleur est noté, jamais adopté.

## 1. [CODE] Implémentation et contrôles

**Grilles, les deux autres seuils restant à leur valeur de RE-1 :**
- **A, frontière F2b / F3 :** F3 si `retrace_ratio` ≥ b, F2b si 0,50 ≤ `retrace_ratio` < b, avec b ∈ {0,75 ; 0,80 ; 0,85 ; 0,90 ; 0,95}.
  - L'univers R2 ne change pas.
  - En cooldown, les entrées non plus : seul le stop des trades dont le retracement est entre b et 0,85 change (77 à 190 trades).
- **B, marge du stop de F3 :** niveau = extremum du segment ∓ δ · ATR14(t), avec δ ∈ {−0,25 ; 0 ; +0,25 ; +0,50}.
  - δ < 0 place le stop à l'intérieur du range (plus serré).
  - Le plancher de 0,25 ATR sous l'entrée n'est jamais actif.
  - La distance médiane du stop passe de 1,84 à 2,59 ATR.
- **C, exclusion de `nis_z_100` :** signal gardé si `nis_z_100` ≤ quantile p de l'atlas entier, avec p ∈ {0,70 ; 0,75 ; 0,80 ; 0,85 ; 0,90}. C'est la convention du Q4 de B01.
  - Seuils : 0,919 / 1,225 / 1,599 / 2,057 / 2,749.
  - Candidats : 1 358 à 1 705 ; ils vont par emboîtement.

**Contrôles bloquants, tous passés :**
- ancre P6.5d ;
- p = 0,75 redonne les 1 452 candidats (F2b 741, F3 711) et la frontière 0,85 redonne les sous-familles de B01 ;
- RE-1 est identique à C02bis trade par trade, et ses métriques à `resultats_C02bis.csv` (écart relatif maximal 4,5·10⁻⁶) ;
- le point RE-1 de chaque grille redonne RE-1 ;
- les variantes de A et de B ont les entrées de RE-1 ;
- la décomposition de C est refermée à 10⁻⁹ près ;
- les signaux joués seuls redonnent les trades de RE-1.

**Calcul :** 28 lignes en 54 s.

## 2. [OBS] Mesures (H26 ; PnL et MDD à 0,25 % par ATR)

### 2.1 A — frontière F2b / F3 : plateau de 0,85 à 0,95, pente en dessous

| Frontière | Espérance ATR [IC], 5 bps | Effet apparié à RE-1 [IC] | MDD | Calmar | 10 bps : espérance ; Calmar |
|---|---|---|---|---|---|
| 0,75 | +0,274 [−0,001 ; +0,543] | −0,095 [−0,157 ; −0,030] | −19,2 % | 0,58 | +0,138 ; 0,25 |
| 0,80 | +0,331 [+0,054 ; +0,608] | −0,038 [−0,091 ; +0,009] | −14,1 % | 0,99 | +0,195 ; 0,48 |
| **0,85 (RE-1)** | **+0,369 [+0,098 ; +0,645]** | — | **−13,5 %** | **1,16** | **+0,233 ; 0,60** |
| 0,90 | +0,391 [+0,119 ; +0,662] | +0,022 [−0,022 ; +0,068] | −13,4 % | 1,21 | +0,255 ; 0,64 |
| 0,95 | +0,396 [+0,116 ; +0,679] | +0,028 [−0,052 ; +0,108] | −14,2 % | 1,18 | +0,260 ; 0,64 |

- **De 0,85 à 0,95, rien ne bouge significativement :**
  - espérance +0,369 à +0,396 ;
  - MDD −13,4 à −14,2 % ;
  - Calmar 1,16 à 1,21.
- **En dessous, la pente est descendante :**
  - à 0,80, −0,038 (non significatif) ;
  - à 0,75, −0,095 ATR par trade (significatif), MDD −19,2 %.
- **RE-1 est 3e sur 5**, en espérance comme en Calmar. La frontière 0,85, fixée avant tout calcul en B01, n'a pas été calée sur cette courbe.
- **Mécanisme : l'effet du stop à l'extremum par bande de retracement** (trades de RE-1, mêmes entrées ; effet par trade du SL-B 0 contre l'absence de stop).

  | Retracement | Trades | Sans stop (5 bps) | Effet du stop [IC] |
  |---|---|---|---|
  | [0,50 ; 0,75[ | 390 | +0,220 | −0,151 [−0,485 ; +0,202] |
  | [0,75 ; 0,80[ | 106 | +1,027 | −0,579 [−1,147 ; −0,026] |
  | [0,80 ; 0,85[ | 77 | +0,887 | −0,530 [−1,274 ; +0,129] |
  | [0,85 ; 0,90[ | 87 | −0,101 | −0,275 [−0,815 ; +0,283] |
  | [0,90 ; 0,95[ | 103 | +0,448 | −0,058 [−0,807 ; +0,661] |
  | [0,95 ; ∞[ | 317 | +0,258 | +0,144 [−0,148 ; +0,447] |

  - Sous 0,85, le stop coupe les meilleurs F2b : les bandes 0,75-0,85 font +0,9 à +1,0 ATR sans stop. Le coût est de 0,53 à 0,58 ATR par trade touché.
  - Le stop ne devient neutre ou utile qu'à partir de 0,90, et positif seulement au-delà de 0,95, sans que ce soit significatif.
  - Sur les 507 F3 de RE-1, l'effet net sur l'espérance est ≈ +0,03 ATR : le stop de F3 sert le risque, pas l'alpha (C02bis).

### 2.2 B — marge du stop de F3 : plateau de −0,25 à +0,25 ATR

| δ (ATR) | Espérance ATR [IC], 5 bps | Effet apparié à RE-1 [IC] | MDD | Calmar | Stoppés parmi F3 | 10 bps : espérance ; Calmar |
|---|---|---|---|---|---|---|
| −0,25 | +0,360 [+0,093 ; +0,627] | −0,009 [−0,050 ; +0,026] | −13,0 % | 1,19 | 55 % | +0,224 ; 0,63 |
| **0 (RE-1)** | **+0,369 [+0,098 ; +0,645]** | — | **−13,5 %** | **1,16** | 51 % | **+0,233 ; 0,60** |
| +0,25 | +0,355 [+0,079 ; +0,637] | −0,014 [−0,036 ; +0,014] | −14,0 % | 1,07 | 46 % | +0,219 ; 0,54 |
| +0,50 | +0,333 [+0,059 ; +0,612] | −0,036 [−0,066 ; −0,000] | −15,2 % | 0,91 | 44 % | +0,197 ; 0,45 |

- **Entre −0,25 et +0,25 ATR, l'effet apparié reste dans ±0,015 ATR**, non significatif, et le MDD entre −13,0 et −14,0 %.
- **Élargir davantage coûte peu à peu :** à +0,50, −0,036 ATR (IC en limite de 0), MDD −15,2 %, Calmar 0,91.
- **RE-1 est 1er sur 4 en espérance et 2e en Calmar** (−0,25 : 1,19).
- **δ = 0 n'est pas un artefact de bord.** C'était la valeur la plus serrée de la grille de C02, {0 ; 0,25 ; 0,5 ; 1}. Le côté plus serré, testé ici pour la première fois, est plat.

### 2.3 C — exclusion de `nis_z_100` : RE-1 au sommet, pente plus raide côté permissif

| Exclusion | Espérance ATR [IC], 5 bps | Écart à RE-1, mois communs [IC] | MDD | Calmar | Trades | 10 bps : espérance ; Calmar |
|---|---|---|---|---|---|---|
| > P70 | +0,350 [+0,074 ; +0,636] | −0,019 [−0,084 ; +0,047] | −17,8 % | 0,77 | 1 023 | +0,212 ; 0,40 |
| **> P75 (RE-1)** | **+0,369 [+0,098 ; +0,645]** | — | **−13,5 %** | **1,16** | 1 080 | **+0,233 ; 0,60** |
| > P80 | +0,310 [+0,049 ; +0,571] | −0,059 [−0,117 ; −0,009] | −15,9 % | 0,84 | 1 139 | +0,176 ; 0,40 |
| > P85 | +0,238 [−0,005 ; +0,494] | −0,131 [−0,213 ; −0,052] | −17,5 % | 0,59 | 1 192 | +0,105 ; 0,20 |
| > P90 | +0,219 [−0,011 ; +0,455] | −0,150 [−0,259 ; −0,044] | −17,7 % | 0,56 | 1 253 | +0,087 ; 0,16 |

- **RE-1 est 1er sur 5** en espérance et en Calmar, à 5 et 10 bps.
- **Côté permissif, la baisse est monotone et significative à chaque pas.** Les signaux admis perdent : −0,31 ATR par trade à P80, −0,53 à P85, −0,29 à P90. Chaque tranche de 5 centiles fait entrer des signaux de choc à espérance négative : c'est une protection progressive.
- **Côté restrictif (P70), l'espérance ne bouge pas** (−0,019, non significatif). Les 72 trades retirés étaient bons : +0,64 ATR par trade. Resserrer n'apporte rien.
  - Le MDD de −17,8 % et le Calmar de 0,77 viennent du chemin réel. Sur les chemins réordonnés, P70 fait mieux que RE-1 dans 49 % des cas pour le MDD et 26 % pour le Calmar (I-M10).
- **Par signal joué seul, sans chaîne, l'espérance change de signe au seuil P75 :**
  - P70-P75 : +0,53 [−0,27 ; +1,34] (94 signaux) ;
  - P75-P80 : −0,30 [−0,79 ; +0,20] (87 signaux) ;
  - P80-P85 : −0,74 ; P85-P90 : +0,22 ; au-delà de P90 : −0,41.

  Les IC des bandes voisines se recouvrent. Au-delà de P75, la part de F3 monte de 74 à 96 %.
- **Réserve de sélection :** P75 est la borne de quartile fixée en B01, mais l'exclusion de Q4 a été décidée après C01, sur les mêmes données. Que RE-1 soit le meilleur point de sa grille est donc en partie attendu. La version causale du seuil (P75 glissant ou expansif) tenait en C02bis (RE-4).

### 2.4 Huit métriques : RE-1 et ses voisins immédiats (H26, 5 bps)

| Métrique | RE-1 | A 0,80 | A 0,90 | B −0,25 | B +0,25 | C P70 | C P80 |
|---|---|---|---|---|---|---|---|
| PnL Net Total : 0,25 %/ATR ; 1x ; bps | +138 % ; +204 % ; +13 320 | +119 % ; +168 % ; +11 958 | +147 % ; +192 % ; +13 051 | +137 % ; +207 % ; +13 392 | +131 % ; +186 % ; +12 760 | +116 % ; +148 % ; +11 097 | +113 % ; +153 % ; +11 580 |
| Profit Factor (1x) | 1,20 | 1,18 | 1,19 | 1,20 | 1,18 | 1,17 | 1,16 |
| Win Rate | 44,3 % | 42,9 % | 45,5 % | 43,2 % | 45,1 % | 44,3 % | 43,9 % |
| Espérance : ATR [IC] ; bps | +0,369 [+0,098 ; +0,645] ; +12,3 | +0,331 [+0,054 ; +0,608] ; +11,1 | +0,391 [+0,119 ; +0,662] ; +12,1 | +0,360 [+0,093 ; +0,627] ; +12,4 | +0,355 [+0,079 ; +0,637] ; +11,8 | +0,350 [+0,074 ; +0,636] ; +10,8 | +0,310 [+0,049 ; +0,571] ; +10,2 |
| Max Drawdown ; Calmar | −13,5 % ; 1,16 | −14,1 % ; 0,99 | −13,4 % ; 1,21 | −13,0 % ; 1,19 | −14,0 % ; 1,07 | −17,8 % ; 0,77 | −15,9 % ; 0,84 |
| Trades (/mois) | 1 080 (15,0) | 1 080 (15,0) | 1 080 (15,0) | 1 080 (15,0) | 1 080 (15,0) | 1 023 (14,2) | 1 139 (15,8) |
| Durée médiane (barres) | 26 | 26 | 26 | 26 | 26 | 26 | 26 |
| Part des frais (1x) | 29 % | 31 % | 29 % | 29 % | 30 % | 32 % | 33 % |

- **Années :** les 14 points de grille ont 5 ou 6 années sur 6 à espérance positive. 2021 reste l'année faible, de −0,14 à +0,06 ATR.

### 2.5 Verdicts de la règle fixée avant le calcul

| Grille | 5 bps | 10 bps | Rang de RE-1 (espérance ; Calmar, 5 bps) |
|---|---|---|---|
| A — frontière F2b / F3 | plateau | plateau | 3/5 ; 3/5 |
| B — marge du stop de F3 | plateau | plateau | 1/4 ; 2/4 |
| C — exclusion de `nis_z_100` | plateau, en limite | **falaise (côté P80)** | 1/5 ; 1/5 |

- À 5 bps, l'écart de P80 (−0,059 ATR, IC < 0) reste sous le seuil (d1) de −0,074.
- À 10 bps, le même écart (−0,057) dépasse le seuil de −0,047, car l'espérance de RE-1 y est plus basse. L'effet physique est le même : c'est le seuil relatif qui change.

## 3. [HYP] Lectures

- **Le stop à l'extremum n'invalide le breakout qu'après un retracement presque complet de la jambe précédente** (≥ 0,90-0,95).
  - Plus bas, un retour à l'extremum est un retest, un balayage de liquidité comme pour F2b, et le couper détruit les meilleurs trades.
  - La frontière physique de l'invalidation est donc plutôt au-dessus de 0,85 qu'en dessous. RE-1 est au bord bas du plateau : une dérive vers le haut est sans danger, une dérive vers le bas coûte.
- **L'information du stop de F3 est une zone de ±0,25 ATR autour de l'extremum, pas un point.** Un breakout qui revient dans cette zone a échoué. Lui laisser plus de marge laisse courir des pertes, sans rattraper de gagnants.
- **Au-delà de P75, `nis_z_100` marque des signaux déclenchés par une bougie de choc (K2)**, presque tous des F3 (74 à 96 %). Le filtre suit alors un choc plutôt qu'un retournement de vitesse. La pente est continue ; seul le passage de signe au voisinage de P75 est net, et il reste bruité.

## 4. [DECISION] Proposée

- **RE-1 est conservé inchangé pour l'Étape D.** Aucun paramètre ne bouge. Les voisins meilleurs, A 0,90 et 0,95 et B −0,25, sont notés mais ne sont ni significatifs ni adoptés.
- **Frontière F2b / F3 et marge du stop :** plateaux. Rien à signaler avant l'Étape D.
- **Signalement formel : l'exclusion de `nis_z_100` est une falaise d'un côté.**
  - Formelle à 10 bps, en limite à 5 bps.
  - Resserrer le seuil ne change pas l'espérance (−0,02, non significatif).
  - Le relâcher de 5 centiles coûte 0,06 ATR par trade : −16 % de l'espérance à 5 bps, −25 % à 10 bps.
  - Le relâcher de 10 centiles coûte 0,13 ATR : −35 % et −55 %.
  - C'est le seuil le plus sensible de RE-1, et le seul que la sélection de C01 a pu favoriser.
- **Conséquence proposée pour l'Étape D, sans réglage :** garder la règle P75 calculée sur les signaux de chaque actif, ou sa version causale.
  - Publier pour chaque actif l'espérance par bande de `nis_z_100`, comme ici, pour vérifier que la bascule reste au voisinage de P75.
  - Une bascule nettement plus haute ou plus basse serait le premier signal de non-portabilité.
