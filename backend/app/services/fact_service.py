from __future__ import annotations

from datetime import datetime, timezone

from app.models.domain import FactRecord
from app.repositories.base import Repository

REVIEWABLE_FACT_STATUSES = frozenset({"pending_review", "confirmed", "rejected"})


class FactService:
    """处理事实筛选与人工复核的服务。    Handle fact filtering and manual review workflows."""

    def __init__(self, repository: Repository) -> None:
        """绑定事实服务所需的仓储依赖。    Bind the repository dependency required by the fact service."""

        self._repository = repository

    def review_fact(
        self,
        fact_id: str,
        *,
        status: str,
        reviewer: str | None = None,
        note: str | None = None,
    ) -> FactRecord | None:
        """更新事实审核状态并记录复核元数据。    Update a fact review status and record review metadata."""

        normalized_status = status.strip()
        if normalized_status not in REVIEWABLE_FACT_STATUSES:
            raise ValueError(f"Unsupported fact review status: {status}")

        metadata_updates: dict[str, object] = {
            "reviewed_at": datetime.now(timezone.utc).isoformat(),
        }
        if reviewer:
            metadata_updates["reviewer"] = reviewer.strip()
        if note:
            metadata_updates["review_note"] = note.strip()

        return self._repository.update_fact(
            fact_id,
            status=normalized_status,
            metadata_updates=metadata_updates,
        )
