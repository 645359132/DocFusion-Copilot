from __future__ import annotations

from app.core.catalog import FIELD_ALIASES, INTENT_KEYWORDS
from app.repositories.memory import InMemoryRepository
from app.utils.normalizers import find_entity_mentions


class AgentService:
    """面向 MVP 自然语言接口的规则式规划服务。
    Rule-based planner for the MVP natural-language endpoint.
    """

    def __init__(self, repository: InMemoryRepository) -> None:
        """绑定共享仓储依赖。
        Bind the service to the shared repository.
        """
        self._repository = repository

    def chat(self, message: str, context_id: str | None = None) -> dict[str, object]:
        """将用户消息转换为轻量意图与预览结果。
        Turn a user message into a lightweight intent and preview payload.
        """
        intent = self._infer_intent(message)
        fields = self._infer_fields(message)
        entities = find_entity_mentions(message)
        preview_facts = self._preview_facts(fields, entities)
        return {
            "intent": intent,
            "entities": entities or (["城市"] if "城市" in message else []),
            "fields": fields,
            "target": "uploaded_template" if intent == "extract_and_fill_template" else "fact_store",
            "need_db_store": intent in {"extract_and_fill_template", "extract_facts"},
            "context_id": context_id,
            "preview": preview_facts,
        }

    def _infer_intent(self, message: str) -> str:
        """根据关键词规则推断最匹配的意图。
        Infer the best-matching intent from keyword rules.
        """
        lowered = message.lower()
        for intent, keywords in INTENT_KEYWORDS.items():
            if any(keyword in lowered or keyword in message for keyword in keywords):
                return intent
        return "query_facts"

    def _infer_fields(self, message: str) -> list[str]:
        """识别消息中提到的业务字段。
        Detect requested business fields mentioned in the message.
        """
        lowered = message.lower()
        fields: list[str] = []
        for canonical_name, aliases in FIELD_ALIASES.items():
            candidates = {canonical_name, *aliases}
            if any(candidate.lower() in lowered or candidate in message for candidate in candidates):
                fields.append(canonical_name)
        return fields

    def _preview_facts(self, fields: list[str], entities: list[str]) -> list[dict[str, object]]:
        """返回与请求匹配的 canonical 事实预览。
        Return a small preview of matching canonical facts for the request.
        """
        preview: list[dict[str, object]] = []
        source_entities = entities or [None]
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
