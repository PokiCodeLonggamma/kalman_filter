# RE-1 — Livre blanc « Fonds propres »

*Cahier des charges du bot d'exécution de RE-1 version finale (VF). Rédigé le 2026-10-05, à la décision du porteur qui
clôt la branche « Fonds propres » du projet. Aucun calcul nouveau : chaque chiffre vient des rapports D02.1, D03.1,
D04, D04.1 et D04.2 (sources en §7). État du dépôt : `5650153`.*

Balises : `[CODE]` programmé et vérifiable dans le dépôt ; `[OBS]` mesuré sur données réelles ; `[HYP]` hypothèse ou
lecture.

## 0. En bref

- **Mécanique.** Le signal est un retournement après une jambe de tendance courte de l'oscillateur AKF-TSO v2.1
  (Kalman sur barres de 30 min). Il est confirmé à la clôture : vitesse du Kalman déjà retournée, jambe retracée d'au
  moins 50 %, pas de choc d'innovation. Entrée à l'ouverture suivante, tenue de 26 barres (13 h), une position par actif.
  Les trades F3 ont un stop à l'extremum du segment ; tous les trades ont un stop catastrophe à 4 ATR14.
- **Portefeuille.** BTC, ETH, SOL, AVAX, XRP et or (XAU) sur un capital commun. Taille : r % du capital par ATR14,
  plafonnée à 1x par position.
- **Profil.** WR 42 % ; le trade médian perd ; l'avantage tient à environ 1 % des trades. À 0,25 %/ATR sur
  2021-10 → 2026-09 : +584 %, MDD −37,4 %, pire journée −5,20 %. Hors 2026, ≈ +20 % par an pour le même MDD.
- **Taille.** La pire journée vaut environ 21 × r (§3).
- **Exécution.** Une barre de retard ne coûte rien ; le glissement des stops peut annuler l'avantage (§4).

## 1. Spécification du moteur (RE-1 VF) — `[CODE]`

Le code du dépôt est la référence. En cas d'écart entre ce texte et le code, le code fait foi :
- indicateur : `src/indicator/`, réplique Python certifiée du baseline gelé `pine/baseline/AKF_TSO_v2.1_baseline.pine` ;
- variables connues à t : `src/anatomy/causal.py`, `src/categorization/families.py`, `src/features/` ;
- univers et stops : `src/optimization/universe.py` (`candidates`), `src/envelope/stops.py`, `src/envelope/stress.py` ;
- version finale : `src/strategy/final.py` (`run_final`) ; exécution : `src/optimization/engine.py` (`run_trades`) ;
- taille et capital commun : `src/envelope/metrics.py` (`risk_weights`), `src/envelope/portfolio.py`.

### 1.1 Données

- **Barres :** OHLC de 30 min, horodatées en UTC à l'ouverture et clôturées. Une série par actif et par flux, triée,
  sans doublon.
- **Barres telles que servies :** aucun trou n'est comblé et aucune barre n'est fabriquée. H et le verrou se comptent en
  barres de la série, pas en temps : une barre absente n'est pas comptée, et le week-end de l'or n'existe pas dans la
  série.
- **Warm-up :** aucun signal avant la 300e barre de 30 min et la 300e bougie d'une heure entièrement clôturée (bougies
  ancrées sur l'heure UTC). Sur un actif coté 24 h sur 24, cela fait 600 barres.
- **Origine :** le Kalman et l'ATR démarrent à la première barre de l'historique (X = [close₀, 0], P = I). Pour la
  parité avec les tests, le bot recalcule depuis la même origine que les séries de référence (§1.8), puis avance barre
  par barre.

### 1.2 Filtre de Kalman (AKF-TSO v2.1, réglages par défaut)

| Élément | Valeur |
|---|---|
| État et mesure | X = [x0 niveau, x1 vitesse par barre] ; F = [[1, 1], [0, 1]] ; H = [1, 0] ; mesure = close de la barre |
| Bruit de processus | Q = [[q1, q1·q2], [q2·q1, q2]] · Q_scale ; q1 = q2 = 0,01 ; Q_scale = 1 |
| Bruit de mesure | R_t = R0 · (σ20,t / SMA100(σ20)_t)^γ ; **R0 = 100** ; γ = 0,5. σ20 est l'écart-type population (ddof 0) du close sur 20 barres. R = R0 tant que la SMA100 n'existe pas |
| Écarts au Kalman standard (reproduits) | diagonale de P remise à 1 avant chaque prédiction ; mise à jour de P sous forme de Joseph |
| Innovation | ν_t = close_t − x0 prédit ; S_t = P̂00 + R_t ; NIS_t = ν_t² / S_t |

### 1.3 Oscillateur et signal natif

- **Oscillateur :**
  - A_t = max |x1| sur les 5 dernières barres (N2 = 5, barre courante incluse ; A = 1 si A ≤ 1e−10) ;
  - ratio_t = 100 · x1_t / A_t ;
  - ts_t = moyenne pondérée sur 3 barres du ratio, poids 1, 2, 3 (R2 = 3).
- **Zones :** +1 si ts > 30, −1 si ts < −30, 0 sinon (inégalités strictes). Un segment est une suite de barres de même
  zone.
- **Signal :** il tient sur une seule barre, la première barre neutre (zone 0, longueur 1) après un segment de zone −1
  (Long) ou +1 (Short). Ce segment doit compter au moins 6 barres, avec un extrême |ts| ≥ 60.
- **Candidats :** tous les signaux bruts valides le sont, répétitions de même sens comprises. L'exécution
  « stop-and-reverse » du Pine n'est pas utilisée.

### 1.4 Variables de sélection, connues à la clôture de t

Notations : d = sens (+1 Long, −1 Short). L = `prev_seg_len`, longueur du segment de tendance qui vient de finir,
c'est-à-dire les barres [t − L, t − 1].

| Variable | Définition |
|---|---|
| ATR14(t) | ATR de Wilder (`ta.atr(14)` du Pine). TR = max(high − low, \|high − close₋₁\|, \|low − close₋₁\|) ; amorce = moyenne des 14 premiers TR ; ensuite ATR_t = (13 · ATR_{t−1} + TR_t) / 14. ATR_bps(t) = ATR14(t) / close_t · 10⁴ |
| `leg_atr` | (plus haut des high − plus bas des low sur [t − L, t − 1]) / ATR14(t) |
| extremum du segment | plus bas des low (Long) ou plus haut des high (Short) sur [t − L, t], première occurrence |
| `retrace_ratio` | (\|close_t − extremum\| / ATR14(t)) / `leg_atr` |
| x1 déjà retourné | d · x1_t > 0 |
| `nis_z_100` | z-score du NIS sur [t − 99, t] (moyenne et écart-type ddof 0) |

### 1.5 Univers de RE-1 : seuils statiques

Un signal est candidat si les quatre conditions tiennent :
1. `leg_atr` < **2,823322693433984** (médiane de BTC) ;
2. `retrace_ratio` ≥ **0,50** ;
3. x1 déjà retourné ;
4. `nis_z_100` ≤ **1,2245041356145911** (P75 linéaire de BTC ; un NaN exclut le signal).

- **Origine des seuils :** l'atlas BTC/USD 30 min 2020-2025 (7 296 signaux). Ils sont gelés à la précision machine et
  comparés en float64 exact.
- **Jamais recalculés,** ni par actif ni dans le temps. `[OBS]` Le recalibrage glissant n'a apporté aucune valeur :
  8 écarts significativement négatifs et 1 positif sur 92 (D02) ; WFO abandonné en D02.1.
- **Routage, connu à t :** **F2b** si 0,50 ≤ `retrace_ratio` < 0,85 ; **F3** si `retrace_ratio` ≥ **0,85**
  (frontière).

### 1.6 Exécution d'un trade

| Élément | Règle |
|---|---|
| Entrée | ouverture de la barre t + 1, au prix P0 = open[t + 1], dans le sens d |
| Sortie à horizon | ouverture de t + 27 : **H = 26** barres détenues, soit 13 h |
| Verrou (cooldown) **26** | après un signal exécuté en t, tout signal antérieur à t + 26 est ignoré, que le stop ait été touché ou non. D'où une seule position par actif, et un actif reste à plat après un stop jusqu'à t + 27 |
| Stop catastrophe (tous les trades) | P0 − d · **4** · ATR14(t) |
| Stop SL-B (F3 seulement) | extremum du segment (δ = 0), jamais à moins de 0,25 · ATR14(t) de P0. Long : min(extremum, P0 − 0,25 · ATR) ; Short : max(extremum, P0 + 0,25 · ATR) |
| Stop effectif | F2b : stop catastrophe seul. F3 : le plus proche de P0 entre SL-B et le stop catastrophe |
| Surveillance | high et low des barres t + 1 à t + 26, barre d'entrée comprise. Sortie au niveau ; si une barre autre que celle de l'entrée ouvre au-delà du niveau (gap), sortie à son ouverture |
| Niveaux | fixés à l'entrée et jamais déplacés : ni break-even, ni trailing, ni take-profit |
| Même instant | les trades qui sortent sont clos avant que les nouveaux entrent |

`[OBS]` En D03.1, le stop catastrophe n'a touché que des F2b (284 sur BTC, 98 sur SOL). Pour F3, SL-B est en pratique
toujours le plus proche.

### 1.7 Taille et capital

- **Poids d'un trade :** w = min(1, r / ATR_bps(t)), où r est le risque par ATR en bps du capital (25 bps = 0,25 %). Un
  mouvement d'un ATR14(t) vaut r du capital, sauf quand le plafond de 1x s'applique, ce qui est presque toujours le cas
  de l'or.
- **Notionnel :** w × capital valorisé à l'instant de l'entrée, c'est-à-dire le capital réalisé plus la valeur latente
  des autres positions à leur dernière clôture.
- **Frais :** déduits du notionnel à la sortie ; 5 bps aller-retour sur les cryptos, 4 bps sur l'or. Les rapports les
  lisent aussi à 10 et 6 bps.
- **Perte d'un trade au stop catastrophe :** au plus ≈ 4 · r du capital (moins si la taille est plafonnée), plus les
  frais et le gap. `[OBS]` À 0,25 % : −1,02 à −1,05 % par stop. Le pire trade de toute la réserve fait −1,21 % (XRP, gap
  de janvier 2017).

### 1.8 Critère de conformité du bot

Avant d'engager du capital, le moteur du bot est rejoué sur les séries de référence (5 bps, 0,25 %/ATR). Il doit
redonner les trades un par un :

| Série (flux) | Trades | Espérance par trade (ATR) |
|---|---|---|
| BTC/USD 2015-2025 (Bitstamp, panne de janvier 2015 retirée) | 2 075 | +0,180207 |
| SOL/USD 2021-2025 (Coinbase) | 769 | +0,135282 |
| ETH/USD 2017-08 → 2026-09 (Bitstamp) | 1 525 | +0,183415 |
| XRP/USD 2016-12 → 2026-09 (Bitstamp) | 1 689 | +0,262972 |
| Portefeuille des six, 2021-10 → 2026-09 | 4 744 | +0,198452 ; PnL +584,19 % ; MDD −37,40 % |

Rejeu de référence : `python experiments/D04/run_D04.py --controle` et `experiments/D04_1/run_D04_1.py`.

**Pièges d'implémentation :**
- la convention de fin d'échantillon de l'atlas (`anatomy.dev_universe`) ne garde un signal que si sa sortie native est
  observée ; c'est une convention de test, à ne pas appliquer en direct ;
- la décision n'utilise aucune donnée postérieure à la clôture de t ;
- les signaux se calculent actif par actif ; seul le capital est commun.

**Boucle du bot (schéma) :**

```text
à chaque clôture de barre t (UTC, toutes les 30 min), pour chaque actif :
    avancer Kalman, oscillateur, ATR14 et NIS d'une barre
    si une position atteint son horizon (ouverture de t_signal + 27) : la clore à l'ouverture de t + 1
    si signal natif en t, warm-up passé et t ≥ verrou de l'actif :
        calculer leg_atr, retrace_ratio, x1, nis_z_100
        si candidat RE-1 :
            verrou de l'actif ← t + 26
            entrer en d à l'ouverture de t + 1, notionnel = min(1, r / ATR_bps(t)) × capital valorisé
            stop ← P0 − d · 4 · ATR14(t) ; si F3 : le plus proche de P0 entre SL-B et ce stop
            poser le stop sur la plateforme dès le remplissage
```

## 2. Univers du portefeuille

### 2.1 Les six actifs (liste définitive)

| Actif | Flux des tests | Frais A/R | Période (version finale) | Espérance ATR [IC 95 %] ; bps | MDD 0,25 %/ATR |
|---|---|---|---|---|---|
| BTC/USD | Bitstamp | 5 bps | 2015-2025 | +0,180 [+0,012 ; +0,350] ; +9,8 | −21,4 % |
| | | | 2026 (janvier-septembre) | +0,705 [+0,045 ; +1,469] ; +32,3 | −6,9 % |
| ETH/USD | Bitstamp | 5 bps | 2017-08 → 2026-09 (réserve) | +0,183 [−0,010 ; +0,385] ; +10,4 | −39,1 % |
| SOL/USD | Coinbase | 5 bps | 2021-2025 | +0,135 [−0,117 ; +0,415] ; +9,3 | −15,2 % |
| | | | 2026 | +0,410 [−0,081 ; +0,997] ; +25,2 | −6,0 % |
| AVAX/USD | Coinbase | 5 bps | 2026 | +1,059 [+0,328 ; +1,784] ; +46,8 | −4,7 % |
| XRP/USD | Bitstamp | 5 bps | 2016-12 → 2026-09 (réserve) | +0,263 [−0,014 ; +0,640] ; +16,0 | −20,9 % |
| XAU/USD (CFD) | HistData | 4 bps | 2026 (jusqu'au 24 septembre) | +0,987 [+0,449 ; +1,479] ; +29,3 | −3,1 % |

- **IC :** bootstrap par grappes mensuelles, 2 000 tirages.
- **AVAX et or :** aucune mesure isolée de la version finale avant 2026 ; ils sont mesurés dans le portefeuille de
  D04.1.
- **ETH, gardé par décision du porteur :** seul sur 2021-10 → 2026-09, il perd 18 %, mais le retirer serait une
  sélection après lecture de la réserve.

### 2.2 Rôle de l'or

- `[OBS]` **L'or est le seul actif dont le retrait aggrave le portefeuille** (D04.2, 0,25 %/ATR) :
  - sans or : pire journée −5,71 % au lieu de −5,20 %, MDD −41,5 % au lieu de −37,4 %, Calmar 1,04 au lieu de 1,25 ;
  - sans l'une des cryptos, la pire journée reste entre −4,06 % et −5,14 %.
- `[OBS]` **Le 2022-11-04 (pire journée, plus bas à 08:00 UTC),** les cinq cryptos perdent entre −0,73 % et −1,41 % du
  capital chacune et l'or gagne +0,51 %, ce qui fait exactement l'écart entre les deux portefeuilles (D04.1).
- `[OBS]` **Les pires journées sont des chocs crypto simultanés, dans les deux sens.** Le 2022-11-04, une hausse stoppe
  quatre ventes ; le 2025-11-06, une baisse stoppe quatre achats. Le « krach » qui menace RE-1 est donc un choc adverse
  commun aux cryptos, à la hausse comme à la baisse.
- `[OBS]` **L'or rapporte peu seul.**
  - Sur 2021-10 → 2026-09, il fait +15 %, dont +21 % sur les neuf mois de 2026.
  - Avant 2026, son brut était absorbé par les frais (RE-1 sans stop catastrophe, 4 bps) : +0,011 ATR net sur 2009-2019
    (D02.0) ; brut +0,24 ATR pour 0,26 ATR de frais sur 2020-2025 (D01).
  - Sa taille est presque toujours plafonnée à 1x (ATR14 sous 25 bps). Il porte donc moins de 0,25 % de risque par
    ATR, et il explique l'essentiel de l'exposition brute au-delà de 1x.
- `[HYP]` **Son rôle est d'amortir, pas de rapporter.** Ses signaux ne se déclenchent pas avec ceux des cryptos, parce
  que son marché, ses séances et ses moteurs diffèrent. La corrélation entre l'or et les cryptos n'a pas été mesurée, et
  l'effet repose sur quelques journées.

## 3. Matrice de dimensionnement (D04.2, axe levier)

**Cadre.** Six actifs sur un capital commun, entrées du 2021-10-01 au 2026-10-01 exclu (1 775 journées UTC en position).
Frais 5 bps (or 4 bps), plafond de 1x par position. Les trades sont les mêmes à toutes les tailles : PF 1,13, WR
42,3 %, +0,198 ATR, 4 744 trades.

**8 métriques, référence 0,25 %/ATR :**

| PnL net : 0,25 %/ATR ; 1x par position ; bps (1x) | PF (1x) | WR | Espérance : ATR ; bps | MDD : 0,25 %/ATR ; 1x | Trades (/mois) | Durée médiane | Part des frais (1x) | Calmar |
|---|---|---|---|---|---|---|---|---|
| +584 % ; +1 439 % ; +46 985 | 1,13 | 42,3 % | +0,198 ; +9,9 | −37,4 % ; −81,5 % | 4 744 (79,1) | 26 barres (13 h) | 33 % | 1,25 |

**Matrice :**

| Risque par trade (% du capital par ATR14) | Pire journée : valorisé ; solde ; pessimiste | Journées < −4 % : valorisé ; solde | Journées < −3 % (valorisé) | MDD | PnL (5 ans) | Rendement annualisé historique | Calmar | Exposition brute : max ; P99 |
|---|---|---|---|---|---|---|---|---|
| 0,05 % | −1,10 % ; −0,88 % ; −1,26 % | 0 ; 0 | 0 | −10,7 % | +57 % | +9,4 % | 0,89 | 1,55x ; 0,85x |
| 0,10 % | −2,16 % ; −1,75 % ; −2,48 % | 0 ; 0 | 0 | −19,8 % | +139 % | +19,0 % | 0,96 | 3,10x ; 1,66x |
| 0,15 % | −3,19 % ; −2,55 % ; −3,66 % | 0 ; 0 | 2 | −26,3 % | +248 % | +28,3 % | 1,08 | 4,17x ; 2,28x |
| 0,20 % | −4,18 % ; −3,33 % ; −4,80 % | 3 ; 0 | 7 | −32,1 % | +387 % | +37,3 % | 1,16 | 4,60x ; 2,74x |
| **0,25 % (référence)** | −5,20 % ; −4,16 % ; −5,90 % | 5 ; 3 | 25 | −37,4 % | +584 % | +46,9 % | 1,25 | 5,22x ; 3,09x |
| 0,30 % | −6,32 % ; −4,98 % ; −6,96 % | 12 ; 10 | 60 | −43,1 % | +803 % | +55,3 % | 1,28 | 5,55x ; 3,41x |

- **Références de la journée :** journée UTC. « Valorisé » = capital valorisé à 00:00, gains latents compris ; « solde »
  = solde réalisé à 00:00 ; « pessimiste » = toutes les positions à l'extrême défavorable de la même barre.
- **Rendement annualisé :** (1 + PnL)^(1/5) − 1, soit Calmar × |MDD|. C'est un historique, pas une espérance (voir
  ci-dessous).

**Curseur journalier.** La pire journée est un multiple à peu près constant de r :

| Lecture | Multiple de r |
|---|---|
| Pire journée historique, capital valorisé | ≈ 21 (20,8 à 22,0) |
| Pire journée historique, solde réalisé | ≈ 17 (16,6 à 17,6) |
| Borne pessimiste historique | 23 à 25 |
| Six stops catastrophe le même jour, sans gap ni gain latent rendu (mécanique) | 24 |

- `[HYP]` **Lecture :** pour une perte journalière tolérée L, r ≈ L / multiple. Avec L = 4 %, r ≈ 0,24 % (solde
  historique), 0,19 % (valorisé historique), 0,17 % (six stops) ou 0,16 % (borne pessimiste).
- `[CODE]` **La borne mécanique peut être dépassée :**
  - par un gain latent rendu, puisque la référence valorisée l'inclut ;
  - par un gap au-delà du stop ;
  - par deux trades du même actif dans la journée (un verrou de 26 barres en laisse passer deux sur 48).

**Lecture des autres colonnes :**
- `[OBS]` **Toujours les mêmes journées :** la pire est le 2026-01-26 jusqu'à 0,20 %/ATR, puis le 2022-11-04 au-delà ;
  le 2025-11-06 suit de près (−5,06 % à 0,25 %/ATR).
- `[OBS]` **Le MDD croît moins vite que r ;** il vaut encore −10,7 % à 0,05 %/ATR.
- `[OBS]` **Le rendement est concentré dans le temps.**
  - À 0,25 %/ATR, le capital vaut 1,03 fin 2022, 1,64 fin 2023, 1,92 fin 2024, 2,18 fin 2025, puis 6,84 fin
    septembre 2026, soit ×3,1 en neuf mois.
  - Hors 2026, cela fait ≈ +20 % par an pour le même MDD (Calmar ≈ 0,5).
  - 2026 est la période la plus favorable mesurée.
- `[OBS]` **Sans taille en ATR** (1x par position), la pire journée atteint −16,8 % et le MDD −81,5 % (D04.1).
- `[OBS]` **Levier :** l'exposition brute dépasse 1x dès 0,10 %/ATR (maximum 3,1x) ; le compte doit pouvoir porter ce
  levier.

## 4. Avertissements opérationnels et psychologiques

### 4.1 Latence : une barre de retard ne coûte rien

- `[OBS]` **Mesure de D03.1** (RE-1 sans stop catastrophe), entrée à open[t + 2] au lieu de open[t + 1], soit 30 min plus
  tard, avec le même stop et le même verrou :
  - BTC 2015-2025 : +0,014 ATR [−0,025 ; +0,056] ; +0,032 sur 2015-2019, −0,003 sur 2020-2025 ;
  - SOL : +0,002 ;
  - 48 trades de BTC et 8 de SOL sortent aussitôt, leur stop étant déjà franchi à l'entrée.
- `[HYP]` **RE-1 n'exploite pas une microstructure fugace : la vitesse n'est pas un avantage à acheter.** D'où la
  décision du porteur (2026-10-03) d'autoriser les ordres à cours limité (maker) pour les entrées. Si l'ordre n'est
  pas rempli, l'entrée se fait au marché à la barre suivante.
- **Règle de repli :** les niveaux de stop restent ceux calculés sur P0 = open[t + 1]. Si le stop est déjà franchi au
  remplissage, le bot ne prend pas la position (convention de D03.1 : sortie immédiate, brut nul).
- **Non mesuré :**
  - le taux de remplissage d'un ordre passif ;
  - la sélection adverse. Un ordre passif se remplit surtout quand le prix revient contre la position ; les ordres non
    remplis sont ceux où le prix est parti dans le bon sens, et les rattraper coûte plus que le retard moyen mesuré ;
  - le niveau réel des frais maker ;
  - le retard des sorties.

### 4.2 Glissement des stops : le vrai risque d'exécution

- `[OBS]` **Stops de F3 seuls (D03.1, BTC 2015-2025) :** 23 % des trades sortent sur un stop de F3. Exécutés 0,5 ATR14(t)
  plus loin, l'espérance passe de +0,218 à +0,102 ATR [−0,083 ; +0,290] et le Calmar de 0,32 à 0,10. Sur SOL, elle passe
  de +0,190 à +0,069.
- `[OBS]` **Avec en plus le stop catastrophe et une barre de retard** (glissement sur tous les stops), l'espérance tombe
  à −0,003 ATR [−0,178 ; +0,169] sur BTC et −0,039 sur SOL. L'avantage disparaît.
- `[CODE]` **Coût par trade :** un glissement moyen de k ATR sur chaque sortie sur stop retire exactement
  k × (part des sorties sur stop) à l'espérance en ATR. Dans la version finale :

  | Actif | Part des sorties sur stop | Coût par 0,1 ATR de glissement | Glissement qui annule l'espérance |
  |---|---|---|---|
  | BTC 2015-2025 | 36,7 % (478 SL-B de F3 + 284 stops catastrophe sur 2 075) | 0,037 ATR | ≈ 0,49 ATR |
  | ETH | 40,3 % | 0,040 ATR | ≈ 0,46 ATR |
  | XRP | 37,1 % | 0,037 ATR | ≈ 0,71 ATR |

- **Ordre de grandeur :** l'ATR14 moyen des trades de BTC 2015-2025 vaut 57 bps (D02.1). 0,1 ATR fait donc ≈ 6 bps, et
  0,5 ATR ≈ 28 bps.
- `[HYP]` **Exigences pour le bot :**
  - les stops sont posés sur la plateforme dès le remplissage de l'entrée, jamais gérés par le seul client ;
  - le stop catastrophe est un ordre stop au marché. Il existe pour borner la perte, alors qu'un stop à cours limité peut
    rester inexécuté dans un krach ;
  - le glissement réel des stops, en ATR, est mesuré en direct avant d'engager du capital, puis suivi. C'est la variable
    d'exécution qui pèse le plus.

### 4.3 Chasseur de queue droite : accepter des mois de saignement

- `[OBS]` **Le trade médian perd :** WR 42,3 % (portefeuille), PF 1,13. Médiane −0,97 ATR sur ETH, −0,65 ATR sur XRP.
- `[OBS]` **Sans le 1 % meilleur des trades, l'espérance tombe à zéro ou en dessous :**
  - BTC +0,035 ATR [−0,128 ; +0,199] (RE-1 sans stop catastrophe, D02.1), ETH −0,060, XRP −0,058 ;
  - sur BTC, 21 trades (1 %) font 84 % de la somme nette en ATR ;
  - sur XRP, un seul trade en fait 56 % : celui du 2023-07-13, jour de la décision de justice dans l'affaire SEC
    contre Ripple.
- `[OBS]` **Profil de ces trades** (BTC, D02.1) : ouverts à ATR bas (32 bps en moyenne, contre 57), avec une grosse
  position (6 sur 21 plafonnés à 1x), aucun stoppé.
- `[OBS]` **Une année peut tenir à un trade.** En 2023, le portefeuille gagne +59 % ; le trade de XRP a rapporté
  ≈ +62 % du capital valorisé à son entrée, avec la même règle de taille.
- `[OBS]` **Le temps sous l'eau est long.**
  - MDD de −37,4 % (0,25 %/ATR) : pic le 2023-07-13, creux le 2024-01-27, retour au pic le 2025-03-02. Soit 598 jours
    sous le pic, dont 198 de baisse.
  - L'année 2022 finit à +1 %.
  - ETH perd trois années sur dix (2022, 2023, 2025), XRP deux (2019, 2020).
- `[HYP]` **Conséquences pour l'exploitation :**
  - ne pas couper le bot pendant un drawdown. Les trades qui font l'année sont rares et imprévisibles ; en manquer un
    change le résultat de plusieurs années ;
  - aucune règle de pause (après N pertes, après un drawdown) ni aucune intervention manuelle n'a été testée. Toute
    règle qui retire des trades risque de retirer le 1 % qui porte l'avantage ;
  - choisir r d'abord sur le MDD et la durée sous l'eau que l'on peut tenir, pas sur le rendement.

### 4.4 Autres risques hors modèle

- **Portage non modélisé :** financement des contrats perpétuels (funding), emprunt pour les ventes, financement de nuit
  du CFD or. Un trade dure 13 h et traverse en général un ou deux paiements de funding (toutes les 8 h). À chiffrer sur
  le lieu d'exécution avant le déploiement.
- **Flux de prix :** les signaux viennent d'un Kalman sur le close de Bitstamp, Coinbase et HistData. Un autre flux
  donne d'autres signaux, et l'écart n'est pas mesuré. Il faut rejouer l'historique du flux d'exécution (§1.8) avant de
  trader.
- **Levier et ventes :** l'exposition brute va de 1,5x à 5,6x au maximum selon r (§3), avec des ventes à découvert. Il
  faut un compte sur marge ou des dérivés ; les appels de marge et les liquidations ne sont pas modélisés.
- **Or :** séances, coupure quotidienne, week-end. Un gap d'ouverture saute le stop ; la sortie se fait alors à
  l'ouverture, comme dans les tests.
- **Frais :** les tests supposent 5 bps aller-retour. À 10 bps, l'espérance tombe à +0,056 ATR (BTC 2015-2025), +0,088
  (ETH) et +0,181 (XRP).
- **Contrepartie :** les fonds déposés sur une plateforme portent son risque (faillite, gel des retraits). Ce risque est
  hors du champ des tests.

## 5. Limites de la preuve

- **La réserve a été lue une fois (D04) :** ETH, XRP et 2026 ne sont plus hors échantillon. La composition et la matrice
  (D04.1, D04.2) ont été mesurées après cette lecture ; elles sont descriptives.
- **Marges minces :** les IC d'ETH et de XRP contiennent 0, et sans le 1 % meilleur l'avantage disparaît.
- **2026 :** c'est la période la plus favorable mesurée ; elle ne s'extrapole pas.
- **Seuils :** estimés sur BTC 2020-2025, ils s'appliquent aussi aux trades antérieurs à 2020 (BTC, ETH, XRP), qui
  utilisent donc des seuils venus de données postérieures. Aucun seuil n'a été estimé sur ETH ou XRP.
- **Stop catastrophe :** le scénario qu'il couvre, un krach de 20 à 30 % pendant une position à 1x, n'existe pas dans
  l'historique.
- **Corrélations :** non mesurées entre les actifs, sauf BTC et SOL (corrélation mensuelle −0,04, D03).

## 6. Statut

- **Branche « Fonds propres » close le 2026-10-05,** sur décision du porteur. Le moteur, l'univers et la règle de taille
  sont gelés ; seul r reste à choisir au déploiement.
- **Suite :** un nouveau cycle de recherche, consacré aux contraintes des Prop Firms, avec son propre protocole.

## 7. Sources

- `experiments/D02_1/rapport_D02_1.md` : queue du 1 % meilleur (K14).
- `experiments/D03_1/rapport_D03_1.md` : stop catastrophe, glissement des stops, latence.
- `experiments/D04/rapport_D04.md`, `experiments/D04/lectures_D04.json` : réserve (ETH, XRP, 2026), queue droite, part
  des stops.
- `experiments/D04_1/rapport_D04_1.md` : portefeuille des six, pire journée, contributions.
- `experiments/D04_2/rapport_D04_2.md`, `experiments/D04_2/resultats_D04_2.csv` : composition et levier.
- `RESEARCH_LOG.md` : décisions du porteur (2026-10-03, 2026-10-05).
