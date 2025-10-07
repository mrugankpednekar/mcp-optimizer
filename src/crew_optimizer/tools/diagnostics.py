from __future__ import annotations

from crewai_tools import BaseTool

from ..schemas import LPModel
from ..solvers.lp.diagnostics import analyze_infeasibility


class InfeasibilityAnalysisTool(BaseTool):
    name = "analyze_infeasibility"
    description = "Suggest potentially conflicting constraints for infeasible models."

    def _run(self, model: dict) -> dict:
        lp_model = LPModel.model_validate(model)
        report = analyze_infeasibility(lp_model)
        return report
