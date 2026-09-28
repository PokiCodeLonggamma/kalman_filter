# EXP-C01 — Découplage de la sortie et isolation des régimes, en exécution séquentielle

- **Date :** 2026-09-29. **Étape :** C, enveloppe mécanique (premier test).
- **Actif et période :** BTC/USD Bitstamp 30 min, 2020-01 → 2025-12 (72 mois). 2026, ETH et XRP ne sont pas lus.
- **Univers :**
  - configurations à horizon fixe : les 7 296 signaux d'A01 (identité contrôlée) ;
  - ancre native : 7 297 signaux, les mêmes plus celui de fin 2025, dont la sortie tombe en 2026.
- **Frais :** 5 et 10 bps aller-retour, déduits de chaque trade (net = brut − frais).
- **Reproduire :** `python experiments/C01/run_C01.py` (≈ 70 s) ; tests : `python -m pytest tests`.

## 0. Cadrage (validé par le porteur)

- **QUESTION :** en exécution séquentielle (une position à la fois), nette de 5 et 10 bps, que produisent :
  1. le remplacement de la sortie native par une sortie à horizon fixe H ∈ {6, 13, 26, 48}, sur tous les signaux ;
  2. à H fixé, l'exclusion des signatures de continuation ou la restriction aux régimes de B01 ;
  3. l'éviction de `nis_z_100` Q4, et l'inversion en continuation de R3 et de `nis_z_100` Q4 ?
- **PERTINENCE POUR LE FILTRE AKF :** la sortie native coupe vers 13 barres, dans le creux de respiration de l'oscillateur, et produit 84 retournements par mois. C01 isole l'effet du découplage de la sortie et du filtrage cinématique, avant tout stop.
- **CE QUE LE PROTOCOLE MESURE RÉELLEMENT :** sur les trades effectivement exécutés :
  - le tableau des 8 métriques à 5 et 10 bps ;
  - la décomposition Long / Short / timing / dérive (I-M7), en bps et en ATR14(t) ;
  - la stabilité annuelle ;
  - un IC 95 % de l'espérance et du timing, par bootstrap de grappes mensuelles (I-M6).
- **CE QU'IL NE PERMET PAS DE CONCLURE :**
  - l'effet d'un stop-loss, d'un break-even ou d'un filtre de tendance ;
  - une validation hors échantillon. Les régimes ont été définis après lecture de B01, sur les mêmes données. Les seuils (médiane de `leg_atr`, P75 de `nis_z_100`) sont calculés sur 2020-2025 entier ;
  - la meilleure paire (régime, H) est retenue parmi 64 : son résultat est optimiste.

## 1. [CODE] Implémentation et contrôles

- **Étape 0, copie certifiée depuis #KAKALMAN** (lecture seule ; manifeste `manifest_copie_C01_sha256.txt`). 9 fichiers copiés, SHA-256 identiques :
  - `estimand/stoploss.py`, `estimand/bars.py`, `labeling/costs.py` ;
  - `experiments/p6_5/strategie_stop*` : script, JSON et trois CSV de référence.
- **Trois écarts à la liste, tous signalés dans le manifeste.**
  - `estimand/excursions.py` est ajouté : `stoploss.py` en importe la constante `BPS`.
  - Les deux `__init__.py` sont écrits à neuf et minimaux : ceux d'origine importent des modules non copiés.
  - Les tests d'origine importent aussi des modules non copiés. Leurs fonctions de test sont reprises à l'identique (11 pour `stoploss`, 2 pour `costs`), mais pas les 4 tests propres au script P6.5d.
- **Ancre P6.5d, contrôle bloquant : reproduite à l'identique.**
  - Sans stop : 6 037 trades identiques au fichier de référence (barres, sens, rendements) ; espérance nette de −5,339143 bps ; PnL composé de −98,6701 % ; PF 0,907.
  - Stop à 2,5 % : 6 589 trades identiques.
  - Toutes les métriques du JSON de référence sont retrouvées : espérance, somme nette, WR, capital composé, drawdowns valorisé et aux sorties, durée médiane.
- **`src/envelope/`** (rien n'est réécrit : `apply_stop` exécute chaque trade, `equity_curve` et `drawdown_stats` valorisent le capital, `net_label` déduit les frais).
  - `time_stop_trades` : entrée à open[t + 1] si aucune position n'est ouverte, sortie à **open[t + 1 + H]**. La position est détenue pendant les barres t + 1 … t + H. Un signal pendant la détention est ignoré. Un signal à la clôture de t + H entre à la sortie même, sans barre partagée. Une sortie au-delà de 2025 est ramenée à la dernière barre de 2025. Le mode continuation inverse le sens.
  - Sortie à l'open plutôt qu'au close de B01 : cela permet de réutiliser `apply_stop` tel quel en C02. L'écart open[b + 1] / close[b] est de 1,25 bps en médiane et de 13,9 bps au P99.
  - `summarize` (8 métriques et décomposition par sens), `mean_ci` (bootstrap de grappes mensuelles), `by_year`.
- **Régimes :** recalculés depuis l'atlas. Les familles sont identiques à B01 et les effectifs à ceux du prompt : R1 1 935, R2 1 874, R3 2 347, `nis_z_100` Q4 1 824, etc.
- **Tests :** 26 ajoutés, dont 3 à la relecture (11 dans `tests/test_envelope.py`, 2 dans `tests/test_categorization.py`, 13 repris de #KAKALMAN). La suite complète passe : 176 réussis, 2 ignorés.
- **Relecture du 2026-09-29 :** contrôles A, B et C (§5, annexes F à H). La part des frais s'affiche « sans objet » si le PnL brut est ≤ 0 et « > 1 000 % » s'il est quasi nul, avec le brut par trade à côté.

## 2. [OBS] Mesures

Les tableaux complets des 8 métriques, à 5 et 10 bps, sont dans les annexes B à E ; figures 1 à 4. Sauf mention contraire, les chiffres sont nets de 5 bps, en bps par trade, avec leur IC 95 %.

### Palier 1 — Le découplage de la sortie ne suffit pas

| Tous les signaux | Trades / mois | Espérance nette [IC 95 %] | Espérance brute | Short net | PnL composé | Part des frais |
|---|---|---|---|---|---|---|
| Ancre native (signal opposé) | 83,8 | −5,3 [−10,8 ; +0,3] | −0,3 | −11,1 | −98,7 % | 1 474 % |
| H = 6 | 101,3 | −3,7 [−6,5 ; −0,9] | +1,3 | −4,6 | −95,7 % | 383 % |
| H = 13 | 68,1 | −4,3 [−9,2 ; +0,1] | +0,7 | −6,4 | −94,0 % | 729 % |
| H = 26 | 42,8 | −10,8 [−20,5 ; −2,9] | −5,8 | −19,0 | −98,4 % | 86 % |
| H = 48 | 25,9 | −16,0 [−32,1 ; +0,3] | −11,0 | −27,4 | −98,1 % | 45 % |

- Le poids des frais baisse, mais l'espérance brute du flux complet n'est jamais positive au-delà de 1 bps. Elle devient négative dès H = 26, où les Short subissent la hausse du BTC.
- La perte de la mécanique native ne vient donc pas seulement du turnover.
- À 10 bps, tout finit autour de −99 %.

### Palier 2 — Les régimes se séparent nettement

- **R3 et `nis_z_100` Q4, dans le sens du signal : pertes nettes, IC entièrement sous zéro de H6 à H26.**
  - R3 : −6,1 [−10,6 ; −1,1] ; −9,4 [−16,8 ; −1,5] ; −20,3 [−29,8 ; −11,3].
  - `nis_z_100` Q4 : −9,7 [−14,5 ; −4,9] ; −15,8 [−25,6 ; −6,9] ; −20,1 [−35,3 ; −4,4].
  - 0 à 2 années positives sur 6.
- **Les exclure améliore, sans franchir nettement les frais.** Sans `nis_z_100` Q4 : +0,8, +1,0 et +3,8 à H13, H26 et H48, avec des IC contenant 0. Le PnL composé reste négatif (−17 à −33 %).
- **R1, sans stop : négatif à tous les horizons** (−1,5 à −13,4 ; IC à H26 de [−24,5 ; −2,1]). Pourtant son WR est de 52,4 % à H6 : son avantage de médiane ne passe pas les frais en moyenne.
- **R2 : proche de 0.** +2,2 à H26 ; F2b · x1 déjà retourné +6,9 ; F3 · x1 déjà retourné +0,3.

### Palier 3A — L'éviction de `nis_z_100` Q4 améliore 18 comparaisons sur 20

| Contrôle → variante | H | Espérance du contrôle | Espérance de la variante [IC 95 %] | Long / Short | PnL composé | Années > 0 |
|---|---|---|---|---|---|---|
| R2 → R2 hors Q4 | 26 | +2,2 | +12,3 [−0,8 ; +26,4] | +14,2 / +10,1 | +187 % | 5/6 |
| ↳ F2b · x1 retourné → hors Q4 | 26 | +6,9 | +11,5 [−2,9 ; +26,7] | +9,8 / +13,2 | +78 % | 4/6 |
| ↳ F3 · x1 retourné → hors Q4 | 26 | +0,3 | +9,3 [−12,2 ; +28,4] | +10,7 / +7,4 | +48 % | 4/6 |
| Tous hors R3 → hors R3 et Q4 | 48 | +1,7 | +12,0 [−4,2 ; +30,1] | +28,0 / −3,2 | +192 % | 4/6 |
| R1 → R1 hors Q4 | 6 | −1,5 | +0,0 [−5,3 ; +4,9] | +0,9 / −0,7 | −8 % | 2/6 |

- **R2 hors Q4 n'est positif qu'à H26.** Il est à +0,3 à H13 et à −2,9 à H48.
- **Relecture : R2 hors Q4 mêle deux familles de comportements différents.**
  - F2b · x1 déjà retourné hors Q4 est positif à H13, H26 et H48 : +4,0, +11,5 et +3,4 bps ; +0,02, +0,39 et +0,22 ATR. À 10 bps, il ne tient qu'à H26 (+6,5 bps, +0,26 ATR, PF 1,09).
  - F3 · x1 déjà retourné hors Q4 rompt la régularité. En 2024 il fait −47 bps par trade à H26 et −60 à H48 ; à H48, Long −14,0 et Short +26,3.
- **Tous hors R3 et Q4 n'est positif qu'à H48** (+1,1 à H26). Le gain y est porté par les Long (dérive +15,6), avec 2021 et 2022 négatives.

### Palier 3B — Inversion en continuation

- **R3 en continuation, H26 : +10,3 [+1,3 ; +19,8].** C'est le seul IC entièrement positif des 64 configurations à 5 bps.
  - PF 1,15 ; PnL +281 % ; 23 trades par mois ; les deux sens sont positifs (Long +14,6, Short +6,2) ; 5 années sur 6.
  - En revanche, par année : +28, +26, +7, 0, +11, −8 bps. Et en ATR : +0,11 à 5 bps, −0,01 à 10 bps. Le gain vient des années volatiles 2020-2021.
- **`nis_z_100` Q4 en continuation : +5,8 à H13 et +10,1 à H26, IC contenant 0.** Positif en 2020-2021, négatif en 2024-2025 aux deux horizons.
- **À H6, l'inversion ne donne rien** (−3,9 et −0,3) : la continuation se développe au-delà d'une dizaine de barres.

### Les quatre configurations positives à 5 bps

| Configuration | PnL composé ; bps cumulés | PF | WR | Espérance : bps [IC] ; ATR | Max DD valorisé | Trades ; ignorés ; /mois | Durée | Part des frais |
|---|---|---|---|---|---|---|---|---|
| R2 hors Q4, H26 | +187 % ; +13 309 | 1,18 | 49,4 % | +12,3 [−0,8 ; +26,4] ; +0,35 | −47,6 % | 1 080 ; 26 % ; 15,0 | 26 | 29 % |
| R3 en continuation, H26 | +281 % ; +17 236 | 1,15 | 51,6 % | +10,3 [+1,3 ; +19,8] ; +0,11 | −47,6 % | 1 674 ; 29 % ; 23,2 | 26 | 33 % |
| `nis_z_100` Q4 en continuation, H26 | +129 % ; +12 380 | 1,13 | 51,4 % | +10,1 [−5,6 ; +25,3] ; +0,13 | −63,9 % | 1 231 ; 33 % ; 17,1 | 26 | 33 % |
| Tous hors R3 et Q4, H48 | +192 % ; +18 232 | 1,12 | 49,9 % | +12,0 [−4,2 ; +30,1] ; +0,23 | −80,7 % | 1 525 ; 62 % ; 21,2 | 48 | 29 % |

- **À 10 bps, aucune configuration n'a d'IC entièrement positif.** Les mêmes espérances tombent à +7,3, +5,3, +5,1 et +7,0 bps. En ATR : +0,22, −0,01, +0,04 et +0,10.
- **Dynamique :** même positifs, ces profils subissent des drawdowns valorisés de 48 à 81 % en réinvestissement intégral.
- **Écart entre moyenne arithmétique et PnL composé :** l'écart-type par trade vaut 111 bps à H6, environ 220 bps à H26 et 317 bps à H48. Il coûte 0,6 à 5 bps par trade au capital composé. Ainsi, Tous hors Q4 à H48 fait +3,8 bps en moyenne, mais −1,3 bps en moyenne géométrique, d'où son PnL composé négatif.

## 3. [HYP] Lectures

- **Le signal v2.1 pris dans son sens, sans stop, ne dégage pas d'espérance nette solide.** Seul R2 hors Q4 à H26 s'en approche. L'information cinématique la plus robuste est négative : R3 et `nis_z_100` Q4 signent une continuation. C01 le confirme en trades séquentiels.
- **R3 en continuation :** un signal tardif, après une grande jambe ou un choc, laisse la tendance précédente reprendre sur une vingtaine de barres. Le gain dépend du régime de volatilité (2020-2021). C'est la question à trancher avant d'en faire une piste.
- **R2 hors Q4 à H26 :** cassure de compression cohérente avec B01 (timing moyen de +0,28 ATR à H26). Le gain est des deux côtés, 5 années sur 6, et tient en ATR à 10 bps. Mais le pic isolé à H26 fait craindre un effet étroit ou en partie dû au bruit.
- **R1 :** comme B01 l'annonçait, son avantage de médiane ne survit pas aux frais sans stop. Le test pertinent est celui du stop (C02).
- **`nis_z_100` Q4 :** son exclusion est le filtre le plus régulier de C01 (18 comparaisons sur 20).

## 4. [DECISION] Orientations (rien n'est lancé)

- **Constat :**
  - le découplage de la sortie ne rend pas le flux complet rentable ;
  - le filtrage cinématique ne change le signe que pour quelques paires (régime, H), à 5 bps, avec des IC larges ;
  - à 10 bps, aucune configuration n'a d'IC entièrement positif ;
  - la seule espérance à IC positif est R3 en continuation à H26 : c'est un meilleur de 64, porté par 2020-2021.
- **Décisions du porteur (relecture du 2026-09-29) :**
  - la continuation est écartée définitivement comme mode d'entrée : R3 et `nis_z_100` Q4 ne servent plus que de filtres d'exclusion. R3 en continuation tombe à environ +2,3 bps par trade sur 2022-2025 (−2,7 à 10 bps, −0,01 ATR à 10 bps sur toute la période) ; `nis_z_100` Q4 en continuation fait −23,0, −13,4 et −5,5 bps en 2022, 2024 et 2025 ;
  - R2 hors Q4 n'est pas traité comme un bloc : F2b · x1 déjà retourné hors Q4 est le candidat principal de C02, F3 · x1 déjà retourné hors Q4 est traité à part.
- **Pour C02 (stop-loss seul, OFAT),** candidats : F2b · x1 déjà retourné hors Q4 (H26) avec un stop large ou un break-even différé ; F3 · x1 déjà retourné hors Q4, à part ; R1 (H6 ou H13) avec un stop structurel serré.
- **Points à trancher avant C02 :**
  1. le choix de H par régime : les pics sont isolés (R2 hors Q4 à H26, Tous hors R3 et Q4 à H48) ;
  2. le dimensionnement : le réinvestissement intégral donne des drawdowns de 48 à 81 % et un écart arithmétique / composé de 2 à 5 bps par trade ;
  3. les frais : à 10 bps, rien ne se distingue de 0 ; l'hypothèse de 5 bps devient décisive ;
  4. une validation hors échantillon, avant toute conclusion (Étape D).
- **Aucune Étape C02 n'est lancée.**

## 5. Contrôles complémentaires (relecture du 2026-09-29)

Demandés par le porteur avant de cadrer C02 ; calculés sur les données de C01, sans C02. Détail : annexes F à H, `controle_A_C01.csv`, `controle_B_C01.csv`. Chiffres nets de 5 bps.

### Contrôle A — Éviction pure ou déblocage séquentiel ? (H26)

- **[CODE]** La course du contrôle est purgée a posteriori de ses trades `nis_z_100` Q4, sans rouvrir les signaux qu'ils masquaient. On la compare à la course hors Q4, qui rouvre ces signaux.

| Groupe | Course du contrôle | Trades Q4 retirés | Purge a posteriori (éviction pure) | Course hors Q4 | Dont trades débloqués |
|---|---|---|---|---|---|
| R2 | +2,2 (1 353) | −22,0 (319) | +9,7 [−3,7 ; +23,1] (1 034) | +12,3 (1 080) | +54,7 (61) |
| ↳ F2b · x1 déjà retourné | +6,9 (676) | −69,6 (43) | +12,1 [−3,5 ; +27,9] (633) | +11,5 (639) | −54,2 (6) |
| ↳ F3 · x1 déjà retourné | +0,3 (902) | −10,3 (314) | +5,9 [−14,9 ; +24,9] (588) | +9,3 (601) | +122,8 (15) |

- **[OBS] F2b · x1 déjà retourné : le gain vient entièrement de l'éviction.** Retirer ses 43 trades Q4 (−69,6 bps en moyenne) le porte de +6,9 à +12,1. Les 633 trades conservés sont tous repris par la course hors Q4, qui n'en débloque que 6.
- **[OBS] R2 : environ trois quarts de l'amélioration viennent de l'éviction (+7,5 bps), un quart du calendrier (+2,6 bps).** Ce quart repose sur 61 trades débloqués à +54,7 bps en moyenne.
- **[OBS] F3 · x1 déjà retourné : un tiers de son PnL hors Q4 vient de 15 trades débloqués** (+122,8 bps en moyenne, soit 2,5 % des trades). L'éviction pure ne donne que +5,9 [−14,9 ; +24,9].

### Contrôle B — Seuils causaux

- **[CODE]** Médiane de `leg_atr` et P75 de `nis_z_100` recalculés sur les seuls signaux précédents : fenêtre glissante de 500 signaux, ou fenêtre expansive. Les 500 premiers signaux (janvier à mai 2020) servent de période de chauffe. Les trois variantes sont comparées sur la même période. `R1` ne dépend pas de la médiane de `leg_atr` : seul son filtre Q4 change.
- **[OBS] Les masques changent à peine** : 98,6 à 99,9 % des signaux restent classés de la même façon.

| Configuration, horizon | Seuils de l'échantillon entier | Glissante 500 signaux | Expansive |
|---|---|---|---|
| F2b · x1 déjà retourné hors Q4, H26 | +10,2 [−3,7 ; +25,5] | +11,5 [−3,4 ; +29,0] | +12,6 [−3,2 ; +29,6] |
| R2 hors Q4, H26 | +11,6 [−3,6 ; +26,3] | +12,9 [−1,8 ; +27,7] | +11,4 [−4,0 ; +26,1] |
| F3 · x1 déjà retourné hors Q4, H26 | +10,0 [−10,7 ; +29,7] | +10,8 [−10,4 ; +31,1] | +9,0 [−12,7 ; +29,3] |
| R1 hors Q4, H6 | −0,8 [−6,1 ; +4,1] | −1,6 [−7,0 ; +3,2] | −0,9 [−6,2 ; +3,9] |

- **[OBS] Les résultats ne dépendent pas du calcul des quantiles sur 2020-2025 entier** : les écarts restent sous 2,5 bps. R1 hors Q4 n'a pas d'avantage à H6, quelle que soit la variante : il était à +0,0 sur toute la période et reste proche de −1 bps hors de la période de chauffe.

### Contrôle C — Capital à risque constant par trade

- **[CODE]** La taille de chaque position est choisie pour qu'un ATR14(t) représente une part fixe du capital, avec un levier plafonné à 1x. Les frais sont proportionnels au notionnel. Le capital est valorisé à chaque clôture de barre, comme `equity_curve`.
- **[OBS] Ton exemple (1 ATR = 1 % du capital) ne change presque rien.** L'ATR14 médian vaut 50 bps, donc 90 % des trades restent au plafond de 1x (exposition moyenne 0,98). On retrouve à peu près le notionnel fixe. Le niveau 0,25 % (12 % de trades plafonnés, exposition moyenne 0,55) réalise l'alignement voulu sur l'espérance en ATR.

| Configuration | Notionnel fixe 1x : PnL ; DD | Risque 0,25 % par ATR, 5 bps : PnL ; DD | Risque 0,25 %, 10 bps : PnL ; DD |
|---|---|---|---|
| F2b · x1 déjà retourné hors Q4, H26 | +78 % ; −45 % | +72 % ; −13 % | +42 % ; −17 % |
| R2 hors Q4, H26 | +187 % ; −48 % | +122 % ; −20 % | +60 % ; −22 % |
| R3 en continuation, H26 | +281 % ; −48 % | +60 % ; −34 % | +3 % ; −47 % |
| Tous hors R3 et Q4, H48 | +192 % ; −81 % | +98 % ; −46 % | +29 % ; −49 % |
| Ancre native | −98,7 % ; −99,6 % | −76 % ; −86 % | −96 % ; −97 % |

- **[OBS] À risque constant, les drawdowns fondent là où l'espérance en ATR est positive.** F2b · x1 déjà retourné hors Q4 passe de −45 % à −13 %, pour un PnL presque inchangé.
- **[OBS] R3 en continuation, pondéré par l'ATR, retombe à +3 % à 10 bps :** son gain venait des années les plus volatiles.

### [HYP] et suite

- **F2b · x1 déjà retourné hors Q4 à H26 résiste aux trois contrôles :** gain dû à l'éviction pure, seuils causaux, risque constant. Son IC reste pourtant large ([−3,5 ; +27,9] en éviction pure) et il perd à H6. Il a été retenu après lecture des résultats, sur 64 configurations puis une séparation F2b / F3 : c'est le meilleur candidat de C02, pas un résultat établi.
- **F3 · x1 déjà retourné hors Q4 tient surtout par ses trades débloqués et par ses années 2020-2021 et 2025.** Son éviction pure n'est pas distinguable de 0.
- **Le dimensionnement à risque constant** pourrait devenir la convention de capital de l'Étape C. C'est à valider, comme facteur distinct, avant ou après C02.
- **Aucune Étape C02 n'est lancée.**

---

# Annexes chiffrées (générées par `run_C01.py`)

## A. Ancre et conventions

| Contrôle | Résultat |
|---|---|
| Ancre P6.5d sans stop (sortie au signal opposé, 5 bps) | 6 037 trades identiques au fichier de référence (barres, sens, rendements) ; trade ouvert fin 2025 : signal 105211 |
| Ancre P6.5d, stop 2,5 % | 6 589 trades identiques (test `test_ancre_p65d_reproduite`) |
| Signaux de la stratégie native | 7 297 (univers A01 + le signal de fin 2025) |
| Univers des configurations à horizon fixe | 7 296 signaux d'A01 ; familles identiques à B01 |
| Sortie à horizon fixe | open[t + 1 + H] ; position détenue pendant les barres t + 1 … t + H |
| Écart open[b + 1] / close[b] (toutes barres) | nul dans 15,0 % des cas ; médiane 1,25 bps ; P99 13,90 bps ; max 151,8 bps |
| Période | 2020-01 → 2025-12 (72 mois) ; aucune barre de 2026 lue |

## B. Palier 1 — Découplage de la sortie (Tous)

Contrôle : ancre native (sortie au signal opposé). Variantes : même flux, sortie à horizon fixe.

**5 bps aller-retour — 8 métriques**

| Configuration | PnL net : composé ; bps cumulés | PF | WR | Espérance : bps [IC 95 %] ; ATR | Max DD : valorisé ; bps | Trades : n ; ignorés ; /mois | Durée méd. (barres) | Part des frais ; brut par trade (bps) |
|---|---|---|---|---|---|---|---|---|
| Ancre native P6.5d | −98,7 % ; −32232 | 0,907 | 43,8 % | −5,3 [−10,8 ; +0,3] ; −0,077 | −99,6 % ; −47280 | 6 037 ; 17 % ; 83,8 | 13 | sans objet (brut ≤ 0) ; −0,3 |
| Tous, H = 6 | −95,7 % ; −26967 | 0,899 | 46,9 % | −3,7 [−6,5 ; −0,9] ; −0,095 | −97,8 % ; −34428 | 7 296 ; 0 % ; 101,3 | 6 | 383 % ; +1,3 |
| Tous, H = 13 | −94,0 % ; −21159 | 0,921 | 48,0 % | −4,3 [−9,2 ; +0,1] ; −0,074 | −96,4 % ; −27407 | 4 905 ; 33 % ; 68,1 | 13 | 729 % ; +0,7 |
| Tous, H = 26 | −98,4 % ; −33234 | 0,864 | 48,5 % | −10,8 [−20,5 ; −2,9] ; −0,138 | −99,1 % ; −39987 | 3 080 ; 58 % ; 42,8 | 26 | sans objet (brut ≤ 0) ; −5,8 |
| Tous, H = 48 | −98,1 % ; −29866 | 0,858 | 49,0 % | −16,0 [−32,1 ; +0,3] ; −0,289 | −99,2 % ; −40174 | 1 866 ; 74 % ; 25,9 | 48 | sans objet (brut ≤ 0) ; −11,0 |

**5 bps — Long / Short / timing (nets)**

| Configuration | Long : bps ; ATR | Short : bps ; ATR | Timing : bps [IC 95 %] ; ATR | Dérive (bps) | Écart à Tous, Long / Short (bps) | Années PnL > 0 | Années timing > 0 |
|---|---|---|---|---|---|---|---|
| Ancre native P6.5d | +0,41 ; +0,032 | −11,09 ; −0,186 | −5,3 [−10,8 ; +0,3] ; −0,077 | +5,75 | — | 2/6 | 2/6 |
| Tous, H = 6 | −2,82 ; −0,072 | −4,56 ; −0,117 | −3,7 [−6,5 ; −0,9] ; −0,094 | +0,87 | +0,00 / +0,00 | 1/6 | 1/6 |
| Tous, H = 13 | −2,15 ; −0,020 | −6,40 ; −0,126 | −4,3 [−9,2 ; +0,1] ; −0,073 | +2,13 | +0,00 / +0,00 | 2/6 | 2/6 |
| Tous, H = 26 | −2,48 ; +0,034 | −19,01 ; −0,309 | −10,7 [−20,4 ; −2,9] ; −0,138 | +8,26 | +0,00 / +0,00 | 1/6 | 1/6 |
| Tous, H = 48 | −3,31 ; −0,126 | −27,43 ; −0,436 | −15,4 [−31,2 ; +0,8] ; −0,281 | +12,06 | +0,00 / +0,00 | 1/6 | 1/6 |

**10 bps aller-retour — 8 métriques**

| Configuration | PnL net : composé ; bps cumulés | PF | WR | Espérance : bps [IC 95 %] ; ATR | Max DD : valorisé ; bps | Trades : n ; ignorés ; /mois | Durée méd. (barres) | Part des frais ; brut par trade (bps) |
|---|---|---|---|---|---|---|---|---|
| Ancre native P6.5d | −99,9 % ; −62417 | 0,829 | 40,9 % | −10,3 [−15,8 ; −4,7] ; −0,201 | −100,0 % ; −72667 | 6 037 ; 17 % ; 83,8 | 13 | sans objet (brut ≤ 0) ; −0,3 |
| Tous, H = 6 | −99,9 % ; −63447 | 0,778 | 42,6 % | −8,7 [−11,5 ; −5,9] ; −0,217 | −99,9 % ; −67567 | 7 296 ; 0 % ; 101,3 | 6 | 767 % ; +1,3 |
| Tous, H = 13 | −99,5 % ; −45684 | 0,837 | 45,3 % | −9,3 [−14,2 ; −4,9] ; −0,194 | −99,6 % ; −49530 | 4 905 ; 33 % ; 68,1 | 13 | > 1 000 % ; +0,7 |
| Tous, H = 26 | −99,6 % ; −48634 | 0,808 | 46,9 % | −15,8 [−25,5 ; −7,9] ; −0,258 | −99,8 % ; −52653 | 3 080 ; 58 % ; 42,8 | 26 | sans objet (brut ≤ 0) ; −5,8 |
| Tous, H = 48 | −99,2 % ; −39196 | 0,818 | 48,0 % | −21,0 [−37,1 ; −4,7] ; −0,408 | −99,6 % ; −47749 | 1 866 ; 74 % ; 25,9 | 48 | sans objet (brut ≤ 0) ; −11,0 |

**10 bps — Long / Short / timing (nets)**

| Configuration | Long : bps ; ATR | Short : bps ; ATR | Timing : bps [IC 95 %] ; ATR | Dérive (bps) | Écart à Tous, Long / Short (bps) | Années PnL > 0 | Années timing > 0 |
|---|---|---|---|---|---|---|---|
| Ancre native P6.5d | −4,59 ; −0,092 | −16,09 ; −0,310 | −10,3 [−15,8 ; −4,7] ; −0,201 | +5,75 | — | 1/6 | 1/6 |
| Tous, H = 6 | −7,82 ; −0,194 | −9,56 ; −0,240 | −8,7 [−11,5 ; −5,9] ; −0,217 | +0,87 | +0,00 / +0,00 | 0/6 | 0/6 |
| Tous, H = 13 | −7,15 ; −0,137 | −11,40 ; −0,249 | −9,3 [−14,2 ; −4,9] ; −0,193 | +2,13 | +0,00 / +0,00 | 0/6 | 0/6 |
| Tous, H = 26 | −7,48 ; −0,085 | −24,01 ; −0,429 | −15,7 [−25,4 ; −7,9] ; −0,257 | +8,26 | +0,00 / +0,00 | 0/6 | 0/6 |
| Tous, H = 48 | −8,31 ; −0,242 | −32,43 ; −0,558 | −20,4 [−36,2 ; −4,2] ; −0,400 | +12,06 | +0,00 / +0,00 | 1/6 | 1/6 |

## C. Palier 2 — Sous-ensemble cinématique à horizon fixe (sens du signal)

Contrôle : Tous au même horizon (première ligne de chaque tableau).

#### H = 6

**5 bps aller-retour — 8 métriques**

| Configuration | PnL net : composé ; bps cumulés | PF | WR | Espérance : bps [IC 95 %] ; ATR | Max DD : valorisé ; bps | Trades : n ; ignorés ; /mois | Durée méd. (barres) | Part des frais ; brut par trade (bps) |
|---|---|---|---|---|---|---|---|---|
| Tous | −95,7 % ; −26967 | 0,899 | 46,9 % | −3,7 [−6,5 ; −0,9] ; −0,095 | −97,8 % ; −34428 | 7 296 ; 0 % ; 101,3 | 6 | 383 % ; +1,3 |
| Tous hors R3 | −78,8 % ; −12568 | 0,928 | 48,2 % | −2,5 [−5,6 ; +0,6] ; −0,086 | −89,6 % ; −20340 | 4 949 ; 0 % ; 68,7 | 6 | 203 % ; +2,5 |
| Tous hors nis_z_100 Q4 | −71,0 % ; −9296 | 0,949 | 48,4 % | −1,7 [−4,9 ; +1,8] ; −0,071 | −86,9 % ; −17923 | 5 472 ; 0 % ; 76,0 | 6 | 151 % ; +3,3 |
| R1 | −32,5 % ; −2803 | 0,958 | 52,4 % | −1,4 [−5,9 ; +3,1] ; −0,044 | −48,5 % ; −6085 | 1 935 ; 0 % ; 26,9 | 6 | 141 % ; +3,6 |
| R2 | −46,0 % ; −4943 | 0,929 | 45,5 % | −2,6 [−7,8 ; +2,6] ; −0,097 | −68,8 % ; −10752 | 1 874 ; 0 % ; 26,0 | 6 | 212 % ; +2,4 |
| ↳ F2b · x1 déjà retourné | −21,5 % ; −1996 | 0,924 | 45,6 % | −2,5 [−9,8 ; +5,6] ; −0,086 | −40,8 % ; −4779 | 787 ; 0 % ; 10,9 | 6 | 203 % ; +2,5 |
| ↳ F3 · x1 déjà retourné | −31,2 % ; −2946 | 0,932 | 45,4 % | −2,7 [−10,1 ; +4,1] ; −0,105 | −54,1 % ; −7151 | 1 087 ; 0 % ; 15,1 | 6 | 218 % ; +2,3 |
| R3 | −79,8 % ; −14399 | 0,841 | 44,4 % | −6,1 [−10,6 ; −1,1] ; −0,114 | −87,1 % ; −19108 | 2 347 ; 0 % ; 32,6 | 6 | sans objet (brut ≤ 0) ; −1,1 |
| nis_z_100 Q4 | −85,2 % ; −17671 | 0,792 | 42,6 % | −9,7 [−14,5 ; −4,9] ; −0,165 | −87,1 % ; −19073 | 1 824 ; 0 % ; 25,3 | 6 | sans objet (brut ≤ 0) ; −4,7 |

**5 bps — Long / Short / timing (nets)**

| Configuration | Long : bps ; ATR | Short : bps ; ATR | Timing : bps [IC 95 %] ; ATR | Dérive (bps) | Écart à Tous, Long / Short (bps) | Années PnL > 0 | Années timing > 0 |
|---|---|---|---|---|---|---|---|
| Tous | −2,82 ; −0,072 | −4,56 ; −0,117 | −3,7 [−6,5 ; −0,9] ; −0,094 | +0,87 | +0,00 / +0,00 | 1/6 | 1/6 |
| Tous hors R3 | −0,41 ; −0,051 | −4,56 ; −0,118 | −2,5 [−5,5 ; +0,6] ; −0,085 | +2,08 | +2,42 / −0,00 | 1/6 | 1/6 |
| Tous hors nis_z_100 Q4 | −0,05 ; −0,019 | −3,34 ; −0,123 | −1,7 [−4,9 ; +1,8] ; −0,071 | +1,64 | +2,77 / +1,22 | 2/6 | 2/6 |
| R1 | +0,79 ; +0,033 | −3,27 ; −0,107 | −1,2 [−5,7 ; +3,4] ; −0,037 | +2,03 | +3,61 / +1,29 | 2/6 | 2/6 |
| R2 | −3,85 ; −0,146 | −1,37 ; −0,046 | −2,6 [−7,8 ; +2,7] ; −0,096 | −1,24 | −1,02 / +3,19 | 1/6 | 1/6 |
| ↳ F2b · x1 déjà retourné | −3,85 ; −0,141 | −1,26 ; −0,034 | −2,6 [−9,8 ; +5,4] ; −0,087 | −1,30 | −1,03 / +3,30 | 2/6 | 2/6 |
| ↳ F3 · x1 déjà retourné | −3,84 ; −0,150 | −1,45 ; −0,055 | −2,6 [−10,0 ; +4,5] ; −0,102 | −1,20 | −1,02 / +3,11 | 1/6 | 1/6 |
| R3 | −7,60 ; −0,113 | −4,55 ; −0,114 | −6,1 [−10,5 ; −1,1] ; −0,114 | −1,53 | −4,78 / +0,01 | 1/6 | 1/6 |
| nis_z_100 Q4 | −11,30 ; −0,233 | −8,14 ; −0,100 | −9,7 [−14,5 ; −4,9] ; −0,167 | −1,58 | −8,48 / −3,58 | 0/6 | 0/6 |

**10 bps aller-retour — 8 métriques**

| Configuration | PnL net : composé ; bps cumulés | PF | WR | Espérance : bps [IC 95 %] ; ATR | Max DD : valorisé ; bps | Trades : n ; ignorés ; /mois | Durée méd. (barres) | Part des frais ; brut par trade (bps) |
|---|---|---|---|---|---|---|---|---|
| Tous | −99,9 % ; −63447 | 0,778 | 42,6 % | −8,7 [−11,5 ; −5,9] ; −0,217 | −99,9 % ; −67567 | 7 296 ; 0 % ; 101,3 | 6 | 767 % ; +1,3 |
| Tous hors R3 | −98,2 % ; −37313 | 0,802 | 43,9 % | −7,5 [−10,6 ; −4,4] ; −0,210 | −98,5 % ; −39920 | 4 949 ; 0 % ; 68,7 | 6 | 406 % ; +2,5 |
| Tous hors nis_z_100 Q4 | −98,1 % ; −36656 | 0,813 | 43,5 % | −6,7 [−9,9 ; −3,2] ; −0,202 | −98,8 % ; −41109 | 5 472 ; 0 % ; 76,0 | 6 | 303 % ; +3,3 |
| R1 | −74,4 % ; −12478 | 0,826 | 48,6 % | −6,4 [−10,9 ; −1,9] ; −0,160 | −75,7 % ; −13060 | 1 935 ; 0 % ; 26,9 | 6 | 282 % ; +3,6 |
| R2 | −78,8 % ; −14313 | 0,810 | 40,9 % | −7,6 [−12,8 ; −2,4] ; −0,228 | −84,9 % ; −17973 | 1 874 ; 0 % ; 26,0 | 6 | 423 % ; +2,4 |
| ↳ F2b · x1 déjà retourné | −47,0 % ; −5931 | 0,793 | 40,7 % | −7,5 [−14,8 ; +0,6] ; −0,220 | −58,0 % ; −8294 | 787 ; 0 % ; 10,9 | 6 | 406 % ; +2,5 |
| ↳ F3 · x1 déjà retourné | −60,1 % ; −8381 | 0,820 | 41,1 % | −7,7 [−15,1 ; −0,9] ; −0,234 | −69,7 % ; −11178 | 1 087 ; 0 % ; 15,1 | 6 | 437 % ; +2,3 |
| R3 | −93,7 % ; −26134 | 0,732 | 40,0 % | −11,1 [−15,6 ; −6,1] ; −0,231 | −95,7 % ; −29871 | 2 347 ; 0 % ; 32,6 | 6 | sans objet (brut ≤ 0) ; −1,1 |
| nis_z_100 Q4 | −94,1 % ; −26791 | 0,704 | 40,1 % | −14,7 [−19,5 ; −9,9] ; −0,261 | −94,5 % ; −27638 | 1 824 ; 0 % ; 25,3 | 6 | sans objet (brut ≤ 0) ; −4,7 |

**10 bps — Long / Short / timing (nets)**

| Configuration | Long : bps ; ATR | Short : bps ; ATR | Timing : bps [IC 95 %] ; ATR | Dérive (bps) | Écart à Tous, Long / Short (bps) | Années PnL > 0 | Années timing > 0 |
|---|---|---|---|---|---|---|---|
| Tous | −7,82 ; −0,194 | −9,56 ; −0,240 | −8,7 [−11,5 ; −5,9] ; −0,217 | +0,87 | +0,00 / +0,00 | 0/6 | 0/6 |
| Tous hors R3 | −5,41 ; −0,177 | −9,56 ; −0,241 | −7,5 [−10,5 ; −4,4] ; −0,209 | +2,08 | +2,42 / −0,00 | 0/6 | 0/6 |
| Tous hors nis_z_100 Q4 | −5,05 ; −0,150 | −8,34 ; −0,254 | −6,7 [−9,9 ; −3,2] ; −0,202 | +1,64 | +2,77 / +1,22 | 1/6 | 1/6 |
| R1 | −4,21 ; −0,082 | −8,27 ; −0,223 | −6,2 [−10,7 ; −1,6] ; −0,152 | +2,03 | +3,61 / +1,29 | 1/6 | 1/6 |
| R2 | −8,85 ; −0,280 | −6,37 ; −0,174 | −7,6 [−12,8 ; −2,3] ; −0,227 | −1,24 | −1,02 / +3,19 | 1/6 | 1/6 |
| ↳ F2b · x1 déjà retourné | −8,85 ; −0,275 | −6,26 ; −0,167 | −7,6 [−14,8 ; +0,4] ; −0,221 | −1,30 | −1,03 / +3,30 | 1/6 | 1/6 |
| ↳ F3 · x1 déjà retourné | −8,84 ; −0,283 | −6,45 ; −0,181 | −7,6 [−15,0 ; −0,5] ; −0,232 | −1,20 | −1,02 / +3,11 | 1/6 | 1/6 |
| R3 | −12,60 ; −0,227 | −9,55 ; −0,236 | −11,1 [−15,5 ; −6,1] ; −0,232 | −1,53 | −4,78 / +0,01 | 0/6 | 0/6 |
| nis_z_100 Q4 | −16,30 ; −0,328 | −13,14 ; −0,197 | −14,7 [−19,5 ; −9,9] ; −0,263 | −1,58 | −8,48 / −3,58 | 0/6 | 0/6 |

#### H = 13

**5 bps aller-retour — 8 métriques**

| Configuration | PnL net : composé ; bps cumulés | PF | WR | Espérance : bps [IC 95 %] ; ATR | Max DD : valorisé ; bps | Trades : n ; ignorés ; /mois | Durée méd. (barres) | Part des frais ; brut par trade (bps) |
|---|---|---|---|---|---|---|---|---|
| Tous | −94,0 % ; −21159 | 0,921 | 48,0 % | −4,3 [−9,2 ; +0,1] ; −0,074 | −96,4 % ; −27407 | 4 905 ; 33 % ; 68,1 | 13 | 729 % ; +0,7 |
| Tous hors R3 | −76,1 % ; −9376 | 0,952 | 47,6 % | −2,6 [−7,7 ; +2,5] ; −0,062 | −85,8 % ; −16462 | 3 652 ; 26 % ; 50,7 | 13 | 206 % ; +2,4 |
| Tous hors nis_z_100 Q4 | −16,7 % ; +2977 | 1,015 | 48,7 % | +0,8 [−5,0 ; +6,1] ; +0,001 | −69,0 % ; −8647 | 3 946 ; 28 % ; 54,8 | 13 | 87 % ; +5,8 |
| R1 | −57,0 % ; −5908 | 0,937 | 49,8 % | −3,3 [−10,8 ; +4,3] ; −0,078 | −69,8 % ; −9958 | 1 801 ; 7 % ; 25,0 | 13 | 291 % ; +1,7 |
| R2 | −51,4 % ; −5005 | 0,944 | 45,6 % | −3,2 [−12,0 ; +5,4] ; −0,035 | −68,4 % ; −10017 | 1 574 ; 16 % ; 21,9 | 13 | 275 % ; +1,8 |
| ↳ F2b · x1 déjà retourné | 9,7 % ; +1834 | 1,050 | 46,7 % | +2,5 [−7,4 ; +12,9] ; +0,027 | −32,1 % ; −3317 | 735 ; 7 % ; 10,2 | 13 | 67 % ; +7,5 |
| ↳ F3 · x1 déjà retourné | −51,6 % ; −5781 | 0,905 | 45,3 % | −5,9 [−17,5 ; +5,6] ; −0,094 | −62,8 % ; −8632 | 981 ; 10 % ; 13,6 | 13 | sans objet (brut ≤ 0) ; −0,9 |
| R3 | −89,9 % ; −19852 | 0,837 | 45,3 % | −9,4 [−16,8 ; −1,5] ; −0,142 | −93,8 % ; −25106 | 2 103 ; 10 % ; 29,2 | 13 | sans objet (brut ≤ 0) ; −4,4 |
| nis_z_100 Q4 | −93,1 % ; −23930 | 0,764 | 45,3 % | −15,8 [−25,6 ; −6,8] ; −0,204 | −95,3 % ; −28222 | 1 516 ; 17 % ; 21,1 | 13 | sans objet (brut ≤ 0) ; −10,8 |

**5 bps — Long / Short / timing (nets)**

| Configuration | Long : bps ; ATR | Short : bps ; ATR | Timing : bps [IC 95 %] ; ATR | Dérive (bps) | Écart à Tous, Long / Short (bps) | Années PnL > 0 | Années timing > 0 |
|---|---|---|---|---|---|---|---|
| Tous | −2,15 ; −0,020 | −6,40 ; −0,126 | −4,3 [−9,2 ; +0,1] ; −0,073 | +2,13 | +0,00 / +0,00 | 2/6 | 2/6 |
| Tous hors R3 | −1,00 ; −0,013 | −3,99 ; −0,105 | −2,5 [−7,8 ; +2,7] ; −0,059 | +1,50 | +1,15 / +2,41 | 3/6 | 3/6 |
| Tous hors nis_z_100 Q4 | +5,52 ; +0,100 | −3,84 ; −0,094 | +0,8 [−4,9 ; +6,2] ; +0,003 | +4,68 | +7,67 / +2,56 | 3/6 | 3/6 |
| R1 | −2,69 ; −0,026 | −3,76 ; −0,121 | −3,2 [−11,0 ; +4,5] ; −0,073 | +0,53 | −0,54 / +2,64 | 1/6 | 1/6 |
| R2 | −2,45 ; −0,062 | −3,94 ; −0,008 | −3,2 [−12,0 ; +5,2] ; −0,035 | +0,75 | −0,30 / +2,46 | 2/6 | 2/6 |
| ↳ F2b · x1 déjà retourné | +3,69 ; +0,057 | +1,36 ; −0,002 | +2,5 [−7,5 ; +13,1] ; +0,027 | +1,16 | +5,84 / +7,76 | 3/6 | 4/6 |
| ↳ F3 · x1 déjà retourné | −5,47 ; −0,125 | −6,38 ; −0,058 | −5,9 [−17,5 ; +5,2] ; −0,092 | +0,46 | −3,32 / +0,02 | 2/6 | 2/6 |
| R3 | −6,05 ; −0,056 | −13,05 ; −0,232 | −9,6 [−17,1 ; −1,5] ; −0,144 | +3,50 | −3,91 / −6,65 | 1/6 | 1/6 |
| nis_z_100 Q4 | −19,96 ; −0,243 | −11,81 ; −0,166 | −15,9 [−25,6 ; −6,9] ; −0,205 | −4,07 | −17,81 / −5,41 | 2/6 | 2/6 |

**10 bps aller-retour — 8 métriques**

| Configuration | PnL net : composé ; bps cumulés | PF | WR | Espérance : bps [IC 95 %] ; ATR | Max DD : valorisé ; bps | Trades : n ; ignorés ; /mois | Durée méd. (barres) | Part des frais ; brut par trade (bps) |
|---|---|---|---|---|---|---|---|---|
| Tous | −99,5 % ; −45684 | 0,837 | 45,3 % | −9,3 [−14,2 ; −4,9] ; −0,194 | −99,6 % ; −49530 | 4 905 ; 33 % ; 68,1 | 13 | > 1 000 % ; +0,7 |
| Tous hors R3 | −96,2 % ; −27636 | 0,864 | 45,1 % | −7,6 [−12,7 ; −2,5] ; −0,184 | −97,0 % ; −30307 | 3 652 ; 26 % ; 50,7 | 13 | 411 % ; +2,4 |
| Tous hors nis_z_100 Q4 | −88,4 % ; −16753 | 0,918 | 45,9 % | −4,2 [−10,0 ; +1,1] ; −0,126 | −94,7 % ; −24975 | 3 946 ; 28 % ; 54,8 | 13 | 174 % ; +5,8 |
| R1 | −82,6 % ; −14913 | 0,848 | 46,7 % | −8,3 [−15,8 ; −0,7] ; −0,193 | −86,1 % ; −17349 | 1 801 ; 7 % ; 25,0 | 13 | 581 % ; +1,7 |
| R2 | −77,9 % ; −12875 | 0,863 | 43,1 % | −8,2 [−17,0 ; +0,4] ; −0,164 | −81,3 % ; −14609 | 1 574 ; 16 % ; 21,9 | 13 | 549 % ; +1,8 |
| ↳ F2b · x1 déjà retourné | −24,1 % ; −1841 | 0,952 | 44,1 % | −2,5 [−12,4 ; +7,9] ; −0,106 | −45,6 % ; −5467 | 735 ; 7 % ; 10,2 | 13 | 133 % ; +7,5 |
| ↳ F3 · x1 déjà retourné | −70,4 % ; −10686 | 0,831 | 42,7 % | −10,9 [−22,5 ; +0,6] ; −0,222 | −74,3 % ; −11925 | 981 ; 10 % ; 13,6 | 13 | sans objet (brut ≤ 0) ; −0,9 |
| R3 | −96,5 % ; −30367 | 0,763 | 43,0 % | −14,4 [−21,8 ; −6,5] ; −0,259 | −97,7 % ; −34701 | 2 103 ; 10 % ; 29,2 | 13 | sans objet (brut ≤ 0) ; −4,4 |
| nis_z_100 Q4 | −96,8 % ; −31510 | 0,702 | 43,3 % | −20,8 [−30,6 ; −11,8] ; −0,300 | −97,3 % ; −33483 | 1 516 ; 17 % ; 21,1 | 13 | sans objet (brut ≤ 0) ; −10,8 |

**10 bps — Long / Short / timing (nets)**

| Configuration | Long : bps ; ATR | Short : bps ; ATR | Timing : bps [IC 95 %] ; ATR | Dérive (bps) | Écart à Tous, Long / Short (bps) | Années PnL > 0 | Années timing > 0 |
|---|---|---|---|---|---|---|---|
| Tous | −7,15 ; −0,137 | −11,40 ; −0,249 | −9,3 [−14,2 ; −4,9] ; −0,193 | +2,13 | +0,00 / +0,00 | 0/6 | 0/6 |
| Tous hors R3 | −6,00 ; −0,136 | −8,99 ; −0,227 | −7,5 [−12,8 ; −2,3] ; −0,181 | +1,50 | +1,15 / +2,41 | 0/6 | 0/6 |
| Tous hors nis_z_100 Q4 | +0,52 ; −0,025 | −8,84 ; −0,222 | −4,2 [−9,9 ; +1,2] ; −0,124 | +4,68 | +7,67 / +2,56 | 1/6 | 1/6 |
| R1 | −7,69 ; −0,139 | −8,76 ; −0,237 | −8,2 [−16,0 ; −0,5] ; −0,188 | +0,53 | −0,54 / +2,64 | 0/6 | 1/6 |
| R2 | −7,45 ; −0,193 | −8,94 ; −0,134 | −8,2 [−17,0 ; +0,2] ; −0,164 | +0,75 | −0,30 / +2,46 | 1/6 | 1/6 |
| ↳ F2b · x1 déjà retourné | −1,31 ; −0,077 | −3,64 ; −0,133 | −2,5 [−12,5 ; +8,1] ; −0,105 | +1,16 | +5,84 / +7,76 | 2/6 | 2/6 |
| ↳ F3 · x1 déjà retourné | −10,47 ; −0,256 | −11,38 ; −0,182 | −10,9 [−22,5 ; +0,2] ; −0,219 | +0,46 | −3,32 / +0,02 | 0/6 | 0/6 |
| R3 | −11,05 ; −0,168 | −18,05 ; −0,356 | −14,6 [−22,1 ; −6,5] ; −0,262 | +3,50 | −3,91 / −6,65 | 0/6 | 0/6 |
| nis_z_100 Q4 | −24,96 ; −0,337 | −16,81 ; −0,266 | −20,9 [−30,6 ; −11,9] ; −0,301 | −4,07 | −17,81 / −5,41 | 1/6 | 1/6 |

#### H = 26

**5 bps aller-retour — 8 métriques**

| Configuration | PnL net : composé ; bps cumulés | PF | WR | Espérance : bps [IC 95 %] ; ATR | Max DD : valorisé ; bps | Trades : n ; ignorés ; /mois | Durée méd. (barres) | Part des frais ; brut par trade (bps) |
|---|---|---|---|---|---|---|---|---|
| Tous | −98,4 % ; −33234 | 0,864 | 48,5 % | −10,8 [−20,5 ; −2,9] ; −0,138 | −99,1 % ; −39987 | 3 080 ; 58 % ; 42,8 | 26 | sans objet (brut ≤ 0) ; −5,8 |
| Tous hors R3 | −90,1 % ; −16234 | 0,920 | 48,7 % | −6,3 [−14,6 ; +1,8] ; −0,115 | −96,0 % ; −26670 | 2 572 ; 48 % ; 35,7 | 26 | sans objet (brut ≤ 0) ; −1,3 |
| Tous hors nis_z_100 Q4 | −33,2 % ; +2658 | 1,014 | 50,0 % | +1,0 [−7,2 ; +9,0] ; +0,001 | −84,3 % ; −15591 | 2 633 ; 52 % ; 36,6 | 26 | 83 % ; +6,0 |
| R1 | −90,8 % ; −19756 | 0,838 | 51,1 % | −13,4 [−24,5 ; −2,1] ; −0,236 | −92,7 % ; −22393 | 1 477 ; 24 % ; 20,5 | 26 | sans objet (brut ≤ 0) ; −8,4 |
| R2 | −7,1 % ; +2994 | 1,028 | 48,0 % | +2,2 [−9,6 ; +14,0] ; +0,126 | −58,2 % ; −7113 | 1 353 ; 28 % ; 18,8 | 26 | 69 % ; +7,2 |
| ↳ F2b · x1 déjà retourné | 34,7 % ; +4675 | 1,098 | 48,8 % | +6,9 [−7,5 ; +21,2] ; +0,300 | −44,6 % ; −5260 | 676 ; 14 % ; 9,4 | 26 | 42 % ; +11,9 |
| ↳ F3 · x1 déjà retourné | −22,0 % ; +247 | 1,003 | 47,0 % | +0,3 [−17,5 ; +17,4] ; −0,046 | −70,9 % ; −10277 | 902 ; 17 % ; 12,5 | 26 | 95 % ; +5,3 |
| R3 | −97,7 % ; −33976 | 0,754 | 44,5 % | −20,3 [−29,8 ; −11,3] ; −0,343 | −98,5 % ; −37392 | 1 674 ; 29 % ; 23,2 | 26 | sans objet (brut ≤ 0) ; −15,3 |
| nis_z_100 Q4 | −94,4 % ; −24690 | 0,790 | 45,7 % | −20,1 [−35,3 ; −4,4] ; −0,328 | −95,4 % ; −27374 | 1 231 ; 33 % ; 17,1 | 26 | sans objet (brut ≤ 0) ; −15,1 |

**5 bps — Long / Short / timing (nets)**

| Configuration | Long : bps ; ATR | Short : bps ; ATR | Timing : bps [IC 95 %] ; ATR | Dérive (bps) | Écart à Tous, Long / Short (bps) | Années PnL > 0 | Années timing > 0 |
|---|---|---|---|---|---|---|---|
| Tous | −2,48 ; +0,034 | −19,01 ; −0,309 | −10,7 [−20,4 ; −2,9] ; −0,138 | +8,26 | +0,00 / +0,00 | 1/6 | 1/6 |
| Tous hors R3 | +8,35 ; +0,174 | −19,48 ; −0,375 | −5,6 [−13,7 ; +2,6] ; −0,100 | +13,91 | +10,83 / −0,47 | 2/6 | 2/6 |
| Tous hors nis_z_100 Q4 | +13,31 ; +0,248 | −11,22 ; −0,245 | +1,0 [−7,3 ; +8,8] ; +0,002 | +12,27 | +15,79 / +7,79 | 4/6 | 4/6 |
| R1 | −3,75 ; −0,007 | −20,90 ; −0,415 | −12,3 [−23,0 ; −1,5] ; −0,211 | +8,57 | −1,27 / −1,88 | 1/6 | 2/6 |
| R2 | +6,85 ; +0,227 | −2,73 ; +0,018 | +2,1 [−9,9 ; +13,4] ; +0,123 | +4,79 | +9,33 / +16,28 | 4/6 | 4/6 |
| ↳ F2b · x1 déjà retourné | +11,59 ; +0,517 | +2,46 ; +0,092 | +7,0 [−7,7 ; +21,4] ; +0,305 | +4,56 | +14,07 / +21,47 | 4/6 | 4/6 |
| ↳ F3 · x1 déjà retourné | +1,64 ; −0,023 | −1,30 ; −0,074 | +0,2 [−17,1 ; +16,6] ; −0,048 | +1,47 | +4,12 / +17,71 | 3/6 | 3/6 |
| R3 | −16,20 ; −0,315 | −24,60 ; −0,373 | −20,4 [−30,0 ; −11,3] ; −0,344 | +4,20 | −13,72 / −5,59 | 0/6 | 0/6 |
| nis_z_100 Q4 | −12,79 ; −0,268 | −26,75 ; −0,383 | −19,8 [−35,3 ; −4,3] ; −0,326 | +6,98 | −10,30 / −7,74 | 2/6 | 2/6 |

**10 bps aller-retour — 8 métriques**

| Configuration | PnL net : composé ; bps cumulés | PF | WR | Espérance : bps [IC 95 %] ; ATR | Max DD : valorisé ; bps | Trades : n ; ignorés ; /mois | Durée méd. (barres) | Part des frais ; brut par trade (bps) |
|---|---|---|---|---|---|---|---|---|
| Tous | −99,6 % ; −48634 | 0,808 | 46,9 % | −15,8 [−25,5 ; −7,9] ; −0,258 | −99,8 % ; −52653 | 3 080 ; 58 % ; 42,8 | 26 | sans objet (brut ≤ 0) ; −5,8 |
| Tous hors R3 | −97,3 % ; −29094 | 0,861 | 46,5 % | −11,3 [−19,6 ; −3,2] ; −0,236 | −98,4 % ; −34869 | 2 572 ; 48 % ; 35,7 | 26 | sans objet (brut ≤ 0) ; −1,3 |
| Tous hors nis_z_100 Q4 | −82,1 % ; −10507 | 0,947 | 47,9 % | −4,0 [−12,2 ; +4,0] ; −0,124 | −92,8 % ; −22756 | 2 633 ; 52 % ; 36,6 | 26 | 166 % ; +6,0 |
| R1 | −95,6 % ; −27141 | 0,784 | 49,4 % | −18,4 [−29,5 ; −7,1] ; −0,351 | −96,1 % ; −28483 | 1 477 ; 24 % ; 20,5 | 26 | sans objet (brut ≤ 0) ; −8,4 |
| R2 | −52,8 % ; −3771 | 0,966 | 46,3 % | −2,8 [−14,6 ; +9,0] ; −0,003 | −71,0 % ; −9825 | 1 353 ; 28 % ; 18,8 | 26 | 139 % ; +7,2 |
| ↳ F2b · x1 déjà retourné | −3,9 % ; +1295 | 1,026 | 47,3 % | +1,9 [−12,5 ; +16,2] ; +0,168 | −49,4 % ; −5895 | 676 ; 14 % ; 9,4 | 26 | 84 % ; +11,9 |
| ↳ F3 · x1 déjà retourné | −50,3 % ; −4263 | 0,946 | 45,5 % | −4,7 [−22,5 ; +12,4] ; −0,174 | −77,6 % ; −12897 | 902 ; 17 % ; 12,5 | 26 | 190 % ; +5,3 |
| R3 | −99,0 % ; −42346 | 0,703 | 42,8 % | −25,3 [−34,8 ; −16,3] ; −0,460 | −99,2 % ; −44352 | 1 674 ; 29 % ; 23,2 | 26 | sans objet (brut ≤ 0) ; −15,3 |
| nis_z_100 Q4 | −97,0 % ; −30845 | 0,745 | 44,1 % | −25,1 [−40,3 ; −9,4] ; −0,425 | −97,2 % ; −31769 | 1 231 ; 33 % ; 17,1 | 26 | sans objet (brut ≤ 0) ; −15,1 |

**10 bps — Long / Short / timing (nets)**

| Configuration | Long : bps ; ATR | Short : bps ; ATR | Timing : bps [IC 95 %] ; ATR | Dérive (bps) | Écart à Tous, Long / Short (bps) | Années PnL > 0 | Années timing > 0 |
|---|---|---|---|---|---|---|---|
| Tous | −7,48 ; −0,085 | −24,01 ; −0,429 | −15,7 [−25,4 ; −7,9] ; −0,257 | +8,26 | +0,00 / +0,00 | 0/6 | 0/6 |
| Tous hors R3 | +3,35 ; +0,051 | −24,48 ; −0,494 | −10,6 [−18,7 ; −2,4] ; −0,221 | +13,91 | +10,83 / −0,47 | 1/6 | 1/6 |
| Tous hors nis_z_100 Q4 | +8,31 ; +0,124 | −16,22 ; −0,370 | −4,0 [−12,3 ; +3,8] ; −0,123 | +12,27 | +15,79 / +7,79 | 2/6 | 2/6 |
| R1 | −8,75 ; −0,120 | −25,90 ; −0,531 | −17,3 [−28,0 ; −6,5] ; −0,325 | +8,57 | −1,27 / −1,88 | 1/6 | 1/6 |
| R2 | +1,85 ; +0,097 | −7,73 ; −0,109 | −2,9 [−14,9 ; +8,4] ; −0,006 | +4,79 | +9,33 / +16,28 | 1/6 | 1/6 |
| ↳ F2b · x1 déjà retourné | +6,59 ; +0,381 | −2,54 ; −0,036 | +2,0 [−12,7 ; +16,4] ; +0,173 | +4,56 | +14,07 / +21,47 | 4/6 | 4/6 |
| ↳ F3 · x1 déjà retourné | −3,36 ; −0,152 | −6,30 ; −0,199 | −4,8 [−22,1 ; +11,6] ; −0,175 | +1,47 | +4,12 / +17,71 | 3/6 | 3/6 |
| R3 | −21,20 ; −0,428 | −29,60 ; −0,495 | −25,4 [−35,0 ; −16,3] ; −0,461 | +4,20 | −13,72 / −5,59 | 0/6 | 0/6 |
| nis_z_100 Q4 | −17,79 ; −0,364 | −31,75 ; −0,482 | −24,8 [−40,3 ; −9,3] ; −0,423 | +6,98 | −10,30 / −7,74 | 1/6 | 1/6 |

#### H = 48

**5 bps aller-retour — 8 métriques**

| Configuration | PnL net : composé ; bps cumulés | PF | WR | Espérance : bps [IC 95 %] ; ATR | Max DD : valorisé ; bps | Trades : n ; ignorés ; /mois | Durée méd. (barres) | Part des frais ; brut par trade (bps) |
|---|---|---|---|---|---|---|---|---|
| Tous | −98,1 % ; −29866 | 0,858 | 49,0 % | −16,0 [−32,1 ; +0,3] ; −0,289 | −99,2 % ; −40174 | 1 866 ; 74 % ; 25,9 | 48 | sans objet (brut ≤ 0) ; −11,0 |
| Tous hors R3 | −41,2 % ; +2823 | 1,016 | 49,6 % | +1,7 [−11,5 ; +15,2] ; +0,200 | −92,4 % ; −20663 | 1 657 ; 67 % ; 23,0 | 48 | 75 % ; +6,7 |
| Tous hors nis_z_100 Q4 | −19,8 % ; +6371 | 1,036 | 50,7 % | +3,8 [−10,4 ; +17,4] ; −0,158 | −62,7 % ; −7307 | 1 695 ; 69 % ; 23,5 | 48 | 57 % ; +8,8 |
| R1 | −75,4 % ; −7738 | 0,940 | 50,5 % | −6,9 [−22,9 ; +11,8] ; −0,100 | −87,0 % ; −14495 | 1 128 ; 42 % ; 15,7 | 48 | sans objet (brut ≤ 0) ; −1,9 |
| R2 | −51,7 % ; −1938 | 0,983 | 46,4 % | −1,8 [−18,7 ; +16,4] ; +0,066 | −77,7 % ; −12099 | 1 050 ; 44 % ; 14,6 | 48 | 159 % ; +3,2 |
| ↳ F2b · x1 déjà retourné | −12,9 % ; +1330 | 1,022 | 47,8 % | +2,2 [−20,6 ; +25,3] ; +0,194 | −57,6 % ; −7545 | 594 ; 25 % ; 8,2 | 48 | 69 % ; +7,2 |
| ↳ F3 · x1 déjà retourné | −23,4 % ; +1457 | 1,018 | 49,1 % | +2,0 [−21,8 ; +25,0] ; +0,116 | −67,8 % ; −9755 | 745 ; 31 % ; 10,3 | 48 | 72 % ; +7,0 |
| R3 | −91,8 % ; −19000 | 0,859 | 47,8 % | −15,4 [−30,8 ; +1,2] ; −0,415 | −96,7 % ; −28864 | 1 235 ; 47 % ; 17,2 | 48 | sans objet (brut ≤ 0) ; −10,4 |
| nis_z_100 Q4 | −57,0 % ; −3129 | 0,971 | 47,9 % | −3,3 [−23,9 ; +19,2] ; −0,042 | −79,3 % ; −11935 | 952 ; 48 % ; 13,2 | 48 | 292 % ; +1,7 |

**5 bps — Long / Short / timing (nets)**

| Configuration | Long : bps ; ATR | Short : bps ; ATR | Timing : bps [IC 95 %] ; ATR | Dérive (bps) | Écart à Tous, Long / Short (bps) | Années PnL > 0 | Années timing > 0 |
|---|---|---|---|---|---|---|---|
| Tous | −3,31 ; −0,126 | −27,43 ; −0,436 | −15,4 [−31,2 ; +0,8] ; −0,281 | +12,06 | +0,00 / +0,00 | 1/6 | 1/6 |
| Tous hors R3 | +15,82 ; +0,485 | −11,41 ; −0,063 | +2,2 [−11,3 ; +15,6] ; +0,211 | +13,61 | +19,13 / +16,02 | 5/6 | 5/6 |
| Tous hors nis_z_100 Q4 | +21,29 ; +0,089 | −12,36 ; −0,385 | +4,5 [−9,4 ; +18,3] ; −0,148 | +16,83 | +24,60 / +15,07 | 4/6 | 4/6 |
| R1 | +2,16 ; −0,052 | −14,04 ; −0,139 | −5,9 [−21,7 ; +13,2] ; −0,095 | +8,10 | +5,47 / +13,39 | 3/6 | 3/6 |
| R2 | +9,39 ; +0,284 | −13,74 ; −0,164 | −2,2 [−19,0 ; +15,5] ; +0,060 | +11,57 | +12,70 / +13,69 | 3/6 | 3/6 |
| ↳ F2b · x1 déjà retourné | +17,08 ; +0,699 | −11,82 ; −0,285 | +2,6 [−20,3 ; +26,4] ; +0,207 | +14,45 | +20,39 / +15,61 | 3/6 | 4/6 |
| ↳ F3 · x1 déjà retourné | −4,64 ; −0,095 | +9,81 ; +0,369 | +2,6 [−20,7 ; +23,9] ; +0,137 | −7,23 | −1,33 / +37,24 | 3/6 | 3/6 |
| R3 | −0,52 ; −0,017 | −30,28 ; −0,814 | −15,4 [−30,4 ; +1,2] ; −0,415 | +14,88 | +2,80 / −2,85 | 1/6 | 1/6 |
| nis_z_100 Q4 | +5,28 ; +0,048 | −11,19 ; −0,124 | −3,0 [−23,4 ; +19,1] ; −0,038 | +8,24 | +8,59 / +16,24 | 3/6 | 4/6 |

**10 bps aller-retour — 8 métriques**

| Configuration | PnL net : composé ; bps cumulés | PF | WR | Espérance : bps [IC 95 %] ; ATR | Max DD : valorisé ; bps | Trades : n ; ignorés ; /mois | Durée méd. (barres) | Part des frais ; brut par trade (bps) |
|---|---|---|---|---|---|---|---|---|
| Tous | −99,2 % ; −39196 | 0,818 | 48,0 % | −21,0 [−37,1 ; −4,7] ; −0,408 | −99,6 % ; −47749 | 1 866 ; 74 % ; 25,9 | 48 | sans objet (brut ≤ 0) ; −11,0 |
| Tous hors R3 | −74,4 % ; −5462 | 0,970 | 48,9 % | −3,3 [−16,5 ; +10,2] ; +0,079 | −94,5 % ; −23813 | 1 657 ; 67 % ; 23,0 | 48 | 149 % ; +6,7 |
| Tous hors nis_z_100 Q4 | −65,7 % ; −2104 | 0,988 | 49,3 % | −1,2 [−15,4 ; +12,4] ; −0,282 | −77,7 % ; −10006 | 1 695 ; 69 % ; 23,5 | 48 | 114 % ; +8,8 |
| R1 | −86,0 % ; −13378 | 0,898 | 49,6 % | −11,9 [−27,9 ; +6,8] ; −0,217 | −91,9 % ; −19117 | 1 128 ; 42 % ; 15,7 | 48 | sans objet (brut ≤ 0) ; −1,9 |
| R2 | −71,4 % ; −7188 | 0,939 | 45,2 % | −6,8 [−23,7 ; +11,4] ; −0,062 | −83,7 % ; −14943 | 1 050 ; 44 % ; 14,6 | 48 | 317 % ; +3,2 |
| ↳ F2b · x1 déjà retourné | −35,3 % ; −1640 | 0,974 | 46,0 % | −2,8 [−25,6 ; +20,3] ; +0,062 | −62,4 % ; −7815 | 594 ; 25 % ; 8,2 | 48 | 138 % ; +7,2 |
| ↳ F3 · x1 déjà retourné | −47,2 % ; −2268 | 0,973 | 47,9 % | −3,0 [−26,8 ; +20,0] ; −0,009 | −74,6 % ; −10755 | 745 ; 31 % ; 10,3 | 48 | 144 % ; +7,0 |
| R3 | −95,6 % ; −25175 | 0,817 | 46,6 % | −20,4 [−35,8 ; −3,8] ; −0,531 | −98,2 % ; −34759 | 1 235 ; 47 % ; 17,2 | 48 | sans objet (brut ≤ 0) ; −10,4 |
| nis_z_100 Q4 | −73,3 % ; −7889 | 0,929 | 47,5 % | −8,3 [−28,9 ; +14,2] ; −0,140 | −85,4 % ; −15240 | 952 ; 48 % ; 13,2 | 48 | 584 % ; +1,7 |

**10 bps — Long / Short / timing (nets)**

| Configuration | Long : bps ; ATR | Short : bps ; ATR | Timing : bps [IC 95 %] ; ATR | Dérive (bps) | Écart à Tous, Long / Short (bps) | Années PnL > 0 | Années timing > 0 |
|---|---|---|---|---|---|---|---|
| Tous | −8,31 ; −0,242 | −32,43 ; −0,558 | −20,4 [−36,2 ; −4,2] ; −0,400 | +12,06 | +0,00 / +0,00 | 1/6 | 1/6 |
| Tous hors R3 | +10,82 ; +0,360 | −16,41 ; −0,181 | −2,8 [−16,3 ; +10,6] ; +0,089 | +13,61 | +19,13 / +16,02 | 3/6 | 4/6 |
| Tous hors nis_z_100 Q4 | +16,29 ; −0,035 | −17,36 ; −0,509 | −0,5 [−14,4 ; +13,3] ; −0,272 | +16,83 | +24,60 / +15,07 | 3/6 | 3/6 |
| R1 | −2,84 ; −0,169 | −19,04 ; −0,255 | −10,9 [−26,7 ; +8,2] ; −0,212 | +8,10 | +5,47 / +13,39 | 1/6 | 2/6 |
| R2 | +4,39 ; +0,154 | −18,74 ; −0,290 | −7,2 [−24,0 ; +10,5] ; −0,068 | +11,57 | +12,70 / +13,69 | 2/6 | 2/6 |
| ↳ F2b · x1 déjà retourné | +12,08 ; +0,567 | −16,82 ; −0,416 | −2,4 [−25,3 ; +21,4] ; +0,075 | +14,45 | +20,39 / +15,61 | 3/6 | 3/6 |
| ↳ F3 · x1 déjà retourné | −9,64 ; −0,221 | +4,81 ; +0,244 | −2,4 [−25,7 ; +18,9] ; +0,011 | −7,23 | −1,33 / +37,24 | 3/6 | 3/6 |
| R3 | −5,52 ; −0,128 | −35,28 ; −0,935 | −20,4 [−35,4 ; −3,8] ; −0,531 | +14,88 | +2,80 / −2,85 | 1/6 | 1/6 |
| nis_z_100 Q4 | +0,28 ; −0,047 | −16,19 ; −0,226 | −8,0 [−28,4 ; +14,1] ; −0,136 | +8,24 | +8,59 / +16,24 | 2/6 | 2/6 |

## D. Palier 3 — Ablation et inversion d'un seul facteur

Chaque variante suit immédiatement son contrôle du palier 2.

### 3A. Éviction de nis_z_100 Q4

#### H = 6

**5 bps aller-retour — 8 métriques**

| Configuration | PnL net : composé ; bps cumulés | PF | WR | Espérance : bps [IC 95 %] ; ATR | Max DD : valorisé ; bps | Trades : n ; ignorés ; /mois | Durée méd. (barres) | Part des frais ; brut par trade (bps) |
|---|---|---|---|---|---|---|---|---|
| Tous hors R3 | −78,8 % ; −12568 | 0,928 | 48,2 % | −2,5 [−5,6 ; +0,6] ; −0,086 | −89,6 % ; −20340 | 4 949 ; 0 % ; 68,7 | 6 | 203 % ; +2,5 |
| Tous hors R3 et hors nis_z_100 Q4 | −53,8 % ; −5454 | 0,960 | 48,9 % | −1,3 [−4,6 ; +2,1] ; −0,069 | −74,9 % ; −12095 | 4 066 ; 0 % ; 56,5 | 6 | 137 % ; +3,7 |
| R1 | −32,5 % ; −2803 | 0,958 | 52,4 % | −1,4 [−5,9 ; +3,1] ; −0,044 | −48,5 % ; −6085 | 1 935 ; 0 % ; 26,9 | 6 | 141 % ; +3,6 |
| R1 hors nis_z_100 Q4 | −8,2 % ; +34 | 1,001 | 53,5 % | +0,0 [−5,3 ; +4,9] ; −0,031 | −40,7 % ; −4663 | 1 592 ; 0 % ; 22,1 | 6 | 100 % ; +5,0 |
| R2 | −46,0 % ; −4943 | 0,929 | 45,5 % | −2,6 [−7,8 ; +2,6] ; −0,097 | −68,8 % ; −10752 | 1 874 ; 0 % ; 26,0 | 6 | 212 % ; +2,4 |
| R2 hors nis_z_100 Q4 | −35,7 % ; −3556 | 0,928 | 45,7 % | −2,4 [−8,3 ; +4,0] ; −0,091 | −61,0 % ; −8799 | 1 452 ; 0 % ; 20,2 | 6 | 196 % ; +2,6 |
| ↳ F2b · x1 déjà retourné | −21,5 % ; −1996 | 0,924 | 45,6 % | −2,5 [−9,8 ; +5,6] ; −0,086 | −40,8 % ; −4779 | 787 ; 0 % ; 10,9 | 6 | 203 % ; +2,5 |
| ↳ F2b · x1 déjà retourné hors nis_z_100 Q4 | −15,4 % ; −1284 | 0,946 | 45,9 % | −1,7 [−9,5 ; +7,0] ; −0,085 | −38,3 % ; −4398 | 741 ; 0 % ; 10,3 | 6 | 153 % ; +3,3 |
| ↳ F3 · x1 déjà retourné | −31,2 % ; −2946 | 0,932 | 45,4 % | −2,7 [−10,1 ; +4,1] ; −0,105 | −54,1 % ; −7151 | 1 087 ; 0 % ; 15,1 | 6 | 218 % ; +2,3 |
| ↳ F3 · x1 déjà retourné hors nis_z_100 Q4 | −23,9 % ; −2273 | 0,912 | 45,4 % | −3,2 [−12,3 ; +5,3] ; −0,097 | −42,1 % ; −5044 | 711 ; 0 % ; 9,9 | 6 | 277 % ; +1,8 |

**5 bps — Long / Short / timing (nets)**

| Configuration | Long : bps ; ATR | Short : bps ; ATR | Timing : bps [IC 95 %] ; ATR | Dérive (bps) | Écart à Tous, Long / Short (bps) | Années PnL > 0 | Années timing > 0 |
|---|---|---|---|---|---|---|---|
| Tous hors R3 | −0,41 ; −0,051 | −4,56 ; −0,118 | −2,5 [−5,5 ; +0,6] ; −0,085 | +2,08 | +2,42 / −0,00 | 1/6 | 1/6 |
| Tous hors R3 et hors nis_z_100 Q4 | +1,31 ; −0,006 | −3,91 ; −0,131 | −1,3 [−4,6 ; +2,2] ; −0,068 | +2,61 | +4,14 / +0,65 | 2/6 | 2/6 |
| R1 | +0,79 ; +0,033 | −3,27 ; −0,107 | −1,2 [−5,7 ; +3,4] ; −0,037 | +2,03 | +3,61 / +1,29 | 2/6 | 2/6 |
| R1 hors nis_z_100 Q4 | +0,89 ; +0,048 | −0,67 ; −0,094 | +0,1 [−5,3 ; +5,2] ; −0,023 | +0,78 | +3,72 / +3,89 | 2/6 | 3/6 |
| R2 | −3,85 ; −0,146 | −1,37 ; −0,046 | −2,6 [−7,8 ; +2,7] ; −0,096 | −1,24 | −1,02 / +3,19 | 1/6 | 1/6 |
| R2 hors nis_z_100 Q4 | −2,55 ; −0,106 | −2,33 ; −0,074 | −2,4 [−8,3 ; +4,3] ; −0,090 | −0,11 | +0,27 / +2,23 | 3/6 | 3/6 |
| ↳ F2b · x1 déjà retourné | −3,85 ; −0,141 | −1,26 ; −0,034 | −2,6 [−9,8 ; +5,4] ; −0,087 | −1,30 | −1,03 / +3,30 | 2/6 | 2/6 |
| ↳ F2b · x1 déjà retourné hors nis_z_100 Q4 | −3,28 ; −0,134 | −0,18 ; −0,035 | −1,7 [−9,4 ; +7,1] ; −0,085 | −1,55 | −0,46 / +4,38 | 2/6 | 2/6 |
| ↳ F3 · x1 déjà retourné | −3,84 ; −0,150 | −1,45 ; −0,055 | −2,6 [−10,0 ; +4,5] ; −0,102 | −1,20 | −1,02 / +3,11 | 1/6 | 1/6 |
| ↳ F3 · x1 déjà retourné hors nis_z_100 Q4 | −1,87 ; −0,080 | −4,87 ; −0,119 | −3,4 [−12,7 ; +5,2] ; −0,100 | +1,50 | +0,95 / −0,32 | 2/6 | 2/6 |

**10 bps aller-retour — 8 métriques**

| Configuration | PnL net : composé ; bps cumulés | PF | WR | Espérance : bps [IC 95 %] ; ATR | Max DD : valorisé ; bps | Trades : n ; ignorés ; /mois | Durée méd. (barres) | Part des frais ; brut par trade (bps) |
|---|---|---|---|---|---|---|---|---|
| Tous hors R3 | −98,2 % ; −37313 | 0,802 | 43,9 % | −7,5 [−10,6 ; −4,4] ; −0,210 | −98,5 % ; −39920 | 4 949 ; 0 % ; 68,7 | 6 | 406 % ; +2,5 |
| Tous hors R3 et hors nis_z_100 Q4 | −94,0 % ; −25784 | 0,823 | 44,1 % | −6,3 [−9,6 ; −2,9] ; −0,200 | −95,3 % ; −28365 | 4 066 ; 0 % ; 56,5 | 6 | 273 % ; +3,7 |
| R1 | −74,4 % ; −12478 | 0,826 | 48,6 % | −6,4 [−10,9 ; −1,9] ; −0,160 | −75,7 % ; −13060 | 1 935 ; 0 % ; 26,9 | 6 | 282 % ; +3,6 |
| R1 hors nis_z_100 Q4 | −58,6 % ; −7926 | 0,859 | 49,5 % | −5,0 [−10,3 ; −0,1] ; −0,152 | −64,5 % ; −9492 | 1 592 ; 0 % ; 22,1 | 6 | 199 % ; +5,0 |
| R2 | −78,8 % ; −14313 | 0,810 | 40,9 % | −7,6 [−12,8 ; −2,4] ; −0,228 | −84,9 % ; −17973 | 1 874 ; 0 % ; 26,0 | 6 | 423 % ; +2,4 |
| R2 hors nis_z_100 Q4 | −68,9 % ; −10816 | 0,799 | 40,1 % | −7,4 [−13,3 ; −1,0] ; −0,232 | −77,4 % ; −14204 | 1 452 ; 0 % ; 20,2 | 6 | 392 % ; +2,6 |
| ↳ F2b · x1 déjà retourné | −47,0 % ; −5931 | 0,793 | 40,7 % | −7,5 [−14,8 ; +0,6] ; −0,220 | −58,0 % ; −8294 | 787 ; 0 % ; 10,9 | 6 | 406 % ; +2,5 |
| ↳ F2b · x1 déjà retourné hors nis_z_100 Q4 | −41,6 % ; −4989 | 0,808 | 40,6 % | −6,7 [−14,5 ; +2,0] ; −0,221 | −54,8 % ; −7571 | 741 ; 0 % ; 10,3 | 6 | 306 % ; +3,3 |
| ↳ F3 · x1 déjà retourné | −60,1 % ; −8381 | 0,820 | 41,1 % | −7,7 [−15,1 ; −0,9] ; −0,234 | −69,7 % ; −11178 | 1 087 ; 0 % ; 15,1 | 6 | 437 % ; +2,3 |
| ↳ F3 · x1 déjà retourné hors nis_z_100 Q4 | −46,7 % ; −5828 | 0,790 | 39,5 % | −8,2 [−17,3 ; +0,3] ; −0,242 | −55,2 % ; −7641 | 711 ; 0 % ; 9,9 | 6 | 554 % ; +1,8 |

**10 bps — Long / Short / timing (nets)**

| Configuration | Long : bps ; ATR | Short : bps ; ATR | Timing : bps [IC 95 %] ; ATR | Dérive (bps) | Écart à Tous, Long / Short (bps) | Années PnL > 0 | Années timing > 0 |
|---|---|---|---|---|---|---|---|
| Tous hors R3 | −5,41 ; −0,177 | −9,56 ; −0,241 | −7,5 [−10,5 ; −4,4] ; −0,209 | +2,08 | +2,42 / −0,00 | 0/6 | 0/6 |
| Tous hors R3 et hors nis_z_100 Q4 | −3,69 ; −0,138 | −8,91 ; −0,260 | −6,3 [−9,6 ; −2,8] ; −0,199 | +2,61 | +4,14 / +0,65 | 1/6 | 1/6 |
| R1 | −4,21 ; −0,082 | −8,27 ; −0,223 | −6,2 [−10,7 ; −1,6] ; −0,152 | +2,03 | +3,61 / +1,29 | 1/6 | 1/6 |
| R1 hors nis_z_100 Q4 | −4,11 ; −0,073 | −5,67 ; −0,215 | −4,9 [−10,3 ; +0,2] ; −0,144 | +0,78 | +3,72 / +3,89 | 2/6 | 2/6 |
| R2 | −8,85 ; −0,280 | −6,37 ; −0,174 | −7,6 [−12,8 ; −2,3] ; −0,227 | −1,24 | −1,02 / +3,19 | 1/6 | 1/6 |
| R2 hors nis_z_100 Q4 | −7,55 ; −0,249 | −7,33 ; −0,213 | −7,4 [−13,3 ; −0,7] ; −0,231 | −0,11 | +0,27 / +2,23 | 1/6 | 1/6 |
| ↳ F2b · x1 déjà retourné | −8,85 ; −0,275 | −6,26 ; −0,167 | −7,6 [−14,8 ; +0,4] ; −0,221 | −1,30 | −1,03 / +3,30 | 1/6 | 1/6 |
| ↳ F2b · x1 déjà retourné hors nis_z_100 Q4 | −8,28 ; −0,271 | −5,18 ; −0,172 | −6,7 [−14,4 ; +2,1] ; −0,221 | −1,55 | −0,46 / +4,38 | 2/6 | 1/6 |
| ↳ F3 · x1 déjà retourné | −8,84 ; −0,283 | −6,45 ; −0,181 | −7,6 [−15,0 ; −0,5] ; −0,232 | −1,20 | −1,02 / +3,11 | 1/6 | 1/6 |
| ↳ F3 · x1 déjà retourné hors nis_z_100 Q4 | −6,87 ; −0,228 | −9,87 ; −0,260 | −8,4 [−17,7 ; +0,2] ; −0,244 | +1,50 | +0,95 / −0,32 | 1/6 | 1/6 |

#### H = 13

**5 bps aller-retour — 8 métriques**

| Configuration | PnL net : composé ; bps cumulés | PF | WR | Espérance : bps [IC 95 %] ; ATR | Max DD : valorisé ; bps | Trades : n ; ignorés ; /mois | Durée méd. (barres) | Part des frais ; brut par trade (bps) |
|---|---|---|---|---|---|---|---|---|
| Tous hors R3 | −76,1 % ; −9376 | 0,952 | 47,6 % | −2,6 [−7,7 ; +2,5] ; −0,062 | −85,8 % ; −16462 | 3 652 ; 26 % ; 50,7 | 13 | 206 % ; +2,4 |
| Tous hors R3 et hors nis_z_100 Q4 | 1,4 % ; +4027 | 1,026 | 48,7 % | +1,3 [−5,2 ; +8,0] ; −0,001 | −65,6 % ; −7734 | 3 122 ; 23 % ; 43,4 | 13 | 79 % ; +6,3 |
| R1 | −57,0 % ; −5908 | 0,937 | 49,8 % | −3,3 [−10,8 ; +4,3] ; −0,078 | −69,8 % ; −9958 | 1 801 ; 7 % ; 25,0 | 13 | 291 % ; +1,7 |
| R1 hors nis_z_100 Q4 | −18,7 % ; −164 | 0,998 | 50,4 % | −0,1 [−9,5 ; +9,6] ; −0,046 | −53,6 % ; −6297 | 1 501 ; 6 % ; 20,8 | 13 | 102 % ; +4,9 |
| R2 | −51,4 % ; −5005 | 0,944 | 45,6 % | −3,2 [−12,0 ; +5,4] ; −0,035 | −68,4 % ; −10017 | 1 574 ; 16 % ; 21,9 | 13 | 275 % ; +1,8 |
| R2 hors nis_z_100 Q4 | −11,1 % ; +380 | 1,006 | 46,3 % | +0,3 [−8,6 ; +8,7] ; +0,031 | −56,0 % ; −7139 | 1 240 ; 15 % ; 17,2 | 13 | 94 % ; +5,3 |
| ↳ F2b · x1 déjà retourné | 9,7 % ; +1834 | 1,050 | 46,7 % | +2,5 [−7,4 ; +12,9] ; +0,027 | −32,1 % ; −3317 | 735 ; 7 % ; 10,2 | 13 | 67 % ; +7,5 |
| ↳ F2b · x1 déjà retourné hors nis_z_100 Q4 | 20,9 % ; +2744 | 1,081 | 46,6 % | +3,9 [−7,0 ; +15,8] ; +0,022 | −34,9 % ; −3748 | 695 ; 6 % ; 9,7 | 13 | 56 % ; +8,9 |
| ↳ F3 · x1 déjà retourné | −51,6 % ; −5781 | 0,905 | 45,3 % | −5,9 [−17,5 ; +5,6] ; −0,094 | −62,8 % ; −8632 | 981 ; 10 % ; 13,6 | 13 | sans objet (brut ≤ 0) ; −0,9 |
| ↳ F3 · x1 déjà retourné hors nis_z_100 Q4 | −23,7 % ; −1890 | 0,948 | 46,4 % | −2,9 [−13,9 ; +7,3] ; +0,007 | −44,8 % ; −5473 | 646 ; 9 % ; 9,0 | 13 | 241 % ; +2,1 |

**5 bps — Long / Short / timing (nets)**

| Configuration | Long : bps ; ATR | Short : bps ; ATR | Timing : bps [IC 95 %] ; ATR | Dérive (bps) | Écart à Tous, Long / Short (bps) | Années PnL > 0 | Années timing > 0 |
|---|---|---|---|---|---|---|---|
| Tous hors R3 | −1,00 ; −0,013 | −3,99 ; −0,105 | −2,5 [−7,8 ; +2,7] ; −0,059 | +1,50 | +1,15 / +2,41 | 3/6 | 3/6 |
| Tous hors R3 et hors nis_z_100 Q4 | +3,14 ; +0,068 | −0,47 ; −0,067 | +1,3 [−5,2 ; +8,1] ; +0,001 | +1,81 | +5,29 / +5,93 | 2/6 | 2/6 |
| R1 | −2,69 ; −0,026 | −3,76 ; −0,121 | −3,2 [−11,0 ; +4,5] ; −0,073 | +0,53 | −0,54 / +2,64 | 1/6 | 1/6 |
| R1 hors nis_z_100 Q4 | −1,05 ; −0,021 | +0,62 ; −0,065 | −0,2 [−10,1 ; +10,3] ; −0,043 | −0,84 | +1,09 / +7,02 | 2/6 | 2/6 |
| R2 | −2,45 ; −0,062 | −3,94 ; −0,008 | −3,2 [−12,0 ; +5,2] ; −0,035 | +0,75 | −0,30 / +2,46 | 2/6 | 2/6 |
| R2 hors nis_z_100 Q4 | −0,91 ; −0,008 | +1,69 ; +0,076 | +0,4 [−8,5 ; +8,9] ; +0,034 | −1,30 | +1,24 / +8,09 | 3/6 | 3/6 |
| ↳ F2b · x1 déjà retourné | +3,69 ; +0,057 | +1,36 ; −0,002 | +2,5 [−7,5 ; +13,1] ; +0,027 | +1,16 | +5,84 / +7,76 | 3/6 | 4/6 |
| ↳ F2b · x1 déjà retourné hors nis_z_100 Q4 | +2,42 ; +0,027 | +5,48 ; +0,017 | +3,9 [−6,9 ; +15,8] ; +0,022 | −1,53 | +4,56 / +11,88 | 3/6 | 3/6 |
| ↳ F3 · x1 déjà retourné | −5,47 ; −0,125 | −6,38 ; −0,058 | −5,9 [−17,5 ; +5,2] ; −0,092 | +0,46 | −3,32 / +0,02 | 2/6 | 2/6 |
| ↳ F3 · x1 déjà retourné hors nis_z_100 Q4 | −1,33 ; +0,014 | −5,02 ; −0,003 | −3,2 [−14,3 ; +7,1] ; +0,006 | +1,84 | +0,82 / +1,38 | 2/6 | 2/6 |

**10 bps aller-retour — 8 métriques**

| Configuration | PnL net : composé ; bps cumulés | PF | WR | Espérance : bps [IC 95 %] ; ATR | Max DD : valorisé ; bps | Trades : n ; ignorés ; /mois | Durée méd. (barres) | Part des frais ; brut par trade (bps) |
|---|---|---|---|---|---|---|---|---|
| Tous hors R3 | −96,2 % ; −27636 | 0,864 | 45,1 % | −7,6 [−12,7 ; −2,5] ; −0,184 | −97,0 % ; −30307 | 3 652 ; 26 % ; 50,7 | 13 | 411 % ; +2,4 |
| Tous hors R3 et hors nis_z_100 Q4 | −78,7 % ; −11583 | 0,929 | 46,1 % | −3,7 [−10,2 ; +3,0] ; −0,128 | −90,1 % ; −19785 | 3 122 ; 23 % ; 43,4 | 13 | 159 % ; +6,3 |
| R1 | −82,6 % ; −14913 | 0,848 | 46,7 % | −8,3 [−15,8 ; −0,7] ; −0,193 | −86,1 % ; −17349 | 1 801 ; 7 % ; 25,0 | 13 | 581 % ; +1,7 |
| R1 hors nis_z_100 Q4 | −61,6 % ; −7669 | 0,902 | 47,4 % | −5,1 [−14,5 ; +4,6] ; −0,165 | −77,0 % ; −12638 | 1 501 ; 6 % ; 20,8 | 13 | 204 % ; +4,9 |
| R2 | −77,9 % ; −12875 | 0,863 | 43,1 % | −8,2 [−17,0 ; +0,4] ; −0,164 | −81,3 % ; −14609 | 1 574 ; 16 % ; 21,9 | 13 | 549 % ; +1,8 |
| R2 hors nis_z_100 Q4 | −52,2 % ; −5820 | 0,915 | 43,5 % | −4,7 [−13,6 ; +3,7] ; −0,106 | −69,7 % ; −10827 | 1 240 ; 15 % ; 17,2 | 13 | 188 % ; +5,3 |
| ↳ F2b · x1 déjà retourné | −24,1 % ; −1841 | 0,952 | 44,1 % | −2,5 [−12,4 ; +7,9] ; −0,106 | −45,6 % ; −5467 | 735 ; 7 % ; 10,2 | 13 | 133 % ; +7,5 |
| ↳ F2b · x1 déjà retourné hors nis_z_100 Q4 | −14,6 % ; −731 | 0,980 | 44,0 % | −1,1 [−12,0 ; +10,8] ; −0,113 | −47,5 % ; −5858 | 695 ; 6 % ; 9,7 | 13 | 112 % ; +8,9 |
| ↳ F3 · x1 déjà retourné | −70,4 % ; −10686 | 0,831 | 42,7 % | −10,9 [−22,5 ; +0,6] ; −0,222 | −74,3 % ; −11925 | 981 ; 10 % ; 13,6 | 13 | sans objet (brut ≤ 0) ; −0,9 |
| ↳ F3 · x1 déjà retourné hors nis_z_100 Q4 | −44,8 % ; −5120 | 0,866 | 43,3 % | −7,9 [−18,9 ; +2,3] ; −0,135 | −54,9 % ; −7151 | 646 ; 9 % ; 9,0 | 13 | 482 % ; +2,1 |

**10 bps — Long / Short / timing (nets)**

| Configuration | Long : bps ; ATR | Short : bps ; ATR | Timing : bps [IC 95 %] ; ATR | Dérive (bps) | Écart à Tous, Long / Short (bps) | Années PnL > 0 | Années timing > 0 |
|---|---|---|---|---|---|---|---|
| Tous hors R3 | −6,00 ; −0,136 | −8,99 ; −0,227 | −7,5 [−12,8 ; −2,3] ; −0,181 | +1,50 | +1,15 / +2,41 | 0/6 | 0/6 |
| Tous hors R3 et hors nis_z_100 Q4 | −1,86 ; −0,058 | −5,47 ; −0,195 | −3,7 [−10,2 ; +3,1] ; −0,126 | +1,81 | +5,29 / +5,93 | 1/6 | 1/6 |
| R1 | −7,69 ; −0,139 | −8,76 ; −0,237 | −8,2 [−16,0 ; −0,5] ; −0,188 | +0,53 | −0,54 / +2,64 | 0/6 | 1/6 |
| R1 hors nis_z_100 Q4 | −6,05 ; −0,139 | −4,38 ; −0,185 | −5,2 [−15,1 ; +5,3] ; −0,162 | −0,84 | +1,09 / +7,02 | 1/6 | 1/6 |
| R2 | −7,45 ; −0,193 | −8,94 ; −0,134 | −8,2 [−17,0 ; +0,2] ; −0,164 | +0,75 | −0,30 / +2,46 | 1/6 | 1/6 |
| R2 hors nis_z_100 Q4 | −5,91 ; −0,146 | −3,31 ; −0,059 | −4,6 [−13,5 ; +3,9] ; −0,103 | −1,30 | +1,24 / +8,09 | 3/6 | 3/6 |
| ↳ F2b · x1 déjà retourné | −1,31 ; −0,077 | −3,64 ; −0,133 | −2,5 [−12,5 ; +8,1] ; −0,105 | +1,16 | +5,84 / +7,76 | 2/6 | 2/6 |
| ↳ F2b · x1 déjà retourné hors nis_z_100 Q4 | −2,58 ; −0,108 | +0,48 ; −0,118 | −1,1 [−11,9 ; +10,8] ; −0,113 | −1,53 | +4,56 / +11,88 | 2/6 | 2/6 |
| ↳ F3 · x1 déjà retourné | −10,47 ; −0,256 | −11,38 ; −0,182 | −10,9 [−22,5 ; +0,2] ; −0,219 | +0,46 | −3,32 / +0,02 | 0/6 | 0/6 |
| ↳ F3 · x1 déjà retourné hors nis_z_100 Q4 | −6,33 ; −0,131 | −10,02 ; −0,142 | −8,2 [−19,3 ; +2,1] ; −0,136 | +1,84 | +0,82 / +1,38 | 2/6 | 1/6 |

#### H = 26

**5 bps aller-retour — 8 métriques**

| Configuration | PnL net : composé ; bps cumulés | PF | WR | Espérance : bps [IC 95 %] ; ATR | Max DD : valorisé ; bps | Trades : n ; ignorés ; /mois | Durée méd. (barres) | Part des frais ; brut par trade (bps) |
|---|---|---|---|---|---|---|---|---|
| Tous hors R3 | −90,1 % ; −16234 | 0,920 | 48,7 % | −6,3 [−14,6 ; +1,8] ; −0,115 | −96,0 % ; −26670 | 2 572 ; 48 % ; 35,7 | 26 | sans objet (brut ≤ 0) ; −1,3 |
| Tous hors R3 et hors nis_z_100 Q4 | −26,3 % ; +2539 | 1,015 | 50,0 % | +1,1 [−7,4 ; +10,1] ; +0,003 | −79,0 % ; −11322 | 2 270 ; 44 % ; 31,5 | 26 | 82 % ; +6,1 |
| R1 | −90,8 % ; −19756 | 0,838 | 51,1 % | −13,4 [−24,5 ; −2,1] ; −0,236 | −92,7 % ; −22393 | 1 477 ; 24 % ; 20,5 | 26 | sans objet (brut ≤ 0) ; −8,4 |
| R1 hors nis_z_100 Q4 | −60,7 % ; −6147 | 0,936 | 51,1 % | −4,9 [−17,6 ; +7,1] ; −0,111 | −77,6 % ; −11858 | 1 263 ; 21 % ; 17,5 | 26 | > 1 000 % ; +0,1 |
| R2 | −7,1 % ; +2994 | 1,028 | 48,0 % | +2,2 [−9,6 ; +14,0] ; +0,126 | −58,2 % ; −7113 | 1 353 ; 28 % ; 18,8 | 26 | 69 % ; +7,2 |
| R2 hors nis_z_100 Q4 | 187,4 % ; +13309 | 1,178 | 49,4 % | +12,3 [−0,8 ; +26,4] ; +0,354 | −47,6 % ; −5852 | 1 080 ; 26 % ; 15,0 | 26 | 29 % ; +17,3 |
| ↳ F2b · x1 déjà retourné | 34,7 % ; +4675 | 1,098 | 48,8 % | +6,9 [−7,5 ; +21,2] ; +0,300 | −44,6 % ; −5260 | 676 ; 14 % ; 9,4 | 26 | 42 % ; +11,9 |
| ↳ F2b · x1 déjà retourné hors nis_z_100 Q4 | 77,5 % ; +7345 | 1,169 | 49,6 % | +11,5 [−2,8 ; +26,7] ; +0,389 | −44,7 % ; −5463 | 639 ; 14 % ; 8,9 | 26 | 30 % ; +16,5 |
| ↳ F3 · x1 déjà retourné | −22,0 % ; +247 | 1,003 | 47,0 % | +0,3 [−17,5 ; +17,4] ; −0,046 | −70,9 % ; −10277 | 902 ; 17 % ; 12,5 | 26 | 95 % ; +5,3 |
| ↳ F3 · x1 déjà retourné hors nis_z_100 Q4 | 48,2 % ; +5598 | 1,126 | 47,4 % | +9,3 [−12,2 ; +28,4] ; +0,144 | −48,0 % ; −5997 | 601 ; 15 % ; 8,3 | 26 | 35 % ; +14,3 |

**5 bps — Long / Short / timing (nets)**

| Configuration | Long : bps ; ATR | Short : bps ; ATR | Timing : bps [IC 95 %] ; ATR | Dérive (bps) | Écart à Tous, Long / Short (bps) | Années PnL > 0 | Années timing > 0 |
|---|---|---|---|---|---|---|---|
| Tous hors R3 | +8,35 ; +0,174 | −19,48 ; −0,375 | −5,6 [−13,7 ; +2,6] ; −0,100 | +13,91 | +10,83 / −0,47 | 2/6 | 2/6 |
| Tous hors R3 et hors nis_z_100 Q4 | +13,31 ; +0,265 | −10,07 ; −0,237 | +1,6 [−6,8 ; +10,4] ; +0,014 | +11,69 | +15,80 / +8,95 | 2/6 | 2/6 |
| R1 | −3,75 ; −0,007 | −20,90 ; −0,415 | −12,3 [−23,0 ; −1,5] ; −0,211 | +8,57 | −1,27 / −1,88 | 1/6 | 2/6 |
| R1 hors nis_z_100 Q4 | +1,31 ; +0,072 | −9,45 ; −0,247 | −4,1 [−17,3 ; +8,6] ; −0,087 | +5,38 | +3,79 / +9,56 | 4/6 | 4/6 |
| R2 | +6,85 ; +0,227 | −2,73 ; +0,018 | +2,1 [−9,9 ; +13,4] ; +0,123 | +4,79 | +9,33 / +16,28 | 4/6 | 4/6 |
| R2 hors nis_z_100 Q4 | +14,24 ; +0,482 | +10,10 ; +0,205 | +12,2 [−0,9 ; +25,9] ; +0,344 | +2,07 | +16,72 / +29,11 | 5/6 | 5/6 |
| ↳ F2b · x1 déjà retourné | +11,59 ; +0,517 | +2,46 ; +0,092 | +7,0 [−7,7 ; +21,4] ; +0,305 | +4,56 | +14,07 / +21,47 | 4/6 | 4/6 |
| ↳ F2b · x1 déjà retourné hors nis_z_100 Q4 | +9,77 ; +0,531 | +13,23 ; +0,246 | +11,5 [−3,2 ; +26,8] ; +0,388 | −1,73 | +12,25 / +32,25 | 4/6 | 4/6 |
| ↳ F3 · x1 déjà retourné | +1,64 ; −0,023 | −1,30 ; −0,074 | +0,2 [−17,1 ; +16,6] ; −0,048 | +1,47 | +4,12 / +17,71 | 3/6 | 3/6 |
| ↳ F3 · x1 déjà retourné hors nis_z_100 Q4 | +10,73 ; +0,268 | +7,42 ; −0,024 | +9,1 [−13,4 ; +29,3] ; +0,122 | +1,65 | +13,21 / +26,44 | 4/6 | 4/6 |

**10 bps aller-retour — 8 métriques**

| Configuration | PnL net : composé ; bps cumulés | PF | WR | Espérance : bps [IC 95 %] ; ATR | Max DD : valorisé ; bps | Trades : n ; ignorés ; /mois | Durée méd. (barres) | Part des frais ; brut par trade (bps) |
|---|---|---|---|---|---|---|---|---|
| Tous hors R3 | −97,3 % ; −29094 | 0,861 | 46,5 % | −11,3 [−19,6 ; −3,2] ; −0,236 | −98,4 % ; −34869 | 2 572 ; 48 % ; 35,7 | 26 | sans objet (brut ≤ 0) ; −1,3 |
| Tous hors R3 et hors nis_z_100 Q4 | −76,3 % ; −8811 | 0,949 | 47,8 % | −3,9 [−12,4 ; +5,1] ; −0,122 | −90,1 % ; −18789 | 2 270 ; 44 % ; 31,5 | 26 | 163 % ; +6,1 |
| R1 | −95,6 % ; −27141 | 0,784 | 49,4 % | −18,4 [−29,5 ; −7,1] ; −0,351 | −96,1 % ; −28483 | 1 477 ; 24 % ; 20,5 | 26 | sans objet (brut ≤ 0) ; −8,4 |
| R1 hors nis_z_100 Q4 | −79,1 % ; −12462 | 0,875 | 49,5 % | −9,9 [−22,6 ; +2,1] ; −0,230 | −85,9 % ; −15948 | 1 263 ; 21 % ; 17,5 | 26 | > 1 000 % ; +0,1 |
| R2 | −52,8 % ; −3771 | 0,966 | 46,3 % | −2,8 [−14,6 ; +9,0] ; −0,003 | −71,0 % ; −9825 | 1 353 ; 28 % ; 18,8 | 26 | 139 % ; +7,2 |
| R2 hors nis_z_100 Q4 | 67,5 % ; +7909 | 1,102 | 47,5 % | +7,3 [−5,8 ; +21,4] ; +0,218 | −51,1 % ; −6278 | 1 080 ; 26 % ; 15,0 | 26 | 58 % ; +17,3 |
| ↳ F2b · x1 déjà retourné | −3,9 % ; +1295 | 1,026 | 47,3 % | +1,9 [−12,5 ; +16,2] ; +0,168 | −49,4 % ; −5895 | 676 ; 14 % ; 9,4 | 26 | 84 % ; +11,9 |
| ↳ F2b · x1 déjà retourné hors nis_z_100 Q4 | 29,0 % ; +4150 | 1,092 | 48,2 % | +6,5 [−7,8 ; +21,7] ; +0,255 | −47,7 % ; −6028 | 639 ; 14 % ; 8,9 | 26 | 61 % ; +16,5 |
| ↳ F3 · x1 déjà retourné | −50,3 % ; −4263 | 0,946 | 45,5 % | −4,7 [−22,5 ; +12,4] ; −0,174 | −77,6 % ; −12897 | 902 ; 17 % ; 12,5 | 26 | 190 % ; +5,3 |
| ↳ F3 · x1 déjà retourné hors nis_z_100 Q4 | 9,7 % ; +2593 | 1,056 | 45,4 % | +4,3 [−17,2 ; +23,4] ; +0,003 | −54,3 % ; −7021 | 601 ; 15 % ; 8,3 | 26 | 70 % ; +14,3 |

**10 bps — Long / Short / timing (nets)**

| Configuration | Long : bps ; ATR | Short : bps ; ATR | Timing : bps [IC 95 %] ; ATR | Dérive (bps) | Écart à Tous, Long / Short (bps) | Années PnL > 0 | Années timing > 0 |
|---|---|---|---|---|---|---|---|
| Tous hors R3 | +3,35 ; +0,051 | −24,48 ; −0,494 | −10,6 [−18,7 ; −2,4] ; −0,221 | +13,91 | +10,83 / −0,47 | 1/6 | 1/6 |
| Tous hors R3 et hors nis_z_100 Q4 | +8,31 ; +0,139 | −15,07 ; −0,361 | −3,4 [−11,8 ; +5,4] ; −0,111 | +11,69 | +15,80 / +8,95 | 2/6 | 2/6 |
| R1 | −8,75 ; −0,120 | −25,90 ; −0,531 | −17,3 [−28,0 ; −6,5] ; −0,325 | +8,57 | −1,27 / −1,88 | 1/6 | 1/6 |
| R1 hors nis_z_100 Q4 | −3,69 ; −0,047 | −14,45 ; −0,367 | −9,1 [−22,3 ; +3,6] ; −0,207 | +5,38 | +3,79 / +9,56 | 1/6 | 1/6 |
| R2 | +1,85 ; +0,097 | −7,73 ; −0,109 | −2,9 [−14,9 ; +8,4] ; −0,006 | +4,79 | +9,33 / +16,28 | 1/6 | 1/6 |
| R2 hors nis_z_100 Q4 | +9,24 ; +0,345 | +5,10 ; +0,070 | +7,2 [−5,9 ; +20,9] ; +0,208 | +2,07 | +16,72 / +29,11 | 5/6 | 5/6 |
| ↳ F2b · x1 déjà retourné | +6,59 ; +0,381 | −2,54 ; −0,036 | +2,0 [−12,7 ; +16,4] ; +0,173 | +4,56 | +14,07 / +21,47 | 4/6 | 4/6 |
| ↳ F2b · x1 déjà retourné hors nis_z_100 Q4 | +4,77 ; +0,394 | +8,23 ; +0,114 | +6,5 [−8,2 ; +21,8] ; +0,254 | −1,73 | +12,25 / +32,25 | 4/6 | 4/6 |
| ↳ F3 · x1 déjà retourné | −3,36 ; −0,152 | −6,30 ; −0,199 | −4,8 [−22,1 ; +11,6] ; −0,175 | +1,47 | +4,12 / +17,71 | 3/6 | 3/6 |
| ↳ F3 · x1 déjà retourné hors nis_z_100 Q4 | +5,73 ; +0,127 | +2,42 ; −0,163 | +4,1 [−18,4 ; +24,3] ; −0,018 | +1,65 | +13,21 / +26,44 | 4/6 | 4/6 |

#### H = 48

**5 bps aller-retour — 8 métriques**

| Configuration | PnL net : composé ; bps cumulés | PF | WR | Espérance : bps [IC 95 %] ; ATR | Max DD : valorisé ; bps | Trades : n ; ignorés ; /mois | Durée méd. (barres) | Part des frais ; brut par trade (bps) |
|---|---|---|---|---|---|---|---|---|
| Tous hors R3 | −41,2 % ; +2823 | 1,016 | 49,6 % | +1,7 [−11,5 ; +15,2] ; +0,200 | −92,4 % ; −20663 | 1 657 ; 67 % ; 23,0 | 48 | 75 % ; +6,7 |
| Tous hors R3 et hors nis_z_100 Q4 | 192,2 % ; +18231 | 1,119 | 49,9 % | +12,0 [−4,2 ; +30,1] ; +0,227 | −80,7 % ; −13448 | 1 525 ; 62 % ; 21,2 | 48 | 29 % ; +17,0 |
| R1 | −75,4 % ; −7738 | 0,940 | 50,5 % | −6,9 [−22,9 ; +11,8] ; −0,100 | −87,0 % ; −14495 | 1 128 ; 42 % ; 15,7 | 48 | sans objet (brut ≤ 0) ; −1,9 |
| R1 hors nis_z_100 Q4 | −31,5 % ; +1772 | 1,016 | 51,2 % | +1,8 [−16,0 ; +18,2] ; −0,038 | −72,7 % ; −11142 | 1 012 ; 36 % ; 14,1 | 48 | 74 % ; +6,8 |
| R2 | −51,7 % ; −1938 | 0,983 | 46,4 % | −1,8 [−18,7 ; +16,4] ; +0,066 | −77,7 % ; −12099 | 1 050 ; 44 % ; 14,6 | 48 | 159 % ; +3,2 |
| R2 hors nis_z_100 Q4 | −47,8 % ; −2502 | 0,972 | 46,9 % | −2,9 [−21,5 ; +16,4] ; +0,071 | −70,9 % ; −9830 | 864 ; 40 % ; 12,0 | 48 | 238 % ; +2,1 |
| ↳ F2b · x1 déjà retourné | −12,9 % ; +1330 | 1,022 | 47,8 % | +2,2 [−20,6 ; +25,3] ; +0,194 | −57,6 % ; −7545 | 594 ; 25 % ; 8,2 | 48 | 69 % ; +7,2 |
| ↳ F2b · x1 déjà retourné hors nis_z_100 Q4 | −5,7 % ; +1912 | 1,034 | 48,2 % | +3,4 [−17,2 ; +25,4] ; +0,219 | −60,8 % ; −8085 | 564 ; 24 % ; 7,8 | 48 | 60 % ; +8,4 |
| ↳ F3 · x1 déjà retourné | −23,4 % ; +1457 | 1,018 | 49,1 % | +2,0 [−21,8 ; +25,0] ; +0,116 | −67,8 % ; −9755 | 745 ; 31 % ; 10,3 | 48 | 72 % ; +7,0 |
| ↳ F3 · x1 déjà retourné hors nis_z_100 Q4 | −12,7 % ; +1471 | 1,026 | 49,1 % | +2,8 [−22,9 ; +26,6] ; +0,201 | −68,1 % ; −9417 | 523 ; 26 % ; 7,3 | 48 | 64 % ; +7,8 |

**5 bps — Long / Short / timing (nets)**

| Configuration | Long : bps ; ATR | Short : bps ; ATR | Timing : bps [IC 95 %] ; ATR | Dérive (bps) | Écart à Tous, Long / Short (bps) | Années PnL > 0 | Années timing > 0 |
|---|---|---|---|---|---|---|---|
| Tous hors R3 | +15,82 ; +0,485 | −11,41 ; −0,063 | +2,2 [−11,3 ; +15,6] ; +0,211 | +13,61 | +19,13 / +16,02 | 5/6 | 5/6 |
| Tous hors R3 et hors nis_z_100 Q4 | +28,01 ; +0,548 | −3,22 ; −0,077 | +12,4 [−3,9 ; +30,5] ; +0,236 | +15,61 | +31,32 / +24,21 | 4/6 | 4/6 |
| R1 | +2,16 ; −0,052 | −14,04 ; −0,139 | −5,9 [−21,7 ; +13,2] ; −0,095 | +8,10 | +5,47 / +13,39 | 3/6 | 3/6 |
| R1 hors nis_z_100 Q4 | +17,77 ; +0,115 | −10,57 ; −0,155 | +3,6 [−13,4 ; +19,2] ; −0,020 | +14,17 | +21,09 / +16,86 | 3/6 | 4/6 |
| R2 | +9,39 ; +0,284 | −13,74 ; −0,164 | −2,2 [−19,0 ; +15,5] ; +0,060 | +11,57 | +12,70 / +13,69 | 3/6 | 3/6 |
| R2 hors nis_z_100 Q4 | −1,49 ; +0,239 | −4,56 ; −0,129 | −3,0 [−21,3 ; +16,0] ; +0,055 | +1,54 | +1,82 / +22,87 | 3/6 | 4/6 |
| ↳ F2b · x1 déjà retourné | +17,08 ; +0,699 | −11,82 ; −0,285 | +2,6 [−20,3 ; +26,4] ; +0,207 | +14,45 | +20,39 / +15,61 | 3/6 | 4/6 |
| ↳ F2b · x1 déjà retourné hors nis_z_100 Q4 | +8,88 ; +0,562 | −2,06 ; −0,121 | +3,4 [−17,4 ; +25,1] ; +0,221 | +5,47 | +12,19 / +25,37 | 3/6 | 3/6 |
| ↳ F3 · x1 déjà retourné | −4,64 ; −0,095 | +9,81 ; +0,369 | +2,6 [−20,7 ; +23,9] ; +0,137 | −7,23 | −1,33 / +37,24 | 3/6 | 3/6 |
| ↳ F3 · x1 déjà retourné hors nis_z_100 Q4 | −14,00 ; −0,053 | +26,33 ; +0,556 | +6,2 [−18,3 ; +29,5] ; +0,251 | −20,16 | −10,68 / +53,76 | 3/6 | 4/6 |

**10 bps aller-retour — 8 métriques**

| Configuration | PnL net : composé ; bps cumulés | PF | WR | Espérance : bps [IC 95 %] ; ATR | Max DD : valorisé ; bps | Trades : n ; ignorés ; /mois | Durée méd. (barres) | Part des frais ; brut par trade (bps) |
|---|---|---|---|---|---|---|---|---|
| Tous hors R3 | −74,4 % ; −5462 | 0,970 | 48,9 % | −3,3 [−16,5 ; +10,2] ; +0,079 | −94,5 % ; −23813 | 1 657 ; 67 % ; 23,0 | 48 | 149 % ; +6,7 |
| Tous hors R3 et hors nis_z_100 Q4 | 36,3 % ; +10606 | 1,068 | 48,9 % | +7,0 [−9,2 ; +25,1] ; +0,104 | −83,9 % ; −14748 | 1 525 ; 62 % ; 21,2 | 48 | 59 % ; +17,0 |
| R1 | −86,0 % ; −13378 | 0,898 | 49,6 % | −11,9 [−27,9 ; +6,8] ; −0,217 | −91,9 % ; −19117 | 1 128 ; 42 % ; 15,7 | 48 | sans objet (brut ≤ 0) ; −1,9 |
| R1 hors nis_z_100 Q4 | −58,7 % ; −3288 | 0,971 | 50,4 % | −3,2 [−21,0 ; +13,2] ; −0,158 | −80,1 % ; −11810 | 1 012 ; 36 % ; 14,1 | 48 | 148 % ; +6,8 |
| R2 | −71,4 % ; −7188 | 0,939 | 45,2 % | −6,8 [−23,7 ; +11,4] ; −0,062 | −83,7 % ; −14943 | 1 050 ; 44 % ; 14,6 | 48 | 317 % ; +3,2 |
| R2 hors nis_z_100 Q4 | −66,2 % ; −6822 | 0,926 | 45,6 % | −7,9 [−26,5 ; +11,4] ; −0,064 | −78,5 % ; −10971 | 864 ; 40 % ; 12,0 | 48 | 475 % ; +2,1 |
| ↳ F2b · x1 déjà retourné | −35,3 % ; −1640 | 0,974 | 46,0 % | −2,8 [−25,6 ; +20,3] ; +0,062 | −62,4 % ; −7815 | 594 ; 25 % ; 8,2 | 48 | 138 % ; +7,2 |
| ↳ F2b · x1 déjà retourné hors nis_z_100 Q4 | −28,9 % ; −908 | 0,984 | 46,5 % | −1,6 [−22,2 ; +20,4] ; +0,086 | −63,0 % ; −8685 | 564 ; 24 % ; 7,8 | 48 | 119 % ; +8,4 |
| ↳ F3 · x1 déjà retourné | −47,2 % ; −2268 | 0,973 | 47,9 % | −3,0 [−26,8 ; +20,0] ; −0,009 | −74,6 % ; −10755 | 745 ; 31 % ; 10,3 | 48 | 144 % ; +7,0 |
| ↳ F3 · x1 déjà retourné hors nis_z_100 Q4 | −32,8 % ; −1144 | 0,980 | 47,6 % | −2,2 [−27,9 ; +21,6] ; +0,065 | −72,7 % ; −10957 | 523 ; 26 % ; 7,3 | 48 | 128 % ; +7,8 |

**10 bps — Long / Short / timing (nets)**

| Configuration | Long : bps ; ATR | Short : bps ; ATR | Timing : bps [IC 95 %] ; ATR | Dérive (bps) | Écart à Tous, Long / Short (bps) | Années PnL > 0 | Années timing > 0 |
|---|---|---|---|---|---|---|---|
| Tous hors R3 | +10,82 ; +0,360 | −16,41 ; −0,181 | −2,8 [−16,3 ; +10,6] ; +0,089 | +13,61 | +19,13 / +16,02 | 3/6 | 4/6 |
| Tous hors R3 et hors nis_z_100 Q4 | +23,01 ; +0,423 | −8,22 ; −0,199 | +7,4 [−8,9 ; +25,5] ; +0,112 | +15,61 | +31,32 / +24,21 | 4/6 | 4/6 |
| R1 | −2,84 ; −0,169 | −19,04 ; −0,255 | −10,9 [−26,7 ; +8,2] ; −0,212 | +8,10 | +5,47 / +13,39 | 1/6 | 2/6 |
| R1 hors nis_z_100 Q4 | +12,77 ; −0,006 | −15,57 ; −0,275 | −1,4 [−18,4 ; +14,2] ; −0,140 | +14,17 | +21,09 / +16,86 | 3/6 | 2/6 |
| R2 | +4,39 ; +0,154 | −18,74 ; −0,290 | −7,2 [−24,0 ; +10,5] ; −0,068 | +11,57 | +12,70 / +13,69 | 2/6 | 2/6 |
| R2 hors nis_z_100 Q4 | −6,49 ; +0,104 | −9,56 ; −0,263 | −8,0 [−26,3 ; +11,0] ; −0,079 | +1,54 | +1,82 / +22,87 | 3/6 | 1/6 |
| ↳ F2b · x1 déjà retourné | +12,08 ; +0,567 | −16,82 ; −0,416 | −2,4 [−25,3 ; +21,4] ; +0,075 | +14,45 | +20,39 / +15,61 | 3/6 | 3/6 |
| ↳ F2b · x1 déjà retourné hors nis_z_100 Q4 | +3,88 ; +0,429 | −7,06 ; −0,255 | −1,6 [−22,4 ; +20,1] ; +0,087 | +5,47 | +12,19 / +25,37 | 3/6 | 3/6 |
| ↳ F3 · x1 déjà retourné | −9,64 ; −0,221 | +4,81 ; +0,244 | −2,4 [−25,7 ; +18,9] ; +0,011 | −7,23 | −1,33 / +37,24 | 3/6 | 3/6 |
| ↳ F3 · x1 déjà retourné hors nis_z_100 Q4 | −19,00 ; −0,188 | +21,33 ; +0,419 | +1,2 [−23,3 ; +24,5] ; +0,115 | −20,16 | −10,68 / +53,76 | 3/6 | 4/6 |

### 3B. Inversion en continuation (−direction)

#### H = 6

**5 bps aller-retour — 8 métriques**

| Configuration | PnL net : composé ; bps cumulés | PF | WR | Espérance : bps [IC 95 %] ; ATR | Max DD : valorisé ; bps | Trades : n ; ignorés ; /mois | Durée méd. (barres) | Part des frais ; brut par trade (bps) |
|---|---|---|---|---|---|---|---|---|
| R3 | −79,8 % ; −14399 | 0,841 | 44,4 % | −6,1 [−10,6 ; −1,1] ; −0,114 | −87,1 % ; −19108 | 2 347 ; 0 % ; 32,6 | 6 | sans objet (brut ≤ 0) ; −1,1 |
| R3 en continuation | −65,7 % ; −9071 | 0,897 | 48,2 % | −3,9 [−8,9 ; +0,6] ; −0,122 | −71,4 % ; −11861 | 2 347 ; 0 % ; 32,6 | 6 | 440 % ; +1,1 |
| nis_z_100 Q4 | −85,2 % ; −17671 | 0,792 | 42,6 % | −9,7 [−14,5 ; −4,9] ; −0,165 | −87,1 % ; −19073 | 1 824 ; 0 % ; 25,3 | 6 | sans objet (brut ≤ 0) ; −4,7 |
| nis_z_100 Q4 en continuation | −18,1 % ; −569 | 0,992 | 52,6 % | −0,3 [−5,1 ; +4,5] ; −0,027 | −37,4 % ; −4273 | 1 824 ; 0 % ; 25,3 | 6 | 107 % ; +4,7 |

**5 bps — Long / Short / timing (nets)**

| Configuration | Long : bps ; ATR | Short : bps ; ATR | Timing : bps [IC 95 %] ; ATR | Dérive (bps) | Écart à Tous, Long / Short (bps) | Années PnL > 0 | Années timing > 0 |
|---|---|---|---|---|---|---|---|
| R3 | −7,60 ; −0,113 | −4,55 ; −0,114 | −6,1 [−10,5 ; −1,1] ; −0,114 | −1,53 | −4,78 / +0,01 | 1/6 | 1/6 |
| R3 en continuation | −5,45 ; −0,130 | −2,40 ; −0,114 | −3,9 [−8,9 ; +0,5] ; −0,122 | −1,53 | −2,63 / +2,16 | 2/6 | 2/6 |
| nis_z_100 Q4 | −11,30 ; −0,233 | −8,14 ; −0,100 | −9,7 [−14,5 ; −4,9] ; −0,167 | −1,58 | −8,48 / −3,58 | 0/6 | 0/6 |
| nis_z_100 Q4 en continuation | −1,86 ; −0,095 | +1,30 ; +0,044 | −0,3 [−5,1 ; +4,5] ; −0,026 | −1,58 | +0,96 / +5,86 | 2/6 | 2/6 |

**10 bps aller-retour — 8 métriques**

| Configuration | PnL net : composé ; bps cumulés | PF | WR | Espérance : bps [IC 95 %] ; ATR | Max DD : valorisé ; bps | Trades : n ; ignorés ; /mois | Durée méd. (barres) | Part des frais ; brut par trade (bps) |
|---|---|---|---|---|---|---|---|---|
| R3 | −93,7 % ; −26134 | 0,732 | 40,0 % | −11,1 [−15,6 ; −6,1] ; −0,231 | −95,7 % ; −29871 | 2 347 ; 0 % ; 32,6 | 6 | sans objet (brut ≤ 0) ; −1,1 |
| R3 en continuation | −89,4 % ; −20806 | 0,779 | 44,6 % | −8,9 [−13,9 ; −4,4] ; −0,239 | −89,8 % ; −21152 | 2 347 ; 0 % ; 32,6 | 6 | 881 % ; +1,1 |
| nis_z_100 Q4 | −94,1 % ; −26791 | 0,704 | 40,1 % | −14,7 [−19,5 ; −9,9] ; −0,261 | −94,5 % ; −27638 | 1 824 ; 0 % ; 25,3 | 6 | sans objet (brut ≤ 0) ; −4,7 |
| nis_z_100 Q4 en continuation | −67,1 % ; −9689 | 0,879 | 49,2 % | −5,3 [−10,1 ; −0,5] ; −0,123 | −69,3 % ; −9847 | 1 824 ; 0 % ; 25,3 | 6 | 213 % ; +4,7 |

**10 bps — Long / Short / timing (nets)**

| Configuration | Long : bps ; ATR | Short : bps ; ATR | Timing : bps [IC 95 %] ; ATR | Dérive (bps) | Écart à Tous, Long / Short (bps) | Années PnL > 0 | Années timing > 0 |
|---|---|---|---|---|---|---|---|
| R3 | −12,60 ; −0,227 | −9,55 ; −0,236 | −11,1 [−15,5 ; −6,1] ; −0,232 | −1,53 | −4,78 / +0,01 | 0/6 | 0/6 |
| R3 en continuation | −10,45 ; −0,251 | −7,40 ; −0,228 | −8,9 [−13,9 ; −4,5] ; −0,240 | −1,53 | −2,63 / +2,16 | 1/6 | 1/6 |
| nis_z_100 Q4 | −16,30 ; −0,328 | −13,14 ; −0,197 | −14,7 [−19,5 ; −9,9] ; −0,263 | −1,58 | −8,48 / −3,58 | 0/6 | 0/6 |
| nis_z_100 Q4 en continuation | −6,86 ; −0,193 | −3,70 ; −0,051 | −5,3 [−10,1 ; −0,5] ; −0,122 | −1,58 | +0,96 / +5,86 | 1/6 | 1/6 |

#### H = 13

**5 bps aller-retour — 8 métriques**

| Configuration | PnL net : composé ; bps cumulés | PF | WR | Espérance : bps [IC 95 %] ; ATR | Max DD : valorisé ; bps | Trades : n ; ignorés ; /mois | Durée méd. (barres) | Part des frais ; brut par trade (bps) |
|---|---|---|---|---|---|---|---|---|
| R3 | −89,9 % ; −19852 | 0,837 | 45,3 % | −9,4 [−16,8 ; −1,5] ; −0,142 | −93,8 % ; −25106 | 2 103 ; 10 % ; 29,2 | 13 | sans objet (brut ≤ 0) ; −4,4 |
| R3 en continuation | −34,3 % ; −1178 | 0,990 | 49,3 % | −0,6 [−8,5 ; +6,8] ; −0,093 | −72,6 % ; −11761 | 2 103 ; 10 % ; 29,2 | 13 | 113 % ; +4,4 |
| nis_z_100 Q4 | −93,1 % ; −23930 | 0,764 | 45,3 % | −15,8 [−25,6 ; −6,8] ; −0,204 | −95,3 % ; −28222 | 1 516 ; 17 % ; 21,1 | 13 | sans objet (brut ≤ 0) ; −10,8 |
| nis_z_100 Q4 en continuation | 84,2 % ; +8770 | 1,103 | 49,8 % | +5,8 [−3,2 ; +15,6] ; +0,011 | −61,2 % ; −8803 | 1 516 ; 17 % ; 21,1 | 13 | 46 % ; +10,8 |

**5 bps — Long / Short / timing (nets)**

| Configuration | Long : bps ; ATR | Short : bps ; ATR | Timing : bps [IC 95 %] ; ATR | Dérive (bps) | Écart à Tous, Long / Short (bps) | Années PnL > 0 | Années timing > 0 |
|---|---|---|---|---|---|---|---|
| R3 | −6,05 ; −0,056 | −13,05 ; −0,232 | −9,6 [−17,1 ; −1,5] ; −0,144 | +3,50 | −3,91 / −6,65 | 1/6 | 1/6 |
| R3 en continuation | +3,05 ; −0,014 | −3,95 ; −0,166 | −0,4 [−8,5 ; +7,1] ; −0,090 | +3,50 | +5,20 / +2,45 | 1/6 | 1/6 |
| nis_z_100 Q4 | −19,96 ; −0,243 | −11,81 ; −0,166 | −15,9 [−25,6 ; −6,9] ; −0,205 | −4,07 | −17,81 / −5,41 | 2/6 | 2/6 |
| nis_z_100 Q4 en continuation | +1,81 ; −0,032 | +9,96 ; +0,056 | +5,9 [−3,1 ; +15,6] ; +0,012 | −4,07 | +3,96 / +16,36 | 4/6 | 4/6 |

**10 bps aller-retour — 8 métriques**

| Configuration | PnL net : composé ; bps cumulés | PF | WR | Espérance : bps [IC 95 %] ; ATR | Max DD : valorisé ; bps | Trades : n ; ignorés ; /mois | Durée méd. (barres) | Part des frais ; brut par trade (bps) |
|---|---|---|---|---|---|---|---|---|
| R3 | −96,5 % ; −30367 | 0,763 | 43,0 % | −14,4 [−21,8 ; −6,5] ; −0,259 | −97,7 % ; −34701 | 2 103 ; 10 % ; 29,2 | 13 | sans objet (brut ≤ 0) ; −4,4 |
| R3 en continuation | −77,1 % ; −11693 | 0,901 | 46,9 % | −5,6 [−13,5 ; +1,8] ; −0,210 | −85,9 % ; −18161 | 2 103 ; 10 % ; 29,2 | 13 | 225 % ; +4,4 |
| nis_z_100 Q4 | −96,8 % ; −31510 | 0,702 | 43,3 % | −20,8 [−30,6 ; −11,8] ; −0,300 | −97,3 % ; −33483 | 1 516 ; 17 % ; 21,1 | 13 | sans objet (brut ≤ 0) ; −10,8 |
| nis_z_100 Q4 en continuation | −13,7 % ; +1190 | 1,013 | 47,8 % | +0,8 [−8,2 ; +10,6] ; −0,085 | −71,6 % ; −11324 | 1 516 ; 17 % ; 21,1 | 13 | 93 % ; +10,8 |

**10 bps — Long / Short / timing (nets)**

| Configuration | Long : bps ; ATR | Short : bps ; ATR | Timing : bps [IC 95 %] ; ATR | Dérive (bps) | Écart à Tous, Long / Short (bps) | Années PnL > 0 | Années timing > 0 |
|---|---|---|---|---|---|---|---|
| R3 | −11,05 ; −0,168 | −18,05 ; −0,356 | −14,6 [−22,1 ; −6,5] ; −0,262 | +3,50 | −3,91 / −6,65 | 0/6 | 0/6 |
| R3 en continuation | −1,95 ; −0,137 | −8,95 ; −0,278 | −5,4 [−13,5 ; +2,1] ; −0,207 | +3,50 | +5,20 / +2,45 | 1/6 | 1/6 |
| nis_z_100 Q4 | −24,96 ; −0,337 | −16,81 ; −0,266 | −20,9 [−30,6 ; −11,9] ; −0,301 | −4,07 | −17,81 / −5,41 | 1/6 | 1/6 |
| nis_z_100 Q4 en continuation | −3,19 ; −0,131 | +4,96 ; −0,037 | +0,9 [−8,1 ; +10,6] ; −0,084 | −4,07 | +3,96 / +16,36 | 3/6 | 3/6 |

#### H = 26

**5 bps aller-retour — 8 métriques**

| Configuration | PnL net : composé ; bps cumulés | PF | WR | Espérance : bps [IC 95 %] ; ATR | Max DD : valorisé ; bps | Trades : n ; ignorés ; /mois | Durée méd. (barres) | Part des frais ; brut par trade (bps) |
|---|---|---|---|---|---|---|---|---|
| R3 | −97,7 % ; −33976 | 0,754 | 44,5 % | −20,3 [−29,8 ; −11,3] ; −0,343 | −98,5 % ; −37392 | 1 674 ; 29 % ; 23,2 | 26 | sans objet (brut ≤ 0) ; −15,3 |
| R3 en continuation | 280,6 % ; +17236 | 1,154 | 51,6 % | +10,3 [+1,3 ; +19,8] ; +0,109 | −47,6 % ; −6022 | 1 674 ; 29 % ; 23,2 | 26 | 33 % ; +15,3 |
| nis_z_100 Q4 | −94,4 % ; −24690 | 0,790 | 45,7 % | −20,1 [−35,3 ; −4,4] ; −0,328 | −95,4 % ; −27374 | 1 231 ; 33 % ; 17,1 | 26 | sans objet (brut ≤ 0) ; −15,1 |
| nis_z_100 Q4 en continuation | 129,2 % ; +12380 | 1,125 | 51,4 % | +10,1 [−5,6 ; +25,3] ; +0,134 | −63,9 % ; −8038 | 1 231 ; 33 % ; 17,1 | 26 | 33 % ; +15,1 |

**5 bps — Long / Short / timing (nets)**

| Configuration | Long : bps ; ATR | Short : bps ; ATR | Timing : bps [IC 95 %] ; ATR | Dérive (bps) | Écart à Tous, Long / Short (bps) | Années PnL > 0 | Années timing > 0 |
|---|---|---|---|---|---|---|---|
| R3 | −16,20 ; −0,315 | −24,60 ; −0,373 | −20,4 [−30,0 ; −11,3] ; −0,344 | +4,20 | −13,72 / −5,59 | 0/6 | 0/6 |
| R3 en continuation | +14,60 ; +0,129 | +6,20 ; +0,090 | +10,4 [+1,3 ; +20,0] ; +0,110 | +4,20 | +17,08 / +25,22 | 5/6 | 5/6 |
| nis_z_100 Q4 | −12,79 ; −0,268 | −26,75 ; −0,383 | −19,8 [−35,3 ; −4,3] ; −0,326 | +6,98 | −10,30 / −7,74 | 2/6 | 2/6 |
| nis_z_100 Q4 en continuation | +16,75 ; +0,186 | +2,79 ; +0,077 | +9,8 [−5,7 ; +25,3] ; +0,132 | +6,98 | +19,23 / +21,80 | 3/6 | 3/6 |

**10 bps aller-retour — 8 métriques**

| Configuration | PnL net : composé ; bps cumulés | PF | WR | Espérance : bps [IC 95 %] ; ATR | Max DD : valorisé ; bps | Trades : n ; ignorés ; /mois | Durée méd. (barres) | Part des frais ; brut par trade (bps) |
|---|---|---|---|---|---|---|---|---|
| R3 | −99,0 % ; −42346 | 0,703 | 42,8 % | −25,3 [−34,8 ; −16,3] ; −0,460 | −99,2 % ; −44352 | 1 674 ; 29 % ; 23,2 | 26 | sans objet (brut ≤ 0) ; −15,3 |
| R3 en continuation | 64,9 % ; +8866 | 1,077 | 49,5 % | +5,3 [−3,7 ; +14,8] ; −0,008 | −61,7 % ; −8025 | 1 674 ; 29 % ; 23,2 | 26 | 65 % ; +15,3 |
| nis_z_100 Q4 | −97,0 % ; −30845 | 0,745 | 44,1 % | −25,1 [−40,3 ; −9,4] ; −0,425 | −97,2 % ; −31769 | 1 231 ; 33 % ; 17,1 | 26 | sans objet (brut ≤ 0) ; −15,1 |
| nis_z_100 Q4 en continuation | 23,9 % ; +6225 | 1,061 | 49,6 % | +5,1 [−10,6 ; +20,3] ; +0,037 | −75,8 % ; −12038 | 1 231 ; 33 % ; 17,1 | 26 | 66 % ; +15,1 |

**10 bps — Long / Short / timing (nets)**

| Configuration | Long : bps ; ATR | Short : bps ; ATR | Timing : bps [IC 95 %] ; ATR | Dérive (bps) | Écart à Tous, Long / Short (bps) | Années PnL > 0 | Années timing > 0 |
|---|---|---|---|---|---|---|---|
| R3 | −21,20 ; −0,428 | −29,60 ; −0,495 | −25,4 [−35,0 ; −16,3] ; −0,461 | +4,20 | −13,72 / −5,59 | 0/6 | 0/6 |
| R3 en continuation | +9,60 ; +0,008 | +1,20 ; −0,022 | +5,4 [−3,7 ; +15,0] ; −0,007 | +4,20 | +17,08 / +25,22 | 4/6 | 4/6 |
| nis_z_100 Q4 | −17,79 ; −0,364 | −31,75 ; −0,482 | −24,8 [−40,3 ; −9,3] ; −0,423 | +6,98 | −10,30 / −7,74 | 1/6 | 1/6 |
| nis_z_100 Q4 en continuation | +11,75 ; +0,088 | −2,21 ; −0,018 | +4,8 [−10,7 ; +20,3] ; +0,035 | +6,98 | +19,23 / +21,80 | 3/6 | 3/6 |

#### H = 48

**5 bps aller-retour — 8 métriques**

| Configuration | PnL net : composé ; bps cumulés | PF | WR | Espérance : bps [IC 95 %] ; ATR | Max DD : valorisé ; bps | Trades : n ; ignorés ; /mois | Durée méd. (barres) | Part des frais ; brut par trade (bps) |
|---|---|---|---|---|---|---|---|---|
| R3 | −91,8 % ; −19000 | 0,859 | 47,8 % | −15,4 [−30,8 ; +1,2] ; −0,415 | −96,7 % ; −28864 | 1 235 ; 47 % ; 17,2 | 48 | sans objet (brut ≤ 0) ; −10,4 |
| R3 en continuation | 2,6 % ; +6650 | 1,055 | 48,3 % | +5,4 [−11,2 ; +20,8] ; +0,183 | −71,7 % ; −10761 | 1 235 ; 47 % ; 17,2 | 48 | 48 % ; +10,4 |
| nis_z_100 Q4 | −57,0 % ; −3129 | 0,971 | 47,9 % | −3,3 [−23,9 ; +19,2] ; −0,042 | −79,3 % ; −11935 | 952 ; 48 % ; 13,2 | 48 | 292 % ; +1,7 |
| nis_z_100 Q4 en continuation | −70,6 % ; −6391 | 0,942 | 49,9 % | −6,7 [−29,2 ; +13,9] ; −0,155 | −80,7 % ; −10408 | 952 ; 48 % ; 13,2 | 48 | sans objet (brut ≤ 0) ; −1,7 |

**5 bps — Long / Short / timing (nets)**

| Configuration | Long : bps ; ATR | Short : bps ; ATR | Timing : bps [IC 95 %] ; ATR | Dérive (bps) | Écart à Tous, Long / Short (bps) | Années PnL > 0 | Années timing > 0 |
|---|---|---|---|---|---|---|---|
| R3 | −0,52 ; −0,017 | −30,28 ; −0,814 | −15,4 [−30,4 ; +1,2] ; −0,415 | +14,88 | +2,80 / −2,85 | 1/6 | 1/6 |
| R3 en continuation | +20,28 ; +0,572 | −9,48 ; −0,205 | +5,4 [−11,2 ; +20,4] ; +0,183 | +14,88 | +23,59 / +17,95 | 4/6 | 5/6 |
| nis_z_100 Q4 | +5,28 ; +0,048 | −11,19 ; −0,124 | −3,0 [−23,4 ; +19,1] ; −0,038 | +8,24 | +8,59 / +16,24 | 3/6 | 4/6 |
| nis_z_100 Q4 en continuation | +1,19 ; −0,079 | −15,28 ; −0,237 | −7,0 [−29,1 ; +13,4] ; −0,158 | +8,24 | +4,51 / +12,15 | 2/6 | 2/6 |

**10 bps aller-retour — 8 métriques**

| Configuration | PnL net : composé ; bps cumulés | PF | WR | Espérance : bps [IC 95 %] ; ATR | Max DD : valorisé ; bps | Trades : n ; ignorés ; /mois | Durée méd. (barres) | Part des frais ; brut par trade (bps) |
|---|---|---|---|---|---|---|---|---|
| R3 | −95,6 % ; −25175 | 0,817 | 46,6 % | −20,4 [−35,8 ; −3,8] ; −0,531 | −98,2 % ; −34759 | 1 235 ; 47 % ; 17,2 | 48 | sans objet (brut ≤ 0) ; −10,4 |
| R3 en continuation | −44,7 % ; +475 | 1,004 | 47,3 % | +0,4 [−16,2 ; +15,8] ; +0,067 | −75,3 % ; −11312 | 1 235 ; 47 % ; 17,2 | 48 | 96 % ; +10,4 |
| nis_z_100 Q4 | −73,3 % ; −7889 | 0,929 | 47,5 % | −8,3 [−28,9 ; +14,2] ; −0,140 | −85,4 % ; −15240 | 952 ; 48 % ; 13,2 | 48 | 584 % ; +1,7 |
| nis_z_100 Q4 en continuation | −81,8 % ; −11151 | 0,901 | 49,2 % | −11,7 [−34,2 ; +8,9] ; −0,253 | −87,3 % ; −14573 | 952 ; 48 % ; 13,2 | 48 | sans objet (brut ≤ 0) ; −1,7 |

**10 bps — Long / Short / timing (nets)**

| Configuration | Long : bps ; ATR | Short : bps ; ATR | Timing : bps [IC 95 %] ; ATR | Dérive (bps) | Écart à Tous, Long / Short (bps) | Années PnL > 0 | Années timing > 0 |
|---|---|---|---|---|---|---|---|
| R3 | −5,52 ; −0,128 | −35,28 ; −0,935 | −20,4 [−35,4 ; −3,8] ; −0,531 | +14,88 | +2,80 / −2,85 | 1/6 | 1/6 |
| R3 en continuation | +15,28 ; +0,451 | −14,48 ; −0,316 | +0,4 [−16,2 ; +15,4] ; +0,067 | +14,88 | +23,59 / +17,95 | 4/6 | 4/6 |
| nis_z_100 Q4 | +0,28 ; −0,047 | −16,19 ; −0,226 | −8,0 [−28,4 ; +14,1] ; −0,136 | +8,24 | +8,59 / +16,24 | 2/6 | 2/6 |
| nis_z_100 Q4 en continuation | −3,81 ; −0,181 | −20,28 ; −0,332 | −12,0 [−34,1 ; +8,4] ; −0,256 | +8,24 | +4,51 / +12,15 | 2/6 | 2/6 |

## E. Stabilité annuelle : espérance nette par trade (bps, 5 bps aller-retour)

### H = 6

Entre parenthèses : nombre de trades.

| Configuration | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 |
|---|---|---|---|---|---|---|
| Tous | +3,2 (1 189) | −10,5 (1 226) | −6,7 (1 235) | −0,3 (1 236) | −4,1 (1 193) | −3,6 (1 217) |
| Tous hors R3 | +4,8 (856) | −5,8 (845) | −4,0 (822) | −1,0 (835) | −5,0 (786) | −4,6 (805) |
| Tous hors nis_z_100 Q4 | +6,2 (901) | −8,1 (886) | −4,3 (945) | +1,9 (933) | −3,3 (906) | −2,6 (901) |
| R1 | +3,9 (326) | −6,6 (308) | −8,3 (319) | +6,3 (320) | −3,9 (322) | −0,5 (340) |
| R2 | +6,7 (327) | −6,4 (346) | −3,3 (293) | −2,8 (325) | −4,9 (297) | −5,5 (286) |
| ↳ F2b · x1 déjà retourné | +7,1 (160) | −12,8 (145) | −2,7 (123) | −2,2 (124) | −9,0 (122) | +3,8 (113) |
| ↳ F3 · x1 déjà retourné | +6,3 (167) | −1,8 (201) | −3,7 (170) | −3,2 (201) | −2,1 (175) | −11,5 (173) |
| R3 | −0,8 (333) | −21,0 (381) | −12,1 (413) | +1,2 (401) | −2,4 (407) | −1,6 (412) |
| nis_z_100 Q4 | −6,0 (288) | −16,8 (340) | −14,5 (290) | −6,9 (303) | −6,6 (287) | −6,4 (316) |
| Tous hors R3 et hors nis_z_100 Q4 | +5,5 (703) | −6,5 (666) | −2,6 (692) | +1,5 (686) | −3,6 (656) | −2,7 (663) |
| R1 hors nis_z_100 Q4 | +7,2 (263) | −4,7 (252) | −7,6 (266) | +8,6 (253) | −0,4 (278) | −2,6 (280) |
| R2 hors nis_z_100 Q4 | +7,5 (256) | −9,9 (251) | −4,8 (233) | +1,5 (259) | −10,6 (231) | +1,0 (222) |
| ↳ F2b · x1 déjà retourné hors nis_z_100 Q4 | +10,1 (149) | −10,2 (132) | −2,9 (119) | −2,9 (123) | −11,3 (114) | +5,4 (104) |
| ↳ F3 · x1 déjà retourné hors nis_z_100 Q4 | +3,8 (107) | −9,6 (119) | −6,8 (114) | +5,5 (136) | −10,0 (117) | −2,9 (118) |
| R3 en continuation | −9,2 (333) | +11,0 (381) | +2,1 (413) | −11,2 (401) | −7,6 (407) | −8,4 (412) |
| nis_z_100 Q4 en continuation | −4,0 (288) | +6,8 (340) | +4,5 (290) | −3,1 (303) | −3,4 (287) | −3,6 (316) |

### H = 13

Entre parenthèses : nombre de trades.

| Configuration | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 |
|---|---|---|---|---|---|---|
| Tous | −3,0 (809) | −6,6 (826) | −13,2 (825) | −5,2 (818) | +1,9 (796) | +0,5 (831) |
| Tous hors R3 | +1,8 (633) | −1,4 (629) | −13,4 (602) | −7,2 (610) | +2,3 (578) | +2,5 (600) |
| Tous hors nis_z_100 Q4 | +7,2 (655) | −0,1 (651) | −5,8 (679) | −0,6 (659) | +1,4 (649) | +2,7 (653) |
| R1 | −0,3 (309) | −6,9 (285) | −9,6 (294) | −4,6 (294) | +2,0 (292) | −0,7 (327) |
| R2 | −3,1 (270) | −0,5 (298) | −15,3 (241) | +0,4 (269) | −6,9 (250) | +5,2 (246) |
| ↳ F2b · x1 déjà retourné | +16,6 (148) | −0,7 (136) | −5,9 (113) | +0,3 (120) | −4,3 (113) | +5,6 (105) |
| ↳ F3 · x1 déjà retourné | −13,4 (150) | +3,6 (188) | −17,5 (151) | −9,2 (174) | −5,7 (157) | +4,3 (161) |
| R3 | −9,2 (307) | −31,9 (348) | −7,5 (371) | −4,3 (357) | −6,6 (352) | +2,0 (368) |
| nis_z_100 Q4 | −36,9 (240) | −36,8 (276) | −15,0 (249) | −16,9 (246) | +7,1 (238) | +4,8 (267) |
| Tous hors R3 et hors nis_z_100 Q4 | +14,0 (544) | −3,2 (522) | −5,6 (529) | −0,8 (520) | −1,8 (501) | +4,6 (506) |
| R1 hors nis_z_100 Q4 | +14,7 (251) | −1,8 (238) | −10,4 (249) | −0,5 (237) | +0,1 (255) | −2,9 (271) |
| R2 hors nis_z_100 Q4 | +13,9 (215) | −6,0 (224) | −11,0 (197) | +6,7 (216) | −15,0 (196) | +12,4 (192) |
| ↳ F2b · x1 déjà retourné hors nis_z_100 Q4 | +23,8 (137) | +2,2 (128) | −5,8 (110) | −1,5 (119) | −4,9 (105) | +5,7 (96) |
| ↳ F3 · x1 déjà retourné hors nis_z_100 Q4 | +6,1 (98) | −9,1 (113) | −11,8 (103) | −2,2 (117) | −16,9 (105) | +16,2 (110) |
| R3 en continuation | −0,8 (307) | +21,9 (348) | −2,5 (371) | −5,7 (357) | −3,4 (352) | −12,0 (368) |
| nis_z_100 Q4 en continuation | +26,9 (240) | +26,8 (276) | +5,0 (249) | +6,9 (246) | −17,1 (238) | −14,8 (267) |

### H = 26

Entre parenthèses : nombre de trades.

| Configuration | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 |
|---|---|---|---|---|---|---|
| Tous | −1,8 (498) | −30,3 (522) | −21,8 (521) | −8,3 (518) | −3,1 (504) | +1,3 (517) |
| Tous hors R3 | −9,8 (442) | −21,6 (435) | −6,3 (428) | −17,2 (432) | +4,1 (413) | +14,0 (422) |
| Tous hors nis_z_100 Q4 | +6,1 (435) | +27,3 (440) | −24,1 (456) | +2,5 (445) | −7,8 (431) | +2,9 (426) |
| R1 | −21,8 (256) | −9,5 (240) | −22,1 (234) | −28,4 (242) | −4,9 (244) | +5,2 (261) |
| R2 | −0,7 (232) | −0,4 (243) | +0,5 (209) | +0,8 (235) | +9,1 (216) | +4,6 (218) |
| ↳ F2b · x1 déjà retourné | +15,9 (133) | −12,1 (126) | −7,0 (105) | +20,0 (111) | +20,4 (102) | +5,2 (99) |
| ↳ F3 · x1 déjà retourné | +7,7 (136) | +24,6 (168) | −2,8 (139) | −17,0 (161) | −23,8 (145) | +10,8 (153) |
| R3 | −38,2 (253) | −36,0 (287) | −16,7 (286) | −10,0 (280) | −21,0 (282) | −1,7 (286) |
| nis_z_100 Q4 | −42,5 (185) | −63,2 (227) | +13,0 (205) | −24,4 (201) | +3,4 (202) | −4,5 (211) |
| Tous hors R3 et hors nis_z_100 Q4 | +16,0 (396) | −11,1 (374) | −9,0 (385) | −1,5 (385) | −0,6 (371) | +12,8 (359) |
| R1 hors nis_z_100 Q4 | +0,4 (211) | +1,6 (202) | −28,1 (203) | −16,4 (202) | +6,2 (223) | +4,9 (222) |
| R2 hors nis_z_100 Q4 | +21,9 (189) | +6,1 (192) | +7,9 (173) | +19,8 (188) | −2,7 (171) | +20,2 (167) |
| ↳ F2b · x1 déjà retourné hors nis_z_100 Q4 | +27,2 (122) | −10,6 (119) | −2,5 (102) | +18,3 (110) | +24,6 (95) | +13,3 (91) |
| ↳ F3 · x1 déjà retourné hors nis_z_100 Q4 | +25,6 (92) | +45,3 (105) | +6,4 (94) | −0,3 (108) | −47,0 (99) | +25,0 (103) |
| R3 en continuation | +28,2 (253) | +26,0 (287) | +6,7 (286) | +0,0 (280) | +11,0 (282) | −8,3 (286) |
| nis_z_100 Q4 en continuation | +32,5 (185) | +53,2 (227) | −23,0 (205) | +14,4 (201) | −13,4 (202) | −5,5 (211) |

### H = 48

Entre parenthèses : nombre de trades.

| Configuration | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 |
|---|---|---|---|---|---|---|
| Tous | +6,9 (303) | −26,2 (315) | −24,8 (313) | −36,3 (310) | −13,8 (313) | −1,1 (312) |
| Tous hors R3 | +0,1 (282) | −47,2 (278) | +12,9 (273) | +1,6 (273) | +27,0 (277) | +16,5 (274) |
| Tous hors nis_z_100 Q4 | +7,2 (276) | +19,4 (282) | −10,0 (286) | +12,0 (283) | −9,2 (289) | +3,7 (279) |
| R1 | −40,5 (186) | −3,3 (182) | +1,5 (180) | −32,3 (191) | +3,4 (192) | +28,7 (197) |
| R2 | +11,1 (175) | −23,3 (186) | −16,0 (168) | −1,5 (179) | +16,8 (175) | +2,7 (167) |
| ↳ F2b · x1 déjà retourné | +9,4 (114) | −5,3 (109) | −36,4 (88) | +33,0 (102) | +19,6 (94) | −13,4 (87) |
| ↳ F3 · x1 déjà retourné | +14,2 (119) | −17,6 (134) | +30,8 (121) | −19,6 (128) | −26,1 (120) | +32,9 (123) |
| R3 | +29,4 (186) | −25,1 (207) | −31,5 (217) | −34,6 (210) | −7,2 (202) | −17,5 (213) |
| nis_z_100 Q4 | +28,8 (153) | −38,2 (174) | +16,1 (161) | −23,8 (150) | −0,0 (152) | +0,5 (162) |
| Tous hors R3 et hors nis_z_100 Q4 | +19,2 (256) | −15,0 (258) | −6,7 (251) | +43,2 (255) | +15,3 (253) | +15,8 (252) |
| R1 hors nis_z_100 Q4 | −34,6 (166) | −5,0 (165) | +6,6 (163) | −12,7 (167) | +19,4 (180) | +34,4 (171) |
| R2 hors nis_z_100 Q4 | +5,7 (148) | −17,4 (151) | −30,5 (138) | +18,0 (149) | −0,0 (143) | +6,0 (135) |
| ↳ F2b · x1 déjà retourné hors nis_z_100 Q4 | +22,6 (107) | −18,0 (102) | −32,3 (86) | +32,4 (101) | +21,4 (87) | −12,7 (81) |
| ↳ F3 · x1 déjà retourné hors nis_z_100 Q4 | +30,6 (84) | +9,7 (92) | −1,6 (84) | −3,7 (89) | −60,2 (88) | +43,9 (86) |
| R3 en continuation | −39,4 (186) | +15,1 (207) | +21,5 (217) | +24,6 (210) | −2,8 (202) | +7,5 (213) |
| nis_z_100 Q4 en continuation | −38,8 (153) | +28,2 (174) | −26,1 (161) | +13,8 (150) | −10,0 (152) | −10,5 (162) |

### Ancre native

| Configuration | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 |
|---|---|---|---|---|---|---|
| Ancre native P6.5d | +6,3 (1 000) | −18,6 (1 000) | −13,6 (1 015) | −5,3 (1 040) | −3,3 (971) | +2,4 (1 011) |

## F. Contrôle A — Éviction pure contre déblocage séquentiel (H = 26, 5 bps)

La course du contrôle est purgée a posteriori de ses trades `nis_z_100` Q4, sans rouvrir les signaux qu'ils masquaient (ligne 3). La course hors Q4 (ligne 4) rouvre ces signaux : ses trades se partagent entre ceux qu'elle a en commun avec 3 (4a) et ceux qu'elle débloque (4b). Éviction pure = 3 − 1 ; effet de calendrier = 4 − 3.

### R2

| Ensemble de trades | n | Espérance nette : bps [IC 95 %] ; ATR | Long / Short (bps) |
|---|---|---|---|
| 1. course du contrôle | 1 353 | +2,2 [−9,6 ; +14,0] ; +0,126 | +6,9 / −2,7 |
| 2. dont trades nis_z_100 Q4 | 319 | −22,0 [−47,1 ; +1,7] ; −0,400 | −19,8 / −23,9 |
| 3. contrôle purgé a posteriori (éviction pure) | 1 034 | +9,7 [−3,7 ; +23,1] ; +0,288 | +14,0 / +4,7 |
| 3b. dont trades absents de la course hors Q4 | 15 | +1,9 [−131,1 ; +147,6] ; −0,714 | +18,6 / −17,1 |
| 4. course hors Q4 | 1 080 | +12,3 [−0,8 ; +26,4] ; +0,354 | +14,2 / +10,1 |
| 4a. dont trades communs avec 3 | 1 019 | +9,8 [−3,4 ; +23,3] ; +0,303 | +13,9 / +5,1 |
| 4b. dont trades débloqués (absents de 3) | 61 | +54,7 [−3,4 ; +115,4] ; +1,208 | +18,5 / +114,5 |

### ↳ F2b · x1 déjà retourné

| Ensemble de trades | n | Espérance nette : bps [IC 95 %] ; ATR | Long / Short (bps) |
|---|---|---|---|
| 1. course du contrôle | 676 | +6,9 [−7,5 ; +21,2] ; +0,300 | +11,6 / +2,5 |
| 2. dont trades nis_z_100 Q4 | 43 | −69,6 [−144,2 ; +3,0] ; −0,906 | +16,2 / −111,1 |
| 3. contrôle purgé a posteriori (éviction pure) | 633 | +12,1 [−3,5 ; +27,9] ; +0,381 | +11,4 / +12,8 |
| 3b. dont trades absents de la course hors Q4 | 0 | — | — / — |
| 4. course hors Q4 | 639 | +11,5 [−2,8 ; +26,7] ; +0,389 | +9,8 / +13,2 |
| 4a. dont trades communs avec 3 | 633 | +12,1 [−3,5 ; +27,9] ; +0,381 | +11,4 / +12,8 |
| 4b. dont trades débloqués (absents de 3) | 6 | −54,2 [−214,7 ; +113,6] ; +1,187 | −92,0 / +135,1 |

### ↳ F3 · x1 déjà retourné

| Ensemble de trades | n | Espérance nette : bps [IC 95 %] ; ATR | Long / Short (bps) |
|---|---|---|---|
| 1. course du contrôle | 902 | +0,3 [−17,5 ; +17,4] ; −0,046 | +1,6 / −1,3 |
| 2. dont trades nis_z_100 Q4 | 314 | −10,3 [−37,6 ; +20,4] ; −0,265 | −11,7 / −9,0 |
| 3. contrôle purgé a posteriori (éviction pure) | 588 | +5,9 [−14,9 ; +24,9] ; +0,071 | +7,6 / +3,6 |
| 3b. dont trades absents de la course hors Q4 | 2 | −144,3 [−201,2 ; −87,5] ; −2,786 | −87,5 / −201,2 |
| 4. course hors Q4 | 601 | +9,3 [−12,2 ; +28,4] ; +0,144 | +10,7 / +7,4 |
| 4a. dont trades communs avec 3 | 586 | +6,4 [−14,9 ; +25,7] ; +0,080 | +7,9 / +4,4 |
| 4b. dont trades débloqués (absents de 3) | 15 | +122,8 [+41,6 ; +193,0] ; +2,608 | +88,4 / +260,6 |

## G. Contrôle B — Seuils causaux (5 bps)

Médiane de `leg_atr` et P75 de `nis_z_100` calculés sur les seuls signaux précédents. Les 500 premiers signaux (janvier à mai 2020) n'ont pas de seuil causal : les trois variantes sont comparées sur la même période, après eux. `R1` ne dépend pas de la médiane de `leg_atr` : seul son filtre Q4 change.

### Accord des masques avec les seuils de l'échantillon entier

| Configuration | échantillon entier | glissante 500 signaux | expansive |
|---|---|---|---|
| R1 hors Q4 | 1 483 signaux ; 100,0 % | 1 483 signaux ; 99,6 % | 1 488 signaux ; 99,9 % |
| R2 hors Q4 | 1 348 signaux ; 100,0 % | 1 347 signaux ; 98,6 % | 1 299 signaux ; 99,2 % |
| ↳ F2b · x1 déjà retourné hors Q4 | 679 signaux ; 100,0 % | 678 signaux ; 99,2 % | 646 signaux ; 99,4 % |
| ↳ F3 · x1 déjà retourné hors Q4 | 669 signaux ; 100,0 % | 669 signaux ; 99,5 % | 653 signaux ; 99,8 % |

### R1 hors Q4

Espérance nette : bps [IC 95 %] ; ATR (trades)

| Horizon | échantillon entier | glissante 500 signaux | expansive |
|---|---|---|---|
| H = 6 | −0,8 [−6,1 ; +4,1] ; −0,028 (1 483) | −1,6 [−7,0 ; +3,2] ; −0,039 (1 483) | −0,9 [−6,2 ; +3,9] ; −0,029 (1 488) |
| H = 13 | −3,1 [−11,6 ; +5,5] ; −0,070 (1 398) | −3,6 [−12,2 ; +5,0] ; −0,075 (1 398) | −3,2 [−11,7 ; +5,2] ; −0,072 (1 403) |
| H = 26 | −6,4 [−18,2 ; +4,3] ; −0,113 (1 175) | −6,1 [−18,0 ; +4,9] ; −0,109 (1 174) | −6,1 [−18,1 ; +4,6] ; −0,112 (1 178) |
| H = 48 | +3,6 [−14,4 ; +20,5] ; +0,019 (940) | +4,4 [−12,7 ; +21,5] ; +0,032 (942) | +6,1 [−10,9 ; +23,0] ; +0,048 (944) |

### R2 hors Q4

Espérance nette : bps [IC 95 %] ; ATR (trades)

| Horizon | échantillon entier | glissante 500 signaux | expansive |
|---|---|---|---|
| H = 6 | −3,7 [−9,6 ; +2,7] ; −0,115 (1 348) | −3,9 [−9,8 ; +2,8] ; −0,122 (1 347) | −2,9 [−8,7 ; +3,4] ; −0,106 (1 299) |
| H = 13 | −0,8 [−10,6 ; +8,5] ; +0,008 (1 155) | −1,2 [−11,4 ; +8,7] ; +0,008 (1 149) | −1,5 [−11,5 ; +8,0] ; −0,012 (1 114) |
| H = 26 | +11,6 [−3,6 ; +26,3] ; +0,334 (1 008) | +12,9 [−1,8 ; +27,7] ; +0,357 (1 005) | +11,4 [−4,0 ; +26,1] ; +0,321 (972) |
| H = 48 | −3,7 [−20,9 ; +15,5] ; +0,032 (807) | −0,2 [−18,3 ; +19,4] ; +0,102 (806) | −0,5 [−19,0 ; +19,3] ; +0,053 (790) |

### ↳ F2b · x1 déjà retourné hors Q4

Espérance nette : bps [IC 95 %] ; ATR (trades)

| Horizon | échantillon entier | glissante 500 signaux | expansive |
|---|---|---|---|
| H = 6 | −4,6 [−11,7 ; +3,5] ; −0,134 (679) | −5,1 [−12,0 ; +3,2] ; −0,158 (678) | −3,7 [−10,8 ; +4,6] ; −0,126 (646) |
| H = 13 | +1,0 [−10,1 ; +12,6] ; −0,032 (637) | −0,3 [−11,0 ; +11,5] ; −0,045 (633) | −0,3 [−11,2 ; +11,6] ; −0,054 (605) |
| H = 26 | +10,2 [−3,7 ; +25,5] ; +0,372 (592) | +11,5 [−3,4 ; +29,0] ; +0,371 (584) | +12,6 [−3,2 ; +29,6] ; +0,401 (563) |
| H = 48 | +1,6 [−23,0 ; +24,5] ; +0,198 (521) | +6,2 [−19,3 ; +29,6] ; +0,255 (517) | +7,1 [−19,5 ; +32,0] ; +0,235 (499) |

### ↳ F3 · x1 déjà retourné hors Q4

Espérance nette : bps [IC 95 %] ; ATR (trades)

| Horizon | échantillon entier | glissante 500 signaux | expansive |
|---|---|---|---|
| H = 6 | −2,7 [−12,1 ; +5,7] ; −0,095 (669) | −2,6 [−12,2 ; +5,8] ; −0,085 (669) | −2,2 [−11,7 ; +6,1] ; −0,087 (653) |
| H = 13 | −2,7 [−14,9 ; +9,2] ; +0,000 (609) | −2,8 [−15,3 ; +9,2] ; −0,006 (610) | −3,1 [−16,2 ; +8,9] ; −0,023 (597) |
| H = 26 | +10,0 [−10,7 ; +29,7] ; +0,138 (566) | +10,8 [−10,4 ; +31,1] ; +0,140 (569) | +9,0 [−12,7 ; +29,3] ; +0,088 (555) |
| H = 48 | −1,0 [−26,2 ; +22,8] ; +0,134 (491) | −6,0 [−29,5 ; +16,9] ; −0,005 (492) | −2,1 [−26,5 ; +21,0] ; +0,071 (484) |

## H. Contrôle C — Capital à risque constant par trade

Taille de position telle qu'un ATR14(t) représente une part fixe du capital, levier plafonné à 1x ; frais proportionnels au notionnel. Cellules : PnL composé ; max drawdown valorisé. Dernière colonne : exposition moyenne et part des trades plafonnés, à H = 26 (ancre : sortie native).

### 1 ATR = 0,25 % du capital, 5 bps aller-retour

| Configuration | H = 6 | H = 13 | H = 26 | H = 48 | Exposition ; plafonnés |
|---|---|---|---|---|---|
| Ancre native P6.5d | −76 % ; −86 % (sortie native) |  |  |  | 0,56 ; 12 % |
| Tous | −81 % ; −85 % | −64 % ; −74 % | −74 % ; −78 % | −79 % ; −87 % | 0,54 ; 11 % |
| Tous hors R3 | −64 % ; −71 % | −47 % ; −62 % | −55 % ; −72 % | 88 % ; −50 % | 0,55 ; 11 % |
| Tous hors nis_z_100 Q4 | −60 % ; −67 % | −10 % ; −45 % | −23 % ; −57 % | −44 % ; −56 % | 0,56 ; 12 % |
| R1 | −20 % ; −23 % | −30 % ; −41 % | −63 % ; −65 % | −33 % ; −53 % | 0,53 ; 10 % |
| R2 | −35 % ; −45 % | −20 % ; −43 % | 31 % ; −27 % | −6 % ; −49 % | 0,58 ; 13 % |
| ↳ F2b · x1 déjà retourné | −15 % ; −24 % | 3 % ; −17 % | 54 % ; −16 % | 17 % ; −32 % | 0,59 ; 14 % |
| ↳ F3 · x1 déjà retourné | −23 % ; −32 % | −24 % ; −39 % | −15 % ; −48 % | −4 % ; −56 % | 0,57 ; 13 % |
| R3 | −49 % ; −55 % | −53 % ; −61 % | −78 % ; −81 % | −73 % ; −81 % | 0,53 ; 11 % |
| nis_z_100 Q4 | −54 % ; −56 % | −56 % ; −63 % | −65 % ; −66 % | −19 % ; −35 % | 0,47 ; 5 % |
| Tous hors R3 et hors nis_z_100 Q4 | −49 % ; −56 % | −9 % ; −42 % | −3 % ; −44 % | 98 % ; −46 % | 0,57 ; 12 % |
| R1 hors nis_z_100 Q4 | −12 % ; −20 % | −16 % ; −32 % | −36 % ; −44 % | −14 % ; −45 % | 0,55 ; 11 % |
| R2 hors nis_z_100 Q4 | −26 % ; −38 % | 1 % ; −31 % | 122 % ; −20 % | −5 % ; −37 % | 0,60 ; 16 % |
| ↳ F2b · x1 déjà retourné hors nis_z_100 Q4 | −14 % ; −23 % | 2 % ; −20 % | 72 % ; −13 % | 18 % ; −31 % | 0,60 ; 15 % |
| ↳ F3 · x1 déjà retourné hors nis_z_100 Q4 | −14 % ; −23 % | −3 % ; −27 % | 16 % ; −34 % | 3 % ; −47 % | 0,61 ; 17 % |
| R3 en continuation | −47 % ; −53 % | −36 % ; −51 % | 60 % ; −34 % | 49 % ; −33 % | 0,53 ; 11 % |
| nis_z_100 Q4 en continuation | −11 % ; −17 % | 4 % ; −37 % | 42 % ; −24 % | −34 % ; −46 % | 0,47 ; 5 % |

### 1 ATR = 0,25 % du capital, 10 bps aller-retour

| Configuration | H = 6 | H = 13 | H = 26 | H = 48 | Exposition ; plafonnés |
|---|---|---|---|---|---|
| Ancre native P6.5d | −96 % ; −97 % (sortie native) |  |  |  | 0,56 ; 12 % |
| Tous | −98 % ; −98 % | −91 % ; −92 % | −89 % ; −90 % | −87 % ; −91 % | 0,54 ; 11 % |
| Tous hors R3 | −91 % ; −91 % | −81 % ; −84 % | −78 % ; −83 % | 19 % ; −54 % | 0,55 ; 11 % |
| Tous hors nis_z_100 Q4 | −92 % ; −92 % | −71 % ; −78 % | −63 % ; −74 % | −65 % ; −69 % | 0,56 ; 12 % |
| R1 | −52 % ; −53 % | −57 % ; −62 % | −75 % ; −76 % | −51 % ; −63 % | 0,53 ; 10 % |
| R2 | −62 % ; −66 % | −49 % ; −56 % | −11 % ; −41 % | −31 % ; −58 % | 0,58 ; 13 % |
| ↳ F2b · x1 déjà retourné | −33 % ; −39 % | −17 % ; −31 % | 26 % ; −20 % | −2 % ; −34 % | 0,59 ; 14 % |
| ↳ F3 · x1 déjà retourné | −43 % ; −47 % | −43 % ; −49 % | −35 % ; −55 % | −22 % ; −59 % | 0,57 ; 13 % |
| R3 | −72 % ; −75 % | −73 % ; −76 % | −86 % ; −87 % | −80 % ; −86 % | 0,53 ; 11 % |
| nis_z_100 Q4 | −70 % ; −71 % | −69 % ; −72 % | −74 % ; −75 % | −35 % ; −45 % | 0,47 ; 5 % |
| Tous hors R3 et hors nis_z_100 Q4 | −84 % ; −85 % | −63 % ; −72 % | −49 % ; −63 % | 29 % ; −49 % | 0,57 ; 12 % |
| R1 hors nis_z_100 Q4 | −44 % ; −45 % | −44 % ; −51 % | −55 % ; −59 % | −35 % ; −53 % | 0,55 ; 11 % |
| R2 hors nis_z_100 Q4 | −53 % ; −58 % | −30 % ; −46 % | 60 % ; −22 % | −27 % ; −45 % | 0,60 ; 16 % |
| ↳ F2b · x1 déjà retourné hors nis_z_100 Q4 | −31 % ; −38 % | −17 % ; −32 % | 42 % ; −17 % | −0 % ; −34 % | 0,60 ; 15 % |
| ↳ F3 · x1 déjà retourné hors nis_z_100 Q4 | −31 % ; −35 % | −20 % ; −34 % | −3 % ; −39 % | −12 % ; −51 % | 0,61 ; 17 % |
| R3 en continuation | −71 % ; −72 % | −63 % ; −67 % | 3 % ; −47 % | 8 % ; −34 % | 0,53 ; 11 % |
| nis_z_100 Q4 en continuation | −42 % ; −43 % | −27 % ; −44 % | 6 % ; −34 % | −48 % ; −55 % | 0,47 ; 5 % |

### 1 ATR = 1,00 % du capital, 5 bps aller-retour

| Configuration | H = 6 | H = 13 | H = 26 | H = 48 | Exposition ; plafonnés |
|---|---|---|---|---|---|
| Ancre native P6.5d | −98 % ; −99 % (sortie native) |  |  |  | 0,98 ; 90 % |
| Tous | −96 % ; −98 % | −89 % ; −93 % | −96 % ; −98 % | −97 % ; −99 % | 0,97 ; 90 % |
| Tous hors R3 | −81 % ; −89 % | −62 % ; −81 % | −85 % ; −94 % | 1 % ; −88 % | 0,98 ; 90 % |
| Tous hors nis_z_100 Q4 | −79 % ; −87 % | −9 % ; −61 % | −28 % ; −82 % | −34 % ; −66 % | 0,98 ; 91 % |
| R1 | −34 % ; −45 % | −41 % ; −59 % | −87 % ; −90 % | −71 % ; −84 % | 0,98 ; 90 % |
| R2 | −47 % ; −67 % | −43 % ; −67 % | 19 % ; −57 % | −33 % ; −73 % | 0,98 ; 92 % |
| ↳ F2b · x1 déjà retourné | −21 % ; −40 % | 17 % ; −31 % | 52 % ; −41 % | −7 % ; −58 % | 0,98 ; 93 % |
| ↳ F3 · x1 déjà retourné | −33 % ; −51 % | −48 % ; −60 % | −15 % ; −67 % | −7 % ; −66 % | 0,98 ; 90 % |
| R3 | −79 % ; −84 % | −87 % ; −90 % | −97 % ; −98 % | −92 % ; −97 % | 0,97 ; 89 % |
| nis_z_100 Q4 | −81 % ; −84 % | −87 % ; −91 % | −92 % ; −93 % | −55 % ; −76 % | 0,96 ; 85 % |
| Tous hors R3 et hors nis_z_100 Q4 | −63 % ; −76 % | 16 % ; −56 % | −12 % ; −74 % | 178 % ; −78 % | 0,98 ; 91 % |
| R1 hors nis_z_100 Q4 | −18 % ; −39 % | −14 % ; −45 % | −55 % ; −72 % | −31 % ; −73 % | 0,98 ; 91 % |
| R2 hors nis_z_100 Q4 | −37 % ; −60 % | −3 % ; −52 % | 214 % ; −44 % | −31 % ; −64 % | 0,99 ; 93 % |
| ↳ F2b · x1 déjà retourné hors nis_z_100 Q4 | −17 % ; −39 % | 22 % ; −34 % | 85 % ; −40 % | −3 % ; −59 % | 0,99 ; 94 % |
| ↳ F3 · x1 déjà retourné hors nis_z_100 Q4 | −24 % ; −39 % | −17 % ; −42 % | 50 % ; −45 % | 5 % ; −64 % | 0,98 ; 93 % |
| R3 en continuation | −61 % ; −71 % | −37 % ; −71 % | 306 % ; −49 % | 33 % ; −68 % | 0,97 ; 89 % |
| nis_z_100 Q4 en continuation | −26 % ; −40 % | 26 % ; −59 % | 90 % ; −60 % | −65 % ; −77 % | 0,96 ; 85 % |
