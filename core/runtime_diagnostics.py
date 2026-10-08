"""
Runtime Diagnostics
-------------------

Diagnostic and health-reporting layer for the Agent Simulation Engine.

This module performs runtime checks without giving the model any
application authority.

It is intentionally independent from agent reasoning.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .model_runtime import ModelRuntime, ModelRuntimeInfo
from .runtime_manager import RuntimeManager


class RuntimeDiagnosticsError(RuntimeError):
    """Raised when runtime diagnostics cannot be completed."""


@dataclass
class RuntimeDiagnosticResult:
    """Result of a single runtime diagnostic check."""

    name: str
    status: str
    message: str
    details: Dict[str, Any] = field(
        default_factory=dict
    )

    @property
    def passed(self) -> bool:
        return self.status == "ok"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "status": self.status,
            "message": self.message,
            "details": dict(self.details),
            "passed": self.passed,
        }


@dataclass
class RuntimeDiagnosticReport:
    """Complete runtime diagnostic report."""

    timestamp: str
    runtime: Dict[str, Any]
    checks: List[RuntimeDiagnosticResult]
    healthy: bool

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "runtime": dict(self.runtime),
            "checks": [
                check.to_dict()
                for check in self.checks
            ],
            "healthy": self.healthy,
        }


class RuntimeDiagnostics:
    """
    Performs configuration, availability and health diagnostics
    against the active ModelRuntime.
    """

    def __init__(
        self,
        runtime_manager: RuntimeManager,
    ) -> None:
        if not isinstance(
            runtime_manager,
            RuntimeManager,
        ):
            raise RuntimeDiagnosticsError(
                "runtime_manager must be a RuntimeManager."
            )

        self.runtime_manager = runtime_manager

    async def run(
        self,
    ) -> RuntimeDiagnosticReport:
        """
        Run all available runtime diagnostics.
        """

        timestamp = datetime.now(
            timezone.utc
        ).isoformat()

        checks: List[
            RuntimeDiagnosticResult
        ] = []

        configuration = (
            self.runtime_manager.config.public_dict()
        )

        checks.append(
            self._check_configuration(
                configuration
            )
        )

        runtime = self.runtime_manager.runtime

        if runtime is None:
            try:
                runtime = (
                    self.runtime_manager.ensure_started()
                )

            except Exception as exc:
                checks.append(
                    RuntimeDiagnosticResult(
                        name="runtime_startup",
                        status="error",
                        message=(
                            "Runtime could not be started."
                        ),
                        details={
                            "error": str(exc),
                        },
                    )
                )

                return RuntimeDiagnosticReport(
                    timestamp=timestamp,
                    runtime=configuration,
                    checks=checks,
                    healthy=False,
                )

        checks.append(
            self._check_runtime_interface(
                runtime
            )
        )

        description_check = (
            self._check_description(
                runtime
            )
        )

        checks.append(
            description_check
        )

        try:
            health = await (
                self.runtime_manager.health()
            )

            checks.append(
                self._check_health(
                    health
                )
            )

            runtime_info = (
                health.to_dict()
                if isinstance(
                    health,
                    ModelRuntimeInfo,
                )
                else {}
            )

        except Exception as exc:
            checks.append(
                RuntimeDiagnosticResult(
                    name="runtime_health",
                    status="error",
                    message=(
                        "Runtime health check failed."
                    ),
                    details={
                        "error": str(exc),
                    },
                )
            )

            runtime_info = {}

        healthy = all(
            check.passed
            for check in checks
        )

        return RuntimeDiagnosticReport(
            timestamp=timestamp,
            runtime={
                **configuration,
                **runtime_info,
            },
            checks=checks,
            healthy=healthy,
        )

    def configuration(
        self,
    ) -> Dict[str, Any]:
        """
        Return safe runtime configuration.
        """

        return (
            self.runtime_manager
            .config
            .public_dict()
        )

    def status(
        self,
    ) -> Dict[str, Any]:
        """
        Return non-network diagnostic status.

        Unlike run(), this method does not perform a health request.
        """

        return {
            "runtime_manager": (
                self.runtime_manager.status()
            ),
            "configuration": (
                self.configuration()
            ),
        }

    @staticmethod
    def _check_configuration(
        configuration: Dict[str, Any],
    ) -> RuntimeDiagnosticResult:
        required = [
            "runtime",
            "provider",
            "model",
            "base_url",
        ]

        missing = [
            key
            for key in required
            if not configuration.get(key)
        ]

        if missing:
            return RuntimeDiagnosticResult(
                name="configuration",
                status="error",
                message=(
                    "Runtime configuration is incomplete."
                ),
                details={
                    "missing": missing,
                },
            )

        return RuntimeDiagnosticResult(
            name="configuration",
            status="ok",
            message=(
                "Runtime configuration is valid."
            ),
            details={
                "runtime": configuration["runtime"],
                "provider": configuration["provider"],
                "model": configuration["model"],
                "local": configuration.get(
                    "local",
                    False,
                ),
                "api_key_configured": configuration.get(
                    "api_key_configured",
                    False,
                ),
            },
        )

    @staticmethod
    def _check_runtime_interface(
        runtime: ModelRuntime,
    ) -> RuntimeDiagnosticResult:
        required_methods = [
            "health",
            "generate",
            "describe",
        ]

        missing = [
            method
            for method in required_methods
            if not callable(
                getattr(
                    runtime,
                    method,
                    None,
                )
            )
        ]

        if missing:
            return RuntimeDiagnosticResult(
                name="runtime_interface",
                status="error",
                message=(
                    "Runtime does not implement the required "
                    "ModelRuntime interface."
                ),
                details={
                    "missing_methods": missing,
                },
            )

        return RuntimeDiagnosticResult(
            name="runtime_interface",
            status="ok",
            message=(
                "Runtime implements the ModelRuntime interface."
            ),
            details={
                "runtime_class": type(
                    runtime
                ).__name__,
            },
        )

    @staticmethod
    def _check_description(
        runtime: ModelRuntime,
    ) -> RuntimeDiagnosticResult:
        try:
            description = runtime.describe()

        except Exception as exc:
            return RuntimeDiagnosticResult(
                name="runtime_description",
                status="error",
                message=(
                    "Runtime description failed."
                ),
                details={
                    "error": str(exc),
                },
            )

        if isinstance(
            description,
            ModelRuntimeInfo,
        ):
            return RuntimeDiagnosticResult(
                name="runtime_description",
                status="ok",
                message=(
                    "Runtime description is available."
                ),
                details={
                    "runtime": description.runtime,
                    "provider": description.provider,
                    "model": description.model,
                    "endpoint": description.endpoint,
                    "capabilities": list(
                        description.capabilities
                    ),
                    "hardware": dict(
                        description.hardware
                    ),
                },
            )

        if isinstance(
            description,
            dict,
        ):
            return RuntimeDiagnosticResult(
                name="runtime_description",
                status="ok",
                message=(
                    "Runtime description is available."
                ),
                details={
                    "description": description,
                },
            )

        return RuntimeDiagnosticResult(
            name="runtime_description",
            status="error",
            message=(
                "Runtime returned an unsupported description type."
            ),
            details={
                "type": type(
                    description
                ).__name__,
            },
        )

    @staticmethod
    def _check_health(
        health: ModelRuntimeInfo,
    ) -> RuntimeDiagnosticResult:
        if not isinstance(
            health,
            ModelRuntimeInfo,
        ):
            return RuntimeDiagnosticResult(
                name="runtime_health",
                status="error",
                message=(
                    "Runtime health returned an invalid result."
                ),
                details={
                    "type": type(
                        health
                    ).__name__,
                },
            )

        if health.available:
            return RuntimeDiagnosticResult(
                name="runtime_health",
                status="ok",
                message=(
                    "Model runtime is available."
                ),
                details={
                    "runtime": health.runtime,
                    "provider": health.provider,
                    "model": health.model,
                    "endpoint": health.endpoint,
                    "capabilities": list(
                        health.capabilities
                    ),
                },
            )

        return RuntimeDiagnosticResult(
            name="runtime_health",
            status="error",
            message=(
                "Model runtime is unavailable."
            ),
            details={
                "runtime": health.runtime,
                "provider": health.provider,
                "model": health.model,
                "endpoint": health.endpoint,
                "error": health.error,
            },
        )


def create_runtime_diagnostics(
    runtime_manager: RuntimeManager,
) -> RuntimeDiagnostics:
    """
    Convenience factory for runtime diagnostics.
    """

    return RuntimeDiagnostics(
        runtime_manager
    )