from __future__ import annotations

from typing import Dict, List

from ...schemas import LPModel, SolveOptions
from .simplex import solve_lp


def analyze_infeasibility(model: LPModel) -> Dict[str, object]:
    options = SolveOptions(return_duals=False)
    base_solution = solve_lp(model, options)
    if base_solution.status != "infeasible":
        return {
            "status": base_solution.status,
            "message": base_solution.message or "Model is not infeasible",
            "conflicts": [],
        }

    conflicts: List[str] = []
    for idx, cons in enumerate(model.constraints):
        relaxed = model.model_copy(deep=True)
        relaxed.constraints.pop(idx)
        result = solve_lp(relaxed, options)
        if result.status != "infeasible":
            conflicts.append(cons.name)

    return {
        "status": "infeasible",
        "message": "Identified candidate conflicting constraints",
        "conflicts": conflicts,
    }
