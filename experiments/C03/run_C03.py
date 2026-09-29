"""EXP-C03 — break-even différé sur RE-1, configuration de référence du moteur de régimes, une position à la fois.

Usage, depuis la racine du dépôt : python experiments/C03/run_C03.py [--rapport]
  --rapport : régénère seulement rapport_C03.md depuis les CSV et controles_C03.json.
Sorties dans experiments/C03/ : resultats_C03.csv, annuel_C03.csv, controles_C03.json, figures/*.png,
rapport_C03.md (= narratif_C03.md rédigé à la main, suivi des annexes chiffrées générées ici).

Contrôle (décision du porteur, 2026-09-29) : RE-1, soit R2 hors nis_z_100 Q4, F2b sans stop, F3 SL-B à l'extremum du
segment, pyramiding 0, cooldown jusqu'à t + 1 + H. H = 26, et H ∈ {24, 28} pour vérifier le plateau.
Facteur unique : break-even différé (`envelope.breakeven_trades`).
- Seuil d'activation m · ATR14(t), m ∈ {1 ; 1,5 ; 2 ; 2,5 ; 3 ; 4}, lu sur les barres t + 1 … t + H − 1.
- Le stop initial prime sur la barre d'activation.
- Stop remonté à open[t + 1] ± 5 bps de b + 1 à t + H, même niveau à 10 bps de frais.
Périmètres : V1 = F3 seul, V2 = F2b seul, V3 = F2b et F3. Lecture principale en cooldown : mêmes entrées que RE-1,
effet apparié BE − RE-1 (I-M9). La réouverture immédiate est en annexe.
Frais 5 et 10 bps ; capital à 0,25 % par ATR14(t), 1x en référence ; IC 95 % par grappes mensuelles, 2 000 tirages.
Drawdown : effet apparié sur le MDD aux sorties (0,25 %/ATR, 5 bps), bootstrap par mois d'entrée (mêmes tirages).
Annexe : borne optimiste d'un take-profit fixe (exclusion décidée par le porteur, vérifiée ici).
Les mises en forme, le moteur de C02bis (contrôle), l'ancre et les métriques viennent de run_C02bis.py (importé).
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
from envelope import breakeven_trades, breakeven_trigger_levels, effect_ci, risk_weights, route_levels  # noqa: E402
from estimand import load_bars_dev  # noqa: E402
from estimand.excursions import BPS  # noqa: E402
from estimand.stoploss import TRADE_COLUMNS  # noqa: E402


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


C2B = _load("run_C02bis", ROOT / "experiments" / "C02bis" / "run_C02bis.py")
fr, sg, pct, spct, n_fr, ci, sci, table = C2B.fr, C2B.sg, C2B.pct, C2B.spct, C2B.n_fr, C2B.ci, C2B.sci, C2B.table

FIG = HERE / "figures"
FEES = (5.0, 10.0)
YEARS = list(range(2020, 2026))
N_BOOT = C2B.N_BOOT
FLOOR = C2B.FLOOR
BE_BPS = 5.0
H_MAIN = 26
HORIZONS = (24, 26, 28)
M_GRID = (1.0, 1.5, 2.0, 2.5, 3.0, 4.0)
TP_GRID = (2.0, 3.0, 4.0, 5.0, 6.0)
MODES = {"cooldown": False, "réouverture": True}
RE1_RULES = {"F2b": None, "F3": ("SL-B", 0.0)}
PERIMETRES = {"V1": ("F3",), "V2": ("F2b",), "V3": ("F2b", "F3")}
NOMS_P = {"V1": "V1 — BE sur F3", "V2": "V2 — BE sur F2b", "V3": "V3 — BE sur F2b et F3"}
CONFIGS = [("RE-1", None, np.nan)] + [(f"{p} m{m:g}", p, m) for p in PERIMETRES for m in M_GRID]
QUANTS = (0.50, 0.75, 0.90, 0.95, 0.99)
C02BIS_CSV = ROOT / "experiments" / "C02bis" / "resultats_C02bis.csv"


def nom(cfg: str) -> str:
    if cfg == "RE-1":
        return "RE-1 (contrôle)"
    p, m = cfg.split(" m")
    return f"{p} — BE {fr(float(m), 1)} ATR ({'+'.join(PERIMETRES[p])})"


# ── Moteur ──────────────────────────────────────────────────────────────────────
class EngineBE:
    """Signaux de R2 hors Q4, stop initial de RE-1 routé par sous-famille ; break-even sur un périmètre."""

    def __init__(self, bars, atlas, atr, masks):
        r2 = masks["R2"]
        self.bars = bars
        self.t = atlas.bar_index.to_numpy()[r2]
        self.s = atlas.direction.to_numpy()[r2]
        self.fam = np.where(masks["F3"][r2], "F3", "F2b")
        self.a = np.asarray(atr, dtype=float)[self.t]                 # ATR14(t) en prix
        self.level = route_levels(bars, self.t, self.s, self.a, atlas.prev_seg_len.to_numpy()[r2], self.fam,
                                  RE1_RULES, FLOOR)
        self.fam_s = pd.Series(self.fam, index=self.t)
        self.atr_s = pd.Series(self.a, index=self.t)
        self.n_cand = int(r2.sum())

    def run(self, H: int, dynamic: bool, perimetre: str | None = None, m: float = np.nan) -> pd.DataFrame:
        trig = None
        if perimetre is not None:
            mm = np.where(np.isin(self.fam, PERIMETRES[perimetre]), m, np.nan)
            trig = breakeven_trigger_levels(self.bars, self.t, self.s, self.a, mm)
        return breakeven_trades(self.bars, self.t, self.s, H, self.level, trig, BE_BPS, dynamic)


def net_atr(tr, atr_bps, fee) -> np.ndarray:
    return (tr.ret_gross_bps.to_numpy() - fee) / atr_bps.reindex(tr.signal_bar.to_numpy()).to_numpy()


def be_metrics(tr, bars, atr_bps, fee, eng: EngineBE) -> tuple[dict, pd.DataFrame]:
    m, y = C2B.metrics(tr, bars, atr_bps, fee, eng.n_cand, eng.fam_s)
    na = net_atr(tr, atr_bps, fee)
    q = np.quantile(na, QUANTS)
    m.update({f"q{int(round(100 * p))}_atr": float(v) for p, v in zip(QUANTS, q)})
    m.update({"part_sup3_atr": float((na >= 3).mean()), "part_sup5_atr": float((na >= 5).mean()),
              "moy_top10_atr": float(na[na >= q[2]].mean()),
              "part_be_actif": float((tr.be_bar >= 0).mean()), "part_be_stop": float(tr.be_stop.mean()),
              "part_be_gap": float((tr.be_stop & tr.gap).mean()),
              "part_stop_initial": float((tr.stop & ~tr.be_stop).mean())})
    return m, y


def mechanics(tr, ctrl, eng: EngineBE, bars, atr_bps) -> tuple[dict, dict]:
    """Décomposition de l'effet apparié (lecture cooldown, mêmes entrées) : seuls les trades sortis au break-even
    changent. Sauvés : break-even meilleur que la sortie de RE-1 ; coupés : RE-1 finissait plus haut."""
    atr = atr_bps.reindex(tr.signal_bar.to_numpy()).to_numpy()
    d = (tr.ret_gross_bps.to_numpy() - ctrl.ret_gross_bps.to_numpy()) / atr
    be = tr.be_stop.to_numpy(dtype=bool)
    if len(d) and np.abs(d[~be]).max(initial=0.0) > 1e-9:
        raise SystemExit("effet apparié non nul hors des sorties au break-even : arrêt")
    base = net_atr(ctrl, atr_bps, 5.0)                                # résultat net de RE-1, 5 bps
    fam = eng.fam_s.reindex(tr.signal_bar.to_numpy()).to_numpy()
    n = len(tr)
    sv, ct = be & (d > 0), be & (d < 0)

    def mean(v):
        return float(v.mean()) if len(v) else np.nan

    out = {"n_actifs": int((tr.be_bar >= 0).sum()), "n_be": int(be.sum()), "n_be_gap": int((be & tr.gap.to_numpy()).sum()),
           "n_sauves": int(sv.sum()), "gain_sauves": float(d[sv].sum() / n), "moy_gain_sauves": mean(d[sv]),
           "re1_sauves": mean(base[sv]), "n_coupes": int(ct.sum()), "cout_coupes": float(d[ct].sum() / n),
           "moy_cout_coupes": mean(d[ct]), "re1_coupes": mean(base[ct]),
           "n_coupes_re1_sup3": int((ct & (base >= 3)).sum()), "cout_coupes_re1_sup3": float(d[ct & (base >= 3)].sum() / n)}
    for k in ("F2b", "F3"):
        sel = fam == k
        out[f"effet_atr_{k}"] = mean(d[sel])
        out[f"n_be_{k}"] = int((be & sel).sum())
    years = bars.time.iloc[tr.entry_bar.to_numpy()].dt.year.to_numpy()
    return out, {int(y): mean(d[years == y]) for y in YEARS}


def excursions(tr, bars, eng: EngineBE, H: int) -> pd.DataFrame:
    """MFE en ATR14(t) depuis open[t + 1] : sur toute la fenêtre t + 1 … t + H (MFE26, arrêts ignorés) et avant la
    sortie de RE-1 (barre du stop comprise)."""
    op, hi, lo = (bars[c].to_numpy(dtype=float) for c in ("open", "high", "low"))
    t, e, s = tr.signal_bar.to_numpy(), tr.entry_bar.to_numpy(), tr.side.to_numpy()
    x = np.minimum(t + 1 + H, len(bars) - 1)
    held = np.where(tr.stop.to_numpy(dtype=bool), tr.exit_bar.to_numpy(), x - 1)
    a = eng.atr_s.reindex(t).to_numpy()
    full, avant = [], []
    for ei, xi, hi_end, si, ai in zip(e, x, held, s, a):
        p0 = op[ei]
        f = (hi[ei:xi].max() - p0) if si == 1 else (p0 - lo[ei:xi].min())
        v = (hi[ei:hi_end + 1].max() - p0) if si == 1 else (p0 - lo[ei:hi_end + 1].min())
        full.append(f / ai)
        avant.append(v / ai)
    return pd.DataFrame({"mfe_full": full, "mfe_avant": avant, "p0": op[e], "atr": a})


def tp_bound(ctrl, bars, eng: EngineBE, atr_bps, H: int) -> dict:
    """Borne optimiste d'un take-profit fixe TP · ATR14(t) sur les trades de RE-1 : sortie à +TP dès que la MFE
    l'atteint (fenêtre complète : TP toujours touché avant le stop ; ou avant la sortie de RE-1), résultat de RE-1
    sinon. Et la MFE des trades de RE-1 face aux seuils m du break-even."""
    ex = excursions(ctrl, bars, eng, H)
    gross = ctrl.ret_gross_bps.to_numpy()
    atr_b = atr_bps.reindex(ctrl.signal_bar.to_numpy()).to_numpy()
    out = {"tp": [], "mfe": []}
    for fee in FEES:
        base = (gross - fee) / atr_b
        out[f"re1_esp_{fee:g}"] = float(base.mean())
        out[f"re1_q90_{fee:g}"] = float(np.quantile(base, 0.9))
        for tp in TP_GRID:
            g_tp = tp * ex.atr.to_numpy() / ex.p0.to_numpy() * BPS          # gain brut à +TP · ATR14(t)
            row = {"frais_bps": fee, "tp": tp}
            for w in ("full", "avant"):
                hit = ex[f"mfe_{w}"].to_numpy() >= tp
                v = (np.where(hit, g_tp, gross) - fee) / atr_b
                row.update({f"part_{w}": float(hit.mean()), f"esp_{w}": float(v.mean()),
                            f"re1_touches_{w}": float(base[hit].mean()) if hit.any() else np.nan})
            out["tp"].append(row)
    base = (gross - 5.0) / atr_b
    for m in M_GRID:
        for w in ("full", "avant"):
            hit = ex[f"mfe_{w}"].to_numpy() >= m
            lose = hit & (base < 0)
            out["mfe"].append({"m": m, "fenetre": w, "part_atteint": float(hit.mean()), "part_atteint_perdant": float(lose.mean()),
                               "part_perdants_parmi_atteints": float(lose.sum() / hit.sum()) if hit.any() else np.nan,
                               "perte_moyenne": float(base[lose].mean()) if lose.any() else np.nan})
    return out


def month_orders(tr, bars, n_boot: int = N_BOOT, seed: int = 0) -> list[np.ndarray]:
    """Tirages de mois d'entrée avec remise (générateur et ordre de `envelope.metrics._cluster_counts`) : pour chaque
    tirage, indices des trades des mois tirés, mois dans l'ordre du tirage, trades dans l'ordre chronologique."""
    t = bars.time.iloc[tr.entry_bar.to_numpy()]
    _, inv = np.unique((t.dt.year * 12 + t.dt.month).to_numpy(), return_inverse=True)
    g = int(inv.max()) + 1
    members = [np.flatnonzero(inv == k) for k in range(g)]
    rng = np.random.default_rng(seed)
    return [np.concatenate([members[k] for k in rng.integers(0, g, g)]) for _ in range(n_boot)]


def sized_returns(tr, atr_bps, fee) -> np.ndarray:
    a = atr_bps.reindex(tr.signal_bar.to_numpy()).to_numpy(dtype=float)
    return risk_weights(a, C2B.RISK) * (tr.ret_gross_bps.to_numpy(dtype=float) - fee) / BPS


def mdd_exits(r: np.ndarray) -> float:
    """MDD du capital composé aux sorties (formule de `summarize_sized`, `mdd_sorties`)."""
    c = np.cumprod(1.0 + r)
    return float(min(0.0, (c / np.maximum.accumulate(np.r_[1.0, c])[1:] - 1.0).min()))


def mdd_effect(tr, ctrl, orders, atr_bps, fee: float = 5.0) -> dict:
    """Effet apparié sur le MDD aux sorties (points ; > 0 : drawdown moins profond avec le break-even), IC 95 % par
    bootstrap de mois d'entrée, part des tirages où le break-even est moins profond."""
    r0, r1 = sized_returns(ctrl, atr_bps, fee), sized_returns(tr, atr_bps, fee)
    d = np.array([mdd_exits(r1[o]) - mdd_exits(r0[o]) for o in orders])
    lo, hi = np.percentile(d, [2.5, 97.5])
    return {"dmdd_sorties": mdd_exits(r1) - mdd_exits(r0), "dmdd_lo": float(lo), "dmdd_hi": float(hi),
            "p_dmdd_moins_profond": float((d > 0).mean())}


# ── Grille ──────────────────────────────────────────────────────────────────────
def run_grid(bars, atr_bps, eng: EngineBE) -> tuple[list, list, dict]:
    rows, ann, trades = [], [], {}
    for H in HORIZONS:
        ctrl = {mode: eng.run(H, dyn) for mode, dyn in MODES.items()}
        orders = month_orders(ctrl["cooldown"], bars)
        for cfg, p, m in CONFIGS:
            runs = ctrl if p is None else {mode: eng.run(H, dyn, p, m) for mode, dyn in MODES.items()}
            extra, per_year = {}, {}
            if p is not None:
                extra.update({f"{k}_vs_RE1": v for k, v in
                              effect_ci(runs["cooldown"], ctrl["cooldown"], bars, atr_bps, N_BOOT).items()})
                mech, per_year = mechanics(runs["cooldown"], ctrl["cooldown"], eng, bars, atr_bps)
                extra.update(mech)
                extra.update(mdd_effect(runs["cooldown"], ctrl["cooldown"], orders, atr_bps))
            for mode, tr in runs.items():
                trades[(cfg, H, mode)] = tr
                for fee in FEES:
                    mm, y = be_metrics(tr, bars, atr_bps, fee, eng)
                    key = {"configuration": cfg, "perimetre": p or "—", "m": m, "H": H, "mode": mode, "frais_bps": fee}
                    row = {**key, **mm}
                    row.update(extra if mode == "cooldown" else C2B.decomposition(tr, runs["cooldown"], atr_bps, fee))
                    rows.append(row)
                    for r in y.to_dict("records"):
                        r.update(key)
                        if mode == "cooldown" and p is not None:
                            r["effet_atr_vs_RE1"] = per_year.get(int(r["annee"]), np.nan)
                        ann.append(r)
        print(f"  H = {H} : fait")
    return rows, ann, trades


def check_controls(res: pd.DataFrame, bars, atr_bps, eng: EngineBE, eng_c2b) -> dict:
    """Bloquant : RE-1 = RE-1 de C02bis, trade par trade et dans resultats_C02bis.csv (H ∈ {24, 26, 28}, cooldown
    et réouverture, 5 et 10 bps) ; un seuil d'activation infini redonne RE-1."""
    ref = pd.read_csv(C02BIS_CSV)
    cols = ["n_trades", "esperance_bps", "esperance_atr", "esperance_atr_lo", "esperance_atr_hi", "pnl_compose", "mdd_valorise",
            "pf", "wr", "pnl_compose_r25", "mdd_valorise_r25", "calmar_r25"]
    worst, n = 0.0, 0
    for H in HORIZONS:
        for mode, dyn in MODES.items():
            a, (b, _) = eng.run(H, dyn), eng_c2b.run("R2", RE1_RULES, H, dyn)
            if not a[TRADE_COLUMNS].equals(b[TRADE_COLUMNS]):
                raise SystemExit(f"RE-1 H{H} {mode} : trades différents de C02bis : arrêt")
            if not eng.run(H, dyn, "V3", np.inf)[TRADE_COLUMNS].equals(b[TRADE_COLUMNS]):
                raise SystemExit(f"seuil infini H{H} {mode} : différent de RE-1 : arrêt")
            for fee in FEES:
                r = res[(res.configuration == "RE-1") & (res.H == H) & (res["mode"] == mode) & (res.frais_bps == fee)].iloc[0]
                g = ref[(ref.variante_seuils == C2B.ENTIER) & (ref.configuration == "RE-1") & (ref.H == H)
                        & (ref["mode"] == mode) & (ref.frais_bps == fee)].iloc[0]
                for c in cols:
                    x, y = float(r[c]), float(g[c])
                    if not np.isclose(x, y, rtol=1e-5, atol=1e-9):
                        raise SystemExit(f"RE-1 H{H} {mode} {fee:g} bps : {c} différent de C02bis ({x} contre {y}) : arrêt")
                    worst = max(worst, abs(x - y) / max(abs(y), 1e-12))
                n += 1
    return {"lignes_comparees": n, "ecart_relatif_max": worst}


# ── Sections du rapport ─────────────────────────────────────────────────────────
class Index:
    def __init__(self, res):
        self.d = {(r["configuration"], int(r["H"]), r["mode"], float(r["frais_bps"])): r for r in res.to_dict("records")}

    def __call__(self, cfg, H=H_MAIN, mode="cooldown", fee=5.0) -> dict:
        return self.d[(cfg, int(H), mode, float(fee))]


def cfgs(p: str) -> list[str]:
    return [f"{p} m{m:g}" for m in M_GRID]


def section_controles(meta) -> str:
    a, c = meta["ancre"], meta["controles"]
    rows = [["Ancre P6.5d, sans stop et stop 2,5 %",
             f"{n_fr(a['sans_stop']['n_trades'])} et {n_fr(a['stop_2_5']['n_trades'])} trades identiques au fichier de "
             "référence"],
            ["RE-1 = RE-1 de C02bis", f"trades identiques à H ∈ {{24, 26, 28}}, cooldown et réouverture ; {c['lignes_comparees']} "
             f"lignes de métriques identiques à resultats_C02bis.csv (écart relatif max {sci(c['ecart_relatif_max'])})"],
            ["Seuil d'activation infini", "redonne RE-1 trade par trade (V3, les deux lectures, trois horizons)"],
            ["Effet apparié", "nul sur tous les trades non sortis au break-even (vérifié pour chaque variante)"],
            ["Univers", f"R2 hors Q4 = {C2B.EXPECTED['R2']} signaux : F2b {C2B.EXPECTED['F2b']}, F3 {C2B.EXPECTED['F3']} ; "
             "familles identiques à B01"],
            ["Break-even", "seuil m · ATR14(t) lu sur high (Long) ou low (Short) des barres t + 1 … t + H − 1 ; stop initial "
             "prioritaire sur la barre d'activation ; stop à open[t + 1] ± 5 bps de b + 1 à t + H (niveau identique à 10 bps "
             "de frais) ; gap : sortie à l'ouverture"],
            ["IC 95 %", f"grappes mensuelles d'entrée, {n_fr(N_BOOT)} tirages ; effets appariés sur les entrées de RE-1 "
             "(lecture cooldown)"],
            ["Capital", "1 ATR14(t) = 0,25 % du capital, levier ≤ 1x ; notionnel 1x en référence ; Calmar = PnL annualisé "
             "sur 6 ans / valeur absolue du MDD valorisé, à 0,25 % par ATR"],
            ["Période", "2020-01 → 2025-12 (72 mois) ; aucune barre de 2026 lue"]]
    return "## A. Contrôles bloquants et conventions\n\n" + table(["Contrôle", "Résultat"], rows)


HEAD8 = ["Configuration", "PnL : 0,25 %/ATR ; 1x ; bps (1x)", "PF : 1x ; pondéré", "WR", "Espérance : bps [IC] ; ATR [IC]",
         "MDD valorisé : 0,25 %/ATR ; 1x", "Trades (/mois) ; stop initial ; BE", "Durée méd.", "Part des frais ; brut/trade"]
HEADX = ["Configuration", "Long / Short (ATR)", "Timing ATR [IC]", "F2b : esp. ATR", "F3 : esp. ATR", "Années > 0 : ATR ; PnL",
         "PnL annualisé ; Calmar", "BE activé ; sorti au BE (dont gap)"]


def row8(r, name) -> list:
    return [name, f"{spct(r['pnl_compose_r25'])} ; {spct(r['pnl_compose'])} ; {sg(r['pnl_bps'], 0)}",
            f"{fr(r['pf'], 2)} ; {fr(r['pf_r25'], 2)}", pct(r["wr"]),
            f"{ci(r['esperance_bps'], r['esperance_bps_lo'], r['esperance_bps_hi'], 1)} ; "
            f"{ci(r['esperance_atr'], r['esperance_atr_lo'], r['esperance_atr_hi'], 3)}",
            f"{pct(r['mdd_valorise_r25'])} ; {pct(r['mdd_valorise'], 0)}",
            f"{n_fr(r['n_trades'])} ({fr(r['trades_par_mois'], 1)}) ; {pct(r['part_stop_initial'], 0)} ; {pct(r['part_be_stop'], 0)}",
            fr(r["duree_mediane"], 0), C2B.frais_cell(r)]


def rowx(r, name) -> list:
    return [name, f"{sg(r['long_atr'], 2)} / {sg(r['short_atr'], 2)}",
            ci(r["timing_atr"], r["timing_atr_lo"], r["timing_atr_hi"], 3),
            sg(r["esperance_atr_F2b"], 3), sg(r["esperance_atr_F3"], 3),
            f"{int(r['annees_atr_pos'])}/6 ; {int(r['annees_pnl_r25_pos'])}/6",
            f"{spct(r['cagr_r25'], 1)} ; {fr(r['calmar_r25'], 2)}",
            f"{pct(r['part_be_actif'], 0)} ; {pct(r['part_be_stop'], 0)} ({pct(r['part_be_gap'], 1)})"]


def section_h26(ix) -> str:
    out = [f"## B. Tableau complet à H = {H_MAIN} (lecture cooldown)"]
    order = ["RE-1"] + [c for p in PERIMETRES for c in cfgs(p)]
    for fee in FEES:
        out.append(f"**{fr(fee, 0)} bps aller-retour — 8 métriques**\n\n" + table(HEAD8, [row8(ix(c, fee=fee), nom(c)) for c in order]))
        out.append(f"**{fr(fee, 0)} bps — sens, sous-familles, régularité, break-even**\n\n"
                   + table(HEADX, [rowx(ix(c, fee=fee), nom(c)) for c in order]))
    return "\n\n".join(out)


def section_effets(ix) -> str:
    out = ["## C. Effet apparié BE − RE-1 (lecture cooldown, mêmes entrées)",
           "Moyenne par trade de (variante − RE-1) sur toutes les entrées de RE-1, frais compensés (identique à 5 et 10 bps)."]
    rows = []
    for m in M_GRID:
        cells = []
        for p in PERIMETRES:
            r = ix(f"{p} m{m:g}")
            cells.append(f"{ci(r['effet_atr_vs_RE1'], r['effet_atr_lo_vs_RE1'], r['effet_atr_hi_vs_RE1'], 3)} ; "
                         f"{ci(r['effet_bps_vs_RE1'], r['effet_bps_lo_vs_RE1'], r['effet_bps_hi_vs_RE1'], 1)}")
        rows.append([f"m = {fr(m, 1)}"] + cells)
    out.append(f"### H = {H_MAIN} : ATR [IC] ; bps [IC]\n\n" + table(["Seuil"] + [NOMS_P[p] for p in PERIMETRES], rows))
    for H in HORIZONS:
        if H == H_MAIN:
            continue
        rows = [[f"m = {fr(m, 1)}"] + [ci(ix(f'{p} m{m:g}', H)['effet_atr_vs_RE1'], ix(f'{p} m{m:g}', H)['effet_atr_lo_vs_RE1'],
                                          ix(f'{p} m{m:g}', H)['effet_atr_hi_vs_RE1'], 3) for p in PERIMETRES] for m in M_GRID]
        out.append(f"### H = {H} : ATR [IC]\n\n" + table(["Seuil"] + [NOMS_P[p] for p in PERIMETRES], rows))
    ref = " ; ".join(f"{pct(ix('RE-1', H)['mdd_sorties_r25'], 1)} à H = {H}" for H in HORIZONS)
    out.append("### Effet apparié sur le drawdown\n\nMDD du capital aux sorties, 0,25 % par ATR, 5 bps. Cellule : écart "
               "BE − RE-1 observé, en points de MDD (> 0 : drawdown moins profond avec le break-even) ; plage P2,5-P97,5 "
               "de cet écart sur 2 000 chemins où les mois d'entrée sont tirés avec remise (mêmes tirages que les IC) ; "
               "part des chemins où le break-even est moins profond. Le MDD dépend de l'ordre des trades : la plage décrit "
               "l'écart sur des chemins réordonnés, ce n'est pas un IC centré sur l'écart observé, qui peut en sortir. MDD "
               f"aux sorties de RE-1 : {ref}.")
    for H in HORIZONS:
        rows = []
        for m in M_GRID:
            cells = []
            for p in PERIMETRES:
                r = ix(f"{p} m{m:g}", H)
                cells.append(f"{sg(100 * r['dmdd_sorties'], 1)} ; [{sg(100 * r['dmdd_lo'], 1)} ; "
                             f"{sg(100 * r['dmdd_hi'], 1)}] ; {fr(r['p_dmdd_moins_profond'], 2)}")
            rows.append([f"m = {fr(m, 1)}"] + cells)
        out.append(f"**H = {H}**\n\n" + table(["Seuil"] + [NOMS_P[p] for p in PERIMETRES], rows))
    return "\n\n".join(out)


def section_mecanique(ix) -> str:
    out = [f"## D. Mécanique du break-even à H = {H_MAIN} (cooldown, mêmes entrées que RE-1)",
           "Seuls les trades sortis au break-even changent. Sauvés : le break-even sort plus haut que RE-1 ; coupés : RE-1 "
           "finissait plus haut. Gain et coût : ATR par trade sur toutes les entrées ; leur somme est l'effet apparié. "
           "« RE-1 » : résultat net moyen (5 bps) de ces trades dans RE-1."]
    rows = []
    for p in PERIMETRES:
        for c in cfgs(p):
            r = ix(c)
            n = r["n_trades"]
            rows.append([nom(c), f"{n_fr(r['n_actifs'])} ({pct(r['n_actifs'] / n, 0)})",
                         f"{n_fr(r['n_be'])} ({n_fr(r['n_be_gap'])})",
                         f"{n_fr(r['n_sauves'])} ; {sg(r['moy_gain_sauves'], 2)} ; {sg(r['re1_sauves'], 2)}",
                         f"{n_fr(r['n_coupes'])} ; {sg(r['moy_cout_coupes'], 2)} ; {sg(r['re1_coupes'], 2)}",
                         f"{n_fr(r['n_coupes_re1_sup3'])} ; {sg(r['cout_coupes_re1_sup3'], 3)}",
                         f"{sg(r['gain_sauves'], 3)} ; {sg(r['cout_coupes'], 3)} ; {sg(r['effet_atr_vs_RE1'], 3)}",
                         f"{sg(r['effet_atr_F2b'], 3)} ; {sg(r['effet_atr_F3'], 3)}"])
    out.append(table(["Configuration", "Activés (part)", "Sortis au BE (gap)", "Sauvés : n ; effet moyen ; RE-1",
                      "Coupés : n ; effet moyen ; RE-1", "Coupés avec RE-1 ≥ +3 ATR : n ; coût par trade",
                      "Gain ; coût ; effet par trade", "Effet par trade : F2b ; F3"], rows))
    return "\n\n".join(out)


def section_queue(ix) -> str:
    out = [f"## E. Queue droite à H = {H_MAIN} (cooldown, 5 bps)",
           "Distribution du résultat net par trade en ATR14(t). Top 10 % : moyenne des trades au-dessus de leur propre P90."]
    rows = []
    for c in ["RE-1"] + [c for p in PERIMETRES for c in cfgs(p)]:
        r = ix(c)
        rows.append([nom(c)] + [sg(r[f"q{int(round(100 * q))}_atr"], 2) for q in QUANTS]
                    + [pct(r["part_sup3_atr"]), pct(r["part_sup5_atr"]), sg(r["moy_top10_atr"], 2), sg(r["esperance_atr"], 3)])
    out.append(table(["Configuration", "P50", "P75", "P90", "P95", "P99", "≥ +3 ATR", "≥ +5 ATR", "Top 10 %", "Espérance"], rows))
    return "\n\n".join(out)


def section_plateau(ix) -> str:
    out = ["## F. Plateau d'horizon (cooldown)",
           "Cellule : espérance ATR [IC] ; PnL ; MDD ; Calmar, à 0,25 % par ATR. Puis, à 10 bps : espérance ATR ; PnL."]
    rows = []
    for c in ["RE-1"] + [c for p in PERIMETRES for c in cfgs(p)]:
        cells = []
        for H in HORIZONS:
            r, r10 = ix(c, H), ix(c, H, fee=10.0)
            cells.append(f"{ci(r['esperance_atr'], r['esperance_atr_lo'], r['esperance_atr_hi'], 3)} ; "
                         f"{spct(r['pnl_compose_r25'])} ; {pct(r['mdd_valorise_r25'], 1)} ; {fr(r['calmar_r25'], 2)} ‖ "
                         f"10 bps : {sg(r10['esperance_atr'], 3)} ; {spct(r10['pnl_compose_r25'])}")
        rows.append([nom(c)] + cells)
    out.append(table(["Configuration"] + [f"H = {H}" for H in HORIZONS], rows))
    return "\n\n".join(out)


def section_annees(ann) -> str:
    out = [f"## G. Stabilité annuelle à H = {H_MAIN} (cooldown)",
           "Effet apparié BE − RE-1 par année d'entrée (ATR par trade), puis PnL composé par année à 0,25 % par ATR (5 bps)."]
    a = ann[(ann.H == H_MAIN) & (ann["mode"] == "cooldown") & (ann.frais_bps == 5.0)]
    rows = []
    for c in ["RE-1"] + [c for p in PERIMETRES for c in cfgs(p)]:
        g = a[a.configuration == c].set_index("annee")
        eff = [sg(g.effet_atr_vs_RE1.get(y), 3) if c != "RE-1" else "—" for y in YEARS]
        rows.append([nom(c)] + eff + [" ; ".join(spct(g.pnl_compose_r25.get(y), 0) for y in YEARS)])
    out.append(table(["Configuration"] + [str(y) for y in YEARS] + ["PnL par année"], rows))
    return "\n\n".join(out)


def section_tp(meta) -> str:
    tp = meta["take_profit"]
    out = [f"## H. Take-profit fixe : borne optimiste (décision du porteur, vérifiée) et excursion favorable de RE-1",
           f"Trades de RE-1 à H = {H_MAIN}, cooldown. Espérance nette par trade de RE-1 : {sg(tp['re1_esp_5'], 3)} ATR à 5 bps, "
           f"{sg(tp['re1_esp_10'], 3)} à 10 bps ; P90 du résultat net : {sg(tp['re1_q90_5'], 2)} ATR (5 bps).",
           "Borne optimiste : sortie à +TP · ATR14(t) dès que la MFE atteint TP, résultat de RE-1 sinon. Fenêtre complète : "
           "MFE sur t + 1 … t + H, stops ignorés (TP toujours touché avant le stop) ; avant sortie : MFE jusqu'à la sortie "
           "de RE-1, barre du stop comprise (TP prioritaire dans la barre)."]
    rows = []
    for r in tp["tp"]:
        rows.append([fr(r["frais_bps"], 0) + " bps", f"TP = {fr(r['tp'], 0)} ATR",
                     f"{pct(r['part_full'], 1)} ; {sg(r['esp_full'], 3)} ; {sg(r['re1_touches_full'], 2)}",
                     f"{pct(r['part_avant'], 1)} ; {sg(r['esp_avant'], 3)} ; {sg(r['re1_touches_avant'], 2)}"])
    out.append(table(["Frais", "Take-profit", "Fenêtre complète : touchés ; espérance ; RE-1 des touchés",
                      "Avant sortie : touchés ; espérance ; RE-1 des touchés"], rows))
    rows = []
    mf = pd.DataFrame(tp["mfe"])
    for m in M_GRID:
        cells = []
        for w in ("full", "avant"):
            r = mf[(mf.m == m) & (mf.fenetre == w)].iloc[0]
            cells.append(f"{pct(r.part_atteint, 1)} ; {pct(r.part_atteint_perdant, 1)} ({pct(r.part_perdants_parmi_atteints, 0)}) ; "
                         f"{sg(r.perte_moyenne, 2)}")
        rows.append([f"m = {fr(m, 1)}"] + cells)
    out.append("**Excursion favorable des trades de RE-1** — cellule : part des trades dont la MFE atteint m ATR ; part "
               "qui l'atteint puis finit en perte nette à 5 bps (part parmi ceux qui l'atteignent) ; perte nette moyenne de "
               "ces derniers (ATR).\n\n" + table(["Seuil", "MFE26, fenêtre complète", "MFE avant la sortie de RE-1"], rows))
    return "\n\n".join(out)


def section_reouverture(ix) -> str:
    out = [f"## I. Annexe — réouverture immédiate après un stop ou un break-even (H = {H_MAIN}, 5 bps)",
           "Débloqués : trades ouverts grâce à une sortie anticipée, absents de la lecture cooldown de la même configuration ; "
           "perdus : trades de la lecture cooldown masqués par un débloqué."]
    rows = []
    for c in ["RE-1"] + [c for p in PERIMETRES for c in cfgs(p)]:
        cd, d = ix(c), ix(c, mode="réouverture")
        rows.append([nom(c), f"{n_fr(cd['n_trades'])} ; {n_fr(d['n_trades'])}",
                     f"{n_fr(d['n_debloques'])} ; {sg(d['esperance_debloques_atr'], 3)}",
                     f"{n_fr(d['n_perdus'])} ; {sg(d['esperance_perdus_atr'], 3)}",
                     f"{sg(cd['esperance_atr'], 3)} ; {ci(d['esperance_atr'], d['esperance_atr_lo'], d['esperance_atr_hi'], 3)}",
                     f"{spct(cd['pnl_compose_r25'])} ; {spct(d['pnl_compose_r25'])}",
                     f"{pct(cd['mdd_valorise_r25'], 1)} ; {pct(d['mdd_valorise_r25'], 1)}",
                     f"{fr(cd['calmar_r25'], 2)} ; {fr(d['calmar_r25'], 2)}"])
    out.append(table(["Configuration", "Trades : cooldown ; réouverture", "Débloqués : n ; esp. ATR", "Perdus : n ; esp. ATR",
                      "Esp. ATR : cooldown ; réouverture [IC]", "PnL : cooldown ; réouverture", "MDD : cooldown ; réouverture",
                      "Calmar : cooldown ; réouverture"], rows))
    return "\n\n".join(out)


def write_report(res, ann, meta) -> None:
    ix = Index(res)
    parts = [section_controles(meta), section_h26(ix), section_effets(ix), section_mecanique(ix), section_queue(ix),
             section_plateau(ix), section_annees(ann), section_tp(meta), section_reouverture(ix)]
    narr = HERE / "narratif_C03.md"
    head = narr.read_text(encoding="utf-8") if narr.exists() else "# EXP-C03\n\n*(narratif à rédiger)*\n"
    (HERE / "rapport_C03.md").write_text(
        head.rstrip() + "\n\n---\n\n# Annexes chiffrées (générées par `run_C03.py`)\n\n" + "\n\n".join(parts) + "\n",
        encoding="utf-8")


# ── Figures ─────────────────────────────────────────────────────────────────────
COLORS = {"V1": "#1f77b4", "V2": "#d62728", "V3": "#2ca02c"}


def _save(fig, name: str) -> None:
    for k in range(6):
        try:
            fig.savefig(FIG / name, dpi=130)
            return
        except OSError:
            if k == 5:
                raise
            time.sleep(0.5)


def fig_effets(ix) -> None:
    fig, axes = plt.subplots(2, 3, figsize=(19, 10), sharex=True, sharey="row")
    x = np.array(M_GRID)
    cols = {0: ("effet_atr_vs_RE1", "effet_atr_lo_vs_RE1", "effet_atr_hi_vs_RE1", 1.0),
            1: ("dmdd_sorties", "dmdd_lo", "dmdd_hi", 100.0)}
    for i, (c, clo, chi, k) in cols.items():
        for ax, H in zip(axes[i], HORIZONS):
            for j, p in enumerate(PERIMETRES):
                rs = [ix(f"{p} m{m:g}", H) for m in M_GRID]
                y, lo, hi = (k * np.array([r[v] for r in rs]) for v in (c, clo, chi))
                xx = x + (j - 1) * 0.06
                ax.vlines(xx, lo, hi, color=COLORS[p], lw=0.9)          # IC (ligne 1) ; plage des tirages (ligne 2)
                ax.plot(xx, y, color=COLORS[p], marker="o", ms=5, lw=1.5, label=NOMS_P[p])
            ax.axhline(0, color="0.3", lw=0.8)
            ax.set_xticks(M_GRID)
            ax.set_title(f"H = {H}", fontsize=10)
            ax.grid(alpha=0.3, lw=0.5)
    for ax in axes[1]:
        ax.set_xlabel("Seuil d'activation m (ATR14(t))", fontsize=9)
    axes[0, 0].set_ylabel("Effet sur l'espérance, BE − RE-1 (ATR14(t) par trade), IC 95 %", fontsize=9)
    axes[1, 0].set_ylabel("Effet sur le MDD aux sorties, 5 bps (points ; > 0 : moins profond) ;\nécart observé et plage "
                          "P2,5-P97,5 sur les chemins réordonnés par mois", fontsize=9)
    axes[0, 0].legend(fontsize=8, frameon=False)
    fig.suptitle("EXP-C03 — Effet apparié du break-even différé sur les entrées de RE-1 (lecture cooldown)", fontsize=11)
    fig.tight_layout()
    _save(fig, "fig1_effet_apparie_BE.png")
    plt.close(fig)


def fig_mecanique(ix) -> None:
    fig, axes = plt.subplots(1, 3, figsize=(19, 5.8), sharey=True)
    x = np.arange(len(M_GRID))
    for ax, p in zip(axes, PERIMETRES):
        rs = [ix(f"{p} m{m:g}") for m in M_GRID]
        ax.bar(x, [r["gain_sauves"] for r in rs], color="#2ca02c", alpha=0.8, label="gain sur les trades sauvés")
        ax.bar(x, [r["cout_coupes"] for r in rs], color="#d62728", alpha=0.8, label="coût sur les trades coupés")
        ax.plot(x, [r["effet_atr_vs_RE1"] for r in rs], "kD", ms=6, label="effet net")
        ax.axhline(0, color="0.3", lw=0.8)
        ax.set_xticks(x, [fr(m, 1) for m in M_GRID])
        ax.set_xlabel("Seuil d'activation m (ATR14(t))", fontsize=9)
        ax.set_title(NOMS_P[p], fontsize=10)
        ax.grid(alpha=0.3, lw=0.5, axis="y")
    axes[0].set_ylabel("ATR14(t) par trade, sur toutes les entrées de RE-1", fontsize=9)
    axes[0].legend(fontsize=8, frameon=False)
    fig.suptitle(f"EXP-C03 — Ce que le break-even sauve et ce qu'il coupe (H = {H_MAIN}, cooldown)", fontsize=11)
    fig.tight_layout()
    _save(fig, "fig2_mecanique_BE_H26.png")
    plt.close(fig)


def fig_queue(trades, atr_bps) -> None:
    fig, axes = plt.subplots(1, 3, figsize=(19, 5.8), sharey=True)
    grid = np.linspace(0, 15, 301)
    base = net_atr(trades[("RE-1", H_MAIN, "cooldown")], atr_bps, 5.0)
    shades = {1.0: 0.35, 2.0: 0.65, 4.0: 1.0}
    for ax, p in zip(axes, PERIMETRES):
        ax.plot(grid, [(base >= g).mean() for g in grid], color="k", lw=2, label="RE-1")
        for m, al in shades.items():
            v = net_atr(trades[(f"{p} m{m:g}", H_MAIN, "cooldown")], atr_bps, 5.0)
            ax.plot(grid, [(v >= g).mean() for g in grid], color=COLORS[p], alpha=al, lw=1.5, label=f"BE m = {fr(m, 0)}")
        ax.set_yscale("log")
        ax.set_xlabel("Résultat net par trade (ATR14(t), 5 bps)", fontsize=9)
        ax.set_title(NOMS_P[p], fontsize=10)
        ax.grid(alpha=0.3, lw=0.5, which="both")
        ax.legend(fontsize=8, frameon=False)
    axes[0].set_ylabel("Part des trades au-dessus du seuil (échelle log)", fontsize=9)
    fig.suptitle(f"EXP-C03 — Queue droite des trades de RE-1 avec et sans break-even (H = {H_MAIN}, cooldown)", fontsize=11)
    fig.tight_layout()
    _save(fig, "fig3_queue_droite_H26.png")
    plt.close(fig)


def fig_pnl(ix) -> None:
    fig, axes = plt.subplots(2, 2, figsize=(15, 9), sharex=True)
    for i, fee in enumerate(FEES):
        ref = ix("RE-1", fee=fee)
        for j, (k, lab) in enumerate((("pnl_compose_r25", "PnL composé, 0,25 % par ATR (%)"),
                                      ("mdd_valorise_r25", "Max drawdown valorisé (%)"))):
            ax = axes[i, j]
            ax.axhline(100 * ref[k], color="k", ls="--", lw=1.2, label="RE-1")
            for p in PERIMETRES:
                ax.plot(M_GRID, [100 * ix(f"{p} m{m:g}", fee=fee)[k] for m in M_GRID], color=COLORS[p], marker="o",
                        ms=5, lw=1.5, label=NOMS_P[p])
            ax.set_ylabel(f"{fr(fee, 0)} bps — {lab}", fontsize=9)
            ax.grid(alpha=0.3, lw=0.5)
            ax.set_xticks(M_GRID)
    for ax in axes[1]:
        ax.set_xlabel("Seuil d'activation m (ATR14(t))", fontsize=9)
    axes[0, 0].legend(fontsize=8, frameon=False)
    fig.suptitle(f"EXP-C03 — PnL et drawdown selon le seuil du break-even (H = {H_MAIN}, cooldown)", fontsize=11)
    fig.tight_layout()
    _save(fig, "fig4_pnl_drawdown_H26.png")
    plt.close(fig)


# ── Programme ───────────────────────────────────────────────────────────────────
def main() -> None:
    if "--rapport" in sys.argv:
        res, ann = pd.read_csv(HERE / "resultats_C03.csv"), pd.read_csv(HERE / "annuel_C03.csv")
        write_report(res, ann, json.loads((HERE / "controles_C03.json").read_text(encoding="utf-8")))
        print(f"rapport_C03.md régénéré dans {HERE}")
        return
    t0 = time.time()
    df, bars = load_dev_bars(), load_bars_dev()
    if not np.array_equal(df[["open", "high", "low", "close"]].to_numpy(), bars[["open", "high", "low", "close"]].to_numpy()):
        raise SystemExit("barres différentes entre anatomy et estimand : arrêt")
    atlas, f, idx, atr = build_atlas(df)
    ref = pd.read_csv(ROOT / "experiments" / "A01" / "atlas_signaux.csv", usecols=["bar_index", "direction"])
    if not (np.array_equal(ref.bar_index, atlas.bar_index) and np.array_equal(ref.direction, atlas.direction)):
        raise SystemExit("univers différent de experiments/A01/atlas_signaux.csv : arrêt")
    meta = {"ancre": C2B.check_anchor(bars, f)}
    atr_bps = pd.Series(atlas.atr14_bps.to_numpy(), index=atlas.bar_index.to_numpy())
    masks = C2B.full_masks(atlas)
    eng = EngineBE(bars, atlas, atr, masks)
    print(f"contrôles préalables passés ({time.time() - t0:.0f} s)")
    rows, ann, trades = run_grid(bars, atr_bps, eng)
    res, ann = pd.DataFrame(rows), pd.DataFrame(ann)
    meta["controles"] = check_controls(res, bars, atr_bps, eng, C2B.Engine(bars, atlas, atr, masks))
    meta["take_profit"] = tp_bound(trades[("RE-1", H_MAIN, "cooldown")], bars, eng, atr_bps, H_MAIN)
    meta["duree_s"] = round(time.time() - t0)
    res.to_csv(HERE / "resultats_C03.csv", index=False, float_format="%.6g")
    ann.to_csv(HERE / "annuel_C03.csv", index=False, float_format="%.6g")
    (HERE / "controles_C03.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
    FIG.mkdir(parents=True, exist_ok=True)
    ix = Index(res)
    fig_effets(ix)
    fig_mecanique(ix)
    fig_queue(trades, atr_bps)
    fig_pnl(ix)
    write_report(res, ann, meta)
    print(f"C03 : {len(res)} lignes de résultats en {meta['duree_s']} s ; rapport, tableaux et figures dans {HERE}")


if __name__ == "__main__":
    main()
