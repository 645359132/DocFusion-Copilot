from __future__ import annotations

from app.schemas.common import APIModel


class FactEvaluationAcceptedResponse(APIModel):
    """事实抽取评测任务入队响应。    Response returned after a fact-evaluation task is queued."""

    task_id: str
    status: str
    annotation_name: str


class TemplateBenchmarkAcceptedResponse(APIModel):
    """模板基准测试任务入队响应。    Response returned after a template-benchmark task is queued."""

    task_id: str
    status: str
    template_name: str
    expected_result_name: str


class BenchmarkReportResponse(APIModel):
    """评测或基准测试报告响应。    Response payload for an evaluation or benchmark report."""

    task_id: str
    task_type: str
    report: dict[str, object]
