from crew_optimizer.solvers.lp.parser import parse_nl_to_lp


def test_parser_outputs_expected_variables():
    spec = "maximize 3x + 2y subject to x + 2y <= 14, 3x - y >= 0, x <= 5, x,y >= 0"
    model = parse_nl_to_lp(spec)

    assert {v.name for v in model.variables} == {"x", "y"}
    assert model.sense == "max"
    assert len(model.constraints) == 2

    bounds = {var.name: (var.lb, var.ub) for var in model.variables}
    assert bounds["x"] == (0.0, 5.0)
    assert bounds["y"] == (0.0, None)
