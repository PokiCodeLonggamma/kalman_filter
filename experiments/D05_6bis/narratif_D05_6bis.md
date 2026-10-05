# EXP-D05.6bis — Une taille propre à chaque phase : challenge et compte financé (« hybride »)

*GO du porteur du 2026-10-05 : combos A et B, et mesures propres (« si oui, ajoute-les à ce run »). Calcul : `python
experiments/D05_6bis/run_D05_6bis.py --calcul` (136 s).*

*Méthode, avec le moteur `propfirm` :*
- *Une simulation de challenge par taille de challenge, une simulation de compte financé par taille de compte financé ;
  chaque combinaison relie les deux (7 × 7 = 49).*
  - *Challenge : risque fixe 0,10 à 0,30 %/ATR ; coussin r0 0,15 et 0,20.*
  - *Compte financé : risque fixe 0,10 à 0,30 ; coussin r0 0,20 ; relance (0,20 ; 0,40 quand le capital valorisé tombe à
    −5 % ; 0,20 de nouveau au-dessus de −2 % : le miroir du frein A).*
  - *Combos du porteur : A = coussin r0 0,15 ou 0,20 en challenge, fixe 0,20 ou 0,25 en compte financé ; B = fixe 0,15
    en challenge, fixe 0,20 ou 0,25 en compte financé. Le reste est l'exploration autorisée par le porteur.*
  - *0,30 a été ajouté après un premier calcul : en suite de tentatives, le meilleur r était au bord de la grille.*
- *Deux mesures, en euros pour un compte de 100 000 :*
  - *valeur d'une tentative (D05.5) : −540 € + (540 € + 80 % des retraits) s'il y a au moins un retrait ;*
  - *suite de tentatives (nouvelle, `propfirm.suite`) : un seul compte à la fois ; au minuit qui suit chaque échec du
    challenge ou chaque perte du compte financé, une nouvelle tentative à 540 €. C'est la lecture « Burn & Churn ».*
- *Horizons : 12 et 24 mois depuis le départ, et 12 mois sans 2026. Référence : fixe 0,20 dans les deux phases.*
- *Écarts appariés (mêmes départs) avec IC à 95 % par blocs de mois de départ.*
- *Contrôle passé : fixe r dans les deux phases redonne D05.5 ; coussin 0,20 dans les deux phases redonne D05.6 ; chaque
  taille de challenge redonne D05.6.*

## Verdict

- **Ni le combo A ni le combo B ne battent la référence** (+9 218 € par tentative à 12 mois).
  - **A (coussin en challenge)** : −0,8 à −3,2 k€ par tentative à 12 mois, jusqu'à −4,8 k€ sans 2026.
    - En suite de tentatives, il perd 10 à 12 k€ en 12 mois et environ 30 k€ en 24 mois : un challenge bloqué occupe
      la place.
    - Son délai médian (137 et 174 jours) dépasse ta limite de 120 jours.
  - **B (fixe 0,15 en challenge)** : égal à la référence par tentative (−274 € et +7 € à 12 mois ; IC de part et
    d'autre de zéro), moins bon en suite (−1,7 à −3,2 k€).
- **Ce qui bat la référence partout : garder 0,20 en challenge et monter le seul compte financé.**
  - Fixe 0,25 en compte financé : +1,0 à +1,2 k€ par tentative ; +2,4 à +6,8 k€ en suite.
  - Relance en compte financé : +1,7 à +2,1 k€ par tentative ; +3,6 à +10,4 k€ en suite.
  - « Partout » : tentative et suite, 12 et 24 mois, sans 2026, IC sans zéro ; écart positif ou nul pour chaque année
    de départ.
- **Dans le compte financé, l'optimum du risque fixe est vers 0,25.** 0,30 fait moins bien (−0,4 k€ contre la
  référence, au lieu de +1,0 k€). Le coussin détruit de la valeur (−2,9 à −5,3 k€).
- **En suite de tentatives, la vitesse du challenge prime.**
  - À taille de compte financé égale (0,20, 0,25 ou relance), un challenge à 0,25 ou 0,30 bat 0,20.
  - L'écart à la référence monte jusqu'à +17,5 k€ en 24 mois (0,30 × relance), et l'optimum n'est pas atteint à 0,30.
  - Par tentative, au contraire, un challenge à 0,25 ou 0,30 fait moins bien que la référence (−0,8 à −6,9 k€).
- **Le compte financé agressif ne gagne qu'après une réussite.** Démarrés à un minuit quelconque, 0,25 et la relance
  retirent moins que 0,20 (16,1 et 15,7 k€ contre 18,0 k€ en 12 mois).

## 1. Le challenge selon sa taille

| Taille du challenge | Réussite P1 + P2 [IC 95 %] | Délai médian ; P90 | En cours | Sans 2026 : réussite ; en cours ; délai médian | Délai médian < 120 j |
|---|---|---|---|---|---|
| fixe 0,10 | 78,5 % [69,7 ; 86,7] | 173 ; 371 j | 3,4 % | 61,7 % ; 17,1 % ; 203 j | non |
| fixe 0,15 (B) | 60,4 % [49,5 ; 71,4] | 100 ; 230 j | 2,1 % | 53,6 % ; 2,3 % ; 118 j | oui |
| fixe 0,20 (réf.) | 58,8 % [47,9 ; 69,3] | 68 ; 158 j | 1,6 % | 52,3 % ; 2,0 % ; 78 j | oui |
| fixe 0,25 | 51,0 % [40,2 ; 61,2] | 41 ; 94 j | 1,5 % | 44,2 % ; 1,5 % ; 47 j | oui |
| fixe 0,30 | 45,2 % [35,3 ; 54,9] | 32 ; 69 j | 1,5 % | 39,2 % ; 1,2 % ; 35 j | oui |
| coussin 0,15 (A) | 97,9 % [94,3 ; 100,0] | 174 ; 1 049 j | 2,1 % | 57,8 % ; 42,2 % ; 143 j | non |
| coussin 0,20 (A) | 93,4 % [88,0 ; 97,8] | 137 ; 1 081 j | 6,1 % | 60,9 % ; 38,6 % ; 111 j | non (oui sans 2026) |

- `[OBS]` **Entre 0,15 et 0,20, la réussite ne change pas** (+1,6 point, IC presque confondus) ; 0,20 va 32 jours plus
  vite.
- `[OBS]` **À 0,30, la perte du jour commence à compter :** 4,9 % des départs échouent par elle (0,7 % à 0,25).

## 2. Valeur d'une tentative

| Challenge × compte financé | 12 mois [IC 95 %] | Écart à la réf., 12 mois [IC 95 %] | 24 mois (écart) | Sans 2026 (écart) |
|---|---|---|---|---|
| **réf.** fixe 0,20 × fixe 0,20 | +9 218 € [+5 833 ; +12 821] | — | +10 906 € | +11 100 € |
| B · fixe 0,15 × fixe 0,20 | +8 943 € | −274 € [−1 401 ; +1 040] | +11 930 € (+1 024) | +10 854 € (−246) |
| B · fixe 0,15 × fixe 0,25 | +9 225 € | +7 € [−1 446 ; +1 437] | +11 895 € (+989) | +11 155 € (+55) |
| A · coussin 0,15 × fixe 0,20 | +8 395 € | −822 € [−3 071 ; +1 676] | +8 258 € (−2 649) | +7 473 € (−3 627) |
| A · coussin 0,15 × fixe 0,25 | +7 067 € | −2 150 € [−4 714 ; +392] | +6 819 € (−4 088) | +6 276 € (−4 824) |
| A · coussin 0,20 × fixe 0,20 | +6 043 € | −3 175 € [−4 901 ; −1 570] | +6 567 € (−4 339) | +6 417 € (−4 683) |
| A · coussin 0,20 × fixe 0,25 | +6 551 € | −2 667 € [−4 298 ; −1 130] | +7 253 € (−3 654) | +6 937 € (−4 163) |
| fixe 0,20 × **fixe 0,25** | +10 259 € | **+1 042 €** [+481 ; +1 617] | +12 150 € (+1 243) | +12 319 € (+1 219) |
| fixe 0,20 × fixe 0,30 | +8 827 € | −391 € [−2 629 ; +1 426] | +10 521 € (−386) | +10 555 € (−545) |
| fixe 0,20 × **relance** | +10 895 € | **+1 677 €** [+586 ; +2 945] | +13 018 € (+2 112) | +13 135 € (+2 035) |
| fixe 0,20 × coussin 0,20 | +6 309 € | −2 909 € [−5 837 ; +124] | +8 014 € (−2 892) | +5 792 € (−5 307) |
| fixe 0,25 × fixe 0,25 | +7 504 € | −1 714 € [−3 521 ; −69] | +8 694 € (−2 212) | +8 849 € (−2 251) |
| fixe 0,30 × fixe 0,25 | +5 959 € | −3 258 € [−5 548 ; −1 136] | +6 693 € (−4 213) | +6 796 € (−4 304) |

- `[OBS]` **Le gain vient du compte financé, et ses queues le montrent.**
  - Avec 0,25, la tentative fait mieux que la référence dans 46 % des départs, moins bien dans 3,6 % ; le reste est
    égal (même challenge, échoué).
  - P90 : +38,3 k€ (0,25) et +46,4 k€ (relance), contre +35,0 k€ pour la référence. La médiane reste à −540 € : la
    moitié des tentatives ne touche aucun retrait en 12 mois.
- `[OBS]` **Par année de départ** (2021 à 2025), l'écart est positif chaque année pour 0,25 (+0,3 à +2,0 k€), et
  positif ou nul pour la relance (0 à +4,3 k€, surtout 2022 et 2023).
- `[OBS]` **Le coussin en challenge n'a l'avantage que pour les départs de 2025** (+3,4 et +11,3 k€), qui
  profitent de 2026 ; de 2021 à 2024, il perd chaque année.

## 3. Suite de tentatives (« Burn & Churn », un seul compte à la fois)

| Challenge × compte financé | 12 mois [IC 95 %] | Écart à la réf., 12 mois [IC 95 %] | 24 mois (écart) | Sans 2026 (écart) | Tentatives ; comptes financés en 24 mois |
|---|---|---|---|---|---|
| **réf.** fixe 0,20 × fixe 0,20 | +19 791 € [+15 501 ; +24 062] | — | +41 435 € | +17 274 € | 5,5 ; 2,2 |
| B · fixe 0,15 × fixe 0,20 | +16 703 € | −3 088 € [−3 734 ; −2 393] | +39 141 € (−2 294) | +14 046 € (−3 228) | 4,1 ; 1,6 |
| B · fixe 0,15 × fixe 0,25 | +17 408 € | −2 383 € [−3 549 ; −1 324] | +39 744 € (−1 691) | +14 816 € (−2 458) | 4,5 ; 1,9 |
| A · coussin 0,15 × fixe 0,20 | +8 452 € | −11 339 € [−14 384 ; −8 201] | +11 596 € (−29 839) | +7 195 € (−10 079) | 1,7 ; 0,9 |
| A · coussin 0,20 × fixe 0,20 | +7 769 € | −12 022 € [−15 399 ; −8 717] | +10 694 € (−30 741) | +6 254 € (−11 020) | 1,7 ; 0,9 |
| fixe 0,20 × **fixe 0,25** | +22 461 € | **+2 670 €** [+2 025 ; +3 342] | +48 246 € (+6 810) | +19 658 € (+2 384) | 6,0 ; 2,3 |
| fixe 0,20 × **relance** | +23 368 € | **+3 577 €** [+2 147 ; +4 988] | +51 869 € (+10 433) | +21 373 € (+4 099) | 6,0 ; 2,3 |
| fixe 0,25 × fixe 0,25 | +25 037 € | +5 246 € [+3 840 ; +6 680] | +50 929 € (+9 493) | +21 022 € (+3 748) | 7,9 ; 3,8 |
| fixe 0,30 × fixe 0,25 | +27 146 € | +7 355 € [+5 536 ; +9 340] | +54 508 € (+13 073) | +21 958 € (+4 685) | 9,1 ; 4,0 |
| fixe 0,30 × relance | +26 180 € | +6 389 € [+5 209 ; +7 567] | +58 920 € (+17 485) | +23 950 € (+6 677) | 8,3 ; 3,7 |

(Les combos A à 0,25 en compte financé sont du même ordre : −11,3 à −12,0 k€ en 12 mois, −30,4 et −30,9 k€ en 24 mois.)

- `[OBS]` **La suite inverse le classement du challenge.** Un échec y coûte 540 € et quelques semaines, puis une
  nouvelle tentative démarre ; un challenge plus court donne plus de tentatives et plus de comptes financés.
- `[OBS]` **Le coussin en challenge bloque la suite :** 1,7 tentative en 24 mois, contre 5,5 pour la référence.
- `[OBS]` **La référence est déjà très positive en suite :** médiane +18,1 k€ en 12 mois, P10 −2,2 k€ (quatre échecs),
  P90 +43,8 k€.
- `[OBS]` **À 0,30, l'optimum n'est pas atteint** (+17,5 k€ en 24 mois avec la relance). La grille s'arrête là.

## 4. Le compte financé, seul ou après une réussite

| Compte financé | Démarré à un minuit quelconque, 12 mois : reçu (80 %) ; perdus ; durée de vie médiane des perdus | Après une réussite du challenge à 0,20 : écart par tentative à 12 mois |
|---|---|---|
| fixe 0,15 | 16 295 € ; 89,1 % ; 161 j | −2 014 € |
| fixe 0,20 | 17 964 € ; 96,0 % ; 104 j | réf. |
| fixe 0,25 | 16 071 € ; 99,1 % ; 74 j | +1 042 € |
| fixe 0,30 | 12 541 € ; 100 % ; 54 j | −391 € |
| relance 0,20 → 0,40 | 15 683 € ; 99,8 % ; 78 j | +1 677 € |
| coussin 0,20 | 14 647 € ; 2,7 % ; 17 j | −2 909 € |

- `[OBS]` **Le classement s'inverse selon le moment du départ.**
  - Démarré à un minuit quelconque, 0,20 retire le plus.
  - Démarré juste après une réussite du challenge, 0,25 et la relance retirent plus que 0,20, à 12 comme à 24 mois.

## 5. Lecture

- `[HYP]` **Le challenge sert de filtre de période.**
  - Il réussit quand la stratégie traverse une bonne période. Le compte financé démarre alors dans cette période, et un
    risque plus haut l'exploite avant qu'elle ne finisse.
  - Un challenge rapide est un filtre réactif et bon marché : il échoue vite et pour 540 € dans les mauvaises périodes.
  - Cette lecture repose sur la persistance des bonnes périodes de RE-1. D05.7 peut la tester : un tirage par blocs
    courts coupe cette persistance, et l'avantage devrait alors fondre.
- `[HYP]` **Dans le compte financé, la perte du porteur est plafonnée.** Doubler le risque en creux (relance) y paie,
  alors que réduire le risque (coussin) y coûte. C'est la convexité de D05.5, vue sous un autre angle.
- `[HYP]` **Ton objectif de challenge et la politique « Burn & Churn » se contredisent.**
  - Par tentative, la meilleure taille de challenge est 0,15 à 0,20.
  - En suite, c'est la plus rapide mesurée (0,30), au prix d'une réussite plus faible (45 %).
  - Le choix dépend de la façon dont tu opères : une tentative à la fois, rachetée aussitôt après chaque échec (lecture
    « suite »), ou des tentatives dont le nombre est fixé à l'avance (lecture « tentative »).

## 6. Limites

- **Données déjà lues ; départs chevauchants.** 49 combinaisons : la meilleure est optimiste. Les IC par blocs de mois
  ne couvrent pas la dépendance entre périodes de plusieurs mois ; ils sont trop étroits pour un effet qui tiendrait à
  ces périodes.
- **0,30 ajouté après lecture,** pour situer l'optimum de la suite. Au-delà de 0,25, l'exécution réelle s'éloigne du
  modèle : écarts, glissement et gaps à fort levier ne sont pas modélisés, et la perte du jour commence à compter.
- **Relance :** seuils repris du frein du porteur, mesurés une seule fois. Doubler le risque après une perte peut
  tomber sous les règles de comportement d'une firme ; à vérifier dans les conditions FTMO.
- **Suite :** un seul compte à la fois, rachat immédiat, nombre de tentatives illimité, 540 € chacune ; pas de comptes
  en parallèle, pas de remise sur un nouvel essai.
- **Mêmes limites de coûts et de règles de la firme que D05.5.** Les 8 métriques par trade sont celles de D05.4 : les
  trades ne changent pas, seules les tailles changent.
