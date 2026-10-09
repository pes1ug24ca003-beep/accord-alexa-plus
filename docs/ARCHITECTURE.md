# Architecture Foundation (Specification-Level)

## System shape
- `apps/web`: frontend experience for interviews, agreement review, and monitoring.
- `apps/api`: backend service exposing interview, planning, agreement, and monitoring endpoints.
- `packages/sim`: simulation utilities for Alexa+ voice, notifications, calendar, and activity events.

## Frontend architecture (spec)
- Single web client with three main flows:
  1. Private interview capture
  2. Agreement review/edit/accept
  3. Monitoring and drift status
- State model separates:
  - private local draft state
  - shared agreement state
  - simulated signal timeline

## Backend architecture (spec)
- API modules:
  - Interview intake
  - Constraint extraction orchestration
  - Fairness solver orchestration
  - Agreement persistence/versioning
  - Drift detection (14-day window)
- Privacy guard sits between extraction outputs and any shared prompt/context construction.

## AI architecture (spec)
- AI used for:
  - extracting structured constraints from private interviews
  - generating safe, non-identifying explanation summaries
- AI not used for final allocation authority; deterministic solver owns final plan computation.
- Prompt construction policy enforces no cross-member raw transcript leakage.

## Database architecture (spec)
Logical entities:
- Member
- InterviewSession (private)
- DerivedConstraint (sanitized)
- ChoreDefinition
- AgreementVersion
- Assignment
- MonitoringSignal (simulated)
- DriftReport

Storage boundary:
- Raw private interview content stored and accessed only in member-scoped paths.
- Solver/monitoring read from sanitized derived tables/views.

## 14-day drift detection model (spec)
- Sliding 14-day window over assignment completion and sentiment/check-in indicators.
- Trigger conditions (example baseline):
  - repeated missed chores above threshold
  - burden delta imbalance above threshold
  - sustained negative check-in trend
- Output: DriftReport with reason codes and renegotiation recommendation.

## Staged implementation boundaries
- Stage 1: schema + simulation + deterministic solver core.
- Stage 2: end-to-end API + web workflow with local persistence.
- Stage 3: UI polish + richer monitoring visualizations.
- Stage 4: optional hardening and broader testing.
