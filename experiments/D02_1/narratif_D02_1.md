# EXP-D02.1 — Verrou fixe et WFO de H_exit ; WFO de R0 sur grille fine avec inertie ; stress (BTC 2015-2025)

*Demande, cadrage et arbitrages du porteur du 2026-10-03 (`RESEARCH_LOG.md`, entrée EXP-D02.1). Calcul :
`python experiments/D02_1/run_D02_1.py --calcul` (174 s, commit 466d767). BTC/USD Bitstamp, 22 semestres hors échantillon
(S1 2015 → S2 2025), IS de 24 mois, 5 bps (10 bps en stress), 0,25 % du capital par ATR14(t), levier ≤ 1x. Annexes
générées en fin de document.*

## Verdict

- **D02.1a, verrou fixe de 26 barres.** Il répare le WFO-H : +0,227 ATR [+0,090 ; +0,365] face au WFO-H de D02, règle
  « surpasse » de D02 remplie. Il n'ajoute rien à RE-1 gelée : +0,029 ATR [−0,075 ; +0,139], −0,2 bps [−4,9 ; +4,7], même
  MDD. Sur les mêmes 2 075 entrées, l'effet des sorties choisies est nul, avec ou sans la coupure de l'option C.
- **D02.1b, grille fine et inertie.** La candidate (grille 9, inertie) ne fait pas mieux que le WFO-R0 de D02 (−0,038 ATR
  [−0,209 ; +0,130]) et prend plus de risque (MDD −35,7 % contre −15,8 % à 0,25 %/ATR). La grille fine gagne en 2015-2019
  et perd en 2020-2025, surtout en 2022.
- **Le WFO-R0 de D02 tenait à un départage.** En 2018-S2, l'égalité {50 ; 100} a été tranchée vers R0 = 100, le point de
  RE-1. Avec l'inertie (R0 = 50 gardé), 2018 passe de +0,482 à −0,160 ATR et la série retombe au niveau de RE-1
  (−0,065 ATR [−0,155 ; −0,002] face au WFO-R0 de D02).
- **Stress.** À 10 bps, aucune série n'a d'IC > 0. Sans son 1 % de meilleurs trades (21 sur 2 075), RE-1 gelée passe de
  +0,218 à +0,035 ATR [−0,128 ; +0,199] et de +159 % à +9 % à 0,25 %/ATR. Toutes les séries tombent entre −0,17 et
  +0,10 ATR. Les deux stress combinés rendent toutes les séries négatives.
- **Décision proposée au porteur.** Aucune des deux modifications ne surpasse RE-1 gelée (règle de D02). RE-1 gelée reste
  la référence. Le verrou fixe de 26 barres devient la convention, sans effet sur RE-1 (H = 26).

## 1. Contrôle de non-régression (bloquant, passé)

- **Données :** empreinte BTC 2013-2025 conforme à l'audit D02.0, réserve 2026 tronquée, panne de 215 barres retirée,
  22 semestres.
- **Noyau :** les 1 080 trades de RE-1 sur BTC 2020-2025 sont identiques (contrôles de Gate 0 de D02 repassés).
- **D02 reproduit avec le verrou par défaut (verrou = H) :**
  - cartes IS des branches R0 et H identiques au bit près (22 semestres) ;
  - choix identiques à `parametres_D02.csv` ;
  - séries RE-1 gelée (2 075 trades), Contrôle (1 909), WFO-R0 (1 836) et WFO-H (1 847) identiques à
    `trades_D02.csv.gz`.
- **Verrou ≥ H :** à H = 6, 16 et 26 avec un verrou de 26, les séries sont identiques à `envelope.lock_trades` (D01.6).
- **Population constante :** avec un verrou de 26, les 2 075 entrées de RE-1 gelée sont identiques pour les 28 valeurs
  de H.

## 2. Résultats nets, BTC 2015-2025, 5 bps

| Variante | PnL : 0,25 %/ATR ; 1x ; bps (1x) | PF (1x) | WR | Espérance ATR [IC] ; bps | MDD : 0,25 %/ATR ; 1x | Trades (/mois) | Durée médiane | Part des frais (1x) ; brut ; frais (ATR) | Calmar 0,25 %/ATR |
|---|---|---|---|---|---|---|---|---|---|
| RE-1 gelée | +159 % ; +396 % ; +21 149 | 1,15 | 43,9 % | +0,218 [+0,032 ; +0,401] ; +10,2 | −28,4 % ; −53,0 % | 2 075 (15,7) | 26 b ; 13 h | 33 % ; +0,34 ; 0,12 | 0,32 |
| WFO-H_exit verrou 26 | +173 % ; +335 % ; +20 828 | 1,13 | 43,7 % | +0,246 [+0,028 ; +0,467] ; +10,0 | −28,4 % ; −53,0 % | 2 075 (15,7) | 26 b ; 13 h | 33 % ; +0,37 ; 0,12 | 0,34 |
| WFO-H (D02) | −2 % ; −20 % ; +2 260 | 1,02 | 42,4 % | +0,019 [−0,202 ; +0,244] ; +1,2 | −46,0 % ; −69,8 % | 1 847 (14,0) | 26 b ; 13 h | 80 % ; +0,14 ; 0,13 | −0,00 |
| WFO-R0 (D02) | +214 % ; +478 % ; +22 133 | 1,18 | 43,6 % | +0,291 [+0,088 ; +0,499] ; +12,1 | −15,8 % ; −40,6 % | 1 836 (13,9) | 26 b ; 13 h | 29 % ; +0,42 ; 0,13 | 0,69 |
| WFO-R0 grille 9 inertie | +168 % ; +441 % ; +21 790 | 1,18 | 43,3 % | +0,253 [+0,035 ; +0,465] ; +11,7 | −35,7 % ; −56,3 % | 1 859 (14,1) | 26 b ; 13 h | 30 % ; +0,38 ; 0,13 | 0,26 |
| WFO-R0 grille 9 | +192 % ; +443 % ; +21 840 | 1,18 | 43,3 % | +0,273 [+0,060 ; +0,480] ; +11,8 | −29,9 % ; −56,1 % | 1 855 (14,1) | 26 b ; 13 h | 30 % ; +0,40 ; 0,13 | 0,34 |
| WFO-R0 grille 5 inertie | +137 % ; +297 % ; +18 369 | 1,14 | 43,3 % | +0,226 [+0,018 ; +0,436] ; +9,8 | −31,8 % ; −49,4 % | 1 867 (14,1) | 26 b ; 13 h | 34 % ; +0,35 ; 0,13 | 0,26 |
| Contrôle | +114 % ; +221 % ; +16 162 | 1,12 | 43,0 % | +0,194 [+0,000 ; +0,399] ; +8,5 | −27,9 % ; −48,4 % | 1 909 (14,5) | 26 b ; 13 h | 37 % ; +0,32 ; 0,13 | 0,26 |

Médiane par trade de −0,43 à −0,61 ATR pour toutes les séries ; P90 de +4,8 à +5,5 ATR ; décile supérieur de +8,8 à
+10,0 ATR en moyenne (annexe A7).

## 3. D02.1a — WFO de H_exit à entrées constantes

- `[OBS]` **Le verrou fixe supprime l'effet de population.** Les 2 075 entrées sont celles de RE-1 gelée. Face au WFO-H de
  D02 : +0,227 ATR [+0,090 ; +0,365], +8,8 bps [+1,4 ; +16,2], rendement +9,7 points par an [+3,6 ; +16,3], Calmar
  meilleur sur 100 % des chemins réordonnés.
- `[OBS]` **Aucune valeur des sorties.** Effet trade par trade face à RE-1 gelée (mêmes entrées, IC par grappes de mois) :
  - 2015-2025 : +0,029 ATR [−0,075 ; +0,139], −0,2 bps [−4,9 ; +4,7] ; sans la coupure de l'option C : +0,035 ATR
    [−0,071 ; +0,147], −0,1 bps ;
  - 2015-2019 : +0,005 ; 2020-2025 : +0,050 [−0,085 ; +0,183].
  - L'écart positif en ATR et nul en bps vient des trades à ATR faible.
- `[OBS]` **H choisi :** 26 (repli, 5 semestres jusqu'au S1 2017), puis 48, 34, 32, 34, 34, 36, 36, 28, 26, 26, 34, 34,
  38, 36, 34, 34, 34. H moyen 31,9 ; 35 % des trades à H = 26.
- `[OBS]` **La règle du centre décide plus souvent qu'en D02.** 10 semestres sur 22 ont une zone de 23 à 28 cases (7 en
  D02), et le choix tombe alors à 32-38. Le meilleur Calmar IS était ailleurs, et changeant : H = 14-16 de 2018-S2 à
  2019-S2 (+1,59 à +2,95), 40-42 en 2020 et 2024, 22 en 2025.
- `[OBS]` **Option C :** 137 trades (6,6 %) sont clos par l'entrée suivante, 10,1 % de ceux à H > 26.
- `[OBS]` **Profil à H fixe sur les mêmes entrées** (lecture descriptive ex post sur tout 2015-2025, sans choix) :
  - espérance de −0,08 ATR à H = 6, +0,218 à 26 et +0,25 à 30 ;
  - creux à +0,22-0,24 entre 32 et 36, bosse à +0,32-0,34 entre 38 et 44 ;
  - +0,25 à +0,30 de 46 à 60.
  - Choisir H sur ce profil serait un choix en échantillon ; le WFO, lui, ne l'a pas trouvé.

## 4. D02.1b — WFO de R0, grille fine et inertie

- `[OBS]` **R0 choisi** (\* : égalité tranchée par l'inertie quand elle change le choix) :
  - WFO-R0 de D02 : 200 de 2015-S1 à 2017-S1, 50 en 2017-S2 et 2018-S1, 100 ensuite ;
  - grille 5 avec inertie : idem, sauf 2018-S2 = 50\* (12 égalités tranchées par l'inertie, une seule change le choix) ;
  - grille 9 : 200, 200, 200, 300, 300, 25, 25, 75, 150, puis 100, sauf 2021-S2 = 50 et 2022-S2 = 25 ;
  - grille 9 avec inertie : idem, sauf 2022-S1 = 75\*.
  - R0 = 100 tient 15, 14, 11 et 10 semestres respectivement.
- `[OBS]` **Par période** (5 bps ; espérance ATR [IC] ; PnL 0,25 %/ATR (1x) ; MDD 0,25 %/ATR (1x)) :

| Série | 2015-2019 | 2020-2025 |
|---|---|---|
| RE-1 gelée | +0,064 [−0,158 ; +0,308] ; +12 % (+74 %) ; −28,4 % (−53,0 %) | +0,357 [+0,086 ; +0,633] ; +132 % (+184 %) ; −13,5 % (−43,9 %) |
| WFO-H_exit verrou 26 | +0,070 [−0,230 ; +0,385] ; +15 % (+56 %) ; −28,4 % (−53,0 %) | +0,407 [+0,111 ; +0,707] ; +138 % (+179 %) ; −15,8 % (−45,0 %) |
| WFO-R0 (D02) | +0,205 [−0,084 ; +0,488] ; +41 % (+101 %) ; −15,8 % (−40,6 %) | +0,355 [+0,076 ; +0,639] ; +122 % (+188 %) ; −13,8 % (−33,4 %) |
| WFO-R0 grille 9 inertie | +0,304 [−0,016 ; +0,650] ; +67 % (+202 %) ; −15,3 % (−30,1 %) | +0,216 [−0,072 ; +0,504] ; +60 % (+79 %) ; −35,7 % (−56,3 %) |
| WFO-R0 grille 9 | +0,304 [−0,016 ; +0,650] ; +67 % (+202 %) ; −15,3 % (−30,1 %) | +0,249 [−0,035 ; +0,527] ; +74 % (+80 %) ; −29,9 % (−56,1 %) |
| WFO-R0 grille 5 inertie | +0,059 [−0,249 ; +0,362] ; +6 % (+38 %) ; −31,8 % (−49,4 %) | +0,355 [+0,076 ; +0,639] ; +122 % (+188 %) ; −13,8 % (−33,4 %) |

- `[OBS]` **2015-2019 :** la grille fine fait +0,240 ATR [−0,092 ; +0,569] face à RE-1 gelée et +0,099 [−0,175 ; +0,406]
  face au WFO-R0 de D02 (Calmar 0,71 contre 0,08 pour RE-1).
- `[OBS]` **2020-2025 :** elle quitte R0 = 100 en 2021-S2 (50) et en 2022 (75 puis 25). 2022 vaut −0,392 ATR
  (−17,2 %) avec la règle de D02, −0,562 (−24,1 %) avec l'inertie, contre +0,305 (+11,5 %) pour RE-1 gelée. Le MDD de la
  candidate (−35,7 %) date de 2022.
- `[OBS]` **Décomposition sur 2015-2025** (écart en ATR [IC]) :
  - inertie sur grille 5 : −0,065 [−0,155 ; −0,002], venu de 2018-S2 seul (2018 : −0,160 contre +0,482) ;
  - grille 9 face à grille 5 (règle de D02) : −0,019 [−0,186 ; +0,145], MDD −13,8 points ;
  - inertie sur grille 9 : −0,019 [−0,063 ; +0,016].

## 5. Stress et anatomie de la queue droite

Espérance ATR [IC] ; PnL 0,25 %/ATR (1x) ; MDD 0,25 %/ATR (1x), 2015-2025 ; tableaux complets en annexe A4.

| Série | 5 bps | 10 bps | 5 bps sans top 1 % | 10 bps sans top 1 % |
|---|---|---|---|---|
| RE-1 gelée | +0,218 [+0,032 ; +0,401] ; +159 % (+396 %) ; −28,4 % (−53,0 %) | +0,093 [−0,094 ; +0,277] ; +43 % (+76 %) ; −36,3 % (−60,8 %) | +0,035 [−0,128 ; +0,199] ; +9 % (+58 %) ; −35,0 % (−58,6 %) | −0,089 [−0,250 ; +0,075] ; −40 % (−44 %) ; −52,2 % (−66,0 %) |
| WFO-H_exit verrou 26 | +0,246 [+0,028 ; +0,467] ; +173 % (+335 %) ; −28,4 % (−53,0 %) | +0,122 [−0,095 ; +0,344] ; +51 % (+54 %) ; −37,1 % (−60,8 %) | +0,017 [−0,158 ; +0,193] ; +0 % (+21 %) ; −42,3 % (−60,2 %) | −0,106 [−0,282 ; +0,070] ; −44 % (−57 %) ; −54,6 % (−71,6 %) |
| WFO-H (D02) | +0,019 [−0,202 ; +0,244] ; −2 % (−20 %) ; −46,0 % (−69,8 %) | −0,106 [−0,328 ; +0,120] ; −42 % (−68 %) ; −62,0 % (−82,1 %) | −0,166 [−0,367 ; +0,029] ; −53 % (−70 %) ; −63,9 % (−82,5 %) | −0,291 [−0,494 ; −0,095] ; −72 % (−88 %) ; −76,0 % (−91,1 %) |
| WFO-R0 (D02) | +0,291 [+0,088 ; +0,499] ; +214 % (+478 %) ; −15,8 % (−40,6 %) | +0,165 [−0,043 ; +0,373] ; +85 % (+131 %) ; −20,6 % (−46,6 %) | +0,096 [−0,093 ; +0,285] ; +40 % (+95 %) ; −22,2 % (−48,0 %) | −0,030 [−0,218 ; +0,160] ; −17 % (−21 %) ; −33,2 % (−58,0 %) |
| WFO-R0 grille 9 inertie | +0,253 [+0,035 ; +0,465] ; +168 % (+441 %) ; −35,7 % (−56,3 %) | +0,127 [−0,091 ; +0,341] ; +57 % (+114 %) ; −39,5 % (−61,4 %) | +0,021 [−0,162 ; +0,202] ; −0 % (+15 %) ; −37,4 % (−59,4 %) | −0,105 [−0,290 ; +0,077] ; −41 % (−54 %) ; −52,5 % (−70,8 %) |
| WFO-R0 grille 9 | +0,273 [+0,060 ; +0,480] ; +192 % (+443 %) ; −29,9 % (−56,1 %) | +0,146 [−0,071 ; +0,355] ; +72 % (+115 %) ; −33,9 % (−61,1 %) | +0,040 [−0,146 ; +0,218] ; +9 % (+15 %) ; −31,7 % (−59,3 %) | −0,086 [−0,273 ; +0,094] ; −35 % (−54 %) ; −48,2 % (−70,6 %) |
| WFO-R0 grille 5 inertie | +0,226 [+0,018 ; +0,436] ; +137 % (+297 %) ; −31,8 % (−49,4 %) | +0,099 [−0,109 ; +0,308] ; +38 % (+56 %) ; −36,5 % (−53,9 %) | +0,037 [−0,156 ; +0,227] ; +9 % (+39 %) ; −35,6 % (−51,7 %) | −0,089 [−0,284 ; +0,099] ; −37 % (−49 %) ; −49,3 % (−68,0 %) |
| Contrôle | +0,194 [+0,000 ; +0,399] ; +114 % (+221 %) ; −27,9 % (−48,4 %) | +0,066 [−0,128 ; +0,269] ; +23 % (+24 %) ; −35,1 % (−56,6 %) | +0,008 [−0,165 ; +0,184] ; −4 % (+17 %) ; −41,4 % (−56,2 %) | −0,118 [−0,293 ; +0,057] ; −44 % (−54 %) ; −55,6 % (−69,6 %) |

- `[OBS]` **Comparaisons sous stress** (annexe A4) : aucune série ne surpasse RE-1 gelée. Les écarts restent dans un IC
  qui contient 0, sauf celui du WFO-H de D02, négatif sous chaque stress (−0,20 ATR). WFO-H_exit face au WFO-H de D02
  reste tangible sous chaque stress (+0,18 à +0,23 ATR).
- `[OBS]` **Anatomie de la queue de RE-1 gelée** (5 bps) :
  - les 21 meilleurs trades (1 %) font 84 % de la somme nette en ATR (379,5 sur 451,4) et 91 % de la croissance
    log du capital à 0,25 %/ATR ;
  - les 104 meilleurs (5 %) font 266 % du total, les 208 meilleurs (10 %) 409 % : les 90 % restants perdent environ
    trois fois le résultat final ;
  - ces 21 trades sont des mouvements de +196 à +961 bps bruts, ouverts quand l'ATR était bas (32 bps en moyenne,
    contre 57 pour l'ensemble) ; 6 sont plafonnés à 1x et aucun n'est stoppé ;
  - ils sont répartis sur 10 des 11 années : 2 en 2015, 2016, 2017, 2018 et 2025 ; 3 en 2019 ; 5 en 2022 ; 1 en 2021,
    2023 et 2024 ; aucun en 2020.

## 6. Lecture

- `[HYP]` **Les sorties ne portent pas l'avantage.** À entrées constantes, aucun horizon choisi en IS ne bat H = 26 hors
  échantillon. Le recalibrage de H n'a d'effet que par le calendrier des entrées, effet que le verrou fixe neutralise.
  La règle du centre ramène ensuite le choix vers le milieu de la grille (I-M18).
- `[HYP]` **R0 se choisit mal sur 24 mois.** Plus la grille est fine, plus le WFO change de R0, et chaque changement est un
  pari sur un semestre. 2022 montre le coût d'un pari perdu. L'avance du WFO-R0 de D02 tenait à un seul départage vers
  le point de RE-1, construite sur 2020-2025. Ce n'est pas un avantage adaptatif démontré.
- `[HYP]` **RE-1 récolte des expansions de volatilité nées d'états calmes.** Environ deux par an, elles font l'essentiel du
  résultat ; le trade médian perd 0,4 ATR. La robustesse se joue sur la fréquence et la taille de ces expansions, pas
  sur le trade moyen. Les 10 bps et le retrait du 1 % meilleur s'additionnent jusqu'à effacer l'avantage.

## 7. Pistes (à cadrer par le porteur, rien de lancé)

1. **Prop firm :** la série saigne entre deux grands gagnants (MDD −28 % à 0,25 %/ATR sur 2015-2025). Les règles de
   perte journalière et totale de la firme visée fixent la taille par trade : à mesurer avec ces règles, sur RE-1 gelée.
2. **Queue droite :** étudier ce qui précède les 21 grands gagnants (ATR bas, compression, sous-famille, heure),
   description seule, sans apprentissage, pour savoir si la queue se laisse cibler ou seulement attendre.
3. **H_exit fixe plus long :** le profil descriptif bombe entre 38 et 44 barres. Un test propre exigerait de choisir H
   sur une période et de le lire sur une autre (par exemple, choix sur 2015-2019, lecture sur 2020-2025), pas sur ce
   profil.
4. **WFO de R0 :** à mettre de côté sur BTC, ou à réserver au hold-out ; aucune règle testée n'a battu RE-1 gelée.
