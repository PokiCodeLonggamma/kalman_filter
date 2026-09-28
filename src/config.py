"""Configuration du projet KAKALMAN. Les valeurs reflètent docs/decisions.md."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Source de données (D1, D7, D12) : spot, versionnée par échange
DATA_RAW = ROOT / "data" / "raw" / "bitstamp_btcusd_30m.csv"
TIMEFRAME = "30min"

# Baseline Pine unique et immuable (D24)
BASELINE_PINE = ROOT / "pine" / "baseline" / "AKF_TSO_v2.1_baseline.pine"
BASELINE_SHA256 = "c70062b8414ab4f522970511f034fb2a4bfa0b26b10a189c1c74b74ecd30b317"

# Oracle de parité P0 (vérifié sur TradingView), jamais modifié
ORACLE = ROOT / "experiments" / "p0" / "akf_replique_pine.py"

# Warm-up unifié du pipeline Python (D22), compté depuis la 1re barre de chaque actif
WARMUP_BARS = 300

# Convention d'exécution (D25) : "open_next" en production, "close" pour la parité TradingView
FILL_PRICE_DEFAULT = "open_next"
ORACLE_SHA256 = "3598db1717541cffabe87c8cf2a29ba6b95006f2595e6bc4d3598bb6e4cec429"

# Parité P2 (docs/P2_parite.md) : tolérance absolue modules vs oracle
PARITY_ABS_TOL = 1e-5

# ── Features P3/P4 (docs/P3_features_kalman.md, D27, D32, D33) ────────────────
FEATURE_VOL_LOOKBACK = 20      # vol_bps : écart-type des log-rendements sur 20 barres (D17, D19)
NIS_Z_WINDOW = 100             # z-score glissant du NIS, fenêtre [t−99, t] (D20)
CHOP_WINDOW = 48               # n_short_seg_48, n_zone_changes_48 (D23)
AUTOCORR_WINDOW = 48           # innov_autocorr_48, corrélation glissante lag 1 (D33)
SHORT_SEG_BARS = 6             # « segment court » = même borne que min_trend_bars (D23)
SATURATION_TH = 99.9           # is_saturated = prev_seg_extreme_abs >= 99.9 (D19)
WARMUP_BARS_1H = 300           # bougies 1 h ENTIÈREMENT clôturées avant toute feature 1 h (D32)
DEFAULT_ASSET = "BTC/USD"
FEATURES_CSV = ROOT / "data" / "processed" / "kalman_features_v2.csv"

# ── Labeling P4 (docs/P4_labeling.md, D34 à D36) ──────────────────────────────
# Coût canonique de recherche ML1 (D36) : 5 bps aller-retour = 2·fee + spread + 2·slippage = 2·1,5 + 1,0 + 2·0,5.
# Hypothèse simplificatrice, injectée explicitement dans `labeling.CostModel(**CANONICAL_COST)` : le modèle de coût
# lui-même n'a aucune valeur par défaut. Les scénarios 0/5/10/20/40 bps restent des analyses de sensibilité.
CANONICAL_COST = {"fee_bps": 1.5, "spread_bps": 1.0, "slippage_bps": 0.5}
LABEL_VERSION = "B-1.0"        # cible B (D34) + coût canonique (D36)
LABELS_CSV = ROOT / "data" / "processed" / "kalman_labels.csv"
ML1_DATASET_CSV = ROOT / "data" / "processed" / "kalman_ml1_dataset.csv"

# ── P5 / ML1 baseline logistique (docs/P5_logistic.md, D37) — fixé ex ante, jamais optimisé ─────────────────────
ML_FIRST_TEST = "2022-01-01"   # premier bloc de test ; train initial = 2020-2021
ML_TEST_MONTHS = 6             # blocs de test semestriels : 8 plis 2022 S1 → 2025 S2
ML_HOLDOUT_START = "2026-01-01"  # réserve scellée : aucun événement entré ou sorti à partir de cette date en dev
ML_EMBARGO = "1D"              # 48 barres de 30 min ; sans effet en walk-forward avant (aucun train après le test)
ML_LOGIT_C = 1.0               # L2, C fixé ; C = 0,1 et 10 rapportés en contrôle, sans sélection
ML_LOGIT_C_CONTROLE = (0.1, 10.0)
ML_WINSOR_Q = (0.005, 0.995)   # écrêtage aux quantiles du train du pli
ML_BOOT_B = 2000               # bootstrap par blocs mensuels des prédictions OOS
ML_PERM_B = 500                # permutation par blocs mensuels de y dans chaque train (S1)
ML_COEF_BOOT_B = 200           # bootstrap par blocs mensuels du train pour les IC de coefficients (V2, V3)
ML_SEED = 20260921

# ── P6 / ML1 XGBoost (docs/P6_xgboost.md, D39) — verrouillé ex ante par Aymeric, jamais optimisé ──────────────────
# 13 features V1 brutes (aucun prétraitement), hyperparamètres fixes, 3 graines moyennées, split interne 80/20.
P6_XGB_PARAMS = {"objective": "binary:logistic", "eval_metric": "logloss", "tree_method": "hist",
                 "n_estimators": 2000, "learning_rate": 0.03, "max_depth": 2, "min_child_weight": 10,
                 "gamma": 0.0, "subsample": 0.80, "colsample_bytree": 0.80, "reg_lambda": 10.0,
                 "reg_alpha": 0.10, "n_jobs": 1}
P6_SEEDS = (20260921, 20260922, 20260923)   # p_xgb = moyenne arithmétique des 3 graines, aucune sélection
P6_EARLY_STOPPING_ROUNDS = 50               # sur la LogLoss NON pondérée de la validation interne
P6_INNER_VALID_FRAC = 0.20                  # validation interne = 20 % les plus récents du train externe conservé
P6_V1_REFERENCE = ROOT / "experiments" / "p6" / "v1_reference_af894d8.csv"   # prédictions V1 de P5, bit à bit

# ── P6.1 / capacité XGBoost nested (docs/P6_1_capacite.md, D41) — verrouillé ex ante par Aymeric ────────────────────
# Seuls max_depth, min_child_weight, reg_lambda et reg_alpha varient ; C0 = configuration P6 (D39) à l'identique.
# Graines, early stopping (50) et split interne 80/20 : ceux de P6 (P6_SEEDS, P6_EARLY_STOPPING_ROUNDS, ...).
P61_COMMON = {"objective": "binary:logistic", "eval_metric": "logloss", "tree_method": "hist", "n_estimators": 2000,
              "learning_rate": 0.03, "gamma": 0.0, "subsample": 0.80, "colsample_bytree": 0.80, "n_jobs": 1}
P61_CANDIDATES = {"C0": {"max_depth": 2, "min_child_weight": 10, "reg_lambda": 10.0, "reg_alpha": 0.10},
                  "C1": {"max_depth": 2, "min_child_weight": 5, "reg_lambda": 5.0, "reg_alpha": 0.05},
                  "C2": {"max_depth": 3, "min_child_weight": 5, "reg_lambda": 5.0, "reg_alpha": 0.05},
                  "C3": {"max_depth": 3, "min_child_weight": 2, "reg_lambda": 2.0, "reg_alpha": 0.00}}
P61_ORDER = ("C0", "C1", "C2", "C3")      # du moins au plus complexe : ordre de la règle de parcimonie
P61_EPSILON = 0.0005                      # écart de LogLoss interne sous lequel le candidat le plus simple l'emporte
P61_MIN_COMPLEX_FOLDS = 2                 # critère 4 : au moins 2 plis sur 8 retiennent un candidat plus complexe que C0

# ── P6.5 / audit descriptif de l'estimand (docs/P6_5_estimand.md, D43) — descriptif, aucun modèle ─────────────────
P65_HORIZONS = (1, 2, 4, 6, 8, 12, 16, 24, 48)          # barres de 30 min après l'entrée open[b+1]
P65_MFE_THRESHOLDS = (0, 5, 25, 30, 50, 100)            # bps bruts ; sensibilités descriptives, ni TP ni label
P65_EXCURSION_GRID = (10, 25, 50, 75, 100, 150, 200, 300, 500)   # bps ; courbes P(final | MAE ≤ −x), P(final | MFE ≥ x)
P65_DURATION_BINS = ((7, 9), (10, 12), (13, 20), (21, 38), (39, None))   # classes de durée (quantiles de P4 §6)
P65_TAIL_SHARES = (0.01, 0.05, 0.10)
P65_QUANTILES = (0.01, 0.05, 0.10, 0.25, 0.50, 0.75, 0.90, 0.95, 0.99)
P65_BLOCKS = {"innovation": ["innov_rel_al", "nis_z_100"], "vitesse_30m": ["x1_bps_al", "trend_strength_al"],
              "tendance_1h": ["x1_1h_bps_al", "macro_align_1h"],
              "bruit_amplitude": ["log_R_rel", "peak_bps_vol", "A_vol"],
              "structure": ["prev_seg_len", "n_short_seg_48", "bars_since_last_direct_jump", "is_saturated"]}

# ── P6.5b / placebo et conditionnement physique (docs/P6_5b_placebo_strates.md, D45) — descriptif, aucun modèle ─────
P65B_SEED = 20260924                      # graine des entrées placebo (distincte de ML_SEED et des graines P6)
P65B_K = 500                              # réplications placebo par variante
P65B_VARIANTS = ("uniforme", "meme_mois")  # entrée tirée sur toute la période / dans le mois calendaire de l'événement
P65B_HORIZONS = (2, 4, 6, 12)             # horizons fixes du conditionnement (barres de 30 min après open[b+1])
P65B_MFE_THRESHOLDS = (30, 50, 100)       # bps bruts ; parts descriptives, ni TP ni label
P65B_QUARTILE_FEATURES = ("nis_z_100", "innov_rel_al")   # conditionnement 1 : quartiles sur les 7 296 événements
P65B_SEG_LEN_CLASSES = ((6, 6), (7, 9), (10, None))      # conditionnement 3 : marginal / intermédiaire / mûr
P65B_ALPHA = 0.05                         # IC 95 % ; Bonferroni sur la famille strates × horizons

# ── P6.5c / placebo à règle de sortie identique (docs/P6_5c_placebo_sortie.md, D47) — descriptif, aucun modèle ─────
P65C_SEED = 20260925                      # graine des entrées placebo (distincte de P65B_SEED, ML_SEED, P6_SEEDS)
P65C_K = 500                              # réplications placebo, variante même mois seule
P65C_STRESS = ("nis_z_100 Q1", "nis_z_100 Q1-Q3", "nis_z_100 Q4")      # strates de D45 reprises
P65C_STRESS_CONTRASTS = (("nis_z_100 Q1", "nis_z_100 Q4"), ("nis_z_100 Q1-Q3", "nis_z_100 Q4"))

# ── P6.5d / stratégie AKF-TSO v2.1 gelée + stop-loss fixe (docs/P6_5d_stop_loss.md, D48) — descriptif ──────────────
P65D_STOP = 0.025                         # 2,5 % du prix d'entrée, fixé a priori par Aymeric ; aucune autre valeur testée
P65D_COST_BPS = 5.0                       # coût aller-retour par trade (dataset B-1.0), net = brut − 5 bps

# ── Étape 1 / mécanique de la stratégie (docs/E1_mecanique.md, D50) — descriptif, aucun ML, aucune sélection ────────
# EMA et ATR réservés au module d'exécution `src/strategy/` (amendement CLAUDE.md, D50) ; signal Kalman v2.1 invariant.
E1_FILTRES = {"aucun": None, "ema50_k0": (50, 0.0), "ema50_k1": (50, 1.0), "ema20_k0": (20, 0.0), "ema20_k1": (20, 1.0)}
E1_ATR = 14                               # ATR de Wilder (ta.atr de Pine), barres de 30 min
E1_STOPS_ATR = (None, 2.5)                # stop à P0 − side · 2,5 · ATR14[b]
E1_TPS_ATR = (None, 2.0)                  # take-profit à P0 + side · 2,0 · ATR14[b]
E1_TIME_STOPS = (None, 14)                # sortie à l'ouverture de la 14e barre après l'entrée
E1_COST_BPS = 5.0                         # coût aller-retour par trade
