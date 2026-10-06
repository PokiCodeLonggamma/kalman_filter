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
| D | EXP-D03 | faite (2026-10-03) ; décision du porteur : aucun filtre, exploitation en portefeuille multi-actifs | Exploitation en fonds propres. Profil à t des 5 % meilleurs trades de RE-1 gelée (BTC 2015-2025) : le « calme » tient au classement en ATR et à la taille de position (en bps, les plus gros gains naissent à ATR haut, I-M20) ; ni la compression, ni %B, ni l'EMA 200 ne séparent les groupes. Filtre ATR ≤ P60 glissant : garde le top 1 %, Calmar 0,34 contre 0,32, gain limité à 2020-2025, absent sur SOL (non retenu, proposition). Portefeuille BTC + SOL 2021-2025 : corrélation mensuelle −0,04, Calmar 1,58 contre 1,18 pour BTC seul, MDD −15,2 % (K15) ; avantage de SOL non établi à 95 %. RE-1 inchangée. |
| D | EXP-D03.1 | faite (2026-10-03) ; décision du porteur : stop catastrophe greffé, version finale de RE-1 | RE-1 version finale absolue (décision du porteur), lectures de viabilité sur BTC 2015-2025 et SOL : stop catastrophe de 4 ATR (pire perte d'un trade −6,2 % → −1,05 % du capital ; coût −0,037 ATR non significatif sur 2015-2025, −0,121 [−0,237 ; −0,006] sur 2020-2025, −9,9 bps sur SOL) ; glissement de 0,5 ATR sur les stops de F3 (−0,115 ATR par trade) ; entrée retardée d'une barre (sans effet). K16. Ensuite : protocole de D04 à consigner, puis téléchargements et levée des verrous. |
| 7 | EXP-D04 | faite (2026-10-03) ; règle du porteur : condition 1 remplie, survie à 2026 à juger par le porteur | Épreuve de la réserve, protocole pré-enregistré (4c549ba). Version finale de RE-1 (stop catastrophe de 4 ATR). Test A, 5 bps : ETH +0,183 ATR [−0,010 ; +0,385], MDD −39,1 % ; XRP +0,263 [−0,014 ; +0,640], MDD −20,9 %. Test B, 2026 : BTC +0,705, SOL +0,410, AVAX +1,059, or +0,987 ATR ; MDD −3,1 à −6,9 % ; pire journée −1,1 à −1,8 % ; pire trade −1,04 %. Sans le 1 % meilleur, ETH et XRP ≈ −0,06 ATR ; un trade de XRP (SEC contre Ripple, juillet 2023) = 56 % de la somme. K17. |
| 7 | EXP-D04.1 | faite (2026-10-04) | Pire journée du portefeuille complet (six actifs, capital commun, 0,25 %/ATR par trade) : −5,20 % sur le capital valorisé de minuit, −4,16 % sur le solde réalisé, −5,90 % en borne pessimiste ; 5 journées sous −4 % en cinq ans ; actif seul au pire −2,57 %. Cause : stops catastrophe touchés ensemble sur des cryptos corrélées. Portefeuille 2021-10 → 2026-09 : +584 %, MDD −37,4 %, Calmar 1,25, exposition jusqu'à 5,2x. K18. |
| 7 | EXP-D04.2 | faite (2026-10-04) | Portefeuille en OFAT (fenêtre 2021-10 → 2026-09). Composition à 0,25 %/ATR : sans XRP pire journée −5,03 %, PnL +274 %, MDD −35,6 % ; aucun retrait d'actif ne passe au-dessus de −4 % (au mieux −4,06 %) ; sans or −5,71 %. Levier : pire journée ≈ 21 × risque par trade, −3,19 % à 0,15 %/ATR (aucune journée sous −4 %), MDD −26,3 % ; −10,7 % à 0,05 %/ATR. |
| 7 | Livre blanc « Fonds propres » | fait (2026-10-05) ; décision du porteur : branche « Fonds propres » close, cycle Prop Firm à ouvrir | `RE1_FONDS_PROPRES_LIVRE_BLANC.md`, cahier des charges du bot : moteur de la version finale et critère de conformité, six actifs, matrice de taille de D04.2, avertissements (latence sans coût, glissement des stops, profil de queue droite, portage non modélisé). Aucun calcul nouveau. |
| — | Trois directions | décision du porteur (2026-10-05) | 1 Fonds propres : paper trading et workstation (simulateur puis démo ; NautilusTrader sous porte de parité, repli sur notre moteur), session dédiée en worktree. 2 Prop Firm : cycle suivant, avec le porteur, sur `main`. 3 Sniper manuel : dépôt privé séparé, signaux rares pour trades manuels ; exploration libre, cadrage, puis méthode sous protocole. Prompts dans `prompts/`. |
| 7 | Cadrage Prop Firm (D05) | décision du porteur (2026-10-05) | Plan du porteur critiqué sur rapports existants : TradFi déjà lue (D01.7), break-even déjà rejeté (C03), perte totale statique liante. Étalon FTMO Swing (objectifs 9 % puis 5 %, perte du jour 5 % à minuit CET/CEST, perte totale 10 % statique, levier crypto 1:2, or 1:30, marge plafonnée). D05.3 annulé ; D05.1 recadré pour plus tard (profil des actifs, TradFi cTrader, GLE candidat) ; simulateur d'abord. |
| 7 | EXP-D05.4 | faite (2026-10-05) | Simulateur de challenge (`src/propfirm/`), 1 826 départs quotidiens, RE-1 VF sur six actifs. Réussite P1 + P2 : 88 % (0,05 %/ATR, délai médian 571 j), 79 % (0,10, 173 j), 60 % (0,15, 100 j), 59 % (0,20, 68 j), 51 % (0,25, 41 j). Échecs par la perte totale statique ; perte du jour non liante (≤ 0,7 %). Marge 1:2 sans effet notable jusqu'à 0,15. En un an, au mieux 67,6 % (0,10) ; en 90 jours, 38,9 % (0,25). Sans 2026 : 43 à 62 %. |
| 7 | EXP-D05.5 | faite (2026-10-05) | Compte financé FTMO (80 %, retrait tous les 14 jours, 540 € remboursés au premier retrait). Valeur d'une tentative à 12 mois : −273 € (0,05), +3 336 € (0,10), +6 902 € (0,15), +9 218 € (0,20), +7 504 € (0,25) ; maximum à 0,20 aussi à 24 mois et sans 2026. De 0,10 à 0,25, 71 à 99 % des comptes financés perdus en un an, après 16 à 22 % du compte retirés ; à 0,05, jamais perdus. |
| 7 | EXP-D05.6 | faite (2026-10-05) | Variantes de taille du porteur contre un risque fixe, au même délai médian. A (frein) : +1,9 point, valeur −4 653 €. B (sprint) : −5,7 points. C (coussin) : aucun échec par la perte totale, réussite de 93 à 98 % (+17 à +24 points), mais comptes bloqués (P90 jusqu'à 1 081 jours ; sans 2026, 38 à 43 % en cours). Aucune variante n'approche la valeur du risque fixe à 0,20. Cible du porteur sans 2026 : seul C à r0 = 0,20. |
| 7 | EXP-D05.6bis | faite (2026-10-05) | Une taille propre à chaque phase (« Burn & Churn », GO du porteur), 7 × 7 combinaisons ; valeur d'une tentative et d'une suite de tentatives (un compte à la fois). Ni le combo A (coussin en challenge : −0,8 à −4,8 k€ par tentative, −11 à −31 k€ en suite) ni le combo B (fixe 0,15 : égal par tentative, −1,7 à −3,2 k€ en suite) ne battent la référence (fixe 0,20 partout, +9 218 €). Bat la référence partout : challenge 0,20 et compte financé à 0,25 (+1,0 à +1,2 k€ par tentative) ou en relance (+1,7 à +2,1 k€). En suite, un challenge plus rapide paie (0,30 : jusqu'à +17,5 k€ en 24 mois, optimum non atteint). Gains du compte financé agressif seulement après une réussite (filtre de période, à tester en D05.7). |
| 7 | Roster final (D05.6bis) | décision du porteur (2026-10-05) | Relance gardée ; trois pistes : 1 (0,20 × 0,25), 2 (0,25 × 0,25), 3 (relance, challenge 0,20 à 0,30). Seul le compte financé à 0,25 gagne partout et chaque année. Challenge rapide : perd par tentative ; gagne en suite, fragile de 0,20 à 0,25 à 24 mois, net de 0,25 à 0,30. Relance : dans le bruit par tentative, +3,6 à +4,8 k€ en suite à 24 mois. D05.7 sur ce roster, après GO. |
| 7 | EXP-D05.7 | faite (2026-10-05) | Tirage par blocs sans 2026 (221 semaines, `propfirm.blocs`), 200 histoires par longueur de bloc (1 et 4 semaines), roster final. La vitesse du challenge survit en suite (+1,9 à +2,3 k€ par pas en 12 mois, +3,4 à +4,1 k€ en 24 mois ; 80 à 94 % des histoires). La relance ne survit pas (médiane −1,1 à +0,1 k€) ; compte financé 0,25 égal à 0,20 par tentative, petit gain en suite. Blocs de 4 semaines proches de ceux d'une semaine. Histoire réelle favorable à toutes les pistes (78e à 96e centile) : médianes recomposées de +3,1 à +4,6 k€ par tentative à 12 mois, de +23 à +34 k€ en suite à 24 mois. |
| 7 | Verrouillage de la taille (D05) | décision du porteur (2026-10-05) | Piste 1 verrouillée : challenge 0,20 × compte financé 0,25, un compte à la fois, budget de tentatives contrôlé. Piste 2 archivée comme option de croissance. Fin des recherches sur la taille. |
| 7 | EXP-D05.8 | faite (2026-10-05) | Moment d'achat du challenge (référence, pistes 1 et 2). Tendance haussière du panier crypto : aucun gain par tentative, −1,7 à −6,1 k€ en suite. Sortie de compression de la volatilité : +3,2 à +4,7 k€ par tentative (IC avec zéro, gain concentré en 2023-2024), −0,7 à −1,9 k€ en suite (piste 1), 20 % de challenges en moins. Avec une règle d'attente, la piste 1 dépasse la piste 2. Recommandation : aucun filtre. Séquence taille close. |
| 7 | Aucun filtre d'achat (D05) | décision du porteur (2026-10-05) | Rachat au minuit qui suit la fin du compte précédent. Push de D05.7 et D05.8 fait (origin = `ee1ee00`). D05.1 ouvert : univers TradFi, GLE parmi d'autres candidats ; profil d'abord, extracteur cTrader Open API ensuite. |
| 7 | EXP-D05.1 (profil) | note livrée, grille validée par le porteur (2026-10-05) | Profil des actifs pour RE-1 hors crypto, sans calcul (`experiments/D05_1/profil_actifs_D05_1.md`). Signal transposé sur les 13 séries hors crypto, rente non (brut médian +0,15 ATR, aucun IC > 0). Ratio vital brut / frais : cryptos 3,6 à 4,2 ; indices, or, argent et GBPJPY 0,2 à 1,0 ; points morts du coût : BTC ≈ 18 bps, indices 2 à 5 bps. Grille de 13 axes sans seuil ; demandes à l'extracteur : écarts par heure, swaps, fiches de symboles, roulements. |
| 7 | D05.1 : données FTMO par cTrader Open API | décision du porteur (2026-10-05) ; code prêt, non lancé | D01.7 écarté comme filtre. Candidats : GLE, WTI, Brent, US100, US30, GER40, GBPJPY, plus les fiches des six actifs actuels ; de 2020-01 à aujourd'hui, 2026 incluse ; coûts FTMO. Objectif : l'inclusion dans le portefeuille, contre les pistes 1 et 2. `marketdata.ctrader` (JSON sur WebSocket, OAuth, 18 tests) et `donnees_D05_1.py` prêts ; application à créer par le porteur. |
| 7 | EXP-D05.1 (grille mesurée) | faite (2026-10-05) | Sans RE-1 ni coût, BTC, SOL, or et candidats Saxo 2020-2025 (`profil.grille`, 13 tests). Queue de 13 h en ATR : 11 à 28 fois le repère gaussien ; US100 et US30 autant que BTC par fenêtre, mais saison horaire 2,4 à 2,6 fois plus marquée. Persistance (VR), naissance au calme et plus gros pas : sans pouvoir distinctif. Coupures, gaps et plafond de 1x distinguent les séries ; GBPJPY puis l'or les moins liés à BTC. Creux de RE-1 riche en expansions sur BTC (1,64). Quatre points de la note corrigés. Proposé : z26 corrigé de la saison ; données FTMO. |
| 7 | EXP-D05.1 (correction horaire) | faite (2026-10-06), mise de côté par le porteur | z26 corrigé de la saison horaire (facteur causal par demi-heure locale, 40 jours ; 4 tests). Fenêtres à 10 ATR ou plus pour 1 000, brut → corrigé : US100 51 → 17, US30 43 → 14, GER40 26 → 13, or 31 → 15, GBPJPY 22 → 15, BTC 40 → 35, SOL 22 → 20. Corrigée, la queue de BTC vaut 2,1 à 2,7 fois celle de chaque candidat ; indices penchés à la baisse. Fréquences moyennées sur les 26 alignements (artefact d'alignement relevé). |
| 7 | EXP-D05.1 (données FTMO et frictions) | faite (2026-10-06) ; passation | cBot cTrader (v1, v2) au lieu de l'Open API. 11 symboles vérifiés (corrélation 0,98 à 0,998 avec les séries du dépôt, décalage nul) ; SAN et AVAX à récupérer. Frictions trade par trade (`propfirm.frictions`) : écart par demi-heure locale, commission, swaps par rollover, pauses de cotation des cryptos. Cryptos : 8,9 à 19,1 bps par trade contre 5 (commission 6,5 bps, swap −30 %/an, levier 1:1) ; or 1,9 bps. Baseline cTrader (six marches) préparée pour la session suivante (`passation_D05_1.md`). |
| 7 | EXP-D05.1, étape 2 (profil TradFi) | fait (2026-10-06) | RE-1 version finale sur barres FTMO, frictions réelles (SAN absent). Espérance nette (ATR) : or +0,019, US100 −0,038, US30 −0,108, GER40 +0,086, GBPJPY +0,006, WTI −0,311, Brent −0,394 ; même forme que BTC en plus petit (+5 ATR : 8,5 à 14,6 par an contre 17,8) ; corrélation mensuelle avec le panier crypto proche de zéro (WTI −0,43). Étape 3 (inclusion) à cadrer. |
| 7 | D05.1 : univers et nouvelle piste | décision du porteur (2026-10-06) | SAN remplacé par META ; AVAX remplacé par une autre crypto FTMO, au choix du porteur (liste courte : AAVE, LINK, UNI, XLM, DOGE ; critères structurels). Nouvelle piste : optimiser uniquement les paramètres du filtre de Kalman sur un actif hors crypto (US100) pour tester le besoin de réglage par actif (walk-forward, configurations comptées, écart apparié contre RE-1 figée). Données : cBot v3. |
| 7 | D05.1 : données complètes, clôture | fait (2026-10-06) ; passation | Export v3 : META (FTMO depuis 2025-01), AVAX (écart réel 18,3 bps : net +0,308 → −0,009 ATR par trade), cryptos candidates. Page FTMO : swaps du pétrole confirmés, levier Swing réel 1:1 crypto et 1:15 or (étalon de D05.4 faux pour Swing). Remplacement d'AVAX mis de côté. `passation_D05_1.md` : Baseline cTrader, META, inclusion, piste US100. |

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
