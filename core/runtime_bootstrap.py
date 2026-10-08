"""
Runtime Bootstrap
-----------------

Application-level bootstrap for the model runtime.

This module creates the runtime infrastructure required by the Agent
Simulation Engine without coupling the application to a specific
model, operating system, server, or hardware platform.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

from .runtime_config import RuntimeConfig
from .runtime_diagnostics import (
    RuntimeDiagnosticReport,
    RuntimeDiagnostics,
)
from .runtime_manager import RuntimeManager


class RuntimeBootstrapError(RuntimeError):
    """Raised when runtime bootstrap fails."""


@dataclass
class RuntimeApplication:
    """
    Container for the application's runtime infrastructure.

    This object deliberately contains infrastructure only. It does not
    contain agents, tools, memory, or application authority.
    """

    config: RuntimeConfig
    manager: RuntimeManager
    diagnostics: RuntimeDiagnostics

    def status(self) -> Dict[str, Any]:
        """
        Return safe runtime application status.
        """

        return {
            "config": self.config.public_dict(),
            "manager": self.manager.status(),
            "runtime_active": (
                self.manager.runtime is not None
            ),
        }

    async def health(
        self,
    ) -> RuntimeDiagnosticReport:
        """
        Run the complete runtime diagnostic suite.
        """

        return await self.diagnostics.run()

    async def shutdown(self) -> None:
        """
        Shut down the active runtime.
        """

        await self.manager.stop()


class RuntimeBootstrap:
    """
    Creates and manages the application's runtime infrastructure.
    """

    def __init__(
        self,
        config: Optional[RuntimeConfig] = None,
    ) -> None:
        self.config = (
            config
            or RuntimeConfig.from_environment()
        )

        self.manager = RuntimeManager(
            config=self.config
        )

        self.diagnostics = RuntimeDiagnostics(
            self.manager
        )

        self.application = RuntimeApplication(
            config=self.config,
            manager=self.manager,
            diagnostics=self.diagnostics,
        )

    def start(
        self,
    ) -> RuntimeApplication:
        """
        Start the configured runtime infrastructure.

        Runtime creation is performed here explicitly rather than
        during object construction.
        """

        try:
            self.manager.start()

        except Exception as exc:
            raise RuntimeBootstrapError(
                f"Runtime bootstrap failed: {exc}"
            ) from exc

        return self.application

    def prepare(
        self,
    ) -> RuntimeApplication:
        """
        Prepare runtime infrastructure without starting inference.

        This creates configuration, manager and diagnostics objects but
        leaves actual runtime startup lazy.
        """

        return self.application

    async def start_and_check(
        self,
    ) -> RuntimeDiagnosticReport:
        """
        Start the runtime and immediately perform diagnostics.
        """

        self.start()

        try:
            return await self.diagnostics.run()

        except Exception as exc:
            raise RuntimeBootstrapError(
                f"Runtime diagnostic startup check failed: {exc}"
            ) from exc

    async def shutdown(self) -> None:
        """
        Shut down the runtime.
        """

        await self.manager.stop()


def create_runtime_application(
    config: Optional[RuntimeConfig] = None,
) -> RuntimeApplication:
    """
    Create and start the runtime application.
    """

    bootstrap = RuntimeBootstrap(
        config=config
    )

    return bootstrap.start()


def prepare_runtime_application(
    config: Optional[RuntimeConfig] = None,
) -> RuntimeApplication:
    """
    Create runtime infrastructure without starting the model runtime.
    """

    bootstrap = RuntimeBootstrap(
        config=config
    )

    return bootstrap.prepare()