"""Provider-neutral runtime configuration for Agent Simulation Engine."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Dict, Optional


class RuntimeConfigError(ValueError):
    """Raised when runtime configuration is invalid."""


@dataclass
class RuntimeConfig:
    runtime: str = "openai_compatible"
    provider: str = "openai_compatible"
    model: str = "local-model"
    base_url: str = "http://127.0.0.1:8080/v1"
    api_key: Optional[str] = None
    timeout: float = 300.0
    temperature: float = 0.2
    max_tokens: int = 4096
    max_reasoning_steps: int = 24
    runtime_name: Optional[str] = None
    hardware: Optional[str] = None
    local: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.runtime = str(self.runtime).strip().lower()
        self.provider = str(self.provider).strip()
        self.model = str(self.model).strip()
        self.base_url = str(self.base_url).strip().rstrip("/")

        if (
            not self.runtime
            or not self.provider
            or not self.model
            or not self.base_url
        ):
            raise RuntimeConfigError(
                "Runtime, provider, model and base_url must not be empty."
            )

        if (
            self.timeout <= 0
            or self.temperature < 0
            or self.max_tokens <= 0
            or self.max_reasoning_steps <= 0
        ):
            raise RuntimeConfigError(
                "Invalid timeout, temperature, token limit or "
                "reasoning-step limit."
            )

        if not self.runtime_name:
            self.runtime_name = f"{self.provider}:{self.model}"

        if self.metadata is None:
            self.metadata = {}

    @classmethod
    def from_environment(cls) -> "RuntimeConfig":
        runtime = (
            os.getenv("MODEL_RUNTIME")
            or os.getenv("BRAIN_PROVIDER")
            or "openai_compatible"
        )
        provider = (
            os.getenv("MODEL_PROVIDER")
            or cls._default_provider(runtime)
        )

        return cls(
            runtime=runtime,
            provider=provider,
            model=(
                os.getenv("MODEL_NAME")
                or os.getenv("BRAIN_MODEL")
                or "local-model"
            ),
            base_url=(
                os.getenv("MODEL_BASE_URL")
                or os.getenv("BRAIN_BASE_URL")
                or "http://127.0.0.1:8080/v1"
            ),
            api_key=(
                os.getenv("MODEL_API_KEY")
                or os.getenv("BRAIN_API_KEY")
            ),
            timeout=cls._float_env(
                "MODEL_TIMEOUT", "BRAIN_TIMEOUT", 300.0
            ),
            temperature=cls._float_env(
                "MODEL_TEMPERATURE", "BRAIN_TEMPERATURE", 0.2
            ),
            max_tokens=cls._int_env(
                "MODEL_MAX_TOKENS", "BRAIN_MAX_TOKENS", 4096
            ),
            max_reasoning_steps=cls._int_env(
                "MODEL_MAX_REASONING_STEPS",
                "BRAIN_MAX_REASONING_STEPS",
                24,
            ),
            runtime_name=os.getenv("MODEL_RUNTIME_NAME") or None,
            hardware=(
                os.getenv("MODEL_HARDWARE")
                or os.getenv("BRAIN_HARDWARE")
                or None
            ),
            local=cls._bool_env("MODEL_LOCAL", True),
        )

    def to_dict(self, include_secret: bool = False) -> Dict[str, Any]:
        result = {
            "runtime": self.runtime,
            "provider": self.provider,
            "model": self.model,
            "base_url": self.base_url,
            "timeout": self.timeout,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "max_reasoning_steps": self.max_reasoning_steps,
            "runtime_name": self.runtime_name,
            "hardware": self.hardware,
            "local": self.local,
            "api_key_configured": bool(self.api_key),
            "metadata": dict(self.metadata),
        }

        if include_secret:
            result["api_key"] = self.api_key

        return result

    def public_dict(self) -> Dict[str, Any]:
        return self.to_dict(include_secret=False)

    def with_overrides(self, **overrides: Any) -> "RuntimeConfig":
        values = self.to_dict(include_secret=True)
        values.update(overrides)
        values.pop("api_key_configured", None)
        return RuntimeConfig(**values)

    def is_local(self) -> bool:
        return self.local

    def has_api_key(self) -> bool:
        return bool(self.api_key)

    @staticmethod
    def _default_provider(runtime: str) -> str:
        value = str(runtime).strip().lower()

        if value in {"development", "dev", "test"}:
            return "development"

        if value in {"llama_cpp", "llama-server", "llamacpp"}:
            return "llama.cpp"

        if value == "local":
            return "local"

        return "openai_compatible"

    @staticmethod
    def _float_environment(
        primary: str,
        secondary: str,
        default: float,
    ) -> float:
        return RuntimeConfig._float_env(primary, secondary, default)

    @staticmethod
    def _int_environment(
        primary: str,
        secondary: str,
        default: int,
    ) -> int:
        return RuntimeConfig._int_env(primary, secondary, default)

    @staticmethod
    def _bool_environment(name: str, default: bool) -> bool:
        return RuntimeConfig._bool_env(name, default)

    @staticmethod
    def _float_env(
        primary: str,
        secondary: str,
        default: float,
    ) -> float:
        value = os.getenv(primary, os.getenv(secondary))

        if value is None:
            return default

        try:
            return float(value)
        except ValueError as exc:
            raise RuntimeConfigError(
                f"Invalid numeric value for {primary}/{secondary}: {value}"
            ) from exc

    @staticmethod
    def _int_env(
        primary: str,
        secondary: str,
        default: int,
    ) -> int:
        value = os.getenv(primary, os.getenv(secondary))

        if value is None:
            return default

        try:
            return int(value)
        except ValueError as exc:
            raise RuntimeConfigError(
                f"Invalid integer value for {primary}/{secondary}: {value}"
            ) from exc

    @staticmethod
    def _bool_env(name: str, default: bool) -> bool:
        value = os.getenv(name)

        if value is None:
            return default

        normalized = value.strip().lower()

        if normalized in {"1", "true", "yes", "on"}:
            return True

        if normalized in {"0", "false", "no", "off"}:
            return False

        raise RuntimeConfigError(
            f"Invalid boolean value for {name}: {value}"
        )