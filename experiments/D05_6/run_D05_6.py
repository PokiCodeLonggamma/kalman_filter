"""EXP-D05.6 — taille selon l'état du compte (variantes du porteur) contre un risque fixe : challenge FTMO et valeur
d'une tentative, RE-1 version finale sur les six actifs. GO du porteur du 2026-10-05 (variantes A, B et C, « une à la
fois, comparées à un r fixe »).

Usage, depuis la racine du dépôt : python experiments/D05_6/run_D05_6.py --calcul | --rapport

Cadrage (fixé avant le calcul ; lecture sans seuil de décision, sauf la cible écrite par le porteur)
- QUESTION : les variantes A (frein), B (sprint) et C (coussin) font-elles mieux qu'un risque fixe, en réussite et en
  délai du challenge, et en valeur d'une tentative ?
- DONNÉES : celles de D05.4 et D05.5 (trades de D04.1, six actifs, 2021-10 → 2026-09 ; frais 5 bps, or 4 bps).
- MÉTHODE : `propfirm.simuler` avec une taille selon l'état du compte ; poids = min(1, risque / ATR14 du trade).
  - Référence : risque fixe r ∈ {0,05 ; 0,10 ; 0,15 ; 0,20 ; 0,25} %/ATR (frontière).
  - A, frein : 0,20 %/ATR ; 0,10 % quand le capital valorisé tombe à −5 % ; 0,20 % de nouveau au-dessus de −2 %.
  - B, sprint : 0,10 %/ATR ; 0,20 % quand le capital valorisé atteint +3 % ; 0,10 % de nouveau sous +1 %.
  - C, coussin : risque proportionnel à la distance au plancher de −10 %, r0 à capital 1 ; r0 ∈ {0,10 ; 0,15 ; 0,20 ;
    0,25} %/ATR.
  Seuils sur le capital valorisé de chaque compte (challenge P1, P2, compte financé), relatif à son solde initial ;
  même règle en challenge et en compte financé. Lecture principale de D05.4 (marge 1:2 plafonnée, borne pessimiste,
  perte du jour depuis le solde de minuit) ; compte financé et valeur de D05.5 (80 %, retraits tous les 14 jours,
  540 € remboursés au premier retrait).
- CRITÈRE DE LECTURE : réussite P1 + P2 [IC 95 %], causes d'échec, délai médian et P90, sur tous les départs et sans
  2026 ; écart à la frontière du risque fixe au même délai médian (interpolation linéaire entre deux r fixes) ; cible
  du porteur (délai médian de P1 + P2 entre 90 et 180 jours, réussite d'au moins 60 à 65 %) ; valeur d'une tentative à
  12 mois [IC 95 %], et sans 2026.
- Contrôle bloquant : chaque risque fixe redonne D05.4 (réussite, délai médian) et D05.5 (valeur à 12 mois, avec et
  sans 2026).
- Biais : données déjà lues ; 2026 très favorable ; départs chevauchants ; seuils des variantes fixés par le porteur
  après lecture de D05.4. Lecture descriptive.
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

spec = importlib.util.spec_from_file_location("run_D05_5", ROOT / "experiments" / "D05_5" / "run_D05_5.py")
D055 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(D055)
D054, D041, D04, D02, D01 = D055.D054, D055.D041, D055.D04, D055.D02, D055.D01

from propfirm import (FTMO_SWING, LEVIER_FTMO_SWING, Coussin, Fixe, Frein, Sprint, challenge,  # noqa: E402
                      departs_minuit, resume, simuler, valeur)
from reserve import levee  # noqa: E402

FIG = HERE / "figures"
MOTIF = "EXP-D05.6 (porteur, 2026-10-05)"
A, B = D054.A, D054.B
RISKS = D054.RISKS
FENETRES = (("toute", None), ("sans_2026", D054.COUPURE))
CIBLE = (90.0, 180.0)
CONFIGS = ([("fixe", f"r fixe {r / 100:.2f}", Fixe(r)) for r in RISKS]
           + [("A", "A · frein 0,20 → 0,10", Frein(haut=20.0, bas=10.0, seuil=0.95, retour=0.98)),
              ("B", "B · sprint 0,10 → 0,20", Sprint(bas=10.0, haut=20.0, seuil=1.03, retour=1.01))]
           + [("C", f"C · coussin r0 {r0 / 100:.2f}", Coussin(r0)) for r0 in (10.0, 15.0, 20.0, 25.0)])


def stop(msg: str):
    raise SystemExit(f"D05.6, contrôle bloquant : {msg} : arrêt")


def run_calcul() -> None:
    t0 = time.time()
    ctrl = {"date": pd.Timestamp.now(tz="UTC").strftime("%Y-%m-%d %H:%M UTC"), "commit": D04.git_head(), "motif": MOTIF}
    d054 = D054._sel(pd.read_csv(ROOT / "experiments" / "D05_4" / "resultats_D05_4.csv", dtype={"annee": str}))
    d055 = pd.read_csv(ROOT / "experiments" / "D05_5" / "resultats_D05_5.csv")
    rows = []
    with levee(MOTIF):
        assets = D041.load_all()
        departs = departs_minuit(A, B, FTMO_SWING.fuseau)
        lg = D054.legs(assets, 25.0)                         # poids des jambes inutilisés : la taille les remplace
        atr = [assets[leg.name]["atr_bps"][leg.trades.signal_bar.to_numpy()] for leg in lg]
        for famille, nom, taille in CONFIGS:
            sim_c = simuler(lg, departs, levier=LEVIER_FTMO_SWING, plafonner=True, taille=taille, atr=atr)
            sim_f = simuler(lg, departs, D055.FINANCE, levier=LEVIER_FTMO_SWING, plafonner=True, taille=taille, atr=atr,
                            retrait_jours=D055.RETRAIT_JOURS)
            for fen, coup in FENETRES:
                rc = resume(challenge(sim_c, coupure=coup))
                v = D055.suivis(valeur(sim_c, sim_f, frais=D055.FRAIS, part=D055.PART, horizon_jours=365, coupure=coup),
                                365, coup)
                rv = D055.resume_valeur(v, 365)
                rows.append({"famille": famille, "configuration": nom, "fenetre": fen, **rc,
                             **{f"v_{k}": x for k, x in rv.items()}})
                if famille == "fixe":
                    r = taille.r
                    ref5 = d055[(d055.risque_bps == r) & (d055.lecture == ("12 mois" if coup is None
                                                                          else "sans 2026, 12 mois"))].iloc[0]
                    ok = np.isclose(rv["valeur"], ref5.valeur, rtol=1e-5)
                    if coup is None:
                        ref4 = d054[d054.risque_bps == r].iloc[0]
                        ok &= np.isclose(rc["p_reussite"], ref4.p_reussite, rtol=1e-5) and np.isclose(
                            rc["jours_total_med"], ref4.jours_total_med, rtol=1e-5)
                    if not ok:
                        stop(f"{nom}, {fen} : ne redonne pas D05.4 et D05.5")
                    ctrl[f"{nom}_{fen}_egal_D05_4_D05_5"] = {"p_reussite": round(rc["p_reussite"], 6),
                                                              "valeur_12m": round(rv["valeur"], 6)}
            print(f"{nom} : fait ({time.time() - t0:.0f} s)", flush=True)
    res = frontiere(pd.DataFrame(rows))
    res.to_csv(HERE / "resultats_D05_6.csv", index=False, float_format="%.6g")
    ctrl["duree_s"] = round(time.time() - t0)
    (HERE / "controles_D05_6.json").write_text(json.dumps(D01.jsonable(ctrl), ensure_ascii=False, indent=1),
                                               encoding="utf-8")
    figures()
    write_rapport()
    print(f"D05.6 : fait en {ctrl['duree_s']} s ; sorties dans {HERE}")


def frontiere(res: pd.DataFrame) -> pd.DataFrame:
    """Réussite et valeur du risque fixe au même délai médian (interpolation linéaire entre deux r fixes ; hors de la
    plage des r fixes : vide) ; cible du porteur."""
    out = []
    for fen, g in res.groupby("fenetre", sort=False):
        f = g[g.famille == "fixe"].sort_values("jours_total_med")
        x = f.jours_total_med.to_numpy()
        g = g.copy()
        g["p_fixe_meme_delai"] = np.interp(g.jours_total_med, x, f.p_reussite, left=np.nan, right=np.nan)
        g["v_fixe_meme_delai"] = np.interp(g.jours_total_med, x, f.v_valeur, left=np.nan, right=np.nan)
        out.append(g)
    res = pd.concat(out, ignore_index=True)
    dans = res.jours_total_med.between(*CIBLE)
    res["cible"] = np.where(dans & (res.p_reussite >= 0.65), "oui (≥ 65 %)",
                            np.where(dans & (res.p_reussite >= 0.60), "oui (≥ 60 %)", "non"))
    return res


def figures() -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    res = pd.read_csv(HERE / "resultats_D05_6.csv")
    FIG.mkdir(parents=True, exist_ok=True)
    ink, muted, grid = "#0b0b0b", "#52514e", "#e4e3df"
    fig, axes = plt.subplots(1, 2, figsize=(15, 6.2))
    g = res[res.fenetre == "toute"]
    styles = {"fixe": ("o-", "#52514e", "risque fixe (0,05 à 0,25)"), "C": ("s-", "#2a78d6", "C · coussin (r0 0,10 à 0,25)"),
              "A": ("D", "#eb6834", "A · frein"), "B": ("^", "#1baf7a", "B · sprint")}
    for ax, col, titre in ((axes[0], "p_reussite", "Réussite P1 + P2 (% des départs)"),
                           (axes[1], "v_valeur", "Valeur d'une tentative à 12 mois (€)")):
        scale = 100 if col == "p_reussite" else D055.COMPTE
        if col == "p_reussite":
            ax.axvspan(*CIBLE, color="#2a78d6", alpha=0.06, lw=0)
            ax.axhline(60, color=muted, lw=0.8, ls=":")
        for fam, (mk, c, lab) in styles.items():
            s = g[g.famille == fam].sort_values("jours_total_med")
            ax.plot(s.jours_total_med, scale * s[col], mk, color=c, lw=1.8, ms=8, label=lab)
            if fam in ("fixe", "C"):
                for _, x in s.iterrows():
                    ax.annotate(x.configuration.split()[-1], (x.jours_total_med, scale * x[col]), fontsize=7,
                                color=muted, xytext=(4, 4), textcoords="offset points")
        ax.set_xscale("log")
        ticks = [30, 50, 100, 200, 500, 1000]
        ax.set_xticks(ticks, [str(t) for t in ticks])
        ax.minorticks_off()
        ax.set_xlabel("délai médian de P1 + P2 (jours, échelle logarithmique)", color=muted)
        ax.set_title(titre + " ; zone bleue : délai visé par le porteur" if col == "p_reussite" else titre,
                     fontsize=10, color=ink)
        ax.grid(color=grid, lw=0.8)
        ax.set_axisbelow(True)
        for sp in ("top", "right"):
            ax.spines[sp].set_visible(False)
        ax.legend(fontsize=8, loc="upper center", bbox_to_anchor=(0.5, -0.13), ncol=4, frameon=False)
    fig.tight_layout()
    fig.savefig(FIG / "D05_6_frontiere.png", dpi=110)
    plt.close(fig)


fr, sg, pct, spct, n_fr, table = D01.fr, D01.sg, D01.pct, D01.spct, D01.n_fr, D01.table
eur = D055.eur


def _p(x) -> str:
    return "—" if pd.isna(x) else pct(x, 1)


def _d(x, y) -> str:
    return "—" if pd.isna(y) else f"{sg(100 * (x - y), 1)} pt"


def write_rapport() -> None:
    res = pd.read_csv(HERE / "resultats_D05_6.csv")
    ct = json.loads((HERE / "controles_D05_6.json").read_text(encoding="utf-8"))
    narr = HERE / "narratif_D05_6.md"
    out = [narr.read_text(encoding="utf-8") if narr.exists() else "# EXP-D05.6 — rapport (narratif à rédiger)\n",
           "", "---", "", "# Annexes générées (`run_D05_6.py --calcul`, puis `--rapport`)", "",
           f"Calcul du {ct['date']}, commit `{ct['commit']}`, {ct['duree_s']} s.", "", "## A1. Contrôle bloquant (passé)", ""]
    out += [f"- {k} : {json.dumps(v, ensure_ascii=False)}." for k, v in ct.items()
            if k not in ("date", "commit", "duree_s", "motif")]
    for fen, titre in (("toute", "tous les départs"), ("sans_2026", "sans 2026")):
        g = res[res.fenetre == fen]
        out += ["", f"## A2. Challenge et valeur, {titre} ({int(g.n_departs.iat[0])} départs ; valeur à 12 mois sur "
                    f"{int(g.v_n_departs.iat[0])} départs)", "",
                table(["Configuration", "Réussite P1 + P2 [IC 95 %]", "Échec : jour ; total", "En cours",
                       "Délai médian ; P90", "Cible du porteur", "Écart au risque fixe au même délai",
                       "Valeur à 12 mois [IC 95 %]", "Écart de valeur au même délai", "≥ 1 retrait en 12 mois"],
                      [[x.configuration, f"{_p(x.p_reussite)} [{_p(x.ic_bas)} ; {_p(x.ic_haut)}]",
                        f"{_p(x.p_echec_p1_jour + x.p_echec_p2_jour)} ; {_p(x.p_echec_p1_max + x.p_echec_p2_max)}",
                        _p(x.p_en_cours_p1 + x.p_en_cours_p2),
                        f"{fr(x.jours_total_med, 0)} ; {fr(x.jours_total_p90, 0)} j", x.cible,
                        "—" if x.famille == "fixe" else _d(x.p_reussite, x.p_fixe_meme_delai),
                        f"{eur(x.v_valeur)} [{eur(x.v_valeur_ic_bas)} ; {eur(x.v_valeur_ic_haut)}]",
                        "—" if x.famille == "fixe" or pd.isna(x.v_fixe_meme_delai) else eur(x.v_valeur - x.v_fixe_meme_delai),
                        _p(x.v_p_retrait)]
                       for _, x in g.iterrows()])]
    out += ["", "## A3. Figure", "", "![Frontière](figures/D05_6_frontiere.png)", ""]
    (HERE / "rapport_D05_6.md").write_text("\n".join(out) + "\n", encoding="utf-8")


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
