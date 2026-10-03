# PROJECT PLAN — AKF-TSO SYSTEMATIC RESEARCH

## Objectif

Comprendre si le signal AKF-TSO peut être transformé en une stratégie de trading simple, robuste et exploitable.

Le projet doit rester volontairement flexible au départ.  
Les phases servent de cadre général, mais les expériences précises seront définies progressivement en fonction des résultats.

---

## FEUILLE DE ROUTE MÉTHODOLOGIQUE (recadrage du 2026-09-27)

Démarche : **mesurer → caractériser → catégoriser → isoler → exploiter** l'information cinématique du moteur, puis déterminer dans quelles conditions elle reste robuste hors échantillon (hypothèse directrice : `RESEARCH_PHILOSOPHY.md` §1). Cette démarche remplace la séquence EXP-001 (stop-and-reverse natif) / EXP-002 (signal contre hasard) proposée en fin d'audit. Aucun test « signal brut contre hasard ».

| Étape | Objet | Phases ci-dessous |
|---|---|---|
| **A — Anatomie** | Distribution naturelle des caractéristiques du signal brut : retard par rapport à l'extremum de prix, mouvement précédent (`prev_seg_len`, saturation de `trend_strength`), innovation (`nis_z_100`), amplitude normalisée (`A_vol`). Strictement descriptive : ni seuil, ni catégorie, ni paramètre optimisé. | 2 |
| **B — Catégorisation** | Familles de signaux (tendance, épuisement calme à faible NIS, panique/breakout à fort NIS, faux retournement en range plat) ; signatures présentant une asymétrie d'excursion favorable. | 2 |
| **C — Enveloppe** | Sortie découplée de l'oscillateur inverse ; Time-Stop borné, Stop-Loss en multiples d'ATR, Break-Even dynamique ; filtre de tendance macro (ex. alignement EMA). Un facteur à la fois. | 3, 4 |
| **D — Adaptation** | Optuna + WFO : stabilité des plateaux dans le temps, transférabilité à d'autres dynamiques (ETF volatil type SOXS, indice). | 5, 6 |

Chaque test est précédé du cadrage obligatoire (`RESEARCH_PHILOSOPHY.md` §4.6).

### Avancement (au 2026-10-01)

| Étape | Expérience | Statut | Résultat principal |
|---|---|---|---|
| A | EXP-A01 | faite | Géométrie du signal stationnaire en ATR14(t) : l'enveloppe s'exprime en ATR. |
| B | EXP-B01 et relecture | faite | Trois régimes : R1 essoufflement, R2 sortie de range, R3 continuation. |
| C | EXP-C01 et relecture | faite | Sortie à horizon fixe ; R3 et `nis_z_100` Q4 exclus ; F2b · x1 hors Q4 à H26 candidat principal. |
| C | EXP-C02 et relecture | faite | Stop différencié : F2b sans stop, F3 stop à l'extremum du segment ; R1 sans espérance nette. |
| C | EXP-C02bis et relecture | faite | Moteur de régimes (vetos : x1 non retourné, R3, `nis_z_100` Q4). RE-1 validé par le porteur comme référence de l'Étape C : F2b sans stop, F3 stop à l'extremum, cooldown, H = 26 commun et verrouillé. Même espérance que R2 uniforme, drawdown −20 % → −13 %, plateau H20-32. |
| C | EXP-C03 et analyse approfondie | faite | Break-even différé sur RE-1 (F3, F2b ou les deux ; seuil de 1 à 4 ATR). Aucun alpha. Comme outil de risque, il équivaut à réduire la taille et ne résiste pas à 5 bps de glissement. RE-1 conservé intact. Take-profit fixe exclu : même sa borne optimiste reste sous RE-1. |
| C | EXP-C04 | faite | Filtre de tendance macro (EMA 200, EMA 50, Kalman v2.1 sur 4 h), en veto des signaux contre-tendance. Rejeté : les trades contre-tendance ne sont pas toxiques et portent les grands retournements. RE-1 reste pur : c'est la stratégie cœur. Étapes annoncées par le porteur : C05 (sensibilité), puis D (portabilité multi-actifs). |
| C | EXP-C05 | faite | Sensibilité des trois seuils de RE-1, un à la fois. Plateaux pour la frontière F2b / F3 (0,85 à 0,95) et la marge du stop de F3 (−0,25 à +0,25 ATR). L'exclusion de `nis_z_100` est une falaise côté permissif, signalée avant l'Étape D. RE-1 inchangé. |
| D | EXP-D01 et D01 bis | faite | Portabilité de RE-1 figée, seuils BTC gelés, descriptive. La géométrie des signaux se transpose. SOL/USD : +0,190 ATR [−0,079 ; +0,484], MDD −13,1 %. CFD or : net nul, le brut de +0,24 ATR étant absorbé par 0,26 ATR de frais. ETF SPY et XLE (séance régulière) : brut 0,00 et +0,10 ATR, environ 2 trades par mois ; le filtre nis écarte 64 à 74 % des signaux nés d'un gap, mais les trades traversent deux nuits (gaps = 35 à 47 % de leur amplitude). WTI retiré par le porteur, remplacé par XLE. RE-1 inchangée. |
| D | EXP-D01.5 | faite | Sensibilité de RE-1 à H seul, descriptive (or H 26-130 ; SPY et XLE H 6-130 ; 4 bps). Aucun IC à borne basse > 0 sur 15 configurations. Or : frais fixes en ATR (0,26), brut non croissant, H = 26 meilleur point. SPY : H = 13 traverse encore une nuit (91 %), H = 6 réduit les nuits sans brut à protéger. XLE : pic à H = 65 porté par la population (effet apparié ≈ 0). RE-1 inchangée. |
| D | EXP-D01.7 | terminée (descriptive) | Portabilité zero-shot, séries Saxo (futures continus abandonnés, raccords non ajustés) ; univers du porteur : US100, US30, GER40, EU50, HK50, XAGUSD, GBPJPY et 5 CFD sur ETF. Aucun IC > 0 au coût principal ; brut de +0,06 à +0,42 ATR, absorbé par des frais de 0,24 à 0,42 ATR hors ETF ; US30 brut symétrique (+7,9 bps [+0,8 ; +16,0]), +0,211 ATR à l'écart réel ; ETF : brut venu des nuits, ~140 trades. GBPJPY Saxo confirme la partie 1. RE-1 inchangée. D02 à cadrer par le porteur. |
| D | EXP-D01.6 | faite | Exploration sur SPY et XLE, descriptive. Les 31 trades de XLE sautés à H = 65 valent +0,118 ATR avec la sortie de RE-1 (−0,48 seulement tenus 65 barres) ; aucune signature à t hors leur délai depuis le trade précédent, rien ne se réplique sur SPY. Verrouillage distinct de la sortie (26 à 90) : zigzag, aucun IC > 0. Sortie de fin de séance : aucun IC > 0 ; brut en séance +0,16 ATR sur SPY (≈ frais), −0,09 sur XLE ; la nuit aide XLE et pèse sur SPY. RE-1 inchangée. |
| D | **Clôture de D01** | décision du porteur (2026-10-01) | D01 est close : SOL et l'or jugés assez encourageants pour poursuivre ; D01 a dégagé les limites de RE-1 en zero-shot et les axes d'adaptation (réactivité R0, horizon H, transfert des seuils, coût d'exécution, horizon en temps sur les séances). |
| D | EXP-D02.0 | faite (descriptive) | Rétro-test de RE-1 figée sur des périodes jamais vues, préalable de D02. BTC/USD 2013-2019 : −0,045 ATR [−0,244 ; +0,157] à 5 bps (brut +0,06 contre +0,50 en 2020-2025 ; 2014-2015 portent l'écart) ; or 2009-2019 : +0,011 (brut +0,30 absorbé par 0,29 ATR de frais). Panne de Bitstamp de 2015 sans effet. RE-1 inchangée. Univers de D02 : AVAX ajouté par le porteur. |
| D | EXP-D02 | faite (2026-10-01) ; décision du porteur le 2026-10-02 : RE-1 gelée gardée, WFO-R0 à creuser, multi-actif mis de côté | Walk-forward par actif (BTC 2013-2025, SOL, AVAX, or 2009-2025) de H (6 à 60), R0 (10 à 500) et de la frontière F2b/F3 (0,75 à 0,95), en OFAT puis conjointement (700 combinaisons par IS, 42 000 évaluations). IS de 24 mois, OOS de 6 mois, seuils réestimés sur chaque IS, choix au centre de la plus grande zone connexe à Calmar > 0 ; noyau Numba identique à RE-1 au bit près (Gate 0). Aucune variante ne surpasse RE-1 gelée, aucun WFO n'est retenu face à son Statique ; le recalibrage dégrade plus souvent qu'il n'améliore (8 écarts significativement négatifs, 1 positif sur 92). Meilleure série : BTC WFO-R0, +0,291 ATR [+0,088 ; +0,499], MDD −15,8 %, mais +0,074 non significatif face à RE-1 gelée (gain venu de 2015 et 2018). Sur BTC, chaque calibration vaut pour son époque (K13). RE-1 inchangée. |
| D | EXP-D02.1 | faite (2026-10-03) ; décision du porteur : WFO abandonné définitivement, RE-1 gelée version finale du moteur | BTC 2015-2025. Verrou (cooldown) fixé à 26 barres pour tous les tests (décision du porteur) et WFO de H_exit à entrées constantes (option C : l'entrée suivante clôt la position) ; WFO de R0 sur la grille {10, 25, 50, 75, 100, 150, 200, 300, 500} avec inertie ; stress du porteur (10 bps, retrait du 1 % meilleur, les deux) sur toutes les séries. Aucune des deux modifications ne surpasse RE-1 gelée. Le verrou répare le WFO-H (+0,227 ATR face à celui de D02), sans effet des sorties (+0,029 [−0,075 ; +0,139] face à RE-1 gelée). La grille fine gagne en 2015-2019, perd en 2020-2025 (MDD −35,7 %) ; l'avance du WFO-R0 de D02 tenait au départage de 2018-S2 vers R0 = 100 (I-M19). Sans le 1 % meilleur, toutes les séries tombent entre −0,17 et +0,10 ATR (K14). RE-1 inchangée. |
| D | EXP-D03 | faite (2026-10-03) ; suite à décider par le porteur | Exploitation en fonds propres. Profil à t des 5 % meilleurs trades de RE-1 gelée (BTC 2015-2025) : le « calme » tient au classement en ATR et à la taille de position (en bps, les plus gros gains naissent à ATR haut, I-M20) ; ni la compression, ni %B, ni l'EMA 200 ne séparent les groupes. Filtre ATR ≤ P60 glissant : garde le top 1 %, Calmar 0,34 contre 0,32, gain limité à 2020-2025, absent sur SOL (non retenu, proposition). Portefeuille BTC + SOL 2021-2025 : corrélation mensuelle −0,04, Calmar 1,58 contre 1,18 pour BTC seul, MDD −15,2 % (K15) ; avantage de SOL non établi à 95 %. RE-1 inchangée. |

**Direction de l'Étape D (porteur, 2026-09-29).** RE-1 est fonctionnelle, relativement performante sans optimisation, et figée.
- **D01, portabilité multi-actifs sans optimisation :** RE-1 figée sur d'autres actifs. Si elle tient, cela valide la stratégie elle-même.
- **D02, optimisation (Optuna, walk-forward) :** mesure le gain de performance dû à l'optimisation, contre RE-1 figée.
- Ensuite, la validation finale sur le hold-out (phase 7).

La reprise se fait avec `passation.md` (réécrit le 2026-10-01 pour la transition D01 → D02), qui donne l'état complet du projet.

**Conventions de l'Étape C (décisions du porteur) :**
- une position à la fois ;
- frais de 5 et 10 bps ;
- capital à 0,25 % par ATR14(t), notionnel 1x en référence ;
- IC par grappes mensuelles, en bps et en ATR ;
- hold-out scellé jusqu'à la fin de l'Étape D.

Les meilleurs résultats de chaque étape sont regroupés dans `BEST_RESULTS.md`.

---

## PHASE 1 — AUDIT DE L'EXISTANT (« Phase 0 » dans les échanges — close le 2026-09-27)

Avant de recommencer :

- comprendre les travaux déjà réalisés ;
- identifier ce qui fonctionne déjà ;
- récupérer les composants réutilisables ;
- comprendre les expériences déjà réalisées et leurs conclusions ;
- identifier les pistes déjà abandonnées.

Les anciens travaux sont des sources d'information, pas des vérités absolues.

Aucun ancien travail ne doit être modifié ou supprimé.

---

## PHASE 2 — STRATÉGIE DE BASE

Construire un point de départ simple autour du signal AKF-TSO.

Commencer par reproduire fidèlement son fonctionnement et mesurer son comportement avec une mécanique de trading minimale.

Tester plusieurs actifs afin de comprendre comment le signal se comporte selon les marchés.

Objectif : obtenir un premier état des lieux simple et concret.

---

## PHASE 3 — CONSTRUCTION DE LA STRATÉGIE

Chercher progressivement une mécanique simple autour du signal :

- entrée ;
- sortie ;
- stop ;
- time-stop ;
- take-profit ;
- break-even ;
- éventuellement d'autres règles pertinentes.

Tester les idées simplement, une par une au départ, afin de comprendre leur intérêt.

L'objectif n'est pas de multiplier les règles mais de trouver une mécanique cohérente avec le comportement du signal.

---

## PHASE 4 — SENSIBILITÉ

Une fois une première mécanique intéressante identifiée, étudier sa sensibilité aux paramètres.

Objectif :

- comprendre quels paramètres comptent réellement ;
- repérer les réglages fragiles ;
- identifier les zones relativement stables.

Cette phase doit rester simple et exploratoire.

---

## PHASE 5 — OPTIMISATION & WALK-FORWARD

Lorsque la mécanique est suffisamment comprise, utiliser **Optuna** pour rechercher de bonnes configurations de paramètres.

L'optimisation sera ensuite intégrée dans un **Walk-Forward Optimization** afin de tester si les paramètres peuvent être recalibrés dans le temps et conserver leur intérêt hors échantillon.

Comparer notamment :

- paramètres fixes ;
- paramètres optimisés ;
- paramètres recalibrés par WFO.

L'objectif n'est pas de trouver le meilleur backtest historique, mais de déterminer si l'optimisation et le recalibrage apportent réellement quelque chose.

---

## PHASE 6 — TRANSFERT INTER-ACTIFS

Tester si la mécanique développée fonctionne également sur d'autres marchés.

Point de départ :

- BTC ;
- SOL ;
- SOXS ;
- WTI.

L'objectif est de déterminer ce qui semble propre à un actif et ce qui semble plus général.

---

## PHASE 7 — VALIDATION FINALE

Conserver certains actifs hors de la recherche pour une validation finale.

Actifs envisagés :

- ETH ;
- XRP.

Lorsque la stratégie est suffisamment stabilisée, l'appliquer sur ces données sans nouvelle optimisation spécifique.

Objectif : obtenir une dernière observation hors échantillon.

---

# PRINCIPES GÉNÉRAUX

- KISS.
- Comprendre avant de complexifier.
- Tester peu de choses mais en tirer des enseignements.
- Ne pas multiplier les règles ou les modèles sans raison.
- Les résultats doivent guider la suite du projet.
- Les métriques principales restent simples : PnL, trades, Win Rate, Profit Factor, espérance, Max Drawdown, coûts, etc.
- Les papers et travaux historiques servent de sources d'idées, pas de protocole obligatoire.
- Le projet doit pouvoir changer de direction si les premières expériences montrent qu'une autre approche est plus pertinente.

> Chaque nouvelle étape doit répondre à une question simple :
> **« Qu'est-ce qu'on cherche à comprendre maintenant ? »**
