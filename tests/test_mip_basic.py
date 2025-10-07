import math

import pytest

from mcp_optimizer.schemas import LPModel, Variable, Constraint, LinearExpr, LinearTerm, SolveOptions
from mcp_optimizer.mip.branch_and_cut import solve_mip_branch_and_cut


def make_basic_mip() -> LPModel:
    variables = [
        Variable(name="x", lb=0.0, ub=1.0, is_integer=True),
        Variable(name="y", lb=0.0, ub=1.0, is_integer=True),
    ]
    constraints = [
        Constraint(
            name="limit",
            lhs=LinearExpr(terms=[LinearTerm(var="x", coef=1.0), LinearTerm(var="y", coef=1.0)], constant=0.0),
            cmp="<=",
            rhs=1.0,
        )
    ]
    objective = LinearExpr(terms=[LinearTerm(var="x", coef=1.0), LinearTerm(var="y", coef=1.0)], constant=0.0)
    return LPModel(name="basic-mip", sense="max", objective=objective, variables=variables, constraints=constraints)


def test_branch_and_cut_finds_integer_solution():
    model = make_basic_mip()
    solution = solve_mip_branch_and_cut(model, SolveOptions())

    assert solution.status == "optimal"
    assert solution.x is not None
    total = solution.x["x"] + solution.x["y"]
    assert total == pytest.approx(1.0, abs=1e-6)
    for var in ("x", "y"):
        assert math.isclose(solution.x[var], round(solution.x[var]), abs_tol=1e-6)
