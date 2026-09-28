"""Tests de `labeling.costs` repris à l'identique de #KAKALMAN `tests/test_labeling.py` (D36).

Seuls les 2 tests qui n'appellent pas `labeling.label_events` (module non copié) sont repris, sans modification.
Empreinte du fichier d'origine : experiments/C01/manifest_copie_C01_sha256.txt.
"""
import numpy as np
import pandas as pd

from config import CANONICAL_COST
from labeling import CostModel, net_label


def test_rendement_net_nul_etiquete_0():
    r, y = net_label([10.0, 10.000001, 9.99, np.nan, -3.0], 10.0)
    np.testing.assert_array_equal(y[:3], [0.0, 1.0, 0.0])
    assert np.isnan(y[3]) and np.isnan(r[3]) and y[4] == 0.0


def test_cout_canonique_5_bps():
    """D36 : hypothèse canonique de recherche = 2·1,5 + 1,0 + 2·0,5 = 5 bps, injectée explicitement."""
    assert CANONICAL_COST == {"fee_bps": 1.5, "spread_bps": 1.0, "slippage_bps": 0.5}
    comp = CostModel(**CANONICAL_COST).components(pd.DataFrame(index=range(3)))
    assert (comp.cost_bps == 5.0).all()
