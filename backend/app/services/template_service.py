from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from app.core.config import Settings
from app.models.domain import (
    FilledCellRecord,
    TaskRecord,
    TaskStatus,
    TaskType,
    TemplateResultRecord,
)
from app.repositories.memory import InMemoryRepository
from app.tasks.executor import TaskExecutor
from app.utils.files import safe_filename
from app.utils.ids import new_id
from app.utils.normalizers import format_value, is_entity_column, normalize_entity_name, normalize_field_name
from app.utils.spreadsheet import CellWrite, SpreadsheetSheet, apply_xlsx_updates, build_cell_ref, load_xlsx


class TemplateService:
    """处理模板上传、工作簿分析和单元格级回填。
    Handle template upload, workbook analysis and cell-level filling.
    """

    def __init__(
        self,
        repository: InMemoryRepository,
        executor: TaskExecutor,
        settings: Settings,
    ) -> None:
        """初始化模板回填任务所需依赖。
        Initialize dependencies used by template filling tasks.
        """
        self._repository = repository
        self._executor = executor
        self._settings = settings

    def submit_fill_task(
        self,
        *,
        template_name: str,
        content: bytes,
        fill_mode: str = "canonical",
        document_set_id: str | None = None,
        document_ids: list[str] | None = None,
    ) -> TaskRecord:
        """保存模板上传内容并加入异步回填队列。
        Persist a template upload and enqueue asynchronous filling work.
        """
        suffix = Path(template_name).suffix.lower()
        if suffix not in self._settings.supported_template_extensions:
            raise ValueError(f"Unsupported template type: {suffix}")

        task = TaskRecord(
            task_id=new_id("task"),
            task_type=TaskType.fill_template,
            status=TaskStatus.queued,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            message="Template received and queued for filling.",
            result={"template_name": template_name},
        )

        stored_name = f"{task.task_id}_{safe_filename(template_name)}"
        template_path = self._settings.temp_dir / stored_name
        template_path.write_bytes(content)

        resolved_document_ids = self._resolve_document_ids(document_set_id, document_ids)
        self._repository.upsert_task(task)
        self._executor.submit(
            task.task_id,
            self._fill_template,
            task.task_id,
            template_name,
            template_path,
            fill_mode,
            resolved_document_ids,
        )
        return task

    def get_result(self, task_id: str) -> TemplateResultRecord | None:
        """返回回填任务对应的完成结果。
        Return the completed result associated with a fill task.
        """
        return self._repository.get_template_result(task_id)

    def _resolve_document_ids(
        self,
        document_set_id: str | None,
        document_ids: list[str] | None,
    ) -> list[str]:
        """将显式或隐式文档集解析为具体文档 id 列表。
        Resolve an explicit or implicit document set into concrete document ids.
        """
        if document_ids:
            return document_ids
        if document_set_id and document_set_id not in {"default", "all"}:
            split_ids = [item.strip() for item in document_set_id.split(",") if item.strip()]
            if split_ids:
                return split_ids
        return [document.doc_id for document in self._repository.list_documents() if document.status == "parsed"]

    def _fill_template(
        self,
        task_id: str,
        template_name: str,
        template_path: Path,
        fill_mode: str,
        document_ids: list[str],
    ) -> None:
        """执行单个排队模板任务的工作簿回填流程。
        Execute the workbook filling pipeline for one queued task.
        """
        self._repository.update_task(
            task_id,
            status=TaskStatus.running,
            progress=0.1,
            message="Analysing template structure.",
            result_updates={"document_ids": document_ids},
        )
        try:
            suffix = template_path.suffix.lower()
            if suffix == ".docx":
                raise NotImplementedError("Current MVP only supports xlsx template filling.")
            if suffix != ".xlsx":
                raise ValueError(f"Unsupported template type: {suffix}")

            workbook = load_xlsx(template_path)
            facts = self._repository.list_facts(canonical_only=(fill_mode == "canonical"), document_ids=set(document_ids))
            fact_lookup = {}
            for fact in sorted(facts, key=lambda item: item.confidence, reverse=True):
                fact_lookup.setdefault((fact.entity_name, fact.field_name), fact)
            unique_entities = list(dict.fromkeys(fact.entity_name for fact in facts if fact.entity_name))

            updates: list[CellWrite] = []
            filled_cells: list[FilledCellRecord] = []
            for sheet in workbook.sheets:
                header_row, entity_column, field_columns = self._detect_layout(sheet)
                if header_row is None or entity_column is None or not field_columns:
                    continue
                sheet_updates, sheet_filled_cells = self._build_sheet_updates(
                    sheet=sheet,
                    header_row=header_row,
                    entity_column=entity_column,
                    field_columns=field_columns,
                    fact_lookup=fact_lookup,
                    unique_entities=unique_entities,
                )
                updates.extend(sheet_updates)
                filled_cells.extend(sheet_filled_cells)

            output_file_name = f"{task_id}_{safe_filename(template_name)}"
            output_path = self._settings.outputs_dir / output_file_name
            apply_xlsx_updates(template_path, output_path, updates)

            result = TemplateResultRecord(
                task_id=task_id,
                template_name=template_name,
                output_path=str(output_path),
                output_file_name=output_file_name,
                created_at=datetime.now(timezone.utc),
                fill_mode=fill_mode,
                document_ids=document_ids,
                filled_cells=filled_cells,
            )
            self._repository.save_template_result(result)
            self._repository.update_task(
                task_id,
                status=TaskStatus.succeeded,
                progress=1.0,
                message="Template filled successfully.",
                result_updates={
                    "output_file_name": output_file_name,
                    "filled_cells": len(filled_cells),
                },
            )
        except Exception as exc:
            self._repository.update_task(
                task_id,
                status=TaskStatus.failed,
                progress=1.0,
                message="Template filling failed.",
                error=str(exc),
            )

    def _detect_layout(
        self,
        sheet: SpreadsheetSheet,
    ) -> tuple[int | None, int | None, list[tuple[int, str]]]:
        """推断工作表的表头行、实体列和目标字段列。
        Infer the header row, entity column and target field columns of a sheet.
        """
        best_row_index: int | None = None
        best_score = -1
        best_fields: list[tuple[int, str]] = []
        best_entity_column: int | None = None

        for row in sheet.rows[:10]:
            score = 0
            entity_column: int | None = None
            field_columns: list[tuple[int, str]] = []
            for column_index, raw_value in enumerate(row.values, start=1):
                if is_entity_column(raw_value):
                    entity_column = column_index
                    score += 3
                field_name = normalize_field_name(raw_value)
                if field_name:
                    field_columns.append((column_index, field_name))
                    score += 2
            if score > best_score and field_columns:
                best_row_index = row.row_index
                best_score = score
                best_fields = field_columns
                best_entity_column = entity_column or 1

        return best_row_index, best_entity_column, best_fields

    def _build_sheet_updates(
        self,
        *,
        sheet: SpreadsheetSheet,
        header_row: int,
        entity_column: int,
        field_columns: list[tuple[int, str]],
        fact_lookup: dict[tuple[str, str], object],
        unique_entities: list[str],
    ) -> tuple[list[CellWrite], list[FilledCellRecord]]:
        """将事实结果转换为单个工作表的具体单元格写入操作。
        Convert facts into concrete cell writes for one worksheet.
        """
        rows_after_header = [row for row in sheet.rows if row.row_index > header_row]
        updates: list[CellWrite] = []
        filled_cells: list[FilledCellRecord] = []

        assigned_entities: list[str] = []
        entity_cursor = 0
        next_row_index = max([header_row, *(row.row_index for row in rows_after_header)], default=header_row) + 1

        def write_row(row_index: int, entity_name: str, write_entity_cell: bool) -> None:
            """为目标工作表中的一个实体行追加单元格写入操作。
            Append cell writes for one entity row in the target worksheet.
            """
            if write_entity_cell:
                updates.append(
                    CellWrite(
                        sheet_name=sheet.name,
                        cell_ref=build_cell_ref(row_index, entity_column),
                        value=entity_name,
                    )
                )
            for column_index, field_name in field_columns:
                fact = fact_lookup.get((entity_name, field_name))
                if fact is None:
                    continue
                value = fact.value_num if fact.value_num is not None else fact.value_text
                if isinstance(value, float) and not value.is_integer():
                    cell_value: str | float = float(format_value(value))
                elif isinstance(value, float):
                    cell_value = int(value)
                else:
                    cell_value = value
                cell_ref = build_cell_ref(row_index, column_index)
                updates.append(CellWrite(sheet_name=sheet.name, cell_ref=cell_ref, value=cell_value))
                filled_cells.append(
                    FilledCellRecord(
                        sheet_name=sheet.name,
                        cell_ref=cell_ref,
                        entity_name=entity_name,
                        field_name=field_name,
                        value=cell_value,
                        fact_id=fact.fact_id,
                        confidence=fact.confidence,
                    )
                )

        for row in rows_after_header:
            entity_value = row.values[entity_column - 1] if len(row.values) >= entity_column else ""
            normalized_entity = normalize_entity_name(entity_value) if entity_value else ""
            if not normalized_entity and entity_cursor < len(unique_entities):
                normalized_entity = unique_entities[entity_cursor]
                entity_cursor += 1
                write_row(row.row_index, normalized_entity, True)
            elif normalized_entity:
                write_row(row.row_index, normalized_entity, False)
            if normalized_entity:
                assigned_entities.append(normalized_entity)

        for entity_name in unique_entities:
            if entity_name in assigned_entities:
                continue
            write_row(next_row_index, entity_name, True)
            next_row_index += 1

        return updates, filled_cells
