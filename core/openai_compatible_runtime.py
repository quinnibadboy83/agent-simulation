from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

import httpx

from .model_runtime import (
    ModelRequest,
    ModelResponse,
    ModelRuntime,
    ModelRuntimeAuthenticationError,
    ModelRuntimeInfo,
    ModelRuntimeRequestError,
    ModelRuntimeUnavailable,
    RuntimeCapabilities,
)


class OpenAICompatibleRuntimeError(Exception):
    """Base error for the OpenAI-compatible model runtime."""


class OpenAICompatibleRuntime(ModelRuntime):
    """
    Provider-neutral runtime for OpenAI-compatible model servers.

    Intended targets include:

        - llama-server
        - llama.cpp HTTP server
        - local model servers
        - desktop inference servers
        - Android/local inference bridges
        - other OpenAI-compatible runtimes

    The Agent Simulation Engine does not need to know which model
    server is underneath this class.

    Architecture:

        AutonomousBrain
              |
              v
        BrainRuntime
              |
              v
        OpenAICompatibleRuntime
              |
              v
        /v1/chat/completions
              |
              v
        local model
    """

    name = "openai_compatible"

    def __init__(
        self,
        base_url: str,
        model: str,
        provider: str = "openai_compatible",
        api_key: Optional[str] = None,
        timeout: float = 300.0,
        runtime_name: str = "openai_compatible",
    ):
        self.base_url = (
            str(base_url or "")
            .strip()
            .rstrip("/")
        )

        self.model = (
            str(model or "")
            .strip()
        )

        self.provider = (
            str(provider or "openai_compatible")
            .strip()
        )

        self.api_key = (
            str(api_key or "")
            .strip()
        )

        self.timeout = float(
            timeout
        )

        self.name = (
            str(runtime_name or self.name)
            .strip()
        )

        if not self.base_url:
            raise ValueError(
                "base_url cannot be empty."
            )

        if not self.model:
            raise ValueError(
                "model cannot be empty."
            )

    # ------------------------------------------------------------------
    # Endpoint helpers
    # ------------------------------------------------------------------

    def _models_url(self) -> str:
        return (
            f"{self.base_url}/models"
        )

    def _chat_url(self) -> str:
        return (
            f"{self.base_url}/chat/completions"
        )

    # ------------------------------------------------------------------
    # Headers
    # ------------------------------------------------------------------

    def _headers(
        self,
    ) -> Dict[str, str]:
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        if self.api_key:
            headers["Authorization"] = (
                f"Bearer {self.api_key}"
            )

        return headers

    # ------------------------------------------------------------------
    # Static runtime description
    # ------------------------------------------------------------------

    def describe(
        self,
    ) -> ModelRuntimeInfo:
        return ModelRuntimeInfo(
            runtime=self.name,
            provider=self.provider,
            model=self.model,
            available=False,
            endpoint=self.base_url,
            capabilities=[
                RuntimeCapabilities.CHAT,
                RuntimeCapabilities.REASONING,
                RuntimeCapabilities.TOOL_CALLING,
                RuntimeCapabilities.LOCAL,
            ],
            metadata={
                "protocol": (
                    "OpenAI-compatible"
                ),
                "chat_endpoint": (
                    self._chat_url()
                ),
                "models_endpoint": (
                    self._models_url()
                ),
            },
        )

    # ------------------------------------------------------------------
    # Health
    # ------------------------------------------------------------------

    async def health(
        self,
    ) -> ModelRuntimeInfo:
        """
        Test whether the configured model server is reachable.

        The health check is intentionally read-only.
        """

        description = self.describe()

        try:
            timeout = httpx.Timeout(
                timeout=self.timeout,
                connect=min(
                    self.timeout,
                    30.0,
                ),
                read=self.timeout,
                write=min(
                    self.timeout,
                    30.0,
                ),
                pool=min(
                    self.timeout,
                    30.0,
                ),
            )

            async with httpx.AsyncClient(
                timeout=timeout
            ) as client:

                response = await client.get(
                    self._models_url(),
                    headers=self._headers(),
                )

                if response.status_code in {
                    401,
                    403,
                }:
                    return ModelRuntimeInfo(
                        runtime=description.runtime,
                        provider=description.provider,
                        model=description.model,
                        available=False,
                        endpoint=description.endpoint,
                        capabilities=list(
                            description.capabilities
                        ),
                        metadata=dict(
                            description.metadata
                        ),
                        error=(
                            "Model runtime authentication "
                            "was rejected."
                        ),
                    )

                response.raise_for_status()

                try:
                    payload = response.json()
                except ValueError:
                    payload = {
                        "raw_response": (
                            response.text[:2000]
                        )
                    }

                return ModelRuntimeInfo(
                    runtime=description.runtime,
                    provider=description.provider,
                    model=self._resolve_model(
                        payload
                    ),
                    available=True,
                    endpoint=description.endpoint,
                    capabilities=list(
                        description.capabilities
                    ),
                    metadata={
                        **description.metadata,
                        "server_response": payload,
                    },
                )

        except httpx.TimeoutException as exc:
            return ModelRuntimeInfo(
                runtime=description.runtime,
                provider=description.provider,
                model=description.model,
                available=False,
                endpoint=description.endpoint,
                capabilities=list(
                    description.capabilities
                ),
                metadata=dict(
                    description.metadata
                ),
                error=(
                    "Model runtime health check timed out: "
                    f"{exc}"
                ),
            )

        except httpx.HTTPStatusError as exc:
            return ModelRuntimeInfo(
                runtime=description.runtime,
                provider=description.provider,
                model=description.model,
                available=False,
                endpoint=description.endpoint,
                capabilities=list(
                    description.capabilities
                ),
                metadata=dict(
                    description.metadata
                ),
                error=(
                    "Model runtime returned HTTP "
                    f"{exc.response.status_code}."
                ),
            )

        except httpx.HTTPError as exc:
            return ModelRuntimeInfo(
                runtime=description.runtime,
                provider=description.provider,
                model=description.model,
                available=False,
                endpoint=description.endpoint,
                capabilities=list(
                    description.capabilities
                ),
                metadata=dict(
                    description.metadata
                ),
                error=(
                    f"Model runtime connection failed: {exc}"
                ),
            )

        except Exception as exc:
            return ModelRuntimeInfo(
                runtime=description.runtime,
                provider=description.provider,
                model=description.model,
                available=False,
                endpoint=description.endpoint,
                capabilities=list(
                    description.capabilities
                ),
                metadata=dict(
                    description.metadata
                ),
                error=str(exc),
            )

    # ------------------------------------------------------------------
    # Generation
    # ------------------------------------------------------------------

    async def generate(
        self,
        request: ModelRequest,
    ) -> ModelResponse:
        """
        Generate one model response.

        The runtime converts the provider-neutral ModelRequest into
        the OpenAI-compatible chat-completions format.
        """

        if not isinstance(
            request,
            ModelRequest,
        ):
            raise OpenAICompatibleRuntimeError(
                "request must be a ModelRequest instance."
            )

        if not request.messages:
            raise OpenAICompatibleRuntimeError(
                "Cannot generate from an empty message list."
            )

        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": list(
                request.messages
            ),
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
            "stream": False,
        }

        if request.tools:
            payload["tools"] = list(
                request.tools
            )

            payload["tool_choice"] = "auto"

        if request.metadata:
            metadata = dict(
                request.metadata
            )

            # Metadata belongs to the application/runtime layer.
            # Do not blindly inject arbitrary metadata into the
            # provider request.
            provider_extra = metadata.get(
                "provider_extra"
            )

            if isinstance(
                provider_extra,
                dict,
            ):
                payload.update(
                    provider_extra
                )

        timeout = httpx.Timeout(
            timeout=self.timeout,
            connect=min(
                self.timeout,
                30.0,
            ),
            read=self.timeout,
            write=min(
                self.timeout,
                30.0,
            ),
            pool=min(
                self.timeout,
                30.0,
            ),
        )

        try:
            async with httpx.AsyncClient(
                timeout=timeout
            ) as client:

                response = await client.post(
                    self._chat_url(),
                    headers=self._headers(),
                    json=payload,
                )

                if response.status_code in {
                    401,
                    403,
                }:
                    raise ModelRuntimeAuthenticationError(
                        "Model runtime authentication failed."
                    )

                if response.status_code >= 400:
                    body = response.text[
                        :4000
                    ]

                    raise ModelRuntimeRequestError(
                        "Model runtime returned HTTP "
                        f"{response.status_code}: {body}"
                    )

                try:
                    raw_response = response.json()
                except ValueError as exc:
                    raise ModelRuntimeRequestError(
                        "Model runtime returned invalid JSON."
                    ) from exc

        except (
            ModelRuntimeAuthenticationError,
            ModelRuntimeRequestError,
        ):
            raise

        except httpx.TimeoutException as exc:
            raise ModelRuntimeUnavailable(
                "Model runtime request timed out: "
                f"{exc}"
            ) from exc

        except httpx.HTTPError as exc:
            raise ModelRuntimeUnavailable(
                "Model runtime connection failed: "
                f"{exc}"
            ) from exc

        except Exception as exc:
            raise ModelRuntimeRequestError(
                "Unexpected model runtime error: "
                f"{exc}"
            ) from exc

        return self._parse_response(
            raw_response
        )

    # ------------------------------------------------------------------
    # Response parsing
    # ------------------------------------------------------------------

    def _parse_response(
        self,
        response: Any,
    ) -> ModelResponse:
        if not isinstance(
            response,
            dict,
        ):
            raise ModelRuntimeRequestError(
                "Model runtime returned a non-object response."
            )

        choices = response.get(
            "choices"
        )

        if not isinstance(
            choices,
            list,
        ):
            choices = []

        first_choice: Dict[str, Any] = {}

        if choices:
            candidate = choices[0]

            if isinstance(
                candidate,
                dict,
            ):
                first_choice = candidate

        message = first_choice.get(
            "message"
        )

        if not isinstance(
            message,
            dict,
        ):
            message = {}

        content = (
            message.get(
                "content"
            )
            or ""
        )

        if not isinstance(
            content,
            str,
        ):
            content = str(
                content
            )

        reasoning_content = (
            message.get(
                "reasoning_content"
            )
            or message.get(
                "reasoning"
            )
            or ""
        )

        if not isinstance(
            reasoning_content,
            str,
        ):
            reasoning_content = str(
                reasoning_content
            )

        tool_calls = (
            message.get(
                "tool_calls",
                [],
            )
            or []
        )

        if not isinstance(
            tool_calls,
            list,
        ):
            tool_calls = []

        finish_reason = (
            first_choice.get(
                "finish_reason"
            )
        )

        if finish_reason is not None:
            finish_reason = str(
                finish_reason
            )

        model = response.get(
            "model"
        )

        if model is not None:
            model = str(
                model
            )

        usage = response.get(
            "usage",
            {},
        )

        if not isinstance(
            usage,
            dict,
        ):
            usage = {}

        return ModelResponse(
            content=content,
            reasoning_content=(
                reasoning_content.strip()
            ),
            tool_calls=[
                call
                for call in tool_calls
                if isinstance(
                    call,
                    dict,
                )
            ],
            finish_reason=finish_reason,
            model=model,
            usage=usage,
            raw_response=response,
            metadata={
                "runtime": self.name,
                "provider": self.provider,
                "protocol": (
                    "OpenAI-compatible"
                ),
            },
        )

    # ------------------------------------------------------------------
    # Model discovery
    # ------------------------------------------------------------------

    def _resolve_model(
        self,
        payload: Any,
    ) -> str:
        """
        Determine the model reported by /models.

        If discovery does not expose a usable model identifier,
        retain the configured model.
        """

        if not isinstance(
            payload,
            dict,
        ):
            return self.model

        data = payload.get(
            "data"
        )

        if not isinstance(
            data,
            list,
        ):
            return self.model

        for item in data:
            if not isinstance(
                item,
                dict,
            ):
                continue

            model_id = item.get(
                "id"
            )

            if not model_id:
                continue

            model_id = str(
                model_id
            )

            if model_id == self.model:
                return model_id

        for item in data:
            if not isinstance(
                item,
                dict,
            ):
                continue

            model_id = item.get(
                "id"
            )

            if model_id:
                return str(
                    model_id
                )

        return self.model

    # ------------------------------------------------------------------
    # Utility
    # ------------------------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        """
        Return a JSON-safe runtime configuration.

        Secrets are deliberately excluded.
        """

        return {
            "runtime": self.name,
            "provider": self.provider,
            "model": self.model,
            "base_url": self.base_url,
            "timeout": self.timeout,
            "api_key_configured": bool(
                self.api_key
            ),
        }