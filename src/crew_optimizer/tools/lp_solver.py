from __future__ import annotations

from crewai_tools import BaseTool

from ..schemas import LPModel, SolveOptions
from ..solvers.lp.simplex import solve_lp


class SolveLPTool(BaseTool):
    name = "solve_linear_program"
    description = (
        "Solve a linear program using SciPy's HiGHS solver. "
        "Provide JSON matching the LPModel schema."
    )

    def _run(self, model: dict, options: dict | None = None) -> dict:
        lp_model = LPModel.model_validate(model)
        opts = SolveOptions.model_validate(options or {})
        solution = solve_lp(lp_model, opts)
        return solution.model_dump()
