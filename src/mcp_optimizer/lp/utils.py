import numpy as np
from typing import Dict, Tuple, List, Any

from ..schemas import LPModel


def build_standard_form(model: LPModel) -> Tuple[np.ndarray, np.ndarray, np.ndarray, Dict[str, Any], List[int], str]:
    """
    Convert general LP to standard form Ax = b, x >= 0 with slacks/artificial vars.
    Return A, b, c, metadata, initial basis indices, and the original sense.
    """

    col_names: List[str] = []
    col_types: List[str] = []
    objective_coeffs_raw: List[float] = []
    rows: List[List[float]] = []
    rhs_values: List[float] = []
    basis: List[int] = []
    row_names: List[str] = []
    row_sources: List[str] = []
    structural_indices: List[int] = []
    artificial_indices: List[int] = []
    slack_indices: List[int] = []

    components: Dict[str, List[Tuple[int, float]]] = {}
    offsets: Dict[str, float] = {}

    def add_column(name: str, col_type: str) -> int:
        col_names.append(name)
        col_types.append(col_type)
        objective_coeffs_raw.append(0.0)
        for row in rows:
            row.append(0.0)
        return len(col_names) - 1

    # Structural variables derived from original variables
    extra_constraints: List[Tuple[str, List[Tuple[str, float]], float, str, float, str]] = []
    for var in model.variables:
        lb = var.lb
        ub = var.ub
        if lb is not None and np.isneginf(lb):
            lb = None
        if ub is not None and np.isposinf(ub):
            ub = None
        if lb is not None and ub is not None and lb > ub:
            raise ValueError(f"Variable {var.name} has inconsistent bounds (lb {lb} > ub {ub}).")

        if lb is None:
            # Free variable -> split into difference of non-negative variables
            idx_pos = add_column(f"{var.name}__pos", "structural")
            idx_neg = add_column(f"{var.name}__neg", "structural")
            components[var.name] = [(idx_pos, 1.0), (idx_neg, -1.0)]
            offsets[var.name] = 0.0
            structural_indices.extend([idx_pos, idx_neg])
        else:
            idx = add_column(f"{var.name}", "structural")
            components[var.name] = [(idx, 1.0)]
            offsets[var.name] = lb
            structural_indices.append(idx)

        if ub is not None:
            # Add upper bound as an inequality: x <= ub
            extra_constraints.append(
                (f"bound_{var.name}_ub", [(var.name, 1.0)], 0.0, "<=", ub, "bound")
            )

    # Build objective coefficients
    objective_constant = model.objective.constant
    for term in model.objective.terms:
        if term.var not in components:
            raise ValueError(f"Objective references unknown variable '{term.var}'.")
        objective_constant += term.coef * offsets[term.var]
        for idx, coef in components[term.var]:
            objective_coeffs_raw[idx] += term.coef * coef

    # Collect constraints (original + bounds)
    constraint_specs: List[Tuple[str, List[Tuple[str, float]], float, str, float, str]] = []
    for cons in model.constraints:
        terms = [(t.var, t.coef) for t in cons.lhs.terms]
        constraint_specs.append((cons.name, terms, cons.lhs.constant, cons.cmp, cons.rhs, "model"))

    constraint_specs.extend(extra_constraints)

    # Build matrix rows
    for name, terms, constant, cmp, rhs, source in constraint_specs:
        coeff_entries: Dict[int, float] = {}
        shift = constant
        for var_name, coef in terms:
            if var_name not in components:
                raise ValueError(f"Constraint '{name}' references unknown variable '{var_name}'.")
            shift += coef * offsets[var_name]
            for idx, comp_coef in components[var_name]:
                coeff_entries[idx] = coeff_entries.get(idx, 0.0) + coef * comp_coef
        rhs_value = rhs - shift

        if rhs_value < 0:
            coeff_entries = {idx: -val for idx, val in coeff_entries.items()}
            rhs_value = -rhs_value
            if cmp == "<=":
                cmp = ">="
            elif cmp == ">=":
                cmp = "<="

        if rhs_value < 0 and abs(rhs_value) > 1e-12:
            raise ValueError(
                f"Constraint '{name}' yields negative right-hand side after standardisation."
            )
        if abs(rhs_value) <= 1e-12:
            rhs_value = 0.0

        if cmp == "<=":
            idx_slack = add_column(f"slack_{name}", "slack")
            coeff_entries[idx_slack] = coeff_entries.get(idx_slack, 0.0) + 1.0
            basis.append(idx_slack)
            slack_indices.append(idx_slack)
        elif cmp == ">=":
            idx_surplus = add_column(f"surplus_{name}", "surplus")
            coeff_entries[idx_surplus] = coeff_entries.get(idx_surplus, 0.0) - 1.0
            idx_art = add_column(f"artificial_{name}", "artificial")
            coeff_entries[idx_art] = coeff_entries.get(idx_art, 0.0) + 1.0
            basis.append(idx_art)
            artificial_indices.append(idx_art)
        else:  # equality
            idx_art = add_column(f"artificial_{name}", "artificial")
            coeff_entries[idx_art] = coeff_entries.get(idx_art, 0.0) + 1.0
            basis.append(idx_art)
            artificial_indices.append(idx_art)

        row = [0.0] * len(col_names)
        for idx, value in coeff_entries.items():
            row[idx] = value
        rows.append(row)
        rhs_values.append(rhs_value)
        row_names.append(name)
        row_sources.append(source)

    if rows:
        A = np.array(rows, dtype=float)
        b = np.array(rhs_values, dtype=float)
    else:
        A = np.zeros((0, len(col_names)), dtype=float)
        b = np.zeros(0, dtype=float)

    c_raw = np.array(objective_coeffs_raw, dtype=float)
    if model.sense == "max":
        c = c_raw.copy()
    else:
        c = -c_raw

    metadata: Dict[str, Any] = {
        "original_names": [var.name for var in model.variables],
        "col_names": col_names,
        "col_types": col_types,
        "components": components,
        "offsets": offsets,
        "constraint_names": row_names,
        "constraint_sources": row_sources,
        "artificial_indices": artificial_indices,
        "slack_indices": slack_indices,
        "structural_indices": structural_indices,
        "objective_constant": objective_constant,
        "objective_structural": c_raw,
    }

    return A, b, c, metadata, basis, model.sense


def analyze_infeasibility_model(model: LPModel) -> Dict[str, Any]:
    """Very small IIS-style heuristic: drop each constraint and re-solve."""

    from ..lp.simplex import simplex_solve  # local import to avoid cycle
    from ..schemas import SolveOptions

    try:
        solution = simplex_solve(model, SolveOptions(return_duals=False))
    except ValueError as exc:  # structural issues detected early
        return {
            "status": "error",
            "message": str(exc),
            "conflicting_constraints": [],
            "suggestions": ["Check variable bounds and ensure lb <= ub."],
        }

    if solution.status != "infeasible":
        return {
            "status": solution.status,
            "message": solution.message or "Model is not infeasible.",
            "conflicting_constraints": [],
            "suggestions": [],
        }

    conflicts: List[str] = []
    for idx, cons in enumerate(model.constraints):
        trimmed_constraints = model.constraints[:idx] + model.constraints[idx + 1 :]
        sub_model = model.model_copy(deep=True)
        sub_model.constraints = trimmed_constraints
        sub_solution = simplex_solve(sub_model, SolveOptions(return_duals=False))
        if sub_solution.status != "infeasible":
            conflicts.append(cons.name)

    suggestions = []
    if conflicts:
        suggestions.append("Relax or inspect the conflicting constraints above.")
    else:
        suggestions.append("Consider relaxing bounds or checking for contradictory requirements.")

    return {
        "status": "infeasible",
        "message": "Detected infeasibility; listed constraints critical to infeasibility.",
        "conflicting_constraints": conflicts,
        "suggestions": suggestions,
    }
