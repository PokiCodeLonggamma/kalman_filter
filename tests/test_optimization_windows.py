"""EXP-D02 — fenêtres semestrielles du walk-forward (`optimization.windows`) : comptes du protocole du porteur, IS de
24 mois juste avant chaque OOS de 6 mois, réserve 2026."""
import pandas as pd
import pytest

from optimization.windows import bar_span, walk_forward_windows

UTC = "UTC"


@pytest.mark.parametrize("first, n, oos0", [
    ("2013-01-01 00:00", 22, "2015-01-01"),                   # BTC Bitstamp
    ("2009-03-15 22:00", 29, "2011-07-01"),                   # or HistData
    ("2021-06-17 16:00", 5, "2023-07-01"),                    # SOL Coinbase
    ("2021-09-30 19:00", 4, "2024-01-01"),                    # AVAX Coinbase
])
def test_fenetres_du_protocole(first, n, oos0):
    w = walk_forward_windows(pd.Timestamp(first, tz=UTC))
    assert len(w) == n
    assert w[0].oos_start == pd.Timestamp(oos0, tz=UTC)
    assert w[-1].oos_end == pd.Timestamp("2026-01-01", tz=UTC)
    for i, x in enumerate(w):
        assert x.k == i and x.is_end == x.oos_start
        assert x.is_start == x.oos_start - pd.DateOffset(months=24)
        assert x.oos_end == x.oos_start + pd.DateOffset(months=6)
        assert x.oos_start.month in (1, 7) and x.oos_start.day == 1 and x.oos_start.hour == 0
    assert all(a.oos_end == b.oos_start for a, b in zip(w, w[1:]))  # semestres contigus, sans recouvrement
    assert w[0].is_start >= pd.Timestamp(first, tz=UTC)


def test_fenetres_refusent_la_reserve_2026():
    with pytest.raises(ValueError, match="réserve 2026"):
        walk_forward_windows(pd.Timestamp("2021-01-01", tz=UTC), end=pd.Timestamp("2026-07-01", tz=UTC))


def test_fenetres_jusqu_a_une_fin_anterieure():
    w = walk_forward_windows(pd.Timestamp("2021-01-01", tz=UTC), end=pd.Timestamp("2024-01-01", tz=UTC))
    assert [x.oos_start.strftime("%Y-%m") for x in w] == ["2023-01", "2023-07"]


def test_barres_d_une_periode_demi_ouverte():
    t = pd.Series(pd.date_range("2022-12-31 23:00", periods=6, freq="30min", tz=UTC))
    first, last = bar_span(t, pd.Timestamp("2023-01-01", tz=UTC), pd.Timestamp("2023-01-01 01:30", tz=UTC))
    assert (first, last) == (2, 4)
    with pytest.raises(ValueError, match="aucune barre"):
        bar_span(t, pd.Timestamp("2024-01-01", tz=UTC), pd.Timestamp("2024-07-01", tz=UTC))
