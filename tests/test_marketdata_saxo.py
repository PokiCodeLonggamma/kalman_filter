"""EXP-D01.7 — `marketdata.saxo` (Saxo OpenAPI LIVE) sans réseau : PKCE (S256), URL d'autorisation, échange du code et
rafraîchissement (paramètres de la documentation), réserve 2026 avant et après chaque requête de graphique, lecture des
échantillons et des champs de prix, bloc CSV reproductible, clé d'application lue sans être exposée, jeton jamais
présent dans une erreur."""
import base64
import hashlib
import io
import json
import os
import re
import urllib.error
import urllib.parse

import pandas as pd
import pytest

from marketdata import saxo


def test_pkce_s256_conforme_a_la_documentation():
    v, c = saxo.pkce_pair()
    assert 43 <= len(v) <= 128 and re.fullmatch(r"[A-Za-z0-9\-._~]+", v)
    assert c == base64.urlsafe_b64encode(hashlib.sha256(v.encode()).digest()).rstrip(b"=").decode()
    assert saxo.pkce_pair()[0] != v


def test_url_d_autorisation_et_echanges_oauth():
    url = saxo.authorize_url("APPKEY", "http://localhost:47321/akf-callback", "ETAT", "DEFI")
    p = urllib.parse.urlparse(url)
    q = dict(urllib.parse.parse_qsl(p.query))
    assert f"{p.scheme}://{p.netloc}{p.path}" == "https://live.logonvalidation.net/authorize"
    assert q == {"response_type": "code", "client_id": "APPKEY", "state": "ETAT",
                 "redirect_uri": "http://localhost:47321/akf-callback", "code_challenge": "DEFI",
                 "code_challenge_method": "S256"}
    sent = []
    post = lambda url, form: sent.append((url, form)) or {"access_token": "x", "expires_in": 1200}  # noqa: E731
    saxo.exchange_code("APPKEY", "CODE", "http://localhost:1/akf-callback", "VERIF", post=post)
    saxo.refresh("RT", "VERIF", post=post)
    assert sent[0] == ("https://live.logonvalidation.net/token",
                       {"grant_type": "authorization_code", "client_id": "APPKEY", "code": "CODE",
                        "redirect_uri": "http://localhost:1/akf-callback", "code_verifier": "VERIF"})
    assert sent[1][1] == {"grant_type": "refresh_token", "refresh_token": "RT", "code_verifier": "VERIF"}


def test_reserve_2026_avant_la_requete():
    saxo.check_window(pd.Timestamp("2025-12-31T23:30:00Z"), "UpTo", 1200, 30)
    saxo.check_window(pd.Timestamp("2025-12-01T00:00:00Z"), "From", 1200, 30)       # finit le 2025-12-25
    with pytest.raises(ValueError):
        saxo.check_window(pd.Timestamp("2026-01-01T00:00:00Z"), "UpTo", 10, 30)
    with pytest.raises(ValueError):
        saxo.check_window(pd.Timestamp("2025-12-20T00:00:00Z"), "From", 1200, 30)   # atteindrait 2026
    with pytest.raises(ValueError):
        saxo.check_window(pd.Timestamp("2020-01-02T00:00:00Z"), "From", 1201, 30)


class FauxClient:
    def __init__(self, body, status=200):
        self.body, self.status, self.params = body, status, None

    def get(self, path, params=None):
        self.path, self.params = path, params
        return self.status, self.body


def _ech(t, **f):
    return {"Time": t, **f}


def test_graphique_parametres_lecture_et_champs_de_prix():
    body = {"ChartInfo": {"FirstSampleTime": "2016-01-04T00:00:00.000000Z", "DelayedByMinutes": 0, "Horizon": 30},
            "Data": [_ech("2020-01-02T00:30:00Z", OpenBid=1, HighBid=2, LowBid=0.5, CloseBid=1.5, OpenAsk=1.1,
                          HighAsk=2.1, LowAsk=0.6, CloseAsk=1.6),
                     _ech("2020-01-02T00:00:00Z", OpenBid=1, HighBid=2, LowBid=0.5, CloseBid=1.5, OpenAsk=1.1,
                          HighAsk=2.1, LowAsk=0.6, CloseAsk=1.6)]}
    c = FauxClient(body)
    st, b = saxo.get_chart(c, 4912, "CfdOnIndex", 30, "From", pd.Timestamp("2020-01-02", tz="UTC"), 1200)
    assert st == 200 and c.path == "/chart/v3/charts"
    assert c.params == {"AssetType": "CfdOnIndex", "Uic": 4912, "Horizon": 30, "Mode": "From",
                        "Time": "2020-01-02T00:00:00Z", "Count": 1200, "FieldGroups": "ChartInfo,Data,DisplayAndFormat"}
    df = saxo.samples_frame(b)
    assert list(df.time.astype(str)) == ["2020-01-02 00:00:00+00:00", "2020-01-02 00:30:00+00:00"]
    assert saxo.price_fields(df) == {"bid_ask": saxo.BID_ASK, "dernier": [], "volume": [], "autres": []}
    saxo.get_chart(c, 1, "CfdOnIndex", 30, "From", pd.Timestamp("2020-01-02", tz="UTC"), 10, extended_hours=True)
    assert c.params["ExtendedHoursEnabled"] == "true"


def test_barre_de_2026_recue_est_une_erreur():
    c = FauxClient({"Data": [_ech("2026-01-02T00:00:00Z", Open=1, High=1, Low=1, Close=1)]})
    with pytest.raises(RuntimeError):
        saxo.get_chart(c, 1, "ContractFutures", 30, "UpTo", pd.Timestamp("2025-12-31T23:30:00Z"), 5)


def test_bloc_csv_reproductible(tmp_path):
    df = saxo.samples_frame({"Data": [_ech("2020-01-02T00:00:00Z", Open=1.0, High=2.0, Low=0.5, Close=1.5, Volume=3)]})
    m1 = saxo.write_block(df, tmp_path / "a.csv", {"uic": 1})
    m2 = saxo.write_block(df, tmp_path / "b.csv", {"uic": 1})
    assert m1["sha256"] == m2["sha256"] and m1["n_rows"] == 1 and m1["first"] == "2020-01-02T00:00:00Z"
    assert json.loads((tmp_path / "a.meta.json").read_text(encoding="utf-8"))["uic"] == 1


def test_cle_d_application_environnement_puis_registre_jamais_affichee():
    assert saxo.app_key({"SAXO_APP_KEY": "K1"}, registry=lambda n: "K2") == "K1"
    assert saxo.app_key({}, registry=lambda n: "K2") == "K2"
    with pytest.raises(SystemExit) as e:
        saxo.app_key({}, registry=lambda n: None)
    assert "K" not in str(e.value).replace("SAXO_APP_KEY", "")


def test_jeton_dans_l_en_tete_seulement_jamais_dans_une_erreur(monkeypatch):
    monkeypatch.setenv(saxo.TOKEN_ENV, "JETON-SECRET")
    seen = {}

    def opener(req, timeout):
        seen["auth"] = req.headers.get("Authorization")
        raise urllib.error.HTTPError(req.full_url, 403, "Forbidden", {}, io.BytesIO(b'{"ErrorCode":"Forbidden"}'))

    st, body = saxo.SaxoClient(opener=opener, pause=0).get("/chart/v3/charts", {"Uic": 1})
    assert seen["auth"] == "Bearer JETON-SECRET"
    assert st == 403 and "JETON-SECRET" not in body
