from __future__ import annotations

import re
from collections import OrderedDict
from dataclasses import replace

from app.core.catalog import FIELD_ALIASES, FIELD_ENTITY_TYPES
from app.models.domain import DocumentBlock, DocumentRecord, FactRecord
from app.utils.ids import new_id
from app.utils.normalizers import (
    convert_to_canonical_unit,
    extract_numeric_with_unit,
    find_entity_mentions,
    infer_year,
    is_entity_column,
    normalize_entity_name,
    normalize_field_name,
)

_BRACKET_UNIT_RE = re.compile(r"[（(](.*?)[）)]")
_GENERIC_NUMBER_RE = re.compile(r"(?P<value>-?\d[\d,]*(?:\.\d+)?)\s*(?P<unit>万亿元|亿元|亿|万元|元|万人|人|%)?")


class FactExtractionService:
    """从标准化文档块中抽取结构化事实。
    Extract structured facts from normalized document blocks.
    """

    def extract(self, document: DocumentRecord, blocks: list[DocumentBlock]) -> list[FactRecord]:
        """执行块级抽取并返回去重后的事实列表。
        Run block-level extraction and return deduplicated facts.
        """
        facts: list[FactRecord] = []
        for block in blocks:
            if block.block_type == "table_row":
                facts.extend(self._extract_from_table_row(document, block))
                continue
            facts.extend(self._extract_from_text(document, block))
        return list(self._deduplicate(facts).values())

    def _extract_from_table_row(self, document: DocumentRecord, block: DocumentBlock) -> list[FactRecord]:
        """从标准化表格行块中抽取事实。
        Extract facts from a normalized table row block.
        """
        row_values = block.metadata.get("row_values")
        if not isinstance(row_values, dict):
            return []

        entity_name = ""
        for header, value in row_values.items():
            if is_entity_column(str(header)) and value:
                entity_name = normalize_entity_name(str(value))
                break
            if normalize_field_name(header) is None and value:
                mentions = find_entity_mentions(str(value))
                if mentions:
                    entity_name = mentions[0]
                    break

        facts: list[FactRecord] = []
        year = infer_year(block.text) or infer_year(document.file_name)

        for header, raw_value in row_values.items():
            field_name = normalize_field_name(str(header))
            if not field_name or not str(raw_value).strip():
                continue

            header_unit = self._extract_unit_from_header(str(header))
            value_num, detected_unit = extract_numeric_with_unit(str(raw_value))
            final_num, final_unit = convert_to_canonical_unit(
                field_name,
                value_num,
                detected_unit or header_unit,
            )
            entity = entity_name or self._fallback_entity_from_text(block.text)
            if not entity and FIELD_ENTITY_TYPES.get(field_name) == "city":
                continue

            facts.append(
                FactRecord(
                    fact_id=new_id("fact"),
                    entity_type=FIELD_ENTITY_TYPES.get(field_name, "generic"),
                    entity_name=entity or document.file_name,
                    field_name=field_name,
                    value_num=final_num,
                    value_text=str(raw_value).strip(),
                    unit=final_unit,
                    year=year,
                    source_doc_id=document.doc_id,
                    source_block_id=block.block_id,
                    source_span=block.text,
                    confidence=0.95 if entity else 0.86,
                    status="confirmed",
                )
            )
        return facts

    def _extract_from_text(self, document: DocumentRecord, block: DocumentBlock) -> list[FactRecord]:
        """从自由文本段落或标题中抽取事实。
        Extract facts from free-form paragraph or heading text.
        """
        content = block.text
        if not content:
            return []

        entity_positions = self._find_entity_positions(content, block.section_path)
        year = infer_year(content) or infer_year(document.file_name)
        facts: list[FactRecord] = []

        for canonical_name, aliases in FIELD_ALIASES.items():
            alias_candidates = sorted({canonical_name, *aliases}, key=len, reverse=True)
            for alias in alias_candidates:
                for match in re.finditer(re.escape(alias), content, flags=re.IGNORECASE):
                    raw_value, unit = self._find_numeric_near_alias(content, match.start(), match.end())
                    if raw_value is None:
                        continue
                    entity_name = self._resolve_nearest_entity(entity_positions, match.start())
                    if not entity_name and FIELD_ENTITY_TYPES.get(canonical_name) == "city":
                        continue
                    final_num, final_unit = convert_to_canonical_unit(canonical_name, raw_value, unit)
                    confidence = 0.88 if entity_name else 0.72
                    facts.append(
                        FactRecord(
                            fact_id=new_id("fact"),
                            entity_type=FIELD_ENTITY_TYPES.get(canonical_name, "generic"),
                            entity_name=entity_name or document.file_name,
                            field_name=canonical_name,
                            value_num=final_num,
                            value_text=content[max(0, match.start() - 24) : min(len(content), match.end() + 24)].strip(),
                            unit=final_unit,
                            year=year,
                            source_doc_id=document.doc_id,
                            source_block_id=block.block_id,
                            source_span=content,
                            confidence=confidence,
                            status="confirmed" if confidence >= 0.8 else "pending_review",
                        )
                    )
        return facts

    def _deduplicate(self, facts: list[FactRecord]) -> OrderedDict[tuple[str, str, str, str], FactRecord]:
        """合并重复事实并保留最高置信度版本。
        Collapse duplicate facts while keeping the highest-confidence copy.
        """
        deduplicated: OrderedDict[tuple[str, str, str, str], FactRecord] = OrderedDict()
        for fact in facts:
            key = (
                fact.entity_name,
                fact.field_name,
                fact.value_text,
                fact.source_block_id,
            )
            existing = deduplicated.get(key)
            if existing is None or fact.confidence > existing.confidence:
                deduplicated[key] = replace(fact)
        return deduplicated

    def _find_entity_positions(self, text: str, section_path: list[str]) -> list[tuple[int, str]]:
        """定位文本中的候选实体及其位置。
        Locate candidate entity mentions and their positions inside text.
        """
        found: list[tuple[int, str]] = []
        seen: set[str] = set()
        for entity_name in find_entity_mentions(text, section_path):
            position = text.find(entity_name)
            if position >= 0 and entity_name not in seen:
                found.append((position, entity_name))
                seen.add(entity_name)
        for section in section_path:
            normalized = normalize_entity_name(section)
            if normalized and normalized not in seen and normalized in text:
                found.append((text.find(normalized), normalized))
                seen.add(normalized)
        return sorted(found, key=lambda item: item[0])

    def _resolve_nearest_entity(self, positions: list[tuple[int, str]], anchor: int) -> str | None:
        """选择距离字段别名最近的实体提及。
        Choose the entity mention closest to a field alias occurrence.
        """
        if not positions:
            return None
        best_position, best_name = min(positions, key=lambda item: abs(item[0] - anchor))
        if best_position > anchor and len(positions) > 1:
            previous_entities = [item for item in positions if item[0] <= anchor]
            if previous_entities:
                return previous_entities[-1][1]
        return best_name

    def _find_numeric_near_alias(self, text: str, start: int, end: int) -> tuple[float | None, str | None]:
        """查找字段别名附近最近的数值表达。
        Find the closest numeric expression around a detected field alias.
        """
        window_start = max(0, start - 32)
        window_end = min(len(text), end + 32)
        window = text[window_start:window_end]
        local_anchor = start - window_start
        matches = list(_GENERIC_NUMBER_RE.finditer(window))
        if not matches:
            return None, None
        nearest = min(matches, key=lambda item: abs(item.start() - local_anchor))
        if nearest.group("value") is None:
            return None, None
        return float(nearest.group("value").replace(",", "")), nearest.group("unit")

    def _extract_unit_from_header(self, header: str) -> str | None:
        """从表头中读取单位提示。
        Read a unit hint from a table header if one is present.
        """
        match = _BRACKET_UNIT_RE.search(header)
        if not match:
            return None
        return match.group(1).strip()

    def _fallback_entity_from_text(self, text: str) -> str:
        """回退到文本片段中首个检测到的实体。
        Fallback to the first detected entity mention in a text snippet.
        """
        entities = find_entity_mentions(text)
        return entities[0] if entities else ""
