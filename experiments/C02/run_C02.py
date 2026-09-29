"""EXP-C02 — stop-loss en prix par sous-famille, sur l'enveloppe à horizon fixe de C01, en exécution séquentielle.

Usage, depuis la racine du dépôt : python experiments/C02/run_C02.py [--rapport]
  --rapport : régénère seulement rapport_C02.md depuis resultats_C02.csv, annuel_C02.csv et controles_C02.json.
Sorties dans experiments/C02/ : resultats_C02.csv, annuel_C02.csv, controles_C02.json, figures/*.png,
rapport_C02.md (= narratif_C02.md rédigé à la main, suivi des annexes chiffrées générées ici).

OFAT : pour chaque paire (sous-ensemble, H), le contrôle est la même configuration sans stop, identique à C01
(vérifié, bloquant) ; seule la règle de stop change. Ni take-profit ni break-even.
- SL-A : open[t + 1] ∓ k · ATR14(t), k ∈ {1 ; 1,5 ; 2 ; 2,5 ; 3 ; 4 ; 5} ;
- SL-B : extremum du segment qualifiant ∓ delta · ATR14(t), delta ∈ {0 ; 0,25 ; 0,5 ; 1}, plancher 0,25 ATR14(t).
Deux lectures : entrées figées de la course sans stop (effet pur du stop) et séquentiel dynamique (le stop libère la
position). Frais 5 et 10 bps. Capital : 1 ATR14(t) = 0,25 % du capital, levier plafonné à 1x ; notionnel 1x gardé dans
le CSV. IC 95 % : bootstrap de grappes mensuelles, 2 000 tirages, en bps et en ATR14(t).
"""
from __future__ import annotations

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
from categorization import add_derived, assign_families, bin_descriptor  # noqa: E402
from envelope import (atr_stop_levels, by_year, dev_signals, effect_ci, equity_curve_sized, mean_ci,  # noqa: E402
                      risk_weights, segment_extremum, stop_trades, structural_stop_levels, summarize,
                      summarize_sized, time_stop_trades, trade_frame)
from estimand import load_bars_dev  # noqa: E402
from estimand.excursions import BPS  # noqa: E402
from estimand.stoploss import simulate_strategy  # noqa: E402

FIG = HERE / "figures"
FEES = (5.0, 10.0)
YEARS = list(range(2020, 2026))
RISK = 25.0                            # 1 ATR14(t) = 0,25 % du capital, levier plafonné à 1x
N_BOOT = 2000
K_ATR = (1.0, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0)
DELTAS = (0.0, 0.25, 0.5, 1.0)
FLOOR = 0.25
MODES = ("figé", "dynamique")
Q4 = "nis_z_100 Q4"
REF_TRADES = ROOT / "experiments" / "p6_5" / "strategie_stop_trades.csv"
C01_CSV = ROOT / "experiments" / "C01" / "resultats_C01.csv"

R1, F1, F5 = f"R1 hors {Q4}", f"↳ F1 · x1 encore opposé hors {Q4}", f"↳ F5 · x1 encore opposé hors {Q4}"
F2B, F3, R2 = f"↳ F2b · x1 déjà retourné hors {Q4}", f"↳ F3 · x1 déjà retourné hors {Q4}", f"R2 hors {Q4}"
GROUPS = {"R1": {"titre": f"Essoufflement — R1 hors {Q4}", "H": (6, 13, 26), "sous_ensembles": [R1, F1, F5],
                 "H_principal": 13},
          "R2": {"titre": f"Sortie de compression — R2 hors {Q4}", "H": (13, 26, 48), "sous_ensembles": [F2B, F3, R2],
                 "H_principal": 26}}
EXPECTED = {R1: 1592, F1: 962, F5: 630, F2B: 741, F3: 711, R2: 1452}
IN_C01 = (R1, F2B, F3, R2)
STOPS = [("sans", np.nan)] + [("SL-A", k) for k in K_ATR] + [("SL-B", d) for d in DELTAS]


def stop_key(fam: str, p: float) -> str:
    return "sans" if fam == "sans" else f"{fam} {p:g}"


KEYS = [stop_key(f, p) for f, p in STOPS]


# ── Mise en forme ───────────────────────────────────────────────────────────────
def fr(x, nd=2) -> str:
    return "—" if x is None or pd.isna(x) else f"{x:.{nd}f}".replace(".", ",").replace("-", "−")


def sg(x, nd=1) -> str:
    if x is None or pd.isna(x):
        return "—"
    return ("+∞" if x > 0 else "−∞") if np.isinf(x) else f"{x:+.{nd}f}".replace(".", ",").replace("-", "−")


def pct(x, nd=1) -> str:
    return "—" if x is None or pd.isna(x) else fr(100 * x, nd) + " %"


def spct(x, nd=0) -> str:
    return "—" if x is None or pd.isna(x) else sg(100 * x, nd) + " %"


def n_fr(n) -> str:
    return f"{int(n):,}".replace(",", " ")


def sci(x) -> str:
    if x == 0:
        return "0"
    e = int(np.floor(np.log10(abs(x))))
    return f"{fr(x / 10 ** e, 1)}·10{str(e).translate(str.maketrans('-0123456789', '⁻⁰¹²³⁴⁵⁶⁷⁸⁹'))}"


def ci(x, lo, hi, nd) -> str:
    return f"{sg(x, nd)} [{sg(lo, nd)} ; {sg(hi, nd)}]"


def table(header, rows) -> str:
    out = ["| " + " | ".join(header) + " |", "|" + "|".join(["---"] * len(header)) + "|"]
    return "\n".join(out + ["| " + " | ".join(str(c) for c in r) + " |" for r in rows])


def stop_label(key: str) -> str:
    if key == "sans":
        return "Sans stop (contrôle)"
    fam, p = key.split()
    return f"SL-A {fr(float(p), 1)} ATR" if fam == "SL-A" else f"SL-B extremum + {fr(float(p), 2)} ATR"


# ── Univers, sous-ensembles, contrôles bloquants ────────────────────────────────
def subset_masks(atlas: pd.DataFrame) -> dict[str, np.ndarray]:
    """Définitions figées de B01 (RESEARCH_INSIGHTS.md §4) et de C01, recalculées depuis l'atlas."""
    d = add_derived(atlas)
    fam = assign_families(d, float(np.median(d.leg_atr)))
    ref = pd.read_csv(ROOT / "experiments" / "B01" / "excursions_signaux.csv", usecols=["bar_index", "famille"])
    if not (np.array_equal(ref.bar_index, atlas.bar_index) and np.array_equal(ref.famille, fam)):
        raise SystemExit("familles différentes de experiments/B01/excursions_signaux.csv : arrêt")
    x1 = d.x1_already_flipped_at_t.to_numpy(dtype=bool)
    hors_q4 = bin_descriptor(d.nis_z_100, "nis_z_100")[0] != "Q4"
    m = {R1: np.isin(fam, ["F1", "F5"]) & ~x1 & hors_q4, F1: (fam == "F1") & ~x1 & hors_q4,
         F5: (fam == "F5") & ~x1 & hors_q4, F2B: (fam == "F2b") & x1 & hors_q4, F3: (fam == "F3") & x1 & hors_q4,
         R2: np.isin(fam, ["F2b", "F3"]) & x1 & hors_q4}
    bad = {k: int(v.sum()) for k, v in m.items() if int(v.sum()) != EXPECTED[k]}
    if bad:
        raise SystemExit(f"effectifs différents du cadrage : {bad}")
    return m


def check_anchor(bars, f) -> dict:
    """Ancre P6.5d sans stop et stop 2,5 % : trades identiques au fichier de référence (bloquant). La variante à stop
    valide l'exécution des stops par `apply_stop` sur BTC (mèches, gaps)."""
    sig = dev_signals(f)
    ref = pd.read_csv(REF_TRADES)
    out = {}
    for variante, stop, n_ref in [("sans_stop", None, 6037), ("stop_2_5", 0.025, 6589)]:
        tr, _ = simulate_strategy(bars, sig, stop)
        r = ref[ref.variante == variante].reset_index(drop=True)
        same = len(tr) == len(r) == n_ref and all(np.array_equal(tr[c].to_numpy(), r[c].to_numpy()) for c in
                                                  ("entry_bar", "exit_bar", "side", "signal_bar", "stop", "gap"))
        same = same and np.array_equal([float(f"{v:.10g}") for v in tr.ret_gross_bps], r.ret_gross_bps.to_numpy())
        if not same:
            raise SystemExit(f"ancre P6.5d ({variante}) non reproduite : arrêt")
        out[variante] = {"n_trades": len(tr), "n_stops": int(tr.stop.sum()), "n_gaps": int(tr.gap.sum())}
    return out


def check_segment(bars, atlas, atr, masks) -> dict:
    """SL-B : l'extremum du segment est celui de `obs_dist_seg_atr`, donc de `retrace_ratio` (bloquant). Écart avec la
    fenêtre littérale du cadrage, low[t − prev_seg_len + 1 : t + 1], qui omet la première barre du segment qualifiant."""
    t, s, n = (atlas[c].to_numpy() for c in ("bar_index", "direction", "prev_seg_len"))
    close = bars.close.to_numpy()
    ext = segment_extremum(bars, t, s, n)
    err = float(np.max(np.abs(np.abs(close[t] - ext) / atr[t] - atlas.obs_dist_seg_atr.to_numpy())))
    if not err < 1e-9:
        raise SystemExit(f"extremum du segment différent de obs_dist_seg_atr ({err:.3g}) : arrêt")
    lit = segment_extremum(bars, t, s, n - 1)
    diff = ext != lit
    return {"ecart_max_obs_dist_seg_atr": err, "n_signaux": int(len(t)),
            "fenetre_litterale_differe": int(diff.sum()),
            "fenetre_litterale_differe_par_sous_ensemble": {k: int((diff & m).sum()) for k, m in masks.items()},
            "ecart_median_atr_si_differe": float(np.median(np.abs(ext - lit)[diff] / atr[t][diff])) if diff.any()
            else 0.0}


def check_c01(res: pd.DataFrame) -> dict:
    """Les contrôles sans stop reproduisent C01 (bloquant) : mêmes trades, mêmes métriques déterministes."""
    ref = pd.read_csv(C01_CSV)
    ref = ref[ref.H.astype(str) != "native"].copy()
    ref["H"] = ref.H.astype(int)
    cols = ["n_trades", "esperance_bps", "esperance_atr", "pnl_compose", "pf", "wr", "mdd_valorise", "duree_mediane",
            "pnl_compose_r25", "mdd_valorise_r25"]
    ctrl = res[(res.stop == "sans") & (res["mode"] == "dynamique") & res.configuration.isin(IN_C01)]
    worst = 0.0
    for _, r in ctrl.iterrows():
        g = ref[(ref.configuration == r.configuration) & (ref.H == r.H) & (ref.frais_bps == r.frais_bps)]
        if len(g) != 1:
            raise SystemExit(f"contrôle absent de C01 : {r.configuration}, H = {r.H}")
        for c in cols:
            a, b = float(r[c]), float(g[c].iloc[0])
            if not np.isclose(a, b, rtol=1e-5, atol=1e-9):
                raise SystemExit(f"contrôle différent de C01 : {r.configuration}, H = {r.H}, {c} ({a} contre {b})")
            worst = max(worst, abs(a - b) / max(abs(b), 1e-12))
    if len(ctrl) != 24:
        raise SystemExit(f"{len(ctrl)} contrôles comparés à C01 au lieu de 24 : arrêt")
    return {"lignes_comparees": int(len(ctrl)), "colonnes": cols, "ecart_relatif_max": worst}


def atr_by_year(bars, atlas, atr) -> list[dict]:
    """ATR14 médian en bps, par année : toutes les barres, et barres des signaux (remarque du porteur sur le poids de
    2021 dans les IC en bps)."""
    y_bar = bars.time.dt.year.to_numpy()
    a_bar = atr / bars.close.to_numpy() * BPS
    out = []
    for y in YEARS:
        sel = (atlas.year == y).to_numpy()
        out.append({"annee": y, "atr_bps_barres": float(np.nanmedian(a_bar[y_bar == y])),
                    "atr_bps_signaux": float(np.median(atlas.atr14_bps.to_numpy()[sel]))})
    return out


# ── Calcul ──────────────────────────────────────────────────────────────────────
def dist_stats(tr, level: pd.Series, atr) -> dict:
    """Distance entre l'entrée et le stop des trades exécutés, en ATR14(t)."""
    if level.isna().all() or not len(tr):
        return {"distance_p10_atr": np.nan, "distance_p50_atr": np.nan, "distance_p90_atr": np.nan}
    sb = tr.signal_bar.to_numpy()
    d = tr.side.to_numpy() * (tr.entry_price.to_numpy() - level.reindex(sb).to_numpy()) / atr[sb]
    p10, p50, p90 = np.percentile(d, [10, 50, 90])
    return {"distance_p10_atr": float(p10), "distance_p50_atr": float(p50), "distance_p90_atr": float(p90)}


def decomposition(dyn, fig, atr_bps, fee) -> dict:
    """Séquentiel dynamique contre entrées figées : trades débloqués par un stop (absents de la course figée) et trades
    perdus (de la course figée, masqués par un trade débloqué)."""
    new, lost = dyn[~dyn.signal_bar.isin(set(fig.signal_bar))], fig[~fig.signal_bar.isin(set(dyn.signal_bar))]

    def esp(tr):
        if not len(tr):
            return np.nan, np.nan
        net = tr.ret_gross_bps.to_numpy() - fee
        return float(net.mean()), float((net / atr_bps.reindex(tr.signal_bar.to_numpy()).to_numpy()).mean())

    (nb, na), (lb, la) = esp(new), esp(lost)
    return {"n_debloques": len(new), "esperance_debloques_bps": nb, "esperance_debloques_atr": na,
            "n_perdus": len(lost), "esperance_perdus_bps": lb, "esperance_perdus_atr": la}


def annual_rows(tr, bars, atr_bps, fee, base: dict) -> list[dict]:
    y = by_year(tr, bars, atr_bps, fee)
    tf = trade_frame(tr, bars, atr_bps, fee)
    w = risk_weights(atr_bps.reindex(tr.signal_bar.to_numpy()).to_numpy(dtype=float), RISK)
    lg = pd.Series(np.log1p(w * tf.net_bps.to_numpy() / BPS)).groupby(tf.year.to_numpy()).sum()
    y["pnl_compose_r25"] = np.expm1(lg.reindex(y.annee.to_numpy()).to_numpy())
    y["part_stop"] = pd.Series(tr.stop.to_numpy(dtype=float)).groupby(tf.year.to_numpy()).mean() \
        .reindex(y.annee.to_numpy()).to_numpy()
    return [{**base, **r} for r in y.to_dict("records")]


def run_all(bars, atlas, atr, atr_bps, masks):
    op = bars.open.to_numpy(dtype=float)
    t_all, s_all, n_all = (atlas[c].to_numpy() for c in ("bar_index", "direction", "prev_seg_len"))
    res, ann, trades, dists = [], [], {}, []
    for grp, g in GROUPS.items():
        for name in g["sous_ensembles"]:
            m = masks[name]
            t, s, n = t_all[m], s_all[m], n_all[m]
            a = atr[t]                                                     # ATR14(t) en prix
            base_dist = s * (op[t + 1] - segment_extremum(bars, t, s, n)) / a
            for dl in DELTAS:
                dd = np.maximum(base_dist + dl, FLOOR)
                dists.append({"configuration": name, "delta": dl, "p10": float(np.percentile(dd, 10)),
                              "p50": float(np.median(dd)), "p90": float(np.percentile(dd, 90)),
                              "part_plancher": float((base_dist + dl < FLOOR).mean())})
            for H in g["H"]:
                ctrl = stop_trades(bars, t, s, H)
                if not ctrl.equals(time_stop_trades(bars, t, s, H)):
                    raise SystemExit("stop_trades sans stop différent de time_stop_trades : arrêt")
                for fam, p in STOPS:
                    key = stop_key(fam, p)
                    if fam == "sans":
                        level, runs = None, {"figé": ctrl, "dynamique": ctrl}
                    else:
                        level = (atr_stop_levels(bars, t, s, a, p) if fam == "SL-A"
                                 else structural_stop_levels(bars, t, s, a, n, p, FLOOR))
                        runs = {mode: stop_trades(bars, t, s, H, level, dynamic=(mode == "dynamique"))
                                for mode in MODES}
                    eff = effect_ci(runs["figé"], ctrl, bars, atr_bps, N_BOOT)
                    lv = pd.Series(np.nan if level is None else level, index=t, dtype=float)
                    for mode, tr in runs.items():
                        trades[(name, H, key, mode)] = tr
                        info = {"groupe": grp, "configuration": name, "H": H, "stop": key, "famille_stop": fam,
                                "parametre": p, "mode": mode, "part_stop": float(tr.stop.mean()),
                                "part_gap": float(tr.gap.mean()), **dist_stats(tr, lv, atr),
                                **(eff if mode == "figé" else {})}
                        for fee in FEES:
                            row = {**info, "frais_bps": fee,
                                   **summarize(tr, bars, atr_bps, fee, n_candidates=len(t)),
                                   **mean_ci(tr, bars, fee, N_BOOT, atr_bps=atr_bps),
                                   **{f"{k}_r25": v for k, v in summarize_sized(tr, bars, atr_bps, fee, RISK).items()}}
                            if mode == "dynamique":
                                row.update(decomposition(tr, runs["figé"], atr_bps, fee))
                            res.append(row)
                            ann += annual_rows(tr, bars, atr_bps, fee, {k: info[k] for k in (
                                "groupe", "configuration", "H", "stop", "mode")} | {"frais_bps": fee})
            print(f"  {name} : fait")
    res, ann = pd.DataFrame(res), pd.DataFrame(ann)
    cnt = ann.groupby(["configuration", "H", "stop", "mode", "frais_bps"]).agg(
        annees_pnl_pos=("pnl_bps", lambda v: int((v > 0).sum())),
        annees_pnl_r25_pos=("pnl_compose_r25", lambda v: int((v > 0).sum()))).reset_index()
    res = res.merge(cnt, on=["configuration", "H", "stop", "mode", "frais_bps"], how="left")
    ctl = res[res.stop == "sans"].set_index(["configuration", "H", "mode", "frais_bps"])
    for c in ("esperance_bps", "esperance_atr", "pnl_compose_r25", "mdd_valorise_r25"):
        res[f"ecart_controle_{c}"] = [r[c] - ctl.loc[(r.configuration, r.H, r["mode"], r.frais_bps), c]
                                      for _, r in res.iterrows()]
    return res, ann, trades, pd.DataFrame(dists)


# ── Sections du rapport ─────────────────────────────────────────────────────────
class Index:
    def __init__(self, res):
        self.d = {(r["configuration"], int(r["H"]), r["stop"], r["mode"], float(r["frais_bps"])): r
                  for r in res.to_dict("records")}

    def __call__(self, name, H, key, mode, fee=5.0) -> dict:
        return self.d[(name, int(H), key, mode, float(fee))]


def frais_cell(r) -> str:
    brut = sg(r["brut_bps"] / r["n_trades"], 1)
    if r["brut_bps"] <= 0:
        return f"sans objet (brut ≤ 0) ; {brut}"
    return f"{'> 1 000 %' if r['part_frais'] > 10 else pct(r['part_frais'], 0)} ; {brut}"


def section_controles(meta) -> str:
    a, sgm, c = meta["ancre"], meta["segment"], meta["c01"]
    lit = ", ".join(f"{k.replace('↳ ', '')} {v}" for k, v in sgm["fenetre_litterale_differe_par_sous_ensemble"].items())
    rows = [["Ancre P6.5d sans stop", f"{n_fr(a['sans_stop']['n_trades'])} trades identiques au fichier de référence"],
            ["Ancre P6.5d, stop 2,5 % (exécution des stops par `apply_stop` sur BTC)",
             f"{n_fr(a['stop_2_5']['n_trades'])} trades identiques, dont {n_fr(a['stop_2_5']['n_stops'])} stoppés et "
             f"{n_fr(a['stop_2_5']['n_gaps'])} gaps"],
            ["Contrôles sans stop = C01", f"{c['lignes_comparees']} lignes (4 sous-ensembles communs × 3 horizons × 2 "
             f"frais) ; écart relatif max {sci(c['ecart_relatif_max'])} (arrondi du CSV de C01)"],
            ["`stop_trades` sans stop = `time_stop_trades`", "identiques pour les 18 paires (sous-ensemble, H)"],
            ["Extremum de SL-B = extremum de `obs_dist_seg_atr` (horizon [t − prev_seg_len, t])",
             f"écart max {sci(sgm['ecart_max_obs_dist_seg_atr'])} ATR sur {n_fr(sgm['n_signaux'])} signaux"],
            ["Fenêtre littérale du cadrage [t − prev_seg_len + 1, t]",
             f"extremum différent pour {n_fr(sgm['fenetre_litterale_differe'])} signaux sur "
             f"{n_fr(sgm['n_signaux'])} (écart médian {fr(sgm['ecart_median_atr_si_differe'], 2)} ATR) ; par "
             f"sous-ensemble : {lit}"],
            ["IC 95 %", f"bootstrap de grappes (mois civils d'entrée), {n_fr(N_BOOT)} tirages, graine 0"],
            ["Capital", "1 ATR14(t) = 0,25 % du capital, levier plafonné à 1x, frais proportionnels au notionnel ; "
             "notionnel 1x dans le CSV"],
            ["Période", "2020-01 → 2025-12 (72 mois) ; aucune barre de 2026 lue"]]
    return "## A. Contrôles bloquants et conventions\n\n" + table(["Contrôle", "Résultat"], rows)


def section_distances(dist) -> str:
    rows = []
    for name in dist.configuration.unique():
        g = dist[dist.configuration == name]
        rows.append([name] + [f"{fr(r.p50, 2)} [{fr(r.p10, 2)} ; {fr(r.p90, 2)}] ; {pct(r.part_plancher, 0)}"
                              for r in g.itertuples()])
    return ("## B. Distance entre l'entrée et le stop SL-B, en ATR14(t)\n\n"
            "Tous les signaux candidats. Cellule : médiane [P10 ; P90] ; part des signaux où le plancher de "
            f"{fr(FLOOR, 2)} ATR s'applique. SL-A : distance fixe k.\n\n"
            + table(["Sous-ensemble"] + [f"SL-B extremum + {fr(d, 2)} ATR" for d in DELTAS], rows))


def section_remarque(ix, meta) -> str:
    rows = []
    for g in GROUPS.values():
        for name in g["sous_ensembles"]:
            for H in g["H"]:
                cells = []
                for fee in FEES:
                    r = ix(name, H, "sans", "dynamique", fee)
                    cells += [ci(r["esperance_bps"], r["esperance_bps_lo"], r["esperance_bps_hi"], 1),
                              ci(r["esperance_atr"], r["esperance_atr_lo"], r["esperance_atr_hi"], 3)]
                r = ix(name, H, "sans", "dynamique", 5.0)
                rows.append([name, f"H = {H}", n_fr(r["n_trades"])] + cells
                            + [ci(r["timing_atr"], r["timing_atr_lo"], r["timing_atr_hi"], 3)])
    atr = meta["atr_annuel"]
    return ("## C. Contrôles sans stop : IC 95 % en bps et en ATR14(t)\n\n"
            + table(["Sous-ensemble", "H", "Trades", "5 bps : espérance bps [IC]", "5 bps : espérance ATR [IC]",
                     "10 bps : espérance bps [IC]", "10 bps : espérance ATR [IC]", "5 bps : timing ATR [IC]"], rows)
            + "\n\n**ATR14 médian (bps), par année**\n\n"
            + table(["Mesure"] + [str(a["annee"]) for a in atr],
                    [["Toutes les barres"] + [fr(a["atr_bps_barres"], 1) for a in atr],
                     ["Barres des 7 296 signaux"] + [fr(a["atr_bps_signaux"], 1) for a in atr]]))


HEAD5 = ["Stop", "Stoppés : figé ; dyn.", "Effet pur, entrées figées : ATR [IC 95 %]", "Figé : espérance ATR [IC]",
         "Dyn. : PnL composé ; MDD valorisé", "Dyn. : PF 1x ; PF pondéré ; WR", "Dyn. : espérance bps [IC] ; ATR [IC]",
         "Dyn. : timing ATR [IC]", "Dyn. : trades ; /mois ; débloqués", "Dyn. : durée méd.",
         "Dyn. : part des frais ; brut/trade"]
HEAD10 = ["Stop", "Figé : espérance ATR [IC]", "Dyn. : PnL composé ; MDD valorisé", "Dyn. : PF 1x ; PF pondéré ; WR",
          "Dyn. : espérance bps [IC] ; ATR [IC]", "Dyn. : timing ATR [IC]", "Dyn. : part des frais ; brut/trade"]


def _dyn_cells(r) -> list:
    return [f"{spct(r['pnl_compose_r25'])} ; {pct(r['mdd_valorise_r25'], 0)}",
            f"{fr(r['pf'], 2)} ; {fr(r['pf_r25'], 2)} ; {pct(r['wr'], 0)}",
            f"{ci(r['esperance_bps'], r['esperance_bps_lo'], r['esperance_bps_hi'], 1)} ; "
            f"{ci(r['esperance_atr'], r['esperance_atr_lo'], r['esperance_atr_hi'], 3)}",
            ci(r["timing_atr"], r["timing_atr_lo"], r["timing_atr_hi"], 3)]


def section_profils(ix) -> str:
    out = ["## D. Profils des stops, par sous-ensemble et horizon",
           "Espérance, timing et effet : nets, par trade, en ATR14(t) ou en bps. PnL composé et MDD valorisé : capital "
           "à 0,25 % par ATR. PF 1x : gains / pertes des trades en bps nets ; PF pondéré : des PnL à 0,25 % par ATR. "
           "Effet pur : moyenne appariée (stop − sans stop) sur les entrées de la course sans stop, identique à 5 et "
           "10 bps. Débloqués : trades du séquentiel dynamique absents de la course figée."]
    for g in GROUPS.values():
        out.append(f"### {g['titre']}")
        for name in g["sous_ensembles"]:
            for H in g["H"]:
                rows5, rows10 = [], []
                for key in KEYS:
                    f5, d5 = ix(name, H, key, "figé"), ix(name, H, key, "dynamique")
                    rows5.append([stop_label(key), f"{pct(f5['part_stop'], 0)} ; {pct(d5['part_stop'], 0)}",
                                  "—" if key == "sans" else ci(f5["effet_atr"], f5["effet_atr_lo"], f5["effet_atr_hi"], 3),
                                  ci(f5["esperance_atr"], f5["esperance_atr_lo"], f5["esperance_atr_hi"], 3)]
                                 + _dyn_cells(d5)
                                 + [f"{n_fr(d5['n_trades'])} ; {fr(d5['trades_par_mois'], 1)} ; "
                                    f"{n_fr(d5['n_debloques'])}", fr(d5["duree_mediane"], 0), frais_cell(d5)])
                    f10, d10 = ix(name, H, key, "figé", 10.0), ix(name, H, key, "dynamique", 10.0)
                    rows10.append([stop_label(key), ci(f10["esperance_atr"], f10["esperance_atr_lo"],
                                                       f10["esperance_atr_hi"], 3)] + _dyn_cells(d10) + [frais_cell(d10)])
                out.append(f"#### {name} — H = {H}\n\n**5 bps aller-retour**\n\n" + table(HEAD5, rows5)
                           + "\n\n**10 bps aller-retour**\n\n" + table(HEAD10, rows10))
    return "\n\n".join(out)


def section_reouverture(ix) -> str:
    out = ["## E. Entrées figées contre séquentiel dynamique (5 bps, horizon principal du groupe)",
           "Débloqués : trades ouverts grâce à un stop, absents de la course figée. Perdus : trades de la course figée "
           "masqués par un trade débloqué. Espérances nettes en ATR14(t)."]
    for g in GROUPS.values():
        H = g["H_principal"]
        for name in g["sous_ensembles"]:
            rows = []
            for key in KEYS[1:]:
                f5, d5 = ix(name, H, key, "figé"), ix(name, H, key, "dynamique")
                rows.append([stop_label(key), n_fr(f5["n_trades"]), n_fr(d5["n_trades"]),
                             f"{n_fr(d5['n_debloques'])} ; {sg(d5['esperance_debloques_atr'], 3)}",
                             f"{n_fr(d5['n_perdus'])} ; {sg(d5['esperance_perdus_atr'], 3)}",
                             sg(f5["esperance_atr"], 3), sg(d5["esperance_atr"], 3),
                             f"{spct(f5['pnl_compose_r25'])} ; {pct(f5['mdd_valorise_r25'], 0)}",
                             f"{spct(d5['pnl_compose_r25'])} ; {pct(d5['mdd_valorise_r25'], 0)}"])
            out.append(f"### {name} — H = {H}\n\n" + table(
                ["Stop", "Trades figés", "Trades dyn.", "Débloqués : n ; esp. ATR", "Perdus : n ; esp. ATR",
                 "Esp. ATR figé", "Esp. ATR dyn.", "Figé : PnL ; MDD", "Dyn. : PnL ; MDD"], rows))
    return "\n\n".join(out)


def section_annees(ann) -> str:
    out = ["## F. Stabilité annuelle (séquentiel dynamique, 5 bps, horizon principal du groupe)",
           "Cellule : espérance nette par trade en ATR14(t) (trades). Dernière colonne : années à PnL > 0 à 0,25 % "
           "par ATR."]
    a5 = ann[(ann["mode"] == "dynamique") & (ann.frais_bps == 5.0)]
    for g in GROUPS.values():
        H = g["H_principal"]
        for name in g["sous_ensembles"]:
            rows = []
            for key in KEYS:
                gg = a5[(a5.configuration == name) & (a5.H == H) & (a5.stop == key)].set_index("annee")
                rows.append([stop_label(key)] + [f"{sg(gg.esperance_atr.get(y), 2)} ({n_fr(gg.n_trades.get(y, 0))})"
                                                 for y in YEARS] + [f"{int((gg.pnl_compose_r25 > 0).sum())}/6"])
            out.append(f"### {name} — H = {H}\n\n" + table(["Stop"] + [str(y) for y in YEARS] + ["Années > 0"], rows))
    return "\n\n".join(out)


def write_report(res, ann, meta) -> None:
    ix = Index(res)
    dist = pd.DataFrame(meta["distances"])
    parts = [section_controles(meta), section_distances(dist), section_remarque(ix, meta), section_profils(ix),
             section_reouverture(ix), section_annees(ann)]
    narr = HERE / "narratif_C02.md"
    head = narr.read_text(encoding="utf-8") if narr.exists() else "# EXP-C02\n\n*(narratif à rédiger)*\n"
    (HERE / "rapport_C02.md").write_text(
        head.rstrip() + "\n\n---\n\n# Annexes chiffrées (générées par `run_C02.py`)\n\n" + "\n\n".join(parts) + "\n",
        encoding="utf-8")


# ── Figures ─────────────────────────────────────────────────────────────────────
X_ORDER = [stop_key("SL-A", k) for k in K_ATR] + ["sans"] + [stop_key("SL-B", d) for d in DELTAS]
X_LAB = [fr(k, 1) for k in K_ATR] + ["sans\nstop"] + [f"+{fr(d, 2)}" for d in DELTAS]
H_COLORS = {6: "#9ecae1", 13: "#4292c6", 26: "#08519c", 48: "#08306b"}


def _save(fig, name: str) -> None:
    for k in range(6):
        try:
            fig.savefig(FIG / name, dpi=130)
            return
        except OSError:
            if k == 5:
                raise
            time.sleep(0.5)


def fig_profile(ix, grp, fname) -> None:
    g = GROUPS[grp]
    fig, axes = plt.subplots(2, 3, figsize=(20, 9.5), sharex=True)
    x = np.arange(len(X_ORDER), dtype=float)
    for j, name in enumerate(g["sous_ensembles"]):
        for i, H in enumerate(g["H"]):
            off = (i - 1) * 0.18
            col = H_COLORS[H]
            dyn = [ix(name, H, k, "dynamique") for k in X_ORDER]
            fig_ = [ix(name, H, k, "figé") for k in X_ORDER]
            y = np.array([r["esperance_atr"] for r in dyn])
            lo = np.array([r["esperance_atr_lo"] for r in dyn])
            hi = np.array([r["esperance_atr_hi"] for r in dyn])
            ax = axes[0, j]
            ax.errorbar(x + off, y, yerr=[np.maximum(y - lo, 0), np.maximum(hi - y, 0)], color=col, marker="o",
                        ms=4, lw=1.4, capsize=2, elinewidth=0.8, label=f"H = {H}, dynamique")
            ax.plot(x + off, [r["esperance_atr"] for r in fig_], color=col, ls="--", lw=1.0, marker="x", ms=4,
                    label=f"H = {H}, entrées figées")
            ax = axes[1, j]
            ax.plot(x + off, [100 * r["mdd_valorise_r25"] for r in dyn], color=col, marker="o", ms=4, lw=1.4,
                    label=f"H = {H}, dynamique")
            ax.plot(x + off, [100 * r["mdd_valorise_r25"] for r in fig_], color=col, ls="--", lw=1.0, marker="x",
                    ms=4, label=f"H = {H}, entrées figées")
        axes[0, j].set_title(name, fontsize=10)
    for ax in axes.flat:
        ax.axvline(len(K_ATR) + 0.5, color="0.5", lw=0.8, ls=":")
        ax.grid(alpha=0.3, lw=0.5)
        ax.tick_params(labelsize=8)
        ax.set_xticks(np.arange(len(X_ORDER)), X_LAB)
    for ax in axes[0]:
        ax.axhline(0, color="0.3", lw=0.8)
    for ax in axes[1]:
        ax.set_xlabel("SL-A : k (ATR14)            |            SL-B : marge sous / sur l'extremum (ATR14)", fontsize=8)
    axes[0, 0].set_ylabel("Espérance nette par trade, 5 bps (ATR14(t)) — IC 95 %", fontsize=9)
    axes[1, 0].set_ylabel("Max drawdown valorisé, 0,25 % par ATR, 5 bps (%)", fontsize=9)
    axes[0, 0].legend(fontsize=7, frameon=False, ncol=2)
    fig.suptitle(f"EXP-C02 — Profil des stops : {g['titre']} (trait plein : séquentiel dynamique ; tirets : entrées "
                 "figées)", fontsize=11)
    fig.tight_layout()
    _save(fig, fname)
    plt.close(fig)


EQ_KEYS = ["sans", "SL-A 1", "SL-A 2", "SL-A 3", "SL-A 5", "SL-B 0", "SL-B 0.5"]
EQ_STYLE = {"sans": ("#000000", "-", 1.8), "SL-A 1": ("#c6dbef", "-", 1.1), "SL-A 2": ("#6baed6", "-", 1.1),
            "SL-A 3": ("#2171b5", "-", 1.1), "SL-A 5": ("#08306b", "-", 1.1), "SL-B 0": ("#fd8d3c", "--", 1.2),
            "SL-B 0.5": ("#a63603", "--", 1.2)}


def fig_equity(bars, trades, atr_bps) -> None:
    fig, axes = plt.subplots(2, 3, figsize=(20, 9.5), sharex=True)
    for i, g in enumerate(GROUPS.values()):
        H = g["H_principal"]
        for j, name in enumerate(g["sous_ensembles"]):
            ax = axes[i, j]
            for key in EQ_KEYS:
                tr = trades[(name, H, key, "dynamique")]
                w = risk_weights(atr_bps.reindex(tr.signal_bar.to_numpy()).to_numpy(dtype=float), RISK)
                eq = equity_curve_sized(bars, tr, 5.0, w)
                c, ls, lw = EQ_STYLE[key]
                ax.plot(eq.index, 100 * (eq.to_numpy() - 1), color=c, ls=ls, lw=lw, label=stop_label(key))
            ax.axhline(0, color="0.4", lw=0.7)
            ax.set_title(f"{name} — H = {H}", fontsize=10)
            ax.grid(alpha=0.3, lw=0.5)
            ax.tick_params(labelsize=8)
        axes[i, 0].set_ylabel("PnL net composé (%)", fontsize=9)
    axes[0, 0].legend(fontsize=7, frameon=False)
    fig.suptitle("EXP-C02 — Courbes de capital, 1 ATR14(t) = 0,25 % du capital, 5 bps, séquentiel dynamique",
                 fontsize=11)
    fig.tight_layout()
    _save(fig, "fig3_courbes_equite_025atr.png")
    plt.close(fig)


def fig_years(ann) -> None:
    a5 = ann[(ann["mode"] == "dynamique") & (ann.frais_bps == 5.0)]
    fig, axes = plt.subplots(2, 3, figsize=(20, 11))
    for i, g in enumerate(GROUPS.values()):
        H = g["H_principal"]
        for j, name in enumerate(g["sous_ensembles"]):
            ax = axes[i, j]
            mat = np.full((len(KEYS), len(YEARS)), np.nan)
            for a, key in enumerate(KEYS):
                gg = a5[(a5.configuration == name) & (a5.H == H) & (a5.stop == key)].set_index("annee")
                for b, y in enumerate(YEARS):
                    if y in gg.index:
                        mat[a, b] = gg.esperance_atr.loc[y]
            lim = np.nanmax(np.abs(mat))
            ax.imshow(mat, cmap="RdBu", vmin=-lim, vmax=lim, aspect="auto")
            for a in range(mat.shape[0]):
                for b in range(mat.shape[1]):
                    ax.text(b, a, sg(mat[a, b], 2), ha="center", va="center", fontsize=7)
            ax.set_xticks(range(len(YEARS)), YEARS, fontsize=8)
            ax.set_yticks(range(len(KEYS)), [stop_label(k) for k in KEYS], fontsize=7)
            ax.set_title(f"{name} — H = {H}", fontsize=9)
    fig.suptitle("EXP-C02 — Espérance nette par trade et par année (ATR14(t), 5 bps, séquentiel dynamique)", fontsize=11)
    fig.tight_layout()
    _save(fig, "fig4_stabilite_annuelle_C02.png")
    plt.close(fig)


# ── Programme ───────────────────────────────────────────────────────────────────
def main() -> None:
    if "--rapport" in sys.argv:
        res, ann = pd.read_csv(HERE / "resultats_C02.csv"), pd.read_csv(HERE / "annuel_C02.csv")
        write_report(res, ann, json.loads((HERE / "controles_C02.json").read_text(encoding="utf-8")))
        print(f"rapport_C02.md régénéré dans {HERE}")
        return
    t0 = time.time()
    df, bars = load_dev_bars(), load_bars_dev()
    if not np.array_equal(df[["open", "high", "low", "close"]].to_numpy(), bars[["open", "high", "low", "close"]].to_numpy()):
        raise SystemExit("barres différentes entre anatomy et estimand : arrêt")
    atlas, f, idx, atr = build_atlas(df)
    ref = pd.read_csv(ROOT / "experiments" / "A01" / "atlas_signaux.csv", usecols=["bar_index", "direction"])
    if not (np.array_equal(ref.bar_index, atlas.bar_index) and np.array_equal(ref.direction, atlas.direction)):
        raise SystemExit("univers différent de experiments/A01/atlas_signaux.csv : arrêt")
    meta = {"ancre": check_anchor(bars, f)}
    masks = subset_masks(atlas)
    meta["segment"] = check_segment(bars, atlas, atr, masks)
    atr_bps = pd.Series(atlas.atr14_bps.to_numpy(), index=atlas.bar_index.to_numpy())
    print(f"contrôles bloquants passés ({time.time() - t0:.0f} s) ; calcul des {len(KEYS)} règles de stop")
    res, ann, trades, dist = run_all(bars, atlas, atr, atr_bps, masks)
    meta["c01"] = check_c01(res)
    meta["distances"] = dist.to_dict("records")
    meta["atr_annuel"] = atr_by_year(bars, atlas, atr)
    meta["duree_s"] = round(time.time() - t0)
    res.to_csv(HERE / "resultats_C02.csv", index=False, float_format="%.6g")
    ann.to_csv(HERE / "annuel_C02.csv", index=False, float_format="%.6g")
    (HERE / "controles_C02.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
    FIG.mkdir(parents=True, exist_ok=True)
    ix = Index(res)
    fig_profile(ix, "R1", "fig1_profil_stops_R1_F1_F5.png")
    fig_profile(ix, "R2", "fig2_profil_stops_R2_F2b_F3.png")
    fig_equity(bars, trades, atr_bps)
    fig_years(ann)
    write_report(res, ann, meta)
    print(f"C02 : {len(res)} lignes de résultats en {meta['duree_s']} s ; rapport, tableaux et figures dans {HERE}")


if __name__ == "__main__":
    main()
