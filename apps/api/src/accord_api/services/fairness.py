"""Deterministic placeholder fairness solver implementation."""

from __future__ import annotations

from datetime import timedelta

from ..models import Assignment, AssignmentStatus, PrivacyClassification
from ..solver_interface import DeterministicFairnessSolver, SolverInput, SolverOutput
from ..utils import utcnow


class PlaceholderDeterministicFairnessSolver(DeterministicFairnessSolver):
    """Temporary deterministic solver used until optimization solver is implemented."""

    def generate_plan(self, solver_input: SolverInput) -> SolverOutput:
        if not solver_input.member_ids or not solver_input.task_efforts:
            return SolverOutput(
                proposed_assignments=[],
                fairness_score=0.0,
                rationale="Insufficient members or tasks for proposal.",
                tie_break_trace=["empty_inputs"],
            )

        member_ids = sorted(solver_input.member_ids)
        task_efforts = sorted(solver_input.task_efforts, key=lambda t: (t.estimated_effort, t.task))

        assignments: list[Assignment] = []
        now = utcnow()
        for idx, task_effort in enumerate(task_efforts):
            member_id = member_ids[idx % len(member_ids)]
            assignments.append(
                Assignment(
                    assignment_id=f"proposal-{idx + 1}",
                    member_id=member_id,
                    task=task_effort.task,
                    frequency="weekly",
                    estimated_effort=task_effort.estimated_effort,
                    assigned_date=now + timedelta(days=idx),
                    status=AssignmentStatus.SCHEDULED,
                )
            )

        fairness_score = round(1.0 - (len(task_efforts) % len(member_ids)) * 0.05, 2)
        rationale = "Deterministic placeholder assignment generated from sorted members/tasks."
        return SolverOutput(
            proposed_assignments=assignments,
            fairness_score=max(0.0, fairness_score),
            rationale=rationale,
            tie_break_trace=[
                "member_order:sorted",
                "task_order:effort_then_name",
                "distribution:round_robin",
                f"privacy_filter:{PrivacyClassification.SHAREABLE_DERIVED.value}_only",
            ],
        )
