"""Create and manage agent brains using one shared model runtime."""
from __future__ import annotations

from typing import Any, Dict, Optional

from .runtime_config import RuntimeConfig
from .runtime_manager import RuntimeManager


class AgentBrainManager:
    """Attach one AutonomousBrain per agent while sharing one runtime instance."""

    def __init__(
        self,
        memory: Any,
        world: Any = None,
        tools: Any = None,
        llm: Any = None,
        config: Any = None,
        brain_factory: Any = None,
        runtime_manager: Optional[RuntimeManager] = None,
        runtime: Any = None,
    ) -> None:
        self.memory = memory
        self.world = world
        self.tools = tools
        self.llm = llm
        self.config = config
        self.brain_factory = brain_factory

        if runtime_manager is not None:
            self.runtime_manager = runtime_manager
        elif runtime is not None:
            self.runtime_manager = RuntimeManager(
                config=RuntimeConfig.from_environment(),
                runtime=runtime,
            )
        else:
            self.runtime_manager = RuntimeManager(
                config=RuntimeConfig.from_environment()
            )

        self._runtime_error: Optional[str] = None
        self.brains: Dict[str, Any] = {}

    def _shared_runtime(self) -> Any:
        """Lazily create one runtime and reuse it for every brain."""
        if self.runtime_manager.runtime is not None:
            return self.runtime_manager.runtime

        try:
            return self.runtime_manager.start()
        except Exception as exc:
            self._runtime_error = str(exc)
            return None

    def create_brain(self, agent: Any, objective: str = "") -> Any:
        name = self._agent_name(agent)

        if not name:
            raise ValueError("Cannot create brain for unnamed agent.")

        if name in self.brains:
            brain = self.brains[name]
            if objective and hasattr(brain, "objective"):
                brain.objective = objective
            return brain

        brain = None

        if self.brain_factory is not None:
            brain = self._create_with_factory(agent, name, objective)

        if brain is None:
            brain = self._create_direct(agent, name, objective)

        if brain is None:
            raise RuntimeError(
                f"Unable to create AutonomousBrain for agent '{name}'."
            )

        self.brains[name] = brain
        self._attach_to_agent(agent, brain)
        return brain

    def _create_with_factory(
        self,
        agent: Any,
        agent_name: str,
        objective: str,
    ) -> Optional[Any]:
        for method_name in (
            "create_for_agent",
            "create_brain",
            "build",
            "create",
        ):
            method = getattr(self.brain_factory, method_name, None)

            if not callable(method):
                continue

            for kwargs in (
                {"agent": agent, "objective": objective},
                {"agent_name": agent_name, "objective": objective},
                {"agent": agent},
                {"agent_name": agent_name},
            ):
                try:
                    result = method(**kwargs)
                    if result is not None:
                        return result
                except TypeError:
                    continue
                except Exception:
                    continue

        return None

    def _create_direct(
        self,
        agent: Any,
        agent_name: str,
        objective: str,
    ) -> Optional[Any]:
        try:
            from .brain import AutonomousBrain
        except Exception:
            return None

        shared_runtime = self._shared_runtime()

        base = {
            "agent_name": agent_name,
            "memory": self.memory,
            "tools": self.tools,
            "llm": self.llm,
            "config": self.config,
            "objective": objective,
        }

        attempts = []

        if shared_runtime is not None:
            attempts.extend(
                [
                    {
                        **base,
                        "room": getattr(agent, "room", None),
                        "runtime": shared_runtime,
                    },
                    {
                        **base,
                        "room": getattr(agent, "cognitive_room", None),
                        "runtime": shared_runtime,
                    },
                ]
            )

        attempts.extend(
            [
                {**base, "room": getattr(agent, "room", None)},
                {**base, "room": getattr(agent, "cognitive_room", None)},
            ]
        )

        for kwargs in attempts:
            try:
                return AutonomousBrain(**kwargs)
            except TypeError:
                continue
            except Exception as exc:
                if self._runtime_error is None:
                    self._runtime_error = str(exc)

        return None

    def attach_brain(self, agent: Any, brain: Any) -> bool:
        name = self._agent_name(agent)

        if not name:
            return False

        self.brains[name] = brain
        self._attach_to_agent(agent, brain)
        return True

    @staticmethod
    def _attach_to_agent(agent: Any, brain: Any) -> None:
        method = getattr(agent, "attach_brain", None)

        if callable(method):
            try:
                method(brain)
                return
            except Exception:
                pass

        try:
            agent.brain = brain
        except Exception:
            pass

    def attach_all(
        self,
        agents: Any,
        objectives: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        results: Dict[str, Any] = {}

        for name, agent in self._normalise_agents(agents).items():
            try:
                brain = self.create_brain(
                    agent,
                    (objectives or {}).get(
                        name,
                        self._default_objective(name),
                    ),
                )
                results[name] = {
                    "attached": True,
                    "agent": name,
                    "brain": self._brain_status(brain),
                }
            except Exception as exc:
                results[name] = {
                    "attached": False,
                    "agent": name,
                    "error": str(exc),
                }

        return results

    def attach_to_agents(
        self,
        agents: Any,
        objectives: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        return self.attach_all(agents, objectives)

    def get_brain(self, agent_name: str) -> Optional[Any]:
        return self.brains.get(agent_name)

    def get(self, agent_name: str) -> Optional[Any]:
        return self.get_brain(agent_name)

    async def think(
        self,
        agent_name: str,
        prompt: str,
        **kwargs: Any,
    ) -> Any:
        brain = self.get_brain(agent_name)

        if brain is None:
            raise ValueError(
                f"No brain is attached to agent '{agent_name}'."
            )

        method = getattr(brain, "think", None)

        if not callable(method):
            raise RuntimeError(
                f"Brain for '{agent_name}' does not support think()."
            )

        result = method(prompt, **kwargs)
        return await result if hasattr(result, "__await__") else result

    async def run(
        self,
        agent_name: str,
        objective: str,
        **kwargs: Any,
    ) -> Any:
        brain = self.get_brain(agent_name)

        if brain is None:
            raise ValueError(
                f"No brain is attached to agent '{agent_name}'."
            )

        method = getattr(brain, "run", None)

        if not callable(method):
            raise RuntimeError(
                f"Brain for '{agent_name}' does not support run()."
            )

        result = method(objective, **kwargs)
        return await result if hasattr(result, "__await__") else result

    def status(self) -> Dict[str, Any]:
        return {
            "brain_count": len(self.brains),
            "shared_runtime": self.runtime_manager.status(),
            "runtime_error": self._runtime_error,
            "agents": {
                name: self._brain_status(brain)
                for name, brain in self.brains.items()
            },
        }

    def get_status(self) -> Dict[str, Any]:
        return self.status()

    @staticmethod
    def _brain_status(brain: Any) -> Dict[str, Any]:
        method = getattr(brain, "status", None)

        if callable(method):
            try:
                value = method()
                return (
                    value
                    if isinstance(value, dict)
                    else {"status": value}
                )
            except Exception as exc:
                return {"status": "error", "error": str(exc)}

        return {
            "status": "attached",
            "brain_type": type(brain).__name__,
        }

    def reset_brain(self, agent_name: str) -> bool:
        brain = self.get_brain(agent_name)
        method = getattr(brain, "reset", None) if brain else None

        if not callable(method):
            return False

        try:
            method()
            return True
        except Exception:
            return False

    def reset_all(self) -> Dict[str, bool]:
        return {
            name: self.reset_brain(name)
            for name in self.brains
        }

    def remove_brain(self, agent_name: str) -> bool:
        return self.brains.pop(agent_name, None) is not None

    @staticmethod
    def _agent_name(agent: Any) -> str:
        if isinstance(agent, str):
            return agent

        return str(
            getattr(agent, "name", None)
            or getattr(agent, "agent_name", None)
            or ""
        )

    def _normalise_agents(self, agents: Any) -> Dict[str, Any]:
        if agents is None:
            return {}

        if isinstance(agents, dict):
            return {
                self._agent_name(value) or str(key): value
                for key, value in agents.items()
            }

        if isinstance(agents, (list, tuple, set)):
            return {
                self._agent_name(value): value
                for value in agents
                if self._agent_name(value)
            }

        name = self._agent_name(agents)
        return {name: agents} if name else {}

    @staticmethod
    def _default_objective(agent_name: str) -> str:
        name = agent_name.lower().replace("_", "")

        objectives = {
            "boss": (
                "Coordinate the agent system, plan Creator objectives, "
                "delegate when useful, inspect results, and protect "
                "approval requirements."
            ),
            "banker": (
                "Analyse the simulated economy, balances, transactions, "
                "costs and financial risks."
            ),
            "infofarmer": (
                "Research permitted sources, evaluate evidence, retain "
                "useful findings and report concise results."
            ),
            "opportunityagent": (
                "Discover, analyse, rank and test realistic opportunities "
                "within the approval framework."
            ),
        }

        return objectives.get(
            name,
            "Understand objectives, reason from available evidence, use "
            "permitted tools, remember results, and report outcomes.",
        )