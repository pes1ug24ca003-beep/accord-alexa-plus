from __future__ import annotations

from fastapi import APIRouter, Depends

from ...dependencies import get_service
from ...privacy import caller_member_id
from ...serializers import serialize_agreement
from ...services.use_cases import AccordService
from ..schemas import CounterRequest, GenerateAgreementRequest

router = APIRouter(prefix="/agreements", tags=["agreements"])


@router.post("/generate", status_code=201)
def generate_proposal(
    payload: GenerateAgreementRequest,
    requester_member_id: str = Depends(caller_member_id),
    service: AccordService = Depends(get_service),
) -> dict:
    agreement = service.generate_agreement_proposal(
        payload.householdId, requester_member_id, payload.derivedConstraintIds
    )
    return {"agreement": serialize_agreement(agreement)}


@router.get("/{agreement_id}/versions/{version}")
def get_proposal(agreement_id: str, version: int, service: AccordService = Depends(get_service)) -> dict:
    agreement = service.get_agreement(agreement_id, version)
    return {"agreement": serialize_agreement(agreement)}


@router.get("/{agreement_id}/history")
def get_agreement_history(agreement_id: str, service: AccordService = Depends(get_service)) -> dict:
    versions = service.get_agreement_history(agreement_id)
    return {"versions": [serialize_agreement(v) for v in versions]}


@router.post("/{agreement_id}/versions/{version}/approve")
def approve(
    agreement_id: str,
    version: int,
    requester_member_id: str = Depends(caller_member_id),
    service: AccordService = Depends(get_service),
) -> dict:
    agreement = service.approve_agreement(agreement_id, version, requester_member_id)
    return {"agreement": serialize_agreement(agreement)}


@router.post("/{agreement_id}/versions/{version}/veto")
def veto(
    agreement_id: str,
    version: int,
    requester_member_id: str = Depends(caller_member_id),
    service: AccordService = Depends(get_service),
) -> dict:
    agreement = service.veto_agreement(agreement_id, version, requester_member_id)
    return {"agreement": serialize_agreement(agreement)}


@router.post("/{agreement_id}/versions/{version}/counter")
def counter(
    agreement_id: str,
    version: int,
    payload: CounterRequest,
    requester_member_id: str = Depends(caller_member_id),
    service: AccordService = Depends(get_service),
) -> dict:
    agreement = service.counteroffer_agreement(
        agreement_id, version, requester_member_id, payload.proposalDeltaSummary
    )
    return {"agreement": serialize_agreement(agreement)}


@router.post("/{agreement_id}/versions/{version}/activate")
def activate(
    agreement_id: str,
    version: int,
    requester_member_id: str = Depends(caller_member_id),
    service: AccordService = Depends(get_service),
) -> dict:
    agreement = service.activate_agreement(agreement_id, version, requester_member_id)
    return {"agreement": serialize_agreement(agreement)}
