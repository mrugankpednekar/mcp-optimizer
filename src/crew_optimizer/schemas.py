from __future__ import annotations

from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, Field

Sense = Literal["min", "max"]
Cmp = Literal["<=", ">=", "=="]
PivotRule = Literal["dantzig", "bland"]


class Variable(BaseModel):
    name: str
    lb: float | None = None
    ub: float | None = None
    is_integer: bool = False


class LinearTerm(BaseModel):
    var: str
    coef: float


class LinearExpr(BaseModel):
    terms: List[LinearTerm] = Field(default_factory=list)
    constant: float = 0.0


class Constraint(BaseModel):
    name: str
    lhs: LinearExpr
    cmp: Cmp
    rhs: float


class LPModel(BaseModel):
    name: str = "problem"
    sense: Sense
    objective: LinearExpr
    variables: List[Variable]
    constraints: List[Constraint]

    def variable_index(self) -> Dict[str, int]:
        return {var.name: idx for idx, var in enumerate(self.variables)}


class SolveOptions(BaseModel):
    max_iters: int = 10_000
    tol: float = 1e-9
    pivot_rule: PivotRule = "dantzig"
    return_duals: bool = True


class LPSolution(BaseModel):
    status: Literal["optimal", "infeasible", "unbounded", "iteration_limit"]
    objective_value: Optional[float]
    x: Dict[str, float] | None
    reduced_costs: Dict[str, float] | None
    duals: Dict[str, float] | None
    iterations: int
    message: str = ""


class MIPSolution(BaseModel):
    status: Literal["optimal", "infeasible", "unbounded", "iteration_limit"]
    objective_value: Optional[float]
    x: Dict[str, float] | None
    iterations: int
    message: str = ""
