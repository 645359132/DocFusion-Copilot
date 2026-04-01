from __future__ import annotations

from pathlib import Path

from app.models.domain import DocumentBlock
from app.parsers.base import DocumentParser
from app.utils.ids import new_id


class PdfParser(DocumentParser):
    """将 PDF 文档逐页解析为文本块和表格行块。
    Parse PDF documents page-by-page into text and table-row blocks.
    """

    supported_suffixes = (".pdf",)

    def parse(self, path: Path, doc_id: str) -> list[DocumentBlock]:
        """通过 pdfplumber 提取每页文本和表格。
        Extract per-page text and tables using pdfplumber.
        """
        import pdfplumber

        blocks: list[DocumentBlock] = []
        index = 0

        with pdfplumber.open(path) as pdf:
            for page_number, page in enumerate(pdf.pages, start=1):
                # Extract page text
                page_text = (page.extract_text() or "").strip()
                if page_text:
                    index += 1
                    blocks.append(
                        DocumentBlock(
                            block_id=new_id("blk"),
                            doc_id=doc_id,
                            block_type="page",
                            text=page_text,
                            section_path=[f"Page {page_number}"],
                            page_or_index=page_number,
                            metadata={"page_number": page_number},
                        )
                    )

                # Extract tables from the page
                tables = page.extract_tables() or []
                for table_index, table in enumerate(tables):
                    if not table or len(table) < 2:
                        continue
                    # First row is headers
                    headers = [str(cell or "").strip() for cell in table[0]]
                    if not any(headers):
                        continue

                    for row in table[1:]:
                        row_values = [str(cell or "").strip() for cell in row]
                        if not any(row_values):
                            continue
                        index += 1
                        row_map = {
                            header: row_values[pos] if pos < len(row_values) else ""
                            for pos, header in enumerate(headers)
                        }
                        blocks.append(
                            DocumentBlock(
                                block_id=new_id("blk"),
                                doc_id=doc_id,
                                block_type="table_row",
                                text=" | ".join(row_values),
                                section_path=[f"Page {page_number}"],
                                page_or_index=index,
                                metadata={
                                    "page_number": page_number,
                                    "table_index": table_index,
                                    "headers": headers,
                                    "row_values": row_map,
                                },
                            )
                        )

        return blocks
