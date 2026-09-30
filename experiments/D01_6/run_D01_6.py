"""EXP-D01.6 — exploration de deux mécaniques de D01.5 sur SPY et XLE : verrouillage (cooldown) et séance.

Usage, depuis la racine du dépôt : python experiments/D01_6/run_D01_6.py [--rapport]
  (défaut)  : contrôles bloquants, puis les trois actions → resultats_D01_6.csv, profil_D01_6.csv,
              diagnostics_D01_6.json, controles_D01_6.json, figures/, rapport_D01_6.md ;
  --rapport : régénère rapport_D01_6.md (narratif_D01_6.md rédigé à la main, puis annexes générées) sans recalcul.
Données : celles de D01 (ETF SPY et XLE, Alpaca, séance régulière 2020-2025), inchangées. Frais : 4 bps.

Cadrage (porteur, 2026-09-30)
- QUESTION : (1) les 31 trades de RE-1 sur XLE que la course à H = 65 saute ont-ils une signature mesurable à t ?
  (2) un verrouillage plus long que la sortie (H_exit = 26, H_cooldown ∈ {26, 48, 65, 90}) donne-t-il une espérance
  nette robuste ? (3) le signal a-t-il une valeur en séance seule, sans nuit détenue ?
- PERTINENCE POUR LE FILTRE AKF : dans RE-1, H fixe à la fois la sortie et le verrouillage (cooldown compté depuis le
  signal). D01.5 a montré que le gain de XLE à H = 65 vient des trades sautés (population), pas de la sortie. Les gaps
  d'ouverture sont des innovations d'une barre pour le filtre : une sortie avant la nuit isole la cinématique en séance.
- CE QUE LE PROTOCOLE MESURE RÉELLEMENT :
  - action 1 : profil à t des trades sautés contre les trades gardés (XLE ; réplication sur SPY), et leur valeur nette
    avec la sortie de RE-1 (26 barres) et avec la sortie à 65 barres ;
  - action 2 : les 8 métriques de RE-1 à verrouillage 26, 48, 65, 90, sortie à 26 barres ;
  - action 3 : sortie forcée au close de la dernière barre de séance, (a) sur les entrées de RE-1 (effet apparié) et
    (b) avec la position libérée à la clôture (stratégie de séance autonome).
- CE QU'IL NE PERMET PAS DE CONCLURE : aucun filtre n'est retenu. Un seuil lu sur 31 trades d'un actif serait ajusté à
  l'échantillon ; une signature n'est crédible que si elle se répète sur SPY. Pas de hold-out. La clôture est exécutée
  au close de la dernière barre continue (15:30-16:00), pas au prix de l'enchère de clôture.

Règle de lecture (fixée avant le calcul du profil et des variantes)
- Signature (action 1) : une variable dont l'AUC (probabilité qu'un trade sauté dépasse un trade gardé) a un IC 95 %
  qui exclut 0,5 sur XLE, et le même sens sur SPY. Elle n'a d'intérêt pour RE-1 que si les trades sautés perdent avec
  la sortie de RE-1 (26 barres).
- Avantage (actions 2 et 3) : borne basse de l'IC 95 % par grappes mensuelles > 0, en ATR et en bps.
- Variables du profil, toutes connues à t : `nis_z_100`, `retrace_ratio`, `leg_atr`, sens, heure du signal, tercile
  d'ATR14(t) (demandées par le porteur) ; famille F2b/F3 ; et trois variables de réplique : barres depuis le signal du
  trade précédent de RE-1, même sens que lui, son résultat brut connu à t (réalisé s'il est clos, latent au close de t
  sinon, en ATR14 de son signal).
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

from categorization import add_derived  # noqa: E402
from envelope import effect_ci, route_levels  # noqa: E402
from envelope.decouple import lock_trades, session_close_trades, session_last_bar  # noqa: E402
from envelope.metrics import _entry_month  # noqa: E402
from estimand.excursions import BPS  # noqa: E402
from estimand.stoploss import TRADE_COLUMNS  # noqa: E402
from strategy import FLOOR, H, RULES, metrics, run_re1, sample_years  # noqa: E402
from utils.data_loader import meta_path  # noqa: E402


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


D01 = _load("run_D01", ROOT / "experiments" / "D01" / "run_D01.py")
D015 = _load("run_D01_5", ROOT / "experiments" / "D01_5" / "run_D01_5.py")
fr, sg, pct, spct, n_fr, ci, table = D01.fr, D01.sg, D01.pct, D01.spct, D01.n_fr, D01.ci, D01.table

FEE = 4.0
ACTIFS = ("XLE", "SPY")
LOCKS = (26, 48, 65, 90)
H_SAUT = 65
NY = "America/New_York"
N_BOOT = 2000
FIG = HERE / "figures"
CONTINUES = ["nis_z_100", "retrace_ratio", "leg_atr", "barres_depuis_precedent", "resultat_precedent_atr"]
BINAIRES = ["long", "F3", "meme_sens"]
HEURES = ["ouverture 09:30", "10:00-11:30", "12:00-13:30", "14:00-15:00", "dernière barre"]


# ── Entrées de RE-1 ─────────────────────────────────────────────────────────────
def re1_inputs(p: dict) -> tuple[np.ndarray, np.ndarray, np.ndarray, pd.Series]:
    """Signaux candidats de RE-1, sens, niveaux de stop et sous-familles : mêmes calculs que `strategy.run_re1`."""
    m, atlas = p["m"]["R2"], p["atlas"]
    t, s, n = (atlas[c].to_numpy()[m] for c in ("bar_index", "direction", "prev_seg_len"))
    fam = np.where(p["m"]["F3"][m], "F3", "F2b")
    level = route_levels(p["bars"], t, s, np.asarray(p["atr"], dtype=float)[t], n, fam, RULES, FLOOR)
    return t, s, level, pd.Series(fam, index=t)


def net_atr(tr: pd.DataFrame, atr_bps: pd.Series) -> np.ndarray:
    return (tr.ret_gross_bps.to_numpy(dtype=float) - FEE) / atr_bps.reindex(tr.signal_bar.to_numpy()).to_numpy()


def hours_held(bars: pd.DataFrame, tr: pd.DataFrame) -> np.ndarray:
    """De l'ouverture de la barre d'entrée à l'exécution : ouverture de `exit_bar` (sortie à horizon, D01), début de la
    barre du stop (D01), clôture de la dernière barre de séance pour une sortie de fin de séance."""
    t = bars.time.to_numpy(dtype="datetime64[ns]")
    e, x = tr.entry_bar.to_numpy(), tr.exit_bar.to_numpy()
    sess = tr["session_exit"].to_numpy(dtype=bool) if "session_exit" in tr else np.zeros(len(tr), dtype=bool)
    out = np.where(sess, t[x - 1] + np.timedelta64(30, "m"), t[x])
    return (out - t[e]) / np.timedelta64(1, "h")


def measure(p: dict, tr: pd.DataFrame, fam: pd.Series, ref: pd.DataFrame | None = None) -> tuple[dict, pd.DataFrame]:
    bars, atr_bps = p["bars"], p["atr_bps"]
    ny = sample_years(bars)
    m, y = metrics(tr[TRADE_COLUMNS], bars, atr_bps, FEE, int(p["m"]["R2"].sum()), fam, ny)
    a = atr_bps.reindex(tr.signal_bar.to_numpy()).to_numpy()
    b_m, b_lo, b_hi = D01.boot_ci(tr.ret_gross_bps.to_numpy(dtype=float) / a, _entry_month(tr, bars))
    hours = hours_held(bars, tr)
    m.update({"frais_bps": FEE, "brut_atr": b_m, "brut_atr_lo": b_lo, "brut_atr_hi": b_hi,
              "frais_atr": float((FEE / a).mean()), "duree_mediane_h": float(np.median(hours)),
              "duree_h_P90": float(np.percentile(hours, 90)), "n_annees": len(y)})
    if "session_exit" in tr:
        m["part_sortie_seance"] = float(tr.session_exit.mean())
    if ref is not None:
        v, vr = net_atr(tr, atr_bps), net_atr(ref, atr_bps)
        common = np.isin(tr.signal_bar.to_numpy(), ref.signal_bar.to_numpy())
        dropped = ~np.isin(ref.signal_bar.to_numpy(), tr.signal_bar.to_numpy())
        m.update({"part_communs_re1": float(common.mean()), "n_retires": int(dropped.sum()),
                  "retires_atr": float(vr[dropped].mean()) if dropped.any() else np.nan,
                  "n_ajoutes": int((~common).sum()),
                  "ajoutes_atr": float(v[~common].mean()) if (~common).any() else np.nan})
    return m, y


# ── Action 1 : profil des trades sautés ─────────────────────────────────────────
def features(p: dict, ref: pd.DataFrame, fam: pd.Series) -> pd.DataFrame:
    """Variables connues à t pour chaque trade de RE-1."""
    bars, atlas = p["bars"], p["atlas"]
    t = ref.signal_bar.to_numpy()
    d = add_derived(atlas)
    at = lambda col: pd.Series(d[col].to_numpy(dtype=float), index=atlas.bar_index.to_numpy()).reindex(t).to_numpy()  # noqa: E731
    first = D01.session_first(bars)[t]
    last = session_last_bar(bars)[t] == t
    local = bars.time.iloc[t].dt.tz_convert(NY)
    hm = (local.dt.hour + local.dt.minute / 60.0).to_numpy()
    heure = np.where(first, HEURES[0], np.where(last, HEURES[4], np.where(hm < 12, HEURES[1],
                                                                             np.where(hm < 14, HEURES[2], HEURES[3]))))
    a = p["atr_bps"].reindex(t).to_numpy()
    terc = np.digitize(a, np.quantile(a, [1 / 3, 2 / 3]))
    side = ref.side.to_numpy(dtype=np.int64)
    close = bars.close.to_numpy(dtype=float)
    prev_res = np.full(len(t), np.nan)
    for i in range(1, len(t)):                                        # trade précédent : j = i − 1, connu à t_i
        j = i - 1
        if ref.exit_bar.iat[j] <= t[i]:
            g = ref.ret_gross_bps.iat[j]                              # clos : résultat réalisé
        else:
            g = side[j] * (close[t[i]] / ref.entry_price.iat[j] - 1.0) * BPS   # ouvert : latent au close de t
        prev_res[i] = g / a[j]
    return pd.DataFrame({"signal_bar": t, "nis_z_100": at("nis_z_100"), "retrace_ratio": at("retrace_ratio"),
                         "leg_atr": at("leg_atr"), "long": (side == 1).astype(float),
                         "F3": (fam.reindex(t).to_numpy() == "F3").astype(float), "heure": heure,
                         "tercile_atr": terc, "barres_depuis_precedent": np.r_[np.nan, np.diff(t)].astype(float),
                         "meme_sens": np.r_[np.nan, (side[1:] == side[:-1]).astype(float)],
                         "resultat_precedent_atr": prev_res})


def auc(x1: np.ndarray, x0: np.ndarray) -> float:
    return float((x1[:, None] > x0[None, :]).mean() + 0.5 * (x1[:, None] == x0[None, :]).mean())


def auc_ci(x1, x0, seed: int = 0) -> tuple[float, float, float]:
    """AUC (probabilité qu'une valeur du groupe 1 dépasse une valeur du groupe 0) et IC 95 % par bootstrap des trades,
    stratifié par groupe."""
    x1, x0 = x1[~np.isnan(x1)], x0[~np.isnan(x0)]
    rng = np.random.default_rng(seed)
    b = [auc(x1[rng.integers(0, len(x1), len(x1))], x0[rng.integers(0, len(x0), len(x0))]) for _ in range(N_BOOT)]
    lo, hi = np.percentile(b, [2.5, 97.5])
    return auc(x1, x0), float(lo), float(hi)


def profile(key: str, p: dict, ref: pd.DataFrame, fam: pd.Series, tr_saut: pd.DataFrame) -> tuple[list, dict]:
    bars, atr_bps = p["bars"], p["atr_bps"]
    f = features(p, ref, fam)
    kept = np.isin(ref.signal_bar.to_numpy(), tr_saut.signal_bar.to_numpy())
    v26 = net_atr(ref, atr_bps)
    fz = D015.frozen_exit(p, ref, fam, H_SAUT)
    v65 = net_atr(fz, atr_bps)
    months = _entry_month(ref, bars)
    groups = {}
    for name, g in (("sautes", ~kept), ("gardes", kept)):
        e26 = D01.boot_ci(v26, months, g)
        e65 = D01.boot_ci(v65, months, g)
        top = np.sort(v26[g])[::-1]
        groups[name] = {"n": int(g.sum()), "net26": e26, "net65": e65, "mediane26": float(np.median(v26[g])),
                        "wr26": float((v26[g] > 0).mean()), "top3_26": float(top[:3].sum() / g.sum()),
                        "sans_top3_26": float(top[3:].mean()), "stoppes26": float(ref.stop.to_numpy()[g].mean())}
    rows = []
    for c in CONTINUES + BINAIRES:
        x = f[c].to_numpy(dtype=float)
        a, lo, hi = auc_ci(x[~kept], x[kept])
        q = lambda v: [float(np.nanpercentile(v, k)) for k in (25, 50, 75)] if c in CONTINUES else [float(np.nanmean(v))]  # noqa: E731
        rows.append({"actif": key, "variable": c, "sautes": q(x[~kept]), "gardes": q(x[kept]), "auc": a,
                     "auc_lo": lo, "auc_hi": hi})
    for c, cats in (("heure", HEURES), ("tercile_atr", [0, 1, 2])):
        for k in cats:
            x = (f[c].to_numpy() == k).astype(float)
            rows.append({"actif": key, "variable": f"{c} = {k}", "sautes": [float(x[~kept].mean())],
                         "gardes": [float(x[kept].mean())], "auc": np.nan, "auc_lo": np.nan, "auc_hi": np.nan,
                         "net26_categorie": float(v26[x == 1].mean()) if x.any() else np.nan})
    diag = {"groupes": groups, "barres_depuis_precedent_sautes": [float(np.nanmin(f.barres_depuis_precedent[~kept])),
                                                                   float(np.nanmax(f.barres_depuis_precedent[~kept]))],
            "effet_65_contre_26": {k: float((v65 - v26)[g].mean()) for k, g in (("sautes", ~kept), ("gardes", kept))},
            "par_trade_sautes": [{"signal": str(bars.time.iat[int(ti)]), "sens": int(si), "net26": float(a26),
                                  "net65": float(a65)} for ti, si, a26, a65 in
                                 zip(ref.signal_bar.to_numpy()[~kept], ref.side.to_numpy()[~kept], v26[~kept],
                                     v65[~kept])]}
    return rows, diag


# ── Déroulé ─────────────────────────────────────────────────────────────────────
def run_asset(key: str, audit: dict) -> tuple[list, list, dict, dict]:
    if audit[key]["doc"]["sha256"] != json.loads(meta_path(D01.ASSETS[key]["csv"]).read_text(encoding="utf-8"))["sha256"]:
        raise SystemExit(f"{key} : empreinte du CSV différente de l'audit de D01 : arrêt")
    p = D01.prepare(key)
    bars = p["bars"]
    ref, fam = run_re1(bars, p["atlas"], p["atr"], p["m"])
    t, s, level, fam_s = re1_inputs(p)
    if not fam_s.equals(fam):
        raise SystemExit(f"{key} : sous-familles différentes de run_re1 : arrêt")
    local_dates = bars.time.dt.tz_convert(NY).dt.date
    n_seances = int(D01.session_first(bars).sum()) + 1
    ctrl = {"sha256": audit[key]["doc"]["sha256"], "trades_re1": len(ref), "seances": n_seances,
            "dates_new_york": int(local_dates.nunique())}
    if n_seances != ctrl["dates_new_york"]:
        raise SystemExit(f"{key} : trou de données en séance (séances {n_seances} contre {ctrl['dates_new_york']} dates) : arrêt")
    rows = []
    # action 2 : verrouillage distinct de la sortie
    for lock in LOCKS:
        tr = lock_trades(bars, t, s, H, lock, level)
        if lock == H and not tr.equals(ref):
            raise SystemExit(f"{key} : verrouillage 26 différent de RE-1 : arrêt")
        m, _ = measure(p, tr, fam, ref)
        m.update({"action": "2 verrouillage", "actif": key, "variante": f"H_exit 26, H_cooldown {lock}",
                  "h_cooldown": lock})
        rows.append(m)
    tr65, _ = run_re1(bars, p["atlas"], p["atr"], p["m"], horizon=H_SAUT)
    lk65 = lock_trades(bars, t, s, H, H_SAUT, level)
    if not np.array_equal(lk65.signal_bar.to_numpy(), tr65.signal_bar.to_numpy()):
        raise SystemExit(f"{key} : verrouillage 65 sans la population de la course à H = 65 : arrêt")
    ctrl["verrouillage_65_population_de_H65"] = True
    # action 1 : profil des trades sautés par la course à H = 65
    prof, diag = profile(key, p, ref, fam, tr65)
    # action 3 : sortie forcée en fin de séance
    dl = session_close_trades(bars, t, s, H, level, release="lock")
    if not all(np.array_equal(dl[c].to_numpy(), ref[c].to_numpy()) for c in ("entry_bar", "side", "signal_bar")):
        raise SystemExit(f"{key} : sortie de fin de séance (entrées de RE-1) sans les entrées de RE-1 : arrêt")
    ds = session_close_trades(bars, t, s, H, level, release="session")
    end = session_last_bar(bars)
    for tr in (dl, ds):
        e, x = tr.entry_bar.to_numpy(), tr.exit_bar.to_numpy()
        se = tr.session_exit.to_numpy(dtype=bool)
        if not ((x[se] - 1 == end[e[se]]).all() and (x[~se] <= end[e[~se]]).all()):
            raise SystemExit(f"{key} : une position de séance traverse une nuit : arrêt")
    ctrl["aucune_nuit_detenue"] = True
    eff = effect_ci(dl[TRADE_COLUMNS], ref, bars, p["atr_bps"], N_BOOT)
    for name, tr, extra in (("RE-1 (nuits détenues)", ref, {}),
                            ("séance, entrées de RE-1", dl, {f"apparie_{k}": v for k, v in eff.items()}),
                            ("séance, libérée à la clôture", ds, {})):
        m, _ = measure(p, tr, fam, ref)
        m.update({"action": "3 séance", "actif": key, "variante": name, **extra})
        rows.append(m)
    diag["seance"] = {"sorties_de_fin_de_seance": {k: int(v.session_exit.sum()) for k, v in (("entrees_re1", dl),
                                                                                                ("liberee", ds))}}
    print(f"{key} : RE-1 {len(ref)} trades ; sautés à H = 65 : {len(ref) - int(np.isin(ref.signal_bar, tr65.signal_bar).sum())} ; "
          f"séance {len(dl)} et {len(ds)} trades")
    return rows, prof, diag, ctrl


def run_main() -> None:
    t0 = time.time()
    audit = json.loads((ROOT / "experiments" / "D01" / "audit_D01.json").read_text(encoding="utf-8"))
    rows, prof, diags, ctrl = [], [], {}, {"frais_bps": FEE, "verrouillages": LOCKS, "actifs": {}}
    for key in ACTIFS:
        r, pr, d, c = run_asset(key, audit)
        rows += r
        prof += pr
        diags[key], ctrl["actifs"][key] = d, c
    res = pd.DataFrame(rows)
    lead = ["action", "actif", "variante", "frais_bps", "annees"]
    res = res[lead + [c for c in res.columns if c not in lead]]
    ctrl["duree_s"] = round(time.time() - t0)
    res.to_csv(HERE / "resultats_D01_6.csv", index=False, float_format="%.6g")
    pd.DataFrame(prof).to_json(HERE / "profil_D01_6.json", orient="records", force_ascii=False, indent=1)
    (HERE / "diagnostics_D01_6.json").write_text(json.dumps(D01.jsonable(diags), ensure_ascii=False, indent=1),
                                                 encoding="utf-8")
    (HERE / "controles_D01_6.json").write_text(json.dumps(D01.jsonable(ctrl), ensure_ascii=False, indent=1),
                                               encoding="utf-8")
    FIG.mkdir(parents=True, exist_ok=True)
    figure(res)
    write_report()
    print(f"D01.6 : {len(res)} lignes en {ctrl['duree_s']} s ; résultats, figure et rapport dans {HERE}")


# ── Figure ──────────────────────────────────────────────────────────────────────
def figure(res: pd.DataFrame) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(14, 4.8))
    ax = axes[0]
    for i, key in enumerate(ACTIFS):
        r = res[(res.action == "2 verrouillage") & (res.actif == key)]
        x = np.arange(len(r)) + (i - 0.5) * 0.12
        e = r.esperance_atr.to_numpy()
        ax.errorbar(x, e, yerr=[e - r.esperance_atr_lo, r.esperance_atr_hi - e], fmt="o-", capsize=3,
                    color=D01.COLORS[key], label=f"{key}")
    ax.set_xticks(np.arange(len(LOCKS)))
    ax.set_xticklabels([f"H_cooldown {k}" for k in LOCKS])
    ax.set_title("Action 2 : H_exit = 26, verrouillage variable (4 bps)")
    ax2 = axes[1]
    names = ["RE-1 (nuits détenues)", "séance, entrées de RE-1", "séance, libérée à la clôture"]
    for i, key in enumerate(ACTIFS):
        r = res[(res.action == "3 séance") & (res.actif == key)].set_index("variante").loc[names]
        x = np.arange(len(names)) + (i - 0.5) * 0.12
        e = r.esperance_atr.to_numpy()
        ax2.errorbar(x, e, yerr=[e - r.esperance_atr_lo, r.esperance_atr_hi - e], fmt="o", capsize=3,
                     color=D01.COLORS[key], label=key)
    ax2.set_xticks(np.arange(len(names)))
    ax2.set_xticklabels(["RE-1\n(nuits détenues)", "séance\n(entrées de RE-1)", "séance\n(libérée à la clôture)"])
    ax2.set_title("Action 3 : sortie forcée en fin de séance (4 bps)")
    for a in axes:
        a.axhline(0, color="k", lw=0.8)
        a.set_ylabel("espérance nette par trade (ATR14(t)) [IC 95 %]")
        a.grid(alpha=0.3)
        a.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(FIG / "D01_6.png", dpi=120)
    plt.close(fig)


# ── Rapport ─────────────────────────────────────────────────────────────────────
def row8(r) -> list:
    return [f"{r['actif']} · {r['variante']}", f"{spct(r['pnl_compose_r25'])} ; {spct(r['pnl_compose'])}",
            fr(r["pf"], 2), pct(r["wr"]), ci(r["esperance_atr"], r["esperance_atr_lo"], r["esperance_atr_hi"], 3),
            ci(r["esperance_bps"], r["esperance_bps_lo"], r["esperance_bps_hi"], 1),
            f"{sg(r['brut_atr'], 3)} ; {fr(r['frais_atr'], 3)}",
            f"{pct(r['mdd_valorise_r25'])} ; {pct(r['mdd_valorise'])}",
            f"{fr(r['calmar_r25'], 2)} ; {fr(r['calmar_1x'], 2)}",
            f"{n_fr(r['n_trades'])} ({fr(r['trades_par_mois'], 1)})",
            f"{fr(r['duree_mediane'], 0)} ; {fr(r['duree_mediane_h'], 1)} h",
            "brut ≤ 0" if r["brut_bps"] <= 0 else ("> 1 000 %" if r["part_frais"] > 10 else pct(r["part_frais"], 0))]


HEAD8 = ["Actif · variante", "PnL : 0,25 %/ATR ; 1x", "PF (1x)", "WR", "Espérance ATR [IC]", "Espérance bps [IC]",
         "Brut ; frais (ATR)", "MDD : 0,25 %/ATR ; 1x", "Calmar : 0,25 %/ATR ; 1x", "Trades (/mois)",
         "Durée médiane : barres ; h", "Part des frais (1x, brut en bps)"]


def section_profil(prof: pd.DataFrame, diags: dict) -> str:
    out = ["### B. Action 1 : trades sautés par la course à H = 65 contre trades gardés (entrées de RE-1)"]
    for key in ACTIFS:
        g = diags[key]["groupes"]
        out.append(f"\n**{key}**\n")
        out.append(table(["Groupe", "n", "Net à la sortie de RE-1 (26 barres), ATR [IC]", "Médiane (26)",
                          "WR (26)", "Net sans ses 3 meilleurs trades (26)", "Net à 65 barres, ATR [IC]"],
                         [[k, g[k]["n"], ci(*g[k]["net26"], 3), sg(g[k]["mediane26"], 3), pct(g[k]["wr26"]),
                           sg(g[k]["sans_top3_26"], 3), ci(*g[k]["net65"], 3)] for k in ("sautes", "gardes")]))
        rows = []
        for _, r in prof[prof.actif == key].iterrows():
            if r["variable"] in CONTINUES:
                cell = lambda q: f"{sg(q[1], 2)} [{sg(q[0], 2)} ; {sg(q[2], 2)}]"  # noqa: E731
                rows.append([r["variable"], cell(r["sautes"]), cell(r["gardes"]),
                             ci(r["auc"], r["auc_lo"], r["auc_hi"], 2), "—"])
            elif r["variable"] in BINAIRES:
                rows.append([f"part {r['variable']}", pct(r["sautes"][0], 0), pct(r["gardes"][0], 0),
                             ci(r["auc"], r["auc_lo"], r["auc_hi"], 2), "—"])
            else:
                rows.append([r["variable"], pct(r["sautes"][0], 0), pct(r["gardes"][0], 0), "—",
                             sg(r["net26_categorie"], 3)])
        out.append("")
        out.append(table(["Variable à t", "Sautés : P50 [P25 ; P75] ou part", "Gardés", "AUC sautés > gardés [IC]",
                          "Net (26) de la catégorie, tous trades"], rows))
    return "\n".join(out)


def write_report() -> None:
    res = pd.read_csv(HERE / "resultats_D01_6.csv")
    prof = pd.read_json(HERE / "profil_D01_6.json", orient="records")
    diags = json.loads((HERE / "diagnostics_D01_6.json").read_text(encoding="utf-8"))
    ctrl = json.loads((HERE / "controles_D01_6.json").read_text(encoding="utf-8"))
    narr = HERE / "narratif_D01_6.md"
    head = narr.read_text(encoding="utf-8").rstrip() + "\n\n" if narr.exists() else "# EXP-D01.6\n\n"
    c = ["### A. Contrôles bloquants", "",
         "- Empreintes SHA-256 identiques à l'audit de D01 ; une séance par date de New York (aucun trou en séance).",
         "- Verrouillage 26 = RE-1 trade par trade ; verrouillage 65 = population de la course à H = 65 de D01.5.",
         "- Sortie de fin de séance : entrées de RE-1 identiques en lecture « entrées de RE-1 » ; aucune position ne "
         "traverse une nuit (sortie au plus tard au close de la dernière barre de la séance d'entrée)."]
    for key, v in ctrl["actifs"].items():
        c.append(f"- {key} : {v['trades_re1']} trades de RE-1, {v['seances']} séances.")
    c.append(f"- Durée du calcul : {ctrl['duree_s']} s.")
    a2 = res[res.action == "2 verrouillage"]
    pop = table(["Actif · variante", "Communs avec RE-1", "Trades de RE-1 retirés : n ; net (26) ATR",
                 "Trades ajoutés : n ; net ATR"],
                [[f"{r['actif']} · {r['variante']}", pct(r["part_communs_re1"], 0),
                  f"{int(r['n_retires'])} ; {sg(r['retires_atr'], 3)}", f"{int(r['n_ajoutes'])} ; {sg(r['ajoutes_atr'], 3)}"]
                 for _, r in a2.iterrows()])
    a3 = res[res.action == "3 séance"]
    app = table(["Actif", "Sorties de fin de séance (entrées de RE-1)", "Effet apparié séance − RE-1, ATR [IC]",
                 "Effet apparié, bps [IC]"],
                [[r["actif"], pct(r["part_sortie_seance"], 0),
                  ci(r["apparie_effet_atr"], r["apparie_effet_atr_lo"], r["apparie_effet_atr_hi"], 3),
                  ci(r["apparie_effet_bps"], r["apparie_effet_bps_lo"], r["apparie_effet_bps_hi"], 1)]
                 for _, r in a3[a3.variante == "séance, entrées de RE-1"].iterrows()])
    parts = [head + "## Annexes générées (run_D01_6.py)", "\n".join(c), section_profil(prof, diags),
             "### C. Action 2 : H_exit = 26, verrouillage H_cooldown ∈ {26, 48, 65, 90}\n\n"
             + table(HEAD8, [row8(r) for _, r in a2.iterrows()]) + "\n\n" + pop,
             "### D. Action 3 : sortie forcée au close de la dernière barre de séance\n\n"
             + table(HEAD8, [row8(r) for _, r in a3.iterrows()]) + "\n\n" + app,
             "### E. Figure\n\n![Verrouillage et séance](figures/D01_6.png)"]
    (HERE / "rapport_D01_6.md").write_text("\n\n".join(parts) + "\n", encoding="utf-8")


def main() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        pass
    if "--rapport" in sys.argv:
        write_report()
        print(f"rapport régénéré : {HERE / 'rapport_D01_6.md'}")
    else:
        run_main()


if __name__ == "__main__":
    main()
