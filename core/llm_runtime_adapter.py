"""
LLM Runtime Adapter
-------------------

Compatibility bridge between the existing LLMClient and the
provider-independent ModelRuntime architecture.

The adapter now supports the RuntimeManager so the application can
select the configured runtime without requiring AutonomousBrain to
know which runtime is being used.

Architecture:

    AutonomousBrain
          |
          v
    BrainRuntime
          |
          v
    LLMRuntimeAdapter
          |
          +--------------------+
          |                    |
          v                    v
    RuntimeManager       legacy LLMClient
          |
          v
    RuntimeFactory
          |
          v
    ModelRuntime
"""

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

from .runtime_config import (
    RuntimeConfig,
)

from .runtime_manager import (
    RuntimeManager,
    RuntimeManagerError,
)


class LLMRuntimeAdapterError(Exception):
    """Raised when the LLM runtime adapter fails."""


class LLMRuntimeAdapter(ModelRuntime):
    """
    Compatibility adapter between LLMClient and ModelRuntime.

    The RuntimeManager is preferred.

    The legacy LLMClient remains available as a compatibility fallback.

    This allows the existing AutonomousBrain to migrate to the new
    runtime architecture without breaking its current interface.
    """

    name = "llm_runtime_adapter"

    def __init__(
        self,
        client: LLMClient,
        runtime_manager: Optional[RuntimeManager] = None,
        runtime_name: str = "llm_runtime_adapter",
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

        self.runtime_manager = (
            runtime_manager
            if runtime_manager is not None
            else RuntimeManager(
                config=RuntimeConfig.from_environment()
            )
        )

        self._last_health: Optional[
            ModelRuntimeInfo
        ] = None

    # ------------------------------------------------------------------
    # Runtime access
    # ------------------------------------------------------------------

    def _managed_runtime(self) -> Optional[ModelRuntime]:
        """
        Return the currently active managed runtime.

        This method does not create a runtime. Runtime creation remains
        lazy until generation or an explicit health check.
        """

        return self.runtime_manager.runtime

    def _ensure_managed_runtime(self) -> ModelRuntime:
        """
        Create and return the configured managed runtime.
        """

        try:
            return self.runtime_manager.ensure_started()

        except RuntimeManagerError as exc:
            raise ModelRuntimeError(
                f"Unable to start model runtime: {exc}"
            ) from exc

        except Exception as exc:
            raise ModelRuntimeError(
                f"Unexpected runtime startup error: {exc}"
            ) from exc

    # ------------------------------------------------------------------
    # Runtime description
    # ------------------------------------------------------------------

    def describe(
        self,
    ) -> ModelRuntimeInfo:
        """
        Describe the managed runtime when available.

        Before the managed runtime is started, describe the configured
        runtime using RuntimeConfig without making a network request.
        """

        managed = self._managed_runtime()

        if managed is not None:
            try:
                description = managed.describe()

                if isinstance(
                    description,
                    ModelRuntimeInfo,
                ):
                    return description

                if isinstance(
                    description,
                    dict,
                ):
                    return ModelRuntimeInfo(
                        runtime=str(
                            description.get(
                                "runtime",
                                self.name,
                            )
                        ),
                        provider=str(
                            description.get(
                                "provider",
                                self.runtime_manager.config.provider,
                            )
                        ),
                        model=str(
                            description.get(
                                "model",
                                self.runtime_manager.config.model,
                            )
                        ),
                        available=bool(
                            description.get(
                                "available",
                                False,
                            )
                        ),
                        endpoint=description.get(
                            "endpoint",
                            self.runtime_manager.config.base_url,
                        ),
                        capabilities=list(
                            description.get(
                                "capabilities",
                                [],
                            )
                        ),
                        hardware=dict(
                            description.get(
                                "hardware",
                                {},
                            )
                        ),
                        metadata=dict(
                            description.get(
                                "metadata",
                                {},
                            )
                        ),
                        error=description.get(
                            "error"
                        ),
                    )

            except Exception:
                pass

        config = self.runtime_manager.config

        return ModelRuntimeInfo(
            runtime=(
                config.runtime_name
                or self.name
            ),
            provider=config.provider,
            model=config.model,
            available=False,
            endpoint=config.base_url,
            capabilities=[
                RuntimeCapabilities.CHAT,
                RuntimeCapabilities.REASONING,
                RuntimeCapabilities.TOOL_CALLING,
            ],
            hardware=(
                {
                    "configured": config.hardware
                }
                if config.hardware
                else {}
            ),
            metadata={
                "adapter": "LLMRuntimeAdapter",
                "runtime_manager": True,
                "runtime_started": (
                    self.runtime_manager.started
                ),
                "local": config.local,
            },
        )

    # ------------------------------------------------------------------
    # Runtime health
    # ------------------------------------------------------------------

    async def health(
        self,
    ) -> ModelRuntimeInfo:
        """
        Check the managed runtime.

        If the managed runtime cannot be used, the legacy LLMClient is
        checked as a compatibility path.
        """

        try:
            result = await self.runtime_manager.health()

            if isinstance(
                result,
                ModelRuntimeInfo,
            ):
                self._last_health = result
                return result

        except Exception as managed_error:
            description = self.describe()

            fallback = await self._legacy_health(
                description=description,
                error=str(managed_error),
            )

            self._last_health = fallback

            return fallback

        result = self.describe()

        self._last_health = result

        return result

    async def _legacy_health(
        self,
        description: ModelRuntimeInfo,
        error: Optional[str] = None,
    ) -> ModelRuntimeInfo:
        """
        Check the legacy LLMClient for compatibility.
        """

        health_method = getattr(
            self.client,
            "health",
            None,
        )

        if not callable(
            health_method
        ):
            return ModelRuntimeInfo(
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
                metadata={
                    **description.metadata,
                    "compatibility_mode": True,
                },
                error=(
                    error
                    or "LLMClient does not provide health()."
                ),
            )

        try:
            raw_health = await health_method()

            if isinstance(
                raw_health,
                dict,
            ):
                status = str(
                    raw_health.get(
                        "status",
                        "",
                    )
                    or ""
                ).lower()

                return ModelRuntimeInfo(
                    runtime=description.runtime,
                    provider=str(
                        raw_health.get(
                            "provider",
                            description.provider,
                        )
                        or description.provider
                    ),
                    model=str(
                        raw_health.get(
                            "model",
                            description.model,
                        )
                        or description.model
                    ),
                    available=(
                        status == "ready"
                    ),
                    endpoint=description.endpoint,
                    capabilities=list(
                        description.capabilities
                    ),
                    hardware=dict(
                        description.hardware
                    ),
                    metadata={
                        **description.metadata,
                        "compatibility_mode": True,
                        "health_status": status,
                    },
                    error=raw_health.get(
                        "error"
                    ),
                )

        except Exception as exc:
            return ModelRuntimeInfo(
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
                metadata={
                    **description.metadata,
                    "compatibility_mode": True,
                },
                error=str(exc),
            )

        return ModelRuntimeInfo(
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
            metadata={
                **description.metadata,
                "compatibility_mode": True,
            },
            error=error,
        )

    # ------------------------------------------------------------------
    # Generation
    # ------------------------------------------------------------------

    async def generate(
        self,
        request: ModelRequest,
    ) -> ModelResponse:
        """
        Generate through the RuntimeManager.

        The managed ModelRuntime is now the primary inference path.

        If runtime startup or generation fails, the legacy LLMClient
        remains available as a compatibility fallback.
        """

        if not isinstance(
            request,
            ModelRequest,
        ):
            raise LLMRuntimeAdapterError(
                "request must be a ModelRequest instance."
            )

        try:
            runtime = self._ensure_managed_runtime()

            response = await runtime.generate(
                request
            )

            return self._normalise_runtime_response(
                response
            )

        except ModelRuntimeError:
            raise

        except Exception as exc:
            raise ModelRuntimeError(
                f"Managed runtime generation failed: {exc}"
            ) from exc

    # ------------------------------------------------------------------
    # Legacy generation
    # ------------------------------------------------------------------

    async def generate_legacy(
        self,
        request: ModelRequest,
    ) -> ModelResponse:
        """
        Explicitly generate through the existing LLMClient.

        This is retained for migration, diagnostics, and compatibility.
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
                f"Unexpected legacy model runtime error: {exc}"
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
                "runtime_mode": "legacy_llm_client",
                "compatibility_mode": True,
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
        Shut down the managed runtime.

        The legacy client is only closed separately when no managed
        runtime is active.
        """

        try:
            await self.runtime_manager.stop()
        except Exception:
            pass

        if self.runtime_manager.runtime is not None:
            return

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
    # Response normalisation
    # ------------------------------------------------------------------

    @staticmethod
    def _normalise_runtime_response(
        response: Any,
    ) -> ModelResponse:
        """
        Ensure the runtime response conforms to ModelResponse.
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

        raise ModelRuntimeError(
            "Runtime returned an unsupported response type."
        )

    # ------------------------------------------------------------------
    # Reasoning extraction
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_reasoning(
        response: Dict[str, Any],
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