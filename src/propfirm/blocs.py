"""EXP-D05.7 — tirage par blocs de semaines : histoires recomposées pour le simulateur de challenge (décision du porteur
du 2026-10-05).

- Une semaine va du lundi 00:00 local au lundi suivant. Elle apporte tous les trades entrés pendant elle, sur toutes
  les jambes, chacun avec son propre chemin de barres, même quand il déborde sur la semaine suivante.
- Une histoire place à sa semaine k la semaine source tirée pour elle, décalée de (début de k − début de la source).
  Un trade garde ses prix, son sens, son P&L brut, son stop et son ATR ; seules ses dates changent.
- Tirage : blocs de `longueur` semaines consécutives, début uniforme ; l'histoire a autant de semaines que la source.
- Un trade qui chevaucherait le précédent du même actif (débordement d'une semaine sur le premier trade de la
  suivante) va dans une jambe de débordement du même actif. L'histoire identité redonne donc les jambes d'origine.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from envelope.portfolio import Leg
from propfirm.moteur import HALF

SEMAINE_JOURS = 7


def semaines(debut, fin, fuseau: str = "Europe/Prague") -> np.ndarray:
    """Bornes (UTC, ns) des semaines locales entières de `debut` (un lundi) à `fin` (un lundi) : n + 1 valeurs."""
    jours = pd.date_range(pd.Timestamp(debut), pd.Timestamp(fin), freq=f"{SEMAINE_JOURS}D")
    if pd.Timestamp(debut).weekday() != 0 or jours[-1] != pd.Timestamp(fin):
        raise ValueError("semaines : début et fin doivent être des lundis")
    return jours.tz_localize(fuseau).tz_convert("UTC").asi8.copy()


def tirage(n_semaines: int, longueur: int, rng: np.random.Generator) -> np.ndarray:
    """Semaine source de chaque semaine de l'histoire : blocs de `longueur` semaines consécutives dont le début est
    tiré uniformément, mis bout à bout puis tronqués à `n_semaines`."""
    n_blocs = -(-n_semaines // longueur)
    debuts = rng.integers(0, n_semaines - longueur + 1, size=n_blocs)
    return (debuts[:, None] + np.arange(longueur)[None, :]).ravel()[:n_semaines].astype(np.int64)


def histoire(legs: list[Leg], atr: list[np.ndarray], bornes: np.ndarray,
             source: np.ndarray) -> tuple[list[Leg], list[np.ndarray]]:
    """Jambes et ATR (une valeur par trade) de l'histoire dont la semaine k est la semaine source `source[k]`."""
    bornes, source = np.asarray(bornes, dtype=np.int64), np.asarray(source, dtype=np.int64)
    n = len(bornes) - 1
    out_legs, out_atr = [], []
    for leg, a in zip(legs, atr):
        tr = leg.trades.reset_index(drop=True)
        t = pd.DatetimeIndex(leg.bars.time).asi8
        e, x = tr.entry_bar.to_numpy(dtype=np.int64), tr.exit_bar.to_numpy(dtype=np.int64)
        sem = np.searchsorted(bornes, t[e], side="right") - 1
        par_semaine = [np.flatnonzero(sem == w) for w in range(n)]
        sel = np.concatenate([par_semaine[w] for w in source] + [np.zeros(0, dtype=np.int64)])
        dec = np.concatenate([np.full(len(par_semaine[w]), bornes[k] - bornes[w], dtype=np.int64)
                              for k, w in enumerate(source)] + [np.zeros(0, dtype=np.int64)])
        stop = tr.stop.to_numpy(dtype=bool)
        entree = t[e[sel]] + dec
        sortie = t[x[sel]] + dec + np.where(stop[sel], HALF, 0)
        jambes, fins = [], []                                 # trades de chaque jambe ; dernier instant de sortie
        for i in range(len(sel)):
            for q, f in enumerate(fins):
                if f <= entree[i]:
                    break
            else:
                q = len(fins)
                jambes.append([])
                fins.append(np.iinfo(np.int64).min)
            jambes[q].append(i)
            fins[q] = sortie[i]
        cols = ("open", "high", "low", "close")
        for membres in jambes:
            membres = np.asarray(membres, dtype=np.int64)
            j = sel[membres]
            longs = x[j] - e[j] + 1
            barre = np.concatenate([np.arange(e[q], x[q] + 1) for q in j])
            decal = np.repeat(dec[membres], longs)
            bars = pd.DataFrame({"time": pd.to_datetime(t[barre] + decal, utc=True),
                                 **{c: leg.bars[c].to_numpy(dtype=float)[barre] for c in cols if c in leg.bars}})
            debut = np.r_[0, np.cumsum(longs)[:-1]]
            trades = tr.iloc[j].reset_index(drop=True).copy()
            trades["entry_bar"] = debut
            trades["exit_bar"] = debut + longs - 1
            trades["signal_bar"] = debut - 1
            cout = leg.cost if np.ndim(leg.cost) == 0 else np.asarray(leg.cost, dtype=float)[j]
            out_legs.append(Leg(leg.name, bars, trades, np.asarray(leg.weight)[j], cout))
            out_atr.append(np.asarray(a, dtype=float)[j])
    return out_legs, out_atr
