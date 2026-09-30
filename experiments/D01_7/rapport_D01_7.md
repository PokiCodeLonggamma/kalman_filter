# EXP-D01.7 — Portabilité de RE-1 figée sur des marchés 24/5 (zero-shot) : GBPJPY mesuré, futures en attente

- **Date :** 2026-10-01. **Étape :** D, test de portabilité. **Descriptif** : RE-1 strictement gelée (H = 26, R0 = 100, frontière 0,85, P75 et médiane de `leg_atr` de BTC, cooldown, SL-B, F2b/F3), aucun réglage par actif, aucune modification de RE-1 sur la base de ces résultats.
- **État de cette version :**
  - GBPJPY mesuré, BTC en référence.
  - NQ, RTY, CL et HG bloqués avant téléchargement : l'accès aux données demande une action du porteur (§1.2).
- **Données :** 2020-2025 seulement, chaque série étant tronquée avant le 2026-01-01 au chargement. Rien de 2026 n'a été téléchargé.
- **Code :**
  - `experiments/D01_7/donnees_D01_7.py` (acquisition) ;
  - `experiments/D01_7/run_D01_7.py` (`--audit`, puis contrôles et mesures). Il réutilise la chaîne de D01 : `strategy.run_re1`, `prepare`, `diagnostics`.

## 0. Cadrage

- **QUESTION :** RE-1, verrouillée en C02bis sur BTC, conserve-t-elle son comportement sur des marchés traditionnels à cotation quasi continue 24/5 ?
- **PERTINENCE POUR LE FILTRE AKF :** D01 a montré que la géométrie des signaux se transpose, mais que la rente dépend de la structure du marché. Un marché 24/5 retire la nuit des ETF, mais garde le week-end, et, pour les futures, la pause de CME et les roulements.
- **CE QUE LE PROTOCOLE MESURE RÉELLEMENT :**
  - l'audit des données avant tout backtest ;
  - par actif, les 8 métriques en brut et nettes de coûts déclarés, l'espérance en ATR et en bps avec IC par grappes mensuelles, le capital à 0,25 %/ATR et à 1x ;
  - Long/Short, F2b/F3, volatilité, sessions, interruptions, concentration, queues.
- **CE QU'IL NE PERMET PAS DE CONCLURE :** pas de validation hors échantillon ; pas de classement statistique des actifs ; coûts réels non mesurés (swaps et financement absents) ; aucun réglage.

## 1. Données et contrôles (avant les résultats)

### 1.1 GBPJPY : source de repli déclarée, validée par recoupement

- **Dukascopy, demandé par le porteur, n'est pas accessible sans action de sa part.**
  - Le flux datafeed.dukascopy.com répond HTTP 429 dès la deuxième requête et renvoie à sa page d'export.
  - Cette page réserve l'historique en vrac à un bucket AWS « Requester Pays » (`cfg-public-proper-wallaby`, eu-west-1), avec des identifiants AWS obligatoires. Coût annoncé : environ 0,06 $ pour une paire majeure.
  - Aucun contournement.
- **Source retenue et déclarée : HistData.com.** Bougies d'une minute gratuites (bid), sans compte, agrégées en 30 min ; même chaîne que l'or de D01, horloge convertie en UTC.
- **Audit [OBS] :**
  - 73 055 barres, du 2020-01-01 22:00 au 2025-12-31 21:30 UTC ; aucun doublon, désordre, prix négatif ni OHLC incohérent ; couverture conforme ; plus long trou 72 h (Nouvel An).
  - **Structure hebdomadaire :** 288 reprises sur 314 le dimanche à 17:00 heure de New York, 299 fins de semaine le vendredi à 17:00, ce qui est la séance du marché des changes. Les autres reprises correspondent à des fêtes.
  - **Recoupement externe** avec les taux de midi de la Réserve fédérale (H.10, DEXUSUK × DEXJPUS) : sur 1 438 jours, la corrélation des variations quotidiennes vaut 0,9997 à 12:00 heure de New York. L'écart de niveau médian est de −1,2 bps (le bid est sous le milieu), l'écart absolu au P95 de 3,0 bps. Le meilleur décalage horaire est 0, avec un pic net : 0,978 et 0,984 à ± 30 min. **Horloge et prix sont validés** (critère fixé avant : ≥ 0,95).
  - **Défaut de données en 2023 :** 673 des 690 interruptions de 30 min à 24 h en semaine tombent en 2023, pour environ 1 758 barres manquantes, soit près de 14 % des barres de l'année. Les autres années en comptent 2 à 6.
    - Aucun seuil de densité de trous n'avait été fixé avant le calcul : l'actif n'est pas bloqué après coup.
    - 2023 est présentée à part dans les résultats (§2).
- **Ce que ce n'est pas :** Dukascopy aurait donné des ticks avec le bid et l'ask, donc un écart mesuré et une année 2023 sans trous.

### 1.2 Futures NQ, RTY, CL, HG : bloqués, action du porteur requise

- **QuantConnect exige un compte et une connexion.**
- Ses données ne sont utilisables que dans son cloud (Research, backtests). Sa documentation de licence est claire :
  - l'Object Store accepte les envois mais pas les téléchargements, « as it would be an easy way to export data » ;
  - le téléchargement local demande une licence payante : US Futures Security Master (600 $ par an au premier palier) plus 0,50 $ par fichier (ticker, jour, format) en minute. Il est réservé à LEAN : « cannot be redistributed or converted in any format ».
- **Conséquence : les barres de QuantConnect ne peuvent pas entrer dans notre chaîne locale.** L'audit, la parité du moteur et les contrôles de look-ahead s'y font en local.
- **Aucune série n'a été téléchargée et aucun backtest n'a été lancé.** Les options sont données au porteur dans le compte rendu.

### 1.3 Contrôles bloquants

- Ancre P6.5d reproduite ; RE-1 de la chaîne = C02bis (1 080 trades, 40 métriques, écart ≤ 5·10⁻⁶) ; seuils BTC gelés.
- **Invariance d'échelle** (prérequis des futures rétro-ajustés : le facteur commun d'une fenêtre dépend des roulements postérieurs) :
  - BTC multiplié par 0,37 et par 2,9 : signaux identiques ;
  - descripteurs identiques à 3·10⁻⁵ près en relatif (`nis_z_100` ; médiane 10⁻¹⁰), soit la précision machine ;
  - seuls basculent 1 et 4 signaux dont le `retrace_ratio` vaut exactement 0,50, la borne de F2b (passage en F5) ;
  - RE-1 à ×2,9 : 1 trade de moins sur 1 080, espérance +0,3686 → +0,3676 ATR.
  - **Le rétro-ajustement par ratio n'apporterait donc aucune information future**, hormis ces égalités au seuil.

## 2. Résultats [OBS]

**Coûts aller-retour (hypothèses fixées avant) :** BTC 0, 5 et 10 bps. GBPJPY 0 (brut), 2 bps (écart ECN d'environ 1,5 à 2 pips plus commission ; la série est un bid, le coût couvre l'écart entier) et 4 bps (lecture principale, convention de D01 pour les CFD).

| Métrique | BTC 5 bps (réf.) | GBPJPY brut | GBPJPY 2 bps | GBPJPY 4 bps |
|---|---|---|---|---|
| Trades (par mois) | 1 080 (15,0) | 687 (9,5) | 687 (9,5) | 687 (9,5) |
| **Espérance ATR [IC]** | +0,369 [+0,098 ; +0,645] | −0,035 [−0,284 ; +0,221] | −0,239 [−0,490 ; +0,018] | **−0,443 [−0,697 ; −0,180]** |
| Espérance bps [IC] | +12,3 [+0,2 ; +24,4] | −0,6 [−3,7 ; +2,5] | −2,6 [−5,7 ; +0,5] | −4,6 [−7,7 ; −1,5] |
| Frais en ATR par trade | 0,14 | 0 | 0,20 | 0,41 |
| WR ; PF (1x) | 44,3 % ; 1,20 | 42,1 % ; 0,96 | 40,5 % ; 0,84 | 38,0 % ; 0,74 |
| PnL 0,25 %/ATR ; 1x | +138 % ; +204 % | −4 % ; −5 % | −16 % ; −17 % | −27 % ; −27 % |
| MDD 0,25 %/ATR ; 1x | −13,5 % ; −43,9 % | −8,7 % ; −8,8 % | −16,8 % ; −17,5 % | −27,2 % ; −27,9 % |
| Calmar 0,25 %/ATR ; 1x | 1,16 ; 0,46 | −0,07 ; −0,09 | −0,17 ; −0,17 | −0,19 ; −0,19 |
| Long ; Short (ATR) | +0,457 ; +0,266 | −0,014 ; −0,058 | −0,218 ; −0,262 | −0,422 ; −0,467 |
| F2b ; F3 (ATR) | +0,459 ; +0,267 | −0,129 ; +0,066 | −0,338 ; −0,134 | −0,546 ; −0,333 |
| Années à espérance > 0 | 6/6 | 3/6 | 1/6 | 0/6 |

- **Le brut est nul sur GBPJPY** : −0,035 ATR, IC ±0,25, contre +0,504 sur BTC. Ce ne sont pas les frais qui effacent un avantage : il n'y en a pas avant frais.
- **Les frais pèsent lourd.** L'ATR de 30 min de GBPJPY vaut 10 à 11 bps (P50 11,1 ; BTC 35 à 55). À 4 bps, les frais coûtent 0,41 ATR par trade, plus que sur l'or en D01 (0,26).
- **Le dimensionnement à 0,25 %/ATR est dégénéré sur GBPJPY.** Il demanderait environ 2,3 fois de levier ; le plafond de 1x mord sur 98 % des trades. Les colonnes « 0,25 %/ATR » valent donc le 1x (risque réel ≈ 0,11 % par ATR).
- **Pas de dérive, sens symétriques** : dérive +0,02 ATR, Long et Short proches en brut.
- **Années :** à 4 bps, toutes les années sont négatives (−0,17 à −0,72 ATR). En brut, 2022, 2023 et 2024 sont positives (+0,15, +0,09, +0,21), les autres négatives. **2023, l'année trouée, n'est pas un cas à part** (−0,30 à 4 bps).
- **Interruptions** (week-ends, fêtes, trous) : 9,5 % des trades en traversent une (6 % durent plus de 24 h). La composante des écarts de reprise vaut +0,013 ATR ; 5 stops percés sur 189 (+0,99 ATR). Elles ne pèsent pas.
- **Sessions** (heure de New York du signal) : 53 % des signaux tombent en session asiatique (17:00-02:00), la plus calme.
  - Asie −0,50 [−0,90 ; −0,10] ; Londres −0,60 [−1,13 ; −0,02] ; Londres-New York −0,42 ; New York après-midi −0,01 [−0,64 ; +0,74], à 4 bps.
  - Sur BTC, les quatre sessions sont positives.
- **Volatilité** (terciles d'ATR14(t), médianes 7,6, 10,0 et 14,0 bps) :
  - net à 4 bps : calme −0,46, milieu −0,64, agité −0,23 ;
  - brut +0,10, −0,24 et +0,04 : pas de régime porteur ;
  - frais 0,55, 0,40 et 0,27 ATR.
- **Concentration et queues :** médiane −1,42 ATR, P5 −5,5, P95 +6,1. Le décile supérieur apporte +0,75 ATR par trade ; sans lui, −1,32. Même profil de queue droite que BTC (médiane −0,42), sans la moyenne positive.
- **Stops de F3 :** 57 % des F3 sont stoppés (BTC 51 %) ; effet apparié du stop +0,20 [−0,12 ; +0,54] ATR.
- **Signaux :**
  - La médiane locale de `leg_atr` vaut 2,86 (BTC 2,82) : la géométrie se transpose.
  - Le P75 local de `nis_z_100` vaut 1,40 (BTC 1,22) : 28 % des signaux dépassent le seuil BTC.
  - Univers de RE-1 : 867 candidats pour 4 959 signaux.

## 3. Lecture

- [HYP] Sur GBPJPY à 30 min, RE-1 ne capte pas de mouvement exploitable. Le brut est nul dans les deux sens, à toutes les sessions et dans tous les régimes de volatilité. C'est une différence de nature avec BTC, pas seulement de coût.
- [HYP] Même avec un brut du niveau de SOL (+0,25 ATR), une paire de change calme ne couvrirait pas 4 bps à cette échelle de temps : le rapport frais / ATR (0,41) est structurellement défavorable pour une tenue de 13 h.
- [PISTE] Futures NQ, RTY, CL, HG, selon l'accès choisi par le porteur (compte rendu).
- [PISTE] Dukascopy (ticks bid et ask, via AWS) pour mesurer l'écart réel de GBPJPY et disposer d'un 2023 complet. Utile seulement si le porteur veut confirmer un résultat déjà net en brut.
- [PISTE] Pour les actifs calmes, une unité de temps plus longue changerait le rapport frais / ATR. Ce n'est plus du zero-shot, donc hors D01.7.

## Annexes générées (run_D01_7.py)

### A. Audit des données (avant tout backtest)

**BTC — BTC/USD (Bitstamp, référence RE-1)**

| Contrôle | Mesure |
|---|---|
| Source ; instrument | bitstamp ; BTC/USD, carnet spot de Bitstamp (TradingView : BITSTAMP:BTCUSD) |
| Fuseau ; prix | UTC ; — |
| Barres ; première ; dernière | 105 216 ; 2020-01-01 00:00 ; 2025-12-31 23:30 |
| Intégrité (doublons, désordre, prix, OHLC) | aucun défaut |
| Couverture 2020-2025 | conforme |
| Trous (n ; barres manquantes) : ≤ 2 h ; ≤ 3 jours ; > 3 jours | 0 (0) ; 0 (0) ; 0 (0) |
| Plus longs trous |  |
| Barres plates ; SHA-256 | 40 ; 4a70ac3c9f999af0… |

**GBPJPY — GBP/JPY au comptant (HistData, bid)**

| Contrôle | Mesure |
|---|---|
| Source ; instrument | histdata.com ; GBP/JPY au comptant (TradingView : FX:GBPJPY, OANDA:GBPJPY) |
| Fuseau ; prix | étiquettes HistData converties en UTC : la FAQ annonce un EST fixe, mais l'horloge suit l'heure d'été européenne (serveur EET/EEST moins 7 h ; bid (FAQ HistData : barres construites sur le bid des ticks) |
| Barres ; première ; dernière | 73 055 ; 2020-01-01 22:00 ; 2025-12-31 21:30 |
| Intégrité (doublons, désordre, prix, OHLC) | aucun défaut |
| Couverture 2020-2025 | conforme |
| Trous (n ; barres manquantes) : ≤ 2 h ; ≤ 3 jours ; > 3 jours | 678 (1 542) ; 326 (30 571) ; 0 (0) |
| Plus longs trous | 72 h après 2020-12-31 21:30 ; 72 h après 2023-12-29 21:30 ; 70 h après 2023-04-06 23:30 |
| Barres plates ; SHA-256 | 2 ; f0cb7f99566f31d9… |
| Reprises après plus de 24 h ; ouverture (New York) | 314 ; dim 17:00 : 288, dim 18:00 : 14, dim 17:30 : 4, dim 19:00 : 3, dim 18:30 : 1, dim 19:30 : 1 |
| Fin de semaine (New York) | ven 17:00 : 299, ven 16:00 : 8, ven 15:00 : 2, ven 02:30 : 1, jeu 17:00 : 1, jeu 20:00 : 1 |
| Interruptions de 30 min à 24 h en semaine ; barres manquantes ; par année | 690 ; 1 758 ; 2020 : 2, 2021 : 2, 2022 : 3, 2023 : 673, 2024 : 4, 2025 : 6 |
| Recoupement H.10 (12:00 New York) | 1438 jours ; corrélation des variations 0,9997 ; écart médian −1,2 bps (absolu 1,3, P95 3,0) ; meilleur décalage 0 demi-heure ; valide |

**NQ — E-mini Nasdaq-100, future continu : bloqué.** en attente du porteur : QuantConnect exige un compte, et ses données ne sont utilisables que dans son cloud (aucun export ; Object Store sans téléchargement ; téléchargement local sous licence payante, réservé à LEAN et non convertible) ; aucune série téléchargée, aucun backtest.

**RTY — E-mini Russell 2000, future continu : bloqué.** en attente du porteur : QuantConnect exige un compte, et ses données ne sont utilisables que dans son cloud (aucun export ; Object Store sans téléchargement ; téléchargement local sous licence payante, réservé à LEAN et non convertible) ; aucune série téléchargée, aucun backtest.

**CL — WTI Crude Oil, future continu : bloqué.** en attente du porteur : QuantConnect exige un compte, et ses données ne sont utilisables que dans son cloud (aucun export ; Object Store sans téléchargement ; téléchargement local sous licence payante, réservé à LEAN et non convertible) ; aucune série téléchargée, aucun backtest.

**HG — Copper, future continu : bloqué.** en attente du porteur : QuantConnect exige un compte, et ses données ne sont utilisables que dans son cloud (aucun export ; Object Store sans téléchargement ; téléchargement local sous licence payante, réservé à LEAN et non convertible) ; aucune série téléchargée, aucun backtest.

### B. Contrôles bloquants

- Ancre P6.5d reproduite ; RE-1 de la chaîne D01 = RE-1 de C02bis (1080 trades, 40 métriques, écart relatif max 4.5e-06).
- Seuils de population gelés à leur valeur BTC (médiane de `leg_atr`, P75 de `nis_z_100`) ; RE-1 inchangée.
- Réserve 2026 : chaque série est tronquée avant le 2026-01-01 au chargement ; rien de 2026 n'a été téléchargé.
- Invariance d'échelle (prérequis des futures rétro-ajustés), BTC × 0.37 : signaux identiques ; descripteurs à 3.0e-05 près en relatif (le plus sensible : `nis_z_100`) ; 1 signaux changent de famille (F2b → F5 (retrace_ratio 0.500000000000)) ; RE-1 : 1080 trades communs, 0 seulement sur l'original, 0 seulement sur la série multipliée ; espérance à 5 bps +0,3686 → +0,3686 ATR.
- Invariance d'échelle (prérequis des futures rétro-ajustés), BTC × 2.9 : signaux identiques ; descripteurs à 2.5e-05 près en relatif (le plus sensible : `nis_z_100`) ; 4 signaux changent de famille (F2b → F5 (retrace_ratio 0.500000000000); F2b → F5 (retrace_ratio 0.500000000000); F2b → F5 (retrace_ratio 0.500000000000); F2b → F5 (retrace_ratio 0.500000000000)) ; RE-1 : 1079 trades communs, 1 seulement sur l'original, 0 seulement sur la série multipliée ; espérance à 5 bps +0,3686 → +0,3676 ATR.
- BTC : mesuré (1080 trades, 1452 candidats, 6,00 ans).
- GBPJPY : mesuré (687 trades, 867 candidats, 6,00 ans).
- NQ : bloqué — en attente du porteur : QuantConnect exige un compte, et ses données ne sont utilisables que dans son cloud (aucun export ; Object Store sans téléchargement ; téléchargement local sous licence payante, réservé à LEAN et non convertible) ; aucune série téléchargée, aucun backtest.
- RTY : bloqué — en attente du porteur : QuantConnect exige un compte, et ses données ne sont utilisables que dans son cloud (aucun export ; Object Store sans téléchargement ; téléchargement local sous licence payante, réservé à LEAN et non convertible) ; aucune série téléchargée, aucun backtest.
- CL : bloqué — en attente du porteur : QuantConnect exige un compte, et ses données ne sont utilisables que dans son cloud (aucun export ; Object Store sans téléchargement ; téléchargement local sous licence payante, réservé à LEAN et non convertible) ; aucune série téléchargée, aucun backtest.
- HG : bloqué — en attente du porteur : QuantConnect exige un compte, et ses données ne sont utilisables que dans son cloud (aucun export ; Object Store sans téléchargement ; téléchargement local sous licence payante, réservé à LEAN et non convertible) ; aucune série téléchargée, aucun backtest.

### C. Résultats nets (8 métriques ; brut = 0 bps)

| Actif, frais | PnL net : 0,25 %/ATR ; 1x ; bps cumulés (1x) | PF : 1x ; pondéré | WR | Espérance : bps [IC] ; ATR [IC] | MDD valorisé : 0,25 %/ATR ; 1x | Trades (par mois) ; stoppés | Durée médiane : barres ; calendaire | Part des frais : 1x ; pondérée |
|---|---|---|---|---|---|---|---|---|
| BTC 0 bps | +229 % ; +421 % ; +18720 | 1,29 ; 1,40 | 45,7 % | +17,3 [+5,2 ; +29,4] ; +0,504 [+0,235 ; +0,777] | −11,6 % ; −39,6 % | 1 080 (15,0) ; 24 % | 26 ; 13,0 h | 0 % ; 0 % |
| BTC 5 bps | +138 % ; +204 % ; +13320 | 1,20 ; 1,28 | 44,3 % | +12,3 [+0,2 ; +24,4] ; +0,369 [+0,098 ; +0,645] | −13,5 % ; −43,9 % | 1 080 (15,0) ; 24 % | 26 ; 13,0 h | 29 % ; 26 % |
| BTC 10 bps | +72 % ; +77 % ; +7920 | 1,11 ; 1,17 | 42,8 % | +7,3 [−4,8 ; +19,4] ; +0,233 [−0,041 ; +0,511] | −15,9 % ; −48,0 % | 1 080 (15,0) ; 24 % | 26 ; 13,0 h | 58 % ; 52 % |
| GBPJPY 0 bps | −4 % ; −5 % ; −406 | 0,96 ; 0,97 | 42,1 % | −0,6 [−3,7 ; +2,5] ; −0,035 [−0,284 ; +0,221] | −8,7 % ; −8,8 % | 687 (9,5) ; 28 % | 26 ; 13,0 h | brut ≤ 0 ; brut ≤ 0 |
| GBPJPY 2 bps | −16 % ; −17 % ; −1780 | 0,84 ; 0,85 | 40,5 % | −2,6 [−5,7 ; +0,5] ; −0,239 [−0,490 ; +0,018] | −16,8 % ; −17,5 % | 687 (9,5) ; 28 % | 26 ; 13,0 h | brut ≤ 0 ; brut ≤ 0 |
| GBPJPY 4 bps | −27 % ; −27 % ; −3154 | 0,74 ; 0,75 | 38,0 % | −4,6 [−7,7 ; −1,5] ; −0,443 [−0,697 ; −0,180] | −27,2 % ; −27,9 % | 687 (9,5) ; 28 % | 26 ; 13,0 h | brut ≤ 0 ; brut ≤ 0 |

| Actif, frais | Années | 0,25 %/ATR : CAGR ; Calmar | 1x : CAGR ; Calmar | Exposition moyenne ; trades plafonnés à 1x | Long / Short (ATR) | Timing ATR [IC] | Timing bps [IC] | F2b : n ; ATR | F3 : n ; ATR |
|---|---|---|---|---|---|---|---|---|---|
| BTC 0 bps | 6,00 | +22,0 % ; 1,89 | +31,6 % ; 0,80 | 60 % ; 16 % | +0,593 / +0,402 | +0,497 [+0,228 ; +0,766] | +17,3 [+5,2 ; +29,5] | 573 ; +0,592 | 507 ; +0,406 |
| BTC 5 bps | 6,00 | +15,6 % ; 1,16 | +20,3 % ; 0,46 | 60 % ; 16 % | +0,457 / +0,266 | +0,362 [+0,089 ; +0,638] | +12,3 [+0,2 ; +24,5] | 573 ; +0,459 | 507 ; +0,267 |
| BTC 10 bps | 6,00 | +9,5 % ; 0,60 | +10,0 % ; 0,21 | 60 % ; 16 % | +0,320 / +0,131 | +0,226 [−0,050 ; +0,507] | +7,3 [−4,8 ; +19,5] | 573 ; +0,326 | 507 ; +0,127 |
| GBPJPY 0 bps | 6,00 | −0,6 % ; −0,07 | −0,8 % ; −0,09 | 100 % ; 98 % | −0,014 / −0,058 | −0,036 [−0,290 ; +0,223] | −0,6 [−3,8 ; +2,5] | 356 ; −0,129 | 331 ; +0,066 |
| GBPJPY 2 bps | 6,00 | −2,9 % ; −0,17 | −3,0 % ; −0,17 | 100 % ; 98 % | −0,218 / −0,262 | −0,240 [−0,494 ; +0,023] | −2,6 [−5,8 ; +0,5] | 356 ; −0,338 | 331 ; −0,134 |
| GBPJPY 4 bps | 6,00 | −5,1 % ; −0,19 | −5,2 % ; −0,19 | 100 % ; 98 % | −0,422 / −0,467 | −0,444 [−0,700 ; −0,180] | −4,6 [−7,8 ; −1,5] | 356 ; −0,546 | 331 ; −0,333 |

### D. Analyses (frais principaux de chaque actif)

**BTC (5 bps)**

| Famille | Sens | n | Espérance ATR [IC] | bps |
|---|---|---|---|---|
| F2b | Long | 290 | +0,617 [+0,140 ; +1,096] | +15,9 |
| F2b | Short | 283 | +0,296 [−0,206 ; +0,796] | +7,6 |
| F2b | tous | 573 | +0,459 [+0,106 ; +0,801] | +11,8 |
| F3 | Long | 290 | +0,296 [−0,108 ; +0,740] | +9,3 |
| F3 | Short | 217 | +0,227 [−0,210 ; +0,715] | +17,8 |
| F3 | tous | 507 | +0,267 [−0,063 ; +0,620] | +12,9 |
| tous | Long | 580 | +0,457 [+0,106 ; +0,807] | +12,6 |
| tous | Short | 500 | +0,266 [−0,094 ; +0,636] | +12,0 |
| tous | tous | 1080 | +0,369 [+0,098 ; +0,645] | +12,3 |

| Tercile d'ATR14(t) | ATR (bps) | n | Espérance ATR [IC] | WR | Stoppés |
|---|---|---|---|---|---|
| T1 calme | 5-35 | 360 | +0,517 [−0,062 ; +1,170] | 43,3 % | 26 % |
| T2 | 35-55 | 360 | +0,525 [+0,129 ; +0,935] | 45,3 % | 25 % |
| T3 agité | 56-260 | 360 | +0,064 [−0,272 ; +0,392] | 44,2 % | 20 % |

| Session du signal (New York) | n | Part | Espérance ATR [IC] | WR |
|---|---|---|---|---|
| Asie 17:00-02:00 | 415 | 38 % | +0,424 [+0,049 ; +0,836] | 44,8 % |
| Londres 02:00-08:00 | 329 | 30 % | +0,181 [−0,327 ; +0,686] | 41,9 % |
| Londres-New York 08:00-12:00 | 171 | 16 % | +0,453 [−0,196 ; +1,208] | 46,2 % |
| New York 12:00-17:00 | 165 | 15 % | +0,516 [−0,143 ; +1,267] | 45,5 % |

| Interruptions (week-end, fêtes, trous) | Mesure |
|---|---|
| Reprises ; écart de reprise absolu P50 / P90 (ATR) | 0 ; — / — |
| Trades exposés | 0,0 % |
| Net exposés ; non exposés (ATR) | — [— ; —] ; +0,369 [+0,098 ; +0,645] |
| Brut log = écarts + reste (ATR) | +0,503 = +0,000 + +0,503 |
| Stops en gap / stops ; dépassement moyen | 0/257 ; — ATR |

| Concentration et queues (ATR par trade) | Mesure |
|---|---|
| Moyenne ; médiane ; moyenne winsorisée P1-P99 | +0,369 ; −0,423 ; +0,379 |
| Apport des 5 meilleurs ; espérance sans eux | +0,100 ; +0,270 |
| Apport du décile supérieur ; espérance sans lui | +0,919 ; −0,612 |
| Apport du décile inférieur | −0,537 |
| Quantiles P5 ; P10 ; P50 ; P90 ; P95 | −4,43 ; −2,83 ; −0,42 ; +5,53 ; +8,44 |

- Stops de F3 : 257/507 ; effet apparié du stop sur F3 +0,031 [−0,230 ; +0,305] ATR ; sans stop : MDD −20,5 % (0,25 %/ATR).
- Bandes de `nis_z_100` (signaux R2 isolés, bornes BTC) : ≤ P70 : 1358, +0,166 ; P70–P75 : 94, +0,529 ; P75–P80 : 87, −0,300 ; P80–P85 : 82, −0,744 ; P85–P90 : 84, +0,223 ; > P90 : 169, −0,405.
- Durée calendaire : médiane 13,0 h, P90 13,0 h, plus de 24 h : 0 %.

**GBPJPY (4 bps)**

| Famille | Sens | n | Espérance ATR [IC] | bps |
|---|---|---|---|---|
| F2b | Long | 168 | −0,357 [−0,966 ; +0,265] | −1,9 |
| F2b | Short | 188 | −0,715 [−1,280 ; −0,143] | −7,5 |
| F2b | tous | 356 | −0,546 [−0,966 ; −0,112] | −4,8 |
| F3 | Long | 189 | −0,479 [−0,914 ; −0,005] | −4,7 |
| F3 | Short | 142 | −0,138 [−0,734 ; +0,502] | −3,8 |
| F3 | tous | 331 | −0,333 [−0,629 ; −0,016] | −4,3 |
| tous | Long | 357 | −0,422 [−0,765 ; −0,066] | −3,4 |
| tous | Short | 330 | −0,467 [−0,886 ; −0,009] | −5,9 |
| tous | tous | 687 | −0,443 [−0,697 ; −0,180] | −4,6 |

| Tercile d'ATR14(t) | ATR (bps) | n | Espérance ATR [IC] | WR | Stoppés |
|---|---|---|---|---|---|
| T1 calme | 5-9 | 229 | −0,456 [−0,944 ; +0,042] | 35,8 % | 29 % |
| T2 | 9-12 | 229 | −0,642 [−1,133 ; −0,147] | 38,9 % | 25 % |
| T3 agité | 12-40 | 229 | −0,233 [−0,570 ; +0,096] | 39,3 % | 28 % |

| Session du signal (New York) | n | Part | Espérance ATR [IC] | WR |
|---|---|---|---|---|
| Asie 17:00-02:00 | 365 | 53 % | −0,500 [−0,903 ; −0,096] | 37,0 % |
| Londres 02:00-08:00 | 159 | 23 % | −0,603 [−1,129 ; −0,021] | 35,8 % |
| Londres-New York 08:00-12:00 | 60 | 9 % | −0,422 [−0,980 ; +0,135] | 41,7 % |
| New York 12:00-17:00 | 103 | 15 % | −0,008 [−0,641 ; +0,742] | 42,7 % |

| Interruptions (week-end, fêtes, trous) | Mesure |
|---|---|
| Reprises ; écart de reprise absolu P50 / P90 (ATR) | 1004 ; 0,57 / 1,81 |
| Trades exposés | 9,5 % |
| Net exposés ; non exposés (ATR) | −0,497 [−1,560 ; +0,686] ; −0,438 [−0,693 ; −0,186] |
| Brut log = écarts + reste (ATR) | −0,034 = +0,013 + −0,047 |
| Stops en gap / stops ; dépassement moyen | 5/189 ; +0,99 ATR |

| Concentration et queues (ATR par trade) | Mesure |
|---|---|
| Moyenne ; médiane ; moyenne winsorisée P1-P99 | −0,443 ; −1,418 ; −0,458 |
| Apport des 5 meilleurs ; espérance sans eux | +0,124 ; −0,572 |
| Apport du décile supérieur ; espérance sans lui | +0,748 ; −1,325 |
| Apport du décile inférieur | −0,620 |
| Quantiles P5 ; P10 ; P50 ; P90 ; P95 | −5,52 ; −3,73 ; −1,42 ; +4,15 ; +6,12 |

- Stops de F3 : 189/331 ; effet apparié du stop sur F3 +0,200 [−0,118 ; +0,544] ATR ; sans stop : MDD −32,2 % (0,25 %/ATR).
- Bandes de `nis_z_100` (signaux R2 isolés, bornes BTC) : ≤ P70 : 790, −0,381 ; P70–P75 : 77, −0,665 ; P75–P80 : 87, +0,049 ; P80–P85 : 60, −0,957 ; P85–P90 : 56, −0,732 ; > P90 : 130, −0,456.
- Durée calendaire : médiane 13,0 h, P90 13,0 h, plus de 24 h : 6 %.

### E. Figure

![Capital et sessions](figures/D01_7.png)
