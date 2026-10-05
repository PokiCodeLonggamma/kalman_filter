# EXP-D05.6 — Taille selon l'état du compte : variantes A, B et C contre un risque fixe

*GO du porteur du 2026-10-05 (« une à la fois, comparées à un r fixe »). Calcul : `python
experiments/D05_6/run_D05_6.py --calcul` (175 s).*

*Variantes (seuils sur le capital valorisé de chaque compte, même règle en challenge et en compte financé) :*
- *A, frein : 0,20 %/ATR ; 0,10 à −5 % ; de nouveau 0,20 au-dessus de −2 %.*
- *B, sprint : 0,10 ; 0,20 à +3 % ; de nouveau 0,10 sous +1 %.*
- *C, coussin : risque proportionnel à la distance au plancher de −10 %, égal à r0 quand le capital vaut 1.*

*Lecture principale de D05.4 ; valeur d'une tentative de D05.5. Contrôle passé : chaque risque fixe redonne D05.4 et
D05.5.*

*Comparaison au risque fixe : réussite et valeur d'un risque fixe au même délai médian, par interpolation linéaire
entre deux r fixes.*

## Verdict

- **A (frein) ne fait pas mieux qu'un risque fixe.**
  - Réussite : 61,2 % en 79 jours, soit +1,9 point au même délai (sans 2026 : +0,9), dans le bruit.
  - Valeur à 12 mois : +3 768 €, soit −4 653 € au même délai.
- **B (sprint) fait moins bien qu'un risque fixe** : 69,1 % en 158 jours, soit −5,7 points au même délai (sans 2026 :
  −4,9).
- **C (coussin) supprime les échecs par la perte totale**, par construction : le risque tend vers zéro près du
  plancher.
  - Sur tous les départs, la réussite monte à 93 à 98 %, soit +17 à +24 points au même délai.
  - Mais les échecs se changent en comptes bloqués : P90 du délai de 682 à 1 081 jours.
  - Sans 2026, 38 à 43 % des comptes C restent en cours, et la réussite retombe à 57 à 61 %.
- **Ta cible** (délai médian de 90 à 180 jours, réussite d'au moins 60 à 65 %) :
  - sur tous les départs, elle est atteinte par le risque fixe à 0,10 et 0,15, par B et par C (r0 de 0,15 à 0,25) ;
  - sans 2026, seul C à r0 = 0,20 l'atteint (60,9 % en 111 jours), avec 38,6 % de comptes encore en cours.
- **Valeur d'une tentative :** aucune variante n'approche le risque fixe à 0,20 (+9 218 € à 12 mois). A, B et C
  restent entre +2 171 et +4 484 €.

## 1. Tous les départs (1 826 ; valeur à 12 mois sur 1 462 départs)

| Configuration | Réussite P1 + P2 [IC 95 %] | Échecs, perte totale | En cours | Délai médian ; P90 | Écart au fixe, même délai | Valeur à 12 mois [IC 95 %] | Écart de valeur, même délai |
|---|---|---|---|---|---|---|---|
| r fixe 0,10 | 78,5 % [69,7 ; 86,7] | 18,1 % | 3,4 % | 173 ; 371 j | — | +3 336 € [+2 031 ; +4 774] | — |
| r fixe 0,15 | 60,4 % [49,5 ; 71,4] | 37,5 % | 2,1 % | 100 ; 230 j | — | +6 902 € [+4 418 ; +9 728] | — |
| r fixe 0,20 | 58,8 % [47,9 ; 69,3] | 39,5 % | 1,6 % | 68 ; 158 j | — | +9 218 € [+5 833 ; +12 821] | — |
| A · frein | 61,2 % [50,6 ; 71,5] | 37,1 % | 1,6 % | 79 ; 241 j | +1,9 pt | +3 768 € [+2 448 ; +5 288] | −4 653 € |
| B · sprint | 69,1 % [59,7 ; 78,5] | 28,2 % | 2,7 % | 158 ; 413 j | −5,7 pt | +3 459 € [+2 104 ; +5 025] | −605 € |
| C · r0 0,10 | 97,0 % [92,7 ; 100,0] | 0,0 % | 3,0 % | 230 ; 978 j | +17,1 pt | +2 171 € [+1 037 ; +3 600] | −650 € |
| C · r0 0,15 | 97,9 % [94,3 ; 100,0] | 0,0 % | 2,1 % | 174 ; 1 049 j | +19,3 pt | +4 463 € [+2 726 ; +6 638] | +1 134 € |
| C · r0 0,20 | 93,4 % [88,0 ; 97,8] | 0,0 % (jour : 0,4 %) | 6,1 % | 137 ; 1 081 j | +24,0 pt | +4 484 € [+2 642 ; +7 008] | −630 € |
| C · r0 0,25 | 81,5 % [72,8 ; 89,9] | 0,0 % (jour : 1,5 %) | 16,9 % | 100 ; 682 j | +21,2 pt | +4 383 € [+2 293 ; +7 306] | −2 521 € |

- `[OBS]` **A et B se situent sur la frontière du risque fixe, ou en dessous.**
  - Le frein réduit la taille dans les creux, ce qui ralentit aussi la remontée.
  - Le sprint accélère après +3 %, puis revient à 0,10 sous +1 % : il paie les reculs au risque haut.
- `[OBS]` **Avec C, les pertes du jour remplacent les pertes totales.** Au-dessus du capital initial, le risque passe
  au-dessus de r0 (jusqu'à 1,9 fois r0 près de +9 %). D'où 0,4 % et 1,5 % d'échecs par la perte du jour à r0 = 0,20
  et 0,25.
- `[OBS]` **C allonge la queue des délais :** le P90 passe de 158-371 jours à 682-1 081 jours. Un compte proche du
  plancher n'y risque presque plus rien et attend.

## 2. Sans 2026 (1 553 départs ; valeur à 12 mois sur 1 189 départs)

| Configuration | Réussite P1 + P2 [IC 95 %] | En cours | Délai médian | Écart au fixe, même délai | Valeur à 12 mois |
|---|---|---|---|---|---|
| r fixe 0,10 | 61,7 % [49,6 ; 73,3] | 17,1 % | 203 j | — | +2 340 € |
| r fixe 0,15 | 53,6 % [41,2 ; 66,3] | 2,3 % | 118 j | — | +8 397 € |
| r fixe 0,20 | 52,3 % [40,5 ; 64,7] | 2,0 % | 78 j | — | +11 100 € |
| A · frein | 54,0 % [41,8 ; 65,5] | 2,3 % | 104 j | +0,9 pt | +4 479 € |
| B · sprint | 56,7 % [44,5 ; 68,4] | 10,2 % | 208 j | −4,9 pt | +3 221 € |
| C · r0 0,15 | 57,8 % [45,7 ; 70,3] | 42,2 % | 143 j | +1,8 pt | +2 964 € |
| C · r0 0,20 | 60,9 % [48,4 ; 73,4] | 38,6 % | 111 j | +7,5 pt | +2 850 € |
| C · r0 0,25 | 56,3 % [45,2 ; 68,1] | 41,9 % | 83 j | +3,9 pt | +2 762 € |

- `[OBS]` **La réussite de C tenait en partie à 2026.** Sans 2026, l'avantage de C tombe de +17-24 à +2-8 points :
  les comptes bloqués le restent faute de l'embellie de 2026.

## 3. Lecture

- `[HYP]` **Le coussin protège la réussite, le risque fixe haut maximise la valeur.**
  - En challenge, un risque qui baisse près du plancher transforme les échecs en attentes.
  - En compte financé, il freine l'extraction des gains. Or la perte du porteur y est plafonnée à 540 € (D05.5), donc
    protéger le compte financé coûte de la valeur.
- `[HYP]` **Combinaison à mesurer : C en challenge, risque fixe haut en compte financé.** Elle pourrait réunir la
  réussite de C et la valeur du risque fixe à 0,20. C'est un facteur nouveau, la taille propre à chaque phase, à
  mesurer seul.

## 4. Limites

- **Seuils des variantes fixés par le porteur après lecture de D05.4,** sur des données déjà lues. Départs
  chevauchants : IC larges.
- **La comparaison au même délai** interpole linéairement entre deux r fixes ; entre 173 et 571 jours, l'écart entre
  ces deux points est large.
- **C suppose une surveillance continue de l'équité** et une taille recalculée à chaque entrée. Un gap qui ferait
  perdre plus que le coussin en une fois n'est pas apparu ici, mais reste possible.
- **Mêmes limites de coûts et de règles de la firme que D05.5.**
- **Les 8 métriques par trade sont celles de D05.4 :** les trades ne changent pas, seules les tailles changent.
