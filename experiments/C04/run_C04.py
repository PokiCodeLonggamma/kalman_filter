"""EXP-C04 — filtre de contexte macro : veto des signaux contre la tendance de fond, sur RE-1.

Usage, depuis la racine du dépôt : python experiments/C04/run_C04.py [--rapport]
  --rapport : régénère seulement rapport_C04.md depuis les CSV et controles_C04.json.
Sorties dans experiments/C04/ : resultats_C04.csv, annuel_C04.csv, controles_C04.json, figures/*.png,
rapport_C04.md (= narratif_C04.md rédigé à la main, suivi des annexes chiffrées générées ici).

Contrôle : RE-1 (R2 hors nis_z_100 Q4, F2b sans stop, F3 SL-B à l'extremum, H = 26, cooldown, pyramiding 0).
Facteur unique : veto directionnel à l'entrée (`context.counter_trend`) ; Long seulement si la tendance est
haussière, Short seulement si elle est baissière. Tendance lue à la clôture de la barre du signal :
- V1 : close > EMA(close, 200) (barres 30 min) ; V2 : close > EMA(close, 50) ;
- V3 : signe de x1 du filtre v2.1 sur bougies 4 h entièrement clôturées (`context.htf_kalman_trend`), valide après
  300 bougies (avant : pas de veto). R0 = 1 000 sur 30 min écarté à la conception : régimes de x1 de 19 barres en
  médiane contre 11 pour le filtre de base, pas un horizon macro.
Deux lectures : séquentielle (un signal vétoé n'existe pas, la position reste libre : lecture principale) et figée
(les trades de RE-1 moins les trades vétoés : un signal vétoé impose le même cooldown que s'il avait été pris,
effet pur du veto, sans effet de chaîne). Frais 5 et 10 bps séparés ; capital à 0,25 % par ATR14(t) ; IC 95 % par
grappes mensuelles, 2 000 tirages ; chemins réordonnés par mois (I-M10) ; RE-1 réduit au même MDD (I-M11).
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
from context import counter_trend, ema_trend, htf_kalman_trend  # noqa: E402
from envelope import equity_curve_sized, risk_weights, route_levels, stop_trades  # noqa: E402
from envelope.metrics import _boot_mean, _cluster_counts, _entry_month  # noqa: E402
from estimand import load_bars_dev  # noqa: E402
from estimand.stoploss import TRADE_COLUMNS  # noqa: E402


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


C3A = _load("run_C03_approfondi", ROOT / "experiments" / "C03" / "run_C03_approfondi.py")
C3, C2B = C3A.C3, C3A.C2B
fr, sg, pct, spct, n_fr, ci, sci, table = C2B.fr, C2B.sg, C2B.pct, C2B.spct, C2B.n_fr, C2B.ci, C2B.sci, C2B.table

FIG = HERE / "figures"
FEES = (5.0, 10.0)
YEARS = list(range(2020, 2026))
N_BOOT = C2B.N_BOOT
N_YEARS = 6.0
H_MAIN = 26
HORIZONS = (24, 26, 28)
RE1_RULES = {"F2b": None, "F3": ("SL-B", 0.0)}
VARIANTES = {"V1": "V1 — EMA 200", "V2": "V2 — EMA 50", "V3": "V3 — Kalman 4 h"}
LECTURES = ("séquentielle", "figée")
C02BIS_CSV = ROOT / "experiments" / "C02bis" / "resultats_C02bis.csv"


def nom(cfg: str, lecture: str | None = None) -> str:
    if cfg == "RE-1":
        return "RE-1 (contrôle)"
    return VARIANTES[cfg] + ("" if lecture in (None, "séquentielle") else " (figée)")


# ── Moteur ──────────────────────────────────────────────────────────────────────
class Ctx:
    """Signaux candidats de RE-1 (R2 hors Q4), stop de RE-1 routé, tendance de chaque variante au signal, veto."""

    def __init__(self, bars, atlas, atr, masks):
        r2 = masks["R2"]
        self.bars = bars
        self.t = atlas.bar_index.to_numpy()[r2]
        self.s = atlas.direction.to_numpy()[r2]
        self.fam = np.where(masks["F3"][r2], "F3", "F2b")
        a = np.asarray(atr, dtype=float)[self.t]
        self.level = route_levels(bars, self.t, self.s, a, atlas.prev_seg_len.to_numpy()[r2], self.fam, RE1_RULES,
                                  C2B.FLOOR)
        self.fam_s = pd.Series(self.fam, index=self.t)
        close = bars.close.to_numpy(dtype=float)
        self.k4 = htf_kalman_trend(bars, hours=4)
        self.trend_bars = {"V1": ema_trend(close, 200), "V2": ema_trend(close, 50), "V3": self.k4.trend.to_numpy()}
        self.trend = {v: tr[self.t] for v, tr in self.trend_bars.items()}
        self.veto = {v: counter_trend(self.s, tr) for v, tr in self.trend.items()}

    def run(self, H: int, veto: np.ndarray | None = None) -> pd.DataFrame:
        keep = np.ones(len(self.t), dtype=bool) if veto is None else ~veto
        return stop_trades(self.bars, self.t[keep], self.s[keep], H, self.level[keep], dynamic=False)

    def vetoed_signals(self, v: str) -> set:
        return set(self.t[self.veto[v]])


def net_atr(tr, atr_bps, fee) -> np.ndarray:
    return (tr.ret_gross_bps.to_numpy(dtype=float) - fee) / atr_bps.reindex(tr.signal_bar.to_numpy()).to_numpy()


def q(b, p) -> float:
    return float(np.nanpercentile(b, p))


# ── Trades contre-tendance de RE-1 ──────────────────────────────────────────────
def split(re1, vetoed_sigs: set, ctx: Ctx, bars, atr_bps) -> dict:
    """Trades de RE-1 dont le signal serait vétoé (contre-tendance) contre les autres (alignés) : espérances, IC et
    écart aligné − contre-tendance sur les mêmes tirages de mois, par sous-famille et par sens ; queue droite."""
    cv = re1.signal_bar.isin(vetoed_sigs).to_numpy()
    fam = ctx.fam_s.reindex(re1.signal_bar.to_numpy()).to_numpy()
    side = re1.side.to_numpy()
    w, inv, g = _cluster_counts(_entry_month(re1, bars), N_BOOT, 0)
    out = {"n": len(re1), "n_contre": int(cv.sum()), "part_contre": float(cv.mean())}
    groups = {"tous": np.ones(len(re1), bool), "F2b": fam == "F2b", "F3": fam == "F3", "Long": side == 1, "Short": side == -1}
    for fee in FEES:
        v = net_atr(re1, atr_bps, fee)
        for gname, gm in groups.items():
            a, c = gm & ~cv, gm & cv
            ba, bc = _boot_mean(w, inv, g, v, a), _boot_mean(w, inv, g, v, c)
            k = f"{gname}_{fee:g}"
            out.update({f"n_aligne_{k}": int(a.sum()), f"n_contre_{k}": int(c.sum()),
                        f"esp_aligne_{k}": float(v[a].mean()) if a.any() else np.nan,
                        f"esp_aligne_lo_{k}": q(ba, 2.5), f"esp_aligne_hi_{k}": q(ba, 97.5),
                        f"esp_contre_{k}": float(v[c].mean()) if c.any() else np.nan,
                        f"esp_contre_lo_{k}": q(bc, 2.5), f"esp_contre_hi_{k}": q(bc, 97.5),
                        f"ecart_{k}": float(v[a].mean() - v[c].mean()) if a.any() and c.any() else np.nan,
                        f"ecart_lo_{k}": q(ba - bc, 2.5), f"ecart_hi_{k}": q(ba - bc, 97.5)})
    base = net_atr(re1, atr_bps, 5.0)
    top, big3 = base >= np.quantile(base, 0.9), base >= 3.0
    top20 = np.zeros(len(base), bool)
    top20[np.argsort(base)[-20:]] = True
    for name, sel in (("top10", top), ("sup3", big3), ("top20", top20)):
        out.update({f"n_{name}": int(sel.sum()), f"n_{name}_contre": int((sel & cv).sum()),
                    f"part_{name}_contre": float((sel & cv).sum() / sel.sum()),
                    f"contribution_{name}_contre": float(base[sel & cv].sum() / base[sel].sum())})
    out["taux_top10_contre"] = float((top & cv).sum() / cv.sum()) if cv.any() else np.nan
    out["taux_top10_aligne"] = float((top & ~cv).sum() / (~cv).sum())
    for name, sel in (("contre", cv), ("aligne", ~cv)):
        out.update({f"p10_{name}": q(base[sel], 10), f"med_{name}": q(base[sel], 50), f"p90_{name}": q(base[sel], 90)})
    return out


def decompose(filt, re1, vetoed_sigs: set, atr_bps, fee) -> dict:
    """Lecture séquentielle contre RE-1 : trades vétoés, trades alignés perdus par effet de chaîne, trades ajoutés
    (signaux libérés par un veto). Bilan refermé : filtrée = RE-1 − vétoés − perdus + ajoutés."""
    sf, sr = set(filt.signal_bar), set(re1.signal_bar)
    vet = re1[re1.signal_bar.isin(vetoed_sigs)]
    lost = re1[~re1.signal_bar.isin(vetoed_sigs) & ~re1.signal_bar.isin(sf)]
    add = filt[~filt.signal_bar.isin(sr)]
    s = {k: net_atr(x, atr_bps, fee) for k, x in (("f", filt), ("r", re1), ("v", vet), ("l", lost), ("a", add))}
    if not np.isclose(s["f"].sum(), s["r"].sum() - s["v"].sum() - s["l"].sum() + s["a"].sum(), rtol=1e-9, atol=1e-9):
        raise SystemExit("décomposition séquentielle non refermée : arrêt")
    return {"n_vetoes": len(vet), "esp_vetoes": float(s["v"].mean()) if len(vet) else np.nan, "n_perdus": len(lost),
            "esp_perdus": float(s["l"].mean()) if len(lost) else np.nan, "n_ajoutes": len(add),
            "esp_ajoutes": float(s["a"].mean()) if len(add) else np.nan}


# ── Risque de chemin et taille ──────────────────────────────────────────────────
def paired_paths(tr_b, tr_a, bars, atr_bps, fee, n_boot: int = N_BOOT, seed: int = 0) -> dict:
    """Variante (b) contre RE-1 (a) sur les mêmes chemins : mois civils d'entrée tirés avec remise (générateur de
    `_cluster_counts`), trades de chaque configuration dans ces mois. MDD aux sorties et Calmar sur 6 ans."""
    def months(tr):
        tt = bars.time.iloc[tr.entry_bar.to_numpy()]
        return (tt.dt.year * 12 + tt.dt.month).to_numpy()
    ma, mb = months(tr_a), months(tr_b)
    allm = np.unique(np.r_[ma, mb])
    ia, ib = np.searchsorted(allm, ma), np.searchsorted(allm, mb)
    ga = [np.flatnonzero(ia == k) for k in range(len(allm))]
    gb = [np.flatnonzero(ib == k) for k in range(len(allm))]
    ra, rb = C3.sized_returns(tr_a, atr_bps, fee), C3.sized_returns(tr_b, atr_bps, fee)
    rng = np.random.default_rng(seed)
    dm, dc = np.empty(n_boot), np.empty(n_boot)

    def stats(r):
        mdd = C3.mdd_exits(r)
        return mdd, np.expm1(np.log1p(r).sum() / N_YEARS) / abs(mdd)
    for i in range(n_boot):
        d = rng.integers(0, len(allm), len(allm))
        oa = np.concatenate([ga[k] for k in d]).astype(int)
        ob = np.concatenate([gb[k] for k in d]).astype(int)
        (m_a, c_a), (m_b, c_b) = stats(ra[oa]), stats(rb[ob])
        dm[i], dc[i] = m_b - m_a, c_b - c_a
    (m_a, c_a), (m_b, c_b) = stats(ra), stats(rb)
    return {"dmdd_obs": m_b - m_a, "dmdd_lo": q(dm, 2.5), "dmdd_hi": q(dm, 97.5), "p_mdd": float((dm > 0).mean()),
            "dcalmar_obs": c_b - c_a, "dcalmar_lo": q(dc, 2.5), "dcalmar_hi": q(dc, 97.5), "p_calmar": float((dc > 0).mean())}


def size_check(filt, re1, bars, atr_bps, fee) -> dict:
    """I-M11 : RE-1 réduit en taille jusqu'au MDD valorisé de la variante ; écart de PnL annualisé à MDD égal."""
    v = C3A.sized_path(filt, bars, atr_bps, fee, C2B.RISK)
    r = C3A.size_matched(re1, bars, atr_bps, fee, v["mdd"])
    return {"taille_cagr_variante": v["cagr"], "taille_mdd": v["mdd"], "taille_re1_risque_bps": r["risque_bps"],
            "taille_re1_cagr": r["cagr"], "taille_ecart_cagr": v["cagr"] - r["cagr"],
            "sous_pic_variante": v["sous_pic_jours"], "sous_pic_re1_reduit": r["sous_pic_jours"]}


# ── Grille ──────────────────────────────────────────────────────────────────────
def run_grid(ctx: Ctx, bars, atr_bps) -> tuple[list, list, dict, dict]:
    rows, ann, trades, splits = [], [], {}, {}
    for H in HORIZONS:
        re1 = ctx.run(H)
        trades[("RE-1", "séquentielle", H)] = re1
        runs = [("RE-1", "séquentielle", re1, len(ctx.t), {})]
        for v in VARIANTES:
            vs = ctx.vetoed_signals(v)
            filt = ctx.run(H, ctx.veto[v])
            froz = re1[~re1.signal_bar.isin(vs)].reset_index(drop=True)
            trades[(v, "séquentielle", H)], trades[(v, "figée", H)] = filt, froz
            runs += [(v, "séquentielle", filt, int((~ctx.veto[v]).sum()), {"vs": vs}),
                     (v, "figée", froz, int((~ctx.veto[v]).sum()), {"vs": vs})]
            if H == H_MAIN:
                splits[v] = split(re1, vs, ctx, bars, atr_bps)
        for cfg, lec, tr, n_cand, extra in runs:
            for fee in FEES:
                m, y = C2B.metrics(tr, bars, atr_bps, fee, n_cand, ctx.fam_s)
                row = {"configuration": cfg, "lecture": lec, "H": H, "frais_bps": fee, **m}
                if cfg != "RE-1":
                    row["n_signaux_vetoes"] = int(ctx.veto[cfg].sum())
                    if lec == "séquentielle":
                        row.update(decompose(tr, re1, extra["vs"], atr_bps, fee))
                    row.update(paired_paths(tr, re1, bars, atr_bps, fee))
                    if H == H_MAIN:
                        row.update(size_check(tr, re1, bars, atr_bps, fee))
                rows.append(row)
                ann += [{"configuration": cfg, "lecture": lec, "H": H, "frais_bps": fee, **r} for r in y.to_dict("records")]
        print(f"  H = {H} : fait")
    return rows, ann, trades, splits


def describe_trends(ctx: Ctx) -> dict:
    """Durée des régimes de tendance (barres 30 min), part haussière, validité, sur les barres de signaux possibles."""
    out = {}
    first = int(ctx.t.min())
    for v, tr in ctx.trend_bars.items():
        x = tr[first:]
        ok = x != 0
        ch = np.flatnonzero(np.diff(x[ok]) != 0)
        runs = np.diff(ch)
        out[v] = {"duree_mediane": float(np.median(runs)), "duree_moyenne": float(runs.mean()),
                  "part_haussiere": float((x[ok] == 1).mean()), "part_indefinie": float((~ok).mean()),
                  "signaux_indefinis": int((ctx.trend[v] == 0).sum()), "signaux_vetoes": int(ctx.veto[v].sum()),
                  "part_signaux_vetoes": float(ctx.veto[v].mean()),
                  "vetoes_long": int((ctx.veto[v] & (ctx.s == 1)).sum()), "vetoes_short": int((ctx.veto[v] & (ctx.s == -1)).sum())}
    return out


def check_re1(ctx: Ctx, bars, atr_bps, eng_c2b, res: pd.DataFrame) -> dict:
    """Bloquant : RE-1 = RE-1 de C02bis, trade par trade (H24, 26, 28) et dans resultats_C02bis.csv (5 et 10 bps)."""
    ref = pd.read_csv(C02BIS_CSV)
    cols = ["n_trades", "esperance_bps", "esperance_atr", "esperance_atr_lo", "esperance_atr_hi", "pnl_compose",
            "mdd_valorise", "pf", "wr", "pnl_compose_r25", "mdd_valorise_r25", "calmar_r25"]
    worst, n = 0.0, 0
    for H in HORIZONS:
        a, (b, _) = ctx.run(H), eng_c2b.run("R2", RE1_RULES, H, False)
        if not a[TRADE_COLUMNS].equals(b[TRADE_COLUMNS]):
            raise SystemExit(f"RE-1 H{H} : trades différents de C02bis : arrêt")
        for fee in FEES:
            r = res[(res.configuration == "RE-1") & (res.H == H) & (res.frais_bps == fee)].iloc[0]
            g = ref[(ref.variante_seuils == C2B.ENTIER) & (ref.configuration == "RE-1") & (ref.H == H)
                    & (ref["mode"] == "cooldown") & (ref.frais_bps == fee)].iloc[0]
            for c in cols:
                x, y = float(r[c]), float(g[c])
                if not np.isclose(x, y, rtol=1e-5, atol=1e-9):
                    raise SystemExit(f"RE-1 H{H} {fee:g} bps : {c} différent de C02bis ({x} contre {y}) : arrêt")
                worst = max(worst, abs(x - y) / max(abs(y), 1e-12))
            n += 1
    return {"lignes_comparees": n, "ecart_relatif_max": worst}


# ── Rapport ─────────────────────────────────────────────────────────────────────
class Index:
    def __init__(self, res):
        self.d = {(r["configuration"], r["lecture"], int(r["H"]), float(r["frais_bps"])): r for r in res.to_dict("records")}

    def __call__(self, cfg, lecture="séquentielle", H=H_MAIN, fee=5.0) -> dict:
        return self.d[(cfg, lecture, int(H), float(fee))]


def section_A(meta) -> str:
    a, c = meta["ancre"], meta["re1"]
    rows = [["Ancre P6.5d", f"{n_fr(a['sans_stop']['n_trades'])} et {n_fr(a['stop_2_5']['n_trades'])} trades identiques"],
            ["RE-1 = RE-1 de C02bis", f"trades identiques à H24, 26 et 28 ; {c['lignes_comparees']} lignes de métriques "
             f"identiques à resultats_C02bis.csv (écart relatif max {sci(c['ecart_relatif_max'])})"],
            ["Décomposition séquentielle", "filtrée = RE-1 − vétoés − perdus par chaîne + ajoutés, refermée à 10⁻⁹ près "
             "pour chaque variante, chaque horizon et chaque niveau de frais"],
            ["Causalité des tendances", "EMA récursive et Kalman 4 h lus à la clôture de la barre du signal ; bougie 4 h lue "
             "seulement une fois close ; tests de troncature (tests/test_context.py)"],
            ["Période", "2020-01 → 2025-12 ; aucune barre de 2026 lue ; ETH et XRP non lus"]]
    return "## A. Contrôles bloquants\n\n" + table(["Contrôle", "Résultat"], rows)


def section_B(meta) -> str:
    rows = []
    for v, d in meta["tendances"].items():
        rows.append([VARIANTES[v], fr(d["duree_mediane"], 0), fr(d["duree_moyenne"], 1), pct(d["part_haussiere"]),
                     f"{n_fr(d['signaux_indefinis'])}",
                     f"{n_fr(d['signaux_vetoes'])} ({pct(d['part_signaux_vetoes'])}) : {n_fr(d['vetoes_long'])} Long, "
                     f"{n_fr(d['vetoes_short'])} Short"])
    return ("## B. Définitions de tendance\n\nDurées des régimes en barres de 30 min, de la barre du premier signal à fin 2025 "
            "(tendance définie). Signaux : les 1 452 candidats de RE-1 (R2 hors Q4).\n\n"
            + table(["Tendance", "Régime médian", "Régime moyen", "Part haussière", "Signaux sans tendance (pas de veto)",
                     "Signaux vétoés"], rows))


def section_C(meta) -> str:
    out = [f"## C. Trades de RE-1 contre la tendance (H = {H_MAIN}, cooldown)",
           "Contre-tendance : trades de RE-1 dont le signal serait vétoé. Espérance nette par trade en ATR [IC 95 % par "
           "grappes mensuelles] ; écart aligné − contre-tendance sur les mêmes tirages."]
    for fee in FEES:
        rows = []
        for v, s in meta["splits"].items():
            for gname in ("tous", "F2b", "F3", "Long", "Short"):
                k = f"{gname}_{fee:g}"
                rows.append([VARIANTES[v], gname, f"{n_fr(s[f'n_aligne_{k}'])} ; {n_fr(s[f'n_contre_{k}'])}",
                             ci(s[f"esp_aligne_{k}"], s[f"esp_aligne_lo_{k}"], s[f"esp_aligne_hi_{k}"], 3),
                             ci(s[f"esp_contre_{k}"], s[f"esp_contre_lo_{k}"], s[f"esp_contre_hi_{k}"], 3),
                             ci(s[f"ecart_{k}"], s[f"ecart_lo_{k}"], s[f"ecart_hi_{k}"], 3)])
        out.append(f"**{fr(fee, 0)} bps**\n\n" + table(["Tendance", "Groupe", "Trades : alignés ; contre", "Alignés",
                                                        "Contre-tendance", "Écart aligné − contre"], rows))
    rows = []
    for v, s in meta["splits"].items():
        rows.append([VARIANTES[v], f"{n_fr(s['n_contre'])} ({pct(s['part_contre'])})",
                     f"{n_fr(s['n_top10_contre'])}/{n_fr(s['n_top10'])} ({pct(s['part_top10_contre'])}) ; "
                     f"{pct(s['contribution_top10_contre'])} de leur contribution",
                     f"{n_fr(s['n_sup3_contre'])}/{n_fr(s['n_sup3'])} ({pct(s['part_sup3_contre'])})",
                     f"{n_fr(s['n_top20_contre'])}/20",
                     f"{sg(s['p10_contre'], 2)} / {sg(s['med_contre'], 2)} / {sg(s['p90_contre'], 2)}",
                     f"{sg(s['p10_aligne'], 2)} / {sg(s['med_aligne'], 2)} / {sg(s['p90_aligne'], 2)}"])
    out.append("**Queue droite** — gros gagnants de RE-1 (5 bps) parmi les trades contre-tendance ; distribution P10 / "
               "médiane / P90 du résultat net (ATR).\n\n"
               + table(["Tendance", "Trades contre-tendance (part)", "Décile supérieur de RE-1 contre-tendance",
                        "Gagnants ≥ +3 ATR contre-tendance", "20 meilleurs trades contre-tendance",
                        "Contre : P10 / méd. / P90", "Alignés : P10 / méd. / P90"], rows))
    return "\n\n".join(out)


HEAD8 = ["Configuration", "PnL : 0,25 %/ATR ; 1x ; bps (1x)", "PF : 1x ; pondéré", "WR", "Espérance : bps [IC] ; ATR [IC]",
         "MDD valorisé : 0,25 %/ATR ; 1x", "Trades (/mois) ; stoppés", "Durée méd.", "Part des frais ; brut/trade"]
HEADX = ["Configuration", "Long / Short (ATR)", "F2b : n ; esp. ATR", "F3 : n ; esp. ATR", "Années > 0 : ATR ; PnL",
         "PnL annualisé ; Calmar"]


def section_D(ix) -> str:
    out = [f"## D. Huit métriques à H = {H_MAIN}",
           "Lecture séquentielle : un signal vétoé n'existe pas, la position reste libre (lecture principale). Lecture figée : "
           "les trades de RE-1 moins les trades vétoés (un signal vétoé impose le même cooldown que s'il avait été pris)."]
    order = [("RE-1", "séquentielle")] + [(v, lec) for v in VARIANTES for lec in LECTURES]
    for fee in FEES:
        rs = [(ix(c, l, fee=fee), nom(c, l)) for c, l in order]
        out.append(f"**{fr(fee, 0)} bps — 8 métriques**\n\n" + table(HEAD8, [C2B.row8(r, n) for r, n in rs]))
        out.append(f"**{fr(fee, 0)} bps — sens, sous-familles, régularité**\n\n"
                   + table(HEADX, [[n, f"{sg(r['long_atr'], 2)} / {sg(r['short_atr'], 2)}",
                                    f"{n_fr(r['n_F2b'])} ; {sg(r['esperance_atr_F2b'], 3)}",
                                    f"{n_fr(r['n_F3'])} ; {sg(r['esperance_atr_F3'], 3)}",
                                    f"{int(r['annees_atr_pos'])}/6 ; {int(r['annees_pnl_r25_pos'])}/6",
                                    f"{spct(r['cagr_r25'], 1)} ; {fr(r['calmar_r25'], 2)}"] for r, n in rs]))
    return "\n\n".join(out)


def section_E(ix) -> str:
    rows = []
    for v in VARIANTES:
        for fee in FEES:
            r = ix(v, fee=fee)
            rows.append([VARIANTES[v], f"{fr(fee, 0)} bps", f"{n_fr(r['n_vetoes'])} ; {sg(r['esp_vetoes'], 3)}",
                         f"{n_fr(r['n_perdus'])} ; {sg(r['esp_perdus'], 3)}", f"{n_fr(r['n_ajoutes'])} ; {sg(r['esp_ajoutes'], 3)}",
                         f"{n_fr(ix('RE-1', fee=fee)['n_trades'])} → {n_fr(r['n_trades'])} ; "
                         f"{sg(ix('RE-1', fee=fee)['esperance_atr'], 3)} → {sg(r['esperance_atr'], 3)}"])
    return (f"## E. Lecture séquentielle : décomposition contre RE-1 (H = {H_MAIN})\n\nVétoés : trades de RE-1 retirés ; "
            "perdus : trades alignés de RE-1 absents de la variante (un trade ajouté occupe leur place) ; ajoutés : signaux "
            "alignés que RE-1 ignorait (position occupée par un trade vétoé). n ; espérance nette par trade (ATR).\n\n"
            + table(["Tendance", "Frais", "Vétoés", "Perdus par chaîne", "Ajoutés", "Trades ; espérance ATR : RE-1 → variante"],
                    rows))


def section_F(ix) -> str:
    rows = []
    for v in VARIANTES:
        for lec in LECTURES:
            for fee in FEES:
                r, b = ix(v, lec, fee=fee), ix("RE-1", fee=fee)
                rows.append([nom(v, lec), f"{fr(fee, 0)} bps", f"{pct(b['mdd_valorise_r25'], 1)} → {pct(r['mdd_valorise_r25'], 1)}",
                             f"{fr(b['calmar_r25'], 2)} → {fr(r['calmar_r25'], 2)}",
                             f"{sg(100 * r['dmdd_obs'], 1)} [{sg(100 * r['dmdd_lo'], 1)} ; {sg(100 * r['dmdd_hi'], 1)}] ; "
                             f"{pct(r['p_mdd'], 0)}",
                             f"{sg(r['dcalmar_obs'], 2)} [{sg(r['dcalmar_lo'], 2)} ; {sg(r['dcalmar_hi'], 2)}] ; {pct(r['p_calmar'], 0)}",
                             (f"{sg(100 * r['taille_ecart_cagr'], 1)} pt ({fr(r['taille_re1_risque_bps'] / 100, 3)} %)"
                              if not pd.isna(r.get("taille_ecart_cagr", np.nan)) else "—")])
    return (f"## F. Risque (H = {H_MAIN}) : chemin réel, chemins réordonnés, taille\n\nMDD valorisé et Calmar du chemin réel "
            "(RE-1 → variante). Chemins : 2 000 tirages des mois d'entrée avec remise, mêmes mois pour RE-1 et la variante ; "
            "écart observé [P2,5 ; P97,5] ; part des chemins où la variante fait mieux (MDD aux sorties). Taille : écart de "
            "PnL annualisé entre la variante et RE-1 réduit au même MDD valorisé (risque par ATR de RE-1 réduit).\n\n"
            + table(["Configuration", "Frais", "MDD : RE-1 → variante", "Calmar : RE-1 → variante", "Écart de MDD (points) ; "
                     "chemins", "Écart de Calmar ; chemins", "À MDD égal, face à RE-1 réduit"], rows))


def section_G(ix) -> str:
    rows = []
    for c, lec in [("RE-1", "séquentielle")] + [(v, "séquentielle") for v in VARIANTES]:
        cells = []
        for fee in FEES:
            for H in HORIZONS:
                r = ix(c, lec, H, fee)
                cells.append(f"{sg(r['esperance_atr'], 3)} ; {pct(r['mdd_valorise_r25'], 1)} ; {fr(r['calmar_r25'], 2)}")
        rows.append([nom(c, lec)] + cells)
    return ("## G. Plateau d'horizon (lecture séquentielle)\n\nCellule : espérance ATR ; MDD ; Calmar.\n\n"
            + table(["Configuration"] + [f"{fr(f, 0)} bps, H = {H}" for f in FEES for H in HORIZONS], rows))


def section_H(ann) -> str:
    a5 = ann[(ann.H == H_MAIN) & (ann.frais_bps == 5.0)]
    rows = []
    for c, lec in [("RE-1", "séquentielle")] + [(v, l) for v in VARIANTES for l in LECTURES]:
        g = a5[(a5.configuration == c) & (a5.lecture == lec)].set_index("annee")
        rows.append([nom(c, lec)] + [f"{sg(g.esperance_atr.get(y), 2)} ({n_fr(g.n_trades.get(y, 0))})" for y in YEARS]
                    + [" ; ".join(spct(g.pnl_compose_r25.get(y), 0) for y in YEARS)])
    return (f"## H. Stabilité annuelle (H = {H_MAIN}, 5 bps)\n\nCellule : espérance nette par trade en ATR (trades) ; "
            "dernière colonne : PnL composé par année à 0,25 % par ATR.\n\n"
            + table(["Configuration"] + [str(y) for y in YEARS] + ["PnL par année"], rows))


def write_report(res, ann, meta) -> None:
    ix = Index(res)
    parts = [section_A(meta), section_B(meta), section_C(meta), section_D(ix), section_E(ix), section_F(ix), section_G(ix),
             section_H(ann)]
    narr = HERE / "narratif_C04.md"
    head = narr.read_text(encoding="utf-8") if narr.exists() else "# EXP-C04\n\n*(narratif à rédiger)*\n"
    (HERE / "rapport_C04.md").write_text(
        head.rstrip() + "\n\n---\n\n# Annexes chiffrées (générées par `run_C04.py`)\n\n" + "\n\n".join(parts) + "\n",
        encoding="utf-8")


# ── Figures ─────────────────────────────────────────────────────────────────────
COLORS = {"RE-1": "#000000", "V1": "#1f77b4", "V2": "#d62728", "V3": "#2ca02c"}


def _save(fig, name: str) -> None:
    for k in range(6):
        try:
            fig.savefig(FIG / name, dpi=130)
            return
        except OSError:
            if k == 5:
                raise
            time.sleep(0.5)


def fig_asymetrie(meta) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(17, 6), sharey=True)
    groups = ("tous", "F2b", "F3", "Long", "Short")
    for ax, fee in zip(axes, FEES):
        for j, (v, s) in enumerate(meta["splits"].items()):
            for k, (kind, mk) in enumerate((("aligne", "o"), ("contre", "x"))):
                x = np.arange(len(groups)) + (j - 1) * 0.22 + (k - 0.5) * 0.08
                y = np.array([s[f"esp_{kind}_{g}_{fee:g}"] for g in groups])
                lo = np.array([s[f"esp_{kind}_lo_{g}_{fee:g}"] for g in groups])
                hi = np.array([s[f"esp_{kind}_hi_{g}_{fee:g}"] for g in groups])
                ax.errorbar(x, y, yerr=[np.maximum(y - lo, 0), np.maximum(hi - y, 0)], fmt=mk, color=COLORS[v], ms=6,
                            capsize=2, elinewidth=0.8,
                            label=f"{VARIANTES[v]} — {'alignés' if kind == 'aligne' else 'contre-tendance'}")
        ax.axhline(0, color="0.3", lw=0.8)
        ax.set_xticks(range(len(groups)), groups)
        ax.set_title(f"{fr(fee, 0)} bps", fontsize=10)
        ax.grid(alpha=0.3, lw=0.5)
    axes[0].set_ylabel("Espérance nette par trade de RE-1 (ATR14(t)), IC 95 %", fontsize=9)
    axes[0].legend(fontsize=7, frameon=False, ncol=2)
    fig.suptitle("EXP-C04 — Trades de RE-1 alignés contre trades contre la tendance (H26)", fontsize=11)
    fig.tight_layout()
    _save(fig, "fig1_asymetrie_alignement.png")
    plt.close(fig)


def fig_equity(bars, trades, atr_bps) -> None:
    fig, axes = plt.subplots(2, 1, figsize=(17, 9), sharex=True, gridspec_kw={"height_ratios": [2, 1]})
    for c in ["RE-1"] + list(VARIANTES):
        tr = trades[(c, "séquentielle", H_MAIN)]
        w = risk_weights(atr_bps.reindex(tr.signal_bar.to_numpy()).to_numpy(dtype=float), C2B.RISK)
        eq = equity_curve_sized(bars, tr, 5.0, w)
        v = eq.to_numpy()
        axes[0].plot(eq.index, 100 * (v - 1), color=COLORS[c], lw=1.8 if c == "RE-1" else 1.1, label=nom(c))
        axes[1].plot(eq.index, 100 * (v / np.maximum.accumulate(v) - 1), color=COLORS[c], lw=1.4 if c == "RE-1" else 1.0)
    axes[0].set_ylabel("PnL net composé, 0,25 % par ATR (%)", fontsize=9)
    axes[1].set_ylabel("Sous le pic (%)", fontsize=9)
    axes[0].legend(fontsize=8, frameon=False)
    for ax in axes:
        ax.grid(alpha=0.3, lw=0.5)
    fig.suptitle("EXP-C04 — Capital et drawdown, H26, 5 bps, lecture séquentielle", fontsize=11)
    fig.tight_layout()
    _save(fig, "fig2_courbes_equite_H26.png")
    plt.close(fig)


def fig_queue(meta, trades, atr_bps) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(17, 5.8))
    names = list(meta["splits"])
    x = np.arange(len(names))
    for k, (key, lab) in enumerate((("part_contre", "tous les trades"), ("part_sup3_contre", "gagnants ≥ +3 ATR"),
                                    ("part_top10_contre", "décile supérieur"), ("contribution_top10_contre",
                                                                               "contribution du décile supérieur"))):
        axes[0].bar(x + (k - 1.5) * 0.2, [100 * meta["splits"][v][key] for v in names], width=0.2, label=lab)
    axes[0].set_xticks(x, [VARIANTES[v] for v in names])
    axes[0].set_ylabel("Part contre-tendance (%)", fontsize=9)
    axes[0].legend(fontsize=8, frameon=False)
    axes[0].grid(alpha=0.3, lw=0.5, axis="y")
    re1 = trades[("RE-1", "séquentielle", H_MAIN)]
    base = net_atr(re1, atr_bps, 5.0)
    grid = np.linspace(-8, 15, 400)
    for v in names:
        vs = trades[(v, "figée", H_MAIN)].signal_bar
        cv = ~re1.signal_bar.isin(set(vs)).to_numpy()
        axes[1].plot(grid, [(base[cv] >= g).mean() for g in grid], color=COLORS[v], lw=1.4, label=f"{VARIANTES[v]} — contre")
    axes[1].plot(grid, [(base >= g).mean() for g in grid], color="k", lw=2, label="RE-1, tous")
    axes[1].set_yscale("log")
    axes[1].set_xlabel("Résultat net par trade de RE-1 (ATR14(t), 5 bps)", fontsize=9)
    axes[1].set_ylabel("Part des trades au-dessus du seuil (log)", fontsize=9)
    axes[1].legend(fontsize=8, frameon=False)
    axes[1].grid(alpha=0.3, lw=0.5, which="both")
    fig.suptitle("EXP-C04 — Le veto retire-t-il la queue droite de RE-1 ? (H26)", fontsize=11)
    fig.tight_layout()
    _save(fig, "fig3_queue_droite_contre_tendance.png")
    plt.close(fig)


def fig_years(ann) -> None:
    a5 = ann[(ann.H == H_MAIN) & (ann.frais_bps == 5.0)]
    order = [("RE-1", "séquentielle")] + [(v, l) for v in VARIANTES for l in LECTURES]
    mat = np.full((len(order), len(YEARS)), np.nan)
    for a, (c, l) in enumerate(order):
        g = a5[(a5.configuration == c) & (a5.lecture == l)].set_index("annee")
        for b, y in enumerate(YEARS):
            if y in g.index:
                mat[a, b] = g.esperance_atr.loc[y]
    fig, ax = plt.subplots(figsize=(11, 5.5))
    lim = np.nanmax(np.abs(mat))
    ax.imshow(mat, cmap="RdBu", vmin=-lim, vmax=lim, aspect="auto")
    for a in range(mat.shape[0]):
        for b in range(mat.shape[1]):
            ax.text(b, a, sg(mat[a, b], 2), ha="center", va="center", fontsize=8)
    ax.set_xticks(range(len(YEARS)), YEARS, fontsize=8)
    ax.set_yticks(range(len(order)), [nom(c, l) for c, l in order], fontsize=8)
    fig.suptitle("EXP-C04 — Espérance nette par trade et par année (ATR14(t), H26, 5 bps)", fontsize=11)
    fig.tight_layout()
    _save(fig, "fig4_stabilite_annuelle.png")
    plt.close(fig)


# ── Programme ───────────────────────────────────────────────────────────────────
def _json(o):
    if isinstance(o, dict):
        return {k: _json(v) for k, v in o.items()}
    if isinstance(o, list):
        return [_json(v) for v in o]
    if isinstance(o, (np.floating, float)):
        return None if not np.isfinite(o) else float(o)
    if isinstance(o, np.integer):
        return int(o)
    if isinstance(o, np.bool_):
        return bool(o)
    return o


def main() -> None:
    if "--rapport" in sys.argv:
        res, ann = pd.read_csv(HERE / "resultats_C04.csv"), pd.read_csv(HERE / "annuel_C04.csv")
        write_report(res, ann, json.loads((HERE / "controles_C04.json").read_text(encoding="utf-8")))
        print(f"rapport_C04.md régénéré dans {HERE}")
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
    ctx = Ctx(bars, atlas, atr, masks)
    meta["tendances"] = describe_trends(ctx)
    print(f"contrôles préalables et tendances ({time.time() - t0:.0f} s)")
    rows, ann, trades, splits = run_grid(ctx, bars, atr_bps)
    res, ann = pd.DataFrame(rows), pd.DataFrame(ann)
    meta["re1"] = check_re1(ctx, bars, atr_bps, C2B.Engine(bars, atlas, atr, masks), res)
    meta["splits"] = splits
    meta["duree_s"] = round(time.time() - t0)
    res.to_csv(HERE / "resultats_C04.csv", index=False, float_format="%.6g")
    ann.to_csv(HERE / "annuel_C04.csv", index=False, float_format="%.6g")
    (HERE / "controles_C04.json").write_text(json.dumps(_json(meta), ensure_ascii=False, indent=1), encoding="utf-8")
    FIG.mkdir(parents=True, exist_ok=True)
    fig_asymetrie(meta)
    fig_equity(bars, trades, atr_bps)
    fig_queue(meta, trades, atr_bps)
    fig_years(ann)
    write_report(res, ann, json.loads(json.dumps(_json(meta))))
    print(f"C04 : {len(res)} lignes de résultats en {meta['duree_s']} s ; rapport, tableaux et figures dans {HERE}")


if __name__ == "__main__":
    main()
