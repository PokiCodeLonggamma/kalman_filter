"""EXP-D02.0 — acquisition des historiques longs (décisions du porteur du 2026-10-01).

Usage, depuis la racine du dépôt : python experiments/D02_0/donnees_D02_0.py [--force]
Une série déjà construite (CSV et .meta.json présents) n'est pas reconstruite, sauf avec --force. Écrit
data/raw/<fichier>.csv (ignoré par git) et son .meta.json (versionné). La réserve 2026 n'est jamais téléchargée.

- BTC/USD : Bitstamp, barres natives de 30 min, années 2013 à 2025, par notre téléchargeur (`marketdata.bitstamp`)
  plutôt que par copie du fichier de NewKalman (décision du porteur : provenance documentée). Même carnet et même
  requête que la série 2020-2026 du dépôt : valeurs identiques attendues sur 2020-2025 (contrôle de l'audit).
  2012 est écarté : 79 % des barres de mars 2012 sans transaction (sonde du 2026-10-01).
- Or : CFD XAU/USD, HistData M1, années 2009 à 2025, même chaîne que la série 2020-2025 (`marketdata.histdata` ;
  archives 2020-2025 relues depuis le cache). L'horloge EET/EEST − 7 h, établie sur 2020-2025, est revérifiée année
  par année par l'audit.
- AVAX/USD (question du porteur : ajouter une autre crypto, comme AVAX) : Coinbase Exchange, carnet spot AVAX-USD,
  coté depuis le 2021-09-30, même chaîne que SOL (bougies de 15 min agrégées en 30 min). Sources écartées (sondes du
  2026-10-01) : Binance.US AVAXUSD (coté depuis le 2021-11-18, aucune bougie en 2024, quasi aucune transaction en
  2025) ; Bitstamp AVAX/USD (coté depuis le 2022-03-08) ; Binance AVAX/USDT (cotation en USDT, écartée pour SOL).
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "src"))

from marketdata import build_coinbase_csv, build_histdata_csv  # noqa: E402
from marketdata.bitstamp import build_bitstamp_csv  # noqa: E402

RAW = ROOT / "data" / "raw"
CACHE = RAW / "_cache"
FORCE = "--force" in sys.argv


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


D01 = _load("donnees_D01", ROOT / "experiments" / "D01" / "donnees_D01.py")

BTC_META = {
    "actif": "BTC",
    "instrument": "BTC/USD, carnet spot de Bitstamp (TradingView : BITSTAMP:BTCUSD)",
    "nature": "spot crypto, cotation en dollars américains",
    "ticker": "btcusd (Bitstamp)",
    "continuite": "sans objet : instrument spot, série unique",
    "rolls": "sans objet",
    "ajustements": "aucun",
    "timezone": "UTC (ouverture des barres Bitstamp)",
    "horaires": "cotation continue 24/7 ; les interruptions sont des maintenances ou incidents de la plateforme",
    "construction_barres": "barres natives de 30 min de l'API OHLC publique de Bitstamp (step 1800), telles que "
                           "servies ; une barre sans transaction est servie plate au dernier prix, volume nul, et "
                           "gardée",
    "couverture_demandee": "2013-01-01 → 2025-12-31 ; 2026 non téléchargé",
    "sources_ecartees": "copie du fichier de NewKalman (même carnet, construction non documentée ; décision du "
                        "porteur) ; Bitstamp 2012 (79 % des barres de mars 2012 sans transaction)",
    "decision": "porteur, 2026-10-01 : historique long de BTC/USD, d'abord pour le rétro-test de RE-1 figée "
                "(2013-2019), puis pour D02 ; retéléchargé par notre script",
}

XAU_META = {
    **D01.XAU_META,
    "couverture_demandee": "années 2009 à 2025 ; 2026 non téléchargé",
    "timezone": D01.XAU_META["timezone"] + " ; revérifiée année par année sur 2009-2019 par l'audit de D02.0",
    "decision": "porteur, 2026-09-30 : CFD sur l'or (nom TradingView), source libre ; 2026-10-01 : historique long, "
                "d'abord pour le rétro-test de RE-1 figée (2009-2019), puis pour D02",
}

AVAX_META = {
    "actif": "AVAX",
    "instrument": "AVAX/USD, carnet spot de Coinbase Exchange (TradingView : COINBASE:AVAXUSD)",
    "nature": "spot crypto, cotation en dollars américains",
    "ticker": "AVAX-USD (Coinbase Exchange)",
    "continuite": "sans objet : instrument spot, série unique",
    "rolls": "sans objet",
    "ajustements": "aucun",
    "timezone": "UTC (début des bougies Coinbase)",
    "horaires": "cotation continue 24/7 ; les interruptions sont des maintenances ou incidents de la plateforme",
    "construction_barres": D01.SOL_META["construction_barres"].replace("(en SOL)", "(en AVAX)"),
    "couverture_demandee": "2021-09 → 2025-12 ; AVAX-USD est coté sur Coinbase depuis le 2021-09-30 ; 2026 non "
                           "téléchargé",
    "sources_ecartees": "Binance.US AVAXUSD (coté depuis le 2021-11-18, aucune bougie en 2024, quasi aucune "
                        "transaction en 2025) ; Bitstamp AVAX/USD (coté depuis le 2022-03-08) ; Binance AVAX/USDT "
                        "(cotation en USDT, écartée par le porteur pour SOL)",
    "decision": "question du porteur, 2026-10-01 : ajouter une autre crypto à l'univers, comme AVAX ; données "
                "seulement, aucun backtest",
}


def built(csv: Path) -> bool:
    done = csv.exists() and csv.with_name(csv.stem + ".meta.json").exists() and not FORCE
    if done:
        print(f"{csv.name} : déjà construit (--force pour reconstruire)")
    return done


def main() -> None:
    out = RAW / "bitstamp_btcusd_30m_2013_2025.csv"
    if not built(out):
        m = build_bitstamp_csv("btcusd", 2013, 2025, out, CACHE / "bitstamp", BTC_META)
        print(f"BTC : {m['n_rows']} barres, {m['first']} → {m['last']}, SHA-256 {m['sha256'][:12]}…", flush=True)
    out = RAW / "histdata_xauusd_30m_2009_2025.csv"
    if not built(out):
        m = build_histdata_csv("XAUUSD", 2009, 2025, out, CACHE / "histdata", XAU_META)
        print(f"XAU : {m['n_rows']} barres, {m['first']} → {m['last']}, SHA-256 {m['sha256'][:12]}…", flush=True)
    out = RAW / "coinbase_avaxusd_30m.csv"
    if not built(out):
        m = build_coinbase_csv("AVAX-USD", "2021-09", "2025-12", out, CACHE / "coinbase", AVAX_META)
        print(f"AVAX : {m['n_rows']} barres, {m['first']} → {m['last']}, SHA-256 {m['sha256'][:12]}…", flush=True)


if __name__ == "__main__":
    main()
