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
