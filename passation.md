# PASSATION — AKF-TSO : fin de l'Étape C → Étape D

> **À lire en entier avant toute action.** Rédigée le 2026-09-29 par la session qui a mené les Étapes A à C. Elle donne :
> - l'état du projet et les règles ;
> - les résultats et les problèmes rencontrés ;
> - le plan de la suite et les fichiers à lire.
>
> Tout ce qui est écrit ici a été vérifié dans le dépôt le jour de la rédaction. En cas de doute, le dépôt fait foi : `RESEARCH_LOG.md` pour l'historique, `BEST_RESULTS.md` pour les chiffres.

## Sommaire
0. En une minute
1. Le porteur et la façon de travailler
2. Règles non négociables
3. Dépôt, GitHub, environnement
4. Carte du dépôt et ordre de lecture
5. Historique : de la Phase 0 à C05
6. La stratégie cœur RE-1 (figée)
7. Problèmes rencontrés et leçons
8. Étape D : direction et chantier D01
9. Dossiers externes (lecture seule)
10. Premier message attendu de la nouvelle session

---

## 0. En une minute

- **Projet :** AKF-TSO. Recherche en trading systématique autour du déclencheur de l'indicateur Pine *AKF-TSO v2.1*, un filtre de Kalman adaptatif à deux états (niveau, vitesse) avec un oscillateur de tendance.
- **But :** une mécanique de trading simple, rentable après frais, et robuste hors échantillon.
- **Démarche :** mesurer → caractériser → catégoriser → isoler → exploiter l'information cinématique du moteur (`RESEARCH_PHILOSOPHY.md` §1).
- **Où on en est : l'Étape C (enveloppe) est close.** La stratégie cœur, **RE-1**, est :
  - **fonctionnelle** ;
  - **relativement performante, sans aucune optimisation numérique** : sur BTC/USD 30 min 2020-2025, +0,369 ATR par trade [+0,098 ; +0,645] net de 5 bps, +138 % à 0,25 % du capital par ATR, drawdown −13,5 %, Calmar 1,16, 6 années positives sur 6 ;
  - **figée** : aucun paramètre ne bouge plus.
- **Direction du projet (décision du porteur) :**
  - **D01 — portabilité sans optimisation.** Appliquer RE-1 telle quelle à d'autres actifs. Si elle tient, cela valide la stratégie elle-même.
  - **D02 — optimisation** (Optuna, walk-forward). Elle mesurera le gain de performance dû à l'optimisation, par rapport à RE-1 figée.
  - Puis la **validation finale** sur le hold-out, scellé jusqu'à la fin de l'Étape D.
- **Ta première tâche :** comprendre le projet, puis cadrer D01 avec le porteur (§8). **Ne lance aucun calcul avant son GO.**

---

## 1. Le porteur et la façon de travailler

**Le porteur.** Aymeric écrit en français. Il travaille en quant.
- **Réponses attendues :** denses, factuelles, sans flatterie.
- **Balises systématiques :** `[CODE]` (programmé, vérifiable), `[OBS]` (mesuré), `[HYP]` (explication proposée), `[DECISION]`.
- **Ses prompts :** des textes longs collés, qui contiennent le plan de l'expérience. Il y intègre parfois l'analyse d'une autre IA (Gemini).

**Vérifier ses chiffres avant de les consigner.** Ses relectures contiennent parfois des écarts. Il faut recalculer, consigner la valeur vérifiée et signaler l'écart. Exemples :
- 501e signal au 9 juin 2020, et non au 18 mai ;
- 59 signaux F3 contraires, et non 61 ;
- « les trades contre-tendance sont l'alpha majeur de la queue droite » : ils portent en réalité leur part, proportionnelle à leur poids.

**Pour chaque expérience :**
1. **Cadrage obligatoire en 4 champs**, avant tout test (`RESEARCH_PHILOSOPHY.md` §4.6) : QUESTION / PERTINENCE POUR LE FILTRE AKF / CE QUE LE PROTOCOLE MESURE RÉELLEMENT / CE QU'IL NE PERMET PAS DE CONCLURE.
2. **Règle de décision ou de lecture écrite avant le calcul.** Elle figure dans l'en-tête du script et dans le narratif.
3. **Code de calcul nouveau :** un module `src/` avec ses tests `pytest`, dans un **commit séparé** de l'analyse scientifique.
4. **Script** `experiments/<ID>/run_<ID>.py`, lancé depuis la racine :
   - contrôles bloquants d'abord (`SystemExit` en cas d'écart) ;
   - puis résultats CSV et JSON, et figures.
5. **Rapport :** `narratif_<ID>.md` rédigé à la main, puis `rapport_<ID>.md` = narratif + annexes chiffrées générées (`python experiments/<ID>/run_<ID>.py --rapport` régénère le rapport sans recalcul).
6. **Documentation à jour :**
   - entrée `RESEARCH_LOG.md` au modèle standard (en tête de fichier) ;
   - `RESEARCH_INSIGHTS.md`, `BEST_RESULTS.md`, et le tableau d'avancement de `PROJECT_PLAN.md`.
7. **Commit(s) local(aux)**, compte rendu au porteur (8 métriques, balises, décision proposée), et **push seulement sur son accord explicite**.
8. **Aucune expérience suivante sans GO explicite.**

**Tableau standard obligatoire à 8 métriques** (`CLAUDE.md` §2), pour chaque test :
- PnL net (composé et bps) ;
- Profit Factor ;
- Win Rate ;
- espérance (bps et ATR) ;
- Max Drawdown ;
- nombre de trades et cadence ;
- durée médiane ;
- part des frais.

---

## 2. Règles non négociables (gouvernance)

Sources : `CLAUDE.md` et les consignes du porteur. Elles priment sur toute autre considération.

- **Périmètre d'écriture :** `C:\Users\poek9\Projet Claude\#KalmanFilter` seulement.
  - Tous les autres dossiers (`#KAKALMAN`, `Kalman`, `NewKalman`, `Kalman FTMO`, `Kalman FTMO 2`, `Stratégie Bot Kalman Filter`, etc.) sont **strictement en lecture seule** : ne jamais modifier, supprimer, renommer ni déplacer.
  - Copier un fichier depuis ces dossiers vers `#KalmanFilter` demande l'accord du porteur. C'est ainsi qu'ont été faites les « copies certifiées » 46bb722 et 19a5990.
- **Baseline Pine gelée :** `pine/baseline/AKF_TSO_v2.1_baseline.pine`, empreinte SHA-256 dans `src/config.py`.
- **Moteur de parité sanctuarisé :** `src/indicator/`, conforme au Pine à 10⁻¹⁰ près (5,2·10⁻¹⁰ sur 117 584 barres). **Ne jamais réécrire le calcul du Kalman.**
- **Hold-out scellé :**
  - **ETH et XRP : n'y touche sous aucun prétexte**, pas même pour ouvrir leurs fichiers ;
  - **BTC 2026 :** tous les chargeurs tronquent avant le 2026-01-01 (`estimand.bars.check_no_holdout`, `anatomy.DEV_END`).
- **Aucun backtest sur TradingView.**
- **Git :**
  - commits locaux propres ;
  - **aucun push sans autorisation formelle.** Le dépôt GitHub est PUBLIC : pousser, c'est publier ;
  - ne supprimer, renommer ni déplacer aucun ancien dossier de travail.
- **Calcul :** aucun calcul lourd, aucun balayage combinatoire géant, aucune optimisation sans avoir présenté un plan succinct et obtenu une validation humaine explicite.
- **Méthode :**
  - un facteur à la fois (OFAT) ;
  - pas d'optimisation conjointe ;
  - pas de sélection a posteriori du meilleur point ;
  - toute modification de code ou d'architecture est séparée de l'analyse scientifique.
- **Frais dès la première barre :** 5 et 10 bps aller-retour sur crypto, présentés séparément ; 4 bps sur actions et ETF. Aucune décision sur un résultat brut.
- **Zéro machine learning :** ni XGBoost, ni régression logistique, ni méta-labeling.
- **Tests :** tout module de calcul nouveau a ses tests `pytest`, qui vérifient :
  - la non-régression ;
  - l'absence de lookahead (`shift(-1)` interdit) ;
  - la causalité, par des tests de troncature.
- **Hors périmètre :** le dossier parent `Projet Claude` contient d'autres projets et des fichiers personnels sans rapport avec AKF-TSO. Ne pas les ouvrir.

---

## 3. Dépôt, GitHub, environnement

| Élément | Valeur |
|---|---|
| Dossier local | `C:\Users\poek9\Projet Claude\#KalmanFilter` (le `#` impose de mettre les chemins entre guillemets) |
| GitHub | https://github.com/PokiCodeLonggamma/kalman_filter — **public**, branche `main` |
| État au 2026-09-29 | `origin/main` = `f281bdf` (C05). Les commits locaux ultérieurs éventuels sont listés par `git log` |
| Identité git du dépôt | `PokiCodeLonggamma <250868839+PokiCodeLonggamma@users.noreply.github.com>` (préférée par le porteur ; seul le 1er commit `1ae82b8` est signé pokito95) |
| Push (Git Bash), **seulement après accord** | `GIT_TERMINAL_PROMPT=0 GCM_INTERACTIVE=never timeout 120 git push origin main` |
| Système | Windows 11 ; Git Bash et PowerShell ; application Claude Code de bureau |
| Python | 3.11.9 ; numpy 2.4.2 ; pandas 2.3.3 ; matplotlib (`pyproject.toml`) |
| Lancer un script | depuis la racine : `PYTHONIOENCODING=utf-8 python experiments/<ID>/run_<ID>.py` |
| Tests | `python -m pytest -q` → **200 réussis, 2 ignorés** au 2026-09-29 (97 s ; `pythonpath = src, experiments/p0`) |
| Données | `data/raw/bitstamp_btcusd_30m.csv` (ignoré par git) et son `.meta.json` versionné (SHA-256, heure d'extraction). BTC/USD Bitstamp 30 min du 2020-01-01 au 2026-09-15, 117 585 lignes ; le code tronque au 2025-12-31 23:30 UTC |
| Mémoire de l'assistant | `C:\Users\poek9\.claude\projects\C--Users-poek9-Projet-Claude--KalmanFilter\memory\` (`MEMORY.md` et ses fiches), chargée automatiquement dans ce projet |
| Audit de la Phase 0 | Artifact https://claude.ai/artifact/VL4Nv1tt1x5aSEGGXoJngz. Sa section « Phase 1 » (EXP-001/002) est **abandonnée** |

**Historique git** (les hashes figurent aussi dans `RESEARCH_LOG.md`) :

| Étape | Commits |
|---|---|
| Gouvernance et copie certifiée | `1ae82b8`, `f850f18`, `46bb722`, `19a5990` |
| A01 | `6a3ce87`, `50ded4f`, `94a83bb` |
| B01 | `a20e052`, `5d0639b` |
| C01 | `73da9cc`, `e583e70` |
| C02 | `11d81c2`, `899956a` |
| C02bis | `13e8ee4`, `2b6fed7` |
| C03 | `1348193`, `547af84`, `47a3262` |
| C04 | `eb8949f`, `1dba30c` |
| C05 | `f281bdf` |

**Pièges techniques rencontrés :**
- **Scripts longs :** les heredocs longs en Bash peuvent être tronqués ; écrire les fichiers avec les outils d'édition.
- **Sortie tamponnée :** la sortie d'un script Python lancé en arrière-plan n'apparaît qu'à la fin.
- **Avertissements git :** les avertissements CRLF sont bénins (`.gitattributes`).
- **Contrôle d'autorisation :** en mode auto, il peut échouer par intermittence. Il suffit de réessayer plus tard.
- **`src/config.py` :** c'est une copie de `#KAKALMAN`. Il contient des constantes des phases ML historiques et renvoie à des `docs/` qui sont dans `#KAKALMAN`. Ne pas le « nettoyer » : les tests en dépendent.

---

## 4. Carte du dépôt et ordre de lecture

**Ordre de lecture recommandé :**
1. `CLAUDE.md` — instructions opérationnelles (chargé automatiquement).
2. `RESEARCH_PHILOSOPHY.md` — hypothèse directrice (§1), grille d'analyse (§4), cadrage obligatoire (§4.6).
3. `PROJECT_PLAN.md` — feuille de route A → D, tableau d'avancement, phases 5 à 7 (optimisation, transfert, validation finale).
4. `BEST_RESULTS.md` — la **fiche de RE-1** en tête, les meilleurs résultats de chaque étape, les pistes écartées.
5. `RESEARCH_INSIGHTS.md` — leçons de méthode I-M1 à I-M12, cinématique du moteur K1-K6, phénomènes P1-P3, régimes R1-R3, questions ouvertes (§5).
6. `RESEARCH_LOG.md` — journal complet, de la Phase 0 à C05, avec chaque décision du porteur.
7. `experiments/C02bis/rapport_C02bis.md` (naissance de RE-1) et `experiments/C05/rapport_C05.md` (sensibilité).
8. Le code (ci-dessous), puis un script récent de bout en bout : `experiments/C05/run_C05.py`.

**Code (`src/`) :**

| Module | Rôle | Statut |
|---|---|---|
| `indicator/` (`kalman.py`, `trend_strength.py`, `segments.py`, `_bounds.py`) | Réplique certifiée du Pine v2.1 : Kalman, oscillateur, zones et signaux | **Sanctuarisé, ne pas modifier** |
| `features/` (`kalman_intrinsic.py`, `multi_tf.py`) | Descripteurs du moteur (`nis_z_100`, segments…) et features 1 h | Copie certifiée de `#KAKALMAN` |
| `estimand/` (`bars.py`, `stoploss.py`, `excursions.py`) | Chargement BTC tronqué, garde hold-out, exécution des stops, courbes de capital, drawdowns | Copie certifiée |
| `labeling/costs.py`, `utils/data_loader.py`, `config.py` | Modèle de coût, chargeur OHLC avec contrôle SHA-256, constantes | Copies certifiées |
| `anatomy/` | A01 : `load_dev_bars`, `build_atlas` (7 296 signaux BTC 2020-2025), colonnes causales et a posteriori | Projet |
| `categorization/` | B01 : `add_derived` (`retrace_ratio`), `assign_families` (F1-F5), `bin_descriptor`, `causal_threshold`, bootstrap par grappes | Projet |
| `envelope/` | C : `stops.py` (SL-A, SL-B, `route_levels`, `stop_trades`, `breakeven_trades`), `metrics.py` (8 métriques, IC par grappes, effet apparié, capital dimensionné), `sequential.py` | Projet |
| `context/` | C04 : tendances EMA et Kalman 4 h, veto contre-tendance. Filtre rejeté, gardé pour mémoire | Projet |

**Autres dossiers :**

| Dossier | Contenu |
|---|---|
| `tests/` | 14 fichiers de tests et `conftest.py` : parité, indicateur, features, anatomie, catégorisation, enveloppe, contexte… ; `fixtures/` = fenêtre de données TradingView pour la parité |
| `experiments/p0/` | Oracle de parité `akf_replique_pine.py` (**ne jamais modifier**) |
| `experiments/p6_5/` | Trades de référence de l'ancre P6.5d (6 037 trades sans stop, 6 589 avec un stop de 2,5 %), contrôle bloquant de chaque script C |
| `experiments/A01` … `C05` | Une expérience par dossier : `run_*.py`, `narratif_*.md`, `rapport_*.md`, CSV, JSON de contrôles, `figures/` |
| `pine/baseline/` | Baseline Pine gelée |

**Chaîne de réutilisation des scripts.** Les scripts C s'importent entre eux par `importlib` : C05 → `C03/run_C03_approfondi.py` → `C03/run_C03.py` → `C02bis/run_C02bis.py`.
- Fonctions utiles :
  - dans C02bis : `full_masks`, `Engine`, `metrics` (8 métriques et Calmar), `check_anchor`, `row8` ;
  - dans C03 : `sized_returns`, `mdd_exits` ;
  - dans C03 approfondi : `sized_path`, `size_matched` ;
  - dans C04 : `paired_paths` ;
  - dans C05 : la classe `Sens`, RE-1 paramétrée.
- **Attention :** ces scripts contiennent des contrôles propres à BTC (effectifs attendus, familles comparées au CSV de B01, ancre P6.5d). Ils ne sont pas réutilisables tels quels sur un autre actif (§8).

---

## 5. Historique : de la Phase 0 à C05

| Étape | Expérience | Résultat principal | Décision |
|---|---|---|---|
| Phase 0 (audit) | Archives, `#KAKALMAN` | Moteur v2.1 certifié. La mécanique native (stop-and-reverse, 5 bps) fait −98,7 % : 6 037 trades, −5,3 bps par trade, frais ≈ 30 200 bps pour un brut de −2 047 bps. Les chiffres des archives (Pine V2, variantes du moteur) ne sont pas transposables | Recadrage du 2026-09-27 : feuille de route A → D ; aucun test « signal contre hasard » |
| A — Anatomie | A01 | Géométrie du signal stationnaire en ATR14(t). Le déclencheur arrive environ 5 barres après l'extremum et mêle retournement et décélération ; x1 est déjà retourné dans 51,8 % des cas | Tout s'exprime en ATR14(t) |
| B — Catégorisation | B01 et relecture | Trois régimes : R1 essoufflement (x1 encore opposé), R2 sortie de range (F2b ou F3, x1 déjà retourné, queue droite), R3 continuation. `nis_z_100` Q4 = continuation | R3 et Q4 = filtres d'exclusion |
| C — Enveloppe | C01 | Sortie à horizon fixe ; F2b · x1 hors Q4 à H26 : +0,389 ATR [+0,079 ; +0,700] | Continuation écartée définitivement |
| | C02 | F2b : tout stop dégrade. F3 : stop à l'extremum, drawdown −34 % → −13 %. R1, F1, F5 : aucune espérance nette | x1 retourné = prérequis d'entrée |
| | C02bis | Moteur de régimes **RE-1** : même espérance que R2 uniforme, drawdown −20,5 % → −13,5 %. Plateau H20-32 ; tient avec des seuils causaux ; le cooldown bat la réouverture | **RE-1 validé**, H = 26 verrouillé, take-profit exclu |
| | C03 | Break-even différé : aucun alpha. Comme outil de risque, il équivaut à réduire la taille ; perdu dès 5 bps de glissement | Rejeté |
| | C04 | Filtre de tendance macro (EMA 200, EMA 50, Kalman 4 h) : les trades contre-tendance ne sont pas toxiques ; le veto dégrade tout | Rejeté, RE-1 reste pur |
| | C05 | Sensibilité, un seuil à la fois : plateaux pour la frontière F2b / F3 (0,85-0,95) et la marge du stop (±0,25 ATR). L'exclusion de `nis_z_100` est une falaise côté permissif | RE-1 inchangé ; falaise signalée avant D |

Les pistes écartées, « à ne pas retester sans élément nouveau », sont dans le tableau final de `BEST_RESULTS.md`.

---

## 6. La stratégie cœur RE-1 (figée)

### 6.1 Définition exacte

- **Signal :** déclencheur natif AKF-TSO v2.1 (`indicator`) sur barres de 30 min. Warm-up : 300 barres de 30 min et 300 bougies 1 h.
  - Paramètres par défaut du Kalman (`KalmanParams`) : R0 = 100, q1 = q2 = 0,01, q_scale = 1, γ = 0,5, vol_lookback = 20.
  - Oscillateur : N2 = 5, R2 = 3.
  - L'atlas BTC 2020-2025 compte 7 296 signaux.
- **Univers (R2 hors `nis_z_100` Q4) :**
  - jambe précédente courte : `leg_atr` < médiane de l'atlas, soit **2,8233 ATR** sur BTC ;
  - `retrace_ratio` = `obs_dist_seg_atr` / `leg_atr` ≥ 0,50 ;
  - x1 déjà retourné à t (`x1_already_flipped_at_t`) ;
  - `nis_z_100` ≤ P75 de l'atlas (quantile linéaire), soit **1,2245** sur BTC ;
  - sur BTC : 1 874 signaux R2, dont 1 452 hors Q4 (F2b 741, F3 711).
- **Routage, connu à t :**
  - **F2b** (0,50 ≤ `retrace_ratio` < 0,85) : **sans stop** ;
  - **F3** (`retrace_ratio` ≥ 0,85) : **stop SL-B à l'extremum** du segment [t − `prev_seg_len`, t]. C'est le plus bas des `low` pour un Long, le plus haut des `high` pour un Short, avec δ = 0. Il n'est jamais à moins de 0,25 ATR14(t) de l'entrée.
- **Exécution :**
  - entrée à open[t + 1] ;
  - sortie à open[t + 1 + H], **H = 26** barres (13 h) ;
  - stop testé en intrabarre sur [t + 1, t + H] ; sortie au niveau du stop, ou à l'ouverture en cas de gap au-delà.
- **Séquencement :**
  - une position à la fois (pyramiding 0) : un signal reçu en position est ignoré ;
  - **cooldown** : après un stop, on reste à plat jusqu'à t + 1 + H. Les entrées sont donc celles de la course sans stop (`stop_trades(..., dynamic=False)`).
- **Frais :** 5 et 10 bps aller-retour par trade, déduits du rendement brut.
- **Capital :**
  - 0,25 % du capital par ATR14(t) (poids = min(1, 25 bps / ATR14 en bps), levier ≤ 1x) ;
  - le notionnel 1x sert de référence.
- **Mesures :**
  - IC 95 % par bootstrap de grappes de mois d'entrée, 2 000 tirages ;
  - Calmar = PnL annualisé / |MDD valorisé| ;
  - effets appariés sur les mêmes entrées (I-M9) ;
  - MDD lu comme une statistique de chemin (I-M10) ;
  - comparaison à RE-1 réduit au même MDD (I-M11).
- **Code de référence :**
  - `experiments/C02bis/run_C02bis.py` (`Engine.run("R2", {"F2b": None, "F3": ("SL-B", 0.0)}, 26, False)`) ;
  - `experiments/C05/run_C05.py` (`Sens.run()`), identique trade par trade.

### 6.2 Fiche de performance (BTC/USD 30 min, 2020-2025, H26)

| Métrique | 5 bps | 10 bps |
|---|---|---|
| PnL net : 0,25 %/ATR ; 1x ; bps cumulés (1x) | +138 % ; +204 % ; +13 320 | +72 % ; +77 % ; +7 920 |
| Profit Factor (1x ; pondéré) | 1,20 ; 1,28 | 1,11 ; 1,17 |
| Win Rate | 44,3 % | 42,8 % |
| Espérance ATR [IC] | +0,369 [+0,098 ; +0,645] | +0,233 [−0,041 ; +0,511] |
| Espérance bps [IC] | +12,3 [+0,2 ; +24,4] | +7,3 [−4,8 ; +19,4] |
| Max Drawdown : 0,25 %/ATR ; 1x | −13,5 % ; −43,9 % | −15,9 % ; −48,0 % |
| Trades | 1 080 (15,0 par mois), dont 24 % stoppés | idem |
| Durée médiane | 26 barres (13 h) | idem |
| Part des frais (1x) ; brut par trade | 29 % ; +17,3 bps | 58 % ; +17,3 bps |
| Années positives | 6 sur 6 | 5 sur 6 (2021) |
| Calmar (annualisé) | 1,16 (+15,6 % par an) | 0,60 (+9,5 % par an) |

Par sous-famille, à 5 bps : F2b 573 trades, +0,459 ATR ; F3 507 trades, +0,267 ATR.

### 6.3 Ce que « sans optimisation » veut dire, et ses limites

- **Aucune optimisation numérique :** ni Optuna, ni recherche de maximum.
  - Les seuils 0,50 et 0,85 de `retrace_ratio` sont physiques, fixés en B01 avant tout calcul.
  - P75 est une convention de quartile, la médiane de `leg_atr` aussi, et δ = 0 est l'extremum lui-même.
  - H = 26 a été retenu sur un plateau (IC > 0 de H20 à H32).
- **Mais plusieurs choix ont été faits après lecture de BTC 2020-2025 :**
  - l'exclusion de Q4 (après C01) ;
  - la règle de F3 (après C02) ;
  - H = 26 dans une grille d'horizons.

  D'où l'importance de D01.
- **Points faibles connus :**
  - à 10 bps, l'IC en ATR contient 0 ;
  - l'IC en bps n'est positif qu'avec la période janvier-juin 2020 ;
  - 2021 est l'année faible ;
  - l'exclusion de `nis_z_100` est le seul seuil sensible (C05) : relâchée à P80, −0,059 ATR, significatif ;
  - un seul actif, dans l'échantillon.

---

## 7. Problèmes rencontrés et leçons

**Données et hold-out**
- **Le hold-out n'est pas vierge.** ETH et XRP ont déjà été vus par l'ancien projet *Kalman* et les « Labos 2-3 » ; la réserve BTC 2026 a aussi été vue. La validation finale devra être lue avec cette réserve.
- **Seul BTC/USD 30 min est dans le dépôt.** Les données multi-actifs restent à constituer (§8).

**Méthode** (`RESEARCH_INSIGHTS.md` §1)
- **I-M9 :** une règle de sortie se juge d'abord par effet apparié, sur les mêmes entrées.
- **I-M10 :** le drawdown est une statistique de chemin. On lit une plage de chemins réordonnés, pas un IC.
- **I-M11 :** une règle de risque se juge contre une simple réduction de taille, à MDD égal.
- **I-M12 :** la sensibilité d'un seuil se lit par bandes marginales. Le rang du contrôle dans sa grille indique s'il a pu être calé sur la courbe.
- **I-M5, I-M6 et I-M8 :** lire la médiane, la moyenne et les queues ; donner les IC en bps **et** en ATR.
- **Espérance portée par la queue droite.** Le décile supérieur apporte 0,92 ATR par trade, plus que l'espérance totale : toute règle qui coupe les gagnants extrêmes (break-even, take-profit, veto) détruit l'espérance.
- **Les signaux qui tombent pendant la fenêtre d'un signal précédent perdent**, pris ou non : c'est la raison du cooldown (C02bis, C04).

**Biais de sélection à garder en tête :** exclusion de Q4 décidée après C01 ; règle de F3 après C02 ; RE-1 est au sommet de la grille `nis_z_100` en C05 en partie pour cette raison.

**Techniques** (le détail est dans `RESEARCH_LOG.md`)

| Où | Problème | Correction |
|---|---|---|
| C02 | La fenêtre du SL-B a été prise sur [t − `prev_seg_len`, t], celle de `retrace_ratio`, et non sur la formule du cadrage | Écart signalé et conservé |
| C02bis | Annualisation des variantes à seuils causaux | 5,56 ans, du 501e signal (9 juin 2020) à fin 2025, et non 6 ans |
| C03 | Une plage de chemins réordonnés avait été appelée « IC » | Renommée « plage P2,5-P97,5 » |
| C04 | Avec warm-up = 0, une barre sans bougie 4 h close recevait une tendance | Tendance valide seulement après au moins une bougie close |
| C04 | Comparaison `Timestamp` / `datetime64` dans un test | Corrigée |
| Général | Relectures du porteur | Toujours recalculer (§1) |

---

## 8. Étape D : direction et chantier D01

### 8.1 Direction (porteur, 2026-09-29)

- **D01 — portabilité multi-actifs, sans optimisation.**
  - On applique RE-1 figée à d'autres actifs, sans réglage propre à chaque actif.
  - La réussite validerait la stratégie elle-même.
- **D02 — optimisation** (Optuna puis walk-forward, `PROJECT_PLAN.md` phase 5).
  - On mesure le gain de performance dû à l'optimisation, contre RE-1 figée comme référence.
- **Ensuite :** validation finale sur le hold-out (phase 7), sans nouvelle optimisation.

### 8.2 Ce qu'il faut cadrer avec le porteur avant tout code (D01)

**1. Les actifs.**
- Le plan (phase 6) cite BTC, SOL, SOXS et WTI ; la feuille de route évoque aussi « un indice ».
- ETH et XRP sont exclus : c'est le hold-out.
- Le porteur choisit.

**2. Les données (état au 2026-09-29).** Toutes les sources ci-dessous sont en lecture seule. Chacune devra être copiée dans `data/raw/` avec son `.meta.json` (SHA-256, heure d'extraction, source), avec l'accord du porteur.

| Source | Couverture | Utilisable pour D01 ? |
|---|---|---|
| `Kalman/DB/raw_sol_usd_1h.parquet` | SOL/USD **1 h**, 2020-08-15 → 2026-04-24, 49 871 lignes | En partie : 1 h et non 30 min ; source à établir |
| `Kalman FTMO 2/akf_pipeline/Datas pour ML (…)/SOL/BITSTAMP_SOLUSD, 30.csv` | SOL 30 min, **2025-01-01 → 2026-04-20** (export TradingView) | Trop court |
| `…/BNB/BITSTAMP_BNBUSD, 30.csv` | 2025-12-21 → 2026-04-19, barres souvent plates | Non |
| `NewKalman/data/raw/btc_usd_30m.parquet` | BTC 30 min, 2013-01-01 → 2026-08-24 | Test **temporel** possible sur BTC 2013-2019 (période non utilisée pour construire RE-1 ; source à établir) |
| `Kalman/DB/raw_btc_usd_1h.parquet` | BTC 1 h, 2012 → 2026-04 | Contrôle éventuel |
| SOXS, WTI | **Aucune donnée trouvée** | Source à décider par le porteur |

- **Téléchargement :** `#KAKALMAN/src/utils/download_ohlc.py` télécharge l'OHLC Bitstamp par l'API publique, sans clé, avec paramètre `pair` (ex. `solusd`). Il écrit le schéma attendu par `utils.data_loader.load_ohlc` et le `.meta.json`.
  - Le copier dans le dépôt demande l'accord du porteur.
  - **Tout téléchargement demande son autorisation explicite.**
- Les fichiers ETH et XRP de ces dossiers ne doivent jamais être ouverts.

**3. Le transfert des seuils** (décision de conception, à trancher avant le calcul) :
- (a) **Valeurs BTC transposées telles quelles.** Elles sont sans dimension : `leg_atr` en ATR (2,8233), `nis_z_100` en z-score (1,2245), `retrace_ratio` (0,50 / 0,85), δ en ATR.
- (b) **Même règle, calculée sur l'atlas de chaque actif :** médiane et P75 de l'échantillon de l'actif. C'est la définition littérale de RE-1, mais dans l'échantillon.
- (c) **Même règle en version causale**, P75 glissant ou expansif (`categorization.causal_threshold`). Elle a été validée sur BTC en C02bis (RE-4).

C05 recommande (b) ou (c), plus la publication, par actif, de l'espérance par bande de `nis_z_100`, pour vérifier que la bascule reste au voisinage de P75.

**4. Actifs non cotés 24 h sur 24** (SOXS, WTI) :
- H = 26 compté en barres enjambe les nuits et les week-ends ;
- l'ATR intègre les gaps, et le stop est exécuté à l'ouverture en cas de gap (déjà codé) ;
- frais de 4 bps sur actions et ETF ;
- le chargeur signale les trous sans les combler.

À cadrer.

**5. Critères de réussite, fixés avant le calcul.** Par exemple :
- espérance nette > 0 à 5 bps sur chaque actif, avec son IC ;
- aucun actif à espérance significativement négative ;
- profil de risque comparable ;
- F2b et F3 lus séparément ;
- stabilité annuelle.

Le porteur tranche. `CLAUDE.md` rappelle d'éviter les vetos dogmatiques : mesurer d'abord, arbitrer ensuite.

**6. Période :** 2020-2025 par défaut ; 2026 scellé pour tous les actifs (`check_no_holdout` s'applique partout).

### 8.3 Points techniques vérifiés dans le code (utiles pour D01)

- **Le déclencheur est invariant d'échelle :**
  - le gain du Kalman ne dépend que de Q, R et du rapport sans dimension `rv / av` (R_t = R0 · (rv/av)^γ) ; il ne dépend pas du niveau de prix ;
  - l'oscillateur vaut `trend_strength` = WMA(100 · x1 / max|x1| sur 5 barres) ;
  - les descripteurs de RE-1 sont en ATR14(t) ;
  - le NIS brut dépend de l'échelle de prix, mais `nis_z_100` est un z-score glissant sur 100 barres.

  À contrôler sur chaque actif avant tout PnL, comme en A01 : nombre de signaux, distributions de `leg_atr`, de `retrace_ratio` et de `nis_z_100`.
- **Code propre à BTC :**
  - `anatomy.load_dev_bars()` lit le CSV BTC de `config.DATA_RAW` ; `utils.data_loader.load_ohlc(path)` accepte un autre chemin, avec son `.meta.json` ;
  - `anatomy.build_atlas(df)` est générique : n'importe quel OHLC de 30 min.
- **Proposition d'architecture, à valider avec le porteur :**
  1. Un **commit de code séparé**, par exemple `src/strategy/re1.py`. Il implémente RE-1 figée pour n'importe quel actif : barres → atlas → masques → routage → trades → métriques. Ses tests :
     - **reproduction trade par trade des 1 080 trades BTC de RE-1** (contrôle bloquant de non-régression) ;
     - causalité par troncature ;
     - garde hold-out.
  2. Ensuite l'expérience `experiments/D01/`, sur chaque actif :
     - les 8 métriques à 5 et 10 bps ;
     - les années ;
     - F2b et F3 ;
     - les bandes de `nis_z_100` ;
     - les chemins et la taille.

     Aucune optimisation.

---

## 9. Dossiers externes (lecture seule)

Tous sont dans `C:\Users\poek9\Projet Claude\`.

| Dossier | Contenu utile | Statut |
|---|---|---|
| `#KAKALMAN` | Projet précédent : moteur certifié, parité P0-P2, features P3, labeling P4, essais ML P5-P6 (logistique, XGBoost ; non repris, zéro ML ici), audits P6.5, `docs/` (`decisions.md`, `P2_parite.md`, `P6_5d_stop_loss.md`…), `src/utils/download_ohlc.py`, données BTC | Source des copies certifiées ; lecture seule |
| `Kalman` | Ancien projet ; `DB/` : parquets 1 h (BTC, SOL, ETH) | Lecture seule ; **ETH à ne pas ouvrir** |
| `NewKalman` | Variante du moteur (règles de flip) ; BTC 30 min et 1 h depuis 2013 | Lecture seule ; chiffres non transposables |
| `Kalman FTMO 2` | `akf_pipeline/`, avec des exports TradingView multi-actifs (BTC, ETH, SOL, BNB ; 15 min à 1 jour) | Lecture seule ; réservoir d'hypothèses (`RESEARCH_PHILOSOPHY.md` §4.5.3) ; **ETH à ne pas ouvrir** |
| `Kalman FTMO` | Projet antérieur, aucune donnée de marché repérée | Lecture seule |
| `Stratégie Bot Kalman Filter` | `KalmanOpti/` : ancienne optimisation sur BTCUSDT 1 h (2018-2024) | Lecture seule |

---

## 10. Premier message attendu de la nouvelle session

Après avoir lu cette passation, les documents du §4 et le code :
1. Vérifier l'état : `git status`, `git log --oneline -5`, `python -m pytest -q` (attendu : 200 réussis, 2 ignorés).
2. Rendre au porteur un **compte rendu court** :
   - ta compréhension du projet et de RE-1 ;
   - les règles de gouvernance ;
   - la situation des données ;
   - la liste des décisions à prendre pour D01 (§8.2).
3. **Ne rien lancer, ne rien modifier, ne rien pousser** avant son GO sur le cadrage de D01.
