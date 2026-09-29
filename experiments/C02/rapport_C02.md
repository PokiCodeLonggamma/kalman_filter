# EXP-C02 — Stop-loss en prix par sous-famille, en exécution séquentielle

- **Date :** 2026-09-29. **Étape :** C, enveloppe mécanique (deuxième test ; OFAT : le stop seul).
- **Actif et période :** BTC/USD Bitstamp 30 min, 2020-01 → 2025-12 (72 mois). 2026, ETH et XRP ne sont pas lus.
- **Univers :** six sous-ensembles de C01, définitions figées de B01 (`nis_z_100` Q4 exclu partout).

  | Groupe | Sous-ensemble | Candidats | Horizons |
  |---|---|---|---|
  | Essoufflement | R1 hors Q4 | 1 592 | 6, 13, 26 |
  | | ↳ F1 · x1 encore opposé hors Q4 (jambe ≥ 2,82 ATR) | 962 | 6, 13, 26 |
  | | ↳ F5 · x1 encore opposé hors Q4 (jambe < 2,82 ATR) | 630 | 6, 13, 26 |
  | Sortie de compression | ↳ F2b · x1 déjà retourné hors Q4 (candidat principal) | 741 | 13, 26, 48 |
  | | ↳ F3 · x1 déjà retourné hors Q4 | 711 | 13, 26, 48 |
  | | R2 hors Q4 (référence) | 1 452 | 13, 26, 48 |

- **Frais :** 5 et 10 bps aller-retour, déduits de chaque trade.
- **Capital (convention de l'Étape C, décision du porteur) :** 1 ATR14(t) = 0,25 % du capital, levier plafonné à 1x, frais proportionnels au notionnel. Elle vaut pour le PnL composé et le drawdown valorisé ; le notionnel 1x reste dans le CSV.
- **Reproduire :** `python experiments/C02/run_C02.py` (≈ 280 s) ; `--rapport` régénère ce rapport depuis les CSV ; tests : `python -m pytest tests`.

## 0. Cadrage (validé par le porteur)

- **QUESTION :** à horizon H fixé, le contrôle est la même configuration sans stop (C01). Un stop-loss intrabarre en prix peut être placé de deux façons :
  - SL-A : à k · ATR14(t) de open[t + 1] ;
  - SL-B : sur l'extremum causal du segment qualifiant, avec une marge δ · ATR14(t).

  Deux questions :
  1. Sur R1 hors Q4, F1 et F5 (H ∈ {6, 13, 26}), coupe-t-il la queue gauche et redresse-t-il l'espérance nette ?
  2. Sur F2b, F3 et R2 hors Q4 (H ∈ {13, 26, 48}), réduit-il le drawdown sans amputer la queue droite, notamment dans le trou d'air de F3 en 2024 ?
- **PERTINENCE POUR LE FILTRE AKF :** R1 porte une lourde queue gauche sans stop (P10 = −4,7 ATR à H26). F2b et F3 portent une asymétrie de queue droite, mais n'entrent pas au même point du range (`retrace_ratio` < 0,85 pour F2b, ≥ 0,85 pour F3).
- **CE QUE LE PROTOCOLE MESURE RÉELLEMENT :** l'impact marginal du stop (`apply_stop` de #KAKALMAN) face au contrôle sans stop, net de 5 et 10 bps, en séparant :
  - l'effet pur du stop, à entrées identiques ;
  - l'effet de réouverture séquentielle, quand le stop libère la position avant t + 1 + H.
- **CE QU'IL NE PERMET PAS DE CONCLURE :**
  - l'effet d'un take-profit, d'un break-even, d'un filtre macro ou du multiplexage R1 + R2 ;
  - une validation hors échantillon (régimes définis après B01, seuils calculés sur 2020-2025) ;
  - 198 paires (sous-ensemble, H, règle) sont testées dans chaque lecture : la meilleure est optimiste.

## 1. [CODE] Implémentation et contrôles

- **`src/envelope/stops.py`** (nouveau) :
  - `atr_stop_levels` (SL-A) ;
  - `segment_extremum` et `structural_stop_levels` (SL-B, plancher à 0,25 ATR de open[t + 1]) ;
  - `stop_distance` ;
  - `stop_trades` : exécution séquentielle à horizon fixe avec stop.

  Le niveau du stop ne lit que les barres ≤ t et open[t + 1]. `apply_stop` n'est pas modifié. Il reçoit, pour chaque trade, la distance relative side · (open[t + 1] − niveau) / open[t + 1]. Ce passage vectoriel donne le même résultat que les appels trade par trade (test).
- **Stop intrabarre** (convention certifiée de P6.5d) :
  - le stop est testé sur les barres t + 1 … t + H, barre d'entrée comprise ;
  - s'il est touché, la sortie se fait au niveau du stop, ou à l'ouverture si la barre ouvre au-delà ;
  - sinon, la sortie a lieu à open[t + 1 + H].

  Les gaps sont négligeables : au plus 0,4 % des trades.
- **Deux lectures :**
  - entrées figées : les trades de la course sans stop, dont seule la sortie change ;
  - séquentiel dynamique : un stop touché pendant la barre b libère la position, et le premier signal admissible est celui de la clôture de b (convention de `simulate_strategy`).
- **Métriques (`src/envelope/metrics.py`) :**
  - `mean_ci` donne les IC 95 % de l'espérance et du timing en bps et en ATR14(t). Le bootstrap est vectorisé : mêmes tirages de mois que `cluster_bootstrap`, bornes identiques à 10⁻⁹ près (test).
  - `effect_ci` mesure l'effet apparié (variante − contrôle) sur les mêmes entrées, avec son IC. Il est identique à 5 et 10 bps, les frais s'annulant.
  - `summarize_sized` ajoute le PF et la part des frais des PnL pondérés à 0,25 % par ATR.
- **Grille :** 6 sous-ensembles × 3 horizons × 12 règles (sans stop, SL-A k ∈ {1 ; 1,5 ; 2 ; 2,5 ; 3 ; 4 ; 5}, SL-B δ ∈ {0 ; 0,25 ; 0,5 ; 1}) × 2 lectures × 2 frais = 864 lignes. Bootstrap : 2 000 tirages.
- **Contrôles bloquants, tous passés :**
  - ancre P6.5d reproduite à l'identique, sans stop (6 037 trades) et avec stop à 2,5 % (6 589 trades, 780 stoppés) ;
  - les 24 contrôles sans stop communs avec C01 sont identiques (écart relatif ≤ 4,5·10⁻⁶, arrondi du CSV) ;
  - `stop_trades` sans stop redonne `time_stop_trades` ;
  - l'extremum de SL-B est celui de `obs_dist_seg_atr` (écart nul sur les 7 296 signaux).
- **Écart au cadrage, fenêtre de SL-B.** La formule du cadrage, `min(low[t − prev_seg_len + 1 : t + 1])`, omet la première barre du segment qualifiant tel que le code le définit (barres [t − prev_seg_len, t − 1]).
  - J'ai retenu l'horizon segment [t − prev_seg_len, t]. C'est celui de `obs_dist_seg_atr`, donc de `retrace_ratio` : le stop repose sur l'extremum dont les familles mesurent le retracement.
  - Les deux fenêtres diffèrent pour 932 signaux sur 7 296 : 6 % de R1 hors Q4, 20 % de F2b, 29 % de F3, 25 % de R2 hors Q4. L'écart médian est de 0,24 ATR.
  - Recalcul de contrôle, hors livrables : avec la fenêtre littérale, les 72 configurations SL-B (en séquentiel dynamique, 5 bps) changent d'espérance d'au plus 0,05 ATR ; le classement et les conclusions sont inchangés.
- **Tests :** 9 nouveaux dans `tests/test_envelope.py`.
  - Mèche et gap, pour un Long et pour un Short, et stop touché dans la barre d'entrée.
  - Extremum, marge et plancher de SL-B.
  - Distance vectorielle égale aux appels unitaires.
  - Absence de stop égale à C01.
  - Libération anticipée : lecture dynamique contre entrées figées.
  - Causalité des niveaux par troncature.
  - IC en bps et en ATR égaux au bootstrap de grappes.
  - Effet apparié.
  - Extremum du segment égal à celui de `retrace_ratio` sur BTC.

  Suite complète : 185 réussis, 2 ignorés.

## 2. [OBS] Mesures

### 2.1 Remarque du porteur : l'IC en ATR — vérifiée

- **ATR14 médian des barres de signal :** 80,3 bps en 2021 contre 33,6 bps en 2023. En notionnel fixe, 2021 pèse 2,4 fois plus en moyenne et 5,7 fois plus en variance.
- **Contrôles sans stop à H26, 5 bps :** seuls ces deux-là ont un IC en ATR entièrement positif, et leur timing aussi.

  | Sous-ensemble | Espérance en bps [IC] | Espérance en ATR [IC] | Timing en ATR [IC] |
  |---|---|---|---|
  | F2b · x1 déjà retourné hors Q4 | +11,5 [−2,9 ; +26,0] | +0,389 [+0,079 ; +0,700] | +0,388 [+0,076 ; +0,700] |
  | R2 hors Q4 | +12,3 [−1,5 ; +25,8] | +0,354 [+0,051 ; +0,643] | +0,344 [+0,045 ; +0,626] |

  À 10 bps, leurs IC en ATR contiennent 0 : +0,255 [−0,056 ; +0,569] et +0,218 [−0,088 ; +0,510].
- **Robustesse de F2b :** son espérance en ATR ne vient pas de quelques trades.
  - Moyenne winsorisée P1/P99 : +0,389, inchangée.
  - Sans ses 5 meilleurs trades : +0,232.
  - Médiane −0,05 ATR, P10 −4,4 et P90 +5,6 : l'espérance est portée par la queue droite (P90 + P10 = +1,15 ATR).
- **F5, sens inverse :** positif en bps à H6 et H13 (+3,1 et +3,5 bps), il est négatif en ATR (−0,044 et −0,106). Son avantage en bps vient des années très volatiles ; à risque constant, il disparaît.

### 2.2 Essoufflement — R1, F1, F5 : le stop coupe la queue gauche sans créer d'espérance

- **Effet pur (entrées figées) :**
  - aucun stop ne dégrade significativement ;
  - 3 effets sur 99 ont un IC > 0 (R1 H13 SL-A 5 ; F1 H13 SL-A 4 et 5), tous petits (+0,05 à +0,07 ATR). C'est de l'ordre de ce que le hasard donne sur 99 IC à 95 % ;
  - effets moyens : +0,020 ATR (R1), +0,037 (F1), +0,001 (F5).
- **Séquentiel dynamique :** aucune configuration n'a d'IC > 0.
  - Les meilleures sont F1 H26 SL-A 1,5 ATR (+0,087 ATR [−0,122 ; +0,294], +14 %, DD −16 %) et F1 H13 SL-A 2 (+0,062 [−0,101 ; +0,244]).
  - Ces gains ne résistent pas à la winsorisation P1/P99 : F1 H13 SL-A 2 passe de +0,062 à −0,002, F1 H26 SL-A 1,5 de +0,087 à +0,018.
  - L'écart au contrôle vient surtout de 2022.
  - Le niveau positif tient à un seul trade, commun à toutes les règles : un saut du 29 août 2023, en marché calme, vaut +44 ATR à lui seul. L'unité ATR amplifie ces sauts ; F2b n'y est pas sensible (§2.1).
- **Forme de la distribution** (R1 H26, sans stop → SL-B à l'extremum) :
  - médiane +0,09 → −0,81 ATR ;
  - P10 −4,7 → −1,6 ATR ; P90 +4,1 → +2,5 ATR ;
  - moyenne −0,111 → −0,035.

  Le stop coupe bien la queue gauche, mais une partie des trajectoires coupées aurait fini dans le sens du signal (`RESEARCH_INSIGHTS.md` §5 Q1).
- **Drawdown :** il baisse (R1 H26 : −44 % → −26 % avec SL-A 1,5 ; R1 H13 : −32 % → −19 à −22 %), mais le PnL de R1 reste ≤ +2 %.
- **F5 :** les stops resserrent la distribution autour d'un centre négatif. À H26, 7 règles sur 11 ont un IC entièrement négatif (SL-B à l'extremum : −0,165 [−0,306 ; −0,007]).
- **À 10 bps :** tout le groupe est négatif. R1 à H6 et H26 a un IC < 0 pour presque toutes les règles.

### 2.3 Sortie de compression — le stop détruit F2b, protège F3

- **F2b · x1 déjà retourné hors Q4, H26 (candidat principal) : chaque stop dégrade.**
  - L'effet pur est entièrement négatif pour 10 règles sur 11, de −0,22 à −0,38 ATR par trade. Seul SL-A 5 ATR fait −0,150 [−0,347 ; +0,040].
  - Espérance : +0,389 → +0,02 à +0,24 ATR.
  - PnL : +72 % → +3 à +38 %.
  - Drawdown : −13 %, pas amélioré (−12 à −22 %).
  - SL-A 2 ATR porte la médiane à −2,05 ATR : la moitié des trades sont coupés près de leur stop, et une partie des gagnants futurs avec eux. Les années 2023-2025 perdent l'essentiel de leur gain : +16 %, +13 %, +11 % → +2 %, +1 %, +1 %.
  - À H13, gains non significatifs (SL-A 1,5 : +0,087 [−0,021 ; +0,194]).
  - À H48, les stops serrés (SL-A 1 et 1,5, SL-B à l'extremum) réduisent le drawdown (−31 % → −17 à −19 %) mais abaissent l'espérance (+0,219 → +0,17 à +0,18 ATR). Le PnL monte (+18 % → +26 à +28 %), porté par ce drawdown plus faible et par les trades débloqués.
- **F3 · x1 déjà retourné hors Q4, H26 : un stop large protège.**
  - Avec SL-A 2 ATR ou SL-B à l'extremum :
    - drawdown −34 % → −14 % et −13 % ;
    - PnL +16 % → +33 % et +36 % ;
    - espérance +0,144 → +0,186 et +0,202 ATR ;
    - années positives 3/6 → 6/6.
  - L'année 2024 passe de −1,00 ATR par trade (−22 %) à +0,04 (SL-A 2) et +0,03 (SL-B).
  - L'effet pur, +0,09 ATR, a un IC qui contient 0.
  - Robustesse : sans ses 5 meilleurs trades, le contrôle tombe à +0,004 ATR ; avec SL-A 2 ou SL-B, il reste à +0,06 et +0,08.
  - À H48 : SL-A 5 fait +0,444 ATR [−0,017 ; +0,958], +49 %, drawdown −20 % (contrôle −47 %).
- **R2 hors Q4 mêle ces deux réponses opposées.** À H26, 7 règles sur 11 dégradent significativement. SL-A 5 ATR garde +0,286 ATR [+0,019 ; +0,562] (+93 %, drawdown −18 %) : c'est la seule configuration avec stop dont l'IC en ATR est positif.

**Tableau des 8 métriques — séquentiel dynamique, 5 bps** (PnL et drawdown à 0,25 % par ATR ; entre parenthèses, notionnel 1x)

| Métrique | F2b H26 sans stop | F2b H26 SL-A 5 | F3 H26 sans stop | F3 H26 SL-A 2 | F3 H26 SL-B extremum | R1 H13 sans stop | R1 H13 SL-A 2 |
|---|---|---|---|---|---|---|---|
| PnL net total | +72 % (+78 % ; +7 345 bps) | +38 % (+40 %) | +16 % (+48 %) | +33 % (+67 %) | +36 % (+72 %) | −16 % (−19 %) | +2 % (+3 %) |
| Profit factor : 1x ; pondéré | 1,17 ; 1,28 | 1,11 ; 1,16 | 1,13 ; 1,08 | 1,17 ; 1,17 | 1,18 ; 1,19 | 1,00 ; 0,96 | 1,02 ; 1,02 |
| Win rate | 49,6 % | 48,0 % | 47,4 % | 36,0 % | 36,5 % | 50,4 % | 45,6 % |
| Espérance : bps [IC] ; ATR [IC] | +11,5 [−2,9 ; +26,0] ; +0,389 [+0,079 ; +0,700] | +7,5 [−6,6 ; +21,4] ; +0,244 [−0,063 ; +0,544] | +9,3 [−12,4 ; +28,2] ; +0,144 [−0,293 ; +0,548] | +9,8 [−4,7 ; +24,0] ; +0,186 [−0,116 ; +0,496] | +10,4 [−3,3 ; +24,5] ; +0,202 [−0,106 ; +0,520] | −0,1 [−9,3 ; +9,3] ; −0,046 [−0,208 ; +0,121] | +1,1 [−5,9 ; +8,7] ; +0,013 [−0,102 ; +0,135] |
| Max drawdown valorisé | −13,2 % (−44,7 %) | −12,9 % (−42,9 %) | −33,7 % (−48,0 %) | −13,6 % (−26,1 %) | −12,9 % (−29,8 %) | −31,8 % (−53,6 %) | −21,5 % (−45,7 %) |
| Trades (/mois) ; stoppés | 639 (8,9) ; 0 % | 640 (8,9) ; 18 % | 601 (8,3) ; 0 % | 627 (8,7) ; 52 % | 620 (8,6) ; 50 % | 1 501 (20,8) ; 0 % | 1 513 (21,0) ; 35 % |
| Durée médiane | 26 barres | 26 | 26 | 24 | 26 | 13 | 13 |
| Part des frais (1x) ; brut/trade | 30 % ; +16,5 bps | 40 % ; +12,5 | 35 % ; +14,3 | 34 % ; +14,8 | 32 % ; +15,4 | 102 % ; +4,9 | 82 % ; +6,1 |

À 10 bps, aucune configuration n'a d'IC > 0 ni en bps ni en ATR. Espérances en ATR à 10 bps :

| Configuration | Espérance en ATR | PnL | Drawdown |
|---|---|---|---|
| F2b H26 sans stop | +0,255 | +42 % | −17 % |
| F2b H26 SL-A 5 | +0,110 | +14 % | −20 % |
| F3 H26 sans stop | +0,003 | −3 % | −39 % |
| F3 H26 SL-B extremum | +0,062 | +12 % | −16 % |
| R1 H13 SL-A 2 | −0,107 | −33 % | −38 % |

### 2.4 Entrées figées contre séquentiel dynamique

L'écart entre les deux lectures vient des trades débloqués par un stop :
- **R1 H26 :** 25 à 153 trades débloqués, d'espérance positive avec les stops serrés (+0,24 ATR avec SL-A 1 ; +0,43 avec SL-B à l'extremum). La lecture dynamique fait mieux : SL-B, −0,075 → −0,035 ATR ; PnL −23 % → −13 %.
- **F3 H26 :** 1 à 81 trades débloqués selon la règle, très négatifs (−0,2 à −1,0 ATR). La lecture dynamique fait moins bien : SL-A 2, +0,233 → +0,186 ATR ; PnL +41 % → +33 %.
- **F2b H26 :** au plus 48 débloqués ; effet marginal.
- **R2 H48 :** jusqu'à 383 débloqués, le plus souvent positifs.

La réentrée après un stop est donc un facteur à part entière : elle aide R1 et nuit à F3.

### 2.5 Stabilité annuelle (5 bps, séquentiel dynamique)

- **F2b H26 sans stop :** 5 années positives sur 6 (2021 : −0,15 ATR). Les stops effacent surtout 2023-2025.
- **F3 H26, SL-A 2 et SL-B :** 6 années sur 6. Le stop supprime le trou de 2024 mais divise par deux environ les gains de 2020, 2021 et 2025.
- **R1 H13 :** au mieux 4 années positives sur 6 (SL-A 5), 3 pour SL-A 1 à 4.

## 3. [HYP] Lectures

- **Le point d'entrée dans le range décide de l'effet du stop.**
  - F2b entre au milieu du range (retracement 0,50 à 0,85). Ses gains arrivent après des excursions adverses de 1 à 3 ATR : un stop dans la fenêtre de 26 barres coupe des gagnants futurs.
  - F3 entre près de l'extrémité opposée (retracement ≥ 0,85). Quand il échoue, il échoue franchement (2024) : le stop coupe l'échec.
- **R1 :** l'avantage de B01 était une médiane positive à court terme, avec une lourde queue gauche. Le stop échange cette queue contre une médiane négative, et l'espérance ne change presque pas. Les trajectoires coupées ne sont pas des reprises de tendance franches : une partie revient dans le sens du signal.
- **Réouverture :**
  - après un stop sur R1, le signal suivant garde de l'information ;
  - après un stop sur F3, les échecs se suivent : les trades débloqués prolongent la même structure perdante.
- **F5 :** son avantage à court terme, en bps, est un effet de pondération par la volatilité.

## 4. [DECISION] Orientations (rien n'est lancé)

- **À POURSUIVRE, par sous-famille :**
  - **F2b · x1 déjà retourné hors Q4 : pas de stop à H26.** Chaque stop coûte 0,15 à 0,38 ATR par trade sans réduire le drawdown. Si un stop de catastrophe est exigé pour le risque, SL-A 5 ATR est le moins coûteux (−0,15 ATR, IC [−0,35 ; +0,04]).
  - **F3 · x1 déjà retourné hors Q4 : SL-B à l'extremum (δ = 0) ou SL-A 2 ATR, à H26.** Drawdown −34 % → −13 %, 6 années positives sur 6, trou de 2024 effacé. En revanche, l'effet moyen n'est pas significatif et il tient à 2024.
  - **R2 hors Q4, traité comme un bloc : sans objet.** Ses deux composantes répondent en sens contraire au stop.
- **NON CONCLUANT à REJETÉ — R1 hors Q4, F1, F5.** Aucune règle de stop ne produit d'espérance nette positive ; à 10 bps, tout est négatif ; F5 est négatif en ATR à tous les horizons.
- **Points à trancher avant C02bis :**
  1. La place de R1 dans le moteur de régimes : pas de routage, ou attente d'un autre facteur (take-profit, break-even).
  2. Un stop de catastrophe pour F2b, ou aucun.
  3. La règle de réentrée après un stop, facteur séparé (utile à R1, nuisible à F3).
  4. Les frais canoniques : à 10 bps, seules les estimations centrales de F2b et R2 restent nettement positives.
  5. Le hold-out.

  C02bis n'est pas lancé.

---

# Annexes chiffrées (générées par `run_C02.py`)

## A. Contrôles bloquants et conventions

| Contrôle | Résultat |
|---|---|
| Ancre P6.5d sans stop | 6 037 trades identiques au fichier de référence |
| Ancre P6.5d, stop 2,5 % (exécution des stops par `apply_stop` sur BTC) | 6 589 trades identiques, dont 780 stoppés et 0 gaps |
| Contrôles sans stop = C01 | 24 lignes (4 sous-ensembles communs × 3 horizons × 2 frais) ; écart relatif max 4,5·10⁻⁶ (arrondi du CSV de C01) |
| `stop_trades` sans stop = `time_stop_trades` | identiques pour les 18 paires (sous-ensemble, H) |
| Extremum de SL-B = extremum de `obs_dist_seg_atr` (horizon [t − prev_seg_len, t]) | écart max 0 ATR sur 7 296 signaux |
| Fenêtre littérale du cadrage [t − prev_seg_len + 1, t] | extremum différent pour 932 signaux sur 7 296 (écart médian 0,24 ATR) ; par sous-ensemble : R1 hors nis_z_100 Q4 102, F1 · x1 encore opposé hors nis_z_100 Q4 21, F5 · x1 encore opposé hors nis_z_100 Q4 81, F2b · x1 déjà retourné hors nis_z_100 Q4 151, F3 · x1 déjà retourné hors nis_z_100 Q4 205, R2 hors nis_z_100 Q4 356 |
| IC 95 % | bootstrap de grappes (mois civils d'entrée), 2 000 tirages, graine 0 |
| Capital | 1 ATR14(t) = 0,25 % du capital, levier plafonné à 1x, frais proportionnels au notionnel ; notionnel 1x dans le CSV |
| Période | 2020-01 → 2025-12 (72 mois) ; aucune barre de 2026 lue |

## B. Distance entre l'entrée et le stop SL-B, en ATR14(t)

Tous les signaux candidats. Cellule : médiane [P10 ; P90] ; part des signaux où le plancher de 0,25 ATR s'applique. SL-A : distance fixe k.

| Sous-ensemble | SL-B extremum + 0,00 ATR | SL-B extremum + 0,25 ATR | SL-B extremum + 0,50 ATR | SL-B extremum + 1,00 ATR |
|---|---|---|---|---|
| R1 hors nis_z_100 Q4 | 0,97 [0,41 ; 1,70] ; 4 % | 1,22 [0,66 ; 1,95] ; 0 % | 1,47 [0,91 ; 2,20] ; 0 % | 1,97 [1,41 ; 2,70] ; 0 % |
| ↳ F1 · x1 encore opposé hors nis_z_100 Q4 | 1,21 [0,53 ; 1,90] ; 2 % | 1,46 [0,78 ; 2,15] ; 0 % | 1,71 [1,03 ; 2,40] ; 0 % | 2,21 [1,53 ; 2,90] ; 0 % |
| ↳ F5 · x1 encore opposé hors nis_z_100 Q4 | 0,75 [0,32 ; 1,13] ; 7 % | 1,00 [0,57 ; 1,38] ; 0 % | 1,25 [0,82 ; 1,63] ; 0 % | 1,75 [1,32 ; 2,13] ; 0 % |
| ↳ F2b · x1 déjà retourné hors nis_z_100 Q4 | 1,53 [1,13 ; 1,99] ; 0 % | 1,78 [1,38 ; 2,24] ; 0 % | 2,03 [1,63 ; 2,49] ; 0 % | 2,53 [2,13 ; 2,99] ; 0 % |
| ↳ F3 · x1 déjà retourné hors nis_z_100 Q4 | 2,10 [1,59 ; 2,64] ; 0 % | 2,35 [1,84 ; 2,89] ; 0 % | 2,60 [2,09 ; 3,14] ; 0 % | 3,10 [2,59 ; 3,64] ; 0 % |
| R2 hors nis_z_100 Q4 | 1,78 [1,24 ; 2,47] ; 0 % | 2,03 [1,49 ; 2,72] ; 0 % | 2,28 [1,74 ; 2,97] ; 0 % | 2,78 [2,24 ; 3,47] ; 0 % |

## C. Contrôles sans stop : IC 95 % en bps et en ATR14(t)

| Sous-ensemble | H | Trades | 5 bps : espérance bps [IC] | 5 bps : espérance ATR [IC] | 10 bps : espérance bps [IC] | 10 bps : espérance ATR [IC] | 5 bps : timing ATR [IC] |
|---|---|---|---|---|---|---|---|
| R1 hors nis_z_100 Q4 | H = 6 | 1 592 | +0,0 [−5,0 ; +4,8] | −0,031 [−0,118 ; +0,062] | −5,0 [−10,0 ; −0,2] | −0,152 [−0,235 ; −0,059] | −0,023 [−0,111 ; +0,075] |
| R1 hors nis_z_100 Q4 | H = 13 | 1 501 | −0,1 [−9,3 ; +9,3] | −0,046 [−0,208 ; +0,121] | −5,1 [−14,3 ; +4,3] | −0,165 [−0,328 ; +0,001] | −0,043 [−0,216 ; +0,136] |
| R1 hors nis_z_100 Q4 | H = 26 | 1 263 | −4,9 [−17,3 ; +7,0] | −0,111 [−0,311 ; +0,090] | −9,9 [−22,3 ; +2,0] | −0,230 [−0,429 ; −0,028] | −0,087 [−0,303 ; +0,125] |
| ↳ F1 · x1 encore opposé hors nis_z_100 Q4 | H = 6 | 962 | −2,0 [−8,4 ; +4,4] | −0,023 [−0,133 ; +0,107] | −7,0 [−13,4 ; −0,6] | −0,134 [−0,241 ; −0,006] | −0,005 [−0,119 ; +0,133] |
| ↳ F1 · x1 encore opposé hors nis_z_100 Q4 | H = 13 | 950 | −3,0 [−14,6 ; +8,5] | −0,023 [−0,220 ; +0,183] | −8,0 [−19,6 ; +3,5] | −0,134 [−0,329 ; +0,070] | −0,014 [−0,230 ; +0,211] |
| ↳ F1 · x1 encore opposé hors nis_z_100 Q4 | H = 26 | 840 | −4,8 [−23,8 ; +10,8] | −0,044 [−0,333 ; +0,228] | −9,8 [−28,8 ; +5,8] | −0,155 [−0,446 ; +0,118] | −0,016 [−0,303 ; +0,252] |
| ↳ F5 · x1 encore opposé hors nis_z_100 Q4 | H = 6 | 630 | +3,1 [−5,7 ; +12,3] | −0,044 [−0,184 ; +0,088] | −1,9 [−10,7 ; +7,3] | −0,179 [−0,319 ; −0,046] | −0,057 [−0,201 ; +0,079] |
| ↳ F5 · x1 encore opposé hors nis_z_100 Q4 | H = 13 | 604 | +3,5 [−8,5 ; +15,5] | −0,106 [−0,349 ; +0,129] | −1,5 [−13,5 ; +10,5] | −0,238 [−0,489 ; +0,003] | −0,123 [−0,371 ; +0,107] |
| ↳ F5 · x1 encore opposé hors nis_z_100 Q4 | H = 26 | 572 | −6,6 [−25,0 ; +11,4] | −0,274 [−0,638 ; +0,089] | −11,6 [−30,0 ; +6,4] | −0,406 [−0,771 ; −0,043] | −0,298 [−0,689 ; +0,065] |
| ↳ F2b · x1 déjà retourné hors nis_z_100 Q4 | H = 13 | 695 | +3,9 [−7,0 ; +15,2] | +0,022 [−0,198 ; +0,240] | −1,1 [−12,0 ; +10,2] | −0,113 [−0,341 ; +0,105] | +0,022 [−0,199 ; +0,239] |
| ↳ F2b · x1 déjà retourné hors nis_z_100 Q4 | H = 26 | 639 | +11,5 [−2,9 ; +26,0] | +0,389 [+0,079 ; +0,700] | +6,5 [−7,9 ; +21,0] | +0,255 [−0,056 ; +0,569] | +0,388 [+0,076 ; +0,700] |
| ↳ F2b · x1 déjà retourné hors nis_z_100 Q4 | H = 48 | 564 | +3,4 [−18,7 ; +24,7] | +0,219 [−0,313 ; +0,768] | −1,6 [−23,7 ; +19,7] | +0,086 [−0,437 ; +0,633] | +0,221 [−0,311 ; +0,773] |
| ↳ F3 · x1 déjà retourné hors nis_z_100 Q4 | H = 13 | 646 | −2,9 [−13,9 ; +7,6] | +0,007 [−0,232 ; +0,253] | −7,9 [−18,9 ; +2,6] | −0,135 [−0,372 ; +0,109] | +0,006 [−0,233 ; +0,245] |
| ↳ F3 · x1 déjà retourné hors nis_z_100 Q4 | H = 26 | 601 | +9,3 [−12,4 ; +28,2] | +0,144 [−0,293 ; +0,548] | +4,3 [−17,4 ; +23,2] | +0,003 [−0,437 ; +0,415] | +0,122 [−0,319 ; +0,530] |
| ↳ F3 · x1 déjà retourné hors nis_z_100 Q4 | H = 48 | 523 | +2,8 [−22,9 ; +26,9] | +0,201 [−0,407 ; +0,812] | −2,2 [−27,9 ; +21,9] | +0,065 [−0,542 ; +0,665] | +0,251 [−0,317 ; +0,815] |
| R2 hors nis_z_100 Q4 | H = 13 | 1 240 | +0,3 [−8,9 ; +8,8] | +0,031 [−0,146 ; +0,208] | −4,7 [−13,9 ; +3,8] | −0,106 [−0,283 ; +0,073] | +0,034 [−0,144 ; +0,207] |
| R2 hors nis_z_100 Q4 | H = 26 | 1 080 | +12,3 [−1,5 ; +25,8] | +0,354 [+0,051 ; +0,643] | +7,3 [−6,5 ; +20,8] | +0,218 [−0,088 ; +0,510] | +0,344 [+0,045 ; +0,626] |
| R2 hors nis_z_100 Q4 | H = 48 | 864 | −2,9 [−21,5 ; +16,3] | +0,071 [−0,381 ; +0,508] | −7,9 [−26,5 ; +11,3] | −0,064 [−0,512 ; +0,372] | +0,055 [−0,379 ; +0,479] |

**ATR14 médian (bps), par année**

| Mesure | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 |
|---|---|---|---|---|---|---|
| Toutes les barres | 57,4 | 80,0 | 55,8 | 34,4 | 46,7 | 37,2 |
| Barres des 7 296 signaux | 57,3 | 80,3 | 54,8 | 33,6 | 45,9 | 36,8 |

## D. Profils des stops, par sous-ensemble et horizon

Espérance, timing et effet : nets, par trade, en ATR14(t) ou en bps. PnL composé et MDD valorisé : capital à 0,25 % par ATR. PF 1x : gains / pertes des trades en bps nets ; PF pondéré : des PnL à 0,25 % par ATR. Effet pur : moyenne appariée (stop − sans stop) sur les entrées de la course sans stop, identique à 5 et 10 bps. Débloqués : trades du séquentiel dynamique absents de la course figée.

### Essoufflement — R1 hors nis_z_100 Q4

#### R1 hors nis_z_100 Q4 — H = 6

**5 bps aller-retour**

| Stop | Stoppés : figé ; dyn. | Effet pur, entrées figées : ATR [IC 95 %] | Figé : espérance ATR [IC] | Dyn. : PnL composé ; MDD valorisé | Dyn. : PF 1x ; PF pondéré ; WR | Dyn. : espérance bps [IC] ; ATR [IC] | Dyn. : timing ATR [IC] | Dyn. : trades ; /mois ; débloqués | Dyn. : durée méd. | Dyn. : part des frais ; brut/trade |
|---|---|---|---|---|---|---|---|---|---|---|
| Sans stop (contrôle) | 0 % ; 0 % | — | −0,031 [−0,118 ; +0,062] | −12 % ; −20 % | 1,00 ; 0,95 ; 54 % | +0,0 [−5,0 ; +4,8] ; −0,031 [−0,118 ; +0,062] | −0,023 [−0,111 ; +0,075] | 1 592 ; 22,1 ; 0 | 6 | 100 % ; +5,0 |
| SL-A 1,0 ATR | 44 % ; 44 % | +0,008 [−0,042 ; +0,058] | −0,023 [−0,100 ; +0,061] | −12 % ; −19 % | 0,93 ; 0,95 ; 43 % | −2,1 [−5,7 ; +1,9] ; −0,023 [−0,100 ; +0,061] | −0,018 [−0,100 ; +0,070] | 1 592 ; 22,1 ; 0 | 6 | 170 % ; +2,9 |
| SL-A 1,5 ATR | 29 % ; 29 % | +0,011 [−0,036 ; +0,056] | −0,020 [−0,094 ; +0,065] | −10 % ; −15 % | 0,99 ; 0,96 ; 49 % | −0,3 [−4,7 ; +4,1] ; −0,020 [−0,094 ; +0,065] | −0,016 [−0,095 ; +0,075] | 1 592 ; 22,1 ; 0 | 6 | 106 % ; +4,7 |
| SL-A 2,0 ATR | 19 % ; 19 % | +0,027 [−0,015 ; +0,066] | −0,004 [−0,080 ; +0,078] | −3 % ; −15 % | 1,03 ; 0,99 ; 52 % | +1,0 [−3,4 ; +5,1] ; −0,004 [−0,080 ; +0,078] | +0,001 [−0,077 ; +0,088] | 1 592 ; 22,1 ; 0 | 6 | 83 % ; +6,0 |
| SL-A 2,5 ATR | 14 % ; 14 % | +0,008 [−0,031 ; +0,045] | −0,023 [−0,100 ; +0,061] | −10 % ; −18 % | 1,00 ; 0,96 ; 53 % | −0,1 [−4,5 ; +4,1] ; −0,023 [−0,100 ; +0,061] | −0,018 [−0,097 ; +0,068] | 1 592 ; 22,1 ; 0 | 6 | 101 % ; +4,9 |
| SL-A 3,0 ATR | 10 % ; 10 % | −0,001 [−0,036 ; +0,033] | −0,033 [−0,111 ; +0,051] | −13 % ; −22 % | 0,98 ; 0,95 ; 53 % | −0,6 [−5,1 ; +3,7] ; −0,033 [−0,111 ; +0,051] | −0,027 [−0,107 ; +0,061] | 1 592 ; 22,1 ; 0 | 6 | 114 % ; +4,4 |
| SL-A 4,0 ATR | 5 % ; 5 % | −0,007 [−0,036 ; +0,021] | −0,039 [−0,122 ; +0,050] | −15 % ; −23 % | 0,98 ; 0,94 ; 53 % | −0,8 [−5,6 ; +3,8] ; −0,039 [−0,122 ; +0,050] | −0,030 [−0,116 ; +0,066] | 1 592 ; 22,1 ; 0 | 6 | 118 % ; +4,2 |
| SL-A 5,0 ATR | 3 % ; 3 % | +0,008 [−0,014 ; +0,030] | −0,024 [−0,104 ; +0,064] | −9 % ; −19 % | 1,01 ; 0,97 ; 53 % | +0,3 [−4,5 ; +4,8] ; −0,024 [−0,104 ; +0,064] | −0,013 [−0,095 ; +0,078] | 1 592 ; 22,1 ; 0 | 6 | 94 % ; +5,3 |
| SL-B extremum + 0,00 ATR | 45 % ; 45 % | +0,020 [−0,030 ; +0,072] | −0,012 [−0,081 ; +0,069] | −7 % ; −18 % | 0,96 ; 0,97 ; 41 % | −1,2 [−4,5 ; +2,3] ; −0,012 [−0,081 ; +0,069] | −0,008 [−0,082 ; +0,079] | 1 592 ; 22,1 ; 0 | 6 | 131 % ; +3,8 |
| SL-B extremum + 0,25 ATR | 40 % ; 40 % | −0,017 [−0,067 ; +0,036] | −0,049 [−0,124 ; +0,038] | −20 % ; −22 % | 0,90 ; 0,90 ; 43 % | −3,1 [−7,1 ; +1,0] ; −0,049 [−0,124 ; +0,038] | −0,045 [−0,121 ; +0,045] | 1 592 ; 22,1 ; 0 | 6 | 256 % ; +1,9 |
| SL-B extremum + 0,50 ATR | 33 % ; 33 % | −0,016 [−0,064 ; +0,034] | −0,047 [−0,118 ; +0,032] | −19 % ; −21 % | 0,93 ; 0,91 ; 47 % | −2,1 [−6,0 ; +2,0] ; −0,047 [−0,118 ; +0,032] | −0,044 [−0,117 ; +0,041] | 1 592 ; 22,1 ; 0 | 6 | 170 % ; +2,9 |
| SL-B extremum + 1,00 ATR | 21 % ; 21 % | +0,007 [−0,038 ; +0,051] | −0,025 [−0,096 ; +0,055] | −10 % ; −18 % | 0,99 ; 0,96 ; 51 % | −0,3 [−4,6 ; +4,1] ; −0,025 [−0,096 ; +0,055] | −0,018 [−0,093 ; +0,069] | 1 592 ; 22,1 ; 0 | 6 | 106 % ; +4,7 |

**10 bps aller-retour**

| Stop | Figé : espérance ATR [IC] | Dyn. : PnL composé ; MDD valorisé | Dyn. : PF 1x ; PF pondéré ; WR | Dyn. : espérance bps [IC] ; ATR [IC] | Dyn. : timing ATR [IC] | Dyn. : part des frais ; brut/trade |
|---|---|---|---|---|---|---|
| Sans stop (contrôle) | −0,152 [−0,235 ; −0,059] | −44 % ; −45 % | 0,86 ; 0,79 ; 49 % | −5,0 [−10,0 ; −0,2] ; −0,152 [−0,235 ; −0,059] | −0,144 [−0,232 ; −0,047] | 199 % ; +5,0 |
| SL-A 1,0 ATR | −0,144 [−0,218 ; −0,061] | −43 % ; −45 % | 0,78 ; 0,76 ; 40 % | −7,1 [−10,7 ; −3,1] ; −0,144 [−0,218 ; −0,061] | −0,139 [−0,218 ; −0,052] | 340 % ; +2,9 |
| SL-A 1,5 ATR | −0,141 [−0,214 ; −0,060] | −42 % ; −44 % | 0,84 ; 0,79 ; 46 % | −5,3 [−9,7 ; −0,9] ; −0,141 [−0,214 ; −0,060] | −0,137 [−0,212 ; −0,049] | 211 % ; +4,7 |
| SL-A 2,0 ATR | −0,125 [−0,199 ; −0,045] | −38 % ; −40 % | 0,88 ; 0,82 ; 48 % | −4,0 [−8,4 ; +0,1] ; −0,125 [−0,199 ; −0,045] | −0,119 [−0,196 ; −0,034] | 166 % ; +6,0 |
| SL-A 2,5 ATR | −0,144 [−0,219 ; −0,062] | −42 % ; −44 % | 0,86 ; 0,80 ; 49 % | −5,1 [−9,5 ; −0,9] ; −0,144 [−0,219 ; −0,062] | −0,139 [−0,217 ; −0,056] | 202 % ; +4,9 |
| SL-A 3,0 ATR | −0,153 [−0,230 ; −0,071] | −44 % ; −46 % | 0,84 ; 0,79 ; 49 % | −5,6 [−10,1 ; −1,3] ; −0,153 [−0,230 ; −0,071] | −0,147 [−0,227 ; −0,062] | 228 % ; +4,4 |
| SL-A 4,0 ATR | −0,159 [−0,240 ; −0,073] | −45 % ; −47 % | 0,84 ; 0,78 ; 49 % | −5,8 [−10,6 ; −1,2] ; −0,159 [−0,240 ; −0,073] | −0,150 [−0,233 ; −0,060] | 237 % ; +4,2 |
| SL-A 5,0 ATR | −0,144 [−0,223 ; −0,058] | −42 % ; −43 % | 0,87 ; 0,80 ; 49 % | −4,7 [−9,5 ; −0,2] ; −0,144 [−0,223 ; −0,058] | −0,134 [−0,215 ; −0,044] | 188 % ; +5,3 |
| SL-B extremum + 0,00 ATR | −0,132 [−0,200 ; −0,053] | −40 % ; −42 % | 0,80 ; 0,77 ; 38 % | −6,2 [−9,5 ; −2,7] ; −0,132 [−0,200 ; −0,053] | −0,128 [−0,200 ; −0,046] | 261 % ; +3,8 |
| SL-B extremum + 0,25 ATR | −0,169 [−0,242 ; −0,087] | −48 % ; −49 % | 0,76 ; 0,73 ; 40 % | −8,1 [−12,1 ; −4,0] ; −0,169 [−0,242 ; −0,087] | −0,166 [−0,242 ; −0,078] | 513 % ; +1,9 |
| SL-B extremum + 0,50 ATR | −0,168 [−0,236 ; −0,091] | −48 % ; −49 % | 0,80 ; 0,75 ; 43 % | −7,1 [−11,0 ; −3,0] ; −0,168 [−0,236 ; −0,091] | −0,165 [−0,237 ; −0,083] | 340 % ; +2,9 |
| SL-B extremum + 1,00 ATR | −0,145 [−0,215 ; −0,069] | −42 % ; −44 % | 0,85 ; 0,79 ; 47 % | −5,3 [−9,6 ; −0,9] ; −0,145 [−0,215 ; −0,069] | −0,138 [−0,213 ; −0,056] | 211 % ; +4,7 |

#### R1 hors nis_z_100 Q4 — H = 13

**5 bps aller-retour**

| Stop | Stoppés : figé ; dyn. | Effet pur, entrées figées : ATR [IC 95 %] | Figé : espérance ATR [IC] | Dyn. : PnL composé ; MDD valorisé | Dyn. : PF 1x ; PF pondéré ; WR | Dyn. : espérance bps [IC] ; ATR [IC] | Dyn. : timing ATR [IC] | Dyn. : trades ; /mois ; débloqués | Dyn. : durée méd. | Dyn. : part des frais ; brut/trade |
|---|---|---|---|---|---|---|---|---|---|---|
| Sans stop (contrôle) | 0 % ; 0 % | — | −0,046 [−0,208 ; +0,121] | −16 % ; −32 % | 1,00 ; 0,96 ; 50 % | −0,1 [−9,3 ; +9,3] ; −0,046 [−0,208 ; +0,121] | −0,043 [−0,216 ; +0,136] | 1 501 ; 20,8 ; 0 | 13 | 102 % ; +4,9 |
| SL-A 1,0 ATR | 61 % ; 61 % | +0,027 [−0,092 ; +0,147] | −0,019 [−0,128 ; +0,098] | −10 % ; −28 % | 0,95 ; 0,97 ; 33 % | −1,9 [−7,5 ; +3,7] ; −0,017 [−0,126 ; +0,097] | −0,016 [−0,129 ; +0,107] | 1 536 ; 21,3 ; 36 | 8 | 163 % ; +3,1 |
| SL-A 1,5 ATR | 46 % ; 46 % | +0,043 [−0,079 ; +0,159] | −0,003 [−0,119 ; +0,122] | −3 % ; −22 % | 1,00 ; 1,00 ; 41 % | −0,2 [−7,3 ; +7,2] ; −0,000 [−0,114 ; +0,122] | −0,001 [−0,120 ; +0,126] | 1 523 ; 21,2 ; 23 | 13 | 103 % ; +4,8 |
| SL-A 2,0 ATR | 35 % ; 35 % | +0,056 [−0,040 ; +0,153] | +0,011 [−0,105 ; +0,134] | +2 % ; −22 % | 1,02 ; 1,02 ; 46 % | +1,1 [−5,9 ; +8,7] ; +0,013 [−0,102 ; +0,135] | +0,016 [−0,105 ; +0,146] | 1 513 ; 21,0 ; 13 | 13 | 82 % ; +6,1 |
| SL-A 2,5 ATR | 27 % ; 27 % | +0,058 [−0,031 ; +0,145] | +0,013 [−0,119 ; +0,145] | +1 % ; −20 % | 1,01 ; 1,01 ; 48 % | +0,6 [−7,3 ; +9,1] ; +0,007 [−0,124 ; +0,140] | +0,008 [−0,128 ; +0,148] | 1 508 ; 20,9 ; 7 | 13 | 89 % ; +5,6 |
| SL-A 3,0 ATR | 21 % ; 20 % | +0,051 [−0,022 ; +0,129] | +0,005 [−0,133 ; +0,145] | +0 % ; −19 % | 1,02 ; 1,01 ; 49 % | +0,7 [−7,5 ; +9,5] ; +0,006 [−0,132 ; +0,143] | +0,008 [−0,133 ; +0,154] | 1 505 ; 20,9 ; 4 | 13 | 87 % ; +5,7 |
| SL-A 4,0 ATR | 13 % ; 13 % | +0,047 [−0,012 ; +0,111] | +0,002 [−0,134 ; +0,144] | −0 % ; −19 % | 1,02 ; 1,01 ; 50 % | +1,0 [−7,5 ; +9,6] ; +0,001 [−0,136 ; +0,142] | +0,009 [−0,137 ; +0,160] | 1 504 ; 20,9 ; 3 | 13 | 84 % ; +6,0 |
| SL-A 5,0 ATR | 7 % ; 7 % | +0,055 [+0,007 ; +0,107] | +0,009 [−0,132 ; +0,156] | +2 % ; −19 % | 1,03 ; 1,02 ; 50 % | +1,4 [−7,2 ; +10,2] ; +0,009 [−0,132 ; +0,156] | +0,018 [−0,132 ; +0,174] | 1 501 ; 20,8 ; 0 | 13 | 79 % ; +6,4 |
| SL-B extremum + 0,00 ATR | 60 % ; 60 % | +0,027 [−0,096 ; +0,150] | −0,019 [−0,127 ; +0,099] | −8 % ; −29 % | 0,95 ; 0,97 ; 31 % | −1,8 [−6,8 ; +3,6] ; −0,014 [−0,118 ; +0,100] | −0,013 [−0,123 ; +0,110] | 1 532 ; 21,3 ; 32 | 9 | 154 % ; +3,2 |
| SL-B extremum + 0,25 ATR | 55 % ; 55 % | −0,020 [−0,144 ; +0,103] | −0,066 [−0,176 ; +0,053] | −26 % ; −35 % | 0,89 ; 0,90 ; 34 % | −4,4 [−10,0 ; +1,4] ; −0,070 [−0,176 ; +0,046] | −0,069 [−0,181 ; +0,055] | 1 524 ; 21,2 ; 24 | 10 | 885 % ; +0,6 |
| SL-B extremum + 0,50 ATR | 49 % ; 49 % | +0,001 [−0,111 ; +0,116] | −0,045 [−0,160 ; +0,079] | −20 % ; −30 % | 0,95 ; 0,93 ; 38 % | −2,3 [−9,4 ; +4,9] ; −0,050 [−0,161 ; +0,070] | −0,051 [−0,167 ; +0,077] | 1 519 ; 21,1 ; 19 | 13 | 188 % ; +2,7 |
| SL-B extremum + 1,00 ATR | 37 % ; 37 % | +0,043 [−0,050 ; +0,143] | −0,002 [−0,126 ; +0,128] | −6 % ; −22 % | 0,99 ; 0,99 ; 44 % | −0,4 [−8,0 ; +7,6] ; −0,009 [−0,130 ; +0,120] | −0,003 [−0,131 ; +0,135] | 1 513 ; 21,0 ; 13 | 13 | 108 % ; +4,6 |

**10 bps aller-retour**

| Stop | Figé : espérance ATR [IC] | Dyn. : PnL composé ; MDD valorisé | Dyn. : PF 1x ; PF pondéré ; WR | Dyn. : espérance bps [IC] ; ATR [IC] | Dyn. : timing ATR [IC] | Dyn. : part des frais ; brut/trade |
|---|---|---|---|---|---|---|
| Sans stop (contrôle) | −0,165 [−0,328 ; +0,001] | −44 % ; −51 % | 0,90 ; 0,85 ; 47 % | −5,1 [−14,3 ; +4,3] ; −0,165 [−0,328 ; +0,001] | −0,162 [−0,335 ; +0,013] | 204 % ; +4,9 |
| SL-A 1,0 ATR | −0,138 [−0,247 ; −0,022] | −41 % ; −47 % | 0,83 ; 0,82 ; 31 % | −6,9 [−12,5 ; −1,3] ; −0,137 [−0,245 ; −0,023] | −0,136 [−0,249 ; −0,014] | 326 % ; +3,1 |
| SL-A 1,5 ATR | −0,122 [−0,239 ; +0,002] | −37 % ; −42 % | 0,89 ; 0,87 ; 39 % | −5,2 [−12,3 ; +2,2] ; −0,120 [−0,235 ; +0,001] | −0,121 [−0,238 ; +0,005] | 206 % ; +4,8 |
| SL-A 2,0 ATR | −0,109 [−0,223 ; +0,015] | −33 % ; −38 % | 0,92 ; 0,89 ; 43 % | −3,9 [−10,9 ; +3,7] ; −0,107 [−0,225 ; +0,017] | −0,104 [−0,224 ; +0,024] | 164 % ; +6,1 |
| SL-A 2,5 ATR | −0,107 [−0,235 ; +0,028] | −34 % ; −42 % | 0,91 ; 0,89 ; 45 % | −4,4 [−12,3 ; +4,1] ; −0,113 [−0,240 ; +0,021] | −0,111 [−0,246 ; +0,029] | 178 % ; +5,6 |
| SL-A 3,0 ATR | −0,114 [−0,250 ; +0,028] | −34 % ; −42 % | 0,92 ; 0,89 ; 46 % | −4,3 [−12,5 ; +4,5] ; −0,114 [−0,249 ; +0,026] | −0,111 [−0,252 ; +0,037] | 174 % ; +5,7 |
| SL-A 4,0 ATR | −0,118 [−0,254 ; +0,025] | −34 % ; −43 % | 0,92 ; 0,89 ; 47 % | −4,0 [−12,5 ; +4,6] ; −0,119 [−0,254 ; +0,022] | −0,111 [−0,253 ; +0,040] | 168 % ; +6,0 |
| SL-A 5,0 ATR | −0,110 [−0,248 ; +0,038] | −32 % ; −41 % | 0,93 ; 0,90 ; 47 % | −3,6 [−12,2 ; +5,2] ; −0,110 [−0,248 ; +0,038] | −0,101 [−0,253 ; +0,056] | 157 % ; +6,4 |
| SL-B extremum + 0,00 ATR | −0,139 [−0,247 ; −0,019] | −40 % ; −45 % | 0,83 ; 0,82 ; 30 % | −6,8 [−11,8 ; −1,4] ; −0,133 [−0,239 ; −0,018] | −0,133 [−0,244 ; −0,009] | 309 % ; +3,2 |
| SL-B extremum + 0,25 ATR | −0,185 [−0,298 ; −0,066] | −51 % ; −55 % | 0,79 ; 0,77 ; 32 % | −9,4 [−15,0 ; −3,6] ; −0,189 [−0,299 ; −0,072] | −0,189 [−0,300 ; −0,063] | > 1 000 % ; +0,6 |
| SL-B extremum + 0,50 ATR | −0,165 [−0,280 ; −0,041] | −47 % ; −51 % | 0,84 ; 0,81 ; 36 % | −7,3 [−14,4 ; −0,1] ; −0,170 [−0,282 ; −0,047] | −0,171 [−0,288 ; −0,041] | 377 % ; +2,7 |
| SL-B extremum + 1,00 ATR | −0,122 [−0,243 ; +0,009] | −38 % ; −44 % | 0,89 ; 0,87 ; 42 % | −5,4 [−13,0 ; +2,6] ; −0,129 [−0,250 ; +0,000] | −0,123 [−0,251 ; +0,015] | 216 % ; +4,6 |

#### R1 hors nis_z_100 Q4 — H = 26

**5 bps aller-retour**

| Stop | Stoppés : figé ; dyn. | Effet pur, entrées figées : ATR [IC 95 %] | Figé : espérance ATR [IC] | Dyn. : PnL composé ; MDD valorisé | Dyn. : PF 1x ; PF pondéré ; WR | Dyn. : espérance bps [IC] ; ATR [IC] | Dyn. : timing ATR [IC] | Dyn. : trades ; /mois ; débloqués | Dyn. : durée méd. | Dyn. : part des frais ; brut/trade |
|---|---|---|---|---|---|---|---|---|---|---|
| Sans stop (contrôle) | 0 % ; 0 % | — | −0,111 [−0,311 ; +0,090] | −36 % ; −44 % | 0,94 ; 0,91 ; 51 % | −4,9 [−17,3 ; +7,0] ; −0,111 [−0,311 ; +0,090] | −0,087 [−0,303 ; +0,125] | 1 263 ; 17,5 ; 0 | 26 | > 1 000 % ; +0,1 |
| SL-A 1,0 ATR | 74 % ; 74 % | +0,012 [−0,167 ; +0,187] | −0,099 [−0,219 ; +0,027] | −22 % ; −33 % | 0,93 ; 0,92 ; 25 % | −3,0 [−9,7 ; +3,2] ; −0,065 [−0,192 ; +0,058] | −0,062 [−0,193 ; +0,071] | 1 399 ; 19,4 ; 153 | 9 | 255 % ; +2,0 |
| SL-A 1,5 ATR | 62 % ; 62 % | +0,031 [−0,133 ; +0,196] | −0,079 [−0,218 ; +0,064] | −20 % ; −26 % | 0,96 ; 0,94 ; 33 % | −2,5 [−10,4 ; +5,0] ; −0,056 [−0,198 ; +0,079] | −0,057 [−0,208 ; +0,086] | 1 361 ; 18,9 ; 113 | 16 | 201 % ; +2,5 |
| SL-A 2,0 ATR | 52 % ; 52 % | +0,041 [−0,102 ; +0,195] | −0,070 [−0,210 ; +0,068] | −22 % ; −32 % | 0,98 ; 0,94 ; 39 % | −1,3 [−8,8 ; +6,5] ; −0,065 [−0,204 ; +0,070] | −0,064 [−0,210 ; +0,074] | 1 335 ; 18,5 ; 86 | 24 | 134 % ; +3,7 |
| SL-A 2,5 ATR | 44 % ; 43 % | +0,040 [−0,097 ; +0,184] | −0,071 [−0,228 ; +0,077] | −22 % ; −34 % | 0,98 ; 0,95 ; 44 % | −1,5 [−10,1 ; +7,7] ; −0,064 [−0,220 ; +0,085] | −0,063 [−0,222 ; +0,094] | 1 314 ; 18,2 ; 64 | 26 | 143 % ; +3,5 |
| SL-A 3,0 ATR | 37 % ; 36 % | +0,027 [−0,106 ; +0,169] | −0,083 [−0,249 ; +0,079] | −22 % ; −38 % | 0,97 ; 0,95 ; 46 % | −2,2 [−11,7 ; +7,9] ; −0,065 [−0,226 ; +0,102] | −0,061 [−0,231 ; +0,115] | 1 305 ; 18,1 ; 52 | 26 | 181 % ; +2,8 |
| SL-A 4,0 ATR | 26 % ; 25 % | +0,019 [−0,090 ; +0,135] | −0,091 [−0,259 ; +0,072] | −25 % ; −38 % | 0,95 ; 0,94 ; 48 % | −3,6 [−13,7 ; +6,8] ; −0,075 [−0,245 ; +0,086] | −0,062 [−0,238 ; +0,113] | 1 298 ; 18,0 ; 43 | 26 | 358 % ; +1,4 |
| SL-A 5,0 ATR | 17 % ; 17 % | +0,035 [−0,062 ; +0,134] | −0,075 [−0,250 ; +0,103] | −21 % ; −38 % | 0,97 ; 0,96 ; 50 % | −2,2 [−13,0 ; +8,8] ; −0,052 [−0,227 ; +0,126] | −0,028 [−0,214 ; +0,158] | 1 283 ; 17,8 ; 25 | 26 | 181 % ; +2,8 |
| SL-B extremum + 0,00 ATR | 72 % ; 72 % | +0,036 [−0,133 ; +0,205] | −0,075 [−0,194 ; +0,050] | −13 % ; −33 % | 0,97 ; 0,96 ; 25 % | −1,4 [−7,5 ; +4,7] ; −0,035 [−0,161 ; +0,096] | −0,035 [−0,165 ; +0,102] | 1 394 ; 19,4 ; 151 | 9 | 137 % ; +3,6 |
| SL-B extremum + 0,25 ATR | 68 % ; 69 % | −0,021 [−0,185 ; +0,144] | −0,132 [−0,259 ; +0,000] | −36 % ; −38 % | 0,90 ; 0,86 ; 28 % | −5,1 [−11,5 ; +1,5] ; −0,122 [−0,247 ; +0,009] | −0,124 [−0,251 ; +0,017] | 1 376 ; 19,1 ; 131 | 11 | sans objet (brut ≤ 0) ; −0,1 |
| SL-B extremum + 0,50 ATR | 63 % ; 63 % | +0,001 [−0,166 ; +0,169] | −0,109 [−0,239 ; +0,020] | −34 % ; −37 % | 0,92 ; 0,89 ; 32 % | −4,1 [−10,8 ; +2,5] ; −0,114 [−0,238 ; +0,015] | −0,115 [−0,245 ; +0,015] | 1 359 ; 18,9 ; 112 | 15 | 572 % ; +0,9 |
| SL-B extremum + 1,00 ATR | 54 % ; 54 % | +0,015 [−0,130 ; +0,164] | −0,096 [−0,244 ; +0,050] | −27 % ; −37 % | 0,96 ; 0,92 ; 38 % | −2,4 [−10,7 ; +5,9] ; −0,083 [−0,232 ; +0,062] | −0,077 [−0,232 ; +0,074] | 1 339 ; 18,6 ; 89 | 23 | 195 % ; +2,6 |

**10 bps aller-retour**

| Stop | Figé : espérance ATR [IC] | Dyn. : PnL composé ; MDD valorisé | Dyn. : PF 1x ; PF pondéré ; WR | Dyn. : espérance bps [IC] ; ATR [IC] | Dyn. : timing ATR [IC] | Dyn. : part des frais ; brut/trade |
|---|---|---|---|---|---|---|
| Sans stop (contrôle) | −0,230 [−0,429 ; −0,028] | −55 % ; −59 % | 0,88 ; 0,84 ; 49 % | −9,9 [−22,3 ; +2,0] ; −0,230 [−0,429 ; −0,028] | −0,207 [−0,421 ; +0,006] | > 1 000 % ; +0,1 |
| SL-A 1,0 ATR | −0,218 [−0,341 ; −0,091] | −47 % ; −50 % | 0,84 ; 0,80 ; 24 % | −8,0 [−14,7 ; −1,8] ; −0,184 [−0,315 ; −0,060] | −0,182 [−0,315 ; −0,051] | 509 % ; +2,0 |
| SL-A 1,5 ATR | −0,199 [−0,338 ; −0,055] | −45 % ; −48 % | 0,87 ; 0,84 ; 32 % | −7,5 [−15,4 ; −0,0] ; −0,176 [−0,320 ; −0,039] | −0,177 [−0,328 ; −0,034] | 401 % ; +2,5 |
| SL-A 2,0 ATR | −0,190 [−0,332 ; −0,051] | −46 % ; −50 % | 0,90 ; 0,85 ; 39 % | −6,3 [−13,8 ; +1,5] ; −0,185 [−0,327 ; −0,050] | −0,184 [−0,332 ; −0,044] | 269 % ; +3,7 |
| SL-A 2,5 ATR | −0,190 [−0,350 ; −0,039] | −45 % ; −50 % | 0,91 ; 0,86 ; 43 % | −6,5 [−15,1 ; +2,7] ; −0,183 [−0,342 ; −0,032] | −0,182 [−0,345 ; −0,022] | 287 % ; +3,5 |
| SL-A 3,0 ATR | −0,203 [−0,375 ; −0,037] | −45 % ; −51 % | 0,90 ; 0,87 ; 45 % | −7,2 [−16,7 ; +2,9] ; −0,184 [−0,349 ; −0,015] | −0,180 [−0,353 ; −0,004] | 363 % ; +2,8 |
| SL-A 4,0 ATR | −0,211 [−0,381 ; −0,045] | −47 % ; −53 % | 0,89 ; 0,87 ; 47 % | −8,6 [−18,7 ; +1,8] ; −0,195 [−0,367 ; −0,030] | −0,181 [−0,358 ; −0,007] | 717 % ; +1,4 |
| SL-A 5,0 ATR | −0,195 [−0,376 ; −0,015] | −44 % ; −50 % | 0,90 ; 0,88 ; 49 % | −7,2 [−18,0 ; +3,8] ; −0,172 [−0,352 ; +0,008] | −0,147 [−0,339 ; +0,040] | 362 % ; +2,8 |
| SL-B extremum + 0,00 ATR | −0,195 [−0,317 ; −0,066] | −41 % ; −47 % | 0,86 ; 0,83 ; 25 % | −6,4 [−12,5 ; −0,3] ; −0,154 [−0,283 ; −0,021] | −0,154 [−0,288 ; −0,015] | 275 % ; +3,6 |
| SL-B extremum + 0,25 ATR | −0,252 [−0,380 ; −0,113] | −56 % ; −57 % | 0,81 ; 0,76 ; 27 % | −10,1 [−16,5 ; −3,5] ; −0,241 [−0,369 ; −0,106] | −0,243 [−0,373 ; −0,102] | sans objet (brut ≤ 0) ; −0,1 |
| SL-B extremum + 0,50 ATR | −0,229 [−0,362 ; −0,095] | −54 % ; −56 % | 0,84 ; 0,79 ; 31 % | −9,1 [−15,8 ; −2,5] ; −0,233 [−0,359 ; −0,101] | −0,235 [−0,367 ; −0,101] | > 1 000 % ; +0,9 |
| SL-B extremum + 1,00 ATR | −0,215 [−0,368 ; −0,069] | −50 % ; −55 % | 0,89 ; 0,84 ; 37 % | −7,4 [−15,7 ; +0,9] ; −0,203 [−0,355 ; −0,056] | −0,196 [−0,353 ; −0,046] | 390 % ; +2,6 |

#### ↳ F1 · x1 encore opposé hors nis_z_100 Q4 — H = 6

**5 bps aller-retour**

| Stop | Stoppés : figé ; dyn. | Effet pur, entrées figées : ATR [IC 95 %] | Figé : espérance ATR [IC] | Dyn. : PnL composé ; MDD valorisé | Dyn. : PF 1x ; PF pondéré ; WR | Dyn. : espérance bps [IC] ; ATR [IC] | Dyn. : timing ATR [IC] | Dyn. : trades ; /mois ; débloqués | Dyn. : durée méd. | Dyn. : part des frais ; brut/trade |
|---|---|---|---|---|---|---|---|---|---|---|
| Sans stop (contrôle) | 0 % ; 0 % | — | −0,023 [−0,133 ; +0,107] | −6 % ; −14 % | 0,94 ; 0,96 ; 53 % | −2,0 [−8,4 ; +4,4] ; −0,023 [−0,133 ; +0,107] | −0,005 [−0,119 ; +0,133] | 962 ; 13,4 ; 0 | 6 | 166 % ; +3,0 |
| SL-A 1,0 ATR | 45 % ; 45 % | +0,021 [−0,051 ; +0,095] | −0,002 [−0,105 ; +0,121] | −4 % ; −14 % | 0,90 ; 0,98 ; 43 % | −3,3 [−8,4 ; +2,3] ; −0,002 [−0,105 ; +0,121] | +0,009 [−0,099 ; +0,138] | 962 ; 13,4 ; 0 | 6 | 291 % ; +1,7 |
| SL-A 1,5 ATR | 30 % ; 30 % | +0,026 [−0,044 ; +0,094] | +0,003 [−0,105 ; +0,123] | −2 % ; −14 % | 0,97 ; 0,99 ; 49 % | −0,9 [−6,4 ; +5,3] ; +0,003 [−0,105 ; +0,123] | +0,010 [−0,103 ; +0,137] | 962 ; 13,4 ; 0 | 6 | 121 % ; +4,1 |
| SL-A 2,0 ATR | 19 % ; 19 % | +0,040 [−0,015 ; +0,095] | +0,017 [−0,085 ; +0,139] | +1 % ; −12 % | 1,00 ; 1,02 ; 52 % | −0,2 [−5,5 ; +5,6] ; +0,017 [−0,085 ; +0,139] | +0,027 [−0,082 ; +0,157] | 962 ; 13,4 ; 0 | 6 | 103 % ; +4,8 |
| SL-A 2,5 ATR | 14 % ; 14 % | +0,021 [−0,026 ; +0,067] | −0,002 [−0,104 ; +0,115] | −2 % ; −12 % | 0,96 ; 0,99 ; 53 % | −1,3 [−6,8 ; +4,8] ; −0,002 [−0,104 ; +0,115] | +0,009 [−0,096 ; +0,133] | 962 ; 13,4 ; 0 | 6 | 135 % ; +3,7 |
| SL-A 3,0 ATR | 10 % ; 10 % | +0,004 [−0,037 ; +0,046] | −0,019 [−0,122 ; +0,098] | −6 % ; −14 % | 0,93 ; 0,96 ; 53 % | −2,4 [−8,5 ; +3,8] ; −0,019 [−0,122 ; +0,098] | −0,007 [−0,115 ; +0,117] | 962 ; 13,4 ; 0 | 6 | 194 % ; +2,6 |
| SL-A 4,0 ATR | 5 % ; 5 % | +0,003 [−0,030 ; +0,036] | −0,020 [−0,124 ; +0,101] | −6 % ; −14 % | 0,93 ; 0,97 ; 53 % | −2,5 [−8,8 ; +3,8] ; −0,020 [−0,124 ; +0,101] | −0,005 [−0,117 ; +0,125] | 962 ; 13,4 ; 0 | 6 | 201 % ; +2,5 |
| SL-A 5,0 ATR | 2 % ; 2 % | +0,013 [−0,011 ; +0,043] | −0,010 [−0,118 ; +0,111] | −3 % ; −13 % | 0,96 ; 0,99 ; 53 % | −1,5 [−7,7 ; +4,8] ; −0,010 [−0,118 ; +0,111] | +0,008 [−0,104 ; +0,136] | 962 ; 13,4 ; 0 | 6 | 143 % ; +3,5 |
| SL-B extremum + 0,00 ATR | 39 % ; 39 % | +0,029 [−0,043 ; +0,108] | +0,006 [−0,095 ; +0,122] | −1 % ; −15 % | 0,94 ; 0,99 ; 43 % | −1,9 [−6,8 ; +3,4] ; +0,006 [−0,095 ; +0,122] | +0,015 [−0,092 ; +0,141] | 962 ; 13,4 ; 0 | 6 | 161 % ; +3,1 |
| SL-B extremum + 0,25 ATR | 35 % ; 35 % | −0,009 [−0,084 ; +0,068] | −0,032 [−0,140 ; +0,089] | −10 % ; −18 % | 0,88 ; 0,93 ; 44 % | −4,1 [−9,4 ; +1,5] ; −0,032 [−0,140 ; +0,089] | −0,023 [−0,137 ; +0,104] | 962 ; 13,4 ; 0 | 6 | 531 % ; +0,9 |
| SL-B extremum + 0,50 ATR | 30 % ; 30 % | −0,009 [−0,077 ; +0,064] | −0,032 [−0,141 ; +0,087] | −10 % ; −17 % | 0,92 ; 0,93 ; 47 % | −2,9 [−8,6 ; +3,1] ; −0,032 [−0,141 ; +0,087] | −0,025 [−0,138 ; +0,103] | 962 ; 13,4 ; 0 | 6 | 237 % ; +2,1 |
| SL-B extremum + 1,00 ATR | 19 % ; 19 % | +0,019 [−0,038 ; +0,077] | −0,004 [−0,106 ; +0,116] | −3 % ; −12 % | 0,96 ; 0,98 ; 51 % | −1,5 [−7,3 ; +4,7] ; −0,004 [−0,106 ; +0,116] | +0,007 [−0,100 ; +0,132] | 962 ; 13,4 ; 0 | 6 | 143 % ; +3,5 |

**10 bps aller-retour**

| Stop | Figé : espérance ATR [IC] | Dyn. : PnL composé ; MDD valorisé | Dyn. : PF 1x ; PF pondéré ; WR | Dyn. : espérance bps [IC] ; ATR [IC] | Dyn. : timing ATR [IC] | Dyn. : part des frais ; brut/trade |
|---|---|---|---|---|---|---|
| Sans stop (contrôle) | −0,134 [−0,241 ; −0,006] | −27 % ; −29 % | 0,82 ; 0,81 ; 50 % | −7,0 [−13,4 ; −0,6] ; −0,134 [−0,241 ; −0,006] | −0,116 [−0,228 ; +0,019] | 331 % ; +3,0 |
| SL-A 1,0 ATR | −0,113 [−0,213 ; +0,005] | −25 % ; −27 % | 0,76 ; 0,80 ; 41 % | −8,3 [−13,4 ; −2,7] ; −0,113 [−0,213 ; +0,005] | −0,102 [−0,205 ; +0,019] | 581 % ; +1,7 |
| SL-A 1,5 ATR | −0,109 [−0,214 ; +0,010] | −24 % ; −26 % | 0,83 ; 0,82 ; 46 % | −5,9 [−11,4 ; +0,3] ; −0,109 [−0,214 ; +0,010] | −0,101 [−0,210 ; +0,025] | 242 % ; +4,1 |
| SL-A 2,0 ATR | −0,094 [−0,196 ; +0,026] | −21 % ; −23 % | 0,86 ; 0,85 ; 49 % | −5,2 [−10,5 ; +0,6] ; −0,094 [−0,196 ; +0,026] | −0,084 [−0,190 ; +0,044] | 207 % ; +4,8 |
| SL-A 2,5 ATR | −0,113 [−0,214 ; +0,000] | −24 % ; −26 % | 0,83 ; 0,83 ; 49 % | −6,3 [−11,8 ; −0,2] ; −0,113 [−0,214 ; +0,000] | −0,102 [−0,207 ; +0,020] | 270 % ; +3,7 |
| SL-A 3,0 ATR | −0,130 [−0,232 ; −0,016] | −27 % ; −29 % | 0,81 ; 0,81 ; 50 % | −7,4 [−13,5 ; −1,2] ; −0,130 [−0,232 ; −0,016] | −0,118 [−0,224 ; +0,004] | 388 % ; +2,6 |
| SL-A 4,0 ATR | −0,132 [−0,236 ; −0,014] | −27 % ; −28 % | 0,80 ; 0,81 ; 50 % | −7,5 [−13,8 ; −1,2] ; −0,132 [−0,236 ; −0,014] | −0,116 [−0,225 ; +0,011] | 401 % ; +2,5 |
| SL-A 5,0 ATR | −0,121 [−0,230 ; −0,002] | −25 % ; −27 % | 0,83 ; 0,83 ; 50 % | −6,5 [−12,7 ; −0,2] ; −0,121 [−0,230 ; −0,002] | −0,103 [−0,213 ; +0,022] | 286 % ; +3,5 |
| SL-B extremum + 0,00 ATR | −0,105 [−0,204 ; +0,009] | −23 % ; −25 % | 0,79 ; 0,81 ; 40 % | −6,9 [−11,8 ; −1,6] ; −0,105 [−0,204 ; +0,009] | −0,096 [−0,202 ; +0,027] | 322 % ; +3,1 |
| SL-B extremum + 0,25 ATR | −0,143 [−0,250 ; −0,026] | −30 % ; −32 % | 0,75 ; 0,77 ; 42 % | −9,1 [−14,4 ; −3,5] ; −0,143 [−0,250 ; −0,026] | −0,134 [−0,247 ; −0,008] | > 1 000 % ; +0,9 |
| SL-B extremum + 0,50 ATR | −0,144 [−0,249 ; −0,026] | −30 % ; −31 % | 0,79 ; 0,78 ; 44 % | −7,9 [−13,6 ; −1,9] ; −0,144 [−0,249 ; −0,026] | −0,136 [−0,248 ; −0,010] | 473 % ; +2,1 |
| SL-B extremum + 1,00 ATR | −0,115 [−0,216 ; +0,001] | −25 % ; −26 % | 0,82 ; 0,82 ; 48 % | −6,5 [−12,3 ; −0,3] ; −0,115 [−0,216 ; +0,001] | −0,104 [−0,208 ; +0,019] | 286 % ; +3,5 |

#### ↳ F1 · x1 encore opposé hors nis_z_100 Q4 — H = 13

**5 bps aller-retour**

| Stop | Stoppés : figé ; dyn. | Effet pur, entrées figées : ATR [IC 95 %] | Figé : espérance ATR [IC] | Dyn. : PnL composé ; MDD valorisé | Dyn. : PF 1x ; PF pondéré ; WR | Dyn. : espérance bps [IC] ; ATR [IC] | Dyn. : timing ATR [IC] | Dyn. : trades ; /mois ; débloqués | Dyn. : durée méd. | Dyn. : part des frais ; brut/trade |
|---|---|---|---|---|---|---|---|---|---|---|
| Sans stop (contrôle) | 0 % ; 0 % | — | −0,023 [−0,220 ; +0,183] | −8 % ; −18 % | 0,94 ; 0,98 ; 50 % | −3,0 [−14,6 ; +8,5] ; −0,023 [−0,220 ; +0,183] | −0,014 [−0,230 ; +0,211] | 950 ; 13,2 ; 0 | 13 | 256 % ; +2,0 |
| SL-A 1,0 ATR | 61 % ; 61 % | +0,032 [−0,118 ; +0,180] | +0,008 [−0,136 ; +0,176] | +1 % ; −22 % | 0,94 ; 1,01 ; 34 % | −2,3 [−9,7 ; +5,7] ; +0,024 [−0,120 ; +0,190] | +0,032 [−0,117 ; +0,207] | 958 ; 13,3 ; 8 | 8 | 183 % ; +2,7 |
| SL-A 1,5 ATR | 44 % ; 44 % | +0,064 [−0,076 ; +0,205] | +0,041 [−0,120 ; +0,217] | +10 % ; −17 % | 1,02 ; 1,06 ; 42 % | +0,8 [−8,3 ; +10,3] ; +0,059 [−0,097 ; +0,234] | +0,060 [−0,101 ; +0,242] | 958 ; 13,3 ; 8 | 13 | 87 % ; +5,8 |
| SL-A 2,0 ATR | 35 % ; 35 % | +0,070 [−0,044 ; +0,187] | +0,047 [−0,116 ; +0,224] | +11 % ; −15 % | 1,01 ; 1,06 ; 46 % | +0,3 [−9,1 ; +10,1] ; +0,062 [−0,101 ; +0,244] | +0,071 [−0,102 ; +0,259] | 955 ; 13,3 ; 5 | 13 | 94 % ; +5,3 |
| SL-A 2,5 ATR | 26 % ; 26 % | +0,071 [−0,028 ; +0,177] | +0,048 [−0,122 ; +0,235] | +7 % ; −16 % | 0,99 ; 1,04 ; 48 % | −0,6 [−11,0 ; +10,1] ; +0,047 [−0,123 ; +0,233] | +0,057 [−0,115 ; +0,252] | 951 ; 13,2 ; 1 | 13 | 115 % ; +4,4 |
| SL-A 3,0 ATR | 20 % ; 20 % | +0,055 [−0,034 ; +0,153] | +0,032 [−0,133 ; +0,225] | +4 % ; −16 % | 0,97 ; 1,03 ; 48 % | −1,7 [−12,5 ; +9,3] ; +0,031 [−0,133 ; +0,224] | +0,041 [−0,130 ; +0,245] | 951 ; 13,2 ; 1 | 13 | 153 % ; +3,3 |
| SL-A 4,0 ATR | 12 % ; 12 % | +0,070 [+0,001 ; +0,150] | +0,046 [−0,128 ; +0,237] | +8 % ; −16 % | 0,98 ; 1,05 ; 50 % | −1,3 [−12,1 ; +10,1] ; +0,046 [−0,129 ; +0,236] | +0,059 [−0,119 ; +0,261] | 951 ; 13,2 ; 1 | 13 | 134 % ; +3,7 |
| SL-A 5,0 ATR | 7 % ; 7 % | +0,057 [+0,002 ; +0,124] | +0,034 [−0,147 ; +0,232] | +5 % ; −17 % | 0,96 ; 1,03 ; 50 % | −1,9 [−13,4 ; +9,6] ; +0,034 [−0,147 ; +0,232] | +0,049 [−0,136 ; +0,261] | 950 ; 13,2 ; 0 | 13 | 161 % ; +3,1 |
| SL-B extremum + 0,00 ATR | 55 % ; 54 % | +0,019 [−0,131 ; +0,167] | −0,004 [−0,156 ; +0,178] | −0 % ; −26 % | 0,95 ; 1,01 ; 34 % | −1,9 [−9,5 ; +6,3] ; +0,016 [−0,135 ; +0,194] | +0,022 [−0,137 ; +0,209] | 958 ; 13,3 ; 8 | 11 | 161 % ; +3,1 |
| SL-B extremum + 0,25 ATR | 51 % ; 51 % | −0,035 [−0,188 ; +0,110] | −0,058 [−0,218 ; +0,119] | −15 % ; −29 % | 0,88 ; 0,92 ; 37 % | −5,5 [−13,8 ; +3,0] ; −0,051 [−0,207 ; +0,124] | −0,045 [−0,205 ; +0,143] | 957 ; 13,3 ; 7 | 13 | sans objet (brut ≤ 0) ; −0,5 |
| SL-B extremum + 0,50 ATR | 44 % ; 44 % | +0,002 [−0,130 ; +0,137] | −0,021 [−0,190 ; +0,159] | −8 % ; −25 % | 0,95 ; 0,97 ; 40 % | −2,3 [−12,2 ; +7,7] ; −0,015 [−0,180 ; +0,164] | −0,012 [−0,181 ; +0,175] | 957 ; 13,3 ; 7 | 13 | 187 % ; +2,7 |
| SL-B extremum + 1,00 ATR | 33 % ; 33 % | +0,074 [−0,033 ; +0,190] | +0,051 [−0,116 ; +0,237] | +8 % ; −17 % | 1,00 ; 1,05 ; 46 % | −0,1 [−10,1 ; +9,8] ; +0,053 [−0,115 ; +0,241] | +0,065 [−0,110 ; +0,259] | 955 ; 13,3 ; 5 | 13 | 102 % ; +4,9 |

**10 bps aller-retour**

| Stop | Figé : espérance ATR [IC] | Dyn. : PnL composé ; MDD valorisé | Dyn. : PF 1x ; PF pondéré ; WR | Dyn. : espérance bps [IC] ; ATR [IC] | Dyn. : timing ATR [IC] | Dyn. : part des frais ; brut/trade |
|---|---|---|---|---|---|---|
| Sans stop (contrôle) | −0,134 [−0,329 ; +0,070] | −28 % ; −35 % | 0,86 ; 0,87 ; 47 % | −8,0 [−19,6 ; +3,5] ; −0,134 [−0,329 ; +0,070] | −0,125 [−0,337 ; +0,096] | 513 % ; +2,0 |
| SL-A 1,0 ATR | −0,103 [−0,245 ; +0,060] | −22 % ; −30 % | 0,83 ; 0,87 ; 32 % | −7,3 [−14,7 ; +0,7] ; −0,087 [−0,232 ; +0,076] | −0,079 [−0,228 ; +0,096] | 366 % ; +2,7 |
| SL-A 1,5 ATR | −0,071 [−0,231 ; +0,107] | −15 % ; −25 % | 0,91 ; 0,93 ; 40 % | −4,2 [−13,3 ; +5,3] ; −0,052 [−0,210 ; +0,123] | −0,051 [−0,212 ; +0,129] | 174 % ; +5,8 |
| SL-A 2,0 ATR | −0,065 [−0,226 ; +0,111] | −14 % ; −24 % | 0,91 ; 0,94 ; 44 % | −4,7 [−14,1 ; +5,1] ; −0,049 [−0,211 ; +0,128] | −0,040 [−0,209 ; +0,147] | 187 % ; +5,3 |
| SL-A 2,5 ATR | −0,063 [−0,237 ; +0,126] | −16 % ; −24 % | 0,89 ; 0,92 ; 46 % | −5,6 [−16,0 ; +5,1] ; −0,064 [−0,237 ; +0,125] | −0,054 [−0,225 ; +0,140] | 229 % ; +4,4 |
| SL-A 3,0 ATR | −0,079 [−0,246 ; +0,115] | −19 % ; −27 % | 0,88 ; 0,91 ; 46 % | −6,7 [−17,5 ; +4,3] ; −0,080 [−0,247 ; +0,113] | −0,070 [−0,241 ; +0,131] | 305 % ; +3,3 |
| SL-A 4,0 ATR | −0,065 [−0,241 ; +0,123] | −16 % ; −26 % | 0,89 ; 0,93 ; 47 % | −6,3 [−17,1 ; +5,1] ; −0,066 [−0,241 ; +0,122] | −0,051 [−0,230 ; +0,148] | 267 % ; +3,7 |
| SL-A 5,0 ATR | −0,077 [−0,255 ; +0,119] | −18 % ; −27 % | 0,88 ; 0,92 ; 47 % | −6,9 [−18,4 ; +4,6] ; −0,077 [−0,255 ; +0,119] | −0,062 [−0,246 ; +0,146] | 322 % ; +3,1 |
| SL-B extremum + 0,00 ATR | −0,115 [−0,266 ; +0,063] | −22 % ; −33 % | 0,84 ; 0,86 ; 32 % | −6,9 [−14,5 ; +1,3] ; −0,096 [−0,245 ; +0,082] | −0,089 [−0,245 ; +0,098] | 323 % ; +3,1 |
| SL-B extremum + 0,25 ATR | −0,170 [−0,325 ; +0,004] | −34 % ; −38 % | 0,78 ; 0,80 ; 35 % | −10,5 [−18,8 ; −2,0] ; −0,163 [−0,316 ; +0,013] | −0,156 [−0,315 ; +0,030] | sans objet (brut ≤ 0) ; −0,5 |
| SL-B extremum + 0,50 ATR | −0,133 [−0,297 ; +0,047] | −28 % ; −34 % | 0,85 ; 0,85 ; 38 % | −7,3 [−17,2 ; +2,7] ; −0,127 [−0,290 ; +0,052] | −0,123 [−0,292 ; +0,065] | 375 % ; +2,7 |
| SL-B extremum + 1,00 ATR | −0,060 [−0,227 ; +0,125] | −16 % ; −23 % | 0,90 ; 0,93 ; 44 % | −5,1 [−15,1 ; +4,8] ; −0,058 [−0,224 ; +0,126] | −0,045 [−0,221 ; +0,149] | 205 % ; +4,9 |

#### ↳ F1 · x1 encore opposé hors nis_z_100 Q4 — H = 26

**5 bps aller-retour**

| Stop | Stoppés : figé ; dyn. | Effet pur, entrées figées : ATR [IC 95 %] | Figé : espérance ATR [IC] | Dyn. : PnL composé ; MDD valorisé | Dyn. : PF 1x ; PF pondéré ; WR | Dyn. : espérance bps [IC] ; ATR [IC] | Dyn. : timing ATR [IC] | Dyn. : trades ; /mois ; débloqués | Dyn. : durée méd. | Dyn. : part des frais ; brut/trade |
|---|---|---|---|---|---|---|---|---|---|---|
| Sans stop (contrôle) | 0 % ; 0 % | — | −0,044 [−0,333 ; +0,228] | −16 % ; −32 % | 0,94 ; 0,96 ; 54 % | −4,8 [−23,8 ; +10,8] ; −0,044 [−0,333 ; +0,228] | −0,016 [−0,303 ; +0,252] | 840 ; 11,7 ; 0 | 26 | > 1 000 % ; +0,2 |
| SL-A 1,0 ATR | 72 % ; 72 % | +0,044 [−0,191 ; +0,278] | +0,001 [−0,172 ; +0,180] | +5 % ; −24 % | 1,01 ; 1,04 ; 27 % | +0,5 [−9,5 ; +10,3] ; +0,044 [−0,137 ; +0,220] | +0,052 [−0,130 ; +0,236] | 896 ; 12,4 ; 60 | 8 | 92 % ; +5,5 |
| SL-A 1,5 ATR | 60 % ; 60 % | +0,080 [−0,123 ; +0,274] | +0,036 [−0,168 ; +0,242] | +14 % ; −16 % | 1,04 ; 1,07 ; 35 % | +2,1 [−9,4 ; +13,1] ; +0,087 [−0,122 ; +0,294] | +0,090 [−0,115 ; +0,304] | 882 ; 12,2 ; 48 | 17 | 70 % ; +7,1 |
| SL-A 2,0 ATR | 51 % ; 51 % | +0,077 [−0,096 ; +0,249] | +0,034 [−0,177 ; +0,233] | +6 % ; −17 % | 1,02 ; 1,03 ; 42 % | +1,1 [−11,1 ; +12,3] ; +0,055 [−0,160 ; +0,257] | +0,059 [−0,149 ; +0,260] | 872 ; 12,1 ; 39 | 26 | 82 % ; +6,1 |
| SL-A 2,5 ATR | 43 % ; 43 % | +0,062 [−0,097 ; +0,230] | +0,018 [−0,192 ; +0,220] | +0 % ; −21 % | 1,00 ; 1,01 ; 46 % | +0,0 [−13,3 ; +11,9] ; +0,026 [−0,193 ; +0,231] | +0,035 [−0,174 ; +0,229] | 863 ; 12,0 ; 29 | 26 | 99 % ; +5,0 |
| SL-A 3,0 ATR | 37 % ; 37 % | +0,031 [−0,136 ; +0,203] | −0,013 [−0,226 ; +0,187] | −6 % ; −24 % | 0,96 ; 0,99 ; 48 % | −2,7 [−16,6 ; +10,2] ; −0,008 [−0,234 ; +0,199] | +0,002 [−0,218 ; +0,205] | 860 ; 11,9 ; 25 | 26 | 216 % ; +2,3 |
| SL-A 4,0 ATR | 26 % ; 26 % | +0,058 [−0,073 ; +0,194] | +0,014 [−0,214 ; +0,227] | −2 % ; −24 % | 0,96 ; 1,00 ; 51 % | −3,2 [−17,0 ; +9,7] ; +0,022 [−0,208 ; +0,235] | +0,043 [−0,184 ; +0,253] | 857 ; 11,9 ; 19 | 26 | 276 % ; +1,8 |
| SL-A 5,0 ATR | 18 % ; 17 % | +0,055 [−0,058 ; +0,165] | +0,011 [−0,240 ; +0,240] | −3 % ; −29 % | 0,96 ; 1,00 ; 53 % | −3,2 [−19,1 ; +11,0] ; +0,018 [−0,227 ; +0,243] | +0,048 [−0,197 ; +0,273] | 851 ; 11,8 ; 12 | 26 | 279 % ; +1,8 |
| SL-B extremum + 0,00 ATR | 67 % ; 67 % | +0,049 [−0,189 ; +0,280] | +0,005 [−0,165 ; +0,188] | +6 % ; −25 % | 1,01 ; 1,04 ; 30 % | +0,7 [−8,9 ; +10,1] ; +0,047 [−0,129 ; +0,231] | +0,050 [−0,133 ; +0,237] | 896 ; 12,4 ; 62 | 11 | 88 % ; +5,7 |
| SL-B extremum + 0,25 ATR | 64 % ; 64 % | −0,005 [−0,224 ; +0,226] | −0,048 [−0,231 ; +0,141] | −11 % ; −26 % | 0,95 ; 0,95 ; 32 % | −2,9 [−12,9 ; +7,4] ; −0,031 [−0,217 ; +0,162] | −0,028 [−0,214 ; +0,170] | 890 ; 12,4 ; 56 | 13 | 234 % ; +2,1 |
| SL-B extremum + 0,50 ATR | 58 % ; 59 % | +0,028 [−0,178 ; +0,235] | −0,016 [−0,205 ; +0,177] | −8 % ; −24 % | 0,98 ; 0,97 ; 36 % | −1,0 [−11,7 ; +9,8] ; −0,016 [−0,204 ; +0,180] | −0,016 [−0,200 ; +0,181] | 881 ; 12,2 ; 47 | 18 | 125 % ; +4,0 |
| SL-B extremum + 1,00 ATR | 49 % ; 49 % | +0,094 [−0,091 ; +0,273] | +0,050 [−0,160 ; +0,260] | +3 % ; −21 % | 1,02 ; 1,02 ; 42 % | +1,2 [−11,0 ; +12,7] ; +0,050 [−0,164 ; +0,259] | +0,061 [−0,149 ; +0,270] | 868 ; 12,1 ; 34 | 26 | 81 % ; +6,2 |

**10 bps aller-retour**

| Stop | Figé : espérance ATR [IC] | Dyn. : PnL composé ; MDD valorisé | Dyn. : PF 1x ; PF pondéré ; WR | Dyn. : espérance bps [IC] ; ATR [IC] | Dyn. : timing ATR [IC] | Dyn. : part des frais ; brut/trade |
|---|---|---|---|---|---|---|
| Sans stop (contrôle) | −0,155 [−0,446 ; +0,118] | −33 % ; −42 % | 0,88 ; 0,89 ; 53 % | −9,8 [−28,8 ; +5,8] ; −0,155 [−0,446 ; +0,118] | −0,128 [−0,414 ; +0,140] | > 1 000 % ; +0,2 |
| SL-A 1,0 ATR | −0,111 [−0,288 ; +0,071] | −17 % ; −32 % | 0,91 ; 0,91 ; 26 % | −4,5 [−14,5 ; +5,3] ; −0,068 [−0,252 ; +0,109] | −0,059 [−0,243 ; +0,126] | 183 % ; +5,5 |
| SL-A 1,5 ATR | −0,076 [−0,282 ; +0,130] | −10 % ; −24 % | 0,95 ; 0,96 ; 35 % | −2,9 [−14,4 ; +8,1] ; −0,024 [−0,236 ; +0,184] | −0,020 [−0,227 ; +0,190] | 140 % ; +7,1 |
| SL-A 2,0 ATR | −0,078 [−0,291 ; +0,122] | −16 % ; −29 % | 0,94 ; 0,94 ; 41 % | −3,9 [−16,1 ; +7,3] ; −0,056 [−0,273 ; +0,147] | −0,051 [−0,261 ; +0,149] | 165 % ; +6,1 |
| SL-A 2,5 ATR | −0,094 [−0,304 ; +0,111] | −20 % ; −32 % | 0,93 ; 0,93 ; 45 % | −5,0 [−18,3 ; +6,9] ; −0,085 [−0,305 ; +0,121] | −0,076 [−0,287 ; +0,119] | 199 % ; +5,0 |
| SL-A 3,0 ATR | −0,125 [−0,339 ; +0,079] | −25 % ; −35 % | 0,90 ; 0,91 ; 47 % | −7,7 [−21,6 ; +5,2] ; −0,120 [−0,347 ; +0,086] | −0,108 [−0,329 ; +0,092] | 432 % ; +2,3 |
| SL-A 4,0 ATR | −0,098 [−0,327 ; +0,116] | −22 % ; −33 % | 0,90 ; 0,93 ; 50 % | −8,2 [−22,0 ; +4,7] ; −0,089 [−0,321 ; +0,125] | −0,068 [−0,298 ; +0,142] | 552 % ; +1,8 |
| SL-A 5,0 ATR | −0,101 [−0,352 ; +0,132] | −22 % ; −39 % | 0,90 ; 0,93 ; 52 % | −8,2 [−24,1 ; +6,0] ; −0,094 [−0,337 ; +0,131] | −0,063 [−0,307 ; +0,164] | 557 % ; +1,8 |
| SL-B extremum + 0,00 ATR | −0,107 [−0,282 ; +0,078] | −16 % ; −33 % | 0,92 ; 0,92 ; 29 % | −4,3 [−13,9 ; +5,1] ; −0,064 [−0,240 ; +0,119] | −0,060 [−0,239 ; +0,127] | 177 % ; +5,7 |
| SL-B extremum + 0,25 ATR | −0,160 [−0,345 ; +0,028] | −30 % ; −36 % | 0,87 ; 0,85 ; 31 % | −7,9 [−17,9 ; +2,4] ; −0,142 [−0,330 ; +0,048] | −0,139 [−0,326 ; +0,060] | 469 % ; +2,1 |
| SL-B extremum + 0,50 ATR | −0,128 [−0,318 ; +0,061] | −27 % ; −35 % | 0,90 ; 0,88 ; 35 % | −6,0 [−16,7 ; +4,8] ; −0,127 [−0,318 ; +0,067] | −0,126 [−0,313 ; +0,068] | 250 % ; +4,0 |
| SL-B extremum + 1,00 ATR | −0,062 [−0,276 ; +0,147] | −18 % ; −32 % | 0,94 ; 0,93 ; 41 % | −3,8 [−16,0 ; +7,7] ; −0,061 [−0,277 ; +0,148] | −0,049 [−0,259 ; +0,163] | 161 % ; +6,2 |

#### ↳ F5 · x1 encore opposé hors nis_z_100 Q4 — H = 6

**5 bps aller-retour**

| Stop | Stoppés : figé ; dyn. | Effet pur, entrées figées : ATR [IC 95 %] | Figé : espérance ATR [IC] | Dyn. : PnL composé ; MDD valorisé | Dyn. : PF 1x ; PF pondéré ; WR | Dyn. : espérance bps [IC] ; ATR [IC] | Dyn. : timing ATR [IC] | Dyn. : trades ; /mois ; débloqués | Dyn. : durée méd. | Dyn. : part des frais ; brut/trade |
|---|---|---|---|---|---|---|---|---|---|---|
| Sans stop (contrôle) | 0 % ; 0 % | — | −0,044 [−0,184 ; +0,088] | −6 % ; −11 % | 1,11 ; 0,94 ; 54 % | +3,1 [−5,7 ; +12,3] ; −0,044 [−0,184 ; +0,088] | −0,057 [−0,201 ; +0,079] | 630 ; 8,8 ; 0 | 6 | 62 % ; +8,1 |
| SL-A 1,0 ATR | 43 % ; 43 % | −0,012 [−0,093 ; +0,069] | −0,057 [−0,159 ; +0,047] | −8 % ; −10 % | 0,99 ; 0,90 ; 44 % | −0,2 [−6,9 ; +6,9] ; −0,057 [−0,159 ; +0,047] | −0,064 [−0,167 ; +0,040] | 630 ; 8,8 ; 0 | 6 | 104 % ; +4,8 |
| SL-A 1,5 ATR | 29 % ; 29 % | −0,010 [−0,085 ; +0,060] | −0,055 [−0,169 ; +0,064] | −8 % ; −11 % | 1,02 ; 0,92 ; 49 % | +0,6 [−6,8 ; +8,3] ; −0,055 [−0,169 ; +0,064] | −0,059 [−0,180 ; +0,066] | 630 ; 8,8 ; 0 | 6 | 89 % ; +5,6 |
| SL-A 2,0 ATR | 19 % ; 19 % | +0,008 [−0,061 ; +0,077] | −0,037 [−0,157 ; +0,085] | −4 % ; −6 % | 1,10 ; 0,95 ; 52 % | +2,8 [−5,0 ; +10,9] ; −0,037 [−0,157 ; +0,085] | −0,041 [−0,161 ; +0,082] | 630 ; 8,8 ; 0 | 6 | 64 % ; +7,8 |
| SL-A 2,5 ATR | 14 % ; 14 % | −0,011 [−0,075 ; +0,056] | −0,055 [−0,176 ; +0,069] | −7 % ; −10 % | 1,06 ; 0,93 ; 53 % | +1,8 [−6,1 ; +10,2] ; −0,055 [−0,176 ; +0,069] | −0,064 [−0,184 ; +0,061] | 630 ; 8,8 ; 0 | 6 | 73 % ; +6,8 |
| SL-A 3,0 ATR | 10 % ; 10 % | −0,009 [−0,064 ; +0,048] | −0,054 [−0,176 ; +0,071] | −7 % ; −11 % | 1,07 ; 0,93 ; 53 % | +2,2 [−6,0 ; +10,6] ; −0,054 [−0,176 ; +0,071] | −0,060 [−0,183 ; +0,068] | 630 ; 8,8 ; 0 | 6 | 70 % ; +7,2 |
| SL-A 4,0 ATR | 6 % ; 6 % | −0,022 [−0,069 ; +0,026] | −0,067 [−0,200 ; +0,058] | −10 % ; −13 % | 1,06 ; 0,90 ; 53 % | +1,9 [−6,2 ; +10,3] ; −0,067 [−0,200 ; +0,058] | −0,071 [−0,204 ; +0,058] | 630 ; 8,8 ; 0 | 6 | 73 % ; +6,9 |
| SL-A 5,0 ATR | 3 % ; 3 % | +0,000 [−0,039 ; +0,037] | −0,044 [−0,185 ; +0,087] | −6 % ; −10 % | 1,11 ; 0,94 ; 53 % | +3,1 [−5,4 ; +12,3] ; −0,044 [−0,185 ; +0,087] | −0,051 [−0,198 ; +0,083] | 630 ; 8,8 ; 0 | 6 | 62 % ; +8,1 |
| SL-B extremum + 0,00 ATR | 54 % ; 54 % | +0,005 [−0,085 ; +0,098] | −0,040 [−0,125 ; +0,048] | −6 % ; −8 % | 1,00 ; 0,92 ; 37 % | −0,1 [−5,8 ; +5,9] ; −0,040 [−0,125 ; +0,048] | −0,046 [−0,133 ; +0,047] | 630 ; 8,8 ; 0 | 5 | 101 % ; +4,9 |
| SL-B extremum + 0,25 ATR | 47 % ; 47 % | −0,031 [−0,116 ; +0,060] | −0,075 [−0,174 ; +0,032] | −11 % ; −12 % | 0,94 ; 0,86 ; 41 % | −1,5 [−8,2 ; +5,8] ; −0,075 [−0,174 ; +0,032] | −0,082 [−0,183 ; +0,025] | 630 ; 8,8 ; 0 | 6 | 143 % ; +3,5 |
| SL-B extremum + 0,50 ATR | 38 % ; 38 % | −0,026 [−0,112 ; +0,061] | −0,071 [−0,174 ; +0,036] | −10 % ; −11 % | 0,97 ; 0,88 ; 46 % | −0,8 [−7,4 ; +6,6] ; −0,071 [−0,174 ; +0,036] | −0,077 [−0,183 ; +0,033] | 630 ; 8,8 ; 0 | 6 | 119 % ; +4,2 |
| SL-B extremum + 1,00 ATR | 24 % ; 24 % | −0,012 [−0,084 ; +0,059] | −0,057 [−0,177 ; +0,064] | −8 % ; −10 % | 1,06 ; 0,92 ; 50 % | +1,6 [−6,1 ; +9,4] ; −0,057 [−0,177 ; +0,064] | −0,059 [−0,179 ; +0,064] | 630 ; 8,8 ; 0 | 6 | 76 % ; +6,6 |

**10 bps aller-retour**

| Stop | Figé : espérance ATR [IC] | Dyn. : PnL composé ; MDD valorisé | Dyn. : PF 1x ; PF pondéré ; WR | Dyn. : espérance bps [IC] ; ATR [IC] | Dyn. : timing ATR [IC] | Dyn. : part des frais ; brut/trade |
|---|---|---|---|---|---|---|
| Sans stop (contrôle) | −0,179 [−0,319 ; −0,046] | −23 % ; −24 % | 0,94 ; 0,76 ; 49 % | −1,9 [−10,7 ; +7,3] ; −0,179 [−0,319 ; −0,046] | −0,192 [−0,338 ; −0,055] | 124 % ; +8,1 |
| SL-A 1,0 ATR | −0,191 [−0,295 ; −0,088] | −24 % ; −25 % | 0,82 ; 0,71 ; 40 % | −5,2 [−11,9 ; +1,9] ; −0,191 [−0,295 ; −0,088] | −0,200 [−0,300 ; −0,094] | 208 % ; +4,8 |
| SL-A 1,5 ATR | −0,189 [−0,305 ; −0,072] | −24 % ; −25 % | 0,86 ; 0,73 ; 44 % | −4,4 [−11,8 ; +3,3] ; −0,189 [−0,305 ; −0,072] | −0,194 [−0,314 ; −0,070] | 177 % ; +5,6 |
| SL-A 2,0 ATR | −0,172 [−0,295 ; −0,050] | −21 % ; −22 % | 0,93 ; 0,77 ; 47 % | −2,2 [−10,0 ; +5,9] ; −0,172 [−0,295 ; −0,050] | −0,177 [−0,305 ; −0,052] | 128 % ; +7,8 |
| SL-A 2,5 ATR | −0,190 [−0,313 ; −0,062] | −23 % ; −24 % | 0,90 ; 0,75 ; 48 % | −3,2 [−11,1 ; +5,2] ; −0,190 [−0,313 ; −0,062] | −0,199 [−0,323 ; −0,073] | 146 % ; +6,8 |
| SL-A 3,0 ATR | −0,188 [−0,312 ; −0,068] | −23 % ; −24 % | 0,91 ; 0,75 ; 48 % | −2,8 [−11,0 ; +5,6] ; −0,188 [−0,312 ; −0,068] | −0,196 [−0,322 ; −0,067] | 139 % ; +7,2 |
| SL-A 4,0 ATR | −0,201 [−0,331 ; −0,074] | −25 % ; −26 % | 0,90 ; 0,73 ; 48 % | −3,1 [−11,2 ; +5,3] ; −0,201 [−0,331 ; −0,074] | −0,207 [−0,340 ; −0,078] | 145 % ; +6,9 |
| SL-A 5,0 ATR | −0,179 [−0,321 ; −0,046] | −23 % ; −23 % | 0,94 ; 0,76 ; 48 % | −1,9 [−10,4 ; +7,3] ; −0,179 [−0,321 ; −0,046] | −0,187 [−0,330 ; −0,052] | 123 % ; +8,1 |
| SL-B extremum + 0,00 ATR | −0,174 [−0,262 ; −0,085] | −22 % ; −23 % | 0,81 ; 0,71 ; 34 % | −5,1 [−10,8 ; +0,9] ; −0,174 [−0,262 ; −0,085] | −0,181 [−0,270 ; −0,086] | 203 % ; +4,9 |
| SL-B extremum + 0,25 ATR | −0,210 [−0,309 ; −0,101] | −26 % ; −27 % | 0,78 ; 0,68 ; 38 % | −6,5 [−13,2 ; +0,8] ; −0,210 [−0,309 ; −0,101] | −0,217 [−0,320 ; −0,107] | 287 % ; +3,5 |
| SL-B extremum + 0,50 ATR | −0,205 [−0,309 ; −0,100] | −26 % ; −26 % | 0,81 ; 0,70 ; 41 % | −5,8 [−12,4 ; +1,6] ; −0,205 [−0,309 ; −0,100] | −0,213 [−0,319 ; −0,102] | 238 % ; +4,2 |
| SL-B extremum + 1,00 ATR | −0,192 [−0,312 ; −0,070] | −24 % ; −25 % | 0,89 ; 0,74 ; 45 % | −3,4 [−11,1 ; +4,4] ; −0,192 [−0,312 ; −0,070] | −0,195 [−0,318 ; −0,068] | 151 % ; +6,6 |

#### ↳ F5 · x1 encore opposé hors nis_z_100 Q4 — H = 13

**5 bps aller-retour**

| Stop | Stoppés : figé ; dyn. | Effet pur, entrées figées : ATR [IC 95 %] | Figé : espérance ATR [IC] | Dyn. : PnL composé ; MDD valorisé | Dyn. : PF 1x ; PF pondéré ; WR | Dyn. : espérance bps [IC] ; ATR [IC] | Dyn. : timing ATR [IC] | Dyn. : trades ; /mois ; débloqués | Dyn. : durée méd. | Dyn. : part des frais ; brut/trade |
|---|---|---|---|---|---|---|---|---|---|---|
| Sans stop (contrôle) | 0 % ; 0 % | — | −0,106 [−0,349 ; +0,129] | −13 % ; −28 % | 1,08 ; 0,91 ; 50 % | +3,5 [−8,5 ; +15,5] ; −0,106 [−0,349 ; +0,129] | −0,123 [−0,371 ; +0,107] | 604 ; 8,4 ; 0 | 13 | 59 % ; +8,5 |
| SL-A 1,0 ATR | 62 % ; 61 % | −0,006 [−0,195 ; +0,177] | −0,112 [−0,250 ; +0,031] | −14 % ; −21 % | 0,93 ; 0,86 ; 32 % | −2,4 [−9,9 ; +5,3] ; −0,110 [−0,247 ; +0,028] | −0,128 [−0,260 ; +0,008] | 609 ; 8,5 ; 5 | 8 | 190 % ; +2,6 |
| SL-A 1,5 ATR | 48 % ; 48 % | −0,018 [−0,200 ; +0,155] | −0,124 [−0,288 ; +0,037] | −16 % ; −24 % | 0,95 ; 0,87 ; 39 % | −2,1 [−11,0 ; +6,1] ; −0,125 [−0,285 ; +0,038] | −0,130 [−0,288 ; +0,031] | 606 ; 8,4 ; 2 | 13 | 173 % ; +2,9 |
| SL-A 2,0 ATR | 36 % ; 36 % | −0,005 [−0,177 ; +0,154] | −0,111 [−0,275 ; +0,068] | −13 % ; −20 % | 1,02 ; 0,89 ; 44 % | +1,0 [−7,4 ; +9,9] ; −0,113 [−0,279 ; +0,062] | −0,124 [−0,291 ; +0,054] | 606 ; 8,4 ; 2 | 13 | 83 % ; +6,0 |
| SL-A 2,5 ATR | 27 % ; 27 % | +0,003 [−0,139 ; +0,144] | −0,103 [−0,274 ; +0,087] | −12 % ; −22 % | 1,03 ; 0,91 ; 46 % | +1,2 [−7,8 ; +11,2] ; −0,105 [−0,277 ; +0,085] | −0,124 [−0,303 ; +0,064] | 606 ; 8,4 ; 2 | 13 | 81 % ; +6,2 |
| SL-A 3,0 ATR | 21 % ; 20 % | +0,026 [−0,093 ; +0,153] | −0,079 [−0,260 ; +0,119] | −9 % ; −22 % | 1,07 ; 0,93 ; 48 % | +3,0 [−6,6 ; +13,2] ; −0,076 [−0,257 ; +0,120] | −0,092 [−0,280 ; +0,103] | 605 ; 8,4 ; 1 | 13 | 63 % ; +8,0 |
| SL-A 4,0 ATR | 13 % ; 13 % | −0,000 [−0,108 ; +0,109] | −0,106 [−0,310 ; +0,099] | −13 % ; −24 % | 1,07 ; 0,91 ; 49 % | +3,0 [−7,3 ; +13,9] ; −0,106 [−0,310 ; +0,099] | −0,116 [−0,324 ; +0,091] | 604 ; 8,4 ; 0 | 13 | 62 % ; +8,0 |
| SL-A 5,0 ATR | 7 % ; 7 % | +0,038 [−0,042 ; +0,123] | −0,068 [−0,281 ; +0,148] | −8 % ; −22 % | 1,12 ; 0,95 ; 50 % | +4,9 [−6,0 ; +16,4] ; −0,068 [−0,281 ; +0,148] | −0,079 [−0,293 ; +0,138] | 604 ; 8,4 ; 0 | 13 | 51 % ; +9,9 |
| SL-B extremum + 0,00 ATR | 69 % ; 69 % | +0,031 [−0,159 ; +0,213] | −0,075 [−0,194 ; +0,055] | −10 % ; −18 % | 0,94 ; 0,88 ; 26 % | −1,8 [−7,9 ; +4,8] ; −0,077 [−0,196 ; +0,050] | −0,091 [−0,208 ; +0,032] | 610 ; 8,5 ; 6 | 5 | 154 % ; +3,2 |
| SL-B extremum + 0,25 ATR | 63 % ; 63 % | −0,013 [−0,201 ; +0,168] | −0,119 [−0,246 ; +0,023] | −16 % ; −23 % | 0,91 ; 0,84 ; 30 % | −3,2 [−10,2 ; +4,5] ; −0,119 [−0,246 ; +0,021] | −0,133 [−0,262 ; +0,007] | 608 ; 8,4 ; 4 | 8 | 272 % ; +1,8 |
| SL-B extremum + 0,50 ATR | 57 % ; 57 % | −0,033 [−0,214 ; +0,147] | −0,139 [−0,283 ; +0,023] | −18 % ; −25 % | 0,91 ; 0,83 ; 35 % | −3,4 [−11,9 ; +4,6] ; −0,140 [−0,281 ; +0,019] | −0,153 [−0,296 ; +0,006] | 606 ; 8,4 ; 2 | 10 | 317 % ; +1,6 |
| SL-B extremum + 1,00 ATR | 43 % ; 43 % | −0,033 [−0,201 ; +0,129] | −0,138 [−0,308 ; +0,032] | −17 % ; −24 % | 0,96 ; 0,86 ; 40 % | −1,5 [−10,5 ; +7,1] ; −0,140 [−0,306 ; +0,029] | −0,151 [−0,321 ; +0,022] | 606 ; 8,4 ; 2 | 13 | 143 % ; +3,5 |

**10 bps aller-retour**

| Stop | Figé : espérance ATR [IC] | Dyn. : PnL composé ; MDD valorisé | Dyn. : PF 1x ; PF pondéré ; WR | Dyn. : espérance bps [IC] ; ATR [IC] | Dyn. : timing ATR [IC] | Dyn. : part des frais ; brut/trade |
|---|---|---|---|---|---|---|
| Sans stop (contrôle) | −0,238 [−0,489 ; +0,003] | −27 % ; −37 % | 0,97 ; 0,79 ; 46 % | −1,5 [−13,5 ; +10,5] ; −0,238 [−0,489 ; +0,003] | −0,256 [−0,507 ; −0,021] | 118 % ; +8,5 |
| SL-A 1,0 ATR | −0,244 [−0,381 ; −0,098] | −29 % ; −33 % | 0,81 ; 0,72 ; 30 % | −7,4 [−14,9 ; +0,3] ; −0,243 [−0,380 ; −0,099] | −0,262 [−0,396 ; −0,122] | 381 % ; +2,6 |
| SL-A 1,5 ATR | −0,256 [−0,421 ; −0,092] | −30 % ; −34 % | 0,84 ; 0,74 ; 36 % | −7,1 [−16,0 ; +1,1] ; −0,258 [−0,418 ; −0,094] | −0,264 [−0,427 ; −0,101] | 346 % ; +2,9 |
| SL-A 2,0 ATR | −0,243 [−0,412 ; −0,062] | −28 % ; −31 % | 0,91 ; 0,77 ; 41 % | −4,0 [−12,4 ; +4,9] ; −0,246 [−0,416 ; −0,069] | −0,258 [−0,428 ; −0,078] | 167 % ; +6,0 |
| SL-A 2,5 ATR | −0,235 [−0,409 ; −0,039] | −27 % ; −33 % | 0,91 ; 0,79 ; 43 % | −3,8 [−12,8 ; +6,2] ; −0,239 [−0,417 ; −0,042] | −0,258 [−0,439 ; −0,062] | 161 % ; +6,2 |
| SL-A 3,0 ATR | −0,211 [−0,398 ; −0,012] | −24 % ; −31 % | 0,95 ; 0,81 ; 45 % | −2,0 [−11,6 ; +8,2] ; −0,209 [−0,396 ; −0,008] | −0,225 [−0,418 ; −0,023] | 125 % ; +8,0 |
| SL-A 4,0 ATR | −0,238 [−0,450 ; −0,029] | −27 % ; −33 % | 0,95 ; 0,79 ; 45 % | −2,0 [−12,3 ; +8,9] ; −0,238 [−0,450 ; −0,029] | −0,249 [−0,459 ; −0,037] | 125 % ; +8,0 |
| SL-A 5,0 ATR | −0,200 [−0,420 ; +0,022] | −23 % ; −32 % | 1,00 ; 0,82 ; 46 % | −0,1 [−11,0 ; +11,4] ; −0,200 [−0,420 ; +0,022] | −0,212 [−0,435 ; +0,011] | 101 % ; +9,9 |
| SL-B extremum + 0,00 ATR | −0,207 [−0,328 ; −0,075] | −25 % ; −29 % | 0,79 ; 0,72 ; 25 % | −6,8 [−12,9 ; −0,2] ; −0,211 [−0,331 ; −0,080] | −0,225 [−0,346 ; −0,100] | 309 % ; +3,2 |
| SL-B extremum + 0,25 ATR | −0,251 [−0,381 ; −0,107] | −30 % ; −34 % | 0,78 ; 0,70 ; 28 % | −8,2 [−15,2 ; −0,5] ; −0,253 [−0,382 ; −0,111] | −0,267 [−0,398 ; −0,124] | 544 % ; +1,8 |
| SL-B extremum + 0,50 ATR | −0,271 [−0,417 ; −0,106] | −32 % ; −36 % | 0,79 ; 0,70 ; 32 % | −8,4 [−16,9 ; −0,4] ; −0,273 [−0,416 ; −0,110] | −0,287 [−0,431 ; −0,125] | 634 % ; +1,6 |
| SL-B extremum + 1,00 ATR | −0,271 [−0,441 ; −0,095] | −31 % ; −34 % | 0,85 ; 0,74 ; 37 % | −6,5 [−15,5 ; +2,1] ; −0,273 [−0,442 ; −0,099] | −0,285 [−0,459 ; −0,108] | 287 % ; +3,5 |

#### ↳ F5 · x1 encore opposé hors nis_z_100 Q4 — H = 26

**5 bps aller-retour**

| Stop | Stoppés : figé ; dyn. | Effet pur, entrées figées : ATR [IC 95 %] | Figé : espérance ATR [IC] | Dyn. : PnL composé ; MDD valorisé | Dyn. : PF 1x ; PF pondéré ; WR | Dyn. : espérance bps [IC] ; ATR [IC] | Dyn. : timing ATR [IC] | Dyn. : trades ; /mois ; débloqués | Dyn. : durée méd. | Dyn. : part des frais ; brut/trade |
|---|---|---|---|---|---|---|---|---|---|---|
| Sans stop (contrôle) | 0 % ; 0 % | — | −0,274 [−0,638 ; +0,089] | −33 % ; −40 % | 0,91 ; 0,82 ; 47 % | −6,6 [−25,0 ; +11,4] ; −0,274 [−0,638 ; +0,089] | −0,298 [−0,689 ; +0,065] | 572 ; 7,9 ; 0 | 26 | sans objet (brut ≤ 0) ; −1,6 |
| SL-A 1,0 ATR | 77 % ; 77 % | −0,001 [−0,330 ; +0,336] | −0,276 [−0,444 ; −0,104] | −28 % ; −32 % | 0,80 ; 0,74 ; 21 % | −8,7 [−18,6 ; +1,4] ; −0,244 [−0,407 ; −0,077] | −0,253 [−0,418 ; −0,082] | 590 ; 8,2 ; 18 | 9 | sans objet (brut ≤ 0) ; −3,7 |
| SL-A 1,5 ATR | 66 % ; 66 % | −0,022 [−0,327 ; +0,290] | −0,296 [−0,490 ; −0,089] | −32 % ; −35 % | 0,84 ; 0,76 ; 29 % | −8,3 [−19,4 ; +2,7] ; −0,288 [−0,476 ; −0,083] | −0,292 [−0,485 ; −0,093] | 585 ; 8,1 ; 13 | 14 | sans objet (brut ≤ 0) ; −3,3 |
| SL-A 2,0 ATR | 55 % ; 55 % | −0,010 [−0,294 ; +0,288] | −0,285 [−0,503 ; −0,054] | −31 % ; −35 % | 0,91 ; 0,79 ; 35 % | −5,4 [−17,8 ; +8,1] ; −0,286 [−0,498 ; −0,055] | −0,298 [−0,514 ; −0,068] | 581 ; 8,1 ; 9 | 22 | sans objet (brut ≤ 0) ; −0,4 |
| SL-A 2,5 ATR | 45 % ; 45 % | +0,058 [−0,181 ; +0,312] | −0,216 [−0,471 ; +0,043] | −25 % ; −33 % | 0,95 ; 0,85 ; 40 % | −3,0 [−17,1 ; +11,4] ; −0,222 [−0,468 ; +0,032] | −0,243 [−0,499 ; +0,018] | 579 ; 8,0 ; 7 | 26 | 252 % ; +2,0 |
| SL-A 3,0 ATR | 36 % ; 36 % | +0,094 [−0,112 ; +0,322] | −0,180 [−0,461 ; +0,103] | −22 % ; −34 % | 0,97 ; 0,88 ; 43 % | −2,0 [−17,3 ; +13,3] ; −0,180 [−0,459 ; +0,109] | −0,199 [−0,481 ; +0,090] | 578 ; 8,0 ; 6 | 26 | 166 % ; +3,0 |
| SL-A 4,0 ATR | 26 % ; 26 % | +0,012 [−0,179 ; +0,228] | −0,262 [−0,552 ; +0,032] | −31 % ; −39 % | 0,91 ; 0,82 ; 44 % | −5,8 [−21,4 ; +10,5] ; −0,272 [−0,565 ; +0,026] | −0,286 [−0,578 ; +0,015] | 575 ; 8,0 ; 3 | 26 | sans objet (brut ≤ 0) ; −0,8 |
| SL-A 5,0 ATR | 18 % ; 18 % | +0,062 [−0,114 ; +0,255] | −0,213 [−0,525 ; +0,113] | −26 % ; −36 % | 0,95 ; 0,86 ; 45 % | −3,0 [−19,3 ; +13,8] ; −0,213 [−0,525 ; +0,113] | −0,223 [−0,543 ; +0,092] | 572 ; 7,9 ; 0 | 26 | 248 % ; +2,0 |
| SL-B extremum + 0,00 ATR | 81 % ; 81 % | +0,080 [−0,240 ; +0,400] | −0,195 [−0,344 ; −0,035] | −20 % ; −23 % | 0,86 ; 0,78 ; 17 % | −4,8 [−13,5 ; +4,4] ; −0,165 [−0,306 ; −0,007] | −0,172 [−0,321 ; −0,007] | 592 ; 8,2 ; 20 | 5 | > 1 000 % ; +0,2 |
| SL-B extremum + 0,25 ATR | 78 % ; 77 % | −0,009 [−0,322 ; +0,314] | −0,284 [−0,434 ; −0,121] | −31 % ; −32 % | 0,78 ; 0,70 ; 21 % | −8,9 [−18,3 ; +1,0] ; −0,271 [−0,421 ; −0,111] | −0,279 [−0,437 ; −0,111] | 589 ; 8,2 ; 17 | 8 | sans objet (brut ≤ 0) ; −3,9 |
| SL-B extremum + 0,50 ATR | 73 % ; 72 % | −0,027 [−0,334 ; +0,288] | −0,301 [−0,473 ; −0,113] | −33 % ; −34 % | 0,80 ; 0,71 ; 24 % | −9,7 [−20,3 ; +1,2] ; −0,296 [−0,466 ; −0,112] | −0,305 [−0,478 ; −0,118] | 586 ; 8,1 ; 14 | 10 | sans objet (brut ≤ 0) ; −4,7 |
| SL-B extremum + 1,00 ATR | 62 % ; 62 % | −0,054 [−0,351 ; +0,237] | −0,328 [−0,544 ; −0,098] | −35 % ; −37 % | 0,86 ; 0,75 ; 31 % | −8,0 [−20,8 ; +5,1] ; −0,320 [−0,536 ; −0,096] | −0,327 [−0,550 ; −0,096] | 584 ; 8,1 ; 12 | 17 | sans objet (brut ≤ 0) ; −3,0 |

**10 bps aller-retour**

| Stop | Figé : espérance ATR [IC] | Dyn. : PnL composé ; MDD valorisé | Dyn. : PF 1x ; PF pondéré ; WR | Dyn. : espérance bps [IC] ; ATR [IC] | Dyn. : timing ATR [IC] | Dyn. : part des frais ; brut/trade |
|---|---|---|---|---|---|---|
| Sans stop (contrôle) | −0,406 [−0,771 ; −0,043] | −44 % ; −49 % | 0,84 ; 0,75 ; 45 % | −11,6 [−30,0 ; +6,4] ; −0,406 [−0,771 ; −0,043] | −0,430 [−0,823 ; −0,069] | sans objet (brut ≤ 0) ; −1,6 |
| SL-A 1,0 ATR | −0,407 [−0,577 ; −0,230] | −40 % ; −42 % | 0,71 ; 0,64 ; 21 % | −13,7 [−23,6 ; −3,6] ; −0,377 [−0,540 ; −0,206] | −0,387 [−0,555 ; −0,209] | sans objet (brut ≤ 0) ; −3,7 |
| SL-A 1,5 ATR | −0,428 [−0,623 ; −0,217] | −43 % ; −45 % | 0,76 ; 0,67 ; 28 % | −13,3 [−24,4 ; −2,3] ; −0,421 [−0,613 ; −0,213] | −0,426 [−0,625 ; −0,219] | sans objet (brut ≤ 0) ; −3,3 |
| SL-A 2,0 ATR | −0,416 [−0,638 ; −0,181] | −42 % ; −45 % | 0,83 ; 0,71 ; 34 % | −10,4 [−22,8 ; +3,1] ; −0,419 [−0,636 ; −0,183] | −0,432 [−0,657 ; −0,198] | sans objet (brut ≤ 0) ; −0,4 |
| SL-A 2,5 ATR | −0,348 [−0,603 ; −0,080] | −37 % ; −42 % | 0,87 ; 0,76 ; 39 % | −8,0 [−22,1 ; +6,4] ; −0,355 [−0,605 ; −0,092] | −0,377 [−0,639 ; −0,112] | 504 % ; +2,0 |
| SL-A 3,0 ATR | −0,312 [−0,596 ; −0,024] | −34 % ; −40 % | 0,89 ; 0,80 ; 41 % | −7,0 [−22,3 ; +8,3] ; −0,311 [−0,594 ; −0,022] | −0,332 [−0,617 ; −0,039] | 332 % ; +3,0 |
| SL-A 4,0 ATR | −0,394 [−0,684 ; −0,099] | −42 % ; −46 % | 0,85 ; 0,75 ; 42 % | −10,8 [−26,4 ; +5,5] ; −0,403 [−0,698 ; −0,103] | −0,419 [−0,718 ; −0,119] | sans objet (brut ≤ 0) ; −0,8 |
| SL-A 5,0 ATR | −0,344 [−0,658 ; −0,012] | −38 % ; −44 % | 0,88 ; 0,78 ; 43 % | −8,0 [−24,3 ; +8,8] ; −0,344 [−0,658 ; −0,012] | −0,356 [−0,679 ; −0,038] | 497 % ; +2,0 |
| SL-B extremum + 0,00 ATR | −0,326 [−0,482 ; −0,161] | −33 % ; −35 % | 0,74 ; 0,65 ; 17 % | −9,8 [−18,5 ; −0,6] ; −0,298 [−0,448 ; −0,134] | −0,306 [−0,461 ; −0,134] | > 1 000 % ; +0,2 |
| SL-B extremum + 0,25 ATR | −0,415 [−0,574 ; −0,243] | −42 % ; −43 % | 0,69 ; 0,60 ; 20 % | −13,9 [−23,3 ; −4,0] ; −0,405 [−0,558 ; −0,238] | −0,413 [−0,575 ; −0,242] | sans objet (brut ≤ 0) ; −3,9 |
| SL-B extremum + 0,50 ATR | −0,433 [−0,608 ; −0,240] | −44 % ; −45 % | 0,71 ; 0,62 ; 24 % | −14,7 [−25,3 ; −3,8] ; −0,429 [−0,602 ; −0,241] | −0,439 [−0,616 ; −0,246] | sans objet (brut ≤ 0) ; −4,7 |
| SL-B extremum + 1,00 ATR | −0,460 [−0,681 ; −0,223] | −45 % ; −47 % | 0,78 ; 0,67 ; 30 % | −13,0 [−25,8 ; +0,1] ; −0,453 [−0,675 ; −0,226] | −0,461 [−0,688 ; −0,228] | sans objet (brut ≤ 0) ; −3,0 |

### Sortie de compression — R2 hors nis_z_100 Q4

#### ↳ F2b · x1 déjà retourné hors nis_z_100 Q4 — H = 13

**5 bps aller-retour**

| Stop | Stoppés : figé ; dyn. | Effet pur, entrées figées : ATR [IC 95 %] | Figé : espérance ATR [IC] | Dyn. : PnL composé ; MDD valorisé | Dyn. : PF 1x ; PF pondéré ; WR | Dyn. : espérance bps [IC] ; ATR [IC] | Dyn. : timing ATR [IC] | Dyn. : trades ; /mois ; débloqués | Dyn. : durée méd. | Dyn. : part des frais ; brut/trade |
|---|---|---|---|---|---|---|---|---|---|---|
| Sans stop (contrôle) | 0 % ; 0 % | — | +0,022 [−0,198 ; +0,240] | +2 % ; −20 % | 1,08 ; 1,02 ; 47 % | +3,9 [−7,0 ; +15,2] ; +0,022 [−0,198 ; +0,240] | +0,022 [−0,199 ; +0,239] | 695 ; 9,7 ; 0 | 13 | 56 % ; +8,9 |
| SL-A 1,0 ATR | 62 % ; 61 % | +0,034 [−0,124 ; +0,203] | +0,056 [−0,106 ; +0,230] | +9 % ; −11 % | 1,10 ; 1,08 ; 32 % | +3,6 [−4,5 ; +12,8] ; +0,061 [−0,099 ; +0,236] | +0,060 [−0,101 ; +0,236] | 710 ; 9,9 ; 18 | 9 | 58 % ; +8,6 |
| SL-A 1,5 ATR | 46 % ; 46 % | +0,087 [−0,021 ; +0,194] | +0,108 [−0,067 ; +0,297] | +16 % ; −11 % | 1,17 ; 1,12 ; 39 % | +6,8 [−2,1 ; +16,2] ; +0,097 [−0,076 ; +0,280] | +0,097 [−0,076 ; +0,282] | 703 ; 9,8 ; 9 | 13 | 42 % ; +11,8 |
| SL-A 2,0 ATR | 37 % ; 37 % | +0,017 [−0,076 ; +0,113] | +0,039 [−0,154 ; +0,239] | +5 % ; −14 % | 1,10 ; 1,04 ; 42 % | +4,5 [−5,2 ; +14,9] ; +0,032 [−0,161 ; +0,231] | +0,032 [−0,161 ; +0,231] | 699 ; 9,7 ; 5 | 13 | 52 % ; +9,5 |
| SL-A 2,5 ATR | 30 % ; 30 % | −0,060 [−0,160 ; +0,044] | −0,039 [−0,235 ; +0,167] | −7 % ; −24 % | 1,05 ; 0,97 ; 43 % | +2,5 [−7,4 ; +13,2] ; −0,038 [−0,234 ; +0,167] | −0,038 [−0,236 ; +0,167] | 696 ; 9,7 ; 2 | 13 | 67 % ; +7,5 |
| SL-A 3,0 ATR | 24 % ; 24 % | −0,070 [−0,164 ; +0,026] | −0,048 [−0,250 ; +0,163] | −8 % ; −26 % | 1,07 ; 0,96 ; 44 % | +3,3 [−7,3 ; +14,1] ; −0,048 [−0,250 ; +0,163] | −0,048 [−0,254 ; +0,164] | 695 ; 9,7 ; 1 | 13 | 60 % ; +8,3 |
| SL-A 4,0 ATR | 15 % ; 15 % | −0,053 [−0,138 ; +0,028] | −0,031 [−0,258 ; +0,187] | −5 % ; −27 % | 1,07 ; 0,98 ; 45 % | +3,4 [−7,6 ; +14,5] ; −0,031 [−0,258 ; +0,187] | −0,031 [−0,258 ; +0,185] | 695 ; 9,7 ; 0 | 13 | 59 % ; +8,4 |
| SL-A 5,0 ATR | 8 % ; 8 % | −0,026 [−0,092 ; +0,040] | −0,004 [−0,231 ; +0,221] | −1 % ; −25 % | 1,07 ; 1,00 ; 46 % | +3,5 [−7,3 ; +14,7] ; −0,004 [−0,231 ; +0,221] | −0,004 [−0,229 ; +0,221] | 695 ; 9,7 ; 0 | 13 | 59 % ; +8,5 |
| SL-B extremum + 0,00 ATR | 47 % ; 47 % | +0,042 [−0,085 ; +0,166] | +0,064 [−0,112 ; +0,246] | +9 % ; −13 % | 1,13 ; 1,07 ; 39 % | +5,3 [−3,3 ; +14,5] ; +0,060 [−0,114 ; +0,241] | +0,060 [−0,115 ; +0,242] | 703 ; 9,8 ; 9 | 13 | 48 % ; +10,3 |
| SL-B extremum + 0,25 ATR | 42 % ; 42 % | +0,013 [−0,102 ; +0,123] | +0,035 [−0,150 ; +0,225] | +4 % ; −19 % | 1,11 ; 1,03 ; 41 % | +4,9 [−4,2 ; +14,6] ; +0,032 [−0,152 ; +0,223] | +0,032 [−0,152 ; +0,220] | 699 ; 9,7 ; 5 | 13 | 51 % ; +9,9 |
| SL-B extremum + 0,50 ATR | 36 % ; 36 % | +0,010 [−0,085 ; +0,114] | +0,032 [−0,158 ; +0,234] | +5 % ; −16 % | 1,11 ; 1,04 ; 42 % | +4,9 [−4,4 ; +15,0] ; +0,031 [−0,159 ; +0,232] | +0,031 [−0,161 ; +0,231] | 698 ; 9,7 ; 4 | 13 | 50 % ; +9,9 |
| SL-B extremum + 1,00 ATR | 29 % ; 29 % | −0,031 [−0,131 ; +0,070] | −0,009 [−0,213 ; +0,197] | −3 % ; −22 % | 1,09 ; 0,99 ; 43 % | +4,0 [−6,1 ; +14,8] ; −0,014 [−0,218 ; +0,193] | −0,014 [−0,218 ; +0,194] | 696 ; 9,7 ; 2 | 13 | 56 % ; +9,0 |

**10 bps aller-retour**

| Stop | Figé : espérance ATR [IC] | Dyn. : PnL composé ; MDD valorisé | Dyn. : PF 1x ; PF pondéré ; WR | Dyn. : espérance bps [IC] ; ATR [IC] | Dyn. : timing ATR [IC] | Dyn. : part des frais ; brut/trade |
|---|---|---|---|---|---|---|
| Sans stop (contrôle) | −0,113 [−0,341 ; +0,105] | −17 % ; −32 % | 0,98 ; 0,91 ; 44 % | −1,1 [−12,0 ; +10,2] ; −0,113 [−0,341 ; +0,105] | −0,113 [−0,339 ; +0,107] | 112 % ; +8,9 |
| SL-A 1,0 ATR | −0,079 [−0,242 ; +0,100] | −12 % ; −24 % | 0,97 ; 0,92 ; 31 % | −1,4 [−9,5 ; +7,8] ; −0,074 [−0,237 ; +0,104] | −0,075 [−0,239 ; +0,104] | 116 % ; +8,6 |
| SL-A 1,5 ATR | −0,026 [−0,209 ; +0,164] | −6 % ; −21 % | 1,04 ; 0,97 ; 37 % | +1,8 [−7,1 ; +11,2] ; −0,038 [−0,218 ; +0,149] | −0,038 [−0,218 ; +0,147] | 85 % ; +11,8 |
| SL-A 2,0 ATR | −0,096 [−0,292 ; +0,107] | −15 % ; −26 % | 0,99 ; 0,91 ; 40 % | −0,5 [−10,2 ; +9,9] ; −0,103 [−0,298 ; +0,099] | −0,103 [−0,301 ; +0,098] | 105 % ; +9,5 |
| SL-A 2,5 ATR | −0,173 [−0,373 ; +0,038] | −24 % ; −35 % | 0,95 ; 0,86 ; 41 % | −2,5 [−12,4 ; +8,2] ; −0,173 [−0,372 ; +0,039] | −0,173 [−0,373 ; +0,037] | 133 % ; +7,5 |
| SL-A 3,0 ATR | −0,182 [−0,389 ; +0,034] | −25 % ; −37 % | 0,97 ; 0,85 ; 42 % | −1,7 [−12,3 ; +9,1] ; −0,183 [−0,389 ; +0,034] | −0,182 [−0,391 ; +0,032] | 120 % ; +8,3 |
| SL-A 4,0 ATR | −0,166 [−0,398 ; +0,053] | −23 % ; −37 % | 0,97 ; 0,87 ; 43 % | −1,6 [−12,6 ; +9,5] ; −0,166 [−0,398 ; +0,053] | −0,166 [−0,397 ; +0,051] | 119 % ; +8,4 |
| SL-A 5,0 ATR | −0,139 [−0,370 ; +0,085] | −20 % ; −36 % | 0,97 ; 0,89 ; 44 % | −1,5 [−12,3 ; +9,7] ; −0,139 [−0,370 ; +0,085] | −0,139 [−0,370 ; +0,086] | 118 % ; +8,5 |
| SL-B extremum + 0,00 ATR | −0,071 [−0,254 ; +0,111] | −11 % ; −25 % | 1,01 ; 0,93 ; 38 % | +0,3 [−8,3 ; +9,5] ; −0,075 [−0,256 ; +0,105] | −0,075 [−0,257 ; +0,108] | 97 % ; +10,3 |
| SL-B extremum + 0,25 ATR | −0,100 [−0,289 ; +0,092] | −15 % ; −30 % | 1,00 ; 0,90 ; 39 % | −0,1 [−9,2 ; +9,6] ; −0,103 [−0,291 ; +0,086] | −0,103 [−0,291 ; +0,088] | 101 % ; +9,9 |
| SL-B extremum + 0,50 ATR | −0,103 [−0,298 ; +0,099] | −15 % ; −28 % | 1,00 ; 0,91 ; 40 % | −0,1 [−9,4 ; +10,0] ; −0,104 [−0,300 ; +0,097] | −0,104 [−0,302 ; +0,100] | 101 % ; +9,9 |
| SL-B extremum + 1,00 ATR | −0,144 [−0,353 ; +0,070] | −21 % ; −33 % | 0,98 ; 0,88 ; 41 % | −1,0 [−11,1 ; +9,8] ; −0,148 [−0,358 ; +0,066] | −0,148 [−0,360 ; +0,063] | 111 % ; +9,0 |

#### ↳ F2b · x1 déjà retourné hors nis_z_100 Q4 — H = 26

**5 bps aller-retour**

| Stop | Stoppés : figé ; dyn. | Effet pur, entrées figées : ATR [IC 95 %] | Figé : espérance ATR [IC] | Dyn. : PnL composé ; MDD valorisé | Dyn. : PF 1x ; PF pondéré ; WR | Dyn. : espérance bps [IC] ; ATR [IC] | Dyn. : timing ATR [IC] | Dyn. : trades ; /mois ; débloqués | Dyn. : durée méd. | Dyn. : part des frais ; brut/trade |
|---|---|---|---|---|---|---|---|---|---|---|
| Sans stop (contrôle) | 0 % ; 0 % | — | +0,389 [+0,079 ; +0,700] | +72 % ; −13 % | 1,17 ; 1,28 ; 50 % | +11,5 [−2,9 ; +26,0] ; +0,389 [+0,079 ; +0,700] | +0,388 [+0,076 ; +0,700] | 639 ; 8,9 ; 0 | 26 | 30 % ; +16,5 |
| SL-A 1,0 ATR | 73 % ; 73 % | −0,271 [−0,525 ; −0,005] | +0,118 [−0,109 ; +0,362] | +21 % ; −14 % | 1,12 ; 1,15 ; 25 % | +4,8 [−5,6 ; +15,2] ; +0,128 [−0,084 ; +0,360] | +0,128 [−0,085 ; +0,360] | 684 ; 9,5 ; 48 | 9 | 51 % ; +9,8 |
| SL-A 1,5 ATR | 62 % ; 62 % | −0,251 [−0,479 ; −0,002] | +0,138 [−0,101 ; +0,381] | +27 % ; −12 % | 1,14 ; 1,16 ; 33 % | +7,1 [−5,9 ; +20,0] ; +0,154 [−0,076 ; +0,394] | +0,154 [−0,075 ; +0,391] | 667 ; 9,3 ; 30 | 16 | 41 % ; +12,1 |
| SL-A 2,0 ATR | 54 % ; 53 % | −0,332 [−0,541 ; −0,106] | +0,057 [−0,194 ; +0,307] | +10 % ; −16 % | 1,06 ; 1,06 ; 36 % | +3,7 [−8,8 ; +16,6] ; +0,069 [−0,169 ; +0,316] | +0,069 [−0,173 ; +0,312] | 656 ; 9,1 ; 19 | 23 | 58 % ; +8,7 |
| SL-A 2,5 ATR | 45 % ; 45 % | −0,378 [−0,604 ; −0,140] | +0,011 [−0,243 ; +0,267] | +3 % ; −21 % | 1,03 ; 1,02 ; 39 % | +1,6 [−10,9 ; +14,2] ; +0,018 [−0,229 ; +0,265] | +0,018 [−0,229 ; +0,263] | 651 ; 9,0 ; 12 | 26 | 75 % ; +6,6 |
| SL-A 3,0 ATR | 38 % ; 38 % | −0,348 [−0,581 ; −0,116] | +0,041 [−0,226 ; +0,320] | +5 % ; −22 % | 1,05 ; 1,03 ; 42 % | +3,2 [−9,6 ; +16,5] ; +0,044 [−0,226 ; +0,324] | +0,045 [−0,225 ; +0,325] | 645 ; 9,0 ; 6 | 26 | 61 % ; +8,2 |
| SL-A 4,0 ATR | 26 % ; 26 % | −0,223 [−0,436 ; −0,014] | +0,166 [−0,124 ; +0,463] | +26 % ; −13 % | 1,07 ; 1,12 ; 46 % | +5,2 [−8,8 ; +19,1] ; +0,173 [−0,114 ; +0,468] | +0,174 [−0,116 ; +0,460] | 641 ; 8,9 ; 2 | 26 | 49 % ; +10,2 |
| SL-A 5,0 ATR | 18 % ; 18 % | −0,150 [−0,347 ; +0,040] | +0,239 [−0,071 ; +0,541] | +38 % ; −13 % | 1,11 ; 1,16 ; 48 % | +7,5 [−6,6 ; +21,4] ; +0,244 [−0,063 ; +0,544] | +0,244 [−0,063 ; +0,544] | 640 ; 8,9 ; 1 | 26 | 40 % ; +12,5 |
| SL-B extremum + 0,00 ATR | 62 % ; 62 % | −0,279 [−0,520 ; −0,035] | +0,110 [−0,110 ; +0,336] | +18 % ; −15 % | 1,06 ; 1,11 ; 32 % | +3,4 [−8,0 ; +14,6] ; +0,109 [−0,104 ; +0,330] | +0,109 [−0,105 ; +0,329] | 666 ; 9,2 ; 30 | 15 | 60 % ; +8,4 |
| SL-B extremum + 0,25 ATR | 58 % ; 58 % | −0,323 [−0,565 ; −0,086] | +0,066 [−0,169 ; +0,306] | +11 % ; −18 % | 1,07 ; 1,07 ; 34 % | +3,9 [−8,7 ; +16,3] ; +0,070 [−0,153 ; +0,299] | +0,070 [−0,151 ; +0,298] | 661 ; 9,2 ; 24 | 19 | 56 % ; +8,9 |
| SL-B extremum + 0,50 ATR | 53 % ; 53 % | −0,328 [−0,541 ; −0,101] | +0,061 [−0,185 ; +0,316] | +11 % ; −15 % | 1,06 ; 1,07 ; 37 % | +3,7 [−9,4 ; +16,9] ; +0,071 [−0,165 ; +0,318] | +0,071 [−0,162 ; +0,318] | 655 ; 9,1 ; 18 | 24 | 57 % ; +8,7 |
| SL-B extremum + 1,00 ATR | 44 % ; 44 % | −0,341 [−0,558 ; −0,114] | +0,048 [−0,207 ; +0,305] | +5 % ; −20 % | 1,05 ; 1,04 ; 39 % | +3,3 [−9,1 ; +16,1] ; +0,044 [−0,201 ; +0,294] | +0,044 [−0,203 ; +0,292] | 649 ; 9,0 ; 11 | 26 | 60 % ; +8,3 |

**10 bps aller-retour**

| Stop | Figé : espérance ATR [IC] | Dyn. : PnL composé ; MDD valorisé | Dyn. : PF 1x ; PF pondéré ; WR | Dyn. : espérance bps [IC] ; ATR [IC] | Dyn. : timing ATR [IC] | Dyn. : part des frais ; brut/trade |
|---|---|---|---|---|---|---|
| Sans stop (contrôle) | +0,255 [−0,056 ; +0,569] | +42 % ; −17 % | 1,09 ; 1,18 ; 48 % | +6,5 [−7,9 ; +21,0] ; +0,255 [−0,056 ; +0,569] | +0,254 [−0,060 ; +0,568] | 61 % ; +16,5 |
| SL-A 1,0 ATR | −0,016 [−0,244 ; +0,232] | −1 % ; −22 % | 0,99 ; 1,00 ; 24 % | −0,2 [−10,6 ; +10,2] ; −0,006 [−0,219 ; +0,225] | −0,006 [−0,218 ; +0,224] | 102 % ; +9,8 |
| SL-A 1,5 ATR | +0,003 [−0,239 ; +0,246] | +4 % ; −18 % | 1,04 ; 1,03 ; 31 % | +2,1 [−10,9 ; +15,0] ; +0,020 [−0,212 ; +0,264] | +0,020 [−0,212 ; +0,260] | 83 % ; +12,1 |
| SL-A 2,0 ATR | −0,077 [−0,330 ; +0,179] | −9 % ; −27 % | 0,98 ; 0,96 ; 35 % | −1,3 [−13,8 ; +11,6] ; −0,065 [−0,303 ; +0,185] | −0,065 [−0,305 ; +0,182] | 116 % ; +8,7 |
| SL-A 2,5 ATR | −0,124 [−0,377 ; +0,137] | −15 % ; −32 % | 0,95 ; 0,93 ; 38 % | −3,4 [−15,9 ; +9,2] ; −0,117 [−0,368 ; +0,134] | −0,116 [−0,368 ; +0,135] | 150 % ; +6,6 |
| SL-A 3,0 ATR | −0,094 [−0,360 ; +0,187] | −13 % ; −33 % | 0,97 ; 0,95 ; 41 % | −1,8 [−14,6 ; +11,5] ; −0,091 [−0,357 ; +0,191] | −0,089 [−0,360 ; +0,192] | 122 % ; +8,2 |
| SL-A 4,0 ATR | +0,031 [−0,260 ; +0,331] | +4 % ; −24 % | 1,00 ; 1,03 ; 45 % | +0,2 [−13,8 ; +14,1] ; +0,039 [−0,251 ; +0,338] | +0,039 [−0,250 ; +0,332] | 98 % ; +10,2 |
| SL-A 5,0 ATR | +0,104 [−0,200 ; +0,405] | +14 % ; −20 % | 1,04 ; 1,07 ; 47 % | +2,5 [−11,6 ; +16,4] ; +0,110 [−0,195 ; +0,408] | +0,110 [−0,198 ; +0,413] | 80 % ; +12,5 |
| SL-B extremum + 0,00 ATR | −0,024 [−0,245 ; +0,205] | −3 % ; −24 % | 0,97 ; 0,99 ; 31 % | −1,6 [−13,0 ; +9,6] ; −0,025 [−0,237 ; +0,200] | −0,025 [−0,238 ; +0,198] | 120 % ; +8,4 |
| SL-B extremum + 0,25 ATR | −0,069 [−0,305 ; +0,172] | −9 % ; −29 % | 0,98 ; 0,96 ; 33 % | −1,1 [−13,7 ; +11,3] ; −0,064 [−0,291 ; +0,168] | −0,064 [−0,294 ; +0,168] | 113 % ; +8,9 |
| SL-B extremum + 0,50 ATR | −0,074 [−0,321 ; +0,185] | −9 % ; −27 % | 0,98 ; 0,96 ; 36 % | −1,3 [−14,4 ; +11,9] ; −0,063 [−0,297 ; +0,184] | −0,063 [−0,299 ; +0,182] | 114 % ; +8,7 |
| SL-B extremum + 1,00 ATR | −0,087 [−0,339 ; +0,177] | −14 % ; −32 % | 0,97 ; 0,94 ; 38 % | −1,7 [−14,1 ; +11,1] ; −0,090 [−0,338 ; +0,163] | −0,090 [−0,337 ; +0,164] | 120 % ; +8,3 |

#### ↳ F2b · x1 déjà retourné hors nis_z_100 Q4 — H = 48

**5 bps aller-retour**

| Stop | Stoppés : figé ; dyn. | Effet pur, entrées figées : ATR [IC 95 %] | Figé : espérance ATR [IC] | Dyn. : PnL composé ; MDD valorisé | Dyn. : PF 1x ; PF pondéré ; WR | Dyn. : espérance bps [IC] ; ATR [IC] | Dyn. : timing ATR [IC] | Dyn. : trades ; /mois ; débloqués | Dyn. : durée méd. | Dyn. : part des frais ; brut/trade |
|---|---|---|---|---|---|---|---|---|---|---|
| Sans stop (contrôle) | 0 % ; 0 % | — | +0,219 [−0,313 ; +0,768] | +18 % ; −31 % | 1,03 ; 1,08 ; 48 % | +3,4 [−18,7 ; +24,7] ; +0,219 [−0,313 ; +0,768] | +0,221 [−0,311 ; +0,773] | 564 ; 7,8 ; 0 | 48 | 60 % ; +8,4 |
| SL-A 1,0 ATR | 80 % ; 79 % | −0,139 [−0,657 ; +0,348] | +0,080 [−0,162 ; +0,347] | +27 % ; −19 % | 1,12 ; 1,18 ; 20 % | +5,4 [−6,1 ; +18,3] ; +0,181 [−0,065 ; +0,456] | +0,179 [−0,066 ; +0,458] | 661 ; 9,2 ; 105 | 9 | 48 % ; +10,4 |
| SL-A 1,5 ATR | 71 % ; 71 % | −0,101 [−0,561 ; +0,341] | +0,118 [−0,150 ; +0,401] | +26 % ; −17 % | 1,09 ; 1,14 ; 26 % | +5,5 [−8,4 ; +19,9] ; +0,171 [−0,112 ; +0,482] | +0,172 [−0,108 ; +0,480] | 635 ; 8,8 ; 81 | 16 | 48 % ; +10,5 |
| SL-A 2,0 ATR | 65 % ; 65 % | −0,172 [−0,616 ; +0,257] | +0,047 [−0,241 ; +0,357] | +12 % ; −22 % | 1,04 ; 1,07 ; 30 % | +2,6 [−11,2 ; +18,1] ; +0,094 [−0,207 ; +0,430] | +0,094 [−0,212 ; +0,427] | 615 ; 8,5 ; 62 | 23 | 65 % ; +7,6 |
| SL-A 2,5 ATR | 59 % ; 59 % | −0,292 [−0,750 ; +0,156] | −0,073 [−0,370 ; +0,244] | +2 % ; −29 % | 1,00 ; 1,02 ; 33 % | +0,2 [−14,4 ; +16,1] ; +0,024 [−0,304 ; +0,368] | +0,024 [−0,305 ; +0,363] | 605 ; 8,4 ; 53 | 32 | 96 % ; +5,2 |
| SL-A 3,0 ATR | 51 % ; 51 % | −0,185 [−0,639 ; +0,239] | +0,034 [−0,308 ; +0,391] | +13 % ; −27 % | 1,06 ; 1,07 ; 38 % | +5,2 [−11,3 ; +22,9] ; +0,109 [−0,258 ; +0,497] | +0,109 [−0,265 ; +0,497] | 591 ; 8,2 ; 36 | 47 | 49 % ; +10,2 |
| SL-A 4,0 ATR | 41 % ; 41 % | −0,170 [−0,583 ; +0,208] | +0,049 [−0,333 ; +0,451] | +4 % ; −30 % | 1,00 ; 1,03 ; 41 % | −0,4 [−17,4 ; +18,5] ; +0,053 [−0,324 ; +0,454] | +0,053 [−0,323 ; +0,451] | 581 ; 8,1 ; 23 | 48 | 109 % ; +4,6 |
| SL-A 5,0 ATR | 32 % ; 32 % | −0,104 [−0,468 ; +0,234] | +0,115 [−0,290 ; +0,526] | +12 % ; −25 % | 1,02 ; 1,06 ; 45 % | +2,3 [−15,3 ; +22,2] ; +0,114 [−0,290 ; +0,517] | +0,113 [−0,292 ; +0,518] | 575 ; 8,0 ; 16 | 48 | 68 % ; +7,3 |
| SL-B extremum + 0,00 ATR | 71 % ; 71 % | −0,097 [−0,550 ; +0,341] | +0,123 [−0,147 ; +0,406] | +28 % ; −18 % | 1,07 ; 1,15 ; 25 % | +4,3 [−9,1 ; +18,1] ; +0,180 [−0,110 ; +0,481] | +0,179 [−0,106 ; +0,475] | 636 ; 8,8 ; 84 | 16 | 54 % ; +9,3 |
| SL-B extremum + 0,25 ATR | 68 % ; 68 % | −0,169 [−0,629 ; +0,278] | +0,050 [−0,233 ; +0,339] | +16 % ; −18 % | 1,06 ; 1,09 ; 28 % | +3,7 [−9,0 ; +17,5] ; +0,120 [−0,172 ; +0,425] | +0,121 [−0,171 ; +0,423] | 626 ; 8,7 ; 72 | 19 | 57 % ; +8,7 |
| SL-B extremum + 0,50 ATR | 64 % ; 64 % | −0,175 [−0,619 ; +0,263] | +0,044 [−0,253 ; +0,365] | +20 % ; −21 % | 1,08 ; 1,10 ; 31 % | +5,5 [−8,5 ; +21,6] ; +0,134 [−0,174 ; +0,475] | +0,134 [−0,174 ; +0,469] | 614 ; 8,5 ; 61 | 24 | 48 % ; +10,5 |
| SL-B extremum + 1,00 ATR | 57 % ; 57 % | −0,178 [−0,623 ; +0,268] | +0,041 [−0,268 ; +0,357] | +10 % ; −25 % | 1,06 ; 1,06 ; 34 % | +4,4 [−11,7 ; +21,6] ; +0,095 [−0,249 ; +0,450] | +0,094 [−0,249 ; +0,450] | 598 ; 8,3 ; 45 | 35 | 53 % ; +9,4 |

**10 bps aller-retour**

| Stop | Figé : espérance ATR [IC] | Dyn. : PnL composé ; MDD valorisé | Dyn. : PF 1x ; PF pondéré ; WR | Dyn. : espérance bps [IC] ; ATR [IC] | Dyn. : timing ATR [IC] | Dyn. : part des frais ; brut/trade |
|---|---|---|---|---|---|---|
| Sans stop (contrôle) | +0,086 [−0,437 ; +0,633] | −0 % ; −34 % | 0,98 ; 1,02 ; 46 % | −1,6 [−23,7 ; +19,7] ; +0,086 [−0,437 ; +0,633] | +0,087 [−0,444 ; +0,639] | 119 % ; +8,4 |
| SL-A 1,0 ATR | −0,053 [−0,293 ; +0,216] | +4 % ; −22 % | 1,01 ; 1,04 ; 20 % | +0,4 [−11,1 ; +13,3] ; +0,046 [−0,204 ; +0,319] | +0,045 [−0,203 ; +0,326] | 96 % ; +10,4 |
| SL-A 1,5 ATR | −0,016 [−0,283 ; +0,270] | +4 % ; −21 % | 1,01 ; 1,03 ; 26 % | +0,5 [−13,4 ; +14,9] ; +0,038 [−0,249 ; +0,349] | +0,039 [−0,241 ; +0,348] | 96 % ; +10,5 |
| SL-A 2,0 ATR | −0,087 [−0,378 ; +0,228] | −7 % ; −29 % | 0,97 ; 0,98 ; 30 % | −2,4 [−16,2 ; +13,1] ; −0,038 [−0,347 ; +0,300] | −0,038 [−0,345 ; +0,297] | 131 % ; +7,6 |
| SL-A 2,5 ATR | −0,206 [−0,509 ; +0,116] | −15 % ; −38 % | 0,94 ; 0,95 ; 33 % | −4,8 [−19,4 ; +11,1] ; −0,109 [−0,442 ; +0,234] | −0,110 [−0,441 ; +0,233] | 192 % ; +5,2 |
| SL-A 3,0 ATR | −0,099 [−0,447 ; +0,263] | −5 % ; −35 % | 1,00 ; 0,99 ; 37 % | +0,2 [−16,3 ; +17,9] ; −0,024 [−0,394 ; +0,366] | −0,025 [−0,399 ; +0,366] | 98 % ; +10,2 |
| SL-A 4,0 ATR | −0,084 [−0,464 ; +0,315] | −12 % ; −39 % | 0,94 ; 0,97 ; 40 % | −5,4 [−22,4 ; +13,5] ; −0,080 [−0,455 ; +0,320] | −0,080 [−0,456 ; +0,319] | 217 % ; +4,6 |
| SL-A 5,0 ATR | −0,019 [−0,423 ; +0,392] | −6 % ; −33 % | 0,97 ; 0,99 ; 43 % | −2,7 [−20,3 ; +17,2] ; −0,020 [−0,428 ; +0,390] | −0,021 [−0,428 ; +0,385] | 137 % ; +7,3 |
| SL-B extremum + 0,00 ATR | −0,011 [−0,279 ; +0,276] | +6 % ; −24 % | 0,99 ; 1,04 ; 25 % | −0,7 [−14,1 ; +13,1] ; +0,046 [−0,246 ; +0,345] | +0,045 [−0,244 ; +0,342] | 108 % ; +9,3 |
| SL-B extremum + 0,25 ATR | −0,084 [−0,366 ; +0,212] | −3 % ; −29 % | 0,98 ; 1,00 ; 27 % | −1,3 [−14,0 ; +12,5] ; −0,013 [−0,307 ; +0,294] | −0,012 [−0,306 ; +0,288] | 114 % ; +8,7 |
| SL-B extremum + 0,50 ATR | −0,089 [−0,386 ; +0,234] | −0 % ; −27 % | 1,01 ; 1,01 ; 30 % | +0,5 [−13,5 ; +16,6] ; +0,002 [−0,310 ; +0,342] | +0,002 [−0,310 ; +0,338] | 95 % ; +10,5 |
| SL-B extremum + 1,00 ATR | −0,093 [−0,403 ; +0,228] | −8 % ; −35 % | 0,99 ; 0,98 ; 33 % | −0,6 [−16,7 ; +16,6] ; −0,039 [−0,388 ; +0,323] | −0,039 [−0,389 ; +0,321] | 106 % ; +9,4 |

#### ↳ F3 · x1 déjà retourné hors nis_z_100 Q4 — H = 13

**5 bps aller-retour**

| Stop | Stoppés : figé ; dyn. | Effet pur, entrées figées : ATR [IC 95 %] | Figé : espérance ATR [IC] | Dyn. : PnL composé ; MDD valorisé | Dyn. : PF 1x ; PF pondéré ; WR | Dyn. : espérance bps [IC] ; ATR [IC] | Dyn. : timing ATR [IC] | Dyn. : trades ; /mois ; débloqués | Dyn. : durée méd. | Dyn. : part des frais ; brut/trade |
|---|---|---|---|---|---|---|---|---|---|---|
| Sans stop (contrôle) | 0 % ; 0 % | — | +0,007 [−0,232 ; +0,253] | −3 % ; −27 % | 0,95 ; 0,99 ; 46 % | −2,9 [−13,9 ; +7,6] ; +0,007 [−0,232 ; +0,253] | +0,006 [−0,233 ; +0,245] | 646 ; 9,0 ; 0 | 13 | 241 % ; +2,1 |
| SL-A 1,0 ATR | 65 % ; 66 % | +0,049 [−0,114 ; +0,215] | +0,056 [−0,114 ; +0,234] | +7 % ; −13 % | 1,06 ; 1,06 ; 29 % | +2,1 [−5,0 ; +9,5] ; +0,045 [−0,119 ; +0,216] | +0,047 [−0,115 ; +0,211] | 689 ; 9,6 ; 44 | 7 | 70 % ; +7,1 |
| SL-A 1,5 ATR | 49 % ; 50 % | +0,125 [−0,003 ; +0,266] | +0,131 [−0,074 ; +0,355] | +17 % ; −16 % | 1,09 ; 1,12 ; 37 % | +3,7 [−4,9 ; +12,6] ; +0,094 [−0,106 ; +0,310] | +0,096 [−0,100 ; +0,307] | 670 ; 9,3 ; 24 | 13 | 58 % ; +8,7 |
| SL-A 2,0 ATR | 38 % ; 38 % | +0,096 [−0,028 ; +0,222] | +0,102 [−0,110 ; +0,334] | +13 % ; −17 % | 1,04 ; 1,09 ; 42 % | +1,7 [−7,7 ; +11,2] ; +0,085 [−0,126 ; +0,313] | +0,089 [−0,119 ; +0,314] | 656 ; 9,1 ; 12 | 13 | 75 % ; +6,7 |
| SL-A 2,5 ATR | 31 % ; 31 % | +0,046 [−0,081 ; +0,170] | +0,052 [−0,164 ; +0,292] | +6 % ; −17 % | 0,98 ; 1,05 ; 43 % | −0,9 [−10,8 ; +9,2] ; +0,046 [−0,168 ; +0,287] | +0,050 [−0,165 ; +0,285] | 650 ; 9,0 ; 5 | 13 | 122 % ; +4,1 |
| SL-A 3,0 ATR | 25 % ; 25 % | +0,028 [−0,076 ; +0,133] | +0,035 [−0,190 ; +0,280] | +4 % ; −21 % | 0,96 ; 1,03 ; 45 % | −2,4 [−12,9 ; +8,4] ; +0,035 [−0,189 ; +0,280] | +0,040 [−0,181 ; +0,288] | 647 ; 9,0 ; 1 | 13 | 192 % ; +2,6 |
| SL-A 4,0 ATR | 15 % ; 15 % | +0,034 [−0,049 ; +0,123] | +0,040 [−0,180 ; +0,282] | +3 % ; −19 % | 0,95 ; 1,03 ; 46 % | −2,8 [−13,8 ; +8,4] ; +0,040 [−0,180 ; +0,282] | +0,043 [−0,178 ; +0,280] | 646 ; 9,0 ; 0 | 13 | 224 % ; +2,2 |
| SL-A 5,0 ATR | 9 % ; 9 % | +0,019 [−0,048 ; +0,094] | +0,025 [−0,206 ; +0,273] | −0 % ; −23 % | 0,93 ; 1,01 ; 46 % | −3,9 [−15,5 ; +7,2] ; +0,025 [−0,206 ; +0,273] | +0,024 [−0,208 ; +0,269] | 646 ; 9,0 ; 0 | 13 | 460 % ; +1,1 |
| SL-B extremum + 0,00 ATR | 36 % ; 36 % | +0,097 [−0,023 ; +0,223] | +0,103 [−0,114 ; +0,341] | +15 % ; −16 % | 1,03 ; 1,10 ; 42 % | +1,4 [−8,2 ; +11,6] ; +0,096 [−0,120 ; +0,331] | +0,099 [−0,113 ; +0,329] | 651 ; 9,0 ; 5 | 13 | 78 % ; +6,4 |
| SL-B extremum + 0,25 ATR | 33 % ; 33 % | +0,065 [−0,059 ; +0,190] | +0,072 [−0,150 ; +0,315] | +10 % ; −16 % | 1,01 ; 1,07 ; 42 % | +0,4 [−9,5 ; +10,8] ; +0,067 [−0,153 ; +0,306] | +0,070 [−0,147 ; +0,308] | 649 ; 9,0 ; 3 | 13 | 93 % ; +5,4 |
| SL-B extremum + 0,50 ATR | 30 % ; 30 % | +0,034 [−0,089 ; +0,157] | +0,040 [−0,181 ; +0,280] | +5 % ; −18 % | 0,97 ; 1,04 ; 43 % | −1,7 [−11,7 ; +9,0] ; +0,035 [−0,184 ; +0,272] | +0,040 [−0,176 ; +0,274] | 649 ; 9,0 ; 3 | 13 | 151 % ; +3,3 |
| SL-B extremum + 1,00 ATR | 25 % ; 25 % | +0,007 [−0,096 ; +0,116] | +0,014 [−0,202 ; +0,259] | −0 % ; −21 % | 0,93 ; 1,01 ; 44 % | −4,0 [−14,8 ; +6,4] ; +0,014 [−0,201 ; +0,259] | +0,017 [−0,200 ; +0,259] | 647 ; 9,0 ; 1 | 13 | 518 % ; +1,0 |

**10 bps aller-retour**

| Stop | Figé : espérance ATR [IC] | Dyn. : PnL composé ; MDD valorisé | Dyn. : PF 1x ; PF pondéré ; WR | Dyn. : espérance bps [IC] ; ATR [IC] | Dyn. : timing ATR [IC] | Dyn. : part des frais ; brut/trade |
|---|---|---|---|---|---|---|
| Sans stop (contrôle) | −0,135 [−0,372 ; +0,109] | −20 % ; −34 % | 0,87 ; 0,89 ; 43 % | −7,9 [−18,9 ; +2,6] ; −0,135 [−0,372 ; +0,109] | −0,136 [−0,373 ; +0,104] | 482 % ; +2,1 |
| SL-A 1,0 ATR | −0,086 [−0,260 ; +0,097] | −13 % ; −21 % | 0,93 ; 0,90 ; 28 % | −2,9 [−10,0 ; +4,5] ; −0,099 [−0,271 ; +0,073] | −0,097 [−0,264 ; +0,072] | 140 % ; +7,1 |
| SL-A 1,5 ATR | −0,011 [−0,217 ; +0,215] | −5 % ; −24 % | 0,97 ; 0,98 ; 35 % | −1,3 [−9,9 ; +7,6] ; −0,049 [−0,251 ; +0,173] | −0,046 [−0,244 ; +0,170] | 115 % ; +8,7 |
| SL-A 2,0 ATR | −0,040 [−0,257 ; +0,195] | −7 % ; −23 % | 0,93 ; 0,96 ; 39 % | −3,3 [−12,7 ; +6,2] ; −0,056 [−0,270 ; +0,177] | −0,053 [−0,263 ; +0,170] | 150 % ; +6,7 |
| SL-A 2,5 ATR | −0,090 [−0,311 ; +0,152] | −13 % ; −25 % | 0,89 ; 0,93 ; 40 % | −5,9 [−15,8 ; +4,2] ; −0,095 [−0,313 ; +0,145] | −0,092 [−0,308 ; +0,142] | 245 % ; +4,1 |
| SL-A 3,0 ATR | −0,108 [−0,335 ; +0,140] | −15 % ; −28 % | 0,87 ; 0,92 ; 42 % | −7,4 [−17,9 ; +3,4] ; −0,107 [−0,334 ; +0,140] | −0,102 [−0,325 ; +0,146] | 383 % ; +2,6 |
| SL-A 4,0 ATR | −0,102 [−0,323 ; +0,141] | −16 % ; −28 % | 0,87 ; 0,92 ; 43 % | −7,8 [−18,8 ; +3,4] ; −0,102 [−0,323 ; +0,141] | −0,099 [−0,320 ; +0,139] | 449 % ; +2,2 |
| SL-A 5,0 ATR | −0,117 [−0,343 ; +0,126] | −18 % ; −31 % | 0,85 ; 0,91 ; 43 % | −8,9 [−20,5 ; +2,2] ; −0,117 [−0,343 ; +0,126] | −0,117 [−0,347 ; +0,128] | 920 % ; +1,1 |
| SL-B extremum + 0,00 ATR | −0,039 [−0,257 ; +0,200] | −6 % ; −22 % | 0,93 ; 0,97 ; 39 % | −3,6 [−13,2 ; +6,6] ; −0,046 [−0,268 ; +0,189] | −0,042 [−0,258 ; +0,192] | 155 % ; +6,4 |
| SL-B extremum + 0,25 ATR | −0,070 [−0,294 ; +0,174] | −10 % ; −23 % | 0,91 ; 0,95 ; 40 % | −4,6 [−14,5 ; +5,8] ; −0,075 [−0,298 ; +0,164] | −0,071 [−0,290 ; +0,166] | 185 % ; +5,4 |
| SL-B extremum + 0,50 ATR | −0,102 [−0,326 ; +0,141] | −14 % ; −26 % | 0,88 ; 0,92 ; 40 % | −6,7 [−16,7 ; +4,0] ; −0,107 [−0,329 ; +0,131] | −0,102 [−0,321 ; +0,137] | 302 % ; +3,3 |
| SL-B extremum + 1,00 ATR | −0,128 [−0,351 ; +0,123] | −18 % ; −28 % | 0,84 ; 0,90 ; 41 % | −9,0 [−19,8 ; +1,4] ; −0,128 [−0,350 ; +0,123] | −0,125 [−0,347 ; +0,118] | > 1 000 % ; +1,0 |

#### ↳ F3 · x1 déjà retourné hors nis_z_100 Q4 — H = 26

**5 bps aller-retour**

| Stop | Stoppés : figé ; dyn. | Effet pur, entrées figées : ATR [IC 95 %] | Figé : espérance ATR [IC] | Dyn. : PnL composé ; MDD valorisé | Dyn. : PF 1x ; PF pondéré ; WR | Dyn. : espérance bps [IC] ; ATR [IC] | Dyn. : timing ATR [IC] | Dyn. : trades ; /mois ; débloqués | Dyn. : durée méd. | Dyn. : part des frais ; brut/trade |
|---|---|---|---|---|---|---|---|---|---|---|
| Sans stop (contrôle) | 0 % ; 0 % | — | +0,144 [−0,293 ; +0,548] | +16 % ; −34 % | 1,13 ; 1,08 ; 47 % | +9,3 [−12,4 ; +28,2] ; +0,144 [−0,293 ; +0,548] | +0,122 [−0,319 ; +0,530] | 601 ; 8,3 ; 0 | 26 | 35 % ; +14,3 |
| SL-A 1,0 ATR | 76 % ; 76 % | −0,047 [−0,364 ; +0,307] | +0,097 [−0,127 ; +0,337] | +13 % ; −12 % | 1,14 ; 1,10 ; 22 % | +6,0 [−3,7 ; +16,0] ; +0,069 [−0,140 ; +0,287] | +0,079 [−0,134 ; +0,298] | 678 ; 9,4 ; 81 | 7 | 46 % ; +11,0 |
| SL-A 1,5 ATR | 62 % ; 62 % | +0,073 [−0,199 ; +0,384] | +0,216 [−0,059 ; +0,525] | +29 % ; −12 % | 1,18 ; 1,17 ; 31 % | +9,0 [−3,2 ; +21,2] ; +0,149 [−0,118 ; +0,440] | +0,157 [−0,102 ; +0,436] | 652 ; 9,1 ; 56 | 14 | 36 % ; +14,0 |
| SL-A 2,0 ATR | 52 % ; 52 % | +0,090 [−0,181 ; +0,378] | +0,233 [−0,078 ; +0,554] | +33 % ; −14 % | 1,17 ; 1,17 ; 36 % | +9,8 [−4,7 ; +24,0] ; +0,186 [−0,116 ; +0,496] | +0,193 [−0,106 ; +0,500] | 627 ; 8,7 ; 31 | 24 | 34 % ; +14,8 |
| SL-A 2,5 ATR | 45 % ; 45 % | +0,004 [−0,251 ; +0,283] | +0,148 [−0,172 ; +0,476] | +20 % ; −14 % | 1,10 ; 1,11 ; 39 % | +6,5 [−7,4 ; +20,6] ; +0,118 [−0,190 ; +0,433] | +0,121 [−0,188 ; +0,432] | 616 ; 8,6 ; 20 | 26 | 44 % ; +11,5 |
| SL-A 3,0 ATR | 40 % ; 40 % | −0,058 [−0,302 ; +0,209] | +0,085 [−0,231 ; +0,422] | +9 % ; −20 % | 1,03 ; 1,05 ; 41 % | +2,0 [−12,2 ; +16,8] ; +0,064 [−0,249 ; +0,389] | +0,066 [−0,246 ; +0,398] | 612 ; 8,5 ; 15 | 26 | 71 % ; +7,0 |
| SL-A 4,0 ATR | 26 % ; 26 % | +0,032 [−0,164 ; +0,249] | +0,175 [−0,161 ; +0,516] | +26 % ; −16 % | 1,12 ; 1,12 ; 44 % | +8,5 [−7,9 ; +24,9] ; +0,173 [−0,164 ; +0,516] | +0,164 [−0,178 ; +0,506] | 602 ; 8,4 ; 1 | 26 | 37 % ; +13,5 |
| SL-A 5,0 ATR | 19 % ; 19 % | +0,059 [−0,104 ; +0,250] | +0,202 [−0,152 ; +0,562] | +30 % ; −21 % | 1,13 ; 1,14 ; 46 % | +9,5 [−7,5 ; +26,5] ; +0,200 [−0,154 ; +0,562] | +0,176 [−0,175 ; +0,535] | 602 ; 8,4 ; 1 | 26 | 35 % ; +14,5 |
| SL-B extremum + 0,00 ATR | 50 % ; 50 % | +0,093 [−0,172 ; +0,382] | +0,236 [−0,078 ; +0,568] | +36 % ; −13 % | 1,18 ; 1,19 ; 36 % | +10,4 [−3,3 ; +24,5] ; +0,202 [−0,106 ; +0,520] | +0,207 [−0,097 ; +0,528] | 620 ; 8,6 ; 23 | 26 | 32 % ; +15,4 |
| SL-B extremum + 0,25 ATR | 47 % ; 47 % | +0,048 [−0,216 ; +0,334] | +0,192 [−0,132 ; +0,527] | +27 % ; −13 % | 1,14 ; 1,14 ; 38 % | +8,4 [−5,4 ; +22,6] ; +0,157 [−0,160 ; +0,480] | +0,161 [−0,149 ; +0,483] | 617 ; 8,6 ; 20 | 26 | 37 % ; +13,4 |
| SL-B extremum + 0,50 ATR | 44 % ; 44 % | −0,000 [−0,261 ; +0,279] | +0,143 [−0,175 ; +0,483] | +20 % ; −13 % | 1,09 ; 1,11 ; 39 % | +5,7 [−8,3 ; +20,1] ; +0,116 [−0,198 ; +0,439] | +0,117 [−0,194 ; +0,434] | 615 ; 8,5 ; 18 | 26 | 47 % ; +10,7 |
| SL-B extremum + 1,00 ATR | 39 % ; 39 % | −0,071 [−0,315 ; +0,193] | +0,073 [−0,246 ; +0,406] | +8 % ; −20 % | 1,02 ; 1,05 ; 40 % | +1,6 [−13,0 ; +16,5] ; +0,056 [−0,255 ; +0,380] | +0,054 [−0,262 ; +0,377] | 611 ; 8,5 ; 14 | 26 | 76 % ; +6,6 |

**10 bps aller-retour**

| Stop | Figé : espérance ATR [IC] | Dyn. : PnL composé ; MDD valorisé | Dyn. : PF 1x ; PF pondéré ; WR | Dyn. : espérance bps [IC] ; ATR [IC] | Dyn. : timing ATR [IC] | Dyn. : part des frais ; brut/trade |
|---|---|---|---|---|---|---|
| Sans stop (contrôle) | +0,003 [−0,437 ; +0,415] | −3 % ; −39 % | 1,06 ; 1,00 ; 45 % | +4,3 [−17,4 ; +23,2] ; +0,003 [−0,437 ; +0,415] | −0,018 [−0,461 ; +0,389] | 70 % ; +14,3 |
| SL-A 1,0 ATR | −0,044 [−0,275 ; +0,203] | −8 % ; −23 % | 1,02 ; 0,95 ; 21 % | +1,0 [−8,7 ; +11,0] ; −0,075 [−0,293 ; +0,152] | −0,065 [−0,291 ; +0,161] | 91 % ; +11,0 |
| SL-A 1,5 ATR | +0,076 [−0,209 ; +0,388] | +5 % ; −22 % | 1,08 ; 1,04 ; 30 % | +4,0 [−8,2 ; +16,2] ; +0,005 [−0,268 ; +0,299] | +0,014 [−0,255 ; +0,298] | 71 % ; +14,0 |
| SL-A 2,0 ATR | +0,093 [−0,229 ; +0,417] | +10 % ; −18 % | 1,08 ; 1,06 ; 35 % | +4,8 [−9,7 ; +19,0] ; +0,046 [−0,266 ; +0,363] | +0,053 [−0,258 ; +0,366] | 68 % ; +14,8 |
| SL-A 2,5 ATR | +0,007 [−0,320 ; +0,333] | −0 % ; −22 % | 1,02 ; 1,01 ; 37 % | +1,5 [−12,4 ; +15,6] ; −0,021 [−0,332 ; +0,299] | −0,019 [−0,331 ; +0,298] | 87 % ; +11,5 |
| SL-A 3,0 ATR | −0,056 [−0,379 ; +0,286] | −9 % ; −28 % | 0,96 ; 0,97 ; 39 % | −3,0 [−17,2 ; +11,8] ; −0,076 [−0,394 ; +0,254] | −0,073 [−0,389 ; +0,259] | 142 % ; +7,0 |
| SL-A 4,0 ATR | +0,034 [−0,308 ; +0,377] | +5 % ; −24 % | 1,05 ; 1,03 ; 42 % | +3,5 [−12,9 ; +19,9] ; +0,033 [−0,310 ; +0,376] | +0,024 [−0,319 ; +0,364] | 74 % ; +13,5 |
| SL-A 5,0 ATR | +0,061 [−0,297 ; +0,423] | +8 % ; −29 % | 1,06 ; 1,05 ; 44 % | +4,5 [−12,5 ; +21,5] ; +0,060 [−0,299 ; +0,423] | +0,035 [−0,323 ; +0,399] | 69 % ; +14,5 |
| SL-B extremum + 0,00 ATR | +0,096 [−0,226 ; +0,429] | +12 % ; −16 % | 1,09 ; 1,07 ; 35 % | +5,4 [−8,3 ; +19,5] ; +0,062 [−0,251 ; +0,383] | +0,067 [−0,243 ; +0,393] | 65 % ; +15,4 |
| SL-B extremum + 0,25 ATR | +0,051 [−0,280 ; +0,390] | +6 % ; −19 % | 1,05 ; 1,04 ; 36 % | +3,4 [−10,4 ; +17,6] ; +0,017 [−0,305 ; +0,343] | +0,021 [−0,296 ; +0,345] | 74 % ; +13,4 |
| SL-B extremum + 0,50 ATR | +0,003 [−0,321 ; +0,339] | −1 % ; −21 % | 1,01 ; 1,01 ; 37 % | +0,7 [−13,3 ; +15,1] ; −0,024 [−0,342 ; +0,305] | −0,023 [−0,338 ; +0,300] | 94 % ; +10,7 |
| SL-B extremum + 1,00 ATR | −0,068 [−0,390 ; +0,271] | −10 % ; −28 % | 0,95 ; 0,96 ; 39 % | −3,4 [−18,0 ; +11,5] ; −0,085 [−0,400 ; +0,240] | −0,087 [−0,404 ; +0,240] | 151 % ; +6,6 |

#### ↳ F3 · x1 déjà retourné hors nis_z_100 Q4 — H = 48

**5 bps aller-retour**

| Stop | Stoppés : figé ; dyn. | Effet pur, entrées figées : ATR [IC 95 %] | Figé : espérance ATR [IC] | Dyn. : PnL composé ; MDD valorisé | Dyn. : PF 1x ; PF pondéré ; WR | Dyn. : espérance bps [IC] ; ATR [IC] | Dyn. : timing ATR [IC] | Dyn. : trades ; /mois ; débloqués | Dyn. : durée méd. | Dyn. : part des frais ; brut/trade |
|---|---|---|---|---|---|---|---|---|---|---|
| Sans stop (contrôle) | 0 % ; 0 % | — | +0,201 [−0,407 ; +0,812] | +3 % ; −47 % | 1,03 ; 1,04 ; 49 % | +2,8 [−22,9 ; +26,9] ; +0,201 [−0,407 ; +0,812] | +0,251 [−0,317 ; +0,815] | 523 ; 7,3 ; 0 | 48 | 64 % ; +7,8 |
| SL-A 1,0 ATR | 82 % ; 82 % | −0,102 [−0,666 ; +0,438] | +0,099 [−0,163 ; +0,405] | +8 % ; −16 % | 1,01 ; 1,07 ; 18 % | +0,7 [−10,8 ; +13,0] ; +0,076 [−0,183 ; +0,362] | +0,089 [−0,173 ; +0,369] | 650 ; 9,0 ; 131 | 7 | 88 % ; +5,7 |
| SL-A 1,5 ATR | 73 % ; 74 % | +0,018 [−0,491 ; +0,526] | +0,219 [−0,103 ; +0,588] | +9 % ; −20 % | 0,96 ; 1,06 ; 24 % | −2,3 [−16,4 ; +12,4] ; +0,091 [−0,194 ; +0,416] | +0,109 [−0,180 ; +0,426] | 619 ; 8,6 ; 102 | 13 | 185 % ; +2,7 |
| SL-A 2,0 ATR | 66 % ; 66 % | +0,012 [−0,480 ; +0,512] | +0,213 [−0,151 ; +0,610] | +11 % ; −21 % | 0,96 ; 1,07 ; 29 % | −2,6 [−18,3 ; +13,0] ; +0,121 [−0,214 ; +0,463] | +0,142 [−0,188 ; +0,479] | 585 ; 8,1 ; 70 | 22 | 210 % ; +2,4 |
| SL-A 2,5 ATR | 60 % ; 60 % | −0,043 [−0,459 ; +0,394] | +0,158 [−0,234 ; +0,597] | +4 % ; −23 % | 0,93 ; 1,03 ; 34 % | −5,7 [−21,8 ; +10,7] ; +0,124 [−0,242 ; +0,531] | +0,142 [−0,216 ; +0,521] | 566 ; 7,9 ; 51 | 31 | sans objet (brut ≤ 0) ; −0,7 |
| SL-A 3,0 ATR | 55 % ; 55 % | −0,083 [−0,478 ; +0,337] | +0,118 [−0,275 ; +0,556] | −2 % ; −25 % | 0,88 ; 1,00 ; 37 % | −10,9 [−28,9 ; +6,6] ; +0,118 [−0,253 ; +0,543] | +0,138 [−0,222 ; +0,546] | 558 ; 7,8 ; 42 | 38 | sans objet (brut ≤ 0) ; −5,9 |
| SL-A 4,0 ATR | 39 % ; 39 % | +0,098 [−0,262 ; +0,472] | +0,298 [−0,108 ; +0,779] | +28 % ; −17 % | 1,02 ; 1,12 ; 43 % | +1,8 [−17,8 ; +22,4] ; +0,331 [−0,073 ; +0,793] | +0,370 [−0,032 ; +0,826] | 539 ; 7,5 ; 23 | 48 | 73 % ; +6,8 |
| SL-A 5,0 ATR | 28 % ; 28 % | +0,207 [−0,101 ; +0,529] | +0,408 [−0,061 ; +0,932] | +49 % ; −20 % | 1,11 ; 1,19 ; 47 % | +10,5 [−11,2 ; +32,2] ; +0,444 [−0,017 ; +0,958] | +0,456 [−0,000 ; +0,959] | 536 ; 7,4 ; 18 | 48 | 32 % ; +15,5 |
| SL-B extremum + 0,00 ATR | 64 % ; 65 % | +0,093 [−0,328 ; +0,528] | +0,293 [−0,078 ; +0,722] | +15 % ; −19 % | 0,98 ; 1,09 ; 30 % | −1,3 [−16,7 ; +14,6] ; +0,193 [−0,166 ; +0,594] | +0,199 [−0,156 ; +0,588] | 577 ; 8,0 ; 60 | 25 | 135 % ; +3,7 |
| SL-B extremum + 0,25 ATR | 62 % ; 63 % | +0,031 [−0,398 ; +0,477] | +0,232 [−0,170 ; +0,684] | +10 % ; −18 % | 0,95 ; 1,06 ; 32 % | −4,1 [−20,6 ; +12,7] ; +0,161 [−0,212 ; +0,586] | +0,173 [−0,199 ; +0,587] | 571 ; 7,9 ; 54 | 28 | 562 % ; +0,9 |
| SL-B extremum + 0,50 ATR | 60 % ; 60 % | −0,035 [−0,464 ; +0,418] | +0,166 [−0,232 ; +0,622] | +3 % ; −20 % | 0,91 ; 1,03 ; 33 % | −7,4 [−24,1 ; +9,2] ; +0,116 [−0,263 ; +0,549] | +0,129 [−0,240 ; +0,544] | 568 ; 7,9 ; 51 | 32 | sans objet (brut ≤ 0) ; −2,4 |
| SL-B extremum + 1,00 ATR | 54 % ; 54 % | −0,117 [−0,512 ; +0,298] | +0,084 [−0,309 ; +0,556] | −7 % ; −26 % | 0,86 ; 0,99 ; 36 % | −12,8 [−30,4 ; +4,7] ; +0,080 [−0,302 ; +0,541] | +0,099 [−0,278 ; +0,535] | 557 ; 7,7 ; 41 | 40 | sans objet (brut ≤ 0) ; −7,8 |

**10 bps aller-retour**

| Stop | Figé : espérance ATR [IC] | Dyn. : PnL composé ; MDD valorisé | Dyn. : PF 1x ; PF pondéré ; WR | Dyn. : espérance bps [IC] ; ATR [IC] | Dyn. : timing ATR [IC] | Dyn. : part des frais ; brut/trade |
|---|---|---|---|---|---|---|
| Sans stop (contrôle) | +0,065 [−0,542 ; +0,665] | −12 % ; −51 % | 0,98 ; 0,98 ; 48 % | −2,2 [−27,9 ; +21,9] ; +0,065 [−0,542 ; +0,665] | +0,115 [−0,451 ; +0,678] | 128 % ; +7,8 |
| SL-A 1,0 ATR | −0,037 [−0,304 ; +0,269] | −11 % ; −24 % | 0,91 ; 0,94 ; 17 % | −4,3 [−15,8 ; +8,0] ; −0,068 [−0,331 ; +0,217] | −0,055 [−0,317 ; +0,238] | 177 % ; +5,7 |
| SL-A 1,5 ATR | +0,083 [−0,240 ; +0,458] | −10 % ; −28 % | 0,89 ; 0,96 ; 24 % | −7,3 [−21,4 ; +7,4] ; −0,053 [−0,339 ; +0,272] | −0,034 [−0,324 ; +0,288] | 369 % ; +2,7 |
| SL-A 2,0 ATR | +0,077 [−0,293 ; +0,475] | −7 % ; −27 % | 0,90 ; 0,98 ; 29 % | −7,6 [−23,3 ; +8,0] ; −0,018 [−0,360 ; +0,322] | +0,003 [−0,329 ; +0,342] | 421 % ; +2,4 |
| SL-A 2,5 ATR | +0,022 [−0,367 ; +0,458] | −13 % ; −28 % | 0,88 ; 0,96 ; 33 % | −10,7 [−26,8 ; +5,7] ; −0,014 [−0,381 ; +0,394] | +0,004 [−0,355 ; +0,382] | sans objet (brut ≤ 0) ; −0,7 |
| SL-A 3,0 ATR | −0,018 [−0,408 ; +0,415] | −17 % ; −32 % | 0,83 ; 0,94 ; 36 % | −15,9 [−33,9 ; +1,6] ; −0,017 [−0,385 ; +0,416] | +0,002 [−0,355 ; +0,409] | sans objet (brut ≤ 0) ; −5,9 |
| SL-A 4,0 ATR | +0,162 [−0,244 ; +0,641] | +9 % ; −22 % | 0,97 ; 1,05 ; 42 % | −3,2 [−22,8 ; +17,4] ; +0,196 [−0,203 ; +0,656] | +0,235 [−0,166 ; +0,690] | 147 % ; +6,8 |
| SL-A 5,0 ATR | +0,272 [−0,196 ; +0,785] | +27 % ; −25 % | 1,06 ; 1,11 ; 45 % | +5,5 [−16,2 ; +27,2] ; +0,309 [−0,149 ; +0,818] | +0,321 [−0,128 ; +0,819] | 65 % ; +15,5 |
| SL-B extremum + 0,00 ATR | +0,158 [−0,214 ; +0,587] | −3 % ; −25 % | 0,92 ; 1,00 ; 29 % | −6,3 [−21,7 ; +9,6] ; +0,054 [−0,308 ; +0,454] | +0,060 [−0,294 ; +0,451] | 270 % ; +3,7 |
| SL-B extremum + 0,25 ATR | +0,096 [−0,306 ; +0,541] | −8 % ; −24 % | 0,89 ; 0,98 ; 31 % | −9,1 [−25,6 ; +7,7] ; +0,022 [−0,356 ; +0,444] | +0,034 [−0,338 ; +0,445] | > 1 000 % ; +0,9 |
| SL-B extremum + 0,50 ATR | +0,030 [−0,370 ; +0,487] | −13 % ; −26 % | 0,86 ; 0,95 ; 33 % | −12,4 [−29,1 ; +4,2] ; −0,022 [−0,399 ; +0,406] | −0,010 [−0,380 ; +0,407] | sans objet (brut ≤ 0) ; −2,4 |
| SL-B extremum + 1,00 ATR | −0,052 [−0,448 ; +0,408] | −21 % ; −34 % | 0,82 ; 0,92 ; 35 % | −17,8 [−35,4 ; −0,3] ; −0,056 [−0,440 ; +0,397] | −0,037 [−0,411 ; +0,390] | sans objet (brut ≤ 0) ; −7,8 |

#### R2 hors nis_z_100 Q4 — H = 13

**5 bps aller-retour**

| Stop | Stoppés : figé ; dyn. | Effet pur, entrées figées : ATR [IC 95 %] | Figé : espérance ATR [IC] | Dyn. : PnL composé ; MDD valorisé | Dyn. : PF 1x ; PF pondéré ; WR | Dyn. : espérance bps [IC] ; ATR [IC] | Dyn. : timing ATR [IC] | Dyn. : trades ; /mois ; débloqués | Dyn. : durée méd. | Dyn. : part des frais ; brut/trade |
|---|---|---|---|---|---|---|---|---|---|---|
| Sans stop (contrôle) | 0 % ; 0 % | — | +0,031 [−0,146 ; +0,208] | +1 % ; −31 % | 1,01 ; 1,01 ; 46 % | +0,3 [−8,9 ; +8,8] ; +0,031 [−0,146 ; +0,208] | +0,034 [−0,144 ; +0,207] | 1 240 ; 17,2 ; 0 | 13 | 94 % ; +5,3 |
| SL-A 1,0 ATR | 64 % ; 64 % | +0,021 [−0,106 ; +0,150] | +0,052 [−0,077 ; +0,178] | +15 % ; −18 % | 1,07 ; 1,06 ; 30 % | +2,7 [−3,3 ; +9,0] ; +0,049 [−0,072 ; +0,172] | +0,047 [−0,076 ; +0,174] | 1 365 ; 19,0 ; 132 | 7 | 65 % ; +7,7 |
| SL-A 1,5 ATR | 48 % ; 48 % | +0,085 [−0,011 ; +0,185] | +0,116 [−0,026 ; +0,264] | +36 % ; −14 % | 1,13 ; 1,12 ; 38 % | +5,2 [−1,2 ; +12,1] ; +0,104 [−0,035 ; +0,253] | +0,104 [−0,037 ; +0,254] | 1 295 ; 18,0 ; 61 | 13 | 49 % ; +10,2 |
| SL-A 2,0 ATR | 37 % ; 38 % | +0,034 [−0,050 ; +0,123] | +0,065 [−0,082 ; +0,219] | +12 % ; −19 % | 1,05 ; 1,05 ; 41 % | +2,1 [−5,1 ; +9,9] ; +0,048 [−0,097 ; +0,203] | +0,050 [−0,098 ; +0,211] | 1 264 ; 17,6 ; 28 | 13 | 70 % ; +7,1 |
| SL-A 2,5 ATR | 30 % ; 30 % | −0,027 [−0,108 ; +0,061] | +0,005 [−0,146 ; +0,167] | −2 % ; −27 % | 1,00 ; 1,00 ; 42 % | +0,1 [−7,4 ; +8,0] ; +0,003 [−0,150 ; +0,166] | +0,007 [−0,148 ; +0,173] | 1 250 ; 17,4 ; 11 | 13 | 98 % ; +5,1 |
| SL-A 3,0 ATR | 24 % ; 24 % | −0,033 [−0,108 ; +0,043] | −0,001 [−0,157 ; +0,162] | −3 % ; −32 % | 1,00 ; 1,00 ; 44 % | +0,1 [−7,9 ; +8,4] ; +0,000 [−0,157 ; +0,170] | +0,006 [−0,153 ; +0,177] | 1 243 ; 17,3 ; 4 | 13 | 98 % ; +5,1 |
| SL-A 4,0 ATR | 15 % ; 15 % | −0,037 [−0,101 ; +0,024] | −0,006 [−0,173 ; +0,165] | −6 % ; −34 % | 0,99 ; 0,99 ; 45 % | −0,6 [−9,5 ; +8,3] ; −0,007 [−0,174 ; +0,164] | −0,003 [−0,173 ; +0,170] | 1 240 ; 17,2 ; 1 | 13 | 113 % ; +4,4 |
| SL-A 5,0 ATR | 9 % ; 9 % | −0,030 [−0,082 ; +0,019] | +0,001 [−0,174 ; +0,181] | −5 % ; −36 % | 0,98 ; 0,99 ; 46 % | −1,1 [−10,3 ; +7,9] ; +0,001 [−0,174 ; +0,181] | +0,003 [−0,174 ; +0,185] | 1 240 ; 17,2 ; 0 | 13 | 128 % ; +3,9 |
| SL-B extremum + 0,00 ATR | 42 % ; 42 % | +0,046 [−0,050 ; +0,142] | +0,078 [−0,068 ; +0,234] | +22 % ; −15 % | 1,07 ; 1,08 ; 40 % | +3,1 [−4,1 ; +10,6] ; +0,076 [−0,071 ; +0,229] | +0,076 [−0,074 ; +0,232] | 1 264 ; 17,6 ; 29 | 13 | 62 % ; +8,1 |
| SL-B extremum + 0,25 ATR | 38 % ; 37 % | +0,018 [−0,069 ; +0,105] | +0,049 [−0,106 ; +0,210] | +14 % ; −20 % | 1,05 ; 1,05 ; 41 % | +2,5 [−5,2 ; +10,4] ; +0,053 [−0,103 ; +0,214] | +0,053 [−0,105 ; +0,216] | 1 257 ; 17,5 ; 20 | 13 | 67 % ; +7,5 |
| SL-B extremum + 0,50 ATR | 33 % ; 33 % | +0,003 [−0,077 ; +0,087] | +0,035 [−0,116 ; +0,193] | +10 % ; −21 % | 1,03 ; 1,04 ; 42 % | +1,5 [−5,9 ; +9,2] ; +0,041 [−0,108 ; +0,199] | +0,044 [−0,109 ; +0,206] | 1 255 ; 17,4 ; 17 | 13 | 76 % ; +6,5 |
| SL-B extremum + 1,00 ATR | 27 % ; 27 % | −0,031 [−0,107 ; +0,046] | +0,001 [−0,152 ; +0,164] | −4 % ; −31 % | 0,99 ; 1,00 ; 43 % | −0,8 [−9,0 ; +7,4] ; +0,001 [−0,153 ; +0,170] | +0,006 [−0,151 ; +0,177] | 1 245 ; 17,3 ; 6 | 13 | 118 % ; +4,2 |

**10 bps aller-retour**

| Stop | Figé : espérance ATR [IC] | Dyn. : PnL composé ; MDD valorisé | Dyn. : PF 1x ; PF pondéré ; WR | Dyn. : espérance bps [IC] ; ATR [IC] | Dyn. : timing ATR [IC] | Dyn. : part des frais ; brut/trade |
|---|---|---|---|---|---|---|
| Sans stop (contrôle) | −0,106 [−0,283 ; +0,073] | −30 % ; −46 % | 0,92 ; 0,90 ; 44 % | −4,7 [−13,9 ; +3,8] ; −0,106 [−0,283 ; +0,073] | −0,103 [−0,282 ; +0,072] | 188 % ; +5,3 |
| SL-A 1,0 ATR | −0,085 [−0,217 ; +0,048] | −24 % ; −36 % | 0,94 ; 0,91 ; 29 % | −2,3 [−8,3 ; +4,0] ; −0,089 [−0,215 ; +0,036] | −0,091 [−0,220 ; +0,035] | 131 % ; +7,7 |
| SL-A 1,5 ATR | −0,021 [−0,166 ; +0,131] | −8 % ; −28 % | 1,00 ; 0,98 ; 36 % | +0,2 [−6,2 ; +7,1] ; −0,033 [−0,179 ; +0,119] | −0,034 [−0,180 ; +0,121] | 98 % ; +10,2 |
| SL-A 2,0 ATR | −0,072 [−0,219 ; +0,084] | −23 % ; −37 % | 0,94 ; 0,92 ; 39 % | −2,9 [−10,1 ; +4,9] ; −0,089 [−0,238 ; +0,071] | −0,087 [−0,237 ; +0,077] | 140 % ; +7,1 |
| SL-A 2,5 ATR | −0,132 [−0,286 ; +0,034] | −33 % ; −45 % | 0,91 ; 0,89 ; 40 % | −4,9 [−12,4 ; +3,0] ; −0,133 [−0,292 ; +0,033] | −0,129 [−0,288 ; +0,039] | 196 % ; +5,1 |
| SL-A 3,0 ATR | −0,138 [−0,294 ; +0,031] | −33 % ; −47 % | 0,91 ; 0,89 ; 42 % | −4,9 [−12,9 ; +3,4] ; −0,137 [−0,297 ; +0,033] | −0,131 [−0,291 ; +0,040] | 196 % ; +5,1 |
| SL-A 4,0 ATR | −0,143 [−0,311 ; +0,030] | −35 % ; −49 % | 0,90 ; 0,88 ; 43 % | −5,6 [−14,5 ; +3,3] ; −0,144 [−0,311 ; +0,030] | −0,140 [−0,309 ; +0,036] | 225 % ; +4,4 |
| SL-A 5,0 ATR | −0,136 [−0,313 ; +0,049] | −35 % ; −50 % | 0,89 ; 0,89 ; 43 % | −6,1 [−15,3 ; +2,9] ; −0,136 [−0,313 ; +0,049] | −0,133 [−0,309 ; +0,052] | 256 % ; +3,9 |
| SL-B extremum + 0,00 ATR | −0,059 [−0,209 ; +0,096] | −16 % ; −33 % | 0,96 ; 0,95 ; 38 % | −1,9 [−9,1 ; +5,6] ; −0,061 [−0,207 ; +0,093] | −0,061 [−0,211 ; +0,095] | 123 % ; +8,1 |
| SL-B extremum + 0,25 ATR | −0,088 [−0,243 ; +0,076] | −22 % ; −39 % | 0,95 ; 0,93 ; 39 % | −2,5 [−10,2 ; +5,4] ; −0,084 [−0,239 ; +0,079] | −0,084 [−0,239 ; +0,082] | 133 % ; +7,5 |
| SL-B extremum + 0,50 ATR | −0,102 [−0,256 ; +0,058] | −25 % ; −39 % | 0,93 ; 0,92 ; 40 % | −3,5 [−10,9 ; +4,2] ; −0,096 [−0,249 ; +0,066] | −0,093 [−0,248 ; +0,071] | 153 % ; +6,5 |
| SL-B extremum + 1,00 ATR | −0,136 [−0,291 ; +0,029] | −34 % ; −47 % | 0,89 ; 0,88 ; 41 % | −5,8 [−14,0 ; +2,4] ; −0,136 [−0,292 ; +0,033] | −0,131 [−0,289 ; +0,041] | 235 % ; +4,2 |

#### R2 hors nis_z_100 Q4 — H = 26

**5 bps aller-retour**

| Stop | Stoppés : figé ; dyn. | Effet pur, entrées figées : ATR [IC 95 %] | Figé : espérance ATR [IC] | Dyn. : PnL composé ; MDD valorisé | Dyn. : PF 1x ; PF pondéré ; WR | Dyn. : espérance bps [IC] ; ATR [IC] | Dyn. : timing ATR [IC] | Dyn. : trades ; /mois ; débloqués | Dyn. : durée méd. | Dyn. : part des frais ; brut/trade |
|---|---|---|---|---|---|---|---|---|---|---|
| Sans stop (contrôle) | 0 % ; 0 % | — | +0,354 [+0,051 ; +0,643] | +122 % ; −20 % | 1,18 ; 1,23 ; 49 % | +12,3 [−1,5 ; +25,8] ; +0,354 [+0,051 ; +0,643] | +0,344 [+0,045 ; +0,626] | 1 080 ; 15,0 ; 0 | 26 | 29 % ; +17,3 |
| SL-A 1,0 ATR | 75 % ; 75 % | −0,238 [−0,445 ; −0,012] | +0,116 [−0,059 ; +0,288] | +32 % ; −16 % | 1,13 ; 1,11 ; 23 % | +5,4 [−2,9 ; +14,0] ; +0,091 [−0,073 ; +0,251] | +0,089 [−0,077 ; +0,255] | 1 310 ; 18,2 ; 244 | 7 | 48 % ; +10,4 |
| SL-A 1,5 ATR | 62 % ; 62 % | −0,172 [−0,347 ; +0,008] | +0,181 [−0,014 ; +0,395] | +57 % ; −15 % | 1,17 ; 1,16 ; 32 % | +8,6 [−1,3 ; +18,7] ; +0,152 [−0,042 ; +0,360] | +0,150 [−0,044 ; +0,356] | 1 210 ; 16,8 ; 148 | 15 | 37 % ; +13,6 |
| SL-A 2,0 ATR | 53 % ; 53 % | −0,192 [−0,361 ; −0,020] | +0,161 [−0,046 ; +0,376] | +45 % ; −17 % | 1,12 ; 1,12 ; 37 % | +7,1 [−3,8 ; +18,2] ; +0,134 [−0,076 ; +0,356] | +0,132 [−0,079 ; +0,353] | 1 145 ; 15,9 ; 83 | 24 | 41 % ; +12,1 |
| SL-A 2,5 ATR | 45 % ; 45 % | −0,231 [−0,397 ; −0,062] | +0,123 [−0,096 ; +0,355] | +32 % ; −17 % | 1,08 ; 1,09 ; 40 % | +5,3 [−6,2 ; +16,6] ; +0,109 [−0,114 ; +0,337] | +0,109 [−0,118 ; +0,338] | 1 123 ; 15,6 ; 56 | 26 | 48 % ; +10,3 |
| SL-A 3,0 ATR | 38 % ; 38 % | −0,222 [−0,383 ; −0,062] | +0,132 [−0,092 ; +0,374] | +27 % ; −20 % | 1,06 ; 1,08 ; 42 % | +3,9 [−7,7 ; +15,8] ; +0,112 [−0,113 ; +0,350] | +0,116 [−0,111 ; +0,360] | 1 104 ; 15,3 ; 34 | 26 | 56 % ; +8,9 |
| SL-A 4,0 ATR | 26 % ; 25 % | −0,120 [−0,252 ; +0,011] | +0,234 [−0,016 ; +0,494] | +73 % ; −16 % | 1,13 ; 1,17 ; 46 % | +8,9 [−4,0 ; +21,5] ; +0,235 [−0,013 ; +0,494] | +0,232 [−0,018 ; +0,489] | 1 089 ; 15,1 ; 11 | 26 | 36 % ; +13,9 |
| SL-A 5,0 ATR | 18 % ; 18 % | −0,075 [−0,191 ; +0,040] | +0,278 [+0,017 ; +0,556] | +93 % ; −18 % | 1,16 ; 1,19 ; 48 % | +11,0 [−1,6 ; +23,4] ; +0,286 [+0,019 ; +0,562] | +0,280 [+0,018 ; +0,551] | 1 087 ; 15,1 ; 8 | 26 | 31 % ; +16,0 |
| SL-B extremum + 0,00 ATR | 57 % ; 57 % | −0,134 [−0,306 ; +0,044] | +0,220 [+0,021 ; +0,432] | +60 % ; −16 % | 1,15 ; 1,16 ; 34 % | +8,0 [−2,7 ; +18,5] ; +0,166 [−0,036 ; +0,379] | +0,162 [−0,040 ; +0,374] | 1 160 ; 16,1 ; 102 | 20 | 38 % ; +13,0 |
| SL-B extremum + 0,25 ATR | 52 % ; 53 % | −0,182 [−0,354 ; −0,006] | +0,172 [−0,035 ; +0,398] | +45 % ; −18 % | 1,13 ; 1,13 ; 36 % | +7,6 [−3,7 ; +19,0] ; +0,133 [−0,082 ; +0,357] | +0,129 [−0,087 ; +0,356] | 1 148 ; 15,9 ; 86 | 24 | 40 % ; +12,6 |
| SL-B extremum + 0,50 ATR | 49 % ; 48 % | −0,215 [−0,374 ; −0,055] | +0,139 [−0,075 ; +0,369] | +39 % ; −18 % | 1,10 ; 1,11 ; 38 % | +6,1 [−5,4 ; +17,4] ; +0,127 [−0,092 ; +0,352] | +0,124 [−0,098 ; +0,347] | 1 136 ; 15,8 ; 72 | 26 | 45 % ; +11,1 |
| SL-B extremum + 1,00 ATR | 41 % ; 41 % | −0,238 [−0,393 ; −0,078] | +0,115 [−0,097 ; +0,350] | +22 % ; −20 % | 1,05 ; 1,07 ; 40 % | +3,1 [−8,8 ; +14,9] ; +0,092 [−0,127 ; +0,322] | +0,091 [−0,132 ; +0,326] | 1 114 ; 15,5 ; 50 | 26 | 62 % ; +8,1 |

**10 bps aller-retour**

| Stop | Figé : espérance ATR [IC] | Dyn. : PnL composé ; MDD valorisé | Dyn. : PF 1x ; PF pondéré ; WR | Dyn. : espérance bps [IC] ; ATR [IC] | Dyn. : timing ATR [IC] | Dyn. : part des frais ; brut/trade |
|---|---|---|---|---|---|---|
| Sans stop (contrôle) | +0,218 [−0,088 ; +0,510] | +60 % ; −22 % | 1,10 ; 1,14 ; 48 % | +7,3 [−6,5 ; +20,8] ; +0,218 [−0,088 ; +0,510] | +0,208 [−0,093 ; +0,492] | 58 % ; +17,3 |
| SL-A 1,0 ATR | −0,020 [−0,195 ; +0,156] | −11 % ; −33 % | 1,01 ; 0,97 ; 23 % | +0,4 [−7,9 ; +9,0] ; −0,047 [−0,217 ; +0,117] | −0,049 [−0,220 ; +0,119] | 96 % ; +10,4 |
| SL-A 1,5 ATR | +0,046 [−0,154 ; +0,261] | +9 % ; −22 % | 1,07 ; 1,04 ; 31 % | +3,6 [−6,3 ; +13,7] ; +0,015 [−0,181 ; +0,227] | +0,014 [−0,185 ; +0,226] | 73 % ; +13,6 |
| SL-A 2,0 ATR | +0,026 [−0,185 ; +0,246] | +3 % ; −27 % | 1,03 ; 1,02 ; 35 % | +2,1 [−8,8 ; +13,2] ; −0,000 [−0,213 ; +0,231] | −0,003 [−0,219 ; +0,227] | 82 % ; +12,1 |
| SL-A 2,5 ATR | −0,013 [−0,236 ; +0,225] | −5 % ; −31 % | 1,00 ; 1,00 ; 38 % | +0,3 [−11,2 ; +11,6] ; −0,025 [−0,250 ; +0,210] | −0,025 [−0,257 ; +0,209] | 97 % ; +10,3 |
| SL-A 3,0 ATR | −0,004 [−0,232 ; +0,238] | −9 % ; −33 % | 0,98 ; 0,99 ; 41 % | −1,1 [−12,7 ; +10,8] ; −0,023 [−0,250 ; +0,217] | −0,019 [−0,249 ; +0,225] | 112 % ; +8,9 |
| SL-A 4,0 ATR | +0,098 [−0,152 ; +0,361] | +25 % ; −23 % | 1,05 ; 1,07 ; 44 % | +3,9 [−9,0 ; +16,5] ; +0,099 [−0,147 ; +0,356] | +0,097 [−0,156 ; +0,354] | 72 % ; +13,9 |
| SL-A 5,0 ATR | +0,143 [−0,126 ; +0,420] | +39 % ; −24 % | 1,08 ; 1,10 ; 46 % | +6,0 [−6,6 ; +18,4] ; +0,151 [−0,117 ; +0,428] | +0,145 [−0,120 ; +0,419] | 63 % ; +16,0 |
| SL-B extremum + 0,00 ATR | +0,084 [−0,122 ; +0,297] | +13 % ; −23 % | 1,05 ; 1,05 ; 33 % | +3,0 [−7,7 ; +13,5] ; +0,031 [−0,179 ; +0,252] | +0,027 [−0,181 ; +0,247] | 77 % ; +13,0 |
| SL-B extremum + 0,25 ATR | +0,036 [−0,175 ; +0,263] | +3 % ; −29 % | 1,04 ; 1,02 ; 35 % | +2,6 [−8,7 ; +14,0] ; −0,002 [−0,221 ; +0,227] | −0,006 [−0,229 ; +0,223] | 79 % ; +12,6 |
| SL-B extremum + 0,50 ATR | +0,003 [−0,212 ; +0,234] | −1 % ; −26 % | 1,02 ; 1,01 ; 37 % | +1,1 [−10,4 ; +12,4] ; −0,007 [−0,229 ; +0,225] | −0,010 [−0,239 ; +0,223] | 90 % ; +11,1 |
| SL-B extremum + 1,00 ATR | −0,020 [−0,238 ; +0,214] | −13 % ; −35 % | 0,97 ; 0,98 ; 39 % | −1,9 [−13,8 ; +9,9] ; −0,043 [−0,264 ; +0,194] | −0,043 [−0,267 ; +0,194] | 124 % ; +8,1 |

#### R2 hors nis_z_100 Q4 — H = 48

**5 bps aller-retour**

| Stop | Stoppés : figé ; dyn. | Effet pur, entrées figées : ATR [IC 95 %] | Figé : espérance ATR [IC] | Dyn. : PnL composé ; MDD valorisé | Dyn. : PF 1x ; PF pondéré ; WR | Dyn. : espérance bps [IC] ; ATR [IC] | Dyn. : timing ATR [IC] | Dyn. : trades ; /mois ; débloqués | Dyn. : durée méd. | Dyn. : part des frais ; brut/trade |
|---|---|---|---|---|---|---|---|---|---|---|
| Sans stop (contrôle) | 0 % ; 0 % | — | +0,071 [−0,381 ; +0,508] | −5 % ; −37 % | 0,97 ; 1,01 ; 47 % | −2,9 [−21,5 ; +16,3] ; +0,071 [−0,381 ; +0,508] | +0,055 [−0,379 ; +0,479] | 864 ; 12,0 ; 0 | 48 | 238 % ; +2,1 |
| SL-A 1,0 ATR | 82 % ; 81 % | −0,019 [−0,397 ; +0,365] | +0,052 [−0,164 ; +0,279] | +33 % ; −17 % | 1,05 ; 1,12 ; 19 % | +2,4 [−6,1 ; +11,4] ; +0,126 [−0,069 ; +0,338] | +0,122 [−0,073 ; +0,332] | 1 214 ; 16,9 ; 383 | 8 | 67 % ; +7,4 |
| SL-A 1,5 ATR | 73 % ; 73 % | +0,037 [−0,292 ; +0,386] | +0,108 [−0,145 ; +0,371] | +32 % ; −22 % | 1,01 ; 1,10 ; 25 % | +0,5 [−11,0 ; +12,0] ; +0,134 [−0,098 ; +0,375] | +0,130 [−0,101 ; +0,370] | 1 102 ; 15,3 ; 273 | 14 | 91 % ; +5,5 |
| SL-A 2,0 ATR | 66 % ; 65 % | +0,006 [−0,296 ; +0,329] | +0,077 [−0,191 ; +0,355] | +12 % ; −22 % | 0,96 ; 1,05 ; 29 % | −2,7 [−15,2 ; +9,6] ; +0,090 [−0,172 ; +0,371] | +0,084 [−0,179 ; +0,365] | 1 018 ; 14,1 ; 187 | 23 | 213 % ; +2,3 |
| SL-A 2,5 ATR | 60 % ; 59 % | −0,111 [−0,402 ; +0,198] | −0,040 [−0,316 ; +0,250] | −4 % ; −29 % | 0,91 ; 1,00 ; 33 % | −7,5 [−20,9 ; +5,2] ; +0,028 [−0,257 ; +0,319] | +0,023 [−0,261 ; +0,314] | 981 ; 13,6 ; 151 | 32 | sans objet (brut ≤ 0) ; −2,5 |
| SL-A 3,0 ATR | 53 % ; 52 % | −0,055 [−0,338 ; +0,263] | +0,016 [−0,274 ; +0,317] | +7 % ; −32 % | 0,93 ; 1,03 ; 37 % | −5,8 [−19,9 ; +8,5] ; +0,099 [−0,199 ; +0,404] | +0,094 [−0,203 ; +0,399] | 952 ; 13,2 ; 113 | 44 | sans objet (brut ≤ 0) ; −0,8 |
| SL-A 4,0 ATR | 41 % ; 40 % | +0,034 [−0,235 ; +0,320] | +0,105 [−0,241 ; +0,464] | +29 % ; −33 % | 0,98 ; 1,08 ; 42 % | −1,5 [−17,7 ; +14,4] ; +0,182 [−0,160 ; +0,527] | +0,185 [−0,154 ; +0,537] | 919 ; 12,8 ; 78 | 48 | 141 % ; +3,5 |
| SL-A 5,0 ATR | 30 % ; 29 % | +0,111 [−0,131 ; +0,381] | +0,182 [−0,168 ; +0,550] | +51 % ; −26 % | 1,05 ; 1,12 ; 45 % | +4,5 [−11,8 ; +21,4] ; +0,261 [−0,093 ; +0,634] | +0,253 [−0,091 ; +0,619] | 901 ; 12,5 ; 55 | 48 | 53 % ; +9,5 |
| SL-B extremum + 0,00 ATR | 68 % ; 68 % | +0,059 [−0,234 ; +0,377] | +0,130 [−0,134 ; +0,415] | +34 % ; −26 % | 0,98 ; 1,10 ; 27 % | −1,1 [−13,2 ; +11,0] ; +0,183 [−0,091 ; +0,472] | +0,170 [−0,094 ; +0,453] | 1 040 ; 14,4 ; 208 | 20 | 129 % ; +3,9 |
| SL-B extremum + 0,25 ATR | 66 % ; 65 % | −0,009 [−0,311 ; +0,322] | +0,062 [−0,206 ; +0,352] | +19 % ; −25 % | 0,96 ; 1,07 ; 29 % | −2,9 [−15,6 ; +9,5] ; +0,144 [−0,143 ; +0,447] | +0,136 [−0,144 ; +0,429] | 1 016 ; 14,1 ; 185 | 24 | 236 % ; +2,1 |
| SL-B extremum + 0,50 ATR | 63 % ; 62 % | −0,047 [−0,337 ; +0,273] | +0,024 [−0,261 ; +0,318] | +11 % ; −28 % | 0,94 ; 1,04 ; 31 % | −5,1 [−18,8 ; +8,0] ; +0,111 [−0,181 ; +0,427] | +0,104 [−0,185 ; +0,412] | 993 ; 13,8 ; 162 | 27 | sans objet (brut ≤ 0) ; −0,1 |
| SL-B extremum + 1,00 ATR | 56 % ; 55 % | −0,078 [−0,357 ; +0,230] | −0,007 [−0,280 ; +0,280] | +2 % ; −31 % | 0,92 ; 1,02 ; 35 % | −7,0 [−20,6 ; +6,4] ; +0,074 [−0,210 ; +0,359] | +0,068 [−0,213 ; +0,352] | 966 ; 13,4 ; 132 | 39 | sans objet (brut ≤ 0) ; −2,0 |

**10 bps aller-retour**

| Stop | Figé : espérance ATR [IC] | Dyn. : PnL composé ; MDD valorisé | Dyn. : PF 1x ; PF pondéré ; WR | Dyn. : espérance bps [IC] ; ATR [IC] | Dyn. : timing ATR [IC] | Dyn. : part des frais ; brut/trade |
|---|---|---|---|---|---|---|
| Sans stop (contrôle) | −0,064 [−0,512 ; +0,372] | −27 % ; −45 % | 0,93 ; 0,95 ; 46 % | −7,9 [−26,5 ; +11,3] ; −0,064 [−0,512 ; +0,372] | −0,079 [−0,515 ; +0,348] | 475 % ; +2,1 |
| SL-A 1,0 ATR | −0,083 [−0,294 ; +0,146] | −8 % ; −30 % | 0,95 ; 0,98 ; 19 % | −2,6 [−11,1 ; +6,4] ; −0,013 [−0,208 ; +0,199] | −0,016 [−0,214 ; +0,196] | 134 % ; +7,4 |
| SL-A 1,5 ATR | −0,027 [−0,273 ; +0,236] | −5 % ; −27 % | 0,93 ; 1,00 ; 25 % | −4,5 [−16,0 ; +7,0] ; −0,003 [−0,235 ; +0,237] | −0,007 [−0,234 ; +0,235] | 181 % ; +5,5 |
| SL-A 2,0 ATR | −0,058 [−0,329 ; +0,221] | −17 % ; −31 % | 0,90 ; 0,96 ; 29 % | −7,7 [−20,2 ; +4,6] ; −0,044 [−0,307 ; +0,239] | −0,050 [−0,317 ; +0,234] | 426 % ; +2,3 |
| SL-A 2,5 ATR | −0,175 [−0,452 ; +0,116] | −28 % ; −43 % | 0,86 ; 0,93 ; 32 % | −12,5 [−25,9 ; +0,2] ; −0,105 [−0,389 ; +0,180] | −0,111 [−0,392 ; +0,177] | sans objet (brut ≤ 0) ; −2,5 |
| SL-A 3,0 ATR | −0,119 [−0,408 ; +0,188] | −19 % ; −40 % | 0,88 ; 0,96 ; 36 % | −10,8 [−24,9 ; +3,5] ; −0,034 [−0,336 ; +0,273] | −0,039 [−0,337 ; +0,265] | sans objet (brut ≤ 0) ; −0,8 |
| SL-A 4,0 ATR | −0,030 [−0,373 ; +0,328] | −2 % ; −35 % | 0,93 ; 1,01 ; 40 % | −6,5 [−22,7 ; +9,4] ; +0,049 [−0,292 ; +0,393] | +0,052 [−0,287 ; +0,409] | 282 % ; +3,5 |
| SL-A 5,0 ATR | +0,048 [−0,305 ; +0,416] | +16 % ; −29 % | 0,99 ; 1,05 ; 44 % | −0,5 [−16,8 ; +16,4] ; +0,127 [−0,227 ; +0,502] | +0,119 [−0,221 ; +0,493] | 105 % ; +9,5 |
| SL-B extremum + 0,00 ATR | −0,004 [−0,269 ; +0,279] | −2 % ; −28 % | 0,91 ; 1,01 ; 27 % | −6,1 [−18,2 ; +6,0] ; +0,047 [−0,223 ; +0,339] | +0,035 [−0,230 ; +0,318] | 258 % ; +3,9 |
| SL-B extremum + 0,25 ATR | −0,073 [−0,343 ; +0,218] | −12 % ; −30 % | 0,90 ; 0,98 ; 29 % | −7,9 [−20,6 ; +4,5] ; +0,009 [−0,280 ; +0,311] | +0,001 [−0,282 ; +0,294] | 472 % ; +2,1 |
| SL-B extremum + 0,50 ATR | −0,111 [−0,390 ; +0,184] | −17 % ; −31 % | 0,88 ; 0,96 ; 31 % | −10,1 [−23,8 ; +3,0] ; −0,023 [−0,311 ; +0,292] | −0,029 [−0,317 ; +0,278] | sans objet (brut ≤ 0) ; −0,1 |
| SL-B extremum + 1,00 ATR | −0,141 [−0,412 ; +0,143] | −24 % ; −41 % | 0,86 ; 0,95 ; 34 % | −12,0 [−25,6 ; +1,4] ; −0,059 [−0,339 ; +0,227] | −0,064 [−0,344 ; +0,220] | sans objet (brut ≤ 0) ; −2,0 |

## E. Entrées figées contre séquentiel dynamique (5 bps, horizon principal du groupe)

Débloqués : trades ouverts grâce à un stop, absents de la course figée. Perdus : trades de la course figée masqués par un trade débloqué. Espérances nettes en ATR14(t).

### R1 hors nis_z_100 Q4 — H = 13

| Stop | Trades figés | Trades dyn. | Débloqués : n ; esp. ATR | Perdus : n ; esp. ATR | Esp. ATR figé | Esp. ATR dyn. | Figé : PnL ; MDD | Dyn. : PnL ; MDD |
|---|---|---|---|---|---|---|---|---|
| SL-A 1,0 ATR | 1 501 | 1 536 | 36 ; +0,130 | 1 ; +2,317 | −0,019 | −0,017 | −11 % ; −27 % | −10 % ; −28 % |
| SL-A 1,5 ATR | 1 501 | 1 523 | 23 ; +0,264 | 1 ; +2,317 | −0,003 | −0,000 | −5 % ; −22 % | −3 % ; −22 % |
| SL-A 2,0 ATR | 1 501 | 1 513 | 13 ; +0,409 | 1 ; +2,317 | +0,011 | +0,013 | +1 % ; −20 % | +2 % ; −22 % |
| SL-A 2,5 ATR | 1 501 | 1 508 | 7 ; −1,211 | 0 ; — | +0,013 | +0,007 | +2 % ; −19 % | +1 % ; −20 % |
| SL-A 3,0 ATR | 1 501 | 1 505 | 4 ; +0,044 | 0 ; — | +0,005 | +0,006 | +0 % ; −19 % | +0 % ; −19 % |
| SL-A 4,0 ATR | 1 501 | 1 504 | 3 ; −0,481 | 0 ; — | +0,002 | +0,001 | −0 % ; −19 % | −0 % ; −19 % |
| SL-A 5,0 ATR | 1 501 | 1 501 | 0 ; — | 0 ; — | +0,009 | +0,009 | +2 % ; −19 % | +2 % ; −19 % |
| SL-B extremum + 0,00 ATR | 1 501 | 1 532 | 32 ; +0,324 | 1 ; +2,317 | −0,019 | −0,014 | −10 % ; −28 % | −8 % ; −29 % |
| SL-B extremum + 0,25 ATR | 1 501 | 1 524 | 24 ; −0,194 | 1 ; +2,317 | −0,066 | −0,070 | −25 % ; −34 % | −26 % ; −35 % |
| SL-B extremum + 0,50 ATR | 1 501 | 1 519 | 19 ; −0,300 | 1 ; +2,317 | −0,045 | −0,050 | −19 % ; −29 % | −20 % ; −30 % |
| SL-B extremum + 1,00 ATR | 1 501 | 1 513 | 13 ; −0,581 | 1 ; +2,317 | −0,002 | −0,009 | −4 % ; −21 % | −6 % ; −22 % |

### ↳ F1 · x1 encore opposé hors nis_z_100 Q4 — H = 13

| Stop | Trades figés | Trades dyn. | Débloqués : n ; esp. ATR | Perdus : n ; esp. ATR | Esp. ATR figé | Esp. ATR dyn. | Figé : PnL ; MDD | Dyn. : PnL ; MDD |
|---|---|---|---|---|---|---|---|---|
| SL-A 1,0 ATR | 950 | 958 | 8 ; +1,863 | 0 ; — | +0,008 | +0,024 | −3 % ; −22 % | +1 % ; −22 % |
| SL-A 1,5 ATR | 950 | 958 | 8 ; +2,281 | 0 ; — | +0,041 | +0,059 | +5 % ; −16 % | +10 % ; −17 % |
| SL-A 2,0 ATR | 950 | 955 | 5 ; +2,950 | 0 ; — | +0,047 | +0,062 | +7 % ; −15 % | +11 % ; −15 % |
| SL-A 2,5 ATR | 950 | 951 | 1 ; −0,888 | 0 ; — | +0,048 | +0,047 | +7 % ; −16 % | +7 % ; −16 % |
| SL-A 3,0 ATR | 950 | 951 | 1 ; −0,888 | 0 ; — | +0,032 | +0,031 | +4 % ; −16 % | +4 % ; −16 % |
| SL-A 4,0 ATR | 950 | 951 | 1 ; −0,888 | 0 ; — | +0,046 | +0,046 | +8 % ; −16 % | +8 % ; −16 % |
| SL-A 5,0 ATR | 950 | 950 | 0 ; — | 0 ; — | +0,034 | +0,034 | +5 % ; −17 % | +5 % ; −17 % |
| SL-B extremum + 0,00 ATR | 950 | 958 | 8 ; +2,343 | 0 ; — | −0,004 | +0,016 | −5 % ; −26 % | −0 % ; −26 % |
| SL-B extremum + 0,25 ATR | 950 | 957 | 7 ; +0,872 | 0 ; — | −0,058 | −0,051 | −17 % ; −29 % | −15 % ; −29 % |
| SL-B extremum + 0,50 ATR | 950 | 957 | 7 ; +0,800 | 0 ; — | −0,021 | −0,015 | −9 % ; −25 % | −8 % ; −25 % |
| SL-B extremum + 1,00 ATR | 950 | 955 | 5 ; +0,443 | 0 ; — | +0,051 | +0,053 | +8 % ; −17 % | +8 % ; −17 % |

### ↳ F5 · x1 encore opposé hors nis_z_100 Q4 — H = 13

| Stop | Trades figés | Trades dyn. | Débloqués : n ; esp. ATR | Perdus : n ; esp. ATR | Esp. ATR figé | Esp. ATR dyn. | Figé : PnL ; MDD | Dyn. : PnL ; MDD |
|---|---|---|---|---|---|---|---|---|
| SL-A 1,0 ATR | 604 | 609 | 5 ; +0,094 | 0 ; — | −0,112 | −0,110 | −15 % ; −22 % | −14 % ; −21 % |
| SL-A 1,5 ATR | 604 | 606 | 2 ; −0,389 | 0 ; — | −0,124 | −0,125 | −16 % ; −24 % | −16 % ; −24 % |
| SL-A 2,0 ATR | 604 | 606 | 2 ; −0,639 | 0 ; — | −0,111 | −0,113 | −14 % ; −20 % | −13 % ; −20 % |
| SL-A 2,5 ATR | 604 | 606 | 2 ; −0,889 | 0 ; — | −0,103 | −0,105 | −13 % ; −22 % | −12 % ; −22 % |
| SL-A 3,0 ATR | 604 | 605 | 1 ; +1,618 | 0 ; — | −0,079 | −0,076 | −10 % ; −22 % | −9 % ; −22 % |
| SL-A 4,0 ATR | 604 | 604 | 0 ; — | 0 ; — | −0,106 | −0,106 | −13 % ; −24 % | −13 % ; −24 % |
| SL-A 5,0 ATR | 604 | 604 | 0 ; — | 0 ; — | −0,068 | −0,068 | −8 % ; −22 % | −8 % ; −22 % |
| SL-B extremum + 0,00 ATR | 604 | 610 | 6 ; −0,294 | 0 ; — | −0,075 | −0,077 | −10 % ; −18 % | −10 % ; −18 % |
| SL-B extremum + 0,25 ATR | 604 | 608 | 4 ; −0,128 | 0 ; — | −0,119 | −0,119 | −16 % ; −23 % | −16 % ; −23 % |
| SL-B extremum + 0,50 ATR | 604 | 606 | 2 ; −0,348 | 0 ; — | −0,139 | −0,140 | −18 % ; −25 % | −18 % ; −25 % |
| SL-B extremum + 1,00 ATR | 604 | 606 | 2 ; −0,598 | 0 ; — | −0,138 | −0,140 | −17 % ; −24 % | −17 % ; −24 % |

### ↳ F2b · x1 déjà retourné hors nis_z_100 Q4 — H = 26

| Stop | Trades figés | Trades dyn. | Débloqués : n ; esp. ATR | Perdus : n ; esp. ATR | Esp. ATR figé | Esp. ATR dyn. | Figé : PnL ; MDD | Dyn. : PnL ; MDD |
|---|---|---|---|---|---|---|---|---|
| SL-A 1,0 ATR | 639 | 684 | 48 ; +0,176 | 3 ; −1,247 | +0,118 | +0,128 | +18 % ; −16 % | +21 % ; −14 % |
| SL-A 1,5 ATR | 639 | 667 | 30 ; +0,379 | 2 ; −1,616 | +0,138 | +0,154 | +22 % ; −14 % | +27 % ; −12 % |
| SL-A 2,0 ATR | 639 | 656 | 19 ; +0,230 | 2 ; −2,116 | +0,057 | +0,069 | +8 % ; −19 % | +10 % ; −16 % |
| SL-A 2,5 ATR | 639 | 651 | 12 ; +0,390 | 0 ; — | +0,011 | +0,018 | +1 % ; −23 % | +3 % ; −21 % |
| SL-A 3,0 ATR | 639 | 645 | 6 ; +0,375 | 0 ; — | +0,041 | +0,044 | +4 % ; −22 % | +5 % ; −22 % |
| SL-A 4,0 ATR | 639 | 641 | 2 ; +2,696 | 0 ; — | +0,166 | +0,173 | +24 % ; −14 % | +26 % ; −13 % |
| SL-A 5,0 ATR | 639 | 640 | 1 ; +3,684 | 0 ; — | +0,239 | +0,244 | +37 % ; −13 % | +38 % ; −13 % |
| SL-B extremum + 0,00 ATR | 639 | 666 | 30 ; −0,106 | 3 ; −1,826 | +0,110 | +0,109 | +17 % ; −17 % | +18 % ; −15 % |
| SL-B extremum + 0,25 ATR | 639 | 661 | 24 ; +0,029 | 2 ; −1,784 | +0,066 | +0,070 | +10 % ; −18 % | +11 % ; −18 % |
| SL-B extremum + 0,50 ATR | 639 | 655 | 18 ; +0,182 | 2 ; −2,034 | +0,061 | +0,071 | +9 % ; −18 % | +11 % ; −15 % |
| SL-B extremum + 1,00 ATR | 639 | 649 | 11 ; −0,384 | 1 ; −2,227 | +0,048 | +0,044 | +5 % ; −21 % | +5 % ; −20 % |

### ↳ F3 · x1 déjà retourné hors nis_z_100 Q4 — H = 26

| Stop | Trades figés | Trades dyn. | Débloqués : n ; esp. ATR | Perdus : n ; esp. ATR | Esp. ATR figé | Esp. ATR dyn. | Figé : PnL ; MDD | Dyn. : PnL ; MDD |
|---|---|---|---|---|---|---|---|---|
| SL-A 1,0 ATR | 601 | 678 | 81 ; −0,200 | 4 ; −1,241 | +0,097 | +0,069 | +15 % ; −11 % | +13 % ; −12 % |
| SL-A 1,5 ATR | 601 | 652 | 56 ; −0,701 | 5 ; −1,233 | +0,216 | +0,149 | +37 % ; −11 % | +29 % ; −12 % |
| SL-A 2,0 ATR | 601 | 627 | 31 ; −0,958 | 5 ; −1,250 | +0,233 | +0,186 | +41 % ; −12 % | +33 % ; −14 % |
| SL-A 2,5 ATR | 601 | 616 | 20 ; −0,903 | 5 ; −0,455 | +0,148 | +0,118 | +25 % ; −13 % | +20 % ; −14 % |
| SL-A 3,0 ATR | 601 | 612 | 15 ; −0,958 | 4 ; −0,524 | +0,085 | +0,064 | +12 % ; −19 % | +9 % ; −20 % |
| SL-A 4,0 ATR | 601 | 602 | 1 ; −0,895 | 0 ; — | +0,175 | +0,173 | +26 % ; −16 % | +26 % ; −16 % |
| SL-A 5,0 ATR | 601 | 602 | 1 ; −0,895 | 0 ; — | +0,202 | +0,200 | +30 % ; −21 % | +30 % ; −21 % |
| SL-B extremum + 0,00 ATR | 601 | 620 | 23 ; −0,887 | 4 ; −0,969 | +0,236 | +0,202 | +41 % ; −13 % | +36 % ; −13 % |
| SL-B extremum + 0,25 ATR | 601 | 617 | 20 ; −0,995 | 4 ; −0,325 | +0,192 | +0,157 | +33 % ; −13 % | +27 % ; −13 % |
| SL-B extremum + 0,50 ATR | 601 | 615 | 18 ; −0,909 | 4 ; −0,387 | +0,143 | +0,116 | +24 % ; −13 % | +20 % ; −13 % |
| SL-B extremum + 1,00 ATR | 601 | 611 | 14 ; −0,852 | 4 ; −0,512 | +0,073 | +0,056 | +10 % ; −20 % | +8 % ; −20 % |

### R2 hors nis_z_100 Q4 — H = 26

| Stop | Trades figés | Trades dyn. | Débloqués : n ; esp. ATR | Perdus : n ; esp. ATR | Esp. ATR figé | Esp. ATR dyn. | Figé : PnL ; MDD | Dyn. : PnL ; MDD |
|---|---|---|---|---|---|---|---|---|
| SL-A 1,0 ATR | 1 080 | 1 310 | 244 ; −0,040 | 14 ; −0,253 | +0,116 | +0,091 | +32 % ; −12 % | +32 % ; −16 % |
| SL-A 1,5 ATR | 1 080 | 1 210 | 148 ; +0,031 | 18 ; +0,902 | +0,181 | +0,152 | +58 % ; −14 % | +57 % ; −15 % |
| SL-A 2,0 ATR | 1 080 | 1 145 | 83 ; −0,157 | 18 ; +0,419 | +0,161 | +0,134 | +51 % ; −17 % | +45 % ; −17 % |
| SL-A 2,5 ATR | 1 080 | 1 123 | 56 ; +0,135 | 13 ; +1,375 | +0,123 | +0,109 | +36 % ; −17 % | +32 % ; −17 % |
| SL-A 3,0 ATR | 1 080 | 1 104 | 34 ; −0,159 | 10 ; +1,386 | +0,132 | +0,112 | +35 % ; −17 % | +27 % ; −20 % |
| SL-A 4,0 ATR | 1 080 | 1 089 | 11 ; +0,880 | 2 ; +3,326 | +0,234 | +0,235 | +72 % ; −17 % | +73 % ; −16 % |
| SL-A 5,0 ATR | 1 080 | 1 087 | 8 ; +1,496 | 1 ; +1,769 | +0,278 | +0,286 | +88 % ; −18 % | +93 % ; −18 % |
| SL-B extremum + 0,00 ATR | 1 080 | 1 160 | 102 ; −0,351 | 22 ; +0,387 | +0,220 | +0,166 | +73 % ; −15 % | +60 % ; −16 % |
| SL-B extremum + 0,25 ATR | 1 080 | 1 148 | 86 ; −0,114 | 18 ; +1,285 | +0,172 | +0,133 | +54 % ; −16 % | +45 % ; −18 % |
| SL-B extremum + 0,50 ATR | 1 080 | 1 136 | 72 ; +0,086 | 16 ; +0,731 | +0,139 | +0,127 | +41 % ; −18 % | +39 % ; −18 % |
| SL-B extremum + 1,00 ATR | 1 080 | 1 114 | 50 ; +0,021 | 16 ; +1,463 | +0,115 | +0,092 | +29 % ; −22 % | +22 % ; −20 % |

## F. Stabilité annuelle (séquentiel dynamique, 5 bps, horizon principal du groupe)

Cellule : espérance nette par trade en ATR14(t) (trades). Dernière colonne : années à PnL > 0 à 0,25 % par ATR.

### R1 hors nis_z_100 Q4 — H = 13

| Stop | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 | Années > 0 |
|---|---|---|---|---|---|---|---|
| Sans stop (contrôle) | +0,09 (251) | +0,05 (238) | −0,15 (249) | −0,02 (237) | −0,03 (255) | −0,20 (271) | 2/6 |
| SL-A 1,0 ATR | +0,06 (259) | −0,07 (245) | +0,13 (255) | +0,16 (243) | −0,27 (262) | −0,10 (272) | 3/6 |
| SL-A 1,5 ATR | +0,01 (255) | −0,01 (240) | +0,18 (254) | +0,05 (242) | −0,15 (260) | −0,07 (272) | 3/6 |
| SL-A 2,0 ATR | −0,03 (251) | +0,02 (239) | +0,24 (252) | +0,06 (241) | −0,10 (258) | −0,10 (272) | 3/6 |
| SL-A 2,5 ATR | +0,02 (251) | −0,05 (239) | +0,14 (249) | +0,05 (240) | −0,08 (257) | −0,04 (272) | 3/6 |
| SL-A 3,0 ATR | +0,02 (251) | −0,03 (239) | +0,09 (249) | +0,04 (238) | −0,07 (256) | −0,02 (272) | 3/6 |
| SL-A 4,0 ATR | +0,06 (251) | −0,02 (239) | +0,03 (249) | +0,03 (238) | −0,08 (256) | −0,02 (271) | 3/6 |
| SL-A 5,0 ATR | +0,10 (251) | +0,01 (238) | +0,05 (249) | +0,04 (237) | −0,04 (255) | −0,09 (271) | 4/6 |
| SL-B extremum + 0,00 ATR | +0,06 (256) | −0,03 (244) | +0,15 (255) | +0,12 (243) | −0,23 (262) | −0,13 (272) | 3/6 |
| SL-B extremum + 0,25 ATR | +0,03 (254) | −0,12 (243) | +0,11 (254) | +0,07 (242) | −0,32 (259) | −0,17 (272) | 3/6 |
| SL-B extremum + 0,50 ATR | +0,04 (252) | −0,11 (242) | +0,14 (253) | +0,03 (242) | −0,25 (258) | −0,13 (272) | 2/6 |
| SL-B extremum + 1,00 ATR | −0,08 (251) | −0,05 (239) | +0,15 (251) | +0,12 (242) | −0,08 (258) | −0,10 (272) | 2/6 |

### ↳ F1 · x1 encore opposé hors nis_z_100 Q4 — H = 13

| Stop | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 | Années > 0 |
|---|---|---|---|---|---|---|---|
| Sans stop (contrôle) | −0,09 (151) | −0,07 (157) | −0,14 (165) | +0,41 (138) | −0,01 (167) | −0,16 (172) | 2/6 |
| SL-A 1,0 ATR | −0,01 (151) | −0,04 (159) | +0,24 (169) | +0,49 (139) | −0,30 (168) | −0,15 (172) | 2/6 |
| SL-A 1,5 ATR | −0,09 (151) | +0,02 (159) | +0,32 (169) | +0,40 (139) | −0,13 (168) | −0,12 (172) | 3/6 |
| SL-A 2,0 ATR | −0,12 (151) | −0,02 (158) | +0,27 (168) | +0,55 (138) | −0,08 (168) | −0,17 (172) | 2/6 |
| SL-A 2,5 ATR | −0,12 (151) | −0,09 (158) | +0,16 (165) | +0,56 (138) | −0,02 (167) | −0,13 (172) | 2/6 |
| SL-A 3,0 ATR | −0,11 (151) | −0,12 (158) | +0,11 (165) | +0,51 (138) | −0,03 (167) | −0,12 (172) | 2/6 |
| SL-A 4,0 ATR | −0,06 (151) | −0,11 (158) | +0,09 (165) | +0,50 (138) | −0,02 (167) | −0,06 (172) | 2/6 |
| SL-A 5,0 ATR | −0,05 (151) | −0,12 (157) | +0,04 (165) | +0,52 (138) | +0,01 (167) | −0,12 (172) | 3/6 |
| SL-B extremum + 0,00 ATR | −0,02 (151) | −0,02 (159) | +0,32 (169) | +0,44 (139) | −0,32 (168) | −0,23 (172) | 2/6 |
| SL-B extremum + 0,25 ATR | −0,07 (151) | −0,12 (159) | +0,21 (168) | +0,40 (139) | −0,36 (168) | −0,28 (172) | 2/6 |
| SL-B extremum + 0,50 ATR | −0,08 (151) | −0,08 (159) | +0,18 (168) | +0,37 (139) | −0,26 (168) | −0,18 (172) | 2/6 |
| SL-B extremum + 1,00 ATR | −0,19 (151) | −0,05 (158) | +0,21 (167) | +0,59 (139) | −0,01 (168) | −0,17 (172) | 2/6 |

### ↳ F5 · x1 encore opposé hors nis_z_100 Q4 — H = 13

| Stop | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 | Années > 0 |
|---|---|---|---|---|---|---|---|
| Sans stop (contrôle) | +0,37 (108) | +0,19 (90) | −0,20 (92) | −0,59 (107) | −0,11 (105) | −0,28 (102) | 2/6 |
| SL-A 1,0 ATR | +0,19 (110) | −0,12 (91) | −0,14 (92) | −0,29 (108) | −0,29 (105) | −0,02 (103) | 1/6 |
| SL-A 1,5 ATR | +0,20 (108) | −0,10 (90) | −0,19 (92) | −0,42 (108) | −0,23 (105) | −0,01 (103) | 1/6 |
| SL-A 2,0 ATR | +0,11 (108) | +0,01 (90) | +0,06 (92) | −0,59 (108) | −0,21 (105) | −0,01 (103) | 3/6 |
| SL-A 2,5 ATR | +0,24 (108) | −0,04 (90) | +0,00 (92) | −0,66 (108) | −0,18 (105) | +0,04 (103) | 2/6 |
| SL-A 3,0 ATR | +0,23 (108) | +0,04 (90) | −0,03 (92) | −0,64 (107) | −0,14 (105) | +0,11 (103) | 3/6 |
| SL-A 4,0 ATR | +0,25 (108) | +0,10 (90) | −0,17 (92) | −0,61 (107) | −0,20 (105) | +0,02 (102) | 3/6 |
| SL-A 5,0 ATR | +0,33 (108) | +0,18 (90) | −0,05 (92) | −0,59 (107) | −0,17 (105) | −0,07 (102) | 2/6 |
| SL-B extremum + 0,00 ATR | +0,20 (110) | −0,04 (91) | −0,22 (93) | −0,30 (108) | −0,15 (105) | +0,04 (103) | 2/6 |
| SL-B extremum + 0,25 ATR | +0,23 (109) | −0,13 (90) | −0,15 (93) | −0,36 (108) | −0,30 (105) | −0,01 (103) | 1/6 |
| SL-B extremum + 0,50 ATR | +0,23 (108) | −0,20 (90) | −0,04 (92) | −0,43 (108) | −0,32 (105) | −0,07 (103) | 1/6 |
| SL-B extremum + 1,00 ATR | +0,10 (108) | −0,10 (90) | −0,09 (92) | −0,53 (108) | −0,19 (105) | −0,02 (103) | 1/6 |

### ↳ F2b · x1 déjà retourné hors nis_z_100 Q4 — H = 26

| Stop | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 | Années > 0 |
|---|---|---|---|---|---|---|---|
| Sans stop (contrôle) | +0,69 (122) | −0,15 (119) | +0,13 (102) | +0,61 (110) | +0,52 (95) | +0,57 (91) | 5/6 |
| SL-A 1,0 ATR | +0,45 (136) | −0,16 (126) | −0,08 (110) | +0,01 (115) | +0,09 (101) | +0,48 (96) | 3/6 |
| SL-A 1,5 ATR | +0,61 (131) | −0,18 (125) | −0,07 (107) | +0,14 (112) | +0,06 (99) | +0,34 (93) | 4/6 |
| SL-A 2,0 ATR | +0,60 (130) | −0,25 (123) | −0,15 (105) | +0,05 (110) | −0,01 (97) | +0,09 (91) | 4/6 |
| SL-A 2,5 ATR | +0,61 (126) | −0,08 (122) | −0,23 (105) | −0,10 (110) | −0,19 (97) | −0,02 (91) | 1/6 |
| SL-A 3,0 ATR | +0,72 (124) | −0,02 (120) | +0,01 (104) | −0,22 (110) | −0,19 (96) | −0,20 (91) | 1/6 |
| SL-A 4,0 ATR | +0,79 (123) | +0,01 (120) | +0,01 (102) | −0,06 (110) | +0,11 (95) | +0,10 (91) | 2/6 |
| SL-A 5,0 ATR | +0,83 (122) | −0,01 (120) | +0,09 (102) | +0,21 (110) | −0,02 (95) | +0,29 (91) | 5/6 |
| SL-B extremum + 0,00 ATR | +0,72 (131) | −0,26 (125) | −0,12 (107) | +0,08 (110) | −0,01 (101) | +0,17 (92) | 4/6 |
| SL-B extremum + 0,25 ATR | +0,73 (128) | −0,13 (125) | −0,20 (107) | −0,03 (110) | −0,14 (100) | +0,08 (91) | 2/6 |
| SL-B extremum + 0,50 ATR | +0,67 (127) | −0,14 (124) | −0,19 (106) | +0,06 (110) | −0,14 (97) | +0,06 (91) | 3/6 |
| SL-B extremum + 1,00 ATR | +0,65 (125) | −0,08 (121) | −0,03 (105) | −0,10 (110) | −0,20 (97) | −0,11 (91) | 1/6 |

### ↳ F3 · x1 déjà retourné hors nis_z_100 Q4 — H = 26

| Stop | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 | Années > 0 |
|---|---|---|---|---|---|---|---|
| Sans stop (contrôle) | +0,59 (92) | +0,59 (105) | +0,04 (94) | −0,22 (108) | −1,00 (99) | +0,86 (103) | 3/6 |
| SL-A 1,0 ATR | +0,26 (101) | +0,33 (117) | −0,19 (109) | −0,02 (124) | +0,02 (114) | +0,02 (113) | 3/6 |
| SL-A 1,5 ATR | +0,35 (97) | +0,33 (110) | +0,01 (104) | −0,04 (120) | −0,11 (112) | +0,39 (109) | 5/6 |
| SL-A 2,0 ATR | +0,32 (94) | +0,35 (110) | +0,15 (101) | −0,04 (113) | +0,04 (103) | +0,31 (106) | 6/6 |
| SL-A 2,5 ATR | +0,39 (93) | +0,21 (108) | −0,02 (98) | +0,03 (112) | −0,14 (101) | +0,26 (104) | 4/6 |
| SL-A 3,0 ATR | +0,30 (93) | +0,06 (108) | −0,02 (97) | −0,13 (111) | −0,30 (100) | +0,50 (103) | 3/6 |
| SL-A 4,0 ATR | +0,43 (92) | +0,17 (105) | +0,08 (94) | +0,01 (108) | −0,25 (100) | +0,62 (103) | 5/6 |
| SL-A 5,0 ATR | +0,59 (92) | +0,21 (105) | +0,02 (94) | +0,02 (108) | −0,42 (100) | +0,80 (103) | 4/6 |
| SL-B extremum + 0,00 ATR | +0,41 (94) | +0,25 (109) | +0,14 (98) | +0,08 (114) | +0,03 (100) | +0,32 (105) | 6/6 |
| SL-B extremum + 0,25 ATR | +0,41 (93) | +0,24 (108) | +0,11 (97) | +0,01 (114) | −0,08 (100) | +0,27 (105) | 5/6 |
| SL-B extremum + 0,50 ATR | +0,34 (93) | +0,17 (108) | +0,00 (97) | +0,06 (112) | −0,18 (100) | +0,31 (105) | 5/6 |
| SL-B extremum + 1,00 ATR | +0,32 (93) | +0,03 (107) | −0,05 (96) | −0,06 (111) | −0,30 (100) | +0,42 (104) | 4/6 |

### R2 hors nis_z_100 Q4 — H = 26

| Stop | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 | Années > 0 |
|---|---|---|---|---|---|---|---|
| Sans stop (contrôle) | +0,63 (189) | +0,13 (192) | +0,09 (173) | +0,51 (188) | −0,06 (171) | +0,83 (167) | 5/6 |
| SL-A 1,0 ATR | +0,35 (230) | +0,10 (234) | −0,10 (210) | +0,01 (226) | −0,03 (208) | +0,21 (202) | 4/6 |
| SL-A 1,5 ATR | +0,41 (212) | +0,07 (220) | +0,03 (193) | +0,19 (206) | −0,11 (191) | +0,31 (188) | 5/6 |
| SL-A 2,0 ATR | +0,45 (202) | +0,04 (209) | +0,14 (184) | +0,12 (195) | −0,11 (177) | +0,15 (178) | 5/6 |
| SL-A 2,5 ATR | +0,47 (197) | +0,08 (206) | −0,01 (179) | +0,13 (193) | −0,27 (177) | +0,22 (171) | 4/6 |
| SL-A 3,0 ATR | +0,48 (192) | +0,01 (198) | +0,13 (177) | −0,01 (192) | −0,29 (175) | +0,34 (170) | 4/6 |
| SL-A 4,0 ATR | +0,64 (189) | +0,06 (194) | +0,13 (174) | +0,12 (190) | −0,04 (173) | +0,51 (169) | 5/6 |
| SL-A 5,0 ATR | +0,75 (189) | +0,07 (194) | +0,10 (174) | +0,29 (190) | −0,15 (172) | +0,64 (168) | 5/6 |
| SL-B extremum + 0,00 ATR | +0,56 (205) | −0,01 (212) | +0,14 (186) | +0,21 (197) | −0,13 (181) | +0,19 (179) | 4/6 |
| SL-B extremum + 0,25 ATR | +0,55 (201) | +0,05 (210) | +0,10 (183) | +0,13 (197) | −0,23 (180) | +0,16 (177) | 5/6 |
| SL-B extremum + 0,50 ATR | +0,47 (201) | +0,00 (209) | +0,07 (182) | +0,21 (193) | −0,27 (177) | +0,27 (174) | 4/6 |
| SL-B extremum + 1,00 ATR | +0,49 (194) | −0,03 (201) | +0,08 (178) | +0,07 (192) | −0,34 (177) | +0,26 (172) | 4/6 |
