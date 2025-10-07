from __future__ import annotations

from crewai_tools import BaseTool

from ..solvers.lp.parser import parse_nl_to_lp


class NaturalLanguageParserTool(BaseTool):
    name = "parse_lp_specification"
    description = (
        "Parse a compact natural language optimisation prompt into LPModel JSON."
    )

    def _run(self, spec: str) -> dict:
        model = parse_nl_to_lp(spec)
        return model.model_dump()
