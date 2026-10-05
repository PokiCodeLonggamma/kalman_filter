"""EXP-D05.6bis — une taille propre à chaque phase (« hybride ») : challenge FTMO et compte financé avec deux tailles,
valeur d'une tentative et d'une suite de tentatives, RE-1 version finale sur les six actifs. GO du porteur du 2026-10-05
(combos A et B ; mesures propres : « si oui, ajoute-les à ce run »).

Usage, depuis la racine du dépôt : python experiments/D05_6bis/run_D05_6bis.py --calcul | --rapport

Cadrage (fixé avant le calcul ; lecture sans seuil de décision)
- QUESTION : une taille propre à chaque phase bat-elle le risque fixe 0,20 %/ATR dans les deux phases (+9 218 € par
  tentative à 12 mois, D05.5) ?
- DONNÉES : celles de D05.4 à D05.6 (trades de D04.1, six actifs, 2021-10 → 2026-09 ; frais 5 bps, or 4 bps).
- MÉTHODE : une simulation de challenge par taille de challenge, une simulation de compte financé par taille de compte
  financé ; `valeur` et `suite` combinent les deux (7 × 7 combinaisons).
  - Challenge : risque fixe 0,10, 0,15, 0,20, 0,25, 0,30 %/ATR ; coussin r0 0,15 et 0,20.
  - Compte financé : risque fixe 0,10, 0,15, 0,20, 0,25, 0,30 ; coussin r0 0,20 ; relance (0,20 ; 0,40 quand le
    capital valorisé tombe à −5 % ; 0,20 de nouveau au-dessus de −2 % : le miroir du frein A).
  - 0,30 (dans les deux phases) ajouté après un premier calcul : en suite de tentatives, le meilleur r y était au bord
    de la grille (0,25).
  - Combos du porteur : A = coussin r0 0,15 ou 0,20 en challenge, fixe 0,20 ou 0,25 en compte financé ; B = fixe 0,15
    en challenge, fixe 0,20 ou 0,25 en compte financé. Le reste est l'exploration autorisée par le porteur.
  - Valeur d'une tentative (D05.5). Suite de tentatives : un seul compte à la fois, nouvelle tentative (540 €) au
    minuit qui suit chaque échec du challenge ou chaque perte du compte financé.
  - Lecture principale de D05.4 (marge 1:2 plafonnée, borne pessimiste, perte du jour depuis le solde de minuit) ;
    compte financé de D05.5 (80 %, retraits tous les 14 jours, 540 € remboursés au premier retrait).
- CRITÈRE DE LECTURE : valeur moyenne [IC 95 %] à 12 et 24 mois, et sans 2026 (12 mois), pour la tentative et pour la
  suite ; écart apparié à la référence (fixe 0,20 dans les deux phases), IC 95 % par blocs de mois de départ ;
  challenge : réussite, délai médian (objectif du porteur : moins de 120 jours) et P90, en cours ; compte financé :
  part perdue, durée de vie, retraits. Queues : médiane, P10 et P90 par départ ; part des départs où la combinaison
  fait mieux ou moins bien que la référence ; écart moyen par année de départ.
- Contrôle bloquant : (fixe r, fixe r) redonne D05.5 (valeur à 12 mois, 24 mois, sans 2026) pour r ∈ {0,10 ; 0,15 ;
  0,20 ; 0,25} ; (coussin 0,20, coussin 0,20) redonne D05.6 (valeur à 12 mois, deux fenêtres) ; chaque taille de
  challenge redonne la réussite et le délai médian de D05.6.
- Biais : données déjà lues ; 2026 très favorable ; départs chevauchants ; 49 combinaisons : la meilleure est optimiste
  (choisie sur les mêmes données) ; seuils de la relance repris du frein du porteur. Lecture descriptive.
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
D054, D041, D04, D01 = D055.D054, D055.D041, D055.D04, D055.D01

from propfirm import (FTMO_SWING, LEVIER_FTMO_SWING, Coussin, Fixe, Frein, challenge, departs_minuit,  # noqa: E402
                      ic_blocs, resume, simuler, suite, valeur)
from reserve import levee  # noqa: E402

FIG = HERE / "figures"
MOTIF = "EXP-D05.6bis (porteur, 2026-10-05)"
A, B = D054.A, D054.B
FENETRES = (("toute", None), ("sans_2026", D054.COUPURE))
LECTURES = D055.LECTURES                                 # 12 mois, 24 mois, sans 2026 (12 mois)
MESURES = ("tentative", "suite")
DELAI_PORTEUR = 120.0
CHALLENGE = (("fixe 0,10", Fixe(10.0)), ("fixe 0,15", Fixe(15.0)), ("fixe 0,20", Fixe(20.0)),
             ("fixe 0,25", Fixe(25.0)), ("fixe 0,30", Fixe(30.0)), ("coussin 0,15", Coussin(15.0)),
             ("coussin 0,20", Coussin(20.0)))
FINANCE = (("fixe 0,10", Fixe(10.0)), ("fixe 0,15", Fixe(15.0)), ("fixe 0,20", Fixe(20.0)), ("fixe 0,25", Fixe(25.0)),
           ("fixe 0,30", Fixe(30.0)), ("coussin 0,20", Coussin(20.0)),
           ("relance 0,20 → 0,40", Frein(haut=20.0, bas=40.0, seuil=0.95, retour=0.98)))
REF = ("fixe 0,20", "fixe 0,20")
PORTEUR = {("coussin 0,15", "fixe 0,20"): "A", ("coussin 0,15", "fixe 0,25"): "A",
           ("coussin 0,20", "fixe 0,20"): "A", ("coussin 0,20", "fixe 0,25"): "A",
           ("fixe 0,15", "fixe 0,20"): "B", ("fixe 0,15", "fixe 0,25"): "B"}
SELECTION = [REF, ("fixe 0,15", "fixe 0,20"), ("fixe 0,15", "fixe 0,25"), ("coussin 0,15", "fixe 0,20"),
             ("coussin 0,20", "fixe 0,20"), ("fixe 0,20", "fixe 0,25"), ("fixe 0,20", "fixe 0,30"),
             ("fixe 0,20", "relance 0,20 → 0,40"), ("fixe 0,25", "fixe 0,25"), ("fixe 0,25", "relance 0,20 → 0,40"),
             ("fixe 0,30", "fixe 0,30"), ("fixe 0,30", "relance 0,20 → 0,40")]    # affichage des annexes A5-A6
NOM_D056 = {"fixe 0,10": "r fixe 0.10", "fixe 0,15": "r fixe 0.15", "fixe 0,20": "r fixe 0.20",
            "fixe 0,25": "r fixe 0.25", "coussin 0,15": "C · coussin r0 0.15", "coussin 0,20": "C · coussin r0 0.20"}


def stop(msg: str):
    raise SystemExit(f"D05.6bis, contrôle bloquant : {msg} : arrêt")


def run_calcul() -> None:
    t0 = time.time()
    ctrl = {"date": pd.Timestamp.now(tz="UTC").strftime("%Y-%m-%d %H:%M UTC"), "commit": D04.git_head(), "motif": MOTIF}
    d055 = pd.read_csv(ROOT / "experiments" / "D05_5" / "resultats_D05_5.csv")
    d056 = pd.read_csv(ROOT / "experiments" / "D05_6" / "resultats_D05_6.csv")
    with levee(MOTIF):
        assets = D041.load_all()
        departs = departs_minuit(A, B, FTMO_SWING.fuseau)
        lg = D054.legs(assets, 25.0)                         # poids des jambes inutilisés : la taille les remplace
        atr = [assets[leg.name]["atr_bps"][leg.trades.signal_bar.to_numpy()] for leg in lg]
        opts = dict(levier=LEVIER_FTMO_SWING, plafonner=True, atr=atr)
        sims_c = {nom: simuler(lg, departs, taille=t, **opts) for nom, t in CHALLENGE}
        print(f"challenges simulés ({time.time() - t0:.0f} s)", flush=True)
        sims_f = {nom: simuler(lg, departs, D055.FINANCE, taille=t, retrait_jours=D055.RETRAIT_JOURS, **opts)
                  for nom, t in FINANCE}
        print(f"comptes financés simulés ({time.time() - t0:.0f} s)", flush=True)
    ch_rows = []
    for nom, sim in sims_c.items():
        for fen, coup in FENETRES:
            rc = resume(challenge(sim, coupure=coup))
            if nom in NOM_D056:                              # 0,30 : absent de D05.6
                ref6 = d056[(d056.configuration == NOM_D056[nom]) & (d056.fenetre == fen)].iloc[0]
                if not (np.isclose(rc["p_reussite"], ref6.p_reussite, rtol=1e-5)
                        and np.isclose(rc["jours_total_med"], ref6.jours_total_med, rtol=1e-5)):
                    stop(f"challenge {nom}, {fen} : ne redonne pas D05.6")
                ctrl["challenges_egaux_D05_6"] = ctrl.get("challenges_egaux_D05_6", 0) + 1
            ch_rows.append({"challenge": nom, "fenetre": fen, **rc})
    fi_rows = []
    for nom, sim in sims_f.items():
        for h in (365.0, 730.0):
            cf = D055.comptes_finances(sim, h)
            fi_rows.append({"finance": nom, "horizon_jours": h, "comptes": cf["comptes"], "p_perdu": cf["p_perdu_12m"],
                            "duree_mediane_perdus": cf["duree_mediane_perdus"], "retire_moyen": cf["retire_moyen_12m"],
                            "recu_moyen_eur": cf["recu_moyen_12m_eur"]})
    per = {}
    for cn, sc in sims_c.items():
        for fn, sf in sims_f.items():
            for lect, h, coup in LECTURES:
                kw = dict(frais=D055.FRAIS, part=D055.PART, horizon_jours=h, coupure=coup)
                per[(cn, fn, lect, "tentative")] = D055.suivis(valeur(sc, sf, **kw), h, coup)
                per[(cn, fn, lect, "suite")] = D055.suivis(suite(sc, sf, **kw), h, coup)
        print(f"challenge {cn} : combinaisons faites ({time.time() - t0:.0f} s)", flush=True)
    rows, annees = [], []
    for (cn, fn, lect, mes), df in per.items():
        ref = per[(*REF, lect, mes)]
        if not df.depart.equals(ref.depart):
            stop(f"{cn} × {fn}, {lect} : départs différents de la référence")
        x, dx = df.valeur.to_numpy(), df.valeur.to_numpy() - ref.valeur.to_numpy()
        lo, hi = ic_blocs(x, df.depart)
        dlo, dhi = ic_blocs(dx, df.depart)
        row = {"challenge": cn, "finance": fn, "lecture": lect, "mesure": mes, "combo": PORTEUR.get((cn, fn), ""),
               "n_departs": len(df), "valeur": float(x.mean()), "ic_bas": lo, "ic_haut": hi,
               "mediane": float(np.median(x)), "p10": float(np.quantile(x, 0.1)), "p90": float(np.quantile(x, 0.9)),
               "ecart_ref": float(dx.mean()), "ecart_ic_bas": dlo, "ecart_ic_haut": dhi,
               "p_mieux": float((dx > 1e-12).mean()), "p_moins": float((dx < -1e-12).mean())}
        an = df.depart.dt.year.to_numpy()
        for a in np.unique(an):
            m = an == a
            annees.append({"challenge": cn, "finance": fn, "lecture": lect, "mesure": mes, "annee": int(a),
                           "n_departs": int(m.sum()), "valeur": float(x[m].mean()), "ecart_ref": float(dx[m].mean())})
        if mes == "tentative":
            row.update(p_retrait=float((df.n_retraits > 0).mean()), retraits_moyens=float(df.n_retraits.mean()))
        else:
            row.update(tentatives=float(df.n_tentatives.mean()), finances=float(df.n_finances.mean()))
        rows.append(row)
    res = pd.DataFrame(rows)
    for r in (10, 15, 20, 25):
        nom = f"fixe 0,{r}"
        for lect, _, _ in LECTURES:
            x = res[(res.challenge == nom) & (res.finance == nom) & (res.lecture == lect) & (res.mesure == "tentative")]
            ref5 = d055[(d055.risque_bps == r) & (d055.lecture == lect)].iloc[0]
            if not np.isclose(x.valeur.iat[0], ref5.valeur, rtol=1e-5):        # CSV de D05.5 à 6 chiffres
                stop(f"{nom} dans les deux phases, {lect} : ne redonne pas D05.5")
            ctrl[f"{nom}_deux_phases_{lect}_egal_D05_5"] = round(float(x.valeur.iat[0]), 6)
    for fen, lect in (("toute", "12 mois"), ("sans_2026", "sans 2026, 12 mois")):
        x = res[(res.challenge == "coussin 0,20") & (res.finance == "coussin 0,20") & (res.lecture == lect)
                & (res.mesure == "tentative")]
        ref6 = d056[(d056.configuration == NOM_D056["coussin 0,20"]) & (d056.fenetre == fen)].iloc[0]
        if not np.isclose(x.valeur.iat[0], ref6.v_valeur, rtol=1e-5):
            stop(f"coussin 0,20 dans les deux phases, {lect} : ne redonne pas D05.6")
        ctrl[f"coussin 0,20_deux_phases_{lect}_egal_D05_6"] = round(float(x.valeur.iat[0]), 6)
    res.to_csv(HERE / "resultats_D05_6bis.csv", index=False, float_format="%.6g")
    pd.DataFrame(ch_rows).to_csv(HERE / "challenges_D05_6bis.csv", index=False, float_format="%.6g")
    pd.DataFrame(fi_rows).to_csv(HERE / "comptes_finances_D05_6bis.csv", index=False, float_format="%.6g")
    pd.DataFrame(annees).to_csv(HERE / "annees_D05_6bis.csv", index=False, float_format="%.6g")
    ctrl["duree_s"] = round(time.time() - t0)
    (HERE / "controles_D05_6bis.json").write_text(json.dumps(D01.jsonable(ctrl), ensure_ascii=False, indent=1),
                                                  encoding="utf-8")
    figures()
    write_rapport()
    print(f"D05.6bis : fait en {ctrl['duree_s']} s ; sorties dans {HERE}")


def _matrice(res: pd.DataFrame, lect: str, mes: str, col: str) -> pd.DataFrame:
    g = res[(res.lecture == lect) & (res.mesure == mes)]
    return g.pivot(index="challenge", columns="finance", values=col).loc[[c for c, _ in CHALLENGE],
                                                                          [f for f, _ in FINANCE]]


def figures() -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.colors import LinearSegmentedColormap
    res = pd.read_csv(HERE / "resultats_D05_6bis.csv")
    FIG.mkdir(parents=True, exist_ok=True)
    ink, muted = "#0b0b0b", "#52514e"
    cmap = LinearSegmentedColormap.from_list("ecart", ["#eb6834", "#f3f2ef", "#2a78d6"])
    panneaux = (("tentative", "12 mois", "Une tentative, 12 mois"), ("tentative", "24 mois", "Une tentative, 24 mois"),
                ("suite", "12 mois", "Suite de tentatives, 12 mois"), ("suite", "24 mois", "Suite de tentatives, 24 mois"))
    mats = {(m, l): _matrice(res, l, m, "ecart_ref") * D055.COMPTE / 1000 for m, l, _ in panneaux}
    fig, axes = plt.subplots(2, 2, figsize=(16, 13))
    for ax, (mes, lect, titre) in zip(axes.flat, panneaux):
        m = mats[(mes, lect)]
        lo = _matrice(res, lect, mes, "ecart_ic_bas").to_numpy()
        hi = _matrice(res, lect, mes, "ecart_ic_haut").to_numpy()
        val = _matrice(res, lect, mes, "valeur").to_numpy() * D055.COMPTE / 1000
        lim = np.nanmax(np.abs(m.to_numpy()))                 # échelle propre à chaque panneau
        ax.imshow(m.to_numpy(), cmap=cmap, vmin=-lim, vmax=lim, aspect="auto")
        for i in range(m.shape[0]):
            for j in range(m.shape[1]):
                x = m.iat[i, j]
                net = (lo[i, j] > 0) or (hi[i, j] < 0)
                cn, fn = m.index[i], m.columns[j]
                tag = "réf." if (cn, fn) == REF else PORTEUR.get((cn, fn), "")
                txt = (f"{val[i, j]:+.1f}".replace(".", ",") + " k€\n("
                       + ("réf." if tag == "réf." else f"{x:+.1f}".replace(".", ",")) + ")")
                ax.text(j, i, txt, ha="center", va="center", fontsize=7.5, color=ink,
                        fontweight="bold" if net else "normal")
                if tag in ("A", "B", "réf."):
                    ax.add_patch(plt.Rectangle((j - 0.5, i - 0.5), 1, 1, fill=False, lw=2,
                                               ec=ink if tag == "réf." else muted, ls="-" if tag == "réf." else "--"))
                    if tag != "réf.":
                        ax.text(j - 0.44, i - 0.36, tag, fontsize=8, color=muted, fontweight="bold")
        ax.set_xticks(range(m.shape[1]), [f.replace(" → ", "\n→ ") for f in m.columns], fontsize=8, color=muted)
        ax.set_yticks(range(m.shape[0]), m.index, fontsize=8, color=muted)
        ax.set_xlabel("taille du compte financé (%/ATR)", color=muted, fontsize=9)
        ax.set_ylabel("taille du challenge (%/ATR)", color=muted, fontsize=9)
        ax.set_title(f"{titre} ; couleur : ± {lim:.1f} k€".replace(".", ","), fontsize=10, color=ink)
        for sp in ax.spines.values():
            sp.set_visible(False)
    fig.suptitle("Valeur moyenne et écart apparié à la référence (fixe 0,20 dans les deux phases), en k€ ; "
                 "gras : IC 95 % de l'écart sans zéro ; A, B : combos du porteur", fontsize=10, color=ink)
    fig.tight_layout(rect=(0, 0, 1, 0.97))
    fig.savefig(FIG / "D05_6bis_matrices.png", dpi=110)
    plt.close(fig)


fr, sg, pct, n_fr, table = D01.fr, D01.sg, D01.pct, D01.n_fr, D01.table
eur = D055.eur


def _ecart(x) -> str:
    return "réf." if (x.challenge, x.finance) == REF else (
        f"{eur(x.ecart_ref)} [{eur(x.ecart_ic_bas)} ; {eur(x.ecart_ic_haut)}]")


def write_rapport() -> None:
    res = pd.read_csv(HERE / "resultats_D05_6bis.csv")
    ch = pd.read_csv(HERE / "challenges_D05_6bis.csv")
    fi = pd.read_csv(HERE / "comptes_finances_D05_6bis.csv")
    ct = json.loads((HERE / "controles_D05_6bis.json").read_text(encoding="utf-8"))
    narr = HERE / "narratif_D05_6bis.md"
    out = [narr.read_text(encoding="utf-8") if narr.exists() else "# EXP-D05.6bis — rapport (narratif à rédiger)\n",
           "", "---", "", "# Annexes générées (`run_D05_6bis.py --calcul`, puis `--rapport`)", "",
           f"Calcul du {ct['date']}, commit `{ct['commit']}`, {ct['duree_s']} s.", "", "## A1. Contrôle bloquant (passé)", ""]
    out += [f"- {k} : {json.dumps(v, ensure_ascii=False)}." for k, v in ct.items()
            if k not in ("date", "commit", "duree_s", "motif")]
    for fen, titre in (("toute", "tous les départs"), ("sans_2026", "sans 2026")):
        g = ch[ch.fenetre == fen]
        out += ["", f"## A2. Challenge selon sa taille, {titre} ({int(g.n_departs.iat[0])} départs)", "",
                table(["Taille du challenge", "Réussite P1 + P2 [IC 95 %]", "En cours", "Délai médian ; P90",
                       f"Délai médian < {DELAI_PORTEUR:.0f} j (porteur)"],
                      [[x.challenge, f"{pct(x.p_reussite, 1)} [{pct(x.ic_bas, 1)} ; {pct(x.ic_haut, 1)}]",
                        pct(x.p_en_cours_p1 + x.p_en_cours_p2, 1),
                        f"{fr(x.jours_total_med, 0)} ; {fr(x.jours_total_p90, 0)} j",
                        "oui" if x.jours_total_med < DELAI_PORTEUR else "non"] for _, x in g.iterrows()])]
    out += ["", "## A3. Comptes financés démarrés à chaque minuit, selon leur taille", "",
            table(["Taille du compte financé", "Horizon", "Comptes", "Perdus dans l'horizon",
                   "Durée médiane des comptes perdus", "Retiré moyen (avant partage) ; reçu (80 %)"],
                  [[x.finance, f"{x.horizon_jours / 365:.0f} an(s)", n_fr(x.comptes), pct(x.p_perdu, 1),
                    f"{fr(x.duree_mediane_perdus, 0)} j", f"{pct(x.retire_moyen, 2)} ; {fr(x.recu_moyen_eur, 0)} €"]
                   for _, x in fi.iterrows()])]
    for mes, titre in (("tentative", "Valeur d'une tentative"), ("suite", "Valeur d'une suite de tentatives")):
        for lect, _, _ in LECTURES:
            v = _matrice(res, lect, mes, "valeur")
            e = _matrice(res, lect, mes, "ecart_ref")
            n = int(res[(res.lecture == lect) & (res.mesure == mes)].n_departs.iat[0])
            out += ["", f"## A4. {titre}, {lect} ({n} départs) : valeur (écart à la référence)", "",
                    table(["Challenge ↓ / compte financé →"] + list(v.columns),
                          [[c] + [f"{eur(v.at[c, f])} ({'réf.' if (c, f) == REF else eur(e.at[c, f])})"
                                  for f in v.columns] for c in v.index])]
    sel = pd.Series([(c, f) in SELECTION for c, f in zip(res.challenge, res.finance)])
    for mes, titre in (("tentative", "une tentative"), ("suite", "une suite de tentatives")):
        g = res[sel & (res.mesure == mes)].copy()
        g["ordre"] = [SELECTION.index((c, f)) for c, f in zip(g.challenge, g.finance)]
        out += ["", f"## A5. Combinaisons choisies pour l'affichage, {titre} : IC et queues", "",
                table(["Challenge", "Compte financé", "Combo", "Lecture", "Valeur moyenne [IC 95 %]",
                       "Médiane ; P10 ; P90", "Écart apparié à la référence [IC 95 %]",
                       "Départs : mieux ; moins bien que la référence",
                       "≥ 1 retrait" if mes == "tentative" else "Tentatives ; comptes financés par suite"],
                      [[x.challenge, x.finance, "réf." if (x.challenge, x.finance) == REF else (x.combo or "—"),
                        x.lecture, f"{eur(x.valeur)} [{eur(x.ic_bas)} ; {eur(x.ic_haut)}]",
                        f"{eur(x.mediane)} ; {eur(x.p10)} ; {eur(x.p90)}", _ecart(x),
                        "—" if (x.challenge, x.finance) == REF else f"{pct(x.p_mieux, 1)} ; {pct(x.p_moins, 1)}",
                        pct(x.p_retrait, 1) if mes == "tentative" else f"{fr(x.tentatives, 1)} ; {fr(x.finances, 1)}"]
                       for _, x in g.sort_values(["lecture", "ordre"]).iterrows()])]
    an = pd.read_csv(HERE / "annees_D05_6bis.csv")
    for mes, titre in (("tentative", "une tentative"), ("suite", "une suite de tentatives")):
        for lect in ("12 mois", "24 mois"):
            g = an[(an.mesure == mes) & (an.lecture == lect)]
            ans = sorted(g.annee.unique())
            lignes = []
            for c, f in SELECTION:
                h = g[(g.challenge == c) & (g.finance == f)].set_index("annee")
                lignes.append([c, f] + [f"{eur(h.at[a, 'valeur'])}" if (c, f) == REF else eur(h.at[a, 'ecart_ref'])
                                        for a in ans])
            out += ["", f"## A6. Par année de départ, {titre}, {lect} : valeur de la référence, puis écart à la "
                        f"référence", "",
                    table(["Challenge", "Compte financé"] + [f"{a} ({int(g[g.annee == a].n_departs.iat[0])} départs)"
                                                            for a in ans], lignes)]
    out += ["", "## A7. Figure", "", "![Matrices](figures/D05_6bis_matrices.png)", ""]
    (HERE / "rapport_D05_6bis.md").write_text("\n".join(out) + "\n", encoding="utf-8")


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
