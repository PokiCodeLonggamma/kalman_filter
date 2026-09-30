"""EXP-D01.7 — acquisition des séries du test de portabilité 24/5 (décision du porteur, 2026-10-01).

Usage, depuis la racine du dépôt : python experiments/D01_7/donnees_D01_7.py [--force]
Une série déjà construite (CSV et .meta.json présents) n'est pas reconstruite, sauf avec --force. Écrit
data/raw/<source>_<paire>_30m.csv (ignoré par git) et son .meta.json (versionné). La réserve 2026 n'est jamais
téléchargée. Aucune série n'est substituée à une autre : un actif sans source conforme est déclaré bloqué.

- GBPJPY : le porteur demande Dukascopy ou une autre source gratuite fiable (historique 2020-2025).
  - Dukascopy (2026-10-01) : le flux datafeed.dukascopy.com répond HTTP 429 dès la deuxième requête et renvoie à sa
    page d'export, qui réserve l'historique massif à un bucket AWS « Requester Pays » (cfg-public-proper-wallaby,
    eu-west-1 ; identifiants AWS obligatoires, accès anonyme impossible). Action du porteur requise ; blocage non
    contourné.
  - Source retenue, déclarée : HistData.com, bougies d'une minute gratuites (bid), sans compte, agrégées en 30 min ;
    même chaîne que l'or de D01 (`marketdata.histdata`, horloge convertie en UTC). Validée avant tout backtest par
    recoupement avec les taux de midi de New York de la Réserve fédérale (FRED, série H.10).
- NQ, RTY, CL, HG : futures continus demandés sur QuantConnect (mapping OPEN_INTEREST, BACKWARDS_RATIO, profondeur 0).
  QuantConnect exige un compte ; ses données ne sont utilisables que dans son cloud (aucun export, Object Store sans
  téléchargement ; téléchargement local sous licence payante, réservé à LEAN). Bloqués en attente du porteur.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "src"))

from marketdata import build_fred_csv, build_histdata_csv  # noqa: E402

spec = importlib.util.spec_from_file_location("donnees_D01", ROOT / "experiments" / "D01" / "donnees_D01.py")
D01D = importlib.util.module_from_spec(spec)
spec.loader.exec_module(D01D)

RAW, CACHE = D01D.RAW, D01D.CACHE
FORCE = "--force" in sys.argv
D01D.FORCE = FORCE

GBPJPY_META = {
    **D01D.COMMUN_HISTDATA,
    "actif": "GBPJPY",
    "instrument": "GBP/JPY au comptant (TradingView : FX:GBPJPY, OANDA:GBPJPY)",
    "nature": "cotation OTC au comptant d'un courtier forex, compilée par HistData.com",
    "ticker": "GBPJPY (HistData.com, ASCII M1)",
    "continuite": "sans objet : cotation au comptant, sans échéance",
    "rolls": "sans objet ; le coût de portage (swap) n'est pas dans les prix",
    "ajustements": "aucun",
    "horaires": "marché des changes OTC, du dimanche 17:00 au vendredi 17:00 heure de New York, sans pause quotidienne "
                "annoncée ; vérifiés par l'audit",
    "sources_ecartees": "Dukascopy (2026-10-01 : HTTP 429 dès la deuxième requête sur datafeed.dukascopy.com, export "
                        "massif réservé au bucket AWS « Requester Pays » cfg-public-proper-wallaby, identifiants AWS "
                        "obligatoires : action du porteur requise, non contourné) ; OANDA (compte requis) ; Yahoo "
                        "(intrajournalier limité aux 60 derniers jours)",
    "decision": "porteur, 2026-10-01 : Dukascopy ou une autre source gratuite fiable ; HistData déclarée, validée par "
                "recoupement avec les taux H.10 de la Réserve fédérale avant tout backtest",
}
FRED_ROLE = ("référence externe de l'audit de GBPJPY : taux de change de midi à New York de la Réserve fédérale (H.10) ; "
             "GBPJPY de référence = DEXUSUK × DEXJPUS ; aucun calcul de stratégie")
FRED_SERIES = {"DEXUSUK": "dollars américains pour une livre sterling", "DEXJPUS": "yens pour un dollar américain"}


def main() -> None:
    out = RAW / "histdata_gbpjpy_30m.csv"
    if not D01D.built(out):
        meta = build_histdata_csv("GBPJPY", 2020, 2025, out, CACHE / "histdata", GBPJPY_META)
        print(f"GBPJPY : {meta['n_rows']} barres, {meta['first']} → {meta['last']}, SHA-256 {meta['sha256'][:12]}…")
    for sid, unit in FRED_SERIES.items():
        csv = RAW / f"fred_{sid.lower()}.csv"
        if not D01D.built(csv):
            meta = build_fred_csv(sid, "2019-12-01", "2025-12-31", csv, {"role": FRED_ROLE, "unite": unit})
            print(f"FRED {sid} : {meta['n_valeurs']} valeurs, {meta['first']} → {meta['last']}")
    print("NQ, RTY, CL, HG : bloqués — accès QuantConnect ou autre source à décider par le porteur")


if __name__ == "__main__":
    main()
