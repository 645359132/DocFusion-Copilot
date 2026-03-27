from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from app.core.container import get_container
from app.schemas.common import FactResponse
from app.schemas.facts import FactReviewRequest, FactTraceResponse

router = APIRouter()


@router.get("", response_model=list[FactResponse])
def list_facts(
    entity_name: str | None = Query(default=None),
    field_name: str | None = Query(default=None),
    status: str | None = Query(default=None),
    min_confidence: float | None = Query(default=None, ge=0.0, le=1.0),
    canonical_only: bool = Query(default=False),
    document_ids: str | None = Query(default=None),
) -> list[FactResponse]:
    """按条件查询事实记录。
    Query fact records with optional filters.
    """
    parsed_document_ids = {item.strip() for item in (document_ids or "").split(",") if item.strip()} or None
    facts = get_container().repository.list_facts(
        entity_name=entity_name,
        field_name=field_name,
        status=status,
        min_confidence=min_confidence,
        canonical_only=canonical_only,
        document_ids=parsed_document_ids,
    )
    return [FactResponse.model_validate(fact) for fact in facts]


@router.patch("/{fact_id}/review", response_model=FactResponse)
def review_fact(fact_id: str, payload: FactReviewRequest) -> FactResponse:
    """提交事实复核结果并返回更新后的事实。    Submit a fact review decision and return the updated fact."""

    try:
        fact = get_container().fact_service.review_fact(
            fact_id,
            status=payload.status,
            reviewer=payload.reviewer,
            note=payload.note,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if fact is None:
        raise HTTPException(status_code=404, detail="Fact not found.")
    return FactResponse.model_validate(fact)


@router.get("/{fact_id}/trace", response_model=FactTraceResponse)
def get_fact_trace(fact_id: str) -> FactTraceResponse:
    """返回指定事实的证据链与模板使用追溯信息。
    Return evidence and template-usage trace data for a fact.
    """
    trace = get_container().trace_service.get_fact_trace(fact_id)
    if trace is None:
        raise HTTPException(status_code=404, detail="Fact not found.")
    return FactTraceResponse.model_validate(trace)
