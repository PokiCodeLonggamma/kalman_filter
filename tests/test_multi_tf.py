"""Multi-TF 1 h (D32) : agrégation, ancrage, jonction causale, warm-up en bougies 1 h clôturées."""
import numpy as np
import pandas as pd
import pytest

from config import WARMUP_BARS_1H
from features import aggregate_1h, build_features, features_1h
from indicator import run_kalman


def _bars(times, level=100.0, step=1.0):
    t = pd.DatetimeIndex(times)
    c = level + step * np.arange(len(t), dtype=float)
    return pd.DataFrame({"time": t, "open": c - 0.5, "high": c + 1, "low": c - 1, "close": c})


def _btc_like(n=1400):
    c = 30000 + 500 * np.sin(2 * np.pi * np.arange(n) / 37)
    return pd.DataFrame({"time": pd.date_range("2024-01-01", periods=n, freq="30min", tz="UTC"),
                         "open": np.r_[c[0], c[:-1]], "high": c + 1, "low": c - 1, "close": c})


def _rth(days=4, start="2024-03-04"):
    """Séances actions US : 13 barres de 30 min, 09:30 -> 16:00 America/New_York (dernière barre 15:30)."""
    rows, sid = [], []
    for d in pd.bdate_range(start, periods=days, tz="America/New_York"):
        t = pd.date_range(d.normalize() + pd.Timedelta(hours=9, minutes=30), periods=13, freq="30min")
        rows.append(t)
        sid += [d.date().isoformat()] * len(t)
    times = pd.DatetimeIndex(np.concatenate(rows)).tz_convert("UTC")
    return _bars(times), np.array(sid)


# ── Agrégation ──────────────────────────────────────────────────────────────────
def test_aggregate_1h_horloge_utc():
    df = _btc_like(n=8)
    h = aggregate_1h(df)
    assert len(h) == 4 and (h.n_bars == 2).all()
    assert (h.close_time_1h == h.time + pd.Timedelta(hours=1)).all()
    assert h.open.iat[0] == df.open.iat[0] and h.close.iat[0] == df.close.iat[1]
    assert h.high.iat[0] == df.high.iloc[:2].max() and h.low.iat[0] == df.low.iloc[:2].min()


def test_aggregate_1h_heure_incomplete_garde_la_cloture_nominale():
    """Une barre 30 min manquante ne rend pas la bougie 1 h disponible plus tôt."""
    df = _btc_like(n=8).drop(index=3).reset_index(drop=True)          # barre 01:30 absente
    h = aggregate_1h(df)
    incomplete = h[h.n_bars == 1].iloc[0]
    assert incomplete.close_time_1h == incomplete.time + pd.Timedelta(hours=1)


def test_aggregate_1h_ancrage_seance():
    df, sid = _rth(days=2)
    h = aggregate_1h(df, anchor="session", session_id=sid)
    assert len(h) == 14                                                # 7 bougies par séance de 13 barres
    per_day = h.groupby(h.time.dt.tz_convert("America/New_York").dt.date).size()
    assert set(per_day) == {7}
    ny = h.time.dt.tz_convert("America/New_York")
    assert (ny.dt.strftime("%H:%M").unique() == np.array(["09:30", "10:30", "11:30", "12:30", "13:30",
                                                          "14:30", "15:30"])).all()
    fin = h.close_time_1h.dt.tz_convert("America/New_York")
    assert (fin.dt.strftime("%H:%M") <= "16:00").all()                 # aucune bougie ne dépasse la séance
    assert h.n_bars.iloc[6] == 1 and fin.iloc[6].strftime("%H:%M") == "16:00"


def test_ancrage_seance_exige_session_id():
    df, _ = _rth(days=1)
    with pytest.raises(ValueError):
        aggregate_1h(df, anchor="session")
    with pytest.raises(ValueError):
        aggregate_1h(df, anchor="inconnu")


def test_ancrage_horloge_serait_faux_sur_une_seance_a_930():
    """floor('1h') coupe la séance en groupes décalés, dont un premier à une seule barre : motif de D32."""
    df, sid = _rth(days=1)
    horloge = aggregate_1h(df, anchor="utc_hour")
    seance = aggregate_1h(df, anchor="session", session_id=sid)
    assert horloge.n_bars.iat[0] == 1 and len(horloge) == 7
    assert horloge.time.iat[0] != seance.time.iat[0]


# ── Jonction causale ────────────────────────────────────────────────────────────
def test_jonction_utilise_la_derniere_bougie_entierement_close():
    df = _btc_like(n=200)
    f = features_1h(df, warmup_bars_1h=0)
    h = aggregate_1h(df)
    connue = f.close_time_1h.notna().to_numpy()
    assert (f.close_time_1h[connue] <= f.close_time[connue]).all()      # jamais une bougie en cours
    assert not connue[0]                                                # aucune bougie close au 1er close 30 min
    for i in [10, 51, 100, 151]:
        close_t = df.time.iat[i] + pd.Timedelta(minutes=30)
        dispo = h[h.close_time_1h <= close_t]
        assert f.close_time_1h.iat[i] == dispo.close_time_1h.iat[-1]
        assert f.n_1h_closed.iat[i] == len(dispo)
    minute = df.time.dt.minute.to_numpy()
    ecart = (f.close_time - f.close_time_1h).to_numpy()
    assert (ecart[connue & (minute == 0)] == pd.Timedelta(minutes=30)).all()   # :00 -> bougie close à l'heure
    assert (ecart[connue & (minute == 30)] == pd.Timedelta(0)).all()           # :30 -> clôture simultanée


def test_x1_1h_identique_au_kalman_sur_les_bougies_closes():
    df = _btc_like(n=300)
    f = features_1h(df, warmup_bars_1h=0)
    h = aggregate_1h(df)
    x1 = run_kalman(h.close.to_numpy()).x1.to_numpy()
    for i in [20, 77, 150, 299]:
        k = int(f.n_1h_closed.iat[i])
        assert f.x1_1h.iat[i] == pytest.approx(x1[k - 1])               # état de la dernière bougie close
        # et strictement causal : recalculer sur les seules bougies closes donne la même valeur
        assert run_kalman(h.close.to_numpy()[:k]).x1.iat[-1] == pytest.approx(x1[k - 1])


def test_valid_1h_compte_les_bougies_closes():
    df = _btc_like(n=1400)
    f = features_1h(df, warmup_bars_1h=300)
    attendu = np.r_[0, np.repeat(np.arange(1, len(f)), 2)][:len(f)]     # 1 bougie close toutes les 2 barres
    assert (f.n_1h_closed.to_numpy() == attendu).all()
    premiere = int(np.flatnonzero(f.valid_1h.to_numpy())[0])
    assert f.n_1h_closed.iat[premiere] == 300 and premiere == 2 * 300 - 1
    assert not f.valid_1h.iloc[:premiere].any()


def test_warmup_1h_en_bougies_et_non_en_barres_30min():
    """Sur une séance de 13 barres (7 bougies 1 h), 600 barres 30 min ne valent pas 300 bougies 1 h :
    le warm-up doit compter les bougies closes, pas les barres (D32)."""
    df, sid = _rth(days=60)
    f = features_1h(df, anchor="session", session_id=sid, warmup_bars_1h=WARMUP_BARS_1H)
    assert f.n_1h_closed.iat[599] == 323 != WARMUP_BARS_1H
    premiere = int(np.flatnonzero(f.valid_1h.to_numpy())[0])
    assert f.n_1h_closed.iat[premiere] == WARMUP_BARS_1H and premiere != 2 * WARMUP_BARS_1H - 1


@pytest.mark.data
def test_sur_btc_300_bougies_1h_valent_600_barres_30min(features_full):
    f = features_full
    premiere = int(np.flatnonzero(f.valid_1h.to_numpy())[0])
    assert premiere == 2 * WARMUP_BARS_1H - 1
    assert f.n_1h_closed.iat[premiere] == WARMUP_BARS_1H


@pytest.mark.data
def test_x1_1h_bps_sans_dimension(features_full):
    f = features_full[features_full.valid_features]
    assert np.isfinite(f.x1_1h_bps.to_numpy()).all()
    assert np.array_equal(np.sign(f.x1_1h_bps.to_numpy()), f.sign_x1_1h.to_numpy())


def test_features_1h_refuse_un_warmup_negatif():
    with pytest.raises(ValueError):
        features_1h(_btc_like(n=10), warmup_bars_1h=-1)


def test_build_features_accepte_l_ancrage_seance():
    df, sid = _rth(days=40)
    f = build_features(df, warmup_bars=50, warmup_bars_1h=20, anchor_1h="session", session_id=sid,
                       asset="TEST")
    connue = f.close_time_1h.notna().to_numpy()
    assert f.valid_features.any() and (f.close_time_1h[connue] <= f.close_time[connue]).all()
    assert f.asset.iat[0] == "TEST"
