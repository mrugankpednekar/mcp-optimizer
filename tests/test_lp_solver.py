import pytest

from crew_optimizer.schemas import Constraint, LPModel, LinearExpr, LinearTerm, SolveOptions, Variable
from crew_optimizer.solvers.lp.simplex import solve_lp


def make_lp() -> LPModel:
    return LPModel(
        name="diet-toy",
        sense="min",
        objective=LinearExpr(
            terms=[LinearTerm(var="x", coef=3.0), LinearTerm(var="y", coef=2.0)],
            constant=0.0,
        ),
        variables=[
            Variable(name="x", lb=0.0),
            Variable(name="y", lb=0.0),
        ],
        constraints=[
            Constraint(
                name="c1",
                lhs=LinearExpr(
                    terms=[LinearTerm(var="x", coef=1.0), LinearTerm(var="y", coef=2.0)],
                    constant=0.0,
                ),
                cmp=">=",
                rhs=8.0,
            ),
            Constraint(
                name="c2",
                lhs=LinearExpr(
                    terms=[LinearTerm(var="x", coef=3.0), LinearTerm(var="y", coef=1.0)],
                    constant=0.0,
                ),
                cmp=">=",
                rhs=6.0,
            ),
        ],
    )


def test_lp_solver_optimal_solution():
    model = make_lp()
    solution = solve_lp(model, SolveOptions())

    assert solution.status == "optimal"
    assert solution.objective_value == pytest.approx(9.6, rel=1e-6)
    assert solution.x is not None
    assert solution.x["x"] == pytest.approx(0.8, rel=1e-6)
    assert solution.x["y"] == pytest.approx(3.6, rel=1e-6)
