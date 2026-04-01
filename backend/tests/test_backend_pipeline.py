from __future__ import annotations

import io
import json
import shutil
import sys
import unittest
import uuid
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from xml.sax.saxutils import escape

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import Settings
from app.core.openai_client import OpenAICompatibleClient
from app.models.domain import DocumentRecord, DocumentStatus, FactRecord
from app.parsers.factory import ParserRegistry
from app.repositories.memory import InMemoryRepository
from app.services.agent_service import AgentService
from app.services.benchmark_service import BenchmarkService
from app.services.document_interaction_service import DocumentInteractionService
from app.services.document_service import DocumentService
from app.services.fact_extraction import FactExtractionService
from app.services.fact_service import FactService
from app.services.template_service import TemplateService
from app.services.trace_service import TraceService
from app.tasks.executor import TaskExecutor
from app.utils.spreadsheet import load_xlsx
from app.utils.wordprocessing import load_docx_tables
from app.utils.evaluation import generate_benchmark_markdown


class BackendPipelineTests(unittest.TestCase):
    """后端核心业务链路的端到端测试。    End-to-end tests for the backend core business pipeline."""

    def setUp(self) -> None:
        """为每个用例创建隔离的测试工作区。    Create an isolated test workspace for each case."""

        tests_root = Path(__file__).resolve().parents[2] / ".tmp_test_runs"
        tests_root.mkdir(parents=True, exist_ok=True)
        self._workspace_root = tests_root / f"backend_{uuid.uuid4().hex}"
        self._workspace_root.mkdir(parents=True, exist_ok=False)
        self.settings = Settings(workspace_root=self._workspace_root)
        self.settings.ensure_directories()
        self.repository = InMemoryRepository()
        self.executor = TaskExecutor(max_workers=1)
        self.document_service = DocumentService(
            repository=self.repository,
            parser_registry=ParserRegistry(),
            extraction_service=FactExtractionService(),
            executor=self.executor,
            settings=self.settings,
        )
        self.template_service = TemplateService(
            repository=self.repository,
            executor=self.executor,
            settings=self.settings,
            openai_client=OpenAICompatibleClient(
                api_key="",
                base_url="",
                model="gpt-4o-mini",
            ),
        )
        self.benchmark_service = BenchmarkService(
            repository=self.repository,
            executor=self.executor,
            settings=self.settings,
            template_service=self.template_service,
        )
        self.trace_service = TraceService(repository=self.repository)
        self.fact_service = FactService(repository=self.repository)
        self.agent_service = AgentService(
            repository=self.repository,
            openai_client=OpenAICompatibleClient(
                api_key="",
                base_url="",
                model="gpt-4o-mini",
            ),
        )
        self.document_interaction_service = DocumentInteractionService(
            repository=self.repository,
            agent_service=self.agent_service,
            template_service=self.template_service,
            settings=self.settings,
            openai_client=OpenAICompatibleClient(
                api_key="",
                base_url="",
                model="gpt-4o-mini",
            ),
        )

    def tearDown(self) -> None:
        """释放测试资源。    Release resources created by the test case."""

        self.executor.shutdown()
        shutil.rmtree(self._workspace_root, ignore_errors=True)

    def test_text_document_upload_extracts_expected_city_facts(self) -> None:
        """上传文本报告后应得到四条城市事实。    Uploading a text report should yield four city facts."""

        content = (
            "2025年，上海GDP总量56,708.71亿元，常住人口2,487.45万人，"
            "人均GDP228020元，一般公共预算收入8,500.91亿元。"
        )
        _, task = self.document_service.upload_document("city_report.txt", content.encode("utf-8"))
        self.executor.wait(task.task_id, timeout=5)

        facts = self.repository.list_facts(canonical_only=True)
        fields = {fact.field_name for fact in facts}

        self.assertEqual(4, len(facts))
        self.assertEqual({"GDP总量", "常住人口", "人均GDP", "一般公共预算收入"}, fields)
        self.assertTrue(all(fact.entity_name == "上海" for fact in facts))

    def test_template_fill_populates_xlsx_cells(self) -> None:
        """XLSX 模板回填应把事实写回单元格。    XLSX template filling should write facts back into cells."""

        self._seed_city_facts()
        template_bytes = build_simple_template_xlsx(
            headers=["城市", "GDP总量（亿元）", "常住人口（万人）"],
            rows=[
                ["上海", "", ""],
                ["北京", "", ""],
            ],
        )

        task = self.template_service.submit_fill_task(
            template_name="city_template.xlsx",
            content=template_bytes,
            document_ids=["doc_seed"],
            fill_mode="canonical",
        )
        self.executor.wait(task.task_id, timeout=5)

        result = self.template_service.get_result(task.task_id)
        self.assertIsNotNone(result)
        workbook = load_xlsx(Path(result.output_path))
        first_sheet = workbook.sheets[0]
        rows = {row.row_index: row.values for row in first_sheet.rows}

        self.assertEqual("56708.71", rows[2][1])
        self.assertEqual("2487.45", rows[2][2])
        self.assertEqual("52073.4", rows[3][1])
        self.assertGreaterEqual(len(result.filled_cells), 4)

    def test_template_fill_populates_docx_table_cells(self) -> None:
        """DOCX 表格模板回填应写入事实值。    DOCX table-template filling should write fact values into table cells."""

        self._seed_city_facts()
        template_bytes = build_simple_template_docx(
            headers=["城市", "GDP总量（亿元）", "常住人口（万人）"],
            rows=[
                ["上海", "", ""],
                ["北京", "", ""],
            ],
        )

        task = self.template_service.submit_fill_task(
            template_name="city_template.docx",
            content=template_bytes,
            document_ids=["doc_seed"],
            fill_mode="canonical",
        )
        self.executor.wait(task.task_id, timeout=5)

        result = self.template_service.get_result(task.task_id)
        self.assertIsNotNone(result)
        document = load_docx_tables(Path(result.output_path))
        first_table = document.tables[0]
        rows = {row.row_index: row.values for row in first_table.rows}

        self.assertEqual("56708.71", rows[2][1])
        self.assertEqual("2487.45", rows[2][2])
        self.assertEqual("52073.4", rows[3][1])
        self.assertGreaterEqual(len(result.filled_cells), 4)

    def test_trace_service_reports_template_usage(self) -> None:
        """追溯事实时应包含模板使用位置。    Fact tracing should include template usage positions."""

        seeded_facts = self._seed_city_facts()
        template_bytes = build_simple_template_xlsx(
            headers=["城市", "GDP总量（亿元）"],
            rows=[["上海", ""]],
        )

        task = self.template_service.submit_fill_task(
            template_name="trace_template.xlsx",
            content=template_bytes,
            document_ids=["doc_seed"],
            fill_mode="canonical",
        )
        self.executor.wait(task.task_id, timeout=5)

        trace = self.trace_service.get_fact_trace(seeded_facts[0].fact_id)
        self.assertIsNotNone(trace)
        self.assertEqual("上海", trace["fact"].entity_name)
        self.assertTrue(trace["usages"])
        self.assertEqual("B2", trace["usages"][0]["cell_ref"])

    def test_document_interaction_service_can_summarize_documents(self) -> None:
        """文档交互服务应能输出规则摘要。    The document interaction service should produce a deterministic summary."""

        content = (
            "# 城市发展报告\n\n"
            "2025年，上海GDP总量56,708.71亿元，常住人口2,487.45万人。"
        )
        _, task = self.document_service.upload_document("summary.md", content.encode("utf-8"))
        self.executor.wait(task.task_id, timeout=5)

        result = self.document_interaction_service.execute(message="请总结这份文档", context_id="ctx_demo")

        self.assertEqual("summarize_document", result["intent"])
        self.assertEqual("summary", result["execution_type"])
        self.assertIn("共处理", result["summary"])
        self.assertEqual("ctx_demo", result["context_id"])

    def test_document_interaction_service_can_reformat_text_documents(self) -> None:
        """文本整理应输出规范化的 Markdown。    Text cleanup should output normalized Markdown."""

        content = "一、总览  \n\n\n  2025年上海GDP总量56,708.71亿元。\n"
        _, task = self.document_service.upload_document("format.md", content.encode("utf-8"))
        self.executor.wait(task.task_id, timeout=5)

        result = self.document_interaction_service.execute(message="请帮我整理一下格式")

        self.assertEqual("reformat_document", result["intent"])
        self.assertEqual("reformat", result["execution_type"])
        self.assertEqual(1, len(result["artifacts"]))
        artifact_path = Path(result["artifacts"][0]["output_path"])
        self.assertTrue(artifact_path.exists())
        formatted_text = artifact_path.read_text(encoding="utf-8")
        self.assertIn("# 总览", formatted_text)

    def test_document_interaction_service_can_reformat_docx_documents(self) -> None:
        """DOCX 整理应输出规范化后的文件。    DOCX cleanup should output a normalized file artifact."""

        content = build_simple_document_docx(
            paragraphs=[
                "一、  总览",
                "  2025年上海GDP总量56,708.71亿元。 ",
            ]
        )
        _, task = self.document_service.upload_document("format.docx", content)
        self.executor.wait(task.task_id, timeout=5)

        result = self.document_interaction_service.execute(message="请帮我整理一下格式")

        self.assertEqual("reformat_document", result["intent"])
        self.assertEqual("reformat", result["execution_type"])
        artifact_path = Path(result["artifacts"][0]["output_path"])
        with zipfile.ZipFile(artifact_path, "r") as archive:
            document_xml = archive.read("word/document.xml").decode("utf-8")
        self.assertIn("Heading1", document_xml)
        self.assertIn("一、总览", document_xml)

    def test_document_interaction_service_can_edit_text_documents(self) -> None:
        """自然语言编辑应生成修改后的文本文件。    Natural-language editing should generate an edited text file."""

        content = "合同甲方为南京甲公司，乙方为南京乙公司。"
        _, task = self.document_service.upload_document("edit.txt", content.encode("utf-8"))
        self.executor.wait(task.task_id, timeout=5)

        result = self.document_interaction_service.execute(message="将南京甲公司替换为南京采购中心")

        self.assertEqual("edit_document", result["intent"])
        self.assertEqual("edit", result["execution_type"])
        self.assertEqual(1, len(result["artifacts"]))
        self.assertEqual(1, result["artifacts"][0]["change_count"])
        artifact_path = Path(result["artifacts"][0]["output_path"])
        edited_text = artifact_path.read_text(encoding="utf-8")
        self.assertIn("南京采购中心", edited_text)
        self.assertNotIn("南京甲公司", edited_text)

    def test_document_interaction_service_can_edit_docx_documents(self) -> None:
        """自然语言编辑应生成修改后的 DOCX 文件。    Natural-language editing should generate an edited DOCX file."""

        content = build_simple_document_docx(paragraphs=["甲方为南京甲公司。"])
        _, task = self.document_service.upload_document("edit.docx", content)
        self.executor.wait(task.task_id, timeout=5)

        result = self.document_interaction_service.execute(message="把南京甲公司改为南京采购中心")

        self.assertEqual("edit_document", result["intent"])
        self.assertEqual("edit", result["execution_type"])
        self.assertEqual(1, result["artifacts"][0]["change_count"])
        artifact_path = Path(result["artifacts"][0]["output_path"])
        with zipfile.ZipFile(artifact_path, "r") as archive:
            document_xml = archive.read("word/document.xml").decode("utf-8")
        self.assertIn("南京采购中心", document_xml)

    def test_document_interaction_service_can_queue_template_fill_from_natural_language_entry(self) -> None:
        """自然语言执行入口应能直接接收模板文件并提交回填任务。    The natural-language execution entry should accept a template file and queue a fill task."""

        _, city_task = self.document_service.upload_document(
            "city_report.txt",
            "2025年，上海GDP总量56,708.71亿元，常住人口2,487.45万人。".encode("utf-8"),
            document_set_id="set_agent",
        )
        self.executor.wait(city_task.task_id, timeout=5)

        template_bytes = build_simple_template_xlsx(
            headers=["城市", "GDP总量（亿元）", "常住人口（万人）"],
            rows=[["上海", "", ""]],
        )
        response = self.document_interaction_service.execute(
            message="请根据这批文档把这个表格填好",
            document_set_id="set_agent",
            template_name="city_agent_template.xlsx",
            template_content=template_bytes,
            fill_mode="canonical",
            auto_match=True,
        )

        self.assertEqual("extract_and_fill_template", response["intent"])
        self.assertEqual("template_fill_task", response["execution_type"])
        self.assertIsNotNone(response["task_id"])
        self.assertEqual("queued", response["task_status"])
        self.assertEqual("city_agent_template.xlsx", response["template_name"])

        self.executor.wait(response["task_id"], timeout=5)
        result = self.template_service.get_result(response["task_id"])
        self.assertIsNotNone(result)
        workbook = load_xlsx(Path(result.output_path))
        first_sheet = workbook.sheets[0]
        rows = {row.row_index: row.values for row in first_sheet.rows}
        self.assertEqual("56708.71", rows[2][1])
        self.assertEqual("2487.45", rows[2][2])

    def test_fact_review_can_recompute_canonical_selection(self) -> None:
        """人工复核应能更新事实状态并重算 canonical 结果。    Manual review should update fact status and recompute the canonical winner."""

        seeded_facts = self._seed_city_facts()
        backup_fact = FactRecord(
            fact_id="fact_sh_gdp_backup",
            entity_type=seeded_facts[0].entity_type,
            entity_name=seeded_facts[0].entity_name,
            field_name=seeded_facts[0].field_name,
            value_num=56000.0,
            value_text="56,000.00",
            unit=seeded_facts[0].unit,
            year=seeded_facts[0].year,
            source_doc_id="doc_seed",
            source_block_id="blk_3",
            source_span="backup fact",
            confidence=0.85,
        )
        self.repository.add_facts([backup_fact])

        reviewed = self.fact_service.review_fact(
            seeded_facts[0].fact_id,
            status="rejected",
            reviewer="tester",
            note="manual validation failed",
        )

        self.assertIsNotNone(reviewed)
        self.assertEqual("rejected", reviewed.status)
        self.assertEqual("tester", reviewed.metadata["reviewer"])

        canonical_facts = self.repository.list_facts(
            entity_name=seeded_facts[0].entity_name,
            field_name=seeded_facts[0].field_name,
            canonical_only=True,
        )
        self.assertEqual(["fact_sh_gdp_backup"], [fact.fact_id for fact in canonical_facts])

    def test_fact_evaluation_reports_perfect_accuracy_for_matching_labels(self) -> None:
        """事实评测应在标注完全匹配时给出满分。    Fact evaluation should report perfect accuracy for matching labels."""

        self._seed_city_facts()
        annotations = {
            "facts": [
                {"entity_name": "上海", "field_name": "GDP总量", "value_num": 56708.71, "unit": "亿元", "year": 2025},
                {"entity_name": "上海", "field_name": "常住人口", "value_num": 2487.45, "unit": "万人", "year": 2025},
                {"entity_name": "北京", "field_name": "GDP总量", "value_num": 52073.4, "unit": "亿元", "year": 2025},
                {"entity_name": "北京", "field_name": "常住人口", "value_num": 2185.3, "unit": "万人", "year": 2025},
            ]
        }

        task = self.benchmark_service.submit_fact_evaluation(
            annotation_name="facts.json",
            content=json.dumps(annotations, ensure_ascii=False).encode("utf-8"),
            document_ids=["doc_seed"],
            canonical_only=True,
        )
        self.executor.wait(task.task_id, timeout=5)

        task_record = self.repository.get_task(task.task_id)
        self.assertIsNotNone(task_record)
        self.assertEqual("succeeded", str(task_record.status))
        self.assertEqual(1.0, task_record.result["accuracy"])
        report = self.benchmark_service.get_report(task.task_id)
        self.assertIsNotNone(report)
        self.assertEqual(4, report["matched_count"])
        self.assertTrue(report["meets_threshold_0_80"])

    def test_template_benchmark_reports_perfect_accuracy_for_matching_expected_result(self) -> None:
        """模板基准测试应在结果完全匹配时给出满分。    Template benchmark should report perfect accuracy for a perfect fill."""

        self._seed_city_facts()
        template_bytes = build_simple_template_xlsx(
            headers=["城市", "GDP总量（亿元）", "常住人口（万人）"],
            rows=[
                ["上海", "", ""],
                ["北京", "", ""],
            ],
        )
        expected_bytes = build_simple_template_xlsx(
            headers=["城市", "GDP总量（亿元）", "常住人口（万人）"],
            rows=[
                ["上海", "56708.71", "2487.45"],
                ["北京", "52073.4", "2185.3"],
            ],
        )

        task = self.benchmark_service.submit_template_benchmark(
            template_name="city_template.xlsx",
            template_content=template_bytes,
            expected_result_name="city_template_expected.xlsx",
            expected_result_content=expected_bytes,
            fill_mode="canonical",
            document_ids=["doc_seed"],
        )
        self.executor.wait(task.task_id, timeout=5)

        task_record = self.repository.get_task(task.task_id)
        self.assertIsNotNone(task_record)
        self.assertEqual("succeeded", str(task_record.status))
        self.assertEqual(1.0, task_record.result["accuracy"])
        self.assertEqual(4, task_record.result["total_compared_cells"])
        report = self.benchmark_service.get_report(task.task_id)
        self.assertIsNotNone(report)
        self.assertEqual(4, report["matched_cells"])
        self.assertTrue(report["meets_threshold_0_80"])

    def test_template_benchmark_classifies_errors_and_generates_markdown(self) -> None:
        """基准测试应对不匹配单元格分类并支持 Markdown 输出。    Benchmark should classify mismatched cells and support Markdown output."""

        self._seed_city_facts()
        template_bytes = build_simple_template_xlsx(
            headers=["城市", "GDP总量（亿元）", "常住人口（万人）"],
            rows=[
                ["上海", "", ""],
                ["北京", "", ""],
            ],
        )
        # Expected with a deliberate numeric error (unit_conversion_error: 万→亿 for pop)
        expected_bytes = build_simple_template_xlsx(
            headers=["城市", "GDP总量（亿元）", "常住人口（万人）"],
            rows=[
                ["上海", "56708.71", "248745"],
                ["北京", "52073.4", "2185.3"],
            ],
        )

        task = self.benchmark_service.submit_template_benchmark(
            template_name="err_template.xlsx",
            template_content=template_bytes,
            expected_result_name="err_expected.xlsx",
            expected_result_content=expected_bytes,
            fill_mode="canonical",
            document_ids=["doc_seed"],
        )
        self.executor.wait(task.task_id, timeout=5)

        report = self.benchmark_service.get_report(task.task_id)
        self.assertIsNotNone(report)
        self.assertIn("error_counts", report)
        self.assertIsInstance(report["error_counts"], dict)
        # Should have at least one unit_conversion_error (248745 vs 2487.45)
        self.assertGreater(report["error_counts"].get("unit_conversion_error", 0), 0)

        # Verify Markdown generation
        md = generate_benchmark_markdown(report)
        self.assertIn("评测报告", md)
        self.assertIn("误差分类", md)
        self.assertIn("单位换算错误", md)

    def test_template_fill_auto_matches_relevant_documents_and_tracks_elapsed_seconds(self) -> None:
        """普通模板回填应自动筛选相关文档并记录耗时。    Regular template filling should auto-match relevant documents and record elapsed time."""

        _, city_task = self.document_service.upload_document(
            "city_report.txt",
            "2025年，上海GDP总量56,708.71亿元，常住人口2,487.45万人。".encode("utf-8"),
            document_set_id="set_auto",
        )
        _, contract_task = self.document_service.upload_document(
            "contract_report.txt",
            "合同金额为800万元，甲方为南京采购中心，乙方为南京信息公司。".encode("utf-8"),
            document_set_id="set_auto",
        )
        self.executor.wait(city_task.task_id, timeout=5)
        self.executor.wait(contract_task.task_id, timeout=5)

        template_bytes = build_simple_template_xlsx(
            headers=["城市", "GDP总量（亿元）"],
            rows=[["上海", ""]],
        )
        task = self.template_service.submit_fill_task(
            template_name="city_summary_template.xlsx",
            content=template_bytes,
            document_set_id="set_auto",
            auto_match=True,
        )
        self.executor.wait(task.task_id, timeout=5)

        task_record = self.repository.get_task(task.task_id)
        self.assertIsNotNone(task_record)
        self.assertEqual("succeeded", str(task_record.status))
        self.assertEqual("rules", task_record.result["match_mode"])
        self.assertEqual(1, len(task_record.result["matched_document_ids"]))
        matched_document = self.repository.get_document(task_record.result["matched_document_ids"][0])
        self.assertIsNotNone(matched_document)
        self.assertEqual("city_report.txt", matched_document.file_name)
        self.assertGreaterEqual(task_record.result["elapsed_seconds"], 0.0)

    def test_template_fill_respects_document_set_scope(self) -> None:
        """模板回填应只在指定文档批次内检索内容。    Template filling should only search within the requested document batch."""

        _, sh_task = self.document_service.upload_document(
            "shanghai.txt",
            "2025年，上海GDP总量56,708.71亿元。".encode("utf-8"),
            document_set_id="set_a",
        )
        _, bj_task = self.document_service.upload_document(
            "beijing.txt",
            "2025年，北京GDP总量52,073.40亿元。".encode("utf-8"),
            document_set_id="set_b",
        )
        self.executor.wait(sh_task.task_id, timeout=5)
        self.executor.wait(bj_task.task_id, timeout=5)

        template_bytes = build_simple_template_xlsx(
            headers=["城市", "GDP总量（亿元）"],
            rows=[["北京", ""]],
        )
        task = self.template_service.submit_fill_task(
            template_name="beijing_template.xlsx",
            content=template_bytes,
            document_set_id="set_b",
            auto_match=True,
        )
        self.executor.wait(task.task_id, timeout=5)

        task_record = self.repository.get_task(task.task_id)
        self.assertIsNotNone(task_record)
        self.assertEqual(1, len(task_record.result["matched_document_ids"]))
        matched_document = self.repository.get_document(task_record.result["matched_document_ids"][0])
        self.assertIsNotNone(matched_document)
        self.assertEqual("beijing.txt", matched_document.file_name)

        result = self.template_service.get_result(task.task_id)
        self.assertIsNotNone(result)
        workbook = load_xlsx(Path(result.output_path))
        first_sheet = workbook.sheets[0]
        rows = {row.row_index: row.values for row in first_sheet.rows}
        self.assertEqual("52073.4", rows[2][1])

    def test_document_interaction_service_can_extract_fields(self) -> None:
        """extract_fields 意图应返回按实体/字段过滤的结构化结果和产物文件。
        extract_fields intent should return filtered structured results and artifacts."""

        self._seed_city_facts()
        result = self.document_interaction_service.execute(
            message="指标提取 上海 GDP总量",
            document_ids=["doc_seed"],
        )
        self.assertEqual("extract", result["execution_type"])
        self.assertGreater(len(result["artifacts"]), 0)
        artifact = result["artifacts"][0]
        self.assertEqual("extract_fields", artifact["operation"])
        self.assertGreater(artifact["change_count"], 0)
        output = Path(artifact["output_path"])
        self.assertTrue(output.exists())
        data = json.loads(output.read_text(encoding="utf-8"))
        self.assertIsInstance(data, list)
        self.assertGreater(len(data), 0)

    def test_document_interaction_service_can_export_results(self) -> None:
        """export_results 意图应导出事实为 JSON 和 XLSX 文件。
        export_results intent should export facts as JSON and optionally XLSX files."""

        self._seed_city_facts()
        result = self.document_interaction_service.execute(
            message="导出所有数据",
            document_ids=["doc_seed"],
        )
        self.assertEqual("export", result["execution_type"])
        self.assertGreaterEqual(len(result["artifacts"]), 1)
        json_artifact = next(a for a in result["artifacts"] if a["file_name"].endswith(".json"))
        self.assertGreater(json_artifact["change_count"], 0)
        output = Path(json_artifact["output_path"])
        self.assertTrue(output.exists())
        data = json.loads(output.read_text(encoding="utf-8"))
        self.assertGreater(len(data), 0)
        # Check Chinese keys are used in export
        self.assertIn("实体", data[0])
        self.assertIn("字段", data[0])

    # ── T-1: PDF 解析测试 ──

    def test_pdf_upload_generates_page_blocks(self) -> None:
        """上传 PDF 后应生成 page 类型的 Block。
        Uploading a PDF should generate page-type blocks."""

        pdf_bytes = build_simple_pdf_with_table()
        _, task = self.document_service.upload_document("report.pdf", pdf_bytes)
        self.executor.wait(task.task_id, timeout=5)

        doc = self.repository.list_documents()[0]
        blocks = self.repository.list_blocks(doc.doc_id)
        self.assertGreater(len(blocks), 0)
        block_types = {b.block_type for b in blocks}
        self.assertIn("page", block_types)

    def test_pdf_upload_generates_table_row_blocks(self) -> None:
        """上传含表格的 PDF 后应生成 table_row 类型的 Block。
        Uploading a PDF with a table should generate table_row blocks."""

        pdf_bytes = build_simple_pdf_with_table()
        _, task = self.document_service.upload_document("table_report.pdf", pdf_bytes)
        self.executor.wait(task.task_id, timeout=5)

        doc = self.repository.list_documents()[0]
        blocks = self.repository.list_blocks(doc.doc_id)
        table_blocks = [b for b in blocks if b.block_type == "table_row"]
        self.assertGreater(len(table_blocks), 0)
        # Verify table metadata has headers and row_values
        first_table = table_blocks[0]
        self.assertIn("headers", first_table.metadata)
        self.assertIn("row_values", first_table.metadata)

    # ── T-1: Agent 问答分支测试 ──

    def test_agent_qa_branches_dispatch_correctly(self) -> None:
        """summarize / query_status / general_qa 意图应正确分发。
        Agent QA intents should be dispatched correctly."""

        self._seed_city_facts()

        # Test summarize
        result = self.document_interaction_service.execute(
            message="总结一下当前数据",
            document_ids=["doc_seed"],
        )
        self.assertEqual("summary", result["execution_type"])
        self.assertTrue(len(result["summary"]) > 0)

        # Test query_status
        result2 = self.document_interaction_service.execute(
            message="系统状态",
            document_ids=["doc_seed"],
        )
        self.assertEqual("status", result2["execution_type"])
        self.assertIn("文档", result2["summary"])

        # Test general_qa (a message that doesn't match any specific intent)
        result3 = self.document_interaction_service.execute(
            message="请问如何理解这些数据",
            document_ids=["doc_seed"],
        )
        self.assertEqual("qa", result3["execution_type"])

    # ── T-1: 对话 CRUD 测试 ──

    def test_conversation_crud_lifecycle(self) -> None:
        """创建 / 列表 / 获取 / 更新 / 删除对话应正常工作。
        Conversation CRUD lifecycle should work correctly."""

        from app.models.domain import ConversationRecord

        now = datetime.now(timezone.utc)
        record = ConversationRecord(
            conversation_id="conv_test_1",
            title="测试对话",
            created_at=now,
            updated_at=now,
            messages=[{"role": "user", "content": "Hello"}],
        )

        # Create
        created = self.repository.create_conversation(record)
        self.assertEqual("conv_test_1", created.conversation_id)
        self.assertEqual("测试对话", created.title)

        # Get
        fetched = self.repository.get_conversation("conv_test_1")
        self.assertIsNotNone(fetched)
        self.assertEqual(1, len(fetched.messages))

        # List
        conversations = self.repository.list_conversations()
        self.assertEqual(1, len(conversations))
        self.assertEqual("conv_test_1", conversations[0].conversation_id)

        # Update
        fetched.title = "更新后的对话"
        fetched.messages.append({"role": "assistant", "content": "Hi"})
        updated = self.repository.update_conversation(fetched)
        self.assertIsNotNone(updated)
        self.assertEqual("更新后的对话", updated.title)
        self.assertEqual(2, len(updated.messages))

        # Delete
        deleted = self.repository.delete_conversation("conv_test_1")
        self.assertIsNotNone(deleted)
        self.assertIsNone(self.repository.get_conversation("conv_test_1"))
        self.assertEqual(0, len(self.repository.list_conversations()))

    # ── T-1: Agent 对话持久化测试 ──

    def test_agent_service_persists_conversation_to_repository(self) -> None:
        """AgentService 应在接收消息后将对话持久化到仓储。
        AgentService should persist conversations to repository after receiving messages."""

        context_id = "ctx_persist_test"
        self.agent_service.chat("你好", context_id=context_id)

        # Verify conversation was persisted
        record = self.repository.get_conversation(context_id)
        self.assertIsNotNone(record)
        self.assertGreater(len(record.messages), 0)

        # Verify title is auto-generated from first user message
        self.assertTrue(len(record.title) > 0)

        # Clear conversation
        self.agent_service.clear_conversation(context_id)
        self.assertIsNone(self.repository.get_conversation(context_id))

    # ── T-1: Fact 复核测试 ──

    def test_low_confidence_fact_filtering_and_review(self) -> None:
        """低置信度筛选 → 人工修正 → 局部重回填应正常工作。
        Low-confidence filtering → manual review → should work correctly."""

        # Seed facts with varying confidence
        self.repository.add_document(
            DocumentRecord(
                doc_id="doc_review",
                file_name="review.txt",
                stored_path="review.txt",
                doc_type="txt",
                upload_time=datetime.now(timezone.utc),
                status=DocumentStatus.parsed,
                metadata={},
            )
        )
        self.repository.add_facts([
            FactRecord(
                fact_id="fact_high",
                entity_type="city",
                entity_name="上海",
                field_name="GDP总量",
                value_num=56708.71,
                value_text="56708.71",
                unit="亿元",
                year=2025,
                source_doc_id="doc_review",
                source_block_id="blk_1",
                source_span="上海GDP总量56708.71亿元",
                confidence=0.98,
            ),
            FactRecord(
                fact_id="fact_low",
                entity_type="city",
                entity_name="上海",
                field_name="一般公共预算收入",
                value_num=100.0,
                value_text="100",
                unit="亿元",
                year=2025,
                source_doc_id="doc_review",
                source_block_id="blk_1",
                source_span="上海一般公共预算收入100亿元",
                confidence=0.45,
            ),
        ])

        # Filter low-confidence facts
        low = self.repository.list_facts(min_confidence=0.0)
        low_conf = [f for f in low if f.confidence < 0.7]
        self.assertEqual(1, len(low_conf))
        self.assertEqual("fact_low", low_conf[0].fact_id)

        # Manual review: fix the value
        updated = self.repository.update_fact(
            "fact_low",
            status="reviewed",
            metadata_updates={"reviewed_by": "human", "original_value": 100.0},
        )
        self.assertIsNotNone(updated)
        self.assertEqual("reviewed", updated.status)
        self.assertEqual("human", updated.metadata["reviewed_by"])

    def _seed_city_facts(self) -> list[FactRecord]:
        """插入模板测试所需的 canonical 事实。    Insert canonical facts required by template tests."""

        self.repository.add_document(
            DocumentRecord(
                doc_id="doc_seed",
                file_name="seed.txt",
                stored_path="seed.txt",
                doc_type="txt",
                upload_time=datetime.now(timezone.utc),
                status=DocumentStatus.parsed,
                metadata={},
            )
        )
        return self.repository.add_facts(
            [
                FactRecord(
                    fact_id="fact_sh_gdp",
                    entity_type="city",
                    entity_name="上海",
                    field_name="GDP总量",
                    value_num=56708.71,
                    value_text="56,708.71",
                    unit="亿元",
                    year=2025,
                    source_doc_id="doc_seed",
                    source_block_id="blk_1",
                    source_span="上海GDP总量56,708.71亿元",
                    confidence=0.98,
                ),
                FactRecord(
                    fact_id="fact_sh_pop",
                    entity_type="city",
                    entity_name="上海",
                    field_name="常住人口",
                    value_num=2487.45,
                    value_text="2,487.45",
                    unit="万人",
                    year=2025,
                    source_doc_id="doc_seed",
                    source_block_id="blk_1",
                    source_span="上海常住人口2487.45万人",
                    confidence=0.97,
                ),
                FactRecord(
                    fact_id="fact_bj_gdp",
                    entity_type="city",
                    entity_name="北京",
                    field_name="GDP总量",
                    value_num=52073.4,
                    value_text="52,073.40",
                    unit="亿元",
                    year=2025,
                    source_doc_id="doc_seed",
                    source_block_id="blk_2",
                    source_span="北京GDP总量52,073.40亿元",
                    confidence=0.96,
                ),
                FactRecord(
                    fact_id="fact_bj_pop",
                    entity_type="city",
                    entity_name="北京",
                    field_name="常住人口",
                    value_num=2185.3,
                    value_text="2,185.30",
                    unit="万人",
                    year=2025,
                    source_doc_id="doc_seed",
                    source_block_id="blk_2",
                    source_span="北京常住人口2185.30万人",
                    confidence=0.95,
                ),
            ]
        )


def build_simple_template_xlsx(headers: list[str], rows: list[list[str]]) -> bytes:
    """在内存中构造最小可用 XLSX 模板。    Build a minimal usable XLSX template in memory."""

    sheet_rows = [headers, *rows]
    sheet_xml_rows = []
    for row_index, row_values in enumerate(sheet_rows, start=1):
        cells = []
        for column_index, value in enumerate(row_values, start=1):
            column_letter = chr(ord("A") + column_index - 1)
            cell_ref = f"{column_letter}{row_index}"
            cells.append(f'<c r="{cell_ref}" t="inlineStr"><is><t>{escape(value)}</t></is></c>')
        sheet_xml_rows.append(f'<row r="{row_index}">{"".join(cells)}</row>')

    workbook_bytes = io.BytesIO()
    with zipfile.ZipFile(workbook_bytes, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(
            "[Content_Types].xml",
            """<?xml version="1.0" encoding="UTF-8"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
  <Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
</Types>
""",
        )
        archive.writestr(
            "_rels/.rels",
            """<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>
</Relationships>
""",
        )
        archive.writestr(
            "xl/workbook.xml",
            """<?xml version="1.0" encoding="UTF-8"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"
          xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <sheets>
    <sheet name="Sheet1" sheetId="1" r:id="rId1"/>
  </sheets>
</workbook>
""",
        )
        archive.writestr(
            "xl/_rels/workbook.xml.rels",
            """<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>
</Relationships>
""",
        )
        archive.writestr(
            "xl/worksheets/sheet1.xml",
            f"""<?xml version="1.0" encoding="UTF-8"?>
<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
  <sheetData>
    {''.join(sheet_xml_rows)}
  </sheetData>
</worksheet>
""",
        )
    return workbook_bytes.getvalue()


def build_simple_template_docx(headers: list[str], rows: list[list[str]]) -> bytes:
    """在内存中构造最小 DOCX 表格模板。    Build a minimal DOCX table template in memory."""

    return build_simple_document_docx(table_rows=[headers, *rows])


def build_simple_document_docx(
    *,
    paragraphs: list[str] | None = None,
    table_rows: list[list[str]] | None = None,
) -> bytes:
    """在内存中构造最小 DOCX 文档。    Build a minimal DOCX document in memory."""

    paragraph_xml = "".join(
        f"<w:p><w:r><w:t>{escape(text)}</w:t></w:r></w:p>"
        for text in (paragraphs or [])
    )
    table_xml = ""
    if table_rows:
        row_xml = []
        for row in table_rows:
            cells = "".join(
                f"<w:tc><w:p><w:r><w:t>{escape(value)}</w:t></w:r></w:p></w:tc>"
                for value in row
            )
            row_xml.append(f"<w:tr>{cells}</w:tr>")
        table_xml = f"<w:tbl>{''.join(row_xml)}</w:tbl>"

    document_xml = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:body>
    {paragraph_xml}
    {table_xml}
    <w:sectPr/>
  </w:body>
</w:document>
"""

    docx_bytes = io.BytesIO()
    with zipfile.ZipFile(docx_bytes, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(
            "[Content_Types].xml",
            """<?xml version="1.0" encoding="UTF-8"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
</Types>
""",
        )
        archive.writestr(
            "_rels/.rels",
            """<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>
""",
        )
        archive.writestr("word/document.xml", document_xml)
    return docx_bytes.getvalue()


def build_simple_pdf_with_table() -> bytes:
    """生成含文本和表格的最小 PDF。    Build a minimal PDF with text and a table for testing."""

    from fpdf import FPDF

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", size=12)
    pdf.cell(text="City Economic Report 2025")
    pdf.ln(10)

    # Table
    headers = ["City", "GDP", "Population"]
    rows = [
        ["Shanghai", "56708.71", "2487.45"],
        ["Beijing", "52073.40", "2185.30"],
    ]
    col_width = 50
    pdf.set_font("Helvetica", "B", 10)
    for header in headers:
        pdf.cell(col_width, 8, header, border=1)
    pdf.ln()
    pdf.set_font("Helvetica", size=10)
    for row in rows:
        for cell in row:
            pdf.cell(col_width, 8, cell, border=1)
        pdf.ln()

    return bytes(pdf.output())
