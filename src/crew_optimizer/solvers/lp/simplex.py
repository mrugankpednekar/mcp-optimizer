from __future__ import annotations

from typing import Dict, List, Optional, Tuple

import numpy as np
from scipy.optimize import linprog

from ...schemas import LPSolution, LPModel, SolveOptions


def solve_lp(model: LPModel, options: Optional[SolveOptions] = None) -> LPSolution:
    opts = options or SolveOptions()
    c, constant = _build_objective(model)
    A_ub, b_ub, A_eq, b_eq = _build_constraint_matrices(model)
    bounds = _build_bounds(model)

    sense_factor = 1.0 if model.sense == "min" else -1.0
    res = linprog(
        c * sense_factor,
        A_ub=A_ub if A_ub.size else None,
        b_ub=b_ub if b_ub.size else None,
        A_eq=A_eq if A_eq.size else None,
        b_eq=b_eq if b_eq.size else None,
        bounds=bounds,
        method="highs",
        options={"maxiter": opts.max_iters},
    )

    if not res.success:
        status = _map_status(res.status)
        return LPSolution(
            status=status,
            objective_value=None,
            x=None,
            reduced_costs=None,
            duals=None,
            iterations=res.nit,
            message=res.message,
        )

    values = _map_variables(model, res.x)
    objective = float(res.fun * sense_factor + constant)
    reduced_costs = _extract_reduced_costs(model, res, sense_factor)
    duals = _extract_duals(model, res, sense_factor) if opts.return_duals else None

    return LPSolution(
        status="optimal",
        objective_value=objective,
        x=values,
        reduced_costs=reduced_costs,
        duals=duals,
        iterations=res.nit,
        message=res.message or "",
    )


def _build_objective(model: LPModel) -> Tuple[np.ndarray, float]:
    n = len(model.variables)
    c = np.zeros(n)
    constant = model.objective.constant
    name_to_idx = {var.name: idx for idx, var in enumerate(model.variables)}
    for term in model.objective.terms:
        if term.var not in name_to_idx:
            raise ValueError(f"Objective references unknown variable '{term.var}'")
        c[name_to_idx[term.var]] = term.coef
    return c, constant


def _build_constraint_matrices(model: LPModel) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    n = len(model.variables)
    A_ub: List[List[float]] = []
    b_ub: List[float] = []
    A_eq: List[List[float]] = []
    b_eq: List[float] = []
    name_to_idx = {var.name: idx for idx, var in enumerate(model.variables)}

    for cons in model.constraints:
        row = [0.0] * n
        shift = cons.lhs.constant
        for term in cons.lhs.terms:
            if term.var not in name_to_idx:
                raise ValueError(f"Constraint '{cons.name}' references unknown variable '{term.var}'")
            row[name_to_idx[term.var]] += term.coef
        rhs = cons.rhs - shift

        if cons.cmp == "<=":
            A_ub.append(row)
            b_ub.append(rhs)
        elif cons.cmp == ">=":
            A_ub.append([-value for value in row])
            b_ub.append(-rhs)
        else:
            A_eq.append(row)
            b_eq.append(rhs)

    return (
        np.array(A_ub, dtype=float) if A_ub else np.empty((0, n)),
        np.array(b_ub, dtype=float) if b_ub else np.empty(0),
        np.array(A_eq, dtype=float) if A_eq else np.empty((0, n)),
        np.array(b_eq, dtype=float) if b_eq else np.empty(0),
    )


def _build_bounds(model: LPModel) -> List[Tuple[float | None, float | None]]:
    bounds: List[Tuple[float | None, float | None]] = []
    for var in model.variables:
        lb = None if var.lb is None or np.isneginf(var.lb) else var.lb
        ub = None if var.ub is None or np.isposinf(var.ub) else var.ub
        if lb is not None and ub is not None and lb > ub:
            raise ValueError(f"Variable {var.name} has inconsistent bounds {lb}>{ub}")
        bounds.append((lb, ub))
    return bounds


def _map_variables(model: LPModel, values: np.ndarray) -> Dict[str, float]:
    result: Dict[str, float] = {}
    for var, value in zip(model.variables, values):
        result[var.name] = float(value)
    return result


def _extract_reduced_costs(model: LPModel, res, sense_factor: float) -> Dict[str, float]:
    if not hasattr(res, "reduced_costs") and not hasattr(res, "pi"):
        return {}
    reduced = {}
    costs = getattr(res, "reduced_costs", None)
    if costs is None and hasattr(res, "pi"):
        costs = res.pi
    if costs is None:
        return {}
    for var, value in zip(model.variables, costs):
        reduced[var.name] = float(value * sense_factor)
    return reduced


def _extract_duals(model: LPModel, res, sense_factor: float) -> Dict[str, float]:
    duals: Dict[str, float] = {}
    if hasattr(res, "ineqlin") and "marginals" in res.ineqlin:
        for cons, value in zip(
            [c for c in model.constraints if c.cmp != "=="],
            res.ineqlin["marginals"],
        ):
            duals[cons.name] = float(value * sense_factor)
    if hasattr(res, "eqlin") and "marginals" in res.eqlin:
        for cons, value in zip(
            [c for c in model.constraints if c.cmp == "=="],
            res.eqlin["marginals"],
        ):
            duals[cons.name] = float(value * sense_factor)
    return duals


def _map_status(code: int) -> str:
    mapping = {
        0: "optimal",
        1: "iteration_limit",
        2: "infeasible",
        3: "unbounded",
    }
    return mapping.get(code, "iteration_limit")
