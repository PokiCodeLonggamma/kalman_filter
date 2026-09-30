# EXP-D01.6 — Verrouillage et séance : les deux mécaniques de D01.5 sur SPY et XLE

- **Date :** 2026-09-30. **Étape :** D, exploration avant D02 (décision du porteur). **Descriptive** : RE-1 inchangée, aucun filtre ni paramètre retenu, D02 non lancé.
- **Données :** celles de D01 (ETF SPY et XLE, Alpaca, séance régulière 2020-2025), empreintes inchangées. **Frais :** 4 bps.
- **Code :**
  - `src/envelope/decouple.py` (nouveau, 9 tests) : `lock_trades` (verrouillage distinct de l'horizon de sortie) et `session_close_trades` (sortie forcée au close de la dernière barre de séance) ;
  - `experiments/D01_6/run_D01_6.py`.
  - Aucun fichier de RE-1 modifié. Contrôles : verrouillage 26 = RE-1 trade par trade ; verrouillage 65 = population de la course à H = 65 de D01.5 ; aucune position de séance ne traverse une nuit.

## 0. Cadrage

- **QUESTION :**
  1. Les 31 trades de RE-1 sur XLE que la course à H = 65 saute ont-ils une signature mesurable à t ?
  2. Un verrouillage plus long que la sortie (H_exit = 26, H_cooldown ∈ {26, 48, 65, 90}) donne-t-il une espérance nette robuste ?
  3. Le signal a-t-il une valeur en séance seule, sans nuit détenue ?
- **PERTINENCE POUR LE FILTRE AKF :** dans RE-1, H fixe à la fois la sortie et le verrouillage. Les gaps sont des innovations d'une barre pour le filtre : sortir avant la nuit isole la cinématique en séance.
- **CE QUE LE PROTOCOLE MESURE RÉELLEMENT :** le profil à t des trades sautés contre les trades gardés (XLE, réplication sur SPY) et leur valeur à 26 et à 65 barres ; les 8 métriques à chaque verrouillage ; la sortie de fin de séance sur les entrées de RE-1 (effet apparié) et en stratégie de séance autonome.
- **CE QU'IL NE PERMET PAS DE CONCLURE :** aucun filtre n'est retenu (un seuil lu sur 31 trades serait ajusté à l'échantillon) ; pas de hold-out ; clôture exécutée au close de la dernière barre continue, pas au prix de l'enchère.

## 1. Règle de lecture (fixée avant le calcul du profil et des variantes)

- **Signature :** une variable dont l'AUC (probabilité qu'un trade sauté dépasse un trade gardé) a un IC 95 % qui exclut 0,5 sur XLE, avec le même sens sur SPY. Elle n'a d'intérêt pour RE-1 que si les trades sautés perdent avec la sortie de RE-1 (26 barres).
- **Avantage :** borne basse de l'IC 95 % par grappes mensuelles > 0, en ATR et en bps.
- Une mesure a précédé la fixation de cette règle : la valeur à 26 barres des 31 trades (+0,118 ATR), calculée pour vérifier la prémisse.

## 2. Résultats [OBS]

### 2.1 Action 1 : les 31 trades « toxiques » ne le sont qu'à 65 barres

| XLE | n | Net à la sortie de RE-1 (26 barres) [IC] | Médiane | Sans ses 3 meilleurs | Net à 65 barres [IC] |
|---|---|---|---|---|---|
| Sautés à H = 65 | 31 | **+0,118** [−1,16 ; +1,46] | −0,966 | −0,552 | −0,483 [−2,62 ; +1,59] |
| Gardés | 105 | −0,010 [−0,66 ; +0,68] | −0,403 | −0,303 | +0,155 [−0,79 ; +1,13] |

- **Avec la sortie de RE-1, les 31 trades valent +0,118 ATR en moyenne.** Ils ne perdent (−0,48) que tenus 65 barres. La plupart perdent (médiane −0,97, 42 % de gagnants), mais 3 gros gagnants portent la moyenne.
- **Le seul trait qui les distingue à t est leur définition :** ils arrivent 27 à 64 barres après le trade précédent, contre 154 en médiane pour les gardés (AUC 0,06 [0,02 ; 0,10]).
- **Aucune des variables demandées ne les sépare :**
  - `nis_z_100` 0,45 [0,34 ; 0,56] ; `retrace_ratio` 0,45 [0,34 ; 0,57] ; `leg_atr` 0,49 [0,38 ; 0,60] ;
  - sens 0,57 [0,48 ; 0,65] (77 % de Long contre 64 %) ; F3 0,47 ; même sens que le trade précédent 0,55 [0,45 ; 0,64] ; résultat du trade précédent 0,45 [0,34 ; 0,57] ;
  - heure et tercile d'ATR : écarts de parts sans régularité (14:00-15:00 : 48 % contre 32 %).
- **Rien ne se réplique sur SPY** (42 sautés contre 113 gardés).
  - Les tendances de XLE s'y inversent : Long 60 % contre 64 %, même sens 48 % contre 57 %, 14:00-15:00 21 % contre 36 %.
  - Deux AUC y frôlent la borne : `leg_atr` 0,60 [0,499 ; 0,70] et résultat du trade précédent 0,60 [0,499 ; 0,70], contre 0,49 et 0,45 sur XLE.
  - Sur SPY, les sautés valent −0,216 à 26 barres et les gardés −0,137. C'est la tenue longue qui dégrade les gardés : −0,137 → −0,813, soit −0,68 ATR, contre −0,23 pour les sautés.

### 2.2 Action 2 : le verrouillage seul ne crée pas d'espérance

| H_exit = 26 | H_cooldown 26 (RE-1) | 48 | 65 | 90 |
|---|---|---|---|---|
| XLE, net ATR [IC] | +0,020 [−0,59 ; +0,67] | −0,130 [−0,83 ; +0,56] | −0,010 [−0,66 ; +0,68] | +0,123 [−0,64 ; +1,00] |
| XLE, trades retirés : n ; net (26) | — | 26 ; +0,871 | 31 ; +0,118 | 44 ; −0,169 |
| SPY, net ATR [IC] | −0,158 [−0,74 ; +0,43] | −0,017 [−0,64 ; +0,62] | −0,151 [−0,83 ; +0,58] | −0,313 [−1,01 ; +0,43] |
| SPY, trades retirés : n ; net (26) | — | 24 ; −0,752 | 42 ; −0,216 | 52 ; +0,249 |

- **Aucun IC à borne basse > 0. La courbe zigzague sur les deux ETF.**
- Chaque verrouillage retire un paquet différent de trades, dont la valeur à 26 barres va de −0,75 à +0,87 ATR selon L. C'est un tirage de calendrier, sans tendance.
- **XLE, verrouillage 65 avec sortie à 26 : −0,010, et non +0,155.** Le chiffre de D01.5 demandait aussi la sortie à 65 barres pour les 105 trades gardés (−0,010 → +0,155).
- Le verrouillage réduit le MDD de XLE à 65 (−14,3 % contre −19,5 % à 0,25 %/ATR) et celui de SPY à 1x (−13,5 % contre −19,2 %), sans IC positif.

### 2.3 Action 3 : en séance seule, pas d'espérance nette ; la nuit joue en sens opposé sur les deux ETF

| 4 bps | Net ATR [IC] | Brut ATR [IC] ; frais | PnL 0,25 %/ATR ; 1x | MDD 0,25 %/ATR ; 1x | Trades | Durée médiane |
|---|---|---|---|---|---|---|
| XLE · RE-1 (nuits détenues) | +0,020 [−0,59 ; +0,67] | +0,100 ; 0,081 | +0 % ; +7 % | −19,5 % ; −36,4 % | 136 | 48 h |
| XLE · séance, entrées de RE-1 | −0,170 [−0,44 ; +0,11] | −0,089 [−0,36 ; +0,19] ; 0,081 | −6 % ; −6 % | −10,2 % ; −19,1 % | 136 | 2 h |
| XLE · séance, libérée à la clôture | −0,162 [−0,42 ; +0,10] | −0,082 [−0,34 ; +0,17] ; 0,081 | −6 % ; −6 % | −10,8 % ; −19,8 % | 155 | 2 h |
| SPY · RE-1 (nuits détenues) | −0,158 [−0,74 ; +0,43] | +0,004 ; 0,162 | −4 % ; −8 % | −10,9 % ; −19,2 % | 155 | 48 h |
| SPY · séance, entrées de RE-1 | −0,036 [−0,29 ; +0,23] | +0,127 [−0,12 ; +0,39] ; 0,162 | −1 % ; +4 % | −5,1 % ; −7,8 % | 155 | 3 h |
| SPY · séance, libérée à la clôture | −0,008 [−0,25 ; +0,23] | +0,157 [−0,08 ; +0,39] ; 0,164 | +0 % ; +5 % | −7,0 % ; −9,4 % | 182 | 2,5 h |

- **Aucune variante de séance n'a d'IC positif.**
- **SPY :** en séance, le brut est légèrement positif (+0,13 à +0,16 ATR, IC ∋ 0), contre +0,004 pour RE-1. Les frais (0,16 ATR) l'absorbent : net −0,04 et −0,01.
- **XLE :** le brut en séance est négatif (−0,09 ATR). La part positive de RE-1 venait de la nuit.
- **Effet apparié de la sortie de fin de séance** (mêmes entrées que RE-1) : SPY +0,122 [−0,45 ; +0,68], XLE −0,190 [−0,87 ; +0,44]. Nuits et séances suivantes pèsent −0,12 ATR sur SPY et apportent +0,19 sur XLE : effets opposés, tous deux dans le bruit.
- **Le risque baisse fortement en séance.** MDD divisé par deux environ (SPY −5,1 % contre −10,9 % ; XLE −10,2 % contre −19,5 %), et des IC deux fois plus étroits.

## 3. Lecture [HYP]

1. **Il n'y a pas de répliques toxiques à filtrer dans RE-1.**
   - Les 31 trades sautés ne se distinguent à t que par leur délai depuis le trade précédent, et ils gagnent en moyenne avec la sortie de RE-1.
   - Leur perte à 65 barres dit seulement qu'un trade tardif dans un mouvement ne gagne pas à être tenu une semaine sur XLE. SPY montre l'inverse.
2. **Le verrouillage est un sélecteur de calendrier, pas un levier.** Chaque valeur de L retire un paquet de trades différent, et aucun ordre ne se dégage. Si D02 optimise H sur la course séquentielle, il pourra trouver ce genre de pic par hasard ; ajouter H_cooldown comme paramètre multiplierait ces occasions.
3. **Le signal n'a pas de valeur nette en séance sur les ETF à 4 bps.**
   - Sur SPY, le brut en séance (+0,16 ATR) est du même ordre que les frais : le point mort est vers 4 bps.
   - Sur XLE, il est négatif.
   - L'idée d'une « prime overnight » captée par le moteur ne se généralise pas : la nuit aide XLE et pèse sur SPY.

## 4. Écarts au prompt

- « Sur les entrées figées, l'effet n'est que de +0,009 ATR » : +0,009 est l'espérance nette à 65 barres sur les entrées figées. L'effet apparié contre H = 26 est de −0,010 [−0,71 ; +0,75].
- « 31 trades toxiques (qui valaient −0,48 ATR) » : −0,48 à 65 barres. À la sortie de RE-1 (26 barres), ils valent +0,118 ATR.
- « Tout le brut positif vient des gaps », « le signal perd jusqu'à la clôture » : vrai pour XLE, dans le bruit. Sur SPY, la composante des gaps de RE-1 est ≈ 0 (+0,03), et le brut en séance est de +0,13 ATR jusqu'à la clôture.
