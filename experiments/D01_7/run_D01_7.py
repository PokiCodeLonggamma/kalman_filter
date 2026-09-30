"""EXP-D01.7 — portabilité de RE-1 figée, sans réglage, sur des marchés traditionnels 24/5 ; BTC en référence.

Usage, depuis la racine du dépôt : python experiments/D01_7/run_D01_7.py [--audit | --rapport]
  --audit   : étape 1, audit des données, aucun PnL → audit_D01_7.json ;
  (défaut)  : étape 2, contrôles bloquants (ancre P6.5d, parité BTC avec C02bis, seuils gelés, audit sans défaut,
              recoupement externe), puis RE-1 sur chaque actif non bloqué → resultats_D01_7.csv, annuel_D01_7.csv,
              diagnostics_D01_7.json, controles_D01_7.json, figures/, rapport_D01_7.md ;
  --rapport : régénère rapport_D01_7.md (narratif_D01_7.md rédigé à la main, puis annexes générées) sans recalcul.
Données : experiments/D01_7/donnees_D01_7.py.

Cadrage (porteur, 2026-10-01)
- QUESTION : RE-1, telle que verrouillée en C02bis sur BTC (seuils numériques de BTC, H = 26 barres de 30 min, moteur
  v2.1 par défaut), conserve-t-elle son comportement sur des marchés traditionnels à cotation quasi continue 24/5 :
  futures NQ, RTY, CL, HG (continus, OPEN_INTEREST, BACKWARDS_RATIO) et GBPJPY au comptant ?
- PERTINENCE POUR LE FILTRE AKF : D01 a montré que la géométrie des signaux se transpose et que la rente dépend de la
  structure du marché (frais en ATR, séances). Des marchés 24/5 retirent la nuit des ETF mais gardent le week-end et,
  pour les futures, la pause quotidienne de CME et les roulements.
- CE QUE LE PROTOCOLE MESURE RÉELLEMENT : audit des données (couverture, barres, horodatage, trous, séances, roulements,
  recoupement externe) ; puis, par actif, les 8 métriques en brut et nettes de coûts explicites, l'espérance en ATR et en
  bps avec IC par grappes mensuelles, le capital à 0,25 %/ATR et à 1x, Long/Short, F2b/F3, volatilité, sessions,
  exposition au week-end et aux interruptions, concentration du PnL, distribution et queues.
- CE QU'IL NE PERMET PAS DE CONCLURE : pas de validation hors échantillon (2026, ETH et XRP scellés) ; pas de
  classement statistique des actifs ; aucun réglage ni modification de RE-1 sur la base des résultats ; coûts réels non
  mesurés (hypothèses déclarées ; swaps et financement absents).

Règle de lecture (fixée avant le calcul)
- Descriptif : aucun seuil de réussite ; seul motif de blocage = validité des données ou technique. Un actif bloqué est
  documenté, jamais remplacé en silence.
- Coûts aller-retour (hypothèses) : BTC 0, 5 et 10 bps ; GBPJPY 0 (brut), 2 bps (écart acheteur-vendeur ECN d'environ
  1,5 à 2 pips et commission ; la série est un bid, le coût couvre l'écart entier) et 4 bps (lecture principale,
  convention de D01 pour les CFD).
- Recoupement de GBPJPY (critère fixé avant) : prix HistData à 12:00 heure de New York contre DEXUSUK × DEXJPUS
  (taux de midi H.10) : corrélation des variations quotidiennes ≥ 0,95 au décalage 0, meilleur décalage à ± 30 min,
  écart de niveau médian ≤ 10 bps.
- Sessions (heure de New York du signal) : Asie 17:00-02:00, Londres 02:00-08:00, Londres-New York 08:00-12:00,
  New York après-midi 12:00-17:00. Interruptions : barre précédée d'un intervalle de plus de 30 min (week-end, fête,
  trou) ; trade exposé = au moins une telle barre dans ]entrée ; sortie] (définitions de D01 bis).
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
from envelope import equity_curve_sized, risk_weights, route_levels  # noqa: E402
from envelope.metrics import _entry_month  # noqa: E402
from strategy import FLOOR, RISK_BPS, RULES, frozen_masks, metrics, run_re1, sample_years  # noqa: E402
from utils.data_loader import meta_path  # noqa: E402


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


D01 = _load("run_D01", ROOT / "experiments" / "D01" / "run_D01.py")
fr, sg, pct, spct, n_fr, ci, table = D01.fr, D01.sg, D01.pct, D01.spct, D01.n_fr, D01.ci, D01.table

RAW = ROOT / "data" / "raw"
FIG = HERE / "figures"
NY = "America/New_York"
BPS = 1e4
QC_BLOQUE = ("en attente du porteur : QuantConnect exige un compte, et ses données ne sont utilisables que dans son "
             "cloud (aucun export ; Object Store sans téléchargement ; téléchargement local sous licence payante, "
             "réservé à LEAN et non convertible) ; aucune série téléchargée, aucun backtest")
ACTIFS = {
    "BTC": {"nom": "BTC/USD (Bitstamp, référence RE-1)", "csv": DATA_RAW, "fees": (0.0, 5.0, 10.0), "principal": 5.0},
    "GBPJPY": {"nom": "GBP/JPY au comptant (HistData, bid)", "csv": RAW / "histdata_gbpjpy_30m.csv",
               "fees": (0.0, 2.0, 4.0), "principal": 4.0, "couverture": ("2020-01-03", "2025-12-30")},
    "NQ": {"nom": "E-mini Nasdaq-100, future continu", "bloque": QC_BLOQUE},
    "RTY": {"nom": "E-mini Russell 2000, future continu", "bloque": QC_BLOQUE},
    "CL": {"nom": "WTI Crude Oil, future continu", "bloque": QC_BLOQUE},
    "HG": {"nom": "Copper, future continu", "bloque": QC_BLOQUE},
}
for _k in ("GBPJPY",):                                            # réutilisation de prepare, asset_doc, coverage de D01
    D01.ASSETS[_k] = {"nom": ACTIFS[_k]["nom"], "csv": ACTIFS[_k]["csv"], "fees": ACTIFS[_k]["fees"],
                      "couverture": ACTIFS[_k]["couverture"]}
SESSIONS = ["Asie 17:00-02:00", "Londres 02:00-08:00", "Londres-New York 08:00-12:00", "New York 12:00-17:00"]
FED = {"corr_min": 0.95, "decalage_max": 1, "ecart_median_max_bps": 10.0}
ECHELLES = (0.37, 2.9)


# ── Étape 1 : audit ─────────────────────────────────────────────────────────────
def week_structure(bars: pd.DataFrame) -> dict:
    """Reprises après plus de 24 h (week-ends, fêtes) : jour et heure de New York de la première barre et de la fin de la
    dernière barre ; interruptions de 30 min à 24 h en semaine."""
    t = bars.time
    ny = t.dt.tz_convert(NY)
    step = t.diff().to_numpy()
    big = np.flatnonzero(step > np.timedelta64(24, "h"))
    mid = np.flatnonzero((step > np.timedelta64(30, "m")) & (step <= np.timedelta64(24, "h")))
    days = ["lun", "mar", "mer", "jeu", "ven", "sam", "dim"]
    opens = ny.iloc[big]
    ends = ny.iloc[big - 1] + pd.Timedelta(minutes=30)
    lab = lambda s: pd.Series([f"{days[d]} {h:%H:%M}" for d, h in zip(s.dt.dayofweek, s)]).value_counts()  # noqa: E731
    return {"reprises": int(len(big)), "ouverture_new_york": {k: int(v) for k, v in lab(opens).head(6).items()},
            "fin_new_york": {k: int(v) for k, v in lab(ends).head(6).items()},
            "interruptions_en_semaine": int(len(mid)),
            "interruptions_barres_manquantes": int((step[mid] / np.timedelta64(30, "m")).sum() - len(mid)),
            "interruptions_par_annee": {int(k): int(v) for k, v in ny.iloc[mid].dt.year.value_counts().sort_index().items()},
            "interruptions_heure_new_york": {int(k): int(v) for k, v in
                                             ny.iloc[mid].dt.hour.value_counts().head(6).items()},
            "interruptions_duree_h": D01.q(step[mid] / np.timedelta64(1, "h"), (50, 90, 100)) if len(mid) else {}}


def fed_noon(bars: pd.DataFrame) -> dict:
    """GBPJPY HistData à 12:00 heure de New York (close de la barre qui finit à 12:00, et décalages de ± 2 h par pas de
    30 min) contre DEXUSUK × DEXJPUS (taux de midi H.10 de la Réserve fédérale)."""
    ref = {}
    for sid in ("DEXUSUK", "DEXJPUS"):
        s = pd.read_csv(RAW / f"fred_{sid.lower()}.csv", parse_dates=["date"]).dropna()
        ref[sid] = s.set_index("date").valeur
    cross = (ref["DEXUSUK"] * ref["DEXJPUS"]).dropna().rename("fed")
    end = (bars.time + pd.Timedelta(minutes=30)).dt.tz_convert(NY)
    tod = (end - end.dt.normalize())
    rows = {}
    for k in range(-4, 5):
        target = pd.Timedelta(hours=12) + k * pd.Timedelta(minutes=30)
        sel = (tod == target).to_numpy()
        px = pd.Series(bars.close.to_numpy()[sel], index=end[sel].dt.tz_localize(None).dt.normalize().to_numpy())
        j = pd.concat([px.rename("histdata"), cross], axis=1, join="inner").dropna()
        d = np.log(j).diff().dropna()
        rows[k] = {"jours": int(len(j)), "corr_variations": float(d.histdata.corr(d.fed)),
                   "ecart_median_bps": float(((j.histdata / j.fed - 1) * BPS).median()),
                   "ecart_abs_median_bps": float(((j.histdata / j.fed - 1).abs() * BPS).median()),
                   "ecart_abs_P95_bps": float(((j.histdata / j.fed - 1).abs() * BPS).quantile(.95))}
    best = max(rows, key=lambda k: rows[k]["corr_variations"])
    r0 = rows[0]
    ok = (r0["corr_variations"] >= FED["corr_min"] and abs(best) <= FED["decalage_max"]
          and r0["ecart_abs_median_bps"] <= FED["ecart_median_max_bps"])
    return {"par_decalage_demi_heures": rows, "meilleur_decalage_demi_heures": int(best), "valide": bool(ok),
            "critere": FED}


def audit_actif(key: str) -> dict:
    a = ACTIFS[key]
    if a.get("bloque"):
        return {"bloque": a["bloque"], "nom": a["nom"]}
    if key == "BTC":
        au = D01.audit_asset("BTC")
    else:
        au = D01.audit_asset(key)
        p = D01.prepare(key)
        au["semaine"] = week_structure(p["bars"])
        au["recoupement_fed"] = fed_noon(p["bars"])
        if not au["recoupement_fed"]["valide"]:
            au["bloque"] = "recoupement H.10 hors critère"
    au["nom"] = a["nom"]
    return au


def run_audit() -> dict:
    t0 = time.time()
    res = {k: audit_actif(k) for k in ACTIFS}
    res["duree_s"] = round(time.time() - t0)
    (HERE / "audit_D01_7.json").write_text(json.dumps(D01.jsonable(res), ensure_ascii=False, indent=1),
                                           encoding="utf-8")
    for k in ACTIFS:
        r = res[k]
        print(f"{k} : {'bloqué — ' + r['bloque'][:80] if r.get('bloque') else 'audit sans défaut'}")
    return res


# ── Étape 2 : contrôles ─────────────────────────────────────────────────────────
def scale_invariance(p: dict) -> dict:
    """Prérequis des futures rétro-ajustés (BACKWARDS_RATIO) : le facteur d'ajustement commun à une fenêtre dépend des
    roulements postérieurs. Il n'introduit aucune information future si le moteur est invariant d'échelle. Contrôle :
    BTC multiplié par c redonne les mêmes signaux, masques et trades (rendements identiques)."""
    ref, fam_ref = run_re1(p["bars"], p["atlas"], p["atr"], p["m"])
    m_ref, _ = metrics(ref, p["bars"], p["atr_bps"], 5.0, int(p["m"]["R2"].sum()), fam_ref, 6.0, n_boot=200)
    d0 = add_derived(p["atlas"])
    num = [c for c in d0.columns if pd.api.types.is_float_dtype(d0[c])]
    out = {}
    for c in ECHELLES:
        df = p["df"].copy()
        bars = p["bars"].copy()
        for col in ("open", "high", "low", "close"):
            df[col] = df[col] * c
            bars[col] = bars[col] * c
        atlas, _, _, atr = build_atlas(df)
        fam, m = frozen_masks(atlas)
        d1 = add_derived(atlas)
        rel = {k: float(np.nanmax(np.abs(d1[k].to_numpy() - d0[k].to_numpy()) / np.maximum(np.abs(d0[k].to_numpy()), 1e-12)))
               for k in num}
        worst = max(rel, key=rel.get)
        changed = np.flatnonzero(fam != p["fam"])
        tr, fam_s = run_re1(bars, atlas, atr, m)
        m1, _ = metrics(tr, bars, pd.Series(atlas.atr14_bps.to_numpy(), index=atlas.bar_index.to_numpy()), 5.0,
                        int(m["R2"].sum()), fam_s, 6.0, n_boot=200)
        k0, k1 = set(zip(ref.signal_bar, ref.side)), set(zip(tr.signal_bar, tr.side))
        out[str(c)] = {"signaux_identiques": bool(atlas.bar_index.equals(p["atlas"].bar_index)
                                                  and np.array_equal(atlas.direction, p["atlas"].direction)),
                       "descripteur_le_plus_sensible": worst, "ecart_relatif_max": rel[worst],
                       "signaux_changeant_de_famille": int(len(changed)),
                       "changements": [f"{p['fam'][i]} → {fam[i]} (retrace_ratio {d0.retrace_ratio.iat[i]:.12f})"
                                       for i in changed],
                       "trades_communs": len(k0 & k1), "trades_seulement_origine": len(k0 - k1),
                       "trades_seulement_echelle": len(k1 - k0), "esperance_atr_5bps": [m_ref["esperance_atr"],
                                                                                        m1["esperance_atr"]]}
    return out


# ── Étape 3 : mesures ───────────────────────────────────────────────────────────
def gap_exposure(p: dict, tr: pd.DataFrame, fam: pd.Series, v: np.ndarray, months) -> dict:
    """`run_D01.gap_trades` sans le seuil de 1 % de barres d'ouverture (un marché 24/5 n'a qu'une reprise par semaine) :
    mêmes définitions (rendement brut log en ATR14(t) = écarts traversés dans ]entrée ; sortie] + reste)."""
    bars = p["bars"]
    first = D01.session_first(bars)
    o, c = (bars[k].to_numpy(dtype=float) for k in ("open", "close"))
    g = np.zeros(len(o))
    idx = np.flatnonzero(first)
    g[idx] = np.log(o[idx] / c[idx - 1])
    cg, cf = np.cumsum(g), np.cumsum(first)
    e, x = tr.entry_bar.to_numpy(), tr.exit_bar.to_numpy()
    s = tr.side.to_numpy(dtype=np.int64)
    t = tr.signal_bar.to_numpy()
    atr_p = np.asarray(p["atr"], dtype=float)[t]
    a = atr_p / tr.entry_price.to_numpy(dtype=float)
    G = s * (cg[x] - cg[e]) / a
    R = s * np.log(tr.exit_price.to_numpy(dtype=float) / tr.entry_price.to_numpy(dtype=float)) / a
    ng = cf[x] - cf[e]
    seg = pd.Series(p["atlas"].prev_seg_len.to_numpy(), index=p["atlas"].bar_index.to_numpy()).reindex(t).to_numpy()
    level = route_levels(bars, t, s, atr_p, seg, fam.reindex(t).to_numpy(), RULES, FLOOR)
    stp, gp = tr.stop.to_numpy(dtype=bool), tr.gap.to_numpy(dtype=bool)
    over = s * (level - tr.exit_price.to_numpy(dtype=float)) / atr_p
    exp = ng > 0
    gap_abs = np.abs(g[idx]) / (np.asarray(p["atr"], dtype=float)[idx - 1] / c[idx - 1])
    ci3 = lambda vals, keep=None: dict(zip(("moyenne", "lo", "hi"), D01.boot_ci(vals, months, keep)))  # noqa: E731
    return {"reprises": int(first.sum()), "ecart_reprise_abs_atr": D01.q(gap_abs, (50, 90, 99)),
            "part_trades_exposes": float(exp.mean()), "net_exposes": ci3(v, exp), "net_non_exposes": ci3(v, ~exp),
            "brut_log_atr": ci3(R), "composante_ecarts_atr": ci3(G), "composante_hors_ecarts_atr": ci3(R - G),
            "stops": {"n": int(stp.sum()), "n_en_gap": int((stp & gp).sum()),
                      "depassement_atr_moyen": float(over[stp & gp].mean()) if (stp & gp).any() else None}}


def by_session(p: dict, tr: pd.DataFrame, v: np.ndarray, months) -> list[dict]:
    h = p["bars"].time.iloc[tr.signal_bar.to_numpy()].dt.tz_convert(NY).dt.hour.to_numpy()
    lab = np.select([(h >= 17) | (h < 2), h < 8, h < 12], SESSIONS[:3], SESSIONS[3])
    out = []
    for name in SESSIONS:
        keep = lab == name
        m, lo, hi = D01.boot_ci(v, months, keep)
        out.append({"session": name, "n": int(keep.sum()), "part": float(keep.mean()), "esperance_atr": m, "lo": lo,
                    "hi": hi, "wr": float((v[keep] > 0).mean()) if keep.any() else None})
    return out


def concentration(v: np.ndarray) -> dict:
    s = np.sort(v)[::-1]
    k = max(1, int(round(0.1 * len(v))))
    return {"moyenne": float(v.mean()), "mediane": float(np.median(v)), "apport_top5_par_trade": float(s[:5].sum() / len(v)),
            "esperance_sans_top5": float(s[5:].mean()), "apport_decile_superieur_par_trade": float(s[:k].sum() / len(v)),
            "esperance_sans_decile_superieur": float(s[k:].mean()),
            "apport_decile_inferieur_par_trade": float(s[-k:].sum() / len(v))}


def run_main() -> None:
    t0 = time.time()
    audit_path = HERE / "audit_D01_7.json"
    if not audit_path.exists():
        raise SystemExit("audit_D01_7.json absent : lancer d'abord --audit")
    audit = json.loads(audit_path.read_text(encoding="utf-8"))
    ctrl = {"actifs": {}}
    p_btc = D01.prepare("BTC")
    ctrl["btc"] = D01.check_btc(p_btc)
    d_btc = add_derived(p_btc["atlas"])
    D01.BTC_NIS_Q.update({pp: float(np.quantile(d_btc.nis_z_100, pp)) for pp in D01.NIS_PS})
    ctrl["invariance_echelle"] = scale_invariance(p_btc)
    print(f"contrôles BTC et invariance d'échelle passés ({time.time() - t0:.0f} s)")
    rows, years, diags, curves = [], [], {}, {}
    for key, a in ACTIFS.items():
        au = audit[key]
        if au.get("bloque"):
            ctrl["actifs"][key] = {"statut": "bloqué", "motif": au["bloque"]}
            continue
        sha = json.loads(meta_path(a["csv"]).read_text(encoding="utf-8"))["sha256"]
        if au["doc"]["sha256"] != sha:
            raise SystemExit(f"{key} : empreinte du CSV différente de l'audit : arrêt")
        p = p_btc if key == "BTC" else D01.prepare(key)
        tr, fam = run_re1(p["bars"], p["atlas"], p["atr"], p["m"])
        ny = sample_years(p["bars"])
        ctrl["actifs"][key] = {"statut": "mesuré", "annees": ny, "trades": len(tr), "candidats": int(p["m"]["R2"].sum()),
                               "sha256": sha}
        hours = (p["bars"].time.iloc[tr.exit_bar.to_numpy()].to_numpy()
                 - p["bars"].time.iloc[tr.entry_bar.to_numpy()].to_numpy()) / np.timedelta64(1, "h")
        for fee in a["fees"]:
            m, y = metrics(tr, p["bars"], p["atr_bps"], fee, int(p["m"]["R2"].sum()), fam, ny)
            m.update({"actif": key, "frais_bps": fee, "duree_mediane_h": float(np.median(hours)),
                      "debut": str(p["bars"].time.iat[0]), "fin": str(p["bars"].time.iat[-1])})
            rows.append(m)
            y.insert(0, "actif", key)
            y.insert(1, "frais_bps", fee)
            years.append(y)
        fee = a["principal"]
        months = _entry_month(tr, p["bars"])
        v = D01.net_atr(tr, p["atr_bps"], fee)
        d = D01.diagnostics(key, p, tr, fam, fee)
        d.pop("gaps_ouverture", None)
        d.update({"frais_principal_bps": fee, "interruptions": gap_exposure(p, tr, fam, v, months),
                  "sessions": by_session(p, tr, v, months), "concentration": concentration(v)})
        diags[key] = d
        w = risk_weights(p["atr_bps"].reindex(tr.signal_bar.to_numpy()).to_numpy(), RISK_BPS)
        curves[key] = equity_curve_sized(p["bars"], tr, fee, w)
        print(f"{key} : {len(tr)} trades, {fee:g} bps : {rows[-len(a['fees']) + a['fees'].index(fee)]['esperance_atr']:+.3f} ATR "
              f"({time.time() - t0:.0f} s)")
    res = pd.DataFrame(rows)
    lead = ["actif", "frais_bps", "annees", "debut", "fin"]
    res = res[lead + [c for c in res.columns if c not in lead]]
    ctrl["duree_s"] = round(time.time() - t0)
    res.to_csv(HERE / "resultats_D01_7.csv", index=False, float_format="%.6g")
    pd.concat(years, ignore_index=True).to_csv(HERE / "annuel_D01_7.csv", index=False, float_format="%.6g")
    (HERE / "diagnostics_D01_7.json").write_text(json.dumps(D01.jsonable(diags), ensure_ascii=False, indent=1),
                                                 encoding="utf-8")
    (HERE / "controles_D01_7.json").write_text(json.dumps(D01.jsonable(ctrl), ensure_ascii=False, indent=1),
                                               encoding="utf-8")
    FIG.mkdir(parents=True, exist_ok=True)
    figure(curves, diags)
    write_report()
    print(f"D01.7 : {len(res)} lignes en {ctrl['duree_s']} s ; résultats, diagnostics et rapport dans {HERE}")


def figure(curves: dict, diags: dict) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(15, 4.8))
    for key, c in curves.items():
        axes[0].plot(c.index, c.to_numpy(), lw=1.2, label=f"{key} ({diags[key]['frais_principal_bps']:g} bps)",
                     color=D01.COLORS.get(key, "#8c564b"))
    axes[0].set_yscale("log")
    axes[0].axhline(1, color="k", lw=0.8)
    axes[0].set_title("Capital à 0,25 %/ATR, RE-1 figée")
    axes[0].legend(fontsize=8)
    axes[0].grid(alpha=0.3)
    ax = axes[1]
    for i, key in enumerate(curves):
        s = diags[key]["sessions"]
        x = np.arange(len(s)) + (i - 0.5) * 0.15
        e = np.array([r["esperance_atr"] for r in s], dtype=float)
        lo = np.array([r["lo"] for r in s], dtype=float)
        hi = np.array([r["hi"] for r in s], dtype=float)
        ax.errorbar(x, e, yerr=[e - lo, hi - e], fmt="o", capsize=3, color=D01.COLORS.get(key, "#8c564b"), label=key)
    ax.set_xticks(np.arange(len(SESSIONS)))
    ax.set_xticklabels([s.replace(" ", "\n", 1) for s in SESSIONS], fontsize=8)
    ax.axhline(0, color="k", lw=0.8)
    ax.set_title("Espérance nette par session du signal (heure de New York) [IC 95 %]")
    ax.legend(fontsize=8)
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(FIG / "D01_7.png", dpi=120)
    plt.close(fig)


# ── Rapport ─────────────────────────────────────────────────────────────────────
def section_audit(audit: dict) -> str:
    out = ["### A. Audit des données (avant tout backtest)"]
    for key, a in ACTIFS.items():
        au = audit[key]
        if a.get("bloque"):
            out.append(f"\n**{key} — {a['nom']} : bloqué.** {au['bloque']}.")
            continue
        b, doc = au["barres"], au["doc"]
        tr_ = b["trous"]
        cl = tr_["classes"]
        out.append(f"\n**{key} — {a['nom']}**\n")
        rows = [["Source ; instrument", f"{doc.get('source')} ; {doc.get('instrument', doc.get('ticker', '—'))}"],
                ["Fuseau ; prix", f"{doc.get('timezone', 'UTC')[:140]} ; {doc.get('prix', '—')[:60]}"],
                ["Barres ; première ; dernière", f"{n_fr(b['n_barres'])} ; {b['premiere'][:16]} ; {b['derniere'][:16]}"],
                ["Intégrité (doublons, désordre, prix, OHLC)", " ; ".join(au["integrite"]) or "aucun défaut"],
                ["Couverture 2020-2025", " ; ".join(au["couverture"]) or "conforme"],
                ["Trous (n ; barres manquantes) : ≤ 2 h ; ≤ 3 jours ; > 3 jours",
                 " ; ".join(f"{cl[k]['n']} ({n_fr(cl[k]['barres_manquantes'])})" for k in ("<= 2 h", "<= 3 jours", "> 3 jours"))],
                ["Plus longs trous", " ; ".join(f"{fr(x['duree_h'], 0)} h après {x['apres'][:16]}" for x in tr_["plus_longs"][:3])],
                ["Barres plates ; SHA-256", f"{b.get('barres_plates', '—')} ; {doc.get('sha256', '')[:16]}…"]]
        if "semaine" in au:
            s = au["semaine"]
            rows += [["Reprises après plus de 24 h ; ouverture (New York)",
                      f"{s['reprises']} ; " + ", ".join(f"{k} : {v}" for k, v in s["ouverture_new_york"].items())],
                     ["Fin de semaine (New York)", ", ".join(f"{k} : {v}" for k, v in s["fin_new_york"].items())],
                     ["Interruptions de 30 min à 24 h en semaine ; barres manquantes ; par année",
                      f"{s['interruptions_en_semaine']} ; {n_fr(s['interruptions_barres_manquantes'])} ; "
                      + ", ".join(f"{k} : {v}" for k, v in s["interruptions_par_annee"].items())]]
        if "recoupement_fed" in au:
            f = au["recoupement_fed"]
            r0 = f["par_decalage_demi_heures"]["0"]
            rows.append(["Recoupement H.10 (12:00 New York)",
                         f"{r0['jours']} jours ; corrélation des variations {fr(r0['corr_variations'], 4)} ; écart "
                         f"médian {sg(r0['ecart_median_bps'], 1)} bps (absolu {fr(r0['ecart_abs_median_bps'], 1)}, "
                         f"P95 {fr(r0['ecart_abs_P95_bps'], 1)}) ; meilleur décalage {f['meilleur_decalage_demi_heures']} "
                         f"demi-heure ; {'valide' if f['valide'] else 'NON VALIDE'}"])
        out.append(table(["Contrôle", "Mesure"], rows))
    return "\n".join(out)


def section_controles(ctrl: dict) -> str:
    b = ctrl["btc"]
    out = ["### B. Contrôles bloquants", "",
           f"- Ancre P6.5d reproduite ; RE-1 de la chaîne D01 = RE-1 de C02bis ({b['trades']} trades, "
           f"{b['metriques_comparees']} métriques, écart relatif max {b['ecart_relatif_max']:.1e}).",
           "- Seuils de population gelés à leur valeur BTC (médiane de `leg_atr`, P75 de `nis_z_100`) ; RE-1 inchangée.",
           "- Réserve 2026 : chaque série est tronquée avant le 2026-01-01 au chargement ; rien de 2026 n'a été "
           "téléchargé."]
    for c, r in ctrl["invariance_echelle"].items():
        out.append(f"- Invariance d'échelle (prérequis des futures rétro-ajustés), BTC × {c} : signaux "
                   f"{'identiques' if r['signaux_identiques'] else 'DIFFÉRENTS'} ; descripteurs à {r['ecart_relatif_max']:.1e} "
                   f"près en relatif (le plus sensible : `{r['descripteur_le_plus_sensible']}`) ; "
                   f"{r['signaux_changeant_de_famille']} signaux changent de famille ({'; '.join(r['changements'])}) ; "
                   f"RE-1 : {r['trades_communs']} trades communs, {r['trades_seulement_origine']} seulement sur l'original, "
                   f"{r['trades_seulement_echelle']} seulement sur la série multipliée ; espérance à 5 bps "
                   f"{sg(r['esperance_atr_5bps'][0], 4)} → {sg(r['esperance_atr_5bps'][1], 4)} ATR.")
    for key, v in ctrl["actifs"].items():
        out.append(f"- {key} : {v['statut']}" + (f" — {v['motif']}" if v.get("motif") else
                                                 f" ({v['trades']} trades, {v['candidats']} candidats, "
                                                 f"{fr(v['annees'], 2)} ans)") + ".")
    return "\n".join(out)


def section_resultats(res: pd.DataFrame) -> str:
    head = D01.HEAD8
    return ("### C. Résultats nets (8 métriques ; brut = 0 bps)\n\n" + table(head, [D01.row8(r) for _, r in res.iterrows()])
            + "\n\n" + table(D01.HEADRISK, [D01.rowrisk(r) for _, r in res.iterrows()]))


def section_analyses(diags: dict) -> str:
    out = ["### D. Analyses (frais principaux de chaque actif)"]
    for key, d in diags.items():
        out.append(f"\n**{key} ({d['frais_principal_bps']:g} bps)**\n")
        sf = [[c["famille"], c["sens"], c["n"], ci(c["esperance_atr"], c["lo"], c["hi"], 3), sg(c["esperance_bps"], 1)]
              for c in d["sens_familles"]]
        out.append(table(["Famille", "Sens", "n", "Espérance ATR [IC]", "bps"], sf))
        vol = [[r["tercile"], f"{fr(r['atr14_bps'][0], 0)}-{fr(r['atr14_bps'][1], 0)}", r["n"],
                ci(r["esperance_atr"], r["lo"], r["hi"], 3), pct(r["wr"]), pct(r["part_stoppes"], 0)] for r in d["volatilite"]]
        out.append("\n" + table(["Tercile d'ATR14(t)", "ATR (bps)", "n", "Espérance ATR [IC]", "WR", "Stoppés"], vol))
        ses = [[r["session"], r["n"], pct(r["part"], 0), ci(r["esperance_atr"], r["lo"], r["hi"], 3),
                pct(r["wr"]) if r["wr"] is not None else "—"] for r in d["sessions"]]
        out.append("\n" + table(["Session du signal (New York)", "n", "Part", "Espérance ATR [IC]", "WR"], ses))
        g = d["interruptions"]
        out.append("\n" + table(["Interruptions (week-end, fêtes, trous)", "Mesure"], [
            ["Reprises ; écart de reprise absolu P50 / P90 (ATR)",
             f"{g['reprises']} ; {fr(g['ecart_reprise_abs_atr'].get('P50'), 2)} / {fr(g['ecart_reprise_abs_atr'].get('P90'), 2)}"],
            ["Trades exposés", pct(g["part_trades_exposes"], 1)],
            ["Net exposés ; non exposés (ATR)", f"{ci(g['net_exposes']['moyenne'], g['net_exposes']['lo'], g['net_exposes']['hi'], 3)} ; "
                                                f"{ci(g['net_non_exposes']['moyenne'], g['net_non_exposes']['lo'], g['net_non_exposes']['hi'], 3)}"],
            ["Brut log = écarts + reste (ATR)", f"{sg(g['brut_log_atr']['moyenne'], 3)} = {sg(g['composante_ecarts_atr']['moyenne'], 3)} + "
                                                 f"{sg(g['composante_hors_ecarts_atr']['moyenne'], 3)}"],
            ["Stops en gap / stops ; dépassement moyen", f"{g['stops']['n_en_gap']}/{g['stops']['n']} ; "
                                                         f"{sg(g['stops']['depassement_atr_moyen'], 2) if g['stops']['depassement_atr_moyen'] is not None else '—'} ATR"]]))
        c, dist = d["concentration"], d["distribution"]
        out.append("\n" + table(["Concentration et queues (ATR par trade)", "Mesure"], [
            ["Moyenne ; médiane ; moyenne winsorisée P1-P99", f"{sg(c['moyenne'], 3)} ; {sg(c['mediane'], 3)} ; "
                                                             f"{sg(dist['moyenne_winsorisee_P1_P99'], 3)}"],
            ["Apport des 5 meilleurs ; espérance sans eux", f"{sg(c['apport_top5_par_trade'], 3)} ; {sg(c['esperance_sans_top5'], 3)}"],
            ["Apport du décile supérieur ; espérance sans lui", f"{sg(c['apport_decile_superieur_par_trade'], 3)} ; "
                                                                f"{sg(c['esperance_sans_decile_superieur'], 3)}"],
            ["Apport du décile inférieur", sg(c["apport_decile_inferieur_par_trade"], 3)],
            ["Quantiles P5 ; P10 ; P50 ; P90 ; P95", " ; ".join(sg(dist[k], 2) for k in ("P5", "P10", "P50", "P90", "P95"))]]))
        s3 = d["stops_F3"]
        out.append(f"\n- Stops de F3 : {s3['n_stoppes']}/{s3['n_F3']} ; effet apparié du stop sur F3 "
                   f"{ci(s3['effet_stop_sur_F3_atr'], s3['effet_lo'], s3['effet_hi'], 3)} ATR ; sans stop : MDD "
                   f"{pct(s3['sans_stop_mdd_r25'])} (0,25 %/ATR).")
        bands = " ; ".join(f"{b['bande']} : {b['n']}, {sg(b['esperance_atr'], 3)}" for b in d["bandes_nis"]["bandes"])
        out.append(f"- Bandes de `nis_z_100` (signaux R2 isolés, bornes BTC) : {bands}.")
        out.append(f"- Durée calendaire : médiane {fr(d['duree_calendaire_h']['mediane'], 1)} h, P90 "
                   f"{fr(d['duree_calendaire_h']['P90'], 1)} h, plus de 24 h : {pct(d['duree_calendaire_h']['part_plus_de_24_h'], 0)}.")
    return "\n".join(out)


def write_report() -> None:
    audit = json.loads((HERE / "audit_D01_7.json").read_text(encoding="utf-8"))
    res = pd.read_csv(HERE / "resultats_D01_7.csv")
    diags = json.loads((HERE / "diagnostics_D01_7.json").read_text(encoding="utf-8"))
    ctrl = json.loads((HERE / "controles_D01_7.json").read_text(encoding="utf-8"))
    narr = HERE / "narratif_D01_7.md"
    head = narr.read_text(encoding="utf-8").rstrip() + "\n\n" if narr.exists() else "# EXP-D01.7\n\n"
    ann = res.copy()
    parts = [head + "## Annexes générées (run_D01_7.py)", section_audit(audit), section_controles(ctrl),
             section_resultats(ann), section_analyses(diags), "### E. Figure\n\n![Capital et sessions](figures/D01_7.png)"]
    (HERE / "rapport_D01_7.md").write_text("\n\n".join(parts) + "\n", encoding="utf-8")


def main() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        pass
    warnings.simplefilter("ignore")
    if "--audit" in sys.argv:
        run_audit()
    elif "--rapport" in sys.argv:
        write_report()
        print(f"rapport régénéré : {HERE / 'rapport_D01_7.md'}")
    else:
        run_main()


if __name__ == "__main__":
    main()
