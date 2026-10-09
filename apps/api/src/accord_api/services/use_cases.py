"""Application use-cases orchestrating repositories and domain rules."""

from __future__ import annotations

from datetime import datetime

from ..errors import ApiError
from ..models import (
    AgreementStatus,
    AgreementVersion,
    Assignment,
    AssignmentStatus,
    ConsentStatus,
    Counteroffer,
    DerivedConstraint,
    DriftReport,
    DriftStatus,
    Household,
    InterviewStatus,
    Member,
    MonitoringSignal,
    PrivacyClassification,
    PrivacyStatus,
    PrivateInterviewSession,
    RenegotiationCycle,
    RenegotiationStatus,
)
from ..privacy import RESOURCE_NOT_FOUND
from ..solver_interface import SolverInput, TaskEffort
from ..utils import utcnow
from .context import AppContext
from .simulation_adapter import SimulationAdapter


class AccordService:
    def __init__(self, ctx: AppContext) -> None:
        self.ctx = ctx
        self.sim_adapter = SimulationAdapter()

    def _require_household(self, household_id: str) -> Household:
        household = self.ctx.households.get(household_id)
        if not household:
            raise RESOURCE_NOT_FOUND
        return household

    def _require_member(self, member_id: str) -> Member:
        member = self.ctx.members.get(member_id)
        if not member:
            raise RESOURCE_NOT_FOUND
        return member

    def _require_household_membership(self, household_id: str, requester_member_id: str) -> None:
        household = self._require_household(household_id)
        if requester_member_id not in {m.member_id for m in household.members}:
            raise RESOURCE_NOT_FOUND

    def create_household(self, name: str, scenario_metadata: dict[str, str]) -> Household:
        household = Household(
            household_id=self.ctx.id_gen.next("household"),
            name=name,
            scenario_metadata=dict(scenario_metadata),
        )
        return self.ctx.households.create(household)

    def get_household(self, household_id: str) -> Household:
        return self._require_household(household_id)

    def add_member(
        self,
        household_id: str,
        display_name: str,
        role: str,
        consent_status: ConsentStatus = ConsentStatus.PENDING,
        privacy_status: PrivacyStatus = PrivacyStatus.PRIVATE_ONLY,
    ) -> Member:
        household = self._require_household(household_id)
        member = Member(
            member_id=self.ctx.id_gen.next("member"),
            display_name=display_name,
            role=role,
            consent_status=consent_status,
            privacy_status=privacy_status,
        )
        self.ctx.members.add(household_id, member)
        household.add_member(member)
        return member

    def list_members(self, household_id: str) -> list[Member]:
        self._require_household(household_id)
        return self.ctx.members.list_by_household(household_id)

    def start_interview(self, household_id: str, member_id: str) -> PrivateInterviewSession:
        self._require_household(household_id)
        self._require_member(member_id)
        session = PrivateInterviewSession(
            session_id=self.ctx.id_gen.next("session"),
            household_id=household_id,
            member_id=member_id,
            status=InterviewStatus.STARTED,
        )
        return self.ctx.interviews.create(session)

    def submit_interview(
        self, session_id: str, requester_member_id: str, transcript_reference: str
    ) -> PrivateInterviewSession:
        session = self.ctx.interviews.get(session_id)
        if not session:
            raise RESOURCE_NOT_FOUND
        if session.member_id != requester_member_id:
            raise RESOURCE_NOT_FOUND
        session.transcript_reference = transcript_reference
        session.transition(InterviewStatus.SUBMITTED)
        return self.ctx.interviews.update(session)

    def complete_interview(self, session_id: str, requester_member_id: str) -> PrivateInterviewSession:
        session = self.ctx.interviews.get(session_id)
        if not session:
            raise RESOURCE_NOT_FOUND
        if session.member_id != requester_member_id:
            raise RESOURCE_NOT_FOUND
        session.transition(InterviewStatus.COMPLETED)
        return self.ctx.interviews.update(session)

    def get_private_interview(
        self, session_id: str, requester_member_id: str
    ) -> PrivateInterviewSession:
        session = self.ctx.interviews.get(session_id)
        if not session or session.member_id != requester_member_id:
            raise RESOURCE_NOT_FOUND
        return session

    def derive_constraints(
        self, session_id: str, requester_member_id: str
    ) -> list[DerivedConstraint]:
        session = self.get_private_interview(session_id, requester_member_id)
        if session.status != InterviewStatus.COMPLETED:
            raise ApiError("interview_not_completed", "Interview must be completed first.", 409)

        # Deterministic placeholder extraction from private reference (never exposing transcript).
        derived: list[DerivedConstraint] = [
            DerivedConstraint(
                constraint_id=self.ctx.id_gen.next("constraint"),
                household_id=session.household_id,
                member_id=session.member_id,
                category="task_preference",
                preference_or_requirement="prefers balanced weekly chore load",
                importance_weight=0.7,
                flexibility=0.5,
                privacy_classification=PrivacyClassification.SHAREABLE_DERIVED,
                source_session_reference=session.session_id,
            ),
            DerivedConstraint(
                constraint_id=self.ctx.id_gen.next("constraint"),
                household_id=session.household_id,
                member_id=session.member_id,
                category="private_context",
                preference_or_requirement="private_notes_retained_member_scope",
                importance_weight=0.6,
                flexibility=0.4,
                privacy_classification=PrivacyClassification.PRIVATE,
                source_session_reference=session.session_id,
            ),
        ]
        self.ctx.constraints.create_many(derived)
        session.extracted_constraint_references.extend([c.constraint_id for c in derived])
        self.ctx.interviews.update(session)
        return derived

    def list_member_constraints(
        self, member_id: str, requester_member_id: str
    ) -> list[DerivedConstraint]:
        if member_id != requester_member_id:
            raise RESOURCE_NOT_FOUND
        return self.ctx.constraints.list_by_member(member_id)

    def list_shareable_constraints(
        self, household_id: str, requester_member_id: str
    ) -> list[DerivedConstraint]:
        self._require_household_membership(household_id, requester_member_id)
        return [
            constraint
            for constraint in self.ctx.constraints.list_shareable_by_household(household_id)
            if constraint.privacy_classification == PrivacyClassification.SHAREABLE_DERIVED
        ]

    def generate_agreement_proposal(
        self, household_id: str, requester_member_id: str, derived_constraint_ids: list[str]
    ) -> AgreementVersion:
        self._require_household_membership(household_id, requester_member_id)
        household = self._require_household(household_id)
        constraints = [
            c
            for c in self.ctx.constraints.list_by_ids(derived_constraint_ids)
            if c.privacy_classification == PrivacyClassification.SHAREABLE_DERIVED
        ]

        if not constraints:
            raise ApiError("missing_constraints", "No shareable derived constraints provided.", 400)

        solver_input = SolverInput(
            household_id=household_id,
            member_ids=[m.member_id for m in household.members],
            constraints=constraints,
            task_efforts=[
                TaskEffort(task="dishes", estimated_effort=30.0),
                TaskEffort(task="trash", estimated_effort=20.0),
                TaskEffort(task="bathroom", estimated_effort=40.0),
            ],
            availability={m.member_id: "weekly" for m in household.members},
            flexibility={m.member_id: 0.5 for m in household.members},
            weights={m.member_id: 1.0 for m in household.members},
            existing_assignments=self.ctx.assignments.list_by_household(household_id),
            horizon_days=14,
        )
        proposal = self.ctx.fairness_solver.generate_plan(solver_input)

        agreement = AgreementVersion(
            agreement_id=self.ctx.id_gen.next("agreement"),
            household_id=household_id,
            version=1,
            status=AgreementStatus.DRAFT,
            proposal=[],
            fairness_score=proposal.fairness_score,
            rationale=proposal.rationale,
        )
        agreement.transition(AgreementStatus.PROPOSED)

        assignments: list[Assignment] = []
        for proposed in proposal.proposed_assignments:
            assignments.append(
                Assignment(
                    assignment_id=self.ctx.id_gen.next("assignment"),
                    member_id=proposed.member_id,
                    task=proposed.task,
                    frequency=proposed.frequency,
                    estimated_effort=proposed.estimated_effort,
                    assigned_date=proposed.assigned_date,
                    status=AssignmentStatus.SCHEDULED,
                )
            )
        agreement.proposal = assignments

        self.ctx.agreements.create(agreement)
        self.ctx.assignments.create_many(assignments)
        self.ctx.assignments.link_to_household(household_id, [a.assignment_id for a in assignments])
        self.ctx.assignments.link_to_agreement(
            agreement.agreement_id, agreement.version, [a.assignment_id for a in assignments]
        )
        return agreement

    def get_agreement(self, agreement_id: str, version: int) -> AgreementVersion:
        agreement = self.ctx.agreements.get(agreement_id, version)
        if not agreement:
            raise RESOURCE_NOT_FOUND
        return agreement

    def get_agreement_history(self, agreement_id: str) -> list[AgreementVersion]:
        versions = self.ctx.agreements.list_versions(agreement_id)
        if not versions:
            raise RESOURCE_NOT_FOUND
        return versions

    def approve_agreement(
        self, agreement_id: str, version: int, requester_member_id: str
    ) -> AgreementVersion:
        agreement = self.get_agreement(agreement_id, version)
        self._require_household_membership(agreement.household_id, requester_member_id)
        agreement.register_approval(requester_member_id)
        household = self._require_household(agreement.household_id)
        if set(agreement.approvals) >= {m.member_id for m in household.members}:
            if agreement.status == AgreementStatus.PROPOSED:
                agreement.transition(AgreementStatus.APPROVED)
        return self.ctx.agreements.update(agreement)

    def veto_agreement(self, agreement_id: str, version: int, requester_member_id: str) -> AgreementVersion:
        agreement = self.get_agreement(agreement_id, version)
        self._require_household_membership(agreement.household_id, requester_member_id)
        agreement.register_veto(requester_member_id)
        if agreement.status == AgreementStatus.PROPOSED:
            agreement.transition(AgreementStatus.VETOED)
        return self.ctx.agreements.update(agreement)

    def counteroffer_agreement(
        self, agreement_id: str, version: int, requester_member_id: str, message: str
    ) -> AgreementVersion:
        agreement = self.get_agreement(agreement_id, version)
        self._require_household_membership(agreement.household_id, requester_member_id)
        agreement.register_counteroffer(
            Counteroffer(member_id=requester_member_id, message=message, submitted_at=utcnow())
        )
        if agreement.status == AgreementStatus.PROPOSED:
            agreement.transition(AgreementStatus.CHANGES_REQUESTED)
        return self.ctx.agreements.update(agreement)

    def activate_agreement(self, agreement_id: str, version: int, requester_member_id: str) -> AgreementVersion:
        agreement = self.get_agreement(agreement_id, version)
        self._require_household_membership(agreement.household_id, requester_member_id)
        if agreement.status not in (AgreementStatus.APPROVED, AgreementStatus.PROPOSED):
            raise ApiError("invalid_activation_state", "Agreement cannot be activated from current state.", 409)
        if agreement.status == AgreementStatus.PROPOSED:
            agreement.transition(AgreementStatus.APPROVED)
        agreement.transition(AgreementStatus.ACTIVE)
        return self.ctx.agreements.update(agreement)

    def create_assignment(
        self,
        household_id: str,
        requester_member_id: str,
        member_id: str,
        task: str,
        frequency: str,
        estimated_effort: float,
        assigned_date: datetime,
    ) -> Assignment:
        self._require_household_membership(household_id, requester_member_id)
        assignment = Assignment(
            assignment_id=self.ctx.id_gen.next("assignment"),
            member_id=member_id,
            task=task,
            frequency=frequency,
            estimated_effort=estimated_effort,
            assigned_date=assigned_date,
            status=AssignmentStatus.SCHEDULED,
        )
        self.ctx.assignments.create(assignment)
        self.ctx.assignments.link_to_household(household_id, [assignment.assignment_id])
        return assignment

    def list_assignments(self, household_id: str, requester_member_id: str) -> list[Assignment]:
        self._require_household_membership(household_id, requester_member_id)
        return self.ctx.assignments.list_by_household(household_id)

    def update_assignment_status(
        self, assignment_id: str, requester_member_id: str, status: AssignmentStatus
    ) -> Assignment:
        assignment = self.ctx.assignments.get(assignment_id)
        if not assignment:
            raise RESOURCE_NOT_FOUND
        # allow only assigned member to mark progress; hide otherwise
        if assignment.member_id != requester_member_id:
            raise RESOURCE_NOT_FOUND
        assignment.status = status
        return self.ctx.assignments.update(assignment)

    def record_monitoring_signal(
        self,
        household_id: str,
        requester_member_id: str,
        assignment_reference: str,
        member_reference: str,
        expected_contribution: float,
        observed_contribution: float,
        timestamp: datetime,
    ) -> MonitoringSignal:
        self._require_household_membership(household_id, requester_member_id)
        signal = MonitoringSignal(
            signal_id=self.ctx.id_gen.next("signal"),
            assignment_reference=assignment_reference,
            member_reference=member_reference,
            expected_contribution=expected_contribution,
            observed_contribution=observed_contribution,
            timestamp=timestamp,
        )
        self.ctx.monitoring.create(signal, household_id)
        return signal

    def list_monitoring_signals(
        self, household_id: str, requester_member_id: str
    ) -> list[MonitoringSignal]:
        self._require_household_membership(household_id, requester_member_id)
        return self.ctx.monitoring.list_by_household(household_id)

    def generate_drift_report(
        self, agreement_id: str, version: int, requester_member_id: str
    ) -> DriftReport:
        agreement = self.get_agreement(agreement_id, version)
        self._require_household_membership(agreement.household_id, requester_member_id)
        signals = self.ctx.monitoring.list_by_household(agreement.household_id)
        severity, affected_members, evidence, action = self.ctx.drift_service.evaluate(signals)
        affected_assignments = sorted({signal.assignment_reference for signal in signals if signal.expected_contribution > signal.observed_contribution})
        report = DriftReport(
            drift_id=self.ctx.id_gen.next("drift"),
            agreement_version_reference=f"{agreement_id}:v{version}",
            affected_members=affected_members,
            detected_signals=[signal.signal_id for signal in signals],
            severity=severity,
            explanation="Deterministic deviation analysis over expected vs observed contributions.",
            recommended_action=action,
            evidence=evidence,
            affected_assignments=affected_assignments,
            status=DriftStatus.OPEN,
        )
        self.ctx.drift_reports.create(report, agreement.household_id)
        return report

    def get_drift_report(self, drift_id: str, requester_member_id: str) -> DriftReport:
        report = self.ctx.drift_reports.get(drift_id)
        if not report:
            raise RESOURCE_NOT_FOUND
        agreement_id = report.agreement_version_reference.split(":")[0]
        versions = self.ctx.agreements.list_versions(agreement_id)
        if not versions:
            raise RESOURCE_NOT_FOUND
        household_id = versions[0].household_id
        self._require_household_membership(household_id, requester_member_id)
        return report

    def start_renegotiation(
        self, household_id: str, drift_id: str, requester_member_id: str
    ) -> tuple[RenegotiationCycle, list[PrivateInterviewSession]]:
        self._require_household_membership(household_id, requester_member_id)
        if not self.ctx.drift_reports.get(drift_id):
            raise RESOURCE_NOT_FOUND

        cycle = RenegotiationCycle(
            renegotiation_id=self.ctx.id_gen.next("renegotiation"),
            household_id=household_id,
            drift_id=drift_id,
            status=RenegotiationStatus.REQUESTED,
        )
        cycle.transition(RenegotiationStatus.INTERVIEWING)
        self.ctx.renegotiations.create(cycle)

        sessions: list[PrivateInterviewSession] = []
        for member in self.ctx.members.list_by_household(household_id):
            sessions.append(self.start_interview(household_id=household_id, member_id=member.member_id))
        return cycle, sessions

    def demo_roommates_reset(self) -> dict:
        self.ctx.reset()

        household_data = self.sim_adapter.provider.synthetic_household("demo-household", "Accord Demo Home")
        household = self.create_household(
            name=household_data["name"], scenario_metadata=household_data["scenarioMetadata"]
        )

        members_data = self.sim_adapter.provider.synthetic_members(household.household_id, count=3)
        created_members: list[Member] = []
        for m in members_data:
            created_members.append(
                self.add_member(
                    household_id=household.household_id,
                    display_name=m["displayName"],
                    role=m["role"],
                    consent_status=ConsentStatus(m.get("consentStatus", "granted")),
                    privacy_status=PrivacyStatus(m.get("privacyStatus", "private_only")),
                )
            )

        interviews_data = self.sim_adapter.provider.simulated_interview_responses(
            household.household_id, [m.member_id for m in created_members]
        )
        for interview in interviews_data:
            session = PrivateInterviewSession(
                session_id=self.ctx.id_gen.next("session"),
                household_id=household.household_id,
                member_id=interview["memberId"],
                status=InterviewStatus.COMPLETED,
                transcript_reference=interview["transcriptReference"],
            )
            self.ctx.interviews.create(session)
            constraints = [
                DerivedConstraint(
                    constraint_id=self.ctx.id_gen.next("constraint"),
                    household_id=household.household_id,
                    member_id=interview["memberId"],
                    category=c["category"],
                    preference_or_requirement=c["preferenceOrRequirement"],
                    importance_weight=float(c["importanceWeight"]),
                    flexibility=float(c["flexibility"]),
                    privacy_classification=PrivacyClassification(c["privacyClassification"]),
                    source_session_reference=session.session_id,
                )
                for c in interview["derivedConstraints"]
            ]
            self.ctx.constraints.create_many(constraints)
            session.extracted_constraint_references = [c.constraint_id for c in constraints]
            self.ctx.interviews.update(session)

        shared_constraints = self.list_shareable_constraints(
            household.household_id, requester_member_id=created_members[0].member_id
        )
        agreement = self.generate_agreement_proposal(
            household.household_id,
            requester_member_id=created_members[0].member_id,
            derived_constraint_ids=[c.constraint_id for c in shared_constraints],
        )

        timeline = self.sim_adapter.provider.simulate_14_day_timeline(
            household.household_id,
            [m.member_id for m in created_members],
            start_at=utcnow(),
        )
        for signal in timeline["monitoringSignals"]:
            self.ctx.monitoring.create(
                MonitoringSignal(
                    signal_id=self.ctx.id_gen.next("signal"),
                    assignment_reference=signal["assignmentReference"],
                    member_reference=signal["memberReference"],
                    expected_contribution=float(signal["expectedContribution"]),
                    observed_contribution=float(signal["observedContribution"]),
                    timestamp=datetime.fromisoformat(signal["timestamp"]),
                ),
                household.household_id,
            )

        return {
            "mode": "DEVELOPMENT/DEMO ONLY",
            "household": household,
            "members": created_members,
            "agreement": agreement,
            "assignments": agreement.proposal,
            "monitoringSignals": self.ctx.monitoring.list_by_household(household.household_id),
            "simulatedIntegrations": timeline["simulatedIntegrations"],
        }
