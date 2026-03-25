from __future__ import annotations

import re
from pathlib import Path

from app.models.domain import DocumentBlock
from app.parsers.base import DocumentParser, read_text_file
from app.utils.ids import new_id

_HEADING_RE = re.compile(r"^(?P<marker>(?:[一二三四五六七八九十]+[、.]|\d+(?:\.\d+)*[、.]?))")


class PlainTextParser(DocumentParser):
    """将纯文本文件解析为标题块和段落块。
    Parse plain text files into heading and paragraph blocks.
    """

    supported_suffixes = (".txt",)

    def parse(self, path: Path, doc_id: str) -> list[DocumentBlock]:
        """将 TXT 文件转换为简单的标题和段落块。
        Convert a TXT file into simple heading and paragraph blocks.
        """
        text = read_text_file(path)
        blocks: list[DocumentBlock] = []
        section_path: list[str] = []
        paragraph_lines: list[str] = []
        index = 0

        def flush_paragraph() -> None:
            """将缓冲行输出为一个段落块。
            Emit one paragraph block from buffered lines.
            """
            nonlocal index
            if not paragraph_lines:
                return
            index += 1
            content = " ".join(line.strip() for line in paragraph_lines if line.strip())
            blocks.append(
                DocumentBlock(
                    block_id=new_id("blk"),
                    doc_id=doc_id,
                    block_type="paragraph",
                    text=content,
                    section_path=section_path.copy(),
                    page_or_index=index,
                )
            )
            paragraph_lines.clear()

        for line in text.splitlines():
            stripped = line.strip()
            if not stripped:
                flush_paragraph()
                continue
            if _HEADING_RE.match(stripped):
                flush_paragraph()
                section_path = [stripped]
                index += 1
                blocks.append(
                    DocumentBlock(
                        block_id=new_id("blk"),
                        doc_id=doc_id,
                        block_type="heading",
                        text=stripped,
                        section_path=section_path.copy(),
                        page_or_index=index,
                    )
                )
                continue
            paragraph_lines.append(stripped)

        flush_paragraph()
        return blocks
