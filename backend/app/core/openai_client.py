from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any
from urllib import error, request


class OpenAIClientError(RuntimeError):
    """OpenAI 兼容接口调用异常。
    Error raised for OpenAI-compatible API failures.
    """


@dataclass(slots=True)
class OpenAICompatibleClient:
    """OpenAI 兼容聊天接口客户端模板。
    Template client for OpenAI-compatible chat APIs.
    """

    api_key: str
    base_url: str
    model: str
    timeout_seconds: float = 45.0

    @property
    def is_configured(self) -> bool:
        """返回当前客户端是否已具备可用配置。
        Return whether the client has enough configuration to run requests.
        """
        return bool(self.api_key and self.base_url and self.model)

    def create_json_completion(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        json_schema: dict[str, Any] | None = None,
        temperature: float = 0.0,
    ) -> dict[str, Any]:
        """调用 OpenAI 兼容接口并返回 JSON 结果。
        Call an OpenAI-compatible API and return a JSON result.
        """
        if not self.is_configured:
            raise OpenAIClientError(
                "OpenAI-compatible client is not configured. "
                "Fill DOCFUSION_OPENAI_API_KEY / DOCFUSION_OPENAI_BASE_URL / DOCFUSION_OPENAI_MODEL first."
            )

        payload: dict[str, Any] = {
            "model": self.model,
            "temperature": temperature,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }
        if json_schema is not None:
            payload["response_format"] = {
                "type": "json_schema",
                "json_schema": {
                    "name": "docfusion_response",
                    "schema": json_schema,
                },
            }

        raw_response = self._post_json("/chat/completions", payload)
        content = self._extract_message_content(raw_response)
        try:
            return json.loads(content)
        except json.JSONDecodeError as exc:
            raise OpenAIClientError(f"OpenAI-compatible API did not return valid JSON: {content}") from exc

    def _post_json(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        """向 OpenAI 兼容接口发送 JSON POST 请求。
        Send a JSON POST request to an OpenAI-compatible API.
        """
        url = self.base_url.rstrip("/") + path
        body = json.dumps(payload).encode("utf-8")
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        req = request.Request(url, data=body, headers=headers, method="POST")
        try:
            with request.urlopen(req, timeout=self.timeout_seconds) as response:
                return json.loads(response.read().decode("utf-8"))
        except error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise OpenAIClientError(f"OpenAI-compatible API HTTP {exc.code}: {detail}") from exc
        except error.URLError as exc:
            raise OpenAIClientError(f"OpenAI-compatible API connection failed: {exc}") from exc

    @staticmethod
    def _extract_message_content(payload: dict[str, Any]) -> str:
        """从聊天补全响应中提取首个消息文本。
        Extract the first message content from a chat-completions payload.
        """
        try:
            content = payload["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise OpenAIClientError(f"Unexpected OpenAI-compatible API response: {payload}") from exc

        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts: list[str] = []
            for item in content:
                if isinstance(item, dict) and item.get("type") == "text":
                    parts.append(str(item.get("text", "")))
            return "".join(parts)
        return str(content)
