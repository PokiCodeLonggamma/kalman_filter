# EXP-B01 — Catégorisation cinématique et asymétrie d'excursion

- **Date :** 2026-09-28. **Étape :** B, catégorisation.
- **Actif et période :** BTC/USD Bitstamp 30 min, 2020-2025. Données tronquées au 2025-12-31 23:30 UTC ; 2026, ETH et XRP ne sont pas lus.
- **Univers :** les 7 296 signaux d'A01, dont l'identité avec `atlas_signaux.csv` est contrôlée au lancement.
- **Frais :** sans objet. Aucun PnL, aucun backtest de portefeuille, aucun seuil optimisé.
- **Reproduire :** `python experiments/B01/run_B01.py` (≈ 1 min, dont le bootstrap de l'annexe I) ; tests : `python -m pytest tests`.
- **Relecture du 2026-09-28 :** moyennes, queues et trois régimes (§5, annexe I). Elle corrige deux lectures des §3 et §4.

## 0. Cadrage (validé par le porteur)

- **QUESTION :** quelles sous-familles causales du signal v2.1 présentent une asymétrie d'excursion favorable depuis open[t+1] ? Deux critères : MFE_H > \|MAE_H\|, et barrière favorable atteinte en premier dans plus de 50 % des cas. Lesquelles correspondent à un essoufflement de tendance, à une sortie de range ou, au contraire, à une continuation adverse ?
- **PERTINENCE POUR LE FILTRE AKF :** le déclencheur unique mélange des états cinématiques opposés : décélération d'une grande jambe, cassure d'un range étroit, choc de climax. B isole ces régimes avant toute règle de gestion.
- **CE QUE LE PROTOCOLE MESURE RÉELLEMENT :**
  - MFE_H, \|MAE_H\|, Asym_H et rendement signé à H ∈ {6, 13, 26, 48} barres ;
  - premier passage sur des barrières symétriques de ±1,0, ±1,5 et ±2,0 ATR14(t) ;
  - le tout par quartiles univariés et par familles cinématiques, en Long et en Short.
- **CE QU'IL NE PERMET PAS DE CONCLURE :** aucun PnL net, aucune optimisation de seuils (Étapes C et D). Les regroupements R1-R3 de la relecture ont été définis après lecture des résultats : leur tenue hors échantillon n'est pas établie.
- **Principe structurant :** B01 ne suppose pas qu'une enveloppe unique convient à tous les signaux. Les familles restent séparées.

## 1. [CODE] Implémentation et contrôles

- **Module `src/categorization/`.**
  - `excursions.py` :
    - excursions depuis `entry_price = open[t+1]`, en ATR14(t), sur la fenêtre [t+1, t+H] ;
    - barrières de premier passage sur 48 barres au plus ;
    - deux cas particuliers : une barre qui touche les deux barrières est `ambiguous` (comptée comme un échec dans le taux strict) ; une fenêtre coupée par la fin de l'échantillon est `censored` (ou NaN pour les horizons fixes).
  - `families.py` :
    - trois descripteurs dérivés, causaux : `retrace_ratio`, `cycle_seg_div_atr`, `decel_ratio` ;
    - découpage des 15 descripteurs en quartiles à bornes fixes, ou en modalités pour les variables binaires, discrètes ou très concentrées en 0 ;
    - familles F1 à F5, qui forment une partition exhaustive ;
    - résumés d'excursion avec intervalles de Wilson à 95 %.
- **Familles :** `leg_atr` est coupé à sa médiane de 2,823 ATR, `retrace_ratio` aux seuils physiques 0,50 et 0,85 fixés avant le calcul. J'ai ajouté **F5** (jambe courte, retracement < 0,50), absente de ta liste, pour que la partition soit complète.
- **Tests :** 9 nouveaux tests dans `tests/test_categorization.py` :
  - excursions Long et Short depuis open[t+1], avec un écart volontaire entre close[t] et open[t+1] ;
  - barrières : gain, perte, mèche ambiguë, timeout, censure ;
  - taux strict ;
  - quartiles et partition des familles ;
  - causalité par troncature (20 coupes) de `retrace_ratio`, `cycle_seg_div_atr` et `decel_ratio`.

  La suite complète passe : 150 réussis, 2 ignorés, dont les 3 tests ajoutés à la relecture (§5).
- **Censures :** fenêtres incomplètes en fin 2025 : 1 à H = 26, 3 à H = 48. Aucune barrière censurée.
- **Ambiguïtés et timeouts :**
  - barres ambiguës : 1,5 % à ±1,0 ATR, 0,7 % à ±1,5, 0,5 % à ±2,0 ;
  - timeouts : 0,2 %, 1,0 % et 3,8 % respectivement.
- **Contrôle du bêta sans placebo (annexe H) :** pour chaque strate, on compare la variation médiane du close entre open[t+1] et close[t+H] après les signaux Long (ΔL) et après les signaux Short (ΔS).
  - Timing = (ΔL − ΔS) / 2 : la part où le prix suit le sens du signal.
  - Dérive = (ΔL + ΔS) / 2 : la part commune aux deux sens, donc le mouvement du marché.

## 2. [OBS] Mesures

Détails dans les annexes A à H et les figures 1 à 4 ; moyennes et queues dans l'annexe I et la figure 5 (§5).

1. **Signal pris globalement : pas d'asymétrie d'excursion au-delà d'un très court terme.**
   - MFE ≈ \|MAE\| à tous les horizons : 2,12 contre 2,14 ATR à H = 26 ; 3,03 contre 3,04 à H = 48.
   - Part MFE > \|MAE\| : 51,4 % [50,3 ; 52,6] à H = 6, 49,7 % [48,5 ; 50,8] à H = 26.
   - Taux de gain strict aux barrières : 49,5 %, 50,2 % et 50,1 % pour ±1,0, ±1,5 et ±2,0 ATR (Long 48,9 à 49,9 % ; Short 50,1 à 50,8 %).
   - Le close après le signal est de la **dérive pure** : timing −0,02 ATR à H = 26 et +0,01 à H = 48 ; dérive +0,08 et +0,21, soit la hausse du BTC.
2. **Signatures de continuation, anti-timing et stables.**
   - **`nis_z_100` en Q4** (choc de la barre de signal ≥ 1,22) :
     - part MFE > \|MAE\| à H = 26 : 46,3 % [44,0 ; 48,6] ;
     - timing −0,18 ATR à H = 26 et −0,15 à H = 48 ;
     - écart Q4 − Q1 de même signe 6 années sur 6 à H = 6 (−5,6 pts), à H = 26 (−3,6 pts) et sur l'asymétrie à H = 26 (−0,29 ATR) ;
     - effet négatif en Long comme en Short.
   - **`obs_dist_seg_atr` en Q4** (plus de 2,39 ATR déjà parcourus) : 47,2 % [44,9 ; 49,5] ; timing −0,17 et −0,13.
   - **F1 avec x1 déjà retourné** (n = 568) : 45,2 % [41,2 ; 49,4] ; gain ±1,5 de 46,7 % (Long 46,2 %, Short 47,0 %) ; asymétrie médiane négative à tous les horizons, dans les deux sens.
   - **Parcours défavorable à H = 26, mais timing au close nul ou positif :**
     - `prev_seg_len` Q4 (segment ≥ 13 barres) : 46,8 % [44,3 ; 49,3], gain ±1,5 de 46,9 %, écart Q4 − Q1 stable 6 années sur 6 à H = 26 ;
     - `saturation` Q4 : 46,9 % ;
     - `leg_atr` Q4 : 47,3 %.
   - **Balayage (annexe F) :** 9 strates ont une asymétrie médiane négative et un gain strict sous 50 % en Long ET en Short. Aucune ne l'est à un niveau significatif (IC de Wilson) dans les deux sens à la fois.
3. **Signatures favorables : rares et faibles.**
   - **F5** (jambe courte, retracement < 0,50, n = 741) :
     - part MFE > \|MAE\| à H = 6 : 56,0 % [52,4 ; 59,5] (Long 56,3 %, Short 55,8 %) ;
     - gain ±1,0 ATR : 53,6 % ;
     - l'effet s'éteint à H = 26 (50,3 %), et le timing au close est nul ;
     - c'est l'entrée « fraîche » : stop implicite de 0,80 ATR, extremum tenu dans seulement 34,7 % des cas (info).
   - **`cycle_seg_div_atr` > 0** (plus bas plus haut, n = 1 001) : 53,1 % [50,0 ; 56,2] à H = 26 dans les deux sens, mais barrières à 50,4 %.
   - **F2b Long** (gain ±1,5 de 53,7 % [50,2 ; 57,1], 5 années sur 6) et **`A_vol` Q1 Short** (53,7 % [50,4 ; 56,9], 6 années sur 6) sont les seules strates dont l'IC dépasse 50 %. Mais leurs compléments vont en sens inverse (`A_vol` Q1 Long : 46,7 %), et la décomposition montre de la **dérive** :
     - F2b : timing ≈ 0, dérive +0,16 et +0,35 ATR ;
     - `A_vol` Q1 : dérive −0,13 à H = 26, contre +0,08 pour l'ensemble des signaux.
4. **Tes trois phénomènes.**
   - **F1, essoufflement d'une tendance ample** (n = 1 869) :
     - gain ±1,5 de 48,6 % [46,3 ; 50,9], supérieur à 50 % une seule année sur 6 ; part MFE > \|MAE\| à H = 26 de 48,4 % ;
     - pourtant, timing au close positif : +0,14 à H = 26, +0,13 à H = 48 ;
     - le parcours part donc plus souvent contre le signal, alors que le close penche ensuite dans son sens ;
     - x1 encore opposé (n = 1 301) : neutre aux barrières (gain ±1,5 de 49,4 %), mais timing médian au close de +0,25 ATR à H = 26 (§5) ; x1 déjà retourné : continuation (point 2).
   - **F3, sortie de range** (n = 1 315) : neutre en médiane et aux barrières, gain ±1,5 de 49,8 % (Long 48,2 %, Short 51,7 %). F3 pur (n = 767) : 49,0 %, timing médian au close de −0,29 à H = 26. En moyenne, en revanche, timing de +0,30 ATR à H = 48 (§5).
   - **F4, climax** (n = 476) : Long défavorable (45,3 %, asymétrie −0,64 à H = 26), Short favorable (55,3 %, 5 années sur 6). Au close, timing −0,44 et −0,51 : les petits effectifs rendent la lecture fragile.
5. **Profils d'horizon différents selon les familles** (figure 2) :
   - F5 est le plus favorable à 6 barres, puis s'atténue ;
   - F1 et F2a creusent vers 26 barres ;
   - F2b Long monte jusqu'à 48 barres (dérive) ;
   - F4 et F3 pur Long se dégradent avec l'horizon.
6. **Ordres de grandeur.**
   - Les écarts mesurés valent 2 à 6 points de taux et 0,1 à 0,5 ATR d'asymétrie médiane. Les frictions de 5 à 10 bps aller-retour représentent environ 0,1 à 0,2 ATR, pour un ATR14 médian de 50 bps : c'est le même ordre.
   - Deux signaux consécutifs sont espacés de 13 barres en médiane, pour des fenêtres de 48 barres : les observations se chevauchent et les IC de Wilson sont optimistes. La stabilité annuelle est le critère le plus sûr.

## 3. [HYP] Lectures cinématiques

- **Un choc violent sur la barre de signal ou un mouvement déjà consommé signent une continuation.** Après une bougie de contre-tendance extrême (`nis_z_100` Q4) ou une grande distance déjà parcourue, le prix reprend le sens précédent. C'est cohérent avec A01, K2, et avec #KAKALMAN P6.5b (strate Q4 défavorable). C'est la signature la plus stable de B01.
- **L'entrée « fraîche » (F5) porte une asymétrie de très court terme, dans les deux sens.** Elle convient au mieux à une enveloppe brève (horizon de quelques barres, barrières serrées). Son ampleur est de l'ordre des frictions.
- **F1 mêle deux régimes** *(corrigé à la relecture, §5)*. Avec x1 encore opposé, le timing médian est positif (+0,25 ATR à H = 26) mais la queue gauche est lourde ; avec x1 déjà retourné, c'est une continuation. La lecture initiale (« stop structurel large et temps de développement » pour F1 entier) est retirée.
- **La sortie de range se lit en moyenne, pas en médiane** *(corrigé à la relecture, §5)*. En médiane et aux barrières symétriques, F3 est neutre. Mais F2b et F3 avec x1 déjà retourné (R2) ont un timing moyen positif à 26-48 barres, porté par une queue droite. La lecture initiale (« non soutenue sur 48 barres ») reposait sur les seules médianes.
- **`A_vol` Q1 et F2b décrivent une dérive conditionnelle du marché** (bêta de régime), pas le timing du signal. Ils peuvent servir de variables de contexte directionnel, avec la réserve d'un échantillon haussier (`RESEARCH_PHILOSOPHY.md` §4.2).
- **Les familles n'ont pas le même profil d'horizon**, ce qui soutient le principe d'enveloppes propres à chaque mécanisme en C. Mais aucune famille n'est assez forte seule pour porter une règle.

## 4. [DECISION] Orientations (rien n'est lancé)

- **Constat :** aucune famille ne justifie seule une règle de trading. Les effets ont la taille des frictions.
- **Pistes pour l'Étape C,** révisées à la relecture (§5). Chacune se teste un facteur à la fois, nette de frais, par sens, avec la décomposition timing / dérive comme contrôle :
  1. **R3 et `nis_z_100` Q4 :** exclusion en mode retournement sur une enveloppe simple ; test dédié d'une entrée en continuation ;
  2. **R1 (dont F5) :** stop structurel serré derrière l'extremum du segment, horizon borné ;
  3. **R2 :** tenue de 26 à 48 barres, stop large ou break-even différé.
- **Piste retirée :** « un stop structurel large avec du temps pour F1 ». F1 réunit R1 et une part de R3, dont les timings sont de signes opposés, et la piste ne reposait que sur des médianes.
- **`A_vol` et `log_R_rel`** se lisent comme des variables de régime (dérive), pas de timing.
- **`RESEARCH_INSIGHTS.md` :** constats de B01 et de sa relecture reportés (I-M6, I-M7, §4).
- **Aucune Étape C n'est lancée.**

## 5. Relecture (2026-09-28) : médianes, moyennes et queues

Revue indépendante transmise par le porteur. Chacun de ses chiffres a été recalculé sur `excursions_signaux.csv`. Résultats : annexe I, `tableau_regimes_B01.csv`, figure 5.

- **[CODE]**
  - Annexe H complétée par H = 6 et par F1 · x1 encore opposé.
  - Annexe I : timing médian et moyen, avec IC 95 % par bootstrap de grappes mensuelles (2 000 tirages) et stabilité annuelle ; moyenne winsorisée ; écart de chaque sens à Tous ; asymétrie moyenne ; queues.
  - Fonctions `timing_drift`, `tail_sum` et `cluster_bootstrap` dans `families.py`, avec 3 tests.
  - Les sorties d'origine sont inchangées : même SHA-256 pour `excursions_signaux.csv`, mêmes tableaux, mêmes figures 1 à 4.
- **[OBS] L'angle mort est réel.** B01 résumait chaque strate par des médianes et des barrières symétriques. Ces mesures décrivent le cas typique : elles ne voient pas une espérance portée par une queue.
- **[OBS] Les chiffres de la relecture se retrouvent à ±0,01 ATR,** à quatre exceptions près :
  - R1 : stop implicite de 1,08 ATR (et non 1,13). Hors `nis_z_100` Q4 : 0,96 (et non 1,04) ; timing médian à H48 de +0,13 (+0,22) ; P90 + P10 à H26 de −0,49 (−0,41).
  - F1 · x1 déjà retourné : P90 + P10 à H26 vaut −0,28. Les −0,48 et −0,36 cités sont l'asymétrie moyenne et le timing moyen à H48.
  - P90 de MFE et de \|MAE\| à H48 : 10,95 et 9,82 pour F3 · x1 déjà retourné (et non 10,78 et 9,61) ; 10,82 et 9,83 pour F2b · x1 déjà retourné (10,55 et 9,63).
  - « Négatif 6 années sur 6 » vaut pour R3, pas pour `nis_z_100` Q4, dont le timing moyen à H48 est de −0,02 (positif 4 années sur 6).
- **[OBS] Trois régimes** (annexe I.1 ; timing en ATR14(t), sans frais ni stop) :

  | Régime | n (part) | Timing médian H6 / H26 / H48 | Timing moyen H26 [IC 95 %] | Timing moyen H48 [IC 95 %] | P90 + P10 H26, Long / Short |
  |---|---|---|---|---|---|
  | R1 = F1/F5 · x1 encore opposé | 1 935 (26,5 %) | +0,16 / +0,21 / +0,15 | −0,07 [−0,24 ; +0,10] | +0,07 [−0,14 ; +0,28] | −0,72 / −0,58 |
  | R2 = F2b/F3 · x1 déjà retourné | 1 874 (25,7 %) | −0,05 / −0,07 / −0,04 | +0,17 [−0,01 ; +0,34] | +0,28 [+0,03 ; +0,50] | +0,80 / +0,87 |
  | R3 = F1 · x1 déjà retourné, F2a, F4 | 2 347 (32,2 %) | −0,07 / −0,11 / −0,08 | −0,15 [−0,30 ; −0,01] | −0,29 [−0,48 ; −0,07] | −0,27 / −0,14 |
  | Hors R1-R3 | 1 140 (15,6 %) | +0,01 / −0,01 / −0,03 | −0,01 | −0,03 | +0,36 / −0,15 |

  - **R1 :** médiane positive à tous les horizons, IC hors de 0, 6 années sur 6 à H6. Moyenne ≈ 0 : la queue gauche compense.
  - **R2 :** médiane ≈ 0 ; moyenne positive à 26-48 barres, 5 années sur 6 à H48. Asymétrie moyenne de +0,49 ATR à H48, contre +0,03 pour Tous.
  - **R3 :** négatif en médiane comme en moyenne. Timing médian à H26 et timing moyen à H48 négatifs 6 années sur 6. Les deux sens font moins bien que Tous à H48 (Long −0,21, Short −0,35).
- **[OBS] Ce que la vérification ajoute.**
  - **Les moyennes ne tiennent pas à quelques chocs :** winsorisées aux P1 et P99, R2 garde +0,23 à H48 et R3 −0,28.
  - **Leur précision reste faible :** l'IC de R2 touche 0 à H26, celui de F3 seul contient 0 à H48 ([−0,03 ; +0,61]).
  - **R2 réunit deux effets d'un seul côté.** À H48, par rapport à tous les signaux du même sens : F3 · x1 déjà retourné fait +0,62 ATR en Short mais −0,11 en Long ; F2b · x1 déjà retourné fait +0,81 en Long mais −0,12 en Short. De même, F3 est positif en Long (+0,26) comme en Short (+0,33), mais ses Long ne font pas mieux que l'ensemble des Long (+0,04) : l'effet est côté Short.
  - **L'effet moyen de R2 se construit avec l'horizon :** +0,03 à H6, +0,08 à H13, +0,17 à H26, +0,28 à H48.
  - **Les queues de R2 sont plus larges des deux côtés en ATR(t)** : P10 de −6,82 et P90 de +7,65 à H48, contre −6,47 et +6,47 pour Tous. Après une compression, les mouvements suivants sont grands en unités d'ATR(t) ; l'asymétrie droite s'y ajoute.
  - **R1 :** l'extremum du segment ne tient jusqu'au signal suivant que dans 46,9 % des cas (information, I-M1). Un stop placé à l'extremum serait touché environ une fois sur deux avant le signal suivant.
- **[HYP] Lecture du porteur.**
  - R1 est un retournement par décélération : gain typique régulier, pertes rares mais larges quand la tendance reprend.
  - R2 est un breakout de compression : faux départs fréquents (médiane plate), espérance portée par la queue droite.
  - R3 est un signal tardif, après une grande jambe ou sur une bougie de choc : la tendance précédente reprend.
- **[HYP] Complément.** Le sens favorable propre à chaque sous-famille de R2 (Short pour F3, Long pour F2b) pourrait suivre la tendance de l'unité de temps supérieure. À caractériser.
- **Ce que la relecture ne permet pas de conclure :**
  - R1, R2 et R3 ont été définis après lecture des résultats de B01 : leur tenue hors échantillon n'est pas établie ;
  - timing et queues sont mesurés sans frais ni stop. Ils ne disent pas quelle enveloppe coupe la queue gauche de R1 sans détruire sa médiane, ni laquelle laisse courir la queue droite de R2 ;
  - les grappes mensuelles couvrent le chevauchement des fenêtres à l'intérieur d'un mois, pas la dépendance entre mois.
