# EXP-D04.2 — Portefeuille complet, un facteur à la fois : composition et levier

*Demande du porteur du 2026-10-04 ; plan validé par le porteur : l'axe levier fait varier le risque par trade, l'axe
composition retire un actif à la fois. Calcul : `python experiments/D04_2/run_D04_2.py --calcul` (83 s). La référence
est le portefeuille de D04.1 : six actifs, 0,25 % du capital par ATR et par trade, au plus 1x par position, fenêtre
2021-10 → 2026-09, frais 5 bps (or 4 bps). Contrôle passé : la référence redonne D04.1. Annexes générées en fin de
document.*

## Verdict

- **Sans XRP (0,25 %/ATR) :**
  - pire journée −5,03 % (2025-11-06) contre −5,20 %, et −4,08 % rapportée au solde réalisé ;
  - 2 journées sous −4 % au lieu de 5 (1 au lieu de 3 sur le solde) ;
  - MDD −35,6 % contre −37,4 % ; PnL +274 % au lieu de +584 % ; Calmar 0,85 contre 1,25.
- **Retirer un actif ne suffit pas à rester au-dessus de −4 % :** au mieux −4,06 % (sans ETH) et −4,07 % (sans SOL).
  L'or est le seul actif qui diversifie : sans lui, la pire journée passe à −5,71 % et le MDD à −41,5 %.
- **Le levier commande la pire journée, presque proportionnellement (environ 21 fois le risque par trade) :**
  - −1,10 %, −2,16 %, −3,19 %, −4,18 %, −5,20 % et −6,32 % pour 0,05, 0,10, 0,15, 0,20, 0,25 et 0,30 % par ATR ;
  - aucune journée sous −4 % jusqu'à 0,15 % par ATR (pire −3,19 % ; borne pessimiste −3,66 %) ;
  - MDD : −10,7 %, −19,8 %, −26,3 %, −32,1 %, −37,4 % et −43,1 %.

## 1. Axe composition (0,25 % par ATR et par trade)

| Portefeuille | Pire journée : valorisé ; solde ; pessimiste | Jours < −4 % : valorisé ; solde | MDD | PnL | Calmar |
|---|---|---|---|---|---|
| Six actifs (référence) | −5,20 % ; −4,16 % ; −5,90 % | 5 ; 3 | −37,4 % | +584 % | 1,25 |
| Sans BTC | −5,14 % ; −4,20 % ; −5,90 % | 3 ; 1 | −34,8 % | +327 % | 0,97 |
| Sans SOL | −4,07 % ; −3,70 % ; −4,18 % | 1 ; 0 | −33,1 % | +408 % | 1,16 |
| Sans AVAX | −5,14 % ; −4,13 % ; −5,90 % | 3 ; 1 | −41,2 % | +290 % | 0,76 |
| Sans or | −5,71 % ; −4,55 % ; −5,90 % | 5 ; 2 | −41,5 % | +498 % | 1,04 |
| Sans ETH | −4,06 % ; −4,12 % ; −4,06 % | 1 ; 1 | −31,8 % | +756 % | 1,69 |
| Sans XRP | −5,03 % ; −4,08 % ; −5,03 % | 2 ; 1 | −35,6 % | +274 % | 0,85 |

- `[OBS]` **Le mécanisme de D04.1 reste le même.** Les pires journées viennent de stops catastrophe touchés ensemble
  sur plusieurs cryptos (2022-11-04, 2025-11-06) ou d'un gain latent rendu (2026-01-26). Tout portefeuille à cinq
  actifs garde au moins quatre cryptos.
- `[OBS]` **Par trade, l'espérance varie peu d'une composition à l'autre :** +0,157 ATR (sans XRP) à +0,255 (sans
  ETH), pour +0,198 avec les six. Le PnL change beaucoup, parce que le capital commun compose les gains de tous les
  actifs.

## 2. Axe levier (six actifs, plafond de 1x par position)

| Risque par trade | Pire journée : valorisé ; solde ; pessimiste | Jours < −3 % ; < −4 % | MDD | PnL | Calmar | Exposition brute max ; P99 |
|---|---|---|---|---|---|---|
| 0,05 %/ATR | −1,10 % ; −0,88 % ; −1,26 % | 0 ; 0 | −10,7 % | +57 % | 0,89 | 1,55 ; 0,85 |
| 0,10 %/ATR | −2,16 % ; −1,75 % ; −2,48 % | 0 ; 0 | −19,8 % | +139 % | 0,96 | 3,10 ; 1,66 |
| 0,15 %/ATR | −3,19 % ; −2,55 % ; −3,66 % | 2 ; 0 | −26,3 % | +248 % | 1,08 | 4,17 ; 2,28 |
| 0,20 %/ATR | −4,18 % ; −3,33 % ; −4,80 % | 7 ; 3 | −32,1 % | +387 % | 1,16 | 4,60 ; 2,74 |
| 0,25 %/ATR (référence) | −5,20 % ; −4,16 % ; −5,90 % | 25 ; 5 | −37,4 % | +584 % | 1,25 | 5,22 ; 3,09 |
| 0,30 %/ATR | −6,32 % ; −4,98 % ; −6,96 % | 60 ; 12 | −43,1 % | +803 % | 1,28 | 5,55 ; 3,41 |

- `[OBS]` **La pire journée suit le risque par trade presque proportionnellement**, à environ 21 fois le risque par
  ATR. Ce sont les mêmes journées qui la font (2022-11-04, 2025-11-06, 2026-01-26).
- `[OBS]` **Le MDD croît moins vite que le risque ; le Calmar monte de 0,89 à 1,28,** effet de la composition des
  gains.
- `[OBS]` **L'exposition brute dépasse régulièrement 1x dès 0,10 %/ATR** (P99 1,66x, maximum 3,1x), car l'or et les
  cryptos calmes prennent de gros notionnels.

## 3. Lecture

- `[HYP]` **Pour une limite journalière de 4 % sur le capital valorisé, c'est la taille qui compte, pas la
  composition.** À 0,15 %/ATR, la pire journée de cinq ans fait −3,19 % (−3,66 % en borne pessimiste). La marge est
  mince et se mesure sur des données déjà vues.
- `[HYP]` **Retenir « sans ETH » serait une sélection après lecture.** Son meilleur Calmar (1,69) et son meilleur PnL
  (+756 %) viennent de ce qu'ETH a perdu sur cette fenêtre (−18 % seul), ce que l'on sait seulement depuis D04.
  Inversement, une bonne part du rendement de XRP tient au trade de juillet 2023.
- `[HYP]` **Si le compte impose aussi une perte totale maximale, c'est elle qui contraint :** le MDD vaut −26,3 % à
  0,15 %/ATR et encore −10,7 % à 0,05 %/ATR.
