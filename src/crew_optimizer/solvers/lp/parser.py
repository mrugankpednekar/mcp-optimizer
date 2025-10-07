from __future__ import annotations

import re
from collections import OrderedDict
from typing import List, Tuple

from ...schemas import Constraint, LPModel, LinearExpr, LinearTerm, Variable

_TOKEN_SPLIT = re.compile(r",|;|\band\b", re.IGNORECASE)
_OBJECTIVE = re.compile(r"^(maximize|minimize|max|min)\s*(.*)$", re.IGNORECASE)
_CMP = re.compile(r"(<=|>=|==|=)")
_TERM = re.compile(r"([+-]?\s*\d*\.?\d*)\s*([A-Za-z_][\w]*)")
_NUMBER = re.compile(r"[+-]?\s*\d+(?:\.\d+)?")
_MULTI_BOUND = re.compile(
    r"^([A-Za-z_][\w]*(?:\s*,\s*[A-Za-z_][\w]*)+)\s*(<=|>=)\s*(-?\d+(?:\.\d+)?)$"
)


def parse_nl_to_lp(spec: str) -> LPModel:
    if not spec or not spec.strip():
        raise ValueError("Specification is empty")

    normalised = " ".join(spec.replace("\n", " ").split())
    parts = re.split(r"subject to|such that|s\.t\.\s*", normalised, flags=re.IGNORECASE)
    obj_part = parts[0].strip()
    cons_part = parts[1].strip() if len(parts) > 1 else ""

    match = _OBJECTIVE.match(obj_part)
    if not match:
        raise ValueError("Objective must start with 'maximize' or 'minimize'")
    sense_word, expr_text = match.groups()
    sense = "max" if sense_word.lower().startswith("max") else "min"
    objective_expr = _parse_expression(expr_text)

    variables = OrderedDict((term.var, Variable(name=term.var, lb=0.0)) for term in objective_expr.terms)
    constraints: List[Constraint] = []

    tokens: List[str] = []
    if cons_part:
        chunks = [chunk.strip() for chunk in re.split(r";|\band\b", cons_part, flags=re.IGNORECASE) if chunk.strip()]
        for chunk in chunks:
            pieces = [piece.strip() for piece in chunk.split(",") if piece.strip()]
            buffer: List[str] = []
            for piece in pieces:
                buffer.append(piece)
                candidate = ", ".join(buffer)
                if _CMP.search(candidate):
                    tokens.append(candidate.strip())
                    buffer.clear()
            if buffer:
                raise ValueError(f"Could not parse constraint segment '{', '.join(buffer)}'")

    for token in tokens:
        m = _MULTI_BOUND.match(token)
        if m:
            names, cmp, rhs = m.groups()
            rhs_value = float(rhs)
            for var_name in [name.strip() for name in names.split(",") if name.strip()]:
                var = variables.setdefault(var_name, Variable(name=var_name, lb=0.0))
                if cmp == "<=":
                    var.ub = rhs_value if var.ub is None else min(var.ub, rhs_value)
                else:
                    var.lb = rhs_value if var.lb is None else max(var.lb, rhs_value)
            continue

        cmp_match = _CMP.search(token)
        if not cmp_match:
            raise ValueError(f"Could not parse constraint segment '{token}'")
        cmp = cmp_match.group(1)
        left = token[: cmp_match.start()].strip()
        right = token[cmp_match.end() :].strip()
        if not left or not right:
            raise ValueError(f"Constraint '{token}' missing lhs or rhs")
        expr = _parse_expression(left)
        rhs_value = float(right)
        if len(expr.terms) == 1 and abs(expr.constant) < 1e-12 and cmp in {"<=", ">="}:
            term = expr.terms[0]
            var_name = term.var
            coef = term.coef
            if abs(coef) < 1e-12:
                raise ValueError(f"Constraint '{token}' has zero coefficient on '{var_name}'")
            if coef < 0:
                coef *= -1
                rhs_value *= -1
                cmp = ">=" if cmp == "<=" else "<="
            if abs(coef - 1.0) > 1e-12:
                raise ValueError(f"Constraint '{token}' is not a simple bound")
            var = variables.setdefault(var_name, Variable(name=var_name, lb=0.0))
            if cmp == "<=":
                var.ub = rhs_value if var.ub is None else min(var.ub, rhs_value)
            else:
                var.lb = rhs_value if var.lb is None else max(var.lb, rhs_value)
            continue

        constraints.append(
            Constraint(
                name=f"c{len(constraints)+1}",
                lhs=expr,
                cmp="==" if cmp == "=" else cmp,
                rhs=rhs_value,
            )
        )
        for term in expr.terms:
            variables.setdefault(term.var, Variable(name=term.var, lb=0.0))

    return LPModel(
        name="parsed",
        sense=sense,
        objective=objective_expr,
        variables=list(variables.values()),
        constraints=constraints,
    )


def _parse_expression(text: str) -> LinearExpr:
    expr = text.replace("*", "")
    coeffs: OrderedDict[str, float] = OrderedDict()
    spans: List[Tuple[int, int]] = []

    for match in _TERM.finditer(expr):
        coef_text = match.group(1).replace(" ", "")
        var_name = match.group(2)
        if coef_text in ("", "+"):
            coef = 1.0
        elif coef_text in ("-", "- "):
            coef = -1.0
        else:
            coef = float(coef_text)
        coeffs[var_name] = coeffs.get(var_name, 0.0) + coef
        spans.append(match.span())

    remaining = list(expr)
    for start, end in spans:
        for idx in range(start, end):
            remaining[idx] = " "
    constant = 0.0
    for num in _NUMBER.finditer("".join(remaining)):
        val = num.group(0).replace(" ", "")
        if val:
            constant += float(val)

    terms = [LinearTerm(var=name, coef=coef) for name, coef in coeffs.items() if abs(coef) > 1e-12]
    return LinearExpr(terms=terms, constant=constant)
