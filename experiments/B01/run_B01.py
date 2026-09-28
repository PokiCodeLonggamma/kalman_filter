"""EXP-B01 — Catégorisation cinématique et asymétrie d'excursion (Étape B). Aucun PnL, aucun seuil optimisé.

Usage, depuis la racine du dépôt : python experiments/B01/run_B01.py
Sorties dans experiments/B01/ : excursions_signaux.csv, tableaux_univarie_B01.csv, tableaux_familles_B01.csv,
tableau_regimes_B01.csv (relecture), figures/*.png, rapport_B01.md (= narratif_B01.md rédigé à la main, suivi des
annexes chiffrées générées ici).
"""
from __future__ import annotations

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
from categorization import (BARRIERS, DESCRIPTORS, FAMILY_LABELS, HORIZONS, add_derived, assign_families,  # noqa: E402
                            barrier_key, barrier_table, bin_descriptor, cluster_bootstrap, excursion_table, summarize,
                            tail_sum, timing_drift)

FIG = HERE / "figures"
ATLAS_A01 = ROOT / "experiments" / "A01" / "atlas_signaux.csv"
SIDES = {"Tous": 0, "Long": 1, "Short": -1}
YEARS = list(range(2020, 2026))
DIFF_KEYS = ([f"asym_{H}_p50" for H in HORIZONS] + [f"pct_mfe_gt_mae_{H}" for H in HORIZONS]
             + ["win_strict_1p5", "win_strict_2p0"])
FAM_ORDER = ["F1", "F2a", "F2b", "F3", "F3 pur", "F4", "F5"]
FAM_COLORS = {"F1": "#1f5fa8", "F2a": "#6baed6", "F2b": "#8c6bb1", "F3": "#d9822b", "F3 pur": "#e6a15a",
              "F4": "#c0392b", "F5": "#7f7f7f", "Tous": "#222222"}
C_LONG, C_SHORT = "#1f5fa8", "#d9822b"
N_BOOT = 2000
REG = {"R1": "R1 = F1/F5 · x1 encore opposé", "R2": "R2 = F2b/F3 · x1 déjà retourné",
       "R3": "R3 = F1 · x1 déjà retourné, F2a, F4"}
REG_COLORS = {"Tous": "#222222", REG["R1"]: "#1f5fa8", REG["R2"]: "#d9822b", REG["R3"]: "#c0392b",
              "Hors R1-R3": "#7f7f7f"}


# ── Mise en forme ───────────────────────────────────────────────────────────────
def fr(x, nd=2) -> str:
    if x is None or pd.isna(x):
        return "—"
    return f"{x:.{nd}f}".replace(".", ",").replace("-", "−")


def sg(x, nd=2) -> str:
    return "—" if x is None or pd.isna(x) else f"{x:+.{nd}f}".replace(".", ",").replace("-", "−")


def pct(x, nd=1) -> str:
    return "—" if x is None or pd.isna(x) else fr(100 * x, nd) + " %"


def pp(x) -> str:
    return "—" if x is None or pd.isna(x) else (f"{100 * x:+.1f}".replace(".", ",").replace("-", "−") + " pts")


def n_fr(n) -> str:
    return f"{int(n):,}".replace(",", " ")


def table(header, rows) -> str:
    out = ["| " + " | ".join(header) + " |", "|" + "|".join(["---"] * len(header)) + "|"]
    return "\n".join(out + ["| " + " | ".join(str(c) for c in r) + " |" for r in rows])


def side_mask(d: pd.DataFrame, sv: int) -> np.ndarray:
    return np.ones(len(d), dtype=bool) if sv == 0 else (d.direction.to_numpy() == sv)


# ── Calculs ─────────────────────────────────────────────────────────────────────
def univariate(d: pd.DataFrame, ex: pd.DataFrame) -> pd.DataFrame:
    rows, years = [], d.year.to_numpy()
    for name in DESCRIPTORS:
        lab, order, bounds = bin_descriptor(d[name], name)
        lo_c, hi_c = order[0], order[-1]
        for side, sv in SIDES.items():
            sm = side_mask(d, sv)
            res = {}
            for cl in order:
                res[cl] = summarize(ex, sm & (lab == cl))
                rows.append({"descripteur": name, "sens": side, "classe": cl, "bornes": bounds[cl], **res[cl]})
            diff = {k: res[hi_c][k] - res[lo_c][k] for k in DIFF_KEYS}
            same = {k: 0 for k in DIFF_KEYS}
            for y in YEARS:
                ym = years == y
                s1, s0 = summarize(ex, sm & ym & (lab == hi_c)), summarize(ex, sm & ym & (lab == lo_c))
                for k in DIFF_KEYS:
                    dy = s1[k] - s0[k]
                    if pd.notna(dy) and dy != 0 and np.sign(dy) == np.sign(diff[k]):
                        same[k] += 1
            mono = {}
            if len(order) >= 3:
                for k in ("pct_mfe_gt_mae_26", "win_strict_1p5"):
                    dv = np.diff([res[c][k] for c in order])
                    mono[f"monotone_{k}"] = bool(np.all(dv > 0) or np.all(dv < 0))
            rows.append({"descripteur": name, "sens": side, "classe": f"{hi_c} − {lo_c}", "bornes": "", **diff,
                         **{f"annees_meme_signe_{k}": v for k, v in same.items()}, **mono})
    return pd.DataFrame(rows)


def strata(d: pd.DataFrame, fam: np.ndarray) -> dict[str, np.ndarray]:
    r, x1 = d.retrace_ratio.to_numpy(), d.x1_already_flipped_at_t.to_numpy(dtype=bool)
    rank, div, chop = d.run_rank.to_numpy(), d.cycle_seg_div_atr.to_numpy(), d.n_short_seg_48.to_numpy()
    s = {"Tous": np.ones(len(d), dtype=bool)}
    for F in ["F1", "F2a", "F2b", "F3"]:
        s[F] = fam == F
    s["F3 pur"] = (fam == "F3") & (r >= 1.0)
    s["F4"], s["F5"] = fam == "F4", fam == "F5"
    for F in ("F1", "F3"):
        s[f"{F} · x1 déjà retourné"] = (fam == F) & x1
        s[f"{F} · x1 encore opposé"] = (fam == F) & ~x1
    s["Rang 1"], s["Répétition"] = rank == 1, rank > 1
    s["Cycle : segment = extremum"], s["Cycle : plus bas plus haut / plus haut plus bas"] = div <= 1e-12, div > 1e-12
    s["n_short_seg_48 = 0"], s["n_short_seg_48 ≥ 1"] = chop == 0, chop >= 1
    lab, order, _ = bin_descriptor(d.A_vol, "A_vol")
    for q in order:
        s[f"A_vol {q}"] = lab == q
    return s


def families_table(d: pd.DataFrame, ex: pd.DataFrame, st: dict[str, np.ndarray]) -> pd.DataFrame:
    rows, years = [], d.year.to_numpy()
    held = (d.post_lag_bars >= 0).to_numpy()
    for name, m in st.items():
        for side, sv in SIDES.items():
            mm = m & side_mask(d, sv)
            s = summarize(ex, mm)
            yrs = sum(1 for y in YEARS if summarize(ex, mm & (years == y))["win_strict_1p5"] > 0.5)
            rows.append({"strate": name, "sens": side, **s, "part_univers": mm.sum() / len(d),
                         "stop_implicite_p50": float(np.median(d.obs_dist_seg_atr[mm])) if mm.any() else np.nan,
                         "retrace_p50": float(np.median(d.retrace_ratio[mm])) if mm.any() else np.nan,
                         "leg_p50": float(np.median(d.leg_atr[mm])) if mm.any() else np.nan,
                         "info_extremum_tenu": held[mm].mean() if mm.any() else np.nan,
                         "annees_win1p5_sup50": yrs})
    return pd.DataFrame(rows)


def negative_scan(uni: pd.DataFrame, famt: pd.DataFrame) -> pd.DataFrame:
    """Strates où l'asymétrie médiane est négative ET le taux strict < 50 % en Long comme en Short."""
    cands = [(f"{r.descripteur} = {r.classe}", uni[(uni.descripteur == r.descripteur) & (uni.classe == r.classe)])
             for r in uni[~uni.classe.str.contains("−")].drop_duplicates(["descripteur", "classe"]).itertuples()]
    cands += [(s, famt[famt.strate == s]) for s in famt.strate.unique()]
    out = []
    for name, g in cands:
        L, S = g[g.sens == "Long"].iloc[0], g[g.sens == "Short"].iloc[0]
        hs = [H for H in HORIZONS if L[f"asym_{H}_p50"] < 0 and S[f"asym_{H}_p50"] < 0]
        bs = [b for b in ("1p5", "2p0") if L[f"win_strict_{b}"] < 0.5 and S[f"win_strict_{b}"] < 0.5]
        sig = [b for b in ("1p5", "2p0") if L[f"win_strict_{b}_hi"] < 0.5 and S[f"win_strict_{b}_hi"] < 0.5]
        if hs and bs:
            out.append({"strate": name, "n_long": int(L.n), "n_short": int(S.n), "horizons_asym_neg": hs,
                        "barrieres_sous_50": bs, "barrieres_sous_50_wilson": sig,
                        "win1p5_long": L.win_strict_1p5, "win1p5_short": S.win_strict_1p5,
                        "asym26_long": L.asym_26_p50, "asym26_short": S.asym_26_p50})
    return pd.DataFrame(out)


# ── Sections du rapport ─────────────────────────────────────────────────────────
def section_univers(d, ex, leg_p50) -> str:
    rows = [["Signaux (univers A01, contrôlé identique à `atlas_signaux.csv`)", n_fr(len(d))],
            ["Entrée", "open[t+1] ; normalisation par ATR14(t), connu à la clôture de t"],
            ["Médiane de `leg_atr` (coupure des familles)", fr(leg_p50, 3) + " ATR"]]
    for H in HORIZONS:
        rows.append([f"Fenêtres H = {H} incomplètes (fin 2025, NaN)", n_fr(ex[f"mfe_{H}_atr"].isna().sum())])
    for b in BARRIERS:
        o = ex[f"barrier_{barrier_key(b)}_outcome"]
        rows.append([f"Barrières ±{fr(b, 1)} ATR : gain / perte / ambiguë / timeout / censurée",
                     " / ".join(n_fr((o == k).sum()) for k in ("win", "loss", "ambiguous", "timeout", "censored"))])
    return "## A. Univers et conventions\n\n" + table(["Élément", "Valeur"], rows)


def section_reference(famt) -> str:
    g = famt[famt.strate == "Tous"].set_index("sens")
    rows = []
    for H in HORIZONS:
        for k, lab, nd in [("mfe", "MFE", 2), ("mae", "\\|MAE\\|", 2), ("asym", "Asym", 2), ("ret", "Rendement", 2)]:
            rows.append([f"{lab} H = {H} (ATR, médiane)"] + [fr(g.loc[s, f"{k}_{H}_p50"], nd) for s in SIDES])
        rows.append([f"MFE > \\|MAE\\| H = {H}"] + [pct(g.loc[s, f"pct_mfe_gt_mae_{H}"]) for s in SIDES])
    for b in BARRIERS:
        k = barrier_key(b)
        rows.append([f"Barrière ±{fr(b, 1)} : gain strict [IC 95 %]"]
                    + [f"{pct(g.loc[s, f'win_strict_{k}'])} [{pct(g.loc[s, f'win_strict_{k}_lo'])} ; "
                       f"{pct(g.loc[s, f'win_strict_{k}_hi'])}]" for s in SIDES])
        rows.append([f"Barrière ±{fr(b, 1)} : gain, timeouts inclus / ambiguës / timeouts"]
                    + [f"{pct(g.loc[s, f'win_all_{k}'])} / {pct(g.loc[s, f'amb_{k}'])} / {pct(g.loc[s, f'timeout_{k}'])}"
                       for s in SIDES])
    return "## B. Référence : tous les signaux\n\n" + table(["Mesure"] + list(SIDES), rows)


def section_ecarts(uni) -> str:
    diffs = uni[uni.classe.str.contains("−")]
    out = []
    for side in SIDES:
        rows = []
        for r in diffs[diffs.sens == side].itertuples():
            def cell(k, fmt):
                return f"{fmt(getattr(r, k))} ({getattr(r, 'annees_meme_signe_' + k)}/6)"
            rows.append([f"`{r.descripteur}`", r.classe, cell("pct_mfe_gt_mae_6", pp), cell("pct_mfe_gt_mae_26", pp),
                         cell("asym_26_p50", lambda v: fr(v, 2)), cell("win_strict_1p5", pp),
                         cell("win_strict_2p0", pp)])
        out.append(f"### {side}\n\n" + table(["Descripteur", "Classes", "Δ MFE>MAE H6", "Δ MFE>MAE H26",
                                              "Δ Asym H26 (ATR)", "Δ gain ±1,5", "Δ gain ±2,0"], rows))
    return ("## C. Univarié : écart classe haute − classe basse\n\nEntre parenthèses : nombre d'années 2020-2025 où "
            "l'écart annuel a le même signe que l'écart global (bornes de classe fixes).\n\n" + "\n\n".join(out))


def section_detail(uni) -> str:
    cls = uni[~uni.classe.str.contains("−")]
    rows = []
    for (name, cl), g in cls.groupby(["descripteur", "classe"], sort=False):
        g = g.set_index("sens")
        rows.append([f"`{name}`", cl, g.loc["Tous", "bornes"], n_fr(g.loc["Tous", "n"])]
                    + [pct(g.loc[s, "pct_mfe_gt_mae_26"]) for s in SIDES] + [pct(g.loc[s, "win_strict_1p5"]) for s in SIDES])
    return ("## D. Univarié détaillé\n\n" + table(["Descripteur", "Classe", "Bornes", "n", "MFE>MAE H26 Tous",
                                                  "Long", "Short", "Gain ±1,5 Tous", "Long", "Short"], rows))


def section_familles(famt) -> str:
    out = []
    for side in SIDES:
        rows = []
        for r in famt[famt.sens == side].itertuples():
            rows.append([r.strate, f"{n_fr(r.n)} ({pct(r.part_univers)})", fr(r.stop_implicite_p50, 2),
                         pct(r.pct_mfe_gt_mae_6), pct(r.pct_mfe_gt_mae_26), pct(r.pct_mfe_gt_mae_48), fr(r.asym_26_p50, 2),
                         pct(r.win_strict_1p0), f"{pct(r.win_strict_1p5)} [{pct(r.win_strict_1p5_lo)} ; {pct(r.win_strict_1p5_hi)}]",
                         pct(r.win_strict_2p0), pct(r.timeout_2p0), pct(r.info_extremum_tenu), f"{r.annees_win1p5_sup50}/6"])
        out.append(f"### {side}\n\n" + table(["Strate", "n (part)", "Stop implicite P50 (ATR)", "MFE>MAE H6", "H26", "H48",
                                              "Asym H26 P50", "Gain ±1,0", "Gain ±1,5 [IC 95 %]", "Gain ±2,0",
                                              "Timeout ±2,0", "Info : extremum tenu", "Années gain ±1,5 > 50 %"], rows))
    legend = "\n".join(f"- **{k}** : {v}" for k, v in FAMILY_LABELS.items())
    return ("## E. Familles et strates\n\n" + legend + "\n- **F3 pur** : F3 avec `retrace_ratio` ≥ 1,00.\n\n"
            "Taux de gain « strict » : hors timeouts, barres ambiguës comptées en échec. L'extremum tenu est donné à "
            "titre d'information (cible interdite, `RESEARCH_INSIGHTS.md` I-M1).\n\n" + "\n\n".join(out))


def section_negatif(neg) -> str:
    if neg.empty:
        return "## F. Strates à asymétrie négative en Long ET en Short\n\nAucune strate ne remplit la condition."
    rows = [[r.strate, n_fr(r.n_long), n_fr(r.n_short), ", ".join(map(str, r.horizons_asym_neg)),
             ", ".join(r.barrieres_sous_50) or "—", ", ".join(r.barrieres_sous_50_wilson) or "—",
             pct(r.win1p5_long), pct(r.win1p5_short), fr(r.asym26_long, 2), fr(r.asym26_short, 2)] for r in neg.itertuples()]
    return ("## F. Strates à asymétrie négative en Long ET en Short\n\nCondition : médiane de Asym_H < 0 pour au moins un "
            "horizon et taux de gain strict < 50 % pour au moins une barrière (±1,5 ou ±2,0), dans les deux sens.\n\n"
            + table(["Strate", "n Long", "n Short", "H où Asym < 0", "Barrières < 50 %", "< 50 % (IC Wilson)",
                     "Gain ±1,5 Long", "Gain ±1,5 Short", "Asym H26 Long", "Asym H26 Short"], rows))


def section_annees(d, ex, st) -> str:
    years = d.year.to_numpy()
    out = []
    for side, sv in list(SIDES.items())[1:]:
        rows = []
        for F in ["Tous"] + FAM_ORDER:
            mm = st[F] & side_mask(d, sv)
            rows.append([F] + [pct(summarize(ex, mm & (years == y))["win_strict_1p5"]) for y in YEARS])
        out.append(f"### {side}\n\n" + table(["Famille"] + [str(y) for y in YEARS], rows))
    return "## G. Stabilité annuelle : gain strict ±1,5 ATR par famille\n\n" + "\n\n".join(out)


def section_directionnel(d, ex, st) -> str:
    """Décomposition timing / dérive par strate, sans placebo : variation médiane du prix de open[t+1] à close[t+H]
    (en ATR14(t), non orientée) après les signaux Long (ΔL) et après les signaux Short (ΔS).
    timing = (ΔL − ΔS) / 2 (> 0 : le prix va dans le sens du signal) ; dérive = (ΔL + ΔS) / 2 (même sens des deux côtés)."""
    extra = {}
    for name, cl in [("nis_z_100", "Q4"), ("prev_seg_len", "Q4"), ("saturation", "Q4"), ("retrace_ratio", "Q1"),
                     ("leg_atr", "Q4"), ("obs_dist_seg_atr", "Q4")]:
        lab, _, _ = bin_descriptor(d[name], name)
        extra[f"{name} {cl}"] = lab == cl
    keys = (["Tous", "F1", "F1 · x1 encore opposé", "F1 · x1 déjà retourné", "F2a", "F2b", "F3", "F3 pur", "F4", "F5",
             "Rang 1", "Répétition",
             "Cycle : plus bas plus haut / plus haut plus bas", "A_vol Q1", "A_vol Q4"] + list(extra))
    masks = {**st, **extra}
    dirn = d.direction.to_numpy()
    rows = []
    for k in keys:
        m = masks[k]
        cells = [k, n_fr((m & (dirn == 1)).sum()), n_fr((m & (dirn == -1)).sum())]
        for H in (6, 26, 48):
            cells += [fr(v, 2) for v in timing_drift(ex[f"ret_{H}_atr"].to_numpy()[m], dirn[m])]
        s = summarize(ex, m)
        cells += [f"{pct(s['pct_mfe_gt_mae_6'])} [{pct(s['pct_mfe_gt_mae_6_lo'])} ; {pct(s['pct_mfe_gt_mae_6_hi'])}]",
                  f"{pct(s['pct_mfe_gt_mae_26'])} [{pct(s['pct_mfe_gt_mae_26_lo'])} ; {pct(s['pct_mfe_gt_mae_26_hi'])}]"]
        rows.append(cells)
    return ("## H. Timing ou dérive ? Décomposition par strate (sans placebo)\n\nΔL et ΔS : variation médiane du prix "
            "de open[t+1] à close[t+H] (ATR14(t), non orientée), après les signaux Long et après les signaux Short. "
            "Timing = (ΔL − ΔS) / 2 : part où le prix suit le sens du signal. Dérive = (ΔL + ΔS) / 2 : part commune aux "
            "deux sens (marché). Dernières colonnes : part MFE > \\|MAE\\|, Long et Short réunis, IC de Wilson à 95 %.\n\n"
            + "Moyennes, queues et intervalles de confiance du timing : annexe I.\n\n"
            + table(["Strate", "n Long", "n Short", "Timing H6", "Dérive H6", "Timing H26", "Dérive H26", "Timing H48",
                     "Dérive H48", "MFE>MAE H6 [IC]", "MFE>MAE H26 [IC]"], rows))


# ── Relecture : médianes, moyennes, queues et trois régimes ─────────────────────
def regimes(d: pd.DataFrame, fam: np.ndarray) -> dict[str, np.ndarray]:
    """Regroupement proposé par le porteur à la relecture, après lecture des résultats (post hoc) : R1 essoufflement
    précoce, R2 sortie de range avec bascule de vitesse, R3 continuation. Les lignes « ↳ » détaillent les sous-strates."""
    x1 = d.x1_already_flipped_at_t.to_numpy(dtype=bool)
    nis4 = bin_descriptor(d.nis_z_100, "nis_z_100")[0] == "Q4"
    r1 = np.isin(fam, ["F1", "F5"]) & ~x1
    r2 = np.isin(fam, ["F2b", "F3"]) & x1
    r3 = ((fam == "F1") & x1) | np.isin(fam, ["F2a", "F4"])
    return {"Tous": np.ones(len(d), dtype=bool),
            REG["R1"]: r1, "↳ F1 · x1 encore opposé": (fam == "F1") & ~x1,
            "↳ F5 · x1 encore opposé": (fam == "F5") & ~x1, "↳ R1 hors nis_z_100 Q4": r1 & ~nis4,
            REG["R2"]: r2, "↳ F3 · x1 déjà retourné": (fam == "F3") & x1,
            "↳ F2b · x1 déjà retourné": (fam == "F2b") & x1, "↳ R2 hors nis_z_100 Q4": r2 & ~nis4,
            REG["R3"]: r3, "↳ F1 · x1 déjà retourné": (fam == "F1") & x1, "↳ F2a": fam == "F2a", "↳ F4": fam == "F4",
            "Hors R1-R3": ~(r1 | r2 | r3), "nis_z_100 Q4": nis4, "F3 (famille entière)": fam == "F3",
            "F3 pur": (fam == "F3") & (d.retrace_ratio.to_numpy() >= 1.0)}


def regime_table(d: pd.DataFrame, ex: pd.DataFrame, reg: dict[str, np.ndarray]) -> pd.DataFrame:
    """Par groupe et par horizon, sur le rendement orienté ret_H (sans frais ni stop) : timing et dérive en médiane et en
    moyenne, IC 95 % par bootstrap de grappes mensuelles, années > 0, moyenne winsorisée, écart de chaque sens à Tous,
    asymétrie moyenne, queues P10 / P90."""
    dirn, years = d.direction.to_numpy(), d.year.to_numpy()
    ts = pd.to_datetime(d.timestamp, utc=True)
    month = (ts.dt.year * 12 + ts.dt.month).to_numpy()
    ret = {H: ex[f"ret_{H}_atr"].to_numpy() for H in HORIZONS}
    asym = {H: ex[f"asym_{H}_atr"].to_numpy() for H in HORIZONS}
    wins = {}
    for H in HORIZONS:
        chg = dirn * ret[H]                                  # variation non orientée du prix
        wins[H] = dirn * np.clip(chg, *np.nanpercentile(chg, [1, 99]))
    base = {H: (np.nanmean(ret[H][dirn == 1]), np.nanmean(ret[H][dirn == -1])) for H in HORIZONS}
    held = (d.post_lag_bars >= 0).to_numpy()
    rows = []
    for name, m in reg.items():
        idx = np.flatnonzero(m)

        def stat(pos, idx=idx):
            g = idx[pos]
            return [timing_drift(ret[H][g], dirn[g], s)[0] for H in HORIZONS for s in ("median", "mean")]

        lo, hi = np.nanpercentile(cluster_bootstrap(stat, month[idx], N_BOOT, seed=0), [2.5, 97.5], axis=0)
        for j, H in enumerate(HORIZONS):
            r, L, S = ret[H], m & (dirn == 1), m & (dirn == -1)
            row = {"groupe": name, "H": H, "n": int(m.sum()), "n_long": int(L.sum()), "n_short": int(S.sum()),
                   "part_univers": m.mean(), "stop_implicite_p50": float(np.median(d.obs_dist_seg_atr[m])),
                   "info_extremum_tenu": held[m].mean()}
            for k, (s, key) in enumerate((("median", "med"), ("mean", "moy"))):
                row[f"timing_{key}"], row[f"derive_{key}"] = timing_drift(r[m], dirn[m], s)
                row[f"timing_{key}_lo"], row[f"timing_{key}_hi"] = lo[2 * j + k], hi[2 * j + k]
                row[f"annees_timing_{key}_pos"] = int(sum(
                    timing_drift(r[m & (years == y)], dirn[m & (years == y)], s)[0] > 0 for y in YEARS))
            row.update({"timing_moy_winsor": timing_drift(wins[H][m], dirn[m], "mean")[0],
                        "ecart_tous_long": np.nanmean(r[L]) - base[H][0],
                        "ecart_tous_short": np.nanmean(r[S]) - base[H][1],
                        "asym_moy": timing_drift(asym[H][m], dirn[m], "mean")[0],
                        "queue_long": tail_sum(r[L]), "queue_short": tail_sum(r[S]),
                        "p10": float(np.nanpercentile(r[m], 10)), "p90": float(np.nanpercentile(r[m], 90))})
            rows.append(row)
    return pd.DataFrame(rows)


def section_moyennes(rt: pd.DataFrame) -> str:
    g = {(r.groupe, r.H): r for r in rt.itertuples()}
    rows = []
    for name in REG_COLORS:
        r6, r26, r48 = g[(name, 6)], g[(name, 26)], g[(name, 48)]
        rows.append([name, f"{n_fr(r6.n)} ({pct(r6.part_univers)})", fr(r6.stop_implicite_p50, 2),
                     pct(r6.info_extremum_tenu), " / ".join(sg(x.timing_med) for x in (r6, r26, r48)),
                     " / ".join(sg(x.timing_moy) for x in (r6, r26, r48)),
                     f"{sg(r26.queue_long)} / {sg(r26.queue_short)}", f"{sg(r48.queue_long)} / {sg(r48.queue_short)}",
                     sg(r48.asym_moy)])
    synth = table(["Groupe", "n (part)", "Stop implicite P50 (ATR)", "Info : extremum tenu",
                   "Timing médian H6 / H26 / H48", "Timing moyen H6 / H26 / H48", "P90 + P10 H26, Long / Short",
                   "P90 + P10 H48, Long / Short", "Asym moyenne H48"], rows)
    per_h = []
    for j, H in enumerate(HORIZONS):
        rows = [[r.groupe, f"{n_fr(r.n_long)} / {n_fr(r.n_short)}",
                 f"{sg(r.timing_med)} [{sg(r.timing_med_lo)} ; {sg(r.timing_med_hi)}] ({r.annees_timing_med_pos}/6)",
                 f"{sg(r.timing_moy)} [{sg(r.timing_moy_lo)} ; {sg(r.timing_moy_hi)}] ({r.annees_timing_moy_pos}/6)",
                 sg(r.timing_moy_winsor), f"{sg(r.ecart_tous_long)} / {sg(r.ecart_tous_short)}", sg(r.asym_moy),
                 f"{sg(r.queue_long)} / {sg(r.queue_short)}", f"{sg(r.p10)} / {sg(r.p90)}"]
                for r in rt[rt.H == H].itertuples()]
        per_h.append(f"### I.{j + 2} Horizon H = {H}\n\n" + table(
            ["Groupe", "n Long / Short", "Timing médian [IC 95 %] (ans > 0)", "Timing moyen [IC 95 %] (ans > 0)",
             "Moyenne winsorisée", "Écart à Tous, Long / Short", "Asym moyenne", "P90 + P10, Long / Short",
             "P10 / P90"], rows))
    intro = (
        "Regroupement proposé par le porteur à la relecture, après lecture des résultats (post hoc) :\n"
        f"- **{REG['R1']}** : essoufflement précoce ;\n- **{REG['R2']}** : sortie de range avec bascule de vitesse ;\n"
        f"- **{REG['R3']}** : continuation.\n\nLes lignes « ↳ » détaillent les sous-strates ; `nis_z_100` Q4 recoupe R1 "
        "et R2.\n\nToutes les mesures portent sur ret_H, rendement orienté de open[t+1] à close[t+H] en ATR14(t), sans "
        "frais ni stop :\n"
        "- timing = (m_L + m_S) / 2 et dérive = (m_L − m_S) / 2, où m_L et m_S sont la médiane ou la moyenne de ret_H "
        "après les Long et après les Short (annexe H pour la médiane) ;\n"
        f"- IC 95 % : bootstrap de grappes, {n_fr(N_BOOT)} tirages de mois civils avec remise ; les fenêtres qui se "
        "chevauchent dans un même mois restent ensemble ;\n"
        "- (ans > 0) : nombre d'années 2020-2025 où la statistique annuelle est positive ;\n"
        "- moyenne winsorisée : timing moyen après écrêtage de la variation du prix aux P1 et P99 de tous les signaux ;\n"
        "- écart à Tous : moyenne de ret_H du groupe moins celle de tous les signaux du même sens ;\n"
        "- asymétrie moyenne : (moyenne Long + moyenne Short) / 2 de MFE_H − \\|MAE_H\\| ;\n"
        "- P90 + P10 de ret_H par sens : positif quand la queue droite s'étend plus loin que la gauche ; pour Tous, la "
        "dérive du BTC le rend positif en Long et négatif en Short ;\n"
        "- extremum tenu : information a posteriori (`RESEARCH_INSIGHTS.md` I-M1), part des signaux dont l'extremum du "
        "segment tient jusqu'au signal suivant.")
    return ("## I. Médianes, moyennes et queues : trois régimes (relecture)\n\n" + intro + "\n\n### I.1 Synthèse\n\n"
            + synth + "\n\n" + "\n\n".join(per_h))


# ── Figures ─────────────────────────────────────────────────────────────────────
def _save(fig, name: str) -> None:
    for k in range(6):
        try:
            fig.savefig(FIG / name, dpi=150)
            return
        except OSError:
            if k == 5:
                raise
            time.sleep(0.5)


def figures(d, ex, uni, famt, st) -> None:
    FIG.mkdir(parents=True, exist_ok=True)
    diffs = uni[uni.classe.str.contains("−")]
    fig, axes = plt.subplots(1, 2, figsize=(13, 6.5), sharey=True)
    for ax, (k, titre) in zip(axes, [("win_strict_1p5", "Δ gain strict ±1,5 ATR (points)"),
                                     ("pct_mfe_gt_mae_26", "Δ part MFE > |MAE| à H = 26 (points)")]):
        for side, col, off in [("Long", C_LONG, -0.15), ("Short", C_SHORT, 0.15)]:
            g = diffs[diffs.sens == side].reset_index(drop=True)
            for i, r in g.iterrows():
                stable = r[f"annees_meme_signe_{k}"] >= 5
                ax.plot(100 * r[k], i + off, "o", ms=6, color=col, mfc=col if stable else "white", mew=1.4,
                        label=side if i == 0 else None)
        ax.axvline(0, color="0.35", lw=0.8)
        ax.set_title(titre, fontsize=10)
        ax.grid(axis="x", alpha=0.3, lw=0.5)
        ax.tick_params(labelsize=8)
    g = diffs[diffs.sens == "Tous"].reset_index(drop=True)
    axes[0].set_yticks(range(len(g)), [f"{r.descripteur} ({r.classe})" for r in g.itertuples()], fontsize=8)
    axes[0].invert_yaxis()
    axes[0].legend(fontsize=8, frameon=False, loc="lower right")
    fig.suptitle("EXP-B01 — Effet univarié : classe haute − classe basse (plein : même signe ≥ 5 années sur 6)", fontsize=11)
    fig.tight_layout()
    _save(fig, "fig1_univarie_effets.png")
    plt.close(fig)

    fig, axes = plt.subplots(1, 2, figsize=(12, 4.4), sharey=True)
    for ax, side in zip(axes, ["Long", "Short"]):
        for F in ["Tous"] + FAM_ORDER:
            r = famt[(famt.strate == F) & (famt.sens == side)].iloc[0]
            ax.plot(HORIZONS, [r[f"asym_{H}_p50"] for H in HORIZONS], marker="o", ms=4, lw=1.6 if F != "Tous" else 1.2,
                    ls="--" if F in ("Tous", "F3 pur") else "-", color=FAM_COLORS[F], label=F)
        ax.axhline(0, color="0.35", lw=0.8)
        ax.set_xticks(HORIZONS)
        ax.set_xlabel("Horizon H (barres de 30 min)", fontsize=9)
        ax.set_title(side, fontsize=10)
        ax.grid(alpha=0.3, lw=0.5)
        ax.tick_params(labelsize=8)
    axes[0].set_ylabel("Médiane de MFE_H − |MAE_H| (ATR14(t))", fontsize=9)
    axes[1].legend(fontsize=8, frameon=False, ncol=2)
    fig.suptitle("EXP-B01 — Asymétrie d'excursion médiane par famille, depuis open[t+1]", fontsize=11)
    fig.tight_layout()
    _save(fig, "fig2_familles_asym.png")
    plt.close(fig)

    fig, axes = plt.subplots(1, 2, figsize=(12, 4.8), sharey=True)
    labels = ["Tous"] + FAM_ORDER
    for ax, side in zip(axes, ["Long", "Short"]):
        for j, (b, mk) in enumerate([("1p0", "s"), ("1p5", "o"), ("2p0", "^")]):
            for i, F in enumerate(labels):
                r = famt[(famt.strate == F) & (famt.sens == side)].iloc[0]
                y = i + (j - 1) * 0.22
                if b == "1p5":
                    ax.plot([100 * r.win_strict_1p5_lo, 100 * r.win_strict_1p5_hi], [y, y], color=FAM_COLORS[F], lw=1.2)
                ax.plot(100 * r[f"win_strict_{b}"], y, mk, ms=5, color=FAM_COLORS[F],
                        label=f"±{b.replace('p', ',')} ATR" if i == 0 else None)
        ax.axvline(50, color="0.35", lw=0.8, ls="--")
        ax.set_title(side, fontsize=10)
        ax.set_xlabel("Gain strict : barrière favorable touchée en premier (%)", fontsize=9)
        ax.grid(axis="x", alpha=0.3, lw=0.5)
        ax.tick_params(labelsize=8)
    axes[0].set_yticks(range(len(labels)), labels, fontsize=9)
    axes[0].invert_yaxis()
    axes[1].legend(fontsize=8, frameon=False, title="Barrière (IC 95 % : ±1,5)", title_fontsize=8)
    fig.suptitle("EXP-B01 — Barrières symétriques de premier passage (48 barres max.)", fontsize=11)
    fig.tight_layout()
    _save(fig, "fig3_barrieres_long_short.png")
    plt.close(fig)

    years = d.year.to_numpy()
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.4), sharey=True)
    for ax, (side, sv) in zip(axes, [("Long", 1), ("Short", -1)]):
        for F in ["Tous"] + FAM_ORDER:
            mm = st[F] & side_mask(d, sv)
            v = [100 * summarize(ex, mm & (years == y))["win_strict_1p5"] for y in YEARS]
            ax.plot(YEARS, v, marker="o", ms=4, lw=1.4, ls="--" if F in ("Tous", "F3 pur") else "-",
                    color=FAM_COLORS[F], label=F)
        ax.axhline(50, color="0.35", lw=0.8, ls="--")
        ax.set_title(side, fontsize=10)
        ax.grid(alpha=0.3, lw=0.5)
        ax.tick_params(labelsize=8)
    axes[0].set_ylabel("Gain strict ±1,5 ATR (%)", fontsize=9)
    axes[1].legend(fontsize=8, frameon=False, ncol=2)
    fig.suptitle("EXP-B01 — Stabilité annuelle du gain strict ±1,5 ATR par famille", fontsize=11)
    fig.tight_layout()
    _save(fig, "fig4_stabilite_annuelle.png")
    plt.close(fig)


def fig_regimes(rt: pd.DataFrame) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.6), sharey=True)
    for ax, (key, titre) in zip(axes, [("med", "Timing médian"), ("moy", "Timing moyen")]):
        for name, col in REG_COLORS.items():
            g = rt[rt.groupe == name].sort_values("H")
            ax.plot(g.H, g[f"timing_{key}"], marker="o", ms=4, lw=1.6, color=col, ls="--" if name == "Tous" else "-",
                    label=name)
            ax.fill_between(g.H, g[f"timing_{key}_lo"], g[f"timing_{key}_hi"], color=col, alpha=0.10, lw=0)
        ax.axhline(0, color="0.35", lw=0.8)
        ax.set_xticks(HORIZONS)
        ax.set_xlabel("Horizon H (barres de 30 min)", fontsize=9)
        ax.set_title(f"{titre} (bande : IC 95 %, grappes mensuelles)", fontsize=10)
        ax.grid(alpha=0.3, lw=0.5)
        ax.tick_params(labelsize=8)
    axes[0].set_ylabel("(m_L + m_S) / 2 de ret_H (ATR14(t))", fontsize=9)
    axes[1].legend(fontsize=8, frameon=False, loc="lower left")
    fig.suptitle("EXP-B01 — Timing au close par régime, médiane contre moyenne (sans frais ni stop)", fontsize=11)
    fig.tight_layout()
    _save(fig, "fig5_regimes_timing.png")
    plt.close(fig)


def main() -> None:
    df = load_dev_bars()
    atlas, f, idx, atr = build_atlas(df)
    ref = pd.read_csv(ATLAS_A01)
    if not (np.array_equal(ref.bar_index, atlas.bar_index) and np.array_equal(ref.direction, atlas.direction)
            and np.allclose(ref.obs_dist_seg_atr, atlas.obs_dist_seg_atr, rtol=0, atol=1e-12)):
        raise RuntimeError("l'univers recalculé diffère de experiments/A01/atlas_signaux.csv")
    d = add_derived(atlas)
    leg_p50 = float(np.median(d.leg_atr))
    fam = assign_families(d, leg_p50)
    ex = pd.concat([excursion_table(f.open, f.high, f.low, f.close, idx, d.direction, atr),
                    barrier_table(f.open, f.high, f.low, idx, d.direction, atr)], axis=1)

    ids = ["signal_id", "timestamp", "bar_index", "year", "direction", "is_flip"]
    out = pd.concat([d[ids + DESCRIPTORS], pd.Series(fam, name="famille"),
                     (d.post_lag_bars >= 0).rename("post_info_extremum_tenu"), ex], axis=1)
    out.to_csv(HERE / "excursions_signaux.csv", index=False)

    uni = univariate(d, ex)
    st = strata(d, fam)
    famt = families_table(d, ex, st)
    neg = negative_scan(uni, famt)
    uni.to_csv(HERE / "tableaux_univarie_B01.csv", index=False)
    famt.to_csv(HERE / "tableaux_familles_B01.csv", index=False)
    rt = regime_table(d, ex, regimes(d, fam))
    rt.to_csv(HERE / "tableau_regimes_B01.csv", index=False)
    figures(d, ex, uni, famt, st)
    fig_regimes(rt)

    parts = [section_univers(d, ex, leg_p50), section_reference(famt), section_ecarts(uni), section_detail(uni),
             section_familles(famt), section_negatif(neg), section_annees(d, ex, st), section_directionnel(d, ex, st),
             section_moyennes(rt)]
    narr = HERE / "narratif_B01.md"
    head = narr.read_text(encoding="utf-8") if narr.exists() else "# EXP-B01\n\n*(narratif à rédiger)*\n"
    (HERE / "rapport_B01.md").write_text(
        head.rstrip() + "\n\n---\n\n# Annexes chiffrées (générées par `run_B01.py`)\n\n" + "\n\n".join(parts) + "\n",
        encoding="utf-8")
    print(f"B01 : {len(out)} signaux ; rapport, tableaux et figures écrits dans {HERE}")


if __name__ == "__main__":
    main()
