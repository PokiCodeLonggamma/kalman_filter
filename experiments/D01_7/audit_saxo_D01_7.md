# EXP-D01.7 — Test de Saxo OpenAPI (LIVE) comme source des barres de 30 min 2020-2025

- **Date :** 2026-10-01. Étape DATA uniquement : **aucun backtest**, RE-1 inchangée, aucune donnée de 2026 demandée.
- **Code :** `src/marketdata/saxo.py` (10 tests sans réseau), `experiments/D01_7/saxo_probe_D01_7.py`.
- **Rapports bruts :** `saxo_probe_D01_7_sim.json` (simulation), `saxo_probe_D01_7.json` (LIVE).
- **Séries :** `data/raw/saxo_<actif>_<cfd|fut>_30m.csv` (série de travail) et `_brut.csv` (champs reçus, intacts), ignorées par git ; leurs `.meta.json` sont versionnés.

## 1. Authentification

- **Flux :** OAuth 2 PKCE, documentation officielle Saxo. Passerelle `https://gateway.saxobank.com/openapi`, authentification `https://live.logonvalidation.net`.
- **Secrets :**
  - la clé d'application est dans la variable d'environnement `SAXO_APP_KEY` ; elle n'est jamais affichée, seules ses empreintes ont été comparées ;
  - le jeton vit en mémoire du processus seulement (20 min, rafraîchi).
- **Fait par le porteur sur le portail développeur :** compte démo, application SIM « AKF-TSOD017 », rattachement du compte LIVE, licence non commerciale acceptée, application LIVE « AKF-TSOD017-LIVE » (PKCE, trading non activé, approuvée).
- **Prérequis découvert, fait par le porteur :** activer les données de marché via l'API dans SaxoTrader (Profil → Autres → Accès Open API → Activer → Accepter).
  - Sans cet accord, `MarketDataViaOpenApiTermsAccepted = false`, et toutes les requêtes de graphique répondent 403.
  - Saxo désactive par défaut les données non Forex via l'API. Il ne s'agit pas d'un abonnement payant.

## 2. Instruments retenus (/ref/v1/instruments)

| Actif | Version | Symbol | UIC | AssetType | Description | ExchangeId (graphique) | Devise |
|---|---|---|---|---|---|---|---|
| US100 | CFD | USNAS100.I | 4912 | CfdOnIndex | US Tech 100 NAS | NASDAQ | USD |
| US100 | future | NQc1 | 4060 | ContractFutures | E-mini NASDAQ-100 - continuous | CME | USD |
| US2000 | CFD | US2000cont | 133720 | CfdOnFutures | US 2000 continuous | CME | USD |
| US2000 | future | RTYc1 | 7327701 | ContractFutures | E-mini Russell 2000 - continuous | CME | USD |
| WTI | CFD | OILUScont | 22514 | CfdOnFutures | US Crude, continuous | NYMEX | USD |
| WTI | future | CLc1 | 4034 | ContractFutures | Light Sweet Crude Oil (WTI) - Continuous | NYMEX | USD |
| Cuivre | CFD | COPPERUScont | 37264 | CfdOnFutures | US Copper continuous | COMEX | USD |
| Cuivre | future | HGc1 | 4048 | ContractFutures | Copper - continuous | COMEX | USD |

- `TradableAs` vaut `CfdOnIndex` pour USNAS100.I ; il n'est pas renseigné pour les séries continues, qui servent aux graphiques, les positions passant par les contrats à échéance.
- **Choix documenté :** pour chaque actif, la série continue qui couvre 2020.
  - Les CFD continus sur future (`…cont`) existent depuis 2003 à 2012.
  - Les CFD à échéance (OILUSDEC26, US2000DEC26, etc.) n'ont d'historique que depuis leur cotation en 2026.
  - `USNAS100cont` (CFD continu sur future) ne commence qu'en avril 2025 ; c'est donc le CFD sur l'indice au comptant qui est retenu.
  - Pour les futures : contrat continu, place d'origine, hors micro. Le Brent, choisi par erreur au premier passage, est écarté.

## 3. Historique (Horizon = 30)

- **FirstSampleTime :** USNAS100.I et NQc1 2003-10-30, OILUScont et CLc1 2003-10-30, COPPERUScont et HGc1 2003-10-31, US2000cont 2012-02-29, RTYc1 2017-07-09.
- **Modes UpTo et From :** valeurs identiques sur les barres communes.
- **Pagination :** pages de 1 200 barres maximum, contiguës, sans chevauchement.
- **Bloc de test :** réécrit deux fois, même empreinte, donc reproductible.
- **Option ExtendedHoursEnabled :** sans effet sur ces instruments.

| Série | Barres | Première → dernière (UTC) | Pas de 30 min | Reprise quotidienne (New York) | Doublons, OHLC incohérents | Prix ≤ 0 |
|---|---|---|---|---|---|---|
| US100 CFD | 69 805 | 2020-01-01 23:00 → 2025-12-31 21:30 | 97,8 % | 18:00 | 0 ; 0 | 0 |
| NQc1 | 70 667 | 2020-01-01 23:00 → 2025-12-31 21:30 | 97,8 % | 18:00 | 0 ; 0 | 0 |
| US2000 CFD | 61 499 | 2020-01-02 02:01 → 2025-12-31 21:31 | 97,5 % | **21:01** | 0 ; 0 | 0 |
| RTYc1 | 70 618 | 2020-01-01 23:00 → 2025-12-31 21:30 | 97,8 % | 18:00 | 0 ; 0 | 0 |
| WTI CFD | 70 774 | 2020-01-01 23:01 → 2025-12-31 21:31 | 97,8 % | 18:01 | 0 ; 0 | **2** (2020-04-20) |
| CLc1 | 70 138 | 2020-01-01 23:00 → 2025-12-31 21:30 | 97,3 % | 18:00 | 0 ; 0 | **25** (2020-04-20/21) |
| Cuivre CFD | 70 855 | 2020-01-01 23:01 → 2025-12-31 21:31 | 97,8 % | 18:01 | 0 ; 0 | 0 |
| HGc1 | 70 739 | 2020-01-01 23:00 → 2025-12-31 21:30 | 97,8 % | 18:00 | 0 ; 0 | 0 |

- **Horodatage :** UTC (format ISO « Z »), début de barre. Les CFD sur future sont décalés d'une minute (:01 et :31) : c'est leur ouverture de séance, à 18:01 heure de New York.
- **Séances :** 23 h sur 24, 5 jours sur 7, pause de 17:00 à 18:00 heure de New York, ce que confirme le calendrier annoncé par Saxo.
  - Exception : le CFD US2000 est fermé de 17:00 à 21:00 heure de New York, d'où environ 13 % de barres en moins.
- **Trous :** uniquement les pauses quotidiennes, les week-ends et les fêtes (plus long : 77 h).

## 4. Couverture 2020-01-01 → 2025-12-31

Les huit séries couvrent toute la période (2020 à 2025 ; environ 10 200 à 11 800 barres par an). Aucune source n'a été mélangée.

## 5. Type de prix

- **CFD :** OHLC bid et ask (OpenBid … CloseBid, OpenAsk … CloseAsk), sans dernier prix ni volume.
  - La série de travail prend le **bid**, comme HistData ; l'ask reste dans la série brute.
  - Écart de clôture médian : US100 0,9 bp, US2000 3,1, WTI 7,4, cuivre 14,2 bps.
- **Futures :** OHLC du **dernier prix traité** (Open, High, Low, Close) et Volume. Le champ `Interest` vaut 0 : ce n'est pas l'open interest.
- **FX :** non testé ici (GBPJPY vient de HistData). La documentation Saxo décrit des OHLC bid et ask pour le Forex.

## 6. Données de marché et coûts

- **Historique :** complet sans abonnement payant, une fois l'accès Open API activé.
- **Délai :** `DelayedByMinutes` vaut 0 pour les CFD et 10 pour les futures. Le temps réel des futures demanderait un abonnement de bourse, ce qui est sans effet sur 2020-2025.
- **Coût réaliste des CFD :** au moins leur écart (de 1 à 14 bps), plus le financement des positions tenues la nuit. Celui des futures, commissions et ticks, n'est pas mesuré ici.

## 7. Roulements des séries continues : non ajustées

- **NQc1 contre l'indice au comptant (USNAS100.I) :** l'écart entre les deux saute de **+90 à +136 bps le troisième vendredi de chaque échéance trimestrielle**, sur les 14 échéances de 2022 à 2025.
  - Saxo raccorde donc les contrats bruts **à leur échéance**, sans ajustement ni règle d'open interest. Le saut vaut l'écart entre échéances.
- **HGc1 et le CFD cuivre :** sauts de +138 à +190 bps aux dates de roulement (fin août, fin novembre).
- **CLc1 et le CFD WTI :** le plus grand écart de chaque mois vaut environ 90 à 100 bps, contre un écart médian de 0 à 1 bp.
- **RTYc1 :** même construction, ampleur des sauts à quantifier.
- **Conséquence pour RE-1 :** chaque roulement crée un faux gap de 2 à 6 ATR et un faux PnL pour un trade qui l'enjambe. Ce n'est pas la série « sans faux gaps », ajustée par ratio, que demande D01.7.

## 8. Décision

| Actif | CFD | Future |
|---|---|---|
| US100 | **PASS** : complet, propre, sans roulement | **PARTIAL** : roulements non ajustés |
| US2000 | **PARTIAL** : séance réduite, roulements à vérifier | **PARTIAL** : roulements non ajustés |
| WTI | **PARTIAL** : prix ≤ 0 le 2020-04-20, roulements, écart de 7,4 bps | **PARTIAL** : 25 prix ≤ 0, roulements mensuels |
| Cuivre | **PARTIAL** : roulements, écart de 14 bps | **PARTIAL** : roulements non ajustés |

**Décision globale : Saxo est exploitable pour D01.7, sous condition.**
- C'est la seule source qui a fourni localement les huit séries complètes sur 2020-2025, auditables de bout en bout.
- Une seule est utilisable telle quelle : le CFD sur l'indice US100.
- Les sept autres demandent un **ajustement des roulements par ratio**, à construire nous-mêmes à partir des dates d'échéance et de l'écart au roulement.
- Le WTI demande en plus une décision sur avril 2020 : démarrer en mai 2020, ou exclure l'actif.
- Aucun backtest avant validation de ces choix.
