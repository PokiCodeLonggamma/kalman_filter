"""EXP-D05.4 — simulateur de challenge de prop firm : RE-1 version finale sur les six actifs, étalon FTMO Swing, risque
par trade seul facteur. GO du porteur du 2026-10-05 (« GO pour l'Étape 1 : Le Simulateur de Challenge [...] Je valide
ton Cadrage de l'étape 2. Construis le module src/propfirm/ »).

Usage, depuis la racine du dépôt : python experiments/D05_4/run_D05_4.py --calcul | --rapport

Cadrage (fixé avant le calcul, validé par le porteur ; lecture sans seuil de décision)
- QUESTION : avec RE-1 VF telle quelle sur les six actifs, quelle probabilité de réussir P1 (+9 %) puis P2 (+5 %) sans
  franchir −5 % sur une journée ni −10 % au total, en combien de jours, et sur quelle règle échoue-t-on, selon r ?
- DONNÉES : trades de D04.1 (version finale ; fenêtre commune, entrées du 2021-10-01 au 2026-10-01 exclu ; réserve
  levée par `reserve.levee`) ; frais 5 bps aller-retour (or 4 bps) ; swaps non modélisés.
- MÉTHODE : `propfirm.simuler`. Un challenge démarre à chaque minuit CET/CEST de la fenêtre, sur un compte de
  100 000 $ à plat (seuls les trades entrés à partir du départ). Règles FTMO Swing du porteur :
  - objectifs de 9 % puis 5 % ; P2 démarre au minuit qui suit la réussite de P1, sur un compte neuf ;
  - au moins 4 jours de trading ; aucune règle de régularité ; positions du week-end permises ;
  - perte du jour : 5 % du solde initial sous la référence de minuit CET/CEST ; perte totale : 10 %, statique ;
  - levier 1:2 (cryptos) et 1:30 (or). Règle de marge du porteur : une entrée qui dépasserait la marge libre est
    réduite à la marge restante (prorata des entrées simultanées).
  Un facteur : r ∈ {0,05 ; 0,10 ; 0,15 ; 0,20 ; 0,25} %/ATR par trade (plafond 1x par position inchangé). Lecture
  principale : marge plafonnée, borne pessimiste, référence du jour = solde de minuit (FTMO). En regard : sans plafond
  de marge (effet de la marge seule), référence max(solde, équité), capital valorisé aux clôtures, données coupées au
  2026-01-01 (« sans 2026 »).
- CRITÈRE DE LECTURE (sans seuil) : parts de réussite (P1 ; P1 + P2), d'échec par la perte du jour ou la perte totale
  (P1 ou P2) et de challenges en cours ; délai médian et P90 ; par r et par année de départ ; avec et sans 2026 ;
  marge : part des trades réduits ou sautés, dont le top 1 %, et part des états où la marge demandée dépasse
  l'équité ; 8 métriques par r (départ du 2021-10-01) ; IC à 95 % par blocs de mois de départ.
- Conventions fixées avant le calcul :
  - réussite au premier état où capital valorisé − frais de sortie ≥ objectif, avec au moins 4 jours (tout est alors
    clôturé) ;
  - P2 au minuit suivant ; l'échec l'emporte à instant égal ;
  - correction du stop : la perte du stop est cumulée aux extrêmes des autres positions dans sa barre.
- Contrôles bloquants : trades d'ETH et de XRP identiques à D04 ; pour chaque r, sans plafond ni correction, le départ du
  2021-10-01 redonne `portfolio_paths` (chemin entier) et D04.2 (PnL, MDD).
- Biais : toutes les données ont déjà été lues (D04) ; 2026 très favorable ; départs chevauchants (peu de challenges
  indépendants). Lecture descriptive.
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

spec = importlib.util.spec_from_file_location("run_D04_1", ROOT / "experiments" / "D04_1" / "run_D04_1.py")
D041 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(D041)
D04, D02, D01 = D041.D04, D041.D02, D041.D01

from envelope import risk_weights  # noqa: E402
from envelope.daily import daily_from_paths  # noqa: E402
from envelope.portfolio import Leg, portfolio_paths  # noqa: E402
from estimand.stoploss import drawdown_stats  # noqa: E402
from propfirm import FTMO_SWING, LEVIER_FTMO_SWING, challenge, departs_minuit, resume, simuler  # noqa: E402
from reserve import levee  # noqa: E402

FIG = HERE / "figures"
MOTIF = "EXP-D05.4 (porteur, 2026-10-05)"
A, B = D041.WINDOWS["commune"]
RISKS = (5.0, 10.0, 15.0, 20.0, 25.0)                   # bps du capital par ATR14(t)
MARGES = ("sans", "ftmo")
VARIANTES = (("solde", "pessimiste"), ("max", "pessimiste"), ("solde", "valorise"), ("max", "valorise"))
COUPURE = int(pd.Timestamp("2026-01-01", tz=FTMO_SWING.fuseau).value)
COLS = ["capital_valorise", "solde_realise", "capital_pessimiste", "exposition_brute", "positions"]
TOP = 0.01


def stop(msg: str):
    raise SystemExit(f"D05.4, contrôle bloquant : {msg} : arrêt")


def legs(assets: dict, risk_bps: float | None) -> list[Leg]:
    """Jambes de la fenêtre commune ; `risk_bps` None : 1x par position."""
    out = []
    for key in D041.KEYS:
        p = assets[key]
        tr = D041.window_trades(p, A, B)
        w = np.ones(len(tr)) if risk_bps is None else risk_weights(p["atr_bps"][tr.signal_bar.to_numpy()], risk_bps)
        out.append(Leg(key, p["bars"], tr, w, D04.FEES[key][0]))
    return out


def controle(lg: list[Leg], risk: float, dep0: np.ndarray, d042: pd.DataFrame) -> tuple[dict, pd.DataFrame,
                                                                                          pd.DataFrame]:
    """Contrôle bloquant ; rend aussi le chemin non corrigé du départ du 2021-10-01 et `portfolio_paths`."""
    sim = simuler(lg, dep0, levier=LEVIER_FTMO_SWING, correction_stop=False, suivi=0)
    pp, ch = portfolio_paths(lg), sim.chemin
    if not (ch.index.equals(pp.index) and np.allclose(ch[COLS].to_numpy(float), pp[COLS].to_numpy(float), rtol=1e-9,
                                                      atol=1e-12)):
        stop(f"risque {risk:g} bps : le départ du {A} ne redonne pas portfolio_paths")
    pnl = float(ch.capital_valorise.iat[-1] - 1.0)
    mdd = float(drawdown_stats(ch.capital_valorise)["max_drawdown"])
    r = d042[d042.risque_bps_par_atr == risk].iloc[0]
    if not (np.isclose(pnl, r.pnl_compose_r25, rtol=1e-5) and np.isclose(mdd, r.mdd_r25, rtol=1e-5)):
        stop(f"risque {risk:g} bps : PnL ou MDD différents de D04.2")
    return {"etats": len(pp), "pnl": round(pnl, 6), "mdd": round(mdd, 6)}, ch, pp


def approximation(pp: pd.DataFrame, departs: np.ndarray) -> dict:
    """Vérification indépendante, approchée : sur le chemin global de `portfolio_paths` (positions ouvertes au départ
    comprises, frais de sortie et jours minimum ignorés), plus forte baisse de la borne pessimiste depuis chaque minuit
    avant d'atteindre +9 % ; part des départs qui franchissent −10 %."""
    last = pp.groupby(level=0).last()
    t, val = last.index.asi8, last.capital_valorise.to_numpy()
    pes = pp.capital_pessimiste.groupby(level=0).min().to_numpy()
    seuil, plancher = 1.0 + FTMO_SWING.objectifs[0], 1.0 - FTMO_SWING.perte_max
    pires = []
    for s in departs:
        i0 = int(np.searchsorted(t, s, side="right")) - 1
        e0 = val[i0] if i0 >= 0 else 1.0
        rv, rp = val[i0 + 1:] / e0, pes[i0 + 1:] / e0
        hit = np.flatnonzero(rv >= seuil)
        pires.append(rp[:hit[0] if len(hit) else len(rp)].min(initial=1.0))
    pires = np.array(pires)
    k = int(np.argmin(pires))
    return {"approx_part_perte_totale_p1": float(np.mean(pires <= plancher)), "approx_pire_baisse": float(pires[k] - 1.0),
            "approx_pire_depart": str(pd.Timestamp(departs[k], tz="UTC").tz_convert(FTMO_SWING.fuseau).date())}


def ecart_correction(sans: pd.DataFrame, avec: pd.DataFrame) -> dict:
    """Journées UTC (convention de D04) dont la perte pessimiste change avec la correction du stop."""
    da = daily_from_paths(sans.capital_valorise, low=sans.capital_pessimiste)
    db = daily_from_paths(avec.capital_valorise, low=avec.capital_pessimiste)
    d = (db.perte - da.perte).reindex(da.index)
    return {"correction_jours_modifies": int((d.abs() > 1e-12).sum()), "correction_jours": len(da),
            "correction_ecart_max": float(d.min()), "correction_jour_ecart_max": str(d.idxmin().date())}


def executes(lg: list[Leg], sim) -> list[Leg]:
    """Jambes réduites aux trades de taille > 0 du départ suivi (marge plafonnée : trades sautés retirés)."""
    t, out = sim.tailles, []
    for leg in lg:
        j = t.trade[(t.jambe == leg.name) & (t.obtenu > 0)].to_numpy()
        out.append(Leg(leg.name, leg.bars, leg.trades.iloc[j].reset_index(drop=True), np.asarray(leg.weight)[j],
                       leg.cost))
    return out


def stats_marge(sim, lg: list[Leg], assets: dict) -> dict:
    t = sim.tailles
    tr = {leg.name: leg.trades for leg in lg}
    cost = {leg.name: leg.cost for leg in lg}
    net = np.array([(tr[n].ret_gross_bps.iat[j] - cost[n]) / assets[n]["atr_bps"][tr[n].signal_bar.iat[j]]
                    for n, j in zip(t.jambe, t.trade)])
    ratio, obt = (t.obtenu / t.demande).to_numpy(), t.obtenu.to_numpy()
    top = np.argsort(-net)[:max(1, int(np.ceil(TOP * len(t))))]
    ch = sim.chemin
    tenu = ch.positions > 0
    return {"marge_trades": len(t), "marge_part_reduits": float(np.mean(ratio < 1 - 1e-9)),
            "marge_part_sautes": float(np.mean(obt <= 0)), "marge_ratio_moyen": float(ratio.mean()),
            "top1_n": len(top), "top1_part_reduits": float(np.mean(ratio[top] < 1 - 1e-9)),
            "top1_part_sautes": float(np.mean(obt[top] <= 0)), "top1_ratio_moyen": float(ratio[top].mean()),
            "marge_max": float(ch.marge.max()), "part_etats_marge_sup_1": float(np.mean(ch.marge[tenu] > 1 + 1e-12))}


def run_calcul() -> None:
    t0 = time.time()
    ctrl = {"date": pd.Timestamp.now(tz="UTC").strftime("%Y-%m-%d %H:%M UTC"), "commit": D04.git_head(), "motif": MOTIF}
    d042 = pd.read_csv(ROOT / "experiments" / "D04_2" / "resultats_D04_2.csv")
    d042 = d042[d042.axe.isin(["référence", "levier"])]
    rows, met, starts = [], [], []
    with levee(MOTIF):
        assets = D041.load_all()
        ctrl.update(D041.controls(assets))
        departs = departs_minuit(A, B, FTMO_SWING.fuseau)
        ctrl["departs"] = {"n": len(departs), "premier": str(pd.Timestamp(departs[0], tz="UTC")),
                           "dernier": str(pd.Timestamp(departs[-1], tz="UTC"))}
        for risk in RISKS:
            lg = legs(assets, risk)
            ctrl[f"portfolio_paths_et_D04_2_r{risk:g}"], ch0, pp = controle(lg, risk, departs[:1], d042)
            approx = approximation(pp, departs)
            r42 = d042[d042.risque_bps_par_atr == risk].iloc[0]
            for marge in MARGES:
                cap = marge == "ftmo"
                sim = simuler(lg, departs, levier=LEVIER_FTMO_SWING, plafonner=cap, suivi=0)
                for ref, mode in VARIANTES:
                    for fen, coup in (("toute", None), ("sans_2026", COUPURE)):
                        out = challenge(sim, ref, mode, coup)
                        base = {"risque_bps": risk, "marge": marge, "reference": ref, "mode": mode, "fenetre": fen}
                        rows.append({**base, "annee": "toutes", **resume(out)})
                        if (ref, mode) == ("solde", "pessimiste"):
                            for y, sub in out.groupby(out.depart.dt.year):
                                rows.append({**base, "annee": str(y), **resume(sub)})
                            if fen == "toute":
                                starts.append(out.assign(risque_bps=risk, marge=marge))
                sim1 = simuler(legs(assets, None), departs[:1], levier=LEVIER_FTMO_SWING, plafonner=cap, suivi=0)
                m = D041.metrics8(executes(lg, sim), None, sim.chemin, sim1.chemin, assets, A, B)
                m.update(stats_marge(sim, lg, assets))
                dp = daily_from_paths(sim.chemin.capital_valorise, low=sim.chemin.capital_pessimiste)
                m.update({"pire_jour_pessimiste_utc": float(dp.perte.min()),
                          "pire_jour_pessimiste_utc_date": str(dp.perte.idxmin().date()),
                          "pire_jour_pessimiste_D04_2": float(r42.pessimiste_pire),
                          "pire_jour_pessimiste_D04_2_date": r42.pessimiste_pire_jour})
                if not cap:
                    m.update(ecart_correction(ch0, sim.chemin))
                    m.update(approx)
                    m["moteur_part_perte_totale_p1"] = float((challenge(sim).issue_p1 == "perte_max").mean())
                met.append({"risque_bps": risk, "marge": marge, **m})
                print(f"risque {risk:g} bps, marge {marge} : fait ({time.time() - t0:.0f} s)", flush=True)
    pd.DataFrame(rows).to_csv(HERE / "resultats_D05_4.csv", index=False, float_format="%.6g")
    pd.DataFrame(met).to_csv(HERE / "metriques_D05_4.csv", index=False, float_format="%.6g")
    sd = pd.concat(starts, ignore_index=True)
    sd["depart"] = sd.depart.dt.strftime("%Y-%m-%d")
    sd.to_csv(HERE / "departs_D05_4.csv.gz", index=False, float_format="%.4f")
    ctrl["duree_s"] = round(time.time() - t0)
    (HERE / "controles_D05_4.json").write_text(json.dumps(D01.jsonable(ctrl), ensure_ascii=False, indent=1),
                                               encoding="utf-8")
    figures()
    write_rapport()
    print(f"D05.4 : fait en {ctrl['duree_s']} s ; sorties dans {HERE}")


def _sel(res: pd.DataFrame, marge="ftmo", ref="solde", mode="pessimiste", fen="toute", annee="toutes") -> pd.DataFrame:
    return res[(res.marge == marge) & (res.reference == ref) & (res["mode"] == mode) & (res.fenetre == fen)
               & (res.annee == annee)].sort_values("risque_bps")


def figures() -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    res = pd.read_csv(HERE / "resultats_D05_4.csv", dtype={"annee": str})
    FIG.mkdir(parents=True, exist_ok=True)
    ink, muted, grid = "#0b0b0b", "#52514e", "#e4e3df"
    main, sans = _sel(res), _sel(res, marge="sans")
    x = np.arange(len(main))
    labels = [f"{r / 100:.2f}" for r in main.risque_bps]
    fig, axes = plt.subplots(1, 2, figsize=(15, 6.4))
    ax = axes[0]
    parts = [("Réussite P1 + P2", main.p_reussite, "#2a78d6"),
             ("Échec : perte du jour", main.p_echec_p1_jour + main.p_echec_p2_jour, "#eb6834"),
             ("Échec : perte totale", main.p_echec_p1_max + main.p_echec_p2_max, "#1baf7a"),
             ("En cours à la fin des données", main.p_en_cours_p1 + main.p_en_cours_p2, "#c9c8c2")]
    bottom = np.zeros(len(main))
    for name, val, color in parts:
        v = 100 * val.to_numpy()
        ax.bar(x, v, 0.62, bottom=bottom, color=color, edgecolor="white", linewidth=1.5, label=name)
        bottom += v
    ax.plot(x, 100 * sans.p_reussite.to_numpy(), "o--", color=ink, lw=1.5, ms=7,
            label="Réussite P1 + P2 sans plafond de marge")
    ax.set_xticks(x, labels)
    ax.set_xlabel("risque par trade (% du capital par ATR14)", color=muted)
    ax.set_ylabel("% des départs quotidiens", color=muted)
    ax.set_title("Issue du challenge (marge 1:2 plafonnée ; perte du jour depuis le solde de minuit)", fontsize=10,
                 color=ink)
    ax.legend(fontsize=8, loc="upper center", bbox_to_anchor=(0.5, -0.13), ncol=3, frameon=False)
    ax = axes[1]
    ax.plot(x, main.jours_total_med, "o-", color="#2a78d6", lw=2, ms=8, label="médiane, toute la fenêtre")
    ax.plot(x, main.jours_total_p90, "o:", color="#2a78d6", lw=1.5, ms=7, label="P90, toute la fenêtre")
    s26 = _sel(res, fen="sans_2026")
    ax.plot(x, s26.jours_total_med, "s-", color="#eb6834", lw=2, ms=7, label="médiane, sans 2026")
    ax.set_xticks(x, labels)
    ax.set_xlabel("risque par trade (% du capital par ATR14)", color=muted)
    ax.set_ylabel("jours calendaires, du départ à la réussite de P2", color=muted)
    ax.set_title("Délai des challenges réussis", fontsize=10, color=ink)
    ax.legend(fontsize=8, loc="upper center", bbox_to_anchor=(0.5, -0.13), ncol=3, frameon=False)
    for ax in axes:
        ax.grid(color=grid, lw=0.8)
        ax.set_axisbelow(True)
        for s in ("top", "right"):
            ax.spines[s].set_visible(False)
    fig.tight_layout()
    fig.savefig(FIG / "D05_4_challenge.png", dpi=110)
    plt.close(fig)


fr, sg, pct, spct, n_fr, table = D01.fr, D01.sg, D01.pct, D01.spct, D01.n_fr, D01.table


def _p(x) -> str:
    return "—" if pd.isna(x) else pct(x, 1)


def _j(x) -> str:
    return "—" if pd.isna(x) else fr(x, 0)


def write_rapport() -> None:
    res = pd.read_csv(HERE / "resultats_D05_4.csv", dtype={"annee": str})
    met = pd.read_csv(HERE / "metriques_D05_4.csv")
    ct = json.loads((HERE / "controles_D05_4.json").read_text(encoding="utf-8"))
    narr = HERE / "narratif_D05_4.md"
    out = [narr.read_text(encoding="utf-8") if narr.exists() else "# EXP-D05.4 — rapport (narratif à rédiger)\n",
           "", "---", "", "# Annexes générées (`run_D05_4.py --calcul`, puis `--rapport`)", "",
           f"Calcul du {ct['date']}, commit `{ct['commit']}`, {ct['duree_s']} s.", "", "## A1. Contrôles bloquants (passés)",
           ""]
    out += [f"- {k} : {json.dumps(v, ensure_ascii=False)}." for k, v in ct.items()
            if k not in ("date", "commit", "duree_s", "motif")]
    head = ["r (%/ATR)", "Réussite P1 + P2 [IC 95 %]", "Réussite P1", "Échec P1 : jour ; total",
            "Échec P2 : jour ; total", "En cours : P1 ; P2", "Jours P1 : méd. ; P90", "Jours P1 + P2 : méd. ; P90"]

    def rows(sel):
        return [[fr(x.risque_bps / 100, 2), f"{_p(x.p_reussite)} [{_p(x.ic_bas)} ; {_p(x.ic_haut)}]",
                 _p(x.p_reussite_p1), f"{_p(x.p_echec_p1_jour)} ; {_p(x.p_echec_p1_max)}",
                 f"{_p(x.p_echec_p2_jour)} ; {_p(x.p_echec_p2_max)}", f"{_p(x.p_en_cours_p1)} ; {_p(x.p_en_cours_p2)}",
                 f"{_j(x.jours_p1_med)} ; {_j(x.jours_p1_p90)}", f"{_j(x.jours_total_med)} ; {_j(x.jours_total_p90)}"]
                for _, x in sel.iterrows()]

    n_dep = int(_sel(res).n_departs.iat[0])
    sd = pd.read_csv(HERE / "departs_D05_4.csv.gz")
    fin = pd.Timestamp(B)
    horizons = (90, 180, 365)
    dans = []
    for (risk, marge), g in sd.groupby(["risque_bps", "marge"], sort=True):
        vu = g[pd.to_datetime(g.depart) + pd.Timedelta(days=max(horizons)) <= fin]   # mêmes départs pour tous
        dans.append([fr(risk / 100, 2), marge]
                    + [_p(((vu.issue == "reussite") & (vu.jours_total <= n)).mean()) for n in horizons])
    n_vu = len(vu)
    out += ["", f"## A2. Lecture principale : marge 1:2 plafonnée, borne pessimiste, perte du jour depuis le solde de "
                f"minuit CET/CEST ({n_dep} départs)", "", table(head, rows(_sel(res))), "",
            f"## A2 bis. Réussite P1 + P2 en moins de 90, 180 et 365 jours (perte du jour depuis le solde, borne "
            f"pessimiste ; mêmes {n_vu} départs pour les trois horizons : ceux suivis au moins 365 jours, jusqu'au "
            f"{(fin - pd.Timedelta(days=365)).date()})", "",
            table(["r (%/ATR)", "Marge"] + [f"≤ {n} jours" for n in horizons], dans), "",
            "## A3. Même lecture sans plafond de marge (effet de la marge seule)", "",
            table(head, rows(_sel(res, marge="sans"))), ""]
    for ref, mode, titre in (("max", "pessimiste", "référence du jour = max(solde, équité) de minuit"),
                             ("solde", "valorise", "capital valorisé aux clôtures (sans extrêmes de barre)"),
                             ("max", "valorise", "max(solde, équité) et capital valorisé")):
        out += [f"## A4. Variante : {titre} (marge plafonnée)", "", table(head, rows(_sel(res, ref=ref, mode=mode))), ""]
    s26 = _sel(res, fen="sans_2026")
    out += [f"## A5. Données coupées au 2026-01-01 (« sans 2026 », {int(s26.n_departs.iat[0])} départs ; marge "
            "plafonnée, lecture principale)", "", table(head, rows(s26)), ""]
    yrs = sorted(y for y in res.annee.unique() if y != "toutes")
    yr = res[(res.marge == "ftmo") & (res.reference == "solde") & (res["mode"] == "pessimiste")
             & (res.fenetre == "toute")]
    out += ["## A6. Réussite P1 + P2 par année de départ (lecture principale ; en cours entre parenthèses)", "",
            table(["r (%/ATR)"] + [f"{y} ({int(yr[(yr.annee == y)].n_departs.iat[0])} départs)" for y in yrs],
                  [[fr(r / 100, 2)] + [f"{_p(z.p_reussite.iat[0])} ({_p(z.p_en_cours_p1.iat[0] + z.p_en_cours_p2.iat[0])})"
                                       for y in yrs for z in [yr[(yr.risque_bps == r) & (yr.annee == y)]]]
                   for r in RISKS]), ""]
    head8 = ["r ; marge", "PnL : r ; 1x ; bps (1x)", "PF (1x)", "WR", "Espérance ATR ; bps", "MDD : r ; 1x",
             "Trades (/mois)", "Durée médiane", "Part des frais (1x)", "Calmar ; expo. brute max ; P99"]
    out += ["## A7. 8 métriques du portefeuille, départ du 2021-10-01 (5 bps, or 4 bps)", "",
            table(head8, [[f"{fr(x.risque_bps / 100, 2)} ; {x.marge}",
                           f"{spct(x.pnl_compose_r25)} ; {spct(x.pnl_compose_1x)} ; {D02.sgn(x.pnl_bps_1x)}",
                           fr(x.pf_1x, 2), pct(x.wr, 1), f"{sg(x.esperance_atr, 3)} ; {sg(x.esperance_bps, 1)}",
                           f"{pct(x.mdd_r25)} ; {pct(x.mdd_1x)}", f"{n_fr(x.n_trades)} ({fr(x.trades_par_mois, 1)})",
                           f"{fr(x.duree_mediane_barres, 0)} b ; {fr(x.duree_mediane_h, 0)} h", pct(x.part_frais_1x, 0),
                           f"{fr(x.calmar_r25, 2)} ; {fr(x.exposition_brute_max, 2)} ; {fr(x.exposition_brute_P99, 2)}"]
                          for _, x in met.iterrows()]), "",
            "## A8. Marge (départ du 2021-10-01)", "",
            table(["r ; marge", "Trades réduits ; sautés ; taille obtenue / demandée", "Top 1 % : réduits ; sautés ; "
                   "obtenue / demandée", "Marge max / équité", "États où la marge dépasse l'équité"],
                  [[f"{fr(x.risque_bps / 100, 2)} ; {x.marge}",
                    f"{_p(x.marge_part_reduits)} ; {_p(x.marge_part_sautes)} ; {_p(x.marge_ratio_moyen)}",
                    f"{_p(x.top1_part_reduits)} ; {_p(x.top1_part_sautes)} ; {_p(x.top1_ratio_moyen)} "
                    f"({int(x.top1_n)} trades)", fr(x.marge_max, 2), _p(x.part_etats_marge_sup_1)]
                   for _, x in met.iterrows()]), "",
            "## A9. Correction de la borne pessimiste (journées UTC, référence = capital valorisé de 00:00, sans "
            "plafond, départ du 2021-10-01)", "",
            table(["r (%/ATR)", "Pire journée : D04.2 (stop à sa clôture précédente)", "Pire journée : D05.4 (perte du "
                   "stop cumulée)", "Journées modifiées", "Écart le plus grand (jour)"],
                  [[fr(x.risque_bps / 100, 2), f"{spct(x.pire_jour_pessimiste_D04_2, 2)} ({x.pire_jour_pessimiste_D04_2_date})",
                    f"{spct(x.pire_jour_pessimiste_utc, 2)} ({x.pire_jour_pessimiste_utc_date})",
                    f"{int(x.correction_jours_modifies)} sur {int(x.correction_jours)}",
                    f"{fr(100 * x.correction_ecart_max, 2)} pt ({x.correction_jour_ecart_max})"]
                   for _, x in met[met.marge == "sans"].iterrows()]), "",
            "## A10. Vérification indépendante, approchée (sans plafond ; chemin global de `portfolio_paths`, positions "
            "ouvertes au départ comprises, frais de sortie et jours minimum ignorés)", "",
            table(["r (%/ATR)", "Départs franchissant −10 % avant +9 % : approché ; moteur",
                   "Plus forte baisse depuis un minuit, avant +9 % (départ)"],
                  [[fr(x.risque_bps / 100, 2), f"{_p(x.approx_part_perte_totale_p1)} ; {_p(x.moteur_part_perte_totale_p1)}",
                    f"{spct(x.approx_pire_baisse, 2)} ({x.approx_pire_depart})"]
                   for _, x in met[met.marge == "sans"].iterrows()]), "",
            "## A11. Figure", "", "![Challenge](figures/D05_4_challenge.png)", ""]
    (HERE / "rapport_D05_4.md").write_text("\n".join(out) + "\n", encoding="utf-8")


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
