"""Deterministic synthetic data generation for Accord simulations."""

from __future__ import annotations

from datetime import datetime, timedelta
from random import Random

from .interfaces import SimulationProvider


class DefaultSimulationProvider(SimulationProvider):
    def __init__(self, seed: int = 7) -> None:
        self._rng = Random(seed)

    def synthetic_household(self, household_id: str, name: str) -> dict:
        return {
            "householdId": household_id,
            "name": name,
            "scenarioMetadata": {
                "mode": "simulated",
                "description": "Three roommates negotiating household chores",
            },
            "members": [],
        }

    def synthetic_members(self, household_id: str, count: int = 3) -> list[dict]:
        roles = ["roommate", "roommate", "roommate"]
        members = []
        for idx in range(count):
            members.append(
                {
                    "memberId": f"{household_id}-member-{idx + 1}",
                    "displayName": f"Roommate {idx + 1}",
                    "role": roles[min(idx, len(roles) - 1)],
                    "consentStatus": "granted",
                    "privacyStatus": "private_only",
                }
            )
        return members

    def simulated_interview_responses(self, household_id: str, member_ids: list[str]) -> list[dict]:
        categories = ["availability", "task_preference", "hard_constraint"]
        responses = []
        for idx, member_id in enumerate(member_ids):
            responses.append(
                {
                    "sessionId": f"{household_id}-session-{idx + 1}",
                    "householdId": household_id,
                    "memberId": member_id,
                    "status": "completed",
                    "transcriptReference": f"private://{household_id}/{member_id}/session-{idx + 1}",
                    "derivedConstraints": [
                        {
                            "constraintId": f"{member_id}-c1",
                            "memberId": member_id,
                            "category": categories[idx % len(categories)],
                            "preferenceOrRequirement": "prefers evening chores",
                            "importanceWeight": round(0.6 + 0.1 * idx, 2),
                            "flexibility": round(0.5 - 0.05 * idx, 2),
                            "privacyClassification": "shareable_derived",
                            "sourceSessionReference": f"{household_id}-session-{idx + 1}",
                        }
                    ],
                }
            )
        return responses

    def simulated_assignments(self, household_id: str, member_ids: list[str], start_at: datetime) -> list[dict]:
        tasks = ["dishes", "trash", "bathroom"]
        assignments = []
        for idx, member_id in enumerate(member_ids):
            assignments.append(
                {
                    "assignmentId": f"{household_id}-a-{idx + 1}",
                    "memberId": member_id,
                    "task": tasks[idx % len(tasks)],
                    "frequency": "weekly",
                    "estimatedEffort": float(30 + idx * 10),
                    "assignedDate": (start_at + timedelta(days=idx)).isoformat(),
                    "status": "scheduled",
                }
            )
        return assignments

    def simulated_monitoring_signals(self, assignments: list[dict], days: int = 14) -> list[dict]:
        if not assignments:
            return []

        base_time = datetime.fromisoformat(assignments[0]["assignedDate"])
        signals = []
        for day in range(days):
            assignment = assignments[day % len(assignments)]
            expected = assignment["estimatedEffort"]
            observed = max(0.0, expected - self._rng.uniform(0.0, expected * 0.25))
            signals.append(
                {
                    "signalId": f"signal-{day + 1}",
                    "assignmentReference": assignment["assignmentId"],
                    "memberReference": assignment["memberId"],
                    "expectedContribution": expected,
                    "observedContribution": round(observed, 2),
                    "timestamp": (base_time + timedelta(days=day)).isoformat(),
                }
            )
        return signals

    def simulate_14_day_timeline(self, household_id: str, member_ids: list[str], start_at: datetime) -> dict:
        assignments = self.simulated_assignments(household_id, member_ids, start_at)
        signals = self.simulated_monitoring_signals(assignments, days=14)
        return {
            "householdId": household_id,
            "durationDays": 14,
            "assignments": assignments,
            "monitoringSignals": signals,
            "simulatedIntegrations": {
                "voice": "simulated",
                "notifications": "simulated",
                "calendar": "simulated",
                "householdActivity": "simulated",
            },
        }
