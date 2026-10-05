"""EXP-D05.4 — issues d'un challenge en deux phases, à partir d'une `Simulation`.

- Une phase (objectif k) se termine au premier de ses événements : échec (perte du jour ou perte totale) ou réussite. À
  instant égal, l'échec l'emporte ; si les deux planchers sont franchis au même état, la cause est le plus haut (le
  premier atteint quand l'équité baisse).
- P2 démarre au premier minuit local qui suit la réussite de P1, sur un compte neuf : son issue est celle de la phase 2
  du départ de ce minuit.
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


def issue_phase(sim: Simulation, k: int, ref: str = "solde", mode: str = "pessimiste",
                coupure: int | None = None) -> tuple[np.ndarray, np.ndarray]:
    """(issue, instant) de la phase d'objectif k pour chaque départ."""
    to = sim.t_objectif[k].copy()
    tx = sim.t_perte_max[mode].copy()
    tj = sim.t_perte_jour[(ref, mode)].copy()
    if coupure is not None:
        for a in (to, tx, tj):
            a[a > coupure] = INF
    rb = sim.ref_breche[(ref, mode)]
    jour_d_abord = (tj < tx) | ((tj == tx) & (rb - sim.regles.perte_jour > 1.0 - sim.regles.perte_max))
    t_echec = np.minimum(tj, tx)
    echec = (t_echec < INF) & (t_echec <= to)
    issue = np.where(echec, np.where(jour_d_abord, PERTE_JOUR, PERTE_MAX), np.where(to < INF, REUSSITE, EN_COURS))
    t = np.where(echec, t_echec, np.where(to < INF, to, INF))
    return issue.astype(np.int8), t.astype(np.int64)


def challenge(sim: Simulation, ref: str = "solde", mode: str = "pessimiste", coupure: int | None = None) -> pd.DataFrame:
    """Une ligne par départ : issue de P1 et délai (jours), issue de P2, issue du challenge (`ISSUES`), délai total."""
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
    out = pd.DataFrame({"depart": pd.to_datetime(d, utc=True).tz_convert(sim.regles.fuseau),
                        "issue_p1": NOM_PHASE[i1],
                        "jours_p1": np.where(i1 != EN_COURS, (t1 - d) / JOUR, np.nan),
                        "issue_p2": np.where(ok1, NOM_PHASE[p2], None),
                        "issue": issue,
                        "jours_total": np.where(t_fin < INF, (t_fin - d) / JOUR, np.nan)})
    if coupure is not None:
        out = out[d < coupure].reset_index(drop=True)
    return out


def resume(out: pd.DataFrame, n_boot: int = 2000, seed: int = 0) -> dict:
    """Parts de chaque issue, réussite de P1, délais (médiane, P90) parmi les réussites, IC à 95 % de la part de
    réussite par rééchantillonnage des mois de départ (les départs d'un même mois se chevauchent)."""
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
    r["ic_bas"] = r["ic_haut"] = np.nan
    if n:
        mois = (out.depart.dt.year * 100 + out.depart.dt.month).to_numpy()
        y = (out.issue == "reussite").to_numpy(dtype=float)
        blocs = np.unique(mois)
        somme = np.array([y[mois == m].sum() for m in blocs])
        compte = np.array([(mois == m).sum() for m in blocs])
        tir = np.random.default_rng(seed).integers(0, len(blocs), size=(n_boot, len(blocs)))
        p = somme[tir].sum(axis=1) / compte[tir].sum(axis=1)
        r["ic_bas"], r["ic_haut"] = float(np.quantile(p, 0.025)), float(np.quantile(p, 0.975))
    return r
