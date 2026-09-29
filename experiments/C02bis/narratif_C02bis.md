# EXP-C02bis — Moteur de régimes sur R2 hors `nis_z_100` Q4 : une enveloppe par sous-famille

- **Date :** 2026-09-29. **Étape :** C, enveloppe mécanique (assemblage après C02).
- **Actif et période :** BTC/USD Bitstamp 30 min, 2020-01 → 2025-12 (72 mois). 2026, ETH et XRP ne sont pas lus.
- **Architecture (décisions du porteur, 2026-09-29) :**
  - vetos d'entrée : `x1_already_flipped_at_t` faux (R1, rejeté définitivement), R3, `nis_z_100` Q4. Seuls les 1 452 signaux de R2 hors Q4 sont pris ;
  - routage causal à t : F2b · x1 déjà retourné (retracement 0,50 à 0,85 ; 741 signaux) et F3 · x1 déjà retourné (≥ 0,85 ; 711 signaux) reçoivent chacun leur enveloppe ;
  - une seule position à la fois pour tout le moteur (pyramiding 0) ; après un stop, cooldown jusqu'à t + 1 + H ou réouverture immédiate.
- **Frais :** 5 bps (exécution maker ou perp VIP) et 10 bps (taker pur).
- **Capital :** 1 ATR14(t) = 0,25 % du capital, levier ≤ 1x ; notionnel 1x en référence.
- **Reproduire :** `python experiments/C02bis/run_C02bis.py` (≈ 100 s) ; `--rapport` régénère ce rapport depuis les CSV ; tests : `python -m pytest tests`.

## 0. Cadrage

- **QUESTION :** en exécution séquentielle globale (une position à la fois), le moteur de régimes différencié forme-t-il un assemblage causal cohérent ? Il route F2b vers une sortie à H sans stop, et F3 vers un stop propre (SL-B à l'extremum du segment ou SL-A 2 ATR), avec un cooldown après stop. Plus précisément :
  1. fait-il mieux que F2b seul (C1) et que R2 hors Q4 uniforme sans stop (C2) ;
  2. H = 26 est-il un plateau (H ∈ {20, 24, 26, 28, 32}) ou un pic, et que se passe-t-il à H = 13 et 48 ;
  3. le cooldown fait-il mieux que la réouverture immédiate ;
  4. un stop de catastrophe sur F2b (RE-3) coûte-t-il ;
  5. l'avantage tient-il avec des seuils causaux (RE-4) ?
- **PERTINENCE POUR LE FILTRE AKF :** F2b et F3 se distinguent par la part de la jambe déjà reprise au signal (`retrace_ratio`, connu à t). En C02, ils ont répondu en sens contraire au stop. Le moteur exploite cette information causale au lieu d'appliquer une enveloppe uniforme.
- **CE QUE LE PROTOCOLE MESURE RÉELLEMENT :**
  - les 8 métriques nettes à 5 et 10 bps, les IC 95 % en bps et en ATR (espérance et timing), le Long / Short ;
  - la contribution de chaque sous-famille, la stabilité annuelle, le Calmar à 0,25 % par ATR ;
  - l'effet apparié de chaque routage face à C2 sur les mêmes entrées (lecture cooldown) ;
  - l'écart entre cooldown et réouverture, et les masques recalculés avec des seuils causaux.
- **CE QU'IL NE PERMET PAS DE CONCLURE :**
  - une validation hors échantillon : les règles de F2b et F3 ont été choisies après lecture de C02, sur les mêmes données ;
  - un plateau au sens de l'Étape D : 5 horizons, un seul actif, paramètres fixes sur 6 ans ;
  - l'effet d'un take-profit, d'un break-even ou d'un filtre macro ;
  - la tenue d'un H propre à chaque sous-famille, non testée : un seul H par configuration.

Les constats de C02 transmis avec ce cadrage ont été vérifiés au rapport C02 (§5). Deux chiffres y sont nuancés :
- le drawdown de F2b avec un stop de 1 à 3 ATR va de −12 à −22 % (et non de −15 à −22 %) ;
- 25 % des trades de F2b passés par −2 ATR finissent positifs nets (27 % en brut).

## 1. [CODE] Implémentation et contrôles

- **`src/envelope/stops.py`**
  - `rule_levels` donne le niveau d'une règle pour chaque signal : sans stop, SL-A ou SL-B.
  - `route_levels` donne à chaque signal le niveau de l'enveloppe de sa sous-famille, connue à t. Une sous-famille sans enveloppe déclarée est une erreur.
  - `stop_trades` accepte désormais un niveau NaN, « sans stop pour ce signal » : `apply_stop` n'est pas modifié et ne touche jamais un niveau NaN.
- **Lectures après un stop :**
  - cooldown = `dynamic=False` (à plat jusqu'à t + 1 + H) ;
  - réouverture = `dynamic=True` (signal admissible dès la clôture de la barre du stop).
- **Grille :**
  - 5 configurations × 7 horizons × 2 lectures × 2 frais ;
  - RE-4 : 4 configurations × 3 horizons × 3 variantes de seuils × 2 lectures × 2 frais.

  Au total, 284 lignes en 102 s.
- **Contrôles bloquants, tous passés :**
  - ancre P6.5d, sans stop et avec stop à 2,5 % ;
  - 36 lignes identiques à C02 : C1 et C2 = contrôles sans stop de C02 ; le moteur avec la même règle pour F2b et F3 = règle uniforme de C02 (SL-B à l'extremum, SL-A 2 ATR) dans les deux lectures, à H13, H26 et H48 ;
  - les masques de l'échantillon entier, restreints après l'amorce, sont identiques aux masques figés.
- **Tests :** 2 nouveaux dans `tests/test_envelope.py`.
  - Un niveau NaN ne coupe jamais ; les autres signaux gardent leur stop.
  - Le routage attribue la règle de chaque sous-famille ; une même règle partout redonne la règle uniforme ; une sous-famille non déclarée lève une erreur.

  Suite complète : 187 réussis, 2 ignorés.

## 2. [OBS] Mesures

### 2.1 À H = 26 : même espérance que R2 uniforme, drawdown presque divisé par deux

5 bps ; lecture cooldown pour les variantes du moteur ; PnL, drawdown et Calmar à 0,25 % par ATR.

| Configuration | Espérance ATR [IC] | Espérance bps [IC] | PnL ; DD | Calmar | Années > 0 | 10 bps : ATR [IC] ; PnL ; DD |
|---|---|---|---|---|---|---|
| C1 — F2b seul | +0,389 [+0,079 ; +0,700] | +11,5 [−2,9 ; +26,0] | +72 % ; −13,2 % | 0,72 | 5/6 | +0,255 [−0,056 ; +0,569] ; +42 % ; −16,7 % |
| C2 — R2 hors Q4 uniforme | +0,354 [+0,051 ; +0,643] | +12,3 [−1,5 ; +25,8] | +122 % ; −20,5 % | 0,69 | 5/6 | +0,218 [−0,088 ; +0,510] ; +60 % ; −22,2 % |
| **RE-1 — F2b sans stop, F3 SL-B** | **+0,369 [+0,098 ; +0,645]** | **+12,3 [+0,2 ; +24,4]** | **+138 % ; −13,5 %** | **1,16** | **6/6** | **+0,233 [−0,041 ; +0,511] ; +72 % ; −15,9 %** |
| RE-2 — F2b sans stop, F3 SL-A 2 | +0,353 [+0,084 ; +0,625] | +11,7 [−0,4 ; +24,2] | +132 % ; −13,1 % | 1,14 | 6/6 | +0,217 [−0,054 ; +0,495] ; +68 % ; −15,1 % |
| RE-3 — F2b SL-A 5, F3 SL-B | +0,288 [+0,045 ; +0,545] | +10,1 [−1,3 ; +22,1] | +96 % ; −15,4 % | 0,77 | 6/6 | +0,153 [−0,094 ; +0,413] ; +42 % ; −17,6 % |

- **RE-1, les 8 métriques à 5 bps :**
  - PnL +138 % (+204 % en 1x ; +13 320 bps cumulés) ;
  - PF 1,20 (1,28 pondéré) ; WR 44,3 % ;
  - espérance +12,3 bps et +0,369 ATR ;
  - drawdown valorisé −13,5 % (−44 % en 1x) ;
  - 1 080 trades (15,0 par mois), dont 24 % stoppés ; durée médiane 26 barres ;
  - frais 29 % du brut (+17,3 bps de brut par trade).
- **Sens :** Long / Short +0,46 / +0,27 ATR, timing +0,362 [+0,089 ; +0,638]. Les deux sens sont positifs : ce n'est pas la seule dérive du BTC.
- **Contribution des sous-familles :** F2b, 573 trades, +0,459 ATR ; F3, 507 trades, +0,267 ATR contre +0,235 sans stop dans C2.
- **Effet apparié du routage face à C2** (mêmes 1 080 entrées) : +0,015 ATR [−0,108 ; +0,141], soit +0,0 bps [−5,6 ; +5,7]. Aucun horizon ne montre d'effet significatif (de −0,029 à +0,094 ATR).

  Le moteur ne crée donc pas d'espérance. Son apport porte sur le risque :
  - drawdown −20,5 % → −13,5 % ;
  - Calmar 0,69 → 1,16 ;
  - 6 années positives sur 6 au lieu de 5 : C2 perd 3 % en 2024, RE-1 y gagne 15 %.
- **Années de RE-1** (ATR par trade ; PnL) :

  | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 |
  |---|---|---|---|---|---|
  | +0,51 ; +25 % | +0,02 ; +0 % | +0,30 ; +12 % | +0,50 ; +25 % | +0,33 ; +15 % | +0,55 ; +18 % |

  2021 est quasi nulle.

### 2.2 Plateau d'horizon : l'espérance tient de H = 20 à 32, le PnL culmine vers 26-28

RE-1, lecture cooldown, 5 bps :

| H | 13 | 20 | 24 | 26 | 28 | 32 | 48 |
|---|---|---|---|---|---|---|---|
| Espérance ATR | +0,066 | +0,210 | +0,328 | +0,369 | +0,371 | +0,316 | +0,165 |
| IC 95 % | [−0,098 ; +0,233] | [+0,008 ; +0,423] | [+0,078 ; +0,583] | [+0,098 ; +0,645] | [+0,078 ; +0,657] | [+0,001 ; +0,628] | [−0,224 ; +0,562] |
| PnL ; DD | +16 % ; −19 % | +65 % ; −12 % | +112 % ; −14 % | +138 % ; −13 % | +129 % ; −16 % | +89 % ; −18 % | +14 % ; −30 % |
| 10 bps : PnL | −20 % | +16 % | +52 % | +72 % | +67 % | +40 % | −12 % |

- **H = 26 n'est pas un pic isolé.**
  - L'IC en ATR est positif de H20 à H32.
  - De H24 à H28, l'espérance varie de moins de 0,05 ATR et le PnL reste entre +112 et +138 %.
  - Le PnL composé est plus pointu que l'espérance par trade : avec H, l'espérance monte et le nombre de trades baisse (1 160 à H20, 1 012 à H32).
- **Hors de la zone, l'avantage s'éteint.** À H13 et H48, aucune configuration n'a d'IC > 0, et à 10 bps le PnL y est négatif ou nul.
- **Les contrôles ont le même profil.** C1 culmine à H28 (+0,461 ATR) ; C2 garde un IC > 0 de H20 à H28.

### 2.3 Cooldown contre réouverture

- **De H13 à H32, le cooldown fait mieux dans les trois variantes.** Exemples pour RE-1 :

  | H | Trades débloqués (espérance) | Cooldown | Réouverture |
  |---|---|---|---|
  | 26 | 37 (−0,40 ATR) | +0,369 ATR ; +138 % | +0,338 ATR ; +133 % |
  | 32 | 53 (−0,65 ATR) | +0,316 ATR ; +89 % | +0,249 ATR ; +69 % |

  Entre H13 et H32, les trades débloqués par un stop ont une espérance de −0,15 à −1,38 ATR.
- **À H48, l'écart s'inverse :** la réouverture fait mieux (débloqués +0,28 à +0,45 ATR), mais aucune configuration n'y est rentable avec un IC > 0.

### 2.4 Stop de catastrophe sur F2b (RE-3) : il coûte sans protéger

- L'effet apparié de RE-3 face à RE-1 est négatif à tous les horizons :
  - −0,080 ATR [−0,181 ; +0,018] à H26 ;
  - significatif à H20 (−0,083 [−0,152 ; −0,023]) et à H24 (−0,097 [−0,199 ; −0,012]).
- À H26, l'espérance de F2b tombe de +0,459 à +0,308 ATR.
- Le drawdown augmente (−13,5 % → −15,4 %) et le Calmar passe de 1,16 à 0,77.

### 2.5 RE-4 : seuils causaux

- **Masques :** la médiane de `leg_atr` et le P75 de `nis_z_100` sont calculés sur les seuls signaux précédents. Les masques restent identiques à 98,6 % (fenêtre glissante de 500 signaux) et 99,2 % (expansive) des signaux après l'amorce.
- **RE-1, H26, cooldown, 5 bps** (après les 500 premiers signaux) :

  | Seuils | Espérance ATR [IC] | Espérance bps [IC] | PnL ; DD | Années > 0 | 10 bps : ATR ; PnL |
  |---|---|---|---|---|---|
  | Échantillon entier | +0,364 [+0,071 ; +0,654] | +11,8 [−1,1 ; +24,5] | +121 % ; −13,5 % | 6/6 | +0,225 ; +63 % |
  | Glissants (500) | +0,366 [+0,072 ; +0,672] | +12,3 [−0,6 ; +25,9] | +118 % ; −12,4 % | 6/6 | +0,225 ; +60 % |
  | Expansifs | +0,342 [+0,038 ; +0,645] | +11,0 [−2,2 ; +24,2] | +103 % ; −13,6 % | 6/6 | +0,202 ; +51 % |

- **Ce qui tient avec des seuils causaux :** l'IC positif en ATR, les 6 années positives, un drawdown de −12 à −14 % et un Calmar de 0,92 à 1,12.
- **Ce qui ne tient pas : l'IC positif en bps.** Il repasse sous 0 dès qu'on retire janvier-mai 2020, même avec les seuils de l'échantillon entier. Il dépendait donc de cette période, pas des seuils.
- La baisse du PnL (+138 % → +121 %) vient de ces mois retirés, pas des seuils.
- RE-2 se comporte de même (+0,335 à +0,356 ATR, +103 à +120 %).
- À H13 et H48, aucune variante n'a d'avantage.

## 3. [HYP] Lectures

- **Le moteur est un gestionnaire de risque, pas une source d'espérance.** L'espérance de R2 hors Q4 vient de la sortie à 26 barres et de l'éviction de Q4 (C01). Le routage coupe les échecs francs de F3 : le drawdown et l'année 2024 s'améliorent, l'espérance moyenne ne change pas.
- **Le cooldown protège de l'échec du breakout.** Après un stop sur F3, le marché a réintégré son range. Le signal suivant, dans la même structure, perd en moyenne. À H48, la fenêtre de cooldown devient trop longue et bloque des signaux utiles.
- **Le plateau de 20 à 32 barres (10 à 16 h)** suggère une durée caractéristique de l'expansion après la sortie de compression. Elle est à éprouver par walk-forward (Étape D), pas à affiner ici.
- **L'IC en bps reste fragile** : il dépend du printemps 2020, très volatil. L'unité ATR, qui neutralise ce poids (I-M8), est la lecture robuste.

## 4. [DECISION] Orientations proposées (rien n'est lancé)

- [x] **À POURSUIVRE : RE-1 en lecture cooldown, à H = 26, devient la configuration de référence du moteur** (F2b sans stop, F3 SL-B à l'extremum).
  - C'est un plateau de 24 à 28 barres, qui tient avec des seuils causaux et apporte un gain de risque robuste.
  - RE-2 (F3 SL-A 2 ATR) est équivalent et sert de variante de secours.
- **Le cooldown est retenu contre la réouverture.**
- **RE-3 est rejeté :** le stop de catastrophe sur F2b coûte 0,08 ATR par trade et augmente le drawdown.
- **Frais :**
  - à 5 bps, RE-1 a un IC entièrement positif en ATR ;
  - à 10 bps, l'estimation reste positive (+0,233 ATR, +72 %, drawdown −15,9 %, Calmar 0,60), mais l'IC contient 0.

  L'hypothèse d'exécution (maker ou taker) conditionne donc la preuve.
- **Points à trancher par le porteur :**
  1. La suite de l'Étape C sur RE-1. Un break-even ou un take-profit risquerait de couper la queue droite de F2b (I-M9 : le mesurer d'abord sur les mêmes entrées). Un filtre macro est l'autre option.
  2. Un H propre à chaque sous-famille (F2b culmine à H28).
  3. Le passage à l'Étape D (walk-forward sur RE-1).
  4. Le hold-out.
