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
