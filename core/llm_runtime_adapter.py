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
    Adapter that exposes the existing LLMClient through the new
    provider-independent ModelRuntime interface.

    This allows the application to migrate gradually.

    Existing:

        AutonomousBrain
            ↓
        LLMClient

    can eventually become:

        AutonomousBrain
            ↓
        ModelRuntime
            ↓
        local / remote model

    without requiring the old LLMClient to disappear immediately.

    The adapter deliberately preserves the existing LLMClient as the
    compatibility layer while the wider application moves toward the
    new runtime abstraction.
    """

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
        self.runtime_name = runtime_name

        self._info = ModelRuntimeInfo(
            name=runtime_name,
            provider=getattr(
                client.config,
                "provider",
                "unknown",
            ),
            model=getattr(
                client.config,
                "model",
                "unknown",
            ),
            capabilities={
                RuntimeCapabilities.CHAT,
                RuntimeCapabilities.TOOL_CALLING,
                RuntimeCapabilities.STREAMING,
                RuntimeCapabilities.REASONING,
            },
            metadata={
                "adapter": "LLMRuntimeAdapter",
                "legacy_client": "LLMClient",
            },
        )

    # ------------------------------------------------------------------
    # Runtime information
    # ------------------------------------------------------------------

    @property
    def info(self) -> ModelRuntimeInfo:
        return self._info

    # ------------------------------------------------------------------
    # Core request
    # ------------------------------------------------------------------

    async def generate(
        self,
        request: ModelRequest,
    ) -> ModelResponse:
        """
        Execute a ModelRequest using the existing LLMClient.
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
        )

        usage = (
            response.get(
                "usage",
                {},
            )
            if isinstance(
                response,
                dict,
            )
            else {}
        )

        metadata = {
            "raw_response": response,
        }

        return ModelResponse(
            text=text,
            reasoning=reasoning,
            tool_calls=tool_calls,
            usage=usage
            if isinstance(
                usage,
                dict,
            )
            else {},
            metadata=metadata,
        )

    # ------------------------------------------------------------------
    # Convenience interface
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
        Convenience wrapper around generate().
        """

        request = ModelRequest(
            messages=messages,
            tools=tools or [],
            temperature=temperature,
            max_tokens=max_tokens,
        )

        return await self.generate(
            request
        )

    # ------------------------------------------------------------------
    # Health
    # ------------------------------------------------------------------

    async def health_check(
        self,
    ) -> bool:
        """
        Check whether the underlying LLM client can reach its model
        provider.

        This deliberately uses the existing client's configuration
        rather than assuming a particular provider.
        """

        health_method = getattr(
            self.client,
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

        # The legacy client may not expose a health endpoint.
        # Configuration availability is therefore the best fallback.
        return bool(
            getattr(
                self.client.config,
                "enabled",
                False,
            )
        )

    # ------------------------------------------------------------------
    # Shutdown
    # ------------------------------------------------------------------

    async def close(self) -> None:
        """
        Close the underlying LLM client if it provides a close method.
        """

        close_method = getattr(
            self.client,
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

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_reasoning(
        response: Dict[str, Any],
    ) -> str:
        """
        Extract reasoning content from Qwen-compatible and other
        OpenAI-compatible response formats.
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