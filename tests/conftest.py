"""Fixtures communes. Données réelles chargées une fois par session ; tests `data` ignorés si le CSV est absent."""
import numpy as np
import pandas as pd
import pytest

from config import DATA_RAW


@pytest.fixture(scope="session")
def df_full():
    if not DATA_RAW.exists():
        pytest.skip("data/raw/bitstamp_btcusd_30m.csv absent (hors dépôt)")
    from utils.data_loader import load_ohlc
    return load_ohlc()


@pytest.fixture(scope="session")
def oracle_full(df_full):
    from akf_replique_pine import run
    o = run(df_full)
    o["time"] = pd.to_datetime(o.time).dt.tz_localize("UTC")
    return o


@pytest.fixture(scope="session")
def ind_close(df_full):
    """Mode parité : exécution au close, sans warm-up."""
    from indicator import run_indicator
    return run_indicator(df_full, fill_price="close", warmup_bars=0)


@pytest.fixture(scope="session")
def features_full(df_full):
    """Feature Store P4 sur tout l'historique (défauts de production : warm-up 300 barres et 300 bougies 1 h)."""
    from features import build_features
    return build_features(df_full)


@pytest.fixture(scope="session")
def events_full(features_full):
    """Univers événementiel ML1 (option A, D28) : tous les signaux bruts valides."""
    from features import build_events
    return build_events(features_full)


def signal_vector(long_signal, short_signal):
    return np.where(np.asarray(long_signal) == 1, 1, np.where(np.asarray(short_signal) == 1, -1, 0))


@pytest.fixture(scope="session")
def labels_full(features_full, events_full):
    """Cible B (D34) sur tout l'univers ML1, sans coût (le coût est injecté par `labeling.apply_costs`)."""
    from labeling import label_events
    return label_events(features_full, events_full)


# ── EXP-D02 : fabriques de données synthétiques (aucune donnée réelle) ──────────
@pytest.fixture
def barres_synthetiques():
    """Fabrique de barres OHLC de 30 min : marche aléatoire log-normale, ouvertures décalées (gaps)."""
    def make(n: int = 800, seed: int = 0, start: str = "2021-01-01") -> pd.DataFrame:
        rng = np.random.default_rng(seed)
        close = 100.0 * np.exp(np.cumsum(rng.normal(0.0, 0.004, n)))
        open_ = np.r_[100.0, close[:-1]] * np.exp(rng.normal(0.0, 0.003, n))
        high = np.maximum(open_, close) * np.exp(np.abs(rng.normal(0.0, 0.002, n)))
        low = np.minimum(open_, close) * np.exp(-np.abs(rng.normal(0.0, 0.002, n)))
        t = pd.date_range(start, periods=n, freq="30min", tz="UTC")
        return pd.DataFrame({"time": t, "open": open_, "high": high, "low": low, "close": close})
    return make


@pytest.fixture
def signaux_synthetiques():
    """Fabrique de signaux triés (barre, sens) et de niveaux de stop du bon côté de open[t + 1] (NaN : sans stop)."""
    def make(bars: pd.DataFrame, m: int = 120, seed: int = 1, p_stop: float = 0.6):
        rng = np.random.default_rng(seed)
        n = len(bars)
        t = np.sort(rng.choice(np.arange(5, n - 1), size=m, replace=False)).astype(np.int64)
        s = rng.choice(np.array([-1, 1], dtype=np.int64), size=m)
        p0 = bars.open.to_numpy()[t + 1]
        level = p0 * (1.0 - s * rng.uniform(0.001, 0.02, m))
        level[rng.random(m) > p_stop] = np.nan
        return t, s, level
    return make


@pytest.fixture
def atlas_synthetique():
    """Fabrique d'atlas de signaux (colonnes causales de RE-1) sur des barres données, et ATR14 en prix."""
    def make(bars: pd.DataFrame, m: int = 300, seed: int = 2):
        rng = np.random.default_rng(seed)
        n = len(bars)
        t = np.sort(rng.choice(np.arange(40, n - 2), size=m, replace=False)).astype(np.int64)
        leg = rng.uniform(1.0, 5.0, m)
        retrace = rng.uniform(0.2, 1.2, m)
        atlas = pd.DataFrame({
            "bar_index": t, "timestamp": bars.time.iloc[t].to_numpy(),
            "direction": rng.choice(np.array([-1, 1], dtype=np.int64), size=m),
            "prev_seg_len": rng.integers(3, 30, m), "leg_atr": leg, "obs_dist_seg_atr": leg * retrace,
            "obs_dist_cycle_atr": leg * retrace, "A_vol": np.ones(m), "peak_bps_vol": np.ones(m),
            "x1_already_flipped_at_t": rng.random(m) < 0.7, "nis_z_100": rng.normal(0.5, 1.0, m),
            "atr14_bps": np.full(m, 30.0)})
        close = bars.close.to_numpy()
        atr = close * 30.0 / 1e4
        atlas["atr14_bps"] = atr[t] / close[t] * 1e4
        return atlas, atr
    return make
