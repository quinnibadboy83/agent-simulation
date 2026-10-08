"""
Runtime Bootstrap Smoke Test
----------------------------

Structural tests for the runtime bootstrap layer.

These tests deliberately do not perform live model inference or network
requests. They verify that the runtime configuration, manager,
diagnostics, and bootstrap layers work together correctly.
"""

from __future__ import annotations

import asyncio
import os

from .runtime_bootstrap import (
    RuntimeBootstrap,
    RuntimeBootstrapError,
    prepare_runtime_application,
)
from .runtime_config import RuntimeConfig
from .runtime_diagnostics import RuntimeDiagnostics
from .runtime_manager import RuntimeManager


def test_runtime_config() -> None:
    """Verify runtime configuration can be constructed safely."""

    config = RuntimeConfig(
        runtime="openai_compatible",
        provider="test",
        model="test-model",
        base_url="http://127.0.0.1:8080/v1",
        api_key=None,
        timeout=30.0,
        temperature=0.2,
        max_tokens=512,
        max_reasoning_steps=8,
        runtime_name="bootstrap-test",
        hardware="test",
        local=True,
    )

    assert config.runtime == "openai_compatible"
    assert config.provider == "test"
    assert config.model == "test-model"
    assert config.local is True

    public = config.public_dict()

    assert "api_key" not in public


def test_runtime_manager() -> None:
    """Verify the runtime manager can be created without starting inference."""

    config = RuntimeConfig(
        runtime="openai_compatible",
        provider="test",
        model="test-model",
        base_url="http://127.0.0.1:8080/v1",
        api_key=None,
        timeout=30.0,
        temperature=0.2,
        max_tokens=512,
        max_reasoning_steps=8,
        runtime_name="manager-test",
        hardware="test",
        local=True,
    )

    manager = RuntimeManager(config=config)

    assert manager.runtime is None
    assert manager.started is False

    status = manager.status()

    assert isinstance(status, dict)
    assert status["started"] is False


def test_runtime_diagnostics() -> None:
    """Verify diagnostics can be attached to a runtime manager."""

    config = RuntimeConfig(
        runtime="openai_compatible",
        provider="test",
        model="test-model",
        base_url="http://127.0.0.1:8080/v1",
        api_key=None,
        timeout=30.0,
        temperature=0.2,
        max_tokens=512,
        max_reasoning_steps=8,
        runtime_name="diagnostics-test",
        hardware="test",
        local=True,
    )

    manager = RuntimeManager(config=config)
    diagnostics = RuntimeDiagnostics(manager)

    configuration = diagnostics.configuration()

    assert isinstance(configuration, dict)
    assert configuration["runtime"] == "openai_compatible"
    assert configuration["model"] == "test-model"


def test_bootstrap_prepare() -> None:
    """Verify bootstrap preparation does not start the runtime."""

    config = RuntimeConfig(
        runtime="openai_compatible",
        provider="test",
        model="test-model",
        base_url="http://127.0.0.1:8080/v1",
        api_key=None,
        timeout=30.0,
        temperature=0.2,
        max_tokens=512,
        max_reasoning_steps=8,
        runtime_name="prepare-test",
        hardware="test",
        local=True,
    )

    bootstrap = RuntimeBootstrap(config=config)

    application = bootstrap.prepare()

    assert application is bootstrap.application
    assert application.config is config
    assert application.manager is bootstrap.manager
    assert application.diagnostics is bootstrap.diagnostics
    assert application.manager.runtime is None


def test_bootstrap_application_status() -> None:
    """Verify safe application status output."""

    config = RuntimeConfig(
        runtime="openai_compatible",
        provider="test",
        model="test-model",
        base_url="http://127.0.0.1:8080/v1",
        api_key=None,
        timeout=30.0,
        temperature=0.2,
        max_tokens=512,
        max_reasoning_steps=8,
        runtime_name="status-test",
        hardware="test",
        local=True,
    )

    bootstrap = RuntimeBootstrap(config=config)
    application = bootstrap.prepare()

    status = application.status()

    assert isinstance(status, dict)
    assert "config" in status
    assert "manager" in status
    assert "runtime_active" in status
    assert status["runtime_active"] is False

    assert "api_key" not in status["config"]


def test_environment_is_not_modified() -> None:
    """Verify the smoke test does not alter runtime environment settings."""

    before = os.environ.get("MODEL_RUNTIME")

    config = RuntimeConfig(
        runtime="openai_compatible",
        provider="test",
        model="test-model",
        base_url="http://127.0.0.1:8080/v1",
        api_key=None,
        timeout=30.0,
        temperature=0.2,
        max_tokens=512,
        max_reasoning_steps=8,
        runtime_name="environment-test",
        hardware="test",
        local=True,
    )

    bootstrap = RuntimeBootstrap(config=config)
    bootstrap.prepare()

    after = os.environ.get("MODEL_RUNTIME")

    assert before == after


async def test_shutdown() -> None:
    """Verify bootstrap shutdown is safe before runtime startup."""

    config = RuntimeConfig(
        runtime="openai_compatible",
        provider="test",
        model="test-model",
        base_url="http://127.0.0.1:8080/v1",
        api_key=None,
        timeout=30.0,
        temperature=0.2,
        max_tokens=512,
        max_reasoning_steps=8,
        runtime_name="shutdown-test",
        hardware="test",
        local=True,
    )

    bootstrap = RuntimeBootstrap(config=config)

    await bootstrap.shutdown()

    assert bootstrap.manager.runtime is None


def test_prepare_helper() -> None:
    """Verify the module-level preparation helper."""

    config = RuntimeConfig(
        runtime="openai_compatible",
        provider="test",
        model="test-model",
        base_url="http://127.0.0.1:8080/v1",
        api_key=None,
        timeout=30.0,
        temperature=0.2,
        max_tokens=512,
        max_reasoning_steps=8,
        runtime_name="helper-test",
        hardware="test",
        local=True,
    )

    application = prepare_runtime_application(config=config)

    assert application.config is config
    assert application.manager.runtime is None


async def run_all_tests() -> None:
    """Run all bootstrap smoke tests."""

    test_runtime_config()
    test_runtime_manager()
    test_runtime_diagnostics()
    test_bootstrap_prepare()
    test_bootstrap_application_status()
    test_environment_is_not_modified()
    test_prepare_helper()

    await test_shutdown()


def main() -> None:
    """Run the complete structural test suite."""

    asyncio.run(run_all_tests())

    print("RUNTIME BOOTSTRAP STRUCTURAL TESTS PASSED")


if __name__ == "__main__":
    main()