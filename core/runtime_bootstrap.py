"""Application-level runtime bootstrap and diagnostics container."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

from .runtime_config import RuntimeConfig
from .runtime_manager import RuntimeManager
from .runtime_diagnostics import RuntimeDiagnosticReport, RuntimeDiagnostics


class RuntimeBootstrapError(RuntimeError):
    """Raised when runtime bootstrap fails."""


@dataclass
class RuntimeApplication:
    config: RuntimeConfig
    manager: RuntimeManager
    diagnostics: RuntimeDiagnostics

    def status(self) -> Dict[str, Any]:
        return {
            "config": self.config.public_dict(),
            "manager": self.manager.status(),
            "runtime_active": self.manager.runtime is not None,
        }

    async def health(self) -> RuntimeDiagnosticReport:
        return await self.diagnostics.run()

    async def shutdown(self) -> None:
        await self.manager.stop_async()


class RuntimeBootstrap:
    def __init__(
        self,
        config: Optional[RuntimeConfig] = None,
    ) -> None:
        self.config = config or RuntimeConfig.from_environment()
        self.manager = RuntimeManager(config=self.config)
        self.diagnostics = RuntimeDiagnostics(self.manager)
        self.application = RuntimeApplication(
            self.config,
            self.manager,
            self.diagnostics,
        )

    def start(self) -> RuntimeApplication:
        try:
            self.manager.start()
        except Exception as exc:
            raise RuntimeBootstrapError(
                f"Runtime bootstrap failed: {exc}"
            ) from exc

        return self.application

    def prepare(self) -> RuntimeApplication:
        return self.application

    async def start_and_check(self) -> RuntimeDiagnosticReport:
        self.start()

        try:
            return await self.diagnostics.run()
        except Exception as exc:
            raise RuntimeBootstrapError(
                f"Runtime diagnostic startup check failed: {exc}"
            ) from exc

    async def shutdown(self) -> None:
        await self.application.shutdown()


def create_runtime_application(
    config: Optional[RuntimeConfig] = None,
) -> RuntimeApplication:
    return RuntimeBootstrap(config=config).start()


def prepare_runtime_application(
    config: Optional[RuntimeConfig] = None,
) -> RuntimeApplication:
    return RuntimeBootstrap(config=config).prepare()