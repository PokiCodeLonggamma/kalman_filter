"""EXP-D01 — acquisition des séries des actifs de transfert (décision du porteur, 2026-09-30).

Usage, depuis la racine du dépôt : python experiments/D01/donnees_D01.py
Écrit data/raw/<source>_<paire>_30m.csv (ignoré par git) et son .meta.json (versionné). La réserve 2026 n'est jamais
téléchargée. Aucune série n'est substituée à une autre : un actif sans source conforme est déclaré bloqué.

- SOL : SOL/USD (consigne du porteur : SOL/USD et non SOL/USDT). Coinbase Exchange, carnet spot SOL-USD (TradingView :
  COINBASE:SOLUSD), API publique sans clé ; barres de 30 min agrégées exactement depuis les bougies natives de 15 min.
  Coté depuis le 2021-06-17 : aucune place en USD liquide et accessible ne couvre 2020 (FTX a disparu ; Binance.US
  SOLUSD est troué de mi-2023 à février 2025, puis quasi inactif ; Bitstamp SOL/USD n'existe qu'à partir de 2022-2023).
- XAU et WTI : CFD (consigne du porteur : CFD sur l'or et CFD sur le pétrole brut WTI, noms TradingView XAUUSD et
  USOIL). HistData.com, bougies d'une minute gratuites (bid), fournisseur amont non divulgué ; horodatage converti en
  UTC selon l'heure d'été européenne (`marketdata.histdata.label_to_utc`, établi par l'audit).
  Dukascopy, d'abord visé, refuse les accès automatisés (HTTP 429 « Bot blocked ») et réserve l'export massif à un
  bucket AWS « Requester Pays » : blocage non contourné. Alpaca ne cote ni l'or au comptant ni le WTI (seulement des
  ETF, qui seraient des proxys) ; OANDA exige un compte. HistData ne publie WTIUSD que jusqu'au 2023-12-01 : le WTI
  est bloqué avant backtest (couverture inférieure à 2020-2025), décision au porteur.
- Référence externe de l'audit du WTI : prix spot WTI Cushing quotidien de l'EIA (FRED, DCOILWTICO). Elle ne sert à
  aucun calcul de stratégie.
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "src"))

from marketdata import build_coinbase_csv, build_fred_csv, build_histdata_csv  # noqa: E402

RAW = ROOT / "data" / "raw"
CACHE = RAW / "_cache"

SOL_META = {
    "actif": "SOL",
    "instrument": "SOL/USD, carnet spot de Coinbase Exchange (TradingView : COINBASE:SOLUSD)",
    "nature": "spot crypto, cotation en dollars américains",
    "ticker": "SOL-USD (Coinbase Exchange)",
    "continuite": "sans objet : instrument spot, série unique",
    "rolls": "sans objet",
    "ajustements": "aucun",
    "timezone": "UTC (début des bougies Coinbase)",
    "horaires": "cotation continue 24/7 ; les interruptions sont des maintenances ou incidents de la plateforme",
    "construction_barres": "agrégation exacte des bougies natives de 15 min (granularité 900 s) en barres de 30 min "
                           "alignées sur :00 et :30 UTC : open de la première, plus haut, plus bas, close de la "
                           "dernière, somme des volumes (en SOL) ; time = ouverture de la barre ; une barre sans "
                           "transaction est un trou, jamais comblé",
    "couverture_demandee": "2021-01 → 2025-12 ; SOL-USD est coté sur Coinbase depuis le 2021-06-17 ; 2026 non "
                           "téléchargé",
    "sources_ecartees": "Binance SOL/USDT (cotation en USDT, écartée par le porteur) ; Binance.US SOLUSD (trou de "
                        "mi-2023 à février 2025, puis quasi aucune transaction) ; Bitstamp SOL/USD (coté depuis "
                        "2022-2023 seulement) ; Alpaca (provenance des données de 2021-2022 non documentée)",
    "decision": "porteur, 2026-09-30 : SOL/USD et non SOL/USDT ; source libre",
}

COMMUN_HISTDATA = {
    "prix": "bid (FAQ HistData : barres construites sur le bid des ticks)",
    "timezone": "étiquettes HistData converties en UTC : la FAQ annonce un EST fixe, mais l'horloge suit l'heure "
                "d'été européenne (serveur EET/EEST moins 7 h : UTC−5 en hiver européen, UTC−4 de fin mars à fin "
                "octobre) ; établi par l'audit D01 (pause quotidienne à 17:00-18:00 heure de New York toute l'année "
                "après conversion)",
    "horaires": "marché OTC 24 h sur 24, 5 jours sur 7, pause quotidienne d'une heure calée sur New York ; vérifiés "
                "par l'audit",
    "construction_barres": "agrégation exacte des bougies d'une minute en barres de 30 min alignées sur :00 et :30 "
                           "UTC ; time = ouverture de la barre ; volume absent de la source (écrit nul) ; une barre "
                           "sans minute cotée est un trou, jamais comblé",
    "couverture_demandee": "années 2020 à 2025 ; 2026 non téléchargé",
    "sources_ecartees": "Dukascopy (accès automatisés refusés, HTTP 429 « Bot blocked » ; export massif réservé à un "
                        "bucket AWS « Requester Pays ») ; Alpaca (ETF seulement : proxys) ; OANDA (compte requis)",
    "limite": "fournisseur amont (courtier) non divulgué par HistData",
}

XAU_META = {
    "actif": "XAU",
    "instrument": "CFD sur l'or au comptant, XAU/USD (TradingView : XAUUSD, p. ex. OANDA:XAUUSD, FOREXCOM:XAUUSD)",
    "nature": "CFD / cotation OTC au comptant d'un courtier forex, compilée par HistData.com",
    "ticker": "XAUUSD (HistData.com, ASCII M1)",
    "continuite": "sans objet : cotation au comptant, sans échéance",
    "rolls": "sans objet ; le coût de portage (swap) d'un CFD au comptant n'est pas dans les prix",
    "ajustements": "aucun",
    "decision": "porteur, 2026-09-30 : CFD sur l'or (nom TradingView), source libre",
    **COMMUN_HISTDATA,
}

WTI_META = {
    "actif": "WTI",
    "instrument": "CFD sur le pétrole brut WTI, WTI/USD (TradingView : USOIL, p. ex. TVC:USOIL, OANDA:WTICOUSD)",
    "nature": "CFD d'un courtier sur le contrat à terme NYMEX WTI (CL), compilé par HistData.com",
    "ticker": "WTIUSD (HistData.com, ASCII M1)",
    "continuite": "non publiée par la source ; caractérisée par l'audit (écart au spot WTI Cushing quotidien de "
                  "l'EIA, FRED DCOILWTICO)",
    "rolls": "non publiés par la source ; sauts de roulement recherchés par l'audit",
    "ajustements": "aucun appliqué",
    "decision": "porteur, 2026-09-30 : CFD sur le pétrole brut WTI (nom TradingView), source libre",
    **COMMUN_HISTDATA,
    "couverture_demandee": "années 2020 à 2025 ; HistData ne publie WTIUSD que jusqu'au 2023-12-01 (aucun fichier "
                           "pour 2024 et 2025 : jeton de téléchargement vide) ; couverture obtenue 2020-01 → 2023-12-01",
    "statut": "BLOQUÉ avant backtest : couverture 2020-2023 inférieure à la condition 2020-2025 du porteur ; roulements "
              "du CFD non documentés par la source (audit)",
}

FRED_META = {
    "role": "référence externe de l'audit du CFD WTI (prix spot WTI Cushing de l'EIA, quotidien, en dollars par "
            "baril) ; aucun calcul de stratégie",
}


def main() -> None:
    meta = build_coinbase_csv("SOL-USD", "2021-01", "2025-12", RAW / "coinbase_solusd_30m.csv", CACHE / "coinbase",
                              SOL_META)
    print(f"SOL : {meta['n_rows']} barres, {meta['first']} → {meta['last']}, SHA-256 {meta['sha256'][:12]}…")
    for pair, last, m in (("XAUUSD", 2025, XAU_META), ("WTIUSD", 2023, WTI_META)):
        meta = build_histdata_csv(pair, 2020, last, RAW / f"histdata_{pair.lower()}_30m.csv", CACHE / "histdata", m)
        print(f"{m['actif']} : {meta['n_rows']} barres, {meta['first']} → {meta['last']}, "
              f"SHA-256 {meta['sha256'][:12]}…")
    meta = build_fred_csv("DCOILWTICO", "2019-12-01", "2025-12-31", RAW / "fred_dcoilwtico.csv", FRED_META)
    print(f"FRED DCOILWTICO : {meta['n_valeurs']} valeurs, {meta['first']} → {meta['last']}")


if __name__ == "__main__":
    main()
