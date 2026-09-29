# EXP-C03 — Break-even différé sur RE-1 : analyse approfondie (alpha contre gestion du risque)

- **Date :** 2026-09-29
- **Étape :** C Enveloppe, relecture de C03 par le porteur (analyse de Gemini intégrée).
  - Aucune règle nouvelle, sauf un stress d'exécution demandé : le glissement du seul break-even.
  - RE-1 n'est pas modifié.
- **Référence (inchangée) :** RE-1, soit :
  - H = 26, cooldown, pyramiding 0 ;
  - F2b sans stop, F3 SL-B à l'extremum ;
  - vetos R1, R3 et `nis_z_100` Q4 ; x1 retourné comme prérequis d'entrée.
- **Lectures :**
  - 5 et 10 bps, toujours présentés séparément ;
  - capital à 0,25 % par ATR14(t), 1x en référence ;
  - H = 24 et 28 comme contrôles de plateau.
- **Hold-out :** BTC 2026, ETH et XRP restent scellés, non lus.
- **Code et analyse séparés :**
  - code : commit 547af84, paramètre `be_slippage_bps` de `breakeven_trades` (0 par défaut) et son test ;
  - analyse : `run_C03_approfondi.py`, qui relit la grille de C03 sans la modifier.

## 0. Cadrage

- **QUESTION :** deux questions à ne pas confondre.
  - **A (alpha).** Le break-even améliore-t-il E[ATR] par trade ?
  - **B (gestion du risque).** Un break-even peut-il garder une espérance statistiquement comparable tout en réduisant de façon robuste le MDD, en améliorant le Calmar ou la robustesse aux frais ?
  - Trois points spécifiques : V3 à m = 2 (drawdown, glissement du break-even), l'année 2022, et l'asymétrie F2b / F3 (V2 à m = 2).
- **PERTINENCE POUR LE FILTRE AKF :** RE-1 est convexe. Ses 10 % meilleurs trades apportent 0,92 ATR par trade, pour une espérance totale de 0,369. Toute règle de sortie doit donc être jugée séparément sur sa queue droite et sur son risque.
- **CE QUE LE PROTOCOLE MESURE RÉELLEMENT :**
  - l'effet apparié BE − RE-1 sur les mêmes 1 080 entrées : effet causal du mécanisme ;
  - la performance absolue de chaque variante : sa viabilité ;
  - le risque de chemin sur 2 000 chemins où les mois d'entrée sont tirés avec remise ;
  - un RE-1 réduit en taille jusqu'au même drawdown ;
  - le glissement du seul break-even ;
  - le diagnostic trade par trade des sorties au break-even.
- **CE QU'IL NE PERMET PAS DE CONCLURE :**
  - une validation hors échantillon ;
  - le choix d'un m (sélection a posteriori exclue) ;
  - l'effet d'un glissement sur tous les stops : il n'est appliqué qu'au break-even, sur consigne ;
  - une théorie du régime de 2022 : une seule année, 46 sorties au break-even.

## A. Validation technique

- **Tests :**
  - 195 réussis, 2 ignorés ;
  - 8 tests du break-even : activation, niveau net, gap, priorité du stop initial, fenêtre, référence barre par barre, équivalence sans break-even, réouverture, troncature, plus le glissement, dont le test est nouveau.
- **Contrôles bloquants passés :**
  - RE-1 identique à C02bis trade par trade (H24, 26, 28, deux lectures) ;
  - un seuil infini redonne RE-1 ;
  - effet apparié exactement nul hors des sorties au break-even ;
  - glissement nul identique aux courses de C03 ;
  - effet de V3 = effet de V1 + effet de V2, trade par trade, aux trois horizons ;
  - mécanique de V3 à m = 2 identique à `resultats_C03.csv`.
- **Causalité :**
  - le seuil m · ATR14(t) et le niveau open[t + 1] ± 5 bps sont connus à l'entrée ;
  - l'activation se lit sur les barres t + 1 … t + H − 1, et le break-even ne s'applique qu'à partir de b + 1 ;
  - sur la barre d'activation, le stop initial prime, donc aucune sortie au break-even n'est supposée dans la barre même ;
  - un gap est exécuté à l'ouverture ;
  - aucun `shift(-1)` dans `src/envelope` ni dans `experiments/C03` ; test de troncature réussi.
- **Chiffres de la relecture :** tous confirmés dans les résultats bruts, aux arrondis près (annexe A). Une précision : les parts de 89 % (H26) et 92 % (H24) portent sur le MDD aux sorties des chemins réordonnés, alors que −13,5 → −11,7 % et les autres valeurs sont des MDD valorisés du chemin réel.

## B. Résultat principal : effet apparié BE − RE-1 (question A)

Effet par trade sur les 1 080 entrées, en ATR, avec IC 95 % (annexe B pour tous les seuils).

| Seuil | V1 (F3) | V2 (F2b) | V3 (les deux) |
|---|---|---|---|
| m = 1 | −0,036 [−0,143 ; +0,063] | −0,121 [−0,249 ; +0,001] | −0,157 [−0,318 ; +0,007] |
| m = 2 | −0,015 [−0,089 ; +0,047] | −0,004 [−0,082 ; +0,089] | −0,018 [−0,131 ; +0,105] |
| m = 4 | +0,004 [−0,026 ; +0,033] | +0,026 [−0,029 ; +0,103] | +0,030 [−0,035 ; +0,118] |

- **Aucun effet significativement positif, à aucun seuil ni horizon.**
- **Effets significativement négatifs :** V2 à m = 1 à H24 et H28, V3 à m = 1 à H24.
- **Pour m ≥ 2**, l'effet reste entre −0,021 et +0,030 ATR aux trois horizons.
- **Par sous-famille à m = 2 :**
  - F2b : −0,007 ATR par trade de F2b [−0,156 ; +0,167] ;
  - F3 : −0,031 [−0,192 ; +0,101] ;
  - les effets s'additionnent exactement : V3 = V1 + V2.
- **[OBS] Question A : aucun alpha.** Le break-even ne crée pas d'espérance.

## C. Queue droite : part des gros gagnants amputée

RE-1 compte 209 trades à ≥ +3 ATR nets et 108 dans son décile supérieur (annexe C).

| V3 | m = 1 | 1,5 | 2 | 2,5 | 3 | 4 |
|---|---|---|---|---|---|---|
| Gagnants ≥ +3 ATR coupés | 39,2 % | 24,4 % | 17,2 % | 12,4 % | 9,1 % | 5,3 % |
| Part de leur contribution perdue | 39,3 % | 23,9 % | 15,7 % | 11,4 % | 7,9 % | 4,3 % |
| Décile supérieur coupé | 38,9 % | 22,2 % | 13,9 % | 10,2 % | 7,4 % | 4,6 % |

- V1 et V2 se partagent chacun à peu près la moitié de ces parts.
- **À m = 1, le break-even ampute près de 40 % de la queue droite.** C'est cette amputation qui rend l'effet négatif.
- **À m = 2, il coupe encore 1 gros gagnant sur 6.**

## D. Risque : V3 à m = 2 contre RE-1

**Trades concernés (H26) :**
- 565 break-even déclenchés, 268 exécutés (dont 13 en gap) ;
- 147 trades sauvés et 121 coupés ;
- 36 des 209 gagnants à ≥ +3 ATR sont coupés, soit 15,7 % de leur contribution.

**Chemin réel, MDD valorisé ; Calmar :**

| Lecture | H = 24 | H = 26 | H = 28 |
|---|---|---|---|
| 5 bps : RE-1 | −14,2 % ; 0,94 | −13,5 % ; 1,16 | −16,2 % ; 0,92 |
| 5 bps : V3 m = 2 | −11,2 % ; 1,20 | −11,7 % ; 1,25 | −12,5 % ; 1,12 |
| 10 bps : RE-1 | −16,7 % ; 0,43 | −15,9 % ; 0,60 | −18,4 % ; 0,48 |
| 10 bps : V3 m = 2 | −15,5 % ; 0,48 | −13,4 % ; 0,64 | −14,2 % ; 0,57 |

**[OBS] Constats :**
- **Sur le chemin réel**, V3 fait mieux dans les 6 lectures, en MDD comme en Calmar.
- **Sur les 2 000 chemins réordonnés (5 bps) :**
  - le MDD est moins profond dans 92 % (H24), 89 % (H26) et 82 % (H28) des chemins, mais la plage P2,5-P97,5 de l'écart contient 0 partout : la baisse n'est pas démontrée à 95 % ;
  - le Calmar n'est meilleur que dans 82 %, 69 % et 65 % des chemins.
- **Distribution des MDD aux sorties (H26) :**
  - RE-1 : médiane −16,1 % [P5 −26,8 ; P95 −10,8] ;
  - V3 : médiane −13,0 % [−21,4 ; −8,6].
  - Le chemin réel (−12,9 % et −11,2 %) est favorable aux deux.
- **Drawdowns moins profonds mais plus longs.** Le pire drawdown de V3 est le même épisode que celui de RE-1 (pic du 24 avril 2021), plus court en profondeur (−11,7 % contre −13,5 %). Mais il est regagné en juillet 2022, au lieu de mai 2022 : 459 jours sous le pic contre 390. À 10 bps : 738 jours, contre 459 pour un RE-1 réduit au même MDD.
- **À drawdown égal, RE-1 réduit en taille fait presque aussi bien.**
  - RE-1 à 0,211 % par ATR a le même MDD (−11,7 %) et fait +13,5 % par an, contre +14,5 % pour V3 : +1,0 point en faveur de V3 à 5 bps.
  - À 10 bps, l'écart tombe à +0,3 point.

## E. Robustesse aux frais : viabilité absolue, 5 et 10 bps séparés

H26, 0,25 % par ATR. P(E > 0) : part des tirages bootstrap où l'espérance en ATR est positive.

**5 bps**

| Configuration | Espérance ATR [IC] | P(E > 0) | Écart type par trade ; erreur type | MDD | Calmar |
|---|---|---|---|---|---|
| RE-1 | +0,369 [+0,098 ; +0,645] | 99,9 % | 4,19 ; 0,137 | −13,5 % | 1,16 |
| V2 m = 2 | +0,365 [+0,134 ; +0,602] | 100,0 % | 3,93 ; 0,120 | −12,9 % | 1,19 |
| V3 m = 2 | +0,350 [+0,142 ; +0,570] | 100,0 % | 3,78 ; 0,111 | −11,7 % | 1,25 |
| V3 m = 4 | +0,398 [+0,151 ; +0,649] | 100,0 % | 4,01 ; 0,127 | −14,5 % | 1,13 |

**10 bps**

| Configuration | Espérance ATR [IC] | P(E > 0) | Écart type par trade ; erreur type | MDD | Calmar |
|---|---|---|---|---|---|
| RE-1 | +0,233 [−0,041 ; +0,511] | 95,2 % | 4,19 ; 0,138 | −15,9 % | 0,60 |
| V2 m = 2 | +0,229 [−0,007 ; +0,469] | 97,2 % | 3,93 ; 0,121 | −15,4 % | 0,60 |
| V3 m = 2 | +0,215 [+0,005 ; +0,437] | 97,7 % | 3,77 ; 0,112 | −13,4 % | 0,64 |
| V2 m = 4 | +0,259 [+0,003 ; +0,522] | 97,7 % | 4,05 ; 0,130 | −17,3 % | 0,59 |
| V3 m = 4 | +0,263 [+0,014 ; +0,514] | 98,1 % | 4,01 ; 0,128 | −16,9 % | 0,61 |

**[OBS] Le passage au-dessus de 0 à 10 bps vient du resserrement de l'IC, pas d'un gain.**
- Chez V3 à m = 2, l'espérance baisse (+0,233 → +0,215), mais l'écart type par trade aussi (4,19 → 3,77) : l'erreur type passe de 0,138 à 0,112.
- La probabilité d'une espérance positive gagne 2 à 3 points (95,2 % → 97,2-98,1 %).
- Ce passage n'est pas robuste :
  - il ne tient qu'à H26 (1 horizon sur 3, pour V3 à m = 2, 3 et 4 et pour V2 à m = 4) ;
  - il disparaît avec 5 bps de glissement du break-even (V3 à m = 2 : +0,179 [−0,035 ; +0,403]) ;
  - en bps, aucun IC n'exclut 0 à 10 bps.
- V2 et V3 à m = 4 améliorent l'IC sans améliorer le risque (MDD −17,3 et −16,9 % contre −15,9 %).

## F. Stress d'exécution : glissement du seul break-even, V3 à m = 2

Le break-even déclenché reste à open[t + 1] ± 5 bps ; seul son prix d'exécution est dégradé. Nombre de break-even : 565 déclenchés et 268 exécutés, quel que soit le glissement.

| H26 | Glissement 0 | 5 bps | 10 bps | RE-1 |
|---|---|---|---|---|
| **5 bps :** espérance ATR | +0,350 | +0,314 | +0,278 | +0,369 |
| Effet apparié BE − RE-1 [IC] | −0,018 [−0,131 ; +0,105] | −0,054 [−0,168 ; +0,066] | −0,090 [−0,204 ; +0,027] | — |
| PnL ; MDD ; Calmar | +126 % ; −11,7 % ; 1,25 | +108 % ; −11,8 % ; 1,10 | +91 % ; −12,0 % ; 0,95 | +138 % ; −13,5 % ; 1,16 |
| Chemins : MDD meilleur ; Calmar meilleur | 89 % ; 69 % | 82 % ; 48 % | 73 % ; 26 % | — |
| PnL annualisé, écart à RE-1 réduit au même MDD | +1,0 pt | −0,8 pt | −2,7 pt | — |
| **10 bps :** espérance ATR [IC] | +0,215 [+0,005 ; +0,437] | +0,179 [−0,035 ; +0,403] | +0,142 [−0,073 ; +0,370] | +0,233 [−0,041 ; +0,511] |
| MDD ; Calmar | −13,4 % ; 0,64 | −14,7 % ; 0,48 | −16,1 % ; 0,34 | −15,9 % ; 0,60 |
| PnL annualisé, écart à RE-1 réduit au même MDD | +0,3 pt | −1,9 pt | −4,0 pt | — |

**[OBS] Constats :**
- **Le MDD reste plus bas à 5 bps de frais**, même avec 10 bps de glissement, à tous les horizons : la troncature des perdants est mécanique.
- **À 10 bps de frais, il ne résiste pas :** il devient plus profond que celui de RE-1 à H24 dès 5 bps de glissement (−16,8 contre −16,7 %), puis à H24 et H26 avec 10 bps.
- **L'avantage d'efficience disparaît dès 5 bps de glissement :**
  - Calmar 1,10 contre 1,16 à H26 ;
  - Calmar meilleur dans 48 % des chemins seulement ;
  - V3 devient moins efficace qu'un RE-1 simplement réduit en taille (−0,8 point par an à MDD égal).

**Limite du stress :** conformément à la consigne, seul le break-even glisse ; les stops SL-B de RE-1 n'en subissent aucun. V3 exécute 476 ordres stop (208 initiaux et 268 break-even), contre 257 pour RE-1. Un glissement appliqué à tous les stops réduirait donc d'environ un cinquième la pénalité relative de V3 (219 ordres de plus au lieu de 268).

## G. Diagnostic de 2022

**Effet par année (V3 à m = 2, H26), en ATR :**

| Année | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 |
|---|---|---|---|---|---|---|
| Effet apparié | +0,047 | 0,000 | −0,184 | +0,016 | +0,104 | −0,105 |
| IC 95 % | [−0,13 ; +0,24] | [−0,18 ; +0,19] | [−0,54 ; +0,13] | [−0,37 ; +0,50] | [−0,12 ; +0,30] | [−0,37 ; +0,14] |
| Sans les 2 sorties au BE les plus coûteuses de l'année | +0,104 | +0,054 | **+0,006** | +0,123 | +0,194 | −0,016 |

**[OBS] Constats :**
- **2022 n'est pas statistiquement distincte.** Son IC [−0,54 ; +0,13] contient 0 et l'effet global (−0,018).
- **Tout le déficit de 2022 tient à deux trades.** Ce sont les deux plus gros coûts de tout l'échantillon, deux F3 :
  - 2022-03-27, Long : +18,63 ATR dans RE-1 ;
  - 2022-09-06, Short : +14,26 ATR dans RE-1.
  - Chacun n'a reculé que de 0,12 et 0,44 ATR sous l'entrée après la sortie au break-even, puis l'expansion a suivi (volatilité réalisée égale à 2,4 et 1,7 fois l'ATR14).
  - Sans ces deux trades, 2022 fait +0,006.
- **Chaque année a ce type de coût.** Les deux plus gros coûts d'une année vont de 4 à 19 ATR ; sans eux, les années sont entre −0,016 et +0,194.
- **En 2022, les 46 sorties au break-even ressemblent aux 222 des autres années :**
  - même rapport sauvés / coupés (25/21 contre 122/100) ;
  - même MFE avant le break-even (médiane 2,78 contre 2,86 ATR) ;
  - même durée (14,5 contre 13 barres) ;
  - même volatilité réalisée rapportée à l'ATR (0,81 contre 0,80).
- **Ce qui diffère en 2022 :**
  - ATR plus élevé (50 contre 42 bps) ;
  - plus de sorties en gap (11 % contre 4 %) ;
  - des gagnants coupés plus grands (+3,20 contre +2,36 ATR) et des perdants sauvés plus petits (−1,68 contre −2,07).
- **Ce que les variables permettent de caractériser :**
  - *Échecs du breakout (sauvés).* Le recul après le break-even est profond (médiane 2,5 ATR sous l'entrée) ; pour F3, il finit souvent au stop SL-B dans RE-1.
  - *Reprises après retest (coupés).* Le recul est peu profond (médiane 0,68 ATR, 0,39 en 2022), puis la MFE après le break-even atteint 3,3 ATR en médiane.
- **[HYP] Une exposition structurelle, pas une faiblesse propre à 2022.** Le break-even, à l'entrée + 5 bps, se trouve dans la zone de retest des breakouts. Son effet annuel dépend de sa probabilité de couper l'un des rares gagnants extrêmes de RE-1. 2022 en a eu deux, et les données ne permettent pas d'aller plus loin : une année, 46 sorties.

## H. Asymétrie F2b / F3 : V2 à m = 2 (break-even sur F2b seul) contre RE-1

| H26, par sous-famille | Sauvés : n ; RE-1 moyen | Coupés : n ; RE-1 moyen | Effet par trade de la sous-famille [IC] |
|---|---|---|---|
| F2b (V2) | 73 ; −2,30 ATR | 70 ; +2,34 ATR | −0,007 [−0,156 ; +0,167] |
| F3 (V1) | 74 ; −1,72 ATR | 51 ; +2,73 ATR | −0,031 [−0,192 ; +0,101] |

**[OBS] Mécanique : l'hypothèse du porteur est confirmée.**
- Sur F3, le SL-B plafonne déjà les pertes : les perdants sauvés ne perdaient que −1,72 ATR, contre −2,30 pour F2b. Le break-even n'a donc presque rien à sauver sur F3, et il coupe des gagnants plus grands (+2,73 contre +2,34).
- Les dix plus grands gains du break-even sont tous des F2b, dont +30,4 ATR le 2023-01-11. Les deux plus grands coûts sont des F3.

**[OBS] Mais V2 n'apporte rien de mesurable :**
- Espérance : effet −0,004 [−0,082 ; +0,089].
- MDD à 5 bps : −13,8 / −12,9 / −12,7 % contre −14,2 / −13,5 / −16,2 % pour RE-1.
- MDD à 10 bps : −16,3 / −15,4 / −14,9 % contre −16,7 / −15,9 / −18,4 %.
- Calmar : 0,99 / 1,19 / 1,10 contre 0,94 / 1,16 / 0,92.
- Chemins : MDD meilleur dans 79 à 87 % des cas, Calmar dans 60 à 80 %.
- À MDD égal, V2 ne fait que +0,3 point par an (5 bps) et +0,1 point (10 bps) de plus qu'un RE-1 réduit en taille.

**[HYP]** Si un break-even devait être utilisé, ce serait sur l'enveloppe sans stop (F2b), où il agit comme une protection tardive de la queue gauche. Pour comparaison, le stop de catastrophe à 5 ATR sur F2b (RE-3, C02bis) coûtait 0,08 ATR par trade ; le break-even à m = 2 sur F2b coûte à peu près 0. C'est la protection la moins chère testée pour F2b, mais elle n'apporte aucun gain mesurable, et rien ne justifie de l'utiliser.

## I. Décision scientifique

**Règle de décision (fixée avant les tests F, G, H et le bootstrap du Calmar)**

1. **Critère primaire, alpha.** Le break-even n'entre dans le baseline que si son effet apparié sur E[ATR] est significativement positif (IC 95 %) à H26, et positif à H24 et H28. Il est écarté du baseline si cet effet est significativement négatif à un horizon, ou négatif aux trois : dans ce cas, l'amputation de la queue droite n'est pas compensée.
2. **Critère secondaire, gestion du risque.** Une variante devient une *variante candidate*, sans remplacer RE-1, si elle satisfait S1 et, en plus, soit S2 et S3, soit S4 :
   - **S1 :** son espérance est comparable, c'est-à-dire que l'IC de l'effet apparié contient 0 aux trois horizons ;
   - **S2 :** son MDD est plus bas dans toutes les lectures (trois horizons, 5 et 10 bps, glissement du break-even de 0, 5 et 10 bps), et la plage P2,5-P97,5 de l'écart sur les chemins réordonnés exclut 0 ;
   - **S3 :** son Calmar est meilleur dans les mêmes lectures, et démontré de la même façon sur les chemins réordonnés ;
   - **S4 :** l'IC de son espérance à 10 bps exclut 0 aux trois horizons et résiste au glissement.

L'équivalent en taille (RE-1 au même MDD) a été ajouté après lecture du stress de glissement. Il sert d'interprétation et n'entre pas dans la règle.

**Application**

| Critère | V3 m = 2 | V2 m = 2 | V1 m = 2 |
|---|---|---|---|
| Primaire : effet significativement positif | non | non | non |
| Primaire : écarté du baseline | oui (effet négatif aux trois horizons : −0,009 ; −0,018 ; −0,018) | oui (−0,004 ; −0,004 ; −0,021) | non (−0,004 ; −0,015 ; +0,003) |
| S1 : espérance comparable | oui | oui | oui |
| S2 : MDD robuste et démontré | **non** (meilleur dans 82 à 92 % des chemins, non démontré ; plus profond à 10 bps avec glissement) | **non** (79 à 87 %, non démontré) | **non** (plus profond à 10 bps à H24 et H26) |
| S3 : Calmar robuste et démontré | **non** (65 à 82 % des chemins ; plus bas que RE-1 dès 5 bps de glissement) | **non** (60 à 80 % ; égal à 10 bps, H26) | **non** |
| S4 : viabilité à 10 bps | **non** (IC > 0 à H26 seulement ; perdu avec 5 bps de glissement) | **non** (0 horizon sur 3) | **non** |

**[DECISION] Proposée : 1. Break-even rejeté, RE-1 conservé intact.**

- **Alpha :**
  - aucun seuil n'améliore l'espérance ;
  - m ≤ 1,5 ampute jusqu'à 40 % de la queue droite et dégrade l'espérance, significativement pour F2b ;
  - m ≥ 2 est neutre.
- **Gestion du risque :**
  - la baisse du drawdown de V3 à m = 2 est cohérente sur le chemin réel (6 lectures sur 6) et probable (8 à 9 chemins sur 10), mais pas démontrée ;
  - elle rallonge les périodes sous le pic (459 jours contre 390) ;
  - son gain d'efficience (+1 point par an à MDD égal) s'inverse dès 5 bps de glissement du break-even.
  - À exécution réaliste, un RE-1 simplement réduit en taille fait mieux, sans paramètre supplémentaire.
- **À ne pas retester sans élément nouveau :**
  - le break-even à l'entrée ;
  - la sélection a posteriori d'un m pour le risque.

  Le point faible identifié est la position du break-even dans la zone de retest. Un niveau différent serait une règle nouvelle, non proposée ici.
