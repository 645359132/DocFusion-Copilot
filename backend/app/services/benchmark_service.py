from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter

from app.core.config import Settings
from app.models.domain import TaskRecord, TaskStatus, TaskType
from app.repositories.base import Repository
from app.services.template_service import TemplateService
from app.tasks.executor import TaskExecutor
from app.utils.evaluation import compare_filled_templates, evaluate_extracted_facts
from app.utils.files import safe_filename
from app.utils.ids import new_id


class BenchmarkService:
    """提供抽取评测与模板基准测试能力。    Provide extraction evaluation and template benchmark capabilities."""

    def __init__(
        self,
        repository: Repository,
        executor: TaskExecutor,
        settings: Settings,
        template_service: TemplateService,
    ) -> None:
        """初始化高阶评测服务依赖。    Initialize dependencies required by the advanced evaluation service."""

        self._repository = repository
        self._executor = executor
        self._settings = settings
        self._template_service = template_service

    def submit_fact_evaluation(
        self,
        *,
        annotation_name: str,
        content: bytes,
        document_ids: list[str] | None = None,
        canonical_only: bool = True,
        min_confidence: float | None = None,
    ) -> TaskRecord:
        """提交事实抽取评测任务。    Submit a fact-extraction evaluation task."""

        task = TaskRecord(
            task_id=new_id("task"),
            task_type=TaskType.evaluate_facts,
            status=TaskStatus.queued,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            message="Fact evaluation task received.",
            result={"annotation_name": annotation_name},
        )
        annotation_path = self._settings.temp_dir / f"{task.task_id}_{safe_filename(annotation_name)}"
        annotation_path.write_bytes(content)
        resolved_document_ids = self._template_service.resolve_document_ids("default", document_ids)
        self._repository.upsert_task(task)
        self._executor.submit(
            task.task_id,
            self._evaluate_facts_task,
            task.task_id,
            annotation_path,
            resolved_document_ids,
            canonical_only,
            min_confidence,
        )
        return task

    def submit_template_benchmark(
        self,
        *,
        template_name: str,
        template_content: bytes,
        expected_result_name: str,
        expected_result_content: bytes,
        fill_mode: str = "canonical",
        document_set_id: str | None = None,
        document_ids: list[str] | None = None,
    ) -> TaskRecord:
        """提交模板回填基准测试任务。    Submit a template-fill benchmark task."""

        task = TaskRecord(
            task_id=new_id("task"),
            task_type=TaskType.benchmark_template_fill,
            status=TaskStatus.queued,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            message="Template benchmark task received.",
            result={
                "template_name": template_name,
                "expected_result_name": expected_result_name,
            },
        )
        template_path = self._settings.temp_dir / f"{task.task_id}_{safe_filename(template_name)}"
        expected_path = self._settings.temp_dir / f"{task.task_id}_expected_{safe_filename(expected_result_name)}"
        template_path.write_bytes(template_content)
        expected_path.write_bytes(expected_result_content)
        resolved_document_ids = self._template_service.resolve_document_ids(document_set_id, document_ids)
        self._repository.upsert_task(task)
        self._executor.submit(
            task.task_id,
            self._benchmark_template_fill_task,
            task.task_id,
            template_name,
            template_path,
            expected_path,
            fill_mode,
            resolved_document_ids,
        )
        return task

    def get_report(self, task_id: str) -> dict[str, object] | None:
        """返回指定评测任务的 JSON 报告内容。    Return the JSON report payload for an evaluation task."""

        task = self._repository.get_task(task_id)
        if task is None:
            return None
        report_path = task.result.get("report_path")
        if not isinstance(report_path, str):
            return None
        path = Path(report_path)
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def _evaluate_facts_task(
        self,
        task_id: str,
        annotation_path: Path,
        document_ids: list[str],
        canonical_only: bool,
        min_confidence: float | None,
    ) -> None:
        """执行事实抽取评测任务。    Execute a fact-extraction evaluation task."""

        self._repository.update_task(
            task_id,
            status=TaskStatus.running,
            progress=0.1,
            message="Loading labeled fact annotations.",
            result_updates={"document_ids": document_ids},
        )
        try:
            started_at = perf_counter()
            expected_items = self._load_expected_facts(annotation_path)
            predicted_facts = self._repository.list_facts(
                canonical_only=canonical_only,
                document_ids=set(document_ids),
                min_confidence=min_confidence,
            )
            report = evaluate_extracted_facts(predicted_facts, expected_items)
            report["task_id"] = task_id
            report["task_type"] = TaskType.evaluate_facts.value
            report["document_ids"] = document_ids
            report["elapsed_seconds"] = round(perf_counter() - started_at, 4)
            report_path = self._settings.outputs_dir / f"{task_id}_fact_evaluation_report.json"
            report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
            self._repository.update_task(
                task_id,
                status=TaskStatus.succeeded,
                progress=1.0,
                message="Fact evaluation completed successfully.",
                result_updates={
                    "matched_count": report["matched_count"],
                    "expected_count": report["expected_count"],
                    "accuracy": report["accuracy"],
                    "f1": report["f1"],
                    "report_path": str(report_path),
                },
            )
        except Exception as exc:
            self._repository.update_task(
                task_id,
                status=TaskStatus.failed,
                progress=1.0,
                message="Fact evaluation failed.",
                error=str(exc),
            )

    def _benchmark_template_fill_task(
        self,
        task_id: str,
        template_name: str,
        template_path: Path,
        expected_path: Path,
        fill_mode: str,
        document_ids: list[str],
    ) -> None:
        """执行模板回填基准测试任务。    Execute a template-fill benchmark task."""

        self._repository.update_task(
            task_id,
            status=TaskStatus.running,
            progress=0.1,
            message="Running template-fill benchmark.",
            result_updates={"document_ids": document_ids},
        )
        try:
            started_at = perf_counter()
            fill_result = self._template_service.fill_template_once(
                task_id=task_id,
                template_name=template_name,
                template_path=template_path,
                fill_mode=fill_mode,
                document_ids=document_ids,
                output_file_name=f"{task_id}_{safe_filename(template_name)}",
                persist_result=True,
            )
            elapsed_seconds = round(perf_counter() - started_at, 4)
            comparison = compare_filled_templates(
                template_path=template_path,
                generated_path=fill_result.output_path,
                expected_path=expected_path,
            )
            report = {
                "task_id": task_id,
                "task_type": TaskType.benchmark_template_fill.value,
                "template_name": template_name,
                "document_ids": document_ids,
                "elapsed_seconds": elapsed_seconds,
                "generated_output_file_name": fill_result.output_file_name,
                "generated_output_path": fill_result.output_path,
                **comparison,
            }
            report_path = self._settings.outputs_dir / f"{task_id}_template_benchmark_report.json"
            report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
            self._repository.update_task(
                task_id,
                status=TaskStatus.succeeded,
                progress=1.0,
                message="Template benchmark completed successfully.",
                result_updates={
                    "accuracy": report["accuracy"],
                    "elapsed_seconds": elapsed_seconds,
                    "total_compared_cells": report["total_compared_cells"],
                    "matched_cells": report["matched_cells"],
                    "report_path": str(report_path),
                    "output_file_name": fill_result.output_file_name,
                },
            )
        except Exception as exc:
            self._repository.update_task(
                task_id,
                status=TaskStatus.failed,
                progress=1.0,
                message="Template benchmark failed.",
                error=str(exc),
            )

    def _load_expected_facts(self, annotation_path: Path) -> list[dict[str, object]]:
        """读取并解析事实标注文件。    Read and parse a labeled fact-annotation file."""

        payload = json.loads(annotation_path.read_text(encoding="utf-8"))
        if isinstance(payload, list):
            return [self._coerce_expected_fact(item) for item in payload if isinstance(item, dict)]
        if isinstance(payload, dict):
            facts = payload.get("facts", [])
            if isinstance(facts, list):
                return [self._coerce_expected_fact(item) for item in facts if isinstance(item, dict)]
        raise ValueError("Annotation file must be a JSON list or an object containing a 'facts' list.")

    def _coerce_expected_fact(self, item: dict[str, object]) -> dict[str, object]:
        """校验并返回单条标注事实。    Validate and return one labeled fact item."""

        if not item.get("entity_name") or not item.get("field_name"):
            raise ValueError("Each labeled fact must contain 'entity_name' and 'field_name'.")
        return dict(item)
