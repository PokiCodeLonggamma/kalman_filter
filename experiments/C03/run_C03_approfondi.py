"""EXP-C03 — analyse approfondie (relecture du porteur, 2026-09-29) : alpha contre gestion du risque.

Usage, depuis la racine du dépôt : python experiments/C03/run_C03_approfondi.py [--rapport]
  --rapport : régénère seulement rapport_C03_approfondi.md depuis approfondi_C03.json et diagnostic_2022_C03.csv.
Entrées : resultats_C03.csv (grille de C03, inchangée). Sorties dans experiments/C03/ : approfondi_C03.json,
diagnostic_2022_C03.csv, figures/fig5 à fig8, rapport_C03_approfondi.md (= narratif_C03_approfondi.md rédigé à la
main, suivi des annexes chiffrées générées ici, lettrées comme le narratif, de A à H).

Aucune règle nouvelle : RE-1 (H = 26, cooldown, F2b sans stop, F3 SL-B à l'extremum) reste le contrôle. Les variantes
sont celles de C03, sur les mêmes 1 080 entrées. Seul ajout d'exécution : le glissement du seul break-even
(`breakeven_trades(..., be_slippage_bps)`, 0, 5 ou 10 bps) sur V3 à m = 2.
- effet apparié BE − RE-1 (mécanisme) séparé de la performance absolue de la variante (viabilité) ;
- IC 95 % par grappes mensuelles d'entrée, 2 000 tirages (mêmes tirages que les IC de C03) ;
- risque de chemin : MDD aux sorties et Calmar sur 2 000 chemins où les mois d'entrée sont tirés avec remise (I-M10),
  MDD valorisé et Calmar observés sur le chemin réel ;
- 5 et 10 bps présentés séparément ; capital à 0,25 % par ATR14(t).
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

from anatomy import build_atlas, load_dev_bars  # noqa: E402
from envelope import breakeven_trades, breakeven_trigger_levels, effect_ci, equity_curve_sized, risk_weights  # noqa: E402
from envelope.metrics import _boot_mean, _cluster_counts, _entry_month  # noqa: E402
from estimand import load_bars_dev  # noqa: E402
from estimand.stoploss import TRADE_COLUMNS, drawdown_stats  # noqa: E402


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


C3 = _load("run_C03", HERE / "run_C03.py")
C2B = C3.C2B
fr, sg, pct, spct, n_fr, ci, table = C3.fr, C3.sg, C3.pct, C3.spct, C3.n_fr, C3.ci, C3.table

FIG = HERE / "figures"
FEES = (5.0, 10.0)
YEARS = list(range(2020, 2026))
N_BOOT = C3.N_BOOT
N_YEARS = 6.0
H_MAIN, HORIZONS, M_GRID, PERIMETRES = C3.H_MAIN, C3.HORIZONS, C3.M_GRID, C3.PERIMETRES
SLIPS = (0.0, 5.0, 10.0)
FOCUS = ("V3", 2.0)
TRIO = [("V1", 2.0), ("V2", 2.0), ("V3", 2.0)]


def key(p: str, m: float) -> str:
    return f"{p} m{m:g}"


# ── Calculs ─────────────────────────────────────────────────────────────────────
def run_be(eng, H: int, p: str | None = None, m: float = np.nan, slip: float = 0.0) -> pd.DataFrame:
    """Course de C03 (lecture cooldown) avec glissement éventuel du seul break-even."""
    trig = None
    if p is not None:
        mm = np.where(np.isin(eng.fam, PERIMETRES[p]), m, np.nan)
        trig = breakeven_trigger_levels(eng.bars, eng.t, eng.s, eng.a, mm)
    return breakeven_trades(eng.bars, eng.t, eng.s, H, eng.level, trig, C3.BE_BPS, False, be_slippage_bps=slip)


def diff_atr(tr, ctrl, atr_bps) -> np.ndarray:
    """Effet apparié par trade, en ATR14(t) : les frais s'annulent."""
    atr = atr_bps.reindex(tr.signal_bar.to_numpy()).to_numpy(dtype=float)
    return (tr.ret_gross_bps.to_numpy(dtype=float) - ctrl.ret_gross_bps.to_numpy(dtype=float)) / atr


def boot(tr, bars, v, keep=None) -> np.ndarray:
    """Moyennes bootstrap de `v` (tirages de `mean_ci` et `effect_ci` : grappes mensuelles, graine 0)."""
    w, inv, g = _cluster_counts(_entry_month(tr, bars), N_BOOT, 0)
    return _boot_mean(w, inv, g, np.asarray(v, dtype=float), keep)


def q(b, p) -> float:
    return float(np.nanpercentile(b, p))


def path_draws(tr, ctrl, orders, atr_bps, fee: float) -> dict:
    """MDD aux sorties et Calmar (PnL annualisé sur 6 ans / |MDD|) de RE-1 et de la variante sur les mêmes chemins."""
    out = {}
    for k, t in (("re1", ctrl), ("be", tr)):
        r = C3.sized_returns(t, atr_bps, fee)
        mdd = np.array([C3.mdd_exits(r[o]) for o in orders])
        cagr = np.expm1(np.array([np.log1p(r[o]).sum() for o in orders]) / N_YEARS)
        out[k] = {"mdd": mdd, "calmar": cagr / np.abs(mdd)}
        full = np.log1p(r).sum()
        out[k]["obs_mdd"] = C3.mdd_exits(r)
        out[k]["obs_calmar"] = float(np.expm1(full / N_YEARS) / abs(out[k]["obs_mdd"]))
    return out


def path_summary(pd_: dict) -> dict:
    dm = pd_["be"]["mdd"] - pd_["re1"]["mdd"]
    dc = pd_["be"]["calmar"] - pd_["re1"]["calmar"]
    s = {"mdd_re1_obs": pd_["re1"]["obs_mdd"], "mdd_be_obs": pd_["be"]["obs_mdd"],
         "calmar_re1_obs": pd_["re1"]["obs_calmar"], "calmar_be_obs": pd_["be"]["obs_calmar"],
         "p_mdd": float((dm > 0).mean()), "p_calmar": float((dc > 0).mean())}
    for p in (2.5, 25, 50, 75, 97.5):
        s[f"dmdd_p{p:g}"], s[f"dcalmar_p{p:g}"] = q(dm, p), q(dc, p)
    for k in ("re1", "be"):
        for p in (5, 50, 95):
            s[f"mdd_{k}_p{p}"] = q(pd_[k]["mdd"], p)
    return s


def tail(tr, ctrl, atr_bps) -> dict:
    """Part des gros gagnants de RE-1 (≥ +3 ATR ; décile supérieur) coupés par le break-even et contribution perdue."""
    base, d = C3.net_atr(ctrl, atr_bps, 5.0), diff_atr(tr, ctrl, atr_bps)
    cut = tr.be_stop.to_numpy(dtype=bool) & (d < 0)
    out = {}
    for name, sel in (("sup3", base >= 3.0), ("top10", base >= np.quantile(base, 0.9))):
        out[f"n_{name}"] = int(sel.sum())
        out[f"n_{name}_coupes"] = int((sel & cut).sum())
        out[f"part_{name}_coupes"] = float((sel & cut).sum() / sel.sum())
        out[f"part_{name}_contribution_perdue"] = float(-d[sel & cut].sum() / base[sel].sum())
        out[f"cout_{name}_par_trade"] = float(d[sel & cut].sum() / len(d))
    return out


def counts(tr, ctrl, atr_bps) -> dict:
    d = diff_atr(tr, ctrl, atr_bps)
    be = tr.be_stop.to_numpy(dtype=bool)
    return {"n_trades": len(tr), "n_actifs": int((tr.be_bar >= 0).sum()), "n_be": int(be.sum()),
            "n_be_gap": int((be & tr.gap.to_numpy(dtype=bool)).sum()), "n_sauves": int((be & (d > 0)).sum()),
            "n_coupes": int((be & (d < 0)).sum())}


def absolute(tr, bars, atr_bps, fee, eng) -> dict:
    """Performance absolue d'une configuration : espérance, IC, probabilité bootstrap d'une espérance > 0, dispersion
    par trade et erreur type de la moyenne, en ATR ; PnL, MDD valorisé et Calmar à 0,25 % par ATR."""
    m, _ = C3.be_metrics(tr, bars, atr_bps, fee, eng)
    v = C3.net_atr(tr, atr_bps, fee)
    b = boot(tr, bars, v)
    return {"esp_atr": float(v.mean()), "esp_atr_lo": m["esperance_atr_lo"], "esp_atr_hi": m["esperance_atr_hi"],
            "esp_bps": m["esperance_bps"], "esp_bps_lo": m["esperance_bps_lo"], "esp_bps_hi": m["esperance_bps_hi"],
            "p_esp_pos": float((b > 0).mean()), "sd_trade_atr": float(v.std(ddof=1)), "se_boot_atr": float(np.nanstd(b)),
            "pnl_r25": m["pnl_compose_r25"], "mdd_r25": m["mdd_valorise_r25"], "calmar_r25": m["calmar_r25"],
            "annees_pnl_pos": m["annees_pnl_r25_pos"], "pnl_1x": m["pnl_compose"], "pnl_bps": m["pnl_bps"], "pf": m["pf"],
            "wr": m["wr"], "n_trades": m["n_trades"], "trades_par_mois": m["trades_par_mois"],
            "duree_mediane": m["duree_mediane"], "part_frais": m["part_frais"], "part_stop_initial": m["part_stop_initial"],
            "part_be_stop": m["part_be_stop"]}


def paired(tr, ctrl, bars, atr_bps, eng) -> dict:
    """Effet apparié global et par sous-famille (par trade de la sous-famille), avec IC."""
    d = diff_atr(tr, ctrl, atr_bps)
    out = {k: v for k, v in effect_ci(tr, ctrl, bars, atr_bps, N_BOOT).items()}
    fam = eng.fam_s.reindex(tr.signal_bar.to_numpy()).to_numpy()
    for k in ("F2b", "F3"):
        sel = fam == k
        b = boot(tr, bars, d, sel)
        out.update({f"effet_{k}": float(d[sel].mean()), f"effet_{k}_lo": q(b, 2.5), f"effet_{k}_hi": q(b, 97.5)})
        be = tr.be_stop.to_numpy(dtype=bool) & sel
        base = C3.net_atr(ctrl, atr_bps, 5.0)
        sv, ct = be & (d > 0), be & (d < 0)
        out.update({f"n_actifs_{k}": int(((tr.be_bar >= 0).to_numpy() & sel).sum()), f"n_be_{k}": int(be.sum()),
                    f"n_sauves_{k}": int(sv.sum()), f"re1_sauves_{k}": float(base[sv].mean()) if sv.any() else np.nan,
                    f"gain_sauves_{k}": float(d[sv].mean()) if sv.any() else np.nan,
                    f"n_coupes_{k}": int(ct.sum()), f"re1_coupes_{k}": float(base[ct].mean()) if ct.any() else np.nan,
                    f"cout_coupes_{k}": float(d[ct].mean()) if ct.any() else np.nan,
                    f"n_sup3_{k}": int((sel & (base >= 3)).sum()), f"n_sup3_coupes_{k}": int((ct & (base >= 3)).sum())})
    return out


def episodes(eq: pd.Series, k: int = 3) -> list[dict]:
    """Les k épisodes de drawdown les plus profonds du capital valorisé : pic, creux, retour au pic (ou fin)."""
    v, t = eq.to_numpy(dtype=float), pd.DatetimeIndex(eq.index)
    peak = np.maximum.accumulate(v)
    dd = v / peak - 1.0
    out, i, n = [], 0, len(v)
    while i < n:
        if dd[i] < 0:
            j = i
            while j < n and dd[j] < 0:
                j += 1
            seg = np.arange(i, j)
            trough = seg[np.argmin(dd[seg])]
            out.append({"profondeur": float(dd[trough]), "pic": str(t[i - 1] if i > 0 else t[0])[:10],
                        "creux": str(t[trough])[:10], "retour": str(t[j])[:10] if j < n else "non regagné"})
            i = j
        else:
            i += 1
    return sorted(out, key=lambda e: e["profondeur"])[:k]


def sized_path(tr, bars, atr_bps, fee: float, risk_bps: float) -> dict:
    """PnL, PnL annualisé, MDD valorisé, durée sous le pic et Calmar d'une course à `risk_bps` du capital par ATR."""
    atr = atr_bps.reindex(tr.signal_bar.to_numpy()).to_numpy(dtype=float)
    w = risk_weights(atr, risk_bps)
    st = drawdown_stats(equity_curve_sized(bars, tr, fee, w))
    pnl = float(np.prod(1.0 + w * (tr.ret_gross_bps.to_numpy(dtype=float) - fee) / 1e4) - 1.0)
    cagr = (1.0 + pnl) ** (1.0 / N_YEARS) - 1.0
    return {"risque_bps": risk_bps, "pnl": pnl, "cagr": cagr, "mdd": st["max_drawdown"],
            "sous_pic_jours": st["plus_longue_periode_sous_le_pic_jours"], "calmar": cagr / abs(st["max_drawdown"])}


def size_matched(ctrl, bars, atr_bps, fee: float, target_mdd: float) -> dict:
    """RE-1 au risque par ATR qui donne le MDD valorisé `target_mdd` (quelques itérations sur la quasi-proportionnalité
    du MDD au risque) : le même drawdown obtenu en réduisant seulement la taille, sans break-even."""
    risk = C2B.RISK
    for _ in range(6):
        s = sized_path(ctrl, bars, atr_bps, fee, risk)
        if abs(s["mdd"] - target_mdd) < 1e-5:
            break
        risk *= target_mdd / s["mdd"]
    return sized_path(ctrl, bars, atr_bps, fee, risk)


def concentration(tr, ctrl, bars, atr_bps, k: int = 2) -> list[dict]:
    """Par année : effet apparié, puis effet sans les k sorties au BE les plus coûteuses ; plus grand coût unitaire."""
    d = diff_atr(tr, ctrl, atr_bps)
    years = bars.time.iloc[tr.entry_bar.to_numpy()].dt.year.to_numpy()
    base = C3.net_atr(ctrl, atr_bps, 5.0)
    rows = []
    for y in YEARS:
        idx = np.flatnonzero(years == y)
        worst = idx[np.argsort(d[idx])[:k]]
        rest = np.setdiff1d(idx, worst)
        rows.append({"annee": y, "effet": float(d[idx].mean()), "effet_sans_pires": float(d[rest].mean()),
                     "pires_couts": [float(v) for v in d[worst]], "pires_re1": [float(v) for v in base[worst]],
                     "gain_max": float(d[idx].max())})
    return rows


def costliest(tr, ctrl, bars, atr_bps, eng, n: int = 10, best: bool = False) -> list[dict]:
    """Les n sorties au BE les plus coûteuses (ou, `best`, les plus favorables) par rapport à RE-1."""
    d = diff_atr(tr, ctrl, atr_bps)
    base = C3.net_atr(ctrl, atr_bps, 5.0)
    out = []
    for i in (np.argsort(d)[::-1] if best else np.argsort(d))[:n]:
        r = tr.iloc[i]
        out.append({"entree": str(bars.time.iloc[int(r.entry_bar)])[:16], "sous_famille": eng.fam_s[int(r.signal_bar)],
                    "sens": "Long" if int(r.side) == 1 else "Short", "res_re1": float(base[i]), "effet": float(d[i])})
    return out


def per_year(tr, ctrl, bars, atr_bps) -> list[dict]:
    d = diff_atr(tr, ctrl, atr_bps)
    years = bars.time.iloc[tr.entry_bar.to_numpy()].dt.year.to_numpy()
    be = tr.be_stop.to_numpy(dtype=bool)
    base = C3.net_atr(ctrl, atr_bps, 5.0)
    rows = []
    for y in YEARS:
        sel = years == y
        sub = tr[sel].reset_index(drop=True)
        b = boot(sub, bars, d[sel])
        rows.append({"annee": y, "n_trades": int(sel.sum()), "n_be": int((be & sel).sum()),
                     "n_sauves": int((be & sel & (d > 0)).sum()), "n_coupes": int((be & sel & (d < 0)).sum()),
                     "effet": float(d[sel].mean()), "effet_lo": q(b, 2.5), "effet_hi": q(b, 97.5),
                     "re1_esp": float(base[sel].mean()), "re1_long": int((sel & (tr.side.to_numpy() == 1)).sum()),
                     "re1_short": int((sel & (tr.side.to_numpy() == -1)).sum())})
    return rows


def diagnostic(tr, ctrl, eng, bars, atr_bps, H: int) -> pd.DataFrame:
    """Une ligne par trade sorti au break-even : excursions, durées, résultats, volatilité réalisée, trajectoire."""
    op, hi, lo, cl = (bars[c].to_numpy(dtype=float) for c in ("open", "high", "low", "close"))
    base, res = C3.net_atr(ctrl, atr_bps, 5.0), C3.net_atr(tr, atr_bps, 5.0)
    rows = []
    for i in np.flatnonzero(tr.be_stop.to_numpy(dtype=bool)):
        r, c = tr.iloc[i], ctrl.iloc[i]
        t, e, s, xb, ba = (int(r.signal_bar), int(r.entry_bar), int(r.side), int(r.exit_bar), int(r.be_bar))
        p0, a = float(r.entry_price), float(eng.atr_s[t])
        x = min(t + 1 + H, len(bars) - 1)
        fin = int(c.exit_bar) if bool(c.stop) else x - 1              # dernière barre détenue par RE-1

        def fav(a0, a1):
            return ((hi[a0:a1 + 1].max() - p0) if s == 1 else (p0 - lo[a0:a1 + 1].min())) / a

        def adv(a0, a1):
            return ((p0 - lo[a0:a1 + 1].min()) if s == 1 else (hi[a0:a1 + 1].max() - p0)) / a

        rv = float(np.diff(np.log(cl[e - 1:x])).std(ddof=1) * 1e4)
        rows.append({"entree": str(bars.time.iloc[e])[:16], "annee": int(bars.time.iloc[e].year),
                     "sous_famille": eng.fam_s[t], "sens": "Long" if s == 1 else "Short",
                     "atr14_bps": float(atr_bps[t]), "vol_realisee_bps": rv, "vol_sur_atr": rv / float(atr_bps[t]),
                     "mae_avant_activation": adv(e, ba), "mfe_avant_be": fav(e, xb - 1),
                     "barres_avant_activation": ba - e + 1, "barres_avant_be": xb - e + 1,
                     "gap": bool(r.gap), "retest_apres_be": adv(xb, fin), "mfe_apres_be": fav(xb, fin),
                     "re1_stoppe": bool(c.stop), "res_re1": float(base[i]), "res_be": float(res[i]),
                     "effet": float(res[i] - base[i]),
                     "trajectoire": "échec, sauvé" if res[i] > base[i] else "reprise après retest, coupé"})
    return pd.DataFrame(rows)


def aggregate(dg: pd.DataFrame) -> dict:
    out = {"n_be": len(dg), "n_sauves": int((dg.effet > 0).sum()), "n_coupes": int((dg.effet < 0).sum()),
           "effet_moyen_par_sortie": float(dg.effet.mean()), "part_long": float((dg.sens == "Long").mean()),
           "part_f2b": float((dg.sous_famille == "F2b").mean()), "part_gap": float(dg.gap.mean())}
    for c in ("atr14_bps", "vol_sur_atr", "mae_avant_activation", "mfe_avant_be", "barres_avant_be", "retest_apres_be",
              "mfe_apres_be"):
        out[f"med_{c}"] = float(dg[c].median())
    for g, sel in (("sauves", dg.effet > 0), ("coupes", dg.effet < 0)):
        out[f"re1_{g}"] = float(dg.res_re1[sel].mean()) if sel.any() else np.nan
        out[f"med_retest_{g}"] = float(dg.retest_apres_be[sel].median()) if sel.any() else np.nan
        out[f"med_mfe_apres_{g}"] = float(dg.mfe_apres_be[sel].median()) if sel.any() else np.nan
    return out


# ── Programme de calcul ─────────────────────────────────────────────────────────
def compute(bars, atlas, atr) -> tuple[dict, pd.DataFrame, dict]:
    atr_bps = pd.Series(atlas.atr14_bps.to_numpy(), index=atlas.bar_index.to_numpy())
    eng = C3.EngineBE(bars, atlas, atr, C2B.full_masks(atlas))
    res = pd.read_csv(HERE / "resultats_C03.csv")
    meta: dict = {"controles": {}}
    ctrl = {H: run_be(eng, H) for H in HORIZONS}
    orders = {H: C3.month_orders(ctrl[H], bars) for H in HORIZONS}
    keep = {}

    # Contrôles bloquants : glissement nul = C03 ; additivité des effets par sous-famille ; mécanique de C03.
    for H in HORIZONS:
        for p, m in TRIO:
            if not run_be(eng, H, p, m)[TRADE_COLUMNS].equals(eng.run(H, False, p, m)[TRADE_COLUMNS]):
                raise SystemExit(f"{key(p, m)} H{H} : glissement nul différent de C03 : arrêt")
        d = {p: diff_atr(run_be(eng, H, p, 2.0), ctrl[H], atr_bps) for p in PERIMETRES}
        if not np.allclose(d["V3"], d["V1"] + d["V2"], rtol=0, atol=1e-12):
            raise SystemExit(f"H{H} : effet de V3 différent de V1 + V2 : arrêt")
    ix = C3.Index(res)
    tr26 = run_be(eng, H_MAIN, *FOCUS)
    c = counts(tr26, ctrl[H_MAIN], atr_bps)
    r = ix(key(*FOCUS))
    if (c["n_actifs"], c["n_be"], c["n_sauves"], c["n_coupes"]) != (r["n_actifs"], r["n_be"], r["n_sauves"], r["n_coupes"]):
        raise SystemExit("mécanique de V3 m = 2 différente de resultats_C03.csv : arrêt")
    meta["controles"] = {"glissement_nul_egal_C03": True, "additivite_V3_egal_V1_plus_V2": True,
                         "mecanique_egale_C03": True}

    # B. Effets appariés, par sous-famille, à H26 (toutes les variantes).
    meta["effets"] = {}
    for p in PERIMETRES:
        for m in M_GRID:
            tr = run_be(eng, H_MAIN, p, m)
            keep[key(p, m)] = tr
            meta["effets"][key(p, m)] = {**paired(tr, ctrl[H_MAIN], bars, atr_bps, eng), **tail(tr, ctrl[H_MAIN], atr_bps),
                                         **counts(tr, ctrl[H_MAIN], atr_bps)}
    print("  effets appariés et queue droite : faits")

    # D. Risque : V1, V2, V3 à m = 2, trois horizons, chemins réordonnés (5 et 10 bps).
    meta["risque"] = {}
    for H in HORIZONS:
        for p, m in TRIO:
            tr = run_be(eng, H, p, m)
            for fee in FEES:
                meta["risque"][f"{key(p, m)} H{H} {fee:g}"] = path_summary(path_draws(tr, ctrl[H], orders[H], atr_bps, fee))
    pdraw = path_draws(tr26, ctrl[H_MAIN], orders[H_MAIN], atr_bps, 5.0)
    meta["episodes"], meta["sous_pic"] = {}, {}
    for name, tr in (("RE-1", ctrl[H_MAIN]), (key("V2", 2.0), keep[key("V2", 2.0)]), (key(*FOCUS), tr26)):
        w = risk_weights(atr_bps.reindex(tr.signal_bar.to_numpy()).to_numpy(dtype=float), C2B.RISK)
        eq = equity_curve_sized(bars, tr, 5.0, w)
        meta["episodes"][name] = episodes(eq)
        meta["sous_pic"][name] = drawdown_stats(eq)["plus_longue_periode_sous_le_pic_jours"]
    print("  risque de chemin : fait")

    # E. Performance absolue à 5 et 10 bps, H26 (toutes les configurations), et IC à 10 bps aux trois horizons.
    meta["absolu"] = {}
    for fee in FEES:
        meta["absolu"][f"RE-1 {fee:g}"] = absolute(ctrl[H_MAIN], bars, atr_bps, fee, eng)
        for k, tr in keep.items():
            meta["absolu"][f"{k} {fee:g}"] = absolute(tr, bars, atr_bps, fee, eng)
    print("  performance absolue : faite")

    # F. Glissement du break-even, V3 à m = 2.
    meta["glissement"] = {}
    for H in HORIZONS:
        for slip in SLIPS:
            tr = run_be(eng, H, *FOCUS, slip=slip)
            eff = effect_ci(tr, ctrl[H], bars, atr_bps, N_BOOT)
            for fee in FEES:
                ab = absolute(tr, bars, atr_bps, fee, eng)
                ps = path_summary(path_draws(tr, ctrl[H], orders[H], atr_bps, fee))
                meta["glissement"][f"H{H} g{slip:g} {fee:g}"] = {**ab, **eff, **counts(tr, ctrl[H], atr_bps),
                                                                 "p_mdd": ps["p_mdd"], "p_calmar": ps["p_calmar"],
                                                                 "dmdd_p2.5": ps["dmdd_p2.5"], "dmdd_p97.5": ps["dmdd_p97.5"]}
        print(f"  glissement H = {H} : fait")

    # D5. Même drawdown par la seule taille : RE-1 au risque par ATR qui égale le MDD de la variante (H26).
    meta["taille"] = []
    for fee in FEES:
        for name, tr in [(f"V3 m = 2, glissement {s:g} bps", run_be(eng, H_MAIN, *FOCUS, slip=s)) for s in SLIPS] + \
                        [("V2 m = 2", keep[key("V2", 2.0)]), ("V1 m = 2", keep[key("V1", 2.0)])]:
            v = sized_path(tr, bars, atr_bps, fee, C2B.RISK)
            r = size_matched(ctrl[H_MAIN], bars, atr_bps, fee, v["mdd"])
            meta["taille"].append({"frais_bps": fee, "variante": name, "variante_cagr": v["cagr"], "variante_mdd": v["mdd"],
                                   "variante_calmar": v["calmar"], "variante_sous_pic": v["sous_pic_jours"],
                                   "re1_risque_bps": r["risque_bps"], "re1_cagr": r["cagr"], "re1_mdd": r["mdd"],
                                   "re1_calmar": r["calmar"], "re1_sous_pic": r["sous_pic_jours"]})
    print("  équivalent en taille : fait")

    # G. Diagnostic par année et trades sortis au break-even (V3, m = 2, H26).
    meta["annees"] = per_year(tr26, ctrl[H_MAIN], bars, atr_bps)
    meta["concentration"] = concentration(tr26, ctrl[H_MAIN], bars, atr_bps)
    meta["plus_couteux"] = costliest(tr26, ctrl[H_MAIN], bars, atr_bps, eng)
    meta["plus_favorables"] = costliest(tr26, ctrl[H_MAIN], bars, atr_bps, eng, best=True)
    meta["stops_initiaux"] = {"RE-1": int((ctrl[H_MAIN].stop & ~ctrl[H_MAIN].be_stop).sum()),
                              key(*FOCUS): int((tr26.stop & ~tr26.be_stop).sum()), "be": int(tr26.be_stop.sum())}
    dg = diagnostic(tr26, ctrl[H_MAIN], eng, bars, atr_bps, H_MAIN)
    meta["diag_agregats"] = {"2022": aggregate(dg[dg.annee == 2022]), "autres années": aggregate(dg[dg.annee != 2022]),
                             "toutes": aggregate(dg)}
    close = bars.set_index("time").close
    meta["btc_2022"] = float(close[close.index.year == 2022].iloc[-1] / close[close.index.year == 2022].iloc[0] - 1)
    print("  diagnostic 2022 : fait")
    return meta, dg, {"pdraw": pdraw, "ctrl": ctrl, "keep": keep, "tr26": tr26, "atr_bps": atr_bps, "dg": dg,
                      "eng": eng}


# ── Rapport ─────────────────────────────────────────────────────────────────────
def verification(ix, meta) -> list[list]:
    rk = meta["risque"]

    def row(label, annonce, mesure):
        return [label, annonce, mesure]

    v, r = ix(key(*FOCUS)), ix("RE-1")
    rows = []
    for H in HORIZONS:
        a, b = ix("RE-1", H), ix(key(*FOCUS), H)
        rows.append(row(f"MDD valorisé RE-1 → V3 m = 2, H{H}, 5 bps",
                        {24: "−14,2 → −11,2 %", 26: "−13,5 → −11,7 %", 28: "−16,2 → −12,5 %"}[H],
                        f"{pct(a['mdd_valorise_r25'], 2)} → {pct(b['mdd_valorise_r25'], 2)}"))
    for H, ann in ((26, "1,16 → 1,25"), (24, "0,94 → 1,20")):
        rows.append(row(f"Calmar RE-1 → V3 m = 2, H{H}, 5 bps", ann,
                        f"{fr(ix('RE-1', H)['calmar_r25'], 3)} → {fr(ix(key(*FOCUS), H)['calmar_r25'], 3)}"))
    for H, ann in ((26, "89 %"), (24, "92 %")):
        rows.append(row(f"Chemins où V3 m = 2 a un MDD moins profond, H{H}", ann,
                        f"{pct(rk[f'{key(*FOCUS)} H{H} 5']['p_mdd'], 1)} (MDD aux sorties, 2 000 chemins)"))
    e1 = meta["effets"][key("V3", 1.0)]
    rows.append(row("V3 m = 1 : gagnants coupés ; dont ≥ +3 ATR", "273 ; 82",
                    f"{n_fr(e1['n_coupes'])} ; {n_fr(e1['n_sup3_coupes'])}"))
    r1 = ix(key("V3", 1.0))
    rows.append(row("V3 m = 1 : coût des coupés ; gain des sauvés (ATR par trade, sur les 1 080 entrées)",
                    "−0,726 ; +0,569", f"{sg(r1['cout_coupes'], 3)} ; {sg(r1['gain_sauves'], 3)}"))
    rows.append(row("V3 m = 2 : sauvés, gain ; coupés, coût ; effet [IC]",
                    "147, +0,270 ; 121, −0,288 ; −0,018 [−0,131 ; +0,105]",
                    f"{n_fr(v['n_sauves'])}, {sg(v['gain_sauves'], 3)} ; {n_fr(v['n_coupes'])}, {sg(v['cout_coupes'], 3)} ; "
                    f"{ci(v['effet_atr_vs_RE1'], v['effet_atr_lo_vs_RE1'], v['effet_atr_hi_vs_RE1'], 3)}"))
    rows.append(row("RE-1 à 10 bps : espérance ATR [IC]", "+0,233 [−0,041 ; +0,511]",
                    ci(ix("RE-1", fee=10.0)["esperance_atr"], ix("RE-1", fee=10.0)["esperance_atr_lo"],
                       ix("RE-1", fee=10.0)["esperance_atr_hi"], 3)))
    return rows


def section_A(meta, ix) -> str:
    c = meta["controles"]
    rows = [["Glissement nul", "V1, V2 et V3 à m = 2, trois horizons : trades identiques aux courses de C03"
             if c["glissement_nul_egal_C03"] else "échec"],
            ["Additivité", "effet apparié de V3 = effet de V1 + effet de V2, trade par trade, aux trois horizons "
             "(les sous-familles ne partagent aucun trade en lecture cooldown)" if c["additivite_V3_egal_V1_plus_V2"] else "échec"],
            ["Mécanique", "V3 m = 2 : trades activés, sortis au break-even, sauvés et coupés identiques à resultats_C03.csv"
             if c["mecanique_egale_C03"] else "échec"],
            ["Contrôles de C03", "RE-1 = RE-1 de C02bis trade par trade (H24, 26, 28, deux lectures) ; seuil infini = RE-1 ; "
             "effet nul hors sorties au break-even (controles_C03.json)"]]
    out = ["## Annexe A — Validation technique", table(["Contrôle", "Résultat"], rows),
           "**Chiffres de la relecture, vérifiés dans les résultats bruts** (resultats_C03.csv et chemins réordonnés)",
           table(["Chiffre", "Relecture", "Mesuré"], verification(ix, meta))]
    return "\n\n".join(out)


def section_B(meta) -> str:
    out = [f"## Annexe B — Effet apparié BE − RE-1 à H = {H_MAIN}, global et par sous-famille (mêmes 1 080 entrées)",
           "Global : ATR par trade sur toutes les entrées [IC 95 %]. Par sous-famille : ATR par trade de la sous-famille "
           "[IC 95 %] ; une variante n'agit que sur son périmètre (V1 : F3 ; V2 : F2b)."]
    rows = []
    for p in PERIMETRES:
        for m in M_GRID:
            e = meta["effets"][key(p, m)]
            fam = [ci(e[f"effet_{k}"], e[f"effet_{k}_lo"], e[f"effet_{k}_hi"], 3) if k in PERIMETRES[p] else "— (hors périmètre)"
                   for k in ("F2b", "F3")]
            rows.append([C3.nom(key(p, m)), ci(e["effet_atr"], e["effet_atr_lo"], e["effet_atr_hi"], 3)] + fam)
    out.append(table(["Variante", "Global", "Sur les trades F2b (573)", "Sur les trades F3 (507)"], rows))
    return "\n\n".join(out)


def section_C(meta) -> str:
    e0 = meta["effets"][key("V3", 1.0)]
    out = [f"## Annexe C — Queue droite : gros gagnants de RE-1 coupés par le break-even (H = {H_MAIN})",
           f"Gros gagnants : trades de RE-1 à ≥ +3 ATR nets ({n_fr(e0['n_sup3'])} trades) et décile supérieur "
           f"({n_fr(e0['n_top10'])} trades). Cellule : part coupée ; part de leur contribution perdue ; coût par trade "
           "sur les 1 080 entrées (ATR)."]
    for name, lab in (("sup3", "≥ +3 ATR"), ("top10", "décile supérieur")):
        rows = []
        for m in M_GRID:
            cells = []
            for p in PERIMETRES:
                e = meta["effets"][key(p, m)]
                cells.append(f"{pct(e[f'part_{name}_coupes'], 1)} ; {pct(e[f'part_{name}_contribution_perdue'], 1)} ; "
                             f"{sg(e[f'cout_{name}_par_trade'], 3)}")
            rows.append([f"m = {fr(m, 1)}"] + cells)
        out.append(f"**Gros gagnants {lab}**\n\n" + table(["Seuil"] + [C3.NOMS_P[p] for p in PERIMETRES], rows))
    return "\n\n".join(out)


def section_D(meta, ix) -> str:
    rk = meta["risque"]
    e = meta["effets"][key(*FOCUS)]
    out = ["## Annexe D — Risque : V3 m = 2 (et V1, V2 à m = 2) contre RE-1",
           f"**D0. Trades concernés (V3 m = 2, H26)** — sur {n_fr(e['n_trades'])} entrées : {n_fr(e['n_actifs'])} break-even "
           f"déclenchés, {n_fr(e['n_be'])} exécutés (dont {n_fr(e['n_be_gap'])} en gap) : {n_fr(e['n_sauves'])} sauvés, "
           f"{n_fr(e['n_coupes'])} coupés. Gros gagnants de RE-1 coupés : {n_fr(e['n_sup3_coupes'])} sur {n_fr(e['n_sup3'])} à "
           f"≥ +3 ATR ({pct(e['part_sup3_coupes'], 1)}, {pct(e['part_sup3_contribution_perdue'], 1)} de leur contribution), "
           f"{n_fr(e['n_top10_coupes'])} sur {n_fr(e['n_top10'])} du décile supérieur ({pct(e['part_top10_coupes'], 1)}).",
           "**D1. Chemin réel** — MDD valorisé et Calmar à 0,25 % par ATR (resultats_C03.csv)."]
    rows = []
    for fee in FEES:
        for H in HORIZONS:
            cells = [f"{pct(ix('RE-1', H, fee=fee)['mdd_valorise_r25'], 1)} ; {fr(ix('RE-1', H, fee=fee)['calmar_r25'], 2)}"]
            for p, m in TRIO:
                r = ix(key(p, m), H, fee=fee)
                cells.append(f"{pct(r['mdd_valorise_r25'], 1)} ; {fr(r['calmar_r25'], 2)}")
            rows.append([f"{fr(fee, 0)} bps, H = {H}"] + cells)
    out.append(table(["Lecture", "RE-1", "V1 m = 2 (F3)", "V2 m = 2 (F2b)", "V3 m = 2 (les deux)"], rows))
    out.append("**D2. Chemins réordonnés** — 2 000 chemins, mois d'entrée tirés avec remise (mêmes tirages que les IC). "
               "MDD aux sorties ; Calmar = PnL annualisé sur 6 ans / |MDD aux sorties|. Cellule : écart observé sur le chemin "
               "réel ; P2,5 / médiane / P97,5 de l'écart sur les chemins ; part des chemins où la variante fait mieux.")
    rows = []
    for fee in FEES:
        for H in HORIZONS:
            for p, m in TRIO:
                s = rk[f"{key(p, m)} H{H} {fee:g}"]
                rows.append([f"{fr(fee, 0)} bps, H = {H}", key(p, m).replace(" m", " m = "),
                             f"{sg(100 * (s['mdd_be_obs'] - s['mdd_re1_obs']), 1)} ; {sg(100 * s['dmdd_p2.5'], 1)} / "
                             f"{sg(100 * s['dmdd_p50'], 1)} / {sg(100 * s['dmdd_p97.5'], 1)} ; {pct(s['p_mdd'], 0)}",
                             f"{sg(s['calmar_be_obs'] - s['calmar_re1_obs'], 2)} ; {sg(s['dcalmar_p2.5'], 2)} / "
                             f"{sg(s['dcalmar_p50'], 2)} / {sg(s['dcalmar_p97.5'], 2)} ; {pct(s['p_calmar'], 0)}"])
    out.append(table(["Lecture", "Variante", "Écart de MDD (points)", "Écart de Calmar"], rows))
    s = rk[f"{key(*FOCUS)} H{H_MAIN} 5"]
    out.append(f"**D3. Distribution des MDD aux sorties (H26, 5 bps)** — RE-1 : P5 {pct(s['mdd_re1_p5'], 1)}, médiane "
               f"{pct(s['mdd_re1_p50'], 1)}, P95 {pct(s['mdd_re1_p95'], 1)} (chemin réel {pct(s['mdd_re1_obs'], 1)}). "
               f"V3 m = 2 : P5 {pct(s['mdd_be_p5'], 1)}, médiane {pct(s['mdd_be_p50'], 1)}, P95 {pct(s['mdd_be_p95'], 1)} "
               f"(chemin réel {pct(s['mdd_be_obs'], 1)}).")
    rows = []
    for name, eps in meta["episodes"].items():
        rows.append([name.replace(" m", " m = ")] + [f"{pct(ep['profondeur'], 1)} ({ep['pic']} → {ep['creux']}, "
                                                      f"retour {ep['retour']})" for ep in eps]
                    + [fr(meta["sous_pic"][name], 0)])
    out.append("**D4. Trois drawdowns les plus profonds du capital valorisé (H26, 5 bps)** — pic → creux, retour au pic ; "
               "dernière colonne : plus longue période sous le pic (jours).\n\n"
               + table(["Configuration", "1er", "2e", "3e", "Sous le pic (j)"], rows))
    rows = []
    for t in meta["taille"]:
        rows.append([f"{fr(t['frais_bps'], 0)} bps", t["variante"],
                     f"{spct(t['variante_cagr'], 1)} ; {pct(t['variante_mdd'], 1)} ; {fr(t['variante_calmar'], 2)} ; "
                     f"{fr(t['variante_sous_pic'], 0)} j",
                     f"{fr(t['re1_risque_bps'] / 100, 3)} % ; {spct(t['re1_cagr'], 1)} ; {pct(t['re1_mdd'], 1)} ; "
                     f"{fr(t['re1_calmar'], 2)} ; {fr(t['re1_sous_pic'], 0)} j",
                     f"{sg(100 * (t['variante_cagr'] - t['re1_cagr']), 1)} pt"])
    out.append("**D5. Même drawdown par la seule taille (H26)** — RE-1, sans break-even, au risque par ATR qui donne le "
               "même MDD valorisé que la variante. Si la variante fait mieux à MDD égal, le break-even améliore l'efficience "
               "du capital ; sinon il équivaut à réduire la taille.\n\n"
               + table(["Frais", "Variante (0,25 % par ATR)", "Variante : PnL annualisé ; MDD ; Calmar ; sous le pic",
                        "RE-1 réduit : risque par ATR ; PnL annualisé ; MDD ; Calmar ; sous le pic",
                        "Écart de PnL annualisé, variante − RE-1 réduit"], rows))
    return "\n\n".join(out)


def abs_row(a: dict, name: str) -> list:
    return [name, ci(a["esp_atr"], a["esp_atr_lo"], a["esp_atr_hi"], 3), ci(a["esp_bps"], a["esp_bps_lo"], a["esp_bps_hi"], 1),
            pct(a["p_esp_pos"], 1), f"{fr(a['sd_trade_atr'], 2)} ; {fr(a['se_boot_atr'], 3)}",
            spct(a["pnl_r25"]), pct(a["mdd_r25"], 1), fr(a["calmar_r25"], 2)]


def section_E(meta) -> str:
    ab = meta["absolu"]
    head = ["Configuration", "Espérance ATR [IC]", "Espérance bps [IC]", "P(espérance > 0)", "Écart type par trade ; "
            "erreur type (ATR)", "PnL", "MDD", "Calmar"]
    out = [f"## Annexe E — Performance absolue à 5 et 10 bps (H = {H_MAIN}, cooldown, 0,25 % par ATR)",
           "P(espérance > 0) : part des 2 000 tirages bootstrap (grappes mensuelles) où l'espérance en ATR est positive. "
           "Erreur type : écart type bootstrap de l'espérance ; elle fixe la largeur de l'IC."]
    order = ["RE-1"] + [key(p, m) for p in PERIMETRES for m in M_GRID]
    for fee in FEES:
        rows = [abs_row(ab[f"{k} {fee:g}"], C3.nom(k)) for k in order]
        out.append(f"**{fr(fee, 0)} bps**\n\n" + table(head, rows))
    return "\n\n".join(out)


def section_E10(ix) -> str:
    rows = []
    for k in ["RE-1"] + [key(p, m) for p in PERIMETRES for m in M_GRID]:
        cells = [ci(ix(k, H, fee=10.0)["esperance_atr"], ix(k, H, fee=10.0)["esperance_atr_lo"],
                    ix(k, H, fee=10.0)["esperance_atr_hi"], 3) for H in HORIZONS]
        n_pos = sum(ix(k, H, fee=10.0)["esperance_atr_lo"] > 0 for H in HORIZONS)
        rows.append([C3.nom(k)] + cells + [f"{n_pos}/3"])
    return ("**IC de l'espérance à 10 bps aux trois horizons** (resultats_C03.csv) — dernière colonne : horizons où l'IC "
            "exclut 0.\n\n" + table(["Configuration"] + [f"H = {H}" for H in HORIZONS] + ["IC > 0"], rows))


def section_F(meta) -> str:
    g = meta["glissement"]
    out = ["## Annexe F — Stress d'exécution : glissement du seul break-even, V3 m = 2",
           "Le break-even reste à open[t + 1] ± 5 bps ; son prix d'exécution (niveau, ou ouverture en gap) est dégradé de 0, "
           "5 ou 10 bps. Stop initial et sorties à horizon inchangés. Effet apparié : sur les entrées de RE-1, frais "
           "compensés. Chemins : part des 2 000 chemins réordonnés où V3 a un MDD (un Calmar) meilleur que RE-1."]
    for fee in FEES:
        rows = []
        for H in HORIZONS:
            for slip in SLIPS:
                r = g[f"H{H} g{slip:g} {fee:g}"]
                rows.append([f"H = {H}", f"{fr(slip, 0)} bps", ci(r["esp_atr"], r["esp_atr_lo"], r["esp_atr_hi"], 3),
                             ci(r["effet_atr"], r["effet_atr_lo"], r["effet_atr_hi"], 3), spct(r["pnl_r25"]),
                             pct(r["mdd_r25"], 1), fr(r["calmar_r25"], 2), f"{n_fr(r['n_actifs'])} ; {n_fr(r['n_be'])}",
                             f"{pct(r['p_mdd'], 0)} ; {pct(r['p_calmar'], 0)}"])
        out.append(f"**{fr(fee, 0)} bps**\n\n" + table(["Horizon", "Glissement BE", "Espérance ATR [IC]",
                                                        "Effet apparié BE − RE-1 [IC]", "PnL", "MDD", "Calmar",
                                                        "BE déclenchés ; exécutés", "Chemins : MDD ; Calmar"], rows))
    head = ["Configuration", "PnL : 0,25 %/ATR ; 1x ; bps (1x)", "PF", "WR", "Espérance : bps [IC] ; ATR [IC]", "MDD",
            "Trades (/mois) ; stop initial ; BE", "Durée méd.", "Part des frais (1x)"]
    for fee in FEES:
        rows = []
        for name, a in [("RE-1", meta["absolu"][f"RE-1 {fee:g}"])] + \
                       [(f"V3 m = 2, glissement {s:g} bps", g[f"H{H_MAIN} g{s:g} {fee:g}"]) for s in SLIPS]:
            rows.append([name, f"{spct(a['pnl_r25'])} ; {spct(a['pnl_1x'])} ; {sg(a['pnl_bps'], 0)}", fr(a["pf"], 2),
                         pct(a["wr"]), f"{ci(a['esp_bps'], a['esp_bps_lo'], a['esp_bps_hi'], 1)} ; "
                                       f"{ci(a['esp_atr'], a['esp_atr_lo'], a['esp_atr_hi'], 3)}",
                         pct(a["mdd_r25"], 1), f"{n_fr(a['n_trades'])} ({fr(a['trades_par_mois'], 1)}) ; "
                                               f"{pct(a['part_stop_initial'], 0)} ; {pct(a['part_be_stop'], 0)}",
                         fr(a["duree_mediane"], 0), pct(a["part_frais"], 0)])
        out.append(f"**Huit métriques, H26, {fr(fee, 0)} bps**\n\n" + table(head, rows))
    return "\n\n".join(out)


def section_G(meta, dg: pd.DataFrame) -> str:
    out = [f"## Annexe G — Diagnostic par année, V3 m = 2 (H = {H_MAIN}, cooldown)",
           "**G1. Effet apparié par année d'entrée** — IC 95 % par grappes mensuelles de l'année ; RE-1 : espérance nette "
           "(5 bps) et nombre de Long / Short."]
    rows = [[str(r["annee"]), n_fr(r["n_trades"]), f"{n_fr(r['n_be'])} ({n_fr(r['n_sauves'])} sauvés, {n_fr(r['n_coupes'])} coupés)",
             ci(r["effet"], r["effet_lo"], r["effet_hi"], 3), sg(r["re1_esp"], 3), f"{n_fr(r['re1_long'])} / {n_fr(r['re1_short'])}"]
            for r in meta["annees"]]
    out.append(table(["Année", "Trades", "Sortis au BE", "Effet apparié ATR [IC]", "RE-1 : espérance ATR", "Long / Short"],
                     rows))
    ag = meta["diag_agregats"]
    lab = {"n_be": "Sorties au break-even", "n_sauves": "Sauvés (échec du breakout)", "n_coupes": "Coupés (reprise après retest)",
           "effet_moyen_par_sortie": "Effet moyen par sortie au BE (ATR)", "re1_sauves": "RE-1 moyen des sauvés (ATR)",
           "re1_coupes": "RE-1 moyen des coupés (ATR)", "part_long": "Part de Long", "part_f2b": "Part de F2b",
           "part_gap": "Part de sorties en gap", "med_atr14_bps": "ATR14 médian (bps)",
           "med_vol_sur_atr": "Volatilité réalisée / ATR14, médiane", "med_mae_avant_activation": "Excursion adverse avant activation, médiane (ATR)",
           "med_mfe_avant_be": "MFE avant le BE, médiane (ATR)", "med_barres_avant_be": "Barres avant le BE, médiane",
           "med_retest_apres_be": "Profondeur du retest après le BE, médiane (ATR)",
           "med_retest_sauves": "… retest des sauvés, médiane (ATR)", "med_retest_coupes": "… retest des coupés, médiane (ATR)",
           "med_mfe_apres_be": "MFE après le BE, médiane (ATR)", "med_mfe_apres_coupes": "… MFE après le BE des coupés, médiane"}
    rows = []
    for k, name in lab.items():
        cells = []
        for g in ("2022", "autres années", "toutes"):
            v = ag[g][k]
            cells.append(n_fr(v) if k.startswith("n_") else (pct(v, 0) if k.startswith("part_") else sg(v, 2)))
        rows.append([name] + cells)
    out.append(f"**G2. Trades sortis au break-even : 2022 contre les autres années** (BTC en 2022 : {spct(meta['btc_2022'], 0)})\n\n"
               + table(["Mesure", "2022", "Autres années", "Toutes"], rows))
    rows = [[str(c["annee"]), sg(c["effet"], 3), sg(c["effet_sans_pires"], 3),
             " ; ".join(f"{sg(v, 2)} (RE-1 {sg(b, 2)})" for v, b in zip(c["pires_couts"], c["pires_re1"])), sg(c["gain_max"], 2)]
            for c in meta["concentration"]]
    out.append("**G2 bis. Concentration du coût par année** — effet apparié de l'année, puis sans ses deux sorties au BE "
               "les plus coûteuses (même traitement pour chaque année) ; plus grand gain unitaire du break-even.\n\n"
               + table(["Année", "Effet par trade", "Sans les 2 plus coûteuses", "Les 2 plus coûteuses : effet (RE-1)",
                        "Plus grand gain"], rows))
    for k, lab in (("plus_couteux", "les plus coûteuses"), ("plus_favorables", "les plus favorables")):
        rows = [[c["entree"], c["sous_famille"], c["sens"], sg(c["res_re1"], 2), sg(c["effet"], 2)] for c in meta[k]]
        out.append(f"**G2 ter. Les dix sorties au BE {lab}, toutes années** (ATR)\n\n"
                   + table(["Entrée (UTC)", "Famille", "Sens", "RE-1", "Effet du BE"], rows))
    d22 = dg[dg.annee == 2022].sort_values("entree")
    rows = [[r.entree, r.sous_famille, r.sens, fr(r.atr14_bps, 0), fr(r.vol_sur_atr, 2), fr(r.mae_avant_activation, 2),
             fr(r.mfe_avant_be, 2), f"{r.barres_avant_be}{' (gap)' if r.gap else ''}", fr(r.retest_apres_be, 2),
             fr(r.mfe_apres_be, 2), sg(r.res_re1, 2) + (" (stop)" if r.re1_stoppe else ""), sg(r.res_be, 2), r.trajectoire]
            for r in d22.itertuples()]
    out.append("**G3. Les trades de 2022 sortis au break-even** — excursions en ATR14(t) depuis open[t + 1] ; volatilité "
               "réalisée = écart type des rendements 30 min pendant la fenêtre de RE-1 ; retest = excursion adverse entre la "
               "sortie au BE et la fin de RE-1.\n\n"
               + table(["Entrée (UTC)", "Famille", "Sens", "ATR14 (bps)", "Vol. / ATR", "Adverse avant activation",
                        "MFE avant BE", "Barres avant BE", "Retest après BE", "MFE après BE", "RE-1 (ATR)", "V3 (ATR)",
                        "Trajectoire"], rows))
    return "\n\n".join(out)


def section_H(meta, ix) -> str:
    rk = meta["risque"]
    out = ["## Annexe H — Asymétrie F2b / F3 à m = 2 : V2 (BE sur F2b seul) contre RE-1, avec V1 et V3",
           "Sur les mêmes entrées. Les effets sont additifs (annexe A) : V3 = V1 + V2 trade par trade."]
    rows = []
    for p, m in TRIO:
        e = meta["effets"][key(p, m)]
        for k in ("F2b", "F3"):
            if e[f"n_be_{k}"] == 0:
                continue
            rows.append([key(p, m).replace(" m", " m = "), k, f"{n_fr(e[f'n_actifs_{k}'])} ; {n_fr(e[f'n_be_{k}'])}",
                         f"{n_fr(e[f'n_sauves_{k}'])} ; {sg(e[f'gain_sauves_{k}'], 2)} ; {sg(e[f're1_sauves_{k}'], 2)}",
                         f"{n_fr(e[f'n_coupes_{k}'])} ; {sg(e[f'cout_coupes_{k}'], 2)} ; {sg(e[f're1_coupes_{k}'], 2)}",
                         f"{n_fr(e[f'n_sup3_coupes_{k}'])} / {n_fr(e[f'n_sup3_{k}'])}",
                         ci(e[f"effet_{k}"], e[f"effet_{k}_lo"], e[f"effet_{k}_hi"], 3)])
    out.append("**H1. Mécanique par sous-famille (H26)**\n\n"
               + table(["Variante", "Sous-famille", "Activés ; sortis au BE", "Sauvés : n ; gain moyen ; RE-1 moyen",
                        "Coupés : n ; coût moyen ; RE-1 moyen", "Gagnants ≥ +3 ATR coupés", "Effet par trade de la sous-famille [IC]"],
                        rows))
    rows = []
    for p, m in [("RE-1", None)] + TRIO:
        cells = []
        for fee in FEES:
            for H in HORIZONS:
                r = ix("RE-1" if p == "RE-1" else key(p, m), H, fee=fee)
                cells.append(f"{sg(r['esperance_atr'], 3)} ; {pct(r['mdd_valorise_r25'], 1)} ; {fr(r['calmar_r25'], 2)}")
        rows.append([p if p == "RE-1" else key(p, m).replace(" m", " m = ")] + cells)
    out.append("**H2. Espérance ATR ; MDD ; Calmar aux trois horizons** (5 bps puis 10 bps)\n\n"
               + table(["Configuration"] + [f"{fr(f, 0)} bps, H = {H}" for f in FEES for H in HORIZONS], rows))
    return "\n\n".join(out)


def write_report(meta, dg) -> None:
    ix = C3.Index(pd.read_csv(HERE / "resultats_C03.csv"))
    parts = [section_A(meta, ix), section_B(meta), section_C(meta), section_D(meta, ix), section_E(meta), section_E10(ix),
             section_F(meta), section_G(meta, dg), section_H(meta, ix)]
    narr = HERE / "narratif_C03_approfondi.md"
    head = narr.read_text(encoding="utf-8") if narr.exists() else "# EXP-C03 — analyse approfondie\n\n*(narratif à rédiger)*\n"
    (HERE / "rapport_C03_approfondi.md").write_text(
        head.rstrip() + "\n\n---\n\n# Annexes chiffrées (générées par `run_C03_approfondi.py`)\n\n" + "\n\n".join(parts) + "\n",
        encoding="utf-8")


# ── Figures ─────────────────────────────────────────────────────────────────────
def fig_bootstrap(pdraw) -> None:
    fig, axes = plt.subplots(1, 3, figsize=(19, 5.6))
    for k, col, lab in (("re1", "k", "RE-1"), ("be", "#2ca02c", "V3 m = 2")):
        axes[0].hist(100 * pdraw[k]["mdd"], bins=60, alpha=0.45, color=col, label=lab)
        axes[0].axvline(100 * pdraw[k]["obs_mdd"], color=col, lw=2)
    axes[0].set_xlabel("MDD aux sorties sur les chemins réordonnés (%) ; trait : chemin réel", fontsize=9)
    axes[0].legend(fontsize=8, frameon=False)
    for ax, k, lab, sc in ((axes[1], "mdd", "Écart de MDD, V3 − RE-1 (points ; > 0 : V3 moins profond)", 100.0),
                           (axes[2], "calmar", "Écart de Calmar, V3 − RE-1", 1.0)):
        d = sc * (pdraw["be"][k] - pdraw["re1"][k])
        obs = sc * ((pdraw["be"]["obs_mdd"] - pdraw["re1"]["obs_mdd"]) if k == "mdd"
                    else (pdraw["be"]["obs_calmar"] - pdraw["re1"]["obs_calmar"]))
        ax.hist(d, bins=60, color="#2ca02c", alpha=0.6)
        ax.axvline(0, color="0.3", lw=1)
        ax.axvline(obs, color="k", lw=2, label="chemin réel")
        for p in (2.5, 97.5):
            ax.axvline(np.percentile(d, p), color="#2ca02c", ls="--", lw=1)
        ax.set_xlabel(lab, fontsize=9)
        ax.set_title(f"part des chemins > 0 : {pct((d > 0).mean(), 0)}", fontsize=10)
        ax.legend(fontsize=8, frameon=False)
    fig.suptitle("EXP-C03 approfondi — Risque de chemin de V3 m = 2 contre RE-1 (H26, 5 bps, 2 000 chemins réordonnés "
                 "par mois)", fontsize=11)
    fig.tight_layout()
    C3._save(fig, "fig5_bootstrap_risque_V3m2.png")
    plt.close(fig)


def fig_equity(bars, ctrl, keep, tr26, atr_bps) -> None:
    fig, axes = plt.subplots(2, 1, figsize=(17, 9), sharex=True, gridspec_kw={"height_ratios": [2, 1]})
    for name, tr, col, lw in (("RE-1", ctrl, "k", 1.8), ("V2 m = 2 (BE sur F2b)", keep[key("V2", 2.0)], "#d62728", 1.1),
                              ("V3 m = 2 (BE sur F2b et F3)", tr26, "#2ca02c", 1.1)):
        w = risk_weights(atr_bps.reindex(tr.signal_bar.to_numpy()).to_numpy(dtype=float), C2B.RISK)
        eq = equity_curve_sized(bars, tr, 5.0, w)
        axes[0].plot(eq.index, 100 * (eq.to_numpy() - 1), color=col, lw=lw, label=name)
        axes[1].plot(eq.index, 100 * (eq.to_numpy() / np.maximum.accumulate(eq.to_numpy()) - 1), color=col, lw=lw)
    axes[0].set_ylabel("PnL net composé, 0,25 % par ATR (%)", fontsize=9)
    axes[1].set_ylabel("Sous le pic (%)", fontsize=9)
    axes[0].legend(fontsize=8, frameon=False)
    for ax in axes:
        ax.grid(alpha=0.3, lw=0.5)
        ax.axvspan(pd.Timestamp("2022-01-01", tz="UTC"), pd.Timestamp("2023-01-01", tz="UTC"), color="0.93", zorder=0)
    fig.suptitle("EXP-C03 approfondi — Capital et drawdown, H26, 5 bps (zone grise : 2022)", fontsize=11)
    fig.tight_layout()
    C3._save(fig, "fig6_equite_sous_eau_H26.png")
    plt.close(fig)


def fig_slippage(meta, ix) -> None:
    g = meta["glissement"]
    fig, axes = plt.subplots(1, 3, figsize=(19, 5.4))
    for fee, ls in zip(FEES, ("-", "--")):
        ref = ix("RE-1", fee=fee)
        ys = [[g[f"H{H_MAIN} g{s:g} {fee:g}"][k] for s in SLIPS] for k in ("esp_atr", "mdd_r25", "calmar_r25")]
        for ax, y, rk, sc in zip(axes, ys, ("esperance_atr", "mdd_valorise_r25", "calmar_r25"), (1, 100, 1)):
            ax.plot(SLIPS, sc * np.array(y), color="#2ca02c", marker="o", ls=ls, label=f"V3 m = 2, {fr(fee, 0)} bps")
            ax.axhline(sc * ref[rk], color="k", ls=ls, lw=1, label=f"RE-1, {fr(fee, 0)} bps")
    for ax, lab in zip(axes, ("Espérance nette par trade (ATR14(t))", "MDD valorisé, 0,25 % par ATR (%)", "Calmar")):
        ax.set_xlabel("Glissement du seul break-even (bps)", fontsize=9)
        ax.set_ylabel(lab, fontsize=9)
        ax.set_xticks(SLIPS)
        ax.grid(alpha=0.3, lw=0.5)
    axes[0].legend(fontsize=8, frameon=False)
    fig.suptitle("EXP-C03 approfondi — Stress d'exécution du break-even, V3 m = 2, H26", fontsize=11)
    fig.tight_layout()
    C3._save(fig, "fig7_stress_glissement_BE.png")
    plt.close(fig)


def fig_2022(meta, dg) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(17, 6))
    for sel, col, lab in ((dg.annee != 2022, "0.6", "autres années"), (dg.annee == 2022, "#d62728", "2022")):
        axes[0].scatter(dg.retest_apres_be[sel], dg.res_re1[sel], s=14, color=col, alpha=0.75, label=lab)
    axes[0].axhline(0, color="0.3", lw=0.8)
    axes[0].set_xlabel("Profondeur du retest après la sortie au BE (ATR14(t) sous l'entrée)", fontsize=9)
    axes[0].set_ylabel("Résultat net de RE-1 pour ce trade (ATR14(t), 5 bps) ; > 0 : trade coupé par le BE", fontsize=9)
    axes[0].legend(fontsize=8, frameon=False)
    axes[0].grid(alpha=0.3, lw=0.5)
    yr = meta["annees"]
    x = np.arange(len(yr))
    y = np.array([r["effet"] for r in yr])
    lo, hi = np.array([r["effet_lo"] for r in yr]), np.array([r["effet_hi"] for r in yr])
    axes[1].errorbar(x, y, yerr=[y - lo, hi - y], fmt="o", color="#2ca02c", capsize=4)
    axes[1].axhline(0, color="0.3", lw=0.8)
    axes[1].set_xticks(x, [str(r["annee"]) for r in yr])
    axes[1].set_ylabel("Effet apparié V3 m = 2 − RE-1 par trade (ATR14(t)), IC 95 %", fontsize=9)
    axes[1].grid(alpha=0.3, lw=0.5)
    fig.suptitle("EXP-C03 approfondi — Trades sortis au break-even (V3 m = 2, H26) et effet par année", fontsize=11)
    fig.tight_layout()
    C3._save(fig, "fig8_diagnostic_2022.png")
    plt.close(fig)


# ── Programme ───────────────────────────────────────────────────────────────────
def _json(o):
    if isinstance(o, dict):
        return {k: _json(v) for k, v in o.items()}
    if isinstance(o, list):
        return [_json(v) for v in o]
    if isinstance(o, (np.floating, float)):
        return None if not np.isfinite(o) else float(o)
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, np.bool_):
        return bool(o)
    return o


def main() -> None:
    if "--rapport" in sys.argv:
        meta = json.loads((HERE / "approfondi_C03.json").read_text(encoding="utf-8"))
        write_report(meta, pd.read_csv(HERE / "diagnostic_2022_C03.csv"))
        print(f"rapport_C03_approfondi.md régénéré dans {HERE}")
        return
    t0 = time.time()
    df, bars = load_dev_bars(), load_bars_dev()
    atlas, f, idx, atr = build_atlas(df)
    meta, dg, ctx = compute(bars, atlas, atr)
    meta["duree_s"] = round(time.time() - t0)
    (HERE / "approfondi_C03.json").write_text(json.dumps(_json(meta), ensure_ascii=False, indent=1), encoding="utf-8")
    dg.to_csv(HERE / "diagnostic_2022_C03.csv", index=False, float_format="%.6g")
    ix = C3.Index(pd.read_csv(HERE / "resultats_C03.csv"))
    fig_bootstrap(ctx["pdraw"])
    fig_equity(bars, ctx["ctrl"][H_MAIN], ctx["keep"], ctx["tr26"], ctx["atr_bps"])
    fig_slippage(meta, ix)
    fig_2022(meta, dg)
    write_report(json.loads(json.dumps(_json(meta))), dg)
    print(f"C03 approfondi : fait en {meta['duree_s']} s ; rapport, tableaux et figures dans {HERE}")


if __name__ == "__main__":
    main()
