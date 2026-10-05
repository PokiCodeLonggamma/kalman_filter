# EXP-D05.7 — Tirage par blocs de semaines, sans 2026 : le roster final face à des histoires recomposées

*GO du porteur du 2026-10-05 : blocs d'une semaine et de quatre semaines, 200 histoires chacune. Calcul : `python
experiments/D05_7/run_D05_7.py --calcul` (2 367 s sur 6 processus).*

*Méthode, avec `propfirm.blocs` (nouveau) et le moteur `propfirm` :*
- *Source : 221 semaines entières, du lundi 2021-10-04 au lundi 2025-12-29, soit 4 006 trades des six actifs, sans
  2026.*
- *Histoire recomposée : 221 semaines tirées avec remise, par blocs d'une semaine ou de quatre semaines consécutives.*
  - *Chaque semaine apporte tous ses trades sur les six actifs, avec leur chemin de prix d'origine.*
  - *Les liens entre actifs dans la semaine sont gardés ; l'enchaînement des semaines (ou des mois) est détruit.*
- *Sur chaque histoire : la référence et les 5 pistes du roster, un départ à chaque minuit, la valeur d'une tentative
  et d'une suite de tentatives, à 12 et 24 mois.*
- *Contrôle passé : l'histoire « semaines dans l'ordre » redonne exactement la simulation d'origine (24 valeurs).*
- *Lecture : écarts entre pistes sur les mêmes histoires ; part des histoires où l'écart est positif ; rang de
  l'histoire réelle (sans 2026) dans la distribution.*

## Verdict

- **La vitesse du challenge survit, en suite de tentatives.**
  - Chaque pas de vitesse (0,20 → 0,25, puis 0,25 → 0,30) rapporte en médiane +1,9 à +2,3 k€ en 12 mois, et +3,4 à
    +4,1 k€ en 24 mois.
  - L'écart est positif dans 80 à 94 % des histoires, avec des blocs d'une comme de quatre semaines.
  - L'histoire réelle était même moins favorable à la vitesse que la plupart des histoires recomposées (rang de 18 à
    38 %, sauf 0,25 → 0,30 à 24 mois : 62 à 66 %).
- **La relance ne survit pas.**
  - Au lieu du risque fixe 0,25, elle rapporte en médiane de −1,1 à +0,1 k€ selon la lecture, et n'est positive que
    dans 37 à 58 % des histoires.
  - Son gain dans l'histoire réelle se plaçait parmi les 10 à 24 % d'histoires les plus favorables.
- **Le compte financé à 0,25 au lieu de 0,20 ne survit pas par tentative.**
  - Médiane de −0,1 à +0,04 k€ ; positif dans 42 à 52 % des histoires.
  - L'histoire réelle se plaçait parmi les 3 à 6 % les plus favorables.
  - En suite, il garde un petit gain : +0,4 à +1,3 k€ en médiane, positif dans 62 à 68 % des histoires.
- **Les blocs de quatre semaines ne changent presque rien.** Garder un mois d'enchaînement ne rend ni la relance ni
  l'avantage du compte financé agressif.
- **Toutes les pistes valent beaucoup moins dans les histoires recomposées.**
  - L'histoire réelle se place entre les 78e et 96e centiles, pour chaque piste.
  - Par tentative à 12 mois, la valeur passe de +6,7 à +13,2 k€ (réel) à +3,1 à +4,6 k€ en médiane.
  - En suite à 24 mois, de +38,5 à +56,7 k€ à +23,0 à +34,1 k€.
  - La valeur reste positive dans 90 à 99,5 % des histoires.
- **Par tentative, les pistes deviennent presque équivalentes.** La perte du challenge rapide (−3,1 à −3,5 k€ dans
  l'histoire réelle, à 12 mois) se réduit à −0,1 à −0,2 k€ en médiane. L'histoire réelle était parmi les 2 à 6 % les
  plus défavorables à la vitesse.

## 1. Challenges

| Challenge | Histoire réelle : réussite ; délai médian | Blocs d'une semaine : réussite médiane [P5 ; P95] ; délai | Blocs de quatre semaines |
|---|---|---|---|
| 0,20 | 52,4 % ; 78 j | 38,5 % [22,2 ; 60,2] ; 70 j | 41,9 % [22,9 ; 59,6] ; 70 j |
| 0,25 | 44,4 % ; 47 j | 36,4 % [20,8 ; 54,6] ; 50 j | 39,0 % [23,6 ; 54,2] ; 49 j |
| 0,30 | 39,3 % ; 35 j | 34,2 % [21,6 ; 47,8] ; 38 j | 35,9 % [22,4 ; 49,5] ; 37 j |

- `[OBS]` **Sans l'ordre réel des semaines, la réussite baisse pour tous les challenges, et surtout pour le plus
  lent :** −13,9 points à 0,20, −5,1 points à 0,30 (blocs d'une semaine). Les réussites se rapprochent (34 à 39 %).

## 2. Écarts entre pistes (médiane [P5 ; P95] sur 200 histoires ; part positive ; rang de l'histoire réelle)

| Écart | Mesure | Histoire réelle | Blocs d'une semaine | Blocs de quatre semaines |
|---|---|---|---|---|
| 1 − réf. : financé 0,25 | tentative, 12 mois | +1 215 € | −8 € [−4 265 ; +1 266] ; 48 % ; rang 94 % | −28 € [−3 169 ; +1 246] ; 44 % ; rang 94 % |
| | suite, 24 mois | +7 037 € | +1 302 € [−10 125 ; +8 820] ; 63 % ; rang 90 % | +1 297 € [−14 474 ; +9 203] ; 62 % ; rang 90 % |
| 2 − 1 : challenge 0,25 | tentative, 12 mois | −3 456 € | −69 € [−2 810 ; +1 135] ; 44 % ; rang 4 % | −138 € [−3 183 ; +913] ; 40 % ; rang 4 % |
| | suite, 12 mois | +1 343 € | +2 287 € [−342 ; +7 684] ; 94 % ; rang 30 % | +2 109 € [−564 ; +5 811] ; 90 % ; rang 36 % |
| | suite, 24 mois | +530 € | +4 054 € [−2 379 ; +19 359] ; 86 % ; rang 18 % | +3 645 € [−4 320 ; +15 687] ; 80 % ; rang 24 % |
| 3a − 1 : relance | tentative, 12 mois | +822 € | −83 € [−1 551 ; +3 355] ; 45 % ; rang 84 % | +101 € [−1 394 ; +2 385] ; 58 % ; rang 76 % |
| | suite, 24 mois | +4 830 € | −949 € [−9 663 ; +11 110] ; 40 % ; rang 84 % | −154 € [−8 718 ; +12 282] ; 48 % ; rang 84 % |
| 3b − 2 : relance (challenge 0,25) | suite, 24 mois | +4 593 € | −1 103 € [−9 241 ; +7 945] ; 37 % ; rang 90 % | −167 € [−9 116 ; +12 145] ; 48 % ; rang 82 % |
| 3b − 3a : challenge 0,25 (relance) | suite, 24 mois | +293 € | +3 942 € [−3 717 ; +18 244] ; 83 % ; rang 19 % | +3 365 € [−2 473 ; +12 620] ; 83 % ; rang 20 % |
| 3c − 3b : challenge 0,30 (relance) | suite, 12 mois | +1 458 € | +2 107 € [−395 ; +6 988] ; 92 % ; rang 38 % | +2 064 € [−745 ; +6 321] ; 88 % ; rang 38 % |
| | suite, 24 mois | +6 096 € | +4 105 € [−2 634 ; +13 986] ; 84 % ; rang 66 % | +4 004 € [−4 460 ; +17 159] ; 84 % ; rang 62 % |

(Toutes les lectures sont en annexe A3.)

## 3. Valeur des pistes (médiane sur 200 histoires, blocs d'une semaine ; histoire réelle entre parenthèses)

| Piste | Tentative, 12 mois | Suite, 12 mois | Suite, 24 mois |
|---|---|---|---|
| Référence 0,20 × 0,20 | +4 153 € (+11 117 €) | +10 166 € (+17 277 €) | +23 630 € (+38 488 €) |
| 1 · 0,20 × 0,25 | +3 786 € (+12 332 €) | +10 129 € (+19 668 €) | +23 007 € (+45 526 €) |
| 2 · 0,25 × 0,25 | +3 400 € (+8 876 €) | +13 192 € (+21 011 €) | +27 984 € (+46 056 €) |
| 3a · 0,20 × relance | +4 124 € (+13 154 €) | +10 190 € (+21 385 €) | +23 206 € (+50 356 €) |
| 3b · 0,25 × relance | +3 597 € (+10 042 €) | +12 219 € (+22 547 €) | +27 749 € (+50 649 €) |
| 3c · 0,30 × relance | +3 129 € (+6 707 €) | +15 357 € (+24 005 €) | +32 880 € (+56 745 €) |

- `[OBS]` **En suite, le classement sans l'ordre réel ne dépend plus que de la vitesse du challenge :** 3c en tête, puis
  2 et 3b, puis 1, 3a et la référence, ces trois-là à égalité.

## 4. Lecture

- `[HYP]` **La vitesse paie en suite par mécanique.** Un challenge plus court donne plus de tentatives et de comptes
  financés par an. Sans l'ordre réel, les réussites se rapprochent, et c'est alors le nombre de tentatives qui décide.
- `[HYP]` **La relance et le compte financé agressif misaient sur l'ordre des semaines.** Leur gain de D05.6bis venait
  des comptes financés démarrés dans une bonne période, juste après une réussite (D05.6bis, §4). Sans cet ordre, ils ne
  rapportent plus.
  - Un mois d'enchaînement ne suffit pas à le rendre. Soit cette persistance dure plus d'un mois, soit l'histoire
    réelle a simplement été favorable.
  - Le tirage ne permet pas de trancher entre les deux.
- `[HYP]` **Le scénario annoncé par le porteur ne s'est pas produit.** L'avantage des pistes rapides ne s'effondre pas
  avec des blocs d'une semaine. Ce qui s'effondre, aux deux longueurs, c'est le gain du compte financé agressif et de
  la relance.
- `[HYP]` **L'histoire réelle a été favorable à toutes les pistes.** Les valeurs de D05.4 à D05.6bis sont donc hautes :
  les médianes recomposées sont plus prudentes pour une projection.

## 5. Limites

- **200 histoires par série :** une part d'histoires est connue à ± 3,5 points environ.
- **Blocs d'au plus quatre semaines :** une persistance de plusieurs mois (régimes de marché) n'est pas testée. Des
  blocs de 13 semaines la testeraient, avec seulement 17 blocs par histoire.
- **Les histoires recomposent les semaines de 2021 à 2025 :** elles ne contiennent aucun marché absent de ces données.
- **Débordements :** un trade qui chevauche deux blocs garde son chemin d'origine. Décalage d'une heure possible entre
  heure d'été et heure d'hiver.
- **Roster choisi sur ces données (D05.6bis).** Au-delà de 0,25 %/ATR, l'exécution réelle s'éloigne du modèle (écarts,
  glissement et gaps non modélisés).
- **Suite :** un seul compte à la fois, rachat immédiat, nombre de tentatives illimité ; mêmes limites de coûts et de
  règles de la firme que D05.5.
- **Les 8 métriques par trade sont celles de D04.1 :** les trades ne changent pas, seul leur ordre change.
