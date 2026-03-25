from __future__ import annotations

import re
from collections.abc import Iterable

from app.core.catalog import (
    CITY_NAMES,
    ENTITY_COLUMN_ALIASES,
    FIELD_ALIASES,
    FIELD_CANONICAL_UNITS,
)

_BRACKET_TEXT_RE = re.compile(r"[（(].*?[)）]")
_WHITESPACE_RE = re.compile(r"\s+")
_NUMERIC_RE = re.compile(r"(?P<value>-?\d[\d,]*(?:\.\d+)?)\s*(?P<unit>万亿元|亿元|亿|万元|元|万人|人|%)?")
_YEAR_RE = re.compile(r"(?P<year>(?:19|20)\d{2})年?")
_CITY_RE = re.compile(r"(?P<name>[\u4e00-\u9fff]{2,8}市)")

_FIELD_ALIAS_LOOKUP: dict[str, str] = {}
for canonical_name, aliases in FIELD_ALIASES.items():
    normalized_values = {canonical_name, *aliases}
    for alias in normalized_values:
        stripped = _WHITESPACE_RE.sub("", _BRACKET_TEXT_RE.sub("", alias)).lower()
        _FIELD_ALIAS_LOOKUP[stripped] = canonical_name

_ENTITY_COLUMN_LOOKUP = {
    _WHITESPACE_RE.sub("", _BRACKET_TEXT_RE.sub("", name)).lower()
    for name in ENTITY_COLUMN_ALIASES
}


def strip_header_adornments(raw_value: str) -> str:
    """移除表头字符串中的空白和括号提示信息。
    Remove whitespace and bracketed hints from a header string.
    """
    return _WHITESPACE_RE.sub("", _BRACKET_TEXT_RE.sub("", raw_value or "")).strip()


def normalize_field_name(raw_value: str) -> str | None:
    """将原始表头或别名映射为标准字段名。
    Map a raw header or alias string to its canonical field name.
    """
    if not raw_value:
        return None
    candidate = strip_header_adornments(raw_value).lower()
    return _FIELD_ALIAS_LOOKUP.get(candidate)


def is_entity_column(raw_value: str) -> bool:
    """判断某个表头是否可能表示实体列。
    Return whether a header is likely describing the entity column.
    """
    return strip_header_adornments(raw_value).lower() in _ENTITY_COLUMN_LOOKUP


def normalize_entity_name(raw_value: str) -> str:
    """标准化实体名称，便于跨文档和模板匹配。
    Normalize entity text for matching across documents and templates.
    """
    candidate = re.sub(r"[\s:：\-_/]+", "", raw_value or "")
    if candidate.endswith("市") and len(candidate) > 2:
        candidate = candidate[:-1]
    return candidate


def find_entity_mentions(text: str, extra_candidates: Iterable[str] | None = None) -> list[str]:
    """返回文本片段中检测到的唯一实体提及。
    Return unique entity mentions detected in a text snippet.
    """
    candidates: list[str] = []
    seen: set[str] = set()

    def _push(name: str) -> None:
        """在保持顺序的前提下插入一个标准化实体提及。
        Insert one normalized entity mention while preserving order.
        """
        normalized = normalize_entity_name(name)
        if normalized and normalized not in seen:
            seen.add(normalized)
            candidates.append(normalized)

    for city_name in CITY_NAMES:
        if city_name in text:
            _push(city_name)

    for match in _CITY_RE.finditer(text):
        _push(match.group("name"))

    if extra_candidates:
        for candidate in extra_candidates:
            if candidate and candidate in text:
                _push(candidate)

    return candidates


def infer_year(text: str) -> int | None:
    """推断文本中首次出现的四位年份。
    Infer the first four-digit year mentioned in text.
    """
    match = _YEAR_RE.search(text)
    if not match:
        return None
    return int(match.group("year"))


def extract_numeric_with_unit(raw_value: str) -> tuple[float | None, str | None]:
    """从文本中提取一个数值和可选单位。
    Extract one numeric value and optional unit from text.
    """
    if not raw_value:
        return None, None
    match = _NUMERIC_RE.search(raw_value.replace("，", ","))
    if not match:
        return None, None
    number = float(match.group("value").replace(",", ""))
    unit = match.group("unit")
    return number, unit


def convert_to_canonical_unit(
    field_name: str,
    value_num: float | None,
    unit: str | None,
) -> tuple[float | None, str | None]:
    """将数值转换为字段配置的标准单位。
    Convert a value into the canonical unit configured for a field.
    """
    if value_num is None:
        return None, FIELD_CANONICAL_UNITS.get(field_name, unit)

    canonical_unit = FIELD_CANONICAL_UNITS.get(field_name, unit)
    if not unit or not canonical_unit or unit == canonical_unit:
        return value_num, canonical_unit

    if field_name in {"GDP总量", "一般公共预算收入"}:
        if unit == "万亿元":
            return value_num * 10000, "亿元"
        if unit == "万元":
            return value_num / 10000, "亿元"
        if unit == "元":
            return value_num / 100000000, "亿元"
        if unit == "亿":
            return value_num, "亿元"

    if field_name == "常住人口":
        if unit == "人":
            return value_num / 10000, "万人"

    if field_name in {"人均GDP", "合同金额"}:
        if unit == "万元":
            return value_num * 10000, "元"
        if unit in {"亿元", "亿"}:
            return value_num * 100000000, "元"

    return value_num, canonical_unit


def format_value(value: float | None) -> str:
    """将数值格式化为紧凑的人类可读字符串。
    Format a numeric value into a compact human-readable string.
    """
    if value is None:
        return ""
    if float(value).is_integer():
        return str(int(value))
    return f"{value:.4f}".rstrip("0").rstrip(".")
