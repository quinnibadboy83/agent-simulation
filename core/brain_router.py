"""
Brain Router
------------
Routes arbitrary Creator requests into the autonomous agent brain network.

The router does not depend on fixed commands such as:
    search <topic>
    research <topic>

Instead, the Creator can provide a natural-language objective and the
router gives it to the appropriate autonomous brain.

Routing priority:

Creator
   ↓
BrainRouter
   ↓
Boss brain
   ↓
Specialist agents / tools
   ↓
Result
"""

from __future__ import annotations

import inspect
from typing import Any, Dict, Optional


class BrainRouter:
    """
    Central natural-language router for the autonomous agent system.
    """

    def __init__(
        self,
        brain_manager: Any = None,
        agents: Optional[Dict[str, Any]] = None,
        boss: Any = None,
        memory: Any = None,
        tools: Any = None,
        world: Any = None,
        economy: Any = None,
        **kwargs: Any,
    ):
        self.brain_manager = brain_manager
        self.agents = agents or {}
        self.boss = boss
        self.memory = memory
        self.tools = tools
        self.world = world
        self.economy = economy

        self.enabled = (
            self.brain_manager is not None
        )

        self.last_request: Optional[str] = None
        self.last_result: Any = None
        self.request_count = 0

    # ------------------------------------------------------------------
    # Main routing API
    # ------------------------------------------------------------------

    async def route(
        self,
        command: str = "",
        **kwargs: Any,
    ) -> Any:
        """
        Primary natural-language routing method.
        """

        return await self.process(
            command=command,
            **kwargs,
        )

    async def process(
        self,
        command: str = "",
        **kwargs: Any,
    ) -> Any:
        """
        Process an arbitrary Creator objective.
        """

        command = str(command or "").strip()

        if not command:
            return {
                "status": "error",
                "message": "No Creator objective was supplied.",
            }

        if not self.enabled:
            raise RuntimeError(
                "BrainRouter is disabled because the "
                "AgentBrainManager is unavailable."
            )

        self.last_request = command
        self.request_count += 1

        # Always prefer Boss as the primary coordinating brain.
        boss_brain = self._get_brain("Boss")

        if boss_brain is not None:
            result = await self._run_brain(
                boss_brain,
                command,
            )

            self.last_result = result

            return {
                "status": "success",
                "router": "BrainRouter",
                "agent": "Boss",
                "objective": command,
                "result": self._serialise(result),
            }

        # If Boss has no brain, select a suitable specialist.
        specialist = self._select_specialist(
            command
        )

        if specialist is not None:
            agent_name, brain = specialist

            result = await self._run_brain(
                brain,
                command,
            )

            self.last_result = result

            return {
                "status": "success",
                "router": "BrainRouter",
                "agent": agent_name,
                "objective": command,
                "result": self._serialise(result),
            }

        raise RuntimeError(
            "No active autonomous brain is available."
        )

    async def handle(
        self,
        command: str = "",
        **kwargs: Any,
    ) -> Any:
        return await self.process(
            command=command,
            **kwargs,
        )

    async def dispatch(
        self,
        command: str = "",
        **kwargs: Any,
    ) -> Any:
        return await self.process(
            command=command,
            **kwargs,
        )

    async def run(
        self,
        command: str = "",
        **kwargs: Any,
    ) -> Any:
        return await self.process(
            command=command,
            **kwargs,
        )

    async def route_command(
        self,
        command: str = "",
        **kwargs: Any,
    ) -> Any:
        return await self.process(
            command=command,
            **kwargs,
        )

    # ------------------------------------------------------------------
    # Brain execution
    # ------------------------------------------------------------------

    async def _run_brain(
        self,
        brain: Any,
        command: str,
    ) -> Any:
        """
        Execute the supplied objective against an AutonomousBrain.

        Different compatible brain interfaces are supported because the
        brain layer is still being assembled.
        """

        if brain is None:
            raise RuntimeError(
                "Cannot execute a missing brain."
            )

        # The AutonomousBrain.run() method is the preferred interface.
        run_method = getattr(
            brain,
            "run",
            None,
        )

        if callable(run_method):

            attempts = [
                lambda: run_method(
                    command
                ),
                lambda: run_method(
                    objective=command
                ),
                lambda: run_method(
                    prompt=command
                ),
            ]

            for attempt in attempts:
                try:
                    result = attempt()

                    if inspect.isawaitable(result):
                        result = await result

                    return result

                except TypeError:
                    continue

        # Compatibility with brains exposing think().
        think_method = getattr(
            brain,
            "think",
            None,
        )

        if callable(think_method):

            attempts = [
                lambda: think_method(
                    command
                ),
                lambda: think_method(
                    prompt=command
                ),
                lambda: think_method(
                    objective=command
                ),
            ]

            for attempt in attempts:
                try:
                    result = attempt()

                    if inspect.isawaitable(result):
                        result = await result

                    return result

                except TypeError:
                    continue

        # Compatibility with reason().
        reason_method = getattr(
            brain,
            "reason",
            None,
        )

        if callable(reason_method):

            attempts = [
                lambda: reason_method(
                    command
                ),
                lambda: reason_method(
                    prompt=command
                ),
                lambda: reason_method(
                    objective=command
                ),
            ]

            for attempt in attempts:
                try:
                    result = attempt()

                    if inspect.isawaitable(result):
                        result = await result

                    return result

                except TypeError:
                    continue

        raise RuntimeError(
            "The autonomous brain does not expose "
            "a compatible run(), think(), or reason() method."
        )

    # ------------------------------------------------------------------
    # Brain lookup
    # ------------------------------------------------------------------

    def _get_brain(
        self,
        agent_name: str,
    ) -> Any:

        if self.brain_manager is not None:

            getter = getattr(
                self.brain_manager,
                "get_brain",
                None,
            )

            if callable(getter):

                try:
                    brain = getter(
                        agent_name
                    )

                    if brain is not None:
                        return brain

                except Exception:
                    pass

            getter = getattr(
                self.brain_manager,
                "get",
                None,
            )

            if callable(getter):

                try:
                    brain = getter(
                        agent_name
                    )

                    if brain is not None:
                        return brain

                except Exception:
                    pass

            brains = getattr(
                self.brain_manager,
                "brains",
                {},
            )

            if isinstance(brains, dict):
                brain = brains.get(
                    agent_name
                )

                if brain is not None:
                    return brain

        agent = self.agents.get(
            agent_name
        )

        if agent is not None:
            brain = getattr(
                agent,
                "brain",
                None,
            )

            if brain is not None:
                return brain

        return None

    # ------------------------------------------------------------------
    # Specialist selection
    # ------------------------------------------------------------------

    def _select_specialist(
        self,
        command: str,
    ):
        """
        Basic semantic hinting used only when Boss has no brain.

        Once Boss is active, Boss itself is responsible for deciding
        whether to delegate.
        """

        text = command.lower()

        candidates = []

        if any(
            word in text
            for word in (
                "research",
                "researching",
                "find out",
                "information",
                "source",
                "sources",
                "crypto",
                "bitcoin",
                "ethereum",
                "market",
                "news",
                "investigate",
            )
        ):
            candidates.append(
                "InfoFarmer"
            )

        if any(
            word in text
            for word in (
                "money",
                "finance",
                "financial",
                "balance",
                "income",
                "expense",
                "transaction",
                "profit",
                "revenue",
            )
        ):
            candidates.append(
                "Banker"
            )

        if any(
            word in text
            for word in (
                "opportunity",
                "opportunities",
                "business",
                "idea",
                "ideas",
                "revenue",
                "affiliate",
                "software",
                "saas",
                "content",
                "social",
                "instagram",
                "youtube",
                "tiktok",
                "reddit",
            )
        ):
            candidates.append(
                "OpportunityAgent"
            )

        for name in candidates:

            brain = self._get_brain(
                name
            )

            if brain is not None:
                return name, brain

        # Last-resort specialist.
        for name in (
            "InfoFarmer",
            "OpportunityAgent",
            "Banker",
        ):

            brain = self._get_brain(
                name
            )

            if brain is not None:
                return name, brain

        return None

    # ------------------------------------------------------------------
    # Status
    # ------------------------------------------------------------------

    def status(self) -> Dict[str, Any]:

        active_brains = {}

        if self.brain_manager is not None:

            manager_status = getattr(
                self.brain_manager,
                "status",
                None,
            )

            if callable(manager_status):

                try:
                    active_brains = manager_status()
                except Exception as exc:
                    active_brains = {
                        "error": str(exc)
                    }

        return {
            "router": "BrainRouter",
            "enabled": self.enabled,
            "request_count": self.request_count,
            "last_request": self.last_request,
            "active_brains": self._serialise(
                active_brains
            ),
        }

    # ------------------------------------------------------------------
    # Reset
    # ------------------------------------------------------------------

    def reset(self) -> Dict[str, Any]:

        self.last_request = None
        self.last_result = None
        self.request_count = 0

        return {
            "status": "reset",
            "router": "BrainRouter",
        }

    # ------------------------------------------------------------------
    # Serialisation
    # ------------------------------------------------------------------

    def _serialise(
        self,
        value: Any,
    ) -> Any:

        if value is None:
            return None

        if isinstance(
            value,
            (
                str,
                int,
                float,
                bool,
            ),
        ):
            return value

        if isinstance(value, dict):
            return {
                str(key): self._serialise(
                    item
                )
                for key, item in value.items()
            }

        if isinstance(
            value,
            (
                list,
                tuple,
                set,
            ),
        ):
            return [
                self._serialise(item)
                for item in value
            ]

        if hasattr(
            value,
            "model_dump",
        ):
            try:
                return self._serialise(
                    value.model_dump()
                )
            except Exception:
                pass

        if hasattr(
            value,
            "__dict__",
        ):
            try:
                return self._serialise(
                    vars(value)
                )
            except Exception:
                pass

        return str(value)
