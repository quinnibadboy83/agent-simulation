from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass
class BrainConfig:
    """
    Configuration for the autonomous LLM brain.

    The LLM is external to the agent application.

    The model is responsible for reasoning, planning and deciding which
    available capabilities it wants to use.

    Security boundaries are NOT implemented by limiting the model here.
    Consequential actions are controlled externally by the ToolRegistry
    and Creator ApprovalGate.
    """

    enabled: bool = False

    # Supported conceptually:
    # llama_cpp
    # openai_compatible
    # any future OpenAI-compatible provider
    provider: str = "llama_cpp"

    # OpenAI-compatible API root.
    #
    # Example llama.cpp:
    # http://127.0.0.1:8080/v1
    #
    # Example remote server:
    # https://your-server.example/v1
    base_url: str = "http://127.0.0.1:8080/v1"

    model: str = "local-model"

    # Empty is valid for local llama.cpp servers.
    api_key: str = ""

    # The model controls its own generation behaviour.
    temperature: float = 0.2

    # This is a request parameter, not a safety restriction.
    # Increase it for larger reasoning/output requirements.
    max_tokens: int = 4096

    # Maximum HTTP request duration.
    timeout: float = 300.0

    # Maximum number of agent reasoning/tool iterations.
    #
    # This is an orchestration guard against infinite loops.
    # It does NOT restrict what the model is allowed to reason about
    # or what capabilities it can request.
    max_reasoning_steps: int = 24

    @classmethod
    def from_environment(cls) -> "BrainConfig":
        return cls(
            enabled=_bool_env(
                "BRAIN_ENABLED",
                False,
            ),
            provider=os.getenv(
                "BRAIN_PROVIDER",
                "llama_cpp",
            ).strip(),
            base_url=os.getenv(
                "BRAIN_BASE_URL",
                "http://127.0.0.1:8080/v1",
            ).strip().rstrip("/"),
            model=os.getenv(
                "BRAIN_MODEL",
                "local-model",
            ).strip(),
            api_key=os.getenv(
                "BRAIN_API_KEY",
                "",
            ),
            temperature=_float_env(
                "BRAIN_TEMPERATURE",
                0.2,
            ),
            max_tokens=_int_env(
                "BRAIN_MAX_TOKENS",
                4096,
            ),
            timeout=_float_env(
                "BRAIN_TIMEOUT",
                300.0,
            ),
            max_reasoning_steps=_int_env(
                "BRAIN_MAX_REASONING_STEPS",
                24,
            ),
        )

    def public(self) -> dict:
        """
        Return configuration suitable for API status output.

        Never expose the API key.
        """
        return {
            "enabled": self.enabled,
            "provider": self.provider,
            "base_url": self.base_url,
            "model": self.model,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "timeout": self.timeout,
            "max_reasoning_steps": self.max_reasoning_steps,
        }


def _bool_env(
    name: str,
    default: bool,
) -> bool:
    value = os.getenv(
        name,
        str(default),
    ).strip().lower()

    return value in {
        "1",
        "true",
        "yes",
        "on",
        "enabled",
    }


def _float_env(
    name: str,
    default: float,
) -> float:
    try:
        value = float(
            os.getenv(
                name,
                str(default),
            )
        )

        if value < 0:
            return default

        return value

    except (TypeError, ValueError):
        return default


def _int_env(
    name: str,
    default: int,
) -> int:
    try:
        value = int(
            os.getenv(
                name,
                str(default),
            )
        )

        if value <= 0:
            return default

        return value

    except (TypeError, ValueError):
        return default
