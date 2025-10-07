import numpy as np
from typing import Dict, Tuple, Any, List, Optional, Set

from .utils import build_standard_form
from ..schemas import LPModel, SolveOptions, LPSolution


def simplex_solve(model: LPModel, opts: SolveOptions) -> LPSolution:
    """
    Naive primal simplex with Phase I/II, Bland fallback to avoid cycling.
    Works on small/medium LPs; engineered for clarity, not speed.
    """

    try:
        A, b, c, meta, basis, sense = build_standard_form(model)
    except ValueError as exc:
        return LPSolution(
            status="infeasible",
            objective_value=None,
            x=None,
            reduced_costs=None,
            duals=None,
            iterations=0,
            message=str(exc),
        )

    m, n = A.shape
    use_bland = opts.pivot_rule == "bland"
    iterations = 0

    phase1 = _phase_I(A, b, c, basis, meta, use_bland, opts)
    iterations += phase1.get("iterations", 0)
    if phase1["status"] == "infeasible":
        return LPSolution(
            status="infeasible",
            objective_value=None,
            x=None,
            reduced_costs=None,
            duals=None,
            iterations=iterations,
            message="Infeasible.",
        )
    if phase1["status"] == "iteration_limit":
        return LPSolution(
            status="iteration_limit",
            objective_value=None,
            x=None,
            reduced_costs=None,
            duals=None,
            iterations=iterations,
            message="Hit iteration limit in Phase I.",
        )
    if phase1["status"] == "unbounded":
        return LPSolution(
            status="unbounded",
            objective_value=None,
            x=None,
            reduced_costs=None,
            duals=None,
            iterations=iterations,
            message="Phase I detected unbounded auxiliary problem (likely modelling error).",
        )

    basis = phase1["basis"]

    remaining_iters = max(opts.max_iters - iterations, 1)
    phase2 = _phase_II(A, b, c, basis, sense, meta, use_bland, opts, remaining_iters)
    iterations += phase2.get("iterations", 0)
    status = phase2["status"]

    if status == "iteration_limit":
        return LPSolution(
            status="iteration_limit",
            objective_value=None,
            x=None,
            reduced_costs=None,
            duals=None,
            iterations=iterations,
            message="Hit iteration limit in Phase II.",
        )
    if status == "unbounded":
        return LPSolution(
            status="unbounded",
            objective_value=None,
            x=None,
            reduced_costs=None,
            duals=None,
            iterations=iterations,
            message="Unbounded.",
        )

    x_std = phase2["x"]
    reduced_costs_full = phase2["reduced_costs"]
    duals_vec = phase2["duals"]
    objective = phase2["objective"]

    x_original = _reconstruct_original_solution(meta, x_std)
    reduced_costs = _reconstruct_reduced_costs(meta, reduced_costs_full)
    duals = _map_duals(meta, duals_vec, opts)

    if sense == "max":
        objective_value = meta["objective_constant"] + objective
    else:
        objective_value = meta["objective_constant"] - objective

    return LPSolution(
        status="optimal",
        objective_value=float(objective_value),
        x={k: float(v) for k, v in x_original.items()},
        reduced_costs={k: float(v) for k, v in reduced_costs.items()},
        duals=duals,
        iterations=iterations,
        message="",
    )


def _phase_I(
    A: np.ndarray,
    b: np.ndarray,
    c: np.ndarray,
    basis: List[int],
    meta: Dict[str, Any],
    use_bland: bool,
    opts: SolveOptions,
) -> Dict[str, Any]:
    artificial = set(meta["artificial_indices"])
    if not artificial or A.shape[0] == 0:
        x = _basic_solution(A, b, basis, opts.tol)
        return {
            "status": "feasible",
            "basis": basis.copy(),
            "x": x,
            "iterations": 0,
        }

    c_phase1 = np.zeros_like(c)
    for idx in artificial:
        c_phase1[idx] = -1.0  # maximise => drives artificials to zero

    result = _run_simplex(
        A,
        b,
        c_phase1,
        basis.copy(),
        opts,
        use_bland,
        max_iterations=opts.max_iters,
        forbidden=None,
    )

    if result["status"] != "optimal":
        return result

    x = result["x"]
    sum_artificial = float(sum(x[idx] for idx in artificial))
    if sum_artificial > opts.tol:
        return {
            "status": "infeasible",
            "basis": result["basis"],
            "x": x,
            "iterations": result["iterations"],
        }

    return {
        "status": "feasible",
        "basis": result["basis"],
        "x": x,
        "iterations": result["iterations"],
    }


def _phase_II(
    A: np.ndarray,
    b: np.ndarray,
    c: np.ndarray,
    basis: List[int],
    sense: str,
    meta: Dict[str, Any],
    use_bland: bool,
    opts: SolveOptions,
    max_iterations: int,
) -> Dict[str, Any]:
    forbidden = set(meta["artificial_indices"])
    result = _run_simplex(
        A,
        b,
        c,
        basis.copy(),
        opts,
        use_bland,
        max_iterations=max_iterations,
        forbidden=forbidden,
    )
    return result


def _run_simplex(
    A: np.ndarray,
    b: np.ndarray,
    c: np.ndarray,
    basis: List[int],
    opts: SolveOptions,
    use_bland: bool,
    max_iterations: Optional[int],
    forbidden: Optional[Set[int]],
) -> Dict[str, Any]:
    basis = basis.copy()
    forbidden = set() if forbidden is None else set(forbidden)
    tol = opts.tol
    m, n = A.shape
    iterations = 0
    max_iter = max_iterations if max_iterations is not None else opts.max_iters
    max_iter = max(max_iter, 1)

    if m == 0:
        positive_indices = [j for j in range(n) if j not in forbidden and c[j] > tol]
        if positive_indices:
            return {
                "status": "unbounded",
                "basis": basis.copy(),
                "iterations": iterations,
                "x": np.zeros(n),
                "objective": np.inf,
                "duals": np.zeros(0),
                "reduced_costs": c.copy(),
            }
        reduced = c.copy()
        reduced[np.abs(reduced) < tol] = 0.0
        return {
            "status": "optimal",
            "basis": basis.copy(),
            "iterations": iterations,
            "x": np.zeros(n),
            "objective": 0.0,
            "duals": np.zeros(0),
            "reduced_costs": reduced,
        }

    while True:
        B = A[:, basis]
        try:
            xB = np.linalg.solve(B, b)
        except np.linalg.LinAlgError:
            xB = np.linalg.lstsq(B, b, rcond=None)[0]
        xB[np.abs(xB) < tol] = 0.0
        if np.any(xB < -tol):
            xB = np.maximum(xB, 0.0)

        try:
            y = np.linalg.solve(B.T, c[basis])
        except np.linalg.LinAlgError:
            y = np.linalg.lstsq(B.T, c[basis], rcond=None)[0]
        reduced = c - A.T @ y
        reduced[np.abs(reduced) < tol] = 0.0
        reduced[basis] = 0.0

        entering_candidates = []
        for j in range(n):
            if j in basis or j in forbidden:
                continue
            if reduced[j] > tol:
                entering_candidates.append((j, reduced[j]))

        if not entering_candidates:
            x = np.zeros(n)
            x[basis] = xB
            objective = float(c[basis] @ xB)
            return {
                "status": "optimal",
                "basis": basis.copy(),
                "iterations": iterations,
                "x": x,
                "objective": objective,
                "duals": y,
                "reduced_costs": reduced,
            }

        if iterations >= max_iter:
            x = np.zeros(n)
            x[basis] = xB
            return {
                "status": "iteration_limit",
                "basis": basis.copy(),
                "iterations": iterations,
                "x": x,
                "objective": float(c[basis] @ xB),
                "duals": y,
                "reduced_costs": reduced,
            }

        if use_bland:
            entering = min(j for j, _ in entering_candidates)
        else:
            entering = max(entering_candidates, key=lambda item: item[1])[0]

        d = np.linalg.solve(B, A[:, entering])
        d[np.abs(d) < tol] = 0.0
        if np.all(d <= tol):
            return {
                "status": "unbounded",
                "basis": basis.copy(),
                "iterations": iterations,
                "x": np.zeros(n),
                "objective": np.inf,
                "duals": y,
                "reduced_costs": reduced,
            }

        ratios: List[Tuple[float, int]] = []
        for idx, value in enumerate(d):
            if value > tol:
                ratios.append((xB[idx] / value if value != 0 else np.inf, idx))
        if not ratios:
            return {
                "status": "unbounded",
                "basis": basis.copy(),
                "iterations": iterations,
                "x": np.zeros(n),
                "objective": np.inf,
                "duals": y,
                "reduced_costs": reduced,
            }

        if use_bland:
            theta, pivot_row = min(ratios, key=lambda item: (item[0], basis[item[1]]))
        else:
            theta, pivot_row = min(ratios, key=lambda item: item[0])

        basis[pivot_row] = entering
        iterations += 1


def _basic_solution(A: np.ndarray, b: np.ndarray, basis: List[int], tol: float) -> np.ndarray:
    n = A.shape[1] if A.ndim == 2 else len(basis)
    x = np.zeros(n)
    if A.shape[0] == 0 or len(basis) == 0:
        return x
    B = A[:, basis]
    try:
        xB = np.linalg.solve(B, b)
    except np.linalg.LinAlgError:
        xB = np.linalg.lstsq(B, b, rcond=None)[0]
    xB[np.abs(xB) < tol] = 0.0
    x[basis] = xB
    return x


def _reconstruct_original_solution(meta: Dict[str, Any], x_std: np.ndarray) -> Dict[str, float]:
    result: Dict[str, float] = {}
    for var_name in meta["original_names"]:
        value = meta["offsets"][var_name]
        for idx, coef in meta["components"][var_name]:
            value += coef * x_std[idx]
        if abs(value) < 1e-12:
            value = 0.0
        result[var_name] = value
    return result


def _reconstruct_reduced_costs(meta: Dict[str, Any], reduced: np.ndarray) -> Dict[str, float]:
    rc: Dict[str, float] = {}
    for var_name in meta["original_names"]:
        value = 0.0
        for idx, coef in meta["components"][var_name]:
            value += coef * reduced[idx]
        if abs(value) < 1e-12:
            value = 0.0
        rc[var_name] = value
    return rc


def _map_duals(meta: Dict[str, Any], duals: np.ndarray, opts: SolveOptions) -> Optional[Dict[str, float]]:
    if not opts.return_duals or duals is None or duals.size == 0:
        return None
    result: Dict[str, float] = {}
    for idx, name in enumerate(meta["constraint_names"]):
        value = float(duals[idx])
        if abs(value) < 1e-12:
            value = 0.0
        result[name] = value
    return result
