"""EXP-D02 — walk-forward de RE-1 (BTC, SOL, AVAX, or) : protocole du porteur, cadrage validé le 2026-10-01
(`RESEARCH_LOG.md`, entrée EXP-D02).

Usage, depuis la racine du dépôt : python experiments/D02/run_D02.py --gate0 | --grille | --rapport
  --gate0   : contrôle bloquant Gate 0, avant toute grille → gate0_D02.json, gate0_D02.md (reproduction de résultats
              publiés et parité du noyau, sans aucune performance hors du point de RE-1).
  --grille  : second GO du porteur (2026-10-01) : contrôles bloquants de Gate 0 (données, parité BTC), 20 atlas,
              42 000 évaluations IS, 40 séries hors échantillon, comparaisons, sensibilités de BTC → resultats_D02.csv,
              annuel_D02.csv, comparaisons_D02.csv, parametres_D02.csv, cartes_D02.npz, trades_D02.csv.gz,
              diagnostics_D02.json, controles_D02.json, figures/, rapport_D02.md.
  --rapport : régénère gate0_D02.md et rapport_D02.md (narratif_D02.md écrit à la main, puis annexes), sans calcul.

Grille (second GO du porteur, 2026-10-01 ; règles fixées avant le calcul)
- Données : BTC/USD Bitstamp 2013-2025, panne de janvier 2015 retirée (convention de D02.0) ; SOL/USD et AVAX/USD
  Coinbase ; CFD or HistData 2009-2025. Une passe indépendante par actif ; un atlas par R0 ∈ {10, 50, 100, 200, 500}.
- Coûts : principal 5 bps (crypto) et 4 bps (or), seul utilisé pour le choix en IS ; stress hors échantillon, avec les
  paramètres choisis au coût principal, sans réoptimisation : 10 bps (crypto) et 6 bps (or).
- Choix en IS : `optimization.select_plateau` (règle du porteur : centre de la plus grande zone connexe de cases
  admissibles à Calmar net > 0) sur la grille 5 × 28 × 5 de chaque fenêtre ; branches OFAT = axes passant par RE-1 ;
  Statique = choix de l'IS du premier semestre, gardé ; WFO = choix de chaque IS.
- Séries hors échantillon : 10 par actif, une course continue chacune (`run_oos`), mêmes dates ; annualisation sur
  le nombre de semestres hors échantillon / 2.
- Lecture (règles du porteur, forme opérationnelle validée ; `optimization.compare` au coût principal) :
  - « surpasse RE-1 gelée » : espérance tangible (IC 95 % > 0 en ATR et en bps) et rendement tangible (IC 95 % > 0),
    sans dégrader le MDD (plage P2,5-P97,5 de l'écart de MDD aux sorties pas entièrement défavorable : borne haute ≥ 0) ;
  - « WFO retenu face à son Statique » : espérance tangible, Calmar en hausse sur toute la plage des chemins (borne
    basse > 0) et MDD non dégradé ; sinon le Statique est préféré ;
  - conjointe (Statique et WFO) : règle « surpasse », face à la meilleure variante 1D (Calmar à 0,25 %/ATR hors
    échantillon le plus élevé parmi les six Statique / WFO de H, R0 et frontière) ;
  - verdict d'un actif : si aucune variante ne surpasse RE-1 gelée, absence de valeur ajoutée démontrée avec ce
    protocole, RE-1 inchangée ;
  - lus aussi : effet propre contre le Contrôle ; stabilité des paramètres choisis ; effet de H sur entrées figées
    (I-M16, branche H) ; brut, frais, queues ; stress de coût ; nombre de comparaisons publié.
- Sensibilités de BTC : série brute (panne gardée) ; lecture dès le S1 2016 (Statique tiré de l'IS 2014-2015).

Gate 0 (règles fixées avant le calcul, protocole du porteur et audit validé) :
- G0-1 noyau = RE-1 sur BTC 2020-2025 : 0 trade manquant, 0 trade fantôme, barre par barre (`DataFrame.equals`
  avec `strategy.run_re1`, lui-même identique à C02bis) ; écart relatif ≤ 1e-5 sur le PnL cumulé et l'espérance en
  ATR contre `resultats_C02bis.csv`, à 5 et 10 bps.
- G0-2 parité hors du point de RE-1 (même règle d'identité) : H = 6 et 60 ; frontière 0,75 et 0,95 ; R0 = 10 et 500
  (atlas du moteur certifié, seuils de la période) ; paramètres qui changent à chaque frontière de semestre (référence
  Python indépendante : `apply_stop` et `_sequential` du dépôt, horizon par signal).
- G0-3 ancres : RE-1 gelée par le noyau redonne D01 (SOL 5 et 10 bps, or 2020-2025 4 bps) et D02.0 (BTC 2013-2019
  5 et 10 bps, or 2009-2019 4 bps), trades identiques à `run_re1` et métriques à 1e-5 des CSV publiés (6 chiffres).
- G0-4 données de D02 : empreintes des quatre séries égales aux audits validés ; réserve 2026 tronquée ; panne de
  Bitstamp de janvier 2015 (215 barres plates) ; fenêtres 22 / 29 / 5 / 4.
- G0-5 seuils : fenêtre BTC 2020-2025 entière = seuils gelés de RE-1, à la précision machine.
- G0-6 métriques d'IS (`objective.is_metrics`) = `strategy.metrics` sur les 1 080 trades (PnL, MDD, Calmar, espérance).
- Mesure de temps (non bloquante) : coût d'une évaluation, estimation de la grille.
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


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


D02_0 = _load("run_D02_0", ROOT / "experiments" / "D02_0" / "run_D02_0.py")
D01 = D02_0.D01
C2B = D01.C2B

from anatomy import build_atlas  # noqa: E402
from categorization import add_derived  # noqa: E402
from envelope import effect_ci, stop_distance  # noqa: E402
from envelope.stops import _sequential  # noqa: E402
from estimand.stoploss import TRADE_COLUMNS, apply_stop  # noqa: E402
from indicator import KalmanParams  # noqa: E402
from optimization import (GRID_F, GRID_H, GRID_R0, VARIANTS, AssetData, Params, branch_choice,  # noqa: E402
                          candidates, evaluate_is, frozen_entries, is_metrics, oos_candidates, paired_comparison,
                          prepare_inputs, run_oos, run_trades, series_stats, signal_table, simulate, variant_schedule,
                          walk_forward_windows, window_thresholds)
from strategy import (H, LEG_ATR_P50_BTC, NIS_Z100_P75_BTC, frozen_masks, load_asset, metrics, run_re1,  # noqa: E402
                      sample_years)
from strategy.re1 import N_BOOT  # noqa: E402
from utils.data_loader import meta_path, sha256_file  # noqa: E402

RAW = ROOT / "data" / "raw"
BPS = 1e4
UTC = "UTC"
TOL = 1e-5
SERIES = {  # actif de D02 → (CSV, nombre de semestres hors échantillon du protocole, audit validé)
    "BTC": (RAW / "bitstamp_btcusd_30m_2013_2025.csv", 22, "D02.0"),
    "XAU": (RAW / "histdata_xauusd_30m_2009_2025.csv", 29, "D02.0"),
    "SOL": (RAW / "coinbase_solusd_30m.csv", 5, "D01"),
    "AVAX": (RAW / "coinbase_avaxusd_30m.csv", 4, "D02.0"),
}
COLS = ["n_trades", "esperance_atr", "esperance_bps", "esperance_atr_lo", "esperance_atr_hi", "pnl_compose",
        "pnl_bps", "pnl_compose_r25", "mdd_valorise", "mdd_valorise_r25", "pf", "wr", "calmar_r25", "calmar_1x",
        "part_stop", "n_F3", "esperance_atr_F3", "annees_atr_pos"]


def stop(msg: str):
    raise SystemExit(f"Gate 0 : {msg} : arrêt")


def rel(x: float, y: float) -> float:
    return abs(float(x) - float(y)) / max(abs(float(y)), 1e-12)


def compare(got: dict, ref: pd.Series, cols=COLS, label: str = "") -> float:
    """Écart relatif maximal entre métriques ; arrêt au-delà de 1e-5 (et 1e-9 en absolu)."""
    worst = 0.0
    for c in cols:
        x, y = float(got[c]), float(ref[c])
        if not np.isclose(x, y, rtol=TOL, atol=1e-9):
            stop(f"{label} : {c} = {x} contre {y} publié")
        worst = max(worst, rel(x, y))
    return worst


def engine_re1(p: dict, horizon: int = H, frontier: float = 0.85, thresholds=(LEG_ATR_P50_BTC, NIS_Z100_P75_BTC)):
    """RE-1 par le noyau : table des signaux, candidats, `run_trades` ; famille déduite du stop (F3 = stop SL-B)."""
    tab = signal_table(p["bars"], p["atlas"], p["atr"])
    t, s, lv = candidates(tab, thresholds[0], thresholds[1], frontier)
    tr = run_trades(p["bars"], t, s, horizon, lv)
    return tr, pd.Series(np.where(np.isnan(lv), "F2b", "F3"), index=t), tab


def identity(got: pd.DataFrame, ref: pd.DataFrame, label: str) -> dict:
    """Trades manquants et fantômes (clé : signal, entrée, sens), puis identité barre par barre."""
    key = ["signal_bar", "entry_bar", "side"]
    a = set(map(tuple, got[key].to_numpy().tolist()))
    b = set(map(tuple, ref[key].to_numpy().tolist()))
    out = {"trades": len(got), "reference": len(ref), "manquants": len(b - a), "fantomes": len(a - b),
           "identiques": bool(got.equals(ref))}
    if out["manquants"] or out["fantomes"] or not out["identiques"]:
        stop(f"{label} : noyau différent de la référence {out}")
    return out


def reference_par_signal(bars, t, s, h, level, last) -> pd.DataFrame:
    """Référence Python indépendante du noyau : `apply_stop` et `_sequential` du dépôt, horizon par signal."""
    ok = t + 1 < last
    t, s, h, level = t[ok], s[ok], h[ok], level[ok]
    e, x = t + 1, np.minimum(t + 1 + h, last)
    with np.errstate(invalid="ignore"):
        out = apply_stop(bars, e, x, s, stop_distance(bars, t, s, level))
    keep = _sequential(t, x - 1)
    res = out.iloc[keep].reset_index(drop=True)
    res["signal_bar"] = t[keep]
    return res[TRADE_COLUMNS]


# ── G0-1, G0-5, G0-6 : BTC 2020-2025 ────────────────────────────────────────────
def g0_btc(p: dict) -> tuple[dict, pd.DataFrame]:
    out = {"c02bis": D01.check_btc(p)}                        # run_re1 = C02bis, trades et 40 métriques (D01)
    got, fam, tab = engine_re1(p)
    ref, fam_ref = run_re1(p["bars"], p["atlas"], p["atr"], p["m"])
    out["identite"] = identity(got, ref, "G0-1 BTC 2020-2025")
    if not fam.equals(fam_ref):
        stop("G0-1 : familles F2b/F3 différentes de RE-1")
    res = pd.read_csv(ROOT / "experiments" / "C02bis" / "resultats_C02bis.csv")
    n_cand = int(p["m"]["R2"].sum())
    worst = {}
    for fee in (5.0, 10.0):
        m, _ = metrics(got, p["bars"], p["atr_bps"], fee, n_cand, fam, sample_years(p["bars"]))
        g = res[(res.variante_seuils == C2B.ENTIER) & (res.configuration == "RE-1") & (res.H == H)
                & (res["mode"] == "cooldown") & (res.frais_bps == fee)].iloc[0]
        cols = [c for c in ("pnl_compose", "pnl_compose_r25", "esperance_atr", "esperance_bps", "n_trades",
                            "mdd_valorise", "mdd_valorise_r25", "calmar_r25") if c in g.index]
        worst[f"{fee:g}"] = {"colonnes": cols, "ecart_relatif_max": compare(m, g, cols, f"G0-1 {fee:g} bps")}
    out["metriques_c02bis"] = worst
    leg, nis, n = window_thresholds(tab, pd.Timestamp("2020-01-01", tz=UTC), pd.Timestamp("2026-01-01", tz=UTC))
    if (leg, nis, n) != (LEG_ATR_P50_BTC, NIS_Z100_P75_BTC, 7296):
        stop(f"G0-5 : seuils de la fenêtre 2020-2025 {leg}, {nis}, {n} différents des seuils gelés")
    out["seuils_2020_2025"] = {"leg_atr_p50": leg, "nis_z_100_p75": nis, "signaux": n, "egaux_aux_geles": True}
    m, _ = metrics(got, p["bars"], p["atr_bps"], 5.0, n_cand, fam, 6.0)
    atr_bar = p["atr"] / p["bars"].close.to_numpy() * BPS
    om = is_metrics(got, p["bars"].close.to_numpy(), atr_bar, 5.0, n_years=6.0)
    pairs = {"pnl_r25": "pnl_compose_r25", "mdd_r25": "mdd_valorise_r25", "calmar_r25": "calmar_r25",
             "esperance_atr": "esperance_atr", "n_trades": "n_trades"}
    ecarts = {k: rel(om[k], m[v]) for k, v in pairs.items()}
    if max(ecarts.values()) > 1e-12:
        stop(f"G0-6 : métriques d'IS différentes de strategy.metrics {ecarts}")
    out["objectif"] = {"ecart_relatif_max": max(ecarts.values()), "detail": ecarts}
    return out, got


# ── G0-2 : parité hors du point de RE-1 ─────────────────────────────────────────
def g0_hors_point(p: dict) -> tuple[dict, dict]:
    out, tabs, temps = {}, {}, {}
    _, m = frozen_masks(p["atlas"])
    for h in (6, 60):
        got, _, _ = engine_re1(p, horizon=h)
        out[f"H={h}"] = identity(got, run_re1(p["bars"], p["atlas"], p["atr"], m, horizon=h)[0], f"G0-2 H = {h}")
    r = add_derived(p["atlas"]).retrace_ratio.to_numpy()
    for f in (0.75, 0.95):
        got, _, _ = engine_re1(p, frontier=f)
        ref = run_re1(p["bars"], p["atlas"], p["atr"], dict(m, F3=m["R2"] & (r >= f)))[0]
        out[f"frontiere={f:.2f}"] = identity(got, ref, f"G0-2 frontière {f:.2f}")
    tabs[100.0] = signal_table(p["bars"], p["atlas"], p["atr"])
    for r0 in (10.0, 500.0):
        t0 = time.time()
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            atlas, _, _, atr = build_atlas(p["df"], kalman=KalmanParams(R0=r0))
        temps[r0] = time.time() - t0
        if not np.array_equal(atr, p["atr"], equal_nan=True):        # 13 NaN d'amorce de Wilder de part et d'autre
            stop(f"G0-2 R0 = {r0:g} : ATR14 dépendant de R0")
        pr = dict(p, atlas=atlas)
        tab = signal_table(p["bars"], atlas, atr)
        tabs[r0] = tab
        leg, nis, _ = window_thresholds(tab, pd.Timestamp("2020-01-01", tz=UTC), pd.Timestamp("2026-01-01", tz=UTC))
        got, _, _ = engine_re1(pr, thresholds=(leg, nis))
        ref = run_re1(p["bars"], atlas, atr, frozen_masks(atlas, leg, nis)[1])[0]
        out[f"R0={r0:g}"] = dict(identity(got, ref, f"G0-2 R0 = {r0:g}"), signaux=len(atlas))
    atr_bar = p["atr"] / p["bars"].close.to_numpy() * BPS
    if not np.array_equal(atr_bar[p["atlas"].bar_index.to_numpy()], p["atlas"].atr14_bps.to_numpy()):
        stop("G0-2 : ATR14 en bps par barre différent de celui de l'atlas")
    data = AssetData("BTC 2020-2025", p["bars"], tabs, atr_bar, 5.0)
    ws = walk_forward_windows(p["bars"].time.iat[0])
    cycle = [Params(10.0, 60, 0.80), Params(500.0, 40, 0.90), Params(100.0, 60, 0.85), Params(10.0, 6, 0.95)]
    sched = [cycle[i % len(cycle)] for i in range(len(ws))]
    t, s, h, lv, k = oos_candidates(data, ws, sched, "fenetre")
    got = run_oos(data, (t, s, h, lv, k))
    ref = reference_par_signal(p["bars"], t, s, h, lv, len(p["bars"]) - 1)
    ident = identity(got[TRADE_COLUMNS], ref, "G0-2 paramètres par semestre")
    sem = got.semestre.to_numpy()
    exit_t = p["bars"].time.iloc[got.exit_bar.to_numpy()].reset_index(drop=True)
    cross = (exit_t >= pd.Series([ws[i].oos_end for i in sem])).to_numpy()
    hold = got.exit_bar.to_numpy() - got.entry_bar.to_numpy()
    own_h = np.array([sched[i].h for i in sem])
    free = ~got.stop.to_numpy(dtype=bool) & (got.exit_bar.to_numpy() < len(p["bars"]) - 1)
    if not (hold[free] == own_h[free]).all():
        stop("G0-2 : un trade sans stop ne garde pas l'horizon de son semestre")
    if not (cross & free).any():
        stop("G0-2 : aucun trade à cheval sur deux semestres, contrôle sans objet")
    out["parametres_par_semestre"] = dict(ident, semestres=len(ws), a_cheval=int(cross.sum()),
                                          a_cheval_sans_stop=int((cross & free).sum()),
                                          a_cheval_horizon_propre=bool((hold[cross & free] == own_h[cross & free]).all()))
    return out, {"atlas_s": temps, "tabs": tabs, "data": data, "windows": ws}


# ── G0-3 : ancres D01 et D02.0 ──────────────────────────────────────────────────
def g0_ancres() -> dict:
    out = {}
    r01 = pd.read_csv(ROOT / "experiments" / "D01" / "resultats_D01.csv")
    for key in ("SOL", "XAU"):
        p = D01.prepare(key)
        got, fam, _ = engine_re1(p)
        ref, _ = run_re1(p["bars"], p["atlas"], p["atr"], p["m"])
        o = {"identite": identity(got, ref, f"G0-3 D01 {key}"), "metriques": {}}
        for fee in D01.ASSETS[key]["fees"]:
            m, _ = metrics(got, p["bars"], p["atr_bps"], fee, int(p["m"]["R2"].sum()), fam, sample_years(p["bars"]))
            row = r01[(r01.actif == key) & (r01.frais_bps == fee)].iloc[0]
            o["metriques"][f"{fee:g}"] = {"esperance_atr": m["esperance_atr"],
                                          "ecart_relatif_max": compare(m, row, label=f"G0-3 D01 {key} {fee:g} bps")}
        out[f"D01 {key} 2020-2025"] = o
    r02 = pd.read_csv(ROOT / "experiments" / "D02_0" / "resultats_D02_0.csv")
    for key in ("BTC 2013-2019", "XAU 2009-2019"):
        p = D02_0.prepare(key)
        got, fam, _ = engine_re1(p)
        ref, _ = run_re1(p["bars"], p["atlas"], p["atr"], p["m"])
        o = {"identite": identity(got, ref, f"G0-3 D02.0 {key}"), "metriques": {}}
        for fee in D02_0.LECTURES[key]["fees"]:
            m, _ = D02_0.measure(key, p, got, fam, fee, int(p["m"]["R2"].sum()), p["info"]["annees"])
            row = r02[(r02.actif == key) & (r02.frais_bps == fee)].iloc[0]
            o["metriques"][f"{fee:g}"] = {"esperance_atr": m["esperance_atr"],
                                          "ecart_relatif_max": compare(m, row, label=f"G0-3 D02.0 {key} {fee:g} bps")}
        out[f"D02.0 {key}"] = o
    return out


# ── G0-4 : données de D02 ───────────────────────────────────────────────────────
def g0_donnees() -> dict:
    a01 = json.loads((ROOT / "experiments" / "D01" / "audit_D01.json").read_text(encoding="utf-8"))
    a02 = json.loads((ROOT / "experiments" / "D02_0" / "audit_donnees_D02_0.json").read_text(encoding="utf-8"))
    out = {}
    for key, (csv, n_oos, src) in SERIES.items():
        audit = a01[key]["doc"]["sha256"] if src == "D01" else a02[key]["sha256"]
        meta = json.loads(meta_path(csv).read_text(encoding="utf-8"))
        sha = sha256_file(csv)
        if not sha == meta["sha256"] == audit:
            stop(f"G0-4 {key} : empreinte du CSV différente de l'audit {src}")
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            df, bars = load_asset(csv)
        o = {"audit": src, "sha256": sha[:16], "premiere_barre": str(bars.time.iat[0]),
             "derniere_barre": str(bars.time.iat[-1]), "barres": len(bars)}
        if bars.time.iat[-1] >= pd.Timestamp("2026-01-01", tz=UTC):
            stop(f"G0-4 {key} : barre de 2026")
        if key == "BTC":
            mask = D02_0.outage_mask(df)
            o["panne_2015_barres_retirees"] = int(mask.sum())
            if int(mask.sum()) != 215:
                stop("G0-4 BTC : panne de janvier 2015 différente de 215 barres")
            o["barres"] = int(len(bars) - mask.sum())
        ws = walk_forward_windows(bars.time.iat[0])
        if len(ws) != n_oos:
            stop(f"G0-4 {key} : {len(ws)} semestres hors échantillon au lieu de {n_oos}")
        o.update({"semestres_oos": len(ws), "premier_is": str(ws[0].is_start.date()),
                  "premier_oos": str(ws[0].oos_start.date()), "fin_oos": str(ws[-1].oos_end.date())})
        out[key] = o
    raw = json.loads(meta_path(RAW / "bitstamp_btcusd_30m.csv").read_text(encoding="utf-8"))
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        _, b = load_asset(RAW / "bitstamp_btcusd_30m.csv")
    out["reserve_2026"] = {"fichier_btc_2020_derniere_barre_brute": raw["last"], "derniere_barre_lue": str(b.time.iat[-1]),
                           "tronquee": bool(b.time.iat[-1] < pd.Timestamp("2026-01-01", tz=UTC))}
    if not out["reserve_2026"]["tronquee"]:
        stop("G0-4 : réserve 2026 non tronquée au chargement")
    return out


# ── Mesure de temps (non bloquante) ─────────────────────────────────────────────
def mesure_temps(p: dict, tab, atlas_s: dict) -> dict:
    """Coût d'une évaluation (noyau + métriques) au point de RE-1 sur 6 ans, ramené à un IS de 24 mois."""
    t, s, lv = candidates(tab, LEG_ATR_P50_BTC, NIS_Z100_P75_BTC, 0.85)
    args = prepare_inputs(p["bars"], t, s, H, lv)
    close = p["bars"].close.to_numpy()
    atr_bar = p["atr"] / close * BPS
    is_metrics(simulate(*args), close, atr_bar, 5.0, n_years=6.0)          # compilation déjà faite par les tests
    n = 200
    t0 = time.perf_counter()
    for _ in range(n):
        is_metrics(simulate(*args), close, atr_bar, 5.0, n_years=6.0)
    per = (time.perf_counter() - t0) / n
    n_eval = 700 * sum(v[1] for v in SERIES.values())
    return {"evaluation_6_ans_ms": per * 1e3, "evaluation_is_24_mois_ms_estimee": per * 1e3 / 3,
            "evaluations_grille": n_eval, "grille_minutes_estimees": n_eval * per / 3 / 60,
            "atlas_btc_2020_2025_par_r0_s": {f"{k:g}": v for k, v in atlas_s.items()}}


# ── Rapport ─────────────────────────────────────────────────────────────────────
def write_report(g: dict) -> None:
    b, hp, an, dn, tm = g["G0-1"], g["G0-2"], g["G0-3"], g["G0-4"], g["temps"]
    L = ["# EXP-D02 — Gate 0 : rapport de validation", "",
         f"- **Date :** {g['date']} ; durée {g['duree_s']} s ; commit du code : `{g['commit']}`.",
         "- **Nature :** contrôle bloquant avant toute grille. Aucun calcul de recherche : seuls des trades et des "
         "métriques déjà publiés sont reproduits ; la parité hors du point de RE-1 est vérifiée sans aucune "
         "performance calculée ni publiée.",
         f"- **Verdict : {'PASSÉ' if g['passe'] else 'ÉCHEC'}** (tout écart arrête le script).", "",
         "## Synthèse", "", "| Contrôle | Règle | Résultat |", "|---|---|---|"]
    def f(x, d=3, sign=False):                                # décimale française
        return (f"{x:+.{d}f}" if sign else f"{x:.{d}f}").replace(".", ",").replace("-", "−")

    def e(x):
        if x == 0:
            return "0"
        m, p = f"{x:.1e}".split("e")
        return f"{m.replace('.', ',')}·10{str(int(p)).translate(str.maketrans('0123456789-', '⁰¹²³⁴⁵⁶⁷⁸⁹⁻'))}"

    i = b["identite"]
    w = max(b["metriques_c02bis"][k]["ecart_relatif_max"] for k in ("5", "10"))
    L.append(f"| G0-1 noyau = RE-1, BTC 2020-2025 | 0 manquant, 0 fantôme, identité barre par barre ; ≤ 1e-5 sur PnL "
             f"et espérance | {i['trades']} trades sur {i['reference']} ; {i['manquants']} manquant, {i['fantomes']} "
             f"fantôme ; identiques à `run_re1` au bit près ; écart au CSV de C02bis (6 chiffres) ≤ {e(w)} à 5 et "
             f"10 bps |")
    names = {"H=6": "H = 6", "H=60": "H = 60", "frontiere=0.75": "frontière 0,75", "frontiere=0.95": "frontière 0,95",
             "R0=10": "R0 = 10", "R0=500": "R0 = 500"}
    L.append("| G0-2 hors du point de RE-1 | identité avec `run_re1` | "
             + " ; ".join(f"{v} : {hp[k]['trades']} trades identiques" for k, v in names.items()) + " |")
    ps = hp["parametres_par_semestre"]
    L.append(f"| G0-2 paramètres par semestre | identité avec la référence Python ; horizon propre ; au moins un trade "
             f"à cheval | {ps['trades']} trades identiques sur {ps['semestres']} semestres ; trades à cheval sur deux "
             f"semestres : {ps['a_cheval']} (dont {ps['a_cheval_sans_stop']} sans stop, à l'horizon de leur signal) |")
    for k, o in an.items():
        ex = max(v["ecart_relatif_max"] for v in o["metriques"].values())
        esp = " ; ".join(f"{fee} bps {f(v['esperance_atr'], sign=True)} ATR" for fee, v in o["metriques"].items())
        L.append(f"| G0-3 ancre {k} | trades = `run_re1` ; métriques à 1e-5 du CSV publié | {o['identite']['trades']} "
                 f"trades identiques ; {esp} ; écart au CSV ≤ {e(ex)} |")
    for k in ("BTC", "XAU", "SOL", "AVAX"):
        o = dn[k]
        extra = f" ; panne : {o['panne_2015_barres_retirees']} barres retirées" if k == "BTC" else ""
        L.append(f"| G0-4 données {k} | empreinte = audit {o['audit']} ; {SERIES[k][1]} semestres | `{o['sha256']}…` ; "
                 f"{o['premiere_barre'][:16]} → {o['derniere_barre'][:16]} ; {o['semestres_oos']} semestres "
                 f"({o['premier_oos']} → {o['fin_oos']}){extra} |")
    r = dn["reserve_2026"]
    L.append(f"| G0-4 réserve 2026 | aucune barre de 2026 lue | fichier BTC 2020 brut jusqu'au "
             f"{r['fichier_btc_2020_derniere_barre_brute'][:16]}, lu jusqu'au {r['derniere_barre_lue'][:16]} |")
    s = b["seuils_2020_2025"]
    L.append(f"| G0-5 seuils par fenêtre | fenêtre 2020-2025 = seuils gelés, au bit près | "
             f"`{s['leg_atr_p50']!r}` ; `{s['nis_z_100_p75']!r}` ; {s['signaux']} signaux |")
    L.append(f"| G0-6 métriques d'IS | = `strategy.metrics` | écart relatif maximal {e(b['objectif']['ecart_relatif_max'])} |")
    L += ["", "## Temps de calcul (mesure, non bloquante)", "",
          f"- Une évaluation (noyau + métriques) au point de RE-1 sur BTC 2020-2025 (6 ans) : "
          f"{f(tm['evaluation_6_ans_ms'], 2)} ms ; sur un IS de 24 mois : ≈ {f(tm['evaluation_is_24_mois_ms_estimee'], 2)} ms.",
          f"- Grille du protocole : {tm['evaluations_grille']:_} évaluations IS (700 × 60 fenêtres) ≈ "
          f"{f(tm['grille_minutes_estimees'] * 60, 0)} s de noyau et de métriques.".replace("_", " "),
          "- Le coût réel est celui des atlas : BTC 2020-2025, "
          + ", ".join(f"R0 = {k} : {f(v, 1)} s" for k, v in tm["atlas_btc_2020_2025_par_r0_s"].items())
          + " ; 20 atlas (4 actifs × 5 R0) sur les séries longues : quelques minutes.", ""]
    (HERE / "gate0_D02.md").write_text("\n".join(L) + "\n", encoding="utf-8")


def run_gate0() -> None:
    import subprocess
    t0 = time.time()
    commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    g = {"date": pd.Timestamp.now(tz="UTC").strftime("%Y-%m-%d %H:%M UTC"), "commit": commit}
    g["G0-4"] = g0_donnees()
    print(f"G0-4 données : passé ({time.time() - t0:.0f} s)", flush=True)
    p = D01.prepare("BTC")
    g["G0-1"], _ = g0_btc(p)
    print(f"G0-1, G0-5, G0-6 BTC 2020-2025 : passés ({time.time() - t0:.0f} s)", flush=True)
    g["G0-2"], extra = g0_hors_point(p)
    print(f"G0-2 hors du point de RE-1 : passé ({time.time() - t0:.0f} s)", flush=True)
    g["G0-3"] = g0_ancres()
    print(f"G0-3 ancres D01 et D02.0 : passées ({time.time() - t0:.0f} s)", flush=True)
    g["temps"] = mesure_temps(p, extra["tabs"][100.0], extra["atlas_s"])
    g["passe"] = True
    g["duree_s"] = round(time.time() - t0)
    (HERE / "gate0_D02.json").write_text(json.dumps(D01.jsonable(g), ensure_ascii=False, indent=1), encoding="utf-8")
    write_report(g)
    print(f"Gate 0 passé en {g['duree_s']} s ; gate0_D02.json et gate0_D02.md dans {HERE}")


# ═══ Grille : second GO du porteur (2026-10-01) ═════════════════════════════════
ASSETS = {
    "BTC": {"csv": SERIES["BTC"][0], "panne": True, "fees": (5.0, 10.0),
            "nom": "BTC/USD Bitstamp 2013-2025, panne de janvier 2015 retirée"},
    "SOL": {"csv": SERIES["SOL"][0], "panne": False, "fees": (5.0, 10.0), "nom": "SOL/USD Coinbase, dès le 2021-06-17"},
    "AVAX": {"csv": SERIES["AVAX"][0], "panne": False, "fees": (5.0, 10.0),
             "nom": "AVAX/USD Coinbase, dès le 2021-09-30"},
    "XAU": {"csv": SERIES["XAU"][0], "panne": False, "fees": (4.0, 6.0), "nom": "CFD or XAU/USD HistData, dès 2009-03-15"},
}
BTC_BRUT = {"csv": SERIES["BTC"][0], "panne": False, "fees": (5.0,), "nom": "BTC/USD Bitstamp, série brute"}
NAMES = list(VARIANTS)
ONE_D = ["Statique-H", "WFO-H", "Statique-R0", "WFO-R0", "Statique-frontière", "WFO-frontière"]
PAIRS = {"H": ("WFO-H", "Statique-H"), "R0": ("WFO-R0", "Statique-R0"),
         "frontiere": ("WFO-frontière", "Statique-frontière"), "conjointe": ("WFO-conjointe", "Statique-conjointe")}
FIG = HERE / "figures"


def prepare_d02(key: str, cfg: dict) -> tuple[AssetData, dict]:
    """Barres (empreinte vérifiée, réserve 2026 tronquée, panne retirée si demandé), un atlas et une table de signaux
    par R0, ATR14 en bps par barre (indépendant de R0, contrôlé), coût principal."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        df, _ = load_asset(cfg["csv"])
    info = {"barres_lues": len(df)}
    if cfg["panne"]:
        mask = D02_0.outage_mask(df)
        info["panne_barres_retirees"] = int(mask.sum())
        df = df[~mask].reset_index(drop=True)
    bars = df[["time", "open", "high", "low", "close"]].copy()
    tabs, atr0, secs = {}, None, {}
    for r0 in GRID_R0:
        t0 = time.time()
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            atlas, _, _, atr = build_atlas(df, kalman=KalmanParams(R0=r0))
        if atr0 is None:
            atr0 = atr
        elif not np.array_equal(atr, atr0, equal_nan=True):
            stop(f"{key} : ATR14 dépendant de R0")
        tabs[r0] = signal_table(bars, atlas, atr)
        secs[f"{r0:g}"] = round(time.time() - t0, 1)
        info[f"signaux_R0_{r0:g}"] = len(atlas)
    atr_bps = atr0 / bars.close.to_numpy() * BPS
    if not np.array_equal(atr_bps[tabs[100.0].t], tabs[100.0].atr_bps):
        stop(f"{key} : ATR14 en bps par barre différent de celui de l'atlas")
    info.update({"barres": len(bars), "premiere": str(bars.time.iat[0]), "derniere": str(bars.time.iat[-1]),
                 "atlas_s": secs})
    return AssetData(key, bars, tabs, atr_bps, cfg["fees"][0]), info


def run_series(data: AssetData, windows, evs, names=NAMES) -> dict:
    """Les séries hors échantillon : calendrier de paramètres, candidats, course continue, famille de chaque signal
    (F3 = signal routé vers le stop SL-B)."""
    out = {}
    for name in names:
        sched, thr = variant_schedule(evs, name)
        cands = oos_candidates(data, windows, sched, thr)
        tr = run_oos(data, cands)
        fam = pd.Series(np.where(np.isnan(cands[3]), "F2b", "F3"), index=cands[0])
        out[name] = {"trades": tr, "cands": cands, "fam": fam, "sched": sched, "seuils": thr}
    return out


def choice_rows(key: str, windows, evs) -> list[dict]:
    rows = []
    for branch in PAIRS:
        for w, ev in zip(windows, evs):
            p, info = branch_choice(ev, branch)
            rows.append({"actif": key, "branche": branch, "k": w.k, "oos_debut": str(w.oos_start.date()),
                         "R0": p.r0, "H": p.h, "frontiere": p.frontier, "repli": info["repli"], "zone": info["zone"],
                         "n_zones": info["n_zones"], "n_candidates": info["n_candidates"],
                         "calmar_zone": info["calmar_zone"],
                         "leg_p50_R0_100": float(ev["leg_p50"][GRID_R0.index(100.0)]),
                         "nis_p75_R0_100": float(ev["nis_p75"][GRID_R0.index(100.0)])})
    return rows


def measure_d02(label: str, name: str, s: dict, data: AssetData, fee: float, n_years: float):
    """Métriques de `strategy.metrics` (8 métriques, IC, 0,25 %/ATR et 1x), plus brut, frais, queues et durée."""
    tr = s["trades"][TRADE_COLUMNS]
    atr_s = pd.Series(data.atr_bps, index=np.arange(len(data.bars)))
    m, y = metrics(tr, data.bars, atr_s, fee, len(s["cands"][0]), s["fam"], n_years)
    a = atr_s.reindex(tr.signal_bar.to_numpy()).to_numpy()
    ret = tr.ret_gross_bps.to_numpy(dtype=float)
    na = (ret - fee) / a
    t = data.bars.time
    hours = (t.iloc[tr.exit_bar.to_numpy()].to_numpy() - t.iloc[tr.entry_bar.to_numpy()].to_numpy()) \
        / np.timedelta64(1, "h")
    p90 = float(np.quantile(na, 0.9)) if len(na) else np.nan
    m.update({"actif": label, "variante": name, "frais_bps": fee, "annees": n_years,
              "brut_atr": float(np.mean(ret / a)) if len(a) else np.nan,
              "frais_atr": float(np.mean(fee / a)) if len(a) else np.nan,
              "mediane_atr": float(np.median(na)) if len(na) else np.nan,
              "p10_atr": float(np.quantile(na, 0.1)) if len(na) else np.nan, "p90_atr": p90,
              "moy_decile_sup_atr": float(na[na >= p90].mean()) if len(na) else np.nan,
              "duree_mediane_h": float(np.median(hours)) if len(hours) else np.nan,
              "debut": str(t.iloc[tr.entry_bar.to_numpy()].min()), "fin": str(t.iloc[tr.exit_bar.to_numpy()].max())})
    y.insert(0, "actif", label)
    y.insert(1, "variante", name)
    y.insert(2, "frais_bps", fee)
    return m, y


def compare_asset(label: str, data: AssetData, windows, series: dict, main: dict, fee: float,
                  only_re1: bool = False) -> list[dict]:
    """Comparaisons appariées par mois (règles en tête de module) ; `only_re1` : contre RE-1 gelée seulement."""
    start, end = windows[0].oos_start, windows[-1].oos_end
    st = {n: series_stats(s["trades"], data.bars, data.atr_bps, fee, start, end) for n, s in series.items()}
    rows = []

    def add(a: str, b: str, famille: str):
        c = paired_comparison(st[a], st[b])
        not_worse = bool(c["d_mdd_sorties_hi"] >= 0)
        rows.append({"actif": label, "frais_bps": fee, "famille": famille, "variante": a, "reference": b, **c,
                     "mdd_non_degrade": not_worse,
                     "surpasse": bool(c["esperance_tangible"] and c["rendement_tangible"] and not_worse),
                     "wfo_retenu": bool(c["esperance_tangible"] and c["d_calmar_sorties_lo"] > 0 and not_worse)})
    for n in NAMES[1:]:
        add(n, "RE-1 gelée", "contre RE-1 gelée")
    if only_re1:
        return rows
    for n in NAMES[2:]:
        add(n, "Contrôle", "contre le Contrôle")
    for w, s in PAIRS.values():
        add(w, s, "WFO contre Statique")
    best = max(ONE_D, key=lambda n: main[n]["calmar_r25"] if np.isfinite(main[n]["calmar_r25"]) else -np.inf)
    for n in ("Statique-conjointe", "WFO-conjointe"):
        add(n, best, "conjointe contre meilleure 1D")
    return rows


def frozen_h(data: AssetData, series: dict) -> dict:
    """Effet de l'horizon choisi (Statique-H, WFO-H) sur les entrées figées du Contrôle (I-M16) : mêmes entrées, même
    stop, horizon du semestre de chaque entrée ; effet apparié par trade, IC par grappes mensuelles."""
    ctrl = series["Contrôle"]
    base = ctrl["trades"][TRADE_COLUMNS].reset_index(drop=True)
    t, _, _, lv, _ = ctrl["cands"]
    level = pd.Series(lv, index=t).reindex(base.signal_bar.to_numpy()).to_numpy()
    if not frozen_entries(data.bars, base, H, level).equals(base):
        stop("entrées figées : H = 26 ne redonne pas le Contrôle")
    sem = ctrl["trades"].semestre.to_numpy()
    atr_s = pd.Series(data.atr_bps, index=np.arange(len(data.bars)))
    out = {}
    for name in ("Statique-H", "WFO-H"):
        hs = np.array([series[name]["sched"][i].h for i in sem], dtype=np.int64)
        fz = frozen_entries(data.bars, base, hs, level)
        out[name] = {**effect_ci(fz, base, data.bars, atr_s, n_boot=N_BOOT), "trades": len(base),
                     "h_moyen": float(hs.mean()), "part_h_26": float((hs == H).mean())}
    return out


def equity_points(s: dict, data: AssetData, fee: float) -> pd.Series:
    """Capital composé à 0,25 %/ATR aux sorties (figure)."""
    tr = s["trades"]
    a = data.atr_bps[tr.signal_bar.to_numpy()]
    r = np.minimum(1.0, 25.0 / a) * (tr.ret_gross_bps.to_numpy(dtype=float) - fee) / BPS
    return pd.Series(np.cumprod(1.0 + r), index=pd.DatetimeIndex(data.bars.time.iloc[tr.exit_bar.to_numpy()]))


def figures_d02(curves: dict, choices: pd.DataFrame) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    FIG.mkdir(parents=True, exist_ok=True)
    style = {"RE-1 gelée": ("k", 2.0), "Contrôle": ("#7f7f7f", 1.6), "Statique-conjointe": ("#ff7f0e", 1.4),
             "WFO-conjointe": ("#d62728", 1.6)}
    fig, axes = plt.subplots(2, 2, figsize=(14, 9))
    for ax, (key, cur) in zip(axes.ravel(), curves.items()):
        for name, eq in cur.items():
            c, lw = style.get(name, (None, 0.7))
            ax.step(eq.index, 100 * (eq.to_numpy() - 1.0), where="post", color=c, lw=lw,
                    alpha=1.0 if name in style else 0.55, label=name)
        ax.axhline(0, color="k", lw=0.5)
        ax.set_title(f"{key} : capital hors échantillon (0,25 %/ATR, coût principal)", fontsize=10)
        ax.set_ylabel("PnL composé (%)")
        ax.grid(alpha=0.3)
    axes[0, 0].legend(fontsize=7, ncol=2)
    fig.tight_layout()
    fig.savefig(FIG / "D02_capital.png", dpi=110)
    plt.close(fig)
    conj = choices[choices.branche == "conjointe"]
    fig, axes = plt.subplots(3, 1, figsize=(12, 9), sharex=True)
    for key, g in conj.groupby("actif", sort=False):
        x = pd.to_datetime(g.oos_debut)
        axes[0].step(x, [GRID_R0.index(v) for v in g.R0], where="post", label=key)
        axes[1].step(x, g.H, where="post", label=key)
        axes[2].step(x, g.frontiere, where="post", label=key)
    axes[0].set_yticks(range(len(GRID_R0)), [f"{v:g}" for v in GRID_R0])
    for ax, lab in zip(axes, ("R0", "H (barres)", "frontière F2b/F3")):
        ax.set_ylabel(lab)
        ax.grid(alpha=0.3)
    axes[0].legend(fontsize=8)
    axes[0].set_title("WFO conjoint : paramètres choisis à chaque semestre (règle de la zone connexe)", fontsize=10)
    fig.tight_layout()
    fig.savefig(FIG / "D02_parametres.png", dpi=110)
    plt.close(fig)


def run_grille() -> None:
    import subprocess
    t0 = time.time()
    commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    ctrl = {"date": pd.Timestamp.now(tz="UTC").strftime("%Y-%m-%d %H:%M UTC"), "commit": commit}
    ctrl["G0-4"] = g0_donnees()
    ctrl["G0-1"], _ = g0_btc(D01.prepare("BTC"))
    print(f"contrôles bloquants de Gate 0 repassés ({time.time() - t0:.0f} s)", flush=True)
    rows, years, comps, choices, diags, cartes, trades, curves = [], [], [], [], {}, {}, [], {}
    for key, cfg in ASSETS.items():
        data, info = prepare_d02(key, cfg)
        windows = walk_forward_windows(data.bars.time.iat[0])
        if len(windows) != SERIES[key][1]:
            stop(f"{key} : {len(windows)} semestres au lieu de {SERIES[key][1]}")
        t1 = time.time()
        evs = [evaluate_is(data, w) for w in windows]
        info["grille_s"] = round(time.time() - t1, 1)
        info["evaluations"] = 700 * len(windows)
        for w, ev in zip(windows, evs):
            for k, v in ev.items():
                cartes[f"{key}|{w.k}|{k}"] = v
        choices += choice_rows(key, windows, evs)
        series = run_series(data, windows, evs)
        ny = len(windows) / 2.0
        main = {}
        for fee in cfg["fees"]:
            for name, s in series.items():
                m, y = measure_d02(key, name, s, data, fee, ny)
                rows.append(m)
                years.append(y)
                if fee == cfg["fees"][0]:
                    main[name] = m
        comps += compare_asset(key, data, windows, series, main, cfg["fees"][0])
        comps += compare_asset(key, data, windows, series, main, cfg["fees"][1], only_re1=True)
        diags[key] = {"nom": cfg["nom"], "info": info, "semestres": len(windows),
                      "premier_oos": str(windows[0].oos_start.date()), "entrees_figees_H": frozen_h(data, series)}
        for name, s in series.items():
            tr = s["trades"].copy()
            tr.insert(0, "variante", name)
            tr.insert(0, "actif", key)
            tr["entree"] = data.bars.time.iloc[tr.entry_bar.to_numpy()].to_numpy()
            trades.append(tr)
        curves[key] = {name: equity_points(s, data, cfg["fees"][0]) for name, s in series.items()}
        if key == "BTC":                                       # sensibilité : lecture dès le S1 2016
            if windows[2].oos_start != pd.Timestamp("2016-01-01", tz=UTC):
                stop("sensibilité 2013 : troisième semestre différent du S1 2016")
            s16 = run_series(data, windows[2:], evs[2:])
            m16 = {n: measure_d02("BTC 2016-2025", n, s, data, 5.0, (len(windows) - 2) / 2.0)[0]
                   for n, s in s16.items()}
            rows += list(m16.values())
            comps += compare_asset("BTC 2016-2025", data, windows[2:], s16, m16, 5.0, only_re1=True)
        print(f"{key} : {len(windows)} semestres, {info['evaluations']} évaluations IS en {info['grille_s']} s, "
              f"séries et comparaisons faites ({time.time() - t0:.0f} s)", flush=True)
    data_b, info_b = prepare_d02("BTC brut", BTC_BRUT)              # sensibilité : panne gardée
    windows_b = walk_forward_windows(data_b.bars.time.iat[0])
    evs_b = [evaluate_is(data_b, w) for w in windows_b]
    sb = run_series(data_b, windows_b, evs_b)
    mb = {n: measure_d02("BTC brut", n, s, data_b, 5.0, len(windows_b) / 2.0)[0] for n, s in sb.items()}
    rows += list(mb.values())
    comps += compare_asset("BTC brut", data_b, windows_b, sb, mb, 5.0, only_re1=True)
    diags["BTC brut"] = {"info": info_b, "semestres": len(windows_b)}
    print(f"sensibilité BTC brut faite ({time.time() - t0:.0f} s)", flush=True)
    res = pd.DataFrame(rows)
    lead = ["actif", "variante", "frais_bps", "annees", "debut", "fin"]
    res = res[lead + [c for c in res.columns if c not in lead]]
    res.to_csv(HERE / "resultats_D02.csv", index=False, float_format="%.6g")
    pd.concat(years, ignore_index=True).to_csv(HERE / "annuel_D02.csv", index=False, float_format="%.6g")
    pd.DataFrame(comps).to_csv(HERE / "comparaisons_D02.csv", index=False, float_format="%.6g")
    ch = pd.DataFrame(choices)
    ch.to_csv(HERE / "parametres_D02.csv", index=False, float_format="%.6g")
    np.savez_compressed(HERE / "cartes_D02.npz", **cartes)
    (pd.concat(trades, ignore_index=True).drop(columns=["entry_price", "exit_price"])   # aucun prix publié
     .to_csv(HERE / "trades_D02.csv.gz", index=False, float_format="%.10g"))
    ctrl["duree_s"] = round(time.time() - t0)
    ctrl["comparaisons"] = len(comps)
    (HERE / "diagnostics_D02.json").write_text(json.dumps(D01.jsonable(diags), ensure_ascii=False, indent=1),
                                               encoding="utf-8")
    (HERE / "controles_D02.json").write_text(json.dumps(D01.jsonable(ctrl), ensure_ascii=False, indent=1),
                                             encoding="utf-8")
    figures_d02(curves, ch)
    write_rapport_d02()
    print(f"D02 : {len(res)} lignes de résultats, {len(comps)} comparaisons en {ctrl['duree_s']} s ; sorties dans {HERE}")


# ── Rapport de D02 (annexes générées ; narratif_D02.md écrit à la main) ─────────
fr, sg, pct, spct, n_fr, ci, table = D01.fr, D01.sg, D01.pct, D01.spct, D01.n_fr, D01.ci, D01.table


def sgn(x) -> str:
    """Entier signé avec séparateur des milliers (bps cumulés)."""
    return "—" if pd.isna(x) else f"{x:+,.0f}".replace(",", " ").replace("-", "−")


def annex_metrics(res: pd.DataFrame, label: str, fee: float) -> str:
    r = res[(res.actif == label) & (res.frais_bps == fee)]
    head = ["Variante", "PnL : 0,25 %/ATR ; 1x ; bps (1x)", "PF (1x)", "WR", "Espérance ATR [IC] ; bps",
            "MDD : 0,25 %/ATR ; 1x", "Trades (/mois)", "Durée médiane", "Part des frais (1x) ; brut ; frais (ATR)",
            "Calmar 0,25 %/ATR"]
    rows = []
    for _, x in r.iterrows():
        frais = "brut ≤ 0" if x.brut_bps <= 0 else pct(x.part_frais, 0)
        rows.append([x.variante, f"{spct(x.pnl_compose_r25)} ; {spct(x.pnl_compose)} ; {sgn(x.pnl_bps)}",
                     fr(x.pf, 2), pct(x.wr, 1),
                     f"{ci(x.esperance_atr, x.esperance_atr_lo, x.esperance_atr_hi, 3)} ; {sg(x.esperance_bps, 1)}",
                     f"{pct(x.mdd_valorise_r25)} ; {pct(x.mdd_valorise)}",
                     f"{n_fr(x.n_trades)} ({fr(x.trades_par_mois, 1)})",
                     f"{fr(x.duree_mediane, 0)} b ; {fr(x.duree_mediane_h, 0)} h",
                     f"{frais} ; {sg(x.brut_atr, 2)} ; {fr(x.frais_atr, 2)}", fr(x.calmar_r25, 2)])
    return table(head, rows)


def annex_tails(res: pd.DataFrame, label: str, fee: float) -> str:
    r = res[(res.actif == label) & (res.frais_bps == fee)]
    head = ["Variante", "Médiane (ATR)", "P10 ; P90", "Moyenne du décile sup.", "Années > 0", "Part stoppée",
            "F2b ; F3 (ATR)"]
    rows = [[x.variante, sg(x.mediane_atr, 2), f"{sg(x.p10_atr, 2)} ; {sg(x.p90_atr, 2)}", sg(x.moy_decile_sup_atr, 2),
             f"{int(x.annees_atr_pos)}", pct(x.part_stop, 0), f"{sg(x.esperance_atr_F2b, 3)} ; {sg(x.esperance_atr_F3, 3)}"]
            for _, x in r.iterrows()]
    return table(head, rows)


def annex_comparisons(cp: pd.DataFrame, label: str, fee: float, famille: str) -> str:
    c = cp[(cp.actif == label) & (cp.frais_bps == fee) & (cp.famille == famille)]
    head = ["A contre B", "Δ espérance ATR [IC]", "Δ espérance bps [IC]", "Δ rendement annuel [IC]",
            "Δ MDD sorties (plage) ; part A mieux", "Δ Calmar sorties (plage) ; part A mieux", "Verdict"]
    rows = []
    for _, x in c.iterrows():
        if famille == "WFO contre Statique":
            v = "WFO retenu" if x.wfo_retenu else "Statique préféré"
        else:
            v = "surpasse" if x.surpasse else "non"
        rows.append([f"{x.variante} / {x.reference}",
                     ci(x.d_esperance_atr, x.d_esperance_atr_lo, x.d_esperance_atr_hi, 3),
                     ci(x.d_esperance_bps, x.d_esperance_bps_lo, x.d_esperance_bps_hi, 1),
                     f"{spct(x.d_rendement_annuel, 1)} [{spct(x.d_rendement_annuel_lo, 1)} ; "
                     f"{spct(x.d_rendement_annuel_hi, 1)}]",
                     f"{spct(x.d_mdd_sorties, 1)} [{spct(x.d_mdd_sorties_lo, 1)} ; {spct(x.d_mdd_sorties_hi, 1)}] ; "
                     f"{pct(x.part_mdd_meilleur, 0)}",
                     f"{sg(x.d_calmar_sorties, 2)} [{sg(x.d_calmar_sorties_lo, 2)} ; {sg(x.d_calmar_sorties_hi, 2)}] ; "
                     f"{pct(x.part_calmar_meilleur, 0)}", v])
    return table(head, rows)


def annex_parameters(ch: pd.DataFrame, label: str) -> str:
    c = ch[ch.actif == label]
    head = ["Branche", "Paramètre choisi à chaque semestre (WFO)", "Replis sur RE-1", "Zone : médiane (min-max)"]
    rows = []
    for branch, g in c.groupby("branche", sort=False):
        if branch == "H":
            seq = ", ".join(str(int(v)) for v in g.H)
        elif branch == "R0":
            seq = ", ".join(f"{v:g}" for v in g.R0)
        elif branch == "frontiere":
            seq = ", ".join(fr(v, 2) for v in g.frontiere)
        else:
            seq = " ; ".join(f"({v.R0:g}, {int(v.H)}, {fr(v.frontiere, 2)})" for v in g.itertuples())
        z = g.zone[~g.repli]
        rows.append([branch, seq, f"{int(g.repli.sum())} sur {len(g)}",
                     f"{fr(z.median(), 0)} ({int(z.min())}-{int(z.max())})" if len(z) else "—"])
    return table(head, rows)


def write_rapport_d02() -> None:
    res = pd.read_csv(HERE / "resultats_D02.csv")
    cp = pd.read_csv(HERE / "comparaisons_D02.csv")
    ch = pd.read_csv(HERE / "parametres_D02.csv")
    dg = json.loads((HERE / "diagnostics_D02.json").read_text(encoding="utf-8"))
    ct = json.loads((HERE / "controles_D02.json").read_text(encoding="utf-8"))
    narr = HERE / "narratif_D02.md"
    out = [narr.read_text(encoding="utf-8") if narr.exists() else "# EXP-D02 — rapport (narratif à rédiger)\n",
           "", "---", "", "# Annexes générées (`run_D02.py --grille`, puis `--rapport`)", "",
           f"Calcul du {ct['date']}, commit `{ct['commit']}`, {ct['duree_s']} s ; {ct['comparaisons']} comparaisons "
           f"appariées publiées. Contrôles bloquants de Gate 0 repassés avant la grille (données, 1 080 trades de RE-1).",
           ""]
    for i, key in enumerate(ASSETS, start=1):
        fees = ASSETS[key]["fees"]
        d = dg[key]
        info = d["info"]
        out += [f"## A{i}. {key} — {d['nom']}", "",
                f"- {d['semestres']} semestres hors échantillon dès le {d['premier_oos']} ; "
                f"{n_fr(info['evaluations'])} évaluations IS en {fr(info['grille_s'], 1)} s ; signaux par R0 : "
                + ", ".join(f"{r} : {n_fr(info[f'signaux_R0_{r}'])}" for r in ("10", "50", "100", "200", "500")) + ".",
                "", f"**Résultats nets à {fees[0]:g} bps (coût principal)**", "", annex_metrics(res, key, fees[0]), "",
                f"**Stress à {fees[1]:g} bps (paramètres choisis à {fees[0]:g} bps)**", "",
                annex_metrics(res, key, fees[1]), "", "**Queues et sous-familles (coût principal)**", "",
                annex_tails(res, key, fees[0]), ""]
        for fam in ("contre RE-1 gelée", "contre le Contrôle", "WFO contre Statique", "conjointe contre meilleure 1D"):
            out += [f"**Comparaisons appariées par mois, {fam} ({fees[0]:g} bps)**", "",
                    annex_comparisons(cp, key, fees[0], fam), ""]
        out += [f"**Contre RE-1 gelée au stress de {fees[1]:g} bps**", "",
                annex_comparisons(cp, key, fees[1], "contre RE-1 gelée"), "",
                "**Paramètres choisis (règle de la zone connexe)**", "", annex_parameters(ch, key), ""]
        fz = d["entrees_figees_H"]
        out += ["**Effet de l'horizon sur les entrées figées du Contrôle (I-M16)**", "",
                table(["Variante", "Trades", "H moyen ; part à 26", "Effet ATR [IC]", "Effet bps [IC]"],
                      [[n, n_fr(v["trades"]), f"{fr(v['h_moyen'], 1)} ; {pct(v['part_h_26'], 0)}",
                        ci(v["effet_atr"], v["effet_atr_lo"], v["effet_atr_hi"], 3),
                        ci(v["effet_bps"], v["effet_bps_lo"], v["effet_bps_hi"], 1)] for n, v in fz.items()]), ""]
    out += ["## A5. Sensibilités de BTC", "",
            "**Lecture dès le S1 2016 (Statique tiré de l'IS 2014-2015), 5 bps**", "",
            annex_metrics(res, "BTC 2016-2025", 5.0), "", annex_comparisons(cp, "BTC 2016-2025", 5.0,
                                                                          "contre RE-1 gelée"), "",
            "**Série brute, panne de janvier 2015 gardée, 5 bps**", "", annex_metrics(res, "BTC brut", 5.0), "",
            annex_comparisons(cp, "BTC brut", 5.0, "contre RE-1 gelée"), "",
            "## A6. Figures", "", "![Capital hors échantillon](figures/D02_capital.png)", "",
            "![Paramètres du WFO conjoint](figures/D02_parametres.png)", ""]
    (HERE / "rapport_D02.md").write_text("\n".join(out) + "\n", encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--gate0", action="store_true", help="contrôle bloquant avant toute grille")
    ap.add_argument("--grille", action="store_true", help="second GO : grille, séries hors échantillon, rapport")
    ap.add_argument("--rapport", action="store_true", help="régénère les rapports depuis les sorties, sans calcul")
    args = ap.parse_args()
    if args.rapport:
        write_report(json.loads((HERE / "gate0_D02.json").read_text(encoding="utf-8")))
        if (HERE / "resultats_D02.csv").exists():
            write_rapport_d02()
        return
    if args.grille:
        run_grille()
        return
    if not args.gate0:
        raise SystemExit("EXP-D02 : préciser --gate0, --grille ou --rapport")
    run_gate0()


if __name__ == "__main__":
    main()
