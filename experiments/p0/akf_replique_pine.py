"""
akf_replique_pine.py — Réplique Python LECTURE SEULE de « AKF-TSO v2.1 Reversal » (Pine v6), paramètres par défaut.
Produite en P0 (15/09/2026) pour exposer les variables internes non tracées par le Pine. Ce n'est PAS le module P2.

Usage :
    import pandas as pd
    from akf_replique_pine import run
    df = pd.read_csv("btcusd_30m_bitstamp.csv", parse_dates=["time"]).iloc[:-1]   # retirer la barre non confirmée
    out = run(df)   # colonnes : x0, x1, x0_pred, innov, S, nis, K0, K1, P00..., R, A, ratio, ts, ts_plot,
                    #            zone, seg_zone, seg_len, seg_ext, prev_zone, prev_len, prev_ext, long, short

Fidélité vérifiée (données Bitstamp API depuis 2025-06-01, TradingView BITSTAMP:BTCUSD 30 min) :
    barre 2026-09-15 14:00 UTC (16:00 Paris) → Kalman 76 683 · TS affiché −76 · R_used 95 · innovation −458 · NIS 1 911
    table TradingView −89 % = ts ; horodatages des 20 signaux du carnet P0 identiques ; 720 entrées 2026 vs 718 trades clos TV.

Conventions reproduites volontairement (NE PAS « corriger » ici) :
    - reset_P_diag=True : P[0,0] = P[1,1] = 1 avant chaque prédiction (lignes Pine 62-63 hors `var`).
    - ta.stdev / ta.variance Pine = écart-type population (ddof=0) ; WMA poids 1..n.
    - Q = [[q1, q1*q2],[q1*q2, q2]] ; R = R0 * (stdev20/sma100(stdev20))**gamma, R0 tant que la SMA100 est na.
Limites : boucle Python (quelques secondes pour ~22 k barres), pas de tests, options Myers-Tapley / R estimé / debug non implémentées.
"""
import numpy as np, pandas as pd
def pine_wma(x, n):
    w = np.arange(1, n+1); out = np.full(len(x), np.nan)
    for i in range(n-1, len(x)):
        seg = x[i-n+1:i+1]
        if not np.isnan(seg).any(): out[i] = (seg*w).sum()/w.sum()
    return out
def run(df, R0=100.0, q1=0.01, q2=0.01, gamma=0.5, N2=5, R1=3, R2=3, vol_lkb=20,
        up_th=30.0, down_th=-30.0, min_bars=6, min_ts=60.0, use_strength=True, reset_P_diag=True):
    c = df.close.values; n = len(c)
    s = pd.Series(c)
    rv = s.rolling(vol_lkb).std(ddof=0).values
    av = pd.Series(rv).rolling(100).mean().values
    F = np.array([[1.,1.],[0.,1.]]); H = np.array([[1.,0.]])
    Q = np.array([[q1, q1*q2],[q1*q2, q2]])
    P = np.eye(2); X = np.array([c[0], 0.])
    buf = []
    rec = {k: np.full(n, np.nan) for k in ["x0","x1","x0_pred","x1_pred","innov","S","nis","K0","K1",
           "P00","P01","P11","Ppred00","Ppred01","Ppred11","R","A","ratio","ts"]}
    ts_hist = []  # entrées de la wma conditionnelle
    for i in range(n):
        if reset_P_diag:
            P[0,0] = 1.0; P[1,1] = 1.0      # lignes 62-63 exécutées à chaque barre
        R = R0
        if gamma > 0 and i > vol_lkb and not np.isnan(av[i]) and av[i] > 0:
            R = R0 * (rv[i]/av[i])**gamma
        xp = F @ X
        Pp = F @ P @ F.T + Q
        S = (H @ Pp @ H.T)[0,0] + R
        K = (Pp @ H.T) / S
        innov = c[i] - xp[0]
        X = xp + K[:,0]*innov
        IKH = np.eye(2) - K @ H
        P = IKH @ Pp @ IKH.T + (K * R) @ K.T
        buf.append(X[1]);  buf = buf[-N2:]
        r = rec
        r["x0"][i],r["x1"][i],r["x0_pred"][i],r["x1_pred"][i]=X[0],X[1],xp[0],xp[1]
        r["innov"][i],r["S"][i],r["nis"][i]=innov,S,innov*innov/S
        r["K0"][i],r["K1"][i]=K[0,0],K[1,0]
        r["P00"][i],r["P01"][i],r["P11"][i]=P[0,0],P[0,1],P[1,1]
        r["Ppred00"][i],r["Ppred01"][i],r["Ppred11"][i]=Pp[0,0],Pp[0,1],Pp[1,1]
        r["R"][i]=R
        if len(buf) >= N2:
            A = max(abs(v) for v in buf); A = A if A > 1e-10 else 1.0
            ts_hist.append((i, X[1]/A*100)); r["A"][i]=A; r["ratio"][i]=X[1]/A*100
    idx = np.array([t[0] for t in ts_hist]); vals = np.array([t[1] for t in ts_hist])
    w = pine_wma(vals, R2); rec["ts"][idx] = w
    out = pd.DataFrame(rec); out.insert(0,"time",df.time.values); out["close"]=c
    out["high"]=df.high.values; out["low"]=df.low.values
    out["ts_plot"] = pine_wma(out.ts.values, R1)
    # zones / segments
    seg_zone=0; seg_len=0; seg_ext=0.0; pz=0; pl=0; pe=0.0
    cols = {k: np.zeros(n) for k in ["zone","seg_zone","seg_len","seg_ext","prev_zone","prev_len","prev_ext","long","short"]}
    for i in range(n):
        ts = rec["ts"][i]
        if not np.isnan(ts):
            z = 1 if ts > up_th else (-1 if ts < down_th else 0)
            if z == seg_zone:
                seg_len += 1; seg_ext = max(seg_ext, abs(ts))
            else:
                pz,pl,pe = seg_zone,seg_len,seg_ext; seg_zone=z; seg_len=1; seg_ext=abs(ts)
            cols["zone"][i]=z
        L = seg_zone==0 and pz==-1 and seg_len==1 and pl>=min_bars and ((not use_strength) or pe>=min_ts)
        Sh= seg_zone==0 and pz==1 and seg_len==1 and pl>=min_bars and ((not use_strength) or pe>=min_ts)
        for k,v in zip(["seg_zone","seg_len","seg_ext","prev_zone","prev_len","prev_ext","long","short"],
                       [seg_zone,seg_len,seg_ext,pz,pl,pe,L,Sh]): cols[k][i]=v
    for k,v in cols.items(): out[k]=v
    return out
