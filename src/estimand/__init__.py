"""Sous-ensemble du paquet `estimand` de #KAKALMAN (P6.5, D43 et D48), copié à l'identique pour l'Étape C (EXP-C01).

- `bars` : barres de développement tronquées avant 2026, contrôle de la réserve (`check_no_holdout`) ;
- `excursions` : constante `BPS`, dont dépend `stoploss` ;
- `stoploss` : trade avec ou sans stop (`apply_stop`), stratégie native stop-and-reverse (`simulate_strategy`),
  capital valorisé (`equity_curve`) et drawdown (`drawdown_stats`).

Empreintes : experiments/C01/manifest_copie_C01_sha256.txt. Ce fichier-ci n'est pas une copie : l'`__init__`
d'origine importe des modules non copiés (`association`, `horizons`, `payoff`).
"""
from estimand.bars import HOLDOUT, check_no_holdout, load_bars_dev, load_events_dev
from estimand.excursions import BPS, EXCURSION_COLUMNS, excursions

__all__ = ["HOLDOUT", "check_no_holdout", "load_bars_dev", "load_events_dev", "BPS", "EXCURSION_COLUMNS", "excursions"]
