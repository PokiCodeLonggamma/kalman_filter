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

---

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
  - Relecture du porteur : rejet définitif proposé, avec un veto d'entrée si x1 n'est pas retourné. À acter dans le cadrage de C02bis.

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
- **Piste C du porteur, non validée :** tenue de 26 à 48 barres, stop large ou break-even différé.
- **Pistes testées (EXP-C01, EXP-C02), nettes de 5 bps, une position à la fois, hors `nis_z_100` Q4 :**
  - `[OBS]` **F2b · x1 déjà retourné, sortie à H26 sans stop.**
    - +0,389 ATR [+0,079 ; +0,700] par trade (+11,5 bps), inchangé après winsorisation.
    - +72 %, drawdown −13 % à 0,25 % par ATR.
    - Chaque stop le dégrade, de 0,15 à 0,38 ATR : 54 % des trades passent par −2 ATR puis finissent à −1,4 ATR en moyenne.
  - `[OBS]` **F3 · x1 déjà retourné, stop à l'extremum du segment.**
    - À H26 : drawdown −34 % → −13 %, 6 années positives sur 6, Long et Short positifs.
    - Sans stop, les trades qui touchent l'extremum finissent à −2,2 ATR.
  - `[OBS]` **Assemblage à H26** (F2b sans stop, F3 stop à l'extremum) : +0,369 ATR [+0,098 ; +0,645], +138 %, drawdown −13,5 %, 6 années sur 6. Le gain sur R2 uniforme porte sur le drawdown, pas sur l'espérance.
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
2. R2 : combien de temps laisser courir, et avec quel stop ? **En partie répondu (EXP-C01, EXP-C02)** : H26 ; F2b sans stop, F3 stop à l'extremum. Reste à vérifier le plateau d'horizon autour de 26 barres *(C02bis)*.
3. R2 : le sens favorable de F3 (Short) et de F2b (Long) dépend-il de la tendance de l'unité de temps supérieure ? *(caractérisation)* Avec un stop à l'extremum, F3 devient positif des deux côtés (estimations centrales, IC contenant 0). `[HYP]` Son asymétrie tiendrait en partie à ses échecs non coupés.
4. ~~R3 et `nis_z_100` Q4 : faut-il seulement les exclure, ou les prendre en continuation ?~~ **Tranché par le porteur (EXP-C01)** : exclusion seulement.
5. Après un stop, faut-il un cooldown jusqu'à t + 1 + H ou une réouverture immédiate ? *(C02bis)*
6. L'assemblage différencié de R2 tient-il avec des seuils causaux, puis hors échantillon ? *(C02bis, puis Étape D)*
