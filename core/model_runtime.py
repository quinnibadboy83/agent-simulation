from __future__ import annotations

"""
Model Runtime
-------------

Provider/runtime abstraction for the Agent Simulation Engine.

The Agent Simulation Engine must not depend directly on:

    - Termux
    - llama-server
    - Cloudflare
    - a particular model
    - a particular computer
    - a particular operating system

This module defines the runtime boundary between the agent brain and
the underlying language model.

The long-term architecture is:

    Agent Brain
        |
        v
    Model Runtime
        |
        +-- Local OpenAI-compatible runtime
        +-- Native llama.cpp runtime
        +-- Other local runtimes
        +-- Future model runtimes
        |
        v
    Open-weight model

The model is the base reasoning engine.

The Agent Simulation Engine remains responsible for:

    - memory
    - experience
    - learning
    - planning
    - tools
    - permissions
    - action approval
    - agent state
    - orchestration

This separation is intentional.

A model can therefore be replaced without rebuilding the agent
architecture.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Runtime errors
# ---------------------------------------------------------------------------


class ModelRuntimeError(Exception):
    """Base exception raised by the model runtime layer."""


class ModelRuntimeUnavailable(ModelRuntimeError):
    """Raised when a model runtime cannot currently be reached."""


class ModelRuntimeAuthenticationError(ModelRuntimeError):
    """Raised when a model runtime rejects authentication."""


class ModelRuntimeRequestError(ModelRuntimeError):
    """Raised when a model runtime rejects a request."""


# ---------------------------------------------------------------------------
# Runtime metadata
# ---------------------------------------------------------------------------


@dataclass
class ModelRuntimeInfo:
    """
    Describes the currently configured model runtime.

    This object deliberately describes the runtime rather than the
    intelligence of the model itself.
    """

    runtime: str
    provider: str
    model: str

    available: bool = False

    endpoint: Optional[str] = None

    capabilities: List[str] = field(
        default_factory=list
    )

    hardware: Dict[str, Any] = field(
        default_factory=dict
    )

    metadata: Dict[str, Any] = field(
        default_factory=dict
    )

    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert runtime information into a JSON-safe dictionary.
        """

        return {
            "runtime": self.runtime,
            "provider": self.provider,
            "model": self.model,
            "available": self.available,
            "endpoint": self.endpoint,
            "capabilities": list(
                self.capabilities
            ),
            "hardware": dict(
                self.hardware
            ),
            "metadata": dict(
                self.metadata
            ),
            "error": self.error,
        }


# ---------------------------------------------------------------------------
# Runtime request
# ---------------------------------------------------------------------------


@dataclass
class ModelRequest:
    """
    Provider-neutral model request.

    Agents should eventually construct this object instead of knowing
    how a particular model server expects its request formatted.
    """

    messages: List[Dict[str, Any]]

    tools: Optional[
        List[Dict[str, Any]]
    ] = None

    temperature: float = 0.2

    max_tokens: int = 1024

    metadata: Dict[str, Any] = field(
        default_factory=dict
    )

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the request to a normal dictionary.
        """

        result: Dict[str, Any] = {
            "messages": list(
                self.messages
            ),
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }

        if self.tools:
            result["tools"] = list(
                self.tools
            )

        if self.metadata:
            result["metadata"] = dict(
                self.metadata
            )

        return result


# ---------------------------------------------------------------------------
# Runtime response
# ---------------------------------------------------------------------------


@dataclass
class ModelResponse:
    """
    Provider-neutral model response.

    The raw provider response is retained so that we do not throw away
    information that may become useful to the learning and evaluation
    systems later.
    """

    content: str = ""

    reasoning_content: str = ""

    tool_calls: List[
        Dict[str, Any]
    ] = field(
        default_factory=list
    )

    finish_reason: Optional[str] = None

    model: Optional[str] = None

    usage: Dict[str, Any] = field(
        default_factory=dict
    )

    raw_response: Dict[str, Any] = field(
        default_factory=dict
    )

    metadata: Dict[str, Any] = field(
        default_factory=dict
    )

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the response into a JSON-safe dictionary.
        """

        return {
            "content": self.content,
            "reasoning_content": (
                self.reasoning_content
            ),
            "tool_calls": list(
                self.tool_calls
            ),
            "finish_reason": (
                self.finish_reason
            ),
            "model": self.model,
            "usage": dict(
                self.usage
            ),
            "raw_response": dict(
                self.raw_response
            ),
            "metadata": dict(
                self.metadata
            ),
        }


# ---------------------------------------------------------------------------
# Abstract runtime
# ---------------------------------------------------------------------------


class ModelRuntime(ABC):
    """
    Abstract model runtime.

    This is the key portability boundary of the Agent Simulation
    Engine.

    Nothing above this layer should need to know whether the model
    runs on:

        - Android
        - Windows
        - Linux
        - macOS
        - CPU
        - GPU
        - NPU
        - llama.cpp
        - another local inference engine
        - another compatible runtime
    """

    name: str = "unknown"

    @abstractmethod
    async def health(
        self,
    ) -> ModelRuntimeInfo:
        """
        Determine whether the runtime is available.
        """

        raise NotImplementedError

    @abstractmethod
    async def generate(
        self,
        request: ModelRequest,
    ) -> ModelResponse:
        """
        Generate a model response.
        """

        raise NotImplementedError

    @abstractmethod
    def describe(
        self,
    ) -> ModelRuntimeInfo:
        """
        Return static/runtime configuration information.
        """

        raise NotImplementedError


# ---------------------------------------------------------------------------
# Runtime registry
# ---------------------------------------------------------------------------


class ModelRuntimeRegistry:
    """
    Registry of available model runtimes.

    The registry allows the application to discover and select a
    runtime without hard-coding a particular model into the agents.

    Future examples:

        registry.register("llama_cpp", runtime)

        registry.register("native_android", runtime)

        registry.register("desktop_gpu", runtime)

        registry.register("other_local_runtime", runtime)
    """

    def __init__(self):
        self._runtimes: Dict[
            str,
            ModelRuntime,
        ] = {}

    def register(
        self,
        name: str,
        runtime: ModelRuntime,
    ) -> None:
        """
        Register or replace a runtime.
        """

        normalized = (
            str(name)
            .strip()
            .lower()
        )

        if not normalized:
            raise ValueError(
                "Runtime name cannot be empty."
            )

        self._runtimes[
            normalized
        ] = runtime

    def unregister(
        self,
        name: str,
    ) -> bool:
        """
        Remove a runtime.

        Returns True when a runtime was removed.
        """

        normalized = (
            str(name)
            .strip()
            .lower()
        )

        return (
            self._runtimes.pop(
                normalized,
                None,
            )
            is not None
        )

    def get(
        self,
        name: str,
    ) -> Optional[ModelRuntime]:
        """
        Retrieve a runtime by name.
        """

        normalized = (
            str(name)
            .strip()
            .lower()
        )

        return self._runtimes.get(
            normalized
        )

    def require(
        self,
        name: str,
    ) -> ModelRuntime:
        """
        Retrieve a runtime or raise a clear error.
        """

        runtime = self.get(
            name
        )

        if runtime is None:
            raise ModelRuntimeError(
                f"Model runtime '{name}' "
                "is not registered."
            )

        return runtime

    def names(self) -> List[str]:
        """
        Return registered runtime names.
        """

        return sorted(
            self._runtimes.keys()
        )

    def describe_all(
        self,
    ) -> Dict[str, Dict[str, Any]]:
        """
        Return descriptions for all registered runtimes.
        """

        result: Dict[
            str,
            Dict[str, Any],
        ] = {}

        for name, runtime in (
            self._runtimes.items()
        ):
            try:
                result[name] = (
                    runtime.describe().to_dict()
                )
            except Exception as exc:
                result[name] = {
                    "runtime": name,
                    "available": False,
                    "error": str(exc),
                }

        return result


# ---------------------------------------------------------------------------
# Runtime selection
# ---------------------------------------------------------------------------


class ModelRuntimeSelector:
    """
    Select the most appropriate runtime.

    This is intentionally conservative in the first version.

    We do NOT automatically move inference between machines yet.

    The purpose of this class is to establish the decision boundary
    that will later use hardware capabilities, model availability,
    memory requirements, performance and user preferences.
    """

    def __init__(
        self,
        registry: ModelRuntimeRegistry,
    ):
        self.registry = registry

    def select(
        self,
        preferred_runtime: Optional[str] = None,
    ) -> ModelRuntime:
        """
        Select a runtime.

        If a preferred runtime is supplied, it is used when available.

        Otherwise the first registered runtime is selected.

        Later versions can make this decision using:

            - available RAM
            - GPU VRAM
            - CPU architecture
            - accelerator support
            - model size
            - quantisation
            - performance
            - battery state
            - user settings
        """

        if preferred_runtime:
            runtime = self.registry.get(
                preferred_runtime
            )

            if runtime is not None:
                return runtime

            raise ModelRuntimeUnavailable(
                "Preferred model runtime "
                f"'{preferred_runtime}' "
                "is not registered."
            )

        names = self.registry.names()

        if not names:
            raise ModelRuntimeUnavailable(
                "No model runtimes are registered."
            )

        runtime = self.registry.get(
            names[0]
        )

        if runtime is None:
            raise ModelRuntimeUnavailable(
                "The selected model runtime "
                "could not be loaded."
            )

        return runtime


# ---------------------------------------------------------------------------
# Runtime learning hooks
# ---------------------------------------------------------------------------


@dataclass
class ModelExperience:
    """
    Structured record of an interaction with the model.

    This is NOT model training.

    It is the first foundation for application-level learning.

    Future learning modules can store and analyse these experiences
    to improve:

        - prompts
        - planning
        - tool selection
        - memory retrieval
        - agent delegation
        - decision quality
        - model selection
    """

    agent: Optional[str]

    objective: Optional[str]

    request: ModelRequest

    response: ModelResponse

    success: bool

    outcome: Optional[str] = None

    feedback: Optional[str] = None

    score: Optional[float] = None

    tags: List[str] = field(
        default_factory=list
    )

    metadata: Dict[str, Any] = field(
        default_factory=dict
    )

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert experience into a serialisable dictionary.
        """

        return {
            "agent": self.agent,
            "objective": self.objective,
            "request": self.request.to_dict(),
            "response": self.response.to_dict(),
            "success": self.success,
            "outcome": self.outcome,
            "feedback": self.feedback,
            "score": self.score,
            "tags": list(
                self.tags
            ),
            "metadata": dict(
                self.metadata
            ),
        }


# ---------------------------------------------------------------------------
# Runtime capability helpers
# ---------------------------------------------------------------------------


class RuntimeCapabilities:
    """
    Standard capability names used by the Agent Simulation Engine.
    """

    CHAT = "chat"

    REASONING = "reasoning"

    TOOL_CALLING = "tool_calling"

    STREAMING = "streaming"

    LOCAL = "local"

    GPU = "gpu"

    CPU = "cpu"

    MEMORY = "memory"

    EMBEDDINGS = "embeddings"

    VISION = "vision"

    AUDIO = "audio"


# ---------------------------------------------------------------------------
# Factory helpers
# ---------------------------------------------------------------------------


def create_runtime_registry() -> ModelRuntimeRegistry:
    """
    Create an empty runtime registry.

    The actual runtime implementations are registered by the
    application bootstrap layer.

    Keeping creation separate from registration prevents the core
    agent architecture from becoming dependent on one particular
    inference engine.
    """

    return ModelRuntimeRegistry()


def create_runtime_selector(
    registry: ModelRuntimeRegistry,
) -> ModelRuntimeSelector:
    """
    Create the runtime selector used by the application.
    """

    return ModelRuntimeSelector(
        registry
    )