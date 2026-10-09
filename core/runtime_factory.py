"""Construct a configured ModelRuntime without binding the app to a provider."""
from __future__ import annotations

from typing import Any, Optional

from .model_runtime import ModelRuntime, ModelRuntimeError
from .openai_compatible_runtime import OpenAICompatibleRuntime
from .development_runtime import DevelopmentModelRuntime
from .runtime_config import RuntimeConfig


class RuntimeFactoryError(ModelRuntimeError):
    """Raised when a runtime cannot be constructed."""


class RuntimeFactory:
    DEFAULT_RUNTIME = "openai_compatible"
    DEFAULT_BASE_URL = "http://127.0.0.1:8080/v1"
    DEFAULT_TIMEOUT = 300.0

    SUPPORTED_RUNTIMES = {
        "development",
        "dev",
        "test",
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
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        provider: Optional[str] = None,
        api_key: Optional[str] = None,
        timeout: Optional[float] = None,
        runtime_name: Optional[str] = None,
        config: Optional[RuntimeConfig] = None,
        **kwargs: Any,
    ) -> ModelRuntime:
        cfg = config or RuntimeConfig.from_environment()

        kind = str(
            runtime_type or cfg.runtime or cls.DEFAULT_RUNTIME
        ).strip().lower()

        if kind not in cls.SUPPORTED_RUNTIMES:
            raise RuntimeFactoryError(
                f"Unsupported runtime '{kind}'. Supported: "
                f"{', '.join(sorted(cls.SUPPORTED_RUNTIMES))}"
            )

        selected_model = model or cfg.model
        selected_provider = provider or cfg.provider
        selected_name = runtime_name or cfg.runtime_name

        if kind in {"development", "dev", "test"}:
            return DevelopmentModelRuntime(
                model=selected_model,
                runtime_name=(
                    selected_name or f"development:{selected_model}"
                ),
                provider=selected_provider or "development",
            )

        return OpenAICompatibleRuntime(
            base_url=(
                base_url or cfg.base_url or cls.DEFAULT_BASE_URL
            ),
            model=selected_model,
            provider=selected_provider,
            api_key=cfg.api_key if api_key is None else api_key,
            timeout=cfg.timeout if timeout is None else timeout,
            runtime_name=selected_name,
        )

    @classmethod
    def from_environment(cls) -> ModelRuntime:
        config = RuntimeConfig.from_environment()
        return cls.create(config=config)