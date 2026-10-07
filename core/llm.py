from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

import httpx

from .brain_config import BrainConfig


class LLMError(Exception):
    """Raised when the configured language model cannot be used."""


class LLMClient:
    """
    Provider-independent asynchronous LLM client.

    Communicates with an OpenAI-compatible /chat/completions endpoint.

    Supported backends include:

        - llama.cpp / llama-server
        - Qwen GGUF models
        - Llama GGUF models
        - Gemma GGUF models
        - remote OpenAI-compatible inference servers
        - other compatible open-source model servers

    The client uses streaming for chat completions.

    Streaming is important when the model is exposed through a proxy
    such as Cloudflare because the proxy can otherwise terminate a
    long-running request before the model has finished generating.

    Model output does not receive application authority.

    ToolRegistry and ApprovalGate remain responsible for deciding
    whether requested actions can actually execute.
    """

    def __init__(
        self,
        config: Optional[BrainConfig] = None,
    ):
        self.config = (
            config
            if config is not None
            else BrainConfig.from_environment()
        )

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
        Send a streaming chat completion request.

        The complete streamed response is reconstructed into the normal
        OpenAI-compatible response format before being returned.

        This means the rest of the agent architecture does not need to
        know whether the underlying model response was streamed.

        Tool definitions remain available to the model.

        A requested tool is NOT automatically authorised.

        ToolRegistry and ApprovalGate remain responsible for execution.
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
            "stream": True,
        }

        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"

        try:
            return await self._stream_chat(
                payload
            )

        except LLMError:
            raise

        except httpx.TimeoutException as exc:
            raise LLMError(
                "LLM streaming request timed out after "
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

    async def _stream_chat(
        self,
        payload: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Consume an OpenAI-compatible Server-Sent Events stream.

        The method reconstructs the final response into the same shape
        expected by AutonomousBrain.
        """

        content_parts: List[str] = []
        reasoning_parts: List[str] = []

        tool_calls: Dict[int, Dict[str, Any]] = {}

        finish_reason: Optional[str] = None
        response_id: Optional[str] = None
        response_model: Optional[str] = None

        usage: Dict[str, Any] = {}

        received_data = False

        timeout = httpx.Timeout(
            timeout=self.config.timeout,
            connect=min(
                float(self.config.timeout),
                30.0,
            ),
            read=float(self.config.timeout),
            write=min(
                float(self.config.timeout),
                30.0,
            ),
            pool=min(
                float(self.config.timeout),
                30.0,
            ),
        )

        async with httpx.AsyncClient(
            timeout=timeout
        ) as client:

            async with client.stream(
                "POST",
                self.endpoint(),
                headers=self._headers(
                    streaming=True
                ),
                json=payload,
            ) as response:

                if response.status_code >= 400:
                    body = await response.aread()

                    try:
                        body_text = body.decode(
                            "utf-8",
                            errors="replace",
                        )
                    except Exception:
                        body_text = str(body)

                    raise LLMError(
                        "LLM server returned HTTP "
                        f"{response.status_code}: "
                        f"{body_text[:4000]}"
                    )

                async for line in response.aiter_lines():

                    if not line:
                        continue

                    line = line.strip()

                    if not line:
                        continue

                    if line.startswith(":"):
                        # SSE comment/keep-alive.
                        continue

                    if not line.startswith(
                        "data:"
                    ):
                        continue

                    raw_data = line[
                        len("data:"):
                    ].strip()

                    if not raw_data:
                        continue

                    if raw_data == "[DONE]":
                        break

                    received_data = True

                    try:
                        chunk = json.loads(
                            raw_data
                        )
                    except (
                        TypeError,
                        ValueError,
                        json.JSONDecodeError,
                    ):
                        # Ignore malformed SSE fragments rather than
                        # destroying an otherwise valid streamed result.
                        continue

                    if not isinstance(
                        chunk,
                        dict,
                    ):
                        continue

                    if response_id is None:
                        value = chunk.get("id")

                        if value is not None:
                            response_id = str(value)

                    if response_model is None:
                        value = chunk.get("model")

                        if value is not None:
                            response_model = str(
                                value
                            )

                    chunk_usage = chunk.get(
                        "usage"
                    )

                    if isinstance(
                        chunk_usage,
                        dict,
                    ):
                        usage.update(
                            chunk_usage
                        )

                    choices = chunk.get(
                        "choices"
                    )

                    if not isinstance(
                        choices,
                        list,
                    ):
                        continue

                    for choice in choices:

                        if not isinstance(
                            choice,
                            dict,
                        ):
                            continue

                        reason = choice.get(
                            "finish_reason"
                        )

                        if reason is not None:
                            finish_reason = str(
                                reason
                            )

                        delta = choice.get(
                            "delta"
                        )

                        if not isinstance(
                            delta,
                            dict,
                        ):
                            continue

                        # --------------------------------------------------
                        # Normal assistant content
                        # --------------------------------------------------

                        delta_content = delta.get(
                            "content"
                        )

                        if isinstance(
                            delta_content,
                            str,
                        ):
                            content_parts.append(
                                delta_content
                            )

                        # --------------------------------------------------
                        # Qwen reasoning content
                        # --------------------------------------------------

                        delta_reasoning = (
                            delta.get(
                                "reasoning_content"
                            )
                        )

                        if isinstance(
                            delta_reasoning,
                            str,
                        ):
                            reasoning_parts.append(
                                delta_reasoning
                            )

                        # Some OpenAI-compatible servers use "reasoning".
                        delta_reasoning_alt = (
                            delta.get(
                                "reasoning"
                            )
                        )

                        if isinstance(
                            delta_reasoning_alt,
                            str,
                        ):
                            reasoning_parts.append(
                                delta_reasoning_alt
                            )

                        # --------------------------------------------------
                        # Tool calls
                        # --------------------------------------------------

                        delta_tool_calls = (
                            delta.get(
                                "tool_calls"
                            )
                        )

                        if not isinstance(
                            delta_tool_calls,
                            list,
                        ):
                            continue

                        for tool_delta in (
                            delta_tool_calls
                        ):
                            self._merge_tool_delta(
                                tool_calls,
                                tool_delta,
                            )

        if not received_data:
            raise LLMError(
                "LLM server returned an empty streaming response."
            )

        reconstructed_tool_calls = (
            self._finalise_tool_calls(
                tool_calls
            )
        )

        message: Dict[str, Any] = {
            "role": "assistant",
            "content": (
                "".join(content_parts)
                if content_parts
                else None
            ),
        }

        if reasoning_parts:
            message[
                "reasoning_content"
            ] = "".join(
                reasoning_parts
            )

        if reconstructed_tool_calls:
            message[
                "tool_calls"
            ] = reconstructed_tool_calls

        result: Dict[str, Any] = {
            "id": (
                response_id
                or "llama-stream"
            ),
            "object": "chat.completion",
            "model": (
                response_model
                or self.config.model
            ),
            "choices": [
                {
                    "index": 0,
                    "message": message,
                    "finish_reason": (
                        finish_reason
                        or "stop"
                    ),
                }
            ],
        }

        if usage:
            result["usage"] = usage

        return result

    @staticmethod
    def _merge_tool_delta(
        tool_calls: Dict[int, Dict[str, Any]],
        tool_delta: Any,
    ) -> None:
        """
        Merge one streamed tool-call delta into the accumulated
        tool-call structure.
        """

        if not isinstance(
            tool_delta,
            dict,
        ):
            return

        index_value = tool_delta.get(
            "index",
            0,
        )

        try:
            index = int(
                index_value
            )
        except (
            TypeError,
            ValueError,
        ):
            index = 0

        existing = tool_calls.get(
            index
        )

        if existing is None:
            existing = {
                "id": "",
                "type": "function",
                "function": {
                    "name": "",
                    "arguments": "",
                },
            }

            tool_calls[index] = existing

        call_id = tool_delta.get(
            "id"
        )

        if isinstance(
            call_id,
            str,
        ):
            existing["id"] += call_id

        call_type = tool_delta.get(
            "type"
        )

        if isinstance(
            call_type,
            str,
        ):
            existing["type"] = call_type

        function_delta = tool_delta.get(
            "function"
        )

        if not isinstance(
            function_delta,
            dict,
        ):
            return

        function = existing[
            "function"
        ]

        function_name = (
            function_delta.get(
                "name"
            )
        )

        if isinstance(
            function_name,
            str,
        ):
            function["name"] += function_name

        arguments = (
            function_delta.get(
                "arguments"
            )
        )

        if isinstance(
            arguments,
            str,
        ):
            function["arguments"] += arguments

    @staticmethod
    def _finalise_tool_calls(
        tool_calls: Dict[int, Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        Convert accumulated streamed tool calls into normal
        OpenAI-compatible tool-call objects.
        """

        output: List[Dict[str, Any]] = []

        for index in sorted(
            tool_calls.keys()
        ):
            call = tool_calls[index]

            function = call.get(
                "function"
            )

            if not isinstance(
                function,
                dict,
            ):
                function = {}

            output.append(
                {
                    "id": (
                        call.get("id")
                        or f"call_{index}"
                    ),
                    "type": (
                        call.get("type")
                        or "function"
                    ),
                    "function": {
                        "name": (
                            function.get(
                                "name"
                            )
                            or ""
                        ),
                        "arguments": (
                            function.get(
                                "arguments"
                            )
                            or ""
                        ),
                    },
                }
            )

        return output

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

        return self.extract_text(
            result
        )

    @staticmethod
    def extract_text(
        response: Dict[str, Any],
    ) -> str:
        """
        Extract assistant text from an OpenAI-compatible response.
        """

        choices = response.get(
            "choices"
        )

        if not isinstance(
            choices,
            list,
        ):
            return ""

        if not choices:
            return ""

        first = choices[0]

        if not isinstance(
            first,
            dict,
        ):
            return ""

        message = first.get(
            "message"
        )

        if not isinstance(
            message,
            dict,
        ):
            return ""

        content = message.get(
            "content"
        )

        if content is None:
            return ""

        if isinstance(
            content,
            str,
        ):
            return content

        if isinstance(
            content,
            list,
        ):
            parts: List[str] = []

            for item in content:

                if isinstance(
                    item,
                    str,
                ):
                    parts.append(
                        item
                    )
                    continue

                if not isinstance(
                    item,
                    dict,
                ):
                    continue

                text = item.get(
                    "text"
                )

                if isinstance(
                    text,
                    str,
                ):
                    parts.append(
                        text
                    )

            return "".join(
                parts
            )

        return str(
            content
        )

    @staticmethod
    def extract_tool_calls(
        response: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """
        Extract model-requested tool calls.
        """

        choices = response.get(
            "choices"
        )

        if not isinstance(
            choices,
            list,
        ):
            return []

        if not choices:
            return []

        first = choices[0]

        if not isinstance(
            first,
            dict,
        ):
            return []

        message = first.get(
            "message"
        )

        if not isinstance(
            message,
            dict,
        ):
            return []

        tool_calls = message.get(
            "tool_calls"
        )

        if not isinstance(
            tool_calls,
            list,
        ):
            return []

        return [
            call
            for call in tool_calls
            if isinstance(
                call,
                dict,
            )
        ]

    @staticmethod
    def extract_finish_reason(
        response: Dict[str, Any],
    ) -> Optional[str]:
        """
        Extract the provider's finish reason when available.
        """

        choices = response.get(
            "choices"
        )

        if not isinstance(
            choices,
            list,
        ):
            return None

        if not choices:
            return None

        first = choices[0]

        if not isinstance(
            first,
            dict,
        ):
            return None

        value = first.get(
            "finish_reason"
        )

        if value is None:
            return None

        return str(
            value
        )

    @staticmethod
    def extract_usage(
        response: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Extract token usage information when supplied by the provider.
        """

        usage = response.get(
            "usage"
        )

        if not isinstance(
            usage,
            dict,
        ):
            return {}

        return usage

    def _headers(
        self,
        streaming: bool = False,
    ) -> Dict[str, str]:
        """
        Build HTTP headers.

        Local llama.cpp servers normally do not require authentication.

        Remote providers may require a bearer token.
        """

        headers: Dict[str, str] = {
            "Content-Type": "application/json",
            "Accept": (
                "text/event-stream"
                if streaming
                else "application/json"
            ),
            "Cache-Control": "no-cache",
        }

        api_key = (
            self.config.api_key or ""
        ).strip()

        if api_key:
            headers["Authorization"] = (
                f"Bearer {api_key}"
            )

        return headers
