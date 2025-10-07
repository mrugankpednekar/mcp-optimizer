from __future__ import annotations

from crewai_tools import BaseTool

from ..schemas import LPModel, SolveOptions
from ..solvers.mip.branch_and_cut import solve_mip


class SolveMIPTool(BaseTool):
    name = "solve_mixed_integer_program"
    description = (
        "Solve a mixed-integer linear program using a depth-first branch and bound search."
    )

    def _run(self, model: dict, options: dict | None = None, use_or_tools: bool = False) -> dict:
        mip_model = LPModel.model_validate(model)
        opts = SolveOptions.model_validate(options or {})
        solution = solve_mip(mip_model, opts, use_or_tools=use_or_tools)
        return solution.model_dump()
