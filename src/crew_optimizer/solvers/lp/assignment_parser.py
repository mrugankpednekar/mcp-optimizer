"""
Specialized parser for assignment/transportation problems with matrix data.

This handles problems like:
- Job assignment to machines
- Transportation problems
- Resource allocation with capacity constraints
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from ...schemas import Constraint, LPModel, LinearExpr, LinearTerm, Variable
from .data_parser import parse_data_file


def parse_assignment_problem(
    energy_file_content: str,
    capacity_file_content: str,
    problem_type: str = "minimize_energy",
    energy_file_format: str = "csv",
    capacity_file_format: str = "csv",
) -> LPModel:
    """
    Parse an assignment problem from energy and capacity data files.

    This creates a linear program for assigning jobs to machines:
    - Variables: x_ij (fraction of job i assigned to machine j)
    - Objective: Minimize total energy consumption
    - Constraints:
      * Each job must be fully processed: sum_j x_ij = 1 for all i
      * Machine capacity: sum_i x_ij <= C_j for all j
      * Non-negativity: x_ij >= 0

    Args:
        energy_file_content: Content of energy consumption matrix (jobs x machines)
        capacity_file_content: Content of machine capacity vector
        problem_type: Type of problem ('minimize_energy' or 'minimize_cost')
        energy_file_format: Format of energy file
        capacity_file_format: Format of capacity file

    Returns:
        LPModel instance
    """
    # Parse energy matrix
    energy_data = parse_data_file(energy_file_content, file_format=energy_file_format)
    if energy_data["rows"] == 0:
        raise ValueError("Energy file is empty")

    # Parse capacity vector
    capacity_data = parse_data_file(capacity_file_content, file_format=capacity_file_format)
    if capacity_data["rows"] == 0:
        raise ValueError("Capacity file is empty")

    # Extract data
    energy_rows = energy_data["data"]
    capacity_rows = capacity_data["data"]

    # Get column names (machine names)
    energy_columns = energy_data["columns"]
    # First column is typically the job identifier
    if len(energy_columns) < 2:
        raise ValueError("Energy file must have at least 2 columns (job_id and machine columns)")

    job_id_col = energy_columns[0]
    machine_cols = energy_columns[1:]

    # Extract capacity mapping
    capacity_map = {}
    capacity_col = None
    machine_id_col = None

    # Find capacity and machine ID columns
    if isinstance(capacity_rows[0], dict):
        cols = list(capacity_rows[0].keys())
        # Look for 'capacity' or 'machine' columns
        for col in cols:
            if "capacity" in col.lower():
                capacity_col = col
            if "machine" in col.lower() or col.lower() in ["id", "machine_id", "j"]:
                machine_id_col = col

        if not capacity_col:
            # Assume last numeric column is capacity
            for col in reversed(cols):
                val = capacity_rows[0].get(col)
                if isinstance(val, (int, float)):
                    capacity_col = col
                    break

        if not machine_id_col:
            # Assume first column is machine ID
            machine_id_col = cols[0]

        # Build capacity map
        for row in capacity_rows:
            if isinstance(row, dict):
                machine_id = str(row.get(machine_id_col, ""))
                capacity_val = row.get(capacity_col)
                if capacity_val is not None:
                    try:
                        capacity_map[machine_id] = float(capacity_val)
                    except (ValueError, TypeError):
                        pass

    # Build variables and objective
    variables: List[Variable] = []
    objective_terms: List[LinearTerm] = []
    var_index_map: Dict[tuple, int] = {}  # (job_id, machine_name) -> variable index

    num_jobs = len(energy_rows)
    num_machines = len(machine_cols)

    # Create variables x_ij for each job-machine pair
    for i, energy_row in enumerate(energy_rows):
        if not isinstance(energy_row, dict):
            continue

        job_id = str(energy_row.get(job_id_col, i + 1))

        for machine_col in machine_cols:
            # Get energy consumption
            energy_val = energy_row.get(machine_col)
            if energy_val is None:
                continue

            try:
                energy = float(energy_val)
            except (ValueError, TypeError):
                continue

            # Create variable name
            var_name = f"x_{job_id}_{machine_col}"
            var_idx = len(variables)
            variables.append(Variable(name=var_name, lb=0.0))
            var_index_map[(job_id, machine_col)] = var_idx

            # Add to objective
            objective_terms.append(LinearTerm(var=var_name, coef=energy))

    # Build constraints
    constraints: List[Constraint] = []

    # Constraint 1: Each job must be fully processed (sum_j x_ij = 1)
    for i, energy_row in enumerate(energy_rows):
        if not isinstance(energy_row, dict):
            continue

        job_id = str(energy_row.get(job_id_col, i + 1))
        job_terms: List[LinearTerm] = []

        for machine_col in machine_cols:
            if (job_id, machine_col) in var_index_map:
                var_name = f"x_{job_id}_{machine_col}"
                job_terms.append(LinearTerm(var=var_name, coef=1.0))

        if job_terms:
            constraints.append(
                Constraint(
                    name=f"job_{job_id}_complete",
                    lhs=LinearExpr(terms=job_terms, constant=0.0),
                    cmp="==",
                    rhs=1.0,
                )
            )

    # Constraint 2: Machine capacity (sum_i x_ij <= C_j)
    import re

    for machine_col in machine_cols:
        # Find capacity for this machine
        capacity = None

        # Extract machine number from column name (e.g., "Machine 1" -> 1, "1" -> 1)
        match = re.search(r"(\d+)", machine_col)
        if match:
            machine_num_str = match.group(1)
            machine_num = int(machine_num_str)

            # Try to find capacity by machine number
            # Check direct match
            capacity = capacity_map.get(machine_num_str) or capacity_map.get(str(machine_num))

            # If not found, try matching by index (machine numbers are 1-indexed)
            if capacity is None:
                # Capacity rows are typically ordered by machine number
                for idx, row in enumerate(capacity_rows):
                    if isinstance(row, dict):
                        row_machine_id = str(row.get(machine_id_col, ""))
                        # Check if this row corresponds to our machine
                        if (
                            row_machine_id == machine_num_str
                            or row_machine_id == str(machine_num)
                            or (machine_id_col and str(idx + 1) == machine_num_str)
                        ):
                            if capacity_col:
                                try:
                                    capacity = float(row.get(capacity_col, 0))
                                    break
                                except (ValueError, TypeError):
                                    pass
                    elif isinstance(row, list) and len(row) >= 2:
                        # Assume first element is machine ID, last is capacity
                        try:
                            row_machine_id = str(row[0])
                            if row_machine_id == machine_num_str or row_machine_id == str(machine_num):
                                capacity = float(row[-1])
                                break
                        except (ValueError, TypeError, IndexError):
                            pass

            # If still not found, use index-based matching (assume ordered list)
            if capacity is None and machine_num <= len(capacity_rows):
                row = capacity_rows[machine_num - 1]  # 1-indexed to 0-indexed
                if isinstance(row, dict) and capacity_col:
                    try:
                        capacity = float(row.get(capacity_col, 0))
                    except (ValueError, TypeError):
                        pass
                elif isinstance(row, list) and len(row) > 1:
                    try:
                        capacity = float(row[-1])  # Assume last element is capacity
                    except (ValueError, TypeError):
                        pass

        if capacity is None or capacity <= 0:
            # Skip this machine if we can't find capacity
            continue

        # Build constraint terms for this machine
        machine_terms: List[LinearTerm] = []
        for i, energy_row in enumerate(energy_rows):
            if not isinstance(energy_row, dict):
                continue

            job_id = str(energy_row.get(job_id_col, i + 1))
            if (job_id, machine_col) in var_index_map:
                var_name = f"x_{job_id}_{machine_col}"
                machine_terms.append(LinearTerm(var=var_name, coef=1.0))

        if machine_terms:
            constraints.append(
                Constraint(
                    name=f"machine_{machine_col}_capacity",
                    lhs=LinearExpr(terms=machine_terms, constant=0.0),
                    cmp="<=",
                    rhs=float(capacity),
                )
            )

    return LPModel(
        name="assignment_problem",
        sense="min",
        objective=LinearExpr(terms=objective_terms, constant=0.0),
        variables=variables,
        constraints=constraints,
    )

