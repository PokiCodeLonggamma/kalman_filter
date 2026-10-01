"""Saxo OpenAPI, environnement LIVE : authentification OAuth 2 PKCE, recherche d'instruments, barres de graphique
(EXP-D01.7, test de source de données ; aucun backtest).

Documentation officielle suivie (developer.saxo) :
- environnements : passerelle REST https://gateway.saxobank.com/openapi, authentification https://live.logonvalidation.net ;
  les jetons d'un jour du portail ne valent que pour la simulation ; en LIVE, un jeton s'obtient par un flux OAuth ;
- « Authorization Code Grant (PKCE) » : GET /authorize (response_type=code, client_id, state, redirect_uri,
  code_challenge, code_challenge_method=S256) ; POST /token (application/x-www-form-urlencoded : grant_type=
  authorization_code, client_id, code, redirect_uri, code_verifier) ; rafraîchissement (grant_type=refresh_token,
  refresh_token, code_verifier) ; jeton d'accès 1 200 s, jeton de rafraîchissement 2 400 s ; l'URL de retour est
  enregistrée sans port, tout port est accepté si le domaine et le chemin correspondent ;
- GET /ref/v1/instruments (Keywords, AssetTypes, IncludeNonTradable, $top, $skip) : Symbol, Identifier (UIC),
  AssetType, Description, ExchangeId, CurrencyCode, TradableAs ;
- GET /chart/v3/charts (AssetType, Uic, Horizon en minutes, Mode UpTo/From, Time, Count ≤ 1 200, FieldGroups,
  ExtendedHoursEnabled) : ChartInfo (DelayedByMinutes, ExchangeId, FirstSampleTime, Horizon) ; Data (Time ; Open, High,
  Low, Close : dernier prix traité ; OpenBid … CloseBid et OpenAsk … CloseAsk ; Volume ; Interest).

Secrets :
- la clé d'application (client_id) est lue dans SAXO_APP_KEY : environnement du processus, sinon variables
  d'environnement de l'utilisateur Windows (HKCU\\Environment, écrites par `setx`) ; jamais affichée ni écrite ;
- le jeton d'accès vit uniquement dans os.environ["SAXO_ACCESS_TOKEN"] du processus : jamais affiché, jamais écrit
  sur disque, perdu à la fin du processus.

Réserve 2026 : aucune requête de graphique ne peut viser une barre postérieure au 2025-12-31 23:59:59 UTC
(`check_window` avant chaque appel) ; toute barre reçue au-delà serait une erreur.
"""
from __future__ import annotations

import base64
import hashlib
import http.server
import json
import os
import secrets
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Callable

import pandas as pd

GATEWAY = "https://gateway.saxobank.com/openapi"
AUTH = "https://live.logonvalidation.net"
HOLDOUT = pd.Timestamp("2026-01-01", tz="UTC")
MAX_COUNT = 1200
APP_KEY_ENV, TOKEN_ENV = "SAXO_APP_KEY", "SAXO_ACCESS_TOKEN"
CALLBACK_PATH = "/akf-callback"
BID_ASK = ["OpenBid", "HighBid", "LowBid", "CloseBid", "OpenAsk", "HighAsk", "LowAsk", "CloseAsk"]
LAST = ["Open", "High", "Low", "Close", "Volume"]


# ── Secrets ─────────────────────────────────────────────────────────────────────
def app_key(env=None, registry: Callable[[str], str | None] | None = None) -> str:
    """Clé d'application : environnement du processus, sinon variables d'environnement de l'utilisateur Windows."""
    env = os.environ if env is None else env
    if env.get(APP_KEY_ENV):
        return env[APP_KEY_ENV]
    value = (registry or _user_env_registry)(APP_KEY_ENV)
    if not value:
        raise SystemExit(f"variable d'environnement {APP_KEY_ENV} absente (clé de l'application Saxo LIVE)")
    return value


def _user_env_registry(name: str) -> str | None:
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as k:
            return winreg.QueryValueEx(k, name)[0]
    except (ImportError, OSError):
        return None


# ── OAuth 2 PKCE ────────────────────────────────────────────────────────────────
def pkce_pair() -> tuple[str, str]:
    """(code_verifier, code_challenge S256) : 64 caractères non réservés, BASE64URL(SHA256(verifier)) sans remplissage."""
    verifier = secrets.token_urlsafe(48)[:64]
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode("ascii")).digest()).rstrip(b"=").decode()
    return verifier, challenge


def authorize_url(client_id: str, redirect_uri: str, state: str, challenge: str, auth: str = AUTH) -> str:
    q = {"response_type": "code", "client_id": client_id, "state": state, "redirect_uri": redirect_uri,
         "code_challenge": challenge, "code_challenge_method": "S256"}
    return f"{auth}/authorize?{urllib.parse.urlencode(q)}"


def _post_form(url: str, form: dict) -> dict:
    req = urllib.request.Request(url, data=urllib.parse.urlencode(form).encode(), method="POST",
                                 headers={"Content-Type": "application/x-www-form-urlencoded"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        raise SystemExit(f"échange OAuth refusé (HTTP {e.code}) : {e.read()[:300]!r}") from None


def exchange_code(client_id: str, code: str, redirect_uri: str, verifier: str, post=_post_form,
                  auth: str = AUTH) -> dict:
    return post(f"{auth}/token", {"grant_type": "authorization_code", "client_id": client_id, "code": code,
                                  "redirect_uri": redirect_uri, "code_verifier": verifier})


def refresh(refresh_token: str, verifier: str, post=_post_form, auth: str = AUTH) -> dict:
    return post(f"{auth}/token", {"grant_type": "refresh_token", "refresh_token": refresh_token,
                                  "code_verifier": verifier})


def browser_login(client_id: str, port: int = 47321, timeout_s: int = 900, on_ready: Callable[[str], None] = print,
                  auth: str = AUTH) -> dict:
    """Flux PKCE avec serveur de retour local (127.0.0.1) : /start redirige vers la page de connexion Saxo (l'URL, qui
    porte la clé d'application, n'est jamais affichée) ; /akf-callback reçoit le code, vérifie `state` et l'échange.
    Le porteur se connecte lui-même dans son navigateur. Renvoie la réponse du point /token (jetons en mémoire)."""
    verifier, challenge = pkce_pair()
    state = secrets.token_urlsafe(24)
    redirect_uri = f"http://localhost:{port}{CALLBACK_PATH}"
    target = authorize_url(client_id, redirect_uri, state, challenge, auth)
    box: dict = {}
    done = threading.Event()

    class Handler(http.server.BaseHTTPRequestHandler):
        def log_message(self, *a):                                     # pas de journal (l'URL porte le code)
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
            if q.get("state", [""])[0] != state:
                box["error"] = "state différent : réponse rejetée"
            elif "code" not in q:
                box["error"] = f"pas de code : {q.get('error', ['?'])[0]}"
            else:
                box["code"] = q["code"][0]
            self._send(200, "<p>Connexion reçue. Vous pouvez fermer cet onglet ; le test Saxo continue.</p>"
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
    tok = exchange_code(client_id, box["code"], redirect_uri, verifier, auth=auth)
    tok["_verifier"] = verifier
    return tok


# ── Appels OpenAPI ──────────────────────────────────────────────────────────────
class SaxoClient:
    """GET authentifié sur la passerelle : jeton lu dans os.environ[SAXO_ACCESS_TOKEN] à chaque appel ; nouvel essai
    après 429 (en-tête Retry-After) ou 5xx ; une erreur renvoie (statut, corps) sans jamais exposer le jeton."""

    def __init__(self, gateway: str = GATEWAY, opener: Callable | None = None, pause: float = 0.25):
        self.gateway, self.opener, self.pause = gateway, opener or urllib.request.urlopen, pause
        self.calls = 0

    def get(self, path: str, params: dict | None = None, tries: int = 5) -> tuple[int, dict | str]:
        url = f"{self.gateway}{path}" + (f"?{urllib.parse.urlencode(params, doseq=True)}" if params else "")
        for k in range(tries):
            req = urllib.request.Request(url, headers={"Authorization": f"Bearer {os.environ[TOKEN_ENV]}",
                                                       "Accept": "application/json"})
            try:
                with self.opener(req, timeout=60) as r:
                    self.calls += 1
                    time.sleep(self.pause)
                    body = r.read()
                    return r.status, (json.loads(body) if body else {})
            except urllib.error.HTTPError as e:
                self.calls += 1
                body = e.read()[:2000].decode("utf-8", "replace")
                if e.code == 429 or e.code >= 500:
                    time.sleep(float(e.headers.get("Retry-After") or 2 * (k + 1)))
                    continue
                return e.code, body
        return 429, "trop de requêtes"


def search_instruments(client: SaxoClient, keywords: str, asset_types: list[str], top: int = 100) -> list[dict]:
    status, body = client.get("/ref/v1/instruments", {"Keywords": keywords, "AssetTypes": ",".join(asset_types),
                                                      "IncludeNonTradable": "true", "$top": top})
    if status != 200:
        return [{"erreur": status, "corps": body}]
    keep = ("Symbol", "Identifier", "AssetType", "Description", "ExchangeId", "CurrencyCode", "TradableAs", "GroupId",
            "SummaryType")
    return [{k: d.get(k) for k in keep} for d in body.get("Data", [])]


def check_window(time_utc: pd.Timestamp, mode: str, count: int, horizon_min: int) -> None:
    """Réserve 2026 : la dernière barre visée par la requête doit être antérieure au 2026-01-01."""
    if count < 1 or count > MAX_COUNT or mode not in ("UpTo", "From"):
        raise ValueError("Count dans [1, 1 200] et Mode UpTo ou From exigés")
    last = time_utc if mode == "UpTo" else time_utc + pd.Timedelta(minutes=horizon_min) * (count - 1)
    if last >= HOLDOUT:
        raise ValueError(f"réserve 2026 : la requête atteindrait {last}")


def get_chart(client: SaxoClient, uic: int, asset_type: str, horizon: int, mode: str, time_utc: pd.Timestamp,
              count: int = MAX_COUNT, extended_hours: bool | None = None) -> tuple[int, dict | str]:
    """Une page de /chart/v3/charts (ChartInfo, Data, DisplayAndFormat). En mode From, la fenêtre visée est bornée
    en nombre de barres : count × horizon après `time_utc`, contrôlée avant l'appel."""
    time_utc = pd.Timestamp(time_utc).tz_convert("UTC")
    check_window(time_utc, mode, count, horizon)
    params = {"AssetType": asset_type, "Uic": int(uic), "Horizon": int(horizon), "Mode": mode,
              "Time": time_utc.strftime("%Y-%m-%dT%H:%M:%SZ"), "Count": int(count),
              "FieldGroups": "ChartInfo,Data,DisplayAndFormat"}
    if extended_hours is not None:
        params["ExtendedHoursEnabled"] = str(bool(extended_hours)).lower()
    status, body = client.get("/chart/v3/charts", params)
    if status == 200 and isinstance(body, dict):
        bad = [s["Time"] for s in body.get("Data", []) if pd.Timestamp(s["Time"]) >= HOLDOUT]
        if bad:
            raise RuntimeError(f"réserve 2026 : {len(bad)} barres reçues au-delà de 2025 (requête {params['Time']})")
    return status, body


def samples_frame(body: dict) -> pd.DataFrame:
    """Échantillons en DataFrame trié (time UTC, champs reçus tels quels)."""
    df = pd.DataFrame(body.get("Data", []))
    if df.empty:
        return df
    df.insert(0, "time", pd.to_datetime(df.pop("Time"), utc=True))
    return df.sort_values("time").reset_index(drop=True)


def price_fields(df: pd.DataFrame) -> dict:
    """Champs de prix effectivement renseignés : bid/ask, dernier prix, volume."""
    has = lambda cols: [c for c in cols if c in df and df[c].notna().any()]  # noqa: E731
    return {"bid_ask": has(BID_ASK), "dernier": has(LAST[:4]), "volume": has(["Volume"]),
            "autres": [c for c in df.columns if c not in ["time"] + BID_ASK + LAST]}


def write_block(df: pd.DataFrame, out_csv: Path, meta: dict) -> dict:
    """CSV de test reproductible (colonnes reçues, time en UTC ISO) et son .meta.json avec empreinte SHA-256."""
    out_csv = Path(out_csv)
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    out = df.copy()
    out["time"] = out["time"].dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    out.to_csv(out_csv, index=False, lineterminator="\n")
    meta = {**meta, "n_rows": len(out), "first": out["time"].iat[0] if len(out) else None,
            "last": out["time"].iat[-1] if len(out) else None,
            "sha256": hashlib.sha256(out_csv.read_bytes()).hexdigest()}
    out_csv.with_name(out_csv.stem + ".meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1),
                                                             encoding="utf-8")
    return meta
