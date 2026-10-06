"""EXP-D05.1 — fichiers du cBot AkfExportFtmo (`marketdata.ftmo`) : bougies M30, ticks bid/ask, fiches ; écarts à
l'ouverture des barres et profil par demi-heure locale. Réserve 2026 : bougies tronquées au 2026-01-01 hors levée ;
ticks de 2026 refusés hors levée."""
import numpy as np
import pandas as pd
import pytest

import reserve
from marketdata.ftmo import (ecarts_barres, ecrire_serie, lire_bougies, lire_fiches, lire_ticks, profil_ecarts)
from utils.data_loader import load_ohlc


def _bougies(tmp_path, times, rows=None):
    n = len(times)
    rows = rows or [(100.0, 101.0, 99.0, 100.5, 10)] * n
    df = pd.DataFrame(rows, columns=["open", "high", "low", "close", "tick_volume"])
    df.insert(0, "time", [pd.Timestamp(t).strftime("%Y-%m-%dT%H:%M:%SZ") for t in times])
    p = tmp_path / "ftmo_x_m30.csv"
    df.to_csv(p, index=False)
    return p


def test_bougies_utc_tronquees_a_la_reserve_hors_levee(tmp_path):
    t = ["2025-12-31 23:00", "2025-12-31 23:30", "2026-01-01 00:00", "2026-01-01 00:30"]
    p = _bougies(tmp_path, t)
    b = lire_bougies(p)
    assert list(b.columns) == ["time", "open", "high", "low", "close", "volume"]
    assert len(b) == 2 and str(b.time.dt.tz) == "UTC"
    with reserve.levee("test"):
        assert len(lire_bougies(p)) == 4


@pytest.mark.parametrize("rows,motif", [
    ([(100.0, 99.0, 98.0, 100.0, 1), (100.0, 101.0, 99.0, 100.5, 1)], "incohérent"),
    ([(100.0, 101.0, 101.5, 100.0, 1), (100.0, 101.0, 99.0, 100.5, 1)], "incohérent"),
])
def test_bougies_incoherentes_refusees(tmp_path, rows, motif):
    p = _bougies(tmp_path, ["2024-01-02 00:00", "2024-01-02 00:30"], rows)
    with pytest.raises(ValueError, match=motif):
        lire_bougies(p)


def test_bougies_doublons_ou_desordre_refuses(tmp_path):
    with pytest.raises(ValueError, match="ordre"):
        lire_bougies(_bougies(tmp_path, ["2024-01-02 00:30", "2024-01-02 00:00"]))
    with pytest.raises(ValueError, match="ordre"):
        lire_bougies(_bougies(tmp_path, ["2024-01-02 00:00", "2024-01-02 00:00"]))


def _ticks(tmp_path, rows):
    p = tmp_path / "ftmo_x_ticks.csv"
    pd.DataFrame(rows, columns=["time", "bid", "ask"]).to_csv(p, index=False)
    return p


def test_ticks_de_2026_exigent_la_levee(tmp_path):
    p = _ticks(tmp_path, [("2026-09-28T10:00:00.100Z", 100.0, 100.1), ("2026-09-28T10:00:01.000Z", 100.0, 100.2)])
    with pytest.raises(ValueError, match="réserve 2026"):
        lire_ticks(p)
    with reserve.levee("test"):
        t = lire_ticks(p)
    assert len(t) == 2 and str(t.time.dt.tz) == "UTC"


def test_ticks_ask_sous_bid_refuse(tmp_path):
    p = _ticks(tmp_path, [("2025-09-28T10:00:00.100Z", 100.0, 99.9)])
    with pytest.raises(ValueError, match="ask"):
        lire_ticks(p)


def test_ecrire_serie_relue_par_load_ohlc(tmp_path):
    p = _bougies(tmp_path, pd.date_range("2024-01-02", periods=6, freq="30min", tz="UTC"))
    b = lire_bougies(p)
    out = tmp_path / "ftmo_x_30m.csv"
    meta = ecrire_serie(b, out, {"source": "test"}, extrait="2024-01-03T00:00:00Z")
    df = load_ohlc(out)
    assert len(df) == 6 and meta["sha256"] and meta["n_rows"] == 6
    assert np.allclose(df[["open", "high", "low", "close"]].to_numpy(), b[["open", "high", "low", "close"]].to_numpy())
    assert (df.volume.to_numpy() == b.volume.to_numpy()).all()


def test_ecart_de_chaque_barre_a_son_ouverture():
    """Médiane des écarts des ticks des 5 premières minutes ; sinon dernier tick avant l'ouverture."""
    t0 = pd.Timestamp("2025-03-04 10:00", tz="UTC")
    ticks = pd.DataFrame({"time": [t0 - pd.Timedelta(minutes=2), t0 + pd.Timedelta(seconds=10),
                                   t0 + pd.Timedelta(minutes=1), t0 + pd.Timedelta(minutes=4),
                                   t0 + pd.Timedelta(minutes=20), t0 + pd.Timedelta(minutes=40)],
                          "bid": [100.0] * 6, "ask": [100.05, 100.01, 100.02, 100.03, 100.50, 100.04]})
    e = ecarts_barres(ticks, pd.DatetimeIndex([t0, t0 + pd.Timedelta(minutes=30)]))
    mid = lambda a: (a - 100.0) / ((a + 100.0) / 2) * 1e4            # noqa: E731
    assert e.iat[0] == pytest.approx(mid(100.02))                      # médiane de 1, 2 et 3 centimes
    assert e.iat[1] == pytest.approx(mid(100.50))                      # aucun tick dans [10:30, 10:35) : dernier avant


def test_profil_par_demi_heure_locale():
    t = pd.DatetimeIndex(["2025-07-01 21:00", "2025-07-02 21:00", "2025-07-01 21:30"], tz="UTC")   # 17:00 et 17:30 NY
    e = pd.Series([4.0, 6.0, 1.0], index=t)
    p = profil_ecarts(e, "America/New_York")
    assert len(p) == 48 and p.loc[34, "mediane"] == pytest.approx(5.0) and p.loc[35, "mediane"] == pytest.approx(1.0)
    assert p.loc[34, "n"] == 2 and np.isnan(p.loc[0, "mediane"])


def test_fiches_lues_par_nom(tmp_path):
    p = tmp_path / "ftmo_symboles_fiches.csv"
    p.write_text('nom,description,digits,swap_type,swap_long,swap_short,swap_triple,levier_paliers,seances\n'
                 'US100.cash,"NASDAQ 100 Index, Spot CFD",2,Points,-6.96,0.34,Friday,"0:20|5000:10","Sun 22:05-Mon 21:00"\n',
                 encoding="utf-8")
    f = lire_fiches(p)
    assert f.loc["US100.cash", "description"] == "NASDAQ 100 Index, Spot CFD" and f.loc["US100.cash", "digits"] == 2
