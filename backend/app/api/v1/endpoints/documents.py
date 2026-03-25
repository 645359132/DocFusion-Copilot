from __future__ import annotations

from fastapi import APIRouter, File, HTTPException, UploadFile

from app.core.container import get_container
from app.schemas.common import DocumentResponse
from app.schemas.documents import DocumentUploadAcceptedResponse

router = APIRouter()


@router.post("/upload", response_model=DocumentUploadAcceptedResponse)
async def upload_document(file: UploadFile = File(...)) -> DocumentUploadAcceptedResponse:
    """接收源文档并加入异步解析队列。
    Accept a source document and queue an asynchronous parsing task.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="Missing uploaded file name.")
    content = await file.read()
    try:
        document, task = get_container().document_service.upload_document(file.filename, content)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return DocumentUploadAcceptedResponse(
        task_id=task.task_id,
        status=task.status,
        document=DocumentResponse.model_validate(document),
    )


@router.get("", response_model=list[DocumentResponse])
def list_documents() -> list[DocumentResponse]:
    """列出后端仓储当前已知的全部文档。
    List documents currently known to the backend repository.
    """
    documents = get_container().document_service.list_documents()
    return [DocumentResponse.model_validate(document) for document in documents]
