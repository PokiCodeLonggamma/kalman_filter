# PASSATION — D05.1 : l'objectif stratégique (sauver la piste 2 par le portefeuille)

*Rédigée le 2026-10-06 à la clôture de la session « données FTMO, frictions et profil TradFi ». Direction Prop Firm
(D05), dépôt `#KalmanFilter`, branche `main`.*

*À lire avec `CLAUDE.md`, `experiments/D05_1/narratif_frictions_D05_1.md`, `experiments/D05_1/rapport_profil_D05_1.md`
et `experiments/D05_6bis/rapport_D05_6bis.md`.*

*Les données sont réglées : la session suivante ne traite que la stratégie.*

## 0. En une minute

- **Étalon :** compte FTMO Swing de 100 000.
  - Challenge : 9 % puis 5 % ; perte du jour de 5 % à minuit CET/CEST ; perte totale de 10 %, statique ; au moins
    4 jours.
  - Compte financé : 80 % des gains, retrait tous les 14 jours, 540 € remboursés au premier retrait.
  - Moteur : `propfirm` (D05.4 à D05.8).
- **Stratégie :** RE-1 version finale, figée : RE-1 et un stop catastrophe à 4 ATR (`strategy.final`).
  - Six actifs : BTC, ETH, SOL, AVAX, XRP, or.
  - Fenêtre commune 2021-10-01 → 2026-10-01 (AVAX coté depuis le 2021-09-30).
- **Pistes :**
  - référence : 0,20 × 0,20 %/ATR ;
  - **piste 1 : 0,20 × 0,25**, verrouillée par le porteur, par sécurité ;
  - **piste 2 : 0,25 × 0,25, « Burn & Churn pur »** : rachat immédiat (540 €) au minuit qui suit chaque échec.
  - Aucun filtre d'achat.
- **Ce qu'elles valent dans D05.6bis.** Conditions : frais conventionnels de 5 bps (or 4 bps), marge plafonnée à 1:2
  pour les cryptos et 1:30 pour l'or.

  | | Réussite du challenge | Sans 2026 | Délai médian | Suite à 24 mois |
  |---|---|---|---|---|
  | Challenge à 0,20 (référence, piste 1) | 58,8 % | 52,3 % | 68 j | référence +41,4 k€ ; piste 1 +48,2 k€ |
  | Challenge à 0,25 (piste 2) | 51,0 % | 44,2 % | 41 j | +50,9 k€ [44,4 ; 57,3] |

### L'objectif stratégique (le porteur, 2026-10-06)

> « Le Vrai Objectif Stratégique (L'Endgame) : Sauver la Piste 2 ». La piste 2 écrase tout en suite de tentatives ; son
> seul point faible est son taux d'échec en challenge (hivers crypto). Mission de D05.1 : de l'optimisation de
> portefeuille, pas une simple addition d'actifs. Lisser la courbe d'équité (réduire la variance globale) pour faire
> remonter la réussite du challenge de la piste 2 au-dessus de 60-65 % ; si oui, la piste 2 devient le standard
> définitif. D05.1 peut aussi améliorer la stratégie retenue par la gestion de portefeuille et de nouveaux actifs.

- **Axes du porteur pour l'inclusion :**
  - décorrélation temporelle : les « cygnes noirs » TradFi tombent-ils quand la crypto stagne ?
  - exposition simultanée (« portfolio heat ») face à la perte du jour de 5 % ;
  - allocation par kurtosis : même risque (0,25) pour la TradFi, ou risque modulé selon l'épaisseur des queues.
- **Plan validé, dans cet ordre strict :**
  1. **Baseline cTrader** des pistes 1 et 2 ;
  2. **profil TradFi** (RE-1 pure, coûts FTMO) : fait, sauf META (§5) ;
  3. **inclusion** dans le portefeuille.
- Le porteur statue sur la méthode d'inclusion après les résultats **descriptifs** des étapes 1 et 2. Les conclusions
  de D01.7 sont **ignorées comme filtre** (2026-10-05).

## 1. Gouvernance (voir `CLAUDE.md`)

- **Aucun calcul de recherche, aucune modification, aucun push sans GO explicite.** Le dépôt GitHub est public : pousser
  revient à publier. Commits locaux propres.
- **Intouchables :**
  - RE-1 figée ; `src/indicator/` sanctuarisé ; baseline Pine gelée ;
  - ne jamais supprimer, renommer ni déplacer un ancien dossier.
- **Réserve :** ETH, XRP et 2026 sont lus depuis D04, sur décision du porteur, mais **seulement dans un bloc
  `reserve.levee(motif)`** ; hors du bloc, les gardes tronquent au 2026-01-01.
- **Accès et confidentialité :**
  - ne jamais demander de clé ni de jeton dans le chat ;
  - aucune donnée personnelle saisie par l'agent ;
  - les fichiers Sniper (`prompts/sniper/`, `prompts/init_d3_sniper.md`, `prompts/Piste complémentaire_sniper.md`)
    restent hors des commits.
- **Méthode :**
  - cadrage en 4 champs avant tout test : QUESTION / DONNÉES / MÉTHODE / CRITÈRE DE LECTURE, avec ce que ça ne permet
    pas de conclure ;
  - **aucun critère a priori** ;
  - OFAT ;
  - tableau des 8 métriques (PnL et MDD à 0,25 %/ATR et à 1x) ;
  - frais réels dès la première barre ;
  - balises [CODE] / [OBS] / [HYP] ;
  - chiffres du porteur recalculés.
- **Forme des réponses :** en français, courtes et denses, sans flatterie ; le porteur se tutoie.

## 2. État du dépôt (clôture du 2026-10-06)

- origin/main = `b020961`. **Commits locaux de D05.1, non poussés** (push sur GO), de `2eb5e81` au commit de cette
  passation :
  - correction horaire ;
  - cBot v1 à v3 ;
  - frais par trade ;
  - lecteur FTMO et frictions ;
  - pauses ;
  - audit ;
  - échelle de la Baseline ;
  - frictions mesurées ;
  - profil TradFi ;
  - page FTMO ;
  - décisions.
- **Tests :** `python -m pytest -q` → 456 réussis, 2 ignorés (≈ 2 min 30).
- **Console Windows en cp1252 :** lancer les scripts avec `PYTHONIOENCODING=utf-8`.

## 3. Données (prêtes)

### 3.1 Sources retenues (porteur)

| Actifs | Prix | Frictions |
|---|---|---|
| Cryptos du portefeuille (BTC, ETH, XRP ; SOL, AVAX) | séries des courtiers de D05 (Bitstamp ; Coinbase), `D041.load_all()` dans un bloc `levee` | FTMO |
| Hors crypto (or, US100, US30, GER40, GBPJPY, WTI, Brent, META) | **barres FTMO**, sans complément Saxo | FTMO |

- **Or :** HistData dans D05 ; barres FTMO dans la Baseline (marche `or_ftmo`) et dans le profil TradFi.
- **Univers :**
  - SAN (= Banco Santander) **remplacé par META** ;
  - **AVAX gardé** : son remplacement est mis de côté par le porteur.

### 3.2 Fichiers FTMO (hors Git, `data/raw/*`)

- **Exports du cBot `experiments/D05_1/cbot/AkfExportFtmo.cs`** (lancé par le porteur ; aucun ordre) :
  - `data/raw/ftmo/export_2026-10-06/` (v1) ;
  - `…_v2/` (fiches complètes) ;
  - `…_v3/` (META, AVAUSD, cryptos candidates, fiches et liste à jour).
  - Chaque export contient bougies M30 (UTC, bid), ticks bid/ask des 10 derniers jours et fiches. La liste compte
    363 noms, dont 196 actifs.
- **Séries au schéma de `load_ohlc`** (`run_frictions_D05_1.py --import`) : `data/raw/ftmo/ftmo_<clé>_30m.csv` et leur
  `.meta.json`. Empreintes dans `experiments/D05_1/import_ftmo_D05_1.json`.

| Clé | Symbole FTMO | Première barre | Remarque |
|---|---|---|---|
| US100, US30, GER40, WTI, Brent | `US100.cash`, `US30.cash`, `GER40.cash`, `USOIL.cash`, `UKOIL.cash` | 2020-11-08 | |
| XAU | `XAUUSD` | 2020-05-06 | |
| GBPJPY | `GBPJPY` | 2020-04-01 | |
| META | `META` | **2025-01-27** | 5 505 barres ; séance US de 13:35 à 20:00 UTC |
| BTC, ETH, XRP | `BTCUSD`, `ETHUSD`, `XRPUSD` | 2020-07 | calendrier des pauses, recoupement |
| SOL | `SOLUSD` | 2025-04-17 | idem |
| AVAX | `AVAUSD` | 2021-10-31 | idem |
| Cryptos candidates | `DOGEUSD`, `LNKUSD` (2021-09) ; `AAVUSD` (2024-01) ; `UNIUSD`, `XLMUSD` (2024-12) | | gardées pour un remplacement futur d'AVAX |

- **Vérification (`experiments/D05_1/audit_ftmo_D05_1.md`) :**
  - corrélation des rendements de 30 min de 0,98 à 0,998 avec Saxo, HistData, Bitstamp et Coinbase (WTI : 0,93) ;
  - décalage nul partout (UTC) ;
  - niveau à +0,5 à +2,3 bps hors crypto, −4 à −18 bps sur les cryptos (bid FTMO).
- **Page FTMO des symboles (`experiments/D05_1/ftmo_site_symboles_D05_1.json`) :** les fiches cTrader concordent. Les
  commissions de cTrader sont par côté. Le levier Swing est de 1:1 pour les cryptos et les actions, 1:15 pour les indices,
  le pétrole et l'or, 1:30 pour le FX. Les maintenances crypto du week-end sont programmées.
- **Open API :** l'application « AKF-TSO Research Data » (ID 42882) reste « Submitted ». Elle n'est plus nécessaire.

## 4. Frictions FTMO (`experiments/D05_1/narratif_frictions_D05_1.md`)

| Actif | Écart médian (bps) | Commission par côté (bps) | Swap par nuit, long / short (bps) | Jour triple | Levier Swing |
|---|---|---|---|---|---|
| BTC ; ETH ; SOL ; AVAX ; XRP | 0,1 ; 2,2 ; 2,5 ; **18,3** ; 10,0 | 3,25 | +8,33 / +8,33 (−30 %/an) | vendredi | 1:1 |
| Or | 1,0 | 0,07 | +1,57 / +0,10 | mercredi | 1:15 |
| US100 ; US30 ; GER40 | 0,5 ; 0,5 ; 0,8 | 0 | +2,24 / −0,11 ; +0,34 / +1,80 ; +1,78 / +0,02 | vendredi | 1:15 |
| GBPJPY | 1,0 (10,5 au rollover) | 0,19 | −0,15 / +1,04 | mercredi | 1:30 |
| WTI ; Brent | 8,6 ; 7,1 | 0 | −5,5 / +24,8 ; −5,8 / +26,3 (confirmé par FTMO) | vendredi | 1:15 |
| META | 5,8 | 0,20 | +2,23 / +1,77 | vendredi | 1:1 |

- **Modèle (`propfirm.frictions.couts_trades`)** : bps du notionnel, prélevés à la sortie.
  - Écart par demi-heure locale (New York ; Francfort pour GER40).
  - Série au milieu (cryptos des courtiers) : moitié de l'écart à l'entrée, moitié à la sortie. Série au bid (barres
    FTMO, HistData) : un long paie l'écart à l'entrée, un short à la sortie.
  - Commission des deux côtés.
  - Swap à chaque rollover traversé (17:00 New York ; poids 3 le jour triple, 0 le week-end).
- **Pauses des cryptos (`ajuster_pauses`)** :
  - une entrée pendant une pause est abandonnée ;
  - une sortie ou un stop pendant une pause s'exécute à la réouverture ;
  - calendrier propre à chaque actif sur son historique FTMO, celui de BTC avant.
- [OBS] **Frictions par trade, fenêtre D05** : BTC 8,9 bps ; ETH 11,1 ; SOL 11,5 ; **AVAX 27,7** ; XRP 19,1 ; or 1,9.
  La convention était de 5 bps (or 4).
  - Net par trade, convention → FTMO : BTC +0,240 → +0,134 ATR ; ETH −0,063 → −0,193 ; SOL +0,177 → +0,091 ;
    **AVAX +0,308 → −0,009** ; XRP +0,391 → +0,117 ; or (HistData) +0,112 → +0,243.
  - **Attendu :** une Baseline cTrader nettement sous D05.6bis.
- **Hypothèses ouvertes :**
  - rollover à 17:00 New York ;
  - base de 360 jours des swaps en % ;
  - écarts mesurés sur dix jours de 2026, appliqués à toute la période ;
  - swap imputé à la sortie ;
  - stop franchi pendant une pause exécuté à la réouverture ;
  - une partie des trous du samedi seraient propres à chaque symbole (AVAX : 17 entrées abandonnées avec son calendrier,
    48 avec celui de BTC).

## 5. Résultats acquis

- **Étape 1, frictions :** §4. La Baseline elle-même n'est pas lancée.
- **Étape 2, profil TradFi** (`experiments/D05_1/rapport_profil_D05_1.md`) : RE-1 figée sur les barres FTMO, frictions
  réelles, de 2020-04/11 à 2026-10.
  - Espérance nette (ATR) : or +0,019 ; US100 −0,038 ; US30 −0,108 ; GER40 +0,086 ; GBPJPY +0,006 ; WTI −0,311 ;
    Brent −0,394.
  - PnL à 0,25 %/ATR : +8,6 % ; +2,3 % ; −8,1 % ; +3,2 % ; +3,9 % ; −40 % ; −41 %.
  - Même forme que BTC, en plus petit :
    - net médian de −1,0 à −1,8 ATR ;
    - trades à +5 ATR ou plus : 8,5 à 14,6 par an, contre 17,8 pour BTC ;
    - tout devient négatif sans les 1 % meilleurs trades.
  - Corrélation mensuelle avec le panier crypto de −0,15 à +0,11, sauf le WTI (−0,43). Les mois où le panier perd,
    US30 et GER40 gagnent (+10,2 % et +8,1 %).
  - **META non mesuré** : historique FTMO depuis le 2025-01-27 seulement.
  - [OBS] **Or :** sur les barres FTMO, son brut est plus faible que sur HistData (fenêtre D05 : +0,14 contre +0,36 ATR,
    pour 447 entrées communes). C'est à examiner.

## 6. Code

| Fichier | Rôle | Tests |
|---|---|---|
| `src/envelope/portfolio.py` | `Leg.cost` scalaire ou un frais par trade ; `leg_costs` | `tests/test_couts_par_trade.py` (5) |
| `src/propfirm/moteur.py`, `blocs.py` | frais de chaque trade ; frais de sortie du trade ouvert dans l'objectif | idem |
| `src/marketdata/ftmo.py` | lecture des bougies (tronquées au 2026-01-01 hors levée), des ticks (levée exigée) et des fiches ; écriture des séries ; écarts à l'ouverture des barres ; profil par demi-heure ; `pauses_cotation` | `tests/test_marketdata_ftmo.py` (10) |
| `src/propfirm/frictions.py` | `jours_swap`, `nuits`, `swap_bps`, `commission_bps`, `ecart_trades`, `couts_trades`, `ajuster_pauses` | `tests/test_propfirm_frictions.py` (25) |
| `experiments/D05_1/audit_ftmo_D05_1.py` | vérification des exports | — |
| `experiments/D05_1/run_frictions_D05_1.py` | `--import`, `--frictions` (faits), `--baseline` (préparé, **jamais lancé**) | — |
| `experiments/D05_1/run_profil_D05_1.py` | étape 2 (fait, sans META) | — |

**`--baseline` : six marches, un facteur ajouté à chaque marche.**
- Marches :
  1. `convention` : contrôle bloquant, doit redonner le roster de D05.6bis ;
  2. `ecart_commission` ;
  3. `swaps` ;
  4. `pauses` ;
  5. `or_ftmo` ;
  6. `levier_compte` : levier Swing réel, crypto 1:1 et or 1:15 = Baseline cTrader.
- Pistes : référence, piste 1, piste 2.
- Sorties : `baseline_D05_1.csv`, `baseline_challenges_D05_1.csv`, `baseline_ecarts_D05_1.csv` (écarts appariés à la
  marche précédente et à la convention), `baseline_metriques_D05_1.csv` (8 métriques), `controles_baseline_D05_1.json`.
- Durée estimée : 5 à 10 minutes. **Le code n'a jamais tourné** : en attendre des erreurs simples.

## 7. Suite (décisions du porteur, puis GO)

0. **Simplicité d'abord (porteur, 2026-10-06) :** « ne complexifions pas trop ». RE-1 gelée avec la piste 1 peut déjà
   être testée en prop firm. Le porteur la testera **en démo dès l'accord de Spotware**.
   - Point technique : l'application Open API actuelle est en lecture seule (scope « accounts »). Trader en démo par
     l'Open API demandera le scope « trading » et un nouveau consentement du porteur.
   - Les étapes ci-dessous ne doivent pas retarder ce test.
1. **Baseline cTrader (étape 1).**
   - Points à acter :
     - levier de référence : le compte Swing réel (1:1 et 1:15), confirmé par FTMO, ou l'étalon de D05.4 (1:2 et 1:30),
       qui était faux pour Swing ;
     - lecture de l'or : examiner d'abord l'écart HistData / FTMO.
   - Puis : cadrage dans le journal, `--baseline`, rapport.
   - **Ce qui se lit :** réussite et délai du challenge de la piste 2, marche par marche.
2. **META (étape 2).** Historique FTMO de 20 mois seulement. Choix du porteur : profil sur cette période courte, ou
   autre source de prix (Alpaca SIP, téléchargé par le porteur avec ses clés).
3. **Inclusion (étape 3).**
   - Le moteur sait déjà faire : plusieurs jambes, levier par actif (ajouter la TradFi à `LEVIER_FTMO_SWING` ou passer
     un dictionnaire), marge plafonnée, frais par trade, tailles par risque.
   - À cadrer : fenêtre commune (2021-10 avec AVAX), allocation (même risque ou modulé par la queue), limite d'exposition
     simultanée, lecture (réussite et délai du challenge de la piste 2, perte du jour, valeur en suite).
4. **Nouvelle piste (porteur) : adapter le filtre de Kalman à chaque actif.**
   - **Première étape, simplifiée par le porteur le 2026-10-06 :** adapter **R0 seul pour chaque actif, avec Optuna**.
     H, les seuils et la frontière restent ceux de RE-1 figée.
   - **Ce qu'on sait déjà (D02) :** walk-forward de R0 sur une grille de 5 valeurs (10, 50, 100, 200, 500).
     - BTC : +0,291 ATR, contre +0,218 pour RE-1 figée ; écart +0,074 [−0,067 ; +0,225], porté par 2015 et 2018.
     - Or : −0,150 [−0,294 ; −0,021] face au contrôle.
     - Le porteur avait jugé le WFO-R0 « à creuser » (2026-10-02).
   - **À cadrer avant tout calcul :**
     - actifs concernés : chaque actif hors crypto, et les cryptos du portefeuille si le porteur le veut ;
     - espace de R0 : continu, en échelle log ;
     - fonction objectif : D02 retenait le Calmar net sur plateau avec une espérance en ATR positive ;
     - découpage IS/OOS : walk-forward ;
     - nombre d'essais Optuna, compté et consigné ;
     - frictions FTMO incluses ;
     - lecture : écart apparié contre RE-1 figée sur le même actif ;
     - [HYP] biais de sélection.
   - **Ensuite seulement :** le reste des paramètres du filtre (Q…), si le porteur l'ouvre.
   - **Outil :** Optuna 4.8.0 est installé, mais **absent de `pyproject.toml`** : l'ajouter sur GO, avec des tests.
5. **Remplacement d'AVAX** (mis de côté par le porteur).
   - [OBS] AVAX devient nul net chez FTMO (−0,01 ATR par trade).
   - Données prêtes pour DOGE, LINK, AAVE, UNI et XLM : FTMO dans `export_2026-10-06_v3`. La série Coinbase est à
     télécharger sur GO.
   - Le porteur avait écarté LINK en D02.0.

## 8. Message de reprise (à coller dans la nouvelle session)

> Bonjour. Tu reprends la direction Prop Firm (D05) d'AKF-TSO, chantier D05.1, dans
> `C:\Users\poek9\Projet Claude\#KalmanFilter` (branche `main`). Lis d'abord `CLAUDE.md`, puis `passation_D05_1.md`,
> puis `experiments/D05_1/narratif_frictions_D05_1.md` et `experiments/D05_1/rapport_profil_D05_1.md`. Les données sont
> prêtes : tu ne t'occupes que de la stratégie.
>
> Ne complexifions pas : RE-1 gelée avec la piste 1 peut déjà être testée en prop firm. Je la testerai en démo dès
> l'accord de Spotware. L'objectif de D05.1 reste de sauver la piste 2 par le portefeuille, sans retarder ce test.
>
> Vérifie l'état (git log, tests) sans rien modifier. Rends-moi un compte rendu court : ce que tu as compris, ce qui est
> acquis, et ta proposition de cadrage pour chacun des points ci-dessous. Ne lance aucun calcul avant mon GO.
>
> Éléments à cadrer avant tout calcul :
> 1. **Baseline cTrader** (`run_frictions_D05_1.py --baseline`, jamais lancé) :
>    - levier de référence : compte Swing réel (cryptos 1:1, or 1:15) ou étalon de D05.4 (1:2, 1:30) ;
>    - source de l'or : HistData ou barres FTMO (expliquer d'abord l'écart de brut, +0,36 contre +0,14 ATR) ;
>    - lecture : réussite et délai du challenge des pistes 1 et 2, marche par marche.
> 2. **META :** profil sur l'historique FTMO court (depuis 2025-01) ou autre source de prix.
> 3. **R0 par actif via Optuna** (H, seuils et frontière figés) :
>    - actifs concernés ;
>    - espace de R0 ;
>    - fonction objectif ;
>    - découpage walk-forward IS/OOS ;
>    - nombre d'essais, compté ;
>    - frictions FTMO incluses ;
>    - écart apparié contre RE-1 figée sur le même actif ;
>    - repère : WFO-R0 de D02 ;
>    - Optuna à ajouter à `pyproject.toml`, avec des tests.
> 4. **Inclusion TradFi (étape 3) :**
>    - fenêtre commune ;
>    - allocation (même risque ou modulé par la queue) ;
>    - limite d'exposition simultanée ;
>    - lecture : réussite du challenge de la piste 2, délai, perte du jour, valeur en suite.
