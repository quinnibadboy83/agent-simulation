"""
Base Agent
----------

Common cognitive and operational foundation for all agents.

Every specialised agent inherits from this class.

Architecture:

    Perceive
        ↓
    Remember
        ↓
    Think
        ↓
    Plan
        ↓
    Select Tool
        ↓
    ToolRegistry
        ↓
    Observe Result
        ↓
    Learn / Continue

Important:

    BaseAgent does NOT execute tools directly.

    All tool execution passes through ToolRegistry so that:
        - operating mode is enforced
        - simulation/live restrictions are enforced
        - protected actions require Creator approval
        - approvals are tied to exact parameters
        - execution is logged
"""

from typing import Any, Dict, List, Optional

from core.memory import SharedMemory
from core.tools import ToolRegistry
from core.cognitive_room import CognitiveRoom


class BaseAgent:
    """
    Common parent class for every autonomous agent.

    Specialised agents should override or extend:
        - think()
        - perceive()
        - plan()
        - act()

    They should NOT bypass ToolRegistry when executing tools.
    """

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

        # ---------------------------------------------------------
        # Private cognitive environment
        # ---------------------------------------------------------

        self.cognitive_room = CognitiveRoom(
            agent_name=self.name,
            role=self.role,
            description=self.description,
            identity=identity,
        )

        # ---------------------------------------------------------
        # Register initial public status
        # ---------------------------------------------------------

        self._publish_status()

        self.memory.log(
            self.name,
            f"Agent initialised: {self.role}",
        )

    # =============================================================
    # COGNITIVE LIFECYCLE
    # =============================================================

    def perceive(self) -> Dict[str, Any]:
        """
        Gather the information currently relevant to this agent.

        This method is intentionally conservative.

        It reads shared state and the agent's assigned tasks but does
        not perform external actions.
        """

        tasks = self.memory.get_tasks(
            assigned_to=self.name
        )

        pending_tasks = [
            task
            for task in tasks
            if task.get("status") == "pending"
        ]

        unread_messages = (
            self.cognitive_room.unread_messages()
        )

        observation = {
            "agent": self.name,
            "status": self.status,
            "current_task": self.current_task,
            "pending_tasks": pending_tasks,
            "unread_messages": unread_messages,
        }

        self.cognitive_room.observe(
            content=str(observation),
            source="shared_memory",
        )

        return observation

    def remember(
        self,
        content: str,
        category: str = "general",
    ) -> Dict[str, Any]:
        """
        Store information in the agent's private cognitive memory.
        """

        return self.cognitive_room.remember(
            content=content,
            category=category,
        )

    def think(self, input_text: str) -> str:
        """
        Basic reasoning layer.

        This is deliberately simple for now.

        Later this method becomes the common integration point for
        an external/local reasoning model such as DeepSeek.

        The model will produce reasoning/plans, but actual execution
        will still be forced through ToolRegistry.
        """

        input_text = str(input_text or "").strip()

        if not input_text:
            return (
                f"{self.name} has no new input to reason about."
            )

        input_lower = input_text.lower()

        # Record the incoming cognitive stimulus.
        self.cognitive_room.observe(
            content=input_text,
            source="input",
        )

        # Existing status/report behaviour is preserved.
        if (
            "status" in input_lower
            or "report" in input_lower
        ):
            result = self.get_status_report()

            self.cognitive_room.think(
                result,
                kind="status_reasoning",
            )

            return result

        if "help" in input_lower:
            result = self.get_help()

            self.cognitive_room.think(
                result,
                kind="help_reasoning",
            )

            return result

        # Remember the request.
        self.remember(
            input_text,
            category="input",
        )

        result = (
            f"{self.name} received: "
            f"'{input_text}'. "
            "Awaiting clearer orders from Boss."
        )

        self.cognitive_room.think(
            result,
            kind="reasoning",
        )

        return result

    def plan(
        self,
        objective: str,
        steps: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Create a private execution plan.

        No external action occurs here.

        A later AI brain can replace the simple step input with
        generated plans.
        """

        objective = str(objective or "").strip()

        if not objective:
            self.cognitive_room.clear_objective()
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
            f"Created plan for objective: {objective}",
            kind="planning",
        )

        return list(
            self.cognitive_room.plan
        )

    def act(
        self,
        tool_name: str,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Execute a tool through the central ToolRegistry.

        This method intentionally contains no direct function
        execution.

        ToolRegistry remains the security boundary.
        """

        self.update_status(
            "acting"
        )

        result = self.execute_tool(
            tool_name,
            **kwargs,
        )

        self.observe_result(
            tool_name=tool_name,
            result=result,
        )

        if result.get("success"):
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

    def observe_result(
        self,
        tool_name: str,
        result: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Feed a tool result back into the agent's private cognitive room.
        """

        observation = {
            "tool": tool_name,
            "result": result,
        }

        self.cognitive_room.observe(
            content=str(observation),
            source=f"tool:{tool_name}",
        )

        if result.get("success"):
            self.remember(
                (
                    f"Tool '{tool_name}' succeeded. "
                    f"Result: {result.get('result')}"
                ),
                category="tool_result",
            )

            self.cognitive_room.think(
                (
                    f"Observed successful execution of "
                    f"'{tool_name}'."
                ),
                kind="observation",
            )

        elif result.get(
            "requires_approval"
        ):
            self.remember(
                (
                    f"Tool '{tool_name}' requires Creator "
                    f"approval. Result: {result}"
                ),
                category="approval",
            )

            self.cognitive_room.think(
                (
                    f"Execution of '{tool_name}' is waiting "
                    "for Creator approval."
                ),
                kind="approval_wait",
            )

        else:
            self.remember(
                (
                    f"Tool '{tool_name}' failed or was blocked. "
                    f"Result: {result}"
                ),
                category="tool_error",
            )

            self.cognitive_room.think(
                (
                    f"Observed failure or blocking of "
                    f"'{tool_name}'."
                ),
                kind="error_analysis",
            )

        return observation

    def run_cycle(self) -> Dict[str, Any]:
        """
        Perform one autonomous cognitive cycle.

        This is the common loop that specialised agents can later
        customise.

        Current implementation is deliberately non-destructive:
        it perceives and reasons but does not invent consequential
        actions.

        Future AI-driven agents can use the resulting cognitive state
        to select tools, while ToolRegistry remains the final gate.
        """

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

    # =============================================================
    # TOOL EXECUTION
    # =============================================================

    def execute_tool(
        self,
        tool_name: str,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Execute a registered tool.

        All execution is delegated to ToolRegistry.

        The agent therefore cannot bypass:
            - simulation mode
            - live mode
            - Creator approval
            - approval parameter matching
            - execution logging
        """

        return self.tools.execute(
            tool_name,
            agent=self.name,
            **kwargs,
        )

    # =============================================================
    # TASK MANAGEMENT
    # =============================================================

    def get_current_tasks(
        self,
    ) -> List[Dict[str, Any]]:
        """
        Return all tasks assigned to this agent.
        """

        return self.memory.get_tasks(
            assigned_to=self.name
        )

    def get_pending_tasks(
        self,
    ) -> List[Dict[str, Any]]:
        """
        Return pending tasks assigned to this agent.
        """

        tasks = self.get_current_tasks()

        return [
            task
            for task in tasks
            if task.get("status") == "pending"
        ]

    def set_current_task(
        self,
        task: Optional[Dict[str, Any]],
    ) -> None:
        """
        Set the task currently being worked on.
        """

        self.current_task = task

        if task is None:
            self.cognitive_room.clear_objective()
            return

        objective = task.get(
            "description"
        ) or task.get(
            "title",
            "",
        )

        if objective:
            self.cognitive_room.set_objective(
                objective
            )

        self.cognitive_room.remember(
            str(task),
            category="task",
        )

    # =============================================================
    # STATUS / COMMUNICATION
    # =============================================================

    def get_status_report(self) -> str:
        """
        Generate a human-readable status report.
        """

        status = self.memory.get_agent_status(
            self.name
        )

        tasks = self.memory.get_tasks(
            assigned_to=self.name
        )

        pending = [
            task
            for task in tasks
            if task.get("status") == "pending"
        ]

        report = (
            f"**{self.name}** ({self.role})\n"
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
                f"{self.current_task.get('title', 'unknown')}\n"
            )

        if pending:
            report += (
                "Next task: "
                f"{pending[0]['title']}"
            )

        return report

    def get_help(self) -> str:
        """
        Return the agent's basic capabilities.
        """

        return (
            f"I am {self.name}, the {self.role}. "
            "I can perceive tasks, maintain private cognitive "
            "state, reason about objectives, create plans, "
            "use registered tools, and observe their results."
        )

    def receive_message(
        self,
        sender: str,
        content: str,
    ) -> Dict[str, Any]:
        """
        Receive a private cognitive message.

        Messages are stored in the agent's CognitiveRoom rather
        than being automatically placed into the shared world.
        """

        message = self.cognitive_room.receive_message(
            sender=sender,
            content=content,
        )

        self.cognitive_room.think(
            (
                f"Received message from {sender}: "
                f"{content}"
            ),
            kind="communication",
        )

        return message

    def get_unread_messages(
        self,
    ) -> List[Dict[str, Any]]:
        """
        Return unread private messages.
        """

        return self.cognitive_room.unread_messages()

    def mark_messages_read(
        self,
    ) -> None:
        """
        Mark all private messages as read.
        """

        self.cognitive_room.mark_messages_read()

    # =============================================================
    # STATUS CONTROL
    # =============================================================

    def update_status(
        self,
        new_status: str,
    ) -> None:
        """
        Update both local and shared agent status.
        """

        self.status = new_status

        self._publish_status()

        self.memory.log(
            self.name,
            f"Status changed to: {new_status}",
        )

    def _publish_status(
        self,
    ) -> None:
        """
        Publish public status without exposing the entire private
        cognitive room.
        """

        self.memory.set_agent_status(
            self.name,
            {
                "role": self.role,
                "status": self.status,
                "description": self.description,
                "current_task": (
                    self.current_task
                ),
                "objective": (
                    self.cognitive_room.objective
                ),
            },
        )

    # =============================================================
    # COGNITIVE STATE
    # =============================================================

    def get_cognitive_state(
        self,
    ) -> Dict[str, Any]:
        """
        Return a snapshot of the agent's private cognitive state.
        """

        return self.cognitive_room.snapshot()

    def set_objective(
        self,
        objective: str,
    ) -> None:
        """
        Set the agent's current cognitive objective.
        """

        self.cognitive_room.set_objective(
            objective
        )

        self._publish_status()

    def clear_objective(
        self,
    ) -> None:
        """
        Clear the current cognitive objective.
        """

        self.cognitive_room.clear_objective()

        self._publish_status()



