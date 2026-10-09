"""
Development Model Runtime
-------------------------

Deterministic, offline model runtime used to test the Agent Simulation
Engine without requiring a real LLM server.

This runtime is intentionally simple.

It exists to prove that the application's runtime abstraction,
BrainRuntime, memory, learning, and orchestration layers can operate
without depending on a hosted inference provider.

It performs no network requests and executes no tools.
"""

from __future__ import annotations

from typing import Any, Dict

from .model_runtime import (
    ModelRequest,
    ModelResponse,
    ModelRuntime,
    ModelRuntimeInfo,
    RuntimeCapabilities,
)


class DevelopmentRuntimeError(RuntimeError):
    """Raised when the development runtime fails."""


class DevelopmentModelRuntime(ModelRuntime):
    """
    Deterministic local runtime for development and integration testing.

    This is NOT an LLM.

    Its purpose is to provide a stable runtime implementation while the
    real local model runtime is unavailable.

    Later, this implementation can be replaced by llama.cpp,
    llama-server, or another local inference backend without changing
    the higher-level agent architecture.
    """

    def __init__(
        self,
        model: str = "development-model",
        runtime_name: str = "development",
        provider: str = "development",
    ) -> None:
        self.model = model
        self.runtime_name = runtime_name
        self.provider = provider

    def describe(self) -> ModelRuntimeInfo:
        """Describe this runtime."""

        return ModelRuntimeInfo(
            runtime=self.runtime_name,
            provider=self.provider,
            model=self.model,
            available=True,
            endpoint=None,
            capabilities=[
                RuntimeCapabilities.CHAT,
                RuntimeCapabilities.REASONING,
                RuntimeCapabilities.LOCAL,
                RuntimeCapabilities.CPU,
            ],
            # ModelRuntimeInfo expects a dictionary here, not a string.
            hardware={
                "mode": "development",
                "local": True,
                "network_inference": False,
            },
            metadata={
                "mode": "deterministic",
                "network": False,
                "inference": False,
            },
            error=None,
        )

    async def health(self) -> ModelRuntimeInfo:
        """Return a healthy runtime status."""

        return self.describe()

    async def generate(
        self,
        request: ModelRequest,
    ) -> ModelResponse:
        """
        Produce a deterministic response.

        The request is inspected only to identify the user's latest
        message. No external service is contacted.
        """

        if request is None:
            raise DevelopmentRuntimeError(
                "ModelRequest is required."
            )

        messages = request.messages or []
        user_message = ""

        for message in reversed(messages):
            if (
                isinstance(message, dict)
                and message.get("role") == "user"
            ):
                content = message.get("content", "")

                if content is None:
                    content = ""

                user_message = str(content)
                break

        if not user_message:
            user_message = "No user request supplied."

        content = (
            "DEVELOPMENT RUNTIME RESPONSE\n\n"
            "The Agent Simulation Engine successfully reached "
            "the model-runtime layer.\n\n"
            f"Received request: {user_message}\n\n"
            "Runtime status: ONLINE\n"
            "Inference mode: DEVELOPMENT\n"
            "Network inference: DISABLED\n\n"
            "This response proves that the application's runtime "
            "abstraction is functioning. A real local LLM runtime "
            "can replace this runtime without changing the "
            "higher-level architecture."
        )

        return ModelResponse(
            content=content,
            reasoning_content=(
                "Development runtime verified the request and "
                "returned a deterministic test response."
            ),
            tool_calls=[],
            finish_reason="stop",
            model=self.model,
            usage={
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
            },
            raw_response={
                "development_runtime": True,
                "request_received": True,
            },
            metadata={
                "runtime": self.runtime_name,
                "provider": self.provider,
                "deterministic": True,
            },
        )

    async def close(self) -> None:
        """Close the development runtime."""

        return None

    def to_dict(self) -> Dict[str, Any]:
        """Return a safe serialisable description."""

        return self.describe().to_dict()


def create_development_runtime(
    model: str = "development-model",
) -> DevelopmentModelRuntime:
    """Create a development runtime."""

    return DevelopmentModelRuntime(
        model=model,
    )