"""EXP-D05.4 à D05.6bis — issues d'un challenge en deux phases, du compte financé, et valeur d'une tentative, à partir de
`Simulation`.

- Une phase (objectif k) se termine au premier de ses événements : échec (perte du jour ou perte totale) ou réussite. À
  instant égal, l'échec l'emporte ; si les deux planchers sont franchis au même état, la cause est le plus haut (le
  premier atteint quand l'équité baisse).
- P2 démarre au premier minuit local qui suit la réussite de P1, sur un compte neuf : son issue est celle de la phase 2
  du départ de ce minuit. Le compte financé démarre de même au premier minuit qui suit la réussite de P2.
- Compte financé (EXP-D05.5) : il dure jusqu'à sa première rupture de règle ; seuls les retraits antérieurs comptent.
  Valeur d'une tentative = − frais + (frais remboursés + part × retraits) si au moins un retrait a lieu.
- Suite de tentatives (EXP-D05.6bis) : un seul compte à la fois, une nouvelle tentative au minuit qui suit chaque échec
  du challenge ou chaque rupture du compte financé ; la taille du challenge et celle du compte financé peuvent différer
  (deux `Simulation`).
- `coupure` (ns) : les événements postérieurs ne sont pas observés (« en cours ») ; les départs à partir de la coupure
  sont retirés.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from propfirm.moteur import INF, Simulation

EN_COURS, REUSSITE, PERTE_JOUR, PERTE_MAX = 0, 1, 2, 3
NOM_PHASE = np.array(["en_cours", "reussite", "perte_jour", "perte_max"], dtype=object)
ISSUES = ("reussite", "echec_p1_jour", "echec_p1_max", "echec_p2_jour", "echec_p2_max", "en_cours_p1", "en_cours_p2")
JOUR = 86_400 * 10**9


def _echec(sim: Simulation, ref: str, mode: str, coupure: int | None) -> tuple[np.ndarray, np.ndarray]:
    """(instant de la première rupture de règle, cause) de chaque départ ; INF : aucune."""
    tx = sim.t_perte_max[mode].copy()
    tj = sim.t_perte_jour[(ref, mode)].copy()
    if coupure is not None:
        tx[tx > coupure] = INF
        tj[tj > coupure] = INF
    rb = sim.ref_breche[(ref, mode)]
    jour_d_abord = (tj < tx) | ((tj == tx) & (rb - sim.regles.perte_jour > 1.0 - sim.regles.perte_max))
    return np.minimum(tj, tx), np.where(jour_d_abord, PERTE_JOUR, PERTE_MAX)


def issue_phase(sim: Simulation, k: int, ref: str = "solde", mode: str = "pessimiste",
                coupure: int | None = None) -> tuple[np.ndarray, np.ndarray]:
    """(issue, instant) de la phase d'objectif k pour chaque départ."""
    to = sim.t_objectif[k].copy()
    if coupure is not None:
        to[to > coupure] = INF
    t_echec, cause = _echec(sim, ref, mode, coupure)
    echec = (t_echec < INF) & (t_echec <= to)
    issue = np.where(echec, cause, np.where(to < INF, REUSSITE, EN_COURS))
    t = np.where(echec, t_echec, np.where(to < INF, to, INF))
    return issue.astype(np.int8), t.astype(np.int64)


def _enchainer(sim: Simulation, ref: str, mode: str, coupure: int | None):
    """(issue de P1, issue de P2, instant de la réussite de P2 ou INF, issue du challenge) de chaque départ."""
    d = sim.departs
    n = len(d)
    i1, t1 = issue_phase(sim, 0, ref, mode, coupure)
    i2, t2 = issue_phase(sim, 1, ref, mode, coupure)
    ok1 = i1 == REUSSITE
    k2 = np.searchsorted(d, np.where(ok1, t1, d[0]), side="left")
    has2 = ok1 & (k2 < n)
    k2c = np.minimum(k2, n - 1)
    p2 = np.where(has2, i2[k2c], EN_COURS)
    t_fin = np.where(has2 & (p2 != EN_COURS), t2[k2c], INF)
    issue = np.full(n, "en_cours_p1", dtype=object)
    issue[i1 == PERTE_JOUR], issue[i1 == PERTE_MAX] = "echec_p1_jour", "echec_p1_max"
    for code, nom in ((REUSSITE, "reussite"), (PERTE_JOUR, "echec_p2_jour"), (PERTE_MAX, "echec_p2_max"),
                      (EN_COURS, "en_cours_p2")):
        issue[ok1 & (p2 == code)] = nom
    return i1, t1, p2, t_fin, issue


def _depart_local(sim: Simulation) -> pd.Series:
    return pd.Series(pd.to_datetime(sim.departs, utc=True).tz_convert(sim.regles.fuseau))


def challenge(sim: Simulation, ref: str = "solde", mode: str = "pessimiste", coupure: int | None = None) -> pd.DataFrame:
    """Une ligne par départ : issue de P1 et délai (jours), issue de P2, issue du challenge (`ISSUES`), délai total."""
    d = sim.departs
    i1, t1, p2, t_fin, issue = _enchainer(sim, ref, mode, coupure)
    ok1 = i1 == REUSSITE
    out = pd.DataFrame({"depart": _depart_local(sim),
                        "issue_p1": NOM_PHASE[i1],
                        "jours_p1": np.where(i1 != EN_COURS, (t1 - d) / JOUR, np.nan),
                        "issue_p2": np.where(ok1, NOM_PHASE[p2], None),
                        "issue": issue,
                        "jours_total": np.where(t_fin < INF, (t_fin - d) / JOUR, np.nan)})
    if coupure is not None:
        out = out[d < coupure].reset_index(drop=True)
    return out


def _retraits(sim: Simulation) -> pd.DataFrame:
    if sim.retraits is None:
        return pd.DataFrame({"depart": np.array([], dtype=np.int64), "t": np.array([], dtype=np.int64),
                             "montant": np.array([], dtype=float)})
    return sim.retraits


def financement(sim: Simulation, ref: str = "solde", mode: str = "pessimiste",
                coupure: int | None = None) -> pd.DataFrame:
    """Une ligne par départ d'un compte financé : fin (première rupture ; INF si aucune), cause, durée (jours), nombre
    et somme des retraits antérieurs à la rupture."""
    d, n = sim.departs, len(sim.departs)
    fin, cause = _echec(sim, ref, mode, coupure)
    r = _retraits(sim)
    rd, rt = r.depart.to_numpy(dtype=np.int64), r.t.to_numpy(dtype=np.int64)
    keep = rt < fin[rd] if len(r) else np.zeros(0, dtype=bool)
    if coupure is not None:
        keep &= rt <= coupure
    n_ret, retire = np.zeros(n, dtype=np.int64), np.zeros(n)
    np.add.at(n_ret, rd[keep], 1)
    np.add.at(retire, rd[keep], r.montant.to_numpy(dtype=float)[keep])
    out = pd.DataFrame({"depart": _depart_local(sim), "fin": fin,
                        "issue": np.where(fin < INF, NOM_PHASE[cause], "en_cours"),
                        "jours": np.where(fin < INF, (fin - d) / JOUR, np.nan), "n_retraits": n_ret, "retire": retire})
    if coupure is not None:
        out = out[d < coupure].reset_index(drop=True)
    return out


def valeur(sim_c: Simulation, sim_f: Simulation, ref: str = "solde", mode: str = "pessimiste", frais: float = 0.0054,
           part: float = 0.8, horizon_jours: float | None = None, coupure: int | None = None) -> pd.DataFrame:
    """Une ligne par départ de challenge, en fraction du capital du compte : issue du challenge, compte financé ou non,
    retraits de ce compte (avant sa rupture, dans `horizon_jours` depuis le départ du challenge, avant la coupure),
    somme reçue (frais remboursés au premier retrait + part du porteur) et valeur = reçu − frais."""
    if not np.array_equal(sim_c.departs, sim_f.departs):
        raise ValueError("valeur : challenge et compte financé sur les mêmes départs")
    d, n = sim_c.departs, len(sim_c.departs)
    _, _, _, t_fin, issue = _enchainer(sim_c, ref, mode, coupure)
    ok = issue == "reussite"
    k3 = np.searchsorted(d, np.where(ok, t_fin, d[0]), side="left")
    finance = ok & (k3 < n)
    fin_f, _ = _echec(sim_f, ref, mode, coupure)
    r = _retraits(sim_f)
    rd, rt, rm = r.depart.to_numpy(dtype=np.int64), r.t.to_numpy(dtype=np.int64), r.montant.to_numpy(dtype=float)
    lo, hi = np.searchsorted(rd, k3, side="left"), np.searchsorted(rd, k3, side="right")
    n_ret, retire = np.zeros(n, dtype=np.int64), np.zeros(n)
    for s in np.flatnonzero(finance):
        tt, mm = rt[lo[s]:hi[s]], rm[lo[s]:hi[s]]
        lim = tt < fin_f[k3[s]]
        if horizon_jours is not None:
            lim &= tt <= d[s] + int(round(horizon_jours * JOUR))
        if coupure is not None:
            lim &= tt <= coupure
        n_ret[s], retire[s] = int(lim.sum()), float(mm[lim].sum())
    recu = np.where(n_ret > 0, frais + part * retire, 0.0)
    out = pd.DataFrame({"depart": _depart_local(sim_c), "issue": issue,
                        "jours_total": np.where(t_fin < INF, (t_fin - d) / JOUR, np.nan), "finance": finance,
                        "n_retraits": n_ret, "retire": retire, "recu": recu, "valeur": recu - frais})
    if coupure is not None:
        out = out[d < coupure].reset_index(drop=True)
    return out


def suite(sim_c: Simulation, sim_f: Simulation, ref: str = "solde", mode: str = "pessimiste", frais: float = 0.0054,
          part: float = 0.8, horizon_jours: float = 365.0, coupure: int | None = None) -> pd.DataFrame:
    """EXP-D05.6bis — suite de tentatives, un seul compte à la fois : une tentative au départ, puis une nouvelle au
    premier minuit qui suit l'échec du challenge ou la rupture du compte financé. Chaque tentative coûte `frais` à son
    départ, remboursés à son premier retrait. Ne comptent que les tentatives démarrées et les retraits reçus dans
    `horizon_jours` depuis le départ (et avant la coupure) ; la suite s'arrête sur un challenge en cours ou un compte
    financé ouvert à l'horizon. Une ligne par départ, en fraction du capital du compte : valeur (somme nette reçue),
    nombre de tentatives et de comptes financés."""
    if not np.array_equal(sim_c.departs, sim_f.departs):
        raise ValueError("suite : challenge et compte financé sur les mêmes départs")
    d, n = sim_c.departs, len(sim_c.departs)
    _, t1, _, t_fin, issue = _enchainer(sim_c, ref, mode, coupure)
    ok = issue == "reussite"
    fin_c = np.where(np.isin(issue, ("echec_p1_jour", "echec_p1_max")), t1, t_fin)    # INF : challenge en cours
    fin_f, _ = _echec(sim_f, ref, mode, coupure)
    r = _retraits(sim_f)
    rd, rt, rm = r.depart.to_numpy(dtype=np.int64), r.t.to_numpy(dtype=np.int64), r.montant.to_numpy(dtype=float)
    lo, hi = np.searchsorted(rd, np.arange(n), side="left"), np.searchsorted(rd, np.arange(n), side="right")
    h = int(round(horizon_jours * JOUR))
    val, n_t, n_f = np.zeros(n), np.zeros(n, dtype=np.int64), np.zeros(n, dtype=np.int64)
    for s0 in range(n):
        lim = d[s0] + h if coupure is None else min(d[s0] + h, coupure)
        k = s0
        while k < n and d[k] <= lim:
            val[s0] -= frais
            n_t[s0] += 1
            fin = fin_c[k]
            if ok[k]:
                k3 = int(np.searchsorted(d, fin, side="left"))
                if k3 >= n or d[k3] > lim:
                    break
                n_f[s0] += 1
                tt, mm = rt[lo[k3]:hi[k3]], rm[lo[k3]:hi[k3]]
                m = (tt < fin_f[k3]) & (tt <= lim)
                if m.any():
                    val[s0] += frais + part * mm[m].sum()
                fin = fin_f[k3]
            if fin > lim:                                     # INF compris
                break
            k = max(int(np.searchsorted(d, fin, side="left")), k + 1)
    out = pd.DataFrame({"depart": _depart_local(sim_c), "valeur": val, "n_tentatives": n_t, "n_finances": n_f})
    if coupure is not None:
        out = out[d < coupure].reset_index(drop=True)
    return out


def ic_blocs(x, depart: pd.Series, n_boot: int = 2000, seed: int = 0) -> tuple[float, float]:
    """IC à 95 % de la moyenne de `x` par rééchantillonnage des mois de départ (les départs d'un même mois se
    chevauchent)."""
    x = np.asarray(x, dtype=float)
    if not len(x):
        return np.nan, np.nan
    mois = (depart.dt.year * 100 + depart.dt.month).to_numpy()
    blocs = np.unique(mois)
    somme = np.array([x[mois == m].sum() for m in blocs])
    compte = np.array([(mois == m).sum() for m in blocs])
    tir = np.random.default_rng(seed).integers(0, len(blocs), size=(n_boot, len(blocs)))
    p = somme[tir].sum(axis=1) / compte[tir].sum(axis=1)
    return float(np.quantile(p, 0.025)), float(np.quantile(p, 0.975))


def resume(out: pd.DataFrame, n_boot: int = 2000, seed: int = 0) -> dict:
    """Parts de chaque issue, réussite de P1, délais (médiane, P90) parmi les réussites, IC à 95 % de la part de
    réussite par blocs de mois de départ."""
    n = len(out)
    r = {"n_departs": n}
    for k in ISSUES:
        r[f"p_{k}"] = float((out.issue == k).mean()) if n else np.nan
    r["p_reussite_p1"] = float((out.issue_p1 == "reussite").mean()) if n else np.nan
    for nom, x in (("jours_p1", out.jours_p1[out.issue_p1 == "reussite"]),
                   ("jours_total", out.jours_total[out.issue == "reussite"])):
        x = x.to_numpy(dtype=float)
        r[f"{nom}_med"] = float(np.median(x)) if len(x) else np.nan
        r[f"{nom}_p90"] = float(np.quantile(x, 0.9)) if len(x) else np.nan
    r["ic_bas"], r["ic_haut"] = ic_blocs((out.issue == "reussite").to_numpy(dtype=float), out.depart, n_boot, seed)
    return r
