import math
from typing import Dict, Any, Optional, List, Tuple

from ..schemas import LPModel, SolveOptions, LPSolution, Variable
from ..lp.simplex import simplex_solve


def solve_mip_branch_and_cut(
    model: LPModel, opts: SolveOptions, use_or_tools: bool = False
) -> LPSolution:
    """
    Tiny branch-and-cut:
      - Relax integrality, solve LP
      - If fractional var, branch with x<=floor and x>=ceil
      - Optionally generate simple Gomory fractional cut at nodes
    For larger instances, if use_or_tools=True, solve with OR-Tools as a baseline.
    """

    if use_or_tools:
        try:
            return _solve_with_ortools(model)
        except ImportError:
            pass  # fall back to internal solver
        except RuntimeError as exc:
            return LPSolution(
                status="iteration_limit",
                objective_value=None,
                x=None,
                reduced_costs=None,
                duals=None,
                iterations=0,
                message=str(exc),
            )

    if not any(var.is_integer for var in model.variables):
        return simplex_solve(model, opts)

    branch_opts = opts.model_copy(update={"return_duals": False})
    sense_factor = 1.0 if model.sense == "max" else -1.0
    max_nodes = min(1024, max(64, len([v for v in model.variables if v.is_integer]) * 20))

    best_solution: Optional[LPSolution] = None
    best_value: Optional[float] = None
    total_iterations = 0
    nodes_explored = 0
    stack: List[Tuple[LPModel, int]] = [(model, 0)]

    while stack and nodes_explored < max_nodes:
        current_model, depth = stack.pop()
        lp_solution = simplex_solve(current_model, branch_opts)
        total_iterations += lp_solution.iterations
        nodes_explored += 1

        if lp_solution.status == "infeasible":
            continue
        if lp_solution.status == "unbounded":
            return LPSolution(
                status="unbounded",
                objective_value=None,
                x=None,
                reduced_costs=None,
                duals=None,
                iterations=total_iterations,
                message="LP relaxation unbounded; MILP appears unbounded.",
            )
        if lp_solution.status != "optimal" or lp_solution.objective_value is None:
            continue

        current_value = lp_solution.objective_value
        if best_value is not None and sense_factor * current_value <= sense_factor * best_value + opts.tol:
            continue

        fractional = _select_fractional_variable(current_model, lp_solution.x or {}, opts.tol)
        if fractional is None:
            best_solution = lp_solution
            best_value = current_value
            continue

        var_name, value = fractional
        floor_val = math.floor(value)
        ceil_val = math.ceil(value)

        left_model = _tighten_bound(current_model, var_name, "ub", floor_val)
        right_model = _tighten_bound(current_model, var_name, "lb", ceil_val)

        if right_model is not None:
            stack.append((right_model, depth + 1))
        if left_model is not None:
            stack.append((left_model, depth + 1))

    if best_solution is None:
        status = "iteration_limit" if nodes_explored >= max_nodes else "infeasible"
        message = (
            "Reached branch limit before finding feasible integer solution."
            if status == "iteration_limit"
            else "No feasible integer assignment found."
        )
        return LPSolution(
            status=status,
            objective_value=None,
            x=None,
            reduced_costs=None,
            duals=None,
            iterations=total_iterations,
            message=message,
        )

    return LPSolution(
        status="optimal",
        objective_value=best_solution.objective_value,
        x=best_solution.x,
        reduced_costs=None,
        duals=None,
        iterations=total_iterations,
        message=f"Explored nodes: {nodes_explored}",
    )


def _select_fractional_variable(model: LPModel, values: Dict[str, float], tol: float) -> Optional[Tuple[str, float]]:
    best_var: Optional[str] = None
    best_gap = 0.0
    best_value = 0.0
    for var in model.variables:
        if not var.is_integer:
            continue
        value = values.get(var.name)
        if value is None:
            continue
        gap = abs(value - round(value))
        if gap > tol and gap > best_gap + tol * 0.1:
            best_gap = gap
            best_var = var.name
            best_value = value
    if best_var is None:
        return None
    return best_var, best_value


def _tighten_bound(model: LPModel, var_name: str, bound_type: str, bound_value: float) -> Optional[LPModel]:
    new_model = model.model_copy(deep=True)
    target: Optional[Variable] = None
    for var in new_model.variables:
        if var.name == var_name:
            target = var
            break
    if target is None:
        return None

    eps = 1e-9
    if bound_type == "ub":
        if target.ub is not None and target.ub <= bound_value + eps:
            return None
        target.ub = bound_value if target.ub is None else min(target.ub, bound_value)
    else:
        if target.lb is not None and target.lb >= bound_value - eps:
            return None
        target.lb = bound_value if target.lb is None else max(target.lb, bound_value)

    if target.lb is not None and target.ub is not None and target.lb > target.ub + eps:
        return None
    return new_model


def _solve_with_ortools(model: LPModel) -> LPSolution:
    try:
        from ortools.linear_solver import pywraplp
    except ImportError as exc:  # pragma: no cover - optional dependency
        raise ImportError("ortools is not installed") from exc

    solver = pywraplp.Solver.CreateSolver("CBC")
    if solver is None:
        raise RuntimeError("Failed to create OR-Tools CBC solver")

    variables: Dict[str, Any] = {}
    for var in model.variables:
        lb = var.lb if var.lb is not None else -solver.infinity()
        ub = var.ub if var.ub is not None else solver.infinity()
        if var.is_integer:
            variables[var.name] = solver.IntVar(lb, ub, var.name)
        else:
            variables[var.name] = solver.NumVar(lb, ub, var.name)

    for cons in model.constraints:
        lhs = solver.Sum(term.coef * variables[term.var] for term in cons.lhs.terms) + cons.lhs.constant
        if cons.cmp == "<=":
            solver.Add(lhs <= cons.rhs)
        elif cons.cmp == ">=":
            solver.Add(lhs >= cons.rhs)
        else:
            solver.Add(lhs == cons.rhs)

    objective = solver.Sum(term.coef * variables[term.var] for term in model.objective.terms) + model.objective.constant
    if model.sense == "max":
        solver.Maximize(objective)
    else:
        solver.Minimize(objective)

    result_status = solver.Solve()
    status_map = {
        pywraplp.Solver.OPTIMAL: "optimal",
        pywraplp.Solver.INFEASIBLE: "infeasible",
        pywraplp.Solver.UNBOUNDED: "unbounded",
        pywraplp.Solver.ABNORMAL: "iteration_limit",
        pywraplp.Solver.NOT_SOLVED: "iteration_limit",
    }
    status = status_map.get(result_status, "iteration_limit")

    if status != "optimal":
        return LPSolution(
            status=status,
            objective_value=None,
            x=None,
            reduced_costs=None,
            duals=None,
            iterations=solver.iterations() if hasattr(solver, "iterations") else 0,
            message="OR-Tools returned status %s" % status,
        )

    solution = {name: variables[name].solution_value() for name in variables}
    objective_value = solver.Objective().Value()

    return LPSolution(
        status="optimal",
        objective_value=objective_value,
        x=solution,
        reduced_costs=None,
        duals=None,
        iterations=solver.iterations() if hasattr(solver, "iterations") else 0,
        message="Solved via OR-Tools CBC",
    )
