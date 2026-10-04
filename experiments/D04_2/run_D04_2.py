"""EXP-D04.2 — portefeuille complet en un facteur à la fois : composition (un actif retiré à la fois, dont XRP) et levier
(risque par trade), autour de la référence de D04.1. Demande du porteur du 2026-10-04 (« 1) Test sans XRP dans le
portefeuille. 2) Test également plusieurs configurations de portefeuille différent. 3) Test aussi, en OFAT différents
leverage. »), plan validé par le porteur (réponses du 2026-10-04 : levier = risque par trade ; compositions = retrait
d'un actif à la fois).

Usage, depuis la racine du dépôt : python experiments/D04_2/run_D04_2.py --calcul | --rapport

Cadrage (fixé avant le calcul ; lecture sans seuil de décision)
- QUESTION : comment la pire journée, le drawdown et le rendement du portefeuille changent-ils (1) sans XRP et sans
  chacun des autres actifs, (2) quand le risque par trade varie ?
- DONNÉES : celles de D04.1 (version finale de RE-1, séries de D04, réserve levée) ; fenêtre commune, entrées du
  2021-10-01 au 2026-10-01 exclu ; frais 5 bps (or 4 bps).
- MÉTHODE : référence = six actifs, 0,25 % du capital valorisé par ATR14(t) et par trade, ≤ 1x par position (D04.1).
  Un facteur à la fois : axe composition, six portefeuilles à cinq actifs au risque de référence ; axe levier, risque
  de 0,05, 0,10, 0,15, 0,20, 0,25 et 0,30 % par ATR sur les six actifs, plafond de 1x inchangé (il touche moins de
  trades quand le risque baisse : l'or n'est plus plafonné sous ≈ 0,12 %). Mesures de D04.1 (`portfolio_paths`,
  `daily_from_paths`).
- CRITÈRE DE LECTURE : pire journée (capital valorisé, solde réalisé, borne pessimiste) et sa date ; journées sous −3 et
  −4 % ; P1 ; 2026 à part ; MDD, PnL, Calmar, exposition brute ; 8 métriques ; PnL et MDD à 1x par position à côté
  pour l'axe composition.
- Biais : la réserve a été lue ; retirer un actif à la fois évite de choisir une composition après lecture. Lecture
  descriptive, sans valeur de validation.
- Contrôle bloquant : la référence redonne D04.1 (pire journée, PnL, MDD).
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
from reserve import levee  # noqa: E402

FIG = HERE / "figures"
MOTIF = "EXP-D04.2 (porteur, 2026-10-04)"
A, B = D041.WINDOWS["commune"]
REF_RISK = 25.0
RISKS = (5.0, 10.0, 15.0, 20.0, 25.0, 30.0)                 # bps du capital par ATR14(t)
KEYS = D041.KEYS


def stop(msg: str):
    raise SystemExit(f"D04.2, contrôle bloquant : {msg} : arrêt")


def legs(assets: dict, keys, risk_bps: float | None) -> list[Leg]:
    """Jambes de la fenêtre commune ; `risk_bps` None : 1x par position."""
    out = []
    for key in keys:
        p = assets[key]
        tr = D041.window_trades(p, A, B)
        w = np.ones(len(tr)) if risk_bps is None else risk_weights(p["atr_bps"][tr.signal_bar.to_numpy()], risk_bps)
        out.append(Leg(key, p["bars"], tr, w, D04.FEES[key][0]))
    return out


def measure(assets: dict, axis: str, label: str, keys, risk_bps: float, with_1x: bool) -> tuple[dict, list]:
    lg = legs(assets, keys, risk_bps)
    paths = portfolio_paths(lg)
    lg1 = legs(assets, keys, None) if with_1x else lg
    paths1 = portfolio_paths(lg1) if with_1x else paths
    d = {"valorise": daily_from_paths(paths.capital_valorise),
         "solde": daily_from_paths(paths.capital_valorise, reference=paths.solde_realise),
         "pessimiste": daily_from_paths(paths.capital_valorise, low=paths.capital_pessimiste)}
    row = {"axe": axis, "configuration": label, "actifs": " ".join(keys), "risque_bps_par_atr": risk_bps}
    m = D041.metrics8(lg, lg1, paths, paths1, assets, A, B)
    if not with_1x:
        m["pnl_compose_1x"], m["mdd_1x"] = np.nan, np.nan
    row.update(m)
    for ref, x in d.items():
        for tag, y in (("", x), ("_2026", x[x.index >= D04.ts("2026-01-01")])):
            s = D041.distribution(y)
            row.update({f"{ref}{tag}_pire": s["pire"], f"{ref}{tag}_pire_jour": s["pire_jour"], f"{ref}{tag}_P1": s["P1"],
                        f"{ref}{tag}_jours_sous_3pct": s["jours_sous_3pct"], f"{ref}{tag}_jours_sous_4pct": s["jours_sous_4pct"],
                        f"{ref}{tag}_jours": s["jours_en_position"]})
    worst = D041.worst_days(paths, d["valorise"], list(keys), n=3)
    return row, worst


def run_calcul() -> None:
    t0 = time.time()
    rows, worst = [], {}
    ctrl = {"date": pd.Timestamp.now(tz="UTC").strftime("%Y-%m-%d %H:%M UTC"), "commit": D04.git_head()}
    with levee(MOTIF):
        assets = D041.load_all()
        row, w = measure(assets, "référence", "six actifs", KEYS, REF_RISK, True)
        ref = pd.read_csv(ROOT / "experiments" / "D04_1" / "resultats_D04_1.csv")
        r = ref[ref.fenetre == "commune"].iloc[0]
        pire = json.loads((ROOT / "experiments" / "D04_1" / "pires_journees_D04_1.json").read_text(
            encoding="utf-8"))["distribution"]["commune·valorise"]["pire"]
        if not (np.isclose(row["valorise_pire"], pire, rtol=1e-9) and np.isclose(row["pnl_compose_r25"],
                r.pnl_compose_r25, rtol=1e-5) and np.isclose(row["mdd_r25"], r.mdd_r25, rtol=1e-5)):
            stop("la référence ne redonne pas D04.1")
        ctrl["reference_egale_D04_1"] = {"pire_journee": round(row["valorise_pire"], 6), "pnl": round(row["pnl_compose_r25"], 6),
                                         "mdd": round(row["mdd_r25"], 6)}
        rows.append(row)
        worst["référence"] = w
        for out in KEYS:
            keys = [k for k in KEYS if k != out]
            row, w = measure(assets, "composition", f"sans {out}", keys, REF_RISK, True)
            rows.append(row)
            worst[f"sans {out}"] = w
            print(f"sans {out} fait ({time.time() - t0:.0f} s)", flush=True)
        for risk in RISKS:
            if risk == REF_RISK:
                continue
            row, w = measure(assets, "levier", f"risque {risk / 100:.2f} %/ATR", KEYS, risk, False)
            rows.append(row)
            worst[f"risque {risk / 100:.2f}"] = w
            print(f"risque {risk:g} bps fait ({time.time() - t0:.0f} s)", flush=True)
    res = pd.DataFrame(rows)
    res.to_csv(HERE / "resultats_D04_2.csv", index=False, float_format="%.6g")
    (HERE / "pires_journees_D04_2.json").write_text(json.dumps(D01.jsonable(worst), ensure_ascii=False, indent=1),
                                                    encoding="utf-8")
    ctrl["duree_s"] = round(time.time() - t0)
    (HERE / "controles_D04_2.json").write_text(json.dumps(D01.jsonable(ctrl), ensure_ascii=False, indent=1),
                                               encoding="utf-8")
    figures(res)
    write_rapport()
    print(f"D04.2 : {len(res)} configurations en {ctrl['duree_s']} s ; sorties dans {HERE}")


def figures(res: pd.DataFrame) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    FIG.mkdir(parents=True, exist_ok=True)
    fig, axes = plt.subplots(1, 2, figsize=(16, 6))
    lev = res[res.axe.isin(["levier", "référence"])].sort_values("risque_bps_par_atr")
    x = lev.risque_bps_par_atr / 100
    ax = axes[0]
    ax.plot(x, 100 * lev.valorise_pire, "o-", color="#d62728", label="pire journée (capital valorisé)")
    ax.plot(x, 100 * lev.solde_pire, "s--", color="#ff7f0e", label="pire journée (solde réalisé)")
    ax.plot(x, 100 * lev.pessimiste_pire, "^:", color="#8c564b", label="pire journée (borne pessimiste)")
    ax.plot(x, 100 * lev.mdd_r25, "o-", color="k", label="MDD")
    ax.axhline(-4, color="k", lw=0.8, ls="--")
    ax.set_xlabel("risque par trade (% du capital par ATR14)")
    ax.set_ylabel("%")
    ax.set_title("Axe levier : six actifs, 2021-10 → 2026-09", fontsize=10)
    ax.grid(alpha=0.3)
    ax.legend(fontsize=8)
    comp = res[res.axe.isin(["composition", "référence"])]
    ax = axes[1]
    pos = np.arange(len(comp))
    ax.bar(pos - 0.2, 100 * comp.valorise_pire, width=0.4, color="#d62728", label="pire journée (capital valorisé)")
    ax.bar(pos + 0.2, 100 * comp.mdd_r25 / 5, width=0.4, color="#7f7f7f", label="MDD / 5")
    ax.axhline(-4, color="k", lw=0.8, ls="--")
    ax.set_xticks(pos, comp.configuration, rotation=20, fontsize=8)
    ax.set_title("Axe composition : 0,25 %/ATR par trade", fontsize=10)
    ax.grid(alpha=0.3, axis="y")
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(FIG / "D04_2_ofat.png", dpi=110)
    plt.close(fig)


fr, sg, pct, spct, n_fr, table = D01.fr, D01.sg, D01.pct, D01.spct, D01.n_fr, D01.table


def write_rapport() -> None:
    res = pd.read_csv(HERE / "resultats_D04_2.csv")
    pj = json.loads((HERE / "pires_journees_D04_2.json").read_text(encoding="utf-8"))
    ct = json.loads((HERE / "controles_D04_2.json").read_text(encoding="utf-8"))
    narr = HERE / "narratif_D04_2.md"
    out = [narr.read_text(encoding="utf-8") if narr.exists() else "# EXP-D04.2 — rapport (narratif à rédiger)\n",
           "", "---", "", "# Annexes générées (`run_D04_2.py --calcul`, puis `--rapport`)", "",
           f"Calcul du {ct['date']}, commit `{ct['commit']}`, {ct['duree_s']} s.", "", "## A1. Contrôle bloquant (passé)", "",
           f"- reference_egale_D04_1 : {json.dumps(ct['reference_egale_D04_1'], ensure_ascii=False)}.", ""]
    head = ["Configuration", "Pire journée : valorisé ; solde ; pessimiste", "Jours < −3 % ; < −4 % (valorisé ; solde)",
            "P1 (valorisé)", "2026 : pire journée valorisé ; solde", "PnL : config. ; 1x", "MDD : config. ; 1x", "Calmar",
            "Expo. brute max ; P99"]

    def rows(sel):
        return [[x.configuration,
                 f"{spct(x.valorise_pire, 2)} ({x.valorise_pire_jour}) ; {spct(x.solde_pire, 2)} ; {spct(x.pessimiste_pire, 2)}",
                 f"{x.valorise_jours_sous_3pct} ; {x.valorise_jours_sous_4pct} ({x.solde_jours_sous_3pct} ; "
                 f"{x.solde_jours_sous_4pct})", spct(x.valorise_P1, 2),
                 f"{spct(x.valorise_2026_pire, 2)} ; {spct(x.solde_2026_pire, 2)}",
                 f"{spct(x.pnl_compose_r25)} ; {spct(x.pnl_compose_1x) if pd.notna(x.pnl_compose_1x) else '—'}",
                 f"{pct(x.mdd_r25)} ; {pct(x.mdd_1x) if pd.notna(x.mdd_1x) else '—'}", fr(x.calmar_r25, 2),
                 f"{fr(x.exposition_brute_max, 2)} ; {fr(x.exposition_brute_P99, 2)}"] for _, x in sel.iterrows()]

    comp = res[res.axe.isin(["référence", "composition"])]
    lev = res[res.axe.isin(["référence", "levier"])].sort_values("risque_bps_par_atr")
    out += ["## A2. Axe composition (0,25 %/ATR par trade, plafond 1x)", "", table(head, rows(comp)), "",
            "## A3. Axe levier (six actifs, plafond 1x)", "", table(head, rows(lev)), "",
            "## A4. 8 métriques (frais de base)", "",
            table(["Configuration", "PnL : config. ; bps (1x)", "PF (1x)", "WR", "Espérance ATR ; bps", "MDD config.",
                   "Trades (/mois)", "Durée médiane", "Part des frais (1x)"],
                  [[x.configuration, f"{spct(x.pnl_compose_r25)} ; {D02.sgn(x.pnl_bps_1x)}", fr(x.pf_1x, 2), pct(x.wr, 1),
                    f"{sg(x.esperance_atr, 3)} ; {sg(x.esperance_bps, 1)}", pct(x.mdd_r25),
                    f"{n_fr(x.n_trades)} ({fr(x.trades_par_mois, 1)})",
                    f"{fr(x.duree_mediane_barres, 0)} b ; {fr(x.duree_mediane_h, 0)} h", pct(x.part_frais_1x, 0)]
                   for _, x in pd.concat([comp, lev[lev.axe == "levier"]]).iterrows()]), "",
            "## A5. Trois pires journées par configuration (capital valorisé de 00:00)", "",
            table(["Configuration", "1re", "2e", "3e"],
                  [[k] + [f"{x['jour']} {spct(x['perte'], 2)} (solde {spct(x['perte_ref_solde'], 2)})" for x in v]
                   for k, v in pj.items()]), "",
            "## A6. Figure", "", "![OFAT](figures/D04_2_ofat.png)", ""]
    (HERE / "rapport_D04_2.md").write_text("\n".join(out) + "\n", encoding="utf-8")


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
        write_rapport()


if __name__ == "__main__":
    main()
