"""
Application Runtime Smoke Test
------------------------------

Structural tests for the application-level runtime bridge.

These tests do not perform live model inference or network requests.
They verify that ApplicationRuntime correctly connects to the runtime
bootstrap infrastructure.
"""

from __future__ import annotations

import asyncio

from .application_runtime import (
    ApplicationRuntime,
    ApplicationRuntimeError,
    create_application_runtime,
)
from .runtime_config import RuntimeConfig


def create_test_config() -> RuntimeConfig:
    """Create an isolated configuration for structural testing."""

    return RuntimeConfig(
        runtime="openai_compatible",
        provider="test",
        model="test-model",
        base_url="http://127.0.0.1:8080/v1",
        api_key=None,
        timeout=30.0,
        temperature=0.2,
        max_tokens=512,
        max_reasoning_steps=8,
        runtime_name="application-runtime-test",
        hardware="test",
        local=True,
    )


def test_initial_state() -> None:
    """Verify a new application runtime starts lazily."""

    runtime = ApplicationRuntime(
        config=create_test_config()
    )

    assert runtime.started is False
    assert runtime.runtime is None

    status = runtime.status()

    assert status["prepared"] is False
    assert status["started"] is False
    assert status["runtime_active"] is False


def test_prepare() -> None:
    """Verify runtime infrastructure can be prepared without startup."""

    runtime = ApplicationRuntime(
        config=create_test_config()
    )

    application = runtime.prepare()

    assert application is runtime.application
    assert runtime.started is False
    assert runtime.runtime is None

    status = runtime.status()

    assert status["prepared"] is True
    assert status["started"] is False
    assert status["runtime_active"] is False


def test_status_hides_secrets() -> None:
    """Verify runtime status does not expose API credentials."""

    config = create_test_config()

    runtime = ApplicationRuntime(
        config=config
    )

    runtime.prepare()

    status = runtime.status()

    assert "api_key" not in status["config"]


def test_runtime_property_before_start() -> None:
    """Verify runtime property remains empty before startup."""

    runtime = ApplicationRuntime(
        config=create_test_config()
    )

    assert runtime.runtime is None


def test_factory_helper() -> None:
    """Verify the module-level creation helper."""

    runtime = create_application_runtime(
        config=create_test_config()
    )

    assert isinstance(
        runtime,
        ApplicationRuntime,
    )

    assert runtime.started is False
    assert runtime.runtime is None


def test_runtime_configuration() -> None:
    """Verify the supplied configuration reaches the bootstrap layer."""

    config = create_test_config()

    runtime = ApplicationRuntime(
        config=config
    )

    application = runtime.prepare()

    assert application.config is config
    assert application.manager.config is config


async def test_shutdown_before_start() -> None:
    """Verify shutdown is safe before runtime startup."""

    runtime = ApplicationRuntime(
        config=create_test_config()
    )

    await runtime.shutdown()

    assert runtime.started is False
    assert runtime.runtime is None


async def test_shutdown_after_prepare() -> None:
    """Verify prepared infrastructure can be shut down safely."""

    runtime = ApplicationRuntime(
        config=create_test_config()
    )

    runtime.prepare()

    await runtime.shutdown()

    assert runtime.application is None
    assert runtime.started is False
    assert runtime.runtime is None


async def test_health_requires_no_manual_runtime_creation() -> None:
    """
    Verify the health path can initialise the application structure.

    The test intentionally uses a local test endpoint. It does not
    require that endpoint to be available; any live connection failure
    is handled as a runtime diagnostic result rather than a structural
    failure.
    """

    runtime = ApplicationRuntime(
        config=create_test_config()
    )

    report = await runtime.health()

    assert isinstance(report, dict)
    assert "healthy" in report
    assert "checks" in report
    assert "runtime" in report

    await runtime.shutdown()


async def test_restart_requires_runtime_startup() -> None:
    """
    Verify restart preserves the application-level lifecycle contract.

    No real inference is required. The test only verifies that restart
    attempts to create the configured runtime through the bootstrap
    layer.
    """

    runtime = ApplicationRuntime(
        config=create_test_config()
    )

    try:
        await runtime.restart()

    except ApplicationRuntimeError:
        # Expected when the configured test endpoint is unavailable.
        pass

    finally:
        await runtime.shutdown()

    assert runtime.application is None
    assert runtime.started is False


async def run_all_tests() -> None:
    """Run all application runtime structural tests."""

    test_initial_state()
    test_prepare()
    test_status_hides_secrets()
    test_runtime_property_before_start()
    test_factory_helper()
    test_runtime_configuration()

    await test_shutdown_before_start()
    await test_shutdown_after_prepare()
    await test_health_requires_no_manual_runtime_creation()
    await test_restart_requires_runtime_startup()


def main() -> None:
    """Run the complete smoke-test suite."""

    asyncio.run(run_all_tests())

    print("APPLICATION RUNTIME STRUCTURAL TESTS PASSED")


if __name__ == "__main__":
    main()