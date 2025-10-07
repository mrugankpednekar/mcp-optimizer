#!/usr/bin/env python3
import argparse
import json
import random
from pathlib import Path
from typing import List, Optional

from mcp_optimizer.schemas import LPModel, Variable, Constraint, LinearExpr, LinearTerm


def generate_random_lp(num_vars: int, num_constraints: int, seed: Optional[int] = None) -> LPModel:
    rng = random.Random(seed)
    variables = [Variable(name=f"x{i}", lb=0.0) for i in range(num_vars)]
    constraints: List[Constraint] = []
    for j in range(num_constraints):
        terms = [
            LinearTerm(var=f"x{i}", coef=rng.uniform(0.5, 5.0))
            for i in range(num_vars)
        ]
        rhs = rng.uniform(num_vars * 2.0, num_vars * 6.0)
        constraints.append(
            Constraint(
                name=f"c{j}",
                lhs=LinearExpr(terms=terms, constant=0.0),
                cmp="<=",
                rhs=rhs,
            )
        )
    objective = LinearExpr(
        terms=[LinearTerm(var=f"x{i}", coef=rng.uniform(1.0, 4.0)) for i in range(num_vars)],
        constant=0.0,
    )
    return LPModel(
        name="random-lp",
        sense="min",
        objective=objective,
        variables=variables,
        constraints=constraints,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate random feasible LP instances.")
    parser.add_argument("--vars", type=int, default=3, help="Number of variables")
    parser.add_argument("--constraints", type=int, default=3, help="Number of constraints")
    parser.add_argument("--seed", type=int, default=None, help="Random seed")
    parser.add_argument("--count", type=int, default=1, help="Number of instances")
    parser.add_argument("--out", type=Path, default=None, help="Optional output file")
    args = parser.parse_args()

    instances = [
        generate_random_lp(args.vars, args.constraints, (args.seed or 0) + idx)
        for idx in range(args.count)
    ]
    payload = [instance.model_dump() for instance in instances]

    if args.out:
        Path(args.out).write_text(json.dumps(payload, indent=2))
    else:
        print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
