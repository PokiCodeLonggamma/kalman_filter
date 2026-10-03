"""EXP-D04 — levée explicite de la réserve 2026 (`reserve.levee`) : scellée par défaut, ouverte seulement dans le bloc,
rescellée après, même sur erreur ; gardes des lectures (`check_no_holdout`, `strategy.load_asset`) et des
téléchargeurs Bitstamp, Coinbase et HistData (API simulées, sans réseau)."""
import io
import zipfile

import numpy as np
import pandas as pd
import pytest

from estimand.bars import check_no_holdout
from marketdata.bitstamp import build_bitstamp_csv, fetch_ohlc
from marketdata.coinbase import build_coinbase_csv, fetch_candles
from reserve import exiger_levee, levee, motif, scellee
from strategy import load_asset
from test_marketdata import HTML_ANNEE, FakeCoinbase
from test_marketdata_bitstamp import FakeBitstamp
from utils.data_loader import load_ohlc


def test_scellee_par_defaut_levee_dans_le_bloc_seulement():
    assert scellee() and motif() is None
    with levee("D04"):
        assert not scellee() and motif() == "D04"
        with levee("imbrique"):
            assert motif() == "imbrique"
        assert motif() == "D04"
        exiger_levee("test")                                        # ne lève rien dans le bloc
    assert scellee()
    with pytest.raises(ValueError, match="réserve 2026"):
        exiger_levee("test")
    with pytest.raises(RuntimeError):
        with levee("D04"):
            raise RuntimeError("panne")
    assert scellee()                                                # rescellée même après une erreur
    for bad in ("", "  ", None):
        with pytest.raises(ValueError, match="motif"):
            with levee(bad):
                pass


def test_controle_des_barres_et_lecture_d_un_actif(tmp_path, barres_synthetiques):
    df = pd.DataFrame({"time": pd.date_range("2025-12-31 22:00", periods=6, freq="30min", tz="UTC")})
    with pytest.raises(ValueError, match="réserve 2026"):
        check_no_holdout(df)
    with levee("D04"):
        check_no_holdout(df)
    bars = barres_synthetiques(200, start="2025-12-29")
    bars["volume"] = 1.0
    bars["timestamp"] = bars.time.astype("int64") // 10**9
    path = tmp_path / "x_30m.csv"
    bars[["time", "timestamp", "open", "high", "low", "close", "volume"]].to_csv(path, index=False)
    import hashlib
    import json
    meta = {"sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "extracted_at_utc": "2026-02-01T00:00:00+00:00"}
    path.with_name(path.stem + ".meta.json").write_text(json.dumps(meta), encoding="utf-8")
    d, b = load_asset(path)                                         # défaut : tronqué avant 2026
    assert b.time.max() < pd.Timestamp("2026-01-01", tz="UTC")
    with pytest.raises(ValueError, match="réserve 2026"):
        load_asset(path, end="2026-01-02")
    with levee("D04"):
        d2, b2 = load_asset(path, end="2026-01-02")
    assert b2.time.max() == pd.Timestamp("2026-01-01 23:30", tz="UTC")
    assert b2[b2.time < "2026-01-01"].equals(b)                     # même passé, à l'identique


def test_bitstamp_annee_partielle_levee_et_page_vide(tmp_path):
    fake = FakeBitstamp("2025-12-01", "2026-03-01")
    with pytest.raises(ValueError, match="réserve 2026"):
        build_bitstamp_csv("btcusd", 2025, 2026, tmp_path / "o.csv", tmp_path / "c", None, fake, end="2026-02-01")
    assert fake.urls == []
    with levee("D04"):
        meta = build_bitstamp_csv("btcusd", 2025, 2026, tmp_path / "o.csv", tmp_path / "c", None, fake,
                                  end="2026-02-01")
        with pytest.raises(ValueError, match="hors de l'année"):
            build_bitstamp_csv("btcusd", 2025, 2026, tmp_path / "p.csv", tmp_path / "c", None, fake, end="2027-02-01")
    d = load_ohlc(tmp_path / "o.csv")
    assert d.time.iat[0] == pd.Timestamp("2025-12-01", tz="UTC") and d.time.iat[-1] == pd.Timestamp("2026-01-31 23:30",
                                                                                                    tz="UTC")
    assert len(d) == 62 * 48 and meta["reserve_levee"] == "D04" and meta["fin_exclue"].startswith("2026-02-01")
    names = sorted(p.name for p in (tmp_path / "c").iterdir())
    assert names == ["bitstamp_btcusd_1800s_2025.csv", "bitstamp_btcusd_1800s_2026_avant_20260201.csv"]
    with pytest.raises(ValueError, match="futur"):
        with levee("D04"):
            build_bitstamp_csv("btcusd", 2026, 2026, tmp_path / "q.csv", tmp_path / "c", None, fake)


def test_bitstamp_paire_cotee_en_cours_d_annee_et_page_vide(tmp_path):
    late = FakeBitstamp("2013-03-10", "2014-01-01")                 # paire cotée à partir du 10 mars 2013
    meta = build_bitstamp_csv("xrpusd", 2012, 2013, tmp_path / "x.csv", tmp_path / "c", None, late)
    d = load_ohlc(tmp_path / "x.csv")
    assert d.time.iat[0] == pd.Timestamp("2013-03-10", tz="UTC") and len(d) == (365 - 68) * 48
    assert [f["barres"] for f in meta["fichiers_annuels"]] == [0, (365 - 68) * 48]   # 2012 : année vide
    with pytest.raises(RuntimeError, match="aucune barre"):
        fetch_ohlc("xrpusd", "2013-01-01", "2013-02-01", fetch=lambda url: {"data": {"ohlc": []}})


def test_coinbase_mois_de_2026_dans_le_bloc_seulement(tmp_path):
    times = pd.date_range("2025-12-01", "2026-02-01", freq="15min", tz="UTC", inclusive="left")
    fake = FakeCoinbase(times)
    with pytest.raises(ValueError, match="réserve 2026"):
        build_coinbase_csv("SOL-USD", "2025-12", "2026-01", tmp_path / "o.csv", tmp_path / "c", None, fake)
    assert fake.urls == []
    with levee("D04"):
        meta = build_coinbase_csv("SOL-USD", "2025-12", "2026-01", tmp_path / "o.csv", tmp_path / "c", None, fake)
        assert fetch_candles("SOL-USD", "2026-01-01", "2026-01-02", 900, fake).time.iat[0] == times[31 * 96]
        with pytest.raises(ValueError, match="pas terminé"):
            build_coinbase_csv("SOL-USD", "2099-01", "2099-01", tmp_path / "f.csv", tmp_path / "c", None, fake)
    d = load_ohlc(tmp_path / "o.csv")
    assert len(d) == 62 * 48 and meta["reserve_levee"] == "D04"


def _zip(name: str, lines: list[str]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr(f"{name}.csv", "\n".join(lines) + "\n")
    return buf.getvalue()


class FakeHistDataMois:
    """Pages annuelles (2025) et mensuelles (2026, `…/2026/<mois>`) ; formulaire avec `datemonth` = AAAAMM."""

    def __init__(self, data: dict):
        self.data, self.posts = data, []

    def get(self, url: str) -> str:
        parts = url.rstrip("/").split("/")
        if parts[-2] == "2026":
            y, m = 2026, int(parts[-1])
            return (HTML_ANNEE.replace('name="date" value="2020"', 'name="date" value="2026"')
                    .replace('name="datemonth" value="2020"', f'name="datemonth" value="2026{m:02d}"'))
        y = int(parts[-1])
        return HTML_ANNEE.replace('value="2020"', f'value="{y}"')

    def post(self, url: str, fields: dict, referer: str) -> bytes:
        self.posts.append(dict(fields))
        tag = fields["datemonth"] if fields["date"] == "2026" else fields["date"]
        return _zip(f"DAT_ASCII_{fields['fxpair']}_M1_{tag}", self.data[tag])


def test_histdata_archives_mensuelles_de_2026_dans_le_bloc_seulement(tmp_path):
    from marketdata import build_histdata_csv
    y2025 = [f"20251231 {h}{m:02d}00;{200 + m};{201 + m};{199 + m};{200.5 + m};0" for h in (18, 19) for m in (0, 45)]
    jan = [f"20260105 10{m:02d}00;{300 + m};{301 + m};{299 + m};{300.5 + m};0" for m in (0, 15)]
    fev = [f"20260210 10{m:02d}00;{400 + m};{401 + m};{399 + m};{400.5 + m};0" for m in (0, 40)]
    fake = FakeHistDataMois({"2025": y2025, "202601": jan, "202602": fev})
    out = tmp_path / "x.csv"
    with pytest.raises(ValueError, match="réserve 2026"):
        build_histdata_csv("XAUUSD", 2025, 2025, out, tmp_path / "c", None, fake, months=[(2026, 1)],
                           end="2026-03-01")
    assert fake.posts == []
    with levee("D04"):
        meta = build_histdata_csv("XAUUSD", 2025, 2025, out, tmp_path / "c", None, fake,
                                  months=[(2026, 1), (2026, 2)], end="2026-03-01")
    df = pd.read_csv(out, parse_dates=["time"])
    # hiver : UTC = étiquette + 5 h ; les minutes du 31/12 au soir tombant en 2026 sont désormais gardées
    want = ["2025-12-31 23:00", "2025-12-31 23:30", "2026-01-01 00:00", "2026-01-01 00:30", "2026-01-05 15:00",
            "2026-02-10 15:00", "2026-02-10 15:30"]
    assert df.time.tolist() == list(pd.to_datetime(want, utc=True))
    assert [p["datemonth"] for p in fake.posts[1:]] == ["202601", "202602"]
    assert [a["archive"] for a in meta["archives"]] == ["HISTDATA_COM_ASCII_XAUUSD_M12025.zip",
                                                        "HISTDATA_COM_ASCII_XAUUSD_M1202601.zip",
                                                        "HISTDATA_COM_ASCII_XAUUSD_M1202602.zip"]
    assert meta["reserve_levee"] == "D04"
    with pytest.raises(ValueError, match="pas terminé"):
        with levee("D04"):
            build_histdata_csv("XAUUSD", 2025, 2025, out, tmp_path / "c", None, fake, months=[(2099, 1)],
                               end="2099-02-01")


def test_formulaire_mensuel_verifie():
    from marketdata.histdata import form_fields
    html = (HTML_ANNEE.replace('name="date" value="2020"', 'name="date" value="2026"')
            .replace('name="datemonth" value="2020"', 'name="datemonth" value="202603"'))
    assert form_fields(html, "XAUUSD", 2026, 3)["datemonth"] == "202603"
    with pytest.raises(ValueError, match="2026-04"):
        form_fields(html, "XAUUSD", 2026, 4)
