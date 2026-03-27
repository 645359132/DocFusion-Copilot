from __future__ import annotations

import re

from app.core.catalog import FIELD_ALIASES, INTENT_KEYWORDS
from app.core.openai_client import OpenAIClientError, OpenAICompatibleClient
from app.repositories.base import Repository
from app.utils.normalizers import find_entity_mentions

_REPLACE_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"[将把](?P<old>.+?)(?:替换为|改为|改成)(?P<new>.+)"),
    re.compile(r"把文中(?P<old>.+?)(?:替换为|改为|改成)(?P<new>.+)"),
)
_TRAILING_PUNCTUATION = "。！？!?，,；;：:"
_QUOTE_CHARS = "\"'“”‘’《》「」『』"


class AgentService:
    """面向 MVP 自然语言接口的规则式规划服务。    Rule-based planner for the MVP natural-language endpoint."""

    def __init__(self, repository: Repository, openai_client: OpenAICompatibleClient) -> None:
        """绑定共享仓储依赖。    Bind the service to the shared repository."""

        self._repository = repository
        self._openai_client = openai_client

    def chat(self, message: str, context_id: str | None = None) -> dict[str, object]:
        """将用户消息转换为轻量意图与预览结果。    Turn a user message into a lightweight intent and preview payload."""

        plan = self._plan_message(message)
        intent = str(plan["intent"])
        fields = [str(field) for field in plan.get("fields", [])]
        entities = [str(entity) for entity in plan.get("entities", [])]
        edits = self._normalize_edits(plan.get("edits", []))
        preview_facts = self._preview_facts(fields, entities)
        return {
            "intent": intent,
            "entities": entities or (["城市"] if "城市" in message else []),
            "fields": fields,
            "target": str(
                plan.get("target")
                or ("uploaded_template" if intent == "extract_and_fill_template" else "fact_store")
            ),
            "need_db_store": bool(plan.get("need_db_store", intent in {"extract_and_fill_template", "extract_facts"})),
            "context_id": context_id,
            "preview": preview_facts,
            "edits": edits,
            "planner": "openai" if plan.get("planner") == "openai" else "rules",
        }

    def _plan_message(self, message: str) -> dict[str, object]:
        """为自然语言消息生成结构化执行计划。    Generate a structured execution plan for a natural-language message."""

        if self._openai_client.is_configured:
            try:
                return self._plan_with_openai(message)
            except OpenAIClientError:
                pass
        return self._fallback_plan(message)

    def _plan_with_openai(self, message: str) -> dict[str, object]:
        """使用 OpenAI 兼容接口生成结构化计划。    Generate a structured plan using an OpenAI-compatible API."""

        payload = self._openai_client.create_json_completion(
            system_prompt=(
                "你是 DocFusion 后端的指令规划器。"
                "请把用户消息转换成稳定、简洁、可执行的 JSON 计划。"
                "intent 只能从以下值中选择："
                "extract_facts, query_facts, extract_and_fill_template, trace_fact, edit_document, summarize_document, reformat_document。"
            ),
            user_prompt=f"用户消息：{message}",
            json_schema={
                "type": "object",
                "properties": {
                    "intent": {"type": "string"},
                    "entities": {"type": "array", "items": {"type": "string"}},
                    "fields": {"type": "array", "items": {"type": "string"}},
                    "target": {"type": "string"},
                    "need_db_store": {"type": "boolean"},
                    "edits": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "old_text": {"type": "string"},
                                "new_text": {"type": "string"},
                            },
                            "required": ["old_text", "new_text"],
                            "additionalProperties": False,
                        },
                    },
                },
                "required": ["intent", "entities", "fields", "target", "need_db_store", "edits"],
                "additionalProperties": False,
            },
        )
        payload["planner"] = "openai"
        return payload

    def _infer_intent(self, message: str) -> str:
        """根据关键词规则推断最匹配的意图。    Infer the best-matching intent from keyword rules."""

        edits = self._infer_edits(message)
        if edits:
            return "edit_document"

        lowered = message.lower()
        for intent, keywords in INTENT_KEYWORDS.items():
            if any(keyword in lowered or keyword in message for keyword in keywords):
                return intent
        if any(keyword in message for keyword in ("摘要", "总结", "概述")):
            return "summarize_document"
        if any(keyword in message for keyword in ("排版", "格式", "整理", "规范", "重排", "清理")):
            return "reformat_document"
        return "query_facts"

    def _fallback_plan(self, message: str) -> dict[str, object]:
        """使用本地规则生成执行计划。    Generate an execution plan using local rules."""

        intent = self._infer_intent(message)
        return {
            "intent": intent,
            "entities": find_entity_mentions(message),
            "fields": self._infer_fields(message),
            "target": "uploaded_template" if intent == "extract_and_fill_template" else "fact_store",
            "need_db_store": intent in {"extract_and_fill_template", "extract_facts"},
            "edits": self._infer_edits(message),
            "planner": "rules",
        }

    def _infer_fields(self, message: str) -> list[str]:
        """识别消息中提到的业务字段。    Detect requested business fields mentioned in the message."""

        lowered = message.lower()
        fields: list[str] = []
        for canonical_name, aliases in FIELD_ALIASES.items():
            candidates = {canonical_name, *aliases}
            if any(candidate.lower() in lowered or candidate in message for candidate in candidates):
                fields.append(canonical_name)
        return fields

    def _infer_edits(self, message: str) -> list[dict[str, str]]:
        """从消息中提取简单文本替换指令。    Extract simple text-replacement edits from the message."""

        edits: list[dict[str, str]] = []
        for pattern in _REPLACE_PATTERNS:
            match = pattern.search(message)
            if not match:
                continue
            old_text = self._clean_edit_text(match.group("old"))
            new_text = self._clean_edit_text(match.group("new"))
            if old_text and new_text and old_text != new_text:
                edits.append({"old_text": old_text, "new_text": new_text})
        return edits

    def _clean_edit_text(self, value: str) -> str:
        """清理替换指令中的引号和尾部标点。    Clean quotes and trailing punctuation from edit text."""

        cleaned = value.strip().strip(_QUOTE_CHARS).strip()
        while cleaned and cleaned[-1] in _TRAILING_PUNCTUATION:
            cleaned = cleaned[:-1].rstrip()
        return cleaned.strip(_QUOTE_CHARS).strip()

    def _normalize_edits(self, raw_edits: object) -> list[dict[str, str]]:
        """把计划中的编辑描述标准化为替换对。    Normalize edit descriptions from a plan into replacement pairs."""

        normalized: list[dict[str, str]] = []
        if not isinstance(raw_edits, list):
            return normalized
        for item in raw_edits:
            if not isinstance(item, dict):
                continue
            old_text = self._clean_edit_text(str(item.get("old_text", "")))
            new_text = self._clean_edit_text(str(item.get("new_text", "")))
            if old_text and new_text and old_text != new_text:
                normalized.append({"old_text": old_text, "new_text": new_text})
        return normalized

    def _preview_facts(self, fields: list[str], entities: list[str]) -> list[dict[str, object]]:
        """返回与请求匹配的 canonical 事实预览。    Return a small preview of matching canonical facts for the request."""

        preview: list[dict[str, object]] = []
        source_entities = [entity for entity in entities if entity != "城市"] or [None]
        source_fields = fields or [None]
        for entity_name in source_entities:
            for field_name in source_fields:
                facts = self._repository.list_facts(
                    entity_name=entity_name,
                    field_name=field_name,
                    canonical_only=True,
                )
                for fact in facts[:5]:
                    preview.append(
                        {
                            "fact_id": fact.fact_id,
                            "entity_name": fact.entity_name,
                            "field_name": fact.field_name,
                            "value_num": fact.value_num,
                            "value_text": fact.value_text,
                            "unit": fact.unit,
                            "year": fact.year,
                            "confidence": fact.confidence,
                        }
                    )
        return preview[:10]
