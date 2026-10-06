from __future__ import annotations

from typing import Any, Dict, List, Optional

import httpx

from .brain_config import BrainConfig


class LLMError(Exception):
    """Raised when the configured language model cannot be used."""


class LLMClient:
    """
    Model-independent LLM client.

    The initial implementation targets an OpenAI-compatible endpoint,
    which is provided by llama.cpp's llama-server.

    This means the agent system does not depend on a particular model.
    Qwen, another GGUF model, or a future stronger model can be placed
    behind the same interface.
    """

    def __init__(
        self,
        config: Optional[BrainConfig] = None,
    ):
        self.config = config or BrainConfig.from_environment()

    def is_enabled(self) -> bool:
        return bool(self.config.enabled)

    def endpoint(self) -> str:
        return (
            f"{self.config.base_url}"
            "/chat/completions"
        )

    async def health(self) -> Dict[str, Any]:
        if not self.config.enabled:
            return {
                "status": "disabled",
                "provider": self.config.provider,
                "model": self.config.model,
            }

        url = f"{self.config.base_url}/models"

        try:
            async with httpx.AsyncClient(
                timeout=self.config.timeout
            ) as client:
                response = await client.get(
                    url,
                    headers=self._headers(),
                )

            response.raise_for_status()

            data = response.json()

            return {
                "status": "ready",
                "provider": self.config.provider,
                "model": self.config.model,
                "server": data,
            }

        except Exception as exc:
            return {
                "status": "unavailable",
                "provider": self.config.provider,
                "model": self.config.model,
                "error": str(exc),
            }

    async def chat(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> Dict[str, Any]:

        if not self.config.enabled:
            raise LLMError(
                "LLM brain is disabled. "
                "Set BRAIN_ENABLED=true and configure the model server."
            )

        payload: Dict[str, Any] = {
            "model": self.config.model,
            "messages": messages,
            "temperature": (
                self.config.temperature
                if temperature is None
                else temperature
            ),
            "max_tokens": (
                self.config.max_tokens
                if max_tokens is None
                else max_tokens
            ),
        }

        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"

        try:
            async with httpx.AsyncClient(
                timeout=self.config.timeout
            ) as client:
                response = await client.post(
                    self.endpoint(),
                    headers=self._headers(),
                    json=payload,
                )

            if response.status_code >= 400:
                raise LLMError(
                    f"LLM server returned HTTP "
                    f"{response.status_code}: "
                    f"{response.text[:2000]}"
                )

            data = response.json()

            if not isinstance(data, dict):
                raise LLMError(
                    "LLM server returned an invalid response."
                )

            return data

        except httpx.TimeoutException as exc:
            raise LLMError(
                f"LLM request timed out after "
                f"{self.config.timeout} seconds."
            ) from exc

        except httpx.HTTPError as exc:
            raise LLMError(
                f"LLM HTTP connection failed: {exc}"
            ) from exc

    async def simple_chat(
        self,
        system: str,
        user: str,
    ) -> str:

        result = await self.chat(
            messages=[
                {
                    "role": "system",
                    "content": system,
                },
                {
                    "role": "user",
                    "content": user,
                },
            ]
        )

        return self.extract_text(result)

    @staticmethod
    def extract_text(
        response: Dict[str, Any],
    ) -> str:

        choices = response.get("choices")

        if not isinstance(choices, list) or not choices:
            return ""

        first = choices[0]

        if not isinstance(first, dict):
            return ""

        message = first.get("message")

        if not isinstance(message, dict):
            return ""

        content = message.get("content")

        if content is None:
            return ""

        if isinstance(content, str):
            return content

        return str(content)

    @staticmethod
    def extract_tool_calls(
        response: Dict[str, Any],
    ) -> List[Dict[str, Any]]:

        choices = response.get("choices")

        if not isinstance(choices, list) or not choices:
            return []

        first = choices[0]

        if not isinstance(first, dict):
            return []

        message = first.get("message")

        if not isinstance(message, dict):
            return []

        tool_calls = message.get("tool_calls")

        if not isinstance(tool_calls, list):
            return []

        return [
            call
            for call in tool_calls
            if isinstance(call, dict)
        ]

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": (
                f"Bearer {self.config.api_key}"
            ),
            "Content-Type": "application/json",
        }
