from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from .brain_config import BrainConfig
from .brain_memory import BrainMemory
from .brain_tools import BrainToolAdapter
from .llm import LLMClient, LLMError

from .brain_runtime import (
    BrainRuntime,
    BrainRuntimeError,
)

from .llm_runtime_adapter import (
    LLMRuntimeAdapter,
)

from .model_runtime import (
    ModelRuntime,
    ModelRuntimeError,
)

from .experience_memory import (
    Experience,
    ExperienceMemory,
)

from .knowledge_store import (
    KnowledgeStore,
)

from .memory_retrieval import (
    MemoryRetrieval,
)

from .cognitive_context import (
    CognitiveContextBuilder,
)


class AutonomousBrain:
    """
    LLM-driven autonomous reasoning engine.

    The brain is separate from the agent.

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

    Persistent cognitive layer:

        experience
            ↓
        evaluation / learning
            ↓
        knowledge
            ↓
        retrieval
            ↓
        cognitive context
            ↓
        reasoning

    Runtime layer:

        AutonomousBrain
              ↓
        BrainRuntime
              ↓
        ModelRuntime
              ↓
        local / remote model

    The existing LLMClient remains supported as a compatibility
    fallback while the runtime architecture is migrated.

    Existing BrainMemory remains available for short-term/current
    cognitive state.

    ExperienceMemory and KnowledgeStore provide persistent learning
    across runs.
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
        experience_memory: Optional[ExperienceMemory] = None,
        knowledge_store: Optional[KnowledgeStore] = None,
        memory_retrieval: Optional[MemoryRetrieval] = None,
        runtime: Optional[ModelRuntime] = None,
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

        # --------------------------------------------------------------
        # Existing LLM client.
        #
        # This remains available for compatibility.
        # --------------------------------------------------------------

        self.llm = (
            llm
            if llm is not None
            else LLMClient(self.config)
        )

        # --------------------------------------------------------------
        # Model runtime.
        #
        # If an explicit ModelRuntime is supplied, use it.
        #
        # Otherwise wrap the existing LLMClient so the brain can use
        # the new provider-independent runtime interface without
        # breaking the current system.
        # --------------------------------------------------------------

        self.runtime = runtime

        if self.runtime is not None:
            self.brain_runtime = BrainRuntime(
                runtime=self.runtime,
                legacy_llm=self.llm,
            )
        else:
            self.runtime_adapter = (
                LLMRuntimeAdapter(
                    self.llm
                )
            )

            self.brain_runtime = BrainRuntime(
                runtime=self.runtime_adapter,
                legacy_llm=self.llm,
            )

        # --------------------------------------------------------------
        # Existing short-term cognitive memory.
        # --------------------------------------------------------------

        self.cognitive_memory = BrainMemory(
            memory=memory,
            room=room,
        )

        # --------------------------------------------------------------
        # Persistent learning memory.
        # --------------------------------------------------------------

        self.experience_memory = (
            experience_memory
            if experience_memory is not None
            else ExperienceMemory()
        )

        self.knowledge_store = (
            knowledge_store
            if knowledge_store is not None
            else KnowledgeStore()
        )

        self.memory_retrieval = (
            memory_retrieval
            if memory_retrieval is not None
            else MemoryRetrieval(
                experience_memory=(
                    self.experience_memory
                ),
                knowledge_store=(
                    self.knowledge_store
                ),
            )
        )

        self.cognitive_context = (
            CognitiveContextBuilder(
                experience_memory=(
                    self.experience_memory
                ),
                knowledge_store=(
                    self.knowledge_store
                ),
                retrieval=(
                    self.memory_retrieval
                ),
            )
        )

        # --------------------------------------------------------------
        # Existing tool system.
        # --------------------------------------------------------------

        self.tool_adapter = BrainToolAdapter(
            tools=tools,
        )

        self.objective = objective

        self.last_response: Optional[
            Dict[str, Any]
        ] = None

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

        request = str(
            request or ""
        ).strip()

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

        # --------------------------------------------------------------
        # Build persistent cognitive context BEFORE reasoning.
        # --------------------------------------------------------------

        cognitive_context = (
            self.cognitive_context.build_for_planning(
                agent_name=self.agent_name,
                goal=active_objective,
                limit=10,
            )
        )

        messages: List[
            Dict[str, Any]
        ] = [
            {
                "role": "system",
                "content": self._build_system_prompt(
                    active_objective,
                    cognitive_context=cognitive_context,
                ),
            },
            {
                "role": "user",
                "content": request,
            },
        ]

        # --------------------------------------------------------------
        # Autonomous reasoning loop.
        # --------------------------------------------------------------

        for step in range(
            self.config.max_reasoning_steps
        ):
            self.step_count = step + 1
            self.state = "thinking"

            try:
                runtime_response = (
                    await self.brain_runtime.generate(
                        messages=messages,
                        tools=(
                            self.tool_adapter.definitions()
                        ),
                        temperature=(
                            self.config.temperature
                        ),
                        max_tokens=(
                            self.config.max_tokens
                        ),
                    )
                )

                response = (
                    runtime_response.raw_response
                    if runtime_response.raw_response
                    else self._runtime_response_to_dict(
                        runtime_response
                    )
                )

            except (
                LLMError,
                ModelRuntimeError,
                BrainRuntimeError,
            ) as exc:

                self.state = "error"

                self._record_experience(
                    request=request,
                    objective=active_objective,
                    decision="Model runtime request failed.",
                    action="reason",
                    result=str(exc),
                    success=False,
                    lesson=(
                        "The reasoning cycle failed because "
                        "the configured model runtime returned "
                        "an error."
                    ),
                )

                return {
                    "status": "error",
                    "agent": self.agent_name,
                    "request": request,
                    "message": str(exc),
                    "step": self.step_count,
                }

            except Exception as exc:

                self.state = "error"

                self._record_experience(
                    request=request,
                    objective=active_objective,
                    decision="Unexpected reasoning failure.",
                    action="reason",
                    result=str(exc),
                    success=False,
                    lesson=(
                        "The reasoning cycle encountered "
                        "an unexpected exception."
                    ),
                )

                return {
                    "status": "error",
                    "agent": self.agent_name,
                    "request": request,
                    "message": (
                        f"Unexpected model error: {exc}"
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

            # ----------------------------------------------------------
            # Tool calls are taken from the runtime response rather
            # than directly from LLMClient.
            # ----------------------------------------------------------

            tool_calls = (
                runtime_response.tool_calls
                or []
            )

            # ----------------------------------------------------------
            # No tool call means the model has produced its answer.
            # ----------------------------------------------------------

            if not tool_calls:

                final_text = (
                    runtime_response.content
                    or self._extract_text_from_response(
                        response
                    )
                )

                if not final_text:
                    final_text = (
                        runtime_response.reasoning_content
                        or self._extract_reasoning_text(
                            response
                        )
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

                self._record_experience(
                    request=request,
                    objective=active_objective,
                    decision=(
                        "Completed the requested reasoning task."
                    ),
                    action="reason",
                    result=final_text,
                    success=True,
                    lesson=(
                        "The reasoning cycle completed successfully."
                    ),
                )

                return {
                    "status": "success",
                    "agent": self.agent_name,
                    "request": request,
                    "objective": active_objective,
                    "response": final_text,
                    "steps": self.step_count,
                    "memory": (
                        self._memory_summary(
                            cognitive_context
                        )
                    ),
                    "runtime": (
                        self.brain_runtime.describe()
                    ),
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

                # ------------------------------------------------------
                # Store tool experience.
                #
                # Tool success is evidence for future learning.
                # It does not grant permission for future actions.
                # ------------------------------------------------------

                self._record_experience(
                    request=request,
                    objective=active_objective,
                    decision=(
                        f"Selected tool '{tool_name}'."
                    ),
                    action=tool_name,
                    result=result,
                    success=(
                        self._tool_result_success(
                            result
                        )
                    ),
                    lesson=(
                        self._tool_result_lesson(
                            tool_name,
                            result,
                        )
                    ),
                )

        # --------------------------------------------------------------
        # Reasoning limit reached.
        # --------------------------------------------------------------

        self.state = "paused"

        self._record_experience(
            request=request,
            objective=active_objective,
            decision=(
                "Reasoning cycle reached its configured limit."
            ),
            action="reason",
            result=(
                "Maximum reasoning steps reached."
            ),
            success=False,
            lesson=(
                "The reasoning cycle reached the configured "
                "maximum number of steps before completion."
            ),
        )

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
    # Runtime response conversion
    # ------------------------------------------------------------------

    @staticmethod
    def _runtime_response_to_dict(
        response: Any,
    ) -> Dict[str, Any]:
        """
        Convert a provider-neutral ModelResponse into the legacy
        OpenAI-compatible response structure used by the brain's
        existing parsing helpers.

        This exists only as a compatibility bridge.
        """

        tool_calls = (
            response.tool_calls
            or []
        )

        message: Dict[str, Any] = {
            "role": "assistant",
            "content": (
                response.content
                or ""
            ),
        }

        if response.reasoning_content:
            message[
                "reasoning_content"
            ] = response.reasoning_content

        if tool_calls:
            message[
                "tool_calls"
            ] = tool_calls

        return {
            "choices": [
                {
                    "message": message,
                    "finish_reason": (
                        response.finish_reason
                    ),
                }
            ],
            "model": response.model,
            "usage": (
                response.usage
                or {}
            ),
            "runtime_metadata": (
                response.metadata
                or {}
            ),
        }

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

        if not callable(
            execute
        ):
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
        cognitive_context=None,
    ) -> str:

        if cognitive_context is None:

            cognitive_context = (
                self.cognitive_context.build_for_planning(
                    agent_name=self.agent_name,
                    goal=objective,
                    limit=10,
                )
            )

        persistent_context = (
            cognitive_context.system_context
        )

        short_term_context = (
            self.cognitive_memory.system_context(
                agent_name=self.agent_name,
                objective=objective,
            )
        )

        return f"""
You are the autonomous AI brain of:

{self.agent_name}

You are NOT a scripted command parser.

Understand natural-language objectives and determine the best
permitted way to accomplish them.

You have access to tools, short-term cognitive memory, persistent
experience memory, and learned knowledge.

REASONING LOOP

PERCEIVE
→ UNDERSTAND
→ REASON
→ PLAN
→ SELECT ACTION
→ USE TOOL
→ OBSERVE RESULT
→ REASON AGAIN

You may perform multiple tool/reasoning steps when necessary.

IMPORTANT RESPONSE RULE

Be efficient.

Do not spend excessive time generating internal reasoning.

For a simple request, answer immediately.

When a tool is necessary, select the appropriate tool and use it.

After receiving a tool result, determine whether the objective is
satisfied. If it is satisfied, provide the answer. If more work is
required, continue.

Keep the visible final answer concise and useful.

Do not fabricate information.

Do not fabricate tool results.

Never claim an external action happened unless the tool explicitly
confirms that it happened.

PERSISTENT MEMORY RULES

Persistent memory is evidence, not authority.

Previous success does not guarantee future success.

Previous failure does not prove an approach can never work.

Conflicting evidence must remain visible.

Always consider the current situation.

Memory does not grant permission to execute actions.

LEARNING RULE

Use previous experiences and learned knowledge to improve decisions.

Do not pretend that memory is certain when confidence is low.

Do not invent lessons that are not supported by stored experience
or knowledge.

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

SHORT-TERM COGNITIVE MEMORY

{short_term_context}

PERSISTENT COGNITIVE CONTEXT

{persistent_context}

CURRENT OBJECTIVE

{objective}
""".strip()

    # ------------------------------------------------------------------
    # Persistent experience recording
    # ------------------------------------------------------------------

    def _record_experience(
        self,
        request: str,
        objective: str,
        decision: str,
        action: str,
        result: Any,
        success: Optional[bool],
        lesson: str = "",
    ) -> None:

        try:

            experience = Experience(
                agent_name=self.agent_name,
                goal=objective,
                decision=decision,
                action=action,
                result=result,
                success=success,
                lesson=lesson,
                confidence=(
                    0.9
                    if success is True
                    else 0.3
                    if success is False
                    else 0.5
                ),
                context={
                    "request": request,
                    "objective": objective,
                    "steps": self.step_count,
                },
                metadata={
                    "source": "AutonomousBrain",
                    "brain_agent": self.agent_name,
                },
            )

            self.experience_memory.save(
                experience
            )

        except Exception:
            # Persistent learning must never crash the brain.
            pass

    @staticmethod
    def _tool_result_success(
        result: Any,
    ) -> Optional[bool]:

        if not isinstance(
            result,
            dict,
        ):
            return True

        status = str(
            result.get(
                "status",
                "",
            )
        ).lower()

        if status in {
            "error",
            "failed",
            "failure",
        }:
            return False

        if status in {
            "success",
            "ok",
            "completed",
        }:
            return True

        return None

    @staticmethod
    def _tool_result_lesson(
        tool_name: str,
        result: Any,
    ) -> str:

        success = (
            AutonomousBrain._tool_result_success(
                result
            )
        )

        if success is True:
            return (
                f"Tool '{tool_name}' produced a successful "
                "result in this reasoning cycle."
            )

        if success is False:
            return (
                f"Tool '{tool_name}' produced an unsuccessful "
                "result in this reasoning cycle."
            )

        return (
            f"Tool '{tool_name}' produced a result whose "
            "success status was not explicitly determined."
        )

    @staticmethod
    def _memory_summary(
        cognitive_context,
    ) -> Dict[str, Any]:

        if cognitive_context is None:
            return {
                "retrieved": False,
            }

        return {
            "retrieved": True,
            "matches": len(
                cognitive_context.memory.matches
            ),
            "experiences": len(
                cognitive_context.memory.experiences
            ),
            "knowledge": len(
                cognitive_context.memory.knowledge
            ),
            "guidance": len(
                cognitive_context.guidance
            ),
        }

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
            not isinstance(
                choices,
                list,
            )
            or not choices
        ):
            return {
                "role": "assistant",
                "content": "",
            }

        first = choices[0]

        if not isinstance(
            first,
            dict,
        ):
            return {
                "role": "assistant",
                "content": "",
            }

        message = first.get(
            "message"
        )

        if not isinstance(
            message,
            dict,
        ):
            return {
                "role": "assistant",
                "content": "",
            }

        output = dict(
            message
        )

        output.setdefault(
            "role",
            "assistant",
        )

        return output

    @staticmethod
    def _extract_text_from_response(
        response: Dict[str, Any],
    ) -> str:

        choices = response.get(
            "choices"
        )

        if (
            not isinstance(
                choices,
                list,
            )
            or not choices
        ):
            return ""

        first = choices[0]

        if not isinstance(
            first,
            dict,
        ):
            return ""

        message = first.get(
            "message"
        )

        if not isinstance(
            message,
            dict,
        ):
            return ""

        content = (
            message.get(
                "content"
            )
            or ""
        )

        return str(
            content
            or ""
        ).strip()

    @staticmethod
    def _extract_reasoning_text(
        response: Dict[str, Any],
    ) -> str:

        choices = response.get(
            "choices"
        )

        if (
            not isinstance(
                choices,
                list,
            )
            or not choices
        ):
            return ""

        first = choices[0]

        if not isinstance(
            first,
            dict,
        ):
            return ""

        message = first.get(
            "message"
        )

        if not isinstance(
            message,
            dict,
        ):
            return ""

        reasoning = (
            message.get(
                "reasoning_content"
            )
            or message.get(
                "reasoning"
            )
            or ""
        )

        if reasoning is None:
            return ""

        return str(
            reasoning
        ).strip()

    @staticmethod
    def _tool_name(
        tool_call: Dict[str, Any],
    ) -> str:

        function = tool_call.get(
            "function"
        )

        if isinstance(
            function,
            dict,
        ):
            return str(
                function.get(
                    "name"
                )
                or ""
            )

        return str(
            tool_call.get(
                "name"
            )
            or ""
        )

    @staticmethod
    def _tool_arguments(
        tool_call: Dict[str, Any],
    ) -> Dict[str, Any]:

        function = tool_call.get(
            "function"
        )

        if isinstance(
            function,
            dict,
        ):
            raw = function.get(
                "arguments",
                {},
            )
        else:
            raw = tool_call.get(
                "arguments",
                {},
            )

        if isinstance(
            raw,
            dict,
        ):
            return raw

        if isinstance(
            raw,
            str,
        ):

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

            output = dict(
                result
            )

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

    def status(
        self,
    ) -> Dict[str, Any]:

        runtime_description = {}

        try:
            runtime_description = (
                self.brain_runtime.describe()
            )
        except Exception as exc:
            runtime_description = {
                "runtime": "unknown",
                "available": False,
                "error": str(exc),
            }

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
            "persistent_memory": True,
            "runtime": runtime_description,
        }

    def reset(
        self,
    ) -> None:

        self.step_count = 0
        self.last_response = None
        self.state = "idle"