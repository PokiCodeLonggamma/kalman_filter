"""P6.5d — stratégie AKF-TSO v2.1 gelée, sans stop et avec un stop-loss fixe de 2,5 % (D48). Descriptif, aucun ML.

    python experiments/p6_5/strategie_stop.py

Définitions pré-enregistrées (D48) : le script refuse de calculer si un fichier du protocole n'est pas commité.
Signal, filtre et features inchangés ; entrée open[b + 1] ; sortie normale au signal opposé (open[t_opp + 1]) ; stop
2,5 % du prix d'entrée dans le sens de la position, testé sur les high / low des barres détenues, gap exécuté à
l'ouverture (conventions de `estimand.stoploss`). Une seule valeur de stop, fixée a priori : aucune sélection.
Deux niveaux : trade par trade (7 296 événements, comme la cible B) et stratégie séquentielle (sémantique Pine).
Rendements bruts et nets (coût aller-retour 5 bps). Réserve 2026 scellée.

Écrit dans experiments/p6_5/ : strategie_stop.json, strategie_stop_trades.csv, strategie_stop_evenements.csv,
strategie_stop_equite.csv (capital en fin de journée UTC).
"""
from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT_DIR / "src"))

from config import ML1_DATASET_CSV, P65D_COST_BPS, P65D_STOP  # noqa: E402
from estimand import (HOLDOUT, distribution_stats, load_bars_dev, load_events_dev, tail_contributions,  # noqa: E402
                      win_loss_decomposition)
from estimand.exit_rule import load_signals_dev  # noqa: E402
from estimand.stoploss import apply_stop, drawdown_stats, equity_curve, simulate_strategy  # noqa: E402
from estimand.strata import MonthBootstrap, ci95  # noqa: E402
from estimand_audit import _json, sha256  # noqa: E402

OUT = Path(__file__).resolve().parent
OOS_START = pd.Timestamp("2022-01-01", tz="UTC")
VARIANTES = {"sans_stop": None, "stop_2_5": P65D_STOP}
PROTOCOLE = ["src/config.py", "src/estimand", "experiments/p6_5/strategie_stop.py", "docs/decisions.md",
             "docs/P6_5d_stop_loss.md", "tests/test_estimand_p65d.py", "tests/test_estimand_p65d_btc.py"]


def _git(*args) -> str:
    return subprocess.run(["git", *args], cwd=ROOT_DIR, capture_output=True, text=True).stdout.strip()


def verifier_preenregistrement() -> str:
    sale = _git("status", "--porcelain", "--", *PROTOCOLE)
    if sale:
        raise SystemExit("protocole D48 non commité, calcul refusé :\n" + sale)
    return _git("log", "-1", "--format=%h", "--", *PROTOCOLE)


def profil(brut: np.ndarray) -> dict:
    """Distribution par trade, brut et net ; gagnants / perdants et queues sur le net."""
    net = brut - P65D_COST_BPS
    return {"n": int(len(brut)), "brut": distribution_stats(brut), "net": distribution_stats(net),
            "taux_de_reussite_brut": float((brut > 0).mean()), "taux_de_reussite_net": float((net > 0).mean()),
            "gagnants_perdants_net": win_loss_decomposition(net), "queues_net": tail_contributions(net),
            "gagnants_perdants_brut": win_loss_decomposition(brut), "queues_brut": tail_contributions(brut),
            "somme_nette_bps": float(net.sum())}


def niveau_evenement(bars, ev, mb) -> tuple[dict, pd.DataFrame]:
    sans = apply_stop(bars, ev.entry_bar, ev.exit_bar, ev.side, None)
    avec = apply_stop(bars, ev.entry_bar, ev.exit_bar, ev.side, P65D_STOP)
    if not np.array_equal(sans.ret_gross_bps.to_numpy(), ev.ret_gross_bps.to_numpy()):
        raise SystemExit("sans stop, le rendement trade par trade diffère de la cible B : arrêt")
    s, a = sans.ret_gross_bps.to_numpy(), avec.ret_gross_bps.to_numpy()
    st = avec.stop.to_numpy()
    d_est, d_tirs = mb.mean(a - s)
    res = {"sans_stop": profil(s), "stop_2_5": profil(a),
           "part_stoppee": float(st.mean()), "n_stoppes": int(st.sum()), "n_gaps": int(avec.gap.sum()),
           "rendement_stop_moyen_brut": float(a[st].mean()), "rendement_stop_min_brut": float(a[st].min()),
           "stoppes_rendement_sans_stop_moyen": float(s[st].mean()),
           "stoppes_part_finale_positive_sans_stop": float((s[st] > 0).mean()),
           "stoppes_part_finale_sous_moins_250_sans_stop": float((s[st] < -250).mean()),
           "ecart_moyen_apparie_brut": {"estimation": d_est, "ic95": ci95(d_tirs)},
           "moyenne_brute_ic95": {k: ci95(mb.mean(v)[1]) for k, v in (("sans_stop", s), ("stop_2_5", a))},
           "par_annee": {int(y): {"n": int(m.sum()), "sans_stop_moyen_brut": float(s[m].mean()),
                                  "stop_moyen_brut": float(a[m].mean()), "part_stoppee": float(st[m].mean())}
                         for y in sorted(ev.entry_time.dt.year.unique()) for m in [(ev.entry_time.dt.year == y).to_numpy()]}}
    table = pd.concat([ev[["bar_index", "entry_time", "side", "run_rank", "duration_bars"]],
                       sans.ret_gross_bps.rename("ret_sans_stop_bps"),
                       avec[["exit_bar", "stop", "gap", "ret_gross_bps"]].rename(
                           columns={"exit_bar": "sortie_stop", "ret_gross_bps": "ret_stop_bps"})], axis=1)
    return res, table


def bloc_capital(bars, trades) -> dict:
    """Rendement composé et drawdowns, bruts et nets, d'un ensemble de trades (capital initial 1)."""
    out = {}
    for nom, cout in (("net", P65D_COST_BPS), ("brut", 0.0)):
        r = trades.ret_gross_bps.to_numpy() - cout
        cap = np.cumprod(1 + r / 1e4)
        pic = np.maximum.accumulate(np.r_[1.0, cap])[1:]
        out[nom] = {"rendement_compose": float(cap[-1] - 1), "moyenne_bps": float(r.mean()),
                    "taux_de_reussite": float((r > 0).mean()),
                    "max_drawdown_valorise": drawdown_stats(equity_curve(bars, trades, cout)),
                    "max_drawdown_aux_sorties": float(min(0.0, (cap / pic - 1).min()))}
    return out


def niveau_strategie(bars, trades, ouvert, ev) -> tuple[dict, pd.Series]:
    t_entree = bars.time.iloc[trades.entry_bar.to_numpy()].reset_index(drop=True)
    brut = trades.ret_gross_bps.to_numpy()
    net = brut - P65D_COST_BPS
    annees = t_entree.dt.year.to_numpy()
    oos = (t_entree >= OOS_START).to_numpy()
    detenu = int((trades.exit_bar - trades.entry_bar + trades.stop.astype(int)).sum())    # barre du stop détenue
    periode = int(trades.exit_bar.iloc[-1] - trades.entry_bar.iloc[0] + 1)
    cible_b = ev.set_index("bar_index").ret_gross_bps                                        # contrefactuel sans stop
    st = trades.stop.to_numpy()
    sans = cible_b.reindex(trades.signal_bar[st]).to_numpy()
    res = {"n_trades": int(len(trades)), "n_stops": int(st.sum()), "n_gaps": int(trades.gap.sum()),
           "part_long": float((trades.side == 1).mean()), **profil(brut),
           "capital": bloc_capital(bars, trades),
           "moyenne_nette_ic95": ci95(MonthBootstrap(t_entree).mean(net)[1]),
           "exposition": detenu / periode, "periode_barres": periode,
           "duree_mediane_barres": float((trades.exit_bar - trades.entry_bar + trades.stop.astype(int)).median()),
           "stoppes_rendement_sans_stop": None if not st.any() else {
               "n_sans_evenement": int(np.isnan(sans).sum()), "moyen_brut": float(np.nanmean(sans)),
               "part_finale_positive": float(np.nanmean(sans > 0)),
               "part_finale_sous_moins_250": float(np.nanmean(sans < -250))},
           "par_annee": {int(y): {"n": int((annees == y).sum()),
                                  "rendement_compose_net": float(np.prod(1 + net[annees == y] / 1e4) - 1),
                                  "rendement_compose_brut": float(np.prod(1 + brut[annees == y] / 1e4) - 1),
                                  "moyenne_nette": float(net[annees == y].mean())} for y in sorted(set(annees))},
           "oos_2022_2025": None if not oos.any() else {"n": int(oos.sum()),
                                                        **bloc_capital(bars, trades[oos].reset_index(drop=True))},
           "trade_ouvert_fin_2025": ouvert}
    return res, equity_curve(bars, trades, P65D_COST_BPS)


def main() -> int:
    t0 = time.time()
    preenregistrement = verifier_preenregistrement()
    bars, ev, signals = load_bars_dev(), load_events_dev(), load_signals_dev()
    assert (bars.time < pd.Timestamp("2026-01-01", tz="UTC")).all() and len(ev) == 7296
    if {"sklearn", "xgboost", "ml"} & {m.split(".")[0] for m in sys.modules}:
        raise SystemExit("import ML détecté : arrêt (D48)")
    if not (ev.cost_bps == P65D_COST_BPS).all():
        raise SystemExit("coût du dataset différent de 5 bps : arrêt")
    mb = MonthBootstrap(ev.entry_time)
    rap = {"protocole": {"decision": "D48", "stop": P65D_STOP, "cout_bps": P65D_COST_BPS,
                         "strategie": "AKF-TSO v2.1 gelée, signaux bruts B-1.0, entrée open[b+1], sortie open[t_opp+1]",
                         "gestion": "sémantique Pine : retournement au signal opposé, pyramiding 0, à plat après un "
                                    "stop jusqu'au prochain signal de n'importe quel sens",
                         "conventions_stop": "high/low des barres détenues, barre d'entrée comprise ; stop avant le "
                                             "signal opposé de la même barre ; gap exécuté à l'ouverture"},
           "tracabilite": {"commit": _git("rev-parse", "--short", "HEAD"), "commit_preenregistrement": preenregistrement,
                           "dataset_sha256": sha256(ML1_DATASET_CSV), "barres_max": str(bars.time.max()),
                           "modules_ml_importes": sorted({"sklearn", "xgboost", "ml"} & {
                               m.split(".")[0] for m in sys.modules}),
                           "reference_anterieure_v1_stop_2_5": "aucune dans le dépôt KAKALMAN ; reproductibilité "
                                                               "vérifiée sur la cible B (sans stop)"}}
    rap["evenements"], table_ev = niveau_evenement(bars, ev, mb)
    print(f"niveau trade ({time.time() - t0:.0f} s)", flush=True)
    trades_all, equites, strat = [], {}, {}
    for nom, stop in VARIANTES.items():
        trades, ouvert = simulate_strategy(bars, signals, stop)
        if stop is None:
            ref = ev[ev.run_rank == 1]
            if not (np.array_equal(trades.entry_bar.to_numpy(), ref.entry_bar.to_numpy())
                    and np.array_equal(trades.exit_bar.to_numpy(), ref.exit_bar.to_numpy())
                    and np.array_equal(trades.ret_gross_bps.to_numpy(), ref.ret_gross_bps.to_numpy())):
                raise SystemExit("sans stop, la stratégie ne reproduit pas les décisions run_rank == 1 : arrêt")
        if (bars.time.iloc[trades.exit_bar.to_numpy()] >= HOLDOUT).any():
            raise SystemExit("sortie en 2026 : arrêt")
        strat[nom], eq = niveau_strategie(bars, trades, ouvert, ev)
        equites[nom] = eq.groupby(eq.index.normalize()).last()
        trades_all.append(trades.assign(variante=nom, entry_time=bars.time.iloc[trades.entry_bar.to_numpy()].to_numpy()))
        print(f"stratégie {nom} : {len(trades)} trades ({time.time() - t0:.0f} s)", flush=True)
    rap["strategie"] = strat
    pd.concat(trades_all, ignore_index=True).to_csv(OUT / "strategie_stop_trades.csv", index=False, float_format="%.10g")
    table_ev.to_csv(OUT / "strategie_stop_evenements.csv", index=False, float_format="%.10g")
    pd.DataFrame(equites).rename_axis("jour").to_csv(OUT / "strategie_stop_equite.csv", float_format="%.8g")
    rap["duree_s"] = time.time() - t0
    (OUT / "strategie_stop.json").write_text(json.dumps(_json(rap), indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"rapport écrit ({time.time() - t0:.0f} s)", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
