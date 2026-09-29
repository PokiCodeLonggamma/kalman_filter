"""EXP-C05 — sensibilité de RE-1 à ses trois seuils durs, un facteur à la fois (OFAT).

Usage, depuis la racine du dépôt : python experiments/C05/run_C05.py [--rapport]
  --rapport : régénère seulement rapport_C05.md depuis les CSV et controles_C05.json.
Sorties dans experiments/C05/ : resultats_C05.csv, annuel_C05.csv, controles_C05.json, figures/*.png,
rapport_C05.md (= narratif_C05.md rédigé à la main, suivi des annexes chiffrées générées ici).

Contrôle : RE-1 (R2 hors nis_z_100 Q4, F2b sans stop, F3 SL-B à l'extremum, H = 26, cooldown, pyramiding 0).
Trois grilles, chacune seule, les deux autres seuils restant à leur valeur de RE-1 :
- A, frontière F2b / F3 : F3 si retrace_ratio ≥ b (SL-B 0), F2b si 0,50 ≤ retrace_ratio < b (sans stop),
  b ∈ {0,75 ; 0,80 ; 0,85 ; 0,90 ; 0,95}. L'univers ne change pas ; en cooldown, les entrées non plus : seul le stop
  des trades dont le retracement est entre b et 0,85 change.
- B, marge du stop de F3 : SL-B δ, niveau = extremum du segment ∓ δ · ATR14(t) (δ > 0 : au-delà de l'extremum, plus
  large ; δ < 0 : à l'intérieur du range, plus serré), δ ∈ {−0,25 ; 0 ; +0,25 ; +0,50} ; plancher de RE-1 inchangé
  (jamais à moins de 0,25 ATR de l'entrée). Mêmes entrées que RE-1.
- C, exclusion de nis_z_100 : signal gardé si nis_z_100 ≤ quantile p des signaux de l'atlas entier (convention de Q4
  en B01 : échantillon entier, interpolation linéaire ; p = 0,75 redonne RE-1), p ∈ {0,70 ; 0,75 ; 0,80 ; 0,85 ;
  0,90}. L'univers change ; la chaîne séquentielle est recalculée.
Frais 5 et 10 bps séparés ; capital à 0,25 % par ATR14(t) ; IC 95 % par grappes mensuelles, 2 000 tirages ; effet
apparié sur les mêmes entrées (A, B) ; écarts d'espérance, de MDD et de Calmar sur les mêmes mois tirés (I-M10) ;
RE-1 réduit au même MDD (I-M11).

Lecture fixée avant le calcul (5 bps ; 10 bps en contrôle). Voisins immédiats de RE-1 : A 0,80 et 0,90 ; B −0,25 et
+0,25 ; C P70 et P80. Un voisin se dégrade nettement si :
  (d1) son écart d'espérance à RE-1 est ≤ −20 % de l'espérance de RE-1, avec un IC 95 % entièrement négatif (effet
       apparié pour A et B, mois communs pour C) ;
  (d2) son espérance ou son Calmar est inférieur à la moitié de celui de RE-1 ;
  (d3) son MDD valorisé est plus profond que 1,5 fois celui de RE-1.
Plateau : aucun voisin immédiat en dégradation nette ; falaise : un seul ; crête : les deux. Falaise et crête sont
signalées formellement avant l'Étape D. Un voisin significativement meilleur (IC > 0) est noté, jamais adopté. Les
points extrêmes (A 0,75 et 0,95, B +0,50, C P85 et P90) décrivent la pente, sans entrer dans le verdict.
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
from categorization import add_derived  # noqa: E402
from envelope import effect_ci, equity_curve_sized, risk_weights, route_levels, stop_trades  # noqa: E402
from envelope.metrics import _boot_mean, _cluster_counts, _entry_month  # noqa: E402
from envelope.stops import _candidates, segment_extremum  # noqa: E402
from estimand import load_bars_dev  # noqa: E402
from estimand.stoploss import TRADE_COLUMNS, apply_stop  # noqa: E402


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
H = 26
RE1_RULES = {"F2b": None, "F3": ("SL-B", 0.0)}
GRILLES = {"A": (0.75, 0.80, 0.85, 0.90, 0.95), "B": (-0.25, 0.0, 0.25, 0.50), "C": (0.70, 0.75, 0.80, 0.85, 0.90)}
BASE = {"A": 0.85, "B": 0.0, "C": 0.75}
VOISINS = {"A": (0.80, 0.90), "B": (-0.25, 0.25), "C": (0.70, 0.80)}
KW = {"A": "boundary", "B": "delta", "C": "p"}
TITRES = {"A": "A — frontière F2b / F3 (retrace_ratio)", "B": "B — marge δ du stop de F3 (ATR14(t))",
          "C": "C — exclusion de nis_z_100 (centile de l'atlas)"}
SEUIL_D1, SEUIL_D2, SEUIL_D3 = 0.20, 0.5, 1.5
EDGES_R = (0.50, 0.75, 0.80, 0.85, 0.90, 0.95, np.inf)
PS_NIS = (0.0, 0.70, 0.75, 0.80, 0.85, 0.90, 1.0)
C02BIS_CSV = ROOT / "experiments" / "C02bis" / "resultats_C02bis.csv"


def val_label(g: str, v: float) -> str:
    if g == "A":
        return fr(v, 2)
    if g == "B":
        return "0" if v == 0 else sg(v, 2)
    return f"P{round(100 * v)}"


def is_base(g: str, v: float) -> bool:
    return bool(np.isclose(v, BASE[g]))


def nom(g: str, v: float) -> str:
    s = {"A": f"frontière {fr(v, 2)}", "B": f"δ = {val_label('B', v)} ATR", "C": f"exclusion > P{round(100 * v)}"}[g]
    return s + (" (RE-1)" if is_base(g, v) else "")


def net_atr(tr, atr_bps, fee) -> np.ndarray:
    return (tr.ret_gross_bps.to_numpy(dtype=float) - fee) / atr_bps.reindex(tr.signal_bar.to_numpy()).to_numpy()


def q(b, p) -> float:
    return float(np.nanpercentile(b, p))


def boot_ci(v, months, keep=None, seed: int = 0) -> tuple[float, float, float]:
    """Moyenne de `v` restreinte à `keep`, IC 95 % par grappes mensuelles d'entrée (tirages de `_cluster_counts`)."""
    keep = np.ones(len(v), dtype=bool) if keep is None else np.asarray(keep, dtype=bool)
    if not keep.any():
        return np.nan, np.nan, np.nan
    w, inv, g = _cluster_counts(months, N_BOOT, seed)
    b = _boot_mean(w, inv, g, v, keep)
    return float(v[keep].mean()), q(b, 2.5), q(b, 97.5)


def same_entries(a, b) -> bool:
    return len(a) == len(b) and all(np.array_equal(a[c].to_numpy(), b[c].to_numpy())
                                    for c in ("entry_bar", "side", "signal_bar"))


# ── Moteur ──────────────────────────────────────────────────────────────────────
class Sens:
    """Signaux de l'atlas, R2 avant l'exclusion de nis_z_100, exécution de RE-1 paramétrée par un seul seuil."""

    def __init__(self, bars, atlas, atr):
        d = add_derived(atlas)
        leg = d.leg_atr.to_numpy()
        self.bars = bars
        self.t = atlas.bar_index.to_numpy()
        self.s = atlas.direction.to_numpy()
        self.n = atlas.prev_seg_len.to_numpy()
        self.a = np.asarray(atr, dtype=float)[self.t]
        self.r = d.retrace_ratio.to_numpy()
        self.nis = d.nis_z_100.to_numpy()
        # R2 avant nis : jambe courte (leg_atr < médiane, `assign_families`), retracement ≥ 0,50, x1 déjà retourné
        self.base = (leg < float(np.median(leg))) & (self.r >= 0.5) & d.x1_already_flipped_at_t.to_numpy(dtype=bool)
        self.r_s, self.nis_s = pd.Series(self.r, index=self.t), pd.Series(self.nis, index=self.t)
        self.a_s, self.n_s = pd.Series(self.a, index=self.t), pd.Series(self.n, index=self.t)

    def threshold(self, p: float) -> float:
        return float(np.quantile(self.nis, p))

    def universe(self, p: float = 0.75) -> np.ndarray:
        return self.base & (self.nis <= self.threshold(p))

    def setup(self, boundary=0.85, delta=0.0, p=0.75, rules=None, mask=None):
        m = self.universe(p) if mask is None else mask
        t, s, n, a, r = self.t[m], self.s[m], self.n[m], self.a[m], self.r[m]
        fam = np.where(r >= boundary, "F3", "F2b")
        rules = {"F2b": None, "F3": ("SL-B", float(delta))} if rules is None else rules
        level = route_levels(self.bars, t, s, a, n, fam, rules, C2B.FLOOR)
        return t, s, level, pd.Series(fam, index=t)

    def run(self, boundary=0.85, delta=0.0, p=0.75, rules=None) -> tuple[pd.DataFrame, pd.Series]:
        t, s, level, fam = self.setup(boundary, delta, p, rules)
        return stop_trades(self.bars, t, s, H, level, dynamic=False), fam

    def isolated(self, mask) -> tuple[pd.DataFrame, pd.Series]:
        """Chaque signal du masque joué seul avec l'enveloppe de RE-1, sans sélection séquentielle."""
        t, s, level, fam = self.setup(mask=mask)
        _, t2, s2, e, x, dist = _candidates(self.bars, t, s, H, level, "isolated")
        with np.errstate(invalid="ignore"):
            out = apply_stop(self.bars, e, x, s2, dist)
        out = out.reset_index(drop=True)
        out["signal_bar"] = t2
        return out[TRADE_COLUMNS], fam


# ── Contrôles bloquants ─────────────────────────────────────────────────────────
def check_universe(sens: Sens, masks) -> dict:
    m = sens.universe(0.75)
    if not np.array_equal(m, masks["R2"]):
        raise SystemExit("univers paramétré (p = 0,75) différent de R2 hors Q4 : arrêt")
    f3 = sens.r[m] >= 0.85
    if not np.array_equal(f3, masks["F3"][m]):
        raise SystemExit("frontière 0,85 : sous-familles différentes de B01 : arrêt")
    return {"n_atlas": len(sens.t), "n_base": int(sens.base.sum()), "n_R2": int(m.sum()), "n_F2b": int((~f3).sum()),
            "n_F3": int(f3.sum())}


def check_re1(re1, fam1, bars, atr_bps, eng) -> dict:
    """Bloquant : RE-1 = RE-1 de C02bis, trade par trade et dans resultats_C02bis.csv (5 et 10 bps)."""
    b, _ = eng.run("R2", RE1_RULES, H, False)
    if not re1[TRADE_COLUMNS].equals(b[TRADE_COLUMNS]):
        raise SystemExit("RE-1 : trades différents de C02bis : arrêt")
    ref = pd.read_csv(C02BIS_CSV)
    cols = ["n_trades", "esperance_bps", "esperance_atr", "esperance_atr_lo", "esperance_atr_hi", "pnl_compose",
            "mdd_valorise", "pf", "wr", "pnl_compose_r25", "mdd_valorise_r25", "calmar_r25"]
    worst, n = 0.0, 0
    for fee in FEES:
        m, _ = C2B.metrics(re1, bars, atr_bps, fee, int(len(fam1)), fam1)
        g = ref[(ref.variante_seuils == C2B.ENTIER) & (ref.configuration == "RE-1") & (ref.H == H)
                & (ref["mode"] == "cooldown") & (ref.frais_bps == fee)].iloc[0]
        for c in cols:
            x, y = float(m[c]), float(g[c])
            if not np.isclose(x, y, rtol=1e-5, atol=1e-9):
                raise SystemExit(f"RE-1 {fee:g} bps : {c} différent de C02bis ({x} contre {y}) : arrêt")
            worst = max(worst, abs(x - y) / max(abs(y), 1e-12))
        n += 1
    return {"lignes_comparees": n, "ecart_relatif_max": worst, "n_trades": len(re1)}


# ── Mesures ─────────────────────────────────────────────────────────────────────
def touched(g, v, tr, re1, fam, fam1, sens: Sens, bars, atr_bps) -> dict:
    """A : trades de RE-1 changés de sous-famille ; B : trades de F3. Effet apparié restreint à ces trades [IC], part
    stoppée de F3 ; B : distance médiane du stop à l'entrée (ATR) et part des stops au plancher."""
    if not same_entries(tr, re1):
        raise SystemExit(f"grille {g} = {v} : entrées différentes de RE-1 : arrêt")
    sb = tr.signal_bar.to_numpy()
    f_new, f_old = fam.reindex(sb).to_numpy(), fam1.reindex(sb).to_numpy()
    keep = (f_new != f_old) if g == "A" else (f_old == "F3")
    d = (tr.ret_gross_bps.to_numpy(dtype=float) - re1.ret_gross_bps.to_numpy(dtype=float)) \
        / atr_bps.reindex(sb).to_numpy(dtype=float)
    e, lo, hi = boot_ci(d, _entry_month(tr, bars), keep)
    f3 = f_new == "F3"
    out = {"n_touches": int(keep.sum()), "effet_touches_atr": e, "effet_touches_atr_lo": lo, "effet_touches_atr_hi": hi,
           "n_vers_F3": int((f3 & (f_old == "F2b")).sum()), "n_vers_F2b": int((~f3 & (f_old == "F3")).sum()),
           "part_stop_F3": float(tr.stop.to_numpy(dtype=bool)[f3].mean()) if f3.any() else np.nan}
    if g == "B":
        t3, s3 = sb[f3], tr.side.to_numpy(dtype=np.int64)[f3]
        a3, n3 = sens.a_s.reindex(t3).to_numpy(), sens.n_s.reindex(t3).to_numpy()
        p0 = bars.open.to_numpy(dtype=float)[t3 + 1]
        raw = segment_extremum(bars, t3, s3, n3) - s3 * float(v) * a3
        lvl = np.where(s3 == 1, np.minimum(raw, p0 - C2B.FLOOR * a3), np.maximum(raw, p0 + C2B.FLOOR * a3))
        out.update({"distance_stop_med_atr": float(np.median(s3 * (p0 - lvl) / a3)),
                    "part_plancher": float((lvl != raw).mean())})
    return out


def paths_vs_re1(tr_b, tr_a, bars, atr_bps, fee, n_boot: int = N_BOOT, seed: int = 0) -> dict:
    """Variante (b) contre RE-1 (a) sur les mêmes chemins (C04, `paired_paths`) : mois civils d'entrée tirés avec
    remise, trades de chaque configuration dans ces mois. Écart d'espérance par trade (ATR), de MDD aux sorties et de
    Calmar sur 6 ans."""
    ma, mb = _entry_month(tr_a, bars), _entry_month(tr_b, bars)
    allm = np.unique(np.r_[ma, mb])
    ia, ib = np.searchsorted(allm, ma), np.searchsorted(allm, mb)
    ga = [np.flatnonzero(ia == k) for k in range(len(allm))]
    gb = [np.flatnonzero(ib == k) for k in range(len(allm))]
    ra, rb = C3.sized_returns(tr_a, atr_bps, fee), C3.sized_returns(tr_b, atr_bps, fee)
    va, vb = net_atr(tr_a, atr_bps, fee), net_atr(tr_b, atr_bps, fee)
    rng = np.random.default_rng(seed)
    de, dm, dc = np.empty(n_boot), np.empty(n_boot), np.empty(n_boot)

    def stats(r):
        mdd = C3.mdd_exits(r)
        with np.errstate(divide="ignore"):
            return mdd, np.expm1(np.log1p(r).sum() / N_YEARS) / abs(mdd)
    for i in range(n_boot):
        d = rng.integers(0, len(allm), len(allm))
        oa = np.concatenate([ga[k] for k in d]).astype(int)
        ob = np.concatenate([gb[k] for k in d]).astype(int)
        (m_a, c_a), (m_b, c_b) = stats(ra[oa]), stats(rb[ob])
        de[i], dm[i], dc[i] = vb[ob].mean() - va[oa].mean(), m_b - m_a, c_b - c_a
    (m_a, c_a), (m_b, c_b) = stats(ra), stats(rb)
    return {"de_obs": float(vb.mean() - va.mean()), "de_lo": q(de, 2.5), "de_hi": q(de, 97.5),
            "dmdd_obs": m_b - m_a, "dmdd_lo": q(dm, 2.5), "dmdd_hi": q(dm, 97.5), "p_mdd": float((dm > 0).mean()),
            "dcalmar_obs": c_b - c_a, "dcalmar_lo": q(dc, 2.5), "dcalmar_hi": q(dc, 97.5),
            "p_calmar": float((dc > 0).mean())}


def size_check(tr, re1, bars, atr_bps, fee) -> dict:
    """I-M11 : RE-1 mis à la taille qui donne le MDD valorisé de la variante ; écart de PnL annualisé à MDD égal."""
    v = C3A.sized_path(tr, bars, atr_bps, fee, C2B.RISK)
    r = C3A.size_matched(re1, bars, atr_bps, fee, v["mdd"])
    return {"taille_mdd": v["mdd"], "taille_re1_risque_bps": r["risque_bps"], "taille_re1_cagr": r["cagr"],
            "taille_ecart_cagr": v["cagr"] - r["cagr"]}


def decompose_c(tr, re1, u_var: set, u_re1: set, atr_bps, fee) -> dict:
    """Grille C contre RE-1 : retirés (signal de RE-1 exclu), perdus par chaîne (signal gardé, position prise), nouveaux
    signaux (admis par la variante seule), libérés par chaîne. Bilan refermé :
    variante = RE-1 − retirés − perdus + nouveaux + libérés."""
    sv, sr = set(tr.signal_bar), set(re1.signal_bar)
    parts = {"retires": re1[~re1.signal_bar.isin(u_var)],
             "perdus": re1[re1.signal_bar.isin(u_var) & ~re1.signal_bar.isin(sv)],
             "nouveaux": tr[~tr.signal_bar.isin(u_re1)],
             "liberes": tr[tr.signal_bar.isin(u_re1) & ~tr.signal_bar.isin(sr)]}
    s = {k: net_atr(x, atr_bps, fee) for k, x in parts.items()}
    lhs = net_atr(tr, atr_bps, fee).sum()
    rhs = net_atr(re1, atr_bps, fee).sum() - s["retires"].sum() - s["perdus"].sum() + s["nouveaux"].sum() \
        + s["liberes"].sum()
    if not np.isclose(lhs, rhs, rtol=1e-9, atol=1e-9):
        raise SystemExit("décomposition de la grille C non refermée : arrêt")
    out = {}
    for k, x in s.items():
        out.update({f"n_{k}": len(x), f"esp_{k}": float(x.mean()) if len(x) else np.nan, f"somme_{k}": float(x.sum())})
    return out


def run_grid(sens: Sens, re1, fam1, bars, atr_bps) -> tuple[list, list, dict]:
    rows, ann, trades = [], [], {}
    u_re1 = set(sens.t[sens.universe(0.75)])
    for g, values in GRILLES.items():
        for v in values:
            tr, fam = sens.run(**{KW[g]: v})
            trades[(g, v)] = tr
            base = is_base(g, v)
            if base and not tr[TRADE_COLUMNS].equals(re1[TRADE_COLUMNS]):
                raise SystemExit(f"grille {g} : le point de RE-1 ne redonne pas RE-1 : arrêt")
            p = v if g == "C" else 0.75
            u = sens.universe(p)
            extra = {"n_candidats": int(u.sum()), "seuil_nis": sens.threshold(p),
                     "part_base_exclue": float(1.0 - u.sum() / sens.base.sum())}
            if g in ("A", "B"):
                extra.update(touched(g, v, tr, re1, fam, fam1, sens, bars, atr_bps))
                if not base:
                    extra.update(effect_ci(tr, re1, bars, atr_bps, N_BOOT))
            for fee in FEES:
                m, y = C2B.metrics(tr, bars, atr_bps, fee, int(u.sum()), fam)
                row = {"grille": g, "valeur": v, "re1": base, "frais_bps": fee, **m, **extra}
                if not base:
                    row.update(paths_vs_re1(tr, re1, bars, atr_bps, fee))
                    row.update(size_check(tr, re1, bars, atr_bps, fee))
                    if g == "C":
                        row.update(decompose_c(tr, re1, set(sens.t[u]), u_re1, atr_bps, fee))
                rows.append(row)
                ann += [{"grille": g, "valeur": v, "frais_bps": fee, **r} for r in y.to_dict("records")]
        print(f"  grille {g} : faite")
    return rows, ann, trades


def bands_retrace(sens: Sens, re1, bars, atr_bps) -> list[dict]:
    """Effet du stop SL-B 0 contre l'absence de stop, trade par trade de RE-1 (mêmes entrées), par bande de
    retracement : la grille A déplace la frontière à travers ces bandes."""
    u0, _ = sens.run(rules={"F2b": None, "F3": None})
    u1, _ = sens.run(rules={"F2b": ("SL-B", 0.0), "F3": ("SL-B", 0.0)})
    if not (same_entries(u0, re1) and same_entries(u1, re1)):
        raise SystemExit("bandes de retracement : entrées différentes de RE-1 : arrêt")
    sb = re1.signal_bar.to_numpy()
    r = sens.r_s.reindex(sb).to_numpy()
    d = (u1.ret_gross_bps.to_numpy(dtype=float) - u0.ret_gross_bps.to_numpy(dtype=float)) \
        / atr_bps.reindex(sb).to_numpy(dtype=float)
    months = _entry_month(re1, bars)
    e0, e1 = net_atr(u0, atr_bps, 5.0), net_atr(u1, atr_bps, 5.0)
    rows = []
    for lo_, hi_ in zip(EDGES_R[:-1], EDGES_R[1:]):
        k = (r >= lo_) & (r < hi_)
        e, lo, hi = boot_ci(d, months, k)
        rows.append({"bande": f"[{fr(lo_, 2)} ; {fr(hi_, 2) if np.isfinite(hi_) else '∞'}[", "n": int(k.sum()),
                     "regime_re1": "SL-B 0" if lo_ >= 0.85 else "sans stop", "esp_sans_stop": float(e0[k].mean()),
                     "esp_slb0": float(e1[k].mean()), "effet_stop": e, "effet_stop_lo": lo, "effet_stop_hi": hi,
                     "part_stoppee": float(u1.stop.to_numpy(dtype=bool)[k].mean())})
    return rows


def bands_nis(sens: Sens, re1, bars, atr_bps) -> list[dict]:
    """Chaque signal de R2 avant l'exclusion de nis_z_100 joué seul avec l'enveloppe de RE-1, par bande de centile de
    nis_z_100 (quantiles de l'atlas entier) : lecture par signal, sans chaîne séquentielle."""
    iso, fam = sens.isolated(sens.base)
    sub = iso[iso.signal_bar.isin(set(re1.signal_bar))].reset_index(drop=True)
    if not sub[TRADE_COLUMNS].equals(re1[TRADE_COLUMNS]):
        raise SystemExit("signaux joués seuls : trades de RE-1 non reproduits : arrêt")
    sb = iso.signal_bar.to_numpy()
    nis = sens.nis_s.reindex(sb).to_numpy()
    edges = [-np.inf] + [sens.threshold(p) for p in PS_NIS[1:-1]] + [np.inf]
    months = _entry_month(iso, bars)
    v5, v10 = net_atr(iso, atr_bps, 5.0), net_atr(iso, atr_bps, 10.0)
    f3 = fam.reindex(sb).to_numpy() == "F3"
    in_re1 = iso.signal_bar.isin(set(re1.signal_bar)).to_numpy()
    rows = []
    for i in range(len(PS_NIS) - 1):
        k = (nis > edges[i]) & (nis <= edges[i + 1])
        lab = (f"≤ P{round(100 * PS_NIS[1])}" if i == 0 else f"> P{round(100 * PS_NIS[i])}" if i == len(PS_NIS) - 2
               else f"P{round(100 * PS_NIS[i])}–P{round(100 * PS_NIS[i + 1])}")
        e, lo, hi = boot_ci(v5, months, k)
        rows.append({"bande": lab, "seuil_lo": edges[i], "seuil_hi": edges[i + 1], "n": int(k.sum()),
                     "n_dans_re1": int((k & in_re1).sum()), "esp5": e, "esp5_lo": lo, "esp5_hi": hi,
                     "esp10": float(v10[k].mean()), "mediane5": float(np.median(v5[k])), "wr5": float((v5[k] > 0).mean()),
                     "p90_5": q(v5[k], 90), "part_F3": float(f3[k].mean())})
    return rows


# ── Lecture fixée avant le calcul ───────────────────────────────────────────────
class Index:
    def __init__(self, res):
        self.d = {(r["grille"], round(float(r["valeur"]), 4), float(r["frais_bps"])): r for r in res.to_dict("records")}

    def __call__(self, g, v, fee=5.0) -> dict:
        return self.d[(g, round(float(v), 4), float(fee))]


def lecture(ix: Index, fee: float) -> dict:
    out = {}
    for g in GRILLES:
        b = ix(g, BASE[g], fee)
        vs = {}
        for v in VOISINS[g]:
            r = ix(g, v, fee)
            d, lo, hi = ((r["effet_atr"], r["effet_atr_lo"], r["effet_atr_hi"]) if g in ("A", "B")
                         else (r["de_obs"], r["de_lo"], r["de_hi"]))
            d1 = bool(d <= -SEUIL_D1 * b["esperance_atr"] and hi < 0)
            d2 = bool(r["esperance_atr"] < SEUIL_D2 * b["esperance_atr"] or r["calmar_r25"] < SEUIL_D2 * b["calmar_r25"])
            d3 = bool(r["mdd_valorise_r25"] < SEUIL_D3 * b["mdd_valorise_r25"])
            vs[val_label(g, v)] = {"valeur": v, "ecart": d, "ecart_lo": lo, "ecart_hi": hi, "d1": d1, "d2": d2, "d3": d3,
                                   "net": d1 or d2 or d3, "meilleur": bool(lo > 0)}
        k = sum(x["net"] for x in vs.values())
        es = [ix(g, v, fee)["esperance_atr"] for v in GRILLES[g]]
        cs = [ix(g, v, fee)["calmar_r25"] for v in GRILLES[g]]
        out[g] = {"voisins": vs, "verdict": ("plateau", "falaise", "crête")[k],
                  "rang_esperance": 1 + sum(e > b["esperance_atr"] for e in es),
                  "rang_calmar": 1 + sum(c > b["calmar_r25"] for c in cs), "n_points": len(GRILLES[g])}
    return out


# ── Rapport ─────────────────────────────────────────────────────────────────────
HEAD8 = ["Configuration", "PnL : 0,25 %/ATR ; 1x ; bps (1x)", "PF : 1x ; pondéré", "WR", "Espérance : bps [IC] ; ATR [IC]",
         "MDD valorisé : 0,25 %/ATR ; 1x", "Trades (/mois) ; stoppés", "Durée méd.", "Part des frais ; brut/trade"]


def _f(x) -> float:
    return np.nan if x is None else float(x)


def section_A(meta) -> str:
    a, c, u = meta["ancre"], meta["re1"], meta["univers"]
    rows = [["Ancre P6.5d", f"{n_fr(a['sans_stop']['n_trades'])} et {n_fr(a['stop_2_5']['n_trades'])} trades identiques"],
            ["Univers paramétré", f"p = 0,75 redonne les {n_fr(u['n_R2'])} candidats de RE-1 (F2b {n_fr(u['n_F2b'])}, "
             f"F3 {n_fr(u['n_F3'])}) ; frontière 0,85 = sous-familles de B01 ; {n_fr(u['n_base'])} signaux de R2 avant "
             f"l'exclusion de nis_z_100, sur {n_fr(u['n_atlas'])} signaux de l'atlas"],
            ["RE-1 = RE-1 de C02bis", f"{n_fr(c['n_trades'])} trades identiques à H26 ; {c['lignes_comparees']} lignes de "
             f"métriques identiques à resultats_C02bis.csv (écart relatif max {sci(c['ecart_relatif_max'])})"],
            ["Point RE-1 de chaque grille", "A = 0,85, B = 0 et C = P75 : trades identiques à RE-1"],
            ["Mêmes entrées (A, B)", "chaque variante de A et de B a les entrées de RE-1, trade par trade (effet apparié)"],
            ["Décomposition (C)", "variante = RE-1 − retirés − perdus + nouveaux + libérés, refermée à 10⁻⁹ près, à 5 et "
             "10 bps"],
            ["Signaux joués seuls (bandes)", "restreints aux signaux pris par RE-1, ils redonnent ses trades"],
            ["Période", "2020-01 → 2025-12 ; aucune barre de 2026 lue ; ETH et XRP non lus"]]
    return "## A. Contrôles bloquants\n\n" + table(["Contrôle", "Résultat"], rows)


def section_B(ix: Index) -> str:
    ra = [[val_label("A", v) + (" (RE-1)" if is_base("A", v) else ""), n_fr(ix("A", v)["n_F2b"]), n_fr(ix("A", v)["n_F3"]),
           f"{n_fr(ix('A', v)['n_vers_F3'])} → F3 ; {n_fr(ix('A', v)['n_vers_F2b'])} → F2b",
           pct(ix("A", v)["part_stop_F3"], 0)] for v in GRILLES["A"]]
    rb = [[val_label("B", v) + (" (RE-1)" if is_base("B", v) else ""), n_fr(ix("B", v)["n_F3"]),
           fr(ix("B", v)["distance_stop_med_atr"], 2), pct(ix("B", v)["part_plancher"], 1),
           pct(ix("B", v)["part_stop_F3"], 0)] for v in GRILLES["B"]]
    rc = [[val_label("C", v) + (" (RE-1)" if is_base("C", v) else ""), fr(ix("C", v)["seuil_nis"], 3),
           n_fr(ix("C", v)["n_candidats"]), pct(ix("C", v)["part_base_exclue"], 1), n_fr(ix("C", v)["n_trades"])]
          for v in GRILLES["C"]]
    return ("## B. Grilles\n\n**A — frontière F2b / F3** (trades de RE-1, mêmes entrées)\n\n"
            + table(["Frontière", "Trades F2b", "Trades F3", "Changés de sous-famille", "Stoppés parmi F3"], ra)
            + "\n\n**B — marge du stop de F3** (distance du stop à l'entrée open[t + 1], ATR14(t) ; plancher : 0,25 ATR)\n\n"
            + table(["δ (ATR)", "Trades F3", "Distance médiane du stop", "Stops au plancher", "Stoppés parmi F3"], rb)
            + "\n\n**C — exclusion de nis_z_100** (seuil : quantile de l'atlas entier ; part exclue : des signaux de R2 "
              "avant l'exclusion)\n\n"
            + table(["Centile", "Seuil nis_z_100", "Candidats", "Part exclue", "Trades"], rc))


def section_C(ix: Index) -> str:
    out = [f"## C. Huit métriques à H = {H}"]
    for g in GRILLES:
        for fee in FEES:
            out.append(f"**{TITRES[g]}, {fr(fee, 0)} bps**\n\n"
                       + table(HEAD8, [C2B.row8(ix(g, v, fee), nom(g, v)) for v in GRILLES[g]]))
    return "\n\n".join(out)


def _paths_cells(r) -> list:
    if r["re1"]:
        return ["—", "—", "—", "—"]
    g = r["grille"]
    e, lo, hi = ((r["effet_atr"], r["effet_atr_lo"], r["effet_atr_hi"]) if g in ("A", "B")
                 else (r["de_obs"], r["de_lo"], r["de_hi"]))
    return [ci(e, lo, hi, 3),
            f"{sg(100 * r['dmdd_obs'], 1)} [{sg(100 * r['dmdd_lo'], 1)} ; {sg(100 * r['dmdd_hi'], 1)}] ; {pct(r['p_mdd'], 0)}",
            f"{sg(r['dcalmar_obs'], 2)} [{sg(r['dcalmar_lo'], 2)} ; {sg(r['dcalmar_hi'], 2)}] ; {pct(r['p_calmar'], 0)}",
            f"{sg(100 * r['taille_ecart_cagr'], 1)} pt ({fr(r['taille_re1_risque_bps'] / 100, 3)} %)"]


def section_D(ix: Index) -> str:
    out = [f"## D. Sensibilité (H = {H})",
           "Espérance nette par trade en ATR [IC 95 % par grappes mensuelles] ; PnL composé à 0,25 % par ATR et son "
           "annualisé ; MDD valorisé ; Calmar = PnL annualisé / |MDD| sur 6 ans. Écart d'espérance à RE-1 : effet apparié "
           "trade par trade pour A et B (mêmes entrées, indépendant des frais), écart des moyennes sur les mêmes mois "
           "tirés pour C. Chemins : 2 000 tirages des mois d'entrée avec remise, mêmes mois pour RE-1 et la variante ; "
           "écart observé [P2,5 ; P97,5] ; part des chemins où la variante fait mieux (MDD aux sorties). À MDD égal : "
           "écart de PnL annualisé entre la variante et RE-1 mis à la taille qui donne le même MDD valorisé (risque par "
           "ATR de RE-1 entre parenthèses)."]
    for g in GRILLES:
        for fee in FEES:
            rows = []
            for v in GRILLES[g]:
                r = ix(g, v, fee)
                rows.append([nom(g, v), ci(r["esperance_atr"], r["esperance_atr_lo"], r["esperance_atr_hi"], 3),
                             f"{spct(r['pnl_compose_r25'])} ; {spct(r['cagr_r25'], 1)}/an", pct(r["mdd_valorise_r25"]),
                             fr(r["calmar_r25"], 2)] + _paths_cells(r))
            out.append(f"**{TITRES[g]}, {fr(fee, 0)} bps**\n\n"
                       + table(["Configuration", "Espérance ATR [IC]", "PnL ; annualisé", "MDD", "Calmar",
                                "Écart d'espérance à RE-1 [IC]", "Écart de MDD (points) ; chemins meilleurs",
                                "Écart de Calmar ; chemins meilleurs", "À MDD égal face à RE-1"], rows))
    return "\n\n".join(out)


def section_E(ix: Index, meta) -> str:
    br = meta["bandes_retrace"]
    rows = [[b["bande"], n_fr(b["n"]), b["regime_re1"], sg(b["esp_sans_stop"], 3), sg(b["esp_slb0"], 3),
             ci(b["effet_stop"], b["effet_stop_lo"], b["effet_stop_hi"], 3), pct(b["part_stoppee"], 0)] for b in br]
    out = ["## E. Mécanismes",
           "**A — effet du stop à l'extremum par bande de retracement.** Trades de RE-1 (mêmes entrées) joués sans stop "
           "puis tous avec SL-B 0 ; effet par trade du stop (ATR, indépendant des frais) [IC] ; espérances nettes à 5 bps. "
           "La grille A déplace la frontière à travers ces bandes : 0,75 et 0,80 ajoutent le stop aux bandes [0,75 ; "
           "0,85[, 0,90 et 0,95 le retirent aux bandes [0,85 ; 0,95[.\n\n"
           + table(["Retracement", "Trades", "Régime dans RE-1", "Sans stop", "SL-B 0", "Effet du stop [IC]",
                    "Stoppés (SL-B 0)"], rows)]
    rows = []
    for g in ("A", "B"):
        for v in GRILLES[g]:
            if is_base(g, v):
                continue
            r = ix(g, v)
            rows.append([nom(g, v), n_fr(r["n_touches"]),
                         ci(r["effet_touches_atr"], r["effet_touches_atr_lo"], r["effet_touches_atr_hi"], 3),
                         ci(r["effet_atr"], r["effet_atr_lo"], r["effet_atr_hi"], 3), pct(r["part_stop_F3"], 0)])
    out.append("**A et B — trades touchés.** A : trades changés de sous-famille ; B : trades de F3. Effet apparié sur "
               "ces trades et sur l'ensemble des trades de RE-1 (ATR, indépendant des frais).\n\n"
               + table(["Configuration", "Trades touchés", "Effet sur les trades touchés [IC]",
                        "Effet par trade de RE-1 [IC]", "Stoppés parmi F3"], rows))
    rows = []
    for v in GRILLES["C"]:
        if is_base("C", v):
            continue
        for fee in FEES:
            r, b = ix("C", v, fee), ix("C", BASE["C"], fee)
            rows.append([nom("C", v), f"{fr(fee, 0)} bps", f"{n_fr(r['n_retires'])} ; {sg(r['esp_retires'], 3)}",
                         f"{n_fr(r['n_perdus'])} ; {sg(r['esp_perdus'], 3)}",
                         f"{n_fr(r['n_nouveaux'])} ; {sg(r['esp_nouveaux'], 3)}",
                         f"{n_fr(r['n_liberes'])} ; {sg(r['esp_liberes'], 3)}",
                         f"{n_fr(b['n_trades'])} → {n_fr(r['n_trades'])} ; {sg(b['esperance_atr'], 3)} → "
                         f"{sg(r['esperance_atr'], 3)}"])
    out.append("**C — décomposition contre RE-1.** Retirés : trades de RE-1 dont le signal est exclu ; perdus : trades de "
               "RE-1 dont le signal est gardé mais tombe pendant un trade nouveau ; nouveaux : signaux que seule la variante "
               "admet ; libérés : signaux gardés par les deux que RE-1 ignorait (position occupée). n ; espérance nette "
               "par trade (ATR).\n\n"
               + table(["Configuration", "Frais", "Retirés", "Perdus par chaîne", "Nouveaux signaux", "Libérés par chaîne",
                        "Trades ; espérance : RE-1 → variante"], rows))
    bn = meta["bandes_nis"]
    rows = [[b["bande"], f"]{fr(b['seuil_lo'], 3) if b['seuil_lo'] is not None else '−∞'} ; "
             f"{fr(b['seuil_hi'], 3) if b['seuil_hi'] is not None else '+∞'}]", n_fr(b["n"]), n_fr(b["n_dans_re1"]),
             ci(b["esp5"], b["esp5_lo"], b["esp5_hi"], 3), sg(b["esp10"], 3), sg(b["mediane5"], 3), pct(b["wr5"], 0),
             sg(b["p90_5"], 2), pct(b["part_F3"], 0)] for b in bn]
    out.append("**C — chaque signal joué seul, par bande de nis_z_100.** Signaux de R2 avant l'exclusion, enveloppe de "
               "RE-1 (H26, F2b sans stop, F3 SL-B 0), sans sélection séquentielle : trades qui se chevauchent, lecture par "
               "signal. Espérance nette en ATR [IC 95 % par grappes mensuelles].\n\n"
               + table(["Bande (atlas)", "Seuils nis_z_100", "Signaux", "Pris par RE-1", "Esp. 5 bps [IC]", "Esp. 10 bps",
                        "Médiane 5 bps", "Gagnants", "P90", "Part F3"], rows))
    return "\n\n".join(out)


def section_F(ann) -> str:
    a5 = ann[ann.frais_bps == 5.0]
    rows = []
    for g in GRILLES:
        for v in GRILLES[g]:
            s = a5[(a5.grille == g) & np.isclose(a5.valeur, v)].set_index("annee")
            rows.append([nom(g, v)] + [f"{sg(s.esperance_atr.get(y), 2)} ({n_fr(s.n_trades.get(y, 0))})" for y in YEARS]
                        + [" ; ".join(spct(s.pnl_compose_r25.get(y), 0) for y in YEARS)])
    return (f"## F. Stabilité annuelle (H = {H}, 5 bps)\n\nCellule : espérance nette par trade en ATR (trades) ; dernière "
            "colonne : PnL composé par année à 0,25 % par ATR.\n\n"
            + table(["Configuration"] + [str(y) for y in YEARS] + ["PnL par année"], rows))


def section_G(ix: Index, meta) -> str:
    out = ["## G. Lecture fixée avant le calcul",
           "Voisins immédiats de RE-1. (d1) écart d'espérance ≤ −20 % de celle de RE-1, IC entièrement négatif ; (d2) "
           "espérance ou Calmar < moitié de RE-1 ; (d3) MDD valorisé plus profond que 1,5 fois celui de RE-1. Plateau : "
           "aucun voisin en dégradation nette ; falaise : un ; crête : les deux. Rang : place de RE-1 dans sa grille "
           "(1 = meilleur)."]
    rows = []
    for fee in FEES:
        lec = meta["lecture"][f"{fee:g}"]
        for g in GRILLES:
            L, b = lec[g], ix(g, BASE[g], fee)
            for lab, x in L["voisins"].items():
                r = ix(g, x["valeur"], fee)
                rows.append([TITRES[g].split(" — ")[0], f"{fr(fee, 0)} bps", lab,
                             f"{ci(x['ecart'], x['ecart_lo'], x['ecart_hi'], 3)} ; seuil {sg(-SEUIL_D1 * b['esperance_atr'], 3)}"
                             + (" ✗" if x["d1"] else ""),
                             f"{sg(r['esperance_atr'], 3)} / {sg(b['esperance_atr'], 3)} ; {fr(r['calmar_r25'], 2)} / "
                             f"{fr(b['calmar_r25'], 2)}" + (" ✗" if x["d2"] else ""),
                             f"{pct(r['mdd_valorise_r25'])} / {pct(b['mdd_valorise_r25'])}" + (" ✗" if x["d3"] else ""),
                             "oui" if x["net"] else "non", "oui" if x["meilleur"] else "non",
                             f"{L['verdict']} ; rang {L['rang_esperance']}/{L['n_points']} (esp.), "
                             f"{L['rang_calmar']}/{L['n_points']} (Calmar)"])
    out.append(table(["Grille", "Frais", "Voisin", "(d1) Écart d'espérance [IC]", "(d2) Esp. ; Calmar : voisin / RE-1",
                      "(d3) MDD : voisin / RE-1", "Dégradation nette", "Meilleur (IC > 0)", "Verdict ; rang de RE-1"], rows))
    return "\n\n".join(out)


def write_report(res, ann, meta) -> None:
    ix = Index(res)
    parts = [section_A(meta), section_B(ix), section_C(ix), section_D(ix), section_E(ix, meta), section_F(ann),
             section_G(ix, meta)]
    narr = HERE / "narratif_C05.md"
    head = narr.read_text(encoding="utf-8") if narr.exists() else "# EXP-C05\n\n*(narratif à rédiger)*\n"
    (HERE / "rapport_C05.md").write_text(
        head.rstrip() + "\n\n---\n\n# Annexes chiffrées (générées par `run_C05.py`)\n\n" + "\n\n".join(parts) + "\n",
        encoding="utf-8")


# ── Figures ─────────────────────────────────────────────────────────────────────
FEE_COLORS = ("#1f77b4", "#d62728")


def _save(fig, name: str) -> None:
    for k in range(6):
        try:
            fig.savefig(FIG / name, dpi=130)
            return
        except OSError:
            if k == 5:
                raise
            time.sleep(0.5)


def fig_sensibilite(ix: Index) -> None:
    fig, axes = plt.subplots(3, 3, figsize=(17, 11), sharex="col")
    for j, g in enumerate(GRILLES):
        xs = np.array(GRILLES[g], dtype=float)
        for k, (fee, col) in enumerate(zip(FEES, FEE_COLORS)):
            rs = [ix(g, v, fee) for v in xs]
            e = np.array([r["esperance_atr"] for r in rs])
            lo, hi = np.array([r["esperance_atr_lo"] for r in rs]), np.array([r["esperance_atr_hi"] for r in rs])
            dx = (k - 0.5) * 0.08 * (xs.max() - xs.min()) / (len(xs) - 1)
            axes[0, j].errorbar(xs + dx, e, yerr=[e - lo, hi - e], fmt="o-", color=col, capsize=3, lw=1.4, ms=5,
                                label=f"{fr(fee, 0)} bps (IC 95 %)")
            axes[1, j].plot(xs, [100 * r["mdd_valorise_r25"] for r in rs], "o-", color=col, lw=1.4, ms=5)
            axes[2, j].plot(xs, [r["calmar_r25"] for r in rs], "o-", color=col, lw=1.4, ms=5)
        for i in range(3):
            axes[i, j].axvline(BASE[g], color="0.4", ls="--", lw=0.9)
            axes[i, j].grid(alpha=0.3, lw=0.5)
        axes[0, j].axhline(0, color="0.3", lw=0.8)
        axes[0, j].set_title(TITRES[g], fontsize=10)
        axes[2, j].set_xticks(xs, [val_label(g, v) for v in xs])
    axes[0, 0].set_ylabel("Espérance nette par trade (ATR14(t))", fontsize=9)
    axes[1, 0].set_ylabel("MDD valorisé, 0,25 % par ATR (%)", fontsize=9)
    axes[2, 0].set_ylabel("Calmar (PnL annualisé / |MDD|)", fontsize=9)
    axes[0, 0].legend(fontsize=8, frameon=False)
    fig.suptitle("EXP-C05 — Sensibilité de RE-1 à ses trois seuils (H26, un facteur à la fois ; tirets : RE-1)",
                 fontsize=11)
    fig.tight_layout()
    _save(fig, "fig1_sensibilite.png")
    plt.close(fig)


def fig_effets(ix: Index) -> None:
    fig, axes = plt.subplots(1, 3, figsize=(17, 5.4))
    for j, g in enumerate(GRILLES):
        ax, xs = axes[j], np.array(GRILLES[g], dtype=float)
        series = [(None, "0.2", "effet apparié (mêmes entrées, tous frais)")] if g in ("A", "B") else \
            [(fee, col, f"{fr(fee, 0)} bps, mois communs") for fee, col in zip(FEES, FEE_COLORS)]
        for k, (fee, col, lab) in enumerate(series):
            y, lo, hi = [], [], []
            for v in xs:
                r = ix(g, v, fee or 5.0)
                if is_base(g, v):
                    y.append(0.0), lo.append(0.0), hi.append(0.0)
                elif g in ("A", "B"):
                    y.append(r["effet_atr"]), lo.append(r["effet_atr_lo"]), hi.append(r["effet_atr_hi"])
                else:
                    y.append(r["de_obs"]), lo.append(r["de_lo"]), hi.append(r["de_hi"])
            y, lo, hi = np.array(y), np.array(lo), np.array(hi)
            dx = (k - (len(series) - 1) / 2) * 0.08 * (xs.max() - xs.min()) / (len(xs) - 1)
            ax.errorbar(xs + dx, y, yerr=[y - lo, hi - y], fmt="o-", color=col, capsize=3, lw=1.3, ms=5, label=lab)
        for fee, col in zip(FEES, FEE_COLORS):
            ax.axhline(-SEUIL_D1 * ix(g, BASE[g], fee)["esperance_atr"], color=col, ls=":", lw=1.0,
                       label=f"seuil (d1), {fr(fee, 0)} bps")
        ax.axhline(0, color="0.3", lw=0.8)
        ax.axvline(BASE[g], color="0.4", ls="--", lw=0.9)
        ax.set_xticks(xs, [val_label(g, v) for v in xs])
        ax.set_title(TITRES[g], fontsize=10)
        ax.grid(alpha=0.3, lw=0.5)
        ax.legend(fontsize=7, frameon=False)
    axes[0].set_ylabel("Écart d'espérance par trade à RE-1 (ATR14(t)), IC 95 %", fontsize=9)
    fig.suptitle("EXP-C05 — Écart à RE-1 de chaque point de grille (H26)", fontsize=11)
    fig.tight_layout()
    _save(fig, "fig2_ecarts_a_RE1.png")
    plt.close(fig)


def fig_bandes(meta) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(17, 5.6))
    for ax, key, (yk, lk, hk), title, split, ylab in (
            (axes[0], "bandes_retrace", ("effet_stop", "effet_stop_lo", "effet_stop_hi"),
             "A — effet du stop SL-B 0 contre sans stop, par bande de retracement (trades de RE-1)", 2.5,
             "Effet par trade du stop (ATR14(t)), IC 95 %"),
            (axes[1], "bandes_nis", ("esp5", "esp5_lo", "esp5_hi"),
             "C — chaque signal de R2 joué seul, par bande de nis_z_100 (5 bps)", 1.5,
             "Espérance nette par signal (ATR14(t)), IC 95 %")):
        b = meta[key]
        x = np.arange(len(b))
        y, lo, hi = (np.array([_f(r[k]) for r in b]) for k in (yk, lk, hk))
        ax.errorbar(x, y, yerr=[y - lo, hi - y], fmt="o", color="k", capsize=3, ms=6)
        for i, r in enumerate(b):
            ax.annotate(f"n = {r['n']}", (i, hi[i]), textcoords="offset points", xytext=(0, 5), ha="center", fontsize=7)
        ax.axhline(0, color="0.3", lw=0.8)
        ax.axvline(split, color="0.4", ls="--", lw=0.9)
        ax.set_xticks(x, [r["bande"] for r in b], fontsize=8)
        ax.set_title(title, fontsize=10)
        ax.set_ylabel(ylab, fontsize=9)
        ax.grid(alpha=0.3, lw=0.5)
    fig.suptitle("EXP-C05 — Mécanismes (H26 ; tirets : seuil de RE-1)", fontsize=11)
    fig.tight_layout()
    _save(fig, "fig3_mecanismes_bandes.png")
    plt.close(fig)


def fig_equite(bars, trades, atr_bps) -> None:
    fig, axes = plt.subplots(1, 3, figsize=(18, 5.6), sharey=True)
    cmap = plt.get_cmap("viridis")
    for j, g in enumerate(GRILLES):
        vals = GRILLES[g]
        for k, v in enumerate(vals):
            tr = trades[(g, v)]
            w = risk_weights(atr_bps.reindex(tr.signal_bar.to_numpy()).to_numpy(dtype=float), C2B.RISK)
            eq = equity_curve_sized(bars, tr, 5.0, w)
            b = is_base(g, v)
            axes[j].plot(eq.index, 100 * (eq.to_numpy() - 1), color="k" if b else cmap(k / (len(vals) - 1)),
                         lw=2.0 if b else 1.0, label=val_label(g, v) + (" (RE-1)" if b else ""), zorder=3 if b else 2)
        axes[j].set_title(TITRES[g], fontsize=10)
        axes[j].grid(alpha=0.3, lw=0.5)
        axes[j].legend(fontsize=8, frameon=False)
    axes[0].set_ylabel("PnL net composé, 0,25 % par ATR, 5 bps (%)", fontsize=9)
    fig.suptitle("EXP-C05 — Capital de chaque point de grille (H26, 5 bps)", fontsize=11)
    fig.tight_layout()
    _save(fig, "fig4_courbes_equite.png")
    plt.close(fig)


# ── Programme ───────────────────────────────────────────────────────────────────
def _json(o):
    if isinstance(o, dict):
        return {str(k): _json(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
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
        res, ann = pd.read_csv(HERE / "resultats_C05.csv"), pd.read_csv(HERE / "annuel_C05.csv")
        write_report(res, ann, json.loads((HERE / "controles_C05.json").read_text(encoding="utf-8")))
        print(f"rapport_C05.md régénéré dans {HERE}")
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
    sens = Sens(bars, atlas, atr)
    meta["univers"] = check_universe(sens, masks)
    re1, fam1 = sens.run()
    meta["re1"] = check_re1(re1, fam1, bars, atr_bps, C2B.Engine(bars, atlas, atr, masks))
    print(f"contrôles préalables ({time.time() - t0:.0f} s)")
    rows, ann, trades = run_grid(sens, re1, fam1, bars, atr_bps)
    res, ann = pd.DataFrame(rows), pd.DataFrame(ann)
    meta["bandes_retrace"] = bands_retrace(sens, re1, bars, atr_bps)
    meta["bandes_nis"] = bands_nis(sens, re1, bars, atr_bps)
    ix = Index(res)
    meta["lecture"] = {f"{fee:g}": lecture(ix, fee) for fee in FEES}
    meta["duree_s"] = round(time.time() - t0)
    res.to_csv(HERE / "resultats_C05.csv", index=False, float_format="%.6g")
    ann.to_csv(HERE / "annuel_C05.csv", index=False, float_format="%.6g")
    (HERE / "controles_C05.json").write_text(json.dumps(_json(meta), ensure_ascii=False, indent=1), encoding="utf-8")
    FIG.mkdir(parents=True, exist_ok=True)
    fig_sensibilite(ix)
    fig_effets(ix)
    fig_bandes(json.loads(json.dumps(_json(meta))))
    fig_equite(bars, trades, atr_bps)
    write_report(res, ann, json.loads(json.dumps(_json(meta))))
    print(f"C05 : {len(res)} lignes de résultats en {meta['duree_s']} s ; rapport, tableaux et figures dans {HERE}")


if __name__ == "__main__":
    main()
