"""Chargeur OHLC : barres non clôturées, métadonnées d'extraction, doublons, trous (synthétique)."""
import json
import warnings

import pandas as pd
import pytest

from utils.data_loader import load_ohlc, meta_path, sha256_file


def _csv(tmp_path, times):
    t = pd.DatetimeIndex(times)
    p = tmp_path / "x_30m.csv"
    pd.DataFrame({"time": t.strftime("%Y-%m-%d %H:%M:%S+00:00"), "timestamp": t.astype("int64") // 10**9,
                  "open": 1.0, "high": 1.0, "low": 1.0, "close": 1.0, "volume": 1.0}).to_csv(p, index=False)
    return p


def test_retire_la_barre_non_cloturee(tmp_path):
    t = pd.date_range("2026-09-15 15:00", periods=3, freq="30min", tz="UTC")
    df = load_ohlc(_csv(tmp_path, t), extracted_at=pd.Timestamp("2026-09-15 16:19", tz="UTC"))
    assert df.time.tolist() == list(t[:2])


def test_heure_d_extraction_lue_dans_les_metadonnees(tmp_path):
    t = pd.date_range("2026-09-15 15:00", periods=3, freq="30min", tz="UTC")
    p = _csv(tmp_path, t)
    meta_path(p).write_text(json.dumps({"extracted_at_utc": "2026-09-15T16:19:00+00:00", "sha256": sha256_file(p)}))
    with warnings.catch_warnings():
        warnings.simplefilter("error")                              # aucun repli sur la date de modification
        assert load_ohlc(p).time.tolist() == list(t[:2])
    meta_path(p).write_text(json.dumps({"extracted_at_utc": "2026-09-15T16:19:00+00:00", "sha256": "0" * 64}))
    with pytest.raises(ValueError):
        load_ohlc(p)


def test_doublons_refuses_et_trous_signales(tmp_path):
    t = pd.date_range("2026-09-15 10:00", periods=4, freq="30min", tz="UTC")
    with pytest.raises(ValueError):
        load_ohlc(_csv(tmp_path, t.append(t[-1:])), extracted_at=pd.Timestamp("2026-09-16", tz="UTC"))
    holed = t.delete(1)
    with pytest.warns(UserWarning):
        df = load_ohlc(_csv(tmp_path, holed), extracted_at=pd.Timestamp("2026-09-16", tz="UTC"))
    assert len(df) == 3 and df.attrs["gaps"] == [(str(t[0]), str(t[2]), 1)]


def test_donnees_du_projet_ont_des_metadonnees():
    from config import DATA_RAW
    if not DATA_RAW.exists():
        pytest.skip("données absentes (hors dépôt)")
    assert meta_path(DATA_RAW).exists()
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        df = load_ohlc()
    assert len(df) == 117584 and df.attrs["gaps"] == []
