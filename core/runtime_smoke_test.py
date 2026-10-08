from __future__ import annotations

"""
Runtime Smoke Test
------------------

Verifies that the new ModelRuntime architecture can be imported,
constructed and inspected without requiring a live model server.

This is intentionally lightweight.

It does NOT:
    - start a model
    - contact Render
    - contact Cloudflare
    - contact Hugging Face
    - generate model tokens
    - modify agent memory
    - execute agent tools

Its purpose is to prove that the runtime abstraction is structurally
valid before AutonomousBrain is migrated onto it.
"""

from typing import Any, Dict

from .brain_runtime import BrainRuntime
from .llm_runtime_adapter import LLMRuntimeAdapter
from .model_runtime import (
    ModelRequest,
    ModelResponse,
    ModelRuntime,
    ModelRuntimeInfo,
)


def run_runtime_smoke_test() -> Dict[str, Any]:
    """
    Run the structural runtime compatibility checks.

    Returns a JSON-safe result dictionary.
    """

    results: Dict[str, Any] = {
        "status": "running",
        "checks": [],
        "errors": [],
    }

    # --------------------------------------------------------------
    # Check 1: ModelRequest
    # --------------------------------------------------------------

    try:
        request = ModelRequest(
            messages=[
                {
                    "role": "user",
                    "content": "runtime smoke test",
                }
            ],
            tools=[],
            temperature=0.2,
            max_tokens=32,
        )

        request_dict = request.to_dict()

        if (
            isinstance(
                request_dict,
                dict,
            )
            and "messages" in request_dict
        ):
            results["checks"].append(
                {
                    "name": "model_request",
                    "status": "passed",
                }
            )
        else:
            raise RuntimeError(
                "ModelRequest did not produce a valid dictionary."
            )

    except Exception as exc:
        results["errors"].append(
            {
                "name": "model_request",
                "error": str(exc),
            }
        )

    # --------------------------------------------------------------
    # Check 2: ModelResponse
    # --------------------------------------------------------------

    try:
        response = ModelResponse(
            content="smoke test",
            reasoning_content="",
            tool_calls=[],
            finish_reason="stop",
            model="test-model",
        )

        response_dict = response.to_dict()

        required_fields = {
            "content",
            "reasoning_content",
            "tool_calls",
            "finish_reason",
            "model",
            "usage",
            "raw_response",
            "metadata",
        }

        if required_fields.issubset(
            response_dict.keys()
        ):
            results["checks"].append(
                {
                    "name": "model_response",
                    "status": "passed",
                }
            )
        else:
            missing = sorted(
                required_fields
                - set(
                    response_dict.keys()
                )
            )

            raise RuntimeError(
                "ModelResponse missing fields: "
                + ", ".join(missing)
            )

    except Exception as exc:
        results["errors"].append(
            {
                "name": "model_response",
                "error": str(exc),
            }
        )

    # --------------------------------------------------------------
    # Check 3: ModelRuntimeInfo
    # --------------------------------------------------------------

    try:
        info = ModelRuntimeInfo(
            runtime="smoke_test",
            provider="test",
            model="test-model",
            available=False,
            capabilities=[],
        )

        info_dict = info.to_dict()

        required_fields = {
            "runtime",
            "provider",
            "model",
            "available",
            "endpoint",
            "capabilities",
            "hardware",
            "metadata",
            "error",
        }

        if required_fields.issubset(
            info_dict.keys()
        ):
            results["checks"].append(
                {
                    "name": "model_runtime_info",
                    "status": "passed",
                }
            )
        else:
            missing = sorted(
                required_fields
                - set(
                    info_dict.keys()
                )
            )

            raise RuntimeError(
                "ModelRuntimeInfo missing fields: "
                + ", ".join(missing)
            )

    except Exception as exc:
        results["errors"].append(
            {
                "name": "model_runtime_info",
                "error": str(exc),
            }
        )

    # --------------------------------------------------------------
    # Check 4: ModelRuntime remains abstract
    # --------------------------------------------------------------

    try:
        if ModelRuntime.__abstractmethods__:
            results["checks"].append(
                {
                    "name": "model_runtime_abstract_interface",
                    "status": "passed",
                    "abstract_methods": sorted(
                        ModelRuntime.__abstractmethods__
                    ),
                }
            )
        else:
            raise RuntimeError(
                "ModelRuntime unexpectedly has no abstract methods."
            )

    except Exception as exc:
        results["errors"].append(
            {
                "name": "model_runtime_abstract_interface",
                "error": str(exc),
            }
        )

    # --------------------------------------------------------------
    # Check 5: BrainRuntime can exist without a runtime
    # --------------------------------------------------------------

    try:
        bridge = BrainRuntime()

        if not bridge.using_runtime:
            results["checks"].append(
                {
                    "name": "brain_runtime_empty_state",
                    "status": "passed",
                }
            )
        else:
            raise RuntimeError(
                "Empty BrainRuntime unexpectedly reports "
                "an active runtime."
            )

    except Exception as exc:
        results["errors"].append(
            {
                "name": "brain_runtime_empty_state",
                "error": str(exc),
            }
        )

    # --------------------------------------------------------------
    # Check 6: LLMRuntimeAdapter is structurally instantiable
    #
    # We use a tiny fake LLM client instead of a real network client.
    # This avoids any external dependency.
    # --------------------------------------------------------------

    try:

        class FakeConfig:
            provider = "test"
            model = "test-model"
            enabled = False
            base_url = None

        class FakeLLMClient:
            config = FakeConfig()

            async def chat(
                self,
                messages,
                tools=None,
                temperature=None,
                max_tokens=None,
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
                    "model": "test-model",
                    "usage": {},
                }

            def extract_text(
                self,
                response,
            ):
                return "test"

            def extract_tool_calls(
                self,
                response,
            ):
                return []

        fake_client = FakeLLMClient()

        adapter = LLMRuntimeAdapter.__new__(
            LLMRuntimeAdapter
        )

        adapter.client = fake_client
        adapter.name = "smoke_test_adapter"
        adapter._last_health = None

        description = adapter.describe()

        if not isinstance(
            description,
            ModelRuntimeInfo,
        ):
            raise RuntimeError(
                "LLMRuntimeAdapter.describe() did not return "
                "ModelRuntimeInfo."
            )

        results["checks"].append(
            {
                "name": "llm_runtime_adapter_structure",
                "status": "passed",
                "runtime": description.runtime,
                "provider": description.provider,
                "model": description.model,
            }
        )

    except Exception as exc:
        results["errors"].append(
            {
                "name": "llm_runtime_adapter_structure",
                "error": str(exc),
            }
        )

    # --------------------------------------------------------------
    # Final result
    # --------------------------------------------------------------

    if results["errors"]:
        results["status"] = "failed"
    else:
        results["status"] = "passed"

    results["summary"] = {
        "checks_passed": len(
            results["checks"]
        ),
        "checks_failed": len(
            results["errors"]
        ),
    }

    return results


if __name__ == "__main__":
    import json

    result = run_runtime_smoke_test()

    print(
        json.dumps(
            result,
            indent=2,
            default=str,
        )
    )