"""EXP-D05.5 — phase financée : valeur d'une tentative de challenge FTMO, RE-1 version finale sur les six actifs. GO du
porteur du 2026-10-05 (« GO pour modéliser la valeur d'une tentative (EV) »), règles FTMO standard confirmées par le
porteur.

Usage, depuis la racine du dépôt : python experiments/D05_5/run_D05_5.py --calcul | --rapport

Cadrage (fixé avant le calcul ; lecture sans seuil de décision)
- QUESTION : que vaut une tentative de challenge (100 000 ; 540 € payés, remboursés au premier retrait), une fois le
  compte financé (80 % des gains pour le porteur, retrait tous les 14 jours, perte totale 10 % statique, perte du jour
  5 %), selon le risque par trade r ?
- DONNÉES : trades de D04.1 (six actifs, entrées du 2021-10-01 au 2026-10-01 exclu ; réserve levée par
  `reserve.levee`) ; frais 5 bps (or 4 bps) ; swaps non modélisés.
- MÉTHODE : `propfirm`. Challenge : celui de D05.4 (lecture principale : marge 1:2 plafonnée, borne pessimiste, perte du
  jour depuis le solde de minuit). Compte financé : il démarre au minuit qui suit la réussite de P2, compte neuf, mêmes
  règles de perte et de marge, sans objectif ; tous les 14 jours à minuit, retrait de min(solde, équité) − 1 s'il est
  positif (positions gardées) ; il s'arrête à sa première rupture de règle. Valeur d'une tentative = − 540 € + (540 € +
  80 % des retraits) si au moins un retrait a lieu. Même r en challenge et en compte financé : r ∈ {0,05 ; 0,10 ;
  0,15 ; 0,20 ; 0,25} %/ATR. Horizons : 12 et 24 mois depuis le départ du challenge (départs suivis assez longtemps) ;
  « sans 2026 » : événements après le 2025-12-31 non observés, horizon 12 mois.
- CRITÈRE DE LECTURE (sans seuil) : valeur moyenne d'une tentative (€ et % du compte) avec IC à 95 % par blocs de mois
  de départ ; part des tentatives qui touchent au moins un retrait ; reçu moyen par compte financé ; comptes financés :
  durée de vie, part perdue en 12 mois, retraits en 12 mois. La cible du porteur (délai médian de P1 + P2 entre 90 et
  180 jours, réussite d'au moins 60 à 65 %) est lue en D05.6.
- Conventions : 540 € = 0,54 % du compte (même devise) ; le délai d'ouverture du compte financé par la firme est ignoré.
- Contrôle bloquant : pour chaque r, le challenge redonne D05.4 (part de réussite, délai médian).
- Biais : données déjà lues ; 2026 très favorable ; départs chevauchants. Lecture descriptive.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
import time
import warnings
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "src"))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

spec = importlib.util.spec_from_file_location("run_D05_4", ROOT / "experiments" / "D05_4" / "run_D05_4.py")
D054 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(D054)
D041, D04, D02, D01 = D054.D041, D054.D04, D054.D02, D054.D01

from propfirm import (FTMO_SWING, INF, LEVIER_FTMO_SWING, Regles, challenge, departs_minuit, financement,  # noqa: E402
                      ic_blocs, resume, simuler, valeur)
from reserve import levee  # noqa: E402

FIG = HERE / "figures"
MOTIF = "EXP-D05.5 (porteur, 2026-10-05)"
A, B = D054.A, D054.B
FIN = pd.Timestamp(B, tz="UTC")                         # fin des données
RISKS = D054.RISKS
COMPTE, FRAIS_EUR, PART, RETRAIT_JOURS = 100_000.0, 540.0, 0.80, 14
FRAIS = FRAIS_EUR / COMPTE
FINANCE = Regles(objectifs=(), perte_jour=FTMO_SWING.perte_jour, perte_max=FTMO_SWING.perte_max,
                 jours_min=FTMO_SWING.jours_min, fuseau=FTMO_SWING.fuseau)
LECTURES = (("12 mois", 365, None), ("24 mois", 730, None), ("sans 2026, 12 mois", 365, D054.COUPURE))


def stop(msg: str):
    raise SystemExit(f"D05.5, contrôle bloquant : {msg} : arrêt")


def suivis(out: pd.DataFrame, horizon: float, coupure: int | None) -> pd.DataFrame:
    """Départs suivis au moins `horizon` jours avant la fin des données (ou la coupure)."""
    fin = FIN if coupure is None else pd.Timestamp(coupure, tz="UTC")
    return out[out.depart + pd.Timedelta(days=horizon) <= fin].reset_index(drop=True)


def resume_valeur(v: pd.DataFrame, horizon: float) -> dict:
    """Valeur moyenne et IC ; part des tentatives financées dans l'horizon, et avec au moins un retrait ; reçu moyen et
    nombre de retraits des comptes financés dans l'horizon."""
    lo, hi = ic_blocs(v.valeur.to_numpy(), v.depart)
    dans = v.finance & (v.jours_total <= horizon)
    fin = v[dans]
    return {"n_departs": len(v), "valeur": float(v.valeur.mean()), "valeur_ic_bas": lo, "valeur_ic_haut": hi,
            "p_finance": float(dans.mean()), "p_retrait": float((v.n_retraits > 0).mean()),
            "recu_moyen_finance": float(fin.recu.mean()) if len(fin) else np.nan,
            "retraits_moyens_finance": float(fin.n_retraits.mean()) if len(fin) else np.nan}


def comptes_finances(sim_f, horizon: float = 365.0) -> dict:
    """Comptes financés démarrés à chaque minuit et suivis `horizon` jours : part perdue dans l'horizon, durée de vie
    médiane des comptes perdus (à tout moment), retraits dans l'horizon."""
    fa = financement(sim_f)
    m = (fa.depart + pd.Timedelta(days=horizon) <= FIN).to_numpy()
    d, fin, jours = sim_f.departs, fa.fin.to_numpy(), fa.jours.to_numpy()
    rd, rt, rm = (sim_f.retraits[c].to_numpy() for c in ("depart", "t", "montant"))
    keep = (rt < fin[rd]) & (rt <= d[rd] + int(horizon * 86_400 * 10**9))
    som = np.zeros(len(d))
    np.add.at(som, rd[keep], rm[keep])
    return {"comptes": int(m.sum()), "p_perdu_12m": float(np.mean(jours[m] <= horizon)),
            "duree_mediane_perdus": float(np.nanmedian(jours[m])), "retire_moyen_12m": float(som[m].mean()),
            "recu_moyen_12m_eur": float(PART * som[m].mean() * COMPTE)}


def run_calcul() -> None:
    t0 = time.time()
    ctrl = {"date": pd.Timestamp.now(tz="UTC").strftime("%Y-%m-%d %H:%M UTC"), "commit": D04.git_head(), "motif": MOTIF}
    d054 = pd.read_csv(ROOT / "experiments" / "D05_4" / "resultats_D05_4.csv", dtype={"annee": str})
    d054 = D054._sel(d054)
    rows, fin_rows, per = [], [], []
    with levee(MOTIF):
        assets = D041.load_all()
        departs = departs_minuit(A, B, FTMO_SWING.fuseau)
        for risk in RISKS:
            lg = D054.legs(assets, risk)
            sim_c = simuler(lg, departs, levier=LEVIER_FTMO_SWING, plafonner=True)
            ch = resume(challenge(sim_c))
            ref = d054[d054.risque_bps == risk].iloc[0]
            if not (np.isclose(ch["p_reussite"], ref.p_reussite, rtol=1e-5)          # CSV de D05.4 à 6 chiffres
                    and np.isclose(ch["jours_total_med"], ref.jours_total_med, rtol=1e-5)):
                stop(f"risque {risk:g} bps : le challenge ne redonne pas D05.4")
            ctrl[f"challenge_egal_D05_4_r{risk:g}"] = {"p_reussite": round(ch["p_reussite"], 6),
                                                       "jours_total_med": round(ch["jours_total_med"], 3)}
            sim_f = simuler(lg, departs, FINANCE, levier=LEVIER_FTMO_SWING, plafonner=True,
                            retrait_jours=RETRAIT_JOURS)
            for nom, h, coup in LECTURES:
                v = suivis(valeur(sim_c, sim_f, frais=FRAIS, part=PART, horizon_jours=h, coupure=coup), h, coup)
                c = suivis(challenge(sim_c, coupure=coup), h, coup)
                rows.append({"risque_bps": risk, "lecture": nom, **resume_valeur(v, h),
                             **{f"challenge_{k}": x for k, x in resume(c).items()}})
                if nom == "12 mois":
                    per.append(v.assign(risque_bps=risk))
            fin_rows.append({"risque_bps": risk, **comptes_finances(sim_f)})
            print(f"risque {risk:g} bps : fait ({time.time() - t0:.0f} s)", flush=True)
    pd.DataFrame(rows).to_csv(HERE / "resultats_D05_5.csv", index=False, float_format="%.6g")
    pd.DataFrame(fin_rows).to_csv(HERE / "comptes_finances_D05_5.csv", index=False, float_format="%.6g")
    sd = pd.concat(per, ignore_index=True)
    sd["depart"] = sd.depart.dt.strftime("%Y-%m-%d")
    sd.to_csv(HERE / "departs_D05_5.csv.gz", index=False, float_format="%.6g")
    ctrl["duree_s"] = round(time.time() - t0)
    (HERE / "controles_D05_5.json").write_text(json.dumps(D01.jsonable(ctrl), ensure_ascii=False, indent=1),
                                               encoding="utf-8")
    figures()
    write_rapport()
    print(f"D05.5 : fait en {ctrl['duree_s']} s ; sorties dans {HERE}")


def figures() -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    res = pd.read_csv(HERE / "resultats_D05_5.csv")
    FIG.mkdir(parents=True, exist_ok=True)
    ink, muted, grid = "#0b0b0b", "#52514e", "#e4e3df"
    fig, ax = plt.subplots(figsize=(9, 5.6))
    styles = {"12 mois": ("o-", "#2a78d6"), "24 mois": ("s-", "#eb6834"), "sans 2026, 12 mois": ("^--", "#1baf7a")}
    for nom, (mk, col) in styles.items():
        s = res[res.lecture == nom].sort_values("risque_bps")
        x = s.risque_bps / 100
        ax.plot(x, s.valeur * COMPTE, mk, color=col, lw=2, ms=7, label=nom)
        ax.fill_between(x, s.valeur_ic_bas * COMPTE, s.valeur_ic_haut * COMPTE, color=col, alpha=0.12, lw=0)
    ax.axhline(0, color=muted, lw=1)
    ax.set_xlabel("risque par trade (% du capital par ATR14)", color=muted)
    ax.set_ylabel("valeur moyenne d'une tentative (€, compte de 100 000)", color=muted)
    ax.set_title("Valeur d'une tentative de challenge FTMO (IC à 95 % par blocs de mois)", fontsize=10, color=ink)
    ax.legend(fontsize=8, loc="upper center", bbox_to_anchor=(0.5, -0.13), ncol=3, frameon=False)
    ax.grid(color=grid, lw=0.8)
    ax.set_axisbelow(True)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    fig.tight_layout()
    fig.savefig(FIG / "D05_5_valeur.png", dpi=110)
    plt.close(fig)


fr, sg, pct, spct, n_fr, table = D01.fr, D01.sg, D01.pct, D01.spct, D01.n_fr, D01.table


def eur(x) -> str:
    return "—" if pd.isna(x) else f"{x * COMPTE:+,.0f} €".replace(",", " ").replace("-", "−")


def write_rapport() -> None:
    res = pd.read_csv(HERE / "resultats_D05_5.csv")
    fin = pd.read_csv(HERE / "comptes_finances_D05_5.csv")
    ct = json.loads((HERE / "controles_D05_5.json").read_text(encoding="utf-8"))
    narr = HERE / "narratif_D05_5.md"
    out = [narr.read_text(encoding="utf-8") if narr.exists() else "# EXP-D05.5 — rapport (narratif à rédiger)\n",
           "", "---", "", "# Annexes générées (`run_D05_5.py --calcul`, puis `--rapport`)", "",
           f"Calcul du {ct['date']}, commit `{ct['commit']}`, {ct['duree_s']} s.", "", "## A1. Contrôle bloquant (passé)", ""]
    out += [f"- {k} : {json.dumps(v, ensure_ascii=False)}." for k, v in ct.items()
            if k not in ("date", "commit", "duree_s", "motif")]
    for nom in ("12 mois", "24 mois", "sans 2026, 12 mois"):
        s = res[res.lecture == nom].sort_values("risque_bps")
        out += ["", f"## A2. Valeur d'une tentative, {nom} ({int(s.n_departs.iat[0])} départs suivis assez longtemps)", "",
                table(["r (%/ATR)", "Valeur moyenne [IC 95 %]", "Financées dans l'horizon",
                       "Tentatives avec ≥ 1 retrait (valeur > 0)", "Reçu moyen par compte financé ; retraits",
                       "Réussite P1 + P2, sans limite de temps ; délai médian (mêmes départs)"],
                      [[fr(x.risque_bps / 100, 2), f"{eur(x.valeur)} [{eur(x.valeur_ic_bas)} ; {eur(x.valeur_ic_haut)}]",
                        pct(x.p_finance, 1), pct(x.p_retrait, 1),
                        f"{eur(x.recu_moyen_finance)} ; {fr(x.retraits_moyens_finance, 1)}",
                        f"{pct(x.challenge_p_reussite, 1)} ; {fr(x.challenge_jours_total_med, 0)} j"]
                       for _, x in s.iterrows()])]
    out += ["", "## A3. Comptes financés démarrés à chaque minuit, suivis 12 mois", "",
            table(["r (%/ATR)", "Comptes", "Perdus en 12 mois", "Durée médiane des comptes perdus",
                   "Retiré moyen en 12 mois (avant le partage) ; reçu (80 %)"],
                  [[fr(x.risque_bps / 100, 2), n_fr(x.comptes), pct(x.p_perdu_12m, 1),
                    f"{fr(x.duree_mediane_perdus, 0)} j", f"{pct(x.retire_moyen_12m, 2)} ; {fr(x.recu_moyen_12m_eur, 0)} €"]
                   for _, x in fin.sort_values("risque_bps").iterrows()]),
            "", "## A4. Figure", "", "![Valeur](figures/D05_5_valeur.png)", ""]
    (HERE / "rapport_D05_5.md").write_text("\n".join(out) + "\n", encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--calcul", action="store_true")
    g.add_argument("--rapport", action="store_true")
    args = ap.parse_args()
    warnings.simplefilter("ignore")
    if args.calcul:
        run_calcul()
    else:
        figures()
        write_rapport()


if __name__ == "__main__":
    main()
