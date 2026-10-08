from __future__ import annotations

from typing import Any, Dict, List, Optional

from .llm import (
    LLMClient,
    LLMError,
)

from .model_runtime import (
    ModelRequest,
    ModelResponse,
    ModelRuntime,
    ModelRuntimeError,
    ModelRuntimeInfo,
    RuntimeCapabilities,
)


class LLMRuntimeAdapterError(Exception):
    """Raised when the LLM runtime adapter fails."""


class LLMRuntimeAdapter(ModelRuntime):
    """
    Compatibility adapter between the existing LLMClient and the
    provider-independent ModelRuntime interface.

    Current transition:

        AutonomousBrain
              |
              v
        BrainRuntime
              |
              v
        LLMRuntimeAdapter
              |
              v
          LLMClient

    Future:

        AutonomousBrain
              |
              v
        BrainRuntime
              |
              v
        ModelRuntime
              |
              +-- local llama.cpp
              +-- Android runtime
              +-- desktop runtime
              +-- other local runtimes

    The existing LLMClient remains intact.
    """

    name = "llm_client_adapter"

    def __init__(
        self,
        client: LLMClient,
        runtime_name: str = "llm_client_adapter",
    ):
        if not isinstance(
            client,
            LLMClient,
        ):
            raise LLMRuntimeAdapterError(
                "client must be an LLMClient instance."
            )

        self.client = client
        self.name = runtime_name

        self._last_health: Optional[
            ModelRuntimeInfo
        ] = None

    # ------------------------------------------------------------------
    # Runtime description
    # ------------------------------------------------------------------

    def describe(
        self,
    ) -> ModelRuntimeInfo:
        """
        Describe the underlying LLMClient runtime.
        """

        config = getattr(
            self.client,
            "config",
            None,
        )

        provider = str(
            getattr(
                config,
                "provider",
                "unknown",
            )
            or "unknown"
        )

        model = str(
            getattr(
                config,
                "model",
                "unknown",
            )
            or "unknown"
        )

        enabled = bool(
            getattr(
                config,
                "enabled",
                False,
            )
        )

        base_url = getattr(
            config,
            "base_url",
            None,
        )

        return ModelRuntimeInfo(
            runtime=self.name,
            provider=provider,
            model=model,
            available=enabled,
            endpoint=(
                str(base_url)
                if base_url
                else None
            ),
            capabilities=[
                RuntimeCapabilities.CHAT,
                RuntimeCapabilities.REASONING,
                RuntimeCapabilities.TOOL_CALLING,
                RuntimeCapabilities.STREAMING,
            ],
            metadata={
                "adapter": (
                    "LLMRuntimeAdapter"
                ),
                "legacy_client": "LLMClient",
                "compatibility_mode": True,
            },
        )

    # ------------------------------------------------------------------
    # Runtime health
    # ------------------------------------------------------------------

    async def health(
        self,
    ) -> ModelRuntimeInfo:
        """
        Check the underlying LLMClient and return standard runtime
        information.
        """

        description = self.describe()

        try:
            health_method = getattr(
                self.client,
                "health",
                None,
            )

            if not callable(
                health_method
            ):
                result = ModelRuntimeInfo(
                    runtime=description.runtime,
                    provider=description.provider,
                    model=description.model,
                    available=description.available,
                    endpoint=description.endpoint,
                    capabilities=list(
                        description.capabilities
                    ),
                    hardware=dict(
                        description.hardware
                    ),
                    metadata=dict(
                        description.metadata
                    ),
                    error=(
                        "LLMClient does not provide health()."
                    ),
                )

                self._last_health = result

                return result

            raw_health = await health_method()

            if not isinstance(
                raw_health,
                dict,
            ):
                result = ModelRuntimeInfo(
                    runtime=description.runtime,
                    provider=description.provider,
                    model=description.model,
                    available=False,
                    endpoint=description.endpoint,
                    capabilities=list(
                        description.capabilities
                    ),
                    hardware=dict(
                        description.hardware
                    ),
                    metadata=dict(
                        description.metadata
                    ),
                    error=(
                        "LLMClient health() returned "
                        "an unexpected response."
                    ),
                )

                self._last_health = result

                return result

            status = str(
                raw_health.get(
                    "status",
                    "",
                )
                or ""
            ).lower()

            available = (
                status == "ready"
            )

            error = raw_health.get(
                "error"
            )

            result = ModelRuntimeInfo(
                runtime=description.runtime,
                provider=(
                    str(
                        raw_health.get(
                            "provider",
                            description.provider,
                        )
                        or description.provider
                    )
                ),
                model=(
                    str(
                        raw_health.get(
                            "model",
                            description.model,
                        )
                        or description.model
                    )
                ),
                available=available,
                endpoint=description.endpoint,
                capabilities=list(
                    description.capabilities
                ),
                hardware=dict(
                    description.hardware
                ),
                metadata={
                    **description.metadata,
                    "health_status": status,
                    "health_response": raw_health,
                },
                error=(
                    str(error)
                    if error
                    else None
                ),
            )

            self._last_health = result

            return result

        except Exception as exc:
            result = ModelRuntimeInfo(
                runtime=description.runtime,
                provider=description.provider,
                model=description.model,
                available=False,
                endpoint=description.endpoint,
                capabilities=list(
                    description.capabilities
                ),
                hardware=dict(
                    description.hardware
                ),
                metadata=dict(
                    description.metadata
                ),
                error=str(exc),
            )

            self._last_health = result

            return result

    # ------------------------------------------------------------------
    # Generation
    # ------------------------------------------------------------------

    async def generate(
        self,
        request: ModelRequest,
    ) -> ModelResponse:
        """
        Convert a provider-neutral ModelRequest into the existing
        LLMClient request format.
        """

        if not isinstance(
            request,
            ModelRequest,
        ):
            raise LLMRuntimeAdapterError(
                "request must be a ModelRequest instance."
            )

        try:
            response = await self.client.chat(
                messages=request.messages,
                tools=request.tools,
                temperature=request.temperature,
                max_tokens=request.max_tokens,
            )

        except LLMError as exc:
            raise ModelRuntimeError(
                str(exc)
            ) from exc

        except Exception as exc:
            raise ModelRuntimeError(
                f"Unexpected model runtime error: {exc}"
            ) from exc

        text = (
            self.client.extract_text(
                response
            )
            or ""
        )

        reasoning = (
            self._extract_reasoning(
                response
            )
        )

        tool_calls = (
            self.client.extract_tool_calls(
                response
            )
            or []
        )

        finish_reason = (
            self.client.extract_finish_reason(
                response
            )
        )

        usage = (
            self.client.extract_usage(
                response
            )
            or {}
        )

        model = None

        if isinstance(
            response,
            dict,
        ):
            raw_model = response.get(
                "model"
            )

            if raw_model is not None:
                model = str(
                    raw_model
                )

        return ModelResponse(
            content=str(
                text
                or ""
            ),
            reasoning_content=str(
                reasoning
                or ""
            ),
            tool_calls=tool_calls,
            finish_reason=finish_reason,
            model=model,
            usage=(
                usage
                if isinstance(
                    usage,
                    dict,
                )
                else {}
            ),
            raw_response=(
                response
                if isinstance(
                    response,
                    dict,
                )
                else {}
            ),
            metadata={
                "runtime": self.name,
                "adapter": (
                    "LLMRuntimeAdapter"
                ),
            },
        )

    # ------------------------------------------------------------------
    # Compatibility chat method
    # ------------------------------------------------------------------

    async def chat(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[
            List[Dict[str, Any]]
        ] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> ModelResponse:
        """
        Convenience method matching the existing LLMClient style.
        """

        request = ModelRequest(
            messages=messages,
            tools=tools or [],
            temperature=(
                0.2
                if temperature is None
                else temperature
            ),
            max_tokens=(
                1024
                if max_tokens is None
                else max_tokens
            ),
        )

        return await self.generate(
            request
        )

    # ------------------------------------------------------------------
    # Shutdown
    # ------------------------------------------------------------------

    async def close(
        self,
    ) -> None:
        """
        Close the underlying client when supported.

        The current LLMClient does not maintain a persistent client
        connection, so this is intentionally a no-op unless a future
        implementation provides close().
        """

        close_method = getattr(
            self.client,
            "close",
            None,
        )

        if not callable(
            close_method
        ):
            return

        result = close_method()

        if hasattr(
            result,
            "__await__",
        ):
            await result

    # ------------------------------------------------------------------
    # Reasoning extraction
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_reasoning(
        response: Dict[str, Any],
    ) -> str:
        """
        Extract reasoning_content from an OpenAI-compatible response.
        """

        choices = response.get(
            "choices"
        )

        if (
            not isinstance(
                choices,
                list,
            )
            or not choices
        ):
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