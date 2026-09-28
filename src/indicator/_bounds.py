"""Validation des paramètres, calquée sur les minval / maxval des inputs du Pine (l. 5-31)."""
from __future__ import annotations


def check_range(name: str, value, lo=None, hi=None, integer: bool = False) -> None:
    if integer and (isinstance(value, bool) or int(value) != value):
        raise ValueError(f"{name} doit être entier (reçu {value!r})")
    if lo is not None and value < lo:
        raise ValueError(f"{name} = {value!r} < minval {lo} du Pine")
    if hi is not None and value > hi:
        raise ValueError(f"{name} = {value!r} > maxval {hi} du Pine")
