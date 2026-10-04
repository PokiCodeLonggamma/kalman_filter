"""EXP-D04.1 — pire journée du portefeuille complet : RE-1 version finale sur BTC, SOL, AVAX, or, ETH et XRP en même
temps, sur un capital commun. Demande du porteur du 2026-10-04 (« Mesure la pire journée du portefeuille complet »),
après EXP-D04.

Usage, depuis la racine du dépôt : python experiments/D04_1/run_D04_1.py --calcul | --rapport

Cadrage (fixé avant le calcul ; lecture sans seuil de décision)
- QUESTION : quelle est la pire journée UTC du capital commun quand la version finale de RE-1 tourne en même temps sur
  les six actifs de D04, et combien de journées approchent la limite de perte journalière de 4 % citée par le porteur ?
- DONNÉES : séries et trades de D04 (version finale, tous les candidats, verrou continu ; réserve levée par
  `reserve.levee`). Lecture principale : période commune des six actifs, entrées du 2021-10-01 au 2026-10-01 exclu (AVAX
  coté dès le 2021-09-30 ; or jusqu'au 2026-09-24). Lecture complémentaire : actifs disponibles dès le 2017-08-16 (BTC,
  ETH, XRP, or ; SOL et AVAX à leur cotation), pour couvrir les krachs de 2017-2021 (dont mars 2020).
- MÉTHODE : capital commun (`envelope.portfolio_paths`, règles de `portfolio_equity` de D03) : à l'entrée, notionnel =
  0,25 % du capital valorisé par ATR14(t), ≤ 1x par position ; frais 5 bps (or 4 bps) à la sortie ; capital valorisé
  à chaque clôture de 30 min puis après chaque sortie et entrée. Journée UTC ]J 00:00, J + 1 00:00] ; perte du jour =
  plus bas / référence − 1, la référence étant (a) le capital valorisé à 00:00, (b) le solde réalisé à 00:00 ; borne
  pessimiste : toutes les positions à l'extrême défavorable de la même barre. Lecture à 1x par position à côté.
- CRITÈRE DE LECTURE : pire journée et ses contributions par actif ; quantiles des pertes journalières ; nombre de
  journées sous −1, −2, −3 et −4 % (la limite de 4 % du porteur sert de repère) ; pire journée de chaque actif seul
  sur la même période ; exposition brute ; 8 métriques du portefeuille.
- Contrôles bloquants : trades d'ETH et de XRP identiques à D04 (nombre, espérance) ; une jambe seule dans
  `portfolio_paths` redonne ses pertes journalières de `envelope.daily_losses`.
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

spec = importlib.util.spec_from_file_location("run_D04", ROOT / "experiments" / "D04" / "run_D04.py")
D04 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(D04)
D03, D02, D01 = D04.D03, D04.D02, D04.D01

from envelope import risk_weights  # noqa: E402
from envelope.daily import daily_from_paths, daily_losses  # noqa: E402
from envelope.portfolio import Leg, portfolio_paths  # noqa: E402
from estimand.stoploss import TRADE_COLUMNS, drawdown_stats  # noqa: E402
from reserve import levee  # noqa: E402
from utils.data_loader import meta_path  # noqa: E402

BPS = 1e4
FIG = HERE / "figures"
MOTIF = "EXP-D04.1 (porteur, 2026-10-04)"
KEYS = ("BTC", "SOL", "AVAX", "XAU", "ETH", "XRP")
WINDOWS = {"commune": ("2021-10-01", "2026-10-01"), "longue": ("2017-08-16", "2026-10-01")}
LIMITS = (-0.01, -0.02, -0.03, -0.04)


def stop(msg: str):
    raise SystemExit(f"D04.1, contrôle bloquant : {msg} : arrêt")


def ts(x) -> pd.Timestamp:
    return D04.ts(x)


def load_all() -> dict:
    out = {}
    for key in KEYS:
        if key in D04.PAIRS:
            csv, end = D04.ethxrp_csv(key), D04.END
        else:
            csv = D04.EXTENDED[key]
            meta = json.loads(meta_path(csv).read_text(encoding="utf-8"))
            end = ts(meta.get("fin_exclue", D04.END))
        p = D04.prepare(key, csv, end)
        p["s"] = D04.final_series(p, None, None)
        out[key] = p
        print(f"{key} prêt", flush=True)
    return out


def window_trades(p: dict, a: str, b: str) -> pd.DataFrame:
    return D03.subset(p["s"], p["bars"], a, b)["trades"][TRADE_COLUMNS].reset_index(drop=True)


def legs_for(assets: dict, a: str, b: str, one_x: bool = False) -> list[Leg]:
    legs = []
    for key, p in assets.items():
        tr = window_trades(p, a, b)
        if not len(tr):
            continue
        w = np.ones(len(tr)) if one_x else risk_weights(p["atr_bps"][tr.signal_bar.to_numpy()], 25.0)
        legs.append(Leg(key, p["bars"], tr, w, D04.FEES[key][0]))
    return legs


def controls(assets: dict) -> dict:
    out = {}
    ref = pd.read_csv(ROOT / "experiments" / "D04" / "resultats_D04.csv")
    for key in D04.PAIRS:
        tr = assets[key]["s"]["trades"]
        a = assets[key]["atr_bps"][tr.signal_bar.to_numpy()]
        e = float(np.mean((tr.ret_gross_bps.to_numpy() - 5.0) / a))
        r = ref[(ref.cle == key) & (ref.frais_bps == 5.0)].iloc[0]
        if len(tr) != r.n_trades or not np.isclose(e, r.esperance_atr, rtol=1e-5):
            stop(f"{key} : trades différents de D04")
        out[f"{key}_identique_a_D04"] = {"trades": len(tr), "esperance_atr": round(e, 6)}
    leg = legs_for({"ETH": assets["ETH"]}, *WINDOWS["commune"])[0]
    pa = portfolio_paths([leg])
    da = daily_from_paths(pa.capital_valorise)
    db = daily_losses(leg.bars, leg.trades, leg.cost, leg.weight)
    common = da.index.intersection(db.index)
    if len(common) != len(db) or not np.allclose(np.minimum(da.perte[common], 0), np.minimum(db.perte[common], 0),
                                                 rtol=1e-12, atol=1e-15):
        stop("une jambe seule ne redonne pas ses pertes journalières")
    out["jambe_seule_ETH_pertes_journalieres_identiques"] = int(len(common))
    return out


def worst_days(paths: pd.DataFrame, d: pd.DataFrame, names: list[str], n: int = 5) -> list[dict]:
    """Les n pires journées (référence : capital valorisé à 00:00) et la contribution de chaque actif au plus bas."""
    out = []
    pnl = paths[[f"pnl_{k}" for k in names]]
    dpess = daily_from_paths(paths.capital_valorise, low=paths.capital_pessimiste)
    dbal = daily_from_paths(paths.capital_valorise, reference=paths.solde_realise)
    for day in d.perte.nsmallest(n).index:
        before = paths.index <= day
        start_pnl = pnl[before].iloc[-1] if before.any() else pnl.iloc[0] * 0.0
        inday = (paths.index > day) & (paths.index <= day + pd.Timedelta(days=1))
        sub = paths[inday]
        k = int(np.argmin(sub.capital_valorise.to_numpy()))
        low_t = sub.index[k]
        contrib = (pnl[inday].iloc[k] - start_pnl) / d.debut[day]
        out.append({"jour": str(day.date()), "perte": float(d.perte[day]), "perte_pessimiste": float(dpess.perte[day]),
                    "perte_ref_solde": float(dbal.perte[day]), "heure_du_plus_bas": str(low_t),
                    "positions_au_plus_bas": int(sub.positions.iat[k]),
                    "exposition_brute_max_du_jour": float(sub.exposition_brute.max()),
                    "contributions": {c.removeprefix("pnl_"): float(v) for c, v in contrib.items() if abs(v) > 1e-12}})
    return out


def distribution(d: pd.DataFrame) -> dict:
    x = d.perte.to_numpy()
    return {"jours_en_position": len(x), "pire": float(x.min()), "pire_jour": str(d.perte.idxmin().date()),
            "P1": float(np.quantile(x, 0.01)), "P5": float(np.quantile(x, 0.05)), "mediane": float(np.median(x)),
            **{f"jours_sous_{int(-100 * l)}pct": int((x < l).sum()) for l in LIMITS}}


def metrics8(legs: list[Leg], legs1x: list[Leg], paths: pd.DataFrame, paths1x: pd.DataFrame, assets: dict,
             a: str, b: str) -> dict:
    """8 métriques du portefeuille : PnL et MDD sur le capital commun (0,25 %/ATR ; 1x par position) ; PF, WR,
    espérance, durée et part des frais sur l'ensemble des trades (1x, poolés)."""
    rows = []
    for leg in legs:
        p = assets[leg.name]
        tr = leg.trades
        a_bps = p["atr_bps"][tr.signal_bar.to_numpy()]
        t = p["bars"].time
        hours = ((t.iloc[tr.exit_bar.to_numpy()].to_numpy() - t.iloc[tr.entry_bar.to_numpy()].to_numpy())
                 / np.timedelta64(1, "h"))
        rows.append(pd.DataFrame({"gross": tr.ret_gross_bps.to_numpy(dtype=float), "fee": leg.cost, "atr": a_bps,
                                  "bars": (tr.exit_bar - tr.entry_bar).to_numpy(), "hours": hours}))
    x = pd.concat(rows, ignore_index=True)
    net = x.gross - x.fee
    ny = (ts(b) - ts(a)) / pd.Timedelta(days=365.25)
    closes = paths.capital_valorise
    mdd, mdd1 = drawdown_stats(closes)["max_drawdown"], drawdown_stats(paths1x.capital_valorise)["max_drawdown"]
    pnl = float(closes.iat[-1] - 1.0)
    cagr = (1.0 + pnl) ** (1.0 / ny) - 1.0
    return {"pnl_compose_r25": pnl, "pnl_compose_1x": float(paths1x.capital_valorise.iat[-1] - 1.0),
            "pnl_bps_1x": float(net.sum()), "pf_1x": float(net[net > 0].sum() / -net[net < 0].sum()),
            "wr": float((net > 0).mean()), "esperance_atr": float((net / x.atr).mean()), "esperance_bps": float(net.mean()),
            "mdd_r25": float(mdd), "mdd_1x": float(mdd1), "n_trades": len(x), "trades_par_mois": len(x) / (12 * ny),
            "duree_mediane_barres": float(np.median(x.bars)), "duree_mediane_h": float(np.median(x.hours)),
            "part_frais_1x": float(x.fee.sum() / x.gross.sum()) if x.gross.sum() > 0 else np.nan,
            "calmar_r25": float(cagr / abs(mdd)) if mdd < 0 else np.nan, "annees": ny,
            "exposition_brute_max": float(paths.exposition_brute.max()),
            "exposition_brute_P99": float(np.quantile(paths.exposition_brute[paths.positions > 0], 0.99)),
            "part_etats_exposition_sup_1": float((paths.exposition_brute[paths.positions > 0] > 1.0).mean()),
            "positions_max": int(paths.positions.max())}


def run_calcul() -> None:
    t0 = time.time()
    res, days_out, worst, dist, alone, curves = [], [], {}, {}, {}, {}
    ctrl = {"date": pd.Timestamp.now(tz="UTC").strftime("%Y-%m-%d %H:%M UTC"), "commit": D04.git_head()}
    with levee(MOTIF):
        assets = load_all()
        ctrl.update(controls(assets))
        for wname, (a, b) in WINDOWS.items():
            legs, legs1 = legs_for(assets, a, b), legs_for(assets, a, b, one_x=True)
            names = [leg.name for leg in legs]
            paths, paths1 = portfolio_paths(legs), portfolio_paths(legs1)
            d = {"valorise": daily_from_paths(paths.capital_valorise),
                 "solde": daily_from_paths(paths.capital_valorise, reference=paths.solde_realise),
                 "pessimiste": daily_from_paths(paths.capital_valorise, low=paths.capital_pessimiste),
                 "valorise_1x": daily_from_paths(paths1.capital_valorise)}
            for ref, x in d.items():
                dist[f"{wname}·{ref}"] = distribution(x)
                y = x[x.index >= ts("2026-01-01")]
                if len(y):
                    dist[f"{wname}·{ref}·2026"] = distribution(y)
                days_out.append(x.assign(fenetre=wname, reference=ref).reset_index())
            worst[wname] = worst_days(paths, d["valorise"], names)
            alone[wname] = {}
            for leg in legs:
                dl = daily_losses(leg.bars, leg.trades, leg.cost, leg.weight)
                alone[wname][leg.name] = {"pire": float(dl.perte.min()), "jour": str(dl.perte.idxmin().date()),
                                          "trades": len(leg.trades)}
            m = metrics8(legs, legs1, paths, paths1, assets, a, b)
            res.append({"fenetre": wname, "debut": a, "fin": b, "actifs": " ".join(names), **m})
            curves[wname] = (paths.capital_valorise.groupby(level=0).last(), d["valorise"].perte)
            print(f"fenêtre {wname} faite ({time.time() - t0:.0f} s)", flush=True)
    pd.DataFrame(res).to_csv(HERE / "resultats_D04_1.csv", index=False, float_format="%.6g")
    pd.concat(days_out, ignore_index=True).to_csv(HERE / "journees_D04_1.csv.gz", index=False, float_format="%.8g")
    (HERE / "pires_journees_D04_1.json").write_text(json.dumps(D01.jsonable({"portefeuille": worst, "distribution": dist,
                                                                             "actif_seul": alone}),
                                                               ensure_ascii=False, indent=1), encoding="utf-8")
    ctrl["duree_s"] = round(time.time() - t0)
    (HERE / "controles_D04_1.json").write_text(json.dumps(D01.jsonable(ctrl), ensure_ascii=False, indent=1),
                                               encoding="utf-8")
    figures(curves)
    write_rapport()
    print(f"D04.1 : fait en {ctrl['duree_s']} s ; sorties dans {HERE}")


def figures(curves: dict) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    FIG.mkdir(parents=True, exist_ok=True)
    fig, axes = plt.subplots(2, 2, figsize=(16, 9), sharex="col")
    for col, (wname, (eq, loss)) in enumerate(curves.items()):
        axes[0, col].plot(eq.index, 100 * (eq.to_numpy() - 1.0), lw=1.0, color="k")
        axes[0, col].set_title(f"Portefeuille, fenêtre {wname} : capital valorisé (0,25 %/ATR par trade)", fontsize=10)
        axes[0, col].set_ylabel("PnL composé (%)")
        axes[1, col].bar(loss.index, 100 * loss.clip(upper=0).to_numpy(), width=1.0, color="#d62728")
        axes[1, col].axhline(-4, color="k", lw=0.8, ls="--")
        axes[1, col].set_title("Perte du jour UTC (référence : capital valorisé à 00:00) ; repère −4 %", fontsize=10)
        axes[1, col].set_ylabel("%")
        for ax in axes[:, col]:
            ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(FIG / "D04_1_portefeuille.png", dpi=110)
    plt.close(fig)


fr, sg, pct, spct, n_fr, table = D01.fr, D01.sg, D01.pct, D01.spct, D01.n_fr, D01.table


def write_rapport() -> None:
    res = pd.read_csv(HERE / "resultats_D04_1.csv")
    pj = json.loads((HERE / "pires_journees_D04_1.json").read_text(encoding="utf-8"))
    ct = json.loads((HERE / "controles_D04_1.json").read_text(encoding="utf-8"))
    narr = HERE / "narratif_D04_1.md"
    out = [narr.read_text(encoding="utf-8") if narr.exists() else "# EXP-D04.1 — rapport (narratif à rédiger)\n",
           "", "---", "", "# Annexes générées (`run_D04_1.py --calcul`, puis `--rapport`)", "",
           f"Calcul du {ct['date']}, commit `{ct['commit']}`, {ct['duree_s']} s.", "", "## A1. Contrôles bloquants (passés)",
           ""]
    out += [f"- {k} : {json.dumps(v, ensure_ascii=False)}." for k, v in ct.items() if k not in ("date", "commit", "duree_s")]
    out += ["", "## A2. 8 métriques du portefeuille (5 bps, or 4 bps)", "",
            table(["Fenêtre (actifs)", "PnL : 0,25 %/ATR ; 1x par position ; bps (1x)", "PF (1x)", "WR",
                   "Espérance ATR ; bps", "MDD : 0,25 %/ATR ; 1x", "Trades (/mois)", "Durée médiane",
                   "Part des frais (1x)", "Calmar ; exposition brute max ; P99"],
                  [[f"{x.fenetre} {x.debut} → {x.fin} ({x.actifs})",
                    f"{spct(x.pnl_compose_r25)} ; {spct(x.pnl_compose_1x)} ; {D02.sgn(x.pnl_bps_1x)}", fr(x.pf_1x, 2),
                    pct(x.wr, 1), f"{sg(x.esperance_atr, 3)} ; {sg(x.esperance_bps, 1)}",
                    f"{pct(x.mdd_r25)} ; {pct(x.mdd_1x)}", f"{n_fr(x.n_trades)} ({fr(x.trades_par_mois, 1)})",
                    f"{fr(x.duree_mediane_barres, 0)} b ; {fr(x.duree_mediane_h, 0)} h", pct(x.part_frais_1x, 0),
                    f"{fr(x.calmar_r25, 2)} ; {fr(x.exposition_brute_max, 2)} ; {fr(x.exposition_brute_P99, 2)}"]
                   for _, x in res.iterrows()]), ""]
    head = ["Lecture", "Jours en position", "Pire journée (date)", "P1 ; P5 ; médiane",
            "Jours sous −1 % ; −2 % ; −3 % ; −4 %"]
    rows = [[k, n_fr(v["jours_en_position"]), f"{spct(v['pire'], 2)} ({v['pire_jour']})",
             f"{spct(v['P1'], 2)} ; {spct(v['P5'], 2)} ; {spct(v['mediane'], 2)}",
             f"{v['jours_sous_1pct']} ; {v['jours_sous_2pct']} ; {v['jours_sous_3pct']} ; {v['jours_sous_4pct']}"]
            for k, v in pj["distribution"].items()]
    out += ["## A3. Pertes journalières du portefeuille", "",
            "Références : `valorise` = capital valorisé à 00:00 UTC ; `solde` = solde réalisé à 00:00 ; `pessimiste` = "
            "toutes les positions à l'extrême défavorable de la même barre ; `valorise_1x` = 1x par position.", "",
            table(head, rows), ""]
    for wname, days in pj["portefeuille"].items():
        out += [f"## A4. Les cinq pires journées, fenêtre {wname} (0,25 %/ATR)", "",
                table(["Jour", "Perte : valorisée ; pessimiste ; sur solde", "Plus bas (UTC) ; positions ; expo. max",
                       "Contributions au plus bas (% du capital de 00:00)"],
                      [[x["jour"], f"{spct(x['perte'], 2)} ; {spct(x['perte_pessimiste'], 2)} ; "
                                   f"{spct(x['perte_ref_solde'], 2)}",
                        f"{x['heure_du_plus_bas'][11:16]} ; {x['positions_au_plus_bas']} ; "
                        f"{fr(x['exposition_brute_max_du_jour'], 2)}",
                        " ; ".join(f"{k} {spct(v, 2)}" for k, v in sorted(x["contributions"].items(),
                                                                            key=lambda kv: kv[1]))]
                       for x in days]), ""]
    out += ["## A5. Pire journée de chaque actif seul (même fenêtre, mêmes trades, 0,25 %/ATR)", "",
            table(["Fenêtre"] + list(pj["actif_seul"]["commune"]),
                  [[w] + [f"{spct(v['pire'], 2)} ({v['jour']})" for v in a.values()]
                   for w, a in pj["actif_seul"].items() if list(a) == list(pj["actif_seul"]["commune"])]
                  + [[w] + [f"{k} {spct(v['pire'], 2)} ({v['jour']})" for k, v in a.items()]
                     for w, a in pj["actif_seul"].items() if list(a) != list(pj["actif_seul"]["commune"])]), "",
            "## A6. Figure", "", "![Portefeuille](figures/D04_1_portefeuille.png)", ""]
    (HERE / "rapport_D04_1.md").write_text("\n".join(out) + "\n", encoding="utf-8")


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
