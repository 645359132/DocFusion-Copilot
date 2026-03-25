from __future__ import annotations

from app.schemas.common import APIModel, DocumentResponse


class DocumentUploadAcceptedResponse(APIModel):
    """文档上传入队后的响应结构。
    Response returned after a document upload is queued.
    """

    task_id: str
    status: str
    document: DocumentResponse
