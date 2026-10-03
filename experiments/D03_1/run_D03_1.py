"""EXP-D03.1 — viabilité et sécurité de RE-1 version finale : stop catastrophe de 4 ATR, glissement des stops de F3,
entrée retardée d'une barre ; BTC 2015-2025 et SOL. Demande du porteur du 2026-10-03 (`RESEARCH_LOG.md`, EXP-D03.1).

Usage, depuis la racine du dépôt : python experiments/D03_1/run_D03_1.py --calcul | --rapport

Règles fixées avant le calcul (porteur, 2026-10-03 ; le moteur n'est pas rouvert, chaque test est une lecture)
- Données et moteur : ceux de D03 (BTC/USD Bitstamp, panne de 2015 retirée, entrées 2015-2025 ; SOL/USD Coinbase,
  tout l'historique jusqu'au 2025-12-31) ; RE-1 gelée (seuils BTC gelés, R0 = 100, frontière 0,85, H = 26, verrou 26,
  F2b sans stop, F3 stop SL-B à l'extremum du segment) ; 5 bps (10 bps en lecture) ; 0,25 % du capital par ATR14(t),
  levier ≤ 1x ; PnL et MDD à 1x à côté.
- Action 1, stop catastrophe : niveau open[t + 1] − sens · 4 · ATR14(t) (SL-A de C02) greffé sur tous les trades, F2b et
  F3 ; pour F3, le premier des deux stops touché sort (`nearest_levels`) ; exécution du noyau (niveau, ou ouverture
  au-delà en cas de gap). Le verrou ne change pas : mêmes entrées que RE-1.
- Action 2a, glissement : les trades de F3 sortis sur stop sont exécutés 0,5 · ATR14(t) plus loin (`slip_stops`).
- Action 2b, latence : toutes les entrées retardées d'une barre (open[t + 2]), même horizon de 26 barres, même stop,
  même verrou relatif ; un niveau déjà franchi à l'entrée retardée fait sortir aussitôt, brut nul (`delayed_trades`).
- Lecture supplémentaire, signalée comme telle : les trois ensemble (stop 4 ATR, retard d'une barre, glissement de
  0,5 ATR sur toutes les sorties sur stop).
- Lecture (sans seuil ; « coût marginal » laissé au porteur) : 8 métriques ; écart apparié par mois (règles de D02) ;
  effet trade par trade sur les mêmes signaux ; trades coupés par le stop catastrophe et ce qu'ils auraient fait
  sans lui ; pire perte d'un trade en capital ; top 1 % et 5 % touchés.
- Contrôles bloquants : ceux de D03 (RE-1 gelée BTC = D02, SOL = D01, portefeuille d'une jambe = dépôt) ; retard nul,
  glissement nul et stop catastrophe infini redonnent RE-1 gelée trade par trade.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import re
import subprocess
import sys
import time
from pathlib import Path
from types import SimpleNamespace

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "src"))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


D03 = _load("run_D03", ROOT / "experiments" / "D03" / "run_D03.py")
D02, D01 = D03.D02, D03.D01

from envelope import atr_stop_levels, effect_ci  # noqa: E402
from envelope.stress import delayed_trades, nearest_levels, slip_stops  # noqa: E402
from estimand.stoploss import TRADE_COLUMNS  # noqa: E402
from optimization import candidates, run_trades  # noqa: E402
from strategy import LEG_ATR_P50_BTC, NIS_Z100_P75_BTC  # noqa: E402

BPS = 1e4
FIG = HERE / "figures"
FEES = (5.0, 10.0)
K_CAT, K_SLIP, DELAY = 4.0, 0.5, 1
RE1, CAT, SLIP, LATE, ALL = ("RE-1 gelée", "Stop catastrophe 4 ATR", "Glissement 0,5 ATR (stops de F3)",
                             "Entrée retardée d'une barre", "Les trois ensemble")
NAMES = [RE1, CAT, SLIP, LATE, ALL]
PERIODS = {"BTC": {"2015-2025": ("2015-01-01", "2026-01-01"), "2015-2019": ("2015-01-01", "2020-01-01"),
                   "2020-2025": ("2020-01-01", "2026-01-01")},
           "SOL": {"2021-2025": ("2021-06-01", "2026-01-01")}}


def stop(msg: str):
    raise SystemExit(f"D03.1, contrôle bloquant : {msg} : arrêt")


def ts(x: str) -> pd.Timestamp:
    return pd.Timestamp(x, tz="UTC")


def variants(p: dict, start: str, end: str) -> tuple[dict, dict]:
    """Les cinq séries d'un actif sur les mêmes candidats de RE-1 gelée."""
    bars, atr_bps = p["bars"], p["atr_bps"]
    t, s, lv = candidates(p["tab"], LEG_ATR_P50_BTC, NIS_Z100_P75_BTC, 0.85, ts(start), ts(end))
    atr_px = atr_bps[t] * bars.close.to_numpy(dtype=float)[t] / BPS          # ATR14(t) en prix
    cat = atr_stop_levels(bars, t, s, atr_px, K_CAT)
    lv_cat = nearest_levels(s, lv, cat)
    base = run_trades(bars, t, s, 26, lv)
    out = {RE1: base, CAT: run_trades(bars, t, s, 26, lv_cat), SLIP: slip_stops(base, atr_bps, K_SLIP),
           LATE: delayed_trades(bars, t, s, 26, lv, DELAY),
           ALL: slip_stops(delayed_trades(bars, t, s, 26, lv_cat, DELAY), atr_bps, K_SLIP)}
    if not delayed_trades(bars, t, s, 26, lv, 0).equals(base) or not slip_stops(base, atr_bps, 0.0).equals(base):
        stop("retard nul ou glissement nul différent de RE-1 gelée")
    far = nearest_levels(s, lv, atr_stop_levels(bars, t, s, atr_px, 1e6))       # jamais touché
    if not run_trades(bars, t, s, 26, far).equals(base):
        stop("stop catastrophe infini différent de RE-1 gelée")
    fam = pd.Series(np.where(np.isnan(lv), "F2b", "F3"), index=t)
    series = {n: {"trades": tr, "cands": (t, s, lv), "fam": fam} for n, tr in out.items()}
    chosen = pd.Series(np.isfinite(cat) & (lv_cat == cat), index=t)            # stop catastrophe le plus proche
    return series, {"chosen_cat": chosen, "fam": fam}


def aligned(var: pd.DataFrame, base: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Mêmes signaux ; entrée de la référence prêtée à la variante (grappe mensuelle d'entrée commune)."""
    common = np.intersect1d(var.signal_bar.to_numpy(), base.signal_bar.to_numpy())
    v = var.set_index("signal_bar").loc[common].reset_index()
    b = base.set_index("signal_bar").loc[common].reset_index()
    v["entry_bar"], v["side"] = b.entry_bar.to_numpy(), b.side.to_numpy()
    return v[TRADE_COLUMNS], b[TRADE_COLUMNS]


def capital_r(tr: pd.DataFrame, atr_bps, fee: float) -> np.ndarray:
    a = np.asarray(atr_bps, dtype=float)[tr.signal_bar.to_numpy(dtype=np.int64)]
    return np.minimum(1.0, 25.0 / a) * (tr.ret_gross_bps.to_numpy(dtype=float) - fee) / BPS


def diagnostics(p: dict, series: dict, info: dict) -> dict:
    atr = p["atr_bps"]
    base, cat = series[RE1]["trades"], series[CAT]["trades"]
    sb = base.signal_bar.to_numpy()
    net_b = (base.ret_gross_bps.to_numpy() - 5.0) / atr[sb]
    order = np.argsort(-net_b, kind="stable")
    top1 = set(sb[order[:int(np.ceil(0.01 * len(sb) - 1e-9))]])
    top5 = set(sb[order[:int(np.ceil(0.05 * len(sb) - 1e-9))]])
    if not np.array_equal(cat.signal_bar.to_numpy(), sb):
        stop("stop catastrophe : entrées différentes de RE-1 gelée")
    hit = cat.stop.to_numpy() & info["chosen_cat"].reindex(sb).to_numpy(dtype=bool)
    net_c = (cat.ret_gross_bps.to_numpy() - 5.0) / atr[sb]
    fam = info["fam"].reindex(sb).to_numpy()
    out = {"stop_catastrophe": {
        "touches": int(hit.sum()), "touches_F2b": int((hit & (fam == "F2b")).sum()),
        "touches_F3": int((hit & (fam == "F3")).sum()), "part_trades": float(hit.mean()),
        "esperance_atr_touches_avec": float(net_c[hit].mean()) if hit.any() else np.nan,
        "esperance_atr_touches_sans": float(net_b[hit].mean()) if hit.any() else np.nan,
        "part_touches_finis_positifs_sans": float((net_b[hit] > 0).mean()) if hit.any() else np.nan,
        "top1_coupes": int(sum(x in top1 for x in sb[hit])), "top5_coupes": int(sum(x in top5 for x in sb[hit])),
        "pire_trade_capital_avant": float(capital_r(base, atr, 5.0).min()),
        "pire_trade_capital_apres": float(capital_r(cat, atr, 5.0).min()),
        "pire_trade_1x_bps_avant": float(base.ret_gross_bps.min() - 5.0),
        "pire_trade_1x_bps_apres": float(cat.ret_gross_bps.min() - 5.0)}}
    slip = series[SLIP]["trades"]
    stopped = base.stop.to_numpy()
    out["glissement"] = {"trades_stoppes_F3": int(stopped.sum()), "part_trades": float(stopped.mean()),
                         "cout_moyen_atr_par_trade": float(K_SLIP * stopped.mean())}
    late = series[LATE]["trades"]
    instant = (late.exit_bar.to_numpy() == late.entry_bar.to_numpy())
    out["retard"] = {"trades": len(late), "sorties_immediates": int(instant.sum()),
                     "signaux_perdus_en_fin": int(len(base) - len(late))}
    atr_s = pd.Series(atr, index=np.arange(len(atr)))
    out["effets_trade_par_trade"] = {}
    for n in NAMES[1:]:
        v, b = aligned(series[n]["trades"], base)
        out["effets_trade_par_trade"][n] = {**effect_ci(v, b, p["bars"], atr_s, n_boot=D03.D02.N_BOOT), "trades": len(v)}
        for f in ("F2b", "F3"):
            m = info["fam"].reindex(v.signal_bar.to_numpy()).to_numpy() == f
            d = (v.ret_gross_bps.to_numpy() - b.ret_gross_bps.to_numpy())[m] / atr[v.signal_bar.to_numpy()[m]]
            out["effets_trade_par_trade"][n][f"effet_atr_{f}"] = float(d.mean()) if m.any() else np.nan
    return out


def run_calcul() -> None:
    t0 = time.time()
    commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, capture_output=True,
                            text=True).stdout.strip()
    btc, sol = D03.prepare("BTC"), D03.prepare("SOL")
    s_btc, s_sol = D03.re1(btc, *D03.P_BTC), D03.re1(sol, None, None)
    ctrl = {"date": pd.Timestamp.now(tz="UTC").strftime("%Y-%m-%d %H:%M UTC"), "commit": commit}
    ctrl.update(D03.controls(btc, sol, s_btc, s_sol))
    rows, comps, diags, curves = [], [], {}, {}
    for key, p, ref in (("BTC", btc, s_btc), ("SOL", sol, s_sol)):
        full = list(PERIODS[key].values())[0]
        series, info = variants(p, *full)
        if not series[RE1]["trades"][TRADE_COLUMNS].equals(ref["trades"][TRADE_COLUMNS]):
            stop(f"{key} : RE-1 gelée de D03.1 différente de celle de D03")
        diags[key] = diagnostics(p, series, info)
        data = SimpleNamespace(bars=p["bars"], atr_bps=p["atr_bps"])
        curves[key] = {n: D02.equity_points(series[n], data, 5.0) for n in (RE1, CAT, LATE, ALL)}
        for per, (a, b) in PERIODS[key].items():
            for fee in FEES:
                label = f"{key} {per} · {fee:g} bps"
                for n, s in series.items():
                    m, _ = D03.measure(label, n, s, p, fee, a, b)
                    rows.append(m)
                comps += D03.compare_rows(label, p, series, RE1, fee, a, b)
        print(f"{key} fait ({time.time() - t0:.0f} s)", flush=True)
    ctrl["controles_D03_1"] = "retard nul, glissement nul et stop catastrophe infini redonnent RE-1 gelée (BTC, SOL)"
    res = pd.DataFrame(rows)
    lead = ["actif", "variante", "frais_bps", "annees", "debut", "fin"]
    res[lead + [c for c in res.columns if c not in lead]].to_csv(HERE / "resultats_D03_1.csv", index=False,
                                                                 float_format="%.6g")
    pd.DataFrame(comps).to_csv(HERE / "comparaisons_D03_1.csv", index=False, float_format="%.6g")
    (HERE / "diagnostics_D03_1.json").write_text(json.dumps(D01.jsonable(diags), ensure_ascii=False, indent=1),
                                                 encoding="utf-8")
    ctrl["duree_s"] = round(time.time() - t0)
    ctrl["comparaisons"] = len(comps)
    (HERE / "controles_D03_1.json").write_text(json.dumps(D01.jsonable(ctrl), ensure_ascii=False, indent=1),
                                               encoding="utf-8")
    figures(curves)
    write_rapport()
    print(f"D03.1 : {len(res)} lignes, {len(comps)} comparaisons en {ctrl['duree_s']} s ; sorties dans {HERE}")


def figures(curves: dict) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    FIG.mkdir(parents=True, exist_ok=True)
    style = {RE1: ("k", 1.8), CAT: ("#d62728", 1.3), LATE: ("#1f77b4", 1.1), ALL: ("#ff7f0e", 1.1)}
    fig, axes = plt.subplots(1, 2, figsize=(16, 6))
    for ax, (key, cur) in zip(axes, curves.items()):
        for n, eq in cur.items():
            c, lw = style[n]
            ax.step(eq.index, 100 * (eq.to_numpy() - 1.0), where="post", color=c, lw=lw, label=n)
        ax.axhline(0, color="k", lw=0.5)
        ax.set_title(f"{key} : capital valorisé aux sorties (0,25 %/ATR, 5 bps)", fontsize=10)
        ax.set_ylabel("PnL composé (%)")
        ax.grid(alpha=0.3)
        ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(FIG / "D03_1_capital.png", dpi=110)
    plt.close(fig)


fr, sg, pct, spct, n_fr, ci, table = D01.fr, D01.sg, D01.pct, D01.spct, D01.n_fr, D01.ci, D01.table


def write_rapport() -> None:
    res = pd.read_csv(HERE / "resultats_D03_1.csv")
    cp = pd.read_csv(HERE / "comparaisons_D03_1.csv")
    dg = json.loads((HERE / "diagnostics_D03_1.json").read_text(encoding="utf-8"))
    ct = json.loads((HERE / "controles_D03_1.json").read_text(encoding="utf-8"))
    narr = HERE / "narratif_D03_1.md"
    out = [narr.read_text(encoding="utf-8") if narr.exists() else "# EXP-D03.1 — rapport (narratif à rédiger)\n",
           "", "---", "", "# Annexes générées (`run_D03_1.py --calcul`, puis `--rapport`)", "",
           f"Calcul du {ct['date']}, commit `{ct['commit']}`, {ct['duree_s']} s ; {ct['comparaisons']} comparaisons "
           "appariées publiées.", "", "## A1. Contrôles bloquants (passés)", ""]
    out += [f"- {k} : " + re.sub(r"\b(\d)(\d{3})\b", r"\1 \2", str(v)) + "." for k, v in ct.items()
            if k not in ("date", "commit", "duree_s", "comparaisons", "donnees")]
    for i, key in enumerate(("BTC", "SOL"), start=2):
        d = dg[key]
        c, g, r = d["stop_catastrophe"], d["glissement"], d["retard"]
        out += ["", f"## A{i}. {key}", "",
                f"- Stop catastrophe : {c['touches']} trades touchés ({pct(c['part_trades'], 1)} ; F2b {c['touches_F2b']}, "
                f"F3 {c['touches_F3']}) ; leur espérance {sg(c['esperance_atr_touches_avec'], 2)} ATR avec le stop, "
                f"{sg(c['esperance_atr_touches_sans'], 2)} sans ; {pct(c['part_touches_finis_positifs_sans'], 0)} auraient "
                f"fini positifs sans lui ; top 1 % coupés : {c['top1_coupes']}, top 5 % : {c['top5_coupes']} ; pire trade "
                f"en capital (0,25 %/ATR) {spct(c['pire_trade_capital_avant'], 2)} → {spct(c['pire_trade_capital_apres'], 2)}"
                f" ; pire trade à 1x {sg(c['pire_trade_1x_bps_avant'], 0)} → {sg(c['pire_trade_1x_bps_apres'], 0)} bps.",
                f"- Glissement : {g['trades_stoppes_F3']} trades de F3 stoppés ({pct(g['part_trades'], 1)}) ; coût moyen "
                f"{fr(g['cout_moyen_atr_par_trade'], 3)} ATR par trade.",
                f"- Retard : {n_fr(r['trades'])} trades, dont {r['sorties_immediates']} sorties immédiates (niveau déjà "
                f"franchi) ; {r['signaux_perdus_en_fin']} signal perdu en fin de série.", "",
                "**Effet trade par trade sur les mêmes signaux (variante − RE-1 gelée)**", "",
                table(["Variante", "Trades", "Effet ATR [IC]", "Effet bps [IC]", "F2b ; F3 (ATR)"],
                      [[n, n_fr(v["trades"]), ci(v["effet_atr"], v["effet_atr_lo"], v["effet_atr_hi"], 3),
                        ci(v["effet_bps"], v["effet_bps_lo"], v["effet_bps_hi"], 1),
                        f"{sg(v['effet_atr_F2b'], 3)} ; {sg(v['effet_atr_F3'], 3)}"]
                       for n, v in d["effets_trade_par_trade"].items()]), ""]
        for per in PERIODS[key]:
            for fee in FEES:
                label = f"{key} {per} · {fee:g} bps"
                x = res[res.actif == label].copy()
                x["variante"] = pd.Categorical(x.variante, NAMES, ordered=True)
                out += [f"**{label}**", "", D02.annex_metrics(x.sort_values("variante"), label, fee), "",
                        D02.annex_comparisons(cp, label, fee, f"contre {RE1}"), ""]
    out += ["## A4. Figure", "", "![Capital](figures/D03_1_capital.png)", ""]
    (HERE / "rapport_D03_1.md").write_text("\n".join(out) + "\n", encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--calcul", action="store_true", help="contrôles, cinq séries par actif, rapport")
    ap.add_argument("--rapport", action="store_true", help="régénère rapport_D03_1.md depuis les sorties")
    args = ap.parse_args()
    if args.rapport:
        write_rapport()
        return
    if not args.calcul:
        raise SystemExit("EXP-D03.1 : préciser --calcul ou --rapport")
    run_calcul()


if __name__ == "__main__":
    main()
