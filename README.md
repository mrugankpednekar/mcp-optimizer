# Crew Optimizer

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
   - `solve_word_problem_with_data` - Solve optimization problems using data from files

For local testing:

```bash
mcp http src/crew_optimizer/server.py --port 3333 --cors "*"
```

## Testing

Install test dependencies (`pip install pytest`) and run:

```bash
python -m pytest
```

The suite covers the LP solver, MILP branch-and-bound, and the NL parser.

## Solving Word Problems with Data Files

The MCP server includes a `solve_word_problem_with_data` tool that can parse data files (CSV, JSON, Excel) and use them to solve optimization word problems. This is particularly useful when you have data in files and want to formulate and solve optimization problems based on that data.

### Example Usage

```python
# Example: Solve a production planning problem with data from a CSV file
csv_data = """product,cost,capacity,demand
Widget,10,100,50
Gadget,15,80,60
Thing,12,120,40"""

problem = """
Minimize total cost subject to:
- Production of each product cannot exceed capacity
- Production must meet demand
- All production quantities are non-negative
"""

# The tool will parse the CSV, extract the cost, capacity, and demand values,
# and formulate the optimization problem automatically.
```

The tool supports:
- **CSV/TSV files**: Automatically detects and parses comma or tab-separated values
- **JSON files**: Parses JSON arrays or objects
- **Excel files**: Requires `pandas` and `openpyxl` (install with `pip install crew-optimizer[excel]`)
- **Auto-detection**: Automatically detects file format if not specified

The parsed data is incorporated into the problem description, allowing the natural language parser to extract values and formulate constraints and objective functions based on the actual data.

## Licence

Distributed under the MIT Licence. See `LICENSE` for details.
