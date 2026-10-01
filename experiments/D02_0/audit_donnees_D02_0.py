"""EXP-D02.0 — audit des historiques longs, avant tout backtest (aucun signal, aucun PnL).

Usage, depuis la racine du dépôt : python experiments/D02_0/audit_donnees_D02_0.py
Écrit audit_donnees_D02_0.json et audit_donnees_D02_0.md. Aucune barre n'est corrigée, comblée ni supprimée ; aucune
barre de 2026 n'est lue au-delà du chargement (filtre immédiat).

Contrôles (définitions fixées avant le calcul) :
- intégrité, trous et sauts : `marketdata.audit.audit_bars` (chaîne de D01) ;
- par année : barres, part des créneaux attendus (crypto : cotation continue 24/7 ; or : calendrier 23/5 théorique
  en heure de New York, lundi-jeudi hors 17:00-18:00, vendredi avant 17:00, dimanche dès 18:00, sans jours fériés),
  barres hors calendrier, barres sans transaction (volume nul) et barres plates (high = low) ;
- crypto : suites de barres sans transaction d'au moins 4 h (Bitstamp sert des barres plates pendant ses arrêts) ;
- BTC : valeurs identiques à la série du dépôt (bitstamp_btcusd_30m.csv) sur 2020-2025, barre par barre ;
- or : valeurs identiques à la série de D01 (histdata_xauusd_30m.csv) sur 2020-2025 ; horloge : pause quotidienne
  lue en heure de New York semaine par semaine (lundi-jeudi), par année (contrôle de fuseau de D01) ; plus longues
  suites de créneaux du calendrier sans barre (fêtes ou trous de la source) ;
- AVAX : couverture depuis la cotation, trous, barres d'un seul quart d'heure (méta).
"""
from __future__ import annotations

import json
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "src"))

from marketdata.audit import audit_bars  # noqa: E402
from utils.data_loader import load_ohlc, meta_path  # noqa: E402

RAW = ROOT / "data" / "raw"
HOLDOUT = pd.Timestamp("2026-01-01", tz="UTC")
BAR = pd.Timedelta(minutes=30)
IDLE_MIN_BARS = 8                                       # suite sans transaction signalée : au moins 4 h
SERIES = {
    "BTC": {"csv": RAW / "bitstamp_btcusd_30m_2013_2025.csv", "ref": RAW / "bitstamp_btcusd_30m.csv",
            "kind": "24/7", "nom": "BTC/USD Bitstamp"},
    "XAU": {"csv": RAW / "histdata_xauusd_30m_2009_2025.csv", "ref": RAW / "histdata_xauusd_30m.csv",
            "kind": "23/5", "nom": "CFD or XAU/USD HistData"},
    "AVAX": {"csv": RAW / "coinbase_avaxusd_30m.csv", "kind": "24/7", "nom": "AVAX/USD Coinbase"},
}
INTEGRITE = ("doublons", "desordre", "prix_non_positifs", "incoherences_ohlc")


def load(path: Path) -> pd.DataFrame:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")                 # trous signalés par load_ohlc : mesurés ici
        df = load_ohlc(path)
    return df[df.time < HOLDOUT].reset_index(drop=True)


def calendar_23_5(first: pd.Timestamp, last: pd.Timestamp) -> pd.DatetimeIndex:
    """Créneaux de 30 min du calendrier 23/5 théorique (heure de New York), sans jours fériés, dans [first, last]."""
    slots = pd.date_range(first, last, freq="30min", tz="UTC")
    ny = slots.tz_convert("America/New_York")
    tod = ny.hour + ny.minute / 60.0
    dow = ny.dayofweek
    keep = (((dow <= 3) & ~((tod >= 17) & (tod < 18))) | ((dow == 4) & (tod < 17)) | ((dow == 6) & (tod >= 18)))
    return slots[keep]


def expected_slots(kind: str, first: pd.Timestamp, last: pd.Timestamp) -> pd.DatetimeIndex:
    if kind == "24/7":
        return pd.date_range(first, last, freq="30min", tz="UTC")
    return calendar_23_5(first, last)


def per_year(df: pd.DataFrame, kind: str) -> dict:
    t = df.time
    out = {}
    for y in range(t.iat[0].year, t.iat[-1].year + 1):
        a = max(pd.Timestamp(f"{y}-01-01", tz="UTC"), t.iat[0])          # année partielle : bornée par la série
        b = min(pd.Timestamp(f"{y}-12-31 23:30", tz="UTC"), t.iat[-1])
        exp = expected_slots(kind, a, b)
        g = df[(t >= a) & (t <= b)]
        inside = g.time.isin(exp)
        row = {"barres": int(len(g)), "attendues": int(len(exp)), "part_presente": float(inside.sum() / len(exp)),
               "hors_calendrier": int((~inside).sum()), "plates": int((g.high == g.low).sum())}
        if kind == "24/7":
            row["volume_nul"] = int((g.volume <= 0).sum())
        out[y] = row
    return out


def idle_runs(df: pd.DataFrame, min_bars: int = IDLE_MIN_BARS) -> list[dict]:
    """Suites de barres consécutives (pas de 30 min) sans transaction, d'au moins `min_bars` barres."""
    v0 = (df.volume <= 0).to_numpy()
    cont = np.r_[False, (df.time.diff().iloc[1:] == BAR).to_numpy()]
    start = v0 & ~(np.r_[False, v0[:-1]] & cont)
    ids = np.cumsum(start)
    runs = []
    for k in np.unique(ids[v0]):
        idx = np.flatnonzero(v0 & (ids == k))
        if len(idx) >= min_bars:
            runs.append({"debut": str(df.time.iat[idx[0]]), "fin": str(df.time.iat[idx[-1]]), "barres": int(len(idx)),
                         "heures": len(idx) / 2.0})
    return runs


def missing_runs(df: pd.DataFrame, kind: str, top: int = 12) -> list[dict]:
    """Plus longues suites de créneaux attendus sans barre (calendrier de `expected_slots`)."""
    exp = expected_slots(kind, df.time.iat[0], df.time.iat[-1])
    miss = ~exp.isin(pd.DatetimeIndex(df.time))
    if not miss.any():
        return []
    pos = np.flatnonzero(miss)
    brk = np.r_[True, np.diff(pos) > 1]
    ids = np.cumsum(brk)
    runs = []
    for k in np.unique(ids):
        p = pos[ids == k]
        runs.append({"debut": str(exp[p[0]]), "fin": str(exp[p[-1]]), "creneaux": int(len(p))})
    runs.sort(key=lambda r: -r["creneaux"])
    return runs[:top]


def pause_by_year(t: pd.Series) -> dict:
    """Contrôle de fuseau de D01 (`session_profile`), par année : heures sans barre, lundi-jeudi, heure de New York."""
    ny = t.dt.tz_convert("America/New_York")
    wd = ny[ny.dt.dayofweek <= 3]
    weeks = {}
    for wk, g in wd.groupby(wd.dt.tz_localize(None).dt.to_period("W-SUN")):
        cnt = g.dt.hour.value_counts().reindex(range(24), fill_value=0)
        weeks[wk.start_time] = tuple(int(h) for h in range(24) if cnt[h] == 0)
    w = pd.Series(weeks, dtype=object)
    out = {}
    for y, g in w.groupby(w.index.year):
        odd = g[g.map(lambda x: x != (17,))]
        out[int(y)] = {"semaines": int(len(g)), "pause_17h_exactement": int(g.map(lambda x: x == (17,)).sum()),
                       "pause_17h_et_autres_heures": int(g.map(lambda x: 17 in x and x != (17,)).sum()),
                       "sans_pause_17h": int(g.map(lambda x: 17 not in x).sum()),
                       "exemples_autres": {str(k.date()): list(v) for k, v in odd.head(6).items()}}
    return out


def clock_by_year(df: pd.DataFrame) -> dict:
    """Horloge sans recours à la pause (ajouté après l'audit : la pause de 17:00 NY est en partie cotée en 2009-2018).
    Par année et saison de New York (EDT / EST) : ouverture du dimanche et dernière barre du vendredi (mode, heure de
    New York) ; |rendement| moyen, lundi-vendredi, des barres de 07:30, 08:00 et 08:30 NY (annonces américaines de
    08:30), barres précédées d'une barre à 30 min. Une erreur d'une heure déplacerait l'ouverture à 17:00 ou 19:00 et
    le pic de 08:30 vers 07:30 ou 09:30."""
    ny = df.time.dt.tz_convert("America/New_York")
    edt = ny.map(lambda x: bool(x.dst()))
    ret = pd.Series(np.abs(np.log(df.close / df.close.shift(1))).to_numpy() * 1e4, index=df.index)
    ok = (df.time.diff() == BAR) & (ny.dt.dayofweek <= 4)
    hm = ny.dt.strftime("%H:%M")
    out = {}
    for (y, e), idx in ny.groupby([ny.dt.year, edt]).groups.items():
        g = ny.loc[idx]
        sun, fri = g[g.dt.dayofweek == 6], g[g.dt.dayofweek == 4]
        so = sun.groupby(sun.dt.date).min().dt.strftime("%H:%M") if len(sun) else pd.Series(dtype=object)
        fl = fri.groupby(fri.dt.date).max().dt.strftime("%H:%M") if len(fri) else pd.Series(dtype=object)
        r = {k: float(ret[idx][ok[idx] & (hm[idx] == k)].mean()) for k in ("07:30", "08:00", "08:30")}
        out[f"{y} {'EDT' if e else 'EST'}"] = {
            "ouverture_dimanche": f"{so.mode().iat[0]} ({pc((so == so.mode().iat[0]).mean(), 0)})" if len(so) else None,
            "derniere_barre_vendredi": f"{fl.mode().iat[0]} ({pc((fl == fl.mode().iat[0]).mean(), 0)})" if len(fl) else None,
            "r_bps": r, "rapport_0830_0730": r["08:30"] / r["07:30"]}
    return out


def identity(new: pd.DataFrame, ref: pd.DataFrame, first: str, last: str) -> dict:
    a0, b0 = pd.Timestamp(first, tz="UTC"), pd.Timestamp(last, tz="UTC")
    a = new[(new.time >= a0) & (new.time < b0)].set_index("time")
    b = ref[(ref.time >= a0) & (ref.time < b0)].set_index("time")
    common = a.index.intersection(b.index)
    cols = ["open", "high", "low", "close", "volume"]
    x, y = a.loc[common, cols].to_numpy(), b.loc[common, cols].to_numpy()
    return {"periode": f"{first} → {last} (exclu)", "barres_nouvelle": int(len(a)), "barres_reference": int(len(b)),
            "communes": int(len(common)), "identiques": int((x == y).all(axis=1).sum()),
            "ecart_max": {c: float(np.abs(x[:, i] - y[:, i]).max()) if len(common) else None
                          for i, c in enumerate(cols)},
            "seulement_nouvelle": int(len(a.index.difference(b.index))),
            "seulement_reference": int(len(b.index.difference(a.index)))}


def audit_series(key: str, s: dict) -> dict:
    if not s["csv"].exists():
        return {"absent": s["csv"].name}
    df = load(s["csv"])
    meta = json.loads(meta_path(s["csv"]).read_text(encoding="utf-8"))
    a = audit_bars(df)
    out = {"fichier": s["csv"].name, "sha256": meta["sha256"], "source": meta["source"],
           "premiere": a["premiere"], "derniere": a["derniere"], "n_barres": a["n_barres"],
           "integrite": {k: a[k] for k in INTEGRITE}, "trous": a["trous"], "sauts": a["sauts"],
           "annees": per_year(df, s["kind"]), "manques_plus_longs": missing_runs(df, s["kind"])}
    if s["kind"] == "24/7":
        runs = idle_runs(df)
        out["suites_sans_transaction"] = {
            "n": len(runs), "par_annee": {int(y): int(sum(1 for r in runs if r["debut"][:4] == str(y)))
                                          for y in sorted({int(r["debut"][:4]) for r in runs})},
            "plus_longues": sorted(runs, key=lambda r: -r["barres"])[:12]}
    if key == "XAU":
        out["pause_new_york"] = pause_by_year(df.time)
        ny = df.time.dt.tz_convert("America/New_York")
        p = ny[(ny.dt.dayofweek <= 3) & (ny.dt.hour == 17)]
        out["barres_pause_17h_new_york"] = {int(y): {k: int(v) for k, v in g.dt.strftime("%H:%M").value_counts()
                                                     .sort_index().items()} for y, g in p.groupby(p.dt.year)}
        out["horloge"] = clock_by_year(df)
        out["barres_moins_de_30_minutes"] = meta.get("n_barres_moins_de_30_minutes")
        out["doublons_exacts_supprimes"] = {a_["archive"][-8:-4]: a_["doublons_exacts_supprimes"]["n"]
                                            for a_ in meta["archives"]}
    if key == "AVAX":
        out["barres_un_seul_quart_d_heure"] = meta.get("n_barres_un_seul_quart_d_heure")
    if s.get("ref") and s["ref"].exists():
        out["identite_2020_2025"] = identity(df, load(s["ref"]), "2020-01-01", "2026-01-01")
    return out


def pc(x: float, d: int = 1) -> str:
    return f"{100 * x:.{d}f} %".replace(".", ",")


def write_md(res: dict) -> None:
    L = ["# EXP-D02.0 — audit des historiques longs (avant tout backtest)", "",
         "Généré par `audit_donnees_D02_0.py`. Aucune barre corrigée, comblée ni supprimée ; 2026 non lu.", ""]
    L += ["## Synthèse", "", "| Série | Fichier | Première | Dernière | Barres | SHA-256 | Intégrité | Trous |",
          "|---|---|---|---|---|---|---|---|"]
    for k, r in res.items():
        if "absent" in r:
            L.append(f"| {k} | {r['absent']} | — | — | — | — | absent | — |")
            continue
        integ = "aucun défaut" if not any(r["integrite"].values()) else ", ".join(
            f"{a} {b}" for a, b in r["integrite"].items() if b)
        tr = r["trous"]
        longest = f", plus long {tr['plus_longs'][0]['duree_h']:.1f} h" if tr["plus_longs"] else ""
        L.append(f"| {k} | `{r['fichier']}` | {r['premiere'][:16]} | {r['derniere'][:16]} | {r['n_barres']} | "
                 f"`{r['sha256'][:12]}…` | {integ} | {tr['n']} ({tr['barres_manquantes']} barres){longest} |")
    for k, r in res.items():
        if "absent" in r:
            continue
        L += ["", f"## {k} — {SERIES[k]['nom']}", "", "| Année | Barres | Attendues | Présentes | Hors calendrier | "
              "Plates | Volume nul |", "|---|---|---|---|---|---|---|"]
        for y, a in r["annees"].items():
            L.append(f"| {y} | {a['barres']} | {a['attendues']} | {pc(a['part_presente'])} | {a['hors_calendrier']} | "
                     f"{a['plates']} ({pc(a['plates'] / max(a['barres'], 1))}) | "
                     f"{a.get('volume_nul', '—')}{'' if 'volume_nul' not in a else ' (' + pc(a['volume_nul'] / max(a['barres'], 1)) + ')'} |")
        if "identite_2020_2025" in r:
            i = r["identite_2020_2025"]
            L += ["", f"Identité avec la série de référence sur {i['periode']} : {i['identiques']} barres identiques sur "
                  f"{i['communes']} communes ({i['barres_nouvelle']} contre {i['barres_reference']} barres) ; écart "
                  f"maximal {max(v for v in i['ecart_max'].values() if v is not None):g}."]
        if "suites_sans_transaction" in r:
            st = r["suites_sans_transaction"]
            L += ["", f"Suites sans transaction ≥ 4 h : {st['n']} (par année : {st['par_annee']}). Plus longues :", ""]
            L += [f"- {x['debut'][:16]} → {x['fin'][:16]} : {x['heures']:g} h" for x in st["plus_longues"][:8]]
        if "pause_new_york" in r:
            L += ["", "Pause quotidienne (lundi-jeudi, heure de New York), semaines par année :", "",
                  "| Année | Semaines | Pause à 17 h seule | 17 h et autres heures | Sans pause à 17 h | Exemples |",
                  "|---|---|---|---|---|---|"]
            for y, p in r["pause_new_york"].items():
                ex = "; ".join(f"{d} {v}" for d, v in list(p["exemples_autres"].items())[:3])
                L.append(f"| {y} | {p['semaines']} | {p['pause_17h_exactement']} | {p['pause_17h_et_autres_heures']} | "
                         f"{p['sans_pause_17h']} | {ex} |")
        if "barres_pause_17h_new_york" in r:
            L += ["", "Barres lundi-jeudi dans la pause 17:00-18:00 NY (créneaux 17:00 / 17:30), par année : " +
                  "; ".join(f"{y} {v.get('17:00', 0)}/{v.get('17:30', 0)}" for y, v in
                            r["barres_pause_17h_new_york"].items()) + "."]
        if "horloge" in r:
            L += ["", "Horloge sans la pause (heure de New York) : ouverture du dimanche, dernière barre du vendredi, "
                  "|rendement| moyen des barres de 07:30, 08:00 et 08:30 (bps) :", "",
                  "| Année, saison | Ouverture dimanche | Dernière barre vendredi | 07:30 | 08:00 | 08:30 | 08:30 / 07:30 |",
                  "|---|---|---|---|---|---|---|"]
            for k, h in r["horloge"].items():
                rb = h["r_bps"]
                L.append(f"| {k} | {h['ouverture_dimanche']} | {h['derniere_barre_vendredi']} | {rb['07:30']:.1f} | "
                         f"{rb['08:00']:.1f} | {rb['08:30']:.1f} | {h['rapport_0830_0730']:.2f} |")
        if r["manques_plus_longs"]:
            L += ["", "Plus longues suites de créneaux attendus sans barre :", ""]
            L += [f"- {x['debut'][:16]} → {x['fin'][:16]} : {x['creneaux']} créneaux ({x['creneaux'] / 2:g} h)"
                  for x in r["manques_plus_longs"][:8]]
        sa = r["sauts"]["plus_grands_rendements"][:5]
        L += ["", "Plus grands rendements de clôture à clôture (bps) : " +
              "; ".join(f"{x['time'][:16]} {x['bps']:.0f}" for x in sa) + "."]
    (HERE / "audit_donnees_D02_0.md").write_text("\n".join(L) + "\n", encoding="utf-8")


def main() -> None:
    res = {k: audit_series(k, s) for k, s in SERIES.items()}
    (HERE / "audit_donnees_D02_0.json").write_text(json.dumps(res, ensure_ascii=False, indent=1, default=str),
                                                   encoding="utf-8")
    write_md(res)
    print((HERE / "audit_donnees_D02_0.md").read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
