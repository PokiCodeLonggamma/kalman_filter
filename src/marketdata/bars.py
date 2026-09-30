"""Agrégation exacte de sous-barres (bougies de 1 ou 15 min) en barres de 30 min alignées sur :00 et :30 UTC."""
from __future__ import annotations

import pandas as pd

BAR = pd.Timedelta(minutes=30)


def aggregate_30m(sub: pd.DataFrame) -> pd.DataFrame:
    """open de la première sous-barre, plus haut des high, plus bas des low, close de la dernière, somme des volumes ;
    `n_sub` : sous-barres présentes. Une barre sans aucune sous-barre n'existe pas (trou, jamais comblé)."""
    c = sub.sort_values("time").reset_index(drop=True)
    g = c.groupby(c.time.dt.floor(BAR), sort=True)
    out = pd.DataFrame({"open": g.open.first(), "high": g.high.max(), "low": g.low.min(), "close": g.close.last(),
                        "volume": g.volume.sum(), "n_sub": g.size()})
    out.index.name = "time"
    out = out.reset_index()
    out.insert(1, "timestamp", out.time.map(lambda t: int(t.timestamp())).astype("int64"))
    return out
