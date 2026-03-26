from __future__ import annotations

from app.schemas.common import APIModel, DocumentResponse


class DocumentUploadAcceptedResponse(APIModel):
    """文档上传入队后的响应结构。
    Response returned after a document upload is queued.
    """

    task_id: str
    status: str
    document: DocumentResponse
    document_set_id: str | None = None


class DocumentBatchUploadItemResponse(APIModel):
    """批量上传中的单个文档入队结果。
    Result item for one document accepted during a batch upload.
    """

    task_id: str
    status: str
    document: DocumentResponse


class DocumentBatchUploadAcceptedResponse(APIModel):
    """批量文档上传入队后的响应结构。
    Response returned after a batch of documents is queued.
    """

    document_set_id: str
    items: list[DocumentBatchUploadItemResponse]
