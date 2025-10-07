from __future__ import annotations

from fastmcp import FastMCP

from .schemas import LPModel, SolveOptions
from .solvers.lp.simplex import solve_lp
from .solvers.mip.branch_and_cut import solve_mip
from .solvers.lp.parser import parse_nl_to_lp
from .solvers.lp.diagnostics import analyze_infeasibility

mcp_app = FastMCP("Crew Optimizer")


@mcp_app.tool()
def solve_linear_program(model: LPModel, options: SolveOptions | None = None) -> dict:
    """Solve a linear program and return the solution as JSON."""
    opts = options or SolveOptions()
    solution = solve_lp(model, opts)
    return solution.model_dump()


@mcp_app.tool()
def solve_mixed_integer_program(
    model: LPModel,
    options: SolveOptions | None = None,
    use_or_tools: bool = False,
) -> dict:
    """Solve a MILP using branch-and-bound or OR-Tools fallback."""
    opts = options or SolveOptions(return_duals=False)
    solution = solve_mip(model, opts, use_or_tools=use_or_tools)
    return solution.model_dump()


@mcp_app.tool()
def parse_natural_language(spec: str) -> dict:
    """Parse a natural-language LP specification into structured JSON."""
    model = parse_nl_to_lp(spec)
    return model.model_dump()


@mcp_app.tool()
def diagnose_infeasibility(model: LPModel) -> dict:
    """Return heuristic infeasibility analysis for the given LP."""
    return analyze_infeasibility(model)


if __name__ == "__main__":
    mcp_app.run(transport="http", host="0.0.0.0", port=3333, cors="*")
