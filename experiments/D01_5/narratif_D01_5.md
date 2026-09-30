# EXP-D01.5 — Sensibilité de RE-1 à l'horizon H seul : or, SPY, XLE

- **Date :** 2026-09-30. **Étape :** D, étape intermédiaire entre D01 et D02 (décision du porteur). **Descriptive** : RE-1 inchangée, aucun H retenu ni figé.
- **Facteur unique (OFAT) :** H, compté en barres de 30 min de la série. Tout le reste est celui de RE-1 : moteur v2.1 par défaut (R0 = 100), seuils BTC gelés (`leg_atr` P50 = 2,8233 ; `nis_z_100` P75 = 1,2245), F2b sans stop, F3 SL-B à l'extremum (δ = 0, plancher 0,25 ATR), entrée à open[t + 1], une position à la fois, cooldown.
- **Grilles du porteur :** XAU H ∈ {26, 48, 72, 96, 130} ; SPY et XLE H ∈ {6, 13, 26, 65, 130}.
- **Données :** celles de D01, inchangées (empreintes vérifiées) : CFD or HistData 2020-2025, ETF SPY et XLE Alpaca en séance régulière 2020-2025. **Frais :** 4 bps aller-retour.
- **Code :** `experiments/D01_5/run_D01_5.py`. Il réutilise `strategy.run_re1(horizon=H)` et, depuis D01, `prepare` et `gap_trades` (définitions de gaps de D01 bis). Aucun module de `src/` modifié. Test ajouté : RE-1 à H = 6 et H = 130 (structure des trades, causalité par troncature).

## 0. Cadrage

- **QUESTION :** une translation de H seul corrige-t-elle les faiblesses de D01 ?
  - Or : brut +0,24 ATR, frais 0,26 ATR à H = 26. Hypothèse du porteur : un H plus long fait croître le brut et dilue ce coût fixe.
  - SPY, XLE : H = 26 traverse deux nuits. Hypothèses du porteur : H ≤ 13 limite l'exposition aux nuits ; H ≥ 65 dilue le bruit des gaps dans la tendance.
- **PERTINENCE POUR LE FILTRE AKF :** H est le seul paramètre de RE-1 lié au temps. Le déclencheur juge la cinématique à t ; H décide quand ce jugement est encaissé, donc combien de frais, de dérive de l'actif et de nuits entrent dans chaque trade.
- **CE QUE LE PROTOCOLE MESURE RÉELLEMENT :**
  - la course séquentielle de RE-1 à chaque H (la population de trades change avec H) : les 8 métriques, l'espérance nette et brute avec IC par grappes mensuelles, le capital, le MDD et le Calmar à 0,25 %/ATR et à 1x, Long/Short, timing et dérive ;
  - l'effet apparié de H sur les entrées figées de RE-1 à H = 26 : mêmes trades, seule la sortie change ;
  - les gaps : exposition, décomposition du brut, stops percés.
- **CE QU'IL NE PERMET PAS DE CONCLURE :**
  - aucun H n'est validé : le meilleur des cinq, choisi après coup, surestime l'espérance (c'est l'objet du WFO de D02) ;
  - pas de hold-out ;
  - pas de coûts de portage (swap du CFD, emprunt des titres vendus à découvert).

## 1. Règle de lecture (fixée avant le calcul)

- Un avantage se lit sur l'IC 95 % par grappes mensuelles, en ATR et en bps : borne basse > 0. Une espérance ponctuelle > 0 dont l'IC contient 0 n'est pas un avantage établi.
- La réponse à H se lit sur la courbe entière (croissante, plateau, pic isolé), pas sur la meilleure valeur.
- Chaque variation est lue avec son effet apparié et sa décomposition timing/dérive (timing = moyenne de Long et de Short, dérive = leur demi-écart, en net).

## 2. Contrôles

Tous passés (annexe A) :
- empreintes des séries identiques à l'audit de D01 ;
- à H = 26, la chaîne redonne D01 : 23 métriques par actif, écart relatif ≤ 5·10⁻⁶ ; 4 mesures de gaps ;
- entrées figées à H = 26 identiques, trade par trade, à RE-1 ;
- à chaque H, une position à la fois, entrée à open[t + 1] et sortie à H barres hors stop.

## 3. Résultats [OBS]

**Vue d'ensemble : aucune des 15 configurations n'a un IC à borne basse > 0, ni en ATR ni en bps.** Seul XLE a des espérances ponctuelles > 0 en ATR : +0,020 à H = 26 et +0,155 à H = 65. Le seul IC d'espérance qui exclut 0 est négatif : SPY à H = 65, −38,3 bps [−76,2 ; −2,8].

### 3.1 Or (XAU) : le brut ne croît pas avec H

| H (durée médiane) | 26 (13 h) | 48 (25 h) | 72 (37 h) | 96 (50 h) | 130 (68 h) |
|---|---|---|---|---|---|
| Espérance nette ATR [IC] | −0,019 [−0,36 ; +0,35] | −0,120 [−0,62 ; +0,40] | −0,071 [−0,66 ; +0,55] | −0,185 [−0,89 ; +0,55] | −0,702 [−1,62 ; +0,26] |
| Brut ; frais (ATR) | +0,239 ; 0,257 | +0,138 ; 0,257 | +0,184 ; 0,255 | +0,071 ; 0,256 | −0,446 ; 0,255 |
| Long ; Short (ATR) | +0,33 ; −0,43 | +0,52 ; −0,86 | +0,62 ; −0,84 | +0,52 ; −0,92 | +0,08 ; −1,54 |
| Dérive (ATR) | +0,38 | +0,69 | +0,73 | +0,72 | +0,81 |
| Entrées figées : effet contre H = 26 [IC] | — | +0,02 [−0,26 ; +0,28] | +0,08 [−0,32 ; +0,49] | −0,03 [−0,48 ; +0,45] | −0,15 [−0,70 ; +0,48] |
| MDD 0,25 %/ATR ; 1x | −13,6 % ; −13,3 % | −18,8 % ; −19,8 % | −22,9 % ; −24,8 % | −30,6 % ; −31,6 % | −41,6 % ; −42,8 % |

- **Les frais restent à 0,26 ATR par trade à chaque H.** Ce sont 4 bps rapportés à l'ATR14(t) de l'entrée : H n'y entre pas.
- **Le brut par trade ne croît pas.**
  - Course séquentielle : +0,24 → +0,14 → +0,18 → +0,07 → −0,45 ATR.
  - Entrées figées (mêmes trades) : brut +0,24 → +0,26 → +0,32 → +0,21 → +0,09. Plat aux erreurs près, IC de l'effet ∋ 0.
- **Ce qui croît avec H, c'est l'exposition à la dérive de l'or** (+184 % sur l'échantillon) : +0,38 → +0,81 ATR. Elle joue des deux côtés : les Long gagnent (+0,33 → +0,62 à H = 72), les Short perdent davantage (−0,43 → −1,54). Le timing net passe de −0,05 à −0,73.
- **Le risque croît avec H** à dimensionnement égal : MDD −13,6 % → −41,6 % à 0,25 %/ATR ; IC de l'espérance 2,6 fois plus large à H = 130 qu'à H = 26.
- **Les gaps de l'or ne pèsent pas.** Les trades traversent la pause quotidienne et les week-ends (38 % à H = 26, 78 % au-delà), mais les 2 mêmes stops seulement sont percés à chaque H : coût ≤ 0,005 ATR par trade.
- **Forme de la réponse :** H = 26, celui de RE-1, est le meilleur point de la grille, à ≈ 0. Au-delà, la courbe décroît.

### 3.2 SPY : raccourcir H réduit les nuits, sans brut à protéger

| H (durée médiane) | 6 (3 h) | 13 (24 h) | 26 (48 h) | 65 (168 h) | 130 (336 h) |
|---|---|---|---|---|---|
| Espérance nette ATR [IC] | −0,161 [−0,53 ; +0,20] | −0,189 [−0,67 ; +0,29] | −0,158 [−0,74 ; +0,43] | −0,756 [−1,66 ; +0,15] | −0,378 [−1,86 ; +1,24] |
| Brut ATR | +0,004 | −0,026 | +0,004 | −0,594 | −0,218 |
| Trades exposés à une nuit | 50 % | 91 % | 92 % | 92 % | 92 % |
| Brut = gaps + séance (ATR, log) | −0,005 + 0,007 | +0,014 − 0,042 | +0,027 − 0,026 | +0,027 − 0,632 | +0,380 − 0,591 |
| Stops percés / stops ; dépassement moyen | 5/30 ; +1,78 | 6/35 ; +2,78 | 8/46 ; +2,57 | 8/47 ; +2,51 | 10/40 ; +1,95 |
| Coût des dépassements (ATR par trade) | 0,047 | 0,099 | 0,133 | 0,175 | 0,221 |
| Long ; Short (ATR) | −0,229 ; −0,055 | −0,205 ; −0,163 | +0,107 ; −0,601 | −0,039 ; −2,004 | +1,100 ; −2,617 |

- **H = 13 ne limite pas l'exposition aux nuits : 91 % des trades en traversent une, contre 92 % à H = 26.** 13 barres font exactement une séance, donc tout trade non stoppé en séance traverse une nuit.
- **Seul H = 6 réduit l'exposition** : 50 % des trades, et le coût des stops percés passe de 0,133 à 0,047 ATR par trade. **Le brut reste nul (+0,004 ATR)** : il n'y a pas d'espérance en séance que les gaps masqueraient. La composante en séance vaut ≈ 0 à tout H ≤ 26.
- **H ≥ 65 ne dilue pas les gaps.**
  - Les stops percés restent (8 à 10) et leur coût par trade augmente (0,175 et 0,221 ATR).
  - La dérive de SPY domine (+0,98 puis +1,86 ATR) et écrase les Short (−2,00 et −2,62).
  - H = 65 : −0,756 ATR, IC en bps entièrement négatif ; timing −1,02 [−2,01 ; −0,01].
- **Entrées figées :** l'effet de H va de −0,555 à −0,001 ATR, tous les IC ∋ 0.

### 3.3 XLE : un pic isolé à H = 65, porté par la population

| H (durée médiane) | 6 (20 h) | 13 (24 h) | 26 (48 h) | 65 (168 h) | 130 (335 h) |
|---|---|---|---|---|---|
| Espérance nette ATR [IC] | −0,252 [−0,64 ; +0,13] | −0,083 [−0,55 ; +0,43] | +0,020 [−0,59 ; +0,67] | +0,155 [−0,79 ; +1,13] | −1,573 [−3,51 ; +0,20] |
| Brut ATR | −0,172 | −0,003 | +0,100 | +0,235 | −1,493 |
| Trades exposés à une nuit | 57 % | 91 % | 90 % | 90 % | 92 % |
| Brut = gaps + séance (ATR, log) | −0,084 − 0,090 | +0,119 − 0,128 | +0,192 − 0,101 | +0,365 − 0,111 | −0,626 − 0,802 |
| Entrées figées : effet contre H = 26 [IC] | −0,30 [−0,87 ; +0,20] | −0,22 [−0,59 ; +0,15] | — | −0,01 [−0,71 ; +0,75] | −0,49 [−1,81 ; +0,73] |
| PnL 0,25 %/ATR ; 1x | −10 % ; −9 % | −3 % ; +11 % | +0 % ; +7 % | +3 % ; +20 % | −29 % ; −50 % |
| MDD 0,25 %/ATR ; 1x | −18,2 % ; −32,6 % | −18,1 % ; −31,4 % | −19,5 % ; −36,4 % | −10,9 % ; −26,3 % | −35,6 % ; −64,0 % |

- **Forme de la réponse : un pic isolé.** L'espérance monte de −0,25 (H = 6) à +0,16 (H = 65), puis tombe à −1,57 à H = 130.
  - À H = 130, les Short perdent −3,68 ATR (rallye de 2021-2022) et F2b, sans stop, −4,44 ATR sur 30 trades.
  - À H = 65 : 3 années positives sur 6, 2025 à −2,47 ATR.
- **Le gain de H = 65 ne vient pas de la sortie.**
  - Sur les mêmes 136 entrées que H = 26, sortir à 65 barres donne +0,009 ATR (effet −0,010 [−0,71 ; +0,75]).
  - La course à H = 65 garde 105 de ces 136 trades. Les 31 qu'elle saute, parce qu'une position de 65 barres est encore ouverte, valaient −0,48 ATR en moyenne à H = 65.
  - Le « gain » est donc un effet de calendrier : la sélection des trades, pas la sortie.
- **Le brut de XLE vient des nuits :** +0,12 à +0,37 ATR de gaps à H = 13-65, IC ∋ 0. La composante en séance est négative à chaque H, de −0,09 à −0,80 ATR.

## 4. Lecture physique [HYP]

1. **H déplace l'exposition, pas l'avantage.** Sur les mêmes entrées, déplacer la sortie de 6 à 130 barres change l'espérance de −0,55 à +0,08 ATR, avec des IC qui contiennent 0. Ce qui change nettement avec H, c'est la part de dérive de l'actif, le nombre de nuits et le risque par trade.
2. **L'hypothèse de dilution des frais sur l'or ne tient pas.**
   - Elle suppose un brut croissant avec H. Sur les mêmes entrées, le brut reste plat de 13 à 50 h (+0,21 à +0,32 ATR, écarts dans le bruit) puis baisse, et la dérive se compense entre Long et Short.
   - Le point mort des frais de l'or à H = 26 est d'environ 3,7 bps aller-retour (brut = 0,93 fois les frais de 4 bps). Mais l'IC du brut contient 0.
3. **Une sortie en fin de séance sur les ETF supprimerait les gaps sans créer d'avantage.** Mesure à l'appui : la composante en séance est ≈ 0 sur SPY et négative sur XLE à chaque H. Sur XLE, les gaps portent la seule part positive du brut.
4. **Pour le cadrage de D02 :**
   - la course séquentielle mêle l'effet de la sortie et un effet de calendrier (quels trades sont sautés) : sur XLE à H = 65, +0,155 contre +0,009 sur entrées figées. Un optimiseur de H sur la course séquentielle ajustera aussi ce calendrier ;
   - à dimensionnement égal (0,25 %/ATR14 de 30 min), le risque par trade croît avec H (MDD de l'or ×3 entre 26 et 130). Comparer des H sur le Calmar suppose de fixer cette convention ;
   - sur XAU, SPY et XLE, aucun H de la grille n'a d'avantage établi. Un WFO y mesurerait d'abord le biais de sélection de l'optimiseur, ce qui peut servir de témoin pour D02.

## 5. Écarts au prompt

- « Slippage de +2,6 ATR » : c'est le dépassement moyen de 8 stops percés sur 46 sur SPY. Leur coût rapporté à tous les trades est de 0,133 ATR par trade. Sur XLE, le dépassement moyen est de +1,0 ATR.
- « Rendement brut positif » de l'or à H = 26 : +0,239 ATR, mais IC [−0,105 ; +0,605].
