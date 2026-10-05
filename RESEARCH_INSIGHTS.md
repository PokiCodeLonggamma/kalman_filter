# RESEARCH INSIGHTS — DÉCOUVERTES STRUCTURANTES

> Ce fichier consigne ce que les expériences validées ont établi : sur le moteur, sur la méthode, et les hypothèses qu'elles ouvrent. **Ce ne sont ni des règles de trading, ni des conclusions de rentabilité.**
>
> Les règles du laboratoire sont dans `RESEARCH_PHILOSOPHY.md`, le détail des expériences dans `RESEARCH_LOG.md`.
>
> **Statuts :**
> - `[OBS]` mesuré et reproductible, source citée ;
> - `[HYP]` interprétation ou piste à tester ;
> - `[MÉTHODE]` règle d'analyse adoptée par le porteur du projet.
>
> Mis à jour après chaque expérience validée. Sauf mention contraire, les chiffres portent sur BTC/USD 30 min, 2020-2025, moteur v2.1 aux réglages par défaut, univers des 7 296 signaux. Médianes suivies de [P25 ; P75].

---

## 1. Méthode

### I-M1 — La tenue de l'extremum n'est pas une cible `[MÉTHODE]`
*Porteur, 2026-09-28. Source : EXP-A01, annexe I.*

La « tenue de l'extremum du segment jusqu'au signal suivant » (`post_lag_bars` ≥ 0, soit une excursion adverse inférieure à `obs_dist_seg_atr`) croît mécaniquement avec la distance déjà parcourue à l'entrée :

| Quartile de `obs_dist_seg_atr` | Distance médiane à l'extremum | Part de la jambe déjà reprise (`obs_dist_seg_atr` / `leg_atr`) | Extremum tenu |
|---|---|---|---|
| Q1 [0,00 ; 1,26 ATR] | 0,92 ATR | 35 % (entrée fraîche) | 36,5 % |
| Q2 [1,26 ; 1,77 ATR] | 1,52 ATR | 59 % | 61,4 % |
| Q3 [1,77 ; 2,39 ATR] | 2,04 ATR | 72 % | 72,6 % |
| Q4 [2,39 ; 7,72 ATR] | 2,94 ATR | 87 % (mouvement déjà mangé) | 85,3 % |

- **Ce n'est pas un signe de qualité.** Si l'extremum tient plus souvent en Q4, ce n'est pas que le signal y est meilleur. Un recul de près de 3 ATR en une douzaine de barres est simplement plus rare qu'un recul de 0,9 ATR : le résultat est tautologique.
- **Règle :** cette variable ne sert jamais seule de cible à l'Étape B. La maximiser sélectionnerait les entrées les plus tardives (grande distance parcourue, fort choc `nis_z_100`). Elle enfermerait aussi la recherche dans l'horizon de la sortie native (~13 barres). Elle reste une variable descriptive.

### I-M2 — Cible de l'Étape B `[MÉTHODE]`
*Décision du porteur, 2026-09-28, conforme à `PROJECT_PLAN.md`.*

La cible de B est l'**asymétrie de l'excursion future**, MFE_H contre \|MAE_H\| :
- mesurée depuis le prix d'entrée exécutable open[t+1] ;
- exprimée en ATR14(t) ;
- à horizons fixes H ∈ {6, 13, 26, 48} barres ;
- et par barrières symétriques de ±1,5 et ±2,0 ATR (quelle barrière est touchée en premier).

Elle se mesure séparément par sens et par type de signal (rang 1 ou répétition).

### I-M3 — Vérifier les artefacts de définition avant de parler de populations `[MÉTHODE]`
*Source : EXP-A01, relecture, annexe H.*

- La bimodalité de `post_lag_bars` (creux autour de 0) ne révèle pas deux horloges du filtre. L'identité est exacte sur les 7 296 signaux : `post_lag_bars` < 0 ⇔ l'excursion adverse jusqu'au signal suivant dépasse `obs_dist_seg_atr`.
- Casser l'extremum demande de parcourir plus que les 1,77 ATR médians déjà faits, ce qui prend plusieurs barres. Le creux autour de 0 est donc une conséquence de la géométrie de la fenêtre.

### I-M4 — Ne pas élaguer les variables sur la seule corrélation `[MÉTHODE]`
*Source : EXP-A01, relecture.*

- Une variable corrélée à 0,96 peut porter une information utile dans son écart à sa jumelle. Exemple : `cycle_seg_div_atr` = `obs_dist_cycle_atr` − `obs_dist_seg_atr`, qui signale un plus bas plus haut. Il vaut mieux extraire l'écart que jeter la variable.
- Chaque variable est classée explicitement comme retenue ou écartée. Pour B, `nis_z_100_seg_max` avait été oublié.

### I-M5 — Un écart de médianes se juge avec son incertitude `[MÉTHODE]` `[OBS]`
*Source : EXP-A01, annexe H, bootstrap 2 000 tirages.*

- Répétitions Short à +24 barres : +0,11 ATR [−0,02 ; +0,30]. Rangs 1 Short : −0,13 [−0,26 ; −0,03]. Les intervalles sont disjoints de justesse : l'écart entre les deux groupes sort du bruit.
- C'est notable sur un actif en hausse séculaire, où les rangs 1 Short ont une médiane négative à +12, +24 et +48 barres.
- En revanche, la médiane des répétitions Short **ne se distingue pas de zéro**.

### I-M6 — Lire le centre et les queues d'une distribution `[MÉTHODE]`
*Porteur, relecture d'EXP-B01, 2026-09-28.*

- Une médiane et un taux de barrière symétrique (1:1) décrivent le cas typique. Ils ne voient pas une espérance portée par une queue.
- Un breakout peut avoir une médiane nulle (faux départs) et une moyenne positive (queue droite). Un retournement peut avoir une médiane positive et une moyenne nulle (queue gauche, sans stop). Ces deux profils orientent vers des enveloppes différentes (hypothèses du §4).
- **Règle :** chaque strate se résume par sa médiane, sa moyenne et ses queues (P10, P90, P90 + P10), par sens.
- Une moyenne en ATR se juge avec sa robustesse :
  - IC par bootstrap de grappes mensuelles, car les fenêtres se chevauchent ;
  - stabilité annuelle ;
  - moyenne winsorisée aux P1 et P99.

### I-M7 — Contrôle du bêta sans placebo : timing et dérive `[MÉTHODE]`
*Source : EXP-B01, annexes H et I ; mesure reprise par le porteur à la relecture.*

- m_L et m_S sont la médiane (ou la moyenne) du rendement orienté après les Long et après les Short.
  - Timing = (m_L + m_S) / 2 : part où le prix suit le sens du signal.
  - Dérive = (m_L − m_S) / 2 : part commune aux deux sens, donc le mouvement du marché.
- **Limite :** la dérive ne s'annule que si les Long et les Short d'une strate voient le même marché. Un effet présent d'un seul côté se répartit à parts égales entre timing et dérive.
- On lit donc aussi, pour chaque sens, l'écart à l'ensemble des signaux du même sens.

### I-M8 — Juger une espérance en bps et en ATR14(t) `[MÉTHODE]`
*Consigne du porteur, EXP-C02, 2026-09-29.*

- **Pourquoi les deux unités.** En notionnel fixe, les années volatiles dominent. L'ATR14 médian des signaux vaut 80,3 bps en 2021 contre 33,6 en 2023 : 2021 pèse 2,4 fois plus en moyenne et 5,7 fois plus en variance.
- L'espérance en ATR14(t) est le rendement par trade à risque constant, convention de l'Étape C (1 ATR = 0,25 % du capital).
- **Règle :** IC 95 % par grappes mensuelles sur l'espérance et le timing, en bps et en ATR.
- **Exemples :**
  - F2b · x1 hors Q4 à H26 : +11,5 bps [−2,9 ; +26,0], mais +0,389 ATR [+0,079 ; +0,700] ;
  - à l'inverse, F5 est positif en bps à court terme et négatif en ATR.
- **Piège propre à l'ATR :** un saut en marché calme vaut beaucoup d'ATR (+44 ATR le 29 août 2023). La winsorisation P1/P99 le détecte.

### I-M9 — Une règle de sortie se juge d'abord sur les mêmes entrées `[MÉTHODE]`
*Source : EXP-C02 et sa relecture.*

- L'effet d'un stop, d'un take-profit ou d'un break-even se mesure d'abord par différence appariée, sur les entrées de la course de contrôle, avec son IC par grappes. Les frais s'annulent et la variance due aux entrées disparaît.
- En séquentiel, la règle change aussi les entrées : une position libérée plus tôt prend le signal suivant. Cet effet de réouverture se lit à part.
- La lecture « entrées figées » est une règle exécutable : un cooldown qui garde la position à plat jusqu'à la sortie prévue t + 1 + H.

### I-M10 — Le drawdown est une statistique de chemin `[MÉTHODE]`
*Source : EXP-C03.*

- Le MDD dépend de l'ordre des trades. Son effet apparié se lit sur des chemins réordonnés : les mois d'entrée sont tirés avec remise, avec les mêmes tirages que les IC.
- On en retient la plage P2,5-P97,5 de l'écart et la part des chemins où la variante est moins profonde. Ce n'est pas un IC centré sur l'écart observé, qui peut sortir de la plage.
- Un écart de 1 à 4 points de MDD entre deux règles voisines reste du bruit de chemin tant que la plage contient 0. Un MDD qui ne varie pas de façon monotone avec le paramètre signale le même bruit.

### I-M11 — Une règle de gestion du risque se juge contre la simple réduction de taille `[MÉTHODE]`
*Source : EXP-C03, analyse approfondie.*

- Une règle qui baisse le MDD en baissant aussi le rendement peut n'être qu'un désendettement.
- On la compare donc au contrôle réduit en taille jusqu'au même MDD valorisé. Si elle ne fait pas mieux en PnL annualisé à MDD égal, elle n'améliore pas l'efficience du capital, et la réduction de taille l'obtient sans paramètre supplémentaire.
- Exemple : V3 à m = 2 fait +1,0 point par an de mieux sans glissement, mais −0,8 point avec 5 bps de glissement du break-even.
- La durée sous le pic se lit à côté : un drawdown moins profond peut être plus long.

### I-M12 — La sensibilité d'un seuil se lit par bandes marginales `[MÉTHODE]`
*Source : EXP-C05.*

- Déplacer un seuil change la règle d'une bande de signaux seulement. À entrées égales, l'effet d'un point de grille est la somme des effets par bande.
- La courbe de sensibilité s'explique donc par la table des bandes. Exemple, la frontière F2b / F3 : le stop coûte 0,53 à 0,58 ATR par trade sur les retracements de 0,75 à 0,85, et rien au-delà.
- La lecture (plateau, falaise, crête) est fixée avant le calcul, sur les voisins immédiats. Ne pas l'imposer aux points extrêmes, qui décrivent seulement la pente.
- Deux réserves :
  - le rang du contrôle dans sa grille dit si le seuil a pu être calé sur la courbe ;
  - un seuil choisi après lecture des mêmes données (exclusion de Q4 après C01) est attendu au sommet.

### I-M13 — Vérifier le fuseau et les séances d'une source par sa structure, pas par sa documentation `[MÉTHODE]`
*Source : EXP-D01, audit des données.*

- La FAQ de HistData annonce un EST fixe. La pause quotidienne des CFD (17:00-18:00 heure de New York) montre une horloge EET/EEST moins 7 h : UTC−4 de fin mars à fin octobre.
- **Règle :** pour toute série en séances, lire la pause quotidienne et l'ouverture hebdomadaire en heure locale du marché, semaine par semaine, avant tout calcul. Chercher aussi les doublons exacts autour des changements d'heure (une heure par an chez HistData).
- **Portée :** un décalage d'heures entières ne change ni les barres ni les trades de RE-1. Il change le calendrier : années, mois des grappes, rapprochement avec une référence externe.

### I-M14 — Les frais se lisent en ATR, actif par actif `[MÉTHODE]` `[OBS]`
*Source : EXP-D01.*

- Un frais fixe en bps coûte fee / ATR14(t) par trade : 0,14 ATR sur BTC à 5 bps, 0,06 sur SOL à 5 bps, 0,26 sur l'or à 4 bps. Les bruts sont de +0,50, +0,25 et +0,24 ATR.
- **Règle :** publier le brut et les frais en ATR à côté du net. Un actif calme à l'échelle des barres peut perdre un avantage brut réel ; l'écart se lit alors comme une question d'échelle de temps.
- **EXP-D01.7 :** sur GBPJPY (ATR de 30 min ≈ 11 bps), 4 bps coûtent 0,41 ATR par trade. Le dimensionnement à 0,25 %/ATR y demanderait environ 2,3 fois de levier : le plafond de 1x mord sur 98 % des trades, et les métriques « 0,25 %/ATR » valent alors le 1x. Vérifier la part plafonnée avant de lire une métrique dimensionnée.

### I-M15 — Séries d'actions et d'ETF : calendrier, enchère, dividendes et fractionnements `[MÉTHODE]`
*Source : EXP-D01 bis.*

- **Clôtures anticipées.** Un filtre horaire fixe (09:30-16:00) garde le post-marché des séances fermées à 13:00. Il faut appliquer le calendrier de la place et le vérifier sur les données : le volume s'effondre après la clôture.
- **Enchère de clôture.** Horodatée à 16:00:00, elle tombe hors de la dernière barre de séance : le close de cette barre est la dernière transaction continue.
- **Série ajustée.** Mesurer sur la série ajustée des dividendes et des fractionnements, et garder la série brute pour les repérer. XLE a été fractionné 2 pour 1 le 2025-12-05 : −6 931 bps en série brute. Seuil de détection des dividendes au-dessus du bruit d'arrondi des prix ajustés (jusqu'à 5 bps sur un titre à 30-90 $).

### I-M17 — Le moteur est invariant d'échelle à la précision machine : un rétro-ajustement par ratio n'apporte pas d'information future `[MÉTHODE]` `[OBS]`
*Source : EXP-D01.7 (contrôle sur BTC multiplié par 0,37 et 2,9).*

- Les signaux sont identiques et les descripteurs identiques à 3·10⁻⁵ près en relatif (`nis_z_100` ; médiane 10⁻¹⁰).
- Seuls basculent les signaux dont `retrace_ratio` vaut exactement 0,50, la borne de F2b (passage en F5). RE-1 à ×2,9 : 1 trade de moins sur 1 080, espérance +0,3686 → +0,3676 ATR.
- **Règle :** une série continue rétro-ajustée par ratio (futures) est utilisable. Le facteur commun à une fenêtre dépend des roulements postérieurs, mais il ne change que ces égalités au seuil.
- Un rétro-ajustement par différence (BACKWARDS_PANAMA) ne serait pas couvert : il change les rendements relatifs.

### I-M16 — Une variation de H se lit sur entrées figées : la course séquentielle y ajoute un effet de calendrier `[MÉTHODE]` `[OBS]`
*Source : EXP-D01.5.*

- En séquentiel (une position à la fois), allonger H fait sauter les signaux qui arrivent pendant la position. Le résultat mêle donc l'effet de la sortie et le choix des trades gardés.
- XLE, H = 65 : +0,155 ATR en séquentiel, +0,009 sur les mêmes entrées que H = 26 (effet −0,010 [−0,71 ; +0,75]). Les 31 trades sautés valaient −0,48 ATR. Or, H = 130 : −0,702 en séquentiel, −0,165 sur entrées figées (trades sautés +0,38).
- **Règle :** publier l'effet apparié sur entrées figées à côté de toute variation de H (extension d'I-M9). Un optimiseur de H sur la course séquentielle ajuste aussi ce calendrier.
- À dimensionnement égal (0,25 % par ATR14 de 30 min), le risque par trade croît avec H : MDD de l'or −13,6 % à H = 26, −41,6 % à H = 130. Comparer des H au Calmar suppose de fixer cette convention.
- **Verrouillage découplé de la sortie (EXP-D01.6).** À sortie fixe (26 barres), faire varier le verrouillage (26 à 90) donne un zigzag sans tendance sur SPY et XLE : chaque valeur retire un paquet de trades différent, valant de −0,75 à +0,87 ATR. Les trades sautés ne se distinguent à t que par leur délai depuis le trade précédent. Le verrouillage est un sélecteur de calendrier, pas un paramètre à optimiser.
- **Recalibrage de H (EXP-D02).** Sur BTC 2015-2025, H réoptimisé chaque semestre perd −0,174 ATR [−0,276 ; −0,074] face à H = 26 en séquentiel, mais −0,008 [−0,121 ; +0,116] sur les entrées figées du Contrôle : la perte est un effet de calendrier, pas de sortie.
- **Verrou fixe (EXP-D02.1, décision du porteur : 26 barres pour tous les tests).** Les 2 075 entrées de RE-1 gelée restent identiques pour tout H ; au-delà de 26, l'entrée suivante clôt la position (option C). Le WFO de H_exit regagne +0,227 ATR [+0,090 ; +0,365] sur celui de D02, mais ne fait pas mieux que H = 26 : +0,029 [−0,075 ; +0,139]. Le verrou supprime l'effet de calendrier ; il ne révèle aucune valeur des sorties.

### I-M18 — Un choix « au centre du plateau » dépend de la géométrie de la grille `[MÉTHODE]` `[OBS]`
*Source : EXP-D02 (règle du porteur : centre de la plus grande zone connexe à Calmar net > 0).*

- En trois dimensions (R0 sur 5 rangs, H sur 28 pas, frontière sur 5 pas), les zones retenues couvrent souvent une grande part de la grille : de 107 à 559 cases sur 700 sur BTC (médiane 280). Leur centre retombe alors près du centre de la grille (H de 30 à 44 sur BTC), quel que soit le marché.
- Sur un axe entièrement positif, le centre est le milieu de l'axe : la frontière tombe sur 0,85, milieu de 0,75-0,95, par construction.
- **Règle :** publier la taille des zones avec le choix, et lire ce choix au regard des bornes de la grille. Un choix au centre d'une très grande zone ne mesure pas le marché ; il reflète les bornes posées.
- **À entrées constantes (EXP-D02.1),** le profil de H se lisse : 10 semestres sur 22 ont une zone de 23 à 28 cases sur 28 (7 en D02), et le choix tombe à 32-38, alors que le meilleur Calmar IS était à 14-16 (2018-2019), 40-42 (2020, 2024) ou 22 (2025).

### I-M19 — Un départage vers le point de référence transporte l'information de sa période de construction `[MÉTHODE]` `[OBS]`
*Source : EXP-D02.1 (WFO de R0, règle de D02 contre inertie).*

- En D02, les égalités au centre d'une zone étaient tranchées vers le point de RE-1 (R0 = 100), autour duquel RE-1 a été construite sur BTC 2020-2025. Sur la grille {10, 50, 100, 200, 500}, ce départage a joué 12 semestres sur 22.
- Avec l'inertie (case la plus proche du choix précédent), un seul choix change : 2018-S2, R0 = 50 au lieu de 100. 2018 passe de +0,482 à −0,160 ATR, et toute l'avance du WFO-R0 de D02 disparaît (−0,065 [−0,155 ; −0,002]).
- **Règle :** un walk-forward qui se replie ou départage vers la configuration de référence hérite de l'information de sa période de construction. Lire son avance au regard des semestres tranchés par ce départage, et tester une règle neutre à côté.

### I-M20 — Un classement en ATR favorise les trades ouverts à ATR bas : profiler aussi en bps `[MÉTHODE]` `[OBS]`
*Source : EXP-D03 (profil des 5 % meilleurs trades de RE-1 gelée, BTC 2015-2025).*

- Le rendement en ATR divise le mouvement par l'ATR du signal : à mouvement égal, un ATR bas donne un rang plus haut. Avec un risque de 0,25 % par ATR, ces trades engagent aussi plus de notionnel, donc pèsent plus dans le capital.
- Classés en ATR, les 104 meilleurs trades naissent à ATR bas (médiane 37 bps contre 48) ; classés en bps, à ATR haut (75 bps). Les deux classements n'ont que 53 trades en commun.
- **Règle :** tout profil des meilleurs ou des pires trades se lit selon deux classements, en ATR (poids dans le capital) et en bps (mouvement du marché), avant d'en tirer un filtre.

### I-M21 — Une fréquence d'événements rares sur fenêtres disjointes dépend de l'alignement : la moyenner sur tous les alignements `[MÉTHODE]` `[OBS]`
*Source : EXP-D05.1 (correction horaire).*

- Sur BTC 2020-2025, les fenêtres de 26 barres à 20 ATR ou plus passent de 2,2 à 4,0 par an selon la barre de départ
  du découpage. À 10 ATR, l'écart reste sous 10 %.
- **Règle :** compter les événements rares sur toutes les fenêtres glissantes, puis rapporter la fréquence au nombre de
  fenêtres disjointes ; dire à partir de quel seuil l'alignement compte.

---

## 2. Cinématique du moteur v2.1
*Source : EXP-A01.*

### K1 — Le déclencheur mêle retournement et décélération
- `[OBS]` Position du signal par rapport au passage à zéro de la vitesse filtrée x1 :
  - à la barre même : 36,8 % ;
  - 1 à 2 barres avant : 27,7 % ;
  - 3 barres ou plus avant : 21,2 % ;
  - après : 0,7 % ;
  - aucun passage avant le signal suivant : 13,6 %.
- `[OBS]` 48,2 % des signaux partent avec x1 encore du sens opposé.
- `[HYP]` La normalisation par max\|x1\| sur 5 barres confond deux mécanismes : le retournement de la vitesse et la simple décélération d'une tendance qui continue.

### K2 — La distance déjà parcourue dépend de la barre de signal, pas de l'attente
- `[OBS]` À l'entrée, le prix est déjà à 1,77 ATR [1,26 ; 2,39] de l'extremum du segment.
- `[OBS]` Corrélations de rang de cette distance : ρ = 0,09 avec l'ancienneté de l'extremum, 0,63 avec `nis_z_100` (choc de la barre de signal), 0,44 avec x1 déjà retourné.
- `[OBS]` Le rebond médian a lieu avant le signal : de −0,67 ATR à τ = −6 à 0 à τ = 0. Ensuite, le close médian reste plat, alors que x1 monte à +0,28 ATR/barre à τ = +5.
- `[HYP]` Avec un gain figé, le filtre absorbe le rebond avec environ 5 barres de retard. Un `nis_z_100` élevé à τ = 0 ferait entrer après une bougie de rebond déjà consommée. C'est cohérent avec la strate `nis_z_100` Q4 défavorable de #KAKALMAN P6.5b.

### K3 — Tenue ou cassure de l'extremum du segment
- `[OBS]` L'extremum tient jusqu'au signal suivant dans 63,9 % des cas. L'horizon médian est de 13 barres [10 ; 17].
- `[OBS]` Quand il est cassé (36,1 %), le prix va au-delà de l'extremum de +1,45 ATR en médiane, +2,57 ATR en moyenne, et +6,21 ATR au P90.
- `[HYP]` Cette extension est la signature d'une reprise de tendance, ou d'une cassure par l'autre bord.

### K4 — Sortie de la zone neutre après le signal
- `[OBS]` `trend_strength` quitte la zone [−30 ; +30] vers la zone du sens du signal dans 91,2 % des cas, en 2 barres [1 ; 2].
- `[OBS]` Il retourne vers sa zone d'origine dans 8,8 % des cas, en 3 barres [2 ; 4].

### K5 — Répétitions (`run_rank` > 1, 17,3 % des signaux)
- `[OBS]` Ce sont surtout des deuxièmes jambes vers un nouvel extremum : c'est le cas de 86,3 % d'entre elles, comme des rangs 1.
- `[OBS]` Leur vitesse de pointe est plus faible que celle de la jambe précédente dans 56,6 % des cas.
- `[OBS]` Leur extremum est cassé moins souvent : 31,0 % contre 37,1 %. La marge est plus grande (1,93 contre 1,73 ATR), pour une excursion adverse égale (1,23 contre 1,25 ATR).
- `[HYP]` L'étiquette « double bottom » n'est pas soutenue. B dira si `run_rank > 1` est un atout.

### K6 — Cycle et stationnarité
- `[OBS]` Un signal de même sens revient toutes les 26 barres [21 ; 34], un signal de sens opposé toutes les 13 [10 ; 20]. La cadence est de 101,9 signaux par mois.
- `[OBS]` En unités d'ATR, la géométrie du signal varie peu de 2020 à 2025. Seul le niveau de volatilité change : l'ATR14 médian va de 34 à 80 bps selon l'année.
- `[HYP]` Une enveloppe exprimée en ATR14(t) devrait mieux se transférer entre régimes qu'une enveloppe en bps.

### K7 — La géométrie du déclencheur est la même d'un actif à l'autre
*Source : EXP-D01.*

- `[OBS]` Sur BTC, SOL/USD et l'or :
  - `leg_atr` P50 : 2,82 / 2,85 / 2,90 ;
  - `retrace_ratio` P50 : 0,62 / 0,60 / 0,59 ;
  - part de `nis_z_100` au-dessus de 1,2245 : 25,0 / 27,3 / 24,9 % ;
  - x1 déjà retourné : 51,8 / 52,3 / 49,4 % ;
  - alors que l'ATR14 médian vaut 50, 95 et 17 bps.
- `[HYP]` La stationnarité en ATR de K6 vaut aussi entre actifs. Des seuils sans dimension sélectionnent la même population partout : le transfert (a) est cohérent avec le moteur. La rente, elle, varie d'un marché à l'autre.

### K7 bis — GBPJPY : la géométrie se transpose, le brut non
*Source : EXP-D01.7.*

- `[OBS]` La médiane locale de `leg_atr` vaut 2,86 (BTC 2,82) et le P75 local de `nis_z_100` 1,40 (BTC 1,22). La géométrie du déclencheur se transpose, comme en D01.
- `[OBS]` Le brut de RE-1 est nul (−0,035 ATR [−0,284 ; +0,221]) : symétrique, sans dérive, à toutes les sessions et dans tous les terciles de volatilité. Le profil de queue reste celui de BTC (médiane −1,42 ATR, décile supérieur +0,75 ATR par trade), sans la moyenne positive.
- `[HYP]` Même cinématique détectée, mais sans suite exploitable à 13 h sur une paire de change calme.

### K8 — Gaps d'ouverture : le filtre d'innovation les écarte à l'entrée, pas en position
*Source : EXP-D01 bis (SPY, XLE, séance régulière).*

- `[OBS]` Le gap est une innovation pour le filtre. Sur la barre d'ouverture, `nis_z_100` vaut 1,40 et 1,59 en médiane, contre 0,14 ailleurs. Le seuil de RE-1 écarte 64 % et 74 % des signaux R2 nés d'un gap.
- `[OBS]` H = 26 barres fait traverser deux nuits (48 h calendaires). Les gaps pèsent 35 à 47 % de l'amplitude des trades. Les stops percés à l'ouverture dépassent leur niveau de +1,0 à +2,6 ATR en moyenne.
- `[OBS]` Les écarts de nuit allongent les jambes mesurées en ATR (`leg_atr` P50 3,1 à 3,2, contre 2,8 à 2,9 ailleurs).
- `[HYP]` Sur une série en séances, un horizon compté en barres mêle la cinématique d'une séance et le risque de nuit.

### K9 — H déplace l'exposition, pas l'avantage
*Source : EXP-D01.5 (or H 26-130 ; SPY et XLE H 6-130 ; 4 bps).*

- `[OBS]` Les frais en ATR ne dépendent pas de H : fee / ATR14(t) de l'entrée, 0,26 par trade sur l'or à tout H.
- `[OBS]` Le brut par trade ne croît pas avec H. Or, sur les mêmes entrées : +0,24, +0,26, +0,32, +0,21, +0,09 ATR de 13 h à 68 h. Sur les trois actifs, l'effet apparié de H va de −0,55 à +0,08 ATR, tous les IC ∋ 0.
- `[OBS]` Ce qui croît avec H : la dérive de l'actif, qui joue des deux côtés (or +0,38 → +0,81 ATR ; Short −0,43 → −1,54), le nombre de nuits et le risque par trade.
- `[OBS]` En séance régulière, H = 13 barres = une séance : 91 % des trades traversent une nuit, comme à H = 26. Seul H = 6 réduit l'exposition (50 à 57 %). La composante en séance du brut est ≈ 0 sur SPY et négative sur XLE à tout H.
- `[HYP]` Sur ces marchés, l'avantage manque en amont de la sortie. Une sortie en fin de séance retirerait les gaps (coût des stops percés : 0,05 à 0,22 ATR par trade sur SPY) sans créer d'espérance. **Mesuré en D01.6 (K10).**

### K10 — En séance seule, le signal n'a pas de valeur nette sur les ETF ; la nuit joue en sens opposé
*Source : EXP-D01.6 (SPY, XLE ; sortie forcée au close de la dernière barre de séance ; 4 bps).*

- `[OBS]` Sur les entrées de RE-1, sortir avant la nuit donne un brut de +0,127 ATR sur SPY (IC [−0,12 ; +0,39]) et −0,089 sur XLE. Les frais (0,16 et 0,08 ATR) laissent un net de −0,04 et −0,17. Libérée à la clôture : −0,01 et −0,16. Aucun IC > 0.
- `[OBS]` Effet apparié séance − RE-1 : SPY +0,12, XLE −0,19 ATR (IC ∋ 0). Nuits et séances suivantes pèsent sur SPY et portent XLE : pas de prime overnight générale.
- `[OBS]` En séance, le MDD est divisé par deux environ et les IC sont deux fois plus étroits (durée médiane 2 à 3 h contre 48 h).
- `[HYP]` Sur SPY, le brut en séance est du même ordre que les frais (point mort ≈ 4 bps) : la question y est le coût d'exécution, pas le signal seul.

### K11 — Hors crypto, la rente de RE-1 se joue dans le rapport brut / frais en ATR
*Source : EXP-D01.7, partie 2 (CFD sur indices, argent, GBPJPY et CFD sur ETF chez Saxo, coût principal validé par le
porteur).*

- `[OBS]` La géométrie se transpose sur 12 actifs : `leg_atr` médian de 2,85 à 3,43 (BTC 2,82), P75 de `nis_z_100` de 1,03
  à 1,46 (BTC 1,22).
- `[OBS]` **Le brut est faible** : de +0,06 à +0,42 ATR sur 9 actifs, négatif sur 3, contre +0,50 sur BTC. Aucun IC en ATR
  ne dépasse 0.
- `[OBS]` **Le coût en ATR tranche.** Sur les CFD sur indices, l'argent et GBPJPY, l'ATR de 30 min vaut 11 à 34 bps : 4 à
  11 bps y coûtent 0,24 à 0,42 ATR. Sur BTC, 5 bps coûtent 0,14 ATR, et 4 bps coûtent 0,06 à 0,16 ATR sur les ETF.
- `[OBS]` **US30** gagne en brut des deux côtés (+0,44 et +0,20) ; son brut est positif en bps (+7,9 [+0,8 ; +16,0]).
  - À son écart réel chez Saxo (1,4 bp), il donne +0,211 ATR [−0,136 ; +0,556].
  - GER40, au contraire, ne gagne que par ses Longs, portés par la dérive du DAX.
- `[OBS]` **ETF de séance :** le brut vient des gaps de nuit (GDX +0,41 contre +0,02 en séance), sur environ 140 trades.
  C'est la structure de K8 à K10.
- `[HYP]` Une même cinématique produit une rente là où le mouvement qui suit, en ATR, dépasse nettement le coût en ATR.
  Sur des marchés calmes à 30 min, le levier est le coût d'exécution ; ce n'est pas le signal.

### K12 — Hors de sa période de construction, RE-1 perd son avantage sur BTC ; sur l'or, le brut persiste mais les frais l'absorbent
*Source : EXP-D02.0 (rétro-test de RE-1 figée : BTC/USD Bitstamp 2013-2019, CFD or HistData 2009-2019).*

- `[OBS]` BTC 2013-2019 : −0,045 ATR [−0,244 ; +0,157] à 5 bps, contre +0,369 [+0,098 ; +0,645] en 2020-2025. Le brut
  tombe de +0,50 à +0,06 ATR ; les frais (0,10 ATR) ne sont pas en cause.
- `[OBS]` Le timing (moyenne des deux sens) passe de +0,362 à −0,061, F2b de +0,459 à −0,224 ; 2014-2015 portent l'écart,
  2017 est positive (+0,469).
- `[OBS]` Les populations bougent peu (médiane de `leg_atr` 2,59 contre 2,82 ; P75 de `nis_z_100` 1,14 contre 1,22), mais
  la bande > P90 de `nis_z_100`, écartée par le veto, gagne en trades isolés (+0,60 [+0,20 ; +1,03]) quand elle perdait
  en 2020-2025 (−0,40).
- `[OBS]` Or : brut +0,30 ATR sur 2009-2019 (IC > 0 en log) et +0,24 sur 2020-2025, absorbé par 0,26 à 0,29 ATR de frais à
  4 bps ; 2009-2015 positifs chaque année (ATR de 13,5 à 19 bps), 2016-2019 négatifs.
- `[HYP]` L'avantage de RE-1 sur BTC dépend de la période : sélection en échantillon pendant la construction (A01 → C05),
  ou changement de régime ; le rétro-test ne sépare pas les deux. D02 devra mesurer son gain sur ces périodes aussi.

### K13 — Sur BTC, chaque calibration vaut pour son époque ; le walk-forward semestriel ne suit pas le basculement
*Source : EXP-D02 (walk-forward de H, R0 et de la frontière, IS de 24 mois, OOS de 6 mois, 5 bps).*

- `[OBS]` Espérance moyenne par trade (ATR) sur 2015-2019 puis 2020-2025 :
  - RE-1 gelée, construite sur 2020-2025 : +0,064 puis +0,357 ;
  - Statique-R0 (R0 = 200, choisi sur 2013-2014) : +0,301 puis −0,191 ;
  - Statique-conjointe (R0 = 200, H = 36, choisie sur 2013-2014) : +0,337 puis −0,077.
- `[OBS]` WFO-R0 passe de R0 = 200 à 50 en 2017, puis à 100 dès le S2 2018 : +0,205 sur 2015-2019, +0,355 ensuite
  (mêmes trades que le Contrôle). Il manque 2019 (−0,074, contre +0,692 à R0 = 200). Face à RE-1 gelée sur 2015-2025 :
  +0,074 ATR [−0,067 ; +0,225] ; lu dès 2016 : +0,004.
- `[OBS]` Sur 92 comparaisons au coût principal (BTC, SOL, AVAX, or), aucune variante ne surpasse RE-1 gelée et 8 écarts
  d'espérance sont significativement négatifs en ATR, contre 1 positif.
- `[HYP]` La cinématique que RE-1 exploite change de réglage optimal entre les deux époques de BTC (marché spot étroit,
  puis marché à dérivés et ETF). Un recalibrage sur 24 mois réagit trop tard, ou par hasard ; la valeur ajoutée du
  walk-forward n'est pas démontrée avec ce protocole.

### K14 — L'avantage de RE-1 tient à environ deux grands gagnants par an : des expansions de volatilité nées d'états calmes
*Source : EXP-D02.1 (stress du porteur, BTC 2015-2025, 5 bps).*

- `[OBS]` Les 21 meilleurs trades de RE-1 gelée (1 % de 2 075) font 84 % de la somme nette en ATR et 91 % de la croissance
  log du capital à 0,25 %/ATR. Les 5 % meilleurs font 266 % du total, les 10 % meilleurs 409 % : le reste perd environ
  trois fois le résultat final. Le trade médian perd 0,43 ATR.
- `[OBS]` Ces 21 trades sont des mouvements de +196 à +961 bps bruts, ouverts quand l'ATR était bas (32 bps en moyenne,
  contre 57), sans stop touché ; 6 sont plafonnés à 1x. Ils sont répartis sur 10 des 11 années (aucun en 2020).
- `[OBS]` Sans eux, RE-1 gelée fait +0,035 ATR [−0,128 ; +0,199] et +9 % au lieu de +159 % ; à 10 bps en plus, −0,089.
  Toutes les séries de D02 et de D02.1 suivent le même schéma.
- `[HYP]` RE-1 récolte des expansions de volatilité qui partent d'états calmes. Sa robustesse dépend de leur fréquence et
  de leur taille, pas du trade moyen ; les frais et la perte de quelques grands gagnants s'additionnent jusqu'à
  l'effacer.
- `[OBS]` **Nuance (EXP-D03, I-M20) :** le « calme » tient surtout au classement en ATR et à la taille de position. En bps,
  les plus gros gains naissent à ATR haut : par quintile du rang d'ATR, +4,8, +7,4, +15,0, +2,6, +21,2 bps (bas → haut).
  Le filtre ATR ≤ P60 garde les 21 trades du top 1 % mais ne change pas le Calmar (0,34 contre 0,32).

### K15 — Sur 2021-2025, BTC et SOL ne sont pas corrélés sous RE-1 gelée : la diversification améliore le Calmar
*Source : EXP-D03 (portefeuille sur capital commun, 0,25 %/ATR par trade sur chaque actif, 5 bps).*

- `[OBS]` Corrélation des rendements mensuels −0,04. Portefeuille : PnL +163 %, MDD −15,2 %, Calmar 1,58, contre 1,18
  pour BTC seul et 0,59 pour SOL seul ; 59 % de mois positifs contre 54 et 56 %.
- `[OBS]` La plus longue période sous le pic n'est pas raccourcie (238 jours contre 224 pour BTC seul). Exposition brute
  jusqu'à 2,0 ; les deux positions sont ouvertes 7 % du temps.
- `[HYP]` Le gain vient de flux d'avantage indépendants ; il ne vaut que si chacun est réel. Celui de SOL ne l'est pas à
  95 % (+0,190 ATR [−0,079 ; +0,484]), et BTC 2021-2025 est dans la période de construction de RE-1.

---

### K16 — L'exécution des stops pèse plus que la latence ; le stop catastrophe borne la perte d'un trade
*Source : EXP-D03.1 (BTC 2015-2025, SOL 2021-2025, 5 bps, 0,25 %/ATR ; lectures, moteur inchangé).*

- `[OBS]` Entrer une barre plus tard (30 min) ne change rien : +0,014 ATR [−0,025 ; +0,056] sur BTC, +0,002 sur SOL.
- `[OBS]` 23 % des trades sortent sur le stop de F3 ; un glissement de 0,5 ATR sur ces sorties coûte −0,115 ATR par
  trade (BTC) et −0,121 (SOL), la moitié de l'espérance. L'espérance de BTC s'annulerait vers 0,95 ATR de glissement.
- `[OBS]` Un stop de 4 ATR ne touche que des F2b (13 à 14 % des trades) et ramène la pire perte d'un trade de −6,2 % à
  −1,05 % du capital (BTC). Coût : −0,037 ATR [−0,118 ; +0,040] sur 2015-2025, mais −0,121 [−0,237 ; −0,006] sur
  2020-2025 et −9,9 bps [−20,4 ; −1,2] sur SOL ; 89 % des trades coupés auraient fini négatifs.
- `[HYP]` RE-1 n'exploite pas une micro-structure fugace ; son risque d'exécution est la qualité des sorties sur stop.
  Le stop catastrophe est une assurance dont l'historique ne contient pas le sinistre (krach de 20 à 30 % pendant une
  position à 1x).

---

---

### K17 — Hors échantillon, RE-1 garde le signe et le profil de queue ; sa marge reste mince
*Source : EXP-D04 (réserve levée, protocole pré-enregistré ; version finale avec stop catastrophe de 4 ATR ; 5 bps).*

- `[OBS]` ETH +0,183 ATR [−0,010 ; +0,385] et XRP +0,263 [−0,014 ; +0,640] sur 9 à 10 ans ; trade médian −0,97 et −0,65
  ATR ; F3 et F2b positifs sur les deux. Sans le 1 % meilleur : −0,060 et −0,058 (BTC 2015-2025 sans stop : +0,035).
- `[OBS]` Un seul trade de XRP, ouvert le 2023-07-13 (décision SEC contre Ripple), fait +247 ATR, 56 % de la somme et
  +61,9 % du capital : la queue droite contient aussi des sauts de nouvelles, non reproductibles.
- `[OBS]` 2026 (neuf mois) : BTC, SOL, AVAX et l'or tous positifs, +0,41 à +1,06 ATR, l'or compris (net nul en
  échantillon) : régime porteur commun aux actifs.
- `[OBS]` La perte journalière d'un compte peut dépasser la perte maximale d'un trade : ETH −3,03 % le 2020-08-02, un
  gain latent de +4,5 % rendu dans un krach éclair (−0,50 % rapporté au solde réalisé).
- `[HYP]` RE-1 est une récolte de queue droite transportable d'un actif à l'autre ; sa rentabilité dépend de quelques
  événements par an et de l'exécution des stops dans les mouvements extrêmes.

---

### K18 — En portefeuille, la pire journée vient des stops touchés ensemble sur des cryptos corrélées
*Source : EXP-D04.1 (six actifs, capital commun, 0,25 %/ATR par trade, 5 bps ; 2021-10 → 2026-09).*

- `[OBS]` Pire journée −5,20 % sur le capital valorisé de minuit (−4,16 % sur le solde réalisé), contre −2,57 % au pire
  pour un actif seul ; 5 journées sous −4 % en cinq ans.
- `[OBS]` Les pires journées réunissent quatre stops catastrophe de cryptos différentes, touchés dans la même heure
  (2022-11-04, 2025-11-06), à environ −1 % chacun : un même mouvement déclenche le même signal sur des actifs corrélés.
  L'or a compensé une fois (+2,07 %).
- `[OBS]` Une journée de −5,14 % (2026-01-26) n'est qu'un gain latent rendu : positive sur le solde réalisé.
- `[HYP]` La diversification de RE-1 entre cryptos réduit peu le risque d'une journée ; la perte journalière dépend du
  nombre de positions crypto ouvertes ensemble et de la taille par trade.

### K19 — Hors crypto, la queue de 13 h en ATR brut est surtout la saison horaire
*Source : EXP-D05.1 (grille et correction horaire ; séries Saxo et HistData, 2020-2025).*

- `[OBS]` En ATR brut, US100 et US30 ont autant de fenêtres de 13 h à 10 ATR ou plus que BTC (51 et 43 pour 1 000,
  contre 40). Une fois la saison horaire retirée : 17 et 14, contre 35 ; GER40 13, or 15, GBPJPY 15, SOL 20.
- `[OBS]` La persistance (VR(26) de 0,89 à 0,98, BTC le plus bas) et la naissance au calme (77 à 81 % partout) ne
  distinguent pas les marchés de RE-1.
- `[HYP]` Les expansions de 13 h hors heure fixe, le « phénomène crypto », sont deux à trois fois plus rares sur les
  candidats TradFi que sur BTC. Leur queue brute est l'ouverture au comptant rapportée à un ATR de nuit.


## 3. Trois phénomènes captés par le déclencheur
*Hypothèse de travail du porteur, 2026-09-28. Chiffres vérifiés : EXP-A01, annexe I.*

**Idée directrice.** Il s'agit de revenir à la logique physique du Pine V2 (AFK TSO REVERSAL). Le moteur y détecte deux choses : l'arrêt, l'essoufflement ou le retournement d'une tendance en cours, ou bien la direction d'une sortie de range. On greffe ensuite des règles de gestion adaptées à chaque cas.

L'atlas A01 soutient cette lecture à travers le ratio de retracement `retrace_ratio` = `obs_dist_seg_atr` / `leg_atr`. Les seuils 0,5, 0,85 et 2,8 ATR sont un découpage exploratoire : ils ne sont ni optimisés ni validés.

### P1 — Arrêt ou essoufflement d'une vraie tendance
*`retrace_ratio` < 0,5 et `leg_atr` ≥ 2,8 : 1 875 signaux, 25,7 %.*

- `[OBS]` Le marché vient de faire une jambe ample (`leg_atr` médian de 4,73 ATR). Le prix n'en a repris que 1,47 ATR, moins du tiers.
- `[OBS]` x1 n'est pas encore retourné dans 69,7 % des cas. `A_vol` vaut 0,60 et `nis_z_100` 0,29.
- `[OBS]` Quand l'essoufflement n'est qu'une pause (42,8 % de cassures de l'extremum), le prix va au-delà de l'extremum de +1,28 ATR en médiane, +2,40 en moyenne et +5,86 au P90.
- `[HYP]` Sans stop, le Pine V2 restait piégé à contre-tendance pendant cette reprise.
- **Piste d'enveloppe pour l'Étape C, non validée :** un stop structurel placé juste derrière l'extremum du segment (environ 1,5 à 2 ATR). Il coûterait peu quand la tendance reprend, face au potentiel de retracement d'une jambe de 4,7 ATR.
- **Mesuré par B01 :** voir R1 et R3 (§4). P1 mêle les deux, selon que x1 est encore opposé ou déjà retourné.

### P2 — Sortie de range, cassure de compression
*`retrace_ratio` ≥ 0,85 et `leg_atr` < 2,8 : 1 304 signaux, 17,9 %.*

- `[OBS]` Segment comprimé : `leg_atr` médian de 2,06 ATR, `A_vol` bas à 0,47. La barre de signal est impulsive : `nis_z_100` médian de 0,57, x1 déjà retourné dans 82,5 % des cas.
- `[OBS]` La distance déjà parcourue (2,22 ATR) dépasse l'amplitude du segment.
- `[OBS]` Sur l'ensemble des signaux, 934 (12,8 %) ont un `retrace_ratio` ≥ 1 : leur barre de signal clôture au-delà de tout le range du segment qualifiant. Leur `nis_z_100` médian vaut 1,34 et x1 est retourné dans 89,3 % des cas.
- `[OBS]` Dans P2, l'extremum est cassé dans 26,9 % des cas.
- `[HYP]` La normalisation sur 5 barres faisait saturer `trend_strength` sur du bruit plat (`RESEARCH_PHILOSOPHY.md` §4.4.2). Sur ce sous-ensemble, le déclencheur ne joue donc pas un retournement : il détecte la direction d'une sortie de range, malgré le nom du script.
- **Piste d'enveloppe pour l'Étape C, non validée :** un breakout a besoin de temps pour se développer. Cela plaide pour une tenue au-delà du premier repli de l'oscillateur (~13 barres), avec break-even ou stop large, là où la sortie native coupait tôt.
- **Mesuré par B01 :** voir R2 (§4).

### P3 — La zone bleue du Pine V2 : arrêt, puis confirmation
- `[CODE]` Dans le Pine V2, la condition `is_neutral_g` (`trend_strength` dans [−30 ; +30]) reste vraie pendant toute la traversée de la zone bleue. En v2.1, le signal est one-shot, à la première barre neutre.
- `[OBS]` La sortie de la zone bleue vers la zone opposée survient dans 91,2 % des cas, en 2 barres [1 ; 2] (K4).
- `[HYP]` L'entrée en zone bleue détecte l'arrêt de la vitesse précédente. La sortie vers la zone opposée confirme que x1 a basculé dans le nouveau sens : retournement confirmé ou sortie de range validée. Quand l'arrêt échoue, l'extension au-delà de l'extremum (K3) signe la reprise de tendance.

### Signaux hors P1 et P2
*4 117 signaux, 56,4 %.*

- `[OBS]` Profil proche de la moyenne : `leg_atr` de 2,68, distance parcourue de 1,74, extremum cassé dans 35,9 % des cas.
- Ils ne sont pas encore caractérisés.

---

## 4. Trois régimes du déclencheur
*EXP-B01 et sa relecture, 2026-09-28. Source : rapport B01, §5 et annexe I.*

- Regroupement proposé par le porteur après lecture des résultats (post hoc).
- Mesures sur le rendement orienté de open[t+1] à close[t+H], en ATR14(t), sans frais ni stop. Timing au sens de I-M7.
- Entre crochets : IC 95 % par bootstrap de grappes mensuelles.

### B0 — Pris globalement, le signal est symétrique
- `[OBS]` MFE ≈ \|MAE\| à tous les horizons ; gain strict aux barrières ±1,5 ATR : 50,2 %.
- `[OBS]` Timing ≈ 0 en médiane comme en moyenne, de H6 à H48. Seule ressort la dérive du BTC : +0,21 ATR à H48.

### R1 — Essoufflement précoce : F1 ou F5, x1 encore opposé
*1 935 signaux, 26,5 %. Extremum du segment à 1,08 ATR de l'entrée en médiane (F1 : 1,34 ; F5 : 0,76).*
- `[OBS]` Avantage de médiane. Timing médian :
  - +0,16 ATR [+0,10 ; +0,22] à H6, positif 6 années sur 6 ;
  - +0,21 [+0,07 ; +0,32] à H26, 5 années sur 6 ;
  - +0,15 à H48.
- `[OBS]` Pas d'avantage de moyenne : −0,07 [−0,24 ; +0,10] à H26.
- `[OBS]` La queue gauche est plus lourde que la droite. À H26, P90 + P10 = −0,72 ATR en Long et −0,58 en Short (P10 −4,68, P90 +4,04).
- `[OBS]` L'extremum du segment ne tient jusqu'au signal suivant que dans 46,9 % des cas (information, I-M1).
- `[HYP]` Retournement par décélération : gain typique régulier, pertes rares mais larges quand la tendance reprend.
- **Piste C du porteur, non validée :** stop structurel serré derrière l'extremum du segment, horizon borné.
  - Seule l'enveloppe dira si ce stop coupe la queue gauche sans détruire la médiane.
  - Il serait touché environ une fois sur deux avant le signal suivant.
- **Piste testée (EXP-C02), nette de frais, une position à la fois, hors `nis_z_100` Q4 :**
  - `[OBS]` Le stop coupe la queue gauche mais détruit la médiane. R1 H26, stop à l'extremum : P10 −4,7 → −1,6 ATR, médiane +0,09 → −0,81 ATR. Une partie des trajectoires coupées aurait fini dans le sens du signal.
  - `[OBS]` Aucune règle (SL-A de 1 à 5 ATR, SL-B) ne donne d'espérance positive. À 10 bps, tout est négatif.
  - `[OBS]` F5 : positif en bps à court terme, négatif en ATR. 5 bps y coûtent 0,135 ATR par trade.
  - **Décision du porteur (2026-09-29) :** rejet définitif de R1, F1 et F5. `x1_already_flipped_at_t` vrai est un prérequis d'entrée du système, avec les vetos R3 et `nis_z_100` Q4.

### R2 — Sortie de range avec bascule de vitesse : F2b ou F3, x1 déjà retourné
*1 874 signaux, 25,7 %.*
- `[OBS]` Pas d'avantage de médiane : −0,05 à H6, −0,07 à H26, −0,04 à H48.
- `[OBS]` L'avantage de moyenne se construit avec l'horizon :
  - +0,03 à H6 ;
  - +0,17 [−0,01 ; +0,34] à H26 ;
  - +0,28 [+0,03 ; +0,50] à H48, positif 5 années sur 6 (2024 négative), +0,23 en moyenne winsorisée.
- `[OBS]` Asymétrie moyenne MFE − \|MAE\| : +0,49 ATR à H48, contre +0,03 pour l'ensemble des signaux.
- `[OBS]` La queue droite est plus longue des deux côtés : P90 + P10 = +0,80 en Long et +0,87 en Short à H26.
- `[OBS]` Les deux queues sont aussi plus larges en ATR(t) que pour l'ensemble des signaux : P10 −6,82 et P90 +7,65 à H48, contre −6,47 et +6,47.
- `[OBS]` Chaque sous-famille ne porte qu'un sens. À H48, écart à l'ensemble des signaux du même sens :
  - F3 · x1 déjà retourné : +0,62 ATR en Short, −0,11 en Long ;
  - F2b · x1 déjà retourné : +0,81 en Long, −0,12 en Short.
- `[HYP]` Breakout de compression : faux départs fréquents, espérance portée par la queue droite.
- `[HYP]` Le sens propre à chaque sous-famille pourrait suivre la tendance de l'unité de temps supérieure.
- **Piste C du porteur :** tenue de 26 à 48 barres, stop large ou break-even différé.
  - Retenus : la tenue à H26 et le stop différencié (C01 à C02bis).
  - Break-even différé : sans valeur marginale (C03).
- **Pistes testées (EXP-C01, EXP-C02), nettes de 5 bps, une position à la fois, hors `nis_z_100` Q4 :**
  - `[OBS]` **F2b · x1 déjà retourné, sortie à H26 sans stop.**
    - +0,389 ATR [+0,079 ; +0,700] par trade (+11,5 bps), inchangé après winsorisation.
    - +72 %, drawdown −13 % à 0,25 % par ATR.
    - Chaque stop le dégrade, de 0,15 à 0,38 ATR : 54 % des trades passent par −2 ATR puis finissent à −1,4 ATR en moyenne.
  - `[OBS]` **F3 · x1 déjà retourné, stop à l'extremum du segment.**
    - À H26 : drawdown −34 % → −13 %, 6 années positives sur 6, Long et Short positifs.
    - Sans stop, les trades qui touchent l'extremum finissent à −2,2 ATR.
  - `[OBS]` **Moteur de régimes (EXP-C02bis)** : F2b sans stop, F3 stop à l'extremum, cooldown après stop, H26.
    - +0,369 ATR [+0,098 ; +0,645], +138 %, drawdown −13,5 %, Calmar 1,16, 6 années positives sur 6.
    - Même espérance que R2 uniforme : effet apparié +0,015 ATR [−0,108 ; +0,141]. Le gain porte sur le risque.
    - Plateau : IC > 0 de H20 à H32. Le résultat tient avec des seuils causaux (en ATR).
    - Le cooldown fait mieux que la réouverture jusqu'à H32. Un stop de catastrophe sur F2b coûte 0,08 ATR par trade.
    - `[OBS]` **Filtrage mutuel sous pyramiding 0.** Un signal contraire à la position ouverte de l'autre sous-famille est ignoré. Joués seuls, ces signaux contraires perdaient :
      - F3 contre un F2b ouvert : 59 trades, −1,22 ATR sans stop, −0,49 avec le stop ;
      - F2b contre un F3 ouvert : 44 trades, −0,38 ATR.

      Les signaux de même sens évincés ne perdaient pas (F3 +0,71 ; F2b −0,01). Dans le moteur, F2b passe de +0,389 à +0,459 ATR, et F3 de +0,236 à +0,267 avec stop (+0,144 → +0,235 sans stop). H26, 5 bps.
    - `[HYP]` Le contre-signal de l'autre sous-famille tombe pendant l'expansion du breakout en cours et se trompe de sens. Une position à la fois le filtre sans règle supplémentaire.
    - **Décision du porteur (2026-09-29) :** RE-1 validé comme configuration de référence de l'Étape C. H = 26 est commun aux deux sous-familles et verrouillé. Le take-profit fixe est exclu.
    - `[OBS]` **Filtre de tendance macro (EXP-C04) : les trades contre-tendance ne sont pas toxiques.**
      - Les trades de RE-1 contre la tendance, qu'elle soit mesurée par l'EMA 200, l'EMA 50 ou x1 d'un Kalman sur 4 h, valent autant que les alignés, voire plus : +0,39 à +0,43 ATR, contre +0,32 à +0,35.
      - Ils portent jusqu'à 48 % du décile supérieur et 9 des 20 meilleurs trades.
      - F2b contre-tendance est le meilleur groupe (+0,52 à +0,58). Les Long contre la tendance 4 h font +0,64.
      - Le veto dégrade l'espérance (+0,369 → +0,22 à +0,26) et le Calmar (1,16 → 0,41 à 0,49). RE-1 reste pur.
    - `[OBS]` **Les signaux qui tombent pendant la fenêtre d'un signal précédent perdent**, que ce signal ait été pris ou non : −0,48 ATR après un veto EMA 200. C'est le même phénomène que les réouvertures après stop de C02bis.
    - `[HYP]` Le retournement de x1 dans R2 hors Q4 anticipe déjà le changement de régime. Une tendance plus lente n'arrive qu'après, et le veto retire les V de la queue droite.
    - `[OBS]` **Break-even différé (EXP-C03) : aucun seuil n'améliore l'espérance de RE-1.**
      - m ≤ 1,5 ATR la dégrade, surtout sur F2b ; m ≥ 2 est neutre (−0,02 à +0,03 ATR, IC ±0,1).
      - Sauvés et coupés s'équilibrent : pour V3 à m = 2, +0,270 contre −0,288 ATR par trade.
      - La baisse du drawdown (V3 à m = 2 : −13,5 → −11,7 %) n'est pas significative (I-M10).
    - `[OBS]` **Take-profit fixe.** Même la borne optimiste (TP pris dès que la MFE26 l'atteint) reste sous RE-1 : +0,200 à +0,347 ATR contre +0,369. Le décile supérieur apporte 0,92 ATR par trade, plus que l'espérance totale.
    - `[HYP]` Le break-even ne distingue pas le retest de l'échec : un trade activé sur deux repasse par l'entrée, et ceux qui repartent ensuite valent ceux qu'il sauve.
    - `[OBS]` **Analyse approfondie (C03) : ni alpha, ni gain de risque démontré.**
      - V3 à m = 2 baisse le MDD sur le chemin réel (6 lectures sur 6), mais seulement dans 82 à 92 % des chemins réordonnés, et le Calmar dans 65 à 82 %.
      - Ses drawdowns sont plus longs (459 jours contre 390).
      - Dès 5 bps de glissement du break-even, un RE-1 simplement réduit en taille fait mieux à MDD égal (I-M11).
      - Le déficit de 2022 (−0,184 ATR) tient à deux gagnants F3 extrêmes coupés (+18,6 et +14,3 ATR dans RE-1) ; sans eux, +0,006.
      - Sur F3, le SL-B plafonne déjà ce que le break-even pourrait sauver. Ses 10 plus grands gains sont des F2b.
    - `[HYP]` Le break-even, à l'entrée + 5 bps, se trouve dans la zone de retest des breakouts. Son coût annuel dépend de la probabilité de couper l'un des rares gagnants extrêmes qui portent l'espérance.
    - `[OBS]` **Sensibilité des trois seuils de RE-1 (EXP-C05), un seuil à la fois, H26, 5 bps.**
      - **Frontière F2b / F3 :** plateau de 0,85 à 0,95 (espérance +0,369 à +0,396, MDD −13,4 à −14,2 %). À 0,75 : −0,095 ATR [−0,157 ; −0,030], MDD −19,2 %.
      - **Mécanisme :** le stop à l'extremum coûte 0,53 à 0,58 ATR par trade sur les retracements de 0,75 à 0,85, qui font +0,9 à +1,0 ATR sans stop. Il ne devient neutre qu'à partir de 0,90, et n'est positif, sans être significatif, qu'au-delà de 0,95.
      - **Marge du stop de F3 :** plateau de −0,25 à +0,25 ATR (effets de ±0,015 ATR). +0,50 coûte 0,036.
      - **Exclusion de `nis_z_100` :** RE-1 est au sommet. Relâchée, −0,06 (P80) à −0,15 ATR (P90), significatif ; resserrée (P70), −0,02, non significatif. C'est une falaise d'un côté, signalée avant l'Étape D.
      - Par signal joué seul, l'espérance passe de +0,53 (P70-P75) à −0,30 (P75-P80), avec des IC qui se recouvrent. La part de F3 monte de 74 à 96 % au-delà de P75.
    - `[HYP]` Le retour à l'extremum n'invalide le breakout qu'après un retracement presque complet de la jambe précédente (≥ 0,90-0,95). En dessous, c'est un retest : c'est le mécanisme de F2b, qui s'étend jusqu'à 0,85.
  - `[HYP]` Le point d'entrée dans le range décide.
    - F2b entre au milieu : un repli de 1 à 3 ATR est un balayage de liquidité avant l'expansion.
    - F3 entre près de l'extrémité opposée : casser l'extremum invalide le breakout.

### R3 — Continuation : F1 avec x1 déjà retourné, F2a, F4
*2 347 signaux, 32,2 %.*
- `[OBS]` Anti-timing en médiane comme en moyenne :
  - timing médian −0,11 [−0,22 ; −0,02] à H26, négatif 6 années sur 6 ;
  - timing moyen −0,29 [−0,48 ; −0,07] à H48, négatif 6 années sur 6.
- `[OBS]` Les deux sens font moins bien que l'ensemble des signaux à H48 : −0,21 ATR en Long, −0,35 en Short.
- `[OBS]` `nis_z_100` Q4 (1 824 signaux, qui recoupent R1 et R2) : continuation nette jusqu'à H26 (timing moyen −0,25 [−0,39 ; −0,09]), effacée en moyenne à H48 (−0,02).
- `[HYP]` Signal tardif, après une grande jambe ou sur une bougie de choc : la tendance précédente reprend.
- **Piste C du porteur, non validée :** exclusion en mode retournement ; test dédié d'une entrée en continuation.
- **Piste testée (EXP-C01) :**
  - `[OBS]` Dans le sens du signal, R3 et `nis_z_100` Q4 perdent : IC entièrement négatifs de H6 à H26.
  - `[OBS]` En continuation, R3 fait +10,3 bps [+1,3 ; +19,8] à H26, porté par 2020-2021.
  - **Décision du porteur (2026-09-29) :** continuation écartée. R3 et `nis_z_100` Q4 ne servent que de filtres d'exclusion.

### Hors R1-R3
*1 140 signaux, 15,6 % : F2b ou F3 avec x1 encore opposé, F5 avec x1 déjà retourné.*
- `[OBS]` Timing médian et moyen entre −0,03 et +0,11 ATR, IC contenant 0 à tous les horizons.

### Limites
- Les regroupements sont post hoc. Leur tenue hors échantillon (autre actif, nouveau hold-out) n'est pas établie.
- Rien n'intègre ici les frais ni un stop. Les écarts mesurés (0,1 à 0,3 ATR) ont l'ordre de grandeur des frictions (0,1 à 0,2 ATR).
- Les autres questions posées à B01 n'ont pas révélé d'avantage net : répétitions (`run_rank` > 1) et divergence de cycle (`cycle_seg_div_atr` > 0) donnent un gain strict ±1,5 de 50,0 % et 50,4 %.

---

## 5. Questions ouvertes
*Rien n'est lancé.*

1. ~~R1 : un stop serré à l'extremum du segment améliore-t-il la distribution, ou coupe-t-il surtout des trajectoires qui auraient fini dans le sens du signal ?~~ **Répondu (EXP-C02)** : il coupe surtout des trajectoires qui auraient fini dans le sens du signal ; aucune espérance positive.
2. ~~R2 : combien de temps laisser courir, et avec quel stop ?~~ **Répondu (EXP-C01 à C02bis)** : H26, avec un plateau de H20 à H32 ; F2b sans stop, F3 stop à l'extremum. H = 26 est verrouillé par le porteur.
3. ~~R2 : le sens favorable de F3 (Short) et de F2b (Long) dépend-il de la tendance de l'unité de temps supérieure ?~~ **Répondu (EXP-C04)** : non. Dans RE-1, les trades contre la tendance (EMA 200, EMA 50, Kalman 4 h) valent autant que les alignés, voire plus. Avec un stop à l'extremum, F3 est positif des deux côtés (C02).
4. ~~R3 et `nis_z_100` Q4 : faut-il seulement les exclure, ou les prendre en continuation ?~~ **Tranché par le porteur (EXP-C01)** : exclusion seulement.
5. ~~Après un stop, faut-il un cooldown jusqu'à t + 1 + H ou une réouverture immédiate ?~~ **Répondu (EXP-C02bis)** : le cooldown, jusqu'à H32 ; à H48, l'écart s'inverse.
6. L'assemblage différencié de R2 tient-il avec des seuils causaux, puis hors échantillon ? **En partie répondu (EXP-C02bis, EXP-D01)** : il tient avec des seuils causaux, en ATR. Transféré tel quel (D01, descriptif) : sa population se retrouve sur SOL/USD et sur l'or ; l'espérance nette est positive sur SOL (IC contenant zéro) et nulle sur l'or. Hold-out : validation finale.
7. ~~Faut-il un horizon propre à chaque sous-famille ?~~ **Tranché par le porteur (2026-09-29)** : non, H = 26 est commun. À H28, F2b monte à +0,569 ATR, mais F3 tombe à +0,148, le DD passe à −16,2 % et le Calmar à 0,92. Ce serait un paramètre libre choisi après lecture.
8. ~~Un break-even ou un take-profit améliore-t-il RE-1 ?~~ **Répondu (EXP-C03 et son analyse approfondie)** : non. Le break-even est neutre pour m ≥ 2 et nuisible en dessous. Comme outil de risque, il équivaut à une réduction de taille et ne résiste pas à 5 bps de glissement. Même la borne optimiste du take-profit reste sous RE-1.
9. ~~Un filtre de tendance macro améliore-t-il RE-1 ?~~ **Répondu (EXP-C04)** : non. Les trades contre-tendance ne sont pas toxiques, et le veto retire des V de la queue droite. En séquentiel, il fait en plus entrer des signaux perdants.
10. ~~Les seuils durs de RE-1 reposent-ils sur des plateaux ?~~ **Répondu (EXP-C05)** : oui pour la frontière F2b / F3 (0,85 à 0,95) et pour la marge du stop de F3 (−0,25 à +0,25 ATR). L'exclusion de `nis_z_100` est une falaise côté permissif, signalée avant l'Étape D.
11. ~~La bascule d'espérance de `nis_z_100` au voisinage de P75 se retrouve-t-elle sur les autres actifs ?~~ **Mesuré (EXP-D01, trades isolés)** : pas telle quelle. Sur SOL, la bande sous P70 est positive (IC > 0), mais la bande au-delà de P90 l'est aussi ; sur l'or, les bandes sont nulles ou négatives. Aucun réglage.
12. Quelle échelle de temps rend le rapport frais / ATR compatible avec l'or (brut +0,24 ATR, frais 0,26 ATR à 30 min) ? Question de vitesse : H et R0 en D02, ou unité de temps des barres (hors périmètre de D02 tel qu'annoncé). **Mesuré pour H (EXP-D01.5) :** allonger H ne dilue pas les frais, qui restent à 0,26 ATR par trade ; le brut ne croît pas (+0,24 → −0,45 ATR de H = 26 à 130). **Mesuré pour R0, H et la frontière en walk-forward (EXP-D02) :** sur 2011-2025, toutes les séries perdent à 4 bps (−0,045 à −0,196 ATR), et R0 recalibré fait pire que le Contrôle (−0,150 [−0,294 ; −0,021]). Reste l'unité de temps des barres.
13. L'inversion F2b / F3 de l'or (F2b Short −0,70, F3 Long +0,55) tient-elle à la hausse séculaire de 2020-2025 (dérive +0,38 ATR) ou à la microstructure d'un CFD ? Non testé.
14. ~~WTI : quelle source pour 2020-2025 ?~~ **Tranché par le porteur (2026-09-30)** : WTI retiré de D01, remplacé par l'ETF XLE (corrélation quotidienne 0,46 avec le spot WTI, 0,60 avec SPY).
15. Sur une série en séances, H doit-il se compter en barres ou en temps, et faut-il sortir avant la nuit ? D01 bis montre des trades traversant deux nuits, les gaps pesant 35 à 47 % de leur amplitude. Question pour D02, à cadrer : H est l'un des deux paramètres autorisés. **Mesuré (EXP-D01.5) :** H = 13 traverse encore une nuit (91 % des trades) ; H = 6 réduit l'exposition de moitié, mais la composante en séance est ≈ 0 (SPY) ou négative (XLE) : sortir avant la nuit ne créerait pas d'espérance (K9). **Mesuré (EXP-D01.6) :** la sortie de fin de séance donne un net de −0,04 (SPY) et −0,17 ATR (XLE), sans IC > 0, avec un MDD divisé par deux (K10).
16. La queue droite de RE-1 (21 trades, 1 %, font 84 % de l'espérance en ATR ; ouverts à ATR bas, K14) se laisse-t-elle cibler à t, ou seulement attendre ? **Décrit (EXP-D03) :** ni la compression (Bollinger, ATR), ni %B, ni l'EMA 200, ni `leg_atr` ne la séparent une fois l'artefact du classement en ATR écarté (I-M20) ; le filtre ATR ≤ P60 ne change pas le Calmar.
17. Le contraste horaire de RE-1 sur BTC (04-08 h UTC +0,689 ATR, 16-20 h −0,205 ; EXP-D03, descriptif, sans IC) se retrouve-t-il sur des données non vues (SOL, BTC 2013-2014) ? Non testé.
