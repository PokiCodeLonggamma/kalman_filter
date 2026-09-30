# BEST RESULTS — les meilleurs résultats de chaque étape

> Aide-mémoire : les deux ou trois résultats les plus utiles de chaque étape, avec leur statut. Le détail est dans `RESEARCH_LOG.md`, la lecture dans `RESEARCH_INSIGHTS.md`, les chiffres dans `experiments/<expérience>/`.
>
> Tout porte sur BTC/USD 30 min, 2020-2025, **dans l'échantillon**, sauf l'Étape D (transfert à d'autres actifs). Aucun résultat n'est validé hors échantillon : le hold-out (BTC 2026, ETH, XRP) reste scellé jusqu'à la fin de l'Étape D.
>
> **Conventions :**
> - PnL nets de frais ; une position à la fois ;
> - capital à 0,25 % par ATR14(t), levier ≤ 1x, sauf mention « 1x » ;
> - IC 95 % par bootstrap de grappes mensuelles.
>
> Mis à jour après chaque expérience.

---

## Configuration de référence du moteur (EXP-C02bis, RE-1)
*Validée officiellement par le porteur le 2026-09-29 comme référence de l'Étape C. H = 26 est commun aux deux sous-familles et verrouillé. Sont vérifiés : le plateau d'horizon, les seuils causaux, la règle de réentrée et la sensibilité des trois seuils (C05). Aucune validation hors échantillon.*

- **Signaux :** R2 hors `nis_z_100` Q4 (vetos d'entrée : x1 non retourné, R3, `nis_z_100` Q4).
- **Sortie :** à H26, avec une enveloppe par sous-famille, connue à t :
  - F2b · x1 déjà retourné (retracement de 0,50 à 0,85) : sans stop ;
  - F3 · x1 déjà retourné (retracement ≥ 0,85) : stop à l'extremum du segment qualifiant.
- **Après un stop :** cooldown jusqu'à t + 1 + H.

| Métrique | 5 bps | 10 bps |
|---|---|---|
| PnL net total : composé à 0,25 %/ATR ; 1x ; bps cumulés (1x) | +138 % ; +204 % ; +13 320 bps | +72 % ; +77 % ; +7 920 bps |
| Profit factor : 1x ; pondéré | 1,20 ; 1,28 | 1,11 ; 1,17 |
| Win rate | 44,3 % | 42,8 % |
| Espérance par trade : ATR [IC] | +0,369 [+0,098 ; +0,645] | +0,233 [−0,041 ; +0,511] |
| Espérance par trade : bps [IC] | +12,3 [+0,2 ; +24,4] | +7,3 [−4,8 ; +19,4] |
| Max drawdown valorisé : 0,25 %/ATR ; 1x | −13,5 % ; −43,9 % | −15,9 % ; −48,0 % |
| Trades | 1 080 (15,0 par mois), dont 24 % stoppés | idem |
| Durée médiane | 26 barres (13 h) | idem |
| Part des frais (1x) ; brut par trade | 29 % ; +17,3 bps | 58 % ; +17,3 bps |
| Années positives | 6 sur 6 | 5 sur 6 (2021) |
| Calmar (PnL annualisé / drawdown, 0,25 %/ATR) | 1,16 (+15,6 % par an) | 0,60 (+9,5 % par an) |

**À garder en tête :**
- **Même espérance que R2 hors Q4 sans stop.** Sur les mêmes entrées, l'effet apparié vaut +0,015 ATR [−0,108 ; +0,141]. Le moteur gère le risque : drawdown −20,5 % → −13,5 %, Calmar 0,69 → 1,16, 2024 à +15 % au lieu de −3 %.
- **Plateau :** l'IC en ATR est positif de H20 à H32 ; le PnL passe de +65 % (H20) à +138 % (H26) puis +89 % (H32). À H13 et H48, pas d'avantage.
- **Seuils causaux :** +0,34 à +0,37 ATR avec IC > 0, 6 années sur 6, drawdown de −12 à −14 %. Calmar de 1,00 à 1,21, annualisé sur les 5,56 ans qui suivent l'amorce.
- **IC en bps fragile :** il ne reste positif qu'avec la période du 13 janvier au 9 juin 2020.
- **Filtrage mutuel :** une position à la fois écarte les contre-signaux de l'autre sous-famille, qui perdaient seuls (F3 contre un F2b ouvert : −1,22 ATR).
- La règle de F3 a été choisie après lecture de C02. À 10 bps, l'IC contient 0.
- **Break-even et take-profit (EXP-C03) :** aucun ne l'améliore ; RE-1 reste intact.
- **Sensibilité (EXP-C05) :**
  - plateaux pour la frontière F2b / F3 (0,85 à 0,95) et pour la marge du stop de F3 (−0,25 à +0,25 ATR) ;
  - seuil sensible : l'exclusion de `nis_z_100`, falaise côté permissif (P80 : −0,06 ATR par trade, significatif). Signalé avant l'Étape D.

---

## Point de départ — Phase 0
- **Mécanique native v2.1** (stop-and-reverse, 5 bps) : 6 037 trades (84 par mois), −5,3 bps par trade, PF 0,907, capital −98,7 %. Les frais cumulés (≈ 30 200 bps) écrasent un PnL brut déjà négatif (−2 047 bps).
- C'est la référence reproduite à l'identique (ancre P6.5d), non une piste.

## Étape A — Anatomie (EXP-A01, descriptive)
1. **Géométrie stationnaire en ATR14(t).** Distances et durées sont stables de 2020 à 2025 en ATR, alors que l'ATR14 médian varie de 34 à 80 bps selon l'année. Toute l'enveloppe s'exprime donc en ATR14(t), d'où la convention de capital à 0,25 % par ATR.
2. **Le déclencheur mêle retournement et décélération.**
   - Le signal arrive environ 5 barres après l'extremum de prix.
   - Il tombe au passage à zéro de la vitesse x1, ou 1 à 2 barres avant, dans 64,5 % des cas.
   - x1 est déjà du sens du signal dans 51,8 % des cas. D'où `x1_already_flipped_at_t`, qui sépare R1 de R2.
3. **La tenue de l'extremum n'est pas une cible** (I-M1). Elle croît mécaniquement avec la distance déjà parcourue : 36,5 % au premier quartile, 85,3 % au dernier. La cible de B est l'asymétrie d'excursion.

## Étape B — Catégorisation (EXP-B01 et relecture, sans frais ni stop)
1. **Trois régimes du déclencheur :**
   - R1, essoufflement : médiane positive, queue gauche ;
   - R2, sortie de range : moyenne positive à 26-48 barres, queue droite ;
   - R3, continuation.
2. **R2 à H48 :** timing moyen +0,28 ATR [+0,03 ; +0,50], 5 années positives sur 6. F2b porte le Long (+0,81 ATR d'écart à l'ensemble), F3 le Short (+0,62).
3. **Signatures de continuation, devenues filtres d'exclusion :**
   - R3 : timing moyen −0,29 ATR [−0,48 ; −0,07] à H48, négatif 6 années sur 6 ;
   - `nis_z_100` Q4 : −0,25 [−0,39 ; −0,09] à H26.

## Étape C — Enveloppe

### EXP-C01 — sortie à horizon fixe et régimes (5 bps)
1. **F2b · x1 déjà retourné hors Q4, H26, sans stop.**
   - Espérance : +11,5 bps [−2,9 ; +26,0] ; +0,389 ATR [+0,079 ; +0,700], inchangée après winsorisation.
   - +72 %, drawdown −13 % ; 639 trades (8,9 par mois) ; 5 années positives sur 6.
   - 10 bps : +0,255 ATR, +42 %.
   - Le gain vient de l'éviction pure de `nis_z_100` Q4 (contrôle A).
2. **R2 hors Q4, H26, sans stop.** +12,3 bps [−1,5 ; +25,8] ; +0,354 ATR [+0,051 ; +0,643] ; +122 %, drawdown −20,5 % ; 1 080 trades (15 par mois).
3. **Éviction de `nis_z_100` Q4 :** c'est le filtre le plus régulier, qui améliore 18 comparaisons sur 20.

### EXP-C02 — stop-loss par sous-famille (5 bps, séquentiel)
1. **F3 · x1 déjà retourné hors Q4, H26, stop à l'extremum du segment.**
   - Drawdown −34 % → −13 %.
   - PnL +16 % → +36 %, et +41 % en cooldown.
   - 6 années positives sur 6 ; Long et Short positifs.
   - Espérance +0,202 ATR [−0,106 ; +0,520].
2. **F2b : aucun stop.** Chaque stop coûte 0,15 à 0,38 ATR par trade ; l'effet apparié est négatif pour 10 règles sur 11. La moitié des trades passent par −2 ATR avant l'expansion.
3. **R2 hors Q4, H26, SL-A 5 ATR.** C'est la seule configuration avec stop dont l'IC en ATR est positif : +0,286 [+0,019 ; +0,562], +93 %, drawdown −18 %.

La relecture de C02 assemble 1 et 2 ; EXP-C02bis en fait la configuration de référence (en tête de fichier).

### EXP-C02bis — moteur de régimes (5 bps, séquentiel global, une position à la fois)
1. **RE-1 en cooldown, H26** (F2b sans stop, F3 stop à l'extremum) : +0,369 ATR [+0,098 ; +0,645], +138 %, drawdown −13,5 %, Calmar 1,16, 6 années positives sur 6. Le détail est en tête de fichier.
2. **Plateau d'horizon.** L'IC en ATR de RE-1 est positif de H20 à H32 (+0,21 à +0,37 ATR). Entre H24 et H28, l'espérance varie de moins de 0,05 ATR et le PnL va de +112 à +138 %.
3. **Tenue avec des seuils causaux** (glissants ou expansifs) : +0,34 à +0,37 ATR avec IC > 0, +103 à +118 %, drawdown −12 à −14 %, Calmar 1,00 à 1,21 (sur 5,56 ans), 6 années sur 6.

### EXP-C03 — break-even différé sur RE-1 (5 bps, cooldown, mêmes entrées)
1. **Aucune valeur marginale du break-even.**
   - Pour m ≥ 2 ATR, l'effet apparié va de −0,021 à +0,030 ATR par trade (IC ±0,1), aux trois horizons H24, H26 et H28.
   - Pour m ≤ 1,5, il est négatif : jusqu'à −0,157 ATR (V3 à m = 1), significatif pour F2b à H24 et H28.
2. **Mécanique : sauvés et coupés s'équilibrent.**
   - V3 à m = 2 : 147 trades sauvés (+1,98 ATR chacun) contre 121 coupés (−2,57), soit +0,270 contre −0,288 ATR par trade.
   - Le décile supérieur de RE-1 apporte 0,92 ATR par trade, plus que l'espérance totale (+0,369).
3. **Drawdown : une tendance, pas un résultat.**
   - V3 à m = 2 : −11,7 % contre −13,5 % à H26, avec une baisse aux trois horizons.
   - Écart non significatif : moins profond dans 89 % des chemins réordonnés, plage [−2,1 ; +11,6] points (I-M10). Coût : −0,018 ATR par trade. Non retenu.

Le take-profit fixe est exclu : même sa borne optimiste reste sous RE-1 (+0,200 à +0,347 ATR contre +0,369). La décision du porteur est vérifiée.

**Analyse approfondie (relecture du porteur) : décision 1, break-even rejeté et RE-1 intact.**
- **Aucun gain de risque démontré pour V3 à m = 2.** Le MDD est meilleur dans 82 à 92 % des chemins réordonnés, le Calmar dans 65 à 82 %. Les drawdowns sont plus longs : 459 jours sous le pic contre 390.
- **À MDD égal, ce n'est qu'un désendettement.** Un RE-1 réduit à 0,211 % par ATR fait +13,5 % par an, contre +14,5 % pour V3 sans glissement (I-M11).
- **Il ne résiste pas à l'exécution.** Dès 5 bps de glissement du break-even, le Calmar tombe à 1,10, sous les 1,16 de RE-1 ; à MDD égal, V3 fait −0,8 point par an face à RE-1 réduit.
- **2022 tient à deux trades.** Son déficit (−0,184 ATR) vient de deux gagnants F3 extrêmes coupés (+18,6 et +14,3 ATR dans RE-1) ; sans eux, l'année fait +0,006.

### EXP-C04 — filtre de tendance macro sur RE-1 (5 bps, H26)
1. **Les trades contre-tendance de RE-1 ne sont pas toxiques.** Ils valent +0,389 (EMA 200), +0,398 (EMA 50) et +0,426 ATR (Kalman 4 h), contre +0,32 à +0,35 pour les alignés. Aucun écart n'est significatif, et tous vont en faveur des contre-tendance.
2. **Ils portent les grands retournements.**
   - Selon la tendance, 33 à 48 % du décile supérieur de RE-1 est contre-tendance, dont 9 des 20 meilleurs trades pour le Kalman 4 h.
   - F2b contre-tendance est le meilleur groupe (+0,52 à +0,58). Les Long contre la tendance 4 h font +0,64 ATR [+0,17 ; +1,08].
3. **Le veto dégrade tout.**
   - Espérance +0,369 → +0,22 à +0,26 ; PnL +138 % → +38 à +55 % ; Calmar 1,16 → 0,41 à 0,49.
   - Même constat à 10 bps et à H24, H26 et H28.
   - En séquentiel, les signaux ajoutés dans la fenêtre d'un trade vétoé perdent (−0,48 ATR pour l'EMA 200). **RE-1 reste pur.**

### EXP-C05 — sensibilité de RE-1 à ses trois seuils (5 bps, H26, un seuil à la fois)
1. **Frontière F2b / F3 : plateau de 0,85 à 0,95, pente en dessous.**
   - De 0,85 à 0,95 : espérance +0,369 à +0,396 ATR, MDD −13,4 à −14,2 %, Calmar 1,16 à 1,21. Effets appariés non significatifs.
   - À 0,75 : −0,095 ATR par trade [−0,157 ; −0,030], MDD −19,2 %. Le stop à l'extremum coupe les meilleurs F2b, qui font +0,9 à +1,0 ATR sans stop pour un retracement de 0,75 à 0,85.
   - RE-1 est 3e sur 5 : la frontière, fixée en B01, n'a pas été calée sur cette courbe.
2. **Marge du stop de F3 : plateau de −0,25 à +0,25 ATR.**
   - Effets appariés de −0,009 et −0,014 ATR, non significatifs.
   - À +0,50 : −0,036, MDD −15,2 %, Calmar 0,91.
   - δ = 0 était la valeur la plus serrée de C02 ; le côté plus serré est plat.
3. **Exclusion de `nis_z_100` : RE-1 au sommet (1er sur 5), falaise côté permissif.**
   - Écarts à RE-1 : P80 −0,059 [−0,117 ; −0,009], P85 −0,131, P90 −0,150 ATR ; Calmar 0,84, 0,59 et 0,56. Les signaux admis perdent (−0,29 à −0,53 ATR).
   - P70 : −0,019, non significatif.
   - Verdict de la règle fixée avant le calcul : plateau en limite à 5 bps, falaise à 10 bps. **Signalement formel avant l'Étape D.**

L'Étape C a testé ses quatre facteurs (horizon, stop par sous-famille, break-even, filtre macro) et la sensibilité de ses seuils. RE-1, en tête de fichier, est la stratégie cœur, inchangée.

---

## Étape D — Adaptation

### EXP-D01 et D01 bis — portabilité de RE-1 figée, sans réglage (descriptive ; seuils numériques de BTC gelés)
*Aucun critère de réussite ni classement (décision du porteur). WTI retiré par le porteur (données), remplacé par XLE.*

| | BTC 5 bps (réf.) | SOL/USD 5 bps | CFD or 4 bps | SPY 4 bps | XLE 4 bps |
|---|---|---|---|---|---|
| Période | 2020-2025 | 2021-06-17 → 2025 | 2020-2025 | 2020-2025 (séance régulière) | 2020-2025 (séance régulière) |
| Trades (par mois) | 1 080 (15,0) | 769 (14,1) | 651 (9,0) | 155 (2,2) | 136 (1,9) |
| Espérance ATR [IC] | +0,369 [+0,098 ; +0,645] | +0,190 [−0,079 ; +0,484] | −0,019 [−0,362 ; +0,349] | −0,158 [−0,736 ; +0,434] | +0,020 [−0,588 ; +0,674] |
| Espérance bps [IC] | +12,3 [+0,2 ; +24,4] | +19,2 [−3,6 ; +44,2] | +1,1 [−4,9 ; +7,5] | −4,5 [−23,7 ; +14,9] | +7,4 [−28,7 ; +43,9] |
| PnL : 0,25 %/ATR ; 1x | +138 % ; +204 % | +39 % ; +173 % | +0,6 % ; +5,4 % | −4,2 % ; −7,9 % | +0,1 % ; +7,2 % |
| MDD valorisé : 0,25 %/ATR ; 1x | −13,5 % ; −43,9 % | −13,1 % ; −42,3 % | −13,6 % ; −13,3 % | −10,9 % ; −19,2 % | −19,5 % ; −36,4 % |
| Calmar : 0,25 %/ATR ; 1x | 1,16 ; 0,46 | 0,58 ; 0,59 | 0,01 ; 0,07 | −0,07 ; −0,07 | 0,00 ; 0,03 |
| Brut ; frais (ATR par trade) | +0,50 ; 0,14 | +0,25 ; 0,06 | +0,24 ; 0,26 | 0,00 ; 0,16 | +0,10 ; 0,08 |
| F2b ; F3 (ATR) | +0,459 ; +0,267 | +0,287 ; +0,076 | −0,304 ; +0,313 | +0,059 ; −0,367 | −0,186 ; +0,139 |
| Années à espérance ATR > 0 | 6/6 | 5/5 | 2/6 | 2/6 | 3/6 |

- **10 bps :** SOL +0,129 ATR [−0,140 ; +0,425] ; BTC +0,233 [−0,041 ; +0,511], soit +7,3 bps [−4,8 ; +19,4] (estimation positive, IC qui traverse zéro).
- **La population transfère, la rente dépend du marché.**
  - Géométrie des signaux identique sur la crypto et l'or ; jambes plus longues sur les ETF (gaps).
  - Brut divisé par deux sur SOL et l'or ; nul sur les ETF.
  - Sur l'or, 4 bps coûtent 0,26 ATR par trade.
- **Gaps d'ouverture (ETF) :**
  - le filtre `nis_z_100` écarte 64 à 74 % des signaux nés d'un gap ;
  - mais H = 26 barres fait traverser deux nuits : les gaps pèsent 35 à 47 % de l'amplitude des trades ;
  - les stops percés à l'ouverture dépassent leur niveau de +1,0 à +2,6 ATR en moyenne.
- **Constantes sur tous les actifs :** queue droite (le décile supérieur fait plus que le total) ; le stop de F3 réduit le drawdown.

### EXP-D01.5 — sensibilité de RE-1 à H seul (4 bps, descriptive, aucun H retenu)
*Grilles du porteur : or H ∈ {26, 48, 72, 96, 130} ; SPY et XLE H ∈ {6, 13, 26, 65, 130}. Aucune des 15 configurations n'a un IC à borne basse > 0.*

| Meilleur point de chaque grille (ATR) | Espérance ATR [IC] | PnL : 0,25 %/ATR ; 1x | MDD : 0,25 %/ATR ; 1x | Effet apparié contre H = 26 | Lecture |
|---|---|---|---|---|---|
| Or, H = 26 (RE-1) | −0,019 [−0,362 ; +0,349] | +1 % ; +5 % | −13,6 % ; −13,3 % | — | au-delà, décroissant jusqu'à −0,702 (H = 130) |
| SPY, H = 26 (RE-1) | −0,158 [−0,736 ; +0,434] | −4 % ; −8 % | −10,9 % ; −19,2 % | — | plat de 6 à 26 (−0,16 à −0,19), puis −0,76 et −0,38 |
| XLE, H = 65 | +0,155 [−0,788 ; +1,130] | +3 % ; +20 % | −10,9 % ; −26,3 % | −0,010 [−0,71 ; +0,75] | pic isolé (H = 130 : −1,573), gain dû à la population |

- **Or :** frais fixes en ATR (0,26 par trade à tout H) ; le brut ne croît pas avec H ; la dérive croît des deux côtés.
- **ETF :** H = 13 traverse encore une nuit (91 % des trades) ; H = 6 réduit les nuits de moitié, mais la composante en séance est ≈ 0 (SPY) ou négative (XLE).

### EXP-D01.6 — verrouillage et séance sur SPY et XLE (4 bps, exploratoire, rien retenu)
*Aucune variante n'a un IC à borne basse > 0. Meilleurs points ci-dessous, à titre descriptif.*

| Variante | Espérance ATR [IC] | PnL : 0,25 %/ATR ; 1x | MDD : 0,25 %/ATR ; 1x | Lecture |
|---|---|---|---|---|
| SPY · séance, libérée à la clôture | −0,008 [−0,248 ; +0,225] | +0 % ; +5 % | −7,0 % ; −9,4 % | brut +0,157 ATR ≈ frais 0,164 ; risque divisé par deux |
| XLE · H_exit 26, H_cooldown 90 | +0,123 [−0,639 ; +1,003] | +2 % ; +9 % | −17,4 % ; −35,5 % | zigzag selon le verrouillage (48 : −0,130) : calendrier |

- Les 31 trades de XLE « sautés » à H = 65 gagnent +0,118 ATR avec la sortie de RE-1 : rien à filtrer.

### EXP-D01.7 (en cours) — portabilité zero-shot sur marchés 24/5
*GBPJPY mesuré ; NQ, RTY, CL, HG en attente d'accès aux données.*

| | BTC 5 bps (réf.) | GBPJPY brut | GBPJPY 4 bps |
|---|---|---|---|
| Espérance ATR [IC] | +0,369 [+0,098 ; +0,645] | −0,035 [−0,284 ; +0,221] | −0,443 [−0,697 ; −0,180] |
| PnL : 0,25 %/ATR ; 1x | +138 % ; +204 % | −4 % ; −5 % | −27 % ; −27 % |
| MDD : 0,25 %/ATR ; 1x | −13,5 % ; −43,9 % | −8,7 % ; −8,8 % | −27,2 % ; −27,9 % |
| Frais en ATR ; trades (/mois) | 0,14 ; 1 080 (15,0) | 0 ; 687 (9,5) | 0,41 ; 687 (9,5) |

- GBPJPY : brut nul dans les deux sens ; le 0,25 %/ATR est plafonné à 1x pour 98 % des trades (ATR de 30 min ≈ 11 bps).

## Pistes écartées (à ne pas retester sans élément nouveau)

| Piste | Raison | Source |
|---|---|---|
| Stop-and-reverse natif | −98,7 % ; frais ≈ 30 200 bps pour un brut de −2 047 bps | Phase 0 |
| Tous les signaux à horizon fixe | −3,7 à −16,0 bps par trade de H6 à H48 | C01 |
| Entrée en continuation (R3, `nis_z_100` Q4) | +10,3 bps [+1,3 ; +19,8] à H26 seulement, porté par 2020-2021 ; écartée par le porteur | C01 |
| R1, F1, F5 (x1 encore opposé) | aucune espérance nette positive, avec ou sans stop ; les frais coûtent 0,135 ATR par trade sur F5 ; rejet définitif (décision du porteur) : x1 retourné est un prérequis d'entrée | C02 |
| Stop sur F2b | coupe les gagnants : −0,15 à −0,38 ATR par trade | C02 |
| Stop de catastrophe à 5 ATR sur F2b dans le moteur (RE-3) | −0,08 ATR par trade, drawdown plus élevé, Calmar 0,77 contre 1,16 | C02bis |
| Réouverture immédiate après un stop (H ≤ 32) | les trades débloqués font −0,15 à −1,38 ATR ; le cooldown fait mieux | C02bis |
| Horizon propre à chaque sous-famille (F2b à H28) | à H28 : F3 +0,148 ATR, DD −16,2 %, Calmar 0,92 ; paramètre libre choisi après lecture ; H = 26 verrouillé (décision du porteur) | C02bis |
| Take-profit fixe sur RE-1 (2 à 6 ATR) | même la borne optimiste (TP pris dès que la MFE26 l'atteint) reste sous RE-1 : +0,200 à +0,347 ATR contre +0,369 ; exclu (décision du porteur, vérifiée) | C03 |
| Break-even différé sur RE-1, m ≤ 1,5 ATR | ampute la queue droite ; effet apparié jusqu'à −0,157 ATR par trade ; significatif pour F2b à H24 et H28 | C03 |
| Break-even différé sur RE-1, m ≥ 2 ATR | effet apparié de −0,02 à +0,03 ATR par trade ; baisse du drawdown non significative ; non retenu (KISS) | C03 |
| Break-even comme variante de gestion du risque (V3 ou V2, m = 2) | gain de MDD non démontré (82 à 92 % des chemins), Calmar fragile, drawdowns plus longs ; à MDD égal, équivaut à réduire la taille ; perdu dès 5 bps de glissement du break-even | C03, analyse approfondie |
| Veto des signaux contre la tendance (EMA 200, EMA 50, Kalman v2.1 sur 4 h) | les trades contre-tendance valent autant ou plus que les alignés (+0,39 à +0,43 ATR) et portent jusqu'à 48 % du décile supérieur ; espérance +0,369 → +0,22 à +0,26 ; Calmar 1,16 → 0,41 à 0,49 ; pire à 10 bps et sur tout le plateau | C04 |
| Stop à l'extremum pour les retracements de 0,75 à 0,85 (frontière F2b / F3 abaissée) | coupe les meilleurs F2b (+0,9 à +1,0 ATR sans stop) ; frontière 0,75 : −0,095 ATR par trade [−0,157 ; −0,030], MDD −19,2 % | C05 |
| Exclusion de `nis_z_100` relâchée (P80 à P90) | les signaux admis perdent (−0,29 à −0,53 ATR) ; −0,06 à −0,15 ATR par trade, significatif ; Calmar 0,84 → 0,56 | C05 |
