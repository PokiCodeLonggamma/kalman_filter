"""EXP-D02 — noyau Numba (`optimization.engine`) : identique à `envelope.stop_trades` (`dynamic=False`), horizon et
niveau de stop par signal, borne de fin (dernière barre d'un IS), contrôles d'entrée."""
import numpy as np
import pandas as pd
import pytest

from envelope import stop_distance, stop_trades
from envelope.stops import _sequential
from estimand.stoploss import TRADE_COLUMNS, apply_stop
from optimization.engine import run_trades


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
