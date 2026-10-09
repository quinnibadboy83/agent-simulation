"""Lifecycle manager for one shared model runtime."""
from __future__ import annotations

from typing import Any, Dict, Optional

from .model_runtime import ModelRuntime, ModelRuntimeInfo
from .runtime_config import RuntimeConfig
from .runtime_factory import RuntimeFactory


class RuntimeManagerError(RuntimeError):
    """Raised when runtime lifecycle management fails."""


class RuntimeManager:
    def __init__(
        self,
        config: Optional[RuntimeConfig] = None,
        runtime: Optional[ModelRuntime] = None,
    ) -> None:
        self.config = config or RuntimeConfig.from_environment()
        self._runtime = runtime
        self._started = runtime is not None
        self._last_error: Optional[str] = None

    @property
    def runtime(self) -> Optional[ModelRuntime]:
        return self._runtime

    @property
    def started(self) -> bool:
        return self._started

    def start(self) -> ModelRuntime:
        if self._runtime is not None:
            self._started = True
            return self._runtime

        try:
            self._runtime = RuntimeFactory.create(config=self.config)
            self._started = True
            self._last_error = None
            return self._runtime
        except Exception as exc:
            self._last_error = str(exc)
            raise RuntimeManagerError(
                f"Unable to start model runtime: {exc}"
            ) from exc

    def ensure_started(self) -> ModelRuntime:
        return (
            self._runtime
            if self._runtime is not None
            else self.start()
        )

    def health(self) -> Any:
        runtime = self.ensure_started()

        try:
            return runtime.health()
        except Exception as exc:
            self._last_error = str(exc)
            raise RuntimeManagerError(
                f"Runtime health check failed: {exc}"
            ) from exc

    def describe(self) -> Any:
        runtime = self.ensure_started()

        try:
            return runtime.describe()
        except Exception as exc:
            self._last_error = str(exc)
            raise RuntimeManagerError(
                f"Runtime description failed: {exc}"
            ) from exc

    def status(self) -> Dict[str, Any]:
        """Return a backwards-compatible, secret-free runtime status."""
        if self._runtime is not None:
            try:
                info = self._runtime.describe()

                if isinstance(info, ModelRuntimeInfo):
                    result = {
                        "active": True,
                        **info.to_dict(),
                    }
                elif isinstance(info, dict):
                    result = {
                        "active": True,
                        **dict(info),
                    }
                else:
                    result = {
                        "active": True,
                        "runtime": type(self._runtime).__name__,
                    }

                result["started"] = self._started
                result["configuration"] = self.config.public_dict()

                if self._last_error:
                    result["error"] = self._last_error

                return result

            except Exception as exc:
                error = str(exc)
        else:
            error = self._last_error

        return {
            "started": self._started,
            "active": False,
            "configuration": self.config.public_dict(),
            "runtime": {},
            "error": error,
        }

    def restart(self) -> ModelRuntime:
        self.stop()
        return self.start()

    def replace(self, runtime: ModelRuntime) -> ModelRuntime:
        if runtime is None:
            raise RuntimeManagerError(
                "Cannot replace runtime with None."
            )

        self.stop()
        self._runtime = runtime
        self._started = True
        self._last_error = None
        return runtime

    def stop(self) -> None:
        """Detach the runtime synchronously without leaking coroutines."""
        runtime, self._runtime = self._runtime, None
        self._started = False

        if runtime is None:
            return

        for method_name in ("close", "shutdown", "stop"):
            method = getattr(runtime, method_name, None)

            if not callable(method):
                continue

            try:
                result = method()

                if hasattr(result, "__await__"):
                    close_method = getattr(result, "close", None)
                    if callable(close_method):
                        close_method()

                break

            except Exception as exc:
                self._last_error = str(exc)
                break

    async def stop_async(self) -> None:
        """Stop the runtime and await asynchronous shutdown if supported."""
        runtime, self._runtime = self._runtime, None
        self._started = False

        if runtime is None:
            return

        for method_name in (
            "aclose",
            "async_shutdown",
            "close",
            "shutdown",
            "stop",
        ):
            method = getattr(runtime, method_name, None)

            if not callable(method):
                continue

            try:
                result = method()

                if hasattr(result, "__await__"):
                    await result

            except Exception as exc:
                self._last_error = str(exc)

            break

    def close(self) -> None:
        self.stop()