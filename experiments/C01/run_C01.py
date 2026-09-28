"""EXP-C01 — découplage de la sortie (horizon fixe) et isolation des régimes en exécution séquentielle (Étape C).

Usage, depuis la racine du dépôt : python experiments/C01/run_C01.py
Sorties dans experiments/C01/ : resultats_C01.csv, annuel_C01.csv, figures/*.png, rapport_C01.md (= narratif_C01.md
rédigé à la main, suivi des annexes chiffrées générées ici).

Aucun stop, aucun take-profit : sortie à open[t + 1 + H] (H ∈ {6, 13, 26, 48}), une seule position à la fois, frais
aller-retour de 5 et 10 bps. Contrôle bloquant : l'ancre native P6.5d doit être reproduite à l'identique.
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
from categorization import add_derived, assign_families, bin_descriptor  # noqa: E402
from envelope import by_year, dev_signals, mean_ci, summarize, time_stop_trades  # noqa: E402
from estimand import load_bars_dev  # noqa: E402
from estimand.stoploss import simulate_strategy  # noqa: E402

FIG = HERE / "figures"
HORIZONS = (6, 13, 26, 48)
FEES = (5.0, 10.0)
YEARS = list(range(2020, 2026))
REF_TRADES = ROOT / "experiments" / "p6_5" / "strategie_stop_trades.csv"
ANCRE = "Ancre native P6.5d"
Q4 = "nis_z_100 Q4"
EXPECTED = {"R1": 1935, "R2": 1874, "R3": 2347, Q4: 1824, "Tous hors R3": 4949, f"Tous hors {Q4}": 5472,
            "Tous hors R3 et hors Q4": 4066, "R1 hors Q4": 1592, "R2 hors Q4": 1452, "F2b·x1": 787, "F3·x1": 1087,
            "F2b·x1 hors Q4": 741, "F3·x1 hors Q4": 711}


# ── Mise en forme ───────────────────────────────────────────────────────────────
def fr(x, nd=2) -> str:
    return "—" if x is None or pd.isna(x) else f"{x:.{nd}f}".replace(".", ",").replace("-", "−")


def sg(x, nd=1) -> str:
    if x is None or pd.isna(x):
        return "—"
    return "+∞" if np.isinf(x) else f"{x:+.{nd}f}".replace(".", ",").replace("-", "−")


def pct(x, nd=1) -> str:
    return "—" if x is None or pd.isna(x) else fr(100 * x, nd) + " %"


def n_fr(n) -> str:
    return f"{int(n):,}".replace(",", " ")


def table(header, rows) -> str:
    out = ["| " + " | ".join(header) + " |", "|" + "|".join(["---"] * len(header)) + "|"]
    return "\n".join(out + ["| " + " | ".join(str(c) for c in r) + " |" for r in rows])


# ── Univers, régimes, configurations ────────────────────────────────────────────
def regime_masks(atlas: pd.DataFrame) -> dict[str, np.ndarray]:
    """Définitions figées de l'annexe I de B01 (RESEARCH_INSIGHTS.md §4), recalculées depuis l'atlas."""
    d = add_derived(atlas)
    fam = assign_families(d, float(np.median(d.leg_atr)))
    x1 = d.x1_already_flipped_at_t.to_numpy(dtype=bool)
    q4 = bin_descriptor(d.nis_z_100, "nis_z_100")[0] == "Q4"
    ref = pd.read_csv(ROOT / "experiments" / "B01" / "excursions_signaux.csv", usecols=["bar_index", "famille"])
    if not (np.array_equal(ref.bar_index, atlas.bar_index) and np.array_equal(ref.famille, fam)):
        raise SystemExit("familles différentes de experiments/B01/excursions_signaux.csv : arrêt")
    r1 = np.isin(fam, ["F1", "F5"]) & ~x1
    r2 = np.isin(fam, ["F2b", "F3"]) & x1
    r3 = ((fam == "F1") & x1) | np.isin(fam, ["F2a", "F4"])
    f2b, f3 = (fam == "F2b") & x1, (fam == "F3") & x1
    m = {"R1": r1, "R2": r2, "R3": r3, Q4: q4, "Tous hors R3": ~r3, f"Tous hors {Q4}": ~q4,
         "Tous hors R3 et hors Q4": ~(r3 | q4), "R1 hors Q4": r1 & ~q4, "R2 hors Q4": r2 & ~q4, "F2b·x1": f2b,
         "F3·x1": f3, "F2b·x1 hors Q4": f2b & ~q4, "F3·x1 hors Q4": f3 & ~q4}
    bad = {k: int(v.sum()) for k, v in m.items() if int(v.sum()) != EXPECTED[k]}
    if bad:
        raise SystemExit(f"effectifs différents de B01 : {bad}")
    return m


def configurations(m: dict[str, np.ndarray], n: int) -> list[dict]:
    """(nom, masque, mode, palier, contrôle). Chaque variante ne diffère de son contrôle que par un facteur."""
    c = [dict(nom="Tous", masque=np.ones(n, dtype=bool), mode=1, palier="1 et 2", controle=ANCRE)]
    for nom, key in [("Tous hors R3", "Tous hors R3"), (f"Tous hors {Q4}", f"Tous hors {Q4}"), ("R1", "R1"),
                     ("R2", "R2"), ("↳ F2b · x1 déjà retourné", "F2b·x1"), ("↳ F3 · x1 déjà retourné", "F3·x1"),
                     ("R3", "R3"), (Q4, Q4)]:
        c.append(dict(nom=nom, masque=m[key], mode=1, palier="2", controle="Tous"))
    for nom, key, ctrl in [(f"Tous hors R3 et hors {Q4}", "Tous hors R3 et hors Q4", "Tous hors R3"),
                           (f"R1 hors {Q4}", "R1 hors Q4", "R1"), (f"R2 hors {Q4}", "R2 hors Q4", "R2"),
                           (f"↳ F2b · x1 déjà retourné hors {Q4}", "F2b·x1 hors Q4", "↳ F2b · x1 déjà retourné"),
                           (f"↳ F3 · x1 déjà retourné hors {Q4}", "F3·x1 hors Q4", "↳ F3 · x1 déjà retourné")]:
        c.append(dict(nom=nom, masque=m[key], mode=1, palier="3A", controle=ctrl))
    for nom, key, ctrl in [("R3 en continuation", "R3", "R3"), (f"{Q4} en continuation", Q4, Q4)]:
        c.append(dict(nom=nom, masque=m[key], mode=-1, palier="3B", controle=ctrl))
    return c


def check_anchor(bars, f) -> tuple[pd.DataFrame, dict]:
    """Ancre native P6.5d : trades identiques au fichier de référence (bloquant)."""
    sig = dev_signals(f)
    tr, ouvert = simulate_strategy(bars, sig, None)
    ref = pd.read_csv(REF_TRADES)
    ref = ref[ref.variante == "sans_stop"].reset_index(drop=True)
    same = len(tr) == len(ref) == 6037 and all(np.array_equal(tr[c].to_numpy(), ref[c].to_numpy())
                                               for c in ("entry_bar", "exit_bar", "side", "signal_bar"))
    same = same and np.array_equal([float(f"{v:.10g}") for v in tr.ret_gross_bps], ref.ret_gross_bps.to_numpy())
    if not same:
        raise SystemExit("ancre P6.5d non reproduite : arrêt (tout écart bloque la suite)")
    return tr, {"n_signaux": len(sig), "ouvert": ouvert}


# ── Calcul ──────────────────────────────────────────────────────────────────────
def run_all(bars, atlas, atr_bps, confs, anchor_tr, n_sig_all):
    t_all = atlas.bar_index.to_numpy()
    s_all = atlas.direction.to_numpy()
    res, ann, trades = [], [], {}
    for fee in FEES:
        m = summarize(anchor_tr, bars, atr_bps, fee, n_candidates=n_sig_all, n_open=1)
        res.append({"palier": "1", "configuration": ANCRE, "controle": "", "mode": 1, "H": "native",
                    "frais_bps": fee, **m, **mean_ci(anchor_tr, bars, fee)})
        ann += [{"configuration": ANCRE, "H": "native", "frais_bps": fee, **r}
                for r in by_year(anchor_tr, bars, atr_bps, fee).to_dict("records")]
    trades[(ANCRE, "native")] = anchor_tr
    for c in confs:
        for H in HORIZONS:
            tr = time_stop_trades(bars, t_all[c["masque"]], s_all[c["masque"]], H, c["mode"])
            trades[(c["nom"], H)] = tr
            for fee in FEES:
                m = summarize(tr, bars, atr_bps, fee, n_candidates=int(c["masque"].sum()))
                res.append({"palier": c["palier"], "configuration": c["nom"], "controle": c["controle"],
                            "mode": c["mode"], "H": H, "frais_bps": fee, **m, **mean_ci(tr, bars, fee)})
                ann += [{"configuration": c["nom"], "H": H, "frais_bps": fee, **r}
                        for r in by_year(tr, bars, atr_bps, fee).to_dict("records")]
    res, ann = pd.DataFrame(res), pd.DataFrame(ann)
    tous = res[res.configuration == "Tous"].set_index(["H", "frais_bps"])
    for u in ("bps", "atr"):
        for s in ("long", "short"):
            res[f"ecart_tous_{s}_{u}"] = [r[f"{s}_{u}"] - tous.loc[(r.H, r.frais_bps), f"{s}_{u}"]
                                         if r.H != "native" else np.nan for _, r in res.iterrows()]
    cnt = ann.groupby(["configuration", "H", "frais_bps"]).agg(
        annees_pnl_pos=("pnl_bps", lambda v: int((v > 0).sum())),
        annees_timing_pos=("timing_bps", lambda v: int((v > 0).sum()))).reset_index()
    res = res.merge(cnt, on=["configuration", "H", "frais_bps"], how="left")
    return res, ann, trades


def exit_gap_bps(bars) -> dict:
    """Écart entre close[t + H] (sortie des excursions de B01) et open[t + 1 + H] (sortie de C01), toutes barres."""
    c, o = bars.close.to_numpy()[:-1], bars.open.to_numpy()[1:]
    g = np.abs(o / c - 1.0) * 1e4
    return {"identiques": float((g == 0).mean()), "p50": float(np.median(g)), "p99": float(np.percentile(g, 99)),
            "max": float(g.max())}


# ── Sections du rapport ─────────────────────────────────────────────────────────
HEAD8 = ["Configuration", "PnL net : composé ; bps cumulés", "PF", "WR", "Espérance : bps [IC 95 %] ; ATR",
         "Max DD : valorisé ; bps", "Trades : n ; ignorés ; /mois", "Durée méd. (barres)", "Part des frais"]
HEADLS = ["Configuration", "Long : bps ; ATR", "Short : bps ; ATR", "Timing : bps [IC 95 %] ; ATR", "Dérive (bps)",
          "Écart à Tous, Long / Short (bps)", "Années PnL > 0", "Années timing > 0"]


def row8(r) -> list:
    return [r.configuration, f"{pct(r.pnl_compose)} ; {sg(r.pnl_bps, 0)}", fr(r.pf, 3), pct(r.wr),
            f"{sg(r.esperance_bps, 1)} [{sg(r.esperance_bps_lo, 1)} ; {sg(r.esperance_bps_hi, 1)}] ; {sg(r.esperance_atr, 3)}",
            f"{pct(r.mdd_valorise)} ; {sg(r.mdd_bps, 0)}",
            f"{n_fr(r.n_trades)} ; {pct(r.part_ignores, 0)} ; {fr(r.trades_par_mois, 1)}", fr(r.duree_mediane, 0),
            pct(r.part_frais, 0)]


def rowls(r) -> list:
    return [r.configuration, f"{sg(r.long_bps, 2)} ; {sg(r.long_atr, 3)}", f"{sg(r.short_bps, 2)} ; {sg(r.short_atr, 3)}",
            f"{sg(r.timing_bps, 1)} [{sg(r.timing_bps_lo, 1)} ; {sg(r.timing_bps_hi, 1)}] ; {sg(r.timing_atr, 3)}",
            sg(r.derive_bps, 2),
            "—" if pd.isna(r.ecart_tous_long_bps) else f"{sg(r.ecart_tous_long_bps, 2)} / {sg(r.ecart_tous_short_bps, 2)}",
            f"{int(r.annees_pnl_pos)}/6", f"{int(r.annees_timing_pos)}/6"]


def _block(res, names, H, title) -> str:
    out = [f"#### {title}"]
    for fee in FEES:
        sub = [res[(res.configuration == n) & (res.H == h) & (res.frais_bps == fee)].iloc[0] for n, h in
               [(n, H if n != ANCRE else "native") for n in names]]
        out.append(f"**{fr(fee, 0)} bps aller-retour — 8 métriques**\n\n" + table(HEAD8, [row8(r) for r in sub]))
        out.append(f"**{fr(fee, 0)} bps — Long / Short / timing (nets)**\n\n" + table(HEADLS, [rowls(r) for r in sub]))
    return "\n\n".join(out)


def section_controles(meta) -> str:
    a, g = meta["ancre"], meta["gap"]
    rows = [["Ancre P6.5d sans stop (sortie au signal opposé, 5 bps)",
             f"6 037 trades identiques au fichier de référence (barres, sens, rendements) ; trade ouvert fin 2025 : "
             f"signal {a['ouvert']['signal_bar']}"],
            ["Ancre P6.5d, stop 2,5 %", "6 589 trades identiques (test `test_ancre_p65d_reproduite`)"],
            ["Signaux de la stratégie native", f"{n_fr(a['n_signaux'])} (univers A01 + le signal de fin 2025)"],
            ["Univers des configurations à horizon fixe", "7 296 signaux d'A01 ; familles identiques à B01"],
            ["Sortie à horizon fixe", "open[t + 1 + H] ; position détenue pendant les barres t + 1 … t + H"],
            ["Écart open[b + 1] / close[b] (toutes barres)",
             f"nul dans {pct(g['identiques'])} des cas ; médiane {fr(g['p50'], 2)} bps ; P99 {fr(g['p99'], 2)} bps ; "
             f"max {fr(g['max'], 1)} bps"],
            ["Période", "2020-01 → 2025-12 (72 mois) ; aucune barre de 2026 lue"]]
    return "## A. Ancre et conventions\n\n" + table(["Contrôle", "Résultat"], rows)


def section_palier1(res) -> str:
    out = ["## B. Palier 1 — Découplage de la sortie (Tous)",
           "Contrôle : ancre native (sortie au signal opposé). Variantes : même flux, sortie à horizon fixe."]
    for fee in FEES:
        sub = [res[(res.configuration == ANCRE) & (res.frais_bps == fee)].iloc[0]]
        sub += [res[(res.configuration == "Tous") & (res.H == H) & (res.frais_bps == fee)].iloc[0] for H in HORIZONS]
        lab = [ANCRE] + [f"Tous, H = {H}" for H in HORIZONS]
        rows8 = [[lab[i]] + row8(r)[1:] for i, r in enumerate(sub)]
        rowsls = [[lab[i]] + rowls(r)[1:] for i, r in enumerate(sub)]
        out.append(f"**{fr(fee, 0)} bps aller-retour — 8 métriques**\n\n" + table(HEAD8, rows8))
        out.append(f"**{fr(fee, 0)} bps — Long / Short / timing (nets)**\n\n" + table(HEADLS, rowsls))
    return "\n\n".join(out)


def section_palier2(res) -> str:
    names = ["Tous", "Tous hors R3", f"Tous hors {Q4}", "R1", "R2", "↳ F2b · x1 déjà retourné",
             "↳ F3 · x1 déjà retourné", "R3", Q4]
    out = ["## C. Palier 2 — Sous-ensemble cinématique à horizon fixe (sens du signal)",
           "Contrôle : Tous au même horizon (première ligne de chaque tableau)."]
    out += [_block(res, names, H, f"H = {H}") for H in HORIZONS]
    return "\n\n".join(out)


def section_palier3(res) -> str:
    pairs_a = [("Tous hors R3", f"Tous hors R3 et hors {Q4}"), ("R1", f"R1 hors {Q4}"), ("R2", f"R2 hors {Q4}"),
               ("↳ F2b · x1 déjà retourné", f"↳ F2b · x1 déjà retourné hors {Q4}"),
               ("↳ F3 · x1 déjà retourné", f"↳ F3 · x1 déjà retourné hors {Q4}")]
    pairs_b = [("R3", "R3 en continuation"), (Q4, f"{Q4} en continuation")]
    out = ["## D. Palier 3 — Ablation et inversion d'un seul facteur",
           "Chaque variante suit immédiatement son contrôle du palier 2."]
    for titre, pairs in [(f"3A. Éviction de {Q4}", pairs_a), ("3B. Inversion en continuation (−direction)", pairs_b)]:
        out.append(f"### {titre}")
        out += [_block(res, [n for p in pairs for n in p], H, f"H = {H}") for H in HORIZONS]
    return "\n\n".join(out)


def section_annees(ann) -> str:
    out = ["## E. Stabilité annuelle : espérance nette par trade (bps, 5 bps aller-retour)"]
    for H in HORIZONS:
        g = ann[(ann.H == H) & (ann.frais_bps == 5.0)]
        rows = []
        for name in g.configuration.unique():
            gg = g[g.configuration == name].set_index("annee")
            rows.append([name] + [f"{sg(gg.esperance_bps.get(y), 1)} ({n_fr(gg.n_trades.get(y, 0))})" for y in YEARS])
        out.append(f"### H = {H}\n\nEntre parenthèses : nombre de trades.\n\n" + table(["Configuration"] + [str(y) for y in YEARS], rows))
    a = ann[(ann.configuration == ANCRE) & (ann.frais_bps == 5.0)].set_index("annee")
    out.append("### Ancre native\n\n" + table(["Configuration"] + [str(y) for y in YEARS],
                                             [[ANCRE] + [f"{sg(a.esperance_bps.get(y), 1)} ({n_fr(a.n_trades.get(y, 0))})"
                                                         for y in YEARS]]))
    return "\n\n".join(out)


# ── Figures ─────────────────────────────────────────────────────────────────────
MAIN = ["Tous", f"Tous hors R3 et hors {Q4}", "R1", "R2", "R3", Q4, "R3 en continuation", f"{Q4} en continuation"]
COLORS = {"Tous": "#222222", f"Tous hors R3 et hors {Q4}": "#7f7f7f", "R1": "#1f5fa8", "R2": "#d9822b",
          "R3": "#c0392b", Q4: "#8c6bb1", "R3 en continuation": "#e57373", f"{Q4} en continuation": "#b39ddb",
          "Tous hors R3": "#9e9e9e", f"Tous hors {Q4}": "#bdbdbd", f"R1 hors {Q4}": "#5b8fd1",
          f"R2 hors {Q4}": "#f0a75a", ANCRE: "#000000"}
H_COLORS = {6: "#9ecae1", 13: "#6baed6", 26: "#2171b5", 48: "#08306b"}


def _save(fig, name: str) -> None:
    for k in range(6):
        try:
            fig.savefig(FIG / name, dpi=140)
            return
        except OSError:
            if k == 5:
                raise
            time.sleep(0.5)


def _cum(bars, tr, fee):
    net = tr.ret_gross_bps.to_numpy() - fee
    return pd.DatetimeIndex(bars.time.iloc[tr.exit_bar.to_numpy()]), np.cumsum(net)


def figures(bars, res, ann, trades) -> None:
    FIG.mkdir(parents=True, exist_ok=True)
    fig, axes = plt.subplots(2, 5, figsize=(22, 8.5), sharex=True)
    for i, fee in enumerate(FEES):
        ax = axes[i, 0]
        x, y = _cum(bars, trades[(ANCRE, "native")], fee)
        ax.plot(x, y, color="k", lw=1.4, label="Ancre native")
        for H in HORIZONS:
            x, y = _cum(bars, trades[("Tous", H)], fee)
            ax.plot(x, y, color=H_COLORS[H], lw=1.2, label=f"Tous, H = {H}")
        ax.set_title(f"Palier 1 — {fr(fee, 0)} bps", fontsize=10)
        for j, H in enumerate(HORIZONS):
            ax = axes[i, j + 1]
            for name in MAIN:
                x, y = _cum(bars, trades[(name, H)], fee)
                ax.plot(x, y, color=COLORS[name], lw=1.3 if name != "Tous" else 1.6,
                        ls="--" if "continuation" in name else "-", label=name)
            ax.set_title(f"H = {H} — {fr(fee, 0)} bps", fontsize=10)
    for ax in axes.flat:
        ax.axhline(0, color="0.4", lw=0.7)
        ax.grid(alpha=0.3, lw=0.5)
        ax.tick_params(labelsize=7)
    axes[0, 0].set_ylabel("PnL net cumulé (bps)", fontsize=9)
    axes[1, 0].set_ylabel("PnL net cumulé (bps)", fontsize=9)
    axes[0, 0].legend(fontsize=7, frameon=False)
    axes[0, 4].legend(fontsize=7, frameon=False, loc="lower left")
    fig.suptitle("EXP-C01 — PnL net cumulé (somme des bps nets par trade), une position à la fois, sans stop", fontsize=12)
    fig.tight_layout()
    _save(fig, "fig1_courbes_pnl_5_10bps.png")
    plt.close(fig)

    r5 = res[res.frais_bps == 5.0]
    anc = float(r5[r5.configuration == ANCRE].esperance_bps.iloc[0])
    fig, axes = plt.subplots(1, 2, figsize=(14, 5.2), sharey=True)
    groups = [["Tous", "Tous hors R3", f"Tous hors {Q4}", "R1", "R2", "R3", Q4],
              [f"Tous hors R3 et hors {Q4}", f"R1 hors {Q4}", f"R2 hors {Q4}", "R3 en continuation",
               f"{Q4} en continuation", "Tous"]]
    for ax, names, titre in zip(axes, groups, ["Paliers 1 et 2", "Palier 3 (ablation, inversion)"]):
        for name in names:
            g = r5[r5.configuration == name].sort_values("H")
            ax.plot(g.H.astype(int), g.esperance_bps, marker="o", ms=4, color=COLORS[name],
                    ls="--" if "continuation" in name else "-", lw=1.6 if name == "Tous" else 1.3, label=name)
        ax.axhline(0, color="0.3", lw=0.8)
        ax.axhline(5, color="0.3", lw=0.8, ls=":")
        ax.axhline(anc, color="k", lw=0.9, ls="-.")
        ax.text(48, anc, " ancre native", fontsize=7, va="bottom", ha="right")
        ax.text(48, 5, " seuil à 10 bps", fontsize=7, va="bottom", ha="right")
        ax.set_xticks(HORIZONS)
        ax.set_xlabel("Horizon de sortie H (barres de 30 min)", fontsize=9)
        ax.set_title(titre, fontsize=10)
        ax.grid(alpha=0.3, lw=0.5)
        ax.legend(fontsize=7, frameon=False)
    axes[0].set_ylabel("Espérance nette par trade à 5 bps (bps)", fontsize=9)
    fig.suptitle("EXP-C01 — Espérance nette par horizon (à 10 bps : toutes les courbes baissent de 5 bps)", fontsize=11)
    fig.tight_layout()
    _save(fig, "fig2_esperance_par_horizon.png")
    plt.close(fig)

    names = [n for n in dict.fromkeys(r5.configuration) if n != ANCRE]
    fig, axes = plt.subplots(1, 3, figsize=(20, 8.5), sharey=True)
    for ax, (k, titre) in zip(axes, [("long_bps", "Long net (bps)"), ("short_bps", "Short net (bps)"),
                                     ("timing_bps", "Timing net = (Long + Short) / 2 (bps)")]):
        mat = np.array([[r5[(r5.configuration == n) & (r5.H == H)][k].iloc[0] for H in HORIZONS] for n in names])
        lim = np.nanmax(np.abs(mat))
        ax.imshow(mat, cmap="RdBu", vmin=-lim, vmax=lim, aspect="auto")
        for a in range(mat.shape[0]):
            for b in range(mat.shape[1]):
                ax.text(b, a, sg(mat[a, b], 1), ha="center", va="center", fontsize=7)
        ax.set_xticks(range(len(HORIZONS)), [f"H = {H}" for H in HORIZONS], fontsize=8)
        ax.set_title(titre, fontsize=10)
    axes[0].set_yticks(range(len(names)), names, fontsize=8)
    fig.suptitle("EXP-C01 — Long, Short et timing nets par configuration et horizon (5 bps aller-retour)", fontsize=11)
    fig.tight_layout()
    _save(fig, "fig3_long_vs_short_timing.png")
    plt.close(fig)

    a5 = ann[ann.frais_bps == 5.0]
    fig, axes = plt.subplots(1, 4, figsize=(24, 8.5), sharey=True)
    for ax, H in zip(axes, HORIZONS):
        mat = np.array([[a5[(a5.configuration == n) & (a5.H == H) & (a5.annee == y)].esperance_bps.sum()
                         if ((a5.configuration == n) & (a5.H == H) & (a5.annee == y)).any() else np.nan
                         for y in YEARS] for n in names])
        lim = np.nanmax(np.abs(mat))
        ax.imshow(mat, cmap="RdBu", vmin=-lim, vmax=lim, aspect="auto")
        for i in range(mat.shape[0]):
            for j in range(mat.shape[1]):
                ax.text(j, i, sg(mat[i, j], 0), ha="center", va="center", fontsize=7)
        ax.set_xticks(range(len(YEARS)), YEARS, fontsize=8)
        ax.set_title(f"H = {H}", fontsize=10)
    axes[0].set_yticks(range(len(names)), names, fontsize=8)
    fig.suptitle("EXP-C01 — Espérance nette par trade et par année (bps, 5 bps aller-retour)", fontsize=11)
    fig.tight_layout()
    _save(fig, "fig4_stabilite_annuelle_C01.png")
    plt.close(fig)


def main() -> None:
    t0 = time.time()
    df, bars = load_dev_bars(), load_bars_dev()
    if not np.array_equal(df[["open", "high", "low", "close"]].to_numpy(), bars[["open", "high", "low", "close"]].to_numpy()):
        raise SystemExit("barres différentes entre anatomy et estimand : arrêt")
    atlas, f, idx, atr = build_atlas(df)
    ref = pd.read_csv(ROOT / "experiments" / "A01" / "atlas_signaux.csv", usecols=["bar_index", "direction"])
    if not (np.array_equal(ref.bar_index, atlas.bar_index) and np.array_equal(ref.direction, atlas.direction)):
        raise SystemExit("univers différent de experiments/A01/atlas_signaux.csv : arrêt")
    anchor_tr, meta_a = check_anchor(bars, f)
    confs = configurations(regime_masks(atlas), len(atlas))
    atr_bps = pd.Series(atlas.atr14_bps.to_numpy(), index=atlas.bar_index.to_numpy())
    res, ann, trades = run_all(bars, atlas, atr_bps, confs, anchor_tr, meta_a["n_signaux"])
    res.to_csv(HERE / "resultats_C01.csv", index=False, float_format="%.6g")
    ann.to_csv(HERE / "annuel_C01.csv", index=False, float_format="%.6g")
    figures(bars, res, ann, trades)
    meta = {"ancre": meta_a, "gap": exit_gap_bps(bars)}
    parts = [section_controles(meta), section_palier1(res), section_palier2(res), section_palier3(res),
             section_annees(ann)]
    narr = HERE / "narratif_C01.md"
    head = narr.read_text(encoding="utf-8") if narr.exists() else "# EXP-C01\n\n*(narratif à rédiger)*\n"
    (HERE / "rapport_C01.md").write_text(
        head.rstrip() + "\n\n---\n\n# Annexes chiffrées (générées par `run_C01.py`)\n\n" + "\n\n".join(parts) + "\n",
        encoding="utf-8")
    print(f"C01 : {len(res)} lignes de résultats en {time.time() - t0:.0f} s ; rapport, tableaux et figures dans {HERE}")


if __name__ == "__main__":
    main()
