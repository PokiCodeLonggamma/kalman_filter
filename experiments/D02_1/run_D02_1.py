"""EXP-D02.1 — verrou fixe de 26 barres et WFO de H_exit (D02.1a) ; WFO de R0 sur grille fine avec inertie (D02.1b) ;
stress du porteur ; BTC seul. Demande, cadrage et arbitrages du porteur du 2026-10-03 (`RESEARCH_LOG.md`, EXP-D02.1).

Usage, depuis la racine du dépôt : python experiments/D02_1/run_D02_1.py --calcul | --rapport
  --calcul  : contrôle de non-régression bloquant (G1-G5), puis D02.1a, D02.1b et stress → resultats_D02_1.csv,
              annuel_D02_1.csv, comparaisons_D02_1.csv, parametres_D02_1.csv, cartes_D02_1.npz, trades_D02_1.csv.gz,
              diagnostics_D02_1.json, controles_D02_1.json, figures/, rapport_D02_1.md.
  --rapport : régénère rapport_D02_1.md (narratif_D02_1.md écrit à la main, puis annexes), sans calcul.

Règles fixées avant le calcul (porteur, 2026-10-03)
- Données : BTC/USD Bitstamp 2013-2025, panne de janvier 2015 retirée (D02.0) ; 22 semestres hors échantillon, du S1
  2015 au S2 2025 ; IS = les 24 mois précédents ; frais 5 bps (choix en IS, lecture principale), 10 bps en stress ;
  capital à 0,25 % par ATR14(t), levier ≤ 1x, PnL et MDD à 1x à côté.
- Verrou (cooldown) de 26 barres pour tous les tests, compté depuis le signal ; option C : si H_exit > 26 et qu'une
  entrée survient alors que le trade précédent est ouvert, elle clôt la position (une position, levier ≤ 1x).
- D02.1a : RE-1 gelée (seuils BTC gelés, R0 = 100, frontière 0,85 ; ses 2 075 entrées) ; H_exit de 6 à 60 au pas de
  2 ; choix par semestre, règle de D02 inchangée (centre de la plus grande zone à Calmar > 0 ; égalités et repli vers
  H = 26). Annexe : effet trade par trade sans la coupure (entrées figées, I-M16).
- D02.1b : WFO-R0 de D02 (H = 26, frontière 0,85, seuils réestimés sur chaque IS et pour chaque R0) sur la grille
  {10, 25, 50, 75, 100, 150, 200, 300, 500} ; inertie : égalité au centre → la case la plus proche du R0 précédent
  (première fenêtre : meilleur Calmar IS) ; aucune zone → R0 précédent (première fenêtre : meilleur Calmar IS défini).
  Décomposition 2 × 2 (grille 5 / 9 × règle de D02 / inertie) ; candidate = grille 9 avec inertie.
- Stress, pour toutes les séries et tous les comparateurs : 10 bps ; retrait du 1 % meilleur (⌈1 % · n⌉ trades,
  rendement net en ATR, chaque série retire les siens) ; les deux combinés.
- Lecture (sans seuil) : 8 métriques ; écarts appariés par mois (`optimization.compare`, règles de D02 ; « surpasse »
  de D02 rapporté) ; effet trade par trade à entrées égales ; périodes 2015-2019 et 2020-2025 ; queues ; choix.

Contrôle de non-régression (bloquant, avant tout résultat)
- G1 données : empreinte de la série BTC 2013-2025 = audit D02.0 ; réserve 2026 tronquée ; panne de 215 barres ;
  22 semestres.
- G2 noyau = RE-1 sur BTC 2020-2025 : contrôles G0-1, G0-5 et G0-6 de D02 repassés (1 080 trades identiques).
- G3 D02 reproduit avec le verrou par défaut (= H) : cartes IS des branches R0 et H identiques à cartes_D02.npz au bit
  près, choix identiques à parametres_D02.csv, séries RE-1 gelée, Contrôle, WFO-R0 et WFO-H identiques à
  trades_D02.csv.gz (barres, sens, stop, gap ; rendement à la précision du fichier, 10 chiffres).
- G4 verrou de 26 ≥ H : séries de RE-1 gelée à H = 6, 16 et 26 identiques à `envelope.lock_trades` (D01.6).
- G5 population constante : avec le verrou de 26, entrées hors échantillon identiques à celles de RE-1 gelée à chaque
  H de la grille ; part des trades clos par l'entrée suivante publiée (lecture descriptive, H fixe).
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import re
import subprocess
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


D02 = _load("run_D02", ROOT / "experiments" / "D02" / "run_D02.py")
D02_0, D01 = D02.D02_0, D02.D01

from anatomy import build_atlas  # noqa: E402
from envelope import effect_ci  # noqa: E402
from envelope.decouple import lock_trades  # noqa: E402
from estimand.stoploss import TRADE_COLUMNS  # noqa: E402
from indicator import KalmanParams  # noqa: E402
from optimization import (GRID_H, GRID_R0, GRID_R0_FIN, RE1_INDEX, AssetData, Params, axis_schedule,  # noqa: E402
                          drop_best, evaluate_is, frozen_entries, oos_candidates, paired_comparison, run_oos,
                          series_stats, signal_table, superseded, walk_forward_windows)
from optimization.walkforward import METRICS  # noqa: E402
from strategy import load_asset  # noqa: E402
from strategy.re1 import N_BOOT  # noqa: E402
from utils.data_loader import meta_path, sha256_file  # noqa: E402

UTC = "UTC"
BPS = 1e4
D02_DIR = ROOT / "experiments" / "D02"
CSV = D02.SERIES["BTC"][0]
FIG = HERE / "figures"
LOCK = 26
GRID_A = ((100.0,), GRID_H, (0.85,))
GRID_B5 = (GRID_R0, (26,), (0.85,))
GRID_B9 = (GRID_R0_FIN, (26,), (0.85,))
I5 = [GRID_R0_FIN.index(r) for r in GRID_R0]
REF_H, REF5, REF9 = GRID_H.index(26), GRID_R0.index(100.0), GRID_R0_FIN.index(100.0)
KEY = ["signal_bar", "entry_bar", "side"]

RE1 = "RE-1 gelée"
CTRL = "Contrôle"
WH_D02 = "WFO-H (D02)"
WR_D02 = "WFO-R0 (D02)"
WH_EXIT = "WFO-H_exit verrou 26"
WR5_IN = "WFO-R0 grille 5 inertie"
WR9 = "WFO-R0 grille 9"
WR9_IN = "WFO-R0 grille 9 inertie"
NAMES = [RE1, CTRL, WH_D02, WR_D02, WH_EXIT, WR5_IN, WR9, WR9_IN]
NEW = [WH_EXIT, WR5_IN, WR9, WR9_IN]
D02_NAMES = {RE1: "RE-1 gelée", CTRL: "Contrôle", WR_D02: "WFO-R0", WH_D02: "WFO-H"}
PAIRS = [(WH_EXIT, WH_D02, "D02.1a contre D02"), (WR9_IN, WR_D02, "D02.1b contre D02"),
         (WR5_IN, WR_D02, "décomposition"), (WR9, WR_D02, "décomposition"), (WR9_IN, WR9, "décomposition")]
PERIODS = {"2015-2025": ("2015-01-01", "2026-01-01", 11.0), "2015-2019": ("2015-01-01", "2020-01-01", 5.0),
           "2020-2025": ("2020-01-01", "2026-01-01", 6.0)}
READINGS = {"5 bps": (5.0, False), "10 bps": (10.0, False), "5 bps sans top 1 %": (5.0, True),
            "10 bps sans top 1 %": (10.0, True)}


def stop(msg: str):
    raise SystemExit(f"D02.1, contrôle de non-régression : {msg} : arrêt")


def ts(x: str) -> pd.Timestamp:
    return pd.Timestamp(x, tz=UTC)


# ── Données : un atlas par R0 de la grille fine ─────────────────────────────────
def prepare_btc() -> tuple[AssetData, dict]:
    """Comme `run_D02.prepare_d02` pour BTC (empreinte vérifiée en G1, réserve 2026 tronquée, panne retirée), avec un
    atlas par R0 de la grille fine."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        df, _ = load_asset(CSV)
    mask = D02_0.outage_mask(df)
    df = df[~mask].reset_index(drop=True)
    bars = df[["time", "open", "high", "low", "close"]].copy()
    tabs, atr0, info = {}, None, {"panne_barres_retirees": int(mask.sum()), "atlas_s": {}}
    for r0 in GRID_R0_FIN:
        t0 = time.time()
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            atlas, _, _, atr = build_atlas(df, kalman=KalmanParams(R0=r0))
        if atr0 is None:
            atr0 = atr
        elif not np.array_equal(atr, atr0, equal_nan=True):
            stop("ATR14 dépendant de R0")
        tabs[r0] = signal_table(bars, atlas, atr)
        info["atlas_s"][f"{r0:g}"] = round(time.time() - t0, 1)
        info[f"signaux_R0_{r0:g}"] = len(atlas)
        print(f"atlas R0 = {r0:g} : {len(atlas)} signaux ({info['atlas_s'][f'{r0:g}']} s)", flush=True)
    atr_bps = atr0 / bars.close.to_numpy() * BPS
    if not np.array_equal(atr_bps[tabs[100.0].t], tabs[100.0].atr_bps):
        stop("ATR14 en bps par barre différent de celui de l'atlas")
    info.update({"barres": len(bars), "premiere": str(bars.time.iat[0]), "derniere": str(bars.time.iat[-1])})
    return AssetData("BTC", bars, tabs, atr_bps, 5.0), info


def make_series(data: AssetData, windows, choix, thresholds: str, lock) -> dict:
    """Série hors échantillon d'un calendrier (liste de (Params, info) ou de Params) : course continue, familles."""
    sched = [c[0] if isinstance(c, tuple) else c for c in choix]
    cands = oos_candidates(data, windows, sched, thresholds)
    tr = run_oos(data, cands, lock=lock)
    fam = pd.Series(np.where(np.isnan(cands[3]), "F2b", "F3"), index=cands[0])
    return {"trades": tr, "cands": cands, "fam": fam, "sched": sched,
            "choix": [c for c in choix if isinstance(c, tuple)]}


# ── Contrôle de non-régression ──────────────────────────────────────────────────
def g1_donnees() -> dict:
    a02 = json.loads((ROOT / "experiments" / "D02_0" / "audit_donnees_D02_0.json").read_text(encoding="utf-8"))
    meta = json.loads(meta_path(CSV).read_text(encoding="utf-8"))
    sha = sha256_file(CSV)
    if not sha == meta["sha256"] == a02["BTC"]["sha256"]:
        stop("G1 : empreinte de la série BTC différente de l'audit D02.0")
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        df, bars = load_asset(CSV)
    if bars.time.iat[-1] >= ts("2026-01-01"):
        stop("G1 : barre de 2026")
    panne = int(D02_0.outage_mask(df).sum())
    if panne != 215:
        stop("G1 : panne de janvier 2015 différente de 215 barres")
    ws = walk_forward_windows(bars.time.iat[0])
    if len(ws) != 22:
        stop(f"G1 : {len(ws)} semestres au lieu de 22")
    return {"sha256": sha[:16], "derniere_barre": str(bars.time.iat[-1]), "panne_barres": panne, "semestres": len(ws),
            "premier_oos": str(ws[0].oos_start.date())}


def g3_d02(windows, evs9, evs_h, series) -> dict:
    z = np.load(D02_DIR / "cartes_D02.npz")
    i0, j0, k0 = RE1_INDEX
    for w, e9, eh in zip(windows, evs9, evs_h):
        for key in METRICS:
            full = z[f"BTC|{w.k}|{key}"]
            if not np.array_equal(e9[key][I5, 0, 0], full[:, j0, k0], equal_nan=True):
                stop(f"G3 : carte IS de la branche R0, semestre {w.k}, {key}")
            if not np.array_equal(eh[key][0, :, 0], full[i0, :, k0], equal_nan=True):
                stop(f"G3 : carte IS de la branche H, semestre {w.k}, {key}")
        for key in ("leg_p50", "nis_p75", "n_signaux"):
            if not np.array_equal(e9[key][I5], z[f"BTC|{w.k}|{key}"], equal_nan=True):
                stop(f"G3 : seuils de l'IS, semestre {w.k}, {key}")
    p = pd.read_csv(D02_DIR / "parametres_D02.csv")
    out = {"cartes": f"{len(windows)} semestres × (5 R0 + 28 H) cases identiques au bit près"}
    for branch, name, attr in (("R0", WR_D02, "r0"), ("H", WH_D02, "h")):
        ref = p[(p.actif == "BTC") & (p.branche == branch)].sort_values("k")
        got = series[name]["choix"]
        same = (np.allclose([getattr(c[0], attr) for c in got], ref[branch].to_numpy())
                and [c[1]["repli"] for c in got] == ref.repli.tolist()
                and [c[1]["zone"] for c in got] == ref.zone.tolist()
                and [c[1]["n_zones"] for c in got] == ref.n_zones.tolist())
        if not same:
            stop(f"G3 : choix de la branche {branch} différents de parametres_D02.csv")
        out[f"choix_{branch}"] = "identiques"
    stored = pd.read_csv(D02_DIR / "trades_D02.csv.gz")
    stored = stored[stored.actif == "BTC"]
    for mine, theirs in D02_NAMES.items():
        a = series[mine]["trades"].reset_index(drop=True)
        b = stored[stored.variante == theirs].reset_index(drop=True)
        same = (len(a) == len(b)
                and all(np.array_equal(a[c].to_numpy(dtype=np.int64), b[c].to_numpy(dtype=np.int64))
                        for c in ("entry_bar", "exit_bar", "side", "signal_bar", "semestre"))
                and all(np.array_equal(a[c].to_numpy(dtype=bool), b[c].to_numpy(dtype=bool)) for c in ("stop", "gap"))
                and np.allclose(a.ret_gross_bps.to_numpy(), b.ret_gross_bps.to_numpy(), rtol=1e-9, atol=1e-9))
        if not same:
            stop(f"G3 : série {mine} différente de trades_D02.csv.gz")
        out[f"serie_{theirs}"] = f"{len(a)} trades identiques"
    return out


def g4_lock_trades(data: AssetData, windows) -> dict:
    out = {}
    for h in (6, 16, 26):
        cands = oos_candidates(data, windows, [Params(100.0, h, 0.85)] * len(windows), "geles")
        t, s, _, lv, _ = cands
        got = run_oos(data, cands, lock=LOCK).drop(columns="semestre")
        if not got.equals(lock_trades(data.bars, t, s, h, LOCK, lv)):
            stop(f"G4 : verrou de 26 à H = {h} différent de lock_trades")
        out[f"H_{h}"] = f"{len(got)} trades identiques à lock_trades"
    return out


def g5_population(data: AssetData, windows, re1: pd.DataFrame) -> tuple[dict, list[dict]]:
    """Entrées constantes ; part des trades clos par l'entrée suivante et espérance à H fixe (lecture descriptive)."""
    rows = []
    for h in GRID_H:
        cands = oos_candidates(data, windows, [Params(100.0, h, 0.85)] * len(windows), "geles")
        tr = run_oos(data, cands, lock=LOCK)
        if not tr[KEY].equals(re1[KEY]):
            stop(f"G5 : verrou de 26 à H = {h}, entrées différentes de RE-1 gelée")
        net = (tr.ret_gross_bps.to_numpy() - 5.0) / data.atr_bps[tr.signal_bar.to_numpy()]
        rows.append({"H": h, "trades": len(tr), "part_coupee": float(superseded(tr, h).mean()),
                     "part_stop": float(tr.stop.mean()), "esperance_atr_5bps": float(net.mean())})
    return {"entrees_constantes": f"2 075 entrées identiques pour les {len(GRID_H)} valeurs de H"}, rows


# ── Mesures ─────────────────────────────────────────────────────────────────────
def subset(s: dict, data: AssetData, start: str, end: str) -> dict:
    """Trades et candidats dont l'entrée tombe dans [start, end)."""
    a, b = ts(start), ts(end)
    tr = s["trades"]
    et = data.bars.time.iloc[tr.entry_bar.to_numpy()].to_numpy()
    sel = (et >= a) & (et < b)
    ct = data.bars.time.iloc[np.minimum(s["cands"][0] + 1, len(data.bars) - 1)].to_numpy()
    csel = (ct >= a) & (ct < b)
    return {"trades": tr[sel].reset_index(drop=True), "cands": tuple(c[csel] for c in s["cands"]), "fam": s["fam"]}


def stressed(s: dict, data: AssetData, fee: float, drop: bool) -> dict:
    return dict(s, trades=drop_best(s["trades"], data.atr_bps, fee)) if drop else s


def compare_rows(data: AssetData, series: dict, label: str, fee: float, drop: bool, start: str, end: str) -> list:
    st = {}
    for n, s in series.items():
        sub = subset(s, data, start, end)
        st[n] = series_stats(stressed(sub, data, fee, drop)["trades"], data.bars, data.atr_bps, fee, ts(start), ts(end))
    rows = []
    for a, b, fam in [(n, RE1, "contre RE-1 gelée") for n in NAMES[1:]] + PAIRS:
        c = paired_comparison(st[a], st[b])
        not_worse = bool(c["d_mdd_sorties_hi"] >= 0)
        rows.append({"actif": label, "frais_bps": fee, "famille": fam, "variante": a, "reference": b, **c,
                     "mdd_non_degrade": not_worse,
                     "surpasse": bool(c["esperance_tangible"] and c["rendement_tangible"] and not_worse)})
    return rows


def trade_effects(data: AssetData, re1: pd.DataFrame, tr: pd.DataFrame, fz: pd.DataFrame) -> dict:
    """Effet apparié trade par trade (mêmes entrées) de D02.1a, avec et sans la coupure, par période."""
    atr_s = pd.Series(data.atr_bps, index=np.arange(len(data.bars)))
    et = data.bars.time.iloc[re1.entry_bar.to_numpy()].to_numpy()
    out = {}
    for per, (a, b, _) in PERIODS.items():
        sel = (et >= ts(a)) & (et < ts(b))
        out[per] = {"trades": int(sel.sum()),
                    "avec_coupure": effect_ci(tr[sel], re1[sel], data.bars, atr_s, n_boot=N_BOOT),
                    "sans_coupure": effect_ci(fz[sel], re1[sel], data.bars, atr_s, n_boot=N_BOOT)}
    return out


def choice_rows(name: str, windows, choix, evs, axis: int, grid) -> list[dict]:
    """Choix de chaque semestre, avec le profil IS de l'axe (meilleur Calmar, Calmar choisi, Calmar de RE-1)."""
    vals = grid[axis]
    ref = REF_H if axis == 1 else vals.index(100.0)
    rows = []
    for w, (p, info), ev in zip(windows, choix, evs):
        c = np.asarray(ev["calmar_r25"], dtype=float).reshape(-1)
        e = np.asarray(ev["esperance_atr"], dtype=float).reshape(-1)
        best = int(np.nanargmax(np.where(e > 0, c, np.nan))) if np.isfinite(np.where(e > 0, c, np.nan)).any() else None
        i = info["index"]
        rows.append({"variante": name, "k": w.k, "oos_debut": str(w.oos_start.date()), "R0": p.r0, "H": p.h,
                     "repli": info["repli"], "inertie": info.get("inertie"), "zone": info["zone"],
                     "n_zones": info["n_zones"], "n_candidates": info["n_candidates"],
                     "calmar_zone": info["calmar_zone"], "calmar_choisi": float(c[i]),
                     "calmar_re1": float(c[ref]), "meilleur": None if best is None else vals[best],
                     "calmar_meilleur": None if best is None else float(c[best])})
    return rows


# ── Calcul ──────────────────────────────────────────────────────────────────────
def run_calcul() -> None:
    t0 = time.time()
    commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, capture_output=True,
                            text=True).stdout.strip()
    ctrl = {"date": pd.Timestamp.now(tz="UTC").strftime("%Y-%m-%d %H:%M UTC"), "commit": commit}
    ctrl["G1"] = g1_donnees()
    ctrl["G2"], _ = D02.g0_btc(D01.prepare("BTC"))
    print(f"G1, G2 passés ({time.time() - t0:.0f} s)", flush=True)
    data, info = prepare_btc()
    windows = walk_forward_windows(data.bars.time.iat[0])
    if len(windows) != 22:
        stop("22 semestres attendus")
    t1 = time.time()
    evs9 = [evaluate_is(data, w, grid=GRID_B9, lock=LOCK) for w in windows]          # D02.1b (verrou = H = 26)
    evs5 = [{k: np.asarray(v)[I5] for k, v in ev.items()} for ev in evs9]
    evs_h = [evaluate_is(data, w, grid=GRID_A) for w in windows]                       # WFO-H de D02 (verrou = H)
    evs_a = [evaluate_is(data, w, grid=GRID_A, lock=LOCK, thresholds="geles") for w in windows]   # D02.1a
    info["evaluations_is"] = len(windows) * (len(GRID_R0_FIN) + 2 * len(GRID_H))
    info["grille_s"] = round(time.time() - t1, 1)
    re1 = [Params(100.0, 26, 0.85)] * len(windows)
    series = {RE1: make_series(data, windows, re1, "geles", None),
              CTRL: make_series(data, windows, re1, "fenetre", None),
              WH_D02: make_series(data, windows, axis_schedule(evs_h, GRID_A, 1, REF_H), "fenetre", None),
              WR_D02: make_series(data, windows, axis_schedule(evs5, GRID_B5, 0, REF5), "fenetre", None)}
    ctrl["G3"] = g3_d02(windows, evs9, evs_h, series)
    ctrl["G4"] = g4_lock_trades(data, windows)
    base = series[RE1]["trades"][TRADE_COLUMNS].reset_index(drop=True)
    ctrl["G5"], g5_rows = g5_population(data, windows, base)
    print(f"G3, G4, G5 passés : non-régression validée ({time.time() - t0:.0f} s)", flush=True)

    # D02.1a — WFO de H_exit, verrou de 26, entrées de RE-1 gelée
    series[WH_EXIT] = make_series(data, windows, axis_schedule(evs_a, GRID_A, 1, REF_H), "geles", LOCK)
    tr_a = series[WH_EXIT]["trades"][TRADE_COLUMNS].reset_index(drop=True)
    if not tr_a[KEY].equals(base[KEY]):
        stop("D02.1a : entrées différentes de RE-1 gelée")
    t_c, _, h_c, lv_c, _ = series[WH_EXIT]["cands"]
    h_tr = pd.Series(h_c, index=t_c).reindex(tr_a.signal_bar.to_numpy()).to_numpy()
    lv_tr = pd.Series(lv_c, index=t_c).reindex(tr_a.signal_bar.to_numpy()).to_numpy()
    fz = frozen_entries(data.bars, base, h_tr, lv_tr)                                   # sans la coupure
    cut = superseded(tr_a, h_tr)
    diag_a = {"effets_trade_par_trade": trade_effects(data, base, tr_a, fz),
              "part_coupee": float(cut.mean()), "coupes": int(cut.sum()),
              "part_coupee_si_H_sup_26": float(cut[h_tr > 26].mean()) if (h_tr > 26).any() else np.nan,
              "h_moyen": float(h_tr.mean()), "part_h_26": float((h_tr == 26).mean()),
              "profil_H_fixe": g5_rows}

    # D02.1b — WFO de R0 : grille 5 / 9 × règle de D02 / inertie
    series[WR5_IN] = make_series(data, windows, axis_schedule(evs5, GRID_B5, 0, REF5, inertie=True), "fenetre", LOCK)
    series[WR9] = make_series(data, windows, axis_schedule(evs9, GRID_B9, 0, REF9), "fenetre", LOCK)
    series[WR9_IN] = make_series(data, windows, axis_schedule(evs9, GRID_B9, 0, REF9, inertie=True), "fenetre", LOCK)
    series = {n: series[n] for n in NAMES}
    print(f"séries hors échantillon faites ({time.time() - t0:.0f} s)", flush=True)

    rows, years, comps = [], [], []
    for per, (a, b, ny) in PERIODS.items():
        for rd, (fee, drop) in READINGS.items():
            if per != "2015-2025" and drop:
                continue
            label = f"{per} · {rd}"
            for name, s in series.items():
                m, y = D02.measure_d02(label, name, stressed(subset(s, data, a, b), data, fee, drop), data, fee, ny)
                m.update({"periode": per, "lecture": rd})
                rows.append(m)
                if per == "2015-2025" and rd == "5 bps":
                    years.append(y)
            comps += compare_rows(data, series, label, fee, drop, a, b)
    print(f"mesures et {len(comps)} comparaisons faites ({time.time() - t0:.0f} s)", flush=True)

    choices = (choice_rows(WH_D02, windows, series[WH_D02]["choix"], evs_h, 1, GRID_A)
               + choice_rows(WH_EXIT, windows, series[WH_EXIT]["choix"], evs_a, 1, GRID_A))
    for name, evs, grid in ((WR_D02, evs5, GRID_B5), (WR5_IN, evs5, GRID_B5), (WR9, evs9, GRID_B9),
                            (WR9_IN, evs9, GRID_B9)):
        choices += choice_rows(name, windows, series[name]["choix"], evs, 0, grid)
    ch = pd.DataFrame(choices)
    diag_b = {}
    for name in (WR_D02, WR5_IN, WR9, WR9_IN):
        g = ch[ch.variante == name]
        diag_b[name] = {"chemin_R0": [float(v) for v in g.R0], "replis": int(g.repli.sum()),
                        "egalites_tranchees_par_inertie": int((g.inertie == "egalite").sum()),
                        "aucune_zone_inertie": int((g.inertie == "aucune zone").sum()),
                        "egalites_paires": int(((g.zone % 2 == 0) & (g.zone > 0)).sum()),
                        "semestres_R0_100": int((g.R0 == 100.0).sum())}
    ga = ch[ch.variante == WH_EXIT]
    diag_a.update({"chemin_H": [int(v) for v in ga.H], "replis": int(ga.repli.sum()),
                   "zone_axe_entier": int((ga.zone == len(GRID_H)).sum()), "zone_23_et_plus": int((ga.zone >= 23).sum())})

    res = pd.DataFrame(rows)
    lead = ["periode", "lecture", "variante", "frais_bps", "annees", "debut", "fin"]
    res = res[lead + [c for c in res.columns if c not in lead]]
    res.to_csv(HERE / "resultats_D02_1.csv", index=False, float_format="%.6g")
    pd.concat(years, ignore_index=True).to_csv(HERE / "annuel_D02_1.csv", index=False, float_format="%.6g")
    pd.DataFrame(comps).to_csv(HERE / "comparaisons_D02_1.csv", index=False, float_format="%.6g")
    ch.to_csv(HERE / "parametres_D02_1.csv", index=False, float_format="%.6g")
    cartes = {}
    for prefix, evs in (("A", evs_a), ("B9", evs9)):
        for w, ev in zip(windows, evs):
            for k, v in ev.items():
                cartes[f"{prefix}|{w.k}|{k}"] = v
    np.savez_compressed(HERE / "cartes_D02_1.npz", **cartes)
    trades = []
    for name in NEW:
        tr = series[name]["trades"].copy()
        tr.insert(0, "variante", name)
        tr["entree"] = data.bars.time.iloc[tr.entry_bar.to_numpy()].to_numpy()
        if name == WH_EXIT:
            tr["coupe"] = cut
        trades.append(tr)
    (pd.concat(trades, ignore_index=True).drop(columns=["entry_price", "exit_price"])    # aucun prix publié
     .to_csv(HERE / "trades_D02_1.csv.gz", index=False, float_format="%.10g"))
    diags = {"donnees": info, "D02_1a": diag_a, "D02_1b": diag_b,
             "trades": {n: len(s["trades"]) for n, s in series.items()}}
    ctrl["duree_s"] = round(time.time() - t0)
    ctrl["comparaisons"] = len(comps)
    (HERE / "diagnostics_D02_1.json").write_text(json.dumps(D01.jsonable(diags), ensure_ascii=False, indent=1),
                                                 encoding="utf-8")
    (HERE / "controles_D02_1.json").write_text(json.dumps(D01.jsonable(ctrl), ensure_ascii=False, indent=1),
                                               encoding="utf-8")
    figures(data, windows, series, evs_a, evs9)
    write_rapport()
    print(f"D02.1 : {len(res)} lignes de résultats, {len(comps)} comparaisons en {ctrl['duree_s']} s ; sorties dans {HERE}")


def figures(data: AssetData, windows, series: dict, evs_a, evs9) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    FIG.mkdir(parents=True, exist_ok=True)
    lab = [f"{w.oos_start.year}-S{1 if w.oos_start.month == 1 else 2}" for w in windows]
    x = np.arange(len(windows))
    fig, axes = plt.subplots(1, 2, figsize=(16, 7))
    ca = np.array([ev["calmar_r25"][0, :, 0] for ev in evs_a]).T
    cb = np.array([ev["calmar_r25"][:, 0, 0] for ev in evs9]).T
    for ax, c, ticks, title in ((axes[0], ca, [str(h) for h in GRID_H], "D02.1a : Calmar IS selon H_exit (verrou 26)"),
                                (axes[1], cb, [f"{r:g}" for r in GRID_R0_FIN], "D02.1b : Calmar IS selon R0")):
        im = ax.imshow(np.clip(c, -2, 2), aspect="auto", origin="lower", cmap="RdYlGn", vmin=-2, vmax=2)
        ax.set_xticks(x, lab, rotation=90, fontsize=7)
        step = 2 if len(ticks) > 10 else 1
        ax.set_yticks(np.arange(len(ticks))[::step], ticks[::step], fontsize=7)
        ax.set_title(title, fontsize=10)
        fig.colorbar(im, ax=ax, fraction=0.04, label="Calmar IS (borné à ±2)")
    axes[0].plot(x, [GRID_H.index(p.h) for p in series[WH_EXIT]["sched"]], "ko-", ms=4, lw=1, label=WH_EXIT)
    axes[0].axhline(REF_H, color="b", lw=0.8, ls="--", label="H = 26 (RE-1)")
    axes[0].legend(fontsize=7, loc="upper left")
    for name, mk in ((WR_D02, "s"), (WR9, "x"), (WR9_IN, "o")):
        axes[1].plot(x, [GRID_R0_FIN.index(p.r0) for p in series[name]["sched"]], mk + "-", ms=5, lw=0.8, label=name)
    axes[1].legend(fontsize=7, loc="upper left")
    fig.tight_layout()
    fig.savefig(FIG / "D02_1_cartes.png", dpi=110)
    plt.close(fig)
    fig, ax = plt.subplots(figsize=(13, 6))
    style = {RE1: ("k", 2.0), WR_D02: ("#7f7f7f", 1.4), WH_EXIT: ("#1f77b4", 1.6), WR9_IN: ("#d62728", 1.6)}
    for name, s in series.items():
        eq = D02.equity_points(s, data, 5.0)
        c, lw = style.get(name, (None, 0.8))
        ax.step(eq.index, 100 * (eq.to_numpy() - 1.0), where="post", color=c, lw=lw,
                alpha=1.0 if name in style else 0.6, label=name)
    ax.axhline(0, color="k", lw=0.5)
    ax.set_title("BTC 2015-2025 : capital hors échantillon (0,25 %/ATR, 5 bps)", fontsize=10)
    ax.set_ylabel("PnL composé (%)")
    ax.grid(alpha=0.3)
    ax.legend(fontsize=8, ncol=2)
    fig.tight_layout()
    fig.savefig(FIG / "D02_1_capital.png", dpi=110)
    plt.close(fig)


# ── Rapport (annexes générées ; narratif_D02_1.md écrit à la main) ──────────────
fr, sg, pct, spct, n_fr, ci, table = D01.fr, D01.sg, D01.pct, D01.spct, D01.n_fr, D01.ci, D01.table


def metrics_table(res: pd.DataFrame, label: str, fee: float, names) -> str:
    r = res[res.variante.isin(names)].copy()
    r["actif"] = r.periode + " · " + r.lecture
    r["variante"] = pd.Categorical(r.variante, names, ordered=True)
    return D02.annex_metrics(r.sort_values("variante"), label, fee)


def comparisons_table(cp: pd.DataFrame, label: str, fee: float, famille: str) -> str:
    return D02.annex_comparisons(cp, label, fee, famille)


def _controls(d: dict) -> str:
    names = {"cartes": "cartes", "choix_R0": "choix de R0", "choix_H": "choix de H"}
    out = []
    for k, v in d.items():
        k = names.get(k, k.replace("serie_", "série ").replace("H_", "H = "))
        out.append(f"{k} : " + re.sub(r"\b(\d)(\d{3})\b", r"\1 \2", str(v)))
    return " ; ".join(out)


def write_rapport() -> None:
    res = pd.read_csv(HERE / "resultats_D02_1.csv")
    cp = pd.read_csv(HERE / "comparaisons_D02_1.csv")
    ch = pd.read_csv(HERE / "parametres_D02_1.csv")
    yr = pd.read_csv(HERE / "annuel_D02_1.csv")
    dg = json.loads((HERE / "diagnostics_D02_1.json").read_text(encoding="utf-8"))
    ct = json.loads((HERE / "controles_D02_1.json").read_text(encoding="utf-8"))
    narr = HERE / "narratif_D02_1.md"
    main = "2015-2025 · 5 bps"
    out = [narr.read_text(encoding="utf-8") if narr.exists() else "# EXP-D02.1 — rapport (narratif à rédiger)\n",
           "", "---", "", "# Annexes générées (`run_D02_1.py --calcul`, puis `--rapport`)", "",
           f"Calcul du {ct['date']}, commit `{ct['commit']}`, {ct['duree_s']} s ; {ct['comparaisons']} comparaisons "
           "appariées publiées.", "", "## A1. Contrôle de non-régression (bloquant, passé)", ""]
    g1 = ct["G1"]
    out += [f"- G1 données : empreinte `{g1['sha256']}…` conforme à l'audit D02.0 ; dernière barre {g1['derniere_barre']} ;"
            f" panne de {g1['panne_barres']} barres retirée ; {g1['semestres']} semestres dès le {g1['premier_oos']}.",
            f"- G2 noyau : {n_fr(ct['G2']['identite']['trades'])} trades de RE-1 sur BTC 2020-2025 identiques "
            "(contrôles G0-1, G0-5, G0-6 de D02 repassés).",
            "- G3 D02 reproduit avec le verrou par défaut : " + _controls(ct["G3"]) + ".",
            "- G4 verrou ≥ H = `lock_trades` : " + _controls(ct["G4"]) + ".",
            f"- G5 population constante : {ct['G5']['entrees_constantes']}.", ""]
    a = dg["D02_1a"]
    out += ["## A2. D02.1a — WFO de H_exit, verrou de 26 barres, entrées de RE-1 gelée", "",
            f"**Résultats nets, {main}**", "", metrics_table(res, main, 5.0, [RE1, WH_D02, WH_EXIT]), "",
            "**Stress à 10 bps**", "", metrics_table(res, "2015-2025 · 10 bps", 10.0, [RE1, WH_D02, WH_EXIT]), "",
            "**Effet trade par trade à entrées égales (I-M16) : WFO-H_exit − RE-1 gelée**", "",
            table(["Période", "Trades", "Avec la coupure (option C) : ATR [IC] ; bps [IC]",
                   "Sans la coupure (entrées figées) : ATR [IC] ; bps [IC]"],
                  [[per, n_fr(v["trades"]),
                    f"{ci(v['avec_coupure']['effet_atr'], v['avec_coupure']['effet_atr_lo'], v['avec_coupure']['effet_atr_hi'], 3)} ; "
                    f"{ci(v['avec_coupure']['effet_bps'], v['avec_coupure']['effet_bps_lo'], v['avec_coupure']['effet_bps_hi'], 1)}",
                    f"{ci(v['sans_coupure']['effet_atr'], v['sans_coupure']['effet_atr_lo'], v['sans_coupure']['effet_atr_hi'], 3)} ; "
                    f"{ci(v['sans_coupure']['effet_bps'], v['sans_coupure']['effet_bps_lo'], v['sans_coupure']['effet_bps_hi'], 1)}"]
                   for per, v in a["effets_trade_par_trade"].items()]), "",
            f"Trades clos par l'entrée suivante : {n_fr(a['coupes'])} ({pct(a['part_coupee'], 1)} ; "
            f"{pct(a['part_coupee_si_H_sup_26'], 1)} des trades à H > 26). H moyen {fr(a['h_moyen'], 1)} ; H = 26 pour "
            f"{pct(a['part_h_26'], 0)} des trades ; replis sur H = 26 : {a['replis']} semestres ; zone couvrant tout l'axe "
            f"(28 cases) : {a['zone_axe_entier']} semestre{'s' if a['zone_axe_entier'] > 1 else ''}, 23 cases ou plus : "
            f"{a['zone_23_et_plus']}.", "",
            "**Profil à H fixe sur les mêmes entrées (lecture descriptive, 2015-2025, 5 bps ; aucun choix)**", "",
            table(["H", "Espérance ATR", "Part close par l'entrée suivante", "Part stoppée"],
                  [[str(r["H"]), sg(r["esperance_atr_5bps"], 3), pct(r["part_coupee"], 1), pct(r["part_stop"], 0)]
                   for r in a["profil_H_fixe"]]), "",
            "**Comparaisons appariées par mois (5 bps)**", "",
            comparisons_table(cp[cp.variante.isin([WH_D02, WH_EXIT]) & (cp.reference.isin([RE1, WH_D02]))], main, 5.0,
                              "contre RE-1 gelée"), "",
            comparisons_table(cp, main, 5.0, "D02.1a contre D02"), ""]
    out += ["## A3. D02.1b — WFO de R0, grille fine et inertie", "",
            f"**Résultats nets, {main}**", "", metrics_table(res, main, 5.0, [RE1, CTRL, WR_D02, WR5_IN, WR9, WR9_IN]),
            "", "**Stress à 10 bps**", "",
            metrics_table(res, "2015-2025 · 10 bps", 10.0, [RE1, CTRL, WR_D02, WR5_IN, WR9, WR9_IN]), "",
            "**Comparaisons appariées par mois contre RE-1 gelée (5 bps)**", "",
            comparisons_table(cp[cp.variante.isin([CTRL, WR_D02, WR5_IN, WR9, WR9_IN])], main, 5.0, "contre RE-1 gelée"),
            "", "**Candidate contre WFO-R0 de D02, et décomposition 2 × 2 (5 bps)**", "",
            comparisons_table(cp, main, 5.0, "D02.1b contre D02"), "", comparisons_table(cp, main, 5.0, "décomposition"),
            "", "**R0 choisi à chaque semestre**", ""]
    sem = ch[ch.variante == WR9_IN].oos_debut.tolist()
    rows = []
    for name in (WR_D02, WR5_IN, WR9, WR9_IN):
        g = ch[ch.variante == name]
        mark = ["*" if i == "egalite" else ("°" if i == "aucune zone" else "") for i in g.inertie.fillna("")]
        rows.append([name] + [f"{v:g}{m}" for v, m in zip(g.R0, mark)])
    out += [table(["Variante"] + [s[:7] for s in sem], rows), "",
            "\\* égalité au centre tranchée par l'inertie ; ° aucune zone, R0 précédent gardé.", "",
            table(["Variante", "Replis", "Égalités tranchées par l'inertie", "Zones paires", "Semestres à R0 = 100"],
                  [[n, str(v["replis"]), str(v["egalites_tranchees_par_inertie"]), str(v["egalites_paires"]),
                    str(v["semestres_R0_100"])] for n, v in dg["D02_1b"].items()]), ""]
    out += ["## A4. Stress du porteur (toutes les séries, 2015-2025)", ""]
    for rd, (fee, _) in READINGS.items():
        label = f"2015-2025 · {rd}"
        out += [f"**{rd}**", "", metrics_table(res, label, fee, NAMES), "",
                comparisons_table(cp, label, fee, "contre RE-1 gelée"), ""]
        if rd != "5 bps":
            out += [comparisons_table(cp, label, fee, "D02.1a contre D02"), "",
                    comparisons_table(cp, label, fee, "D02.1b contre D02"), ""]
    out += ["## A5. Périodes (5 bps)", ""]
    for per in ("2015-2019", "2020-2025"):
        label = f"{per} · 5 bps"
        out += [f"**{per}**", "", metrics_table(res, label, 5.0, NAMES), "",
                comparisons_table(cp, label, 5.0, "contre RE-1 gelée"), "",
                comparisons_table(cp, label, 5.0, "D02.1a contre D02"), "",
                comparisons_table(cp, label, 5.0, "D02.1b contre D02"), ""]
    piv = yr.pivot_table(index="annee", columns="variante", values="esperance_atr", sort=False)
    out += ["## A6. Espérance nette par année (ATR, 5 bps)", "",
            table(["Année"] + NAMES, [[str(int(y))] + [sg(piv.loc[y, n], 3) if n in piv.columns else "—" for n in NAMES]
                                      for y in piv.index]), "",
            "## A7. Queues et sous-familles (2015-2025, 5 bps)", ""]
    r = res[res.variante.isin(NAMES)].copy()
    r["actif"] = r.periode + " · " + r.lecture
    out += [D02.annex_tails(r, main, 5.0), "", "## A8. Figures", "",
            "![Cartes IS et choix](figures/D02_1_cartes.png)", "", "![Capital hors échantillon](figures/D02_1_capital.png)",
            ""]
    (HERE / "rapport_D02_1.md").write_text("\n".join(out) + "\n", encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--calcul", action="store_true", help="non-régression bloquante, D02.1a, D02.1b, stress, rapport")
    ap.add_argument("--rapport", action="store_true", help="régénère rapport_D02_1.md depuis les sorties, sans calcul")
    args = ap.parse_args()
    if args.rapport:
        write_rapport()
        return
    if not args.calcul:
        raise SystemExit("EXP-D02.1 : préciser --calcul ou --rapport")
    run_calcul()


if __name__ == "__main__":
    main()
