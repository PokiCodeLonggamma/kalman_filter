# EXP-B01 — Catégorisation cinématique et asymétrie d'excursion

- **Date :** 2026-09-28. **Étape :** B, catégorisation.
- **Actif et période :** BTC/USD Bitstamp 30 min, 2020-2025. Données tronquées au 2025-12-31 23:30 UTC ; 2026, ETH et XRP ne sont pas lus.
- **Univers :** les 7 296 signaux d'A01, dont l'identité avec `atlas_signaux.csv` est contrôlée au lancement.
- **Frais :** sans objet. Aucun PnL, aucun backtest de portefeuille, aucun seuil optimisé.
- **Reproduire :** `python experiments/B01/run_B01.py` (≈ 15 s) ; tests : `python -m pytest tests`.

## 0. Cadrage (validé par le porteur)

- **QUESTION :** quelles sous-familles causales du signal v2.1 présentent une asymétrie d'excursion favorable depuis open[t+1] ? Deux critères : MFE_H > \|MAE_H\|, et barrière favorable atteinte en premier dans plus de 50 % des cas. Lesquelles correspondent à un essoufflement de tendance, à une sortie de range ou, au contraire, à une continuation adverse ?
- **PERTINENCE POUR LE FILTRE AKF :** le déclencheur unique mélange des états cinématiques opposés : décélération d'une grande jambe, cassure d'un range étroit, choc de climax. B isole ces régimes avant toute règle de gestion.
- **CE QUE LE PROTOCOLE MESURE RÉELLEMENT :**
  - MFE_H, \|MAE_H\|, Asym_H et rendement signé à H ∈ {6, 13, 26, 48} barres ;
  - premier passage sur des barrières symétriques de ±1,0, ±1,5 et ±2,0 ATR14(t) ;
  - le tout par quartiles univariés et par familles cinématiques, en Long et en Short.
- **CE QU'IL NE PERMET PAS DE CONCLURE :** aucun PnL net, aucune optimisation de seuils (Étapes C et D).
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

  La suite complète passe : 147 réussis, 2 ignorés.
- **Censures :** fenêtres incomplètes en fin 2025 : 1 à H = 26, 3 à H = 48. Aucune barrière censurée.
- **Ambiguïtés et timeouts :**
  - barres ambiguës : 1,5 % à ±1,0 ATR, 0,7 % à ±1,5, 0,5 % à ±2,0 ;
  - timeouts : 0,2 %, 1,0 % et 3,8 % respectivement.
- **Contrôle du bêta sans placebo (annexe H) :** pour chaque strate, on compare la variation médiane du close entre open[t+1] et close[t+H] après les signaux Long (ΔL) et après les signaux Short (ΔS).
  - Timing = (ΔL − ΔS) / 2 : la part où le prix suit le sens du signal.
  - Dérive = (ΔL + ΔS) / 2 : la part commune aux deux sens, donc le mouvement du marché.

## 2. [OBS] Mesures

Détails dans les annexes A à H et les figures 1 à 4.

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
     - x1 encore opposé (n = 1 301) : neutre (49,4 %) ; x1 déjà retourné : continuation (point 2).
   - **F3, sortie de range** (n = 1 315) : neutre, gain ±1,5 de 49,8 % (Long 48,2 %, Short 51,7 %). F3 pur (n = 767) : 49,0 %, timing au close de −0,29 à H = 26.
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
- **F1 part souvent contre le signal avant de pencher dans son sens.** C'est compatible avec l'hypothèse P1 (stop structurel large et temps de développement). La part favorable reste faible (+0,13 ATR) et la dérive y pèse (+0,21).
- **La lecture « sortie de range » (F3) n'est pas soutenue sur 48 barres :** les excursions sont neutres et le close de F3 pur revient contre le signal à 26 barres.
- **`A_vol` Q1 et F2b décrivent une dérive conditionnelle du marché** (bêta de régime), pas le timing du signal. Ils peuvent servir de variables de contexte directionnel, avec la réserve d'un échantillon haussier (`RESEARCH_PHILOSOPHY.md` §4.2).
- **Les familles n'ont pas le même profil d'horizon**, ce qui soutient le principe d'enveloppes propres à chaque mécanisme en C. Mais aucune famille n'est assez forte seule pour porter une règle.

## 4. [DECISION] Orientations (rien n'est lancé)

- **Constat :** aucune famille ne justifie seule une règle de trading. Les effets ont la taille des frictions.
- **Pistes pour l'Étape C,** à tester un facteur à la fois, nettes de frais, par sens, avec la décomposition timing / dérive comme contrôle :
  1. exclure les signatures de continuation (`nis_z_100` Q4, `obs_dist_seg_atr` Q4, F1 avec x1 déjà retourné) sur une enveloppe simple ;
  2. une enveloppe courte dédiée à F5 ;
  3. un stop structurel large avec du temps pour F1.
- **`A_vol` et `log_R_rel`** se lisent comme des variables de régime (dérive), pas de timing.
- **À faire valider :** reporter dans `RESEARCH_INSIGHTS.md` les constats de B01 que tu retiens, en particulier la décomposition timing / dérive comme contrôle du bêta sans placebo.
- **Aucune Étape C n'est lancée.**
