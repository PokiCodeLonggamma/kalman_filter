# PASSATION — AKF-TSO : clôture de D01 → Étape D02 (walk-forward, adaptation multi-actifs)

> **À lire en entier avant toute action.** Rédigée le 2026-10-01 par la session qui a mené D01 à D01.7. Elle remplace la
> passation du 2026-09-29 (fin de l'Étape C), conservée dans l'historique git (`4831a1c`).
>
> Tout ce qui est écrit ici a été vérifié dans le dépôt le jour de la rédaction. En cas de doute, le dépôt fait foi :
> `RESEARCH_LOG.md` pour l'historique et les décisions, `BEST_RESULTS.md` pour les chiffres, `RESEARCH_INSIGHTS.md`
> pour les enseignements.
>
> **Statut :** validé par le porteur le 2026-10-01. **Aucun calcul D02 n'est lancé** : la nouvelle session attend le
> cadrage de D02 par le porteur.

## Sommaire
0. En une minute
1. Le porteur et la façon de travailler
2. Gouvernance : règles non négociables et décisions du porteur
3. Historique synthétique : de la Phase 0 à D01.7
4. RE-1 : définition exacte et paramètres gelés
5. Étape D01 : résultats et enseignements
6. Bilan : validé, rejeté, laissé ouvert
7. Données et sources
8. Architecture du dépôt
9. Scripts importants et leur rôle
10. Méthodologie statistique
11. Règles anti-look-ahead et anti-data-mining
12. Erreurs méthodologiques et pièges à ne pas reproduire
13. Étape D02 : objectifs, espace d'optimisation, protocole WFO / OOS / hold-out, livrables
14. État exact du dépôt et des commits
15. Prochaines étapes concrètes et premier message attendu

---

## 0. En une minute

- **Projet :** AKF-TSO. Recherche en trading systématique autour du déclencheur de l'indicateur Pine *AKF-TSO v2.1*,
  un filtre de Kalman adaptatif à deux états (niveau, vitesse) suivi d'un oscillateur de tendance.
- **But :** une mécanique de trading simple, rentable après frais et robuste hors échantillon.
- **Démarche :** mesurer → caractériser → catégoriser → isoler → exploiter l'information cinématique du moteur
  (`RESEARCH_PHILOSOPHY.md` §1).
- **Stratégie cœur : RE-1**, construite aux Étapes A à C sur BTC/USD 30 min 2020-2025 et **figée**.
  - Net de 5 bps : +0,369 ATR par trade [+0,098 ; +0,645].
  - Capital : +138 % à 0,25 % du capital par ATR (+204 % à 1x) ; MDD −13,5 % (−43,9 % à 1x).
  - Calmar 1,16 ; 6 années positives sur 6.
- **D01, portabilité zero-shot : close** (décision du porteur, 2026-10-01).
  - RE-1 figée a été appliquée telle quelle à SOL, à l'or, à SPY, à XLE, à GBPJPY, à 5 CFD sur indices, à l'argent et à
    5 CFD sur ETF.
  - La géométrie des signaux se transpose partout ; la rente, non.
  - Aucun actif hors BTC n'a d'IC à borne basse positive au coût principal.
  - Le porteur juge SOL et l'or assez encourageants pour poursuivre (§2.3).
- **Étape suivante : D02, optimisation walk-forward et adaptation multi-actifs.**
  - Elle mesure ce qu'apportent l'optimisation et le recalibrage, contre RE-1 figée.
  - Espace d'optimisation : H et R0 (cadrage antérieur du porteur), le reste à trancher avec lui (§13).
- **Ta première tâche :** lire, vérifier l'état du dépôt, puis cadrer D02 avec le porteur (§15). **Ne lance aucun
  calcul avant son GO.**

---

## 1. Le porteur et la façon de travailler

**Le porteur.** Aymeric écrit en français et travaille en quant.
- **Réponses :** courtes, denses, factuelles, sans flatterie.
- **Balises systématiques :** `[CODE]` (programmé, vérifiable), `[OBS]` (mesuré), `[HYP]` (explication proposée),
  `[PISTE]` (suite possible), `[DECISION]`.
- **Ses prompts :** de longs textes collés qui contiennent le plan de l'expérience. Il y intègre parfois l'analyse d'une
  autre IA (Gemini, ChatGPT).
  - Un protocole écrit à la première personne du porteur vaut consigne.
  - Une analyse d'un tiers vaut avis, à discuter.
- **Ses postulats deviennent des décisions :** les consigner sans les rediscuter. Les faits contraires vont au §5 de
  `RESEARCH_PHILOSOPHY.md`.
- **Pas de test « signal brut contre hasard »** : il l'a rejeté le 2026-09-27 (biais de dérive et de bêta). On mesure de
  façon descriptive.

**Vérifier ses chiffres avant de les consigner.** Ses relectures contiennent parfois des écarts : recalculer, consigner
la valeur vérifiée et signaler l'écart. Exemples :
- 501e signal au 9 juin 2020, et non au 18 mai ;
- 59 signaux F3 contraires, et non 61 ;
- BTC à 10 bps : +7,33 bps [−4,83 ; +19,41], et non +7,5 [−4,7 ; +19,5].

**Pour chaque expérience :**
1. **Cadrage obligatoire en 4 champs**, avant tout test (`RESEARCH_PHILOSOPHY.md` §4.6) :
   - QUESTION ;
   - PERTINENCE POUR LE FILTRE AKF ;
   - CE QUE LE PROTOCOLE MESURE RÉELLEMENT ;
   - CE QU'IL NE PERMET PAS DE CONCLURE.
2. **Règle de décision ou de lecture écrite avant le calcul**, dans l'en-tête du script et dans le narratif.
3. **Code de calcul nouveau :** un module `src/` avec ses tests `pytest`, dans un **commit séparé** de l'analyse.
4. **Script** `experiments/<ID>/run_<ID>.py`, lancé depuis la racine :
   - contrôles bloquants d'abord, avec `SystemExit` en cas d'écart ;
   - puis résultats CSV et JSON, figures, rapport.
5. **Rapport :** `narratif_<ID>.md`, écrit à la main, puis `rapport_<ID>.md` = narratif + annexes générées.
   `python experiments/<ID>/run_<ID>.py --rapport` régénère le rapport sans recalcul.
6. **Documentation à jour :**
   - entrée `RESEARCH_LOG.md` au modèle standard : cadrage, hypothèse, règle, tableau des 8 métriques, analyse
     `[CODE]` / `[OBS]` / `[HYP]`, décision ;
   - `RESEARCH_INSIGHTS.md`, `BEST_RESULTS.md`, tableau d'avancement de `PROJECT_PLAN.md`.
7. **Commits locaux**, compte rendu au porteur (8 métriques, balises, décision proposée), puis **push seulement sur son
   accord explicite**, donné pour chaque push.
8. **Aucune expérience suivante sans GO explicite.**

**Tableau standard à 8 métriques** (`CLAUDE.md` §2), pour chaque test :
- PnL net composé et en bps ;
- Profit Factor ;
- Win Rate ;
- espérance en bps et en ATR ;
- Max Drawdown ;
- nombre de trades et cadence ;
- durée médiane ;
- part des frais.

**Exigence du porteur :** toujours le PnL composé et le MDD **à 1x à côté de 0,25 %/ATR**.

---

## 2. Gouvernance : règles non négociables et décisions du porteur

### 2.1 Règles (sources : `CLAUDE.md`, consignes du porteur)

- **Périmètre d'écriture :** `C:\Users\poek9\Projet Claude\#KalmanFilter` seulement.
  - Les autres dossiers (`#KAKALMAN`, `Kalman`, `NewKalman`, `Kalman FTMO`, `Kalman FTMO 2`,
    `Stratégie Bot Kalman Filter`, etc.) sont en **lecture seule stricte**.
  - Toute copie vers le dépôt demande l'accord du porteur.
  - Le dossier parent `Projet Claude` contient d'autres projets personnels : ne pas les ouvrir.
- **Baseline Pine gelée :** `pine/baseline/AKF_TSO_v2.1_baseline.pine` ; son empreinte SHA-256 est dans `src/config.py`.
- **Moteur de parité sanctuarisé :** `src/indicator/`, conforme au Pine à 10⁻¹⁰ près (5,2·10⁻¹⁰ sur 117 584 barres).
  **Ne jamais réécrire le calcul du Kalman.**
- **Hold-out :**
  - **ETH et XRP : n'y touche sous aucun prétexte**, pas même pour ouvrir leurs fichiers.
  - **2026, pour tous les actifs :** totalement hors échantillon. Ne jamais utiliser de donnée postérieure au
    2025-12-31 pour un test.
  - Les chargeurs tronquent avant le 2026-01-01 : `estimand.bars.check_no_holdout`, `anatomy.DEV_END`, `strategy.load_asset`.
  - Le client Saxo refuse toute requête ou barre de 2026 : `marketdata.saxo.check_window` et `get_chart`.
  - **Réserve :** le hold-out n'est pas vierge. ETH et XRP ont été vus par d'anciens projets (*Kalman*, « Labos 2-3 »),
    et BTC 2026 a aussi été vu.
- **Aucun backtest sur TradingView par l'agent.**
- **Git :**
  - commits locaux propres ;
  - **aucun push sans autorisation formelle** : le dépôt GitHub est **public**, pousser revient à publier ;
  - ne supprimer, renommer ni déplacer aucun ancien dossier de travail.
- **Calcul :** aucun calcul lourd, balayage combinatoire géant ni optimisation sans plan succinct présenté et validation
  humaine explicite.
- **Méthode :**
  - un facteur à la fois (OFAT) ;
  - pas d'optimisation conjointe non déclarée ;
  - pas de sélection a posteriori du meilleur point ;
  - code ou architecture séparés de l'analyse scientifique.
- **Frais dès la première barre :** 5 et 10 bps aller-retour sur crypto ; 4 bps sur actions, ETF et CFD par convention ;
  coûts de D01.7 au §5.4. Aucune décision sur un résultat brut.
- **Zéro machine learning :** ni XGBoost, ni régression logistique, ni méta-labeling.
- **Tests :** tout module de calcul nouveau a ses tests `pytest` : non-régression, absence de lookahead (`shift(-1)`
  interdit), causalité par troncature.
- **Secrets :**
  - ne jamais demander au porteur de poster une clé ou un jeton dans le chat ;
  - un secret se stocke uniquement dans une variable d'environnement ;
  - l'agent ne saisit jamais de mot de passe ni d'identifiant : le porteur se connecte lui-même ;
  - une clé ne se vérifie que par empreinte SHA-256, jamais affichée.
- **Sources de données :**
  - ne jamais compléter avec une autre source sans le signaler ;
  - ne jamais remplacer une source en silence par une donnée de qualité différente ;
  - un actif sans donnée conforme est **bloqué et documenté**, pas remplacé.
- **Abonnements :** ne jamais faire souscrire le porteur à un abonnement avant d'avoir établi que la donnée est déjà
  disponible.

### 2.2 Décisions structurantes du porteur (chronologie)

| Date | Décision |
|---|---|
| 2026-09-27 | Recadrage : feuille de route A → D, mesures descriptives, aucun test « signal contre hasard » |
| 2026-09-29 | RE-1 validée comme stratégie cœur de l'Étape C. H = 26 verrouillé, take-profit exclu, continuation écartée, R1/F1/F5 rejetés (x1 retourné = prérequis d'entrée) |
| 2026-09-29 | Direction de l'Étape D : D01 = portabilité sans optimisation (valide la stratégie) ; D02 = optimisation, qui mesure le gain dû à l'optimisation ; puis validation finale sur le hold-out |
| 2026-09-30 | D01 : transfert option (a), seuils BTC gelés ; D01 descriptif, sans critère de réussite ; SOL/USD et non SOL/USDT ; or et WTI en CFD (HistData) ; WTI retiré, remplacé par XLE, plus SPY |
| 2026-09-30 | D01.5 (H seul) et D01.6 (verrouillage, séance) insérées, descriptives |
| 2026-10-01 | D01.7 : portabilité zero-shot sur marchés quasi continus |
| 2026-10-01 | D01.7, sources : Saxo OpenAPI LIVE, futures et CFD continus abandonnés, univers redéfini, Japan 225 remplacé par HK50, ETF inclus, coûts validés, GBPJPY lu chez Saxo |
| 2026-10-01 | **Clôture officielle de D01 ; passage à D02** (WFO, adaptation multi-actifs) ; `passation.md` à relire avant toute expérience |

### 2.3 Clôture de D01 (porteur, 2026-10-01)

> « On clôture officiellement D01. Même si tous les actifs n'ont pas confirmé un avantage statistiquement établi, les
> premiers tests sur SOL et XAU ont été suffisamment encourageants pour justifier la poursuite du projet. D01 a surtout
> permis d'identifier les limites de RE-1 en zero-shot et de dégager les principaux axes d'adaptation pour la suite. »

**Faits à garder en tête, consignés au §5 de `RESEARCH_PHILOSOPHY.md` :**
- SOL/USD : +0,190 ATR [−0,079 ; +0,484] à 5 bps. Estimation positive, IC qui contient 0.
- Or : −0,019 ATR [−0,362 ; +0,349] à 4 bps. Brut de +0,24 ATR, absorbé par 0,26 ATR de frais.

---

## 3. Historique synthétique : de la Phase 0 à D01.7

| Étape | Expérience | Résultat principal | Décision |
|---|---|---|---|
| Phase 0 (audit) | Archives, `#KAKALMAN` | Moteur v2.1 certifié. La mécanique native (stop-and-reverse, 5 bps) fait −98,7 % (6 037 trades, −5,3 bps par trade). Les chiffres des archives ne sont pas transposables | Recadrage : A → D |
| A — Anatomie | A01 | Géométrie du signal stationnaire en ATR14(t). Le déclencheur arrive environ 5 barres après l'extremum ; x1 est déjà retourné dans 51,8 % des cas | Tout s'exprime en ATR14(t) |
| B — Catégorisation | B01 et relecture | Trois régimes : R1 essoufflement (x1 encore opposé), R2 sortie de range (F2b ou F3, x1 retourné, queue droite), R3 continuation ; `nis_z_100` Q4 = continuation | R3 et Q4 = filtres d'exclusion |
| C — Enveloppe | C01 | Sortie à horizon fixe : F2b · x1 hors Q4 à H26 +0,389 ATR | Continuation écartée |
| | C02 | F2b : tout stop dégrade ; F3 : stop à l'extremum (DD −34 % → −13 %) ; R1, F1, F5 sans espérance | x1 retourné obligatoire |
| | C02bis | **RE-1** : même espérance que R2 uniforme, DD −20,5 % → −13,5 % ; plateau H20-32 ; tient avec des seuils causaux ; le cooldown bat la réouverture | **RE-1 validée**, H = 26 verrouillé |
| | C03 | Break-even différé : aucun alpha ; outil de risque équivalent à une réduction de taille | Rejeté |
| | C04 | Filtre de tendance macro (EMA 200, EMA 50, Kalman 4 h) : le veto dégrade tout | Rejeté |
| | C05 | Sensibilité OFAT : plateaux pour la frontière F2b/F3 (0,85-0,95) et la marge du stop (±0,25 ATR) ; falaise de `nis_z_100` côté permissif | RE-1 inchangée |
| D — Adaptation | D01, D01 bis | Portabilité zero-shot : SOL +0,190 ATR ; or −0,019 ; SPY −0,158 ; XLE +0,020. La géométrie se transpose | RE-1 inchangée |
| | D01.5 | H seul (or 26-130, SPY/XLE 6-130) : aucun IC > 0 sur 15 configurations ; H déplace l'exposition, pas l'espérance | Aucun H retenu |
| | D01.6 | Verrouillage et séance (SPY/XLE) : aucune signature, aucun IC > 0 ; sortie de fin de séance : brut ≈ frais sur SPY | Rien retenu |
| | D01.7 | Partie 1 : GBPJPY HistData, brut nul. Partie 2 (Saxo) : 12 actifs, aucun IC > 0 au coût principal | D01 close |

Pistes écartées, à ne pas retester sans élément nouveau : tableau final de `BEST_RESULTS.md`.

---

## 4. RE-1 : définition exacte et paramètres gelés

### 4.1 Définition (code : `src/strategy/re1.py`, identique à C02bis trade par trade)

- **Signal :** déclencheur natif AKF-TSO v2.1 (`anatomy.build_atlas`, moteur certifié `src/indicator/`), sur barres de
  30 min.
  - Paramètres par défaut du Kalman : **R0 = 100**, q1 = q2 = 0,01, q_scale = 1, γ = 0,5, vol_lookback = 20.
  - Oscillateur : N2 = 5, R2 = 3.
  - Warm-up : 300 barres de 30 min et 300 bougies de 1 h.
- **Familles (B01, `categorization.assign_families`) :**
  - `retrace_ratio` = `obs_dist_seg_atr` / `leg_atr` ;
  - F2b : 0,50 ≤ `retrace_ratio` < 0,85 ; F3 : `retrace_ratio` ≥ 0,85 ;
  - R2 = (F2b | F3) avec **x1 déjà retourné** à t ;
  - R1 = (F1 | F5) avec x1 encore opposé ; R3 = (F1 avec x1 retourné) | F2a | F4.
- **Univers de RE-1 : R2 hors `nis_z_100` Q4.**
  - Jambe précédente courte : `leg_atr` < **2,823322693433984** (médiane de l'atlas BTC 2020-2025, gelée).
  - `nis_z_100` ≤ **1,2245041356145911** (P75 linéaire de l'atlas BTC, gelé) ; NaN exclu.
  - Sur BTC : 7 296 signaux, 1 452 candidats, **1 080 trades**.
- **Routage, connu à t :**
  - **F2b : sans stop** ;
  - **F3 : stop SL-B à l'extremum** du segment [t − `prev_seg_len`, t] : plus bas des `low` pour un Long, plus haut des
    `high` pour un Short, δ = 0. Le stop n'est jamais à moins de **0,25 ATR14(t)** (FLOOR) de open[t + 1].
- **Exécution :**
  - entrée à open[t + 1] ;
  - sortie à open[t + 1 + **H**], avec **H = 26 barres** de la série ;
  - stop testé en intrabarre sur [t + 1, t + H], exécuté au niveau du stop, ou à l'ouverture en cas de gap au-delà.
- **Séquencement :**
  - une position à la fois : un signal reçu en position est ignoré ;
  - **cooldown** après un stop jusqu'à t + 1 + H, via `stop_trades(..., dynamic=False)`.
- **Frais :** aller-retour par trade, déduits du rendement brut dès la première barre.
- **Capital :**
  - **0,25 % du capital par ATR14(t)** : poids = min(1, 25 bps / ATR14 en bps), levier ≤ 1x ;
  - le notionnel 1x sert de référence.

### 4.2 Paramètres gelés

| Paramètre | Valeur | Origine |
|---|---|---|
| R0 ; q1, q2 ; γ ; N2, R2 | 100 ; 0,01 ; 0,5 ; 5, 3 | réglages par défaut du Pine v2.1 |
| Seuil de `leg_atr` | 2,823322693433984 | médiane de l'atlas BTC 2020-2025 |
| Seuil de `nis_z_100` | 1,2245041356145911 | P75 de l'atlas BTC 2020-2025 |
| Bornes de `retrace_ratio` | 0,50 ; 0,85 | physiques, fixées en B01 |
| Stop de F3 | SL-B, δ = 0, plancher 0,25 ATR | C02 |
| H | 26 barres | C02bis (plateau H20-32), verrouillé |
| Risque | 25 bps par ATR14(t), plafond 1x | convention du porteur |

**Ce que « sans optimisation » veut dire :** aucune recherche numérique de maximum. Mais l'exclusion de Q4 (après C01),
la règle de F3 (après C02) et H = 26 (sur une grille) ont été décidés après lecture de BTC 2020-2025 : il y a un biais
de sélection connu.

### 4.3 Fiche de performance (BTC/USD 30 min, 2020-2025)

| Métrique | 5 bps | 10 bps |
|---|---|---|
| PnL net : 0,25 %/ATR ; 1x ; bps cumulés (1x) | +138 % ; +204 % ; +13 320 | +72 % ; +77 % ; +7 920 |
| Profit Factor : 1x ; pondéré | 1,20 ; 1,28 | 1,11 ; 1,17 |
| Win Rate | 44,3 % | 42,8 % |
| Espérance ATR [IC] ; bps [IC] | +0,369 [+0,098 ; +0,645] ; +12,3 [+0,2 ; +24,4] | +0,233 [−0,041 ; +0,511] ; +7,3 [−4,8 ; +19,4] |
| Max Drawdown : 0,25 %/ATR ; 1x | −13,5 % ; −43,9 % | −15,9 % ; −48,0 % |
| Trades | 1 080 (15,0 par mois), 24 % stoppés | idem |
| Durée médiane | 26 barres (13 h) | idem |
| Part des frais (1x) | 29 % | 58 % |
| Années positives ; Calmar (0,25 %/ATR) | 6/6 ; 1,16 | 5/6 ; 0,60 |

**Points faibles connus :**
- à 10 bps, l'IC en ATR contient 0 ;
- l'IC en bps n'est positif qu'avec janvier-juin 2020 ;
- 2021 est l'année faible ;
- l'exclusion de `nis_z_100` est le seul seuil sensible (C05) ;
- l'espérance est portée par la queue droite : le décile supérieur apporte +0,92 ATR par trade, la médiane est de
  −0,42 ATR.

---

## 5. Étape D01 : résultats et enseignements

### 5.1 D01 et D01 bis : portabilité zero-shot (seuils BTC gelés, option (a))

| | BTC 5 bps (réf.) | SOL/USD 5 bps | CFD or 4 bps | SPY 4 bps | XLE 4 bps |
|---|---|---|---|---|---|
| Période | 2020-2025 | 2021-06-17 → 2025 | 2020-2025 | 2020-2025, séance | 2020-2025, séance |
| Trades (par mois) | 1 080 (15,0) | 769 (14,1) | 651 (9,0) | 155 (2,2) | 136 (1,9) |
| Espérance ATR [IC] | +0,369 [+0,098 ; +0,645] | +0,190 [−0,079 ; +0,484] | −0,019 [−0,362 ; +0,349] | −0,158 [−0,736 ; +0,434] | +0,020 [−0,588 ; +0,674] |
| PnL : 0,25 %/ATR ; 1x | +138 % ; +204 % | +39 % ; +173 % | +0,6 % ; +5,4 % | −4,2 % ; −7,9 % | +0,1 % ; +7,2 % |
| MDD : 0,25 %/ATR ; 1x | −13,5 % ; −43,9 % | −13,1 % ; −42,3 % | −13,6 % ; −13,3 % | −10,9 % ; −19,2 % | −19,5 % ; −36,4 % |
| Brut ; frais (ATR par trade) | +0,50 ; 0,14 | +0,25 ; 0,06 | +0,24 ; 0,26 | 0,00 ; 0,16 | +0,10 ; 0,08 |

- La géométrie des signaux est identique sur la crypto et l'or (K7) ; jambes plus longues sur les ETF, à cause des gaps.
- **ETF :** le filtre `nis_z_100` écarte 64 à 74 % des signaux nés d'un gap. Mais H = 26 barres traverse deux nuits :
  les gaps pèsent 35 à 47 % de l'amplitude, et les stops percés dépassent leur niveau de +1,0 à +2,6 ATR (K8).

### 5.2 D01.5 : H seul (descriptive, 4 bps)

- Or : H ∈ {26, 48, 72, 96, 130} ; SPY et XLE : H ∈ {6, 13, 26, 65, 130}. **Aucun IC à borne basse > 0** sur 15
  configurations.
- Or : frais fixes en ATR (0,26 à tout H), brut non croissant, H = 26 meilleur point.
- SPY : H = 13 traverse encore une nuit (91 % des trades) ; H = 6 réduit l'exposition sans brut à protéger.
- XLE : pic à H = 65 (+0,155 ATR), porté par la population ; effet apparié −0,010.
- **K9 :** H déplace l'exposition et la dérive, pas l'espérance. **I-M16 :** une variation de H se lit sur entrées
  figées.

### 5.3 D01.6 : verrouillage et séance (SPY, XLE, exploratoire)

- Les 31 trades de XLE « sautés » à H = 65 valent +0,118 ATR avec la sortie de RE-1 : rien à filtrer.
- Verrouillage découplé de la sortie (H_exit 26, H_cooldown 26-90) : zigzag de calendrier, aucun IC > 0.
- Sortie forcée en fin de séance : brut +0,16 ATR sur SPY (≈ frais), −0,09 sur XLE ; MDD divisé par deux. La nuit aide
  XLE et pèse sur SPY (K10).

### 5.4 D01.7 : marchés quasi continus et CFD sur ETF

**Partie 1 :** GBPJPY de HistData. Brut −0,035 ATR ; −0,443 [−0,697 ; −0,180] à 4 bps ; frais 0,41 ATR.

**Accès aux données :**
- QuantConnect n'autorise aucun export ; le dépôt GitHub axb0306/cme-futures-ohlc a été jugé FAIL.
- Puis Saxo OpenAPI LIVE.
  - Ses séries continues (futures c1, CFD « cont ») sont brutes : le changement de contrat n'est pas ajusté.
  - Le WTI change de contrat le dernier jour de cotation, vers 11:00 heure de New York, au milieu d'une barre.
  - **Futures et CFD continus abandonnés par le porteur.**

**Partie 2 : univers du porteur, séries Saxo, coûts validés avant le calcul.** Le coût principal vaut le plus grand de
4 bps et du P90 de l'écart acheteur-vendeur, arrondi au point supérieur.

| Actif (coût) | Espérance ATR [IC] | Brut ; frais (ATR) | PnL : 0,25 %/ATR ; 1x | MDD : 0,25 %/ATR ; 1x | Trades | Années > 0 |
|---|---|---|---|---|---|---|
| US30 (4) | −0,004 [−0,350 ; +0,348] | +0,33 ; 0,33 | +11 % ; +29 % | −13,7 % ; −14,1 % | 710 | 2/6 |
| GER40 (4) | −0,005 [−0,292 ; +0,294] | +0,24 ; 0,24 | +0 % ; +5 % | −22,9 % ; −27,5 % | 545 | 2/6 |
| US100 (4) | −0,097 [−0,428 ; +0,252] | +0,14 ; 0,24 | −5 % ; −10 % | −19,7 % ; −27,0 % | 695 | 1/6 |
| HK50 (8) | −0,103 [−0,539 ; +0,334] | +0,19 ; 0,30 | −9 % ; −15 % | −32,3 % ; −41,9 % | 425 | 2/6 |
| GBPJPY (4) | −0,303 [−0,572 ; −0,031] | +0,10 ; 0,40 | −20 % ; −21 % | −22,0 % ; −22,1 % | 754 | 0/6 |
| XAGUSD (11) | −0,307 [−0,634 ; +0,006] | +0,06 ; 0,37 | −41 % ; −57 % | −43,5 % ; −59,7 % | 651 | 1/6 |
| EU50 (7) | −0,590 [−0,946 ; −0,214] | −0,17 ; 0,42 | −37 % ; −44 % | −40,6 % ; −47,8 % | 535 | 1/6 |
| GDX (4) | +0,349 [−0,365 ; +1,076] | +0,42 ; 0,07 | +12 % ; +70 % | −8,5 % ; −19,1 % | 143 | 5/6 |
| USO (4) | +0,148 [−0,553 ; +0,813] | +0,22 ; 0,07 | +4 % ; +65 % | −9,6 % ; −24,8 % | 140 | 2/6 |
| URA (4) | +0,093 [−0,823 ; +1,100] | +0,15 ; 0,06 | +2 % ; −18 % | −12,6 % ; −41,8 % | 127 | 2/6 |
| SMH (4) | −0,180 [−0,795 ; +0,409] | −0,11 ; 0,08 | −7 % ; −13 % | −15,5 % ; −30,4 % | 149 | 2/6 |
| TLT (4) | −0,205 [−0,972 ; +0,570] | −0,04 ; 0,16 | −9 % ; −11 % | −16,6 % ; −21,1 % | 157 | 2/6 |

- **Le coût en ATR tranche (K11, I-M14).**
  - Sur les CFD sur indices, l'argent et GBPJPY, l'ATR de 30 min vaut 11 à 34 bps : les frais (0,24 à 0,42 ATR)
    absorbent un brut de +0,06 à +0,33.
  - Sur BTC, 5 bps ne coûtent que 0,14 ATR, pour un brut de +0,50.
- **US30 :** brut positif des deux côtés (+0,44 et +0,20). C'est le seul IC en bps au-dessus de 0 en brut :
  +7,9 bps [+0,8 ; +16,0].
  - À son écart réel chez Saxo (1,4 bp) : +0,211 ATR [−0,136 ; +0,556].
  - GER40 n'est porté que par ses Longs, c'est-à-dire par la dérive du DAX.
- **ETF :** environ 140 trades chacun, 91 à 94 % exposés à une nuit. Le brut vient des gaps (GDX : +0,41 contre +0,02 en
  séance) ; on ne peut pas le distinguer du bruit.
- **GBPJPY Saxo** confirme la partie 1 : brut +0,095, −0,303 à 4 bps.
- **Contrôles :**
  - recoupements externes : US100 contre NASDAQ-100 0,9991, US30 contre Dow Jones 0,9994, GBPJPY contre H.10 0,9997 ;
    meilleur décalage 0 ;
  - aucun changement de contrat caché dans les CFD sur indice ;
  - quatre fermetures de bourse admises, déclarées avant le calcul.
- **Indication donnée au porteur, hors protocole :** SMH en 2025 seul (RE-1, 4 bps) : 31 trades, +5,5 % à 1x, +3,3 % à
  0,25 %/ATR ; MDD −4,7 % à 0,25 %/ATR, −13,5 % à 1x ; l'ETF a pris +47,3 % sur l'année. 2026 n'a pas été calculé
  (réserve).

### 5.5 Enseignements transversaux de D01

- **La population transfère, la rente dépend du marché :**
  - géométrie identique en ATR (K7, K7 bis, K11) ;
  - brut faible hors crypto ;
  - frais en ATR décisifs (I-M14).
- **Séances et nuits :** sur un actif de séance, un horizon en barres mêle cinématique de séance et risque de nuit
  (K8 à K10). Sortir avant la nuit ne crée pas d'espérance (K10).
- **H :** aucun H alternatif n'apporte d'espérance en zero-shot (K9).
- **Queues :** partout, médiane négative et décile supérieur qui porte tout. C'est le profil de BTC, sans la moyenne
  positive hors BTC et SOL.
- **Axes d'adaptation pour D02**, d'après le porteur et les mesures :
  - réactivité du filtre (R0) ;
  - horizon (H) ;
  - transfert des seuils de population ;
  - coût d'exécution par marché ;
  - horizon en temps sur les actifs de séance.

---

## 6. Bilan : validé, rejeté, laissé ouvert

**Validé (décisions du porteur) :**
- moteur v2.1 certifié ;
- expression en ATR14(t) ;
- régimes R1-R3 ;
- **RE-1** comme stratégie cœur figée (F2b sans stop, F3 SL-B, cooldown, H = 26) ;
- conventions de capital et de frais ;
- clôture de D01.

**Rejeté (tableau « Pistes écartées » de `BEST_RESULTS.md`) :**
- stop-and-reverse natif ;
- horizon fixe sur tous les signaux ;
- continuation (R3, Q4) ;
- R1/F1/F5 ;
- stop sur F2b ;
- stop de catastrophe RE-3 ;
- réouverture immédiate ;
- H par sous-famille ;
- take-profit fixe ;
- break-even, comme alpha et comme outil de risque ;
- veto contre-tendance ;
- frontière F2b/F3 abaissée ;
- exclusion de `nis_z_100` relâchée.

En D01 :
- futures continus non ajustés (Saxo, GitHub) ;
- WTI HistData (couverture et contrat du mois) ;
- NLR (sélection par erreur, illiquide) ;
- Japan 225 (absent chez Saxo).

**Laissé ouvert :**
- **D02 entier (§13).**
- Transfert des seuils de population hors BTC : option (a) gelée, option (b) quantiles par actif, option (c) quantiles
  causaux. Seule (a) a été testée.
- Coût réel d'exécution chez Saxo (écart, commission des CFD sur ETF, financement de nuit). Il décide pour US30, US100
  et GER40.
- Sur les actifs de séance, H en barres ou en temps (question 15 de `RESEARCH_INSIGHTS.md`).
- Seuils de population quand R0 ≠ 100 : leur sens change avec la réactivité du filtre.
- Demande SMH de janvier 2025 au 30 septembre 2026 (comparaison avec un backtest TradingView du Pine) :
  - 2025 a été donné ;
  - **2026 n'a pas été calculé**, car c'est la réserve ; il faut une décision explicite du porteur ;
  - une comparaison à périmètre égal sur 2025 a été proposée : même stratégie de retournement rejouée en Python.
- Questions ouvertes de `RESEARCH_INSIGHTS.md` §5.

---

## 7. Données et sources

Les CSV sont dans `data/raw/` et ignorés par git. Leurs `.meta.json` sont versionnés : source, SHA-256, heure
d'extraction, couverture, construction. Tous les chargements tronquent avant le 2026-01-01.

| Série (fichier) | Source | Nature | Usage |
|---|---|---|---|
| `bitstamp_btcusd_30m.csv` | Bitstamp, API publique | BTC/USD spot 30 min (fichier jusqu'au 2026-09-15, tronqué) | Construction de RE-1 (A → C), référence |
| `bitstamp_btcusd_30m_2013_2025.csv` | Bitstamp, API publique (`src/marketdata/bitstamp.py`) | BTC/USD spot 30 min 2013-2025 ; identique à la série ci-dessus sur 2020-2025 ; panne du 5 au 9 janvier 2015 (barres plates) | D02.0 (rétro-test 2013-2019), D02 |
| `coinbase_solusd_30m.csv` | Coinbase, bougies de 15 min agrégées | SOL/USD dès 2021-06-17 | D01 |
| `coinbase_avaxusd_30m.csv` | Coinbase, bougies de 15 min agrégées | AVAX/USD dès 2021-09-30 | Univers de D02 (porteur) |
| `histdata_xauusd_30m.csv` | HistData M1 (bid) | CFD or ; horloge EET/EEST − 7 h corrigée | D01, D01.5 |
| `histdata_xauusd_30m_2009_2025.csv` | HistData M1 (bid) | CFD or 2009-03-15 → 2025 ; identique à la série de D01 sur 2020-2025 ; pause de 17:00 New York en partie cotée en 2009-2018 | D02.0, D02 |
| `histdata_wtiusd_30m.csv` | HistData M1 | CFD WTI, contrat du mois, arrêté au 2023-12-01 | Retiré (audit seul) |
| `alpaca_spy_30m.csv`, `alpaca_xle_30m.csv` (+ `_brut`) | Alpaca SIP, téléchargés par le porteur | ETF en séance régulière, séries ajustée et brute | D01 bis, D01.5, D01.6 |
| `histdata_gbpjpy_30m.csv` | HistData M1 (bid) | GBPJPY ; trous en 2023 (14 %) | D01.7, partie 1 |
| `saxo_<clé>_30m.csv` (+ `_brut`, `_test`) | Saxo OpenAPI LIVE (compte du porteur) | US30, GER40, EU50, HK50 (CfdOnIndex, bid) ; XAGUSD, GBPJPY (FxSpot, bid) ; ETF TLT, USO, SMH, URA, GDX (CfdOnEtf, prix traités, séance) | D01.7, partie 2 |
| `saxo_us100_cfd_30m.csv` | Saxo | USNAS100.I, CFD sur l'indice au comptant | D01.7 |
| `saxo_{us100,us2000,usoil,copper}_{cfd,fut}_30m.csv` | Saxo | Séries continues non ajustées | Abandonnées (audit) |
| `saxo_etf_nlr_30m.csv` | Saxo | NLR, sélectionné par erreur | Inutilisable, conservé déclaré |
| `fred_*.csv` | FRED | DCOILWTICO, DEXUSUK, DEXJPUS, NASDAQ100, DJIA | Recoupements externes |

**Accès à Saxo, pour une nouvelle session :**
1. La clé de l'application LIVE « AKF-TSOD017-LIVE » (PKCE, trading non activé) est dans la variable d'environnement
   utilisateur `SAXO_APP_KEY`. Elle n'est jamais affichée ; son préfixe d'empreinte est consigné dans la mémoire de
   l'assistant (la clé SIM a une autre empreinte).
2. Lancer `python experiments/D01_7/saxo_univers_D01_7.py`. Le script ouvre http://localhost:47321/start, que l'on
   ouvre dans le navigateur intégré ; **le porteur se connecte lui-même.**
3. Le jeton reste en mémoire du processus seulement (20 min, rafraîchi).
4. Les données de marché via l'API sont activées dans SaxoTrader (Profil → Autres → Accès Open API). Sans cela,
   les requêtes répondent 403.
5. Chaque nouvelle série demande une connexion.

**Pièges de données connus :**
- clôtures anticipées du NYSE à 13:00 ;
- split 2:1 de XLE (2025-12-05), neutralisé par la série ajustée ;
- CFD sur indices US cotés jusqu'à 16:00 heure de New York avant 2022, puis jusqu'à 17:00 ;
- ETF chez Saxo : ajustés des splits, pas des dividendes, sans heures étendues.

---

## 8. Architecture du dépôt

```
#KalmanFilter/
├── CLAUDE.md, PROJECT_PLAN.md, RESEARCH_PHILOSOPHY.md     gouvernance, feuille de route, esprit
├── RESEARCH_LOG.md, RESEARCH_INSIGHTS.md, BEST_RESULTS.md  journal, enseignements, meilleurs résultats
├── passation.md                                         ce document
├── pine/baseline/AKF_TSO_v2.1_baseline.pine             baseline gelée
├── src/                                                 code (pythonpath = src, experiments/p0)
├── tests/                                               18 fichiers de tests, conftest.py, fixtures/
├── experiments/<ID>/                                    une expérience par dossier
└── data/raw/                                            séries (CSV ignorés, .meta.json versionnés)
```

| Module `src/` | Rôle | Statut |
|---|---|---|
| `indicator/` (`kalman.py`, `trend_strength.py`, `segments.py`, `_bounds.py`) | Réplique certifiée du Pine v2.1 : Kalman, oscillateur, zones, signaux | **Sanctuarisé** |
| `features/` (`kalman_intrinsic.py`, `multi_tf.py`) | Descripteurs (`nis_z_100`, segments) et features 1 h | Copie certifiée de `#KAKALMAN` |
| `estimand/` (`bars.py`, `stoploss.py`, `excursions.py`) | Chargement tronqué, garde hold-out, stops, courbes, drawdowns | Copie certifiée |
| `labeling/costs.py`, `utils/data_loader.py`, `config.py` | Coûts, chargeur OHLC à contrôle SHA-256, constantes | Copies certifiées ; `config.py` à ne pas « nettoyer » |
| `anatomy/` | A01 : `build_atlas` (signaux et descripteurs), `DEV_END` | Projet |
| `categorization/` | B01 : `add_derived`, `assign_families`, `causal_threshold`, bootstrap par grappes | Projet |
| `envelope/` | C : `stops.py` (SL-A, SL-B, `route_levels`, `stop_trades`, `breakeven_trades`), `metrics.py`, `sequential.py` (dont `simulate_strategy`, stop-and-reverse natif), `decouple.py` (D01.6) | Projet |
| `context/` | C04 : tendances de contexte, veto contre-tendance | Rejeté, gardé pour mémoire |
| `strategy/re1.py` | **RE-1 générique** pour tout OHLC de 30 min : `load_asset`, `frozen_masks`, `run_re1`, `metrics`, `sample_years` ; seuils BTC gelés | **Référence de D02** |
| `marketdata/` | Acquisition et audit : `coinbase`, `histdata`, `alpaca`, `fred`, `saxo` (OAuth PKCE, graphiques v3, garde 2026), `audit`, `bars` | Projet |

---

## 9. Scripts importants et leur rôle

| Script | Rôle |
|---|---|
| `experiments/C02bis/run_C02bis.py` | Naissance de RE-1 : `Engine`, `full_masks`, `metrics`, `check_anchor` (ancre P6.5d) ; référence trade par trade |
| `experiments/C05/run_C05.py` | Sensibilité de RE-1 (classe `Sens`), modèle de lecture plateau / falaise / crête |
| `experiments/D01/run_D01.py` | Chaîne multi-actifs : `prepare`, `audit_asset`, `coverage`, `check_btc` (parité C02bis bloquante), `diagnostics`, `boot_ci`, tableaux `row8` |
| `experiments/D01/donnees_D01.py` | Acquisition de D01 (Coinbase, HistData, FRED, EIA) |
| `experiments/D01_5/run_D01_5.py` | Grille de H sur entrées figées (`frozen_exit`) |
| `experiments/D01_6/run_D01_6.py` | Verrouillage découplé, sortie de fin de séance |
| `experiments/D01_7/run_D01_7.py` | Portabilité 24/5 et ETF : `--audit`, mesures, `--rapport` ; recoupements externes, fermetures admises |
| `experiments/D01_7/saxo_univers_D01_7.py` | Sondage et téléchargement Saxo (`--seulement`, `--analyse`) ; ticker exact exigé |
| `experiments/D01_7/saxo_probe_D01_7.py` | Première sonde Saxo (CFD et futures) ; fonctions réutilisées (`Session`, `probe_cfd`) |
| `experiments/D01_7/donnees_D01_7.py` | HistData GBPJPY, séries FRED |
| `experiments/p0/akf_replique_pine.py` | Oracle de parité (**ne jamais modifier**) |
| `experiments/p6_5/` | Trades de l'ancre P6.5d, contrôle bloquant |

**Chaînes d'import :**
- D01.7 → D01 → C02bis, par `importlib`. `run_D01_7` enregistre ses actifs dans `D01.ASSETS`.
- Les scripts C contiennent des contrôles propres à BTC : pour un autre actif, passer par `strategy.re1` et la chaîne de
  D01.

**Commandes :**
- Depuis la racine : `PYTHONIOENCODING=utf-8 python experiments/<ID>/run_<ID>.py`.
- Tests : `python -m pytest -q` → **244 réussis, 2 ignorés** au 2026-10-01 (environ 2 min).

---

## 10. Méthodologie statistique

- **Espérance par trade en ATR14(t) et en bps**, avec IC 95 % par bootstrap de grappes de mois d'entrée (2 000 tirages,
  graine fixe). Les deux IC sont toujours publiés (I-M8) ; ils peuvent diverger, comme sur US30.
- **Lecture des distributions :** médiane, moyenne, moyenne winsorisée P1-P99, queues P5/P95, apport du décile
  supérieur (I-M5, I-M6). L'espérance est portée par la queue droite.
- **Bêta contre timing sans placebo (I-M7) :**
  - timing = moyenne de la composante Long et de la composante Short ;
  - dérive = demi-écart entre les deux.
- **Effet apparié sur les mêmes entrées** avant toute lecture séquentielle (I-M9). Une variation de H ou de sortie se
  lit sur entrées figées (I-M16).
- **Drawdown = statistique de chemin** : plage de chemins réordonnés, jamais appelée « IC » (I-M10).
- **Règle de risque contre simple réduction de taille**, à MDD égal (I-M11).
- **Sensibilité par bandes marginales** ; règle plateau / falaise / crête fixée avant (I-M12, C05).
- **Capital :**
  - composé à 0,25 %/ATR (plafond 1x) et à 1x ;
  - Calmar = PnL annualisé / |MDD valorisé| ;
  - annualisation sur la durée propre de chaque série (`sample_years`).
- **Frais en ATR, actif par actif** (I-M14) : frais / ATR14(t) à l'entrée.
- **Interruptions et gaps :** décomposition du brut en composante de reprise et composante hors reprise ; stops percés
  et leur dépassement.
- **Données :** structure vérifiée (fuseau, séances) par les données elles-mêmes, pas par la documentation (I-M13).
  Recoupement externe quand une référence existe.
- **Invariance d'échelle du moteur**, vérifiée à la précision machine (I-M17).

---

## 11. Règles anti-look-ahead et anti-data-mining

**Anti-look-ahead :**
- signal à la clôture de t, entrée à open[t + 1] ;
- aucune donnée postérieure à t dans un descripteur ; `shift(-1)` interdit ;
- tests de causalité par troncature dans chaque module ;
- seuils de population gelés (option (a)), ou causaux (`categorization.causal_threshold`, glissants ou expansifs),
  jamais calculés sur l'échantillon testé sans le dire ;
- stops testés en intrabarre, exécution au niveau ou à l'ouverture en cas de gap ;
- aucune barre de 2026 : gardes dans les chargeurs et dans le client Saxo ;
- un rétro-ajustement par ratio n'introduirait pas d'information future, puisque le moteur est invariant d'échelle
  (I-M17). Il n'est plus utilisé : les séries continues ont été abandonnées.

**Anti-data-mining :**
- cadrage en 4 champs et règle de lecture **écrits avant le calcul**, dans le script et le narratif ;
- un facteur à la fois ; grilles déclarées à l'avance ; tous les points publiés, pas seulement le meilleur ;
- lecture de plateaux, pas de pics. Le rang du point de référence dans sa grille est publié (I-M12) ;
- pas de test « signal contre hasard » ; pas de placebo non apparié ;
- frais dès la première barre ; aucune décision sur le brut ;
- **sélection d'actifs** : choisir pour D02 les meilleurs actifs de D01 revient à sélectionner sur le même échantillon,
  ce qui favorise les gagnants chanceux. Toute sélection doit être vérifiée hors échantillon ;
- hold-out scellé (ETH, XRP, 2026) jusqu'à la validation finale, sans nouvelle optimisation.

---

## 12. Erreurs méthodologiques et pièges à ne pas reproduire

| Où | Erreur ou piège | Leçon |
|---|---|---|
| Phase 0 | Chiffres d'archives d'autres moteurs pris pour référence | Non transposables (moteur, règles, frais) |
| Recadrage | Test « signal contre hasard » | Rejeté : biais de dérive et de bêta |
| C01 à C02bis | Exclusion de Q4, règle de F3, H = 26 décidés après lecture | Biais de sélection connu : d'où D01, puis le hold-out |
| C02 | Fenêtre du SL-B prise sur [t − `prev_seg_len`, t], et non sur la formule du cadrage | Écart signalé, conservé |
| C02bis | Annualisation des seuils causaux sur 6 ans | 5,56 ans, du 501e signal (9 juin 2020) à fin 2025 |
| C03 | Plage de chemins réordonnés appelée « IC » | « Plage P2,5-P97,5 » |
| C04 | Tendance attribuée avant la première bougie de 4 h close | Tendance valide seulement après une bougie close |
| D01 | Horloge HistData supposée en EST fixe | En réalité EET/EEST − 7 h : vérifier par la structure (I-M13) |
| D01 bis | Clôtures anticipées et split de XLE | Calendrier NYSE et série ajustée (I-M15) |
| D01.7 | Séries continues Saxo supposées sans roulement | Raccords bruts ; WTI au milieu d'une barre : impossible à ajuster proprement |
| D01.7 | Motif de recherche trop large : NLR retenu à la place d'URA | Ticker exact exigé, aucun repli |
| D01.7 | Convention `_brut.csv` différente entre Alpaca (série non ajustée) et Saxo (champs bid/ask) | Contournée dans `run_D01_7._gaps_profile` |
| D01.7 | Lire l'espérance seulement en ATR | US30 : −0,004 ATR mais +3,9 bps ; publier les deux |
| Saxo | Clé SIM enregistrée au lieu de la clé LIVE ; 403 sans accès Open API activé | Vérifier par empreinte ; activer l'accès dans SaxoTrader |
| Porteur | Chiffres de relecture non vérifiés | Toujours recalculer et signaler l'écart |
| Outils | Longs heredocs Bash tronqués ou mal interprétés ; sortie tamponnée en arrière-plan | Écrire les fichiers avec les outils d'édition ; lire la sortie à la fin |
| Secrets | Clés Alpaca collées dans le chat par le porteur | Jamais utilisées ni écrites ; rotation conseillée ; variables d'environnement seulement |

---

## 13. Étape D02 : objectifs, espace d'optimisation, protocole WFO / OOS / hold-out, livrables

> Cette section reprend ce que le porteur a décidé, puis **propose** le reste. Tout ce qui est marqué
> « à trancher » doit être validé par lui avant le moindre code ou calcul.
>
> **Mise à jour du 2026-10-01 : le protocole EXP-D02 du porteur tranche les points ouverts de §13.2 à §13.4**
> (`RESEARCH_LOG.md`, entrée EXP-D02). En bref :
> - univers BTC 2013-2025, SOL, AVAX, or 2009-2025, une passe indépendante par actif ;
> - H (6 à 60), R0 (10 à 500) et frontière F2b/F3 (0,75 à 0,95), en OFAT puis conjointement ; grille exhaustive ;
> - IS de 24 mois, OOS de 6 mois ; seuils de population réestimés sur chaque IS ;
> - choix en IS au Calmar net sur voisinage ;
> - noyau Numba (VectorBT abandonné) et Gate 0 avant tout calcul.
>
> La fonction objectif « fixée avant » de §13.2.3 est celle du porteur ; l'agent ne propose aucun seuil a priori. Le
> reste de la section décrit l'état de la réflexion avant ce protocole.

### 13.1 Objectifs

- **Décidé (`PROJECT_PLAN.md` phase 5, direction du 2026-09-29) :** mesurer le gain de performance dû à l'optimisation,
  contre RE-1 figée. On compare :
  - les paramètres fixes, RE-1 ;
  - les paramètres optimisés sur l'échantillon ;
  - les paramètres recalibrés par walk-forward.

  Le but n'est pas le meilleur backtest historique : il s'agit de savoir si optimisation et recalibrage apportent
  réellement quelque chose hors échantillon.
- **Décidé (2026-10-01) : adaptation multi-actifs.** Le walk-forward doit dire si un recalibrage dans le temps, par actif
  ou commun à plusieurs actifs, rend RE-1 exploitable là où le zero-shot ne l'était pas.
- **Esprit (`RESEARCH_PHILOSOPHY.md` §3.3, §4.3) :** Optuna scanne des plateaux, il ne cherche pas des pics. Un échec
  à paramètres fixes signale d'abord la non-stationnarité (§4.4).

### 13.2 Espace d'optimisation envisagé

- **Cadrage antérieur du porteur :** D02 = VectorBT + Optuna en walk-forward, **sur H et R0 seulement**.
  - **R0** est le seul axe sensible du moteur : sous le reset de P, Q est inerte (`RESEARCH_PHILOSOPHY.md` §5). Il règle
    la réactivité du filtre ; la valeur par défaut est 100.
  - **H** est l'horizon de sortie, 26 barres dans RE-1. En zero-shot, il déplace l'exposition, pas l'espérance (K9).
- **À trancher avec le porteur :**
  1. **Plages et pas :**
     - R0 sur une échelle logarithmique, par exemple 25 à 400 ;
     - H, par exemple 13 à 52 barres, ou en heures pour les actifs de séance.
     - Grille complète (carte de plateau lisible) ou Optuna (TPE) : avec 2 paramètres, une grille est plus transparente ;
       Optuna reste possible.
  2. **Seuils de population quand R0 ≠ 100.** Le seuil de `leg_atr` (2,8233) et celui de `nis_z_100` (1,2245) ont été
     calibrés à R0 = 100 sur BTC. Trois options :
     - (a) les garder gelés ;
     - (b) les recalculer par fenêtre d'apprentissage ;
     - (c) les rendre causaux.

     Le choix change la population des signaux.
  3. **Fonction objectif**, fixée avant :
     - espérance nette en ATR, avec un nombre minimal de trades ;
     - ou Calmar à 0,25 %/ATR ;
     - ou un critère de plateau : centre d'une zone stable plutôt que maximum ;
     - et la règle de choix du point, par exemple le centre d'un plateau dont les voisins restent au-dessus de X.
  4. **Univers :**
     - quels actifs ? BTC et SOL au minimum ; **AVAX ajouté par le porteur (2026-10-01)** ; LINK et LTC non ajoutés ;
       or, US30, GER40, US100, GDX… selon le porteur ;
     - un jeu de paramètres par actif, ou commun à plusieurs actifs (paramètres poolés) ?
  5. **Coûts :** ceux de D01 et D01.7 par actif (crypto 5 et 10 bps, or 4, coût principal des CFD et ETF). Faut-il
     d'abord mesurer le coût réel chez Saxo ?
  6. **Horizon sur les actifs de séance :** en barres ou en heures, et sortie avant la nuit ou non.
- **Hors périmètre, sauf décision contraire :**
  - les autres paramètres du moteur (q1, q2, γ, N2, R2) ;
  - les bornes de `retrace_ratio` ;
  - le stop de F3 ;
  - les règles rejetées de l'Étape C.

  Respect de l'OFAT : on ne rouvre pas l'enveloppe en même temps que le moteur.

### 13.3 Protocole WFO / OOS / hold-out (proposition)

- **Données :** depuis D02.0, historiques longs disponibles : BTC 2013-2025, or 2009-2025, AVAX depuis le 2021-09-30
  (SOL depuis le 2021-06-17). Le porteur veut le plus de données possible pour le walk-forward. La référence figée
  dépend de la période (D02.0 : BTC 2013-2019 −0,045 ATR, or 2009-2019 +0,011). 2026 et ETH/XRP restent scellés.
- **Découpage, à trancher :** fenêtres glissantes, par exemple 24 mois d'apprentissage et 6 mois de test, au pas de 6
  mois. Cela donne 8 tests hors échantillon couvrant 2022-2025 ; une variante ancrée est possible.
  - Le warm-up du moteur (300 barres et 300 bougies de 1 h) est pris dans les données qui précèdent chaque test : c'est
    causal.
  - Les trades sont attribués au test par leur entrée ; une position ouverte à la frontière est fermée selon sa règle.
- **Références sur les mêmes fenêtres de test :**
  - RE-1 figée (R0 = 100, H = 26) ;
  - le meilleur point plein échantillon, biaisé par construction, à titre de borne ;
  - le WFO.

  **Le gain de l'optimisation est la différence WFO − RE-1 figée**, mesurée hors échantillon par effet apparié quand
  c'est possible.
- **Lecture, fixée avant :**
  - les 8 métriques hors échantillon concaténées, IC par grappes mensuelles en ATR et en bps ;
  - la stabilité des paramètres choisis d'une fenêtre à l'autre : un plateau stable ou des sauts ;
  - la carte de plateau de chaque fenêtre d'apprentissage ;
  - le nombre total de configurations essayées, publié.
- **Hold-out :** il n'est ouvert qu'une fois, pour la validation finale (phase 7), avec les paramètres et la règle de
  recalibrage figés, sans nouvelle optimisation. Le hold-out n'étant pas vierge (§2.1), il faut le lire avec réserve.

### 13.4 Prérequis techniques (proposition)

- **Moteur de référence :** `strategy.re1` (parité C02bis bloquante sur 1 080 trades).
  - Si VectorBT est retenu, il doit d'abord **reproduire RE-1 trade par trade** sur BTC, comme contrôle bloquant.
  - Sinon, Optuna ou une grille pilote directement `strategy.re1`.
- **Coût de calcul :**
  - un changement de R0 impose de recalculer l'atlas, soit le Kalman sur toute la série (quelques secondes par actif) ;
  - un changement de H ne touche que l'enveloppe.

  Il faut donc précalculer un atlas par couple (actif, R0), puis balayer H. Le plan doit chiffrer le nombre de
  configurations avant le GO.
- **Code nouveau,** par exemple `src/optimization/` pour les fenêtres, l'objectif et le choix sur plateau :
  - avec ses tests : causalité des fenêtres, aucun recouvrement entre apprentissage et test, reproduction de RE-1 à
    R0 = 100 et H = 26 ;
  - dans un commit séparé de l'analyse.

### 13.5 Livrables attendus (modèle du projet)

1. Le cadrage en 4 champs, la règle de lecture et le plan chiffré (actifs, plages, nombre de configurations, découpage),
   **validés par le porteur avant le calcul**.
2. Le module `src/` et ses tests, dans un commit séparé.
3. `experiments/D02/run_D02.py` :
   - contrôles bloquants (parité RE-1, garde 2026) ;
   - résultats CSV et JSON ;
   - cartes de plateau ;
   - tableaux hors échantillon à 8 métriques, avec PnL et MDD à 1x à côté de 0,25 %/ATR.
4. `narratif_D02.md` et `rapport_D02.md`.
5. Mises à jour de `RESEARCH_LOG.md`, `RESEARCH_INSIGHTS.md`, `BEST_RESULTS.md` et `PROJECT_PLAN.md`.
6. Commits locaux ; push sur accord.

---

## 14. État exact du dépôt et des commits (2026-10-01)

| Élément | Valeur |
|---|---|
| Dossier local | `C:\Users\poek9\Projet Claude\#KalmanFilter` (le `#` impose des guillemets) |
| GitHub | https://github.com/PokiCodeLonggamma/kalman_filter, **public**, branche `main` |
| `origin/main` | le commit qui contient cette passation, validée par le porteur et poussée le 2026-10-01 (vérifier par `git log -2`) ; avant elle : `1243da3` (D01.7, partie 2) |
| Commits locaux non poussés | aucun au moment de la validation ; ensuite, D02.0 : `7dca1f8` (données, poussé), puis le commit du rétro-test (voir `git log`) |
| Identité git | `PokiCodeLonggamma <250868839+PokiCodeLonggamma@users.noreply.github.com>` |
| Tests | 249 réussis, 2 ignorés (244 à la validation, +5 en D02.0) |
| Système | Windows 11, Git Bash et PowerShell, application Claude Code de bureau, navigateur intégré |
| Python | 3.11 ; numpy, pandas, matplotlib (`pyproject.toml`) |
| Mémoire de l'assistant | `C:\Users\poek9\.claude\projects\C--Users-poek9-Projet-Claude--KalmanFilter\memory\` |

**Commits par étape :**

| Étape | Commits |
|---|---|
| Gouvernance et copies certifiées | `1ae82b8`, `f850f18`, `46bb722`, `19a5990` |
| A01 | `6a3ce87`, `50ded4f`, `94a83bb` |
| B01 | `a20e052`, `5d0639b` |
| C01 | `73da9cc`, `e583e70` |
| C02 | `11d81c2`, `899956a` |
| C02bis | `13e8ee4`, `2b6fed7` |
| C03 | `1348193`, `547af84`, `47a3262` |
| C04 | `eb8949f`, `1dba30c` |
| C05 | `f281bdf` |
| Passation C → D | `4831a1c` |
| D01, D01 bis | `1f57997`, `2b5b32c`, `a228b5b`, `04b35f7`, `05a6970` |
| D01.5 | `5b156d0` |
| D01.6 | `3ad0f1b` |
| D01.7 | `39988a3` (partie 1), `454566c` (audit GitHub), `9c208a0`, `49433e8`, `78f51f7`, `8557219` (Saxo), `e8bcc24` (raccords), `343112c` (univers), `1243da3` (partie 2) |
| D02.0 | `7dca1f8` (historiques longs et audit), puis le rétro-test de RE-1 figée |

---

## 15. Prochaines étapes concrètes et premier message attendu

1. **Fait (2026-10-01) :** passation relue et validée par le porteur, puis poussée. Ensuite, sur décision du porteur : EXP-D02.0,
   historiques longs (BTC 2013, or 2009, AVAX) et rétro-test de RE-1 figée (`experiments/D02_0/narratif_D02_0.md`).
2. **Nouvelle session :** lire ce document, puis :
   - `CLAUDE.md`, `RESEARCH_PHILOSOPHY.md`, `PROJECT_PLAN.md` ;
   - `BEST_RESULTS.md`, `RESEARCH_INSIGHTS.md` ;
   - les dernières entrées de `RESEARCH_LOG.md` ;
   - `src/strategy/re1.py` ;
   - `experiments/D01_7/narratif_D01_7.md`.
3. **Vérifier l'état :** `git status`, `git log --oneline -5`, `python -m pytest -q` (attendu : 249 réussis, 2 ignorés).
4. **Rendre au porteur un compte rendu court**, balisé :
   - compréhension du projet et de RE-1 ;
   - règles ;
   - état des données ;
   - **liste des décisions à prendre pour D02** (§13.2 à 13.4) : actifs, plages de H et de R0, seuils à R0 ≠ 100,
     fonction objectif et règle de plateau, découpage du walk-forward, paramètres par actif ou communs, coûts, horizon
     sur les séances, outil (VectorBT avec parité, ou moteur maison).
5. **Ne rien lancer, ne rien modifier, ne rien pousser** avant le GO du porteur sur le cadrage de D02.
