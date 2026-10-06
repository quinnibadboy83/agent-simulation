from __future__ import annotations

from typing import Any, Dict, Optional

from .brain import AutonomousBrain
from .brain_config import BrainConfig
from .llm import LLMClient


class BrainFactory:
    """
    Central factory for creating autonomous brains.

    Keeping construction here means the rest of the application does
    not need to know which model provider is being used.
    """

    def __init__(
        self,
        config: Optional[BrainConfig] = None,
    ):
        self.config = (
            config
            or BrainConfig.from_environment()
        )

        self.llm = LLMClient(
            self.config
        )

    def create(
        self,
        agent_name: str,
        memory=None,
        room=None,
        tools=None,
        objective: Optional[str] = None,
    ) -> AutonomousBrain:

        return AutonomousBrain(
            agent_name=agent_name,
            memory=memory,
            room=room,
            tools=tools,
            llm=self.llm,
            config=self.config,
            objective=objective,
        )

    def status(self) -> Dict[str, Any]:
        return {
            "status": "ready"
            if self.config.enabled
            else "disabled",
            "configuration": self.config.public(),
        }

    async def health(self) -> Dict[str, Any]:
        return await self.llm.health()
