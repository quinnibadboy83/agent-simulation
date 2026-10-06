from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass
class BrainConfig:
    """
    Configuration for the autonomous LLM brain.

    The model itself is intentionally external to the Python application.
    This allows us to start with a lightweight open model and later move
    to a stronger model without rebuilding the agent architecture.
    """

    enabled: bool = False

    provider: str = "llama_cpp"

    base_url: str = "http://127.0.0.1:8080/v1"

    model: str = "local-model"

    api_key: str = "sk-no-key-required"

    temperature: float = 0.2

    max_tokens: int = 2048

    timeout: float = 120.0

    max_reasoning_steps: int = 12

    @classmethod
    def from_environment(cls) -> "BrainConfig":
        enabled_value = os.getenv(
            "BRAIN_ENABLED",
            "false",
        ).strip().lower()

        enabled = enabled_value in {
            "1",
            "true",
            "yes",
            "on",
        }

        return cls(
            enabled=enabled,
            provider=os.getenv(
                "BRAIN_PROVIDER",
                "llama_cpp",
            ),
            base_url=os.getenv(
                "BRAIN_BASE_URL",
                "http://127.0.0.1:8080/v1",
            ).rstrip("/"),
            model=os.getenv(
                "BRAIN_MODEL",
                "local-model",
            ),
            api_key=os.getenv(
                "BRAIN_API_KEY",
                "sk-no-key-required",
            ),
            temperature=_float_env(
                "BRAIN_TEMPERATURE",
                0.2,
            ),
            max_tokens=_int_env(
                "BRAIN_MAX_TOKENS",
                2048,
            ),
            timeout=_float_env(
                "BRAIN_TIMEOUT",
                120.0,
            ),
            max_reasoning_steps=_int_env(
                "BRAIN_MAX_REASONING_STEPS",
                12,
            ),
        )

    def public(self) -> dict:
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


def _float_env(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default


def _int_env(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default
