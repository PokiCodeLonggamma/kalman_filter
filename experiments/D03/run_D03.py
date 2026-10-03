"""EXP-D03 — profilage des extrêmes, filtre de compression (ATR) et portefeuille BTC + SOL, sur RE-1 gelée, version
finale du moteur. Demande du porteur du 2026-10-03 (`RESEARCH_LOG.md`, entrée EXP-D03).

Usage, depuis la racine du dépôt : python experiments/D03/run_D03.py --calcul | --rapport
  --calcul  : contrôles bloquants, actions 1 à 3 → profil_D03.csv, resultats_D03.csv, comparaisons_D03.csv,
              portefeuille_D03.csv, diagnostics_D03.json, controles_D03.json, figures/, rapport_D03.md.
  --rapport : régénère rapport_D03.md (narratif_D03.md écrit à la main, puis annexes), sans calcul.

Règles fixées avant le calcul (porteur, 2026-10-03 ; aucune optimisation)
- Données : BTC/USD Bitstamp 2013-2025, panne de janvier 2015 retirée ; SOL/USD Coinbase dès le 2021-06-17 ; barres de
  30 min ; 2026, ETH et XRP ne sont pas lus. RE-1 gelée : seuils BTC gelés, R0 = 100, frontière 0,85, H = 26, verrou de
  26 barres ; 5 bps (10 bps en lecture) ; 0,25 % du capital par ATR14(t), levier ≤ 1x par position ; PnL et MDD à 1x.
- Action 1 (descriptive, BTC 2015-2025, 2 075 trades) : Alpha = les ⌈5 % · n⌉ = 104 meilleurs trades par rendement
  net en ATR (poids dans le capital à 0,25 %/ATR) ; Usure = les autres. Contrôle d'artefact de définition : même
  découpage par rendement net en bps, le rang en ATR favorisant mécaniquement les ATR bas. Variables lues à la clôture
  du signal t : ATR14 en bps et son rang sur 24 mois glissants ; `leg_atr` et son rapport au P50 local (médiane des
  signaux des 24 mois glissants, population du seuil de RE-1) ; %B et largeur relative des bandes de Bollinger (20,
  2 écarts-types de population, convention TradingView), %B orienté dans le sens du trade, rang de la largeur sur 24
  mois ; écart à l'EMA 200 des clôtures 30 min (EMA de C04) en ATR, orienté dans le sens du trade ; heure UTC de
  l'entrée.
- Action 2 : règle d'entrée du porteur, ATR14_bps(t) ≤ P60 glissant de l'ATR14_bps des barres de ]t − 730 j, t]
  (causale ; aucun seuil fixe tiré de l'action 1, ce serait un choix en échantillon). Deux lectures : entrées figées
  (le verrou suit les signaux de RE-1, les trades filtrés ne sont pas pris : effet pur du filtre, I-M16) et séquentielle
  (le verrou ne suit que les entrées prises). Lecture hors de l'échantillon de l'idée : même filtre sur SOL dès que la
  fenêtre couvre 700 jours, entrées du 2023-07-01 au 2025-12-31.
- Action 3 : portefeuille RE-1 gelée BTC + SOL sur un capital commun (`envelope.portfolio_equity`), 0,25 %/ATR par
  trade sur chaque actif, entrées du 2021-07-01 au 2025-12-31 ; BTC seul et SOL seul sur la même période ; lecture à 1x
  par position (exposition brute jusqu'à 2x). BTC 2021-2025 est dans la période de construction de RE-1 ; SOL est lu en
  transfert (seuils BTC).
- Contrôles bloquants : empreintes des données ; RE-1 gelée BTC 2015-2025 = les 2 075 trades de D02 ; RE-1 gelée SOL =
  `run_re1` et métriques de D01 ; portefeuille d'une seule jambe = capital valorisé du dépôt.
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


D02 = _load("run_D02", ROOT / "experiments" / "D02" / "run_D02.py")
D02_0, D01 = D02.D02_0, D02.D01

from anatomy import build_atlas  # noqa: E402
from context import bollinger, ema, trailing_quantile, trailing_rank  # noqa: E402
from envelope import Leg, equity_curve_sized, portfolio_equity, risk_weights  # noqa: E402
from estimand.stoploss import TRADE_COLUMNS, drawdown_stats  # noqa: E402
from indicator import KalmanParams  # noqa: E402
from optimization import candidates, paired_comparison, run_trades, series_stats, signal_table  # noqa: E402
from strategy import LEG_ATR_P50_BTC, NIS_Z100_P75_BTC, load_asset, metrics, run_re1, sample_years  # noqa: E402
from utils.data_loader import meta_path, sha256_file  # noqa: E402

UTC = "UTC"
BPS = 1e4
FIG = HERE / "figures"
FEES = (5.0, 10.0)
WINDOW, SPAN = "730D", "700D"
KEY = ["signal_bar", "entry_bar", "side"]
P_BTC = ("2015-01-01", "2026-01-01")
P_PORT = ("2021-07-01", "2026-01-01")
P_SOL_FILTRE = ("2023-07-01", "2026-01-01")
PERIODS = {"2015-2025": ("2015-01-01", "2026-01-01"), "2015-2019": ("2015-01-01", "2020-01-01"),
           "2020-2025": ("2020-01-01", "2026-01-01")}
RE1, FIGEES, SEQ = "RE-1 gelée", "RE-1 + filtre ATR (entrées figées)", "RE-1 + filtre ATR (séquentiel)"
VARS = {"atr_bps": "ATR14 (bps)", "atr_rang": "ATR14, rang sur 24 mois", "leg_atr": "leg_atr",
        "leg_rapport": "leg_atr / P50 local", "pctb": "%B (Bollinger 20, 2)", "pctb_sens": "%B orienté",
        "bw": "Largeur de Bollinger (%)", "bw_rang": "Largeur, rang sur 24 mois", "ema_sens": "Écart à l'EMA 200 orienté (ATR)"}


def stop(msg: str):
    raise SystemExit(f"D03, contrôle bloquant : {msg} : arrêt")


def ts(x: str) -> pd.Timestamp:
    return pd.Timestamp(x, tz=UTC)


# ── Données et RE-1 gelée ───────────────────────────────────────────────────────
def prepare(key: str) -> dict:
    """Barres (empreinte vérifiée, réserve 2026 tronquée, panne de 2015 retirée pour BTC), atlas à R0 = 100, table des
    signaux, ATR14 en bps par barre."""
    csv = D02.SERIES[key][0]
    meta = json.loads(meta_path(csv).read_text(encoding="utf-8"))
    sha = sha256_file(csv)
    if sha != meta["sha256"]:
        stop(f"{key} : empreinte du CSV différente de son .meta.json")
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        df, _ = load_asset(csv)
    info = {"sha256": sha[:16]}
    if key == "BTC":
        mask = D02_0.outage_mask(df)
        if int(mask.sum()) != 215:
            stop("BTC : panne de janvier 2015 différente de 215 barres")
        df = df[~mask].reset_index(drop=True)
        info["panne_barres_retirees"] = 215
    bars = df[["time", "open", "high", "low", "close"]].copy()
    if bars.time.iat[-1] >= ts("2026-01-01"):
        stop(f"{key} : barre de 2026")
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        atlas, _, _, atr = build_atlas(df, kalman=KalmanParams(R0=100.0))
    tab = signal_table(bars, atlas, atr)
    info.update({"barres": len(bars), "premiere": str(bars.time.iat[0]), "derniere": str(bars.time.iat[-1]),
                 "signaux": len(atlas)})
    return {"key": key, "bars": bars, "tab": tab, "atr_bps": atr / bars.close.to_numpy() * BPS, "info": info}


def re1(p: dict, start: str | None, end: str | None, keep=None) -> dict:
    """RE-1 gelée : candidats aux seuils BTC gelés, noyau à H = 26 (verrou = H) ; `keep` : masque de candidats gardés
    avant la course séquentielle (filtre en séquentiel)."""
    t, s, lv = candidates(p["tab"], LEG_ATR_P50_BTC, NIS_Z100_P75_BTC, 0.85,
                          None if start is None else ts(start), None if end is None else ts(end))
    if keep is not None:
        k = keep[t]
        t, s, lv = t[k], s[k], lv[k]
    tr = run_trades(p["bars"], t, s, 26, lv)
    return {"trades": tr, "cands": (t, s, lv), "fam": pd.Series(np.where(np.isnan(lv), "F2b", "F3"), index=t)}


def controls(btc: dict, sol: dict, s_btc: dict, s_sol: dict) -> dict:
    out = {"donnees": {"BTC": btc["info"], "SOL": sol["info"]}}
    stored = pd.read_csv(ROOT / "experiments" / "D02" / "trades_D02.csv.gz")
    ref = stored[(stored.actif == "BTC") & (stored.variante == "RE-1 gelée")].reset_index(drop=True)
    a = s_btc["trades"]
    same = (len(a) == len(ref) and all(np.array_equal(a[c].to_numpy(dtype=np.int64), ref[c].to_numpy(dtype=np.int64))
                                       for c in ("entry_bar", "exit_bar", "side", "signal_bar"))
            and all(np.array_equal(a[c].to_numpy(dtype=bool), ref[c].to_numpy(dtype=bool)) for c in ("stop", "gap"))
            and np.allclose(a.ret_gross_bps.to_numpy(), ref.ret_gross_bps.to_numpy(), rtol=1e-9, atol=1e-9))
    if not same:
        stop("RE-1 gelée BTC 2015-2025 différente de D02")
    out["RE-1 gelée BTC 2015-2025"] = f"{len(a)} trades identiques à D02"
    p = D01.prepare("SOL")
    ref_sol, _ = run_re1(p["bars"], p["atlas"], p["atr"], p["m"])
    if not s_sol["trades"][TRADE_COLUMNS].equals(ref_sol):
        stop("RE-1 gelée SOL différente de run_re1")
    r01 = pd.read_csv(ROOT / "experiments" / "D01" / "resultats_D01.csv")
    fam = pd.Series(np.where(np.isnan(s_sol["cands"][2]), "F2b", "F3"), index=s_sol["cands"][0])
    for fee in FEES:
        m, _ = metrics(ref_sol, p["bars"], p["atr_bps"], fee, int(p["m"]["R2"].sum()), fam, sample_years(p["bars"]))
        row = r01[(r01.actif == "SOL") & (r01.frais_bps == fee)].iloc[0]
        D02.compare(m, row, label=f"D01 SOL {fee:g} bps")
    out["RE-1 gelée SOL"] = f"{len(ref_sol)} trades identiques à run_re1 ; métriques de D01 à 1e-5 (5 et 10 bps)"
    w = risk_weights(btc["atr_bps"][a.signal_bar.to_numpy()], 25.0)
    eq, info = portfolio_equity([Leg("BTC", btc["bars"], a, w, 5.0)])
    ref_eq = equity_curve_sized(btc["bars"], a, 5.0, w)
    if not (np.isclose(info["pnl"], ref_eq.iloc[-1] - 1.0, rtol=1e-10)
            and np.isclose(drawdown_stats(eq)["max_drawdown"], drawdown_stats(ref_eq)["max_drawdown"], rtol=1e-10)):
        stop("portefeuille d'une jambe différent du capital valorisé du dépôt")
    out["portefeuille une jambe"] = "PnL et MDD identiques au capital valorisé de RE-1 gelée BTC (1e-10)"
    return out


# ── Action 1 : profil des trades à t ────────────────────────────────────────────
def features(p: dict, tr: pd.DataFrame) -> pd.DataFrame:
    bars, tab, atr = p["bars"], p["tab"], p["atr_bps"]
    times, close = bars.time, bars.close.to_numpy(dtype=float)
    sb = tr.signal_bar.to_numpy(dtype=np.int64)
    side = tr.side.to_numpy(dtype=np.int64)
    pctb, bw = bollinger(close, 20, 2.0)
    leg_p50 = trailing_quantile(tab.time, tab.leg_atr, 0.5, WINDOW, SPAN)
    i = np.searchsorted(tab.t, sb)
    if not np.array_equal(tab.t[i], sb):
        stop("profil : signal absent de la table")
    dist = (close - ema(close, 200)) / close * BPS / atr
    ret = tr.ret_gross_bps.to_numpy(dtype=float)
    return pd.DataFrame({
        "signal_bar": sb, "entree": times.iloc[tr.entry_bar.to_numpy()].to_numpy(), "side": side,
        "stop": tr.stop.to_numpy(dtype=bool), "net_bps": ret - FEES[0], "net_atr": (ret - FEES[0]) / atr[sb],
        "atr_bps": atr[sb], "atr_rang": trailing_rank(times, atr, WINDOW, SPAN)[sb],
        "atr_p60": trailing_quantile(times, atr, 0.6, WINDOW, SPAN)[sb],
        "leg_atr": tab.leg_atr[i], "leg_rapport": tab.leg_atr[i] / leg_p50[i],
        "pctb": pctb[sb], "pctb_sens": np.where(side == 1, pctb[sb], 1.0 - pctb[sb]),
        "bw": 100.0 * bw[sb], "bw_rang": trailing_rank(times, bw, WINDOW, SPAN)[sb], "ema_sens": side * dist[sb],
        "heure": pd.DatetimeIndex(times.iloc[tr.entry_bar.to_numpy()]).hour})


def groups(f: pd.DataFrame) -> pd.DataFrame:
    n = len(f)
    k5, k1 = int(np.ceil(0.05 * n - 1e-9)), int(np.ceil(0.01 * n - 1e-9))
    f = f.copy()
    for col, name in (("net_atr", "alpha"), ("net_bps", "alpha_bps")):
        flag = np.zeros(n, bool)
        flag[np.argsort(-f[col].to_numpy(), kind="stable")[:k5]] = True
        f[name] = flag
    top1 = np.zeros(n, bool)
    top1[np.argsort(-f.net_atr.to_numpy(), kind="stable")[:k1]] = True
    f["top1"] = top1
    return f


def profile_rows(f: pd.DataFrame) -> list[dict]:
    rows = []
    for v in VARS:
        x = f[v].to_numpy(dtype=float)
        u = x[~f.alpha]
        row = {"variable": v, "usure_mediane": np.nanmedian(u), "usure_p25": np.nanpercentile(u, 25),
               "usure_p75": np.nanpercentile(u, 75), "usure_moyenne": np.nanmean(u)}
        for g in ("alpha", "alpha_bps", "top1"):
            a = x[f[g]]
            row.update({f"{g}_mediane": np.nanmedian(a), f"{g}_p25": np.nanpercentile(a, 25),
                        f"{g}_p75": np.nanpercentile(a, 75), f"{g}_moyenne": np.nanmean(a),
                        f"{g}_sous_mediane_usure": float(np.mean(a < np.nanmedian(u)))})
        rows.append(row)
    return rows


def quintile_rows(f: pd.DataFrame) -> list[dict]:
    rows = []
    tot_atr, tot_bps = f.net_atr.sum(), f.net_bps.sum()
    for v in ("atr_rang", "atr_bps", "bw_rang", "pctb_sens", "ema_sens", "leg_rapport"):
        q = pd.qcut(f[v], 5, labels=False, duplicates="drop")
        for b in sorted(q.dropna().unique()):
            g = f[q == b]
            rows.append({"variable": v, "quintile": int(b) + 1, "borne_basse": float(g[v].min()),
                         "borne_haute": float(g[v].max()), "trades": len(g), "esperance_atr": g.net_atr.mean(),
                         "esperance_bps": g.net_bps.mean(), "mediane_atr": g.net_atr.median(),
                         "alpha": int(g.alpha.sum()), "top1": int(g.top1.sum()),
                         "part_somme_atr": g.net_atr.sum() / tot_atr, "part_somme_bps": g.net_bps.sum() / tot_bps})
    return rows


def hour_rows(f: pd.DataFrame) -> list[dict]:
    rows = []
    for h0 in range(0, 24, 4):
        g = f[(f.heure >= h0) & (f.heure < h0 + 4)]
        rows.append({"heures_utc": f"{h0:02d}-{h0 + 4:02d}", "trades": len(g), "alpha": int(g.alpha.sum()),
                     "top1": int(g.top1.sum()), "esperance_atr": g.net_atr.mean(), "esperance_bps": g.net_bps.mean()})
    return rows


# ── Mesures ─────────────────────────────────────────────────────────────────────
def subset(s: dict, bars: pd.DataFrame, start: str, end: str) -> dict:
    tr = s["trades"]
    et = bars.time.iloc[tr.entry_bar.to_numpy()].to_numpy()
    sel = (et >= ts(start)) & (et < ts(end))
    t = s["cands"][0]
    ct = bars.time.iloc[np.minimum(t + 1, len(bars) - 1)].to_numpy()
    csel = (ct >= ts(start)) & (ct < ts(end))
    return {"trades": tr[sel].reset_index(drop=True), "cands": tuple(c[csel] for c in s["cands"]), "fam": s["fam"]}


def measure(label: str, name: str, s: dict, p: dict, fee: float, start: str, end: str) -> tuple[dict, pd.DataFrame]:
    ny = (ts(end) - ts(start)) / pd.Timedelta(days=365.25)
    data = SimpleNamespace(bars=p["bars"], atr_bps=p["atr_bps"])
    m, y = D02.measure_d02(label, name, subset(s, p["bars"], start, end), data, fee, round(ny, 2))
    return m, y


def compare_rows(label: str, p: dict, series: dict, ref: str, fee: float, start: str, end: str) -> list[dict]:
    st = {n: series_stats(subset(s, p["bars"], start, end)["trades"], p["bars"], p["atr_bps"], fee, ts(start), ts(end))
          for n, s in series.items()}
    rows = []
    for n in series:
        if n == ref:
            continue
        c = paired_comparison(st[n], st[ref])
        not_worse = bool(c["d_mdd_sorties_hi"] >= 0)
        rows.append({"actif": label, "frais_bps": fee, "famille": f"contre {ref}", "variante": n, "reference": ref, **c,
                     "mdd_non_degrade": not_worse,
                     "surpasse": bool(c["esperance_tangible"] and c["rendement_tangible"] and not_worse)})
    return rows


# ── Action 3 : portefeuille ─────────────────────────────────────────────────────
def leg(name: str, p: dict, s: dict, fee: float, one_x: bool = False) -> Leg:
    tr = subset(s, p["bars"], *P_PORT)["trades"]
    w = np.ones(len(tr)) if one_x else risk_weights(p["atr_bps"][tr.signal_bar.to_numpy()], 25.0)
    return Leg(name, p["bars"], tr[TRADE_COLUMNS], w, fee)


def monthly(eq: pd.Series) -> pd.Series:
    """Rendements mensuels du capital valorisé sur tous les mois de la période (mois sans événement : 0)."""
    months = pd.period_range(P_PORT[0], ts(P_PORT[1]) - pd.Timedelta(days=1), freq="M")
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        last = eq.groupby(eq.index.tz_localize(None).to_period("M")).last()
    level = pd.concat([pd.Series([1.0], index=[months[0] - 1]), last.reindex(months)]).ffill()
    return level.pct_change().iloc[1:]


def portfolio_rows(btc: dict, sol: dict, s_btc: dict, s_sol: dict) -> tuple[list[dict], dict, dict]:
    rows, curves, months = [], {}, {}
    ny = (ts(P_PORT[1]) - ts(P_PORT[0])) / pd.Timedelta(days=365.25)
    for fee in FEES:
        for one_x in (False, True):
            legs = {"BTC": leg("BTC", btc, s_btc, fee, one_x), "SOL": leg("SOL", sol, s_sol, fee, one_x)}
            for name, ls in (("BTC seul", [legs["BTC"]]), ("SOL seul", [legs["SOL"]]),
                             ("Portefeuille BTC + SOL", [legs["BTC"], legs["SOL"]])):
                eq, info = portfolio_equity(ls)
                dd = drawdown_stats(eq)
                mo = monthly(eq)
                cagr = (1.0 + info["pnl"]) ** (1.0 / ny) - 1.0
                trades = pd.concat([lg.trades for lg in ls])
                net = trades.ret_gross_bps.to_numpy() - fee
                rows.append({"serie": name, "frais_bps": fee, "dimension": "1x par position" if one_x else "0,25 %/ATR",
                             "trades": len(trades), "trades_par_mois": len(trades) / (12 * ny), "pnl": info["pnl"],
                             "mdd": dd["max_drawdown"], "calmar": cagr / abs(dd["max_drawdown"]),
                             "plus_longue_sous_le_pic_jours": dd["plus_longue_periode_sous_le_pic_jours"],
                             "mois_positifs": float((mo > 0).mean()), "mois": len(mo),
                             "exposition_max": info["exposition_max"],
                             "part_temps_en_position": info["part_temps_en_position"],
                             "part_temps_deux_positions": info["part_temps_deux_positions"],
                             "pf_1x": net[net > 0].sum() / -net[net < 0].sum(), "wr": float((net > 0).mean()),
                             "esperance_bps": net.mean()})
                if fee == FEES[0] and not one_x:
                    curves[name], months[name] = eq, mo
    corr = float(pd.concat([months["BTC seul"], months["SOL seul"]], axis=1).fillna(0.0).corr().iloc[0, 1])
    return rows, curves, {"correlation_mensuelle_btc_sol": corr}


# ── Calcul ──────────────────────────────────────────────────────────────────────
def run_calcul() -> None:
    t0 = time.time()
    commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, capture_output=True,
                            text=True).stdout.strip()
    btc, sol = prepare("BTC"), prepare("SOL")
    s_btc, s_sol = re1(btc, *P_BTC), re1(sol, None, None)
    ctrl = {"date": pd.Timestamp.now(tz="UTC").strftime("%Y-%m-%d %H:%M UTC"), "commit": commit}
    ctrl.update(controls(btc, sol, s_btc, s_sol))
    print(f"contrôles bloquants passés ({time.time() - t0:.0f} s)", flush=True)

    # Action 1
    f = groups(features(btc, s_btc["trades"]))
    prof, quint, hours = profile_rows(f), quintile_rows(f), hour_rows(f)
    diag = {"alpha": int(f.alpha.sum()), "top1": int(f.top1.sum()),
            "alpha_communs_atr_bps": int((f.alpha & f.alpha_bps).sum()),
            "part_somme_atr_alpha": float(f.net_atr[f.alpha].sum() / f.net_atr.sum()),
            "part_somme_bps_alpha": float(f.net_bps[f.alpha].sum() / f.net_bps.sum()),
            "part_somme_bps_alpha_bps": float(f.net_bps[f.alpha_bps].sum() / f.net_bps.sum())}

    # Action 2 : filtre ATR ≤ P60 glissant
    filt = {}
    for key, p, s, period in (("BTC", btc, s_btc, P_BTC), ("SOL", sol, s_sol, P_SOL_FILTRE)):
        atr = p["atr_bps"]
        p60 = trailing_quantile(p["bars"].time, atr, 0.6, WINDOW, SPAN)
        with np.errstate(invalid="ignore"):
            ok = atr <= p60
        tr = s["trades"]
        frozen = {"trades": tr[ok[tr.signal_bar.to_numpy()]].reset_index(drop=True), "cands": s["cands"],
                  "fam": s["fam"]}
        start = period[0] if key == "SOL" else P_BTC[0]
        seq = re1(p, start, period[1], keep=ok)
        filt[key] = {RE1: s, FIGEES: frozen, SEQ: seq}
        if key == "BTC":
            kept = ok[f.signal_bar.to_numpy()]
            new = ~seq["trades"].set_index(KEY).index.isin(tr.set_index(KEY).index)
            na = (seq["trades"].ret_gross_bps.to_numpy() - 5.0) / atr[seq["trades"].signal_bar.to_numpy()]
            diag.update({"filtre_part_gardee": float(kept.mean()), "alpha_gardes": int((f.alpha & kept).sum()),
                         "top1_gardes": int((f.top1 & kept).sum()),
                         "usure_retiree": int((~f.alpha & ~kept).sum()), "alpha_retires": int((f.alpha & ~kept).sum()),
                         "esperance_atr_usure_retiree": float(f.net_atr[~f.alpha & ~kept].mean()),
                         "esperance_atr_retires": float(f.net_atr[~kept].mean()),
                         "esperance_atr_gardes": float(f.net_atr[kept].mean()),
                         "sequentiel_trades_nouveaux": int(new.sum()),
                         "sequentiel_esperance_atr_nouveaux": float(na[new].mean()) if new.any() else np.nan})
            f["filtre_ok"] = kept
    rows, years, comps = [], [], []
    for per, (a, b) in PERIODS.items():
        for fee in FEES:
            label = f"BTC {per} · {fee:g} bps"
            for name, s in filt["BTC"].items():
                m, y = measure(label, name, s, btc, fee, a, b)
                rows.append(m)
                if per == "2015-2025" and fee == FEES[0]:
                    years.append(y)
            comps += compare_rows(label, btc, filt["BTC"], RE1, fee, a, b)
    for fee in FEES:
        label = f"SOL 2023-S2 → 2025 · {fee:g} bps"
        for name, s in filt["SOL"].items():
            rows.append(measure(label, name, s, sol, fee, *P_SOL_FILTRE)[0])
        comps += compare_rows(label, sol, filt["SOL"], RE1, fee, *P_SOL_FILTRE)
        label = f"SOL 2021-S2 → 2025 · {fee:g} bps"
        rows.append(measure(label, RE1, s_sol, sol, fee, *P_PORT)[0])
        label = f"BTC 2021-S2 → 2025 · {fee:g} bps"
        rows.append(measure(label, RE1, s_btc, btc, fee, *P_PORT)[0])
    print(f"actions 1 et 2 faites ({time.time() - t0:.0f} s)", flush=True)

    # Action 3
    port, curves, pdiag = portfolio_rows(btc, sol, s_btc, s_sol)
    diag.update(pdiag)

    res = pd.DataFrame(rows)
    lead = ["actif", "variante", "frais_bps", "annees", "debut", "fin"]
    res = res[lead + [c for c in res.columns if c not in lead]]
    res.to_csv(HERE / "resultats_D03.csv", index=False, float_format="%.6g")
    pd.concat(years, ignore_index=True).to_csv(HERE / "annuel_D03.csv", index=False, float_format="%.6g")
    pd.DataFrame(comps).to_csv(HERE / "comparaisons_D03.csv", index=False, float_format="%.6g")
    pd.DataFrame(port).to_csv(HERE / "portefeuille_D03.csv", index=False, float_format="%.6g")
    f.to_csv(HERE / "profil_D03.csv", index=False, float_format="%.6g")                    # aucun prix publié
    diags = {"profil": prof, "quintiles": quint, "heures": hours, "chiffres": diag}
    (HERE / "diagnostics_D03.json").write_text(json.dumps(D01.jsonable(diags), ensure_ascii=False, indent=1),
                                               encoding="utf-8")
    ctrl["duree_s"] = round(time.time() - t0)
    ctrl["comparaisons"] = len(comps)
    (HERE / "controles_D03.json").write_text(json.dumps(D01.jsonable(ctrl), ensure_ascii=False, indent=1),
                                             encoding="utf-8")
    figures(f, curves)
    write_rapport()
    print(f"D03 : {len(res)} lignes de résultats, {len(comps)} comparaisons en {ctrl['duree_s']} s ; sorties dans {HERE}")


def figures(f: pd.DataFrame, curves: dict) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    FIG.mkdir(parents=True, exist_ok=True)
    panels = ["atr_bps", "atr_rang", "bw_rang", "pctb_sens", "ema_sens", "leg_rapport"]
    fig, axes = plt.subplots(2, 4, figsize=(17, 8))
    for ax, v in zip(axes.ravel(), panels):
        data = [f.loc[~f.alpha, v].dropna(), f.loc[f.alpha, v].dropna(), f.loc[f.alpha_bps, v].dropna()]
        ax.boxplot(data, showfliers=False)
        ax.set_xticks([1, 2, 3], ["Usure", "Alpha (ATR)", "Alpha (bps)"], fontsize=8)
        ax.set_title(VARS[v], fontsize=9)
        ax.grid(alpha=0.3)
    ax = axes.ravel()[6]
    h = np.arange(24)
    ax.bar(h - 0.2, f[~f.alpha].heure.value_counts(normalize=True).reindex(h, fill_value=0), 0.4, label="Usure")
    ax.bar(h + 0.2, f[f.alpha].heure.value_counts(normalize=True).reindex(h, fill_value=0), 0.4, label="Alpha (ATR)")
    ax.set_title("Heure UTC de l'entrée (part du groupe)", fontsize=9)
    ax.legend(fontsize=7)
    ax = axes.ravel()[7]
    ax.scatter(f.atr_bps[~f.alpha], f.net_bps[~f.alpha], s=4, alpha=0.3, label="Usure")
    ax.scatter(f.atr_bps[f.alpha], f.net_bps[f.alpha], s=10, alpha=0.8, label="Alpha (ATR)")
    ax.set_xscale("log")
    ax.set_xlabel("ATR14 (bps)")
    ax.set_ylabel("Rendement net (bps)")
    ax.set_title("Rendement net selon l'ATR au signal", fontsize=9)
    ax.legend(fontsize=7)
    fig.suptitle("BTC 2015-2025, RE-1 gelée : profil à t des 5 % meilleurs trades (Alpha) contre les autres (Usure)",
                 fontsize=10)
    fig.tight_layout()
    fig.savefig(FIG / "D03_profil.png", dpi=110)
    plt.close(fig)
    fig, ax = plt.subplots(figsize=(13, 6))
    style = {"BTC seul": ("#f2a900", 1.3), "SOL seul": ("#9945ff", 1.3), "Portefeuille BTC + SOL": ("k", 2.0)}
    for name, eq in curves.items():
        c, lw = style[name]
        ax.step(eq.index, 100 * (eq.to_numpy() - 1.0), where="post", color=c, lw=lw, label=name)
    ax.axhline(0, color="k", lw=0.5)
    ax.set_title("RE-1 gelée, 2021-07 → 2025 : capital valorisé (0,25 %/ATR par trade, 5 bps)", fontsize=10)
    ax.set_ylabel("PnL composé (%)")
    ax.grid(alpha=0.3)
    ax.legend(fontsize=9)
    fig.tight_layout()
    fig.savefig(FIG / "D03_portefeuille.png", dpi=110)
    plt.close(fig)


# ── Rapport (annexes générées ; narratif_D03.md écrit à la main) ────────────────
fr, sg, pct, spct, n_fr, ci, table = D01.fr, D01.sg, D01.pct, D01.spct, D01.n_fr, D01.ci, D01.table
NDEC = {"atr_bps": 1, "atr_rang": 2, "leg_atr": 2, "leg_rapport": 2, "pctb": 2, "pctb_sens": 2, "bw": 2, "bw_rang": 2,
        "ema_sens": 2}


def write_rapport() -> None:
    res = pd.read_csv(HERE / "resultats_D03.csv")
    cp = pd.read_csv(HERE / "comparaisons_D03.csv")
    pt = pd.read_csv(HERE / "portefeuille_D03.csv")
    yr = pd.read_csv(HERE / "annuel_D03.csv")
    dg = json.loads((HERE / "diagnostics_D03.json").read_text(encoding="utf-8"))
    ct = json.loads((HERE / "controles_D03.json").read_text(encoding="utf-8"))
    c = dg["chiffres"]
    narr = HERE / "narratif_D03.md"
    out = [narr.read_text(encoding="utf-8") if narr.exists() else "# EXP-D03 — rapport (narratif à rédiger)\n",
           "", "---", "", "# Annexes générées (`run_D03.py --calcul`, puis `--rapport`)", "",
           f"Calcul du {ct['date']}, commit `{ct['commit']}`, {ct['duree_s']} s ; {ct['comparaisons']} comparaisons "
           "appariées publiées.", "", "## A1. Contrôles bloquants (passés)", ""]
    out += [f"- {k} : " + re.sub(r"\b(\d)(\d{3})\b", r"\1 \2", str(v)) + "." for k, v in ct.items()
            if k not in ("date", "commit", "duree_s", "comparaisons", "donnees")]
    out += ["", "## A2. Profil à t : Alpha (5 % meilleurs) contre Usure (95 %), BTC 2015-2025, 5 bps", "",
            f"Alpha : {c['alpha']} trades ({pct(c['part_somme_atr_alpha'], 0)} de la somme nette en ATR, "
            f"{pct(c['part_somme_bps_alpha'], 0)} de la somme en bps) ; Alpha classé en bps : "
            f"{pct(c['part_somme_bps_alpha_bps'], 0)} de la somme en bps ; {c['alpha_communs_atr_bps']} trades communs "
            "aux deux classements.", "",
            table(["Variable", "Usure : médiane [P25 ; P75]", "Alpha (ATR) : médiane [P25 ; P75] ; sous la médiane d'Usure",
                   "Alpha (bps) : médiane [P25 ; P75] ; sous la médiane d'Usure", "Top 1 % : médiane"],
                  [[VARS[r["variable"]],
                    f"{fr(r['usure_mediane'], NDEC[r['variable']])} [{fr(r['usure_p25'], NDEC[r['variable']])} ; "
                    f"{fr(r['usure_p75'], NDEC[r['variable']])}]",
                    f"{fr(r['alpha_mediane'], NDEC[r['variable']])} [{fr(r['alpha_p25'], NDEC[r['variable']])} ; "
                    f"{fr(r['alpha_p75'], NDEC[r['variable']])}] ; {pct(r['alpha_sous_mediane_usure'], 0)}",
                    f"{fr(r['alpha_bps_mediane'], NDEC[r['variable']])} [{fr(r['alpha_bps_p25'], NDEC[r['variable']])} ; "
                    f"{fr(r['alpha_bps_p75'], NDEC[r['variable']])}] ; {pct(r['alpha_bps_sous_mediane_usure'], 0)}",
                    fr(r["top1_mediane"], NDEC[r["variable"]])] for r in dg["profil"]]), "",
            "**Espérance par quintile de la variable (2 075 trades, 5 bps)**", ""]
    q = pd.DataFrame(dg["quintiles"])
    for v, g in q.groupby("variable", sort=False):
        out += [f"*{VARS[v]}*", "",
                table(["Quintile (bornes)", "Trades", "Espérance ATR ; bps", "Médiane ATR", "Alpha ; top 1 %",
                       "Part de la somme ATR ; bps"],
                      [[f"Q{int(r.quintile)} ({fr(r.borne_basse, NDEC[v])} à {fr(r.borne_haute, NDEC[v])})",
                        n_fr(r.trades), f"{sg(r.esperance_atr, 3)} ; {sg(r.esperance_bps, 1)}", sg(r.mediane_atr, 2),
                        f"{int(r.alpha)} ; {int(r.top1)}", f"{pct(r.part_somme_atr, 0)} ; {pct(r.part_somme_bps, 0)}"]
                       for r in g.itertuples()]), ""]
    out += ["*Heure UTC de l'entrée*", "",
            table(["Heures UTC", "Trades", "Alpha ; top 1 %", "Espérance ATR ; bps"],
                  [[h["heures_utc"], n_fr(h["trades"]), f"{h['alpha']} ; {h['top1']}",
                    f"{sg(h['esperance_atr'], 3)} ; {sg(h['esperance_bps'], 1)}"] for h in dg["heures"]]), ""]
    names = [RE1, FIGEES, SEQ]
    out += ["## A3. Filtre ATR14 ≤ P60 glissant sur 24 mois (BTC)", "",
            f"Trades de RE-1 gardés : {pct(c['filtre_part_gardee'], 0)} ; Alpha gardés : {c['alpha_gardes']} sur "
            f"{c['alpha']} ; top 1 % gardés : {c['top1_gardes']} sur {c['top1']} ; retirés : {n_fr(c['usure_retiree'])} "
            f"trades d'Usure ({sg(c['esperance_atr_usure_retiree'], 3)} ATR en moyenne) et {c['alpha_retires']} Alpha. "
            f"Espérance de tous les trades retirés {sg(c['esperance_atr_retires'], 3)} ATR, des gardés "
            f"{sg(c['esperance_atr_gardes'], 3)}. En séquentiel : {c['sequentiel_trades_nouveaux']} trades "
            f"nouveaux (signaux libérés du verrou), {sg(c['sequentiel_esperance_atr_nouveaux'], 3)} ATR en moyenne.", ""]
    for per in PERIODS:
        for fee in FEES:
            label = f"BTC {per} · {fee:g} bps"
            r = res[res.actif == label].copy()
            r["variante"] = pd.Categorical(r.variante, names, ordered=True)
            out += [f"**{label}**", "", D02.annex_metrics(r.sort_values("variante"), label, fee), "",
                    D02.annex_comparisons(cp, label, fee, f"contre {RE1}"), ""]
    out += ["**Hors de l'échantillon de l'idée : SOL, entrées du 2023-07-01 au 2025-12-31**", ""]
    for fee in FEES:
        label = f"SOL 2023-S2 → 2025 · {fee:g} bps"
        r = res[res.actif == label].copy()
        r["variante"] = pd.Categorical(r.variante, names, ordered=True)
        out += [D02.annex_metrics(r.sort_values("variante"), label, fee), "",
                D02.annex_comparisons(cp, label, fee, f"contre {RE1}"), ""]
    piv = yr.pivot_table(index="annee", columns="variante", values="esperance_atr", sort=False)
    out += ["**Espérance par année (ATR, 5 bps)**", "",
            table(["Année"] + names, [[str(int(y))] + [sg(piv.loc[y, n], 3) for n in names] for y in piv.index]), ""]
    out += ["## A4. Portefeuille RE-1 gelée BTC + SOL, entrées du 2021-07-01 au 2025-12-31", "",
            f"Corrélation des rendements mensuels BTC / SOL (0,25 %/ATR, 5 bps) : {fr(c['correlation_mensuelle_btc_sol'], 2)}.",
            ""]
    for fee in FEES:
        for dim in ("0,25 %/ATR", "1x par position"):
            g = pt[(pt.frais_bps == fee) & (pt.dimension == dim)]
            out += [f"**{fee:g} bps, {dim}**", "",
                    table(["Série", "PnL", "MDD", "Calmar", "Plus longue période sous le pic", "Mois positifs",
                           "Trades (/mois)", "PF (1x) ; WR ; espérance bps", "Exposition brute max ; temps à 2 positions"],
                          [[x.serie, spct(x.pnl), pct(x.mdd), fr(x.calmar, 2), f"{fr(x.plus_longue_sous_le_pic_jours, 0)} j",
                            f"{pct(x.mois_positifs, 0)} de {int(x.mois)}", f"{n_fr(x.trades)} ({fr(x.trades_par_mois, 1)})",
                            f"{fr(x.pf_1x, 2)} ; {pct(x.wr, 1)} ; {sg(x.esperance_bps, 1)}",
                            f"{fr(x.exposition_max, 2)} ; {pct(x.part_temps_deux_positions, 0)}"] for x in g.itertuples()]),
                    ""]
    for key in ("BTC", "SOL"):
        for fee in FEES:
            label = f"{key} 2021-S2 → 2025 · {fee:g} bps"
            out += [f"**{label}, 8 métriques**", "", D02.annex_metrics(res, label, fee), ""]
    out += ["## A5. Figures", "", "![Profil à t](figures/D03_profil.png)", "",
            "![Portefeuille](figures/D03_portefeuille.png)", ""]
    (HERE / "rapport_D03.md").write_text("\n".join(out) + "\n", encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--calcul", action="store_true", help="contrôles, actions 1 à 3, rapport")
    ap.add_argument("--rapport", action="store_true", help="régénère rapport_D03.md depuis les sorties, sans calcul")
    args = ap.parse_args()
    if args.rapport:
        write_rapport()
        return
    if not args.calcul:
        raise SystemExit("EXP-D03 : préciser --calcul ou --rapport")
    run_calcul()


if __name__ == "__main__":
    main()
