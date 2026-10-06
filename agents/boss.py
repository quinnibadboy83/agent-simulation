"""
Boss Agent
----------
Primary coordinator and command-routing agent.

Boss can:
- Inspect system status.
- Inspect other agents.
- Request research.
- Scan opportunities.
- Analyse opportunities.
- Delegate tasks.
- Run cognitive cycles.

Boss cannot:
- Change simulation/live mode.
- Bypass Creator approval.
- Perform protected consequential actions directly.
"""

from typing import Any, Dict

from .base_agent import BaseAgent


class Boss(BaseAgent):
    def __init__(self, memory, tools):
        super().__init__(
            name="Boss",
            role="Coordinator",
            memory=memory,
            tools=tools,
            description=(
                "Coordinates the agent system, interprets Creator "
                "commands, delegates work, monitors progress, and "
                "coordinates research and opportunity discovery."
            ),
        )

    # ------------------------------------------------------------------
    # Command processing
    # ------------------------------------------------------------------

    def process_command(self, command: str) -> Dict[str, Any]:
        command = (command or "").strip()

        if not command:
            return {
                "status": "error",
                "agent": self.name,
                "message": "No command supplied.",
            }

        lowered = command.lower()

        if lowered in {"help", "?", "commands"}:
            return self.get_help()

        if lowered in {
            "status",
            "system status",
            "system",
        }:
            return self._system_status()

        if lowered in {
            "agent status",
            "agents",
            "agent list",
        }:
            return self._agent_status()

        if lowered in {
            "balance",
            "money",
            "funds",
        }:
            return self.execute_tool(
                "check_balance",
            )

        if lowered.startswith("research "):
            query = command[9:].strip()

            if not query:
                return {
                    "status": "error",
                    "agent": self.name,
                    "message": "Research query is required.",
                }

            return self.execute_tool(
                "web_search",
                query=query,
            )

        if lowered.startswith("search "):
            query = command[7:].strip()

            if not query:
                return {
                    "status": "error",
                    "agent": self.name,
                    "message": "Search query is required.",
                }

            return self.execute_tool(
                "web_search",
                query=query,
            )

        if lowered.startswith("farm "):
            topic = command[5:].strip()

            if not topic:
                return {
                    "status": "error",
                    "agent": self.name,
                    "message": "Information topic is required.",
                }

            return self.execute_tool(
                "farm_info",
                topic=topic,
            )

        if lowered in {
            "scan",
            "opportunities",
            "find opportunities",
            "scan opportunities",
        }:
            return self._delegate_to_agent(
                "OpportunityAgent",
                "scan",
            )

        if lowered.startswith("scan "):
            category = command[5:].strip()

            return self._delegate_to_agent(
                "OpportunityAgent",
                f"scan {category}",
            )

        if lowered.startswith("analyse "):
            opportunity_id = command[8:].strip()

            if not opportunity_id:
                return {
                    "status": "error",
                    "agent": self.name,
                    "message": "Opportunity ID is required.",
                }

            return self._delegate_to_agent(
                "OpportunityAgent",
                f"analyse {opportunity_id}",
            )

        if lowered.startswith("analyze "):
            opportunity_id = command[8:].strip()

            if not opportunity_id:
                return {
                    "status": "error",
                    "agent": self.name,
                    "message": "Opportunity ID is required.",
                }

            return self._delegate_to_agent(
                "OpportunityAgent",
                f"analyse {opportunity_id}",
            )

        if lowered in {
            "economy",
            "economy report",
            "financial report",
        }:
            return self.execute_tool(
                "economy_report",
            )

        if lowered in {
            "mode",
            "money mode",
            "operating mode",
        }:
            return self.execute_tool(
                "money_mode",
            )

        if lowered.startswith("mode "):
            return {
                "status": "blocked",
                "agent": self.name,
                "message": (
                    "Boss cannot change operating mode. "
                    "Simulation/live mode is controlled by the "
                    "Creator."
                ),
            }

        if lowered.startswith("assign "):
            return self._create_task_from_command(
                command[7:].strip()
            )

        if lowered.startswith("task "):
            return self._create_task_from_command(
                command[5:].strip()
            )

        if lowered.startswith("delegate "):
            return self._delegate_command(
                command[9:].strip()
            )

        detected_agent = self._detect_agent(command)

        if detected_agent:
            return self._delegate_to_agent(
                detected_agent,
                command,
            )

        if lowered in {
            "run",
            "cycle",
            "run cycle",
        }:
            return self.run_cycle()

        return {
            "status": "error",
            "agent": self.name,
            "message": f"Unknown Boss command: {command}",
            "help": self.get_help(),
        }

    # ------------------------------------------------------------------
    # Task creation
    # ------------------------------------------------------------------

    def _create_task_from_command(
        self,
        command: str,
    ) -> Dict[str, Any]:
        if not command:
            return {
                "status": "error",
                "agent": self.name,
                "message": "Task description is required.",
            }

        target = self._detect_agent(command)

        if target:
            return self._delegate_to_agent(
                target,
                command,
            )

        return self.create_task(
            title=command,
            description=command,
        )

    # ------------------------------------------------------------------
    # Delegation
    # ------------------------------------------------------------------

    def _delegate_command(
        self,
        command: str,
    ) -> Dict[str, Any]:
        if not command:
            return {
                "status": "error",
                "agent": self.name,
                "message": "Delegation command is required.",
            }

        target = self._detect_agent(command)

        if not target:
            return {
                "status": "error",
                "agent": self.name,
                "message": (
                    "Could not determine which agent should "
                    "receive the task."
                ),
                "available_agents": [
                    "Banker",
                    "InfoFarmer",
                    "OpportunityAgent",
                ],
            }

        return self._delegate_to_agent(
            target,
            command,
        )

    def _delegate_to_agent(
        self,
        agent_name: str,
        command: str,
    ) -> Dict[str, Any]:
        agent = self._find_agent(agent_name)

        if agent is None:
            return {
                "status": "error",
                "agent": self.name,
                "message": f"Agent {agent_name} is not available.",
            }

        try:
            if hasattr(agent, "process_command"):
                result = agent.process_command(command)

            elif hasattr(agent, "process_order"):
                result = agent.process_order(command)

            else:
                result = {
                    "status": "error",
                    "message": (
                        f"{agent_name} cannot process commands."
                    ),
                }

            return {
                "status": "success",
                "agent": self.name,
                "delegated_to": agent_name,
                "command": command,
                "result": result,
            }

        except Exception as exc:
            return {
                "status": "error",
                "agent": self.name,
                "delegated_to": agent_name,
                "message": str(exc),
            }

    # ------------------------------------------------------------------
    # Status
    # ------------------------------------------------------------------

    def _system_status(self) -> Dict[str, Any]:
        return {
            "status": "success",
            "agent": self.name,
            "system": {
                "agent": self.name,
                "role": self.role,
                "objective": self.get_objective(),
                "status": self.status,
                "mode": self._get_mode(),
            },
        }

    def _agent_status(self) -> Dict[str, Any]:
        reports = {}

        for agent_name in [
            "Boss",
            "Banker",
            "InfoFarmer",
            "OpportunityAgent",
        ]:
            agent = self._find_agent(agent_name)

            if agent is None:
                continue

            try:
                reports[agent_name] = agent.get_status_report()
            except Exception as exc:
                reports[agent_name] = {
                    "status": "error",
                    "message": str(exc),
                }

        return {
            "status": "success",
            "agent": self.name,
            "agents": reports,
        }

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _find_agent(self, name: str):
        if name == self.name:
            return self

        registry = getattr(self.tools, "agents", None)

        if isinstance(registry, dict):
            if name in registry:
                return registry[name]

        # The orchestrator normally performs cross-agent routing.
        # This fallback keeps Boss functional when used independently.
        return None

    def _detect_agent(
        self,
        command: str,
    ) -> str:
        lowered = command.lower()

        if "opportunityagent" in lowered:
            return "OpportunityAgent"

        if "opportunity agent" in lowered:
            return "OpportunityAgent"

        if "opportunities" in lowered:
            return "OpportunityAgent"

        if "revenue" in lowered:
            return "OpportunityAgent"

        if "infofarmer" in lowered:
            return "InfoFarmer"

        if "info farmer" in lowered:
            return "InfoFarmer"

        if "researcher" in lowered:
            return "InfoFarmer"

        if "research" in lowered:
            return "InfoFarmer"

        if "banker" in lowered:
            return "Banker"

        if "finance" in lowered:
            return "Banker"

        if "money" in lowered:
            return "Banker"

        return ""

    def _get_mode(self) -> str:
        try:
            if hasattr(self.tools, "get_mode"):
                return self.tools.get_mode()
        except Exception:
            pass

        return "simulation"

    # ------------------------------------------------------------------
    # Help
    # ------------------------------------------------------------------

    def get_help(self) -> Dict[str, Any]:
        return {
            "status": "success",
            "agent": self.name,
            "role": self.role,
            "commands": [
                "status",
                "agent status",
                "balance",
                "research <query>",
                "search <query>",
                "farm <topic>",
                "scan",
                "scan <category>",
                "opportunities",
                "analyse <opportunity_id>",
                "analyze <opportunity_id>",
                "economy",
                "mode",
                "assign <task>",
                "delegate <agent> <task>",
                "run",
                "help",
            ],
            "capabilities": [
                "System coordination",
                "Agent delegation",
                "Research requests",
                "Opportunity discovery",
                "Opportunity analysis",
                "Task creation",
                "System monitoring",
            ],
            "safety": (
                "Boss cannot change operating mode or bypass "
                "Creator approval for consequential actions."
            ),
        }
