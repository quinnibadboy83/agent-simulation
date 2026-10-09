
"""
Brain Router
------------
Routes arbitrary Creator requests to the autonomous agent network.

Boss is the primary coordinating brain. Specialist agents are used
when Boss is unavailable. Routing is task-agnostic: the Creator may
request research, writing, analysis, planning, coding, or other work.
"""

from __future__ import annotations

import inspect
from typing import Any, Dict, Optional


class BrainRouter:
    """Central natural-language router for the agent system."""

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
    ) -> None:
        self.brain_manager = brain_manager
        self.agents = agents or {}
        self.boss = boss
        self.memory = memory
        self.tools = tools
        self.world = world
        self.economy = economy

        self.enabled = brain_manager is not None
        self.last_request: Optional[str] = None
        self.last_result: Any = None
        self.last_status: Optional[str] = None
        self.request_count = 0

    async def route(self, command: str = "", **kwargs: Any) -> Any:
        return await self.process(command=command, **kwargs)

    async def process(self, command: str = "", **kwargs: Any) -> Any:
        """Run an arbitrary Creator objective through an available brain."""
        command = str(command or "").strip()

        if not command:
            return {
                "status": "error",
                "router": "BrainRouter",
                "message": "No Creator objective was supplied.",
            }

        if not self.enabled:
            raise RuntimeError(
                "BrainRouter is disabled because AgentBrainManager "
                "is unavailable."
            )

        self.last_request = command
        self.request_count += 1

        brain = self._get_brain("Boss")
        agent_name = "Boss"

        if brain is None:
            specialist = self._select_specialist(command)
            if specialist is not None:
                agent_name, brain = specialist

        if brain is None:
            self.last_status = "error"
            raise RuntimeError("No active autonomous brain is available.")

        try:
            result = await self._run_brain(brain, command)
        except Exception as exc:
            self.last_status = "error"
            self.last_result = {
                "status": "error",
                "agent": agent_name,
                "message": str(exc),
            }
            raise RuntimeError(
                f"{agent_name} failed to execute the objective: {exc}"
            ) from exc

        self.last_result = result
        result_status = self._result_status(result)

        # Do not report a successful execution when the brain explicitly
        # reports that it failed or could not run.
        if result_status in {
            "error",
            "failed",
            "brain_disabled",
            "brain_unavailable",
        }:
            self.last_status = "error"
        else:
            self.last_status = "success"

        return {
            "status": self.last_status,
            "router": "BrainRouter",
            "agent": agent_name,
            "objective": command,
            "result": self._serialise(result),
        }

    async def handle(self, command: str = "", **kwargs: Any) -> Any:
        return await self.process(command=command, **kwargs)

    async def dispatch(self, command: str = "", **kwargs: Any) -> Any:
        return await self.process(command=command, **kwargs)

    async def run(self, command: str = "", **kwargs: Any) -> Any:
        return await self.process(command=command, **kwargs)

    async def route_command(
        self, command: str = "", **kwargs: Any
    ) -> Any:
        return await self.process(command=command, **kwargs)

    async def _run_brain(self, brain: Any, command: str) -> Any:
        """
        Execute a brain exactly once using a compatible public method.

        Signature inspection selects a compatible argument form before
        execution. A TypeError raised inside the brain is not treated as
        evidence that the request should be executed again.
        """
        if brain is None:
            raise RuntimeError("Cannot execute a missing brain.")

        for method_name in ("run", "think", "reason"):
            method = getattr(brain, method_name, None)
            if not callable(method):
                continue

            called, result = await self._call_compatible(
                method, command
            )
            if called:
                return result

        raise RuntimeError(
            "The autonomous brain exposes no compatible run(), "
            "think(), or reason() method."
        )

    async def _call_compatible(self, method: Any, command: str):
        """Call a compatible method once; never retry an executed call."""
        candidates = (
            ((command,), {}),
            ((), {"request": command}),
            ((), {"command": command}),
            ((), {"objective": command}),
            ((), {"prompt": command}),
        )

        try:
            signature = inspect.signature(method)
        except (TypeError, ValueError):
            # If introspection is unavailable, make one conventional call.
            result = method(command)
            if inspect.isawaitable(result):
                result = await result
            return True, result

        for args, kwargs in candidates:
            try:
                signature.bind(*args, **kwargs)
            except TypeError:
                continue

            # Invoke only after binding succeeds. Exceptions raised here
            # belong to the brain and must propagate without another call.
            result = method(*args, **kwargs)
            if inspect.isawaitable(result):
                result = await result
            return True, result

        return False, None

    @staticmethod
    def _result_status(result: Any) -> Optional[str]:
        if isinstance(result, dict):
            status = result.get("status")
            if isinstance(status, str):
                return status.strip().lower()
        return None

    def _get_brain(self, agent_name: str) -> Any:
        manager = self.brain_manager

        if manager is not None:
            for getter_name in ("get_brain", "get"):
                getter = getattr(manager, getter_name, None)
                if callable(getter):
                    try:
                        brain = getter(agent_name)
                        if brain is not None:
                            return brain
                    except Exception:
                        pass

            brains = getattr(manager, "brains", {})
            if isinstance(brains, dict):
                brain = brains.get(agent_name)
                if brain is not None:
                    return brain

        agent = self.agents.get(agent_name)
        if agent is not None:
            return getattr(agent, "brain", None)

        return None

    def _select_specialist(self, command: str):
        """
        Select a specialist only if Boss has no brain.

        This is a fallback, not a restriction on the kinds of tasks
        agents can handle. Boss normally receives the full objective.
        """
        text = command.lower()
        candidates = []

        if any(word in text for word in (
            "research", "find out", "information", "source",
            "sources", "news", "investigate", "evidence",
        )):
            candidates.append("InfoFarmer")

        if any(word in text for word in (
            "money", "finance", "financial", "balance",
            "income", "expense", "transaction", "profit", "revenue",
        )):
            candidates.append("Banker")

        if any(word in text for word in (
            "opportunity", "opportunities", "business", "affiliate",
            "saas", "marketing", "social media",
        )):
            candidates.append("OpportunityAgent")

        # If the task doesn't match a specialist hint, use the first
        # available specialist rather than rejecting an arbitrary task.
        candidates.extend(
            name for name in (
                "InfoFarmer", "Banker", "OpportunityAgent"
            )
            if name not in candidates
        )

        for name in candidates:
            brain = self._get_brain(name)
            if brain is not None:
                return name, brain

        return None

    def status(self) -> Dict[str, Any]:
        active_brains = {}

        if self.brain_manager is not None:
            method = getattr(self.brain_manager, "status", None)
            if callable(method):
                try:
                    active_brains = method()
                except Exception as exc:
                    active_brains = {"error": str(exc)}

        return {
            "router": "BrainRouter",
            "enabled": self.enabled,
            "request_count": self.request_count,
            "last_request": self.last_request,
            "last_status": self.last_status,
            "active_brains": self._serialise(active_brains),
        }

    def reset(self) -> Dict[str, Any]:
        self.last_request = None
        self.last_result = None
        self.last_status = None
        self.request_count = 0

        return {
            "status": "reset",
            "router": "BrainRouter",
        }

    def _serialise(self, value: Any) -> Any:
        if value is None or isinstance(value, (str, int, float, bool)):
            return value

        if isinstance(value, dict):
            return {
                str(key): self._serialise(item)
                for key, item in value.items()
            }

        if isinstance(value, (list, tuple, set)):
            return [self._serialise(item) for item in value]

        for method_name in ("model_dump", "dict"):
            method = getattr(value, method_name, None)
            if callable(method):
                try:
                    return self._serialise(method())
                except Exception:
                    pass

        if hasattr(value, "__dict__"):
            try:
                return self._serialise(vars(value))
            except Exception:
                pass

        return str(value)
