"""EXP-B01 — catégorisation cinématique et asymétrie d'excursion (Étape B ; aucun PnL, aucun seuil optimisé).

    from categorization import excursion_table, barrier_table, add_derived, assign_families, summarize

Les excursions (`excursions.py`) sont a posteriori et partent de l'entrée exécutable open[t+1], en ATR14(t).
Les descripteurs (`families.py`) sont causaux : ce sont ceux d'A01, plus `retrace_ratio`.
"""
from categorization.excursions import (BARRIER_HORIZON, BARRIERS, HORIZONS, OUTCOMES, barrier_key, barrier_table,
                                       excursion_table)
from categorization.families import (DESCRIPTORS, FAMILY_LABELS, add_derived, assign_families, bin_descriptor,
                                     cluster_bootstrap, summarize, tail_sum, timing_drift, wilson)

__all__ = ["HORIZONS", "BARRIERS", "BARRIER_HORIZON", "OUTCOMES", "barrier_key", "excursion_table", "barrier_table",
           "DESCRIPTORS", "FAMILY_LABELS", "add_derived", "assign_families", "bin_descriptor", "summarize", "wilson",
           "timing_drift", "tail_sum", "cluster_bootstrap"]
