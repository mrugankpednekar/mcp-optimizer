from mcp.server.fastmcp import FastMCP
from .schemas import LPModel, SolveOptions
from .lp.simplex import simplex_solve
from .mip.branch_and_cut import solve_mip_branch_and_cut
from .lp.parser import parse_natural_language_spec
from .lp.utils import analyze_infeasibility_model

mcp = FastMCP("MCP Optimizer")


@mcp.tool()
def solve_lp(model: LPModel, options: SolveOptions | None = None) -> dict:
    "Solve a linear program via primal simplex and return solution dict."
    opts = options or SolveOptions()
    return simplex_solve(model, opts).model_dump()


@mcp.tool()
def solve_mip(model: LPModel, use_or_tools: bool = False, options: SolveOptions | None = None) -> dict:
    "Solve a MILP via tiny branch-and-cut (or OR-Tools if requested)."
    opts = options or SolveOptions(return_duals=False)
    return solve_mip_branch_and_cut(model, opts, use_or_tools=use_or_tools).model_dump()


@mcp.tool()
def parse_nl_to_lp(spec: str) -> dict:
    "Parse a small natural-language spec into a structured LPModel JSON."
    return parse_natural_language_spec(spec).model_dump()


@mcp.tool()
def analyze_infeasibility(model: LPModel) -> dict:
    "Return basic infeasibility diagnostics (IIS heuristic, conflicting constraints)."
    return analyze_infeasibility_model(model)


if __name__ == "__main__":
    # Allow: `uv run mcp dev src/mcp_optimizer/server.py` or pack as stdio/http via CLI
    mcp.run()
