import re
from collections import OrderedDict
from typing import List, Tuple

from ..schemas import LPModel, Variable, LinearExpr, LinearTerm, Constraint

_TOKEN_SPLIT = re.compile(r",|;|\band\b", re.IGNORECASE)
_COMPARATOR = re.compile(r"(<=|>=|==|=)")
_MULTI_BOUND = re.compile(
    r"^([A-Za-z_][\w]*(?:\s*,\s*[A-Za-z_][\w]*)+)\s*(<=|>=)\s*(-?\d+(?:\.\d+)?)$"
)
_TERM_PATTERN = re.compile(r"([+-]?\s*\d*\.?\d*)\s*([A-Za-z_][\w]*)")
_NUMBER_PATTERN = re.compile(r"[+-]?\s*\d+(?:\.\d+)?")


def parse_natural_language_spec(spec: str) -> LPModel:
    """
    Extremely small rule-based parser for toy specs like:
      "maximize 3x + 2y subject to x + 2y <= 14, 3x - y >= 0, x <= 5, x,y >= 0"
    Not robust; intended as a demo to show LLM mediation points.
    """

    if not spec or not spec.strip():
        raise ValueError("Specification is empty.")

    normalized = " ".join(spec.replace("\n", " ").split())
    pieces = re.split(r"subject to|such that|s\.t\.", normalized, flags=re.IGNORECASE)
    objective_part = pieces[0].strip()
    constraints_part = pieces[1].strip() if len(pieces) > 1 else ""

    match = re.match(r"(maximize|minimize|max|min)\s*(.*)", objective_part, flags=re.IGNORECASE)
    if not match:
        raise ValueError("Objective must start with 'maximize' or 'minimize'.")
    sense_word = match.group(1).lower()
    sense = "max" if sense_word.startswith("max") else "min"
    objective_expr_str = match.group(2).strip()
    if not objective_expr_str:
        raise ValueError("Objective expression is missing.")

    objective_expr = _parse_linear_expr(objective_expr_str)
    variable_names = OrderedDict((term.var, None) for term in objective_expr.terms)

    constraints: List[Constraint] = []
    if constraints_part:
        tokens = [tok.strip() for tok in _TOKEN_SPLIT.split(constraints_part) if tok.strip()]
    else:
        tokens = []

    for token in tokens:
        multi = _MULTI_BOUND.match(token)
        if multi:
            vars_chunk, cmp, rhs_text = multi.groups()
            rhs_value = float(rhs_text)
            for var_name in [v.strip() for v in vars_chunk.split(",") if v.strip()]:
                expr = LinearExpr(terms=[LinearTerm(var=var_name, coef=1.0)], constant=0.0)
                constraint = Constraint(
                    name=f"c{len(constraints) + 1}",
                    lhs=expr,
                    cmp=cmp,
                    rhs=rhs_value,
                )
                constraints.append(constraint)
                variable_names.setdefault(var_name, None)
            continue

        comp_match = _COMPARATOR.search(token)
        if not comp_match:
            raise ValueError(f"Could not parse constraint segment '{token}'.")
        cmp = comp_match.group(1)
        lhs_str = token[: comp_match.start()].strip()
        rhs_str = token[comp_match.end() :].strip()
        if not lhs_str or not rhs_str:
            raise ValueError(f"Incomplete constraint expression '{token}'.")
        expr = _parse_linear_expr(lhs_str)
        try:
            rhs_value = float(rhs_str)
        except ValueError as exc:  # pragma: no cover - defensive guard
            raise ValueError(f"Right-hand side '{rhs_str}' is not numeric.") from exc
        cmp_norm = "==" if cmp == "=" else cmp
        constraint = Constraint(
            name=f"c{len(constraints) + 1}",
            lhs=expr,
            cmp=cmp_norm,  # type: ignore[arg-type]
            rhs=rhs_value,
        )
        constraints.append(constraint)
        for term in expr.terms:
            variable_names.setdefault(term.var, None)

    variables = [Variable(name=name, lb=0.0) for name in variable_names.keys()]

    return LPModel(
        name="parsed",
        sense=sense,
        objective=objective_expr,
        variables=variables,
        constraints=constraints,
    )


def _parse_linear_expr(expr_str: str) -> LinearExpr:
    expr_clean = expr_str.replace("*", "")
    coeffs: OrderedDict[str, float] = OrderedDict()
    spans: List[Tuple[int, int]] = []

    for match in _TERM_PATTERN.finditer(expr_clean):
        coef_text = match.group(1).replace(" ", "")
        var_name = match.group(2)
        if coef_text in ("", "+", "+"):
            coef = 1.0
        elif coef_text in ("-", "- "):
            coef = -1.0
        else:
            coef = float(coef_text)
        coeffs[var_name] = coeffs.get(var_name, 0.0) + coef
        spans.append(match.span())

    remaining = list(expr_clean)
    for start, end in spans:
        for idx in range(start, end):
            remaining[idx] = " "
    remaining_str = "".join(remaining)

    constant = 0.0
    for num_match in _NUMBER_PATTERN.finditer(remaining_str):
        text = num_match.group(0).replace(" ", "")
        if text:
            constant += float(text)

    terms = [LinearTerm(var=name, coef=coef) for name, coef in coeffs.items() if abs(coef) > 1e-12]
    return LinearExpr(terms=terms, constant=constant)
