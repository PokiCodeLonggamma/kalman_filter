"""EXP-D05.1, étape 2 — RE-1 version finale sur les actifs hors crypto, barres et frictions FTMO (profil TradFi).

GO du porteur : plan validé le 2026-10-06 (« Étape 2 : Profilage TradFi (RE-1 pure). Fais tourner le modèle sur l'Or,
WTI, Brent, US100, US30, GER40, GBPJPY et SAN avec les coûts FTMO. Je veux l'anatomie de leurs gains (queues, fréquences
des cygnes noirs). ») ; lancement demandé le 2026-10-06 (« backtest notre stratégie sur tous les nouveaux actifs avec les
datas ctrader »).

Cadrage (fixé avant le calcul ; lecture descriptive, sans seuil ni classement) :
- QUESTION : que produit RE-1 version finale, figée, sur chaque actif hors crypto du compte FTMO, une fois payées les
  frictions réelles du compte ; où se trouve son gain (queues, fréquence des grands trades) ?
- DONNÉES : barres M30 FTMO (bid) de l'or, du WTI (USOIL.cash), du Brent (UKOIL.cash), d'US100, US30, GER40 et GBPJPY,
  de la première barre disponible (2020-04 à 2020-11) au 2026-10-01 ; frictions de `propfirm.frictions` (écart par
  demi-heure locale mesuré sur les ticks, commission et swaps des fiches v2). SAN : non exporté, absent. Repère : BTC et
  panier crypto de la fenêtre D05 (séries des courtiers, frictions FTMO, calendrier des pauses), sans nouveau calcul.
- MÉTHODE : `D04.prepare` (atlas à R0 = 100, seuils BTC gelés, ATR14) puis `D04.final_series` (RE-1 et stop
  catastrophe à 4 ATR) sur chaque série ; frais par trade = écart + commission + swaps ; tableau des 8 métriques à
  0,25 %/ATR (plafond 1x par position) et à 1x ; même tableau sans les swaps (unité des swaps du pétrole non vérifiée) ;
  anatomie du net par trade en ATR (quantiles, part des 1 % et 5 % meilleurs trades, trades à +3, +5 et +10 ATR ou plus
  par an, longs et courts) ; nets par année ; corrélation mensuelle avec le panier crypto (net en ATR × 0,25 %, sans
  composition), 2021-10 → 2026-09.
- CE QUE ÇA NE PERMET PAS DE CONCLURE : aucune inclusion (étape 3) ; écarts mesurés sur dix jours de 2026 appliqués à
  toute la période ; swaps du pétrole à la lettre de la fiche (25 bps par nuit en short, [HYP] unité) ; rollover à 17:00
  New York ; seuils de RE-1 gelés sur BTC (D01.7 : transposition sans réglage, conclusions ignorées comme filtre) ;
  historiques de moins de six ans ; données déjà lues (Saxo 2020-2025 en D01.7 et D05.1) ; 2026 inclus.

Usage : python experiments/D05_1/run_profil_D05_1.py
Sorties : profil_tradfi_D05_1.csv (8 métriques), anatomie_tradfi_D05_1.csv, annees_tradfi_D05_1.csv,
correlations_tradfi_D05_1.csv, trades_tradfi_D05_1.csv.gz ; lecture dans rapport_profil_D05_1.md (rédigé).
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

spec = importlib.util.spec_from_file_location("run_frictions_D05_1", HERE / "run_frictions_D05_1.py")
F = importlib.util.module_from_spec(spec)
spec.loader.exec_module(F)
D04, D041, D01 = F.D04, F.D041, F.D01

from envelope import risk_weights  # noqa: E402
from envelope.portfolio import Leg, portfolio_paths  # noqa: E402
from propfirm.frictions import couts_trades  # noqa: E402
from reserve import levee  # noqa: E402

MOTIF = "EXP-D05.1, étape 2 : profil TradFi, RE-1 sur barres FTMO (porteur, 2026-10-06)"
TRADFI = ("XAU", "US100", "US30", "GER40", "GBPJPY", "WTI", "BRENT")
FIN = "2026-10-01"
CRYPTO = ("BTC", "ETH", "SOL", "AVAX", "XRP")
SEUILS = (3.0, 5.0, 10.0)
RISQUE = 0.0025                       # 1 ATR14 = 0,25 % du capital


def anatomie(net: np.ndarray, annees: float, sens: np.ndarray | None = None) -> dict:
    """Net par trade en ATR : quantiles, concentration dans les meilleurs trades, grands trades par an."""
    n = len(net)
    s = np.sort(net)[::-1]
    k1, k5 = max(1, int(round(0.01 * n))), max(1, int(round(0.05 * n)))
    out = {"trades": n, "net_moyen_atr": float(net.mean()), "net_median_atr": float(np.median(net)),
           "p01": float(np.quantile(net, 0.01)), "p05": float(np.quantile(net, 0.05)),
           "p95": float(np.quantile(net, 0.95)), "p99": float(np.quantile(net, 0.99)), "max": float(net.max()),
           "min": float(net.min()), "somme_atr": float(net.sum()), "somme_top1pc_atr": float(s[:k1].sum()),
           "somme_top5pc_atr": float(s[:k5].sum()), "somme_sans_top1pc_atr": float(s[k1:].sum()),
           "somme_sans_top5pc_atr": float(s[k5:].sum()), "pertes_sous_m3_par_an": float((net <= -3.0).sum() / annees)}
    for x in SEUILS:
        out[f"trades_sup_{x:g}atr_par_an"] = float((net >= x).sum() / annees)
        out[f"trades_sup_{x:g}atr"] = int((net >= x).sum())
    if sens is not None:
        for v, nom in ((1, "longs"), (-1, "courts")):
            m = sens == v
            out[f"{nom}"] = int(m.sum())
            out[f"net_moyen_{nom}_atr"] = float(net[m].mean()) if m.any() else np.nan
    return out


def main() -> None:
    t0 = time.time()
    f = F.fiches()
    lignes, anat, ann, trades_out, mensuel = [], [], [], [], {}
    with levee(MOTIF):
        for key in TRADFI:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                p = D04.prepare(key, F.RAW / f"ftmo_{key.lower()}_30m.csv", D04.END)
                p["s"] = D04.final_series(p, None, None)
            a = str(p["bars"].time.iat[0].date())
            tr = D041.window_trades(p, a, FIN)
            prof, _ = F.mesurer_ecarts(key)
            fi, _ = F.fiche(f, key)
            c = couts_trades(tr, p["bars"], fi, prof.mediane, F.FUSEAU[key], prix="bid", sept_jours=False,
                             usd_par_cotation=F.USD_PAR_COTATION.get(key, 1.0))
            atr = p["atr_bps"][tr.signal_bar.to_numpy()]
            ny = (D04.ts(FIN) - D04.ts(a)) / pd.Timedelta(days=365.25)
            for variante, cout in (("frictions FTMO", c.total.to_numpy()),
                                   ("sans swaps", (c.ecart + c.commission).to_numpy())):
                lg = [Leg(key, p["bars"], tr, risk_weights(atr, 25.0), cout)]
                lg1 = [Leg(key, p["bars"], tr, np.ones(len(tr)), cout)]
                m8 = D041.metrics8(lg, lg1, portfolio_paths(lg), portfolio_paths(lg1), {key: p}, a, FIN)
                lignes.append({"cle": key, "symbole": F.NOMS[key], "variante": variante, "debut": a, "fin": FIN,
                               "frais_moyens_bps": float(cout.mean()), "frais_moyens_atr": float((cout / atr).mean()),
                               "ecart_atr": float((c.ecart / atr).mean()),
                               "commission_atr": float((c.commission / atr).mean()),
                               "swap_atr": float((c.swap / atr).mean()), "atr_median_bps": float(np.median(atr)),
                               "part_avec_rollover": float((c.nuits > 0).mean()), **m8})
            brut = tr.ret_gross_bps.to_numpy(dtype=float) / atr
            net = (tr.ret_gross_bps.to_numpy(dtype=float) - c.total.to_numpy()) / atr
            anat.append({"cle": key, "fenetre": f"{a} → {FIN}", "brut_moyen_atr": float(brut.mean()),
                         **anatomie(net, ny, tr.side.to_numpy())})
            t_e = p["bars"].time.iloc[tr.entry_bar.to_numpy()].reset_index(drop=True)
            an = t_e.dt.year.to_numpy()
            for y in np.unique(an):
                m = an == y
                ann.append({"cle": key, "annee": int(y), "trades": int(m.sum()), "net_somme_atr": float(net[m].sum()),
                            "net_moyen_atr": float(net[m].mean()), "brut_moyen_atr": float(brut[m].mean()),
                            "trades_sup_3atr": int((net[m] >= 3.0).sum()), "trades_sup_5atr": int((net[m] >= 5.0).sum())})
            mensuel[key] = pd.Series(net * RISQUE, index=t_e.dt.tz_convert(None).dt.to_period("M")).groupby(level=0).sum()
            trades_out.append(pd.DataFrame({"cle": key, "entree": t_e, "sens": tr.side.to_numpy(), "stop": tr.stop.to_numpy(),
                                            "brut_bps": tr.ret_gross_bps.to_numpy(dtype=float), "atr_bps": atr,
                                            "ecart": c.ecart, "commission": c.commission, "swap": c.swap,
                                            "nuits": c.nuits, "net_atr": net}))
            print(f"{key} : {len(tr)} trades, net moyen {net.mean():+.3f} ATR ({time.time() - t0:.0f} s)", flush=True)
    # repère crypto : trades de la fenêtre D05 avec frictions FTMO et calendrier des pauses (étape 1, sans recalcul)
    cc = pd.read_csv(HERE / "couts_trades_D05_1.csv.gz", parse_dates=["entree"])
    cc = cc[(cc.calendrier == "ftmo") & cc.cle.isin(CRYPTO)]
    cc["net_atr"] = (cc.brut_bps - cc.total) / cc.atr_bps
    ny_d05 = (D04.ts(F.B) - D04.ts(F.A)) / pd.Timedelta(days=365.25)
    btc = cc[cc.cle == "BTC"]
    anat.append({"cle": "BTC (repère)", "fenetre": f"{F.A} → {F.B}", "brut_moyen_atr": float((btc.brut_bps / btc.atr_bps).mean()),
                 **anatomie(btc.net_atr.to_numpy(), ny_d05, btc.sens.to_numpy())})
    anat.append({"cle": "Panier crypto (repère)", "fenetre": f"{F.A} → {F.B}",
                 "brut_moyen_atr": float((cc.brut_bps / cc.atr_bps).mean()),
                 **anatomie(cc.net_atr.to_numpy(), ny_d05, cc.sens.to_numpy())})
    panier = pd.Series(cc.net_atr.to_numpy() * RISQUE / len(CRYPTO),
                       index=pd.DatetimeIndex(cc.entree).tz_convert(None).to_period("M")).groupby(level=0).sum()
    mois = pd.period_range(F.A, "2026-09", freq="M")
    panier = panier.reindex(mois, fill_value=0.0)
    cor = []
    for key, s in mensuel.items():
        s = s.reindex(mois, fill_value=0.0)
        neg = panier < 0
        cor.append({"cle": key, "mois": len(mois), "correlation_mensuelle_panier": float(s.corr(panier)),
                    "net_mois_panier_negatif_pc": float(100 * s[neg].sum()), "mois_panier_negatif": int(neg.sum()),
                    "net_mois_panier_positif_pc": float(100 * s[~neg].sum()),
                    "part_mois_positifs_quand_panier_negatif": float((s[neg] > 0).mean()) if neg.any() else np.nan})
    pd.DataFrame(lignes).to_csv(HERE / "profil_tradfi_D05_1.csv", index=False, float_format="%.6g")
    pd.DataFrame(anat).to_csv(HERE / "anatomie_tradfi_D05_1.csv", index=False, float_format="%.6g")
    pd.DataFrame(ann).to_csv(HERE / "annees_tradfi_D05_1.csv", index=False, float_format="%.6g")
    pd.DataFrame(cor).to_csv(HERE / "correlations_tradfi_D05_1.csv", index=False, float_format="%.6g")
    pd.concat(trades_out, ignore_index=True).to_csv(HERE / "trades_tradfi_D05_1.csv.gz", index=False, float_format="%.6g")
    ctrl = {"date": pd.Timestamp.now(tz="UTC").strftime("%Y-%m-%d %H:%M UTC"), "commit": D04.git_head(), "motif": MOTIF,
            "duree_s": round(time.time() - t0)}
    (HERE / "controles_profil_D05_1.json").write_text(json.dumps(D01.jsonable(ctrl), ensure_ascii=False, indent=1),
                                                      encoding="utf-8")
    print(f"profil TradFi : fait en {ctrl['duree_s']} s")


if __name__ == "__main__":
    main()
