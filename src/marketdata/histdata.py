"""Bougies d'une minute HistData.com (ASCII « Generic », gratuites, sans compte) agrégées en barres de 30 min
(EXP-D01 : CFD sur l'or XAUUSD et CFD sur le pétrole brut WTI, WTIUSD).

- Téléchargement : une archive par année civile, par le formulaire public de la page de l'année (jeton `tk` lu sur
  la page, puis POST sur get.php). HistData ne publie pas d'empreinte : le SHA-256 de chaque archive est consigné.
- Format : « AAAAMMJJ HHMMSS;open;high;low;close;volume » ; prix construits sur le bid des ticks (FAQ) ; volume
  toujours nul ; une minute sans cotation est absente.
- Horodatage : la FAQ annonce un EST fixe (UTC−5), mais l'audit d'EXP-D01 montre une horloge qui suit l'heure d'été
  européenne : étiquette = heure d'un serveur EET/EEST moins 7 h, soit UTC−5 en hiver européen et UTC−4 de fin mars
  à fin octobre. Preuve : avec UTC = étiquette + 5 h, la pause quotidienne de l'or et du WTI (17:00-18:00 heure de
  New York) tombe à 21:00 UTC seulement pendant les semaines où New York est déjà à l'heure d'été et l'Europe pas
  encore, et à 22:00 UTC le reste de l'été. Conversion retenue : heure serveur = étiquette + 7 h, localisée en
  Europe/Athens (EET/EEST), puis UTC ; la pause tombe alors à 17:00 heure de New York toute l'année (contrôle de
  l'audit). Les valeurs des barres ne changent pas (décalage d'heures entières), seuls leurs horodatages.
- Doublons : HistData répète à l'identique une heure par an (00:00-00:59 UTC le lundi qui suit la fin de l'heure
  d'été européenne, artefact de conversion horaire ; continuité des prix vérifiée, aucune heure manquante). Les
  doublons exacts sont supprimés et comptés dans le méta ; des doublons de valeurs différentes arrêtent tout.
- Agrégation exacte en barres de 30 min alignées sur :00 et :30 UTC (`marketdata.bars.aggregate_30m`).
- Le fournisseur amont (courtier) et, pour le WTI, la règle de roulement du CFD ne sont pas publiés : limites à
  documenter et à caractériser par l'audit.
- Réserve 2026 : aucune année ≥ 2026 n'est demandée, aucune barre ≥ 2026-01-01 n'est écrite.
"""
from __future__ import annotations

import hashlib
import http.cookiejar
import io
import json
import re
import time
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path

import pandas as pd

from marketdata.bars import aggregate_30m
from utils.data_loader import meta_path

PAGE = "https://www.histdata.com/download-free-forex-historical-data/?/ascii/1-minute-bar-quotes/{pair}/{year}"
GET_PHP = "https://www.histdata.com/get.php"
HOLDOUT = pd.Timestamp("2026-01-01", tz="UTC")
SERVER_SHIFT = pd.Timedelta(hours=7)                  # étiquette HistData + 7 h = heure du serveur source
SERVER_TZ = "Europe/Athens"                           # EET (UTC+2) / EEST (UTC+3), règles européennes
USER_AGENT = "Mozilla/5.0 (akf-tso-research)"
FIELDS = ("tk", "date", "datemonth", "platform", "timeframe", "fxpair")
CSV_COLUMNS = ["time", "timestamp", "open", "high", "low", "close", "volume"]


class Session:
    """Session HTTP avec cookies : GET d'une page, POST d'un formulaire. Une pause suit chaque requête."""

    def __init__(self, pause: float = 1.0):
        self.opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
        self.pause = pause

    def _open(self, req: urllib.request.Request) -> bytes:
        with self.opener.open(req, timeout=180) as r:
            data = r.read()
        time.sleep(self.pause)
        return data

    def get(self, url: str) -> str:
        return self._open(urllib.request.Request(url, headers={"User-Agent": USER_AGENT})).decode("utf-8", "replace")

    def post(self, url: str, fields: dict, referer: str) -> bytes:
        body = urllib.parse.urlencode(fields).encode()
        return self._open(urllib.request.Request(url, data=body, headers={"User-Agent": USER_AGENT,
                                                                          "Referer": referer}))


def form_fields(html: str, pair: str, year: int) -> dict:
    """Champs du formulaire de téléchargement de la page annuelle ; vérifie la paire et l'année."""
    found = {}
    for k, v in re.findall(r'name="(' + "|".join(FIELDS) + r')"[^>]*value="([^"]*)"', html):
        found.setdefault(k, v)
    missing = [k for k in FIELDS if k not in found]
    if missing:
        raise ValueError(f"HistData {pair} {year} : champs absents du formulaire {missing}")
    if found["fxpair"].upper() != pair.upper() or found["date"] != str(year) or found["timeframe"] != "M1":
        raise ValueError(f"HistData : formulaire inattendu {found}")
    return found


def fetch_year(pair: str, year: int, cache: Path, session=None) -> tuple[Path, str]:
    """Archive annuelle (cache réutilisé s'il contient le CSV attendu) et son SHA-256."""
    if pd.Timestamp(f"{year}-01-01", tz="UTC") >= HOLDOUT:
        raise ValueError(f"réserve 2026 : l'année {year} n'est pas téléchargeable")
    pair = pair.upper()
    path = Path(cache) / f"HISTDATA_COM_ASCII_{pair}_M1{year}.zip"
    name = f"DAT_ASCII_{pair}_M1_{year}.csv"
    if not (path.exists() and zipfile.is_zipfile(path) and name in zipfile.ZipFile(path).namelist()):
        session = session or Session()
        page = PAGE.format(pair=pair.lower(), year=year)
        data = session.post(GET_PHP, form_fields(session.get(page), pair, year), page)
        if not zipfile.is_zipfile(io.BytesIO(data)) or name not in zipfile.ZipFile(io.BytesIO(data)).namelist():
            raise ValueError(f"HistData {pair} {year} : réponse sans archive {name}")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    return path, hashlib.sha256(path.read_bytes()).hexdigest()


def label_to_utc(label: pd.Series) -> pd.Series:
    """Étiquette HistData (naïve) → UTC : + 7 h, localisée en EET/EEST, convertie en UTC. Les heures ambiguës ou
    inexistantes du serveur (nuit du samedi au dimanche des changements d'heure, marché fermé) arrêtent tout."""
    return (label + SERVER_SHIFT).dt.tz_localize(SERVER_TZ, ambiguous="raise", nonexistent="raise").dt.tz_convert("UTC")


def parse_m1(text: str) -> pd.DataFrame:
    """Lignes « AAAAMMJJ HHMMSS;o;h;l;c;v » → bougies d'une minute, time en UTC (`label_to_utc`)."""
    df = pd.read_csv(io.StringIO(text), sep=";", header=None, names=["label", "open", "high", "low", "close",
                                                                        "volume"], dtype={"label": str})
    out = pd.DataFrame({"time": label_to_utc(pd.to_datetime(df.label, format="%Y%m%d %H%M%S"))})
    for c in ("open", "high", "low", "close", "volume"):
        out[c] = df[c].astype(float)
    return out


def read_year(path: Path, pair: str, year: int) -> pd.DataFrame:
    with zipfile.ZipFile(path) as z:
        return parse_m1(z.read(f"DAT_ASCII_{pair.upper()}_M1_{year}.csv").decode("ascii"))


def drop_exact_duplicates(m1: pd.DataFrame, who: str) -> tuple[pd.DataFrame, dict]:
    """Supprime les minutes répétées à l'identique (même horodatage, mêmes OHLC) ; toute autre répétition arrête."""
    dup = m1.time.duplicated(keep=False)
    if not dup.any():
        return m1, {"n": 0, "dates": []}
    if m1[dup].groupby("time")[["open", "high", "low", "close"]].nunique().gt(1).any().any():
        raise ValueError(f"{who} : minutes dupliquées de valeurs différentes")
    extra = m1.time.duplicated(keep="first")
    info = {"n": int(extra.sum()), "dates": sorted({str(d) for d in m1.time[extra].dt.date})}
    return m1[~extra].reset_index(drop=True), info


def build_histdata_csv(pair: str, first_year: int, last_year: int, out_csv: Path, cache: Path,
                       meta_extra: dict | None = None, session=None) -> dict:
    """Archives annuelles [first_year, last_year], agrégation en 30 min, CSV au schéma de `load_ohlc` et `.meta.json`."""
    if last_year >= HOLDOUT.year:
        raise ValueError(f"réserve 2026 : l'année {last_year} n'est pas téléchargeable")
    frames, files = [], []
    for y in range(first_year, last_year + 1):
        path, sha = fetch_year(pair, y, cache, session)
        m1, dup = drop_exact_duplicates(read_year(path, pair, y), f"{pair} {y}")
        frames.append(m1)
        files.append({"archive": path.name, "sha256": sha, "minutes": len(m1), "doublons_exacts_supprimes": dup})
    m1 = pd.concat(frames, ignore_index=True).sort_values("time").reset_index(drop=True)
    if m1.time.duplicated().any():
        raise ValueError(f"{pair} : minutes dupliquées entre archives annuelles")
    m1 = m1[m1.time < HOLDOUT]                      # étiquettes du 31/12 au soir tombant en 2026 UTC : exclues
    bars = aggregate_30m(m1)
    out_csv = Path(out_csv)
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    bars[CSV_COLUMNS].to_csv(out_csv, index=False)
    meta = {"source": "histdata.com", "url_page": PAGE.format(pair=pair.lower(), year="<année>"), "pair": pair.lower(),
            "granularite_source": "M1 (bougies d'une minute, bid)", "step_s": 1800,
            "extracted_at_utc": pd.Timestamp.now(tz="UTC").isoformat(),
            "extracted_at_origin": "heure du téléchargement (années civiles complètes, antérieures à 2026)",
            "n_rows": len(bars), "first": str(bars.time.iat[0]), "last": str(bars.time.iat[-1]),
            "minutes_sources": int(len(m1)), "n_barres_moins_de_30_minutes": int((bars.n_sub < 30).sum()),
            "sha256": hashlib.sha256(out_csv.read_bytes()).hexdigest(), "archives": files, **(meta_extra or {})}
    meta_path(out_csv).write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
    return meta
