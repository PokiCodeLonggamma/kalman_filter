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

---

# Annexes chiffrées (générées par `run_C03_approfondi.py`)

## Annexe A — Validation technique

| Contrôle | Résultat |
|---|---|
| Glissement nul | V1, V2 et V3 à m = 2, trois horizons : trades identiques aux courses de C03 |
| Additivité | effet apparié de V3 = effet de V1 + effet de V2, trade par trade, aux trois horizons (les sous-familles ne partagent aucun trade en lecture cooldown) |
| Mécanique | V3 m = 2 : trades activés, sortis au break-even, sauvés et coupés identiques à resultats_C03.csv |
| Contrôles de C03 | RE-1 = RE-1 de C02bis trade par trade (H24, 26, 28, deux lectures) ; seuil infini = RE-1 ; effet nul hors sorties au break-even (controles_C03.json) |

**Chiffres de la relecture, vérifiés dans les résultats bruts** (resultats_C03.csv et chemins réordonnés)

| Chiffre | Relecture | Mesuré |
|---|---|---|
| MDD valorisé RE-1 → V3 m = 2, H24, 5 bps | −14,2 → −11,2 % | −14,23 % → −11,24 % |
| MDD valorisé RE-1 → V3 m = 2, H26, 5 bps | −13,5 → −11,7 % | −13,47 % → −11,65 % |
| MDD valorisé RE-1 → V3 m = 2, H28, 5 bps | −16,2 → −12,5 % | −16,16 % → −12,55 % |
| Calmar RE-1 → V3 m = 2, H26, 5 bps | 1,16 → 1,25 | 1,155 → 1,246 |
| Calmar RE-1 → V3 m = 2, H24, 5 bps | 0,94 → 1,20 | 0,937 → 1,203 |
| Chemins où V3 m = 2 a un MDD moins profond, H26 | 89 % | 88,8 % (MDD aux sorties, 2 000 chemins) |
| Chemins où V3 m = 2 a un MDD moins profond, H24 | 92 % | 91,8 % (MDD aux sorties, 2 000 chemins) |
| V3 m = 1 : gagnants coupés ; dont ≥ +3 ATR | 273 ; 82 | 273 ; 82 |
| V3 m = 1 : coût des coupés ; gain des sauvés (ATR par trade, sur les 1 080 entrées) | −0,726 ; +0,569 | −0,726 ; +0,569 |
| V3 m = 2 : sauvés, gain ; coupés, coût ; effet [IC] | 147, +0,270 ; 121, −0,288 ; −0,018 [−0,131 ; +0,105] | 147, +0,270 ; 121, −0,288 ; −0,018 [−0,131 ; +0,105] |
| RE-1 à 10 bps : espérance ATR [IC] | +0,233 [−0,041 ; +0,511] | +0,233 [−0,041 ; +0,511] |

## Annexe B — Effet apparié BE − RE-1 à H = 26, global et par sous-famille (mêmes 1 080 entrées)

Global : ATR par trade sur toutes les entrées [IC 95 %]. Par sous-famille : ATR par trade de la sous-famille [IC 95 %] ; une variante n'agit que sur son périmètre (V1 : F3 ; V2 : F2b).

| Variante | Global | Sur les trades F2b (573) | Sur les trades F3 (507) |
|---|---|---|---|
| V1 — BE 1,0 ATR (F3) | −0,036 [−0,143 ; +0,063] | — (hors périmètre) | −0,077 [−0,307 ; +0,137] |
| V1 — BE 1,5 ATR (F3) | −0,023 [−0,111 ; +0,054] | — (hors périmètre) | −0,050 [−0,236 ; +0,114] |
| V1 — BE 2,0 ATR (F3) | −0,015 [−0,089 ; +0,047] | — (hors périmètre) | −0,031 [−0,192 ; +0,101] |
| V1 — BE 2,5 ATR (F3) | +0,002 [−0,064 ; +0,053] | — (hors périmètre) | +0,005 [−0,135 ; +0,114] |
| V1 — BE 3,0 ATR (F3) | −0,000 [−0,040 ; +0,038] | — (hors périmètre) | −0,000 [−0,085 ; +0,080] |
| V1 — BE 4,0 ATR (F3) | +0,004 [−0,026 ; +0,033] | — (hors périmètre) | +0,009 [−0,055 ; +0,070] |
| V2 — BE 1,0 ATR (F2b) | −0,121 [−0,249 ; +0,001] | −0,228 [−0,465 ; +0,002] | — (hors périmètre) |
| V2 — BE 1,5 ATR (F2b) | −0,042 [−0,139 ; +0,063] | −0,079 [−0,263 ; +0,117] | — (hors périmètre) |
| V2 — BE 2,0 ATR (F2b) | −0,004 [−0,082 ; +0,089] | −0,007 [−0,156 ; +0,167] | — (hors périmètre) |
| V2 — BE 2,5 ATR (F2b) | −0,014 [−0,091 ; +0,077] | −0,027 [−0,175 ; +0,144] | — (hors périmètre) |
| V2 — BE 3,0 ATR (F2b) | +0,009 [−0,061 ; +0,093] | +0,016 [−0,114 ; +0,175] | — (hors périmètre) |
| V2 — BE 4,0 ATR (F2b) | +0,026 [−0,029 ; +0,103] | +0,049 [−0,054 ; +0,191] | — (hors périmètre) |
| V3 — BE 1,0 ATR (F2b+F3) | −0,157 [−0,318 ; +0,007] | −0,228 [−0,465 ; +0,002] | −0,077 [−0,307 ; +0,137] |
| V3 — BE 1,5 ATR (F2b+F3) | −0,065 [−0,208 ; +0,075] | −0,079 [−0,263 ; +0,117] | −0,050 [−0,236 ; +0,114] |
| V3 — BE 2,0 ATR (F2b+F3) | −0,018 [−0,131 ; +0,105] | −0,007 [−0,156 ; +0,167] | −0,031 [−0,192 ; +0,101] |
| V3 — BE 2,5 ATR (F2b+F3) | −0,012 [−0,118 ; +0,097] | −0,027 [−0,175 ; +0,144] | +0,005 [−0,135 ; +0,114] |
| V3 — BE 3,0 ATR (F2b+F3) | +0,009 [−0,070 ; +0,105] | +0,016 [−0,114 ; +0,175] | −0,000 [−0,085 ; +0,080] |
| V3 — BE 4,0 ATR (F2b+F3) | +0,030 [−0,035 ; +0,118] | +0,049 [−0,054 ; +0,191] | +0,009 [−0,055 ; +0,070] |

## Annexe C — Queue droite : gros gagnants de RE-1 coupés par le break-even (H = 26)

Gros gagnants : trades de RE-1 à ≥ +3 ATR nets (209 trades) et décile supérieur (108 trades). Cellule : part coupée ; part de leur contribution perdue ; coût par trade sur les 1 080 entrées (ATR).

**Gros gagnants ≥ +3 ATR**

| Seuil | V1 — BE sur F3 | V2 — BE sur F2b | V3 — BE sur F2b et F3 |
|---|---|---|---|
| m = 1,0 | 17,2 % ; 16,6 % ; −0,217 | 22,0 % ; 22,7 % ; −0,298 | 39,2 % ; 39,3 % ; −0,515 |
| m = 1,5 | 11,0 % ; 11,2 % ; −0,147 | 13,4 % ; 12,7 % ; −0,166 | 24,4 % ; 23,9 % ; −0,313 |
| m = 2,0 | 8,1 % ; 7,7 % ; −0,101 | 9,1 % ; 8,0 % ; −0,105 | 17,2 % ; 15,7 % ; −0,206 |
| m = 2,5 | 5,7 % ; 5,2 % ; −0,068 | 6,7 % ; 6,2 % ; −0,082 | 12,4 % ; 11,4 % ; −0,149 |
| m = 3,0 | 4,8 % ; 3,6 % ; −0,047 | 4,3 % ; 4,4 % ; −0,057 | 9,1 % ; 7,9 % ; −0,104 |
| m = 4,0 | 2,9 % ; 2,4 % ; −0,032 | 2,4 % ; 1,9 % ; −0,025 | 5,3 % ; 4,3 % ; −0,056 |

**Gros gagnants décile supérieur**

| Seuil | V1 — BE sur F3 | V2 — BE sur F2b | V3 — BE sur F2b et F3 |
|---|---|---|---|
| m = 1,0 | 16,7 % ; 16,4 % ; −0,151 | 22,2 % ; 23,3 % ; −0,214 | 38,9 % ; 39,7 % ; −0,365 |
| m = 1,5 | 9,3 % ; 10,5 % ; −0,097 | 13,0 % ; 12,5 % ; −0,115 | 22,2 % ; 23,0 % ; −0,211 |
| m = 2,0 | 5,6 % ; 6,4 % ; −0,059 | 8,3 % ; 7,5 % ; −0,069 | 13,9 % ; 13,9 % ; −0,128 |
| m = 2,5 | 3,7 % ; 4,2 % ; −0,038 | 6,5 % ; 6,1 % ; −0,056 | 10,2 % ; 10,3 % ; −0,094 |
| m = 3,0 | 2,8 % ; 2,3 % ; −0,021 | 4,6 % ; 4,6 % ; −0,042 | 7,4 % ; 6,9 % ; −0,063 |
| m = 4,0 | 2,8 % ; 2,3 % ; −0,021 | 1,9 % ; 1,5 % ; −0,014 | 4,6 % ; 3,8 % ; −0,035 |

## Annexe D — Risque : V3 m = 2 (et V1, V2 à m = 2) contre RE-1

**D0. Trades concernés (V3 m = 2, H26)** — sur 1 080 entrées : 565 break-even déclenchés, 268 exécutés (dont 13 en gap) : 147 sauvés, 121 coupés. Gros gagnants de RE-1 coupés : 36 sur 209 à ≥ +3 ATR (17,2 %, 15,7 % de leur contribution), 15 sur 108 du décile supérieur (13,9 %).

**D1. Chemin réel** — MDD valorisé et Calmar à 0,25 % par ATR (resultats_C03.csv).

| Lecture | RE-1 | V1 m = 2 (F3) | V2 m = 2 (F2b) | V3 m = 2 (les deux) |
|---|---|---|---|---|
| 5 bps, H = 24 | −14,2 % ; 0,94 | −12,7 % ; 1,04 | −13,8 % ; 0,99 | −11,2 % ; 1,20 |
| 5 bps, H = 26 | −13,5 % ; 1,16 | −13,1 % ; 1,13 | −12,9 % ; 1,19 | −11,7 % ; 1,25 |
| 5 bps, H = 28 | −16,2 % ; 0,92 | −14,1 % ; 1,05 | −12,7 % ; 1,10 | −12,5 % ; 1,12 |
| 10 bps, H = 24 | −16,7 % ; 0,43 | −18,0 % ; 0,40 | −16,3 % ; 0,46 | −15,5 % ; 0,48 |
| 10 bps, H = 26 | −15,9 % ; 0,60 | −16,7 % ; 0,52 | −15,4 % ; 0,60 | −13,4 % ; 0,64 |
| 10 bps, H = 28 | −18,4 % ; 0,48 | −16,4 % ; 0,55 | −14,9 % ; 0,55 | −14,2 % ; 0,57 |

**D2. Chemins réordonnés** — 2 000 chemins, mois d'entrée tirés avec remise (mêmes tirages que les IC). MDD aux sorties ; Calmar = PnL annualisé sur 6 ans / |MDD aux sorties|. Cellule : écart observé sur le chemin réel ; P2,5 / médiane / P97,5 de l'écart sur les chemins ; part des chemins où la variante fait mieux.

| Lecture | Variante | Écart de MDD (points) | Écart de Calmar |
|---|---|---|---|
| 5 bps, H = 24 | V1 m = 2 | +1,0 ; −2,5 / +1,4 / +5,2 ; 80 % | +0,07 ; −0,31 / +0,07 / +0,45 ; 68 % |
| 5 bps, H = 24 | V2 m = 2 | +0,5 ; −1,2 / +2,0 / +8,0 ; 87 % | +0,06 ; −0,22 / +0,13 / +0,61 ; 80 % |
| 5 bps, H = 24 | V3 m = 2 | +2,7 ; −1,6 / +3,3 / +10,5 ; 92 % | +0,27 ; −0,31 / +0,20 / +0,91 ; 82 % |
| 5 bps, H = 26 | V1 m = 2 | +0,8 ; −2,9 / +1,3 / +5,3 ; 80 % | +0,01 ; −0,40 / +0,03 / +0,44 ; 59 % |
| 5 bps, H = 26 | V2 m = 2 | +0,6 ; −1,6 / +1,9 / +8,7 ; 86 % | +0,04 ; −0,31 / +0,11 / +0,77 ; 72 % |
| 5 bps, H = 26 | V3 m = 2 | +1,6 ; −2,1 / +3,1 / +11,6 ; 89 % | +0,08 ; −0,52 / +0,14 / +0,97 ; 69 % |
| 5 bps, H = 28 | V1 m = 2 | +2,1 ; −2,9 / +1,3 / +5,1 ; 78 % | +0,16 ; −0,30 / +0,06 / +0,45 ; 70 % |
| 5 bps, H = 28 | V2 m = 2 | +3,3 ; −2,6 / +1,8 / +8,9 ; 79 % | +0,20 ; −0,40 / +0,05 / +0,61 ; 60 % |
| 5 bps, H = 28 | V3 m = 2 | +3,4 ; −3,4 / +2,7 / +11,7 ; 82 % | +0,21 ; −0,54 / +0,10 / +0,85 ; 65 % |
| 10 bps, H = 24 | V1 m = 2 | −1,6 ; −3,6 / +1,5 / +6,4 ; 78 % | −0,05 ; −0,22 / +0,02 / +0,24 ; 60 % |
| 10 bps, H = 24 | V2 m = 2 | +0,4 ; −1,6 / +2,2 / +8,9 ; 86 % | +0,03 ; −0,16 / +0,05 / +0,35 ; 74 % |
| 10 bps, H = 24 | V3 m = 2 | +1,6 ; −2,5 / +3,7 / +12,6 ; 89 % | +0,06 ; −0,24 / +0,08 / +0,49 ; 73 % |
| 10 bps, H = 26 | V1 m = 2 | −0,9 ; −4,1 / +1,3 / +5,9 ; 75 % | −0,08 ; −0,33 / −0,00 / +0,25 ; 48 % |
| 10 bps, H = 26 | V2 m = 2 | +0,5 ; −2,0 / +2,2 / +9,9 ; 83 % | +0,01 ; −0,25 / +0,04 / +0,43 ; 65 % |
| 10 bps, H = 26 | V3 m = 2 | +2,6 ; −3,7 / +3,2 / +13,1 ; 84 % | +0,05 ; −0,45 / +0,03 / +0,51 ; 57 % |
| 10 bps, H = 28 | V1 m = 2 | +2,0 ; −3,6 / +1,4 / +5,7 ; 76 % | +0,07 ; −0,22 / +0,03 / +0,27 ; 64 % |
| 10 bps, H = 28 | V2 m = 2 | +2,8 ; −3,6 / +1,8 / +9,7 ; 75 % | +0,04 ; −0,32 / −0,00 / +0,35 ; 50 % |
| 10 bps, H = 28 | V3 m = 2 | +4,0 ; −5,1 / +2,7 / +12,8 ; 78 % | +0,09 ; −0,42 / +0,02 / +0,50 ; 55 % |

**D3. Distribution des MDD aux sorties (H26, 5 bps)** — RE-1 : P5 −26,8 %, médiane −16,1 %, P95 −10,8 % (chemin réel −12,9 %). V3 m = 2 : P5 −21,4 %, médiane −13,0 %, P95 −8,6 % (chemin réel −11,2 %).

**D4. Trois drawdowns les plus profonds du capital valorisé (H26, 5 bps)** — pic → creux, retour au pic ; dernière colonne : plus longue période sous le pic (jours).

| Configuration | 1er | 2e | 3e | Sous le pic (j) |
|---|---|---|---|---|
| RE-1 | −13,5 % (2021-04-24 → 2022-01-25, retour 2022-05-19) | −12,9 % (2023-06-25 → 2023-09-30, retour 2023-12-18) | −12,2 % (2022-09-07 → 2023-02-04, retour 2023-04-19) | 390 |
| V2 m = 2 | −12,9 % (2021-04-24 → 2022-01-25, retour 2022-05-19) | −11,5 % (2023-07-05 → 2023-09-30, retour 2023-12-15) | −9,4 % (2022-09-07 → 2022-11-25, retour 2023-03-22) | 390 |
| V3 m = 2 | −11,7 % (2021-04-24 → 2021-07-19, retour 2022-07-27) | −10,7 % (2022-08-08 → 2022-11-25, retour 2023-03-22) | −10,7 % (2023-07-05 → 2023-09-30, retour 2023-11-26) | 459 |

**D5. Même drawdown par la seule taille (H26)** — RE-1, sans break-even, au risque par ATR qui donne le même MDD valorisé que la variante. Si la variante fait mieux à MDD égal, le break-even améliore l'efficience du capital ; sinon il équivaut à réduire la taille.

| Frais | Variante (0,25 % par ATR) | Variante : PnL annualisé ; MDD ; Calmar ; sous le pic | RE-1 réduit : risque par ATR ; PnL annualisé ; MDD ; Calmar ; sous le pic | Écart de PnL annualisé, variante − RE-1 réduit |
|---|---|---|---|---|
| 5 bps | V3 m = 2, glissement 0 bps | +14,5 % ; −11,7 % ; 1,25 ; 459 j | 0,211 % ; +13,5 % ; −11,7 % ; 1,16 ; 390 j | +1,0 pt |
| 5 bps | V3 m = 2, glissement 5 bps | +12,9 % ; −11,8 % ; 1,10 ; 459 j | 0,214 % ; +13,7 % ; −11,8 % ; 1,17 ; 390 j | −0,8 pt |
| 5 bps | V3 m = 2, glissement 10 bps | +11,4 % ; −12,0 % ; 0,95 ; 459 j | 0,220 % ; +14,1 % ; −12,0 % ; 1,18 ; 390 j | −2,7 pt |
| 5 bps | V2 m = 2 | +15,3 % ; −12,9 % ; 1,19 ; 390 j | 0,239 % ; +15,0 % ; −12,9 % ; 1,17 ; 390 j | +0,3 pt |
| 5 bps | V1 m = 2 | +14,7 % ; −13,1 % ; 1,13 ; 459 j | 0,242 % ; +15,2 % ; −13,1 % ; 1,16 ; 390 j | −0,5 pt |
| 10 bps | V3 m = 2, glissement 0 bps | +8,5 % ; −13,4 % ; 0,64 ; 738 j | 0,208 % ; +8,2 % ; −13,4 % ; 0,61 ; 459 j | +0,3 pt |
| 10 bps | V3 m = 2, glissement 5 bps | +7,0 % ; −14,7 % ; 0,48 ; 783 j | 0,230 % ; +8,9 % ; −14,7 % ; 0,61 ; 459 j | −1,9 pt |
| 10 bps | V3 m = 2, glissement 10 bps | +5,5 % ; −16,1 % ; 0,34 ; 791 j | 0,253 % ; +9,6 % ; −16,1 % ; 0,60 ; 459 j | −4,0 pt |
| 10 bps | V2 m = 2 | +9,3 % ; −15,4 % ; 0,60 ; 459 j | 0,241 % ; +9,2 % ; −15,4 % ; 0,60 ; 459 j | +0,1 pt |
| 10 bps | V1 m = 2 | +8,7 % ; −16,7 % ; 0,52 ; 772 j | 0,264 % ; +9,9 % ; −16,7 % ; 0,59 ; 459 j | −1,2 pt |

## Annexe E — Performance absolue à 5 et 10 bps (H = 26, cooldown, 0,25 % par ATR)

P(espérance > 0) : part des 2 000 tirages bootstrap (grappes mensuelles) où l'espérance en ATR est positive. Erreur type : écart type bootstrap de l'espérance ; elle fixe la largeur de l'IC.

**5 bps**

| Configuration | Espérance ATR [IC] | Espérance bps [IC] | P(espérance > 0) | Écart type par trade ; erreur type (ATR) | PnL | MDD | Calmar |
|---|---|---|---|---|---|---|---|
| RE-1 (contrôle) | +0,369 [+0,098 ; +0,645] | +12,3 [+0,2 ; +24,4] | 99,9 % | 4,19 ; 0,137 | +138 % | −13,5 % | 1,16 |
| V1 — BE 1,0 ATR (F3) | +0,333 [+0,095 ; +0,581] | +9,4 [−1,7 ; +20,6] | 99,8 % | 3,88 ; 0,124 | +117 % | −17,5 % | 0,79 |
| V1 — BE 1,5 ATR (F3) | +0,345 [+0,101 ; +0,598] | +9,4 [−1,4 ; +20,3] | 99,9 % | 3,97 ; 0,124 | +122 % | −16,0 % | 0,89 |
| V1 — BE 2,0 ATR (F3) | +0,354 [+0,105 ; +0,614] | +10,6 [−1,0 ; +22,3] | 99,9 % | 4,05 ; 0,127 | +128 % | −13,1 % | 1,13 |
| V1 — BE 2,5 ATR (F3) | +0,371 [+0,114 ; +0,634] | +12,0 [+0,4 ; +24,0] | 99,9 % | 4,09 ; 0,129 | +137 % | −12,4 % | 1,25 |
| V1 — BE 3,0 ATR (F3) | +0,368 [+0,108 ; +0,628] | +11,5 [−0,6 ; +23,6] | 100,0 % | 4,14 ; 0,131 | +135 % | −12,7 % | 1,21 |
| V1 — BE 4,0 ATR (F3) | +0,373 [+0,106 ; +0,643] | +11,7 [−0,5 ; +23,9] | 99,9 % | 4,16 ; 0,135 | +139 % | −13,1 % | 1,20 |
| V2 — BE 1,0 ATR (F2b) | +0,248 [+0,028 ; +0,481] | +9,1 [−1,2 ; +19,4] | 98,8 % | 3,54 ; 0,113 | +79 % | −12,2 % | 0,83 |
| V2 — BE 1,5 ATR (F2b) | +0,327 [+0,096 ; +0,573] | +11,7 [+1,0 ; +22,5] | 99,9 % | 3,83 ; 0,119 | +114 % | −14,7 % | 0,92 |
| V2 — BE 2,0 ATR (F2b) | +0,365 [+0,134 ; +0,602] | +12,4 [+1,4 ; +23,4] | 100,0 % | 3,93 ; 0,120 | +136 % | −12,9 % | 1,19 |
| V2 — BE 2,5 ATR (F2b) | +0,354 [+0,113 ; +0,595] | +12,0 [+0,6 ; +23,3] | 100,0 % | 3,97 ; 0,123 | +130 % | −14,3 % | 1,04 |
| V2 — BE 3,0 ATR (F2b) | +0,377 [+0,129 ; +0,627] | +13,1 [+1,2 ; +24,7] | 100,0 % | 4,00 ; 0,126 | +144 % | −14,4 % | 1,12 |
| V2 — BE 4,0 ATR (F2b) | +0,394 [+0,143 ; +0,654] | +13,4 [+1,5 ; +25,4] | 100,0 % | 4,05 ; 0,128 | +148 % | −15,0 % | 1,09 |
| V3 — BE 1,0 ATR (F2b+F3) | +0,212 [+0,030 ; +0,407] | +6,2 [−3,0 ; +15,8] | 98,8 % | 3,16 ; 0,098 | +63 % | −15,5 % | 0,55 |
| V3 — BE 1,5 ATR (F2b+F3) | +0,304 [+0,097 ; +0,527] | +8,8 [−1,1 ; +19,0] | 99,9 % | 3,58 ; 0,108 | +99 % | −15,8 % | 0,77 |
| V3 — BE 2,0 ATR (F2b+F3) | +0,350 [+0,142 ; +0,570] | +10,6 [−0,3 ; +21,7] | 100,0 % | 3,78 ; 0,111 | +126 % | −11,7 % | 1,25 |
| V3 — BE 2,5 ATR (F2b+F3) | +0,357 [+0,133 ; +0,586] | +11,7 [+0,4 ; +22,6] | 100,0 % | 3,87 ; 0,116 | +129 % | −12,3 % | 1,20 |
| V3 — BE 3,0 ATR (F2b+F3) | +0,377 [+0,140 ; +0,616] | +12,2 [+0,6 ; +23,6] | 100,0 % | 3,95 ; 0,121 | +141 % | −13,4 % | 1,18 |
| V3 — BE 4,0 ATR (F2b+F3) | +0,398 [+0,151 ; +0,649] | +12,7 [+0,7 ; +24,6] | 100,0 % | 4,01 ; 0,127 | +149 % | −14,5 % | 1,13 |

**10 bps**

| Configuration | Espérance ATR [IC] | Espérance bps [IC] | P(espérance > 0) | Écart type par trade ; erreur type (ATR) | PnL | MDD | Calmar |
|---|---|---|---|---|---|---|---|
| RE-1 (contrôle) | +0,233 [−0,041 ; +0,511] | +7,3 [−4,8 ; +19,4] | 95,2 % | 4,19 ; 0,138 | +72 % | −15,9 % | 0,60 |
| V1 — BE 1,0 ATR (F3) | +0,197 [−0,043 ; +0,448] | +4,4 [−6,7 ; +15,6] | 94,2 % | 3,88 ; 0,125 | +57 % | −23,5 % | 0,33 |
| V1 — BE 1,5 ATR (F3) | +0,209 [−0,034 ; +0,463] | +4,4 [−6,4 ; +15,3] | 95,0 % | 3,97 ; 0,125 | +60 % | −22,3 % | 0,37 |
| V1 — BE 2,0 ATR (F3) | +0,218 [−0,035 ; +0,478] | +5,6 [−6,0 ; +17,3] | 95,2 % | 4,05 ; 0,128 | +65 % | −16,7 % | 0,52 |
| V1 — BE 2,5 ATR (F3) | +0,235 [−0,026 ; +0,503] | +7,0 [−4,6 ; +19,0] | 96,2 % | 4,09 ; 0,131 | +72 % | −14,3 % | 0,66 |
| V1 — BE 3,0 ATR (F3) | +0,233 [−0,032 ; +0,495] | +6,5 [−5,6 ; +18,6] | 95,7 % | 4,14 ; 0,133 | +70 % | −15,0 % | 0,62 |
| V1 — BE 4,0 ATR (F3) | +0,237 [−0,035 ; +0,508] | +6,7 [−5,5 ; +18,9] | 95,5 % | 4,15 ; 0,136 | +73 % | −15,5 % | 0,62 |
| V2 — BE 1,0 ATR (F2b) | +0,112 [−0,109 ; +0,346] | +4,1 [−6,2 ; +14,4] | 84,4 % | 3,54 ; 0,114 | +29 % | −14,1 % | 0,31 |
| V2 — BE 1,5 ATR (F2b) | +0,191 [−0,047 ; +0,440] | +6,7 [−4,0 ; +17,5] | 94,4 % | 3,83 ; 0,121 | +55 % | −17,1 % | 0,44 |
| V2 — BE 2,0 ATR (F2b) | +0,229 [−0,007 ; +0,469] | +7,4 [−3,6 ; +18,4] | 97,2 % | 3,93 ; 0,121 | +70 % | −15,4 % | 0,60 |
| V2 — BE 2,5 ATR (F2b) | +0,219 [−0,029 ; +0,466] | +7,0 [−4,4 ; +18,3] | 96,2 % | 3,97 ; 0,124 | +66 % | −16,7 % | 0,53 |
| V2 — BE 3,0 ATR (F2b) | +0,241 [−0,007 ; +0,499] | +8,1 [−3,8 ; +19,7] | 96,9 % | 4,00 ; 0,127 | +77 % | −16,8 % | 0,59 |
| V2 — BE 4,0 ATR (F2b) | +0,259 [+0,003 ; +0,522] | +8,4 [−3,5 ; +20,4] | 97,7 % | 4,05 ; 0,130 | +80 % | −17,3 % | 0,59 |
| V3 — BE 1,0 ATR (F2b+F3) | +0,076 [−0,108 ; +0,277] | +1,2 [−8,0 ; +10,8] | 77,5 % | 3,16 ; 0,098 | +18 % | −21,2 % | 0,13 |
| V3 — BE 1,5 ATR (F2b+F3) | +0,168 [−0,038 ; +0,395] | +3,8 [−6,1 ; +14,0] | 94,6 % | 3,58 ; 0,108 | +44 % | −20,8 % | 0,30 |
| V3 — BE 2,0 ATR (F2b+F3) | +0,215 [+0,005 ; +0,437] | +5,6 [−5,3 ; +16,7] | 97,7 % | 3,77 ; 0,112 | +63 % | −13,4 % | 0,64 |
| V3 — BE 2,5 ATR (F2b+F3) | +0,221 [−0,003 ; +0,453] | +6,7 [−4,6 ; +17,6] | 97,2 % | 3,87 ; 0,117 | +65 % | −14,3 % | 0,61 |
| V3 — BE 3,0 ATR (F2b+F3) | +0,241 [+0,001 ; +0,489] | +7,2 [−4,4 ; +18,6] | 97,6 % | 3,94 ; 0,122 | +74 % | −15,9 % | 0,61 |
| V3 — BE 4,0 ATR (F2b+F3) | +0,263 [+0,014 ; +0,514] | +7,7 [−4,3 ; +19,6] | 98,1 % | 4,01 ; 0,128 | +80 % | −16,9 % | 0,61 |

**IC de l'espérance à 10 bps aux trois horizons** (resultats_C03.csv) — dernière colonne : horizons où l'IC exclut 0.

| Configuration | H = 24 | H = 26 | H = 28 | IC > 0 |
|---|---|---|---|---|
| RE-1 (contrôle) | +0,194 [−0,057 ; +0,451] | +0,233 [−0,041 ; +0,511] | +0,235 [−0,058 ; +0,524] | 0/3 |
| V1 — BE 1,0 ATR (F3) | +0,165 [−0,061 ; +0,398] | +0,197 [−0,043 ; +0,448] | +0,234 [−0,025 ; +0,508] | 0/3 |
| V1 — BE 1,5 ATR (F3) | +0,181 [−0,044 ; +0,420] | +0,209 [−0,034 ; +0,463] | +0,240 [−0,023 ; +0,510] | 0/3 |
| V1 — BE 2,0 ATR (F3) | +0,189 [−0,049 ; +0,431] | +0,218 [−0,035 ; +0,478] | +0,238 [−0,038 ; +0,514] | 0/3 |
| V1 — BE 2,5 ATR (F3) | +0,199 [−0,033 ; +0,447] | +0,235 [−0,026 ; +0,503] | +0,240 [−0,035 ; +0,520] | 0/3 |
| V1 — BE 3,0 ATR (F3) | +0,193 [−0,047 ; +0,439] | +0,233 [−0,032 ; +0,495] | +0,230 [−0,050 ; +0,510] | 0/3 |
| V1 — BE 4,0 ATR (F3) | +0,202 [−0,042 ; +0,455] | +0,237 [−0,035 ; +0,508] | +0,228 [−0,058 ; +0,519] | 0/3 |
| V2 — BE 1,0 ATR (F2b) | +0,075 [−0,125 ; +0,289] | +0,112 [−0,109 ; +0,346] | +0,085 [−0,141 ; +0,327] | 0/3 |
| V2 — BE 1,5 ATR (F2b) | +0,156 [−0,063 ; +0,385] | +0,191 [−0,047 ; +0,440] | +0,174 [−0,075 ; +0,425] | 0/3 |
| V2 — BE 2,0 ATR (F2b) | +0,189 [−0,028 ; +0,413] | +0,229 [−0,007 ; +0,469] | +0,214 [−0,029 ; +0,470] | 0/3 |
| V2 — BE 2,5 ATR (F2b) | +0,183 [−0,037 ; +0,418] | +0,219 [−0,029 ; +0,466] | +0,223 [−0,028 ; +0,480] | 0/3 |
| V2 — BE 3,0 ATR (F2b) | +0,192 [−0,030 ; +0,428] | +0,241 [−0,007 ; +0,499] | +0,245 [−0,014 ; +0,510] | 0/3 |
| V2 — BE 4,0 ATR (F2b) | +0,214 [−0,016 ; +0,460] | +0,259 [+0,003 ; +0,522] | +0,257 [−0,008 ; +0,531] | 1/3 |
| V3 — BE 1,0 ATR (F2b+F3) | +0,047 [−0,124 ; +0,231] | +0,076 [−0,108 ; +0,277] | +0,084 [−0,121 ; +0,301] | 0/3 |
| V3 — BE 1,5 ATR (F2b+F3) | +0,143 [−0,047 ; +0,352] | +0,168 [−0,038 ; +0,395] | +0,179 [−0,040 ; +0,422] | 0/3 |
| V3 — BE 2,0 ATR (F2b+F3) | +0,185 [−0,016 ; +0,396] | +0,215 [+0,005 ; +0,437] | +0,217 [−0,016 ; +0,461] | 1/3 |
| V3 — BE 2,5 ATR (F2b+F3) | +0,189 [−0,021 ; +0,413] | +0,221 [−0,003 ; +0,453] | +0,228 [−0,011 ; +0,476] | 0/3 |
| V3 — BE 3,0 ATR (F2b+F3) | +0,191 [−0,028 ; +0,418] | +0,241 [+0,001 ; +0,489] | +0,240 [−0,010 ; +0,504] | 1/3 |
| V3 — BE 4,0 ATR (F2b+F3) | +0,222 [−0,009 ; +0,472] | +0,263 [+0,014 ; +0,514] | +0,250 [−0,005 ; +0,522] | 1/3 |

## Annexe F — Stress d'exécution : glissement du seul break-even, V3 m = 2

Le break-even reste à open[t + 1] ± 5 bps ; son prix d'exécution (niveau, ou ouverture en gap) est dégradé de 0, 5 ou 10 bps. Stop initial et sorties à horizon inchangés. Effet apparié : sur les entrées de RE-1, frais compensés. Chemins : part des 2 000 chemins réordonnés où V3 a un MDD (un Calmar) meilleur que RE-1.

**5 bps**

| Horizon | Glissement BE | Espérance ATR [IC] | Effet apparié BE − RE-1 [IC] | PnL | MDD | Calmar | BE déclenchés ; exécutés | Chemins : MDD ; Calmar |
|---|---|---|---|---|---|---|---|---|
| H = 24 | 0 bps | +0,320 [+0,120 ; +0,530] | −0,009 [−0,102 ; +0,085] | +114 % | −11,2 % | 1,20 | 567 ; 261 | 92 % ; 82 % |
| H = 24 | 5 bps | +0,286 [+0,085 ; +0,497] | −0,042 [−0,138 ; +0,051] | +98 % | −11,6 % | 1,04 | 567 ; 261 | 86 % ; 61 % |
| H = 24 | 10 bps | +0,252 [+0,052 ; +0,465] | −0,076 [−0,173 ; +0,017] | +82 % | −12,6 % | 0,84 | 567 ; 261 | 77 % ; 35 % |
| H = 26 | 0 bps | +0,350 [+0,142 ; +0,570] | −0,018 [−0,131 ; +0,105] | +126 % | −11,7 % | 1,25 | 565 ; 268 | 89 % ; 69 % |
| H = 26 | 5 bps | +0,314 [+0,106 ; +0,534] | −0,054 [−0,168 ; +0,066] | +108 % | −11,8 % | 1,10 | 565 ; 268 | 82 % ; 48 % |
| H = 26 | 10 bps | +0,278 [+0,068 ; +0,501] | −0,090 [−0,204 ; +0,027] | +91 % | −12,0 % | 0,95 | 565 ; 268 | 73 % ; 26 % |
| H = 28 | 0 bps | +0,352 [+0,122 ; +0,596] | −0,018 [−0,140 ; +0,106] | +120 % | −12,5 % | 1,12 | 553 ; 275 | 82 % ; 65 % |
| H = 28 | 5 bps | +0,315 [+0,084 ; +0,560] | −0,055 [−0,176 ; +0,070] | +102 % | −13,0 % | 0,96 | 553 ; 275 | 74 % ; 44 % |
| H = 28 | 10 bps | +0,278 [+0,050 ; +0,523] | −0,092 [−0,213 ; +0,033] | +86 % | −13,5 % | 0,81 | 553 ; 275 | 63 % ; 23 % |

**10 bps**

| Horizon | Glissement BE | Espérance ATR [IC] | Effet apparié BE − RE-1 [IC] | PnL | MDD | Calmar | BE déclenchés ; exécutés | Chemins : MDD ; Calmar |
|---|---|---|---|---|---|---|---|---|
| H = 24 | 0 bps | +0,185 [−0,016 ; +0,396] | −0,009 [−0,102 ; +0,085] | +54 % | −15,5 % | 0,48 | 567 ; 261 | 89 % ; 73 % |
| H = 24 | 5 bps | +0,151 [−0,050 ; +0,362] | −0,042 [−0,138 ; +0,051] | +42 % | −16,8 % | 0,36 | 567 ; 261 | 81 % ; 46 % |
| H = 24 | 10 bps | +0,117 [−0,084 ; +0,329] | −0,076 [−0,173 ; +0,017] | +31 % | −18,0 % | 0,26 | 567 ; 261 | 67 % ; 20 % |
| H = 26 | 0 bps | +0,215 [+0,005 ; +0,437] | −0,018 [−0,131 ; +0,105] | +63 % | −13,4 % | 0,64 | 565 ; 268 | 84 % ; 57 % |
| H = 26 | 5 bps | +0,179 [−0,035 ; +0,403] | −0,054 [−0,168 ; +0,066] | +50 % | −14,7 % | 0,48 | 565 ; 268 | 75 % ; 34 % |
| H = 26 | 10 bps | +0,142 [−0,073 ; +0,370] | −0,090 [−0,204 ; +0,027] | +38 % | −16,1 % | 0,34 | 565 ; 268 | 61 % ; 14 % |
| H = 28 | 0 bps | +0,217 [−0,016 ; +0,461] | −0,018 [−0,140 ; +0,106] | +60 % | −14,2 % | 0,57 | 553 ; 275 | 78 % ; 55 % |
| H = 28 | 5 bps | +0,179 [−0,052 ; +0,426] | −0,055 [−0,176 ; +0,070] | +47 % | −15,0 % | 0,44 | 553 ; 275 | 67 % ; 32 % |
| H = 28 | 10 bps | +0,142 [−0,092 ; +0,391] | −0,092 [−0,213 ; +0,033] | +35 % | −16,1 % | 0,32 | 553 ; 275 | 53 % ; 15 % |

**Huit métriques, H26, 5 bps**

| Configuration | PnL : 0,25 %/ATR ; 1x ; bps (1x) | PF | WR | Espérance : bps [IC] ; ATR [IC] | MDD | Trades (/mois) ; stop initial ; BE | Durée méd. | Part des frais (1x) |
|---|---|---|---|---|---|---|---|---|
| RE-1 | +138 % ; +204 % ; +13320 | 1,20 | 44,3 % | +12,3 [+0,2 ; +24,4] ; +0,369 [+0,098 ; +0,645] | −13,5 % | 1 080 (15,0) ; 24 % ; 0 % | 26 | 29 % |
| V3 m = 2, glissement 0 bps | +126 % ; +163 % ; +11475 | 1,21 | 35,3 % | +10,6 [−0,3 ; +21,7] ; +0,350 [+0,142 ; +0,570] | −11,7 % | 1 080 (15,0) ; 19 % ; 25 % | 26 | 32 % |
| V3 m = 2, glissement 5 bps | +108 % ; +130 % ; +10135 | 1,18 | 33,3 % | +9,4 [−1,6 ; +20,4] ; +0,314 [+0,106 ; +0,534] | −11,8 % | 1 080 (15,0) ; 19 % ; 25 % | 26 | 35 % |
| V3 m = 2, glissement 10 bps | +91 % ; +101 % ; +8795 | 1,15 | 33,3 % | +8,1 [−2,7 ; +19,1] ; +0,278 [+0,068 ; +0,501] | −12,0 % | 1 080 (15,0) ; 19 % ; 25 % | 26 | 38 % |

**Huit métriques, H26, 10 bps**

| Configuration | PnL : 0,25 %/ATR ; 1x ; bps (1x) | PF | WR | Espérance : bps [IC] ; ATR [IC] | MDD | Trades (/mois) ; stop initial ; BE | Durée méd. | Part des frais (1x) |
|---|---|---|---|---|---|---|---|---|
| RE-1 | +72 % ; +77 % ; +7920 | 1,11 | 42,8 % | +7,3 [−4,8 ; +19,4] ; +0,233 [−0,041 ; +0,511] | −15,9 % | 1 080 (15,0) ; 24 % ; 0 % | 26 | 58 % |
| V3 m = 2, glissement 0 bps | +63 % ; +53 % ; +6075 | 1,10 | 32,4 % | +5,6 [−5,3 ; +16,7] ; +0,215 [+0,005 ; +0,437] | −13,4 % | 1 080 (15,0) ; 19 % ; 25 % | 26 | 64 % |
| V3 m = 2, glissement 5 bps | +50 % ; +34 % ; +4735 | 1,08 | 32,4 % | +4,4 [−6,6 ; +15,4] ; +0,179 [−0,035 ; +0,403] | −14,7 % | 1 080 (15,0) ; 19 % ; 25 % | 26 | 70 % |
| V3 m = 2, glissement 10 bps | +38 % ; +17 % ; +3395 | 1,06 | 32,4 % | +3,1 [−7,7 ; +14,1] ; +0,142 [−0,073 ; +0,370] | −16,1 % | 1 080 (15,0) ; 19 % ; 25 % | 26 | 76 % |

## Annexe G — Diagnostic par année, V3 m = 2 (H = 26, cooldown)

**G1. Effet apparié par année d'entrée** — IC 95 % par grappes mensuelles de l'année ; RE-1 : espérance nette (5 bps) et nombre de Long / Short.

| Année | Trades | Sortis au BE | Effet apparié ATR [IC] | RE-1 : espérance ATR | Long / Short |
|---|---|---|---|---|---|
| 2020 | 189 | 37 (20 sauvés, 17 coupés) | +0,047 [−0,129 ; +0,242] | +0,514 | 104 / 85 |
| 2021 | 192 | 45 (24 sauvés, 21 coupés) | +0,000 [−0,182 ; +0,189] | +0,024 | 100 / 92 |
| 2022 | 173 | 46 (25 sauvés, 21 coupés) | −0,184 [−0,538 ; +0,133] | +0,305 | 93 / 80 |
| 2023 | 188 | 62 (34 sauvés, 28 coupés) | +0,016 [−0,365 ; +0,503] | +0,504 | 97 / 91 |
| 2024 | 171 | 37 (25 sauvés, 12 coupés) | +0,104 [−0,120 ; +0,298] | +0,334 | 95 / 76 |
| 2025 | 167 | 41 (19 sauvés, 22 coupés) | −0,105 [−0,374 ; +0,144] | +0,550 | 91 / 76 |

**G2. Trades sortis au break-even : 2022 contre les autres années** (BTC en 2022 : −64 %)

| Mesure | 2022 | Autres années | Toutes |
|---|---|---|---|
| Sorties au break-even | 46 | 222 | 268 |
| Sauvés (échec du breakout) | 25 | 122 | 147 |
| Coupés (reprise après retest) | 21 | 100 | 121 |
| Effet moyen par sortie au BE (ATR) | −0,69 | +0,06 | −0,07 |
| RE-1 moyen des sauvés (ATR) | −1,68 | −2,07 | −2,01 |
| RE-1 moyen des coupés (ATR) | +3,20 | +2,36 | +2,51 |
| Part de Long | 52 % | 49 % | 49 % |
| Part de F2b | 46 % | 55 % | 53 % |
| Part de sorties en gap | 11 % | 4 % | 5 % |
| ATR14 médian (bps) | +49,82 | +42,43 | +43,05 |
| Volatilité réalisée / ATR14, médiane | +0,81 | +0,80 | +0,80 |
| Excursion adverse avant activation, médiane (ATR) | +0,86 | +0,61 | +0,62 |
| MFE avant le BE, médiane (ATR) | +2,78 | +2,86 | +2,85 |
| Barres avant le BE, médiane | +14,50 | +13,00 | +13,00 |
| Profondeur du retest après le BE, médiane (ATR) | +1,30 | +1,56 | +1,50 |
| … retest des sauvés, médiane (ATR) | +2,76 | +2,47 | +2,48 |
| … retest des coupés, médiane (ATR) | +0,39 | +0,75 | +0,68 |
| MFE après le BE, médiane (ATR) | +1,87 | +1,94 | +1,91 |
| … MFE après le BE des coupés, médiane | +3,60 | +3,33 | +3,34 |

**G2 bis. Concentration du coût par année** — effet apparié de l'année, puis sans ses deux sorties au BE les plus coûteuses (même traitement pour chaque année) ; plus grand gain unitaire du break-even.

| Année | Effet par trade | Sans les 2 plus coûteuses | Les 2 plus coûteuses : effet (RE-1) | Plus grand gain |
|---|---|---|---|---|
| 2020 | +0,047 | +0,104 | −6,19 (RE-1 +6,19) ; −4,34 (RE-1 +4,34) | +7,19 |
| 2021 | +0,000 | +0,054 | −5,07 (RE-1 +5,07) ; −5,00 (RE-1 +5,00) | +4,77 |
| 2022 | −0,184 | +0,006 | −18,63 (RE-1 +18,63) ; −14,26 (RE-1 +14,26) | +4,79 |
| 2023 | +0,016 | +0,123 | −11,17 (RE-1 +10,73) ; −8,85 (RE-1 +8,85) | +30,38 |
| 2024 | +0,104 | +0,194 | −10,44 (RE-1 +10,44) ; −4,52 (RE-1 +4,52) | +5,11 |
| 2025 | −0,105 | −0,016 | −8,44 (RE-1 +8,44) ; −6,45 (RE-1 +6,45) | +6,97 |

**G2 ter. Les dix sorties au BE les plus coûteuses, toutes années** (ATR)

| Entrée (UTC) | Famille | Sens | RE-1 | Effet du BE |
|---|---|---|---|---|
| 2022-03-27 14:30 | F3 | Long | +18,63 | −18,63 |
| 2022-09-06 13:30 | F3 | Short | +14,26 | −14,26 |
| 2023-05-27 13:00 | F2b | Long | +10,73 | −11,17 |
| 2024-10-09 08:00 | F2b | Short | +10,44 | −10,44 |
| 2022-06-05 12:30 | F3 | Long | +9,15 | −9,15 |
| 2023-10-15 10:30 | F2b | Long | +8,85 | −8,85 |
| 2023-12-17 14:00 | F2b | Short | +8,66 | −8,66 |
| 2025-10-19 04:30 | F2b | Long | +8,44 | −8,44 |
| 2023-02-14 07:30 | F2b | Long | +8,21 | −8,21 |
| 2023-04-30 05:00 | F3 | Long | +7,72 | −7,72 |

**G2 ter. Les dix sorties au BE les plus favorables, toutes années** (ATR)

| Entrée (UTC) | Famille | Sens | RE-1 | Effet du BE |
|---|---|---|---|---|
| 2023-01-11 12:00 | F2b | Short | −30,38 | +30,38 |
| 2020-05-24 05:30 | F2b | Long | −7,19 | +7,19 |
| 2025-05-07 16:00 | F2b | Short | −6,97 | +6,97 |
| 2020-03-15 19:30 | F2b | Long | −6,96 | +6,96 |
| 2023-07-02 13:30 | F2b | Short | −6,29 | +6,29 |
| 2023-05-10 04:00 | F2b | Short | −5,78 | +5,78 |
| 2024-12-30 09:00 | F2b | Long | −5,11 | +5,11 |
| 2022-12-06 21:30 | F2b | Long | −4,79 | +4,79 |
| 2021-12-03 05:30 | F2b | Long | −4,77 | +4,77 |
| 2024-12-08 22:00 | F2b | Long | −4,53 | +4,53 |

**G3. Les trades de 2022 sortis au break-even** — excursions en ATR14(t) depuis open[t + 1] ; volatilité réalisée = écart type des rendements 30 min pendant la fenêtre de RE-1 ; retest = excursion adverse entre la sortie au BE et la fin de RE-1.

| Entrée (UTC) | Famille | Sens | ATR14 (bps) | Vol. / ATR | Adverse avant activation | MFE avant BE | Barres avant BE | Retest après BE | MFE après BE | RE-1 (ATR) | V3 (ATR) | Trajectoire |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2022-01-11 09:00 | F3 | Short | 66 | 0,78 | 0,49 | 2,62 | 13 | 3,32 | 2,01 | −2,32 (stop) | −0,00 | échec, sauvé |
| 2022-01-20 10:30 | F3 | Long | 39 | 1,82 | 1,11 | 8,37 | 23 | 4,94 | 1,89 | −1,91 (stop) | −0,00 | échec, sauvé |
| 2022-02-06 12:00 | F2b | Short | 38 | 1,34 | 4,37 | 2,59 | 8 | 7,37 | 1,03 | −2,24 | −0,00 | échec, sauvé |
| 2022-02-25 22:30 | F2b | Long | 91 | 0,57 | 0,07 | 3,92 | 21 | 0,98 | 1,15 | +0,13 | −0,00 | reprise après retest, coupé |
| 2022-03-02 11:00 | F2b | Long | 74 | 0,84 | 2,56 | 2,20 | 9 | 2,21 | 3,54 | −0,82 | −0,00 | échec, sauvé |
| 2022-03-03 03:00 | F2b | Short | 69 | 0,74 | 0,20 | 2,92 | 19 | 0,98 | 4,86 | +4,13 | −0,00 | reprise après retest, coupé |
| 2022-03-13 08:00 | F3 | Short | 34 | 0,83 | 0,30 | 5,35 | 15 | −0,10 | 4,16 | +3,07 | −0,00 | reprise après retest, coupé |
| 2022-03-17 16:30 | F2b | Short | 65 | 0,50 | 0,95 | 2,01 | 26 | 0,30 | 0,75 | +0,22 | −0,00 | reprise après retest, coupé |
| 2022-03-27 14:30 | F3 | Long | 27 | 2,39 | 1,51 | 2,64 | 12 | 0,12 | 25,52 | +18,63 | −0,00 | reprise après retest, coupé |
| 2022-03-29 16:00 | F3 | Short | 52 | 0,62 | 1,69 | 2,18 | 15 | 0,24 | 3,67 | +0,88 | −0,00 | reprise après retest, coupé |
| 2022-03-31 09:00 | F3 | Long | 36 | 1,22 | 1,08 | 2,08 | 10 (gap) | 1,95 | −0,35 | −1,49 (stop) | −0,60 | échec, sauvé |
| 2022-04-04 11:00 | F2b | Short | 47 | 0,83 | 1,70 | 4,05 | 19 | 4,13 | 1,32 | −2,50 | −0,00 | échec, sauvé |
| 2022-04-16 21:00 | F3 | Long | 29 | 0,57 | 0,03 | 3,36 | 7 | 1,62 | 1,90 | +0,89 | −0,00 | reprise après retest, coupé |
| 2022-04-23 19:00 | F3 | Short | 31 | 0,90 | 2,17 | 2,99 | 17 | 1,20 | 1,35 | −0,86 | −0,00 | échec, sauvé |
| 2022-04-28 13:30 | F3 | Short | 54 | 0,84 | 0,39 | 2,72 | 4 | 3,87 | 1,01 | −2,06 (stop) | −0,00 | échec, sauvé |
| 2022-04-30 04:30 | F2b | Short | 43 | 0,52 | 0,95 | 2,77 | 24 | 0,09 | 2,01 | +1,86 | −0,00 | reprise après retest, coupé |
| 2022-05-13 16:30 | F3 | Short | 119 | 0,57 | 0,15 | 2,34 | 5 | 0,01 | 2,87 | +2,27 | −0,00 | reprise après retest, coupé |
| 2022-05-14 17:00 | F3 | Long | 90 | 0,66 | 0,28 | 2,26 | 6 | 0,10 | 3,81 | +1,77 | −0,00 | reprise après retest, coupé |
| 2022-05-15 07:30 | F2b | Long | 79 | 0,75 | 1,49 | 2,77 | 14 | 0,52 | 5,30 | +4,51 | −0,00 | reprise après retest, coupé |
| 2022-05-17 11:30 | F2b | Short | 64 | 0,97 | 1,65 | 5,09 | 21 | 1,16 | 0,96 | −1,18 | −0,00 | échec, sauvé |
| 2022-05-27 11:00 | F2b | Short | 74 | 0,79 | 2,71 | 2,48 | 18 | 1,10 | 1,49 | +0,76 | −0,00 | reprise après retest, coupé |
| 2022-06-05 12:30 | F3 | Long | 29 | 1,23 | 1,48 | 4,65 | 9 | −0,03 | 9,93 | +9,15 | −0,00 | reprise après retest, coupé |
| 2022-06-12 14:00 | F3 | Short | 66 | 1,29 | 1,45 | 2,29 | 2 (gap) | 3,57 | −0,96 | −1,68 (stop) | −1,07 | échec, sauvé |
| 2022-06-14 20:00 | F3 | Short | 170 | 0,65 | 0,17 | 2,20 | 8 | 0,37 | 5,35 | +5,15 | −0,00 | reprise après retest, coupé |
| 2022-06-16 19:00 | F2b | Short | 142 | 0,56 | 0,31 | 2,69 | 15 | 0,91 | 2,35 | −0,29 | +0,00 | échec, sauvé |
| 2022-06-18 18:00 | F3 | Short | 119 | 1,42 | 0,17 | 4,50 | 7 | 3,66 | 3,83 | −2,95 (stop) | +0,00 | échec, sauvé |
| 2022-06-22 10:00 | F3 | Long | 104 | 0,65 | 1,48 | 2,12 | 11 | 2,79 | 1,21 | −2,25 (stop) | −0,00 | échec, sauvé |
| 2022-06-27 04:30 | F3 | Long | 59 | 0,97 | 0,57 | 2,48 | 17 (gap) | 3,96 | 0,50 | −2,37 (stop) | −0,07 | échec, sauvé |
| 2022-07-04 22:30 | F2b | Long | 71 | 0,65 | 0,13 | 3,53 | 20 | 2,44 | 1,77 | −1,48 | −0,00 | échec, sauvé |
| 2022-07-06 17:00 | F2b | Long | 76 | 0,37 | 0,86 | 2,34 | 26 | 0,32 | 0,69 | −0,05 | −0,00 | échec, sauvé |
| 2022-07-08 06:00 | F3 | Short | 86 | 0,77 | 0,04 | 3,65 | 19 | 1,37 | 1,58 | +0,71 | +0,00 | reprise après retest, coupé |
| 2022-07-29 04:00 | F2b | Long | 72 | 0,86 | 0,13 | 3,05 | 7 | 2,76 | 1,85 | −0,46 | −0,00 | échec, sauvé |
| 2022-08-14 01:00 | F3 | Long | 43 | 0,69 | 1,02 | 4,91 | 22 | 1,23 | 1,29 | −0,59 | −0,00 | échec, sauvé |
| 2022-08-21 19:30 | F3 | Long | 42 | 0,75 | 0,61 | 2,80 | 4 (gap) | 2,70 | 1,82 | −2,16 (stop) | −0,26 | échec, sauvé |
| 2022-08-22 23:30 | F3 | Long | 54 | 0,83 | 0,18 | 2,30 | 12 | 2,37 | 0,69 | −2,18 (stop) | −0,00 | échec, sauvé |
| 2022-08-26 00:30 | F3 | Short | 41 | 1,13 | 0,87 | 4,67 | 25 | 3,81 | 3,01 | −1,88 (stop) | −0,00 | échec, sauvé |
| 2022-08-30 01:00 | F2b | Long | 47 | 0,69 | 1,49 | 3,27 | 26 | 0,11 | 1,94 | −0,03 | −0,00 | échec, sauvé |
| 2022-09-06 00:00 | F2b | Long | 35 | 1,26 | 0,23 | 5,58 | 4 | 1,81 | 3,60 | +0,70 | −0,00 | reprise après retest, coupé |
| 2022-09-06 13:30 | F3 | Short | 42 | 1,74 | 0,59 | 2,27 | 3 | 0,44 | 15,62 | +14,26 | −0,00 | reprise après retest, coupé |
| 2022-10-12 00:00 | F2b | Long | 33 | 0,44 | 0,52 | 2,17 | 26 | 1,48 | 1,75 | +0,04 | −0,00 | reprise après retest, coupé |
| 2022-11-13 01:00 | F2b | Long | 33 | 1,02 | 6,73 | 3,09 | 21 (gap) | 5,06 | −2,80 | −3,25 | −4,74 | reprise après retest, coupé |
| 2022-11-28 13:30 | F2b | Short | 23 | 1,46 | 3,11 | 4,46 | 7 | 5,16 | 2,14 | −3,06 | −0,00 | échec, sauvé |
| 2022-12-06 21:30 | F2b | Long | 24 | 1,01 | 0,63 | 3,58 | 16 | 6,31 | 1,48 | −4,79 | −0,00 | échec, sauvé |
| 2022-12-16 23:00 | F3 | Short | 41 | 0,55 | 0,10 | 2,41 | 3 | 0,39 | 2,07 | +0,28 | +0,00 | reprise après retest, coupé |
| 2022-12-18 13:30 | F3 | Long | 13 | 1,06 | 2,00 | 2,80 | 11 | −0,13 | 5,47 | +0,96 | −0,00 | reprise après retest, coupé |
| 2022-12-31 08:00 | F2b | Long | 11 | 0,78 | 1,27 | 3,80 | 23 | 0,00 | 0,72 | −0,40 | −0,00 | échec, sauvé |

## Annexe H — Asymétrie F2b / F3 à m = 2 : V2 (BE sur F2b seul) contre RE-1, avec V1 et V3

Sur les mêmes entrées. Les effets sont additifs (annexe A) : V3 = V1 + V2 trade par trade.

**H1. Mécanique par sous-famille (H26)**

| Variante | Sous-famille | Activés ; sortis au BE | Sauvés : n ; gain moyen ; RE-1 moyen | Coupés : n ; coût moyen ; RE-1 moyen | Gagnants ≥ +3 ATR coupés | Effet par trade de la sous-famille [IC] |
|---|---|---|---|---|---|---|
| V1 m = 2 | F3 | 246 ; 125 | 74 ; +1,69 ; −1,72 | 51 ; −2,76 ; +2,73 | 17 / 94 | −0,031 [−0,192 ; +0,101] |
| V2 m = 2 | F2b | 319 ; 143 | 73 ; +2,28 ; −2,30 | 70 ; −2,43 ; +2,34 | 19 / 115 | −0,007 [−0,156 ; +0,167] |
| V3 m = 2 | F2b | 319 ; 143 | 73 ; +2,28 ; −2,30 | 70 ; −2,43 ; +2,34 | 19 / 115 | −0,007 [−0,156 ; +0,167] |
| V3 m = 2 | F3 | 246 ; 125 | 74 ; +1,69 ; −1,72 | 51 ; −2,76 ; +2,73 | 17 / 94 | −0,031 [−0,192 ; +0,101] |

**H2. Espérance ATR ; MDD ; Calmar aux trois horizons** (5 bps puis 10 bps)

| Configuration | 5 bps, H = 24 | 5 bps, H = 26 | 5 bps, H = 28 | 10 bps, H = 24 | 10 bps, H = 26 | 10 bps, H = 28 |
|---|---|---|---|---|---|---|
| RE-1 | +0,328 ; −14,2 % ; 0,94 | +0,369 ; −13,5 % ; 1,16 | +0,371 ; −16,2 % ; 0,92 | +0,194 ; −16,7 % ; 0,43 | +0,233 ; −15,9 % ; 0,60 | +0,235 ; −18,4 % ; 0,48 |
| V1 m = 2 | +0,324 ; −12,7 % ; 1,04 | +0,354 ; −13,1 % ; 1,13 | +0,374 ; −14,1 % ; 1,05 | +0,189 ; −18,0 % ; 0,40 | +0,218 ; −16,7 % ; 0,52 | +0,238 ; −16,4 % ; 0,55 |
| V2 m = 2 | +0,324 ; −13,8 % ; 0,99 | +0,365 ; −12,9 % ; 1,19 | +0,349 ; −12,7 % ; 1,10 | +0,189 ; −16,3 % ; 0,46 | +0,229 ; −15,4 % ; 0,60 | +0,214 ; −14,9 % ; 0,55 |
| V3 m = 2 | +0,320 ; −11,2 % ; 1,20 | +0,350 ; −11,7 % ; 1,25 | +0,352 ; −12,5 % ; 1,12 | +0,185 ; −15,5 % ; 0,48 | +0,215 ; −13,4 % ; 0,64 | +0,217 ; −14,2 % ; 0,57 |
