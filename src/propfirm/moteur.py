"""EXP-D05.4 — simulateur de challenge de prop firm (étalon : compte FTMO Swing, décision du porteur du 2026-10-05).

Un départ par minuit local (CET/CEST). Chaque départ est un compte neuf, à plat, qui ne prend que les trades entrés à
partir de lui. Tous les départs avancent ensemble sur la même suite d'événements, avec les règles de
`envelope.portfolio_paths` : à instant égal, clôtures, puis sorties, puis entrées ; à l'entrée, notionnel = poids ×
capital valorisé du départ. Sans plafond ni correction, le départ qui voit tous les trades redonne `portfolio_paths`.

- Marge (`plafonner`) : marge utilisée = Σ valeur de marché / levier de l'actif ; marge libre = capital valorisé − marge
  utilisée. Une entrée qui dépasserait la marge libre est réduite à ce qu'elle permet ; des entrées simultanées se la
  partagent au prorata de leurs demandes (règle du porteur). Les sorties du même instant libèrent leur marge avant.
- Correction du stop (`correction_stop`, par défaut) : à la clôture de la barre d'un stop, la position stoppée compte
  pour sa perte réalisée, en même temps que les autres positions à leur extrême défavorable (`portfolio_paths` la
  gardait à sa clôture précédente).
- Règles, en fraction du solde initial de chaque départ (1) :
  - objectif atteint au premier état où capital valorisé − frais de sortie des positions ouvertes ≥ 1 + objectif, avec au
    moins `jours_min` jours locaux comptant une entrée (tout est alors clôturé) ;
  - perte du jour : un état de la journée locale ]minuit, minuit suivant] ≤ référence de minuit − `perte_jour` ;
    référence = solde réalisé (FTMO) ou max(solde, capital valorisé) ;
  - perte totale : un état ≤ 1 − `perte_max` ;
  - deux lectures : borne pessimiste (extrêmes de la barre) et capital valorisé (clôtures).
Aucun prix postérieur à l'instant évalué n'est lu.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from envelope.portfolio import Leg
from estimand.excursions import BPS

INF = np.iinfo(np.int64).max
HALF = 30 * 60 * 10**9
MARK, EXIT, ENTRY = 0, 1, 2
MODES = ("pessimiste", "valorise")
REFS = ("solde", "max")


@dataclass(frozen=True)
class Regles:
    objectifs: tuple = (0.09, 0.05)          # P1, P2 : fractions du solde initial
    perte_jour: float = 0.05
    perte_max: float = 0.10                  # statique
    jours_min: int = 4
    fuseau: str = "Europe/Prague"            # minuit CET/CEST


FTMO_SWING = Regles()
LEVIER_FTMO_SWING = {"BTC": 2.0, "ETH": 2.0, "SOL": 2.0, "AVAX": 2.0, "XRP": 2.0, "XAU": 30.0}


@dataclass
class Simulation:
    departs: np.ndarray                      # ns UTC, croissants
    regles: Regles
    t_objectif: np.ndarray                   # (objectifs, départs), ns ; INF : jamais
    t_perte_max: dict                        # mode → (départs,)
    t_perte_jour: dict                       # (référence, mode) → (départs,)
    ref_breche: dict                         # (référence, mode) → référence de minuit au premier franchissement
    chemin: pd.DataFrame | None              # départ suivi : un état par instant (colonnes de `portfolio_paths`, marge)
    tailles: pd.DataFrame | None             # départ suivi : une ligne par entrée (demande, obtenu)


def departs_minuit(debut, fin, fuseau: str = "Europe/Prague") -> np.ndarray:
    """Minuits locaux du jour `debut` au jour `fin` exclu, en ns UTC."""
    jours = pd.date_range(pd.Timestamp(debut).date(), pd.Timestamp(fin).date(), freq="D", inclusive="left")
    return jours.tz_localize(fuseau).tz_convert("UTC").asi8.copy()


def _jours(t: np.ndarray, fuseau: str) -> np.ndarray:
    loc = pd.to_datetime(t, utc=True).tz_convert(fuseau)
    return np.asarray(loc.year * 10000 + loc.month * 100 + loc.day, dtype=np.int64)


def _evenements(legs: list[Leg]) -> list[np.ndarray]:
    """(instant, nature, jambe, trade, clôture, extrême défavorable), triés par instant puis nature (ordre stable)."""
    parts = []
    for li, leg in enumerate(legs):
        tr = leg.trades.reset_index(drop=True)
        n = len(tr)
        if len(leg.weight) != n:
            raise ValueError(f"simuler : {leg.name}, un poids par trade exigé")
        e, x = tr.entry_bar.to_numpy(dtype=np.int64), tr.exit_bar.to_numpy(dtype=np.int64)
        stop = tr.stop.to_numpy(dtype=bool)
        if n > 1 and not np.where(stop[:-1], x[:-1] < e[1:], x[:-1] <= e[1:]).all():
            raise ValueError(f"simuler : {leg.name}, trades qui se chevauchent sur un même actif")
        t = pd.DatetimeIndex(leg.bars.time).asi8
        side = tr.side.to_numpy(dtype=np.int64)
        m = x - e
        jm = np.repeat(np.arange(n), m)
        km = np.repeat(e, m) + np.arange(m.sum()) - np.repeat(np.cumsum(m) - m, m)
        low, high = leg.bars.low.to_numpy(dtype=float), leg.bars.high.to_numpy(dtype=float)
        adv = np.where(side[jm] == 1, low[km], high[km])
        vide = np.full(n, np.nan)
        parts.append((np.r_[t[e], t[km] + HALF, np.where(stop, t[x] + HALF, t[x])],
                      np.r_[np.full(n, ENTRY), np.full(len(km), MARK), np.full(n, EXIT)],
                      np.full(2 * n + len(km), li), np.r_[np.arange(n), jm, np.arange(n)],
                      np.r_[vide, leg.bars.close.to_numpy(dtype=float)[km], vide], np.r_[vide, adv, vide]))
    cols = [np.concatenate([p[i] for p in parts]) for i in range(6)]
    order = np.lexsort((cols[1], cols[0]))
    return [c[order] for c in cols]


def simuler(legs: list[Leg], departs, regles: Regles = FTMO_SWING, levier: dict | None = None,
            plafonner: bool = False, correction_stop: bool = True, suivi: int | None = None) -> Simulation:
    """Premiers instants d'objectif, de perte du jour et de perte totale de chaque départ ; chemin et tailles du départ
    `suivi`. `levier` (nom de jambe → levier) sert à mesurer la marge, et à la plafonner si `plafonner`."""
    departs = np.asarray(departs, dtype=np.int64)
    if not len(departs) or (np.diff(departs) <= 0).any():
        raise ValueError("simuler : départs croissants exigés")
    if plafonner and levier is None:
        raise ValueError("simuler : plafond de marge sans levier")
    nl, ns = len(legs), len(departs)
    lev = None if levier is None else [float(levier[leg.name]) for leg in legs]
    ev_t, ev_k, ev_l, ev_j, ev_p, ev_a = _evenements(legs)
    trades = [leg.trades.reset_index(drop=True) for leg in legs]
    p_in = [tr.entry_price.to_numpy(dtype=float) for tr in trades]
    s_in = [tr.side.to_numpy(dtype=float) for tr in trades]
    gain = [(tr.ret_gross_bps.to_numpy(dtype=float) - float(leg.cost)) / BPS for tr, leg in zip(trades, legs)]
    arret = [tr.stop.to_numpy(dtype=bool) for tr in trades]
    poids = [np.asarray(leg.weight, dtype=float) for leg in legs]
    cout = [float(leg.cost) / BPS for leg in legs]

    notion, cap = np.zeros((nl, ns)), np.ones(ns)
    ouvert, sens, p0, last, adv = [False] * nl, [0.0] * nl, [1.0] * nl, [1.0] * nl, [1.0] * nl
    n_jours, dernier = np.zeros(ns, dtype=np.int64), np.full(ns, -1, dtype=np.int64)
    val_prec = np.ones(ns)
    seuils = [1.0 + o for o in regles.objectifs]
    t_obj = np.full((len(seuils), ns), INF, dtype=np.int64)
    t_max = {m: np.full(ns, INF, dtype=np.int64) for m in MODES}
    t_jour = {(r, m): np.full(ns, INF, dtype=np.int64) for r in REFS for m in MODES}
    ref_b = {k: np.full(ns, np.nan) for k in t_jour}
    att_obj = np.ones((len(seuils), ns), dtype=bool)
    att_max = {m: np.ones(ns, dtype=bool) for m in MODES}
    att_jour = {k: np.ones(ns, dtype=bool) for k in t_jour}
    plancher_max = 1.0 - regles.perte_max
    ref, plancher = {}, {}

    def somme(fac, base):
        out = base.copy()
        for li in range(nl):
            if fac[li] != 0.0:
                out += fac[li] * notion[li]
        return out

    def latents():
        return [sens[li] * (last[li] / p0[li] - 1.0) if ouvert[li] else 0.0 for li in range(nl)]

    def controler(tm, val, pes, frais):
        for mode, x in (("pessimiste", pes), ("valorise", val)):
            hit = (x <= plancher_max) & att_max[mode]
            if hit.any():
                t_max[mode][hit] = tm
                att_max[mode][hit] = False
            for r in REFS:
                hit = (x <= plancher[r]) & att_jour[(r, mode)]
                if hit.any():
                    t_jour[(r, mode)][hit] = tm
                    ref_b[(r, mode)][hit] = ref[r][hit]
                    att_jour[(r, mode)][hit] = False
        net, ok = val - frais, n_jours >= regles.jours_min
        for k, seuil in enumerate(seuils):
            hit = (net >= seuil) & ok & att_obj[k]
            if hit.any():
                t_obj[k][hit] = tm
                att_obj[k][hit] = False

    lignes, tailles = [], []

    def noter(tm, val, pes):
        s, v = suivi, val[suivi]
        tenues = [li for li in range(nl) if ouvert[li] and notion[li, s] > 0.0]
        brute = sum(notion[li, s] * last[li] / p0[li] for li in tenues)
        marge = (sum(notion[li, s] * last[li] / p0[li] / lev[li] for li in tenues) / v) if lev is not None else np.nan
        lignes.append((tm, v, cap[s], pes[s], brute / v if tenues else 0.0, len(tenues), marge))

    uniq, debut = np.unique(ev_t, return_index=True)
    bornes = np.r_[debut, len(ev_t)]
    jour_etat, jour_entree = _jours(uniq - 1, regles.fuseau), _jours(uniq, regles.fuseau)
    nat, jam, trd, clo, ext = ev_k.tolist(), ev_l.tolist(), ev_j.tolist(), ev_p.tolist(), ev_a.tolist()
    jour = None
    for g in range(len(uniq)):
        tm = int(uniq[g])
        if jour_etat[g] != jour:                              # minuit local : références du jour
            jour = jour_etat[g]
            ref = {"solde": cap.copy(), "max": np.maximum(cap, val_prec)}
            plancher = {r: ref[r] - regles.perte_jour for r in REFS}
        marques, sorties, entrees = [], [], []
        for i in range(bornes[g], bornes[g + 1]):
            (marques if nat[i] == MARK else sorties if nat[i] == EXIT else entrees).append(i)
        if marques:
            for i in marques:
                last[jam[i]], adv[jam[i]] = clo[i], ext[i]
            vues = {jam[i] for i in marques}
            f = latents()
            gq = [sens[li] * ((adv[li] if li in vues else last[li]) / p0[li] - 1.0) if ouvert[li] else 0.0
                  for li in range(nl)]
            fr = [cout[li] if ouvert[li] else 0.0 for li in range(nl)]
            if correction_stop:
                for i in sorties:
                    li, j = jam[i], trd[i]
                    if arret[li][j]:
                        f[li] = gq[li] = gain[li][j]
                        fr[li] = 0.0
            val, pes = somme(f, cap), somme(gq, cap)
            controler(tm, val, pes, somme(fr, np.zeros(ns)))
            if suivi is not None:
                noter(tm, val, pes)
            val_prec = val
        if sorties or entrees:
            for i in sorties:
                li, j = jam[i], trd[i]
                cap += notion[li] * gain[li][j]
                notion[li] = 0.0
                ouvert[li] = False
            if entrees:
                val = somme(latents(), cap)
                n_dem = int(np.searchsorted(departs, tm, side="right"))      # départs déjà commencés
                dem = []
                for i in entrees:
                    d = poids[jam[i]][trd[i]] * val
                    d[n_dem:] = 0.0
                    dem.append(d)
                obt = dem
                if plafonner:
                    utilisee = somme([last[li] / p0[li] / lev[li] if ouvert[li] else 0.0 for li in range(nl)],
                                     np.zeros(ns))
                    libre = np.maximum(val - utilisee, 0.0)
                    besoin = np.zeros(ns)
                    for q, i in enumerate(entrees):
                        besoin += dem[q] / lev[jam[i]]
                    frac = np.ones(ns)
                    trop = besoin > libre
                    frac[trop] = libre[trop] / besoin[trop]
                    obt = [d * frac for d in dem]
                engage = np.zeros(ns, dtype=bool)
                for q, i in enumerate(entrees):
                    li, j = jam[i], trd[i]
                    notion[li] = obt[q]
                    ouvert[li], sens[li] = True, s_in[li][j]
                    p0[li] = last[li] = adv[li] = p_in[li][j]
                    engage |= obt[q] > 0.0
                    if suivi is not None:
                        tailles.append((legs[li].name, j, tm, poids[li][j], dem[q][suivi], obt[q][suivi], val[suivi]))
                nouveau = engage & (dernier != jour_entree[g])
                n_jours[nouveau] += 1
                dernier[nouveau] = jour_entree[g]
            val = somme(latents(), cap)
            controler(tm, val, val, somme([cout[li] if ouvert[li] else 0.0 for li in range(nl)], np.zeros(ns)))
            if suivi is not None:
                noter(tm, val, val)
            val_prec = val

    chemin = taille = None
    if suivi is not None:
        cols = ["capital_valorise", "solde_realise", "capital_pessimiste", "exposition_brute", "positions", "marge"]
        df = pd.DataFrame(lignes, columns=["time"] + cols)
        chemin = df.set_index(pd.to_datetime(df.pop("time"), utc=True))
        taille = pd.DataFrame(tailles, columns=["jambe", "trade", "entree", "poids", "demande", "obtenu", "capital"])
        taille["entree"] = pd.to_datetime(taille.entree, utc=True)
    return Simulation(departs, regles, t_obj, t_max, t_jour, ref_b, chemin, taille)
