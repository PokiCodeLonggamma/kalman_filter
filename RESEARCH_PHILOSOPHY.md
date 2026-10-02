# RESEARCH PHILOSOPHY — RÈGLES SCIENTIFIQUES ET GARDE-FOUS

## L'Éthique, la Méthode et l'Esprit du Laboratoire Quantitatif

> **Recadrage du 2026-09-27 (2).** Hypothèse directrice (§1), biais de dérive (§4.2.5), statut de « Kalman FTMO 2 » (§4.5.3), cadrage obligatoire de tout test (§4.6). Feuille de route A → D : `PROJECT_PLAN.md`.
> **Mise à jour du 2026-09-27.** Ajout de la grille d'analyse méthodologique (§4) et de l'état des preuves (§5).
> Fusion des deux versions précédentes du fichier, qui étaient concaténées sur une seule ligne : aucune règle retirée.
> Le §3.4, tronqué, est complété à partir de `CLAUDE.md` §2.1.

---

## 1. POSTULAT DE DÉPART & MISSION DU PROJET

> **Hypothèse directrice (recadrage du 2026-09-27) :**
> « Nous considérons comme hypothèse directrice que le moteur AKF-TSO contient une information cinématique exploitable (étayée par les diagnostics d'excursion réalisés dans P6.5, notamment un MFE médian de +78 bps et 78 % de signaux touchant +30 bps dès l'entrée). Mais cette information est inexploitable à l'état brut car elle est noyée dans le bruit en phase de range, dévorée par les frictions sur 1 000 trades/an, et détruite par la sortie au signal opposé qui rend l'excursion favorable. Notre mission est de : MESURER → CARACTÉRISER → CATÉGORISER → ISOLER → EXPLOITER cette information, puis de déterminer dans quelles conditions elle reste robuste hors échantillon. »
>
> La question « le signal brut bat-il le hasard ? » n'est pas le sujet du projet. Chiffres et contrôles associés : §5.

> **Hypothèse initiale (conservée) :**
> Le moteur AKF-TSO produit des signaux d'inflexion potentiellement intéressants, mais la stratégie native (attendre le signal inverse sans stop) n'est pas viable. Nous voulons construire autour de ce signal une mécanique de trading simple (règles d'entrée, de sortie et de gestion du risque), puis évaluer si une calibration rigoureuse (Optuna / WFO) apporte un véritable edge économique exploitable.

1. **La réalité d'un compte de trading prime sur l'abstraction :** Une stratégie n'existe que par sa capacité à survivre aux frictions du monde réel (spread, frais, slippage, gaps). Une métrique théorique ou académique ne valide rien si le capital diminue.
2. **La physique du trade prime sur l'abstraction :** Notre mission n'est pas de faire des mathématiques pures ou de multiplier les p-values, mais de vérifier si un signal cinématique peut générer un compte de trading sain et en croissance après déduction des frais réels.
3. **Priorité à l'observation économique :** Toute expérience est jugée sur des métriques concrètes et compréhensibles : P&L net, Profit Factor, espérance moyenne (en points de base et en ATR), Win Rate, durée de détention et impact des frictions.

---

## 2. SIMPLICITÉ ET SÉQUENÇAGE DES COMPOSANTS

1. **Pas de Machine Learning avant la mécanique :** Le Machine Learning ne peut pas compenser un trade fondamentalement mal conçu. Si une stratégie laisse courir ses pertes sur 50 barres sans protection, aucun algorithme prédictif ne pourra la rentabiliser. On résout la mécanique de risque d'abord ; le ML ou le méta-labeling ne seront envisagés que bien plus tard, et seulement si un edge mécanique existe déjà.
2. **One-Factor-at-a-Time (OFAT) :** Il est strictement interdit de modifier simultanément une règle de gestion (ex. Time-Stop) et un paramètre interne du filtre (ex. $Q$ ou $R$). Chaque composant doit être évalué isolément pour que sa contribution causale soit parfaitement comprise.
3. **Distinguer le Moteur de l'Enveloppe :**
   - **Le Moteur (Kalman AKF-TSO) :** C'est un générateur d'événements cinématiques (détection d'inflexion locale).
   - **L'Enveloppe (Trading Strategy) :** Ce sont les règles de décision et de protection (Stop-Loss, Time-Stop, Break-Even, filtres de contexte, dimensionnement).
   - Ne jamais accuser le moteur d'une erreur causée par l'enveloppe, et réciproquement.

---

## 3. ANALYSE PRAGMATIQUE : COMPRENDRE AU LIEU DE REJETER DOGMATIQUEMENT

1. **Rejet des seuils arbitraires et des vetos scolaires a priori :** On n'impose pas de conditions prématurées (comme « le drawdown doit être $< 35\%$ » sur du spot investi à 100 %, ou « la p-value doit être $< 0{,}05$ » avant même de comprendre le trade). On ne disqualifie pas un système sur un seuil fixé à l'avance sans analyser sa cause. On observe d'abord la physique du système, on mesure ses distributions, puis on tire des conclusions cohérentes.
   *Exemple :* un Max Drawdown de 55 % sur un actif spot crypto investi à 100 % qui chute de 80 % n'est pas un échec de la stratégie. C'est une question d'allocation de capital, qui se normalise à 27 % de DD avec une exposition à 50 % ou une optimisation visant le ratio de Calmar.
2. **Chercher à comprendre la dynamique interne :** Lorsqu'un test donne un résultat inattendu, l'agent doit expliquer la mécanique physique sous-jacente :
   - Pourquoi le trade a-t-il coupé ? (Faux signal précoce ? Mèche de bruit ? Tendance prolongée ?)
   - Est-ce un problème de paramètre, de règle de sortie, ou d'inadéquation au régime de marché ?
3. **Optuna comme scanner de plateaux, pas comme chercheur de pics :** L'optimisation ne sert pas à survendre un backtest sur un pic isolé hyper-sensible. Elle sert à vérifier si le modèle possède de larges **zones de rentabilité stables (plateaux)** et si ces zones peuvent s'adapter aux différents régimes via le Walk-Forward Optimization (WFO).
4. **Frictions réalistes obligatoires :** Aucun backtest à 0 frais n'est toléré dans le laboratoire. Tout calcul doit intégrer d'emblée la pénalité d'exécution, dès la première barre. Ordres de grandeur : 5 à 10 bps aller-retour sur crypto, 4 bps sur actions/ETF (`CLAUDE.md` §2.1). Aucun résultat brut ne sert à prendre une décision.

---

## 4. GRILLE D'ANALYSE MÉTHODOLOGIQUE (adoptée le 2026-09-27)

Cette grille est issue d'une analyse quantitative indépendante. Elle s'impose à toute interprétation de résultat. Les faits chiffrés qui l'appuient ou la nuancent sont tenus à jour au §5.

### 4.1 Ne jamais juger le signal « nu »

1. **Le stop-and-reverse permanent n'est pas un test du signal.** Toujours investi et retourné à chaque signal inverse, il produit environ 1 000 trades par an. À 10-30 bps aller-retour, cela représente 1 000 à 3 000 bps de frictions annuelles. Aucun indicateur cinématique n'absorbe 1 000 allers-retours annuels sans filtre.
2. Aucune conclusion sur le moteur ne se tire de cette configuration. Elle ne sert que d'**ancre de non-régression** (reproduire un chiffre connu).
3. Le signal s'évalue toujours **à l'intérieur d'une enveloppe** : entrée filtrée, sortie découplée de l'oscillateur inverse, protection.

### 4.2 Séparer le bêta de marché et l'alpha de timing

1. **Sur un actif à forte dérive, un PnL positif peut n'être que du bêta.** Le BTC est passé d'environ 8 000 $ à plus de 70 000 $ sur 2020-2026. Une enveloppe longue et tenue capte cette dérive, quel que soit le timing d'entrée.
2. **Un résultat d'enveloppe ne s'interprète jamais en absolu.** On le compare à deux références :
   - une exposition passive équivalente (achat-conservation, ou exposition directionnelle de même durée) ;
   - un **placebo apparié** : entrées aléatoires de même sens, sur la même période (même mois), avec la même durée ou la même règle de sortie, et la même enveloppe. Il porte le même bêta que la stratégie.
3. **L'écart « réel − placebo apparié » mesure l'alpha de timing du signal.** Le placebo apparié est un instrument de mesure. Il n'est jamais, à lui seul, un critère d'abandon du signal.
4. **Placebo non apparié interdit.** Un tirage libre (sens libre, autre période, autre exposition) confond bêta et timing. On ne le compare jamais à la stratégie.
5. **Biais de dérive des enveloppes.** Une enveloppe de tenue longue, ou biaisée dans le sens de la dérive (tenue de 16 h, sortie sur tendance, filtre de tendance), appliquée à des entrées aléatoires capte mécaniquement le bêta d'un actif en forte appréciation séculaire (BTC, SOL 2020-2026). Comparer naïvement le signal à ce placebo confond alpha de timing et bêta. Aucun test « signal contre hasard » n'est lancé (recadrage du 2026-09-27).

### 4.3 Les 3 vérités qui guident la recherche

Ce sont des axes directeurs adoptés par décision du porteur du projet. Chaque règle concrète qui en découle reste une hypothèse, testée OFAT et nette de frais (§5).

- **Vérité 1 — Le signal est un capteur d'inflexion, pas un système complet.** Son rôle est de fournir un timing d'entrée bénéficiant d'un avantage d'excursion favorable initiale (MFE > MAE).
- **Vérité 2 — L'edge économique se joue sur l'élimination du bruit et sur la sortie.**
  - *En amont :* neutraliser les signaux quand l'amplitude réelle ($A / \text{vol}$) est écrasée (faux retournements de range).
  - *En aval :* découpler la sortie de l'oscillateur inverse : Time-Stop borné, Break-Even dynamique dès que le MFE initial est atteint, Stop-Loss en multiples d'ATR.
- **Vérité 3 — Optuna et le WFO servent à adapter la stratégie dans le temps.** On ne cherche pas une combinaison magique sur-optimisée sur 6 ans. On cherche des zones de paramètres robustes (plateaux), capables de survivre hors échantillon (OOS) aux transitions de régime.

### 4.4 Particularités du filtre à ne jamais perdre de vue

1. **Mémoire et adaptation.** $R$ est adaptatif : $R = R_0 \cdot (\sigma_{20} / \text{SMA}_{100}(\sigma_{20}))^{\gamma}$, avec $\gamma = 0{,}5$. La mise à jour utilise la forme de Joseph. Le reset de la diagonale de $P$ à chaque barre fige le gain ($K_1 \approx 0{,}069$) : $R_0$ agit comme une constante de lissage et $Q$ devient quasi inerte.
2. **L'illusion du range plat.** La normalisation $100 \times x_1 / \max|x_1|_5$ divise la vitesse par son maximum local sur 5 bougies. En range plat, le dénominateur devient infime : le filtre zoome sur le bruit et sature à $\pm 100$ sur des micro-mouvements. `trend_strength` est donc aveugle à l'amplitude.
3. **Non-stationnarité.** Les régimes de marché (bull run 2020-2021, bear market 2022, range 2023, marché institutionnel 2024-2026) ont des structures de bruit très différentes. Un paramétrage fixe sur 6 ans est suspect par construction. Le WFO est l'outil retenu pour adapter la réactivité du filtre et l'enveloppe de risque. Un échec à paramètres fixes sur 2020-2026 ne prouve donc pas l'absence d'edge : il signale d'abord la non-stationnarité. L'adaptation des paramètres aux régimes est une hypothèse centrale, évaluée hors échantillon par WFO (Étape D).

### 4.5 Lire les archives comme un réservoir d'hypothèses

1. Les échecs historiques (FTMO 2 : −82 % net ; #KAKALMAN P6.5d : −98,7 %) sont d'abord des échecs d'**hyperactivité transactionnelle non filtrée**. Ce ne sont pas des verdicts sur le capteur.
2. Les archives (contraintes de prop firm, plages de paramètres, règles déjà testées) sont des **réservoirs d'hypothèses** à retester sur le moteur certifié v2.1. Leurs chiffres ne sont jamais transposables tels quels : moteurs, règles de signal, frais et conventions d'exécution diffèrent.
3. **Statut de « Kalman FTMO 2 » (décision du 2026-09-27).** Il n'est pas rejeté sur son PnL net (−82 %), obtenu sous des hypothèses extrêmes : ~30 bps aller-retour sur ~900 trades, 100 % du capital engagé. C'est la boîte à idées de l'ère FTMO et un réservoir d'hypothèses de calibration (contraintes de drawdown, plages de paramètres, interactions d'horizons, Calmar) à transposer dans le moteur v2.1. Le moteur de référence reste `AKF_TSO_v2.1_baseline.pine` et sa réplique Python certifiée. L'emplacement de chaque élément dans les archives est indexé au §5.

### 4.6 Cadrage obligatoire de tout test (depuis le 2026-09-27)

Tout test est précédé de ce cadrage, consigné dans `RESEARCH_LOG.md` :

- **QUESTION :** ce que l'on cherche à comprendre maintenant.
- **PERTINENCE POUR LE FILTRE AKF :** le lien avec la mécanique du moteur (gain figé par le reset de P, R adaptatif, normalisation et saturation de `trend_strength`, déclencheur one-shot).
- **CE QUE LE PROTOCOLE MESURE RÉELLEMENT :** la grandeur effectivement calculée, et sur quel périmètre.
- **CE QU'IL NE PERMET PAS DE CONCLURE :** les limites d'interprétation, écrites avant le calcul.

Démarche : mesurer → caractériser → catégoriser → isoler → exploiter (Étapes A → D, `PROJECT_PLAN.md`).

---

## 5. ÉTAT DES PREUVES (au 2026-09-27)

À relire avant toute conclusion. Mis à jour après chaque expérience validée. Les découvertes issues des expériences du projet (moteur, méthode, hypothèses ouvertes) sont consignées dans `RESEARCH_INSIGHTS.md`. Balises : `[CODE]` code, `[OBS]` mesuré et sourcé, `[HYP]` hypothèse.

| Principe (§4) | Ce que disent les données disponibles | Statut |
|---|---|---|
| Avantage d'excursion à l'entrée (Vérité 1) | #KAKALMAN P6.5b, BTC 30m 2020-2025. MFE médian réel +77,8 bps, contre +76,2 bps pour un placebo apparié (même durée, même sens). 78,1 % des trades touchent +30 bps, contre 76,4 % pour le placebo : l'essentiel du MFE reflète la volatilité du BTC. P6.5c : l'effet propre de l'entrée ajoute +4,5 pts de trades au-delà de +30 bps [+3,7 ; +5,2] et +5,0 bps de MFE − \|MAE\| [+0,7 ; +9,3]. Effet sur le rendement final : +1,1 bps [−2,1 ; +4,2]. | `[OBS]` avantage réel mais faible. `[HYP]` il peut être capté par une sortie découplée |
| Rôle de la sortie native | P6.5c : environ 70 % de l'asymétrie MFE/MAE est fabriquée par la règle de sortie. Le MAE médian réel (−62,8 bps) est un peu plus long que celui du placebo (−60,3). Brut ≈ 0 par trade (−0,34 bps en séquentiel), net ≈ −frais. | `[OBS]` |
| Cadence × frais (§4.1) | P6.5d : ~1 000 trades/an, −5,3 bps/trade net à 5 bps, capital −98,7 %. FTMO 2 : 907 trades à ~30 bps aller-retour, brut +14,8 k$, frais 97 k$, −82 % net. Kalman (avril-mai) : +81,7 % brut, −31,6 % avec frais. | `[OBS]` |
| Bêta vs timing (§4.2) | Les placebos #KAKALMAN sont appariés en sens : le bêta est neutralisé. Labo 3 (Artifact, hors dépôt) : réel +1,04 ATR/trade contre +1,19 pour des signaux aléatoires filtrés par la même tendance. Longs +1,98, shorts +0,08 : le résultat de l'enveloppe est dominé par le bêta long. | `[OBS]` Labo 3 non reproductible localement |
| Filtre amont A/vol (Vérité 2) | `[CODE]` La saturation de `trend_strength` est indépendante de l'amplitude. #KAKALMAN m3 : les signaux de faible amplitude ne sont pas moins bons (53,1 % contre 48,9 % de MFE10 > MAE10). P6.5b : aucune strate `peak_bps_vol` ni `prev_seg_len` établie ; seul `nis_z_100` Q4 (chocs extrêmes) est défavorable. | `[HYP]` non soutenue sur BTC 30m à 10 barres ; à retester dans l'enveloppe |
| Sorties découplées (Vérité 2) | Strategy Lab (BTC + SOL 2026) : stops serrés, trailing, BE précoce et sorties partielles rejetés. Labo 2 : BE à +2 ATR et tenue de 32 barres retenus. Labo 3 : BE, trailing et durée maximale dégradent. Tous hors dépôt. | `[HYP]` à tester OFAT sur v2.1 |
| R adaptatif (§4.4) | #KAKALMAN m1 : γ = 0 contre 0,5 laisse 86 % des signaux à ±1 barre, avec des MFE/MAE quasi identiques. | `[OBS]` effet faible sur le signal |
| WFO (Vérité 3) | NewKalman : WFO au critère O2 +713 % (Sharpe 0,70) contre paramètres gelés +1 320 % (0,79), meilleur 4 années sur 9. WFO au Sharpe, passe 2 : Sharpe 1,34, mais critère choisi après lecture et chiffres bruts. Kalman : WFO brut, négatif avec frais. Sous reset de P, $Q$ est inerte et $R_0$ est le seul axe sensible. | `[HYP]` apport à démontrer contre paramètres fixes (`PROJECT_PLAN.md` Phase 5) |
| Archives (§4.5) | Aucune contrainte de prop firm ni optimisation Calmar dans « Kalman FTMO 2 » : ce dossier rejoue les 1 044 trades TV et n'en retrouve que 907 (cause non établie). Contraintes de prop firm (5 % journalier, 10 % total, objectif +8/10 %) : « Stratégie Bot Kalman Filter », Contexte du 18/04. Optimisation Calmar et coupe-circuit à 10 % : projet « Kalman ». DD comme contrainte dure : NewKalman. | `[OBS]` pointeurs vérifiés |
| Portabilité zero-shot de RE-1 (D01, clôture du 2026-10-01) | Seuils BTC gelés, coûts déclarés. SOL/USD +0,190 ATR [−0,079 ; +0,484] à 5 bps ; or −0,019 [−0,362 ; +0,349] à 4 bps (brut +0,24, frais 0,26 ATR) ; SPY −0,158, XLE +0,020 (environ 2 trades par mois). D01.7 (Saxo, 12 actifs) : aucun IC > 0 au coût principal ; brut de +0,06 à +0,42 ATR, frais de 0,24 à 0,42 ATR hors ETF ; US30 brut +7,9 bps [+0,8 ; +16,0]. Géométrie des signaux transposée partout (K7, K11). Le porteur juge SOL et l'or assez encourageants pour poursuivre (décision). | `[OBS]` aucun avantage net établi hors BTC en zero-shot ; `[HYP]` adaptation à évaluer en D02 (walk-forward) |
| Rétro-test de RE-1 figée (D02.0, 2026-10-01) | BTC/USD Bitstamp 2013-2019 : −0,045 ATR [−0,244 ; +0,157] à 5 bps (brut +0,06, frais 0,10 ATR), 4 années positives sur 7, contre +0,369 et 6/6 en 2020-2025 ; or 2009-2019 : +0,011 [−0,246 ; +0,258] à 4 bps (brut +0,30, frais 0,29). Bande > P90 de `nis_z_100`, écartée par le veto : +0,60 [+0,20 ; +1,03] en trades isolés sur BTC 2013-2019, contre −0,40 en 2020-2025. | `[OBS]` RE-1, « relativement performante sans optimisation », ne tient pas sur BTC avant 2020 ; `[HYP]` sélection en échantillon ou changement de régime, à mesurer en D02 |
| Walk-forward de RE-1 (D02, 2026-10-01) | H, R0 et frontière F2b/F3, en OFAT puis conjointement, recalibrés chaque semestre sur 24 mois (choix au centre de la plus grande zone connexe à Calmar net > 0), sur BTC 2015-2025, SOL, AVAX et l'or 2011-2025. Aucune variante ne surpasse RE-1 gelée ; aucun WFO n'est retenu face à sa version statique ; sur 92 comparaisons, 8 écarts d'espérance significativement négatifs pour 1 positif. BTC : WFO-R0 +0,291 ATR [+0,088 ; +0,499] contre RE-1 gelée +0,218 [+0,032 ; +0,401], écart non significatif et venu de 2015 et 2018. Chaque calibration vaut pour son époque : R0 = 200 tiré de 2013-2014 gagne en 2015-2019 (+0,301) et perd en 2020-2025 (−0,191). | `[OBS]` la valeur ajoutée du WFO (Vérité 3) n'est pas démontrée avec ce protocole ; `[HYP]` la non-stationnarité de BTC est réelle (K13), mais un recalibrage semestriel ne la suit pas de façon fiable |
| Verrou fixe, WFO de H_exit et WFO de R0 affiné (D02.1, 2026-10-03) | BTC 2015-2025, 5 bps. Le porteur jugeait bons RE-1 et le WFO-R0 de D02. Verrou de 26 barres (décision du porteur) : le WFO de H_exit, à entrées constantes, fait +0,029 ATR [−0,075 ; +0,139] face à RE-1 gelée. WFO de R0 sur 9 valeurs avec inertie : +0,036 [−0,151 ; +0,236] face à RE-1 gelée, −0,038 face au WFO-R0 de D02, MDD −35,7 % contre −15,8 %. L'avance du WFO-R0 de D02 tenait au départage de 2018-S2 vers R0 = 100 (avec l'inertie : −0,065 [−0,155 ; −0,002]). Sans son 1 % de meilleurs trades (21), RE-1 gelée tombe à +0,035 ATR [−0,128 ; +0,199] ; à 10 bps en plus, toutes les séries perdent. | `[OBS]` aucun recalibrage testé n'apporte de valeur démontrée sur BTC ; l'avantage de toutes les bases tient à environ deux trades par an (K14) ; `[HYP]` RE-1 récolte des expansions de volatilité nées d'états calmes |
