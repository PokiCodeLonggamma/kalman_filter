"""Coûts de transaction injectables (D36) : aucune valeur par défaut, aucune valeur codée en dur.

    cost_bps = 2 · fee_bps + spread_bps + 2 · slippage_bps          (aller-retour, en bps du notionnel)

Un événement = 1 ordre d'entrée + 1 ordre de sortie, d'où les facteurs 2 sur les frais et le glissement, et un
spread complet (une demi-fourchette par ordre). Sous Q-G Flat, un retournement = sortie du trade n + entrée du trade
n+1 : deux ordres réels, chacun porté par son événement, donc aucun double comptage.

`ret_net_bps = ret_gross_bps − cost_bps` est l'approximation linéaire de `(1 + r)(1 − c) − 1` ; le terme croisé
`r·c` vaut au plus 0,2 bps pour |r| ≤ 2 000 bps et c = 10 bps (docs/P4_labeling.md §8).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Union

import numpy as np
import pandas as pd

#: Composante de coût : scalaire (bps), ou fonction `labels -> tableau par événement` (coût variable dans le
#: temps ou par actif : grille tarifaire datée, spread observé...).
CostComponent = Union[float, Callable[[pd.DataFrame], "np.ndarray | pd.Series"]]
COST_COLUMNS = ["fee_bps", "spread_bps", "slippage_bps", "cost_bps", "ret_net_bps", "y_net"]


@dataclass(frozen=True)
class CostModel:
    """Modèle de coût aller-retour. Les trois composantes sont obligatoires et conservées séparément."""
    fee_bps: CostComponent
    spread_bps: CostComponent
    slippage_bps: CostComponent

    def components(self, labels: pd.DataFrame) -> pd.DataFrame:
        """Une ligne par événement : `fee_bps`, `spread_bps`, `slippage_bps`, `cost_bps`."""
        n = len(labels)
        out = {}
        for name in ("fee_bps", "spread_bps", "slippage_bps"):
            comp = getattr(self, name)
            v = comp(labels) if callable(comp) else comp
            v = np.broadcast_to(np.asarray(v, dtype=float), (n,)).copy()
            if not np.isfinite(v).all() or (v < 0).any():
                raise ValueError(f"CostModel.{name} : valeurs finies et >= 0 exigées")
            out[name] = v
        out["cost_bps"] = 2.0 * out["fee_bps"] + out["spread_bps"] + 2.0 * out["slippage_bps"]
        return pd.DataFrame(out, index=labels.index)


def net_label(ret_gross_bps, cost_bps) -> tuple[np.ndarray, np.ndarray]:
    """(ret_net_bps, y_net) avec y_net = 1 si ret_net_bps > 0 (strict), 0 sinon, NaN si le rendement est indéfini.

    Forme pure, utilisée par `apply_costs` et par les analyses de sensibilité à un coût total donné.
    """
    r = np.asarray(ret_gross_bps, dtype=float) - np.asarray(cost_bps, dtype=float)
    y = np.where(np.isnan(r), np.nan, (r > 0).astype(float))
    return r, y


def apply_costs(labels: pd.DataFrame, cost_model: CostModel) -> pd.DataFrame:
    """Ajoute les composantes de coût, `ret_net_bps` et `y_net` à la table de `label_events` (copie).

    Un événement censuré garde `ret_net_bps = y_net = NaN` : jamais 0 ni 1.
    """
    if not isinstance(cost_model, CostModel):
        raise TypeError("apply_costs : cost_model doit être un CostModel explicite")
    out = labels.drop(columns=[c for c in COST_COLUMNS if c in labels.columns]).copy()
    comp = cost_model.components(out)
    out[comp.columns] = comp
    out["ret_net_bps"], out["y_net"] = net_label(out["ret_gross_bps"], out["cost_bps"])
    return out
