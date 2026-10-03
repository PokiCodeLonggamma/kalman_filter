"""Réserve 2026 (hold-out, D43) : scellée par défaut dans tout le dépôt.

Levée seulement à l'intérieur d'un bloc explicite `with levee("motif"):` (EXP-D04, décision du porteur du 2026-10-03,
« Lève la restriction ») : aucune variable d'environnement, aucun autre interrupteur. Hors du bloc, les gardes
restent celles d'origine : `estimand.bars.check_no_holdout`, `strategy.load_asset` (fin au 2026-01-01) et les
téléchargeurs Bitstamp, Coinbase et HistData refusent toute date ≥ 2026-01-01. Les autres téléchargeurs (Alpaca,
FRED, Saxo) ne consultent pas l'interrupteur et restent scellés.
"""
from __future__ import annotations

from contextlib import contextmanager

import pandas as pd

from config import ML_HOLDOUT_START

DEBUT = pd.Timestamp(ML_HOLDOUT_START, tz="UTC")
_MOTIFS: list[str] = []


@contextmanager
def levee(motif: str):
    """Lève la réserve pendant le bloc ; le motif (expérience) est obligatoire. Rescellée à la sortie, même sur erreur."""
    if not isinstance(motif, str) or not motif.strip():
        raise ValueError("levée de la réserve 2026 : motif obligatoire")
    _MOTIFS.append(motif.strip())
    try:
        yield
    finally:
        _MOTIFS.pop()


def scellee() -> bool:
    return not _MOTIFS


def motif() -> str | None:
    """Motif de la levée en cours, None si la réserve est scellée."""
    return _MOTIFS[-1] if _MOTIFS else None


def exiger_levee(quoi: str) -> None:
    """Erreur « réserve 2026 » si la réserve est scellée (message commun à toutes les gardes)."""
    if scellee():
        raise ValueError(f"réserve 2026 : {quoi} (réserve scellée ; levée seulement dans `reserve.levee`)")
