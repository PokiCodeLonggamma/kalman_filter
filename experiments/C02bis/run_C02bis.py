"""EXP-C02bis — moteur de régimes sur R2 hors nis_z_100 Q4 : une enveloppe par sous-famille, une position à la fois.

Usage, depuis la racine du dépôt : python experiments/C02bis/run_C02bis.py [--rapport]
  --rapport : régénère seulement rapport_C02bis.md depuis les CSV et controles_C02bis.json.
Sorties dans experiments/C02bis/ : resultats_C02bis.csv, annuel_C02bis.csv, controles_C02bis.json, figures/*.png,
rapport_C02bis.md (= narratif_C02bis.md rédigé à la main, suivi des annexes chiffrées générées ici).

Architecture (décisions du porteur, 2026-09-29) :
- vetos d'entrée : x1 non retourné (R1 et le reste), R3, nis_z_100 Q4 : seuls les signaux de R2 hors Q4 sont pris ;
- routage causal à t : F2b · x1 déjà retourné (retracement 0,50 à 0,85) et F3 · x1 déjà retourné (≥ 0,85) reçoivent
  chacun leur enveloppe (sortie à H, stop propre) ;
- pyramiding 0 global ; après un stop : cooldown jusqu'à t + 1 + H, ou réouverture immédiate.
Configurations : C1 (F2b seul, sans stop), C2 (R2 hors Q4 uniforme, sans stop), RE-1 (F2b sans stop, F3 SL-B à
l'extremum), RE-2 (F2b sans stop, F3 SL-A 2 ATR), RE-3 (F2b SL-A 5 ATR, F3 SL-B à l'extremum) ; H ∈ {13, 20, 24, 26,
28, 32, 48}. RE-4 : C1, C2, RE-1 et RE-2 avec les seuils causaux du contrôle B de C01, à H ∈ {13, 26, 48}.
Frais 5 et 10 bps ; capital à 0,25 % par ATR14(t) (1x en référence) ; IC 95 % par grappes mensuelles, 2 000 tirages.
Relecture du porteur (2026-09-29) : annualisation (Calmar) et cadence mensuelle des variantes RE-4 sur leur propre
période, du 501e signal (9 juin 2020) à fin 2025, et non sur 6 ans ; filtrage mutuel F2b / F3 (section H).
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
from categorization import add_derived, assign_families, bin_descriptor, causal_threshold  # noqa: E402
from envelope import (by_year, dev_signals, effect_ci, equity_curve_sized, mean_ci, risk_weights,  # noqa: E402
                      route_levels, stop_trades, summarize, summarize_sized, trade_frame)
from estimand import load_bars_dev  # noqa: E402
from estimand.excursions import BPS  # noqa: E402
from estimand.stoploss import simulate_strategy  # noqa: E402

FIG = HERE / "figures"
FEES = (5.0, 10.0)
YEARS = list(range(2020, 2026))
N_YEARS = 6.0                                             # 2020-01-01 → 2025-12-31, échantillon entier
T0 = pd.Timestamp("2020-01-01", tz="UTC")
RISK = 25.0
N_BOOT = 2000
BURN_IN = 500
FLOOR = 0.25
H_MAIN = (13, 26, 48)
H_FINE = (20, 24, 26, 28, 32)
HORIZONS = (13, 20, 24, 26, 28, 32, 48)
MODES = {"cooldown": False, "réouverture": True}
REF_TRADES = ROOT / "experiments" / "p6_5" / "strategie_stop_trades.csv"
C02_CSV = ROOT / "experiments" / "C02" / "resultats_C02.csv"
F2B_C02, R2_C02 = "↳ F2b · x1 déjà retourné hors nis_z_100 Q4", "R2 hors nis_z_100 Q4"
EXPECTED = {"R2": 1452, "F2b": 741, "F3": 711}
CONFIGS = [
    {"key": "C1", "nom": "C1 — F2b seul, sans stop", "univers": "F2b", "regles": {"F2b": None}},
    {"key": "C2", "nom": "C2 — R2 hors Q4 uniforme, sans stop", "univers": "R2", "regles": {"F2b": None, "F3": None}},
    {"key": "RE-1", "nom": "RE-1 — F2b sans stop, F3 SL-B extremum", "univers": "R2",
     "regles": {"F2b": None, "F3": ("SL-B", 0.0)}},
    {"key": "RE-2", "nom": "RE-2 — F2b sans stop, F3 SL-A 2 ATR", "univers": "R2",
     "regles": {"F2b": None, "F3": ("SL-A", 2.0)}},
    {"key": "RE-3", "nom": "RE-3 — F2b SL-A 5 ATR, F3 SL-B extremum", "univers": "R2",
     "regles": {"F2b": ("SL-A", 5.0), "F3": ("SL-B", 0.0)}},
]
NOMS = {c["key"]: c["nom"] for c in CONFIGS}
RE4_KEYS = ("C1", "C2", "RE-1", "RE-2")
ENTIER, VARIANTES = "échantillon entier", ("échantillon entier, après 500", "glissante 500 signaux", "expansive")


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


def ci(x, lo, hi, nd) -> str:
    return f"{sg(x, nd)} [{sg(lo, nd)} ; {sg(hi, nd)}]"


def sci(x) -> str:
    if x == 0:
        return "0"
    e = int(np.floor(np.log10(abs(x))))
    return f"{fr(x / 10 ** e, 1)}·10{str(e).translate(str.maketrans('-0123456789', '⁻⁰¹²³⁴⁵⁶⁷⁸⁹'))}"


def table(header, rows) -> str:
    out = ["| " + " | ".join(header) + " |", "|" + "|".join(["---"] * len(header)) + "|"]
    return "\n".join(out + ["| " + " | ".join(str(c) for c in r) + " |" for r in rows])


def label(key, mode) -> str:
    return NOMS[key] if key in ("C1", "C2") else f"{NOMS[key]} ({mode})"


# ── Univers, contrôles bloquants ────────────────────────────────────────────────
def full_masks(atlas) -> dict[str, np.ndarray]:
    """R2 hors Q4 et ses deux sous-familles, définitions figées de B01 (seuils de l'échantillon entier)."""
    d = add_derived(atlas)
    fam = assign_families(d, float(np.median(d.leg_atr)))
    ref = pd.read_csv(ROOT / "experiments" / "B01" / "excursions_signaux.csv", usecols=["bar_index", "famille"])
    if not (np.array_equal(ref.bar_index, atlas.bar_index) and np.array_equal(ref.famille, fam)):
        raise SystemExit("familles différentes de experiments/B01/excursions_signaux.csv : arrêt")
    x1 = d.x1_already_flipped_at_t.to_numpy(dtype=bool)
    hors_q4 = bin_descriptor(d.nis_z_100, "nis_z_100")[0] != "Q4"
    m = {"F2b": (fam == "F2b") & x1 & hors_q4, "F3": (fam == "F3") & x1 & hors_q4}
    m["R2"] = m["F2b"] | m["F3"]
    bad = {k: int(v.sum()) for k, v in m.items() if int(v.sum()) != EXPECTED[k]}
    if bad:
        raise SystemExit(f"effectifs différents du cadrage : {bad}")
    return m


def causal_masks(atlas) -> tuple[dict, list[dict]]:
    """Contrôle B de C01 : médiane de leg_atr et P75 de nis_z_100 sur les seuls signaux précédents (fenêtre de 500
    signaux ou expansive, 500 signaux d'amorce). Les trois variantes ne gardent que les signaux après l'amorce."""
    d = add_derived(atlas)
    x1 = d.x1_already_flipped_at_t.to_numpy(dtype=bool)
    r, leg, nis = d.retrace_ratio.to_numpy(), d.leg_atr.to_numpy(), d.nis_z_100.to_numpy()
    n = len(d)
    post = np.arange(n) >= BURN_IN
    thr = {VARIANTES[0]: (np.full(n, np.median(leg)), np.full(n, np.quantile(nis, 0.75))),
           VARIANTES[1]: (causal_threshold(leg, 0.5, BURN_IN, BURN_IN), causal_threshold(nis, 0.75, BURN_IN, BURN_IN)),
           VARIANTES[2]: (causal_threshold(leg, 0.5, None, BURN_IN), causal_threshold(nis, 0.75, None, BURN_IN))}
    out, accord = {}, []
    for v, (tl, tn) in thr.items():
        small, keep = leg < tl, (nis <= tn) & x1 & post
        m = {"F2b": small & (r >= 0.5) & (r < 0.85) & keep, "F3": small & (r >= 0.85) & keep}
        m["R2"] = m["F2b"] | m["F3"]
        out[v] = m
    ref = out[VARIANTES[0]]
    for v, m in out.items():
        for k in ("R2", "F2b", "F3"):
            accord.append({"variante": v, "sous_ensemble": k, "n_signaux": int(m[k].sum()),
                           "accord": float((m[k][post] == ref[k][post]).mean())})
    return out, accord


def check_anchor(bars, f) -> dict:
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
        out[variante] = {"n_trades": len(tr), "n_stops": int(tr.stop.sum())}
    return out


# ── Moteur ──────────────────────────────────────────────────────────────────────
class Engine:
    """Signaux candidats d'un univers (masque), sous-famille de chaque signal, niveaux de stop routés."""

    def __init__(self, bars, atlas, atr, masks):
        self.bars, self.atr, self.masks = bars, atr, masks
        self.t_all, self.s_all, self.n_all = (atlas[c].to_numpy() for c in ("bar_index", "direction", "prev_seg_len"))

    def run(self, univers: str, regles: dict, H: int, dynamic: bool) -> tuple[pd.DataFrame, pd.Series]:
        m = self.masks[univers]
        t, s, n = self.t_all[m], self.s_all[m], self.n_all[m]
        fam = np.where(self.masks["F3"][m], "F3", "F2b")
        level = None
        if any(r is not None for r in regles.values()):
            level = route_levels(self.bars, t, s, self.atr[t], n, fam, regles, FLOOR)
        return stop_trades(self.bars, t, s, H, level, dynamic=dynamic), pd.Series(fam, index=t)


def cagr(pnl, n_years: float) -> float:
    return float((1.0 + pnl) ** (1.0 / n_years) - 1.0)


def metrics(tr, bars, atr_bps, fee, n_cand, fam: pd.Series, n_years: float = N_YEARS) -> tuple[dict, pd.DataFrame]:
    """`n_years` : durée de la période où la variante peut trader (annualisation et cadence mensuelle)."""
    m = summarize(tr, bars, atr_bps, fee, n_candidates=n_cand)
    m["trades_par_mois"] = m["n_trades"] / (12.0 * n_years)
    m.update(mean_ci(tr, bars, fee, N_BOOT, atr_bps=atr_bps))
    m.update({f"{k}_r25": v for k, v in summarize_sized(tr, bars, atr_bps, fee, RISK).items()})
    m["cagr_r25"] = cagr(m["pnl_compose_r25"], n_years)
    m["calmar_r25"] = m["cagr_r25"] / abs(m["mdd_valorise_r25"]) if m["mdd_valorise_r25"] < 0 else np.nan
    m["part_stop"] = float(tr.stop.mean())
    tf = trade_frame(tr, bars, atr_bps, fee)
    f = fam.reindex(tr.signal_bar.to_numpy()).to_numpy()
    for k in ("F2b", "F3"):
        sel = f == k
        m[f"n_{k}"] = int(sel.sum())
        m[f"esperance_atr_{k}"] = float(tf.net_atr[sel].mean()) if sel.any() else np.nan
        m[f"esperance_bps_{k}"] = float(tf.net_bps[sel].mean()) if sel.any() else np.nan
    y = by_year(tr, bars, atr_bps, fee)
    w = risk_weights(atr_bps.reindex(tr.signal_bar.to_numpy()).to_numpy(dtype=float), RISK)
    lg = pd.Series(np.log1p(w * tf.net_bps.to_numpy() / BPS)).groupby(tf.year.to_numpy()).sum()
    y["pnl_compose_r25"] = np.expm1(lg.reindex(y.annee.to_numpy()).to_numpy())
    m["annees_atr_pos"] = int((y.esperance_atr > 0).sum())
    m["annees_pnl_r25_pos"] = int((y.pnl_compose_r25 > 0).sum())
    return m, y


def decomposition(dyn, cd, atr_bps, fee) -> dict:
    new, lost = dyn[~dyn.signal_bar.isin(set(cd.signal_bar))], cd[~cd.signal_bar.isin(set(dyn.signal_bar))]

    def esp(tr):
        if not len(tr):
            return np.nan
        return float(((tr.ret_gross_bps.to_numpy() - fee) / atr_bps.reindex(tr.signal_bar.to_numpy()).to_numpy()).mean())

    return {"n_debloques": len(new), "esperance_debloques_atr": esp(new), "n_perdus": len(lost),
            "esperance_perdus_atr": esp(lost)}


def run_grid(bars, atr_bps, eng: Engine, keys, horizons, variante: str,
             n_years: float = N_YEARS) -> tuple[list, list, dict]:
    rows, ann, trades = [], [], {}
    for H in horizons:
        runs = {}
        for c in (c for c in CONFIGS if c["key"] in keys):
            n_cand = int(eng.masks[c["univers"]].sum())
            for mode, dyn in MODES.items():
                tr, fam = eng.run(c["univers"], c["regles"], H, dyn)
                runs[(c["key"], mode)] = (tr, fam, n_cand)
        for (key, mode), (tr, fam, n_cand) in runs.items():
            trades[(variante, key, H, mode)] = tr
            extra = {}
            if mode == "cooldown" and key.startswith("RE"):
                ctrl = runs[("C2", "cooldown")][0]
                extra.update({f"{k}_vs_C2": v for k, v in effect_ci(tr, ctrl, bars, atr_bps, N_BOOT).items()})
                if key == "RE-3":
                    extra.update({f"{k}_vs_RE1": v for k, v in
                                  effect_ci(tr, runs[("RE-1", "cooldown")][0], bars, atr_bps, N_BOOT).items()})
            for fee in FEES:
                m, y = metrics(tr, bars, atr_bps, fee, n_cand, fam, n_years)
                row = {"variante_seuils": variante, "configuration": key, "nom": NOMS[key], "H": H, "mode": mode,
                       "frais_bps": fee, "annees": n_years, **m, **extra}
                if mode == "réouverture":
                    row.update(decomposition(tr, runs[(key, "cooldown")][0], atr_bps, fee))
                rows.append(row)
                ann += [{"variante_seuils": variante, "configuration": key, "H": H, "mode": mode, "frais_bps": fee, **r}
                        for r in y.to_dict("records")]
        print(f"  {variante}, H = {H} : fait")
    return rows, ann, trades


def mutual_filter(eng: Engine, bars, atr_bps, H: int = 26) -> list[dict]:
    """Filtrage mutuel de F2b et F3 sous pyramiding 0 (lecture cooldown) : trades de chaque sous-famille jouée seule
    absents du moteur (évincés), classés selon le trade du moteur ouvert à leur signal (l'autre sous-famille en sens
    opposé ou de même sens, ou la même sous-famille par effet de chaîne), et trades du moteur absents de la course
    seule (ajoutés par chaîne). Résultats évincés : ceux de la course seule ; ajoutés : ceux du moteur."""
    cases = [("F2b", "sans stop", None, "C2 et RE-1", {"F2b": None, "F3": ("SL-B", 0.0)}),
             ("F3", "sans stop", None, "C2", {"F2b": None, "F3": None}),
             ("F3", "SL-B extremum", ("SL-B", 0.0), "RE-1", {"F2b": None, "F3": ("SL-B", 0.0)})]
    rows = []
    for sub, stop, rule, moteur, regles in cases:
        alone, _ = eng.run(sub, {sub: rule}, H, False)
        eng_tr, fam = eng.run("R2", regles, H, False)
        ef = fam.reindex(eng_tr.signal_bar.to_numpy()).to_numpy()
        kept = eng_tr[ef == sub]
        ev = alone[~alone.signal_bar.isin(set(kept.signal_bar))]
        add = kept[~kept.signal_bar.isin(set(alone.signal_bar))]
        j = np.searchsorted(eng_tr.signal_bar.to_numpy(), ev.signal_bar.to_numpy(), side="left") - 1
        if (j < 0).any() or not (ev.signal_bar.to_numpy() < eng_tr.signal_bar.to_numpy()[j] + H).all():
            raise SystemExit(f"filtrage mutuel {sub} : trade évincé sans trade bloquant : arrêt")
        other = ef[j] != sub
        same = eng_tr.side.to_numpy()[j] == ev.side.to_numpy()
        groups = {"oppose": other & ~same, "meme_sens": other & same, "chaine": ~other}
        for fee in FEES:
            def natr(tr):
                return (tr.ret_gross_bps.to_numpy() - fee) / atr_bps.reindex(tr.signal_bar.to_numpy()).to_numpy()
            va, ve, vk, vd = natr(alone), natr(ev), natr(kept), natr(add)
            row = {"sous_famille": sub, "stop": stop, "moteur": moteur, "H": H, "frais_bps": fee,
                   "n_seule": len(alone), "esp_seule": float(va.mean()), "n_moteur": len(kept),
                   "esp_moteur": float(vk.mean()), "n_ajoutes": len(add),
                   "esp_ajoutes": float(vd.mean()) if len(add) else np.nan}
            for g, sel in groups.items():
                row[f"n_{g}"] = int(sel.sum())
                row[f"esp_{g}"] = float(ve[sel].mean()) if sel.any() else np.nan
            if not np.isclose(va.sum() - ve.sum() + vd.sum(), vk.sum(), rtol=1e-9, atol=1e-9):
                raise SystemExit(f"filtrage mutuel {sub} : bilan non refermé : arrêt")
            rows.append(row)
    return rows


def check_c02(res: pd.DataFrame, bars, atr_bps, eng: Engine) -> dict:
    """Bloquant : C1 et C2 = contrôles sans stop de C02 ; le moteur avec une même règle pour F2b et F3 = la règle
    uniforme de C02 (SL-B à l'extremum, SL-A 2 ATR), dans les deux lectures, à H ∈ {13, 26, 48}."""
    ref = pd.read_csv(C02_CSV)
    cols = ["n_trades", "esperance_bps", "esperance_atr", "pnl_compose", "mdd_valorise", "pf", "wr", "pnl_compose_r25",
            "mdd_valorise_r25"]
    worst, n = 0.0, 0

    def cmp(a: dict, g: pd.Series, what: str):
        nonlocal worst, n
        for c in cols:
            x, y = float(a[c]), float(g[c])
            if not np.isclose(x, y, rtol=1e-5, atol=1e-9):
                raise SystemExit(f"différent de C02 : {what}, {c} ({x} contre {y}) : arrêt")
            worst = max(worst, abs(x - y) / max(abs(y), 1e-12))
        n += 1

    for H in H_MAIN:
        for fee in FEES:
            for key, name in (("C1", F2B_C02), ("C2", R2_C02)):
                a = res[(res.variante_seuils == ENTIER) & (res.configuration == key) & (res.H == H)
                        & (res["mode"] == "cooldown") & (res.frais_bps == fee)].iloc[0]
                g = ref[(ref.configuration == name) & (ref.H == H) & (ref.stop == "sans") & (ref["mode"] == "dynamique")
                        & (ref.frais_bps == fee)].iloc[0]
                cmp(a, g, f"{key} H{H} {fee:g} bps")
        for stop, rule in (("SL-B 0", ("SL-B", 0.0)), ("SL-A 2", ("SL-A", 2.0))):
            for mode, dyn in MODES.items():
                tr, _ = eng.run("R2", {"F2b": rule, "F3": rule}, H, dyn)
                for fee in FEES:
                    a = {**summarize(tr, bars, atr_bps, fee, int(eng.masks["R2"].sum())),
                         **{f"{k}_r25": v for k, v in summarize_sized(tr, bars, atr_bps, fee, RISK).items()}}
                    g = ref[(ref.configuration == R2_C02) & (ref.H == H) & (ref.stop == stop)
                            & (ref["mode"] == ("figé" if not dyn else "dynamique")) & (ref.frais_bps == fee)].iloc[0]
                    cmp(a, g, f"routage uniforme {stop} H{H} {mode} {fee:g} bps")
    return {"lignes_comparees": n, "ecart_relatif_max": worst}


# ── Sections du rapport ─────────────────────────────────────────────────────────
class Index:
    def __init__(self, res):
        self.d = {(r["variante_seuils"], r["configuration"], int(r["H"]), r["mode"], float(r["frais_bps"])): r
                  for r in res.to_dict("records")}

    def __call__(self, key, H, mode="cooldown", fee=5.0, variante=ENTIER) -> dict:
        return self.d[(variante, key, int(H), mode, float(fee))]


ROWS_MAIN = [("C1", "cooldown"), ("C2", "cooldown"), ("RE-1", "cooldown"), ("RE-1", "réouverture"),
             ("RE-2", "cooldown"), ("RE-2", "réouverture"), ("RE-3", "cooldown"), ("RE-3", "réouverture")]


def frais_cell(r) -> str:
    brut = sg(r["brut_bps"] / r["n_trades"], 1)
    if r["brut_bps"] <= 0:
        return f"sans objet (brut ≤ 0) ; {brut}"
    return f"{'> 1 000 %' if r['part_frais'] > 10 else pct(r['part_frais'], 0)} ; {brut}"


def section_controles(meta) -> str:
    a, c = meta["ancre"], meta["c02"]
    acc = pd.DataFrame(meta["accord"])
    rows = [["Ancre P6.5d, sans stop et stop 2,5 %",
             f"{n_fr(a['sans_stop']['n_trades'])} et {n_fr(a['stop_2_5']['n_trades'])} trades identiques au fichier de "
             "référence"],
            ["C1, C2 et routage uniforme = C02", f"{c['lignes_comparees']} lignes identiques (écart relatif max "
             f"{sci(c['ecart_relatif_max'])}) : C1 = F2b sans stop, C2 = R2 hors Q4 sans stop ; moteur avec la même "
             "règle pour F2b et F3 = règle uniforme de C02 (SL-B à l'extremum, SL-A 2 ATR), cooldown = « entrées "
             "figées », réouverture = « séquentiel dynamique »"],
            ["Univers", f"R2 hors Q4 = {EXPECTED['R2']} signaux : F2b · x1 déjà retourné {EXPECTED['F2b']}, F3 · x1 déjà "
             f"retourné {EXPECTED['F3']} ; familles identiques à B01"],
            ["Seuils causaux (RE-4)", "; ".join(f"{r.variante} : R2 {n_fr(r.n_signaux)} signaux, accord {pct(r.accord)}"
                                                for r in acc[acc.sous_ensemble == "R2"].itertuples())],
            ["IC 95 %", f"grappes mensuelles d'entrée, {n_fr(N_BOOT)} tirages ; effets appariés sur les mêmes entrées "
             "que C2 (lecture cooldown)"],
            ["Capital", "1 ATR14(t) = 0,25 % du capital, levier ≤ 1x ; notionnel 1x en référence ; Calmar = PnL "
             "annualisé / valeur absolue du MDD valorisé, à 0,25 % par ATR, annualisé sur la période où la variante peut trader "
             f"(6 ans ; {fr(meta['post_amorce']['annees'], 2)} ans pour les variantes RE-4, après l'amorce)"],
            ["Période", "2020-01 → 2025-12 (72 mois) ; aucune barre de 2026 lue"]]
    return "## A. Contrôles bloquants et conventions\n\n" + table(["Contrôle", "Résultat"], rows)


HEAD8 = ["Configuration", "PnL : 0,25 %/ATR ; 1x ; bps (1x)", "PF : 1x ; pondéré", "WR",
         "Espérance : bps [IC] ; ATR [IC]", "MDD valorisé : 0,25 %/ATR ; 1x", "Trades (/mois) ; stoppés",
         "Durée méd.", "Part des frais ; brut/trade"]
HEADX = ["Configuration", "Long / Short (ATR)", "Timing ATR [IC]", "F2b : n ; esp. ATR", "F3 : n ; esp. ATR",
         "Années > 0 : ATR ; PnL", "PnL annualisé ; Calmar"]


def row8(r, name) -> list:
    return [name, f"{spct(r['pnl_compose_r25'])} ; {spct(r['pnl_compose'])} ; {sg(r['pnl_bps'], 0)}",
            f"{fr(r['pf'], 2)} ; {fr(r['pf_r25'], 2)}", pct(r["wr"]),
            f"{ci(r['esperance_bps'], r['esperance_bps_lo'], r['esperance_bps_hi'], 1)} ; "
            f"{ci(r['esperance_atr'], r['esperance_atr_lo'], r['esperance_atr_hi'], 3)}",
            f"{pct(r['mdd_valorise_r25'])} ; {pct(r['mdd_valorise'], 0)}",
            f"{n_fr(r['n_trades'])} ({fr(r['trades_par_mois'], 1)}) ; {pct(r['part_stop'], 0)}",
            fr(r["duree_mediane"], 0), frais_cell(r)]


def rowx(r, name) -> list:
    return [name, f"{sg(r['long_atr'], 2)} / {sg(r['short_atr'], 2)}",
            ci(r["timing_atr"], r["timing_atr_lo"], r["timing_atr_hi"], 3),
            f"{n_fr(r['n_F2b'])} ; {sg(r['esperance_atr_F2b'], 3)}", f"{n_fr(r['n_F3'])} ; {sg(r['esperance_atr_F3'], 3)}",
            f"{int(r['annees_atr_pos'])}/6 ; {int(r['annees_pnl_r25_pos'])}/6",
            f"{spct(r['cagr_r25'], 1)} ; {fr(r['calmar_r25'], 2)}"]


def section_h(ix, H) -> str:
    out = [f"## B. Tableau complet à H = {H}"]
    for fee in FEES:
        rs = [(ix(k, H, m, fee), label(k, m)) for k, m in ROWS_MAIN]
        out.append(f"**{fr(fee, 0)} bps aller-retour — 8 métriques**\n\n" + table(HEAD8, [row8(r, n) for r, n in rs]))
        out.append(f"**{fr(fee, 0)} bps — sens, sous-familles, régularité**\n\n" + table(HEADX, [rowx(r, n) for r, n in rs]))
    return "\n\n".join(out)


def section_plateau(ix) -> str:
    out = ["## C. Profil d'horizon (plateau autour de H = 26)",
           "Lecture cooldown pour les variantes du moteur. Première table : espérance nette par trade en ATR [IC 95 %]. "
           "Seconde : PnL composé ; MDD valorisé, à 0,25 % par ATR."]
    keys = ["C1", "C2", "RE-1", "RE-2", "RE-3"]
    for fee in FEES:
        r1 = [[NOMS[k]] + [ci(ix(k, H, fee=fee)["esperance_atr"], ix(k, H, fee=fee)["esperance_atr_lo"],
                              ix(k, H, fee=fee)["esperance_atr_hi"], 3) for H in HORIZONS] for k in keys]
        r2 = [[NOMS[k]] + [f"{spct(ix(k, H, fee=fee)['pnl_compose_r25'])} ; {pct(ix(k, H, fee=fee)['mdd_valorise_r25'], 0)}"
                           for H in HORIZONS] for k in keys]
        hd = ["Configuration"] + [f"H = {H}" for H in HORIZONS]
        out.append(f"**{fr(fee, 0)} bps — espérance ATR [IC]**\n\n" + table(hd, r1))
        out.append(f"**{fr(fee, 0)} bps — PnL ; MDD**\n\n" + table(hd, r2))
    return "\n\n".join(out)


def section_modes(ix) -> str:
    out = ["## D. Cooldown contre réouverture immédiate (5 bps)",
           "Débloqués : trades ouverts grâce à un stop, absents de la lecture cooldown ; perdus : trades de la lecture "
           "cooldown masqués par un trade débloqué."]
    rows = []
    for key in ("RE-1", "RE-2", "RE-3"):
        for H in HORIZONS:
            c, d = ix(key, H, "cooldown"), ix(key, H, "réouverture")
            rows.append([NOMS[key], f"H = {H}", f"{n_fr(c['n_trades'])} ; {n_fr(d['n_trades'])}",
                         f"{n_fr(d['n_debloques'])} ; {sg(d['esperance_debloques_atr'], 3)}",
                         f"{n_fr(d['n_perdus'])} ; {sg(d['esperance_perdus_atr'], 3)}",
                         f"{sg(c['esperance_atr'], 3)} ; {sg(d['esperance_atr'], 3)}",
                         f"{spct(c['pnl_compose_r25'])} ; {spct(d['pnl_compose_r25'])}",
                         f"{pct(c['mdd_valorise_r25'], 0)} ; {pct(d['mdd_valorise_r25'], 0)}"])
    out.append(table(["Configuration", "H", "Trades : cooldown ; réouverture", "Débloqués : n ; esp. ATR",
                      "Perdus : n ; esp. ATR", "Esp. ATR : cooldown ; réouverture", "PnL : cooldown ; réouverture",
                      "MDD : cooldown ; réouverture"], rows))
    return "\n\n".join(out)


def section_effets(ix) -> str:
    out = ["## E. Effets appariés (lecture cooldown, mêmes entrées que C2)",
           "Moyenne par trade de (variante − C2), frais compensés : l'effet des stops propres à chaque sous-famille. "
           "Dernière colonne : RE-3 − RE-1, soit l'effet du stop de catastrophe SL-A 5 ATR sur F2b."]
    rows = []
    for H in HORIZONS:
        cells = [f"{ci(ix(k, H)['effet_atr_vs_C2'], ix(k, H)['effet_atr_lo_vs_C2'], ix(k, H)['effet_atr_hi_vs_C2'], 3)} ; "
                 f"{ci(ix(k, H)['effet_bps_vs_C2'], ix(k, H)['effet_bps_lo_vs_C2'], ix(k, H)['effet_bps_hi_vs_C2'], 1)}"
                 for k in ("RE-1", "RE-2", "RE-3")]
        r3 = ix("RE-3", H)
        cells.append(f"{ci(r3['effet_atr_vs_RE1'], r3['effet_atr_lo_vs_RE1'], r3['effet_atr_hi_vs_RE1'], 3)}")
        rows.append([f"H = {H}"] + cells)
    out.append(table(["Horizon", "RE-1 − C2 : ATR [IC] ; bps [IC]", "RE-2 − C2", "RE-3 − C2", "RE-3 − RE-1 (ATR)"], rows))
    return "\n\n".join(out)


def section_annees(ann) -> str:
    out = ["## F. Stabilité annuelle (5 bps)", "Cellule : espérance nette par trade en ATR14(t) (trades) ; dernière "
           "colonne : PnL composé à 0,25 % par ATR, année par année."]
    a5 = ann[(ann.variante_seuils == ENTIER) & (ann.frais_bps == 5.0)]
    for H in H_MAIN:
        rows = []
        for key, mode in ROWS_MAIN:
            g = a5[(a5.configuration == key) & (a5.H == H) & (a5["mode"] == mode)].set_index("annee")
            rows.append([label(key, mode)] + [f"{sg(g.esperance_atr.get(y), 2)} ({n_fr(g.n_trades.get(y, 0))})"
                                              for y in YEARS]
                        + [" ; ".join(spct(g.pnl_compose_r25.get(y), 0) for y in YEARS)])
        out.append(f"### H = {H}\n\n" + table(["Configuration"] + [str(y) for y in YEARS] + ["PnL par année"], rows))
    return "\n\n".join(out)


def section_causal(ix, meta) -> str:
    acc = pd.DataFrame(meta["accord"])
    pa = meta["post_amorce"]
    debut = pd.Timestamp(pa["debut"])
    out = ["## G. RE-4 — Seuils causaux (contrôle B de C01)",
           f"Médiane de `leg_atr` et P75 de `nis_z_100` calculés sur les seuls signaux précédents. Les {BURN_IN} premiers "
           f"signaux (13 janvier → {debut:%d/%m/%Y %H:%M} UTC) sont exclus des trois variantes, comparées sur la même "
           f"période : du {BURN_IN + 1}e signal au 31/12/2025, soit {fr(pa['annees'], 2)} ans (annualisation du Calmar "
           "et cadence mensuelle ; 6 ans pour l'échantillon entier).",
           "### Accord des masques avec les seuils de l'échantillon entier (après les 500 premiers signaux)\n\n"
           + table(["Sous-ensemble"] + list(VARIANTES),
                   [[k] + [f"{n_fr(acc[(acc.variante == v) & (acc.sous_ensemble == k)].n_signaux.iloc[0])} ; "
                           f"{pct(acc[(acc.variante == v) & (acc.sous_ensemble == k)].accord.iloc[0])}"
                           for v in VARIANTES] for k in ("R2", "F2b", "F3")])]
    for H in H_MAIN:
        rows = []
        for key in RE4_KEYS:
            for mode in (("cooldown",) if key in ("C1", "C2") else ("cooldown", "réouverture")):
                cells = []
                for v in VARIANTES:
                    r5, r10 = ix(key, H, mode, 5.0, v), ix(key, H, mode, 10.0, v)
                    cells.append(f"{ci(r5['esperance_atr'], r5['esperance_atr_lo'], r5['esperance_atr_hi'], 3)} ; "
                                 f"{spct(r5['pnl_compose_r25'])} ; {pct(r5['mdd_valorise_r25'], 0)} ; "
                                 f"{spct(r5['cagr_r25'], 1)} par an, Calmar {fr(r5['calmar_r25'], 2)} ; "
                                 f"{int(r5['annees_pnl_r25_pos'])}/6 ‖ 10 bps : {sg(r10['esperance_atr'], 3)} ; "
                                 f"{spct(r10['pnl_compose_r25'])}")
                rows.append([label(key, mode)] + cells)
        out.append(f"### H = {H}\n\nCellule, à 5 bps : espérance ATR [IC] ; PnL ; MDD ; PnL annualisé et Calmar ; années "
                   f"à PnL > 0. Puis, à 10 bps : espérance ATR ; PnL.\n\n" + table(["Configuration"] + list(VARIANTES), rows))
    return "\n\n".join(out)


def section_filtrage(meta) -> str:
    mf = pd.DataFrame(meta["filtrage_mutuel"])
    out = ["## H. Filtrage mutuel de F2b et F3 sous pyramiding 0 (H = 26, cooldown)",
           "Chaque sous-famille jouée seule, puis dans le moteur. Évincés : trades de la course seule absents du moteur, "
           "classés selon le trade du moteur ouvert à leur signal ; résultat de la course seule. Ajoutés : trades du "
           "moteur absents de la course seule (un trade évincé libère la place d'un signal suivant) ; résultat du moteur. "
           "Bilan refermé : seule − évincés + ajoutés = moteur."]
    for fee in FEES:
        rows = []
        for r in mf[mf.frais_bps == fee].itertuples():
            autre = "F3" if r.sous_famille == "F2b" else "F2b"
            rows.append([f"{r.sous_famille}, {r.stop} (moteur : {r.moteur})", f"{n_fr(r.n_seule)} ; {sg(r.esp_seule, 3)}",
                         f"{n_fr(r.n_oppose)} ; {sg(r.esp_oppose, 3)}", f"{n_fr(r.n_meme_sens)} ; {sg(r.esp_meme_sens, 3)}",
                         f"{n_fr(r.n_chaine)} ; {sg(r.esp_chaine, 3)}", f"{n_fr(r.n_ajoutes)} ; {sg(r.esp_ajoutes, 3)}",
                         f"{n_fr(r.n_moteur)} ; {sg(r.esp_moteur, 3)}"])
        out.append(f"**{fr(fee, 0)} bps — n ; espérance nette par trade (ATR)**\n\n"
                   + table(["Sous-famille, stop", "Seule", "Évincés : l'autre sous-famille ouverte en sens opposé",
                            "Évincés : l'autre, même sens", "Évincés : même sous-famille (chaîne)", "Ajoutés (chaîne)",
                            "Dans le moteur"], rows))
    return "\n\n".join(out)


def write_report(res, ann, meta) -> None:
    ix = Index(res)
    parts = [section_controles(meta), section_h(ix, 26), section_plateau(ix), section_modes(ix), section_effets(ix),
             section_annees(ann), section_causal(ix, meta), section_filtrage(meta)]
    narr = HERE / "narratif_C02bis.md"
    head = narr.read_text(encoding="utf-8") if narr.exists() else "# EXP-C02bis\n\n*(narratif à rédiger)*\n"
    (HERE / "rapport_C02bis.md").write_text(
        head.rstrip() + "\n\n---\n\n# Annexes chiffrées (générées par `run_C02bis.py`)\n\n" + "\n\n".join(parts) + "\n",
        encoding="utf-8")


# ── Figures ─────────────────────────────────────────────────────────────────────
COLORS = {"C1": "#7f7f7f", "C2": "#000000", "RE-1": "#d62728", "RE-2": "#1f77b4", "RE-3": "#2ca02c"}


def _save(fig, name: str) -> None:
    for k in range(6):
        try:
            fig.savefig(FIG / name, dpi=130)
            return
        except OSError:
            if k == 5:
                raise
            time.sleep(0.5)


def fig_plateau(ix) -> None:
    fig, axes = plt.subplots(2, 3, figsize=(19, 9.5), sharex=True)
    x = np.array(HORIZONS, dtype=float)
    for i, fee in enumerate(FEES):
        for j, key in enumerate(("C1", "C2", "RE-1", "RE-2", "RE-3")):
            rs = [ix(key, H, fee=fee) for H in HORIZONS]
            y = np.array([r["esperance_atr"] for r in rs])
            lo, hi = np.array([r["esperance_atr_lo"] for r in rs]), np.array([r["esperance_atr_hi"] for r in rs])
            off = (j - 2) * 0.35
            axes[i, 0].errorbar(x + off, y, yerr=[np.maximum(y - lo, 0), np.maximum(hi - y, 0)], color=COLORS[key],
                                marker="o", ms=4, lw=1.4, capsize=2, elinewidth=0.8, label=NOMS[key])
            axes[i, 1].plot(x, [100 * r["pnl_compose_r25"] for r in rs], color=COLORS[key], marker="o", ms=4, lw=1.4)
            axes[i, 2].plot(x, [100 * r["mdd_valorise_r25"] for r in rs], color=COLORS[key], marker="o", ms=4, lw=1.4)
        axes[i, 0].set_ylabel(f"{fr(fee, 0)} bps — espérance nette par trade (ATR14(t)), IC 95 %", fontsize=9)
        axes[i, 1].set_ylabel(f"{fr(fee, 0)} bps — PnL composé, 0,25 % par ATR (%)", fontsize=9)
        axes[i, 2].set_ylabel(f"{fr(fee, 0)} bps — max drawdown valorisé (%)", fontsize=9)
    for ax in axes.flat:
        ax.axvspan(19, 33, color="0.92", zorder=0)
        ax.axhline(0, color="0.3", lw=0.8)
        ax.grid(alpha=0.3, lw=0.5)
        ax.set_xticks(HORIZONS)
        ax.tick_params(labelsize=8)
    for ax in axes[1]:
        ax.set_xlabel("Horizon de sortie H (barres de 30 min) ; zone grise : sensibilité fine 20-32", fontsize=8)
    axes[0, 0].legend(fontsize=7, frameon=False)
    fig.suptitle("EXP-C02bis — Profil d'horizon du moteur de régimes (lecture cooldown)", fontsize=11)
    fig.tight_layout()
    _save(fig, "fig1_plateau_horizon.png")
    plt.close(fig)


def fig_equity(bars, trades, atr_bps) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(19, 6.5), sharey=False)
    for ax, fee in zip(axes, FEES):
        for key, mode in [("C1", "cooldown"), ("C2", "cooldown"), ("RE-1", "cooldown"), ("RE-1", "réouverture"),
                          ("RE-2", "cooldown"), ("RE-3", "cooldown")]:
            tr = trades[(ENTIER, key, 26, mode)]
            w = risk_weights(atr_bps.reindex(tr.signal_bar.to_numpy()).to_numpy(dtype=float), RISK)
            eq = equity_curve_sized(bars, tr, fee, w)
            ax.plot(eq.index, 100 * (eq.to_numpy() - 1), color=COLORS[key], lw=1.8 if key == "RE-1" else 1.1,
                    ls="--" if mode == "réouverture" else "-", label=label(key, mode))
        ax.axhline(0, color="0.4", lw=0.7)
        ax.set_title(f"H = 26, {fr(fee, 0)} bps", fontsize=10)
        ax.grid(alpha=0.3, lw=0.5)
        ax.tick_params(labelsize=8)
    axes[0].set_ylabel("PnL net composé, 1 ATR14(t) = 0,25 % du capital (%)", fontsize=9)
    axes[0].legend(fontsize=7, frameon=False)
    fig.suptitle("EXP-C02bis — Courbes de capital du moteur de régimes", fontsize=11)
    fig.tight_layout()
    _save(fig, "fig2_courbes_equite_H26.png")
    plt.close(fig)


def fig_years(ann) -> None:
    a5 = ann[(ann.variante_seuils == ENTIER) & (ann.frais_bps == 5.0)]
    fig, axes = plt.subplots(1, 3, figsize=(20, 6.5), sharey=True)
    names = [label(k, m) for k, m in ROWS_MAIN]
    for ax, H in zip(axes, H_MAIN):
        mat = np.full((len(ROWS_MAIN), len(YEARS)), np.nan)
        for a, (key, mode) in enumerate(ROWS_MAIN):
            g = a5[(a5.configuration == key) & (a5.H == H) & (a5["mode"] == mode)].set_index("annee")
            for b, y in enumerate(YEARS):
                if y in g.index:
                    mat[a, b] = g.esperance_atr.loc[y]
        lim = np.nanmax(np.abs(mat))
        ax.imshow(mat, cmap="RdBu", vmin=-lim, vmax=lim, aspect="auto")
        for a in range(mat.shape[0]):
            for b in range(mat.shape[1]):
                ax.text(b, a, sg(mat[a, b], 2), ha="center", va="center", fontsize=8)
        ax.set_xticks(range(len(YEARS)), YEARS, fontsize=8)
        ax.set_title(f"H = {H}", fontsize=10)
    axes[0].set_yticks(range(len(names)), names, fontsize=8)
    fig.suptitle("EXP-C02bis — Espérance nette par trade et par année (ATR14(t), 5 bps)", fontsize=11)
    fig.tight_layout()
    _save(fig, "fig3_stabilite_annuelle.png")
    plt.close(fig)


def fig_causal(ix) -> None:
    fig, axes = plt.subplots(1, 3, figsize=(19, 5.8), sharey=True)
    marks = {VARIANTES[0]: "o", VARIANTES[1]: "s", VARIANTES[2]: "^"}
    for ax, H in zip(axes, H_MAIN):
        for i, key in enumerate(RE4_KEYS):
            for j, v in enumerate(VARIANTES):
                r = ix(key, H, "cooldown", 5.0, v)
                xx = i + (j - 1) * 0.22
                ax.errorbar([xx], [r["esperance_atr"]], yerr=[[max(r["esperance_atr"] - r["esperance_atr_lo"], 0)],
                                                              [max(r["esperance_atr_hi"] - r["esperance_atr"], 0)]],
                            color=COLORS[key], marker=marks[v], ms=6, capsize=3, label=v if i == 0 else None)
        ax.axhline(0, color="0.3", lw=0.8)
        ax.set_xticks(range(len(RE4_KEYS)), RE4_KEYS)
        ax.set_title(f"H = {H}, 5 bps, lecture cooldown", fontsize=10)
        ax.grid(alpha=0.3, lw=0.5)
    axes[0].set_ylabel("Espérance nette par trade (ATR14(t)), IC 95 %", fontsize=9)
    axes[0].legend(fontsize=8, frameon=False)
    fig.suptitle("EXP-C02bis — RE-4 : seuils de l'échantillon entier contre seuils causaux (après les 500 premiers "
                 "signaux)", fontsize=11)
    fig.tight_layout()
    _save(fig, "fig4_seuils_causaux.png")
    plt.close(fig)


# ── Programme ───────────────────────────────────────────────────────────────────
def main() -> None:
    if "--rapport" in sys.argv:
        res, ann = pd.read_csv(HERE / "resultats_C02bis.csv"), pd.read_csv(HERE / "annuel_C02bis.csv")
        write_report(res, ann, json.loads((HERE / "controles_C02bis.json").read_text(encoding="utf-8")))
        print(f"rapport_C02bis.md régénéré dans {HERE}")
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
    atr_bps = pd.Series(atlas.atr14_bps.to_numpy(), index=atlas.bar_index.to_numpy())
    eng = Engine(bars, atlas, atr, full_masks(atlas))
    cmasks, meta["accord"] = causal_masks(atlas)
    if not all(np.array_equal(cmasks[VARIANTES[0]][k], eng.masks[k] & (np.arange(len(atlas)) >= BURN_IN))
               for k in ("R2", "F2b", "F3")):
        raise SystemExit("masques de l'échantillon entier après l'amorce différents des masques figés : arrêt")
    print(f"contrôles préalables passés ({time.time() - t0:.0f} s)")
    debut = bars.time.iloc[int(atlas.bar_index.iloc[BURN_IN])]           # premier signal après l'amorce
    n_post = N_YEARS - (debut - T0) / pd.Timedelta(days=365.25)
    meta["post_amorce"] = {"debut": str(debut), "annees": n_post}
    rows, ann, trades = run_grid(bars, atr_bps, eng, [c["key"] for c in CONFIGS], HORIZONS, ENTIER)
    for v in VARIANTES:
        r, a, _ = run_grid(bars, atr_bps, Engine(bars, atlas, atr, cmasks[v]), RE4_KEYS, H_MAIN, v, n_post)
        rows, ann = rows + r, ann + a
    res, ann = pd.DataFrame(rows), pd.DataFrame(ann)
    meta["c02"] = check_c02(res, bars, atr_bps, eng)
    meta["filtrage_mutuel"] = mutual_filter(eng, bars, atr_bps)
    meta["duree_s"] = round(time.time() - t0)
    res.to_csv(HERE / "resultats_C02bis.csv", index=False, float_format="%.6g")
    ann.to_csv(HERE / "annuel_C02bis.csv", index=False, float_format="%.6g")
    (HERE / "controles_C02bis.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
    FIG.mkdir(parents=True, exist_ok=True)
    ix = Index(res)
    fig_plateau(ix)
    fig_equity(bars, trades, atr_bps)
    fig_years(ann)
    fig_causal(ix)
    write_report(res, ann, meta)
    print(f"C02bis : {len(res)} lignes de résultats en {meta['duree_s']} s ; rapport, tableaux et figures dans {HERE}")


if __name__ == "__main__":
    main()
