"""Sous-ensemble du paquet `labeling` de #KAKALMAN (D36) : `costs`, copié à l'identique pour l'Étape C (EXP-C01).

    net = ret_gross_bps − cost_bps          (`net_label` ; coût aller-retour, en bps du notionnel)

Empreinte : experiments/C01/manifest_copie_C01_sha256.txt. Ce fichier-ci n'est pas une copie : l'`__init__` d'origine
importe des modules non copiés (`target`, `weights`).
"""
from labeling.costs import COST_COLUMNS, CostModel, apply_costs, net_label

__all__ = ["COST_COLUMNS", "CostModel", "apply_costs", "net_label"]
