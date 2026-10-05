"""EXP-D05.1 — `marketdata.ctrader` (cTrader Open API, JSON sur WebSocket) sans réseau : URL d'autorisation et point
jeton (paramètres de la documentation), secrets lus sans être exposés, requêtes appariées par clientMsgId (battements et
événements ignorés), erreurs et limite de débit, cadence des requêtes d'historique, battement après un silence,
authentification de l'application puis du compte, symboles par nom exact, barres relatives converties en prix,
téléchargement à rebours par fenêtres, réserve 2026, écriture au schéma de `load_ohlc`."""
import json
import urllib.parse

import pandas as pd
import pytest

import reserve
from marketdata import ctrader


# ── OAuth et secrets ────────────────────────────────────────────────────────────
def test_url_d_autorisation_en_lecture_seule():
    url = ctrader.grant_url("CID", "http://localhost:47322/akf-ctrader")
    p = urllib.parse.urlparse(url)
    assert f"{p.scheme}://{p.netloc}{p.path}" == "https://id.ctrader.com/my/settings/openapi/grantingaccess/"
    assert dict(urllib.parse.parse_qsl(p.query)) == {"client_id": "CID", "redirect_uri": "http://localhost:47322/akf-ctrader",
                                                     "scope": "accounts", "product": "web"}


def test_echange_du_code_et_rafraichissement_au_point_jeton():
    vus = []
    ok = {"accessToken": "AT", "tokenType": "bearer", "expiresIn": 2628000, "refreshToken": "RT", "errorCode": None,
          "description": None}
    get = lambda url: vus.append(url) or ok  # noqa: E731
    assert ctrader.exchange_code("CID", "s3cr3t", "c0de", "http://localhost:1/akf-ctrader", get=get)["accessToken"] == "AT"
    ctrader.refresh("CID", "s3cr3t", "RT0", get=get)
    p0, p1 = (urllib.parse.urlparse(u) for u in vus)
    assert f"{p0.scheme}://{p0.netloc}{p0.path}" == "https://openapi.ctrader.com/apps/token"
    assert dict(urllib.parse.parse_qsl(p0.query)) == {"grant_type": "authorization_code", "code": "c0de",
                                                      "redirect_uri": "http://localhost:1/akf-ctrader",
                                                      "client_id": "CID", "client_secret": "s3cr3t"}
    assert dict(urllib.parse.parse_qsl(p1.query)) == {"grant_type": "refresh_token", "refresh_token": "RT0",
                                                      "client_id": "CID", "client_secret": "s3cr3t"}


def test_jeton_refuse_sans_exposer_le_secret_ni_le_code():
    get = lambda url: {"accessToken": None, "errorCode": "ACCESS_DENIED", "description": "expiré"}  # noqa: E731
    with pytest.raises(SystemExit) as e:
        ctrader.exchange_code("CID", "s3cr3t", "c0de-123", "http://localhost:1/x", get=get)
    assert "ACCESS_DENIED" in str(e.value) and "s3cr3t" not in str(e.value) and "c0de-123" not in str(e.value)


def test_secret_lu_dans_le_processus_puis_le_registre_utilisateur():
    assert ctrader.secret("CTRADER_CLIENT_ID", env={"CTRADER_CLIENT_ID": "a"}, registry=lambda n: "b") == "a"
    assert ctrader.secret("CTRADER_CLIENT_ID", env={}, registry=lambda n: "b") == "b"
    with pytest.raises(SystemExit) as e:
        ctrader.secret("CTRADER_CLIENT_SECRET", env={}, registry=lambda n: None)
    assert "CTRADER_CLIENT_SECRET" in str(e.value)


# ── Transport ───────────────────────────────────────────────────────────────────
class FausseConnexion:
    """Répond à chaque requête par la réponse scriptée de son payloadType ; `avant` : messages bruts (battement,
    événement) servis avant la première réponse."""

    def __init__(self, reponses, avant=()):
        self.reponses = {k: list(v) for k, v in reponses.items()}
        self.envoyes, self.file, self.avant = [], [], list(avant)

    def send(self, texte):
        msg = json.loads(texte)
        self.envoyes.append(msg)
        if msg["payloadType"] == 51:
            return
        self.file.extend(self.avant)
        self.avant = []
        pt, payload = self.reponses[msg["payloadType"]].pop(0)
        self.file.append(json.dumps({"clientMsgId": msg["clientMsgId"], "payloadType": pt, "payload": payload}))

    def recv(self):
        return self.file.pop(0)

    def close(self):
        pass


class Horloge:
    def __init__(self):
        self.t, self.pauses = 0.0, []

    def __call__(self):
        return self.t

    def dormir(self, s):
        self.pauses.append(s)
        self.t += s


def _client(conn, env="demo"):
    h = Horloge()
    return ctrader.CTraderClient(conn, env=env, clock=h, sleep=h.dormir), h


def test_requete_appariee_par_identifiant_malgre_battements_et_evenements():
    battement = json.dumps({"payloadType": 51, "payload": {}})
    evenement = json.dumps({"clientMsgId": "autre", "payloadType": 2131, "payload": {}})
    conn = FausseConnexion({2100: [(2101, {})]}, avant=[battement, evenement])
    c, _ = _client(conn)
    assert c.request(2100, {"clientId": "CID", "clientSecret": "s"}, 2101) == {}
    m = conn.envoyes[0]
    assert m["payloadType"] == 2100 and m["payload"] == {"clientId": "CID", "clientSecret": "s"} and m["clientMsgId"]


def test_erreur_du_serveur_levee_avec_son_code_sans_le_jeton():
    conn = FausseConnexion({2149: [(2142, {"errorCode": "CH_ACCESS_TOKEN_INVALID", "description": "Invalid token"})]})
    c, _ = _client(conn)
    with pytest.raises(ctrader.CTraderError) as e:
        c.request(2149, {"accessToken": "jeton-secret"}, 2150)
    assert e.value.code == "CH_ACCESS_TOKEN_INVALID" and "jeton-secret" not in str(e.value)


def test_limite_de_debit_attend_le_delai_puis_renvoie():
    conn = FausseConnexion({2137: [(2142, {"errorCode": "BLOCKED_PAYLOAD_TYPE", "retryAfter": 2}),
                                   (2138, {"trendbar": []})]})
    c, h = _client(conn)
    assert c.request(2137, {"symbolId": 1}, 2138) == {"trendbar": []}
    assert 2 in h.pauses and [m["payloadType"] for m in conn.envoyes] == [2137, 2137]


def test_requetes_d_historique_espacees_d_un_quart_de_seconde():
    conn = FausseConnexion({2137: [(2138, {}), (2138, {})], 2114: [(2115, {})]})
    c, h = _client(conn)
    c.request(2137, {}, 2138)
    c.request(2114, {}, 2115)
    c.request(2137, {}, 2138)
    assert h.pauses == [pytest.approx(0.25)]


def test_battement_envoye_apres_un_silence_de_neuf_secondes():
    conn = FausseConnexion({2114: [(2115, {}), (2115, {})]})
    c, h = _client(conn)
    c.request(2114, {}, 2115)
    h.t += 9.5
    c.request(2114, {}, 2115)
    assert [m["payloadType"] for m in conn.envoyes] == [2114, 51, 2114]


# ── Authentification ────────────────────────────────────────────────────────────
def _comptes(*comptes):
    return {"accessToken": "AT", "permissionScope": "SCOPE_VIEW", "ctidTraderAccount": list(comptes)}


def test_authentification_application_puis_compte_choisi_par_login():
    comptes = _comptes({"ctidTraderAccountId": 11, "isLive": False, "traderLogin": 501, "brokerTitleShort": "FTMO"},
                       {"ctidTraderAccountId": 12, "isLive": False, "traderLogin": "502", "brokerTitleShort": "FTMO"})
    conn = FausseConnexion({2100: [(2101, {})], 2149: [(2150, comptes)], 2102: [(2103, {"ctidTraderAccountId": 12})]})
    c, _ = _client(conn)
    compte = ctrader.authenticate(c, "CID", "s3cr3t", "AT", login=502)
    assert compte["ctidTraderAccountId"] == 12 and compte["brokerTitleShort"] == "FTMO" and not compte["isLive"]
    assert [m["payloadType"] for m in conn.envoyes] == [2100, 2149, 2102]
    assert conn.envoyes[2]["payload"] == {"ctidTraderAccountId": 12, "accessToken": "AT"}


def test_compte_ambigu_ou_d_un_autre_environnement_refuse():
    deux = _comptes({"ctidTraderAccountId": 11, "isLive": False, "traderLogin": 501},
                    {"ctidTraderAccountId": 12, "isLive": False, "traderLogin": 502})
    c, _ = _client(FausseConnexion({2100: [(2101, {})], 2149: [(2150, deux)]}))
    with pytest.raises(SystemExit) as e:                               # deux comptes, aucun login : pas de choix implicite
        ctrader.authenticate(c, "CID", "s3cr3t", "AT")
    assert "501" in str(e.value) and "502" in str(e.value) and "s3cr3t" not in str(e.value)
    live = _comptes({"ctidTraderAccountId": 13, "isLive": True, "traderLogin": 503})
    c, _ = _client(FausseConnexion({2100: [(2101, {})], 2149: [(2150, live)]}), env="demo")
    with pytest.raises(SystemExit):                                    # compte live sur la connexion de démo
        ctrader.authenticate(c, "CID", "s3cr3t", "AT")


# ── Symboles ────────────────────────────────────────────────────────────────────
LEGERS = [{"symbolId": 1, "symbolName": "US100.cash", "enabled": True, "description": "US Tech 100"},
          {"symbolId": 2, "symbolName": "GBPJPY", "enabled": True},
          {"symbolId": 3, "symbolName": "US100", "enabled": False}]


def test_liste_et_fiches_des_symboles():
    conn = FausseConnexion({2114: [(2115, {"ctidTraderAccountId": 12, "symbol": LEGERS})],
                            2116: [(2117, {"ctidTraderAccountId": 12, "symbol": [{"symbolId": 1, "digits": 2,
                                                                                   "swapLong": -5.1}]})]})
    c, _ = _client(conn)
    assert ctrader.symbols_list(c, 12) == LEGERS
    assert ctrader.symbol_specs(c, 12, [1])[0]["swapLong"] == -5.1
    assert conn.envoyes[0]["payload"] == {"ctidTraderAccountId": 12, "includeArchivedSymbols": False}
    assert conn.envoyes[1]["payload"] == {"ctidTraderAccountId": 12, "symbolId": [1]}


def test_symboles_resolus_par_nom_exact_et_recherche_par_motif():
    r = ctrader.resolve(LEGERS, {"US100": "US100.cash", "GBPJPY": "GBPJPY"})
    assert r["US100"]["symbolId"] == 1 and r["GBPJPY"]["symbolId"] == 2
    with pytest.raises(KeyError):
        ctrader.resolve(LEGERS, {"GLE": "GLE.FR"})
    with pytest.raises(ValueError):
        ctrader.resolve(LEGERS + [{"symbolId": 4, "symbolName": "GBPJPY"}], {"GBPJPY": "GBPJPY"})
    assert [s["symbolName"] for s in ctrader.search(LEGERS, "us100")] == ["US100.cash", "US100"]
    assert [s["symbolName"] for s in ctrader.search(LEGERS, "tech")] == ["US100.cash"]


# ── Barres ──────────────────────────────────────────────────────────────────────
def _barre(t, low, d_open, d_high, d_close, volume=10):
    b = {"utcTimestampInMinutes": int(pd.Timestamp(t).timestamp() // 60), "low": low, "deltaOpen": d_open,
         "deltaHigh": d_high, "deltaClose": d_close, "volume": volume, "period": 8}
    return {k: v for k, v in b.items() if v != 0}                      # le JSON de protobuf omet les zéros


def test_barres_relatives_converties_en_prix_aux_digits():
    df = ctrader.bars_frame([_barre("2024-03-01T11:00Z", "1235000", 0, 200, 100, "7"),     # int64 en chaîne
                             _barre("2024-03-01T10:30Z", 1_234_500, 200, 900, 600, 42)], digits=3)
    assert list(df.time) == [pd.Timestamp("2024-03-01T10:30Z"), pd.Timestamp("2024-03-01T11:00Z")]
    r = df.iloc[0]
    assert (r.open, r.high, r.low, r.close, r.volume) == (12.347, 12.354, 12.345, 12.351, 42)
    r = df.iloc[1]
    assert (r.open, r.high, r.low, r.close, r.volume) == (12.35, 12.352, 12.35, 12.351, 7)
    assert (r.low_rel, r.d_open, r.d_high, r.d_close) == (1_235_000, 0, 200, 100)


class FauxServeur:
    """Barres de 30 min des jours ouvrés de [debut, fin) ; renvoie toutes les barres de [from, to] (bornes incluses), au
    plus `bloc`, avec hasMore au-delà."""

    def __init__(self, debut, fin, bloc=1000):
        t = pd.date_range(debut, fin, freq="30min", inclusive="left", tz="UTC")
        self.temps, self.bloc, self.requetes = [x for x in t if x.dayofweek < 5], bloc, []

    def request(self, payload_type, payload, expect):
        assert payload_type == 2137 and expect == 2138 and payload["period"] == 8
        self.requetes.append(payload)
        dedans = [x for x in self.temps if payload["fromTimestamp"] <= x.value // 10**6 <= payload["toTimestamp"]]
        sortie = dedans[-self.bloc:]
        return {"trendbar": [_barre(x, 100_000, 0, 10, 5) for x in sortie], "hasMore": len(dedans) > len(sortie)}


UTC = lambda s: pd.Timestamp(s, tz="UTC")  # noqa: E731


def test_telechargement_a_rebours_par_fenetres_avec_hasmore_et_dedoublonnage():
    srv = FauxServeur("2024-01-01", "2024-03-01", bloc=200)            # 240 barres par semaine : hasMore à 7 jours
    df, res = ctrader.download_trendbars(srv, 12, 1, digits=5, start=UTC("2024-01-01"), end=UTC("2024-03-01"),
                                         window=pd.Timedelta(days=7))
    assert list(df.time) == srv.temps
    assert res["barres"] == len(srv.temps) and res["atteint_le_debut"] and res["fenetres_vides"] == 0
    assert res["fenetre_finale_h"] < 7 * 24
    assert all(p["toTimestamp"] <= UTC("2024-03-01").value // 10**6 for p in srv.requetes)


def test_telechargement_s_arrete_apres_des_fenetres_vides_consecutives():
    srv = FauxServeur("2024-02-05", "2024-03-01")
    df, res = ctrader.download_trendbars(srv, 12, 1, digits=5, start=UTC("2023-01-02"), end=UTC("2024-03-01"),
                                         window=pd.Timedelta(days=7), max_empty=4)
    assert df.time.iat[0] == UTC("2024-02-05") and df.time.iat[-1] == srv.temps[-1]
    assert not res["atteint_le_debut"] and res["fenetres_vides"] == 4


def test_reserve_2026_levee_exigee_pour_depasser_le_1er_janvier():
    srv = FauxServeur("2025-12-29", "2026-01-03")
    debut, fin = UTC("2025-12-29"), UTC("2026-01-03")
    with pytest.raises(ValueError, match="réserve 2026"):
        ctrader.download_trendbars(srv, 12, 1, digits=5, start=debut, end=fin)
    assert srv.requetes == []                                          # refus avant toute requête
    with reserve.levee("test EXP-D05.1"):
        df, _ = ctrader.download_trendbars(srv, 12, 1, digits=5, start=debut, end=fin)
    assert df.time.iat[-1] >= UTC("2026-01-01") and df.time.iat[-1] < fin


def test_ecriture_au_schema_de_load_ohlc_avec_serie_brute_et_empreintes(tmp_path):
    df = ctrader.bars_frame([_barre("2024-03-01T10:30Z", 1_234_500, 200, 900, 600, 42),
                             _barre("2024-03-01T11:00Z", 1_235_000, 0, 200, 100, 7)], digits=3)
    meta = ctrader.write_series(df, tmp_path / "ctrader_ftmo_us100_30m.csv", {"symbolName": "US100.cash"})
    out = pd.read_csv(tmp_path / "ctrader_ftmo_us100_30m.csv")
    assert list(out.columns) == ["time", "timestamp", "open", "high", "low", "close", "volume"]
    assert out.timestamp.tolist() == [int(UTC("2024-03-01T10:30").timestamp()), int(UTC("2024-03-01T11:00").timestamp())]
    brut = pd.read_csv(tmp_path / "ctrader_ftmo_us100_30m_brut.csv")
    assert list(brut.columns) == ["time", "low_rel", "d_open", "d_high", "d_close", "volume"]
    m = json.loads((tmp_path / "ctrader_ftmo_us100_30m.meta.json").read_text(encoding="utf-8"))
    assert m["n_rows"] == 2 and m["sha256"] == meta["sha256"] and m["serie_brute"]["sha256"]
    assert m["symbolName"] == "US100.cash"
