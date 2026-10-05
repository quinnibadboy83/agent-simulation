"""
Base Agent
----------

Common cognitive and operational foundation for every agent.
"""

from typing import Any, Dict, List, Optional

from core.cognitive_room import CognitiveRoom
from core.memory import SharedMemory
from core.tools import ToolRegistry


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
        self.current_task = None

        self.cognitive_room = CognitiveRoom(
            agent_name=name,
            role=role,
            description=description,
            identity=identity,
        )

        self._publish_status()

        self.memory.log(
            self.name,
            f"Agent initialised: {self.role}",
        )

    # ------------------------------------------------------------------
    # Perception
    # ------------------------------------------------------------------

    def perceive(
        self,
    ) -> Dict[str, Any]:

        tasks = self.memory.get_tasks(
            assigned_to=self.name
        )

        pending = [
            task
            for task in tasks
            if task.get(
                "status"
            ) == "pending"
        ]

        messages = (
            self.cognitive_room.unread_messages()
        )

        observation = {
            "agent": self.name,
            "status": self.status,
            "current_task": self.current_task,
            "pending_tasks": pending,
            "unread_messages": messages,
        }

        self.cognitive_room.observe(
            str(observation),
            "shared_memory",
        )

        return observation

    # ------------------------------------------------------------------
    # Memory
    # ------------------------------------------------------------------

    def remember(
        self,
        content: str,
        category: str = "general",
    ):
        return self.cognitive_room.remember(
            content,
            category,
        )

    # ------------------------------------------------------------------
    # Reasoning
    # ------------------------------------------------------------------

    def think(
        self,
        input_text: str,
    ) -> str:

        input_text = str(
            input_text or ""
        ).strip()

        if not input_text:
            return (
                f"{self.name} has no new "
                "input to reason about."
            )

        self.cognitive_room.observe(
            input_text,
            "input",
        )

        lower = input_text.lower()

        if (
            "status" in lower
            or "report" in lower
        ):
            result = (
                self.get_status_report()
            )

        elif "help" in lower:
            result = self.get_help()

        else:
            self.remember(
                input_text,
                "input",
            )

            result = (
                f"{self.name} received: "
                f"'{input_text}'. "
                "Awaiting clearer orders."
            )

        self.cognitive_room.think(
            result,
            "reasoning",
        )

        return result

    # ------------------------------------------------------------------
    # Planning
    # ------------------------------------------------------------------

    def plan(
        self,
        objective: str,
        steps: Optional[
            List[str]
        ] = None,
    ):

        objective = str(
            objective or ""
        ).strip()

        if not objective:
            self.clear_objective()
            return []

        self.cognitive_room.set_objective(
            objective
        )

        if steps is None:
            steps = [
                f"Understand objective: {objective}",
                "Gather relevant information",
                "Evaluate available options",
                "Select the safest useful action",
                "Execute permitted tools",
                "Observe the result",
                "Record what was learned",
            ]

        self.cognitive_room.set_plan(
            steps
        )

        self.cognitive_room.think(
            f"Created plan for: {objective}",
            "planning",
        )

        self._publish_status()

        return list(
            self.cognitive_room.plan
        )

    # ------------------------------------------------------------------
    # Action
    # ------------------------------------------------------------------

    def act(
        self,
        tool_name: str,
        **kwargs: Any,
    ) -> Dict[str, Any]:

        self.update_status(
            "acting"
        )

        result = self.execute_tool(
            tool_name,
            **kwargs,
        )

        self.observe_result(
            tool_name,
            result,
        )

        if result.get(
            "success"
        ):
            self.update_status(
                "working"
            )

        elif result.get(
            "requires_approval"
        ):
            self.update_status(
                "awaiting_approval"
            )

        else:
            self.update_status(
                "working"
            )

        return result

    def execute_tool(
        self,
        tool_name: str,
        **kwargs: Any,
    ) -> Dict[str, Any]:

        return self.tools.execute(
            tool_name,
            agent=self.name,
            **kwargs,
        )

    # ------------------------------------------------------------------
    # Observation / learning
    # ------------------------------------------------------------------

    def observe_result(
        self,
        tool_name: str,
        result: Dict[str, Any],
    ) -> None:

        self.cognitive_room.observe(
            str(result),
            f"tool:{tool_name}",
        )

        if result.get(
            "success"
        ):
            self.remember(
                (
                    f"Tool '{tool_name}' "
                    "succeeded. "
                    f"Result: {result.get('result')}"
                ),
                "tool_result",
            )

        elif result.get(
            "requires_approval"
        ):
            self.remember(
                (
                    f"Tool '{tool_name}' "
                    "requires Creator approval."
                ),
                "approval",
            )

        else:
            self.remember(
                (
                    f"Tool '{tool_name}' "
                    f"failed or was blocked: "
                    f"{result}"
                ),
                "tool_error",
            )

    # ------------------------------------------------------------------
    # Autonomous cycle
    # ------------------------------------------------------------------

    def run_cycle(
        self,
    ) -> Dict[str, Any]:

        self.update_status(
            "perceiving"
        )

        perception = self.perceive()

        self.update_status(
            "thinking"
        )

        reasoning = self.think(
            str(perception)
        )

        self.update_status(
            "working"
        )

        return {
            "agent": self.name,
            "cycle": "completed",
            "perception": perception,
            "reasoning": reasoning,
            "cognitive_state": (
                self.cognitive_room.snapshot()
            ),
        }

    # ------------------------------------------------------------------
    # Tasks
    # ------------------------------------------------------------------

    def get_current_tasks(
        self,
    ):
        return self.memory.get_tasks(
            assigned_to=self.name
        )

    def get_pending_tasks(
        self,
    ):
        return [
            task
            for task in self.get_current_tasks()
            if task.get(
                "status"
            ) == "pending"
        ]

    def set_current_task(
        self,
        task: Optional[
            Dict[str, Any]
        ],
    ) -> None:

        self.current_task = task

        if task is None:
            self.clear_objective()
            return

        objective = (
            task.get("description")
            or task.get("title", "")
        )

        if objective:
            self.set_objective(
                objective
            )

        self.remember(
            str(task),
            "task",
        )

    # ------------------------------------------------------------------
    # Status
    # ------------------------------------------------------------------

    def get_status_report(
        self,
    ) -> str:

        status = self.memory.get_agent_status(
            self.name
        )

        pending = self.get_pending_tasks()

        report = (
            f"**{self.name}** "
            f"({self.role})\n"
        )

        report += (
            f"Status: "
            f"{status.get('status', 'unknown')}\n"
        )

        report += (
            f"Pending tasks: "
            f"{len(pending)}\n"
        )

        if self.current_task:
            report += (
                "Current task: "
                f"{self.current_task.get('title')}\n"
            )

        if pending:
            report += (
                "Next task: "
                f"{pending[0]['title']}"
            )

        return report

    def get_help(
        self,
    ) -> str:
        return (
            f"I am {self.name}, "
            f"the {self.role}. "
            "I can perceive tasks, maintain "
            "private cognitive state, reason, "
            "plan, use registered tools and "
            "observe results."
        )

    # ------------------------------------------------------------------
    # Communication
    # ------------------------------------------------------------------

    def receive_message(
        self,
        sender: str,
        content: str,
    ):
        message = (
            self.cognitive_room.receive_message(
                sender,
                content,
            )
        )

        self.cognitive_room.think(
            (
                f"Received message from "
                f"{sender}: {content}"
            ),
            "communication",
        )

        return message

    def get_unread_messages(
        self,
    ):
        return (
            self.cognitive_room.unread_messages()
        )

    def mark_messages_read(
        self,
    ):
        self.cognitive_room.mark_messages_read()

    # ------------------------------------------------------------------
    # State
    # ------------------------------------------------------------------

    def update_status(
        self,
        new_status: str,
    ) -> None:

        self.status = new_status

        self._publish_status()

        self.memory.log(
            self.name,
            f"Status changed to: {new_status}",
        )

    def _publish_status(
        self,
    ) -> None:

        self.memory.set_agent_status(
            self.name,
            {
                "role": self.role,
                "status": self.status,
                "description": self.description,
                "current_task": self.current_task,
                "objective": (
                    self.cognitive_room.objective
                ),
            },
        )

    def get_cognitive_state(
        self,
    ):
        return (
            self.cognitive_room.snapshot()
        )

    def set_objective(
        self,
        objective: str,
    ):
        self.cognitive_room.set_objective(
            objective
        )

        self._publish_status()

    def clear_objective(
        self,
    ):
        self.cognitive_room.clear_objective()

        self._publish_status()
