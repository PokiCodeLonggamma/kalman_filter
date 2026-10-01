# EXP-D01.7 — Univers redéfini : disponibilité et couverture chez Saxo (30 min, 2020-2025)

- **Date :** 2026-10-01. Étape DATA uniquement : **aucun backtest**, RE-1 inchangée, aucune donnée de 2026 demandée.
- **Décisions du porteur (2026-10-01) :**
  - abandon des futures et des CFD continus, pour éviter toute gestion de roulements (constats en annexe 9 de
    `audit_saxo_D01_7.md`) ;
  - univers : US100 CFD, GBPJPY, Germany 40, Japan 225, EU Stocks 50, US 30 et XAGUSD ;
  - **Japan 225 remplacé par Hong Kong 50**, car absent chez Saxo (§1) ;
  - en option, des CFD sur ETF : SMH et URA demandés par le porteur ; TLT, USO et GDX choisis par l'agent.
- **Code :** `experiments/D01_7/saxo_univers_D01_7.py`, qui reprend la connexion et les tests de `saxo_probe_D01_7.py`.
- **Rapports bruts :**
  - `saxo_univers_D01_7.json` : sondage, sur trois connexions du porteur. La première s'est arrêtée après 5 téléchargements, sur un défaut du script avec les CFD sur ETF. La deuxième est complète. La troisième, ciblée, porte sur URA.
  - `univers_D01_7.json` : contrôles hors ligne.
- **Séries :** `data/raw/saxo_<clé>_30m.csv` et `_brut.csv`, ignorées par git ; leurs `.meta.json` sont versionnés.
- **Règle de sélection fixée avant le sondage :**
  - indices : CfdOnIndex seulement, c'est-à-dire un CFD sur l'indice au comptant, sans échéance ;
  - argent et GBPJPY : FxSpot ;
  - ETF : CfdOnEtf au ticker exact ;
  - un instrument absent est signalé, jamais remplacé en silence.

## 1. Instruments retenus

| Actif | Symbole | UIC | Type | Description | 30 min depuis | Délai |
|---|---|---|---|---|---|---|
| US100 | USNAS100.I | 4912 | CfdOnIndex | US Tech 100 NAS | 2003-10-30 | 0 |
| US30 | US30.I | 4911 | CfdOnIndex | US 30 Wall Street | 2003-10-31 | 0 |
| GER40 | GER40.I | 4910 | CfdOnIndex | Germany 40 | 2003-10-31 | 0 |
| EU50 | EU50.I | 16753 | CfdOnIndex | EU Stocks 50 | 2005-08-22 | 0 |
| HK50 | HK50.I | 47624 | CfdOnIndex | Hong Kong 50 | 2010-07-05 | 0 |
| XAGUSD | XAGUSD | 8177 | FxSpot | Silver/US Dollar | 2004-03-16 | 0 |
| GBPJPY | GBPJPY | 26 | FxSpot | British Pound/Japanese Yen | 2002-09-25 | 0 |
| *ETF* TLT | TLT:xnas | 3441903 | CfdOnEtf | iShares 20+ Year Treasury Bond ETF | 2016-02-02 | 15 min |
| *ETF* USO | USO:arcx | 35959 | CfdOnEtf | United States Oil ETF | 2008-11-25 | 15 min |
| *ETF* SMH | SMH:xnas | 15709451 | CfdOnEtf | VanEck Semiconductor ETF | 2019-12-11 | 15 min |
| *ETF* URA | URA:arcx | 49142 | CfdOnEtf | Global X Uranium ETF | 2010-11-05 | 15 min |
| *ETF* GDX | GDX:arcx | 35663 | CfdOnEtf | VanEck Gold Miners ETF | 2006-05-31 | 15 min |

- **Japan 225 :** aucun CfdOnIndex ne répond à « Japan 225 », « JP225 » ou « Nikkei » pour ce compte, alors que le compte
  est autorisé à trader les CfdOnIndex. Hong Kong 50 le remplace, sur décision du porteur.
- **NLR, retenu par erreur à la place d'URA lors de la deuxième passe :**
  - le motif « uranium » acceptait aussi NLR (VanEck Uranium and Nuclear), et la règle du plus ancien historique l'a
    préféré ;
  - corrigé : un ticker demandé doit maintenant correspondre exactement, sans repli sur un autre candidat ;
  - URA a été retéléchargé lors de la troisième passe ; NLR est conservé, renommé, à titre déclaré.
- **Délai :** les 15 min des ETF sont le délai des cotations en temps réel, sans abonnement de bourse. Il est sans effet
  sur 2020-2025.

## 2. Couverture et intégrité, du 2020-01-01 au 2025-12-31

| Actif | Barres | Première → dernière (UTC) | Pas de 30 min | Barres par an | Doublons ; OHLC incohérents ; prix ≤ 0 | Écart acheteur-vendeur P50 / P90 |
|---|---|---|---|---|---|---|
| US100 | 69 805 | 2020-01-01 23:00 → 2025-12-31 21:30 | 97,8 % | 11 284 à 11 837 | 0 ; 0 ; 0 | 0,9 / 1,5 bp |
| US30 | 69 729 | 2020-01-01 23:00 → 2025-12-31 21:30 | 97,8 % | 11 266 à 11 837 | 0 ; 0 ; 0 | 1,4 / 1,9 bp |
| GER40 | 62 430 | 2020-01-02 00:00 → 2025-12-30 20:30 | 97,5 % | 10 331 à 10 485 | 0 ; 0 ; 0 | 2,2 / 3,7 bps |
| EU50 | 62 370 | 2020-01-02 00:00 → 2025-12-30 20:30 | 97,5 % | 10 327 à 10 468 | 0 ; 0 ; 0 | 4,8 / 6,1 bps |
| HK50 | 47 025 | 2020-01-02 01:00 → 2025-12-31 03:30 | 90,8 % | 7 751 à 7 996 | 0 ; 0 ; 0 | 6,1 / 7,9 bps |
| XAGUSD | 70 962 | 2020-01-01 23:00 → 2025-12-31 21:30 | 97,8 % | 11 780 à 11 869 | 0 ; 0 ; 0 | 6,6 / 10,1 bps |
| GBPJPY | 76 607 | 2020-01-01 18:00 → 2025-12-31 21:30 | 99,6 % | 12 730 à 12 806 | 0 ; 0 ; 0 | 2,5 / 4,0 bps |
| TLT | 19 532 | 2020-01-02 14:30 → 2025-12-31 20:30 | 92,3 % | 3 232 à 3 276 | 0 ; 0 ; 0 | — (prix traités) |
| USO | 19 531 | idem | 92,3 % | 3 232 à 3 276 | 0 ; 0 ; 0 | — |
| SMH | 19 532 | idem | 92,3 % | 3 232 à 3 276 | 0 ; 0 ; 0 | — |
| URA | 19 479 | idem | 92,0 % | 3 225 à 3 269 | 0 ; 0 ; 0 | — |
| GDX | 19 532 | idem | 92,3 % | 3 232 à 3 276 | 0 ; 0 ; 0 | — |
| *NLR (erreur)* | 12 146 | idem | 74,5 % | **519** (2020) à 3 232 | 0 ; 0 ; 0 | — |

- **Vérifications de téléchargement, sur les 12 instruments :**
  - modes UpTo et From identiques sur les barres communes ;
  - blocs de test réécrits deux fois avec la même empreinte ;
  - pages contiguës, sans doublon ni valeur contradictoire ;
  - aucune barre de 2026.
- **Type de prix :**
  - CFD sur indice, argent et GBPJPY : OHLC acheteur et vendeur ; la série de travail prend le **bid**, l'ask reste dans
    la série brute ;
  - CFD sur ETF : **dernier prix traité** OHLC et volume, sans cours acheteur ni vendeur.
- **ETF :**
  - historique **ajusté des splits**, vérifié sur USO : il cote 21,20 $ le 2020-04-23, soit 8 fois le prix d'alors
    (environ 2,65 $), avant son regroupement 1 pour 8 du 2020-04-28, et aucun saut ne marque le regroupement ;
  - dividendes non ajustés : les baisses aux dates de détachement sont réelles, de quelques dizaines de bps.

## 3. Séances (heure de New York)

- **US100 et US30 :**
  - 23 h sur 24, pause de 17:00 à 18:00, reprise le dimanche à 18:00 ;
  - **jusqu'en 2021, le CFD fermait à 16:00** (pause de 16:00 à 18:00). L'heure de 16:00 à 17:00 est cotée depuis 2022,
    d'où environ 11 300 puis 11 800 barres par an.
- **GER40 et EU50 :** de 02:00 à 22:00 heure de Berlin, soit une reprise à 19:00 ou 20:00 à New York ; pause de 3,5 à
  4,5 h par jour.
- **HK50 :** séances de la bourse de Hong Kong, environ 31 barres par jour :
  - matin de 09:15 à 12:00, après-midi de 13:00 à 16:30, nuit de 17:15 à 03:00, heure de Hong Kong ;
  - pauses de 1 h, de 45 à 90 min, et de 6 h 30.
- **XAGUSD :** 23 h sur 24, pause de 17:00 à 18:00, reprise le dimanche à 18:00.
- **GBPJPY :** cotation continue en semaine (99,6 % de pas de 30 min) ; Saxo ouvre le dimanche dès 13:00-15:00 à New
  York, HistData à 17:00.
- **ETF :** séance américaine seule, de 09:30 à 16:00, soit 13 barres par jour.
  - Saxo ne sert pas les heures étendues pour ces graphiques : la même requête sur SMH renvoie des barres identiques,
    avec ou sans `ExtendedHoursEnabled`.
  - Structure de SPY et XLE en D01 bis : un trade de 26 barres traverse au moins une nuit.

## 4. Contrôles particuliers

- **Aucun changement de contrat caché dans les CFD sur indice.**
  - Méthode : sauts en séance supérieurs à 10 fois la médiane, et au moins à 5 bps, par jour d'échéance des futures
    contre les autres jours.
  - US100 : 0,04 contre 0,05.
  - US30 : 0,04 contre 0,04.
  - GER40 : 0,13 contre 0,08 (3 sauts : deux le 2020-03-20, un le 2023-03-17).
  - EU50 : 0,17 contre 0,04 (4 sauts, dont 3 sous 8 bps ; le maximum de −77 bps date du 2020-03-20 à 15:00 heure de
    Berlin).
  - HK50 : 0,03 contre 0,02, sur les échéances mensuelles (avant-dernier jour ouvré, fêtes de Hong Kong non modélisées).
  - Aucun saut ne tombe à l'heure de règlement des futures ; ce sont des sauts de marché.
- **Les plus grands sauts sont des événements réels**, aucune correction :
  - mars 2020 ;
  - la réouverture de HK50 le 2025-04-07 (−745 bps, droits de douane) ;
  - XAGUSD le 2021-01-31 (+522 bps) ;
  - XAGUSD le 2025-12-28 (±239 bps en séance, dimanche soir peu liquide, l'argent autour de 80 $).
- **Indices de prix :** US100, US30, EU50 et HK50 baissent réellement aux dates de détachement des dividendes. Le
  détenteur du CFD reçoit un ajustement en espèces, qui n'apparaît pas dans le prix. Non traité ; GER40 (DAX) est un
  indice de rendement total.
- **GBPJPY, Saxo contre HistData :**
  - corrélation des rendements de 30 min de 0,993, écart de niveau médian de −0,7 bp, P90 de 1,1 bp ;
  - Saxo comble le trou de HistData en 2023 : 12 730 barres contre 10 785 ;
  - 3 555 barres Saxo sont absentes de HistData (trous de 2023 et dimanches précoces) ; 3 barres HistData sont absentes
    de Saxo.
- **NLR, sélectionné par erreur :** illiquide, avec 519 barres en 2020 et 74,5 % de pas de 30 min. Inutilisable.
- **URA :** 51 barres manquantes en 2020, aux moments sans transaction.

## 5. Décision

| Actif | Verdict | Motif |
|---|---|---|
| US100 | **PASS** | déjà validé ; complet, propre, sans roulement |
| US30 | **PASS** | complet, propre, aucun raccord caché |
| GER40 | **PASS** | complet, propre, aucun raccord caché |
| EU50 | **PASS** | complet, propre, aucun raccord caché ; écart de 4,8 bps |
| HK50 | **PASS** | complet, propre ; trois séances par jour ; écart de 6,1 bps |
| XAGUSD | **PASS** | complet, propre ; écart de 6,6 bps |
| GBPJPY (Saxo) | **PASS** | complet ; concorde avec HistData ; 2023 complet |
| GBPJPY (HistData) | PARTIAL | trous de 2023 (14 % de l'année) |
| TLT, USO, SMH, URA, GDX | **PASS (séance américaine)** | données complètes ; ETF en séance seule, sans heures étendues |
| Japan 225 | FAIL | absent des CfdOnIndex ; remplacé par HK50 |
| NLR | FAIL | erreur de sélection, illiquide ; hors univers |

**Décision globale :** l'univers principal est complet chez Saxo, avec HK50 à la place de Japan 225, ainsi que les 5 ETF
en option. Les données sont validées pour le backtest de D01.7, sous trois choix du porteur :

1. **Source de GBPJPY.** Recommandé : Saxo, complet et de même source que le reste, à la place de HistData.
2. **Coûts aller-retour, à fixer avant le backtest.**
   - Proposition, chaque actif lu en 0 (brut), à l'écart médian mesuré, et à un coût principal égal au plus grand de
     4 bps et de l'écart P90 arrondi au point supérieur.
   - Coût principal, par actif : US100 4 ; US30 4 ; GER40 4 ; EU50 7 ; HK50 8 ; XAGUSD 11 ; GBPJPY 4 ; ETF 4.
   - Pour les ETF, il s'agit de la convention de D01 : écart non mesurable sur des prix traités, commission Saxo non
     mesurée.
   - Le financement des positions tenues la nuit n'est pas compté : limite déclarée.
3. **Les 5 ETF dans D01.7 ou non.** Ce sont des actifs de séance comme SPY et XLE.
