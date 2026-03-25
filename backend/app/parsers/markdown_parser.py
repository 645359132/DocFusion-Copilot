from __future__ import annotations

from pathlib import Path

from app.models.domain import DocumentBlock
from app.parsers.base import DocumentParser, read_text_file
from app.utils.ids import new_id


class MarkdownParser(DocumentParser):
    """将 Markdown 文件解析为标题、段落和表格行。
    Parse Markdown files into headings, paragraphs and table rows.
    """

    supported_suffixes = (".md",)

    def parse(self, path: Path, doc_id: str) -> list[DocumentBlock]:
        """将 Markdown 文件转换为标准化文档块。
        Convert a Markdown file into normalized document blocks.
        """
        text = read_text_file(path)
        lines = text.splitlines()
        blocks: list[DocumentBlock] = []
        section_path: list[str] = []
        paragraph_lines: list[str] = []
        table_lines: list[str] = []
        index = 0

        def flush_paragraph() -> None:
            """将缓冲中的 Markdown 行输出为一个段落块。
            Emit one paragraph block from buffered Markdown lines.
            """
            nonlocal index
            if not paragraph_lines:
                return
            index += 1
            blocks.append(
                DocumentBlock(
                    block_id=new_id("blk"),
                    doc_id=doc_id,
                    block_type="paragraph",
                    text=" ".join(paragraph_lines).strip(),
                    section_path=section_path.copy(),
                    page_or_index=index,
                )
            )
            paragraph_lines.clear()

        def flush_table() -> None:
            """将缓冲中的 Markdown 表格行输出为表格块。
            Emit table-row blocks from buffered Markdown table lines.
            """
            nonlocal index
            if len(table_lines) < 2:
                table_lines.clear()
                return
            rows = [_parse_markdown_row(line) for line in table_lines]
            headers = rows[0]
            data_rows = rows[2:] if len(rows) > 2 else []
            for row_values in data_rows:
                if not any(row_values):
                    continue
                index += 1
                row_map = {
                    header: row_values[position] if position < len(row_values) else ""
                    for position, header in enumerate(headers)
                }
                blocks.append(
                    DocumentBlock(
                        block_id=new_id("blk"),
                        doc_id=doc_id,
                        block_type="table_row",
                        text=" | ".join(row_values),
                        section_path=section_path.copy(),
                        page_or_index=index,
                        metadata={
                            "headers": headers,
                            "row_values": row_map,
                        },
                    )
                )
            table_lines.clear()

        for line in lines:
            stripped = line.strip()
            if stripped.startswith("#"):
                flush_paragraph()
                flush_table()
                level = len(stripped) - len(stripped.lstrip("#"))
                title = stripped[level:].strip()
                section_path = section_path[: max(level - 1, 0)]
                section_path.append(title)
                index += 1
                blocks.append(
                    DocumentBlock(
                        block_id=new_id("blk"),
                        doc_id=doc_id,
                        block_type="heading",
                        text=title,
                        section_path=section_path.copy(),
                        page_or_index=index,
                    )
                )
                continue

            if stripped.startswith("|") and stripped.endswith("|"):
                flush_paragraph()
                table_lines.append(stripped)
                continue

            if table_lines:
                flush_table()

            if not stripped:
                flush_paragraph()
                continue

            paragraph_lines.append(stripped)

        flush_paragraph()
        flush_table()
        return blocks


def _parse_markdown_row(line: str) -> list[str]:
    """将单行 Markdown 表格拆分为去空白后的单元格值。
    Split one Markdown table line into trimmed cell values.
    """
    return [cell.strip() for cell in line.strip().strip("|").split("|")]
