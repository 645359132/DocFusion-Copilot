from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from app.core.config import Settings
from app.models.domain import DocumentRecord, DocumentStatus, TaskRecord, TaskStatus, TaskType
from app.parsers.factory import ParserRegistry
from app.repositories.memory import InMemoryRepository
from app.services.fact_extraction import FactExtractionService
from app.tasks.executor import TaskExecutor
from app.utils.files import safe_filename
from app.utils.ids import new_id


class DocumentService:
    """处理文档上传、解析任务和事实抽取编排。
    Handle document uploads, parsing tasks and fact extraction orchestration.
    """

    def __init__(
        self,
        repository: InMemoryRepository,
        parser_registry: ParserRegistry,
        extraction_service: FactExtractionService,
        executor: TaskExecutor,
        settings: Settings,
    ) -> None:
        """初始化文档处理流程所需依赖。
        Initialize dependencies required for document-processing workflows.
        """
        self._repository = repository
        self._parser_registry = parser_registry
        self._extraction_service = extraction_service
        self._executor = executor
        self._settings = settings

    def upload_document(self, file_name: str, content: bytes) -> tuple[DocumentRecord, TaskRecord]:
        """保存上传文件并加入异步解析流程。
        Persist an uploaded file and enqueue asynchronous parsing work.
        """
        suffix = Path(file_name).suffix.lower()
        if suffix not in self._settings.supported_document_extensions:
            raise ValueError(f"Unsupported document type: {suffix}")

        doc_id = new_id("doc")
        stored_name = f"{doc_id}_{safe_filename(file_name)}"
        stored_path = self._settings.uploads_dir / stored_name
        stored_path.write_bytes(content)

        document = DocumentRecord(
            doc_id=doc_id,
            file_name=file_name,
            stored_path=str(stored_path),
            doc_type=suffix.lstrip("."),
            upload_time=datetime.now(timezone.utc),
            status=DocumentStatus.uploaded,
        )
        task = TaskRecord(
            task_id=new_id("task"),
            task_type=TaskType.parse_document,
            status=TaskStatus.queued,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            message="Document received and queued for parsing.",
            result={"document_id": doc_id},
        )

        self._repository.add_document(document)
        self._repository.upsert_task(task)
        self._executor.submit(task.task_id, self._process_document, document.doc_id, stored_path, task.task_id)
        return document, task

    def list_documents(self) -> list[DocumentRecord]:
        """返回仓储中当前全部文档。
        Return all documents currently stored in the repository.
        """
        return self._repository.list_documents()

    def _process_document(self, doc_id: str, file_path: Path, task_id: str) -> None:
        """解析单个上传文档、抽取事实并更新任务状态。
        Parse one uploaded document, extract facts and update task state.
        """
        self._repository.update_document(doc_id, status=DocumentStatus.parsing)
        self._repository.update_task(
            task_id,
            status=TaskStatus.running,
            progress=0.1,
            message="Parsing document structure.",
        )
        try:
            blocks = self._parser_registry.parse(file_path, doc_id)
            self._repository.replace_blocks(doc_id, blocks)
            self._repository.update_task(
                task_id,
                progress=0.55,
                message=f"Parsed {len(blocks)} blocks, extracting facts.",
                result_updates={"block_count": len(blocks)},
            )

            document = self._repository.get_document(doc_id)
            if document is None:
                raise RuntimeError(f"Document {doc_id} disappeared during parsing.")

            facts = self._extraction_service.extract(document, blocks)
            stored_facts = self._repository.add_facts(facts)
            self._repository.update_document(
                doc_id,
                status=DocumentStatus.parsed,
                metadata_updates={
                    "block_count": len(blocks),
                    "fact_count": len(stored_facts),
                },
            )
            self._repository.update_task(
                task_id,
                status=TaskStatus.succeeded,
                progress=1.0,
                message="Document parsed successfully.",
                result_updates={
                    "fact_count": len(stored_facts),
                },
            )
        except Exception as exc:
            self._repository.update_document(doc_id, status=DocumentStatus.failed)
            self._repository.update_task(
                task_id,
                status=TaskStatus.failed,
                progress=1.0,
                message="Document parsing failed.",
                error=str(exc),
            )
