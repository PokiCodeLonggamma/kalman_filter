"""EXP-D05.1 — frictions du compte FTMO, trade par trade, en bps du notionnel (positives quand elles coûtent).

- Écart : profil par demi-heure locale (médiane des écarts à l'ouverture des barres, `marketdata.ftmo`). Série au milieu
  (`prix="mid"`, séries des courtiers de D05) : moitié de l'écart à l'entrée + moitié à la sortie. Série au bid
  (`prix="bid"`, bougies cTrader) : un long achète à l'ask (écart de l'entrée), un short rachète à l'ask (écart de la
  sortie). Le stop s'exécute dans la barre de sortie : écart de sa demi-heure.
- Commission : à chaque côté, sur le prix d'entrée (types cTrader `SymbolCommissionType`).
- Swap : à chaque rollover traversé, 17:00 New York (convention du marché, [HYP] pour FTMO), compté si l'entrée est
  avant et la sortie à ou après ; poids par jour de semaine (`jours_swap` : triple le jour `Swap3DaysRollover`,
  week-end sans rollover, ou tous les jours pour une cotation 7 j/7 sans jour triple). Swap en pips ou en points du
  prix d'entrée, ou en % par an sur 360 jours ([HYP] base de calcul). Imputé à la sortie (le moteur prélève les frais
  à la sortie).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from marketdata.ftmo import demi_heure

BPS = 1e4
JOURS = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")


def jours_swap(triple: str | None, sept_jours: bool = False) -> dict[int, int]:
    """Poids du rollover par jour de semaine (lundi = 0)."""
    if triple is None or (isinstance(triple, float) and np.isnan(triple)) or triple == "":
        if sept_jours:
            return {k: 1 for k in range(7)}
        return {k: (1 if k < 5 else 0) for k in range(7)}
    j = JOURS.index(triple)
    return {k: (3 if k == j else 1 if k < 5 else 0) for k in range(7)}


def nuits(entree_ns, sortie_ns, jours: dict[int, int], heure: int = 17, fuseau: str = "America/New_York") -> np.ndarray:
    """Rollovers traversés (pondérés) : instants `heure`:00 locaux t avec entrée < t ≤ sortie."""
    e, s = np.asarray(entree_ns, dtype=np.int64), np.asarray(sortie_ns, dtype=np.int64)
    if not len(e):
        return np.zeros(0, dtype=np.int64)
    d0 = pd.Timestamp(int(e.min()), tz="UTC").tz_convert(fuseau).normalize().tz_localize(None) - pd.Timedelta(days=1)
    d1 = pd.Timestamp(int(s.max()), tz="UTC").tz_convert(fuseau).normalize().tz_localize(None) + pd.Timedelta(days=1)
    dates = pd.date_range(d0, d1, freq="D")
    r = (dates + pd.Timedelta(hours=heure)).tz_localize(fuseau).tz_convert("UTC").asi8
    w = np.array([jours[d] for d in dates.weekday], dtype=np.int64)
    cum = np.r_[0, np.cumsum(w)]
    return cum[np.searchsorted(r, s, side="right")] - cum[np.searchsorted(r, e, side="right")]


def swap_bps(typ: str, valeur, prix, pip_size: float, digits: int):
    """Coût d'une nuit en bps du notionnel (négatif : la nuit rapporte)."""
    v, p = np.asarray(valeur, dtype=float), np.asarray(prix, dtype=float)
    if typ == "Pips":
        return -v * pip_size / p * BPS
    if typ == "Points":
        return -v * 10.0 ** (-digits) / p * BPS
    if typ == "Percentage":
        return -v / 100.0 / 360.0 * BPS + 0.0 * p
    raise ValueError(f"swap : type inconnu {typ!r}")


def commission_bps(typ: str, valeur: float, prix, lot_size: float, usd_par_cotation: float = 1.0):
    """Commission d'un côté en bps du notionnel."""
    p = np.asarray(prix, dtype=float)
    if typ == "UsdPerMillionUsdVolume":
        return valeur / 1e6 * BPS + 0.0 * p
    if typ == "PercentageOfTradingVolume":
        return valeur / 100.0 * BPS + 0.0 * p
    if typ == "UsdPerOneLot":
        return valeur / (lot_size * p * usd_par_cotation) * BPS
    if typ == "QuoteCurrencyPerOneLot":
        return valeur / (lot_size * p) * BPS
    raise ValueError(f"commission : type inconnu {typ!r}")


def ecart_trades(trades: pd.DataFrame, bars: pd.DataFrame, profil: pd.Series, fuseau: str,
                 prix: str = "mid") -> np.ndarray:
    """Écart payé par chaque trade (bps) d'après le profil par demi-heure locale (48 valeurs ; une demi-heure sans
    mesure prend la médiane du profil)."""
    v = pd.Series(profil, dtype=float).reindex(range(48)).to_numpy()
    v = np.where(np.isnan(v), np.nanmedian(v), v)
    t = pd.DatetimeIndex(bars.time)
    se = v[demi_heure(t[trades.entry_bar.to_numpy()], fuseau)]
    sx = v[demi_heure(t[trades.exit_bar.to_numpy()], fuseau)]
    if prix == "mid":
        return (se + sx) / 2.0
    if prix == "bid":
        return np.where(trades.side.to_numpy() == 1, se, sx)
    raise ValueError(f"écart : convention de prix inconnue {prix!r}")


def couts_trades(trades: pd.DataFrame, bars: pd.DataFrame, fiche: pd.Series, profil: pd.Series, fuseau: str,
                 prix: str = "mid", sept_jours: bool = False, usd_par_cotation: float = 1.0) -> pd.DataFrame:
    """Écart, commission (deux côtés), swap (nuits × coût d'une nuit), nuits pondérées et total, par trade (bps)."""
    t = pd.DatetimeIndex(bars.time).asi8
    p0 = trades.entry_price.to_numpy(dtype=float)
    side = trades.side.to_numpy()
    ec = ecart_trades(trades, bars, profil, fuseau, prix)
    com = 2.0 * commission_bps(fiche["commission_type"], float(fiche["commission"]), p0, float(fiche["lot_size"]),
                               usd_par_cotation)
    n = nuits(t[trades.entry_bar.to_numpy()], t[trades.exit_bar.to_numpy()],
              jours_swap(fiche.get("swap_triple"), sept_jours))
    taux = np.where(side == 1, float(fiche["swap_long"]), float(fiche["swap_short"]))
    sw = n * swap_bps(fiche["swap_type"], taux, p0, float(fiche["pip_size"]), int(fiche["digits"]))
    return pd.DataFrame({"ecart": ec, "commission": com, "swap": sw, "nuits": n, "total": ec + com + sw})


def ajuster_pauses(trades: pd.DataFrame, bars: pd.DataFrame, pauses: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Trades d'une série continue (cryptos des courtiers de D05) exécutés sur le calendrier de cotation de FTMO :
    - entrée dont la barre s'ouvre pendant une pause : signal abandonné (aucun ordre possible) ;
    - sortie (horizon ou stop) dont la barre s'ouvre pendant une pause : exécutée à l'ouverture de la première barre de
      la réouverture (stop non déclenché, sortie sur gap) ; [HYP] un stop franchi pendant la pause est exécuté à la
      réouverture même si le prix est revenu ;
    - trade suivant du même actif chevauché par une sortie retardée : abandonné (une position à la fois).
    `pauses` : colonnes `debut`, `fin` (ns UTC, `marketdata.ftmo.pauses_cotation`)."""
    t = pd.DatetimeIndex(bars.time).asi8
    deb, fin = pauses.debut.to_numpy(dtype=np.int64), pauses.fin.to_numpy(dtype=np.int64)
    o = np.argsort(deb)
    deb, fin = deb[o], fin[o]

    def pause(x: int) -> int:
        i = int(np.searchsorted(deb, x, side="right")) - 1
        return i if i >= 0 and x < fin[i] else -1

    tr = trades.reset_index(drop=True)
    garde, rows = [], []
    n_e = n_x = n_c = n_fin = 0
    prec_x, prec_stop = None, False
    opn = bars.open.to_numpy(dtype=float)
    for j in range(len(tr)):
        r = tr.iloc[j].copy()
        e, x = int(r.entry_bar), int(r.exit_bar)
        if pause(t[e]) >= 0:
            n_e += 1
            continue
        if prec_x is not None and (e <= prec_x if prec_stop else e < prec_x):
            n_c += 1
            continue
        p = pause(t[x])
        if p >= 0:
            x2 = int(np.searchsorted(t, fin[p], side="left"))
            if x2 >= len(t):
                n_fin += 1
                continue
            r["exit_bar"], r["exit_price"], r["stop"], r["gap"] = x2, opn[x2], False, True
            r["ret_gross_bps"] = float(r.side) * (opn[x2] / float(r.entry_price) - 1.0) * BPS
            n_x += 1
        prec_x, prec_stop = int(r.exit_bar), bool(r.stop)
        rows.append(r)
        garde.append(j)
    out = pd.DataFrame(rows, columns=tr.columns).reset_index(drop=True) if rows else tr.iloc[:0].copy()
    out = out.astype(tr.dtypes.to_dict())
    return out, {"trades": len(tr), "gardes": len(out), "entrees_abandonnees": n_e, "sorties_a_la_reouverture": n_x,
                 "chevauchements_abandonnes": n_c, "fin_de_donnees_abandonnes": n_fin}
