from __future__ import annotations

import re
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

from app.models.domain import DocumentBlock
from app.parsers.base import DocumentParser
from app.utils.ids import new_id

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
W = {"w": W_NS}
_NUMBERED_HEADING_RE = re.compile(
    r"^(?:[一二三四五六七八九十]+[、.．]|\d{1,2}(?:\.\d{1,2}){0,2}[、.．])\s*\S+"
)


def _w(tag: str) -> str:
    """为 WordprocessingML 标签补齐命名空间。    Qualify a WordprocessingML tag with its namespace."""

    return f"{{{W_NS}}}{tag}"


class DocxParser(DocumentParser):
    """将 DOCX 文档解析为标题、段落和表格行文档块。    Parse DOCX files into heading, paragraph and table-row blocks."""

    supported_suffixes = (".docx",)

    def parse(self, path: Path, doc_id: str) -> list[DocumentBlock]:
        """通过 XML 检查从 DOCX 中提取逻辑块。    Extract logical blocks from a DOCX document using XML inspection."""

        blocks: list[DocumentBlock] = []
        section_path: list[str] = []
        index = 0

        with zipfile.ZipFile(path, "r") as archive:
            document_root = ET.fromstring(archive.read("word/document.xml"))

        body = document_root.find("w:body", W)
        if body is None:
            return blocks

        for child in body:
            if child.tag == _w("p"):
                text = "".join(node.text or "" for node in child.findall(".//w:t", W)).strip()
                if not text:
                    continue
                heading_level = _infer_heading_level(child, text)
                index += 1
                if heading_level is not None:
                    section_path = section_path[: max(heading_level - 1, 0)]
                    section_path.append(text)
                    blocks.append(
                        DocumentBlock(
                            block_id=new_id("blk"),
                            doc_id=doc_id,
                            block_type="heading",
                            text=text,
                            section_path=section_path.copy(),
                            page_or_index=index,
                        )
                    )
                    continue

                blocks.append(
                    DocumentBlock(
                        block_id=new_id("blk"),
                        doc_id=doc_id,
                        block_type="paragraph",
                        text=text,
                        section_path=section_path.copy(),
                        page_or_index=index,
                    )
                )
                continue

            if child.tag != _w("tbl"):
                continue

            rows = []
            for row_el in child.findall("w:tr", W):
                row_values = []
                logical_col = 0
                for cell_el in row_el.findall("w:tc", W):
                    tc_pr = cell_el.find("w:tcPr", W)
                    # Check for vertical merge continuation
                    v_merge = tc_pr.find("w:vMerge", W) if tc_pr is not None else None
                    is_v_merge_continue = False
                    if v_merge is not None:
                        val = v_merge.get(_w("val"), "")
                        if val != "restart":
                            is_v_merge_continue = True

                    # Determine horizontal span
                    grid_span = 1
                    if tc_pr is not None:
                        gs_el = tc_pr.find("w:gridSpan", W)
                        if gs_el is not None:
                            try:
                                grid_span = int(gs_el.get(_w("val"), "1"))
                            except (ValueError, TypeError):
                                grid_span = 1

                    value = "" if is_v_merge_continue else "".join(
                        node.text or "" for node in cell_el.findall(".//w:t", W)
                    ).strip()

                    # Fill up to logical column position
                    while len(row_values) < logical_col:
                        row_values.append("")
                    row_values.append(value)
                    for _ in range(grid_span - 1):
                        row_values.append("")
                    logical_col += grid_span
                rows.append(row_values)

            if len(rows) < 2:
                continue

            headers = rows[0]
            for row_values in rows[1:]:
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

        return blocks


def _infer_heading_level(paragraph_el: ET.Element, text: str) -> int | None:
    """根据段落样式或编号模式推断标题层级。    Infer a heading level from paragraph style metadata or numbering patterns."""

    style_el = paragraph_el.find("w:pPr/w:pStyle", W)
    if style_el is not None:
        style_name = style_el.get(f"{{{W_NS}}}val", "")
        digits = "".join(char for char in style_name if char.isdigit())
        if digits:
            return max(int(digits), 1)
        if "heading" in style_name.lower() or "标题" in style_name:
            return 1

    if _NUMBERED_HEADING_RE.match(text):
        prefix = text.split(maxsplit=1)[0]
        if prefix[0].isdigit():
            return min(prefix.rstrip("、.．").count(".") + 1, 4)
        return 1
    return None
