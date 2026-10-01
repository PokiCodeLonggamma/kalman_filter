"""EXP-D02 — walk-forward de RE-1 (BTC, SOL, AVAX, or) : protocole du porteur, cadrage validé le 2026-10-01
(`RESEARCH_LOG.md`, entrée EXP-D02).

Usage, depuis la racine du dépôt : python experiments/D02/run_D02.py --gate0 | --rapport
  --gate0 : contrôle bloquant Gate 0, avant toute grille → gate0_D02.json, gate0_D02.md. Aucun calcul de recherche :
            le script ne reproduit que des trades et des métriques déjà publiés (RE-1 / C02bis, D01, D02.0) et vérifie
            la parité du noyau hors du point de RE-1 sans calculer ni publier aucune performance.
  La grille (42 000 évaluations IS) et les 40 séries hors échantillon attendent le second GO du porteur.

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
from envelope import stop_distance  # noqa: E402
from envelope.stops import _sequential  # noqa: E402
from estimand.stoploss import TRADE_COLUMNS, apply_stop  # noqa: E402
from indicator import KalmanParams  # noqa: E402
from optimization import (GRID, AssetData, Params, candidates, is_metrics, oos_candidates, prepare_inputs,  # noqa: E402
                          run_oos, run_trades, signal_table, simulate, walk_forward_windows, window_thresholds)
from strategy import (H, LEG_ATR_P50_BTC, NIS_Z100_P75_BTC, frozen_masks, load_asset, metrics, run_re1,  # noqa: E402
                      sample_years)
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


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--gate0", action="store_true", help="contrôle bloquant avant toute grille")
    ap.add_argument("--rapport", action="store_true", help="régénère gate0_D02.md depuis gate0_D02.json, sans calcul")
    args = ap.parse_args()
    if args.rapport:
        write_report(json.loads((HERE / "gate0_D02.json").read_text(encoding="utf-8")))
        return
    if not args.gate0:
        raise SystemExit("EXP-D02 : seuls --gate0 et --rapport sont autorisés ; la grille attend le second GO du porteur")
    run_gate0()


if __name__ == "__main__":
    main()
