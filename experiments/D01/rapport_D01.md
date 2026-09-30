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
| ETF SPY (Alpaca, séance régulière) | mesuré | 155 trades sur 191 candidats ; 6,00 ans |
| ETF XLE (Alpaca, séance régulière) | mesuré | 136 trades sur 159 candidats ; 6,00 ans |
| CFD WTI (HistData) | retiré | retiré de D01 par le porteur (2026-09-30) et remplacé par XLE : couverture HistData arrêtée au 2023-12-01 et CFD de contrat du mois non ajusté (audit ci-dessous, pour mémoire). Aucun backtest. |

## B. Données : instruments et audit (étape 1, avant tout PnL)

| Champ | BTC/USD (Bitstamp, référence) | SOL/USD (Coinbase) | CFD or XAU/USD (HistData) | ETF SPY (Alpaca, séance régulière) | ETF XLE (Alpaca, séance régulière) | CFD WTI (HistData) |
|---|---|---|---|---|---|---|
| Instrument | BTC/USD, carnet spot de Bitstamp (TradingView : BITSTAMP:BTCUSD) | SOL/USD, carnet spot de Coinbase Exchange (TradingView : COINBASE:SOLUSD) | CFD sur l'or au comptant, XAU/USD (TradingView : XAUUSD, p. ex. OANDA:XAUUSD, FOREXCOM:XAUUSD) | SPDR S&P 500 ETF Trust (NYSE Arca : SPY ; TradingView : AMEX:SPY) | Energy Select Sector SPDR Fund (NYSE Arca : XLE ; TradingView : AMEX:XLE) | CFD sur le pétrole brut WTI, WTI/USD (TradingView : USOIL, p. ex. TVC:USOIL, OANDA:WTICOUSD) |
| Nature | spot crypto, cotation en dollars américains | spot crypto, cotation en dollars américains | CFD / cotation OTC au comptant d'un courtier forex, compilée par HistData.com | ETF indiciel coté (actions américaines du S&P 500) | ETF sectoriel coté (actions du secteur énergie du S&P 500) ; proxy de l'énergie choisi par le porteur à la place du WTI, sans roulement de contrats ; correspondance avec le WTI documentée par l'audit | CFD d'un courtier sur le contrat à terme NYMEX WTI (CL), compilé par HistData.com |
| Ticker | btcusd (Bitstamp) | SOL-USD (Coinbase Exchange) | XAUUSD (HistData.com, ASCII M1) | SPY | XLE | WTIUSD (HistData.com, ASCII M1) |
| Continuité | sans objet : instrument spot, série unique | sans objet : instrument spot, série unique | sans objet : cotation au comptant, sans échéance | sans objet : titre coté, série unique | sans objet : titre coté, série unique | non publiée par la source ; caractérisée par l'audit (écart au spot WTI Cushing quotidien de l'EIA, FRED DCOILWTICO) |
| Roulements | sans objet | sans objet | sans objet ; le coût de portage (swap) d'un CFD au comptant n'est pas dans les prix | sans objet | sans objet | non publiés par la source ; sauts de roulement recherchés par l'audit |
| Ajustements | aucun | aucun | aucun | fractionnements et dividendes (adjustment=all d'Alpaca) ; série brute écrite à part (_brut) | fractionnements et dividendes (adjustment=all d'Alpaca) ; série brute écrite à part (_brut) | aucun appliqué |
| Prix | — | — | bid (FAQ HistData : barres construites sur le bid des ticks) | transactions consolidées SIP (OHLC des transactions), et non bid/ask | transactions consolidées SIP (OHLC des transactions), et non bid/ask | bid (FAQ HistData : barres construites sur le bid des ticks) |
| Fuseau | UTC | UTC (début des bougies Coinbase) | étiquettes HistData converties en UTC : la FAQ annonce un EST fixe, mais l'horloge suit l'heure d'été européenne (serveur EET/EEST moins 7 h : UTC−5 en hiver européen, UTC−4 de fin mars à fin octobre) ; établi par l'audit D01 (pause quotidienne à 17:00-18:00 heure de New York toute l'année après conversion) | UTC (début de barre) ; séance lue en heure de New York | UTC (début de barre) ; séance lue en heure de New York | étiquettes HistData converties en UTC : la FAQ annonce un EST fixe, mais l'horloge suit l'heure d'été européenne (serveur EET/EEST moins 7 h : UTC−5 en hiver européen, UTC−4 de fin mars à fin octobre) ; établi par l'audit D01 (pause quotidienne à 17:00-18:00 heure de New York toute l'année après conversion) |
| Horaires | cotation continue 24/7 | cotation continue 24/7 ; les interruptions sont des maintenances ou incidents de la plateforme | marché OTC 24 h sur 24, 5 jours sur 7, pause quotidienne d'une heure calée sur New York ; vérifiés par l'audit | séance régulière 09:30-16:00 heure de New York, jours ouvrés du NYSE ; pré- et post-marché écartés | séance régulière 09:30-16:00 heure de New York, jours ouvrés du NYSE ; pré- et post-marché écartés | marché OTC 24 h sur 24, 5 jours sur 7, pause quotidienne d'une heure calée sur New York ; vérifiés par l'audit |
| Construction des barres 30 min | bougies 30 min natives de l'API OHLC publique de Bitstamp (step 1800) | agrégation exacte des bougies natives de 15 min (granularité 900 s) en barres de 30 min alignées sur :00 et :30 UTC : open de la première, plus haut, plus bas, close de la dernière, somme des volumes (en SOL) ; time = ouverture de la barre ; une barre sans transaction est un trou, jamais comblé | agrégation exacte des bougies d'une minute en barres de 30 min alignées sur :00 et :30 UTC ; time = ouverture de la barre ; volume absent de la source (écrit nul) ; une barre sans minute cotée est un trou, jamais comblé | barres natives de 30 min d'Alpaca (flux SIP) filtrées sur la séance régulière : 13 barres par séance, 7 les jours de clôture anticipée | barres natives de 30 min d'Alpaca (flux SIP) filtrées sur la séance régulière : 13 barres par séance, 7 les jours de clôture anticipée | agrégation exacte des bougies d'une minute en barres de 30 min alignées sur :00 et :30 UTC ; time = ouverture de la barre ; volume absent de la source (écrit nul) ; une barre sans minute cotée est un trou, jamais comblé |
| Couverture | 2020-01-01 → 2025-12-31 (lecture tronquée avant 2026) | 2021-01 → 2025-12 ; SOL-USD est coté sur Coinbase depuis le 2021-06-17 ; 2026 non téléchargé | années 2020 à 2025 ; 2026 non téléchargé | 2020-01-01 → 2025-12-31 ; 2026 non téléchargé | 2020-01-01 → 2025-12-31 ; 2026 non téléchargé | années 2020 à 2025 ; HistData ne publie WTIUSD que jusqu'au 2023-12-01 (aucun fichier pour 2024 et 2025 : jeton de téléchargement vide) ; couverture obtenue 2020-01 → 2023-12-01 |
| Limite | — | — | fournisseur amont (courtier) non divulgué par HistData | — | — | fournisseur amont (courtier) non divulgué par HistData |
| Barres (première → dernière) | 105 216 (2020-01-01 00:00 → 2025-12-31 23:30) | 79 577 (2021-06-17 16:00 → 2025-12-31 23:30) | 69 381 (2020-01-01 23:00 → 2025-12-31 21:30) | 19 532 (2020-01-02 14:30 → 2025-12-31 20:30) | 19 532 (2020-01-02 14:30 → 2025-12-31 20:30) | 44 836 (2020-01-01 23:00 → 2023-12-01 21:30) |

| Actif | Barres / cotation 24/7 | Trous : n ; barres manquantes | Trous ≤ 2 h ; ≤ 3 j ; > 3 j | Plus long trou (début) | Défauts d'intégrité | Barres plates ; volume nul | Structure des séances | Écart d'ouverture (bps) : P99,9 ; médiane après trou |
|---|---|---|---|---|---|---|---|---|
| BTC | 100,0 % | 0 ; 0 | 0 ; 0 ; 0 | — | aucune | 40 ; 39 | cotation continue 24/7 | 24 ; — |
| SOL | 100,0 % | 4 ; 23 | 2 ; 2 ; 0 | 2025-10-25 15:00 (5,5 h) | aucune | 0 ; 0 | cotation continue 24/7 | 24 ; 4,8 |
| XAU | 66,0 % | 2 101 ; 35 785 | 1711 ; 377 ; 13 | 2020-12-24 18:30 (76,0 h) | aucune | 0 ; source sans volume | pause 17:00-18:00 NY seule : 303 semaines sur 314 | 40 ; 3,3 |
| SPY | 18,6 % | 1 507 ; 85 601 | 0 ; 1464 ; 43 | 2020-12-24 17:30 (92,5 h) | aucune | 0 ; 0 | séance 09:30-15:30 NY, 13 barres ; 12 séances courtes | 301 ; 33,1 |
| XLE | 18,6 % | 1 507 ; 85 601 | 0 ; 1464 ; 43 | 2020-12-24 17:30 (92,5 h) | aucune | 0 ; 0 | séance 09:30-15:30 NY, 13 barres ; 12 séances courtes | 435 ; 57,1 |
| WTI | 65,3 % | 1 541 ; 23 802 | 1267 ; 265 ; 9 | 2020-12-24 18:30 (76,0 h) | aucune | 0 ; source sans volume | pause 17:00-18:00 NY seule : 195 semaines sur 205 | 142 ; 10,9 |

- XAU : 360 minutes répétées à l'identique supprimées à la construction (2020-10-26, 2021-11-01, 2022-10-31, 2023-10-30, 2024-10-28, 2025-10-27), une heure par an le lundi qui suit la fin de l'heure d'été européenne ; continuité des prix vérifiée.
- WTI : 239 minutes répétées à l'identique supprimées à la construction (2020-10-26, 2021-11-01, 2022-10-31, 2023-10-30), une heure par an le lundi qui suit la fin de l'heure d'été européenne ; continuité des prix vérifiée.

**CFD WTI contre le spot WTI Cushing de l'EIA** (close de la barre 14:00-14:30 heure de New York ; le spot suit le contrat échéant jusqu'à son expiration) :
- 923 jours communs ; écart CFD − spot médian −0,02 $ (par année : 2020 +0,00 ; 2021 −0,03 ; 2022 −0,12 ; 2023 −0,03) ; P5-P95 [−1,88 ; +0,19] $.
- Écart médian par tranche de jours du mois : 1-5 −0,02 ; 6-10 −0,02 ; 11-15 −0,03 ; 16-20 −0,02 ; 21-25 −0,03 ; 26-31 −0,02 $. Jours à plus de 0,25 $ d'écart : 211, par tranche du mois : 1-5 18 ; 6-10 18 ; 11-15 24 ; 16-20 54 ; 21-25 51 ; 26-31 46.
- Corrélation des variations quotidiennes, hors 20-21 avril 2020 : Pearson 0,978, Spearman 0,973.
- Échéance de juin 2021 (contrat de juillet, expiré le 22/06), CFD / spot : 06-16 72,03 / 72,03 ; 06-17 71,04 / 71,06 ; 06-18 71,64 / 71,64 ; 06-21 73,10 / 73,64 ; 06-22 72,82 / 73,15 ; 06-23 73,06 / 73,11 ; 06-24 73,29 / 73,31.
- Avril 2020, CFD / spot : 04-15 19,93 / 19,96 ; 04-16 19,86 / 19,82 ; 04-17 18,29 / 18,31 ; 04-20 20,27 / −36,98 ; 04-21 11,52 / 8,91 ; 04-22 13,77 / 13,64 ; 04-23 16,80 / 15,06 ; 04-24 17,00 / 15,99.

**XLE, proxy de l'énergie (décision du porteur)** : variations quotidiennes contre le spot WTI de l'EIA (hors 17-22 avril 2020) : Pearson 0,46, Spearman 0,56, bêta 0,30 (1 495 jours) ; contre SPY : Pearson 0,60, bêta 1,00.

**WTI retiré** : retiré de D01 par le porteur (2026-09-30) et remplacé par XLE : couverture HistData arrêtée au 2023-12-01 et CFD de contrat du mois non ajusté (audit ci-dessous, pour mémoire). Aucun backtest.

## C. Signaux : distributions face aux seuils BTC gelés (descriptif)

| Actif | Signaux (par mois) | x1 déjà retourné | leg_atr P50 [P25 ; P75] | leg_atr < 2,8233 (seuil BTC) | retrace_ratio P50 [P25 ; P75] | nis_z_100 P50 ; P75 local | nis_z_100 > 1,2245 : tous ; dans R2 | ATR14 bps P50 [P10 ; P90] |
|---|---|---|---|---|---|---|---|---|
| BTC | 7 296 (101,3) | 51,8 % | 2,82 [2,17 ; 3,94] | 50,0 % | 0,62 [0,41 ; 0,84] | 0,19 ; P75 local 1,225 | 25,0 % ; 22,5 % | 49,7 [23,3 ; 99,4] |
| SOL | 5 385 (98,8) | 52,3 % | 2,85 [2,24 ; 3,92] | 49,1 % | 0,60 [0,38 ; 0,84] | 0,33 ; P75 local 1,368 | 27,3 % ; 29,5 % | 94,8 [56,6 ; 168,7] |
| XAU | 4 649 (64,6) | 49,4 % | 2,90 [2,20 ; 4,04] | 47,7 % | 0,59 [0,34 ; 0,82] | 0,25 ; P75 local 1,217 | 24,9 % ; 24,7 % | 17,2 [11,8 ; 28,5] |
| SPY | 1 263 (17,6) | 51,5 % | 3,09 [2,35 ; 4,35] | 41,6 % | 0,59 [0,32 ; 0,86] | 0,21 ; P75 local 1,336 | 28,0 % ; 28,5 % | 28,7 [16,5 ; 57,3] |
| XLE | 1 267 (17,6) | 46,3 % | 3,24 [2,44 ; 4,33] | 37,6 % | 0,58 [0,33 ; 0,86] | 0,21 ; P75 local 1,123 | 22,4 % ; 30,0 % | 52,1 [34,5 ; 92,7] |
| WTI | 3 028 (64,5) | 50,6 % | 2,93 [2,20 ; 4,00] | 46,4 % | 0,61 [0,35 ; 0,87] | 0,25 ; P75 local 1,311 | 26,3 % ; 23,0 % | 45,1 [28,0 ; 88,6] |

| Actif | Familles (seuil leg BTC) | R1 ; R2 avant nis ; R3 ; hors régimes | R2 écartés par nis | Univers RE-1 (F2b ; F3) |
|---|---|---|---|---|
| BTC | F1 1 869 ; F2a 1 303 ; F2b 1 592 ; F3 1 315 ; F4 476 ; F5 741 | 1 935 ; 1 874 ; 2 347 ; 1 140 | 422 | 1 452 (741 ; 711) |
| SOL | F1 1 530 ; F2a 923 ; F2b 1 129 ; F3 1 029 ; F4 289 ; F5 485 | 1 500 ; 1 461 ; 1 668 ; 756 | 431 | 1 030 (548 ; 482) |
| XAU | F1 1 398 ; F2a 760 ; F2b 932 ; F3 787 ; F4 274 ; F5 498 | 1 442 ; 1 128 ; 1 413 ; 666 | 279 | 849 (447 ; 402) |
| SPY | F1 414 ; F2a 200 ; F2b 207 ; F3 211 ; F4 123 ; F5 108 | 370 ; 267 ; 463 ; 163 | 76 | 191 (93 ; 98) |
| XLE | F1 437 ; F2a 234 ; F2b 184 ; F3 205 ; F4 120 ; F5 87 | 405 ; 227 ; 464 ; 171 | 68 | 159 (61 ; 98) |
| WTI | F1 870 ; F2a 472 ; F2b 567 ; F3 517 ; F4 281 ; F5 321 | 916 ; 684 ; 990 ; 438 | 157 | 527 (249 ; 278) |

## D. Tableau standard (8 métriques nettes)

| Actif, frais | PnL net : 0,25 %/ATR ; 1x ; bps cumulés (1x) | PF : 1x ; pondéré | WR | Espérance : bps [IC] ; ATR [IC] | MDD valorisé : 0,25 %/ATR ; 1x | Trades (par mois) ; stoppés | Durée médiane : barres ; calendaire | Part des frais : 1x ; pondérée |
|---|---|---|---|---|---|---|---|---|
| BTC 5 bps | +138 % ; +204 % ; +13320 | 1,20 ; 1,28 | 44,3 % | +12,3 [+0,2 ; +24,4] ; +0,369 [+0,098 ; +0,645] | −13,5 % ; −43,9 % | 1 080 (15,0) ; 24 % | 26 ; 13,0 h | 29 % ; 26 % |
| BTC 10 bps | +72 % ; +77 % ; +7920 | 1,11 ; 1,17 | 42,8 % | +7,3 [−4,8 ; +19,4] ; +0,233 [−0,041 ; +0,511] | −15,9 % ; −48,0 % | 1 080 (15,0) ; 24 % | 26 ; 13,0 h | 58 % ; 52 % |
| SOL 5 bps | +39 % ; +173 % ; +14747 | 1,17 ; 1,16 | 44,1 % | +19,2 [−3,6 ; +44,2] ; +0,190 [−0,079 ; +0,484] | −13,1 % ; −42,3 % | 769 (14,1) ; 24 % | 26 ; 13,0 h | 21 % ; 24 % |
| SOL 10 bps | +24 % ; +86 % ; +10902 | 1,12 ; 1,10 | 43,4 % | +14,2 [−8,6 ; +39,2] ; +0,129 [−0,140 ; +0,425] | −15,2 % ; −44,4 % | 769 (14,1) ; 24 % | 26 ; 13,0 h | 41 % ; 48 % |
| XAU 4 bps | +1 % ; +5 % ; +697 | 1,04 ; 1,01 | 42,5 % | +1,1 [−4,9 ; +7,5] ; −0,019 [−0,362 ; +0,349] | −13,6 % ; −13,3 % | 651 (9,0) ; 26 % | 26 ; 13,0 h | 79 % ; 92 % |
| SPY 4 bps | −4 % ; −8 % ; −696 | 0,91 ; 0,93 | 45,2 % | −4,5 [−23,7 ; +14,9] ; −0,158 [−0,736 ; +0,434] | −10,9 % ; −19,2 % | 155 (2,2) ; 30 % | 26 ; 48,0 h | brut ≤ 0 ; 386 % |
| XLE 4 bps | +0 % ; +7 % ; +1013 | 1,09 ; 1,01 | 44,9 % | +7,4 [−28,7 ; +43,9] ; +0,020 [−0,588 ; +0,674] | −19,5 % ; −36,4 % | 136 (1,9) ; 35 % | 26 ; 48,0 h | 35 % ; 80 % |

## E. Risque, sens, timing et sous-familles

| Actif, frais | Années | 0,25 %/ATR : CAGR ; Calmar | 1x : CAGR ; Calmar | Exposition moyenne ; trades plafonnés à 1x | Long / Short (ATR) | Timing ATR [IC] | Timing bps [IC] | F2b : n ; ATR | F3 : n ; ATR |
|---|---|---|---|---|---|---|---|---|---|
| BTC 5 bps | 6,00 | +15,6 % ; 1,16 | +20,3 % ; 0,46 | 60 % ; 16 % | +0,457 / +0,266 | +0,362 [+0,089 ; +0,638] | +12,3 [+0,2 ; +24,5] | 573 ; +0,459 | 507 ; +0,267 |
| BTC 10 bps | 6,00 | +9,5 % ; 0,60 | +10,0 % ; 0,21 | 60 % ; 16 % | +0,320 / +0,131 | +0,226 [−0,050 ; +0,507] | +7,3 [−4,8 ; +19,5] | 573 ; +0,326 | 507 ; +0,127 |
| SOL 5 bps | 4,54 | +7,6 % ; 0,58 | +24,8 % ; 0,59 | 30 % ; 0 % | +0,246 / +0,136 | +0,191 [−0,079 ; +0,490] | +19,2 [−3,6 ; +44,0] | 415 ; +0,287 | 354 ; +0,076 |
| SOL 10 bps | 4,54 | +4,9 % ; 0,32 | +14,7 % ; 0,33 | 30 % ; 0 % | +0,184 / +0,076 | +0,130 [−0,140 ; +0,431] | +14,2 [−8,6 ; +39,0] | 415 ; +0,228 | 354 ; +0,014 |
| XAU 4 bps | 6,00 | +0,1 % ; 0,01 | +0,9 % ; 0,07 | 98 % ; 89 % | +0,329 / −0,431 | −0,051 [−0,399 ; +0,306] | +0,5 [−5,2 ; +6,9] | 350 ; −0,304 | 301 ; +0,313 |
| SPY 4 bps | 6,00 | −0,7 % ; −0,07 | −1,4 % ; −0,07 | 82 % ; 47 % | +0,107 / −0,601 | −0,247 [−0,825 ; +0,360] | −7,3 [−29,2 ; +14,8] | 76 ; +0,059 | 79 ; −0,367 |
| XLE 4 bps | 6,00 | +0,0 % ; 0,00 | +1,2 % ; 0,03 | 50 % ; 0 % | +0,197 / −0,339 | −0,071 [−0,739 ; +0,650] | +7,1 [−34,0 ; +52,0] | 50 ; −0,186 | 86 ; +0,139 |

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
| SPY 4 bps | F2b | Long | 45 | +0,253 [−1,004 ; +1,521] | +14,2 | +0,073 |
| SPY 4 bps | F2b | Short | 31 | −0,222 [−1,558 ; +1,294] | +3,5 | −0,044 |
| SPY 4 bps | F2b | tous | 76 | +0,059 [−0,806 ; +0,913] | +9,9 | +0,029 |
| SPY 4 bps | F3 | Long | 52 | −0,019 [−0,822 ; +0,861] | −5,1 | −0,006 |
| SPY 4 bps | F3 | Short | 27 | −1,037 [−2,261 ; +0,223] | −43,6 | −0,181 |
| SPY 4 bps | F3 | tous | 79 | −0,367 [−1,101 ; +0,373] | −18,3 | −0,187 |
| SPY 4 bps | tous | Long | 97 | +0,107 [−0,641 ; +0,974] | +3,9 | +0,067 |
| SPY 4 bps | tous | Short | 58 | −0,601 [−1,523 ; +0,395] | −18,4 | −0,225 |
| SPY 4 bps | tous | tous | 155 | −0,158 [−0,736 ; +0,434] | −4,5 | −0,158 |
| XLE 4 bps | F2b | Long | 30 | +0,511 [−1,030 ; +2,033] | +7,6 | +0,113 |
| XLE 4 bps | F2b | Short | 20 | −1,231 [−2,752 ; +0,305] | −12,6 | −0,181 |
| XLE 4 bps | F2b | tous | 50 | −0,186 [−1,269 ; +0,829] | −0,5 | −0,068 |
| XLE 4 bps | F3 | Long | 61 | +0,043 [−0,733 ; +0,874] | +8,3 | +0,019 |
| XLE 4 bps | F3 | Short | 25 | +0,374 [−1,048 ; +2,053] | +21,2 | +0,069 |
| XLE 4 bps | F3 | tous | 86 | +0,139 [−0,577 ; +0,984] | +12,1 | +0,088 |
| XLE 4 bps | tous | Long | 91 | +0,197 [−0,448 ; +0,866] | +8,1 | +0,132 |
| XLE 4 bps | tous | Short | 45 | −0,339 [−1,363 ; +0,802] | +6,2 | −0,112 |
| XLE 4 bps | tous | tous | 136 | +0,020 [−0,588 ; +0,674] | +7,4 | +0,020 |

## G. Stops de F3 (SL-B à l'extremum) : fréquence et contribution

| Actif | Stoppés / F3 | Espérance ATR : stoppés ; F3 non stoppés | Contribution des stoppés (ATR) | Effet apparié du stop sur F3 (ATR [IC]) | MDD 0,25 %/ATR : RE-1 contre sans stop | Calmar : RE-1 contre sans stop | MDD 1x : RE-1 contre sans stop |
|---|---|---|---|---|---|---|---|
| BTC 5 bps | 257 / 507 (51 %) | −2,18 ; +2,78 | −0,518 | +0,031 [−0,230 ; +0,305] | −13,5 % contre −20,5 % | 1,16 contre 0,69 | −43,9 % contre −47,6 % |
| SOL 5 bps | 186 / 354 (53 %) | −2,07 ; +2,45 | −0,500 | +0,027 [−0,182 ; +0,247] | −13,1 % contre −16,8 % | 0,58 contre 0,41 | −42,3 % contre −49,7 % |
| XAU 4 bps | 169 / 301 (56 %) | −2,30 ; +3,65 | −0,596 | −0,031 [−0,355 ; +0,317] | −13,6 % contre −15,3 % | 0,01 contre −0,02 | −13,3 % contre −17,3 % |
| SPY 4 bps | 46 / 79 (58 %) | −2,69 ; +2,87 | −0,798 | +0,461 [−0,248 ; +1,112] | −10,9 % contre −16,0 % | −0,07 contre −0,13 | −19,2 % contre −25,7 % |
| XLE 4 bps | 48 / 86 (56 %) | −2,31 ; +3,24 | −0,816 | +0,398 [−0,227 ; +1,010] | −19,5 % contre −22,3 % | 0,00 contre −0,07 | −36,4 % contre −38,7 % |

## H. Distribution des trades (espérance nette en ATR, frais de lecture principale)

| Actif | P10 ; P25 ; P50 ; P75 ; P90 | Moyenne ; winsorisée P1/P99 | Apport du décile supérieur par trade (part du total) | Durée calendaire (h) : médiane ; P90 ; part > 24 h |
|---|---|---|---|---|
| BTC 5 bps | −2,83 ; −2,10 ; −0,42 ; +2,06 ; +5,53 | +0,369 ; +0,379 | +0,919 (249 %) | 13,0 ; 13,0 ; 0 % |
| SOL 5 bps | −2,82 ; −2,02 ; −0,56 ; +1,97 ; +4,61 | +0,190 ; +0,139 | +0,765 (403 %) | 13,0 ; 13,0 ; 0 % |
| XAU 4 bps | −3,74 ; −2,45 ; −0,93 ; +2,36 ; +5,17 | −0,019 ; −0,023 | +0,847 (espérance totale ≈ 0 ou négative) | 13,0 ; 20,0 ; 8 % |
| SPY 4 bps | −3,96 ; −2,49 ; −0,72 ; +2,30 ; +4,73 | −0,158 ; −0,137 | +0,748 (espérance totale ≈ 0 ou négative) | 48,0 ; 96,0 ; 84 % |
| XLE 4 bps | −3,73 ; −2,46 ; −0,80 ; +2,60 ; +4,63 | +0,020 ; +0,001 | +0,676 (espérance totale ≈ 0 ou négative) | 48,0 ; 96,0 ; 76 % |

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
| SPY 4 bps | T1 calme | 11,9 – 20,7 | 52 | −0,295 [−1,390 ; +0,921] | −2,4 [−20,5 ; +17,4] | 44,2 % | 29 % |
| SPY 4 bps | T2 | 20,8 – 34,2 | 51 | +0,394 [−0,302 ; +1,017] | +11,2 [−8,0 ; +28,7] | 51,0 % | 29 % |
| SPY 4 bps | T3 agité | 34,2 – 227,1 | 52 | −0,562 [−1,630 ; +0,556] | −22,0 [−71,2 ; +32,6] | 40,4 % | 31 % |
| XLE 4 bps | T1 calme | 26,3 – 41,8 | 45 | +0,515 [−0,552 ; +1,548] | +18,0 [−21,7 ; +56,4] | 48,9 % | 36 % |
| XLE 4 bps | T2 | 41,9 – 61,2 | 45 | −0,629 [−1,747 ; +0,621] | −32,0 [−88,8 ; +29,9] | 35,6 % | 40 % |
| XLE 4 bps | T3 agité | 61,9 – 255,6 | 46 | +0,170 [−0,597 ; +0,984] | +35,7 [−34,5 ; +120,5] | 50,0 % | 30 % |

## J. nis_z_100 : bandes de l'univers R2 avant exclusion (trades isolés, bornes aux quantiles de l'atlas BTC)

Descriptif : chaque signal R2 joué seul avec l'enveloppe de RE-1, sans sélection séquentielle. Rien n'en est tiré pour l'exécution.

| Actif | ≤ P70 (BTC) | P70–P75 (BTC) | P75–P80 (BTC) | P80–P85 (BTC) | P85–P90 (BTC) | > P90 (BTC) |
|---|---|---|---|---|---|---|
| BTC 5 bps | 1 358 : +0,17 [−0,05 ; +0,39] | 94 : +0,53 [−0,27 ; +1,34] | 87 : −0,30 [−0,79 ; +0,20] | 82 : −0,74 [−1,51 ; +0,12] | 84 : +0,22 [−0,66 ; +1,21] | 169 : −0,40 [−0,93 ; +0,17] |
| SOL 5 bps | 939 : +0,22 [+0,02 ; +0,46] | 91 : +0,13 [−0,50 ; +0,89] | 90 : −0,23 [−0,83 ; +0,38] | 105 : +0,06 [−0,66 ; +0,95] | 90 : −0,15 [−0,73 ; +0,42] | 146 : +0,55 [−0,01 ; +1,19] |
| XAU 4 bps | 777 : +0,05 [−0,25 ; +0,36] | 72 : −0,43 [−1,28 ; +0,46] | 63 : −0,20 [−1,19 ; +0,88] | 62 : +0,11 [−0,67 ; +0,87] | 53 : −0,05 [−0,90 ; +0,86] | 101 : −0,49 [−1,10 ; +0,15] |
| SPY 4 bps | 178 : +0,14 [−0,41 ; +0,73] | 13 : −1,15 [−3,09 ; +1,08] | 19 : −0,35 [−1,37 ; +0,64] | 15 : −0,90 [−2,31 ; +0,94] | 15 : −0,22 [−1,94 ; +1,55] | 27 : −0,31 [−1,56 ; +1,06] |
| XLE 4 bps | 148 : +0,08 [−0,51 ; +0,72] | 11 : −0,25 [−1,81 ; +1,43] | 8 : +0,74 [−1,53 ; +3,08] | 16 : −0,26 [−2,01 ; +1,66] | 8 : −0,39 [−2,62 ; +2,23] | 36 : −0,64 [−1,60 ; +0,41] |

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
| SPY 4 bps | 2020 | 21 | +0,716 | +31,5 | +3,6 % | +6,6 % | +1,08 / −0,02 |
| SPY 4 bps | 2021 | 28 | −0,542 | −9,3 | −2,7 % | −2,6 % | −0,24 / −0,95 |
| SPY 4 bps | 2022 | 24 | −0,071 | −11,2 | −0,5 % | −3,0 % | −0,24 / +0,21 |
| SPY 4 bps | 2023 | 29 | +0,489 | +0,6 | +2,1 % | +0,0 % | +1,02 / −0,38 |
| SPY 4 bps | 2024 | 22 | −0,678 | −15,2 | −2,7 % | −3,4 % | −0,57 / −0,87 |
| SPY 4 bps | 2025 | 31 | −0,708 | −16,5 | −3,8 % | −5,3 % | −0,39 / −1,29 |
| XLE 4 bps | 2020 | 21 | +1,358 | +140,6 | +7,3 % | +32,9 % | +0,63 / +2,16 |
| XLE 4 bps | 2021 | 28 | −1,198 | −59,1 | −8,1 % | −15,5 % | −1,00 / −1,80 |
| XLE 4 bps | 2022 | 19 | −1,065 | −60,1 | −5,0 % | −11,5 % | −0,61 / −2,04 |
| XLE 4 bps | 2023 | 28 | −0,324 | −21,6 | −2,3 % | −6,2 % | −0,14 / −1,01 |
| XLE 4 bps | 2024 | 25 | +1,036 | +38,8 | +6,5 % | +9,8 % | +1,90 / −0,06 |
| XLE 4 bps | 2025 | 15 | +0,739 | +32,7 | +2,7 % | +4,7 % | +1,64 / −1,06 |

## L. Gaps d'ouverture (séries en séances ; définitions fixées avant le calcul, en tête du script)

**Données et signaux** (sans PnL) :

| Actif | Séances | |Écart| bps : P50 ; P90 ; P99 | |Écart| ATR : P50 ; P90 ; > 1 ATR | Vrai range en ATR (P50) : ouverture ; autres | Part du vrai range à l'ouverture | Signaux : sur barre d'ouverture ; sur dernière barre | nis_z_100 P50 : ouverture ; autres | R2 écartés par nis : ouverture ; autres | Dividendes : ouvertures ajustées (écart moyen) |
|---|---|---|---|---|---|---|---|---|---|
| XAU | 2 101 | 3,3 ; 18,7 ; 71,6 | 0,18 ; 0,98 ; 10 % | 0,78 ; 0,86 | 3 % (3,0 % des barres) | 2,6 % ; 3,6 % | 0,18 ; 0,25 | 38 % ; 25 % | — |
| SPY | 1 507 | 33,1 ; 110,8 ; 327,1 | 1,18 ; 3,14 ; 57 % | 2,01 ; 0,79 | 17 % (7,7 % des barres) | 10,8 % ; 9,8 % | 1,40 ; 0,14 | 64 % ; 20 % | 24 (−36,4 bps ; bruit P99 0,3 bps) |
| XLE | 1 507 | 57,1 ; 195,4 ; 482,7 | 1,14 ; 3,07 ; 56 % | 2,85 ; 0,75 | 22 % (7,7 % des barres) | 11,8 % ; 14,6 % | 1,59 ; 0,13 | 74 % ; 16 % | 24 (−106,0 bps ; bruit P99 5,2 bps) ; fractionnement le 2025-12-05 (−6931 bps) |

**Trades de RE-1** (rendement brut en log, ATR14(t) ; frais de lecture principale pour l'espérance nette par barre de signal) :

| Actif | Écarts traversés par trade (P50) ; trades concernés | Brut (log) ATR [IC] | dont écarts d'ouverture [IC] | dont séance [IC] | Gagnants : écarts ; séance | Perdants : écarts ; séance |
|---|---|---|---|---|---|---|
| XAU 4 bps | 0 ; 38 % | +0,237 [−0,107 ; +0,605] | +0,027 [−0,026 ; +0,092] | +0,210 [−0,116 ; +0,555] | +0,14 ; +3,86 | −0,06 ; −2,49 |
| SPY 4 bps | 2 ; 92 % | +0,000 [−0,578 ; +0,589] | +0,027 [−0,332 ; +0,374] | −0,026 [−0,533 ; +0,475] | +1,26 ; +2,14 | −0,99 ; −1,81 |
| XLE 4 bps | 2 ; 90 % | +0,091 [−0,516 ; +0,749] | +0,192 [−0,254 ; +0,642] | −0,101 [−0,588 ; +0,426] | +1,62 ; +1,84 | −0,97 ; −1,68 |

| Actif | Stops exécutés en gap / stops | Dépassement du niveau (ATR) : moyenne ; P90 | Signal sur barre d'ouverture : n : espérance nette ATR [IC] | Signal sur dernière barre (entrée après l'écart) | Autres signaux |
|---|---|---|---|---|---|
| XAU 4 bps | 2 / 169 | +0,76 ; +1,29 | 7 : −1,700 [−3,614 ; −0,447] | 9 : −0,407 [−1,908 ; +1,423] | 635 : +0,005 [−0,340 ; +0,375] |
| SPY 4 bps | 8 / 46 | +2,57 ; +5,76 | 15 : −1,280 [−3,370 ; +0,605] | 17 : +0,072 [−1,432 ; +1,627] | 123 : −0,053 [−0,711 ; +0,677] |
| XLE 4 bps | 11 / 48 | +1,01 ; +3,25 | 11 : +0,432 [−1,034 ; +1,713] | 23 : −0,743 [−1,839 ; +0,546] | 102 : +0,147 [−0,634 ; +0,927] |

Figures : `figures/capital_D01.png`, `figures/nis_D01.png`, `figures/annees_D01.png`.
