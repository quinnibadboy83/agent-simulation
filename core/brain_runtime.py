from __future__ import annotations

from typing import Any, Dict, List, Optional

from .model_runtime import (
    ModelRequest,
    ModelResponse,
    ModelRuntime,
    ModelRuntimeError,
)


class BrainRuntimeError(Exception):
    """Raised when the brain runtime bridge fails."""


class BrainRuntime:
    """
    Runtime bridge for AutonomousBrain.

    This module provides the transition between the existing
    LLMClient-based brain and the new provider-independent
    ModelRuntime architecture.

    Current architecture:

        AutonomousBrain
              |
              +---- existing LLMClient
              |
              +---- BrainRuntime
                         |
                         v
                    ModelRuntime

    The bridge deliberately does not remove LLMClient.

    That allows the engine to migrate gradually without breaking
    the current working brain.

    The long-term architecture is:

        AutonomousBrain
              |
              v
        ModelRuntime
              |
              +-- llama.cpp
              +-- local desktop runtime
              +-- Android runtime
              +-- other local runtimes
              +-- future runtimes
    """

    def __init__(
        self,
        runtime: Optional[ModelRuntime] = None,
        legacy_llm: Any = None,
    ):
        self.runtime = runtime
        self.legacy_llm = legacy_llm

    @property
    def using_runtime(self) -> bool:
        """
        Return True when a ModelRuntime has been supplied.
        """
        return self.runtime is not None

    @property
    def using_legacy_llm(self) -> bool:
        """
        Return True when the existing LLMClient is being used.
        """
        return self.legacy_llm is not None

    async def generate(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: float = 0.2,
        max_tokens: int = 1024,
    ) -> ModelResponse:
        """
        Generate a response through ModelRuntime.

        If no ModelRuntime is configured, the bridge falls back to
        the existing LLMClient.

        This fallback is temporary and exists to preserve backwards
        compatibility during the migration.
        """

        if self.runtime is not None:
            request = ModelRequest(
                messages=messages,
                tools=tools or [],
                temperature=temperature,
                max_tokens=max_tokens,
            )

            try:
                response = await self.runtime.generate(
                    request
                )

            except ModelRuntimeError:
                raise

            except Exception as exc:
                raise BrainRuntimeError(
                    f"Model runtime generation failed: {exc}"
                ) from exc

            return self._normalise_runtime_response(
                response
            )

        if self.legacy_llm is not None:
            return await self._generate_legacy(
                messages=messages,
                tools=tools,
                temperature=temperature,
                max_tokens=max_tokens,
            )

        raise BrainRuntimeError(
            "No model runtime or legacy LLMClient is configured."
        )

    async def health(self) -> bool:
        """
        Check whether the configured runtime is available.
        """

        if self.runtime is not None:
            try:
                health_method = getattr(
                    self.runtime,
                    "health",
                    None,
                )

                if not callable(
                    health_method
                ):
                    return False

                result = await health_method()

                if isinstance(
                    result,
                    bool,
                ):
                    return result

                available = getattr(
                    result,
                    "available",
                    None,
                )

                if available is not None:
                    return bool(
                        available
                    )

                return False

            except Exception:
                return False

        if self.legacy_llm is not None:
            health_method = getattr(
                self.legacy_llm,
                "health_check",
                None,
            )

            if callable(
                health_method
            ):
                try:
                    result = health_method()

                    if hasattr(
                        result,
                        "__await__",
                    ):
                        result = await result

                    return bool(
                        result
                    )

                except Exception:
                    return False

            config = getattr(
                self.legacy_llm,
                "config",
                None,
            )

            return bool(
                getattr(
                    config,
                    "enabled",
                    False,
                )
            )

        return False

    def describe(self) -> Dict[str, Any]:
        """
        Return a JSON-safe description of the active runtime.
        """

        if self.runtime is not None:
            describe_method = getattr(
                self.runtime,
                "describe",
                None,
            )

            if callable(
                describe_method
            ):
                try:
                    info = describe_method()

                    if hasattr(
                        info,
                        "to_dict",
                    ):
                        return info.to_dict()

                    if isinstance(
                        info,
                        dict,
                    ):
                        return dict(
                            info
                        )

                except Exception as exc:
                    return {
                        "runtime": "unknown",
                        "available": False,
                        "error": str(exc),
                    }

            return {
                "runtime": (
                    getattr(
                        self.runtime,
                        "name",
                        "unknown",
                    )
                ),
                "available": False,
                "error": (
                    "Runtime does not provide describe()."
                ),
            }

        if self.legacy_llm is not None:
            config = getattr(
                self.legacy_llm,
                "config",
                None,
            )

            return {
                "runtime": "legacy_llm_client",
                "provider": getattr(
                    config,
                    "provider",
                    "unknown",
                ),
                "model": getattr(
                    config,
                    "model",
                    "unknown",
                ),
                "available": bool(
                    getattr(
                        config,
                        "enabled",
                        False,
                    )
                ),
                "metadata": {
                    "compatibility_mode": True,
                    "legacy_client": "LLMClient",
                },
            }

        return {
            "runtime": "none",
            "available": False,
        }

    async def close(self) -> None:
        """
        Close the active runtime when supported.
        """

        if self.runtime is not None:
            close_method = getattr(
                self.runtime,
                "close",
                None,
            )

            if callable(
                close_method
            ):
                result = close_method()

                if hasattr(
                    result,
                    "__await__",
                ):
                    await result

        if self.legacy_llm is not None:
            close_method = getattr(
                self.legacy_llm,
                "close",
                None,
            )

            if callable(
                close_method
            ):
                result = close_method()

                if hasattr(
                    result,
                    "__await__",
                ):
                    await result

    async def _generate_legacy(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]],
        temperature: float,
        max_tokens: int,
    ) -> ModelResponse:
        """
        Adapt the existing LLMClient into ModelResponse.

        This is deliberately isolated here so the rest of the
        application can eventually stop knowing about LLMClient.
        """

        try:
            response = await self.legacy_llm.chat(
                messages=messages,
                tools=tools or [],
                temperature=temperature,
                max_tokens=max_tokens,
            )

        except Exception as exc:
            raise BrainRuntimeError(
                f"Legacy LLMClient generation failed: {exc}"
            ) from exc

        extract_text = getattr(
            self.legacy_llm,
            "extract_text",
            None,
        )

        extract_tool_calls = getattr(
            self.legacy_llm,
            "extract_tool_calls",
            None,
        )

        if callable(
            extract_text
        ):
            content = (
                extract_text(
                    response
                )
                or ""
            )
        else:
            content = ""

        if callable(
            extract_tool_calls
        ):
            tool_calls = (
                extract_tool_calls(
                    response
                )
                or []
            )
        else:
            tool_calls = []

        reasoning_content = (
            self._extract_reasoning(
                response
            )
        )

        usage = {}

        if isinstance(
            response,
            dict,
        ):
            raw_usage = response.get(
                "usage",
                {},
            )

            if isinstance(
                raw_usage,
                dict,
            ):
                usage = raw_usage

        return ModelResponse(
            content=str(
                content
                or ""
            ),
            reasoning_content=str(
                reasoning_content
                or ""
            ),
            tool_calls=tool_calls,
            usage=usage,
            raw_response=(
                response
                if isinstance(
                    response,
                    dict,
                )
                else {}
            ),
            metadata={
                "runtime_mode": "legacy_llm_client",
            },
        )

    @staticmethod
    def _normalise_runtime_response(
        response: Any,
    ) -> ModelResponse:
        """
        Ensure a runtime response conforms to ModelResponse.

        This also protects the brain from small differences between
        future runtime implementations.
        """

        if isinstance(
            response,
            ModelResponse,
        ):
            return response

        if isinstance(
            response,
            dict,
        ):
            return ModelResponse(
                content=str(
                    response.get(
                        "content",
                        response.get(
                            "text",
                            "",
                        ),
                    )
                    or ""
                ),
                reasoning_content=str(
                    response.get(
                        "reasoning_content",
                        response.get(
                            "reasoning",
                            "",
                        ),
                    )
                    or ""
                ),
                tool_calls=(
                    response.get(
                        "tool_calls",
                        [],
                    )
                    or []
                ),
                finish_reason=response.get(
                    "finish_reason"
                ),
                model=response.get(
                    "model"
                ),
                usage=(
                    response.get(
                        "usage",
                        {},
                    )
                    or {}
                ),
                raw_response=(
                    response.get(
                        "raw_response",
                        response,
                    )
                    or {}
                ),
                metadata=(
                    response.get(
                        "metadata",
                        {},
                    )
                    or {}
                ),
            )

        raise BrainRuntimeError(
            "Model runtime returned an unsupported response type."
        )

    @staticmethod
    def _extract_reasoning(
        response: Any,
    ) -> str:
        """
        Extract reasoning content from an OpenAI-compatible response.
        """

        if not isinstance(
            response,
            dict,
        ):
            return ""

        choices = response.get(
            "choices"
        )

        if not isinstance(
            choices,
            list,
        ) or not choices:
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

        reasoning = (
            message.get(
                "reasoning_content"
            )
            or message.get(
                "reasoning"
            )
            or ""
        )

        return str(
            reasoning
            or ""
        ).strip()