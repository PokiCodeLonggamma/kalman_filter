# EXP-D05.1 — Mesure de la grille de profil, sans RE-1 ni coût

*GO du porteur du 2026-10-05, pendant l'attente de l'accord de Spotware. Calcul : `python
experiments/D05_1/run_grille_D05_1.py --calcul` (une minute). Données : `grille_D05_1.csv` et `grille_D05_1.json`.*

*Méthode (`profil.grille`, 13 tests) :*
- *Séries : BTC (Bitstamp) et SOL (Coinbase) en ancres ; or (HistData) en repère TradFi du portefeuille ; US100, US30,
  GER40 et GBPJPY (Saxo, prix vendeur) ; du 2020-01-01 au 2025-12-31, SOL dès le 2021-06-17.*
- *Fenêtres disjointes de 26 barres. z26 = mouvement de l'ouverture de t + 1 à celle de t + 27, en ATR14(t) : l'horizon
  et l'unité de RE-1.*
- *Repère : une marche gaussienne à volatilité constante donne 1,75 fenêtre sur 1 000 à |z26| ≥ 10, et aucune à 15.*
- *Aucun coût, aucun trade, aucun classement : grille de lecture, sans seuil. WTI, Brent et GLE attendent les données
  FTMO.*

## Mise à jour du 2026-10-06 : correction de la saison horaire (§7)

- **Une fois la saison horaire retirée, la queue des indices perd environ deux tiers :** US100 passe de 51 à 17
  fenêtres à 10 ATR ou plus pour 1 000, US30 de 43 à 14. GER40 et l'or en perdent la moitié, GBPJPY 30 %, les cryptos
  12 à 14 %.
- **Corrigée, la queue de BTC (35 ‰) vaut 2,1 à 2,7 fois celle de chaque candidat (13 à 17 ‰).** SOL (20 ‰) reste un
  peu au-dessus des candidats, qui se resserrent entre eux.
- **Les expansions des indices hors heure fixe sont surtout des baisses :** US100, 5,2 hausses pour 11,6 baisses ‰.
- **Correction de méthode :** les fréquences sont désormais des moyennes sur les 26 alignements des fenêtres. Un
  alignement unique déplaçait les comptes rares : BTC à 20 ATR ou plus, 2,2 ou 4,0 par an selon le départ.

## Verdict

- **En ATR de 30 min, toutes les séries ont une queue de 13 h bien plus épaisse qu'une marche gaussienne :** 11 à 28 fois
  plus de fenêtres à 10 ATR ou plus.
  - US100 et US30 en ont autant que BTC par fenêtre (49 et 41 pour 1 000, contre 42).
  - L'or, GER40, SOL et GBPJPY en ont moins (19 à 31).
- **Mais les indices et l'or ont une saison horaire bien plus marquée que BTC.** Leur heure la plus agitée l'est 3,2 à 4,4
  fois plus que la plus calme, contre 1,7 sur BTC. `[HYP]` Une part de leur queue vient de l'ouverture au comptant, qui
  tombe chaque jour à la même heure, rapportée à un ATR mesuré dans le calme de la nuit.
- **Trois axes de la note ne distinguent rien :**
  - la persistance : VR(26) de 0,89 à 0,98 partout, et BTC est le plus bas ;
  - la naissance au calme : 77 à 81 % des grandes fenêtres partent d'un ATR sous sa médiane annuelle, sur chaque série ;
  - la taille du plus gros pas : 30 à 38 % du mouvement des grandes fenêtres, partout.
- **Ce qui distingue vraiment les séries :**
  - le calendrier : 58 à 64 % des fenêtres des indices et de l'or traversent une coupure ; aucune sur les cryptos ;
  - les gaps : de 1 à 2,8 gaps de 4 ATR ou plus par an hors cryptos ;
  - le plafond de 1x : il toucherait 43 à 92 % des barres hors cryptos à r = 0,20 ;
  - le lien avec BTC.
- **GBPJPY et l'or sont les moins liés à BTC :**
  - corrélation des variations quotidiennes absolues : 0,10 et 0,16 ;
  - jours extrêmes communs : 8,5 % et 16 %, pour 5 % attendus si les deux séries étaient indépendantes.
  - Les indices le sont deux fois plus : 0,31 à 0,34, et 17 à 22 %.
- **Le creux du portefeuille de RE-1 (2023-07 → 2024-01) n'a pas manqué d'expansions sur BTC :** 1,6 fois plus de
  fenêtres à 10 ATR ou plus qu'en moyenne. Pendant ce creux, l'or et GBPJPY ont été plus actifs que d'habitude (1,34
  et 1,36 fois), les indices moins (0,65 à 0,91).

## 1. Queue d'expansion sur 13 h (fenêtres disjointes de 26 barres)

| Actif | Fenêtres | \|z26\| ≥ 10 pour 1 000 | ≥ 10 par an | ≥ 15 par an | ≥ 20 par an | Hausses / baisses à 10 ATR ou plus |
|---|---|---|---|---|---|---|
| Repère gaussien | — | 1,75 | ≈ 1 | ≈ 0 | 0 | — |
| BTC | 4 042 | 41,6 | 28,0 | 7,8 | 2,2 | 93 / 75 |
| SOL | 3 056 | 22,9 | 15,4 | 4,0 | 1,1 | 38 / 32 |
| Or | 2 664 | 31,2 | 13,8 | 3,7 | 1,2 | 43 / 40 |
| US100 | 2 680 | 49,3 | 22,0 | 6,2 | 1,8 | 56 / 76 |
| US30 | 2 677 | 41,5 | 18,5 | 6,0 | 2,0 | 44 / 67 |
| GER40 | 2 397 | 28,4 | 11,3 | 1,3 | 0,2 | 22 / 46 |
| GBPJPY | 2 942 | 19,4 | 9,5 | 2,0 | 0,5 | 28 / 29 |

- `[OBS]` Par an, les cryptos ont un avantage de calendrier : 674 fenêtres par an, contre environ 446 sur un marché 24/5.
- `[OBS]` Asymétrie : les indices penchent à la baisse (GER40 : deux fois plus de baisses), BTC à la hausse ; l'or et
  GBPJPY sont symétriques.

## 2. Calendrier, sauts et gaps

| Actif | Saison horaire (TR max / min) | Heures cotées par semaine | Fenêtres coupées | Gaps ≥ 4 ATR par an | Sauts d'une barre ≥ 3 ATR (‰) | Plus gros pas des grandes fenêtres |
|---|---|---|---|---|---|---|
| BTC | 1,7 | 168 | 0 % | 0 | 7,0 | 35 % |
| SOL | 1,5 | 168 | 0,1 % | 0 | 3,2 | 33 % |
| Or | 3,5 | 115 | 59 % | 2,3 | 5,6 | 38 % |
| US100 | 4,4 | 115 | 58 % | 1,0 | 8,5 | 34 % |
| US30 | 4,1 | 114 | 58 % | 1,3 | 7,9 | 37 % |
| GER40 | 3,2 | 100 | 64 % | 2,5 | 5,2 | 34 % |
| GBPJPY | 2,2 | 122 | 11 % | 2,8 | 3,5 | 30 % |

- `[OBS]` GBPJPY ne coupe qu'aux week-ends, mais ses gaps pèsent lourd en ATR : médiane 1,9 ATR, P99 6,9 ATR. Son ATR
  est le plus petit de l'échantillon.

## 3. Échelle, plafond, persistance, indépendance

| Actif | ATR médian, bps [P10 ; P90] | Barres plafonnées à 1x, r = 0,20 ; 0,25 | VR(26) | Efficacité sur 26 barres | Corrélation \|r\| quotidiens avec BTC | Jours extrêmes communs avec BTC | Creux de RE-1 : fenêtres ≥ 10 ATR, rapport à la moyenne |
|---|---|---|---|---|---|---|---|
| BTC | 50,5 [23,9 ; 99,6] | 6 % ; 11 % | 0,89 | 0,16 | — | — | 1,64 |
| SOL | 95,6 [57,0 ; 172,1] | 0 % ; 0 % | 0,91 | 0,17 | 0,57 | 41 % | 1,20 |
| Or | 17,5 [11,8 ; 29,1] | 65 % ; 83 % | 0,98 | 0,18 | 0,16 | 16 % | 1,34 |
| US100 | 22,0 [11,7 ; 44,9] | 43 % ; 59 % | 0,97 | 0,20 | 0,32 | 17 % | 0,91 |
| US30 | 15,5 [8,4 ; 33,3] | 68 % ; 80 % | 0,92 | 0,19 | 0,34 | 19 % | 0,69 |
| GER40 | 18,9 [11,7 ; 38,6] | 55 % ; 70 % | 0,96 | 0,19 | 0,31 | 22 % | 0,65 |
| GBPJPY | 11,3 [7,6 ; 18,6] | 92 % ; 97 % | 0,90 | 0,17 | 0,10 | 8,5 % | 1,36 |

- Jours extrêmes : les 5 % de jours les plus agités de chaque série ; 5 % de jours communs si elles étaient
  indépendantes.

## 4. Ce que la mesure change à la note de profil

- **VR au-dessus de 1 n'est pas un marqueur des marchés de RE-1.** BTC a le VR(26) le plus bas (0,89). `[HYP]`
  L'avantage de RE-1 est conditionnel (la cassure après une compression) ; une persistance inconditionnelle ne le voit
  pas.
- **« Un hiver de RE-1 est un marché sans expansion » n'est pas soutenu.** BTC a eu plus de grandes fenêtres pendant le
  creux qu'en moyenne.
- **« Le change n'a pas de queue d'expansion à 30 min » est trop fort.** GBPJPY a une queue (19 ‰, 11 fois le repère),
  la plus mince de l'échantillon.
- **La naissance au calme, telle que définie, est universelle.** C'est l'effet de la division par ATR14(t) (I-M20) :
  l'axe ne distingue rien sous cette forme.

## 7. Correction de la saison horaire (2026-10-06)

*GO du porteur du 2026-10-06. Calcul : `run_grille_D05_1.py --saison` ; données : `grille_saison_D05_1.csv`.*

*Méthode (`profil.grille`, 4 tests de plus) :*
- *Facteur saisonnier causal de chaque barre : TR moyen de sa demi-heure en heure locale sur les 40 jours précédents,
  rapporté au TR moyen de toutes les barres sur la même période.*
- *Fuseaux fixés avant le calcul : UTC (cryptos), New York (US100, US30, or), Francfort (GER40), Londres (GBPJPY).*
- *z26 corrigé = mouvement de 13 h / (ATR désaisonnalisé de t × racine de la moyenne des facteurs² de la fenêtre).
  Sous une marche à saison pure, il suit la même loi qu'un z26 sans saison.*
- *Contrôle du module : une marche gaussienne dont une barre par jour est six fois plus agitée donne 49 fenêtres à
  10 ATR ou plus pour 1 000 en ATR brut, et 5,7 une fois corrigée.*
- *Toutes les fenêtres glissantes (les 26 alignements) ; « par an » = fréquence × fenêtres disjointes par an.*

| Actif | ≥ 10 ATR pour 1 000 : brut → corrigé | ≥ 15 ATR par an : brut → corrigé | ≥ 20 ATR par an : brut → corrigé | Corrigé : hausses / baisses à 10 ATR ou plus (‰) |
|---|---|---|---|---|
| Repère gaussien | 1,75 | ≈ 0 | 0 | — |
| BTC | 40,2 → 34,7 | 8,1 → 7,0 | 3,0 → 2,2 | 18,7 / 16,0 |
| SOL | 22,1 → 19,5 | 3,7 → 3,1 | 1,0 → 1,0 | 11,9 / 7,7 |
| Or | 30,8 → 15,1 | 3,1 → 1,0 | 0,9 → 0,3 | 7,8 / 7,4 |
| US100 | 51,2 → 16,8 | 5,9 → 1,6 | 1,7 → 0,3 | 5,2 / 11,6 |
| US30 | 43,3 → 13,7 | 5,4 → 1,1 | 1,7 → 0,3 | 4,5 / 9,3 |
| GER40 | 25,7 → 13,0 | 1,7 → 0,8 | 0,4 → 0,1 | 3,5 / 9,5 |
| GBPJPY | 21,7 → 15,2 | 2,0 → 1,3 | 0,5 → 0,4 | 6,8 / 8,4 |

- `[OBS]` **Part retirée par la correction :** US100 67 %, US30 68 %, GER40 49 %, or 51 %, GBPJPY 30 %, SOL 12 %,
  BTC 14 %.
- `[OBS]` **Après correction, BTC garde 2,1 à 2,7 fois la queue de chaque candidat ;** à 15 ATR ou plus, 7,0 par an
  contre 0,8 à 1,6.
- `[HYP]` **La queue brute des indices est surtout l'ouverture au comptant, mesurée contre un ATR de nuit.** Les
  expansions de 13 h hors heure fixe, celles du « phénomène crypto », sont deux à trois fois plus rares sur les
  candidats que sur BTC.
- `[HYP]` **RE-1 mesure en ATR brut.** Sur les indices, la saison se traduit donc surtout en mouvements à heure fixe
  autour de ses stops ; seul le backtest dira ce que RE-1 en tire.
- `[OBS]` **Méthode :** les comptes de §1 sont sur un seul alignement. À 10 ATR pour 1 000, ils restent à 10 % près des
  moyennes sur tous les alignements. Les comptes rares par an (15 et 20 ATR) sont à relire avec le tableau ci-dessus.

## 5. Suite proposée (sur GO)

- **z26 corrigé de la saison horaire :** fait (§7).
- **Données FTMO** (après l'accord de Spotware) : coût et swap en ATR, et WTI, Brent et GLE sur la même grille.
- Puis RE-1 sur les candidats retenus par le porteur, et l'inclusion dans le portefeuille contre les pistes 1 et 2.

## 6. Limites

- **Source Saxo (prix vendeur) pour les candidats, HistData pour l'or :** les séries FTMO peuvent différer (horaires,
  coupures, écarts).
- **Une seule période (2020-2025) ;** BTC 2020-2025 est la période de construction de RE-1.
- **Fenêtres alignées sur la 100e barre :** un autre alignement déplace un peu les comptes. Les fréquences par an
  dépendent des heures de cotation.
- **Mesures inconditionnelles :** elles décrivent le marché, pas ce que RE-1 en tire. Seul le backtest le dira.
