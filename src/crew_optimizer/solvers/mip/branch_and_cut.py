from __future__ import annotations

import math
from typing import Dict, List, Optional, Tuple

from ...schemas import LPModel, MIPSolution, SolveOptions, Variable
from ..lp.simplex import solve_lp


def solve_mip(
    model: LPModel,
    options: Optional[SolveOptions] = None,
    use_or_tools: bool = False,
) -> MIPSolution:
    opts = options or SolveOptions(return_duals=False)

    if use_or_tools:
        try:
            return _solve_with_ortools(model)
        except Exception as exc:  # pragma: no cover - optional path
            return MIPSolution(
                status="iteration_limit",
                objective_value=None,
                x=None,
                iterations=0,
                message=f"OR-Tools fallback failed: {exc}",
            )

    if not any(var.is_integer for var in model.variables):
        lp_solution = solve_lp(model, opts)
        return MIPSolution(
            status=lp_solution.status,
            objective_value=lp_solution.objective_value,
            x=lp_solution.x,
            iterations=lp_solution.iterations,
            message=lp_solution.message,
        )

    incumbent: Optional[MIPSolution] = None
    stack: List[Tuple[LPModel, int]] = [(model, 0)]
    explored = 0
    max_nodes = max(128, len(model.variables) * 32)
    sense_factor = 1.0 if model.sense == "max" else -1.0

    while stack and explored < max_nodes:
        current, depth = stack.pop()
        lp_solution = solve_lp(current, opts)
        explored += 1

        if lp_solution.status in {"infeasible", "iteration_limit"}:
            continue
        if lp_solution.status == "unbounded":
            return MIPSolution(
                status="unbounded",
                objective_value=None,
                x=None,
                iterations=explored * opts.max_iters,
                message="LP relaxation unbounded",
            )
        if lp_solution.objective_value is None or lp_solution.x is None:
            continue

        if incumbent and sense_factor * lp_solution.objective_value <= sense_factor * incumbent.objective_value + opts.tol:
            continue

        fractional = _find_fractional(current, lp_solution.x, opts.tol)
        if fractional is None:
            incumbent = MIPSolution(
                status="optimal",
                objective_value=lp_solution.objective_value,
                x=lp_solution.x,
                iterations=explored * opts.max_iters,
                message="Feasible integer solution",
            )
            continue

        var_name, value = fractional
        lower_branch = _tighten_bound(current, var_name, "ub", math.floor(value))
        upper_branch = _tighten_bound(current, var_name, "lb", math.ceil(value))

        if upper_branch is not None:
            stack.append((upper_branch, depth + 1))
        if lower_branch is not None:
            stack.append((lower_branch, depth + 1))

    if incumbent:
        return incumbent

    return MIPSolution(
        status="iteration_limit" if explored >= max_nodes else "infeasible",
        objective_value=None,
        x=None,
        iterations=explored * opts.max_iters,
        message="Search exhausted without finding feasible solution",
    )


def _find_fractional(model: LPModel, values: Dict[str, float], tol: float) -> Optional[Tuple[str, float]]:
    best_name: Optional[str] = None
    best_gap = 0.0
    best_value = 0.0
    for var in model.variables:
        if not var.is_integer:
            continue
        value = values.get(var.name)
        if value is None:
            continue
        gap = abs(value - round(value))
        if gap > tol and gap > best_gap:
            best_gap = gap
            best_name = var.name
            best_value = value
    if best_name is None:
        return None
    return best_name, best_value


def _tighten_bound(model: LPModel, name: str, bound: str, value: float) -> Optional[LPModel]:
    new_model = model.model_copy(deep=True)
    var: Optional[Variable] = None
    for v in new_model.variables:
        if v.name == name:
            var = v
            break
    if var is None:
        return None

    if bound == "ub":
        if var.ub is not None and var.ub <= value:
            return None
        var.ub = value
    else:
        if var.lb is not None and var.lb >= value:
            return None
        var.lb = value
    if var.lb is not None and var.ub is not None and var.lb > var.ub:
        return None
    return new_model


def _solve_with_ortools(model: LPModel) -> MIPSolution:
    from ortools.linear_solver import pywraplp  # type: ignore

    solver = pywraplp.Solver.CreateSolver("CBC")
    if solver is None:
        raise RuntimeError("Unable to initialise OR-Tools CBC solver")

    variables: Dict[str, object] = {}
    for var in model.variables:
        lb = var.lb if var.lb is not None else 0.0
        ub = var.ub if var.ub is not None else solver.infinity()
        if var.is_integer:
            var_obj = solver.IntVar(lb, ub, var.name)
        else:
            var_obj = solver.NumVar(lb, ub, var.name)
        variables[var.name] = var_obj

    for cons in model.constraints:
        expr = solver.Sum(term.coef * variables[term.var] for term in cons.lhs.terms) + cons.lhs.constant
        if cons.cmp == "<=":
            solver.Add(expr <= cons.rhs)
        elif cons.cmp == ">=":
            solver.Add(expr >= cons.rhs)
        else:
            solver.Add(expr == cons.rhs)

    objective_expr = solver.Sum(term.coef * variables[term.var] for term in model.objective.terms) + model.objective.constant
    if model.sense == "max":
        solver.Maximize(objective_expr)
    else:
        solver.Minimize(objective_expr)

    status = solver.Solve()
    status_map = {
        pywraplp.Solver.OPTIMAL: "optimal",
        pywraplp.Solver.FEASIBLE: "optimal",
        pywraplp.Solver.INFEASIBLE: "infeasible",
        pywraplp.Solver.UNBOUNDED: "unbounded",
        pywraplp.Solver.ABNORMAL: "iteration_limit",
        pywraplp.Solver.NOT_SOLVED: "iteration_limit",
    }
    mapped = status_map.get(status, "iteration_limit")

    if mapped != "optimal":
        return MIPSolution(
            status=mapped,
            objective_value=None,
            x=None,
            iterations=0,
            message=f"OR-Tools returned status {mapped}",
        )

    values = {name: variables[name].solution_value() for name in variables}
    return MIPSolution(
        status="optimal",
        objective_value=solver.Objective().Value(),
        x=values,
        iterations=int(solver.iterations() if hasattr(solver, "iterations") else 0),
        message="Solved via OR-Tools",
    )
