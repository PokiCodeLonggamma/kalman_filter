"""EXP-D05.1 — mesure descriptive de la grille de profil (note `experiments/D05_1/profil_actifs_D05_1.md`, §5), sans
RE-1 ni coût, sur des barres de 30 min telles que servies (time, open, high, low, close ; aucun trou comblé).

Conventions :
- ATR14 de Wilder (`anatomy.causal.atr_wilder`), connu à la clôture de t ; ATR_bps = ATR14 / close · 10⁴ ;
- fenêtres disjointes de H = 26 barres après une amorce de 100 barres : barre t, entrée à l'ouverture de t + 1, sortie à
  l'ouverture de t + 27 (horizon de RE-1, compté en barres de la série) ; z26 = (open[t + 27] − open[t + 1]) / ATR14(t) ;
- repère gaussien : marche aléatoire à volatilité constante, cotation continue ; ATR ≈ E[high − low] = 2·√(2/π)·σ d'une
  barre, donc z26 ~ N(0, s²) avec s = √26 / (2·√(2/π)) ≈ 3,2 ; fréquence des deux sens pour 1 000 fenêtres ;
- état calme : ATR_bps(t) sous sa médiane glissante sur 365 jours (fenêtre (t − 365 j, t], causale) ;
- coupure : plus de 30 min entre deux barres consécutives ; gap = |open − close précédent| / ATR14 de la barre
  précédente ;
- indépendance : clôtures quotidiennes (dernière clôture du jour UTC) jointes sur les jours communs, puis rendements.
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd

from anatomy.causal import atr_wilder

H, AMORCE = 26, 100
SEUILS = (5, 10, 15, 20)
QS = (2, 6, 13, 26)
PAS = pd.Timedelta("30min")
GRAND = 10                                      # |z26| ≥ 10 : « grande expansion » des lectures conditionnelles


def atr(bars: pd.DataFrame) -> np.ndarray:
    return atr_wilder(bars.high, bars.low, bars.close)


def fenetres(n: int, h: int = H, amorce: int = AMORCE) -> np.ndarray:
    """Barres t des fenêtres disjointes : t = amorce, amorce + h, … tant que l'ouverture de t + h + 1 existe."""
    return np.arange(amorce, n - h - 1, h)


def z_fenetres(bars: pd.DataFrame, atr_, t: np.ndarray, h: int = H) -> np.ndarray:
    o = bars.open.to_numpy(dtype=float)
    return (o[t + h + 1] - o[t + 1]) / np.asarray(atr_, dtype=float)[t]


def frequences(z, ans: float, seuils=SEUILS) -> dict:
    """Pour chaque seuil k : fenêtres à z ≥ k (haut) et z ≤ −k (bas), total pour 1 000 fenêtres et par an."""
    z = np.asarray(z, dtype=float)
    z = z[np.isfinite(z)]
    out = {}
    for k in seuils:
        haut, bas = int((z >= k).sum()), int((z <= -k).sum())
        out[f"haut_{k}"], out[f"bas_{k}"] = haut, bas
        out[f"pour_mille_{k}"] = 1000.0 * (haut + bas) / len(z) if len(z) else np.nan
        out[f"par_an_{k}"] = (haut + bas) / ans
    return out


def repere_gaussien(k: float, h: int = H) -> float:
    """Fenêtres à |z| ≥ k pour 1 000, sous une marche gaussienne à volatilité constante (cotation continue)."""
    s = math.sqrt(h) / (2 * math.sqrt(2 / math.pi))
    return 1000.0 * math.erfc(k / s / math.sqrt(2))


def variance_ratio(close, q: int) -> float:
    """Var(somme de q rendements logarithmiques consécutifs, chevauchants) / (q · Var(rendement d'une barre))."""
    r = np.diff(np.log(np.asarray(close, dtype=float)))
    r = r[np.isfinite(r)]
    m = r.mean()
    s = np.convolve(r, np.ones(q), "valid")
    return float(np.mean((s - q * m) ** 2) / (q * np.mean((r - m) ** 2)))


def efficacite(close, t: np.ndarray, h: int = H) -> np.ndarray:
    """|close[t + h] − close[t]| / Σ |pas de clôture à clôture| sur les barres t + 1 à t + h."""
    c = np.asarray(close, dtype=float)
    cum = np.concatenate(([0.0], np.cumsum(np.abs(np.diff(c)))))
    chemin = cum[t + h] - cum[t]
    with np.errstate(invalid="ignore", divide="ignore"):
        return np.where(chemin > 0, np.abs(c[t + h] - c[t]) / chemin, np.nan)


def sous_mediane(valeurs, temps, fenetre: str = "365D") -> np.ndarray:
    """Vrai si la valeur est sous la médiane glissante de la fenêtre temporelle (t − fenetre, t], présent inclus."""
    s = pd.Series(np.asarray(valeurs, dtype=float), index=pd.DatetimeIndex(temps))
    return (s < s.rolling(fenetre).median()).to_numpy()


def gaps(bars: pd.DataFrame, atr_, pas: pd.Timedelta = PAS) -> pd.DataFrame:
    """Une ligne par coupure (plus de `pas` depuis la barre précédente) : heure, taille du gap en ATR14 de la barre
    précédente, durée de la coupure en heures."""
    dt = bars.time.diff()
    i = np.flatnonzero((dt > pas).to_numpy())
    o, c, a = bars.open.to_numpy(dtype=float), bars.close.to_numpy(dtype=float), np.asarray(atr_, dtype=float)
    return pd.DataFrame({"time": bars.time.iloc[i].reset_index(drop=True), "taille": np.abs(o[i] - c[i - 1]) / a[i - 1],
                         "duree_h": (dt.iloc[i] / pd.Timedelta(hours=1)).to_numpy()})


def part_gaps(bars: pd.DataFrame) -> float:
    """Σ |open − close précédent| / Σ (|open − close précédent| + |close − open|) : part des gaps dans la variation."""
    o, c = bars.open.to_numpy(dtype=float), bars.close.to_numpy(dtype=float)
    g, corps = np.abs(o[1:] - c[:-1]).sum(), np.abs(c[1:] - o[1:]).sum()
    return float(g / (g + corps)) if g + corps > 0 else np.nan


def _tr_bps(bars: pd.DataFrame) -> np.ndarray:
    h, lo, c = (bars[k].to_numpy(dtype=float) for k in ("high", "low", "close"))
    pc = np.concatenate(([np.nan], c[:-1]))
    return np.fmax(h - lo, np.fmax(np.abs(h - pc), np.abs(lo - pc))) / c * 1e4


def saison(bars: pd.DataFrame) -> pd.Series:
    """TR moyen (bps) par heure UTC d'ouverture de la barre."""
    return pd.Series(_tr_bps(bars)).groupby(bars.time.dt.hour.to_numpy()).mean()


def quotidien(bars: pd.DataFrame) -> pd.Series:
    """Dernière clôture de chaque jour UTC, indexée par le jour (minuit UTC)."""
    s = pd.Series(bars.close.to_numpy(dtype=float), index=pd.DatetimeIndex(bars.time))
    return s.groupby(s.index.normalize()).last()


def independance(q: pd.Series, ref: pd.Series, part: float = 0.05) -> dict:
    """Clôtures quotidiennes jointes sur les jours communs ; corrélations des rendements et de leurs valeurs absolues ;
    part des `part` jours les plus agités de l'actif qui le sont aussi pour la référence (≈ `part` si indépendants)."""
    d = np.log(pd.concat([q, ref], axis=1, keys=["a", "r"]).dropna()).diff().dropna()
    n = max(1, int(round(part * len(d))))
    commun = set(d.a.abs().nlargest(n).index) & set(d.r.abs().nlargest(n).index)
    return {"jours": len(d), "corr": float(d.a.corr(d.r)), "corr_abs": float(d.a.abs().corr(d.r.abs())),
            "jours_extremes_communs": len(commun) / n}


def facteur_saison(bars: pd.DataFrame, fuseau: str = "UTC", jours: int = 40, min_obs: int = 10) -> np.ndarray:
    """Facteur saisonnier causal de chaque barre : TR moyen (bps) de sa demi-heure en heure locale (`fuseau`) sur les
    `jours` précédents, barre exclue, rapporté au TR moyen de toutes les barres sur la même période. NaN faute de passé
    (moins de `min_obs` barres)."""
    tr = _tr_bps(bars)
    idx = pd.DatetimeIndex(bars.time)
    loc = idx.tz_convert(fuseau)
    case = np.asarray(loc.hour * 2 + (loc.minute >= 30))
    fen = f"{jours}D"
    tous = pd.Series(tr, index=idx).rolling(fen, closed="left", min_periods=min_obs).mean().to_numpy()
    moy = np.full(len(tr), np.nan)
    for k in np.unique(case):
        m = case == k
        moy[m] = pd.Series(tr[m], index=idx[m]).rolling(fen, closed="left", min_periods=min_obs).mean().to_numpy()
    return moy / tous


def atr_desaisonnalise(bars: pd.DataFrame, fac, n: int = 14) -> np.ndarray:
    """Moyenne de Wilder (alpha = 1/n) du TR en bps divisé par le facteur saisonnier : le niveau de volatilité hors
    saison horaire, connu à la clôture de t."""
    tr_s = _tr_bps(bars) / np.asarray(fac, dtype=float)
    return pd.Series(tr_s).ewm(alpha=1 / n, adjust=False, ignore_na=True).mean().to_numpy()


def z_saison(bars: pd.DataFrame, fac, atr_s, t: np.ndarray, h: int = H) -> np.ndarray:
    """Mouvement de l'ouverture de t + 1 à celle de t + 27 (bps de close[t]) / (ATR désaisonnalisé de t × racine de la
    moyenne des facteurs² des barres t + 1 à t + h). Sous une marche à saison pure, même loi que z26 sans saison."""
    o, c = bars.open.to_numpy(dtype=float), bars.close.to_numpy(dtype=float)
    f2 = np.asarray(fac, dtype=float) ** 2
    ok = np.isfinite(f2)
    cs = np.concatenate(([0.0], np.cumsum(np.where(ok, f2, 0.0))))
    cn = np.concatenate(([0], np.cumsum(~ok)))
    manque = cn[t + h + 1] - cn[t + 1]
    moy_f2 = np.where(manque == 0, (cs[t + h + 1] - cs[t + 1]) / h, np.nan)
    return (o[t + h + 1] - o[t + 1]) / c[t] * 1e4 / (np.asarray(atr_s, dtype=float)[t] * np.sqrt(moy_f2))


def profil_saison(bars: pd.DataFrame, fuseau: str = "UTC", jours: int = 40, h: int = H, amorce: int = AMORCE,
                  seuils=SEUILS) -> dict:
    """Queue de 13 h corrigée de la saison horaire (`z_saison`), à côté du z26 brut, sur toutes les fenêtres glissantes
    où la correction existe (amorce comptée depuis le premier ATR désaisonnalisé). Les fréquences sont des moyennes sur
    les h alignements possibles des fenêtres disjointes : un alignement unique déplace les comptes rares (BTC, 20 ATR
    ou plus : 2,2 ou 4,0 par an selon le départ). « Par an » : fréquence × fenêtres disjointes par an."""
    b = bars.reset_index(drop=True)
    fac = facteur_saison(b, fuseau, jours)
    atr_s = atr_desaisonnalise(b, fac)
    premier = int(np.flatnonzero(np.isfinite(atr_s))[0])
    t = np.arange(amorce + premier, len(b) - h - 1)
    zs, zb = z_saison(b, fac, atr_s, t, h), z_fenetres(b, atr(b), t, h)
    ok = np.isfinite(zs) & np.isfinite(zb)
    t, zs, zb = t[ok], zs[ok], zb[ok]
    ans = (b.time.iat[t[-1]] - b.time.iat[t[0]]) / pd.Timedelta(days=365.25)
    disjointes = len(t) / h
    a_bps = atr(b) / b.close.to_numpy(dtype=float) * 1e4
    out = {"fuseau": fuseau, "jours": jours, "fenetres_s": disjointes, "s_ans": ans,
           "s_ecart_type": float(np.std(zs)), "brut_ecart_type": float(np.std(zb)),
           "fac_p01": float(np.nanquantile(fac, 0.01)), "fac_p99": float(np.nanquantile(fac, 0.99)),
           "atr_s_sur_atr_p50": float(np.nanmedian(atr_s[t] / a_bps[t]))}
    for nom, z in (("s", zs), ("brut", zb)):
        for k in seuils:
            haut, bas = float(np.mean(z >= k)), float(np.mean(z <= -k))
            out[f"{nom}_haut_pour_mille_{k}"], out[f"{nom}_bas_pour_mille_{k}"] = 1000 * haut, 1000 * bas
            out[f"{nom}_pour_mille_{k}"] = 1000 * (haut + bas)
            out[f"{nom}_par_an_{k}"] = (haut + bas) * disjointes / ans
    return out


def _secondes(temps: pd.Series) -> np.ndarray:
    return ((temps - pd.Timestamp("1970-01-01", tz="UTC")) // pd.Timedelta(seconds=1)).to_numpy(dtype="int64")


def profil(bars: pd.DataFrame, creux=None, h: int = H, amorce: int = AMORCE, seuils=SEUILS,
           min_heure: int = 50) -> dict:
    """Mesures de la grille calculables sur les barres (sans coût ni RE-1). `creux` : (début, fin) d'une période dont on
    compare l'activité au total (creux du portefeuille de RE-1)."""
    b = bars.reset_index(drop=True)
    n, temps = len(b), b.time
    a = atr(b)
    c, o = b.close.to_numpy(dtype=float), b.open.to_numpy(dtype=float)
    atr_bps = a / c * 1e4
    ans = (temps.iat[-1] - temps.iat[0]) / pd.Timedelta(days=365.25)
    t = fenetres(n, h, amorce)
    z = z_fenetres(b, a, t, h)
    v = atr_bps[amorce:]
    out = {"debut": str(temps.iat[0]), "fin": str(temps.iat[-1]), "ans": ans, "barres": n, "fenetres": len(t),
           "atr_bps_p10": float(np.nanquantile(v, 0.10)), "atr_bps_p50": float(np.nanquantile(v, 0.50)),
           "atr_bps_p90": float(np.nanquantile(v, 0.90)), "plafond_r20": float(np.mean(v < 20)),
           "plafond_r25": float(np.mean(v < 25))}
    out.update(frequences(z, ans, seuils))
    out.update({f"repere_{k}": repere_gaussien(k, h) for k in seuils})
    out.update({"z_moyen": float(np.nanmean(z)), "z_p001": float(np.nanquantile(z, 0.001)),
                "z_p01": float(np.nanquantile(z, 0.01)), "z_p99": float(np.nanquantile(z, 0.99)),
                "z_p999": float(np.nanquantile(z, 0.999))})
    exp = a[t + h] / a[t]
    out.update({"expansion_p50": float(np.nanquantile(exp, 0.5)), "expansion_p90": float(np.nanquantile(exp, 0.9)),
                "expansion_p99": float(np.nanquantile(exp, 0.99))})
    calme = sous_mediane(atr_bps, temps, "365D")[t]
    grands = np.abs(z) >= GRAND
    out.update({"calme_tous": float(calme.mean()), "n_grands": int(grands.sum()),
                "calme_grands": float(calme[grands].mean()) if grands.any() else np.nan})
    with np.errstate(invalid="ignore", divide="ignore"):
        pas_ = np.abs(np.diff(c)) / a[:-1]
    out["saut_pour_mille_3"] = float(1000.0 * np.mean(pas_[amorce:] >= 3))
    chemin = lambda k: np.concatenate(([o[k + 1]], c[k + 1:k + h + 1], [o[k + h + 1]]))  # noqa: E731
    parts = [np.abs(np.diff(chemin(k))).max() / abs(o[k + h + 1] - o[k + 1]) for k in t[grands]
             if o[k + h + 1] != o[k + 1]]            # plus gros pas du chemin ouverture → clôtures → ouverture
    out["plus_gros_pas_grands"] = float(np.median(parts)) if parts else np.nan
    out["part_gaps"] = part_gaps(b)
    out.update({f"vr_{q}": variance_ratio(c[amorce:], q) for q in QS})
    out["efficacite_p50"] = float(np.nanmedian(efficacite(c, t, h)))
    s = saison(b)
    nb = b.time.dt.hour.value_counts().reindex(s.index).fillna(0)
    s = s[nb >= min_heure]
    out.update({"saison_max_min": float(s.max() / s.min()), "saison_heure_max": int(s.idxmax())})
    sec = _secondes(temps)
    semaine = (sec - sec[0]) // (7 * 86400)
    out["heures_par_semaine"] = float(pd.Series(semaine).value_counts().median() * 0.5)
    coupure = np.concatenate(([0], np.cumsum((np.diff(sec) > PAS.total_seconds()).astype(int))))
    out["fenetres_coupees"] = float(np.mean(coupure[t + h + 1] - coupure[t + 1] > 0))
    out["duree_fenetre_h_p50"] = float(np.median((sec[t + h + 1] - sec[t + 1]) / 3600))
    g = gaps(b, a)
    g = g[g.time >= temps.iat[amorce]]
    out.update({"gaps_par_an": len(g) / ans,
                "gap_p50": float(g.taille.median()) if len(g) else np.nan,
                "gap_p99": float(g.taille.quantile(0.99)) if len(g) else np.nan,
                **{f"gaps_{k}atr_par_an": float((g.taille >= k).sum() / ans) for k in (1, 2, 4)}})
    if creux is not None:
        tt = temps.iloc[t].reset_index(drop=True)
        m = ((tt >= pd.Timestamp(creux[0])) & (tt < pd.Timestamp(creux[1]))).to_numpy()
        tot = np.mean(np.abs(z) >= GRAND)
        dedans = np.mean(np.abs(z[m]) >= GRAND) if m.any() else np.nan
        out.update({"creux_fenetres": int(m.sum()),
                    "creux_grands_ratio": float(dedans / tot) if tot > 0 and m.any() else np.nan,
                    "creux_amplitude_ratio": float(np.nanmean(np.abs(z[m])) / np.nanmean(np.abs(z)))
                    if m.any() else np.nan})
    return out
