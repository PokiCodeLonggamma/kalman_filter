"""EXP-D02.0 — acquisition Bitstamp (sans réseau : API simulée) : pagination, bornes, doublons, réserve 2026, cache."""
import json
from urllib.parse import parse_qs, urlparse

import numpy as np
import pandas as pd
import pytest

from marketdata.bitstamp import build_bitstamp_csv, fetch_ohlc, parse_ohlc
from utils.data_loader import load_ohlc


class FakeBitstamp:
    """API simulée : une barre à chaque pas (plate et à volume nul quand il n'y a pas de transaction), au plus
    `limit` barres d'ouverture ≥ start, dans l'ordre chronologique, valeurs en chaînes comme l'API réelle."""

    def __init__(self, first: str, last: str, step: int = 1800, seed: int = 0):
        t = pd.date_range(first, last, freq=f"{step}s", tz="UTC", inclusive="left")
        rng = np.random.default_rng(seed)
        c = 100 * np.exp(np.cumsum(rng.normal(0, 0.002, len(t))))
        idle = rng.random(len(t)) < 0.1
        self.rows = []
        for k, (ti, ci) in enumerate(zip(t, c)):
            o, h, lo, v = (c[k - 1], max(ci, c[k - 1]) * 1.001, min(ci, c[k - 1]) * 0.999, 1.5) if k else (ci, ci, ci, 1.0)
            if idle[k] and k:
                o = h = lo = ci = self.rows[-1]["close_f"]
                v = 0.0
            self.rows.append({"timestamp": str(int(ti.timestamp())), "open": f"{o:.2f}", "high": f"{h:.2f}",
                              "low": f"{lo:.2f}", "close": f"{ci:.2f}", "volume": f"{v:.8f}", "close_f": ci})
        self.urls = []

    def __call__(self, url: str):
        self.urls.append(url)
        q = parse_qs(urlparse(url).query)
        start, limit = int(q["start"][0]), int(q["limit"][0])
        sel = [{k: v for k, v in r.items() if k != "close_f"} for r in self.rows if int(r["timestamp"]) >= start]
        return {"data": {"pair": "BTC/USD", "ohlc": sel[:limit]}}


def test_reponse_bitstamp_convertie_au_schema_de_load_ohlc():
    d = parse_ohlc({"data": {"ohlc": [
        {"timestamp": "1356998400", "open": "13.3", "high": "13.4", "low": "13.2", "close": "13.35", "volume": "2.5"},
        {"timestamp": "1356996600", "open": "13.1", "high": "13.3", "low": "13.1", "close": "13.3", "volume": "0"}]}})
    assert list(d.columns) == ["time", "timestamp", "open", "high", "low", "close", "volume"]
    assert d.time.tolist() == [pd.Timestamp("2012-12-31 23:30", tz="UTC"), pd.Timestamp("2013-01-01 00:00", tz="UTC")]
    assert d.timestamp.dtype == "int64" and d.iloc[1][["open", "close", "volume"]].tolist() == [13.3, 13.35, 2.5]


def test_pages_de_1000_barres_bornes_demi_ouvertes_sans_perte_ni_doublon():
    fake = FakeBitstamp("2013-01-01", "2013-03-01")
    d = fetch_ohlc("btcusd", "2013-01-10", "2013-02-20", fetch=fake)
    want = pd.date_range("2013-01-10", "2013-02-20", freq="30min", tz="UTC", inclusive="left")
    assert d.time.tolist() == list(want)                                  # début inclus, fin exclue, aucun trou
    assert len(fake.urls) == int(np.ceil(len(want) / 1000))
    assert not d.time.duplicated().any() and (d.volume == 0).sum() > 0    # barres sans transaction gardées


def test_doublons_identiques_fusionnes_contradictoires_refuses():
    fake = FakeBitstamp("2013-01-01", "2013-02-01")

    def repeated(url, **change):                # chaque page sert deux fois sa dernière barre
        p = fake(url)
        p["data"]["ohlc"].append(dict(p["data"]["ohlc"][-1], **change))
        return p
    d = fetch_ohlc("btcusd", "2013-01-01", "2013-02-01", fetch=repeated)
    assert d.time.is_unique and len(d) == 31 * 48
    with pytest.raises(ValueError, match="valeurs différentes"):
        fetch_ohlc("btcusd", "2013-01-01", "2013-02-01", fetch=lambda u: repeated(u, close="999999"))


def test_reserve_2026_refusee():
    fake = FakeBitstamp("2025-12-30", "2026-01-02")
    with pytest.raises(ValueError, match="réserve 2026"):
        fetch_ohlc("btcusd", "2025-12-30", "2026-01-02", fetch=fake)
    with pytest.raises(ValueError, match="réserve 2026"):
        build_bitstamp_csv("btcusd", 2025, 2026, "x.csv", "c", None, fake)
    assert fake.urls == []                                                # rien n'est demandé


def test_csv_annees_completes_avec_meta_cache_et_lecture_par_load_ohlc(tmp_path):
    fake = FakeBitstamp("2013-01-01", "2015-01-01")
    out = tmp_path / "raw" / "bitstamp_btcusd_30m_2013_2014.csv"
    meta = build_bitstamp_csv("btcusd", 2013, 2014, out, tmp_path / "cache", {"instrument": "BTC/USD"}, fake)
    d = load_ohlc(out)
    assert len(d) == meta["n_rows"] == (365 * 2) * 48 and not d.attrs["gaps"]
    assert meta["first"] == "2013-01-01 00:00:00+00:00" and meta["last"] == "2014-12-31 23:30:00+00:00"
    assert meta["instrument"] == "BTC/USD" and [f["annee"] for f in meta["fichiers_annuels"]] == [2013, 2014]
    assert sum(meta["barres_volume_nul_par_an"].values()) == int((d.volume == 0).sum()) > 0
    assert json.loads(out.with_name(out.stem + ".meta.json").read_text(encoding="utf-8"))["sha256"] == meta["sha256"]
    raw = [r for r in fake.rows if int(r["timestamp"]) < 1420070400]
    assert d.close.tolist() == [float(r["close"]) for r in raw]           # valeurs servies, intactes
    n = len(fake.urls)
    meta2 = build_bitstamp_csv("btcusd", 2013, 2014, out, tmp_path / "cache", {"instrument": "BTC/USD"}, fake)
    assert len(fake.urls) == n and meta2["sha256"] == meta["sha256"]      # années relues depuis le cache, à l'identique
