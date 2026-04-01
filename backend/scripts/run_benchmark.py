#!/usr/bin/env python
"""批量运行测试集评测并输出汇总报告。
Batch-run benchmarks against the test set and output aggregated reports.

Usage:
    python scripts/run_benchmark.py                          # use default test set path
    python scripts/run_benchmark.py --test-dir ../测试集      # custom test set path
    python scripts/run_benchmark.py --api http://localhost:8000/api/v1  # against a running server
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import Settings
from app.core.openai_client import OpenAICompatibleClient
from app.models.domain import DocumentRecord, DocumentStatus
from app.parsers.factory import ParserRegistry
from app.repositories.memory import InMemoryRepository
from app.services.benchmark_service import BenchmarkService
from app.services.document_service import DocumentService
from app.services.fact_extraction import FactExtractionService
from app.services.template_service import TemplateService
from app.tasks.executor import TaskExecutor
from app.utils.evaluation import generate_benchmark_markdown


def _find_test_set_dir(override: str | None) -> Path:
    """定位测试集目录。    Locate the test-set directory."""
    if override:
        p = Path(override)
        if p.is_dir():
            return p
        raise FileNotFoundError(f"Specified test-set directory not found: {override}")
    repo_root = Path(__file__).resolve().parents[2]
    candidate = repo_root / "测试集"
    if candidate.is_dir():
        return candidate
    raise FileNotFoundError("Cannot find 测试集 directory. Use --test-dir to specify.")


def _discover_template_scenarios(test_dir: Path) -> list[dict[str, object]]:
    """发现包含模板的测试场景。    Discover test scenarios that include templates."""
    scenarios: list[dict[str, object]] = []
    template_root = test_dir / "包含模板文件"
    if not template_root.is_dir():
        return scenarios
    for folder in sorted(template_root.iterdir()):
        if not folder.is_dir():
            continue
        template_file = None
        source_files: list[Path] = []
        user_req_file = None
        for f in folder.iterdir():
            if f.name == "用户要求.txt":
                user_req_file = f
            elif f.stem.endswith("模板") or f.stem.endswith("-模板") or "模板" in f.stem:
                template_file = f
            elif f.is_file():
                source_files.append(f)
        if template_file and source_files:
            scenarios.append({
                "name": folder.name,
                "template": template_file,
                "sources": source_files,
                "user_req": user_req_file,
            })
    return scenarios


def _discover_standalone_documents(test_dir: Path) -> list[Path]:
    """发现独立文档（非模板场景中的源文档）。    Discover standalone documents in md/, txt/, word/, Excel/ subfolders."""
    docs: list[Path] = []
    for sub in ("md", "txt", "word", "Excel"):
        sub_dir = test_dir / sub
        if not sub_dir.is_dir():
            continue
        for f in sorted(sub_dir.iterdir()):
            if f.is_file() and f.suffix.lower() in {".md", ".txt", ".docx", ".xlsx", ".pdf"}:
                docs.append(f)
    return docs


def run_offline_benchmark(test_dir: Path, output_dir: Path) -> dict[str, object]:
    """离线模式：直接调用后端服务运行评测。    Offline mode: run benchmarks by directly invoking backend services."""

    workspace_root = output_dir / "workspace"
    workspace_root.mkdir(parents=True, exist_ok=True)
    settings = Settings(workspace_root=workspace_root)
    settings.ensure_directories()
    repository = InMemoryRepository()
    executor = TaskExecutor(max_workers=2)
    parser_registry = ParserRegistry()
    extraction_service = FactExtractionService()
    openai_client = OpenAICompatibleClient(api_key="", base_url="", model="gpt-4o-mini")

    document_service = DocumentService(
        repository=repository,
        parser_registry=parser_registry,
        extraction_service=extraction_service,
        executor=executor,
        settings=settings,
    )
    template_service = TemplateService(
        repository=repository,
        executor=executor,
        settings=settings,
        openai_client=openai_client,
    )
    benchmark_service = BenchmarkService(
        repository=repository,
        executor=executor,
        settings=settings,
        template_service=template_service,
    )

    results: list[dict[str, object]] = []
    all_scenarios = _discover_template_scenarios(test_dir)
    standalone_docs = _discover_standalone_documents(test_dir)

    print(f"Found {len(all_scenarios)} template scenario(s) and {len(standalone_docs)} standalone document(s).")

    # 1) Upload standalone documents
    for doc_path in standalone_docs:
        print(f"  Uploading: {doc_path.name}")
        try:
            _, task = document_service.upload_document(
                doc_path.name,
                doc_path.read_bytes(),
                document_set_id="benchmark_standalone",
            )
            executor.wait(task.task_id, timeout=30)
        except Exception as exc:
            print(f"    ❌ Failed to upload {doc_path.name}: {exc}")

    print(f"  Total facts after standalone upload: {len(repository.list_facts(canonical_only=True))}")

    # 2) Process each template scenario
    for scenario in all_scenarios:
        name = scenario["name"]
        template_path: Path = scenario["template"]
        sources: list[Path] = scenario["sources"]
        print(f"\n=== Scenario: {name} ===")
        print(f"  Template: {template_path.name}")
        print(f"  Sources: {[s.name for s in sources]}")

        set_id = f"bench_{name[:20]}"

        # Upload source documents for this scenario
        doc_ids: list[str] = []
        for src in sources:
            print(f"  Uploading source: {src.name}")
            try:
                doc, task = document_service.upload_document(
                    src.name,
                    src.read_bytes(),
                    document_set_id=set_id,
                )
                executor.wait(task.task_id, timeout=30)
                doc_ids.append(doc.doc_id)
            except Exception as exc:
                print(f"    ❌ Failed: {exc}")

        facts = repository.list_facts(canonical_only=True, document_ids=set(doc_ids))
        print(f"  Extracted {len(facts)} facts from scenario documents")

        # Submit template fill
        started_at = time.perf_counter()
        try:
            task = template_service.submit_fill_task(
                template_name=template_path.name,
                content=template_path.read_bytes(),
                document_ids=doc_ids,
                fill_mode="canonical",
            )
            executor.wait(task.task_id, timeout=90)
            elapsed = round(time.perf_counter() - started_at, 2)
        except Exception as exc:
            print(f"  ❌ Template fill failed: {exc}")
            results.append({
                "scenario": name,
                "status": "failed",
                "error": str(exc),
            })
            continue

        task_record = repository.get_task(task.task_id)
        fill_result = template_service.get_result(task.task_id)

        scenario_result: dict[str, object] = {
            "scenario": name,
            "template": template_path.name,
            "status": str(task_record.status) if task_record else "unknown",
            "elapsed_seconds": elapsed,
            "facts_used": len(facts),
            "filled_cells": len(fill_result.filled_cells) if fill_result else 0,
        }
        if fill_result:
            scenario_result["output_path"] = fill_result.output_path
        results.append(scenario_result)
        print(f"  ✅ Filled {scenario_result['filled_cells']} cells in {elapsed}s")

    executor.shutdown()

    # 3) Build aggregate report
    report = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "test_dir": str(test_dir),
        "total_scenarios": len(all_scenarios),
        "total_standalone_docs": len(standalone_docs),
        "total_facts": len(repository.list_facts(canonical_only=True)),
        "scenarios": results,
    }
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Run DocFusion benchmark suite.")
    parser.add_argument("--test-dir", type=str, default=None, help="Path to 测试集 directory")
    parser.add_argument("--output-dir", type=str, default=None, help="Output directory for reports")
    args = parser.parse_args()

    test_dir = _find_test_set_dir(args.test_dir)
    output_dir = Path(args.output_dir) if args.output_dir else Path(__file__).resolve().parents[1] / "storage" / "benchmark_reports"
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Test set: {test_dir}")
    print(f"Output:   {output_dir}")
    print()

    report = run_offline_benchmark(test_dir, output_dir)

    # Save JSON report
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    json_path = output_dir / f"benchmark_{timestamp}.json"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print(f"\nJSON report: {json_path}")

    # Save Markdown summary
    md_lines = [
        f"# DocFusion Benchmark Report",
        f"",
        f"- **时间**: {report['timestamp']}",
        f"- **测试集**: {report['test_dir']}",
        f"- **场景数**: {report['total_scenarios']}",
        f"- **独立文档数**: {report['total_standalone_docs']}",
        f"- **总事实数**: {report['total_facts']}",
        f"",
        f"## 场景结果",
        f"",
        f"| 场景 | 状态 | 耗时(s) | 事实数 | 填充单元格 |",
        f"|------|------|---------|--------|------------|",
    ]
    for s in report["scenarios"]:
        md_lines.append(
            f"| {s.get('scenario', '')} | {s.get('status', '')} "
            f"| {s.get('elapsed_seconds', 'N/A')} | {s.get('facts_used', 'N/A')} "
            f"| {s.get('filled_cells', 'N/A')} |"
        )
    md_lines.append("")

    md_path = output_dir / f"benchmark_{timestamp}.md"
    md_path.write_text("\n".join(md_lines), encoding="utf-8")
    print(f"Markdown report: {md_path}")


if __name__ == "__main__":
    main()
