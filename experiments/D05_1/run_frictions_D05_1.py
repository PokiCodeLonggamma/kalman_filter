"""EXP-D05.1, étape 1 — frictions FTMO et « Baseline cTrader » : référence, piste 1 et piste 2 recalculées avec les
coûts réels du compte FTMO.

GO du porteur du 2026-10-06 : « Étape 1 : Frictions & Baseline. Analyse les ticks et les swaps. Applique-les aux
Cryptos pour générer notre "Baseline cTrader" de la P1 et P2 (sur 2020-2026). »

Cadrage (fixé avant le calcul ; lecture descriptive, sans seuil) :
- QUESTION : que deviennent la référence (0,20 × 0,20), la piste 1 (0,20 × 0,25) et la piste 2 (0,25 × 0,25, « Burn &
  Churn » : rachat de 540 € au minuit qui suit chaque échec) quand les frais conventionnels (5 bps, or 4 bps) sont
  remplacés par les frictions du compte FTMO (écart à l'heure du trade, commission, swaps) ?
- DONNÉES : trades de RE-1 version finale sur les six actifs de D05 (D04.1 : BTC, ETH, SOL, AVAX, XRP, or ; prix des
  courtiers de D05), fenêtre commune 2021-10-01 → 2026-10-01 (AVAX coté depuis le 2021-09-30 : le portefeuille à six
  actifs ne peut pas commencer en 2020) ; frictions : ticks FTMO du 2026-09-27 au 2026-10-05 et fiches des symboles
  (cBot AkfExportFtmo, versions 1 et 2).
- MÉTHODE : un seul facteur change, le modèle de frais : (a) convention de D05 ; (b) écart + commission FTMO ; (c) (b) +
  swaps = Baseline cTrader. Moteur, tailles, règles FTMO Swing, marge 1:2 (or 1:30) plafonnée, lecture principale de
  D05.4 et compte financé de D05.5 : inchangés. Contrôle bloquant : (a) redonne le roster de D05.6bis.
- CE QUE ÇA MESURE : réussite, délai médian et P90 du challenge ; valeur d'une tentative et d'une suite (12 et 24 mois,
  sans 2026) ; écarts appariés (b − a, c − a) par départ ; 8 métriques du portefeuille ; frais par actif en bps et en
  ATR ; part des trades qui traversent un rollover ; trades entrés ou sortis pendant une pause de cotation FTMO.
- CE QUE ÇA NE PERMET PAS DE CONCLURE : écarts mesurés sur huit jours de 2026, appliqués à 2021-2026 (convention de
  D02.0 : coûts actuels sur les années anciennes) ; rollover à 17:00 New York et base de 360 jours pour les swaps en %
  ([HYP]) ; swap imputé à la sortie, pas chaque nuit ; prix des courtiers de D05, pas ceux de FTMO ; pauses de
  maintenance FTMO des cryptos comptées, pas modélisées ; mêmes biais que D05 (données déjà lues, 2026 favorable,
  départs chevauchants).

Usage, depuis la racine du dépôt : python experiments/D05_1/run_frictions_D05_1.py --import | --frictions | --baseline
`--import` : séries M30 du cBot → data/raw/ftmo/ftmo_<clé>_30m.csv (schéma de `load_ohlc`, .meta.json).
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "src"))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

spec = importlib.util.spec_from_file_location("run_D05_6bis", ROOT / "experiments" / "D05_6bis" / "run_D05_6bis.py")
D056B = importlib.util.module_from_spec(spec)
spec.loader.exec_module(D056B)
D055, D054, D041, D04, D01 = D056B.D055, D056B.D054, D056B.D041, D056B.D04, D056B.D01

from envelope import risk_weights  # noqa: E402
from envelope.portfolio import Leg, portfolio_paths  # noqa: E402
from marketdata.ftmo import ecarts_barres, ecrire_serie, lire_bougies, lire_fiches, lire_ticks, profil_ecarts  # noqa: E402
from propfirm import (FTMO_SWING, LEVIER_FTMO_SWING, challenge, departs_minuit, ic_blocs, resume, simuler,  # noqa: E402
                      suite, valeur)
from propfirm.frictions import commission_bps, couts_trades, jours_swap, swap_bps  # noqa: E402
from reserve import levee  # noqa: E402

RAW = ROOT / "data" / "raw" / "ftmo"
EXPORTS = {"export_2026-10-06": "2026-10-05T23:23:22Z", "export_2026-10-06_v2": None}   # heure de fin du cBot (journal)
MOTIF = "EXP-D05.1, étape 1 : frictions FTMO et Baseline cTrader (porteur, 2026-10-06)"
NOMS = {"BTC": "BTCUSD", "ETH": "ETHUSD", "SOL": "SOLUSD", "AVAX": "AVAUSD", "XRP": "XRPUSD", "XAU": "XAUUSD",
        "US100": "US100.cash", "US30": "US30.cash", "GER40": "GER40.cash", "GBPJPY": "GBPJPY", "WTI": "USOIL.cash",
        "BRENT": "UKOIL.cash", "SAN": "SAN"}
CRYPTO = ("BTC", "ETH", "SOL", "AVAX", "XRP")
FUSEAU = {k: ("Europe/Berlin" if k in ("GER40", "SAN") else "America/New_York") for k in NOMS}   # fixés avant calcul
PRIX_D05 = {"BTC": "mid", "ETH": "mid", "SOL": "mid", "AVAX": "mid", "XRP": "mid", "XAU": "bid"}  # HistData : bid
MODELES = ("convention", "ecart_commission", "baseline_ctrader")
ROSTER = (("Référence", "fixe 0,20", "fixe 0,20"), ("Piste 1", "fixe 0,20", "fixe 0,25"),
          ("Piste 2", "fixe 0,25", "fixe 0,25"))
A, B = D054.A, D054.B


def stop(msg: str):
    raise SystemExit(f"D05.1 étape 1, contrôle bloquant : {msg} : arrêt")


def fichier(nom: str) -> Path:
    """Fichier d'export le plus récent qui porte ce nom."""
    for exp in reversed(list(EXPORTS)):
        p = RAW / exp / nom
        if p.exists():
            return p
    raise FileNotFoundError(nom)


def propre(nom: str) -> str:
    return "".join(c.lower() if c.isalnum() else "_" for c in nom)


def run_import() -> None:
    out = {}
    with levee(MOTIF):
        for cle, nom in NOMS.items():
            try:
                src = fichier(f"ftmo_{propre(nom)}_m30.csv")
            except FileNotFoundError:
                print(f"{cle} : bougies absentes des exports", flush=True)
                continue
            exp = src.parent.name
            if EXPORTS[exp] is None:
                stop(f"heure de fin de {exp} inconnue (journal du cBot)")
            b = lire_bougies(src, fin=pd.Timestamp("2100-01-01", tz="UTC"))
            meta = {"source": "FTMO, compte d'essai cTrader (cBot AkfExportFtmo)", "symbole": nom, "export": exp,
                    "fichier_source": src.name, "decision": "porteur, 2026-10-05 et 2026-10-06 (D05.1)"}
            out[cle] = ecrire_serie(b, RAW / f"ftmo_{cle.lower()}_30m.csv", meta, extrait=EXPORTS[exp])
            print(f"{cle} : {out[cle]['n_rows']} barres, {out[cle]['first']} → {out[cle]['last']}", flush=True)
    (HERE / "import_ftmo_D05_1.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")


# ── Frictions ───────────────────────────────────────────────────────────────────
def fiches() -> pd.DataFrame:
    f = lire_fiches(fichier("ftmo_symboles_fiches.csv"))
    if "swap_type" not in f.columns:
        stop("fiches de la version 2 du cBot requises (type de swap, commission)")
    return f


def mesurer_ecarts(cle: str) -> tuple[pd.Series, pd.DataFrame, dict]:
    """Écarts à l'ouverture des barres FTMO couvertes par les ticks, profil par demi-heure locale, résumé."""
    nom = NOMS[cle]
    t = lire_ticks(fichier(f"ftmo_{propre(nom)}_ticks.csv"))
    b = lire_bougies(fichier(f"ftmo_{propre(nom)}_m30.csv"), fin=pd.Timestamp("2100-01-01", tz="UTC"))
    o = pd.DatetimeIndex(b.time[(b.time >= t.time.iat[0]) & (b.time <= t.time.iat[-1])])
    e = ecarts_barres(t, o).dropna()
    we = e.index.dayofweek >= 5
    p = profil_ecarts(e, FUSEAU[cle])
    top = p.mediane.nlargest(3)
    res = {"cle": cle, "symbole": nom, "ticks": len(t), "barres_mesurees": len(e), "debut": str(t.time.iat[0]),
           "fin": str(t.time.iat[-1]), "ecart_median_bps": float(e.median()), "ecart_moyen_bps": float(e.mean()),
           "ecart_p90_bps": float(e.quantile(0.9)), "ecart_max_bps": float(e.max()),
           "ecart_median_semaine_bps": float(e[~we].median()),
           "ecart_median_weekend_bps": float(e[we].median()) if we.any() else np.nan,
           "pires_demi_heures": "; ".join(f"{int(i) // 2:02d}:{30 * (int(i) % 2):02d} {v:.1f}" for i, v in top.items()),
           "dernier_prix": float(b.close.iat[-1])}
    return e, p, res


def pauses(cle: str) -> pd.DataFrame:
    """Trous de cotation de la série FTMO (débuts et fins des barres manquantes, en ns)."""
    b = lire_bougies(fichier(f"ftmo_{propre(NOMS[cle])}_m30.csv"), fin=pd.Timestamp("2100-01-01", tz="UTC"))
    t = b.time.astype("int64").to_numpy()
    d = np.diff(t)
    k = np.flatnonzero(d > 30 * 60 * 10**9)
    return pd.DataFrame({"debut": t[k] + 30 * 60 * 10**9, "fin": t[k + 1], "heures": d[k] / 3.6e12 - 0.5})


def resume_fiche(cle: str, f: pd.Series, prix: float) -> dict:
    sl = float(swap_bps(f.swap_type, f.swap_long, prix, float(f.pip_size), int(f.digits)))
    ss = float(swap_bps(f.swap_type, f.swap_short, prix, float(f.pip_size), int(f.digits)))
    com = float(commission_bps(f.commission_type, float(f.commission), prix, float(f.lot_size)))
    return {"description": f.description, "swap_type": f.swap_type, "swap_long": f.swap_long, "swap_short": f.swap_short,
            "swap_triple": f.swap_triple if isinstance(f.swap_triple, str) else "",
            "swap_long_bps_nuit": sl, "swap_short_bps_nuit": ss, "commission_type": f.commission_type,
            "commission": f.commission, "commission_bps_cote": com, "levier_paliers": f.levier_paliers,
            "seances": f.seances}


def couts_d05(assets: dict, f: pd.DataFrame, profils: dict) -> dict[str, pd.DataFrame]:
    """Frictions FTMO des trades de la fenêtre commune, par actif."""
    out = {}
    for key in D041.KEYS:
        p = assets[key]
        tr = D041.window_trades(p, A, B)
        c = couts_trades(tr, p["bars"], f.loc[NOMS[key]], profils[key].mediane, FUSEAU[key], prix=PRIX_D05[key],
                         sept_jours=key in CRYPTO)
        c.insert(0, "cle", key)
        c.insert(1, "entree", p["bars"].time.iloc[tr.entry_bar.to_numpy()].to_numpy())
        c.insert(2, "sens", tr.side.to_numpy())
        c["brut_bps"] = tr.ret_gross_bps.to_numpy(dtype=float)
        c["atr_bps"] = p["atr_bps"][tr.signal_bar.to_numpy()]
        c["convention"] = D04.FEES[key][0]
        c["sortie"] = p["bars"].time.iloc[tr.exit_bar.to_numpy()].to_numpy()
        out[key] = c
    return out


def run_frictions() -> None:
    t0 = time.time()
    f = fiches()
    rows, prof, pa = [], [], []
    with levee(MOTIF):
        for cle in NOMS:
            try:
                _, p, res = mesurer_ecarts(cle)
            except FileNotFoundError:
                print(f"{cle} : ticks absents", flush=True)
                continue
            if NOMS[cle] not in f.index:
                stop(f"{cle} : fiche absente")
            res.update(resume_fiche(cle, f.loc[NOMS[cle]], res["dernier_prix"]))
            q = pauses(cle)
            an = pd.to_datetime(q.debut, utc=True).dt.year
            res["pauses_par_an"] = json.dumps({int(y): int(n) for y, n in an.value_counts().sort_index().items()})
            res["heures_manquantes_par_an"] = json.dumps(
                {int(y): round(float(h), 1) for y, h in q.heures.groupby(an.to_numpy()).sum().items()})
            rows.append(res)
            prof.append(p.assign(cle=cle).reset_index(names="demi_heure"))
            pa.append(q.assign(cle=cle))
            print(f"{cle} : écart médian {res['ecart_median_bps']:.2f} bps ; swap {res['swap_long_bps_nuit']:+.2f} / "
                  f"{res['swap_short_bps_nuit']:+.2f} bps par nuit ; commission {res['commission_bps_cote']:.2f} bps "
                  "par côté", flush=True)
        profils = {r["cle"]: prof[i].set_index("demi_heure") for i, r in enumerate(rows)}
        manquants = [k for k in D041.KEYS if k not in profils]
        if manquants:
            stop(f"écarts FTMO absents pour {manquants}")
        assets = D041.load_all()
        couts = couts_d05(assets, f, profils)
    pd.DataFrame(rows).to_csv(HERE / "frictions_D05_1.csv", index=False, float_format="%.6g")
    pd.concat(prof, ignore_index=True).to_csv(HERE / "profils_ecarts_D05_1.csv", index=False, float_format="%.6g")
    allc = pd.concat(couts.values(), ignore_index=True)
    allc.to_csv(HERE / "couts_trades_D05_1.csv.gz", index=False, float_format="%.6g")
    pauses_all = pd.concat(pa, ignore_index=True)
    synth = []
    for key, c in couts.items():
        q = pauses_all[pauses_all.cle == key]
        e, x = c.entree.astype("int64").to_numpy(), c.sortie.astype("int64").to_numpy()
        dans = lambda t: ((t[:, None] >= q.debut.to_numpy()[None, :]) & (t[:, None] < q.fin.to_numpy()[None, :])).any(1)  # noqa: E731
        synth.append({"cle": key, "trades": len(c), "convention_bps": float(c.convention.iat[0]),
                      "ecart_bps": float(c.ecart.mean()), "commission_bps": float(c.commission.mean()),
                      "swap_bps": float(c.swap.mean()), "total_bps": float(c.total.mean()),
                      "total_atr": float((c.total / c.atr_bps).mean()),
                      "convention_atr": float((c.convention / c.atr_bps).mean()),
                      "part_avec_rollover": float((c.nuits > 0).mean()), "nuits_moyennes": float(c.nuits.mean()),
                      "brut_atr": float((c.brut_bps / c.atr_bps).mean()),
                      "net_convention_atr": float(((c.brut_bps - c.convention) / c.atr_bps).mean()),
                      "net_ftmo_atr": float(((c.brut_bps - c.total) / c.atr_bps).mean()),
                      "entrees_en_pause": int(dans(e).sum()), "sorties_en_pause": int(dans(x).sum())})
    pd.DataFrame(synth).to_csv(HERE / "couts_actifs_D05_1.csv", index=False, float_format="%.6g")
    print(f"frictions : fait en {time.time() - t0:.0f} s")


# ── Baseline cTrader ────────────────────────────────────────────────────────────
def jambes(assets: dict, couts: pd.DataFrame, modele: str) -> list[Leg]:
    out = []
    for key in D041.KEYS:
        p = assets[key]
        tr = D041.window_trades(p, A, B)
        c = couts[couts.cle == key]
        if len(c) != len(tr):
            stop(f"{key} : {len(c)} frais pour {len(tr)} trades")
        cost = {"convention": D04.FEES[key][0], "ecart_commission": (c.ecart + c.commission).to_numpy(),
                "baseline_ctrader": c.total.to_numpy()}[modele]
        out.append(Leg(key, p["bars"], tr, risk_weights(p["atr_bps"][tr.signal_bar.to_numpy()], 25.0), cost))
    return out


def run_baseline() -> None:
    t0 = time.time()
    couts = pd.read_csv(HERE / "couts_trades_D05_1.csv.gz")
    roster = pd.read_csv(ROOT / "experiments" / "D05_6bis" / "roster_D05_6bis.csv")
    tc, tf = dict(D056B.CHALLENGE), dict(D056B.FINANCE)
    rows, ch_rows, comps, m8, ctrl, per = [], [], [], [], {}, {}
    with levee(MOTIF):
        assets = D041.load_all()
        departs = departs_minuit(A, B, FTMO_SWING.fuseau)
        for modele in MODELES:
            lg = jambes(assets, couts, modele)
            atr = [assets[leg.name]["atr_bps"][leg.trades.signal_bar.to_numpy()] for leg in lg]
            opts = dict(levier=LEVIER_FTMO_SWING, plafonner=True, atr=atr)
            sims_c = {n: simuler(lg, departs, taille=tc[n], **opts) for n in dict.fromkeys(c for _, c, _ in ROSTER)}
            sims_f = {n: simuler(lg, departs, D055.FINANCE, taille=tf[n], retrait_jours=D055.RETRAIT_JOURS, **opts)
                      for n in dict.fromkeys(f for _, _, f in ROSTER)}
            for n, sim in sims_c.items():
                for fen, coup in D056B.FENETRES:
                    ch_rows.append({"modele": modele, "challenge": n, "fenetre": fen,
                                    **resume(challenge(sim, coupure=coup))})
            for piste, cn, fn in ROSTER:
                for lect, h, coup in D056B.LECTURES_ROSTER:
                    kw = dict(frais=D055.FRAIS, part=D055.PART, horizon_jours=h, coupure=coup)
                    for mes, fn_ in (("tentative", valeur), ("suite", suite)):
                        df = D055.suivis(fn_(sims_c[cn], sims_f[fn], **kw), h, coup)
                        per[(modele, piste, lect, mes)] = df
                        x = df.valeur.to_numpy()
                        if modele == "convention":
                            ref = roster[(roster.piste == piste) & (roster.lecture == lect) & (roster.mesure == mes)]
                            if not np.isclose(x.mean(), ref.valeur.iat[0], rtol=1e-5):
                                stop(f"convention, {piste}, {lect}, {mes} : ne redonne pas le roster de D05.6bis")
                            ctrl[f"{piste}_{lect}_{mes}_egal_D05_6bis"] = round(float(x.mean()), 6)
                        lo, hi = ic_blocs(x, df.depart)
                        row = {"modele": modele, "piste": piste, "challenge": cn, "finance": fn, "lecture": lect,
                               "mesure": mes, "n_departs": len(df), "valeur": float(x.mean()), "ic_bas": lo,
                               "ic_haut": hi, "mediane": float(np.median(x)), "p10": float(np.quantile(x, 0.1)),
                               "p90": float(np.quantile(x, 0.9))}
                        if mes == "tentative":
                            row.update(p_retrait=float((df.n_retraits > 0).mean()))
                        else:
                            row.update(tentatives=float(df.n_tentatives.mean()), finances=float(df.n_finances.mean()))
                        rows.append(row)
            lg1 = [Leg(leg.name, leg.bars, leg.trades, np.ones(len(leg.trades)), leg.cost) for leg in lg]
            m8.append({"modele": modele, **D041.metrics8(lg, lg1, portfolio_paths(lg), portfolio_paths(lg1), assets,
                                                          A, B)})
            print(f"{modele} : simulé ({time.time() - t0:.0f} s)", flush=True)
    for modele in MODELES[1:]:
        for piste, _, _ in ROSTER:
            for lect, _, _ in D056B.LECTURES_ROSTER:
                for mes in ("tentative", "suite"):
                    da, db = per[(modele, piste, lect, mes)], per[("convention", piste, lect, mes)]
                    if not da.depart.equals(db.depart):
                        stop(f"{modele}, {piste}, {lect} : départs différents")
                    dx = da.valeur.to_numpy() - db.valeur.to_numpy()
                    lo, hi = ic_blocs(dx, da.depart)
                    comps.append({"modele": modele, "contre": "convention", "piste": piste, "lecture": lect,
                                  "mesure": mes, "ecart": float(dx.mean()), "ic_bas": lo, "ic_haut": hi,
                                  "p_mieux": float((dx > 1e-12).mean()), "p_moins": float((dx < -1e-12).mean())})
    pd.DataFrame(rows).to_csv(HERE / "baseline_D05_1.csv", index=False, float_format="%.6g")
    pd.DataFrame(ch_rows).to_csv(HERE / "baseline_challenges_D05_1.csv", index=False, float_format="%.6g")
    pd.DataFrame(comps).to_csv(HERE / "baseline_ecarts_D05_1.csv", index=False, float_format="%.6g")
    pd.DataFrame(m8).to_csv(HERE / "baseline_metriques_D05_1.csv", index=False, float_format="%.6g")
    ctrl = {"date": pd.Timestamp.now(tz="UTC").strftime("%Y-%m-%d %H:%M UTC"), "commit": D04.git_head(),
            "motif": MOTIF, **ctrl, "duree_s": round(time.time() - t0)}
    (HERE / "controles_baseline_D05_1.json").write_text(json.dumps(D01.jsonable(ctrl), ensure_ascii=False, indent=1),
                                                        encoding="utf-8")
    print(f"baseline : faite en {ctrl['duree_s']} s")


def main() -> None:
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--import", dest="importer", action="store_true")
    g.add_argument("--frictions", action="store_true")
    g.add_argument("--baseline", action="store_true")
    a = ap.parse_args()
    if a.importer:
        run_import()
    elif a.frictions:
        run_frictions()
    else:
        run_baseline()


if __name__ == "__main__":
    main()
