# EXP-A01 — Anatomie et distribution du signal brut AKF-TSO v2.1

- **Date :** 2026-09-28. **Étape :** A, anatomie (strictement descriptive).
- **Actif et période :** BTC/USD Bitstamp 30 min, du 2020-01-01 au 2025-12-31. Données tronquées au 2025-12-31 23:30 UTC ; 2026, ETH et XRP ne sont pas lus.
- **Moteur :** `AKF_TSO_v2.1_baseline.pine` (SHA-256 `c70062b8…ecd30b317`), réplique certifiée `src/indicator/`, réglages par défaut.
- **Frais :** sans objet (aucune transaction simulée, aucun PnL, pas de tableau des 8 métriques).
- **Reproduire :** `python experiments/A01/run_A01.py` (≈ 30 s) ; tests : `python -m pytest tests`.
- **Relecture du 2026-09-28.** Après une revue indépendante, trois lectures sont corrigées : la bimodalité du retard (§2.3), la description du déclencheur (§2.5) et la liste des descripteurs pour B (§4). Les chiffres de la première version sont inchangés. Contrôles détaillés : annexe H.

## 0. Cadrage

- **QUESTION :** quand, à quelle distance de l'extremum de prix visé et dans quel état cinématique le signal v2.1 se déclenche-t-il ? Ces distributions sont-elles stables d'une année à l'autre ?
- **PERTINENCE POUR LE FILTRE AKF :** trois traits du moteur fixent la géométrie du signal. Le gain est figé par la remise à 1 de la diagonale de P (retard structurel). `trend_strength` est normalisé par max|x1| sur 5 barres (aveugle à l'amplitude). Le déclencheur est one-shot après au moins 6 barres en zone (cadence). A01 mesure les conséquences de ces traits et prépare les variables de l'Étape B.
- **CE QUE LE PROTOCOLE MESURE RÉELLEMENT :** pour les 7 296 signaux de développement :
  - 6 variables a posteriori (`post_`) et 19 variables causales ;
  - leurs distributions par sens, par type (rang 1 ou répétition) et par année ;
  - les profils médians de −48 à +48 barres ;
  - les corrélations de rang entre variables causales.
- **CE QU'IL NE PERMET PAS DE CONCLURE :**
  - rien sur la rentabilité ni sur l'avantage d'excursion : il n'y a ni PnL ni référence, c'est l'objet des Étapes B et C ;
  - les variables `post_` lisent le futur : elles décrivent le moteur et ne deviendront jamais des filtres ;
  - les quantiles ne sont pas des seuils, et les corrélations ne sont pas causales ;
  - les résultats valent pour les réglages par défaut, le BTC 30 min et la période 2020-2025.

## 1. [CODE] Implémentation et contrôles

- **Étape 0 : 26 fichiers copiés à l'identique depuis `#KAKALMAN`**, avec des empreintes SHA-256 égales à la source (`manifest_copie_sha256.txt`). Aucun composant du filtre n'est réécrit. Liste :
  - la baseline Pine ;
  - `src/indicator/` ;
  - `src/features/`, dont `kalman_intrinsic.py` et `multi_tf.py`, nécessaires au masque `valid_features` qui définit l'univers ;
  - `src/config.py` et `src/utils/data_loader.py` ;
  - l'oracle P0 et 9 fichiers de tests ;
  - la fixture TradingView et le CSV BTC 30 min.
- **Suite de tests rejouée dans `#KalmanFilter` :** 138 réussis, 2 ignorés. Les 2 tests ignorés comparent à des CSV de P3 absents du dépôt. Les tests de parité, eux, lisent l'historique jusqu'au 2026-09-15 (fixture TradingView) : c'est un contrôle technique du moteur, sans aucune statistique de recherche.
- **Ancres retrouvées exactement :**
  - 7 297 signaux valides en 2020-2025, dont 1 exclu (2025-12-31 21:30 UTC, sortie native en 2026, convention D43) : **7 296** signaux ;
  - **6 037** rangs 1 ;
  - `run_rank == 1` ⇔ `is_flip` sur 100 % des signaux.
- **Module `src/anatomy/` :** `causal.py` (variables `obs_*`, cinématique, cadence, ATR14 de Wilder) et `posterior.py` (variables `post_*`, profils).
- **13 tests dans `tests/test_anatomy.py` :**
  - séries synthétiques : V, Λ, pause sans passage de x1 par zéro, censure, x1 déjà retourné à l'extremum, segment incohérent ;
  - briques : ATR de Wilder, absence de `shift(-` dans le module causal ;
  - causalité par troncature sur 50 coupes, avec égalité exacte ;
  - ancres ;
  - identités sur les 7 296 signaux :
    - `post_lag_bars = obs_lag_seg_bars` dès que l'extremum est passé ;
    - `post_lag_filter_bars + post_lag_osc_bars = post_lag_bars`.
- **Conventions :**
  - extrêmes lus sur `low` pour un Long, sur `high` pour un Short ; première occurrence en cas d'égalité ;
  - fenêtre a posteriori : [début du segment qualifiant ; signal suivant], bornes incluses ;
  - `saturation` : part des barres du segment qualifiant où \|ts\| ≥ 99,9 ;
  - `leg_atr` : (plus haut − plus bas) du segment / ATR14(t) ;
  - `atr14_bps` est ajoutée pour situer le niveau de volatilité.
- **`is_warmup` est faux partout :** l'univers #KAKALMAN exige déjà `valid_features` (300 barres 30 min et 300 bougies 1 h).
- **Relecture (annexe H) :** l'identité « `post_lag_bars` < 0 ⇔ excursion adverse jusqu'au signal suivant > `obs_dist_seg_atr` » est vérifiée sur les 7 296 signaux. Deux variables dérivées, toutes deux causales, sont calculées pour B : `cycle_seg_div_atr` = `obs_dist_cycle_atr` − `obs_dist_seg_atr` et `decel_ratio` = `A_vol` / `peak_bps_vol`. Les intervalles des médianes de profil sont estimés par bootstrap (2 000 tirages).

## 2. [OBS] Mesures

Les chiffres détaillés sont dans les annexes A à H ci-dessous et dans les figures 1 à 4 (`figures/`).

1. **Cadence.**
   - 101,9 signaux par mois, dont 84,3 flips. Longs et shorts sont équilibrés (3 628 / 3 668).
   - 17,3 % des signaux sont des répétitions de même sens (rang maximal : 6).
   - Cadence et parts sont stables de 2020 à 2025 : 99 à 103 signaux par mois.
2. **Cycle.**
   - Écart médian au signal précédent de même sens : 26 barres [21 ; 34]. De sens opposé : 13 barres [10 ; 20].
   - `trend_strength` orienté (rangs 1) passe de −96,5 à τ = −6 à +93,9 à τ = +6, puis redescend à −55,8 à τ = +17 (figure 2).
3. **Tenue de l'extremum du segment (lecture corrigée).** Le signe de `post_lag_bars` ne mesure pas un retard du filtre. Il dit si l'extremum pré-signal du segment qualifiant tient jusqu'au signal suivant.
   - L'identité est exacte : `post_lag_bars` < 0 ⇔ l'excursion adverse jusqu'au signal suivant dépasse la distance déjà parcourue (`obs_dist_seg_atr`).
   - **L'extremum tient dans 63,9 % des cas.** Horizon : 13 barres [10 ; 17]. Dans ces cas, `post_lag_bars` = `obs_lag_seg_bars` : 5 barres [4 ; 7].
   - **Il est cassé dans 36,1 % des cas.** Le nouvel extremum survient 8 barres plus tard [5 ; 12], à 3,01 ATR [1,99 ; 4,67] du close du signal.
   - Pourquoi `post_lag_bars` est bimodal avec un creux autour de 0 : casser l'extremum demande de parcourir plus que les 1,77 ATR médians déjà faits, ce qui prend plusieurs barres. C'est un effet de géométrie, pas deux horloges.
   - Excursion adverse jusqu'au signal suivant, tous signaux : 1,24 ATR [0,60 ; 2,38].
4. **Mouvement déjà parcouru, en causal.**
   - À la clôture du signal, le prix est à 1,77 ATR [1,26 ; 2,39] de l'extremum du segment (`obs_dist_seg_atr`). Cet extremum date de 5 barres [4 ; 7].
   - Cette distance ne dépend presque pas de l'ancienneté de l'extremum : ρ = 0,09 avec `obs_lag_seg_bars`.
   - Elle varie avec le choc de la barre de signal (ρ = 0,63 avec `nis_z_100`) et avec le retournement déjà acquis de x1 (ρ = 0,44 avec `x1_already_flipped_at_t`).
5. **Position du signal par rapport au passage à zéro de x1 (lecture corrigée).**
   - À la barre même du passage à zéro : 36,8 %.
   - 1 à 2 barres avant : 27,7 %.
   - 3 barres ou plus avant : 21,2 % (P10 : 11 barres).
   - 1 à 2 barres après : 0,7 %.
   - x1 ne franchit pas zéro avant le signal suivant : 13,6 %.
   - Au total, 48,2 % des signaux partent avec x1 encore du sens opposé. La vitesse médiane au signal est de +0,002 ATR/barre.
6. **Barre de déclenchement.** `nis_z_100` montre un pic isolé à τ = 0 : médiane 0,19 [−0,32 ; 1,20], contre −0,42 à τ = −3 et −0,40 à τ = +3 (rangs 1).
7. **Segment qualifiant.**
   - Durée : 10 barres [8 ; 13].
   - `prev_seg_extreme_abs` vaut 100 pour au moins 75 % des signaux (P10 : 97,7).
   - La saturation stricte ne couvre que 18 % [10 ; 29 %] des barres du segment.
   - Amplitude : 2,82 ATR [2,17 ; 3,94].
   - Pics d'innovation : `nis_z_100_seg_max` est corrélé à `log_R_rel` (ρ = 0,74) et à `nis_z_100` (0,64), mais peu à `obs_dist_seg_atr` (0,25).
8. **Trajectoire du close** (figure 1, rangs 1, Long et Short réunis).
   - Avant le signal : sommet de +0,89 ATR à τ = −17, puis creux de −0,67 ATR à τ = −6.
   - Après le signal : médiane comprise entre −0,05 et +0,04 ATR de τ = +1 à τ = +48. La dispersion croît de façon symétrique : [−0,60 ; 0,61] à +3, [−2,73 ; 2,77] à +48.
   - La vitesse x1 passe de +0,002 à τ = 0 à +0,28 ATR/barre à τ = +5, alors que le close médian reste plat.
   - Par sens, avec un intervalle bootstrap à 95 % (annexe H) :
     - rangs 1 Short : −0,10 [−0,18 ; −0,03] à +12, −0,13 [−0,26 ; −0,03] à +24, −0,25 [−0,39 ; −0,08] à +48 ;
     - rangs 1 Long : +0,21 [+0,03 ; +0,32] à +48.
9. **Répétitions** (rang > 1).
   - Elles suivent une dérive adverse plus longue : +2,29 ATR contre le signal à τ = −48, contre +0,01 pour les rangs 1.
   - Le contexte est plus haché (`n_short_seg_48` médian de 1, contre 0) et plus volatil en relatif (`log_R_rel` de +0,026, contre −0,146).
   - **Extremum cassé moins souvent** : 31,0 %, contre 37,1 % pour les rangs 1. L'horizon est le même (13 barres) et l'excursion adverse aussi (1,23 contre 1,25 ATR), mais la marge est plus grande (`obs_dist_seg_atr` de 1,93 contre 1,73).
   - Dans 86,3 % des répétitions, la deuxième jambe marque un nouvel extremum du cycle : nouveau plus bas pour un Long, nouveau plus haut pour un Short. C'est le même taux que pour les rangs 1.
   - Sa vitesse de pointe est plus faible que celle de la jambe précédente dans 56,6 % des cas (`A_vol` plus faible : 55,6 %).
   - Médianes du close : les intervalles bootstrap des répétitions recouvrent ceux des rangs 1, sauf les Shorts à +24 barres (+0,11 [−0,02 ; +0,30] contre −0,13 [−0,26 ; −0,03]).
10. **Divergence de cycle.** Dans 13,7 % des signaux, l'extremum du cycle (depuis le dernier signal opposé) est antérieur au segment qualifiant (`cycle_seg_div_atr` > 0, médiane 0,34 ATR). Pour un Long, cela veut dire un plus bas plus haut ; pour un Short, un plus haut plus bas. Cette variable est presque indépendante de `obs_dist_seg_atr` (ρ = −0,13).
11. **Stabilité annuelle.** En unités d'ATR, retard, distances, durée du segment, saturation, `A_vol` et cadence varient peu de 2020 à 2025. Par exemple, `obs_dist_seg_atr` médian reste entre 1,67 et 1,83. Seul le niveau de volatilité change : l'ATR14 médian passe de 80 bps en 2021 à 34 bps en 2023.
12. **Redondances** (\|ρ\| de Spearman ≥ 0,8) :
    - `obs_dist_seg_atr` et `obs_dist_cycle_atr` (0,96) ;
    - `gap_prev_any_bars` et `gap_prev_opp_bars` (0,92) ;
    - `peak_bps_vol` et `A_vol` (0,86) ;
    - `prev_seg_len` et `gap_prev_any_bars` (0,82) ;
    - `obs_lag_seg_bars` et `obs_lag_cycle_bars` (0,81).

## 3. [HYP] Lectures cinématiques pour l'Étape B

- **Le déclencheur mêle deux mécanismes** : le retournement de la vitesse filtrée (x1 déjà du sens du signal : 51,8 %) et la décélération relative (48,2 %). Dans ce second groupe, 13,6 % des signaux n'ont aucun retournement de x1 avant le signal suivant : ce sont des pauses de tendance.
  - Le retard d'environ 5 barres entre l'extremum et le signal vient du gain figé.
  - Il est corrigé : « détecteur du passage à zéro à ±1 barre » était trop réducteur, puisque 35 % des signaux sortent de cette description.
- **L'issue « extremum tenu » ou « extremum cassé » n'est pas observable à τ = 0.** C'est la cible naturelle de B : quelles signatures causales réduisent le taux de cassure (36,1 %) sans réduire la marge ?
  - Lecture pour C : un stop placé au-delà de l'extremum du segment tient jusqu'au signal suivant dans 63,9 % des cas. C'est un constat a posteriori, pas une règle.
- **Le point d'entrée se dégrade avec le choc de la barre de signal, pas avec l'attente** (ρ = 0,63 contre 0,09).
  - Hypothèse à tester en B : un `nis_z_100` élevé à τ = 0 fait entrer après une bougie de rebond déjà consommée. C'est cohérent avec la strate `nis_z_100` Q4 défavorable de #KAKALMAN P6.5b.
  - Profil candidat : `nis_z_100_seg_max` élevé et `nis_z_100` bas, c'est-à-dire une capitulation pendant le segment puis un retournement calme.
- **La vitesse filtrée après le signal** (pic de +0,28 ATR/barre à τ = +5, close plat) est l'écho retardé du rebond d'avant le signal, pas un mouvement nouveau.
- **Les répétitions** sont surtout des deuxièmes jambes vers un nouvel extremum, avec une divergence de vitesse modeste (57 %). Ce ne sont pas des doubles bottoms : le plus bas plus haut n'apparaît que dans 13,7 % des cas, autant que pour les rangs 1.
  - Leur taux de cassure plus faible s'explique d'abord par une marge plus grande, à excursion adverse égale.
  - B dira si `run_rank > 1` est un atout. Il ne faut ni les pénaliser ni les favoriser par principe.
- **`cycle_seg_div_atr` > 0 identifie causalement un plus bas plus haut** (Long) ou un plus haut plus bas (Short) au sein du cycle. C'est une signature candidate pour B.
- **La géométrie est quasi stationnaire en ATR** : une enveloppe exprimée en ATR14(t) devrait mieux se transférer entre régimes qu'une enveloppe en bps.
- **La médiane négative des rangs 1 Short** et positive des rangs 1 Long à +48 barres a le signe de la dérive haussière du BTC (bêta, `RESEARCH_PHILOSOPHY.md` §4.2).

## 4. [DECISION] Orientations raisonnables (rien n'est lancé)

- **Descripteurs causaux proposés pour B (liste révisée) :**
  - `obs_dist_seg_atr`, `obs_lag_seg_bars`, `x1_already_flipped_at_t` ;
  - `nis_z_100` et `nis_z_100_seg_max` : ce dernier manquait dans la première version, sans avoir été écarté ;
  - `cycle_seg_div_atr` ;
  - `A_vol` et `decel_ratio` ;
  - `log_R_rel`, `leg_atr`, `prev_seg_len`, `saturation`, `n_short_seg_48`, `run_rank`.
- **Ce qui change par rapport à la première version :**
  - `cycle_seg_div_atr` remplace `obs_dist_cycle_atr` et `obs_lag_cycle_bars`. Il garde l'information de structure (plus bas plus haut), ce qui évite de jeter les variables de cycle.
  - `decel_ratio` remplace `peak_bps_vol`. Avec `A_vol`, il conserve l'information du pic de vitesse sans le doublon.
- **Variables écartées :**
  - `gap_prev_opp_bars`, redondante avec `gap_prev_any_bars` ;
  - `prev_seg_extreme_abs`, quasi constant.
- **Unités et découpage :** mesurer les excursions de l'Étape B en ATR14(t), séparément pour Long / Short et rang 1 / répétition. La cible naturelle est la tenue de l'extremum du segment jusqu'au signal suivant, et les excursions à horizon fixe. La réserve 2026 reste fermée.
- **Aucune Étape B n'est lancée.**
