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
