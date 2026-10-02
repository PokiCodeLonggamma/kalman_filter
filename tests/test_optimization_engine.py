"""EXP-D02 — noyau Numba (`optimization.engine`) : identique à `envelope.stop_trades` (`dynamic=False`), horizon et
niveau de stop par signal, borne de fin (dernière barre d'un IS), contrôles d'entrée."""
import numpy as np
import pandas as pd
import pytest

from envelope import stop_distance, stop_trades
from envelope.decouple import lock_trades
from envelope.stops import _sequential
from estimand.stoploss import TRADE_COLUMNS, apply_stop
from optimization.compare import frozen_entries
from optimization.engine import run_trades, superseded


def _reference_par_signal(bars, t, s, h, level, last):
    """Référence Python indépendante : `apply_stop` et `_sequential` du dépôt, sortie à min(t + 1 + h, last) par
    signal, position libérée à la barre x − 1 (cooldown jusqu'à la sortie prévue)."""
    t, s, h, level = (np.asarray(v) for v in (t, s, h, level))
    ok = t + 1 < last
    t, s, h, level = t[ok], s[ok], h[ok], level[ok]
    e, x = t + 1, np.minimum(t + 1 + h, last)
    with np.errstate(invalid="ignore"):
        out = apply_stop(bars, e, x, s, stop_distance(bars, t, s, level))
    keep = _sequential(t, x - 1)
    res = out.iloc[keep].reset_index(drop=True)
    res["signal_bar"] = t[keep]
    return res[TRADE_COLUMNS]


def test_noyau_identique_a_stop_trades_a_horizon_commun(barres_synthetiques, signaux_synthetiques):
    bars = barres_synthetiques(1500)
    t, s, level = signaux_synthetiques(bars, 250)
    stops = gaps = 0
    for h in (1, 3, 26, 60):
        for lv in (None, level):
            ref = stop_trades(bars, t, s, h, lv, dynamic=False)
            got = run_trades(bars, t, s, h, lv)
            assert got.equals(ref), (h, lv is None)
            stops, gaps = stops + int(ref.stop.sum()), gaps + int(ref.gap.sum())
    assert stops > 20 and gaps > 0                            # le jeu exerce bien stops et gaps


def test_noyau_horizon_par_signal_egal_a_la_reference(barres_synthetiques, signaux_synthetiques):
    bars = barres_synthetiques(1500, seed=3)
    t, s, level = signaux_synthetiques(bars, 250, seed=4)
    h = np.random.default_rng(5).integers(1, 50, len(t))
    got = run_trades(bars, t, s, h, level)
    assert got.equals(_reference_par_signal(bars, t, s, h, level, len(bars) - 1))
    assert len(np.unique(got.exit_bar - got.entry_bar)) > 10   # horizons réellement différents


def test_noyau_borne_de_fin_equivaut_a_couper_les_barres(barres_synthetiques, signaux_synthetiques):
    """Fin d'IS : un trade ouvert est clos à l'ouverture de la barre `last` ; aucune barre au-delà n'est lue."""
    bars = barres_synthetiques(1200, seed=6)
    t, s, level = signaux_synthetiques(bars, 200, seed=7)
    last = 700
    got = run_trades(bars, t, s, 26, level, last=last)
    sel = t <= last
    ref = stop_trades(bars.iloc[:last + 1].reset_index(drop=True), t[sel], s[sel], 26, level[sel], dynamic=False)
    assert got.equals(ref) and (got.exit_bar <= last).all()
    altered = bars.copy()
    altered.loc[last + 1:, ["open", "high", "low", "close"]] *= 1.5
    assert run_trades(altered, t, s, 26, level, last=last).equals(got)


def test_noyau_refuse_les_entrees_invalides(barres_synthetiques, signaux_synthetiques):
    bars = barres_synthetiques(400)
    t, s, level = signaux_synthetiques(bars, 40)
    with pytest.raises(ValueError, match="triés"):
        run_trades(bars, t[::-1], s[::-1], 26, level[::-1])
    with pytest.raises(ValueError, match="horizon"):
        run_trades(bars, t, s, 0, level)
    bad = level.copy()
    i = int(np.flatnonzero(~np.isnan(level))[0])
    bad[i] = bars.open.to_numpy()[t[i] + 1] * (1.0 + s[i] * 0.01)   # niveau du mauvais côté
    with pytest.raises(ValueError, match="mauvais côté"):
        run_trades(bars, t, s, 26, bad)
    with pytest.raises(ValueError, match="last"):
        run_trades(bars, t, s, 26, level, last=len(bars))
    late = bars.copy()
    late["time"] = pd.date_range("2025-12-31 20:00", periods=len(bars), freq="30min", tz="UTC")
    with pytest.raises(ValueError, match="réserve 2026"):
        run_trades(late, t, s, 26, level)


def test_noyau_sans_candidat_rend_le_cadre_vide_de_stop_trades(barres_synthetiques):
    bars = barres_synthetiques(300)
    t, s = np.array([len(bars) - 2]), np.array([1])
    got = run_trades(bars, t, s, 26)
    assert got.empty and got.equals(stop_trades(bars, t, s, 26, None, dynamic=False))


# ── EXP-D02.1 : verrou (cooldown) distinct de l'horizon de sortie, option C du porteur ─────────────────────────────

def _niveaux(level, t, trades):
    return pd.Series(level, index=t).reindex(trades.signal_bar.to_numpy()).to_numpy()


def test_verrou_egal_a_l_horizon_redonne_le_noyau_de_d02(barres_synthetiques, signaux_synthetiques):
    bars = barres_synthetiques(1500, seed=8)
    t, s, level = signaux_synthetiques(bars, 250, seed=9)
    for h in (3, 26, 60):
        assert run_trades(bars, t, s, h, level, lock=h).equals(run_trades(bars, t, s, h, level)), h


def test_verrou_au_moins_egal_a_l_horizon_redonne_lock_trades(barres_synthetiques, signaux_synthetiques):
    """Verrou ≥ horizon : sortie à l'horizon ou au stop, entrée suivante à partir de t + verrou (EXP-D01.6)."""
    bars = barres_synthetiques(1500, seed=10)
    t, s, level = signaux_synthetiques(bars, 250, seed=11)
    for h, lock in ((6, 26), (16, 26), (26, 26), (26, 40)):
        assert run_trades(bars, t, s, h, level, lock=lock).equals(lock_trades(bars, t, s, h, lock, level)), (h, lock)


def test_verrou_court_garde_les_entrees_a_tout_horizon(barres_synthetiques, signaux_synthetiques):
    """Verrou de 26 : mêmes entrées qu'à H = 26, quel que soit l'horizon de sortie (population constante)."""
    bars = barres_synthetiques(1500, seed=12)
    t, s, level = signaux_synthetiques(bars, 250, seed=13)
    cols = ["signal_bar", "entry_bar", "side", "entry_price"]
    ref = run_trades(bars, t, s, 26, level)
    for h in (6, 28, 40, 60):
        assert run_trades(bars, t, s, h, level, lock=26)[cols].equals(ref[cols]), h


def test_verrou_court_l_entree_suivante_clot_la_position(barres_synthetiques, signaux_synthetiques):
    """H > verrou : la position encore ouverte sort à l'ouverture où entre la suivante (une position à la fois) ;
    les autres trades sont ceux du signal joué seul (horizon ou stop)."""
    bars = barres_synthetiques(1500, seed=14)
    t, s, level = signaux_synthetiques(bars, 250, seed=15)
    got = run_trades(bars, t, s, 60, level, lock=26)
    e, x = got.entry_bar.to_numpy(), got.exit_bar.to_numpy()
    assert (x[:-1] <= e[1:]).all()
    cut = superseded(got, 60)
    i = np.flatnonzero(cut)
    assert len(i) > 5 and (i < len(got) - 1).all()
    assert (x[i] == e[i + 1]).all() and not got.stop.to_numpy()[i].any()
    assert np.array_equal(got.exit_price.to_numpy()[i], bars.open.to_numpy()[x[i]])
    seul = frozen_entries(bars, got, 60, _niveaux(level, t, got))
    assert got[~cut].equals(seul[~cut])
    assert (seul.exit_bar.to_numpy()[i] > x[i]).all()


def test_verrou_court_ne_lit_aucune_barre_posterieure_a_la_sortie(barres_synthetiques, signaux_synthetiques):
    bars = barres_synthetiques(1500, seed=16)
    t, s, level = signaux_synthetiques(bars, 250, seed=17)
    b = 900
    sel = t + 1 < b
    t, s, level = t[sel], s[sel], level[sel]
    got = run_trades(bars, t, s, 60, level, lock=26)
    altered = bars.copy()
    altered.loc[b:, ["open", "high", "low", "close"]] *= 1.3
    alt = run_trades(altered, t, s, 60, level, lock=26)
    done = (got.exit_bar < b).to_numpy()
    assert done.sum() > 20 and got[done].equals(alt[done])


def test_verrou_invalide_refuse(barres_synthetiques, signaux_synthetiques):
    bars = barres_synthetiques(400)
    t, s, level = signaux_synthetiques(bars, 40)
    with pytest.raises(ValueError, match="verrou"):
        run_trades(bars, t, s, 26, level, lock=0)


def test_coupure_reperee_sans_faux_positif_quand_verrou_egal_horizon(barres_synthetiques, signaux_synthetiques):
    bars = barres_synthetiques(1500, seed=18)
    t, s, level = signaux_synthetiques(bars, 250, seed=19)
    for h in (6, 26, 60):
        assert not superseded(run_trades(bars, t, s, h, level), h).any(), h
    assert not superseded(run_trades(bars, t, s, 26, level, last=700), 26).any()     # fin de série : pas une coupure
