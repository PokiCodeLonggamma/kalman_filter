"""cTrader Open API (Spotware), JSON sur WebSocket : authentification OAuth 2, comptes, symboles, barres historiques
(EXP-D05.1, données du compte FTMO ; aucun backtest).

Documentation officielle suivie (help.ctrader.com/open-api, lue le 2026-10-05) :
- application enregistrée sur le portail https://openapi.ctrader.com, statut « submitted » jusqu'à l'accord de Spotware ;
  Client ID et Client Secret : page Applications, colonne Credentials ; URL de retour ajoutée après l'accord (celle du
  Playground ne vaut que pour le Playground) ;
- code d'autorisation : https://id.ctrader.com/my/settings/openapi/grantingaccess/?client_id&redirect_uri&scope
  &product=web ; scope « accounts » (lecture seule) ou « trading » ; code valable une minute ;
- jeton : GET https://openapi.ctrader.com/apps/token (grant_type=authorization_code, code, redirect_uri, client_id,
  client_secret ; ou grant_type=refresh_token, refresh_token, client_id, client_secret) → accessToken (2 628 000 s,
  ≈ 30 jours), refreshToken sans expiration ; un rafraîchissement invalide les anciens jetons ;
- points d'accès : demo.ctraderapi.com et live.ctraderapi.com ; port 5036 pour le JSON (TCP ou WebSocket) ; démo et live
  séparés ;
- message : {"clientMsgId", "payloadType", "payload"} ; ProtoHeartbeatEvent (51) au moins toutes les 10 s ;
- limites par connexion : 50 requêtes par seconde, 5 pour l'historique ; BLOCKED_PAYLOAD_TYPE avec retryAfter (s) ;
- ProtoOAApplicationAuthReq (2100), ProtoOAGetAccountListByAccessTokenReq (2149), ProtoOAAccountAuthReq (2102),
  ProtoOASymbolsListReq (2114), ProtoOASymbolByIdReq (2116 : digits, swapLong, swapShort, swapRollover3Days,
  swapCalculationType, commission, commissionType, preciseTradingCommissionRate, schedule, scheduleTimeZone, lotSize,
  leverageId, holiday…), ProtoOAGetTrendbarsReq (2137 : fromTimestamp et toTimestamp en ms, period M30 = 8, symbolId,
  count) → trendbar (low, deltaOpen, deltaHigh, deltaClose, volume en ticks, utcTimestampInMinutes = ouverture) et
  hasMore ; prix = valeur relative / 100 000, arrondie aux `digits` du symbole ; erreur : ProtoOAErrorRes (2142).

Secrets : Client ID et Client Secret lus dans CTRADER_CLIENT_ID et CTRADER_CLIENT_SECRET (environnement du processus,
sinon variables d'utilisateur Windows écrites par `setx`). Le jeton d'accès vit dans os.environ["CTRADER_ACCESS_TOKEN"]
du processus, sauf si le porteur l'y a mis lui-même. Rien n'est affiché ni écrit sur disque ; le secret ne part que vers
le point jeton et dans ProtoOAApplicationAuthReq.

Réserve 2026 : un téléchargement qui dépasse le 2026-01-01 exige `reserve.levee(motif)` (décision du porteur du
2026-10-05 : période de 2020-01 à aujourd'hui, 2026 incluse).
"""
from __future__ import annotations

import hashlib
import http.server
import json
import os
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Callable

import numpy as np
import pandas as pd

import reserve

TOKEN_URL = "https://openapi.ctrader.com/apps/token"
GRANT_URL = "https://id.ctrader.com/my/settings/openapi/grantingaccess/"
HOSTS = {"demo": "demo.ctraderapi.com", "live": "live.ctraderapi.com"}
PORT_JSON = 5036
CLIENT_ID_ENV, CLIENT_SECRET_ENV, TOKEN_ENV = "CTRADER_CLIENT_ID", "CTRADER_CLIENT_SECRET", "CTRADER_ACCESS_TOKEN"
CALLBACK_PATH = "/akf-ctrader"
PRICE_SCALE = 100_000
PERIODS = {"M1": 1, "M5": 5, "M15": 7, "M30": 8, "H1": 9, "H4": 10, "D1": 12}
#: ProtoPayloadType (communs) et ProtoOAPayloadType utilisés ici.
PT = {"ERREUR_COMMUNE": 50, "BATTEMENT": 51,
      "APP_AUTH_REQ": 2100, "APP_AUTH_RES": 2101, "COMPTE_AUTH_REQ": 2102, "COMPTE_AUTH_RES": 2103,
      "SYMBOLES_REQ": 2114, "SYMBOLES_RES": 2115, "FICHES_REQ": 2116, "FICHES_RES": 2117,
      "BARRES_REQ": 2137, "BARRES_RES": 2138, "ERREUR": 2142, "TICKS_REQ": 2145,
      "COMPTES_REQ": 2149, "COMPTES_RES": 2150}
HISTORIQUES = {PT["BARRES_REQ"], PT["TICKS_REQ"]}
EVENEMENTS_FATALS = {2147: "jetons invalidés par le serveur", 2148: "client déconnecté par le serveur",
                     2164: "compte déconnecté par le serveur"}
MIN_FENETRE = pd.Timedelta(hours=6)
COLONNES = ["time", "open", "high", "low", "close", "volume", "low_rel", "d_open", "d_high", "d_close"]


# ── Secrets ─────────────────────────────────────────────────────────────────────
def secret(name: str, env=None, registry: Callable[[str], str | None] | None = None) -> str:
    """Valeur d'une variable : environnement du processus, sinon variables d'environnement de l'utilisateur Windows."""
    env = os.environ if env is None else env
    if env.get(name):
        return env[name]
    value = (registry or _user_env_registry)(name)
    if not value:
        raise SystemExit(f"variable d'environnement {name} absente (application cTrader Open API)")
    return value


def _user_env_registry(name: str) -> str | None:
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as k:
            return winreg.QueryValueEx(k, name)[0]
    except (ImportError, OSError):
        return None


# ── OAuth 2 ─────────────────────────────────────────────────────────────────────
def grant_url(client_id: str, redirect_uri: str, scope: str = "accounts") -> str:
    q = {"client_id": client_id, "redirect_uri": redirect_uri, "scope": scope, "product": "web"}
    return f"{GRANT_URL}?{urllib.parse.urlencode(q)}"


def _get_json(url: str) -> dict:
    """GET du point jeton ; une erreur HTTP ne reprend jamais l'URL, qui porte le secret."""
    req = urllib.request.Request(url, headers={"Accept": "application/json", "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        raise SystemExit(f"point jeton cTrader : HTTP {e.code}") from None


def _jeton(rep: dict) -> dict:
    if rep.get("errorCode") or not rep.get("accessToken"):
        raise SystemExit(f"jeton cTrader refusé : {rep.get('errorCode')} ({rep.get('description')})")
    return rep


def exchange_code(client_id: str, client_secret: str, code: str, redirect_uri: str, get=_get_json) -> dict:
    q = {"grant_type": "authorization_code", "code": code, "redirect_uri": redirect_uri, "client_id": client_id,
         "client_secret": client_secret}
    return _jeton(get(f"{TOKEN_URL}?{urllib.parse.urlencode(q)}"))


def refresh(client_id: str, client_secret: str, refresh_token: str, get=_get_json) -> dict:
    q = {"grant_type": "refresh_token", "refresh_token": refresh_token, "client_id": client_id,
         "client_secret": client_secret}
    return _jeton(get(f"{TOKEN_URL}?{urllib.parse.urlencode(q)}"))


def browser_login(client_id: str, client_secret: str, port: int = 47322, scope: str = "accounts",
                  timeout_s: int = 900, on_ready: Callable[[str], None] = print) -> dict:
    """Code d'autorisation par un serveur de retour local (127.0.0.1) : /start redirige vers la page cTrader ID (l'URL,
    qui porte le Client ID, n'est jamais affichée) ; /akf-ctrader reçoit le code, échangé aussitôt (il expire en une
    minute). L'URL http://localhost:<port>/akf-ctrader doit figurer dans les URL de retour de l'application. Le porteur
    se connecte lui-même. Renvoie la réponse du point jeton (jetons en mémoire)."""
    redirect_uri = f"http://localhost:{port}{CALLBACK_PATH}"
    target = grant_url(client_id, redirect_uri, scope)
    box: dict = {}
    done = threading.Event()

    class Handler(http.server.BaseHTTPRequestHandler):
        def log_message(self, *a):                                     # pas de journal : l'URL porte le code
            pass

        def _send(self, code: int, body: str, location: str | None = None):
            self.send_response(code)
            if location:
                self.send_header("Location", location)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(body.encode("utf-8"))

        def do_GET(self):
            url = urllib.parse.urlparse(self.path)
            if url.path == "/start":
                return self._send(302, "", target)
            if url.path != CALLBACK_PATH:
                return self._send(404, "introuvable")
            q = urllib.parse.parse_qs(url.query)
            if "code" in q:
                box["code"] = q["code"][0]
            else:
                box["error"] = f"pas de code : {q.get('error', ['?'])[0]}"
            self._send(200, "<p>Accès reçu. Vous pouvez fermer cet onglet ; le script continue.</p>"
                       if "code" in box else f"<p>Échec : {box.get('error')}</p>")
            done.set()

    server = http.server.ThreadingHTTPServer(("127.0.0.1", port), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    on_ready(f"http://localhost:{port}/start")
    try:
        if not done.wait(timeout_s):
            raise SystemExit("délai de connexion dépassé")
    finally:
        server.shutdown()
    if "code" not in box:
        raise SystemExit(box.get("error", "connexion échouée"))
    return exchange_code(client_id, client_secret, box["code"], redirect_uri)


def access_token(client_id: str, client_secret: str, env=None, registry=None, login=browser_login) -> str:
    """Jeton d'accès : CTRADER_ACCESS_TOKEN (processus, puis utilisateur Windows) s'il existe, sinon connexion par le
    navigateur ; dans ce cas, le jeton n'est gardé que dans os.environ du processus."""
    env = os.environ if env is None else env
    try:
        return secret(TOKEN_ENV, env=env, registry=registry)
    except SystemExit:
        tok = login(client_id, client_secret)
        env[TOKEN_ENV] = tok["accessToken"]
        return tok["accessToken"]


# ── Transport ───────────────────────────────────────────────────────────────────
class CTraderError(RuntimeError):
    def __init__(self, code, description=None):
        self.code, self.description = str(code), description
        super().__init__(f"cTrader : {code}" + (f" ({description})" if description else ""))


def ouvrir(env: str = "demo", timeout: float = 30.0):
    """Connexion WebSocket sécurisée au port JSON (websocket-client)."""
    import websocket
    return websocket.create_connection(f"wss://{HOSTS[env]}:{PORT_JSON}", timeout=timeout)


class CTraderClient:
    """Requêtes JSON synchrones : chaque réponse est appariée à sa requête par clientMsgId ; battements et événements
    sans rapport ignorés ; ProtoOAErrorRes levée en CTraderError (code du serveur, jamais de jeton) ; limite de débit :
    attente de retryAfter puis nouvel envoi ; requêtes d'historique espacées de `pause_hist` (5 par seconde au plus) ;
    battement envoyé avant une requête si rien n'est parti depuis `battement_s`."""

    def __init__(self, conn, env: str = "demo", clock: Callable[[], float] = time.monotonic,
                 sleep: Callable[[float], None] = time.sleep, pause_hist: float = 0.25, battement_s: float = 9.0,
                 essais: int = 5):
        if env not in HOSTS:
            raise ValueError(f"environnement {env!r} : demo ou live")
        self.conn, self.env, self.clock, self.sleep = conn, env, clock, sleep
        self.pause_hist, self.battement_s, self.essais = pause_hist, battement_s, essais
        self._n, self._dernier_envoi, self._dernier_hist = 0, clock(), None
        self.requetes = 0

    def _envoyer(self, payload_type: int, payload: dict, msg_id: str | None = None) -> None:
        msg = {"payloadType": payload_type, "payload": payload}
        if msg_id is not None:
            msg = {"clientMsgId": msg_id, **msg}
        self.conn.send(json.dumps(msg))
        self._dernier_envoi = self.clock()

    def battement(self) -> None:
        self._envoyer(PT["BATTEMENT"], {})

    def _avant(self, payload_type: int) -> None:
        if self.clock() - self._dernier_envoi >= self.battement_s:
            self.battement()
        if payload_type in HISTORIQUES:
            if self._dernier_hist is not None:
                reste = self._dernier_hist + self.pause_hist - self.clock()
                if reste > 0:
                    self.sleep(reste)
            self._dernier_hist = self.clock()

    def request(self, payload_type: int, payload: dict, expect: int) -> dict:
        for _ in range(self.essais):
            self._avant(payload_type)
            self._n += 1
            msg_id = f"akf-{self._n}"
            self._envoyer(payload_type, payload, msg_id)
            self.requetes += 1
            while True:
                m = json.loads(self.conn.recv())
                pt = m.get("payloadType")
                if pt == PT["BATTEMENT"]:
                    continue
                if pt in EVENEMENTS_FATALS:
                    raise CTraderError(pt, EVENEMENTS_FATALS[pt])
                if m.get("clientMsgId") != msg_id:
                    continue
                corps = m.get("payload") or {}
                if pt in (PT["ERREUR"], PT["ERREUR_COMMUNE"]):
                    code = corps.get("errorCode", "?")
                    if code == "BLOCKED_PAYLOAD_TYPE":
                        self.sleep(float(corps.get("retryAfter") or 1.0))
                        break
                    raise CTraderError(code, corps.get("description"))
                if pt != expect:
                    raise CTraderError("REPONSE_INATTENDUE", f"payloadType {pt} au lieu de {expect}")
                return corps
        raise CTraderError("BLOCKED_PAYLOAD_TYPE", f"limite de débit : {self.essais} essais")

    def close(self) -> None:
        self.conn.close()


def connecter(env: str = "demo", **kw) -> CTraderClient:
    return CTraderClient(ouvrir(env), env=env, **kw)


# ── Comptes et symboles ─────────────────────────────────────────────────────────
def authenticate(client: CTraderClient, client_id: str, client_secret: str, access_token: str,
                 login: int | str | None = None) -> dict:
    """Application, liste des comptes accordés au jeton, puis compte choisi par son login (obligatoire s'il y en a
    plusieurs). Le compte doit relever de l'environnement de la connexion (démo ou live)."""
    client.request(PT["APP_AUTH_REQ"], {"clientId": client_id, "clientSecret": client_secret}, PT["APP_AUTH_RES"])
    rep = client.request(PT["COMPTES_REQ"], {"accessToken": access_token}, PT["COMPTES_RES"])
    comptes = rep.get("ctidTraderAccount", [])
    choix = comptes if login is None else [c for c in comptes if str(c.get("traderLogin")) == str(login)]
    if len(choix) != 1:
        liste = "; ".join(f"login {c.get('traderLogin')} ({'live' if c.get('isLive') else 'démo'}, "
                          f"{c.get('brokerTitleShort', '?')})" for c in comptes)
        raise SystemExit(f"compte à préciser par son login : {liste or 'aucun compte accordé à ce jeton'}")
    c = choix[0]
    if bool(c.get("isLive")) != (client.env == "live"):
        raise SystemExit(f"le compte {c.get('traderLogin')} est {'live' if c.get('isLive') else 'démo'} : "
                         f"connexion {client.env} inadaptée")
    acct = int(c["ctidTraderAccountId"])
    client.request(PT["COMPTE_AUTH_REQ"], {"ctidTraderAccountId": acct, "accessToken": access_token},
                   PT["COMPTE_AUTH_RES"])
    return {"ctidTraderAccountId": acct, "isLive": bool(c.get("isLive")), "traderLogin": c.get("traderLogin"),
            "brokerTitleShort": c.get("brokerTitleShort"), "permissionScope": rep.get("permissionScope")}


def symbols_list(client: CTraderClient, acct: int) -> list[dict]:
    rep = client.request(PT["SYMBOLES_REQ"], {"ctidTraderAccountId": acct, "includeArchivedSymbols": False},
                         PT["SYMBOLES_RES"])
    return rep.get("symbol", [])


def symbol_specs(client: CTraderClient, acct: int, ids) -> list[dict]:
    rep = client.request(PT["FICHES_REQ"], {"ctidTraderAccountId": acct, "symbolId": [int(i) for i in ids]},
                         PT["FICHES_RES"])
    return rep.get("symbol", [])


def search(symbols: list[dict], motif: str) -> list[dict]:
    """Symboles dont le nom ou la description contient le motif (casse ignorée), dans l'ordre de la liste."""
    m = motif.lower()
    return [s for s in symbols if m in f"{s.get('symbolName', '')} {s.get('description', '')}".lower()]


def resolve(symbols: list[dict], names: dict[str, str]) -> dict[str, dict]:
    """Code de l'actif → symbole dont le nom est exactement celui demandé (leçon de D01.7) ; absent ou en double :
    erreur."""
    out = {}
    for code, nom in names.items():
        m = [s for s in symbols if s.get("symbolName") == nom]
        if not m:
            raise KeyError(f"{code} : symbole « {nom} » absent")
        if len(m) > 1:
            raise ValueError(f"{code} : « {nom} » ambigu ({len(m)} symboles)")
        out[code] = m[0]
    return out


# ── Barres ──────────────────────────────────────────────────────────────────────
def _ms(t) -> int:
    return int(pd.Timestamp(t).value // 10**6)


def get_trendbars(client, acct: int, symbol_id: int, frm, to, period: str = "M30", count: int | None = None) -> dict:
    payload = {"ctidTraderAccountId": acct, "symbolId": int(symbol_id), "period": PERIODS[period],
               "fromTimestamp": _ms(frm), "toTimestamp": _ms(to)}
    if count:
        payload["count"] = int(count)
    return client.request(PT["BARRES_REQ"], payload, PT["BARRES_RES"])


def bars_frame(trendbars: list[dict], digits: int) -> pd.DataFrame:
    """Barres en DataFrame trié : time (ouverture, UTC), prix = relatif / 100 000 arrondi aux digits, volume en ticks,
    et les entiers relatifs reçus (low_rel, d_open, d_high, d_close). Les champs nuls, omis par le JSON, valent 0."""
    if not trendbars:
        return pd.DataFrame(columns=COLONNES)
    col = lambda k: np.array([int(b.get(k, 0)) for b in trendbars], dtype="int64")  # noqa: E731
    low, d_open, d_high, d_close = col("low"), col("deltaOpen"), col("deltaHigh"), col("deltaClose")
    prix = lambda rel: np.round(rel / PRICE_SCALE, digits)  # noqa: E731
    df = pd.DataFrame({"time": pd.to_datetime(col("utcTimestampInMinutes") * 60, unit="s", utc=True),
                       "open": prix(low + d_open), "high": prix(low + d_high), "low": prix(low),
                       "close": prix(low + d_close), "volume": col("volume"), "low_rel": low, "d_open": d_open,
                       "d_high": d_high, "d_close": d_close})
    return df.sort_values("time").reset_index(drop=True)


def download_trendbars(client, acct: int, symbol_id: int, digits: int, start, end, period: str = "M30",
                       window=pd.Timedelta(days=7), max_empty: int | None = None,
                       before: Callable[[], None] | None = None) -> tuple[pd.DataFrame | None, dict]:
    """Série [start, end) par fenêtres [from, to] successives, de `end` vers le passé. Si le serveur signale hasMore,
    la fenêtre est divisée par deux et la même requête repart (aucune hypothèse sur l'ordre du découpage). Arrêt au
    début, ou après `max_empty` fenêtres vides consécutives (historique plus court que demandé). Au-delà du 2026-01-01,
    la réserve doit être levée. Renvoie les barres (dédoublonnées, triées) et un résumé."""
    start, end = pd.Timestamp(start), pd.Timestamp(end)
    if end > reserve.DEBUT:
        reserve.exiger_levee(f"barres cTrader jusqu'au {end}")
    fenetre = pd.Timedelta(window)
    frames, pages, vides, suite, to, arret = [], 0, 0, 0, end, "debut"
    while to > start:
        if before is not None:
            before()
        frm = max(start, to - fenetre)
        corps = get_trendbars(client, acct, symbol_id, frm, to, period)
        pages += 1
        if corps.get("hasMore"):
            if fenetre / 2 < MIN_FENETRE:
                raise CTraderError("PAGINATION", f"hasMore sur une fenêtre de {fenetre}")
            fenetre = fenetre / 2
            continue
        df = bars_frame(corps.get("trendbar") or [], digits)
        df = df[(df.time >= start) & (df.time < end)] if len(df) else df
        to = frm
        if df.empty:
            vides, suite = vides + 1, suite + 1
            if max_empty is not None and suite >= max_empty:
                arret = "fenetres_vides"
                break
            continue
        suite = 0
        frames.append(df)
    resume = {"pages": pages, "fenetres_vides": vides, "fenetre_finale_h": fenetre / pd.Timedelta(hours=1),
              "atteint_le_debut": arret == "debut"}
    if not frames:
        return None, {**resume, "barres": 0, "erreur": "aucune barre"}
    data = pd.concat(frames, ignore_index=True)
    n0 = len(data)
    dup = data[data.time.duplicated(keep=False)]
    contradictions = int(dup.drop_duplicates(subset=COLONNES).time.duplicated().sum())
    data = data.drop_duplicates("time").sort_values("time").reset_index(drop=True)
    return data, {**resume, "barres": len(data), "doublons_entre_fenetres": n0 - len(data),
                  "valeurs_contradictoires": contradictions, "premiere": str(data.time.iat[0]),
                  "derniere": str(data.time.iat[-1])}


# ── Écriture ────────────────────────────────────────────────────────────────────
def _sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _meta(path: Path, meta: dict) -> None:
    path.with_name(path.stem + ".meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")


def write_series(df: pd.DataFrame, out_csv: Path, meta: dict) -> dict:
    """Série brute intacte (entiers relatifs reçus) dans <out>_brut.csv, et série au schéma de `load_ohlc` (time,
    timestamp, open, high, low, close, volume en ticks). Chaque fichier a son .meta.json avec empreinte SHA-256 ; celui
    de la série de travail porte l'heure d'extraction et l'empreinte de la série brute."""
    out_csv = Path(out_csv)
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    brut_csv = out_csv.with_name(out_csv.stem + "_brut.csv")
    brut = df[["time", "low_rel", "d_open", "d_high", "d_close", "volume"]].copy()
    brut["time"] = brut["time"].dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    brut.to_csv(brut_csv, index=False, lineterminator="\n")
    sha_brut = _sha256(brut_csv)
    _meta(brut_csv, {**meta, "role": "série brute cTrader (prix relatifs entiers, × 100 000), intacte",
                     "n_rows": len(brut), "sha256": sha_brut})
    out = df[["time", "open", "high", "low", "close", "volume"]].copy()
    out.insert(1, "timestamp", ((out.time - pd.Timestamp("1970-01-01", tz="UTC")) // pd.Timedelta(seconds=1))
               .astype("int64"))
    out.to_csv(out_csv, index=False, lineterminator="\n")
    full = {**meta, "prix": "relatif / 100 000 arrondi aux digits du symbole ; volume en ticks",
            "timezone": "UTC (ouverture de la barre)", "n_rows": len(out),
            "first": str(out.time.iat[0]) if len(out) else None, "last": str(out.time.iat[-1]) if len(out) else None,
            "extracted_at_utc": pd.Timestamp.now(tz="UTC").isoformat(),
            "serie_brute": {"fichier": brut_csv.name, "sha256": sha_brut}, "sha256": _sha256(out_csv)}
    _meta(out_csv, full)
    return full
