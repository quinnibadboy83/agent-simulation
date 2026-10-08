"""
Runtime Integration Smoke Test
------------------------------

Structural test for the portable model-runtime architecture.

This test intentionally does not require a running model server.

Run from the repository root with:

    python -m core.runtime_integration_smoke_test
"""

from __future__ import annotations

import asyncio

from .brain_runtime import BrainRuntime
from .llm_runtime_adapter import LLMRuntimeAdapter
from .model_runtime import (
    ModelRequest,
    ModelResponse,
    ModelRuntimeInfo,
)
from .openai_compatible_runtime import (
    OpenAICompatibleRuntime,
)
from .runtime_config import RuntimeConfig
from .runtime_diagnostics import RuntimeDiagnostics
from .runtime_factory import RuntimeFactory
from .runtime_manager import RuntimeManager


class FakeLLMClient:
    """
    Minimal fake client used to verify adapter construction.

    No network calls are made.
    """

    async def health(self):
        return {
            "status": "ready",
            "provider": "fake",
            "model": "fake-model",
        }

    async def chat(
        self,
        messages,
        tools=None,
        temperature=0.2,
        max_tokens=1024,
    ):
        return {
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": "test",
                    },
                    "finish_reason": "stop",
                }
            ],
            "model": "fake-model",
            "usage": {},
        }

    def extract_text(self, response):
        return "test"

    def extract_tool_calls(self, response):
        return []

    def extract_finish_reason(self, response):
        return "stop"

    def extract_usage(self, response):
        return {}

    async def close(self):
        return None


def test_runtime_config():
    config = RuntimeConfig(
        runtime="llama_cpp",
        provider="llama.cpp",
        model="qwen3-8b",
        base_url="http://127.0.0.1:8080/v1",
        timeout=30,
        temperature=0.2,
        max_tokens=4096,
        max_reasoning_steps=24,
        local=True,
    )

    data = config.public_dict()

    assert data["runtime"] == "llama_cpp"
    assert data["provider"] == "llama.cpp"
    assert data["model"] == "qwen3-8b"
    assert data["local"] is True
    assert "api_key" not in data

    print("[PASS] RuntimeConfig")


def test_runtime_factory():
    runtime = RuntimeFactory.create(
        runtime_type="llama_cpp",
        base_url="http://127.0.0.1:8080/v1",
        model="qwen3-8b",
        provider="llama.cpp",
        timeout=30,
    )

    assert isinstance(
        runtime,
        OpenAICompatibleRuntime,
    )

    description = runtime.describe()

    assert isinstance(
        description,
        ModelRuntimeInfo,
    )

    assert description.model == "qwen3-8b"

    print("[PASS] RuntimeFactory")


def test_runtime_manager():
    config = RuntimeConfig(
        runtime="llama_cpp",
        provider="llama.cpp",
        model="qwen3-8b",
        base_url="http://127.0.0.1:8080/v1",
        timeout=30,
    )

    manager = RuntimeManager(
        config=config
    )

    assert manager.runtime is None
    assert manager.started is False

    runtime = manager.start()

    assert isinstance(
        runtime,
        OpenAICompatibleRuntime,
    )

    assert manager.started is True

    status = manager.status()

    assert status["started"] is True
    assert status["runtime"]["active"] is True

    print("[PASS] RuntimeManager")

    return manager


def test_runtime_diagnostics(
    manager: RuntimeManager,
):
    diagnostics = RuntimeDiagnostics(
        manager
    )

    configuration = diagnostics.configuration()

    assert configuration["model"] == "qwen3-8b"
    assert "api_key" not in configuration

    status = diagnostics.status()

    assert "runtime_manager" in status
    assert "configuration" in status

    print("[PASS] RuntimeDiagnostics")


def test_brain_runtime():
    brain_runtime = BrainRuntime()

    assert brain_runtime.using_runtime is False
    assert brain_runtime.using_legacy_llm is False

    print("[PASS] BrainRuntime")


def test_llm_runtime_adapter():
    fake_client = FakeLLMClient()

    adapter = LLMRuntimeAdapter(
        client=fake_client,
    )

    description = adapter.describe()

    assert isinstance(
        description,
        ModelRuntimeInfo,
    )

    assert description.provider

    print("[PASS] LLMRuntimeAdapter")


def test_request_response_models():
    request = ModelRequest(
        messages=[
            {
                "role": "user",
                "content": "test",
            }
        ],
        tools=[],
        temperature=0.2,
        max_tokens=100,
    )

    response = ModelResponse(
        content="test",
        reasoning_content="",
        tool_calls=[],
        finish_reason="stop",
        model="test-model",
        usage={},
        raw_response={},
        metadata={},
    )

    assert request.to_dict()["messages"]
    assert response.to_dict()["content"] == "test"

    print("[PASS] ModelRequest / ModelResponse")


async def cleanup(
    manager: RuntimeManager,
):
    await manager.stop()


def main():
    print()
    print("=" * 60)
    print("Agent Simulation Engine")
    print("Runtime Integration Smoke Test")
    print("=" * 60)
    print()

    test_runtime_config()
    test_runtime_factory()

    manager = test_runtime_manager()

    try:
        test_runtime_diagnostics(
            manager
        )

        test_brain_runtime()
        test_llm_runtime_adapter()
        test_request_response_models()

    finally:
        asyncio.run(
            cleanup(manager)
        )

    print()
    print("=" * 60)
    print("ALL STRUCTURAL TESTS PASSED")
    print("=" * 60)
    print()


if __name__ == "__main__":
    main()