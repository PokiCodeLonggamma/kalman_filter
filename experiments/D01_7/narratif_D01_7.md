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
