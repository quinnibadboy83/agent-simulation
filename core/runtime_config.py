"""
Runtime Configuration
---------------------

Central configuration for the Agent Simulation Engine's model runtime.

This module keeps runtime configuration separate from the runtime
implementation itself.

The configuration layer does not create network connections, load
models, or execute inference. It only describes how the application
should configure its selected runtime.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Dict, Optional


class RuntimeConfigError(ValueError):
    """Raised when runtime configuration is invalid."""


@dataclass
class RuntimeConfig:
    """
    Configuration describing how a model runtime should operate.

    This object intentionally contains configuration only. Runtime
    creation remains the responsibility of RuntimeFactory.
    """

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
        self.runtime = self.runtime.strip().lower()
        self.provider = self.provider.strip()
        self.model = self.model.strip()
        self.base_url = self.base_url.strip()

        if not self.runtime:
            raise RuntimeConfigError(
                "Runtime type cannot be empty."
            )

        if not self.provider:
            raise RuntimeConfigError(
                "Runtime provider cannot be empty."
            )

        if not self.model:
            raise RuntimeConfigError(
                "Runtime model cannot be empty."
            )

        if not self.base_url:
            raise RuntimeConfigError(
                "Runtime base URL cannot be empty."
            )

        if self.timeout <= 0:
            raise RuntimeConfigError(
                "Runtime timeout must be greater than zero."
            )

        if self.temperature < 0:
            raise RuntimeConfigError(
                "Temperature cannot be negative."
            )

        if self.max_tokens <= 0:
            raise RuntimeConfigError(
                "max_tokens must be greater than zero."
            )

        if self.max_reasoning_steps <= 0:
            raise RuntimeConfigError(
                "max_reasoning_steps must be greater than zero."
            )

        if self.runtime_name is None:
            self.runtime_name = (
                f"{self.provider}:{self.model}"
            )

    @classmethod
    def from_environment(cls) -> "RuntimeConfig":
        """
        Build configuration from environment variables.

        Existing BRAIN_* variables are supported so the new runtime
        configuration remains compatible with the current application.
        """

        runtime = (
            os.getenv("MODEL_RUNTIME")
            or os.getenv("BRAIN_PROVIDER")
            or "openai_compatible"
        )

        provider = (
            os.getenv("MODEL_PROVIDER")
            or cls._default_provider(runtime)
        )

        model = (
            os.getenv("MODEL_NAME")
            or os.getenv("BRAIN_MODEL")
            or "local-model"
        )

        base_url = (
            os.getenv("MODEL_BASE_URL")
            or os.getenv("BRAIN_BASE_URL")
            or "http://127.0.0.1:8080/v1"
        )

        api_key = (
            os.getenv("MODEL_API_KEY")
            or os.getenv("BRAIN_API_KEY")
        )

        timeout = cls._float_environment(
            "MODEL_TIMEOUT",
            "BRAIN_TIMEOUT",
            300.0,
        )

        temperature = cls._float_environment(
            "MODEL_TEMPERATURE",
            "BRAIN_TEMPERATURE",
            0.2,
        )

        max_tokens = cls._int_environment(
            "MODEL_MAX_TOKENS",
            "BRAIN_MAX_TOKENS",
            4096,
        )

        max_reasoning_steps = cls._int_environment(
            "MODEL_MAX_REASONING_STEPS",
            "BRAIN_MAX_REASONING_STEPS",
            24,
        )

        runtime_name = (
            os.getenv("MODEL_RUNTIME_NAME")
            or None
        )

        hardware = (
            os.getenv("MODEL_HARDWARE")
            or os.getenv("BRAIN_HARDWARE")
            or None
        )

        local = cls._bool_environment(
            "MODEL_LOCAL",
            True,
        )

        return cls(
            runtime=runtime,
            provider=provider,
            model=model,
            base_url=base_url,
            api_key=api_key,
            timeout=timeout,
            temperature=temperature,
            max_tokens=max_tokens,
            max_reasoning_steps=max_reasoning_steps,
            runtime_name=runtime_name,
            hardware=hardware,
            local=local,
        )

    def to_dict(
        self,
        include_secret: bool = False,
    ) -> Dict[str, Any]:
        """
        Convert configuration to a dictionary.

        API keys are hidden by default.
        """

        data: Dict[str, Any] = {
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
            data["api_key"] = self.api_key

        return data

    def public_dict(self) -> Dict[str, Any]:
        """
        Return a safe configuration representation suitable for
        status endpoints and diagnostics.
        """

        return self.to_dict(include_secret=False)

    def with_overrides(
        self,
        **overrides: Any,
    ) -> "RuntimeConfig":
        """
        Create a new RuntimeConfig with selected values overridden.

        The existing configuration object is not modified.
        """

        values = self.to_dict(include_secret=True)

        values.update(overrides)

        return RuntimeConfig(
            runtime=values["runtime"],
            provider=values["provider"],
            model=values["model"],
            base_url=values["base_url"],
            api_key=values.get("api_key"),
            timeout=values["timeout"],
            temperature=values["temperature"],
            max_tokens=values["max_tokens"],
            max_reasoning_steps=values["max_reasoning_steps"],
            runtime_name=values.get("runtime_name"),
            hardware=values.get("hardware"),
            local=values["local"],
            metadata=dict(values.get("metadata") or {}),
        )

    def is_local(self) -> bool:
        """
        Return whether the configured runtime is intended to be local.
        """

        return self.local

    def has_api_key(self) -> bool:
        """
        Return whether an API key has been configured.
        """

        return bool(self.api_key)

    @staticmethod
    def _default_provider(runtime: str) -> str:
        normalized = runtime.strip().lower()

        if normalized in {
            "llama_cpp",
            "llama-server",
            "llamacpp",
        }:
            return "llama.cpp"

        if normalized == "local":
            return "local"

        return "openai_compatible"

    @staticmethod
    def _float_environment(
        primary: str,
        secondary: str,
        default: float,
    ) -> float:
        value = os.getenv(primary)

        if value is None:
            value = os.getenv(secondary)

        if value is None:
            return default

        try:
            return float(value)
        except ValueError as exc:
            raise RuntimeConfigError(
                f"Invalid numeric value for {primary}/{secondary}: "
                f"{value}"
            ) from exc

    @staticmethod
    def _int_environment(
        primary: str,
        secondary: str,
        default: int,
    ) -> int:
        value = os.getenv(primary)

        if value is None:
            value = os.getenv(secondary)

        if value is None:
            return default

        try:
            return int(value)
        except ValueError as exc:
            raise RuntimeConfigError(
                f"Invalid integer value for {primary}/{secondary}: "
                f"{value}"
            ) from exc

    @staticmethod
    def _bool_environment(
        name: str,
        default: bool,
    ) -> bool:
        value = os.getenv(name)

        if value is None:
            return default

        normalized = value.strip().lower()

        if normalized in {
            "1",
            "true",
            "yes",
            "on",
        }:
            return True

        if normalized in {
            "0",
            "false",
            "no",
            "off",
        }:
            return False

        raise RuntimeConfigError(
            f"Invalid boolean value for {name}: {value}"
        )


def load_runtime_config() -> RuntimeConfig:
    """
    Load the current runtime configuration from the environment.
    """

    return RuntimeConfig.from_environment()