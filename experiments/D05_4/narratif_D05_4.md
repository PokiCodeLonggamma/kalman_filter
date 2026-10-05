# EXP-D05.4 — Simulateur de challenge de prop firm : RE-1 version finale, étalon FTMO Swing

*GO du porteur du 2026-10-05, cadrage de l'agent validé (« Je valide ton Cadrage de l'étape 2. Construis le module
src/propfirm/ »). Module `src/propfirm/` (12 tests) ; calcul : `python experiments/D05_4/run_D05_4.py --calcul`
(188 s).*

*Règles (étalon FTMO Swing, porteur) :*
- *compte de 100 000 $ ; objectif de 9 % (P1), puis de 5 % (P2) ;*
- *perte du jour : 5 % du solde initial sous la référence de minuit CET/CEST ; perte totale : 10 %, statique ;*
- *au moins 4 jours de trading ;*
- *levier 1:2 sur les cryptos et 1:30 sur l'or ; marge plafonnée selon la règle du porteur.*

*Données : trades de D04.1 (six actifs, 2021-10 → 2026-09, 5 bps, or 4 bps). Un challenge démarre à chaque minuit
CET/CEST, soit 1 826 départs. Les contrôles bloquants sont passés et la vérification indépendante concorde (A10).
Annexes générées en fin de document.*

## Verdict

- **La perte totale statique fait presque tous les échecs.** La perte du jour ne fait échouer aucun départ jusqu'à
  0,20 %/ATR, et 0,7 % à 0,25 %/ATR. La perte totale en fait échouer 46,8 % à 0,25 %/ATR. La critique du plan le
  prévoyait.
- **Probabilité contre vitesse** (lecture principale : marge plafonnée, borne pessimiste, perte du jour depuis le solde
  de minuit) :

  | r (%/ATR) | Réussite P1 + P2 [IC 95 %] | Échec, perte totale : P1 ; P2 | En cours à la fin | Délai médian (P90) |
  |---|---|---|---|---|
  | 0,05 | 88,2 % [79,7 ; 95,0] | 0,0 % ; 0,0 % | 11,8 % | 571 j (1 097) |
  | 0,10 | 78,5 % [69,7 ; 86,7] | 9,5 % ; 8,6 % | 3,4 % | 173 j (371) |
  | 0,15 | 60,4 % [49,5 ; 71,4] | 23,3 % ; 14,2 % | 2,2 % | 100 j (230) |
  | 0,20 | 58,8 % [47,9 ; 69,3] | 28,7 % ; 10,8 % | 1,7 % | 68 j (158) |
  | 0,25 | 51,0 % [40,2 ; 61,2] | 33,4 % ; 13,4 % | 1,5 % | 41 j (94) |

- **Le meilleur r dépend de l'horizon visé.** Sur les mêmes 1 462 départs, la part qui réussit P1 + P2 vaut au plus :
  - 38,9 % en 90 jours, à 0,25 ;
  - 52,0 % en 180 jours, à 0,20 ;
  - 67,6 % en un an, à 0,10.
- **Le plafond de marge 1:2 ne détruit pas la stratégie dans cette plage.**
  - Jusqu'à 0,15 %/ATR, au plus 1,6 % des trades sont réduits.
  - À 0,25 %/ATR, 7,5 % des trades sont réduits et 1,0 % sautés, dont 6 et 2 des 48 meilleurs.
  - Effet sur la réussite : de −0,3 à +4,5 points.
- **Le résultat est fragile.**
  - Sans les données de 2026, la réussite perd de 6,5 à 16,8 points dès r = 0,10.
  - Selon l'année de départ, elle va de 56 à 100 % à 0,10.
  - Le « zéro échec » à 0,05 tient à 0,45 point : la pire baisse depuis un minuit atteint −9,55 % (départ du
    2023-07-27).

## 1. Lecture principale

| r (%/ATR) | Réussite P1 | Réussite P1 + P2 [IC 95 %] | Échec P1 : jour ; total | Échec P2 : jour ; total | Délai P1 : méd. ; P90 | Délai P1 + P2 : méd. ; P90 |
|---|---|---|---|---|---|---|
| 0,05 | 93,6 % | 88,2 % [79,7 ; 95,0] | 0,0 % ; 0,0 % | 0,0 % ; 0,0 % | 243 ; 478 j | 571 ; 1 097 j |
| 0,10 | 88,4 % | 78,5 % [69,7 ; 86,7] | 0,0 % ; 9,5 % | 0,0 % ; 8,6 % | 102 ; 295 j | 173 ; 371 j |
| 0,15 | 75,4 % | 60,4 % [49,5 ; 71,4] | 0,0 % ; 23,3 % | 0,0 % ; 14,2 % | 47 ; 168 j | 100 ; 230 j |
| 0,20 | 70,5 % | 58,8 % [47,9 ; 69,3] | 0,0 % ; 28,7 % | 0,0 % ; 10,8 % | 32 ; 100 j | 68 ; 158 j |
| 0,25 | 65,2 % | 51,0 % [40,2 ; 61,2] | 0,7 % ; 33,4 % | 0,0 % ; 13,4 % | 23 ; 62 j | 41 ; 94 j |

- `[OBS]` **La perte du jour ne lie pas.** La pire journée vaut environ 21 × r (D04.2) : le −5 % n'est approché qu'à
  0,25 %/ATR.
  - Avec la référence max(solde, équité) de minuit, plus stricte, on compte 2,4 % d'échecs par la perte du jour à
    0,25 %/ATR, et 0,2 % à 0,20.
  - Le coupe-circuit à −3,5 % prévu par le plan initial (D05.2) viserait donc une règle qui ne fait pas échouer.
- `[OBS]` **Les échecs viennent des longues phases de baisse de RE-1.**
  - Les pires départs datent des semaines qui précèdent les creux : 2023-07-27 (de 0,05 à 0,15), 2023-07-18 (0,20)
    et 2022-07-27 (0,25).
  - Depuis ces départs, la plus forte baisse avant +9 % atteint −9,55 %, −17,91 %, −23,92 %, −29,42 % et −36,59 %
    selon r (A10).
- `[OBS]` **À 0,05 %/ATR, aucun échec, mais lent et sans marge de sécurité.**
  - Délais médians : 243 jours pour P1 et 571 pour P1 + P2.
  - En un an, 13,7 % des départs réussissent les deux phases.
  - 11,8 % des départs sont encore en cours à la fin des données, presque tous partis en 2026.
  - La pire baisse passe à 0,45 point du plancher.
- `[OBS]` **Les intervalles de confiance sont larges** : ±7 à 11 points, par blocs de mois de départ. Les départs se
  chevauchent, et les échecs se groupent en quelques épisodes.

## 2. Probabilité et vitesse à horizon fixé

Mêmes 1 462 départs pour les trois horizons (ceux suivis au moins un an, partis jusqu'au 2025-10-01) :

| r (%/ATR) | ≤ 90 jours | ≤ 180 jours | ≤ 365 jours |
|---|---|---|---|
| 0,05 | 0,0 % | 0,3 % | 13,7 % |
| 0,10 | 3,1 % | 30,8 % | **67,6 %** |
| 0,15 | 18,0 % | 41,8 % | 56,0 % |
| 0,20 | 31,8 % | **52,0 %** | 55,1 % |
| 0,25 | **38,9 %** | 46,4 % | 46,4 % |

- `[OBS]` **Aucun r ne domine.**
  - À 0,25, presque tout se joue en 90 jours : la réussite plafonne à 46,4 %.
  - À 0,10, la réussite monte lentement jusqu'à 67,6 % en un an.
  - 0,15 n'est le meilleur à aucun des trois horizons.
- **Ta règle 70/30 (probabilité/vitesse)** se traduit ici par le choix d'un horizon, ou d'une formule. Je ne fixe ni
  l'un ni l'autre : à toi de trancher.

## 3. Marge (règle du porteur : une entrée qui dépasserait la marge est réduite à la marge restante)

| r (%/ATR) | Sans plafond : états où la marge dépasse l'équité ; maximum | Avec plafond : trades réduits ; sautés | Top 1 % (48 trades) : réduits ; sautés ; taille obtenue | Réussite P1 + P2 : sans ; avec |
|---|---|---|---|---|
| 0,05 | 0,0 % ; 0,77 | 0,0 % ; 0,0 % | 0 ; 0 ; 100 % | 88,2 % ; 88,2 % |
| 0,10 | 0,1 % ; 1,24 | 0,2 % ; 0,0 % | 1 ; 0 ; 99,4 % | 78,3 % ; 78,5 % |
| 0,15 | 1,0 % ; 1,87 | 1,6 % ; 0,1 % | 1 ; 0 ; 98,9 % | 60,2 % ; 60,4 % |
| 0,20 | 2,6 % ; 2,26 | 4,3 % ; 0,4 % | 1 ; 0 ; 98,6 % | 54,3 % ; 58,8 % |
| 0,25 | 4,8 % ; 2,51 | 7,5 % ; 1,0 % | 6 ; 2 ; 92,7 % | 51,3 % ; 51,0 % |

- `[OBS]` **La marge 1:2 ne commence à toucher la queue droite qu'à 0,25 %/ATR**, où 2 des 48 meilleurs trades sont
  sautés.
  - Du 2021-10 au 2026-09, le PnL vaut +538 % avec le plafond, contre +584 % sans.
  - Jusqu'à 0,15, l'effet est négligeable.
  - L'hypothèse de la critique (« la marge touche d'abord les grands gagnants ») n'est donc vérifiée qu'en haut de la
    plage.
- `[OBS]` **À 0,20, le plafond aide un peu** : 58,8 % de réussite contre 54,3 %, et 10,8 % d'échecs en P2 contre
  14,1 %.
  - Il retire de la taille quand l'exposition culmine.
  - Écart non testé : les deux lectures portent sur les mêmes départs.

## 4. Variantes des règles et coupure des données

- `[OBS]` **Les conventions pèsent peu.**
  - Avec la référence max(solde, équité) de minuit, l'écart est d'au plus 0,2 point jusqu'à 0,20.
  - À 0,25 : 50,9 % au lieu de 51,0 %, mais 2,4 % d'échecs par la perte du jour.
  - Juger les pertes au capital valorisé plutôt qu'à la borne pessimiste ajoute au plus 1,2 point.
- `[OBS]` **Sans les données de 2026** (1 553 départs ; événements postérieurs au 2025-12-31 non observés) :
  - réussite : 43,3 % [30,4 ; 56,3], 61,7 % [49,6 ; 73,3], 53,6 % [41,2 ; 66,3], 52,3 % [40,5 ; 64,7] et 44,2 %
    [32,8 ; 55,6], de 0,05 à 0,25 ;
  - délais médians : 886, 203, 118, 78 et 47 jours ;
  - à 0,05, 56,8 % des départs restent en cours.

## 5. Par année de départ (lecture principale)

| r (%/ATR) | 2021 (T4) | 2022 | 2023 | 2024 | 2025 | 2026 (en cours) |
|---|---|---|---|---|---|---|
| 0,05 | 100 % | 100 % | 100 % | 100 % | 100 % | 21,2 % (78,8 %) |
| 0,10 | 100 % | 71,0 % | 55,9 % | 100 % | 82,7 % | 77,3 % (22,7 %) |
| 0,15 | 89,1 % | 65,2 % | 40,0 % | 81,7 % | 28,2 % | 85,7 % (14,3 %) |
| 0,20 | 50,0 % | 60,3 % | 38,6 % | 65,8 % | 53,4 % | 84,6 % (11,0 %) |
| 0,25 | 8,7 % | 57,0 % | 37,0 % | 48,6 % | 49,9 % | 81,0 % (9,9 %) |

- `[OBS]` **Le moment du départ compte autant que r.**
  - À 0,10, les départs de 2023 réussissent à 55,9 % et ceux de 2024 à 100 %.
  - À 0,25, ceux du T4 2021 réussissent à 8,7 % : ils rencontrent le creux de 2022.

## 6. 8 métriques du portefeuille (départ du 2021-10-01, marge plafonnée, 5 bps, or 4 bps)

| r (%/ATR) | PnL : r ; 1x | PF | WR | Espérance ATR ; bps | MDD : r ; 1x | Trades (/mois) | Durée médiane | Part des frais |
|---|---|---|---|---|---|---|---|---|
| 0,05 | +57 % ; +1 115 % | 1,13 | 42,3 % | +0,198 ; +9,9 | −10,7 % ; −66,5 % | 4 744 (79,1) | 26 b ; 13 h | 33 % |
| 0,10 | +138 % ; +1 115 % | 1,13 | 42,3 % | +0,198 ; +9,9 | −19,8 % ; −66,5 % | 4 744 (79,1) | 26 b ; 13 h | 33 % |
| 0,15 | +260 % ; +1 115 % | 1,13 | 42,3 % | +0,201 ; +10,0 | −26,3 % ; −66,5 % | 4 737 (79,0) | 26 b ; 13 h | 33 % |
| 0,20 | +413 % ; +1 115 % | 1,13 | 42,3 % | +0,204 ; +10,1 | −31,3 % ; −66,5 % | 4 723 (78,7) | 26 b ; 13 h | 33 % |
| 0,25 | +538 % ; +1 115 % | 1,12 | 42,3 % | +0,194 ; +9,5 | −36,8 % ; −66,5 % | 4 697 (78,3) | 26 b ; 13 h | 34 % |

- PF, WR, espérance, durée et part des frais sont mesurés sur les trades exécutés (taille > 0), à 1x par trade.
- Sans plafond, on retrouve D04.2 (0,25 %/ATR : +584 %, MDD −37,4 %). À 1x par position, le plafond porte le MDD de
  −81,5 % à −66,5 %.

## 7. Correction de la borne pessimiste

- `[CODE]` **Défaut corrigé dans la barre d'un stop.** `envelope.portfolio_paths` (D04.1, D04.2) laissait la position
  stoppée à sa clôture précédente pendant que les autres positions étaient à leur extrême. Le simulateur cumule la
  perte du stop et ces extrêmes.
- `[OBS]` **Effet de la correction :**
  - 161 à 164 journées UTC changent, sur 1 775 ;
  - l'écart le plus grand tombe le 2023-03-03 : −0,22 point à 0,05 %/ATR, jusqu'à −1,08 point à 0,25 ;
  - la pire journée ne change à aucun r : 2026-01-26, de −1,26 % à −5,90 %. Les chiffres pessimistes de D04.1, D04.2
    et du livre blanc tiennent.

## 8. Lecture

- `[HYP]` **Un challenge FTMO réussit ou échoue selon le moment du départ.** Il dépend de sa position par rapport aux
  longues phases plates ou baissières de RE-1 (2022 ; été 2023 → janvier 2024).
  - L'avantage de RE-1 tient à de rares grands trades (K14, K17). Entre eux, le capital dérive ou baisse, et le
    plancher statique arrive avant l'objectif.
  - Baisser r éloigne le plancher mais allonge l'attente. Monter r raccourcit l'attente mais rapproche le plancher.
- `[HYP]` **Le juge d'un levier.** Un levier (coupe-circuit, taille liée à la distance au plancher, réduction après une
  perte) n'a de valeur que s'il déplace cette frontière au-delà de ce qu'une simple baisse de r obtient.
  - Le coupe-circuit journalier est sans objet ici.
  - La distance au plancher statique est la seule contrainte qui lie.

## 9. Limites

- **Données déjà lues** (D04), 2026 très favorable : la lecture est descriptive.
- **Peu de challenges indépendants** : les départs se chevauchent et les échecs se groupent dans trois ou quatre
  épisodes.
- **Coûts.**
  - Frais de 5 bps, or 4 bps : les écarts et frais de nuit de la firme ne sont pas modélisés.
  - Le glissement des stops n'est pas modélisé ; un glissement moyen d'environ 0,5 ATR annule l'avantage (D03.1).
  - Les prix des CFD de la firme diffèrent de nos flux (Bitstamp, Coinbase, HistData).
- **Conventions.**
  - Tout est clôturé dès l'objectif atteint.
  - P2 démarre au minuit suivant ; le délai d'ouverture du compte par la firme est ignoré.
  - Marge calculée aux prix courants.
  - La liquidation pour marge insuffisante n'est pas modélisée : au plus 1,03 fois l'équité est engagée en marge, donc
    une telle liquidation n'arriverait qu'après une perte bien supérieure à 10 %.
- **Phase financée non mesurée.**
