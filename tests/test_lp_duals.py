import pytest

from mcp_optimizer.schemas import LPModel, Variable, LinearExpr, LinearTerm, Constraint, SolveOptions
from mcp_optimizer.lp.simplex import simplex_solve


def make_equality_lp() -> LPModel:
    variables = [
        Variable(name="x", lb=0.0),
        Variable(name="y", lb=0.0),
    ]
    constraints = [
        Constraint(
            name="balance",
            lhs=LinearExpr(terms=[LinearTerm(var="x", coef=1.0), LinearTerm(var="y", coef=1.0)], constant=0.0),
            cmp="==",
            rhs=4.0,
        ),
        Constraint(
            name="symmetry",
            lhs=LinearExpr(terms=[LinearTerm(var="x", coef=1.0), LinearTerm(var="y", coef=-1.0)], constant=0.0),
            cmp="==",
            rhs=0.0,
        ),
    ]
    objective = LinearExpr(terms=[LinearTerm(var="x", coef=1.0), LinearTerm(var="y", coef=1.0)], constant=0.0)
    return LPModel(name="dual-test", sense="min", objective=objective, variables=variables, constraints=constraints)


def test_dual_values_for_equalities():
    model = make_equality_lp()
    solution = simplex_solve(model, SolveOptions())

    assert solution.status == "optimal"
    assert solution.duals is not None
    assert solution.duals["balance"] == pytest.approx(-1.0, rel=1e-6, abs=1e-6)
    assert solution.duals["symmetry"] == pytest.approx(0.0, abs=1e-6)
