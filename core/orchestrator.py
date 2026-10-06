"""
Orchestrator
------------
Coordinates the autonomous multi-agent system.

Responsibilities:
- Register and manage agents.
- Route commands to the correct agent.
- Run autonomous cognitive cycles.
- Assign and broadcast tasks.
- Respect simulation/live mode boundaries.
- Never bypass Creator approval.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional


class Orchestrator:
    def __init__(
        self,
        memory,
        tools,
        agents: Optional[Dict[str, Any]] = None,
        world=None,
        economy=None,
    ):
        self.memory = memory
        self.tools = tools
        self.world = world
        self.economy = economy

        self.agents: Dict[str, Any] = {}
        self.running = False
        self.cycle_count = 0
        self.last_cycle: Optional[Dict[str, Any]] = None

        for agent in (agents or {}).values():
            self.register_agent(agent)

    # ------------------------------------------------------------------
    # Agent management
    # ------------------------------------------------------------------

    def register_agent(self, agent) -> Dict[str, Any]:
        if agent is None or not getattr(agent, "name", None):
            return {
                "status": "error",
                "message": "Invalid agent.",
            }

        self.agents[agent.name] = agent

        return {
            "status": "success",
            "agent": agent.name,
            "message": f"Agent {agent.name} registered.",
        }

    def unregister_agent(self, name: str) -> Dict[str, Any]:
        if name not in self.agents:
            return {
                "status": "error",
                "message": f"Agent {name} is not registered.",
            }

        del self.agents[name]

        return {
            "status": "success",
            "agent": name,
            "message": f"Agent {name} unregistered.",
        }

    def get_agents(self) -> Dict[str, Any]:
        return self.agents

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self) -> Dict[str, Any]:
        self.running = True

        return {
            "status": "success",
            "running": True,
            "message": "Autonomous orchestration enabled.",
        }

    def stop(self) -> Dict[str, Any]:
        self.running = False

        return {
            "status": "success",
            "running": False,
            "message": "Autonomous orchestration stopped.",
        }

    def status(self) -> Dict[str, Any]:
        return {
            "status": "success",
            "running": self.running,
            "cycle_count": self.cycle_count,
            "agent_count": len(self.agents),
            "agents": list(self.agents.keys()),
            "mode": self._get_mode(),
            "last_cycle": self.last_cycle,
        }

    # ------------------------------------------------------------------
    # Main orchestration
    # ------------------------------------------------------------------

    def run_cycle(
        self,
        command: str = "",
        agent_name: str = "",
    ) -> Dict[str, Any]:
        self.cycle_count += 1

        started_at = self._timestamp()

        if command:
            results = self.route_command(
                command=command,
                agent_name=agent_name,
            )
        else:
            results = {}

            selected_agents = self._select_agents(agent_name)

            for name, agent in selected_agents.items():
                results[name] = self._run_agent_cycle(agent)

        cycle_result = {
            "status": "success",
            "cycle": self.cycle_count,
            "started_at": started_at,
            "completed_at": self._timestamp(),
            "running": self.running,
            "mode": self._get_mode(),
            "results": results,
        }

        self.last_cycle = cycle_result

        return cycle_result

    def run_once(
        self,
        command: str = "",
        agent_name: str = "",
    ) -> Dict[str, Any]:
        return self.run_cycle(
            command=command,
            agent_name=agent_name,
        )

    def run_autonomous_cycle(self) -> Dict[str, Any]:
        if not self.running:
            return {
                "status": "blocked",
                "message": "Orchestrator is stopped.",
                "hint": "Start the orchestrator before autonomous cycles.",
            }

        return self.run_cycle()

    # ------------------------------------------------------------------
    # Task delegation
    # ------------------------------------------------------------------

    def assign_task(
        self,
        agent_name: str,
        task: str,
        priority: str = "normal",
    ) -> Dict[str, Any]:
        if agent_name not in self.agents:
            return {
                "status": "error",
                "message": f"Unknown agent: {agent_name}",
            }

        if not task or not task.strip():
            return {
                "status": "error",
                "message": "Task cannot be empty.",
            }

        agent = self.agents[agent_name]

        if hasattr(agent, "create_task"):
            result = agent.create_task(
                title=task.strip(),
                description=task.strip(),
                priority=priority,
            )

            return {
                "status": "success",
                "agent": agent_name,
                "task": task.strip(),
                "priority": priority,
                "result": result,
            }

        task_record = self.memory.add_task(
            agent=agent_name,
            title=task.strip(),
            description=task.strip(),
            priority=priority,
        )

        return {
            "status": "success",
            "agent": agent_name,
            "task": task.strip(),
            "priority": priority,
            "task_record": task_record,
        }

    def broadcast(self, message: str) -> Dict[str, Any]:
        if not message or not message.strip():
            return {
                "status": "error",
                "message": "Broadcast message cannot be empty.",
            }

        results = {}

        for name, agent in self.agents.items():
            if hasattr(agent, "receive_message"):
                results[name] = agent.receive_message(
                    sender="Orchestrator",
                    message=message.strip(),
                )
            else:
                results[name] = {
                    "status": "skipped",
                    "message": "Agent does not support messages.",
                }

        return {
            "status": "success",
            "message": message.strip(),
            "recipients": list(self.agents.keys()),
            "results": results,
        }

    # ------------------------------------------------------------------
    # Command routing
    # ------------------------------------------------------------------

    def route_command(
        self,
        command: str,
        agent_name: str = "",
    ) -> Dict[str, Any]:
        command = (command or "").strip()

        if not command:
            return {
                "status": "error",
                "message": "No command supplied.",
            }

        if agent_name:
            if agent_name not in self.agents:
                return {
                    "status": "error",
                    "message": f"Unknown agent: {agent_name}",
                    "available_agents": list(self.agents.keys()),
                }

            return self._run_agent_command(
                self.agents[agent_name],
                command,
            )

        detected = self._detect_agent(command)

        if detected:
            return self._run_agent_command(
                self.agents[detected],
                command,
            )

        # Default command owner is Boss.
        if "Boss" in self.agents:
            return self._run_agent_command(
                self.agents["Boss"],
                command,
            )

        # If Boss is unavailable, run against the first registered agent.
        if self.agents:
            first_agent = next(iter(self.agents.values()))

            return self._run_agent_command(
                first_agent,
                command,
            )

        return {
            "status": "error",
            "message": "No agents are registered.",
        }

    # ------------------------------------------------------------------
    # Agent execution
    # ------------------------------------------------------------------

    def _run_agent_cycle(self, agent) -> Dict[str, Any]:
        try:
            if hasattr(agent, "run_cycle"):
                return agent.run_cycle()

            if hasattr(agent, "process_command"):
                return agent.process_command("run")

            if hasattr(agent, "process_order"):
                return agent.process_order("run")

            return {
                "status": "error",
                "agent": getattr(agent, "name", "Unknown"),
                "message": "Agent has no runnable cycle method.",
            }

        except Exception as exc:
            return {
                "status": "error",
                "agent": getattr(agent, "name", "Unknown"),
                "message": str(exc),
            }

    def _run_agent_command(
        self,
        agent,
        command: str,
    ) -> Dict[str, Any]:
        try:
            if hasattr(agent, "process_command"):
                return agent.process_command(command)

            if hasattr(agent, "process_order"):
                return agent.process_order(command)

            return {
                "status": "error",
                "agent": getattr(agent, "name", "Unknown"),
                "message": "Agent cannot process commands.",
            }

        except Exception as exc:
            return {
                "status": "error",
                "agent": getattr(agent, "name", "Unknown"),
                "message": str(exc),
            }

    # ------------------------------------------------------------------
    # Agent selection
    # ------------------------------------------------------------------

    def _select_agents(
        self,
        agent_name: str = "",
    ) -> Dict[str, Any]:
        if agent_name:
            if agent_name in self.agents:
                return {
                    agent_name: self.agents[agent_name],
                }

            return {}

        return dict(self.agents)

    def _detect_agent(self, command: str) -> Optional[str]:
        lowered = command.lower()

        aliases = {
            "boss": "Boss",
            "banker": "Banker",
            "infofarmer": "InfoFarmer",
            "info farmer": "InfoFarmer",
            "researcher": "InfoFarmer",
            "research": "InfoFarmer",
            "opportunity": "OpportunityAgent",
            "opportunities": "OpportunityAgent",
            "opportunityagent": "OpportunityAgent",
            "revenue": "OpportunityAgent",
        }

        for alias, agent_name in aliases.items():
            if alias in lowered and agent_name in self.agents:
                return agent_name

        return None

    # ------------------------------------------------------------------
    # Mode
    # ------------------------------------------------------------------

    def _get_mode(self) -> str:
        try:
            if self.economy is not None and hasattr(
                self.economy,
                "get_mode",
            ):
                return self.economy.get_mode()

            if hasattr(self.memory, "get_world_state"):
                state = self.memory.get_world_state()
                return state.get(
                    "economy_mode",
                    "simulation",
                )

            if hasattr(self.memory, "get_world"):
                state = self.memory.get_world()
                return state.get(
                    "economy_mode",
                    "simulation",
                )

        except Exception:
            pass

        return "simulation"

    # ------------------------------------------------------------------
    # Utility
    # ------------------------------------------------------------------

    @staticmethod
    def _timestamp() -> str:
        return datetime.utcnow().isoformat() + "Z"
