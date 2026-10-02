"""EXP-D02 — statistiques de comparaison de deux séries hors échantillon (`optimization.compare`) : grappes = mois civils
de la période commune (mois vides compris), mêmes tirages pour les deux séries et générateur des IC du dépôt ; écarts
d'espérance (ATR, bps) et de rendement annualisé avec IC 95 % ; chemins réordonnés (MDD aux sorties, Calmar) ; entrées
figées pour lire un changement d'horizon (I-M16)."""
import numpy as np
import pandas as pd
import pytest

from envelope import effect_ci, stop_trades, summarize_sized
from envelope.metrics import _cluster_counts
from optimization.compare import (drop_best, frozen_entries, month_draws, month_index, mdd_exits,
                                  paired_comparison, series_stats)

UTC = "UTC"


def _cas(barres_synthetiques, signaux_synthetiques, seed=0, h=26):
    bars = barres_synthetiques(9000, seed=seed)                # 2021-01-01 → mi-juillet 2021
    t, s, level = signaux_synthetiques(bars, 900, seed=seed + 1)
    tr = stop_trades(bars, t, s, h, level, dynamic=False)
    atr = np.random.default_rng(seed).uniform(15.0, 90.0, len(bars))
    return bars, tr, atr, t, s, level


START, END = pd.Timestamp("2021-01-01", tz=UTC), pd.Timestamp("2021-08-01", tz=UTC)


def test_mois_civils_de_la_periode_commune():
    t = pd.Series(pd.to_datetime(["2021-01-05 00:00", "2021-03-31 23:30", "2021-07-01 00:00"], utc=True))
    idx, g = month_index(t, START, END)
    assert g == 7 and idx.tolist() == [0, 2, 6]
    with pytest.raises(ValueError, match="hors de la période"):
        month_index(pd.Series(pd.to_datetime(["2021-08-01"], utc=True)), START, END)


def test_tirages_identiques_a_ceux_des_ic_du_depot():
    w, _, g = _cluster_counts(np.arange(40), 300, 0)
    d = month_draws(40, 300, 0)
    assert g == 40 and d.shape == (300, 40)
    assert np.array_equal(np.array([np.bincount(x, minlength=40) for x in d], dtype=float), w)


def test_une_serie_contre_elle_meme(barres_synthetiques, signaux_synthetiques):
    bars, tr, atr, *_ = _cas(barres_synthetiques, signaux_synthetiques)
    a = series_stats(tr, bars, atr, 5.0, START, END)
    c = paired_comparison(a, a, n_boot=300)
    for k in ("d_esperance_atr", "d_esperance_bps", "d_rendement_annuel", "d_mdd_sorties", "d_calmar_sorties"):
        assert c[k] == 0.0 and c[f"{k}_lo"] == 0.0 and c[f"{k}_hi"] == 0.0, k
    assert c["part_mdd_meilleur"] == 0.0 and c["part_calmar_meilleur"] == 0.0
    assert not c["esperance_tangible"] and not c["rendement_tangible"]


def test_decalage_constant_de_l_esperance(barres_synthetiques, signaux_synthetiques):
    bars, tr, atr, *_ = _cas(barres_synthetiques, signaux_synthetiques, seed=1)
    b = series_stats(tr, bars, atr, 5.0, START, END)
    a = series_stats(tr, bars, atr, 4.0, START, END)          # 1 bp de frais en moins sur chaque trade
    c = paired_comparison(a, b, n_boot=300)
    shift = float(np.mean(1.0 / atr[tr.signal_bar.to_numpy()]))
    assert np.isclose(c["d_esperance_bps"], 1.0) and np.isclose(c["d_esperance_bps_lo"], 1.0)
    assert np.isclose(c["d_esperance_atr"], shift) and c["d_esperance_atr_lo"] > 0
    assert c["esperance_tangible"] and c["rendement_tangible"] and c["part_calmar_meilleur"] > 0.99


def test_chemin_reel_egal_aux_fonctions_du_depot(barres_synthetiques, signaux_synthetiques):
    bars, tr, atr, *_ = _cas(barres_synthetiques, signaux_synthetiques, seed=2)
    a = series_stats(tr, bars, atr, 5.0, START, END)
    atr_s = pd.Series(atr, index=np.arange(len(bars)))
    sized = summarize_sized(tr, bars, atr_s, 5.0, 25.0)
    assert mdd_exits(a.r) == sized["mdd_sorties"]
    assert np.isclose(np.expm1(np.log1p(a.r).sum()), sized["pnl_compose"], rtol=1e-12)
    empty = series_stats(tr.iloc[:0], bars, atr, 5.0, START, END)
    c = paired_comparison(a, empty, n_boot=200)
    assert np.isnan(c["d_esperance_atr"]) and c["n_b"] == 0


def test_entrees_figees_pour_lire_un_changement_d_horizon(barres_synthetiques, signaux_synthetiques):
    bars, tr, atr, t, s, level = _cas(barres_synthetiques, signaux_synthetiques, seed=3)
    lv = pd.Series(level, index=t).reindex(tr.signal_bar.to_numpy()).to_numpy()
    same = frozen_entries(bars, tr, 26, lv)
    assert same.equals(tr)                                    # même horizon : mêmes trades
    longer = frozen_entries(bars, tr, np.full(len(tr), 40), lv)
    assert np.array_equal(longer.entry_bar, tr.entry_bar) and (longer.exit_bar >= tr.exit_bar).all()
    eff = effect_ci(longer, tr, bars, pd.Series(atr, index=np.arange(len(bars))), n_boot=200)
    assert np.isfinite(eff["effet_atr"]) and eff["effet_atr_lo"] <= eff["effet_atr"] <= eff["effet_atr_hi"]


def test_retrait_des_meilleurs_trades_stress_du_porteur(barres_synthetiques, signaux_synthetiques):
    """EXP-D02.1 : la série sans son 1 % de meilleurs trades (⌈1 % · n⌉, au moins un), classés par rendement net en
    ATR14(t) ; ordre chronologique gardé."""
    bars, tr, atr, *_ = _cas(barres_synthetiques, signaux_synthetiques, seed=21)
    net = (tr.ret_gross_bps.to_numpy() - 5.0) / atr[tr.signal_bar.to_numpy()]
    k = int(np.ceil(0.01 * len(tr)))
    assert len(tr) > 150 and k >= 2
    got = drop_best(tr, atr, 5.0)
    best = np.argsort(-net, kind="stable")[:k]
    assert got.equals(tr.drop(index=best).reset_index(drop=True))
    assert np.argmax(net) in best and np.argmax(tr.ret_gross_bps.to_numpy()) != np.argmax(net)  # rang en ATR
    assert len(drop_best(tr.iloc[:50], atr, 5.0)) == 49 and len(drop_best(tr.iloc[:200], atr, 5.0)) == 198
    assert drop_best(tr.iloc[:0], atr, 5.0).empty
