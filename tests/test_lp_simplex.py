import json
from pathlib import Path

import pytest

from mcp_optimizer.schemas import SolveOptions, LPModel
from mcp_optimizer.lp.simplex import simplex_solve


def load_example(name: str) -> LPModel:
    data = json.loads(Path(__file__).parent.parent.joinpath("examples", name).read_text())
    return LPModel.model_validate(data)


def test_simplex_solves_small_lp():
    model = load_example("small_lp.json")
    solution = simplex_solve(model, SolveOptions())

    assert solution.status == "optimal"
    assert solution.objective_value == pytest.approx(9.6, rel=1e-6)
    assert solution.x is not None
    assert solution.x["x"] == pytest.approx(0.8, rel=1e-6)
    assert solution.x["y"] == pytest.approx(3.6, rel=1e-6)
