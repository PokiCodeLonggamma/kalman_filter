"""EXP-D01.7 (univers redéfini par le porteur le 2026-10-01) — disponibilité et couverture des barres de 30 min
2020-2025 chez Saxo OpenAPI (LIVE) : US100 CFD (déjà validé), GBPJPY, Germany 40, Hong Kong 50, EU Stocks 50, US 30 et
XAGUSD ; en option, cinq CFD sur ETF (TLT, USO ; SMH et URA demandés par le porteur ; GDX). Japan 225, demandé d'abord, n'existe pas en CfdOnIndex pour ce compte
(aucun candidat pour « Japan 225 », « JP225 », « Nikkei ») : remplacé par Hong Kong 50 sur décision du porteur.
Aucun backtest, RE-1 inchangée, aucune donnée de 2026 demandée.

Usage, depuis la racine du dépôt :
  python experiments/D01_7/saxo_univers_D01_7.py [--port 47321]   sondage + téléchargement (connexion Saxo du porteur)
  python experiments/D01_7/saxo_univers_D01_7.py --seulement ETF_URA   passe ciblée (rapport complété), heures étendues
  python experiments/D01_7/saxo_univers_D01_7.py --analyse         contrôles hors ligne des fichiers téléchargés
Connexion : comme saxo_probe_D01_7.py (clé dans SAXO_APP_KEY, jeton en mémoire du processus seulement).
Sorties : saxo_univers_D01_7.json (sondage, réécrit après chaque instrument), univers_D01_7.json (contrôles) ; séries
data/raw/saxo_<clé>_30m.csv et _brut.csv (ignorées par git) avec leurs .meta.json. Une série déjà téléchargée pour le
même UIC n'est pas retéléchargée.
Sélection (fixée avant le sondage) : indices → CfdOnIndex seulement (CFD sur l'indice au comptant, sans échéance ; un
CFD sur future, daté ou continu, n'est jamais retenu) ; GBPJPY et XAGUSD → FxSpot ; ETF → CfdOnEtf. Parmi les
candidats conformes au motif, celui dont l'historique de 30 min est le plus ancien. Un instrument absent ou postérieur au
2020-01-01 est signalé, jamais remplacé.
"""
from __future__ import annotations

import importlib.util
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

from marketdata.saxo import (BID_ASK, ENVIRONMENTS, HOLDOUT, TOKEN_ENV, app_key, browser_login,  # noqa: E402
                             download_upto, get_chart, search_instruments, write_series)


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


P = _load("saxo_probe_D01_7", HERE / "saxo_probe_D01_7.py")
RAW = ROOT / "data" / "raw"
OUT = HERE / "saxo_univers_D01_7.json"
OUT_ANALYSE = HERE / "univers_D01_7.json"
NY = "America/New_York"
START = pd.Timestamp("2020-01-01T00:00:00Z")
CIBLES = {
    "GER40": {"types": ["CfdOnIndex"], "mots": ["Germany 40", "GER40", "DAX"], "motif": r"germany 40|ger ?40|\bdax\b"},
    "HK50": {"types": ["CfdOnIndex"], "mots": ["Hong Kong 50", "HK50", "Hang Seng"], "motif": r"hong kong|hk ?50|hang seng"},
    "EU50": {"types": ["CfdOnIndex"], "mots": ["EU Stocks 50", "EU50", "Euro Stoxx 50"],
             "motif": r"eu stocks 50|eu ?50|stoxx 50"},
    "US30": {"types": ["CfdOnIndex"], "mots": ["US 30", "US30", "Wall Street", "Dow Jones"],
             "motif": r"us ?30|wall street|dow jones"},
    "XAGUSD": {"types": ["FxSpot"], "mots": ["XAGUSD", "Silver"], "motif": r"^xagusd$|silver/us dollar", "symbole": "XAGUSD"},
    "GBPJPY": {"types": ["FxSpot"], "mots": ["GBPJPY"], "motif": r"^gbpjpy$", "symbole": "GBPJPY"},
}
OPTION_ETF = {
    "ETF_TLT": {"symbole": "TLT", "types": ["CfdOnEtf"], "mots": ["TLT", "iShares 20+ Year Treasury"], "motif": r"^tlt(:|$)|20\+ year treasury",
                "interet": "taux longs américains : classe d'actifs absente de l'univers"},
    "ETF_USO": {"symbole": "USO", "types": ["CfdOnEtf"], "mots": ["USO", "United States Oil Fund"], "motif": r"^uso(:|$)|united states oil fund",
                "interet": "pétrole sans raccord de contrat dans le prix (le fonds roule lui-même)"},
    "ETF_SMH": {"symbole": "SMH", "types": ["CfdOnEtf"], "mots": ["SMH", "VanEck Semiconductor"], "motif": r"^smh(:|$)|semiconductor",
                "interet": "semi-conducteurs (demande du porteur) : forte volatilité, tendances longues"},
    "ETF_URA": {"symbole": "URA", "types": ["CfdOnEtf"], "mots": ["URA", "Global X Uranium"], "motif": r"^ura(:|$)|uranium",
                "interet": "uranium (demande du porteur) : thématique, volatil"},
    "ETF_GDX": {"symbole": "GDX", "types": ["CfdOnEtf"], "mots": ["GDX", "VanEck Gold Miners"], "motif": r"^gdx(:|$)|gold miners",
                "interet": "mines d'or (choix de l'agent) : très liquide, volatil, moteur distinct (or et actions)"},
}
US100 = {"fichier": "saxo_us100_cfd_30m.csv", "symbol": "USNAS100.I", "uic": 4912, "asset_type": "CfdOnIndex",
         "statut": "déjà téléchargé et validé (audit_saxo_D01_7.md), non retéléchargé"}
JP225 = {"premier_passage": "0 candidat CfdOnIndex pour « Japan 225 », « JP225 », « Nikkei »",
         "decision_porteur": "remplacé par Hong Kong 50 (2026-10-01)"}


def pick(cands: list[dict], c: dict) -> list[dict]:
    """Candidats du bon type et conformes au motif (description ou symbole)."""
    rx = re.compile(c["motif"], re.I)
    ok = [d for d in cands if "erreur" not in d and d.get("AssetType") in c["types"]
          and (rx.search(str(d.get("Symbol", ""))) or rx.search(str(d.get("Description", ""))))]
    if c.get("symbole"):                       # symbole exigé : aucun repli sur un autre candidat
        ok = [d for d in ok if str(d.get("Symbol", "")).upper().split(":")[0] == c["symbole"]]
    return ok


def sonde(s, key: str, c: dict) -> dict:
    seen, cands = set(), []
    for kw in c["mots"]:
        s.ensure()
        for d in search_instruments(s.client, kw, c["types"]):
            ident = (d.get("Identifier"), d.get("AssetType"))
            if "erreur" in d or ident not in seen:
                seen.add(ident)
                cands.append({**d, "mots_cles": kw})
    pool = pick(cands, c)[:8]
    firsts = []
    for d in pool:
        s.ensure()
        st, b = get_chart(s.client, d["Identifier"], d["AssetType"], 30, "UpTo", P.T_UPTO_FIN, 1)
        info = b.get("ChartInfo", {}) if st == 200 else {}
        firsts.append({"Symbol": d.get("Symbol"), "Identifier": d["Identifier"], "AssetType": d["AssetType"],
                       "Description": d.get("Description"), "TradableAs": d.get("TradableAs"), "statut": st,
                       "FirstSampleTime": info.get("FirstSampleTime"), "DelayedByMinutes": info.get("DelayedByMinutes"),
                       "ExchangeId": info.get("ExchangeId")})
    ranked = sorted([f for f in firsts if f["FirstSampleTime"]], key=lambda f: f["FirstSampleTime"])
    rep = {"candidats": cands, "conformes": firsts, "retenu": None, "test": None}
    if ranked:
        best = next(d for d in pool if d["Identifier"] == ranked[0]["Identifier"] and d["AssetType"] == ranked[0]["AssetType"])
        rep["retenu"] = ranked[0]
        rep["test"] = P.probe_cfd(s, key, best)
    return rep


def telecharge(s, key: str, rep: dict) -> dict:
    """Série complète 2020-2025 (pages UpTo) ; bid OHLC si la série a des cours acheteur/vendeur (CFD sur indice, FX),
    sinon dernier prix traité OHLC et volume (CFD sur ETF). Réutilise un fichier existant du même UIC."""
    t = rep.get("test") or {}
    if not t.get("couvre_2020_01_01"):
        return {"statut": "non téléchargé", "motif": "instrument absent ou historique de 30 min postérieur au 2020-01-01",
                "first_sample_time": t.get("first_sample_time")}
    inst = t["instrument"]
    csv = RAW / f"saxo_{key.lower()}_30m.csv"
    meta_path = csv.with_name(csv.stem + ".meta.json")
    if csv.exists() and meta_path.exists():
        old = json.loads(meta_path.read_text(encoding="utf-8"))
        if old.get("uic") == inst["Identifier"]:
            return {"statut": "déjà téléchargé (même UIC), réutilisé", "fichier": csv.name, "sha256": old.get("sha256"),
                    "n_rows": old.get("n_rows"), "extracted_at_utc": old.get("extracted_at_utc")}
    t0 = time.time()
    df, info = download_upto(s.client, inst["Identifier"], inst["AssetType"], START, before=s.ensure)
    if df is None:
        return {"statut": "erreur", **info}
    kind = "cfd" if all(c in df for c in BID_ASK[:4]) and df[BID_ASK[:4]].notna().all(axis=None) else "fut"
    meta = {"source": "saxo-openapi", "environnement": "LIVE", "actif": key, "uic": inst["Identifier"],
            "asset_type": inst["AssetType"], "symbol": inst.get("Symbol"), "description": inst.get("Description"),
            "exchange_id": (t.get("chart_info") or {}).get("ExchangeId"), "first_sample_time": t.get("first_sample_time"),
            "horizon_min": 30, "couverture_demandee": "2020-01-01 00:00 → 2025-12-31 23:30 UTC ; 2026 jamais demandé",
            "methode": "/chart/v3/charts, pages UpTo de 1 200 barres depuis le 2025-12-31 23:30 UTC vers le passé",
            "rolls": "sans objet : CFD sur l'indice au comptant, FX au comptant ou CFD sur ETF (aucune échéance) ; "
                     "contrôle dans l'audit"}
    m = write_series(df, kind, csv, meta)
    print(f"  {key} : {m['n_rows']} barres, {info['premiere']} → {info['derniere']}, {info['pages']} pages", flush=True)
    return {"statut": "téléchargé", **info, "fichier": csv.name, "prix": m["prix"], "sha256": m["sha256"],
            "n_rows": m["n_rows"], "duree_s": round(time.time() - t0)}


def check_extended(s, uic: int, asset_type: str) -> dict:
    """Heures étendues d'un CFD sur ETF : même requête From (2024-03-04, 60 barres) sans puis avec ExtendedHoursEnabled ;
    on compare l'étendue horaire (le nombre de barres, plafonné par Count, ne suffit pas)."""
    out = {}
    for name, ext in (("sans", None), ("avec", True)):
        s.ensure()
        st, b = get_chart(s.client, uic, asset_type, 30, "From", pd.Timestamp("2024-03-04T14:30:00Z"), 60, extended_hours=ext)
        df = P.samples_frame(b) if st == 200 else None
        if df is None or not len(df):
            out[name] = {"statut": st}
            continue
        ny = df.time.dt.tz_convert(NY)
        out[name] = {"statut": st, "barres": len(df), "premiere_ny": ny.iat[0].strftime("%Y-%m-%d %H:%M"),
                     "derniere_ny": ny.iat[-1].strftime("%Y-%m-%d %H:%M"),
                     "heures_ny": sorted(ny.dt.strftime("%H:%M").unique().tolist())}
    return out


def main() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        pass
    port = int(sys.argv[sys.argv.index("--port") + 1]) if "--port" in sys.argv else 47321
    key = app_key()
    print("Environnement Saxo : LIVE", flush=True)
    print("Serveur local prêt. Ouvrir dans le navigateur, puis se connecter à Saxo :", flush=True)
    tok = browser_login(key, port=port, on_ready=lambda url: print(f"  {url}", flush=True), auth=ENVIRONMENTS["live"][0])
    s = P.Session(tok, "live")
    del tok
    print("Connexion Saxo établie (jeton en mémoire seulement).", flush=True)
    only = sys.argv[sys.argv.index("--seulement") + 1].split(",") if "--seulement" in sys.argv else None
    if only and OUT.exists():                  # passe ciblée : le rapport existant est complété, pas remplacé
        rep = json.loads(OUT.read_text(encoding="utf-8"))
        rep.setdefault("passes_ciblees", []).append({"date_utc": pd.Timestamp.now(tz="UTC").isoformat(), "cles": only})
    else:
        rep = {"date_utc": pd.Timestamp.now(tz="UTC").isoformat(), "environnement": "LIVE",
               "reserve_2026": f"aucune requête au-delà de {HOLDOUT - pd.Timedelta(seconds=1)}",
               "droits": P.account_rights(s), "US100": US100, "JP225": JP225, "univers": {}, "option_etf": {},
               "telechargement": {}}

    def save():
        rep["appels_api"] = s.client.calls
        OUT.write_text(json.dumps(rep, ensure_ascii=False, indent=1, default=str), encoding="utf-8")

    for group, targets in (("univers", CIBLES), ("option_etf", OPTION_ETF)):
        for k, c in targets.items():
            if only and k not in only:
                continue
            try:
                rep[group][k] = sonde(s, k, c)
                r = rep[group][k]["retenu"] or {}
                print(f"{k} : {len(rep[group][k]['candidats'])} candidats, retenu {r.get('Symbol')} "
                      f"({r.get('AssetType')}, 30 min depuis {r.get('FirstSampleTime')})", flush=True)
                rep["telechargement"][k] = telecharge(s, k, rep[group][k])
            except Exception as e:  # noqa: BLE001 — un instrument en échec ne fait pas perdre le rapport
                rep["telechargement"][k] = {"statut": "erreur", "erreur": repr(e)}
                print(f"{k} : erreur {e!r}", flush=True)
            save()
    if only:
        smh = ((rep.get("option_etf", {}).get("ETF_SMH") or {}).get("retenu") or {})
        if smh:
            rep["heures_etendues_etf"] = {"ETF_SMH": check_extended(s, smh["Identifier"], smh["AssetType"])}
            save()
    os.environ.pop(TOKEN_ENV, None)
    print(f"Rapport écrit : {OUT} ({s.client.calls} appels)", flush=True)


# ── Contrôles hors ligne ────────────────────────────────────────────────────────
def nth_friday(y: int, m: int, nth: int = 3) -> pd.Timestamp:
    d = pd.Timestamp(year=y, month=m, day=1)
    return d + pd.Timedelta(days=(4 - d.weekday()) % 7 + 7 * (nth - 1))


QUARTERLY = [nth_friday(y, m).date() for y in range(2020, 2026) for m in (3, 6, 9, 12)]
HK_MONTHLY = [pd.bdate_range(f"{y}-{m:02d}-01", periods=23)[pd.bdate_range(f"{y}-{m:02d}-01", periods=23).month == m][-2].date()
              for y in range(2020, 2026) for m in range(1, 13)]   # avant-dernier jour ouvré (fêtes de HK non modélisées)
EXPIRIES = {"US100": ("3e vendredi trimestriel (CME)", QUARTERLY), "US30": ("3e vendredi trimestriel (CBOT)", QUARTERLY),
            "GER40": ("3e vendredi trimestriel (Eurex)", QUARTERLY), "EU50": ("3e vendredi trimestriel (Eurex)", QUARTERLY),
            "HK50": ("avant-dernier jour ouvré de chaque mois (HKEX, fêtes de HK non modélisées)", HK_MONTHLY)}


def analyse_serie(brut: pd.DataFrame, expiry: tuple | None) -> dict:
    """Couverture, intégrité, séances, écart bid/ask, plus grands sauts ; pour un indice, sauts en séance les jours
    d'échéance des futures (contrôle d'un éventuel raccord caché dans le CFD sur l'indice)."""
    t = brut.time
    ny = t.dt.tz_convert(NY)
    step = t.diff()
    cols = BID_ASK[:4] if "OpenBid" in brut else ["Open", "High", "Low", "Close"]
    o, h, l, c = (brut[x].to_numpy(float) for x in cols)
    with np.errstate(invalid="ignore", divide="ignore"):
        gap = pd.Series(np.log(o[1:] / c[:-1]) * 1e4, index=brut.index[1:]).reindex(brut.index)
    intra = step == pd.Timedelta(minutes=30)
    reprise = (step > pd.Timedelta(minutes=30)) & (step <= pd.Timedelta(hours=24))
    longue = step > pd.Timedelta(hours=24)
    first_ny, last_ny = ny.groupby(ny.dt.date).min(), ny.groupby(ny.dt.date).max()
    out = {
        "prix": "bid OHLC" if cols[0] == "OpenBid" else "dernier prix traité OHLC",
        "premiere": str(t.iat[0]), "derniere": str(t.iat[-1]), "barres": len(brut),
        "barres_par_annee": {int(k): int(v) for k, v in t.dt.year.value_counts().sort_index().items()},
        "doublons": int(t.duplicated().sum()), "desordre": int((step <= pd.Timedelta(0)).sum()),
        "incoherences_ohlc": int(((h < np.maximum(o, c)) | (l > np.minimum(o, c)) | (h < l)).sum()),
        "prix_non_positifs": int((brut[cols] <= 0).any(axis=1).sum()),
        "pas_30_min": round(float(intra.mean()), 4),
        "reprises_quotidiennes_ny": {k: int(v) for k, v in ny[reprise].dt.strftime("%H:%M").value_counts().head(4).items()},
        "duree_pause_quotidienne_min": {k: int(v) for k, v in (step[reprise].dt.total_seconds() / 60).astype(int)
                                        .value_counts().head(3).items()},
        "reprises_hebdo_ny": {k: int(v) for k, v in ny[longue].dt.strftime("%a %H:%M").value_counts().head(3).items()},
        "plus_long_trou_h": round(float(step.max().total_seconds() / 3600), 1),
        "premiere_barre_du_jour_ny_mode": str(first_ny.dt.strftime("%H:%M").mode().iat[0]),
        "derniere_barre_du_jour_ny_mode": str(last_ny.dt.strftime("%H:%M").mode().iat[0]),
        "saut_en_seance_bps": {"P50": round(float(gap[intra].abs().median()), 2),
                               "P99": round(float(gap[intra].abs().quantile(.99)), 1),
                               "max": round(float(gap[intra].abs().max()), 1)},
        "saut_a_la_reprise_bps": {"P50": round(float(gap[reprise | longue].abs().median()), 2),
                                  "P99": round(float(gap[reprise | longue].abs().quantile(.99)), 1)},
        "plus_grands_sauts": [{"time_ny": ny.iat[i].strftime("%Y-%m-%d %a %H:%M"), "bps": round(float(gap.iat[i]), 1),
                               "type": "séance" if intra.iat[i] else "reprise"}
                              for i in gap.abs().sort_values(ascending=False).index[:8]],
    }
    if cols[0] == "OpenBid":
        spread = (brut.CloseAsk - brut.CloseBid) / ((brut.CloseAsk + brut.CloseBid) / 2) * 1e4
        out["ecart_bid_ask_bps"] = {"P50": round(float(spread.median()), 2), "P90": round(float(spread.quantile(.9)), 2),
                                    "negatifs": int((spread < 0).sum())}
    if expiry:
        label, days = expiry
        day = ny.dt.date
        near = np.isin(day, days)
        thr = max(10 * float(gap[intra].abs().median()), 5.0)
        big = intra & (gap.abs() > thr)
        n_ex = int(np.isin(np.array(days), day.unique()).sum())
        out["controle_raccord"] = {
            "echeances": label, "regle": f"sauts en séance > {thr:.1f} bps (10 × la médiane, au moins 5)",
            "jours_echeance_couverts": n_ex, "sauts_jours_echeance": int((big & near).sum()),
            "sauts_autres_jours": int((big & ~near).sum()),
            "sauts_par_jour": {"echeance": round(float((big & near).sum()) / max(n_ex, 1), 3),
                               "autres": round(float((big & ~near).sum()) / (day.nunique() - n_ex), 3)},
            "max_saut_jour_echeance_bps": round(float(gap[intra & near].abs().max()), 1)}
    return out


def compare_histdata(saxo: pd.DataFrame) -> dict:
    """GBPJPY : Saxo contre HistData (deux séries bid) sur les barres communes ; barres HistData manquantes que Saxo
    couvre (trous de 2023)."""
    path = RAW / "histdata_gbpjpy_30m.csv"
    if not path.exists():
        return {"statut": "série HistData absente"}
    hd = pd.read_csv(path, parse_dates=["time"])
    m = saxo[["time", "close"]].merge(hd[["time", "close"]], on="time", suffixes=("_saxo", "_hd"))
    r_s, r_h = np.log(m.close_saxo).diff(), np.log(m.close_hd).diff()
    ok = m.time.diff() == pd.Timedelta(minutes=30)
    yr = lambda d, y: int((d.time.dt.year == y).sum())  # noqa: E731
    lvl = np.log(m.close_saxo / m.close_hd) * 1e4
    return {"barres_communes": len(m), "corr_rendements_30min": round(float(r_s[ok].corr(r_h[ok])), 4),
            "ecart_niveau_close_bps": {"P50": round(float(lvl.median()), 2), "P90_abs": round(float(lvl.abs().quantile(.9)), 2)},
            "barres_par_annee": {y: {"saxo": yr(saxo, y), "histdata": yr(hd, y)} for y in range(2020, 2026)},
            "barres_saxo_absentes_de_histdata": int((~saxo.time.isin(hd.time)).sum()),
            "barres_histdata_absentes_de_saxo": int((~hd.time.isin(saxo.time)).sum())}


def analyse() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        pass
    out = {}
    files = {"US100": "saxo_us100_cfd_30m", **{k: f"saxo_{k.lower()}_30m" for k in (*CIBLES, *OPTION_ETF, "ETF_NLR")}}
    for k, stem in files.items():
        p = RAW / f"{stem}_brut.csv"
        if not p.exists() or not (RAW / f"{stem}.meta.json").exists():
            out[k] = {"statut": "non téléchargé"}
            continue
        brut = pd.read_csv(p, parse_dates=["time"])
        meta = json.loads((RAW / f"{stem}.meta.json").read_text(encoding="utf-8"))
        out[k] = {"symbol": meta.get("symbol"), "uic": meta.get("uic"), "asset_type": meta.get("asset_type"),
                  "description": meta.get("description"), "first_sample_time": meta.get("first_sample_time"),
                  "sha256": meta.get("sha256"), **analyse_serie(brut, EXPIRIES.get(k))}
        if k == "GBPJPY":
            out[k]["comparaison_histdata"] = compare_histdata(pd.read_csv(RAW / f"{stem}.csv", parse_dates=["time"]))
        print(k, {x: out[k][x] for x in ("barres", "premiere", "derniere", "pas_30_min", "prix_non_positifs")}, flush=True)
    OUT_ANALYSE.write_text(json.dumps(out, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    print(f"Contrôles écrits : {OUT_ANALYSE}")


if __name__ == "__main__":
    analyse() if "--analyse" in sys.argv else main()
