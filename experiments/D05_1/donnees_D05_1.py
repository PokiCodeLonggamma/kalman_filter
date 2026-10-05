"""EXP-D05.1 — Données du compte d'essai FTMO par cTrader Open API : compte, symboles et fiches, barres de 30 min.

Décisions du porteur (2026-10-05) : candidats GLE, WTI, Brent, US100, US30, GER40 et GBPJPY ; fiches des six actifs
actuels (coûts réels et swaps) ; période de 2020-01 à aujourd'hui, 2026 incluse ; compte d'essai FTMO sur cTrader.
Aucun backtest. Chaque étape se lance sur GO du porteur.

Usage, depuis la racine du dépôt :
  python experiments/D05_1/donnees_D05_1.py --connexion        compte accordé au jeton (aucun secret affiché)
  python experiments/D05_1/donnees_D05_1.py --symboles         candidats trouvés et fiches → symboles_D05_1.json
  python experiments/D05_1/donnees_D05_1.py --telechargement   barres M30 des noms validés (NOMS) → data/raw/ctrader_ftmo_*
Options : --env demo|live (défaut : demo) ; --login <numéro du compte> s'il y en a plusieurs.

Secrets : CTRADER_CLIENT_ID et CTRADER_CLIENT_SECRET (posés par le porteur avec `setx`). Jeton : CTRADER_ACCESS_TOKEN
s'il existe, sinon connexion du porteur dans son navigateur, par http://localhost:47322/start (l'URL de retour
http://localhost:47322/akf-ctrader doit être déclarée dans l'application) ; portée « accounts », lecture seule.
Sorties : symboles_D05_1.json et telechargement_D05_1.json (versionnés, sans login ni jeton) ; séries
data/raw/ctrader_ftmo_<code>_30m.csv et _brut.csv (ignorées par git) avec leurs .meta.json (versionnés).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "src"))

import pandas as pd  # noqa: E402

import reserve  # noqa: E402
from marketdata import ctrader  # noqa: E402

RAW = ROOT / "data" / "raw"
DEBUT = pd.Timestamp("2020-01-01", tz="UTC")
MOTIF = "EXP-D05.1 : barres FTMO de 2020-01 à aujourd'hui, 2026 incluse (décision du porteur du 2026-10-05)"
CANDIDATS = ["GLE", "WTI", "BRENT", "US100", "US30", "GER40", "GBPJPY"]       # barres et fiches
ACTUELS = ["BTC", "ETH", "SOL", "AVAX", "XRP", "XAU"]                          # fiches seules (coûts, swaps)
#: motifs cherchés dans le nom ou la description des symboles (casse ignorée)
RECHERCHE = {"GLE": ["GLE", "Societe", "Société", "Generale", "Générale"], "WTI": ["USOIL", "WTI", "Crude"],
             "BRENT": ["UKOIL", "Brent"], "US100": ["US100", "NAS100", "USTEC", "Nasdaq"],
             "US30": ["US30", "DJ30", "Dow"], "GER40": ["GER40", "DE40", "DAX", "Germany"], "GBPJPY": ["GBPJPY"],
             "BTC": ["BTC", "Bitcoin"], "ETH": ["ETH", "Ethereum"], "SOL": ["SOLUSD", "Solana"],
             "AVAX": ["AVAX", "Avalanche"], "XRP": ["XRP", "Ripple"], "XAU": ["XAU", "Gold"]}
#: noms exacts des symboles, à remplir après --symboles, sur validation du porteur (leçon de D01.7 : nom exact)
NOMS: dict[str, str] = {}
FENETRE = pd.Timedelta(days=7)                  # 336 barres de 30 min au plus par requête
VIDES_MAX = 8                                   # huit semaines vides de suite : début de l'historique du serveur


def session(env: str, login):
    cid, csec = ctrader.secret(ctrader.CLIENT_ID_ENV), ctrader.secret(ctrader.CLIENT_SECRET_ENV)
    jeton = ctrader.access_token(cid, csec)
    client = ctrader.connecter(env)
    return client, ctrader.authenticate(client, cid, csec, jeton, login)


def _public(compte: dict) -> dict:
    """Compte sans son login (dépôt public)."""
    return {"courtier": compte.get("brokerTitleShort"), "live": compte.get("isLive"),
            "portee": compte.get("permissionScope")}


def connexion(env: str, login) -> None:
    client, compte = session(env, login)
    try:
        print(f"compte {compte['traderLogin']} : {'live' if compte['isLive'] else 'démo'}, "
              f"{compte['brokerTitleShort']}, portée {compte['permissionScope']}")
    finally:
        client.close()


def symboles(env: str, login) -> None:
    client, compte = session(env, login)
    try:
        liste = ctrader.symbols_list(client, compte["ctidTraderAccountId"])
        trouves = {}
        for code, motifs in RECHERCHE.items():
            vus = {}
            for m in motifs:
                for s in ctrader.search(liste, m):
                    vus.setdefault(s["symbolId"], {k: s.get(k) for k in ("symbolId", "symbolName", "description",
                                                                         "enabled")})
            trouves[code] = list(vus.values())
        ids = sorted({s["symbolId"] for v in trouves.values() for s in v})
        fiches = [f for i in range(0, len(ids), 50)
                  for f in ctrader.symbol_specs(client, compte["ctidTraderAccountId"], ids[i:i + 50])]
    finally:
        client.close()
    out = {"extrait_le_utc": pd.Timestamp.now(tz="UTC").isoformat(), "environnement": env, "compte": _public(compte),
           "n_symboles": len(liste), "candidats": trouves, "fiches": fiches}
    (HERE / "symboles_D05_1.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    for code, v in trouves.items():
        print(f"{code:6s} " + (" ; ".join(f"{s['symbolName']} ({s.get('description') or '—'})" for s in v) or "aucun"))


def telechargement(env: str, login) -> None:
    manquants = [c for c in CANDIDATS if c not in NOMS]
    if manquants:
        raise SystemExit(f"noms exacts à valider avant le téléchargement : {', '.join(manquants)} (NOMS)")
    client, compte = session(env, login)
    acct = compte["ctidTraderAccountId"]
    fin = pd.Timestamp.now(tz="UTC").floor("30min")                    # barre en cours exclue
    resumes = {}
    try:
        res = ctrader.resolve(ctrader.symbols_list(client, acct), {c: NOMS[c] for c in CANDIDATS})
        fiches = {f["symbolId"]: f for f in ctrader.symbol_specs(client, acct, [s["symbolId"] for s in res.values()])}
        with reserve.levee(MOTIF):
            for code, s in res.items():
                f = fiches[s["symbolId"]]
                df, r = ctrader.download_trendbars(client, acct, s["symbolId"], int(f["digits"]), DEBUT, fin,
                                                   window=FENETRE, max_empty=VIDES_MAX)
                if df is not None:
                    ctrader.write_series(df, RAW / f"ctrader_ftmo_{code.lower()}_30m.csv",
                                         {"source": "cTrader Open API (Spotware), compte d'essai FTMO",
                                          "environnement": env, "symbolName": s["symbolName"],
                                          "symbolId": s["symbolId"], "digits": int(f["digits"]), "periode": "M30",
                                          "demande": [str(DEBUT), str(fin)], "reserve_2026": reserve.motif(),
                                          "resume": r})
                resumes[code] = {"symbolName": s["symbolName"], **r}
                print(f"{code:6s} {r.get('barres', 0):>7} barres, {r.get('premiere')} → {r.get('derniere')}")
    finally:
        client.close()
        out = {"extrait_le_utc": pd.Timestamp.now(tz="UTC").isoformat(), "environnement": env,
               "compte": _public(compte), "periode": [str(DEBUT), str(fin)], "series": resumes}
        (HERE / "telechargement_D05_1.json").write_text(json.dumps(out, ensure_ascii=False, indent=1),
                                                        encoding="utf-8")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--connexion", action="store_true")
    g.add_argument("--symboles", action="store_true")
    g.add_argument("--telechargement", action="store_true")
    p.add_argument("--env", choices=sorted(ctrader.HOSTS), default="demo")
    p.add_argument("--login", default=None)
    a = p.parse_args()
    (connexion if a.connexion else symboles if a.symboles else telechargement)(a.env, a.login)


if __name__ == "__main__":
    main()
