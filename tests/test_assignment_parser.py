"""Tests for assignment problem parser."""

import pytest

from crew_optimizer.solvers.lp.assignment_parser import parse_assignment_problem
from crew_optimizer.solvers.lp.simplex import solve_lp
from crew_optimizer.schemas import SolveOptions


def test_assignment_problem_small():
    """Test assignment problem with small dataset."""
    energy_csv = """job,Machine 1,Machine 2
1,10,20
2,15,25"""

    capacity_csv = """machine,capacity
1,1
2,1"""

    model = parse_assignment_problem(
        energy_file_content=energy_csv,
        capacity_file_content=capacity_csv,
    )

    assert model.sense == "min"
    assert len(model.variables) == 4  # 2 jobs × 2 machines
    assert len(model.constraints) == 4  # 2 job constraints + 2 capacity constraints

    # Check that each job has a constraint summing to 1
    job_constraints = [c for c in model.constraints if "job" in c.name]
    assert len(job_constraints) == 2
    for constraint in job_constraints:
        assert constraint.cmp == "=="
        assert constraint.rhs == 1.0

    # Check capacity constraints
    capacity_constraints = [c for c in model.constraints if "capacity" in c.name]
    assert len(capacity_constraints) == 2
    for constraint in capacity_constraints:
        assert constraint.cmp == "<="
        assert constraint.rhs == 1.0


def test_assignment_problem_solve():
    """Test solving a small assignment problem."""
    energy_csv = """job,Machine 1,Machine 2
1,10,20
2,15,25"""

    capacity_csv = """machine,capacity
1,1
2,1"""

    model = parse_assignment_problem(
        energy_file_content=energy_csv,
        capacity_file_content=capacity_csv,
    )

    solution = solve_lp(model, SolveOptions())

    assert solution.status == "optimal"
    assert solution.objective_value is not None
    assert solution.x is not None

    # Check that each job is fully assigned
    job1_vars = {k: v for k, v in solution.x.items() if k.startswith("x_1_")}
    job2_vars = {k: v for k, v in solution.x.items() if k.startswith("x_2_")}

    job1_total = sum(job1_vars.values())
    job2_total = sum(job2_vars.values())

    assert abs(job1_total - 1.0) < 1e-6
    assert abs(job2_total - 1.0) < 1e-6

