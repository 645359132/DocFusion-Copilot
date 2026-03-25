from __future__ import annotations

import io
import sys
import unittest
import zipfile
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import get_settings
from app.models.domain import DocumentRecord, DocumentStatus, FactRecord
from app.parsers.factory import ParserRegistry
from app.repositories.memory import InMemoryRepository
from app.services.document_service import DocumentService
from app.services.fact_extraction import FactExtractionService
from app.services.template_service import TemplateService
from app.services.trace_service import TraceService
from app.tasks.executor import TaskExecutor
from app.utils.spreadsheet import load_xlsx


class BackendPipelineTests(unittest.TestCase):
    """后端 MVP 主流程的端到端单元测试。
    End-to-end unit tests for the backend MVP pipeline.
    """

    def setUp(self) -> None:
        """为每个测试用例创建隔离的服务依赖图。
        Create an isolated service graph for each test case.
        """
        self.settings = get_settings()
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
        )
        self.trace_service = TraceService(repository=self.repository)

    def tearDown(self) -> None:
        """释放测试期间创建的执行器资源。
        Shut down executor resources created during the test.
        """
        self.executor.shutdown()

    def test_text_document_upload_extracts_expected_city_facts(self) -> None:
        """上传文本报告后应得到四条 canonical 城市事实。
        Uploading a text report should yield four canonical city facts.
        """
        content = (
            "2025年，上海GDP总量56,708.71亿元，常住人口2487.45万人，"
            "人均GDP228020元，一般公共预算收入8500.91亿元。"
        )
        _, task = self.document_service.upload_document("city_report.txt", content.encode("utf-8"))
        self.executor.wait(task.task_id, timeout=5)

        facts = self.repository.list_facts(canonical_only=True)
        fields = {fact.field_name for fact in facts}

        self.assertEqual(4, len(facts))
        self.assertEqual({"GDP总量", "常住人口", "人均GDP", "一般公共预算收入"}, fields)
        self.assertTrue(all(fact.entity_name == "上海" for fact in facts))

    def test_template_fill_populates_xlsx_cells(self) -> None:
        """模板回填应将预置事实写回到 XLSX 单元格中。
        Template filling should write seeded fact values back into XLSX cells.
        """
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

    def test_trace_service_reports_template_usage(self) -> None:
        """追溯事实时应包含使用该事实的工作簿单元格。
        Tracing a fact should include the workbook cell that consumed it.
        """
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

    def _seed_city_facts(self) -> list[FactRecord]:
        """插入模板相关测试使用的一小组 canonical 事实。
        Insert a small canonical fact set used by template-related tests.
        """
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
    """在内存中构造一个最小可用的 XLSX 工作簿供单元测试使用。
    Build a minimal XLSX workbook in memory for unit tests.
    """
    sheet_rows = [headers, *rows]
    sheet_xml_rows = []
    for row_index, row_values in enumerate(sheet_rows, start=1):
        cells = []
        for column_index, value in enumerate(row_values, start=1):
            column_letter = chr(ord("A") + column_index - 1)
            cell_ref = f"{column_letter}{row_index}"
            cells.append(
                f'<c r="{cell_ref}" t="inlineStr"><is><t>{value}</t></is></c>'
            )
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
