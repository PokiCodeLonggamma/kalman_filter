"""Tests unitaires zones / segments / signaux one-shot / exécution (séquence synthétique contrôlée)."""
import numpy as np
import pandas as pd
import pytest

from indicator.segments import SignalParams, execute, trades, zones_and_signals

NAN = np.nan
# idx 0-2 NaN | 3-9 vert(7) | 10-11 neutre | 12-14 rouge(3) | 15 neutre | 16-21 rouge(6) | 22-23 neutre
# | 24-29 vert(6) | 30-35 rouge(6, saut direct) | 36-38 neutre
TS = np.array([NAN] * 3 + [70] * 7 + [0] * 2 + [-50] * 3 + [0] + [-70] * 6 + [10] * 2 + [70] * 6 + [-70] * 6 + [0] * 3,
              dtype=float)


@pytest.fixture
def sig():
    return zones_and_signals(TS)


def test_zone_nan_tant_que_ts_indefini(sig):
    assert np.isnan(sig.zone[:3]).all() and sig.zone.iat[3] == 1


def test_signaux_one_shot(sig):
    assert np.flatnonzero(sig.short_signal).tolist() == [10]          # pas 11 : seg_len == 1 seulement
    assert np.flatnonzero(sig.long_signal).tolist() == [22, 36]       # 15 rejeté (rouge de 3 barres) ; saut 29->30 sans signal


def test_archivage_prev_seg(sig):
    assert (sig.prev_seg_zone.iat[22], sig.prev_seg_len.iat[22], sig.prev_seg_extreme_abs.iat[22]) == (-1, 6, 70.0)
    assert sig.prev_seg_zone.iat[23] == -1 and sig.seg_len.iat[23] == 2     # figé pendant le neutre


def test_filtre_de_force():
    weak = TS.copy(); weak[3:10] = 55
    assert not zones_and_signals(weak).short_signal.any()
    assert zones_and_signals(weak, SignalParams(use_strength_cond=False)).short_signal.iat[10]


def test_execution_close_pyramiding_0(sig):
    n = len(TS)
    px = np.arange(n, dtype=float) + 100
    ex = execute(sig.long_signal, sig.short_signal, px - 0.5, px, fill_price="close")
    assert np.flatnonzero(ex.decision).tolist() == [10, 22] and np.flatnonzero(ex.ignored).tolist() == [36]
    assert ex.fill_px.iat[10] == px[10] and ex.position.iat[10] == -1 and ex.position.iat[22] == 1


def test_execution_open_next(sig):
    n = len(TS)
    px = np.arange(n, dtype=float) + 100
    op = px - 0.5
    ex = execute(sig.long_signal, sig.short_signal, op, px, fill_price="open_next")
    assert np.flatnonzero(ex.decision).tolist() == [10, 22]
    assert np.flatnonzero(ex.fill).tolist() == [11, 23] and ex.fill_px.iat[11] == op[11]
    assert ex.position.iat[10] == 0 and ex.position.iat[11] == -1 and ex.position.iat[22] == -1 and ex.position.iat[23] == 1
    t = trades(ex)
    assert t.side.tolist() == [-1, 1] and t.exit_bar.iat[0] == 23 and np.isnan(t.exit_px.iat[1])


def test_decision_derniere_barre_non_remplie():
    L = np.zeros(5, bool); L[-1] = True
    ex = execute(L, np.zeros(5, bool), np.ones(5), np.ones(5), fill_price="open_next")
    assert ex.decision.iat[-1] and not ex.fill.any() and ex.position.iat[-1] == 0


def test_warmup_supprime_les_decisions(sig):
    n = len(TS)
    ex = execute(sig.long_signal, sig.short_signal, np.ones(n), np.ones(n), fill_price="close", warmup_bars=15)
    assert np.flatnonzero(ex.decision).tolist() == [22] and np.flatnonzero(ex.ignored).tolist() == [36]


def test_fill_price_invalide(sig):
    with pytest.raises(ValueError):
        execute(sig.long_signal, sig.short_signal, np.ones(len(TS)), np.ones(len(TS)), fill_price="vwap")


def test_zone_seuils_stricts():
    z = zones_and_signals(np.array([30.0, -30.0, 30.0 + 1e-9, -30.0 - 1e-9])).zone.to_numpy()
    assert z.tolist() == [0, 0, 1, -1]


def test_frontieres_min_bars_et_force_inclusives():
    """prev_seg_len >= 6 et prev_seg_extreme_abs >= 60 : bornes incluses (Pine l. 245-246)."""
    s = zones_and_signals(np.array([-60.0] * 6 + [0.0] + [60.0] * 6 + [0.0]))
    assert np.flatnonzero(s.long_signal).tolist() == [6] and np.flatnonzero(s.short_signal).tolist() == [13]


def test_extreme_du_segment_max_courant():
    s = zones_and_signals(np.array([-40.0, -50.0, -65.0, -40.0, -40.0, -40.0, 0.0]))
    assert s.seg_extreme_abs.tolist()[:6] == [40, 50, 65, 65, 65, 65]
    assert s.long_signal.iat[6] and s.prev_seg_extreme_abs.iat[6] == 65


def test_warmup_frontiere_exacte():
    L = np.zeros(10, bool); S = np.zeros(10, bool); S[4] = True; L[5] = True
    ex = execute(L, S, np.ones(10), np.ones(10), fill_price="close", warmup_bars=5)
    assert np.flatnonzero(ex.decision).tolist() == [5] and ex.position.iat[4] == 0


def test_trades_prix_d_entree_et_de_sortie():
    L = np.zeros(6, bool); S = np.zeros(6, bool); S[1] = True; L[3] = True
    op = np.array([10., 11., 12., 13., 14., 15.])
    t = trades(execute(L, S, op, op + 0.5, fill_price="open_next"))
    assert t.entry_bar.tolist() == [2, 4] and t.entry_px.tolist() == [12.0, 14.0]
    assert t.exit_bar.iat[0] == 4 and t.exit_px.iat[0] == 14.0 and pd.isna(t.exit_bar.iat[1])
    assert str(t.exit_bar.dtype) == "Int64" and t.attrs["pending_side"] == 0


def test_trades_ordre_en_attente_derniere_barre():
    L = np.zeros(5, bool); L[-1] = True
    t = trades(execute(L, np.zeros(5, bool), np.ones(5), np.ones(5), fill_price="open_next"))
    assert len(t) == 0 and t.attrs["pending_side"] == 1


def test_execute_longueurs_et_warmup_invalides():
    with pytest.raises(ValueError):
        execute(np.zeros(5, bool), np.zeros(4, bool), np.ones(5), np.ones(5))
    with pytest.raises(ValueError):
        execute(np.zeros(5, bool), np.zeros(5, bool), np.ones(5), np.ones(5), warmup_bars=-1)


@pytest.mark.parametrize("bad", [dict(up_th=-1.0), dict(down_th=1.0), dict(min_trend_bars=0), dict(min_trend_bars=6.5),
                                 dict(min_trend_strength=101.0)])
def test_parametres_signal_hors_bornes(bad):
    with pytest.raises(ValueError):
        SignalParams(**bad)
