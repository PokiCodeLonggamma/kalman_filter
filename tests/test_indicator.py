"""Pipeline run_indicator : warm-up transmis (D22), exécution par défaut (D25), validation des entrées (synthétique)."""
import numpy as np
import pandas as pd
import pytest

from indicator import run_indicator


def _sinus(n=400):
    c = 30000 + 500 * np.sin(2 * np.pi * np.arange(n) / 40)
    return pd.DataFrame({"time": pd.date_range("2024-01-01", periods=n, freq="30min", tz="UTC"),
                         "open": np.r_[c[0], c[:-1]], "high": c + 1, "low": c - 1, "close": c})


def test_run_indicator_transmet_le_warmup():
    df = _sinus()
    first = int(np.flatnonzero(run_indicator(df, warmup_bars=0).decision)[0])
    w = first + 1
    out = run_indicator(df, warmup_bars=w)
    assert not out.decision.iloc[:w].any() and out.decision.iloc[w:].any()
    assert (out.valid.to_numpy() == (np.arange(len(df)) >= w)).all()


def test_run_indicator_defauts_production():
    out = run_indicator(_sinus())
    dec = np.flatnonzero(out.decision)
    assert (~out.valid.iloc[:300]).all() and dec.min() >= 300
    fil = np.flatnonzero(out.fill.to_numpy() != 0)
    assert np.array_equal(fil, dec[dec + 1 < len(out)] + 1)            # open_next par défaut (D25)


def test_run_indicator_refuse_un_temps_non_trie_ou_duplique():
    df = _sinus()
    with pytest.raises(ValueError):
        run_indicator(df.iloc[::-1])
    with pytest.raises(ValueError):
        run_indicator(pd.concat([df.iloc[:10], df.iloc[9:]]))
