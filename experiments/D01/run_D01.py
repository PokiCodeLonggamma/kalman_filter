"""EXP-D01 — portabilité de RE-1 figée, sans réglage (« zero-shot ») : SOL/USD, CFD or, CFD WTI ; BTC en référence.

Usage, depuis la racine du dépôt : python experiments/D01/run_D01.py [--audit | --rapport]
  --audit   : étape 1, audit des données et des signaux, sans aucun PnL → audit_D01.json ;
  (défaut)  : étape 2, contrôles bloquants (ancre P6.5d, parité BTC avec C02bis, seuils gelés, audit sans défaut
              d'intégrité), puis RE-1 sur chaque actif non bloqué → resultats_D01.csv, annuel_D01.csv,
              diagnostics_D01.json, controles_D01.json, figures/, rapport_D01.md ;
  --rapport : régénère rapport_D01.md (narratif_D01.md rédigé à la main, puis annexes générées) sans recalcul.
Données : experiments/D01/donnees_D01.py (Coinbase SOL-USD, HistData XAUUSD et WTIUSD, FRED DCOILWTICO).

Cadrage (décisions du porteur, 2026-09-30)
- QUESTION : que devient RE-1, transférée telle quelle (seuils numériques de BTC, H = 26 barres de 30 min, moteur
  v2.1 par défaut), sur des marchés de structures différentes : SOL/USD (crypto 24/7, plus volatile), or au comptant
  (CFD, 23 h sur 24, 5 jours sur 7), pétrole WTI (CFD sur contrat à terme) ?
- PERTINENCE POUR LE FILTRE AKF : le déclencheur est invariant d'échelle (gain figé par le reset de P, R adaptatif
  selon rv/av, oscillateur normalisé par max|x1|) et les descripteurs de RE-1 sont en ATR14(t) et en z-score. Le
  transfert teste si la cinématique retenue sur BTC (R2 : sortie de range avec x1 déjà retourné, hors choc
  d'innovation nis_z_100) existe ailleurs à paramètres identiques. Les trous de séance des CFD (pause quotidienne,
  week-end) créent des innovations que BTC n'a pas.
- CE QUE LE PROTOCOLE MESURE RÉELLEMENT : pour chaque actif, sur sa période disponible jusqu'au 2025-12-31, les
  8 métriques nettes aux frais de l'actif, l'espérance en ATR et en bps avec IC par grappes mensuelles, le capital à
  0,25 % par ATR14(t) et à 1x, Long/Short, F2b/F3, stops de F3, années, terciles de volatilité, distribution de
  nis_z_100 face au seuil BTC, bandes de nis_z_100 (trades isolés, descriptif), et l'audit des données.
- CE QU'IL NE PERMET PAS DE CONCLURE : pas de validation sur le hold-out (ETH, XRP et 2026 restent scellés) ; pas de
  comparaison statistique ni de classement des actifs ; rien sur l'optimalité des seuils transférés ni sur D02 ;
  coûts réels non modélisés (spread, financement et swaps des CFD) ; sources (Coinbase, HistData) et périodes
  (SOL depuis 2021-06-17) différentes de celles de BTC (Bitstamp, 2020-2025).

Règle de lecture (fixée avant le calcul)
- D01 est descriptif : aucun seuil de réussite ou d'échec sur une métrique de performance, aucun classement des actifs,
  aucune modification, optimisation ni recalibration de RE-1, aucun actif retiré sur sa performance.
- Seul motif de blocage : validité technique ou qualité des données (empreinte, réserve 2026, doublons, désordre, prix
  non positifs, OHLC incohérents ; couverture contraire à la consigne du porteur ; proxy non validé). L'actif bloqué
  est documenté, jamais remplacé.
- Frais : SOL 5 et 10 bps (5 bps en lecture principale) ; XAU et WTI 4 bps ; BTC 5 et 10 bps en référence.
- Définitions : régimes de volatilité = terciles de l'ATR14(t) en bps des trades de RE-1 de l'actif ; bandes de
  nis_z_100 = bornes aux quantiles P70 à P90 de l'atlas BTC (valeurs gelées), chaque signal R2 joué seul avec
  l'enveloppe de RE-1 ; effet du stop de F3 = différence appariée RE-1 − RE-1 sans stop sur les trades F3 (mêmes
  entrées) ; distribution des trades = quantiles, moyenne winsorisée P1/P99, apport du décile supérieur.
"""
from __future__ import annotations

import importlib.util
import json
import sys
import time
import warnings
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "src"))

import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from anatomy import build_atlas  # noqa: E402
from categorization import add_derived  # noqa: E402
from config import DATA_RAW  # noqa: E402
from envelope import risk_weights, route_levels, trade_frame  # noqa: E402
from envelope.metrics import _boot_mean, _cluster_counts, _entry_month  # noqa: E402
from envelope.stops import _candidates  # noqa: E402
from estimand.stoploss import TRADE_COLUMNS, apply_stop  # noqa: E402
from marketdata import audit_bars  # noqa: E402
from strategy import (FLOOR, H, LEG_ATR_P50_BTC, NIS_Z100_P75_BTC, RISK_BPS, RULES, frozen_masks,  # noqa: E402
                      load_asset, metrics, run_re1, sample_years)
from utils.data_loader import meta_path  # noqa: E402


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


C2B = _load("run_C02bis", ROOT / "experiments" / "C02bis" / "run_C02bis.py")
fr, sg, pct, spct, n_fr, ci, table = C2B.fr, C2B.sg, C2B.pct, C2B.spct, C2B.n_fr, C2B.ci, C2B.table

RAW = ROOT / "data" / "raw"
FIG = HERE / "figures"
N_BOOT = 2000
QS = (10, 25, 50, 75, 90)
NIS_PS = (0.70, 0.75, 0.80, 0.85, 0.90)
BPS = 1e4

BTC_DOC = {
    "instrument": "BTC/USD, carnet spot de Bitstamp (TradingView : BITSTAMP:BTCUSD)",
    "nature": "spot crypto, cotation en dollars américains", "ticker": "btcusd (Bitstamp)",
    "continuite": "sans objet : instrument spot, série unique", "rolls": "sans objet", "ajustements": "aucun",
    "timezone": "UTC", "horaires": "cotation continue 24/7",
    "construction_barres": "bougies 30 min natives de l'API OHLC publique de Bitstamp (step 1800)",
    "couverture_demandee": "2020-01-01 → 2025-12-31 (lecture tronquée avant 2026)",
}
ASSETS = {
    "BTC": {"nom": "BTC/USD (Bitstamp, référence)", "csv": DATA_RAW, "fees": (5.0, 10.0)},
    "SOL": {"nom": "SOL/USD (Coinbase)", "csv": RAW / "coinbase_solusd_30m.csv", "fees": (5.0, 10.0)},
    "XAU": {"nom": "CFD or XAU/USD (HistData)", "csv": RAW / "histdata_xauusd_30m.csv", "fees": (4.0,)},
    "WTI": {"nom": "CFD WTI (HistData)", "csv": RAW / "histdata_wtiusd_30m.csv", "fees": (4.0,),
            "bloque": "couverture 2020-01-01 → 2023-12-01 : HistData ne publie pas WTIUSD pour 2024 et 2025, contre "
                      "la condition « au moins 2020-2025 » du porteur. Par ailleurs, l'audit montre un CFD de contrat "
                      "du mois non ajusté, roulé autour de l'échéance : la série porte chaque mois un saut égal à "
                      "l'écart de calendrier (règle non publiée par la source). Série auditée, aucun backtest avant "
                      "décision du porteur."},
}
DOC_KEYS = ["instrument", "nature", "ticker", "continuite", "rolls", "ajustements", "prix", "timezone", "horaires",
            "construction_barres", "couverture_demandee", "limite", "sources_ecartees", "statut"]
INTEGRITE = ("doublons", "desordre", "prix_non_positifs", "incoherences_ohlc")


# ── Outils ──────────────────────────────────────────────────────────────────────
def q(x, ps=QS) -> dict:
    x = np.asarray(x, dtype=float)
    x = x[np.isfinite(x)]
    return {f"P{p}": float(np.percentile(x, p)) for p in ps} if len(x) else {}


def boot_ci(v, months, keep=None, seed: int = 0) -> tuple[float, float, float]:
    """Moyenne de `v` restreinte à `keep`, IC 95 % par grappes mensuelles d'entrée (tirages de `_cluster_counts`)."""
    v = np.asarray(v, dtype=float)
    keep = np.ones(len(v), dtype=bool) if keep is None else np.asarray(keep, dtype=bool)
    if not keep.any():
        return np.nan, np.nan, np.nan
    w, inv, g = _cluster_counts(months, N_BOOT, seed)
    b = _boot_mean(w, inv, g, v, keep)
    lo, hi = np.nanpercentile(b, [2.5, 97.5])
    return float(v[keep].mean()), float(lo), float(hi)


def jsonable(o):
    if isinstance(o, dict):
        return {str(k): jsonable(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [jsonable(v) for v in o]
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating,)):
        return None if np.isnan(o) else float(o)
    if isinstance(o, float) and np.isnan(o):
        return None
    return o


def asset_doc(key: str) -> dict:
    a = ASSETS[key]
    meta = json.loads(meta_path(a["csv"]).read_text(encoding="utf-8"))
    doc = dict(BTC_DOC) if key == "BTC" else {k: meta[k] for k in DOC_KEYS if meta.get(k)}
    doc.update({"source": meta.get("source"), "sha256": meta.get("sha256"), "premiere_barre": meta.get("first"),
                "derniere_barre": meta.get("last"), "barres": meta.get("n_rows")})
    for k in ("n_barres_un_seul_quart_d_heure", "n_barres_moins_de_30_minutes", "minutes_sources"):
        if k in meta:
            doc[k] = meta[k]
    dups = [f.get("doublons_exacts_supprimes") for f in meta.get("archives", []) if f.get("doublons_exacts_supprimes")]
    if dups:
        doc["doublons_exacts_supprimes"] = {"minutes": int(sum(d["n"] for d in dups)),
                                            "dates": [x for d in dups for x in d["dates"]]}
    return doc


def prepare(key: str) -> dict:
    """Barres (empreinte vérifiée, tronquées avant 2026), atlas des signaux, ATR, masques aux seuils BTC gelés."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")                       # trous signalés par load_ohlc : mesurés par l'audit
        df, bars = load_asset(ASSETS[key]["csv"])
    atlas, f, _, atr = build_atlas(df)
    fam, m = frozen_masks(atlas)
    atr_bps = pd.Series(atlas.atr14_bps.to_numpy(), index=atlas.bar_index.to_numpy())
    return {"df": df, "bars": bars, "atlas": atlas, "f": f, "atr": atr, "atr_bps": atr_bps, "fam": fam, "m": m}


# ── Étape 1 : audit des données et des signaux (aucun PnL) ──────────────────────
def session_profile(t: pd.Series) -> dict:
    """Heures UTC sans barre (janvier, juillet) ; pour une cotation en séances : pause quotidienne lue en heure de New
    York semaine par semaine (lundi-jeudi) et heure d'ouverture du dimanche (contrôle du fuseau de la source)."""
    out = {}
    for name, month in (("janvier", 1), ("juillet", 7)):
        s = t[t.dt.month == month]
        cnt = s.dt.hour.value_counts().reindex(range(24), fill_value=0)
        out[f"heures_utc_sans_barre_{name}"] = [int(h) for h in cnt.index[cnt == 0]]
    out["barres_le_samedi"] = int((t.dt.dayofweek == 5).sum())
    ny = t.dt.tz_convert("America/New_York")
    wd = ny[ny.dt.dayofweek <= 3]
    weeks = {}
    for wk, g in wd.groupby(wd.dt.tz_localize(None).dt.to_period("W-SUN")):
        cnt = g.dt.hour.value_counts().reindex(range(24), fill_value=0)
        weeks[str(wk.start_time.date())] = tuple(int(h) for h in range(24) if cnt[h] == 0)
    w = pd.Series(weeks, dtype=object)
    if len(w) and (w.map(len) > 0).mean() > 0.5:                     # cotation en séances
        sun = ny[ny.dt.dayofweek == 6]
        out["pause_new_york"] = {"semaines": int(len(w)), "pause_17h_exactement": int((w == (17,)).sum()),
                                 "pause_17h_et_autres_heures": int(w.map(lambda x: 17 in x and x != (17,)).sum()),
                                 "sans_pause_17h": int(w.map(lambda x: 17 not in x).sum())}
        out["ouverture_dimanche_heure_new_york"] = {int(k): int(v) for k, v in
                                                    sun.groupby(sun.dt.date).min().dt.hour.value_counts().items()}
    return out


def signal_profile(p: dict) -> dict:
    atlas, bars, fam, m = p["atlas"], p["bars"], p["fam"], p["m"]
    d = add_derived(atlas)
    nis = d.nis_z_100.to_numpy(dtype=float)
    months = (bars.time.iat[-1] - bars.time.iat[0]) / pd.Timedelta(days=365.25 / 12)
    yr = []
    for y, g in atlas.groupby("year"):
        sel = (atlas.year == y).to_numpy()
        yr.append({"annee": int(y), "signaux": int(len(g)), "atr14_bps_median": float(g.atr14_bps.median()),
                   "part_nis_au_dessus_seuil_btc": float((nis[sel] > NIS_Z100_P75_BTC).mean()),
                   "univers_RE1": int(m["R2"][sel].sum())})
    r2 = m["R2_avant_nis"]
    return {"n_signaux": int(len(atlas)), "signaux_par_mois": float(len(atlas) / months),
            "part_flips": float(atlas.is_flip.mean()), "part_x1_retourne": float(d.x1_already_flipped_at_t.mean()),
            "leg_atr": q(d.leg_atr), "retrace_ratio": q(d.retrace_ratio), "nis_z_100": q(nis),
            "atr14_bps": q(d.atr14_bps), "prev_seg_len": q(d.prev_seg_len),
            "mediane_locale_leg_atr": float(np.median(d.leg_atr)), "p75_local_nis_z_100": float(np.nanquantile(nis, .75)),
            "part_leg_sous_seuil_btc": float((d.leg_atr < LEG_ATR_P50_BTC).mean()),
            "part_nis_au_dessus_seuil_btc": float((nis > NIS_Z100_P75_BTC).mean()),
            "part_nis_au_dessus_seuil_btc_dans_R2": float((nis[r2] > NIS_Z100_P75_BTC).mean()) if r2.any() else None,
            "nis_nan": int(np.isnan(nis).sum()),
            "familles": {k: int((fam == k).sum()) for k in ("F1", "F2a", "F2b", "F3", "F4", "F5")},
            "regimes": {"R1": int(m["R1"].sum()), "R2_avant_nis": int(r2.sum()), "R3": int(m["R3"].sum()),
                        "hors_regimes": int((~(m["R1"] | r2 | m["R3"])).sum())},
            "nis_exclus": int(m["nis_exclus"].sum()), "univers_RE1": int(m["R2"].sum()), "F2b": int(m["F2b"].sum()),
            "F3": int(m["F3"].sum()), "par_annee": yr}


TRANCHES = ["1-5", "6-10", "11-15", "16-20", "21-25", "26-31"]


def wti_vs_spot(bars: pd.DataFrame) -> dict:
    """CFD WTI contre spot WTI Cushing de l'EIA (qui suit le contrat échéant jusqu'à son expiration) : close de la barre
    14:00-14:30 heure de New York (clôture NYMEX). Un CFD rétro-ajusté s'écarterait durablement du spot ; un CFD de
    contrat du mois non ajusté colle au spot, sauf entre son roulement et l'échéance, où l'écart vaut l'écart de
    calendrier : la série du CFD saute alors de cet écart."""
    ref = pd.read_csv(RAW / "fred_dcoilwtico.csv", parse_dates=["date"]).dropna()
    ny = bars.time.dt.tz_convert("America/New_York")
    sel = ((ny.dt.hour == 14) & (ny.dt.minute == 0)).to_numpy()
    cfd = pd.Series(bars.close.to_numpy()[sel], index=ny[sel].dt.tz_localize(None).dt.normalize().to_numpy())
    j = pd.concat([cfd.rename("cfd"), ref.set_index("date").valeur.rename("spot")], axis=1, join="inner").dropna()
    j["ecart"] = j.cfd - j.spot
    ex = j.drop(pd.to_datetime(["2020-04-20", "2020-04-21"]), errors="ignore")
    tranche = pd.cut(j.index.day, [0, 5, 10, 15, 20, 25, 31], labels=TRANCHES)
    big = j.ecart.abs() > 0.25
    apr = j.loc["2020-04-15":"2020-04-24"]
    return {"jours_communs": int(len(j)), "ecart_mediane": float(j.ecart.median()),
            "ecart_P5_P95": [float(j.ecart.quantile(.05)), float(j.ecart.quantile(.95))],
            "ecart_median_par_annee": {str(y): float(g.ecart.median()) for y, g in j.groupby(j.index.year)},
            "ecart_median_par_tranche_du_mois": {str(k): float(v) for k, v in
                                                 j.ecart.groupby(tranche, observed=True).median().items()},
            "jours_ecart_abs_sup_0_25": int(big.sum()),
            "jours_ecart_abs_sup_0_25_par_tranche": {str(k): int(v) for k, v in
                                                     big.groupby(tranche, observed=False).sum().items()},
            "correlation_variations_hors_20_21_avril_2020": {
                "pearson": float(ex.cfd.diff().corr(ex.spot.diff())),
                "spearman": float(ex.cfd.diff().corr(ex.spot.diff(), method="spearman"))},
            "exemple_echeance_juin_2021": [{"date": str(i.date()), "cfd": float(r.cfd), "spot": float(r.spot)}
                                           for i, r in j.loc["2021-06-16":"2021-06-24"].iterrows()],
            "avril_2020": [{"date": str(i.date()), "cfd": float(r.cfd), "spot": float(r.spot)}
                           for i, r in apr.iterrows()]}


def audit_asset(key: str) -> dict:
    p = prepare(key)
    a = audit_bars(p["df"])
    out = {"doc": asset_doc(key), "barres": a, "seances": session_profile(p["df"].time),
           "integrite": [f"{k} = {a[k]}" for k in INTEGRITE if a[k]], "signaux": signal_profile(p),
           "annees_echantillon": sample_years(p["bars"])}
    if key == "WTI":
        out["wti_contre_spot_eia"] = wti_vs_spot(p["bars"])
    if ASSETS[key].get("bloque"):
        out["bloque"] = ASSETS[key]["bloque"]
    return out


def run_audit() -> dict:
    t0 = time.time()
    res = {k: audit_asset(k) for k in ASSETS}
    res["seuils_btc"] = {"leg_atr_p50": LEG_ATR_P50_BTC, "nis_z_100_p75": NIS_Z100_P75_BTC}
    res["duree_s"] = round(time.time() - t0)
    (HERE / "audit_D01.json").write_text(json.dumps(jsonable(res), ensure_ascii=False, indent=1), encoding="utf-8")
    return res


# ── Étape 2 : contrôles bloquants ───────────────────────────────────────────────
def check_btc(p: dict) -> dict:
    """Ancre P6.5d ; RE-1 de la chaîne D01 = RE-1 de C02bis trade par trade et dans resultats_C02bis.csv."""
    out = {"ancre": C2B.check_anchor(p["bars"], p["f"])}
    d = add_derived(p["atlas"])
    if LEG_ATR_P50_BTC != float(np.median(d.leg_atr)) or NIS_Z100_P75_BTC != float(np.quantile(d.nis_z_100, .75)):
        raise SystemExit("seuils gelés différents des statistiques de l'atlas BTC : arrêt")
    tr, fam = run_re1(p["bars"], p["atlas"], p["atr"], p["m"])
    eng = C2B.Engine(p["bars"], p["atlas"], p["atr"], C2B.full_masks(p["atlas"]))
    ref, ref_fam = eng.run("R2", {"F2b": None, "F3": ("SL-B", 0.0)}, H, False)
    if not (tr.equals(ref) and fam.equals(ref_fam)):
        raise SystemExit("RE-1 (chaîne D01) : trades différents de C02bis : arrêt")
    if sample_years(p["bars"]) != 6.0:
        raise SystemExit("annualisation BTC différente de C02bis : arrêt")
    res = pd.read_csv(ROOT / "experiments" / "C02bis" / "resultats_C02bis.csv")
    cols = ["n_trades", "esperance_bps", "esperance_bps_lo", "esperance_bps_hi", "esperance_atr", "esperance_atr_lo",
            "esperance_atr_hi", "pnl_compose", "mdd_valorise", "pf", "wr", "pnl_compose_r25", "mdd_valorise_r25",
            "calmar_r25", "part_stop", "n_F2b", "n_F3", "esperance_atr_F2b", "esperance_atr_F3", "annees_atr_pos"]
    worst = 0.0
    for fee in (5.0, 10.0):
        got, _ = metrics(tr, p["bars"], p["atr_bps"], fee, int(p["m"]["R2"].sum()), fam, 6.0)
        g = res[(res.variante_seuils == C2B.ENTIER) & (res.configuration == "RE-1") & (res.H == H)
                & (res["mode"] == "cooldown") & (res.frais_bps == fee)].iloc[0]
        for c in cols:
            x, y = float(got[c]), float(g[c])
            if not np.isclose(x, y, rtol=1e-5, atol=1e-9):
                raise SystemExit(f"RE-1 BTC {fee:g} bps : {c} = {x} contre {y} dans C02bis : arrêt")
            worst = max(worst, abs(x - y) / max(abs(y), 1e-12))
    out.update({"trades": len(tr), "identiques_c02bis": True, "metriques_comparees": 2 * len(cols),
                "ecart_relatif_max": worst})
    return out


# ── Étape 2 : mesures par actif ─────────────────────────────────────────────────
def isolated(p: dict, mask: np.ndarray) -> pd.DataFrame:
    """Chaque signal du masque joué seul avec l'enveloppe de RE-1 (sans sélection séquentielle)."""
    atlas = p["atlas"]
    t, s, n = (atlas[c].to_numpy()[mask] for c in ("bar_index", "direction", "prev_seg_len"))
    r = add_derived(atlas).retrace_ratio.to_numpy()[mask]
    fam = np.where(r >= 0.85, "F3", "F2b")
    level = route_levels(p["bars"], t, s, np.asarray(p["atr"], dtype=float)[t], n, fam, RULES, FLOOR)
    _, t2, s2, e, x, dist = _candidates(p["bars"], t, s, H, level, "isolated")
    with np.errstate(invalid="ignore"):
        out = apply_stop(p["bars"], e, x, s2, dist)
    out = out.reset_index(drop=True)
    out["signal_bar"] = t2
    return out[TRADE_COLUMNS]


def net_atr(tr, atr_bps, fee) -> np.ndarray:
    return (tr.ret_gross_bps.to_numpy(dtype=float) - fee) / atr_bps.reindex(tr.signal_bar.to_numpy()).to_numpy()


def diagnostics(key: str, p: dict, tr: pd.DataFrame, fam: pd.Series, fee: float) -> dict:
    bars, atr_bps = p["bars"], p["atr_bps"]
    months = _entry_month(tr, bars)
    v = net_atr(tr, atr_bps, fee)
    vb = tr.ret_gross_bps.to_numpy(dtype=float) - fee
    f = fam.reindex(tr.signal_bar.to_numpy()).to_numpy()
    side = tr.side.to_numpy(dtype=np.int64)
    stop = tr.stop.to_numpy(dtype=bool)
    out = {}
    # distribution des trades
    lo, hi = np.percentile(v, [1, 99])
    k = max(1, int(round(0.1 * len(v))))
    top = np.sort(v)[-k:]
    out["distribution"] = {**q(v, (5, 10, 25, 50, 75, 90, 95)), "moyenne": float(v.mean()),
                           "moyenne_winsorisee_P1_P99": float(np.clip(v, lo, hi).mean()),
                           "apport_decile_superieur_par_trade": float(top.sum() / len(v)),
                           "part_decile_superieur": float(top.sum() / v.sum()) if v.sum() != 0 else None}
    # durée calendaire
    t = bars.time
    hours = (t.iloc[tr.exit_bar.to_numpy()].to_numpy() - t.iloc[tr.entry_bar.to_numpy()].to_numpy()) / np.timedelta64(1, "h")
    out["duree_calendaire_h"] = {"mediane": float(np.median(hours)), "P90": float(np.percentile(hours, 90)),
                                 "part_plus_de_24_h": float((hours > 24).mean())}
    # Long / Short × F2b / F3
    cells = []
    for fk in ("F2b", "F3", "tous"):
        for sk, sv in (("Long", 1), ("Short", -1), ("tous", 0)):
            keep = ((f == fk) if fk != "tous" else np.ones(len(f), bool)) & ((side == sv) if sv else True)
            e, elo, ehi = boot_ci(v, months, keep)
            cells.append({"famille": fk, "sens": sk, "n": int(keep.sum()), "esperance_atr": e, "lo": elo, "hi": ehi,
                          "esperance_bps": float(vb[keep].mean()) if keep.any() else None,
                          "contribution_atr": float(v[keep].sum() / len(v))})
    out["sens_familles"] = cells
    # stops de F3
    tr_ns, _ = run_re1(bars, p["atlas"], p["atr"], p["m"], rules={"F2b": None, "F3": None})
    if not all(np.array_equal(tr[c].to_numpy(), tr_ns[c].to_numpy()) for c in ("entry_bar", "side", "signal_bar")):
        raise SystemExit(f"{key} : RE-1 sans stop n'a pas les entrées de RE-1 : arrêt")
    d = (tr.ret_gross_bps.to_numpy(dtype=float) - tr_ns.ret_gross_bps.to_numpy(dtype=float)) \
        / atr_bps.reindex(tr.signal_bar.to_numpy()).to_numpy()
    f3 = f == "F3"
    eff = boot_ci(d, months, f3)
    m_ns, _ = metrics(tr_ns, bars, atr_bps, fee, int(p["m"]["R2"].sum()), fam, sample_years(bars), n_boot=200)
    out["stops_F3"] = {"n_F3": int(f3.sum()), "n_stoppes": int((stop & f3).sum()),
                       "part_stoppes_F3": float(stop[f3].mean()) if f3.any() else None,
                       "esperance_atr_stoppes": float(v[stop].mean()) if stop.any() else None,
                       "esperance_atr_F3_non_stoppes": float(v[f3 & ~stop].mean()) if (f3 & ~stop).any() else None,
                       "contribution_atr_stoppes": float(v[stop].sum() / len(v)),
                       "effet_stop_sur_F3_atr": eff[0], "effet_lo": eff[1], "effet_hi": eff[2],
                       "sans_stop_mdd_r25": m_ns["mdd_valorise_r25"], "sans_stop_calmar_r25": m_ns["calmar_r25"],
                       "sans_stop_pnl_r25": m_ns["pnl_compose_r25"], "sans_stop_mdd_1x": m_ns["mdd_valorise"],
                       "sans_stop_esperance_atr": m_ns["esperance_atr"]}
    # régimes de volatilité : terciles de l'ATR14(t) en bps des trades
    a = atr_bps.reindex(tr.signal_bar.to_numpy()).to_numpy()
    edges = np.quantile(a, [1 / 3, 2 / 3])
    terc = np.digitize(a, edges)
    rows = []
    for kk, name in enumerate(("T1 calme", "T2", "T3 agité")):
        keep = terc == kk
        e, elo, ehi = boot_ci(v, months, keep)
        eb, eblo, ebhi = boot_ci(vb, months, keep)
        rows.append({"tercile": name, "atr14_bps": [float(a[keep].min()), float(a[keep].max())], "n": int(keep.sum()),
                     "esperance_atr": e, "lo": elo, "hi": ehi, "esperance_bps": eb, "bps_lo": eblo, "bps_hi": ebhi,
                     "wr": float((vb[keep] > 0).mean()), "part_stoppes": float(stop[keep].mean())})
    out["volatilite"] = rows
    # bandes de nis_z_100 (bornes : quantiles de l'atlas BTC, gelées) — trades isolés, descriptif
    nis = add_derived(p["atlas"]).nis_z_100.to_numpy(dtype=float)
    edges_n = [-np.inf] + [BTC_NIS_Q[pp] for pp in NIS_PS] + [np.inf]
    r2 = p["m"]["R2_avant_nis"]
    iso = isolated(p, r2)
    iso_nis = pd.Series(nis, index=p["atlas"].bar_index.to_numpy()).reindex(iso.signal_bar.to_numpy()).to_numpy()
    vi = net_atr(iso, atr_bps, fee)
    mi = _entry_month(iso, bars)
    bands = []
    labels = ["≤ P70"] + [f"P{round(100 * NIS_PS[i])}–P{round(100 * NIS_PS[i + 1])}" for i in range(len(NIS_PS) - 1)] \
        + ["> P90"]
    for i, lab in enumerate(labels):
        keep = (iso_nis > edges_n[i]) & (iso_nis <= edges_n[i + 1])
        e, elo, ehi = boot_ci(vi, mi, keep)
        bands.append({"bande": lab, "bornes": [edges_n[i], edges_n[i + 1]], "n": int(keep.sum()),
                      "esperance_atr": e, "lo": elo, "hi": ehi})
    out["bandes_nis"] = {"n_signaux_R2": int(r2.sum()), "n_isoles": len(iso), "bandes": bands}
    return out


BTC_NIS_Q: dict = {}


def run_main() -> None:
    t0 = time.time()
    audit_path = HERE / "audit_D01.json"
    if not audit_path.exists():
        raise SystemExit("audit_D01.json absent : lancer d'abord --audit")
    audit = json.loads(audit_path.read_text(encoding="utf-8"))
    ctrl = {"seuils_btc": audit["seuils_btc"], "actifs": {}}
    preps = {}
    p_btc = prepare("BTC")
    ctrl["btc"] = check_btc(p_btc)
    d_btc = add_derived(p_btc["atlas"])
    BTC_NIS_Q.update({pp: float(np.quantile(d_btc.nis_z_100, pp)) for pp in NIS_PS})
    ctrl["quantiles_nis_btc"] = {f"P{round(100 * k)}": v for k, v in BTC_NIS_Q.items()}
    print(f"contrôles BTC passés ({time.time() - t0:.0f} s)")
    rows, years, diags = [], [], {}
    for key, a in ASSETS.items():
        au = audit[key]
        if a.get("bloque"):
            ctrl["actifs"][key] = {"statut": "bloqué", "motif": a["bloque"]}
            continue
        if au["integrite"]:
            ctrl["actifs"][key] = {"statut": "bloqué", "motif": "intégrité : " + " ; ".join(au["integrite"])}
            continue
        if au["doc"]["sha256"] != json.loads(meta_path(a["csv"]).read_text(encoding="utf-8"))["sha256"]:
            raise SystemExit(f"{key} : empreinte du CSV différente de l'audit : arrêt")
        p = p_btc if key == "BTC" else prepare(key)
        preps[key] = p
        tr, fam = run_re1(p["bars"], p["atlas"], p["atr"], p["m"])
        ny = sample_years(p["bars"])
        ctrl["actifs"][key] = {"statut": "mesuré", "annees": ny, "trades": len(tr), "candidats": int(p["m"]["R2"].sum())}
        diags[key] = {}
        for fee in a["fees"]:
            m, y = metrics(tr, p["bars"], p["atr_bps"], fee, int(p["m"]["R2"].sum()), fam, ny)
            hours = (p["bars"].time.iloc[tr.exit_bar.to_numpy()].to_numpy()
                     - p["bars"].time.iloc[tr.entry_bar.to_numpy()].to_numpy()) / np.timedelta64(1, "h")
            m.update({"actif": key, "frais_bps": fee, "duree_mediane_h": float(np.median(hours)),
                      "debut": str(p["bars"].time.iat[0]), "fin": str(p["bars"].time.iat[-1])})
            rows.append(m)
            y.insert(0, "actif", key)
            y.insert(1, "frais_bps", fee)
            years.append(y)
            diags[key][f"{fee:g}"] = diagnostics(key, p, tr, fam, fee)
            print(f"{key} {fee:g} bps : {len(tr)} trades, espérance {m['esperance_atr']:+.3f} ATR "
                  f"({time.time() - t0:.0f} s)")
    res = pd.DataFrame(rows)
    lead = ["actif", "frais_bps", "annees", "debut", "fin"]
    res = res[lead + [c for c in res.columns if c not in lead]]
    ann = pd.concat(years, ignore_index=True)
    ctrl["duree_s"] = round(time.time() - t0)
    res.to_csv(HERE / "resultats_D01.csv", index=False, float_format="%.6g")
    ann.to_csv(HERE / "annuel_D01.csv", index=False, float_format="%.6g")
    (HERE / "diagnostics_D01.json").write_text(json.dumps(jsonable(diags), ensure_ascii=False, indent=1),
                                               encoding="utf-8")
    (HERE / "controles_D01.json").write_text(json.dumps(jsonable(ctrl), ensure_ascii=False, indent=1),
                                             encoding="utf-8")
    FIG.mkdir(parents=True, exist_ok=True)
    figures(preps, res)
    write_report()
    print(f"D01 : {len(res)} lignes en {ctrl['duree_s']} s ; résultats, diagnostics, figures et rapport dans {HERE}")


# ── Figures ─────────────────────────────────────────────────────────────────────
COLORS = {"BTC": "#7f7f7f", "SOL": "#9467bd", "XAU": "#d4a017", "WTI": "#1f1f1f"}


def figures(preps: dict, res: pd.DataFrame) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(13, 4.8))
    for key, p in preps.items():
        fee = ASSETS[key]["fees"][0]
        tr, _ = run_re1(p["bars"], p["atlas"], p["atr"], p["m"])
        net = tr.ret_gross_bps.to_numpy(dtype=float) - fee
        w = risk_weights(p["atr_bps"].reindex(tr.signal_bar.to_numpy()).to_numpy(dtype=float), RISK_BPS)
        tx = p["bars"].time.iloc[tr.exit_bar.to_numpy()].to_numpy()
        axes[0].plot(tx, np.cumprod(1 + w * net / BPS), color=COLORS[key], label=f"{key} ({fee:g} bps)")
        axes[1].plot(tx, np.cumprod(1 + net / BPS), color=COLORS[key], label=f"{key} ({fee:g} bps)")
    for ax, ttl in zip(axes, ("Capital à 0,25 % par ATR14(t)", "Capital à 1x (notionnel fixe)")):
        ax.set_yscale("log")
        ax.set_title(f"RE-1 figée — {ttl}, aux sorties")
        ax.axhline(1, color="k", lw=0.6)
        ax.legend()
    fig.tight_layout()
    fig.savefig(FIG / "capital_D01.png", dpi=110)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(8, 4.5))
    for key, p in preps.items():
        nis = add_derived(p["atlas"]).nis_z_100.to_numpy(dtype=float)
        ax.hist(nis[np.isfinite(nis)], bins=np.linspace(-3, 8, 111), density=True, histtype="step", lw=1.4,
                color=COLORS[key], label=key)
    ax.axvline(NIS_Z100_P75_BTC, color="r", ls="--", label=f"seuil RE-1 (P75 BTC = {fr(NIS_Z100_P75_BTC, 3)})")
    ax.set_title("nis_z_100 à la barre du signal (tous les signaux de l'atlas)")
    ax.legend()
    fig.tight_layout()
    fig.savefig(FIG / "nis_D01.png", dpi=110)
    plt.close(fig)

    ann = pd.read_csv(HERE / "annuel_D01.csv")
    fig, ax = plt.subplots(figsize=(10, 4.5))
    keys = list(preps)
    yrs = sorted(ann.annee.unique())
    wdt = 0.8 / len(keys)
    for i, key in enumerate(keys):
        g = ann[(ann.actif == key) & (ann.frais_bps == ASSETS[key]["fees"][0])].set_index("annee").reindex(yrs)
        ax.bar(np.arange(len(yrs)) + i * wdt, g.esperance_atr, wdt, color=COLORS[key], label=key)
    ax.set_xticks(np.arange(len(yrs)) + 0.4 - wdt / 2, [str(y) for y in yrs])
    ax.axhline(0, color="k", lw=0.6)
    ax.set_title("Espérance nette par trade (ATR14(t)) par année d'entrée — frais de lecture principale")
    ax.legend()
    fig.tight_layout()
    fig.savefig(FIG / "annees_D01.png", dpi=110)
    plt.close(fig)


# ── Rapport ─────────────────────────────────────────────────────────────────────
def frais_cell(r) -> str:
    return f"{pct(r['part_frais'], 0)} ; {pct(r['part_frais_r25'], 0)}"


def row8(r) -> list:
    return [f"{r['actif']} {fr(r['frais_bps'], 0)} bps",
            f"{spct(r['pnl_compose_r25'])} ; {spct(r['pnl_compose'])} ; {sg(r['pnl_bps'], 0)}",
            f"{fr(r['pf'], 2)} ; {fr(r['pf_r25'], 2)}", pct(r["wr"]),
            f"{ci(r['esperance_bps'], r['esperance_bps_lo'], r['esperance_bps_hi'], 1)} ; "
            f"{ci(r['esperance_atr'], r['esperance_atr_lo'], r['esperance_atr_hi'], 3)}",
            f"{pct(r['mdd_valorise_r25'])} ; {pct(r['mdd_valorise'], 1)}",
            f"{n_fr(r['n_trades'])} ({fr(r['trades_par_mois'], 1)}) ; {pct(r['part_stop'], 0)}",
            f"{fr(r['duree_mediane'], 0)} ; {fr(r['duree_mediane_h'], 1)} h", frais_cell(r)]


HEAD8 = ["Actif, frais", "PnL net : 0,25 %/ATR ; 1x ; bps cumulés (1x)", "PF : 1x ; pondéré", "WR",
         "Espérance : bps [IC] ; ATR [IC]", "MDD valorisé : 0,25 %/ATR ; 1x", "Trades (par mois) ; stoppés",
         "Durée médiane : barres ; calendaire", "Part des frais : 1x ; pondérée"]


def rowrisk(r) -> list:
    return [f"{r['actif']} {fr(r['frais_bps'], 0)} bps", fr(r["annees"], 2),
            f"{spct(r['cagr_r25'], 1)} ; {fr(r['calmar_r25'], 2)}", f"{spct(r['cagr_1x'], 1)} ; {fr(r['calmar_1x'], 2)}",
            f"{pct(r['exposition_moyenne_r25'], 0)} ; {pct(r['part_plafonnee_r25'], 0)}",
            f"{sg(r['long_atr'], 3)} / {sg(r['short_atr'], 3)}",
            ci(r["timing_atr"], r["timing_atr_lo"], r["timing_atr_hi"], 3),
            ci(r["timing_bps"], r["timing_bps_lo"], r["timing_bps_hi"], 1),
            f"{n_fr(r['n_F2b'])} ; {sg(r['esperance_atr_F2b'], 3)}", f"{n_fr(r['n_F3'])} ; {sg(r['esperance_atr_F3'], 3)}"]


HEADRISK = ["Actif, frais", "Années", "0,25 %/ATR : CAGR ; Calmar", "1x : CAGR ; Calmar",
            "Exposition moyenne ; trades plafonnés à 1x", "Long / Short (ATR)", "Timing ATR [IC]", "Timing bps [IC]",
            "F2b : n ; ATR", "F3 : n ; ATR"]


def section_controles(ctrl: dict) -> str:
    b = ctrl["btc"]
    lines = ["## A. Contrôles bloquants et conventions", "",
             f"- Ancre P6.5d reproduite : {n_fr(b['ancre']['sans_stop']['n_trades'])} trades sans stop, "
             f"{n_fr(b['ancre']['stop_2_5']['n_trades'])} avec un stop de 2,5 %.",
             f"- Seuils gelés égaux aux statistiques de l'atlas BTC : médiane de leg_atr {fr(LEG_ATR_P50_BTC, 4)}, "
             f"P75 de nis_z_100 {fr(NIS_Z100_P75_BTC, 4)} (précision machine).",
             f"- BTC par la chaîne D01 (`strategy.re1`) : {n_fr(b['trades'])} trades identiques à C02bis ; "
             f"{b['metriques_comparees']} métriques comparées à `resultats_C02bis.csv`, écart relatif maximal "
             f"{C2B.sci(b['ecart_relatif_max']) if b['ecart_relatif_max'] > 0 else '0'}.",
             "- Capital : 0,25 % par ATR14(t) (poids min(1 ; 25 bps / ATR14 en bps), levier ≤ 1x) et notionnel 1x. "
             "IC 95 % par bootstrap de grappes de mois d'entrée, 2 000 tirages.",
             "- Annualisation : 6 ans (2020-01-01 → 2025-12-31) moins le temps écoulé entre le 1er janvier 2020 et la "
             "première barre de l'actif (convention de C02bis).", ""]
    rows = []
    for k, v in ctrl["actifs"].items():
        rows.append([ASSETS[k]["nom"], v["statut"], v.get("motif", "") or
                     f"{n_fr(v['trades'])} trades sur {n_fr(v['candidats'])} candidats ; {fr(v['annees'], 2)} ans"])
    return "\n".join(lines + [table(["Actif", "Statut", "Détail"], rows)])


def section_donnees(audit: dict) -> str:
    out = ["## B. Données : instruments et audit (étape 1, avant tout PnL)", ""]
    keys = ["instrument", "nature", "ticker", "continuite", "rolls", "ajustements", "prix", "timezone", "horaires",
            "construction_barres", "couverture_demandee", "limite"]
    noms = {"instrument": "Instrument", "nature": "Nature", "ticker": "Ticker", "continuite": "Continuité",
            "rolls": "Roulements", "ajustements": "Ajustements", "prix": "Prix", "timezone": "Fuseau",
            "horaires": "Horaires", "construction_barres": "Construction des barres 30 min",
            "couverture_demandee": "Couverture", "limite": "Limite"}
    rows = [[noms[k]] + [audit[a]["doc"].get(k, "—") for a in ASSETS] for k in keys]
    rows.append(["Barres (première → dernière)"] + [
        f"{n_fr(audit[a]['barres']['n_barres'])} ({audit[a]['barres']['premiere'][:16]} → "
        f"{audit[a]['barres']['derniere'][:16]})" for a in ASSETS])
    out += [table(["Champ"] + [ASSETS[a]["nom"] for a in ASSETS], rows), ""]
    rows = []
    for a in ASSETS:
        b, s = audit[a]["barres"], audit[a]["seances"]
        tr = b["trous"]
        cl = tr["classes"]
        rows.append([a, pct(b["part_barres_24_7"], 1), f"{n_fr(tr['n'])} ; {n_fr(tr['barres_manquantes'])}",
                     f"{cl['<= 2 h']['n']} ; {cl['<= 3 jours']['n']} ; {cl['> 3 jours']['n']}",
                     f"{tr['plus_longs'][0]['apres'][:16]} ({fr(tr['plus_longs'][0]['duree_h'], 1)} h)"
                     if tr["plus_longs"] else "—",
                     " ; ".join(audit[a]["integrite"]) or "aucune",
                     f"{n_fr(b['barres_plates'])} ; " + ("source sans volume" if b.get("barres_volume_nul") == b["n_barres"]
                                                            else n_fr(b.get("barres_volume_nul", 0))),
                     (f"{s['pause_new_york']['pause_17h_exactement']} / {s['pause_new_york']['semaines']}"
                      if "pause_new_york" in s else "sans objet (24/7)"),
                     fr(b["sauts"]["ecart_ouverture_bps"].get("P99.9", np.nan), 0) + " ; " +
                     fr(b["sauts"]["ecart_ouverture_apres_trou_bps"].get("P50", np.nan), 1)])
    out += [table(["Actif", "Barres / cotation 24/7", "Trous : n ; barres manquantes", "Trous ≤ 2 h ; ≤ 3 j ; > 3 j",
                   "Plus long trou (début)", "Défauts d'intégrité", "Barres plates ; volume nul",
                   "Semaines à pause seule 17:00-18:00 New York", "Écart d'ouverture (bps) : P99,9 ; médiane après trou"],
                  rows), ""]
    for a in ASSETS:
        d = audit[a]["doc"]
        if d.get("doublons_exacts_supprimes"):
            dd = d["doublons_exacts_supprimes"]
            out.append(f"- {a} : {dd['minutes']} minutes répétées à l'identique supprimées à la construction "
                       f"({', '.join(dd['dates'])}), une heure par an le lundi qui suit la fin de l'heure d'été "
                       "européenne ; continuité des prix vérifiée.")
    w = audit["WTI"].get("wti_contre_spot_eia")
    if w:
        c = w["correlation_variations_hors_20_21_avril_2020"]
        par_an = " ; ".join(f"{y} {sg(v, 2)}" for y, v in w["ecart_median_par_annee"].items())
        par_tr = " ; ".join(f"{k} {sg(v, 2)}" for k, v in w["ecart_median_par_tranche_du_mois"].items())
        n_tr = " ; ".join(f"{k} {v}" for k, v in w["jours_ecart_abs_sup_0_25_par_tranche"].items())
        juin = " ; ".join(f"{x['date'][5:]} {fr(x['cfd'], 2)} / {fr(x['spot'], 2)}" for x in w["exemple_echeance_juin_2021"])
        avr = " ; ".join(f"{x['date'][5:]} {fr(x['cfd'], 2)} / {fr(x['spot'], 2)}" for x in w["avril_2020"])
        out += ["", "**CFD WTI contre le spot WTI Cushing de l'EIA** (close de la barre 14:00-14:30 heure de New York ; "
                    "le spot suit le contrat échéant jusqu'à son expiration) :",
                f"- {n_fr(w['jours_communs'])} jours communs ; écart CFD − spot médian {sg(w['ecart_mediane'], 2)} $ "
                f"(par année : {par_an}) ; P5-P95 [{sg(w['ecart_P5_P95'][0], 2)} ; {sg(w['ecart_P5_P95'][1], 2)}] $.",
                f"- Écart médian par tranche de jours du mois : {par_tr} $. Jours à plus de 0,25 $ d'écart : "
                f"{n_fr(w['jours_ecart_abs_sup_0_25'])}, par tranche du mois : {n_tr}.",
                f"- Corrélation des variations quotidiennes, hors 20-21 avril 2020 : Pearson {fr(c['pearson'], 3)}, "
                f"Spearman {fr(c['spearman'], 3)}.",
                f"- Échéance de juin 2021 (contrat de juillet, expiré le 22/06), CFD / spot : {juin}.",
                f"- Avril 2020, CFD / spot : {avr}."]
    for a in ASSETS:
        if audit[a].get("bloque"):
            out += ["", f"**{a} bloqué** : {audit[a]['bloque']}"]
    return "\n".join(out)


def section_signaux(audit: dict) -> str:
    out = ["## C. Signaux : distributions face aux seuils BTC gelés (descriptif)", ""]
    rows = []
    for a in ASSETS:
        s = audit[a]["signaux"]
        rows.append([a, f"{n_fr(s['n_signaux'])} ({fr(s['signaux_par_mois'], 1)})", pct(s["part_x1_retourne"], 1),
                     f"{fr(s['leg_atr']['P50'], 2)} [{fr(s['leg_atr']['P25'], 2)} ; {fr(s['leg_atr']['P75'], 2)}]",
                     pct(s["part_leg_sous_seuil_btc"], 1),
                     f"{fr(s['retrace_ratio']['P50'], 2)} [{fr(s['retrace_ratio']['P25'], 2)} ; "
                     f"{fr(s['retrace_ratio']['P75'], 2)}]",
                     f"{fr(s['nis_z_100']['P50'], 2)} ; P75 local {fr(s['p75_local_nis_z_100'], 3)}",
                     f"{pct(s['part_nis_au_dessus_seuil_btc'], 1)} ; {pct(s['part_nis_au_dessus_seuil_btc_dans_R2'], 1)}",
                     f"{fr(s['atr14_bps']['P50'], 1)} [{fr(s['atr14_bps']['P10'], 1)} ; {fr(s['atr14_bps']['P90'], 1)}]"])
    out += [table(["Actif", "Signaux (par mois)", "x1 déjà retourné", "leg_atr P50 [P25 ; P75]",
                   f"leg_atr < {fr(LEG_ATR_P50_BTC, 4)} (seuil BTC)", "retrace_ratio P50 [P25 ; P75]",
                   "nis_z_100 P50 ; P75 local", f"nis_z_100 > {fr(NIS_Z100_P75_BTC, 4)} : tous ; dans R2",
                   "ATR14 bps P50 [P10 ; P90]"], rows), ""]
    rows = []
    for a in ASSETS:
        s = audit[a]["signaux"]
        fa, rg = s["familles"], s["regimes"]
        rows.append([a, " ; ".join(f"{k} {n_fr(v)}" for k, v in fa.items()),
                     f"{n_fr(rg['R1'])} ; {n_fr(rg['R2_avant_nis'])} ; {n_fr(rg['R3'])} ; {n_fr(rg['hors_regimes'])}",
                     n_fr(s["nis_exclus"]), f"{n_fr(s['univers_RE1'])} ({n_fr(s['F2b'])} ; {n_fr(s['F3'])})"])
    out += [table(["Actif", "Familles (seuil leg BTC)", "R1 ; R2 avant nis ; R3 ; hors régimes", "R2 écartés par nis",
                   "Univers RE-1 (F2b ; F3)"], rows)]
    return "\n".join(out)


def section_metriques(res: pd.DataFrame) -> str:
    rows = [row8(r) for _, r in res.iterrows()]
    rows2 = [rowrisk(r) for _, r in res.iterrows()]
    return "\n".join(["## D. Tableau standard (8 métriques nettes)", "", table(HEAD8, rows), "",
                      "## E. Risque, sens, timing et sous-familles", "", table(HEADRISK, rows2)])


def section_diag(diags: dict, res: pd.DataFrame) -> str:
    out = ["## F. Sens × sous-famille (espérance nette par trade, ATR [IC] ; contribution à l'espérance totale)", ""]
    rows = []
    for a, dd in diags.items():
        fee = f"{ASSETS[a]['fees'][0]:g}"
        for c in dd[fee]["sens_familles"]:
            rows.append([f"{a} {fee} bps", c["famille"], c["sens"], n_fr(c["n"]), ci(c["esperance_atr"], c["lo"], c["hi"], 3),
                         sg(c["esperance_bps"], 1), sg(c["contribution_atr"], 3)])
    out += [table(["Actif", "Famille", "Sens", "n", "Espérance ATR [IC]", "Espérance bps", "Contribution ATR"], rows), ""]
    out += ["## G. Stops de F3 (SL-B à l'extremum) : fréquence et contribution", ""]
    rows = []
    for a, dd in diags.items():
        fee = f"{ASSETS[a]['fees'][0]:g}"
        s = dd[fee]["stops_F3"]
        r = res[(res.actif == a) & (res.frais_bps == float(fee))].iloc[0]
        rows.append([f"{a} {fee} bps", f"{n_fr(s['n_stoppes'])} / {n_fr(s['n_F3'])} ({pct(s['part_stoppes_F3'], 0)})",
                     f"{sg(s['esperance_atr_stoppes'], 2)} ; {sg(s['esperance_atr_F3_non_stoppes'], 2)}",
                     sg(s["contribution_atr_stoppes"], 3), ci(s["effet_stop_sur_F3_atr"], s["effet_lo"], s["effet_hi"], 3),
                     f"{pct(r['mdd_valorise_r25'])} contre {pct(s['sans_stop_mdd_r25'])}",
                     f"{fr(r['calmar_r25'], 2)} contre {fr(s['sans_stop_calmar_r25'], 2)}",
                     f"{pct(r['mdd_valorise'], 1)} contre {pct(s['sans_stop_mdd_1x'], 1)}"])
    out += [table(["Actif", "Stoppés / F3", "Espérance ATR : stoppés ; F3 non stoppés", "Contribution des stoppés (ATR)",
                   "Effet apparié du stop sur F3 (ATR [IC])", "MDD 0,25 %/ATR : RE-1 contre sans stop",
                   "Calmar : RE-1 contre sans stop", "MDD 1x : RE-1 contre sans stop"], rows), ""]
    out += ["## H. Distribution des trades (espérance nette en ATR, frais de lecture principale)", ""]
    rows = []
    for a, dd in diags.items():
        fee = f"{ASSETS[a]['fees'][0]:g}"
        s = dd[fee]["distribution"]
        h = dd[fee]["duree_calendaire_h"]
        rows.append([f"{a} {fee} bps", f"{sg(s['P10'], 2)} ; {sg(s['P25'], 2)} ; {sg(s['P50'], 2)} ; {sg(s['P75'], 2)} ; "
                     f"{sg(s['P90'], 2)}", f"{sg(s['moyenne'], 3)} ; {sg(s['moyenne_winsorisee_P1_P99'], 3)}",
                     f"{sg(s['apport_decile_superieur_par_trade'], 3)} ("
                     + (pct(s['part_decile_superieur'], 0) if s['moyenne'] > 0 else "espérance totale ≤ 0") + ")",
                     f"{fr(h['mediane'], 1)} ; {fr(h['P90'], 1)} ; {pct(h['part_plus_de_24_h'], 0)}"])
    out += [table(["Actif", "P10 ; P25 ; P50 ; P75 ; P90", "Moyenne ; winsorisée P1/P99",
                   "Apport du décile supérieur par trade (part du total)",
                   "Durée calendaire (h) : médiane ; P90 ; part > 24 h"], rows), ""]
    out += ["## I. Régimes de volatilité (terciles de l'ATR14(t) en bps des trades de l'actif)", ""]
    rows = []
    for a, dd in diags.items():
        fee = f"{ASSETS[a]['fees'][0]:g}"
        for t in dd[fee]["volatilite"]:
            rows.append([f"{a} {fee} bps", t["tercile"], f"{fr(t['atr14_bps'][0], 1)} – {fr(t['atr14_bps'][1], 1)}",
                         n_fr(t["n"]), ci(t["esperance_atr"], t["lo"], t["hi"], 3),
                         ci(t["esperance_bps"], t["bps_lo"], t["bps_hi"], 1), pct(t["wr"], 1), pct(t["part_stoppes"], 0)])
    out += [table(["Actif", "Tercile", "ATR14 (bps)", "n", "Espérance ATR [IC]", "Espérance bps [IC]", "WR", "Stoppés"],
                  rows), ""]
    out += ["## J. nis_z_100 : bandes de l'univers R2 avant exclusion (trades isolés, bornes aux quantiles de l'atlas BTC)",
            "", "Descriptif : chaque signal R2 joué seul avec l'enveloppe de RE-1, sans sélection séquentielle. "
                "Rien n'en est tiré pour l'exécution.", ""]
    rows = []
    for a, dd in diags.items():
        fee = f"{ASSETS[a]['fees'][0]:g}"
        bn = dd[fee]["bandes_nis"]
        rows.append([f"{a} {fee} bps"] + [f"{n_fr(b['n'])} : {ci(b['esperance_atr'], b['lo'], b['hi'], 2)}"
                                          for b in bn["bandes"]])
    labels = [b["bande"] for b in next(iter(diags.values()))[f"{ASSETS[next(iter(diags))]['fees'][0]:g}"]["bandes_nis"]["bandes"]]
    out += [table(["Actif"] + [f"{lab} (BTC)" for lab in labels], rows)]
    return "\n".join(out)


def section_annees(ann: pd.DataFrame) -> str:
    out = ["## K. Stabilité annuelle (année d'entrée)", ""]
    rows = []
    for (a, fee), g in ann.groupby(["actif", "frais_bps"], sort=False):
        for _, r in g.iterrows():
            rows.append([f"{a} {fr(fee, 0)} bps", int(r["annee"]), n_fr(r["n_trades"]), sg(r["esperance_atr"], 3),
                         sg(r["esperance_bps"], 1), spct(r["pnl_compose_r25"], 1), spct(r["pnl_compose"], 1),
                         f"{sg(r['long_atr'], 2)} / {sg(r['short_atr'], 2)}"])
    return "\n".join(out + [table(["Actif", "Année", "Trades", "Espérance ATR", "Espérance bps", "PnL 0,25 %/ATR",
                                   "PnL 1x", "Long / Short ATR"], rows)])


def write_report() -> None:
    audit = json.loads((HERE / "audit_D01.json").read_text(encoding="utf-8"))
    parts = []
    narr = HERE / "narratif_D01.md"
    parts.append(narr.read_text(encoding="utf-8").rstrip() if narr.exists() else "# EXP-D01 (narratif à rédiger)")
    parts += ["", "---", "", "# Annexes chiffrées (générées par `run_D01.py`)", ""]
    ctrl_p = HERE / "controles_D01.json"
    if ctrl_p.exists():
        ctrl = json.loads(ctrl_p.read_text(encoding="utf-8"))
        res, ann = pd.read_csv(HERE / "resultats_D01.csv"), pd.read_csv(HERE / "annuel_D01.csv")
        diags = json.loads((HERE / "diagnostics_D01.json").read_text(encoding="utf-8"))
        parts += [section_controles(ctrl), "", section_donnees(audit), "", section_signaux(audit), "",
                  section_metriques(res), "", section_diag(diags, res), "", section_annees(ann), "",
                  "Figures : `figures/capital_D01.png`, `figures/nis_D01.png`, `figures/annees_D01.png`."]
    else:
        parts += [section_donnees(audit), "", section_signaux(audit)]
    (HERE / "rapport_D01.md").write_text("\n".join(parts) + "\n", encoding="utf-8")


def main() -> None:
    if "--rapport" in sys.argv:
        write_report()
        print(f"rapport_D01.md régénéré dans {HERE}")
        return
    if "--audit" in sys.argv:
        res = run_audit()
        write_report()
        for k in ASSETS:
            s = res[k]["signaux"]
            print(f"{k} : {res[k]['barres']['n_barres']} barres ; intégrité {res[k]['integrite'] or 'OK'} ; "
                  f"{s['n_signaux']} signaux ; univers RE-1 {s['univers_RE1']} ; "
                  f"nis > seuil BTC {100 * s['part_nis_au_dessus_seuil_btc']:.1f} %"
                  + (" ; BLOQUÉ" if res[k].get("bloque") else ""))
        print(f"audit en {res['duree_s']} s → audit_D01.json")
        return
    run_main()


if __name__ == "__main__":
    main()
