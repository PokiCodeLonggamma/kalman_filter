"""EXP-D05.8 — moment d'achat du challenge : n'acheter le ticket que lorsque la volatilité du panier crypto sort d'une
zone de compression, ou lorsque le panier est en tendance haussière ; pistes 1 et 2 du roster (D05.6bis), RE-1 version
finale sur les six actifs. GO du porteur du 2026-10-05 (dernière mesure avant la clôture de la séquence taille).

Usage, depuis la racine du dépôt : python experiments/D05_8/run_D05_8.py --calcul | --rapport

Cadrage (fixé avant le calcul ; lecture sans seuil de décision)
- QUESTION : acheter le challenge seulement quand le marché crypto s'éveille (volatilité qui sort d'une compression) ou
  monte (tendance haussière) améliore-t-il la réussite et la valeur des pistes 1 et 2, et de la référence ?
- DONNÉES : celles de D05.4 à D05.6bis (trades de D04.1, six actifs, 2021-10 → 2026-09 ; frais 5 bps, or 4 bps).
  Indicateurs sur les barres de 30 minutes des cinq cryptos (BTC, ETH, SOL, AVAX, XRP), sans l'or.
- MÉTHODE :
  - À chaque minuit local M, avec les seules barres closes au plus tard à M :
    - ATR du panier : moyenne sur les cinq cryptos de l'ATR14 (bps) moyen des barres closes dans la journée qui
      finit à M ;
    - indice du panier : moyenne sur les cinq cryptos du logarithme de la dernière clôture avant M.
  - Filtre V, sortie de compression : moyenne de l'ATR du panier sur 7 jours > moyenne sur 30 jours, alors que la
    moyenne sur 30 jours est sous la médiane de l'ATR du panier sur 365 jours.
  - Filtre T, tendance haussière : indice du panier au-dessus de sa moyenne sur 50 jours.
  - Fenêtres conventionnelles, fixées avant le calcul, non optimisées.
  - Pistes : 1 (challenge 0,20 × compte financé 0,25), 2 (0,25 × 0,25), et la référence (0,20 × 0,20), ajoutée à la
    demande du porteur ; lecture principale de D05.4 à D05.6bis.
  - Par tentative : tentatives démarrées les jours où le filtre est ouvert, contre tous les jours et contre les jours
    fermés.
  - En suite (rachat non aveugle) : un compte à la fois ; la première tentative et chaque rachat attendent le premier
    minuit où le filtre est ouvert (`propfirm.suite`, `permis`) ; comparée, départ par départ, à la suite sans filtre.
  - Horizons : 12 et 24 mois, et 12 mois sans 2026.
- CRITÈRE DE LECTURE (sans seuil) : part des jours ouverts ; réussite et délai médian ; valeur moyenne des tentatives
  ouvertes, fermées et de toutes, écart ouvertes − toutes avec IC à 95 % par blocs de mois ; suite filtrée − suite sans
  filtre, apparié, avec IC ; tentatives par suite ; écart par année de départ.
- Contrôles bloquants : les indicateurs d'un minuit ne changent pas quand on coupe les barres postérieures ; sans
  filtre, les pistes redonnent le roster de D05.6bis.
- Biais : données déjà lues ; filtres proposés par le porteur après lecture de D05.7 ; un filtre de régime mise sur
  la persistance des périodes, que D05.7 a montrée fragile ; départs chevauchants et jours ouverts groupés : IC larges.
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

from propfirm import (FTMO_SWING, LEVIER_FTMO_SWING, Fixe, challenge, departs_minuit, ic_blocs,  # noqa: E402
                      simuler, suite, valeur)
from propfirm.moteur import HALF  # noqa: E402
from reserve import levee  # noqa: E402

FIG = HERE / "figures"
MOTIF = "EXP-D05.8 (porteur, 2026-10-05)"
A, B = D054.A, D054.B
CRYPTOS = ("BTC", "ETH", "SOL", "AVAX", "XRP")
COURT, LONG, ANNEE, TENDANCE = 7, 30, 365, 50
PISTES = (("Référence", Fixe(20.0), Fixe(20.0)), ("Piste 1", Fixe(20.0), Fixe(25.0)),
          ("Piste 2", Fixe(25.0), Fixe(25.0)))
FILTRES = ("aucun", "V · sortie de compression", "T · tendance haussière")
LECTURES = D055.LECTURES                                 # 12 mois, 24 mois, sans 2026 (12 mois)
ROSTER = ROOT / "experiments" / "D05_6bis" / "roster_D05_6bis.csv"


def stop(msg: str):
    raise SystemExit(f"D05.8, contrôle bloquant : {msg} : arrêt")


def journalier(assets: dict, coupure: pd.Timestamp | None = None) -> pd.DataFrame:
    """ATR du panier et indice du panier à chaque minuit local, depuis les barres closes au plus tard à ce minuit."""
    atr, idx = [], []
    for k in CRYPTOS:
        p = assets[k]
        close_t = pd.to_datetime(pd.DatetimeIndex(p["bars"].time).asi8 + HALF, utc=True).tz_convert(FTMO_SWING.fuseau)
        a = pd.Series(np.asarray(p["atr_bps"], dtype=float), index=close_t)
        c = pd.Series(np.log(p["bars"].close.to_numpy(dtype=float)), index=close_t)
        if coupure is not None:
            a, c = a[a.index <= coupure], c[c.index <= coupure]
        atr.append(a.resample("D", closed="right", label="right").mean().rename(k))
        idx.append(c.resample("D", closed="right", label="right").last().ffill().rename(k))
    atr, idx = pd.concat(atr, axis=1), pd.concat(idx, axis=1)
    j = pd.DataFrame({"atr": atr.mean(axis=1), "indice": idx.mean(axis=1)}).dropna()
    j["atr_court"] = j.atr.rolling(COURT).mean()
    j["atr_long"] = j.atr.rolling(LONG).mean()
    j["atr_mediane_an"] = j.atr.rolling(ANNEE).median()
    j["indice_moyenne"] = j.indice.rolling(TENDANCE).mean()
    j["V"] = (j.atr_court > j.atr_long) & (j.atr_long < j.atr_mediane_an)
    j["T"] = j.indice > j.indice_moyenne
    return j


def filtres(j: pd.DataFrame, departs: np.ndarray) -> dict[str, np.ndarray]:
    m = pd.DatetimeIndex(pd.to_datetime(departs, utc=True).tz_convert(FTMO_SWING.fuseau))
    jj = j.reindex(m)
    if jj[["atr_mediane_an", "indice_moyenne"]].isna().any().any():
        stop("indicateurs manquants à un départ (historique trop court)")
    return {FILTRES[0]: np.ones(len(departs), dtype=bool), FILTRES[1]: jj["V"].to_numpy(dtype=bool),
            FILTRES[2]: jj["T"].to_numpy(dtype=bool)}           # jj.T serait la transposée


def ic_ecart(x: np.ndarray, on: np.ndarray, depart: pd.Series, n_boot: int = 2000, seed: int = 0) -> tuple:
    """IC à 95 % de moyenne(x | ouvert) − moyenne(x), par rééchantillonnage des mois de départ."""
    mois = (depart.dt.year * 100 + depart.dt.month).to_numpy()
    blocs = np.unique(mois)
    so = np.array([x[(mois == b) & on].sum() for b in blocs])
    co = np.array([((mois == b) & on).sum() for b in blocs])
    st = np.array([x[mois == b].sum() for b in blocs])
    ct = np.array([(mois == b).sum() for b in blocs])
    tir = np.random.default_rng(seed).integers(0, len(blocs), size=(n_boot, len(blocs)))
    with np.errstate(invalid="ignore", divide="ignore"):
        p = so[tir].sum(1) / co[tir].sum(1) - st[tir].sum(1) / ct[tir].sum(1)
    return float(np.nanquantile(p, 0.025)), float(np.nanquantile(p, 0.975))


def run_calcul() -> None:
    t0 = time.time()
    ctrl = {"date": pd.Timestamp.now(tz="UTC").strftime("%Y-%m-%d %H:%M UTC"), "commit": D04.git_head(), "motif": MOTIF}
    roster = pd.read_csv(ROSTER)
    with levee(MOTIF):
        assets = D041.load_all()
        departs = departs_minuit(A, B, FTMO_SWING.fuseau)
        j = journalier(assets)
        for cut in ("2022-06-15", "2023-11-20", "2025-03-03"):           # causalité : couper l'avenir ne change rien
            c = pd.Timestamp(cut, tz=FTMO_SWING.fuseau)
            jc = journalier(assets, c)
            a, b = j.loc[j.index <= c, ["V", "T", "atr", "indice"]], jc.loc[jc.index <= c, ["V", "T", "atr", "indice"]]
            if not (a.index.equals(b.index) and a.equals(b)):
                stop(f"indicateurs modifiés par les barres postérieures au {cut}")
        ctrl["causalite_coupures"] = 3
        f = filtres(j, departs)
        lg = D054.legs(assets, 25.0)
        atr = [assets[leg.name]["atr_bps"][leg.trades.signal_bar.to_numpy()] for leg in lg]
        opts = dict(levier=LEVIER_FTMO_SWING, plafonner=True, atr=atr)
        sims = {n: (simuler(lg, departs, taille=tc, **opts),
                    simuler(lg, departs, D055.FINANCE, taille=tf, retrait_jours=D055.RETRAIT_JOURS, **opts))
                for n, tc, tf in PISTES}
    print(f"simulations faites ({time.time() - t0:.0f} s)", flush=True)
    jd = j.reindex(pd.DatetimeIndex(pd.to_datetime(departs, utc=True).tz_convert(FTMO_SWING.fuseau)))
    jd.assign(V=f[FILTRES[1]], T=f[FILTRES[2]]).to_csv(HERE / "indicateurs_D05_8.csv", float_format="%.6g")
    rows, annees = [], []
    for piste, _, _ in PISTES:
        sc, sf = sims[piste]
        for lect, h, coup in LECTURES:
            kw = dict(frais=D055.FRAIS, part=D055.PART, horizon_jours=h, coupure=coup)
            v = valeur(sc, sf, **kw)
            on_all = {k: m[:len(v)] for k, m in f.items()}                  # valeur : départs avant la coupure
            ch = challenge(sc, coupure=coup)
            garde = (v.depart + pd.Timedelta(days=h) <= (D055.FIN if coup is None else pd.Timestamp(coup, tz="UTC")))
            v, ch = v[garde.to_numpy()].reset_index(drop=True), ch[garde.to_numpy()].reset_index(drop=True)
            base = suite(sc, sf, **kw)
            if len(base) != len(garde):
                stop("suite et valeur : départs différents")
            base = base[garde.to_numpy()].reset_index(drop=True)
            x = v.valeur.to_numpy()
            for nom, mask in on_all.items():
                on = mask[garde.to_numpy()]
                ok = (ch.issue == "reussite").to_numpy()
                lo, hi = ic_ecart(x, on, v.depart) if 0 < on.sum() < len(on) else (np.nan, np.nan)
                s = suite(sc, sf, permis=f[nom], **kw)
                s = s[garde.to_numpy()].reset_index(drop=True)
                ds = s.valeur.to_numpy() - base.valeur.to_numpy()
                slo, shi = ic_blocs(ds, s.depart) if nom != FILTRES[0] else (0.0, 0.0)
                rows.append({"piste": piste, "filtre": nom, "lecture": lect, "n_departs": len(x),
                             "part_ouverte": float(on.mean()),
                             "valeur_ouverte": float(x[on].mean()) if on.any() else np.nan,
                             "valeur_fermee": float(x[~on].mean()) if (~on).any() else np.nan,
                             "valeur_toutes": float(x.mean()), "ecart_ouverte_toutes": float(x[on].mean() - x.mean()),
                             "ecart_ic_bas": lo, "ecart_ic_haut": hi,
                             "reussite_ouverte": float(ok[on].mean()), "reussite_toutes": float(ok.mean()),
                             "delai_ouverte": float(ch.jours_total[on & ok].median()) if (on & ok).any() else np.nan,
                             "delai_toutes": float(ch.jours_total[ok].median()),
                             "suite_filtree": float(s.valeur.mean()), "suite_sans_filtre": float(base.valeur.mean()),
                             "suite_ecart": float(ds.mean()), "suite_ic_bas": slo, "suite_ic_haut": shi,
                             "suite_mieux": float((ds > 1e-12).mean()), "suite_moins": float((ds < -1e-12).mean()),
                             "tentatives_filtree": float(s.n_tentatives.mean()),
                             "tentatives_sans_filtre": float(base.n_tentatives.mean()),
                             "finances_filtree": float(s.n_finances.mean())})
                an = v.depart.dt.year.to_numpy()
                for y in np.unique(an):
                    m = an == y
                    annees.append({"piste": piste, "filtre": nom, "lecture": lect, "annee": int(y),
                                   "n_departs": int(m.sum()), "part_ouverte": float(on[m].mean()),
                                   "ecart_ouverte_toutes": float(x[m & on].mean() - x[m].mean()) if (m & on).any()
                                   else np.nan, "suite_ecart": float(ds[m].mean())})
            ref = roster[(roster.piste == piste) & (roster.lecture == lect)]
            for mes, val_ in (("tentative", x.mean()), ("suite", base.valeur.mean())):
                r = ref[ref.mesure == mes].valeur.iat[0]
                if not np.isclose(val_, r, rtol=1e-5):
                    stop(f"{piste}, {lect}, {mes} : sans filtre, ne redonne pas le roster de D05.6bis")
                ctrl[f"{piste}_{lect}_{mes}_egal_roster"] = round(float(val_), 6)
        print(f"{piste} : fait ({time.time() - t0:.0f} s)", flush=True)
    pd.DataFrame(rows).to_csv(HERE / "resultats_D05_8.csv", index=False, float_format="%.6g")
    pd.DataFrame(annees).to_csv(HERE / "annees_D05_8.csv", index=False, float_format="%.6g")
    ctrl["duree_s"] = round(time.time() - t0)
    (HERE / "controles_D05_8.json").write_text(json.dumps(D01.jsonable(ctrl), ensure_ascii=False, indent=1),
                                               encoding="utf-8")
    figures()
    write_rapport()
    print(f"D05.8 : fait en {ctrl['duree_s']} s ; sorties dans {HERE}")


def figures() -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    j = pd.read_csv(HERE / "indicateurs_D05_8.csv", index_col=0, parse_dates=True)
    FIG.mkdir(parents=True, exist_ok=True)
    ink, muted, grid = "#0b0b0b", "#52514e", "#e4e3df"
    fig, axes = plt.subplots(2, 1, figsize=(14, 7.5), sharex=True)
    x = j.index

    def ombre(ax, on, couleur, label):
        on = on.astype(bool).to_numpy()
        debut = None
        for i, o in enumerate(np.r_[on, False]):
            if o and debut is None:
                debut = i
            elif not o and debut is not None:
                ax.axvspan(x[debut], x[min(i, len(x) - 1)], color=couleur, alpha=0.13, lw=0,
                           label=label if label else None)
                label, debut = None, None

    ax = axes[0]
    ombre(ax, j["T"], "#2a78d6", "filtre T ouvert (tendance haussière)")
    ax.plot(x, j.indice, color="#2a78d6", lw=1.4, label="indice du panier crypto (log)")
    ax.plot(x, j.indice_moyenne, color=muted, lw=1.1, ls="--", label=f"moyenne sur {TENDANCE} jours")
    ax.set_title("Filtre T : tendance haussière du panier crypto", fontsize=10, color=ink)
    ax = axes[1]
    ombre(ax, j["V"], "#1baf7a", "filtre V ouvert (sortie de compression)")
    ax.plot(x, j.atr_court, color="#1baf7a", lw=1.3, label=f"ATR du panier, moyenne {COURT} jours (bps)")
    ax.plot(x, j.atr_long, color="#eb6834", lw=1.3, label=f"moyenne {LONG} jours")
    ax.plot(x, j.atr_mediane_an, color=muted, lw=1.1, ls="--", label=f"médiane sur {ANNEE} jours")
    ax.set_title("Filtre V : volatilité qui sort d'une compression", fontsize=10, color=ink)
    for ax in axes:
        ax.grid(color=grid, lw=0.8)
        ax.set_axisbelow(True)
        for sp in ("top", "right"):
            ax.spines[sp].set_visible(False)
        ax.legend(fontsize=8, loc="upper left", frameon=False, ncol=2)
    fig.tight_layout()
    fig.savefig(FIG / "D05_8_filtres.png", dpi=110)
    plt.close(fig)


fr, sg, pct, n_fr, table = D01.fr, D01.sg, D01.pct, D01.n_fr, D01.table
eur = D055.eur


def write_rapport() -> None:
    res = pd.read_csv(HERE / "resultats_D05_8.csv")
    an = pd.read_csv(HERE / "annees_D05_8.csv")
    ct = json.loads((HERE / "controles_D05_8.json").read_text(encoding="utf-8"))
    narr = HERE / "narratif_D05_8.md"
    out = [narr.read_text(encoding="utf-8") if narr.exists() else "# EXP-D05.8 — rapport (narratif à rédiger)\n",
           "", "---", "", "# Annexes générées (`run_D05_8.py --calcul`, puis `--rapport`)", "",
           f"Calcul du {ct['date']}, commit `{ct['commit']}`, {ct['duree_s']} s.", "", "## A1. Contrôles bloquants (passés)",
           "", f"- Causalité : indicateurs inchangés après coupure des barres postérieures ({ct['causalite_coupures']} "
               "dates).", "- Sans filtre, les pistes redonnent le roster de D05.6bis :"]
    out += [f"  - {k} : {v}." for k, v in ct.items() if k.endswith("_egal_roster")]
    for lect, _, _ in LECTURES:
        g = res[res.lecture == lect]
        out += ["", f"## A2. Par tentative, {lect} ({int(g.n_departs.iat[0])} départs)", "",
                table(["Piste", "Filtre", "Jours ouverts", "Réussite : ouverts ; tous", "Délai médian : ouverts ; tous",
                       "Valeur : ouverts ; fermés ; tous", "Écart ouverts − tous [IC 95 %]"],
                      [[x.piste, x.filtre, pct(x.part_ouverte, 1),
                        f"{pct(x.reussite_ouverte, 1)} ; {pct(x.reussite_toutes, 1)}",
                        f"{fr(x.delai_ouverte, 0)} ; {fr(x.delai_toutes, 0)} j",
                        f"{eur(x.valeur_ouverte)} ; {eur(x.valeur_fermee)} ; {eur(x.valeur_toutes)}",
                        "—" if x.filtre == FILTRES[0] else
                        f"{eur(x.ecart_ouverte_toutes)} [{eur(x.ecart_ic_bas)} ; {eur(x.ecart_ic_haut)}]"]
                       for _, x in g.iterrows()]),
                "", f"## A3. En suite (rachat seulement aux jours ouverts), {lect}", "",
                table(["Piste", "Filtre", "Suite filtrée", "Écart à la suite sans filtre [IC 95 %]",
                       "Départs : mieux ; moins bien", "Tentatives : filtrée ; sans filtre", "Comptes financés"],
                      [[x.piste, x.filtre, eur(x.suite_filtree),
                        "—" if x.filtre == FILTRES[0] else
                        f"{eur(x.suite_ecart)} [{eur(x.suite_ic_bas)} ; {eur(x.suite_ic_haut)}]",
                        "—" if x.filtre == FILTRES[0] else f"{pct(x.suite_mieux, 1)} ; {pct(x.suite_moins, 1)}",
                        f"{fr(x.tentatives_filtree, 1)} ; {fr(x.tentatives_sans_filtre, 1)}", fr(x.finances_filtree, 1)]
                       for _, x in g.iterrows()])]
    g = an[(an.lecture == "12 mois") & (an.filtre != FILTRES[0])]
    ans = sorted(g.annee.unique())
    out += ["", "## A4. Par année de départ, 12 mois : part des jours ouverts ; écart par tentative ; écart en suite", "",
            table(["Piste", "Filtre"] + [str(a) for a in ans],
                  [[p, fl] + [(lambda r: f"{pct(r.part_ouverte, 0)} ; {eur(r.ecart_ouverte_toutes)} ; "
                                         f"{eur(r.suite_ecart)}")(g[(g.piste == p) & (g.filtre == fl) & (g.annee == a)]
                                                                  .iloc[0]) for a in ans]
                   for p in g.piste.unique() for fl in FILTRES[1:]])]
    out += ["", "## A5. Figure", "", "![Filtres](figures/D05_8_filtres.png)", ""]
    (HERE / "rapport_D05_8.md").write_text("\n".join(out) + "\n", encoding="utf-8")


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
