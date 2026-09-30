# EXP-D01 — Portabilité de RE-1 figée, sans réglage : SOL/USD, CFD or, CFD WTI

- **Date :** 2026-09-30.
- **Étape :** D, première expérience. **Descriptive** par décision du porteur : aucun critère de réussite ou d'échec, aucun classement des actifs, aucune modification de RE-1.
- **Actifs et périodes :**
  - BTC/USD Bitstamp, 2020-2025 : référence ;
  - SOL/USD Coinbase, du 2021-06-17 au 2025-12-31 ;
  - CFD or XAU/USD (HistData), 2020-2025 ;
  - CFD WTI (HistData) : audité, puis **bloqué avant backtest** (voir §2.4) ;
  - 2026, ETH et XRP ne sont ni téléchargés ni lus.
- **Frais :** SOL 5 et 10 bps (lecture principale à 5 bps) ; XAU 4 bps ; BTC 5 et 10 bps. Ce sont des hypothèses de frais d'exécution, pas une mesure du glissement. Aucun stress de glissement n'est appliqué.
- **Stratégie :** RE-1 telle quelle.
  - Moteur v2.1 par défaut : R0 = 100, q1 = q2 = 0,01, γ = 0,5 ; oscillateur N2 = 5, R2 = 3.
  - Univers R2 = (F2b | F3) & x1 déjà retourné, hors `nis_z_100` > seuil.
  - F2b sans stop ; F3 SL-B à l'extremum (δ = 0, plancher 0,25 ATR).
  - H = 26 barres de 30 min de la série ; entrée à open[t + 1] ; une position à la fois ; cooldown.
- **Transfert des seuils, option (a) :** les valeurs numériques de BTC sont gelées à la précision machine : médiane de `leg_atr` = 2,8233, P75 de `nis_z_100` = 1,2245. Les seuils 0,50 et 0,85 de `retrace_ratio` sont fixes. Les quantiles locaux sont publiés à titre descriptif et n'entrent jamais dans l'exécution.
- **Code :**
  - `src/marketdata/` : acquisition et audit, avec tests ;
  - `src/strategy/re1.py` : RE-1 générique, avec tests ;
  - `experiments/D01/donnees_D01.py` : acquisition ;
  - `experiments/D01/run_D01.py` : `--audit`, puis le run.

## 0. Cadrage

- **QUESTION :** que devient RE-1, transférée telle quelle, sur des marchés de structures différentes ?
  - SOL/USD : crypto 24/7, environ deux fois plus volatile que BTC.
  - L'or au comptant : CFD, cotation 23 h sur 24, 5 jours sur 7.
  - Le WTI : CFD sur le contrat à terme.
- **PERTINENCE POUR LE FILTRE AKF :**
  - Le déclencheur est invariant d'échelle : gain figé par le reset de P, R adaptatif selon le rapport rv/av, oscillateur normalisé par max|x1|.
  - Les descripteurs de RE-1 sont en ATR14(t) et en z-score. Le transfert teste donc si la cinématique retenue sur BTC existe ailleurs à paramètres identiques : sortie de range, x1 déjà retourné, sans choc d'innovation.
  - Les CFD ajoutent des trous de séance (pause quotidienne, week-end) que BTC n'a pas.
- **CE QUE LE PROTOCOLE MESURE RÉELLEMENT :** pour chaque actif, sur sa période disponible jusqu'au 2025-12-31 :
  - les 8 métriques nettes aux frais de l'actif ;
  - l'espérance et le timing en ATR et en bps, avec IC par grappes mensuelles ;
  - le capital à 0,25 % par ATR14(t) et à 1x ;
  - Long/Short, F2b/F3, stops de F3, années, terciles de volatilité ;
  - `nis_z_100` face au seuil BTC, et ses bandes (trades isolés) ;
  - l'audit des données.
- **CE QU'IL NE PERMET PAS DE CONCLURE :**
  - pas de validation sur le hold-out ;
  - pas de comparaison statistique ni de classement des actifs ;
  - rien sur l'optimalité des seuils transférés, ni sur D02 ;
  - les coûts réels ne sont pas modélisés (spread, financement et swaps des CFD) ;
  - les sources (Coinbase, HistData) et les périodes (SOL depuis juin 2021) diffèrent de celles de BTC.

**Règle de lecture (fixée avant le calcul, en tête du script) :**
- **Aucun seuil de réussite sur une métrique de performance.**
- **Seul motif de blocage : la validité technique ou la qualité des données.** Cela couvre :
  - l'intégrité ;
  - une couverture contraire à la consigne ;
  - un proxy non validé.
- **L'actif bloqué est documenté, jamais remplacé.**
- **Définitions posées avant le calcul :**
  - régimes de volatilité : terciles de l'ATR14(t), en bps, des trades de l'actif ;
  - bandes de `nis_z_100` : bornes aux quantiles P70-P90 de l'atlas BTC (valeurs gelées) ; chaque signal R2 est joué seul ;
  - effet du stop de F3 : différence appariée RE-1 − RE-1 sans stop, sur les mêmes entrées.

## 1. Consignes du porteur, écarts vérifiés

**[DECISION] Consignes du 2026-09-30 :**
- Actifs retenus : SOL/USD, CFD WTI, CFD or. SOXS est écarté ; BTC 2013-2019 est laissé de côté.
- Transfert : option (a). D01 est descriptif. D02 est préparé mais non lancé.

**Changement de consigne en cours de session : SOL/USD, et non SOL/USDT.**
- La série Binance SOL/USDT, déjà téléchargée, a été supprimée sans avoir été backtestée.
- Le module Binance a été retiré.

**[OBS] Écart dans le prompt, vérifié.**
- La référence BTC à 10 bps vaut **+7,33 bps par trade [−4,83 ; +19,41]** (`resultats_C02bis.csv`, reproduit ici trade par trade), et non « +7,5 [−4,7 ; +19,5] ».
- L'estimation est positive et son IC traverse zéro. En ATR : +0,233 [−0,041 ; +0,511].

**[OBS] Rappel sur C05.** C05 n'a pas conclu que tous les tests de stabilité étaient réussis.
- Le verdict de C05 : plateaux pour la frontière F2b/F3 et pour la marge du stop, mais **falaise côté permissif pour l'exclusion `nis_z_100`**.
- C'est ce seuil qui est transféré tel quel ici.

**Alpaca non utilisé.**
- Alpaca ne cote ni l'or au comptant ni le WTI : il ne propose que des ETF (GLD, USO), qui seraient des proxys.
- Pour SOL, sa provenance 2021-2022 n'est pas documentée.
- Les clés fournies n'ont été écrites dans aucun fichier.

## 2. [CODE] Données : sources, construction, audit (étape 1, avant tout PnL)

### 2.1 Sources retenues et écartées

| Actif | Série retenue | Pourquoi | Écartées |
|---|---|---|---|
| SOL | Coinbase SOL-USD (TradingView : COINBASE:SOLUSD), spot en USD. Bougies natives de 15 min agrégées exactement en 30 min (UTC, :00/:30) | Marché USD le plus liquide, historique public sans clé | Binance SOL/USDT (cotation en USDT, écartée par le porteur) ; Binance.US SOLUSD (trou de mi-2023 à février 2025, puis quasi inactif) ; Bitstamp SOL/USD (coté seulement depuis 2022-2023) |
| XAU | HistData XAUUSD : CFD au comptant, bougies d'une minute (bid) | Seule source gratuite et sans compte couvrant 2020-2025 en intraday | Dukascopy (accès automatisés refusés, HTTP 429 « Bot blocked », export réservé à un bucket AWS payant ; blocage non contourné) ; OANDA (compte requis) |
| WTI | HistData WTIUSD : CFD sur le contrat NYMEX CL, bougies d'une minute (bid) | Même raison | Mêmes sources ; aucune source gratuite de contrat à terme continu en 30 min |
| Réf. WTI | FRED DCOILWTICO : spot WTI Cushing de l'EIA, quotidien | Contrôle de correspondance du CFD WTI | — |

Chaque série a son `.meta.json` versionné (instrument, nature, ticker, continuité, roulements, ajustements, fuseau, horaires, construction, couverture, empreintes). Les données brutes restent hors dépôt.

### 2.2 Audit commun

**[OBS] Aucun défaut d'intégrité** sur les quatre séries : pas de doublon, pas de désordre, pas de prix non positif, pas d'OHLC incohérent.

- **SOL :**
  - 79 577 barres ;
  - 4 trous (23 barres manquantes), le plus long de 5,5 h (2025-10-25) ;
  - 11 barres construites sur un seul quart d'heure.
  - La couverture commence le 2021-06-17, date de cotation de SOL-USD sur Coinbase. Aucune place en USD liquide et accessible ne couvre 2020. La consigne « au moins 2020-2025 » est structurellement impossible pour SOL/USD.
- **XAU :**
  - 69 381 barres, soit 66 % d'une cotation 24/7 ;
  - trous : 1 711 de 2 h au plus (pause quotidienne), 377 de 3 jours au plus (week-ends), 13 de plus de 3 jours (fêtes) ;
  - 404 barres (0,6 %) ont moins de 30 minutes cotées ;
  - la source n'a pas de volume ;
  - H = 26 barres dure 13 h calendaires en médiane, 20 h au P90, et 8 % des trades dépassent 24 h (week-end).

### 2.3 Deux défauts de la source HistData, corrigés et documentés

1. **Fuseau.**
   - **Ce que dit la source :** la FAQ annonce un EST fixe (UTC−5).
   - **Ce que montre l'audit :** avec UTC = étiquette + 5 h, la pause quotidienne de l'or et du WTI (17:00-18:00 heure de New York) tombe à 21:00 UTC seulement pendant les semaines où New York est déjà à l'heure d'été et l'Europe pas encore. Le reste de l'été, elle tombe à 22:00 UTC.
   - **Conclusion :** l'horloge est celle d'un serveur EET/EEST moins 7 h. Elle vaut UTC−5 en hiver européen et UTC−4 de fin mars à fin octobre.
   - **Correction :** étiquette + 7 h, localisée en Europe/Athens, puis UTC.
   - **Contrôle :** la pause tombe à 17:00-18:00 heure de New York dans **303 semaines sur 314** (XAU) et 195 sur 205 (WTI). Les autres semaines ont des heures vides en plus (fêtes), sans exception à 17:00. L'ouverture du dimanche est à 18:00 heure de New York dans 294 semaines sur 309.
   - **Effet :** seuls les horodatages bougent ; les valeurs des barres sont inchangées (décalage d'heures entières).
2. **Doublons.**
   - Une heure par an est répétée à l'identique, le lundi qui suit la fin de l'heure d'été européenne.
   - La continuité des prix est vérifiée et aucune heure ne manque.
   - Les doublons exacts sont supprimés (360 minutes pour XAU, 239 pour WTI). Des doublons de valeurs différentes auraient arrêté la construction.
3. **Limite non corrigible :** HistData ne divulgue pas le courtier qui fournit les cotations.

### 2.4 WTI : bloqué avant backtest

- **[OBS] Couverture.** HistData ne publie WTIUSD que jusqu'au **2023-12-01**. Pour 2024 et 2025, aucun fichier n'est disponible (jeton de téléchargement vide). Cela contredit la consigne « au moins 2020-2025 ».
- **[OBS] Correspondance avec le spot EIA.** Le CFD colle au spot : écart médian −0,02 $, corrélation des variations quotidiennes 0,978 hors 20-21 avril 2020.
- **[OBS] Les écarts de plus de 0,25 $ sont concentrés du 16 au 31 du mois** : 151 jours sur 211, autour des échéances.
  - Juin 2021 (contrat de juillet, expiré le 22/06) : le 21/06, CFD 73,10 contre spot 73,64.
  - 20 avril 2020 : CFD 20,27 contre spot −36,98. Le CFD était déjà sur le contrat de juin.
- **[HYP] Lecture :** le CFD suit le contrat du mois, non ajusté, et roule 1 à 2 jours avant l'échéance. Sa série porte donc chaque mois un saut égal à l'écart de calendrier. La règle n'est pas publiée par la source.
- **Décision :** WTI bloqué, décision du porteur requise (§7). Aucun backtest n'a été lancé sur le WTI.

## 3. [OBS] Signaux : la géométrie du déclencheur se transpose

| | BTC | SOL | XAU |
|---|---|---|---|
| Signaux par mois | 101 | 99 | 65 (moins de barres par jour) |
| x1 déjà retourné | 51,8 % | 52,3 % | 49,4 % |
| `leg_atr` P50 ; part sous le seuil BTC 2,8233 | 2,82 ; 50,0 % | 2,85 ; 49,1 % | 2,90 ; 47,7 % |
| `retrace_ratio` P50 | 0,62 | 0,60 | 0,59 |
| `nis_z_100` > 1,2245 : tous les signaux ; dans R2 | 25,0 % ; 22,5 % | 27,3 % ; 29,5 % | 24,9 % ; 24,7 % |
| P75 local de `nis_z_100` (descriptif) | 1,225 | 1,368 | 1,217 |
| ATR14 médian des signaux (bps) | 49,7 | 94,8 | 17,2 |
| Univers RE-1 (F2b ; F3) → trades | 1 452 (741 ; 711) → 1 080 | 1 030 (548 ; 482) → 769 | 849 (447 ; 402) → 651 |

- **Des distributions quasi identiques, alors que l'ATR en bps varie d'un facteur 5,5.**
  - `leg_atr`, `retrace_ratio` et `nis_z_100` ont pratiquement la même forme sur les trois actifs (figure `nis_D01.png`).
  - Les seuils BTC gelés retiennent donc les mêmes fractions de signaux.
- **[HYP]** La stationnarité en ATR constatée en A01 dans le temps se retrouve d'un actif à l'autre. Le transfert (a) sélectionne la même population cinématique partout.

## 4. [OBS] Résultats nets (H26 ; lecture principale en gras)

| Métrique | **BTC 5 bps** | BTC 10 bps | **SOL 5 bps** | SOL 10 bps | **XAU 4 bps** |
|---|---|---|---|---|---|
| Période ; années | 2020-2025 ; 6,00 | idem | 2021-06-17 → 2025 ; 4,54 | idem | 2020-2025 ; 6,00 |
| PnL composé : 0,25 %/ATR ; **1x** ; bps cumulés (1x) | +138 % ; **+204 %** ; +13 320 | +72 % ; **+77 %** ; +7 920 | +39 % ; **+173 %** ; +14 747 | +24 % ; **+86 %** ; +10 902 | +0,6 % ; **+5,4 %** ; +697 |
| Profit Factor : 1x ; pondéré | 1,20 ; 1,28 | 1,11 ; 1,17 | 1,17 ; 1,16 | 1,12 ; 1,10 | 1,04 ; 1,01 |
| Win Rate | 44,3 % | 42,8 % | 44,1 % | 43,4 % | 42,5 % |
| Espérance ATR [IC 95 %] | +0,369 [+0,098 ; +0,645] | +0,233 [−0,041 ; +0,511] | +0,190 [−0,079 ; +0,484] | +0,129 [−0,140 ; +0,425] | −0,019 [−0,362 ; +0,349] |
| Espérance bps à 1x [IC 95 %] | +12,3 [+0,2 ; +24,4] | +7,3 [−4,8 ; +19,4] | +19,2 [−3,6 ; +44,2] | +14,2 [−8,6 ; +39,2] | +1,1 [−4,9 ; +7,5] |
| MDD valorisé : 0,25 %/ATR ; **1x** | −13,5 % ; **−43,9 %** | −15,9 % ; **−48,0 %** | −13,1 % ; **−42,3 %** | −15,2 % ; **−44,4 %** | −13,6 % ; **−13,3 %** |
| Calmar : 0,25 %/ATR ; 1x | 1,16 ; 0,46 | 0,60 ; 0,21 | 0,58 ; 0,59 | 0,32 ; 0,33 | 0,01 ; 0,07 |
| Trades (par mois) ; stoppés | 1 080 (15,0) ; 24 % | idem | 769 (14,1) ; 24 % | idem | 651 (9,0) ; 26 % |
| Durée médiane : barres ; calendaire | 26 ; 13 h | idem | 26 ; 13 h | idem | 26 ; 13 h (P90 20 h) |
| Part des frais : 1x ; pondérée | 29 % ; 26 % | 58 % ; 52 % | 21 % ; 24 % | 41 % ; 48 % | 79 % ; 92 % |
| Timing ATR [IC] | +0,362 [+0,089 ; +0,638] | +0,226 [−0,050 ; +0,507] | +0,191 [−0,079 ; +0,490] | +0,130 [−0,140 ; +0,431] | −0,051 [−0,399 ; +0,306] |
| F2b ; F3 (ATR par trade) | +0,459 ; +0,267 | +0,326 ; +0,127 | +0,287 ; +0,076 | +0,228 ; +0,014 | −0,304 ; +0,313 |
| Années à espérance ATR > 0 | 6/6 | 5/6 | 5/5 (2021 partielle) | 4/5 | 2/6 (2020, 2022) |

**Exposition moyenne à 0,25 %/ATR :** BTC 60 %, SOL 30 %, XAU 98 %.
- Sur XAU, 89 % des trades sont plafonnés à 1x : l'ATR y est inférieur à 25 bps.
- C'est pourquoi, sur XAU, 0,25 %/ATR et 1x donnent presque les mêmes chiffres. Le budget de risque de 0,25 % par ATR n'y est pas atteint sans levier.

### 4.1 SOL/USD
- **Estimations positives, IC qui contiennent zéro.**
  - À 5 bps : +0,190 ATR et +19,2 bps par trade.
  - À 10 bps : +0,129 ATR et +14,2 bps.
- **L'espérance vient de F2b** (+0,287 ATR). F3 est proche de zéro : +0,076 ATR, soit −4,1 bps.
- **Long et Short sont positifs** : +0,246 et +0,136 ATR.
- **Le stop de F3 garde son rôle d'outil de risque**, comme sur BTC :
  - effet sur l'espérance de F3 : +0,027 ATR [−0,182 ; +0,247], non significatif ;
  - MDD à 0,25 %/ATR : −13,1 % avec le stop, contre −16,8 % sans ;
  - Calmar : 0,58 contre 0,41.
- **Les cinq années sont positives en ATR.**
  - 2022 est tout juste positive : +0,026, et −0,027 à 10 bps.
  - 2025 porte une grande part du PnL à 1x : +91 % sur l'année.
  - La moyenne winsorisée P1/P99 tombe de +0,190 à +0,139 : l'espérance dépend davantage des extrêmes que sur BTC (+0,379 après winsorisation).
- **Dimensionnement :** le PnL passe de +173 % à 1x à +39 % à 0,25 %/ATR, parce que l'exposition moyenne est de 30 %. Le Calmar est le même dans les deux cas (0,58-0,59). Le MDD passe de −42,3 % à −13,1 %.

### 4.2 CFD or (XAU/USD)
- **L'espérance nette est nulle** : −0,019 ATR [−0,362 ; +0,349] ; +1,1 bps [−4,9 ; +7,5].
- **Un brut positif, absorbé par les frais :**

  | | Brut par trade (ATR) | Frais (ATR) | Net (ATR) |
  |---|---|---|---|
  | BTC, 5 bps | +0,504 | 0,136 | +0,369 |
  | SOL, 5 bps | +0,250 | 0,061 | +0,190 |
  | XAU, 4 bps | +0,239 | 0,257 | −0,019 |

  - Le brut de l'or, +0,239 ATR, vaut celui de SOL.
  - Mais 4 bps représentent 0,26 ATR sur un actif dont l'ATR de 30 min médian est de 16 bps. Les frais font 79 % du brut à 1x.
- **Le schéma des sous-familles s'inverse par rapport à BTC :**
  - F2b : −0,304 ATR. Ses Short font −0,704 [−1,402 ; −0,001].
  - F3 : +0,313 ATR. Ses Long font +0,551 [−0,057 ; +1,209].
- **Le partage Long/Short est de la dérive, pas du timing** (I-M7).
  - Long +0,329, Short −0,431.
  - Timing −0,051 [−0,399 ; +0,306] ; dérive +0,380.
  - L'or a été en hausse séculaire sur 2020-2025.
- **Deux années positives sur six** (2020 et 2022). Les terciles de volatilité sont plats : −0,04, −0,05 et +0,03 ATR.

### 4.3 BTC (référence)
- **[CODE] Reproduction exacte de C02bis par la nouvelle chaîne :**
  - 1 080 trades identiques ;
  - 40 métriques comparées, écart relatif maximal 4,5·10⁻⁶ ;
  - ancre P6.5d reproduite.

## 5. [OBS] Mécanismes : ce qui se retrouve, ce qui change

- **Le profil queue droite se retrouve partout.**
  - Trade médian négatif : −0,42, −0,56 et −0,93 ATR (BTC, SOL, XAU).
  - Le décile supérieur apporte, par trade, +0,92, +0,77 et +0,85 ATR : plus que l'espérance totale.
- **Le stop de F3 sert le risque, pas l'alpha, sur les trois actifs.**
  - Part de F3 stoppés : 51 %, 53 % et 56 %. Un trade stoppé perd en moyenne −2,2, −2,1 et −2,3 ATR.
  - Effet apparié sur F3 : +0,03, +0,03 et −0,03 ATR, jamais significatif.
  - MDD à 0,25 %/ATR : −13,5 contre −20,5 % (BTC), −13,1 contre −16,8 % (SOL), −13,6 contre −15,3 % (XAU).
- **La haute volatilité est le régime faible sur BTC et SOL.**
  - Tercile agité : +0,06 et +0,09 ATR, contre +0,52 et +0,24 dans les deux autres.
  - XAU n'a de régime favorable nulle part.
- **La bascule de `nis_z_100` à P75 (C05) ne se reproduit pas telle quelle** (trades isolés, descriptif).
  - BTC : +0,53 ATR entre P70 et P75, puis −0,30 et −0,74 au-delà.
  - SOL : la bande sous P70 est positive, avec un IC au-dessus de zéro (+0,22 [+0,02 ; +0,46]). Mais la bande au-delà de P90 est aussi positive : +0,55 [−0,01 ; +1,19].
  - XAU : bandes nulles ou négatives partout.
- **La hiérarchie F2b > F3 de BTC se retrouve sur SOL, s'inverse sur XAU.**

## 6. [HYP] Lectures

- **La population transfère, la rente dépend du marché.**
  - Les filtres de population (géométrie en ATR, choc d'innovation) sélectionnent la même cinématique partout.
  - L'espérance brute de cette cinématique vaut environ la moitié de celle de BTC sur SOL et sur XAU.
- **Sur l'or en 30 min, le mécanisme est écrasé par le rapport frais / ATR.**
  - Même brut que SOL, mais des frais quatre fois plus lourds en ATR.
  - L'or est trop calme à cette échelle pour un coût fixe de 4 bps.
  - C'est un constat de physique du trade, pas un verdict sur le signal.
  - Il pose une question de vitesse : l'échelle de temps à laquelle l'ATR couvre les frais. Elle relève de H et de R0, ou de l'unité de temps des barres.
- **L'inversion F2b/F3 de l'or est cohérente avec une hausse séculaire forte.**
  - Le retracement intermédiaire vendeur (F2b Short) échoue.
  - La sortie de range acheteuse (F3 Long) porte.
  - Sur BTC 2020-2025, F2b Short restait positif.
- **SOL ressemble à BTC en plus bruité :** même structure, brut divisé par deux, F3 marginal, dépendance accrue aux extrêmes, échantillon plus court (4,5 ans, sans 2020).

## 7. [DECISION] Proposée

- **RE-1 reste inchangée.** D01 est descriptif, sans classement ni retrait d'actif. Aucune recalibration n'est tirée de ces mesures.
- **Trois décisions reviennent au porteur :**
  1. **WTI.** Au choix :
     - (a) mesurer sur HistData de 2020-01 à 2023-11, avec des roulements non ajustés, documentés ;
     - (b) fournir une source couvrant 2020-2025, par exemple OANDA WTICO_USD avec un jeton de compte de démonstration placé en variable d'environnement, ou l'export Dukascopy par AWS ;
     - (c) retirer le WTI de D01.
  2. **XAU.** Valider HistData (courtier non divulgué, fuseau corrigé) ou demander un recoupement sur une seconde source (OANDA XAU_USD, Dukascopy).
  3. **Git.** Commits locaux faits, aucun push (dépôt public).

## 8. Préparation de D02 (réflexion ; rien n'est défini ni testé)

- **Outil.**
  - VectorBT et Numba ne sont pas installés : leur installation demandera l'accord du porteur.
  - Contrôle bloquant proposé pour le portage : reproduire trade par trade les 1 080 trades BTC de `strategy.re1`, comme en D01.
  - Points délicats : le cooldown (entrées de la course sans stop, qui dépendent de H), le stop intrabarre avec gap à l'ouverture, et la sortie à open[t + 1 + H].
- **Paramètres H et R0.**
  - R0 change le signal lui-même, donc l'atlas, les familles et les quantiles. Il faudra trancher : garder les seuils numériques de BTC (R0 = 100) ou les réestimer à chaque R0.
  - H change aussi les entrées, via le cooldown.
  - L'optimisation conjointe de H et R0 est une exception explicite du porteur à la règle OFAT et à l'interdiction d'optimisation conjointe : à consigner comme décision.
- **Ce que D01 met en évidence pour D02, sans rien en conclure :**
  - Les frais pèsent très différemment selon l'actif, en ATR par trade : 0,14 (BTC), 0,06 (SOL), 0,26 (XAU). Toute fonction objectif doit être nette de frais, faute de quoi elle favoriserait les échelles rapides sur les actifs calmes.
  - Le dimensionnement à 0,25 %/ATR est plafonné à 1x sur l'or : les objectifs « à risque normalisé » n'y sont pas comparables tant que le levier est borné à 1.
  - L'espérance tient à la queue droite sur les trois actifs : un Calmar par fenêtre de walk-forward sera bruité. À 9-15 trades par mois, il faudra des fenêtres longues.
