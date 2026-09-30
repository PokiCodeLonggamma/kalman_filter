"""EXP-D01.5 — sensibilité OFAT de RE-1 à l'horizon H seul : or (CFD XAU/USD), ETF SPY et XLE.

Usage, depuis la racine du dépôt : python experiments/D01_5/run_D01_5.py [--rapport]
  (défaut)  : contrôles bloquants (empreintes des séries = audit de D01 ; H = 26 identique à D01 ; entrées figées à
              H = 26 identiques à RE-1), puis RE-1 à chaque H de la grille → resultats_D01_5.csv, annuel_D01_5.csv,
              diagnostics_D01_5.json, controles_D01_5.json, figures/, rapport_D01_5.md ;
  --rapport : régénère rapport_D01_5.md (narratif_D01_5.md rédigé à la main, puis annexes générées) sans recalcul.
Données : celles de D01 (experiments/D01/donnees_D01.py), inchangées.

Cadrage (porteur, 2026-09-30)
- QUESTION : une translation de H seul, tout le reste de RE-1 figé (moteur v2.1 par défaut, R0 = 100, seuils BTC
  gelés, F2b sans stop, F3 SL-B à l'extremum, cooldown), corrige-t-elle les faiblesses de D01 : frais trop lourds en ATR
  sur l'or à H = 26 (brut +0,24 ATR, frais 0,26 ATR) ; exposition de SPY et XLE aux gaps d'ouverture (H = 26 barres de
  séance = deux nuits) ?
- PERTINENCE POUR LE FILTRE AKF : H est le seul paramètre de RE-1 lié au temps, et il est compté en barres de la série.
  Sur l'or (23 h sur 24, 5 jours sur 7), H = 26 dure 13 h ; sur les ETF (13 barres par séance), deux séances. Le
  déclencheur juge la cinématique à t ; H décide quand ce jugement est encaissé, donc combien de frais, de dérive de
  l'actif et de nuits entrent dans chaque trade.
- CE QUE LE PROTOCOLE MESURE RÉELLEMENT : pour chaque H de la grille du porteur (XAU {26, 48, 72, 96, 130} ; SPY et XLE
  {6, 13, 26, 65, 130}), à 4 bps :
  - la course séquentielle de RE-1 (une position à la fois, cooldown ; la population de trades change avec H) : les
    8 métriques nettes, l'espérance nette et brute en ATR et en bps avec IC par grappes mensuelles, les frais en ATR, le
    capital, le MDD et le Calmar à 0,25 % par ATR14(t) et à 1x, Long/Short et timing/dérive, F2b/F3, années ;
  - l'effet apparié de H sur les entrées figées de RE-1 à H = 26 (mêmes trades, seule la sortie change) : il sépare
    l'effet de la sortie de celui de la population (convention depuis C02 : apparié avant séquentiel) ;
  - les gaps (définitions de D01 bis) : part des trades exposés, écarts traversés, décomposition du brut en écarts et
    séance, stops exécutés en gap et leur dépassement. Sur les ETF : nuits et week-ends ; sur l'or : pause quotidienne
    et week-ends.
- CE QU'IL NE PERMET PAS DE CONCLURE : aucun H n'est retenu ni figé. Le meilleur des cinq H, choisi après coup sur
  2020-2025, surestime l'espérance (sélection dans l'échantillon) : la validation hors échantillon d'un H est l'objet de
  D02 (WFO). Pas de hold-out. Coûts de portage absents (swap du CFD, emprunt des ETF vendus à découvert). Grilles
  différentes selon l'actif (choix du porteur).

Règle de lecture (fixée avant le calcul)
- Descriptif : RE-1 inchangée, aucun paramètre figé, aucun actif retiré.
- Un avantage se lit sur l'IC 95 % par grappes mensuelles, en ATR et en bps : borne basse > 0. Une espérance ponctuelle
  > 0 dont l'IC contient 0 n'est pas un avantage établi.
- La réponse à H se lit sur la courbe entière (croissante, plateau, pic isolé), pas sur la meilleure valeur.
- Chaque variation est lue avec son effet apparié (entrées figées) et sa décomposition timing/dérive : une tenue plus
  longue expose davantage à la tendance de l'actif sur 2020-2025.
- Gaps : barre d'ouverture = barre précédée d'un intervalle de plus de 30 min ; trade exposé = au moins une barre
  d'ouverture dans ]entrée ; sortie] ; dépassement d'un stop exécuté en gap = sens · (niveau − prix d'exécution) /
  ATR14(t) ; coût des dépassements = leur somme / nombre de trades.
"""
from __future__ import annotations

import importlib.util
import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "src"))

import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from envelope import equity_curve_sized, risk_weights, route_levels  # noqa: E402
from envelope.metrics import _entry_month, effect_ci  # noqa: E402
from envelope.stops import _candidates  # noqa: E402
from estimand.stoploss import TRADE_COLUMNS, apply_stop  # noqa: E402
from strategy import FLOOR, H, RISK_BPS, RULES, metrics, run_re1, sample_years  # noqa: E402
from utils.data_loader import meta_path  # noqa: E402


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


D01 = _load("run_D01", ROOT / "experiments" / "D01" / "run_D01.py")
fr, sg, pct, spct, n_fr, ci, table = D01.fr, D01.sg, D01.pct, D01.spct, D01.n_fr, D01.ci, D01.table

FEE = 4.0
GRILLES = {"XAU": (26, 48, 72, 96, 130), "SPY": (6, 13, 26, 65, 130), "XLE": (6, 13, 26, 65, 130)}
NOMS = {"XAU": "CFD or XAU/USD (HistData)", "SPY": "ETF SPY (Alpaca, séance régulière)",
        "XLE": "ETF XLE (Alpaca, séance régulière)"}
GAPS = {"XAU": "pause quotidienne et week-ends", "SPY": "nuits et week-ends", "XLE": "nuits et week-ends"}
FIG = HERE / "figures"
N_BOOT = 2000
#: Colonnes de resultats_D01.csv que la course à H = 26 doit redonner (contrôle bloquant).
COLS_D01 = ["n_trades", "esperance_bps", "esperance_bps_lo", "esperance_bps_hi", "esperance_atr", "esperance_atr_lo",
            "esperance_atr_hi", "pnl_compose", "mdd_valorise", "pf", "wr", "pnl_compose_r25", "mdd_valorise_r25",
            "calmar_r25", "calmar_1x", "part_stop", "n_F2b", "n_F3", "esperance_atr_F2b", "esperance_atr_F3",
            "timing_atr", "annees_atr_pos", "duree_mediane_h"]


# ── Mesures ─────────────────────────────────────────────────────────────────────
def frozen_exit(p: dict, ref: pd.DataFrame, fam: pd.Series, horizon: int) -> pd.DataFrame:
    """Entrées figées : les trades de RE-1 à H = 26, sortis à `horizon` barres avec la même enveloppe (niveau du stop de
    F3 inchangé). Les positions peuvent se superposer : lecture par trade seulement (pas de capital)."""
    bars, atlas = p["bars"], p["atlas"]
    t, s = ref.signal_bar.to_numpy(), ref.side.to_numpy(dtype=np.int64)
    seg = pd.Series(atlas.prev_seg_len.to_numpy(), index=atlas.bar_index.to_numpy()).reindex(t).to_numpy()
    level = route_levels(bars, t, s, np.asarray(p["atr"], dtype=float)[t], seg, fam.reindex(t).to_numpy(), RULES,
                         FLOOR)
    ok, t2, s2, e, x, dist = _candidates(bars, t, s, horizon, level, "frozen_exit")
    if not ok.all():
        raise SystemExit("entrées figées : un trade de référence n'est plus exécutable : arrêt")
    with np.errstate(invalid="ignore"):
        out = apply_stop(bars, e, x, s2, dist)
    out = out.reset_index(drop=True)
    out["signal_bar"] = t2
    return out[TRADE_COLUMNS]


def structure_checks(key: str, h: int, tr: pd.DataFrame, n_bars: int) -> None:
    """Une position à la fois avec cooldown (signal suivant ≥ signal + H) ; entrée à open[t + 1] ; sortie à H barres
    hors stop, sauf troncature à la dernière barre de 2025."""
    t = tr.signal_bar.to_numpy()
    free = ~tr.stop.to_numpy(dtype=bool) & (tr.exit_bar.to_numpy() < n_bars - 1)
    if not ((np.diff(t) >= h).all() and (tr.entry_bar.to_numpy() == t + 1).all()
            and ((tr.exit_bar - tr.entry_bar).to_numpy()[free] == h).all()):
        raise SystemExit(f"{key} H = {h} : structure des trades non conforme : arrêt")


def gap_fields(g: dict | None, n_trades: int) -> dict:
    if not g:
        return {}
    st = g["stops"]
    cost = (st["depassement_atr_moyen"] or 0.0) * st["n_en_gap"] / n_trades
    return {"part_expose_gap": g["part_trades_traversant_un_ecart"],
            "gaps_par_trade_moyenne": g["ecarts_traverses_par_trade"]["moyenne"],
            "gaps_par_trade_P50": g["ecarts_traverses_par_trade"]["P50"],
            "brut_log_atr": g["brut_log_atr"]["moyenne"],
            "gaps_atr": g["composante_ecarts_atr"]["moyenne"], "gaps_atr_lo": g["composante_ecarts_atr"]["lo"],
            "gaps_atr_hi": g["composante_ecarts_atr"]["hi"],
            "seance_atr": g["composante_seance_atr"]["moyenne"], "seance_atr_lo": g["composante_seance_atr"]["lo"],
            "seance_atr_hi": g["composante_seance_atr"]["hi"],
            "stops_n": st["n"], "stops_en_gap": st["n_en_gap"], "depassement_moyen_atr": st["depassement_atr_moyen"],
            "depassement_P90_atr": st["depassement_atr_P90"], "cout_depassements_atr_par_trade": cost}


def run_asset(key: str, audit: dict, d01_res: pd.DataFrame, d01_diag: dict) -> tuple[list, list, dict, dict, dict]:
    if audit[key]["doc"]["sha256"] != json.loads(meta_path(D01.ASSETS[key]["csv"]).read_text(encoding="utf-8"))["sha256"]:
        raise SystemExit(f"{key} : empreinte du CSV différente de l'audit de D01 : arrêt")
    p = D01.prepare(key)
    bars, atr_bps = p["bars"], p["atr_bps"]
    n_cand, ny = int(p["m"]["R2"].sum()), sample_years(bars)
    atr_of = lambda tr: atr_bps.reindex(tr.signal_bar.to_numpy()).to_numpy(dtype=float)  # noqa: E731
    ref, fam_ref = run_re1(bars, p["atlas"], p["atr"], p["m"], horizon=H)
    if not frozen_exit(p, ref, fam_ref, H).equals(ref):
        raise SystemExit(f"{key} : entrées figées à H = 26 différentes de RE-1 : arrêt")
    months_ref = _entry_month(ref, bars)
    rows, years, diags, curves = [], [], {}, {}
    ctrl = {"sha256": audit[key]["doc"]["sha256"], "candidats": n_cand, "annees": ny,
            "rendement_actif_echantillon": float(bars.close.iat[-1] / bars.close.iat[0] - 1.0)}
    for h in GRILLES[key]:
        tr, fam = run_re1(bars, p["atlas"], p["atr"], p["m"], horizon=h)
        structure_checks(key, h, tr, len(bars))
        m, y = metrics(tr, bars, atr_bps, FEE, n_cand, fam, ny)
        a = atr_of(tr)
        months = _entry_month(tr, bars)
        gross = tr.ret_gross_bps.to_numpy(dtype=float)
        v = (gross - FEE) / a
        b_m, b_lo, b_hi = D01.boot_ci(gross / a, months)
        hours = (bars.time.iloc[tr.exit_bar.to_numpy()].to_numpy()
                 - bars.time.iloc[tr.entry_bar.to_numpy()].to_numpy()) / np.timedelta64(1, "h")
        fz = frozen_exit(p, ref, fam_ref, h)
        vf = (fz.ret_gross_bps.to_numpy(dtype=float) - FEE) / atr_of(fz)
        f_m, f_lo, f_hi = D01.boot_ci(vf, months_ref)
        eff = effect_ci(fz, ref, bars, atr_bps, N_BOOT)
        g = D01.gap_trades(p, tr, fam, v, months)
        m.update({"actif": key, "H": h, "frais_bps": FEE, "debut": str(bars.time.iat[0]), "fin": str(bars.time.iat[-1]),
                  "duree_mediane_h": float(np.median(hours)), "duree_h_P90": float(np.percentile(hours, 90)),
                  "brut_atr": b_m, "brut_atr_lo": b_lo, "brut_atr_hi": b_hi, "frais_atr": float((FEE / a).mean()),
                  "n_annees": len(y), "part_communs_h26": float(np.isin(tr.signal_bar, ref.signal_bar).mean()),
                  "fige_net_atr": f_m, "fige_net_atr_lo": f_lo, "fige_net_atr_hi": f_hi,
                  "fige_net_bps": float(fz.ret_gross_bps.mean() - FEE), "fige_part_stop": float(fz.stop.mean()),
                  **{f"fige_{k}": val for k, val in eff.items()}, **gap_fields(g, len(tr))})
        rows.append(m)
        y.insert(0, "actif", key)
        y.insert(1, "H", h)
        years.append(y)
        diags[str(h)] = {"gaps": g, "stops_par_famille": {
            k: int((tr.stop.to_numpy(dtype=bool) & (fam.reindex(tr.signal_bar.to_numpy()).to_numpy() == k)).sum())
            for k in ("F2b", "F3")}}
        curves[h] = equity_curve_sized(bars, tr, FEE, risk_weights(a, RISK_BPS))
        if h == H:
            ctrl["h26_identique_d01"] = check_h26(key, m, g, d01_res, d01_diag)
        print(f"{key} H = {h:3d} : {len(tr):4d} trades, nette {m['esperance_atr']:+.3f} ATR "
              f"[{m['esperance_atr_lo']:+.3f} ; {m['esperance_atr_hi']:+.3f}], brute {b_m:+.3f}")
    return rows, years, diags, ctrl, curves


def check_h26(key: str, m: dict, g: dict | None, d01_res: pd.DataFrame, d01_diag: dict) -> dict:
    """La course à H = 26 redonne resultats_D01.csv et les gaps de diagnostics_D01.json (chaîne inchangée)."""
    row = d01_res[(d01_res.actif == key) & (d01_res.frais_bps == FEE)].iloc[0]
    worst = 0.0
    for c in COLS_D01:
        x, y = float(m[c]), float(row[c])
        if not np.isclose(x, y, rtol=1e-5, atol=1e-9):
            raise SystemExit(f"{key} H = 26 : {c} = {x} contre {y} dans D01 : arrêt")
        worst = max(worst, abs(x - y) / max(abs(y), 1e-12))
    gd = d01_diag[key][f"{FEE:g}"]["gaps_ouverture"]
    pairs = [(g["part_trades_traversant_un_ecart"], gd["part_trades_traversant_un_ecart"]),
             (g["stops"]["n_en_gap"], gd["stops"]["n_en_gap"]),
             (g["stops"]["depassement_atr_moyen"], gd["stops"]["depassement_atr_moyen"]),
             (g["composante_ecarts_atr"]["moyenne"], gd["composante_ecarts_atr"]["moyenne"])]
    if not all(np.isclose(a, b, rtol=1e-9) for a, b in pairs):
        raise SystemExit(f"{key} H = 26 : gaps différents de D01 : arrêt")
    return {"metriques_comparees": len(COLS_D01), "ecart_relatif_max": worst, "gaps_compares": len(pairs)}


def run_main() -> None:
    t0 = time.time()
    audit = json.loads((ROOT / "experiments" / "D01" / "audit_D01.json").read_text(encoding="utf-8"))
    d01_res = pd.read_csv(ROOT / "experiments" / "D01" / "resultats_D01.csv")
    d01_diag = json.loads((ROOT / "experiments" / "D01" / "diagnostics_D01.json").read_text(encoding="utf-8"))
    rows, years, diags, ctrl, curves = [], [], {}, {"frais_bps": FEE, "grilles": GRILLES, "actifs": {}}, {}
    for key in GRILLES:
        r, y, d, c, cv = run_asset(key, audit, d01_res, d01_diag)
        rows += r
        years += y
        diags[key], ctrl["actifs"][key], curves[key] = d, c, cv
    res = pd.DataFrame(rows)
    lead = ["actif", "H", "frais_bps", "annees", "debut", "fin"]
    res = res[lead + [c for c in res.columns if c not in lead]]
    ctrl["duree_s"] = round(time.time() - t0)
    res.to_csv(HERE / "resultats_D01_5.csv", index=False, float_format="%.6g")
    pd.concat(years, ignore_index=True).to_csv(HERE / "annuel_D01_5.csv", index=False, float_format="%.6g")
    (HERE / "diagnostics_D01_5.json").write_text(json.dumps(D01.jsonable(diags), ensure_ascii=False, indent=1),
                                                 encoding="utf-8")
    (HERE / "controles_D01_5.json").write_text(json.dumps(D01.jsonable(ctrl), ensure_ascii=False, indent=1),
                                               encoding="utf-8")
    FIG.mkdir(parents=True, exist_ok=True)
    figures(res, curves)
    write_report()
    print(f"D01.5 : {len(res)} lignes en {ctrl['duree_s']} s ; résultats, figures et rapport dans {HERE}")


# ── Figures ─────────────────────────────────────────────────────────────────────
def figures(res: pd.DataFrame, curves: dict) -> None:
    fig, axes = plt.subplots(1, 3, figsize=(16, 4.8))
    for ax, key in zip(axes, GRILLES):
        r = res[res.actif == key].sort_values("H")
        x = np.arange(len(r))
        e = r.esperance_atr.to_numpy()
        ax.errorbar(x - 0.1, e, yerr=[e - r.esperance_atr_lo, r.esperance_atr_hi - e], fmt="o-", color=D01.COLORS[key],
                    capsize=3, label="nette, course séquentielle [IC 95 %]")
        ax.plot(x - 0.1, r.brut_atr, "s--", color=D01.COLORS[key], alpha=0.5, label="brute, course séquentielle")
        f = r.fige_net_atr.to_numpy()
        ax.errorbar(x + 0.1, f, yerr=[f - r.fige_net_atr_lo, r.fige_net_atr_hi - f], fmt="^:", color="k", capsize=3,
                    alpha=0.7, label="nette, entrées figées de H = 26 [IC 95 %]")
        ax.axhline(0, color="k", lw=0.8)
        ax.set_xticks(x)
        ax.set_xticklabels([f"H = {h}\n{fr(dh, 0)} h" for h, dh in zip(r.H, r.duree_mediane_h)])
        ax.set_title(f"{NOMS[key]}, 4 bps")
        ax.set_ylabel("espérance par trade (ATR14(t))")
        ax.grid(alpha=0.3)
    axes[0].legend(fontsize=8, loc="upper left")
    fig.suptitle("EXP-D01.5 — RE-1, H seul varie (durée calendaire médiane sous chaque H)")
    fig.tight_layout()
    fig.savefig(FIG / "H_D01_5.png", dpi=120)
    plt.close(fig)
    fig, axes = plt.subplots(1, 3, figsize=(16, 4.8))
    cmap = plt.get_cmap("viridis")
    for ax, key in zip(axes, GRILLES):
        hs = GRILLES[key]
        for i, h in enumerate(hs):
            c = curves[key][h]
            ax.plot(c.index, c.to_numpy(), color=cmap(i / (len(hs) - 1)), lw=1.6 if h == H else 1.0,
                    label=f"H = {h}" + (" (RE-1)" if h == H else ""))
        ax.set_yscale("log")
        ax.axhline(1, color="k", lw=0.8)
        ax.set_title(f"{key} : capital à 0,25 %/ATR, 4 bps")
        ax.grid(alpha=0.3)
        ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(FIG / "capital_D01_5.png", dpi=120)
    plt.close(fig)


# ── Rapport ─────────────────────────────────────────────────────────────────────
def frais_cell(r) -> str:
    return D01.frais_cell(r)


LIGNES = [
    ("Durée médiane : barres ; calendaire (P90)",
     lambda r: f"{fr(r['duree_mediane'], 0)} ; {fr(r['duree_mediane_h'], 0)} h ({fr(r['duree_h_P90'], 0)} h)"),
    ("Trades (par mois) ; stoppés ; communs avec H = 26",
     lambda r: f"{n_fr(r['n_trades'])} ({fr(r['trades_par_mois'], 1)}) ; {pct(r['part_stop'], 0)} ; "
               f"{pct(r['part_communs_h26'], 0)}"),
    ("PnL net : 0,25 %/ATR ; 1x", lambda r: f"{spct(r['pnl_compose_r25'])} ; {spct(r['pnl_compose'])}"),
    ("PF : 1x ; pondéré", lambda r: f"{fr(r['pf'], 2)} ; {fr(r['pf_r25'], 2)}"),
    ("WR", lambda r: pct(r["wr"])),
    ("**Espérance nette ATR [IC 95 %]**",
     lambda r: "**" + ci(r["esperance_atr"], r["esperance_atr_lo"], r["esperance_atr_hi"], 3) + "**"),
    ("Espérance nette bps [IC 95 %]", lambda r: ci(r["esperance_bps"], r["esperance_bps_lo"], r["esperance_bps_hi"], 1)),
    ("Espérance brute ATR [IC 95 %] ; frais ATR",
     lambda r: f"{ci(r['brut_atr'], r['brut_atr_lo'], r['brut_atr_hi'], 3)} ; {fr(r['frais_atr'], 3)}"),
    ("Part des frais : 1x ; pondérée", frais_cell),
    ("MDD : 0,25 %/ATR ; 1x", lambda r: f"{pct(r['mdd_valorise_r25'])} ; {pct(r['mdd_valorise'])}"),
    ("Calmar : 0,25 %/ATR ; 1x", lambda r: f"{fr(r['calmar_r25'], 2)} ; {fr(r['calmar_1x'], 2)}"),
    ("Long ; Short (ATR)", lambda r: f"{sg(r['long_atr'], 3)} ; {sg(r['short_atr'], 3)}"),
    ("Timing ATR [IC 95 %] ; dérive",
     lambda r: f"{ci(r['timing_atr'], r['timing_atr_lo'], r['timing_atr_hi'], 3)} ; {sg(r['derive_atr'], 3)}"),
    ("F2b : n ; ATR · F3 : n ; ATR",
     lambda r: f"{n_fr(r['n_F2b'])} ; {sg(r['esperance_atr_F2b'], 3)} · {n_fr(r['n_F3'])} ; "
               f"{sg(r['esperance_atr_F3'], 3)}"),
    ("Années à espérance > 0 (ATR)", lambda r: f"{int(r['annees_atr_pos'])}/{int(r['n_annees'])}"),
    ("Entrées figées de H = 26 : nette ATR [IC]",
     lambda r: ci(r["fige_net_atr"], r["fige_net_atr_lo"], r["fige_net_atr_hi"], 3)),
    ("Entrées figées : effet de H contre H = 26, ATR [IC]",
     lambda r: "—" if r["H"] == H else ci(r["fige_effet_atr"], r["fige_effet_atr_lo"], r["fige_effet_atr_hi"], 3)),
]
GAP_LIGNES = [
    ("Trades exposés à un gap ; gaps traversés par trade (moyenne)",
     lambda r: f"{pct(r['part_expose_gap'], 0)} ; {fr(r['gaps_par_trade_moyenne'], 1)}"),
    ("Brut log ATR = gaps [IC] + séance [IC]",
     lambda r: f"{sg(r['brut_log_atr'], 3)} = {ci(r['gaps_atr'], r['gaps_atr_lo'], r['gaps_atr_hi'], 3)} + "
               f"{ci(r['seance_atr'], r['seance_atr_lo'], r['seance_atr_hi'], 3)}"),
    ("Stops en gap / stops ; dépassement moyen (P90), ATR",
     lambda r: f"{int(r['stops_en_gap'])}/{int(r['stops_n'])} ; "
               + ("—" if pd.isna(r["depassement_moyen_atr"]) else
                  f"{sg(r['depassement_moyen_atr'], 2)} ({sg(r['depassement_P90_atr'], 2)})")),
    ("Coût des dépassements (ATR par trade)", lambda r: fr(r["cout_depassements_atr_par_trade"], 3)),
]


def asset_table(res: pd.DataFrame, key: str) -> str:
    r = [row for _, row in res[res.actif == key].sort_values("H").iterrows()]
    head = ["Métrique (4 bps)"] + [f"H = {int(x['H'])}" + (" (RE-1)" if x["H"] == H else "") for x in r]
    body = [[lab] + [f(x) for x in r] for lab, f in LIGNES]
    body += [[f"Gaps ({GAPS[key]}) : {lab[0].lower()}{lab[1:]}"] + [f(x) for x in r] for lab, f in GAP_LIGNES]
    return table(head, body)


def section_controles(ctrl: dict) -> str:
    out = ["### A. Contrôles bloquants", "",
           "- Empreinte SHA-256 de chaque série identique à celle de l'audit de D01 (données inchangées, réserve 2026 "
           "tronquée au chargement).",
           "- Entrées figées à H = 26 identiques, trade par trade, aux trades de RE-1 (même enveloppe, même sortie).",
           "- Chaque course : une position à la fois (signal suivant ≥ signal + H), entrée à open[t + 1], sortie à H "
           "barres hors stop (troncature à la dernière barre de 2025 seulement)."]
    for key, c in ctrl["actifs"].items():
        h = c["h26_identique_d01"]
        out.append(f"- {key} : H = 26 redonne D01 ({h['metriques_comparees']} métriques, écart relatif max "
                   f"{h['ecart_relatif_max']:.1e} ; {h['gaps_compares']} mesures de gaps) ; {c['candidats']} signaux "
                   f"candidats ; annualisation sur {fr(c['annees'], 3)} ans ; rendement de l'actif sur l'échantillon "
                   f"{spct(c['rendement_actif_echantillon'])}.")
    out.append(f"- Durée du calcul : {ctrl['duree_s']} s.")
    return "\n".join(out)


def write_report() -> None:
    res = pd.read_csv(HERE / "resultats_D01_5.csv")
    ctrl = json.loads((HERE / "controles_D01_5.json").read_text(encoding="utf-8"))
    narr = HERE / "narratif_D01_5.md"
    head = narr.read_text(encoding="utf-8").rstrip() + "\n\n" if narr.exists() else "# EXP-D01.5\n\n"
    parts = [head + "## Annexes générées (run_D01_5.py)", section_controles(ctrl)]
    for letter, key in zip("BCD", GRILLES):
        parts.append(f"### {letter}. {NOMS[key]} : H ∈ {{{', '.join(str(h) for h in GRILLES[key])}}}\n\n"
                     + asset_table(res, key))
    parts.append("### E. Figures\n\n![Espérance selon H](figures/H_D01_5.png)\n\n"
                 "![Capital selon H](figures/capital_D01_5.png)")
    (HERE / "rapport_D01_5.md").write_text("\n\n".join(parts) + "\n", encoding="utf-8")


def main() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        pass
    if "--rapport" in sys.argv:
        write_report()
        print(f"rapport régénéré : {HERE / 'rapport_D01_5.md'}")
    else:
        run_main()


if __name__ == "__main__":
    main()
