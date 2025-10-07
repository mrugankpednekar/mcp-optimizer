from __future__ import annotations

from crewai import Agent

from .tools import (
    InfeasibilityAnalysisTool,
    NaturalLanguageParserTool,
    SolveLPTool,
    SolveMIPTool,
)


def lp_agent(verbose: bool = False) -> Agent:
    return Agent(
        name="LP Specialist",
        role="Linear programming solver",
        goal="Solve linear programs accurately and report dual information",
        backstory="A veteran operations researcher fluent in simplex and dual analysis.",
        tools=[SolveLPTool(), InfeasibilityAnalysisTool()],
        verbose=verbose,
    )


def mip_agent(verbose: bool = False) -> Agent:
    return Agent(
        name="MILP Strategist",
        role="Mixed-integer optimisation analyst",
        goal="Find high-quality integer solutions using branch and bound or OR-Tools",
        backstory="Specialises in discrete optimisation with pragmatic heuristics.",
        tools=[SolveMIPTool(), InfeasibilityAnalysisTool()],
        verbose=verbose,
    )


def parser_agent(verbose: bool = False) -> Agent:
    return Agent(
        name="Formulation Assistant",
        role="Translates natural language problem statements into structured LP JSON",
        goal="Produce well-formed LP models ready for solving",
        backstory="Enjoys turning ambiguous briefs into precise mathematical models.",
        tools=[NaturalLanguageParserTool()],
        verbose=verbose,
    )
