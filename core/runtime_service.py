"""
Runtime Service
---------------

Application-facing service for model inference.

This layer keeps the rest of the Agent Simulation Engine independent
from RuntimeManager, RuntimeBootstrap, HTTP endpoints, llama.cpp,
llama-server, or any particular model provider.

The service exposes only the operations the application actually needs:

    generate()
    health()
    describe()
    status()
    shutdown()

Model output remains data. It does not receive application authority,
tool permissions, approval permissions, or access to the Creator Gate.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from .model_runtime import (
    ModelRequest,
    ModelResponse,
)
from .runtime_config import RuntimeConfig
from .runtime_manager import RuntimeManager


class RuntimeServiceError(RuntimeError):
    """Raised when runtime service operations fail."""


class RuntimeService:
    """
    Stable application-facing interface to the model runtime.

    The service owns access to inference but does not own agent
    authority or consequential actions.
    """

    def __init__(
        self,
        manager: RuntimeManager,
    ) -> None:
        if not isinstance(manager, RuntimeManager):
            raise TypeError(
                "manager must be a RuntimeManager"
            )

        self.manager = manager

    @property
    def started(self) -> bool:
        """Return whether a runtime instance is active."""

        return (
            self.manager.runtime is not None
            and self.manager.started
        )

    @property
    def runtime(self) -> Any:
        """Return the active runtime instance."""

        return self.manager.runtime

    @property
    def config(self) -> RuntimeConfig:
        """Return the active runtime configuration."""

        return self.manager.config

    def start(self) -> Any:
        """
        Start the configured model runtime.

        Runtime creation is delegated entirely to RuntimeManager.
        """

        try:
            return self.manager.start()

        except Exception as exc:
            raise RuntimeServiceError(
                f"Runtime service startup failed: {exc}"
            ) from exc

    def ensure_started(self) -> Any:
        """Ensure the runtime is available."""

        try:
            return self.manager.ensure_started()

        except Exception as exc:
            raise RuntimeServiceError(
                f"Runtime service could not start: {exc}"
            ) from exc

    async def generate(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ModelResponse:
        """
        Generate a model response.

        The returned ModelResponse is provider-neutral.

        This method does not execute tools and does not grant the model
        permission to perform any external action.
        """

        runtime = self.ensure_started()

        if runtime is None:
            raise RuntimeServiceError(
                "No model runtime is available"
            )

        request = ModelRequest(
            messages=messages,
            tools=tools or [],
            temperature=(
                self.config.temperature
                if temperature is None
                else temperature
            ),
            max_tokens=(
                self.config.max_tokens
                if max_tokens is None
                else max_tokens
            ),
            metadata=metadata or {},
        )

        try:
            return await runtime.generate(request)

        except Exception as exc:
            raise RuntimeServiceError(
                f"Model generation failed: {exc}"
            ) from exc

    async def health(self) -> Dict[str, Any]:
        """Return runtime health information."""

        try:
            report = await self.manager.health()

            if hasattr(report, "to_dict"):
                return report.to_dict()

            if isinstance(report, dict):
                return report

            return {
                "healthy": False,
                "error": "Unexpected health response",
                "details": str(report),
            }

        except Exception as exc:
            raise RuntimeServiceError(
                f"Runtime health check failed: {exc}"
            ) from exc

    def describe(self) -> Dict[str, Any]:
        """Return safe information about the active runtime."""

        try:
            description = self.manager.describe()

            if hasattr(description, "to_dict"):
                return description.to_dict()

            if isinstance(description, dict):
                return description

            return {
                "runtime": str(description),
            }

        except Exception as exc:
            raise RuntimeServiceError(
                f"Runtime description failed: {exc}"
            ) from exc

    def status(self) -> Dict[str, Any]:
        """Return safe runtime service status."""

        return {
            "started": self.started,
            "runtime_active": self.runtime is not None,
            "manager": self.manager.status(),
        }

    async def restart(
        self,
        config: Optional[RuntimeConfig] = None,
    ) -> Any:
        """Restart the underlying runtime."""

        try:
            return await self.manager.restart(
                config=config
            )

        except Exception as exc:
            raise RuntimeServiceError(
                f"Runtime service restart failed: {exc}"
            ) from exc

    async def shutdown(self) -> None:
        """Stop the underlying runtime safely."""

        try:
            await self.manager.stop()

        except Exception as exc:
            raise RuntimeServiceError(
                f"Runtime service shutdown failed: {exc}"
            ) from exc


def create_runtime_service(
    manager: RuntimeManager,
) -> RuntimeService:
    """Create an application runtime service."""

    return RuntimeService(
        manager=manager
    )