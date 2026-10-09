"""Initial Accord data model entities and lifecycle rules."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any


class ConsentStatus(str, Enum):
    PENDING = "pending"
    GRANTED = "granted"
    REVOKED = "revoked"


class PrivacyStatus(str, Enum):
    PRIVATE_ONLY = "private_only"
    DERIVED_SHAREABLE = "derived_shareable"


class PrivacyClassification(str, Enum):
    PRIVATE = "private"
    SHAREABLE_DERIVED = "shareable_derived"


class InterviewStatus(str, Enum):
    DRAFT = "draft"
    IN_PROGRESS = "in_progress"
    SUBMITTED = "submitted"
    COMPLETED = "completed"


class AgreementStatus(str, Enum):
    PROPOSED = "proposed"
    UNDER_REVIEW = "under_review"
    ACTIVE = "active"
    SUPERSEDED = "superseded"
    CLOSED = "closed"


class DriftSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class DriftStatus(str, Enum):
    OPEN = "open"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"


_INTERVIEW_TRANSITIONS = {
    InterviewStatus.DRAFT: {InterviewStatus.IN_PROGRESS},
    InterviewStatus.IN_PROGRESS: {InterviewStatus.SUBMITTED},
    InterviewStatus.SUBMITTED: {InterviewStatus.COMPLETED},
    InterviewStatus.COMPLETED: set(),
}

_AGREEMENT_TRANSITIONS = {
    AgreementStatus.PROPOSED: {AgreementStatus.UNDER_REVIEW, AgreementStatus.CLOSED},
    AgreementStatus.UNDER_REVIEW: {
        AgreementStatus.ACTIVE,
        AgreementStatus.CLOSED,
        AgreementStatus.SUPERSEDED,
    },
    AgreementStatus.ACTIVE: {AgreementStatus.SUPERSEDED, AgreementStatus.CLOSED},
    AgreementStatus.SUPERSEDED: set(),
    AgreementStatus.CLOSED: set(),
}


@dataclass(slots=True)
class Member:
    member_id: str
    display_name: str
    role: str
    consent_status: ConsentStatus = ConsentStatus.PENDING
    privacy_status: PrivacyStatus = PrivacyStatus.PRIVATE_ONLY


@dataclass(slots=True)
class Household:
    household_id: str
    name: str
    members: list[Member] = field(default_factory=list)
    scenario_metadata: dict[str, Any] = field(default_factory=dict)

    def add_member(self, member: Member) -> None:
        if any(existing.member_id == member.member_id for existing in self.members):
            raise ValueError(f"Member already exists: {member.member_id}")
        self.members.append(member)


@dataclass(slots=True)
class PrivateInterviewSession:
    session_id: str
    household_id: str
    member_id: str
    status: InterviewStatus = InterviewStatus.DRAFT
    transcript_reference: str | None = None
    extracted_constraint_references: list[str] = field(default_factory=list)

    def transition(self, next_status: InterviewStatus) -> None:
        if next_status not in _INTERVIEW_TRANSITIONS[self.status]:
            raise ValueError(
                f"Invalid interview transition: {self.status.value} -> {next_status.value}"
            )
        self.status = next_status

    def to_private_record(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "household_id": self.household_id,
            "member_id": self.member_id,
            "status": self.status.value,
            "transcript_reference": self.transcript_reference,
            "extracted_constraint_references": list(self.extracted_constraint_references),
        }

    def to_shared_summary(self) -> dict[str, Any]:
        """Safe summary that never includes raw/private transcript references."""
        return {
            "session_id": self.session_id,
            "household_id": self.household_id,
            "member_id": self.member_id,
            "status": self.status.value,
            "extracted_constraint_references": list(self.extracted_constraint_references),
        }


@dataclass(slots=True)
class DerivedConstraint:
    constraint_id: str
    member_id: str
    category: str
    preference_or_requirement: str
    importance_weight: float
    flexibility: float
    privacy_classification: PrivacyClassification
    source_session_reference: str


@dataclass(slots=True)
class Assignment:
    assignment_id: str
    member_id: str
    task: str
    frequency: str
    estimated_effort: float
    assigned_date: datetime
    status: str


@dataclass(slots=True)
class Counteroffer:
    member_id: str
    message: str
    submitted_at: datetime


@dataclass(slots=True)
class AgreementVersion:
    agreement_id: str
    version: int
    status: AgreementStatus
    proposal: list[Assignment]
    fairness_score: float
    rationale: str
    approvals: list[str] = field(default_factory=list)
    vetoes: list[str] = field(default_factory=list)
    counteroffers: list[Counteroffer] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def transition(self, next_status: AgreementStatus) -> None:
        if next_status not in _AGREEMENT_TRANSITIONS[self.status]:
            raise ValueError(
                f"Invalid agreement transition: {self.status.value} -> {next_status.value}"
            )
        self.status = next_status

    def register_approval(self, member_id: str) -> None:
        if member_id not in self.approvals:
            self.approvals.append(member_id)

    def register_veto(self, member_id: str) -> None:
        if member_id not in self.vetoes:
            self.vetoes.append(member_id)

    def register_counteroffer(self, counteroffer: Counteroffer) -> None:
        self.counteroffers.append(counteroffer)


@dataclass(slots=True)
class MonitoringSignal:
    signal_id: str
    assignment_reference: str
    member_reference: str
    expected_contribution: float
    observed_contribution: float
    timestamp: datetime


@dataclass(slots=True)
class DriftReport:
    drift_id: str
    agreement_version_reference: str
    affected_members: list[str]
    detected_signals: list[str]
    severity: DriftSeverity
    explanation: str
    recommended_action: str
    status: DriftStatus = DriftStatus.OPEN
