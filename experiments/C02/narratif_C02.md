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

  C02bis n'est pas lancé. Les orientations de la relecture du porteur sont au §5.4.

## 5. Relecture du porteur (2026-09-29)

Revue indépendante des 864 lignes de `resultats_C02.csv`, transmise par le porteur. Chaque chiffre a été recalculé avec le moteur du dépôt (script hors livrables).

### 5.1 Vérifications

| Affirmation de la revue | Recalcul | Verdict |
|---|---|---|
| F2b H26 sans stop : 53,7 % des trades ont une excursion adverse ≥ 2 ATR ; laissés courir, ils finissent à −1,38 ATR et 27,1 % positifs | 53,7 % ; −1,38 ATR brut (−1,52 net de 5 bps) ; 25 % positifs nets | retrouvé |
| Stop de F2b à 2 ATR : −0,62 ATR par trade stoppé, −0,33 sur l'ensemble | −0,618 et −0,332 | retrouvé |
| Drawdown de F2b avec un stop de 1 à 3 ATR : −15 à −22 % | −12 à −22 % (SL-A 1,5 : −12 %, contre −13 % sans stop) | nuancé : pas d'amélioration nette |
| F3 H26 : les trades qui touchent l'extremum finissent à −2,17 ATR sans stop | 50 % des trades touchent ; −2,21 ATR brut (−2,36 net), 21 % positifs ; les autres finissent à +2,68 | retrouvé |
| F5 : 5 bps = 0,135 ATR (ATR médian 45 bps) ; barrières ±1 à ±2 ATR : brut +0,067 à +0,116, net −0,068 à −0,019 ATR | identique au niveau signal (fenêtres chevauchantes) ; le PnL séquentiel (−8,5 à −0,5 %) n'est pas recalculé | retrouvé |
| F3 : Long et Short positifs avec stop aux trois horizons | voir §5.2 | retrouvé (estimations centrales) |
| R2 hors Q4 : +36 % à H13 (SL-A 1,5), +51 % à H48 (SL-A 5) | identique | retrouvé, avec réserve (§5.2) |
| Assemblage R2 hors Q4 à H26, F2b sans stop + F3 SL-B à l'extremum : +0,370 ATR [+0,100 ; +0,648], +12,5 bps [+0,3 ; +24,5], +139 %, DD −12,1 %, 6/6 ans | +0,369 [+0,098 ; +0,645], +12,3 [+0,2 ; +24,4], +138 %, DD −13,5 % valorisé (−12,9 % aux sorties), 6/6 ans ; 1 080 trades (1 079 dans la revue) | retrouvé à 1 % près |

### 5.2 Ce que le narratif n'avait pas dit

- **Le stop rend F3 positif des deux côtés.** Long / Short en ATR, 5 bps, séquentiel dynamique :

  | H | Sans stop | SL-B à l'extremum | Autre règle |
  |---|---|---|---|
  | 13 | +0,01 / −0,00 ; PnL −3 % (1x −24 %) | +0,07 / +0,13 ; +15 % | SL-A 1,5 : +0,08 / +0,12 ; +17 % |
  | 26 | +0,27 / −0,02 ; +16 %, DD −34 % | +0,17 / +0,24 ; +36 %, DD −13 % (1x +72 %) | SL-A 2 : +0,15 / +0,24 ; +33 % |
  | 48 | −0,05 / +0,56 ; +3 %, DD −47 % | +0,16 / +0,24 ; +15 %, DD −19 % | SL-A 5 : +0,38 / +0,53 ; +49 %, DD −20 % |

  Ce sont des estimations centrales. L'IC 95 % de l'espérance de F3 avec stop contient toujours 0.
- **R2 hors Q4 n'est pas un pic isolé à H26 une fois stoppé.**
  - Sans stop, il fait +1 % à H13 et −5 % à H48.
  - SL-A 1,5 à H13 : +36 %, DD −14 %, Long / Short +0,11 / +0,10 ATR.
  - SL-A 5 à H48 : +51 %, +0,261 ATR, DD −26 %.

  Réserve : la règle change avec l'horizon, choisie parmi 11. Avec une règle unique, SL-B à l'extremum, R2 hors Q4 reste positif aux trois horizons (+0,076, +0,166, +0,183 ATR), mais aucun IC n'exclut 0.
- **La lecture « entrées figées » est une règle causale et exécutable.** C'est un cooldown : après un stop, la position reste à plat jusqu'à t + 1 + H, la sortie prévue à l'entrée.
  - F3 H26, SL-B à l'extremum : +0,236 ATR, +41 %, DD −13 % en cooldown, contre +0,202 ATR et +36 % en réouverture immédiate.
  - La réouverture reprend des trades débloqués à −0,89 ATR : ceux qui suivent l'échec du breakout.

### 5.3 Assemblage différencié de R2 hors Q4 (vérification, hors protocole de C02bis)

H26, une position à la fois. Chaque signal suit l'enveloppe de sa sous-famille, connue à t. Lecture cooldown.

| Configuration | Frais | Trades | Espérance ATR [IC] | Espérance bps [IC] | Long / Short (ATR) | PnL ; DD valorisé à 0,25 %/ATR | PnL ; DD en 1x | Années > 0 |
|---|---|---|---|---|---|---|---|---|
| F2b seul, sans stop | 5 | 639 | +0,389 [+0,079 ; +0,700] | +11,5 [−2,9 ; +26,0] | +0,53 / +0,25 | +72 % ; −13 % | +78 % ; −45 % | 5/6 |
| R2 hors Q4 uniforme, sans stop | 5 | 1 080 | +0,354 [+0,051 ; +0,643] | +12,3 [−1,5 ; +25,8] | +0,48 / +0,21 | +122 % ; −21 % | +187 % ; −48 % | 5/6 |
| RE-1 : F2b sans stop, F3 SL-B à l'extremum | 5 | 1 080 | +0,369 [+0,098 ; +0,645] | +12,3 [+0,2 ; +24,4] | +0,46 / +0,27 | +138 % ; −13,5 % | +204 % ; −44 % | 6/6 |
| RE-2 : F2b sans stop, F3 SL-A 2 ATR | 5 | 1 080 | +0,353 [+0,084 ; +0,625] | +11,7 [−0,4 ; +24,2] | +0,43 / +0,26 | +132 % ; −13,1 % | +185 % ; −42 % | 6/6 |
| RE-1 | 10 | 1 080 | +0,233 [−0,041 ; +0,511] | +7,3 [−4,8 ; +19,4] | +0,32 / +0,13 | +72 % ; −15,9 % | +77 % ; −48 % | 5/6 |

- **Années de RE-1, en ATR :** 2020 +0,51 ; 2021 +0,02 ; 2022 +0,30 ; 2023 +0,50 ; 2024 +0,33 ; 2025 +0,55.
- **Réouverture immédiate, 5 bps :** RE-1 fait +0,338 ATR et +133 %.
- **Le gain de RE-1 porte sur le drawdown, pas sur l'espérance.**
  - Sur les mêmes entrées, l'effet apparié contre R2 uniforme vaut +0,015 ATR [−0,108 ; +0,141], soit +0,01 bps [−5,6 ; +5,7].
  - L'amélioration tient au drawdown (−20,5 % → −13,5 %) et à la régularité (6 années positives sur 6).
  - L'IC en bps n'exclut 0 que de 0,2 bps.
  - La règle de F3 a été choisie après lecture de C02 : c'est un résultat dans l'échantillon, à confirmer en C02bis (plateau d'horizon, seuils causaux).

### 5.4 Orientations de la revue (à acter dans le cadrage de C02bis)

- **R1, F1, F5 : rejet définitif proposé.** Veto d'entrée si `x1_already_flipped_at_t` est faux, en plus des vetos R3 et `nis_z_100` Q4. Argument de la revue : même un take-profit symétrique ne compense pas le coût des frais en ATR sur F5 (0,135 ATR par trade).
- **Moteur de régimes :** routage causal de R2 hors Q4. F2b sans stop, F3 stop à l'extremum (ou SL-A 2 ATR).
- **Réentrée après un stop :** facteur à tester, cooldown jusqu'à t + 1 + H contre réouverture immédiate.
- **Contrôles demandés :**
  - plateau d'horizon autour de 26 barres (20, 24, 26, 28, 32 en plus de 13, 26, 48) ;
  - seuils causaux (contrôle B de C01) ;
  - frais de 5 et 10 bps ;
  - capital à 0,25 % par ATR et en 1x.
- **Hold-out** (BTC 2026, ETH, XRP) scellé jusqu'à la fin de l'Étape D.
