"""EXP-B01 — Catégorisation cinématique et asymétrie d'excursion (Étape B). Aucun PnL, aucun seuil optimisé.

Usage, depuis la racine du dépôt : python experiments/B01/run_B01.py
Sorties dans experiments/B01/ : excursions_signaux.csv, tableaux_univarie_B01.csv, tableaux_familles_B01.csv,
figures/*.png, rapport_B01.md (= narratif_B01.md rédigé à la main, suivi des annexes chiffrées générées ici).
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
                            barrier_key, barrier_table, bin_descriptor, excursion_table, summarize)

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


# ── Mise en forme ───────────────────────────────────────────────────────────────
def fr(x, nd=2) -> str:
    if x is None or pd.isna(x):
        return "—"
    return f"{x:.{nd}f}".replace(".", ",").replace("-", "−")


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
    keys = (["Tous", "F1", "F1 · x1 déjà retourné", "F2a", "F2b", "F3", "F3 pur", "F4", "F5", "Rang 1", "Répétition",
             "Cycle : plus bas plus haut / plus haut plus bas", "A_vol Q1", "A_vol Q4"] + list(extra))
    masks = {**st, **extra}
    dirn = d.direction.to_numpy()
    rows = []
    for k in keys:
        m = masks[k]
        cells = [k, n_fr((m & (dirn == 1)).sum()), n_fr((m & (dirn == -1)).sum())]
        for H in (26, 48):
            r = ex[f"ret_{H}_atr"].to_numpy()
            dl = np.nanmedian(r[m & (dirn == 1)])
            ds = np.nanmedian(-r[m & (dirn == -1)])
            cells += [fr((dl - ds) / 2, 2), fr((dl + ds) / 2, 2)]
        s = summarize(ex, m)
        cells += [f"{pct(s['pct_mfe_gt_mae_6'])} [{pct(s['pct_mfe_gt_mae_6_lo'])} ; {pct(s['pct_mfe_gt_mae_6_hi'])}]",
                  f"{pct(s['pct_mfe_gt_mae_26'])} [{pct(s['pct_mfe_gt_mae_26_lo'])} ; {pct(s['pct_mfe_gt_mae_26_hi'])}]"]
        rows.append(cells)
    return ("## H. Timing ou dérive ? Décomposition par strate (sans placebo)\n\nΔL et ΔS : variation médiane du prix "
            "de open[t+1] à close[t+H] (ATR14(t), non orientée), après les signaux Long et après les signaux Short. "
            "Timing = (ΔL − ΔS) / 2 : part où le prix suit le sens du signal. Dérive = (ΔL + ΔS) / 2 : part commune aux "
            "deux sens (marché). Dernières colonnes : part MFE > \\|MAE\\|, Long et Short réunis, IC de Wilson à 95 %.\n\n"
            + table(["Strate", "n Long", "n Short", "Timing H26", "Dérive H26", "Timing H48", "Dérive H48",
                     "MFE>MAE H6 [IC]", "MFE>MAE H26 [IC]"], rows))


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
    figures(d, ex, uni, famt, st)

    parts = [section_univers(d, ex, leg_p50), section_reference(famt), section_ecarts(uni), section_detail(uni),
             section_familles(famt), section_negatif(neg), section_annees(d, ex, st), section_directionnel(d, ex, st)]
    narr = HERE / "narratif_B01.md"
    head = narr.read_text(encoding="utf-8") if narr.exists() else "# EXP-B01\n\n*(narratif à rédiger)*\n"
    (HERE / "rapport_B01.md").write_text(
        head.rstrip() + "\n\n---\n\n# Annexes chiffrées (générées par `run_B01.py`)\n\n" + "\n\n".join(parts) + "\n",
        encoding="utf-8")
    print(f"B01 : {len(out)} signaux ; rapport, tableaux et figures écrits dans {HERE}")


if __name__ == "__main__":
    main()
