"""EXP-D04 (Phase 7) — épreuve de la réserve : RE-1 version finale (stop catastrophe de 4 ATR greffé) sur ETH/USD et
XRP/USD (tout l'historique, test A) et sur 2026 (BTC, SOL, AVAX, or ; test B). Directive du porteur du 2026-10-03
(`RESEARCH_LOG.md`, EXP-D04).

Usage, depuis la racine du dépôt :
  python experiments/D04/run_D04.py --controle        réserve scellée, sans réseau : la version finale redonne D03.1
  python experiments/D04/run_D04.py --telechargement  réserve levée : téléchargements autorisés par le porteur
  python experiments/D04/run_D04.py --calcul          réserve levée : contrôles bloquants, tests A et B, annexes
  python experiments/D04/run_D04.py --rapport         rapport depuis les sorties

Protocole pré-enregistré (porteur, 2026-10-03 ; commit local avant tout téléchargement ; aucune modification après
lecture : un incident de données est consigné comme tel, jamais corrigé en silence)
- Moteur gelé : RE-1 version finale (`strategy.final.run_final`) : seuils BTC gelés, R0 = 100, frontière 0,85, H = 26,
  verrou 26, F2b sans SL-B, F3 SL-B (extremum du segment, δ = 0, plancher 0,25 ATR), stop catastrophe à 4 ATR14(t) sur
  tous les trades (le plus proche des deux pour F3) ; entrée à open[t + 1] ; 0,25 % du capital par ATR14(t), levier
  ≤ 1x ; PnL et MDD à 1x à côté. Aucun autre paramètre, aucun filtre, aucune autre variante calculée sur la réserve.
- Test A (actifs purs) : ETH/USD et XRP/USD Bitstamp 30 min, de la première barre cotée au 2026-10-01 00:00 UTC exclu,
  barres telles que servies (rien de retiré ; audit consigné) ; tous les signaux hors warm-up ; 5 bps (10 bps en
  lecture). 8 métriques ; espérance par année civile d'entrée (ATR et bps, IC 95 % par grappes mensuelles).
- Test B (année pure) : signaux du 2026-01-01 au 2026-10-01 exclu (convention des périodes de D03.1 : candidats
  restreints à la période, verrou neuf au 1er janvier) ; atlas calculé sur l'historique continu (filtre de Kalman depuis
  la première barre). BTC/USD Bitstamp (panne de janvier 2015 retirée, comme en D02-D03.1), SOL/USD et AVAX/USD
  Coinbase (5 bps, 10 en lecture), or XAU/USD HistData (4 bps, 6 en lecture ; si HistData n'a pas publié septembre,
  fin au 2026-09-01). 8 métriques.
- Incident consigné (avant tout calcul sur 2026) : l'archive HistData de juin 2026 sert 26 minutes deux fois avec des
  valeurs différentes ; elles sont fusionnées (`histdata.merge_conflicting_minutes`), rien n'est jeté.
- Lectures de survie (les six séries) : pire trade et pire journée UTC en % du capital (valorisé aux clôtures de 30 min,
  et aux extrêmes défavorables des barres détenues ; `envelope.daily`), à 0,25 %/ATR et à 1x ; MDD ; PnL.
- Règle de décision du porteur (verbatim) : « Si la stratégie dégage une espérance nette strictement positive
  (E[ATR]_net > 0) sur ETH et XRP d'une part, et qu'elle a survécu sans crash à l'année 2026 d'autre part, la stratégie
  est validée pour la production. » Lecture consignée avant les données : E[ATR]_net = moyenne par trade du rendement
  net de 5 bps en ATR14(t), estimation ponctuelle, pour ETH et pour XRP séparément (IC donné en lecture) ; « survécu
  sans crash » : jugé par le porteur sur les mesures, sans seuil fixé (réponse du porteur du 2026-10-03).
- Contrôles bloquants : (1) la version finale redonne trade par trade D03.1 « Stop catastrophe 4 ATR » (BTC 2015-2025,
  SOL) ; (2) empreinte de chaque nouvelle série égale à son méta ; (3) barres antérieures à 2026 des séries prolongées
  égales aux séries scellées ; (4) mêmes candidats (barre, sens, niveaux) avant 2026 et mêmes trades clos avant la
  dernière barre scellée, sur séries prolongées et scellées.
- Réserve non vierge (passation §2.1) : ETH et XRP ont été vus par d'anciens projets (Kalman, « Labos 2-3 ») ; BTC 2026
  aussi. Aucun paramètre de RE-1 n'a été choisi sur ces données.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import re
import subprocess
import sys
import time
import warnings
from pathlib import Path
from types import SimpleNamespace

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


D03_1 = _load("run_D03_1", ROOT / "experiments" / "D03_1" / "run_D03_1.py")
D03, D02, D01 = D03_1.D03, D03_1.D02, D03_1.D01

from anatomy import build_atlas  # noqa: E402
from envelope import mean_ci, risk_weights  # noqa: E402
from envelope.daily import daily_losses  # noqa: E402
from estimand.stoploss import TRADE_COLUMNS  # noqa: E402
from indicator import KalmanParams  # noqa: E402
from optimization import signal_table  # noqa: E402
from reserve import levee  # noqa: E402
from strategy import load_asset  # noqa: E402
from strategy.final import run_final  # noqa: E402
from strategy.re1 import N_BOOT  # noqa: E402
from utils.data_loader import meta_path, sha256_file  # noqa: E402

BPS = 1e4
RAW = ROOT / "data" / "raw"
CACHE = RAW / "_cache"
FIG = HERE / "figures"
MOTIF = "EXP-D04 (porteur, 2026-10-03)"
END = pd.Timestamp("2026-10-01", tz="UTC")
END_XAU_SANS_SEPTEMBRE = pd.Timestamp("2026-09-01", tz="UTC")
B0 = "2026-01-01"
NAME = "RE-1 version finale"
FEES = {"ETH": (5.0, 10.0), "XRP": (5.0, 10.0), "BTC": (5.0, 10.0), "SOL": (5.0, 10.0), "AVAX": (5.0, 10.0),
        "XAU": (4.0, 6.0)}
SEALED = {k: D02.SERIES[k][0] for k in ("BTC", "SOL", "AVAX", "XAU")}
EXTENDED = {"BTC": RAW / "bitstamp_btcusd_30m_2013_2026.csv", "SOL": RAW / "coinbase_solusd_30m_2021_2026.csv",
            "AVAX": RAW / "coinbase_avaxusd_30m_2021_2026.csv", "XAU": RAW / "histdata_xauusd_30m_2009_2026.csv"}
PAIRS = {"ETH": "ethusd", "XRP": "xrpusd"}
SOURCES = {"ETH": "Bitstamp", "XRP": "Bitstamp", "BTC": "Bitstamp", "SOL": "Coinbase", "AVAX": "Coinbase",
           "XAU": "HistData"}


def stop(msg: str):
    raise SystemExit(f"D04, contrôle bloquant : {msg} : arrêt")


def ts(x) -> pd.Timestamp:
    t = pd.Timestamp(x)
    return t.tz_localize("UTC") if t.tzinfo is None else t


def git_head() -> str:
    return subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip()


# ── Téléchargements (réserve levée) ─────────────────────────────────────────────
def _extra(meta: dict, first_builder_key: str) -> dict:
    """Clés descriptives d'un méta existant (celles qui suivent les clés écrites par le téléchargeur)."""
    ks = list(meta)
    return {k: meta[k] for k in ks[ks.index(first_builder_key) + 1:]}


def _old_meta(csv: Path) -> dict:
    return json.loads(meta_path(csv).read_text(encoding="utf-8"))


def ethxrp_csv(key: str) -> Path:
    found = sorted(RAW.glob(f"bitstamp_{PAIRS[key]}_30m_*_2026.csv"))
    if len(found) != 1:
        stop(f"{key} : série introuvable ou ambiguë ({[p.name for p in found]})")
    return found[0]


def download() -> dict:
    """Téléchargements autorisés par le porteur le 2026-10-03 (liste, sources et tailles annoncées avant)."""
    from marketdata.bitstamp import build_bitstamp_csv
    from marketdata.coinbase import build_coinbase_csv
    from marketdata.histdata import build_histdata_csv, fetch_month
    out = {}
    with levee(MOTIF):
        btc_extra = _extra(_old_meta(SEALED["BTC"]), "fichiers_annuels")
        for key, pair in PAIRS.items():
            extra = dict(btc_extra, actif=key,
                         instrument=f"{key}/USD, carnet spot de Bitstamp (TradingView : BITSTAMP:{key}USD)",
                         ticker=f"{pair} (Bitstamp)", couverture_demandee="première barre cotée → 2026-09-30 (fin exclue "
                         "2026-10-01) ; années antérieures à la cotation demandées, vides",
                         sources_ecartees="aucune", decision="porteur, 2026-10-03 : EXP-D04, réserve levée (test A)")
            tmp = CACHE / "bitstamp" / f"_provisoire_{pair}.csv"
            m = build_bitstamp_csv(pair, 2014, 2026, tmp, CACHE / "bitstamp", extra, end=END)
            y0 = int(m["first"][:4])
            final = RAW / f"bitstamp_{pair}_30m_{y0}_2026.csv"
            out[key] = build_bitstamp_csv(pair, y0, 2026, final, CACHE / "bitstamp", extra, end=END)
            tmp.unlink()
            meta_path(tmp).unlink()
            print(f"{key} : {out[key]['n_rows']} barres, {out[key]['first']} → {out[key]['last']}", flush=True)
        extra = dict(btc_extra, couverture_demandee="2013-01-01 → 2026-09-30 (fin exclue 2026-10-01) ; 2026 téléchargé "
                     "pour EXP-D04 (réserve levée)", decision=btc_extra["decision"] + " ; porteur, 2026-10-03 : 2026 "
                     "téléchargé pour EXP-D04")
        out["BTC"] = build_bitstamp_csv("btcusd", 2013, 2026, EXTENDED["BTC"], CACHE / "bitstamp", extra, end=END)
        print(f"BTC : {out['BTC']['n_rows']} barres → {out['BTC']['last']}", flush=True)
        for key, product in (("SOL", "SOL-USD"), ("AVAX", "AVAX-USD")):
            old = _old_meta(SEALED[key])
            extra = dict(_extra(old, "fichiers_15m"), decision_d04="porteur, 2026-10-03 : 2026 téléchargé pour EXP-D04 "
                         "(réserve levée)")
            first = old["fichiers_15m"][0]["mois"]
            out[key] = build_coinbase_csv(product, first, "2026-09", EXTENDED[key], CACHE / "coinbase", extra)
            print(f"{key} : {out[key]['n_rows']} barres → {out[key]['last']}", flush=True)
        old = _old_meta(SEALED["XAU"])
        extra = dict(_extra(old, "archives"), decision_d04="porteur, 2026-10-03 : 2026 téléchargé pour EXP-D04 (réserve "
                     "levée)")
        months, end, note = [(2026, m) for m in range(1, 10)], END, None
        try:
            fetch_month("XAUUSD", 2026, 9, CACHE / "histdata")
        except ValueError as e:                             # septembre pas encore publié : fin au 2026-09-01
            months, end, note = months[:-1], END_XAU_SANS_SEPTEMBRE, f"septembre 2026 indisponible : {e}"
        if note:
            extra["incident_d04"] = note
        extra["incident_d04_conflits"] = ("archive de juin 2026 : 26 minutes servies deux fois avec des valeurs "
                                          "différentes (2026-06-28 22:08 → 2026-06-30 16:02 UTC) ; fusionnées "
                                          "(conflits=\"fusion\"), règle fixée avant tout calcul sur 2026")
        out["XAU"] = build_histdata_csv("XAUUSD", 2009, 2025, EXTENDED["XAU"], CACHE / "histdata", extra,
                                        months=months, end=end, conflits="fusion")
        print(f"XAU : {out['XAU']['n_rows']} barres → {out['XAU']['last']}" + (f" ({note})" if note else ""), flush=True)
    (HERE / "telechargements_D04.json").write_text(json.dumps(D01.jsonable(
        {k: {c: v[c] for c in ("source", "n_rows", "first", "last", "sha256", "extracted_at_utc") if c in v}
         | {"fichier": (ethxrp_csv(k).name if k in PAIRS else EXTENDED[k].name)} for k, v in out.items()}),
        ensure_ascii=False, indent=1), encoding="utf-8")
    return out


# ── Préparation des séries ──────────────────────────────────────────────────────
def prepare(key: str, csv: Path, end: pd.Timestamp | None) -> dict:
    """Barres (empreinte vérifiée, fin `end`, panne de 2015 retirée pour BTC), atlas à R0 = 100, table des signaux,
    ATR14 en bps par barre. `end` > 2026-01-01 exige la réserve levée."""
    meta = json.loads(meta_path(csv).read_text(encoding="utf-8"))
    sha = sha256_file(csv)
    if sha != meta["sha256"]:
        stop(f"{key} : empreinte de {csv.name} différente de son .meta.json")
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        df, _ = load_asset(csv, end=end)
    info = {"fichier": csv.name, "sha256": sha[:16]}
    if key == "BTC":
        mask = D03.D02_0.outage_mask(df)
        if int(mask.sum()) != 215:
            stop("BTC : panne de janvier 2015 différente de 215 barres")
        df = df[~mask].reset_index(drop=True)
        info["panne_barres_retirees"] = 215
    bars = df[["time", "open", "high", "low", "close"]].copy()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        atlas, f, idx, atr = build_atlas(df, kalman=KalmanParams(R0=100.0))
    tab = signal_table(bars, atlas, atr)
    sig = f.signal.to_numpy().astype(int)
    raw = np.flatnonzero((sig != 0) & f.valid_features.to_numpy(dtype=bool))
    tail = raw[raw > (idx.max() if len(idx) else -1)]           # signaux de fin de série sans sortie native observée
    vol = df["volume"].to_numpy(dtype=float) if "volume" in df else np.full(len(df), np.nan)
    year = df.time.dt.year
    info.update({"barres": len(bars), "premiere": str(bars.time.iat[0]), "derniere": str(bars.time.iat[-1]),
                 "signaux": len(atlas), "premier_signal": str(tab.time[0]) if len(tab.t) else None,
                 "signaux_bruts_censures_en_fin": len(tail),
                 "premier_signal_censure": str(bars.time.iat[int(tail[0])]) if len(tail) else None,
                 "volume_nul_par_an": {int(y): int(v) for y, v in pd.Series(vol <= 0).groupby(year.to_numpy()).sum().items()},
                 "plates_par_an": {int(y): int(v) for y, v in
                                   pd.Series((df.high == df.low).to_numpy()).groupby(year.to_numpy()).sum().items()}})
    step = bars.time.diff().fillna(pd.Timedelta(0))
    big = step > pd.Timedelta(minutes=30)
    info["trous"] = int(big.sum())
    if big.any():
        i = int(np.argmax(step.to_numpy()))
        info["plus_long_trou"] = {"apres": str(bars.time.iat[i - 1]), "barres_manquantes":
                                  int(step.iat[i] / pd.Timedelta(minutes=30)) - 1}
    return {"key": key, "bars": bars, "tab": tab, "atr_bps": atr / bars.close.to_numpy() * BPS, "info": info,
            "sig": sig}


def final_series(p: dict, start: str | None, end) -> dict:
    tr, cands, fam = run_final(p["bars"], p["tab"], p["atr_bps"], None if start is None else ts(start),
                               None if end is None else ts(end))
    return {"trades": tr, "cands": cands, "fam": fam}


# ── Contrôles ───────────────────────────────────────────────────────────────────
def check_d03_1() -> dict:
    """Réserve scellée : la version finale redonne, trade par trade, la série « Stop catastrophe 4 ATR » de D03.1."""
    out = {}
    ref = pd.read_csv(ROOT / "experiments" / "D03_1" / "resultats_D03_1.csv")
    for key, label in (("BTC", "BTC 2015-2025 · 5 bps"), ("SOL", "SOL 2021-2025 · 5 bps")):
        p = D03.prepare(key)
        a, b = list(D03_1.PERIODS[key].values())[0]
        series, _ = D03_1.variants(p, a, b)
        s = final_series(p, a, b)
        if not s["trades"][TRADE_COLUMNS].equals(series[D03_1.CAT]["trades"][TRADE_COLUMNS]):
            stop(f"{key} : la version finale diffère de D03.1 « {D03_1.CAT} »")
        m, _ = D03.measure(label, NAME, s, p, 5.0, a, b)
        r = ref[(ref.actif == label) & (ref.variante == D03_1.CAT)].iloc[0]
        if m["n_trades"] != r.n_trades or not np.isclose(m["esperance_atr"], r.esperance_atr, rtol=1e-5):
            stop(f"{key} : métriques différentes de resultats_D03_1.csv")
        out[key] = {"trades": int(m["n_trades"]), "esperance_atr": round(float(m["esperance_atr"]), 6)}
        print(f"{key} : version finale = D03.1 « {D03_1.CAT} » ({m['n_trades']} trades, "
              f"{m['esperance_atr']:+.6f} ATR)", flush=True)
    return out


def check_extension(key: str, sealed: dict, ext: dict) -> dict:
    """Barres, candidats et trades antérieurs à 2026 identiques sur la série prolongée et la série scellée."""
    bs, be = sealed["bars"], ext["bars"]
    n = len(bs)
    if not be.iloc[:n].reset_index(drop=True).equals(bs.reset_index(drop=True)) or be.time.iat[n] < ts(B0):
        stop(f"{key} : barres antérieures à 2026 différentes de la série scellée")
    if not np.array_equal(ext["atr_bps"][:n], sealed["atr_bps"], equal_nan=True):
        stop(f"{key} : ATR14 antérieur à 2026 différent")
    s_s, s_e = final_series(sealed, None, None), final_series(ext, "2000-01-01", B0)
    t_s, t_e = s_s["cands"][0], s_e["cands"][0]
    if np.setdiff1d(t_s, t_e).size:
        stop(f"{key} : candidat de la série scellée absent de la série prolongée")
    extra = np.setdiff1d(t_e, t_s)
    sig = ext["sig"]
    for t in extra:                          # convention de l'atlas (`anatomy.dev_universe`) : sortie native observée
        opp = np.flatnonzero(sig[t + 1:] == -sig[t])
        exit_native = t + 1 + int(opp[0]) + 1 if opp.size else len(sig)
        if exit_native <= n - 1:
            stop(f"{key} : candidat en plus avant 2026 non expliqué par la convention de fin d'échantillon ({t})")
    keep = np.isin(t_e, t_s)
    for i, name in enumerate(("barres", "sens", "SL-B", "niveaux finaux")):
        if not np.array_equal(s_s["cands"][i], s_e["cands"][i][keep], equal_nan=True):
            stop(f"{key} : candidats antérieurs à 2026 différents ({name})")
    t_cut = int(extra.min()) if extra.size else n
    tr = s_s["trades"]
    done = (tr.exit_bar.to_numpy() < n - 1) & (tr.signal_bar.to_numpy() < t_cut)
    a, b = tr[done].reset_index(drop=True), s_e["trades"].iloc[:int(done.sum())].reset_index(drop=True)
    if not a[TRADE_COLUMNS].equals(b[TRADE_COLUMNS]):
        stop(f"{key} : trades antérieurs à 2026 différents")
    return {"barres_avant_2026": n, "candidats_avant_2026": len(t_s), "trades_identiques": int(done.sum()),
            "trades_non_compares_en_fin_de_serie_scellee": int((~done).sum()),
            "candidats_censures_en_fin_de_serie_scellee": [str(ext["bars"].time.iat[int(t)]) for t in extra]}


# ── Mesures ─────────────────────────────────────────────────────────────────────
def measure(label: str, key: str, s: dict, p: dict, fee: float, start: pd.Timestamp, end: pd.Timestamp) -> tuple:
    m, y = D03.measure(label, NAME, s, p, fee, str(start.date()), str(end.date()))
    m.update({"cle": key, "fenetre_debut": str(start.date()), "fenetre_fin": str(end.date())})
    return m, y


def yearly(key: str, s: dict, p: dict, fee: float, start, end) -> pd.DataFrame:
    """Espérance par année civile d'entrée, avec IC 95 % par grappes mensuelles (ATR et bps)."""
    tr = D03.subset(s, p["bars"], str(start.date()), str(end.date()))["trades"][TRADE_COLUMNS]
    bars, atr = p["bars"], pd.Series(p["atr_bps"], index=np.arange(len(p["bars"])))
    year = bars.time.iloc[tr.entry_bar.to_numpy()].dt.year.to_numpy()
    rows = []
    for y in np.unique(year):
        g = tr[year == y].reset_index(drop=True)
        a = atr.reindex(g.signal_bar.to_numpy()).to_numpy()
        net = g.ret_gross_bps.to_numpy(dtype=float) - fee
        w = risk_weights(a, 25.0)
        c = mean_ci(g, bars, fee, N_BOOT, atr_bps=atr)
        rows.append({"actif": key, "frais_bps": fee, "annee": int(y), "n_trades": len(g),
                     "esperance_atr": float(np.mean(net / a)), "esperance_atr_lo": c["esperance_atr_lo"],
                     "esperance_atr_hi": c["esperance_atr_hi"], "esperance_bps": float(net.mean()),
                     "esperance_bps_lo": c["esperance_bps_lo"], "esperance_bps_hi": c["esperance_bps_hi"],
                     "pnl_compose_r25": float(np.prod(1.0 + w * net / BPS) - 1.0), "wr": float((net > 0).mean())})
    return pd.DataFrame(rows)


def survival(key: str, s: dict, p: dict, fee: float, start, end) -> dict:
    tr = D03.subset(s, p["bars"], str(start.date()), str(end.date()))["trades"][TRADE_COLUMNS].reset_index(drop=True)
    bars, t = p["bars"], p["bars"].time
    a = p["atr_bps"][tr.signal_bar.to_numpy()]
    net = tr.ret_gross_bps.to_numpy(dtype=float) - fee
    out = {"actif": key, "frais_bps": fee, "trades": len(tr)}
    for tag, w in (("r25", risk_weights(a, 25.0)), ("1x", np.ones(len(tr)))):
        r = w * net / BPS
        i = int(np.argmin(r))
        out[f"pire_trade_{tag}"] = float(r[i])
        out[f"pire_trade_{tag}_date"] = str(t.iat[int(tr.entry_bar.iat[i])])
        out[f"pire_trade_{tag}_famille"] = str(s["fam"].get(int(tr.signal_bar.iat[i]), "?"))
        for ext in (False, True):
            d = daily_losses(bars, tr, fee, w, extremes=ext)
            k = "extremes" if ext else "clotures"
            out[f"pire_jour_{k}_{tag}"] = float(d.perte.min())
            out[f"pire_jour_{k}_{tag}_date"] = str(d.perte.idxmin().date())
            if not ext:
                out[f"jours_en_position_{tag}"] = len(d)
                out[f"jours_sous_moins_1pct_{tag}"] = int((d.perte < -0.01).sum())
    return out


def curve(s: dict, p: dict, fee: float, start, end) -> pd.Series:
    sub = D03.subset(s, p["bars"], str(start.date()), str(end.date()))
    return D02.equity_points(sub, SimpleNamespace(bars=p["bars"], atr_bps=p["atr_bps"]), fee)


def run_controle() -> None:
    ctrl = {"date": pd.Timestamp.now(tz="UTC").strftime("%Y-%m-%d %H:%M UTC"), "commit": git_head(),
            "version_finale_egale_D03_1": check_d03_1()}
    (HERE / "controle_scelle_D04.json").write_text(json.dumps(D01.jsonable(ctrl), ensure_ascii=False, indent=1),
                                                    encoding="utf-8")
    print("D04 --controle : passé (réserve scellée, aucune donnée de la réserve lue)")


def run_calcul() -> None:
    t0 = time.time()
    ctrl = {"date": pd.Timestamp.now(tz="UTC").strftime("%Y-%m-%d %H:%M UTC"), "commit": git_head(),
            "version_finale_egale_D03_1": check_d03_1()}
    rows, years, surv, curves, data = [], [], [], {}, {}
    with levee(MOTIF):
        ext = {}
        for key in ("BTC", "SOL", "AVAX", "XAU"):
            sealed = D03.prepare(key)
            meta = json.loads(meta_path(EXTENDED[key]).read_text(encoding="utf-8"))
            end_k = ts(meta.get("fin_exclue", END)) if key == "XAU" else END
            ext[key] = prepare(key, EXTENDED[key], end_k)
            ext[key]["end"] = min(end_k, END)
            ctrl[f"prolongement_{key}"] = check_extension(key, sealed, ext[key])
            data[key] = ext[key]["info"]
            print(f"{key} : prolongement contrôlé ({time.time() - t0:.0f} s)", flush=True)
        # Test A : ETH et XRP, tout l'historique
        for key in PAIRS:
            p = prepare(key, ethxrp_csv(key), END)
            data[key] = p["info"]
            s = final_series(p, None, None)
            start = ts(p["tab"].time[0]).normalize()
            for fee in FEES[key]:
                m, _ = measure(f"{key} · test A · {fee:g} bps", key, s, p, fee, start, END)
                m["test"] = "A"
                rows.append(m)
            years.append(yearly(key, s, p, FEES[key][0], start, END))
            surv.append(survival(key, s, p, FEES[key][0], start, END) | {"test": "A"})
            curves[key] = curve(s, p, FEES[key][0], start, END)
            print(f"{key} : test A fait ({time.time() - t0:.0f} s)", flush=True)
        # Test B : 2026
        for key in ("BTC", "SOL", "AVAX", "XAU"):
            p = ext[key]
            s = final_series(p, B0, p["end"])
            for fee in FEES[key]:
                m, _ = measure(f"{key} · 2026 · {fee:g} bps", key, s, p, fee, ts(B0), p["end"])
                m["test"] = "B"
                rows.append(m)
            surv.append(survival(key, s, p, FEES[key][0], ts(B0), p["end"]) | {"test": "B"})
            curves[f"{key} 2026"] = curve(s, p, FEES[key][0], ts(B0), p["end"])
            print(f"{key} : test B fait ({time.time() - t0:.0f} s)", flush=True)
    res = pd.DataFrame(rows)
    lead = ["test", "cle", "actif", "variante", "frais_bps", "fenetre_debut", "fenetre_fin", "annees"]
    res[lead + [c for c in res.columns if c not in lead]].to_csv(HERE / "resultats_D04.csv", index=False,
                                                                 float_format="%.6g")
    pd.concat(years, ignore_index=True).to_csv(HERE / "annuel_D04.csv", index=False, float_format="%.6g")
    pd.DataFrame(surv).to_csv(HERE / "survie_D04.csv", index=False, float_format="%.6g")
    (HERE / "donnees_D04.json").write_text(json.dumps(D01.jsonable(data), ensure_ascii=False, indent=1),
                                           encoding="utf-8")
    ctrl["duree_s"] = round(time.time() - t0)
    (HERE / "controles_D04.json").write_text(json.dumps(D01.jsonable(ctrl), ensure_ascii=False, indent=1),
                                             encoding="utf-8")
    figures(curves)
    write_rapport()
    print(f"D04 : {len(res)} lignes en {ctrl['duree_s']} s ; sorties dans {HERE}")


def figures(curves: dict) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    FIG.mkdir(parents=True, exist_ok=True)
    fig, axes = plt.subplots(1, 2, figsize=(16, 6))
    for ax, keys, title in ((axes[0], ["ETH", "XRP"], "Test A : ETH et XRP, tout l'historique"),
                            (axes[1], ["BTC 2026", "SOL 2026", "AVAX 2026", "XAU 2026"], "Test B : 2026")):
        for k in keys:
            eq = curves[k]
            ax.step(eq.index, 100 * (eq.to_numpy() - 1.0), where="post", lw=1.4, label=k)
        ax.axhline(0, color="k", lw=0.5)
        ax.set_title(f"{title} (capital aux sorties, 0,25 %/ATR, frais de base)", fontsize=10)
        ax.set_ylabel("PnL composé (%)")
        ax.grid(alpha=0.3)
        ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(FIG / "D04_capital.png", dpi=110)
    plt.close(fig)


# ── Rapport (annexes générées ; narratif_D04.md écrit à la main après lecture) ───
fr, sg, pct, spct, n_fr, ci, table = D01.fr, D01.sg, D01.pct, D01.spct, D01.n_fr, D01.ci, D01.table


def metrics_table(res: pd.DataFrame) -> str:
    head = ["Série", "PnL : 0,25 %/ATR ; 1x ; bps (1x)", "PF (1x)", "WR", "Espérance ATR [IC] ; bps",
            "MDD : 0,25 %/ATR ; 1x", "Trades (/mois)", "Durée médiane", "Part des frais (1x) ; brut ; frais (ATR)",
            "Calmar 0,25 %/ATR"]
    rows = []
    for _, x in res.iterrows():
        frais = "brut ≤ 0" if x.brut_bps <= 0 else pct(x.part_frais, 0)
        rows.append([x.actif, f"{spct(x.pnl_compose_r25)} ; {spct(x.pnl_compose)} ; {D02.sgn(x.pnl_bps)}",
                     fr(x.pf, 2), pct(x.wr, 1),
                     f"{ci(x.esperance_atr, x.esperance_atr_lo, x.esperance_atr_hi, 3)} ; {sg(x.esperance_bps, 1)}",
                     f"{pct(x.mdd_valorise_r25)} ; {pct(x.mdd_valorise)}",
                     f"{n_fr(x.n_trades)} ({fr(x.trades_par_mois, 1)})",
                     f"{fr(x.duree_mediane, 0)} b ; {fr(x.duree_mediane_h, 0)} h",
                     f"{frais} ; {sg(x.brut_atr, 2)} ; {fr(x.frais_atr, 2)}", fr(x.calmar_r25, 2)])
    return table(head, rows)


def write_rapport() -> None:
    res = pd.read_csv(HERE / "resultats_D04.csv")
    yr = pd.read_csv(HERE / "annuel_D04.csv")
    sv = pd.read_csv(HERE / "survie_D04.csv")
    ct = json.loads((HERE / "controles_D04.json").read_text(encoding="utf-8"))
    dt = json.loads((HERE / "donnees_D04.json").read_text(encoding="utf-8"))
    narr = HERE / "narratif_D04.md"
    out = [narr.read_text(encoding="utf-8") if narr.exists() else "# EXP-D04 — rapport (narratif à rédiger)\n",
           "", "---", "", "# Annexes générées (`run_D04.py --calcul`, puis `--rapport`)", "",
           f"Calcul du {ct['date']}, commit `{ct['commit']}`, {ct['duree_s']} s.", "", "## A1. Contrôles bloquants (passés)",
           ""]
    for k, v in ct.items():
        if k not in ("date", "commit", "duree_s"):
            out.append(f"- {k} : " + re.sub(r"\b(\d)(\d{3})\b(?!-)", r"\1 \2", json.dumps(v, ensure_ascii=False)) + ".")
    base = res.groupby("cle").frais_bps.transform("min") == res.frais_bps
    for test, title in (("A", "Test A — ETH et XRP, tout l'historique"), ("B", "Test B — 2026 (janvier-septembre)")):
        r = res[res.test == test]
        out += ["", f"## A{2 if test == 'A' else 4}. {title}", "", "**Frais de base (5 bps ; or 4 bps)**", "",
                metrics_table(r[base[r.index]]), "", "**Lecture : frais doublés (10 bps ; or 6 bps)**", "",
                metrics_table(r[~base[r.index]]), ""]
        if test == "A":
            out += ["## A3. Espérance par année d'entrée (5 bps)", ""]
            head = ["Année"] + [f"{k} : trades ; E ATR [IC] ; bps ; PnL 0,25 %/ATR" for k in PAIRS]
            rows = []
            for y in sorted(yr.annee.unique()):
                row = [str(int(y))]
                for k in PAIRS:
                    x = yr[(yr.actif == k) & (yr.annee == y)]
                    if x.empty:
                        row.append("—")
                        continue
                    x = x.iloc[0]
                    row.append(f"{n_fr(x.n_trades)} ; {ci(x.esperance_atr, x.esperance_atr_lo, x.esperance_atr_hi, 3)}"
                               f" ; {sg(x.esperance_bps, 1)} ; {spct(x.pnl_compose_r25)}")
                rows.append(row)
            out += [table(head, rows), ""]
    out += ["## A5. Survie (frais de base)", "",
            table(["Série", "Pire trade : 0,25 %/ATR ; 1x", "Pire journée UTC, clôtures : 0,25 %/ATR ; 1x",
                   "Pire journée, extrêmes : 0,25 %/ATR ; 1x", "Jours en position ; dont < −1 % (0,25 %/ATR)",
                   "Pire trade : date ; famille"],
                  [[f"{x.actif} ({'A' if x.test == 'A' else '2026'})",
                    f"{spct(x.pire_trade_r25, 2)} ; {spct(x.pire_trade_1x, 2)}",
                    f"{spct(x.pire_jour_clotures_r25, 2)} ; {spct(x.pire_jour_clotures_1x, 2)}",
                    f"{spct(x.pire_jour_extremes_r25, 2)} ; {spct(x.pire_jour_extremes_1x, 2)}",
                    f"{n_fr(x.jours_en_position_r25)} ; {n_fr(x.jours_sous_moins_1pct_r25)}",
                    f"{str(x.pire_trade_r25_date)[:10]} ; {x.pire_trade_r25_famille}"] for _, x in sv.iterrows()]),
            "", "## A6. Données", "",
            table(["Série", "Source ; fichier", "Première ; dernière barre", "Barres ; trous (plus long)",
                   "Barres à volume nul ; plates (total)", "Premier signal"],
                  [[k, f"{SOURCES[k]} ; `{d['fichier']}`", f"{d['premiere'][:16]} ; {d['derniere'][:16]}",
                    f"{n_fr(d['barres'])} ; {d['trous']}"
                    + (f" ({d['plus_long_trou']['barres_manquantes']} b après {d['plus_long_trou']['apres'][:10]})"
                       if d.get("plus_long_trou") else ""),
                    f"{n_fr(sum(d['volume_nul_par_an'].values()))} ; {n_fr(sum(d['plates_par_an'].values()))}",
                    str(d["premier_signal"])[:10]] for k, d in dt.items()]),
            ""]
    lec = HERE / "lectures_D04.json"
    if lec.exists():
        lx = json.loads(lec.read_text(encoding="utf-8"))
        out += ["## A7. Lectures complémentaires, hors protocole (`lectures_D04.py`, 5 bps)", "",
                table(["Série", "Médiane ATR", "Part du 1 % ; du 5 % meilleurs", "Espérance sans le 1 % meilleur",
                       "Meilleur trade : date ; ATR ; capital ; part de la somme", "Espérance ; PnL sans lui",
                       "Sorties sur stop ; stop catastrophe", "Pire journée : capital valorisé ; solde réalisé"],
                      [[k, sg(v["mediane_atr"], 2), f"{pct(v['part_top1'], 0)} ({v['n_top1']}) ; {pct(v['part_top5'], 0)}",
                        sg(v["esperance_sans_top1"], 3),
                        f"{v['meilleur_trade_capital']['entree'][:10]} ; {sg(v['meilleur_trade_capital']['atr'], 1)} ; "
                        f"{spct(v['meilleur_trade_capital']['capital'], 1)} ; {pct(v['meilleur_trade_capital']['part_somme_atr'], 0)}",
                        f"{sg(v['meilleur_trade_capital']['esperance_sans_lui'], 3)} ; "
                        f"{spct(v['meilleur_trade_capital']['pnl_r25_sans_lui'])}",
                        f"{pct(v['part_sorties_stop'], 0)} ; {pct(v['part_stop_catastrophe'], 1)}",
                        f"{v['pire_journee']['jour']} : {spct(v['pire_journee']['perte_ref_capital_valorise'], 2)} ; "
                        f"{spct(v['pire_journee']['perte_ref_solde_realise'], 2)}"] for k, v in lx.items()]), ""]
    out += ["## A8. Figure", "", "![Capital](figures/D04_capital.png)", ""]
    (HERE / "rapport_D04.md").write_text("\n".join(out) + "\n", encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--controle", action="store_true", help="réserve scellée : la version finale redonne D03.1")
    g.add_argument("--telechargement", action="store_true", help="réserve levée : téléchargements autorisés")
    g.add_argument("--calcul", action="store_true", help="réserve levée : contrôles, tests A et B, annexes")
    g.add_argument("--rapport", action="store_true", help="régénère rapport_D04.md depuis les sorties")
    args = ap.parse_args()
    if args.controle:
        run_controle()
    elif args.telechargement:
        download()
    elif args.calcul:
        run_calcul()
    else:
        write_rapport()


if __name__ == "__main__":
    main()
