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

---

# Annexes chiffrées (générées par `run_C05.py`)

## A. Contrôles bloquants

| Contrôle | Résultat |
|---|---|
| Ancre P6.5d | 6 037 et 6 589 trades identiques |
| Univers paramétré | p = 0,75 redonne les 1 452 candidats de RE-1 (F2b 741, F3 711) ; frontière 0,85 = sous-familles de B01 ; 1 874 signaux de R2 avant l'exclusion de nis_z_100, sur 7 296 signaux de l'atlas |
| RE-1 = RE-1 de C02bis | 1 080 trades identiques à H26 ; 2 lignes de métriques identiques à resultats_C02bis.csv (écart relatif max 4,5·10⁻⁶) |
| Point RE-1 de chaque grille | A = 0,85, B = 0 et C = P75 : trades identiques à RE-1 |
| Mêmes entrées (A, B) | chaque variante de A et de B a les entrées de RE-1, trade par trade (effet apparié) |
| Décomposition (C) | variante = RE-1 − retirés − perdus + nouveaux + libérés, refermée à 10⁻⁹ près, à 5 et 10 bps |
| Signaux joués seuls (bandes) | restreints aux signaux pris par RE-1, ils redonnent ses trades |
| Période | 2020-01 → 2025-12 ; aucune barre de 2026 lue ; ETH et XRP non lus |

## B. Grilles

**A — frontière F2b / F3** (trades de RE-1, mêmes entrées)

| Frontière | Trades F2b | Trades F3 | Changés de sous-famille | Stoppés parmi F3 |
|---|---|---|---|---|
| 0,75 | 390 | 690 | 183 → F3 ; 0 → F2b | 52 % |
| 0,80 | 496 | 584 | 77 → F3 ; 0 → F2b | 51 % |
| 0,85 (RE-1) | 573 | 507 | 0 → F3 ; 0 → F2b | 51 % |
| 0,90 | 660 | 420 | 0 → F3 ; 87 → F2b | 50 % |
| 0,95 | 763 | 317 | 0 → F3 ; 190 → F2b | 49 % |

**B — marge du stop de F3** (distance du stop à l'entrée open[t + 1], ATR14(t) ; plancher : 0,25 ATR)

| δ (ATR) | Trades F3 | Distance médiane du stop | Stops au plancher | Stoppés parmi F3 |
|---|---|---|---|---|
| −0,25 | 507 | 1,84 | 0,0 % | 55 % |
| 0 (RE-1) | 507 | 2,09 | 0,0 % | 51 % |
| +0,25 | 507 | 2,34 | 0,0 % | 46 % |
| +0,50 | 507 | 2,59 | 0,0 % | 44 % |

**C — exclusion de nis_z_100** (seuil : quantile de l'atlas entier ; part exclue : des signaux de R2 avant l'exclusion)

| Centile | Seuil nis_z_100 | Candidats | Part exclue | Trades |
|---|---|---|---|---|
| P70 | 0,919 | 1 358 | 27,5 % | 1 023 |
| P75 (RE-1) | 1,224 | 1 452 | 22,5 % | 1 080 |
| P80 | 1,599 | 1 539 | 17,9 % | 1 139 |
| P85 | 2,057 | 1 621 | 13,5 % | 1 192 |
| P90 | 2,749 | 1 705 | 9,0 % | 1 253 |

## C. Huit métriques à H = 26

**A — frontière F2b / F3 (retrace_ratio), 5 bps**

| Configuration | PnL : 0,25 %/ATR ; 1x ; bps (1x) | PF : 1x ; pondéré | WR | Espérance : bps [IC] ; ATR [IC] | MDD valorisé : 0,25 %/ATR ; 1x | Trades (/mois) ; stoppés | Durée méd. | Part des frais ; brut/trade |
|---|---|---|---|---|---|---|---|---|
| frontière 0,75 | +89 % ; +104 % ; +9180 | 1,14 ; 1,21 | 41,7 % | +8,5 [−4,0 ; +21,1] ; +0,274 [−0,001 ; +0,543] | −19,2 % ; −55 % | 1 080 (15,0) ; 33 % | 26 | 37 % ; +13,5 |
| frontière 0,80 | +119 % ; +168 % ; +11958 | 1,18 ; 1,26 | 42,9 % | +11,1 [−1,8 ; +23,7] ; +0,331 [+0,054 ; +0,608] | −14,1 % ; −47 % | 1 080 (15,0) ; 28 % | 26 | 31 % ; +16,1 |
| frontière 0,85 (RE-1) | +138 % ; +204 % ; +13320 | 1,20 ; 1,28 | 44,3 % | +12,3 [+0,2 ; +24,4] ; +0,369 [+0,098 ; +0,645] | −13,5 % ; −44 % | 1 080 (15,0) ; 24 % | 26 | 29 % ; +17,3 |
| frontière 0,90 | +147 % ; +192 % ; +13051 | 1,19 ; 1,29 | 45,5 % | +12,1 [+0,0 ; +24,4] ; +0,391 [+0,119 ; +0,662] | −13,4 % ; −44 % | 1 080 (15,0) ; 19 % | 26 | 29 % ; +17,1 |
| frontière 0,95 | +152 % ; +219 % ; +14058 | 1,20 ; 1,29 | 46,4 % | +13,0 [−0,3 ; +26,0] ; +0,396 [+0,116 ; +0,679] | −14,2 % ; −46 % | 1 080 (15,0) ; 14 % | 26 | 28 % ; +18,0 |

**A — frontière F2b / F3 (retrace_ratio), 10 bps**

| Configuration | PnL : 0,25 %/ATR ; 1x ; bps (1x) | PF : 1x ; pondéré | WR | Espérance : bps [IC] ; ATR [IC] | MDD valorisé : 0,25 %/ATR ; 1x | Trades (/mois) ; stoppés | Durée méd. | Part des frais ; brut/trade |
|---|---|---|---|---|---|---|---|---|
| frontière 0,75 | +37 % ; +19 % ; +3780 | 1,05 ; 1,10 | 40,3 % | +3,5 [−9,0 ; +16,1] ; +0,138 [−0,137 ; +0,411] | −21,5 % ; −58 % | 1 080 (15,0) ; 33 % | 26 | 74 % ; +13,5 |
| frontière 0,80 | +58 % ; +56 % ; +6558 | 1,09 ; 1,15 | 41,5 % | +6,1 [−6,8 ; +18,7] ; +0,195 [−0,089 ; +0,478] | −16,6 % ; −50 % | 1 080 (15,0) ; 28 % | 26 | 62 % ; +16,1 |
| frontière 0,85 (RE-1) | +72 % ; +77 % ; +7920 | 1,11 ; 1,17 | 42,8 % | +7,3 [−4,8 ; +19,4] ; +0,233 [−0,041 ; +0,511] | −15,9 % ; −48 % | 1 080 (15,0) ; 24 % | 26 | 58 % ; +17,3 |
| frontière 0,90 | +78 % ; +70 % ; +7651 | 1,11 ; 1,18 | 44,0 % | +7,1 [−5,0 ; +19,4] ; +0,255 [−0,018 ; +0,525] | −15,8 % ; −48 % | 1 080 (15,0) ; 19 % | 26 | 59 % ; +17,1 |
| frontière 0,95 | +82 % ; +86 % ; +8658 | 1,12 ; 1,19 | 44,7 % | +8,0 [−5,3 ; +21,0] ; +0,260 [−0,020 ; +0,541] | −16,6 % ; −50 % | 1 080 (15,0) ; 14 % | 26 | 56 % ; +18,0 |

**B — marge δ du stop de F3 (ATR14(t)), 5 bps**

| Configuration | PnL : 0,25 %/ATR ; 1x ; bps (1x) | PF : 1x ; pondéré | WR | Espérance : bps [IC] ; ATR [IC] | MDD valorisé : 0,25 %/ATR ; 1x | Trades (/mois) ; stoppés | Durée méd. | Part des frais ; brut/trade |
|---|---|---|---|---|---|---|---|---|
| δ = −0,25 ATR | +137 % ; +207 % ; +13392 | 1,20 ; 1,29 | 43,1 % | +12,4 [+0,5 ; +24,5] ; +0,360 [+0,093 ; +0,627] | −13,0 % ; −42 % | 1 080 (15,0) ; 26 % | 26 | 29 % ; +17,4 |
| δ = 0 ATR (RE-1) | +138 % ; +204 % ; +13320 | 1,20 ; 1,28 | 44,3 % | +12,3 [+0,2 ; +24,4] ; +0,369 [+0,098 ; +0,645] | −13,5 % ; −44 % | 1 080 (15,0) ; 24 % | 26 | 29 % ; +17,3 |
| δ = +0,25 ATR | +131 % ; +186 % ; +12760 | 1,18 ; 1,27 | 45,1 % | +11,8 [−0,5 ; +24,7] ; +0,355 [+0,079 ; +0,637] | −14,0 % ; −45 % | 1 080 (15,0) ; 22 % | 26 | 30 % ; +16,8 |
| δ = +0,50 ATR | +118 % ; +143 % ; +11172 | 1,16 ; 1,24 | 45,4 % | +10,3 [−2,1 ; +23,1] ; +0,333 [+0,059 ; +0,612] | −15,2 % ; −47 % | 1 080 (15,0) ; 21 % | 26 | 33 % ; +15,3 |

**B — marge δ du stop de F3 (ATR14(t)), 10 bps**

| Configuration | PnL : 0,25 %/ATR ; 1x ; bps (1x) | PF : 1x ; pondéré | WR | Espérance : bps [IC] ; ATR [IC] | MDD valorisé : 0,25 %/ATR ; 1x | Trades (/mois) ; stoppés | Durée méd. | Part des frais ; brut/trade |
|---|---|---|---|---|---|---|---|---|
| δ = −0,25 ATR | +72 % ; +79 % ; +7992 | 1,12 ; 1,18 | 41,7 % | +7,4 [−4,5 ; +19,5] ; +0,224 [−0,049 ; +0,497] | −15,1 % ; −46 % | 1 080 (15,0) ; 26 % | 26 | 57 % ; +17,4 |
| δ = 0 ATR (RE-1) | +72 % ; +77 % ; +7920 | 1,11 ; 1,17 | 42,8 % | +7,3 [−4,8 ; +19,4] ; +0,233 [−0,041 ; +0,511] | −15,9 % ; −48 % | 1 080 (15,0) ; 24 % | 26 | 58 % ; +17,3 |
| δ = +0,25 ATR | +67 % ; +67 % ; +7360 | 1,10 ; 1,16 | 43,5 % | +6,8 [−5,5 ; +19,7] ; +0,219 [−0,061 ; +0,504] | −16,4 % ; −49 % | 1 080 (15,0) ; 22 % | 26 | 59 % ; +16,8 |
| δ = +0,50 ATR | +58 % ; +41 % ; +5772 | 1,08 ; 1,14 | 43,8 % | +5,3 [−7,1 ; +18,1] ; +0,197 [−0,079 ; +0,479] | −17,6 % ; −51 % | 1 080 (15,0) ; 21 % | 26 | 65 % ; +15,3 |

**C — exclusion de nis_z_100 (centile de l'atlas), 5 bps**

| Configuration | PnL : 0,25 %/ATR ; 1x ; bps (1x) | PF : 1x ; pondéré | WR | Espérance : bps [IC] ; ATR [IC] | MDD valorisé : 0,25 %/ATR ; 1x | Trades (/mois) ; stoppés | Durée méd. | Part des frais ; brut/trade |
|---|---|---|---|---|---|---|---|---|
| exclusion > P70 | +116 % ; +148 % ; +11097 | 1,17 ; 1,27 | 44,3 % | +10,8 [−1,9 ; +23,1] ; +0,350 [+0,074 ; +0,636] | −17,8 % ; −48 % | 1 023 (14,2) ; 23 % | 26 | 32 % ; +15,8 |
| exclusion > P75 (RE-1) | +138 % ; +204 % ; +13320 | 1,20 ; 1,28 | 44,3 % | +12,3 [+0,2 ; +24,4] ; +0,369 [+0,098 ; +0,645] | −13,5 % ; −44 % | 1 080 (15,0) ; 24 % | 26 | 29 % ; +17,3 |
| exclusion > P80 | +113 % ; +153 % ; +11580 | 1,16 ; 1,23 | 43,9 % | +10,2 [−1,5 ; +22,0] ; +0,310 [+0,049 ; +0,571] | −15,9 % ; −42 % | 1 139 (15,8) ; 25 % | 26 | 33 % ; +15,2 |
| exclusion > P85 | +80 % ; +62 % ; +7217 | 1,09 ; 1,17 | 43,0 % | +6,1 [−4,7 ; +17,1] ; +0,238 [−0,005 ; +0,494] | −17,5 % ; −50 % | 1 192 (16,6) ; 26 % | 26 | 45 % ; +11,1 |
| exclusion > P90 | +76 % ; +61 % ; +7249 | 1,09 ; 1,16 | 42,9 % | +5,8 [−4,2 ; +15,9] ; +0,219 [−0,011 ; +0,455] | −17,7 % ; −46 % | 1 253 (17,4) ; 27 % | 26 | 46 % ; +10,8 |

**C — exclusion de nis_z_100 (centile de l'atlas), 10 bps**

| Configuration | PnL : 0,25 %/ATR ; 1x ; bps (1x) | PF : 1x ; pondéré | WR | Espérance : bps [IC] ; ATR [IC] | MDD valorisé : 0,25 %/ATR ; 1x | Trades (/mois) ; stoppés | Durée méd. | Part des frais ; brut/trade |
|---|---|---|---|---|---|---|---|---|
| exclusion > P70 | +58 % ; +49 % ; +5982 | 1,09 ; 1,16 | 42,7 % | +5,8 [−6,9 ; +18,1] ; +0,212 [−0,070 ; +0,498] | −20,0 % ; −52 % | 1 023 (14,2) ; 23 % | 26 | 63 % ; +15,8 |
| exclusion > P75 (RE-1) | +72 % ; +77 % ; +7920 | 1,11 ; 1,17 | 42,8 % | +7,3 [−4,8 ; +19,4] ; +0,233 [−0,041 ; +0,511] | −15,9 % ; −48 % | 1 080 (15,0) ; 24 % | 26 | 58 % ; +17,3 |
| exclusion > P80 | +52 % ; +43 % ; +5885 | 1,08 ; 1,13 | 42,5 % | +5,2 [−6,5 ; +17,0] ; +0,176 [−0,086 ; +0,443] | −18,0 % ; −46 % | 1 139 (15,8) ; 25 % | 26 | 66 % ; +15,2 |
| exclusion > P85 | +27 % ; −11 % ; +1257 | 1,02 ; 1,07 | 41,6 % | +1,1 [−9,7 ; +12,1] ; +0,105 [−0,141 ; +0,363] | −20,1 % ; −54 % | 1 192 (16,6) ; 26 % | 26 | 90 % ; +11,1 |
| exclusion > P90 | +21 % ; −14 % ; +984 | 1,01 ; 1,06 | 41,5 % | +0,8 [−9,2 ; +10,9] ; +0,087 [−0,145 ; +0,326] | −20,7 % ; −54 % | 1 253 (17,4) ; 27 % | 26 | 93 % ; +10,8 |

## D. Sensibilité (H = 26)

Espérance nette par trade en ATR [IC 95 % par grappes mensuelles] ; PnL composé à 0,25 % par ATR et son annualisé ; MDD valorisé ; Calmar = PnL annualisé / |MDD| sur 6 ans. Écart d'espérance à RE-1 : effet apparié trade par trade pour A et B (mêmes entrées, indépendant des frais), écart des moyennes sur les mêmes mois tirés pour C. Chemins : 2 000 tirages des mois d'entrée avec remise, mêmes mois pour RE-1 et la variante ; écart observé [P2,5 ; P97,5] ; part des chemins où la variante fait mieux (MDD aux sorties). À MDD égal : écart de PnL annualisé entre la variante et RE-1 mis à la taille qui donne le même MDD valorisé (risque par ATR de RE-1 entre parenthèses).

**A — frontière F2b / F3 (retrace_ratio), 5 bps**

| Configuration | Espérance ATR [IC] | PnL ; annualisé | MDD | Calmar | Écart d'espérance à RE-1 [IC] | Écart de MDD (points) ; chemins meilleurs | Écart de Calmar ; chemins meilleurs | À MDD égal face à RE-1 |
|---|---|---|---|---|---|---|---|---|
| frontière 0,75 | +0,274 [−0,001 ; +0,543] | +89 % ; +11,2 %/an | −19,2 % | 0,58 | −0,095 [−0,157 ; −0,030] | −5,8 [−9,3 ; +1,8] ; 13 % | −0,61 [−0,95 ; −0,04] ; 1 % | −8,7 pt (0,361 %) |
| frontière 0,80 | +0,331 [+0,054 ; +0,608] | +119 % ; +14,0 %/an | −14,1 % | 0,99 | −0,038 [−0,091 ; +0,009] | −0,8 [−5,6 ; +1,8] ; 22 % | −0,19 [−0,57 ; +0,11] ; 10 % | −2,2 pt (0,263 %) |
| frontière 0,85 (RE-1) | +0,369 [+0,098 ; +0,645] | +138 % ; +15,6 %/an | −13,5 % | 1,16 | — | — | — | — |
| frontière 0,90 | +0,391 [+0,119 ; +0,662] | +147 % ; +16,2 %/an | −13,4 % | 1,21 | +0,022 [−0,022 ; +0,068] | +0,1 [−2,0 ; +3,0] ; 60 % | +0,06 [−0,19 ; +0,38] ; 71 % | +0,8 pt (0,248 %) |
| frontière 0,95 | +0,396 [+0,116 ; +0,679] | +152 % ; +16,7 %/an | −14,2 % | 1,18 | +0,028 [−0,052 ; +0,108] | −0,7 [−6,1 ; +4,5] ; 31 % | +0,02 [−0,47 ; +0,57] ; 50 % | +0,4 pt (0,264 %) |

**A — frontière F2b / F3 (retrace_ratio), 10 bps**

| Configuration | Espérance ATR [IC] | PnL ; annualisé | MDD | Calmar | Écart d'espérance à RE-1 [IC] | Écart de MDD (points) ; chemins meilleurs | Écart de Calmar ; chemins meilleurs | À MDD égal face à RE-1 |
|---|---|---|---|---|---|---|---|---|
| frontière 0,75 | +0,138 [−0,137 ; +0,411] | +37 % ; +5,3 %/an | −21,5 % | 0,25 | −0,095 [−0,157 ; −0,030] | −5,7 [−12,8 ; +1,6] ; 9 % | −0,37 [−0,68 ; −0,04] ; 1 % | −6,3 pt (0,344 %) |
| frontière 0,80 | +0,195 [−0,089 ; +0,478] | +58 % ; +8,0 %/an | −16,6 % | 0,48 | −0,038 [−0,091 ; +0,009] | −0,8 [−7,0 ; +1,8] ; 20 % | −0,13 [−0,39 ; +0,06] ; 9 % | −1,8 pt (0,261 %) |
| frontière 0,85 (RE-1) | +0,233 [−0,041 ; +0,511] | +72 % ; +9,5 %/an | −15,9 % | 0,60 | — | — | — | — |
| frontière 0,90 | +0,255 [−0,018 ; +0,525] | +78 % ; +10,1 %/an | −15,8 % | 0,64 | +0,022 [−0,022 ; +0,068] | +0,1 [−2,3 ; +4,0] ; 65 % | +0,05 [−0,12 ; +0,25] ; 74 % | +0,7 pt (0,249 %) |
| frontière 0,95 | +0,260 [−0,020 ; +0,541] | +82 % ; +10,5 %/an | −16,6 % | 0,64 | +0,028 [−0,052 ; +0,108] | −0,7 [−6,5 ; +6,0] ; 38 % | +0,04 [−0,27 ; +0,42] ; 58 % | +0,7 pt (0,262 %) |

**B — marge δ du stop de F3 (ATR14(t)), 5 bps**

| Configuration | Espérance ATR [IC] | PnL ; annualisé | MDD | Calmar | Écart d'espérance à RE-1 [IC] | Écart de MDD (points) ; chemins meilleurs | Écart de Calmar ; chemins meilleurs | À MDD égal face à RE-1 |
|---|---|---|---|---|---|---|---|---|
| δ = −0,25 ATR | +0,360 [+0,093 ; +0,627] | +137 % ; +15,5 %/an | −13,0 % | 1,19 | −0,009 [−0,050 ; +0,026] | +0,2 [−2,4 ; +2,3] ; 68 % | +0,01 [−0,26 ; +0,23] ; 60 % | +0,3 pt (0,242 %) |
| δ = 0 ATR (RE-1) | +0,369 [+0,098 ; +0,645] | +138 % ; +15,6 %/an | −13,5 % | 1,16 | — | — | — | — |
| δ = +0,25 ATR | +0,355 [+0,079 ; +0,637] | +131 % ; +15,0 %/an | −14,0 % | 1,07 | −0,014 [−0,036 ; +0,014] | −0,6 [−2,5 ; +1,6] ; 23 % | −0,10 [−0,27 ; +0,14] ; 17 % | −1,1 pt (0,261 %) |
| δ = +0,50 ATR | +0,333 [+0,059 ; +0,612] | +118 % ; +13,9 %/an | −15,2 % | 0,91 | −0,036 [−0,066 ; −0,000] | −1,7 [−4,3 ; +1,7] ; 21 % | −0,26 [−0,49 ; +0,07] ; 7 % | −3,1 pt (0,283 %) |

**B — marge δ du stop de F3 (ATR14(t)), 10 bps**

| Configuration | Espérance ATR [IC] | PnL ; annualisé | MDD | Calmar | Écart d'espérance à RE-1 [IC] | Écart de MDD (points) ; chemins meilleurs | Écart de Calmar ; chemins meilleurs | À MDD égal face à RE-1 |
|---|---|---|---|---|---|---|---|---|
| δ = −0,25 ATR | +0,224 [−0,049 ; +0,497] | +72 % ; +9,4 %/an | −15,1 % | 0,63 | −0,009 [−0,050 ; +0,026] | +0,6 [−2,8 ; +2,7] ; 67 % | +0,02 [−0,17 ; +0,14] ; 54 % | +0,3 pt (0,236 %) |
| δ = 0 ATR (RE-1) | +0,233 [−0,041 ; +0,511] | +72 % ; +9,5 %/an | −15,9 % | 0,60 | — | — | — | — |
| δ = +0,25 ATR | +0,219 [−0,061 ; +0,504] | +67 % ; +8,9 %/an | −16,4 % | 0,54 | −0,014 [−0,036 ; +0,014] | −0,5 [−3,2 ; +1,7] ; 23 % | −0,06 [−0,17 ; +0,07] ; 18 % | −0,8 pt (0,259 %) |
| δ = +0,50 ATR | +0,197 [−0,079 ; +0,479] | +58 % ; +7,9 %/an | −17,6 % | 0,45 | −0,036 [−0,066 ; −0,000] | −1,7 [−5,5 ; +1,9] ; 18 % | −0,15 [−0,33 ; +0,02] ; 6 % | −2,3 pt (0,278 %) |

**C — exclusion de nis_z_100 (centile de l'atlas), 5 bps**

| Configuration | Espérance ATR [IC] | PnL ; annualisé | MDD | Calmar | Écart d'espérance à RE-1 [IC] | Écart de MDD (points) ; chemins meilleurs | Écart de Calmar ; chemins meilleurs | À MDD égal face à RE-1 |
|---|---|---|---|---|---|---|---|---|
| exclusion > P70 | +0,350 [+0,074 ; +0,636] | +116 % ; +13,7 %/an | −17,8 % | 0,77 | −0,019 [−0,084 ; +0,047] | −3,9 [−5,0 ; +4,2] ; 49 % | −0,40 [−0,59 ; +0,30] ; 26 % | −5,2 pt (0,333 %) |
| exclusion > P75 (RE-1) | +0,369 [+0,098 ; +0,645] | +138 % ; +15,6 %/an | −13,5 % | 1,16 | — | — | — | — |
| exclusion > P80 | +0,310 [+0,049 ; +0,571] | +113 % ; +13,4 %/an | −15,9 % | 0,84 | −0,059 [−0,117 ; −0,009] | −2,2 [−7,3 ; +1,7] ; 28 % | −0,32 [−0,74 ; +0,06] ; 8 % | −4,1 pt (0,297 %) |
| exclusion > P85 | +0,238 [−0,005 ; +0,494] | +80 % ; +10,3 %/an | −17,5 % | 0,59 | −0,131 [−0,213 ; −0,052] | −3,6 [−12,3 ; +1,8] ; 13 % | −0,58 [−1,13 ; −0,05] ; 1 % | −8,4 pt (0,329 %) |
| exclusion > P90 | +0,219 [−0,011 ; +0,455] | +76 % ; +9,8 %/an | −17,7 % | 0,56 | −0,150 [−0,259 ; −0,044] | −3,9 [−15,1 ; +4,3] ; 20 % | −0,62 [−1,34 ; +0,04] ; 4 % | −9,0 pt (0,332 %) |

**C — exclusion de nis_z_100 (centile de l'atlas), 10 bps**

| Configuration | Espérance ATR [IC] | PnL ; annualisé | MDD | Calmar | Écart d'espérance à RE-1 [IC] | Écart de MDD (points) ; chemins meilleurs | Écart de Calmar ; chemins meilleurs | À MDD égal face à RE-1 |
|---|---|---|---|---|---|---|---|---|
| exclusion > P70 | +0,212 [−0,070 ; +0,498] | +58 % ; +8,0 %/an | −20,0 % | 0,40 | −0,021 [−0,086 ; +0,045] | −3,8 [−6,5 ; +4,9] ; 50 % | −0,20 [−0,40 ; +0,20] ; 24 % | −3,1 pt (0,319 %) |
| exclusion > P75 (RE-1) | +0,233 [−0,041 ; +0,511] | +72 % ; +9,5 %/an | −15,9 % | 0,60 | — | — | — | — |
| exclusion > P80 | +0,176 [−0,086 ; +0,443] | +52 % ; +7,2 %/an | −18,0 % | 0,40 | −0,057 [−0,116 ; −0,008] | −1,8 [−9,3 ; +1,4] ; 20 % | −0,20 [−0,51 ; +0,01] ; 4 % | −3,2 pt (0,285 %) |
| exclusion > P85 | +0,105 [−0,141 ; +0,363] | +27 % ; +4,0 %/an | −20,1 % | 0,20 | −0,128 [−0,210 ; −0,049] | −3,7 [−17,5 ; +1,2] ; 7 % | −0,41 [−0,87 ; −0,05] ; 0 % | −7,1 pt (0,320 %) |
| exclusion > P90 | +0,087 [−0,145 ; +0,326] | +21 % ; +3,3 %/an | −20,7 % | 0,16 | −0,146 [−0,257 ; −0,041] | −4,2 [−20,7 ; +3,3] ; 12 % | −0,45 [−1,04 ; −0,03] ; 1 % | −8,0 pt (0,331 %) |

## E. Mécanismes

**A — effet du stop à l'extremum par bande de retracement.** Trades de RE-1 (mêmes entrées) joués sans stop puis tous avec SL-B 0 ; effet par trade du stop (ATR, indépendant des frais) [IC] ; espérances nettes à 5 bps. La grille A déplace la frontière à travers ces bandes : 0,75 et 0,80 ajoutent le stop aux bandes [0,75 ; 0,85[, 0,90 et 0,95 le retirent aux bandes [0,85 ; 0,95[.

| Retracement | Trades | Régime dans RE-1 | Sans stop | SL-B 0 | Effet du stop [IC] | Stoppés (SL-B 0) |
|---|---|---|---|---|---|---|
| [0,50 ; 0,75[ | 390 | sans stop | +0,220 | +0,069 | −0,151 [−0,485 ; +0,202] | 66 % |
| [0,75 ; 0,80[ | 106 | sans stop | +1,027 | +0,448 | −0,579 [−1,147 ; −0,026] | 53 % |
| [0,80 ; 0,85[ | 77 | sans stop | +0,887 | +0,357 | −0,530 [−1,274 ; +0,129] | 56 % |
| [0,85 ; 0,90[ | 87 | SL-B 0 | −0,101 | −0,376 | −0,275 [−0,815 ; +0,283] | 55 % |
| [0,90 ; 0,95[ | 103 | SL-B 0 | +0,448 | +0,390 | −0,058 [−0,807 ; +0,661] | 52 % |
| [0,95 ; ∞[ | 317 | SL-B 0 | +0,258 | +0,403 | +0,144 [−0,148 ; +0,447] | 49 % |

**A et B — trades touchés.** A : trades changés de sous-famille ; B : trades de F3. Effet apparié sur ces trades et sur l'ensemble des trades de RE-1 (ATR, indépendant des frais).

| Configuration | Trades touchés | Effet sur les trades touchés [IC] | Effet par trade de RE-1 [IC] | Stoppés parmi F3 |
|---|---|---|---|---|
| frontière 0,75 | 183 | −0,558 [−0,920 ; −0,180] | −0,095 [−0,157 ; −0,030] | 52 % |
| frontière 0,80 | 77 | −0,530 [−1,274 ; +0,129] | −0,038 [−0,091 ; +0,009] | 51 % |
| frontière 0,90 | 87 | +0,275 [−0,283 ; +0,815] | +0,022 [−0,022 ; +0,068] | 50 % |
| frontière 0,95 | 190 | +0,157 [−0,298 ; +0,614] | +0,028 [−0,052 ; +0,108] | 49 % |
| δ = −0,25 ATR | 507 | −0,019 [−0,107 ; +0,056] | −0,009 [−0,050 ; +0,026] | 55 % |
| δ = +0,25 ATR | 507 | −0,030 [−0,076 ; +0,029] | −0,014 [−0,036 ; +0,014] | 46 % |
| δ = +0,50 ATR | 507 | −0,077 [−0,143 ; −0,001] | −0,036 [−0,066 ; −0,000] | 44 % |

**C — décomposition contre RE-1.** Retirés : trades de RE-1 dont le signal est exclu ; perdus : trades de RE-1 dont le signal est gardé mais tombe pendant un trade nouveau ; nouveaux : signaux que seule la variante admet ; libérés : signaux gardés par les deux que RE-1 ignorait (position occupée). n ; espérance nette par trade (ATR).

| Configuration | Frais | Retirés | Perdus par chaîne | Nouveaux signaux | Libérés par chaîne | Trades ; espérance : RE-1 → variante |
|---|---|---|---|---|---|---|
| exclusion > P70 | 5 bps | 72 ; +0,641 | 3 ; −2,788 | 0 ; — | 18 ; −0,146 | 1 080 → 1 023 ; +0,369 → +0,350 |
| exclusion > P70 | 10 bps | 72 ; +0,533 | 3 ; −2,858 | 0 ; — | 18 ; −0,263 | 1 080 → 1 023 ; +0,233 → +0,212 |
| exclusion > P80 | 5 bps | 0 ; — | 17 ; +1,479 | 72 ; −0,309 | 4 ; +0,585 | 1 080 → 1 139 ; +0,369 → +0,310 |
| exclusion > P80 | 10 bps | 0 ; — | 17 ; +1,356 | 72 ; −0,416 | 4 ; +0,425 | 1 080 → 1 139 ; +0,233 → +0,176 |
| exclusion > P85 | 5 bps | 0 ; — | 33 ; +1,236 | 138 ; −0,527 | 7 ; −0,144 | 1 080 → 1 192 ; +0,369 → +0,238 |
| exclusion > P85 | 10 bps | 0 ; — | 33 ; +1,112 | 138 ; −0,635 | 7 ; −0,298 | 1 080 → 1 192 ; +0,233 → +0,105 |
| exclusion > P90 | 5 bps | 0 ; — | 42 ; +1,290 | 206 ; −0,289 | 9 ; −1,102 | 1 080 → 1 253 ; +0,369 → +0,219 |
| exclusion > P90 | 10 bps | 0 ; — | 42 ; +1,174 | 206 ; −0,396 | 9 ; −1,245 | 1 080 → 1 253 ; +0,233 → +0,087 |

**C — chaque signal joué seul, par bande de nis_z_100.** Signaux de R2 avant l'exclusion, enveloppe de RE-1 (H26, F2b sans stop, F3 SL-B 0), sans sélection séquentielle : trades qui se chevauchent, lecture par signal. Espérance nette en ATR [IC 95 % par grappes mensuelles].

| Bande (atlas) | Seuils nis_z_100 | Signaux | Pris par RE-1 | Esp. 5 bps [IC] | Esp. 10 bps | Médiane 5 bps | Gagnants | P90 | Part F3 |
|---|---|---|---|---|---|---|---|---|---|
| ≤ P70 | ]−∞ ; 0,919] | 1 358 | 1 008 | +0,166 [−0,052 ; +0,387] | +0,023 | −0,586 | 42 % | +5,08 | 47 % |
| P70–P75 | ]0,919 ; 1,225] | 94 | 72 | +0,529 [−0,267 ; +1,342] | +0,424 | −0,702 | 44 % | +6,39 | 74 % |
| P75–P80 | ]1,225 ; 1,599] | 87 | 0 | −0,300 [−0,792 ; +0,200] | −0,408 | −0,588 | 45 % | +3,16 | 74 % |
| P80–P85 | ]1,599 ; 2,057] | 82 | 0 | −0,744 [−1,514 ; +0,124] | −0,849 | −1,936 | 29 % | +3,50 | 85 % |
| P85–P90 | ]2,057 ; 2,749] | 84 | 0 | +0,223 [−0,656 ; +1,205] | +0,117 | −0,411 | 48 % | +4,68 | 95 % |
| > P90 | ]2,749 ; +∞] | 169 | 0 | −0,405 [−0,930 ; +0,166] | −0,492 | −1,468 | 38 % | +4,60 | 96 % |

## F. Stabilité annuelle (H = 26, 5 bps)

Cellule : espérance nette par trade en ATR (trades) ; dernière colonne : PnL composé par année à 0,25 % par ATR.

| Configuration | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 | PnL par année |
|---|---|---|---|---|---|---|---|
| frontière 0,75 | +0,48 (189) | −0,14 (192) | +0,13 (173) | +0,36 (188) | +0,32 (171) | +0,53 (167) | +24 % ; −7 % ; +5 % ; +17 % ; +14 % ; +17 % |
| frontière 0,80 | +0,54 (189) | −0,05 (192) | +0,21 (173) | +0,44 (188) | +0,30 (171) | +0,56 (167) | +27 % ; −3 % ; +8 % ; +22 % ; +13 % ; +19 % |
| frontière 0,85 (RE-1) | +0,51 (189) | +0,02 (192) | +0,30 (173) | +0,50 (188) | +0,33 (171) | +0,55 (167) | +25 % ; +0 % ; +12 % ; +25 % ; +15 % ; +18 % |
| frontière 0,90 | +0,57 (189) | +0,02 (192) | +0,32 (173) | +0,51 (188) | +0,30 (171) | +0,66 (167) | +28 % ; −0 % ; +12 % ; +25 % ; +13 % ; +21 % |
| frontière 0,95 | +0,58 (189) | +0,04 (192) | +0,39 (173) | +0,38 (188) | +0,22 (171) | +0,80 (167) | +29 % ; +1 % ; +15 % ; +19 % ; +9 % ; +29 % |
| δ = −0,25 ATR | +0,50 (189) | +0,06 (192) | +0,29 (173) | +0,44 (188) | +0,37 (171) | +0,50 (167) | +25 % ; +2 % ; +11 % ; +23 % ; +16 % ; +17 % |
| δ = 0 ATR (RE-1) | +0,51 (189) | +0,02 (192) | +0,30 (173) | +0,50 (188) | +0,33 (171) | +0,55 (167) | +25 % ; +0 % ; +12 % ; +25 % ; +15 % ; +18 % |
| δ = +0,25 ATR | +0,53 (189) | +0,01 (192) | +0,28 (173) | +0,48 (188) | +0,32 (171) | +0,53 (167) | +26 % ; −1 % ; +11 % ; +25 % ; +14 % ; +17 % |
| δ = +0,50 ATR | +0,49 (189) | −0,04 (192) | +0,24 (173) | +0,50 (188) | +0,27 (171) | +0,56 (167) | +24 % ; −3 % ; +9 % ; +26 % ; +12 % ; +19 % |
| exclusion > P70 | +0,56 (176) | −0,07 (181) | +0,31 (164) | +0,42 (182) | +0,29 (163) | +0,63 (157) | +26 % ; −4 % ; +11 % ; +20 % ; +12 % ; +20 % |
| exclusion > P75 (RE-1) | +0,51 (189) | +0,02 (192) | +0,30 (173) | +0,50 (188) | +0,33 (171) | +0,55 (167) | +25 % ; +0 % ; +12 % ; +25 % ; +15 % ; +18 % |
| exclusion > P80 | +0,41 (201) | +0,06 (203) | +0,31 (179) | +0,44 (197) | +0,26 (180) | +0,39 (179) | +21 % ; +2 % ; +12 % ; +23 % ; +12 % ; +12 % |
| exclusion > P85 | +0,30 (209) | −0,06 (214) | +0,33 (188) | +0,31 (202) | +0,31 (191) | +0,26 (188) | +15 % ; −4 % ; +14 % ; +17 % ; +15 % ; +6 % |
| exclusion > P90 | +0,29 (216) | −0,06 (223) | +0,19 (199) | +0,26 (216) | +0,37 (199) | +0,29 (200) | +15 % ; −4 % ; +7 % ; +15 % ; +19 % ; +8 % |

## G. Lecture fixée avant le calcul

Voisins immédiats de RE-1. (d1) écart d'espérance ≤ −20 % de celle de RE-1, IC entièrement négatif ; (d2) espérance ou Calmar < moitié de RE-1 ; (d3) MDD valorisé plus profond que 1,5 fois celui de RE-1. Plateau : aucun voisin en dégradation nette ; falaise : un ; crête : les deux. Rang : place de RE-1 dans sa grille (1 = meilleur).

| Grille | Frais | Voisin | (d1) Écart d'espérance [IC] | (d2) Esp. ; Calmar : voisin / RE-1 | (d3) MDD : voisin / RE-1 | Dégradation nette | Meilleur (IC > 0) | Verdict ; rang de RE-1 |
|---|---|---|---|---|---|---|---|---|
| A | 5 bps | 0,80 | −0,038 [−0,091 ; +0,009] ; seuil −0,074 | +0,331 / +0,369 ; 0,99 / 1,16 | −14,1 % / −13,5 % | non | non | plateau ; rang 3/5 (esp.), 3/5 (Calmar) |
| A | 5 bps | 0,90 | +0,022 [−0,022 ; +0,068] ; seuil −0,074 | +0,391 / +0,369 ; 1,21 / 1,16 | −13,4 % / −13,5 % | non | non | plateau ; rang 3/5 (esp.), 3/5 (Calmar) |
| B | 5 bps | −0,25 | −0,009 [−0,050 ; +0,026] ; seuil −0,074 | +0,360 / +0,369 ; 1,19 / 1,16 | −13,0 % / −13,5 % | non | non | plateau ; rang 1/4 (esp.), 2/4 (Calmar) |
| B | 5 bps | +0,25 | −0,014 [−0,036 ; +0,014] ; seuil −0,074 | +0,355 / +0,369 ; 1,07 / 1,16 | −14,0 % / −13,5 % | non | non | plateau ; rang 1/4 (esp.), 2/4 (Calmar) |
| C | 5 bps | P70 | −0,019 [−0,084 ; +0,047] ; seuil −0,074 | +0,350 / +0,369 ; 0,77 / 1,16 | −17,8 % / −13,5 % | non | non | plateau ; rang 1/5 (esp.), 1/5 (Calmar) |
| C | 5 bps | P80 | −0,059 [−0,117 ; −0,009] ; seuil −0,074 | +0,310 / +0,369 ; 0,84 / 1,16 | −15,9 % / −13,5 % | non | non | plateau ; rang 1/5 (esp.), 1/5 (Calmar) |
| A | 10 bps | 0,80 | −0,038 [−0,091 ; +0,009] ; seuil −0,047 | +0,195 / +0,233 ; 0,48 / 0,60 | −16,6 % / −15,9 % | non | non | plateau ; rang 3/5 (esp.), 3/5 (Calmar) |
| A | 10 bps | 0,90 | +0,022 [−0,022 ; +0,068] ; seuil −0,047 | +0,255 / +0,233 ; 0,64 / 0,60 | −15,8 % / −15,9 % | non | non | plateau ; rang 3/5 (esp.), 3/5 (Calmar) |
| B | 10 bps | −0,25 | −0,009 [−0,050 ; +0,026] ; seuil −0,047 | +0,224 / +0,233 ; 0,63 / 0,60 | −15,1 % / −15,9 % | non | non | plateau ; rang 1/4 (esp.), 2/4 (Calmar) |
| B | 10 bps | +0,25 | −0,014 [−0,036 ; +0,014] ; seuil −0,047 | +0,219 / +0,233 ; 0,54 / 0,60 | −16,4 % / −15,9 % | non | non | plateau ; rang 1/4 (esp.), 2/4 (Calmar) |
| C | 10 bps | P70 | −0,021 [−0,086 ; +0,045] ; seuil −0,047 | +0,212 / +0,233 ; 0,40 / 0,60 | −20,0 % / −15,9 % | non | non | falaise ; rang 1/5 (esp.), 1/5 (Calmar) |
| C | 10 bps | P80 | −0,057 [−0,116 ; −0,008] ; seuil −0,047 ✗ | +0,176 / +0,233 ; 0,40 / 0,60 | −18,0 % / −15,9 % | oui | non | falaise ; rang 1/5 (esp.), 1/5 (Calmar) |
