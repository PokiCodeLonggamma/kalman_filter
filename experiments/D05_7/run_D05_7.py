"""EXP-D05.7 — tirage par blocs de semaines, sans 2026 : le roster final de D05.6bis face à des histoires recomposées,
RE-1 version finale sur les six actifs. GO du porteur du 2026-10-05 (blocs d'une semaine et de quatre semaines, 200
histoires chacune).

Usage, depuis la racine du dépôt : python experiments/D05_7/run_D05_7.py --chrono | --calcul | --rapport

Cadrage (fixé avant le calcul ; lecture sans seuil de décision)
- QUESTION : les gains du challenge rapide (2 − 1, 3b − 3a, 3c − 3b) et de la relance (3a − 1, 3b − 2) survivent-ils
  quand on détruit l'enchaînement des semaines (blocs d'une semaine), ou au-delà d'un mois (blocs de quatre semaines) ?
- DONNÉES : trades de D04.1 (RE-1 version finale, six actifs ; réserve levée par `reserve.levee`) entrés du lundi
  2021-10-04 au lundi 2025-12-29 exclu (221 semaines, sans 2026), avec leur chemin de barres de 30 minutes, leur ATR14
  au signal et leurs frais (5 bps, or 4 bps).
- MÉTHODE :
  - Histoire recomposée (`propfirm.blocs`) : 221 semaines tirées avec remise par blocs de L semaines consécutives
    (L = 1, puis L = 4), début uniforme. Chaque semaine apporte tous ses trades, sur les six actifs, avec leur chemin
    d'origine ; jambe de débordement si un trade chevauche le suivant du même actif.
  - Sur chaque histoire : challenge à 0,20, 0,25 et 0,30 %/ATR ; compte financé fixe 0,20, fixe 0,25 et relance (0,20 ;
    0,40 quand le capital valorisé tombe à −5 % ; 0,20 au-dessus de −2 %). Règles et lecture principale de D05.4 à
    D05.6bis : FTMO Swing, marge plafonnée (crypto 1:2, or 1:30), borne pessimiste, perte du jour depuis le solde de
    minuit ; compte financé à 80 %, retraits tous les 14 jours, 540 € remboursés au premier retrait.
  - Roster : référence (0,20 × 0,20), piste 1 (0,20 × 0,25), piste 2 (0,25 × 0,25), pistes 3a, 3b, 3c (0,20, 0,25,
    0,30 × relance).
  - Départ à chaque minuit local ; valeur moyenne d'une tentative et d'une suite de tentatives, à 12 et 24 mois, sur les
    départs suivis assez longtemps avant la fin de l'histoire (événements postérieurs non observés).
  - 200 histoires par longueur de bloc ; graines 7001 + i (L = 1) et 7401 + i (L = 4) ; calcul en parallèle.
- CRITÈRE DE LECTURE (sans seuil) :
  - pour chaque piste : médiane et P5-P95 de la valeur sur les histoires, et valeur de l'histoire réelle (identité) ;
  - pour chaque écart entre pistes (1 − réf., 2 − 1, 3a − 1, 3b − 2, 3b − 3a, 3c − 3b) : part des histoires où il est
    positif, médiane et P5-P95, et rang de l'écart de l'histoire réelle dans cette distribution ;
  - un écart qui reste du même ordre tient à la mécanique ; un écart qui fond tenait à l'enchaînement des semaines ;
  - réussite et délai médian des challenges par histoire, pour lire le déplacement de toutes les pistes.
- Contrôle bloquant : l'histoire identité (semaines dans l'ordre) redonne exactement l'évaluation des jambes d'origine
  réduites à la fenêtre.
- Biais : données déjà lues ; roster choisi sur ces données (D05.6bis) ; les blocs coupent aussi les liens entre
  semaines voisines (débordements) ; décalage d'une heure possible entre heure d'été et heure d'hiver ; 200 histoires :
  une part d'histoires est connue à ± 3,5 points environ.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
import time
import warnings
from concurrent.futures import ProcessPoolExecutor
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

from envelope.portfolio import Leg  # noqa: E402
from propfirm import (FTMO_SWING, LEVIER_FTMO_SWING, Fixe, Frein, challenge, departs_minuit, simuler,  # noqa: E402
                      suite, valeur)
from propfirm.blocs import histoire, semaines, tirage  # noqa: E402
from reserve import levee  # noqa: E402

FIG = HERE / "figures"
MOTIF = "EXP-D05.7 (porteur, 2026-10-05)"
DEBUT, FIN = "2021-10-04", "2025-12-29"                  # lundis ; fin exclue
LONGUEURS = (1, 4)
N_HIST = 200
GRAINE = {1: 7001, 4: 7401}
HORIZONS = (365, 730)
MESURES = ("tentative", "suite")
CHALLENGE = {"0,20": Fixe(20.0), "0,25": Fixe(25.0), "0,30": Fixe(30.0)}
FINANCE = {"0,20": Fixe(20.0), "0,25": Fixe(25.0), "relance": Frein(haut=20.0, bas=40.0, seuil=0.95, retour=0.98)}
ROSTER = (("Référence", "0,20", "0,20"), ("Piste 1", "0,20", "0,25"), ("Piste 2", "0,25", "0,25"),
          ("Piste 3a", "0,20", "relance"), ("Piste 3b", "0,25", "relance"), ("Piste 3c", "0,30", "relance"))
COMPARAISONS = (("Piste 1", "Référence", "compte financé 0,25 au lieu de 0,20"),
                ("Piste 2", "Piste 1", "challenge 0,25 au lieu de 0,20"),
                ("Piste 3a", "Piste 1", "relance au lieu de 0,25"),
                ("Piste 3b", "Piste 2", "relance au lieu de 0,25 (challenge 0,25)"),
                ("Piste 3b", "Piste 3a", "challenge 0,25 au lieu de 0,20 (relance)"),
                ("Piste 3c", "Piste 3b", "challenge 0,30 au lieu de 0,25 (relance)"))
PROCESSUS = 6                                            # un par cœur physique ; mémoire libre ≈ 3,4 Go
_BASE: dict = {}


def stop(msg: str):
    raise SystemExit(f"D05.7, contrôle bloquant : {msg} : arrêt")


def _reduire(leg: Leg, a: np.ndarray, debut: int, fin: int) -> tuple[Leg, np.ndarray]:
    """La jambe réduite aux trades entrés dans [debut, fin[, ses barres coupées du premier au dernier trade."""
    tr = leg.trades.reset_index(drop=True)
    t = pd.DatetimeIndex(leg.bars.time).asi8
    m = (t[tr.entry_bar.to_numpy()] >= debut) & (t[tr.entry_bar.to_numpy()] < fin)
    tr, a, w = tr[m].reset_index(drop=True).copy(), np.asarray(a)[m], np.asarray(leg.weight)[m]
    lo, hi = int(tr.entry_bar.min()), int(tr.exit_bar.max())
    for c in ("entry_bar", "exit_bar", "signal_bar"):
        tr[c] = tr[c] - lo
    return Leg(leg.name, leg.bars.iloc[lo:hi + 1].reset_index(drop=True), tr, w, leg.cost), a


def base() -> dict:
    """Jambes d'origine réduites à la fenêtre, ATR, bornes des semaines, départs."""
    bornes = semaines(DEBUT, FIN, FTMO_SWING.fuseau)
    with levee(MOTIF):
        assets = D041.load_all()
        lg = D054.legs(assets, 25.0)                         # poids des jambes inutilisés : la taille les remplace
        atr = [assets[leg.name]["atr_bps"][leg.trades.signal_bar.to_numpy()] for leg in lg]
    red = [_reduire(leg, a, bornes[0], bornes[-1]) for leg, a in zip(lg, atr)]
    return {"legs": [r[0] for r in red], "atr": [r[1] for r in red], "bornes": bornes,
            "departs": departs_minuit(DEBUT, FIN, FTMO_SWING.fuseau), "fin": int(bornes[-1])}


def evaluer(lg: list[Leg], atr: list[np.ndarray], departs: np.ndarray, fin: int) -> tuple[list[dict], list[dict]]:
    """Valeurs moyennes du roster (tentative et suite, 12 et 24 mois) et challenges (réussite, délai médian)."""
    opts = dict(levier=LEVIER_FTMO_SWING, plafonner=True, atr=atr)
    sims_c = {n: simuler(lg, departs, taille=t, **opts) for n, t in CHALLENGE.items()}
    sims_f = {n: simuler(lg, departs, D055.FINANCE, taille=t, retrait_jours=D055.RETRAIT_JOURS, **opts)
              for n, t in FINANCE.items()}
    fin_ts = pd.Timestamp(fin, tz="UTC")
    chal = []
    for n, s in sims_c.items():
        out = challenge(s, coupure=fin)
        ok = out.issue == "reussite"
        chal.append({"challenge": n, "p_reussite": float(ok.mean()),
                     "jours_med": float(out.jours_total[ok].median()) if ok.any() else np.nan})
    vals = []
    for piste, cn, fn in ROSTER:
        for h in HORIZONS:
            kw = dict(frais=D055.FRAIS, part=D055.PART, horizon_jours=h, coupure=fin)
            for mes, f in (("tentative", valeur), ("suite", suite)):
                out = f(sims_c[cn], sims_f[fn], **kw)
                out = out[out.depart + pd.Timedelta(days=h) <= fin_ts]
                vals.append({"piste": piste, "horizon": h, "mesure": mes, "n_departs": len(out),
                             "valeur": float(out.valeur.mean())})
    return vals, chal


def _init(b: dict) -> None:
    warnings.simplefilter("ignore")
    _BASE.update(b)


def une_histoire(cle: tuple[int, int]) -> tuple[list[dict], list[dict]]:
    longueur, i = cle
    n = len(_BASE["bornes"]) - 1
    src = tirage(n, longueur, np.random.default_rng(GRAINE[longueur] + i))
    lg, atr = histoire(_BASE["legs"], _BASE["atr"], _BASE["bornes"], src)
    vals, chal = evaluer(lg, atr, _BASE["departs"], _BASE["fin"])
    tag = {"longueur": longueur, "histoire": i, "jambes": len(lg)}
    return [{**tag, **v} for v in vals], [{**tag, **c} for c in chal]


def run_chrono() -> None:
    t0 = time.time()
    b = base()
    _init(b)
    t1 = time.time()
    une_histoire((1, 0))
    t2 = time.time()
    une_histoire((4, 0))
    t3 = time.time()
    w = PROCESSUS
    print(f"chargement {t1 - t0:.0f} s ; une histoire : {t2 - t1:.0f} s (L = 1), {t3 - t2:.0f} s (L = 4) ; "
          f"{len(LONGUEURS) * N_HIST} histoires sur {w} processus : environ "
          f"{len(LONGUEURS) * N_HIST * (t3 - t1) / 2 / w / 60:.0f} min hors partage des cœurs")


def run_calcul() -> None:
    t0 = time.time()
    ctrl = {"date": pd.Timestamp.now(tz="UTC").strftime("%Y-%m-%d %H:%M UTC"), "commit": D04.git_head(), "motif": MOTIF}
    b = base()
    _init(b)
    ref_vals, ref_chal = evaluer(b["legs"], b["atr"], b["departs"], b["fin"])
    n = len(b["bornes"]) - 1
    lg_id, atr_id = histoire(b["legs"], b["atr"], b["bornes"], np.arange(n))
    id_vals, id_chal = evaluer(lg_id, atr_id, b["departs"], b["fin"])
    if len(lg_id) != len(b["legs"]) or not all(np.isclose(u["valeur"], v["valeur"], rtol=1e-12, atol=0.0)
                                               for u, v in zip(ref_vals, id_vals)):
        stop("l'histoire identité ne redonne pas les jambes d'origine")
    ctrl.update(semaines=n, departs=len(b["departs"]), trades=int(sum(len(leg.trades) for leg in b["legs"])),
                identite_egale_origine=len(ref_vals))
    print(f"contrôle d'identité passé ({time.time() - t0:.0f} s)", flush=True)
    cles = [(L, i) for L in LONGUEURS for i in range(N_HIST)]
    w = PROCESSUS
    vals, chal = [], []
    with ProcessPoolExecutor(max_workers=w, initializer=_init, initargs=(b,)) as ex:
        for k, (v, c) in enumerate(ex.map(une_histoire, cles, chunksize=1), 1):
            vals += v
            chal += c
            if k % 20 == 0:
                print(f"{k}/{len(cles)} histoires ({time.time() - t0:.0f} s)", flush=True)
    tag = {"longueur": 0, "histoire": -1, "jambes": len(lg_id)}            # longueur 0 : histoire réelle
    vals += [{**tag, **v} for v in id_vals]
    chal += [{**tag, **c} for c in id_chal]
    pd.DataFrame(vals).to_csv(HERE / "histoires_D05_7.csv", index=False, float_format="%.6g")
    pd.DataFrame(chal).to_csv(HERE / "challenges_D05_7.csv", index=False, float_format="%.6g")
    ctrl.update(processus=w, duree_s=round(time.time() - t0))
    (HERE / "controles_D05_7.json").write_text(json.dumps(D01.jsonable(ctrl), ensure_ascii=False, indent=1),
                                               encoding="utf-8")
    resumer()
    figures()
    write_rapport()
    print(f"D05.7 : fait en {ctrl['duree_s']} s ; sorties dans {HERE}")


def _rang(x: np.ndarray, v: float) -> float:
    """Part des histoires dont la valeur est inférieure à v (égalités comptées pour moitié)."""
    return float(((x < v).sum() + 0.5 * (x == v).sum()) / len(x))


def resumer() -> None:
    h = pd.read_csv(HERE / "histoires_D05_7.csv")
    ch = pd.read_csv(HERE / "challenges_D05_7.csv")
    reel = h[h.longueur == 0].set_index(["piste", "horizon", "mesure"]).valeur
    rows = []
    for L in LONGUEURS:
        g = h[h.longueur == L].pivot_table(index="histoire", columns=["piste", "horizon", "mesure"], values="valeur")
        for piste, _, _ in ROSTER:
            for hz in HORIZONS:
                for mes in MESURES:
                    x = g[(piste, hz, mes)].to_numpy()
                    r = reel[(piste, hz, mes)]
                    rows.append({"longueur": L, "type": "piste", "piste": piste, "contre": "", "horizon": hz,
                                 "mesure": mes, "histoires": len(x), "mediane": float(np.median(x)),
                                 "p5": float(np.quantile(x, 0.05)), "p95": float(np.quantile(x, 0.95)),
                                 "p_positif": float((x > 0).mean()), "reel": float(r), "rang_reel": _rang(x, r)})
        for a, bb, _ in COMPARAISONS:
            for hz in HORIZONS:
                for mes in MESURES:
                    x = (g[(a, hz, mes)] - g[(bb, hz, mes)]).to_numpy()
                    r = reel[(a, hz, mes)] - reel[(bb, hz, mes)]
                    rows.append({"longueur": L, "type": "ecart", "piste": a, "contre": bb, "horizon": hz,
                                 "mesure": mes, "histoires": len(x), "mediane": float(np.median(x)),
                                 "p5": float(np.quantile(x, 0.05)), "p95": float(np.quantile(x, 0.95)),
                                 "p_positif": float((x > 0).mean()), "reel": float(r), "rang_reel": _rang(x, r)})
    pd.DataFrame(rows).to_csv(HERE / "resultats_D05_7.csv", index=False, float_format="%.6g")
    c = ch.groupby(["longueur", "challenge"]).agg(p_reussite_med=("p_reussite", "median"),
                                                  p_reussite_p5=("p_reussite", lambda s: s.quantile(0.05)),
                                                  p_reussite_p95=("p_reussite", lambda s: s.quantile(0.95)),
                                                  jours_med=("jours_med", "median")).reset_index()
    c.to_csv(HERE / "challenges_resume_D05_7.csv", index=False, float_format="%.6g")


def figures() -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.ticker import FuncFormatter, MaxNLocator
    res = pd.read_csv(HERE / "resultats_D05_7.csv")
    FIG.mkdir(parents=True, exist_ok=True)
    ink, muted, grid = "#0b0b0b", "#52514e", "#e4e3df"
    couleur = {1: "#2a78d6", 4: "#1baf7a"}
    panneaux = (("tentative", 365, "Une tentative, 12 mois"), ("suite", 365, "Suite de tentatives, 12 mois"),
                ("suite", 730, "Suite de tentatives, 24 mois"))
    noms = [f"{a} − {b}".replace("Piste ", "").replace("Référence", "réf.") for a, b, _ in COMPARAISONS]
    fig, axes = plt.subplots(1, 3, figsize=(16, 6.2), sharey=True)
    for ax, (mes, hz, titre) in zip(axes, panneaux):
        g = res[(res.type == "ecart") & (res.mesure == mes) & (res.horizon == hz)]
        for k, (a, b, _) in enumerate(COMPARAISONS):
            for dy, L in ((-0.17, 1), (0.17, 4)):
                x = g[(g.piste == a) & (g.contre == b) & (g.longueur == L)].iloc[0]
                y = k + dy
                ax.plot([x.p5 * D055.COMPTE / 1000, x.p95 * D055.COMPTE / 1000], [y, y], color=couleur[L], lw=2,
                        alpha=0.55)
                ax.plot(x.mediane * D055.COMPTE / 1000, y, "o", color=couleur[L], ms=7,
                        label=f"blocs de {L} semaine{'s' if L > 1 else ''} : médiane et P5-P95" if k == 0 else None)
            reel = g[(g.piste == a) & (g.contre == b)].reel.iat[0]
            ax.plot(reel * D055.COMPTE / 1000, k, "D", color="#eb6834", ms=8, mec="white", mew=1.2,
                    label="histoire réelle (sans 2026)" if k == 0 else None)
        ax.axvline(0, color=muted, lw=1)
        ax.set_yticks(range(len(noms)), noms, fontsize=9, color=muted)
        ax.xaxis.set_major_locator(MaxNLocator(6, integer=True))
        ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:+.0f}".replace("-", "−") if v else "0"))
        ax.set_xlabel("écart entre pistes (k€, compte de 100 000)", color=muted)
        ax.set_title(titre, fontsize=10, color=ink)
        ax.grid(axis="x", color=grid, lw=0.8)
        ax.set_axisbelow(True)
        for sp in ("top", "right", "left"):
            ax.spines[sp].set_visible(False)
    axes[0].invert_yaxis()
    h, lab = axes[0].get_legend_handles_labels()
    fig.legend(h, lab, loc="lower center", ncol=3, frameon=False, fontsize=9)
    fig.suptitle("D05.7 — écarts entre pistes sur 200 histoires recomposées, par longueur de bloc", fontsize=11,
                 color=ink)
    fig.tight_layout(rect=(0, 0.07, 1, 0.95))
    fig.savefig(FIG / "D05_7_ecarts.png", dpi=110)
    plt.close(fig)


fr, pct, n_fr, table = D01.fr, D01.pct, D01.n_fr, D01.table
eur = D055.eur


def write_rapport() -> None:
    res = pd.read_csv(HERE / "resultats_D05_7.csv")
    ch = pd.read_csv(HERE / "challenges_resume_D05_7.csv")
    reel = pd.read_csv(HERE / "challenges_D05_7.csv").query("longueur == 0").set_index("challenge")
    ct = json.loads((HERE / "controles_D05_7.json").read_text(encoding="utf-8"))
    narr = HERE / "narratif_D05_7.md"
    out = [narr.read_text(encoding="utf-8") if narr.exists() else "# EXP-D05.7 — rapport (narratif à rédiger)\n",
           "", "---", "", "# Annexes générées (`run_D05_7.py --calcul`, puis `--rapport`)", "",
           f"Calcul du {ct['date']}, commit `{ct['commit']}`, {ct['duree_s']} s sur {ct['processus']} processus.", "",
           "## A1. Contrôle bloquant (passé)", "",
           f"- L'histoire identité redonne les jambes d'origine ({ct['identite_egale_origine']} valeurs égales).",
           f"- {ct['semaines']} semaines, {n_fr(ct['departs'])} départs, {n_fr(ct['trades'])} trades.", "",
           "## A2. Challenges : réussite P1 + P2 et délai médian", "",
           table(["Challenge", "Histoire réelle : réussite ; délai médian"]
                 + [f"Blocs de {L} sem. : réussite médiane [P5 ; P95] ; délai" for L in LONGUEURS],
                 [[c, f"{pct(reel.at[c, 'p_reussite'], 1)} ; {fr(reel.at[c, 'jours_med'], 0)} j"]
                  + [(lambda x: f"{pct(x.p_reussite_med, 1)} [{pct(x.p_reussite_p5, 1)} ; {pct(x.p_reussite_p95, 1)}]"
                                f" ; {fr(x.jours_med, 0)} j")(ch[(ch.longueur == L) & (ch.challenge == c)].iloc[0])
                     for L in LONGUEURS] for c in CHALLENGE])]
    for typ, titre in (("piste", "Valeur des pistes"), ("ecart", "Écarts entre pistes")):
        for mes in MESURES:
            for hz in HORIZONS:
                g = res[(res.type == typ) & (res.mesure == mes) & (res.horizon == hz)]
                lignes = []
                for _, x in g.iterrows():
                    nom = x.piste if typ == "piste" else f"{x.piste} − {x.contre}"
                    lignes.append([nom, f"{x.longueur} sem.", eur(x.reel), f"{eur(x.mediane)} [{eur(x.p5)} ; "
                                   f"{eur(x.p95)}]", pct(x.p_positif, 0), pct(x.rang_reel, 0)])
                out += ["", f"## A3. {titre}, {'une tentative' if mes == 'tentative' else 'suite de tentatives'}, "
                            f"{hz // 365 * 12} mois", "",
                        table([typ == "piste" and "Piste" or "Écart", "Blocs", "Histoire réelle",
                               "Histoires : médiane [P5 ; P95]", "Histoires > 0", "Rang de l'histoire réelle"],
                              lignes)]
    out += ["", "## A4. Figure", "", "![Écarts](figures/D05_7_ecarts.png)", ""]
    (HERE / "rapport_D05_7.md").write_text("\n".join(out) + "\n", encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--chrono", action="store_true")
    g.add_argument("--calcul", action="store_true")
    g.add_argument("--rapport", action="store_true")
    args = ap.parse_args()
    warnings.simplefilter("ignore")
    if args.chrono:
        run_chrono()
    elif args.calcul:
        run_calcul()
    else:
        resumer()
        figures()
        write_rapport()


if __name__ == "__main__":
    main()
