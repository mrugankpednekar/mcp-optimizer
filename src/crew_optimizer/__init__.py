"""Crew Optimizer: CrewAI-based LP and MILP solving agents."""

from importlib import import_module

__all__ = ["OptimizerCrew"]

try:  # pragma: no cover - optional dependency
    OptimizerCrew = import_module(".crew", __name__).OptimizerCrew  # type: ignore[attr-defined]
except ModuleNotFoundError as exc:  # pragma: no cover - crewai optional
    _crew_error = exc

    class OptimizerCrew:  # type: ignore[override]
        def __init__(self, *args, **kwargs) -> None:
            raise ModuleNotFoundError(
                "crewai is required for OptimizerCrew; install crewai and crewai-tools."
            ) from _crew_error
