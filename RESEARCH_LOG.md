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
