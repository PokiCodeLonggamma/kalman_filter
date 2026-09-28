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

---

# Annexes chiffrées (générées par `run_B01.py`)

## A. Univers et conventions

| Élément | Valeur |
|---|---|
| Signaux (univers A01, contrôlé identique à `atlas_signaux.csv`) | 7 296 |
| Entrée | open[t+1] ; normalisation par ATR14(t), connu à la clôture de t |
| Médiane de `leg_atr` (coupure des familles) | 2,823 ATR |
| Fenêtres H = 6 incomplètes (fin 2025, NaN) | 0 |
| Fenêtres H = 13 incomplètes (fin 2025, NaN) | 0 |
| Fenêtres H = 26 incomplètes (fin 2025, NaN) | 1 |
| Fenêtres H = 48 incomplètes (fin 2025, NaN) | 3 |
| Barrières ±1,0 ATR : gain / perte / ambiguë / timeout / censurée | 3 605 / 3 572 / 107 / 12 / 0 |
| Barrières ±1,5 ATR : gain / perte / ambiguë / timeout / censurée | 3 629 / 3 544 / 51 / 72 / 0 |
| Barrières ±2,0 ATR : gain / perte / ambiguë / timeout / censurée | 3 519 / 3 462 / 36 / 279 / 0 |

## B. Référence : tous les signaux

| Mesure | Tous | Long | Short |
|---|---|---|---|
| MFE H = 6 (ATR, médiane) | 0,93 | 0,89 | 0,96 |
| \|MAE\| H = 6 (ATR, médiane) | 0,90 | 0,90 | 0,90 |
| Asym H = 6 (ATR, médiane) | 0,06 | 0,03 | 0,08 |
| Rendement H = 6 (ATR, médiane) | 0,02 | 0,05 | −0,02 |
| MFE > \|MAE\| H = 6 | 51,4 % | 50,9 % | 51,9 % |
| MFE H = 13 (ATR, médiane) | 1,44 | 1,40 | 1,48 |
| \|MAE\| H = 13 (ATR, médiane) | 1,37 | 1,39 | 1,36 |
| Asym H = 13 (ATR, médiane) | 0,09 | 0,06 | 0,11 |
| Rendement H = 13 (ATR, médiane) | −0,02 | 0,02 | −0,07 |
| MFE > \|MAE\| H = 13 | 51,4 % | 51,2 % | 51,7 % |
| MFE H = 26 (ATR, médiane) | 2,12 | 2,08 | 2,17 |
| \|MAE\| H = 26 (ATR, médiane) | 2,14 | 2,17 | 2,12 |
| Asym H = 26 (ATR, médiane) | −0,02 | −0,06 | 0,00 |
| Rendement H = 26 (ATR, médiane) | −0,03 | 0,05 | −0,10 |
| MFE > \|MAE\| H = 26 | 49,7 % | 49,3 % | 50,0 % |
| MFE H = 48 (ATR, médiane) | 3,03 | 3,04 | 3,01 |
| \|MAE\| H = 48 (ATR, médiane) | 3,04 | 3,02 | 3,05 |
| Asym H = 48 (ATR, médiane) | 0,06 | 0,09 | 0,02 |
| Rendement H = 48 (ATR, médiane) | 0,00 | 0,22 | −0,20 |
| MFE > \|MAE\| H = 48 | 50,4 % | 50,6 % | 50,2 % |
| Barrière ±1,0 : gain strict [IC 95 %] | 49,5 % [48,3 % ; 50,6 %] | 48,9 % [47,3 % ; 50,6 %] | 50,1 % [48,4 % ; 51,7 %] |
| Barrière ±1,0 : gain, timeouts inclus / ambiguës / timeouts | 49,4 % / 1,5 % / 0,2 % | 48,8 % / 1,5 % / 0,2 % | 50,0 % / 1,4 % / 0,1 % |
| Barrière ±1,5 : gain strict [IC 95 %] | 50,2 % [49,1 % ; 51,4 %] | 49,7 % [48,1 % ; 51,3 %] | 50,8 % [49,1 % ; 52,4 %] |
| Barrière ±1,5 : gain, timeouts inclus / ambiguës / timeouts | 49,7 % / 0,7 % / 1,0 % | 49,2 % / 0,7 % / 1,1 % | 50,3 % / 0,7 % / 0,9 % |
| Barrière ±2,0 : gain strict [IC 95 %] | 50,1 % [49,0 % ; 51,3 %] | 49,9 % [48,2 % ; 51,5 %] | 50,4 % [48,8 % ; 52,1 %] |
| Barrière ±2,0 : gain, timeouts inclus / ambiguës / timeouts | 48,2 % / 0,5 % / 3,8 % | 47,9 % / 0,5 % / 4,1 % | 48,6 % / 0,5 % / 3,6 % |

## C. Univarié : écart classe haute − classe basse

Entre parenthèses : nombre d'années 2020-2025 où l'écart annuel a le même signe que l'écart global (bornes de classe fixes).

### Tous

| Descripteur | Classes | Δ MFE>MAE H6 | Δ MFE>MAE H26 | Δ Asym H26 (ATR) | Δ gain ±1,5 | Δ gain ±2,0 |
|---|---|---|---|---|---|---|
| `retrace_ratio` | Q4 − Q1 | −2,8 pts (2.0/6) | +2,7 pts (6.0/6) | 0,17 (5.0/6) | +1,6 pts (5.0/6) | +2,1 pts (5.0/6) |
| `obs_dist_seg_atr` | Q4 − Q1 | −3,6 pts (4.0/6) | −2,5 pts (4.0/6) | −0,22 (4.0/6) | −0,4 pts (5.0/6) | −0,9 pts (5.0/6) |
| `obs_lag_seg_bars` | Q4 − Q1 | +0,1 pts (1.0/6) | −2,0 pts (3.0/6) | −0,19 (5.0/6) | −0,9 pts (3.0/6) | −0,8 pts (4.0/6) |
| `x1_already_flipped_at_t` | Vrai − Faux | −2,1 pts (4.0/6) | −0,8 pts (4.0/6) | −0,09 (5.0/6) | −1,4 pts (4.0/6) | −0,8 pts (4.0/6) |
| `nis_z_100` | Q4 − Q1 | −5,6 pts (6.0/6) | −3,6 pts (6.0/6) | −0,29 (6.0/6) | −2,9 pts (4.0/6) | −4,6 pts (5.0/6) |
| `nis_z_100_seg_max` | Q4 − Q1 | −2,1 pts (5.0/6) | −0,6 pts (3.0/6) | −0,02 (4.0/6) | −0,7 pts (4.0/6) | −0,1 pts (4.0/6) |
| `cycle_seg_div_atr` | >0 − 0 | −1,4 pts (3.0/6) | +4,1 pts (5.0/6) | 0,37 (5.0/6) | +0,2 pts (4.0/6) | +0,8 pts (5.0/6) |
| `A_vol` | Q4 − Q1 | −4,0 pts (5.0/6) | −0,4 pts (4.0/6) | 0,01 (2.0/6) | −0,3 pts (2.0/6) | −1,7 pts (6.0/6) |
| `decel_ratio` | Q4 − Q1 | −3,8 pts (5.0/6) | +1,5 pts (4.0/6) | 0,16 (3.0/6) | −0,1 pts (4.0/6) | −0,5 pts (3.0/6) |
| `log_R_rel` | Q4 − Q1 | −0,8 pts (3.0/6) | −2,5 pts (5.0/6) | −0,21 (5.0/6) | −2,1 pts (4.0/6) | −1,9 pts (4.0/6) |
| `leg_atr` | Q4 − Q1 | −1,9 pts (5.0/6) | −3,5 pts (5.0/6) | −0,28 (5.0/6) | −2,4 pts (5.0/6) | −1,9 pts (5.0/6) |
| `prev_seg_len` | Q4 − Q1 | −1,9 pts (4.0/6) | −4,0 pts (6.0/6) | −0,31 (6.0/6) | −4,5 pts (5.0/6) | −3,2 pts (5.0/6) |
| `saturation` | Q4 − Q1 | −2,6 pts (5.0/6) | −3,7 pts (4.0/6) | −0,31 (4.0/6) | −2,9 pts (4.0/6) | −4,6 pts (4.0/6) |
| `n_short_seg_48` | ≥1 − 0 | +0,8 pts (4.0/6) | +1,2 pts (5.0/6) | 0,10 (5.0/6) | −0,1 pts (2.0/6) | +0,1 pts (2.0/6) |
| `run_rank` | >1 − 1 | +1,1 pts (4.0/6) | +1,1 pts (4.0/6) | 0,10 (4.0/6) | −0,3 pts (3.0/6) | −1,0 pts (4.0/6) |

### Long

| Descripteur | Classes | Δ MFE>MAE H6 | Δ MFE>MAE H26 | Δ Asym H26 (ATR) | Δ gain ±1,5 | Δ gain ±2,0 |
|---|---|---|---|---|---|---|
| `retrace_ratio` | Q4 − Q1 | −6,4 pts (5.0/6) | +0,6 pts (3.0/6) | −0,05 (3.0/6) | +0,4 pts (3.0/6) | +2,4 pts (5.0/6) |
| `obs_dist_seg_atr` | Q4 − Q1 | −6,9 pts (5.0/6) | −4,8 pts (6.0/6) | −0,46 (6.0/6) | −3,9 pts (4.0/6) | −2,1 pts (4.0/6) |
| `obs_lag_seg_bars` | Q4 − Q1 | −0,0 pts (3.0/6) | −3,3 pts (4.0/6) | −0,28 (3.0/6) | −1,4 pts (3.0/6) | −2,4 pts (3.0/6) |
| `x1_already_flipped_at_t` | Vrai − Faux | −4,4 pts (4.0/6) | −1,9 pts (5.0/6) | −0,20 (5.0/6) | −3,0 pts (6.0/6) | −3,1 pts (5.0/6) |
| `nis_z_100` | Q4 − Q1 | −6,5 pts (5.0/6) | −4,5 pts (5.0/6) | −0,38 (5.0/6) | −4,6 pts (4.0/6) | −5,2 pts (4.0/6) |
| `nis_z_100_seg_max` | Q4 − Q1 | +1,3 pts (3.0/6) | +0,4 pts (5.0/6) | 0,06 (4.0/6) | +0,2 pts (4.0/6) | +1,3 pts (4.0/6) |
| `cycle_seg_div_atr` | >0 − 0 | −1,3 pts (4.0/6) | +3,2 pts (4.0/6) | 0,36 (4.0/6) | +1,6 pts (3.0/6) | +2,5 pts (4.0/6) |
| `A_vol` | Q4 − Q1 | −2,3 pts (3.0/6) | +4,2 pts (4.0/6) | 0,43 (5.0/6) | +2,9 pts (4.0/6) | +2,1 pts (5.0/6) |
| `decel_ratio` | Q4 − Q1 | −5,1 pts (4.0/6) | +3,6 pts (4.0/6) | 0,30 (5.0/6) | +0,9 pts (3.0/6) | +3,3 pts (4.0/6) |
| `log_R_rel` | Q4 − Q1 | +1,5 pts (4.0/6) | −5,0 pts (5.0/6) | −0,41 (4.0/6) | −3,5 pts (4.0/6) | −3,3 pts (5.0/6) |
| `leg_atr` | Q4 − Q1 | −1,8 pts (4.0/6) | −6,9 pts (6.0/6) | −0,54 (6.0/6) | −5,4 pts (6.0/6) | −4,9 pts (6.0/6) |
| `prev_seg_len` | Q4 − Q1 | −0,3 pts (2.0/6) | −5,0 pts (5.0/6) | −0,40 (5.0/6) | −5,1 pts (6.0/6) | −5,2 pts (6.0/6) |
| `saturation` | Q4 − Q1 | −2,8 pts (4.0/6) | −2,8 pts (4.0/6) | −0,19 (4.0/6) | −4,7 pts (4.0/6) | −5,7 pts (3.0/6) |
| `n_short_seg_48` | ≥1 − 0 | +0,8 pts (2.0/6) | −0,8 pts (2.0/6) | −0,10 (3.0/6) | −0,3 pts (2.0/6) | −0,1 pts (3.0/6) |
| `run_rank` | >1 − 1 | −0,7 pts (4.0/6) | −2,4 pts (5.0/6) | −0,18 (3.0/6) | −3,4 pts (4.0/6) | −1,8 pts (4.0/6) |

### Short

| Descripteur | Classes | Δ MFE>MAE H6 | Δ MFE>MAE H26 | Δ Asym H26 (ATR) | Δ gain ±1,5 | Δ gain ±2,0 |
|---|---|---|---|---|---|---|
| `retrace_ratio` | Q4 − Q1 | +0,7 pts (3.0/6) | +5,1 pts (5.0/6) | 0,48 (6.0/6) | +3,5 pts (5.0/6) | +2,5 pts (4.0/6) |
| `obs_dist_seg_atr` | Q4 − Q1 | −0,7 pts (3.0/6) | −0,1 pts (4.0/6) | −0,03 (3.0/6) | +3,0 pts (4.0/6) | +0,5 pts (3.0/6) |
| `obs_lag_seg_bars` | Q4 − Q1 | +0,3 pts (3.0/6) | −0,7 pts (2.0/6) | −0,05 (4.0/6) | −0,3 pts (4.0/6) | +0,7 pts (4.0/6) |
| `x1_already_flipped_at_t` | Vrai − Faux | +0,1 pts (3.0/6) | +0,3 pts (2.0/6) | 0,02 (3.0/6) | +0,1 pts (3.0/6) | +1,6 pts (5.0/6) |
| `nis_z_100` | Q4 − Q1 | −4,7 pts (4.0/6) | −2,8 pts (4.0/6) | −0,28 (4.0/6) | −1,2 pts (4.0/6) | −4,0 pts (4.0/6) |
| `nis_z_100_seg_max` | Q4 − Q1 | −5,4 pts (6.0/6) | −1,6 pts (4.0/6) | −0,16 (3.0/6) | −1,7 pts (4.0/6) | −1,6 pts (3.0/6) |
| `cycle_seg_div_atr` | >0 − 0 | −1,3 pts (5.0/6) | +5,2 pts (6.0/6) | 0,42 (5.0/6) | −1,2 pts (4.0/6) | −1,1 pts (4.0/6) |
| `A_vol` | Q4 − Q1 | −5,7 pts (6.0/6) | −5,1 pts (5.0/6) | −0,45 (4.0/6) | −3,5 pts (5.0/6) | −5,5 pts (5.0/6) |
| `decel_ratio` | Q4 − Q1 | −2,4 pts (4.0/6) | −0,4 pts (2.0/6) | 0,03 (3.0/6) | −0,8 pts (3.0/6) | −4,1 pts (5.0/6) |
| `log_R_rel` | Q4 − Q1 | −3,1 pts (4.0/6) | +0,1 pts (3.0/6) | −0,01 (3.0/6) | −0,6 pts (4.0/6) | −0,5 pts (3.0/6) |
| `leg_atr` | Q4 − Q1 | −1,9 pts (4.0/6) | −0,4 pts (5.0/6) | −0,04 (5.0/6) | +0,3 pts (2.0/6) | +0,8 pts (2.0/6) |
| `prev_seg_len` | Q4 − Q1 | −3,5 pts (3.0/6) | −3,0 pts (4.0/6) | −0,25 (5.0/6) | −3,8 pts (4.0/6) | −1,1 pts (3.0/6) |
| `saturation` | Q4 − Q1 | −2,4 pts (4.0/6) | −4,5 pts (5.0/6) | −0,39 (5.0/6) | −1,2 pts (5.0/6) | −3,6 pts (4.0/6) |
| `n_short_seg_48` | ≥1 − 0 | +0,7 pts (3.0/6) | +3,2 pts (5.0/6) | 0,33 (6.0/6) | +0,2 pts (4.0/6) | +0,3 pts (5.0/6) |
| `run_rank` | >1 − 1 | +2,8 pts (5.0/6) | +4,4 pts (5.0/6) | 0,38 (5.0/6) | +2,6 pts (5.0/6) | −0,3 pts (4.0/6) |

## D. Univarié détaillé

| Descripteur | Classe | Bornes | n | MFE>MAE H26 Tous | Long | Short | Gain ±1,5 Tous | Long | Short |
|---|---|---|---|---|---|---|---|---|---|
| `retrace_ratio` | Q1 | [0 ; 0.405] | 1 824 | 47,4 % | 47,5 % | 47,4 % | 48,3 % | 47,3 % | 49,1 % |
| `retrace_ratio` | Q2 | [0.405 ; 0.621] | 1 824 | 50,3 % | 51,1 % | 49,5 % | 51,1 % | 52,4 % | 49,7 % |
| `retrace_ratio` | Q3 | [0.621 ; 0.845] | 1 825 | 50,7 % | 50,4 % | 51,1 % | 51,5 % | 51,2 % | 51,9 % |
| `retrace_ratio` | Q4 | [0.845 ; 3.45] | 1 823 | 50,1 % | 48,1 % | 52,5 % | 49,9 % | 47,6 % | 52,6 % |
| `obs_dist_seg_atr` | Q1 | [0 ; 1.26] | 1 824 | 49,7 % | 50,1 % | 49,3 % | 49,6 % | 50,4 % | 49,0 % |
| `obs_dist_seg_atr` | Q2 | [1.26 ; 1.77] | 1 824 | 50,9 % | 52,6 % | 49,2 % | 51,9 % | 52,2 % | 51,6 % |
| `obs_dist_seg_atr` | Q3 | [1.77 ; 2.39] | 1 824 | 50,9 % | 49,7 % | 52,5 % | 50,4 % | 50,0 % | 50,8 % |
| `obs_dist_seg_atr` | Q4 | [2.39 ; 7.72] | 1 824 | 47,2 % | 45,3 % | 49,2 % | 49,1 % | 46,5 % | 52,0 % |
| `obs_lag_seg_bars` | Q1 | [0 ; 4] | 2 686 | 50,4 % | 50,1 % | 50,6 % | 51,0 % | 50,5 % | 51,5 % |
| `obs_lag_seg_bars` | Q2 | [4 ; 5] | 1 193 | 50,7 % | 49,9 % | 51,6 % | 50,2 % | 47,4 % | 53,2 % |
| `obs_lag_seg_bars` | Q3 | [5 ; 7] | 2 153 | 49,0 % | 49,6 % | 48,2 % | 49,3 % | 50,4 % | 48,1 % |
| `obs_lag_seg_bars` | Q4 | [7 ; 18] | 1 264 | 48,3 % | 46,7 % | 49,9 % | 50,2 % | 49,1 % | 51,2 % |
| `x1_already_flipped_at_t` | Faux | x1 encore opposé | 3 515 | 50,1 % | 50,3 % | 49,8 % | 51,0 % | 51,3 % | 50,7 % |
| `x1_already_flipped_at_t` | Vrai | x1 déjà retourné | 3 781 | 49,3 % | 48,4 % | 50,1 % | 49,5 % | 48,3 % | 50,8 % |
| `nis_z_100` | Q1 | [-1.06 ; -0.324] | 1 824 | 49,9 % | 48,8 % | 51,1 % | 50,3 % | 49,8 % | 50,8 % |
| `nis_z_100` | Q2 | [-0.324 ; 0.188] | 1 824 | 52,0 % | 51,7 % | 52,3 % | 51,9 % | 52,6 % | 51,2 % |
| `nis_z_100` | Q3 | [0.188 ; 1.22] | 1 824 | 50,3 % | 52,4 % | 48,2 % | 51,3 % | 51,0 % | 51,6 % |
| `nis_z_100` | Q4 | [1.22 ; 9.55] | 1 824 | 46,3 % | 44,3 % | 48,3 % | 47,4 % | 45,3 % | 49,5 % |
| `nis_z_100_seg_max` | Q1 | [-0.88 ; 0.0362] | 1 824 | 48,6 % | 46,5 % | 50,7 % | 49,1 % | 46,3 % | 51,9 % |
| `nis_z_100_seg_max` | Q2 | [0.0362 ; 0.771] | 1 824 | 52,2 % | 53,9 % | 50,4 % | 52,2 % | 54,0 % | 50,4 % |
| `nis_z_100_seg_max` | Q3 | [0.771 ; 2.18] | 1 824 | 49,8 % | 49,9 % | 49,7 % | 51,1 % | 51,9 % | 50,4 % |
| `nis_z_100_seg_max` | Q4 | [2.18 ; 9.92] | 1 824 | 48,0 % | 46,9 % | 49,0 % | 48,4 % | 46,5 % | 50,3 % |
| `cycle_seg_div_atr` | 0 | le segment porte l'extremum du cycle | 6 295 | 49,1 % | 48,9 % | 49,3 % | 50,2 % | 49,5 % | 50,9 % |
| `cycle_seg_div_atr` | >0 | plus bas plus haut / plus haut plus bas | 1 001 | 53,1 % | 52,0 % | 54,5 % | 50,4 % | 51,0 % | 49,7 % |
| `A_vol` | Q1 | [0.0603 ; 0.396] | 1 824 | 49,8 % | 46,4 % | 53,2 % | 50,2 % | 46,7 % | 53,7 % |
| `A_vol` | Q2 | [0.396 ; 0.548] | 1 824 | 49,6 % | 50,8 % | 48,5 % | 50,4 % | 51,6 % | 49,3 % |
| `A_vol` | Q3 | [0.548 ; 0.724] | 1 824 | 49,7 % | 49,5 % | 49,9 % | 50,4 % | 51,1 % | 49,8 % |
| `A_vol` | Q4 | [0.724 ; 3.05] | 1 824 | 49,4 % | 50,7 % | 48,2 % | 49,9 % | 49,5 % | 50,2 % |
| `decel_ratio` | Q1 | [0.112 ; 0.744] | 1 824 | 49,5 % | 47,1 % | 51,7 % | 50,8 % | 49,4 % | 52,0 % |
| `decel_ratio` | Q2 | [0.744 ; 0.87] | 1 824 | 49,0 % | 50,4 % | 47,5 % | 49,6 % | 49,0 % | 50,3 % |
| `decel_ratio` | Q3 | [0.87 ; 0.981] | 1 824 | 49,1 % | 49,1 % | 49,2 % | 49,8 % | 50,1 % | 49,5 % |
| `decel_ratio` | Q4 | [0.981 ; 1.63] | 1 824 | 51,0 % | 50,6 % | 51,3 % | 50,7 % | 50,3 % | 51,2 % |
| `log_R_rel` | Q1 | [-1.24 ; -0.322] | 1 824 | 50,4 % | 51,4 % | 49,3 % | 50,1 % | 50,4 % | 49,7 % |
| `log_R_rel` | Q2 | [-0.322 ; -0.118] | 1 824 | 50,5 % | 48,7 % | 52,3 % | 52,3 % | 50,9 % | 53,7 % |
| `log_R_rel` | Q3 | [-0.118 ; 0.112] | 1 824 | 49,8 % | 50,7 % | 48,9 % | 50,6 % | 50,6 % | 50,6 % |
| `log_R_rel` | Q4 | [0.112 ; 0.758] | 1 824 | 47,9 % | 46,5 % | 49,3 % | 48,0 % | 46,9 % | 49,1 % |
| `leg_atr` | Q1 | [0.76 ; 2.17] | 1 824 | 50,8 % | 51,7 % | 49,9 % | 51,0 % | 51,3 % | 50,7 % |
| `leg_atr` | Q2 | [2.17 ; 2.82] | 1 824 | 51,4 % | 51,4 % | 51,4 % | 51,5 % | 51,4 % | 51,5 % |
| `leg_atr` | Q3 | [2.82 ; 3.94] | 1 824 | 49,2 % | 49,3 % | 49,1 % | 49,9 % | 50,1 % | 49,7 % |
| `leg_atr` | Q4 | [3.94 ; 13.8] | 1 824 | 47,3 % | 44,8 % | 49,5 % | 48,6 % | 45,9 % | 51,1 % |
| `prev_seg_len` | Q1 | [6 ; 8] | 2 345 | 50,8 % | 51,3 % | 50,3 % | 51,3 % | 51,5 % | 51,1 % |
| `prev_seg_len` | Q2 | [8 ; 10] | 1 801 | 50,5 % | 49,0 % | 52,0 % | 50,6 % | 49,1 % | 52,0 % |
| `prev_seg_len` | Q3 | [10 ; 13] | 1 626 | 49,8 % | 49,6 % | 49,9 % | 51,5 % | 50,6 % | 52,3 % |
| `prev_seg_len` | Q4 | [13 ; 54] | 1 524 | 46,8 % | 46,3 % | 47,2 % | 46,9 % | 46,4 % | 47,3 % |
| `saturation` | Q1 | [0 ; 0.1] | 1 932 | 50,6 % | 49,7 % | 51,4 % | 51,2 % | 51,1 % | 51,4 % |
| `saturation` | Q2 | [0.1 ; 0.182] | 1 744 | 50,5 % | 50,5 % | 50,4 % | 50,4 % | 50,7 % | 50,0 % |
| `saturation` | Q3 | [0.182 ; 0.286] | 1 802 | 50,7 % | 50,1 % | 51,2 % | 50,9 % | 50,4 % | 51,4 % |
| `saturation` | Q4 | [0.286 ; 0.684] | 1 818 | 46,9 % | 46,9 % | 46,9 % | 48,4 % | 46,4 % | 50,2 % |
| `n_short_seg_48` | 0 | aucun segment court | 4 059 | 49,1 % | 49,7 % | 48,6 % | 50,3 % | 49,8 % | 50,7 % |
| `n_short_seg_48` | ≥1 | au moins un | 3 237 | 50,3 % | 48,9 % | 51,7 % | 50,2 % | 49,5 % | 50,9 % |
| `run_rank` | 1 | rang 1 (flip) | 6 037 | 49,5 % | 49,7 % | 49,2 % | 50,3 % | 50,3 % | 50,3 % |
| `run_rank` | >1 | répétition | 1 259 | 50,6 % | 47,4 % | 53,6 % | 50,0 % | 46,9 % | 52,9 % |

## E. Familles et strates

- **F1** : F1 Essoufflement d'une tendance ample (leg ≥ P50, retrace < 0,50)
- **F2a** : F2a Retournement intermédiaire, jambe ample (0,50 ≤ retrace < 0,85, leg ≥ P50)
- **F2b** : F2b Retournement intermédiaire, jambe courte (0,50 ≤ retrace < 0,85, leg < P50)
- **F3** : F3 Sortie de range (leg < P50, retrace ≥ 0,85)
- **F4** : F4 Climax, grand segment ravalé (leg ≥ P50, retrace ≥ 0,85)
- **F5** : F5 Résidu : jambe courte peu retracée (leg < P50, retrace < 0,50)
- **F3 pur** : F3 avec `retrace_ratio` ≥ 1,00.

Taux de gain « strict » : hors timeouts, barres ambiguës comptées en échec. L'extremum tenu est donné à titre d'information (cible interdite, `RESEARCH_INSIGHTS.md` I-M1).

### Tous

| Strate | n (part) | Stop implicite P50 (ATR) | MFE>MAE H6 | H26 | H48 | Asym H26 P50 | Gain ±1,0 | Gain ±1,5 [IC 95 %] | Gain ±2,0 | Timeout ±2,0 | Info : extremum tenu | Années gain ±1,5 > 50 % |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Tous | 7 296 (100,0 %) | 1,77 | 51,4 % | 49,7 % | 50,4 % | −0,02 | 49,5 % | 50,2 % [49,1 % ; 51,4 %] | 50,1 % | 3,8 % | 63,9 % | 4/6 |
| F1 | 1 869 (25,6 %) | 1,47 | 51,4 % | 48,4 % | 50,0 % | −0,12 | 47,6 % | 48,6 % [46,3 % ; 50,9 %] | 48,8 % | 3,6 % | 57,1 % | 1/6 |
| F2a | 1 303 (17,9 %) | 2,37 | 50,6 % | 48,1 % | 50,0 % | −0,17 | 46,8 % | 49,9 % [47,2 % ; 52,6 %] | 50,2 % | 5,2 % | 78,4 % | 2/6 |
| F2b | 1 592 (21,8 %) | 1,47 | 51,8 % | 51,8 % | 51,7 % | 0,17 | 51,5 % | 52,0 % [49,5 % ; 54,4 %] | 50,8 % | 3,1 % | 58,3 % | 3/6 |
| F3 | 1 315 (18,0 %) | 2,23 | 50,1 % | 50,7 % | 50,8 % | 0,09 | 50,3 % | 49,8 % [47,1 % ; 52,5 %] | 50,3 % | 2,7 % | 73,2 % | 3/6 |
| F3 pur | 767 (10,5 %) | 2,46 | 50,5 % | 49,7 % | 49,7 % | −0,02 | 51,0 % | 49,0 % [45,4 % ; 52,5 %] | 48,5 % | 1,4 % | 75,7 % | 2/6 |
| F4 | 476 (6,5 %) | 3,39 | 49,4 % | 47,9 % | 45,6 % | −0,21 | 48,8 % | 49,9 % [45,4 % ; 54,4 %] | 49,6 % | 5,5 % | 89,9 % | 2/6 |
| F5 | 741 (10,2 %) | 0,80 | 56,0 % | 50,3 % | 51,2 % | 0,04 | 53,6 % | 52,2 % [48,6 % ; 55,8 %] | 52,2 % | 4,3 % | 34,7 % | 4/6 |
| F1 · x1 déjà retourné | 568 (7,8 %) | 1,70 | 48,8 % | 45,2 % | 46,3 % | −0,26 | 44,5 % | 46,7 % [42,6 % ; 50,8 %] | 46,9 % | 5,1 % | 65,1 % | 1/6 |
| F1 · x1 encore opposé | 1 301 (17,8 %) | 1,34 | 52,6 % | 49,7 % | 51,7 % | −0,01 | 48,9 % | 49,4 % [46,7 % ; 52,1 %] | 49,5 % | 3,0 % | 53,7 % | 3/6 |
| F3 · x1 déjà retourné | 1 087 (14,9 %) | 2,28 | 50,4 % | 50,5 % | 50,8 % | 0,08 | 51,1 % | 49,9 % [46,9 % ; 52,9 %] | 50,2 % | 2,2 % | 73,7 % | 3/6 |
| F3 · x1 encore opposé | 228 (3,1 %) | 2,00 | 48,7 % | 51,8 % | 50,9 % | 0,23 | 46,5 % | 49,3 % [42,9 % ; 55,8 %] | 50,7 % | 4,8 % | 71,1 % | 1/6 |
| Rang 1 | 6 037 (82,7 %) | 1,73 | 51,3 % | 49,5 % | 50,4 % | −0,04 | 49,6 % | 50,3 % [49,0 % ; 51,6 %] | 50,3 % | 3,8 % | 62,9 % | 3/6 |
| Répétition | 1 259 (17,3 %) | 1,93 | 52,3 % | 50,6 % | 50,2 % | 0,06 | 49,2 % | 50,0 % [47,2 % ; 52,8 %] | 49,3 % | 4,1 % | 69,0 % | 2/6 |
| Cycle : segment = extremum | 6 295 (86,3 %) | 1,81 | 51,6 % | 49,1 % | 50,2 % | −0,08 | 49,5 % | 50,2 % [49,0 % ; 51,4 %] | 50,0 % | 3,8 % | 64,7 % | 4/6 |
| Cycle : plus bas plus haut / plus haut plus bas | 1 001 (13,7 %) | 1,54 | 50,2 % | 53,1 % | 51,7 % | 0,29 | 49,6 % | 50,4 % [47,3 % ; 53,5 %] | 50,8 % | 3,9 % | 58,8 % | 4/6 |
| n_short_seg_48 = 0 | 4 059 (55,6 %) | 1,76 | 51,1 % | 49,1 % | 49,9 % | −0,07 | 49,1 % | 50,3 % [48,7 % ; 51,8 %] | 50,1 % | 3,5 % | 63,9 % | 3/6 |
| n_short_seg_48 ≥ 1 | 3 237 (44,4 %) | 1,78 | 51,9 % | 50,3 % | 50,9 % | 0,03 | 50,0 % | 50,2 % [48,5 % ; 51,9 %] | 50,2 % | 4,3 % | 63,9 % | 4/6 |
| A_vol Q1 | 1 824 (25,0 %) | 1,74 | 52,9 % | 49,8 % | 50,6 % | −0,04 | 50,2 % | 50,2 % [47,9 % ; 52,5 %] | 51,0 % | 3,3 % | 63,9 % | 2/6 |
| A_vol Q2 | 1 824 (25,0 %) | 1,81 | 51,8 % | 49,6 % | 50,3 % | −0,02 | 49,5 % | 50,4 % [48,1 % ; 52,7 %] | 50,3 % | 3,5 % | 65,7 % | 3/6 |
| A_vol Q3 | 1 824 (25,0 %) | 1,82 | 52,1 % | 49,7 % | 49,7 % | −0,01 | 49,9 % | 50,4 % [48,1 % ; 52,7 %] | 50,0 % | 4,5 % | 64,5 % | 4/6 |
| A_vol Q4 | 1 824 (25,0 %) | 1,71 | 48,9 % | 49,4 % | 51,0 % | −0,04 | 48,4 % | 49,9 % [47,6 % ; 52,2 %] | 49,3 % | 4,1 % | 61,6 % | 2/6 |

### Long

| Strate | n (part) | Stop implicite P50 (ATR) | MFE>MAE H6 | H26 | H48 | Asym H26 P50 | Gain ±1,0 | Gain ±1,5 [IC 95 %] | Gain ±2,0 | Timeout ±2,0 | Info : extremum tenu | Années gain ±1,5 > 50 % |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Tous | 3 628 (49,7 %) | 1,86 | 50,9 % | 49,3 % | 50,6 % | −0,06 | 48,9 % | 49,7 % [48,1 % ; 51,3 %] | 49,9 % | 4,1 % | 65,1 % | 3/6 |
| F1 | 853 (11,7 %) | 1,54 | 52,8 % | 48,3 % | 51,0 % | −0,11 | 47,7 % | 47,6 % [44,3 % ; 51,0 %] | 47,9 % | 3,9 % | 58,5 % | 1/6 |
| F2a | 702 (9,6 %) | 2,35 | 49,0 % | 47,3 % | 49,3 % | −0,22 | 46,6 % | 49,6 % [45,8 % ; 53,3 %] | 50,2 % | 6,1 % | 78,5 % | 2/6 |
| F2b | 794 (10,9 %) | 1,51 | 52,5 % | 53,1 % | 54,8 % | 0,27 | 52,8 % | 53,7 % [50,2 % ; 57,1 %] | 51,9 % | 3,0 % | 59,1 % | 5/6 |
| F3 | 705 (9,7 %) | 2,22 | 48,4 % | 49,9 % | 49,6 % | −0,04 | 47,7 % | 48,2 % [44,5 % ; 51,9 %] | 49,4 % | 3,3 % | 71,3 % | 2/6 |
| F3 pur | 373 (5,1 %) | 2,44 | 48,3 % | 47,7 % | 47,7 % | −0,36 | 48,0 % | 46,8 % [41,8 % ; 51,9 %] | 46,9 % | 1,1 % | 71,6 % | 3/6 |
| F4 | 258 (3,5 %) | 3,36 | 45,7 % | 42,6 % | 41,9 % | −0,64 | 44,0 % | 45,3 % [39,3 % ; 51,4 %] | 47,3 % | 5,0 % | 88,0 % | 2/6 |
| F5 | 316 (4,3 %) | 0,82 | 56,3 % | 51,3 % | 50,8 % | 0,10 | 54,3 % | 52,5 % [47,0 % ; 58,0 %] | 52,1 % | 3,5 % | 35,8 % | 3/6 |
| F1 · x1 déjà retourné | 258 (3,5 %) | 1,80 | 48,4 % | 44,2 % | 44,2 % | −0,42 | 44,7 % | 46,2 % [40,2 % ; 52,4 %] | 43,3 % | 5,0 % | 67,4 % | 1/6 |
| F1 · x1 encore opposé | 595 (8,2 %) | 1,42 | 54,6 % | 50,1 % | 53,9 % | 0,02 | 49,0 % | 48,2 % [44,2 % ; 52,3 %] | 49,9 % | 3,4 % | 54,6 % | 1/6 |
| F3 · x1 déjà retourné | 573 (7,9 %) | 2,25 | 48,7 % | 49,7 % | 49,0 % | −0,05 | 48,8 % | 47,9 % [43,8 % ; 52,0 %] | 48,7 % | 2,8 % | 71,4 % | 2/6 |
| F3 · x1 encore opposé | 132 (1,8 %) | 2,08 | 47,0 % | 50,8 % | 52,3 % | 0,17 | 43,2 % | 49,6 % [41,2 % ; 58,1 %] | 52,8 % | 5,3 % | 71,2 % | 2/6 |
| Rang 1 | 3 018 (41,4 %) | 1,82 | 51,1 % | 49,7 % | 51,1 % | −0,02 | 49,4 % | 50,3 % [48,5 % ; 52,1 %] | 50,2 % | 3,8 % | 64,4 % | 3/6 |
| Répétition | 610 (8,4 %) | 2,02 | 50,3 % | 47,4 % | 48,0 % | −0,20 | 46,7 % | 46,9 % [42,9 % ; 50,9 %] | 48,4 % | 5,1 % | 68,5 % | 1/6 |
| Cycle : segment = extremum | 3 086 (42,3 %) | 1,91 | 51,1 % | 48,9 % | 50,5 % | −0,11 | 48,9 % | 49,5 % [47,7 % ; 51,2 %] | 49,5 % | 4,1 % | 65,9 % | 3/6 |
| Cycle : plus bas plus haut / plus haut plus bas | 542 (7,4 %) | 1,62 | 49,8 % | 52,0 % | 51,0 % | 0,25 | 49,0 % | 51,0 % [46,8 % ; 55,2 %] | 52,0 % | 3,9 % | 60,5 % | 4/6 |
| n_short_seg_48 = 0 | 2 013 (27,6 %) | 1,88 | 50,6 % | 49,7 % | 50,8 % | −0,03 | 48,2 % | 49,8 % [47,7 % ; 52,0 %] | 49,9 % | 3,9 % | 65,8 % | 2/6 |
| n_short_seg_48 ≥ 1 | 1 615 (22,1 %) | 1,85 | 51,4 % | 48,9 % | 50,2 % | −0,13 | 49,8 % | 49,5 % [47,1 % ; 52,0 %] | 49,8 % | 4,3 % | 64,3 % | 3/6 |
| A_vol Q1 | 909 (12,5 %) | 1,80 | 50,7 % | 46,4 % | 47,9 % | −0,34 | 47,5 % | 46,7 % [43,4 % ; 49,9 %] | 48,4 % | 3,6 % | 64,4 % | 1/6 |
| A_vol Q2 | 910 (12,5 %) | 1,89 | 52,7 % | 50,8 % | 51,5 % | 0,07 | 49,0 % | 51,6 % [48,3 % ; 54,8 %] | 49,9 % | 3,7 % | 67,8 % | 4/6 |
| A_vol Q3 | 913 (12,5 %) | 1,92 | 51,8 % | 49,5 % | 49,4 % | −0,01 | 50,7 % | 51,1 % [47,8 % ; 54,3 %] | 50,7 % | 4,7 % | 65,0 % | 4/6 |
| A_vol Q4 | 896 (12,3 %) | 1,83 | 48,4 % | 50,7 % | 53,5 % | 0,09 | 48,5 % | 49,5 % [46,3 % ; 52,8 %] | 50,5 % | 4,1 % | 63,3 % | 3/6 |

### Short

| Strate | n (part) | Stop implicite P50 (ATR) | MFE>MAE H6 | H26 | H48 | Asym H26 P50 | Gain ±1,0 | Gain ±1,5 [IC 95 %] | Gain ±2,0 | Timeout ±2,0 | Info : extremum tenu | Années gain ±1,5 > 50 % |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Tous | 3 668 (50,3 %) | 1,68 | 51,9 % | 50,0 % | 50,2 % | 0,00 | 50,1 % | 50,8 % [49,1 % ; 52,4 %] | 50,4 % | 3,6 % | 62,8 % | 4/6 |
| F1 | 1 016 (13,9 %) | 1,40 | 50,3 % | 48,4 % | 49,2 % | −0,14 | 47,5 % | 49,4 % [46,3 % ; 52,5 %] | 49,4 % | 3,4 % | 56,0 % | 1/6 |
| F2a | 601 (8,2 %) | 2,39 | 52,4 % | 49,1 % | 50,9 % | −0,08 | 47,0 % | 50,3 % [46,2 % ; 54,3 %] | 50,2 % | 4,2 % | 78,2 % | 3/6 |
| F2b | 798 (10,9 %) | 1,45 | 51,0 % | 50,4 % | 48,7 % | 0,04 | 50,3 % | 50,3 % [46,8 % ; 53,8 %] | 49,7 % | 3,3 % | 57,5 % | 3/6 |
| F3 | 610 (8,4 %) | 2,24 | 52,1 % | 51,6 % | 52,2 % | 0,23 | 53,3 % | 51,7 % [47,7 % ; 55,6 %] | 51,3 % | 2,0 % | 75,4 % | 3/6 |
| F3 pur | 394 (5,4 %) | 2,47 | 52,5 % | 51,7 % | 51,7 % | 0,22 | 53,8 % | 51,0 % [46,1 % ; 55,9 %] | 50,1 % | 1,8 % | 79,7 % | 3/6 |
| F4 | 218 (3,0 %) | 3,45 | 53,7 % | 54,1 % | 50,0 % | 0,34 | 54,6 % | 55,3 % [48,7 % ; 61,8 %] | 52,2 % | 6,0 % | 92,2 % | 5/6 |
| F5 | 425 (5,8 %) | 0,77 | 55,8 % | 49,6 % | 51,5 % | −0,01 | 53,1 % | 51,9 % [47,1 % ; 56,6 %] | 52,2 % | 4,9 % | 33,9 % | 4/6 |
| F1 · x1 déjà retourné | 310 (4,2 %) | 1,63 | 49,0 % | 46,1 % | 48,1 % | −0,21 | 44,3 % | 47,0 % [41,5 % ; 52,7 %] | 50,0 % | 5,2 % | 63,2 % | 1/6 |
| F1 · x1 encore opposé | 706 (9,7 %) | 1,27 | 50,8 % | 49,4 % | 49,7 % | −0,04 | 48,9 % | 50,4 % [46,7 % ; 54,1 %] | 49,2 % | 2,7 % | 52,8 % | 3/6 |
| F3 · x1 déjà retourné | 514 (7,0 %) | 2,33 | 52,3 % | 51,3 % | 52,8 % | 0,23 | 53,7 % | 52,1 % [47,8 % ; 56,4 %] | 52,0 % | 1,6 % | 76,3 % | 3/6 |
| F3 · x1 encore opposé | 96 (1,3 %) | 1,91 | 51,0 % | 53,1 % | 49,0 % | 0,23 | 51,0 % | 48,9 % [39,1 % ; 58,9 %] | 47,8 % | 4,2 % | 70,8 % | 1/6 |
| Rang 1 | 3 019 (41,4 %) | 1,65 | 51,4 % | 49,2 % | 49,8 % | −0,06 | 49,8 % | 50,3 % [48,5 % ; 52,1 %] | 50,5 % | 3,7 % | 61,3 % | 4/6 |
| Répétition | 649 (8,9 %) | 1,83 | 54,2 % | 53,6 % | 52,2 % | 0,32 | 51,5 % | 52,9 % [49,0 % ; 56,7 %] | 50,2 % | 3,2 % | 69,5 % | 5/6 |
| Cycle : segment = extremum | 3 209 (44,0 %) | 1,71 | 52,1 % | 49,3 % | 49,9 % | −0,05 | 50,0 % | 50,9 % [49,2 % ; 52,6 %] | 50,6 % | 3,6 % | 63,6 % | 3/6 |
| Cycle : plus bas plus haut / plus haut plus bas | 459 (6,3 %) | 1,47 | 50,8 % | 54,5 % | 52,5 % | 0,37 | 50,3 % | 49,7 % [45,1 % ; 54,2 %] | 49,4 % | 3,9 % | 56,9 % | 3/6 |
| n_short_seg_48 = 0 | 2 046 (28,0 %) | 1,65 | 51,6 % | 48,6 % | 49,0 % | −0,14 | 50,0 % | 50,7 % [48,5 % ; 52,8 %] | 50,3 % | 3,1 % | 62,1 % | 3/6 |
| n_short_seg_48 ≥ 1 | 1 622 (22,2 %) | 1,72 | 52,3 % | 51,7 % | 51,7 % | 0,18 | 50,2 % | 50,9 % [48,4 % ; 53,3 %] | 50,6 % | 4,3 % | 63,6 % | 4/6 |
| A_vol Q1 | 915 (12,5 %) | 1,66 | 55,1 % | 53,2 % | 53,2 % | 0,30 | 52,9 % | 53,7 % [50,4 % ; 56,9 %] | 53,6 % | 3,0 % | 63,5 % | 6/6 |
| A_vol Q2 | 914 (12,5 %) | 1,73 | 50,9 % | 48,5 % | 49,1 % | −0,10 | 50,0 % | 49,3 % [46,0 % ; 52,5 %] | 50,6 % | 3,2 % | 63,7 % | 2/6 |
| A_vol Q3 | 911 (12,5 %) | 1,71 | 52,5 % | 49,9 % | 49,9 % | −0,01 | 49,2 % | 49,8 % [46,6 % ; 53,1 %] | 49,3 % | 4,3 % | 64,0 % | 3/6 |
| A_vol Q4 | 928 (12,7 %) | 1,60 | 49,4 % | 48,2 % | 48,5 % | −0,15 | 48,2 % | 50,2 % [47,0 % ; 53,4 %] | 48,1 % | 4,0 % | 60,0 % | 1/6 |

## F. Strates à asymétrie négative en Long ET en Short

Condition : médiane de Asym_H < 0 pour au moins un horizon et taux de gain strict < 50 % pour au moins une barrière (±1,5 ou ±2,0), dans les deux sens.

| Strate | n Long | n Short | H où Asym < 0 | Barrières < 50 % | < 50 % (IC Wilson) | Gain ±1,5 Long | Gain ±1,5 Short | Asym H26 Long | Asym H26 Short |
|---|---|---|---|---|---|---|---|---|---|
| retrace_ratio = Q1 | 773 | 1 051 | 26, 48 | 1p5, 2p0 | — | 47,3 % | 49,1 % | −0,16 | −0,15 |
| nis_z_100 = Q4 | 894 | 930 | 6, 13, 26, 48 | 1p5, 2p0 | — | 45,3 % | 49,5 % | −0,51 | −0,14 |
| nis_z_100_seg_max = Q4 | 908 | 916 | 13, 26 | 2p0 | — | 46,5 % | 50,3 % | −0,27 | −0,05 |
| decel_ratio = Q3 | 915 | 909 | 6, 26 | 2p0 | — | 50,1 % | 49,5 % | −0,13 | −0,05 |
| log_R_rel = Q4 | 908 | 916 | 26 | 1p5, 2p0 | — | 46,9 % | 49,1 % | −0,27 | −0,05 |
| prev_seg_len = Q4 | 732 | 792 | 26 | 1p5, 2p0 | — | 46,4 % | 47,3 % | −0,28 | −0,20 |
| saturation = Q4 | 874 | 944 | 26 | 2p0 | — | 46,4 % | 50,2 % | −0,24 | −0,25 |
| F1 | 853 | 1 016 | 26 | 1p5, 2p0 | — | 47,6 % | 49,4 % | −0,11 | −0,14 |
| F1 · x1 déjà retourné | 258 | 310 | 6, 13, 26, 48 | 1p5 | — | 46,2 % | 47,0 % | −0,42 | −0,21 |

## G. Stabilité annuelle : gain strict ±1,5 ATR par famille

### Long

| Famille | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 |
|---|---|---|---|---|---|---|
| Tous | 51,8 % | 46,4 % | 46,5 % | 53,1 % | 51,7 % | 49,1 % |
| F1 | 45,1 % | 43,5 % | 46,2 % | 53,5 % | 48,5 % | 49,1 % |
| F2a | 46,9 % | 45,6 % | 46,3 % | 52,8 % | 56,3 % | 49,1 % |
| F2b | 58,1 % | 51,6 % | 50,7 % | 58,0 % | 54,2 % | 47,9 % |
| F3 | 54,9 % | 45,6 % | 44,9 % | 45,2 % | 47,1 % | 52,2 % |
| F3 pur | 55,4 % | 37,0 % | 50,9 % | 41,2 % | 49,1 % | 50,7 % |
| F4 | 51,5 % | 38,5 % | 38,3 % | 45,5 % | 56,8 % | 46,5 % |
| F5 | 50,8 % | 55,8 % | 47,5 % | 63,5 % | 48,0 % | 47,5 % |

### Short

| Famille | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 |
|---|---|---|---|---|---|---|
| Tous | 48,6 % | 48,6 % | 50,1 % | 53,8 % | 51,4 % | 51,9 % |
| F1 | 43,3 % | 47,7 % | 47,1 % | 61,6 % | 49,7 % | 48,5 % |
| F2a | 46,3 % | 41,7 % | 53,2 % | 52,1 % | 55,7 % | 48,7 % |
| F2b | 57,7 % | 45,7 % | 46,1 % | 51,2 % | 52,5 % | 48,5 % |
| F3 | 47,6 % | 57,0 % | 49,0 % | 49,6 % | 51,5 % | 54,4 % |
| F3 pur | 42,2 % | 60,6 % | 44,8 % | 47,5 % | 54,5 % | 52,8 % |
| F4 | 36,0 % | 59,4 % | 58,7 % | 53,1 % | 57,1 % | 62,9 % |
| F5 | 51,4 % | 46,4 % | 56,2 % | 51,5 % | 44,4 % | 61,8 % |

## H. Timing ou dérive ? Décomposition par strate (sans placebo)

ΔL et ΔS : variation médiane du prix de open[t+1] à close[t+H] (ATR14(t), non orientée), après les signaux Long et après les signaux Short. Timing = (ΔL − ΔS) / 2 : part où le prix suit le sens du signal. Dérive = (ΔL + ΔS) / 2 : part commune aux deux sens (marché). Dernières colonnes : part MFE > \|MAE\|, Long et Short réunis, IC de Wilson à 95 %.

| Strate | n Long | n Short | Timing H26 | Dérive H26 | Timing H48 | Dérive H48 | MFE>MAE H6 [IC] | MFE>MAE H26 [IC] |
|---|---|---|---|---|---|---|---|---|
| Tous | 3 628 | 3 668 | −0,02 | 0,08 | 0,01 | 0,21 | 51,4 % [50,3 % ; 52,6 %] | 49,7 % [48,5 % ; 50,8 %] |
| F1 | 853 | 1 016 | 0,14 | 0,22 | 0,13 | 0,21 | 51,4 % [49,2 % ; 53,7 %] | 48,4 % [46,1 % ; 50,6 %] |
| F1 · x1 déjà retourné | 258 | 310 | −0,15 | 0,05 | −0,08 | 0,06 | 48,8 % [44,7 % ; 52,9 %] | 45,2 % [41,2 % ; 49,4 %] |
| F2a | 702 | 601 | −0,02 | 0,01 | 0,05 | 0,22 | 50,6 % [47,9 % ; 53,3 %] | 48,1 % [45,4 % ; 50,8 %] |
| F2b | 794 | 798 | 0,02 | 0,16 | −0,01 | 0,35 | 51,8 % [49,3 % ; 54,2 %] | 51,8 % [49,3 % ; 54,2 %] |
| F3 | 705 | 610 | −0,12 | 0,04 | 0,03 | −0,05 | 50,1 % [47,4 % ; 52,8 %] | 50,7 % [48,0 % ; 53,4 %] |
| F3 pur | 373 | 394 | −0,29 | −0,06 | −0,04 | −0,02 | 50,5 % [46,9 % ; 54,0 %] | 49,7 % [46,2 % ; 53,3 %] |
| F4 | 258 | 218 | −0,44 | −0,21 | −0,51 | −0,03 | 49,4 % [44,9 % ; 53,8 %] | 47,9 % [43,4 % ; 52,4 %] |
| F5 | 316 | 425 | −0,04 | −0,08 | 0,06 | 0,19 | 56,0 % [52,4 % ; 59,5 %] | 50,3 % [46,7 % ; 53,9 %] |
| Rang 1 | 3 018 | 3 019 | −0,05 | 0,09 | −0,03 | 0,21 | 51,3 % [50,0 % ; 52,5 %] | 49,5 % [48,2 % ; 50,7 %] |
| Répétition | 610 | 649 | 0,10 | −0,02 | 0,17 | 0,14 | 52,3 % [49,6 % ; 55,1 %] | 50,6 % [47,8 % ; 53,4 %] |
| Cycle : plus bas plus haut / plus haut plus bas | 542 | 459 | −0,04 | 0,01 | −0,18 | 0,28 | 50,2 % [47,2 % ; 53,3 %] | 53,1 % [50,0 % ; 56,2 %] |
| A_vol Q1 | 909 | 915 | −0,10 | −0,13 | −0,01 | 0,03 | 52,9 % [50,6 % ; 55,2 %] | 49,8 % [47,5 % ; 52,1 %] |
| A_vol Q4 | 896 | 928 | 0,03 | 0,17 | −0,03 | 0,36 | 48,9 % [46,6 % ; 51,2 %] | 49,4 % [47,1 % ; 51,7 %] |
| nis_z_100 Q4 | 894 | 930 | −0,18 | 0,03 | −0,15 | 0,22 | 48,6 % [46,3 % ; 50,9 %] | 46,3 % [44,0 % ; 48,6 %] |
| prev_seg_len Q4 | 732 | 792 | 0,02 | 0,17 | 0,17 | 0,25 | 49,9 % [47,4 % ; 52,4 %] | 46,8 % [44,3 % ; 49,3 %] |
| saturation Q4 | 874 | 944 | −0,10 | 0,15 | −0,02 | 0,31 | 49,1 % [46,8 % ; 51,4 %] | 46,9 % [44,6 % ; 49,2 %] |
| retrace_ratio Q1 | 773 | 1 051 | 0,01 | 0,13 | 0,05 | 0,18 | 52,6 % [50,3 % ; 54,9 %] | 47,4 % [45,1 % ; 49,7 %] |
| leg_atr Q4 | 879 | 945 | 0,02 | 0,11 | 0,13 | 0,20 | 50,2 % [47,9 % ; 52,5 %] | 47,3 % [45,0 % ; 49,6 %] |
| obs_dist_seg_atr Q4 | 958 | 866 | −0,17 | 0,08 | −0,13 | 0,19 | 49,1 % [46,8 % ; 51,4 %] | 47,2 % [44,9 % ; 49,5 %] |
