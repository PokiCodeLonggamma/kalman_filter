"""EXP-D01.7 — test de Saxo OpenAPI (LIVE) comme source des barres de 30 min 2020-2025 : CFD US100, US2000, WTI, cuivre,
puis futures NQ, RTY, CL, HG (facultatif). Aucun backtest.

Usage, depuis la racine du dépôt : python experiments/D01_7/saxo_probe_D01_7.py [--port 47321]
1. Prérequis : application LIVE (flux PKCE) créée sur le portail développeur Saxo, URL de retour
   http://localhost/akf-callback ; sa clé dans la variable d'environnement SAXO_APP_KEY (setx), jamais dans le chat.
2. Le script ouvre un serveur local et affiche http://localhost:<port>/start : ouvrir cette adresse dans le navigateur,
   le porteur se connecte lui-même à Saxo. Le jeton reste en mémoire (os.environ du processus), jamais affiché ni écrit.
3. Sondage : droits de marché du compte (deux champs seulement, aucune donnée personnelle), recherche des instruments
   (/ref/v1/instruments), puis pour chaque CFD retenu : FirstSampleTime à Horizon = 30, modes From et UpTo, pagination
   (Count ≤ 1 200), champs de prix, séances, heures étendues, bloc de test écrit deux fois (empreinte comparée).
4. Futures (après les CFD) : recherche ContractFutures et une requête de graphique par actif ; arrêt au premier refus.
Sorties : experiments/D01_7/saxo_probe_D01_7.json ; blocs de test data/raw/saxo_<actif>_30m_test.csv (ignorés par git)
et leurs .meta.json. La réserve 2026 n'est jamais interrogée (marketdata.saxo.check_window).
"""
from __future__ import annotations

import json
import os
import re
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "src"))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from marketdata.saxo import (HOLDOUT, TOKEN_ENV, SaxoClient, app_key, browser_login, get_chart,  # noqa: E402
                             price_fields, refresh, samples_frame, search_instruments, write_block)

RAW = ROOT / "data" / "raw"
OUT = HERE / "saxo_probe_D01_7.json"
NY = "America/New_York"
H30 = 30
T_FROM = pd.Timestamp("2020-01-02T00:00:00Z")
T_UPTO_FIN = pd.Timestamp("2025-12-31T23:30:00Z")
T_UPTO_DEBUT = pd.Timestamp("2020-01-31T23:30:00Z")
CFD = ["CfdOnIndex", "CfdOnFutures"]
FUT = ["ContractFutures"]
CIBLES = {
    "US100": {"futur": "NQ", "mots": ["US Tech 100", "USNAS100", "Nasdaq 100", "NAS100", "US100"],
              "motif": r"nasdaq|tech 100|nas100|us ?100", "mots_futur": ["E-mini Nasdaq 100", "Nasdaq 100", "NQ"]},
    "US2000": {"futur": "RTY", "mots": ["US Small Cap 2000", "US2000", "Russell 2000", "Small Cap"],
               "motif": r"russell|small ?cap|us ?2000", "mots_futur": ["E-mini Russell 2000", "Russell 2000", "RTY"]},
    "USOIL": {"futur": "CL", "mots": ["US Crude", "WTI", "Crude Oil", "OIL"],
              "motif": r"wti|crude|us ?oil|light sweet", "mots_futur": ["WTI Crude Oil", "Crude Oil", "CL"]},
    "COPPER": {"futur": "HG", "mots": ["Copper", "COPPER"], "motif": r"copper|cuivre",
               "mots_futur": ["Copper", "HG"]},
}


def fit_count(t: pd.Timestamp, cap: int = 1200) -> int:
    """Nombre de barres d'une requête From qui reste avant le 2026-01-01 (réserve 2026)."""
    return max(0, min(cap, int((HOLDOUT - t) / pd.Timedelta(minutes=H30))))


class Session:
    """Client et jetons du processus : le jeton d'accès est rafraîchi avant son expiration (1 200 s)."""

    def __init__(self, tok: dict):
        self.client = SaxoClient()
        self._set(tok)

    def _set(self, tok: dict):
        os.environ[TOKEN_ENV] = tok["access_token"]
        self.refresh_token, self.verifier = tok.get("refresh_token"), tok.get("_verifier", self.__dict__.get("verifier"))
        self.expires = time.time() + float(tok.get("expires_in", 1200)) - 120

    def ensure(self):
        if time.time() > self.expires and self.refresh_token:
            tok = refresh(self.refresh_token, self.verifier)
            tok["_verifier"] = self.verifier
            self._set(tok)


def account_rights(s: Session) -> dict:
    """Deux champs seulement : conditions de données de marché via OpenAPI acceptées, types d'actifs autorisés."""
    out = {}
    st, me = s.client.get("/port/v1/users/me")
    out["users_me"] = st if st != 200 else {"MarketDataViaOpenApiTermsAccepted": me.get("MarketDataViaOpenApiTermsAccepted")}
    st, cl = s.client.get("/port/v1/clients/me")
    out["clients_me"] = st if st != 200 else {"LegalAssetTypes": cl.get("LegalAssetTypes")}
    return out


def gaps_profile(df: pd.DataFrame) -> dict:
    """Intervalles entre barres : classes, heures de New York des reprises, jours de la semaine."""
    if len(df) < 2:
        return {}
    t = df["time"]
    step = t.diff().dropna()
    gaps = step[step > pd.Timedelta(minutes=H30)]
    ny = t.iloc[gaps.index].dt.tz_convert(NY)
    return {"barres": len(df), "doublons": int(t.duplicated().sum()), "desordre": int((step <= pd.Timedelta(0)).sum()),
            "pas_30_min": float((step == pd.Timedelta(minutes=H30)).mean()),
            "interruptions": int(len(gaps)),
            "interruptions_duree_h": {k: float(v) for k, v in (gaps.dt.total_seconds() / 3600).describe()[["min", "50%", "max"]].items()} if len(gaps) else {},
            "reprises_heure_new_york": {f"{k:02d}:{m:02d}": int(v) for (k, m), v in
                                        pd.Series(list(zip(ny.dt.hour, ny.dt.minute))).value_counts().head(6).items()},
            "barres_par_jour_semaine": {int(k): int(v) for k, v in t.dt.dayofweek.value_counts().sort_index().items()}}


def ohlc_checks(df: pd.DataFrame) -> dict:
    out = {}
    for side, cols in (("bid", ["OpenBid", "HighBid", "LowBid", "CloseBid"]), ("ask", ["OpenAsk", "HighAsk", "LowAsk", "CloseAsk"]),
                       ("dernier", ["Open", "High", "Low", "Close"])):
        if all(c in df for c in cols) and df[cols].notna().all(axis=None):
            o, h, l, c = (df[x].to_numpy(dtype=float) for x in cols)
            out[side] = {"incoherences": int(((h < np.maximum(o, c)) | (l > np.minimum(o, c)) | (h < l)).sum()),
                         "prix_non_positifs": int((df[cols] <= 0).any(axis=1).sum())}
    if {"CloseAsk", "CloseBid"} <= set(df) and df[["CloseAsk", "CloseBid"]].notna().all(axis=None):
        mid = (df.CloseAsk + df.CloseBid) / 2
        spread = (df.CloseAsk - df.CloseBid) / mid * 1e4
        out["ecart_close_bps"] = {"P50": float(spread.median()), "P90": float(spread.quantile(.9)),
                                  "negatifs": int((spread < 0).sum())}
    if "Volume" in df:
        out["volume_nul"] = int((df.Volume.fillna(0) == 0).sum())
    return out


def probe_cfd(s: Session, key: str, cand: dict) -> dict:
    uic, at = cand["Identifier"], cand["AssetType"]
    rep = {"instrument": cand}
    s.ensure()
    st, body = get_chart(s.client, uic, at, H30, "UpTo", T_UPTO_DEBUT, 50)
    if st != 200:
        rep["erreur_premiere_requete"] = {"statut": st, "corps": body}
        return rep
    info = body.get("ChartInfo", {})
    rep["chart_info"] = info
    rep["display"] = body.get("DisplayAndFormat", {})
    first = pd.Timestamp(info["FirstSampleTime"]) if info.get("FirstSampleTime") else None
    rep["first_sample_time"] = str(first) if first is not None else None
    rep["couvre_2020_01_01"] = bool(first is not None and first <= pd.Timestamp("2020-01-01T00:00:00Z"))
    start = max(T_FROM, first.ceil("30min")) if first is not None else T_FROM
    pages = {}
    for name, mode, t in (("from_debut", "From", start), ("upto_fin_2025", "UpTo", T_UPTO_FIN),
                          ("upto_janvier_2020", "UpTo", T_UPTO_DEBUT)):
        n = fit_count(t) if mode == "From" else 1200
        if n == 0:
            continue
        s.ensure()
        st, b = get_chart(s.client, uic, at, H30, mode, t, n)
        pages[name] = samples_frame(b) if st == 200 else None
        rep[f"page_{name}"] = ({"statut": st, "barres": len(pages[name]),
                                "premiere": str(pages[name].time.iat[0]) if len(pages[name]) else None,
                                "derniere": str(pages[name].time.iat[-1]) if len(pages[name]) else None}
                               if st == 200 else {"statut": st, "corps": b})
    a = pages.get("from_debut")
    if a is not None and len(a):
        rep["champs_prix"] = price_fields(a)
        rep["structure"] = gaps_profile(a)
        rep["controles_ohlc"] = ohlc_checks(a)
        t_next = a.time.iat[-1] + pd.Timedelta(minutes=H30)
        nxt = None
        if fit_count(t_next):
            s.ensure()
            st, b = get_chart(s.client, uic, at, H30, "From", t_next, fit_count(t_next))
            nxt = samples_frame(b) if st == 200 else None
        if nxt is not None and len(nxt):
            rep["pagination_from"] = {"barres": len(nxt), "chevauchement": int(nxt.time.isin(a.time).sum()),
                                      "ecart_entre_pages_h": float((nxt.time.iat[0] - a.time.iat[-1]).total_seconds() / 3600)}
        u = pages.get("upto_janvier_2020")
        if u is not None and len(u):
            common = a.merge(u, on="time", suffixes=("_f", "_u"))
            cols = [c for c in a.columns if c != "time" and c in u.columns]
            same = all(np.allclose(common[f"{c}_f"].astype(float), common[f"{c}_u"].astype(float), equal_nan=True)
                       for c in cols if pd.api.types.is_numeric_dtype(a[c]))
            rep["coherence_from_upto"] = {"barres_communes": len(common), "valeurs_identiques": bool(same)}
        n0 = fit_count(start)
        s.ensure()
        st, b = get_chart(s.client, uic, at, H30, "From", start, n0, extended_hours=True)
        if st == 200:
            rep["heures_etendues"] = {"barres_avec": len(samples_frame(b)), "barres_sans": len(a)}
        meta = {"source": "saxo-openapi", "environnement": "LIVE", "uic": uic, "asset_type": at, "horizon_min": H30,
                "mode": "From", "time": str(start), "count": n0, "symbol": cand.get("Symbol"),
                "description": cand.get("Description"), "role": "bloc de test D01.7 (aucun backtest)"}
        csv = RAW / f"saxo_{key.lower()}_30m_test.csv"
        m1 = write_block(a, csv, meta)
        s.ensure()
        st, b = get_chart(s.client, uic, at, H30, "From", start, n0)
        again = samples_frame(b) if st == 200 else None
        m2 = write_block(again, csv.with_name(csv.stem + "_bis.csv"), meta) if again is not None else None
        rep["bloc_test"] = {"fichier": csv.name, "barres": m1["n_rows"], "sha256": m1["sha256"],
                            "reproductible": bool(m2 and m2["sha256"] == m1["sha256"])}
        if m2:
            csv.with_name(csv.stem + "_bis.csv").unlink()
            csv.with_name(csv.stem + "_bis.meta.json").unlink()
    st, sched = s.client.get(f"/ref/v1/instruments/tradingschedule/{uic}/{at}")
    if st == 200:
        sess = pd.DataFrame(sched.get("Sessions", []))
        if len(sess):
            sess["debut_ny"] = pd.to_datetime(sess.StartTime, utc=True).dt.tz_convert(NY).dt.strftime("%a %H:%M")
            sess["fin_ny"] = pd.to_datetime(sess.EndTime, utc=True).dt.tz_convert(NY).dt.strftime("%a %H:%M")
            rep["seances_annoncees"] = sess[["State", "debut_ny", "fin_ny"]].head(12).to_dict("records")
        rep["fuseau_bourse"] = sched.get("TimeZoneId") or sched.get("TimeZone")
    else:
        rep["seances_annoncees"] = {"statut": st}
    return rep


def choose(cands: list[dict], motif: str) -> list[dict]:
    """Candidats CFD dont la description ou le symbole correspond à l'actif : CfdOnIndex d'abord, puis CfdOnFutures."""
    rx = re.compile(motif, re.I)
    ok = [c for c in cands if "erreur" not in c and rx.search(f"{c.get('Description', '')} {c.get('Symbol', '')}")]
    return sorted(ok, key=lambda c: (c["AssetType"] != "CfdOnIndex", str(c.get("Symbol"))))


def main() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        pass
    port = int(sys.argv[sys.argv.index("--port") + 1]) if "--port" in sys.argv else 47321
    key = app_key()
    print("Serveur local prêt. Ouvrir dans le navigateur, puis se connecter à Saxo :", flush=True)
    tok = browser_login(key, port=port, on_ready=lambda url: print(f"  {url}", flush=True))
    s = Session(tok)
    del tok
    print("Connexion Saxo établie (jeton en mémoire seulement).", flush=True)
    rep = {"date_utc": pd.Timestamp.now(tz="UTC").isoformat(), "environnement": "LIVE",
           "reserve_2026": f"aucune requête au-delà de {HOLDOUT - pd.Timedelta(seconds=1)}", "droits": account_rights(s),
           "cfd": {}, "futures": {}}
    for k, c in CIBLES.items():
        seen, cands = set(), []
        for kw in c["mots"]:
            s.ensure()
            for d in search_instruments(s.client, kw, CFD):
                ident = (d.get("Identifier"), d.get("AssetType"))
                if "erreur" in d:
                    cands.append({**d, "mots_cles": kw})
                elif ident not in seen:
                    seen.add(ident)
                    cands.append({**d, "mots_cles": kw})
        pool = choose(cands, c["motif"])
        rep["cfd"][k] = {"candidats": cands, "retenus_pour_test": [], "tests": []}
        firsts = []
        for cand in pool[:12]:
            s.ensure()
            st, b = get_chart(s.client, cand["Identifier"], cand["AssetType"], H30, "UpTo", T_UPTO_FIN, 1)
            fst = b.get("ChartInfo", {}).get("FirstSampleTime") if st == 200 else None
            firsts.append({"Symbol": cand.get("Symbol"), "Identifier": cand["Identifier"], "AssetType": cand["AssetType"],
                           "Description": cand.get("Description"), "statut": st, "FirstSampleTime": fst,
                           "DelayedByMinutes": b.get("ChartInfo", {}).get("DelayedByMinutes") if st == 200 else None})
        rep["cfd"][k]["premier_echantillon_par_candidat"] = firsts
        ranked = sorted([f for f in firsts if f["FirstSampleTime"]], key=lambda f: (f["AssetType"] != "CfdOnIndex",
                                                                                   f["FirstSampleTime"]))
        for f in ranked[:2]:
            cand = next(x for x in pool if x["Identifier"] == f["Identifier"] and x["AssetType"] == f["AssetType"])
            rep["cfd"][k]["retenus_pour_test"].append(f)
            rep["cfd"][k]["tests"].append(probe_cfd(s, k if not rep["cfd"][k]["tests"] else f"{k}_2", cand))
        print(f"{k} : {len(cands)} candidats, {len(firsts)} interrogés, {len(rep['cfd'][k]['tests'])} testés en détail",
              flush=True)
    for k, c in CIBLES.items():                                        # futures, après les CFD
        seen, cands = set(), []
        for kw in c["mots_futur"]:
            s.ensure()
            for d in search_instruments(s.client, kw, FUT):
                ident = (d.get("Identifier"), d.get("AssetType"))
                if "erreur" in d or ident not in seen:
                    seen.add(ident)
                    cands.append({**d, "mots_cles": kw})
        pool = [d for d in cands if "erreur" not in d][:6]
        trials = []
        for cand in pool[:3]:
            s.ensure()
            st, b = get_chart(s.client, cand["Identifier"], cand["AssetType"], H30, "UpTo", T_UPTO_FIN, 5)
            trials.append({"Symbol": cand.get("Symbol"), "Identifier": cand["Identifier"],
                           "Description": cand.get("Description"), "statut": st,
                           "chart_info": b.get("ChartInfo") if st == 200 else None,
                           "champs_prix": price_fields(samples_frame(b)) if st == 200 and b.get("Data") else None,
                           "erreur": None if st == 200 else b})
            if st != 200:
                break
        rep["futures"][c["futur"]] = {"candidats": cands, "essais": trials}
        print(f"{c['futur']} : {len(cands)} contrats trouvés, {len(trials)} essais de graphique", flush=True)
    rep["appels_api"] = s.client.calls
    OUT.write_text(json.dumps(rep, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    os.environ.pop(TOKEN_ENV, None)
    print(f"Rapport écrit : {OUT} ({s.client.calls} appels)", flush=True)


if __name__ == "__main__":
    main()
