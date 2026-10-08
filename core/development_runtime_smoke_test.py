"""
Development Runtime Smoke Test
------------------------------

Verifies that the deterministic development runtime can pass through
the same ModelRuntime / RuntimeFactory / RuntimeManager architecture
used by the real model runtimes.

No network connection is required.
"""

from __future__ import annotations

import asyncio
import json

from .model_runtime import ModelRequest
from .runtime_config import RuntimeConfig
from .runtime_factory import RuntimeFactory
from .runtime_manager import RuntimeManager


async def run_test() -> None:
    """Run the complete development-runtime test."""

    config = RuntimeConfig(
        runtime="development",
        provider="development",
        model="development-model",
        base_url="http://development.invalid/v1",
        api_key=None,
        timeout=30.0,
        temperature=0.0,
        max_tokens=64,
        max_reasoning_steps=4,
        runtime_name="development:test",
        hardware="development",
        local=True,
    )

    manager = RuntimeManager(
        config=config
    )

    try:
        # -------------------------------------------------------------
        # Factory
        # -------------------------------------------------------------

        runtime = RuntimeFactory.create(
            runtime_type="development",
            model="development-model",
            provider="development",
            runtime_name="development:test",
        )

        assert runtime is not None

        # -------------------------------------------------------------
        # Manager
        # -------------------------------------------------------------

        manager = RuntimeManager(
            config=config,
            runtime=runtime,
        )

        assert manager.started is True
        assert manager.runtime is runtime

        # -------------------------------------------------------------
        # Description
        # -------------------------------------------------------------

        description = runtime.describe()

        assert description.available is True
        assert description.runtime == "development"
        assert description.provider == "development"

        # -------------------------------------------------------------
        # Health
        # -------------------------------------------------------------

        health = await manager.health()

        assert health.available is True

        # -------------------------------------------------------------
        # Real runtime request
        # -------------------------------------------------------------

        request = ModelRequest(
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are testing the Agent Simulation "
                        "development runtime."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        "Test the runtime connection."
                    ),
                },
            ],
            tools=[],
            temperature=0.0,
            max_tokens=32,
            metadata={
                "test": True,
                "source": (
                    "development_runtime_smoke_test"
                ),
            },
        )

        response = await runtime.generate(
            request
        )

        assert response.content
        assert response.finish_reason == "stop"
        assert response.model == "development-model"

        # -------------------------------------------------------------
        # Output
        # -------------------------------------------------------------

        result = {
            "runtime": description.to_dict(),
            "health": health.to_dict(),
            "response": response.to_dict(),
            "manager": manager.status(),
        }

        print(
            json.dumps(
                result,
                indent=2,
                default=str,
            )
        )

        print()
        print(
            "DEVELOPMENT RUNTIME TEST PASSED"
        )

    finally:
        await manager.stop()


def main() -> None:
    """Run the test synchronously."""

    asyncio.run(
        run_test()
    )


if __name__ == "__main__":
    main()