# EXP-D01 — Portabilité de RE-1 figée, sans réglage : SOL/USD, CFD or, ETF SPY et XLE (WTI retiré)

- **Date :** 2026-09-30 (D01, puis D01 bis le même jour).
- **Étape :** D, première expérience. **Descriptive** par décision du porteur : aucun critère de réussite ou d'échec, aucun classement des actifs, aucune modification de RE-1.
- **Actifs et périodes :**
  - BTC/USD Bitstamp, 2020-2025 : référence ;
  - SOL/USD Coinbase, du 2021-06-17 au 2025-12-31 ;
  - CFD or XAU/USD (HistData), 2020-2025 ;
  - **D01 bis :** ETF SPY et XLE (Alpaca, séance régulière), 2020-2025 ;
  - CFD WTI (HistData) : audité, bloqué, puis **retiré par le porteur** et remplacé par XLE (son audit reste ci-dessous pour mémoire) ;
  - 2026, ETH et XRP ne sont ni téléchargés ni lus.
- **Frais :** SOL 5 et 10 bps (lecture principale à 5 bps) ; XAU, SPY et XLE 4 bps ; BTC 5 et 10 bps. Ce sont des hypothèses de frais d'exécution, pas une mesure du glissement. Aucun stress de glissement n'est appliqué.
- **Stratégie :** RE-1 telle quelle.
  - Moteur v2.1 par défaut : R0 = 100, q1 = q2 = 0,01, γ = 0,5 ; oscillateur N2 = 5, R2 = 3.
  - Univers R2 = (F2b | F3) & x1 déjà retourné, hors `nis_z_100` > seuil.
  - F2b sans stop ; F3 SL-B à l'extremum (δ = 0, plancher 0,25 ATR).
  - H = 26 barres de 30 min de la série ; entrée à open[t + 1] ; une position à la fois ; cooldown.
- **Transfert des seuils, option (a) :** les valeurs numériques de BTC sont gelées à la précision machine : médiane de `leg_atr` = 2,8233, P75 de `nis_z_100` = 1,2245. Les seuils 0,50 et 0,85 de `retrace_ratio` sont fixes. Les quantiles locaux sont publiés à titre descriptif et n'entrent jamais dans l'exécution.
- **Code :**
  - `src/marketdata/` : acquisition et audit (Coinbase, HistData, Alpaca, FRED), avec tests ;
  - `src/strategy/re1.py` : RE-1 générique, avec tests ;
  - `experiments/D01/donnees_D01.py` : acquisition ;
  - `experiments/D01/run_D01.py` : `--audit`, puis le run.

## 0. Cadrage

- **QUESTION :** que devient RE-1, transférée telle quelle, sur des marchés de structures différentes ?
  - SOL/USD : crypto 24/7, environ deux fois plus volatile que BTC.
  - L'or au comptant : CFD, cotation 23 h sur 24, 5 jours sur 7.
  - SPY et XLE : ETF actions, séance de 09:30 à 16:00 heure de New York, gaps d'ouverture.
- **PERTINENCE POUR LE FILTRE AKF :**
  - Le déclencheur est invariant d'échelle : gain figé par le reset de P, R adaptatif selon le rapport rv/av, oscillateur normalisé par max|x1|.
  - Les descripteurs de RE-1 sont en ATR14(t) et en z-score. Le transfert teste donc si la cinématique retenue sur BTC existe ailleurs à paramètres identiques : sortie de range, x1 déjà retourné, sans choc d'innovation.
  - Les séances (pause du CFD, nuit et week-end des ETF) ajoutent des écarts d'ouverture que BTC n'a pas. Le filtre les voit comme un mouvement d'une barre, et H = 26 compte des barres, pas des heures.
- **CE QUE LE PROTOCOLE MESURE RÉELLEMENT :** pour chaque actif, sur sa période disponible jusqu'au 2025-12-31 :
  - les 8 métriques nettes aux frais de l'actif ;
  - l'espérance et le timing en ATR et en bps, avec IC par grappes mensuelles ;
  - le capital à 0,25 % par ATR14(t) et à 1x ;
  - Long/Short, F2b/F3, stops de F3, années, terciles de volatilité ;
  - `nis_z_100` face au seuil BTC, et ses bandes (trades isolés) ;
  - pour les séries en séances, les gaps d'ouverture (données, signaux, trades) ;
  - l'audit des données.
- **CE QU'IL NE PERMET PAS DE CONCLURE :**
  - pas de validation sur le hold-out ;
  - pas de comparaison statistique ni de classement des actifs ;
  - rien sur l'optimalité des seuils transférés, ni sur D02 ;
  - les coûts réels ne sont pas modélisés (spread, financement et swaps des CFD) ;
  - les sources (Coinbase, HistData, Alpaca) et la période de SOL (depuis juin 2021) diffèrent de celles de BTC ;
  - sur les ETF, avec environ 2 trades par mois, les IC font ±0,6 ATR : un petit avantage ne se distingue pas de zéro.

**Règle de lecture (fixée avant le calcul, en tête du script) :**
- **Aucun seuil de réussite sur une métrique de performance.**
- **Seul motif de blocage : la validité technique ou la qualité des données.** Cela couvre :
  - l'intégrité ;
  - la couverture 2020-2025, contrôlée pour les CFD et les ETF ;
  - un proxy non validé.
- **L'actif bloqué est documenté, jamais remplacé en silence.**
- **Définitions posées avant le calcul :**
  - régimes de volatilité : terciles de l'ATR14(t), en bps, des trades de l'actif ;
  - bandes de `nis_z_100` : bornes aux quantiles P70-P90 de l'atlas BTC (valeurs gelées) ; chaque signal R2 est joué seul ;
  - effet du stop de F3 : différence appariée RE-1 − RE-1 sans stop, sur les mêmes entrées ;
  - gaps d'ouverture (D01 bis) :
    - barre d'ouverture = barre précédée d'un intervalle de plus de 30 min ;
    - écart en bps et en ATR de la barre précédente ;
    - trade : rendement brut (log, ATR14(t)) décomposé en écarts d'ouverture traversés et reste réalisé en séance ;
    - stops exécutés au-delà de leur niveau à l'ouverture ;
    - espérance selon la barre du signal.

## 1. Consignes du porteur, écarts vérifiés

**[DECISION] Consignes du 2026-09-30 :**
- Actifs initiaux : SOL/USD, CFD WTI, CFD or. SOXS est écarté ; BTC 2013-2019 est laissé de côté.
- Transfert : option (a). D01 est descriptif. D02 est préparé mais non lancé.

**Changements de consigne en cours de session :**
- **SOL/USD, et non SOL/USDT.** La série Binance SOL/USDT, déjà téléchargée, a été supprimée sans avoir été backtestée.
- **WTI.** La série HistData s'arrêtait au 2023-12-01, donc WTI bloqué.
  - Une piste FXCM a été instruite. Elle exigeait une connexion au compte du porteur (téléchargeur Windows ou ForexConnect) et n'a pas abouti.
  - Le porteur a ensuite retiré le WTI et l'a remplacé par l'ETF **XLE**, proxy de l'énergie sans roulement de contrats.
  - Il a ajouté l'ETF **SPY** (marché actions, gaps d'ouverture).
- **Téléchargement Alpaca.** Le porteur l'a lancé lui-même, ses clés placées en variables d'environnement. Aucune clé n'a été manipulée ni écrite par l'assistant.

**[OBS] Écarts dans les prompts, vérifiés :**
- **Référence BTC à 10 bps :** elle vaut **+7,33 bps par trade [−4,83 ; +19,41]** (`resultats_C02bis.csv`, reproduit ici trade par trade), et non « +7,5 [−4,7 ; +19,5] ». L'estimation est positive et son IC traverse zéro. En ATR : +0,233 [−0,041 ; +0,511].
- **C05 n'a pas conclu que tous les tests de stabilité étaient réussis.** Son verdict : plateaux pour la frontière F2b/F3 et pour la marge du stop, mais **falaise côté permissif pour l'exclusion `nis_z_100`**. C'est ce seuil qui est transféré tel quel.
- **« L'alpha de RE-1 est universel » n'est pas établi.** L'espérance brute par trade, en ATR, vaut :
  - SOL : +0,25, avec un IC net qui contient zéro ;
  - or : +0,24 [−0,11 ; +0,61] ;
  - SPY : 0,00 ;
  - XLE : +0,10.

  Ce qui est établi, c'est que la population de signaux se transpose.
- **Motif du blocage du WTI :** d'abord la couverture (fin au 2023-12-01). Les roulements non ajustés ont été documentés en plus.

## 2. [CODE] Données : sources, construction, audit (avant tout PnL)

### 2.1 Sources retenues et écartées

| Actif | Série retenue | Pourquoi | Écartées |
|---|---|---|---|
| SOL | Coinbase SOL-USD (TradingView : COINBASE:SOLUSD), spot en USD. Bougies natives de 15 min agrégées exactement en 30 min (UTC, :00/:30) | Marché USD le plus liquide, historique public sans clé | Binance SOL/USDT (écarté par le porteur) ; Binance.US SOLUSD (trou de mi-2023 à février 2025) ; Bitstamp SOL/USD (coté seulement depuis 2022-2023) |
| XAU | HistData XAUUSD : CFD au comptant, bougies d'une minute (bid) | Seule source gratuite et sans compte couvrant 2020-2025 en intraday | Dukascopy (accès automatisés refusés, « Bot blocked » ; blocage non contourné) ; OANDA (compte requis) |
| SPY, XLE | Alpaca, flux SIP consolidé, barres natives de 30 min, séance régulière. Série ajustée des fractionnements et dividendes (mesurée), série brute (audit) | Seule source intraday 2020-2025 disponible avec le compte du porteur | Yahoo Finance (30 min limité aux 60 derniers jours) |
| WTI (retiré) | HistData WTIUSD : CFD sur le contrat NYMEX CL | — | FXCM (connexion au compte du porteur requise) |
| Réf. | FRED DCOILWTICO : spot WTI Cushing de l'EIA, quotidien | Contrôle du CFD WTI et du proxy XLE | — |

Chaque série a son `.meta.json` versionné (instrument, nature, ticker, continuité, roulements, ajustements, fuseau, horaires, construction, couverture, empreintes). Les données brutes restent hors dépôt.

### 2.2 Audit commun

**[OBS] Aucun défaut d'intégrité** sur les séries mesurées : pas de doublon, pas de désordre, pas de prix non positif, pas d'OHLC incohérent. La couverture 2020-2025 est vérifiée pour XAU, SPY et XLE.

- **SOL :**
  - 79 577 barres ;
  - 4 trous (23 barres manquantes), le plus long de 5,5 h (2025-10-25).
  - La couverture commence le 2021-06-17, date de cotation de SOL-USD sur Coinbase. Aucune place en USD liquide ne couvre 2020 : la consigne « au moins 2020-2025 » est structurellement impossible pour SOL/USD.
- **XAU :**
  - 69 381 barres, soit 66 % d'une cotation 24/7 ;
  - pause quotidienne, week-ends et fêtes ;
  - 404 barres (0,6 %) ont moins de 30 minutes cotées ;
  - la source n'a pas de volume.

### 2.3 Deux défauts de la source HistData, corrigés et documentés

1. **Fuseau.**
   - **Ce que dit la source :** la FAQ annonce un EST fixe.
   - **Ce que montre l'audit :** l'horloge suit l'heure d'été européenne ; c'est un serveur EET/EEST moins 7 h.
   - **Correction :** étiquette + 7 h, localisée en Europe/Athens, puis UTC.
   - **Contrôle :** la pause quotidienne tombe à 17:00-18:00 heure de New York dans **303 semaines sur 314** (XAU), et à cette heure-là toutes les semaines. Seuls les horodatages bougent.
2. **Doublons.** Une heure par an est répétée à l'identique, le lundi qui suit la fin de l'heure d'été européenne. La continuité des prix est vérifiée ; ces doublons exacts sont supprimés.
3. **Limite non corrigible :** HistData ne divulgue pas le courtier qui fournit les cotations.

### 2.4 ETF SPY et XLE (D01 bis)

- **[OBS] Séances.**
  - 1 508 séances et 19 532 barres par ETF.
  - Première barre à 09:30, dernière à 15:30 heure de New York, 13 barres par séance.
  - 12 séances courtes : les clôtures anticipées du NYSE à 13:00.
- **[CODE] Correction des clôtures anticipées.** Le premier filtre (09:30-16:00) gardait les barres de post-marché de ces demi-séances.
  - Le calendrier NYSE des 12 clôtures à 13:00 a été vérifié sur les volumes. Le volume s'effondre après 13:00 sur les 12 dates pour XLE, et sur 11 dates pour SPY au seuil de 0,1.
  - La douzième date pour SPY (2023-11-24) a été vérifiée barre par barre.
  - Les 72 barres (SPY) et 65 barres (XLE) de post-marché sont écartées, sans nouveau téléchargement.
  - L'enchère de clôture, horodatée à 16:00:00, tombe dans la barre de 16:00, écartée. Le close de la barre de 15:30 est donc la dernière transaction de la séance continue.
- **[OBS] Dividendes.** 24 détachements par ETF (4 par an), repérés par l'écart entre séries brute et ajustée :
  - SPY −36 bps en moyenne ;
  - XLE −106 bps ;
  - bruit d'arrondi des prix ajustés : 0,3 bps (SPY) et 5 bps (XLE) au P99.
- **[OBS] Fractionnement de XLE, 2 pour 1, le 2025-12-05.** L'ouverture brute recule de −6 951 bps (log de 0,5), la série ajustée de −20 bps. Sans ajustement, RE-1 aurait vu un krach de 50 %.
- **[OBS] Correspondance du proxy XLE** (variations quotidiennes, hors 17-22 avril 2020) :
  - avec le spot WTI : Pearson 0,46, Spearman 0,56, bêta 0,30 ;
  - avec SPY : Pearson 0,60, bêta 1,00.
  - **XLE est autant un titre du marché actions qu'un proxy du pétrole.**

### 2.5 WTI : retiré (audit pour mémoire)

- **Couverture.** HistData ne publie WTIUSD que jusqu'au 2023-12-01.
- **Nature du CFD.** Il colle au spot EIA (écart médian −0,02 $, corrélation 0,978 hors avril 2020), avec des écarts concentrés du 16 au 31 du mois.
  - Le 20 avril 2020 : CFD 20,27 $ contre spot −36,98 $.
  - [HYP] C'est un contrat du mois non ajusté, roulé 1 à 2 jours avant l'échéance.
- **Décision du porteur :** WTI retiré, remplacé par XLE. Aucun backtest.

## 3. [OBS] Signaux : la géométrie se transpose, mais moins bien sur les ETF

| | BTC | SOL | XAU | SPY | XLE |
|---|---|---|---|---|---|
| Signaux par mois | 101 | 99 | 65 | 17,6 | 17,6 |
| x1 déjà retourné | 51,8 % | 52,3 % | 49,4 % | 51,5 % | 46,3 % |
| `leg_atr` P50 ; part sous le seuil BTC 2,8233 | 2,82 ; 50,0 % | 2,85 ; 49,1 % | 2,90 ; 47,7 % | 3,09 ; 41,6 % | 3,24 ; 37,6 % |
| `retrace_ratio` P50 | 0,62 | 0,60 | 0,59 | 0,59 | 0,58 |
| `nis_z_100` > 1,2245 : tous ; dans R2 | 25,0 % ; 22,5 % | 27,3 % ; 29,5 % | 24,9 % ; 24,7 % | 28,0 % ; 28,5 % | 22,4 % ; 30,0 % |
| ATR14 médian des signaux (bps) | 49,7 | 94,8 | 17,2 | 28,7 | 52,1 |
| Univers RE-1 (F2b ; F3) → trades | 1 452 (741 ; 711) → 1 080 | 1 030 (548 ; 482) → 769 | 849 (447 ; 402) → 651 | 191 (93 ; 98) → 155 | 159 (61 ; 98) → 136 |

- **Crypto et or : des distributions quasi identiques,** alors que l'ATR en bps varie d'un facteur 5,5. Les seuils BTC y retiennent les mêmes fractions de signaux.
- **ETF : les jambes sont plus longues en ATR.**
  - `leg_atr` P50 : 3,09 et 3,24.
  - Le seuil BTC ne retient que 42 % et 38 % des signaux (contre 50 % sur BTC), et F2b se raréfie sur XLE.
  - [HYP] Les écarts de nuit, inclus dans les segments, allongent les jambes mesurées en ATR.
- **Les ETF ne donnent que 13 barres par séance :** environ 2 trades par mois.

## 4. [OBS] Résultats nets (H26 ; lecture principale en gras)

| Métrique | **BTC 5 bps** | BTC 10 bps | **SOL 5 bps** | SOL 10 bps | **XAU 4 bps** | **SPY 4 bps** | **XLE 4 bps** |
|---|---|---|---|---|---|---|---|
| Période ; années | 2020-2025 ; 6,00 | idem | 2021-06-17 → 2025 ; 4,54 | idem | 2020-2025 ; 6,00 | 2020-2025 ; 6,00 | 2020-2025 ; 6,00 |
| PnL composé : 0,25 %/ATR ; **1x** ; bps cumulés (1x) | +138 % ; **+204 %** ; +13 320 | +72 % ; **+77 %** ; +7 920 | +39 % ; **+173 %** ; +14 747 | +24 % ; **+86 %** ; +10 902 | +0,6 % ; **+5,4 %** ; +697 | −4,2 % ; **−7,9 %** ; −696 | +0,1 % ; **+7,2 %** ; +1 013 |
| Profit Factor : 1x ; pondéré | 1,20 ; 1,28 | 1,11 ; 1,17 | 1,17 ; 1,16 | 1,12 ; 1,10 | 1,04 ; 1,01 | 0,91 ; 0,93 | 1,09 ; 1,01 |
| Win Rate | 44,3 % | 42,8 % | 44,1 % | 43,4 % | 42,5 % | 45,2 % | 44,9 % |
| Espérance ATR [IC 95 %] | +0,369 [+0,098 ; +0,645] | +0,233 [−0,041 ; +0,511] | +0,190 [−0,079 ; +0,484] | +0,129 [−0,140 ; +0,425] | −0,019 [−0,362 ; +0,349] | −0,158 [−0,736 ; +0,434] | +0,020 [−0,588 ; +0,674] |
| Espérance bps à 1x [IC 95 %] | +12,3 [+0,2 ; +24,4] | +7,3 [−4,8 ; +19,4] | +19,2 [−3,6 ; +44,2] | +14,2 [−8,6 ; +39,2] | +1,1 [−4,9 ; +7,5] | −4,5 [−23,7 ; +14,9] | +7,4 [−28,7 ; +43,9] |
| MDD valorisé : 0,25 %/ATR ; **1x** | −13,5 % ; **−43,9 %** | −15,9 % ; **−48,0 %** | −13,1 % ; **−42,3 %** | −15,2 % ; **−44,4 %** | −13,6 % ; **−13,3 %** | −10,9 % ; **−19,2 %** | −19,5 % ; **−36,4 %** |
| Calmar : 0,25 %/ATR ; 1x | 1,16 ; 0,46 | 0,60 ; 0,21 | 0,58 ; 0,59 | 0,32 ; 0,33 | 0,01 ; 0,07 | −0,07 ; −0,07 | 0,00 ; 0,03 |
| Trades (par mois) ; stoppés | 1 080 (15,0) ; 24 % | idem | 769 (14,1) ; 24 % | idem | 651 (9,0) ; 26 % | 155 (2,2) ; 30 % | 136 (1,9) ; 35 % |
| Durée médiane : barres ; calendaire | 26 ; 13 h | idem | 26 ; 13 h | idem | 26 ; 13 h (P90 20 h) | 26 ; 48 h (P90 96 h) | 26 ; 48 h (P90 96 h) |
| Part des frais : 1x ; pondérée | 29 % ; 26 % | 58 % ; 52 % | 21 % ; 24 % | 41 % ; 48 % | 79 % ; 92 % | brut ≤ 0 ; 386 % | 35 % ; 80 % |
| Brut ; frais (ATR par trade) | +0,50 ; 0,14 | — | +0,25 ; 0,06 | — | +0,24 ; 0,26 | 0,00 ; 0,16 | +0,10 ; 0,08 |
| Timing ATR [IC] | +0,362 [+0,089 ; +0,638] | +0,226 [−0,050 ; +0,507] | +0,191 [−0,079 ; +0,490] | +0,130 [−0,140 ; +0,431] | −0,051 [−0,399 ; +0,306] | −0,247 [−0,825 ; +0,360] | −0,071 [−0,739 ; +0,650] |
| F2b ; F3 (ATR par trade) | +0,459 ; +0,267 | +0,326 ; +0,127 | +0,287 ; +0,076 | +0,228 ; +0,014 | −0,304 ; +0,313 | +0,059 ; −0,367 | −0,186 ; +0,139 |
| Années à espérance ATR > 0 | 6/6 | 5/6 | 5/5 (2021 partielle) | 4/5 | 2/6 | 2/6 | 3/6 |

**Exposition moyenne à 0,25 %/ATR :** BTC 60 %, SOL 30 %, XAU 98 %, SPY 82 %, XLE 50 %.
- Plafonnement à 1x : 89 % des trades sur XAU, 47 % sur SPY, où l'ATR est souvent inférieur à 25 bps.

### 4.1 SOL/USD
- **Estimations positives, IC qui contiennent zéro** : +0,190 ATR et +19,2 bps à 5 bps ; +0,129 ATR à 10 bps.
- **L'espérance vient de F2b** (+0,287 ATR). F3 est proche de zéro (+0,076). Long et Short sont positifs (+0,246 et +0,136).
- **Le stop de F3 garde son rôle d'outil de risque** : effet +0,027 ATR, non significatif ; MDD −13,1 contre −16,8 % sans stop.
- **Années et dépendance aux extrêmes.** Les cinq années sont positives en ATR, mais 2025 porte +91 % du PnL à 1x. La moyenne winsorisée P1/P99 tombe à +0,139.

### 4.2 CFD or (XAU/USD)
- **L'espérance nette est nulle** : −0,019 ATR [−0,362 ; +0,349].
- **Le brut positif est absorbé par les frais.** Brut +0,239 ATR, mais 4 bps = 0,26 ATR sur un actif dont l'ATR de 30 min médian est de 16 bps. Les frais font 79 % du brut à 1x.
- **F2b et F3 sont inversés par rapport à BTC** : F2b −0,304 (Short −0,704 [−1,402 ; −0,001]), F3 +0,313 (Long +0,551).
- **Le partage Long/Short est de la dérive, pas du timing** : Long +0,33, Short −0,43, timing −0,05, dérive +0,38.
- **Deux années positives sur six.**

### 4.3 ETF SPY
- **Aucun avantage mesurable.** Le brut vaut +0,004 ATR par trade, donc l'espérance nette égale les frais : −0,158 ATR [−0,736 ; +0,434], −4,5 bps [−23,7 ; +14,9].
- **Sous-familles :** F3 négatif (−0,367 ; F3 Short −1,04 [−2,26 ; +0,22]) ; F2b proche de zéro (+0,059).
- **Sens :** Long +0,11, Short −0,60. Timing −0,25 [−0,82 ; +0,36], dérive +0,35 : la hausse du marché de 2020-2025 pénalise les ventes.
- **Deux années positives sur six** (2020, 2023).
- **Le stop de F3 aide ici l'espérance,** sans que ce soit significatif : +0,46 ATR [−0,25 ; +1,11]. MDD −10,9 contre −16,0 % sans stop.

### 4.4 ETF XLE
- **Espérance nulle** : +0,020 ATR [−0,588 ; +0,674], +7,4 bps [−28,7 ; +43,9]. Brut +0,10 ATR, frais 0,08 ATR.
- **Sous-familles inversées par rapport à BTC** (comme l'or) : F2b −0,186 (Short −1,23), F3 +0,139.
- **Sens :** Long +0,20, Short −0,34.
- **Trois années positives sur six**, en alternance : 2020 +1,36, 2021 −1,20, 2022 −1,07, 2024 +1,04 ATR.
- **Drawdown :** −19,5 % à 0,25 %/ATR et −36,4 % à 1x.
- **Le stop de F3 aide ici l'espérance :** +0,40 ATR [−0,23 ; +1,01].

### 4.5 BTC (référence)
- **[CODE] Reproduction exacte de C02bis par la nouvelle chaîne :**
  - 1 080 trades identiques ;
  - 40 métriques comparées, écart relatif maximal 4,5·10⁻⁶ ;
  - ancre P6.5d reproduite.

## 5. [OBS] Gaps d'ouverture : comment RE-1 les absorbe (SPY, XLE ; XAU en contraste)

**Les données.** Sur les ETF, les gaps sont gros à l'échelle de la barre.

| | XAU | SPY | XLE |
|---|---|---|---|
| \|Écart d'ouverture\| P50 ; P90 (bps) | 3,3 ; 18,7 | 33,1 ; 110,8 | 57,1 ; 195,4 |
| \|Écart d'ouverture\| P50 ; P90 (ATR) ; part > 1 ATR | 0,18 ; 0,98 ; 10 % | 1,18 ; 3,14 ; 57 % | 1,14 ; 3,07 ; 56 % |
| Vrai range en ATR (P50) : barre d'ouverture ; autres | 0,78 ; 0,86 | 2,01 ; 0,79 | 2,85 ; 0,75 |
| Part du vrai range total portée par les barres d'ouverture | 3 % (3 % des barres) | 17 % (7,7 % des barres) | 22 % (7,7 % des barres) |

- Le gap médian vaut plus d'un ATR de 30 min. La barre d'ouverture porte 2 à 3 fois l'amplitude d'une barre de séance.

**Les signaux : le filtre `nis_z_100` joue le rôle de filtre de gap.**
- 10,8 % (SPY) et 11,8 % (XLE) des signaux tombent sur la barre d'ouverture, pour 7,7 % des barres.
- À cette barre, `nis_z_100` vaut 1,40 et 1,59 en médiane, contre 0,14 et 0,13 ailleurs : le gap est une innovation.
- Le seuil BTC écarte **64 % (SPY) et 74 % (XLE) des signaux R2 nés d'un gap**, contre 20 % et 16 % des autres. L'univers de RE-1 ne garde que 19 et 14 signaux sur barre d'ouverture.

**Les trades : RE-1 évite d'entrer sur le gap, mais le subit en position.**
- **H = 26 barres = 2 séances.** 92 % (SPY) et 90 % (XLE) des trades traversent au moins une nuit, 2 en médiane. La durée calendaire est de 48 h (P90 96 h), contre 13 h sur BTC.
- **Décomposition du rendement brut (log, en ATR par trade) :**

  | | Brut [IC] | dont gaps traversés [IC] | dont séance [IC] | Gagnants : gaps ; séance | Perdants : gaps ; séance |
  |---|---|---|---|---|---|
  | XAU | +0,237 [−0,107 ; +0,605] | +0,027 [−0,026 ; +0,092] | +0,210 [−0,116 ; +0,555] | +0,14 ; +3,86 | −0,06 ; −2,49 |
  | SPY | +0,000 [−0,578 ; +0,589] | +0,027 [−0,332 ; +0,374] | −0,026 [−0,533 ; +0,475] | +1,26 ; +2,14 | −0,99 ; −1,81 |
  | XLE | +0,091 [−0,516 ; +0,749] | +0,192 [−0,254 ; +0,642] | −0,101 [−0,588 ; +0,426] | +1,62 ; +1,84 | −0,97 ; −1,68 |

  - En moyenne, les gaps ne créent ni ne détruisent de valeur (IC centrés sur zéro).
  - Mais ils pèsent 35 à 47 % de l'amplitude des gagnants et des perdants. Sur l'or, le résultat se fait en séance.
- **Stops percés à l'ouverture.** 8 stops sur 46 (SPY) et 11 sur 48 (XLE) s'exécutent à l'ouverture au-delà de leur niveau. Le dépassement moyen est de +2,57 ATR pour SPY (P90 +5,76) et de +1,01 pour XLE (P90 +3,25), contre +0,76 pour l'or (2 cas). La protection SL-B est poreuse à travers la nuit.
- **Espérance selon la barre du signal** (petits effectifs, rien de significatif) :
  - sur la barre d'ouverture : SPY −1,28 ATR (15 trades), XLE +0,43 (11) ;
  - sur la dernière barre de séance, donc entrée juste après le gap : SPY +0,07 (17), XLE −0,74 (23) ;
  - ailleurs : SPY −0,05 (123), XLE +0,15 (102).

## 6. [OBS] Mécanismes : ce qui se retrouve, ce qui change

- **Le profil queue droite se retrouve partout.**
  - Trade médian négatif : −0,42 à −0,93 ATR.
  - Le décile supérieur apporte, par trade, +0,68 à +0,92 ATR.
- **Le stop de F3 réduit le drawdown sur les cinq actifs.**
  - Sur BTC, SOL et l'or, son effet sur l'espérance est nul (±0,03).
  - Sur les ETF, il est positif (+0,40 et +0,46), sans être significatif. Les F3 stoppés y perdent −2,7 (SPY) et −2,3 ATR (XLE) en moyenne, contre −2,2 sur BTC.
- **La haute volatilité est le régime faible sur BTC et SOL.** Sur l'or et les ETF, les terciles ne montrent pas de structure (effectifs de 45 à 52 trades sur les ETF).
- **La bascule de `nis_z_100` à P75 (C05) ne se reproduit pas telle quelle** (trades isolés, descriptif). Sur SPY, toutes les bandes au-delà de P70 sont négatives. Sur XLE aussi, sauf P75-P80 (+0,74 ATR sur 8 trades). Les IC font ±1,5 à ±2,5 ATR.
- **Hiérarchie F2b > F3 :** celle de BTC se retrouve sur SOL, s'inverse sur l'or et sur XLE, et F3 est négatif sur SPY.

## 7. [HYP] Lectures

- **La population transfère, la rente dépend du marché et de sa structure de cotation.**
  - Sur les marchés 24/7 (SOL) et quasi continus (or), la cinématique captée garde un brut d'environ la moitié de BTC.
  - Sur les ETF en séances, le brut tombe à 0 (SPY) et +0,10 ATR (XLE).
- **L'or en 30 min est asphyxié par le rapport frais / ATR.** C'est un constat de physique du trade, pas un verdict sur le signal : une question d'échelle de temps.
- **Sur les ETF, H compte des barres, pas du temps.**
  - La cinématique d'une séance (une vitesse qui se retourne) est jugée deux séances plus tard, après deux gaps.
  - Le filtre d'innovation écarte bien les signaux nés d'un gap, mais la position subit ensuite des gaps qu'elle n'a pas choisis. Ils pèsent 35 à 47 % de l'amplitude des trades, et les stops sont percés de 1 à 2,6 ATR en moyenne à l'ouverture.
  - L'allongement des jambes par les gaps rend aussi le seuil `leg_atr` de BTC plus sélectif.
- **Dérive :** la hausse de 2020-2025 pénalise les ventes sur l'or et sur SPY.
- **XLE informe sur les actions sectorielles, pas sur le pétrole** (corrélation 0,46 avec le WTI, 0,60 avec SPY).

## 8. [DECISION] Proposée

- **RE-1 reste inchangée.** D01 est clos, descriptif, sans classement ni retrait d'actif sur performance :
  - 5 actifs mesurés : BTC en référence, SOL/USD, or, SPY, XLE ;
  - WTI retiré par le porteur.
- **Carte des faiblesses du modèle fixe, pour D02 :**
  1. **Rapport frais / ATR.** L'or en 30 min : 0,26 ATR de frais par trade.
  2. **Structure de séance.** Sur les ETF, H = 26 barres fait traverser deux nuits ; stops percés ; effectifs d'environ 2 trades par mois.
  3. **Dérive.** Les ventes sont pénalisées en marché haussier : or, SPY.
  4. **Dépendance à la queue droite** sur tous les actifs.
- **Restent au porteur :**
  - la validation de la source XAU (HistData, courtier non divulgué, fuseau corrigé), ou un recoupement ;
  - le push des commits locaux.

## 9. Préparation de D02 (réflexion ; rien n'est défini ni testé)

- **Outil.**
  - VectorBT et Numba ne sont pas installés : leur installation demandera l'accord du porteur.
  - Contrôle bloquant proposé pour le portage : reproduire trade par trade les 1 080 trades BTC de `strategy.re1`.
  - Points délicats : le cooldown (entrées de la course sans stop, qui dépendent de H), le stop intrabarre avec gap à l'ouverture, et la sortie à open[t + 1 + H].
- **Paramètres H et R0.**
  - R0 change le signal lui-même, donc l'atlas, les familles et les quantiles. Il faudra trancher : garder les seuils numériques de BTC ou les réestimer à chaque R0.
  - L'optimisation conjointe de H et R0 est une exception explicite du porteur à la règle OFAT : à consigner comme décision.
- **Ce que D01 met en évidence pour D02, sans rien en conclure :**
  - Les frais pèsent très différemment en ATR selon l'actif : 0,06 à 0,26. Toute fonction objectif doit être nette de frais.
  - Sur les ETF, faire varier H change le nombre de nuits traversées : H ≤ 12 reste dans la séance, H = 13 en traverse une, H = 26 deux. L'effet de H y est en partie un effet d'exposition aux gaps.
  - À environ 2 trades par mois, des fenêtres de walk-forward sur les ETF ne contiendraient que quelques dizaines de trades.
  - Le dimensionnement à 0,25 %/ATR est plafonné à 1x sur l'or et, pour moitié, sur SPY : les objectifs « à risque normalisé » n'y sont pas comparables tant que le levier est borné à 1.
  - L'espérance tient à la queue droite sur tous les actifs : un Calmar par fenêtre sera bruité.
