"""FastAPI request/response schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class CreateHouseholdRequest(BaseModel):
    name: str
    scenarioMetadata: dict[str, Any] = Field(default_factory=dict)


class AddMemberRequest(BaseModel):
    displayName: str
    role: str
    consentStatus: str = "pending"
    privacyStatus: str = "private_only"


class StartInterviewRequest(BaseModel):
    householdId: str
    memberId: str


class SubmitInterviewRequest(BaseModel):
    transcriptReference: str


class MemberActionRequest(BaseModel):
    memberId: str


class CounterRequest(BaseModel):
    memberId: str
    proposalDeltaSummary: str


class GenerateAgreementRequest(BaseModel):
    householdId: str
    derivedConstraintIds: list[str]


class CreateAssignmentRequest(BaseModel):
    householdId: str
    memberId: str
    task: str
    frequency: str
    estimatedEffort: float
    assignedDate: datetime


class UpdateAssignmentStatusRequest(BaseModel):
    status: str


class RecordMonitoringSignalRequest(BaseModel):
    householdId: str
    assignmentReference: str
    memberReference: str
    expectedContribution: float
    observedContribution: float
    timestamp: datetime


class GenerateDriftReportRequest(BaseModel):
    agreementId: str
    version: int


class StartRenegotiationRequest(BaseModel):
    householdId: str
    driftId: str
