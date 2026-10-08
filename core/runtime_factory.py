"""
Runtime Factory
---------------

Creates the model runtime used by the Agent Simulation Engine.

The factory keeps the application independent from any particular
model provider, server, operating system, or hardware configuration.

Supported runtime types currently include:

- OpenAI-compatible HTTP runtimes
- llama.cpp / llama-server through its OpenAI-compatible API

The runtime itself remains behind the ModelRuntime abstraction.
"""

from __future__ import annotations

import os
from typing import Any, Dict, Optional

from .model_runtime import ModelRuntime, ModelRuntimeError
from .openai_compatible_runtime import OpenAICompatibleRuntime


class RuntimeFactoryError(ModelRuntimeError):
    """Raised when a model runtime cannot be created."""


class RuntimeFactory:
    """
    Creates ModelRuntime instances from configuration.

    Configuration can be supplied directly or read from environment
    variables.

    Supported runtime values:

        openai_compatible
        llama_cpp
        llama-server
        llamacpp
        local

    The OpenAI-compatible implementation is intentionally used for
    llama.cpp because llama-server exposes an OpenAI-compatible API.
    """

    DEFAULT_RUNTIME = "openai_compatible"
    DEFAULT_BASE_URL = "http://127.0.0.1:8080/v1"
    DEFAULT_TIMEOUT = 300.0

    SUPPORTED_RUNTIMES = {
        "openai_compatible",
        "llama_cpp",
        "llama-server",
        "llamacpp",
        "local",
    }

    @classmethod
    def create(
        cls,
        runtime_type: Optional[str] = None,
        *,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        provider: Optional[str] = None,
        api_key: Optional[str] = None,
        timeout: Optional[float] = None,
        runtime_name: Optional[str] = None,
        **kwargs: Any,
    ) -> ModelRuntime:
        """
        Create a configured ModelRuntime.

        Explicit arguments take priority over environment variables.
        """

        selected_type = (
            runtime_type
            or os.getenv("MODEL_RUNTIME")
            or os.getenv("BRAIN_PROVIDER")
            or cls.DEFAULT_RUNTIME
        )

        selected_type = selected_type.strip().lower()

        if selected_type not in cls.SUPPORTED_RUNTIMES:
            raise RuntimeFactoryError(
                "Unsupported model runtime: "
                f"{selected_type}. Supported runtimes: "
                f"{', '.join(sorted(cls.SUPPORTED_RUNTIMES))}"
            )

        selected_base_url = (
            base_url
            or os.getenv("MODEL_BASE_URL")
            or os.getenv("BRAIN_BASE_URL")
            or cls.DEFAULT_BASE_URL
        )

        selected_model = (
            model
            or os.getenv("MODEL_NAME")
            or os.getenv("BRAIN_MODEL")
            or "local-model"
        )

        selected_provider = (
            provider
            or os.getenv("MODEL_PROVIDER")
            or cls._default_provider(selected_type)
        )

        selected_api_key = (
            api_key
            if api_key is not None
            else os.getenv("MODEL_API_KEY")
            or os.getenv("BRAIN_API_KEY")
        )

        selected_timeout = cls._resolve_timeout(timeout)

        selected_runtime_name = (
            runtime_name
            or os.getenv("MODEL_RUNTIME_NAME")
            or f"{selected_provider}:{selected_model}"
        )

        if selected_type in {
            "openai_compatible",
            "llama_cpp",
            "llama-server",
            "llamacpp",
            "local",
        }:
            return OpenAICompatibleRuntime(
                base_url=selected_base_url,
                model=selected_model,
                provider=selected_provider,
                api_key=selected_api_key,
                timeout=selected_timeout,
                runtime_name=selected_runtime_name,
                **kwargs,
            )

        raise RuntimeFactoryError(
            f"No factory implementation exists for runtime: {selected_type}"
        )

    @classmethod
    def from_environment(cls) -> ModelRuntime:
        """
        Create a runtime entirely from environment configuration.
        """

        return cls.create()

    @classmethod
    def describe_configuration(cls) -> Dict[str, Any]:
        """
        Return the effective runtime configuration without exposing
        secret values.
        """

        runtime_type = (
            os.getenv("MODEL_RUNTIME")
            or os.getenv("BRAIN_PROVIDER")
            or cls.DEFAULT_RUNTIME
        )

        base_url = (
            os.getenv("MODEL_BASE_URL")
            or os.getenv("BRAIN_BASE_URL")
            or cls.DEFAULT_BASE_URL
        )

        model = (
            os.getenv("MODEL_NAME")
            or os.getenv("BRAIN_MODEL")
            or "local-model"
        )

        provider = (
            os.getenv("MODEL_PROVIDER")
            or cls._default_provider(runtime_type)
        )

        api_key_configured = bool(
            os.getenv("MODEL_API_KEY")
            or os.getenv("BRAIN_API_KEY")
        )

        timeout = cls._resolve_timeout(None)

        return {
            "runtime": runtime_type,
            "provider": provider,
            "model": model,
            "base_url": base_url,
            "timeout": timeout,
            "api_key_configured": api_key_configured,
        }

    @classmethod
    def _default_provider(cls, runtime_type: str) -> str:
        """
        Determine a sensible provider name from the runtime type.
        """

        normalized = runtime_type.strip().lower()

        if normalized in {
            "llama_cpp",
            "llama-server",
            "llamacpp",
        }:
            return "llama.cpp"

        if normalized == "local":
            return "local"

        return "openai_compatible"

    @classmethod
    def _resolve_timeout(cls, timeout: Optional[float]) -> float:
        """
        Resolve the HTTP timeout.

        Explicit timeout takes priority over environment configuration.
        """

        if timeout is not None:
            resolved = float(timeout)
        else:
            raw_timeout = (
                os.getenv("MODEL_TIMEOUT")
                or os.getenv("BRAIN_TIMEOUT")
            )

            if raw_timeout:
                try:
                    resolved = float(raw_timeout)
                except ValueError as exc:
                    raise RuntimeFactoryError(
                        f"Invalid model timeout: {raw_timeout}"
                    ) from exc
            else:
                resolved = cls.DEFAULT_TIMEOUT

        if resolved <= 0:
            raise RuntimeFactoryError(
                "Model runtime timeout must be greater than zero."
            )

        return resolved


def create_model_runtime(
    runtime_type: Optional[str] = None,
    **kwargs: Any,
) -> ModelRuntime:
    """
    Convenience function for creating a model runtime.

    Example:

        runtime = create_model_runtime(
            runtime_type="llama_cpp",
            base_url="http://127.0.0.1:8080/v1",
            model="qwen3-8b",
        )
    """

    return RuntimeFactory.create(
        runtime_type=runtime_type,
        **kwargs,
    )


def create_runtime_from_environment() -> ModelRuntime:
    """
    Convenience function for environment-based runtime creation.
    """

    return RuntimeFactory.from_environment()