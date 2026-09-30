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

---

# Annexes chiffrées (générées par `run_D01.py`)

## A. Contrôles bloquants et conventions

- Ancre P6.5d reproduite : 6 037 trades sans stop, 6 589 avec un stop de 2,5 %.
- Seuils gelés égaux aux statistiques de l'atlas BTC : médiane de leg_atr 2,8233, P75 de nis_z_100 1,2245 (précision machine).
- BTC par la chaîne D01 (`strategy.re1`) : 1 080 trades identiques à C02bis ; 40 métriques comparées à `resultats_C02bis.csv`, écart relatif maximal 4,5·10⁻⁶.
- Capital : 0,25 % par ATR14(t) (poids min(1 ; 25 bps / ATR14 en bps), levier ≤ 1x) et notionnel 1x. IC 95 % par bootstrap de grappes de mois d'entrée, 2 000 tirages.
- Annualisation : 6 ans (2020-01-01 → 2025-12-31) moins le temps écoulé entre le 1er janvier 2020 et la première barre de l'actif (convention de C02bis).

| Actif | Statut | Détail |
|---|---|---|
| BTC/USD (Bitstamp, référence) | mesuré | 1 080 trades sur 1 452 candidats ; 6,00 ans |
| SOL/USD (Coinbase) | mesuré | 769 trades sur 1 030 candidats ; 4,54 ans |
| CFD or XAU/USD (HistData) | mesuré | 651 trades sur 849 candidats ; 6,00 ans |
| CFD WTI (HistData) | bloqué | couverture 2020-01-01 → 2023-12-01 : HistData ne publie pas WTIUSD pour 2024 et 2025, contre la condition « au moins 2020-2025 » du porteur. Par ailleurs, l'audit montre un CFD de contrat du mois non ajusté, roulé autour de l'échéance : la série porte chaque mois un saut égal à l'écart de calendrier (règle non publiée par la source). Série auditée, aucun backtest avant décision du porteur. |

## B. Données : instruments et audit (étape 1, avant tout PnL)

| Champ | BTC/USD (Bitstamp, référence) | SOL/USD (Coinbase) | CFD or XAU/USD (HistData) | CFD WTI (HistData) |
|---|---|---|---|---|
| Instrument | BTC/USD, carnet spot de Bitstamp (TradingView : BITSTAMP:BTCUSD) | SOL/USD, carnet spot de Coinbase Exchange (TradingView : COINBASE:SOLUSD) | CFD sur l'or au comptant, XAU/USD (TradingView : XAUUSD, p. ex. OANDA:XAUUSD, FOREXCOM:XAUUSD) | CFD sur le pétrole brut WTI, WTI/USD (TradingView : USOIL, p. ex. TVC:USOIL, OANDA:WTICOUSD) |
| Nature | spot crypto, cotation en dollars américains | spot crypto, cotation en dollars américains | CFD / cotation OTC au comptant d'un courtier forex, compilée par HistData.com | CFD d'un courtier sur le contrat à terme NYMEX WTI (CL), compilé par HistData.com |
| Ticker | btcusd (Bitstamp) | SOL-USD (Coinbase Exchange) | XAUUSD (HistData.com, ASCII M1) | WTIUSD (HistData.com, ASCII M1) |
| Continuité | sans objet : instrument spot, série unique | sans objet : instrument spot, série unique | sans objet : cotation au comptant, sans échéance | non publiée par la source ; caractérisée par l'audit (écart au spot WTI Cushing quotidien de l'EIA, FRED DCOILWTICO) |
| Roulements | sans objet | sans objet | sans objet ; le coût de portage (swap) d'un CFD au comptant n'est pas dans les prix | non publiés par la source ; sauts de roulement recherchés par l'audit |
| Ajustements | aucun | aucun | aucun | aucun appliqué |
| Prix | — | — | bid (FAQ HistData : barres construites sur le bid des ticks) | bid (FAQ HistData : barres construites sur le bid des ticks) |
| Fuseau | UTC | UTC (début des bougies Coinbase) | étiquettes HistData converties en UTC : la FAQ annonce un EST fixe, mais l'horloge suit l'heure d'été européenne (serveur EET/EEST moins 7 h : UTC−5 en hiver européen, UTC−4 de fin mars à fin octobre) ; établi par l'audit D01 (pause quotidienne à 17:00-18:00 heure de New York toute l'année après conversion) | étiquettes HistData converties en UTC : la FAQ annonce un EST fixe, mais l'horloge suit l'heure d'été européenne (serveur EET/EEST moins 7 h : UTC−5 en hiver européen, UTC−4 de fin mars à fin octobre) ; établi par l'audit D01 (pause quotidienne à 17:00-18:00 heure de New York toute l'année après conversion) |
| Horaires | cotation continue 24/7 | cotation continue 24/7 ; les interruptions sont des maintenances ou incidents de la plateforme | marché OTC 24 h sur 24, 5 jours sur 7, pause quotidienne d'une heure calée sur New York ; vérifiés par l'audit | marché OTC 24 h sur 24, 5 jours sur 7, pause quotidienne d'une heure calée sur New York ; vérifiés par l'audit |
| Construction des barres 30 min | bougies 30 min natives de l'API OHLC publique de Bitstamp (step 1800) | agrégation exacte des bougies natives de 15 min (granularité 900 s) en barres de 30 min alignées sur :00 et :30 UTC : open de la première, plus haut, plus bas, close de la dernière, somme des volumes (en SOL) ; time = ouverture de la barre ; une barre sans transaction est un trou, jamais comblé | agrégation exacte des bougies d'une minute en barres de 30 min alignées sur :00 et :30 UTC ; time = ouverture de la barre ; volume absent de la source (écrit nul) ; une barre sans minute cotée est un trou, jamais comblé | agrégation exacte des bougies d'une minute en barres de 30 min alignées sur :00 et :30 UTC ; time = ouverture de la barre ; volume absent de la source (écrit nul) ; une barre sans minute cotée est un trou, jamais comblé |
| Couverture | 2020-01-01 → 2025-12-31 (lecture tronquée avant 2026) | 2021-01 → 2025-12 ; SOL-USD est coté sur Coinbase depuis le 2021-06-17 ; 2026 non téléchargé | années 2020 à 2025 ; 2026 non téléchargé | années 2020 à 2025 ; HistData ne publie WTIUSD que jusqu'au 2023-12-01 (aucun fichier pour 2024 et 2025 : jeton de téléchargement vide) ; couverture obtenue 2020-01 → 2023-12-01 |
| Limite | — | — | fournisseur amont (courtier) non divulgué par HistData | fournisseur amont (courtier) non divulgué par HistData |
| Barres (première → dernière) | 105 216 (2020-01-01 00:00 → 2025-12-31 23:30) | 79 577 (2021-06-17 16:00 → 2025-12-31 23:30) | 69 381 (2020-01-01 23:00 → 2025-12-31 21:30) | 44 836 (2020-01-01 23:00 → 2023-12-01 21:30) |

| Actif | Barres / cotation 24/7 | Trous : n ; barres manquantes | Trous ≤ 2 h ; ≤ 3 j ; > 3 j | Plus long trou (début) | Défauts d'intégrité | Barres plates ; volume nul | Semaines à pause seule 17:00-18:00 New York | Écart d'ouverture (bps) : P99,9 ; médiane après trou |
|---|---|---|---|---|---|---|---|---|
| BTC | 100,0 % | 0 ; 0 | 0 ; 0 ; 0 | — | aucune | 40 ; 39 | sans objet (24/7) | 24 ; — |
| SOL | 100,0 % | 4 ; 23 | 2 ; 2 ; 0 | 2025-10-25 15:00 (5,5 h) | aucune | 0 ; 0 | sans objet (24/7) | 24 ; 4,8 |
| XAU | 66,0 % | 2 101 ; 35 785 | 1711 ; 377 ; 13 | 2020-12-24 18:30 (76,0 h) | aucune | 0 ; source sans volume | 303 / 314 | 40 ; 3,3 |
| WTI | 65,3 % | 1 541 ; 23 802 | 1267 ; 265 ; 9 | 2020-12-24 18:30 (76,0 h) | aucune | 0 ; source sans volume | 195 / 205 | 142 ; 10,9 |

- XAU : 360 minutes répétées à l'identique supprimées à la construction (2020-10-26, 2021-11-01, 2022-10-31, 2023-10-30, 2024-10-28, 2025-10-27), une heure par an le lundi qui suit la fin de l'heure d'été européenne ; continuité des prix vérifiée.
- WTI : 239 minutes répétées à l'identique supprimées à la construction (2020-10-26, 2021-11-01, 2022-10-31, 2023-10-30), une heure par an le lundi qui suit la fin de l'heure d'été européenne ; continuité des prix vérifiée.

**CFD WTI contre le spot WTI Cushing de l'EIA** (close de la barre 14:00-14:30 heure de New York ; le spot suit le contrat échéant jusqu'à son expiration) :
- 923 jours communs ; écart CFD − spot médian −0,02 $ (par année : 2020 +0,00 ; 2021 −0,03 ; 2022 −0,12 ; 2023 −0,03) ; P5-P95 [−1,88 ; +0,19] $.
- Écart médian par tranche de jours du mois : 1-5 −0,02 ; 6-10 −0,02 ; 11-15 −0,03 ; 16-20 −0,02 ; 21-25 −0,03 ; 26-31 −0,02 $. Jours à plus de 0,25 $ d'écart : 211, par tranche du mois : 1-5 18 ; 6-10 18 ; 11-15 24 ; 16-20 54 ; 21-25 51 ; 26-31 46.
- Corrélation des variations quotidiennes, hors 20-21 avril 2020 : Pearson 0,978, Spearman 0,973.
- Échéance de juin 2021 (contrat de juillet, expiré le 22/06), CFD / spot : 06-16 72,03 / 72,03 ; 06-17 71,04 / 71,06 ; 06-18 71,64 / 71,64 ; 06-21 73,10 / 73,64 ; 06-22 72,82 / 73,15 ; 06-23 73,06 / 73,11 ; 06-24 73,29 / 73,31.
- Avril 2020, CFD / spot : 04-15 19,93 / 19,96 ; 04-16 19,86 / 19,82 ; 04-17 18,29 / 18,31 ; 04-20 20,27 / −36,98 ; 04-21 11,52 / 8,91 ; 04-22 13,77 / 13,64 ; 04-23 16,80 / 15,06 ; 04-24 17,00 / 15,99.

**WTI bloqué** : couverture 2020-01-01 → 2023-12-01 : HistData ne publie pas WTIUSD pour 2024 et 2025, contre la condition « au moins 2020-2025 » du porteur. Par ailleurs, l'audit montre un CFD de contrat du mois non ajusté, roulé autour de l'échéance : la série porte chaque mois un saut égal à l'écart de calendrier (règle non publiée par la source). Série auditée, aucun backtest avant décision du porteur.

## C. Signaux : distributions face aux seuils BTC gelés (descriptif)

| Actif | Signaux (par mois) | x1 déjà retourné | leg_atr P50 [P25 ; P75] | leg_atr < 2,8233 (seuil BTC) | retrace_ratio P50 [P25 ; P75] | nis_z_100 P50 ; P75 local | nis_z_100 > 1,2245 : tous ; dans R2 | ATR14 bps P50 [P10 ; P90] |
|---|---|---|---|---|---|---|---|---|
| BTC | 7 296 (101,3) | 51,8 % | 2,82 [2,17 ; 3,94] | 50,0 % | 0,62 [0,41 ; 0,84] | 0,19 ; P75 local 1,225 | 25,0 % ; 22,5 % | 49,7 [23,3 ; 99,4] |
| SOL | 5 385 (98,8) | 52,3 % | 2,85 [2,24 ; 3,92] | 49,1 % | 0,60 [0,38 ; 0,84] | 0,33 ; P75 local 1,368 | 27,3 % ; 29,5 % | 94,8 [56,6 ; 168,7] |
| XAU | 4 649 (64,6) | 49,4 % | 2,90 [2,20 ; 4,04] | 47,7 % | 0,59 [0,34 ; 0,82] | 0,25 ; P75 local 1,217 | 24,9 % ; 24,7 % | 17,2 [11,8 ; 28,5] |
| WTI | 3 028 (64,5) | 50,6 % | 2,93 [2,20 ; 4,00] | 46,4 % | 0,61 [0,35 ; 0,87] | 0,25 ; P75 local 1,311 | 26,3 % ; 23,0 % | 45,1 [28,0 ; 88,6] |

| Actif | Familles (seuil leg BTC) | R1 ; R2 avant nis ; R3 ; hors régimes | R2 écartés par nis | Univers RE-1 (F2b ; F3) |
|---|---|---|---|---|
| BTC | F1 1 869 ; F2a 1 303 ; F2b 1 592 ; F3 1 315 ; F4 476 ; F5 741 | 1 935 ; 1 874 ; 2 347 ; 1 140 | 422 | 1 452 (741 ; 711) |
| SOL | F1 1 530 ; F2a 923 ; F2b 1 129 ; F3 1 029 ; F4 289 ; F5 485 | 1 500 ; 1 461 ; 1 668 ; 756 | 431 | 1 030 (548 ; 482) |
| XAU | F1 1 398 ; F2a 760 ; F2b 932 ; F3 787 ; F4 274 ; F5 498 | 1 442 ; 1 128 ; 1 413 ; 666 | 279 | 849 (447 ; 402) |
| WTI | F1 870 ; F2a 472 ; F2b 567 ; F3 517 ; F4 281 ; F5 321 | 916 ; 684 ; 990 ; 438 | 157 | 527 (249 ; 278) |

## D. Tableau standard (8 métriques nettes)

| Actif, frais | PnL net : 0,25 %/ATR ; 1x ; bps cumulés (1x) | PF : 1x ; pondéré | WR | Espérance : bps [IC] ; ATR [IC] | MDD valorisé : 0,25 %/ATR ; 1x | Trades (par mois) ; stoppés | Durée médiane : barres ; calendaire | Part des frais : 1x ; pondérée |
|---|---|---|---|---|---|---|---|---|
| BTC 5 bps | +138 % ; +204 % ; +13320 | 1,20 ; 1,28 | 44,3 % | +12,3 [+0,2 ; +24,4] ; +0,369 [+0,098 ; +0,645] | −13,5 % ; −43,9 % | 1 080 (15,0) ; 24 % | 26 ; 13,0 h | 29 % ; 26 % |
| BTC 10 bps | +72 % ; +77 % ; +7920 | 1,11 ; 1,17 | 42,8 % | +7,3 [−4,8 ; +19,4] ; +0,233 [−0,041 ; +0,511] | −15,9 % ; −48,0 % | 1 080 (15,0) ; 24 % | 26 ; 13,0 h | 58 % ; 52 % |
| SOL 5 bps | +39 % ; +173 % ; +14747 | 1,17 ; 1,16 | 44,1 % | +19,2 [−3,6 ; +44,2] ; +0,190 [−0,079 ; +0,484] | −13,1 % ; −42,3 % | 769 (14,1) ; 24 % | 26 ; 13,0 h | 21 % ; 24 % |
| SOL 10 bps | +24 % ; +86 % ; +10902 | 1,12 ; 1,10 | 43,4 % | +14,2 [−8,6 ; +39,2] ; +0,129 [−0,140 ; +0,425] | −15,2 % ; −44,4 % | 769 (14,1) ; 24 % | 26 ; 13,0 h | 41 % ; 48 % |
| XAU 4 bps | +1 % ; +5 % ; +697 | 1,04 ; 1,01 | 42,5 % | +1,1 [−4,9 ; +7,5] ; −0,019 [−0,362 ; +0,349] | −13,6 % ; −13,3 % | 651 (9,0) ; 26 % | 26 ; 13,0 h | 79 % ; 92 % |

## E. Risque, sens, timing et sous-familles

| Actif, frais | Années | 0,25 %/ATR : CAGR ; Calmar | 1x : CAGR ; Calmar | Exposition moyenne ; trades plafonnés à 1x | Long / Short (ATR) | Timing ATR [IC] | Timing bps [IC] | F2b : n ; ATR | F3 : n ; ATR |
|---|---|---|---|---|---|---|---|---|---|
| BTC 5 bps | 6,00 | +15,6 % ; 1,16 | +20,3 % ; 0,46 | 60 % ; 16 % | +0,457 / +0,266 | +0,362 [+0,089 ; +0,638] | +12,3 [+0,2 ; +24,5] | 573 ; +0,459 | 507 ; +0,267 |
| BTC 10 bps | 6,00 | +9,5 % ; 0,60 | +10,0 % ; 0,21 | 60 % ; 16 % | +0,320 / +0,131 | +0,226 [−0,050 ; +0,507] | +7,3 [−4,8 ; +19,5] | 573 ; +0,326 | 507 ; +0,127 |
| SOL 5 bps | 4,54 | +7,6 % ; 0,58 | +24,8 % ; 0,59 | 30 % ; 0 % | +0,246 / +0,136 | +0,191 [−0,079 ; +0,490] | +19,2 [−3,6 ; +44,0] | 415 ; +0,287 | 354 ; +0,076 |
| SOL 10 bps | 4,54 | +4,9 % ; 0,32 | +14,7 % ; 0,33 | 30 % ; 0 % | +0,184 / +0,076 | +0,130 [−0,140 ; +0,431] | +14,2 [−8,6 ; +39,0] | 415 ; +0,228 | 354 ; +0,014 |
| XAU 4 bps | 6,00 | +0,1 % ; 0,01 | +0,9 % ; 0,07 | 98 % ; 89 % | +0,329 / −0,431 | −0,051 [−0,399 ; +0,306] | +0,5 [−5,2 ; +6,9] | 350 ; −0,304 | 301 ; +0,313 |

## F. Sens × sous-famille (espérance nette par trade, ATR [IC] ; contribution à l'espérance totale)

| Actif | Famille | Sens | n | Espérance ATR [IC] | Espérance bps | Contribution ATR |
|---|---|---|---|---|---|---|
| BTC 5 bps | F2b | Long | 290 | +0,617 [+0,140 ; +1,096] | +15,9 | +0,166 |
| BTC 5 bps | F2b | Short | 283 | +0,296 [−0,206 ; +0,796] | +7,6 | +0,078 |
| BTC 5 bps | F2b | tous | 573 | +0,459 [+0,106 ; +0,801] | +11,8 | +0,243 |
| BTC 5 bps | F3 | Long | 290 | +0,296 [−0,108 ; +0,740] | +9,3 | +0,080 |
| BTC 5 bps | F3 | Short | 217 | +0,227 [−0,210 ; +0,715] | +17,8 | +0,046 |
| BTC 5 bps | F3 | tous | 507 | +0,267 [−0,063 ; +0,620] | +12,9 | +0,125 |
| BTC 5 bps | tous | Long | 580 | +0,457 [+0,106 ; +0,807] | +12,6 | +0,245 |
| BTC 5 bps | tous | Short | 500 | +0,266 [−0,094 ; +0,636] | +12,0 | +0,123 |
| BTC 5 bps | tous | tous | 1 080 | +0,369 [+0,098 ; +0,645] | +12,3 | +0,369 |
| SOL 5 bps | F2b | Long | 203 | +0,379 [−0,242 ; +1,001] | +45,2 | +0,100 |
| SOL 5 bps | F2b | Short | 212 | +0,198 [−0,229 ; +0,610] | +33,2 | +0,055 |
| SOL 5 bps | F2b | tous | 415 | +0,287 [−0,075 ; +0,647] | +39,1 | +0,155 |
| SOL 5 bps | F3 | Long | 175 | +0,090 [−0,478 ; +0,734] | −5,3 | +0,021 |
| SOL 5 bps | F3 | Short | 179 | +0,061 [−0,394 ; +0,555] | −3,0 | +0,014 |
| SOL 5 bps | F3 | tous | 354 | +0,076 [−0,287 ; +0,472] | −4,1 | +0,035 |
| SOL 5 bps | tous | Long | 378 | +0,246 [−0,211 ; +0,768] | +21,8 | +0,121 |
| SOL 5 bps | tous | Short | 391 | +0,136 [−0,150 ; +0,431] | +16,6 | +0,069 |
| SOL 5 bps | tous | tous | 769 | +0,190 [−0,079 ; +0,484] | +19,2 | +0,190 |
| XAU 4 bps | F2b | Long | 174 | +0,101 [−0,597 ; +0,817] | +3,2 | +0,027 |
| XAU 4 bps | F2b | Short | 176 | −0,704 [−1,402 ; −0,001] | −9,6 | −0,190 |
| XAU 4 bps | F2b | tous | 350 | −0,304 [−0,829 ; +0,209] | −3,2 | −0,163 |
| XAU 4 bps | F3 | Long | 179 | +0,551 [−0,057 ; +1,209] | +10,2 | +0,152 |
| XAU 4 bps | F3 | Short | 122 | −0,038 [−0,711 ; +0,734] | +0,1 | −0,007 |
| XAU 4 bps | F3 | tous | 301 | +0,313 [−0,103 ; +0,797] | +6,1 | +0,144 |
| XAU 4 bps | tous | Long | 353 | +0,329 [−0,161 ; +0,813] | +6,7 | +0,179 |
| XAU 4 bps | tous | Short | 298 | −0,431 [−0,926 ; +0,078] | −5,6 | −0,197 |
| XAU 4 bps | tous | tous | 651 | −0,019 [−0,362 ; +0,349] | +1,1 | −0,019 |

## G. Stops de F3 (SL-B à l'extremum) : fréquence et contribution

| Actif | Stoppés / F3 | Espérance ATR : stoppés ; F3 non stoppés | Contribution des stoppés (ATR) | Effet apparié du stop sur F3 (ATR [IC]) | MDD 0,25 %/ATR : RE-1 contre sans stop | Calmar : RE-1 contre sans stop | MDD 1x : RE-1 contre sans stop |
|---|---|---|---|---|---|---|---|
| BTC 5 bps | 257 / 507 (51 %) | −2,18 ; +2,78 | −0,518 | +0,031 [−0,230 ; +0,305] | −13,5 % contre −20,5 % | 1,16 contre 0,69 | −43,9 % contre −47,6 % |
| SOL 5 bps | 186 / 354 (53 %) | −2,07 ; +2,45 | −0,500 | +0,027 [−0,182 ; +0,247] | −13,1 % contre −16,8 % | 0,58 contre 0,41 | −42,3 % contre −49,7 % |
| XAU 4 bps | 169 / 301 (56 %) | −2,30 ; +3,65 | −0,596 | −0,031 [−0,355 ; +0,317] | −13,6 % contre −15,3 % | 0,01 contre −0,02 | −13,3 % contre −17,3 % |

## H. Distribution des trades (espérance nette en ATR, frais de lecture principale)

| Actif | P10 ; P25 ; P50 ; P75 ; P90 | Moyenne ; winsorisée P1/P99 | Apport du décile supérieur par trade (part du total) | Durée calendaire (h) : médiane ; P90 ; part > 24 h |
|---|---|---|---|---|
| BTC 5 bps | −2,83 ; −2,10 ; −0,42 ; +2,06 ; +5,53 | +0,369 ; +0,379 | +0,919 (249 %) | 13,0 ; 13,0 ; 0 % |
| SOL 5 bps | −2,82 ; −2,02 ; −0,56 ; +1,97 ; +4,61 | +0,190 ; +0,139 | +0,765 (403 %) | 13,0 ; 13,0 ; 0 % |
| XAU 4 bps | −3,74 ; −2,45 ; −0,93 ; +2,36 ; +5,17 | −0,019 ; −0,023 | +0,847 (espérance totale ≤ 0) | 13,0 ; 20,0 ; 8 % |

## I. Régimes de volatilité (terciles de l'ATR14(t) en bps des trades de l'actif)

| Actif | Tercile | ATR14 (bps) | n | Espérance ATR [IC] | Espérance bps [IC] | WR | Stoppés |
|---|---|---|---|---|---|---|---|
| BTC 5 bps | T1 calme | 4,9 – 34,9 | 360 | +0,517 [−0,062 ; +1,170] | +11,5 [−1,8 ; +27,2] | 43,3 % | 26 % |
| BTC 5 bps | T2 | 34,9 – 55,3 | 360 | +0,525 [+0,129 ; +0,935] | +22,6 [+4,5 ; +41,3] | 45,3 % | 25 % |
| BTC 5 bps | T3 agité | 55,6 – 260,0 | 360 | +0,064 [−0,272 ; +0,392] | +2,9 [−23,7 ; +29,5] | 44,2 % | 20 % |
| SOL 5 bps | T1 calme | 22,7 – 73,5 | 256 | +0,232 [−0,325 ; +0,906] | +21,6 [−11,7 ; +62,8] | 42,6 % | 26 % |
| SOL 5 bps | T2 | 73,8 – 106,0 | 256 | +0,243 [−0,168 ; +0,652] | +22,5 [−12,9 ; +58,6] | 45,7 % | 25 % |
| SOL 5 bps | T3 agité | 106,1 – 453,8 | 257 | +0,094 [−0,193 ; +0,392] | +13,5 [−28,8 ; +57,2] | 44,0 % | 21 % |
| XAU 4 bps | T1 calme | 5,6 – 13,9 | 217 | −0,044 [−0,655 ; +0,614] | −0,6 [−8,0 ; +7,4] | 42,9 % | 30 % |
| XAU 4 bps | T2 | 13,9 – 17,9 | 217 | −0,047 [−0,663 ; +0,568] | −0,3 [−9,4 ; +9,4] | 43,8 % | 26 % |
| XAU 4 bps | T3 agité | 17,9 – 87,4 | 217 | +0,034 [−0,450 ; +0,479] | +4,1 [−9,7 ; +16,9] | 41,0 % | 22 % |

## J. nis_z_100 : bandes de l'univers R2 avant exclusion (trades isolés, bornes aux quantiles de l'atlas BTC)

Descriptif : chaque signal R2 joué seul avec l'enveloppe de RE-1, sans sélection séquentielle. Rien n'en est tiré pour l'exécution.

| Actif | ≤ P70 (BTC) | P70–P75 (BTC) | P75–P80 (BTC) | P80–P85 (BTC) | P85–P90 (BTC) | > P90 (BTC) |
|---|---|---|---|---|---|---|
| BTC 5 bps | 1 358 : +0,17 [−0,05 ; +0,39] | 94 : +0,53 [−0,27 ; +1,34] | 87 : −0,30 [−0,79 ; +0,20] | 82 : −0,74 [−1,51 ; +0,12] | 84 : +0,22 [−0,66 ; +1,21] | 169 : −0,40 [−0,93 ; +0,17] |
| SOL 5 bps | 939 : +0,22 [+0,02 ; +0,46] | 91 : +0,13 [−0,50 ; +0,89] | 90 : −0,23 [−0,83 ; +0,38] | 105 : +0,06 [−0,66 ; +0,95] | 90 : −0,15 [−0,73 ; +0,42] | 146 : +0,55 [−0,01 ; +1,19] |
| XAU 4 bps | 777 : +0,05 [−0,25 ; +0,36] | 72 : −0,43 [−1,28 ; +0,46] | 63 : −0,20 [−1,19 ; +0,88] | 62 : +0,11 [−0,67 ; +0,87] | 53 : −0,05 [−0,90 ; +0,86] | 101 : −0,49 [−1,10 ; +0,15] |

## K. Stabilité annuelle (année d'entrée)

| Actif | Année | Trades | Espérance ATR | Espérance bps | PnL 0,25 %/ATR | PnL 1x | Long / Short ATR |
|---|---|---|---|---|---|---|---|
| BTC 5 bps | 2020 | 189 | +0,514 | +18,4 | +25,3 % | +35,5 % | +0,64 / +0,35 |
| BTC 5 bps | 2021 | 192 | +0,024 | +2,1 | +0,3 % | −4,0 % | +0,24 / −0,21 |
| BTC 5 bps | 2022 | 173 | +0,305 | +9,5 | +11,5 % | +12,9 % | −0,18 / +0,87 |
| BTC 5 bps | 2023 | 188 | +0,504 | +19,1 | +25,4 % | +41,1 % | +1,01 / −0,03 |
| BTC 5 bps | 2024 | 171 | +0,334 | +12,7 | +14,8 % | +21,1 % | +0,40 / +0,25 |
| BTC 5 bps | 2025 | 167 | +0,550 | +12,2 | +18,1 % | +20,9 % | +0,60 / +0,49 |
| BTC 10 bps | 2020 | 189 | +0,407 | +13,4 | +19,2 % | +23,3 % | +0,53 / +0,26 |
| BTC 10 bps | 2021 | 192 | −0,046 | −2,9 | −3,0 % | −12,8 % | +0,17 / −0,28 |
| BTC 10 bps | 2022 | 173 | +0,187 | +4,5 | +6,4 % | +3,5 % | −0,30 / +0,75 |
| BTC 10 bps | 2023 | 188 | +0,297 | +14,1 | +16,4 % | +28,5 % | +0,80 / −0,24 |
| BTC 10 bps | 2024 | 171 | +0,195 | +7,7 | +8,5 % | +11,2 % | +0,26 / +0,11 |
| BTC 10 bps | 2025 | 167 | +0,371 | +7,2 | +10,9 % | +11,2 % | +0,42 / +0,31 |
| SOL 5 bps | 2021 | 87 | +0,200 | −5,0 | +4,1 % | −10,9 % | +0,47 / −0,09 |
| SOL 5 bps | 2022 | 186 | +0,026 | +24,8 | +0,5 % | +33,7 % | −0,44 / +0,41 |
| SOL 5 bps | 2023 | 171 | +0,198 | +8,7 | +8,0 % | +6,4 % | +0,44 / −0,07 |
| SOL 5 bps | 2024 | 156 | +0,110 | +11,4 | +3,8 % | +13,0 % | +0,46 / −0,15 |
| SOL 5 bps | 2025 | 169 | +0,429 | +43,2 | +18,9 % | +90,8 % | +0,41 / +0,45 |
| SOL 10 bps | 2021 | 87 | +0,159 | −10,0 | +3,2 % | −14,7 % | +0,43 / −0,13 |
| SOL 10 bps | 2022 | 186 | −0,027 | +19,8 | −2,0 % | +21,8 % | −0,49 / +0,36 |
| SOL 10 bps | 2023 | 171 | +0,132 | +3,7 | +4,9 % | −2,4 % | +0,37 / −0,14 |
| SOL 10 bps | 2024 | 156 | +0,046 | +6,4 | +1,2 % | +4,6 % | +0,39 / −0,21 |
| SOL 10 bps | 2025 | 169 | +0,360 | +38,2 | +15,5 % | +75,4 % | +0,34 / +0,38 |
| XAU 4 bps | 2020 | 123 | +0,056 | +8,2 | +5,9 % | +10,1 % | +0,19 / −0,11 |
| XAU 4 bps | 2021 | 107 | −0,155 | −3,0 | −3,2 % | −3,4 % | +0,65 / −1,10 |
| XAU 4 bps | 2022 | 119 | +0,476 | +4,3 | +6,5 % | +4,9 % | +0,38 / +0,57 |
| XAU 4 bps | 2023 | 83 | −0,210 | −2,6 | −2,3 % | −2,3 % | −0,28 / −0,14 |
| XAU 4 bps | 2024 | 109 | −0,129 | −1,6 | −2,0 % | −1,9 % | +0,99 / −1,40 |
| XAU 4 bps | 2025 | 110 | −0,251 | −1,0 | −3,7 % | −1,5 % | −0,04 / −0,59 |

Figures : `figures/capital_D01.png`, `figures/nis_D01.png`, `figures/annees_D01.png`.
