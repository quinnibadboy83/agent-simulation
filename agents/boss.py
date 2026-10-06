"""
Boss Agent
----------

Top-level coordinator for the agent system.

The Boss can:
- inspect system state
- delegate tasks
- request research
- inspect opportunities
- analyse the economy
- coordinate other agents

The Boss cannot bypass Creator approval or change
the operating mode.
"""

from typing import Any, Dict, Optional

from .base_agent import BaseAgent
from core.economy import Economy
from core.memory import SharedMemory
from core.tools import ToolRegistry


class BossAgent(BaseAgent):
    def __init__(
        self,
        memory: SharedMemory,
        tools: ToolRegistry,
        economy: Optional[Economy] = None,
    ):
        self.economy = economy

        super().__init__(
            name="Boss",
            role="Overseer",
            memory=memory,
            tools=tools,
            description=(
                "Coordinates the agent system, "
                "delegates work and monitors objectives."
            ),
            identity=(
                "You are Boss, the coordinating intelligence "
                "of the autonomous agent system. "
                "You coordinate other agents, reason about "
                "objectives and delegate work. "
                "You never bypass Creator approval."
            ),
        )

    def process_command(
        self,
        command: str,
    ) -> Any:

        command = str(command).strip()

        if not command:
            return "Boss received an empty command."

        self.perceive(
            command,
            source="creator",
        )

        lowered = command.lower()

        # --------------------------------------------------
        # HELP
        # --------------------------------------------------

        if lowered in {
            "help",
            "?",
            "commands",
        }:
            return self._help()

        # --------------------------------------------------
        # STATUS
        # --------------------------------------------------

        if lowered in {
            "status",
            "system status",
            "system",
        }:
            return self._system_status()

        # --------------------------------------------------
        # AGENT STATUS
        # --------------------------------------------------

        if (
            lowered.startswith("agent status")
            or lowered.startswith("agents")
        ):
            return self._agent_status()

        # --------------------------------------------------
        # BALANCE
        # --------------------------------------------------

        if (
            lowered == "balance"
            or lowered == "money"
            or lowered == "bank balance"
        ):
            return self.execute_tool(
                "check_balance"
            )

        # --------------------------------------------------
        # RESEARCH
        # --------------------------------------------------

        if (
            lowered.startswith("research ")
            or lowered.startswith("search ")
        ):
            topic = self._extract_after_prefix(
                command,
                [
                    "research",
                    "search",
                ],
            )

            return self.execute_tool(
                "web_search",
                query=topic,
            )

        # --------------------------------------------------
        # FARM INFORMATION
        # --------------------------------------------------

        if (
            lowered.startswith("farm ")
            or lowered.startswith("farm info ")
        ):
            topic = self._extract_after_prefix(
                command,
                [
                    "farm info",
                    "farm",
                ],
            )

            return self.execute_tool(
                "farm_info",
                topic=topic,
                agent=self.name,
            )

        # --------------------------------------------------
        # OPPORTUNITIES
        # --------------------------------------------------

        if (
            lowered in {
                "scan",
                "scan opportunities",
                "find opportunities",
                "opportunities",
            }
        ):
            return self.execute_tool(
                "list_opportunities"
            )

        if (
            lowered.startswith("analyse ")
            or lowered.startswith("analyze ")
        ):
            remainder = self._extract_after_prefix(
                command,
                [
                    "analyse",
                    "analyze",
                ],
            )

            try:
                opportunity_id = int(
                    remainder.split()[0]
                )
            except (
                ValueError,
                IndexError,
            ):
                return (
                    "Usage: analyse <opportunity_id>"
                )

            return self.execute_tool(
                "analyse_opportunity",
                opp_id=opportunity_id,
            )

        # --------------------------------------------------
        # ECONOMY REPORT
        # --------------------------------------------------

        if lowered in {
            "economy",
            "economy report",
            "financial report",
            "finance",
        }:
            return self.execute_tool(
                "economy_report"
            )

        # --------------------------------------------------
        # MODE
        # --------------------------------------------------

        if lowered in {
            "mode",
            "operating mode",
            "economy mode",
        }:
            return self.execute_tool(
                "money_mode"
            )

        if (
            lowered.startswith("mode ")
            or lowered.startswith("set mode ")
            or lowered.startswith("economy mode ")
        ):
            return (
                "Operating mode is Creator-controlled. "
                "Use the Creator dashboard to switch "
                "between SIMULATION and REAL/LIVE mode."
            )

        # --------------------------------------------------
        # TASK CREATION
        # --------------------------------------------------

        if (
            lowered.startswith("task ")
            or lowered.startswith("assign ")
            or lowered.startswith("delegate ")
        ):
            return self._create_task_from_command(
                command
            )

        # --------------------------------------------------
        # DIRECT AGENT DELEGATION
        # --------------------------------------------------

        detected_agent = self._detect_agent(
            lowered
        )

        if detected_agent:
            return self._delegate_to_agent(
                detected_agent,
                command,
            )

        # --------------------------------------------------
        # GENERIC REASONING
        # --------------------------------------------------

        return self.run_cycle(
            command
        )

    # ======================================================
    # TASKS
    # ======================================================

    def _create_task_from_command(
        self,
        command: str,
    ) -> Dict[str, Any]:

        text = command.strip()

        for prefix in [
            "task",
            "assign",
            "delegate",
        ]:
            if text.lower().startswith(prefix):
                text = text[
                    len(prefix):
                ].strip()
                break

        target = self._detect_agent(
            text.lower()
        )

        if not target:
            return {
                "success": False,
                "error": (
                    "No valid target agent found. "
                    "Use Boss, Banker, InfoFarmer or "
                    "OpportunityAgent."
                ),
            }

        cleaned = text

        for agent_name in [
            "OpportunityAgent",
            "InfoFarmer",
            "Banker",
            "Boss",
        ]:
            if cleaned.lower().startswith(
                agent_name.lower()
            ):
                cleaned = cleaned[
                    len(agent_name):
                ].strip()

        if cleaned.startswith(":"):
            cleaned = cleaned[1:].strip()

        if not cleaned:
            return {
                "success": False,
                "error": "No task description supplied.",
            }

        task = self.memory.add_task(
            title=cleaned[:100],
            description=cleaned,
            assigned_to=target,
            created_by=self.name,
        )

        self.memory.log(
            self.name,
            (
                f"Task #{task['id']} delegated "
                f"to {target}: {cleaned}"
            ),
        )

        return {
            "success": True,
            "message": (
                f"Task #{task['id']} assigned "
                f"to {target}."
            ),
            "task": task,
        }

    def _delegate_to_agent(
        self,
        agent_name: str,
        command: str,
    ) -> Dict[str, Any]:

        task_description = command.strip()

        prefixes = [
            agent_name,
            agent_name.lower(),
        ]

        for prefix in prefixes:
            if task_description.startswith(
                prefix
            ):
                task_description = (
                    task_description[
                        len(prefix):
                    ].strip()
                )
                break

        if task_description.startswith(":"):
            task_description = (
                task_description[1:].strip()
            )

        if not task_description:
            return {
                "success": False,
                "error": (
                    f"No task supplied for "
                    f"{agent_name}."
                ),
            }

        task = self.memory.add_task(
            title=task_description[:100],
            description=task_description,
            assigned_to=agent_name,
            created_by=self.name,
        )

        return {
            "success": True,
            "message": (
                f"Task #{task['id']} assigned "
                f"to {agent_name}."
            ),
            "task": task,
        }

    # ======================================================
    # REPORTING
    # ======================================================

    def _system_status(self) -> Dict[str, Any]:

        world = self.memory.get_world_state()

        return {
            "agent": self.name,
            "status": self.status,
            "mode": (
                self.economy.get_mode()
                if self.economy
                else "simulation"
            ),
            "world": world,
            "agents": (
                self.memory.get_all_agent_status()
            ),
            "pending_tasks": self.memory.get_tasks(
                status="pending"
            ),
            "pending_approvals": (
                self.tools.approval_gate.list_pending()
            ),
            "balance": self.memory.get_balance(
                "Banker"
            ),
        }

    def _agent_status(self) -> Dict[str, Any]:

        return {
            "success": True,
            "agents": (
                self.memory.get_all_agent_status()
            ),
        }

    # ======================================================
    # HELP
    # ======================================================

    def _help(self) -> str:

        return """
Boss command interface

SYSTEM
------
status
agents
balance
mode
economy report

RESEARCH
--------
research <topic>
search <topic>
farm <topic>

OPPORTUNITIES
-------------
scan
opportunities
analyse <id>

TASKS
-----
task <agent> <description>
assign <agent> <description>
delegate <agent> <description>

AGENTS
------
Boss <task>
Banker <task>
InfoFarmer <task>
OpportunityAgent <task>

Creator-controlled actions
--------------------------
Operating mode changes are controlled by the Creator dashboard.

Consequential actions cannot bypass the Creator Approval Gate.
""".strip()

    # ======================================================
    # HELPERS
    # ======================================================

    @staticmethod
    def _extract_after_prefix(
        command: str,
        prefixes: list,
    ) -> str:

        lowered = command.lower()

        for prefix in prefixes:
            if lowered.startswith(
                prefix.lower()
            ):
                return command[
                    len(prefix):
                ].strip()

        return command.strip()

    @staticmethod
    def _detect_agent(
        text: str,
    ) -> Optional[str]:

        candidates = [
            "OpportunityAgent",
            "InfoFarmer",
            "Banker",
            "Boss",
        ]

        lowered = text.lower()

        for agent in candidates:
            if agent.lower() in lowered:
                return agent

        aliases = {
            "opportunity": "OpportunityAgent",
            "opportunities": "OpportunityAgent",
            "farmer": "InfoFarmer",
            "research": "InfoFarmer",
            "bank": "Banker",
            "finance": "Banker",
        }

        for alias, agent in aliases.items():
            if alias in lowered:
                return agent

        return None
