from __future__ import annotations

from typing import Any, Dict, Optional

from .brain_factory import BrainFactory


class AgentBrainManager:
    """
    Creates and attaches one autonomous brain to each agent.

    The manager keeps model configuration centralized while allowing
    every agent to maintain its own cognitive room and objective.
    """

    def __init__(
        self,
        memory=None,
        tools=None,
        config=None,
    ):
        self.memory = memory
        self.tools = tools
        self.factory = BrainFactory(
            config=config
        )

        self.brains: Dict[str, Any] = {}

    def attach(
        self,
        agent,
        objective: Optional[str] = None,
    ):
        brain = self.factory.create(
            agent_name=agent.name,
            memory=self.memory,
            room=agent.room,
            tools=self.tools,
            objective=objective,
        )

        agent.attach_brain(brain)

        self.brains[agent.name] = brain

        return brain

    def attach_all(
        self,
        agents: Dict[str, Any],
    ) -> Dict[str, Any]:

        attached = {}

        for name, agent in agents.items():
            if agent is None:
                continue

            attached[name] = self.attach(
                agent
            )

        return attached

    def get(
        self,
        agent_name: str,
    ):
        return self.brains.get(
            agent_name
        )

    def status(self) -> Dict[str, Any]:
        return {
            name: brain.status()
            for name, brain in self.brains.items()
        }

    async def health(self) -> Dict[str, Any]:
        return await self.factory.health()
