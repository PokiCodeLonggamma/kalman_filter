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
