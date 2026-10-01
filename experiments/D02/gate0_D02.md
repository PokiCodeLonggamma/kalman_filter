# EXP-D02 — Gate 0 : rapport de validation

- **Date :** 2026-10-01 06:11 UTC ; durée 54 s ; commit du code : `698d688`.
- **Nature :** contrôle bloquant avant toute grille. Aucun calcul de recherche : seuls des trades et des métriques déjà publiés sont reproduits ; la parité hors du point de RE-1 est vérifiée sans aucune performance calculée ni publiée.
- **Verdict : PASSÉ** (tout écart arrête le script).

## Synthèse

| Contrôle | Règle | Résultat |
|---|---|---|
| G0-1 noyau = RE-1, BTC 2020-2025 | 0 manquant, 0 fantôme, identité barre par barre ; ≤ 1e-5 sur PnL et espérance | 1080 trades sur 1080 ; 0 manquant, 0 fantôme ; identiques à `run_re1` au bit près ; écart au CSV de C02bis (6 chiffres) ≤ 3,1·10⁻⁶ à 5 et 10 bps |
| G0-2 hors du point de RE-1 | identité avec `run_re1` | H = 6 : 1452 trades identiques ; H = 60 : 774 trades identiques ; frontière 0,75 : 1080 trades identiques ; frontière 0,95 : 1080 trades identiques ; R0 = 10 : 937 trades identiques ; R0 = 500 : 656 trades identiques |
| G0-2 paramètres par semestre | identité avec la référence Python ; horizon propre ; au moins un trade à cheval | 530 trades identiques sur 8 semestres ; trades à cheval sur deux semestres : 1 (dont 1 sans stop, à l'horizon de leur signal) |
| G0-3 ancre D01 SOL 2020-2025 | trades = `run_re1` ; métriques à 1e-5 du CSV publié | 769 trades identiques ; 5 bps +0,190 ATR ; 10 bps +0,129 ATR ; écart au CSV ≤ 4,5·10⁻⁶ |
| G0-3 ancre D01 XAU 2020-2025 | trades = `run_re1` ; métriques à 1e-5 du CSV publié | 651 trades identiques ; 4 bps −0,019 ATR ; écart au CSV ≤ 4,5·10⁻⁶ |
| G0-3 ancre D02.0 BTC 2013-2019 | trades = `run_re1` ; métriques à 1e-5 du CSV publié | 1357 trades identiques ; 5 bps −0,045 ATR ; 10 bps −0,146 ATR ; écart au CSV ≤ 2,6·10⁻⁶ |
| G0-3 ancre D02.0 XAU 2009-2019 | trades = `run_re1` ; métriques à 1e-5 du CSV publié | 1253 trades identiques ; 4 bps +0,011 ATR ; écart au CSV ≤ 3,3·10⁻⁶ |
| G0-4 données BTC | empreinte = audit D02.0 ; 22 semestres | `fa38b1796e9ee0db…` ; 2013-01-01 00:00 → 2025-12-31 23:30 ; 22 semestres (2015-01-01 → 2026-01-01) ; panne : 215 barres retirées |
| G0-4 données XAU | empreinte = audit D02.0 ; 29 semestres | `945286592f340ded…` ; 2009-03-15 22:00 → 2025-12-31 21:30 ; 29 semestres (2011-07-01 → 2026-01-01) |
| G0-4 données SOL | empreinte = audit D01 ; 5 semestres | `e52874d28b5567d6…` ; 2021-06-17 16:00 → 2025-12-31 23:30 ; 5 semestres (2023-07-01 → 2026-01-01) |
| G0-4 données AVAX | empreinte = audit D02.0 ; 4 semestres | `5bd5cc38b68e9b70…` ; 2021-09-30 19:00 → 2025-12-31 23:30 ; 4 semestres (2024-01-01 → 2026-01-01) |
| G0-4 réserve 2026 | aucune barre de 2026 lue | fichier BTC 2020 brut jusqu'au 2026-09-15 16:00, lu jusqu'au 2025-12-31 23:30 |
| G0-5 seuils par fenêtre | fenêtre 2020-2025 = seuils gelés, au bit près | `2.823322693433984` ; `1.2245041356145911` ; 7296 signaux |
| G0-6 métriques d'IS | = `strategy.metrics` | écart relatif maximal 0 |

## Temps de calcul (mesure, non bloquante)

- Une évaluation (noyau + métriques) au point de RE-1 sur BTC 2020-2025 (6 ans) : 0,12 ms ; sur un IS de 24 mois : ≈ 0,04 ms.
- Grille du protocole : 42 000 évaluations IS (700 × 60 fenêtres) ≈ 2 s de noyau et de métriques.
- Le coût réel est celui des atlas : BTC 2020-2025, R0 = 10 : 5,3 s, R0 = 500 : 5,4 s ; 20 atlas (4 actifs × 5 R0) sur les séries longues : quelques minutes.

