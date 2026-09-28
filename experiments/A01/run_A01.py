"""EXP-A01 — Anatomie et distribution du signal brut AKF-TSO v2.1 (Étape A, descriptive ; aucune transaction simulée).

Usage, depuis la racine du dépôt : python experiments/A01/run_A01.py
Sorties dans experiments/A01/ : atlas_signaux.csv, profils_medians.csv, spearman_causales.csv, figures/*.png,
rapport_A01.md (= narratif_A01.md rédigé à la main, suivi des annexes chiffrées générées ici).
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "src"))

import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from anatomy import TAUS, build_atlas, event_profiles, load_dev_bars  # noqa: E402

FIG = HERE / "figures"
C_LONG, C_SHORT = "#1f5fa8", "#d9822b"
C_RANK1, C_REP = "#1f5fa8", "#d9822b"

#: (colonne, libellé, décimales)
VARS = [
    ("post_lag_bars", "`post_lag_bars` : retard à l'extremum (barres)", 1),
    ("post_dist_atr", "`post_dist_atr` : distance à l'extremum (ATR)", 2),
    ("post_lag_filter_bars", "`post_lag_filter_bars` : extremum → x1 = 0 (barres)", 1),
    ("post_lag_osc_bars", "`post_lag_osc_bars` : x1 = 0 → signal (barres)", 1),
    ("obs_lag_seg_bars", "`obs_lag_seg_bars` (barres)", 1),
    ("obs_dist_seg_atr", "`obs_dist_seg_atr` (ATR)", 2),
    ("obs_lag_cycle_bars", "`obs_lag_cycle_bars` (barres)", 1),
    ("obs_dist_cycle_atr", "`obs_dist_cycle_atr` (ATR)", 2),
    ("prev_seg_len", "`prev_seg_len` (barres)", 1),
    ("prev_seg_extreme_abs", "`prev_seg_extreme_abs`", 1),
    ("saturation", "`saturation` : part du segment à \\|ts\\| ≥ 99,9", 2),
    ("leg_atr", "`leg_atr` : amplitude du segment (ATR)", 2),
    ("peak_bps_vol", "`peak_bps_vol`", 2),
    ("nis_z_100", "`nis_z_100` au signal", 2),
    ("nis_z_100_seg_max", "`nis_z_100_seg_max`", 2),
    ("A_vol", "`A_vol`", 2),
    ("log_R_rel", "`log_R_rel`", 3),
    ("n_short_seg_48", "`n_short_seg_48`", 1),
    ("gap_prev_any_bars", "`gap_prev_any_bars`", 1),
    ("gap_prev_same_bars", "`gap_prev_same_bars`", 1),
    ("gap_prev_opp_bars", "`gap_prev_opp_bars`", 1),
    ("atr14_bps", "`atr14_bps` : ATR14 au signal (bps)", 1),
]
DEC = {c: nd for c, _, nd in VARS}
CAUSAL = ["obs_lag_seg_bars", "obs_dist_seg_atr", "obs_lag_cycle_bars", "obs_dist_cycle_atr", "x1_already_flipped_at_t",
          "prev_seg_len", "prev_seg_extreme_abs", "saturation", "leg_atr", "peak_bps_vol", "nis_z_100",
          "nis_z_100_seg_max", "A_vol", "log_R_rel", "n_short_seg_48", "gap_prev_any_bars", "gap_prev_same_bars",
          "gap_prev_opp_bars", "atr14_bps"]
BY_YEAR = ["post_lag_bars", "post_dist_atr", "obs_dist_seg_atr", "obs_dist_cycle_atr", "prev_seg_len", "saturation",
           "leg_atr", "nis_z_100", "A_vol", "gap_prev_any_bars", "atr14_bps"]
PROFILE_TAUS = [-48, -24, -12, -6, -3, 0, 3, 6, 12, 24, 48]


# ── Mise en forme ───────────────────────────────────────────────────────────────
def fr(x, nd=2) -> str:
    if x is None or pd.isna(x):
        return "—"
    return f"{x:.{nd}f}".replace(".", ",").replace("-", "−")


def pct(x) -> str:
    return fr(100 * x, 1) + " %"


def n_fr(n) -> str:
    return f"{int(n):,}".replace(",", " ")


def iqr(s: pd.Series, nd: int) -> str:
    s = s.dropna()
    if not len(s):
        return "—"
    q = s.quantile([0.25, 0.5, 0.75])
    return f"{fr(q[0.5], nd)} [{fr(q[0.25], nd)} ; {fr(q[0.75], nd)}]"


def table(header, rows) -> str:
    out = ["| " + " | ".join(header) + " |", "|" + "|".join(["---"] * len(header)) + "|"]
    return "\n".join(out + ["| " + " | ".join(r) + " |" for r in rows])


def groups(a: pd.DataFrame) -> dict[str, np.ndarray]:
    return {"Tous": np.ones(len(a), dtype=bool), "Long": (a.direction == 1).to_numpy(),
            "Short": (a.direction == -1).to_numpy(), "Rang 1 (flip)": (a.run_rank == 1).to_numpy(),
            "Répétition": (a.run_rank > 1).to_numpy()}


# ── Tables ──────────────────────────────────────────────────────────────────────
def section_univers(a, f, n_raw) -> str:
    months = (a.timestamp.iloc[-1] - a.timestamp.iloc[0]).days / 30.4375
    rows = [["Barres 30 min lues", f"{n_fr(len(f))} ({f.time.iloc[0]:%Y-%m-%d %H:%M} → {f.time.iloc[-1]:%Y-%m-%d %H:%M} UTC)"],
            ["Signaux bruts valides 2020-2025 (`valid_features`)", n_fr(n_raw)],
            ["Exclus : sortie native en 2026 (convention D43)", n_fr(n_raw - len(a))],
            ["**Univers A01**", f"**{n_fr(len(a))}**"],
            ["Rang 1 (`is_flip`, changement de position)", f"{n_fr(a.is_flip.sum())} ({pct(a.is_flip.mean())})"],
            ["Répétitions de même sens (`run_rank > 1`)", f"{n_fr((a.run_rank > 1).sum())} ({pct((a.run_rank > 1).mean())})"],
            ["Long / Short", f"{n_fr((a.direction == 1).sum())} / {n_fr((a.direction == -1).sum())}"],
            ["Cadence", f"{fr(len(a) / months, 1)} signaux/mois, dont {fr(a.is_flip.sum() / months, 1)} flips/mois"],
            ["Signaux en warm-up (`is_warmup`)", n_fr(a.is_warmup.sum())],
            ["Rang maximal d'une série de même sens", n_fr(a.run_rank.max())]]
    y = a.groupby("year")
    yrows = [[str(k), n_fr(len(g)), pct((g.direction == 1).mean()), pct(g.is_flip.mean()), fr(len(g) / 12, 1)]
             for k, g in y]
    return ("## A. Univers et ancres\n\n" + table(["Élément", "Valeur"], rows) + "\n\n"
            + table(["Année", "Signaux", "Part Long", "Part rang 1", "Signaux/mois"], yrows)
            + "\n\n2020 démarre le 13 janvier (warm-up 30 min et 1 h) : sa cadence mensuelle est sous-estimée d'environ 3 %.")


def section_taux(a) -> str:
    g = groups(a)
    c = a.post_x1_crossed_zero.to_numpy()
    ind = [("Extremum encore à venir au signal (`post_lag_bars` < 0)", a.post_lag_bars.to_numpy() < 0),
           ("Extremum exactement au signal (`post_lag_bars` = 0)", a.post_lag_bars.to_numpy() == 0),
           ("Extremum en bord droit, censuré (`post_is_right_censored`)", a.post_is_right_censored.to_numpy()),
           ("x1 ne franchit pas zéro dans la fenêtre (`post_x1_crossed_zero` = False)", ~c),
           ("x1 déjà du sens du signal à t (`x1_already_flipped_at_t`)", a.x1_already_flipped_at_t.to_numpy()),
           ("x1 déjà du sens du signal à l'extremum (`post_lag_filter_bars` = 0)", a.post_lag_filter_bars.to_numpy() == 0)]
    rows = [[lab] + [pct(v[m].mean()) for m in g.values()] for lab, v in ind]
    osc_neg = (a.post_lag_osc_bars.to_numpy() < 0)
    rows.append(["Parmi les franchissements : signal avant x1 = 0 (`post_lag_osc_bars` < 0)"]
                + [pct(osc_neg[m & c].mean()) for m in g.values()])
    return "## B. Taux\n\n" + table(["Indicateur"] + list(g), rows)


def section_quantiles(a) -> str:
    qs = [0.1, 0.25, 0.5, 0.75, 0.9]
    rows = []
    for c, lab, nd in VARS:
        s = a[c].dropna()
        rows.append([lab, n_fr(len(s))] + [fr(v, nd) for v in s.quantile(qs)])
    return ("## C. Quantiles, tous signaux\n\n" + table(["Variable", "n", "P10", "P25", "P50", "P75", "P90"], rows))


def section_retard_sens(a) -> str:
    lag = a.post_lag_bars
    rows = []
    for lab, m in [("Extremum passé (`post_lag_bars` > 0) : mouvement déjà consommé", lag > 0),
                   ("Extremum au signal (`post_lag_bars` = 0)", lag == 0),
                   ("Extremum à venir (`post_lag_bars` < 0) : mouvement adverse restant", lag < 0)]:
        rows.append([lab, f"{n_fr(m.sum())} ({pct(m.mean())})", iqr(lag[m], 1), iqr(a.post_dist_atr[m], 2),
                     pct(a.post_is_right_censored[m].mean())])
    return ("## C bis. Retard à l'extremum selon son sens\n\n"
            + table(["Cas", "Signaux", "`post_lag_bars`", "`post_dist_atr`", "Censure"], rows))


def section_groupes(a) -> str:
    g = groups(a)
    del g["Tous"]
    rows = [[lab] + [iqr(a.loc[m, c], nd) for m in g.values()] for c, lab, nd in VARS]
    return "## D. Médiane [P25 ; P75] par sens et par type\n\n" + table(["Variable"] + list(g), rows)


def section_annees(a) -> str:
    years = sorted(a.year.unique())
    lab = {c: l for c, l, _ in VARS}
    rows = [[lab[c]] + [iqr(a.loc[a.year == y, c], DEC[c]) for y in years] for c in BY_YEAR]
    return "## E. Médiane [P25 ; P75] par année\n\n" + table(["Variable"] + [str(y) for y in years], rows)


def profile_groups(a) -> dict[str, np.ndarray]:
    r1, dirs = (a.run_rank == 1).to_numpy(), a.direction.to_numpy()
    return {"Rang 1 Long": r1 & (dirs == 1), "Rang 1 Short": r1 & (dirs == -1),
            "Répétition Long": ~r1 & (dirs == 1), "Répétition Short": ~r1 & (dirs == -1),
            "Rang 1": r1, "Répétition": ~r1}


def section_profils(a, prof) -> tuple[str, pd.DataFrame]:
    pg = profile_groups(a)
    recs = []
    for gname, m in pg.items():
        for var, P in prof.items():
            q1, med, q3 = np.nanpercentile(P[m], [25, 50, 75], axis=0)
            for k, tau in enumerate(TAUS):
                recs.append({"groupe": gname, "variable": var, "tau": int(tau), "n": int(m.sum()),
                             "p25": q1[k], "median": med[k], "p75": q3[k]})
    pm = pd.DataFrame(recs)
    out = []
    for var, titre, nd in [("price_atr", "Excursion signée du close, en ATR14(t)", 2),
                           ("ts_oriented", "`trend_strength` orienté (d · ts)", 1),
                           ("x1_atr_oriented", "Vitesse x1 orientée, en ATR14(t) par barre", 3),
                           ("nis_z_100", "`nis_z_100`", 2)]:
        gl = [k for k in pg if var == "price_atr" or k in ("Rang 1", "Répétition")]
        rows = []
        for tau in PROFILE_TAUS:
            cells = []
            for gname in gl:
                r = pm[(pm.groupe == gname) & (pm.variable == var) & (pm.tau == tau)].iloc[0]
                cells.append(f"{fr(r['median'], nd)} [{fr(r.p25, nd)} ; {fr(r.p75, nd)}]")
            rows.append([f"τ = {tau:+d}".replace("-", "−")] + cells)
        out.append(f"### {titre}\n\n" + table(["τ (barres)"] + gl, rows))
    return ("## F. Profils autour du signal : médiane [P25 ; P75]\n\n" + "\n\n".join(out)), pm


def section_spearman(a) -> tuple[str, pd.DataFrame]:
    x = a[CAUSAL].astype(float)
    rho = x.corr(method="spearman")
    pairs = []
    for i, c1 in enumerate(CAUSAL):
        for c2 in CAUSAL[i + 1:]:
            v = rho.loc[c1, c2]
            if pd.notna(v) and abs(v) >= 0.5:
                pairs.append((abs(v), c1, c2, v))
    pairs.sort(reverse=True)
    rows = [[f"`{c1}`", f"`{c2}`", fr(v, 2)] for _, c1, c2, v in pairs]
    const = [c for c in CAUSAL if x[c].nunique() <= 1]
    txt = ("## G. Corrélations de Spearman entre variables causales\n\nMatrice complète : `spearman_causales.csv`, "
           "figure `fig4_spearman.png`. Paires avec \\|ρ\\| ≥ 0,5 :\n\n" + table(["Variable", "Variable", "ρ"], rows))
    if const:
        txt += "\n\nVariables constantes sur l'univers (ρ indéfini) : " + ", ".join(f"`{c}`" for c in const) + "."
    return txt, rho


def section_relecture(a, f, idx, atr, prof) -> str:
    """Contrôles de relecture du 2026-09-28 : tenue de l'extremum du segment, mécanisme du déclencheur,
    divergence de cycle, répétitions, incertitude des médianes de profil."""
    sig = f.signal.to_numpy().astype(int)
    n = len(sig)
    low, high, close = (f[c].to_numpy(dtype=float) for c in ("low", "high", "close"))
    all_sig = np.flatnonzero(sig != 0)
    mae, horizon = [], []
    for t in idx:
        k = np.searchsorted(all_sig, t + 1)
        e = int(all_sig[k]) if k < len(all_sig) else n - 1
        w = slice(t + 1, e + 1)
        adv = close[t] - low[w].min() if sig[t] == 1 else high[w].max() - close[t]
        mae.append(adv / atr[t])
        horizon.append(e - t)
    mae, horizon = np.array(mae), np.array(horizon)
    broken = mae > a.obs_dist_seg_atr.to_numpy()
    identity = np.array_equal(broken, a.post_lag_bars.to_numpy() < 0)
    g = groups(a)
    rows = [["Extremum du segment cassé avant le signal suivant (MAE > `obs_dist_seg_atr`)"]
            + [pct(broken[m].mean()) for m in g.values()],
            ["Horizon jusqu'au signal suivant (barres), P50 [P25 ; P75]"]
            + [iqr(pd.Series(horizon[m]), 0) for m in g.values()],
            ["MAE jusqu'au signal suivant (ATR), P50 [P25 ; P75]"]
            + [iqr(pd.Series(mae[m]), 2) for m in g.values()]]
    t1 = table(["Mesure"] + list(g), rows)

    lo = a.post_lag_osc_bars.to_numpy()
    c = a.post_x1_crossed_zero.to_numpy()
    bins = [("x1 ne franchit pas zéro avant le signal suivant", ~c),
            ("signal ≥ 3 barres avant x1 = 0", c & (lo <= -3)),
            ("signal 1 à 2 barres avant x1 = 0", c & (lo >= -2) & (lo <= -1)),
            ("signal à la barre où x1 = 0", c & (lo == 0)),
            ("signal 1 à 2 barres après x1 = 0", c & (lo >= 1) & (lo <= 2)),
            ("signal ≥ 3 barres après x1 = 0", c & (lo >= 3))]
    t2 = table(["Position du signal par rapport au passage à zéro de x1"] + list(g),
               [[lab] + [pct(v[m].mean()) for m in g.values()] for lab, v in bins])

    div = (a.obs_dist_cycle_atr - a.obs_dist_seg_atr).to_numpy()
    decel = (a.A_vol / a.peak_bps_vol).to_numpy()
    rows3 = [["`cycle_seg_div_atr` = 0 (le segment porte l'extremum du cycle)"] + [pct((div[m] < 1e-12).mean()) for m in g.values()],
             ["`cycle_seg_div_atr` si > 0 (ATR), P50 [P25 ; P75]"]
             + [iqr(pd.Series(div[m & (div >= 1e-12)]), 2) for m in g.values()],
             ["`decel_ratio` = `A_vol` / `peak_bps_vol`, P50 [P25 ; P75]"] + [iqr(pd.Series(decel[m]), 2) for m in g.values()]]
    t3 = table(["Variable dérivée (causale)"] + list(g), rows3)

    extra = pd.DataFrame({"cycle_seg_div_atr": div, "decel_ratio": decel,
                          "obs_dist_seg_atr": a.obs_dist_seg_atr, "obs_lag_seg_bars": a.obs_lag_seg_bars,
                          "x1_already_flipped_at_t": a.x1_already_flipped_at_t.astype(float), "nis_z_100": a.nis_z_100,
                          "nis_z_100_seg_max": a.nis_z_100_seg_max, "A_vol": a.A_vol, "peak_bps_vol": a.peak_bps_vol,
                          "log_R_rel": a.log_R_rel}).corr(method="spearman")
    pairs = [("obs_dist_seg_atr", "obs_lag_seg_bars"), ("obs_dist_seg_atr", "nis_z_100"),
             ("obs_dist_seg_atr", "x1_already_flipped_at_t"), ("obs_dist_seg_atr", "nis_z_100_seg_max"),
             ("nis_z_100_seg_max", "log_R_rel"), ("nis_z_100_seg_max", "nis_z_100"),
             ("obs_dist_seg_atr", "peak_bps_vol"), ("obs_dist_seg_atr", "A_vol"),
             ("x1_already_flipped_at_t", "peak_bps_vol"), ("x1_already_flipped_at_t", "A_vol"),
             ("cycle_seg_div_atr", "obs_dist_seg_atr"), ("decel_ratio", "x1_already_flipped_at_t"),
             ("decel_ratio", "obs_dist_seg_atr")]
    t4 = table(["Variable", "Variable", "ρ"], [[f"`{p}`", f"`{q}`", fr(extra.loc[p, q], 2)] for p, q in pairs])

    rep = (a.run_rank > 1).to_numpy()
    prev_ok = np.r_[False, (a.direction.to_numpy()[1:] == a.direction.to_numpy()[:-1])] & rep
    j = np.flatnonzero(prev_ok)
    slower_peak = (a.peak_bps_vol.to_numpy()[j] < a.peak_bps_vol.to_numpy()[j - 1]).mean()
    slower_a = (a.A_vol.to_numpy()[j] < a.A_vol.to_numpy()[j - 1]).mean()
    t5 = (f"Répétitions comparées au signal de même sens qui les précède ({n_fr(len(j))} paires) : pic de vitesse "
          f"du segment plus faible (`peak_bps_vol`) dans {pct(slower_peak)} des cas, `A_vol` plus faible dans "
          f"{pct(slower_a)} ; le segment porte l'extremum du cycle (plus bas plus bas / plus haut plus haut) dans "
          f"{pct((div[rep] < 1e-12).mean())} des répétitions.")

    rng = np.random.default_rng(20260928)
    pg = profile_groups(a)
    brow = []
    for gname in ["Rang 1 Long", "Rang 1 Short", "Répétition Long", "Répétition Short"]:
        cells = []
        for tau in (12, 24, 48):
            x = prof["price_atr"][pg[gname], np.flatnonzero(TAUS == tau)[0]]
            x = x[~np.isnan(x)]
            boot = np.median(rng.choice(x, size=(2000, len(x)), replace=True), axis=1)
            lo_b, hi_b = np.percentile(boot, [2.5, 97.5])
            cells.append(f"{fr(np.median(x), 2)} [{fr(lo_b, 2)} ; {fr(hi_b, 2)}]")
        brow.append([gname] + cells)
    t6 = table(["Groupe", "τ = +12", "τ = +24", "τ = +48"], brow)

    return ("## H. Relecture du 2026-09-28\n\n"
            f"Identité vérifiée sur les 7 296 signaux : `post_lag_bars` < 0 ⇔ l'excursion adverse jusqu'au signal "
            f"suivant dépasse `obs_dist_seg_atr` : **{'vraie' if identity else 'FAUSSE'}**.\n\n" + t1
            + "\n\n" + t2 + "\n\n" + t3 + "\n\n" + t4 + "\n\n" + t5
            + "\n\nMédiane de l'excursion signée du close (ATR14(t)) et intervalle bootstrap à 95 % (2 000 tirages) :\n\n"
            + t6)


def section_complements(a, f, idx) -> str:
    """Compléments du porteur (2026-09-28) : biais de la tenue de l'extremum comme cible, typologie par
    `retrace_ratio`, extension au-delà de l'extremum cassé, sortie de la zone neutre."""
    held = (a.post_lag_bars >= 0).to_numpy()
    broken = ~held
    retr = (a.obs_dist_seg_atr / a.leg_atr).to_numpy()
    ext = (a.post_dist_atr - a.obs_dist_seg_atr).to_numpy()            # au-delà de l'extremum, si cassé
    q = pd.qcut(a.obs_dist_seg_atr, 4, labels=["Q1", "Q2", "Q3", "Q4"]).to_numpy()
    rows = []
    for lab in ["Q1", "Q2", "Q3", "Q4"]:
        m = q == lab
        s = a.obs_dist_seg_atr[m]
        rows.append([lab, f"[{fr(s.min(), 2)} ; {fr(s.max(), 2)}]", n_fr(m.sum()), fr(s.median(), 2),
                     pct(np.median(retr[m])), pct(held[m].mean())])
    t1 = table(["Quartile de `obs_dist_seg_atr`", "Bornes (ATR)", "Signaux", "`obs_dist_seg_atr` médian",
                "`retrace_ratio` médian", "Extremum tenu jusqu'au signal suivant"], rows)

    zone = f.zone.to_numpy(dtype=float)
    sig = f.signal.to_numpy().astype(int)
    n = len(zone)
    bars_out, side_out = np.full(len(idx), np.nan), np.zeros(len(idx), dtype=int)
    for i, t in enumerate(idx):
        k = t + 1
        while k < n and zone[k] == 0:
            k += 1
        if k < n:
            bars_out[i], side_out[i] = k - t, int(np.sign(zone[k])) * sig[t]
    leg = a.leg_atr.to_numpy()
    p1, p2 = (retr < 0.5) & (leg >= 2.8), (retr >= 0.85) & (leg < 2.8)
    fams = {"Tous": np.ones(len(a), dtype=bool), "P1 : `retrace_ratio` < 0,5 et `leg_atr` ≥ 2,8": p1,
            "P2 : `retrace_ratio` ≥ 0,85 et `leg_atr` < 2,8": p2, "Ni P1 ni P2": ~(p1 | p2),
            "`retrace_ratio` ≥ 1 (tous)": retr >= 1.0}
    rows2 = []
    for lab, m in fams.items():
        b = m & broken
        conf = m & (side_out == 1)
        rows2.append([lab, f"{n_fr(m.sum())} ({pct(m.mean())})", fr(np.median(leg[m]), 2),
                      fr(a.obs_dist_seg_atr[m].median(), 2), fr(a.A_vol[m].median(), 2), fr(a.nis_z_100[m].median(), 2),
                      pct(a.x1_already_flipped_at_t[m].mean()), pct(broken[m].mean()),
                      f"{fr(np.median(ext[b]), 2)} / {fr(np.mean(ext[b]), 2)} / {fr(np.percentile(ext[b], 90), 2)}",
                      f"{pct(conf.sum() / m.sum())} ; {iqr(pd.Series(bars_out[conf]), 0)}"])
    t2 = table(["Famille (seuils exploratoires du porteur)", "Signaux", "`leg_atr` P50", "`obs_dist_seg_atr` P50",
                "`A_vol` P50", "`nis_z_100` P50", "x1 déjà retourné", "Extremum cassé",
                "Extension si cassé : P50 / moyenne / P90 (ATR)",
                "Sortie de zone neutre vers le sens du signal ; barres P50 [P25 ; P75]"], rows2)
    back = side_out == -1
    txt = (f"Sortie de la zone neutre après le signal : vers la zone du sens du signal dans {pct((side_out == 1).mean())} "
           f"des cas, en {iqr(pd.Series(bars_out[side_out == 1]), 0)} barres ; retour vers la zone d'origine dans "
           f"{pct(back.mean())} des cas, en {iqr(pd.Series(bars_out[back]), 0)} barres.")
    return ("## I. Compléments du porteur (2026-09-28)\n\n`retrace_ratio` = `obs_dist_seg_atr` / `leg_atr`. "
            "Extension si cassé = `post_dist_atr` − `obs_dist_seg_atr`. Seuils 0,5 / 0,85 / 2,8 : découpage "
            "exploratoire, non optimisé et non validé.\n\n" + t1 + "\n\n" + t2 + "\n\n" + txt)


# ── Figures ─────────────────────────────────────────────────────────────────────
def _save(fig, name: str) -> None:
    """savefig avec nouvelles tentatives : sous Windows, un processus tiers peut verrouiller un PNG un court instant."""
    for k in range(6):
        try:
            fig.savefig(FIG / name, dpi=150)
            return
        except OSError:
            if k == 5:
                raise
            time.sleep(0.5)


def _band(ax, P, color, label):
    q1, med, q3 = np.nanpercentile(P, [25, 50, 75], axis=0)
    ax.fill_between(TAUS, q1, q3, color=color, alpha=0.15, lw=0)
    ax.plot(TAUS, med, color=color, lw=1.8, label=label)


def _frame_axes(ax, title, xlabel=True):
    ax.axvline(0, color="0.35", lw=0.8, ls=":")
    ax.axhline(0, color="0.35", lw=0.6)
    ax.set_title(title, fontsize=10)
    if xlabel:
        ax.set_xlabel("τ, barres de 30 min autour du signal (0 = barre du signal)", fontsize=8)
    ax.grid(alpha=0.25, lw=0.5)
    ax.tick_params(labelsize=8)


def figures(a, prof, rho) -> None:
    FIG.mkdir(parents=True, exist_ok=True)
    pg = profile_groups(a)
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.2), sharey=True)
    for ax, g in zip(axes, ["Rang 1", "Répétition"]):
        for side, col in [("Long", C_LONG), ("Short", C_SHORT)]:
            m = pg[f"{g} {side}"]
            _band(ax, prof["price_atr"][m], col, f"{side} (n = {n_fr(m.sum())})")
        _frame_axes(ax, "Rang 1 (flip)" if g == "Rang 1" else "Répétition (run_rank > 1)")
        ax.legend(fontsize=8, frameon=False)
    axes[0].set_ylabel("Excursion signée du close / ATR14(t)", fontsize=9)
    fig.suptitle("EXP-A01 — Trajectoire du prix autour du signal (médiane, bande P25-P75)", fontsize=11)
    fig.tight_layout()
    _save(fig, "fig1_profil_prix.png")
    plt.close(fig)

    fig, axes = plt.subplots(1, 3, figsize=(14, 4))
    for ax, (var, titre) in zip(axes, [("ts_oriented", "trend_strength orienté (d · ts)"),
                                       ("x1_atr_oriented", "Vitesse x1 orientée / ATR14(t)"),
                                       ("nis_z_100", "nis_z_100")]):
        for g, col in [("Rang 1", C_RANK1), ("Répétition", C_REP)]:
            _band(ax, prof[var][pg[g]], col, f"{g} (n = {n_fr(pg[g].sum())})")
        _frame_axes(ax, titre)
        if var == "ts_oriented":
            for y in (-30, 30):
                ax.axhline(y, color="0.6", lw=0.6, ls="--")
    axes[0].legend(fontsize=8, frameon=False)
    fig.suptitle("EXP-A01 — État du filtre autour du signal (médiane, bande P25-P75)", fontsize=11)
    fig.tight_layout()
    _save(fig, "fig2_profil_filtre.png")
    plt.close(fig)

    r1 = (a.run_rank == 1).to_numpy()
    fig, axes = plt.subplots(1, 3, figsize=(14, 4))
    bins = np.arange(-40.5, 41.5, 1)
    for m, col, lab in [(r1, C_RANK1, "Rang 1"), (~r1, C_REP, "Répétition")]:
        axes[0].hist(np.clip(a.post_lag_bars[m], -40, 40), bins=bins, density=True, histtype="step", color=col,
                     lw=1.4, label=lab)
    _frame_axes(axes[0], "post_lag_bars (bornes ±40 regroupées)", xlabel=False)
    axes[0].set_xlabel("barres (> 0 : extremum avant le signal)", fontsize=8)
    axes[0].legend(fontsize=8, frameon=False)
    c = a.post_x1_crossed_zero.to_numpy()
    for v, col, lab in [("post_lag_filter_bars", "#4d4d4d", "extremum → x1 = 0 (filtre)"),
                        ("post_lag_osc_bars", "#2ca25f", "x1 = 0 → signal (oscillateur)")]:
        axes[1].hist(np.clip(a.loc[c, v], -40, 40), bins=bins, density=True, histtype="step", color=col, lw=1.4,
                     label=lab)
    _frame_axes(axes[1], "Décomposition du retard (x1 franchit zéro)", xlabel=False)
    axes[1].set_xlabel("barres", fontsize=8)
    axes[1].legend(fontsize=8, frameon=False)
    b2 = np.arange(0, 6.25, 0.25)
    for m, col, lab in [(r1, C_RANK1, "Rang 1"), (~r1, C_REP, "Répétition")]:
        axes[2].hist(np.clip(a.obs_dist_seg_atr[m], 0, 6), bins=b2, density=True, histtype="step", color=col, lw=1.4,
                     label=lab)
    _frame_axes(axes[2], "obs_dist_seg_atr (borne 6 regroupée)", xlabel=False)
    axes[2].set_xlabel("ATR14(t) déjà parcourus depuis l'extremum du segment", fontsize=8)
    axes[2].legend(fontsize=8, frameon=False)
    fig.suptitle("EXP-A01 — Retard et mouvement consommé (densités)", fontsize=11)
    fig.tight_layout()
    _save(fig, "fig3_retard.png")
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(10, 8.5))
    im = ax.imshow(rho.to_numpy(), cmap="RdBu_r", vmin=-1, vmax=1)
    ax.set_xticks(range(len(CAUSAL)), CAUSAL, rotation=90, fontsize=7)
    ax.set_yticks(range(len(CAUSAL)), CAUSAL, fontsize=7)
    for i in range(len(CAUSAL)):
        for j in range(len(CAUSAL)):
            v = rho.iat[i, j]
            if pd.notna(v):
                ax.text(j, i, f"{v:.2f}", ha="center", va="center", fontsize=5.5,
                        color="white" if abs(v) > 0.6 else "black")
    fig.colorbar(im, ax=ax, shrink=0.8, label="ρ de Spearman")
    ax.set_title("EXP-A01 — Corrélations de rang entre variables causales (7 296 signaux)", fontsize=10)
    fig.tight_layout()
    _save(fig, "fig4_spearman.png")
    plt.close(fig)


def main() -> None:
    df = load_dev_bars()
    atlas, f, idx, atr = build_atlas(df)
    n_raw = int(((f.signal.to_numpy() != 0) & f.valid_features.to_numpy(dtype=bool)).sum())
    prof = event_profiles(f, idx, atr)
    atlas.to_csv(HERE / "atlas_signaux.csv", index=False)

    parts = [section_univers(atlas, f, n_raw), section_taux(atlas), section_quantiles(atlas),
             section_retard_sens(atlas), section_groupes(atlas), section_annees(atlas)]
    txt_prof, pm = section_profils(atlas, prof)
    txt_sp, rho = section_spearman(atlas)
    parts += [txt_prof, txt_sp, section_relecture(atlas, f, idx, atr, prof), section_complements(atlas, f, idx)]
    pm.to_csv(HERE / "profils_medians.csv", index=False)
    rho.to_csv(HERE / "spearman_causales.csv")
    figures(atlas, prof, rho)

    narr = HERE / "narratif_A01.md"
    head = narr.read_text(encoding="utf-8") if narr.exists() else "# EXP-A01\n\n*(narratif à rédiger)*\n"
    (HERE / "rapport_A01.md").write_text(
        head.rstrip() + "\n\n---\n\n# Annexes chiffrées (générées par `run_A01.py`)\n\n" + "\n\n".join(parts) + "\n",
        encoding="utf-8")
    print(f"atlas : {len(atlas)} signaux ; rapport et figures écrits dans {HERE}")


if __name__ == "__main__":
    main()
