"""
Runtime Manager
---------------

Lifecycle management for the Agent Simulation Engine's model runtime.

The RuntimeManager sits above RuntimeConfig and RuntimeFactory and
provides one stable interface for:

- creating a runtime
- checking runtime health
- describing the active runtime
- replacing a runtime
- shutting a runtime down
- exposing safe runtime status

The manager does not contain agent reasoning logic.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from .model_runtime import ModelRuntime, ModelRuntimeInfo
from .runtime_config import RuntimeConfig
from .runtime_factory import RuntimeFactory


class RuntimeManagerError(RuntimeError):
    """Raised when runtime lifecycle management fails."""


class RuntimeManager:
    """
    Controls the lifecycle of the application's active model runtime.
    """

    def __init__(
        self,
        config: Optional[RuntimeConfig] = None,
        runtime: Optional[ModelRuntime] = None,
    ) -> None:
        self.config = config or RuntimeConfig.from_environment()
        self._runtime = runtime
        self._started = runtime is not None

    @property
    def runtime(self) -> Optional[ModelRuntime]:
        """Return the currently active runtime."""

        return self._runtime

    @property
    def started(self) -> bool:
        """Return whether a runtime is currently active."""

        return self._started and self._runtime is not None

    def start(self) -> ModelRuntime:
        """
        Create and activate the configured runtime.

        If a runtime is already active, it is returned unchanged.
        """

        if self._runtime is not None:
            self._started = True
            return self._runtime

        try:
            self._runtime = RuntimeFactory.create(
                runtime_type=self.config.runtime,
                base_url=self.config.base_url,
                model=self.config.model,
                provider=self.config.provider,
                api_key=self.config.api_key,
                timeout=self.config.timeout,
                runtime_name=self.config.runtime_name,
            )
        except Exception as exc:
            raise RuntimeManagerError(
                f"Failed to create model runtime: {exc}"
            ) from exc

        self._started = True

        return self._runtime

    def ensure_started(self) -> ModelRuntime:
        """
        Return the active runtime, creating it if necessary.
        """

        if self._runtime is None:
            return self.start()

        self._started = True

        return self._runtime

    async def health(self) -> ModelRuntimeInfo:
        """
        Check the active runtime.

        The runtime is created automatically if necessary.
        """

        runtime = self.ensure_started()

        try:
            return await runtime.health()
        except Exception as exc:
            raise RuntimeManagerError(
                f"Runtime health check failed: {exc}"
            ) from exc

    def describe(self) -> ModelRuntimeInfo:
        """
        Return static information about the active runtime.
        """

        runtime = self.ensure_started()

        try:
            return runtime.describe()
        except Exception as exc:
            raise RuntimeManagerError(
                f"Unable to describe runtime: {exc}"
            ) from exc

    def status(self) -> Dict[str, Any]:
        """
        Return safe runtime status information.

        This method does not perform a network health check.
        """

        runtime_status: Dict[str, Any]

        if self._runtime is None:
            runtime_status = {
                "active": False,
                "runtime": None,
            }
        else:
            try:
                description = self._runtime.describe()

                if isinstance(description, ModelRuntimeInfo):
                    runtime_status = {
                        "active": True,
                        **description.to_dict(),
                    }
                elif isinstance(description, dict):
                    runtime_status = {
                        "active": True,
                        **description,
                    }
                else:
                    runtime_status = {
                        "active": True,
                        "runtime": type(
                            self._runtime
                        ).__name__,
                    }

            except Exception as exc:
                runtime_status = {
                    "active": True,
                    "runtime": type(
                        self._runtime
                    ).__name__,
                    "description_error": str(exc),
                }

        return {
            "started": self.started,
            "configuration": self.config.public_dict(),
            "runtime": runtime_status,
        }

    async def restart(
        self,
        config: Optional[RuntimeConfig] = None,
    ) -> ModelRuntime:
        """
        Shut down the current runtime and create a new one.

        An optional configuration can replace the current configuration.
        """

        await self.stop()

        if config is not None:
            self.config = config

        return self.start()

    async def replace(
        self,
        runtime: ModelRuntime,
    ) -> ModelRuntime:
        """
        Replace the active runtime with an externally-created runtime.

        This is useful for future hardware-specific runtimes such as
        Android, desktop GPU, NPU, or embedded runtimes.
        """

        if runtime is None:
            raise RuntimeManagerError(
                "Replacement runtime cannot be None."
            )

        await self.stop()

        self._runtime = runtime
        self._started = True

        return runtime

    async def stop(self) -> None:
        """
        Shut down the active runtime if it provides a close method.
        """

        runtime = self._runtime

        self._runtime = None
        self._started = False

        if runtime is None:
            return

        close = getattr(runtime, "close", None)

        if close is None:
            return

        try:
            result = close()

            if hasattr(result, "__await__"):
                await result

        except Exception as exc:
            raise RuntimeManagerError(
                f"Failed to close model runtime: {exc}"
            ) from exc

    async def close(self) -> None:
        """
        Alias for stop().
        """

        await self.stop()


def create_runtime_manager(
    config: Optional[RuntimeConfig] = None,
) -> RuntimeManager:
    """
    Create a RuntimeManager.

    The runtime itself is created lazily when start(), health(),
    describe(), or ensure_started() is called.
    """

    return RuntimeManager(config=config)