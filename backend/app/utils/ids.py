from __future__ import annotations

from uuid import uuid4


def new_id(prefix: str) -> str:
    """为仓储对象生成带前缀的短标识符。
    Generate a short prefixed identifier for repository objects.
    """
    return f"{prefix}_{uuid4().hex[:12]}"
