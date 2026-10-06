"""
Base Agent
----------
Common foundation for every autonomous agent.

Each agent has:

- a public/shared state
- a private CognitiveRoom
- tools
- tasks
- objectives
- status
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

    # ------------------------------------------------------------------
    # Perception
    # ------------------------------------------------------------------

    def perceive(
        self,
        input_text: str,
        source: str = "command",
    ) -> Dict[str, Any]:

        observation = self.cognitive_room.observe(
            input_text,
            source=source,
        )

        self.memory.log(
            self.name,
            f"Perceived: {input_text}",
        )

        return observation

    # ------------------------------------------------------------------
    # Memory
    # ------------------------------------------------------------------

    def remember(
        self,
        content: str,
        category: str = "general",
    ) -> Dict[str, Any]:

        return self.cognitive_room.remember(
            content,
            category=category,
        )

    # ------------------------------------------------------------------
    # Reasoning
    # ------------------------------------------------------------------

    def think(
        self,
        input_text: str,
    ) -> str:

        input_lower = input_text.lower()

        self.cognitive_room.think(
            f"Considering input: {input_text}",
            kind="reasoning",
        )

        if (
            "status" in input_lower
            or "report" in input_lower
        ):
            return self.get_status_report()

        if "help" in input_lower:
            return self.get_help()

        return (
            f"{self.name} received: "
            f"'{input_text}'. "
            "Awaiting clearer instructions."
        )

    # ------------------------------------------------------------------
    # Planning
    # ------------------------------------------------------------------

    def plan(
        self,
        steps: List[str],
    ) -> None:

        self.cognitive_room.set_plan(
            steps
        )

    # ------------------------------------------------------------------
    # Tool execution
    # ------------------------------------------------------------------

    def execute_tool(
        self,
        tool_name: str,
        **kwargs: Any,
    ) -> Dict[str, Any]:

        # Some older agents pass their own "agent" keyword.
        # Prevent Python from receiving two values for agent.
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

    # ------------------------------------------------------------------
    # Observation / learning
    # ------------------------------------------------------------------

    def observe_result(
        self,
        result: Any,
        source: str = "tool",
    ) -> None:

        self.cognitive_room.observe(
            str(result),
            source=source,
        )

        self.cognitive_room.remember(
            str(result),
            category="result",
        )

    # ------------------------------------------------------------------
    # Tasks
    # ------------------------------------------------------------------

    def get_tasks(
        self,
    ) -> List[Dict[str, Any]]:

        return self.memory.get_tasks(
            assigned_to=self.name,
        )

    def get_pending_tasks(
        self,
    ) -> List[Dict[str, Any]]:

        return [
            task
            for task in self.get_tasks()
            if task.get("status")
            == "pending"
        ]

    def set_current_task(
        self,
        task: Optional[Dict[str, Any]],
    ) -> None:

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
            f"**{self.name}** ({self.role})\n"
            f"Status: "
            f"{status.get('status', 'unknown')}\n"
            f"Pending tasks: {len(pending)}\n"
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

    def get_help(
        self,
    ) -> str:

        return (
            f"I am {self.name}, "
            f"the {self.role}. "
            "Give me a clear objective or "
            "task and I will work through "
            "the available tools."
        )

    # ------------------------------------------------------------------
    # Objectives
    # ------------------------------------------------------------------

    def set_objective(
        self,
        objective: str,
    ) -> None:

        self.cognitive_room.set_objective(
            objective
        )

        self._publish_status()

    def clear_objective(
        self,
    ) -> None:

        self.cognitive_room.clear_objective()

        self._publish_status()

    # ------------------------------------------------------------------
    # Messages
    # ------------------------------------------------------------------

    def receive_message(
        self,
        sender: str,
        message: str,
    ) -> None:

        self.cognitive_room.receive_message(
            sender,
            message,
        )

    def unread_messages(
        self,
    ) -> List[Dict[str, Any]]:

        return (
            self.cognitive_room
            .unread_messages()
        )

    # ------------------------------------------------------------------
    # Status updates
    # ------------------------------------------------------------------

    def update_status(
        self,
        new_status: str,
    ) -> None:

        self.status = new_status

        self.cognitive_room.status = (
            new_status
        )

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
                "objective": (
                    self.cognitive_room.objective
                ),
                "current_task": (
                    self.current_task
                ),
            },
        )

    # ------------------------------------------------------------------
    # Cognitive state
    # ------------------------------------------------------------------

    def get_cognitive_state(
        self,
    ) -> Dict[str, Any]:

        return self.cognitive_room.snapshot()

    # ------------------------------------------------------------------
    # Standard autonomous cycle
    # ------------------------------------------------------------------

    def run_cycle(
        self,
        input_text: str,
    ) -> Dict[str, Any]:

        self.update_status(
            "thinking"
        )

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
            reasoning,
            kind="reasoning_result",
        )

        self.update_status(
            "idle"
        )

        return {
            "agent": self.name,
            "input": input_text,
            "reasoning": reasoning,
            "cognitive_state": (
                self.get_cognitive_state()
            ),
        }
