# EXP-D03.1 — Viabilité et sécurité de RE-1 : stop catastrophe, glissement des stops, latence (BTC, SOL)

*Demande du porteur du 2026-10-03, avant D04 : le moteur n'est pas rouvert, le but est la survie du capital
(`RESEARCH_LOG.md`, entrée EXP-D03.1). Calcul : `python experiments/D03_1/run_D03_1.py --calcul` (43 s). RE-1 gelée,
5 bps (10 bps en lecture), 0,25 % du capital par ATR14(t) ; BTC/USD Bitstamp 2015-2025, SOL/USD Coinbase 2021-2025.
Annexes générées en fin de document.*

## Verdict

- **Stop catastrophe à 4 ATR : une assurance réelle, au coût inégal selon la période.**
  - Il ne touche que des trades F2b (284 sur BTC, 98 sur SOL ; le SL-B de F3 est toujours plus proche).
  - La pire perte d'un trade passe de −6,2 % à −1,05 % du capital sur BTC, et de −3,3 % à −1,05 % sur SOL.
  - Sur BTC 2015-2025, son coût n'est pas significatif : −0,037 ATR [−0,118 ; +0,040], et le MDD passe de −28,4 % à
    −21,4 %.
  - Il coûte nettement sur la période récente et sur SOL : BTC 2020-2025, −0,121 ATR [−0,237 ; −0,006] et −5,2 points
    de rendement par an ; SOL, −9,9 bps [−20,4 ; −1,2] par trade et un Calmar de 0,34 contre 0,58.
  - Seule la période 2015-2019, la plus faible pour RE-1, en profite (+0,055 ATR, Calmar meilleur sur 91 % des
    chemins).
- **Glissement de 0,5 ATR sur les stops de F3 : le point faible de l'exécution.** 23 % des trades sortent sur stop :
  −0,115 ATR par trade sur BTC et −0,121 sur SOL, soit la moitié de l'espérance. Le Calmar tombe de 0,32 à 0,10 (BTC).
- **Entrée retardée d'une barre (30 min) : sans effet mesurable.** +0,014 ATR [−0,025 ; +0,056] sur BTC, +0,002 sur SOL.
  L'avantage ne tient pas à la vitesse d'exécution.
- **Les trois ensemble :** −0,221 ATR [−0,313 ; −0,137] sur BTC ; l'espérance tombe à −0,003.

## 1. Contrôles bloquants (passés)

- Ceux de D03 : RE-1 gelée BTC = D02 (2 075 trades), SOL = D01 (769), portefeuille d'une jambe = capital du dépôt.
- Un retard nul, un glissement nul et un stop catastrophe à distance infinie redonnent RE-1 gelée trade par trade.

## 2. Stop catastrophe à 4 ATR (5 bps)

| Série | PnL : 0,25 %/ATR ; 1x | Espérance ATR [IC] ; bps | MDD : 0,25 %/ATR ; 1x | Calmar | Pire trade (capital) |
|---|---|---|---|---|---|
| BTC 2015-2025, RE-1 gelée | +159 % ; +396 % | +0,218 [+0,032 ; +0,401] ; +10,2 | −28,4 % ; −53,0 % | 0,32 | −6,2 % |
| BTC 2015-2025, stop 4 ATR | +128 % ; +385 % | +0,180 [+0,012 ; +0,350] ; +9,8 | −21,4 % ; −42,5 % | 0,36 | −1,05 % |
| BTC 2020-2025, RE-1 gelée | +132 % ; +184 % | +0,357 [+0,086 ; +0,633] ; +11,7 | −13,5 % ; −43,9 % | 1,12 | |
| BTC 2020-2025, stop 4 ATR | +75 % ; +100 % | +0,235 [−0,000 ; +0,486] ; +8,3 | −14,8 % ; −39,9 % | 0,66 | |
| SOL 2021-2025, RE-1 gelée | +39 % ; +173 % | +0,190 [−0,079 ; +0,484] ; +19,2 | −13,1 % ; −42,3 % | 0,58 | −3,3 % |
| SOL 2021-2025, stop 4 ATR | +26 % ; +30 % | +0,135 [−0,117 ; +0,415] ; +9,3 | −15,2 % ; −64,6 % | 0,34 | −1,05 % |

- `[OBS]` **Trades coupés :** 13,7 % des trades sur BTC, 12,7 % sur SOL, tous F2b.
  - Ils font −4,13 ATR avec le stop, contre −3,86 sans lui ; 11 % auraient fini positifs (9 % sur SOL).
  - Sur BTC, le stop coupe 1 trade du top 1 % et 7 du top 5 % ; sur SOL, 0 et 1.
- `[OBS]` **Écart apparié par mois, BTC 2015-2025 :** rendement −1,3 point par an [−5,2 ; +2,3] ; MDD meilleur sur
  60 % des chemins réordonnés, Calmar sur 36 %.
- `[OBS]` **À 1x par position,** le stop réduit peu la pire perte, qui vient de trades à ATR élevé (−986 → −960 bps sur
  BTC), et il creuse le MDD de SOL (−42,3 % → −64,6 %).
- `[OBS]` **À 10 bps :** BTC +0,056 contre +0,093 ATR, Calmar 0,07 contre 0,09.

## 3. Glissement des stops et latence (5 bps)

| Série | PnL : 0,25 %/ATR ; 1x | Espérance ATR [IC] ; bps | MDD : 0,25 %/ATR ; 1x | Calmar |
|---|---|---|---|---|
| BTC, glissement de 0,5 ATR (stops de F3) | +45 % ; +39 % | +0,102 [−0,083 ; +0,290] ; +4,2 | −35,4 % ; −61,1 % | 0,10 |
| BTC, entrée retardée d'une barre | +170 % ; +259 % | +0,232 [+0,050 ; +0,412] ; +8,6 | −23,9 % ; −49,4 % | 0,39 |
| BTC, les trois ensemble | −11 % ; −56 % | −0,003 [−0,178 ; +0,169] ; −1,6 | −29,5 % ; −65,5 % | −0,04 |
| SOL, glissement de 0,5 ATR (stops de F3) | +10 % ; +13 % | +0,069 [−0,207 ; +0,369] ; +8,0 | −17,8 % ; −53,8 % | 0,12 |
| SOL, entrée retardée d'une barre | +40 % ; +179 % | +0,192 [−0,091 ; +0,499] ; +19,6 | −15,3 % ; −43,1 % | 0,49 |
| SOL, les trois ensemble | −10 % ; −67 % | −0,039 [−0,314 ; +0,262] ; −7,8 | −32,1 % ; −85,2 % | −0,07 |

- `[OBS]` **Glissement :** 478 trades de F3 stoppés sur 2 075 (23 %) sur BTC, 186 sur 769 sur SOL. Chaque 0,1 ATR de
  glissement sur ces stops coûte environ 0,023 ATR par trade ; l'espérance de BTC s'annulerait vers 0,95 ATR de
  glissement, celle de SOL vers 0,8 ATR.
- `[OBS]` **Latence :** 48 trades sur BTC et 8 sur SOL sortent aussitôt, leur stop étant déjà franchi à l'entrée
  retardée. L'effet est nul sur les deux périodes de BTC (+0,032 ATR en 2015-2019, −0,003 en 2020-2025).

## 4. Lecture

- `[HYP]` **La latence n'est pas un risque.** Une heure de retard (une barre) ne change rien : RE-1 n'exploite pas une
  micro-structure fugace.
- `[HYP]` **L'exécution des stops est le vrai risque.** Un quart des trades sortent sur stop ; la qualité de ces sorties
  (lieu, type d'ordre, liquidité dans les mouvements rapides) pèse plus que tout autre paramètre d'exécution mesuré. Le
  stop catastrophe ajoute 14 % de sorties sur stop, donc autant de sorties exposées au glissement.
- `[HYP]` **Le stop catastrophe est une assurance, pas une amélioration.** Il borne la perte d'un trade à environ 1 %
  du capital. L'historique ne contient pas le scénario qu'il couvre vraiment : un krach de 20 à 30 % pendant une
  position à 1x. Son prix est faible sur 2015-2025 entier, mais élevé sur 2020-2025 et sur SOL.

## 5. Arbitrages (au porteur)

1. **Stop catastrophe :** greffer ou non. Coût non significatif sur BTC 2015-2025, mais −0,121 ATR [−0,237 ; −0,006]
   sur 2020-2025 et −9,9 bps sur SOL. Autre assurance contre la ruine, sans sortie sur stop : un plafond de notionnel
   plus bas que 1x par position, à mesurer si tu le souhaites.
2. **Exécution des stops :** le lieu et le type d'ordre doivent être choisis pour limiter le glissement, mesuré en
   direct avant d'engager du capital.
