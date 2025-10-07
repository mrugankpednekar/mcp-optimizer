import math

from crew_optimizer.schemas import Constraint, LPModel, LinearExpr, LinearTerm, SolveOptions, Variable
from crew_optimizer.solvers.mip.branch_and_cut import solve_mip


def make_mip() -> LPModel:
    return LPModel(
        name="binary",
        sense="max",
        objective=LinearExpr(
            terms=[LinearTerm(var="x", coef=1.0), LinearTerm(var="y", coef=1.0)],
            constant=0.0,
        ),
        variables=[
            Variable(name="x", lb=0.0, ub=1.0, is_integer=True),
            Variable(name="y", lb=0.0, ub=1.0, is_integer=True),
        ],
        constraints=[
            Constraint(
                name="limit",
                lhs=LinearExpr(
                    terms=[LinearTerm(var="x", coef=1.0), LinearTerm(var="y", coef=1.0)],
                    constant=0.0,
                ),
                cmp="<=",
                rhs=1.0,
            )
        ],
    )


def test_mip_solver_integrality():
    model = make_mip()
    solution = solve_mip(model, SolveOptions())

    assert solution.status == "optimal"
    assert solution.x is not None
    total = solution.x["x"] + solution.x["y"]
    assert math.isclose(total, 1.0, abs_tol=1e-6)
    for value in solution.x.values():
        assert math.isclose(value, round(value), abs_tol=1e-6)
