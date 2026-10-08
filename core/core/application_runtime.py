"""
Application Runtime
-------------------

Application-level access to the model runtime.

This module provides a stable bridge between the Agent Simulation
application and the portable model-runtime infrastructure.

The application can use this layer without knowing whether inference
is provided by llama.cpp, llama-server, another OpenAI-compatible local
runtime, desktop hardware, Android hardware, CPU, GPU, or another
supported backend.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from .runtime_bootstrap import (
    RuntimeApplication,
    RuntimeBootstrap,
)
from .runtime_config import RuntimeConfig


class ApplicationRuntimeError(RuntimeError):
    """Raised when application runtime operations fail."""


class ApplicationRuntime:
    """
    High-level runtime service for the Agent Simulation application.

    This class deliberately contains no agent authority, tool execution,
    payment logic, social-account logic, or approval logic.

    It only manages access to the model runtime.
    """

    def __init__(
        self,
        config: Optional[RuntimeConfig] = None,
    ) -> None:
        self.bootstrap = RuntimeBootstrap(
            config=config
        )

        self.application: Optional[
            RuntimeApplication
        ] = None

    @property
    def started(self) -> bool:
        """
        Return whether the application runtime is active.
        """

        return (
            self.application is not None
            and self.application.manager.runtime is not None
        )

    @property
    def runtime(self) -> Any:
        """
        Return the active runtime instance.

        Returns None when the runtime has not been started.
        """

        if self.application is None:
            return None

        return self.application.manager.runtime

    def prepare(self) -> RuntimeApplication:
        """
        Prepare runtime infrastructure without starting inference.
        """

        self.application = self.bootstrap.prepare()

        return self.application

    def start(self) -> RuntimeApplication:
        """
        Start the configured model runtime.
        """

        try:
            self.application = self.bootstrap.start()

            return self.application

        except Exception as exc:
            raise ApplicationRuntimeError(
                f"Application runtime startup failed: {exc}"
            ) from exc

    async def start_and_check(self) -> Dict[str, Any]:
        """
        Start the runtime and run its diagnostic suite.

        Returns a JSON-safe diagnostic report.
        """

        try:
            self.application = (
                self.bootstrap.application
            )

            report = (
                await self.bootstrap.start_and_check()
            )

            return report.to_dict()

        except Exception as exc:
            raise ApplicationRuntimeError(
                f"Application runtime health check failed: {exc}"
            ) from exc

    def status(self) -> Dict[str, Any]:
        """
        Return safe runtime status.

        Secrets such as API keys are never returned.
        """

        if self.application is None:
            return {
                "prepared": False,
                "started": False,
                "runtime_active": False,
            }

        status = self.application.status()

        status["prepared"] = True
        status["started"] = self.started

        return status

    async def health(self) -> Dict[str, Any]:
        """
        Run runtime diagnostics.

        The runtime is started if necessary.
        """

        if self.application is None:
            self.prepare()

        try:
            report = await self.application.health()

            return report.to_dict()

        except Exception as exc:
            raise ApplicationRuntimeError(
                f"Application runtime health check failed: {exc}"
            ) from exc

    async def shutdown(self) -> None:
        """
        Shut down the active model runtime safely.
        """

        if self.application is None:
            return

        try:
            await self.application.shutdown()

        finally:
            self.application = None

    async def restart(
        self,
        config: Optional[RuntimeConfig] = None,
    ) -> RuntimeApplication:
        """
        Restart the runtime.

        If a new configuration is supplied, it becomes the active
        runtime configuration.
        """

        await self.shutdown()

        self.bootstrap = RuntimeBootstrap(
            config=config
        )

        return self.start()


def create_application_runtime(
    config: Optional[RuntimeConfig] = None,
) -> ApplicationRuntime:
    """
    Create an application runtime service.

    The runtime is prepared lazily and is not started automatically.
    """

    return ApplicationRuntime(
        config=config
    )