"""EXP-D02 — walk-forward de RE-1 (protocole du porteur, 2026-10-01 ; `RESEARCH_LOG.md`, entrée EXP-D02).

    from optimization import AssetData, evaluate_is, variant_schedule, oos_candidates, run_oos
    ev = [evaluate_is(data, w) for w in windows]              # grille 5 × 28 × 5 sur chaque IS
    sched, seuils = variant_schedule(ev, "WFO-conjointe")      # paramètres de chaque semestre
    trades = run_oos(data, oos_candidates(data, windows, sched, seuils))

- `engine` : noyau Numba identique à `envelope.stop_trades(..., dynamic=False)`, horizon et stop par signal, fin
  d'IS ; contrôlé trade par trade contre `strategy.run_re1` (Gate 0).
- `windows` : semestres calendaires, IS = 4 semestres précédents, réserve 2026 exclue.
- `universe` : table des signaux d'un atlas (un par R0), seuils de population par fenêtre, candidats de RE-1.
- `objective` : métriques d'IS (espérance en ATR, PnL et MDD valorisé à 0,25 %/ATR, Calmar) du dépôt.
- `selection` : règle de choix du porteur (centre de la plus grande zone connexe à Calmar > 0, repli sur RE-1).
- `walkforward` : grille, évaluation d'un IS, branches, calendriers des 10 séries, course hors échantillon.
- `compare` : écarts appariés par mois (IC 95 %), chemins réordonnés, entrées figées (I-M16).

EXP-D02.1 : verrou distinct de l'horizon (`lock`, option C : l'entrée suivante clôt la position), `superseded`,
inertie de `select_plateau`, `axis_schedule`, grille fine `GRID_R0_FIN`, seuils gelés en IS, retrait des meilleurs
trades (`drop_best`).
"""
from optimization.compare import (SeriesStats, drop_best, frozen_entries, mdd_exits, month_draws, month_index,
                                  paired_comparison, series_stats)
from optimization.engine import prepare_inputs, run_trades, simulate, superseded
from optimization.objective import is_metrics
from optimization.selection import neighbour_mean, plateau_zones, select, select_plateau
from optimization.universe import SignalTable, candidates, signal_table, window_thresholds
from optimization.walkforward import (GRID, GRID_F, GRID_H, GRID_R0, GRID_R0_FIN, RE1_INDEX, RE1_POINT, VARIANTS,
                                      AssetData, Params, axis_schedule, branch_choice, evaluate_is, oos_candidates,
                                      run_oos, variant_schedule)
from optimization.windows import Window, bar_span, in_period, walk_forward_windows

__all__ = ["run_trades", "simulate", "prepare_inputs", "is_metrics", "neighbour_mean", "select", "select_plateau",
           "plateau_zones", "SignalTable", "signal_table", "window_thresholds", "candidates", "GRID", "GRID_R0",
           "GRID_H", "GRID_F", "RE1_POINT", "RE1_INDEX", "VARIANTS", "AssetData", "Params", "evaluate_is",
           "branch_choice", "variant_schedule", "oos_candidates", "run_oos", "Window", "walk_forward_windows",
           "bar_span", "in_period", "SeriesStats", "series_stats", "paired_comparison", "month_index", "month_draws",
           "mdd_exits", "frozen_entries", "superseded", "GRID_R0_FIN", "axis_schedule", "drop_best"]
