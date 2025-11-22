from __future__ import annotations

import os

from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings

from .schemas import LPModel, SolveOptions
from .solvers.lp.simplex import solve_lp
from .solvers.mip.branch_and_cut import solve_mip
from .solvers.lp.parser import parse_nl_to_lp
from .solvers.lp.diagnostics import analyze_infeasibility
from .solvers.lp.enhanced_parser import parse_word_problem_with_data
from .solvers.lp.assignment_parser import parse_assignment_problem

app = FastMCP("Crew Optimizer")


@app.tool()
def solve_linear_program(model: LPModel, options: SolveOptions | None = None) -> dict:
    """Solve a linear program and return the solution as JSON."""
    opts = options or SolveOptions()
    solution = solve_lp(model, opts)
    return solution.model_dump()


@app.tool()
def solve_mixed_integer_program(
    model: LPModel,
    options: SolveOptions | None = None,
    use_or_tools: bool = False,
) -> dict:
    """Solve a MILP using branch-and-bound or OR-Tools fallback."""
    opts = options or SolveOptions(return_duals=False)
    solution = solve_mip(model, opts, use_or_tools=use_or_tools)
    return solution.model_dump()


@app.tool()
def parse_natural_language(spec: str) -> dict:
    """Parse a natural-language LP specification into structured JSON."""
    model = parse_nl_to_lp(spec)
    return model.model_dump()


@app.tool()
def diagnose_infeasibility(model: LPModel) -> dict:
    """Return heuristic infeasibility analysis for the given LP."""
    return analyze_infeasibility(model)


@app.tool()
def solve_word_problem_with_data(
    problem_description: str,
    file_content: str | None = None,
    file_format: str = "auto",
    encoding: str = "utf-8",
    is_base64: bool = False,
    use_mip: bool = False,
    use_or_tools: bool = False,
    options: SolveOptions | None = None,
) -> dict:
    """
    Solve an optimization word problem using data from a file.

    This tool accepts a natural language problem description and optionally a data file.
    It parses the data, incorporates it into the problem formulation, and solves the
    resulting optimization problem.

    Args:
        problem_description: Natural language description of the optimization problem.
            Example: "Minimize total cost subject to demand constraints using the cost
            and demand data from the file."
        file_content: Content of the data file (CSV, JSON, Excel, etc.). Can be plain
            text or base64 encoded.
        file_format: Format of the file ('csv', 'json', 'excel', 'xlsx', 'auto').
            Defaults to 'auto' for automatic detection.
        encoding: Text encoding for the file (default: 'utf-8').
        is_base64: Whether the file_content is base64 encoded (default: False).
        use_mip: Whether to solve as a mixed-integer program (default: False).
        use_or_tools: Whether to use OR-Tools for MIP solving (default: False).
        options: Optional solver options.

    Returns:
        Dictionary containing:
        - 'model': The parsed LP/MIP model
        - 'solution': The solution to the optimization problem
        - 'data_summary': Summary of the parsed data (if file was provided)
    """
    # Parse the word problem with data
    try:
        model = parse_word_problem_with_data(
            problem_description=problem_description,
            file_content=file_content,
            file_format=file_format,
            encoding=encoding,
            is_base64=is_base64,
        )
    except Exception as e:
        return {
            "error": f"Failed to parse problem: {str(e)}",
            "model": None,
            "solution": None,
        }

    # Prepare solver options
    opts = options or SolveOptions()
    if use_mip:
        opts = SolveOptions(return_duals=False, max_iters=opts.max_iters, tol=opts.tol)

    # Solve the problem
    try:
        if use_mip:
            solution = solve_mip(model, opts, use_or_tools=use_or_tools)
        else:
            solution = solve_lp(model, opts)
    except Exception as e:
        return {
            "error": f"Failed to solve problem: {str(e)}",
            "model": model.model_dump(),
            "solution": None,
        }

    # Prepare response
    result = {
        "model": model.model_dump(),
        "solution": solution.model_dump(),
    }

    # Add data summary if file was provided
    if file_content:
        try:
            from .solvers.lp.data_parser import parse_data_file, format_data_summary

            parsed_data = parse_data_file(
                file_content,
                file_format=file_format,
                encoding=encoding,
                is_base64=is_base64,
            )
            result["data_summary"] = format_data_summary(parsed_data)
        except Exception:
            pass  # Don't fail if data summary can't be generated

    return result


@app.tool()
def solve_assignment_problem(
    energy_file_content: str,
    capacity_file_content: str,
    energy_file_format: str = "csv",
    capacity_file_format: str = "csv",
    options: SolveOptions | None = None,
) -> dict:
    """
    Solve a job assignment problem with energy consumption and machine capacity constraints.

    This tool is specifically designed for assignment/transportation problems where:
    - You have jobs that need to be assigned to machines
    - Each job-machine pair has an energy consumption (or cost)
    - Each machine has a capacity constraint
    - The goal is to minimize total energy consumption while ensuring all jobs are processed

    Args:
        energy_file_content: CSV content with energy consumption matrix.
            First column should be job identifier, remaining columns are machines.
            Example: job,Machine 1,Machine 2,... with energy values in cells.
        capacity_file_content: CSV content with machine capacities.
            Should have columns for machine identifier and capacity.
            Example: machine,capacity with one row per machine.
        energy_file_format: Format of energy file (default: 'csv').
        capacity_file_format: Format of capacity file (default: 'csv').
        options: Optional solver options.

    Returns:
        Dictionary containing:
        - 'model': The parsed LP model
        - 'solution': The solution with optimal assignment
        - 'summary': Summary statistics about the solution
    """
    try:
        # Parse the assignment problem
        model = parse_assignment_problem(
            energy_file_content=energy_file_content,
            capacity_file_content=capacity_file_content,
            energy_file_format=energy_file_format,
            capacity_file_format=capacity_file_format,
        )
    except Exception as e:
        return {
            "error": f"Failed to parse assignment problem: {str(e)}",
            "model": None,
            "solution": None,
        }

    # Solve the problem
    opts = options or SolveOptions()
    try:
        solution = solve_lp(model, opts)
    except Exception as e:
        return {
            "error": f"Failed to solve problem: {str(e)}",
            "model": model.model_dump(),
            "solution": None,
        }

    # Generate summary
    summary = {}
    if solution.status == "optimal" and solution.x:
        # Calculate statistics
        total_energy = solution.objective_value or 0.0

        # Count assignments
        assignments = {}
        for var_name, value in solution.x.items():
            if value and value > 1e-6:  # Non-zero assignment
                # Parse variable name: x_job_machine
                parts = var_name.split("_", 2)
                if len(parts) >= 3:
                    job_id = parts[1]
                    machine = "_".join(parts[2:])
                    if job_id not in assignments:
                        assignments[job_id] = []
                    assignments[job_id].append((machine, value))

        summary = {
            "total_energy": total_energy,
            "num_jobs": len(assignments),
            "num_variables": len([v for v in solution.x.values() if v and v > 1e-6]),
        }

        # Calculate unassigned jobs (if any job is not fully assigned)
        unassigned = []
        for job_id, job_assignments in assignments.items():
            total_assigned = sum(val for _, val in job_assignments)
            if abs(total_assigned - 1.0) > 1e-6:
                unassigned.append(job_id)

        summary["unassigned_jobs"] = len(unassigned)
        summary["unassigned_job_ids"] = unassigned[:10]  # First 10

    return {
        "model": model.model_dump(),
        "solution": solution.model_dump(),
        "summary": summary,
    }


if __name__ == "__main__":
    import sys
    
    # Check if we should use stdio (for Claude Desktop) or HTTP
    transport = os.environ.get("MCP_TRANSPORT", "stdio")
    
    if transport == "stdio" or "--stdio" in sys.argv:
        # Use stdio transport for Claude Desktop
        app.run(transport="stdio")
    else:
        # Use HTTP transport for web-based clients
        port = int(os.environ.get("PORT", "8081"))
        app.settings.host = "0.0.0.0"
        app.settings.port = port
        app.settings.streamable_http_path = "/mcp"
        app.settings.transport_security = TransportSecuritySettings(
            enable_dns_rebinding_protection=False,
            allowed_hosts=["*"],
            allowed_origins=["*"],
        )
        app.run(transport="streamable-http")
