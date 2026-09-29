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

---

# Annexes chiffrées (générées par `run_C02bis.py`)

## A. Contrôles bloquants et conventions

| Contrôle | Résultat |
|---|---|
| Ancre P6.5d, sans stop et stop 2,5 % | 6 037 et 6 589 trades identiques au fichier de référence |
| C1, C2 et routage uniforme = C02 | 36 lignes identiques (écart relatif max 4,5·10⁻⁶) : C1 = F2b sans stop, C2 = R2 hors Q4 sans stop ; moteur avec la même règle pour F2b et F3 = règle uniforme de C02 (SL-B à l'extremum, SL-A 2 ATR), cooldown = « entrées figées », réouverture = « séquentiel dynamique » |
| Univers | R2 hors Q4 = 1452 signaux : F2b · x1 déjà retourné 741, F3 · x1 déjà retourné 711 ; familles identiques à B01 |
| Seuils causaux (RE-4) | échantillon entier, après 500 : R2 1 348 signaux, accord 100,0 %; glissante 500 signaux : R2 1 347 signaux, accord 98,6 %; expansive : R2 1 299 signaux, accord 99,2 % |
| IC 95 % | grappes mensuelles d'entrée, 2 000 tirages ; effets appariés sur les mêmes entrées que C2 (lecture cooldown) |
| Capital | 1 ATR14(t) = 0,25 % du capital, levier ≤ 1x ; notionnel 1x en référence ; Calmar = PnL annualisé / |MDD valorisé|, à 0,25 % par ATR |
| Période | 2020-01 → 2025-12 (72 mois) ; aucune barre de 2026 lue |

## B. Tableau complet à H = 26

**5 bps aller-retour — 8 métriques**

| Configuration | PnL : 0,25 %/ATR ; 1x ; bps (1x) | PF : 1x ; pondéré | WR | Espérance : bps [IC] ; ATR [IC] | MDD valorisé : 0,25 %/ATR ; 1x | Trades (/mois) ; stoppés | Durée méd. | Part des frais ; brut/trade |
|---|---|---|---|---|---|---|---|---|
| C1 — F2b seul, sans stop | +72 % ; +78 % ; +7345 | 1,17 ; 1,28 | 49,6 % | +11,5 [−2,9 ; +26,0] ; +0,389 [+0,079 ; +0,700] | −13,2 % ; −45 % | 639 (8,9) ; 0 % | 26 | 30 % ; +16,5 |
| C2 — R2 hors Q4 uniforme, sans stop | +122 % ; +187 % ; +13309 | 1,18 ; 1,23 | 49,4 % | +12,3 [−1,5 ; +25,8] ; +0,354 [+0,051 ; +0,643] | −20,5 % ; −48 % | 1 080 (15,0) ; 0 % | 26 | 29 % ; +17,3 |
| RE-1 — F2b sans stop, F3 SL-B extremum (cooldown) | +138 % ; +204 % ; +13320 | 1,20 ; 1,28 | 44,3 % | +12,3 [+0,2 ; +24,4] ; +0,369 [+0,098 ; +0,645] | −13,5 % ; −44 % | 1 080 (15,0) ; 24 % | 26 | 29 % ; +17,3 |
| RE-1 — F2b sans stop, F3 SL-B extremum (réouverture) | +133 % ; +235 % ; +14523 | 1,21 ; 1,27 | 44,1 % | +13,1 [+0,5 ; +25,6] ; +0,338 [+0,061 ; +0,616] | −13,9 % ; −48 % | 1 108 (15,4) ; 24 % | 26 | 28 % ; +18,1 |
| RE-2 — F2b sans stop, F3 SL-A 2 ATR (cooldown) | +132 % ; +185 % ; +12649 | 1,19 ; 1,27 | 43,9 % | +11,7 [−0,4 ; +24,2] ; +0,353 [+0,084 ; +0,625] | −13,1 % ; −42 % | 1 080 (15,0) ; 25 % | 26 | 30 % ; +16,7 |
| RE-2 — F2b sans stop, F3 SL-A 2 ATR (réouverture) | +125 % ; +204 % ; +13506 | 1,19 ; 1,26 | 43,7 % | +12,2 [−0,4 ; +24,3] ; +0,320 [+0,050 ; +0,590] | −13,3 % ; −45 % | 1 111 (15,4) ; 25 % | 26 | 29 % ; +17,2 |
| RE-3 — F2b SL-A 5 ATR, F3 SL-B extremum (cooldown) | +96 % ; +144 % ; +10947 | 1,16 ; 1,22 | 43,6 % | +10,1 [−1,3 ; +22,1] ; +0,288 [+0,045 ; +0,545] | −15,4 % ; −42 % | 1 080 (15,0) ; 33 % | 26 | 33 % ; +15,1 |
| RE-3 — F2b SL-A 5 ATR, F3 SL-B extremum (réouverture) | +91 % ; +171 % ; +12229 | 1,17 ; 1,20 | 43,3 % | +11,0 [−1,4 ; +23,4] ; +0,261 [+0,012 ; +0,522] | −16,8 % ; −47 % | 1 112 (15,4) ; 33 % | 26 | 31 % ; +16,0 |

**5 bps — sens, sous-familles, régularité**

| Configuration | Long / Short (ATR) | Timing ATR [IC] | F2b : n ; esp. ATR | F3 : n ; esp. ATR | Années > 0 : ATR ; PnL | PnL annualisé ; Calmar |
|---|---|---|---|---|---|---|
| C1 — F2b seul, sans stop | +0,53 / +0,25 | +0,388 [+0,076 ; +0,700] | 639 ; +0,389 | 0 ; — | 5/6 ; 5/6 | +9,5 % ; 0,72 |
| C2 — R2 hors Q4 uniforme, sans stop | +0,48 / +0,21 | +0,344 [+0,045 ; +0,626] | 573 ; +0,459 | 507 ; +0,235 | 5/6 ; 5/6 | +14,2 % ; 0,69 |
| RE-1 — F2b sans stop, F3 SL-B extremum (cooldown) | +0,46 / +0,27 | +0,362 [+0,089 ; +0,638] | 573 ; +0,459 | 507 ; +0,267 | 6/6 ; 6/6 | +15,6 % ; 1,16 |
| RE-1 — F2b sans stop, F3 SL-B extremum (réouverture) | +0,42 / +0,25 | +0,332 [+0,055 ; +0,614] | 590 ; +0,433 | 518 ; +0,231 | 6/6 ; 6/6 | +15,1 % ; 1,09 |
| RE-2 — F2b sans stop, F3 SL-A 2 ATR (cooldown) | +0,43 / +0,26 | +0,347 [+0,080 ; +0,617] | 573 ; +0,459 | 507 ; +0,233 | 6/6 ; 6/6 | +15,0 % ; 1,14 |
| RE-2 — F2b sans stop, F3 SL-A 2 ATR (réouverture) | +0,40 / +0,23 | +0,313 [+0,042 ; +0,588] | 588 ; +0,418 | 523 ; +0,209 | 6/6 ; 6/6 | +14,4 % ; 1,09 |
| RE-3 — F2b SL-A 5 ATR, F3 SL-B extremum (cooldown) | +0,30 / +0,27 | +0,287 [+0,045 ; +0,546] | 573 ; +0,308 | 507 ; +0,267 | 6/6 ; 6/6 | +11,9 % ; 0,77 |
| RE-3 — F2b SL-A 5 ATR, F3 SL-B extremum (réouverture) | +0,26 / +0,27 | +0,261 [+0,013 ; +0,523] | 591 ; +0,292 | 521 ; +0,226 | 6/6 ; 6/6 | +11,4 % ; 0,68 |

**10 bps aller-retour — 8 métriques**

| Configuration | PnL : 0,25 %/ATR ; 1x ; bps (1x) | PF : 1x ; pondéré | WR | Espérance : bps [IC] ; ATR [IC] | MDD valorisé : 0,25 %/ATR ; 1x | Trades (/mois) ; stoppés | Durée méd. | Part des frais ; brut/trade |
|---|---|---|---|---|---|---|---|---|
| C1 — F2b seul, sans stop | +42 % ; +29 % ; +4150 | 1,09 ; 1,18 | 48,2 % | +6,5 [−7,9 ; +21,0] ; +0,255 [−0,056 ; +0,569] | −16,7 % ; −48 % | 639 (8,9) ; 0 % | 26 | 61 % ; +16,5 |
| C2 — R2 hors Q4 uniforme, sans stop | +60 % ; +68 % ; +7909 | 1,10 ; 1,14 | 47,5 % | +7,3 [−6,5 ; +20,8] ; +0,218 [−0,088 ; +0,510] | −22,2 % ; −51 % | 1 080 (15,0) ; 0 % | 26 | 58 % ; +17,3 |
| RE-1 — F2b sans stop, F3 SL-B extremum (cooldown) | +72 % ; +77 % ; +7920 | 1,11 ; 1,17 | 42,8 % | +7,3 [−4,8 ; +19,4] ; +0,233 [−0,041 ; +0,511] | −15,9 % ; −48 % | 1 080 (15,0) ; 24 % | 26 | 58 % ; +17,3 |
| RE-1 — F2b sans stop, F3 SL-B extremum (réouverture) | +67 % ; +93 % ; +8983 | 1,12 ; 1,16 | 42,7 % | +8,1 [−4,5 ; +20,6] ; +0,203 [−0,079 ; +0,486] | −16,2 % ; −51 % | 1 108 (15,4) ; 24 % | 26 | 55 % ; +18,1 |
| RE-2 — F2b sans stop, F3 SL-A 2 ATR (cooldown) | +68 % ; +66 % ; +7249 | 1,10 ; 1,16 | 42,5 % | +6,7 [−5,4 ; +19,2] ; +0,217 [−0,054 ; +0,495] | −15,1 % ; −47 % | 1 080 (15,0) ; 25 % | 26 | 60 % ; +16,7 |
| RE-2 — F2b sans stop, F3 SL-A 2 ATR (réouverture) | +61 % ; +74 % ; +7951 | 1,11 ; 1,15 | 42,4 % | +7,2 [−5,4 ; +19,3] ; +0,184 [−0,086 ; +0,461] | −15,3 % ; −49 % | 1 111 (15,4) ; 25 % | 26 | 58 % ; +17,2 |
| RE-3 — F2b SL-A 5 ATR, F3 SL-B extremum (cooldown) | +42 % ; +42 % ; +5547 | 1,08 ; 1,11 | 42,1 % | +5,1 [−6,3 ; +17,1] ; +0,153 [−0,094 ; +0,413] | −17,6 % ; −46 % | 1 080 (15,0) ; 33 % | 26 | 66 % ; +15,1 |
| RE-3 — F2b SL-A 5 ATR, F3 SL-B extremum (réouverture) | +37 % ; +55 % ; +6669 | 1,09 ; 1,10 | 41,9 % | +6,0 [−6,4 ; +18,4] ; +0,125 [−0,123 ; +0,390] | −18,9 % ; −51 % | 1 112 (15,4) ; 33 % | 26 | 63 % ; +16,0 |

**10 bps — sens, sous-familles, régularité**

| Configuration | Long / Short (ATR) | Timing ATR [IC] | F2b : n ; esp. ATR | F3 : n ; esp. ATR | Années > 0 : ATR ; PnL | PnL annualisé ; Calmar |
|---|---|---|---|---|---|---|
| C1 — F2b seul, sans stop | +0,39 / +0,11 | +0,254 [−0,060 ; +0,568] | 639 ; +0,255 | 0 ; — | 5/6 ; 4/6 | +6,1 % ; 0,36 |
| C2 — R2 hors Q4 uniforme, sans stop | +0,35 / +0,07 | +0,208 [−0,093 ; +0,492] | 573 ; +0,326 | 507 ; +0,096 | 4/6 ; 4/6 | +8,2 % ; 0,37 |
| RE-1 — F2b sans stop, F3 SL-B extremum (cooldown) | +0,32 / +0,13 | +0,226 [−0,050 ; +0,507] | 573 ; +0,326 | 507 ; +0,127 | 5/6 ; 5/6 | +9,5 % ; 0,60 |
| RE-1 — F2b sans stop, F3 SL-B extremum (réouverture) | +0,28 / +0,11 | +0,197 [−0,083 ; +0,482] | 590 ; +0,300 | 518 ; +0,092 | 5/6 ; 5/6 | +9,0 % ; 0,55 |
| RE-2 — F2b sans stop, F3 SL-A 2 ATR (cooldown) | +0,30 / +0,13 | +0,211 [−0,057 ; +0,489] | 573 ; +0,326 | 507 ; +0,094 | 5/6 ; 5/6 | +9,0 % ; 0,60 |
| RE-2 — F2b sans stop, F3 SL-A 2 ATR (réouverture) | +0,26 / +0,09 | +0,177 [−0,098 ; +0,456] | 588 ; +0,285 | 523 ; +0,070 | 6/6 ; 5/6 | +8,3 % ; 0,54 |
| RE-3 — F2b SL-A 5 ATR, F3 SL-B extremum (cooldown) | +0,17 / +0,14 | +0,151 [−0,094 ; +0,413] | 573 ; +0,175 | 507 ; +0,127 | 5/6 ; 5/6 | +6,0 % ; 0,34 |
| RE-3 — F2b SL-A 5 ATR, F3 SL-B extremum (réouverture) | +0,12 / +0,13 | +0,126 [−0,125 ; +0,393] | 591 ; +0,159 | 521 ; +0,087 | 5/6 ; 5/6 | +5,4 % ; 0,29 |

## C. Profil d'horizon (plateau autour de H = 26)

Lecture cooldown pour les variantes du moteur. Première table : espérance nette par trade en ATR [IC 95 %]. Seconde : PnL composé ; MDD valorisé, à 0,25 % par ATR.

**5 bps — espérance ATR [IC]**

| Configuration | H = 13 | H = 20 | H = 24 | H = 26 | H = 28 | H = 32 | H = 48 |
|---|---|---|---|---|---|---|---|
| C1 — F2b seul, sans stop | +0,022 [−0,198 ; +0,240] | +0,241 [−0,019 ; +0,518] | +0,385 [+0,077 ; +0,711] | +0,389 [+0,079 ; +0,700] | +0,461 [+0,121 ; +0,808] | +0,326 [−0,051 ; +0,715] | +0,219 [−0,313 ; +0,768] |
| C2 — R2 hors Q4 uniforme, sans stop | +0,031 [−0,146 ; +0,208] | +0,239 [+0,014 ; +0,477] | +0,324 [+0,049 ; +0,594] | +0,354 [+0,051 ; +0,643] | +0,366 [+0,041 ; +0,676] | +0,340 [−0,021 ; +0,682] | +0,071 [−0,381 ; +0,508] |
| RE-1 — F2b sans stop, F3 SL-B extremum | +0,066 [−0,098 ; +0,233] | +0,210 [+0,008 ; +0,423] | +0,328 [+0,078 ; +0,583] | +0,369 [+0,098 ; +0,645] | +0,371 [+0,078 ; +0,657] | +0,316 [+0,001 ; +0,628] | +0,165 [−0,224 ; +0,562] |
| RE-2 — F2b sans stop, F3 SL-A 2 ATR | +0,063 [−0,095 ; +0,229] | +0,197 [−0,003 ; +0,408] | +0,311 [+0,066 ; +0,558] | +0,353 [+0,084 ; +0,625] | +0,369 [+0,082 ; +0,660] | +0,320 [+0,002 ; +0,628] | +0,160 [−0,222 ; +0,555] |
| RE-3 — F2b SL-A 5 ATR, F3 SL-B extremum | +0,044 [−0,117 ; +0,214] | +0,126 [−0,068 ; +0,334] | +0,231 [+0,007 ; +0,474] | +0,288 [+0,045 ; +0,545] | +0,301 [+0,051 ; +0,567] | +0,283 [−0,008 ; +0,559] | +0,101 [−0,236 ; +0,458] |

**5 bps — PnL ; MDD**

| Configuration | H = 13 | H = 20 | H = 24 | H = 26 | H = 28 | H = 32 | H = 48 |
|---|---|---|---|---|---|---|---|
| C1 — F2b seul, sans stop | +2 % ; −20 % | +39 % ; −11 % | +69 % ; −13 % | +72 % ; −13 % | +83 % ; −15 % | +49 % ; −23 % | +18 % ; −31 % |
| C2 — R2 hors Q4 uniforme, sans stop | +1 % ; −31 % | +62 % ; −18 % | +104 % ; −22 % | +122 % ; −20 % | +117 % ; −24 % | +90 % ; −29 % | −5 % ; −37 % |
| RE-1 — F2b sans stop, F3 SL-B extremum | +16 % ; −19 % | +65 % ; −12 % | +112 % ; −14 % | +138 % ; −13 % | +129 % ; −16 % | +89 % ; −18 % | +14 % ; −30 % |
| RE-2 — F2b sans stop, F3 SL-A 2 ATR | +15 % ; −20 % | +58 % ; −13 % | +105 % ; −13 % | +132 % ; −13 % | +131 % ; −16 % | +93 % ; −18 % | +13 % ; −28 % |
| RE-3 — F2b SL-A 5 ATR, F3 SL-B extremum | +10 % ; −24 % | +36 % ; −16 % | +71 % ; −14 % | +96 % ; −15 % | +98 % ; −15 % | +84 % ; −17 % | +11 % ; −25 % |

**10 bps — espérance ATR [IC]**

| Configuration | H = 13 | H = 20 | H = 24 | H = 26 | H = 28 | H = 32 | H = 48 |
|---|---|---|---|---|---|---|---|
| C1 — F2b seul, sans stop | −0,113 [−0,341 ; +0,105] | +0,107 [−0,155 ; +0,385] | +0,251 [−0,058 ; +0,578] | +0,255 [−0,056 ; +0,569] | +0,326 [−0,011 ; +0,674] | +0,192 [−0,184 ; +0,578] | +0,086 [−0,437 ; +0,633] |
| C2 — R2 hors Q4 uniforme, sans stop | −0,106 [−0,283 ; +0,073] | +0,103 [−0,126 ; +0,342] | +0,190 [−0,086 ; +0,456] | +0,218 [−0,088 ; +0,510] | +0,230 [−0,091 ; +0,544] | +0,205 [−0,151 ; +0,543] | −0,064 [−0,512 ; +0,372] |
| RE-1 — F2b sans stop, F3 SL-B extremum | −0,071 [−0,236 ; +0,100] | +0,073 [−0,131 ; +0,289] | +0,194 [−0,057 ; +0,451] | +0,233 [−0,041 ; +0,511] | +0,235 [−0,058 ; +0,524] | +0,180 [−0,138 ; +0,491] | +0,030 [−0,358 ; +0,428] |
| RE-2 — F2b sans stop, F3 SL-A 2 ATR | −0,074 [−0,237 ; +0,096] | +0,060 [−0,140 ; +0,271] | +0,176 [−0,071 ; +0,428] | +0,217 [−0,054 ; +0,495] | +0,233 [−0,056 ; +0,525] | +0,185 [−0,136 ; +0,491] | +0,025 [−0,354 ; +0,419] |
| RE-3 — F2b SL-A 5 ATR, F3 SL-B extremum | −0,092 [−0,257 ; +0,082] | −0,010 [−0,209 ; +0,198] | +0,097 [−0,131 ; +0,344] | +0,153 [−0,094 ; +0,413] | +0,166 [−0,089 ; +0,439] | +0,148 [−0,144 ; +0,428] | −0,033 [−0,371 ; +0,322] |

**10 bps — PnL ; MDD**

| Configuration | H = 13 | H = 20 | H = 24 | H = 26 | H = 28 | H = 32 | H = 48 |
|---|---|---|---|---|---|---|---|
| C1 — F2b seul, sans stop | −17 % ; −32 % | +14 % ; −15 % | +39 % ; −15 % | +42 % ; −17 % | +52 % ; −17 % | +24 % ; −26 % | −0 % ; −34 % |
| C2 — R2 hors Q4 uniforme, sans stop | −30 % ; −46 % | +14 % ; −28 % | +47 % ; −25 % | +60 % ; −22 % | +58 % ; −26 % | +40 % ; −31 % | −27 % ; −45 % |
| RE-1 — F2b sans stop, F3 SL-B extremum | −20 % ; −37 % | +16 % ; −20 % | +52 % ; −17 % | +72 % ; −16 % | +67 % ; −18 % | +40 % ; −21 % | −12 % ; −35 % |
| RE-2 — F2b sans stop, F3 SL-A 2 ATR | −21 % ; −38 % | +12 % ; −22 % | +47 % ; −16 % | +68 % ; −15 % | +69 % ; −18 % | +43 % ; −20 % | −13 % ; −33 % |
| RE-3 — F2b SL-A 5 ATR, F3 SL-B extremum | −24 % ; −42 % | −4 % ; −31 % | +23 % ; −20 % | +42 % ; −18 % | +44 % ; −18 % | +36 % ; −19 % | −14 % ; −35 % |

## D. Cooldown contre réouverture immédiate (5 bps)

Débloqués : trades ouverts grâce à un stop, absents de la lecture cooldown ; perdus : trades de la lecture cooldown masqués par un trade débloqué.

| Configuration | H | Trades : cooldown ; réouverture | Débloqués : n ; esp. ATR | Perdus : n ; esp. ATR | Esp. ATR : cooldown ; réouverture | PnL : cooldown ; réouverture | MDD : cooldown ; réouverture |
|---|---|---|---|---|---|---|---|
| RE-1 — F2b sans stop, F3 SL-B extremum | H = 13 | 1 240 ; 1 247 | 7 ; −1,345 | 0 ; — | +0,066 ; +0,058 | +16 % ; +14 % | −19 % ; −20 % |
| RE-1 — F2b sans stop, F3 SL-B extremum | H = 20 | 1 160 ; 1 182 | 27 ; −0,938 | 5 ; +0,824 | +0,210 ; +0,181 | +65 % ; +57 % | −12 % ; −14 % |
| RE-1 — F2b sans stop, F3 SL-B extremum | H = 24 | 1 109 ; 1 134 | 35 ; −0,773 | 10 ; +1,036 | +0,328 ; +0,288 | +112 % ; +102 % | −14 % ; −16 % |
| RE-1 — F2b sans stop, F3 SL-B extremum | H = 26 | 1 080 ; 1 108 | 37 ; −0,404 | 9 ; +0,912 | +0,369 ; +0,338 | +138 % ; +133 % | −13 % ; −14 % |
| RE-1 — F2b sans stop, F3 SL-B extremum | H = 28 | 1 051 ; 1 087 | 47 ; −0,734 | 11 ; +0,484 | +0,371 ; +0,322 | +129 % ; +114 % | −16 % ; −15 % |
| RE-1 — F2b sans stop, F3 SL-B extremum | H = 32 | 1 012 ; 1 051 | 53 ; −0,649 | 14 ; +1,659 | +0,316 ; +0,249 | +89 % ; +69 % | −18 % ; −17 % |
| RE-1 — F2b sans stop, F3 SL-B extremum | H = 48 | 864 ; 935 | 91 ; +0,364 | 20 ; +0,563 | +0,165 ; +0,176 | +14 % ; +19 % | −30 % ; −36 % |
| RE-2 — F2b sans stop, F3 SL-A 2 ATR | H = 13 | 1 240 ; 1 253 | 16 ; −1,376 | 3 ; −0,236 | +0,063 ; +0,046 | +15 % ; +10 % | −20 % ; −22 % |
| RE-2 — F2b sans stop, F3 SL-A 2 ATR | H = 20 | 1 160 ; 1 187 | 35 ; −1,012 | 8 ; +1,701 | +0,197 ; +0,151 | +58 % ; +43 % | −13 % ; −14 % |
| RE-2 — F2b sans stop, F3 SL-A 2 ATR | H = 24 | 1 109 ; 1 139 | 44 ; −0,545 | 14 ; +1,541 | +0,311 ; +0,263 | +105 % ; +89 % | −13 % ; −15 % |
| RE-2 — F2b sans stop, F3 SL-A 2 ATR | H = 26 | 1 080 ; 1 111 | 44 ; −0,147 | 13 ; +1,496 | +0,353 ; +0,320 | +132 % ; +125 % | −13 % ; −13 % |
| RE-2 — F2b sans stop, F3 SL-A 2 ATR | H = 28 | 1 051 ; 1 091 | 55 ; −0,459 | 15 ; +1,158 | +0,369 ; +0,316 | +131 % ; +114 % | −16 % ; −15 % |
| RE-2 — F2b sans stop, F3 SL-A 2 ATR | H = 32 | 1 012 ; 1 056 | 59 ; −0,553 | 15 ; +1,426 | +0,320 ; +0,256 | +93 % ; +74 % | −18 % ; −16 % |
| RE-2 — F2b sans stop, F3 SL-A 2 ATR | H = 48 | 864 ; 941 | 96 ; +0,449 | 19 ; +0,754 | +0,160 ; +0,177 | +13 % ; +19 % | −28 % ; −35 % |
| RE-3 — F2b SL-A 5 ATR, F3 SL-B extremum | H = 13 | 1 240 ; 1 247 | 7 ; −1,184 | 0 ; — | +0,044 ; +0,037 | +10 % ; +9 % | −24 % ; −25 % |
| RE-3 — F2b SL-A 5 ATR, F3 SL-B extremum | H = 20 | 1 160 ; 1 183 | 28 ; −0,477 | 5 ; +0,824 | +0,126 ; +0,109 | +36 % ; +32 % | −16 % ; −15 % |
| RE-3 — F2b SL-A 5 ATR, F3 SL-B extremum | H = 24 | 1 109 ; 1 137 | 38 ; −0,574 | 10 ; +0,495 | +0,231 ; +0,202 | +71 % ; +65 % | −14 % ; −16 % |
| RE-3 — F2b SL-A 5 ATR, F3 SL-B extremum | H = 26 | 1 080 ; 1 112 | 41 ; −0,422 | 9 ; +0,448 | +0,288 ; +0,261 | +96 % ; +91 % | −15 % ; −17 % |
| RE-3 — F2b SL-A 5 ATR, F3 SL-B extremum | H = 28 | 1 051 ; 1 092 | 52 ; −0,635 | 11 ; +0,041 | +0,301 ; +0,259 | +98 % ; +87 % | −15 % ; −17 % |
| RE-3 — F2b SL-A 5 ATR, F3 SL-B extremum | H = 32 | 1 012 ; 1 058 | 60 ; −0,786 | 14 ; +0,726 | +0,283 ; +0,217 | +84 % ; +62 % | −17 % ; −17 % |
| RE-3 — F2b SL-A 5 ATR, F3 SL-B extremum | H = 48 | 864 ; 950 | 113 ; +0,284 | 27 ; −0,260 | +0,101 ; +0,134 | +11 % ; +19 % | −25 % ; −26 % |

## E. Effets appariés (lecture cooldown, mêmes entrées que C2)

Moyenne par trade de (variante − C2), frais compensés : l'effet des stops propres à chaque sous-famille. Dernière colonne : RE-3 − RE-1, soit l'effet du stop de catastrophe SL-A 5 ATR sur F2b.

| Horizon | RE-1 − C2 : ATR [IC] ; bps [IC] | RE-2 − C2 | RE-3 − C2 | RE-3 − RE-1 (ATR) |
|---|---|---|---|---|
| H = 13 | +0,035 [−0,026 ; +0,098] ; +2,2 [−0,4 ; +4,7] | +0,032 [−0,030 ; +0,095] ; +2,1 [−0,5 ; +4,9] | +0,013 [−0,060 ; +0,087] ; +1,8 [−1,3 ; +5,3] | −0,022 [−0,058 ; +0,013] |
| H = 20 | −0,029 [−0,138 ; +0,078] ; −0,4 [−4,4 ; +3,8] | −0,042 [−0,150 ; +0,068] ; −1,3 [−5,2 ; +2,7] | −0,112 [−0,237 ; +0,007] ; −3,0 [−7,3 ; +1,4] | −0,083 [−0,152 ; −0,023] |
| H = 24 | +0,004 [−0,104 ; +0,117] ; −0,9 [−5,9 ; +4,1] | −0,013 [−0,127 ; +0,110] ; −1,6 [−6,7 ; +3,6] | −0,093 [−0,222 ; +0,037] ; −3,9 [−9,7 ; +1,9] | −0,097 [−0,199 ; −0,012] |
| H = 26 | +0,015 [−0,108 ; +0,141] ; +0,0 [−5,6 ; +5,7] | −0,001 [−0,129 ; +0,132] ; −0,6 [−6,4 ; +5,3] | −0,065 [−0,211 ; +0,072] ; −2,2 [−8,4 ; +4,0] | −0,080 [−0,181 ; +0,018] |
| H = 28 | +0,005 [−0,124 ; +0,136] ; −0,2 [−6,6 ; +6,2] | +0,003 [−0,134 ; +0,149] ; −0,0 [−6,4 ; +6,4] | −0,064 [−0,223 ; +0,096] ; −1,8 [−9,2 ; +5,4] | −0,069 [−0,180 ; +0,037] |
| H = 32 | −0,025 [−0,178 ; +0,127] ; −1,8 [−8,7 ; +5,3] | −0,020 [−0,180 ; +0,144] ; −1,3 [−8,3 ; +6,3] | −0,057 [−0,244 ; +0,125] ; −0,9 [−8,5 ; +7,2] | −0,032 [−0,153 ; +0,083] |
| H = 48 | +0,094 [−0,113 ; +0,320] ; +0,8 [−8,0 ; +9,8] | +0,089 [−0,127 ; +0,324] ; +1,2 [−8,0 ; +10,3] | +0,030 [−0,221 ; +0,310] ; −0,3 [−9,4 ; +8,9] | −0,064 [−0,266 ; +0,113] |

## F. Stabilité annuelle (5 bps)

Cellule : espérance nette par trade en ATR14(t) (trades) ; dernière colonne : PnL composé à 0,25 % par ATR, année par année.

### H = 13

| Configuration | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 | PnL par année |
|---|---|---|---|---|---|---|---|
| C1 — F2b seul, sans stop | +0,49 (137) | −0,04 (128) | −0,01 (110) | −0,06 (119) | −0,43 (105) | +0,06 (96) | +18 % ; −2 % ; −1 % ; −2 % ; −10 % ; +1 % |
| C2 — R2 hors Q4 uniforme, sans stop | +0,36 (215) | −0,13 (224) | −0,15 (197) | +0,14 (216) | −0,46 (196) | +0,43 (192) | +20 % ; −8 % ; −8 % ; +5 % ; −20 % ; +17 % |
| RE-1 — F2b sans stop, F3 SL-B extremum (cooldown) | +0,36 (215) | −0,09 (224) | −0,08 (197) | +0,13 (216) | −0,27 (196) | +0,35 (192) | +20 % ; −6 % ; −5 % ; +7 % ; −12 % ; +13 % |
| RE-1 — F2b sans stop, F3 SL-B extremum (réouverture) | +0,37 (217) | −0,09 (224) | −0,09 (198) | +0,13 (217) | −0,27 (196) | +0,29 (195) | +21 % ; −6 % ; −5 % ; +7 % ; −12 % ; +12 % |
| RE-2 — F2b sans stop, F3 SL-A 2 ATR (cooldown) | +0,35 (215) | −0,09 (224) | −0,10 (197) | +0,09 (216) | −0,24 (196) | +0,36 (192) | +20 % ; −5 % ; −5 % ; +4 % ; −10 % ; +14 % |
| RE-2 — F2b sans stop, F3 SL-A 2 ATR (réouverture) | +0,36 (217) | −0,08 (225) | −0,12 (199) | +0,07 (218) | −0,27 (198) | +0,29 (196) | +20 % ; −5 % ; −6 % ; +4 % ; −12 % ; +12 % |
| RE-3 — F2b SL-A 5 ATR, F3 SL-B extremum (cooldown) | +0,36 (215) | −0,02 (224) | −0,11 (197) | +0,05 (216) | −0,34 (196) | +0,31 (192) | +21 % ; −2 % ; −6 % ; +4 % ; −14 % ; +12 % |
| RE-3 — F2b SL-A 5 ATR, F3 SL-B extremum (réouverture) | +0,38 (217) | −0,02 (224) | −0,12 (198) | +0,05 (217) | −0,34 (196) | +0,26 (195) | +22 % ; −2 % ; −6 % ; +3 % ; −14 % ; +10 % |

### H = 26

| Configuration | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 | PnL par année |
|---|---|---|---|---|---|---|---|
| C1 — F2b seul, sans stop | +0,69 (122) | −0,15 (119) | +0,13 (102) | +0,61 (110) | +0,52 (95) | +0,57 (91) | +22 % ; −5 % ; +1 % ; +16 % ; +13 % ; +11 % |
| C2 — R2 hors Q4 uniforme, sans stop | +0,63 (189) | +0,13 (192) | +0,09 (173) | +0,51 (188) | −0,06 (171) | +0,83 (167) | +32 % ; +5 % ; +2 % ; +24 % ; −3 % ; +30 % |
| RE-1 — F2b sans stop, F3 SL-B extremum (cooldown) | +0,51 (189) | +0,02 (192) | +0,30 (173) | +0,50 (188) | +0,33 (171) | +0,55 (167) | +25 % ; +0 % ; +12 % ; +25 % ; +15 % ; +18 % |
| RE-1 — F2b sans stop, F3 SL-B extremum (réouverture) | +0,53 (192) | +0,04 (199) | +0,32 (177) | +0,47 (193) | +0,39 (175) | +0,30 (172) | +26 % ; +1 % ; +12 % ; +24 % ; +18 % ; +12 % |
| RE-2 — F2b sans stop, F3 SL-A 2 ATR (cooldown) | +0,50 (189) | +0,04 (192) | +0,30 (173) | +0,43 (188) | +0,36 (171) | +0,52 (167) | +24 % ; +1 % ; +11 % ; +22 % ; +16 % ; +18 % |
| RE-2 — F2b sans stop, F3 SL-A 2 ATR (réouverture) | +0,47 (191) | +0,08 (200) | +0,30 (179) | +0,42 (192) | +0,39 (175) | +0,28 (174) | +23 % ; +3 % ; +12 % ; +21 % ; +17 % ; +12 % |
| RE-3 — F2b SL-A 5 ATR, F3 SL-B extremum (cooldown) | +0,61 (189) | +0,09 (192) | +0,28 (173) | +0,30 (188) | +0,02 (171) | +0,41 (167) | +31 % ; +4 % ; +10 % ; +14 % ; +2 % ; +12 % |
| RE-3 — F2b SL-A 5 ATR, F3 SL-B extremum (réouverture) | +0,62 (192) | +0,11 (200) | +0,28 (178) | +0,23 (195) | +0,04 (175) | +0,27 (172) | +32 % ; +5 % ; +11 % ; +12 % ; +3 % ; +8 % |

### H = 48

| Configuration | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 | PnL par année |
|---|---|---|---|---|---|---|---|
| C1 — F2b seul, sans stop | +0,59 (107) | −0,44 (102) | −0,28 (86) | +1,49 (101) | +0,17 (87) | −0,45 (81) | +15 % ; −12 % ; −9 % ; +30 % ; +6 % ; −7 % |
| C2 — R2 hors Q4 uniforme, sans stop | +0,37 (148) | −0,26 (151) | −0,68 (138) | +0,62 (149) | −0,09 (143) | +0,44 (135) | +12 % ; −10 % ; −23 % ; +16 % ; −4 % ; +10 % |
| RE-1 — F2b sans stop, F3 SL-B extremum (cooldown) | +0,24 (148) | −0,49 (151) | −0,14 (138) | +0,82 (149) | +0,37 (143) | +0,19 (135) | +7 % ; −18 % ; −8 % ; +21 % ; +14 % ; +3 % |
| RE-1 — F2b sans stop, F3 SL-B extremum (réouverture) | +0,25 (158) | −0,60 (165) | −0,13 (148) | +0,85 (162) | +0,50 (156) | +0,19 (146) | +8 % ; −23 % ; −8 % ; +24 % ; +20 % ; +5 % |
| RE-2 — F2b sans stop, F3 SL-A 2 ATR (cooldown) | +0,27 (148) | −0,47 (151) | −0,10 (138) | +0,70 (149) | +0,39 (143) | +0,17 (135) | +8 % ; −17 % ; −7 % ; +15 % ; +15 % ; +2 % |
| RE-2 — F2b sans stop, F3 SL-A 2 ATR (réouverture) | +0,30 (159) | −0,57 (165) | −0,10 (150) | +0,78 (162) | +0,47 (158) | +0,19 (147) | +10 % ; −22 % ; −7 % ; +20 % ; +19 % ; +5 % |
| RE-3 — F2b SL-A 5 ATR, F3 SL-B extremum (cooldown) | +0,43 (148) | −0,35 (151) | −0,01 (138) | +0,12 (149) | +0,38 (143) | +0,05 (135) | +15 % ; −13 % ; −5 % ; +1 % ; +14 % ; −0 % |
| RE-3 — F2b SL-A 5 ATR, F3 SL-B extremum (réouverture) | +0,48 (160) | −0,40 (167) | +0,17 (151) | +0,20 (166) | +0,22 (158) | +0,17 (148) | +19 % ; −16 % ; +2 % ; +4 % ; +9 % ; +3 % |

## G. RE-4 — Seuils causaux (contrôle B de C01)

Médiane de `leg_atr` et P75 de `nis_z_100` calculés sur les seuls signaux précédents. Les 500 premiers signaux (janvier à mai 2020) sont exclus des trois variantes, comparées sur la même période.

### Accord des masques avec les seuils de l'échantillon entier (après les 500 premiers signaux)

| Sous-ensemble | échantillon entier, après 500 | glissante 500 signaux | expansive |
|---|---|---|---|
| R2 | 1 348 ; 100,0 % | 1 347 ; 98,6 % | 1 299 ; 99,2 % |
| F2b | 679 ; 100,0 % | 678 ; 99,2 % | 646 ; 99,4 % |
| F3 | 669 ; 100,0 % | 669 ; 99,5 % | 653 ; 99,8 % |

### H = 13

Cellule, à 5 bps : espérance ATR [IC] ; PnL ; MDD ; années à PnL > 0. Puis, à 10 bps : espérance ATR ; PnL.

| Configuration | échantillon entier, après 500 | glissante 500 signaux | expansive |
|---|---|---|---|
| C1 — F2b seul, sans stop | −0,032 [−0,267 ; +0,198] ; −6 % ; −20 % ; 2/6 ‖ 10 bps : −0,171 ; −23 % | −0,045 [−0,293 ; +0,189] ; −8 % ; −23 % ; 2/6 ‖ 10 bps : −0,187 ; −25 % | −0,054 [−0,294 ; +0,182] ; −9 % ; −21 % ; 2/6 ‖ 10 bps : −0,194 ; −25 % |
| C2 — R2 hors Q4 uniforme, sans stop | +0,008 [−0,205 ; +0,201] ; −6 % ; −31 % ; 3/6 ‖ 10 bps : −0,132 ; −34 % | +0,008 [−0,219 ; +0,219] ; −6 % ; −33 % ; 3/6 ‖ 10 bps : −0,134 ; −34 % | −0,012 [−0,225 ; +0,184] ; −11 % ; −32 % ; 3/6 ‖ 10 bps : −0,154 ; −37 % |
| RE-1 — F2b sans stop, F3 SL-B extremum (cooldown) | +0,047 [−0,142 ; +0,233] ; +8 % ; −19 % ; 3/6 ‖ 10 bps : −0,094 ; −24 % | +0,041 [−0,159 ; +0,239] ; +6 % ; −21 % ; 3/6 ‖ 10 bps : −0,101 ; −26 % | +0,026 [−0,169 ; +0,214] ; +2 % ; −20 % ; 3/6 ‖ 10 bps : −0,116 ; −28 % |
| RE-1 — F2b sans stop, F3 SL-B extremum (réouverture) | +0,037 [−0,150 ; +0,224] ; +6 % ; −20 % ; 3/6 ‖ 10 bps : −0,103 ; −26 % | +0,032 [−0,167 ; +0,234] ; +4 % ; −21 % ; 3/6 ‖ 10 bps : −0,110 ; −27 % | +0,017 [−0,177 ; +0,211] ; +0 % ; −20 % ; 3/6 ‖ 10 bps : −0,125 ; −29 % |
| RE-2 — F2b sans stop, F3 SL-A 2 ATR (cooldown) | +0,044 [−0,135 ; +0,226] ; +7 % ; −20 % ; 3/6 ‖ 10 bps : −0,096 ; −25 % | +0,040 [−0,151 ; +0,237] ; +6 % ; −22 % ; 3/6 ‖ 10 bps : −0,102 ; −26 % | +0,022 [−0,163 ; +0,208] ; +1 % ; −22 % ; 3/6 ‖ 10 bps : −0,120 ; −29 % |
| RE-2 — F2b sans stop, F3 SL-A 2 ATR (réouverture) | +0,025 [−0,154 ; +0,208] ; +3 % ; −22 % ; 3/6 ‖ 10 bps : −0,115 ; −28 % | +0,032 [−0,158 ; +0,225] ; +4 % ; −24 % ; 3/6 ‖ 10 bps : −0,110 ; −27 % | +0,006 [−0,178 ; +0,195] ; −3 % ; −24 % ; 3/6 ‖ 10 bps : −0,136 ; −31 % |

### H = 26

Cellule, à 5 bps : espérance ATR [IC] ; PnL ; MDD ; années à PnL > 0. Puis, à 10 bps : espérance ATR ; PnL.

| Configuration | échantillon entier, après 500 | glissante 500 signaux | expansive |
|---|---|---|---|
| C1 — F2b seul, sans stop | +0,372 [+0,040 ; +0,716] ; +61 % ; −13 % ; 5/6 ‖ 10 bps : +0,234 ; +34 % | +0,371 [+0,043 ; +0,733] ; +58 % ; −14 % ; 5/6 ‖ 10 bps : +0,231 ; +32 % | +0,401 [+0,061 ; +0,767] ; +63 % ; −15 % ; 5/6 ‖ 10 bps : +0,260 ; +37 % |
| C2 — R2 hors Q4 uniforme, sans stop | +0,334 [+0,004 ; +0,662] ; +99 % ; −20 % ; 5/6 ‖ 10 bps : +0,195 ; +46 % | +0,357 [+0,026 ; +0,694] ; +104 % ; −20 % ; 4/6 ‖ 10 bps : +0,216 ; +50 % | +0,321 [−0,015 ; +0,649] ; +87 % ; −18 % ; 5/6 ‖ 10 bps : +0,180 ; +39 % |
| RE-1 — F2b sans stop, F3 SL-B extremum (cooldown) | +0,364 [+0,071 ; +0,654] ; +121 % ; −13 % ; 6/6 ‖ 10 bps : +0,225 ; +63 % | +0,366 [+0,072 ; +0,672] ; +118 % ; −12 % ; 6/6 ‖ 10 bps : +0,225 ; +60 % | +0,342 [+0,038 ; +0,645] ; +103 % ; −14 % ; 6/6 ‖ 10 bps : +0,202 ; +51 % |
| RE-1 — F2b sans stop, F3 SL-B extremum (réouverture) | +0,330 [+0,031 ; +0,626] ; +116 % ; −14 % ; 6/6 ‖ 10 bps : +0,191 ; +57 % | +0,332 [+0,036 ; +0,642] ; +112 % ; −13 % ; 6/6 ‖ 10 bps : +0,191 ; +55 % | +0,304 [+0,002 ; +0,609] ; +96 % ; −13 % ; 6/6 ‖ 10 bps : +0,163 ; +44 % |
| RE-2 — F2b sans stop, F3 SL-A 2 ATR (cooldown) | +0,356 [+0,070 ; +0,640] ; +120 % ; −13 % ; 6/6 ‖ 10 bps : +0,216 ; +61 % | +0,356 [+0,063 ; +0,655] ; +116 % ; −12 % ; 6/6 ‖ 10 bps : +0,215 ; +59 % | +0,335 [+0,043 ; +0,629] ; +103 % ; −13 % ; 6/6 ‖ 10 bps : +0,194 ; +50 % |
| RE-2 — F2b sans stop, F3 SL-A 2 ATR (réouverture) | +0,326 [+0,034 ; +0,619] ; +116 % ; −13 % ; 6/6 ‖ 10 bps : +0,187 ; +58 % | +0,325 [+0,032 ; +0,635] ; +112 % ; −12 % ; 6/6 ‖ 10 bps : +0,184 ; +55 % | +0,297 [+0,002 ; +0,602] ; +96 % ; −13 % ; 6/6 ‖ 10 bps : +0,156 ; +44 % |

### H = 48

Cellule, à 5 bps : espérance ATR [IC] ; PnL ; MDD ; années à PnL > 0. Puis, à 10 bps : espérance ATR ; PnL.

| Configuration | échantillon entier, après 500 | glissante 500 signaux | expansive |
|---|---|---|---|
| C1 — F2b seul, sans stop | +0,198 [−0,364 ; +0,788] ; +13 % ; −31 % ; 3/6 ‖ 10 bps : +0,060 ; −4 % | +0,255 [−0,317 ; +0,863] ; +17 % ; −31 % ; 3/6 ‖ 10 bps : +0,114 ; +0 % | +0,235 [−0,326 ; +0,845] ; +16 % ; −31 % ; 3/6 ‖ 10 bps : +0,096 ; −0 % |
| C2 — R2 hors Q4 uniforme, sans stop | +0,032 [−0,403 ; +0,480] ; −13 % ; −37 % ; 3/6 ‖ 10 bps : −0,106 ; −32 % | +0,102 [−0,326 ; +0,549] ; −3 % ; −35 % ; 3/6 ‖ 10 bps : −0,036 ; −24 % | +0,053 [−0,392 ; +0,500] ; −9 % ; −36 % ; 3/6 ‖ 10 bps : −0,087 ; −29 % |
| RE-1 — F2b sans stop, F3 SL-B extremum (cooldown) | +0,170 [−0,217 ; +0,594] ; +13 % ; −30 % ; 4/6 ‖ 10 bps : +0,031 ; −11 % | +0,204 [−0,179 ; +0,625] ; +19 % ; −29 % ; 4/6 ‖ 10 bps : +0,066 ; −7 % | +0,161 [−0,235 ; +0,583] ; +10 % ; −31 % ; 4/6 ‖ 10 bps : +0,022 ; −13 % |
| RE-1 — F2b sans stop, F3 SL-B extremum (réouverture) | +0,198 [−0,228 ; +0,644] ; +22 % ; −36 % ; 4/6 ‖ 10 bps : +0,059 ; −6 % | +0,218 [−0,212 ; +0,682] ; +25 % ; −37 % ; 4/6 ‖ 10 bps : +0,078 ; −4 % | +0,183 [−0,242 ; +0,637] ; +18 % ; −39 % ; 4/6 ‖ 10 bps : +0,043 ; −9 % |
| RE-2 — F2b sans stop, F3 SL-A 2 ATR (cooldown) | +0,165 [−0,222 ; +0,582] ; +12 % ; −28 % ; 4/6 ‖ 10 bps : +0,027 ; −12 % | +0,201 [−0,182 ; +0,608] ; +18 % ; −28 % ; 4/6 ‖ 10 bps : +0,063 ; −8 % | +0,153 [−0,244 ; +0,564] ; +9 % ; −29 % ; 4/6 ‖ 10 bps : +0,014 ; −14 % |
| RE-2 — F2b sans stop, F3 SL-A 2 ATR (réouverture) | +0,185 [−0,233 ; +0,626] ; +19 % ; −35 % ; 4/6 ‖ 10 bps : +0,046 ; −9 % | +0,201 [−0,219 ; +0,640] ; +20 % ; −37 % ; 4/6 ‖ 10 bps : +0,061 ; −8 % | +0,178 [−0,239 ; +0,619] ; +16 % ; −38 % ; 4/6 ‖ 10 bps : +0,038 ; −11 % |
