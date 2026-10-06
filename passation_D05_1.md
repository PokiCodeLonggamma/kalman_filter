# PASSATION — D05.1 : l'objectif stratégique (sauver la piste 2 par le portefeuille)

*Rédigée le 2026-10-06, à la demande du porteur, à la fin de la session « données FTMO et frictions ». Direction Prop
Firm (D05), dépôt `#KalmanFilter`, branche `main`. À lire avec `CLAUDE.md`, `experiments/D05_1/narratif_frictions_D05_1.md`
et `experiments/D05_6bis/rapport_D05_6bis.md`.*

## 0. En une minute

- **Étalon :** compte FTMO Swing de 100 000.
  - Challenge : 9 % puis 5 % ; perte du jour de 5 % à minuit CET/CEST ; perte totale de 10 %, statique ; au moins
    4 jours.
  - Compte financé : 80 % des gains, retrait tous les 14 jours, 540 € remboursés au premier retrait.
  - Moteur : `propfirm` (D05.4 à D05.8).
- **Stratégie :** RE-1 version finale, figée : RE-1 et un stop catastrophe à 4 ATR (`strategy.final`). Six actifs :
  BTC, ETH, SOL, AVAX, XRP, or. Fenêtre commune 2021-10-01 → 2026-10-01 (AVAX coté depuis le 2021-09-30).
- **Pistes :**
  - référence : 0,20 × 0,20 %/ATR ;
  - **piste 1 : 0,20 × 0,25**, verrouillée par le porteur, choix de sécurité ;
  - **piste 2 : 0,25 × 0,25, « Burn & Churn pur »** : rachat immédiat (540 €) au minuit qui suit chaque échec.
  - Aucun filtre d'achat.
- **Ce qu'elles valent (D05.6bis, frais conventionnels 5 bps, or 4 bps, marge 1:2 crypto et 1:30 or plafonnée) :**

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

- **Axes à garder en tête pour l'inclusion (porteur) :**
  - décorrélation temporelle : les « cygnes noirs » du WTI ou de SAN tombent-ils quand la crypto stagne ?
  - exposition simultanée (« portfolio heat ») : avec 12 actifs, le risque simultané face à la perte du jour de 5 % ;
  - allocation par kurtosis : même risque (0,25) pour la TradFi ou risque modulé selon l'épaisseur des queues.
- **Plan validé, dans cet ordre strict (porteur) :**
  1. **Frictions et Baseline :** Baseline cTrader des pistes 1 et 2 sur les cryptos.
  2. **Profil TradFi (RE-1 pure) :** or, WTI, Brent, US100, US30, GER40, GBPJPY, SAN, coûts FTMO. Anatomie des gains :
     queues, fréquence des cygnes noirs.
  3. **Inclusion portefeuille :** l'ajout sauve-t-il la réussite de la piste 2 ?
- Le porteur attend les résultats **descriptifs** des étapes 1 et 2 avant de statuer sur la méthode d'inclusion. Les
  conclusions de D01.7 sont **ignorées comme filtre** (décision du 2026-10-05).

## 1. Gouvernance (rappel ; voir `CLAUDE.md` et `passation.md` §2)

- **Aucun calcul de recherche, aucune modification, aucun push sans GO explicite.** Le dépôt GitHub est public : pousser
  revient à publier. Commits locaux propres.
- **Intouchables :**
  - RE-1 figée ; `src/indicator/` sanctuarisé ; baseline Pine gelée ;
  - ne jamais supprimer, renommer ni déplacer un ancien dossier.
- **Réserve :**
  - ETH, XRP et 2026 sont lus depuis D04 (décision du porteur), mais **seulement dans un bloc `reserve.levee(motif)`** ;
  - hors du bloc, les gardes tronquent au 2026-01-01.
- **Accès et confidentialité :**
  - ne jamais demander de clé ni de jeton dans le chat ; le porteur se connecte lui-même ;
  - aucune donnée personnelle saisie par l'agent ;
  - les fichiers Sniper (`prompts/sniper/`, `prompts/init_d3_sniper.md`, `prompts/Piste complémentaire_sniper.md`)
    restent hors des commits.
- **Méthode :**
  - cadrage en 4 champs avant tout test : QUESTION / DONNÉES / MÉTHODE / CRITÈRE DE LECTURE, avec ce que ça ne permet
    pas de conclure ;
  - **aucun critère a priori**, ni seuil, ni N minimal ;
  - OFAT ;
  - tableau des 8 métriques (PnL et MDD à 0,25 %/ATR et à 1x) ;
  - frais réels dès la première barre ;
  - balises [CODE] / [OBS] / [HYP] ;
  - chiffres du porteur recalculés avant d'être consignés.
- **Forme des réponses :** en français, courtes et denses, sans flatterie ; le porteur se tutoie.

## 2. État du dépôt (2026-10-06)

- origin/main = `b020961`. **Commits locaux non poussés** (push sur GO seulement) :
  - correction horaire, mise de côté par le porteur : `2eb5e81`, `94616c2`, `2fdb9fe` ;
  - cBot v1 : `7cbaecb`, `13b6a23` ;
  - cBot v2 : `3ea13e1` ;
  - frais par trade : `cdd98a9` ;
  - lecteur FTMO et frictions : `5dfbf03` ;
  - audit : `ba99bb1` ;
  - pauses : `9c423f2` ;
  - échelle des modèles : `ff71a97` ;
  - puis les commits de cette passation.
- Tests : `python -m pytest -q` → 456 réussis, 2 ignorés (≈ 2 min 30).
- Console Windows en cp1252 : lancer les scripts avec `PYTHONIOENCODING=utf-8`, sinon les flèches des `print` cassent.

## 3. Données

### 3.1 FTMO (compte d'essai cTrader)

- **Récupération : cBot `experiments/D05_1/cbot/AkfExportFtmo.cs`, lancé par le porteur.** Il ne passe aucun ordre.
  - L'application Open API « AKF-TSO Research Data » (ID 42882) reste « Submitted » chez Spotware. Elle n'est plus
    nécessaire.
  - Le cBot écrit dans `C:\Users\poek9\OneDrive\Documents\cAlgo\Data\cBots\AkfExportFtmo\`.
- **Copies locales, hors Git (`data/raw/*`) :**
  - `data/raw/ftmo/export_2026-10-06/` : v1 (bougies M30, ticks des 10 derniers jours, fiches simples, liste des 363
    noms, dont 196 actifs) ;
  - `data/raw/ftmo/export_2026-10-06_v2/` : fiches complètes et liste ;
  - `data/raw/ftmo/ftmo_<clé>_30m.csv` et leur `.meta.json` : séries au schéma de `load_ohlc` (`--import`). Empreintes
    dans `experiments/D05_1/import_ftmo_D05_1.json`.
- **Premières barres :** US100, US30, GER40, WTI (`USOIL.cash`), Brent (`UKOIL.cash`) 2020-11-08 ; or 2020-05-06 ;
  GBPJPY 2020-04-01 ; BTC, ETH 2020-07-08 ; XRP 2020-07-13 ; SOL 2025-04-17. La fin est au 2026-10-05.
- **Manquants : SAN et AVAX.** L'instance v2 a gardé l'ancienne liste : un paramètre garde sa valeur tant que le nom de
  propriété ne change pas. AVAX se nomme `AVAUSD`. Pour les récupérer :
  1. dans l'instance, mettre `…;SAN;AVAUSD` dans « Fiches pour » et laisser `SAN;AVAUSD` dans « Bougies et ticks
     pour » ; relancer ;
  2. copier l'export dans `data/raw/ftmo/export_<date>_v3/` ;
  3. ajouter ce dossier et l'heure de fin du journal (UTC) à `EXPORTS`, dans `audit_ftmo_D05_1.py` et dans
     `run_frictions_D05_1.py` ;
  4. relancer `--import`, l'audit et `--frictions`.
  - **SAN : la description (Santander ou Sanofi) n'est pas encore lue.**
  - AVAX garde en attendant l'écart et la fiche de SOLUSD ([HYP]).
- **Vérification (`experiments/D05_1/audit_ftmo_D05_1.md`) :**
  - corrélation des rendements de 30 min de 0,98 à 0,998 avec Saxo, HistData, Bitstamp et Coinbase (WTI : 0,93 face au
    continu raccordé de Saxo) ;
  - décalage nul partout : UTC à l'ouverture des barres ;
  - niveau à +0,5 à +2,3 bps hors crypto, −4 à −18 bps sur les cryptos (bid FTMO face au prix de transaction).

### 3.2 Choix de source (porteur, 2026-10-06)

- **Hors crypto :** barres FTMO, sans complément Saxo. Les indices et le pétrole commencent donc le 2020-11-08.
- **Cryptos :** séries des courtiers de D05, chargées par `D041.load_all()` dans un bloc `levee` (Bitstamp pour BTC,
  ETH, XRP ; Coinbase pour SOL, AVAX), avec les frictions FTMO.
- **Or :** HistData dans D05 ; barres FTMO dans la Baseline (marche `or_ftmo`).

## 4. Frictions FTMO (détail : `experiments/D05_1/narratif_frictions_D05_1.md`)

| Actif | Écart médian (bps) | Commission par côté (bps) | Swap par nuit, long / short (bps) | Jour triple | Levier (fiche) |
|---|---|---|---|---|---|
| BTC, ETH, SOL, XRP | 0,1 ; 2,2 ; 2,5 ; 10,0 | 3,25 | +8,33 / +8,33 (−30 %/an) | vendredi | 1:1 |
| Or | 1,0 | 0,07 | +1,57 / +0,10 | mercredi | 1:15 |
| US100 ; US30 ; GER40 | 0,5 ; 0,5 ; 0,8 | 0 | +2,24 / −0,11 ; +0,34 / +1,80 ; +1,78 / +0,02 | vendredi | 1:15 |
| GBPJPY | 1,0 (10,5 au rollover) | 0,19 | −0,15 / +1,04 | mercredi | 1:30 |
| WTI ; Brent | 8,6 ; 7,1 | 0 | −5,5 / +24,8 ; −5,8 / +26,3 ([HYP] unité) | vendredi | 1:15 |

- **Modèle (`propfirm.frictions.couts_trades`)**, en bps du notionnel, prélevés à la sortie :
  - écart par demi-heure locale (New York ; Francfort pour GER40 et SAN) ;
  - série au milieu (cryptos des courtiers) : moitié de l'écart à l'entrée, moitié à la sortie ;
  - série au bid (barres FTMO, HistData) : un long paie l'écart à l'entrée, un short à la sortie ;
  - commission des deux côtés ;
  - swap à chaque rollover traversé : 17:00 New York, poids 3 le jour triple, 0 le week-end.
- **Pauses des cryptos (`ajuster_pauses`) :** une entrée pendant une pause est abandonnée ; une sortie ou un stop
  pendant une pause est exécuté à la réouverture.
- [OBS] **Fenêtre D05, frictions par trade :** BTC 8,9 bps ; ETH 11,1 ; SOL 11,5 ; AVAX 11,8 (écart de SOL) ; XRP 19,1 ;
  or 1,9. La convention était de 5 bps (or 4).
  - Net par trade, convention → FTMO : BTC +0,240 → +0,134 ATR ; ETH −0,063 → −0,193 ; SOL +0,177 → +0,091 ;
    AVAX +0,308 → +0,215 ; XRP +0,391 → +0,117 ; or (HistData) +0,112 → +0,243.
  - **Attendu :** la Baseline cTrader des pistes 1 et 2 sera nettement sous D05.6bis.
- **Hypothèses ouvertes :**
  - rollover à 17:00 New York ;
  - base de 360 jours des swaps en % ;
  - **unité des swaps du pétrole** : 25 bps par nuit en short à la lettre, invraisemblable comme financement pur ; à
    vérifier dans cTrader ou par une position d'essai tenue une nuit ;
  - pauses du samedi absentes des séances officielles : maintenance, ou trous du serveur d'essai ;
  - écarts mesurés sur dix jours de 2026 et appliqués à toute la période (convention de D02.0) ;
  - swap imputé à la sortie, pas chaque nuit.
- [OBS] **Or, effet de la source :** sur les barres FTMO, le brut vaut +0,14 ATR par trade, contre +0,36 sur HistData,
  avec 447 entrées communes (79-84 %) et un ATR voisin. Il faut l'examiner avant de lire la marche `or_ftmo`.

## 5. Code

| Fichier | Rôle | Tests |
|---|---|---|
| `src/envelope/portfolio.py` | `Leg.cost` scalaire ou un frais par trade ; `leg_costs` | `tests/test_couts_par_trade.py` (5) |
| `src/propfirm/moteur.py`, `blocs.py` | frais de chaque trade ; frais de sortie du trade ouvert dans l'objectif | idem |
| `src/marketdata/ftmo.py` | `lire_bougies` (tronquées au 2026-01-01 hors levée), `lire_ticks` (levée exigée), `lire_fiches`, `ecrire_serie`, `ecarts_barres`, `profil_ecarts`, `demi_heure`, `pauses_cotation` | `tests/test_marketdata_ftmo.py` (10) |
| `src/propfirm/frictions.py` | `jours_swap`, `nuits`, `swap_bps`, `commission_bps`, `ecart_trades`, `couts_trades`, `ajuster_pauses` | `tests/test_propfirm_frictions.py` (25) |
| `experiments/D05_1/audit_ftmo_D05_1.py` | vérification des exports | — |
| `experiments/D05_1/run_frictions_D05_1.py` | `--import`, `--frictions` (faits), `--baseline` (préparé, **non lancé**) | — |

**`--baseline` : six marches, un facteur ajouté à chaque marche.**
- Marches :
  1. `convention` : contrôle bloquant, doit redonner le roster de D05.6bis ;
  2. `ecart_commission` ;
  3. `swaps` ;
  4. `pauses` ;
  5. `or_ftmo` ;
  6. `levier_compte` : crypto 1:1, or 1:15 au lieu de 1:2 et 1:30 = Baseline cTrader.
- Pistes : référence, piste 1, piste 2.
- Sorties : `baseline_D05_1.csv`, `baseline_challenges_D05_1.csv` (réussite, délais), `baseline_ecarts_D05_1.csv`
  (écarts appariés à la marche précédente et à la convention), `baseline_metriques_D05_1.csv` (8 métriques),
  `controles_baseline_D05_1.json`.
- Durée estimée : 5 à 10 minutes.
- **Le code n'a jamais tourné** : en attendre des erreurs simples au premier lancement.

## 6. Étapes suivantes

### Étape 1 : Baseline cTrader

- **Avant le lancement, quatre décisions du porteur :**
  1. SAN et AVAX : relancer le cBot (§3.1), ou garder AVAX sur l'écart de SOL ;
  2. levier de référence : fiche du compte d'essai (1:1 et 1:15) ou étalon de D05.4 (1:2 et 1:30) ;
  3. or : HistData ou barres FTMO (l'écart de brut de §4 est à lire d'abord) ;
  4. unité des swaps du pétrole (étape 2 seulement).
- Puis : cadrage en 4 champs dans le journal, GO, `--baseline`, 8 métriques, rapport.
- **Ce qui se lit :** réussite et délai du challenge de la piste 2, marche par marche.

### Étape 2 : profil TradFi (RE-1 pure, coûts FTMO)

- **Fait le 2026-10-06, à la demande du porteur, sans SAN :** `experiments/D05_1/run_profil_D05_1.py` et
  `rapport_profil_D05_1.md`.
  - Espérance nette (ATR) : or +0,019, US100 −0,038, US30 −0,108, GER40 +0,086, GBPJPY +0,006, WTI −0,311,
    Brent −0,394.
  - Corrélation mensuelle avec le panier crypto proche de zéro, sauf le WTI (−0,42).
- **Restent :** SAN (à exporter) ; swaps du pétrole (unité) ; or FTMO contre HistData.
- **Le paragraphe ci-dessous est le plan d'origine, désormais réalisé :**

- **Code à écrire :** pour chaque actif hors crypto,
  - `D04.prepare(clé, data/raw/ftmo/ftmo_<clé>_30m.csv, D04.END)` dans un bloc `levee` ;
  - puis `D04.final_series` ;
  - puis `couts_trades(..., prix="bid", sept_jours=False, usd_par_cotation=...)`, avec le profil d'écart de l'actif.
- **Mesures :**
  - 8 métriques ;
  - anatomie des gains : distribution du net en ATR, part des 1 % et 5 % meilleurs trades, trades à 3, 5 et 10 ATR ou
    plus par an, nets par année ;
  - recoupement des années avec le panier crypto, pour préparer l'étape 3.
- **Pièges :**
  - swaps du pétrole ;
  - SAN : action, cotée en séance seulement, dividendes en ajustement de cash ;
  - fuseaux, à fixer avant le calcul ;
  - historique depuis 2020-11.

### Étape 3 : inclusion

- **Ce que le moteur sait déjà faire :** plusieurs jambes, levier par actif (ajouter la TradFi à `LEVIER_FTMO_SWING` ou
  passer un dictionnaire), marge plafonnée, frais par trade, tailles par risque (`Fixe`).
- **À cadrer avec le porteur :**
  - fenêtre commune : 2021-10 avec AVAX ;
  - allocation : même risque, ou modulé par la queue ;
  - limite d'exposition simultanée ;
  - lecture : réussite du challenge de la piste 2, délai, perte du jour, valeur en suite.

### Décisions et piste du porteur (2026-10-06, après l'étape 2)

- **Univers :**
  - **SAN remplacé par META** (action US, CFD FTMO).
  - **AVAX remplacé par une autre crypto de la liste FTMO**, au choix du porteur. Liste courte retenue sur des critères
    structurels seulement : écart FTMO (relevé le 2026-10-06 sur la liste de cTrader), série USD chez Coinbase couvrant
    la fenêtre D05, taille.

    | Crypto | Écart FTMO relevé | Série Coinbase USD |
    |---|---|---|
    | AAVE (`AAVUSD`) | ≈ 0,5 bp | depuis 2020-12 |
    | LINK (`LNKUSD`) | ≈ 2,2 bps | depuis 2019-06 |
    | UNI (`UNIUSD`) | ≈ 3,8 bps | depuis 2020-09 |
    | XLM (`XLMUSD`) | ≈ 9,2 bps | depuis 2019-03 |
    | DOGE (`DOGEUSD`) | ≈ 9,4 bps | depuis 2021-06 |
    | *AVAX, pour mémoire (`AVAUSD`)* | ≈ 17,9 bps | — |

  - En D02.0, le porteur avait écarté LINK et LTC de l'univers.
  - Pour la Baseline, le contrôle bloquant garde AVAX : il doit redonner D05.6bis. Le remplacement fait l'objet d'une
    marche à part.
  - L'écart d'AVAX vaut environ 18 bps, contre 2,5 pour SOL : l'hypothèse « écart de SOL » sous-estimait AVAX.
- **Nouvelle piste (porteur) :** optimiser **uniquement les paramètres du filtre de Kalman** sur un seul actif hors
  crypto, par exemple US100, pour voir si la stratégie demande un réglage par actif pour être portable hors crypto.
  - Garde-fous à cadrer avant tout calcul :
    - seuls les paramètres du filtre bougent (R0, et Q si le porteur l'ouvre), pas H ni les seuils ;
    - walk-forward, IS puis OOS, avec la machinerie de D02 (`src/optimization`, `build_atlas(kalman=…)`) ;
    - nombre de configurations compté ;
    - lecture contre RE-1 figée sur le même actif, en écart apparié ;
    - [HYP] biais de sélection : l'actif est choisi après lecture de l'étape 2.
  - Le porteur décide de sa place dans la suite.

## 7. Message de reprise (à coller dans la nouvelle session)

> Bonjour. Tu reprends la direction Prop Firm (D05) d'AKF-TSO, chantier D05.1, dans
> `C:\Users\poek9\Projet Claude\#KalmanFilter` (branche `main`). Lis d'abord `CLAUDE.md`, puis `passation_D05_1.md`,
> puis `experiments/D05_1/narratif_frictions_D05_1.md`. Vérifie l'état (git log, tests) sans rien modifier, et rends-moi
> un compte rendu court : ce que tu as compris de l'objectif stratégique (sauver la piste 2), l'état des données et des
> frictions, et les quatre décisions à prendre avant la Baseline cTrader (§6). Ne lance aucun calcul avant mon GO.
