from __future__ import annotations

from fastapi import APIRouter

from app.core.container import get_container
from app.schemas.agent import AgentChatRequest, AgentChatResponse

router = APIRouter()


@router.post("/chat", response_model=AgentChatResponse)
def chat(payload: AgentChatRequest) -> AgentChatResponse:
    """将自然语言请求解析为轻量级代理计划。 感觉无用
    Parse a natural-language request into a lightweight agent plan.
    """
    response = get_container().agent_service.chat(payload.message, payload.context_id)
    return AgentChatResponse.model_validate(response)
