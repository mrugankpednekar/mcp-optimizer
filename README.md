# Crew Optimizer

[![smithery badge](https://smithery.ai/badge/@mrugankpednekar/mcp-optimizer)](https://smithery.ai/server/@mrugankpednekar/mcp-optimizer)

MCP Optimizer is an MCP server that exposes linear (LP) and mixed-integer (MILP) optimization tooling through the official MCP Python SDK. It ships a readable primal simplex implementation (with duals), a tiny branch-and-cut MILP solver with optional OR-Tools fallback, and helper utilities such as a natural-language LP parser, infeasibility diagnostics, examples, tests, Docker packaging, and CI.
Crew Optimizer rebuilds the original optimisation project around the [CrewAI](https://github.com/joaomdmoura/crewai) ecosystem. It provides reusable CrewAI tools and agents capable of solving linear programs via SciPy's HiGHS backend, exploring mixed-integer models with a lightweight branch-and-bound search (or OR-Tools fallback), translating natural language prompts into LP JSON, and diagnosing infeasibility. You can embed the tools inside your own crews or call them programmatically through the `OptimizerCrew` convenience wrapper, or serve them over the MCP protocol for clients such as Smithery.

## Installation

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .[mip]
```

This installs Crew Optimizer together with optional OR-Tools support for MILP solving. Add `pytest`, `ruff`, or other dev tools as needed (`pip install pytest`).

## Quick Usage

```python
from crew_optimizer import OptimizerCrew

crew = OptimizerCrew(verbose=False)

lp_model = {
    "name": "diet-toy",
    "sense": "min",
    "objective": {
        "terms": [
            {"var": "x", "coef": 3},
            {"var": "y", "coef": 2},
        ],
        "constant": 0,
    },
    "variables": [
        {"name": "x", "lb": 0},
        {"name": "y", "lb": 0},
    ],
    "constraints": [
        {
            "name": "c1",
            "lhs": {
                "terms": [
                    {"var": "x", "coef": 1},
                    {"var": "y", "coef": 2},
                ],
                "constant": 0,
            },
            "cmp": ">=",
            "rhs": 8,
        },
        {
            "name": "c2",
            "lhs": {
                "terms": [
                    {"var": "x", "coef": 3},
                    {"var": "y", "coef": 1},
                ],
                "constant": 0,
            },
            "cmp": ">=",
            "rhs": 6,
        },
    ],
}

solution = crew.solve_lp(lp_model)
print(solution)
```

To integrate with a wider multi-agent workflow, call `crew.build_crew()` to obtain a `Crew` populated with the LP, MILP, and parser agents. Provide model inputs through CrewAI’s shared context as usual.

## MCP / Smithery Hosting

Crew Optimizer ships an MCP server (`python -m crew_optimizer.server`) that wraps the same solvers. The repository already contains a Smithery manifest (`smithery.json`) and build config (`smithery.yaml`).

1. Push the repository to GitHub.
2. In Smithery, choose **Publish an MCP Server**, connect GitHub, and select the repo.
3. Smithery installs the package (`pip install .`) and launches `mcp http src/crew_optimizer/server.py --port 3333` using the bundled startup script.
4. The server exposes the following tools:
   - `solve_linear_program`
   - `solve_mixed_integer_program`
   - `parse_natural_language`
   - `diagnose_infeasibility`

For local testing:

```bash
mcp http src/crew_optimizer/server.py --port 3333 --cors "*"
```

## Testing

Install test dependencies (`pip install pytest`) and run:

`.github/workflows/ci.yml` runs Ruff, Black, pytest, and builds the Docker image on every push/PR to `main`.

## Deployment via Smithery

1. Ensure the GitHub repository is public and contains the bundled `smithery.json` manifest.
2. From Smithery, choose **Publish an MCP Server** → **Continue with GitHub**, select the repository, and confirm the entry command `python -m mcp_optimizer.server`.
3. Verify installation from the Smithery catalog, then connect from ChatGPT/Claude MCP clients over HTTP (port 3333) or stdio.

## Installing via Smithery

To install mcp-optimizer automatically via [Smithery](https://smithery.ai/server/@mrugankpednekar/mcp-optimizer):

```bash
npx -y @smithery/cli install @mrugankpednekar/mcp-optimizer
```

## Benchmarks & Limitations
```bash
python -m pytest
```

The suite covers the LP solver, MILP branch-and-bound, and the NL parser.

## Licence

Distributed under the MIT Licence. See `LICENSE` for details.
