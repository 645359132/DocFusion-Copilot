from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class APIModel(BaseModel):
    """带共享序列化配置的基础 Pydantic 模型。
    Base Pydantic model with shared serialization settings.
    """

    model_config = ConfigDict(from_attributes=True, use_enum_values=True)


class DocumentResponse(APIModel):
    """文档记录的序列化表示。
    Serialized representation of a document record.
    """

    doc_id: str
    file_name: str
    stored_path: str
    doc_type: str
    upload_time: datetime
    status: str
    metadata: dict[str, object]


class BlockResponse(APIModel):
    """已解析文档块的序列化表示。
    Serialized representation of a parsed document block.
    """

    block_id: str
    doc_id: str
    block_type: str
    text: str
    section_path: list[str]
    page_or_index: int | None
    metadata: dict[str, object]


class FactResponse(APIModel):
    """抽取事实的序列化表示。
    Serialized representation of an extracted fact.
    """

    fact_id: str
    entity_type: str
    entity_name: str
    field_name: str
    value_num: float | None
    value_text: str
    unit: str | None
    year: int | None
    source_doc_id: str
    source_block_id: str
    source_span: str
    confidence: float
    conflict_group_id: str | None
    is_canonical: bool
    status: str
    metadata: dict[str, object]


class TaskResponse(APIModel):
    """异步任务的序列化表示。
    Serialized representation of an asynchronous task.
    """

    task_id: str
    task_type: str
    status: str
    created_at: datetime
    updated_at: datetime
    progress: float
    message: str
    error: str | None
    result: dict[str, object]


class FilledCellResponse(APIModel):
    """单个模板单元格回填动作的序列化表示。
    Serialized representation of one template cell fill action.
    """

    sheet_name: str
    cell_ref: str
    entity_name: str
    field_name: str
    value: str | float | int
    fact_id: str
    confidence: float


class TemplateResultResponse(APIModel):
    """已回填模板结果的序列化表示。
    Serialized representation of a filled template result.
    """

    task_id: str
    template_name: str
    output_path: str
    output_file_name: str
    created_at: datetime
    fill_mode: str
    document_ids: list[str]
    filled_cells: list[FilledCellResponse]
