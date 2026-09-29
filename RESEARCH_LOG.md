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
