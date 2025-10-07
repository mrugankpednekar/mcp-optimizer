from pydantic import BaseModel, Field
from typing import Literal, List, Dict, Optional

Sense = Literal["min", "max"]
Cmp = Literal["<=", ">=", "=="]


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


class SolveOptions(BaseModel):
    max_iters: int = 10_000
    tol: float = 1e-9
    pivot_rule: Literal["dantzig", "bland"] = "dantzig"
    return_duals: bool = True


class LPSolution(BaseModel):
    status: Literal["optimal", "infeasible", "unbounded", "iteration_limit"]
    objective_value: Optional[float]
    x: Dict[str, float] | None
    reduced_costs: Dict[str, float] | None
    duals: Dict[str, float] | None
    iterations: int
    message: str = ""
