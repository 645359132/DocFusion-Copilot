from __future__ import annotations

from app.schemas.common import APIModel, BlockResponse, DocumentResponse, FactResponse


class FactTraceResponse(APIModel):
    """事实证据链与下游使用追溯的响应结构。
    Response payload for fact evidence and downstream usage tracing.
    """

    fact: FactResponse
    document: DocumentResponse | None
    block: BlockResponse | None
    usages: list[dict[str, object]]
