"""EXP-D05.1 — frictions FTMO trade par trade (`propfirm.frictions`) : écart à l'heure de l'entrée et de la sortie,
commission des deux côtés, swap de chaque rollover traversé (17:00 New York, jour triple). Frais en bps du notionnel,
positifs quand ils coûtent."""
import numpy as np
import pandas as pd
import pytest

from estimand.stoploss import TRADE_COLUMNS
from propfirm.frictions import commission_bps, couts_trades, ecart_trades, jours_swap, nuits, swap_bps


def _ns(x, tz="America/New_York"):
    return pd.Timestamp(x, tz=tz).value


@pytest.mark.parametrize("entree,sortie,triple,sept,attendu", [
    ("2025-03-03 12:00", "2025-03-04 12:00", "Wednesday", False, 1),     # lundi 17:00
    ("2025-03-05 16:00", "2025-03-06 10:00", "Wednesday", False, 3),     # mercredi triple
    ("2025-03-07 16:00", "2025-03-10 10:00", "Wednesday", False, 1),     # vendredi ; samedi et dimanche sans rollover
    ("2025-03-07 16:00", "2025-03-10 10:00", "Friday", False, 3),        # vendredi triple
    ("2025-03-07 16:00", "2025-03-10 10:00", None, True, 3),             # crypto : vendredi, samedi, dimanche
    ("2025-03-03 17:00", "2025-03-04 16:30", "Wednesday", False, 0),     # entrée à 17:00 : après le rollover
    ("2025-03-03 16:30", "2025-03-03 17:00", "Wednesday", False, 1),     # sortie à l'ouverture de 17:00 : tenue
    ("2025-03-03 09:00", "2025-03-03 16:30", "Wednesday", False, 0),
])
def test_nuits_comptees_au_rollover_de_17_h_new_york(entree, sortie, triple, sept, attendu):
    j = jours_swap(triple, sept_jours=sept)
    assert nuits(np.array([_ns(entree)]), np.array([_ns(sortie)]), j)[0] == attendu


def test_jours_swap():
    assert jours_swap("Wednesday") == {0: 1, 1: 1, 2: 3, 3: 1, 4: 1, 5: 0, 6: 0}
    assert jours_swap(None, sept_jours=True) == {k: 1 for k in range(7)}
    assert jours_swap("Friday", sept_jours=True) == {0: 1, 1: 1, 2: 1, 3: 1, 4: 3, 5: 0, 6: 0}


@pytest.mark.parametrize("typ,valeur,attendu", [
    ("Pips", -6.9638, 6.9638 * 1.0 / 31000.0 * 1e4),      # pip de 1 point sur l'US100 à 31 000
    ("Points", -2179.0, 2179.0 * 1e-3 / 200.0 * 1e4),     # point = 10^-digits (3 décimales), GBPJPY à 200
    ("Percentage", -30.0, 30.0 / 100.0 / 360.0 * 1e4),    # % par an, 360 jours
])
def test_swap_en_bps_par_nuit(typ, valeur, attendu):
    prix = {"Pips": 31000.0, "Points": 200.0, "Percentage": 120000.0}[typ]
    assert swap_bps(typ, valeur, prix, pip_size=1.0, digits=3) == pytest.approx(attendu)


def test_swap_positif_est_un_gain():
    assert swap_bps("Pips", 0.3417, 31000.0, pip_size=1.0, digits=2) < 0


@pytest.mark.parametrize("typ,valeur,attendu", [
    ("UsdPerMillionUsdVolume", 30.0, 0.3),
    ("PercentageOfTradingVolume", 0.0325, 3.25),
    ("UsdPerOneLot", 5.0, 5.0 / (100000.0 * 1.0) * 1e4),
    ("QuoteCurrencyPerOneLot", 500.0, 500.0 / (100000.0 * 200.0) * 1e4),
])
def test_commission_en_bps_par_cote(typ, valeur, attendu):
    prix = 200.0 if typ == "QuoteCurrencyPerOneLot" else 1.0
    assert commission_bps(typ, valeur, prix, lot_size=100000.0, usd_par_cotation=1.0) == pytest.approx(attendu)


def _trades(bars, specs):
    rows = [{"entry_bar": e, "exit_bar": x, "side": s, "entry_price": 100.0, "exit_price": 100.0, "stop": False,
             "gap": False, "ret_gross_bps": 0.0, "signal_bar": e - 1} for e, x, s in specs]
    return pd.DataFrame(rows)[TRADE_COLUMNS]


def test_ecart_mid_moitie_a_l_entree_et_a_la_sortie_bid_selon_le_sens():
    bars = pd.DataFrame({"time": pd.date_range("2025-07-01 13:00", periods=6, freq="30min", tz="UTC")})
    tr = _trades(bars, [(1, 3, 1), (1, 3, -1)])
    profil = pd.Series(np.arange(48, dtype=float))                 # écart = numéro de la demi-heure locale (UTC)
    mid = ecart_trades(tr, bars, profil, "UTC", prix="mid")
    bid = ecart_trades(tr, bars, profil, "UTC", prix="bid")
    assert np.allclose(mid, [(27 + 29) / 2] * 2)                   # 13:30 → 27 ; 14:30 → 29
    assert np.allclose(bid, [27, 29])                              # long : à l'achat (ask) ; short : au rachat (ask)


def test_couts_trades_somme_des_trois_parts():
    bars = pd.DataFrame({"time": pd.date_range("2025-03-03 20:00", periods=60, freq="30min", tz="UTC"),
                         "open": 100.0})
    tr = _trades(bars, [(1, 50, 1), (52, 55, -1)])                  # le premier traverse lundi 17:00 NY (22:00 UTC)
    fiche = pd.Series({"swap_type": "Pips", "swap_long": -0.02, "swap_short": 0.01, "swap_triple": "Wednesday",
                       "pip_size": 1.0, "digits": 2, "commission_type": "UsdPerMillionUsdVolume", "commission": 25.0,
                       "lot_size": 1.0})
    c = couts_trades(tr, bars, fiche, pd.Series(np.full(48, 4.0)), "UTC", prix="mid", sept_jours=False)
    assert list(c.columns) == ["ecart", "commission", "swap", "nuits", "total"]
    assert np.allclose(c.ecart, 4.0) and np.allclose(c.commission, 0.5)
    assert c.nuits.tolist() == [1, 0] and c.swap.iat[0] == pytest.approx(0.02 / 100.0 * 1e4)
    assert np.allclose(c.total, c.ecart + c.commission + c.swap)


# ── Pauses de cotation FTMO (cryptos sur les séries des courtiers de D05) ──────────
from marketdata.ftmo import pauses_cotation  # noqa: E402
from propfirm.frictions import ajuster_pauses  # noqa: E402


def test_pauses_cotation_entre_deux_barres_non_consecutives():
    t = pd.DatetimeIndex(["2025-03-01 10:00", "2025-03-01 10:30", "2025-03-01 14:00", "2025-03-01 14:30"], tz="UTC")
    p = pauses_cotation(t)
    assert len(p) == 1
    assert p.debut.iat[0] == pd.Timestamp("2025-03-01 11:00", tz="UTC").value
    assert p.fin.iat[0] == pd.Timestamp("2025-03-01 14:00", tz="UTC").value


def _continu(n=40, start="2025-03-01 00:00"):
    p = 100.0 + np.arange(n, dtype=float)
    return pd.DataFrame({"time": pd.date_range(start, periods=n, freq="30min", tz="UTC"), "open": p, "high": p + 0.5,
                         "low": p - 0.5, "close": p})


def _tr(bars, specs):
    """specs : (entrée, sortie, sens, stop)."""
    rows = []
    for e, x, s, st in specs:
        p0, p1 = bars.open.iat[e], (bars.open.iat[x] - 0.2 if st else bars.open.iat[x])
        rows.append({"entry_bar": e, "exit_bar": x, "side": s, "entry_price": p0, "exit_price": p1, "stop": st,
                     "gap": False, "ret_gross_bps": s * (p1 / p0 - 1.0) * 1e4, "signal_bar": e - 1})
    return pd.DataFrame(rows)[TRADE_COLUMNS]


def _pause(bars, a, b):
    """Pause couvrant les barres a à b − 1 (réouverture à la barre b)."""
    return pd.DataFrame({"debut": [bars.time.iat[a].value], "fin": [bars.time.iat[b].value]})


def test_sans_pause_les_trades_sont_inchanges():
    bars = _continu()
    tr = _tr(bars, [(2, 8, 1, False), (10, 15, -1, True)])
    out, r = ajuster_pauses(tr, bars, pd.DataFrame({"debut": [], "fin": []}))
    assert out.equals(tr) and r["entrees_abandonnees"] == 0 and r["sorties_a_la_reouverture"] == 0


def test_entree_pendant_une_pause_abandonnee():
    bars = _continu()
    tr = _tr(bars, [(5, 12, 1, False), (20, 26, 1, False)])
    out, r = ajuster_pauses(tr, bars, _pause(bars, 4, 7))
    assert len(out) == 1 and out.entry_bar.iat[0] == 20 and r["entrees_abandonnees"] == 1


@pytest.mark.parametrize("stop", [False, True])
def test_sortie_ou_stop_pendant_une_pause_executes_a_la_reouverture(stop):
    bars = _continu()
    tr = _tr(bars, [(2, 9, -1, stop)])
    out, r = ajuster_pauses(tr, bars, _pause(bars, 8, 12))
    assert out.exit_bar.iat[0] == 12 and out.exit_price.iat[0] == bars.open.iat[12]
    assert not out.stop.iat[0] and out.gap.iat[0]
    assert out.ret_gross_bps.iat[0] == pytest.approx(-1.0 * (bars.open.iat[12] / bars.open.iat[2] - 1.0) * 1e4)
    assert r["sorties_a_la_reouverture"] == 1


def test_sortie_retardee_puis_entree_suivante_a_la_reouverture():
    """Une entrée pendant la pause est abandonnée ; celle de la barre de réouverture suit la sortie retardée."""
    bars = _continu()
    tr = _tr(bars, [(2, 9, 1, False), (10, 16, 1, False), (12, 18, 1, False)])
    out, r = ajuster_pauses(tr, bars, _pause(bars, 8, 12))
    assert out.entry_bar.tolist() == [2, 12] and out.exit_bar.tolist() == [12, 18]
    assert r["entrees_abandonnees"] == 1 and r["sorties_a_la_reouverture"] == 1
    assert r["chevauchements_abandonnes"] == 0
