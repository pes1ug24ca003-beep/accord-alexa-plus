"""Deterministic fairness solver interface contract (no solver implementation)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from .models import Assignment, DerivedConstraint


@dataclass(slots=True)
class SolverInput:
    household_id: str
    member_ids: list[str]
    constraints: list[DerivedConstraint]
    existing_assignments: list[Assignment]
    horizon_days: int


@dataclass(slots=True)
class SolverOutput:
    proposed_assignments: list[Assignment]
    fairness_score: float
    rationale: str
    tie_break_trace: list[str]


class DeterministicFairnessSolver(Protocol):
    """Contract for deterministic, reproducible fairness planners."""

    def generate_plan(self, solver_input: SolverInput) -> SolverOutput:
        """Return deterministic outputs for identical structured inputs."""
        raise NotImplementedError
