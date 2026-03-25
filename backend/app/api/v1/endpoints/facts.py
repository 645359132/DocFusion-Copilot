from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.core.container import get_container
from app.schemas.facts import FactTraceResponse

router = APIRouter()


@router.get("/{fact_id}/trace", response_model=FactTraceResponse)
def get_fact_trace(fact_id: str) -> FactTraceResponse:
    """返回指定事实的证据链与模板使用追溯信息。
    Return evidence and template-usage trace data for a fact.
    """
    trace = get_container().trace_service.get_fact_trace(fact_id)
    if trace is None:
        raise HTTPException(status_code=404, detail="Fact not found.")
    return FactTraceResponse.model_validate(trace)
