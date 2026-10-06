from __future__ import annotations

from typing import Any, Dict, List, Optional

import httpx

from .brain_config import BrainConfig


class LLMError(Exception):
    """Raised when the configured language model cannot be used."""


class LLMClient:
    """
    Provider-independent asynchronous LLM client.

    The client communicates with an OpenAI-compatible /chat/completions
    endpoint.

    This allows the agent architecture to work with:

        - llama.cpp / llama-server
        - Qwen GGUF models
        - Llama GGUF models
        - Gemma GGUF models
        - remote OpenAI-compatible inference servers
        - other compatible open-source model servers

    The LLM itself does not receive authority to bypass application
    security.

    Model output becomes a requested action.

    ToolRegistry and ApprovalGate decide whether that action can actually
    execute.
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

    def models_endpoint(self) -> str:
        return (
            f"{self.config.base_url}"
            "/models"
        )

    async def health(self) -> Dict[str, Any]:
        """
        Check whether the configured model server is reachable.
        """

        if not self.config.enabled:
            return {
                "status": "disabled",
                "provider": self.config.provider,
                "model": self.config.model,
            }

        try:
            async with httpx.AsyncClient(
                timeout=self.config.timeout
            ) as client:
                response = await client.get(
                    self.models_endpoint(),
                    headers=self._headers(),
                )

            response.raise_for_status()

            try:
                data = response.json()
            except ValueError:
                data = {
                    "raw_response": response.text[:2000]
                }

            return {
                "status": "ready",
                "provider": self.config.provider,
                "model": self.config.model,
                "server": data,
            }

        except httpx.TimeoutException:
            return {
                "status": "unavailable",
                "provider": self.config.provider,
                "model": self.config.model,
                "error": (
                    f"Model server timed out after "
                    f"{self.config.timeout} seconds."
                ),
            }

        except httpx.HTTPError as exc:
            return {
                "status": "unavailable",
                "provider": self.config.provider,
                "model": self.config.model,
                "error": str(exc),
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
        """
        Send a chat completion request.

        Tool definitions are supplied to the model as capabilities.

        IMPORTANT:

        A model requesting a tool does NOT mean that the tool is
        automatically permitted to execute.

        The returned tool call must pass through the application's
        ToolRegistry and, where necessary, Creator ApprovalGate.
        """

        if not self.config.enabled:
            raise LLMError(
                "LLM brain is disabled. "
                "Set BRAIN_ENABLED=true and configure "
                "BRAIN_BASE_URL and BRAIN_MODEL."
            )

        if not messages:
            raise LLMError(
                "Cannot send an empty message list to the LLM."
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
                    "LLM server returned HTTP "
                    f"{response.status_code}: "
                    f"{response.text[:4000]}"
                )

            try:
                data = response.json()
            except ValueError as exc:
                raise LLMError(
                    "LLM server returned invalid JSON."
                ) from exc

            if not isinstance(data, dict):
                raise LLMError(
                    "LLM server returned an invalid response object."
                )

            return data

        except LLMError:
            raise

        except httpx.TimeoutException as exc:
            raise LLMError(
                "LLM request timed out after "
                f"{self.config.timeout} seconds."
            ) from exc

        except httpx.HTTPError as exc:
            raise LLMError(
                f"LLM HTTP connection failed: {exc}"
            ) from exc

        except Exception as exc:
            raise LLMError(
                f"Unexpected LLM client error: {exc}"
            ) from exc

    async def simple_chat(
        self,
        system: str,
        user: str,
    ) -> str:
        """
        Convenience method for a normal text response.
        """

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
        """
        Extract assistant text from an OpenAI-compatible response.
        """

        choices = response.get("choices")

        if not isinstance(choices, list):
            return ""

        if not choices:
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

        # Some compatible providers return structured content.
        if isinstance(content, list):
            parts: List[str] = []

            for item in content:
                if isinstance(item, str):
                    parts.append(item)
                    continue

                if not isinstance(item, dict):
                    continue

                text = item.get("text")

                if isinstance(text, str):
                    parts.append(text)

            return "".join(parts)

        return str(content)

    @staticmethod
    def extract_tool_calls(
        response: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """
        Extract model-requested tool calls.
        """

        choices = response.get("choices")

        if not isinstance(choices, list):
            return []

        if not choices:
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

    @staticmethod
    def extract_finish_reason(
        response: Dict[str, Any],
    ) -> Optional[str]:
        """
        Extract the provider's finish reason when available.
        """

        choices = response.get("choices")

        if not isinstance(choices, list):
            return None

        if not choices:
            return None

        first = choices[0]

        if not isinstance(first, dict):
            return None

        value = first.get("finish_reason")

        if value is None:
            return None

        return str(value)

    @staticmethod
    def extract_usage(
        response: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Extract token usage information when supplied by the provider.
        """

        usage = response.get("usage")

        if not isinstance(usage, dict):
            return {}

        return usage

    def _headers(self) -> Dict[str, str]:
        """
        Build HTTP headers.

        Local llama.cpp servers normally do not require authentication.

        Remote providers may require a bearer token.
        """

        headers: Dict[str, str] = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        api_key = (
            self.config.api_key or ""
        ).strip()

        if api_key:
            headers["Authorization"] = (
                f"Bearer {api_key}"
            )

        return headers
