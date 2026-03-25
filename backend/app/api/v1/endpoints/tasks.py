from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.core.container import get_container
from app.schemas.tasks import TaskResponse

router = APIRouter()


@router.get("/{task_id}", response_model=TaskResponse)
def get_task_status(task_id: str) -> TaskResponse:
    """获取异步任务的最新状态快照。
    Fetch the latest status snapshot for an asynchronous task.
    """
    task = get_container().repository.get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found.")
    return TaskResponse.model_validate(task)
