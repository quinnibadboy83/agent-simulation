"""
Live Runtime Probe
------------------

Performs a real model-runtime connectivity and inference test.

Unlike the structural smoke tests, this module intentionally contacts
the configured model runtime.

It does not execute tools, perform external actions, or modify agents.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any, Dict

from .model_runtime import ModelRequest
from .runtime_config import RuntimeConfig
from .runtime_factory import RuntimeFactory
from .runtime_manager import RuntimeManager


def build_test_request(config: RuntimeConfig) -> ModelRequest:
    """Create a minimal safe inference request."""

    return ModelRequest(
        messages=[
            {
                "role": "system",
                "content": (
                    "You are performing a runtime connectivity test. "
                    "Answer briefly."
                ),
            },
            {
                "role": "user",
                "content": (
                    "Reply with exactly: "
                    "AGENT RUNTIME ONLINE"
                ),
            },
        ],
        tools=[],
        temperature=0.0,
        max_tokens=min(config.max_tokens, 32),
        metadata={
            "source": "live_runtime_probe",
            "purpose": "connectivity_test",
        },
    )


async def run_probe() -> Dict[str, Any]:
    """
    Start the configured runtime, check health, and perform one
    minimal inference request.
    """

    config = RuntimeConfig.from_environment()

    manager = RuntimeManager(
        config=config
    )

    result: Dict[str, Any] = {
        "status": "starting",
        "configuration": config.public_dict(),
    }

    try:
        runtime = manager.start()

        if runtime is None:
            return {
                "status": "error",
                "message": (
                    "RuntimeManager did not create a runtime."
                ),
                "configuration": config.public_dict(),
            }

        result["runtime"] = runtime.describe().to_dict()

        health = await manager.health()

        if hasattr(health, "to_dict"):
            result["health"] = health.to_dict()
        else:
            result["health"] = health

        if not result["health"].get("available", False):
            return {
                **result,
                "status": "runtime_unavailable",
                "message": (
                    "The runtime was created, but the model "
                    "endpoint is not currently available."
                ),
            }

        request = build_test_request(config)

        response = await runtime.generate(
            request
        )

        result["response"] = {
            "content": response.content,
            "reasoning_content": (
                response.reasoning_content
            ),
            "finish_reason": (
                response.finish_reason
            ),
            "model": response.model,
            "usage": response.usage,
        }

        result["status"] = "success"

        return result

    except Exception as exc:
        return {
            **result,
            "status": "error",
            "error": str(exc),
            "error_type": type(exc).__name__,
        }

    finally:
        await manager.stop()


async def main_async() -> None:
    """Run and print the live runtime probe."""

    result = await run_probe()

    print(
        json.dumps(
            result,
            indent=2,
            default=str,
        )
    )

    if result.get("status") == "success":
        print()
        print("LIVE MODEL RUNTIME TEST PASSED")
    else:
        print()
        print("LIVE MODEL RUNTIME TEST DID NOT PASS")


def main() -> None:
    """Synchronous command-line entry point."""

    asyncio.run(
        main_async()
    )


if __name__ == "__main__":
    main()