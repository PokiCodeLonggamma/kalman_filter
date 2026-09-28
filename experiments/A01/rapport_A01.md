# EXP-A01 — Anatomie et distribution du signal brut AKF-TSO v2.1

- **Date :** 2026-09-28. **Étape :** A, anatomie (strictement descriptive).
- **Actif et période :** BTC/USD Bitstamp 30 min, du 2020-01-01 au 2025-12-31. Données tronquées au 2025-12-31 23:30 UTC ; 2026, ETH et XRP ne sont pas lus.
- **Moteur :** `AKF_TSO_v2.1_baseline.pine` (SHA-256 `c70062b8…ecd30b317`), réplique certifiée `src/indicator/`, réglages par défaut.
- **Frais :** sans objet (aucune transaction simulée, aucun PnL, pas de tableau des 8 métriques).
- **Reproduire :** `python experiments/A01/run_A01.py` (≈ 30 s) ; tests : `python -m pytest tests`.
- **Relecture du 2026-09-28.** Après une revue indépendante, trois lectures sont corrigées : la bimodalité du retard (§2.3), la description du déclencheur (§2.5) et la liste des descripteurs pour B (§4). Les chiffres de la première version sont inchangés. Contrôles détaillés : annexe H. Compléments du porteur (biais de la tenue de l'extremum, typologie par `retrace_ratio`, zone neutre) : annexe I et `RESEARCH_INSIGHTS.md`.

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
- **L'issue « extremum tenu » ou « extremum cassé » n'est pas observable à τ = 0, et ce n'est pas une cible pour B.** Son taux croît mécaniquement avec la distance déjà parcourue : 36,5 % en Q1, 85,3 % en Q4 (`RESEARCH_INSIGHTS.md`, I-M1). La cible de B est l'asymétrie d'excursion MFE_H / \|MAE_H\| depuis open[t+1] (I-M2).
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
- **Cible et découpage de B :** asymétrie d'excursion MFE_H / \|MAE_H\| depuis open[t+1], en ATR14(t). Horizons fixes H ∈ {6, 13, 26, 48} barres et barrières symétriques de ±1,5 et ±2,0 ATR (`RESEARCH_INSIGHTS.md`, I-M2). Mesure séparée pour Long / Short et rang 1 / répétition. La tenue de l'extremum n'est jamais une cible seule (I-M1). La réserve 2026 reste fermée.
- **Aucune Étape B n'est lancée.**

---

# Annexes chiffrées (générées par `run_A01.py`)

## A. Univers et ancres

| Élément | Valeur |
|---|---|
| Barres 30 min lues | 105 216 (2020-01-01 00:00 → 2025-12-31 23:30 UTC) |
| Signaux bruts valides 2020-2025 (`valid_features`) | 7 297 |
| Exclus : sortie native en 2026 (convention D43) | 1 |
| **Univers A01** | **7 296** |
| Rang 1 (`is_flip`, changement de position) | 6 037 (82,7 %) |
| Répétitions de même sens (`run_rank > 1`) | 1 259 (17,3 %) |
| Long / Short | 3 628 / 3 668 |
| Cadence | 101,9 signaux/mois, dont 84,3 flips/mois |
| Signaux en warm-up (`is_warmup`) | 0 |
| Rang maximal d'une série de même sens | 6 |

| Année | Signaux | Part Long | Part rang 1 | Signaux/mois |
|---|---|---|---|---|
| 2020 | 1 189 | 50,2 % | 84,1 % | 99,1 |
| 2021 | 1 226 | 50,4 % | 81,6 % | 102,2 |
| 2022 | 1 235 | 50,2 % | 82,2 % | 102,9 |
| 2023 | 1 236 | 49,0 % | 84,1 % | 103,0 |
| 2024 | 1 193 | 48,2 % | 81,4 % | 99,4 |
| 2025 | 1 217 | 50,3 % | 83,1 % | 101,4 |

2020 démarre le 13 janvier (warm-up 30 min et 1 h) : sa cadence mensuelle est sous-estimée d'environ 3 %.

## B. Taux

| Indicateur | Tous | Long | Short | Rang 1 (flip) | Répétition |
|---|---|---|---|---|---|
| Extremum encore à venir au signal (`post_lag_bars` < 0) | 36,1 % | 34,9 % | 37,2 % | 37,1 % | 31,0 % |
| Extremum exactement au signal (`post_lag_bars` = 0) | 0,8 % | 0,6 % | 0,9 % | 0,7 % | 0,8 % |
| Extremum en bord droit, censuré (`post_is_right_censored`) | 6,7 % | 6,6 % | 6,8 % | 6,9 % | 6,0 % |
| x1 ne franchit pas zéro dans la fenêtre (`post_x1_crossed_zero` = False) | 13,6 % | 13,3 % | 13,8 % | 13,8 % | 12,2 % |
| x1 déjà du sens du signal à t (`x1_already_flipped_at_t`) | 51,8 % | 52,6 % | 51,0 % | 51,2 % | 55,0 % |
| x1 déjà du sens du signal à l'extremum (`post_lag_filter_bars` = 0) | 9,7 % | 8,7 % | 10,7 % | 10,1 % | 7,7 % |
| Parmi les franchissements : signal avant x1 = 0 (`post_lag_osc_bars` < 0) | 56,6 % | 56,0 % | 57,2 % | 57,5 % | 52,2 % |

## C. Quantiles, tous signaux

| Variable | n | P10 | P25 | P50 | P75 | P90 |
|---|---|---|---|---|---|---|
| `post_lag_bars` : retard à l'extremum (barres) | 7 296 | −11,0 | −6,0 | 4,0 | 6,0 | 8,0 |
| `post_dist_atr` : distance à l'extremum (ATR) | 7 296 | 1,20 | 1,63 | 2,23 | 3,17 | 4,66 |
| `post_lag_filter_bars` : extremum → x1 = 0 (barres) | 6 306 | 0,0 | 3,0 | 5,0 | 7,0 | 9,0 |
| `post_lag_osc_bars` : x1 = 0 → signal (barres) | 6 306 | −11,0 | −2,0 | −1,0 | 0,0 | 0,0 |
| `obs_lag_seg_bars` (barres) | 7 296 | 2,0 | 4,0 | 5,0 | 7,0 | 8,0 |
| `obs_dist_seg_atr` (ATR) | 7 296 | 0,84 | 1,26 | 1,77 | 2,39 | 3,10 |
| `obs_lag_cycle_bars` (barres) | 7 296 | 2,0 | 4,0 | 6,0 | 8,0 | 10,0 |
| `obs_dist_cycle_atr` (ATR) | 7 296 | 0,89 | 1,32 | 1,84 | 2,46 | 3,16 |
| `prev_seg_len` (barres) | 7 296 | 7,0 | 8,0 | 10,0 | 13,0 | 17,0 |
| `prev_seg_extreme_abs` | 7 296 | 97,7 | 100,0 | 100,0 | 100,0 | 100,0 |
| `saturation` : part du segment à \|ts\| ≥ 99,9 | 7 296 | 0,00 | 0,10 | 0,18 | 0,29 | 0,38 |
| `leg_atr` : amplitude du segment (ATR) | 7 296 | 1,79 | 2,17 | 2,82 | 3,94 | 5,58 |
| `peak_bps_vol` | 7 296 | 0,35 | 0,49 | 0,67 | 0,88 | 1,11 |
| `nis_z_100` au signal | 7 296 | −0,54 | −0,32 | 0,19 | 1,22 | 2,75 |
| `nis_z_100_seg_max` | 7 296 | −0,31 | 0,04 | 0,77 | 2,18 | 4,46 |
| `A_vol` | 7 296 | 0,28 | 0,40 | 0,55 | 0,72 | 0,90 |
| `log_R_rel` | 7 296 | −0,485 | −0,322 | −0,118 | 0,112 | 0,323 |
| `n_short_seg_48` | 7 296 | 0,0 | 0,0 | 0,0 | 1,0 | 2,0 |
| `gap_prev_any_bars` | 7 296 | 9,0 | 10,0 | 13,0 | 17,0 | 22,0 |
| `gap_prev_same_bars` | 7 296 | 17,0 | 21,0 | 26,0 | 34,0 | 44,0 |
| `gap_prev_opp_bars` | 7 296 | 9,0 | 10,0 | 13,0 | 20,0 | 31,0 |
| `atr14_bps` : ATR14 au signal (bps) | 7 296 | 23,3 | 34,0 | 49,7 | 70,5 | 99,4 |

## C bis. Retard à l'extremum selon son sens

| Cas | Signaux | `post_lag_bars` | `post_dist_atr` | Censure |
|---|---|---|---|---|
| Extremum passé (`post_lag_bars` > 0) : mouvement déjà consommé | 4 610 (63,2 %) | 5,0 [4,0 ; 7,0] | 2,01 [1,52 ; 2,64] | 0,0 % |
| Extremum au signal (`post_lag_bars` = 0) | 55 (0,8 %) | 0,0 [0,0 ; 0,0] | 1,15 [0,76 ; 2,20] | 0,0 % |
| Extremum à venir (`post_lag_bars` < 0) : mouvement adverse restant | 2 631 (36,1 %) | −8,0 [−12,0 ; −5,0] | 3,01 [1,99 ; 4,67] | 18,7 % |

## D. Médiane [P25 ; P75] par sens et par type

| Variable | Long | Short | Rang 1 (flip) | Répétition |
|---|---|---|---|---|
| `post_lag_bars` : retard à l'extremum (barres) | 4,0 [−6,0 ; 6,0] | 3,0 [−6,0 ; 6,0] | 3,0 [−7,0 ; 6,0] | 4,0 [−4,0 ; 6,0] |
| `post_dist_atr` : distance à l'extremum (ATR) | 2,30 [1,70 ; 3,22] | 2,16 [1,54 ; 3,13] | 2,21 [1,60 ; 3,17] | 2,36 [1,74 ; 3,21] |
| `post_lag_filter_bars` : extremum → x1 = 0 (barres) | 5,0 [3,0 ; 7,0] | 5,0 [3,0 ; 7,0] | 5,0 [3,0 ; 7,0] | 6,0 [3,0 ; 8,0] |
| `post_lag_osc_bars` : x1 = 0 → signal (barres) | −1,0 [−2,0 ; 0,0] | −1,0 [−3,0 ; 0,0] | −1,0 [−3,0 ; 0,0] | −1,0 [−1,0 ; 0,0] |
| `obs_lag_seg_bars` (barres) | 5,0 [4,0 ; 7,0] | 5,0 [4,0 ; 7,0] | 5,0 [4,0 ; 7,0] | 6,0 [4,0 ; 7,0] |
| `obs_dist_seg_atr` (ATR) | 1,86 [1,34 ; 2,44] | 1,68 [1,17 ; 2,33] | 1,73 [1,23 ; 2,34] | 1,93 [1,41 ; 2,55] |
| `obs_lag_cycle_bars` (barres) | 6,0 [4,0 ; 8,0] | 6,0 [4,0 ; 8,0] | 6,0 [4,0 ; 8,0] | 6,0 [4,0 ; 8,0] |
| `obs_dist_cycle_atr` (ATR) | 1,95 [1,42 ; 2,51] | 1,73 [1,23 ; 2,39] | 1,80 [1,29 ; 2,41] | 2,02 [1,50 ; 2,64] |
| `prev_seg_len` (barres) | 10,0 [8,0 ; 13,0] | 10,0 [8,0 ; 13,0] | 10,0 [8,0 ; 13,0] | 10,0 [8,0 ; 14,0] |
| `prev_seg_extreme_abs` | 100,0 [100,0 ; 100,0] | 100,0 [100,0 ; 100,0] | 100,0 [100,0 ; 100,0] | 100,0 [100,0 ; 100,0] |
| `saturation` : part du segment à \|ts\| ≥ 99,9 | 0,18 [0,10 ; 0,29] | 0,18 [0,10 ; 0,30] | 0,18 [0,10 ; 0,29] | 0,23 [0,12 ; 0,33] |
| `leg_atr` : amplitude du segment (ATR) | 2,82 [2,20 ; 3,90] | 2,82 [2,15 ; 3,98] | 2,76 [2,14 ; 3,84] | 3,12 [2,37 ; 4,43] |
| `peak_bps_vol` | 0,66 [0,48 ; 0,87] | 0,67 [0,49 ; 0,89] | 0,69 [0,51 ; 0,91] | 0,54 [0,39 ; 0,72] |
| `nis_z_100` au signal | 0,19 [−0,32 ; 1,19] | 0,19 [−0,33 ; 1,25] | 0,19 [−0,32 ; 1,20] | 0,17 [−0,33 ; 1,32] |
| `nis_z_100_seg_max` | 0,75 [0,04 ; 2,18] | 0,79 [0,04 ; 2,17] | 0,76 [0,05 ; 2,11] | 0,80 [−0,02 ; 2,65] |
| `A_vol` | 0,55 [0,40 ; 0,72] | 0,55 [0,40 ; 0,73] | 0,57 [0,42 ; 0,75] | 0,45 [0,33 ; 0,60] |
| `log_R_rel` | −0,125 [−0,329 ; 0,112] | −0,112 [−0,315 ; 0,111] | −0,146 [−0,344 ; 0,077] | 0,026 [−0,164 ; 0,233] |
| `n_short_seg_48` | 0,0 [0,0 ; 1,0] | 0,0 [0,0 ; 1,0] | 0,0 [0,0 ; 1,0] | 1,0 [1,0 ; 2,0] |
| `gap_prev_any_bars` | 13,0 [10,0 ; 17,0] | 13,0 [10,0 ; 17,0] | 12,0 [10,0 ; 15,0] | 17,0 [14,0 ; 21,5] |
| `gap_prev_same_bars` | 26,0 [21,0 ; 34,0] | 26,0 [21,0 ; 34,0] | 28,0 [23,0 ; 36,0] | 17,0 [14,0 ; 21,5] |
| `gap_prev_opp_bars` | 13,0 [10,0 ; 20,0] | 13,0 [10,0 ; 21,0] | 12,0 [10,0 ; 15,0] | 32,0 [26,0 ; 40,0] |
| `atr14_bps` : ATR14 au signal (bps) | 49,9 [34,1 ; 71,4] | 49,5 [34,0 ; 69,6] | 49,1 [33,5 ; 70,2] | 52,2 [36,8 ; 72,2] |

## E. Médiane [P25 ; P75] par année

| Variable | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 |
|---|---|---|---|---|---|---|
| `post_lag_bars` : retard à l'extremum (barres) | 4,0 [−5,0 ; 6,0] | 3,0 [−7,0 ; 6,0] | 4,0 [−6,0 ; 6,0] | 4,0 [−5,0 ; 6,0] | 3,0 [−7,0 ; 6,0] | 3,0 [−7,0 ; 6,0] |
| `post_dist_atr` : distance à l'extremum (ATR) | 2,07 [1,54 ; 2,92] | 2,21 [1,67 ; 3,15] | 2,26 [1,64 ; 3,29] | 2,33 [1,68 ; 3,34] | 2,30 [1,61 ; 3,22] | 2,25 [1,63 ; 3,14] |
| `obs_dist_seg_atr` (ATR) | 1,67 [1,25 ; 2,26] | 1,79 [1,31 ; 2,34] | 1,76 [1,27 ; 2,40] | 1,83 [1,30 ; 2,51] | 1,80 [1,22 ; 2,45] | 1,78 [1,20 ; 2,35] |
| `obs_dist_cycle_atr` (ATR) | 1,75 [1,31 ; 2,32] | 1,85 [1,33 ; 2,41] | 1,85 [1,34 ; 2,47] | 1,93 [1,39 ; 2,65] | 1,87 [1,27 ; 2,48] | 1,83 [1,27 ; 2,43] |
| `prev_seg_len` (barres) | 10,0 [8,0 ; 13,0] | 10,0 [8,0 ; 13,0] | 10,0 [8,0 ; 13,0] | 10,0 [8,0 ; 12,0] | 10,0 [8,0 ; 13,0] | 10,0 [8,0 ; 13,0] |
| `saturation` : part du segment à \|ts\| ≥ 99,9 | 0,20 [0,11 ; 0,29] | 0,18 [0,09 ; 0,29] | 0,18 [0,10 ; 0,30] | 0,18 [0,11 ; 0,29] | 0,18 [0,10 ; 0,29] | 0,20 [0,10 ; 0,30] |
| `leg_atr` : amplitude du segment (ATR) | 2,70 [2,12 ; 3,74] | 2,78 [2,22 ; 3,78] | 2,88 [2,18 ; 3,96] | 2,78 [2,09 ; 4,08] | 2,88 [2,17 ; 4,09] | 2,93 [2,25 ; 4,06] |
| `nis_z_100` au signal | 0,17 [−0,31 ; 1,17] | 0,34 [−0,27 ; 1,40] | 0,16 [−0,31 ; 1,11] | 0,09 [−0,35 ; 1,15] | 0,17 [−0,33 ; 1,14] | 0,18 [−0,34 ; 1,30] |
| `A_vol` | 0,55 [0,40 ; 0,70] | 0,54 [0,39 ; 0,71] | 0,55 [0,39 ; 0,73] | 0,56 [0,42 ; 0,73] | 0,54 [0,39 ; 0,72] | 0,55 [0,40 ; 0,74] |
| `gap_prev_any_bars` | 13,0 [10,0 ; 17,0] | 13,0 [10,0 ; 17,0] | 13,0 [10,0 ; 17,0] | 12,0 [10,0 ; 16,0] | 13,0 [10,0 ; 17,0] | 13,0 [10,0 ; 17,0] |
| `atr14_bps` : ATR14 au signal (bps) | 57,3 [42,3 ; 76,5] | 80,3 [63,4 ; 107,3] | 54,8 [39,7 ; 72,3] | 33,6 [23,3 ; 45,2] | 45,9 [35,3 ; 59,2] | 36,8 [26,7 ; 48,7] |

## F. Profils autour du signal : médiane [P25 ; P75]

### Excursion signée du close, en ATR14(t)

| τ (barres) | Rang 1 Long | Rang 1 Short | Répétition Long | Répétition Short | Rang 1 | Répétition |
|---|---|---|---|---|---|---|
| τ = −48 | −0,21 [−3,08 ; 2,57] | 0,17 [−2,61 ; 3,21] | 2,08 [−0,36 ; 4,15] | 2,58 [0,09 ; 5,07] | 0,01 [−2,78 ; 2,85] | 2,29 [−0,11 ; 4,55] |
| τ = −24 | −0,18 [−1,73 ; 1,57] | −0,02 [−1,56 ; 1,81] | 1,67 [0,69 ; 2,98] | 1,93 [0,87 ; 3,51] | −0,11 [−1,64 ; 1,70] | 1,79 [0,76 ; 3,26] |
| τ = −12 | 0,36 [−0,34 ; 1,13] | 0,42 [−0,34 ; 1,24] | 0,63 [0,07 ; 1,33] | 0,83 [0,06 ; 1,52] | 0,39 [−0,34 ; 1,19] | 0,74 [0,06 ; 1,42] |
| τ = −6 | −0,69 [−1,32 ; −0,13] | −0,64 [−1,28 ; −0,10] | −0,76 [−1,34 ; −0,28] | −0,70 [−1,35 ; −0,15] | −0,67 [−1,30 ; −0,11] | −0,73 [−1,34 ; −0,22] |
| τ = −3 | −0,56 [−1,09 ; −0,07] | −0,53 [−1,11 ; −0,04] | −0,60 [−1,16 ; −0,07] | −0,59 [−1,13 ; −0,04] | −0,54 [−1,10 ; −0,05] | −0,59 [−1,15 ; −0,06] |
| τ = +0 | 0,00 [0,00 ; 0,00] | 0,00 [−0,00 ; −0,00] | 0,00 [0,00 ; 0,00] | 0,00 [0,00 ; 0,00] | 0,00 [0,00 ; 0,00] | 0,00 [0,00 ; 0,00] |
| τ = +3 | 0,03 [−0,57 ; 0,60] | −0,03 [−0,62 ; 0,62] | 0,11 [−0,52 ; 0,59] | 0,03 [−0,56 ; 0,55] | 0,00 [−0,60 ; 0,61] | 0,06 [−0,55 ; 0,58] |
| τ = +6 | 0,04 [−0,83 ; 0,87] | −0,04 [−0,90 ; 0,83] | 0,07 [−0,78 ; 0,80] | 0,01 [−0,80 ; 0,76] | 0,01 [−0,86 ; 0,84] | 0,04 [−0,80 ; 0,77] |
| τ = +12 | 0,03 [−1,08 ; 1,30] | −0,10 [−1,32 ; 1,18] | −0,00 [−1,26 ; 1,24] | 0,10 [−1,13 ; 1,27] | −0,03 [−1,22 ; 1,24] | 0,05 [−1,18 ; 1,26] |
| τ = +24 | 0,08 [−1,83 ; 1,95] | −0,13 [−2,02 ; 1,65] | 0,08 [−1,75 ; 1,76] | 0,11 [−1,64 ; 1,85] | −0,03 [−1,93 ; 1,82] | 0,08 [−1,70 ; 1,81] |
| τ = +48 | 0,21 [−2,46 ; 2,94] | −0,25 [−2,99 ; 2,52] | 0,31 [−2,44 ; 2,65] | 0,03 [−3,09 ; 2,86] | −0,02 [−2,73 ; 2,77] | 0,19 [−2,74 ; 2,78] |

### `trend_strength` orienté (d · ts)

| τ (barres) | Rang 1 | Répétition |
|---|---|---|
| τ = −48 | 8,9 [−73,6 ; 81,9] | 4,3 [−78,6 ; 78,0] |
| τ = −24 | 19,9 [−61,4 ; 88,3] | −63,0 [−92,8 ; 11,8] |
| τ = −12 | 23,0 [−65,8 ; 64,5] | −34,5 [−87,5 ; 34,4] |
| τ = −6 | −96,5 [−100,0 ; −85,3] | −97,2 [−100,0 ; −87,2] |
| τ = −3 | −81,3 [−89,8 ; −71,0] | −81,9 [−91,1 ; −71,4] |
| τ = +0 | −17,7 [−24,3 ; −9,7] | −17,2 [−24,0 ; −7,9] |
| τ = +3 | 80,7 [63,6 ; 91,7] | 85,0 [66,8 ; 93,5] |
| τ = +6 | 93,9 [64,0 ; 100,0] | 95,2 [69,3 ; 100,0] |
| τ = +12 | 7,7 [−69,9 ; 60,5] | 10,2 [−70,3 ; 58,1] |
| τ = +24 | −7,4 [−75,9 ; 76,6] | 2,9 [−70,5 ; 80,0] |
| τ = +48 | −7,3 [−79,9 ; 75,5] | −4,8 [−80,7 ; 73,3] |

### Vitesse x1 orientée, en ATR14(t) par barre

| τ (barres) | Rang 1 | Répétition |
|---|---|---|
| τ = −48 | 0,021 [−0,199 ; 0,243] | 0,007 [−0,207 ; 0,213] |
| τ = −24 | 0,059 [−0,164 ; 0,272] | −0,135 [−0,271 ; 0,008] |
| τ = −12 | 0,027 [−0,187 ; 0,206] | −0,064 [−0,208 ; 0,044] |
| τ = −6 | −0,370 [−0,524 ; −0,244] | −0,302 [−0,447 ; −0,187] |
| τ = −3 | −0,291 [−0,382 ; −0,214] | −0,246 [−0,329 ; −0,178] |
| τ = +0 | 0,002 [−0,034 ; 0,040] | 0,006 [−0,027 ; 0,042] |
| τ = +3 | 0,233 [0,122 ; 0,348] | 0,221 [0,129 ; 0,327] |
| τ = +6 | 0,262 [0,090 ; 0,439] | 0,260 [0,114 ; 0,412] |
| τ = +12 | −0,006 [−0,176 ; 0,168] | −0,010 [−0,177 ; 0,160] |
| τ = +24 | −0,003 [−0,212 ; 0,196] | 0,012 [−0,194 ; 0,198] |
| τ = +48 | −0,010 [−0,215 ; 0,195] | −0,010 [−0,212 ; 0,191] |

### `nis_z_100`

| τ (barres) | Rang 1 | Répétition |
|---|---|---|
| τ = −48 | −0,38 [−0,60 ; 0,22] | −0,38 [−0,60 ; 0,21] |
| τ = −24 | −0,34 [−0,58 ; 0,38] | −0,43 [−0,61 ; 0,00] |
| τ = −12 | −0,20 [−0,54 ; 0,73] | −0,43 [−0,61 ; 0,13] |
| τ = −6 | −0,51 [−0,65 ; −0,29] | −0,51 [−0,66 ; −0,27] |
| τ = −3 | −0,42 [−0,60 ; 0,02] | −0,43 [−0,62 ; 0,04] |
| τ = +0 | 0,19 [−0,32 ; 1,20] | 0,17 [−0,33 ; 1,32] |
| τ = +3 | −0,40 [−0,61 ; 0,13] | −0,37 [−0,58 ; 0,25] |
| τ = +6 | −0,53 [−0,66 ; −0,29] | −0,50 [−0,64 ; −0,27] |
| τ = +12 | −0,34 [−0,58 ; 0,29] | −0,25 [−0,56 ; 0,40] |
| τ = +24 | −0,40 [−0,60 ; 0,13] | −0,33 [−0,57 ; 0,29] |
| τ = +48 | −0,40 [−0,60 ; 0,16] | −0,36 [−0,58 ; 0,32] |

## G. Corrélations de Spearman entre variables causales

Matrice complète : `spearman_causales.csv`, figure `fig4_spearman.png`. Paires avec \|ρ\| ≥ 0,5 :

| Variable | Variable | ρ |
|---|---|---|
| `obs_dist_seg_atr` | `obs_dist_cycle_atr` | 0,96 |
| `gap_prev_any_bars` | `gap_prev_opp_bars` | 0,92 |
| `peak_bps_vol` | `A_vol` | 0,86 |
| `prev_seg_len` | `gap_prev_any_bars` | 0,82 |
| `obs_lag_seg_bars` | `obs_lag_cycle_bars` | 0,81 |
| `nis_z_100_seg_max` | `log_R_rel` | 0,74 |
| `prev_seg_len` | `gap_prev_opp_bars` | 0,69 |
| `leg_atr` | `log_R_rel` | 0,67 |
| `prev_seg_extreme_abs` | `saturation` | 0,67 |
| `prev_seg_len` | `leg_atr` | 0,66 |
| `nis_z_100` | `nis_z_100_seg_max` | 0,64 |
| `obs_dist_seg_atr` | `nis_z_100` | 0,63 |
| `obs_dist_cycle_atr` | `nis_z_100` | 0,59 |
| `leg_atr` | `gap_prev_any_bars` | 0,57 |
| `nis_z_100` | `log_R_rel` | 0,55 |
| `prev_seg_len` | `log_R_rel` | 0,55 |
| `leg_atr` | `nis_z_100_seg_max` | 0,55 |

## H. Relecture du 2026-09-28

Identité vérifiée sur les 7 296 signaux : `post_lag_bars` < 0 ⇔ l'excursion adverse jusqu'au signal suivant dépasse `obs_dist_seg_atr` : **vraie**.

| Mesure | Tous | Long | Short | Rang 1 (flip) | Répétition |
|---|---|---|---|---|---|
| Extremum du segment cassé avant le signal suivant (MAE > `obs_dist_seg_atr`) | 36,1 % | 34,9 % | 37,2 % | 37,1 % | 31,0 % |
| Horizon jusqu'au signal suivant (barres), P50 [P25 ; P75] | 13 [10 ; 17] | 13 [10 ; 17] | 13 [10 ; 17] | 13 [10 ; 17] | 13 [10 ; 16] |
| MAE jusqu'au signal suivant (ATR), P50 [P25 ; P75] | 1,24 [0,60 ; 2,38] | 1,26 [0,60 ; 2,46] | 1,23 [0,60 ; 2,32] | 1,25 [0,61 ; 2,41] | 1,23 [0,57 ; 2,28] |

| Position du signal par rapport au passage à zéro de x1 | Tous | Long | Short | Rang 1 (flip) | Répétition |
|---|---|---|---|---|---|
| x1 ne franchit pas zéro avant le signal suivant | 13,6 % | 13,3 % | 13,8 % | 13,8 % | 12,2 % |
| signal ≥ 3 barres avant x1 = 0 | 21,2 % | 20,3 % | 22,2 % | 22,0 % | 17,7 % |
| signal 1 à 2 barres avant x1 = 0 | 27,7 % | 28,3 % | 27,1 % | 27,6 % | 28,1 % |
| signal à la barre où x1 = 0 | 36,8 % | 37,3 % | 36,3 % | 35,9 % | 41,0 % |
| signal 1 à 2 barres après x1 = 0 | 0,7 % | 0,8 % | 0,6 % | 0,6 % | 1,0 % |
| signal ≥ 3 barres après x1 = 0 | 0,0 % | 0,0 % | 0,0 % | 0,0 % | 0,0 % |

| Variable dérivée (causale) | Tous | Long | Short | Rang 1 (flip) | Répétition |
|---|---|---|---|---|---|
| `cycle_seg_div_atr` = 0 (le segment porte l'extremum du cycle) | 86,3 % | 85,1 % | 87,5 % | 86,3 % | 86,3 % |
| `cycle_seg_div_atr` si > 0 (ATR), P50 [P25 ; P75] | 0,34 [0,15 ; 0,65] | 0,37 [0,16 ; 0,74] | 0,31 [0,14 ; 0,59] | 0,32 [0,16 ; 0,60] | 0,53 [0,13 ; 1,00] |
| `decel_ratio` = `A_vol` / `peak_bps_vol`, P50 [P25 ; P75] | 0,87 [0,74 ; 0,98] | 0,87 [0,75 ; 0,98] | 0,87 [0,74 ; 0,98] | 0,87 [0,74 ; 0,98] | 0,88 [0,75 ; 0,99] |

| Variable | Variable | ρ |
|---|---|---|
| `obs_dist_seg_atr` | `obs_lag_seg_bars` | 0,09 |
| `obs_dist_seg_atr` | `nis_z_100` | 0,63 |
| `obs_dist_seg_atr` | `x1_already_flipped_at_t` | 0,44 |
| `obs_dist_seg_atr` | `nis_z_100_seg_max` | 0,25 |
| `nis_z_100_seg_max` | `log_R_rel` | 0,74 |
| `nis_z_100_seg_max` | `nis_z_100` | 0,64 |
| `obs_dist_seg_atr` | `peak_bps_vol` | −0,18 |
| `obs_dist_seg_atr` | `A_vol` | −0,03 |
| `x1_already_flipped_at_t` | `peak_bps_vol` | −0,30 |
| `x1_already_flipped_at_t` | `A_vol` | −0,26 |
| `cycle_seg_div_atr` | `obs_dist_seg_atr` | −0,13 |
| `decel_ratio` | `x1_already_flipped_at_t` | 0,16 |
| `decel_ratio` | `obs_dist_seg_atr` | 0,30 |

Répétitions comparées au signal de même sens qui les précède (1 259 paires) : pic de vitesse du segment plus faible (`peak_bps_vol`) dans 56,6 % des cas, `A_vol` plus faible dans 55,6 % ; le segment porte l'extremum du cycle (plus bas plus bas / plus haut plus haut) dans 86,3 % des répétitions.

Médiane de l'excursion signée du close (ATR14(t)) et intervalle bootstrap à 95 % (2 000 tirages) :

| Groupe | τ = +12 | τ = +24 | τ = +48 |
|---|---|---|---|
| Rang 1 Long | 0,03 [−0,03 ; 0,10] | 0,08 [−0,05 ; 0,20] | 0,21 [0,03 ; 0,32] |
| Rang 1 Short | −0,10 [−0,18 ; −0,03] | −0,13 [−0,26 ; −0,03] | −0,25 [−0,39 ; −0,08] |
| Répétition Long | −0,00 [−0,20 ; 0,13] | 0,08 [−0,17 ; 0,25] | 0,31 [−0,08 ; 0,58] |
| Répétition Short | 0,10 [−0,09 ; 0,23] | 0,11 [−0,02 ; 0,30] | 0,03 [−0,33 ; 0,40] |

## I. Compléments du porteur (2026-09-28)

`retrace_ratio` = `obs_dist_seg_atr` / `leg_atr`. Extension si cassé = `post_dist_atr` − `obs_dist_seg_atr`. Seuils 0,5 / 0,85 / 2,8 : découpage exploratoire, non optimisé et non validé.

| Quartile de `obs_dist_seg_atr` | Bornes (ATR) | Signaux | `obs_dist_seg_atr` médian | `retrace_ratio` médian | Extremum tenu jusqu'au signal suivant |
|---|---|---|---|---|---|
| Q1 | [0,00 ; 1,26] | 1 824 | 0,92 | 35,3 % | 36,5 % |
| Q2 | [1,26 ; 1,77] | 1 824 | 1,52 | 59,1 % | 61,4 % |
| Q3 | [1,77 ; 2,39] | 1 824 | 2,04 | 71,9 % | 72,6 % |
| Q4 | [2,39 ; 7,72] | 1 824 | 2,94 | 87,1 % | 85,3 % |

| Famille (seuils exploratoires du porteur) | Signaux | `leg_atr` P50 | `obs_dist_seg_atr` P50 | `A_vol` P50 | `nis_z_100` P50 | x1 déjà retourné | Extremum cassé | Extension si cassé : P50 / moyenne / P90 (ATR) | Sortie de zone neutre vers le sens du signal ; barres P50 [P25 ; P75] |
|---|---|---|---|---|---|---|---|---|---|
| Tous | 7 296 (100,0 %) | 2,82 | 1,77 | 0,55 | 0,19 | 51,8 % | 36,1 % | 1,45 / 2,57 / 6,21 | 91,2 % ; 2 [1 ; 2] |
| P1 : `retrace_ratio` < 0,5 et `leg_atr` ≥ 2,8 | 1 875 (25,7 %) | 4,73 | 1,47 | 0,60 | 0,29 | 30,3 % | 42,8 % | 1,28 / 2,40 / 5,86 | 90,5 % ; 2 [2 ; 3] |
| P2 : `retrace_ratio` ≥ 0,85 et `leg_atr` < 2,8 | 1 304 (17,9 %) | 2,06 | 2,22 | 0,47 | 0,57 | 82,5 % | 26,9 % | 1,71 / 2,89 / 6,46 | 96,5 % ; 1 [1 ; 2] |
| Ni P1 ni P2 | 4 117 (56,4 %) | 2,68 | 1,74 | 0,55 | 0,01 | 51,9 % | 35,9 % | 1,49 / 2,58 / 6,28 | 89,9 % ; 2 [1 ; 2] |
| `retrace_ratio` ≥ 1 (tous) | 934 (12,8 %) | 2,11 | 2,64 | 0,47 | 1,34 | 89,3 % | 20,8 % | 1,65 / 2,89 / 6,62 | 98,7 % ; 1 [1 ; 2] |

Sortie de la zone neutre après le signal : vers la zone du sens du signal dans 91,2 % des cas, en 2 [1 ; 2] barres ; retour vers la zone d'origine dans 8,8 % des cas, en 3 [2 ; 4] barres.
