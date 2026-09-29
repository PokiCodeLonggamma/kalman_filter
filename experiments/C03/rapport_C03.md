# EXP-C03 — Break-even différé sur RE-1

- **Date :** 2026-09-29
- **Étape :** C Enveloppe. Un seul facteur est testé (OFAT) sur la configuration de référence.
- **Actif et période :** BTC/USD Bitstamp 30 min, 2020-01 → 2025-12 (72 mois). 2026, ETH et XRP ne sont pas lus.
- **Frais :** 5 et 10 bps aller-retour. Capital à 0,25 % par ATR14(t), levier ≤ 1x ; 1x en référence.
- **Contrôle :** RE-1, validé par le porteur.
  - Univers : R2 hors `nis_z_100` Q4.
  - F2b sans stop ; F3 SL-B à l'extremum.
  - Pyramiding 0 ; cooldown jusqu'à t + 1 + H.
  - H = 26 ; H = 24 et 28 pour vérifier le plateau.

## 0. Cadrage

- **QUESTION :** on remonte le stop au point d'entrée après une excursion favorable de +m · ATR14(t).
  - Économise-t-on plus sur les trades qui avaient un gain latent puis ont fini en perte qu'on ne perd sur les grands gagnants repassés par l'entrée avant de repartir ?
  - Sur quel périmètre : F3, F2b ou les deux ? Pour quel m ∈ {1 ; 1,5 ; 2 ; 2,5 ; 3 ; 4} ?
- **PERTINENCE POUR LE FILTRE AKF :** l'espérance de RE-1 vient de la queue droite des breakouts de compression. Le break-even est la seule protection de gain qui ne plafonne pas les gagnants ; le porteur a exclu le take-profit fixe.
- **CE QUE LE PROTOCOLE MESURE RÉELLEMENT :**
  - l'effet apparié BE − RE-1 sur les mêmes 1 080 entrées (lecture cooldown, I-M9), en ATR et en bps, avec son IC par grappes mensuelles ;
  - sa décomposition en trades sauvés et coupés ;
  - la queue droite et le drawdown ;
  - les 8 métriques à 5 et 10 bps, les années, le plateau H24-28 ;
  - en annexe : la réouverture immédiate et la borne optimiste d'un take-profit fixe.
- **CE QU'IL NE PERMET PAS DE CONCLURE :**
  - une validation hors échantillon ;
  - l'effet d'un break-even décalé (niveau autre que l'entrée + 5 bps), d'un trailing stop ou d'une sortie partielle, non testés ;
  - le choix d'un m : retenir le meilleur des 18 couples (périmètre, m) après lecture serait une sélection dans l'échantillon.

## 1. [CODE] Implémentation et contrôles

**`breakeven_trades`** (`src/envelope/stops.py`) :
- Le stop initial reste exécuté par `apply_stop` (copie certifiée, inchangée).
- Le seuil d'activation vaut open[t + 1] ± m · ATR14(t) (`breakeven_trigger_levels`). Il est lu sur le high (Long) ou le low (Short) des barres t + 1 … t + H − 1.
- Si le stop initial est touché sur une barre ≤ b, il prime, y compris sur la barre d'activation b.
- Sinon, le stop passe à open[t + 1] ± 5 bps de b + 1 à t + H. La sortie se fait au niveau, ou à l'ouverture en cas de gap (y compris en b + 1).
- Le niveau est le même à 10 bps de frais (consigne du porteur) : un break-even rend alors −5 bps net.
- `stop_trades` partage désormais la sélection séquentielle ; son comportement est inchangé.

**7 tests nouveaux :**
- cas construits en Long et en Short (miroir des prix) ;
- priorité du stop initial sur la même barre ;
- fenêtre d'activation ;
- référence barre par barre sur 500 signaux aléatoires, dans trois réglages ;
- équivalence sans break-even (None, NaN, seuil inatteignable) ;
- réouverture à la barre du break-even ;
- causalité par troncature.

Suite complète : 194 réussis, 2 ignorés.

**Contrôles bloquants passés :**
- ancre P6.5d reproduite ;
- RE-1 identique à C02bis trade par trade, à H24, 26 et 28, dans les deux lectures ; 12 lignes de métriques identiques à `resultats_C02bis.csv` ;
- un seuil infini redonne RE-1 ;
- effet apparié exactement nul sur les trades non sortis au break-even.

**Calcul :** 228 lignes en 95 s (3 horizons × 19 configurations × 2 lectures × 2 niveaux de frais).

**Drawdown :** le MDD dépend de l'ordre des trades. Son effet apparié est lu sur 2 000 chemins où les mois d'entrée sont tirés avec remise (mêmes tirages que les IC). On en donne la plage P2,5-P97,5 et la part des chemins où le break-even est moins profond. Ce n'est pas un IC centré sur l'écart observé (I-M10).

## 2. [OBS] Mesures

### 2.1 Huit métriques à H = 26 (cooldown, 5 bps)

PnL et drawdown à 0,25 % par ATR. Tableau complet en annexe B.

| Configuration | PnL : 0,25 %/ATR ; 1x ; bps | PF | WR | Espérance ATR [IC] ; bps | MDD | Trades ; stop initial ; BE | Durée méd. | Part des frais | Calmar | Effet apparié ATR [IC] |
|---|---|---|---|---|---|---|---|---|---|---|
| RE-1 | +138 % ; +204 % ; +13 320 | 1,20 | 44,3 % | +0,369 [+0,098 ; +0,645] ; +12,3 | −13,5 % | 1 080 (15,0/mois) ; 24 % ; — | 26 | 29 % | 1,16 | — |
| V1 (F3), m = 1 | +117 % ; +131 % ; +10 154 | 1,19 | 36,2 % | +0,333 [+0,095 ; +0,581] ; +9,4 | −17,5 % | 1 080 ; 14 % ; 24 % | 26 | 35 % | 0,79 | −0,036 [−0,143 ; +0,063] |
| V1, m = 2 | +128 % ; +156 % ; +11 396 | 1,18 | 40,6 % | +0,354 [+0,105 ; +0,614] ; +10,6 | −13,1 % | 1 080 ; 19 % ; 12 % | 26 | 32 % | 1,13 | −0,015 [−0,089 ; +0,047] |
| V1, m = 4 | +139 % ; +185 % ; +12 595 | 1,19 | 43,8 % | +0,373 [+0,106 ; +0,643] ; +11,7 | −13,1 % | 1 080 ; 22 % ; 3 % | 26 | 30 % | 1,20 | +0,004 [−0,026 ; +0,033] |
| V2 (F2b), m = 1 | +79 % ; +125 % ; +9 846 | 1,19 | 30,6 % | +0,248 [+0,028 ; +0,481] ; +9,1 | −12,2 % | 1 080 ; 24 % ; 30 % | 23 | 35 % | 0,83 | −0,121 [−0,249 ; +0,001] |
| V2, m = 2 | +136 % ; +211 % ; +13 399 | 1,22 | 39,0 % | +0,365 [+0,134 ; +0,602] ; +12,4 | −12,9 % | 1 080 ; 24 % ; 13 % | 26 | 29 % | 1,19 | −0,004 [−0,082 ; +0,089] |
| V2, m = 4 | +148 % ; +242 % ; +14 435 | 1,22 | 43,0 % | +0,394 [+0,143 ; +0,654] ; +13,4 | −15,0 % | 1 080 ; 24 % ; 3 % | 26 | 27 % | 1,09 | +0,026 [−0,029 ; +0,103] |
| V3 (les deux), m = 1 | +63 % ; +71 % ; +6 680 | 1,17 | 22,6 % | +0,212 [+0,030 ; +0,407] ; +6,2 | −15,5 % | 1 080 ; 14 % ; 54 % | 12 | 45 % | 0,55 | −0,157 [−0,318 ; +0,007] |
| V3, m = 2 | +126 % ; +163 % ; +11 475 | 1,21 | 35,3 % | +0,350 [+0,142 ; +0,570] ; +10,6 | −11,7 % | 1 080 ; 19 % ; 25 % | 26 | 32 % | 1,25 | −0,018 [−0,131 ; +0,105] |
| V3, m = 4 | +149 % ; +222 % ; +13 711 | 1,21 | 42,5 % | +0,398 [+0,151 ; +0,649] ; +12,7 | −14,5 % | 1 080 ; 22 % ; 6 % | 26 | 28 % | 1,13 | +0,030 [−0,035 ; +0,118] |

- Le win rate baisse mécaniquement : une sortie au break-even rend 0 net à 5 bps et ne compte pas comme gagnante.
- Mêmes entrées partout : la cadence reste de 15 trades par mois.

### 2.2 Effet apparié : aucun seuil n'améliore l'espérance

- **m ≤ 1,5 : effet négatif sur F2b et sur les deux sous-familles.**
  - À H26 : V2 à m = 1 perd −0,121 ATR [−0,249 ; +0,001], V3 à m = 1 perd −0,157 [−0,318 ; +0,007].
  - La perte est significative à H24 (V2 : −0,119 [−0,240 ; −0,004] ; V3 : −0,147 [−0,290 ; −0,005]) et à H28 (V2 : −0,150 [−0,297 ; −0,014]).
- **m ≥ 2 : effet nul.** Il va de −0,018 à +0,030 ATR à H26, avec des IC d'environ ±0,1, et de −0,021 à +0,028 à H24 et H28.
- **V1 (break-even sur F3 seul) :** proche de 0 à tous les seuils et horizons (−0,036 à +0,008).
- **Aucune année stable.** V3 à m = 2 donne, de 2020 à 2025 : +0,05 ; 0,00 ; −0,18 ; +0,02 ; +0,10 ; −0,11 ATR. L'année 2022 pénalise tous les break-even sur F3 à m ≤ 2,5.

### 2.3 Mécanique : ce que le break-even sauve et ce qu'il coupe

Réponse à la question du porteur : pour m ≥ 2, les deux plateaux de la balance ont le même poids ; pour m ≤ 1,5, le coût l'emporte.

**Exemple : V3 à m = 2, H26.**
- 565 trades atteignent le seuil (52 %) ; 268 sortent au break-even (25 %, dont 13 en gap).
- **147 trades sauvés :** +1,98 ATR chacun ; ils finissaient à −2,01 dans RE-1.
- **121 trades coupés :** −2,57 ATR chacun ; ils finissaient à +2,51.
- Bilan : +0,270 ATR par trade de gain, −0,288 de coût, soit −0,018 d'effet.
- 36 des coupés finissaient au-delà de +3 ATR ; ils coûtent à eux seuls 0,206 ATR par trade.

**À m = 1 :**
- 309 sauvés (+1,99) contre 273 coupés (−2,87), soit −0,157 d'effet.
- F2b y perd 0,228 ATR par trade de F2b : +0,459 → +0,231.

**À m = 4 :** le break-even ne sort plus que 6 % des trades, et la balance est à +0,030.

### 2.4 Queue droite

- **RE-1 :**
  - P90 à +5,53 ATR, P95 à +8,44 ;
  - 11,3 % des trades au-delà de +5 ATR ;
  - les 10 % meilleurs trades, à +9,19 ATR en moyenne, apportent 0,92 ATR par trade, soit plus que l'espérance totale (+0,369).
- **V3 selon m :**

  | V3 | P90 | Trades > +5 ATR |
  |---|---|---|
  | m = 1 | +3,85 | 7,1 % |
  | m = 2 | +4,90 | 9,6 % |
  | m = 4 | +5,26 | 10,7 % |

- Le break-even ampute la queue droite d'autant plus que m est bas.

### 2.5 Drawdown : une tendance, sans significativité

- **V3 à m = 2 est la seule variante dont le drawdown baisse à tous les horizons :**
  - −13,5 → −11,7 % à H26 ;
  - −14,2 → −11,2 % à H24 ;
  - −16,2 → −12,5 % à H28 ;
  - −15,9 → −13,4 % à 10 bps.
- **Cette baisse n'est pas significative.** Sur les chemins réordonnés, l'écart vaut +1,6 point [−2,1 ; +11,6], et le drawdown est moins profond dans 89 % des chemins (H26).
- Aucune plage n'exclut 0. Selon le couple, la part des chemins moins profonds va de 0,55 à 0,92.
- **Le MDD ne varie pas de façon monotone avec m.** Pour V3 à H26 : −15,5 % (m = 1), −15,8 (1,5), −11,7 (2), −12,3 (2,5), −13,4 (3), −14,5 % (4).

### 2.6 À 10 bps

- **RE-1 :** +0,233 ATR [−0,041 ; +0,511], +72 %, drawdown −15,9 %.
- **V2 et V3 à m = 4 :** IC juste au-dessus de 0 (+0,259 [+0,003 ; +0,522] ; +0,263 [+0,014 ; +0,514]).
- **Ce n'est pas un gain démontré :** leur effet apparié n'est pas significatif (+0,026 ; +0,030). L'IC se resserre parce que le break-even réduit la variance.

### 2.7 Take-profit fixe et excursion : la décision du porteur est vérifiée

- **Borne optimiste :** le TP est pris dès que la MFE26 l'atteint, stops ignorés.
  - L'espérance va de +0,200 ATR (TP à 2 ATR) à +0,347 (TP à 6 ATR), toujours sous RE-1 (+0,369).
  - Le porteur avait trouvé +0,199 à +0,350 ; le P90 mesuré vaut +5,53 ATR (porteur : +5,6).
- **Borne réaliste :** le TP doit être atteint avant la sortie de RE-1. L'espérance va de +0,040 à +0,229 ATR.
- **Excursion favorable.**
  - Atteignent un seuil de MFE26 : 66,7 % des trades pour +1,5 ATR, 57,2 % pour +2 ATR.
  - L'atteignent puis finissent en perte nette : 24,9 % et 18,3 % des trades, à −1,99 et −2,04 ATR en moyenne.
  - Les 23,9 % et 17,5 % du porteur correspondent donc à « atteint puis finit en perte », pas à « atteint ».

### 2.8 Réouverture immédiate (annexe I)

- Dans les 19 configurations, les trades débloqués par une sortie anticipée perdent : −0,06 à −0,68 ATR.
- La réouverture baisse partout l'espérance, de 0,03 à 0,11 ATR, et le Calmar.
- Le cooldown reste la bonne convention, avec ou sans break-even.

## 3. [HYP] Lectures

- **Le break-even ne distingue pas le retest de l'échec.** Après +2 ATR, un trade activé sur deux repasse par l'entrée (268 sur 565). Ceux qui repartent ensuite valent autant que ceux que le break-even sauve. C'est la même physique que le stop sur F2b en C02 : la moitié des trades passent par −2 ATR avant l'expansion.
- **Toute l'espérance est dans le décile supérieur**, qui apporte 0,92 ATR par trade contre 0,37 au total. Une règle qui écrête ou coupe les trajectoires bruyantes doit se payer par autant d'économies à gauche.
- **La sortie à H26 et le cooldown font déjà l'essentiel de la gestion du risque.**
- **Le léger gain de drawdown de V3 à m = 2-2,5 viendrait de la variance réduite** (moins de grands écarts dans les deux sens), pas d'une asymétrie exploitable.

## 4. [DECISION] Proposée (rien n'est lancé)

- [x] **REJETÉ pour m ≤ 1,5 :** le break-even ampute la queue droite et dégrade l'espérance. La perte est significative pour F2b à H24 et à H28.
- [x] **NON CONCLUANT pour m ≥ 2 :**
  - l'effet sur l'espérance est nul ;
  - le drawdown ne baisse pas de façon significative.

  Selon le critère du porteur, le break-even n'est pas retenu, et **RE-1 reste intact**.
- **Take-profit fixe :** exclusion confirmée. Même la borne optimiste reste sous RE-1.
- **Cooldown :** confirmé, y compris avec break-even.
- **Si le porteur tient au drawdown :** V3 à m = 2 est la seule variante dont le drawdown baisse aux trois horizons (de 1,8 à 3,7 points).
  - Cette baisse n'est pas significative et coûte −0,018 ATR par trade.
  - Retenir cette variante reviendrait à choisir un paramètre après lecture, comme un H propre à chaque sous-famille.
- **Points à trancher par le porteur :**
  - la suite : le filtre de tendance macro (dernier facteur prévu de l'Étape C) ou l'Étape D (walk-forward sur RE-1) ;
  - l'hypothèse d'exécution : à 10 bps, l'IC de RE-1 contient 0.

---

# Annexes chiffrées (générées par `run_C03.py`)

## A. Contrôles bloquants et conventions

| Contrôle | Résultat |
|---|---|
| Ancre P6.5d, sans stop et stop 2,5 % | 6 037 et 6 589 trades identiques au fichier de référence |
| RE-1 = RE-1 de C02bis | trades identiques à H ∈ {24, 26, 28}, cooldown et réouverture ; 12 lignes de métriques identiques à resultats_C02bis.csv (écart relatif max 4,5·10⁻⁶) |
| Seuil d'activation infini | redonne RE-1 trade par trade (V3, les deux lectures, trois horizons) |
| Effet apparié | nul sur tous les trades non sortis au break-even (vérifié pour chaque variante) |
| Univers | R2 hors Q4 = 1452 signaux : F2b 741, F3 711 ; familles identiques à B01 |
| Break-even | seuil m · ATR14(t) lu sur high (Long) ou low (Short) des barres t + 1 … t + H − 1 ; stop initial prioritaire sur la barre d'activation ; stop à open[t + 1] ± 5 bps de b + 1 à t + H (niveau identique à 10 bps de frais) ; gap : sortie à l'ouverture |
| IC 95 % | grappes mensuelles d'entrée, 2 000 tirages ; effets appariés sur les entrées de RE-1 (lecture cooldown) |
| Capital | 1 ATR14(t) = 0,25 % du capital, levier ≤ 1x ; notionnel 1x en référence ; Calmar = PnL annualisé sur 6 ans / valeur absolue du MDD valorisé, à 0,25 % par ATR |
| Période | 2020-01 → 2025-12 (72 mois) ; aucune barre de 2026 lue |

## B. Tableau complet à H = 26 (lecture cooldown)

**5 bps aller-retour — 8 métriques**

| Configuration | PnL : 0,25 %/ATR ; 1x ; bps (1x) | PF : 1x ; pondéré | WR | Espérance : bps [IC] ; ATR [IC] | MDD valorisé : 0,25 %/ATR ; 1x | Trades (/mois) ; stop initial ; BE | Durée méd. | Part des frais ; brut/trade |
|---|---|---|---|---|---|---|---|---|
| RE-1 (contrôle) | +138 % ; +204 % ; +13320 | 1,20 ; 1,28 | 44,3 % | +12,3 [+0,2 ; +24,4] ; +0,369 [+0,098 ; +0,645] | −13,5 % ; −44 % | 1 080 (15,0) ; 24 % ; 0 % | 26 | 29 % ; +17,3 |
| V1 — BE 1,0 ATR (F3) | +117 % ; +131 % ; +10154 | 1,19 ; 1,31 | 36,2 % | +9,4 [−1,7 ; +20,6] ; +0,333 [+0,095 ; +0,581] | −17,5 % ; −49 % | 1 080 (15,0) ; 14 % ; 24 % | 26 | 35 % ; +14,4 |
| V1 — BE 1,5 ATR (F3) | +122 % ; +129 % ; +10160 | 1,17 ; 1,30 | 39,1 % | +9,4 [−1,4 ; +20,3] ; +0,345 [+0,101 ; +0,598] | −16,0 % ; −46 % | 1 080 (15,0) ; 17 % ; 16 % | 26 | 35 % ; +14,4 |
| V1 — BE 2,0 ATR (F3) | +128 % ; +156 % ; +11396 | 1,18 ; 1,29 | 40,6 % | +10,6 [−1,0 ; +22,3] ; +0,354 [+0,105 ; +0,614] | −13,1 % ; −42 % | 1 080 (15,0) ; 19 % ; 12 % | 26 | 32 % ; +15,6 |
| V1 — BE 2,5 ATR (F3) | +137 % ; +197 % ; +12969 | 1,20 ; 1,30 | 41,9 % | +12,0 [+0,4 ; +24,0] ; +0,371 [+0,114 ; +0,634] | −12,4 % ; −41 % | 1 080 (15,0) ; 21 % ; 8 % | 26 | 29 % ; +17,0 |
| V1 — BE 3,0 ATR (F3) | +135 % ; +179 % ; +12375 | 1,19 ; 1,29 | 42,6 % | +11,5 [−0,6 ; +23,6] ; +0,368 [+0,108 ; +0,628] | −12,7 % ; −43 % | 1 080 (15,0) ; 21 % ; 5 % | 26 | 30 % ; +16,5 |
| V1 — BE 4,0 ATR (F3) | +139 % ; +185 % ; +12595 | 1,19 ; 1,29 | 43,8 % | +11,7 [−0,5 ; +23,9] ; +0,373 [+0,106 ; +0,643] | −13,1 % ; −44 % | 1 080 (15,0) ; 22 % ; 3 % | 26 | 30 % ; +16,7 |
| V2 — BE 1,0 ATR (F2b) | +79 % ; +125 % ; +9846 | 1,19 ; 1,25 | 30,6 % | +9,1 [−1,2 ; +19,4] ; +0,248 [+0,028 ; +0,481] | −12,2 % ; −38 % | 1 080 (15,0) ; 24 % ; 30 % | 23 | 35 % ; +14,1 |
| V2 — BE 1,5 ATR (F2b) | +114 % ; +191 % ; +12611 | 1,22 ; 1,29 | 35,1 % | +11,7 [+1,0 ; +22,5] ; +0,327 [+0,096 ; +0,573] | −14,7 % ; −44 % | 1 080 (15,0) ; 24 % ; 21 % | 26 | 30 % ; +16,7 |
| V2 — BE 2,0 ATR (F2b) | +136 % ; +211 % ; +13399 | 1,22 ; 1,31 | 39,0 % | +12,4 [+1,4 ; +23,4] ; +0,365 [+0,134 ; +0,602] | −12,9 % ; −42 % | 1 080 (15,0) ; 24 % ; 13 % | 26 | 29 % ; +17,4 |
| V2 — BE 2,5 ATR (F2b) | +130 % ; +198 % ; +13010 | 1,21 ; 1,29 | 40,4 % | +12,0 [+0,6 ; +23,3] ; +0,354 [+0,113 ; +0,595] | −14,3 % ; −45 % | 1 080 (15,0) ; 24 % ; 9 % | 26 | 29 % ; +17,0 |
| V2 — BE 3,0 ATR (F2b) | +144 % ; +232 % ; +14117 | 1,22 ; 1,31 | 41,6 % | +13,1 [+1,2 ; +24,7] ; +0,377 [+0,129 ; +0,627] | −14,4 % ; −45 % | 1 080 (15,0) ; 24 % ; 6 % | 26 | 28 % ; +18,1 |
| V2 — BE 4,0 ATR (F2b) | +148 % ; +242 % ; +14435 | 1,22 ; 1,31 | 43,0 % | +13,4 [+1,5 ; +25,4] ; +0,394 [+0,143 ; +0,654] | −15,0 % ; −46 % | 1 080 (15,0) ; 24 % ; 3 % | 26 | 27 % ; +18,4 |
| V3 — BE 1,0 ATR (F2b+F3) | +63 % ; +71 % ; +6680 | 1,17 ; 1,28 | 22,6 % | +6,2 [−3,0 ; +15,8] ; +0,212 [+0,030 ; +0,407] | −15,5 % ; −44 % | 1 080 (15,0) ; 14 % ; 54 % | 12 | 45 % ; +11,2 |
| V3 — BE 1,5 ATR (F2b+F3) | +99 % ; +119 % ; +9452 | 1,19 ; 1,31 | 29,9 % | +8,8 [−1,1 ; +19,0] ; +0,304 [+0,097 ; +0,527] | −15,8 % ; −46 % | 1 080 (15,0) ; 17 % ; 37 % | 22 | 36 % ; +13,8 |
| V3 — BE 2,0 ATR (F2b+F3) | +126 % ; +163 % ; +11475 | 1,21 ; 1,33 | 35,3 % | +10,6 [−0,3 ; +21,7] ; +0,350 [+0,142 ; +0,570] | −11,7 % ; −40 % | 1 080 (15,0) ; 19 % ; 25 % | 26 | 32 % ; +15,6 |
| V3 — BE 2,5 ATR (F2b+F3) | +129 % ; +192 % ; +12659 | 1,21 ; 1,31 | 38,0 % | +11,7 [+0,4 ; +22,6] ; +0,357 [+0,133 ; +0,586] | −12,3 % ; −42 % | 1 080 (15,0) ; 21 % ; 17 % | 26 | 30 % ; +16,7 |
| V3 — BE 3,0 ATR (F2b+F3) | +141 % ; +206 % ; +13172 | 1,21 ; 1,32 | 39,9 % | +12,2 [+0,6 ; +23,6] ; +0,377 [+0,140 ; +0,616] | −13,4 % ; −45 % | 1 080 (15,0) ; 21 % ; 12 % | 26 | 29 % ; +17,2 |
| V3 — BE 4,0 ATR (F2b+F3) | +149 % ; +222 % ; +13711 | 1,21 ; 1,32 | 42,5 % | +12,7 [+0,7 ; +24,6] ; +0,398 [+0,151 ; +0,649] | −14,5 % ; −45 % | 1 080 (15,0) ; 22 % ; 6 % | 26 | 28 % ; +17,7 |

**5 bps — sens, sous-familles, régularité, break-even**

| Configuration | Long / Short (ATR) | Timing ATR [IC] | F2b : esp. ATR | F3 : esp. ATR | Années > 0 : ATR ; PnL | PnL annualisé ; Calmar | BE activé ; sorti au BE (dont gap) |
|---|---|---|---|---|---|---|---|
| RE-1 (contrôle) | +0,46 / +0,27 | +0,362 [+0,089 ; +0,638] | +0,459 | +0,267 | 6/6 ; 6/6 | +15,6 % ; 1,16 | 0 % ; 0 % (0,0 %) |
| V1 — BE 1,0 ATR (F3) | +0,40 / +0,25 | +0,327 [+0,089 ; +0,574] | +0,459 | +0,190 | 5/6 ; 4/6 | +13,8 % ; 0,79 | 32 % ; 24 % (2,5 %) |
| V1 — BE 1,5 ATR (F3) | +0,42 / +0,26 | +0,339 [+0,095 ; +0,592] | +0,459 | +0,217 | 5/6 ; 4/6 | +14,2 % ; 0,89 | 27 % ; 16 % (0,9 %) |
| V1 — BE 2,0 ATR (F3) | +0,45 / +0,24 | +0,346 [+0,097 ; +0,603] | +0,459 | +0,236 | 6/6 ; 6/6 | +14,7 % ; 1,13 | 23 % ; 12 % (0,6 %) |
| V1 — BE 2,5 ATR (F3) | +0,45 / +0,28 | +0,365 [+0,110 ; +0,624] | +0,459 | +0,272 | 6/6 ; 6/6 | +15,5 % ; 1,25 | 19 % ; 8 % (0,2 %) |
| V1 — BE 3,0 ATR (F3) | +0,46 / +0,26 | +0,361 [+0,103 ; +0,622] | +0,459 | +0,266 | 6/6 ; 5/6 | +15,3 % ; 1,21 | 16 % ; 5 % (0,1 %) |
| V1 — BE 4,0 ATR (F3) | +0,46 / +0,27 | +0,365 [+0,102 ; +0,634] | +0,459 | +0,275 | 5/6 ; 5/6 | +15,6 % ; 1,20 | 12 % ; 3 % (0,0 %) |
| V2 — BE 1,0 ATR (F2b) | +0,27 / +0,23 | +0,246 [+0,030 ; +0,470] | +0,231 | +0,267 | 6/6 ; 6/6 | +10,2 % ; 0,83 | 41 % ; 30 % (3,5 %) |
| V2 — BE 1,5 ATR (F2b) | +0,35 / +0,30 | +0,325 [+0,095 ; +0,564] | +0,380 | +0,267 | 5/6 ; 5/6 | +13,5 % ; 0,92 | 35 % ; 21 % (1,7 %) |
| V2 — BE 2,0 ATR (F2b) | +0,43 / +0,29 | +0,360 [+0,131 ; +0,597] | +0,452 | +0,267 | 6/6 ; 5/6 | +15,3 % ; 1,19 | 30 % ; 13 % (0,6 %) |
| V2 — BE 2,5 ATR (F2b) | +0,43 / +0,27 | +0,348 [+0,108 ; +0,587] | +0,432 | +0,267 | 6/6 ; 5/6 | +14,9 % ; 1,04 | 25 % ; 9 % (0,6 %) |
| V2 — BE 3,0 ATR (F2b) | +0,43 / +0,31 | +0,373 [+0,126 ; +0,621] | +0,475 | +0,267 | 6/6 ; 5/6 | +16,0 % ; 1,12 | 22 % ; 6 % (0,3 %) |
| V2 — BE 4,0 ATR (F2b) | +0,45 / +0,33 | +0,390 [+0,140 ; +0,649] | +0,507 | +0,267 | 5/6 ; 5/6 | +16,4 % ; 1,09 | 16 % ; 3 % (0,1 %) |
| V3 — BE 1,0 ATR (F2b+F3) | +0,21 / +0,21 | +0,212 [+0,030 ; +0,404] | +0,231 | +0,190 | 4/6 ; 4/6 | +8,5 % ; 0,55 | 73 % ; 54 % (6,0 %) |
| V3 — BE 1,5 ATR (F2b+F3) | +0,31 / +0,30 | +0,303 [+0,096 ; +0,527] | +0,380 | +0,217 | 5/6 ; 4/6 | +12,2 % ; 0,77 | 62 % ; 37 % (2,6 %) |
| V3 — BE 2,0 ATR (F2b+F3) | +0,43 / +0,26 | +0,344 [+0,138 ; +0,563] | +0,452 | +0,236 | 6/6 ; 6/6 | +14,5 % ; 1,25 | 52 % ; 25 % (1,2 %) |
| V3 — BE 2,5 ATR (F2b+F3) | +0,42 / +0,28 | +0,351 [+0,127 ; +0,576] | +0,432 | +0,272 | 6/6 ; 6/6 | +14,8 % ; 1,20 | 45 % ; 17 % (0,7 %) |
| V3 — BE 3,0 ATR (F2b+F3) | +0,44 / +0,30 | +0,372 [+0,136 ; +0,613] | +0,475 | +0,266 | 6/6 ; 5/6 | +15,8 % ; 1,18 | 38 % ; 12 % (0,4 %) |
| V3 — BE 4,0 ATR (F2b+F3) | +0,46 / +0,33 | +0,394 [+0,150 ; +0,645] | +0,507 | +0,275 | 5/6 ; 5/6 | +16,5 % ; 1,13 | 28 % ; 6 % (0,1 %) |

**10 bps aller-retour — 8 métriques**

| Configuration | PnL : 0,25 %/ATR ; 1x ; bps (1x) | PF : 1x ; pondéré | WR | Espérance : bps [IC] ; ATR [IC] | MDD valorisé : 0,25 %/ATR ; 1x | Trades (/mois) ; stop initial ; BE | Durée méd. | Part des frais ; brut/trade |
|---|---|---|---|---|---|---|---|---|
| RE-1 (contrôle) | +72 % ; +77 % ; +7920 | 1,11 ; 1,17 | 42,8 % | +7,3 [−4,8 ; +19,4] ; +0,233 [−0,041 ; +0,511] | −15,9 % ; −48 % | 1 080 (15,0) ; 24 % ; 0 % | 26 | 58 % ; +17,3 |
| V1 — BE 1,0 ATR (F3) | +57 % ; +34 % ; +4754 | 1,08 ; 1,17 | 34,0 % | +4,4 [−6,7 ; +15,6] ; +0,197 [−0,043 ; +0,448] | −23,5 % ; −55 % | 1 080 (15,0) ; 14 % ; 24 % | 26 | 69 % ; +14,4 |
| V1 — BE 1,5 ATR (F3) | +60 % ; +33 % ; +4760 | 1,08 ; 1,17 | 36,9 % | +4,4 [−6,4 ; +15,3] ; +0,209 [−0,034 ; +0,463] | −22,3 % ; −52 % | 1 080 (15,0) ; 17 % ; 16 % | 26 | 69 % ; +14,4 |
| V1 — BE 2,0 ATR (F3) | +65 % ; +49 % ; +5996 | 1,09 ; 1,17 | 38,5 % | +5,6 [−6,0 ; +17,3] ; +0,218 [−0,035 ; +0,478] | −16,7 % ; −46 % | 1 080 (15,0) ; 19 % ; 12 % | 26 | 64 % ; +15,6 |
| V1 — BE 2,5 ATR (F3) | +72 % ; +73 % ; +7569 | 1,11 ; 1,18 | 39,9 % | +7,0 [−4,6 ; +19,0] ; +0,235 [−0,026 ; +0,503] | −14,3 % ; −45 % | 1 080 (15,0) ; 21 % ; 8 % | 26 | 59 % ; +17,0 |
| V1 — BE 3,0 ATR (F3) | +70 % ; +63 % ; +6975 | 1,10 ; 1,18 | 40,8 % | +6,5 [−5,6 ; +18,6] ; +0,233 [−0,032 ; +0,495] | −15,0 % ; −47 % | 1 080 (15,0) ; 21 % ; 5 % | 26 | 61 % ; +16,5 |
| V1 — BE 4,0 ATR (F3) | +73 % ; +66 % ; +7195 | 1,10 ; 1,18 | 42,0 % | +6,7 [−5,5 ; +18,9] ; +0,237 [−0,035 ; +0,508] | −15,5 % ; −48 % | 1 080 (15,0) ; 22 % ; 3 % | 26 | 60 % ; +16,7 |
| V2 — BE 1,0 ATR (F2b) | +29 % ; +31 % ; +4446 | 1,08 ; 1,11 | 28,2 % | +4,1 [−6,2 ; +14,4] ; +0,112 [−0,109 ; +0,346] | −14,1 % ; −43 % | 1 080 (15,0) ; 24 % ; 30 % | 23 | 71 % ; +14,1 |
| V2 — BE 1,5 ATR (F2b) | +55 % ; +69 % ; +7211 | 1,12 ; 1,16 | 32,7 % | +6,7 [−4,0 ; +17,5] ; +0,191 [−0,047 ; +0,440] | −17,1 % ; −48 % | 1 080 (15,0) ; 24 % ; 21 % | 26 | 60 % ; +16,7 |
| V2 — BE 2,0 ATR (F2b) | +70 % ; +81 % ; +7999 | 1,12 ; 1,19 | 36,7 % | +7,4 [−3,6 ; +18,4] ; +0,229 [−0,007 ; +0,469] | −15,4 % ; −46 % | 1 080 (15,0) ; 24 % ; 13 % | 26 | 57 % ; +17,4 |
| V2 — BE 2,5 ATR (F2b) | +66 % ; +74 % ; +7609 | 1,11 ; 1,17 | 38,5 % | +7,0 [−4,4 ; +18,3] ; +0,219 [−0,029 ; +0,466] | −16,7 % ; −49 % | 1 080 (15,0) ; 24 % ; 9 % | 26 | 59 % ; +17,0 |
| V2 — BE 3,0 ATR (F2b) | +77 % ; +94 % ; +8717 | 1,13 ; 1,19 | 39,9 % | +8,1 [−3,8 ; +19,7] ; +0,241 [−0,007 ; +0,499] | −16,8 % ; −49 % | 1 080 (15,0) ; 24 % ; 6 % | 26 | 55 % ; +18,1 |
| V2 — BE 4,0 ATR (F2b) | +80 % ; +99 % ; +9035 | 1,13 ; 1,19 | 41,4 % | +8,4 [−3,5 ; +20,4] ; +0,259 [+0,003 ; +0,522] | −17,3 % ; −50 % | 1 080 (15,0) ; 24 % ; 3 % | 26 | 54 % ; +18,4 |
| V3 — BE 1,0 ATR (F2b+F3) | +18 % ; −0 % ; +1280 | 1,03 ; 1,09 | 19,4 % | +1,2 [−8,0 ; +10,8] ; +0,076 [−0,108 ; +0,277] | −21,2 % ; −51 % | 1 080 (15,0) ; 14 % ; 54 % | 12 | 89 % ; +11,2 |
| V3 — BE 1,5 ATR (F2b+F3) | +44 % ; +28 % ; +4052 | 1,08 ; 1,16 | 26,9 % | +3,8 [−6,1 ; +14,0] ; +0,168 [−0,038 ; +0,395] | −20,8 % ; −52 % | 1 080 (15,0) ; 17 % ; 37 % | 22 | 73 % ; +13,8 |
| V3 — BE 2,0 ATR (F2b+F3) | +63 % ; +53 % ; +6075 | 1,10 ; 1,19 | 32,4 % | +5,6 [−5,3 ; +16,7] ; +0,215 [+0,005 ; +0,437] | −13,4 % ; −45 % | 1 080 (15,0) ; 19 % ; 25 % | 26 | 64 % ; +15,6 |
| V3 — BE 2,5 ATR (F2b+F3) | +65 % ; +70 % ; +7259 | 1,12 ; 1,18 | 35,6 % | +6,7 [−4,6 ; +17,6] ; +0,221 [−0,003 ; +0,453] | −14,3 % ; −46 % | 1 080 (15,0) ; 21 % ; 17 % | 26 | 60 % ; +16,7 |
| V3 — BE 3,0 ATR (F2b+F3) | +74 % ; +78 % ; +7773 | 1,12 ; 1,19 | 38,0 % | +7,2 [−4,4 ; +18,6] ; +0,241 [+0,001 ; +0,489] | −15,9 % ; −49 % | 1 080 (15,0) ; 21 % ; 12 % | 26 | 58 % ; +17,2 |
| V3 — BE 4,0 ATR (F2b+F3) | +80 % ; +87 % ; +8311 | 1,12 ; 1,20 | 40,6 % | +7,7 [−4,3 ; +19,6] ; +0,263 [+0,014 ; +0,514] | −16,9 % ; −49 % | 1 080 (15,0) ; 22 % ; 6 % | 26 | 57 % ; +17,7 |

**10 bps — sens, sous-familles, régularité, break-even**

| Configuration | Long / Short (ATR) | Timing ATR [IC] | F2b : esp. ATR | F3 : esp. ATR | Années > 0 : ATR ; PnL | PnL annualisé ; Calmar | BE activé ; sorti au BE (dont gap) |
|---|---|---|---|---|---|---|---|
| RE-1 (contrôle) | +0,32 / +0,13 | +0,226 [−0,050 ; +0,507] | +0,326 | +0,127 | 5/6 ; 5/6 | +9,5 % ; 0,60 | 0 % ; 0 % (0,0 %) |
| V1 — BE 1,0 ATR (F3) | +0,27 / +0,12 | +0,191 [−0,049 ; +0,442] | +0,326 | +0,051 | 4/6 ; 4/6 | +7,8 % ; 0,33 | 32 % ; 24 % (2,5 %) |
| V1 — BE 1,5 ATR (F3) | +0,28 / +0,12 | +0,204 [−0,039 ; +0,458] | +0,326 | +0,078 | 4/6 ; 4/6 | +8,2 % ; 0,37 | 27 % ; 16 % (0,9 %) |
| V1 — BE 2,0 ATR (F3) | +0,32 / +0,10 | +0,210 [−0,040 ; +0,469] | +0,326 | +0,096 | 4/6 ; 4/6 | +8,7 % ; 0,52 | 23 % ; 12 % (0,6 %) |
| V1 — BE 2,5 ATR (F3) | +0,31 / +0,14 | +0,229 [−0,029 ; +0,495] | +0,326 | +0,132 | 5/6 ; 5/6 | +9,4 % ; 0,66 | 19 % ; 8 % (0,2 %) |
| V1 — BE 3,0 ATR (F3) | +0,33 / +0,12 | +0,225 [−0,034 ; +0,487] | +0,326 | +0,127 | 5/6 ; 5/6 | +9,3 % ; 0,62 | 16 % ; 5 % (0,1 %) |
| V1 — BE 4,0 ATR (F3) | +0,33 / +0,13 | +0,230 [−0,038 ; +0,502] | +0,326 | +0,136 | 5/6 ; 5/6 | +9,6 % ; 0,62 | 12 % ; 3 % (0,0 %) |
| V2 — BE 1,0 ATR (F2b) | +0,13 / +0,09 | +0,110 [−0,108 ; +0,339] | +0,098 | +0,127 | 5/6 ; 5/6 | +4,4 % ; 0,31 | 41 % ; 30 % (3,5 %) |
| V2 — BE 1,5 ATR (F2b) | +0,21 / +0,17 | +0,189 [−0,050 ; +0,434] | +0,248 | +0,127 | 5/6 ; 5/6 | +7,5 % ; 0,44 | 35 % ; 21 % (1,7 %) |
| V2 — BE 2,0 ATR (F2b) | +0,30 / +0,15 | +0,224 [−0,006 ; +0,462] | +0,319 | +0,127 | 5/6 ; 5/6 | +9,3 % ; 0,60 | 30 % ; 13 % (0,6 %) |
| V2 — BE 2,5 ATR (F2b) | +0,29 / +0,13 | +0,212 [−0,034 ; +0,456] | +0,299 | +0,127 | 5/6 ; 5/6 | +8,8 % ; 0,53 | 25 % ; 9 % (0,6 %) |
| V2 — BE 3,0 ATR (F2b) | +0,30 / +0,18 | +0,237 [−0,017 ; +0,496] | +0,342 | +0,127 | 5/6 ; 5/6 | +9,9 % ; 0,59 | 22 % ; 6 % (0,3 %) |
| V2 — BE 4,0 ATR (F2b) | +0,31 / +0,20 | +0,254 [+0,001 ; +0,518] | +0,375 | +0,127 | 5/6 ; 5/6 | +10,3 % ; 0,59 | 16 % ; 3 % (0,1 %) |
| V3 — BE 1,0 ATR (F2b+F3) | +0,08 / +0,08 | +0,076 [−0,107 ; +0,273] | +0,098 | +0,051 | 4/6 ; 4/6 | +2,8 % ; 0,13 | 73 % ; 54 % (6,0 %) |
| V3 — BE 1,5 ATR (F2b+F3) | +0,17 / +0,16 | +0,167 [−0,040 ; +0,392] | +0,248 | +0,078 | 4/6 ; 4/6 | +6,3 % ; 0,30 | 62 % ; 37 % (2,6 %) |
| V3 — BE 2,0 ATR (F2b+F3) | +0,29 / +0,12 | +0,208 [−0,002 ; +0,428] | +0,319 | +0,096 | 5/6 ; 4/6 | +8,5 % ; 0,64 | 52 % ; 25 % (1,2 %) |
| V3 — BE 2,5 ATR (F2b+F3) | +0,29 / +0,14 | +0,215 [−0,009 ; +0,439] | +0,299 | +0,132 | 5/6 ; 5/6 | +8,8 % ; 0,61 | 45 % ; 17 % (0,7 %) |
| V3 — BE 3,0 ATR (F2b+F3) | +0,30 / +0,17 | +0,236 [−0,003 ; +0,481] | +0,342 | +0,127 | 5/6 ; 5/6 | +9,7 % ; 0,61 | 38 % ; 12 % (0,4 %) |
| V3 — BE 4,0 ATR (F2b+F3) | +0,32 / +0,20 | +0,258 [+0,008 ; +0,513] | +0,375 | +0,136 | 5/6 ; 5/6 | +10,3 % ; 0,61 | 28 % ; 6 % (0,1 %) |

## C. Effet apparié BE − RE-1 (lecture cooldown, mêmes entrées)

Moyenne par trade de (variante − RE-1) sur toutes les entrées de RE-1, frais compensés (identique à 5 et 10 bps).

### H = 26 : ATR [IC] ; bps [IC]

| Seuil | V1 — BE sur F3 | V2 — BE sur F2b | V3 — BE sur F2b et F3 |
|---|---|---|---|
| m = 1,0 | −0,036 [−0,143 ; +0,063] ; −2,9 [−8,1 ; +1,9] | −0,121 [−0,249 ; +0,001] ; −3,2 [−7,6 ; +1,4] | −0,157 [−0,318 ; +0,007] ; −6,1 [−13,2 ; +1,0] |
| m = 1,5 | −0,023 [−0,111 ; +0,054] ; −2,9 [−7,6 ; +1,4] | −0,042 [−0,139 ; +0,063] ; −0,7 [−4,3 ; +3,0] | −0,065 [−0,208 ; +0,075] ; −3,6 [−10,4 ; +3,0] |
| m = 2,0 | −0,015 [−0,089 ; +0,047] ; −1,8 [−5,9 ; +1,6] | −0,004 [−0,082 ; +0,089] ; +0,1 [−3,2 ; +3,6] | −0,018 [−0,131 ; +0,105] ; −1,7 [−7,5 ; +3,9] |
| m = 2,5 | +0,002 [−0,064 ; +0,053] ; −0,3 [−3,9 ; +2,4] | −0,014 [−0,091 ; +0,077] ; −0,3 [−3,2 ; +3,0] | −0,012 [−0,118 ; +0,097] ; −0,6 [−5,6 ; +4,4] |
| m = 3,0 | −0,000 [−0,040 ; +0,038] ; −0,9 [−4,1 ; +1,4] | +0,009 [−0,061 ; +0,093] ; +0,7 [−1,9 ; +3,8] | +0,009 [−0,070 ; +0,105] ; −0,1 [−4,4 ; +4,2] |
| m = 4,0 | +0,004 [−0,026 ; +0,033] ; −0,7 [−3,7 ; +1,2] | +0,026 [−0,029 ; +0,103] ; +1,0 [−1,0 ; +3,8] | +0,030 [−0,035 ; +0,118] ; +0,4 [−3,3 ; +3,9] |

### H = 24 : ATR [IC]

| Seuil | V1 — BE sur F3 | V2 — BE sur F2b | V3 — BE sur F2b et F3 |
|---|---|---|---|
| m = 1,0 | −0,028 [−0,122 ; +0,061] | −0,119 [−0,240 ; −0,004] | −0,147 [−0,290 ; −0,005] |
| m = 1,5 | −0,012 [−0,087 ; +0,053] | −0,038 [−0,141 ; +0,058] | −0,050 [−0,173 ; +0,071] |
| m = 2,0 | −0,004 [−0,070 ; +0,049] | −0,004 [−0,078 ; +0,070] | −0,009 [−0,102 ; +0,085] |
| m = 2,5 | +0,005 [−0,051 ; +0,051] | −0,010 [−0,081 ; +0,063] | −0,005 [−0,090 ; +0,081] |
| m = 3,0 | −0,000 [−0,035 ; +0,035] | −0,002 [−0,071 ; +0,065] | −0,002 [−0,070 ; +0,072] |
| m = 4,0 | +0,008 [−0,015 ; +0,031] | +0,020 [−0,018 ; +0,071] | +0,028 [−0,018 ; +0,089] |

### H = 28 : ATR [IC]

| Seuil | V1 — BE sur F3 | V2 — BE sur F2b | V3 — BE sur F2b et F3 |
|---|---|---|---|
| m = 1,0 | −0,001 [−0,104 ; +0,093] | −0,150 [−0,297 ; −0,014] | −0,151 [−0,321 ; +0,022] |
| m = 1,5 | +0,005 [−0,081 ; +0,080] | −0,061 [−0,173 ; +0,051] | −0,056 [−0,212 ; +0,097] |
| m = 2,0 | +0,003 [−0,062 ; +0,057] | −0,021 [−0,114 ; +0,082] | −0,018 [−0,140 ; +0,106] |
| m = 2,5 | +0,005 [−0,058 ; +0,054] | −0,012 [−0,096 ; +0,081] | −0,007 [−0,120 ; +0,112] |
| m = 3,0 | −0,005 [−0,045 ; +0,030] | +0,010 [−0,066 ; +0,097] | +0,005 [−0,083 ; +0,109] |
| m = 4,0 | −0,007 [−0,042 ; +0,023] | +0,022 [−0,035 ; +0,099] | +0,015 [−0,057 ; +0,111] |

### Effet apparié sur le drawdown

MDD du capital aux sorties, 0,25 % par ATR, 5 bps. Cellule : écart BE − RE-1 observé, en points de MDD (> 0 : drawdown moins profond avec le break-even) ; plage P2,5-P97,5 de cet écart sur 2 000 chemins où les mois d'entrée sont tirés avec remise (mêmes tirages que les IC) ; part des chemins où le break-even est moins profond. Le MDD dépend de l'ordre des trades : la plage décrit l'écart sur des chemins réordonnés, ce n'est pas un IC centré sur l'écart observé, qui peut en sortir. MDD aux sorties de RE-1 : −13,4 % à H = 24 ; −12,9 % à H = 26 ; −15,2 % à H = 28.

**H = 24**

| Seuil | V1 — BE sur F3 | V2 — BE sur F2b | V3 — BE sur F2b et F3 |
|---|---|---|---|
| m = 1,0 | −3,7 ; [−5,4 ; +6,5] ; 0,60 | +0,9 ; [−6,8 ; +7,7] ; 0,64 | −2,0 ; [−5,9 ; +10,0] ; 0,73 |
| m = 1,5 | −2,3 ; [−2,6 ; +6,3] ; 0,81 | −0,7 ; [−3,6 ; +7,7] ; 0,75 | −2,0 ; [−3,4 ; +10,8] ; 0,84 |
| m = 2,0 | +1,0 ; [−2,5 ; +5,2] ; 0,81 | +0,5 ; [−1,2 ; +8,0] ; 0,87 | +2,7 ; [−1,6 ; +10,5] ; 0,92 |
| m = 2,5 | +1,7 ; [−2,8 ; +4,3] ; 0,78 | −0,3 ; [−1,9 ; +6,3] ; 0,77 | +2,5 ; [−1,9 ; +8,5] ; 0,88 |
| m = 3,0 | +1,2 ; [−2,0 ; +3,1] ; 0,70 | −0,3 ; [−1,7 ; +6,2] ; 0,76 | +0,8 ; [−1,6 ; +7,2] ; 0,85 |
| m = 4,0 | +0,4 ; [−1,2 ; +2,2] ; 0,68 | −1,3 ; [−1,1 ; +4,7] ; 0,71 | −0,9 ; [−1,1 ; +5,5] ; 0,79 |

**H = 26**

| Seuil | V1 — BE sur F3 | V2 — BE sur F2b | V3 — BE sur F2b et F3 |
|---|---|---|---|
| m = 1,0 | −3,9 ; [−4,6 ; +7,1] ; 0,66 | +1,2 ; [−6,7 ; +8,2] ; 0,64 | −1,9 ; [−5,8 ; +11,0] ; 0,73 |
| m = 1,5 | −2,6 ; [−2,5 ; +6,3] ; 0,83 | −1,2 ; [−3,6 ; +8,4] ; 0,72 | −2,4 ; [−3,6 ; +11,4] ; 0,83 |
| m = 2,0 | +0,8 ; [−2,9 ; +5,3] ; 0,81 | +0,6 ; [−1,6 ; +8,7] ; 0,86 | +1,6 ; [−2,1 ; +11,6] ; 0,89 |
| m = 2,5 | +1,3 ; [−2,7 ; +4,8] ; 0,82 | −0,8 ; [−2,4 ; +7,6] ; 0,75 | +1,2 ; [−2,4 ; +10,3] ; 0,86 |
| m = 3,0 | +0,8 ; [−1,8 ; +3,3] ; 0,75 | −0,9 ; [−1,9 ; +7,6] ; 0,76 | +0,0 ; [−1,6 ; +9,1] ; 0,85 |
| m = 4,0 | +0,4 ; [−1,9 ; +2,5] ; 0,67 | −1,5 ; [−1,2 ; +6,8] ; 0,76 | −1,1 ; [−1,5 ; +7,6] ; 0,81 |

**H = 28**

| Seuil | V1 — BE sur F3 | V2 — BE sur F2b | V3 — BE sur F2b et F3 |
|---|---|---|---|
| m = 1,0 | +0,7 ; [−4,3 ; +7,3] ; 0,71 | +2,7 ; [−8,5 ; +7,7] ; 0,55 | +1,5 ; [−7,0 ; +10,9] ; 0,70 |
| m = 1,5 | +1,1 ; [−2,4 ; +6,9] ; 0,84 | +2,6 ; [−4,7 ; +8,8] ; 0,71 | +2,3 ; [−4,2 ; +12,3] ; 0,82 |
| m = 2,0 | +2,1 ; [−2,9 ; +5,1] ; 0,78 | +3,3 ; [−2,6 ; +8,9] ; 0,79 | +3,4 ; [−3,4 ; +11,7] ; 0,82 |
| m = 2,5 | +1,8 ; [−3,0 ; +4,3] ; 0,74 | +2,1 ; [−2,0 ; +8,4] ; 0,79 | +1,8 ; [−3,1 ; +10,6] ; 0,81 |
| m = 3,0 | +1,4 ; [−2,0 ; +2,6] ; 0,70 | +2,1 ; [−1,8 ; +7,8] ; 0,76 | +2,0 ; [−2,4 ; +9,1] ; 0,78 |
| m = 4,0 | +1,4 ; [−2,2 ; +1,7] ; 0,61 | +1,9 ; [−1,5 ; +6,9] ; 0,67 | +2,3 ; [−2,3 ; +7,6] ; 0,68 |

## D. Mécanique du break-even à H = 26 (cooldown, mêmes entrées que RE-1)

Seuls les trades sortis au break-even changent. Sauvés : le break-even sort plus haut que RE-1 ; coupés : RE-1 finissait plus haut. Gain et coût : ATR par trade sur toutes les entrées ; leur somme est l'effet apparié. « RE-1 » : résultat net moyen (5 bps) de ces trades dans RE-1.

| Configuration | Activés (part) | Sortis au BE (gap) | Sauvés : n ; effet moyen ; RE-1 | Coupés : n ; effet moyen ; RE-1 | Coupés avec RE-1 ≥ +3 ATR : n ; coût par trade | Gain ; coût ; effet par trade | Effet par trade : F2b ; F3 |
|---|---|---|---|---|---|---|---|
| V1 — BE 1,0 ATR (F3) | 346 (32 %) | 261 (27) | 157 ; +1,75 ; −1,79 | 104 ; −3,02 ; +3,00 | 36 ; −0,217 | +0,255 ; −0,291 ; −0,036 | +0,000 ; −0,077 |
| V1 — BE 1,5 ATR (F3) | 287 (27 %) | 177 (10) | 107 ; +1,73 ; −1,76 | 70 ; −3,01 ; +2,98 | 23 ; −0,147 | +0,172 ; −0,195 ; −0,023 | +0,000 ; −0,050 |
| V1 — BE 2,0 ATR (F3) | 246 (23 %) | 125 (6) | 74 ; +1,69 ; −1,72 | 51 ; −2,76 ; +2,73 | 17 ; −0,101 | +0,116 ; −0,130 ; −0,015 | +0,000 ; −0,031 |
| V1 — BE 2,5 ATR (F3) | 210 (19 %) | 87 (2) | 53 ; +1,76 ; −1,77 | 34 ; −2,67 ; +2,67 | 12 ; −0,068 | +0,086 ; −0,084 ; +0,002 | +0,000 ; +0,005 |
| V1 — BE 3,0 ATR (F3) | 178 (16 %) | 58 (1) | 35 ; +1,78 ; −1,83 | 23 ; −2,72 ; +2,72 | 10 ; −0,047 | +0,058 ; −0,058 ; −0,000 | +0,000 ; −0,000 |
| V1 — BE 4,0 ATR (F3) | 134 (12 %) | 30 (0) | 21 ; +1,93 ; −1,93 | 9 ; −4,02 ; +4,02 | 6 ; −0,032 | +0,038 ; −0,034 ; +0,004 | +0,000 ; +0,009 |
| V2 — BE 1,0 ATR (F2b) | 440 (41 %) | 321 (38) | 152 ; +2,23 ; −2,25 | 169 ; −2,78 ; +2,70 | 46 ; −0,298 | +0,314 ; −0,435 ; −0,121 | −0,228 ; +0,000 |
| V2 — BE 1,5 ATR (F2b) | 382 (35 %) | 223 (18) | 109 ; +2,18 ; −2,19 | 114 ; −2,48 ; +2,41 | 28 ; −0,166 | +0,220 ; −0,261 ; −0,042 | −0,079 ; +0,000 |
| V2 — BE 2,0 ATR (F2b) | 319 (30 %) | 143 (7) | 73 ; +2,28 ; −2,30 | 70 ; −2,43 ; +2,34 | 19 ; −0,105 | +0,154 ; −0,158 ; −0,004 | −0,007 ; +0,000 |
| V2 — BE 2,5 ATR (F2b) | 272 (25 %) | 98 (6) | 48 ; +2,35 ; −2,37 | 50 ; −2,56 ; +2,40 | 14 ; −0,082 | +0,104 ; −0,119 ; −0,014 | −0,027 ; +0,000 |
| V2 — BE 3,0 ATR (F2b) | 236 (22 %) | 69 (3) | 35 ; +2,80 ; −2,80 | 34 ; −2,61 ; +2,41 | 9 ; −0,057 | +0,091 ; −0,082 ; +0,009 | +0,016 ; +0,000 |
| V2 — BE 4,0 ATR (F2b) | 172 (16 %) | 34 (1) | 18 ; +3,67 ; −3,67 | 16 ; −2,39 ; +2,29 | 5 ; −0,025 | +0,061 ; −0,035 ; +0,026 | +0,049 ; +0,000 |
| V3 — BE 1,0 ATR (F2b+F3) | 786 (73 %) | 582 (65) | 309 ; +1,99 ; −2,02 | 273 ; −2,87 ; +2,81 | 82 ; −0,515 | +0,569 ; −0,726 ; −0,157 | −0,228 ; −0,077 |
| V3 — BE 1,5 ATR (F2b+F3) | 669 (62 %) | 400 (28) | 216 ; +1,96 ; −1,98 | 184 ; −2,68 ; +2,63 | 51 ; −0,313 | +0,391 ; −0,456 ; −0,065 | −0,079 ; −0,050 |
| V3 — BE 2,0 ATR (F2b+F3) | 565 (52 %) | 268 (13) | 147 ; +1,98 ; −2,01 | 121 ; −2,57 ; +2,51 | 36 ; −0,206 | +0,270 ; −0,288 ; −0,018 | −0,007 ; −0,031 |
| V3 — BE 2,5 ATR (F2b+F3) | 482 (45 %) | 185 (8) | 101 ; +2,04 ; −2,05 | 84 ; −2,61 ; +2,51 | 26 ; −0,149 | +0,191 ; −0,203 ; −0,012 | −0,027 ; +0,005 |
| V3 — BE 3,0 ATR (F2b+F3) | 414 (38 %) | 127 (4) | 70 ; +2,29 ; −2,32 | 57 ; −2,65 ; +2,54 | 19 ; −0,104 | +0,149 ; −0,140 ; +0,009 | +0,016 ; −0,000 |
| V3 — BE 4,0 ATR (F2b+F3) | 306 (28 %) | 64 (1) | 39 ; +2,74 ; −2,74 | 25 ; −2,98 ; +2,91 | 11 ; −0,056 | +0,099 ; −0,069 ; +0,030 | +0,049 ; +0,009 |

## E. Queue droite à H = 26 (cooldown, 5 bps)

Distribution du résultat net par trade en ATR14(t). Top 10 % : moyenne des trades au-dessus de leur propre P90.

| Configuration | P50 | P75 | P90 | P95 | P99 | ≥ +3 ATR | ≥ +5 ATR | Top 10 % | Espérance |
|---|---|---|---|---|---|---|---|---|---|
| RE-1 (contrôle) | −0,42 | +2,06 | +5,53 | +8,44 | +13,19 | 19,4 % | 11,3 % | +9,19 | +0,369 |
| V1 — BE 1,0 ATR (F3) | −0,00 | +1,30 | +4,88 | +8,06 | +12,23 | 16,0 % | 9,4 % | +8,55 | +0,333 |
| V1 — BE 1,5 ATR (F3) | −0,00 | +1,64 | +5,01 | +8,09 | +12,23 | 17,2 % | 10,2 % | +8,72 | +0,345 |
| V1 — BE 2,0 ATR (F3) | −0,00 | +1,80 | +5,25 | +8,28 | +12,81 | 17,8 % | 10,6 % | +8,91 | +0,354 |
| V1 — BE 2,5 ATR (F3) | −0,08 | +1,87 | +5,35 | +8,30 | +13,01 | 18,2 % | 10,8 % | +9,01 | +0,371 |
| V1 — BE 3,0 ATR (F3) | −0,22 | +1,92 | +5,38 | +8,42 | +13,19 | 18,4 % | 10,9 % | +9,13 | +0,368 |
| V1 — BE 4,0 ATR (F3) | −0,31 | +2,01 | +5,38 | +8,42 | +13,19 | 18,8 % | 10,9 % | +9,13 | +0,373 |
| V2 — BE 1,0 ATR (F2b) | −0,00 | +0,81 | +4,71 | +7,27 | +12,85 | 15,1 % | 9,0 % | +8,18 | +0,248 |
| V2 — BE 1,5 ATR (F2b) | −0,00 | +1,35 | +4,96 | +7,72 | +13,19 | 16,8 % | 9,9 % | +8,75 | +0,327 |
| V2 — BE 2,0 ATR (F2b) | −0,00 | +1,67 | +5,16 | +8,08 | +13,19 | 17,6 % | 10,4 % | +8,95 | +0,365 |
| V2 — BE 2,5 ATR (F2b) | −0,18 | +1,78 | +5,24 | +8,09 | +13,19 | 18,1 % | 10,6 % | +8,98 | +0,354 |
| V2 — BE 3,0 ATR (F2b) | −0,25 | +1,92 | +5,26 | +8,21 | +13,19 | 18,5 % | 10,8 % | +9,02 | +0,377 |
| V2 — BE 4,0 ATR (F2b) | −0,34 | +1,98 | +5,48 | +8,43 | +13,19 | 18,9 % | 11,1 % | +9,15 | +0,394 |
| V3 — BE 1,0 ATR (F2b+F3) | −0,00 | −0,00 | +3,85 | +6,05 | +11,13 | 11,8 % | 7,1 % | +7,36 | +0,212 |
| V3 — BE 1,5 ATR (F2b+F3) | −0,00 | +0,56 | +4,58 | +7,27 | +12,21 | 14,6 % | 8,8 % | +8,23 | +0,304 |
| V3 — BE 2,0 ATR (F2b+F3) | −0,00 | +1,34 | +4,90 | +7,81 | +12,81 | 16,0 % | 9,6 % | +8,64 | +0,350 |
| V3 — BE 2,5 ATR (F2b+F3) | −0,00 | +1,61 | +5,01 | +8,06 | +13,01 | 16,9 % | 10,2 % | +8,79 | +0,357 |
| V3 — BE 3,0 ATR (F2b+F3) | −0,00 | +1,71 | +5,23 | +8,09 | +13,19 | 17,6 % | 10,5 % | +8,96 | +0,377 |
| V3 — BE 4,0 ATR (F2b+F3) | −0,19 | +1,92 | +5,26 | +8,30 | +13,19 | 18,3 % | 10,7 % | +9,09 | +0,398 |

## F. Plateau d'horizon (cooldown)

Cellule : espérance ATR [IC] ; PnL ; MDD ; Calmar, à 0,25 % par ATR. Puis, à 10 bps : espérance ATR ; PnL.

| Configuration | H = 24 | H = 26 | H = 28 |
|---|---|---|---|
| RE-1 (contrôle) | +0,328 [+0,078 ; +0,583] ; +112 % ; −14,2 % ; 0,94 ‖ 10 bps : +0,194 ; +52 % | +0,369 [+0,098 ; +0,645] ; +138 % ; −13,5 % ; 1,16 ‖ 10 bps : +0,233 ; +72 % | +0,371 [+0,078 ; +0,657] ; +129 % ; −16,2 % ; 0,92 ‖ 10 bps : +0,235 ; +67 % |
| V1 — BE 1,0 ATR (F3) | +0,300 [+0,072 ; +0,531] ; +98 % ; −18,0 % ; 0,67 ‖ 10 bps : +0,165 ; +42 % | +0,333 [+0,095 ; +0,581] ; +117 % ; −17,5 % ; 0,79 ‖ 10 bps : +0,197 ; +57 % | +0,370 [+0,109 ; +0,640] ; +128 % ; −15,5 % ; 0,95 ‖ 10 bps : +0,234 ; +66 % |
| V1 — BE 1,5 ATR (F3) | +0,316 [+0,093 ; +0,554] ; +105 % ; −16,6 % ; 0,76 ‖ 10 bps : +0,181 ; +47 % | +0,345 [+0,101 ; +0,598] ; +122 % ; −16,0 % ; 0,89 ‖ 10 bps : +0,209 ; +60 % | +0,375 [+0,115 ; +0,643] ; +129 % ; −15,1 % ; 0,98 ‖ 10 bps : +0,240 ; +67 % |
| V1 — BE 2,0 ATR (F3) | +0,324 [+0,091 ; +0,562] ; +111 % ; −12,7 % ; 1,04 ‖ 10 bps : +0,189 ; +51 % | +0,354 [+0,105 ; +0,614] ; +128 % ; −13,1 % ; 1,13 ‖ 10 bps : +0,218 ; +65 % | +0,374 [+0,103 ; +0,646] ; +130 % ; −14,1 % ; 1,05 ‖ 10 bps : +0,238 ; +67 % |
| V1 — BE 2,5 ATR (F3) | +0,334 [+0,099 ; +0,580] ; +115 % ; −12,2 % ; 1,12 ‖ 10 bps : +0,199 ; +54 % | +0,371 [+0,114 ; +0,634] ; +137 % ; −12,4 % ; 1,25 ‖ 10 bps : +0,235 ; +72 % | +0,375 [+0,102 ; +0,650] ; +129 % ; −14,4 % ; 1,03 ‖ 10 bps : +0,240 ; +67 % |
| V1 — BE 3,0 ATR (F3) | +0,328 [+0,088 ; +0,573] ; +111 % ; −13,1 % ; 1,02 ‖ 10 bps : +0,193 ; +52 % | +0,368 [+0,108 ; +0,628] ; +135 % ; −12,7 % ; 1,21 ‖ 10 bps : +0,233 ; +70 % | +0,365 [+0,091 ; +0,643] ; +124 % ; −14,8 % ; 0,97 ‖ 10 bps : +0,230 ; +63 % |
| V1 — BE 4,0 ATR (F3) | +0,336 [+0,094 ; +0,585] ; +117 % ; −13,8 % ; 1,00 ‖ 10 bps : +0,202 ; +56 % | +0,373 [+0,106 ; +0,643] ; +139 % ; −13,1 % ; 1,20 ‖ 10 bps : +0,237 ; +73 % | +0,364 [+0,084 ; +0,647] ; +124 % ; −14,8 % ; 0,97 ‖ 10 bps : +0,228 ; +63 % |
| V2 — BE 1,0 ATR (F2b) | +0,210 [+0,009 ; +0,423] ; +64 % ; −13,1 % ; 0,65 ‖ 10 bps : +0,075 ; +18 % | +0,248 [+0,028 ; +0,481] ; +79 % ; −12,2 % ; 0,83 ‖ 10 bps : +0,112 ; +29 % | +0,220 [−0,003 ; +0,459] ; +64 % ; −13,4 % ; 0,64 ‖ 10 bps : +0,085 ; +20 % |
| V2 — BE 1,5 ATR (F2b) | +0,291 [+0,073 ; +0,523] ; +98 % ; −14,9 % ; 0,81 ‖ 10 bps : +0,156 ; +43 % | +0,327 [+0,096 ; +0,573] ; +114 % ; −14,7 % ; 0,92 ‖ 10 bps : +0,191 ; +55 % | +0,310 [+0,067 ; +0,561] ; +99 % ; −13,3 % ; 0,91 ‖ 10 bps : +0,174 ; +45 % |
| V2 — BE 2,0 ATR (F2b) | +0,324 [+0,111 ; +0,546] ; +115 % ; −13,8 % ; 0,99 ‖ 10 bps : +0,189 ; +55 % | +0,365 [+0,134 ; +0,602] ; +136 % ; −12,9 % ; 1,19 ‖ 10 bps : +0,229 ; +70 % | +0,349 [+0,109 ; +0,606] ; +119 % ; −12,7 % ; 1,10 ‖ 10 bps : +0,214 ; +60 % |
| V2 — BE 2,5 ATR (F2b) | +0,318 [+0,099 ; +0,548] ; +113 % ; −14,5 % ; 0,92 ‖ 10 bps : +0,183 ; +53 % | +0,354 [+0,113 ; +0,595] ; +130 % ; −14,3 % ; 1,04 ‖ 10 bps : +0,219 ; +66 % | +0,359 [+0,112 ; +0,614] ; +125 % ; −13,8 % ; 1,05 ‖ 10 bps : +0,223 ; +64 % |
| V2 — BE 3,0 ATR (F2b) | +0,326 [+0,103 ; +0,559] ; +118 % ; −14,6 % ; 0,95 ‖ 10 bps : +0,192 ; +57 % | +0,377 [+0,129 ; +0,627] ; +144 % ; −14,4 % ; 1,12 ‖ 10 bps : +0,241 ; +77 % | +0,381 [+0,124 ; +0,646] ; +138 % ; −13,8 % ; 1,13 ‖ 10 bps : +0,245 ; +74 % |
| V2 — BE 4,0 ATR (F2b) | +0,348 [+0,119 ; +0,593] ; +120 % ; −15,6 % ; 0,90 ‖ 10 bps : +0,214 ; +58 % | +0,394 [+0,143 ; +0,654] ; +148 % ; −15,0 % ; 1,09 ‖ 10 bps : +0,259 ; +80 % | +0,392 [+0,130 ; +0,664] ; +136 % ; −13,9 % ; 1,10 ‖ 10 bps : +0,257 ; +72 % |
| V3 — BE 1,0 ATR (F2b+F3) | +0,181 [+0,010 ; +0,362] ; +53 % ; −16,2 % ; 0,45 ‖ 10 bps : +0,047 ; +10 % | +0,212 [+0,030 ; +0,407] ; +63 % ; −15,5 % ; 0,55 ‖ 10 bps : +0,076 ; +18 % | +0,220 [+0,013 ; +0,438] ; +63 % ; −14,5 % ; 0,58 ‖ 10 bps : +0,084 ; +19 % |
| V3 — BE 1,5 ATR (F2b+F3) | +0,278 [+0,089 ; +0,486] ; +91 % ; −15,9 % ; 0,72 ‖ 10 bps : +0,143 ; +38 % | +0,304 [+0,097 ; +0,527] ; +99 % ; −15,8 % ; 0,77 ‖ 10 bps : +0,168 ; +44 % | +0,314 [+0,095 ; +0,553] ; +98 % ; −13,5 % ; 0,89 ‖ 10 bps : +0,179 ; +45 % |
| V3 — BE 2,0 ATR (F2b+F3) | +0,320 [+0,120 ; +0,530] ; +114 % ; −11,2 % ; 1,20 ‖ 10 bps : +0,185 ; +54 % | +0,350 [+0,142 ; +0,570] ; +126 % ; −11,7 % ; 1,25 ‖ 10 bps : +0,215 ; +63 % | +0,352 [+0,122 ; +0,596] ; +120 % ; −12,5 % ; 1,12 ‖ 10 bps : +0,217 ; +60 % |
| V3 — BE 2,5 ATR (F2b+F3) | +0,323 [+0,118 ; +0,542] ; +116 % ; −11,9 % ; 1,15 ‖ 10 bps : +0,189 ; +55 % | +0,357 [+0,133 ; +0,586] ; +129 % ; −12,3 % ; 1,20 ‖ 10 bps : +0,221 ; +65 % | +0,364 [+0,124 ; +0,609] ; +125 % ; −14,1 % ; 1,03 ‖ 10 bps : +0,228 ; +64 % |
| V3 — BE 3,0 ATR (F2b+F3) | +0,326 [+0,106 ; +0,552] ; +117 % ; −13,4 % ; 1,03 ‖ 10 bps : +0,191 ; +56 % | +0,377 [+0,140 ; +0,616] ; +141 % ; −13,4 % ; 1,18 ‖ 10 bps : +0,241 ; +74 % | +0,375 [+0,127 ; +0,637] ; +132 % ; −13,9 % ; 1,09 ‖ 10 bps : +0,240 ; +70 % |
| V3 — BE 4,0 ATR (F2b+F3) | +0,357 [+0,124 ; +0,603] ; +125 % ; −15,2 % ; 0,96 ‖ 10 bps : +0,222 ; +62 % | +0,398 [+0,151 ; +0,649] ; +149 % ; −14,5 % ; 1,13 ‖ 10 bps : +0,263 ; +80 % | +0,385 [+0,131 ; +0,658] ; +131 % ; −13,7 % ; 1,09 ‖ 10 bps : +0,250 ; +68 % |

## G. Stabilité annuelle à H = 26 (cooldown)

Effet apparié BE − RE-1 par année d'entrée (ATR par trade), puis PnL composé par année à 0,25 % par ATR (5 bps).

| Configuration | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 | PnL par année |
|---|---|---|---|---|---|---|---|
| RE-1 (contrôle) | — | — | — | — | — | — | +25 % ; +0 % ; +12 % ; +25 % ; +15 % ; +18 % |
| V1 — BE 1,0 ATR (F3) | +0,119 | −0,125 | −0,272 | +0,046 | +0,035 | −0,030 | +33 % ; −5 % ; −0 % ; +27 % ; +16 % ; +17 % |
| V1 — BE 1,5 ATR (F3) | +0,068 | −0,087 | −0,279 | +0,069 | +0,103 | −0,022 | +30 % ; −4 % ; −1 % ; +28 % ; +20 % ; +17 % |
| V1 — BE 2,0 ATR (F3) | +0,038 | +0,015 | −0,204 | +0,030 | +0,068 | −0,046 | +28 % ; +1 % ; +2 % ; +26 % ; +18 % ; +16 % |
| V1 — BE 2,5 ATR (F3) | +0,052 | +0,010 | −0,115 | +0,052 | +0,061 | −0,058 | +28 % ; +1 % ; +6 % ; +27 % ; +18 % ; +15 % |
| V1 — BE 3,0 ATR (F3) | +0,045 | −0,014 | −0,048 | +0,049 | +0,013 | −0,055 | +28 % ; −0 % ; +9 % ; +27 % ; +15 % ; +15 % |
| V1 — BE 4,0 ATR (F3) | +0,024 | −0,026 | −0,034 | +0,074 | +0,008 | −0,026 | +27 % ; −1 % ; +10 % ; +29 % ; +15 % ; +17 % |
| V2 — BE 1,0 ATR (F2b) | −0,262 | +0,030 | −0,034 | −0,235 | −0,056 | −0,164 | +11 % ; +2 % ; +10 % ; +13 % ; +12 % ; +13 % |
| V2 — BE 1,5 ATR (F2b) | +0,022 | −0,044 | +0,012 | −0,174 | −0,024 | −0,036 | +27 % ; −2 % ; +12 % ; +16 % ; +14 % ; +16 % |
| V2 — BE 2,0 ATR (F2b) | +0,009 | −0,014 | +0,020 | −0,014 | +0,036 | −0,060 | +26 % ; −0 % ; +12 % ; +24 % ; +17 % ; +15 % |
| V2 — BE 2,5 ATR (F2b) | −0,020 | −0,012 | +0,026 | −0,050 | +0,010 | −0,036 | +24 % ; −0 % ; +13 % ; +22 % ; +15 % ; +17 % |
| V2 — BE 3,0 ATR (F2b) | +0,017 | −0,010 | +0,072 | +0,048 | −0,031 | −0,048 | +26 % ; −0 % ; +15 % ; +28 % ; +13 % ; +16 % |
| V2 — BE 4,0 ATR (F2b) | +0,039 | −0,036 | +0,035 | +0,151 | +0,045 | −0,087 | +28 % ; −1 % ; +13 % ; +31 % ; +17 % ; +14 % |
| V3 — BE 1,0 ATR (F2b+F3) | −0,143 | −0,094 | −0,307 | −0,189 | −0,020 | −0,194 | +18 % ; −4 % ; −1 % ; +14 % ; +14 % ; +12 % |
| V3 — BE 1,5 ATR (F2b+F3) | +0,089 | −0,131 | −0,267 | −0,105 | +0,079 | −0,058 | +32 % ; −6 % ; −0 % ; +18 % ; +19 % ; +14 % |
| V3 — BE 2,0 ATR (F2b+F3) | +0,047 | +0,000 | −0,184 | +0,016 | +0,104 | −0,105 | +28 % ; +0 % ; +3 % ; +25 % ; +20 % ; +13 % |
| V3 — BE 2,5 ATR (F2b+F3) | +0,032 | −0,002 | −0,089 | +0,002 | +0,071 | −0,094 | +27 % ; +0 % ; +7 % ; +24 % ; +18 % ; +14 % |
| V3 — BE 3,0 ATR (F2b+F3) | +0,062 | −0,024 | +0,023 | +0,097 | −0,018 | −0,103 | +29 % ; −1 % ; +13 % ; +30 % ; +14 % ; +13 % |
| V3 — BE 4,0 ATR (F2b+F3) | +0,063 | −0,063 | +0,001 | +0,225 | +0,052 | −0,113 | +29 % ; −3 % ; +12 % ; +34 % ; +17 % ; +13 % |

## H. Take-profit fixe : borne optimiste (décision du porteur, vérifiée) et excursion favorable de RE-1

Trades de RE-1 à H = 26, cooldown. Espérance nette par trade de RE-1 : +0,369 ATR à 5 bps, +0,233 à 10 bps ; P90 du résultat net : +5,53 ATR (5 bps).

Borne optimiste : sortie à +TP · ATR14(t) dès que la MFE atteint TP, résultat de RE-1 sinon. Fenêtre complète : MFE sur t + 1 … t + H, stops ignorés (TP toujours touché avant le stop) ; avant sortie : MFE jusqu'à la sortie de RE-1, barre du stop comprise (TP prioritaire dans la barre).

| Frais | Take-profit | Fenêtre complète : touchés ; espérance ; RE-1 des touchés | Avant sortie : touchés ; espérance ; RE-1 des touchés |
|---|---|---|---|
| 5 bps | TP = 2 ATR | 57,2 % ; +0,200 ; +2,15 | 53,1 % ; +0,040 ; +2,48 |
| 5 bps | TP = 3 ATR | 42,2 % ; +0,278 ; +3,07 | 38,9 % ; +0,112 ; +3,52 |
| 5 bps | TP = 4 ATR | 31,4 % ; +0,309 ; +4,04 | 29,0 % ; +0,166 ; +4,55 |
| 5 bps | TP = 5 ATR | 24,0 % ; +0,314 ; +5,07 | 22,2 % ; +0,193 ; +5,64 |
| 5 bps | TP = 6 ATR | 18,4 % ; +0,347 ; +5,95 | 16,9 % ; +0,229 ; +6,66 |
| 10 bps | TP = 2 ATR | 57,2 % ; +0,064 ; +2,01 | 53,1 % ; −0,096 ; +2,34 |
| 10 bps | TP = 3 ATR | 42,2 % ; +0,142 ; +2,93 | 38,9 % ; −0,024 ; +3,37 |
| 10 bps | TP = 4 ATR | 31,4 % ; +0,173 ; +3,89 | 29,0 % ; +0,030 ; +4,40 |
| 10 bps | TP = 5 ATR | 24,0 % ; +0,179 ; +4,91 | 22,2 % ; +0,057 ; +5,48 |
| 10 bps | TP = 6 ATR | 18,4 % ; +0,211 ; +5,79 | 16,9 % ; +0,093 ; +6,50 |

**Excursion favorable des trades de RE-1** — cellule : part des trades dont la MFE atteint m ATR ; part qui l'atteint puis finit en perte nette à 5 bps (part parmi ceux qui l'atteignent) ; perte nette moyenne de ces derniers (ATR).

| Seuil | MFE26, fenêtre complète | MFE avant la sortie de RE-1 |
|---|---|---|
| m = 1,0 | 77,7 % ; 34,1 % (44 %) ; −2,00 | 73,8 % ; 30,2 % (41 %) ; −1,98 |
| m = 1,5 | 66,7 % ; 24,9 % (37 %) ; −1,99 | 62,6 % ; 20,8 % (33 %) ; −1,98 |
| m = 2,0 | 57,2 % ; 18,3 % (32 %) ; −2,04 | 53,1 % ; 14,3 % (27 %) ; −2,03 |
| m = 2,5 | 49,3 % ; 13,7 % (28 %) ; −2,08 | 45,5 % ; 9,9 % (22 %) ; −2,07 |
| m = 3,0 | 42,2 % ; 10,2 % (24 %) ; −2,27 | 38,9 % ; 6,9 % (18 %) ; −2,34 |
| m = 4,0 | 31,4 % ; 6,1 % (19 %) ; −2,46 | 29,0 % ; 3,7 % (13 %) ; −2,69 |

## I. Annexe — réouverture immédiate après un stop ou un break-even (H = 26, 5 bps)

Débloqués : trades ouverts grâce à une sortie anticipée, absents de la lecture cooldown de la même configuration ; perdus : trades de la lecture cooldown masqués par un débloqué.

| Configuration | Trades : cooldown ; réouverture | Débloqués : n ; esp. ATR | Perdus : n ; esp. ATR | Esp. ATR : cooldown ; réouverture [IC] | PnL : cooldown ; réouverture | MDD : cooldown ; réouverture | Calmar : cooldown ; réouverture |
|---|---|---|---|---|---|---|---|
| RE-1 (contrôle) | 1 080 ; 1 108 | 37 ; −0,404 | 9 ; +0,912 | +0,369 ; +0,338 [+0,061 ; +0,616] | +138 % ; +133 % | −13,5 % ; −13,9 % | 1,16 ; 1,09 |
| V1 — BE 1,0 ATR (F3) | 1 080 ; 1 158 | 95 ; −0,168 | 17 ; +1,841 | +0,333 ; +0,269 [+0,026 ; +0,519] | +117 % ; +102 % | −17,5 % ; −18,0 % | 0,79 ; 0,69 |
| V1 — BE 1,5 ATR (F3) | 1 080 ; 1 132 | 67 ; −0,423 | 15 ; +1,109 | +0,345 ; +0,290 [+0,042 ; +0,543] | +122 % ; +106 % | −16,0 % ; −17,2 % | 0,89 ; 0,75 |
| V1 — BE 2,0 ATR (F3) | 1 080 ; 1 120 | 55 ; −0,384 | 15 ; +1,384 | +0,354 ; +0,304 [+0,054 ; +0,558] | +128 % ; +113 % | −13,1 % ; −13,5 % | 1,13 ; 0,99 |
| V1 — BE 2,5 ATR (F3) | 1 080 ; 1 114 | 45 ; −0,352 | 11 ; +1,542 | +0,371 ; +0,330 [+0,075 ; +0,589] | +137 % ; +127 % | −12,4 % ; −12,5 % | 1,25 ; 1,17 |
| V1 — BE 3,0 ATR (F3) | 1 080 ; 1 110 | 40 ; −0,507 | 10 ; +1,696 | +0,368 ; +0,325 [+0,060 ; +0,589] | +135 % ; +122 % | −12,7 % ; −13,0 % | 1,21 ; 1,09 |
| V1 — BE 4,0 ATR (F3) | 1 080 ; 1 108 | 38 ; −0,433 | 10 ; +1,290 | +0,373 ; +0,337 [+0,063 ; +0,609] | +139 % ; +131 % | −13,1 % ; −13,5 % | 1,20 ; 1,11 |
| V2 — BE 1,0 ATR (F2b) | 1 080 ; 1 201 | 139 ; −0,222 | 18 ; +0,455 | +0,248 ; +0,190 [−0,017 ; +0,404] | +79 % ; +68 % | −12,2 % ; −14,5 % | 0,83 ; 0,63 |
| V2 — BE 1,5 ATR (F2b) | 1 080 ; 1 155 | 88 ; −0,682 | 13 ; +0,532 | +0,327 ; +0,248 [+0,006 ; +0,496] | +114 % ; +92 % | −14,7 % ; −15,0 % | 0,92 ; 0,76 |
| V2 — BE 2,0 ATR (F2b) | 1 080 ; 1 125 | 56 ; −0,251 | 11 ; +1,454 | +0,365 ; +0,324 [+0,089 ; +0,572] | +136 % ; +128 % | −12,9 % ; −13,0 % | 1,19 ; 1,13 |
| V2 — BE 2,5 ATR (F2b) | 1 080 ; 1 120 | 49 ; −0,140 | 9 ; +2,234 | +0,354 ; +0,318 [+0,072 ; +0,566] | +130 % ; +123 % | −14,3 % ; −14,4 % | 1,04 ; 0,99 |
| V2 — BE 3,0 ATR (F2b) | 1 080 ; 1 115 | 44 ; −0,078 | 9 ; +2,234 | +0,377 ; +0,344 [+0,092 ; +0,599] | +144 % ; +139 % | −14,4 % ; −14,5 % | 1,12 ; 1,08 |
| V2 — BE 4,0 ATR (F2b) | 1 080 ; 1 112 | 42 ; −0,235 | 10 ; +1,773 | +0,394 ; +0,358 [+0,098 ; +0,618] | +148 % ; +140 % | −15,0 % ; −15,1 % | 1,09 ; 1,04 |
| V3 — BE 1,0 ATR (F2b+F3) | 1 080 ; 1 255 | 197 ; −0,298 | 22 ; +1,439 | +0,212 ; +0,110 [−0,070 ; +0,302] | +63 % ; +36 % | −15,5 % ; −21,6 % | 0,55 ; 0,24 |
| V3 — BE 1,5 ATR (F2b+F3) | 1 080 ; 1 179 | 116 ; −0,604 | 17 ; +1,342 | +0,304 ; +0,199 [−0,018 ; +0,425] | +99 % ; +68 % | −15,8 % ; −20,7 % | 0,77 ; 0,44 |
| V3 — BE 2,0 ATR (F2b+F3) | 1 080 ; 1 137 | 72 ; −0,222 | 15 ; +1,899 | +0,350 ; +0,294 [+0,078 ; +0,525] | +126 % ; +111 % | −11,7 % ; −11,2 % | 1,25 ; 1,19 |
| V3 — BE 2,5 ATR (F2b+F3) | 1 080 ; 1 126 | 57 ; −0,064 | 11 ; +2,623 | +0,357 ; +0,313 [+0,086 ; +0,544] | +129 % ; +119 % | −12,3 % ; −12,3 % | 1,20 ; 1,13 |
| V3 — BE 3,0 ATR (F2b+F3) | 1 080 ; 1 117 | 47 ; −0,186 | 10 ; +2,886 | +0,377 ; +0,331 [+0,093 ; +0,578] | +141 % ; +128 % | −13,4 % ; −12,9 % | 1,18 ; 1,14 |
| V3 — BE 4,0 ATR (F2b+F3) | 1 080 ; 1 112 | 43 ; −0,264 | 11 ; +2,039 | +0,398 ; +0,357 [+0,102 ; +0,618] | +149 % ; +138 % | −14,5 % ; −14,7 % | 1,13 ; 1,06 |
