"""Application service context and dependency container."""

from __future__ import annotations

from dataclasses import dataclass

from ..repositories.in_memory import (
    InMemoryAgreementRepository,
    InMemoryAssignmentRepository,
    InMemoryConstraintRepository,
    InMemoryDriftRepository,
    InMemoryHouseholdRepository,
    InMemoryInterviewRepository,
    InMemoryMemberRepository,
    InMemoryMonitoringRepository,
    InMemoryRenegotiationRepository,
)
from ..utils import CounterIdGenerator
from .drift import DriftDetectionService
from .fairness import PlaceholderDeterministicFairnessSolver


@dataclass(slots=True)
class AppContext:
    households: InMemoryHouseholdRepository
    members: InMemoryMemberRepository
    interviews: InMemoryInterviewRepository
    constraints: InMemoryConstraintRepository
    agreements: InMemoryAgreementRepository
    assignments: InMemoryAssignmentRepository
    monitoring: InMemoryMonitoringRepository
    drift_reports: InMemoryDriftRepository
    renegotiations: InMemoryRenegotiationRepository
    id_gen: CounterIdGenerator
    fairness_solver: PlaceholderDeterministicFairnessSolver
    drift_service: DriftDetectionService

    def reset(self) -> None:
        self.households.clear()
        self.members.clear()
        self.interviews.clear()
        self.constraints.clear()
        self.agreements.clear()
        self.assignments.clear()
        self.monitoring.clear()
        self.drift_reports.clear()
        self.renegotiations.clear()
        self.id_gen.prefix_counters.clear()


def build_context() -> AppContext:
    return AppContext(
        households=InMemoryHouseholdRepository(),
        members=InMemoryMemberRepository(),
        interviews=InMemoryInterviewRepository(),
        constraints=InMemoryConstraintRepository(),
        agreements=InMemoryAgreementRepository(),
        assignments=InMemoryAssignmentRepository(),
        monitoring=InMemoryMonitoringRepository(),
        drift_reports=InMemoryDriftRepository(),
        renegotiations=InMemoryRenegotiationRepository(),
        id_gen=CounterIdGenerator(),
        fairness_solver=PlaceholderDeterministicFairnessSolver(),
        drift_service=DriftDetectionService(),
    )
