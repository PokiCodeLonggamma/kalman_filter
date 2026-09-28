# EXP-A01 — Anatomie et distribution du signal brut AKF-TSO v2.1

- **Date :** 2026-09-28. **Étape :** A, anatomie (strictement descriptive).
- **Actif et période :** BTC/USD Bitstamp 30 min, du 2020-01-01 au 2025-12-31. Données tronquées au 2025-12-31 23:30 UTC ; 2026, ETH et XRP ne sont pas lus.
- **Moteur :** `AKF_TSO_v2.1_baseline.pine` (SHA-256 `c70062b8…ecd30b317`), réplique certifiée `src/indicator/`, réglages par défaut.
- **Frais :** sans objet (aucune transaction simulée, aucun PnL, pas de tableau des 8 métriques).
- **Reproduire :** `python experiments/A01/run_A01.py` (≈ 20 s) ; tests : `python -m pytest tests`.

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

## 2. [OBS] Mesures

Les chiffres détaillés sont dans les annexes A à G ci-dessous et dans les figures 1 à 4 (`figures/`).

1. **Cadence.**
   - 101,9 signaux par mois, dont 84,3 flips. Longs et shorts sont équilibrés (3 628 / 3 668).
   - 17,3 % des signaux sont des répétitions de même sens (rang maximal : 6).
   - Cadence et parts sont stables de 2020 à 2025 : 99 à 103 signaux par mois.
2. **Cycle.**
   - Écart médian au signal précédent de même sens : 26 barres [21 ; 34]. De sens opposé : 13 barres [10 ; 20].
   - `trend_strength` orienté (rangs 1) passe de −96,5 à τ = −6 à +93,9 à τ = +6, puis redescend à −55,8 à τ = +17 (figure 2).
3. **Retard bimodal** (annexe C bis, figure 3).
   - 63,2 % des signaux arrivent après l'extremum de leur fenêtre : 5 barres après [4 ; 7], avec 2,01 ATR [1,52 ; 2,64] déjà parcourus.
   - 36,1 % le précèdent : l'extremum survient 8 barres plus tard [5 ; 12], après un mouvement adverse de 3,01 ATR [1,99 ; 4,67]. Pour 18,7 % d'entre eux, l'extremum tombe sur le signal suivant (censure).
   - 0,8 % se déclenchent exactement sur l'extremum.
4. **Mouvement consommé, en causal.** À la clôture du signal, le prix est à 1,77 ATR [1,26 ; 2,39] de l'extremum du segment qualifiant (`obs_dist_seg_atr`). Cet extremum date de 5 barres [4 ; 7].
5. **Décomposition du retard** (86,4 % des signaux, ceux où x1 franchit zéro).
   - De l'extremum au passage à zéro de x1 : 5 barres [3 ; 7].
   - Du passage à zéro au signal : −1 barre [−2 ; 0].
   - La vitesse x1 médiane au signal vaut +0,002 ATR/barre (rangs 1). 51,8 % des signaux ont déjà x1 du sens du signal.
   - 13,6 % n'ont aucun passage de x1 par zéro avant le signal suivant.
6. **Barre de déclenchement.** `nis_z_100` montre un pic isolé à τ = 0 : médiane 0,19 [−0,32 ; 1,20], contre −0,42 à τ = −3 et −0,40 à τ = +3 (rangs 1). Corrélation de rang avec le mouvement consommé : ρ(`obs_dist_seg_atr`, `nis_z_100`) = 0,63.
7. **Segment qualifiant.**
   - Durée : 10 barres [8 ; 13].
   - `prev_seg_extreme_abs` vaut 100 pour au moins 75 % des signaux (P10 : 97,7).
   - La saturation stricte ne couvre que 18 % [10 ; 29 %] des barres du segment.
   - Amplitude : 2,82 ATR [2,17 ; 3,94].
8. **Trajectoire du close** (figure 1, rangs 1, Long et Short réunis).
   - Avant le signal : sommet de +0,89 ATR à τ = −17, puis creux de −0,67 ATR à τ = −6.
   - Après le signal : médiane comprise entre −0,05 et +0,04 ATR de τ = +1 à τ = +48. La dispersion croît de façon symétrique : [−0,60 ; 0,61] à +3, [−2,73 ; 2,77] à +48.
   - À +48, les rangs 1 Long sont à +0,21 et les rangs 1 Short à −0,25 ATR.
9. **Répétitions** (rang > 1), comparées aux rangs 1 :
   - elles suivent une dérive adverse plus longue : +2,29 ATR contre le signal à τ = −48, contre +0,01 pour les rangs 1 ;
   - le contexte est plus haché : `n_short_seg_48` médian de 1, contre 0 ;
   - la volatilité relative est plus haute : `log_R_rel` de +0,026, contre −0,146 ;
   - la vitesse relative est plus faible : `A_vol` de 0,45, contre 0,57.
10. **Stabilité annuelle.** En unités d'ATR, retard, distances, durée du segment, saturation, `A_vol` et cadence varient peu de 2020 à 2025. Par exemple, `obs_dist_seg_atr` médian reste entre 1,67 et 1,83. Seul le niveau de volatilité change : l'ATR14 médian passe de 80 bps en 2021 à 34 bps en 2023.
11. **Redondances** (\|ρ\| de Spearman ≥ 0,8) :
    - `obs_dist_seg_atr` et `obs_dist_cycle_atr` (0,96) ;
    - `gap_prev_any_bars` et `gap_prev_opp_bars` (0,92) ;
    - `peak_bps_vol` et `A_vol` (0,86) ;
    - `prev_seg_len` et `gap_prev_any_bars` (0,82) ;
    - `obs_lag_seg_bars` et `obs_lag_cycle_bars` (0,81).

## 3. [HYP] Lectures cinématiques pour l'Étape B

- **Le déclencheur se comporte en détecteur du passage à zéro de la vitesse filtrée**, à ±1 barre près. Il arrive environ 5 barres après l'extremum de prix, ce qui correspond au retard du gain figé. La décélération sans retournement existe (13,6 %), mais elle reste minoritaire.
- **Deux populations coexistent :**
  - des signaux tardifs (63 %), qui arrivent après un mouvement favorable déjà parcouru d'environ 2 ATR ;
  - des signaux prématurés (36 %), qui arrivent avant la fin du mouvement adverse, lequel se prolonge d'environ 3 ATR.

  Une variable causale qui séparerait ces deux populations serait candidate pour l'Étape B.
- **La barre de déclenchement est typiquement un choc d'innovation :** le signal naît souvent d'une seule bougie de contre-tendance, ce qui gonfle aussi le mouvement consommé au moment du signal.
- **La médiane plate du close après le signal ne dit rien de l'excursion** (MFE/MAE). Elle ne dit rien non plus de familles plus étroites : une médiane agrégée peut masquer des sous-familles asymétriques de signes opposés. C'est précisément la question de B.
- **La vitesse filtrée après le signal** (pic de +0,28 ATR/barre à τ = +5) semble être l'écho retardé du rebond d'avant le signal, plutôt qu'un mouvement nouveau.
- **La géométrie du signal est quasi stationnaire en ATR :** une enveloppe exprimée en ATR14(t) devrait mieux se transférer entre régimes qu'une enveloppe en bps.
- **L'écart Long/Short à +48 barres** a le signe de la dérive haussière du BTC (bêta, `RESEARCH_PHILOSOPHY.md` §4.2).
- **Les répétitions sont des signaux à contre-tendance** d'un mouvement plus long, dans un régime plus volatil et plus haché.

## 4. [DECISION] Orientations raisonnables (rien n'est lancé)

- **Jeu de descripteurs causaux pour l'Étape B,** sans les doublons :
  - `obs_dist_seg_atr`, `obs_lag_seg_bars`, `x1_already_flipped_at_t` ;
  - `nis_z_100`, `A_vol`, `log_R_rel` ;
  - `leg_atr`, `prev_seg_len`, `saturation`, `n_short_seg_48` ;
  - `run_rank` (rang 1 ou répétition).
- **Variables écartées de l'Étape B :**
  - `obs_*_cycle_*`, redondantes avec les versions segment ;
  - `peak_bps_vol`, redondante avec `A_vol` ;
  - `gap_prev_opp_bars`, redondante avec `gap_prev_any_bars` ;
  - `prev_seg_extreme_abs`, quasi constant.
- **Unités et découpage :** mesurer les excursions de l'Étape B en ATR14(t), séparément pour Long / Short et rang 1 / répétition. La réserve 2026 reste fermée.
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
