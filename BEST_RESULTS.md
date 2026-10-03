# BEST RESULTS — les meilleurs résultats de chaque étape

> Aide-mémoire : les deux ou trois résultats les plus utiles de chaque étape, avec leur statut. Le détail est dans `RESEARCH_LOG.md`, la lecture dans `RESEARCH_INSIGHTS.md`, les chiffres dans `experiments/<expérience>/`.
>
> Tout porte sur BTC/USD 30 min, 2020-2025, **dans l'échantillon**, sauf l'Étape D (transfert à d'autres actifs). Le hold-out (BTC 2026, ETH, XRP, 2026 des autres actifs) a été levé en EXP-D04 (2026-10-03), protocole pré-enregistré.
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

### EXP-D01.7 — portabilité zero-shot : CFD sur indices, argent, GBPJPY et CFD sur ETF (Saxo, coût principal)
*Descriptive. L'univers a été redéfini par le porteur : futures abandonnés (raccords de Saxo non ajustés), HK50 à la place
de Japan 225. Coûts validés avant le calcul. Aucun IC à borne basse positive.*

| Actif (coût) | Espérance ATR [IC] | Brut ATR ; frais ATR | PnL : 0,25 %/ATR ; 1x | MDD : 0,25 %/ATR ; 1x | Trades | Années > 0 |
|---|---|---|---|---|---|---|
| BTC (5, réf.) | +0,369 [+0,098 ; +0,645] | +0,50 ; 0,14 | +138 % ; +204 % | −13,5 % ; −43,9 % | 1 080 | 6/6 |
| US30 (4) | −0,004 [−0,350 ; +0,348] | +0,33 ; 0,33 | +11 % ; +29 % | −13,7 % ; −14,1 % | 710 | 2/6 |
| GER40 (4) | −0,005 [−0,292 ; +0,294] | +0,24 ; 0,24 | +0 % ; +5 % | −22,9 % ; −27,5 % | 545 | 2/6 |
| US100 (4) | −0,097 [−0,428 ; +0,252] | +0,14 ; 0,24 | −5 % ; −10 % | −19,7 % ; −27,0 % | 695 | 1/6 |
| HK50 (8) | −0,103 [−0,539 ; +0,334] | +0,19 ; 0,30 | −9 % ; −15 % | −32,3 % ; −41,9 % | 425 | 2/6 |
| GBPJPY (4) | −0,303 [−0,572 ; −0,031] | +0,10 ; 0,40 | −20 % ; −21 % | −22,0 % ; −22,1 % | 754 | 0/6 |
| XAGUSD (11) | −0,307 [−0,634 ; +0,006] | +0,06 ; 0,37 | −41 % ; −57 % | −43,5 % ; −59,7 % | 651 | 1/6 |
| EU50 (7) | −0,590 [−0,946 ; −0,214] | −0,17 ; 0,42 | −37 % ; −44 % | −40,6 % ; −47,8 % | 535 | 1/6 |
| GDX (4) | +0,349 [−0,365 ; +1,076] | +0,42 ; 0,07 | +12 % ; +70 % | −8,5 % ; −19,1 % | 143 | 5/6 |
| USO (4) | +0,148 [−0,553 ; +0,813] | +0,22 ; 0,07 | +4 % ; +65 % | −9,6 % ; −24,8 % | 140 | 2/6 |
| URA (4) | +0,093 [−0,823 ; +1,100] | +0,15 ; 0,06 | +2 % ; −18 % | −12,6 % ; −41,8 % | 127 | 2/6 |
| SMH (4) | −0,180 [−0,795 ; +0,409] | −0,11 ; 0,08 | −7 % ; −13 % | −15,5 % ; −30,4 % | 149 | 2/6 |
| TLT (4) | −0,205 [−0,972 ; +0,570] | −0,04 ; 0,16 | −9 % ; −11 % | −16,6 % ; −21,1 % | 157 | 2/6 |

- **Le signal se transpose, la rente non.**
  - Sur les CFD sur indices, l'argent et GBPJPY, l'ATR de 30 min vaut 11 à 34 bps : les frais (0,24 à 0,42 ATR)
    absorbent un brut de +0,06 à +0,33.
  - À l'écart médian de Saxo, US30 donne +0,211 ATR [−0,136 ; +0,556].
- **US30 :** brut positif des deux côtés (+0,44 et +0,20), seul IC en bps au-dessus de 0 en brut (+7,9 bps [+0,8 ; +16,0]).
- **ETF :** frais faibles, mais environ 140 trades et un brut venu des gaps de nuit (GDX +0,41 contre +0,02 en séance).
- **GBPJPY Saxo** confirme la partie 1 (HistData) : brut nul.

### EXP-D02.0 — rétro-test de RE-1 figée sur des périodes jamais vues (BTC 2013-2019, or 2009-2019)
*Descriptive, préalable de D02. Données validées par le porteur ; panne de Bitstamp de janvier 2015 non négociable
(sensibilité sur la série brute : −0,047 contre −0,045). Aucun IC à borne basse positive.*

| Lecture (coût) | Espérance ATR [IC] | Brut ATR ; frais ATR | PnL : 0,25 %/ATR ; 1x | MDD : 0,25 %/ATR ; 1x | Trades | Années > 0 |
|---|---|---|---|---|---|---|
| BTC 2013-2019 (5) | −0,045 [−0,244 ; +0,157] | +0,06 ; 0,10 | −20 % ; −63 % | −48,5 % ; −91,6 % | 1 357 | 4/7 |
| BTC 2014-2019 (5) | −0,065 [−0,278 ; +0,152] | +0,04 ; 0,11 | −22 % ; −43 % | −47,4 % ; −84,5 % | 1 180 | 3/6 |
| Or 2009-2019 (4) | +0,011 [−0,246 ; +0,258] | +0,30 ; 0,29 | −3 % ; −5 % | −29,1 % ; −29,3 % | 1 253 | 7/11 |
| BTC 2020-2025 (5, réf.) | +0,369 [+0,098 ; +0,645] | +0,50 ; 0,14 | +138 % ; +204 % | −13,5 % ; −43,9 % | 1 080 | 6/6 |

- **BTC :** le brut manque (+0,06 ATR contre +0,50) ; 2014 (−0,740) et 2015 (−0,272) portent l'écart ; timing −0,061
  contre +0,362 ; F2b −0,224 contre +0,459.
- **Or :** brut positif sur 17 ans (+0,30 en 2009-2019, IC > 0 en log ; +0,24 en 2020-2025), absorbé par les frais à
  4 bps ; 2009-2015 positifs chaque année, 2016-2019 négatifs.

### EXP-D02 — walk-forward de H, R0 et de la frontière (protocole du porteur ; hors échantillon, coût principal)
*IS de 24 mois, OOS de 6 mois, seuils réestimés sur chaque IS, choix au centre de la plus grande zone connexe à Calmar
net > 0 ; 10 séries par actif, capital continu. Verdict du protocole : aucune variante ne surpasse RE-1 gelée, aucun
WFO n'est retenu face à son Statique ; RE-1 inchangée.*

| Série (coût) | Espérance ATR [IC] | Brut ; frais (ATR) | PnL : 0,25 %/ATR ; 1x | MDD : 0,25 %/ATR ; 1x | Calmar | Trades |
|---|---|---|---|---|---|---|
| BTC 2015-2025 · RE-1 gelée (5) | +0,218 [+0,032 ; +0,401] | +0,34 ; 0,12 | +159 % ; +396 % | −28,4 % ; −53,0 % | 0,32 | 2 075 |
| BTC 2015-2025 · WFO-R0 (5) | +0,291 [+0,088 ; +0,499] | +0,42 ; 0,13 | +214 % ; +478 % | −15,8 % ; −40,6 % | 0,69 | 1 836 |
| BTC 2015-2025 · WFO-conjointe (5) | +0,049 [−0,190 ; +0,284] | +0,17 ; 0,12 | +11 % ; −39 % | −34,0 % ; −60,9 % | 0,03 | 1 591 |
| SOL S2 2023-2025 · RE-1 gelée (5) | +0,252 [−0,191 ; +0,712] | +0,32 ; 0,07 | +27 % ; +114 % | −13,1 % ; −42,3 % | 0,76 | 405 |
| AVAX 2024-2025 · RE-1 gelée (5) | +0,074 [−0,301 ; +0,431] | +0,14 ; 0,06 | +5 % ; −17 % | −16,5 % ; −52,9 % | 0,15 | 329 |
| Or S2 2011-2025 · RE-1 gelée (4) | −0,045 [−0,273 ; +0,177] | +0,24 ; 0,29 | −10 % ; −7 % | −31,9 % ; −32,1 % | −0,02 | 1 637 |

- **BTC, WFO-R0 contre RE-1 gelée :** +0,074 ATR [−0,067 ; +0,225], non significatif ; lu dès 2016, +0,004. Le gain
  tient à 2015 et 2018 (R0 = 200 puis 50 avant de revenir à 100 dès le S2 2018).
- **BTC, chaque calibration vaut pour son époque :** RE-1 gelée +0,064 ATR en 2015-2019 et +0,357 en 2020-2025 ;
  Statique-R0 (R0 = 200 tiré de 2013-2014) +0,301 puis −0,191.
- **Recalibrer H dégrade :** WFO-H −0,174 ATR [−0,276 ; −0,074] face à Statique-H sur BTC ; sur entrées figées, l'effet
  de l'horizon est nul (calendrier, I-M16).
- **10 bps :** plus aucun IC > 0 sur BTC (RE-1 gelée +0,093, WFO-R0 +0,165).

### EXP-D02.1 — verrou fixe et WFO de H_exit ; WFO de R0 sur grille fine avec inertie ; stress (BTC 2015-2025)
*Verrou de 26 barres (option C : l'entrée suivante clôt la position), règle de D02 pour H ; inertie et grille de 9 valeurs
pour R0. Verdict : aucune des deux modifications ne surpasse RE-1 gelée ; RE-1 inchangée.*

| Série (5 bps) | Espérance ATR [IC] | Brut ; frais (ATR) | PnL : 0,25 %/ATR ; 1x | MDD : 0,25 %/ATR ; 1x | Calmar | Trades |
|---|---|---|---|---|---|---|
| RE-1 gelée | +0,218 [+0,032 ; +0,401] | +0,34 ; 0,12 | +159 % ; +396 % | −28,4 % ; −53,0 % | 0,32 | 2 075 |
| WFO-H_exit verrou 26 | +0,246 [+0,028 ; +0,467] | +0,37 ; 0,12 | +173 % ; +335 % | −28,4 % ; −53,0 % | 0,34 | 2 075 |
| WFO-R0 grille 9 inertie | +0,253 [+0,035 ; +0,465] | +0,38 ; 0,13 | +168 % ; +441 % | −35,7 % ; −56,3 % | 0,26 | 1 859 |
| WFO-R0 (D02) | +0,291 [+0,088 ; +0,499] | +0,42 ; 0,13 | +214 % ; +478 % | −15,8 % ; −40,6 % | 0,69 | 1 836 |

- **Verrou fixe :** il répare le WFO-H (+0,227 ATR [+0,090 ; +0,365] face à celui de D02), mais les sorties choisies
  n'ont aucun effet sur les mêmes entrées (+0,029 [−0,075 ; +0,139]).
- **WFO-R0 de D02 :** son avance tenait au départage de 2018-S2 vers R0 = 100 ; avec l'inertie, −0,065 ATR [−0,155 ;
  −0,002].
- **Stress :** sans le 1 % meilleur (21 trades), RE-1 gelée fait +0,035 ATR [−0,128 ; +0,199] et +9 %. À 10 bps et sans
  le 1 % meilleur, toutes les séries sont négatives.

### EXP-D03 — filtre de compression et portefeuille BTC + SOL (RE-1 gelée, version finale)
*Aucune optimisation. Filtre du porteur : ATR14 ≤ P60 glissant sur 24 mois. Portefeuille : capital commun, 0,25 %/ATR
par trade sur chaque actif.*

| Série (5 bps) | Espérance ATR [IC] | PnL : 0,25 %/ATR ; 1x | MDD : 0,25 %/ATR ; 1x | Calmar | Trades |
|---|---|---|---|---|---|
| BTC 2015-2025 · RE-1 gelée | +0,218 [+0,032 ; +0,401] | +159 % ; +396 % | −28,4 % ; −53,0 % | 0,32 | 2 075 |
| BTC 2015-2025 · RE-1 + filtre ATR (entrées figées) | +0,258 [+0,024 ; +0,486] | +125 % ; +205 % | −22,3 % ; −40,2 % | 0,34 | 1 506 |
| 2021-07 → 2025 · BTC seul | +0,370 [+0,050 ; +0,686] | +90 % ; +118 % | −12,9 % ; −29,9 % | 1,18 | 806 |
| 2021-07 → 2025 · portefeuille BTC + SOL | — | +163 % ; +478 % | −15,2 % ; −40,1 % | 1,58 | 1 575 |

- **Filtre ATR :** Calmar inchangé (écart apparié +0,03, 43 % des chemins) ; il garde le top 1 % mais retire 12 Alpha ;
  gain limité à 2020-2025, absent sur SOL.
- **Portefeuille :** corrélation mensuelle BTC / SOL −0,04 ; Calmar 1,18 → 1,58 ; plus longue période sous le pic non
  raccourcie (238 jours) ; avantage de SOL seul +0,190 ATR [−0,079 ; +0,484].
- **Profil :** le « calme » des 5 % meilleurs trades tient au classement en ATR ; classés en bps, ils naissent à ATR
  haut.

### EXP-D03.1 — viabilité et sécurité de RE-1 (lectures, moteur inchangé)
*Stop catastrophe de 4 ATR sur tous les trades ; glissement de 0,5 ATR sur les stops de F3 ; entrée retardée d'une
barre. 5 bps, 0,25 %/ATR.*

| Série | Espérance ATR [IC] | PnL : 0,25 %/ATR ; 1x | MDD : 0,25 %/ATR ; 1x | Calmar | Pire trade (capital) |
|---|---|---|---|---|---|
| BTC 2015-2025 · RE-1 gelée | +0,218 [+0,032 ; +0,401] | +159 % ; +396 % | −28,4 % ; −53,0 % | 0,32 | −6,2 % |
| BTC 2015-2025 · stop 4 ATR | +0,180 [+0,012 ; +0,350] | +128 % ; +385 % | −21,4 % ; −42,5 % | 0,36 | −1,05 % |
| BTC 2015-2025 · entrée retardée | +0,232 [+0,050 ; +0,412] | +170 % ; +259 % | −23,9 % ; −49,4 % | 0,39 | |
| BTC 2015-2025 · glissement 0,5 ATR | +0,102 [−0,083 ; +0,290] | +45 % ; +39 % | −35,4 % ; −61,1 % | 0,10 | |

- **Stop catastrophe :** coût −0,037 ATR non significatif sur 2015-2025, mais −0,121 [−0,237 ; −0,006] sur 2020-2025 et
  −9,9 bps sur SOL ; pire perte d'un trade ramenée à environ 1 % du capital.
- **Latence :** sans effet. **Glissement des stops :** −0,115 ATR par trade pour 0,5 ATR ; c'est le risque d'exécution
  principal.

### RE-1 version finale (décision du porteur, 2026-10-03)
*RE-1 gelée et stop catastrophe de 4 ATR14(t) greffé sur tous les trades (`strategy.final`). Elle redonne trade par
trade la série « Stop catastrophe 4 ATR » de D03.1 : BTC 2015-2025 +0,180 ATR [+0,012 ; +0,350], MDD −21,4 % (1x
−42,5 %) ; SOL +0,135 ATR. Testée sur la réserve en EXP-D04 (ETH, XRP, 2026), protocole pré-enregistré.*

### EXP-D04 — épreuve de la réserve (version finale de RE-1, protocole pré-enregistré)
*Stop catastrophe de 4 ATR inclus ; 0,25 %/ATR ; 5 bps (or 4 bps). Hors échantillon pour RE-1 : aucun paramètre choisi sur
ces données ; ETH, XRP et BTC 2026 avaient été vus par d'anciens projets.*

| Série | Espérance ATR [IC] | PnL : 0,25 %/ATR ; 1x | MDD : 0,25 %/ATR ; 1x | Trades | Pire journée UTC |
|---|---|---|---|---|---|
| ETH 2017-2026 | +0,183 [−0,010 ; +0,385] | +82 % ; +155 % | −39,1 % ; −72,1 % | 1 525 | −3,03 % |
| XRP 2016-2026 | +0,263 [−0,014 ; +0,640] | +148 % ; +354 % | −20,9 % ; −61,7 % | 1 689 | −2,57 % |
| BTC 2026 (9 mois) | +0,705 [+0,045 ; +1,469] | +29 % ; +52 % | −6,9 % ; −8,6 % | 135 | −1,18 % |
| SOL 2026 | +0,410 [−0,081 ; +0,997] | +15 % ; +36 % | −6,0 % ; −19,6 % | 138 | −1,83 % |
| AVAX 2026 | +1,059 [+0,328 ; +1,784] | +32 % ; +61 % | −4,7 % ; −9,9 % | 109 | −1,11 % |
| Or 2026 (4 bps) | +0,987 [+0,449 ; +1,479] | +21 % ; +26 % | −3,1 % ; −5,6 % | 81 | −1,48 % |

- **Signe tenu hors échantillon,** marge mince : sans le 1 % meilleur, ETH et XRP ≈ −0,06 ATR ; un trade de XRP
  (juillet 2023) = 56 % de la somme. 2026 est la période la plus favorable mesurée, à ne pas extrapoler.

## Pistes écartées (à ne pas retester sans élément nouveau)

| Piste | Raison | Source |
|---|---|---|
| Stop-and-reverse natif | −98,7 % ; frais ≈ 30 200 bps pour un brut de −2 047 bps | Phase 0 |
| Tous les signaux à horizon fixe | −3,7 à −16,0 bps par trade de H6 à H48 | C01 |
| Entrée en continuation (R3, `nis_z_100` Q4) | +10,3 bps [+1,3 ; +19,8] à H26 seulement, porté par 2020-2021 ; écartée par le porteur | C01 |
| R1, F1, F5 (x1 encore opposé) | aucune espérance nette positive, avec ou sans stop ; les frais coûtent 0,135 ATR par trade sur F5 ; rejet définitif (décision du porteur) : x1 retourné est un prérequis d'entrée | C02 |
| Stop sur F2b | coupe les gagnants : −0,15 à −0,38 ATR par trade | C02 |
| Stop de catastrophe à 5 ATR sur F2b dans le moteur (RE-3) | −0,08 ATR par trade, drawdown plus élevé, Calmar 0,77 contre 1,16 ; repris ensuite à 4 ATR sur tous les trades comme assurance contre la ruine, non comme amélioration (décision du porteur, 2026-10-03) | C02bis, D03.1 |
| Réouverture immédiate après un stop (H ≤ 32) | les trades débloqués font −0,15 à −1,38 ATR ; le cooldown fait mieux | C02bis |
| Horizon propre à chaque sous-famille (F2b à H28) | à H28 : F3 +0,148 ATR, DD −16,2 %, Calmar 0,92 ; paramètre libre choisi après lecture ; H = 26 verrouillé (décision du porteur) | C02bis |
| Take-profit fixe sur RE-1 (2 à 6 ATR) | même la borne optimiste (TP pris dès que la MFE26 l'atteint) reste sous RE-1 : +0,200 à +0,347 ATR contre +0,369 ; exclu (décision du porteur, vérifiée) | C03 |
| Break-even différé sur RE-1, m ≤ 1,5 ATR | ampute la queue droite ; effet apparié jusqu'à −0,157 ATR par trade ; significatif pour F2b à H24 et H28 | C03 |
| Break-even différé sur RE-1, m ≥ 2 ATR | effet apparié de −0,02 à +0,03 ATR par trade ; baisse du drawdown non significative ; non retenu (KISS) | C03 |
| Break-even comme variante de gestion du risque (V3 ou V2, m = 2) | gain de MDD non démontré (82 à 92 % des chemins), Calmar fragile, drawdowns plus longs ; à MDD égal, équivaut à réduire la taille ; perdu dès 5 bps de glissement du break-even | C03, analyse approfondie |
| Veto des signaux contre la tendance (EMA 200, EMA 50, Kalman v2.1 sur 4 h) | les trades contre-tendance valent autant ou plus que les alignés (+0,39 à +0,43 ATR) et portent jusqu'à 48 % du décile supérieur ; espérance +0,369 → +0,22 à +0,26 ; Calmar 1,16 → 0,41 à 0,49 ; pire à 10 bps et sur tout le plateau | C04 |
| Stop à l'extremum pour les retracements de 0,75 à 0,85 (frontière F2b / F3 abaissée) | coupe les meilleurs F2b (+0,9 à +1,0 ATR sans stop) ; frontière 0,75 : −0,095 ATR par trade [−0,157 ; −0,030], MDD −19,2 % | C05 |
| Exclusion de `nis_z_100` relâchée (P80 à P90) | les signaux admis perdent (−0,29 à −0,53 ATR) ; −0,06 à −0,15 ATR par trade, significatif ; Calmar 0,84 → 0,56 | C05 |
| Walk-forward de H, R0 et de la frontière (recalibrage semestriel sur 24 mois) | aucune variante ne surpasse RE-1 gelée ; recalibrer H ne fait que déplacer le calendrier ; l'avance du WFO-R0 tenait à un départage vers RE-1 ; abandon définitif décidé par le porteur (2026-10-03) | D02, D02.1 |
