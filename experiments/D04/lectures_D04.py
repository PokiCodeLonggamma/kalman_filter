"""EXP-D04 — lectures complémentaires, hors protocole (écrites après la lecture des résultats, sans effet sur la règle
du porteur) : queue droite (part du 1 % et du 5 % meilleurs, espérance sans eux, meilleur trade), stops touchés, et
référence de la pire journée (capital valorisé à 00:00 contre solde réalisé à 00:00).

Usage, depuis la racine du dépôt : python experiments/D04/lectures_D04.py  →  lectures_D04.json
"""
from __future__ import annotations

import importlib.util
import json
import sys
import warnings
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "src"))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

spec = importlib.util.spec_from_file_location("run_D04", HERE / "run_D04.py")
D04 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(D04)

from envelope import risk_weights  # noqa: E402
from envelope.daily import daily_losses, marked_equity  # noqa: E402
from optimization import drop_best  # noqa: E402
from reserve import levee  # noqa: E402

FEE = 5.0


def tails(p: dict, s: dict) -> dict:
    tr = s["trades"].reset_index(drop=True)
    a = p["atr_bps"][tr.signal_bar.to_numpy()]
    net = tr.ret_gross_bps.to_numpy(dtype=float) - FEE
    na = net / a
    w = risk_weights(a, 25.0)
    cap = w * net / 1e4
    top = np.sort(na)[::-1]
    k1, k5 = int(np.ceil(0.01 * len(na))), int(np.ceil(0.05 * len(na)))
    kept = drop_best(tr, pd.Series(p["atr_bps"], index=np.arange(len(p["bars"]))), FEE, 0.01)
    j = int(np.argmax(cap))
    t = p["bars"].time
    fam = s["fam"].reindex(tr.signal_bar.to_numpy()).to_numpy()
    lv = pd.Series(s["cands"][2], index=s["cands"][0]).reindex(tr.signal_bar.to_numpy()).to_numpy()
    lvl = pd.Series(s["cands"][3], index=s["cands"][0]).reindex(tr.signal_bar.to_numpy()).to_numpy()
    cat = tr.stop.to_numpy() & ((fam == "F2b") | (lvl != lv))
    return {"trades": len(tr), "mediane_atr": float(np.median(na)),
            "part_top1": float(top[:k1].sum() / na.sum()), "n_top1": k1, "part_top5": float(top[:k5].sum() / na.sum()),
            "esperance_sans_top1": float(((kept.ret_gross_bps.to_numpy() - FEE)
                                          / p["atr_bps"][kept.signal_bar.to_numpy()]).mean()),
            "meilleur_trade_capital": {"entree": str(t.iat[int(tr.entry_bar.iat[j])]), "brut_bps": float(net[j] + FEE),
                                       "atr": float(na[j]), "capital": float(cap[j]), "part_somme_atr": float(na[j] / na.sum()),
                                       "esperance_sans_lui": float(np.delete(na, j).mean()),
                                       "pnl_r25_sans_lui": float(np.prod(1 + np.delete(cap, j)) - 1),
                                       "pnl_r25": float(np.prod(1 + cap) - 1)},
            "part_sorties_stop": float(tr.stop.mean()), "stop_catastrophe_touche": int(cat.sum()),
            "part_stop_catastrophe": float(cat.mean()), "gaps": int(tr.gap.sum())}


def worst_day_references(p: dict, s: dict) -> dict:
    """Pire journée rapportée au capital valorisé à 00:00 (mesure du protocole) et au solde réalisé à 00:00."""
    tr = s["trades"].reset_index(drop=True)
    w = risk_weights(p["atr_bps"][tr.signal_bar.to_numpy()], 25.0)
    d = daily_losses(p["bars"], tr, FEE, w)
    eq = marked_equity(p["bars"], tr, FEE, w)
    day = d.perte.idxmin()
    # solde réalisé à 00:00 : capital après la dernière sortie antérieure à minuit (ou avant le trade ouvert à minuit)
    exits = (pd.DatetimeIndex(p["bars"].time.iloc[tr.exit_bar.to_numpy()])
             + pd.to_timedelta(np.where(tr.stop.to_numpy(dtype=bool), 30, 0), unit="min"))
    realized = np.cumprod(1.0 + w * (tr.ret_gross_bps.to_numpy() - FEE) / 1e4)
    before = exits <= day
    balance = float(realized[before][-1]) if before.any() else 1.0
    low = float(eq[(eq.index > day) & (eq.index <= day + pd.Timedelta(days=1))].min())
    return {"jour": str(day.date()), "perte_ref_capital_valorise": float(d.perte.min()),
            "perte_ref_solde_realise": low / balance - 1.0}


def main() -> None:
    out = {}
    with levee("EXP-D04 lectures complémentaires"):
        for key in D04.PAIRS:
            p = D04.prepare(key, D04.ethxrp_csv(key), D04.END)
            s = D04.final_series(p, None, None)
            out[key] = tails(p, s) | {"pire_journee": worst_day_references(p, s)}
            print(key, "fait", flush=True)
    (HERE / "lectures_D04.json").write_text(json.dumps(D04.D01.jsonable(out), ensure_ascii=False, indent=1),
                                            encoding="utf-8")


if __name__ == "__main__":
    warnings.simplefilter("ignore")
    main()
