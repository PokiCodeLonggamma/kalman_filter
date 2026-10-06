# Données FTMO et frictions du compte (D05.1)

*2026-10-06. Récupération par le cBot AkfExportFtmo (sans Open API), vérification, et modèle de frictions trade par
trade. Aucune simulation de challenge : la Baseline cTrader, le profil RE-1 TradFi et l'inclusion se font dans la session
suivante (décision du porteur).*

Décisions du porteur, 2026-10-06 :
- terminer ici la récupération, la vérification et les frictions (trous, écart, swaps, commission), puis passation ;
- données cTrader pour les actifs hors crypto (historique FTMO, sans complément Saxo) ; cryptos sur les séries des
  courtiers de D05, avec les frictions FTMO ;
- GLE absent chez FTMO, remplacé par SAN.

Sources : `audit_ftmo_D05_1.md` (généré), `frictions_D05_1.csv`, `couts_actifs_D05_1.csv`, `pauses_D05_1.csv`,
`profils_ecarts_D05_1.csv`.

## 1. Récupération

- [CODE] cBot v1 : bougies M30 (UTC, bid, bougie en cours exclue), ticks bid/ask des 10 derniers jours, fiches simples.
  cBot v2 : fiches complètes (type et jour triple du swap, commission, paliers de levier, séances).
- [OBS] 11 symboles récupérés. Les séries sont importées au schéma de `load_ohlc` dans `data/raw/ftmo/`, avec leur
  empreinte (`import_ftmo_D05_1.json`).

  | Actif | Première barre |
  |---|---|
  | US100, US30, GER40, WTI, Brent | 2020-11-08 |
  | Or | 2020-05-06 |
  | GBPJPY | 2020-04-01 |
  | BTC, ETH | 2020-07-08 |
  | XRP | 2020-07-13 |
  | SOL | 2025-04-17 |

- [OBS] **SAN et AVAX manquent.** L'instance v2 a gardé l'ancienne liste de symboles : cTrader garde la valeur d'un
  paramètre qui conserve le même nom de propriété. AVAX se nomme `AVAUSD` chez FTMO.
- **Pour les récupérer :** mettre `…;SAN;AVAUSD` dans « Fiches pour » de l'instance et relancer, soit une minute. En
  attendant, AVAX prend l'écart et la fiche de SOLUSD ([HYP]).

## 2. Vérification (`audit_ftmo_D05_1.md`)

- [OBS] Horodatages propres : ordre, aucun doublon, grille :00/:30, bougies cohérentes. Barres plates : 1 à 60 par
  série.
- [OBS] **Recoupement avec les séries du dépôt, sur les barres communes :**

  | Actif | Référence | Corrélation 30 min | Décalage du max | Niveau médian |
  |---|---|---|---|---|
  | US100 | Saxo | 0,996 | 0 | +1,2 bps |
  | US30 | Saxo | 0,998 | 0 | +1,1 bps |
  | GER40 | Saxo | 0,998 | 0 | +0,9 bps |
  | GBPJPY | Saxo | 0,994 | 0 | +0,9 bps |
  | WTI | Saxo (continu raccordé à l'échéance) | 0,926 | 0 | +2,3 bps |
  | Or | HistData | 0,998 | 0 | +0,5 bps |
  | BTC | Bitstamp | 0,992 | 0 | −4,0 bps |
  | ETH | Bitstamp | 0,991 | 0 | −7,1 bps |
  | SOL | Coinbase | 0,981 | 0 | −5,0 bps |
  | XRP | Bitstamp | 0,984 | 0 | −17,7 bps |

  Les deux sources sont en UTC à l'ouverture des barres. Le niveau négatif des cryptos est cohérent avec un bid FTMO
  face à un prix de transaction. Aucune référence n'existe pour le Brent.

## 3. Trous de cotation

- [OBS] **Séances officielles des fiches (UTC) :**
  - CFD sur indices, pétrole et or : coupure quotidienne de 20:50 à 22:05, du dimanche 22:05 au vendredi 20:50.
    Brent : de 00:05 à 20:50.
  - GBPJPY : coupure de 20:55 à 21:05.
  - Cryptos : 7 jours sur 7, coupure de 10 minutes de 20:55 à 21:05.
- [OBS] **Barres des cryptos :** pauses le samedi, absentes des séances officielles.
  - Durée de 4 à 15 heures environ, soit 43 à 75 trous par année complète (2021-2025, BTC).
  - Elles sont communes à la plateforme : 357 des 368 pauses d'ETH tombent aussi sur BTC.
  - [HYP] Il s'agit de maintenance, ou de trous du serveur d'essai.
- [CODE] **Traitement retenu :**
  - Hors crypto : RE-1 tourne sur les barres FTMO telles quelles, sans rien combler. Les gaps sont tradés comme ils
    viennent.
  - Cryptos, sur les séries des courtiers, avec `propfirm.frictions.ajuster_pauses` :
    - une entrée qui s'ouvre pendant une pause est abandonnée ;
    - une sortie ou un stop pendant une pause est exécuté à l'ouverture de la réouverture ;
    - [HYP] un stop franchi pendant la pause part même si le prix est revenu ;
    - calendrier propre à chaque actif sur son historique FTMO, celui de BTC avant.
- [OBS] **Effet sur la fenêtre D05 (2021-10 → 2026-10) :**

  | Actif | Entrées abandonnées | Sorties à la réouverture | Net FTMO, continu → pauses (ATR par trade) |
  |---|---|---|---|
  | BTC | 49 sur 885 | 37 | +0,134 → +0,135 |
  | ETH | 47 sur 839 | 42 | −0,193 → −0,207 |
  | SOL | 49 sur 862 | 28 | +0,091 → +0,108 |
  | AVAX | 48 sur 792 | 30 | +0,215 → +0,190 |
  | XRP | 47 sur 834 | 28 | +0,117 → +0,160 |

## 4. Écart (ticks du 2026-09-25 au 2026-10-05)

- [CODE] **Mesure de l'écart :**
  - Écart à l'ouverture de chaque barre M30 : médiane des ticks des 5 premières minutes, sinon le dernier tick de moins
    de 30 minutes.
  - Profil par demi-heure locale : New York, Francfort pour GER40.
  - Série au milieu (courtiers des cryptos) : la moitié de l'écart à l'entrée et l'autre moitié à la sortie.
  - Série au bid (barres FTMO, HistData) : un long paie l'écart à l'entrée, un short à la sortie.
- [OBS] **Écarts médians en bps :** US100 0,50 ; US30 0,48 ; GER40 0,84 ; GBPJPY 1,01, avec un pic de 10,5 au rollover ;
  or 0,99 ; WTI 8,61 ; Brent 7,09 ; BTC 0,12 ; ETH 2,23 ; SOL 2,50 ; XRP 9,99. Ils sont stables sur la période.

## 5. Swaps (fiches v2, bps du notionnel par nuit au dernier prix, coût positif)

| Actif | Type | Long | Short | Triple |
|---|---|---|---|---|
| Cryptos (BTC, ETH, SOL, XRP) | −30 % par an | +8,33 | +8,33 | vendredi |
| US100 | pips | +2,24 | −0,11 | vendredi |
| US30 | pips | +0,34 | +1,80 | vendredi |
| GER40 | pips | +1,78 | +0,02 | vendredi |
| Or | pips | +1,57 | +0,10 | mercredi |
| GBPJPY | pips | −0,15 | +1,04 | mercredi |
| WTI | pips | −5,48 | +24,83 | vendredi |
| Brent | pips | −5,82 | +26,32 | vendredi |

- [CODE] Un swap est compté à chaque rollover traversé : 17:00 New York, entrée avant et sortie à ou après. Le poids
  vaut 3 le jour triple et 0 le week-end ; pour les cryptos, le vendredi triple couvre le week-end. Le swap est imputé à
  la sortie.
- [HYP] **Ce que je n'ai pas pu vérifier :**
  - le rollover à 17:00 New York : cohérent avec la coupure des CFD de 20:50 à 22:05 UTC, mais non vérifié ;
  - la base de 360 jours des swaps en % ;
  - **l'unité des swaps du pétrole.** À la lettre (pip de 1 $), 25 bps par nuit en short, soit environ 90 % par an :
    invraisemblable comme simple financement. Une autre unité serait possible. Il faut le vérifier dans cTrader (fiche
    du symbole) ou par une position d'essai tenue une nuit. Seul le profil TradFi est touché, pas la Baseline crypto +
    or.

## 6. Commission (par côté)

- [OBS] Montants par côté :
  - cryptos : 0,0325 % du volume, soit 3,25 bps (6,5 bps l'aller-retour) ;
  - or : 0,0007 %, soit 0,07 bp ;
  - GBPJPY : 2,5 USD par lot, soit 0,19 bp au taux USD/JPY du 2025-12-31 (FRED) ;
  - indices et pétrole : rien.

## 7. Levier du compte d'essai (fiches)

- [OBS] **Niveaux relevés :** cryptos 1:1 ; indices, pétrole et or 1:15 ; GBPJPY 1:30.
- [OBS] **Écart avec D05.4 :** l'étalon « FTMO Swing » y retenait 1:2 pour les cryptos et 1:30 pour l'or, avec la marge
  plafonnée.
- [HYP] Le compte d'essai serait un compte Swing, auquel cas la marge plafonnée de D05 est trop large. Une marche dédiée
  (`levier_compte`) le mesurera.

## 8. Frictions par trade, fenêtre D05 (`couts_actifs_D05_1.csv`)

| Actif | Trades | Convention (bps) | FTMO : écart + commission + swap = total (bps) | Total en ATR (convention) | Avec rollover | Net par trade en ATR, convention → FTMO |
|---|---|---|---|---|---|---|
| BTC | 885 | 5 | 0,12 + 6,50 + 2,27 = 8,89 | 0,265 (0,159) | 20 % | +0,240 → +0,134 |
| ETH | 839 | 5 | 2,23 + 6,50 + 2,39 = 11,12 | 0,245 (0,115) | 21 % | −0,063 → −0,193 |
| SOL | 862 | 5 | 2,50 + 6,50 + 2,49 = 11,49 | 0,154 (0,068) | 23 % | +0,177 → +0,091 |
| AVAX (écart de SOL) | 792 | 5 | 2,50 + 6,50 + 2,84 = 11,84 | 0,164 (0,071) | 25 % | +0,308 → +0,215 |
| XRP | 834 | 5 | 9,98 + 6,50 + 2,62 = 19,10 | 0,374 (0,100) | 23 % | +0,391 → +0,117 |
| Or (HistData) | 532 | 4 | 1,02 + 0,14 + 0,77 = 1,92 | 0,117 (0,248) | 35 % | +0,112 → +0,243 |
| Or (barres FTMO) | 564 | 4 | 1,02 + 0,14 + 0,74 = 1,90 | 0,119 (0,258) | 32 % | −0,121 → +0,019 |

- [OBS] Sur les cryptos, les frictions FTMO valent 1,8 à 3,8 fois la convention. La commission (6,5 bps l'aller-retour)
  en est la plus grande part. Le swap pèse 2,3 à 2,8 bps en moyenne (8,3 bps par nuit ; 4 % des trades paient le
  vendredi triple).
- [OBS] Pour l'or, c'est l'inverse : FTMO coûte moins que la convention.
- [OBS] **Source de l'or.** Sur les barres FTMO, le brut vaut +0,14 ATR par trade, contre +0,36 sur HistData. Pourtant
  les entrées sont communes à 79-84 % (447) et l'ATR est voisin. L'effet de la source dépasse celui des frictions. Il
  est à examiner avant de lire la marche `or_ftmo`.

## 9. Prêt pour la session suivante

- [CODE] `envelope.portfolio` et `propfirm` acceptent un frais par trade.
- [CODE] `marketdata.ftmo` couvre la lecture, l'écriture, les écarts, le profil et les pauses.
- [CODE] `propfirm.frictions` couvre l'écart, la commission, les rollovers, les swaps et les pauses.
- [CODE] `experiments/D05_1/run_frictions_D05_1.py --baseline` : six marches, chacune ajoutant un facteur.
  1. convention : contrôle bloquant, doit redonner D05.6bis ;
  2. écart + commission ;
  3. swaps ;
  4. pauses ;
  5. or FTMO ;
  6. levier du compte = Baseline cTrader.
- **À trancher par le porteur :**
  - SAN et AVAX : relancer le cBot, ou garder AVAX sur l'écart de SOL ;
  - unité des swaps du pétrole ;
  - levier de référence (fiche du compte d'essai ou étalon de D05.4) ;
  - lecture de l'or (HistData ou barres FTMO).

## 10. Recoupement avec la page FTMO des symboles (2026-10-06, `ftmo_site_symboles_D05_1.json`)

- [OBS] **Les fiches cTrader concordent avec la page publique de FTMO** (points MetaTrader = 10^-digits) :
  - US100 −696,38 / +34,17 points, soit −6,96 / +0,34 ;
  - WTI +49,69 / −225,29 points, soit +0,050 / −0,225 $ par baril ;
  - Brent +60,98 / −275,78 ;
  - or −64,9 / −4,2 ;
  - GBPJPY +3,17 / −21,79 ;
  - cryptos −30 % / −30 %.
- [OBS] **Unité des swaps du pétrole confirmée.** Un short paie environ 25 bps par nuit : ce n'est plus une [HYP].
- [OBS] **Commissions données aller-retour sur la page :** cryptos 0,065 %, or 0,0014 %, GBPJPY 5 USD par lot. Celles de
  cTrader (0,0325 %, 0,0007 %, 2,5 USD) sont donc bien par côté.
- [OBS] **Levier « Swing » de FTMO :** cryptos et actions 1:1 ; indices, pétrole et or 1:15 ; FX 1:30. C'est celui du
  compte d'essai. L'étalon de D05.4 (cryptos 1:2, or 1:30) ne correspond pas au compte Swing ; la marche
  `levier_compte` est le compte réel.
- [OBS] **Maintenances crypto confirmées :** la page annonce des maintenances programmées le week-end, ce qui confirme
  les pauses du samedi.
- [OBS] **SAN = Banco Santander.** Le porteur l'a remplacé par META : swap −16,62 / −13,14 points, commission 0,004 %
  aller-retour, levier Swing 1:1, séance de 16:35 à 23:00 GMT+3.
