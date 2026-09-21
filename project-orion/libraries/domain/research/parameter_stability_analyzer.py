"""Parameter sensitivity, stability surface, and cliff detection analyzer."""

from __future__ import annotations

import logging
from typing import Any

from libraries.domain.research.optimization_models import (
    OptimizationCandidate,
    ParameterSpaceDefinition,
    ParameterStabilityAnalysis,
)

logger = logging.getLogger("research.parameter_stability")


class ParameterStabilityAnalyzer:
    """Analyzes the parameter neighborhood around optimal configurations to distinguish cliffs from plateaus."""

    @classmethod
    def analyze_stability(
        cls,
        best_candidate: OptimizationCandidate,
        all_candidates: list[OptimizationCandidate],
        space: ParameterSpaceDefinition,
    ) -> ParameterStabilityAnalysis:
        """Evaluate neighborhood stability around the top-ranked parameter candidate."""
        optimal_params = dict(best_candidate.parameters)
        opt_score = best_candidate.fitness_score

        # Find 1-step adjacent neighbors
        neighbors = cls._find_adjacent_neighbors(optimal_params, all_candidates, space)

        if not neighbors:
            # No adjacent neighbors found (e.g., coarse grid or random search with sparse points)
            return ParameterStabilityAnalysis(
                optimal_parameters=optimal_params,
                plateau_stability_score=0.5,
                max_neighbor_drop_pct=0.0,
                is_cliff=False,
                cliff_details="No adjacent parameter neighbors available in the search space to assess stability.",
                adjacent_evaluations=(),
            )

        neighbor_evals: list[dict[str, Any]] = []
        drops: list[float] = []
        cliff_triggers: list[str] = []

        for p_name, neighbor_cand in neighbors:
            n_score = neighbor_cand.fitness_score
            n_sharpe = neighbor_cand.sharpe_ratio

            # Calculate relative drop from optimal
            if abs(opt_score) > 0.001:
                drop_pct = max(0.0, (opt_score - n_score) / abs(opt_score)) * 100.0
            else:
                drop_pct = 0.0

            drops.append(drop_pct)

            neighbor_evals.append({
                "varied_parameter": p_name,
                "neighbor_parameters": dict(neighbor_cand.parameters),
                "fitness_score": n_score,
                "sharpe_ratio": n_sharpe,
                "drop_pct": round(drop_pct, 2),
            })

            # Cliff condition: drop exceeds 40% or Sharpe turns negative from positive
            if drop_pct >= 40.0 or (best_candidate.sharpe_ratio > 0.5 and n_sharpe < 0.0):
                cliff_triggers.append(
                    f"Parameter '{p_name}' shifted to {neighbor_cand.parameters.get(p_name)} produces a {drop_pct:.1f}% drop (Sharpe {n_sharpe:.2f})"
                )

        max_drop = max(drops) if drops else 0.0
        mean_drop = sum(drops) / len(drops) if drops else 0.0

        # Plateau score: 1.0 when mean drop is 0, 0.0 when mean drop >= 100%
        plateau_score = max(0.0, min(1.0, 1.0 - (mean_drop / 100.0)))
        is_cliff = len(cliff_triggers) > 0

        if is_cliff:
            cliff_details = (
                "PARAMETER CLIFF DETECTED: The optimal configuration is isolated on a narrow performance spike. "
                + "; ".join(cliff_triggers)
            )
        elif plateau_score >= 0.80:
            cliff_details = (
                f"ROBUST PARAMETER PLATEAU: Surrounding parameter neighbors maintain high performance "
                f"(average variation: {mean_drop:.1f}%). The strategy exhibits broad parameter stability."
            )
        else:
            cliff_details = (
                f"MODERATE STABILITY: Average neighbor performance drop is {mean_drop:.1f}%. "
                f"No acute cliffs detected, but parameters exhibit moderate sensitivity."
            )

        return ParameterStabilityAnalysis(
            optimal_parameters=optimal_params,
            plateau_stability_score=round(plateau_score, 4),
            max_neighbor_drop_pct=round(max_drop, 2),
            is_cliff=is_cliff,
            cliff_details=cliff_details,
            adjacent_evaluations=tuple(neighbor_evals),
        )

    @staticmethod
    def _find_adjacent_neighbors(
        optimal_params: dict[str, Any],
        candidates: list[OptimizationCandidate],
        space: ParameterSpaceDefinition,
    ) -> list[tuple[str, OptimizationCandidate]]:
        """Find candidates that differ from optimal_params by exactly one parameter."""
        neighbors: list[tuple[str, OptimizationCandidate]] = []
        range_map = {r.name: r for r in space.ranges}

        for cand in candidates:
            cand_params = dict(cand.parameters)
            if cand_params == optimal_params:
                continue

            # Check differing keys
            differing_keys = [k for k in optimal_params if cand_params.get(k) != optimal_params.get(k)]
            if len(differing_keys) == 1:
                p_name = differing_keys[0]
                pr = range_map.get(p_name)
                if pr and pr.step is not None:
                    opt_val = float(optimal_params[p_name])
                    cand_val = float(cand_params[p_name])
                    # Check if step difference is roughly 1 step
                    step_diff = abs(cand_val - opt_val)
                    if step_diff <= float(pr.step) * 1.5:
                        neighbors.append((p_name, cand))

        return neighbors
