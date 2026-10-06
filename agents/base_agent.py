from __future__ import annotations

from typing import Any, Dict, List, Optional

from core.cognitive_room import CognitiveRoom


class BaseAgent:
    """
    Base autonomous agent.

    Agents have:
    - identity
    - persistent shared memory
    - private cognitive room
    - tools
    - objectives
    - tasks
    - messages
    - an optional LLM brain

    The LLM brain is deliberately optional while the system is being
    assembled. Once enabled, process_order() can route requests into
    autonomous reasoning instead of scripted command matching.
    """

    def __init__(
        self,
        name: str,
        role: str,
        memory,
        tools,
        description: str = "",
        brain=None,
    ):
        self.name = name
        self.role = role
        self.memory = memory
        self.tools = tools
        self.description = description

        self.identity = {
            "name": name,
            "role": role,
            "description": description,
        }

        self.room = CognitiveRoom(
            agent_name=name,
            role=role,
        )

        self.current_task: Optional[Dict[str, Any]] = None
        self.status = "idle"

        self.brain = brain

        self._publish_status()

    # ------------------------------------------------------------------
    # Brain
    # ------------------------------------------------------------------

    def attach_brain(self, brain) -> None:
        self.brain = brain

    def has_brain(self) -> bool:
        return self.brain is not None

    async def think_with_brain(
        self,
        request: str,
        objective: Optional[str] = None,
    ) -> Dict[str, Any]:
        if self.brain is None:
            return {
                "status": "brain_unavailable",
                "agent": self.name,
                "message": (
                    f"{self.name} does not currently have "
                    "an autonomous brain attached."
                ),
            }

        self.update_status("thinking")

        try:
            result = await self.brain.run(
                request=request,
                objective=objective,
            )

            self.update_status("idle")

            return result

        except Exception as exc:
            self.update_status("error")

            return {
                "status": "error",
                "agent": self.name,
                "message": f"Brain error: {exc}",
            }

    # ------------------------------------------------------------------
    # Cognitive lifecycle
    # ------------------------------------------------------------------

    def perceive(
        self,
        observation: Any,
    ) -> Dict[str, Any]:
        self.room.observe(observation)

        return {
            "agent": self.name,
            "observation": observation,
        }

    def remember(
        self,
        content: Any,
    ) -> None:
        self.room.remember(content)

        add_knowledge = getattr(
            self.memory,
            "add_knowledge",
            None,
        )

        if callable(add_knowledge):
            try:
                add_knowledge(
                    topic=self.name,
                    content=str(content),
                )
            except TypeError:
                try:
                    add_knowledge(
                        self.name,
                        str(content),
                    )
                except Exception:
                    pass
            except Exception:
                pass

    def think(
        self,
        thought: Any,
    ) -> Dict[str, Any]:
        self.room.think(thought)

        return {
            "agent": self.name,
            "thought": thought,
        }

    def plan(
        self,
        steps: List[Any],
    ) -> Dict[str, Any]:
        self.room.set_plan(steps)

        return {
            "agent": self.name,
            "plan": steps,
        }

    # ------------------------------------------------------------------
    # Tools
    # ------------------------------------------------------------------

    def execute_tool(
        self,
        tool_name: str,
        parameters: Optional[Dict[str, Any]] = None,
    ) -> Any:
        parameters = parameters or {}

        execute = getattr(
            self.tools,
            "execute",
            None,
        )

        if not callable(execute):
            return {
                "status": "error",
                "agent": self.name,
                "tool": tool_name,
                "message": (
                    "ToolRegistry does not provide execute()."
                ),
            }

        return execute(
            self.name,
            tool_name,
            parameters,
        )

    def request_tool_approval(
        self,
        tool_name: str,
        parameters: Optional[Dict[str, Any]] = None,
        reason: str = "",
        risk: str = "medium",
    ) -> Any:
        parameters = parameters or {}

        request = getattr(
            self.tools,
            "request_approval",
            None,
        )

        if not callable(request):
            return {
                "status": "error",
                "message": (
                    "ToolRegistry does not provide "
                    "request_approval()."
                ),
            }

        return request(
            agent=self.name,
            tool=tool_name,
            parameters=parameters,
            reason=reason,
            risk=risk,
        )

    def observe_result(
        self,
        result: Any,
    ) -> None:
        self.perceive(result)

    # ------------------------------------------------------------------
    # Tasks
    # ------------------------------------------------------------------

    def create_task(
        self,
        title: str,
        description: str = "",
        priority: int = 5,
        agent: Optional[str] = None,
    ) -> Dict[str, Any]:

        target_agent = agent or self.name

        add_task = getattr(
            self.memory,
            "add_task",
            None,
        )

        if not callable(add_task):
            return {
                "status": "error",
                "message": (
                    "SharedMemory does not provide add_task()."
                ),
            }

        try:
            task = add_task(
                title=title,
                description=description,
                priority=priority,
                agent=target_agent,
            )
        except TypeError:
            task = add_task(
                title,
                description,
                priority,
                target_agent,
            )

        return task

    def get_tasks(self) -> List[Dict[str, Any]]:
        getter = getattr(
            self.memory,
            "get_tasks",
            None,
        )

        if not callable(getter):
            return []

        try:
            result = getter()

            return (
                result
                if isinstance(result, list)
                else []
            )

        except Exception:
            return []

    def get_pending_tasks(self) -> List[Dict[str, Any]]:
        tasks = self.get_tasks()

        return [
            task
            for task in tasks
            if isinstance(task, dict)
            and task.get("status") in {
                "pending",
                "assigned",
                "in_progress",
            }
            and self._task_belongs_to_agent(task)
        ]

    def set_current_task(
        self,
        task: Dict[str, Any],
    ) -> None:
        self.current_task = task

        self.room.remember(
            {
                "event": "current_task",
                "task": task,
            }
        )

        self.update_status("working")

    def complete_current_task(
        self,
        result: Any = None,
    ) -> Any:
        if not self.current_task:
            return None

        task_id = self.current_task.get("id")

        update_task = getattr(
            self.memory,
            "update_task",
            None,
        )

        if callable(update_task) and task_id:
            try:
                updated = update_task(
                    task_id,
                    status="completed",
                    result=result,
                )
            except TypeError:
                try:
                    updated = update_task(
                        task_id=task_id,
                        status="completed",
                        result=result,
                    )
                except Exception:
                    updated = None
        else:
            updated = None

        self.room.complete_plan_step()

        self.current_task = None
        self.update_status("idle")

        return updated

    def fail_current_task(
        self,
        error: Any = None,
    ) -> Any:
        if not self.current_task:
            return None

        task_id = self.current_task.get("id")

        update_task = getattr(
            self.memory,
            "update_task",
            None,
        )

        updated = None

        if callable(update_task) and task_id:
            try:
                updated = update_task(
                    task_id,
                    status="failed",
                    error=error,
                )
            except TypeError:
                try:
                    updated = update_task(
                        task_id=task_id,
                        status="failed",
                        error=error,
                    )
                except Exception:
                    pass

        self.room.fail_plan_step()

        self.current_task = None
        self.update_status("error")

        return updated

    # ------------------------------------------------------------------
    # Objectives
    # ------------------------------------------------------------------

    def set_objective(
        self,
        objective: str,
    ) -> None:
        self.room.set_objective(objective)

        self.remember(
            {
                "event": "objective_set",
                "objective": objective,
            }
        )

    def get_objective(self) -> Optional[str]:
        snapshot = self.room.snapshot()

        return snapshot.get("objective")

    def clear_objective(self) -> None:
        self.room.clear_objective()

    # ------------------------------------------------------------------
    # Messages
    # ------------------------------------------------------------------

    def receive_message(
        self,
        sender: str,
        message: Any,
    ) -> None:
        self.room.receive_message(
            sender=sender,
            message=message,
        )

    def unread_messages(self) -> List[Dict[str, Any]]:
        return self.room.unread_messages()

    # ------------------------------------------------------------------
    # Status
    # ------------------------------------------------------------------

    def update_status(
        self,
        status: str,
    ) -> None:
        self.status = status
        self._publish_status()

    def _publish_status(self) -> None:
        setter = getattr(
            self.memory,
            "set_agent_status",
            None,
        )

        if callable(setter):
            try:
                setter(
                    self.name,
                    {
                        "name": self.name,
                        "role": self.role,
                        "status": self.status,
                        "brain": self.has_brain(),
                    },
                )
                return
            except TypeError:
                try:
                    setter(
                        agent=self.name,
                        status={
                            "name": self.name,
                            "role": self.role,
                            "status": self.status,
                            "brain": self.has_brain(),
                        },
                    )
                    return
                except Exception:
                    pass
            except Exception:
                pass

        try:
            self.memory.world_state.setdefault(
                "agent_status",
                {},
            )

            self.memory.world_state[
                "agent_status"
            ][self.name] = {
                "name": self.name,
                "role": self.role,
                "status": self.status,
                "brain": self.has_brain(),
            }

            self.memory.save()

        except Exception:
            pass

    def get_status_report(self) -> Dict[str, Any]:
        return {
            "status": "success",
            "agent": self.name,
            "role": self.role,
            "state": self.status,
            "brain_attached": self.has_brain(),
            "objective": self.get_objective(),
            "current_task": self.current_task,
            "pending_tasks": len(
                self.get_pending_tasks()
            ),
            "messages": len(
                self.unread_messages()
            ),
        }

    def get_cognitive_state(self) -> Dict[str, Any]:
        return self.room.snapshot()

    def get_help(self) -> Dict[str, Any]:
        return {
            "status": "success",
            "agent": self.name,
            "role": self.role,
            "description": self.description,
            "brain_attached": self.has_brain(),
            "capabilities": [
                "perceive",
                "remember",
                "reason",
                "plan",
                "use tools",
                "create tasks",
                "delegate",
                "learn from observations",
                "maintain cognitive state",
            ],
        }

    # ------------------------------------------------------------------
    # Autonomous cycle
    # ------------------------------------------------------------------

    async def run_cycle(
        self,
        request: Optional[str] = None,
    ) -> Dict[str, Any]:

        objective = (
            request
            or self.get_objective()
        )

        if not objective:
            return {
                "status": "idle",
                "agent": self.name,
                "message": "No active objective.",
            }

        if self.brain is not None:
            return await self.think_with_brain(
                request=objective,
                objective=objective,
            )

        return self._default_task_plan(
            objective
        )

    async def run_autonomous(
        self,
        objective: str,
    ) -> Dict[str, Any]:
        self.set_objective(objective)

        return await self.run_cycle(
            objective
        )

    def _default_task_plan(
        self,
        objective: str,
    ) -> Dict[str, Any]:

        steps = [
            "understand objective",
            "identify missing information",
            "research or inspect available information",
            "analyse findings",
            "produce next action",
        ]

        self.plan(steps)

        return {
            "status": "planned",
            "agent": self.name,
            "objective": objective,
            "plan": steps,
            "message": (
                "No autonomous brain is attached yet."
            ),
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _task_belongs_to_agent(
        self,
        task: Dict[str, Any],
    ) -> bool:

        assigned = (
            task.get("agent")
            or task.get("assigned_to")
        )

        return assigned in {
            None,
            self.name,
        }

    @staticmethod
    def _timestamp() -> str:
        from datetime import datetime, timezone

        return datetime.now(
            timezone.utc
        ).isoformat()
