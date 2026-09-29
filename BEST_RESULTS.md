# BEST RESULTS — les meilleurs résultats de chaque étape

> Aide-mémoire : les deux ou trois résultats les plus utiles de chaque étape, avec leur statut. Le détail est dans `RESEARCH_LOG.md`, la lecture dans `RESEARCH_INSIGHTS.md`, les chiffres dans `experiments/<expérience>/`.
>
> Tout porte sur BTC/USD 30 min, 2020-2025, **dans l'échantillon**. Aucun résultat n'est validé hors échantillon : le hold-out (BTC 2026, ETH, XRP) reste scellé jusqu'à la fin de l'Étape D.
>
> **Conventions :**
> - PnL nets de frais ; une position à la fois ;
> - capital à 0,25 % par ATR14(t), levier ≤ 1x, sauf mention « 1x » ;
> - IC 95 % par bootstrap de grappes mensuelles.
>
> Mis à jour après chaque expérience.

---

## Configuration candidate du moment
*Issue de la relecture de C02 (rapport C02 §5.3) et vérifiée avec le moteur du dépôt. Elle reste à confirmer en EXP-C02bis : plateau d'horizon, seuils causaux, règle de réentrée.*

- **Signaux :** R2 hors `nis_z_100` Q4.
- **Sortie :** à H26, avec une enveloppe par sous-famille, connue à t :
  - F2b · x1 déjà retourné (retracement de 0,50 à 0,85) : sans stop ;
  - F3 · x1 déjà retourné (retracement ≥ 0,85) : stop à l'extremum du segment qualifiant.
- **Après un stop :** cooldown jusqu'à t + 1 + H.

| Métrique | 5 bps | 10 bps |
|---|---|---|
| PnL net total : composé à 0,25 %/ATR ; 1x ; bps cumulés (1x) | +138 % ; +204 % ; +13 320 bps | +72 % ; +77 % ; +7 920 bps |
| Profit factor : 1x ; pondéré | 1,20 ; 1,28 | 1,11 ; 1,17 |
| Win rate | 44,3 % | 42,8 % |
| Espérance par trade : ATR [IC] | +0,369 [+0,098 ; +0,645] | +0,233 [−0,041 ; +0,511] |
| Espérance par trade : bps [IC] | +12,3 [+0,2 ; +24,4] | +7,3 [−4,8 ; +19,4] |
| Max drawdown valorisé : 0,25 %/ATR ; 1x | −13,5 % ; −43,9 % | −15,9 % ; −48,0 % |
| Trades | 1 080 (15,0 par mois), dont 24 % stoppés | idem |
| Durée médiane | 26 barres (13 h) | idem |
| Part des frais (1x) ; brut par trade | 29 % ; +17,3 bps | 58 % ; +17,3 bps |
| Années positives | 6 sur 6 | 5 sur 6 (2021) |

**À garder en tête :**
- Face à R2 hors Q4 sans stop, sur les mêmes entrées, l'espérance ne change pas : effet apparié +0,015 ATR [−0,108 ; +0,141]. Le gain porte sur le drawdown (−20,5 % → −13,5 %) et la régularité.
- La règle de F3 a été choisie après lecture de C02.
- À 10 bps, l'IC contient 0.

---

## Point de départ — Phase 0
- **Mécanique native v2.1** (stop-and-reverse, 5 bps) : 6 037 trades (84 par mois), −5,3 bps par trade, PF 0,907, capital −98,7 %. Les frais cumulés (≈ 30 200 bps) écrasent un PnL brut déjà négatif (−2 047 bps).
- C'est la référence reproduite à l'identique (ancre P6.5d), non une piste.

## Étape A — Anatomie (EXP-A01, descriptive)
1. **Géométrie stationnaire en ATR14(t).** Distances et durées sont stables de 2020 à 2025 en ATR, alors que l'ATR14 médian varie de 34 à 80 bps selon l'année. Toute l'enveloppe s'exprime donc en ATR14(t), d'où la convention de capital à 0,25 % par ATR.
2. **Le déclencheur mêle retournement et décélération.**
   - Le signal arrive environ 5 barres après l'extremum de prix.
   - Il tombe au passage à zéro de la vitesse x1, ou 1 à 2 barres avant, dans 64,5 % des cas.
   - x1 est déjà du sens du signal dans 51,8 % des cas. D'où `x1_already_flipped_at_t`, qui sépare R1 de R2.
3. **La tenue de l'extremum n'est pas une cible** (I-M1). Elle croît mécaniquement avec la distance déjà parcourue : 36,5 % au premier quartile, 85,3 % au dernier. La cible de B est l'asymétrie d'excursion.

## Étape B — Catégorisation (EXP-B01 et relecture, sans frais ni stop)
1. **Trois régimes du déclencheur :**
   - R1, essoufflement : médiane positive, queue gauche ;
   - R2, sortie de range : moyenne positive à 26-48 barres, queue droite ;
   - R3, continuation.
2. **R2 à H48 :** timing moyen +0,28 ATR [+0,03 ; +0,50], 5 années positives sur 6. F2b porte le Long (+0,81 ATR d'écart à l'ensemble), F3 le Short (+0,62).
3. **Signatures de continuation, devenues filtres d'exclusion :**
   - R3 : timing moyen −0,29 ATR [−0,48 ; −0,07] à H48, négatif 6 années sur 6 ;
   - `nis_z_100` Q4 : −0,25 [−0,39 ; −0,09] à H26.

## Étape C — Enveloppe

### EXP-C01 — sortie à horizon fixe et régimes (5 bps)
1. **F2b · x1 déjà retourné hors Q4, H26, sans stop.**
   - Espérance : +11,5 bps [−2,9 ; +26,0] ; +0,389 ATR [+0,079 ; +0,700], inchangée après winsorisation.
   - +72 %, drawdown −13 % ; 639 trades (8,9 par mois) ; 5 années positives sur 6.
   - 10 bps : +0,255 ATR, +42 %.
   - Le gain vient de l'éviction pure de `nis_z_100` Q4 (contrôle A).
2. **R2 hors Q4, H26, sans stop.** +12,3 bps [−1,5 ; +25,8] ; +0,354 ATR [+0,051 ; +0,643] ; +122 %, drawdown −20,5 % ; 1 080 trades (15 par mois).
3. **Éviction de `nis_z_100` Q4 :** c'est le filtre le plus régulier, qui améliore 18 comparaisons sur 20.

### EXP-C02 — stop-loss par sous-famille (5 bps, séquentiel)
1. **F3 · x1 déjà retourné hors Q4, H26, stop à l'extremum du segment.**
   - Drawdown −34 % → −13 %.
   - PnL +16 % → +36 %, et +41 % en cooldown.
   - 6 années positives sur 6 ; Long et Short positifs.
   - Espérance +0,202 ATR [−0,106 ; +0,520].
2. **F2b : aucun stop.** Chaque stop coûte 0,15 à 0,38 ATR par trade ; l'effet apparié est négatif pour 10 règles sur 11. La moitié des trades passent par −2 ATR avant l'expansion.
3. **R2 hors Q4, H26, SL-A 5 ATR.** C'est la seule configuration avec stop dont l'IC en ATR est positif : +0,286 [+0,019 ; +0,562], +93 %, drawdown −18 %.

La relecture de C02 assemble 1 et 2 : c'est la configuration candidate du moment (en tête de fichier).

---

## Pistes écartées (à ne pas retester sans élément nouveau)

| Piste | Raison | Source |
|---|---|---|
| Stop-and-reverse natif | −98,7 % ; frais ≈ 30 200 bps pour un brut de −2 047 bps | Phase 0 |
| Tous les signaux à horizon fixe | −3,7 à −16,0 bps par trade de H6 à H48 | C01 |
| Entrée en continuation (R3, `nis_z_100` Q4) | +10,3 bps [+1,3 ; +19,8] à H26 seulement, porté par 2020-2021 ; écartée par le porteur | C01 |
| R1, F1, F5 (x1 encore opposé) | aucune espérance nette positive, avec ou sans stop ; les frais coûtent 0,135 ATR par trade sur F5 ; rejet définitif proposé par la relecture | C02 |
| Stop sur F2b | coupe les gagnants : −0,15 à −0,38 ATR par trade | C02 |
