"""EXP-D01.6 — `envelope.decouple` : verrouillage distinct de l'horizon de sortie, sortie forcée en fin de séance.
Non-régression (verrouillage = horizon et série continue redonnent `stop_trades(..., dynamic=False)`), règles de
sortie et de verrouillage, aucune nuit détenue, causalité par troncature, absence de lookahead."""
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from config import ROOT
from envelope import atr_stop_levels, stop_trades, structural_stop_levels
from envelope.decouple import lock_trades, session_close_trades, session_last_bar

T0 = pd.Timestamp("2021-01-01", tz="UTC")


def _bars(o, t0=T0):
    o = np.asarray(o, float)
    return pd.DataFrame({"time": t0 + pd.to_timedelta(np.arange(len(o)) * 30, unit="min"), "open": o,
                         "high": o + 0.5, "low": o - 0.5, "close": o})


def _marche(n, seed):
    return _bars(100 * np.exp(np.cumsum(np.random.default_rng(seed).normal(0, 0.01, n))))


def _seances(n_jours, seed, par_jour=13):
    """Séances de `par_jour` barres de 30 min (14:30-21:00 UTC), jours ouvrés, marche aléatoire avec écarts de nuit."""
    rng = np.random.default_rng(seed)
    jours = pd.bdate_range("2024-01-02", periods=n_jours, tz="UTC")
    time = np.concatenate([(j + pd.Timedelta(hours=14, minutes=30)
                            + pd.to_timedelta(np.arange(par_jour) * 30, unit="min")).to_numpy() for j in jours])
    ret = rng.normal(0, 0.004, n_jours * par_jour)
    ret[::par_jour] += rng.normal(0, 0.01, n_jours)                   # écart d'ouverture
    c = 100 * np.exp(np.cumsum(ret))
    o = np.r_[100.0, c[:-1]] * np.exp(np.where(np.arange(len(c)) % par_jour == 0, rng.normal(0, 0.01, len(c)), 0.0))
    hi = np.maximum(o, c) + 0.1
    lo = np.minimum(o, c) - 0.1
    return pd.DataFrame({"time": pd.to_datetime(time, utc=True), "open": o, "high": hi, "low": lo, "close": c})


def _signaux(n, k, seed, lo=60):
    rng = np.random.default_rng(seed)
    t = np.sort(rng.choice(np.arange(lo, n - 2), k, replace=False))
    return t, rng.choice([-1, 1], k), rng.uniform(0.5, 2.0, k), rng.integers(1, 40, k)


# ── Verrouillage distinct de l'horizon ──────────────────────────────────────────
def test_verrouillage_egal_a_l_horizon_redonne_stop_trades_fige():
    b = _marche(4000, 41)
    t, s, a, n = _signaux(4000, 600, 42)
    lvl = structural_stop_levels(b, t, s, a * 0.3, n, 0.0)
    lvl[::2] = np.nan                                                 # moitié sans stop
    for h in (6, 26):
        ref = stop_trades(b, t, s, h, lvl, dynamic=False)
        assert ref.stop.any()
        pd.testing.assert_frame_equal(lock_trades(b, t, s, h, h, lvl), ref)


def test_verrouillage_long_espace_les_entrees_sans_changer_la_sortie():
    b = _marche(4000, 43)
    t, s, a, _ = _signaux(4000, 600, 44)
    o = b.open.to_numpy()
    for lock in (48, 90):
        tr = lock_trades(b, t, s, 26, lock, None)
        e, x = tr.entry_bar.to_numpy(), tr.exit_bar.to_numpy()
        assert (np.diff(tr.signal_bar.to_numpy()) >= lock).all()
        assert (x[x < len(b) - 1] - e[x < len(b) - 1] == 26).all()   # sortie à 26 barres (hors fin de série)
        np.testing.assert_allclose(tr.ret_gross_bps, tr.side * (o[x] / o[e] - 1.0) * 1e4)
    b2 = _bars(np.full(40, 100.0))
    tr = lock_trades(b2, [2, 5, 9, 12, 20], [1, 1, 1, 1, 1], horizon=4, lock=10)
    assert tr.signal_bar.tolist() == [2, 12]                          # 5, 9 : verrouillés ; 20 < 12 + 10


def test_verrouillage_plus_court_que_l_horizon_refuse():
    b = _marche(200, 45)
    with pytest.raises(ValueError):
        lock_trades(b, [10, 20], [1, 1], horizon=26, lock=13)
    with pytest.raises(ValueError):
        session_close_trades(b, [10, 20], [1, 1], horizon=26, release="jour")


# ── Sortie forcée en fin de séance ──────────────────────────────────────────────
def test_serie_continue_redonne_stop_trades_fige():
    b = _marche(4000, 46)
    t, s, a, _ = _signaux(4000, 500, 47)
    lvl = atr_stop_levels(b, t, s, a, 1.5)
    for h in (6, 26):
        got = session_close_trades(b, t, s, h, lvl, release="lock")
        assert not got.session_exit.any()
        pd.testing.assert_frame_equal(got.drop(columns="session_exit"), stop_trades(b, t, s, h, lvl, dynamic=False))


def test_derniere_barre_de_seance():
    b = _seances(3, 48)
    np.testing.assert_array_equal(session_last_bar(b), np.repeat([12, 25, 38], 13))


def test_sortie_au_close_de_la_derniere_barre_avant_l_ecart_de_nuit():
    b = _seances(3, 49)
    b[["open", "high", "low", "close"]] = 100.0
    b["high"], b["low"] = 100.5, 99.5
    b.loc[12, ["close", "high"]] = [101.0, 101.5]                     # clôture de la séance 1
    b.loc[13, ["open", "high", "low", "close"]] = [110.0, 110.5, 109.5, 110.0]   # écart de nuit : jamais encaissé
    tr = session_close_trades(b, [2], [1], horizon=26)
    assert tr[["entry_bar", "exit_bar", "stop", "gap", "session_exit"]].values.tolist() == [[3, 13, False, False, True]]
    np.testing.assert_allclose(tr.exit_price, [101.0])
    np.testing.assert_allclose(tr.ret_gross_bps, [100.0])
    b.loc[6, "low"] = 98.9                                            # stop à 99 touché dans la séance
    tr = session_close_trades(b, [2], [1], horizon=26, level=[99.0])
    assert tr[["exit_bar", "stop", "session_exit"]].values.tolist() == [[6, True, False]]
    np.testing.assert_allclose(tr.ret_gross_bps, [-100.0])
    tr = session_close_trades(b, [2], [1], horizon=4)                # sortie prévue dans la séance : inchangée
    assert tr[["exit_bar", "session_exit"]].values.tolist() == [[7, False]]


def test_liberation_a_la_cloture_contre_entrees_de_re1():
    b = _seances(3, 50)
    t, s = [2, 12, 15, 30], [1, -1, 1, 1]
    fig = session_close_trades(b, t, s, horizon=26, release="lock")
    assert fig.signal_bar.tolist() == [2, 30]                         # verrouillé jusqu'à t + 26 = 28 : entrées de RE-1
    assert fig.signal_bar.tolist() == stop_trades(b, t, s, 26, None, dynamic=False).signal_bar.tolist()
    lib = session_close_trades(b, t, s, horizon=26, release="session")
    assert lib.signal_bar.tolist() == [2, 12, 30]                     # libéré à la clôture (barre 12) ; 15 < 25
    assert lib[["entry_bar", "exit_bar", "session_exit"]].values.tolist() == [[3, 13, True], [13, 26, True],
                                                                               [31, 38, False]]
    np.testing.assert_allclose(lib.exit_price.iloc[:2], b.close.iloc[[12, 25]])


def test_aucune_nuit_detenue_et_causalite_par_troncature():
    b = _seances(120, 51)
    t, s, a, n = _signaux(len(b), 400, 52, lo=45)
    lvl = structural_stop_levels(b, t, s, np.full(len(t), 0.4), n, 0.0)
    end = session_last_bar(b)
    for rel in ("lock", "session"):
        tr = session_close_trades(b, t, s, 26, lvl, release=rel)
        e, x = tr.entry_bar.to_numpy(), tr.exit_bar.to_numpy()
        se, st = tr.session_exit.to_numpy(bool), tr.stop.to_numpy(bool)
        assert se.any() and st.any()
        assert (x[se] - 1 == end[e[se]]).all() and (x[st] <= end[e[st]]).all() and (x[~se & ~st] <= end[e[~se & ~st]]).all()
        cut = 900
        tc = session_close_trades(b.iloc[:cut].reset_index(drop=True), t[t < cut], s[t < cut], 26, lvl[t < cut],
                                  release=rel)
        early = tr[tr.exit_bar < cut - 30].reset_index(drop=True)
        assert len(early) > 20
        pd.testing.assert_frame_equal(tc.iloc[:len(early)].reset_index(drop=True), early)
    tl = lock_trades(b, t, s, 26, 65, lvl)
    tlc = lock_trades(b.iloc[:900].reset_index(drop=True), t[t < 900], s[t < 900], 26, 65, lvl[t < 900])
    early = tl[tl.exit_bar < 870].reset_index(drop=True)
    pd.testing.assert_frame_equal(tlc.iloc[:len(early)].reset_index(drop=True), early)


def test_aucun_decalage_vers_le_futur():
    assert "shift(-" not in Path(ROOT / "src" / "envelope" / "decouple.py").read_text(encoding="utf-8")
