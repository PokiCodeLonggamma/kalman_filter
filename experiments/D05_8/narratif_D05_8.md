# EXP-D05.8 — Moment d'achat du challenge : sortie de compression de la volatilité, tendance haussière

*GO du porteur du 2026-10-05 (dernière mesure de la séquence taille) ; référence ajoutée à sa demande. Calcul :
`python experiments/D05_8/run_D05_8.py --calcul` (88 s).*

*Méthode :*
- *Indicateurs du panier crypto (BTC, ETH, SOL, AVAX, XRP) à chaque minuit, avec les seules barres closes avant lui :*
  - *V, sortie de compression : ATR moyen sur 7 jours au-dessus de sa moyenne sur 30 jours, alors que cette moyenne est
    sous la médiane de l'année ; ouvert 24 % des jours ;*
  - *T, tendance haussière : indice du panier au-dessus de sa moyenne sur 50 jours ; ouvert 50 % des jours.*
  - *Fenêtres conventionnelles, fixées avant le calcul, non optimisées.*
- *Par tentative : tentatives démarrées les jours ouverts, contre toutes.*
- *En suite (« rachat non aveugle ») : un compte à la fois ; la première tentative et chaque rachat attendent un jour
  ouvert. Comparée, départ par départ, à la suite sans filtre.*
- *Pistes : référence (0,20 × 0,20), piste 1 (0,20 × 0,25), piste 2 (0,25 × 0,25).*
- *Contrôles passés : les indicateurs ne changent pas quand on coupe les barres postérieures ; sans filtre, les pistes
  redonnent le roster de D05.6bis.*

## Verdict

- **T (tendance haussière) n'aide pas, et coûte en suite.**
  - Par tentative : +0,0 à +0,7 k€, avec des IC d'environ ±3 k€ ; réussite inchangée (53,6 % contre 55,1 % à 12 mois).
  - En suite : −1,7 à −6,1 k€ selon la piste et la lecture, IC sous zéro. Moins bien dans 30 à 67 % des départs,
    mieux dans 3 à 20 %.
- **V (sortie de compression) : gain par tentative possible, non démontré.**
  - Par tentative : +3,2 à +4,7 k€ (+34 à +54 %), mais tous les IC contiennent zéro.
  - Le gain vient surtout des départs de 2023 et 2024 ; ceux de 2025 perdent (−1,4 à −1,7 k€).
  - La réussite bouge peu : −0,5 point à 12 mois ; +4 à +5 points à 24 mois et sans 2026 (référence et piste 1).
- **En suite, attendre un jour ouvert coûte plus que le filtre ne rapporte.**
  - V : −0,7 à −1,9 k€ pour la référence et la piste 1 (sauf la référence à 24 mois : +0,8 k€, IC avec zéro) ;
    −2,9 à −9,3 k€ pour la piste 2.
  - En revanche, V économise des challenges : piste 1, 2,8 au lieu de 3,5 en 12 mois, 4,9 au lieu de 6,0 en 24 mois.
    La valeur par challenge acheté monte de 14 à 19 %.
- **Une règle d'attente efface l'avantage de la piste 2,** qui vit du nombre de tentatives.
  - Avec V, la piste 1 dépasse la piste 2 en suite à 24 mois (+46,6 k€ contre +41,6 k€) et sans 2026 (+18,7 k€ contre
    +17,2 k€).
  - Sans filtre, la piste 2 restait devant dans les trois lectures.

## 1. Par tentative (12 mois ; 1 462 départs)

| Piste | Filtre | Jours ouverts | Réussite : ouverts ; tous | Valeur : ouverts ; tous | Écart ouverts − tous [IC 95 %] |
|---|---|---|---|---|---|
| Référence | V | 23,8 % | 54,6 % ; 55,1 % | +12 368 € ; +9 218 € | +3 150 € [−1 165 ; +8 397] |
| Référence | T | 49,7 % | 53,6 % ; 55,1 % | +9 489 € ; +9 218 € | +271 € [−2 427 ; +3 072] |
| Piste 1 | V | 23,8 % | 54,6 % ; 55,1 % | +13 747 € ; +10 259 € | +3 488 € [−1 362 ; +9 190] |
| Piste 1 | T | 49,7 % | 53,6 % ; 55,1 % | +10 266 € ; +10 259 € | +6 € [−2 888 ; +3 095] |
| Piste 2 | V | 23,8 % | 41,1 % ; 46,4 % | +10 850 € ; +7 504 € | +3 346 € [−1 237 ; +9 048] |
| Piste 2 | T | 49,7 % | 45,3 % ; 46,4 % | +7 675 € ; +7 504 € | +171 € [−2 598 ; +3 129] |

## 2. En suite, rachat seulement les jours ouverts (12 mois ; 24 mois)

| Piste | Filtre | Suite filtrée, 12 mois (écart [IC 95 %]) | Suite filtrée, 24 mois (écart [IC 95 %]) | Challenges achetés en 24 mois : filtré ; sans filtre |
|---|---|---|---|---|
| Référence | V | +18 587 € (−1 204 [−2 426 ; −272]) | +42 232 € (+797 [−195 ; +1 776]) | 4,3 ; 5,6 |
| Référence | T | +16 606 € (−3 186 [−4 617 ; −1 974]) | +36 751 € (−4 684 [−6 656 ; −3 116]) | 5,9 ; 5,6 |
| Piste 1 | V | +20 534 € (−1 927 [−3 174 ; −883]) | +46 638 € (−1 607 [−2 853 ; −417]) | 4,9 ; 6,0 |
| Piste 1 | T | +19 079 € (−3 382 [−4 615 ; −2 219]) | +42 101 € (−6 144 [−7 554 ; −4 805]) | 6,1 ; 6,0 |
| Piste 2 | V | +22 088 € (−2 949 [−5 292 ; −946]) | +41 612 € (−9 317 [−13 296 ; −5 572]) | 5,6 ; 7,9 |
| Piste 2 | T | +22 952 € (−2 085 [−3 431 ; −876]) | +47 798 € (−3 130 [−4 291 ; −2 040]) | 7,8 ; 7,9 |

## 3. Lecture

- `[HYP]` **RE-1 joue à la hausse comme à la baisse.** Un filtre de tendance haussière ne choisit pas ses bonnes
  périodes ; il ne fait que retarder l'achat.
- `[HYP]` **V vise le moment où la volatilité repart d'un niveau bas,** le terrain d'un suiveur de tendance.
  - Mais son gain tient à quelques épisodes de 2023 et 2024.
  - C'est la fragilité des effets de période vue en D05.7.
- `[HYP]` **En suite, toute règle d'attente échange du temps contre de la sélectivité.** Pour un budget de challenges
  limité, V rapporte un peu plus par challenge acheté, sans que le gain soit démontré.

## 4. Limites

- **Un seul jeu de fenêtres (7, 30, 365 et 50 jours),** non optimisé. D'autres réglages feraient mieux ou moins bien ;
  les chercher sur ces données serait de l'ajustement.
- **Jours ouverts groupés en épisodes :** l'échantillon réel est petit, d'où des IC larges.
- **Pas de test sur histoires recomposées.** Le filtre lit des prix continus ; D05.7 recompose des trades, pas des
  prix.
- **Mêmes limites de coûts et de règles de la firme que D05.5.** Les 8 métriques par trade sont celles de D04.1.
