from __future__ import annotations

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app.core.container import get_container
from app.schemas.benchmarks import (
    BenchmarkReportResponse,
    FactEvaluationAcceptedResponse,
    TemplateBenchmarkAcceptedResponse,
)

router = APIRouter()


@router.post("/facts/evaluate", response_model=FactEvaluationAcceptedResponse)
async def evaluate_facts(
    annotation_file: UploadFile = File(...),
    document_ids: str | None = Form(default=None),
    canonical_only: bool = Form(default=True),
    min_confidence: float | None = Form(default=None),
) -> FactEvaluationAcceptedResponse:
    """上传标注事实并提交抽取评测任务。    Upload labeled facts and queue an extraction-evaluation task."""

    if not annotation_file.filename:
        raise HTTPException(status_code=400, detail="Missing annotation file name.")
    content = await annotation_file.read()
    parsed_document_ids = [item.strip() for item in (document_ids or "").split(",") if item.strip()]
    try:
        task = get_container().benchmark_service.submit_fact_evaluation(
            annotation_name=annotation_file.filename,
            content=content,
            document_ids=parsed_document_ids or None,
            canonical_only=canonical_only,
            min_confidence=min_confidence,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return FactEvaluationAcceptedResponse(
        task_id=task.task_id,
        status=task.status,
        annotation_name=annotation_file.filename,
    )


@router.post("/templates/fill", response_model=TemplateBenchmarkAcceptedResponse)
async def benchmark_template_fill(
    template_file: UploadFile = File(...),
    expected_result_file: UploadFile = File(...),
    document_set_id: str | None = Form(default="default"),
    fill_mode: str = Form(default="canonical"),
    document_ids: str | None = Form(default=None),
) -> TemplateBenchmarkAcceptedResponse:
    """上传模板与期望结果并提交模板回填基准测试。    Upload a template and expected result to queue a fill benchmark."""

    if not template_file.filename or not expected_result_file.filename:
        raise HTTPException(status_code=400, detail="Missing benchmark file name.")

    template_content = await template_file.read()
    expected_result_content = await expected_result_file.read()
    parsed_document_ids = [item.strip() for item in (document_ids or "").split(",") if item.strip()]
    try:
        task = get_container().benchmark_service.submit_template_benchmark(
            template_name=template_file.filename,
            template_content=template_content,
            expected_result_name=expected_result_file.filename,
            expected_result_content=expected_result_content,
            fill_mode=fill_mode,
            document_set_id=document_set_id,
            document_ids=parsed_document_ids or None,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return TemplateBenchmarkAcceptedResponse(
        task_id=task.task_id,
        status=task.status,
        template_name=template_file.filename,
        expected_result_name=expected_result_file.filename,
    )


@router.get("/reports/{task_id}", response_model=BenchmarkReportResponse)
def get_benchmark_report(task_id: str) -> BenchmarkReportResponse:
    """读取指定评测任务的报告。    Read the report of a completed benchmark or evaluation task."""

    task = get_container().repository.get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found.")
    report = get_container().benchmark_service.get_report(task_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Benchmark report not found.")
    return BenchmarkReportResponse(
        task_id=task_id,
        task_type=task.task_type,
        report=report,
    )
