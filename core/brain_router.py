from __future__ import annotations

from typing import Any, Dict, Optional


class BrainRouter:
    """
    Routes arbitrary Creator requests into an agent's autonomous brain.

    This is intentionally NOT a command parser.

    The request is treated as natural language and passed to the LLM.
    The model decides what tools, research, reasoning and delegation
    are appropriate.
    """

    def __init__(
        self,
        agents: Optional[Dict[str, Any]] = None,
        default_agent: str = "Boss",
    ):
        self.agents = agents or {}
        self.default_agent = default_agent

    def register_agent(
        self,
        agent,
    ) -> None:
        self.agents[agent.name] = agent

    def register_agents(
        self,
        agents: Dict[str, Any],
    ) -> None:
        for agent in agents.values():
            self.register_agent(agent)

    async def route(
        self,
        request: str,
        agent_name: Optional[str] = None,
    ) -> Dict[str, Any]:

        target_name = (
            agent_name
            or self.default_agent
        )

        agent = self.agents.get(
            target_name
        )

        if agent is None:
            return {
                "status": "error",
                "message": (
                    f"Agent '{target_name}' "
                    "is not registered."
                ),
                "available_agents": list(
                    self.agents.keys()
                ),
            }

        if not agent.has_brain():
            return {
                "status": "brain_unavailable",
                "agent": target_name,
                "message": (
                    f"Agent '{target_name}' "
                    "does not have an autonomous brain."
                ),
            }

        return await agent.think_with_brain(
            request=request,
            objective=request,
        )

    def status(self) -> Dict[str, Any]:
        return {
            "default_agent": self.default_agent,
            "agents": {
                name: {
                    "brain_attached": agent.has_brain(),
                    "status": agent.status,
                }
                for name, agent in self.agents.items()
            },
        }
