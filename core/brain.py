from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from .brain_config import BrainConfig
from .brain_memory import BrainMemory
from .brain_tools import BrainToolAdapter
from .llm import LLMClient, LLMError


class AutonomousBrain:
    """
    LLM-driven autonomous reasoning engine.

    The brain is intentionally separate from the agent itself.

    The agent provides:
        identity
        memory
        cognitive room
        tools
        objectives

    The brain provides:
        reasoning
        planning
        tool selection
        observation
        iterative decision making

    Flow:

        request
          ↓
        perceive context
          ↓
        LLM reasoning
          ↓
        tool selection
          ↓
        execute tool
          ↓
        observe result
          ↓
        LLM reasoning
          ↓
        repeat
          ↓
        final answer
    """

    def __init__(
        self,
        agent_name: str,
        memory=None,
        room=None,
        tools=None,
        llm: Optional[LLMClient] = None,
        config: Optional[BrainConfig] = None,
        objective: Optional[str] = None,
    ):
        self.agent_name = agent_name
        self.memory = memory
        self.room = room
        self.tools = tools

        self.config = (
            config
            if config is not None
            else BrainConfig.from_environment()
        )

        self.llm = (
            llm
            if llm is not None
            else LLMClient(self.config)
        )

        self.cognitive_memory = BrainMemory(
            memory=memory,
            room=room,
        )

        self.tool_adapter = BrainToolAdapter(
            tools=tools,
        )

        self.objective = objective

        self.last_response: Optional[Dict[str, Any]] = None

        self.step_count = 0

        self.state = "idle"

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    async def run(
        self,
        request: str,
        objective: Optional[str] = None,
    ) -> Dict[str, Any]:

        request = str(request or "").strip()

        if not request:
            return {
                "status": "error",
                "agent": self.agent_name,
                "message": "No request supplied.",
            }

        active_objective = (
            objective
            or self.objective
            or request
        )

        self.objective = active_objective
        self.step_count = 0
        self.state = "thinking"

        self._remember(
            {
                "event": "brain_request",
                "agent": self.agent_name,
                "request": request,
                "objective": active_objective,
            }
        )

        if not self.config.enabled:
            self.state = "idle"

            return {
                "status": "brain_disabled",
                "agent": self.agent_name,
                "request": request,
                "objective": active_objective,
                "message": (
                    "Autonomous LLM brain is currently disabled. "
                    "Configure BRAIN_ENABLED=true and connect "
                    "the configured model server."
                ),
                "configuration": self.config.public(),
            }

        messages: List[Dict[str, Any]] = [
            {
                "role": "system",
                "content": self._build_system_prompt(
                    active_objective
                ),
            },
            {
                "role": "user",
                "content": request,
            },
        ]

        for step in range(
            self.config.max_reasoning_steps
        ):
            self.step_count = step + 1
            self.state = "thinking"

            try:
                response = await self.llm.chat(
                    messages=messages,
                    tools=self.tool_adapter.definitions(),
                )

            except LLMError as exc:
                self.state = "error"

                return {
                    "status": "error",
                    "agent": self.agent_name,
                    "request": request,
                    "message": str(exc),
                    "step": self.step_count,
                }

            except Exception as exc:
                self.state = "error"

                return {
                    "status": "error",
                    "agent": self.agent_name,
                    "request": request,
                    "message": (
                        f"Unexpected LLM error: {exc}"
                    ),
                    "step": self.step_count,
                }

            self.last_response = response

            assistant_message = (
                self._extract_assistant_message(
                    response
                )
            )

            messages.append(
                assistant_message
            )

            tool_calls = (
                self.llm.extract_tool_calls(
                    response
                )
            )

            # ----------------------------------------------------------
            # Model has finished reasoning and produced an answer.
            # ----------------------------------------------------------

            if not tool_calls:
                final_text = self.llm.extract_text(
                    response
                )

                self.state = "complete"

                self._remember(
                    {
                        "event": "brain_result",
                        "agent": self.agent_name,
                        "request": request,
                        "response": final_text,
                        "steps": self.step_count,
                    }
                )

                return {
                    "status": "success",
                    "agent": self.agent_name,
                    "request": request,
                    "objective": active_objective,
                    "response": final_text,
                    "steps": self.step_count,
                }

            # ----------------------------------------------------------
            # Model selected one or more tools.
            # ----------------------------------------------------------

            self.state = "acting"

            for tool_call in tool_calls:
                result = await self._execute_tool_call(
                    tool_call
                )

                tool_name = self._tool_name(
                    tool_call
                )

                tool_call_id = (
                    tool_call.get("id")
                    or ""
                )

                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call_id,
                        "name": tool_name,
                        "content": json.dumps(
                            result,
                            default=str,
                        ),
                    }
                )

                self._observe(
                    {
                        "event": "tool_result",
                        "tool": tool_name,
                        "result": result,
                    }
                )

        # --------------------------------------------------------------
        # Reasoning limit reached.
        # --------------------------------------------------------------

        self.state = "paused"

        return {
            "status": "max_steps_reached",
            "agent": self.agent_name,
            "request": request,
            "objective": active_objective,
            "steps": self.step_count,
            "message": (
                "The autonomous brain reached its configured "
                "reasoning-step limit."
            ),
        }

    async def think(
        self,
        request: str,
        objective: Optional[str] = None,
    ) -> Dict[str, Any]:

        return await self.run(
            request=request,
            objective=objective,
        )

    async def reason(
        self,
        request: str,
        objective: Optional[str] = None,
    ) -> Dict[str, Any]:

        return await self.run(
            request=request,
            objective=objective,
        )

    # ------------------------------------------------------------------
    # Tool execution
    # ------------------------------------------------------------------

    async def _execute_tool_call(
        self,
        tool_call: Dict[str, Any],
    ) -> Dict[str, Any]:

        tool_name = self._tool_name(
            tool_call
        )

        arguments = self._tool_arguments(
            tool_call
        )

        if not tool_name:
            return {
                "status": "error",
                "message": (
                    "The model returned a tool call "
                    "without a tool name."
                ),
            }

        if self.tools is None:
            return {
                "status": "error",
                "tool": tool_name,
                "message": (
                    "ToolRegistry is not available."
                ),
            }

        execute = getattr(
            self.tools,
            "execute",
            None,
        )

        if not callable(execute):
            return {
                "status": "error",
                "tool": tool_name,
                "message": (
                    "ToolRegistry does not provide execute()."
                ),
            }

        try:
            result = execute(
                self.agent_name,
                tool_name,
                arguments,
            )

            return self._normalise_tool_result(
                result,
                tool_name,
            )

        except Exception as exc:
            return {
                "status": "error",
                "tool": tool_name,
                "parameters": arguments,
                "message": str(exc),
            }

    # ------------------------------------------------------------------
    # Prompt / cognitive context
    # ------------------------------------------------------------------

    def _build_system_prompt(
        self,
        objective: str,
    ) -> str:

        context = (
            self.cognitive_memory.system_context(
                agent_name=self.agent_name,
                objective=objective,
            )
        )

        return f"""
You are the autonomous AI brain of:

{self.agent_name}

You are NOT a scripted command parser.

Your purpose is to understand the Creator's natural-language
objective and autonomously determine how best to accomplish it.

You have access to tools and persistent cognitive memory.

Your reasoning loop is:

PERCEIVE
→ UNDERSTAND
→ REASON
→ PLAN
→ SELECT ACTION
→ USE TOOL
→ OBSERVE RESULT
→ REASON AGAIN

You may perform multiple reasoning/tool steps when necessary.

Do not stop simply because one tool returned information.
Determine whether the objective has actually been satisfied.

If information is missing, research it.

If a specialist or tool is appropriate, use it.

If a result is incomplete, continue investigating.

If evidence contradicts an earlier assumption, revise your plan.

Never fabricate information.

Never fabricate tool results.

Never claim an external action happened unless the tool explicitly
confirms that it happened.

SAFETY BOUNDARY

Research, analysis, planning, simulation and information gathering
may be performed autonomously.

Consequential real-world actions require the Creator Approval Gate.

Examples include:

- spending money
- purchases
- sales
- payments
- publishing
- sending external messages
- changing external accounts
- creating external accounts
- advertising spend
- other consequential external actions

Never bypass the approval system.

CURRENT COGNITIVE CONTEXT

{context}

CURRENT OBJECTIVE

{objective}
""".strip()

    # ------------------------------------------------------------------
    # Response parsing
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_assistant_message(
        response: Dict[str, Any],
    ) -> Dict[str, Any]:

        choices = response.get(
            "choices"
        )

        if (
            not isinstance(choices, list)
            or not choices
        ):
            return {
                "role": "assistant",
                "content": "",
            }

        first = choices[0]

        if not isinstance(first, dict):
            return {
                "role": "assistant",
                "content": "",
            }

        message = first.get(
            "message"
        )

        if not isinstance(message, dict):
            return {
                "role": "assistant",
                "content": "",
            }

        output = dict(message)

        output.setdefault(
            "role",
            "assistant",
        )

        return output

    @staticmethod
    def _tool_name(
        tool_call: Dict[str, Any],
    ) -> str:

        function = tool_call.get(
            "function"
        )

        if isinstance(function, dict):
            return str(
                function.get("name")
                or ""
            )

        return str(
            tool_call.get("name")
            or ""
        )

    @staticmethod
    def _tool_arguments(
        tool_call: Dict[str, Any],
    ) -> Dict[str, Any]:

        function = tool_call.get(
            "function"
        )

        if isinstance(function, dict):
            raw = function.get(
                "arguments",
                {},
            )
        else:
            raw = tool_call.get(
                "arguments",
                {},
            )

        if isinstance(raw, dict):
            return raw

        if isinstance(raw, str):
            try:
                decoded = json.loads(
                    raw
                )

                if isinstance(
                    decoded,
                    dict,
                ):
                    return decoded

            except (
                TypeError,
                ValueError,
                json.JSONDecodeError,
            ):
                return {}

        return {}

    @staticmethod
    def _normalise_tool_result(
        result: Any,
        tool_name: str,
    ) -> Dict[str, Any]:

        if isinstance(
            result,
            dict,
        ):
            output = dict(result)

            output.setdefault(
                "tool",
                tool_name,
            )

            return output

        return {
            "status": "success",
            "tool": tool_name,
            "result": result,
        }

    # ------------------------------------------------------------------
    # Cognitive memory
    # ------------------------------------------------------------------

    def _remember(
        self,
        content: Any,
    ) -> None:

        try:
            self.cognitive_memory.remember(
                content
            )
        except Exception:
            pass

    def _observe(
        self,
        observation: Any,
    ) -> None:

        try:
            self.cognitive_memory.observe(
                observation
            )
        except Exception:
            self._remember(
                {
                    "event": "observation",
                    "value": observation,
                }
            )

    # ------------------------------------------------------------------
    # Status
    # ------------------------------------------------------------------

    def status(self) -> Dict[str, Any]:
        return {
            "agent": self.agent_name,
            "state": self.state,
            "enabled": self.config.enabled,
            "provider": self.config.provider,
            "model": self.config.model,
            "steps": self.step_count,
            "objective": self.objective,
            "last_response_available": (
                self.last_response is not None
            ),
            "tools_available": len(
                self.tool_adapter.definitions()
            ),
        }

    def reset(self) -> None:
        self.step_count = 0
        self.last_response = None
        self.state = "idle"
