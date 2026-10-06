"""
Base Agent
----------

Common foundation for every autonomous agent.
"""

from typing import Any, Dict, List, Optional

from core.memory import SharedMemory
from core.tools import ToolRegistry
from core.cognitive_room import CognitiveRoom


class BaseAgent:
    def __init__(
        self,
        name: str,
        role: str,
        memory: SharedMemory,
        tools: ToolRegistry,
        description: str = "",
        identity: Optional[str] = None,
    ):
        self.name = name
        self.role = role
        self.memory = memory
        self.tools = tools
        self.description = description

        self.status = "idle"
        self.current_task: Optional[
            Dict[str, Any]
        ] = None

        self.cognitive_room = CognitiveRoom(
            agent_name=name,
            role=role,
            description=description,
            identity=identity,
        )

        self.memory.set_agent_status(
            self.name,
            {
                "role": self.role,
                "status": self.status,
                "description": self.description,
                "objective": None,
                "current_task": None,
            },
        )

    # ---------------------------------------------------------
    # PERCEPTION / MEMORY / REASONING
    # ---------------------------------------------------------

    def perceive(
        self,
        input_text: str,
        source: str = "command",
    ):
        observation = self.cognitive_room.observe(
            input_text,
            source=source,
        )

        self.memory.log(
            self.name,
            f"Perceived: {input_text}",
        )

        return observation

    def remember(
        self,
        content: str,
        category: str = "general",
    ):
        return self.cognitive_room.remember(
            content,
            category=category,
        )

    def think(
        self,
        input_text: str,
    ):
        self.cognitive_room.think(
            f"Considering input: {input_text}",
            kind="reasoning",
        )

        lowered = input_text.lower()

        if (
            "status" in lowered
            or "report" in lowered
        ):
            return self.get_status_report()

        if "help" in lowered:
            return self.get_help()

        return (
            f"{self.name} received: "
            f"'{input_text}'. "
            "Awaiting a clearer objective."
        )

    # ---------------------------------------------------------
    # PLANNING
    # ---------------------------------------------------------

    def plan(
        self,
        steps: List[str],
    ):
        self.cognitive_room.set_plan(
            steps
        )

    # ---------------------------------------------------------
    # TOOLS
    # ---------------------------------------------------------

    def execute_tool(
        self,
        tool_name: str,
        **kwargs,
    ):
        tool_agent = kwargs.pop(
            "agent",
            self.name,
        )

        result = self.tools.execute(
            tool_name,
            agent=tool_agent,
            **kwargs,
        )

        self.observe_result(
            result,
            source=f"tool:{tool_name}",
        )

        return result

    def request_tool_approval(
        self,
        tool_name: str,
        parameters: Dict[str, Any],
        description: Optional[str] = None,
        risk: str = "high",
    ):
        return self.tools.request_approval(
            tool_name=tool_name,
            agent=self.name,
            parameters=parameters,
            description=description,
            risk=risk,
        )

    def observe_result(
        self,
        result: Any,
        source: str = "tool",
    ):
        self.cognitive_room.observe(
            str(result),
            source=source,
        )

        self.cognitive_room.remember(
            str(result),
            category="result",
        )

    # ---------------------------------------------------------
    # TASKS
    # ---------------------------------------------------------

    def get_tasks(self):
        return self.memory.get_tasks(
            assigned_to=self.name
        )

    def get_pending_tasks(self):
        return [
            task
            for task in self.get_tasks()
            if task.get("status") == "pending"
        ]

    def set_current_task(
        self,
        task: Optional[Dict[str, Any]],
    ):
        self.current_task = task

        if task:
            objective = (
                task.get("description")
                or task.get("title")
                or "Complete assigned task"
            )

            self.cognitive_room.set_objective(
                objective
            )
        else:
            self.cognitive_room.clear_objective()

        self._publish_status()

    def complete_current_task(
        self,
        notes: str = "",
    ):
        if not self.current_task:
            return None

        task_id = self.current_task.get(
            "id"
        )

        result = self.memory.update_task(
            task_id,
            "completed",
            notes=notes,
        )

        self.set_current_task(None)

        return result

    def fail_current_task(
        self,
        reason: str = "",
    ):
        if not self.current_task:
            return None

        task_id = self.current_task.get(
            "id"
        )

        result = self.memory.update_task(
            task_id,
            "failed",
            notes=reason,
        )

        self.set_current_task(None)

        return result

    # ---------------------------------------------------------
    # OBJECTIVES
    # ---------------------------------------------------------

    def set_objective(
        self,
        objective: str,
    ):
        self.cognitive_room.set_objective(
            objective
        )

        self._publish_status()

    def clear_objective(self):
        self.cognitive_room.clear_objective()
        self._publish_status()

    # ---------------------------------------------------------
    # COMMUNICATION
    # ---------------------------------------------------------

    def receive_message(
        self,
        sender: str,
        message: str,
    ):
        return self.cognitive_room.receive_message(
            sender,
            message,
        )

    def unread_messages(self):
        return self.cognitive_room.unread_messages()

    # ---------------------------------------------------------
    # STATUS
    # ---------------------------------------------------------

    def update_status(
        self,
        new_status: str,
    ):
        self.status = new_status
        self.cognitive_room.status = new_status

        self._publish_status()

        self.memory.log(
            self.name,
            f"Status changed to: {new_status}",
        )

    def _publish_status(self):
        self.memory.set_agent_status(
            self.name,
            {
                "role": self.role,
                "status": self.status,
                "description": self.description,
                "objective": (
                    self.cognitive_room.objective
                ),
                "current_task": self.current_task,
            },
        )

    # ---------------------------------------------------------
    # REPORTING
    # ---------------------------------------------------------

    def get_status_report(self):
        status = self.memory.get_agent_status(
            self.name
        )

        pending = self.get_pending_tasks()

        report = (
            f"**{self.name}** "
            f"({self.role})\n"
            f"Status: "
            f"{status.get('status', 'unknown')}\n"
            f"Pending tasks: "
            f"{len(pending)}\n"
        )

        objective = (
            self.cognitive_room.objective
        )

        if objective:
            report += (
                f"Objective: {objective}\n"
            )

        if pending:
            report += (
                "Next task: "
                + pending[0].get(
                    "title",
                    "Untitled",
                )
            )

        return report

    def get_help(self):
        return (
            f"I am {self.name}, "
            f"the {self.role}. "
            "Give me a clear objective or task "
            "and I will work through the tools "
            "available to me."
        )

    # ---------------------------------------------------------
    # COGNITIVE STATE
    # ---------------------------------------------------------

    def get_cognitive_state(self):
        return self.cognitive_room.snapshot()

    # ---------------------------------------------------------
    # AUTONOMOUS CYCLE
    # ---------------------------------------------------------

    def run_cycle(
        self,
        input_text: str,
    ):
        self.update_status(
            "thinking"
        )

        try:
            self.perceive(
                input_text
            )

            self.remember(
                input_text,
                category="input",
            )

            reasoning = self.think(
                input_text
            )

            self.cognitive_room.think(
                str(reasoning),
                kind="reasoning_result",
            )

            return {
                "success": True,
                "agent": self.name,
                "input": input_text,
                "reasoning": reasoning,
                "cognitive_state": (
                    self.get_cognitive_state()
                ),
            }

        except Exception as exc:
            self.memory.log(
                self.name,
                (
                    f"Cycle failed: "
                    f"{str(exc)}"
                ),
                level="error",
            )

            return {
                "success": False,
                "agent": self.name,
                "input": input_text,
                "error": str(exc),
            }

        finally:
            self.update_status(
                "idle"
            )
