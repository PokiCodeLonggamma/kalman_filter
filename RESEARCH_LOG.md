# RESEARCH LOG — JOURNAL D'EXPÉRIMENTATION AKF-TSO

---

## MODÈLE D'ENTRÉE STANDARD (À REPRODUIRE POUR CHAQUE EXPÉRIENCE)

```markdown
### [EXP-XXX] — Titre court de l'expérience
- **Date :** YYYY-MM-DD
- **Étape :** (A Anatomie / B Catégorisation / C Enveloppe / D Optuna-WFO / Transfert / Validation finale — voir `PROJECT_PLAN.md`)
- **Actif & Période :** (ex. BTCUSD 30m, 2020-2025)
- **Modèle de frais :** (ex. 10 bps aller-retour ; « sans objet » pour une mesure descriptive sans PnL)

#### 0. Cadrage obligatoire (`RESEARCH_PHILOSOPHY.md` §4.6)
- **QUESTION :**
- **PERTINENCE POUR LE FILTRE AKF :**
- **CE QUE LE PROTOCOLE MESURE RÉELLEMENT :**
- **CE QU'IL NE PERMET PAS DE CONCLURE :**

#### 1. Hypothèse & Motivation physique
- Quelle inefficience ou quel comportement mécanique cherche-t-on à tester/corriger ?
- Pourquoi cette règle précise ?

#### 2. Règle testée (OFAT)
- **Entrée :** (ex. Open t+1 sur signal Kalman natif)
- **Sortie :** (ex. Time-Stop à 32 barres, Stop-Loss à 4 ATR, BE à +2 ATR...)
- **Contrôle / Baseline de comparaison :** (ex. enveloppe de l'expérience précédente ; le stop-and-reverse natif ne sert que d'ancre de non-régression)

#### 3. Résultats nets
*(Expérience descriptive, Étape A : ce tableau est sans objet ; le remplacer par les distributions mesurées, quantiles et effectifs.)*
| Métrique | Contrôle (Baseline) | Variante testée | Écart / Impact |
|---|---|---|---|
| PnL Net Total | ... | ... | ... |
| Profit Factor | ... | ... | ... |
| Win Rate | ... | ... | ... |
| Espérance / trade | ... | ... | ... |
| Max Drawdown | ... | ... | ... |
| Nombre de trades | ... | ... | ... |
| Durée médiane | ... | ... | ... |
| Part des frais | ... | ... | ... |

#### 4. Analyse causale & Physique du trade
- [OBS] Que s'est-il passé sur les données ? (Comportement des gains, des pertes de queue, des faux départs).
- [HYP] Pourquoi le système réagit-il ainsi ? (Le filtre a-t-il coupé trop tôt ? Le time-stop a-t-il évité un pourrissement ?).

#### 5. Décision
- [ ] **REJETÉ :** L'hypothèse détruit de la valeur ou ajoute une complexité injustifiée.
- [ ] **NON CONCLUANT :** L'effet est dans la marge d'erreur des frictions.
- [ ] **À POURSUIVRE :** Le résultat est suffisamment intéressant pour servir de base de travail à l'étape suivante, sans constituer une conclusion définitive.
```

---

## JOURNAL

### [PHASE 0] — Audit historique : clôture
- **Date :** 2026-09-27
- **Livrable :** Artifact « AKF-TSO — Historical Audit & Project Map » (https://claude.ai/artifact/VL4Nv1tt1x5aSEGGXoJngz).
- **[CODE]** Moteur de référence : `AKF_TSO_v2.1_baseline.pine` (SHA-256 `c70062b8…ecd30b317`) et sa réplique `src/indicator/` (parité 5,2·10⁻¹⁰ sur 117 584 barres). Ils sont dans `#KAKALMAN` (lecture seule) ; leur copie dans `#KalmanFilter` reste à valider.
- **[OBS]** Mécanique native v2.1 (#KAKALMAN P6.5d, BTC 30m 2020-2025, exécution à l'open t+1, 5 bps) : 7 296 signaux, 6 037 changements de position (~84/mois), −5,34 bps/trade net, PF 0,907, capital −98,7 %. Frais cumulés ≈ 30 200 bps pour un PnL brut cumulé de −2 047 bps.
- **[OBS]** Les archives d'avril-mai reposent sur Pine V2 ou sur des variantes du moteur (`use_true_kalman`, règles de flip NewKalman) : chiffres non transposables, réservoir d'hypothèses (`RESEARCH_PHILOSOPHY.md` §4.5).
- **Décision :** recadrage du 2026-09-27. Hypothèse directrice (`RESEARCH_PHILOSOPHY.md` §1), feuille de route A → D (`PROJECT_PLAN.md`), cadrage obligatoire (§4.6). La séquence EXP-001 (stop-and-reverse natif) / EXP-002 (signal contre hasard) est abandonnée.
- **Ouvert :** hold-out final (ETH et XRP ont déjà été vus par le projet Kalman et les Labos 2-3), frais canoniques (5 ou 10 bps), sources de données SOL/SOXS/WTI.

### [EXP-A01] — Anatomie et distribution du signal brut
- **Date :** 2026-09-28
- **Étape :** A Anatomie (descriptive)
- **Actif & Période :** BTC/USD Bitstamp 30m, 2020-01-01 → 2025-12-31 (2026, ETH et XRP non lus)
- **Modèle de frais :** sans objet (aucune transaction simulée)
- **Livrables :** `experiments/A01/rapport_A01.md` ; atlas `experiments/A01/atlas_signaux.csv` (7 296 lignes, SHA-256 `e89d509c…0a3e246c`) ; figures `experiments/A01/figures/`.

#### 0. Cadrage obligatoire
- **QUESTION :** quand, à quelle distance de l'extremum de prix visé et dans quel état cinématique le signal v2.1 se déclenche-t-il ? Ces distributions sont-elles stables par année ?
- **PERTINENCE POUR LE FILTRE AKF :** gain figé par le reset de P, normalisation par max|x1| sur 5 barres (aveugle à l'amplitude), déclencheur one-shot après au moins 6 barres en zone.
- **CE QUE LE PROTOCOLE MESURE RÉELLEMENT :** distributions de 6 variables a posteriori et 19 variables causales sur 7 296 signaux, par sens, type et année ; profils de −48 à +48 barres ; corrélations de Spearman.
- **CE QU'IL NE PERMET PAS DE CONCLURE :** ni rentabilité ni avantage d'excursion ; les variables `post_` ne sont jamais des filtres ; quantiles ≠ seuils ; corrélations ≠ causalité ; valable aux réglages par défaut, BTC 30m, 2020-2025.

#### 1. Hypothèse & Motivation physique
- Aucune hypothèse testée : cartographie de la géométrie naturelle du signal avant toute catégorisation (feuille de route A → D).

#### 2. Règle testée (OFAT)
- Aucune règle : moteur v2.1 par défaut, signal lu à la clôture de t. Contrôle : ancres de #KAKALMAN (7 296 signaux, 6 037 rangs 1) retrouvées exactement.

#### 3. Résultats (descriptifs ; tableau des 8 métriques sans objet)
| Mesure | Valeur |
|---|---|
| Cadence | 101,9 signaux/mois, dont 84,3 flips ; 17,3 % de répétitions de même sens |
| Cycle | écart au précédent de même sens 26 barres [21 ; 34] ; de sens opposé 13 [10 ; 20] |
| Extremum du segment tenu jusqu'au signal suivant | 63,9 % (horizon 13 barres [10 ; 17]) ; identité exacte : cassé ⇔ excursion adverse > `obs_dist_seg_atr` |
| Extremum cassé | 36,1 % : nouvel extremum 8 barres plus tard [5 ; 12], à 3,01 ATR [1,99 ; 4,67] ; bimodalité de `post_lag_bars` = effet de géométrie |
| Mouvement déjà parcouru, causal (`obs_dist_seg_atr`) | 1,77 ATR [1,26 ; 2,39] ; ρ = 0,09 avec l'ancienneté de l'extremum, 0,63 avec `nis_z_100` |
| Signal et passage à zéro de x1 | à la barre : 36,8 % ; 1-2 barres avant : 27,7 % ; ≥ 3 barres avant : 21,2 % ; sans passage : 13,6 % |
| Vitesse x1 au signal | médiane +0,002 ATR/barre ; déjà du sens du signal : 51,8 % |
| Répétitions | extremum cassé 31,0 % contre 37,1 % (marge plus grande, excursion adverse égale) ; nouvel extremum de cycle dans 86,3 % des cas |
| `nis_z_100` | pic isolé à τ = 0 : 0,19 [−0,32 ; 1,20], contre −0,4 à ±3 barres |
| Close après le signal (rangs 1) | médiane entre −0,05 et +0,04 ATR de +1 à +48 barres |
| Stabilité 2020-2025 | géométrie stable en ATR ; ATR14 médian de 34 à 80 bps selon l'année |

#### 4. Analyse causale & Physique du trade
- [OBS] Le signal arrive environ 5 barres après l'extremum de prix. Il tombe à la barre du passage à zéro de x1 ou 1 à 2 barres avant dans 64,5 % des cas ; ailleurs, il précède de 3 barres ou plus un retournement, ou n'en voit aucun. L'extremum du segment tient jusqu'au signal suivant dans 63,9 % des cas. La barre de déclenchement est un choc d'innovation qui porte la distance déjà parcourue.
- [HYP] Le retard vient du gain figé. Le déclencheur mêle retournement et décélération de la vitesse. La tenue de l'extremum est une variable descriptive, jamais une cible seule de B : elle croît mécaniquement avec la distance déjà parcourue (`RESEARCH_INSIGHTS.md`, I-M1). La cible de B est l'asymétrie d'excursion (I-M2). La médiane plate du close ne dit rien de l'excursion ni des sous-familles. La géométrie étant stationnaire en ATR, l'enveloppe devra s'exprimer en ATR14(t).
- **Relecture (2026-09-28)** après revue indépendante : lecture « retard bimodal » corrigée en tenue ou cassure de l'extremum ; description du déclencheur nuancée ; `nis_z_100_seg_max` réintégré dans les descripteurs de B, où il manquait ; `cycle_seg_div_atr` et `decel_ratio` remplacent les variables de cycle et `peak_bps_vol`. L'hypothèse « répétition = double bottom » n'est pas soutenue : 86,3 % des répétitions marquent un nouvel extremum. Détails : rapport, annexe H.

#### 5. Décision
- [ ] **REJETÉ**
- [ ] **NON CONCLUANT**
- [x] **À POURSUIVRE :** l'atlas et le jeu réduit de descripteurs causaux (rapport, §4) servent de base à l'Étape B. Aucune Étape B lancée.

### [EXP-B01] — Catégorisation cinématique et asymétrie d'excursion
- **Date :** 2026-09-28
- **Étape :** B Catégorisation
- **Actif & Période :** BTC/USD Bitstamp 30m, 2020-2025, les 7 296 signaux d'A01 (2026, ETH et XRP non lus)
- **Modèle de frais :** sans objet (aucun PnL, aucune transaction simulée)
- **Livrables :** `experiments/B01/rapport_B01.md` ; `excursions_signaux.csv` (7 296 lignes, SHA-256 `e1459a48…b4d28c`) ; `tableaux_univarie_B01.csv` ; `tableaux_familles_B01.csv` ; 4 figures.

#### 0. Cadrage obligatoire
- **QUESTION :** quelles sous-familles causales présentent une asymétrie d'excursion favorable depuis open[t+1] (MFE_H > \|MAE_H\|, barrière favorable > 50 %) ? Lesquelles relèvent de l'essoufflement, de la sortie de range ou de la continuation ?
- **PERTINENCE POUR LE FILTRE AKF :** le déclencheur unique mélange des états cinématiques opposés. B les sépare avant toute règle de gestion.
- **CE QUE LE PROTOCOLE MESURE RÉELLEMENT :** excursions MFE, MAE, asymétrie et rendement à H ∈ {6, 13, 26, 48} ; premier passage sur des barrières de ±1,0, ±1,5 et ±2,0 ATR14(t) ; par quartiles univariés (15 descripteurs), par familles F1-F5 et par strates, en Long et en Short.
- **CE QU'IL NE PERMET PAS DE CONCLURE :** aucun PnL net, aucune optimisation de seuils.

#### 1. Hypothèse & Motivation physique
- Les mécanismes captés par le déclencheur (essoufflement, sortie de range, climax, répétition) ont-ils des profils d'excursion distincts ? Hypothèse de travail du porteur (`RESEARCH_INSIGHTS.md` §3).

#### 2. Règle testée (OFAT)
- Aucune règle : entrée théorique à open[t+1], mesures a posteriori. Contrôle du bêta sans placebo : décomposition timing = (ΔL − ΔS) / 2, dérive = (ΔL + ΔS) / 2, par strate.

#### 3. Résultats (descriptifs ; tableau des 8 métriques sans objet)
| Mesure | Valeur |
|---|---|
| Tous les signaux | MFE ≈ \|MAE\| ; MFE > \|MAE\| : 51,4 % [50,3 ; 52,6] à H6, 49,7 % à H26 ; gain strict ±1,5 : 50,2 % ; close : timing ≈ 0, dérive +0,21 ATR à H48 |
| Continuation (anti-timing) | `nis_z_100` Q4 : 46,3 % [44,0 ; 48,6] à H26, timing −0,18 ATR, stable 6/6 ans ; `obs_dist_seg_atr` Q4 : 47,2 %, timing −0,17 ; F1 avec x1 déjà retourné : 45,2 % |
| Favorable, court terme | F5 (entrée fraîche, n = 741) : 56,0 % [52,4 ; 59,5] à H6 dans les deux sens ; gain ±1,0 : 53,6 % ; éteint à H26 |
| Favorable apparent = dérive | F2b Long 53,7 % [50,2 ; 57,1] (dérive +0,35) ; `A_vol` Q1 Short 53,7 % [50,4 ; 56,9] (dérive −0,13, Long 46,7 %) |
| Familles du porteur | F1 : 48,6 %, parcours d'abord adverse, close +0,13 ; F3 : 49,8 %, neutre ; F4 : Long 45,3 % / Short 55,3 %, petits effectifs |

#### 4. Analyse causale & Physique du trade
- [OBS] Le signal global n'a pas d'asymétrie d'excursion au-delà de 6 barres. Les effets par strate valent 2 à 6 points et 0,1 à 0,5 ATR, soit l'ordre des frictions (≈ 0,1-0,2 ATR). Les fenêtres se chevauchent, donc les IC sont optimistes.
- [HYP] Un choc violent sur la barre de signal ou un mouvement déjà consommé signent une continuation. L'entrée fraîche (F5) porte un avantage de très court terme. F1 part d'abord contre le signal. F3 n'est pas soutenu comme breakout. `A_vol` et F2b sont de la dérive de régime. Les profils d'horizon différents soutiennent des enveloppes propres à chaque mécanisme.

#### 5. Décision
- [ ] **REJETÉ**
- [ ] **NON CONCLUANT**
- [x] **À POURSUIVRE :** trois pistes pour l'Étape C, à tester un facteur à la fois et nettes de frais : exclure les signatures de continuation, une enveloppe courte pour F5, un stop structurel large pour F1. Aucune Étape C lancée.
