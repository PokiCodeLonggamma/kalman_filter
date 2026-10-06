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
- **Livrables :** `experiments/B01/rapport_B01.md` ; `excursions_signaux.csv` (7 296 lignes, SHA-256 `e1459a48…b4d28c`) ; `tableaux_univarie_B01.csv` ; `tableaux_familles_B01.csv` ; `tableau_regimes_B01.csv` (relecture) ; 5 figures.

#### 0. Cadrage obligatoire
- **QUESTION :** quelles sous-familles causales présentent une asymétrie d'excursion favorable depuis open[t+1] (MFE_H > \|MAE_H\|, barrière favorable > 50 %) ? Lesquelles relèvent de l'essoufflement, de la sortie de range ou de la continuation ?
- **PERTINENCE POUR LE FILTRE AKF :** le déclencheur unique mélange des états cinématiques opposés. B les sépare avant toute règle de gestion.
- **CE QUE LE PROTOCOLE MESURE RÉELLEMENT :** excursions MFE, MAE, asymétrie et rendement à H ∈ {6, 13, 26, 48} ; premier passage sur des barrières de ±1,0, ±1,5 et ±2,0 ATR14(t) ; par quartiles univariés (15 descripteurs), par familles F1-F5 et par strates, en Long et en Short.
- **CE QU'IL NE PERMET PAS DE CONCLURE :** aucun PnL net, aucune optimisation de seuils ; les regroupements R1-R3 de la relecture sont définis après lecture des résultats.

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
| Familles du porteur | F1 : 48,6 %, parcours d'abord adverse, close +0,13 ; F3 : 49,8 %, neutre en médiane (timing moyen +0,30 à H48, côté Short) ; F4 : Long 45,3 % / Short 55,3 %, petits effectifs |
| Relecture : trois régimes (timing au close, IC 95 % par grappes mensuelles) | R1 = F1/F5 · x1 encore opposé (n = 1 935) : médiane +0,16 [+0,10 ; +0,22] à H6, 6/6 ans ; moyenne ≈ 0 (queue gauche). R2 = F2b/F3 · x1 déjà retourné (n = 1 874) : médiane ≈ 0 ; moyenne +0,28 [+0,03 ; +0,50] à H48, 5/6 ans (queue droite). R3 = F1 · x1 déjà retourné, F2a, F4 (n = 2 347) : moyenne −0,29 [−0,48 ; −0,07] à H48, négative 6/6 ans |

#### 4. Analyse causale & Physique du trade
- [OBS] Le signal global n'a pas d'asymétrie d'excursion au-delà de 6 barres. Les effets par strate valent 2 à 6 points et 0,1 à 0,5 ATR, soit l'ordre des frictions (≈ 0,1-0,2 ATR). Les fenêtres se chevauchent, donc les IC sont optimistes.
- [HYP] Un choc violent sur la barre de signal ou un mouvement déjà consommé signent une continuation. L'entrée fraîche (F5) porte un avantage de très court terme. `A_vol` et F2b sont de la dérive de régime. Les profils d'horizon différents soutiennent des enveloppes propres à chaque mécanisme.
- **Relecture (2026-09-28)** après revue indépendante transmise par le porteur (rapport §5, annexe I). Le résumé par médianes et barrières symétriques ne voyait pas les espérances portées par une queue. Deux lectures sont corrigées :
  - F3 « non soutenu comme breakout » : la sortie de range se lit en moyenne (R2), pas en médiane ;
  - « stop large pour F1 » : F1 mêle R1 (timing médian positif) et une part de R3 (continuation).

  Chiffres de la relecture retrouvés à ±0,01 ATR, sauf quatre écarts mineurs (rapport §5). La vérification ajoute trois réserves :
  - les moyennes sont peu précises : l'IC de F3 seul contient 0 à H48 ;
  - R2 réunit deux effets d'un seul côté (F3 · x1 déjà retourné côté Short, F2b · x1 déjà retourné côté Long) ;
  - pour R1, l'extremum du segment ne tient que dans 46,9 % des cas jusqu'au signal suivant.

#### 5. Décision
- [ ] **REJETÉ**
- [ ] **NON CONCLUANT**
- [x] **À POURSUIVRE :** pistes pour l'Étape C, révisées à la relecture, à tester un facteur à la fois et nettes de frais :
  - R3 et `nis_z_100` Q4 : exclusion en retournement, et test dédié en continuation ;
  - R1 : stop structurel serré derrière l'extremum du segment, horizon borné ;
  - R2 : tenue de 26 à 48 barres, stop large ou break-even différé.

  La piste « stop structurel large pour F1 » est retirée. Aucune Étape C lancée.

### [EXP-C01] — Découplage de la sortie et isolation des régimes, en exécution séquentielle
- **Date :** 2026-09-29
- **Étape :** C Enveloppe (premier test)
- **Actif & Période :** BTC/USD Bitstamp 30m, 2020-01 → 2025-12 (72 mois) ; 2026, ETH et XRP non lus
- **Modèle de frais :** 5 et 10 bps aller-retour, déduits de chaque trade
- **Livrables :**
  - `experiments/C01/rapport_C01.md`, `resultats_C01.csv` (130 lignes), `annuel_C01.csv`, 4 figures ;
  - `manifest_copie_C01_sha256.txt` (copie certifiée depuis #KAKALMAN) ;
  - `src/envelope/`, `tests/test_envelope.py`.

#### 0. Cadrage obligatoire
- **QUESTION :** en séquentiel (une position à la fois), net de 5 et 10 bps : effet d'une sortie à horizon fixe H ∈ {6, 13, 26, 48} à la place de la sortie native ; puis, à H fixé, de la restriction aux régimes de B01, de l'éviction de `nis_z_100` Q4 et de l'inversion en continuation de R3 et de `nis_z_100` Q4.
- **PERTINENCE POUR LE FILTRE AKF :** la sortie native coupe vers 13 barres et produit 84 retournements par mois. C01 isole le découplage de la sortie et le filtrage cinématique, avant tout stop.
- **CE QUE LE PROTOCOLE MESURE RÉELLEMENT :** 8 métriques nettes, décomposition Long / Short / timing / dérive (bps et ATR14(t)), stabilité annuelle, IC 95 % par bootstrap de grappes mensuelles, sur les trades exécutés.
- **CE QU'IL NE PERMET PAS DE CONCLURE :**
  - l'effet d'un stop, d'un break-even ou d'un filtre de tendance ;
  - une validation hors échantillon : régimes définis après B01, seuils calculés sur 2020-2025 ;
  - la meilleure des 64 paires (régime, H) est un résultat optimiste.

#### 1. Hypothèse & Motivation physique
- La mécanique native perd-elle surtout par le turnover (frais) ou par l'absence de timing ? Les régimes de B01 (R1, R2, R3, `nis_z_100` Q4) se traduisent-ils en espérances nettes distinctes une fois exécutés un à un ?

#### 2. Règle testée (OFAT)
- **Entrée :** open[t + 1] si aucune position n'est ouverte ; signaux intermédiaires ignorés.
- **Sortie :** open[t + 1 + H], sans stop ni take-profit ; ramenée à la dernière barre de 2025 au besoin.
- **Contrôles :** trois paliers, un seul facteur par comparaison.
  - Palier 1 : ancre native P6.5d, reproduite à l'identique.
  - Palier 2 : Tous au même H.
  - Palier 3 : le groupe du palier 2 (éviction de `nis_z_100` Q4, ou inversion du sens).

#### 3. Résultats nets (5 bps ; IC 95 % par grappes mensuelles)
| Métrique | Ancre native | Tous, H6 | R2 hors Q4, H26 | R3 en continuation, H26 |
|---|---|---|---|---|
| PnL Net Total | −98,7 % ; −32 232 bps | −95,7 % ; −26 967 bps | +187 % ; +13 309 bps | +281 % ; +17 236 bps |
| Profit Factor | 0,907 | 0,899 | 1,18 | 1,15 |
| Win Rate | 43,8 % | 46,9 % | 49,4 % | 51,6 % |
| Espérance / trade | −5,3 bps [−10,8 ; +0,3] ; −0,08 ATR | −3,7 [−6,5 ; −0,9] ; −0,10 ATR | +12,3 [−0,8 ; +26,4] ; +0,35 ATR | +10,3 [+1,3 ; +19,8] ; +0,11 ATR |
| Espérance à 10 bps | −10,3 | −8,7 | +7,3 [−5,8 ; +21,4] ; +0,22 ATR | +5,3 [−3,7 ; +14,8] ; −0,01 ATR |
| Max Drawdown (valorisé) | −99,6 % | −97,8 % | −47,6 % | −47,6 % |
| Nombre de trades | 6 037 (83,8/mois) | 7 296 (101,3/mois) | 1 080 (15,0/mois) | 1 674 (23,2/mois) |
| Durée médiane | 13 barres | 6 barres | 26 barres | 26 barres |
| Part des frais | 1 474 % | 383 % | 29 % | 33 % |

#### 4. Analyse causale & Physique du trade
- [OBS] **Palier 1.** La sortie à horizon fixe réduit le turnover, pas la perte. Espérance nette : −3,7, −4,3, −10,8 et −16,0 bps à H6, H13, H26 et H48, contre −5,3 pour l'ancre. L'espérance brute du flux complet ne dépasse jamais +1,3 bps ; elle devient négative dès H26, par le côté Short.
- [OBS] **Palier 2.** R3 et `nis_z_100` Q4, dans le sens du signal, perdent avec des IC entièrement négatifs de H6 à H26 (jusqu'à −20 bps par trade). R1 est négatif sans stop à tous les horizons. R2 est proche de 0. Exclure `nis_z_100` Q4 donne +0,8 à +3,8 bps à H13-H48, avec des IC contenant 0.
- [OBS] **Palier 3.** L'éviction de `nis_z_100` Q4 améliore 18 comparaisons sur 20. Quatre configurations sont positives à 5 bps :
  - R2 hors Q4 à H26 (pic isolé : +0,3 à H13, −2,9 à H48) ;
  - R3 en continuation à H26, seul IC entièrement positif des 64, porté par 2020-2021 (+28, +26, +7, 0, +11, −8 bps par an) ;
  - `nis_z_100` Q4 en continuation à H26, négatif en 2024-2025 ;
  - Tous hors R3 et Q4 à H48, porté par les Long.
  
  À 10 bps, aucune configuration n'a d'IC entièrement positif. Les drawdowns valorisés vont de 48 à 81 %, et l'écart entre moyenne arithmétique et PnL composé de 0,6 à 5 bps par trade.
- [HYP] Pris dans son sens, sans stop, le signal ne dégage pas d'espérance nette solide. Son information la plus robuste est négative : R3 et `nis_z_100` Q4 marquent une continuation. R3 en continuation dépend du régime de volatilité ; R2 hors Q4 à H26 est cohérent avec B01 mais étroit en horizon ; R1 relève du test du stop.
- **Relecture (2026-09-29)**, contrôles demandés par le porteur (rapport §5, annexes F à H) :
  - **Séparation F2b / F3 dans R2 hors Q4.** F2b · x1 déjà retourné hors Q4 est positif à H13, H26 et H48, et tient 10 bps à H26 (+6,5 bps, +0,26 ATR). F3 · x1 déjà retourné hors Q4 est irrégulier : −47 bps par trade en 2024 à H26.
  - **Contrôle A, éviction pure ou calendrier.** Le gain de F2b · x1 déjà retourné hors Q4 vient entièrement de l'éviction (purge a posteriori : +12,1 [−3,5 ; +27,9]). Celui de R2 en vient aux trois quarts. F3 · x1 déjà retourné doit un tiers de son PnL hors Q4 à 15 trades débloqués.
  - **Contrôle B, seuils causaux** (fenêtre glissante de 500 signaux ou expansive) : 98,6 à 99,9 % des masques inchangés, écarts de résultat sous 2,5 bps. R1 hors Q4 reste sans avantage à H6.
  - **Contrôle C, risque constant par trade.** Avec 1 ATR = 1 % du capital, 90 % des trades restent plafonnés à 1x : rien ne change. Avec 1 ATR = 0,25 % du capital, F2b · x1 déjà retourné hors Q4 à H26 fait +72 % pour un drawdown de −13 % (+42 % et −17 % à 10 bps). R3 en continuation retombe à +3 % à 10 bps.
  - **Affichage** : la part des frais est « sans objet » si le PnL brut est ≤ 0.

#### 5. Décision
- [ ] **REJETÉ**
- [ ] **NON CONCLUANT**
- [x] **À POURSUIVRE :**
  - le découplage seul de la sortie, sur tous les signaux, n'est pas un correctif ;
  - l'éviction de `nis_z_100` Q4 est le filtre le plus régulier ;
  - décisions du porteur (2026-09-29) : la continuation est écartée définitivement comme mode d'entrée, R3 et `nis_z_100` Q4 ne servent plus que de filtres d'exclusion ; R2 hors Q4 n'est pas traité comme un bloc ;
  - candidats pour C02 (stop seul, OFAT) : F2b · x1 déjà retourné hors Q4 à H26 (candidat principal, stop large ou break-even), F3 · x1 déjà retourné hors Q4 à part, R1 avec un stop serré.

  Points à trancher avant C02 : choix de H par régime, dimensionnement (le risque constant par ATR est un candidat de convention), frais canoniques, validation hors échantillon. Aucune Étape C02 lancée.

### [EXP-C02] — Stop-loss en prix par sous-famille, en exécution séquentielle
- **Date :** 2026-09-29
- **Étape :** C Enveloppe (deuxième test ; OFAT : le stop seul)
- **Actif & Période :** BTC/USD Bitstamp 30m, 2020-01 → 2025-12 (72 mois) ; 2026, ETH et XRP non lus
- **Modèle de frais :** 5 et 10 bps aller-retour. Capital : 1 ATR14(t) = 0,25 % du capital, levier ≤ 1x (convention de l'Étape C, décision du porteur) ; notionnel 1x gardé dans le CSV.
- **Livrables :**
  - `experiments/C02/rapport_C02.md`, `resultats_C02.csv` (864 lignes), `annuel_C02.csv`, `controles_C02.json`, 4 figures ;
  - `src/envelope/stops.py` ; IC en ATR et effet apparié dans `src/envelope/metrics.py` ;
  - 9 tests nouveaux dans `tests/test_envelope.py`.

#### 0. Cadrage obligatoire
- **QUESTION :** à H fixé, un stop intrabarre en prix, SL-A (k · ATR14(t) de open[t + 1]) ou SL-B (extremum causal du segment qualifiant ± δ · ATR14(t)) :
  - coupe-t-il la queue gauche de R1 hors Q4, F1 et F5 (H ∈ {6, 13, 26}) et redresse-t-il leur espérance ?
  - protège-t-il F2b, F3 et R2 hors Q4 (H ∈ {13, 26, 48}) sans amputer la queue droite ?
- **PERTINENCE POUR LE FILTRE AKF :** R1 a une lourde queue gauche sans stop ; F2b et F3 portent une queue droite mais n'entrent pas au même point du range.
- **CE QUE LE PROTOCOLE MESURE RÉELLEMENT :** l'effet marginal du stop face au contrôle sans stop de C01, net de 5 et 10 bps. L'effet pur (entrées figées) est séparé de l'effet de réouverture (séquentiel dynamique). Les IC 95 % sont en bps et en ATR (bootstrap de grappes mensuelles, 2 000 tirages).
- **CE QU'IL NE PERMET PAS DE CONCLURE :**
  - l'effet d'un take-profit, d'un break-even, d'un filtre macro ou du multiplexage R1 + R2 ;
  - une validation hors échantillon ;
  - 198 paires par lecture : la meilleure est optimiste.

#### 1. Hypothèse & Motivation physique
- R1 : un stop près de l'extremum coupe-t-il les reprises de tendance ou les trajectoires qui auraient fini dans le sens du signal (`RESEARCH_INSIGHTS.md` §5 Q1) ?
- F2b et F3 : un stop large protège-t-il le capital (trou d'air de F3 en 2024) sans couper les gagnants ?

#### 2. Règle testée (OFAT)
- **Entrée :** open[t + 1], une position à la fois ; sous-ensembles figés de B01 et C01.
- **Sortie :** open[t + 1 + H], ou stop intrabarre plus tôt.
  - SL-A : k ∈ {1 ; 1,5 ; 2 ; 2,5 ; 3 ; 4 ; 5}.
  - SL-B : δ ∈ {0 ; 0,25 ; 0,5 ; 1}, plancher à 0,25 ATR de open[t + 1].
  - Exécution certifiée `apply_stop` : barre d'entrée comprise, gap à l'ouverture.
- **Contrôle :** la même configuration sans stop. Les 24 lignes communes avec C01 sont identiques ; l'ancre P6.5d est reproduite sans stop et avec stop à 2,5 %.
- **Deux lectures :** entrées figées (effet pur) et séquentiel dynamique (le stop libère la position ; le signal de la clôture de la barre du stop est admissible).
- **Écart au cadrage :** SL-B prend l'extremum sur [t − prev_seg_len, t], celui de `retrace_ratio`, et non [t − prev_seg_len + 1, t].
  - Les deux fenêtres diffèrent pour 932 signaux sur 7 296 (25 % de R2 hors Q4), de 0,24 ATR en médiane.
  - Avec la fenêtre littérale, les espérances bougent d'au plus 0,05 ATR ; les conclusions sont inchangées.

#### 3. Résultats nets (5 bps, séquentiel dynamique ; PnL et drawdown à 0,25 % par ATR)
| Métrique | F2b H26 sans stop | F2b H26 SL-A 5 | F3 H26 sans stop | F3 H26 SL-B extremum | R1 H13 SL-A 2 |
|---|---|---|---|---|---|
| PnL Net Total | +72 % (1x : +78 % ; +7 345 bps) | +38 % | +16 % | +36 % | +2 % |
| Profit Factor : 1x ; pondéré | 1,17 ; 1,28 | 1,11 ; 1,16 | 1,13 ; 1,08 | 1,18 ; 1,19 | 1,02 ; 1,02 |
| Win Rate | 49,6 % | 48,0 % | 47,4 % | 36,5 % | 45,6 % |
| Espérance / trade : bps [IC] ; ATR [IC] | +11,5 [−2,9 ; +26,0] ; +0,389 [+0,079 ; +0,700] | +7,5 ; +0,244 [−0,063 ; +0,544] | +9,3 ; +0,144 [−0,293 ; +0,548] | +10,4 ; +0,202 [−0,106 ; +0,520] | +1,1 ; +0,013 [−0,102 ; +0,135] |
| Espérance ATR à 10 bps | +0,255 [−0,056 ; +0,569] | +0,110 | +0,003 | +0,062 | −0,107 |
| Max Drawdown valorisé | −13,2 % | −12,9 % | −33,7 % | −12,9 % | −21,5 % |
| Nombre de trades | 639 (8,9/mois) | 640 ; 18 % stoppés | 601 (8,3/mois) | 620 ; 50 % stoppés | 1 513 (21,0/mois) ; 35 % stoppés |
| Durée médiane | 26 barres | 26 | 26 | 26 | 13 |
| Part des frais (1x) | 30 % | 40 % | 35 % | 32 % | 82 % |

#### 4. Analyse causale & Physique du trade
- [OBS] **Remarque du porteur vérifiée.** ATR14 médian des signaux : 80,3 bps en 2021, 33,6 en 2023. En ATR, deux contrôles sans stop ont un IC 95 % entièrement positif à 5 bps, timing compris : F2b · x1 hors Q4 H26 (+0,389 [+0,079 ; +0,700]) et R2 hors Q4 H26 (+0,354 [+0,051 ; +0,643]). À 10 bps, leurs IC contiennent 0. La moyenne de F2b résiste à la winsorisation P1/P99. F5, positif en bps à H6 et H13, est négatif en ATR.
- [OBS] **R1, F1, F5.**
  - 3 effets purs sur 99 ont un IC > 0 (+0,05 à +0,07 ATR, niveau du hasard) ; aucun stop ne donne d'IC > 0 en séquentiel.
  - Les gains de F1 (jusqu'à +0,087 ATR) ne résistent pas à la winsorisation.
  - Le stop coupe la queue gauche (R1 H26 : P10 −4,7 → −1,6 ATR) mais fait passer la médiane de +0,09 à −0,81 ATR : une partie des trajectoires coupées aurait fini dans le sens du signal.
  - Le drawdown baisse (R1 H26 : −44 % → −26 %). À 10 bps, tout le groupe est négatif ; F5 H26 a un IC < 0 avec 7 règles sur 11.
- [OBS] **F2b H26 : chaque stop dégrade.** L'effet pur a un IC < 0 pour 10 règles sur 11 (−0,22 à −0,38 ATR par trade) ; seul SL-A 5 fait −0,15 [−0,35 ; +0,04]. Le drawdown ne s'améliore pas, et les gains de 2023-2025 disparaissent.
- [OBS] **F3 H26 : un stop large protège.** Avec SL-A 2 ATR ou SL-B à l'extremum :
  - drawdown −34 % → −13 % ;
  - PnL +16 % → +33 et +36 % ;
  - 6 années positives sur 6 ;
  - 2024 : −1,00 → +0,04 ATR par trade.

  L'effet pur, +0,09 ATR, a un IC qui contient 0.
- [OBS] **R2 hors Q4** mêle les deux réponses. À H26, 7 règles dégradent significativement ; SL-A 5 ATR garde +0,286 ATR [+0,019 ; +0,562].
- [OBS] **Réouverture.** Les trades débloqués par un stop sont positifs pour R1 (jusqu'à +0,43 ATR) et négatifs pour F3 (−0,2 à −1,0 ATR). Les gaps sont négligeables (≤ 0,4 % des trades).
- [HYP] Le point d'entrée dans le range décide de l'effet du stop.
  - F2b, entré au milieu du range, gagne après des excursions adverses de 1 à 3 ATR : le stop coupe ses gagnants.
  - F3, entré près de l'extrémité opposée, échoue franchement : le stop coupe l'échec.
  - L'avantage de R1 dans B01 était une médiane, pas une espérance.
- **Relecture (2026-09-29)**, revue indépendante transmise par le porteur. Tous ses chiffres sont recalculés avec le moteur du dépôt et retrouvés à 1 % près (rapport §5).
  - **F2b, balayage de liquidité.** 53,7 % des trades ont une excursion adverse ≥ 2 ATR. Laissés courir, ils finissent à −1,38 ATR brut, et 25 % finissent positifs. Un stop à 2 ATR coûte 0,62 ATR par trade stoppé.
  - **F3, breakout invalidé.** Les 50 % de trades qui touchent l'extremum finissent à −2,21 ATR sans stop ; les autres à +2,68.
  - **F3, Long et Short positifs avec stop aux trois horizons** (estimations centrales). À H26, avec SL-B : +0,17 / +0,24 ATR, contre +0,27 / −0,02 sans stop.
  - **R2 hors Q4 stoppé n'est pas un pic isolé à H26.** Avec la même règle (SL-B), il fait +0,08, +0,17 et +0,18 ATR à H13, H26 et H48 ; aucun IC n'exclut 0.
  - **La lecture « entrées figées » est une règle causale de cooldown** (à plat jusqu'à t + 1 + H après un stop). F3 H26 SL-B y fait +0,236 ATR et +41 %, contre +0,202 et +36 % en réouverture.
  - **F5 :** 5 bps coûtent 0,135 ATR par trade. Des barrières symétriques de ±1 à ±2 ATR laissent l'espérance nette entre −0,07 et −0,02 ATR (niveau signal).
  - **Assemblage R2 hors Q4 H26, F2b sans stop + F3 SL-B** (vérification, hors protocole) :
    - 5 bps : +0,369 ATR [+0,098 ; +0,645], +12,3 bps [+0,2 ; +24,4], +138 %, drawdown −13,5 %, 6 années positives sur 6 ;
    - 10 bps : +0,233 ATR [−0,041 ; +0,511], +72 %, 5 années sur 6.

    Le gain sur R2 uniforme porte sur le drawdown (−20,5 % → −13,5 %), pas sur l'espérance : effet apparié +0,015 ATR [−0,108 ; +0,141]. Règle choisie dans l'échantillon, à confirmer en C02bis.

#### 5. Décision
- [ ] **REJETÉ**
- [ ] **NON CONCLUANT**
- [x] **À POURSUIVRE**, par sous-famille :
  - F2b · x1 déjà retourné hors Q4 : sortie à H26 sans stop ; si un stop de catastrophe est exigé, SL-A 5 ATR est le moins coûteux ;
  - F3 · x1 déjà retourné hors Q4 : SL-B à l'extremum ou SL-A 2 ATR, à H26 ;
  - R2 hors Q4, traité comme un bloc : sans objet ;
  - R1, F1, F5 : non concluant à rejeté (aucune espérance positive avec stop ; tout négatif à 10 bps).
- **Décisions du porteur (2026-09-29, cadrage de C02bis) :**
  - rejet définitif de R1, F1 et F5 ; `x1_already_flipped_at_t` vrai devient un prérequis d'entrée, avec les vetos R3 et `nis_z_100` Q4 ;
  - routage causal de R2 hors Q4 : F2b sans stop, F3 avec son propre stop ;
  - réentrée après un stop comme facteur (cooldown jusqu'à t + 1 + H contre réouverture) ;
  - plateau d'horizon autour de 26 barres et seuils causaux ;
  - frais de 5 et 10 bps ; hold-out scellé jusqu'à la fin de l'Étape D.

### [EXP-C02bis] — Moteur de régimes sur R2 hors Q4 : une enveloppe par sous-famille
- **Date :** 2026-09-29
- **Étape :** C Enveloppe (assemblage après C02)
- **Actif & Période :** BTC/USD Bitstamp 30m, 2020-01 → 2025-12 (72 mois) ; 2026, ETH et XRP non lus
- **Modèle de frais :** 5 et 10 bps aller-retour. Capital à 0,25 % par ATR14(t), levier ≤ 1x ; 1x en référence.
- **Livrables :**
  - `experiments/C02bis/rapport_C02bis.md`, `resultats_C02bis.csv` (284 lignes), `annuel_C02bis.csv`, `controles_C02bis.json`, 4 figures ;
  - `rule_levels`, `route_levels` et niveaux NaN (sans stop) dans `src/envelope/stops.py` ;
  - 2 tests nouveaux.

#### 0. Cadrage obligatoire
- **QUESTION :** en séquentiel global (une position à la fois), le moteur de régimes différencié forme-t-il un assemblage causal cohérent ? Il route F2b vers une sortie à H sans stop et F3 vers un stop propre, avec cooldown après stop.
  - Fait-il mieux que F2b seul et que R2 uniforme ?
  - H = 26 est-il un plateau ?
  - Le cooldown fait-il mieux que la réouverture ?
  - Que coûte un stop de catastrophe sur F2b ?
  - Tient-il avec des seuils causaux ?
- **PERTINENCE POUR LE FILTRE AKF :** `retrace_ratio`, connu à t, sépare F2b et F3, qui répondent en sens contraire au stop (C02).
- **CE QUE LE PROTOCOLE MESURE RÉELLEMENT :**
  - les 8 métriques nettes, les IC 95 % en bps et en ATR, le Long / Short, la contribution par sous-famille, les années et le Calmar ;
  - l'effet apparié face à R2 uniforme sur les mêmes entrées ;
  - l'écart entre cooldown et réouverture, et les masques recalculés avec des seuils causaux.
- **CE QU'IL NE PERMET PAS DE CONCLURE :**
  - une validation hors échantillon : les règles de F2b et F3 ont été choisies après C02 ;
  - un plateau au sens de l'Étape D ;
  - l'effet d'un take-profit, d'un break-even ou d'un filtre macro ;
  - un H propre à chaque sous-famille.

#### 1. Hypothèse & Motivation physique
- Router F2b et F3 selon leur réponse au stop doit garder la queue droite de F2b et couper les échecs de breakout de F3. Le cooldown doit éviter de reprendre le signal suivant dans une structure qui vient d'échouer.

#### 2. Règle testée (OFAT)
- **Entrée :** signaux de R2 hors `nis_z_100` Q4 (vetos : x1 non retourné, R3, Q4), une position à la fois pour tout le moteur.
- **Sortie :** open[t + 1 + H], H ∈ {13, 20, 24, 26, 28, 32, 48}. Stop par sous-famille :
  - RE-1 : F2b sans stop, F3 SL-B à l'extremum ;
  - RE-2 : F2b sans stop, F3 SL-A 2 ATR ;
  - RE-3 : F2b SL-A 5 ATR, F3 SL-B.

  Après un stop, cooldown ou réouverture. RE-4 : C1, C2, RE-1 et RE-2 avec des seuils causaux.
- **Contrôles :** C1 = F2b seul sans stop ; C2 = R2 hors Q4 uniforme sans stop. Tous deux sont identiques à C02 ; le moteur avec la même règle partout redonne la règle uniforme de C02 (36 lignes identiques).

#### 3. Résultats nets (H26, 5 bps, lecture cooldown ; PnL et drawdown à 0,25 % par ATR)
| Métrique | C1 : F2b seul | C2 : R2 uniforme | RE-1 | RE-2 | RE-3 |
|---|---|---|---|---|---|
| PnL Net Total | +72 % | +122 % | +138 % (1x +204 %) | +132 % | +96 % |
| Profit Factor : 1x ; pondéré | 1,17 ; 1,28 | 1,18 ; 1,23 | 1,20 ; 1,28 | 1,19 ; 1,27 | 1,16 ; 1,22 |
| Win Rate | 49,6 % | 49,4 % | 44,3 % | 43,9 % | 43,6 % |
| Espérance ATR [IC] | +0,389 [+0,079 ; +0,700] | +0,354 [+0,051 ; +0,643] | +0,369 [+0,098 ; +0,645] | +0,353 [+0,084 ; +0,625] | +0,288 [+0,045 ; +0,545] |
| Espérance bps [IC] | +11,5 [−2,9 ; +26,0] | +12,3 [−1,5 ; +25,8] | +12,3 [+0,2 ; +24,4] | +11,7 [−0,4 ; +24,2] | +10,1 [−1,3 ; +22,1] |
| Espérance ATR à 10 bps | +0,255 | +0,218 | +0,233 [−0,041 ; +0,511] | +0,217 | +0,153 |
| Max Drawdown valorisé ; Calmar | −13,2 % ; 0,72 | −20,5 % ; 0,69 | −13,5 % ; 1,16 | −13,1 % ; 1,14 | −15,4 % ; 0,77 |
| Nombre de trades | 639 (8,9/mois) | 1 080 (15,0/mois) | 1 080 ; 24 % stoppés | 1 080 ; 25 % | 1 080 ; 33 % |
| Durée médiane | 26 barres | 26 | 26 | 26 | 26 |
| Part des frais (1x) | 30 % | 29 % | 29 % | 30 % | 33 % |

#### 4. Analyse causale & Physique du trade
- [OBS] **RE-1 a la même espérance que R2 uniforme.** Effet apparié : +0,015 ATR [−0,108 ; +0,141], et aucun horizon n'est significatif.
  - Il réduit le risque : drawdown −20,5 % → −13,5 %, Calmar 0,69 → 1,16.
  - Ses 6 années sont positives, 2024 comprise (+15 % contre −3 %).
  - Long / Short +0,46 / +0,27 ATR.
- [OBS] **Plateau.**
  - L'IC en ATR de RE-1 est positif de H20 à H32.
  - Entre H24 et H28, l'espérance varie de moins de 0,05 ATR et le PnL va de +112 à +138 %.
  - À H13 et H48, aucune configuration n'a d'avantage.
- [OBS] **Cooldown.** Il fait mieux que la réouverture jusqu'à H32 : les trades débloqués après un stop font −0,15 à −1,38 ATR. L'écart s'inverse à H48.
- [OBS] **RE-3.** Le stop de catastrophe sur F2b coûte environ 0,08 ATR par trade (significatif à H20 et H24) et augmente le drawdown.
- [OBS] **RE-4, seuils causaux.** RE-1 garde un IC positif en ATR (+0,34 à +0,37), 6 années positives sur 6 et un drawdown de −12 à −14 %. En revanche, son IC positif en bps disparaît dès qu'on retire le 13 janvier-9 juin 2020, même avec les seuils de l'échantillon entier.
- [HYP] Le moteur gère le risque ; l'espérance vient de la sortie à 26 barres et de l'éviction de Q4. Le cooldown évite de reprendre le signal suivant dans un breakout qui vient d'échouer.

#### 5. Décision
- [ ] **REJETÉ**
- [ ] **NON CONCLUANT**
- [x] **À POURSUIVRE :**
  - RE-1 en lecture cooldown, à H = 26, devient la configuration de référence ;
  - RE-2 est une variante équivalente ;
  - RE-3 est rejeté, et le cooldown retenu.

  Points à trancher par le porteur :
  - la suite de l'Étape C (break-even ou take-profit, mesurés d'abord sur les mêmes entrées ; filtre macro) ;
  - un H propre à chaque sous-famille ;
  - le passage à l'Étape D ;
  - l'hypothèse d'exécution (à 10 bps, l'IC contient 0) ;
  - le hold-out.
- **Relecture et décisions du porteur (2026-09-29, cadrage de C03), vérifiées :**
  - **RE-1 validé officiellement** comme configuration de référence de l'Étape C : F2b sans stop, F3 SL-B 0, pyramiding 0, cooldown jusqu'à t + 1 + H.
  - **H = 26, commun aux deux sous-familles, est verrouillé.** À H28, F2b monte (+0,569 ATR), mais F3 baisse (+0,148), le DD passe à −16,2 % (et non −16,0 %) et le Calmar à 0,92. Deux horizons choisis après lecture seraient du cherry-picking dans l'échantillon, avec un paramètre libre de plus.
  - **Correction de l'annualisation des variantes RE-4.** Elles commencent au 501e signal, le 9 juin 2020 à 20 h 30 UTC, et non le 18 mai. Le Calmar et la cadence sont donc annualisés sur 5,56 ans, non 6 (ni 5,62). Calmar de RE-1 à H26 :
    - seuils glissants : 1,21 (+15,1 % par an, DD −12,4 %) ; le porteur avait estimé 1,20 ;
    - échantillon entier après l'amorce : 1,14 ;
    - seuils expansifs : 1,00.
  - **Filtrage mutuel sous pyramiding 0** (annexe H du rapport). Un signal contraire à la position ouverte de l'autre sous-famille est ignoré, et ces signaux perdaient quand on les jouait seuls :
    - F3 contre un F2b ouvert : 59 trades, −1,22 ATR sans stop, −0,49 ATR avec SL-B ;
    - F2b contre un F3 ouvert : 44 trades, −0,38 ATR.

    F2b passe ainsi de +0,389 à +0,459, et F3 SL-B de +0,236 à +0,267 (+0,144 → +0,235 sans stop). La hausse de F3 de +0,144 à +0,267 citée par le porteur cumule le stop et le filtrage.
  - **Take-profit fixe exclu**, ce qui est vérifié en EXP-C03 (annexe H). Le break-even différé est testé en EXP-C03.

### [EXP-C03] — Break-even différé sur RE-1
- **Date :** 2026-09-29
- **Étape :** C Enveloppe (un facteur OFAT sur la configuration de référence)
- **Actif & Période :** BTC/USD Bitstamp 30m, 2020-01 → 2025-12 (72 mois) ; 2026, ETH et XRP non lus
- **Modèle de frais :** 5 et 10 bps aller-retour. Le break-even est à open[t + 1] ± 5 bps dans les deux cas. Capital à 0,25 % par ATR14(t), levier ≤ 1x ; 1x en référence.
- **Livrables :**
  - `experiments/C03/rapport_C03.md`, `resultats_C03.csv` (228 lignes), `annuel_C03.csv`, `controles_C03.json`, 4 figures ;
  - `breakeven_trigger_levels` et `breakeven_trades` dans `src/envelope/stops.py` ;
  - 7 tests nouveaux (suite : 194 réussis, 2 ignorés).

#### 0. Cadrage obligatoire
- **QUESTION :** remonter le stop au point d'entrée après une excursion favorable de +m · ATR14(t) économise-t-il plus sur les trades devenus perdants qu'il ne coûte sur les grands gagnants repassés par l'entrée ?
  - Sur quel périmètre : F3, F2b ou les deux ?
  - Pour quel m ∈ {1 ; 1,5 ; 2 ; 2,5 ; 3 ; 4} ?
- **PERTINENCE POUR LE FILTRE AKF :** l'espérance de RE-1 vient de la queue droite des breakouts de compression. Le break-even est la seule protection de gain qui ne plafonne pas les gagnants ; le porteur a exclu le take-profit fixe.
- **CE QUE LE PROTOCOLE MESURE RÉELLEMENT :**
  - l'effet apparié BE − RE-1 sur les mêmes 1 080 entrées (cooldown), en ATR et en bps, avec IC ;
  - les trades sauvés contre les trades coupés, la queue droite ;
  - le drawdown, sur des chemins réordonnés par mois ;
  - les 8 métriques à 5 et 10 bps, les années, le plateau H24-28 ;
  - en annexe : la réouverture et la borne optimiste d'un take-profit fixe.
- **CE QU'IL NE PERMET PAS DE CONCLURE :**
  - une validation hors échantillon ;
  - l'effet d'un break-even décalé, d'un trailing stop ou d'une sortie partielle ;
  - le choix d'un m après lecture.

#### 1. Hypothèse & Motivation physique
- Sur RE-1, 24,9 % des trades atteignent +1,5 ATR de MFE26 puis finissent en perte nette, à −1,99 ATR en moyenne.
- Un break-even différé pourrait récupérer ces pertes, à condition que les grands gagnants ne repassent pas eux aussi par l'entrée.

#### 2. Règle testée (OFAT)
- **Entrée :** celle de RE-1, inchangée. En lecture cooldown, les entrées sont les mêmes.
- **Sortie :** celle de RE-1, plus un break-even.
  - Seuil : open[t + 1] ± m · ATR14(t), lu sur les barres t + 1 … t + H − 1. Le stop initial prime sur la même barre.
  - Stop remonté à open[t + 1] ± 5 bps, de b + 1 à t + H.
  - Périmètres : V1 = F3, V2 = F2b, V3 = les deux.
  - m ∈ {1 ; 1,5 ; 2 ; 2,5 ; 3 ; 4} ; H ∈ {24, 26, 28}.
- **Contrôle :** RE-1 à H = 26 en cooldown, identique à C02bis trade par trade.

#### 3. Résultats nets (H26, 5 bps, cooldown ; PnL et drawdown à 0,25 % par ATR)
| Métrique | RE-1 | V1 (F3), m = 2 | V2 (F2b), m = 2 | V3, m = 1 | V3, m = 2 | V3, m = 4 |
|---|---|---|---|---|---|---|
| PnL Net Total | +138 % (1x +204 %) | +128 % | +136 % | +63 % | +126 % | +149 % |
| Profit Factor (1x) | 1,20 | 1,18 | 1,22 | 1,17 | 1,21 | 1,21 |
| Win Rate | 44,3 % | 40,6 % | 39,0 % | 22,6 % | 35,3 % | 42,5 % |
| Espérance ATR [IC] ; bps | +0,369 [+0,098 ; +0,645] ; +12,3 | +0,354 ; +10,6 | +0,365 ; +12,4 | +0,212 ; +6,2 | +0,350 [+0,142 ; +0,570] ; +10,6 | +0,398 [+0,151 ; +0,649] ; +12,7 |
| Effet apparié ATR [IC] | — | −0,015 [−0,089 ; +0,047] | −0,004 [−0,082 ; +0,089] | −0,157 [−0,318 ; +0,007] | −0,018 [−0,131 ; +0,105] | +0,030 [−0,035 ; +0,118] |
| Max Drawdown ; Calmar | −13,5 % ; 1,16 | −13,1 % ; 1,13 | −12,9 % ; 1,19 | −15,5 % ; 0,55 | −11,7 % ; 1,25 | −14,5 % ; 1,13 |
| Nombre de trades ; sortis au BE | 1 080 (15,0/mois) ; — | 1 080 ; 12 % | 1 080 ; 13 % | 1 080 ; 54 % | 1 080 ; 25 % | 1 080 ; 6 % |
| Durée médiane | 26 | 26 | 26 | 12 | 26 | 26 |
| Part des frais (1x) | 29 % | 32 % | 29 % | 45 % | 32 % | 28 % |

#### 4. Analyse causale & Physique du trade
- [OBS] **Aucun seuil n'améliore l'espérance.**
  - m ≤ 1,5 : effet négatif sur F2b et sur les deux sous-familles ; significatif à H24 et H28 pour V2 à m = 1.
  - m ≥ 2 : −0,021 à +0,030 ATR, IC d'environ ±0,1, aux trois horizons.
  - V1 : proche de 0 partout.
- [OBS] **Sauvés contre coupés (V3, m = 2).** 147 trades sauvés (+1,98 ATR chacun) contre 121 coupés (−2,57), soit +0,270 contre −0,288 ATR par trade. 36 coupés finissaient au-delà de +3 ATR ; ils coûtent à eux seuls 0,206 ATR par trade.
- [OBS] **Queue droite.**
  - RE-1 : P90 à +5,53 ATR ; le décile supérieur apporte 0,92 ATR par trade, plus que l'espérance totale.
  - Le break-even l'ampute d'autant plus que m est bas : pour V3 à m = 1, le P90 tombe à +3,85.
- [OBS] **Drawdown.**
  - V3 à m = 2 le fait baisser aux trois horizons (−13,5 → −11,7 % à H26), mais sans significativité : +1,6 point [−2,1 ; +11,6] sur les chemins réordonnés, moins profond dans 89 % des chemins.
  - Le MDD ne varie pas de façon monotone avec m.
- [OBS] **Take-profit fixe : la décision du porteur est vérifiée.** Même la borne optimiste reste sous RE-1 : +0,200 à +0,347 ATR contre +0,369.
- [OBS] **Réouverture.** Les trades débloqués perdent dans les 19 configurations ; le cooldown est confirmé.
- [HYP] Le break-even ne distingue pas le retest de l'échec. Un trade activé sur deux repasse par l'entrée, et ceux qui repartent ensuite valent ceux qu'il sauve. La sortie à H26 et le cooldown font déjà l'essentiel de la gestion du risque.

#### 5. Décision
- [x] **REJETÉ pour m ≤ 1,5 :** le break-even ampute la queue droite et dégrade l'espérance.
- [x] **NON CONCLUANT pour m ≥ 2 :** l'effet sur l'espérance est nul et la baisse du drawdown n'est pas significative.

  Le break-even n'est donc pas retenu (critère du porteur), et RE-1 reste intact. L'exclusion du take-profit fixe est confirmée.
- [ ] **À POURSUIVRE**

  Points à trancher par le porteur :
  - la suite : le filtre macro (dernier facteur de l'Étape C) ou l'Étape D ;
  - l'hypothèse d'exécution : à 10 bps, l'IC de RE-1 contient 0.

### [EXP-C03, analyse approfondie] — Break-even : alpha contre gestion du risque (relecture du porteur)
- **Date :** 2026-09-29
- **Étape :** C Enveloppe. Relecture de C03 intégrant l'analyse de Gemini ; aucune règle nouvelle, RE-1 inchangé.
- **Actif & Période :** BTC/USD Bitstamp 30m, 2020-01 → 2025-12 ; 2026, ETH et XRP non lus.
- **Modèle de frais :** 5 et 10 bps, présentés séparément ; capital à 0,25 % par ATR14(t). Stress : glissement du seul break-even de 0, 5 et 10 bps.
- **Livrables :**
  - code, en commit séparé (547af84) : `be_slippage_bps` dans `breakeven_trades` et un test (195 réussis) ;
  - `experiments/C03/run_C03_approfondi.py`, `rapport_C03_approfondi.md` (sections A à I), `approfondi_C03.json`, `diagnostic_2022_C03.csv`, figures 5 à 8.

#### 0. Cadrage obligatoire
- **QUESTION :**
  - A, alpha : le break-even améliore-t-il E[ATR] ?
  - B, gestion du risque : garde-t-il une espérance comparable tout en réduisant de façon robuste le MDD, en améliorant le Calmar ou la robustesse aux frais ?
  - Points spécifiques : V3 à m = 2, glissement du break-even, 2022, asymétrie F2b / F3.
- **PERTINENCE POUR LE FILTRE AKF :** RE-1 est convexe. Son décile supérieur apporte 0,92 ATR par trade, pour une espérance de 0,369.
- **CE QUE LE PROTOCOLE MESURE RÉELLEMENT :**
  - l'effet apparié sur les 1 080 mêmes entrées, séparé de la performance absolue ;
  - le risque de chemin sur 2 000 chemins réordonnés par mois ;
  - un RE-1 réduit en taille jusqu'au même MDD ;
  - le glissement du seul break-even ;
  - un diagnostic trade par trade.
- **CE QU'IL NE PERMET PAS DE CONCLURE :**
  - une validation hors échantillon ;
  - un m choisi a posteriori ;
  - l'effet d'un glissement de tous les stops ;
  - une théorie de 2022 (46 sorties au break-even).

#### 1. Hypothèse & Motivation physique
- Sans alpha, le break-even pourrait encore servir la gestion du risque : tronquer les perdants après +2 ATR réduit la variance et le drawdown.

#### 2. Règle testée (OFAT)
- **Aucune règle nouvelle.** Ce sont les variantes de C03 (V1, V2, V3 × m) sur les mêmes entrées.
- **Un seul stress d'exécution :** le prix d'exécution du break-even de V3 à m = 2 est dégradé de 0, 5 ou 10 bps.
- **Règle de décision fixée avant les tests F à H :**
  - critère primaire (alpha) : effet apparié significativement positif pour entrer dans le baseline ;
  - critère secondaire (risque) : S1, espérance comparable ; puis S2 et S3, MDD et Calmar meilleurs dans toutes les lectures et démontrés à 95 % sur les chemins ; ou S4, IC > 0 à 10 bps aux trois horizons et sous glissement.

#### 3. Résultats nets (H26, 5 bps, cooldown ; PnL et drawdown à 0,25 % par ATR)
| Métrique | RE-1 | V3 m = 2, sans glissement | V3 m = 2, glissement 5 bps | V3 m = 2, glissement 10 bps |
|---|---|---|---|---|
| PnL Net Total (bps, 1x) | +138 % (+13 320) | +126 % (+11 475) | +108 % (+10 135) | +91 % (+8 795) |
| Profit Factor (1x) | 1,20 | 1,21 | 1,18 | 1,15 |
| Win Rate | 44,3 % | 35,3 % | 33,3 % | 33,3 % |
| Espérance ATR [IC] ; bps | +0,369 [+0,098 ; +0,645] ; +12,3 | +0,350 [+0,142 ; +0,570] ; +10,6 | +0,314 [+0,106 ; +0,534] ; +9,4 | +0,278 [+0,068 ; +0,501] ; +8,1 |
| Effet apparié ATR [IC] | — | −0,018 [−0,131 ; +0,105] | −0,054 [−0,168 ; +0,066] | −0,090 [−0,204 ; +0,027] |
| Max Drawdown ; Calmar | −13,5 % ; 1,16 | −11,7 % ; 1,25 | −11,8 % ; 1,10 | −12,0 % ; 0,95 |
| Nombre de trades ; sortis au BE | 1 080 (15,0/mois) ; — | 1 080 ; 25 % | 1 080 ; 25 % | 1 080 ; 25 % |
| Durée médiane | 26 | 26 | 26 | 26 |
| Part des frais (1x) | 29 % | 32 % | 35 % | 38 % |

À 10 bps, dans le même ordre :

| 10 bps | Espérance ATR [IC] | MDD | Calmar |
|---|---|---|---|
| RE-1 | +0,233 [−0,041 ; +0,511] | −15,9 % | 0,60 |
| V3 m = 2, sans glissement | +0,215 [+0,005 ; +0,437] | −13,4 % | 0,64 |
| V3 m = 2, glissement 5 bps | +0,179 [−0,035 ; +0,403] | −14,7 % | 0,48 |
| V3 m = 2, glissement 10 bps | +0,142 [−0,073 ; +0,370] | −16,1 % | 0,34 |

#### 4. Analyse causale & Physique du trade
- [CODE] **Contrôles.** Glissement nul identique à C03 ; effets additifs (V3 = V1 + V2, trade par trade) ; mécanique identique ; aucun `shift(-1)`. Tous les chiffres de la relecture sont confirmés aux arrondis près.
  - Précision : les 89 % et 92 % de chemins portent sur le MDD aux sorties des chemins réordonnés, les −14,2 → −11,2 % sur le MDD valorisé du chemin réel.
- [OBS] **Question A : aucun alpha.**
  - Aucun effet significativement positif, à aucun seuil ni horizon.
  - Effets significativement négatifs : V2 à m = 1 (H24, H28) et V3 à m = 1 (H24).
  - À m = 2, par sous-famille : F2b −0,007 [−0,156 ; +0,167], F3 −0,031 [−0,192 ; +0,101].
- [OBS] **Queue droite.** Gagnants de RE-1 à ≥ +3 ATR coupés par V3 : 39 % à m = 1, 17 % à m = 2, 5 % à m = 4 ; soit 39 %, 16 % et 4 % de leur contribution.
- [OBS] **Risque de V3 à m = 2.**
  - Sur le chemin réel, le MDD et le Calmar sont meilleurs dans les 6 lectures (3 horizons, 5 et 10 bps).
  - Sur les chemins réordonnés, le MDD est meilleur dans 82 à 92 % des cas et le Calmar dans 65 à 82 % : aucune des deux améliorations n'est démontrée à 95 %.
  - Les drawdowns sont moins profonds mais plus longs : 459 jours sous le pic contre 390.
  - À MDD égal, un RE-1 simplement réduit en taille (0,211 % par ATR) fait +13,5 % par an, contre +14,5 % pour V3.
- [OBS] **Frais.**
  - À 10 bps, l'IC de V3 à m = 2 passe au-dessus de 0 parce qu'il se resserre (erreur type 0,138 → 0,112), alors que l'espérance baisse.
  - P(E > 0) passe de 95,2 % à 97,7 %. Ce gain ne vaut qu'à H26 et disparaît avec 5 bps de glissement.
- [OBS] **Glissement.**
  - Le MDD reste plus bas à 5 bps de frais.
  - Le Calmar tombe sous celui de RE-1 dès 5 bps de glissement : à MDD égal, V3 fait alors −0,8 point par an face à RE-1 réduit, et −2,7 points à 10 bps de glissement.
  - Limite : seul le break-even glisse. V3 exécute 476 ordres stop contre 257 pour RE-1.
- [OBS] **2022.**
  - Effet −0,184 [−0,54 ; +0,13] : non distinct des autres années.
  - Il tient entièrement à deux gagnants F3 extrêmes coupés, +18,6 et +14,3 ATR dans RE-1, après des reculs de 0,12 et 0,44 ATR sous l'entrée. Sans eux, 2022 fait +0,006.
  - Le rapport sauvés / coupés, la MFE et la durée sont les mêmes que les autres années.
- [OBS] **F2b / F3.**
  - Sur F3, le SL-B plafonne déjà les pertes que le break-even pourrait sauver (−1,72 contre −2,30 ATR pour F2b).
  - Les 10 plus grands gains du break-even sont des F2b ; ses 2 plus grands coûts, des F3.
  - V2 à m = 2 équivaut à une réduction de taille (+0,3 point par an à MDD égal).
- [HYP] **Une exposition structurelle, pas un régime.** Le break-even, à l'entrée + 5 bps, se trouve dans la zone de retest des breakouts. Son coût dépend de la probabilité de couper l'un des rares gagnants extrêmes, qui portent l'espérance de RE-1. Il réduit la variance, pas le risque par unité de rendement.

#### 5. Décision
- [x] **REJETÉ (décision 1) : break-even rejeté, RE-1 conservé intact.**
  - Aucun alpha.
  - Aucun critère de gestion du risque n'est satisfait (S2, S3, S4).
  - À exécution réaliste, un RE-1 réduit en taille fait mieux, sans paramètre de plus.
- [ ] **NON CONCLUANT**
- [ ] **À POURSUIVRE**

  À ne pas retester sans élément nouveau : le break-even à l'entrée, et un m choisi a posteriori pour le risque.
- **Décision du porteur (2026-09-29, cadrage de C04) :** C03 est close et le break-even définitivement rejeté. RE-1 reste le baseline absolu. Les 4 commits sont poussés (origin = 47a3262).

### [EXP-C04] — Filtre de contexte macro : tendance et alignement
- **Date :** 2026-09-29
- **Étape :** C Enveloppe. Dernier facteur prévu, testé en OFAT sur RE-1.
- **Actif & Période :** BTC/USD Bitstamp 30m, 2020-01 → 2025-12 ; 2026, ETH et XRP non lus.
- **Modèle de frais :** 5 et 10 bps, séparés. Capital à 0,25 % par ATR14(t), 1x en référence.
- **Livrables :**
  - code, en commit séparé (eb8949f) : `src/context/trend.py` et 5 tests (200 réussis) ;
  - `experiments/C04/rapport_C04.md`, `resultats_C04.csv` (42 lignes), `annuel_C04.csv`, `controles_C04.json`, 4 figures.

#### 0. Cadrage obligatoire
- **QUESTION :** un signal de RE-1 (F2b ou F3) a-t-il une espérance asymétrique selon qu'il est aligné ou opposé à la tendance de fond ? Un veto contre-tendance retire-t-il du bruit toxique, ou les grands retournements ?
- **PERTINENCE POUR LE FILTRE AKF :** le déclencheur est un retournement de vitesse du Kalman. Une tendance plus lente pourrait séparer les vrais retournements des contre-mouvements. C'est le dernier point à trancher avant de figer la stratégie cœur.
- **CE QUE LE PROTOCOLE MESURE RÉELLEMENT :**
  - l'espérance des trades alignés et contre-tendance, et leur écart, avec IC sur les mêmes tirages ;
  - la part de la queue droite concernée ;
  - les 8 métriques en lecture séquentielle et figée ;
  - la décomposition en trades vétoés, perdus et ajoutés ;
  - le risque de chemin, la taille, le plateau, les années et l'asymétrie F2b / F3.
- **CE QU'IL NE PERMET PAS DE CONCLURE :**
  - une validation hors échantillon ;
  - l'effet de tendances à d'autres échelles ou de filtres non directionnels ;
  - un réglage des paramètres de tendance, exclu.

#### 1. Hypothèse & Motivation physique
- Un retournement de vitesse aligné sur la tendance lente serait plus fiable. Un signal contre-tendance serait un contre-mouvement voué à l'échec.

#### 2. Règle testée (OFAT)
- **Entrée :** celle de RE-1, avec un veto directionnel.
  - Un Long n'est autorisé que si la tendance est haussière, un Short que si elle est baissière.
  - Tendance à la clôture de la barre du signal :
    - V1 : close > EMA 200 ;
    - V2 : close > EMA 50 ;
    - V3 : signe de x1 du filtre v2.1 sur des bougies 4 h closes, valide après 300 bougies.
  - R0 = 1 000 sur 30 min a été écarté à la conception : ses régimes ne durent que 19 barres, contre 11 pour le filtre de base.
- **Sortie :** celle de RE-1, inchangée.
- **Contrôle :** RE-1, identique à C02bis trade par trade.
- **Règle de décision fixée avant le calcul :**
  - rejet si le filtre retire au moins proportionnellement le décile supérieur (R1), si l'espérance baisse (R2), ou s'il ne bat pas un RE-1 réduit en taille (R3) ;
  - adoption si, à la fois : le bruit contre-tendance est significativement négatif (A1), la variante tient à 10 bps (A2), le Calmar est robuste et démontré (A3), et l'IC reste > 0 (A4).

#### 3. Résultats nets (H26, 5 bps, lecture séquentielle ; PnL et drawdown à 0,25 % par ATR)
| Métrique | RE-1 | V1 : EMA 200 | V2 : EMA 50 | V3 : Kalman 4 h |
|---|---|---|---|---|
| PnL Net Total (1x ; bps) | +138 % (+204 % ; +13 320) | +46 % (+45 % ; +5 196) | +55 % (+16 % ; +3 094) | +38 % (+59 % ; +6 311) |
| Profit Factor (1x) | 1,20 | 1,12 | 1,06 | 1,14 |
| Win Rate | 44,3 % | 40,9 % | 41,3 % | 42,5 % |
| Espérance ATR [IC] ; bps | +0,369 [+0,098 ; +0,645] ; +12,3 | +0,216 [−0,099 ; +0,548] ; +7,5 | +0,260 [−0,036 ; +0,590] ; +4,0 | +0,237 [−0,045 ; +0,533] ; +9,5 |
| Max Drawdown ; Calmar | −13,5 % ; 1,16 | −13,3 % ; 0,49 | −17,1 % ; 0,44 | −13,6 % ; 0,41 |
| Nombre de trades | 1 080 (15,0/mois) | 696 (9,7/mois) | 774 (10,8/mois) | 663 (9,2/mois) |
| Durée médiane | 26 | 26 | 26 | 26 |
| Part des frais (1x) | 29 % | 40 % | 56 % | 34 % |

À 10 bps :

| 10 bps | RE-1 | V1 | V2 | V3 |
|---|---|---|---|---|
| Espérance ATR | +0,233 | +0,078 | +0,119 | +0,095 |
| PnL | +72 % | +18 % | +22 % | +13 % |
| Calmar | 0,60 | 0,17 | 0,19 | 0,13 |

#### 4. Analyse causale & Physique du trade
- [CODE] **Contrôles bloquants passés :** ancre P6.5d ; RE-1 = C02bis ; décomposition refermée. Tendances causales : bougie 4 h lue seulement une fois close, tests de troncature.
- [OBS] **Les trades contre-tendance ne sont pas toxiques.**
  - Espérance des trades contre-tendance, contre alignés :
    - V1 : +0,389 contre +0,352 ;
    - V2 : +0,398 contre +0,353 ;
    - V3 : +0,426 contre +0,317.
  - Aucun écart n'est significatif, et tous vont en faveur des contre-tendance.
- [OBS] **Ils portent les grands retournements.**
  - V3 retire 48 % du décile supérieur et 9 des 20 meilleurs trades.
  - Les Long contre la tendance 4 h font +0,640 ATR [+0,171 ; +1,083].
- [OBS] **F2b / F3.**
  - F2b contre-tendance est le meilleur groupe : +0,52 (V1), +0,58 (V3).
  - Pour F3, contre-tendance et aligné se valent. Le filtre prive surtout F2b de ses meilleurs trades.
- [OBS] **En séquentiel, la position libérée prend des signaux perdants.** Ce sont les signaux qui tombent pendant la fenêtre d'un trade vétoé : −0,48 (V1), −0,38 (V2), −0,05 ATR (V3).
- [OBS] **Risque, taille, plateau, années.**
  - Calmar meilleur dans 5 à 8 % des chemins seulement.
  - À MDD égal, face à RE-1 réduit : −8,9 à −10,8 points par an.
  - Moins bon que RE-1 à H24, H26 et H28.
  - V1 et V3 font passer 2022 en négatif.
- [HYP] **Le retournement de x1 anticipe déjà le changement de régime.** La tendance lente arrive après, et le veto interdit précisément les trades où le Kalman voit le tournant avant elle.
- [HYP] **Un signal consommé doit bloquer sa fenêtre**, même s'il n'est pas pris : c'est le même phénomène que le cooldown de C02bis.

#### 5. Décision
- [x] **REJETÉ pour V1, V2 et V3.**
  - Aucun bruit contre-tendance à éliminer (A1 non satisfait).
  - L'espérance est dégradée (R2) et le filtre ne fait pas mieux qu'une réduction de taille (R3).
  - V3 retire en plus au moins sa part de la queue droite (R1).
  - **RE-1 reste pur.**
- [ ] **NON CONCLUANT**
- [ ] **À POURSUIVRE**

  L'Étape C a testé ses quatre facteurs : horizon, stop par sous-famille, break-even, filtre macro. RE-1 est la stratégie cœur. Le porteur annonce C05 (sensibilité), puis l'Étape D (portabilité multi-actifs).
- **Décision du porteur (2026-09-29, cadrage de C05) :** C04 est close, le filtre macro rejeté, RE-1 reste pur. Les 2 commits sont poussés (origin = 1dba30c).
  - Deux formulations de la relecture sont nuancées ici, selon les mesures.
  - « Les trades contre-tendance constituent l'alpha majeur de la queue droite » : ils portent une part de la queue droite proche de leur poids.
    - Ils représentent 44 %, 35 % et 47 % des trades.
    - Ils font 43 %, 33 % et 48 % du décile supérieur, et 41 %, 32 % et 46 % de sa contribution.
    - Ils font 47 %, 35 % et 53 % des gains ≥ +3 ATR : un peu au-dessus de leur poids, surtout V3 (+5 points).
  - Le rejet tient à ce qu'ils ne sont pas toxiques, pas à ce qu'ils domineraient la queue droite.
  - « Le Kalman est en avance sur la tendance lente » : c'est l'hypothèse [HYP] de C04, compatible avec les mesures mais non démontrée.

### [EXP-C05] — Sensibilité globale de la stratégie cœur (RE-1)
- **Date :** 2026-09-29
- **Étape :** C Enveloppe. Diagnostic de robustesse avant l'Étape D, sans règle nouvelle.
- **Actif & Période :** BTC/USD Bitstamp 30m, 2020-01 → 2025-12 ; 2026, ETH et XRP non lus.
- **Modèle de frais :** 5 et 10 bps, séparés. Capital à 0,25 % par ATR14(t), 1x en référence.
- **Livrables :**
  - `experiments/C05/run_C05.py` ; aucun module de `src/` n'est modifié ;
  - `rapport_C05.md`, `resultats_C05.csv` (28 lignes), `annuel_C05.csv`, `controles_C05.json`, 4 figures.

#### 0. Cadrage obligatoire
- **QUESTION :** les trois seuils durs de RE-1 reposent-ils sur des plateaux ou sur des crêtes ?
  - frontière F2b / F3 à 0,85 de `retrace_ratio` ;
  - marge δ = 0 du stop de F3 ;
  - exclusion de `nis_z_100` au-delà de P75.
- **PERTINENCE POUR LE FILTRE AKF :** chaque seuil traduit une lecture physique du moteur (position dans le range, invalidation du breakout, choc d'innovation). Une crête signalerait un ajustement au bruit de BTC avant la portabilité.
- **CE QUE LE PROTOCOLE MESURE RÉELLEMENT :**
  - la sensibilité locale, un seuil à la fois, de l'espérance [IC], du PnL, du MDD et du Calmar, à 5 et 10 bps ;
  - l'écart à RE-1 : apparié pour A et B (mêmes entrées), sur les mêmes mois tirés pour C ;
  - les chemins réordonnés et l'équivalent en taille ;
  - les mécanismes, par bandes de retracement et de `nis_z_100`.
- **CE QU'IL NE PERMET PAS DE CONCLURE :**
  - une validation hors échantillon ;
  - les interactions entre seuils ;
  - la sensibilité des seuils non testés : coupure de `leg_atr`, borne 0,50, veto R3 ;
  - un meilleur réglage : aucun point n'est adopté.

#### 1. Hypothèse & Motivation physique
- Si les seuils traduisent des phénomènes physiques, la performance varie doucement autour d'eux. Si elle chute à un pas du seuil, celui-ci est calé sur le bruit.

#### 2. Règle testée (OFAT)
- **A :** frontière b ∈ {0,75 ; 0,80 ; 0,85 ; 0,90 ; 0,95}. F3 (SL-B 0) si `retrace_ratio` ≥ b, F2b sans stop sinon. Mêmes entrées que RE-1.
- **B :** SL-B δ ∈ {−0,25 ; 0 ; +0,25 ; +0,50} ATR pour F3 (δ < 0 : plus serré). Mêmes entrées.
- **C :** exclusion de `nis_z_100` au-delà de P70, P75, P80, P85 ou P90 (quantiles de l'atlas). Univers et chaîne recalculés.
- **Contrôle :** RE-1, identique à C02bis trade par trade.
- **Règle de lecture fixée avant le calcul :**
  - on lit les voisins immédiats de RE-1 ;
  - dégradation nette si (d1) écart ≤ −20 % de l'espérance de RE-1 avec IC < 0, (d2) espérance ou Calmar sous la moitié, ou (d3) MDD plus profond que 1,5 fois ;
  - plateau si aucun voisin ne se dégrade nettement, falaise si un seul, crête si les deux ;
  - falaise et crête sont signalées avant l'Étape D ; aucun voisin n'est adopté.

#### 3. Résultats nets (H26, 5 bps ; PnL et MDD à 0,25 % par ATR)
Huit métriques de RE-1 et de ses voisins immédiats :

| Métrique | RE-1 | A 0,80 | A 0,90 | B −0,25 | B +0,25 | C P70 | C P80 |
|---|---|---|---|---|---|---|---|
| PnL Net Total (1x) | +138 % (+204 %) | +119 % (+168 %) | +147 % (+192 %) | +137 % (+207 %) | +131 % (+186 %) | +116 % (+148 %) | +113 % (+153 %) |
| Profit Factor (1x) | 1,20 | 1,18 | 1,19 | 1,20 | 1,18 | 1,17 | 1,16 |
| Win Rate | 44,3 % | 42,9 % | 45,5 % | 43,2 % | 45,1 % | 44,3 % | 43,9 % |
| Espérance ATR ; bps | +0,369 ; +12,3 | +0,331 ; +11,1 | +0,391 ; +12,1 | +0,360 ; +12,4 | +0,355 ; +11,8 | +0,350 ; +10,8 | +0,310 ; +10,2 |
| Max Drawdown ; Calmar | −13,5 % ; 1,16 | −14,1 % ; 0,99 | −13,4 % ; 1,21 | −13,0 % ; 1,19 | −14,0 % ; 1,07 | −17,8 % ; 0,77 | −15,9 % ; 0,84 |
| Nombre de trades (/mois) | 1 080 (15,0) | 1 080 | 1 080 | 1 080 | 1 080 | 1 023 (14,2) | 1 139 (15,8) |
| Durée médiane | 26 | 26 | 26 | 26 | 26 | 26 | 26 |
| Part des frais (1x) | 29 % | 31 % | 29 % | 29 % | 30 % | 32 % | 33 % |

Grilles complètes : espérance ATR ; MDD ; Calmar.

| Grille | Point | 5 bps | 10 bps |
|---|---|---|---|
| A | 0,75 | +0,274 ; −19,2 % ; 0,58 | +0,138 ; −21,5 % ; 0,25 |
| A | 0,80 | +0,331 ; −14,1 % ; 0,99 | +0,195 ; −16,6 % ; 0,48 |
| A | **0,85 (RE-1)** | **+0,369 ; −13,5 % ; 1,16** | **+0,233 ; −15,9 % ; 0,60** |
| A | 0,90 | +0,391 ; −13,4 % ; 1,21 | +0,255 ; −15,8 % ; 0,64 |
| A | 0,95 | +0,396 ; −14,2 % ; 1,18 | +0,260 ; −16,6 % ; 0,64 |
| B | −0,25 | +0,360 ; −13,0 % ; 1,19 | +0,224 ; −15,1 % ; 0,63 |
| B | +0,25 | +0,355 ; −14,0 % ; 1,07 | +0,219 ; −16,4 % ; 0,54 |
| B | +0,50 | +0,333 ; −15,2 % ; 0,91 | +0,197 ; −17,6 % ; 0,45 |
| C | P70 | +0,350 ; −17,8 % ; 0,77 | +0,212 ; −20,0 % ; 0,40 |
| C | P80 | +0,310 ; −15,9 % ; 0,84 | +0,176 ; −18,0 % ; 0,40 |
| C | P85 | +0,238 ; −17,5 % ; 0,59 | +0,105 ; −20,1 % ; 0,20 |
| C | P90 | +0,219 ; −17,7 % ; 0,56 | +0,087 ; −20,7 % ; 0,16 |

#### 4. Analyse causale & Physique du trade
- [CODE] **Contrôles bloquants passés :**
  - ancre P6.5d ;
  - p = 0,75 et la frontière 0,85 redonnent l'univers et les sous-familles de B01 ;
  - RE-1 est identique à C02bis ;
  - le point RE-1 de chaque grille redonne RE-1 ;
  - A et B gardent les entrées de RE-1 ;
  - la décomposition de C est refermée à 10⁻⁹ près.
- [OBS] **A, plateau de 0,85 à 0,95, pente en dessous.**
  - Effets appariés : +0,022 (0,90) et +0,028 (0,95), non significatifs ; −0,038 à 0,80, non significatif ; −0,095 [−0,157 ; −0,030] à 0,75.
  - Par bande, le stop à l'extremum coûte 0,58 et 0,53 ATR par trade sur les retracements de 0,75 à 0,85, qui font +1,03 et +0,89 sans stop. Il n'est positif, sans être significatif, qu'au-delà de 0,95 (+0,14).
  - RE-1 est 3e sur 5.
- [OBS] **B, plateau de −0,25 à +0,25 ATR.**
  - Effets de −0,009 et −0,014 ATR, non significatifs ; +0,50 coûte 0,036 (IC en limite de 0).
  - Le plancher n'est jamais actif. δ = 0 était la valeur la plus serrée de C02 ; le côté plus serré est plat.
- [OBS] **C, RE-1 au sommet (1er sur 5), falaise côté permissif.**
  - Écarts sur les mêmes mois : P80 −0,059 [−0,117 ; −0,009] ; P85 −0,131 ; P90 −0,150, tous significatifs.
  - Les signaux admis perdent : −0,31, −0,53 et −0,29 ATR.
  - P70 : −0,019, non significatif. Les 72 trades retirés valaient +0,64 ATR. Son MDD de −17,8 % tient au chemin réel : P70 fait mieux dans 49 % des chemins réordonnés.
  - Par signal joué seul : +0,53 (P70-P75) contre −0,30 (P75-P80), avec des IC qui se recouvrent.
- [OBS] **Verdicts de la règle.** A et B : plateaux, à 5 et 10 bps. C : plateau en limite à 5 bps (−0,059 contre un seuil de −0,074), falaise à 10 bps (−0,057 contre −0,047).
- [OBS] **Années :** 5 ou 6 années positives sur 6 pour tous les points de grille ; 2021 reste l'année faible.
- [HYP] Le retour à l'extremum n'invalide le breakout qu'après un retracement presque complet de la jambe précédente ; en dessous, c'est un retest.
- [HYP] L'information du stop est une zone de ±0,25 ATR autour de l'extremum, pas un point.
- [HYP] Au-delà de P75, `nis_z_100` signale des déclenchements sur bougie de choc (K2), presque tous des F3 (74 à 96 %).

#### 5. Décision
- [ ] **REJETÉ**
- [ ] **NON CONCLUANT**
- [x] **À POURSUIVRE : RE-1 inchangé pour l'Étape D.**
  - Aucun point de grille n'est adopté. Les voisins meilleurs (A 0,90 et 0,95, B −0,25) sont non significatifs.
  - **Signalement formel :** l'exclusion de `nis_z_100` est une falaise côté permissif. C'est le seuil le plus sensible de RE-1, et le seul que la sélection de C01 a pu favoriser.
  - Proposition pour l'Étape D : garder la règle P75 sur les signaux de chaque actif (ou sa version causale), et publier l'espérance par bande de `nis_z_100` pour vérifier que la bascule reste au voisinage de P75.

### [EXP-D01] — Portabilité de RE-1 figée, sans réglage (SOL/USD, CFD or, CFD WTI)
- **Date :** 2026-09-30
- **Étape :** D Adaptation, D01. Expérience **descriptive** (décision du porteur) : aucun critère de réussite, aucun classement des actifs, aucune modification ni recalibration de RE-1.
- **Actif & Période :**
  - BTC/USD Bitstamp 2020-2025, en référence ;
  - SOL/USD Coinbase, du 2021-06-17 au 2025-12-31 ;
  - CFD or XAU/USD (HistData) 2020-2025 ;
  - CFD WTI (HistData) audité, puis **bloqué** avant backtest ;
  - 2026, ETH et XRP ni téléchargés ni lus.
- **Modèle de frais :** SOL 5 et 10 bps ; XAU 4 bps ; BTC 5 et 10 bps. Ce sont des frais d'exécution ; aucun stress de glissement. Capital à 0,25 % par ATR14(t) et notionnel 1x.
- **Livrables :**
  - code, deux commits séparés : `src/marketdata/` et `experiments/D01/donnees_D01.py` (commit `1f57997`) ; `src/strategy/re1.py` (commit `2b5b32c`) ; 19 tests ;
  - `experiments/D01/run_D01.py` (`--audit`, puis le run) ;
  - `rapport_D01.md`, `resultats_D01.csv`, `annuel_D01.csv`, `audit_D01.json`, `diagnostics_D01.json`, `controles_D01.json`, 3 figures.

#### 0. Cadrage obligatoire
- **QUESTION :** que devient RE-1, transférée telle quelle (seuils numériques de BTC, H = 26 barres, moteur v2.1 par défaut), sur des marchés de structures différentes ?
- **PERTINENCE POUR LE FILTRE AKF :**
  - le déclencheur est invariant d'échelle et les descripteurs de RE-1 sont en ATR14(t) et en z-score ;
  - le transfert teste si la cinématique R2 hors choc d'innovation existe ailleurs à paramètres identiques ;
  - les CFD ajoutent des trous de séance.
- **CE QUE LE PROTOCOLE MESURE RÉELLEMENT :**
  - les 8 métriques nettes aux frais de l'actif ;
  - l'espérance et le timing en ATR et en bps, avec IC par grappes mensuelles ;
  - le capital à 0,25 %/ATR et à 1x ;
  - Long/Short, F2b/F3, stops de F3, années, terciles de volatilité ;
  - `nis_z_100` face au seuil BTC, et ses bandes (trades isolés) ;
  - l'audit des données.
- **CE QU'IL NE PERMET PAS DE CONCLURE :**
  - pas de validation sur le hold-out ;
  - pas de comparaison statistique ni de classement ;
  - rien sur l'optimalité des seuils ni sur D02 ;
  - coûts réels des CFD non modélisés ;
  - sources et périodes différentes de BTC.

#### 1. Hypothèse & Motivation physique
- Si RE-1 capte une cinématique du moteur plutôt qu'une particularité de BTC 2020-2025, sa population et une partie de sa rente doivent se retrouver sur d'autres marchés, sans réglage.

#### 2. Règle testée (OFAT)
- **Règle :** RE-1 telle quelle, avec les seuils numériques de BTC gelés (option (a)) :
  - médiane de `leg_atr` = 2,8233 ;
  - P75 de `nis_z_100` = 1,2245 ;
  - frontières de `retrace_ratio` 0,50 et 0,85.
  - Les quantiles locaux sont publiés à titre descriptif seulement.
- **Contrôle :** BTC par la même chaîne (`strategy.re1`), identique à C02bis trade par trade.
- **Règle de lecture fixée avant le calcul :**
  - D01 est descriptif ;
  - seul motif de blocage : la validité technique ou la qualité des données ;
  - l'actif bloqué est documenté, jamais remplacé ;
  - régimes de volatilité, bandes de `nis_z_100` et effet du stop sont définis dans l'en-tête du script.

#### 3. Résultats nets (H26)
| Métrique | BTC 5 bps | SOL/USD 5 bps | SOL/USD 10 bps | CFD or 4 bps |
|---|---|---|---|---|
| PnL Net Total : 0,25 %/ATR ; 1x | +138 % ; +204 % | +39 % ; +173 % | +24 % ; +86 % | +0,6 % ; +5,4 % |
| Profit Factor (1x ; pondéré) | 1,20 ; 1,28 | 1,17 ; 1,16 | 1,12 ; 1,10 | 1,04 ; 1,01 |
| Win Rate | 44,3 % | 44,1 % | 43,4 % | 42,5 % |
| Espérance ATR [IC] ; bps [IC] | +0,369 [+0,098 ; +0,645] ; +12,3 [+0,2 ; +24,4] | +0,190 [−0,079 ; +0,484] ; +19,2 [−3,6 ; +44,2] | +0,129 [−0,140 ; +0,425] ; +14,2 [−8,6 ; +39,2] | −0,019 [−0,362 ; +0,349] ; +1,1 [−4,9 ; +7,5] |
| Max Drawdown : 0,25 %/ATR ; 1x | −13,5 % ; −43,9 % | −13,1 % ; −42,3 % | −15,2 % ; −44,4 % | −13,6 % ; −13,3 % |
| Nombre de trades (/mois) | 1 080 (15,0) | 769 (14,1) | 769 (14,1) | 651 (9,0) |
| Durée médiane | 26 barres (13 h) | 26 (13 h) | 26 (13 h) | 26 (13 h ; P90 20 h) |
| Part des frais (1x) | 29 % | 21 % | 41 % | 79 % |

- **Calmar :**
  - à 0,25 %/ATR : 1,16 / 0,58 / 0,32 / 0,01 ;
  - à 1x : 0,46 / 0,59 / 0,33 / 0,07.
- **BTC à 10 bps :** +0,233 ATR [−0,041 ; +0,511], +7,3 bps [−4,8 ; +19,4]. L'estimation est positive et son IC traverse zéro.

#### 4. Analyse causale & Physique du trade
- [CODE] **Contrôles bloquants passés :**
  - ancre P6.5d ;
  - seuils gelés égaux aux statistiques de l'atlas BTC ;
  - BTC par la chaîne D01 identique à C02bis : 1 080 trades, 40 métriques, écart relatif ≤ 4,5·10⁻⁶ ;
  - intégrité des quatre séries.
- [OBS] **Données :**
  - **SOL/USD.** Coinbase, bougies de 15 min agrégées en 30 min. Coté depuis le 2021-06-17 ; aucune place en USD liquide ne couvre 2020. Binance SOL/USDT a été écarté par le porteur, Binance.US (trous) et Bitstamp (tardif) aussi.
  - **XAU et WTI.** HistData, bid, courtier non divulgué. Dukascopy refuse les accès automatisés (« Bot blocked ») ; le blocage n'a pas été contourné.
  - **Fuseau HistData corrigé.** La FAQ annonce un EST fixe, mais l'horloge suit l'heure d'été européenne. Contrôle : la pause tombe à 17:00-18:00 heure de New York dans 303 semaines sur 314.
  - **Doublons HistData.** Une heure par an est répétée à l'identique ; ces doublons exacts sont supprimés.
- [OBS] **WTI bloqué.**
  - Couverture jusqu'au 2023-12-01 seulement, contre la consigne 2020-2025.
  - CFD de contrat du mois non ajusté, roulé autour de l'échéance : écart au spot EIA médian −0,02 $, corrélation 0,978 hors avril 2020 ; le 20 avril 2020, CFD 20,27 $ contre spot −36,98 $.
- [OBS] **La géométrie du déclencheur est la même sur les trois actifs,** alors que l'ATR14 médian vaut 50, 95 et 17 bps :
  - `leg_atr` P50 2,82 / 2,85 / 2,90 ;
  - `retrace_ratio` P50 0,62 / 0,60 / 0,59 ;
  - part au-dessus du seuil `nis_z_100` 25,0 / 27,3 / 24,9 %.
- [OBS] **SOL/USD : estimation positive, IC qui contient zéro.**
  - F2b +0,287, F3 +0,076 ATR ; Long +0,25, Short +0,14 ;
  - 5 années sur 5 positives en ATR ; 2025 fait +91 % à 1x ;
  - moyenne winsorisée P1/P99 : +0,139.
- [OBS] **CFD or : net nul.**
  - Brut +0,239 ATR (+5,1 bps), frais 0,257 ATR : un actif trop calme à 30 min pour 4 bps.
  - F2b −0,304 (F2b Short −0,704 [−1,402 ; −0,001]), F3 +0,313 (F3 Long +0,551).
  - Timing −0,05, dérive +0,38 : la hausse séculaire de l'or.
  - 2 années positives sur 6.
  - Dimensionnement plafonné à 1x pour 89 % des trades (ATR < 25 bps).
- [OBS] **Ce qui se retrouve partout :**
  - la queue droite : médiane −0,4 à −0,9 ATR ; le décile supérieur apporte +0,77 à +0,92 ATR par trade ;
  - le stop de F3 sert le risque, pas l'alpha : effet apparié ±0,03 non significatif, MDD réduit sur les trois actifs ;
  - le tercile agité est le plus faible sur BTC et SOL.
- [OBS] **La bascule de `nis_z_100` à P75 ne se reproduit pas telle quelle.** SOL : bande sous P70 positive (IC > 0) et bande au-delà de P90 positive. XAU : bandes nulles ou négatives.
- [HYP] **La population transfère, la rente dépend du marché.** Le brut vaut la moitié de celui de BTC sur SOL et sur l'or ; sur l'or, le rapport frais / ATR l'annule. C'est une question de vitesse (H, R0 ou unité de temps), pas un verdict sur le signal.

#### 5. Décision
- [ ] **REJETÉ**
- [ ] **NON CONCLUANT**
- [x] **À POURSUIVRE (descriptif) : RE-1 inchangée.**
  - Aucune recalibration n'est tirée de D01.
  - À trancher par le porteur :
    - le WTI : mesurer 2020-2023 sur HistData, fournir une autre source (OANDA, Dukascopy par AWS), ou retirer l'actif ;
    - la validation de la source XAU ;
    - le push.
  - Réflexions pour D02 dans le rapport (§8) : aucune fonction objectif ni aucun domaine n'est défini.

### [EXP-D01 bis] — Portabilité de RE-1 figée : ETF SPY et XLE, gaps d'ouverture (WTI retiré)
- **Date :** 2026-09-30
- **Étape :** D Adaptation, D01 bis. Descriptif, mêmes règles que D01 (aucun critère de réussite, aucun classement, RE-1 inchangée).
- **Décision du porteur :** le WTI est retiré (couverture HistData arrêtée au 2023-12-01 ; piste FXCM non aboutie, connexion au compte requise). Il est remplacé par l'ETF XLE, proxy de l'énergie sans roulement. L'ETF SPY est ajouté (marché actions, gaps d'ouverture).
- **Actif & Période :** SPY et XLE, séance régulière 09:30-16:00 heure de New York, 2020-01-02 → 2025-12-31 ; 1 508 séances, 19 532 barres chacun.
- **Modèle de frais :** 4 bps. Capital à 0,25 % par ATR14(t) et notionnel 1x.
- **Données :**
  - Alpaca, flux SIP, barres natives de 30 min ; séries ajustée (fractionnements et dividendes, mesurée) et brute (audit) ;
  - téléchargement lancé par le porteur avec ses clés en variables d'environnement ; aucune clé écrite.
- **Livrables :**
  - `src/marketdata/alpaca.py` et ses tests ;
  - `experiments/D01/run_D01.py` (analyse des gaps d'ouverture) ;
  - `rapport_D01.md` mis à jour (§2.4, §4.3-4.4, §5, annexe L).

#### 0. Cadrage obligatoire
- **QUESTION :** que devient RE-1, telle quelle, sur un marché actions en séances, et comment absorbe-t-elle les gaps d'ouverture ?
- **PERTINENCE POUR LE FILTRE AKF :**
  - le gap est une innovation d'une barre pour le Kalman ;
  - H = 26 compte des barres : sur une séance de 13 barres, il fait traverser deux nuits.
- **CE QUE LE PROTOCOLE MESURE RÉELLEMENT :**
  - les métriques de D01 ;
  - la taille des gaps (en bps et en ATR) et leur part du vrai range ;
  - les signaux sur barre d'ouverture et leur filtrage par `nis_z_100` ;
  - le rendement brut des trades décomposé en gaps traversés et gain en séance ;
  - les stops percés à l'ouverture ;
  - l'espérance selon la barre du signal.
- **CE QU'IL NE PERMET PAS DE CONCLURE :**
  - environ 2 trades par mois, donc des IC de ±0,6 ATR ;
  - XLE n'est pas le pétrole ;
  - aucune conclusion sur un H « en heures » ni sur D02.

#### 1. Hypothèse & Motivation physique
- Si RE-1 capte une cinématique intraséance, les gaps d'ouverture devraient soit la brouiller (signaux nés du gap), soit peser sur les positions tenues d'une séance à l'autre.

#### 2. Règle testée (OFAT)
- **Règle :** RE-1 identique à BTC (option (a)).
- **Contrôle :** BTC identique à C02bis (chaîne D01).
- **Définitions des gaps :** fixées avant le calcul, en tête du script.

#### 3. Résultats nets (H26, 4 bps)
| Métrique | SPY | XLE |
|---|---|---|
| PnL Net Total : 0,25 %/ATR ; 1x | −4,2 % ; −7,9 % | +0,1 % ; +7,2 % |
| Profit Factor (1x ; pondéré) | 0,91 ; 0,93 | 1,09 ; 1,01 |
| Win Rate | 45,2 % | 44,9 % |
| Espérance ATR [IC] ; bps [IC] | −0,158 [−0,736 ; +0,434] ; −4,5 [−23,7 ; +14,9] | +0,020 [−0,588 ; +0,674] ; +7,4 [−28,7 ; +43,9] |
| Max Drawdown : 0,25 %/ATR ; 1x | −10,9 % ; −19,2 % | −19,5 % ; −36,4 % |
| Nombre de trades (/mois) | 155 (2,2) | 136 (1,9) |
| Durée médiane | 26 barres ; 48 h calendaires | 26 barres ; 48 h |
| Part des frais (1x) | brut ≤ 0 (brut +0,00 ATR, frais 0,16 ATR) | 35 % (brut +0,10 ATR, frais 0,08 ATR) |

- **Calmar** (0,25 %/ATR ; 1x) : SPY −0,07 ; −0,07. XLE 0,00 ; 0,03.
- **Années à espérance ATR > 0 :** 2/6 (SPY), 3/6 (XLE).

#### 4. Analyse causale & Physique du trade
- [CODE] **Contrôles :**
  - intégrité ;
  - couverture 2020-2025 ;
  - BTC identique à C02bis ;
  - aucune clé dans les fichiers écrits.
- [CODE] **Clôtures anticipées du NYSE.** Le filtre 09:30-16:00 gardait le post-marché des 12 séances fermées à 13:00. Le calendrier a été vérifié sur les volumes (12/12 pour XLE, 11/12 pour SPY, 12e vérifiée à la main) ; les barres sont refiltrées sans nouveau téléchargement.
- [CODE] **Enchère de clôture.** Horodatée à 16:00, elle tombe dans la barre écartée.
- [OBS] **Dividendes et fractionnement.** 24 dividendes par ETF (SPY −36 bps, XLE −106 bps en moyenne). XLE a été fractionné 2 pour 1 le 2025-12-05 (−6 931 bps en série brute). La série ajustée neutralise les deux.
- [OBS] **Proxy XLE.** Corrélation quotidienne 0,46 avec le spot WTI (bêta 0,30) et 0,60 avec SPY (bêta 1,00).
- [OBS] **Signaux.** `leg_atr` est plus long sur les ETF (P50 3,09 et 3,24) : le seuil BTC ne retient que 42 % et 38 % des signaux. Univers RE-1 : 191 et 159.
- [OBS] **Gaps, données.**
  - |gap| médian 33 et 57 bps, soit 1,2 et 1,1 ATR ; 57 % et 56 % des ouvertures dépassent 1 ATR ;
  - la barre d'ouverture porte 17 % et 22 % du vrai range pour 7,7 % des barres.
- [OBS] **Gaps, signaux.** `nis_z_100` vaut 1,40 et 1,59 en médiane sur la barre d'ouverture, contre 0,14 ailleurs. Le seuil BTC écarte 64 % et 74 % des signaux R2 nés d'un gap, contre 20 % et 16 % des autres.
- [OBS] **Gaps, trades.**
  - 92 % et 90 % des trades traversent au moins une nuit (2 en médiane).
  - Brut : SPY 0,00 = gaps +0,03 + séance −0,03 ; XLE +0,09 = gaps +0,19 + séance −0,10 (IC ±0,4 à 0,6).
  - Les gaps pèsent 35 à 47 % de l'amplitude des gagnants et des perdants.
  - 8 stops sur 46 (SPY) et 11 sur 48 (XLE) sont percés à l'ouverture, avec un dépassement moyen de +2,6 et +1,0 ATR.
- [OBS] **Sous-familles et sens.**
  - SPY : F3 −0,37, F2b +0,06, Short −0,60 (dérive +0,35).
  - XLE : F2b −0,19, F3 +0,14.
  - Le stop de F3 améliore l'espérance sur les deux ETF (+0,46 et +0,40, non significatif).
- [HYP] **H compte des barres.** Sur les ETF, la cinématique d'une séance est jugée deux séances plus tard. Le filtre d'innovation évite d'entrer sur le gap, mais la position subit des gaps non choisis.

#### 5. Décision
- [ ] **REJETÉ**
- [ ] **NON CONCLUANT**
- [x] **À POURSUIVRE (descriptif) : RE-1 inchangée, D01 clos.**
  - Carte des faiblesses du modèle fixe : rapport frais / ATR (or), structure de séance (ETF), dérive (ventes en marché haussier), queue droite.
  - Restent au porteur : la validation de la source XAU et le push.

### [EXP-D01.5] — Sensibilité de RE-1 à l'horizon H seul (or, SPY, XLE)
- **Date :** 2026-09-30
- **Étape :** D Adaptation, étape intermédiaire avant D02 (décision du porteur). Descriptif : RE-1 inchangée, aucun H retenu ni figé ; ni Optuna ni VectorBT.
- **Actif & Période :** données de D01, empreintes inchangées. CFD or XAU/USD (HistData), 2020-2025. ETF SPY et XLE (Alpaca, séance régulière), 2020-2025.
- **Grilles du porteur (OFAT sur H, en barres de 30 min) :** XAU {26, 48, 72, 96, 130} ; SPY et XLE {6, 13, 26, 65, 130}.
- **Modèle de frais :** 4 bps. Capital à 0,25 % par ATR14(t) et notionnel 1x.
- **Livrables :**
  - `experiments/D01_5/run_D01_5.py` (réutilise `strategy.run_re1(horizon=H)`, `prepare` et `gap_trades` de D01) ;
  - `rapport_D01_5.md`, `resultats_D01_5.csv`, `annuel_D01_5.csv`, `diagnostics_D01_5.json`, `controles_D01_5.json`, figures ;
  - test `test_re1_a_un_autre_horizon_structure_et_causalite` (H = 6 et H = 130 sur BTC).

#### 0. Cadrage obligatoire
- **QUESTION :** une translation de H seul corrige-t-elle les faiblesses de D01 ? Or : brut +0,24 ATR contre 0,26 ATR de frais à H = 26. SPY et XLE : H = 26 traverse deux nuits.
- **PERTINENCE POUR LE FILTRE AKF :** H est le seul paramètre de RE-1 lié au temps. Il décide quand le jugement cinématique fait à t est encaissé, donc combien de frais, de dérive et de nuits entrent dans chaque trade.
- **CE QUE LE PROTOCOLE MESURE RÉELLEMENT :**
  - la course séquentielle à chaque H (la population de trades change avec H) ;
  - l'effet apparié de H sur les entrées figées de RE-1 à H = 26 ;
  - timing et dérive ;
  - l'exposition aux gaps et les stops percés.
- **CE QU'IL NE PERMET PAS DE CONCLURE :**
  - aucun H n'est validé : le meilleur des cinq, choisi après coup, surestime l'espérance (objet du WFO de D02) ;
  - pas de hold-out ; pas de coûts de portage.

#### 1. Hypothèse & Motivation physique (porteur)
- **Or :** un H plus long fait croître l'excursion brute et dilue le coût fixe des frais.
- **ETF :** H ≤ 13 limite l'exposition aux nuits ; H ≥ 65 dilue le bruit des gaps dans la tendance.

#### 2. Règle testée (OFAT)
- **Facteur :** H seul ; tout le reste est RE-1.
- **Règle de lecture (fixée avant le calcul) :**
  - avantage = borne basse de l'IC 95 % > 0, en ATR et en bps ;
  - forme de la courbe entière, pas meilleure valeur ;
  - effet apparié et timing/dérive pour chaque H.
- **Contrôles bloquants :** empreintes = audit D01 ; H = 26 redonne D01 (23 métriques par actif, écart ≤ 5·10⁻⁶, et les mesures de gaps) ; entrées figées à H = 26 = RE-1 trade par trade ; structure des trades à chaque H.

#### 3. Résultats nets (4 bps)
| Actif, H | PnL : 0,25 %/ATR ; 1x | PF (1x) | WR | Espérance ATR [IC] | bps | Brut ; frais (ATR) | MDD : 0,25 %/ATR ; 1x | Calmar : 0,25 %/ATR ; 1x | Trades (/mois) | Durée : barres ; h | Part des frais (1x, brut en bps) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| XAU 26 (RE-1) | +1 % ; +5 % | 1,04 | 42,5 % | −0,019 [−0,362 ; +0,349] | +1,1 | +0,239 ; 0,257 | −13,6 % ; −13,3 % | 0,01 ; 0,07 | 651 (9,0) | 26 ; 13 | 79 % |
| XAU 48 | −7 % ; −3 % | 0,99 | 42,3 % | −0,120 [−0,623 ; +0,400] | −0,2 | +0,138 ; 0,257 | −18,8 % ; −19,8 % | −0,07 ; −0,03 | 515 (7,2) | 48 ; 25 | 106 % |
| XAU 72 | −7 % ; −4 % | 0,99 | 37,2 % | −0,071 [−0,661 ; +0,552] | −0,3 | +0,184 ; 0,255 | −22,9 % ; −24,8 % | −0,05 ; −0,03 | 441 (6,1) | 72 ; 37 | 107 % |
| XAU 96 | −9 % ; −4 % | 0,99 | 38,3 % | −0,185 [−0,890 ; +0,548] | −0,3 | +0,071 ; 0,256 | −30,6 % ; −31,6 % | −0,05 ; −0,02 | 386 (5,4) | 96 ; 50 | 108 % |
| XAU 130 | −30 % ; −31 % | 0,81 | 34,3 % | −0,702 [−1,620 ; +0,255] | −10,5 | −0,446 ; 0,255 | −41,6 % ; −42,8 % | −0,14 ; −0,14 | 327 (4,5) | 130 ; 68 | brut ≤ 0 |
| SPY 6 | −6 % ; −5 % | 0,91 | 46,6 % | −0,161 [−0,526 ; +0,202] | −2,5 | +0,004 ; 0,165 | −12,9 % ; −15,1 % | −0,08 ; −0,06 | 191 (2,7) | 6 ; 3 | 260 % |
| SPY 13 | −6 % ; −3 % | 0,96 | 47,9 % | −0,189 [−0,667 ; +0,292] | −1,4 | −0,026 ; 0,163 | −12,5 % ; −18,9 % | −0,08 ; −0,03 | 169 (2,3) | 13 ; 24 | 154 % |
| SPY 26 (RE-1) | −4 % ; −8 % | 0,91 | 45,2 % | −0,158 [−0,736 ; +0,434] | −4,5 | +0,004 ; 0,162 | −10,9 % ; −19,2 % | −0,07 ; −0,07 | 155 (2,2) | 26 ; 48 | brut ≤ 0 |
| SPY 65 | −19 % ; −37 % | 0,57 | 29,6 % | −0,756 [−1,663 ; +0,148] | −38,3 | −0,594 ; 0,162 | −25,9 % ; −43,9 % | −0,14 ; −0,17 | 115 (1,6) | 65 ; 168 | brut ≤ 0 |
| SPY 130 | −10 % ; −22 % | 0,73 | 28,4 % | −0,378 [−1,858 ; +1,241] | −25,0 | −0,218 ; 0,160 | −15,3 % ; −29,0 % | −0,11 ; −0,14 | 88 (1,2) | 130 ; 336 | brut ≤ 0 |
| XLE 6 | −10 % ; −9 % | 0,91 | 44,0 % | −0,252 [−0,638 ; +0,133] | −4,8 | −0,172 ; 0,080 | −18,2 % ; −32,6 % | −0,09 ; −0,05 | 159 (2,2) | 6 ; 20 | brut ≤ 0 |
| XLE 13 | −3 % ; +11 % | 1,13 | 46,6 % | −0,083 [−0,548 ; +0,430] | +8,8 | −0,003 ; 0,081 | −18,1 % ; −31,4 % | −0,03 ; 0,06 | 148 (2,1) | 13 ; 24 | 31 % |
| XLE 26 (RE-1) | +0 % ; +7 % | 1,09 | 44,9 % | +0,020 [−0,588 ; +0,674] | +7,4 | +0,100 ; 0,081 | −19,5 % ; −36,4 % | 0,00 ; 0,03 | 136 (1,9) | 26 ; 48 | 35 % |
| XLE 65 | +3 % ; +20 % | 1,22 | 35,2 % | +0,155 [−0,788 ; +1,130] | +24,9 | +0,235 ; 0,080 | −10,9 % ; −26,3 % | 0,05 ; 0,12 | 105 (1,5) | 65 ; 168 | 14 % |
| XLE 130 | −29 % ; −50 % | 0,64 | 25,3 % | −1,573 [−3,508 ; +0,197] | −71,2 | −1,493 ; 0,081 | −35,6 % ; −64,0 % | −0,16 ; −0,17 | 83 (1,2) | 126 ; 335 | brut ≤ 0 |

- **Aucun IC à borne basse > 0** sur les 15 configurations, ni en ATR ni en bps. Seul IC qui exclut 0 : SPY H = 65, −38,3 bps [−76,2 ; −2,8] (négatif).
- **Entrées figées de H = 26 (effet de H, ATR) :** de −0,555 (SPY 65) à +0,083 (XAU 72), tous les IC ∋ 0.

#### 4. Analyse causale & Physique du trade
- [CODE] Contrôles bloquants passés ; H = 26 redonne D01 à l'identique.
- [OBS] **Or.**
  - Frais fixes : 0,26 ATR par trade à tout H (4 bps / ATR14(t) de l'entrée).
  - Le brut ne croît pas : +0,24 → −0,45 ATR en séquentiel. Sur les mêmes entrées : +0,24, +0,26, +0,32, +0,21, +0,09.
  - La dérive croît (+0,38 → +0,81 ATR) des deux côtés : Long +0,33 → +0,62 (H = 72), Short −0,43 → −1,54 ; timing net −0,05 → −0,73.
  - MDD ×3 (−13,6 % → −41,6 % à 0,25 %/ATR).
  - Gaps négligeables : 2 stops percés à chaque H (les mêmes), coût ≤ 0,005 ATR par trade.
  - H = 26 est le meilleur point de la grille.
- [OBS] **SPY.**
  - H = 13 ne réduit pas les nuits : 91 % des trades en traversent une (13 barres = une séance), contre 92 % à H = 26.
  - H = 6 les réduit (50 %) et divise par trois le coût des stops percés (0,047 contre 0,133 ATR par trade). Mais le brut reste nul (+0,004) : la composante en séance vaut ≈ 0 à tout H ≤ 26.
  - H ≥ 65 : stops percés maintenus (8 à 10), coût 0,175 à 0,221 ATR par trade ; la dérive (+0,98 à +1,86) écrase les Short (−2,00 à −2,62) ; timing à H = 65 −1,02 [−2,01 ; −0,01].
- [OBS] **XLE.**
  - Pic isolé : −0,25 (H = 6) → +0,16 (H = 65) → −1,57 (H = 130 : Short −3,68, F2b −4,44 sur 30 trades).
  - H = 65 sur les mêmes entrées que H = 26 : +0,009 ATR (effet −0,010 [−0,71 ; +0,75]). Les 31 trades que la course à 65 saute valaient −0,48 ATR : le gain vient de la population (calendrier), pas de la sortie.
  - H = 65 : 3 années positives sur 6, 2025 à −2,47 ATR.
  - Brut porté par les nuits (gaps +0,12 à +0,37 ATR à H = 13-65), composante en séance négative à chaque H.
- [HYP] **H déplace l'exposition (dérive, nuits, risque par trade), pas l'avantage.** Une sortie en fin de séance sur les ETF retirerait les gaps sans créer d'espérance (séance ≈ 0 sur SPY, < 0 sur XLE).
- [HYP] **Pour D02 :**
  - la course séquentielle ajoute un effet de calendrier à l'effet de la sortie ; un optimiseur de H l'ajustera aussi ;
  - à 0,25 %/ATR14 de 30 min, le risque par trade croît avec H ; comparer des H au Calmar suppose une convention ;
  - sur XAU, SPY et XLE, un WFO mesurerait d'abord le biais de sélection de l'optimiseur (témoin possible).
- **Écarts au prompt :** « slippage de +2,6 ATR » = dépassement moyen de 8 stops percés sur 46 sur SPY, soit 0,133 ATR par trade ; brut de l'or « positif » = +0,239 ATR, IC [−0,105 ; +0,605].

#### 5. Décision
- [ ] **REJETÉ**
- [ ] **NON CONCLUANT**
- [x] **À POURSUIVRE (descriptif) : H seul ne restaure d'avantage établi sur aucun des trois marchés. RE-1 inchangée (H = 26), D01.5 clos.**
  - Reste au porteur : le cadrage de D02 (objectif, domaine, convention de risque selon H, traitement de l'effet de calendrier).

### [EXP-D01.6] — Verrouillage et séance : profil des trades sautés, découplage sortie / cooldown, sortie de fin de séance (SPY, XLE)
- **Date :** 2026-09-30
- **Étape :** D Adaptation, exploration avant D02 (décision du porteur). Descriptif : RE-1 inchangée, aucun filtre ni paramètre retenu ; D02 non lancé.
- **Actif & Période :** ETF SPY et XLE (Alpaca, séance régulière), 2020-2025, données de D01 (empreintes inchangées).
- **Modèle de frais :** 4 bps. Capital à 0,25 % par ATR14(t) et notionnel 1x.
- **Livrables :**
  - `src/envelope/decouple.py` : `lock_trades`, `session_close_trades`, `session_last_bar` ; tests `tests/test_envelope_decouple.py` (9) ;
  - `experiments/D01_6/run_D01_6.py`, `rapport_D01_6.md`, `resultats_D01_6.csv`, `profil_D01_6.json`, `diagnostics_D01_6.json`, `controles_D01_6.json`, figure.

#### 0. Cadrage obligatoire
- **QUESTION :** (1) les 31 trades de RE-1 sur XLE sautés par la course à H = 65 ont-ils une signature à t ? (2) un verrouillage plus long que la sortie (H_exit 26, H_cooldown 26 à 90) donne-t-il une espérance robuste ? (3) le signal a-t-il une valeur en séance seule ?
- **PERTINENCE POUR LE FILTRE AKF :** dans RE-1, H fixe la sortie et le verrouillage ; les gaps sont des innovations d'une barre, qu'une sortie avant la nuit écarte.
- **CE QUE LE PROTOCOLE MESURE RÉELLEMENT :** profil à t (variables du porteur, famille, trois variables de réplique) avec AUC [IC] ; valeur des groupes à 26 et 65 barres ; 8 métriques par verrouillage ; sortie forcée au close de la dernière barre de séance, sur les entrées de RE-1 (effet apparié) et libérée à la clôture.
- **CE QU'IL NE PERMET PAS DE CONCLURE :** aucun filtre retenu (31 trades) ; pas de hold-out ; clôture au close de la dernière barre continue, pas à l'enchère.

#### 1. Hypothèse & Motivation physique (porteur)
- Le gain de XLE à H = 65 viendrait du verrouillage prolongé, pas de la sortie tardive.
- Le moteur n'aurait pas d'avantage en séance et capterait une prime de risque overnight.

#### 2. Règle testée
- **Action 1 :** signature = AUC dont l'IC exclut 0,5 sur XLE, même sens sur SPY, et utile seulement si les trades sautés perdent à la sortie de RE-1.
- **Actions 2 et 3 :** avantage = borne basse de l'IC 95 % > 0.
- **Contrôles bloquants :** verrouillage 26 = RE-1 trade par trade ; verrouillage 65 = population de H = 65 ; entrées de RE-1 conservées ; aucune nuit détenue en séance ; une séance par date de New York.

#### 3. Résultats nets (4 bps)
| Actif · variante | PnL : 0,25 %/ATR ; 1x | PF (1x) | WR | Espérance ATR [IC] | Espérance bps [IC] | Brut ; frais (ATR) | MDD : 0,25 %/ATR ; 1x | Calmar : 0,25 %/ATR ; 1x | Trades (/mois) | Durée médiane : barres ; h | Part des frais (1x, brut en bps) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| XLE · H_exit 26, H_cooldown 26 (RE-1) | +0 % ; +7 % | 1,09 | 44,9 % | +0,020 [−0,588 ; +0,674] | +7,4 [−28,7 ; +43,9] | +0,100 ; 0,081 | −19,5 % ; −36,4 % | 0,00 ; 0,03 | 136 (1,9) | 26 ; 48,0 h | 35 % |
| XLE · H_exit 26, H_cooldown 48 | −4 % ; −1 % | 1,02 | 42,9 % | −0,130 [−0,829 ; +0,557] | +1,3 [−40,9 ; +43,4] | −0,048 ; 0,082 | −19,2 % ; −36,7 % | −0,04 ; −0,01 | 112 (1,6) | 26 ; 48,0 h | 76 % |
| XLE · H_exit 26, H_cooldown 65 | −1 % ; +4 % | 1,08 | 45,7 % | −0,010 [−0,664 ; +0,683] | +6,2 [−33,0 ; +48,9] | +0,071 ; 0,080 | −14,3 % ; −29,6 % | −0,01 ; 0,02 | 105 (1,5) | 26 ; 48,0 h | 39 % |
| XLE · H_exit 26, H_cooldown 90 | +2 % ; +9 % | 1,15 | 46,2 % | +0,123 [−0,639 ; +1,003] | +12,5 [−33,1 ; +65,0] | +0,203 ; 0,080 | −17,4 % ; −35,5 % | 0,02 ; 0,04 | 93 (1,3) | 26 ; 48,0 h | 24 % |
| XLE · séance, entrées de RE-1 | −6 % ; −6 % | 0,86 | 41,2 % | −0,170 [−0,444 ; +0,107] | −4,3 [−20,9 ; +13,5] | −0,089 ; 0,081 | −10,2 % ; −19,1 % | −0,10 ; −0,06 | 136 (1,9) | 4 ; 2,0 h | brut ≤ 0 |
| XLE · séance, libérée à la clôture | −6 % ; −6 % | 0,87 | 43,2 % | −0,162 [−0,417 ; +0,096] | −3,9 [−18,8 ; +12,4] | −0,082 ; 0,081 | −10,8 % ; −19,8 % | −0,10 ; −0,05 | 155 (2,2) | 4 ; 2,0 h | > 1 000 % |
| SPY · H_exit 26, H_cooldown 26 (RE-1) | −4 % ; −8 % | 0,91 | 45,2 % | −0,158 [−0,736 ; +0,434] | −4,5 [−23,7 ; +14,9] | +0,004 ; 0,162 | −10,9 % ; −19,2 % | −0,07 ; −0,07 | 155 (2,2) | 26 ; 48,0 h | brut ≤ 0 |
| SPY · H_exit 26, H_cooldown 48 | −2 % ; −5 % | 0,94 | 45,2 % | −0,017 [−0,638 ; +0,624] | −3,0 [−25,2 ; +20,5] | +0,144 ; 0,160 | −10,0 % ; −17,7 % | −0,04 ; −0,05 | 135 (1,9) | 26 ; 48,0 h | 410 % |
| SPY · H_exit 26, H_cooldown 65 | −3 % ; −3 % | 0,96 | 44,3 % | −0,151 [−0,829 ; +0,584] | −2,1 [−24,4 ; +24,1] | +0,012 ; 0,162 | −10,3 % ; −13,5 % | −0,05 ; −0,04 | 115 (1,6) | 26 ; 48,0 h | 208 % |
| SPY · H_exit 26, H_cooldown 90 | −7 % ; −8 % | 0,85 | 41,9 % | −0,313 [−1,013 ; +0,426] | −7,6 [−31,4 ; +18,3] | −0,149 ; 0,163 | −13,5 % ; −17,3 % | −0,10 ; −0,08 | 105 (1,5) | 26 ; 48,0 h | brut ≤ 0 |
| SPY · séance, entrées de RE-1 | −1 % ; +4 % | 1,14 | 46,5 % | −0,036 [−0,286 ; +0,230] | +2,9 [−6,4 ; +12,7] | +0,127 ; 0,162 | −5,1 % ; −7,8 % | −0,02 ; 0,09 | 155 (2,2) | 6 ; 3,0 h | 58 % |
| SPY · séance, libérée à la clôture | +0 % ; +5 % | 1,14 | 47,8 % | −0,008 [−0,248 ; +0,225] | +2,9 [−5,8 ; +11,8] | +0,157 ; 0,164 | −7,0 % ; −9,4 % | 0,00 ; 0,09 | 182 (2,5) | 5 ; 2,5 h | 58 % |

- **Aucun IC à borne basse > 0** (actions 2 et 3).

#### 4. Analyse causale & Physique du trade
- [CODE] Contrôles bloquants passés ; `decouple.py` n'appelle que `_candidates`, `_sequential` et `apply_stop`, inchangés.
- [OBS] **Action 1 (XLE).**
  - Les 31 trades sautés valent **+0,118 ATR avec la sortie de RE-1** (médiane −0,97 ; −0,55 sans leurs 3 meilleurs) et −0,48 à 65 barres. Les 105 gardés : −0,010 à 26, +0,155 à 65.
  - Seul trait distinctif : leur définition (27 à 64 barres après le trade précédent, contre 154 en médiane ; AUC 0,06 [0,02 ; 0,10]).
  - Variables du porteur, AUC [IC] : `nis_z_100` 0,45 [0,34 ; 0,56], `retrace_ratio` 0,45 [0,34 ; 0,57], `leg_atr` 0,49 [0,38 ; 0,60], sens 0,57 [0,48 ; 0,65] ; heure et tercile d'ATR sans régularité.
  - Réplication SPY (42 contre 113) : tendances inversées (Long, même sens, 14:00-15:00) ; `leg_atr` et résultat du trade précédent à 0,60 [0,499 ; 0,70], contre 0,49 et 0,45 sur XLE. Aucune signature.
- [OBS] **Action 2.** Zigzag sans tendance (XLE +0,020, −0,130, −0,010, +0,123 ; SPY −0,158, −0,017, −0,151, −0,313). Chaque verrouillage retire un paquet de trades valant de −0,75 à +0,87 ATR à 26 barres. XLE verrouillage 65 avec sortie à 26 : −0,010 (le +0,155 de D01.5 demandait aussi la sortie à 65 barres).
- [OBS] **Action 3.**
  - SPY : brut en séance +0,13 à +0,16 ATR (IC ∋ 0), contre +0,004 pour RE-1 ; frais 0,16 ATR ; net −0,04 et −0,01. MDD −5 à −7 % contre −11 %.
  - XLE : brut en séance −0,09 ; net −0,17 et −0,16.
  - Effet apparié séance − RE-1 : SPY +0,122 [−0,45 ; +0,68], XLE −0,190 [−0,87 ; +0,44] (nuits et séances suivantes : −0,12 sur SPY, +0,19 sur XLE).
- [HYP] Pas de répliques toxiques à filtrer dans RE-1 ; le verrouillage est un sélecteur de calendrier ; pas de valeur nette en séance à 4 bps (point mort ≈ 4 bps sur SPY) ; pas de prime overnight générale (la nuit aide XLE, pèse sur SPY).
- **Écarts au prompt :** +0,009 ATR = espérance à 65 barres sur entrées figées, l'effet apparié est −0,010 ; −0,48 ATR = valeur des 31 trades à 65 barres, +0,118 à 26 ; « tout le brut vient des gaps » vaut pour XLE, pas pour SPY (gaps ≈ 0, séance +0,13).

#### 5. Décision
- [ ] **REJETÉ**
- [ ] **NON CONCLUANT**
- [x] **À POURSUIVRE (descriptif) : aucune signature, aucun verrouillage ni variante de séance à IC > 0. RE-1 inchangée, D01.6 clos.**
  - Outils disponibles pour la suite : `lock_trades` et `session_close_trades`.

### [EXP-D01.7, partie 1] — Portabilité de RE-1 figée sur des marchés 24/5 : GBPJPY mesuré, futures en attente d'accès
- **Date :** 2026-10-01
- **Étape :** D, test de portabilité zero-shot (décision du porteur). RE-1 strictement gelée ; aucune modification sur la base des résultats.
- **Actif & Période :** GBPJPY au comptant 2020-2025 ; BTC 2020-2025 en référence. NQ, RTY, CL, HG bloqués avant téléchargement.
- **Modèle de frais (hypothèses fixées avant) :** BTC 0, 5 et 10 bps ; GBPJPY 0, 2 et 4 bps (principal 4 bps).
- **Livrables :** `experiments/D01_7/donnees_D01_7.py`, `run_D01_7.py`, `rapport_D01_7.md`, `narratif_D01_7.md`, `resultats_D01_7.csv`, `annuel_D01_7.csv`, `audit_D01_7.json`, `diagnostics_D01_7.json`, `controles_D01_7.json`, figure ; métas des séries versionnés.

#### 0. Cadrage obligatoire
- **QUESTION :** RE-1 conserve-t-elle son comportement hors crypto, sur des marchés à cotation quasi continue 24/5 ?
- **PERTINENCE POUR LE FILTRE AKF :** géométrie transposée en D01, rente dépendante de la structure ; le 24/5 retire la nuit des ETF mais garde week-end, pause CME et roulements.
- **CE QUE LE PROTOCOLE MESURE RÉELLEMENT :** audit des données avant backtest, puis 8 métriques en brut et nettes de coûts déclarés, Long/Short, F2b/F3, volatilité, sessions, interruptions, concentration, queues.
- **CE QU'IL NE PERMET PAS DE CONCLURE :** pas de hors échantillon, pas de classement, coûts réels non mesurés.

#### 1. Hypothèse & Motivation physique
- Si la cinématique captée par RE-1 est générique, elle devrait produire un brut positif sur des marchés continus liquides, les frais restant à évaluer en ATR.

#### 2. Règle testée
- **Règle :** RE-1 identique à C02bis, seuils BTC gelés.
- **Contrôles bloquants :** ancre P6.5d ; parité C02bis (1 080 trades, 40 métriques) ; audit sans défaut d'intégrité ni de couverture ; recoupement de GBPJPY avec H.10 (critère fixé avant : corrélation ≥ 0,95 au décalage 0, meilleur décalage à ± 30 min, écart médian ≤ 10 bps) ; invariance d'échelle du moteur (prérequis des futures rétro-ajustés).

#### 3. Résultats nets (GBPJPY)
| Métrique | BTC 5 bps (réf.) | GBPJPY brut | GBPJPY 2 bps | GBPJPY 4 bps |
|---|---|---|---|---|
| PnL Net Total : 0,25 %/ATR ; 1x | +138 % ; +204 % | −4 % ; −5 % | −16 % ; −17 % | −27 % ; −27 % |
| Profit Factor (1x) | 1,20 | 0,96 | 0,84 | 0,74 |
| Win Rate | 44,3 % | 42,1 % | 40,5 % | 38,0 % |
| Espérance ATR [IC] ; bps | +0,369 [+0,098 ; +0,645] ; +12,3 | −0,035 [−0,284 ; +0,221] ; −0,6 | −0,239 [−0,490 ; +0,018] ; −2,6 | −0,443 [−0,697 ; −0,180] ; −4,6 |
| Max Drawdown : 0,25 %/ATR ; 1x | −13,5 % ; −43,9 % | −8,7 % ; −8,8 % | −16,8 % ; −17,5 % | −27,2 % ; −27,9 % |
| Nombre de trades (/mois) | 1 080 (15,0) | 687 (9,5) | idem | idem |
| Durée médiane | 26 barres ; 13 h | 26 barres ; 13 h | idem | idem |
| Part des frais (1x) ; frais en ATR | 29 % ; 0,14 | — ; 0 | brut ≤ 0 ; 0,20 | brut ≤ 0 ; 0,41 |

- **Calmar** (0,25 %/ATR ; 1x) : GBPJPY 4 bps −0,19 ; −0,19. **Long / Short** (brut) −0,014 / −0,058. **F2b / F3** (brut) −0,129 / +0,066. **Années > 0 :** 0/6 à 4 bps, 3/6 en brut.

#### 4. Analyse causale & Physique du trade
- [CODE] **Accès aux données.**
  - Dukascopy : HTTP 429 dès la deuxième requête ; l'historique en vrac est réservé à un bucket AWS « Requester Pays » (identifiants AWS obligatoires). Non contourné ; source de repli HistData déclarée.
  - QuantConnect : compte requis ; données utilisables seulement dans son cloud (Object Store sans téléchargement ; licence locale payante réservée à LEAN, non convertible). Futures bloqués, décision au porteur.
- [OBS] **Audit de GBPJPY.**
  - 73 055 barres, intégrité et couverture conformes ; reprise le dimanche à 17:00 et fin le vendredi à 17:00 heure de New York.
  - Recoupement H.10 : corrélation 0,9997 au décalage 0 (pic net), écart médian −1,2 bps.
  - **Défaut :** 673 des 690 trous de semaine tombent en 2023 (≈ 1 758 barres, 14 % de l'année) ; aucun seuil fixé avant, actif non bloqué ; 2023 n'est pas un cas à part (−0,30 ATR à 4 bps).
- [OBS] **Invariance d'échelle.** À ×0,37 et ×2,9, les signaux sont identiques et les descripteurs identiques à 3·10⁻⁵ près. Seuls basculent les signaux à `retrace_ratio` = 0,50 exactement (F2b → F5). RE-1 à ×2,9 : 1 trade de moins sur 1 080, espérance +0,3686 → +0,3676.
- [OBS] **GBPJPY.**
  - Brut nul, symétrique, sans dérive.
  - ATR de 30 min 10 à 11 bps : les frais coûtent 0,41 ATR à 4 bps. Le 0,25 %/ATR est plafonné à 1x pour 98 % des trades.
  - 53 % des signaux en session asiatique ; toutes les sessions ≤ 0 à 4 bps.
  - Interruptions sans effet (9,5 % des trades, composante +0,013 ATR).
  - Médiane −1,42 ATR ; décile supérieur +0,75 ATR par trade.
- [HYP] Pas de mouvement exploitable par RE-1 sur GBPJPY à 30 min : différence de nature avec BTC, pas seulement de coût.

#### 5. Décision
- [ ] **REJETÉ**
- [ ] **NON CONCLUANT**
- [x] **EN COURS (descriptif) : GBPJPY mesuré (brut nul) ; NQ, RTY, CL, HG en attente de l'accès aux données choisi par le porteur. RE-1 inchangée.**

### [EXP-D01.7, données] — Source Saxo, abandon des séries continues, univers redéfini (aucun backtest)
- **Date :** 2026-10-01
- **Étape :** D, préparation des données de D01.7, sur décisions du porteur. RE-1 gelée ; aucun backtest.
- **Livrables :**
  - code : `src/marketdata/saxo.py` et ses tests, `experiments/D01_7/saxo_probe_D01_7.py`, `saxo_univers_D01_7.py` ;
  - audits : `audit_repo_D01_7.md` (FAIL), `audit_saxo_D01_7.md` (annexe 9 comprise), `audit_univers_D01_7.md` ;
  - rapports bruts : `saxo_probe_D01_7.json`, `saxo_univers_D01_7.json`, `univers_D01_7.json` ;
  - métas des séries versionnés.

#### Constats
- [CODE] **Accès à Saxo OpenAPI LIVE :** flux PKCE, clé dans une variable d'environnement, jeton en mémoire du processus
  seulement. La réserve 2026 est vérifiée avant et après chaque requête.
- [OBS] **Sources écartées :** le dépôt axb0306/cme-futures-ohlc (aucune donnée de 30 min sur 2020-2025) et QuantConnect
  (aucun export autorisé).
- [OBS] **Les séries continues de Saxo sont brutes, non ajustées.** Le future c1 et le CFD « cont » changent de contrat
  au même instant :
  - WTI : le dernier jour de cotation, vers 11:00 heure de New York, au milieu d'une barre ;
  - cuivre : à la réouverture, 2 à 4 jours ouvrés avant le premier jour de notification ;
  - US2000 : le mardi de la semaine d'échéance ;
  - NQ : le 3e vendredi.
  - Décision du porteur : abandon des futures et des CFD continus pour D01.7.
- [OBS] **Univers redéfini par le porteur :**
  - US100, US30, GER40, EU50, HK50, XAGUSD et GBPJPY. HK50 remplace Japan 225, absent des CfdOnIndex pour ce compte.
  - En option, 5 CFD sur ETF : TLT, USO, SMH, URA, GDX.
  - Toutes les séries couvrent 2020-2025, sans défaut d'intégrité.
  - Les CFD sur indice ne montrent aucun changement de contrat caché.
  - Écarts acheteur-vendeur médians de 0,9 à 6,6 bps.
  - Les ETF ne cotent qu'en séance américaine, sans heures étendues, et leur historique est ajusté des splits.
- [OBS] **GBPJPY :** la série Saxo concorde avec HistData (corrélation des rendements de 30 min de 0,993) et comble
  2023.
- [CODE] **Erreur de sélection corrigée :** NLR avait été retenu à la place d'URA. Le ticker demandé doit désormais
  correspondre exactement.

#### Décision
- [x] **Données validées pour le backtest de D01.7**, sous trois choix du porteur : la source de GBPJPY, les coûts
  aller-retour, et l'entrée ou non des ETF dans D01.7. Aucun backtest lancé.

### [EXP-D01.7, partie 2] — Portabilité de RE-1 figée : CFD sur indices, argent, GBPJPY et CFD sur ETF (Saxo)
- **Date :** 2026-10-01
- **Étape :** D, test de portabilité zero-shot (univers redéfini par le porteur). RE-1 strictement gelée ; aucune
  modification sur la base des résultats.
- **Actifs & Période :** 2020-2025, toutes séries Saxo ; BTC en référence.
  - CFD sur indices au comptant : US100, US30, GER40, EU50, HK50 (HK50 à la place de Japan 225, absent chez Saxo).
  - Au comptant : XAGUSD et GBPJPY (GBPJPY lu chez Saxo, sur décision du porteur).
  - CFD sur ETF, en séance américaine : TLT, USO, SMH, URA, GDX.
- **Modèle de frais, validé par le porteur avant le calcul :**
  - trois lectures : 0, écart médian mesuré, et un coût principal égal au plus grand de 4 bps et du P90 de l'écart,
    arrondi au point supérieur ;
  - coût principal : US100, US30, GER40 et GBPJPY 4 bps ; EU50 7 ; HK50 8 ; XAGUSD 11 ; ETF 4 ; BTC 5.
- **Livrables :** `experiments/D01_7/run_D01_7.py`, `narratif_D01_7.md`, `rapport_D01_7.md`, `resultats_D01_7.csv`,
  `annuel_D01_7.csv`, `audit_D01_7.json`, `diagnostics_D01_7.json`, `controles_D01_7.json`, `figures/D01_7.png` ;
  `donnees_D01_7.py` (FRED NASDAQ100 et DJIA).

#### 0. Cadrage obligatoire
- **QUESTION :** RE-1 conserve-t-elle son comportement hors crypto, sur des CFD sur indices quasi continus, de l'argent et
  du change au comptant, et des CFD sur ETF de séance ?
- **PERTINENCE POUR LE FILTRE AKF :** la géométrie se transpose (D01) ; il s'agit de voir si la rente suit sur d'autres
  structures de marché, régions et classes d'actifs.
- **CE QUE LE PROTOCOLE MESURE RÉELLEMENT :**
  - audit et recoupements externes avant tout backtest ;
  - 8 métriques en brut et nettes ;
  - Long/Short, F2b/F3, sessions, interruptions, concentration, queues.
- **CE QU'IL NE PERMET PAS DE CONCLURE :**
  - pas de hors échantillon ;
  - pas de classement : une sélection d'actifs pour D02 faite sur ce même échantillon est biaisée ;
  - coûts réels non mesurés (financement de nuit, dividendes des CFD).

#### 1. Hypothèse & Motivation physique
- Si la cinématique captée par RE-1 est générique, le brut devrait rester positif. Sa rentabilité dépendrait alors du
  rapport entre frais et ATR.

#### 2. Règle testée
- **Règle :** RE-1 identique à C02bis, seuils de BTC gelés.
- **Contrôles bloquants :**
  - ancre P6.5d ; parité avec C02bis (1 080 trades, 40 métriques) ;
  - audit sans défaut, règle des 5 jours de D01, à l'exception de quatre fermetures de bourse déclarées avant le calcul ;
  - recoupements externes, critère de la partie 1 : US100 contre la clôture officielle du NASDAQ-100, US30 contre le Dow
    Jones, GBPJPY contre les taux H.10.

#### 3. Résultats nets (coût principal de chaque actif)
| Actif (coût) | PnL net : 0,25 %/ATR ; 1x ; bps cumulés (1x) | PF (1x) | WR | Espérance ATR [IC] ; bps | MDD : 0,25 %/ATR ; 1x | Trades (/mois) | Durée médiane | Part des frais (1x) ; frais en ATR |
|---|---|---|---|---|---|---|---|---|
| BTC (5, réf.) | +138 % ; +204 % ; +13 320 | 1,20 | 44,3 % | +0,369 [+0,098 ; +0,645] ; +12,3 | −13,5 % ; −43,9 % | 1 080 (15,0) | 26 barres ; 13 h | 29 % ; 0,14 |
| US100 (4) | −5 % ; −10 % ; −707 | 0,97 | 39,6 % | −0,097 [−0,428 ; +0,252] ; −1,0 | −19,7 % ; −27,0 % | 695 (9,7) | 13 h | 134 % ; 0,24 |
| US30 (4) | +11 % ; +29 % ; +2 796 | 1,17 | 41,0 % | −0,004 [−0,350 ; +0,348] ; +3,9 | −13,7 % ; −14,1 % | 710 (9,9) | 13 h | 50 % ; 0,33 |
| GER40 (4) | +0 % ; +5 % ; +767 | 1,05 | 43,1 % | −0,005 [−0,292 ; +0,294] ; +1,4 | −22,9 % ; −27,5 % | 545 (7,6) | 13 h | 74 % ; 0,24 |
| EU50 (7) | −37 % ; −44 % ; −5 682 | 0,70 | 38,3 % | −0,590 [−0,946 ; −0,214] ; −10,6 | −40,6 % ; −47,8 % | 535 (7,4) | 13 h | brut ≤ 0 ; 0,42 |
| HK50 (8) | −9 % ; −15 % ; −1 295 | 0,94 | 40,7 % | −0,103 [−0,539 ; +0,334] ; −3,0 | −32,3 % ; −41,9 % | 425 (5,9) | 20 h | 162 % ; 0,30 |
| XAGUSD (11) | −41 % ; −57 % ; −7 863 | 0,79 | 38,1 % | −0,307 [−0,634 ; +0,006] ; −12,1 | −43,5 % ; −59,7 % | 651 (9,0) | 13 h | brut ≤ 0 en bps ; 0,37 |
| GBPJPY (4) | −20 % ; −21 % ; −2 300 | 0,82 | 40,7 % | −0,303 [−0,572 ; −0,031] ; −3,0 | −22,0 % ; −22,1 % | 754 (10,5) | 13 h | 421 % ; 0,40 |
| TLT (4) | −9 % ; −11 % ; −1 009 | 0,88 | 39,5 % | −0,205 [−0,972 ; +0,570] ; −6,4 | −16,6 % ; −21,1 % | 157 (2,2) | 48 h | brut ≤ 0 ; 0,16 |
| USO (4) | +4 % ; +65 % ; +5 926 | 1,42 | 47,9 % | +0,148 [−0,553 ; +0,813] ; +42,3 | −9,6 % ; −24,8 % | 140 (1,9) | 48 h | 9 % ; 0,07 |
| SMH (4) | −7 % ; −13 % ; −888 | 0,94 | 41,6 % | −0,180 [−0,795 ; +0,409] ; −6,0 | −15,5 % ; −30,4 % | 149 (2,1) | 48 h | brut ≤ 0 ; 0,08 |
| URA (4) | +2 % ; −18 % ; −1 346 | 0,92 | 38,6 % | +0,093 [−0,823 ; +1,100] ; −10,6 | −12,6 % ; −41,8 % | 127 (1,8) | 48 h | brut ≤ 0 en bps ; 0,06 |
| GDX (4) | +12 % ; +70 % ; +6 123 | 1,46 | 44,1 % | +0,349 [−0,365 ; +1,076] ; +42,8 | −8,5 % ; −19,1 % | 143 (2,0) | 48 h | 9 % ; 0,07 |

- **Brut en ATR, sans frais :**
  - US100 +0,139 ; US30 +0,327 (+7,9 bps [+0,8 ; +16,0]) ; GER40 +0,237 ; EU50 −0,172 ; HK50 +0,192 ;
  - XAGUSD +0,060 ; GBPJPY +0,095 ;
  - TLT −0,042 ; USO +0,220 ; SMH −0,105 ; URA +0,154 ; GDX +0,417.
- **À l'écart médian de Saxo :** US30 +0,211 ATR [−0,136 ; +0,556], soit +6,5 bps ; GER40 +0,104 ; US100 +0,086 ;
  HK50 −0,033 ; EU50 −0,458 ; XAGUSD −0,160 ; GBPJPY −0,154.
- **Années à espérance positive au coût principal :** GDX 5/6 ; US30, GER40, HK50, TLT, USO, SMH et URA 2/6 ; US100, EU50
  et XAGUSD 1/6 ; GBPJPY 0/6.

#### 4. Analyse causale & Physique du trade
- [OBS] **Audit :**
  - 13 séries sans défaut ;
  - recoupements : US100 0,9991 (−0,3 bp), US30 0,9994 (−0,3 bp), GBPJPY 0,9997 (−1,9 bp), meilleur décalage 0 ;
  - aucun raccord caché dans les CFD sur indice ;
  - géométrie des signaux transposée : `leg_atr` médian de 2,85 à 3,43, P75 de `nis_z_100` de 1,03 à 1,46.
- [OBS] **Aucun IC à borne basse positive au coût principal.**
  - Estimations positives : GDX, USO, URA, des ETF avec 127 à 157 trades.
  - Négatifs significatifs : EU50 ; GBPJPY à la limite.
- [OBS] **Frais en ATR, de 0,24 à 0,42 sur les CFD sur indices, l'argent et GBPJPY.** Leur ATR de 30 min ne vaut que 11 à
  34 bps, et les frais y atteignent ou dépassent un brut de +0,06 à +0,33 ATR. Sur les ETF, ils ne coûtent que 0,06 à
  0,16 ATR.
- [OBS] **ETF :**
  - 91 à 94 % des trades traversent une nuit.
  - Le brut vient des gaps : GDX +0,41 contre +0,02 en séance ; USO +0,24 contre −0,01 ; SMH +0,21 contre −0,34 ; TLT
    +0,14 contre −0,18. URA fait l'inverse (−0,00 contre +0,14).
  - Stops percés : 7 à 17 par ETF, avec un dépassement de +0,7 à +2,4 ATR.
- [OBS] **Long et Short, en brut :**
  - US30 gagne des deux côtés (+0,44 et +0,20), comme HK50 (+0,16 et +0,23) et GDX (+0,23 et +0,59) ;
  - GER40 n'est porté que par ses Longs (+0,77 contre −0,31) : dérive du DAX, composante symétrique de +0,23.
- [OBS] **GBPJPY Saxo :** brut +0,095 et −0,303 à 4 bps, contre −0,035 et −0,443 avec HistData. Même conclusion ; les trous
  de 2023 étaient sans effet.
- [OBS] **Stop de F3 :** il aide US30 (+0,54 [+0,15 ; +0,93]) et nuit à HK50 (−0,49 [−0,94 ; −0,07]) ; ailleurs, l'IC
  contient 0.
- [OBS] **Queues :** médiane de −0,5 à −1,6 ATR, décile supérieur de +0,7 à +1,1 ATR par trade. C'est le profil de BTC, sans
  la moyenne positive.
- [HYP] **Le signal se transpose, la rente non.** Le rapport décisif est brut / ATR contre frais / ATR, comme pour l'or en
  D01.
- [HYP] **US30 :** son brut est symétrique et positif en bps ; sa viabilité dépend du coût réel (écart de 1,4 bp contre
  4 retenus).
- [HYP] **ETF :** effet des nuits sur environ 140 trades, impossible à distinguer du bruit (K8 à K10).

#### 5. Décision
- [ ] **REJETÉ**
- [ ] **NON CONCLUANT**
- [x] **TERMINÉ (descriptif) : aucun actif à IC > 0 au coût principal ; candidats à examiner pour D02 selon le porteur : US30, GER40, US100, GDX, avec le biais de sélection à contrôler hors échantillon. RE-1 inchangée.**

### [DÉCISION] — Clôture de D01, passage à D02 (2026-10-01)
- **Décision du porteur :** D01 est close (D01, D01 bis, D01.5, D01.6, D01.7). Même sans avantage statistiquement
  établi sur tous les actifs, les premiers tests sur SOL et l'or sont jugés assez encourageants pour poursuivre. D01 a
  surtout permis d'identifier les limites de RE-1 en zero-shot et les axes d'adaptation, et d'éclairer l'effet des gaps,
  de l'horizon et des coûts.
- **Étape suivante :** D02, walk-forward et adaptation multi-actifs. Avant toute expérience, `passation.md` est réécrit
  comme document de référence, à relire et valider par le porteur. Aucun calcul de D02 n'est lancé.
- **Faits consignés** au §5 de `RESEARCH_PHILOSOPHY.md` :
  - SOL +0,190 ATR [−0,079 ; +0,484] à 5 bps ;
  - or −0,019 ATR [−0,362 ; +0,349] à 4 bps (brut +0,24, frais 0,26) ;
  - D01.7 : aucun IC > 0 au coût principal.

### [EXP-D02.0, données] — Historiques longs BTC 2013, or 2009, AVAX ; univers de D02 (2026-10-01)
- **Décisions du porteur :**
  - rétro-test de RE-1 figée sur BTC 2013-2019 et l'or 2009-2019 avant tout walk-forward ;
  - coûts actuels gardés sur les années anciennes (convention) ;
  - SOL/USD Coinbase conservé ; **AVAX/USD ajouté à l'univers de D02** ; LINK et LTC non ajoutés ; ETH et XRP strictement
    réservés au hold-out ;
  - BTC retéléchargé par notre script plutôt que copié de NewKalman (provenance documentée) ;
  - panne de Bitstamp de janvier 2015 : données brutes intactes, période non négociable dans le backtest principal,
    sensibilité sur la série brute.
- **Données, audit validé par le porteur** (`experiments/D02_0/audit_donnees_D02_0.md`) :
  - BTC/USD Bitstamp 2013-2025 : 227 904 barres, aucun trou ; 105 216 barres identiques sur 105 216 à la série du dépôt
    sur 2020-2025 ; 8,0 % de barres plates en 2013 ; panne du 2015-01-05 09:30 au 2015-01-09 20:30 (107,5 h plates) ;
  - or HistData 2009-03-15 → 2025 : 198 695 barres, identique à la série de D01 sur 2020-2025, 97,8 à 99,1 % du calendrier
    23/5 par an (2023 : 86 %) ; horloge validée sur 2009-2018 sans la pause, partiellement cotée ces années-là (ouverture
    du dimanche à 18:00 et dernière barre du vendredi à 16:30 New York, pic des annonces de 08:30) ;
  - AVAX/USD Coinbase 2021-09-30 → 2025 : 74 530 barres, 5 trous (24 barres) ;
  - aucun recoupement externe gratuit de l'or : FRED a retiré les cours LBMA, Stooq impose une vérification anti-robot
    (non contournée).
- **Code :** `src/marketdata/bitstamp.py` (+5 tests, 249 au total), `experiments/D02_0/donnees_D02_0.py`,
  `audit_donnees_D02_0.py` ; commit 7dca1f8, poussé avec l'accord du porteur.

### [EXP-D02.0] — Rétro-test de RE-1 figée : BTC/USD 2013-2019 et CFD or 2009-2019
- **Date :** 2026-10-01
- **Étape :** D, préalable de D02 (aucune optimisation). RE-1 strictement gelée ; aucune modification sur la base des
  résultats.
- **Actifs & Période :** BTC/USD Bitstamp 2013-01-01 → 2019-12-31 (panne de janvier 2015 retirée de la série vue par RE-1,
  sensibilité sur la série brute) ; CFD or HistData 2009-03-15 → 2019-12-31 ; aucune barre de 2020 ni de 2026 lue.
  Références 2020-2025 : BTC (C02bis, D01) et or (D01).
- **Frais :** BTC 5 bps (lecture principale) et 10 bps ; or 4 bps ; coûts actuels sur les années anciennes (convention du
  porteur).
- **Livrables :** `experiments/D02_0/run_D02_0.py`, `narratif_D02_0.md`, `rapport_D02_0.md`, `resultats_D02_0.csv`,
  `annuel_D02_0.csv`, `diagnostics_D02_0.json`, `controles_D02_0.json`, `figures/D02_0.png`.

#### 0. Cadrage obligatoire
- **QUESTION :** RE-1 figée garde-t-elle une espérance nette sur des périodes qu'elle n'a jamais vues ?
- **PERTINENCE POUR LE FILTRE AKF :** seuils et géométrie R2 viennent de BTC 2020-2025 ; des régimes plus anciens testent
  leur stabilité dans le temps, sans adaptation ; c'est la référence figée du walk-forward de D02.
- **CE QUE LE PROTOCOLE MESURE RÉELLEMENT :** 8 métriques nettes à 0,25 %/ATR et à 1x, espérance avec IC par grappes
  mensuelles, années, Long/Short, F2b/F3, populations face aux seuils gelés, frais en ATR ; panne de 2015, marché étroit
  de 2013, lecture hors 2013.
- **CE QU'IL NE PERMET PAS DE CONCLURE :** rien sur 2026 ; coûts anciens sous-estimés par convention ; aucun critère de
  réussite ni comparaison statistique avec 2020-2025 ; aucune modification de RE-1.

#### 1. Hypothèse & Motivation physique
- Si la cinématique captée par RE-1 sur BTC 2020-2025 est structurelle, elle doit produire un brut positif sur des
  périodes antérieures, à seuils identiques.

#### 2. Règle testée
- **Règle :** RE-1 identique à C02bis, seuils BTC 2020-2025 gelés.
- **Contrôles bloquants :** 1 080 trades de C02bis reproduits sur BTC 2020-2025 (40 métriques, écart ≤ 4,5·10⁻⁶) ;
  empreintes des CSV égales à l'audit validé ; barres de la panne vérifiées identiques à la suite plate de l'audit avant
  leur retrait.
- **Écart au cadrage, sans effet :** un trade ouvert en fin de période est clos à la dernière barre (convention de C02bis),
  et non écarté comme annoncé ; aucun trade concerné.

#### 3. Résultats nets
| Lecture (coût) | PnL net : 0,25 %/ATR ; 1x ; bps cumulés (1x) | PF (1x) | WR | Espérance ATR [IC] ; bps | MDD : 0,25 %/ATR ; 1x | Trades (/mois) | Durée médiane | Part des frais (1x) ; brut ATR ; frais ATR |
|---|---|---|---|---|---|---|---|---|
| BTC 2013-2019 (5) | −20 % ; −63 % ; −3 298 | 0,97 | 42,3 % | −0,045 [−0,244 ; +0,157] ; −2,4 | −48,5 % ; −91,6 % | 1 357 (16,2) | 26 barres ; 13 h | 195 % ; +0,056 ; 0,101 |
| BTC 2013-2019 (10) | −42 % ; −81 % ; −10 083 | 0,92 | 41,0 % | −0,146 [−0,346 ; +0,057] ; −7,4 | −56,7 % ; −94,2 % | 1 357 (16,2) | 13 h | 389 % |
| BTC 2014-2019 (5) | −22 % ; −43 % ; −2 190 | 0,98 | 42,5 % | −0,065 [−0,278 ; +0,152] ; −1,9 | −47,4 % ; −84,5 % | 1 180 (16,4) | 13 h | 159 % ; +0,040 ; 0,105 |
| BTC brut, panne gardée (5) | −20 % ; −64 % ; −3 437 | 0,97 | 42,2 % | −0,047 [−0,247 ; +0,156] ; −2,5 | −48,8 % ; −91,7 % | 1 357 (16,2) | 13 h | 203 % |
| Or 2009-2019 (4) | −3 % ; −5 % ; −272 | 0,99 | 41,7 % | +0,011 [−0,246 ; +0,258] ; −0,2 | −29,1 % ; −29,3 % | 1 253 (9,7) | 26 barres ; 13 h | 106 % ; +0,304 ; 0,293 |
| BTC 2020-2025 (5, réf.) | +138 % ; +204 % ; +13 320 | 1,20 | 44,3 % | +0,369 [+0,098 ; +0,645] ; +12,3 | −13,5 % ; −43,9 % | 1 080 (15,0) | 13 h | 29 % ; +0,504 ; 0,136 |
| Or 2020-2025 (4, réf.) | +1 % ; +5 % ; +697 | 1,04 | 42,5 % | −0,019 [−0,362 ; +0,349] ; +1,1 | −13,6 % ; −13,3 % | 651 (9,0) | 13 h | 79 % ; +0,239 ; 0,257 |

- **Années à espérance positive :** BTC 4/7 (2014 −0,740, 2015 −0,272, 2016 −0,002 ; 2017 +0,469) ; or 7/11 (2009-2015
  toutes positives, 2016-2019 toutes négatives).

#### 4. Analyse causale & Physique du trade
- [OBS] **BTC : le brut manque, pas le coût.** Brut +0,056 ATR contre +0,504 en 2020-2025 ; frais 0,10 ATR (ATR de 30 min
  plus large : P50 63,5 bps contre 49,7).
- [OBS] **BTC : le timing disparaît** (−0,061 [−0,259 ; +0,141] contre +0,362) ; Long +0,128, Short −0,249 ; F2b −0,224
  (765 trades) contre +0,459, F3 +0,185 ; stop de F3 sans effet significatif (−0,128 [−0,368 ; +0,095]).
- [OBS] **BTC : populations proches des seuils gelés** (101 signaux par mois ; médiane locale de `leg_atr` 2,59 ; P75 local
  de `nis_z_100` 1,135). Bande > P90 de `nis_z_100` (écartée par le veto, trades isolés) : +0,60 [+0,20 ; +1,03] sur 256
  trades, contre −0,40 en 2020-2025.
- [OBS] **Panne de 2015 sans effet :** aucun trade créé sur les barres plates ni à cheval ; un seul trade diffère
  (2015-01-11 : +0,58 contre −1,93 ATR) ; −0,045 contre −0,047. Marché étroit de 2013 : un seul trade touché ; hors 2013,
  −0,065.
- [OBS] **Or :** brut +0,304 ATR (log +0,305 [+0,053 ; +0,551]), réalisé en séance, absorbé par 0,293 ATR de frais ;
  2009-2015 brut +0,30 à +0,85 (ATR 13,5-19 bps), 2016-2019 brut −0,57 à +0,05 et frais 0,36-0,37 ATR (ATR vers 11 bps) ;
  F2b/F3 de signes opposés à ceux de 2020-2025.
- [HYP] **Sur BTC, l'avantage de RE-1 n'est pas stationnaire :** sélection en échantillon pendant la construction
  (A01 → C05) ou changement de régime (marché spot étroit avant 2017) ; non séparables ici. 2026 reste le seul hors
  échantillon de BTC, non vierge : il a été vu par d'anciens projets (`passation.md` §2.1 ; correction du 2026-10-01,
  la première version disait « vierge »).
- [HYP] **Sur l'or, un brut de +0,25 à +0,30 ATR persiste sur 17 ans** ; le net dépend du rapport brut / frais en ATR (K11)
  et du régime.
- [HYP] **Pour D02 :** la référence figée dépend de la période ; le walk-forward devra montrer un gain sur ces périodes
  aussi ; l'inversion de la bande > P90 désigne les seuils de population comme lieu de la non-stationnarité.

#### 5. Décision
- [ ] **REJETÉ**
- [ ] **NON CONCLUANT**
- [x] **TERMINÉ (descriptif) : BTC 2013-2019 sans espérance nette (estimation négative, IC contenant 0) ; or 2009-2019 net nul, brut positif. Panne de 2015 sans effet. RE-1 inchangée. Univers de D02 : AVAX ajouté.**

### [EXP-D02] — Walk-forward de RE-1 : protocole d'adaptation dynamique (BTC, SOL, AVAX, or) — cadrage validé
- **Date :** 2026-10-01
- **Étape :** D, D02. Protocole écrit par le porteur, audité par l'agent, puis arbitré par le porteur (six points).
  GO pour la documentation, le code (`src/optimization/`) et le contrôle bloquant Gate 0 ; la grille ne part que sur
  un second GO, après lecture du rapport de Gate 0.
- **Actifs & Période :** une passe indépendante par actif, sans aucun paramètre ni seuil mutualisé.
  - BTC/USD Bitstamp 2013-2025, panne de janvier 2015 retirée (convention de D02.0) ;
  - SOL/USD Coinbase dès le 2021-06-17 ; AVAX/USD Coinbase dès le 2021-09-30 ;
  - CFD or XAU/USD HistData dès le 2009-03-15 ;
  - barres de 30 min jusqu'au 2025-12-31 ; 2026, ETH et XRP ne sont pas lus.
- **Modèle de frais :** convention de RE-1, 5 bps aller-retour sur les cryptos et 4 bps sur l'or. Lecture de stress à
  10 bps sur les séries hors échantillon, avec les paramètres choisis au coût principal, sans réoptimisation. Capital à
  0,25 % par ATR14(t), levier ≤ 1x ; PnL et MDD à 1x publiés à côté.

#### 0. Cadrage (format du porteur ; champs du §4.6 inclus)
- **QUESTION :** recalibrer chaque semestre H, R0 ou la frontière F2b/F3, un à un puis ensemble, apporte-t-il hors
  échantillon une valeur nette face à RE-1 gelée et à une calibration statique ?
- **PERTINENCE POUR LE FILTRE AKF :**
  - R0 est le seul axe sensible du moteur sous le reset de P (`RESEARCH_PHILOSOPHY.md` §4.4) ;
  - H fixe le moment où le jugement cinématique fait à t est encaissé (K9) ;
  - la frontière ne change pas la population de RE-1 (petite jambe, retracement ≥ 0,50, x1 retourné) : elle décide
    seulement quels trades portent le stop SL-B ;
  - D02.0 a montré que l'avantage de RE-1 dépend de la période (K12).
- **DONNÉES :** séries ci-dessus, empreintes conformes à leurs `.meta.json`. Fenêtres semestrielles calendaires :
  60 semestres hors échantillon (BTC 22 de 2015 à 2025, or 29 du S2 2011 à 2025, SOL 5 du S2 2023 à 2025, AVAX 4 de
  2024 à 2025), chiffres du porteur vérifiés.
- **MÉTHODE :**
  - **Fenêtres :** apprentissage (IS) = les 4 semestres qui précèdent chaque semestre de test (OOS), soit 24 mois pour
    6 (80/20) ; premier OOS = premier semestre dont l'IS commence à la première barre de la série ou après.
  - **Atlas :** un par valeur de R0 ∈ {10, 50, 100, 200, 500}, calculé par le moteur certifié sur toute la série
    (paramètre transmis à `anatomy.build_atlas`, `src/indicator/` intouché).
  - **Seuils de population :** P50 de `leg_atr` et P75 de `nis_z_100` réestimés sur les signaux de chaque IS, pour
    chaque R0, puis gelés pour le semestre OOS suivant ; aucun quantile sur l'historique entier.
  - **Grille exhaustive** (pas d'Optuna) : H de 6 à 60 barres au pas de 2 (28 valeurs, cooldown = H), R0 (5 valeurs),
    frontière de 0,75 à 0,95 au pas de 0,05 (5 valeurs). Branches OFAT, les autres paramètres aux valeurs de RE-1, et
    branche conjointe (5 × 28 × 5 = 700 combinaisons par IS), espace fixé a priori. 42 000 évaluations IS ; les
    36 configurations distinctes de l'OFAT font partie de la grille conjointe.
  - **Choix en IS** (règle du porteur, forme opérationnelle validée) :
    - admissible : E[ATR] net > 0 et MDD < 0 sur l'IS ;
    - score : moyenne du Calmar net (0,25 %/ATR) de la configuration et de ses voisins immédiats, ±1 pas sur un axe
      (R0 par rang) ; un voisin inadmissible compte pour sa propre valeur ;
    - choix au score maximal parmi les admissibles ; à égalité, le plus proche de RE-1 ; aucun admissible : paramètres
      de RE-1 avec les seuils de la fenêtre ;
    - conventions techniques de l'agent, à confirmer avec Gate 0 : un Calmar indéfini (aucun trade, MDD nul) compte
      pour 0 ; « le plus proche » se mesure en pas de grille (distance L1), puis par ordre lexicographique.
  - **Séries hors échantillon** (10 par actif, capital continu, mêmes dates) : RE-1 gelée (seuils BTC gelés), Contrôle
    (paramètres de RE-1, seuils réestimés seuls), puis Statique (choix de l'IS 1 gelé sur tout l'OOS) et WFO (choix
    semestriel) pour H, R0, frontière et conjointe. Tous, hors RE-1 gelée, partagent la politique de seuils réestimés.
  - **Étanchéité :** un trade d'IS encore ouvert est clos à la dernière barre de son IS (aucune barre OOS ne sert au
    choix) ; une position ouverte en fin de semestre OOS garde jusqu'à sa clôture les règles de son entrée ; un trade
    ouvert le 2025-12-31 est clos à la dernière barre de 2025.
  - **Moteur :** noyau Numba qui reprend `envelope.stop_trades` (`dynamic=False`), avec H et niveau de stop par signal ;
    métriques de `strategy.re1`. VectorBT est abandonné (décision du porteur).
  - **Gate 0, bloquant avant toute grille :**
    - le noyau reproduit les 1 080 trades de RE-1 sur BTC 2020-2025 (`strategy.run_re1`) : 0 trade manquant ou fantôme,
      écart relatif ≤ 10⁻⁵ sur le PnL cumulé et l'espérance en ATR ;
    - parité hors du point de RE-1 (H, frontière, R0, paramètres qui changent à une frontière de semestre) ;
    - ancres : RE-1 gelée redonne D01 (SOL, or 2020-2025) et D02.0 (BTC 2013-2019, or 2009-2019) ;
    - fenêtres 22 / 29 / 5 / 4, empreintes des données, garde 2026, seuils lus sur l'IS seul.
- **CRITÈRE DE LECTURE :**
  - **« Statistiquement tangible »** : écart apparié par mois (mêmes tirages, 2 000, graine fixe), IC 95 % entièrement
    au-dessus de 0 sur l'espérance (ATR et bps) et sur le rendement. MDD et Calmar se lisent sur chemins réordonnés
    (part des chemins, plage P2,5-P97,5) ; « ne dégrade pas le MDD » : plage pas entièrement défavorable.
  - **Règles de décision du porteur :** chaque variante est jugée face à RE-1 gelée ; un WFO n'est retenu face à son
    Statique que si son gain de Calmar et d'espérance est tangible sans dégrader le MDD (sinon, le Statique est
    préféré) ; la conjointe doit dépasser les meilleures variantes 1D et statiques ; si aucune variante ne dépasse
    significativement RE-1 sur le profil global (rendement net, Calmar, MDD, espérance), absence de valeur ajoutée
    démontrée, RE-1 inchangée.
  - **Lus aussi :** effet propre de chaque paramètre contre le Contrôle (même politique de seuils) ; stabilité des
    paramètres choisis ; cartes IS ; effet de H sur entrées figées (I-M16) ; brut, frais et queues ; nombre de
    configurations et de comparaisons publié.
  - **Ce qu'il ne permet pas de conclure :**
    - BTC 2020-2025 a servi à construire RE-1 : aucun de ces semestres n'est vierge, pour aucune variante ;
    - avant 2020, RE-1 gelée porte des seuils estimés sur 2020-2025 : c'est une référence fixe, pas une stratégie
      causale ;
    - SOL et AVAX : 4 à 5 semestres hors échantillon, puissance faible ;
    - les Statiques de BTC sont tirés de l'IS 2013-2014 (marché étroit ; 2014 à −0,740 ATR en D02.0) ;
    - environ 50 comparaisons à 95 % : quelques résultats « significatifs » sont attendus par hasard ;
    - ni portage (funding, emprunt du short, financement de nuit) ni glissement au-delà des frais ; hold-out non lu.
- **Sensibilités de BTC (annexe) :** panne de 2015 sur la série brute (fenêtres touchées recalculées) ; 2013 retiré de la
  lecture (OOS dès le S1 2016, Statique tiré de l'IS 2014-2015, mêmes fenêtres).

#### Décisions du porteur (2026-10-01)
- Protocole EXP-D02 adopté ; l'audit de l'agent (étanchéité, contrôles, limites) est validé.
- Arbitrages : (1) noyau Numba sur `stop_trades`, VectorBT abandonné ; (2) grille exhaustive seule ; (3) score de
  voisinage ; (4) écart apparié par mois ; (5) sensibilités de BTC ; (6) stress à 10 bps.
- Sa réponse « pas de critère a priori » (relecture de `RESEARCH_PHILOSOPHY.md` §3.1) vise les seuils et vetos
  proposés par l'agent ; la règle de choix en IS, fixée par le porteur avant toute mesure, est une consigne.
- Écarts signalés : le moteur de référence est `src/strategy/re1.py` (le protocole écrit `src/strategy.py`) ; stress à
  10 bps appliqué aussi à l'or (coût principal 4 bps), à confirmer.

#### Gate 0 — passé (2026-10-01)
*`experiments/D02/run_D02.py --gate0`, 54 s, rapport `experiments/D02/gate0_D02.md`. Aucun calcul de recherche :
reproduction de résultats publiés et parité du noyau, sans aucune performance calculée hors du point de RE-1.*
- [CODE] Commits `e2728f8` (docs) et `698d688` (`src/optimization`, 291 tests réussis, 2 ignorés).
- [OBS] **G0-1 :** le noyau Numba redonne les 1 080 trades de RE-1 sur BTC 2020-2025, identiques au bit près à
  `strategy.run_re1` (0 manquant, 0 fantôme) ; écart au CSV de C02bis, arrondi à 6 chiffres, ≤ 3,1·10⁻⁶.
- [OBS] **G0-2 :** parité trade par trade à H = 6 et 60, frontière 0,75 et 0,95, R0 = 10 et 500, et avec des paramètres
  qui changent à chaque semestre (530 trades, référence Python indépendante ; un trade à cheval sur deux semestres
  garde l'horizon de son signal).
- [OBS] **G0-3 :** ancres reproduites (SOL +0,190 et +0,129 ATR ; or −0,019 ; BTC 2013-2019 −0,045 et −0,146 ; or
  2009-2019 +0,011), écart aux CSV ≤ 4,5·10⁻⁶.
- [OBS] **G0-4 à G0-6 :** empreintes égales aux audits ; 22 / 29 / 5 / 4 semestres hors échantillon ; panne de 2015
  (215 barres) ; aucune barre de 2026 lue ; seuils de la fenêtre 2020-2025 égaux aux seuils gelés au bit près ;
  métriques d'IS égales à `strategy.metrics`.
- [OBS] Coût : environ 0,04 ms par évaluation d'IS ; les 42 000 évaluations tiennent en quelques secondes, les 20 atlas
  en quelques minutes.
- [OBS] En cours de route : le nombre de signaux ne varie pas de façon monotone avec R0 (8 mois de BTC : R0 = 10, 50,
  100 → 651, 834, 797 signaux) ; une hypothèse inverse dans un test a été corrigée.
- [HYP] Effet de bord de la lecture littérale du score de voisinage : une case en bord de grille, moins entourée, peut
  l'emporter sur le centre d'un plateau (exemple : Calmar [−2 ; 5 ; −2 ; 1,5 ; 1,6 ; 1,5] : 1,55 au bord, 1,533 au
  centre). Soumis au porteur avant la grille.

#### Arbitrages du porteur pour la grille (second GO, 2026-10-01)
- **Règle de choix en IS :** variante topologique. On retient la plus grande zone connexe de la grille (voisins à ±1 pas
  sur un axe) où le Calmar net est > 0, puis la configuration la plus proche de son centre géométrique. L'option
  « voisin absent = 0 » est rejetée : elle postulerait une falaise au-delà de la grille.
- **Calmar indéfini** (aucun trade, rendement nul) : score 0, jamais choisi ; on ne sélectionne pas un système inactif.
- **Stress de coût :** 10 bps sur BTC, SOL et AVAX ; 6 bps sur l'or (coût principal 4 bps). 10 bps est une structure de
  frais de preneur propre à la crypto.
- **Statistiques de comparaison** (écarts appariés par mois, IC 95 %) écrites et testées avant la grille.
- Push autorisé pour `e2728f8`, `698d688` et le commit de Gate 0 ; second GO donné pour les 20 atlas, les 42 000
  évaluations d'IS, les séries hors échantillon et le rapport de D02.

#### Résultats de la grille (2026-10-01, `run_D02.py --grille`, 319 s ; `rapport_D02.md`)
*42 000 évaluations d'IS (règle de la zone connexe), 40 séries hors échantillon, 146 comparaisons appariées publiées
(92 au coût principal). Contrôles bloquants de Gate 0 repassés en tête. Commit du code : `457a1ed`.*

| Actif · série (coût) | PnL : 0,25 %/ATR ; 1x ; bps (1x) | PF (1x) | WR | Espérance ATR [IC] ; bps | MDD : 0,25 %/ATR ; 1x | Trades (/mois) | Durée médiane | Part des frais (1x) ; brut ; frais (ATR) |
|---|---|---|---|---|---|---|---|---|
| BTC · RE-1 gelée (5) | +159 % ; +396 % ; +21 149 | 1,15 | 43,9 % | +0,218 [+0,032 ; +0,401] ; +10,2 | −28,4 % ; −53,0 % | 2 075 (15,7) | 13 h | 33 % ; +0,34 ; 0,12 |
| BTC · Contrôle (5) | +114 % ; +221 % ; +16 162 | 1,12 | 43,0 % | +0,194 [+0,000 ; +0,399] ; +8,5 | −27,9 % ; −48,4 % | 1 909 (14,5) | 13 h | 37 % ; +0,32 ; 0,13 |
| BTC · WFO-R0 (5) | +214 % ; +478 % ; +22 133 | 1,18 | 43,6 % | +0,291 [+0,088 ; +0,499] ; +12,1 | −15,8 % ; −40,6 % | 1 836 (13,9) | 13 h | 29 % ; +0,42 ; 0,13 |
| BTC · WFO-H (5) | −2 % ; −20 % ; +2 260 | 1,02 | 42,4 % | +0,019 [−0,202 ; +0,244] ; +1,2 | −46,0 % ; −69,8 % | 1 847 (14,0) | 13 h | 80 % ; +0,14 ; 0,13 |
| BTC · WFO-conjointe (5) | +11 % ; −39 % ; +191 | 1,00 | 41,2 % | +0,049 [−0,190 ; +0,284] ; +0,1 | −34,0 % ; −60,9 % | 1 591 (12,1) | 16 h | 98 % ; +0,17 ; 0,12 |
| SOL · RE-1 gelée (5) | +27 % ; +114 % ; +9 443 | 1,25 | 45,2 % | +0,252 [−0,191 ; +0,712] ; +23,3 | −13,1 % ; −42,3 % | 405 (13,5) | 13 h | 18 % ; +0,32 ; 0,07 |
| SOL · WFO-conjointe (5) | +26 % ; +78 % ; +7 539 | 1,20 | 48,2 % | +0,261 [−0,199 ; +0,731] ; +19,7 | −19,1 % ; −59,1 % | 382 (12,7) | 13 h | 20 % ; +0,33 ; 0,07 |
| AVAX · RE-1 gelée (5) | +5 % ; −17 % ; −536 | 0,99 | 42,6 % | +0,074 [−0,301 ; +0,431] ; −1,6 | −16,5 % ; −52,9 % | 329 (13,7) | 13 h | 148 % ; +0,14 ; 0,06 |
| AVAX · WFO-conjointe (5) | −18 % ; −48 % ; −5 166 | 0,87 | 39,4 % | −0,238 [−0,615 ; +0,163] ; −16,0 | −23,3 % ; −61,2 % | 322 (13,4) | 15 h | brut ≤ 0 ; −0,17 ; 0,06 |
| XAU · RE-1 gelée (4) | −10 % ; −7 % ; −388 | 0,99 | 41,4 % | −0,045 [−0,273 ; +0,177] ; −0,2 | −31,9 % ; −32,1 % | 1 637 (9,4) | 13 h | 106 % ; +0,24 ; 0,29 |
| XAU · WFO-conjointe (4) | −14 % ; −15 % ; −1 151 | 0,97 | 40,9 % | −0,067 [−0,377 ; +0,232] ; −0,9 | −24,6 % ; −24,7 % | 1 322 (7,6) | 20 h | 128 % ; +0,22 ; 0,29 |

- [OBS] **Aucune variante ne surpasse RE-1 gelée, sur aucun actif ; aucun WFO n'est retenu face à son Statique.**
  Sur 92 comparaisons au coût principal : aucun gain d'espérance tangible en ATR et en bps à la fois ; un seul gain
  de rendement tangible (WFO-R0 contre Statique-R0 sur BTC, +9,8 %/an [+0,4 ; +19,5]).
- [OBS] **Le recalibrage dégrade plus souvent qu'il n'améliore :** 8 écarts d'espérance significativement négatifs en ATR,
  contre 1 positif. WFO-H sur BTC fait −0,174 ATR [−0,276 ; −0,074] face à Statique-H ; WFO-R0 sur l'or fait −0,150
  [−0,294 ; −0,021] face au Contrôle.
- [OBS] **BTC, WFO-R0 :** +0,291 ATR [+0,088 ; +0,499], MDD −15,8 % (0,25 %/ATR), Calmar 0,69, 10 années sur 11. L'écart
  à RE-1 gelée (+0,218) n'est pas significatif : +0,074 [−0,067 ; +0,225]. R0 choisi : 200 jusqu'au S1 2017, puis 50,
  puis 100 dès le S2 2018 (mêmes trades que le Contrôle ensuite). Le gain tient à 2015 (+0,535 contre −0,272) et à
  2018 ; lu dès 2016, +0,004 [−0,114 ; +0,134].
- [OBS] **BTC par période :** RE-1 gelée +0,064 ATR en 2015-2019 et +0,357 en 2020-2025 ; Statique-R0 (R0 = 200, tiré de
  2013-2014) +0,301 puis −0,191 ; Statique-conjointe (200, 36, 0,85) +0,337 puis −0,077. Chaque calibration vaut pour
  son époque.
- [OBS] **H :** choix instable (12 à 50 barres). Sur les entrées figées du Contrôle, l'horizon choisi ne change rien
  (−0,008 ATR [−0,121 ; +0,116]) : la perte de WFO-H vient du calendrier des trades (I-M16).
- [OBS] **Frontière :** inerte, 0,85 dans 21 semestres sur 22 sur BTC. **Seuils réestimés seuls (Contrôle) :** sans effet
  mesurable (BTC −0,024 [−0,093 ; +0,049]).
- [OBS] **Conjointe :** R0 change souvent ; H de 30 à 44 sur BTC. Les zones retenues couvrent 107 à 559 cases sur 700
  (médiane 280) : le centre de la zone retombe près du centre de la grille.
- [OBS] **Or :** toutes les séries perdent (−0,045 à −0,196 ATR ; brut +0,09 à +0,24 pour 0,29 ATR de frais). **SOL,
  AVAX :** IC de ±0,4 à ±0,7 ATR, rien de distinct de RE-1 gelée.
- [OBS] **Stress :** à 10 bps, aucune série de BTC n'a d'IC > 0 (RE-1 gelée +0,093 [−0,094 ; +0,277], WFO-R0 +0,165
  [−0,043 ; +0,373]) ; à 6 bps, l'or perd partout (−0,19 à −0,34). **Panne de 2015 :** sans effet (≤ 0,002 ATR).
- [HYP] Sur BTC, les réglages valent pour une époque ; un recalibrage semestriel sur 24 mois ne suit pas le basculement
  de façon fiable (WFO-R0 l'a suivi en 2017-2018, a manqué 2019).
- [HYP] Recalibrer H ne fait que déplacer le calendrier des trades ; la règle de la zone et de son centre, sur une grille
  où H compte 28 pas contre 5, ramène le choix vers le centre de la grille (effet géométrique).

#### Décision
- [ ] **REJETÉ**
- [x] **NON CONCLUANT au sens du protocole : aucune valeur ajoutée démontrée du walk-forward, par actif comme
  conjointement. RE-1 inchangée.** La suite (hold-out, autre cadrage) est à décider par le porteur.


### [DÉCISION] — Suite de D02 : RE-1 gelée gardée, WFO-R0 à creuser (2026-10-02)
- **Décision du porteur, après lecture de D02 :** RE-1 gelée reste la piste principale ; le walk-forward de R0 est à
  creuser ; le multi-actif est mis de côté pour le moment. Le porteur juge bons les résultats de RE-1 et de WFO-R0.
- **Faits contraires déjà consignés** (§5 de `RESEARCH_PHILOSOPHY.md`, entrée EXP-D02) : l'écart WFO-R0 − RE-1 gelée
  n'est pas significatif (+0,074 ATR [−0,067 ; +0,225]) et vient de 2015 et 2018 (+0,004 lu dès 2016).
- **Relecture de l'agent sur les sorties de D02** (récapitulatif du 2026-10-02, cadrage du 2026-10-03, sans calcul) :
  - la perte de WFO-H vient de la population de trades, pas des sorties : 138 trades du Contrôle perdus (+48,7 bps
    en moyenne), 76 ajoutés (−16,0 bps) ; le cooldown suit H ;
  - WFO-R0 sur BTC ne s'est jamais replié sur RE-1 (0 semestre sur 22) ; le départage vers RE-1 a tranché 12 semestres
    (zones de 2 ou 4 cases) ; de 2022 à 2025, R0 = 100 gagne sur le Calmar IS lui-même ;
  - sur H, la règle du centre suit la grille plus que le profil : 7 semestres sur 22 ont une zone de 23 à 28 cases et
    un choix de 32 à 38 barres ; en 2018-S2 et 2019-S1, le meilleur Calmar IS est à H = 14 (+2,97 ; +3,96), le choix
    à 32 (+0,42 ; +0,50) ;
  - avec un verrou de 26 barres et H > 26, l'entrée suivante tombe avant la sortie pour 3 % (H = 28) à 42 % (H = 60)
    des 2 075 trades de RE-1 gelée.
- **Correction de l'agent :** dans le récapitulatif, « à partir de 2022, R0 = 100 est la seule valeur positive » est
  inexact. C'est vrai dès le S2 2024 ; de 2022 au S1 2024, R0 = 500 (+0,09 à +0,47) et R0 = 10 (+0,38 ; +0,07) étaient
  positifs mais isolés, et R0 = 100 avait le meilleur Calmar IS.

### [EXP-D02.1] — Verrou fixe et WFO de H_exit ; WFO de R0 sur grille fine avec inertie ; stress (BTC) — cadrage validé
- **Date :** 2026-10-03
- **Étape :** D, D02.1. Demande du porteur (2026-10-03), cadrage de l'agent en quatre champs, arbitrages du porteur
  (cinq points), GO pour le code, le contrôle de non-régression, D02.1a puis D02.1b. Push de 457a1ed et 8a2212e
  autorisé (fait, origin = 8a2212e).
- **Décision de méthode du porteur, pour tous les tests futurs (statiques ou WFO) :** le verrou (cooldown) est une
  constante de 26 barres, distincte de l'horizon de sortie H_exit. Elle ne change rien à RE-1 ni au WFO-R0 (H = 26).
- **Actifs & Période :** BTC/USD Bitstamp 2013-2025, panne de janvier 2015 retirée ; 22 semestres hors échantillon, du
  S1 2015 au S2 2025 ; IS = 24 mois. 2026, ETH et XRP ne sont pas lus ; le multi-actif est mis de côté.
- **Modèle de frais :** 5 bps aller-retour (choix en IS, lecture principale), 10 bps en stress ; 0,25 % du capital par
  ATR14(t), levier ≤ 1x ; PnL et MDD à 1x publiés à côté.

#### 0. Cadrage (validé)
- **D02.1a — QUESTION :** à entrées identiques à celles de RE-1 gelée (verrou de 26 barres), recalibrer chaque semestre
  l'horizon de sortie H_exit améliore-t-il le résultat ?
  - **MÉTHODE :** RE-1 gelée (seuils BTC gelés, R0 = 100, frontière 0,85, ses 2 075 entrées) ; H_exit de 6 à 60 au
    pas de 2 ; option C du porteur : si H_exit > 26 et qu'une entrée survient alors que le trade précédent est ouvert,
    elle clôt la position (une position, levier ≤ 1x) ; choix par semestre avec la règle de D02 inchangée (centre de la
    plus grande zone à Calmar > 0, égalités et repli vers H = 26), pour isoler l'effet du verrou ; annexe : effet trade
    par trade sans la coupure (entrées figées, I-M16).
- **D02.1b — QUESTION :** avec 9 valeurs de R0 et l'inertie à la place du départage vers RE-1, que deviennent
  l'espérance nette et le profil de risque du WFO-R0 ?
  - **MÉTHODE :** WFO-R0 de D02 à l'identique (H = 26, verrou 26, frontière 0,85, seuils réestimés sur chaque IS et
    pour chaque R0), grille {10, 25, 50, 75, 100, 150, 200, 300, 500} (centre en rang de grille) ; inertie : égalité au
    centre → la case la plus proche du R0 de la fenêtre précédente (première fenêtre : meilleur Calmar IS) ; aucune
    zone → R0 précédent (première fenêtre : meilleur Calmar IS défini). Décomposition 2 × 2 (grille 5 / 9 × règle de D02
    / inertie) ; candidate = grille 9 avec inertie, les trois autres cases servent seulement à attribuer l'écart.
- **Stress (porteur : pour toutes les séries et tous les comparateurs) :** 10 bps ; retrait du 1 % meilleur (⌈1 % · n⌉
  trades, classés par rendement net en ATR, chaque série retire les siens) ; les deux combinés.
- **CRITÈRE DE LECTURE (sans seuil) :** 8 métriques à 0,25 %/ATR et à 1x ; écarts appariés par mois avec RE-1 gelée et
  les séries de D02 (espérance en ATR et en bps avec IC, rendement, MDD et Calmar sur chemins réordonnés ; règle
  « surpasse » de D02 rapportée) ; effet trade par trade à entrées égales ; paramètres choisis et cartes IS ; périodes
  2015-2019 et 2020-2025 ; médiane, moyenne, décile supérieur.
- **Contrôle de non-régression (bloquant, avant tout résultat) :** données ; Gate 0 de D02 repassé sur BTC 2020-2025 ;
  D02 reproduit avec le verrou par défaut (cartes IS, choix, séries RE-1 gelée, Contrôle, WFO-R0, WFO-H) ; verrou ≥ H
  identique à `envelope.lock_trades` (D01.6) ; entrées constantes à chaque H de la grille avec le verrou de 26.
- **Code :** `optimization.engine` (`lock`, option C, `superseded`), `selection.select_plateau` (inertie),
  `walkforward` (`GRID_R0_FIN`, `axis_schedule`, verrou et seuils gelés en IS), `compare.drop_best` ; 321 tests.

#### Résultats (BTC 2015-2025, 5 bps sauf mention ; `experiments/D02_1/rapport_D02_1.md`)
- **Contrôle de non-régression passé** (174 s, commit 466d767) : données ; 1 080 trades de RE-1 ; D02 reproduit au bit
  près avec le verrou par défaut (cartes IS, choix, séries RE-1 gelée, Contrôle, WFO-R0, WFO-H) ; verrou ≥ H identique
  à `lock_trades` ; 2 075 entrées identiques pour les 28 valeurs de H avec le verrou de 26.
- [OBS] **D02.1a :** WFO-H_exit +0,246 ATR [+0,028 ; +0,467], +10,0 bps, PnL +173 % (1x +335 %), MDD −28,4 % (1x −53,0 %).
  - face à RE-1 gelée : +0,029 ATR [−0,075 ; +0,139], −0,2 bps [−4,9 ; +4,7] ; même écart trade par trade, +0,035 sans
    la coupure de l'option C ;
  - face au WFO-H de D02 : +0,227 [+0,090 ; +0,365], règle « surpasse » remplie ;
  - H choisi : 26 pendant 5 semestres (replis), puis de 26 à 48, surtout 32 à 38 ; 10 semestres sur 22 ont une zone de
    23 à 28 cases (I-M18) ; 137 trades (6,6 %) clos par l'entrée suivante.
- [OBS] **D02.1b :** grille 9 avec inertie +0,253 ATR [+0,035 ; +0,465], PnL +168 % (1x +441 %), MDD −35,7 % (1x −56,3 %),
  Calmar 0,26.
  - face à RE-1 gelée : +0,036 [−0,151 ; +0,236] ; face au WFO-R0 de D02 : −0,038 [−0,209 ; +0,130], MDD −19,7 points ;
  - 2015-2019 : +0,304 (RE-1 gelée +0,064, WFO-R0 de D02 +0,205) ; 2020-2025 : +0,216 (RE-1 gelée +0,357) ;
  - 2022 : −0,562 ATR, −24,1 % (R0 = 50, 75 puis 25).
- [OBS] **Décomposition :** l'inertie sur la grille 5 ne change que 2018-S2 (50 au lieu de 100) et coûte −0,065 ATR
  [−0,155 ; −0,002] (2018 : −0,160 contre +0,482). Grille 9 face à grille 5 : −0,019 [−0,186 ; +0,145] ; inertie sur la
  grille 9 : −0,019 [−0,063 ; +0,016].
- [OBS] **Stress (toutes les séries) :** à 10 bps, aucun IC > 0. Sans le 1 % meilleur, RE-1 gelée fait +0,035 ATR
  [−0,128 ; +0,199] et +9 %, et toutes les séries tombent entre −0,17 et +0,10 ATR. Les deux combinés : toutes négatives
  (RE-1 gelée −0,089).
- [OBS] **Queue de RE-1 gelée :** 21 trades (1 %) font 84 % de la somme nette en ATR et 91 % de la croissance log du
  capital. Ouverts à ATR bas (32 bps contre 57), aucun stoppé, répartis sur 10 des 11 années (K14).
- [HYP] Les sorties ne portent pas l'avantage. R0 se choisit mal sur 24 mois, et l'avance du WFO-R0 de D02 tenait à un
  départage vers le point de RE-1 (I-M19). RE-1 récolte des expansions de volatilité nées d'états calmes.

#### Décision
- [ ] **VALIDÉ**
- [x] **NON CONCLUANT : aucune des deux modifications ne surpasse RE-1 gelée (règle de D02). RE-1 gelée reste la
  référence ; le verrou fixe de 26 barres devient la convention, sans effet sur RE-1.** Suite à décider par le porteur.

### [DÉCISION] — Fin du walk-forward ; RE-1 gelée version finale du moteur ; exploitation en fonds propres (2026-10-03)
- **Décisions du porteur, après lecture de D02.1 :** le walk-forward est définitivement abandonné ; RE-1 gelée est
  déclarée version finale du moteur ; le projet bascule sur l'exploitation en fonds propres, où l'on accepte l'usure du
  trade médian (−0,43 ATR) pour capter la queue droite. Dernier levier visé : filtrer le bruit d'usure sans amputer la
  queue droite (EXP-D03). Push de 466d767 et 8350415 autorisé (fait, origin = 8350415).

### [EXP-D03] — Profilage des extrêmes, filtre de compression (ATR) et portefeuille BTC + SOL
- **Date :** 2026-10-03
- **Étape :** D, D03. Demande du porteur (trois actions, aucune optimisation) ; formes opérationnelles fixées par l'agent
  avant le calcul et consignées ici.
- **Actifs & Période :** BTC/USD Bitstamp 2015-2025 (panne de 2015 retirée) ; SOL/USD Coinbase dès le 2021-06-17 ;
  barres de 30 min ; 2026, ETH et XRP ne sont pas lus.
- **Modèle de frais :** 5 bps aller-retour (10 bps en lecture) ; 0,25 % du capital par ATR14(t), levier ≤ 1x par
  position ; PnL et MDD à 1x publiés à côté.

#### 0. Cadrage (formes opérationnelles, fixées avant le calcul)
- **QUESTION :** les 5 % meilleurs trades de RE-1 gelée se distinguent-ils à t (volatilité, compression, position dans
  les bandes, tendance, heure) ? Le filtre ATR ≤ P60 glissant augmente-t-il le Calmar sans amputer la queue droite ?
  Combiner BTC et SOL lisse-t-il le capital ?
- **DONNÉES :** RE-1 gelée BTC 2015-2025 (2 075 trades, identiques à D02) ; RE-1 gelée SOL (769 trades, identiques à
  D01).
- **MÉTHODE :**
  - Action 1 : Alpha = ⌈5 % · n⌉ = 104 meilleurs trades par rendement net en ATR, Usure = les autres ; même découpage
    en bps contre l'artefact de définition (le rang en ATR favorise les ATR bas). Variables à la clôture de t : ATR14 et
    son rang sur 24 mois glissants, `leg_atr` et son rapport au P50 local (24 mois), %B et largeur de Bollinger (20,
    2 écarts-types de population), rang de la largeur, écart à l'EMA 200 (30 min) en ATR orienté, heure UTC ;
  - Action 2 : ATR14_bps(t) ≤ P60 glissant des barres de ]t − 730 j, t] (aucun seuil fixe tiré de l'action 1) ; lecture
    sur entrées figées (le verrou suit RE-1) et en séquentiel ; même filtre sur SOL dès le S2 2023 (hors de
    l'échantillon de l'idée) ;
  - Action 3 : capital commun (`envelope.portfolio_equity`), 0,25 %/ATR par trade sur chaque actif, entrées du
    2021-07-01 au 2025-12-31.
- **CRITÈRE DE LECTURE (sans seuil) :** distributions comparées et quintiles ; 8 métriques et écarts appariés par mois ;
  Alpha et top 1 % gardés ; PnL, MDD, Calmar, plus longue période sous le pic, mois positifs, corrélation mensuelle.
- **Code :** `context.volatility` (`bollinger`, `trailing_quantile`, `trailing_rank`), `envelope.portfolio`
  (`portfolio_equity`, une jambe = `equity_curve_sized`) ; 332 tests.

#### Résultats (`experiments/D03/rapport_D03.md`)
- **Contrôles bloquants passés :** RE-1 gelée BTC = D02 (2 075 trades) ; SOL = `run_re1` et métriques de D01 ;
  portefeuille d'une jambe = capital valorisé du dépôt.
- [OBS] **Action 1 :** classés en ATR, les 104 Alpha naissent à ATR bas (médiane 37 bps contre 48 pour l'Usure ; rang de
  largeur 0,17 contre 0,28). Classés en bps, ils naissent à ATR haut (75 bps ; rang de largeur 0,46). 53 trades
  communs sur 104. Par quintile du rang d'ATR, l'espérance vaut en bps +4,8, +7,4, +15,0, +2,6, +21,2 (bas → haut).
  %B, EMA 200 et `leg_atr` ne séparent pas les groupes. Heure UTC : 04-08 h +0,689 ATR, 16-20 h −0,205 (descriptif).
- [OBS] **Action 2 (BTC 2015-2025, 5 bps) :** filtre sur entrées figées +0,258 ATR [+0,024 ; +0,486], PnL +125 % (1x
  +205 %), MDD −22,3 % (1x −40,2 %), Calmar 0,34 contre 0,32 ; écart apparié +0,040 [−0,056 ; +0,131] et −1,3 bps,
  Calmar meilleur sur 43 % des chemins. Il garde les 21 trades du top 1 % et 92 Alpha sur 104 ; il retire 557 trades
  d'Usure (−0,091 ATR) et 12 Alpha. 2015-2019 : +0,029 contre +0,064 ; 2020-2025 : +0,456 contre +0,357. Séquentiel :
  Calmar 0,28. 10 bps : Calmar 0,09 des deux côtés. SOL : +0,243 contre +0,252, Calmar 0,57 contre 0,76.
- [OBS] **Action 3 (2021-07 → 2025, 5 bps) :** portefeuille PnL +163 % (1x par position +478 %), MDD −15,2 % (1x
  −40,1 %), Calmar 1,58 contre 1,18 (BTC seul) et 0,59 (SOL seul) ; plus longue période sous le pic 238 jours (224 pour
  BTC, 567 pour SOL) ; mois positifs 59 % ; corrélation mensuelle −0,04 ; exposition brute maximale 2,0. 10 bps : Calmar
  0,77 contre 0,59 et 0,32. SOL seul : +0,190 ATR [−0,079 ; +0,484].
- [HYP] Le « calme » des grands gagnants vient surtout de la taille de position à 0,25 % par ATR ; un filtre de
  compression trie la taille, pas la qualité, et agit comme un désendettement. La diversification est le seul levier
  mesuré qui améliore le rapport rendement / drawdown ; elle repose sur un avantage de SOL non établi à 95 %.

#### Décision
- [ ] **VALIDÉ**
- [x] **Filtre ATR non retenu (proposition) ; portefeuille BTC + SOL : gain de Calmar mesuré, avantage de SOL à
  confirmer.** RE-1 gelée inchangée. Suite à décider par le porteur.

### [DÉCISION] — Architecture finale de RE-1 ; hold-out (D04) différé après D03.1 (2026-10-03)
- **Décisions du porteur :** RE-1 (seuils gelés, R0 = 100, frontière 0,85, H = 26, verrou 26, F2b sans stop, F3 SL-B à
  0) est la version finale absolue, plus aucun paramètre ne sera modifié ; aucun filtre de condition ; exploitation en
  portefeuille multi-actifs pour diluer le drawdown. Levée des scellés annoncée (EXP-D04 : ETH et XRP, année 2026,
  portefeuille BTC + SOL + ETH), puis différée : le porteur a demandé des pistes avant d'ouvrir.
- **Pistes de l'agent :** fixer par écrit le protocole de D04 avant d'ouvrir ; viabilité réelle (coûts du lieu
  d'exécution, latence, glissement des stops, flux de prix) ; risque de perte extrême et taille ; amélioration de
  l'avantage seulement si le moteur est rouvert. Chiffres donnés : coût aller-retour qui annule l'espérance de BTC
  2015-2025, 13,8 bps (18,2 bps en 2020-2025, 7,9 en 2015-2019) ; pires trades −6,2 %, −4,7 % et −4,3 % du capital à
  0,25 %/ATR (F2b sans stop) ; IC attendu d'un actif sur neuf mois de 2026, environ ±0,8 ATR.
- **Réponse du porteur :** point 4 rejeté (le moteur n'est pas rouvert) ; priorité à la survie du capital (points 2
  et 3) : EXP-D03.1 avant D04 ; le protocole de D04 sera consigné ensuite, puis les téléchargements et la levée des
  verrous autorisés. Push de 79be76f autorisé (fait, origin = 79be76f).

### [EXP-D03.1] — Viabilité et sécurité : stop catastrophe, glissement des stops, latence (BTC, SOL)
- **Date :** 2026-10-03
- **Étape :** D, D03.1. Tests du porteur ; formes opérationnelles de l'agent consignées dans
  `experiments/D03_1/run_D03_1.py` avant le calcul. Le moteur n'est pas rouvert : chaque test est une lecture.
- **Actifs & Période :** BTC/USD Bitstamp, entrées 2015-2025 ; SOL/USD Coinbase 2021-2025 ; 5 bps (10 bps en lecture),
  0,25 %/ATR, levier ≤ 1x.
- **MÉTHODE :**
  - stop catastrophe : open[t + 1] − sens · 4 · ATR14(t), greffé sur F2b et F3, le premier stop touché sort ; mêmes
    entrées que RE-1 ;
  - glissement : sorties sur stop de F3 exécutées 0,5 · ATR14(t) plus loin ;
  - latence : entrée à open[t + 2], même horizon, même stop, même verrou relatif ; un stop déjà franchi fait sortir
    aussitôt, brut nul ;
  - lecture supplémentaire : les trois ensemble.
- **Code :** `envelope.stress` (`nearest_levels`, `slip_stops`, `delayed_trades`) ; 337 tests.

#### Résultats (`experiments/D03_1/rapport_D03_1.md`)
- [OBS] **Stop catastrophe :** il ne touche que des F2b (284 sur BTC, 98 sur SOL) ; la pire perte d'un trade passe de
  −6,2 % à −1,05 % du capital (BTC) et de −3,3 % à −1,05 % (SOL).
  - BTC 2015-2025 : +0,180 ATR contre +0,218, écart −0,037 [−0,118 ; +0,040] ; MDD −21,4 % contre −28,4 % ; Calmar 0,36
    contre 0,32 ;
  - BTC 2020-2025 : −0,121 ATR [−0,237 ; −0,006], rendement −5,2 points par an, Calmar 0,66 contre 1,12 ;
  - BTC 2015-2019 : +0,055 ATR, Calmar meilleur sur 91 % des chemins ;
  - SOL : −0,054 ATR, −9,9 bps [−20,4 ; −1,2], Calmar 0,34 contre 0,58 ;
  - 89 % des trades coupés auraient fini négatifs ; 1 trade du top 1 % et 7 du top 5 % coupés sur BTC.
- [OBS] **Glissement de 0,5 ATR :** 23 % des trades sortent sur stop ; −0,115 ATR par trade (BTC), −0,121 (SOL) ; Calmar
  0,32 → 0,10 (BTC). Chaque 0,1 ATR de glissement coûte environ 0,023 ATR par trade.
- [OBS] **Latence d'une barre :** +0,014 ATR [−0,025 ; +0,056] (BTC), +0,002 (SOL).
- [OBS] **Les trois ensemble :** −0,221 ATR [−0,313 ; −0,137] (BTC), espérance −0,003.
- [HYP] La latence n'est pas un risque ; l'exécution des stops l'est. Le stop catastrophe est une assurance contre la
  ruine, dont l'historique ne contient pas le scénario couvert ; son coût est faible sur 2015-2025 entier, élevé sur
  2020-2025 et SOL.

#### Décision
- [ ] **VALIDÉ**
- [x] **À trancher par le porteur :** greffe du stop catastrophe (le « coût marginal » est sa règle) ; choix du lieu et
  du type d'ordre pour les stops. RE-1 inchangée à ce stade.

### [DÉCISION] — Stop catastrophe greffé : RE-1 version finale ; GO de D04 (2026-10-03)
- **Décision du porteur, après lecture de D03.1 :** le stop catastrophe de 4 ATR est greffé définitivement à RE-1 et
  fait partie de la version finale. Motif du porteur : en production ou en compte financé (limite de perte
  journalière de 4 %), un trade F2b sans stop pendant un krach est éliminatoire, quelle que soit la taille. La latence
  nulle mesurée en D03.1 ouvre la voie aux ordres à cours limité pour les entrées.
- **Version finale (`strategy.final`) :** seuils BTC gelés, R0 = 100, frontière 0,85, H = 26, verrou 26, F2b sans
  SL-B, F3 SL-B à 0, stop catastrophe open[t + 1] − sens · 4 · ATR14(t) sur tous les trades (le plus proche des deux pour
  F3). Contrôle : elle redonne trade par trade la série « Stop catastrophe 4 ATR » de D03.1 (BTC 2015-2025 : 2 075
  trades, +0,180 ATR ; SOL : 769 trades, +0,135 ATR).
- **Réserve levée par un interrupteur explicite (`reserve.levee`) :** scellée par défaut dans tout le dépôt ; levée
  seulement dans un bloc du script de D04 (lecture de `strategy.load_asset` au-delà de 2025, contrôle
  `check_no_holdout`, téléchargeurs Bitstamp, Coinbase et HistData). Alpaca, FRED et Saxo restent scellés.
- **Téléchargements autorisés par le porteur** après annonce des fichiers, sources et tailles : ETH/USD et XRP/USD
  (Bitstamp, tout l'historique), 2026 de BTC/USD (Bitstamp), SOL/USD et AVAX/USD (Coinbase), XAU/USD (HistData).
  Push de bb80d6d autorisé (fait, origin = bb80d6d). Pré-enregistrement : commit local, sans push.

### [EXP-D04] — Épreuve de la réserve (Phase 7) : ETH et XRP, année 2026 — protocole pré-enregistré
- **Date :** 2026-10-03
- **Étape :** D, D04 (Phase 7). Protocole du porteur ; formes opérationnelles consignées dans
  `experiments/D04/run_D04.py` et ici, puis commit local, avant tout téléchargement. Aucune modification après lecture.
- **Actifs & Période :** test A, ETH/USD et XRP/USD Bitstamp, de la première barre cotée au 2026-10-01 00:00 UTC
  exclu ; test B, signaux du 2026-01-01 au 2026-10-01 exclu pour BTC/USD (Bitstamp), SOL/USD et AVAX/USD (Coinbase),
  CFD or XAU/USD (HistData ; fin au 2026-09-01 si septembre n'est pas publié). Barres de 30 min telles que servies.
- **Modèle de frais :** 5 bps (or 4 bps) ; 10 bps (or 6 bps) en lecture ; 0,25 % du capital par ATR14(t), levier ≤ 1x ;
  PnL et MDD à 1x à côté.

#### 0. Cadrage
- **QUESTION :** la version finale de RE-1 garde-t-elle une espérance nette positive sur deux actifs jamais utilisés
  pour la construire (ETH, XRP), et comment traverse-t-elle 2026 sur les quatre actifs de développement ?
- **DONNÉES :** séries ci-dessus ; pour le test B, atlas calculé sur l'historique continu (filtre de Kalman depuis la
  première barre ; panne de janvier 2015 retirée pour BTC, comme en D02-D03.1).
- **MÉTHODE :** version finale seule (aucune autre variante calculée sur la réserve) ; test A, tous les signaux hors
  warm-up ; test B, candidats restreints à la période (convention de D03.1, verrou neuf au 1er janvier).
- **CRITÈRE DE LECTURE :** 8 métriques par série ; espérance par année d'entrée pour ETH et XRP (ATR, bps, IC 95 % par
  grappes mensuelles) ; survie : pire trade et pire journée UTC en % du capital (valorisé aux clôtures de 30 min et aux
  extrêmes défavorables des barres détenues), à 0,25 %/ATR et à 1x, MDD, PnL.
- **Règle de décision du porteur (verbatim) :** « Si la stratégie dégage une espérance nette strictement positive
  (E[ATR]_net > 0) sur ETH et XRP d'une part, et qu'elle a survécu sans crash à l'année 2026 d'autre part, la stratégie
  est validée pour la production. » Lecture fixée avant les données : E[ATR]_net = moyenne par trade du rendement net
  de 5 bps en ATR14(t), estimation ponctuelle, pour ETH et pour XRP séparément, IC en lecture ; « survécu sans crash » :
  jugé par le porteur sur les mesures, sans seuil fixé (réponse du porteur).
- **Contrôles bloquants :** version finale = D03.1 (fait, réserve scellée) ; empreintes des nouvelles séries ; barres
  antérieures à 2026 des séries prolongées identiques aux séries scellées ; mêmes candidats et mêmes trades avant 2026.
- **Réserve non vierge (passation §2.1) :** ETH et XRP vus par d'anciens projets (Kalman, « Labos 2-3 ») ; BTC 2026
  aussi. Aucun paramètre de RE-1 n'a été choisi sur ces données.
- **Code :** `reserve` (interrupteur), `strategy.final` (version finale), `envelope.daily` (pertes journalières),
  téléchargeurs (année partielle Bitstamp, mois de 2026 Coinbase, archives mensuelles HistData) ; 349 tests.
- **Incident d'acquisition (avant toute lecture, consigné) :** le premier téléchargement s'est arrêté sur une page vide
  (ETH/USD, départ au 2014-01-01). Sondes : l'API Bitstamp sert les barres de [start, start + 999 pas], pas les 1 000
  premières barres ≥ start ; premières cotations ETH/USD le 2017-08-16 (16:30 UTC en 30 min), XRP/USD le 2016-12-16 ;
  rien avant. Correction du téléchargeur : une page vide est une fenêtre vide, la suivante est demandée (sans perte,
  test sur une API simulée à fenêtre) ; commit séparé avant la reprise.
- **Incidents de données de l'or (avant tout calcul sur 2026, consignés) :** l'archive HistData de juin 2026 sert 26
  minutes deux fois avec des valeurs différentes (2026-06-28 22:08 → 2026-06-30 16:02 UTC, écart jusqu'à 16 $ pour
  ≈ 4 080 $) ; elles sont fusionnées (ouverture de la première ligne, plus haut et plus bas des deux, clôture de la
  dernière ; `histdata.merge_conflicting_minutes`, `conflits="fusion"`), rien n'est jeté. L'archive de septembre est
  partielle (dernière minute le 2026-09-24) : barres prises telles que servies, aucun signal de l'or après le 24.
- **Téléchargements faits (2026-10-03) :** ETH/USD 159 951 barres (2017-08-16 16:30 → 2026-09-30 23:30), XRP/USD
  171 621 (2016-12-16 13:30 → 2026-09-30), BTC/USD 241 008 (2013 → 2026-09-30), SOL/USD 92 669, AVAX/USD 87 622, or
  207 353 (→ 2026-09-24) ; anciennes séries inchangées.
- **Incident de contrôle (avant tout résultat sur 2026, consigné) :** le contrôle (4) s'est arrêté sur l'or : un signal
  du 2025-12-31 17:00 UTC est candidat sur la série prolongée, absent de la série scellée. Cause : convention de
  l'atlas (`anatomy.dev_universe`), un signal n'est gardé que si sa sortie native (ouverture après le premier signal
  opposé) est dans l'échantillon ; sur la série scellée, celle de ce signal tombait en 2026. Aucune variable n'en
  dépend ; même convention en D01-D03.1 (elle écarte aussi les derniers signaux de 2026 sans sortie native observée,
  comptés dans les annexes). Contrôle reformulé : candidats scellés = candidats prolongés hors signaux ainsi
  censurés, chacun vérifié ; trades identiques avant le premier d'entre eux. Bug d'audit corrigé (plus long trou).

#### Résultats (`experiments/D04/rapport_D04.md`)
- **Contrôles bloquants passés :** version finale = D03.1 (BTC 2 075 trades, +0,180207 ATR ; SOL 769, +0,135282) ; séries
  prolongées identiques aux scellées avant 2026 (BTC, SOL, AVAX, or ; un signal de l'or censuré par la convention de
  fin d'échantillon, vérifié) ; BTC 2026 identique à l'ancien fichier Bitstamp (12 368 barres).
- [OBS] **Test A (5 bps) :**
  - ETH (2017-08 → 2026-09) : +0,183 ATR [−0,010 ; +0,385], +10,4 bps ; PnL +82 % (1x +155 %) ; MDD −39,1 % (1x −72,1 %) ;
    1 525 trades (14,0/mois) ; PF 1,11 ; WR 42,0 % ; frais 33 % du brut ; Calmar 0,17 ;
  - XRP (2016-12 → 2026-09) : +0,263 ATR [−0,014 ; +0,640], +16,0 bps [+0,1 ; +32,9] ; PnL +148 % (1x +354 %) ; MDD
    −20,9 % (1x −61,7 %) ; 1 689 trades (14,5/mois) ; PF 1,15 ; WR 43,3 % ; frais 24 % ; Calmar 0,47 ;
  - 10 bps : ETH +0,088, XRP +0,181. Par année : ETH positif 7 ans sur 10 (négatif en 2022, 2023, 2025), XRP 8 sur 10.
- [OBS] **Test B (2026, janvier-septembre ; or jusqu'au 24 septembre) :**
  - BTC +0,705 ATR [+0,045 ; +1,469], PnL +29 %, MDD −6,9 % ; SOL +0,410 [−0,081 ; +0,997], +15 %, −6,0 % ;
  - AVAX +1,059 [+0,328 ; +1,784], +32 %, −4,7 % ; or (4 bps) +0,987 [+0,449 ; +1,479], +21 %, −3,1 %.
- [OBS] **Survie (0,25 %/ATR) :** pire trade −1,04 % (2026), −1,05 % (ETH), −1,21 % (XRP, gap de janvier 2017) ; pire
  journée UTC en 2026 de −1,1 % à −1,8 % (−2,0 % aux extrêmes) ; ETH −3,03 % le 2020-08-02 (gain latent rendu dans un
  krach éclair ; −0,50 % rapporté au solde réalisé), XRP −2,57 %.
- [OBS] **Queue droite (lecture hors protocole) :** sans le 1 % meilleur, ETH −0,060 et XRP −0,058 ATR ; un trade de XRP
  (2023-07-13, jour de la décision SEC contre Ripple) fait 56 % de la somme en ATR (+61,9 % du capital) ; sans lui, XRP
  +0,117 ATR.
- [HYP] La réserve confirme la nature de RE-1 (queue droite, trade médian perdant) avec une marge mince ; 2026 est la
  période la plus favorable mesurée, à ne pas extrapoler ; risques de production : gains latents rendus dans la perte
  journalière, stops remplis dans les krachs éclairs, pertes simultanées d'un portefeuille (non mesurées).

#### Décision
- [ ] **VALIDÉ**
- [x] **Règle du porteur, lecture littérale : condition 1 remplie (ETH +0,183, XRP +0,263 ATR) ; condition 2 (survie à
  2026) à juger par le porteur sur les mesures.** Décision de mise en production au porteur. Commits locaux, non poussés.

### [EXP-D04.1] — Pire journée du portefeuille complet (six actifs, RE-1 version finale)
- **Date :** 2026-10-04
- **Étape :** D, D04.1. Demande du porteur (« Mesure la pire journée du portefeuille complet ») après D04 ; push des
  commits de D04 autorisé et fait (origin = c46a7ca).
- **Actifs & Période :** BTC, SOL, AVAX, or, ETH, XRP (séries de D04) ; fenêtre commune, entrées du 2021-10-01 au
  2026-10-01 exclu ; fenêtre longue dès le 2017-08-16 (SOL et AVAX à leur cotation).
- **Modèle de frais :** 5 bps (or 4 bps) ; 0,25 % du capital valorisé par ATR14(t) et par trade, ≤ 1x par position ;
  1x par position en lecture.

#### 0. Cadrage (fixé avant le calcul, `experiments/D04_1/run_D04_1.py`)
- **QUESTION :** pire journée UTC du capital commun quand la version finale tourne sur les six actifs ; journées proches
  de la limite de 4 % citée par le porteur.
- **MÉTHODE :** `envelope.portfolio_paths` (règles de `portfolio_equity`, un état après les clôtures et un après les
  sorties et entrées de chaque instant) ; `envelope.daily_from_paths` ; référence = capital valorisé à 00:00, ou solde
  réalisé à 00:00 ; borne pessimiste = toutes les positions à l'extrême défavorable de la même barre.
- **CRITÈRE DE LECTURE (sans seuil) :** pire journée et contributions ; quantiles ; journées sous −1 à −4 % ; actifs
  seuls ; 8 métriques ; exposition brute.
- **Code :** `portfolio_paths`, `daily_from_paths` ; 354 tests.

#### Résultats (`experiments/D04_1/rapport_D04_1.md`)
- **Contrôles bloquants passés :** trades d'ETH et de XRP identiques à D04 ; une jambe seule redonne ses pertes
  journalières.
- [OBS] **Fenêtre commune :** pire journée −5,20 % (2022-11-04) sur le capital valorisé, −4,16 % sur le solde réalisé
  (2022-02-06), −5,90 % en borne pessimiste ; 5 journées sous −4 % (3 sur le solde), 25 sous −3 %, 153 sous −2 %, sur
  1 775 ; 2026 : −5,14 % (26 janvier, gain latent rendu), −3,21 % sur le solde. Actif seul, même fenêtre : au pire
  −2,57 % (XRP).
- [OBS] **Mécanisme :** quatre stops catastrophe touchés ensemble sur des cryptos corrélées (2022-11-04 : ventes F2b
  de BTC, SOL, ETH, XRP ; 2025-11-06 : achats F2b de BTC, SOL, AVAX, ETH), environ −1 % chacun.
- [OBS] **8 métriques (fenêtre commune) :** PnL +584 % (1x par position +1 439 %), PF 1,13, WR 42,3 %, +0,198 ATR,
  +9,9 bps, MDD −37,4 % (1x −81,5 %), 4 744 trades (79/mois), 26 barres, frais 33 % du brut, Calmar 1,25 ; exposition
  brute jusqu'à 5,2x (P99 3,1) ; capital ×3,1 sur les neuf mois de 2026 ; MDD du 2023-07-13 au 2024-01-27.
- [OBS] **Fenêtre longue (2017-08 → 2026-09) :** aucune journée pire (−5,20 %), 5 journées sous −4 %.
- [HYP] À 0,25 %/ATR par trade sur six actifs, une limite journalière de 4 % sur le capital valorisé est franchie
  environ une fois par an ; la perte du jour est à peu près proportionnelle à la taille par trade.

#### Décision
- [ ] **VALIDÉ**
- [x] **Mesure faite ; taille par trade et règles du compte à arbitrer par le porteur.** Commit local, non poussé.

### [EXP-D04.2] — Portefeuille complet en OFAT : composition (un actif retiré à la fois) et levier (risque par trade)
- **Date :** 2026-10-04
- **Étape :** D, D04.2. Demande du porteur (« 1) Test sans XRP dans le portefeuille. 2) Test également plusieurs
  configurations de portefeuille différent. 3) Test aussi, en OFAT différents leverage. ») ; plan validé par le
  porteur : levier = risque par trade, compositions = retrait d'un actif à la fois.
- **Actifs & Période :** ceux de D04.1, fenêtre commune 2021-10 → 2026-09 ; 5 bps (or 4 bps).

#### 0. Cadrage (fixé avant le calcul, `experiments/D04_2/run_D04_2.py`)
- **QUESTION :** effet sur la pire journée, le MDD et le PnL (1) du retrait de chaque actif, XRP compris, (2) du risque
  par trade.
- **MÉTHODE :** référence = six actifs, 0,25 %/ATR, ≤ 1x (D04.1) ; axe composition au risque de référence ; axe levier
  à 0,05, 0,10, 0,15, 0,20 et 0,30 %/ATR sur les six actifs, plafond inchangé.
- **CRITÈRE DE LECTURE (sans seuil) :** mesures de D04.1. Biais signalé : la réserve a été lue ; retirer un actif à la
  fois évite de choisir une composition après lecture.

#### Résultats (`experiments/D04_2/rapport_D04_2.md`)
- **Contrôle passé :** la référence redonne D04.1.
- [OBS] **Composition (0,25 %/ATR) :** sans XRP −5,03 % (−4,08 % sur le solde), 2 journées sous −4 %, MDD −35,6 %, PnL
  +274 %, Calmar 0,85 (référence −5,20 %, 5, −37,4 %, +584 %, 1,25) ; au mieux −4,06 % (sans ETH) et −4,07 % (sans
  SOL) ; sans or −5,71 %, MDD −41,5 % : l'or est le seul diversifiant.
- [OBS] **Levier (six actifs) :** pire journée −1,10 / −2,16 / −3,19 / −4,18 / −5,20 / −6,32 % pour 0,05 / 0,10 / 0,15 /
  0,20 / 0,25 / 0,30 %/ATR (≈ 21 × le risque) ; aucune journée sous −4 % jusqu'à 0,15 % ; MDD −10,7 à −43,1 % ; Calmar
  0,89 à 1,28 ; exposition brute P99 de 0,85x à 3,41x.
- [HYP] Pour une limite journalière, la taille commande, pas la composition ; « sans ETH » (Calmar 1,69) serait une
  sélection après lecture ; si le compte impose une perte totale maximale, le MDD contraint davantage (−26,3 % à
  0,15 %/ATR, −10,7 % à 0,05 %).

#### Décision
- [ ] **VALIDÉ**
- [x] **Mesures faites ; composition et taille à arbitrer par le porteur.** Commit local, non poussé.

### [DÉCISION] — Séparation du projet ; branche « Fonds propres » close par son livre blanc (2026-10-05)
- **Décisions du porteur, après lecture de D04.2 :**
  - l'univers des six actifs est gardé entier : retirer ETH serait une sélection après lecture de la réserve ; l'or est
    le seul diversifiant mesuré ;
  - le projet est séparé en deux. La branche « Fonds propres » est close ; un nouveau cycle de recherche, consacré aux
    contraintes des Prop Firms, suivra.
- **Livrable :** `RE1_FONDS_PROPRES_LIVRE_BLANC.md` à la racine, cahier des charges du bot :
  - spécification de la version finale (`strategy.final`) et critère de conformité (rejeu trade par trade) ;
  - univers des six actifs, rôle de l'or ;
  - matrice de taille (D04.2) ;
  - avertissements d'exécution et risques hors modèle.
- **Sources :** aucun calcul nouveau ; chiffres des rapports D02.1, D03.1, D04, D04.1 et D04.2. Déductions
  arithmétiques signalées comme telles : rendement annualisé, multiples de r, coût du glissement selon la part des
  sorties sur stop, ≈ +20 % par an hors 2026.
- **Relecture des énoncés du porteur :**
  - « pire journée ≈ 21 × risque » : confirmé (20,8 à 22,0 fois) ;
  - « l'or, seul vrai parachute lors des krachs » : l'or est le seul actif dont le retrait aggrave la pire journée et le
    MDD. Le 2022-11-04, il gagne +0,51 % au plus bas, un jour de hausse qui stoppe quatre ventes crypto. Sa
    corrélation aux cryptos n'est pas mesurée ;
  - « le trade médian perd, le top 1 % fait la rentabilité » : confirmé sur BTC (RE-1 sans stop catastrophe), ETH et
    XRP ;
  - « la latence ne coûte rien » : mesuré sur l'entrée (D03.1). Le remplissage d'un ordre passif et sa sélection adverse
    ne sont pas mesurés ;
  - « glissement mortel des stops F3 » : 0,5 ATR sur les stops de F3 divise par deux l'espérance de BTC. Appliqué à tous
    les stops de la version finale, un glissement d'environ 0,5 ATR l'annule.
- **Push :** aucun ; commit local.

### [DÉCISION] — Trois directions du projet ; sessions « Fonds propres » (papier) et « Sniper » (2026-10-05)
- **Directions du porteur :**
  1. **Fonds propres** (ce dépôt) : maximiser la rentabilité à risque mesuré. RE-1 VF est gelée (livre blanc) ; étape
     suivante : paper trading et workstation de suivi et d'exécution, dans une session dédiée.
  2. **Prop Firm** (ce dépôt) : valider les challenges en générant un peu de rendement ; cycle de recherche mené avec le
     porteur.
  3. **Sniper manuel** (dépôt séparé, privé) : signaux rares et forts pour des trades manuels, « chasseur de cygnes
     noirs » ; la stratégie peut y être entièrement repensée.
- **Direction 1, choix du porteur :**
  - simulateur interne sur flux réels, puis compte démo ou testnet ;
  - workstation sur NautilusTrader, sous porte de parité (les trades de la version finale reproduits un par un) ; en
    cas d'échec, moteur du dépôt et tableau de bord autre que Streamlit ;
  - plateforme crypto de production à comparer en session ;
  - PC Windows pendant le papier, serveur ensuite ; alertes Telegram ;
  - risque par trade choisi par le porteur sur la matrice du livre blanc (0,25 ou 0,30 %/ATR envisagés) ;
  - ajout d'actifs possible par un test de portabilité pré-enregistré.
- **Direction 3, choix du porteur :**
  - aucune automatisation des ordres : chaque signal donne ses niveaux (entrée à cours limité, stop), que le porteur
    pose lui-même ;
  - frais non pris en compte (stratégie manuelle) ; unité de temps libre (1 h ou autre) ;
  - pool à décider ensemble à partir des moteurs de performance, cryptos d'abord (liquides et illiquides) ;
  - toutes méthodes autorisées (ML, Optuna, autres), dans cet ordre : exploration libre, cadrage de la méthode à plus
    forte valeur ajoutée, méthode optimale sous protocole ;
  - recherches complexes (papiers SSRN récents) : prompt rédigé par l'agent, transmis par le porteur à Perplexity ;
  - alertes Telegram.
- **Rappels de l'agent :**
  - « RE-1 détecte les cygnes noirs » reste une hypothèse : D03 n'a trouvé aucune variable connue à t qui sépare les
    meilleurs trades (Q16, I-M20) ; le chantier Sniper commence par la tester ;
  - ETH, XRP et 2026 sont lus : la réserve du Sniper devra venir de données jamais lues (nouveaux actifs, période à
    venir) ;
  - deux sessions travaillent sur ce dépôt : la direction 1 avance dans un worktree, sur sa branche, et ne modifie pas
    les documents partagés de `main`.
- **Prompts d'initialisation :** `prompts/init_d1_fonds_propres_papier.md` et `prompts/init_d3_sniper.md`.
- **Push :** aucun ; commit local.

### [DÉCISION] — Cycle Prop Firm (D05) : critique du plan du porteur, recadrage (2026-10-05)
- **Plan du porteur (prompt « EXP-D05 ») :**
  - D05.1, univers TradFi : US100 ou GER40, GBPJPY, WTI ; glissement du stop catastrophe sur les gaps ;
  - D05.2, boucliers : coupe-circuit intrabarre à −3,5 % depuis minuit, plafond d'exposition ;
  - D05.3, gestion active : break-even à +1,5 ATR, sortie de 30 % à +2 ATR ;
  - D05.4 : simulateur de challenge ;
  - D05.5 : Monte Carlo, 10 000 chemins.
- **Critique de l'agent (sans calcul, sur rapports existants) :**
  - TradFi déjà lue en EXP-D01.7 (RE-1 avant sa version finale), sans IC > 0 à 4 bps : GER40 −0,005, US100 −0,097,
    GBPJPY −0,303 ATR. WTI retiré par le porteur le 2026-09-30 (HistData arrêté au 2023-12-01). Choisir parmi ces actifs
    serait une sélection après lecture.
  - D05.3 déjà mesuré (EXP-C03) : un break-even déclenché à 1,5 ATR ou moins ampute la queue droite. La sortie
    partielle équivaut à 30 % de take-profit à +2 ATR, qui reste sous RE-1 même en borne optimiste.
  - La contrainte qui lie est la perte totale statique (MDD −10,7 % dès 0,05 %/ATR), pas la perte du jour (≈ 21 × r).
  - Le coupe-circuit à −3,5 % ne jouerait pas sous r ≈ 0,15. Plafond d'exposition et marge risquent de toucher d'abord
    les grands gagnants, nés à ATR bas avec une grosse taille.
  - Un Monte Carlo par trades i.i.d. casse les pires journées, où les pertes tombent ensemble.
  - Le simulateur doit venir d'abord : il juge chaque levier contre une simple baisse de r.
- **Décisions du porteur :**
  - **Étalon : compte FTMO Swing.**
    - Commission crypto nulle, écarts serrés, swap faible.
    - Levier 1:2 sur les cryptos et 1:30 sur l'or ; positions du week-end permises.
    - Perte du jour mesurée sur l'équité, latents inclus, remise à zéro à 00:00 CET/CEST.
    - Objectifs de 9 % puis 5 % ; perte totale de 10 %, statique ; au moins 4 jours ; aucune règle de régularité.
  - **Pas de prompt Perplexity.**
  - **D05.3 annulé** ; le moteur reste strictement gelé.
  - **Marge :** une entrée qui dépasserait la marge du compte est réduite à la marge restante.
  - **D05.1 recadré pour plus tard (« ADN cinématique ») :**
    - profil des actifs où RE-1 gagne : leptokurticité, ratio tendance/range, régimes de volatilité ;
    - puis test TradFi sur des données cTrader 2023-2026, avec parmi les candidats l'action Société Générale (GLE).
  - **GO de l'étape 1 :** simulateur de challenge (EXP-D05.4), sur le cadrage de l'agent.
- **Relecture des énoncés du porteur :**
  - « tests de D01.7 obsolètes (ancienne version de RE-1) » : vrai pour la version, qui n'avait pas le stop
    catastrophe. Le coût exprimé en ATR ne dépend pas de la version : de 0,24 à 0,42 ATR pour un ATR de 11 à 34 bps.
  - « actifs où RE-1 gagne : BTC, SOL, XAU » : l'or est ≈ 0 avant 2026 (D01, D04), alors qu'ETH et XRP gagnent (D04).
  - Objectif de P1 à 9 % : à ma connaissance, FTMO demande 10 % ; le porteur garde 9 % (paramètre du simulateur).
- **Push :** aucun ; commit local.

### [EXP-D05.4] — Simulateur de challenge de prop firm : RE-1 version finale, étalon FTMO Swing
- **Date :** 2026-10-05
- **Étape :** D05, étape 1. GO du porteur ; cadrage de l'agent validé.
- **Actifs & Période :** trades de D04.1 (six actifs, entrées du 2021-10-01 au 2026-10-01 exclu ; réserve levée par
  `reserve.levee`) ; 5 bps (or 4 bps).

#### 0. Cadrage (fixé avant le calcul, `experiments/D05_4/run_D05_4.py`)
- **QUESTION :** avec RE-1 VF telle quelle, selon r :
  - probabilité de réussir P1 (+9 %) puis P2 (+5 %) sans franchir −5 % sur une journée ni −10 % au total ;
  - délai ;
  - règle qui fait échouer.
- **MÉTHODE :** module `src/propfirm/` (12 tests).
  - Un compte à plat de 100 000 $ démarre à chaque minuit CET/CEST : 1 826 départs.
  - Les départs avancent ensemble sur les événements de `portfolio_paths`.
  - Marge 1:2 (cryptos) et 1:30 (or), plafonnée selon la règle du porteur.
  - Pertes jugées sur la borne pessimiste ; perte du jour depuis le solde de minuit (FTMO).
  - Un facteur : r ∈ {0,05 ; 0,10 ; 0,15 ; 0,20 ; 0,25} %/ATR.
  - En regard : sans plafond de marge, référence max(solde, équité), capital valorisé, données coupées au 2026-01-01.
- **CRITÈRE DE LECTURE (sans seuil) :** parts de réussite, d'échec et de challenges en cours ; délais ; par r et par
  année ; IC par blocs de mois de départ.
- **Conventions :**
  - réussite = capital valorisé − frais de sortie ≥ objectif, avec au moins 4 jours ; tout est alors clôturé ;
  - P2 démarre au minuit suivant ;
  - correction de la borne pessimiste : la perte du stop est cumulée aux extrêmes des autres positions.

#### Résultats (`experiments/D05_4/rapport_D05_4.md`)
- **Contrôles passés :**
  - ETH et XRP identiques à D04 ;
  - pour chaque r, sans plafond ni correction, le départ du 2021-10-01 redonne `portfolio_paths` (63 148 états) et
    D04.2 (PnL, MDD) ;
  - vérification indépendante sur le chemin global : 0,0 / 9,5 / 22,9 / 29,6 / 33,4 % d'échecs par la perte totale en
    P1, contre 0,0 / 9,5 / 23,1 / 29,6 / 33,7 % pour le moteur.
- [OBS] **Réussite P1 + P2 de 0,05 à 0,25 %/ATR :**

  | r (%/ATR) | 0,05 | 0,10 | 0,15 | 0,20 | 0,25 |
  |---|---|---|---|---|---|
  | Réussite P1 + P2 | 88,2 % | 78,5 % | 60,4 % | 58,8 % | 51,0 % |
  | IC à 95 % | [79,7 ; 95,0] | [69,7 ; 86,7] | [49,5 ; 71,4] | [47,9 ; 69,3] | [40,2 ; 61,2] |
  | Délai médian | 571 j | 173 j | 100 j | 68 j | 41 j |

  Les échecs viennent presque tous de la perte totale statique (46,8 % des départs à 0,25). La perte du jour ne fait
  échouer aucun départ jusqu'à 0,20, et 0,7 % à 0,25.
- [OBS] **À horizon fixé, sur les mêmes 1 462 départs, le meilleur r change :**
  - en 90 jours, au mieux 38,9 % (r = 0,25) ;
  - en 180 jours, 52,0 % (r = 0,20) ;
  - en un an, 67,6 % (r = 0,10).
- [OBS] **La marge 1:2 pèse peu.**
  - Jusqu'à 0,15, au plus 1,6 % des trades sont réduits.
  - À 0,25, 7,5 % des trades sont réduits et 1,0 % sautés, dont 6 et 2 des 48 meilleurs. Le PnL du 2021-10 au
    2026-09 passe de +584 % à +538 %.
  - Effet sur la réussite : de −0,3 à +4,5 points.
- [OBS] **Fragilité :**
  - sans 2026, la réussite vaut 43,3 / 61,7 / 53,6 / 52,3 / 44,2 % ;
  - à 0,10, elle va de 55,9 % (départs de 2023) à 100 % (2021, 2024) selon l'année de départ ;
  - à 0,05, il n'y a aucun échec, mais la pire baisse depuis un minuit atteint −9,55 % (départ du 2023-07-27).
- [OBS] **Correction de la borne pessimiste :**
  - 161 à 164 journées UTC changent sur 1 775 (au plus −1,08 point à 0,25, le 2023-03-03) ;
  - les pires journées de D04.1 et D04.2 sont inchangées.
- [HYP] **L'issue dépend surtout du moment du départ** par rapport aux longues phases plates ou baissières de RE-1.
  Un levier n'a de valeur que s'il déplace la frontière probabilité / délai au-delà d'une simple baisse de r. Le
  coupe-circuit journalier est sans objet : la perte du jour ne lie pas.

#### Décision
- [ ] **VALIDÉ**
- [x] **Mesures faites ; choix de r (règle 70/30) et suite du cycle à décider par le porteur.** Commit local, non
  poussé.

### [DÉCISION] — Cible du porteur, règles du compte financé, variantes de taille ; GO de D05.5 et D05.6 (2026-10-05)
- **Règle 70/30, précisée par le porteur :** la variable visée est le temps. Délai médian de P1 + P2 entre 3 et 6 mois
  (90 à 180 jours), avec une réussite d'au moins 60 à 65 %.
- **Compte financé (règles FTMO standard confirmées) :** 80 % des gains pour le porteur, retrait tous les 14 jours,
  540 € remboursés au premier retrait, perte totale de 10 % du solde initial, statique. GO pour la valeur d'une
  tentative (D05.5).
- **D05.6, trois variantes de taille, une à la fois, comparées à un r fixe :**
  - A, frein : 0,20 %/ATR ; 0,10 à −5 % ; de nouveau 0,20 au-dessus de −2 % ;
  - B, sprint : 0,10 ; 0,20 à +3 % ; de nouveau 0,10 sous +1 % ;
  - C, coussin : taille proportionnelle à la marge restante avant le plancher de −10 %.
- **Ensuite, après lecture de D05.5 et D05.6 :**
  - D05.7 : tirage par blocs de semaines, sans 2026 ;
  - D05.1 : profil des actifs, puis test sur un export cTrader de l'action Société Générale (GLE), fourni par le
    porteur.
- **Push :** aucun ; commit local.

### [EXP-D05.5] — Phase financée : valeur d'une tentative de challenge FTMO
- **Date :** 2026-10-05
- **Étape :** D05, étape 2. GO du porteur.
- **Actifs & Période :** ceux de D05.4 ; 5 bps (or 4 bps).

#### 0. Cadrage (fixé avant le calcul, `experiments/D05_5/run_D05_5.py`)
- **QUESTION :** que vaut une tentative de challenge une fois le compte financé, selon r ?
- **MÉTHODE :**
  - Challenge de D05.4.
  - Le compte financé démarre au minuit qui suit la réussite de P2, avec les mêmes règles de perte et de marge.
  - Tous les 14 jours, il retire min(solde, équité) − 1 ; les positions restent ouvertes. Il s'arrête à sa première
    rupture.
  - Valeur = −540 € + (540 € + 80 % des retraits) s'il y a au moins un retrait.
  - Même r dans les deux phases ; horizons de 12 et 24 mois, et sans 2026.
- **CRITÈRE DE LECTURE (sans seuil) :** valeur moyenne avec IC par blocs de mois ; part des tentatives avec au moins un
  retrait ; vie et retraits des comptes financés.

#### Résultats (`experiments/D05_5/rapport_D05_5.md`)
- **Contrôle passé :** le challenge redonne D05.4 pour chaque r.
- [OBS] **Valeur d'une tentative à 12 mois** (1 462 départs) :

  | r (%/ATR) | 0,05 | 0,10 | 0,15 | 0,20 | 0,25 |
  |---|---|---|---|---|---|
  | Valeur à 12 mois | −273 € | +3 336 € | +6 902 € | **+9 218 €** | +7 504 € |
  | IC à 95 % | | | | [+5 833 ; +12 821] | |

  - À 24 mois, le maximum est +10 906 € ; sans 2026, +11 100 € ; tous deux à r = 0,20.
  - De 0,10 à 0,20, environ une tentative sur deux touche au moins un retrait.
- [OBS] **Comptes financés suivis 12 mois :**
  - de 0,10 à 0,25, 71 à 99 % sont perdus dans l'année, après avoir retiré 16 à 22 % du compte ;
  - à 0,05, aucun n'est jamais perdu, et ils retirent 10,6 % par an.
- [HYP] **Le gain du porteur est convexe :** sa perte est plafonnée à 540 €, et ses gains retirés ne reviennent jamais
  au compte. La valeur favorise donc 0,20, hors de la cible du porteur (58,8 % en 68 jours).

#### Décision
- [ ] **VALIDÉ**
- [x] **Mesures faites ; à arbitrer par le porteur avec D05.6.** Commit local, non poussé.

### [EXP-D05.6] — Taille selon l'état du compte : variantes A, B et C contre un risque fixe
- **Date :** 2026-10-05
- **Étape :** D05, étape 3. GO du porteur.
- **Actifs & Période :** ceux de D05.4 ; 5 bps (or 4 bps).

#### 0. Cadrage (fixé avant le calcul, `experiments/D05_6/run_D05_6.py`)
- **QUESTION :** A (frein), B (sprint) et C (coussin) font-ils mieux qu'un risque fixe, en réussite, en délai et en
  valeur ?
- **MÉTHODE :**
  - `propfirm.simuler` avec une taille fonction de l'état du compte : poids = min(1, risque / ATR14) ; seuils sur le
    capital valorisé de chaque compte.
  - Même règle en challenge et en compte financé.
  - Références : risque fixe de 0,05 à 0,25 ; C à r0 = 0,10, 0,15, 0,20 et 0,25.
  - Comparaison au risque fixe au même délai médian, par interpolation linéaire.
- **CRITÈRE DE LECTURE :** réussite, causes d'échec, délais, valeur à 12 mois ; tous les départs et sans 2026 ; cible du
  porteur.

#### Résultats (`experiments/D05_6/rapport_D05_6.md`)
- **Contrôle passé :** chaque risque fixe redonne D05.4 et D05.5.
- [OBS] **A, frein :** 61,2 % en 79 jours, +1,9 point au même délai (sans 2026 : +0,9) ; valeur +3 768 €, soit
  −4 653 € au même délai.
- [OBS] **B, sprint :** 69,1 % en 158 jours, −5,7 points au même délai (sans 2026 : −4,9) ; valeur +3 459 €.
- [OBS] **C, coussin :**
  - aucun échec par la perte totale, par construction ;
  - réussite de 93 à 98 %, soit +17 à +24 points au même délai, mais P90 du délai de 682 à 1 081 jours ;
  - sans 2026, 38 à 43 % des comptes restent en cours et la réussite retombe à 57-61 % ;
  - valeur de +2 171 à +4 484 €.
- [OBS] **Cible du porteur (délai médian de 90 à 180 jours, réussite d'au moins 60 à 65 %) :**
  - tous les départs : risque fixe à 0,10 (78,5 %, 173 j) et 0,15 (60,4 %, 100 j), B, C à r0 de 0,15 à 0,25 ;
  - sans 2026 : seul C à r0 = 0,20 (60,9 %, 111 j, 38,6 % en cours).
- [HYP] **Le coussin protège la réussite, le risque fixe haut maximise la valeur.** Une taille propre à chaque phase
  (C en challenge, risque fixe haut en compte financé) est le facteur suivant à mesurer.

#### Décision
- [ ] **VALIDÉ**
- [x] **Mesures faites ; choix de la taille et suite (D05.7, D05.1) à décider par le porteur.** Commit local, non
  poussé.

### [DÉCISION] — « Burn & Churn », une taille propre à chaque phase ; GO de D05.6bis (2026-10-05)
- **Compte financé, nature acceptée par le porteur (« Burn & Churn ») :** extraire le plus possible avant la perte
  totale de 10 %, au risque de 0,20 ou 0,25 ; pas de survie recherchée.
- **Objectifs découplés :**
  - challenge (P1 + P2) : réussite la plus haute possible avec un délai raisonnable, moins de 120 jours (la cible
    précédente était un délai médian de 90 à 180 jours) ;
  - compte financé : valeur la plus haute.
- **Combinaisons à mesurer :**
  - A : coussin r0 0,15 ou 0,20 en challenge ; fixe 0,20 puis 0,25 en compte financé ;
  - B : fixe 0,15 en challenge ; fixe 0,20 puis 0,25 en compte financé.
  - Mesures propres de l'agent autorisées dans le même calcul. Valeur d'une tentative à 12 et 24 mois, contre le risque
    fixe 0,20 dans les deux phases (+9 218 €).
- **D05.7 et D05.1 en pause** jusqu'au verrouillage de la taille.
- **Chiffres du porteur vérifiés :** fixe 0,15 à 60,4 % en 100 jours (D05.6) et +9 218 € (D05.5), conformes. Le
  challenge du combo A dépasse 120 jours de délai médian (137 et 174 jours, D05.6).
- **Push :** aucun ; commit local.

### [EXP-D05.6bis] — Une taille propre à chaque phase : challenge et compte financé (« hybride »)
- **Date :** 2026-10-05
- **Étape :** D05, étape 3 bis. GO du porteur.
- **Actifs & Période :** ceux de D05.4 ; 5 bps (or 4 bps).

#### 0. Cadrage (fixé avant le calcul, `experiments/D05_6bis/run_D05_6bis.py`)
- **QUESTION :** une taille propre à chaque phase bat-elle le risque fixe 0,20 dans les deux phases ?
- **MÉTHODE :**
  - Une simulation par taille de challenge et par taille de compte financé, reliées par `valeur` et par `suite` (7 × 7
    combinaisons).
  - Challenge : fixe 0,10 à 0,30 ; coussin r0 0,15 et 0,20. Compte financé : fixe 0,10 à 0,30 ; coussin r0 0,20 ;
    relance (0,20 ; 0,40 à −5 % ; 0,20 de nouveau au-dessus de −2 %).
  - 0,30 ajouté après un premier calcul, le meilleur r de la suite étant au bord de la grille (0,25).
  - Nouvelle mesure, `propfirm.suite` : un seul compte à la fois, nouvelle tentative de 540 € au minuit qui suit chaque
    échec du challenge ou chaque perte du compte financé (lecture « Burn & Churn »).
- **CRITÈRE DE LECTURE (sans seuil) :** valeur à 12 et 24 mois, et sans 2026, par tentative et par suite ; écart apparié
  à la référence avec IC par blocs de mois ; queues ; écart par année de départ.

#### Résultats (`experiments/D05_6bis/rapport_D05_6bis.md`)
- **Contrôle passé :** les tailles fixes et le coussin dans les deux phases redonnent D05.5 et D05.6.
- [OBS] **Ni A ni B ne battent la référence.**
  - A : −0,8 à −3,2 k€ par tentative à 12 mois (jusqu'à −4,8 k€ sans 2026) ; en suite, environ −11 k€ en 12 mois et
    −30 k€ en 24 mois (challenges bloqués).
  - B : égal par tentative (−274 € et +7 € à 12 mois, IC autour de zéro) ; −1,7 à −3,2 k€ en suite.
- [OBS] **Bat la référence partout (tentative et suite, 12 et 24 mois, sans 2026, IC sans zéro, chaque année de
  départ) : challenge à 0,20, compte financé plus agressif.**
  - Compte financé fixe 0,25 : +1,0 à +1,2 k€ par tentative ; +2,4 à +6,8 k€ en suite.
  - Compte financé en relance : +1,7 à +2,1 k€ par tentative ; +3,6 à +10,4 k€ en suite.
  - Fixe 0,30 en compte financé fait moins bien que 0,25 ; le coussin y coûte 2,9 à 5,3 k€.
- [OBS] **En suite, un challenge plus rapide paie :** à 0,25 ou 0,30, il bat 0,20 à compte financé égal ; jusqu'à
  +17,5 k€ en 24 mois (0,30 × relance) ; optimum non atteint à 0,30. Par tentative, ces challenges perdent 0,8 à
  6,9 k€.
- [OBS] **Démarré à un minuit quelconque, le compte financé à 0,25 ou en relance retire moins qu'à 0,20** (16,1 et
  15,7 k€ contre 18,0 k€ en 12 mois). Démarré juste après une réussite, il retire plus.
- [HYP] **Le challenge sert de filtre de période :** il réussit dans les bonnes périodes de RE-1, que le compte financé
  agressif exploite ensuite. À tester en D05.7, où des blocs courts coupent la persistance des périodes.

#### Décision
- [ ] **VALIDÉ**
- [x] **Mesures faites ; verrouillage de la taille à décider par le porteur.** Commit local, non poussé.

### [DÉCISION] — Relance gardée ; roster final de trois pistes ; D05.7 sur ce roster, après GO (2026-10-05)
- **Relance gardée par le porteur,** malgré une éventuelle règle de comportement de la firme : la perte du porteur est
  plafonnée au prix du challenge (convexité).
- **Roster final :**
  - piste 1, compromis sûr : challenge 0,20 × compte financé 0,25 ;
  - piste 2, Burn & Churn pur : 0,25 × 0,25 ;
  - piste 3, convexité : relance en compte financé, avec un challenge à 0,20, 0,25 ou 0,30 ;
  - la référence (0,20 × 0,20) reste l'ancre.
- **Récap demandé (`run_D05_6bis.py --roster`, contrôle passé ; lecture ajoutée sans 2026 à 24 mois, base de D05.7) :**
  - seul le compte financé à 0,25 (piste 1) gagne dans toutes les lectures et chaque année de départ ;
  - le challenge rapide perd par tentative. En suite, il gagne à 12 mois ; à 24 mois, il devient fragile de 0,20 à
    0,25 (+0,3 à +2,7 k€) et reste net de 0,25 à 0,30 (+6,1 à +6,4 k€) ;
  - la relance au lieu de 0,25 : dans le bruit par tentative avec un challenge à 0,20 ; +3,6 à +4,8 k€ en suite à
    24 mois ;
  - en suite à 24 mois, 3c est en tête (+58,9 k€), devant 3a, 3b et 2 (+50,9 à +52,5 k€) puis 1 (+48,2 k€) ; par
    tentative, 1 et 3a sont en tête.
- **Relecture du porteur corrigée :**
  - le combo B n'a pas de coussin (fixe 0,15) : égal à la référence par tentative, −1,7 à −3,2 k€ en suite ;
  - « +25 à +26 k€ » sont les valeurs des suites à 12 mois des pistes rapides. Sur les +5,2 k€ de la piste 2 au-dessus
    de la référence, +2,7 k€ viennent du compte financé à 0,25 ;
  - un challenge plus agressif perd par tentative ; il ne gagne qu'en suite.
- **D05.7 :** tirage par blocs sans 2026 sur ce roster ; cadrage soumis au porteur, GO attendu.
- **Push :** aucun ; commit local.

### [DÉCISION] — GO de D05.7 (blocs d'une et de quatre semaines) ; push autorisé (2026-10-05)
- **GO du porteur :** tirage par blocs sans 2026 sur le roster final, deux séries de 200 histoires :
  - blocs d'une semaine : l'enchaînement des semaines est entièrement détruit ;
  - blocs de quatre semaines : un mois d'enchaînement est gardé.
- **Lecture annoncée par le porteur :** si l'avantage des pistes rapides s'effondre avec des blocs d'une semaine mais
  résiste avec des blocs de quatre, le modèle a besoin d'un régime persistant d'au moins un mois. Nuance de l'agent :
  le tirage donne un indice, pas une preuve ; l'histoire réelle reste une seule trajectoire.
- **Push autorisé et fait :** `b5cecb5`, `6fc12d2`, `5f4cc65` ; origin/main = `5f4cc65`.
- **Prompt Sniper :** la phrase du porteur sur cTrader reste hors des commits (session parallèle).

### [EXP-D05.7] — Tirage par blocs de semaines, sans 2026 : le roster final face à des histoires recomposées
- **Date :** 2026-10-05
- **Étape :** D05, étape 4. GO du porteur.
- **Actifs & Période :** six actifs ; 221 semaines du lundi 2021-10-04 au lundi 2025-12-29 (sans 2026) ; 5 bps (or
  4 bps).

#### 0. Cadrage (fixé avant le calcul, `experiments/D05_7/run_D05_7.py`)
- **QUESTION :** les gains du challenge rapide et de la relance survivent-ils quand on détruit l'enchaînement des
  semaines (blocs d'une semaine), ou au-delà d'un mois (blocs de quatre semaines) ?
- **MÉTHODE :**
  - Nouveau module `propfirm.blocs`, testé : chaque semaine tirée apporte ses trades sur les six actifs, avec leur
    chemin de prix d'origine.
  - 200 histoires par longueur de bloc.
  - Le roster et la référence sont évalués sur chaque histoire : tentative et suite, à 12 et 24 mois.
- **CRITÈRE DE LECTURE (sans seuil) :** distribution des écarts entre pistes ; part des histoires où l'écart est
  positif ; rang de l'histoire réelle.

#### Résultats (`experiments/D05_7/rapport_D05_7.md`)
- **Contrôle passé :** l'histoire identité redonne exactement la simulation d'origine.
- [OBS] **La vitesse du challenge survit en suite.** Chaque pas (0,20 → 0,25 → 0,30) rapporte en médiane +1,9 à
  +2,3 k€ en 12 mois et +3,4 à +4,1 k€ en 24 mois. L'écart est positif dans 80 à 94 % des histoires, aux deux
  longueurs de bloc.
- [OBS] **La relance ne survit pas :** médiane de −1,1 à +0,1 k€ au lieu du fixe 0,25 ; positive dans 37 à 58 % des
  histoires.
- [OBS] **Le compte financé à 0,25 au lieu de 0,20 ne survit pas par tentative** (médiane proche de zéro, positif dans
  42 à 52 % des histoires). En suite, il garde un petit gain (+0,4 à +1,3 k€, 62 à 68 %).
- [OBS] **Les blocs de quatre semaines donnent presque les mêmes résultats que ceux d'une semaine.**
- [OBS] **L'histoire réelle était favorable à toutes les pistes** (78e à 96e centile).
  - Médianes recomposées : +3,1 à +4,6 k€ par tentative à 12 mois ; +23 à +34 k€ en suite à 24 mois.
  - Valeur positive dans 90 à 99,5 % des histoires.
- [HYP] **La vitesse paie par mécanique** (plus de tentatives). La relance et le compte financé agressif misaient sur
  l'ordre réel des semaines : persistance de plus d'un mois, ou chance.

#### Décision
- [ ] **VALIDÉ**
- [x] **Mesures faites ; choix de la taille à décider par le porteur.** Commit local, non poussé.

### [DÉCISION] — Piste 1 verrouillée ; fin des recherches sur la taille ; piste 2 archivée ; GO du test du moment d'achat (2026-10-05)
- **Taille verrouillée par le porteur : piste 1, challenge 0,20 %/ATR × compte financé 0,25 %/ATR.**
  - Raisons du porteur : discipline budgétaire et psychologique au démarrage ; un compte à la fois, budget de
    tentatives contrôlé, sans rachat aveugle ; réussite du challenge protégée.
- **Relecture de l'agent.** Une fois les semaines mélangées (D05.7), la piste 1 égale la référence en médiane par
  tentative, mais fait moins bien qu'elle dans 52 à 56 % des histoires. Elle ne garantit donc pas de faire au moins
  aussi bien. Correction d'une formule de l'agent (« jamais moins bonne que la référence ») : vrai en médiane, pas
  histoire par histoire.
- **Piste 2 (0,25 × 0,25) archivée comme option de croissance,** à reprendre plus tard avec un Burn & Churn limité.
- **Idée du porteur pour après D05.1 :** les hivers crypto font échouer les challenges. Ajouter des actions ou
  d'autres actifs de la finance traditionnelle pourrait créer des occasions quand la crypto stagne, et relever la
  réussite.
- **Fin des recherches sur la taille des positions en prop firm.**
- **GO d'une dernière mesure, EXP-D05.8 :** acheter le challenge à un moment choisi plutôt qu'un jour quelconque
  (sortie de compression de l'ATR moyen du panier crypto, ou tendance haussière simple), sur les pistes 1 et 2 ;
  puis clôture de la séquence.

### [EXP-D05.8] — Moment d'achat du challenge : sortie de compression de la volatilité, tendance haussière
- **Date :** 2026-10-05
- **Étape :** D05, étape 5 (dernière mesure de la séquence taille). GO du porteur ; référence ajoutée à sa demande.
- **Actifs & Période :** ceux de D05.4 ; indicateurs sur les cinq cryptos ; 5 bps (or 4 bps).

#### 0. Cadrage (fixé avant le calcul, `experiments/D05_8/run_D05_8.py`)
- **QUESTION :** acheter le challenge seulement quand la volatilité du panier crypto sort d'une compression (V), ou
  quand le panier est en tendance haussière (T), améliore-t-il la réussite et la valeur ?
- **MÉTHODE :**
  - V : ATR moyen sur 7 jours au-dessus de sa moyenne sur 30 jours, cette moyenne étant sous la médiane de l'année.
  - T : indice du panier au-dessus de sa moyenne sur 50 jours.
  - Indicateurs causaux, calculés à chaque minuit.
  - Lectures par tentative (jours ouverts contre tous) et en suite : un compte à la fois, rachat seulement les jours
    ouverts (`propfirm.suite`, `permis`).
  - Pistes : référence, piste 1, piste 2.
- **CRITÈRE DE LECTURE (sans seuil) :** écarts avec IC par blocs de mois ; réussite ; challenges achetés ; écart par
  année de départ.

#### Résultats (`experiments/D05_8/rapport_D05_8.md`)
- **Contrôles passés :** causalité des indicateurs ; sans filtre, les pistes redonnent le roster de D05.6bis.
- [OBS] **T n'aide pas :** +0,0 à +0,7 k€ par tentative ; −1,7 à −6,1 k€ en suite (IC sous zéro).
- [OBS] **V : +3,2 à +4,7 k€ par tentative, IC avec zéro.**
  - Le gain vient des départs de 2023 et 2024 ; ceux de 2025 perdent.
  - En suite, l'attente coûte −0,7 à −1,9 k€ (référence, piste 1) et jusqu'à −9,3 k€ (piste 2).
  - V économise 20 % des challenges ; la valeur par challenge acheté monte de 14 à 19 % (piste 1).
- [OBS] **Avec une règle d'attente, la piste 1 dépasse la piste 2 en suite** à 24 mois et sans 2026 ; sans filtre, la
  piste 2 restait devant.
- [HYP] RE-1 joue dans les deux sens : la tendance haussière ne choisit pas ses périodes. Le gain de V tient à
  quelques épisodes.

#### Décision
- [ ] **VALIDÉ**
- [x] **Mesures faites ; filtre de moment d'achat à décider par le porteur.** Recommandation de l'agent : aucun
  filtre. Commit local, non poussé.

### [DÉCISION] — Clôture de la séquence taille (D05.4 à D05.8), à la demande du porteur (2026-10-05)
- **Configuration retenue :** piste 1, challenge 0,20 %/ATR × compte financé 0,25 %/ATR ; un compte à la fois, budget de
  tentatives contrôlé.
- **Archivé :** piste 2 (0,25 × 0,25), option de croissance ; relance ; coussin, frein, sprint ; filtres de moment
  d'achat V et T (D05.8).
- **Repères pour les projections :** médianes des histoires recomposées de D05.7, plus prudentes que l'historique réel.
- **Suite :** D05.1 (profil des actifs, puis export cTrader de GLE fourni par le porteur) ; idée du porteur : des actifs
  de la finance traditionnelle pour les hivers crypto.

### [DÉCISION] — Aucun filtre d'achat ; push de D05.7 et D05.8 ; ouverture de D05.1, actifs TradFi (2026-10-05)
- **Décisions du porteur, après lecture de D05.8 :**
  - filtre d'achat du challenge : aucun ; rachat au minuit qui suit la fin du compte précédent ;
  - push de `74464dc` (D05.7) et `ee1ee00` (D05.8) : fait, origin/main = `ee1ee00` ;
  - D05.1 : univers étendu à la finance traditionnelle, GLE n'étant qu'un candidat parmi d'autres (US100, GBPJPY…) ;
    d'abord un profil théorique des actifs pour RE-1, avant toute donnée nouvelle ; ensuite, après validation, un
    extracteur Python → cTrader Open API (OAuth à configurer avec le porteur) → barres de 30 min 2020-2025 (OHLC, écart,
    volume) → CSV ou Parquet.
- **Relecture des énoncés du porteur :**
  - « Always in the Market » : un compte toujours actif (rachat immédiat), pas une position permanente ; RE-1 reste à
    plat entre ses trades.
  - US100 et GBPJPY ont déjà été mesurés en D01.7 (Saxo, 2020-2025) : −0,097 et −0,303 ATR à 4 bps.
- **Push :** fait pour ces deux commits ; la suite reste en commits locaux.

### [EXP-D05.1, cadrage] — Profil des actifs pour RE-1 hors crypto (note, aucun calcul)
- **Date :** 2026-10-05
- **Livrable :** `experiments/D05_1/profil_actifs_D05_1.md`.
- **Méthode :** relecture des mesures existantes (A01 à D05.7, K7 à K18, livre blanc) ; grille de lecture sans seuil.
- **Contenu :**
  - [OBS] ADN de RE-1 : cassure d'une compression courte, tenue 13 h ; queue droite (1 % des trades, environ deux grands
    gagnants par an, 84 % de la somme nette sur BTC) ; les deux sens ; avantage dépendant de l'époque.
  - [OBS] Signal transposé sur les 13 séries hors crypto, rente non : brut de −0,17 à +0,42 ATR (médiane +0,15), aucun
    IC > 0.
  - Ratio vital brut / frais : cryptos 3,6 à 4,2 ; indices, or, argent et GBPJPY 0,2 à 1,0. Points morts du coût
    aller-retour : BTC ≈ 18 bps, indices 2 à 5 bps, GBPJPY ≈ 1 bp.
  - Empreinte : z26 (mouvement de 26 barres en ATR14(t)) plutôt que le rendement de 30 min ; kurtosis de sauts contre
    kurtosis d'expansion ; repère gaussien (10 ATR en 13 h ≈ une fois par an, 15 ATR jamais) ; fréquences et quantiles
    plutôt que moments.
  - Structure : VR(q) et ratio d'efficacité ; chocs continus contre chocs d'un bloc ; saisonnalité horaire ;
    indépendance vis-à-vis des cryptos.
  - Opérationnel : écart aux heures des entrées ; swap absent de tous les tests, cryptos comprises ; glissement des
    stops ; cadence selon les séances ; plafond de 1x sous 20 à 25 bps d'ATR ; roulements des CFD sur futures.
  - [HYP] Par classe : énergie en CFD continu la plus proche du profil sur le papier ; indices suspendus au coût réel de
    la firme ; change sans queue d'expansion ; actions proches des ETF de séance.
- **Décision :** en attente du porteur (grille, liste des candidats, période et statut de 2026). Commit local.

### [DÉCISION] — D05.1 : D01.7 écarté comme filtre ; candidats, période et firme ; objectif : l'inclusion dans le portefeuille ; extracteur cTrader (2026-10-05)
- **Décisions du porteur :**
  - les conclusions de D01.7 ne servent pas à choisir les actifs. Motif du porteur : en prop firm (taille hybride,
    « Burn & Churn »), un actif à espérance brute légèrement négative peut augmenter la réussite d'un challenge, en
    ajoutant de la variance décorrélée des cryptos pendant les hivers ;
  - mission : trouver des actifs qui reproduisent le phénomène « crypto » de RE-1 (cassure de compression, puis
    expansion directionnelle sur 13 h) ;
  - grille validée ; candidats : GLE, WTI, Brent, US100, US30, GER40 et GBPJPY ; fiches des six actifs actuels pour
    leurs coûts réels et leurs swaps ;
  - période : de 2020-01 à aujourd'hui, 2026 incluse ; firme : FTMO (compte d'essai sur cTrader), dont les coûts, écarts
    et swaps feront foi ;
  - objectif de D05.1 : modéliser l'inclusion de ces actifs dans le portefeuille global et voir si la nouvelle
    configuration bat la piste 1 ou la piste 2 sur un challenge FTMO ;
  - push de `4a96066` et `3f6672d` : fait (origin/main = `3f6672d`).
- **Relecture de l'agent (à mesurer, pas un veto) :**
  - [HYP] Modèle de premier passage (brownien, sans limite de temps) : la réussite ne dépend que de μ/σ². Un compte sans
    avantage réussit P1 dans 10/19 ≈ 53 % des cas, P1 + P2 dans ≈ 35 %. Une variance indépendante sans dérive rapproche
    la réussite de ces valeurs : elle ne l'augmente que si l'on part d'en dessous, si l'actif couvre (corrélation
    négative les jours de pertes crypto, comme l'or) ou, en suite de tentatives, par la vitesse de résolution.
  - Le témoin naturel est la piste 2, qui ajoute de la variance par r avec la dérive de RE-1.
  - GBPJPY : D01.7 l'avait trouvé sans suite à 30 min ; la mesure de persistance de la grille tranchera.
- **Fait `[CODE]` :**
  - `src/marketdata/ctrader.py` : JSON sur WebSocket (port 5036) ; OAuth (URL d'autorisation en lecture seule, point
    jeton, connexion du porteur par serveur de retour local) ; client apparié par clientMsgId, avec battement, limite
    de débit et cadence de l'historique ; comptes, symboles par nom exact, fiches ; barres relatives → prix ;
    téléchargement à rebours par fenêtres, avec hasMore ; réserve 2026 par `reserve.levee` ; écriture au schéma de
    `load_ohlc` ; 18 tests (399 au total).
  - `experiments/D05_1/donnees_D05_1.py` (--connexion, --symboles, --telechargement) : non lancé.
- **Application (2026-10-05) :** « AKF-TSO Research Data » créée par le porteur, accès « Access info on your accounts »
  (lecture seule, ses comptes) et URL de retour `http://localhost:47322/akf-ctrader` ; description ramenée à 175
  caractères (300 au plus). Client ID et Secret posés par le porteur (`setx`), lisibles par le module.
  [OBS] Connexion JSON à demo.ctraderapi.com:5036 établie ; ProtoOAApplicationAuthReq refusé :
  CH_CLIENT_AUTH_FAILURE (« OA client is not in active state ») : statut « Submitted », accord de Spotware attendu.
- **En attente :** accord de Spotware ; puis --connexion et --symboles (sur GO) ; noms exacts validés ;
  téléchargement (sur GO).
- **Push :** aucun ; commit local.

### [EXP-D05.1, grille] — Mesure de la grille de profil, sans RE-1 ni coût (ancres, or, candidats Saxo, 2020-2025)
- **Date :** 2026-10-05 ; GO du porteur (« GO pour la mesure de la grille »), pendant l'attente de l'accord de Spotware.
- **Actifs & Période :** BTC (Bitstamp) et SOL (Coinbase) en ancres ; or (HistData) en repère TradFi du portefeuille ;
  candidats US100, US30, GER40 et GBPJPY (séries Saxo de D01.7) ; du 2020-01-01 au 2025-12-31 (SOL dès 2021-06-17).
- **Code :** `src/profil/grille.py` (13 tests) ; `experiments/D05_1/run_grille_D05_1.py --calcul`.

#### 0. Cadrage (fixé avant le calcul)
- **QUESTION :** les candidats montrent-ils, en structure de marché, l'empreinte des marchés où RE-1 gagne (expansions
  de 13 h nées du calme, des deux côtés, en continu ; persistance aux heures ; indépendance vis-à-vis des cryptos) ?
- **PERTINENCE :** grille de la note de profil, validée par le porteur ; mesure descriptive avant les données FTMO, dont
  viendront les coûts.
- **CE QUE LE PROTOCOLE MESURE :** les axes calculables sur les barres : échelle et plafond de 1x ; queue d'expansion et
  repère gaussien ; naissance au calme ; sauts ou expansions ; persistance ; symétrie ; saison horaire ; continuité ;
  gaps ; indépendance vis-à-vis de BTC ; activité pendant le creux du portefeuille de RE-1 (2023-07-13 → 2024-01-27).
  Fenêtres disjointes de 26 barres ; z26 = (open[t + 27] − open[t + 1]) / ATR14(t).
- **CE QU'IL NE PERMET PAS DE CONCLURE :** aucune rentabilité (ni RE-1, ni coûts) ; source Saxo (prix vendeur), pas
  FTMO ; 2020-2025 seulement ; aucun classement ni seuil ; BTC 2020-2025 est la période de construction de RE-1. WTI,
  Brent et GLE seront mesurés sur les données FTMO.

#### Résultats (`experiments/D05_1/narratif_grille_D05_1.md`)
- [OBS] **Queue de 13 h en ATR(t) :** 11 à 28 fois le repère gaussien (1,75 fenêtre sur 1 000 à |z26| ≥ 10). Pour
  1 000 fenêtres : US100 49,3, BTC 41,6, US30 41,5, or 31,2, GER40 28,4, SOL 22,9, GBPJPY 19,4. Par an, à 15 ATR ou
  plus : BTC 7,8, US100 6,2, US30 6,0, SOL 4,0, or 3,7, GBPJPY 2,0, GER40 1,3.
- [OBS] **Saison horaire** (TR de l'heure la plus agitée / la plus calme) : BTC 1,7, SOL 1,5, GBPJPY 2,2, GER40 3,2,
  or 3,5, US30 4,1, US100 4,4. [HYP] Une part de la queue des indices vient de l'ouverture au comptant à heure fixe.
- [OBS] **Axes sans pouvoir distinctif :** VR(26) de 0,89 à 0,98 (BTC le plus bas) ; 77 à 81 % des grandes fenêtres
  nées sous la médiane d'ATR, partout ; plus gros pas de 30 à 38 % du mouvement, partout.
- [OBS] **Calendrier et gaps :** 58 à 64 % des fenêtres des indices et de l'or traversent une coupure (GBPJPY 11 %,
  cryptos 0) ; gaps de 4 ATR ou plus : 1,0 à 2,8 par an hors cryptos.
- [OBS] **Plafond de 1x à r = 0,20 :** 43 % (US100) à 92 % (GBPJPY) des barres hors cryptos ; BTC 6 %.
- [OBS] **Lien avec BTC** (corrélation des |r| quotidiens ; jours extrêmes communs, 5 % si indépendants) : GBPJPY 0,10
  et 8,5 % ; or 0,16 et 16 % ; indices 0,31 à 0,34 et 17 à 22 % ; SOL 0,57 et 41 %.
- [OBS] **Creux du portefeuille de RE-1 (2023-07-13 → 2024-01-27) :** fenêtres à 10 ATR ou plus, rapportées à la
  moyenne : BTC 1,64, SOL 1,20, or 1,34, GBPJPY 1,36, US100 0,91, US30 0,69, GER40 0,65.
- [OBS] **Asymétrie à 10 ATR ou plus (hausses / baisses) :** BTC 93 / 75 ; US100 56 / 76 ; US30 44 / 67 ; GER40 22 / 46 ;
  or et GBPJPY symétriques.
- **Corrections de la note de profil** (addendum, §10) : le VR ne marque pas les marchés de RE-1 ; « un hiver est un
  marché sans expansion » n'est pas soutenu ; GBPJPY a une queue d'expansion, la plus mince ; la naissance au calme,
  telle que définie, est universelle.

#### Décision
- [x] **Mesure faite, descriptive ; lecture au porteur.** Proposé sur GO : z26 corrigé de la saison horaire ; données
  FTMO (coûts, swaps ; WTI, Brent, GLE). Commit local.

### [EXP-D05.1, correction horaire] — Queue de 13 h corrigée de la saison horaire
- **Date :** 2026-10-06 ; GO du porteur (« GO pour la correction horaire »).
- **Code :** `profil.grille` (`facteur_saison`, `atr_desaisonnalise`, `z_saison`, `profil_saison` ; 4 tests de plus) ;
  `experiments/D05_1/run_grille_D05_1.py --saison`.

#### 0. Cadrage (fixé avant le calcul)
- **QUESTION :** la queue de 13 h des indices et de l'or tient-elle une fois retirée la saison horaire ?
- **PERTINENCE :** en ATR brut, US100 et US30 égalent BTC, avec une saison horaire 2,4 à 2,6 fois plus marquée. Une
  marche gaussienne à saison pure (une barre par jour six fois plus agitée) donne déjà 49 fenêtres à 10 ATR ou plus pour
  1 000 en ATR brut, contre 5,7 une fois corrigée (test du module).
- **CE QUE LE PROTOCOLE MESURE :** z26 corrigé = mouvement de 13 h / (ATR désaisonnalisé de t × racine de la moyenne des
  facteurs² de la fenêtre) ; facteur causal par demi-heure en heure locale, sur les 40 jours précédents ; fuseaux fixés :
  UTC (cryptos), New York (US100, US30, or), Francfort (GER40), Londres (GBPJPY) ; z26 brut sur les mêmes fenêtres ;
  même repère gaussien.
- **CE QU'IL NE PERMET PAS DE CONCLURE :** aucune rentabilité ; RE-1 utilise l'ATR14 brut pour ses stops et sa taille ;
  40 jours et demi-heure locale sont conventionnels, non optimisés ; mêmes limites de source que la grille.

#### Résultats (`experiments/D05_1/narratif_grille_D05_1.md`, §7 ; `grille_saison_D05_1.csv`)
- [OBS] **Fenêtres à 10 ATR ou plus pour 1 000, brut → corrigé :** BTC 40,2 → 34,7 ; SOL 22,1 → 19,5 ; or 30,8 → 15,1 ;
  US100 51,2 → 16,8 ; US30 43,3 → 13,7 ; GER40 25,7 → 13,0 ; GBPJPY 21,7 → 15,2 (repère gaussien 1,75).
- [OBS] **À 15 ATR ou plus par an, corrigé :** BTC 7,0, SOL 3,1, US100 1,6, GBPJPY 1,3, US30 1,1, or 1,0, GER40 0,8.
- [OBS] **Après correction, BTC garde 2,1 à 2,7 fois la queue de chaque candidat.** Les indices penchent à la baisse
  (US100 : 5,2 hausses pour 11,6 baisses ‰).
- [HYP] La queue brute des indices est surtout l'ouverture au comptant, rapportée à un ATR de nuit. Les expansions de
  13 h hors heure fixe sont deux à trois fois plus rares sur les candidats que sur BTC.
- **Méthode :** fréquences moyennées sur les 26 alignements des fenêtres. Un alignement unique déplaçait les comptes
  rares (BTC, 20 ATR ou plus : 2,2 ou 4,0 par an selon le départ) ; les comptes à 10 ATR de la grille restent à 10 %
  près.

#### Décision
- [x] **Mesure faite ; lecture au porteur.** Commit local.


### [DÉCISION] — Correction horaire mise de côté ; attente de l'accord de Spotware (2026-10-06)
- **Décision du porteur :** « Oublie la correction des horaires, on attend le mail. » La correction horaire (§7 du
  narratif de la grille) n'entre pas dans la lecture ; aucun calcul en attendant.
- **État :** application Open API « Submitted » (ID 42882) ; aucun courriel de Spotware au 2026-10-06. Commits locaux
  non poussés : `2eb5e81` (correction), `94616c2` (enseignements I-M21 et K19) et celui-ci.
- **Suite :** à l'accord de Spotware, --connexion (sur GO), puis --symboles et le téléchargement.


### [EXP-D05.1, données FTMO et frictions] — Récupération par cBot, vérification, frictions trade par trade (2026-10-06)
- **Décisions du porteur (2026-10-06) :**
  - pas de mail de Spotware : export par un cBot cTrader (GO) ;
  - GLE absent chez FTMO, remplacé par SAN ;
  - « On finit la récupération des datas et leur vérification et on fait ensuite une passation » ; l'objectif
    stratégique (sauver la piste 2 par le portefeuille) se fera dans une nouvelle session ;
  - « gérer ici proprement les trous, écart, swaps, commission » ; données cTrader pour les actifs hors crypto.
- **Code :**
  - `experiments/D05_1/cbot/AkfExportFtmo.cs` (v1 puis v2) ;
  - `marketdata.ftmo` (lecture, écriture, écarts, profil, pauses) ;
  - `propfirm.frictions` (écart, commission, rollovers, swaps, pauses) ;
  - frais par trade dans `envelope.portfolio` et `propfirm` ;
  - `audit_ftmo_D05_1.py` ; `run_frictions_D05_1.py` (--import, --frictions faits ; --baseline préparé, non lancé) ;
  - 456 tests.

#### Résultats (`experiments/D05_1/narratif_frictions_D05_1.md`, `audit_ftmo_D05_1.md`)
- [OBS] **11 symboles récupérés, SAN et AVAX non.** L'instance v2 a gardé l'ancienne liste ; AVAX se nomme `AVAUSD`.
  Les indices et le pétrole commencent le 2020-11-08, l'or le 2020-05-06, GBPJPY le 2020-04-01, BTC et ETH le 2020-07-08,
  SOL le 2025-04-17.
- [OBS] **Recoupement avec Saxo, HistData, Bitstamp et Coinbase :**
  - corrélation des rendements de 30 min de 0,98 à 0,998 (WTI : 0,93 face au continu raccordé de Saxo) ;
  - décalage nul partout ;
  - niveau à +0,5 à +2,3 bps hors crypto, −4 à −18 bps sur les cryptos (bid FTMO face à un prix de transaction).
- [OBS] **Écarts médians (bps) :** indices 0,5 à 0,8 ; GBPJPY 1,0 ; or 1,0 ; WTI 8,6 ; Brent 7,1 ; BTC 0,1 ; ETH 2,2 ;
  SOL 2,5 ; XRP 10,0.
- [OBS] **Fiches :**
  - cryptos : swap de −30 % par an (8,3 bps par nuit, triple le vendredi), commission de 3,25 bps par côté, levier 1:1 ;
  - indices, pétrole et or : levier 1:15 ;
  - GBPJPY : levier 1:30, 2,5 USD par lot.
  - L'étalon de D05.4 retenait 1:2 et 1:30.
- [OBS] **Pauses du samedi** dans les barres des cryptos, absentes des séances officielles. Leur traitement abandonne
  47 à 49 entrées par actif et décale 28 à 42 sorties sur 2021-10 → 2026-10.
- [OBS] **Frictions par trade, fenêtre D05 :** de 8,9 bps (BTC) à 19,1 bps (XRP), contre 5 bps.
  - Net par trade, convention → FTMO : BTC +0,240 → +0,134 ATR ; ETH −0,063 → −0,193 ; SOL +0,177 → +0,091 ;
    AVAX +0,308 → +0,215 ; XRP +0,391 → +0,117.
  - Or : 1,9 bps contre 4.
  - Or sur barres FTMO : brut +0,14 ATR contre +0,36 sur HistData, pour 447 entrées communes.
- [HYP] **Points non vérifiés :**
  - rollover à 17:00 New York ;
  - base de 360 jours des swaps en % ;
  - swaps du pétrole : 25 bps par nuit en short à la lettre, une unité à vérifier ;
  - pauses du samedi : maintenance, ou trous du serveur d'essai ;
  - AVAX sur l'écart de SOL.

#### Décision
- [x] **Données et frictions faites ; passation pour la session suivante** (`passation_D05_1.md`). Commits locaux.
