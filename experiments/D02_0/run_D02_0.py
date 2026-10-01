"""EXP-D02.0 — rétro-test de RE-1 figée sur des périodes antérieures jamais vues : BTC/USD 2013-2019 (Bitstamp) et CFD
or de mars 2009 à 2019 (HistData). Aucune optimisation, aucun réglage ; préalable de D02.

Usage, depuis la racine du dépôt : python experiments/D02_0/run_D02_0.py [--rapport]
  (défaut)  : contrôles bloquants, RE-1 sur chaque lecture → resultats_D02_0.csv, annuel_D02_0.csv,
              diagnostics_D02_0.json, controles_D02_0.json, figures/D02_0.png, rapport_D02_0.md ;
  --rapport : régénère rapport_D02_0.md (narratif_D02_0.md rédigé à la main, puis annexes générées) sans recalcul.
Données : experiments/D02_0/donnees_D02_0.py ; audit validé par le porteur le 2026-10-01 (audit_donnees_D02_0.md).

Cadrage (validé par le porteur le 2026-10-01)
- QUESTION : RE-1 figée garde-t-elle une espérance nette sur des périodes qu'elle n'a jamais vues : BTC 2013-2019 et
  l'or de mars 2009 à 2019 ?
- PERTINENCE POUR LE FILTRE AKF : les seuils (médiane de leg_atr, P75 de nis_z_100) et la géométrie R2 viennent de BTC
  2020-2025. Des régimes plus anciens (BTC étroit et beaucoup plus volatil ; or : sommet de 2011, krach de 2013, range
  2015-2018) testent la stabilité de la cinématique dans le temps, sans aucune adaptation. C'est la référence figée
  contre laquelle le gain du walk-forward de D02 sera mesuré.
- CE QUE LE PROTOCOLE MESURE RÉELLEMENT : les 8 métriques nettes (BTC 5 bps en lecture principale et 10 bps ; or
  4 bps), PnL composé et MDD à 1x à côté de 0,25 %/ATR, espérance en ATR et en bps avec IC par grappes mensuelles,
  années, Long/Short, F2b/F3, cadence ; écart des populations (médiane de leg_atr et P75 de nis_z_100 de la période)
  aux seuils gelés ; frais en ATR par année ; pour BTC, les trades qui touchent les suites sans transaction de 2013,
  la sensibilité à la panne de janvier 2015 et une lecture hors 2013.
- CE QU'IL NE PERMET PAS DE CONCLURE : rien sur 2026 (scellé) ; coûts actuels appliqués à des années où les vrais coûts
  étaient plus élevés (convention du porteur) ; aucun critère de réussite ni comparaison statistique avec 2020-2025 ;
  aucune modification de RE-1 sur la base de ces résultats ; structure de marché différente (BTC avant 2017, flux du
  courtier HistData avant 2019).

Décisions du porteur (2026-10-01)
- Coûts actuels sur les années anciennes : BTC 5 bps (lecture principale) et 10 bps ; or 4 bps.
- Panne de Bitstamp de janvier 2015 : données brutes intactes ; période non négociable dans le backtest principal,
  aucun trade créé à partir des barres plates. Mise en œuvre : les 215 barres plates sans transaction du
  2015-01-05 09:30 au 2015-01-09 20:30 UTC (suite repérée par l'audit, vérifiée ici avant tout calcul) sont retirées
  de la série vue par RE-1, comme une fermeture de marché : aucun signal ni aucune exécution sur ces barres ; un trade
  ouvert avant la panne la traverse et se termine sur les barres suivantes (H compté en barres de la série, comme les
  CFD sur leurs fermetures). Sensibilité : la même chaîne sur la série brute.
- RE-1 n'est pas modifiée sur la base de ces résultats.

Exécution (fixée avant le calcul)
- Séries tronquées au 2019-12-31 23:30 : aucune barre de 2020 n'est lue ; préchauffage de 300 barres de 30 min et de
  300 bougies d'1 h comptées depuis la première barre ; trade ouvert en fin de période clos à la dernière barre (moteur
  de C02bis, même convention qu'en fin 2025) ;
- annualisation sur la durée propre de la période (de la première barre à la fin de la dernière) ;
- lecture hors 2013 : trades de la lecture principale entrés à partir du 2014-01-01 (mêmes trades, 6 ans) ;
- trades dont la tenue [entrée ; sortie] touche une suite d'au moins 8 barres sans transaction : comptés, isolés ;
- références 2020-2025 (BTC : C02bis et D01 ; or : D01) lues dans experiments/D01/resultats_D01.csv ; contrôle
  bloquant : RE-1 redonne les 1 080 trades de C02bis sur BTC 2020-2025 (`check_btc` de D01).
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

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


D01 = _load("run_D01", ROOT / "experiments" / "D01" / "run_D01.py")
AUD = _load("audit_donnees_D02_0", HERE / "audit_donnees_D02_0.py")
plt = D01.plt
fr, sg, pct, spct, n_fr, ci, table = D01.fr, D01.sg, D01.pct, D01.spct, D01.n_fr, D01.ci, D01.table

from anatomy import build_atlas  # noqa: E402
from categorization import add_derived  # noqa: E402
from envelope import risk_weights  # noqa: E402
from estimand.bars import check_no_holdout  # noqa: E402
from strategy import H, LEG_ATR_P50_BTC, NIS_Z100_P75_BTC, RISK_BPS, frozen_masks, metrics, run_re1  # noqa: E402
from utils.data_loader import load_ohlc, meta_path  # noqa: E402

RAW = ROOT / "data" / "raw"
FIG = HERE / "figures"
BPS = 1e4
BAR = pd.Timedelta(minutes=30)
YEAR = pd.Timedelta(days=365.25)
FIN = pd.Timestamp("2020-01-01", tz="UTC")                  # aucune barre de 2020 n'est lue
HORS_2013 = pd.Timestamp("2014-01-01", tz="UTC")
PANNE = (pd.Timestamp("2015-01-05 09:30", tz="UTC"), pd.Timestamp("2015-01-09 20:30", tz="UTC"))
IDLE_MIN_BARS = 8
BTC_CSV = RAW / "bitstamp_btcusd_30m_2013_2025.csv"
XAU_CSV = RAW / "histdata_xauusd_30m_2009_2025.csv"
LECTURES = {
    "BTC 2013-2019": {"nom": "BTC/USD Bitstamp 2013-2019, panne de janvier 2015 non négociable (lecture principale)",
                      "csv": BTC_CSV, "debut": "2013-01-01", "panne": True, "fees": (5.0, 10.0)},
    "XAU 2009-2019": {"nom": "CFD or XAU/USD HistData, 2009-03-15 → 2019", "csv": XAU_CSV, "debut": "2009-01-01",
                      "panne": False, "fees": (4.0,)},
    "BTC brut": {"nom": "BTC/USD Bitstamp 2013-2019, série brute (sensibilité : barres plates de la panne gardées)",
                 "csv": BTC_CSV, "debut": "2013-01-01", "panne": False, "fees": (5.0, 10.0)},
}
REFS = {"BTC": "BTC 2020-2025 (réf.)", "XAU": "XAU 2020-2025 (réf.)"}
COLORS = {"BTC 2013-2019": "#7f7f7f", "XAU 2009-2019": "#d4a017", "BTC brut": "#1f77b4"}
for _k, _v in LECTURES.items():                              # sections de diagnostic de D01 (frais de lecture)
    D01.ASSETS[_k] = {"nom": _v["nom"], "csv": _v["csv"], "fees": _v["fees"]}


def period_years(bars: pd.DataFrame) -> float:
    """Durée propre de la période, de la première barre à la fin de la dernière, en années de 365,25 jours."""
    return float((bars.time.iat[-1] + BAR - bars.time.iat[0]) / YEAR)



def load(path: Path) -> pd.DataFrame:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")                      # trous signalés par load_ohlc : mesurés par l'audit
        return load_ohlc(path)


def outage_mask(df: pd.DataFrame) -> np.ndarray:
    """Barres de la panne de janvier 2015 ; vérifie avant tout calcul qu'elles forment exactement la suite plate sans
    transaction repérée par l'audit (215 barres au même prix que la dernière clôture avant l'arrêt), bornée par deux
    barres avec transactions."""
    sel = ((df.time >= PANNE[0]) & (df.time <= PANNE[1])).to_numpy()
    g = df[sel]
    n = int((PANNE[1] - PANNE[0]) / BAR) + 1
    before, after = df[df.time < PANNE[0]].iloc[-1], df[df.time > PANNE[1]].iloc[0]
    ok = (len(g) == n and (g.volume == 0).all() and (g.high == g.low).all() and (g.open == g.close).all()
          and g.close.nunique() == 1 and float(g.close.iat[0]) == float(before.close)
          and before.volume > 0 and after.volume > 0 and after.time - PANNE[1] == BAR)
    if not ok:
        raise SystemExit("panne de janvier 2015 : barres différentes de la suite plate de l'audit : arrêt")
    return sel


def prepare(key: str) -> dict:
    """Barres de la lecture (tronquées avant 2020, panne retirée si demandé), atlas, ATR, masques aux seuils gelés."""
    lec = LECTURES[key]
    df = load(lec["csv"])
    df = df[(df.time >= pd.Timestamp(lec["debut"], tz="UTC")) & (df.time < FIN)].reset_index(drop=True)
    info = {"barres_lues": len(df)}
    if lec["panne"]:
        mask = outage_mask(df)
        info["barres_panne_retirees"] = int(mask.sum())
        df = df[~mask].reset_index(drop=True)
    bars = df[["time", "open", "high", "low", "close"]].copy()
    check_no_holdout(bars)
    if not bars.time.is_monotonic_increasing or (bars.time >= FIN).any():
        raise SystemExit(f"{key} : barres non triées ou postérieures à 2019 : arrêt")
    atlas, f, _, atr = build_atlas(df)
    fam, m = frozen_masks(atlas)
    atr_bps = pd.Series(atlas.atr14_bps.to_numpy(), index=atlas.bar_index.to_numpy())
    info.update({"premiere": str(bars.time.iat[0]), "derniere": str(bars.time.iat[-1]), "barres": len(bars),
                 "annees": period_years(bars)})
    return {"df": df, "bars": bars, "atlas": atlas, "f": f, "atr": atr, "atr_bps": atr_bps, "fam": fam, "m": m,
            "info": info}


def net_atr(tr: pd.DataFrame, p: dict, fee: float) -> np.ndarray:
    return (tr.ret_gross_bps.to_numpy(dtype=float) - fee) / p["atr_bps"].reindex(tr.signal_bar.to_numpy()).to_numpy()


def entry_times(tr: pd.DataFrame, p: dict) -> pd.Series:
    return p["bars"].time.iloc[tr.entry_bar.to_numpy()].reset_index(drop=True)


def measure(label: str, p: dict, tr: pd.DataFrame, fam: pd.Series, fee: float, n_cand: int,
            n_years: float) -> tuple[dict, pd.DataFrame]:
    m, y = metrics(tr, p["bars"], p["atr_bps"], fee, n_cand, fam, n_years)
    t = p["bars"].time
    hours = (t.iloc[tr.exit_bar.to_numpy()].to_numpy() - t.iloc[tr.entry_bar.to_numpy()].to_numpy()) \
        / np.timedelta64(1, "h")
    m.update({"actif": label, "frais_bps": fee, "duree_mediane_h": float(np.median(hours)),
              "debut": str(entry_times(tr, p).min()), "fin": str(t.iloc[tr.exit_bar.to_numpy()].max())})
    a = p["atr_bps"].reindex(tr.signal_bar.to_numpy()).to_numpy()
    yrs = entry_times(tr, p).dt.year.to_numpy()
    gross = tr.ret_gross_bps.to_numpy(dtype=float) / a
    extra = pd.DataFrame({"annee": yrs, "brut_atr": gross, "frais_atr": fee / a, "atr14_bps": a}).groupby("annee").agg(
        brut_atr=("brut_atr", "mean"), frais_atr=("frais_atr", "mean"), atr14_bps_P50=("atr14_bps", "median"))
    y = y.merge(extra, left_on="annee", right_index=True, how="left")
    y.insert(0, "actif", label)
    y.insert(1, "frais_bps", fee)
    return m, y


def truncated(tr: pd.DataFrame, p: dict) -> int:
    """Trades clos à la dernière barre avant leur horizon (fin de période), sans stop."""
    last = len(p["bars"]) - 1
    return int(((tr.exit_bar.to_numpy() == last) & ~tr.stop.to_numpy(dtype=bool)
                & (tr.exit_bar.to_numpy() - tr.entry_bar.to_numpy() < H)).sum())


def idle_trades(p: dict, tr: pd.DataFrame, fee: float) -> dict:
    """Trades dont la tenue [entrée ; sortie] touche une suite d'au moins 8 barres sans transaction (audit)."""
    df = p["df"]
    runs = AUD.idle_runs(df, IDLE_MIN_BARS)
    pos = pd.Series(np.arange(len(df)), index=pd.DatetimeIndex(df.time))
    spans = [(int(pos[pd.Timestamp(r["debut"])]), int(pos[pd.Timestamp(r["fin"])])) for r in runs]
    e, x = tr.entry_bar.to_numpy(), tr.exit_bar.to_numpy()
    hit = np.zeros(len(tr), dtype=bool)
    for a, b in spans:
        hit |= (e <= b) & (x >= a)
    v = net_atr(tr, p, fee)
    return {"suites": len(runs), "trades": int(hit.sum()),
            "esperance_atr_touches": float(v[hit].mean()) if hit.any() else None,
            "esperance_atr_autres": float(v[~hit].mean()),
            "liste": [{"entree": str(entry_times(tr, p).iat[i]), "net_atr": float(v[i])} for i in np.flatnonzero(hit)]}


def compare_outage(pa: dict, tra: pd.DataFrame, pb: dict, trb: pd.DataFrame, fee: float) -> dict:
    """Lecture principale (a, panne retirée) contre série brute (b) : trades communs (même entrée, même sens), trades
    propres à chaque lecture, trades de la série brute nés de la panne ou la traversant, trades de (a) traversant le
    trou de la panne, écart d'espérance."""
    ta, tb = entry_times(tra, pa), entry_times(trb, pb)
    xa = pa["bars"].time.iloc[tra.exit_bar.to_numpy()].reset_index(drop=True)
    xb = pb["bars"].time.iloc[trb.exit_bar.to_numpy()].reset_index(drop=True)
    sb = pb["bars"].time.iloc[trb.signal_bar.to_numpy()].reset_index(drop=True)
    ka = pd.Series([f"{t}|{x}" for t, x in zip(ta, tra.side.to_numpy())])
    kb = pd.Series([f"{t}|{x}" for t, x in zip(tb, trb.side.to_numpy())])
    va, vb = net_atr(tra, pa, fee), net_atr(trb, pb, fee)
    only_a, only_b = ~ka.isin(set(kb)), ~kb.isin(set(ka))
    in_out = (sb >= PANNE[0]) & (sb <= PANNE[1])
    cross_b = (tb < PANNE[0]) & (xb >= PANNE[0]) & ~in_out
    cross_a = (ta < PANNE[0]) & (xa > PANNE[1])
    diff_t = pd.concat([ta[only_a], tb[only_b]])

    def lst(ts, xs, v, sel):
        return [{"entree": str(ts.iat[i]), "sortie": str(xs.iat[i]), "net_atr": float(v[i])} for i in np.flatnonzero(sel)]
    return {"trades_principal": len(tra), "trades_brut": len(trb), "communs": int((~only_a).sum()),
            "propres_principal": lst(ta, xa, va, only_a.to_numpy()), "propres_brut": lst(tb, xb, vb, only_b.to_numpy()),
            "premiere_divergence": str(diff_t.min()) if len(diff_t) else None,
            "derniere_divergence": str(diff_t.max()) if len(diff_t) else None,
            "brut_nes_de_la_panne": lst(tb, xb, vb, in_out.to_numpy()),
            "brut_traversant_la_panne": lst(tb, xb, vb, cross_b.to_numpy()),
            "principal_traversant_le_trou": lst(ta, xa, va, cross_a.to_numpy()),
            "somme_net_atr_principal": float(va.sum()), "somme_net_atr_brut": float(vb.sum())}


def reference_rows() -> pd.DataFrame:
    res = pd.read_csv(ROOT / "experiments" / "D01" / "resultats_D01.csv")
    ref = res[((res.actif == "BTC") & res.frais_bps.isin([5.0, 10.0])) | ((res.actif == "XAU") & (res.frais_bps == 4.0))]
    ref = ref.copy()
    ref["actif"] = ref.actif.map(REFS)
    return ref


def run_main() -> None:
    t0 = time.time()
    ctrl: dict = {"seuils_gele": {"leg_atr_p50": LEG_ATR_P50_BTC, "nis_z_100_p75": NIS_Z100_P75_BTC}}
    p_btc = D01.prepare("BTC")
    ctrl["btc_2020_2025"] = D01.check_btc(p_btc)               # convention de C02bis : 6 ans sur 2020-2025
    D01.sample_years = period_years                              # puis durée propre (diagnostics de D01, sans stop)
    d_btc = add_derived(p_btc["atlas"])
    D01.BTC_NIS_Q.update({pp: float(np.quantile(d_btc.nis_z_100, pp)) for pp in D01.NIS_PS})
    print(f"contrôles BTC 2020-2025 passés ({time.time() - t0:.0f} s)", flush=True)
    for key, src in (("BTC 2013-2019", BTC_CSV), ("XAU 2009-2019", XAU_CSV)):
        meta = json.loads(meta_path(src).read_text(encoding="utf-8"))
        audit = json.loads((HERE / "audit_donnees_D02_0.json").read_text(encoding="utf-8"))[key[:3].strip()]
        if meta["sha256"] != audit["sha256"]:
            raise SystemExit(f"{key} : empreinte du CSV différente de l'audit validé : arrêt")
    preps, runs, rows, years, diags, profils = {}, {}, [], [], {}, {}
    ctrl["lectures"] = {}
    for key, lec in LECTURES.items():
        p = prepare(key)
        tr, fam = run_re1(p["bars"], p["atlas"], p["atr"], p["m"])
        preps[key], runs[key] = p, (tr, fam)
        ny = p["info"]["annees"]
        n_cand = int(p["m"]["R2"].sum())
        profils[key] = D01.signal_profile(p)
        ctrl["lectures"][key] = {**p["info"], "trades": len(tr), "candidats": n_cand,
                                 "trades_clos_en_fin_de_periode": truncated(tr, p)}
        for fee in lec["fees"]:
            m, y = measure(key, p, tr, fam, fee, n_cand, ny)
            rows.append(m)
            years.append(y)
            print(f"{key} {fee:g} bps : {len(tr)} trades, espérance {m['esperance_atr']:+.3f} ATR "
                  f"[{m['esperance_atr_lo']:+.3f} ; {m['esperance_atr_hi']:+.3f}] ({time.time() - t0:.0f} s)", flush=True)
        if key != "BTC brut":
            fee = lec["fees"][0]
            diags[key] = {f"{fee:g}": D01.diagnostics(key, p, tr, fam, fee)}
        if key == "BTC 2013-2019":                         # lecture hors 2013 : mêmes trades, entrés dès 2014
            sel = (entry_times(tr, p) >= HORS_2013).to_numpy()
            n_c = int((p["m"]["R2"] & (p["atlas"].timestamp >= HORS_2013).to_numpy()).sum())
            for fee in lec["fees"]:
                m, y = measure("BTC 2014-2019", p, tr[sel].reset_index(drop=True), fam, fee, n_c,
                               float((FIN - HORS_2013) / YEAR))
                rows.append(m)
            diags[key]["suites_sans_transaction"] = idle_trades(p, tr, lec["fees"][0])
    tra, _ = runs["BTC 2013-2019"]
    trb, _ = runs["BTC brut"]
    diags["panne_2015"] = {f"{fee:g}": compare_outage(preps["BTC 2013-2019"], tra, preps["BTC brut"], trb, fee)
                           for fee in (5.0, 10.0)}
    res = pd.concat([pd.DataFrame(rows), reference_rows()], ignore_index=True)
    lead = ["actif", "frais_bps", "annees", "debut", "fin"]
    res = res[lead + [c for c in res.columns if c not in lead]]
    ann = pd.concat(years, ignore_index=True)
    diags["profils_signaux"] = profils
    ctrl["duree_s"] = round(time.time() - t0)
    res.to_csv(HERE / "resultats_D02_0.csv", index=False, float_format="%.6g")
    ann.to_csv(HERE / "annuel_D02_0.csv", index=False, float_format="%.6g")
    (HERE / "diagnostics_D02_0.json").write_text(json.dumps(D01.jsonable(diags), ensure_ascii=False, indent=1),
                                                 encoding="utf-8")
    (HERE / "controles_D02_0.json").write_text(json.dumps(D01.jsonable(ctrl), ensure_ascii=False, indent=1),
                                               encoding="utf-8")
    figure(preps, runs, ann)
    write_report()
    print(f"D02.0 : {len(res)} lignes en {ctrl['duree_s']} s ; résultats, diagnostics, figure et rapport dans {HERE}")


# ── Figure ──────────────────────────────────────────────────────────────────────
def figure(preps: dict, runs: dict, ann: pd.DataFrame) -> None:
    FIG.mkdir(parents=True, exist_ok=True)
    fig, axes = plt.subplots(1, 3, figsize=(18, 4.8))
    for key in ("BTC 2013-2019", "BTC brut", "XAU 2009-2019"):
        p, (tr, _) = preps[key], runs[key]
        fee = LECTURES[key]["fees"][0]
        net = tr.ret_gross_bps.to_numpy(dtype=float) - fee
        w = risk_weights(p["atr_bps"].reindex(tr.signal_bar.to_numpy()).to_numpy(dtype=float), RISK_BPS)
        tx = p["bars"].time.iloc[tr.exit_bar.to_numpy()].to_numpy()
        ls = "--" if key == "BTC brut" else "-"
        axes[0].plot(tx, np.cumprod(1 + w * net / BPS), ls, color=COLORS[key], label=f"{key} ({fee:g} bps)")
        axes[1].plot(tx, np.cumprod(1 + net / BPS), ls, color=COLORS[key], label=f"{key} ({fee:g} bps)")
    for ax, ttl in zip(axes[:2], ("capital à 0,25 % par ATR14(t)", "capital à 1x (notionnel fixe)")):
        ax.set_yscale("log")
        ax.set_title(f"RE-1 figée, rétro-test — {ttl}")
        ax.axhline(1, color="k", lw=0.6)
        ax.legend()
    yrs = list(range(2009, 2020))
    for i, key in enumerate(("BTC 2013-2019", "XAU 2009-2019")):
        g = ann[(ann.actif == key) & (ann.frais_bps == LECTURES[key]["fees"][0])].set_index("annee").reindex(yrs)
        axes[2].bar(np.arange(len(yrs)) + (i - 0.5) * 0.4, g.esperance_atr, 0.4, color=COLORS[key], label=key)
    axes[2].set_xticks(np.arange(len(yrs)), [str(y) for y in yrs])
    axes[2].axhline(0, color="k", lw=0.6)
    axes[2].set_title("Espérance nette par trade (ATR14(t)) par année d'entrée")
    axes[2].legend()
    fig.tight_layout()
    fig.savefig(FIG / "D02_0.png", dpi=110)
    plt.close(fig)


# ── Rapport ─────────────────────────────────────────────────────────────────────
def section_controles(ctrl: dict) -> str:
    b = ctrl["btc_2020_2025"]
    out = ["## A. Contrôles bloquants et conventions", "",
           f"- RE-1 sur BTC 2020-2025 par la chaîne de D01 : {n_fr(b['trades'])} trades identiques à C02bis ; "
           f"{b['metriques_comparees']} métriques comparées, écart relatif maximal "
           f"{D01.C2B.sci(b['ecart_relatif_max']) if b['ecart_relatif_max'] > 0 else '0'} ; ancre P6.5d reproduite.",
           f"- Seuils gelés : médiane de leg_atr {fr(LEG_ATR_P50_BTC, 4)}, P75 de nis_z_100 {fr(NIS_Z100_P75_BTC, 4)} "
           "(atlas BTC 2020-2025), jamais recalculés.",
           "- Empreintes des deux CSV égales à celles de l'audit validé ; aucune barre de 2020 ni de 2026 lue.",
           "- Capital : 0,25 % par ATR14(t) (poids min(1 ; 25 bps / ATR14 en bps), levier ≤ 1x) et notionnel 1x. "
           "IC 95 % par bootstrap de grappes de mois d'entrée, 2 000 tirages. Annualisation sur la durée propre de "
           "chaque période.", ""]
    rows = []
    for k, v in ctrl["lectures"].items():
        extra = f" ; {n_fr(v['barres_panne_retirees'])} barres de panne retirées" if "barres_panne_retirees" in v else ""
        rows.append([k, f"{v['premiere'][:16]} → {v['derniere'][:16]}", f"{n_fr(v['barres'])}{extra}",
                     fr(v["annees"], 2), f"{n_fr(v['trades'])} / {n_fr(v['candidats'])}",
                     n_fr(v["trades_clos_en_fin_de_periode"])])
    return "\n".join(out + [table(["Lecture", "Barres lues (UTC)", "Barres", "Années", "Trades / candidats",
                                   "Trades clos à la dernière barre"], rows)])


def section_metriques(res: pd.DataFrame) -> str:
    return "\n".join(["## B. Tableau standard (8 métriques nettes)", "",
                      table(D01.HEAD8, [D01.row8(r) for _, r in res.iterrows()]), "",
                      "## C. Risque, sens, timing et sous-familles", "",
                      table(D01.HEADRISK, [D01.rowrisk(r) for _, r in res.iterrows()])])


def section_populations(diags: dict) -> str:
    aud01 = json.loads((ROOT / "experiments" / "D01" / "audit_D01.json").read_text(encoding="utf-8"))
    prof = dict(diags["profils_signaux"])
    prof = {"BTC 2013-2019": prof["BTC 2013-2019"], REFS["BTC"]: aud01["BTC"]["signaux"],
            "XAU 2009-2019": prof["XAU 2009-2019"], REFS["XAU"]: aud01["XAU"]["signaux"]}
    rows = []
    for k, s in prof.items():
        rows.append([k, f"{n_fr(s['n_signaux'])} ({fr(s['signaux_par_mois'], 1)})",
                     f"{fr(s['mediane_locale_leg_atr'], 3)} ; {pct(s['part_leg_sous_seuil_btc'], 1)}",
                     f"{fr(s['p75_local_nis_z_100'], 3)} ; {pct(s['part_nis_au_dessus_seuil_btc'], 1)} ; "
                     f"{pct(s['part_nis_au_dessus_seuil_btc_dans_R2'], 1)}",
                     f"{n_fr(s['regimes']['R2_avant_nis'])} → {n_fr(s['univers_RE1'])} ({n_fr(s['F2b'])} ; "
                     f"{n_fr(s['F3'])})",
                     f"{fr(s['atr14_bps']['P50'], 1)} [{fr(s['atr14_bps']['P10'], 1)} ; {fr(s['atr14_bps']['P90'], 1)}]"])
    return "\n".join(["## D. Populations face aux seuils gelés (descriptif, tous les signaux de l'atlas)", "",
                      table(["Période", "Signaux (par mois)",
                             f"leg_atr : médiane locale ; part < {fr(LEG_ATR_P50_BTC, 3)}",
                             f"nis_z_100 : P75 local ; part > {fr(NIS_Z100_P75_BTC, 3)} : tous ; dans R2",
                             "R2 avant nis → univers RE-1 (F2b ; F3)", "ATR14 bps P50 [P10 ; P90]"], rows)])


def section_annees(ann: pd.DataFrame) -> str:
    rows = []
    for (a, fee), g in ann.groupby(["actif", "frais_bps"], sort=False):
        if fee != LECTURES[a]["fees"][0]:
            continue
        for _, r in g.iterrows():
            rows.append([f"{a} {fr(fee, 0)} bps", int(r["annee"]), n_fr(r["n_trades"]), sg(r["esperance_atr"], 3),
                         sg(r["esperance_bps"], 1), f"{sg(r['brut_atr'], 3)} ; {fr(r['frais_atr'], 3)}",
                         fr(r["atr14_bps_P50"], 1), spct(r["pnl_compose_r25"], 1), spct(r["pnl_compose"], 1),
                         f"{sg(r['long_atr'], 2)} / {sg(r['short_atr'], 2)}"])
    return "\n".join(["## E. Années (année d'entrée, frais de lecture principale)", "",
                      table(["Lecture", "Année", "Trades", "Espérance nette ATR", "Espérance nette bps",
                             "Brut ATR ; frais ATR", "ATR14 bps (P50)", "PnL 0,25 %/ATR", "PnL 1x",
                             "Long / Short ATR"], rows)])


def section_panne(diags: dict) -> str:
    out = ["## L. Panne de Bitstamp de janvier 2015 : lecture principale (période non négociable) contre série brute",
           ""]
    for fee, c in diags["panne_2015"].items():
        out += [f"**{fee} bps** : {n_fr(c['trades_principal'])} trades contre {n_fr(c['trades_brut'])} sur la série "
                f"brute ; {n_fr(c['communs'])} communs (même entrée, même sens) ; divergence du "
                f"{(c['premiere_divergence'] or '—')[:16]} au {(c['derniere_divergence'] or '—')[:16]} ; somme des "
                f"espérances nettes {sg(c['somme_net_atr_principal'], 2)} ATR contre {sg(c['somme_net_atr_brut'], 2)}.",
                ""]
    c = diags["panne_2015"]["5"]

    def lines(name, lst):
        return [f"- {name} : " + ("aucun" if not lst else "; ".join(
            f"entrée {x['entree'][:16]}, sortie {x['sortie'][:16]}, {sg(x['net_atr'], 2)} ATR" for x in lst))]
    out += lines("trades de la série brute nés d'un signal sur les barres plates", c["brut_nes_de_la_panne"])
    out += lines("trades de la série brute ouverts avant la panne et la traversant", c["brut_traversant_la_panne"])
    out += lines("trades de la lecture principale traversant le trou de la panne", c["principal_traversant_le_trou"])
    out += lines("trades propres à la lecture principale", c["propres_principal"])
    out += lines("trades propres à la série brute", c["propres_brut"])
    s = diags["BTC 2013-2019"]["suites_sans_transaction"]
    out += ["", "## M. Marché étroit de 2013 : trades touchant une suite d'au moins 4 h sans transaction", "",
            f"{s['suites']} suites hors panne ; {n_fr(s['trades'])} trades touchés, espérance nette "
            f"{sg(s['esperance_atr_touches'], 3) if s['esperance_atr_touches'] is not None else '—'} ATR contre "
            f"{sg(s['esperance_atr_autres'], 3)} pour les autres (5 bps)."]
    return "\n".join(out)


def section_gaps_xau(diags: dict) -> str:
    g = diags["XAU 2009-2019"]["4"].get("gaps_ouverture")
    if not g:
        return ""
    b, ge, gs = g["brut_log_atr"], g["composante_ecarts_atr"], g["composante_seance_atr"]
    return "\n".join(["## N. Or : écarts d'ouverture traversés (définitions de D01)", "",
                      f"Écarts traversés par trade (P50) {fr(g['ecarts_traverses_par_trade']['P50'], 0)} ; trades "
                      f"concernés {pct(g['part_trades_traversant_un_ecart'], 0)} ; brut (log) "
                      f"{ci(b['moyenne'], b['lo'], b['hi'], 3)} ATR, dont écarts {ci(ge['moyenne'], ge['lo'], ge['hi'], 3)}"
                      f", dont séance {ci(gs['moyenne'], gs['lo'], gs['hi'], 3)} ; stops en gap "
                      f"{n_fr(g['stops']['n_en_gap'])} / {n_fr(g['stops']['n'])}."])


def write_report() -> None:
    parts = []
    narr = HERE / "narratif_D02_0.md"
    parts.append(narr.read_text(encoding="utf-8").rstrip() if narr.exists() else "# EXP-D02.0 (narratif à rédiger)")
    parts += ["", "---", "", "# Annexes chiffrées (générées par `run_D02_0.py`)", ""]
    ctrl = json.loads((HERE / "controles_D02_0.json").read_text(encoding="utf-8"))
    res, ann = pd.read_csv(HERE / "resultats_D02_0.csv"), pd.read_csv(HERE / "annuel_D02_0.csv")
    diags = json.loads((HERE / "diagnostics_D02_0.json").read_text(encoding="utf-8"))
    dd = {k: diags[k] for k in ("BTC 2013-2019", "XAU 2009-2019")}
    parts += [section_controles(ctrl), "", section_metriques(res), "", section_populations(diags), "",
              section_annees(ann), "", D01.section_diag(dd, res), "", section_panne(diags), "",
              section_gaps_xau(diags), "", "Figure : `figures/D02_0.png`."]
    (HERE / "rapport_D02_0.md").write_text("\n".join(parts) + "\n", encoding="utf-8")


def main() -> None:
    if "--rapport" in sys.argv:
        write_report()
        print(f"rapport_D02_0.md régénéré dans {HERE}")
        return
    run_main()


if __name__ == "__main__":
    main()
