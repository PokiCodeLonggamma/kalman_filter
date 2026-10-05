"""EXP-D05.1 — Mesure de la grille de profil, sans RE-1 ni coût : ancres BTC et SOL, repère TradFi or (XAU), candidats
US100, US30, GER40 et GBPJPY (séries Saxo de D01.7), du 2020-01-01 au 2025-12-31.

GO du porteur du 2026-10-05 (« GO pour la mesure de la grille »), pendant l'attente de l'accord de Spotware.

Cadrage (fixé avant le calcul) :
- QUESTION : les candidats montrent-ils, en structure de marché, l'empreinte des marchés où RE-1 gagne (expansions de
  13 h nées du calme, des deux côtés, en continu ; persistance aux heures ; indépendance vis-à-vis des cryptos) ?
- PERTINENCE : grille de la note de profil, validée par le porteur ; mesure descriptive avant les données FTMO, dont
  viendront les coûts (écart, commission, swap).
- CE QUE LE PROTOCOLE MESURE : les axes calculables sur les barres (`profil.grille`) : échelle et plafond de 1x ; queue
  d'expansion et repère gaussien ; naissance au calme ; sauts ou expansions ; persistance ; symétrie ; saison horaire ;
  continuité ; gaps ; indépendance vis-à-vis de BTC ; activité pendant le creux du portefeuille de RE-1 (2023-07-13 →
  2024-01-27). Fenêtres disjointes de 26 barres.
- CE QU'IL NE PERMET PAS DE CONCLURE : aucune rentabilité (ni RE-1, ni coûts) ; source Saxo (prix vendeur), pas FTMO ;
  2020-2025 seulement ; aucun classement ni seuil (grille de lecture, le porteur lit) ; BTC 2020-2025 est la période de
  construction de RE-1. WTI, Brent et GLE seront mesurés sur les données FTMO.

Correction de la saison horaire (GO du porteur du 2026-10-06), cadrage fixé avant le calcul :
- QUESTION : la queue de 13 h des indices et de l'or tient-elle une fois retirée la saison horaire ?
- PERTINENCE : en ATR brut, US100 et US30 égalent BTC avec une saison horaire 2,4 à 2,6 fois plus marquée ; une marche
  gaussienne à saison pure (une barre par jour six fois plus agitée) donne déjà 49 fenêtres à 10 ATR ou plus pour
  1 000 en ATR brut (test du module).
- CE QUE LE PROTOCOLE MESURE : z26 corrigé = mouvement de 13 h / (ATR désaisonnalisé de t × racine de la moyenne des
  facteurs² de la fenêtre) ; facteur causal par demi-heure en heure locale, sur les 40 jours précédents ; fuseaux fixés
  avant le calcul : UTC (cryptos), New York (US100, US30, or), Francfort (GER40), Londres (GBPJPY) ; z26 brut sur les
  mêmes fenêtres ; même repère gaussien.
- CE QU'IL NE PERMET PAS DE CONCLURE : aucune rentabilité ; RE-1 utilise l'ATR14 brut pour ses stops et sa taille ;
  40 jours et demi-heure locale sont conventionnels, non optimisés ; mêmes limites de source que la grille.

Usage : python experiments/D05_1/run_grille_D05_1.py --calcul | --saison
Sorties : grille_D05_1.csv (une ligne par actif) et grille_D05_1.json (cadrage, sources, ATR par année, saison horaire) ;
grille_saison_D05_1.csv (correction horaire).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "src"))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from profil import grille  # noqa: E402
from strategy.re1 import load_asset  # noqa: E402

RAW = ROOT / "data" / "raw"
DEBUT = pd.Timestamp("2020-01-01", tz="UTC")
CREUX = (pd.Timestamp("2023-07-13", tz="UTC"), pd.Timestamp("2024-01-27", tz="UTC"))
ACTIFS = {
    "BTC": ("ancre crypto", "BTC/USD Bitstamp", RAW / "bitstamp_btcusd_30m.csv"),
    "SOL": ("ancre crypto", "SOL/USD Coinbase", RAW / "coinbase_solusd_30m.csv"),
    "XAU": ("repère TradFi du portefeuille", "CFD or XAU/USD HistData (bid)", RAW / "histdata_xauusd_30m.csv"),
    "US100": ("candidat", "CFD US Tech 100 Saxo (bid)", RAW / "saxo_us100_cfd_30m.csv"),
    "US30": ("candidat", "CFD US 30 Saxo (bid)", RAW / "saxo_us30_30m.csv"),
    "GER40": ("candidat", "CFD Germany 40 Saxo (bid)", RAW / "saxo_ger40_30m.csv"),
    "GBPJPY": ("candidat", "GBP/JPY au comptant Saxo (bid)", RAW / "saxo_gbpjpy_30m.csv"),
}
FUSEAUX = {"BTC": "UTC", "SOL": "UTC", "XAU": "America/New_York", "US100": "America/New_York",
           "US30": "America/New_York", "GER40": "Europe/Berlin", "GBPJPY": "Europe/London"}
JOURS_SAISON = 40


def calcul() -> None:
    lignes, details, quot = [], {}, {}
    for code, (role, nom, csv) in ACTIFS.items():
        _, bars = load_asset(csv)                                       # barres antérieures au 2026-01-01
        bars = bars[bars.time >= DEBUT].reset_index(drop=True)
        p = grille.profil(bars, creux=CREUX)
        quot[code] = grille.quotidien(bars)
        a = grille.atr(bars)
        bps = pd.Series(a / bars.close.to_numpy() * 1e4, index=bars.time.dt.year.to_numpy())
        details[code] = {"role": role, "nom": nom, "fichier": csv.name,
                         "atr_bps_mediane_par_annee": {int(k): round(float(v), 2)
                                                       for k, v in bps.iloc[grille.AMORCE:].groupby(level=0).median()
                                                       .items()},
                         "saison_tr_bps_par_heure_utc": {int(k): round(float(v), 2)
                                                         for k, v in grille.saison(bars).items()}}
        lignes.append({"actif": code, "role": role, **p})
        print(f"{code:6s} {p['barres']:>7} barres, {p['debut'][:10]} → {p['fin'][:10]}", flush=True)
    for ligne in lignes:
        ligne.update({f"btc_{k}": v for k, v in grille.independance(quot[ligne["actif"]], quot["BTC"]).items()})
    df = pd.DataFrame(lignes)
    df.to_csv(HERE / "grille_D05_1.csv", index=False, lineterminator="\n", float_format="%.6g")
    meta = {"cadrage": __doc__, "debut": str(DEBUT), "creux": [str(x) for x in CREUX],
            "repere_gaussien_pour_mille": {k: grille.repere_gaussien(k) for k in grille.SEUILS}, "actifs": details}
    (HERE / "grille_D05_1.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
    cols = ["actif", "atr_bps_p50", "plafond_r20", "pour_mille_10", "par_an_10", "par_an_15", "haut_10", "bas_10",
            "calme_tous", "calme_grands", "expansion_p90", "saut_pour_mille_3", "plus_gros_pas_grands", "part_gaps",
            "vr_6", "vr_26", "efficacite_p50", "saison_max_min", "heures_par_semaine", "fenetres_coupees",
            "gaps_4atr_par_an", "btc_corr_abs", "btc_jours_extremes_communs", "creux_grands_ratio"]
    with pd.option_context("display.width", 250, "display.max_columns", 40):
        print(df[cols].round(3).to_string(index=False))


def correction_horaire() -> None:
    lignes = []
    for code, (role, _, csv) in ACTIFS.items():
        _, bars = load_asset(csv)
        bars = bars[bars.time >= DEBUT].reset_index(drop=True)
        lignes.append({"actif": code, "role": role,
                       **grille.profil_saison(bars, fuseau=FUSEAUX[code], jours=JOURS_SAISON)})
        print(f"{code:6s} fait", flush=True)
    df = pd.DataFrame(lignes)
    df.to_csv(HERE / "grille_saison_D05_1.csv", index=False, lineterminator="\n", float_format="%.6g")
    cols = ["actif", "fenetres_s", "brut_pour_mille_10", "s_pour_mille_10", "brut_par_an_15", "s_par_an_15",
            "brut_par_an_20", "s_par_an_20", "s_haut_pour_mille_10", "s_bas_pour_mille_10", "brut_ecart_type", "s_ecart_type", "fac_p01",
            "fac_p99", "atr_s_sur_atr_p50"]
    with pd.option_context("display.width", 250, "display.max_columns", 30):
        print(df[cols].round(3).to_string(index=False))


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--calcul", action="store_true")
    g.add_argument("--saison", action="store_true")
    a = p.parse_args()
    calcul() if a.calcul else correction_horaire()


if __name__ == "__main__":
    main()
