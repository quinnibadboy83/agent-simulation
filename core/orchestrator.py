"""
Autonomous Agent Orchestrator
-----------------------------
Coordinates the agent team through a controlled perception/reasoning/
planning/execution loop.

The orchestrator may autonomously perform safe research, analysis,
memory operations, simulation work, and planning.

Consequential external actions remain behind the ToolRegistry approval
gate and cannot be executed without an exact Creator approval.
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
        self.agents = agents or {}
        self.world = world
        self.economy = economy

        self.running = False
        self.cycle_count = 0
        self.last_cycle_at = None

    def register_agent(self, agent) -> Dict[str, Any]:
        if agent is None:
            return {
                "status": "error",
                "message": "Agent is required.",
            }

        name = getattr(agent, "name", None)

        if not name:
            return {
                "status": "error",
                "message": "Agent must have a name.",
            }

        self.agents[name] = agent

        return {
            "status": "success",
            "agent": name,
            "message": f"Registered agent: {name}",
        }

    def unregister_agent(self, agent_name: str) -> Dict[str, Any]:
        agent_name = (agent_name or "").strip()

        if agent_name not in self.agents:
            return {
                "status": "error",
                "message": f"Unknown agent: {agent_name}",
            }

        del self.agents[agent_name]

        return {
            "status": "success",
            "agent": agent_name,
        }

    def get_agents(self) -> List[str]:
        return sorted(self.agents.keys())

    def start(self) -> Dict[str, Any]:
        self.running = True

        self.memory.log(
            "Orchestrator",
            "Autonomous orchestration started.",
        )

        return self.status()

    def stop(self) -> Dict[str, Any]:
        self.running = False

        self.memory.log(
            "Orchestrator",
            "Autonomous orchestration stopped.",
        )

        return self.status()

    def status(self) -> Dict[str, Any]:
        return {
            "status": "success",
            "running": self.running,
            "cycle_count": self.cycle_count,
            "last_cycle_at": self.last_cycle_at,
            "agents": self.get_agents(),
            "agent_count": len(self.agents),
            "mode": self._get_mode(),
            "safety": {
                "consequential_actions_require_creator_approval": True,
                "exact_approval_required": True,
                "approval_is_single_use": True,
            },
        }

    def run_cycle(
        self,
        command: str = "",
        agent_name: str = "",
    ) -> Dict[str, Any]:
        self.cycle_count += 1
        self.last_cycle_at = datetime.utcnow().isoformat()

        command = (command or "").strip()
        agent_name = (agent_name or "").strip()

        results = []

        selected_agents = self._select_agents(
            agent_name=agent_name,
            command=command,
        )

        if not selected_agents:
            return {
                "status": "error",
                "cycle": self.cycle_count,
                "message": "No suitable agents available.",
                "available_agents": self.get_agents(),
            }

        for agent in selected_agents:
            result = self._run_agent_cycle(
                agent,
                command,
            )

            results.append(result)

        self.memory.log(
            "Orchestrator",
            (
                f"Completed autonomous cycle "
                f"{self.cycle_count} with "
                f"{len(results)} agent(s)."
            ),
        )

        return {
            "status": "success",
            "cycle": self.cycle_count,
            "timestamp": self.last_cycle_at,
            "running": self.running,
            "results": results,
        }

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
        """
        Run a safe autonomous cycle without requiring a user command.

        The cycle lets agents inspect their pending work and execute
        only the capabilities already exposed through their normal
        agent/tool interfaces.
        """
        return self.run_cycle()

    def assign_task(
        self,
        agent_name: str,
        task: str,
        priority: str = "normal",
    ) -> Dict[str, Any]:
        agent_name = (agent_name or "").strip()
        task = (task or "").strip()
        priority = (priority or "normal").strip().lower()

        if not agent_name:
            return {
                "status": "error",
                "message": "Agent name is required.",
            }

        if not task:
            return {
                "status": "error",
                "message": "Task is required.",
            }

        agent = self.agents.get(agent_name)

        if agent is None:
            return {
                "status": "error",
                "message": f"Unknown agent: {agent_name}",
                "available_agents": self.get_agents(),
            }

        if hasattr(agent, "create_task"):
            try:
                result = agent.create_task(
                    task,
                    priority=priority,
                )

                return {
                    "status": "success",
                    "agent": agent_name,
                    "task": task,
                    "result": result,
                }
            except TypeError:
                try:
                    result = agent.create_task(task)

                    return {
                        "status": "success",
                        "agent": agent_name,
                        "task": task,
                        "result": result,
                    }
                except Exception as exc:
                    return {
                        "status": "error",
                        "agent": agent_name,
                        "message": str(exc),
                    }

        try:
            task_id = self.memory.add_task(
                agent_name,
                task,
                priority=priority,
            )

            return {
                "status": "success",
                "agent": agent_name,
                "task": task,
                "task_id": task_id,
            }

        except TypeError:
            try:
                task_id = self.memory.add_task(
                    {
                        "agent": agent_name,
                        "description": task,
                        "priority": priority,
                    }
                )

                return {
                    "status": "success",
                    "agent": agent_name,
                    "task": task,
                    "task_id": task_id,
                }

            except Exception as exc:
                return {
                    "status": "error",
                    "agent": agent_name,
                    "message": str(exc),
                }

        except Exception as exc:
            return {
                "status": "error",
                "agent": agent_name,
                "message": str(exc),
            }

    def broadcast(
        self,
        message: str,
        sender: str = "Orchestrator",
    ) -> Dict[str, Any]:
        message = (message or "").strip()

        if not message:
            return {
                "status": "error",
                "message": "Broadcast message is required.",
            }

        delivered = []

        for agent_name, agent in self.agents.items():
            try:
                if hasattr(agent, "receive_message"):
                    agent.receive_message(
                        message,
                        sender=sender,
                    )
                    delivered.append(agent_name)
                    continue

                if hasattr(agent, "room") and hasattr(
                    agent.room,
                    "receive_message",
                ):
                    agent.room.receive_message(
                        message,
                        sender=sender,
                    )
                    delivered.append(agent_name)

            except Exception:
                continue

        self.memory.log(
            "Orchestrator",
            (
                f"Broadcast from {sender}: "
                f"{message}"
            ),
        )

        return {
            "status": "success",
            "sender": sender,
            "message": message,
            "delivered_to": delivered,
        }

    def route_command(
        self,
        command: str,
    ) -> Dict[str, Any]:
        command = (command or "").strip()

        if not command:
            return {
                "status": "error",
                "message": "Command is required.",
            }

        target = self._detect_agent(command)

        if target:
            agent = self.agents.get(target)

            if agent is not None:
                return self._run_agent_command(
                    agent,
                    command,
                )

        boss = self.agents.get("Boss")

        if boss is not None:
            return self._run_agent_command(
                boss,
                command,
            )

        return self.run_cycle(
            command=command,
        )

    def _run_agent_cycle(
        self,
        agent,
        command: str,
    ) -> Dict[str, Any]:
        name = getattr(agent, "name", "Unknown")

        try:
            if command and hasattr(
                agent,
                "process_command",
            ):
                result = agent.process_command(command)

                return {
                    "status": "success",
                    "agent": name,
                    "operation": "command",
                    "result": result,
                }

            if hasattr(agent, "run_cycle"):
                result = agent.run_cycle()

                return {
                    "status": "success",
                    "agent": name,
                    "operation": "cycle",
                    "result": result,
                }

            return {
                "status": "error",
                "agent": name,
                "message": (
                    "Agent has no process_command or "
                    "run_cycle method."
                ),
            }

        except Exception as exc:
            self.memory.log(
                "Orchestrator",
                (
                    f"Agent cycle failed for "
                    f"{name}: {exc}"
                ),
            )

            return {
                "status": "error",
                "agent": name,
                "message": str(exc),
            }

    def _run_agent_command(
        self,
        agent,
        command: str,
    ) -> Dict[str, Any]:
        name = getattr(agent, "name", "Unknown")

        try:
            if hasattr(agent, "process_command"):
                return agent.process_command(command)

            if hasattr(agent, "run_cycle"):
                return agent.run_cycle()

            return {
                "status": "error",
                "agent": name,
                "message": (
                    "Agent cannot process commands."
                ),
            }

        except Exception as exc:
            self.memory.log(
                "Orchestrator",
                (
                    f"Command failed for {name}: "
                    f"{exc}"
                ),
            )

            return {
                "status": "error",
                "agent": name,
                "message": str(exc),
            }

    def _select_agents(
        self,
        agent_name: str = "",
        command: str = "",
    ) -> List[Any]:
        if agent_name:
            agent = self.agents.get(agent_name)

            if agent is not None:
                return [agent]

            return []

        target = self._detect_agent(command)

        if target:
            agent = self.agents.get(target)

            if agent is not None:
                return [agent]

        if command:
            boss = self.agents.get("Boss")

            if boss is not None:
                return [boss]

        return list(self.agents.values())

    def _detect_agent(
        self,
        command: str,
    ) -> str:
        lowered = (command or "").lower()

        names = sorted(
            self.agents.keys(),
            key=len,
            reverse=True,
        )

        for name in names:
            if name.lower() in lowered:
                return name

        aliases = {
            "research": "InfoFarmer",
            "researcher": "InfoFarmer",
            "info": "InfoFarmer",
            "information": "InfoFarmer",
            "finance": "Banker",
            "financial": "Banker",
            "money": "Banker",
            "bank": "Banker",
            "opportunity": "OpportunityAgent",
            "opportunities": "OpportunityAgent",
            "revenue": "OpportunityAgent",
        }

        for keyword, agent_name in aliases.items():
            if keyword in lowered:
                if agent_name in self.agents:
                    return agent_name

        return ""

    def _get_mode(self) -> str:
        if self.economy is not None:
            try:
                return self.economy.get_mode()
            except Exception:
                pass

        try:
            world_state = self.memory.get_world_state()
            return world_state.get(
                "economy_mode",
                "simulation",
            )
        except Exception:
            return "simulation"
