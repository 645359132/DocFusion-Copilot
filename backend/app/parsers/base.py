from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from app.models.domain import DocumentBlock


class DocumentParser(ABC):
    """将文件转换为标准化文档块的抽象解析器协议。
    Abstract parser contract for converting a file into normalized blocks.
    """

    supported_suffixes: tuple[str, ...] = ()

    @abstractmethod
    def parse(self, path: Path, doc_id: str) -> list[DocumentBlock]:
        """将单个文件解析为标准化文档块列表。
        Parse one file into normalized document blocks.
        """
        raise NotImplementedError


def read_text_file(path: Path) -> str:
    """使用常见编码回退链读取文本文件。
    Read a text file using a small fallback chain of common encodings.
    """
    for encoding in ("utf-8", "utf-8-sig", "gbk"):
        try:
            return path.read_text(encoding=encoding)
        except UnicodeDecodeError:
            continue
    return path.read_text(encoding="utf-8", errors="ignore")
