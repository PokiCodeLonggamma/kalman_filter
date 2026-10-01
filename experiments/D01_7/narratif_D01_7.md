# EXP-D01.7 — Portabilité de RE-1 figée (zero-shot) : CFD sur indices, argent, GBPJPY et CFD sur ETF (Saxo)

- **Date :** 2026-10-01. **Étape :** D, test de portabilité.
- **Nature : descriptive.** RE-1 est strictement gelée : H = 26, R0 = 100, frontière 0,85, P75 de `nis_z_100` et médiane
  de `leg_atr` de BTC, cooldown, SL-B, F2b/F3. Aucun réglage par actif, aucune modification de RE-1 sur la base de ces
  résultats.
- **Version : partie 2, univers redéfini par le porteur.**
  - La partie 1 (GBPJPY de HistData : brut −0,035 ATR, −0,443 à 4 bps) reste consignée dans `RESEARCH_LOG.md`.
  - Les futures NQ, RTY, CL et HG sont abandonnés, faute d'accès puis parce que les séries continues de Saxo ne sont pas
    ajustées.
- **Données :**
  - 2020-2025 seulement, chaque série étant tronquée avant le 2026-01-01 au chargement ; rien de 2026 n'a été téléchargé.
  - Séries Saxo OpenAPI LIVE, compte du porteur ; références FRED.
- **Code :**
  - `experiments/D01_7/saxo_univers_D01_7.py` (séries) et `donnees_D01_7.py` (FRED) ;
  - `run_D01_7.py` (`--audit`, puis contrôles et mesures), qui réutilise la chaîne de D01 : `strategy.run_re1`,
    `prepare`, `diagnostics`.

## 0. Cadrage

- **QUESTION :** RE-1, verrouillée en C02bis sur BTC, conserve-t-elle son comportement hors crypto, sur trois familles
  de marchés ?
  - CFD sur indices au comptant cotés presque 24 h sur 24 : US100, US30, GER40, EU50, HK50 ;
  - argent et GBPJPY au comptant ;
  - CFD sur ETF cotés en séance américaine : TLT, USO, SMH, URA, GDX.
- **PERTINENCE POUR LE FILTRE AKF :** D01 a montré que la géométrie des signaux se transpose, mais que la rente dépend de
  la structure du marché : frais en ATR, séances. Cet univers croise marchés quasi continus et marchés de séance,
  régions et classes d'actifs.
- **CE QUE LE PROTOCOLE MESURE RÉELLEMENT :**
  - l'audit des données avant tout backtest ;
  - par actif, les 8 métriques en brut et nettes de coûts déclarés, l'espérance en ATR et en bps avec IC par grappes
    mensuelles, le capital à 0,25 %/ATR et à 1x ;
  - Long/Short, F2b/F3, volatilité, sessions, interruptions, concentration, queues.
- **CE QU'IL NE PERMET PAS DE CONCLURE :**
  - pas de validation hors échantillon ;
  - pas de classement statistique : choisir les meilleurs actifs pour D02 sur ce même échantillon est une sélection, à
    vérifier hors échantillon ;
  - coûts réels non mesurés : ni financement de nuit, ni ajustements de dividendes des CFD ;
  - aucun réglage.

## 1. Données et contrôles (avant les résultats)

### 1.1 Parcours des sources

- **Sources écartées :** QuantConnect (aucun export), puis le dépôt GitHub axb0306/cme-futures-ohlc (FAIL : aucune donnée
  2020-2025).
- **Saxo OpenAPI LIVE :** c'est la seule source qui fournit des séries locales complètes de 2020 à 2025.
  - Ses séries continues (futures c1, CFD « cont ») sont brutes : le raccord au changement de contrat n'est pas ajusté.
  - Celui du WTI tombe au milieu d'une barre de 30 min, le dernier jour de cotation, vers 11:00 heure de New York.
  - Le porteur a abandonné les séries continues (annexe 9 de `audit_saxo_D01_7.md`).
- **Univers redéfini par le porteur :**
  - US100, US30, GER40, EU50, HK50, XAGUSD, GBPJPY. HK50 remplace Japan 225, absent des CFD sur indice chez Saxo.
  - En option, 5 CFD sur ETF, inclus par le porteur : SMH et URA à sa demande ; TLT, USO et GDX choisis par l'agent.
- **GBPJPY :** lu chez Saxo, sur décision du porteur.
- **Coûts aller-retour :** validés par le porteur avant tout résultat (§2).

### 1.2 Audit [OBS]

- **13 séries sans défaut :**
  - aucun doublon, désordre, prix négatif ou nul, ni OHLC incohérent ;
  - couverture de 2020-01-02 à 2025-12-30/31 ;
  - modes de requête UpTo et From identiques, téléchargements reproductibles (`audit_univers_D01_7.md`).
- **Recoupements externes, critère de la partie 1 fixé avant :**

  | Série | Référence | Jours | Corrélation des variations | Écart médian (absolu) | Meilleur décalage |
  |---|---|---|---|---|---|
  | US100 | clôture officielle du NASDAQ-100 à 16:00 | 1 496 | 0,9991 | −0,3 bp (2,1) | 0 |
  | US30 | clôture du Dow Jones à 16:00 | 1 496 | 0,9994 | −0,3 bp (1,5) | 0 |
  | GBPJPY | taux de midi H.10 | 1 499 | 0,9997 | −1,9 bp (1,9) | 0 |

  Horodatage et prix des barres Saxo sont validés.
- **Fermetures de bourse admises**, déclarées avant le calcul (règle des 5 jours de D01 appliquée trou par trou) :
  - Noël 2025 pour GER40 et EU50 (123,5 h) ;
  - pour HK50 : Pâques et Ching Ming 2021, Nouvel An lunaire 2023 et 2025 (126,5 à 141,5 h).

  Aucun autre trou ne dépasse 5 jours.
- **Aucun changement de contrat caché dans les CFD sur indice :** les sauts en séance ne sont pas plus fréquents les
  jours d'échéance des futures.
- **Séances :**
  - CFD sur indices US : 23 h sur 24. Saxo a ajouté l'heure de 16:00 à 17:00 en 2022.
  - GER40 et EU50 : de 02:00 à 22:00 heure de Berlin.
  - HK50 : trois séances de la bourse de Hong Kong par jour.
  - XAGUSD : 23 h sur 24 ; GBPJPY : continu en semaine.
  - ETF : séance américaine seule, sans heures étendues ; historique ajusté des splits.
- **Signaux : la géométrie se transpose.**
  - Médiane locale de `leg_atr` : 2,85 à 3,07 sur les CFD, l'argent et GBPJPY ; 3,18 à 3,43 sur les ETF, allongée par
    les gaps de nuit (K8). BTC : 2,82.
  - P75 local de `nis_z_100` : 1,03 à 1,46 (BTC : 1,22).
  - ATR de 30 min médian : 11 bps (GBPJPY) à 72 bps (URA) ; BTC : 50 bps.

### 1.3 Contrôles bloquants

- Ancre P6.5d reproduite.
- RE-1 de la chaîne = C02bis : 1 080 trades, 40 métriques.
- Seuils de BTC gelés.
- Invariance d'échelle du moteur : contrôle de la partie 1, inchangé.

## 2. Résultats [OBS]

**Coûts aller-retour validés par le porteur.** Chaque actif se lit à trois niveaux : sans frais, à l'écart médian de
Saxo, et au coût principal. Ce coût principal vaut le plus grand de 4 bps et du P90 de l'écart, arrondi au point
supérieur. Pour les ETF, ce sont 0 et 4 bps. BTC, en référence, se lit à 5 bps.

| Actif (coût principal) | Trades (par mois) | Brut ATR | **Net ATR [IC]** | Net bps [IC] | Frais en ATR | WR ; PF (1x) | PnL : 0,25 %/ATR ; 1x | MDD : 0,25 %/ATR ; 1x | Années > 0 |
|---|---|---|---|---|---|---|---|---|---|
| BTC (5 bps, réf.) | 1 080 (15,0) | +0,504 | **+0,369 [+0,098 ; +0,645]** | +12,3 [+0,2 ; +24,4] | 0,14 | 44,3 % ; 1,20 | +138 % ; +204 % | −13,5 % ; −43,9 % | 6/6 |
| US100 (4) | 695 (9,7) | +0,139 | −0,097 [−0,428 ; +0,252] | −1,0 [−8,3 ; +6,5] | 0,24 | 39,6 % ; 0,97 | −5 % ; −10 % | −19,7 % ; −27,0 % | 1/6 |
| US30 (4) | 710 (9,9) | +0,327 | −0,004 [−0,350 ; +0,348] | +3,9 [−3,2 ; +12,0] | 0,33 | 41,0 % ; 1,17 | +11 % ; +29 % | −13,7 % ; −14,1 % | 2/6 |
| GER40 (4) | 545 (7,6) | +0,237 | −0,005 [−0,292 ; +0,294] | +1,4 [−5,2 ; +8,2] | 0,24 | 43,1 % ; 1,05 | +0 % ; +5 % | −22,9 % ; −27,5 % | 2/6 |
| EU50 (7) | 535 (7,4) | −0,172 | **−0,590 [−0,946 ; −0,214]** | −10,6 [−19,1 ; −2,4] | 0,42 | 38,3 % ; 0,70 | −37 % ; −44 % | −40,6 % ; −47,8 % | 1/6 |
| HK50 (8) | 425 (5,9) | +0,192 | −0,103 [−0,539 ; +0,334] | −3,0 [−15,0 ; +10,1] | 0,30 | 40,7 % ; 0,94 | −9 % ; −15 % | −32,3 % ; −41,9 % | 2/6 |
| XAGUSD (11) | 651 (9,0) | +0,060 | −0,307 [−0,634 ; +0,006] | −12,1 [−22,5 ; −1,9] | 0,37 | 38,1 % ; 0,79 | −41 % ; −57 % | −43,5 % ; −59,7 % | 1/6 |
| GBPJPY (4) | 754 (10,5) | +0,095 | **−0,303 [−0,572 ; −0,031]** | −3,0 [−6,5 ; +0,4] | 0,40 | 40,7 % ; 0,82 | −20 % ; −21 % | −22,0 % ; −22,1 % | 0/6 |
| TLT (4) | 157 (2,2) | −0,042 | −0,205 [−0,972 ; +0,570] | −6,4 [−27,8 ; +15,8] | 0,16 | 39,5 % ; 0,88 | −9 % ; −11 % | −16,6 % ; −21,1 % | 2/6 |
| USO (4) | 140 (1,9) | +0,220 | +0,148 [−0,553 ; +0,813] | +42,3 [−27,6 ; +122,1] | 0,07 | 47,9 % ; 1,42 | +4 % ; +65 % | −9,6 % ; −24,8 % | 2/6 |
| SMH (4) | 149 (2,1) | −0,105 | −0,180 [−0,795 ; +0,409] | −6,0 [−38,6 ; +24,7] | 0,08 | 41,6 % ; 0,94 | −7 % ; −13 % | −15,5 % ; −30,4 % | 2/6 |
| URA (4) | 127 (1,8) | +0,154 | +0,093 [−0,823 ; +1,100] | −10,6 [−68,6 ; +47,8] | 0,06 | 38,6 % ; 0,92 | +2 % ; −18 % | −12,6 % ; −41,8 % | 2/6 |
| GDX (4) | 143 (2,0) | +0,417 | +0,349 [−0,365 ; +1,076] | +42,8 [−13,1 ; +109,4] | 0,07 | 44,1 % ; 1,46 | +12 % ; +70 % | −8,5 % ; −19,1 % | 5/6 |

Durée médiane : 26 barres, soit 13 h pour les marchés quasi continus, 20 h pour HK50 et 48 h pour les ETF. La part des
frais et les tableaux complets à tous les coûts sont en annexe C.

- **Aucun actif n'a un IC à borne basse positive au coût principal ; BTC reste le seul.**
  - Estimations positives : GDX, USO et URA. Ce sont des ETF, avec 127 à 157 trades et des IC larges de ±0,7 à ±1,0 ATR.
  - Significativement négatifs : EU50, et GBPJPY d'un cheveu.
- **Le brut est faible.**
  - Positif en estimation sur 9 actifs sur 12 : de +0,06 à +0,42 ATR, contre +0,50 sur BTC. Tous les IC en ATR
    contiennent 0.
  - Seul US30 a un IC en bps au-dessus de 0 : +7,9 bps [+0,8 ; +16,0], pour un IC en ATR de [−0,019 ; +0,667].
- **Ce sont les frais en ATR qui tranchent.**
  - Sur les CFD sur indices, l'argent et GBPJPY, l'ATR de 30 min ne vaut que 11 à 34 bps. Les coûts principaux y
    coûtent de 0,24 à 0,42 ATR par trade, autant ou plus que le brut.
  - Sur les ETF, 4 bps ne coûtent que 0,06 à 0,16 ATR.
  - **À l'écart médian de Saxo :**
    - US30 : +0,211 ATR [−0,136 ; +0,556], soit +6,5 bps [−0,6 ; +14,6] ;
    - GER40 : +0,104 ;
    - US100 : +0,086 ;
    - HK50 : −0,033 ;
    - EU50 : −0,458.
- **ETF : le brut vient des nuits, sur peu de trades.**
  - 91 à 94 % des trades traversent au moins une nuit, et 78 à 81 % durent plus de 24 h.
  - Composante des gaps de nuit et composante en séance :
    - GDX : +0,41 et +0,02 ATR ;
    - USO : +0,24 et −0,01 ;
    - SMH : +0,21 et −0,34 ;
    - TLT : +0,14 et −0,18 ;
    - URA, seul à l'inverse : −0,00 et +0,14.
  - Stops percés à l'ouverture : 7 à 17 par ETF, avec un dépassement de +0,7 à +2,4 ATR. C'est le profil de SPY et XLE
    en D01 bis (K8).
- **Long et Short, en brut :**
  - **US30 gagne des deux côtés** (+0,44 et +0,20), comme HK50 (+0,16 et +0,23) et GDX (+0,23 et +0,59).
  - GER40 n'est porté que par ses Longs (+0,77 contre −0,31). C'est la dérive haussière du DAX ; la composante
    symétrique ne vaut que +0,23.
  - Même dissymétrie sur URA (+0,54 contre −0,35) et USO (−0,04 contre +0,47).
- **Années, au coût principal :**
  - GDX : 5 années positives sur 6 (2023 −0,80).
  - US30 : 2 sur 6, avec 2020 à +0,58.
  - GER40 : +0,65 et +0,51 en 2020-2021, −0,71 en 2025.
  - HK50 : négatif de 2020 à 2022, puis +0,65 et +0,73 en 2024-2025.
  - USO : 2020 à +1,46 à lui seul.
- **GBPJPY Saxo confirme la partie 1.**
  - Brut : +0,095 [−0,167 ; +0,364], contre −0,035 sur HistData.
  - À 4 bps : −0,303 contre −0,443.
  - Les trous de HistData en 2023 ne changeaient pas la conclusion.
- **Dimensionnement :** le 0,25 %/ATR est plafonné à 1x pour 70 à 98 % des trades sur les CFD sur indices et GBPJPY
  (ATR de 11 à 22 bps). Pour eux, la colonne « 0,25 %/ATR » vaut à peu près le 1x.
- **Queues :** médiane de −0,5 (USO) à −1,6 ATR (EU50), et le décile supérieur apporte de +0,7 à +1,1 ATR par trade.
  C'est le profil de BTC (médiane −0,42, décile supérieur +0,92), sans la moyenne positive.
- **Stop de F3 :** il aide US30 (+0,54 [+0,15 ; +0,93]) et nuit à HK50 (−0,49 [−0,94 ; −0,07]). Ailleurs, l'IC contient 0.

## 3. Lecture

- [HYP] **Le signal se transpose, la rente non.**
  - Hors BTC, RE-1 détecte la même cinématique, mais le mouvement qui suit, sur 13 h, vaut peu en ATR.
  - Le rapport décisif est brut / ATR contre frais / ATR. C'est la leçon de l'or en D01, étendue ici aux indices.
- [HYP] **US30 est le seul CFD sur indice dont le brut est symétrique et positif en bps.** Sa viabilité dépend du coût
  réel : écart Saxo de 1,4 bp (P90 1,9), contre 4 bps retenus. C'est une question de coût d'exécution, pas de signal.
- [HYP] **ETF :** le brut observé est un effet des gaps de nuit, mesuré sur environ 140 trades. On ne peut pas le
  distinguer du bruit. Même structure que SPY et XLE (K8 à K10).
- [PISTE] **Si le porteur retient des actifs pour D02,** les candidats par brut et par coût sont :
  - US30 : brut +0,33 ATR, écart de 1,4 bp ;
  - GER40 : brut +0,24, porté par la dérive ;
  - US100 : brut +0,14, écart de 0,9 bp ;
  - GDX : brut +0,42, mais venu des gaps, sur 143 trades.

  Un choix fait sur ce même échantillon est biaisé vers les gagnants chanceux. À valider hors échantillon.
- [PISTE] Mesurer le coût réel chez Saxo, sur un compte de démonstration ou par la grille tarifaire : écart, commission
  des CFD sur ETF, financement de nuit. Il décide pour US30, US100 et GER40.
