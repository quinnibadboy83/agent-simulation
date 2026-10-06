"""
Agent Brain Manager
-------------------
Connects AutonomousBrain instances to the agent network.

This module is responsible for:
- Creating brains for agents
- Attaching brains to agents
- Tracking brain status
- Resetting brain state
- Providing a single management layer for the application's brains

The manager does not perform consequential external actions itself.
Those remain subject to the application's approval and safety layers.
"""

from __future__ import annotations

from typing import Any, Dict, Optional


class AgentBrainManager:
    """
    Creates and manages an AutonomousBrain for each agent.

    Expected dependencies are intentionally duck-typed so this layer
    remains compatible with the rest of the simulation as it evolves.
    """

    def __init__(
        self,
        memory: Any,
        world: Any = None,
        tools: Any = None,
        llm: Any = None,
        config: Any = None,
        brain_factory: Any = None,
    ):
        self.memory = memory
        self.world = world
        self.tools = tools
        self.llm = llm
        self.config = config
        self.brain_factory = brain_factory

        self.brains: Dict[str, Any] = {}

    # ------------------------------------------------------------------
    # Brain creation
    # ------------------------------------------------------------------

    def create_brain(
        self,
        agent: Any,
        objective: str = "",
    ) -> Any:
        """
        Create a brain for an agent.

        If a BrainFactory is available, use it. Otherwise construct
        AutonomousBrain directly.
        """

        agent_name = self._agent_name(agent)

        if not agent_name:
            raise ValueError("Cannot create brain for unnamed agent.")

        # Reuse an existing brain when possible.
        if agent_name in self.brains:
            brain = self.brains[agent_name]

            if objective and hasattr(brain, "objective"):
                try:
                    brain.objective = objective
                except Exception:
                    pass

            return brain

        brain = None

        # Preferred path: BrainFactory.
        if self.brain_factory is not None:
            brain = self._create_with_factory(
                agent=agent,
                agent_name=agent_name,
                objective=objective,
            )

        # Fallback: construct AutonomousBrain directly.
        if brain is None:
            brain = self._create_direct(
                agent=agent,
                agent_name=agent_name,
                objective=objective,
            )

        if brain is None:
            raise RuntimeError(
                f"Unable to create AutonomousBrain for agent '{agent_name}'."
            )

        self.brains[agent_name] = brain

        # Attach brain to agent.
        self._attach_to_agent(agent, brain)

        return brain

    def _create_with_factory(
        self,
        agent: Any,
        agent_name: str,
        objective: str,
    ) -> Optional[Any]:
        factory = self.brain_factory

        methods = (
            "create_for_agent",
            "create_brain",
            "build",
            "create",
        )

        for method_name in methods:
            method = getattr(factory, method_name, None)

            if not callable(method):
                continue

            attempts = [
                {
                    "agent": agent,
                    "objective": objective,
                },
                {
                    "agent_name": agent_name,
                    "objective": objective,
                },
                {
                    "agent": agent,
                },
                {
                    "agent_name": agent_name,
                },
            ]

            for kwargs in attempts:
                try:
                    brain = method(**kwargs)

                    if brain is not None:
                        return brain

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
        """
        Direct construction fallback.

        Imports are kept inside the method to avoid circular imports
        during application startup.
        """

        try:
            from .brain import AutonomousBrain
        except Exception:
            return None

        attempts = [
            {
                "agent_name": agent_name,
                "memory": self.memory,
                "room": getattr(agent, "room", None),
                "tools": self.tools,
                "llm": self.llm,
                "config": self.config,
                "objective": objective,
            },
            {
                "agent_name": agent_name,
                "memory": self.memory,
                "room": getattr(agent, "cognitive_room", None),
                "tools": self.tools,
                "llm": self.llm,
                "config": self.config,
                "objective": objective,
            },
        ]

        for kwargs in attempts:
            try:
                return AutonomousBrain(**kwargs)
            except TypeError:
                continue
            except Exception:
                continue

        return None

    # ------------------------------------------------------------------
    # Attach brains
    # ------------------------------------------------------------------

    def attach_brain(
        self,
        agent: Any,
        brain: Any,
    ) -> bool:
        """
        Attach an already-created brain to an agent.
        """

        agent_name = self._agent_name(agent)

        if not agent_name:
            return False

        self.brains[agent_name] = brain
        self._attach_to_agent(agent, brain)

        return True

    def _attach_to_agent(
        self,
        agent: Any,
        brain: Any,
    ) -> None:

        attach_method = getattr(agent, "attach_brain", None)

        if callable(attach_method):
            try:
                attach_method(brain)
                return
            except Exception:
                pass

        # Compatibility fallback.
        try:
            agent.brain = brain
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Attach to all agents
    # ------------------------------------------------------------------

    def attach_all(
        self,
        agents: Any,
        objectives: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """
        Create and attach brains to every supplied agent.

        Supports either:
            {"Boss": boss, "Banker": banker}

        or:
            [boss, banker]
        """

        objectives = objectives or {}

        normalised = self._normalise_agents(agents)

        results: Dict[str, Any] = {}

        for agent_name, agent in normalised.items():

            objective = objectives.get(
                agent_name,
                self._default_objective(agent_name),
            )

            try:
                brain = self.create_brain(
                    agent=agent,
                    objective=objective,
                )

                results[agent_name] = {
                    "attached": True,
                    "agent": agent_name,
                    "brain": self._brain_status(brain),
                }

            except Exception as exc:
                results[agent_name] = {
                    "attached": False,
                    "agent": agent_name,
                    "error": str(exc),
                }

        return results

    def attach_to_agents(
        self,
        agents: Any,
        objectives: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """
        Compatibility alias for attach_all().
        """

        return self.attach_all(
            agents=agents,
            objectives=objectives,
        )

    # ------------------------------------------------------------------
    # Brain lookup
    # ------------------------------------------------------------------

    def get_brain(
        self,
        agent_name: str,
    ) -> Optional[Any]:
        return self.brains.get(agent_name)

    def get(
        self,
        agent_name: str,
    ) -> Optional[Any]:
        return self.get_brain(agent_name)

    # ------------------------------------------------------------------
    # Thinking
    # ------------------------------------------------------------------

    async def think(
        self,
        agent_name: str,
        prompt: str,
        **kwargs: Any,
    ) -> Any:
        """
        Send a prompt to a specific agent's brain.
        """

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

        if hasattr(result, "__await__"):
            result = await result

        return result

    async def run(
        self,
        agent_name: str,
        objective: str,
        **kwargs: Any,
    ) -> Any:
        """
        Run the autonomous brain loop for one agent.
        """

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

        result = method(
            objective,
            **kwargs,
        )

        if hasattr(result, "__await__"):
            result = await result

        return result

    # ------------------------------------------------------------------
    # Status
    # ------------------------------------------------------------------

    def status(self) -> Dict[str, Any]:
        """
        Return status information for every managed brain.
        """

        output: Dict[str, Any] = {
            "brain_count": len(self.brains),
            "agents": {},
        }

        for agent_name, brain in self.brains.items():
            output["agents"][agent_name] = self._brain_status(brain)

        return output

    def get_status(self) -> Dict[str, Any]:
        return self.status()

    def _brain_status(
        self,
        brain: Any,
    ) -> Dict[str, Any]:

        status_method = getattr(brain, "status", None)

        if callable(status_method):
            try:
                result = status_method()

                if isinstance(result, dict):
                    return result

                return {
                    "status": result,
                }

            except Exception as exc:
                return {
                    "status": "error",
                    "error": str(exc),
                }

        return {
            "status": "attached",
            "brain_type": type(brain).__name__,
        }

    # ------------------------------------------------------------------
    # Reset
    # ------------------------------------------------------------------

    def reset_brain(
        self,
        agent_name: str,
    ) -> bool:

        brain = self.get_brain(agent_name)

        if brain is None:
            return False

        reset_method = getattr(brain, "reset", None)

        if callable(reset_method):
            try:
                result = reset_method()

                if hasattr(result, "__await__"):
                    # Reset is normally synchronous, but preserve
                    # compatibility with async implementations.
                    return True

                return True

            except Exception:
                return False

        return False

    def reset_all(self) -> Dict[str, bool]:
        results: Dict[str, bool] = {}

        for agent_name in self.brains:
            results[agent_name] = self.reset_brain(agent_name)

        return results

    # ------------------------------------------------------------------
    # Removal
    # ------------------------------------------------------------------

    def remove_brain(
        self,
        agent_name: str,
    ) -> bool:

        if agent_name not in self.brains:
            return False

        del self.brains[agent_name]
        return True

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _agent_name(
        self,
        agent: Any,
    ) -> str:

        if isinstance(agent, str):
            return agent

        name = getattr(agent, "name", None)

        if name:
            return str(name)

        agent_name = getattr(agent, "agent_name", None)

        if agent_name:
            return str(agent_name)

        return ""

    def _normalise_agents(
        self,
        agents: Any,
    ) -> Dict[str, Any]:

        if agents is None:
            return {}

        if isinstance(agents, dict):
            result: Dict[str, Any] = {}

            for key, agent in agents.items():
                name = self._agent_name(agent) or str(key)
                result[name] = agent

            return result

        if isinstance(agents, (list, tuple, set)):
            result = {}

            for agent in agents:
                name = self._agent_name(agent)

                if name:
                    result[name] = agent

            return result

        name = self._agent_name(agents)

        if name:
            return {
                name: agents,
            }

        return {}

    def _default_objective(
        self,
        agent_name: str,
    ) -> str:

        name = agent_name.lower()

        if name == "boss":
            return (
                "Coordinate the agent system, understand Creator objectives, "
                "reason about the best next actions, delegate work to "
                "specialist agents when useful, inspect results, and maintain "
                "a coherent plan."
            )

        if name == "banker":
            return (
                "Monitor the simulated economy, analyse financial information, "
                "track balances and transactions, and provide financial "
                "reasoning to the agent system."
            )

        if name in {"infofarmer", "info_farmer", "research"}:
            return (
                "Research information from permitted sources, evaluate "
                "evidence, remember useful findings, and provide concise "
                "research results to the agent system."
            )

        if name in {
            "opportunityagent",
            "opportunity_agent",
            "opportunity",
        }:
            return (
                "Discover, analyse, rank, and test potential opportunities "
                "within the permitted simulation and approval framework."
            )

        return (
            "Understand objectives, reason about available information, "
            "select appropriate tools, complete useful work, remember "
            "important results, and report outcomes."
        )
