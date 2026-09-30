"""EXP-D01 — acquisition Coinbase (sans réseau : API simulée), agrégation exacte 15 min → 30 min, audit des barres."""
from urllib.parse import parse_qs, urlparse

import numpy as np
import pandas as pd
import pytest

from marketdata import aggregate_30m, audit_bars, build_coinbase_csv, fetch_candles, parse_candles
from utils.data_loader import load_ohlc


class FakeCoinbase:
    """API simulée : bougies de 15 min d'un ensemble fixe, renvoyées de la plus récente à la plus ancienne, bornes
    start et end incluses, au plus 300 par requête (sinon erreur, comme l'API réelle)."""

    def __init__(self, times: pd.DatetimeIndex, seed: int = 0):
        rng = np.random.default_rng(seed)
        c = 100 * np.exp(np.cumsum(rng.normal(0, 0.002, len(times))))
        self.rows = [[int(t.timestamp()), ci * 0.99, ci * 1.01, ci * 0.999, ci, 1.0 + k % 3]
                     for k, (t, ci) in enumerate(zip(times, c))]
        self.urls = []

    def __call__(self, url: str):
        self.urls.append(url)
        q = parse_qs(urlparse(url).query)
        g = int(q["granularity"][0])
        a, b = (pd.Timestamp(q[k][0]).timestamp() for k in ("start", "end"))
        if (b - a) / g + 1 > 300:
            raise ValueError("granularity too small for the requested time range")
        return [r for r in reversed(self.rows) if a <= r[0] <= b]


def test_colonnes_coinbase_remises_dans_l_ordre_ohlc():
    d = parse_candles([[1623945600, 39.8, 40.5, 40.0, 40.037, 5454.7], [1623944700, 39.0, 41.0, 40.2, 39.9, 10.0]])
    assert d.time.tolist() == [pd.Timestamp("2021-06-17 15:45", tz="UTC"), pd.Timestamp("2021-06-17 16:00", tz="UTC")]
    assert d.iloc[1][["open", "high", "low", "close", "volume"]].tolist() == [40.0, 40.5, 39.8, 40.037, 5454.7]


def test_agregation_exacte_en_30_min_alignee_et_quart_d_heure_isole_garde():
    t = pd.to_datetime(["2022-03-01 10:00", "2022-03-01 10:15", "2022-03-01 10:30", "2022-03-01 11:15"], utc=True)
    c = pd.DataFrame({"time": t, "open": [10, 11, 12, 13], "high": [11.5, 12, 12.5, 14], "low": [9.5, 10.5, 11.5, 12],
                      "close": [11, 12, 12.2, 13.5], "volume": [1, 2, 3, 4]})
    b = aggregate_30m(c.iloc[::-1])                                          # ordre d'entrée indifférent
    assert b.time.tolist() == list(pd.to_datetime(["2022-03-01 10:00", "2022-03-01 10:30", "2022-03-01 11:00"],
                                                  utc=True))
    assert b.iloc[0][["open", "high", "low", "close", "volume", "n_sub"]].tolist() == [10, 12, 9.5, 12, 3, 2]
    assert b.iloc[1][["open", "close", "n_sub"]].tolist() == [12, 12.2, 1]
    assert b.iloc[2][["open", "high", "low", "close", "n_sub"]].tolist() == [13, 14, 12, 13.5, 1]
    assert b.timestamp.tolist() == [int(x.timestamp()) for x in b.time]


def test_fenetres_de_300_bougies_sans_perte_ni_doublon():
    times = pd.date_range("2021-06-17 16:00", "2021-06-30 23:45", freq="15min", tz="UTC").delete([5, 6, 700])
    fake = FakeCoinbase(times)
    c = fetch_candles("SOL-USD", "2021-06-01", "2021-07-01", 900, fake)
    assert c.time.tolist() == list(times) and len(fake.urls) == int(np.ceil(30 * 96 / 300))
    assert c.close.tolist() == [r[4] for r in fake.rows]


def test_reserve_2026_refusee():
    with pytest.raises(ValueError, match="réserve 2026"):
        fetch_candles("SOL-USD", "2025-12-30", "2026-01-02", 900, FakeCoinbase(pd.DatetimeIndex([], tz="UTC")))
    with pytest.raises(ValueError, match="réserve 2026"):
        build_coinbase_csv("SOL-USD", "2025-12", "2026-01", "x.csv", "c", None, FakeCoinbase(pd.DatetimeIndex([])))


def test_csv_au_schema_de_load_ohlc_avec_meta_et_cache(tmp_path):
    times = pd.date_range("2021-06-17 16:00", "2021-07-02 03:45", freq="15min", tz="UTC").delete([10, 11])
    fake = FakeCoinbase(times)
    out = tmp_path / "raw" / "coinbase_solusd_30m.csv"
    meta = build_coinbase_csv("SOL-USD", "2021-06", "2021-07", out, tmp_path / "cache", {"instrument": "SOL/USD"},
                              fake)
    assert list(pd.read_csv(out).columns) == ["time", "timestamp", "open", "high", "low", "close", "volume"]
    assert meta["instrument"] == "SOL/USD" and [f["mois"] for f in meta["fichiers_15m"]] == ["2021-06", "2021-07"]
    assert meta["n_rows"] == len(aggregate_30m(fake_frame(fake))) and meta["n_barres_un_seul_quart_d_heure"] == 0
    with pytest.warns(UserWarning, match="trou"):
        df = load_ohlc(out)                                                  # 10 et 11 : une barre entière absente
    assert len(df) == meta["n_rows"] and df.time.iat[0] == pd.Timestamp("2021-06-17 16:00", tz="UTC")
    n = len(fake.urls)
    build_coinbase_csv("SOL-USD", "2021-06", "2021-07", out, tmp_path / "cache", None, fake)
    assert len(fake.urls) == n                                               # mois relus depuis le cache


def fake_frame(fake: FakeCoinbase) -> pd.DataFrame:
    return parse_candles(fake.rows)


def test_audit_trous_incoherences_volume_et_sauts():
    t = pd.to_datetime(["2024-01-05 20:00", "2024-01-05 20:30", "2024-01-05 22:00",       # trou de 1 h
                        "2024-01-07 23:00", "2024-01-07 23:30"], utc=True)                 # week-end
    df = pd.DataFrame({"time": t, "open": [10, 10, 10, 12, 11], "high": [11, 10, 12, 12.5, 11.2],
                       "low": [9, 10, 9, 10.5, 10], "close": [10, 10, 11, 10.8, 11.5], "volume": [1, 0, 1, 1, 1]})
    a = audit_bars(df)                                         # barre 4 : high 11,2 < close 11,5 (incohérence OHLC)
    assert a["n_barres"] == 5 and a["doublons"] == 0 and a["desordre"] == 0
    assert a["trous"]["n"] == 2 and a["trous"]["classes"]["<= 2 h"]["n"] == 1
    assert a["trous"]["classes"]["<= 3 jours"]["n"] == 1 and a["trous"]["classes"]["> 3 jours"]["n"] == 0
    assert a["trous"]["classes"]["<= 2 h"]["barres_manquantes"] == 2
    assert a["trous"]["plus_longs"][0]["apres"].startswith("2024-01-05 22:00")          # le week-end est le plus long
    assert a["incoherences_ohlc"] == 1 and a["barres_plates"] == 1 and a["barres_volume_nul"] == 1
    top = a["sauts"]["plus_grands_ecarts_ouverture"][0]
    assert top["time"].startswith("2024-01-07 23:00") and np.isclose(top["bps"], np.log(12 / 11) * 1e4)
    assert np.isclose(a["sauts"]["ecart_ouverture_apres_trou_bps"]["P100"], np.log(12 / 11) * 1e4)
    assert a["barres_par_jour"] == {4: 3, 6: 2}


# ── HistData (CFD or et WTI) et FRED ───────────────────────────────────────────
HTML_ANNEE = ('<form><input type="hidden" name="tk" value="abc123"><input name="date" value="2020" type="hidden">'
              '<input type="hidden" name="datemonth" value="2020"><input type="hidden" name="platform" value="ASCII">'
              '<input type="hidden" name="timeframe" value="M1"><input type="hidden" name="fxpair" value="XAUUSD">'
              '</form><input type="hidden" name="tk" value="abc123">')


def m1_zip(pair: str, year: int, lines: list[str]) -> bytes:
    import io as _io
    import zipfile as _zf
    buf = _io.BytesIO()
    with _zf.ZipFile(buf, "w") as z:
        z.writestr(f"DAT_ASCII_{pair}_M1_{year}.csv", "\n".join(lines) + "\n")
        z.writestr(f"DAT_ASCII_{pair}_M1_{year}.txt", "rapport")
    return buf.getvalue()


class FakeHistData:
    def __init__(self, years: dict):
        self.years, self.posts = years, []

    def get(self, url: str) -> str:
        year = int(url.rsplit("/", 1)[1])
        return HTML_ANNEE.replace('value="2020"', f'value="{year}"')

    def post(self, url: str, fields: dict, referer: str) -> bytes:
        self.posts.append((url, dict(fields), referer))
        return m1_zip(fields["fxpair"], int(fields["date"]), self.years[int(fields["date"])])


def test_formulaire_histdata_lu_et_verifie():
    from marketdata import form_fields
    f = form_fields(HTML_ANNEE, "XAUUSD", 2020)
    assert f == {"tk": "abc123", "date": "2020", "datemonth": "2020", "platform": "ASCII", "timeframe": "M1",
                 "fxpair": "XAUUSD"}
    with pytest.raises(ValueError):
        form_fields(HTML_ANNEE, "WTIUSD", 2020)


def test_etiquettes_histdata_converties_en_utc_selon_l_heure_d_ete_europeenne():
    from marketdata import parse_m1
    d = parse_m1("20200101 180000;1518.768;1520.675;1518.768;1519.895;0\n"       # hiver : UTC = étiquette + 5 h
                 "20200715 163000;1800.0;1801.0;1799.5;1800.5;0\n"               # été européen : + 4 h
                 "20210316 170000;1.0;1.0;1.0;1.0;0\n")                          # New York à l'heure d'été, Europe non
    assert d.time.tolist() == [pd.Timestamp("2020-01-01 23:00", tz="UTC"), pd.Timestamp("2020-07-15 20:30", tz="UTC"),
                               pd.Timestamp("2021-03-16 22:00", tz="UTC")]
    assert d.iloc[0][["open", "high", "low", "close"]].tolist() == [1518.768, 1520.675, 1518.768, 1519.895]


def test_csv_histdata_agrege_en_30_min_avec_meta_cache_et_reserve(tmp_path):
    from marketdata import build_histdata_csv
    y2024 = [f"20241231 16{m:02d}00;{100 + m};{101 + m};{99 + m};{100.5 + m};0" for m in range(0, 60)]
    y2025 = [f"20251231 {h}{m:02d}00;{200 + m};{201 + m};{199 + m};{200.5 + m};0" for h in (18, 19) for m in (0, 45)]
    fake = FakeHistData({2024: y2024, 2025: y2025})
    out = tmp_path / "raw" / "histdata_xauusd_30m.csv"
    meta = build_histdata_csv("XAUUSD", 2024, 2025, out, tmp_path / "cache", {"instrument": "CFD or"}, fake)
    df = pd.read_csv(out, parse_dates=["time"])
    # hiver : UTC = étiquette + 5 h. 2024-12-31 16:00-16:59 → 21:00-21:59 UTC : deux barres ; 2025-12-31 18:00 et 18:45
    # → 23:00 et 23:45 UTC : deux barres de 2025 ; 19:00 et 19:45 → 2026-01-01 00:00 et 00:45 UTC : réserve, exclues
    assert df.time.tolist() == list(pd.to_datetime(["2024-12-31 21:00", "2024-12-31 21:30", "2025-12-31 23:00",
                                                    "2025-12-31 23:30"], utc=True))
    assert df.iloc[0][["open", "high", "low", "close"]].tolist() == [100, 130, 99, 129.5]
    assert meta["n_rows"] == 4 and meta["instrument"] == "CFD or" and len(meta["archives"]) == 2
    assert fake.posts[0][1]["tk"] == "abc123" and fake.posts[0][2].endswith("/xauusd/2024")
    n = len(fake.posts)
    build_histdata_csv("XAUUSD", 2024, 2025, out, tmp_path / "cache", None, fake)
    assert len(fake.posts) == n                                                   # archives relues depuis le cache
    with pytest.raises(ValueError, match="réserve 2026"):
        build_histdata_csv("XAUUSD", 2025, 2026, out, tmp_path / "cache", None, fake)


def test_serie_fred_valeurs_manquantes_et_reserve(tmp_path):
    from marketdata import build_fred_csv, parse_fred
    txt = "observation_date,DCOILWTICO\n2020-04-17,18.31\n2020-04-20,-36.98\n2020-04-21,.\n"
    d = parse_fred(txt, "DCOILWTICO")
    assert d.valeur.iloc[1] == -36.98 and np.isnan(d.valeur.iloc[2])
    meta = build_fred_csv("DCOILWTICO", "2020-04-01", "2020-04-30", tmp_path / "f.csv", None,
                          lambda url: txt.encode())
    assert meta["n_rows"] == 3 and meta["n_valeurs"] == 2
    with pytest.raises(ValueError, match="réserve 2026"):
        build_fred_csv("DCOILWTICO", "2025-01-01", "2026-01-05", tmp_path / "g.csv", None, lambda url: txt.encode())


def test_doublons_exacts_supprimes_et_doublons_contradictoires_refuses():
    from marketdata.histdata import drop_exact_duplicates
    t = pd.to_datetime(["2020-10-26 00:00", "2020-10-26 00:01", "2020-10-26 00:00", "2020-10-26 00:01",
                        "2020-10-26 00:02"], utc=True)
    m = pd.DataFrame({"time": t, "open": [1.0, 2, 1, 2, 3], "high": [1.5, 2.5, 1.5, 2.5, 3.5],
                      "low": [0.5, 1.5, 0.5, 1.5, 2.5], "close": [1.2, 2.2, 1.2, 2.2, 3.2], "volume": 0.0})
    out, info = drop_exact_duplicates(m, "test")
    assert out.time.tolist() == list(pd.to_datetime(["2020-10-26 00:00", "2020-10-26 00:01", "2020-10-26 00:02"],
                                                     utc=True))
    assert info == {"n": 2, "dates": ["2020-10-26"]}
    m.loc[3, "close"] = 9.9
    with pytest.raises(ValueError, match="valeurs différentes"):
        drop_exact_duplicates(m, "test")
