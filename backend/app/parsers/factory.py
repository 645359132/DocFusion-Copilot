from __future__ import annotations

from pathlib import Path

from app.models.domain import DocumentBlock
from app.parsers.base import DocumentParser
from app.parsers.docx_parser import DocxParser
from app.parsers.markdown_parser import MarkdownParser
from app.parsers.pdf_parser import PdfParser
from app.parsers.text_parser import PlainTextParser
from app.parsers.xlsx_parser import XlsxParser


class ParserRegistry:
    """按文件后缀分发到具体解析器的注册表。
    Registry that dispatches files to the correct concrete parser.
    """

    def __init__(self) -> None:
        """初始化内置的解析器实现。
        Initialize built-in parser implementations.
        """
        self._parsers: list[DocumentParser] = [
            DocxParser(),
            MarkdownParser(),
            PdfParser(),
            PlainTextParser(),
            XlsxParser(),
        ]

    def parse(self, file_path: str | Path, doc_id: str) -> list[DocumentBlock]:
        """选择首个支持该后缀的解析器来处理文件。
        Parse a file by selecting the first parser that supports its suffix.
        """
        path = Path(file_path)
        suffix = path.suffix.lower()
        for parser in self._parsers:
            if suffix in parser.supported_suffixes:
                return parser.parse(path, doc_id)
        raise ValueError(f"Unsupported document type: {suffix}")
