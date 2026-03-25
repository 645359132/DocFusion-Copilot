from __future__ import annotations

from pathlib import Path

from app.models.domain import DocumentBlock
from app.parsers.base import DocumentParser
from app.utils.ids import new_id
from app.utils.spreadsheet import load_xlsx


class XlsxParser(DocumentParser):
    """将 XLSX 工作簿解析为按行组织的标准化表格块。
    Parse XLSX workbooks into normalized row-oriented table blocks.
    """

    supported_suffixes = (".xlsx",)

    def parse(self, path: Path, doc_id: str) -> list[DocumentBlock]:
        """将工作表中的行提取为结构化表格行块。
        Extract worksheet rows as structured table-row blocks.
        """
        workbook = load_xlsx(path)
        blocks: list[DocumentBlock] = []
        index = 0

        for sheet in workbook.sheets:
            if not sheet.rows:
                continue
            headers = next((row.values for row in sheet.rows if any(cell.strip() for cell in row.values)), [])
            if not headers:
                continue

            for row in sheet.rows[1:]:
                if not any(cell.strip() for cell in row.values):
                    continue
                index += 1
                row_map = {
                    header: row.values[position] if position < len(row.values) else ""
                    for position, header in enumerate(headers)
                }
                blocks.append(
                    DocumentBlock(
                        block_id=new_id("blk"),
                        doc_id=doc_id,
                        block_type="table_row",
                        text=" | ".join(row.values),
                        section_path=[sheet.name],
                        page_or_index=index,
                        metadata={
                            "sheet_name": sheet.name,
                            "headers": headers,
                            "row_values": row_map,
                            "row_index": row.row_index,
                        },
                    )
                )

        return blocks
