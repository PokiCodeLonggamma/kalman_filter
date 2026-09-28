"""Filtre de Kalman 2 états d'AKF-TSO v2.1 (Pine l. 5-24, 55-160).

État X = [x0 niveau ($), x1 vitesse ($/barre)], F = [[1,1],[0,1]], H = [1,0].
Reproduit le baseline tel quel, y compris ses écarts à un Kalman standard :
  - E1 : diagonale de P remise à 1 avant chaque prédiction (l. 62-63 hors `var`) — `reset_P_diag=True` (D16) ;
  - E2 : Q = [[Q1, Q1·Q2], [Q2·Q1, Q2]] · Q_scale ;
  - E3 : R = R0 · (σ₂₀ / SMA₁₀₀(σ₂₀))^γ en $², R = R0 tant que la SMA n'existe pas (D14).
Options inactives du Pine non implémentées : Myers-Tapley, R estimé, debug (l. 9-10, 21-23).
Les opérations suivent l'oracle P0 (experiments/p0/akf_replique_pine.py) : parité mesurée ≤ 5e-10 (docs/P2_parite.md).
Note numérique : σ₂₀ = pandas rolling std (ddof = 0), comme l'oracle. La somme directe de ta.stdev en diffère
d'au plus 1,25e-6 sur R aux paramètres par défaut (0 écart discret) — écart commun à l'oracle, documenté en P2.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from indicator._bounds import check_range

VOL_SMA = 100   # ta.sma(realized_vol_g, 100), codé en dur l. 82


@dataclass(frozen=True)
class KalmanParams:
    R0: float = 100.0            # Base Measurement Noise R0 (minval 1)
    q1: float = 0.01             # Process Noise Q1 (minval 0.0001)
    q2: float = 0.01             # Process Noise Q2 (minval 0.0001)
    q_scale: float = 1.0         # Q scale (0.1 .. 10)
    gamma: float = 0.5           # Volatility Sensitivity gamma (0 .. 3)
    vol_lookback: int = 20       # Volatility Lookback (minval 5)
    reset_P_diag: bool = True    # E1, comportement du baseline (False : variante pine/experimental/)

    def __post_init__(self):
        check_range("R0", self.R0, lo=1.0)
        check_range("q1", self.q1, lo=1e-4)
        check_range("q2", self.q2, lo=1e-4)
        check_range("q_scale", self.q_scale, lo=0.1, hi=10.0)
        check_range("gamma", self.gamma, lo=0.0, hi=3.0)
        check_range("vol_lookback", self.vol_lookback, lo=5, integer=True)


KALMAN_COLUMNS = ["x0", "x1", "x0_pred", "x1_pred", "innov", "S", "nis", "K0", "K1",
                  "P00", "P01", "P11", "Ppred00", "Ppred01", "Ppred11", "R"]


def adaptive_R(close: np.ndarray, p: KalmanParams = KalmanParams()) -> np.ndarray:
    """R_used de la l. 93-97 : ta.stdev population (ddof = 0) du niveau de prix, SMA100, puissance γ."""
    close = np.asarray(close, dtype=float)
    n = len(close)
    R = np.full(n, float(p.R0))
    if p.gamma <= 0:
        return R
    rv = pd.Series(close).rolling(p.vol_lookback).std(ddof=0).to_numpy()
    av = pd.Series(rv).rolling(VOL_SMA).mean().to_numpy()
    ok = (np.arange(n) > p.vol_lookback) & ~np.isnan(av)
    ok[ok] = av[ok] > 0
    R[ok] = p.R0 * np.power(rv[ok] / av[ok], p.gamma)
    return R


def run_kalman(close: np.ndarray, p: KalmanParams = KalmanParams()) -> pd.DataFrame:
    """Boucle barre par barre à la clôture confirmée. Renvoie une colonne par grandeur de KALMAN_COLUMNS."""
    c = np.asarray(close, dtype=float)
    n = len(c)
    R_all = adaptive_R(c, p)
    F = np.array([[1., 1.], [0., 1.]])
    H = np.array([[1., 0.]])
    Q = np.array([[p.q1 * p.q_scale, p.q1 * p.q2 * p.q_scale],
                  [p.q2 * p.q1 * p.q_scale, p.q2 * p.q_scale]])
    P = np.eye(2)
    X = np.array([c[0], 0.])                      # barstate.isfirst : X = [close, 0]
    out = {k: np.full(n, np.nan) for k in KALMAN_COLUMNS}
    for i in range(n):
        if p.reset_P_diag:
            P[0, 0] = 1.0
            P[1, 1] = 1.0
        R = R_all[i]
        xp = F @ X
        Pp = F @ P @ F.T + Q
        S = (H @ Pp @ H.T)[0, 0] + R
        K = (Pp @ H.T) / S
        innov = c[i] - xp[0]
        X = xp + K[:, 0] * innov
        IKH = np.eye(2) - K @ H
        P = IKH @ Pp @ IKH.T + (K * R) @ K.T      # forme de Joseph
        out["x0"][i], out["x1"][i] = X[0], X[1]
        out["x0_pred"][i], out["x1_pred"][i] = xp[0], xp[1]
        out["innov"][i], out["S"][i] = innov, S
        out["nis"][i] = innov * innov / S if S > 0 else np.nan
        out["K0"][i], out["K1"][i] = K[0, 0], K[1, 0]
        out["P00"][i], out["P01"][i], out["P11"][i] = P[0, 0], P[0, 1], P[1, 1]
        out["Ppred00"][i], out["Ppred01"][i], out["Ppred11"][i] = Pp[0, 0], Pp[0, 1], Pp[1, 1]
        out["R"][i] = R
    return pd.DataFrame(out)
