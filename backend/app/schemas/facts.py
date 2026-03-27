from __future__ import annotations

from pydantic import Field

from app.schemas.common import APIModel, BlockResponse, DocumentResponse, FactResponse


class FactReviewRequest(APIModel):
    """事实人工复核请求体。    Request payload for manual fact review."""

    status: str = Field(min_length=1)
    reviewer: str | None = None
    note: str | None = None


class FactTraceResponse(APIModel):
    """事实证据链与下游使用追溯的响应结构。
    Response payload for fact evidence and downstream usage tracing.
    """

    fact: FactResponse
    document: DocumentResponse | None
    block: BlockResponse | None
    usages: list[dict[str, object]]
