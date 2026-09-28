"""(B) Excursions extrêmes sur la vie du trade de référence (P6.5, D43 ; convention P1 validée par Aymeric).

Pour un événement d'entrée `open[entry_bar]` (= open[b+1]) et de sortie `open[exit_bar]` (signal opposé) :
- chemin = high / low des barres détenues `[entry_bar, exit_bar − 1]` ;
- `mfe_bps` = excursion favorable maximale en bps bruts (Long : max high ; Short : min low), ≥ 0 ;
- `mae_bps` = excursion adverse maximale (Long : min low ; Short : max high), ≤ 0 ;
- `h_mfe`, `h_mae` = barre d'atteinte (0 = barre d'entrée), première occurrence ; `f_mfe`, `f_mae` = même moment en
  fraction de la durée ;
- `ret_gross_bps` = rendement brut à la sortie (recalculé, doit égaler celui de P4) ; le signe net = brut − 5 bps.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

BPS = 1e4
EXCURSION_COLUMNS = ["mfe_bps", "mae_bps", "h_mfe", "h_mae", "f_mfe", "f_mae", "duration_bars", "ret_gross_bps",
                     "mfe_avant_mae"]


def excursions(bars: pd.DataFrame, events: pd.DataFrame) -> pd.DataFrame:
    op = bars["open"].to_numpy(dtype=float)
    hi = bars["high"].to_numpy(dtype=float)
    lo = bars["low"].to_numpy(dtype=float)
    e = events["entry_bar"].to_numpy(dtype=np.int64)
    x = events["exit_bar"].to_numpy(dtype=np.int64)
    side = events["side"].to_numpy(dtype=np.int64)
    if (x <= e).any() or (x >= len(op)).any():
        raise ValueError("excursions : sortie hors des barres de développement ou antérieure à l'entrée")
    rows = np.empty((len(e), len(EXCURSION_COLUMNS)))
    for i in range(len(e)):
        p0, a, b, s = op[e[i]], e[i], x[i], side[i]
        fav = (hi[a:b] / p0 - 1.0) * BPS if s == 1 else (1.0 - lo[a:b] / p0) * BPS
        adv = (lo[a:b] / p0 - 1.0) * BPS if s == 1 else (1.0 - hi[a:b] / p0) * BPS
        k_f, k_a = int(np.argmax(fav)), int(np.argmin(adv))
        d = b - a
        rows[i] = [fav[k_f], adv[k_a], k_f, k_a, k_f / d, k_a / d, d, s * (op[b] / p0 - 1.0) * BPS, k_f < k_a]
    out = pd.DataFrame(rows, columns=EXCURSION_COLUMNS, index=events.index)
    for c in ("h_mfe", "h_mae", "duration_bars"):
        out[c] = out[c].astype(np.int64)
    out["mfe_avant_mae"] = out["mfe_avant_mae"].astype(bool)
    return out
