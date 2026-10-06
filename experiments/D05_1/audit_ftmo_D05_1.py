"""EXP-D05.1 — vérification des données FTMO exportées par le cBot AkfExportFtmo (récupération sans Open API).

Décision du porteur du 2026-10-06 : finir la récupération et la vérification des données, puis passation ; l'objectif
stratégique (Baseline cTrader, profil RE-1 TradFi, inclusion) se fera dans une nouvelle session. Aucun backtest ici.

Ce que l'audit vérifie, par symbole (fixé avant lecture) :
- bougies M30 : horodatages (ordre, doublons, alignement sur :00 et :30), cohérence OHLC, barres plates, volume nul,
  première et dernière barre, trous de cotation par an et motifs récurrents (jour, heure UTC, durée) ;
- ticks : période couverte, écart à l'ouverture des barres (médiane, moyenne, P90, max ; semaine et week-end) ;
- fiches (version 2 du cBot) : description, type et valeur des swaps (bps par nuit au dernier prix), jour triple,
  commission (bps par côté), paliers de levier, séances ;
- recoupement avec les séries déjà dans le dépôt, sur les barres communes : corrélation des rendements de 30 min (barres
  consécutives des deux côtés), décalage qui maximise la corrélation (−2 à +2 barres : 0 attendu si les deux sont en
  UTC à l'ouverture), écart de niveau (médiane, P1, P99, en bps), couverture mutuelle.
Limites : les séries de référence ont leurs propres conventions (Bitstamp et Coinbase : prix de transaction ; Saxo et
HistData : bid) ; le WTI de Saxo est un CFD continu raccordé à l'échéance (rendements des jours de roulement faussés) ;
aucune référence pour le Brent et SAN.

Usage : python experiments/D05_1/audit_ftmo_D05_1.py
Sorties : audit_ftmo_D05_1.json et audit_ftmo_D05_1.md.
"""
from __future__ import annotations

import json
import sys
import warnings
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "src"))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from marketdata.ftmo import ecarts_barres, lire_bougies, lire_fiches, lire_ticks  # noqa: E402
from propfirm.frictions import commission_bps, swap_bps  # noqa: E402
from reserve import levee  # noqa: E402
from utils.data_loader import load_ohlc  # noqa: E402

RAW = ROOT / "data" / "raw"
FTMO = RAW / "ftmo"
EXPORTS = ("export_2026-10-06", "export_2026-10-06_v2")
MOTIF = "EXP-D05.1, vérification des données FTMO (porteur, 2026-10-06)"
NOMS = {"US100": "US100.cash", "US30": "US30.cash", "GER40": "GER40.cash", "GBPJPY": "GBPJPY", "WTI": "USOIL.cash",
        "BRENT": "UKOIL.cash", "XAU": "XAUUSD", "SAN": "SAN", "BTC": "BTCUSD", "ETH": "ETHUSD", "SOL": "SOLUSD",
        "AVAX": "AVAUSD", "XRP": "XRPUSD"}
REFS = {"US100": ("Saxo CFD US Tech 100 (bid)", "saxo_us100_cfd_30m.csv"),
        "US30": ("Saxo CFD US 30 (bid)", "saxo_us30_30m.csv"),
        "GER40": ("Saxo CFD Germany 40 (bid)", "saxo_ger40_30m.csv"),
        "GBPJPY": ("Saxo GBPJPY (bid)", "saxo_gbpjpy_30m.csv"),
        "WTI": ("Saxo CFD OILUScont (bid, raccordé à l'échéance)", "saxo_usoil_cfd_30m.csv"),
        "XAU": ("HistData XAUUSD (bid)", "histdata_xauusd_30m_2009_2026.csv"),
        "BTC": ("Bitstamp BTC/USD", "bitstamp_btcusd_30m_2013_2026.csv"),
        "ETH": ("Bitstamp ETH/USD", "bitstamp_ethusd_30m_2017_2026.csv"),
        "XRP": ("Bitstamp XRP/USD", "bitstamp_xrpusd_30m_2016_2026.csv"),
        "SOL": ("Coinbase SOL/USD", "coinbase_solusd_30m_2021_2026.csv"),
        "AVAX": ("Coinbase AVAX/USD", "coinbase_avaxusd_30m_2021_2026.csv")}
HALF = pd.Timedelta(minutes=30)
TOUT = pd.Timestamp("2100-01-01", tz="UTC")


def propre(nom: str) -> str:
    return "".join(c.lower() if c.isalnum() else "_" for c in nom)


def fichier(nom: str) -> Path | None:
    for exp in reversed(EXPORTS):
        p = FTMO / exp / nom
        if p.exists():
            return p
    return None


def audit_bougies(b: pd.DataFrame) -> dict:
    t = b.time
    d = t.diff()
    trous = d > HALF
    x = pd.DataFrame({"debut": t.shift(1)[trous] + HALF, "h": d[trous] / pd.Timedelta(hours=1) - 0.5})
    an = x.debut.dt.year
    motif = (x.debut.dt.day_name().str[:3] + " " + x.debut.dt.strftime("%H:%M"))
    top = (x.assign(m=motif).groupby("m").h.agg(["size", "median"]).sort_values("size", ascending=False).head(3))
    return {"barres": len(b), "premiere": str(t.iat[0]), "derniere": str(t.iat[-1]),
            "hors_grille_30min": int(((t.dt.minute % 30) != 0).sum() + (t.dt.second != 0).sum()),
            "plates": int((b.high == b.low).sum()), "volume_nul": int((b.volume <= 0).sum()),
            "trous": int(trous.sum()), "trous_par_an": {int(k): int(v) for k, v in an.value_counts().sort_index().items()},
            "heures_manquantes_par_an": {int(k): round(float(v), 1) for k, v in x.h.groupby(an).sum().items()},
            "plus_long_trou_h": round(float(x.h.max()), 1) if len(x) else 0.0,
            "plus_long_trou_debut": str(x.debut.iat[int(np.argmax(x.h.to_numpy()))]) if len(x) else None,
            "motifs_recurrents": [f"{m} UTC : {int(r['size'])} fois, médiane {r['median']:.1f} h"
                                  for m, r in top.iterrows()]}


def audit_ticks(t: pd.DataFrame, b: pd.DataFrame) -> dict:
    o = pd.DatetimeIndex(b.time[(b.time >= t.time.iat[0]) & (b.time <= t.time.iat[-1])])
    e = ecarts_barres(t, o).dropna()
    we = e.index.dayofweek >= 5
    return {"ticks": len(t), "debut": str(t.time.iat[0]), "fin": str(t.time.iat[-1]), "barres_mesurees": len(e),
            "ecart_median_bps": float(e.median()), "ecart_moyen_bps": float(e.mean()),
            "ecart_p90_bps": float(e.quantile(0.9)), "ecart_max_bps": float(e.max()),
            "ecart_median_semaine_bps": float(e[~we].median()),
            "ecart_median_weekend_bps": float(e[we].median()) if we.any() else None}


def audit_fiche(f: pd.Series, prix: float) -> dict:
    out = {"description": f.description, "digits": int(f.digits), "lot_size": float(f.lot_size)}
    if "swap_type" not in f.index:
        return out | {"version_fiche": 1, "swap_long": float(f.swap_long), "swap_short": float(f.swap_short)}
    sl = float(swap_bps(f.swap_type, f.swap_long, prix, float(f.pip_size), int(f.digits)))
    ss = float(swap_bps(f.swap_type, f.swap_short, prix, float(f.pip_size), int(f.digits)))
    com = float(commission_bps(f.commission_type, float(f.commission), prix, float(f.lot_size)))
    return out | {"version_fiche": 2, "base": f.base, "cotation": f.cotation, "swap_type": f.swap_type,
                  "swap_long": float(f.swap_long), "swap_short": float(f.swap_short),
                  "swap_cout_long_bps_nuit": sl, "swap_cout_short_bps_nuit": ss,
                  "swap_triple": f.swap_triple if isinstance(f.swap_triple, str) else None,
                  "commission_type": f.commission_type, "commission": float(f.commission),
                  "commission_bps_cote_usd": com, "levier_paliers": f.levier_paliers, "seances": f.seances}


def recouper(b: pd.DataFrame, ref_csv: Path) -> dict:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        r = load_ohlc(ref_csv)
    decale = bool(((r.time.dt.minute % 30) != 0).any())
    if decale:                                   # Saxo OILUScont : barres à :01 et :31, ramenées à :00 et :30
        r = r.assign(time=r.time.dt.floor("30min")).drop_duplicates("time")
    r = r[(r.time >= b.time.iat[0]) & (r.time <= b.time.iat[-1])]
    x = pd.merge(b[["time", "close"]], r[["time", "close"]], on="time", suffixes=("_f", "_r"))
    if len(x) < 100:
        return {"barres_communes": len(x)}
    niveau = (x.close_f / x.close_r - 1.0) * 1e4

    def rendements(s: pd.DataFrame, col: str) -> pd.Series:
        ok = s.time.diff() == HALF
        return np.log(s[col]).diff().where(ok)

    rf = rendements(b, "close").set_axis(b.time)
    rr = rendements(r, "close").set_axis(r.time)
    j = pd.concat([rf, rr], axis=1, keys=["f", "r"], join="inner").dropna()
    cor = {k: float(j.f.corr(j.r.shift(k))) for k in range(-2, 3)}
    return {"barres_communes": len(x), "horodatage_ref_arrondi": decale, "debut": str(x.time.iat[0]),
            "fin": str(x.time.iat[-1]),
            "couverture_ftmo_dans_ref": float(len(x) / len(b[(b.time >= r.time.iat[0]) & (b.time <= r.time.iat[-1])])),
            "couverture_ref_dans_ftmo": float(len(x) / len(r)) if len(r) else None,
            "rendements_communs": len(j), "correlation_30min": cor[0],
            "decalage_max_correlation": int(max(cor, key=cor.get)),
            "correlations_decalees": {str(k): round(v, 4) for k, v in cor.items()},
            "niveau_median_bps": float(niveau.median()), "niveau_p1_bps": float(niveau.quantile(0.01)),
            "niveau_p99_bps": float(niveau.quantile(0.99))}


def main() -> None:
    fp = fichier("ftmo_symboles_fiches.csv")
    fiches = lire_fiches(fp)
    out = {"date": pd.Timestamp.now(tz="UTC").strftime("%Y-%m-%d %H:%M UTC"), "motif": MOTIF,
           "fichier_fiches": f"{fp.parent.name}/{fp.name}", "symboles": {}}
    liste = pd.read_csv(fichier("ftmo_symboles_liste.csv"))
    out["symboles_du_compte"] = int((~liste.nom.str.contains("_removed|Demo Import", regex=True)).sum())
    with levee(MOTIF):
        for cle, nom in NOMS.items():
            res = {"symbole": nom}
            pb = fichier(f"ftmo_{propre(nom)}_m30.csv")
            if pb is None:
                res["absent"] = "bougies non exportées"
                out["symboles"][cle] = res
                print(f"{cle} : absent", flush=True)
                continue
            b = lire_bougies(pb, fin=TOUT)
            res["export"] = pb.parent.name
            res["bougies"] = audit_bougies(b)
            pt = fichier(f"ftmo_{propre(nom)}_ticks.csv")
            if pt is not None:
                res["ticks"] = audit_ticks(lire_ticks(pt), b)
            if nom in fiches.index:
                res["fiche"] = audit_fiche(fiches.loc[nom], float(b.close.iat[-1]))
            if cle in REFS:
                res["recoupement"] = {"reference": REFS[cle][0], **recouper(b, RAW / REFS[cle][1])}
            out["symboles"][cle] = res
            rc = res.get("recoupement", {})
            print(f"{cle} : {res['bougies']['barres']} barres ; corr {rc.get('correlation_30min', float('nan')):.4f} "
                  f"décalage {rc.get('decalage_max_correlation')} ; niveau {rc.get('niveau_median_bps', float('nan')):+.1f}"
                  " bps", flush=True)
    (HERE / "audit_ftmo_D05_1.json").write_text(json.dumps(out, ensure_ascii=False, indent=1, default=str),
                                                encoding="utf-8")
    ecrire_md(out)
    print("audit : fait")


def _f(x, n=2, sgn=False):
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return "—"
    s = f"{x:+.{n}f}" if sgn else f"{x:.{n}f}"
    return s.replace(".", ",").replace("-", "−")


def ecrire_md(out: dict) -> None:
    L = ["# Vérification des données FTMO (D05.1)", "",
         f"*Généré par `audit_ftmo_D05_1.py` le {out['date']} ; fiches : `{out['fichier_fiches']}` ; "
         f"{out['symboles_du_compte']} symboles actifs sur le compte.*", "",
         "## 1. Bougies M30", "",
         "| Actif | Symbole | Barres | Première | Dernière | Trous | Plus long (h) | Motif le plus fréquent | Plates |",
         "|---|---|---|---|---|---|---|---|---|"]
    for cle, r in out["symboles"].items():
        if "bougies" not in r:
            L.append(f"| {cle} | {r['symbole']} | absent | | | | | | |")
            continue
        g = r["bougies"]
        L.append(f"| {cle} | {r['symbole']} | {g['barres']} | {g['premiere'][:16]} | {g['derniere'][:16]} | "
                 f"{g['trous']} | {_f(g['plus_long_trou_h'], 1)} | {(g['motifs_recurrents'] or ['—'])[0]} | "
                 f"{g['plates']} |")
    L += ["", "## 2. Écarts (ticks, ouverture des barres, bps du milieu)", "",
          "| Actif | Période | Barres | Médiane | Moyenne | P90 | Max | Semaine | Week-end |", "|---|---|---|---|---|---|---|---|---|"]
    for cle, r in out["symboles"].items():
        t = r.get("ticks")
        if t:
            L.append(f"| {cle} | {t['debut'][:10]} → {t['fin'][:10]} | {t['barres_mesurees']} | "
                     f"{_f(t['ecart_median_bps'])} | {_f(t['ecart_moyen_bps'])} | {_f(t['ecart_p90_bps'])} | "
                     f"{_f(t['ecart_max_bps'], 1)} | {_f(t['ecart_median_semaine_bps'])} | "
                     f"{_f(t['ecart_median_weekend_bps'])} |")
    L += ["", "## 3. Fiches : swaps et commission (bps du notionnel au dernier prix ; coût positif)", "",
          "| Actif | Description | Swap (type) | Long / nuit | Short / nuit | Triple | Commission (type) | "
          "Commission / côté | Levier |", "|---|---|---|---|---|---|---|---|---|"]
    for cle, r in out["symboles"].items():
        f = r.get("fiche")
        if not f:
            continue
        if f["version_fiche"] == 1:
            L.append(f"| {cle} | {f['description']} | v1 : {f['swap_long']} / {f['swap_short']} (unité inconnue) "
                     "| | | | | | |")
            continue
        L.append(f"| {cle} | {f['description']} | {f['swap_type']} ({f['swap_long']} / {f['swap_short']}) | "
                 f"{_f(f['swap_cout_long_bps_nuit'], 2, True)} | {_f(f['swap_cout_short_bps_nuit'], 2, True)} | "
                 f"{f['swap_triple'] or '—'} | {f['commission_type']} ({f['commission']}) | "
                 f"{_f(f['commission_bps_cote_usd'])} | {f['levier_paliers']} |")
    L += ["", "## 4. Recoupement avec les séries du dépôt (barres communes)", "",
          "| Actif | Référence | Barres communes | Corrélation 30 min | Décalage du max | Niveau médian (bps) | "
          "P1 ; P99 (bps) |", "|---|---|---|---|---|---|---|"]
    for cle, r in out["symboles"].items():
        c = r.get("recoupement")
        if not c or "correlation_30min" not in c:
            continue
        L.append(f"| {cle} | {c['reference']} | {c['barres_communes']} | {_f(c['correlation_30min'], 4)} | "
                 f"{c['decalage_max_correlation']} | {_f(c['niveau_median_bps'], 1, True)} | "
                 f"{_f(c['niveau_p1_bps'], 1, True)} ; {_f(c['niveau_p99_bps'], 1, True)} |")
    (HERE / "audit_ftmo_D05_1.md").write_text("\n".join(L) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
