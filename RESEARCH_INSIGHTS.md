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

### P2 — Sortie de range, cassure de compression
*`retrace_ratio` ≥ 0,85 et `leg_atr` < 2,8 : 1 304 signaux, 17,9 %.*

- `[OBS]` Segment comprimé : `leg_atr` médian de 2,06 ATR, `A_vol` bas à 0,47. La barre de signal est impulsive : `nis_z_100` médian de 0,57, x1 déjà retourné dans 82,5 % des cas.
- `[OBS]` La distance déjà parcourue (2,22 ATR) dépasse l'amplitude du segment.
- `[OBS]` Sur l'ensemble des signaux, 934 (12,8 %) ont un `retrace_ratio` ≥ 1 : leur barre de signal clôture au-delà de tout le range du segment qualifiant. Leur `nis_z_100` médian vaut 1,34 et x1 est retourné dans 89,3 % des cas.
- `[OBS]` Dans P2, l'extremum est cassé dans 26,9 % des cas.
- `[HYP]` La normalisation sur 5 barres faisait saturer `trend_strength` sur du bruit plat (`RESEARCH_PHILOSOPHY.md` §4.4.2). Sur ce sous-ensemble, le déclencheur ne joue donc pas un retournement : il détecte la direction d'une sortie de range, malgré le nom du script.
- **Piste d'enveloppe pour l'Étape C, non validée :** un breakout a besoin de temps pour se développer. Cela plaide pour une tenue au-delà du premier repli de l'oscillateur (~13 barres), avec break-even ou stop large, là où la sortie native coupait tôt.

### P3 — La zone bleue du Pine V2 : arrêt, puis confirmation
- `[CODE]` Dans le Pine V2, la condition `is_neutral_g` (`trend_strength` dans [−30 ; +30]) reste vraie pendant toute la traversée de la zone bleue. En v2.1, le signal est one-shot, à la première barre neutre.
- `[OBS]` La sortie de la zone bleue vers la zone opposée survient dans 91,2 % des cas, en 2 barres [1 ; 2] (K4).
- `[HYP]` L'entrée en zone bleue détecte l'arrêt de la vitesse précédente. La sortie vers la zone opposée confirme que x1 a basculé dans le nouveau sens : retournement confirmé ou sortie de range validée. Quand l'arrêt échoue, l'extension au-delà de l'extremum (K3) signe la reprise de tendance.

### Signaux hors P1 et P2
*4 117 signaux, 56,4 %.*

- `[OBS]` Profil proche de la moyenne : `leg_atr` de 2,68, distance parcourue de 1,74, extremum cassé dans 35,9 % des cas.
- Ils ne sont pas encore caractérisés.

---

## 4. Questions ouvertes pour EXP-B01
*À mesurer sans a priori, avec la cible I-M2. Rien n'est lancé.*

1. L'avantage d'excursion, MFE_H contre \|MAE_H\|, se concentre-t-il dans l'essoufflement ou le retournement d'une vraie tendance ? Descripteurs : `leg_atr` élevé, `retrace_ratio` bas ou modéré, `decel_ratio`.
2. Se concentre-t-il dans les sorties de range ? Descripteurs : `leg_atr` et `A_vol` comprimés, `retrace_ratio` ≥ 0,85.
3. Se concentre-t-il dans l'épuisement à deux jambes ou la divergence de cycle ? Descripteurs : `run_rank` > 1, `cycle_seg_div_atr` > 0.
4. À l'inverse, quels signaux ont une excursion négative, c'est-à-dire continuent dans le sens de la tendance précédente ? Candidats : pauses en tendance, chocs extrêmes `nis_z_100` Q4.
