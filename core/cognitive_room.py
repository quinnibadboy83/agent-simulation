"""
Cognitive Room
--------------
Private working environment for an autonomous agent.

The CognitiveRoom separates an agent's private cognitive state
from the shared world/blackboard used by the rest of the simulation.

It stores:
- identity
- objectives
- memories
- thoughts
- observations
- messages
- plans
"""

from datetime import datetime
from typing import Any, Dict, List, Optional


class CognitiveRoom:
    def __init__(
        self,
        agent_name: str,
        role: str,
        description: str = "",
        identity: Optional[str] = None,
    ):
        self.agent_name = agent_name
        self.role = role
        self.description = description

        self.identity = identity or (
            f"You are {agent_name}, a {role}."
        )

        self.objective: Optional[str] = None
        self.status = "idle"

        self.memory: List[Dict[str, Any]] = []
        self.thoughts: List[Dict[str, Any]] = []
        self.messages: List[Dict[str, Any]] = []
        self.observations: List[Dict[str, Any]] = []
        self.plan: List[Dict[str, Any]] = []

    # ------------------------------------------------------------------
    # OBJECTIVES
    # ------------------------------------------------------------------

    def set_objective(self, objective: str) -> None:
        self.objective = objective
        self.status = "working"

        self.think(
            f"Objective set: {objective}",
            kind="objective",
        )

    def clear_objective(self) -> None:
        self.objective = None
        self.status = "idle"
        self.plan = []

    # ------------------------------------------------------------------
    # MEMORY
    # ------------------------------------------------------------------

    def remember(
        self,
        content: str,
        category: str = "general",
    ) -> Dict[str, Any]:
        item = {
            "timestamp": self._timestamp(),
            "category": category,
            "content": content,
        }

        self.memory.append(item)

        # Keep the private room bounded.
        self.memory = self.memory[-200:]

        return item

    # ------------------------------------------------------------------
    # PERCEPTION
    # ------------------------------------------------------------------

    def observe(
        self,
        content: str,
        source: str = "world",
    ) -> Dict[str, Any]:
        item = {
            "timestamp": self._timestamp(),
            "source": source,
            "content": content,
        }

        self.observations.append(item)

        # Keep recent observations.
        self.observations = self.observations[-100:]

        return item

    # ------------------------------------------------------------------
    # THINKING
    # ------------------------------------------------------------------

    def think(
        self,
        content: str,
        kind: str = "reasoning",
    ) -> Dict[str, Any]:
        item = {
            "timestamp": self._timestamp(),
            "kind": kind,
            "content": content,
        }

        self.thoughts.append(item)

        # Keep the private thought history bounded.
        self.thoughts = self.thoughts[-100:]

        return item

    # ------------------------------------------------------------------
    # MESSAGES
    # ------------------------------------------------------------------

    def receive_message(
        self,
        sender: str,
        content: str,
    ) -> Dict[str, Any]:
        item = {
            "timestamp": self._timestamp(),
            "sender": sender,
            "content": content,
            "read": False,
        }

        self.messages.append(item)
        self.messages = self.messages[-100:]

        return item

    def unread_messages(self) -> List[Dict[str, Any]]:
        return [
            message
            for message in self.messages
            if not message.get("read", False)
        ]

    def mark_messages_read(self) -> None:
        for message in self.messages:
            message["read"] = True

    # ------------------------------------------------------------------
    # PLANNING
    # ------------------------------------------------------------------

    def set_plan(self, steps: List[str]) -> None:
        self.plan = [
            {
                "step": index,
                "description": step,
                "status": "pending",
            }
            for index, step in enumerate(steps, start=1)
        ]

    def complete_plan_step(self, step: int) -> bool:
        for item in self.plan:
            if item["step"] == step:
                item["status"] = "completed"
                return True

        return False

    def fail_plan_step(
        self,
        step: int,
        reason: str = "",
    ) -> bool:
        for item in self.plan:
            if item["step"] == step:
                item["status"] = "failed"

                if reason:
                    item["reason"] = reason

                return True

        return False

    # ------------------------------------------------------------------
    # STATE
    # ------------------------------------------------------------------

    def snapshot(self) -> Dict[str, Any]:
        return {
            "agent_name": self.agent_name,
            "role": self.role,
            "description": self.description,
            "identity": self.identity,
            "objective": self.objective,
            "status": self.status,
            "memory": self.memory[-50:],
            "thoughts": self.thoughts[-50:],
            "messages": self.messages[-50:],
            "observations": self.observations[-50:],
            "plan": self.plan,
        }

    # ------------------------------------------------------------------
    # INTERNAL
    # ------------------------------------------------------------------

    @staticmethod
    def _timestamp() -> str:
        return datetime.utcnow().isoformat()
