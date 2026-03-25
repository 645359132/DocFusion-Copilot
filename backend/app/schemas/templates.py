from __future__ import annotations

from app.schemas.common import APIModel, TemplateResultResponse


class TemplateFillAcceptedResponse(APIModel):
    """模板回填任务入队后的响应结构。
    Response returned after a template fill task is queued.
    """

    task_id: str
    status: str
    template_name: str


class TemplateFillResultResponse(APIModel):
    """用于返回已完成模板结果元数据的包装结构。
    Wrapper schema for returning completed template result metadata.
    """

    result: TemplateResultResponse
