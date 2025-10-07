from __future__ import annotations

from typing import Any, Dict, Optional

from crewai import Agent, Crew, Task

from .agents import lp_agent, mip_agent, parser_agent
from .schemas import LPModel, SolveOptions
from .tools import (
    InfeasibilityAnalysisTool,
    NaturalLanguageParserTool,
    SolveLPTool,
    SolveMIPTool,
)


class OptimizerCrew:
    """Utility to expose optimisation solvers through CrewAI tools and agents."""

    def __init__(self, verbose: bool = False) -> None:
        self.verbose = verbose
        self.lp_tool = SolveLPTool()
        self.mip_tool = SolveMIPTool()
        self.parser_tool = NaturalLanguageParserTool()
        self.diagnostics_tool = InfeasibilityAnalysisTool()
        self._lp_agent: Optional[Agent] = None
        self._mip_agent: Optional[Agent] = None
        self._parser_agent: Optional[Agent] = None

    def solve_lp(self, model: Dict[str, Any], options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        lp_model = LPModel.model_validate(model)
        opts = SolveOptions.model_validate(options or {})
        return self.lp_tool.run(model=lp_model.model_dump(), options=opts.model_dump())

    def solve_mip(
        self,
        model: Dict[str, Any],
        options: Optional[Dict[str, Any]] = None,
        use_or_tools: bool = False,
    ) -> Dict[str, Any]:
        lp_model = LPModel.model_validate(model)
        opts = SolveOptions.model_validate(options or {})
        return self.mip_tool.run(
            model=lp_model.model_dump(),
            options=opts.model_dump(),
            use_or_tools=use_or_tools,
        )

    def parse(self, spec: str) -> Dict[str, Any]:
        return self.parser_tool.run(spec=spec)

    def analyze_infeasibility(self, model: Dict[str, Any]) -> Dict[str, Any]:
        lp_model = LPModel.model_validate(model)
        return self.diagnostics_tool.run(model=lp_model.model_dump())

    def build_crew(self) -> Crew:
        """Create a CrewAI Crew preloaded with optimisation agents."""
        self._lp_agent = lp_agent(verbose=self.verbose)
        self._mip_agent = mip_agent(verbose=self.verbose)
        self._parser_agent = parser_agent(verbose=self.verbose)

        tasks = [
            Task(
                description="Solve LP requests provided in the shared context.",
                agent=self._lp_agent,
                expected_output="Return JSON with simplex solution details.",
            ),
            Task(
                description="Handle MILP requests with branch-and-bound or OR-Tools fallback.",
                agent=self._mip_agent,
                expected_output="Return JSON describing the integer solution.",
            ),
            Task(
                description="Translate optimisation briefs into LP JSON schemas.",
                agent=self._parser_agent,
                expected_output="Return LPModel JSON specification.",
            ),
        ]
        return Crew(
            agents=[self._lp_agent, self._mip_agent, self._parser_agent],
            tasks=tasks,
            verbose=self.verbose,
        )
