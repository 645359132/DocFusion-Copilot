from __future__ import annotations

from app.repositories.memory import InMemoryRepository


class TraceService:
    """构建事实证据链及其模板使用追溯信息。
    Build evidence traces for extracted facts and their template usages.
    """

    def __init__(self, repository: InMemoryRepository) -> None:
        """绑定共享仓储依赖。
        Bind the service to the shared repository.
        """
        self._repository = repository

    def get_fact_trace(self, fact_id: str) -> dict[str, object] | None:
        """返回单个事实的来源与使用追溯数据。
        Return source and usage trace data for a single fact.
        """
        fact = self._repository.get_fact(fact_id)
        if fact is None:
            return None
        document = self._repository.get_document(fact.source_doc_id)
        block = self._repository.get_fact_block(fact_id)
        usages: list[dict[str, object]] = []
        for template_result in self._repository.list_template_results():
            for cell in template_result.filled_cells:
                if cell.fact_id != fact_id:
                    continue
                usages.append(
                    {
                        "task_id": template_result.task_id,
                        "output_file_name": template_result.output_file_name,
                        "sheet_name": cell.sheet_name,
                        "cell_ref": cell.cell_ref,
                    }
                )
        return {
            "fact": fact,
            "document": document,
            "block": block,
            "usages": usages,
        }
