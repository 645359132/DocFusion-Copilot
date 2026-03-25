from __future__ import annotations

import re
from pathlib import Path


_INVALID_FILENAME_CHARS = re.compile(r"[^A-Za-z0-9._\-\u4e00-\u9fff]+")


def safe_filename(file_name: str) -> str:
    """清洗用户上传文件名以便本地保存。
    Sanitize a user-supplied file name for local storage.
    """
    cleaned = _INVALID_FILENAME_CHARS.sub("_", file_name).strip("._")
    return cleaned or "unnamed"


def ensure_directory(path: Path) -> Path:
    """按需创建目录并返回该路径对象。
    Create a directory if needed and return the same path.
    """
    path.mkdir(parents=True, exist_ok=True)
    return path
