from __future__ import annotations

from pydantic import Field

from app.schemas.common import APIModel


class AgentChatRequest(APIModel):
    """轻量级代理规划接口的输入载荷。
    Input payload for the lightweight agent planning endpoint.
    """

    message: str = Field(min_length=1)
    context_id: str | None = None


class AgentChatResponse(APIModel):
    """代理接口返回的规则式规划结果。
    Rule-based planning result returned by the agent endpoint.
    """

    intent: str
    entities: list[str]
    fields: list[str]
    target: str
    need_db_store: bool
    context_id: str | None
    preview: list[dict[str, object]]
