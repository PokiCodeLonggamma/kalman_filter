"""EXP-D05.1, étape 1 — frictions FTMO (écart, commission, swaps, pauses de cotation) et « Baseline cTrader » :
référence, piste 1 et piste 2 recalculées avec les conditions réelles du compte FTMO.

GO du porteur du 2026-10-06 : « Étape 1 : Frictions & Baseline. Analyse les ticks et les swaps. Applique-les aux
Cryptos pour générer notre "Baseline cTrader" de la P1 et P2 (sur 2020-2026). » Décisions du même jour : les frictions
(trous, écart, swaps, commission) sont traitées dans cette session ; données cTrader pour les actifs hors crypto, séries
des courtiers de D05 pour les cryptos ; la Baseline (`--baseline`) se lance dans la session suivante.

Cadrage (fixé avant le calcul ; lecture descriptive, sans seuil) :
- QUESTION : que deviennent la référence (0,20 × 0,20), la piste 1 (0,20 × 0,25) et la piste 2 (0,25 × 0,25, « Burn &
  Churn » : rachat de 540 € au minuit qui suit chaque échec) dans les conditions du compte FTMO ?
- DONNÉES : trades de RE-1 version finale sur les six actifs de D05 (D04.1), fenêtre commune 2021-10-01 → 2026-10-01
  (AVAX coté depuis le 2021-09-30 : le portefeuille à six actifs ne peut pas commencer en 2020) ; cryptos sur les
  séries des courtiers (Bitstamp, Coinbase) ; or sur HistData puis sur les barres FTMO ; frictions : ticks FTMO du
  2026-09-25 au 2026-10-05, fiches des symboles (cBot AkfExportFtmo v2), calendrier des pauses tiré des barres FTMO.
- MÉTHODE : une échelle de modèles, un facteur ajouté à chaque marche (écart apparié marche par marche) :
  1. `convention` : 5 bps (or 4 bps), contrôle bloquant : redonne le roster de D05.6bis ;
  2. `ecart_commission` : écart à l'heure de l'entrée et de la sortie + commission des deux côtés ;
  3. `swaps` : + swap de chaque rollover traversé ;
  4. `pauses` : + exécution des cryptos sur le calendrier FTMO (`propfirm.frictions.ajuster_pauses`) ;
  5. `or_ftmo` : + or sur les barres FTMO (signaux, prix et frictions FTMO) ;
  6. `levier_compte` : + levier du compte d'essai (fiches : cryptos 1:1, or 1:15) au lieu de l'étalon de D05.4 (1:2 et
     1:30) = Baseline cTrader.
  Moteur, tailles, règles FTMO Swing, marge 1:2 (or 1:30) plafonnée, lecture principale de D05.4 et compte financé de
  D05.5 : inchangés.
- CE QUE ÇA MESURE : réussite, délai médian et P90 du challenge ; valeur d'une tentative et d'une suite (12 et 24 mois,
  sans 2026, sans 2026 à 24 mois) ; écarts appariés par départ ; 8 métriques du portefeuille ; frictions par actif en
  bps et en ATR ; trades touchés par les pauses.
- CE QUE ÇA NE PERMET PAS DE CONCLURE : écarts mesurés sur dix jours de 2026, appliqués à 2021-2026 (convention de
  D02.0 : coûts actuels sur les années anciennes) ; rollover à 17:00 New York et base de 360 jours pour les swaps en %
  ([HYP]) ; swap imputé à la sortie ; calendrier des pauses de BTC pour SOL et AVAX avant leur historique FTMO ; un
  stop franchi pendant une pause est exécuté à la réouverture même si le prix est revenu ([HYP]) ; pauses du samedi
  absentes des séances officielles des fiches (maintenance ou trous du serveur d'essai : [HYP]) ; AVAX : écart et fiche
  de SOLUSD (AVAUSD non exporté, [HYP]) ; commission de GBPJPY convertie au taux USD/JPY du 2025-12-31 ; mêmes biais que D05
  (données déjà lues, 2026 favorable, départs chevauchants).

Usage, depuis la racine du dépôt : python experiments/D05_1/run_frictions_D05_1.py --import | --frictions | --baseline
- `--import` : bougies M30 du cBot → data/raw/ftmo/ftmo_<clé>_30m.csv (schéma de `load_ohlc`, .meta.json) ;
- `--frictions` : écarts, fiches, pauses, frictions trade par trade des six actifs (descriptif, sans simulation) ;
- `--baseline` : l'échelle des cinq modèles sur le roster (session suivante, sur GO).
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
from marketdata.ftmo import (ecarts_barres, ecrire_serie, lire_bougies, lire_fiches, lire_ticks,  # noqa: E402
                             pauses_cotation, profil_ecarts)
from propfirm import (FTMO_SWING, LEVIER_FTMO_SWING, challenge, departs_minuit, ic_blocs, resume, simuler,  # noqa: E402
                      suite, valeur)
from propfirm.frictions import ajuster_pauses, commission_bps, couts_trades, swap_bps  # noqa: E402
from reserve import levee  # noqa: E402

RAW = ROOT / "data" / "raw" / "ftmo"
EXPORTS = {"export_2026-10-06": "2026-10-05T23:23:22Z", "export_2026-10-06_v2": "2026-10-06T00:21:48Z"}  # fin (journal)
MOTIF = "EXP-D05.1, étape 1 : frictions FTMO et Baseline cTrader (porteur, 2026-10-06)"
NOMS = {"BTC": "BTCUSD", "ETH": "ETHUSD", "SOL": "SOLUSD", "AVAX": "AVAUSD", "XRP": "XRPUSD", "XAU": "XAUUSD",
        "US100": "US100.cash", "US30": "US30.cash", "GER40": "GER40.cash", "GBPJPY": "GBPJPY", "WTI": "USOIL.cash",
        "BRENT": "UKOIL.cash", "SAN": "SAN"}
CRYPTO = ("BTC", "ETH", "SOL", "AVAX", "XRP")
FUSEAU = {k: ("Europe/Berlin" if k in ("GER40", "SAN") else "America/New_York") for k in NOMS}   # fixés avant calcul
PRIX_D05 = {"BTC": "mid", "ETH": "mid", "SOL": "mid", "AVAX": "mid", "XRP": "mid", "XAU": "bid"}  # HistData : bid
MODELES = ("convention", "ecart_commission", "swaps", "pauses", "or_ftmo", "levier_compte")
USD_PAR_COTATION = {"GBPJPY": 1.0 / 156.8}          # USD par JPY : FRED DEXJPUS du 2025-12-31 ([HYP] taux constant)
SUBSTITUT = {"AVAX": "SOL"}                         # AVAUSD non exporté : écart et fiche de SOLUSD ([HYP])
ROSTER = (("Référence", "fixe 0,20", "fixe 0,20"), ("Piste 1", "fixe 0,20", "fixe 0,25"),
          ("Piste 2", "fixe 0,25", "fixe 0,25"))
A, B = D054.A, D054.B
TOUT = pd.Timestamp("2100-01-01", tz="UTC")


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


def bougies(cle: str) -> pd.DataFrame:
    return lire_bougies(fichier(f"ftmo_{propre(NOMS[cle])}_m30.csv"), fin=TOUT)


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
            meta = {"source": "FTMO, compte d'essai cTrader (cBot AkfExportFtmo)", "symbole": nom, "export": exp,
                    "fichier_source": src.name, "decision": "porteur, 2026-10-05 et 2026-10-06 (D05.1)"}
            out[cle] = ecrire_serie(lire_bougies(src, fin=TOUT), RAW / f"ftmo_{cle.lower()}_30m.csv", meta,
                                    extrait=EXPORTS[exp])
            print(f"{cle} : {out[cle]['n_rows']} barres, {out[cle]['first']} → {out[cle]['last']}", flush=True)
    (HERE / "import_ftmo_D05_1.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")


# ── Frictions ───────────────────────────────────────────────────────────────────
def fiches() -> pd.DataFrame:
    f = lire_fiches(fichier("ftmo_symboles_fiches.csv"))
    if "swap_type" not in f.columns:
        stop("fiches de la version 2 du cBot requises (type de swap, commission)")
    return f


def mesurer_ecarts(cle: str) -> tuple[pd.DataFrame, dict]:
    """Profil par demi-heure locale des écarts à l'ouverture des barres FTMO couvertes par les ticks, et résumé."""
    t = lire_ticks(fichier(f"ftmo_{propre(NOMS[cle])}_ticks.csv"))
    b = bougies(cle)
    o = pd.DatetimeIndex(b.time[(b.time >= t.time.iat[0]) & (b.time <= t.time.iat[-1])])
    e = ecarts_barres(t, o).dropna()
    we = e.index.dayofweek >= 5
    p = profil_ecarts(e, FUSEAU[cle])
    top = p.mediane.nlargest(3)
    res = {"cle": cle, "symbole": NOMS[cle], "ticks": len(t), "barres_mesurees": len(e), "debut": str(t.time.iat[0]),
           "fin": str(t.time.iat[-1]), "ecart_median_bps": float(e.median()), "ecart_moyen_bps": float(e.mean()),
           "ecart_p90_bps": float(e.quantile(0.9)), "ecart_max_bps": float(e.max()),
           "ecart_median_semaine_bps": float(e[~we].median()),
           "ecart_median_weekend_bps": float(e[we].median()) if we.any() else np.nan,
           "pires_demi_heures_locales": "; ".join(f"{int(i) // 2:02d}:{30 * (int(i) % 2):02d} {v:.1f}"
                                                  for i, v in top.items()),
           "dernier_prix": float(b.close.iat[-1])}
    return p, res


def resume_fiche(cle: str, f: pd.Series, prix: float) -> dict:
    sl = float(swap_bps(f.swap_type, f.swap_long, prix, float(f.pip_size), int(f.digits)))
    ss = float(swap_bps(f.swap_type, f.swap_short, prix, float(f.pip_size), int(f.digits)))
    com = float(commission_bps(f.commission_type, float(f.commission), prix, float(f.lot_size),
                               USD_PAR_COTATION.get(cle, 1.0)))
    return {"description": f.description, "swap_type": f.swap_type, "swap_long": f.swap_long, "swap_short": f.swap_short,
            "swap_triple": f.swap_triple if isinstance(f.swap_triple, str) else "",
            "swap_cout_long_bps_nuit": sl, "swap_cout_short_bps_nuit": ss, "commission_type": f.commission_type,
            "commission": f.commission, "commission_bps_cote": com, "levier_paliers": f.levier_paliers,
            "levier": levier(f), "seances": f.seances}


def levier(f: pd.Series) -> float:
    """Levier du premier palier de la fiche (« volume:levier|… »)."""
    return float(str(f.levier_paliers).split("|")[0].split(":")[1])


def fiche(f: pd.DataFrame, cle: str) -> tuple[pd.Series, str]:
    """Fiche du symbole, ou celle de son substitut ; et le nom de la source."""
    if NOMS[cle] in f.index:
        return f.loc[NOMS[cle]], NOMS[cle]
    if cle in SUBSTITUT and NOMS[SUBSTITUT[cle]] in f.index:
        return f.loc[NOMS[SUBSTITUT[cle]]], NOMS[SUBSTITUT[cle]]
    stop(f"{cle} : fiche absente")


def calendrier(cle: str) -> pd.DataFrame:
    """Pauses de cotation FTMO d'une crypto : les siennes sur son historique FTMO, celles de BTC avant (pauses communes
    à la plateforme : 357 des 368 pauses d'ETH sont aussi celles de BTC)."""
    btc = pauses_cotation(bougies("BTC").time)
    try:
        b = bougies(cle)
    except FileNotFoundError:
        return btc.assign(source="BTC")
    t0 = b.time.iat[0].value
    propre_ = pauses_cotation(b.time).assign(source=cle)
    avant = btc[btc.fin <= t0].assign(source="BTC")
    return pd.concat([avant, propre_], ignore_index=True)


def serie_xau_ftmo() -> dict:
    """Or sur les barres FTMO, préparé comme les actifs de D04 (atlas, signaux, RE-1 version finale)."""
    p = D04.prepare("XAU", RAW / "ftmo_xau_30m.csv", D04.END)
    p["s"] = D04.final_series(p, None, None)
    return p


def trades_variantes(assets: dict, xau_ftmo: dict) -> tuple[dict, list]:
    """Trades de la fenêtre commune : `continu` (séries de D05), `ftmo` (cryptos sur le calendrier FTMO ; or sur les
    barres FTMO)."""
    out, journal = {}, []
    for key in D041.KEYS:
        p = assets[key]
        tr = D041.window_trades(p, A, B)
        out[(key, "continu")] = (p, tr)
        if key in CRYPTO:
            adj, r = ajuster_pauses(tr, p["bars"], calendrier(key))
            out[(key, "ftmo")] = (p, adj)
            journal.append({"cle": key, **r})
        else:
            out[(key, "ftmo")] = (xau_ftmo, D041.window_trades(xau_ftmo, A, B))
    return out, journal


def couts(variantes: dict, f: pd.DataFrame, profils: dict) -> pd.DataFrame:
    rows = []
    for (key, cal), (p, tr) in variantes.items():
        prix = "bid" if (key == "XAU" or cal == "ftmo" and key not in CRYPTO) else PRIX_D05[key]
        c = couts_trades(tr, p["bars"], fiche(f, key)[0], profils[key].mediane, FUSEAU[key], prix=prix,
                         sept_jours=key in CRYPTO, usd_par_cotation=USD_PAR_COTATION.get(key, 1.0))
        t = p["bars"].time
        c.insert(0, "cle", key)
        c.insert(1, "calendrier", cal)
        c.insert(2, "trade", np.arange(len(tr)))
        c.insert(3, "entree", t.iloc[tr.entry_bar.to_numpy()].to_numpy())
        c.insert(4, "sortie", t.iloc[tr.exit_bar.to_numpy()].to_numpy())
        c.insert(5, "sens", tr.side.to_numpy())
        c["brut_bps"] = tr.ret_gross_bps.to_numpy(dtype=float)
        c["atr_bps"] = p["atr_bps"][tr.signal_bar.to_numpy()]
        c["convention"] = D04.FEES[key][0]
        rows.append(c)
    return pd.concat(rows, ignore_index=True)


def run_frictions() -> None:
    t0 = time.time()
    f = fiches()
    rows, prof = [], []
    with levee(MOTIF):
        for cle in NOMS:
            try:
                p, res = mesurer_ecarts(cle)
            except FileNotFoundError:
                if cle in SUBSTITUT:
                    p, res = mesurer_ecarts(SUBSTITUT[cle])
                    res.update(cle=cle, substitut=NOMS[SUBSTITUT[cle]])
                    print(f"{cle} : ticks absents, écart de {NOMS[SUBSTITUT[cle]]} ([HYP])", flush=True)
                else:
                    print(f"{cle} : ticks absents", flush=True)
                    continue
            fi, source = fiche(f, cle)
            res.update(resume_fiche(cle, fi, res["dernier_prix"]), fiche_source=source)
            rows.append(res)
            prof.append(p.assign(cle=cle).reset_index(names="demi_heure"))
            print(f"{cle} : écart médian {res['ecart_median_bps']:.2f} bps ; swap {res['swap_cout_long_bps_nuit']:+.2f} / "
                  f"{res['swap_cout_short_bps_nuit']:+.2f} bps par nuit ; commission {res['commission_bps_cote']:.2f} bps "
                  "par côté", flush=True)
        profils = {r["cle"]: prof[i].set_index("demi_heure") for i, r in enumerate(rows)}
        manquants = [k for k in D041.KEYS if k not in profils]
        if manquants:
            stop(f"écarts FTMO absents pour {manquants}")
        assets = D041.load_all()
        variantes, journal = trades_variantes(assets, serie_xau_ftmo())
        c = couts(variantes, f, profils)
    pd.DataFrame(rows).to_csv(HERE / "frictions_D05_1.csv", index=False, float_format="%.6g")
    pd.concat(prof, ignore_index=True).to_csv(HERE / "profils_ecarts_D05_1.csv", index=False, float_format="%.6g")
    pd.DataFrame(journal).to_csv(HERE / "pauses_D05_1.csv", index=False)
    c.to_csv(HERE / "couts_trades_D05_1.csv.gz", index=False, float_format="%.6g")
    synth = []
    for (key, cal), g in c.groupby(["cle", "calendrier"], sort=False):
        a = g.atr_bps
        synth.append({"cle": key, "calendrier": cal, "trades": len(g), "convention_bps": float(g.convention.iat[0]),
                      "ecart_bps": float(g.ecart.mean()), "commission_bps": float(g.commission.mean()),
                      "swap_bps": float(g.swap.mean()), "total_bps": float(g.total.mean()),
                      "convention_atr": float((g.convention / a).mean()), "total_atr": float((g.total / a).mean()),
                      "swap_atr": float((g.swap / a).mean()), "part_avec_rollover": float((g.nuits > 0).mean()),
                      "nuits_moyennes": float(g.nuits.mean()), "brut_atr": float((g.brut_bps / a).mean()),
                      "net_convention_atr": float(((g.brut_bps - g.convention) / a).mean()),
                      "net_ftmo_atr": float(((g.brut_bps - g.total) / a).mean())})
    pd.DataFrame(synth).to_csv(HERE / "couts_actifs_D05_1.csv", index=False, float_format="%.6g")
    print(f"frictions : faites en {time.time() - t0:.0f} s")


# ── Baseline cTrader (session suivante) ─────────────────────────────────────────
def jambes(variantes: dict, c: pd.DataFrame, modele: str) -> tuple[list[Leg], dict]:
    """Jambes d'un modèle de l'échelle ; et les actifs (barres, ATR) qu'elles utilisent."""
    out, actifs = [], {}
    for key in D041.KEYS:
        cal = "continu" if modele in ("convention", "ecart_commission", "swaps") else "ftmo"
        if modele == "pauses" and key == "XAU":
            cal = "continu"
        p, tr = variantes[(key, cal)]
        g = c[(c.cle == key) & (c.calendrier == cal)].sort_values("trade")
        if len(g) != len(tr):
            stop(f"{key}, {modele} : {len(g)} frais pour {len(tr)} trades")
        cost = {"convention": D04.FEES[key][0], "ecart_commission": (g.ecart + g.commission).to_numpy()}.get(
            modele, g.total.to_numpy())
        out.append(Leg(key, p["bars"], tr, risk_weights(p["atr_bps"][tr.signal_bar.to_numpy()], 25.0), cost))
        actifs[key] = p
    return out, actifs


def run_baseline() -> None:
    t0 = time.time()
    c = pd.read_csv(HERE / "couts_trades_D05_1.csv.gz")
    roster = pd.read_csv(ROOT / "experiments" / "D05_6bis" / "roster_D05_6bis.csv")
    tc, tf = dict(D056B.CHALLENGE), dict(D056B.FINANCE)
    fi = fiches()
    rows, ch_rows, comps, m8, ctrl, per = [], [], [], [], {}, {}
    with levee(MOTIF):
        assets = D041.load_all()
        variantes, _ = trades_variantes(assets, serie_xau_ftmo())
        departs = departs_minuit(A, B, FTMO_SWING.fuseau)
        for modele in MODELES:
            lg, actifs = jambes(variantes, c, modele)
            atr = [actifs[leg.name]["atr_bps"][leg.trades.signal_bar.to_numpy()] for leg in lg]
            lev = LEVIER_FTMO_SWING if modele != "levier_compte" else {k: levier(fiche(fi, k)[0]) for k in D041.KEYS}
            opts = dict(levier=lev, plafonner=True, atr=atr)
            sims_c = {n: simuler(lg, departs, taille=tc[n], **opts) for n in dict.fromkeys(x for _, x, _ in ROSTER)}
            sims_f = {n: simuler(lg, departs, D055.FINANCE, taille=tf[n], retrait_jours=D055.RETRAIT_JOURS, **opts)
                      for n in dict.fromkeys(x for _, _, x in ROSTER)}
            for n, sim in sims_c.items():
                for fen, coup in D056B.FENETRES:
                    ch_rows.append({"modele": modele, "challenge": n, "fenetre": fen,
                                    **resume(challenge(sim, coupure=coup))})
            for piste, cn, fn in ROSTER:
                for lect, h, coup in D056B.LECTURES_ROSTER:
                    kw = dict(frais=D055.FRAIS, part=D055.PART, horizon_jours=h, coupure=coup)
                    for mes, f_ in (("tentative", valeur), ("suite", suite)):
                        df = D055.suivis(f_(sims_c[cn], sims_f[fn], **kw), h, coup)
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
            m8.append({"modele": modele, **D041.metrics8(lg, lg1, portfolio_paths(lg), portfolio_paths(lg1), actifs,
                                                          A, B)})
            print(f"{modele} : simulé ({time.time() - t0:.0f} s)", flush=True)
    for k in range(1, len(MODELES)):
        for piste, _, _ in ROSTER:
            for lect, _, _ in D056B.LECTURES_ROSTER:
                for mes in ("tentative", "suite"):
                    for contre in (MODELES[k - 1], MODELES[0]):
                        da, db = per[(MODELES[k], piste, lect, mes)], per[(contre, piste, lect, mes)]
                        if not da.depart.equals(db.depart):
                            stop(f"{MODELES[k]}, {piste}, {lect} : départs différents")
                        dx = da.valeur.to_numpy() - db.valeur.to_numpy()
                        lo, hi = ic_blocs(dx, da.depart)
                        comps.append({"modele": MODELES[k], "contre": contre, "piste": piste, "lecture": lect,
                                      "mesure": mes, "ecart": float(dx.mean()), "ic_bas": lo, "ic_haut": hi,
                                      "p_mieux": float((dx > 1e-12).mean()), "p_moins": float((dx < -1e-12).mean())})
                        if contre == MODELES[0] and k == 1:
                            break
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
