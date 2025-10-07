#!/usr/bin/env python3
import json
import time
from pathlib import Path

from mcp_optimizer.lp.simplex import simplex_solve
from mcp_optimizer.schemas import LPModel, SolveOptions
from scripts.generate_instances import generate_random_lp


def load_example(name: str) -> LPModel:
    path = Path(__file__).resolve().parent.parent / "examples" / name
    return LPModel.model_validate(json.loads(path.read_text()))


def main() -> None:
    opts = SolveOptions()
    cases = [("examples/small_lp.json", load_example("small_lp.json"))]
    for seed in range(3):
        cases.append((f"random-{seed}", generate_random_lp(3, 3, seed)))

    print("name,status,objective,iterations,time_ms")
    for name, model in cases:
        start = time.perf_counter()
        solution = simplex_solve(model, opts)
        elapsed_ms = (time.perf_counter() - start) * 1000
        print(
            f"{name},{solution.status},{solution.objective_value},{solution.iterations},{elapsed_ms:.2f}"
        )


if __name__ == "__main__":
    main()
