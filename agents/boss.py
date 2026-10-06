"""
Boss Agent
----------

Overseer of the autonomous agent system.

The Boss:
- receives Creator commands
- delegates work
- monitors other agents
- can inspect the economy
- can request protected actions
- cannot bypass Creator approval
"""

from typing import Any, Dict, List

from .base_agent import BaseAgent
from core.memory import SharedMemory
from core.tools import ToolRegistry


class BossAgent(BaseAgent):

    def __init__(
        self,
        memory: SharedMemory,
        tools: ToolRegistry,
    ):
        super().__init__(
            name="Boss",
            role="Overseer",
            memory=memory,
            tools=tools,
            description=(
                "Oversees the agent system, "
                "delegates objectives, monitors "
                "progress and coordinates the "
                "other agents."
            ),
        )

        self.update_status("ready")

    # ------------------------------------------------------------------
    # Main command interface
    # ------------------------------------------------------------------

    def process_command(
        self,
        command: str,
    ) -> str:

        command_text = command.strip()

        if not command_text:
            return "Boss received an empty command."

        self.memory.log(
            "Boss",
            f"Creator command received: {command_text}",
        )

        self.perceive(
            command_text,
            source="creator",
        )

        self.remember(
            command_text,
            category="creator_command",
        )

        command_lower = command_text.lower()

        # --------------------------------------------------------------
        # Help
        # --------------------------------------------------------------

        if (
            command_lower == "help"
            or command_lower.startswith("help ")
        ):
            return self._help()

        # --------------------------------------------------------------
        # Status
        # --------------------------------------------------------------

        if (
            command_lower == "status"
            or "system status" in command_lower
        ):
            return self._system_status()

        # --------------------------------------------------------------
        # Agent status
        # --------------------------------------------------------------

        if (
            "agent status" in command_lower
            or command_lower == "agents"
            or command_lower == "agent status"
        ):
            return self._agent_status()

        # --------------------------------------------------------------
        # Balance
        # --------------------------------------------------------------

        if (
            "balance" in command_lower
            or "banker report" in command_lower
        ):
            return self.execute_tool(
                "check_balance"
            ).get(
                "result",
                "Unable to retrieve balance.",
            )

        # --------------------------------------------------------------
        # Research delegation
        # --------------------------------------------------------------

        if (
            command_lower.startswith("research ")
            or command_lower.startswith("find information ")
            or command_lower.startswith("search ")
        ):
            topic = self._extract_after_prefix(
                command_text,
                [
                    "research",
                    "find information",
                    "search",
                ],
            )

            if not topic:
                return (
                    "Specify a research topic."
                )

            return self._delegate_research(
                topic
            )

        # --------------------------------------------------------------
        # Farming
        # --------------------------------------------------------------

        if (
            command_lower.startswith("farm ")
            or "farm information" in command_lower
        ):
            topic = self._extract_after_prefix(
                command_text,
                [
                    "farm information",
                    "farm",
                ],
            )

            if not topic:
                return (
                    "Specify what InfoFarmer "
                    "should research."
                )

            return self._delegate_research(
                topic
            )

        # --------------------------------------------------------------
        # Opportunity scanning
        # --------------------------------------------------------------

        if (
            "scan opportunities" in command_lower
            or command_lower == "scan"
            or "find opportunities" in command_lower
        ):
            return self._delegate_opportunities(
                "scan"
            )

        # --------------------------------------------------------------
        # Opportunity listing
        # --------------------------------------------------------------

        if (
            "list opportunities"
            in command_lower
            or command_lower == "opportunities"
        ):
            return self._delegate_opportunities(
                "opportunities"
            )

        # --------------------------------------------------------------
        # Economy report
        # --------------------------------------------------------------

        if (
            "economy report" in command_lower
            or command_lower == "economy"
        ):
            return self._delegate_opportunities(
                "report"
            )

        # --------------------------------------------------------------
        # Simulation / real mode
        # --------------------------------------------------------------

        if (
            "simulation mode" in command_lower
            or command_lower == "simulation"
        ):
            return self._delegate_opportunities(
                "mode simulation"
            )

        if (
            "real mode" in command_lower
            or "live mode" in command_lower
            or command_lower == "real"
        ):
            return self._delegate_opportunities(
                "mode real"
            )

        # --------------------------------------------------------------
        # Task creation
        # --------------------------------------------------------------

        if (
            command_lower.startswith("task ")
            or command_lower.startswith("assign ")
        ):
            return self._create_task_from_command(
                command_text
            )

        # --------------------------------------------------------------
        # Generic delegation
        # --------------------------------------------------------------

        if "banker" in command_lower:
            return self._send_to_agent(
                "Banker",
                command_text,
            )

        if (
            "infofarmer" in command_lower
            or "researcher" in command_lower
        ):
            return self._send_to_agent(
                "InfoFarmer",
                command_text,
            )

        if (
            "opportunity" in command_lower
            or "scout" in command_lower
        ):
            return self._send_to_agent(
                "OpportunityAgent",
                command_text,
            )

        # --------------------------------------------------------------
        # Standard cognitive cycle
        # --------------------------------------------------------------

        return self.run_cycle(
            command_text
        )["reasoning"]

    # ------------------------------------------------------------------
    # Delegation
    # ------------------------------------------------------------------

    def _delegate_research(
        self,
        topic: str,
    ) -> str:

        task = self.memory.add_task(
            title=f"Research: {topic}",
            description=(
                f"Research and collect useful "
                f"information about {topic}."
            ),
            assigned_to="InfoFarmer",
            created_by="Boss",
        )

        self.memory.log(
            "Boss",
            (
                f"Delegated research task "
                f"#{task['id']} to InfoFarmer."
            ),
        )

        return (
            f"Research task #{task['id']} "
            f"assigned to InfoFarmer.\n"
            f"Topic: {topic}"
        )

    def _delegate_opportunities(
        self,
        command: str,
    ) -> str:

        task = self.memory.add_task(
            title=(
                f"Opportunity: {command}"
            ),
            description=(
                f"OpportunityAgent should "
                f"execute: {command}"
            ),
            assigned_to="OpportunityAgent",
            created_by="Boss",
        )

        self.memory.log(
            "Boss",
            (
                f"Delegated opportunity task "
                f"#{task['id']}."
            ),
        )

        return (
            f"Opportunity task #{task['id']} "
            f"assigned to OpportunityAgent.\n"
            f"Instruction: {command}"
        )

    def _send_to_agent(
        self,
        agent_name: str,
        command: str,
    ) -> str:

        task = self.memory.add_task(
            title=(
                f"Boss instruction: "
                f"{command[:60]}"
            ),
            description=command,
            assigned_to=agent_name,
            created_by="Boss",
        )

        self.memory.log(
            "Boss",
            (
                f"Delegated task #{task['id']} "
                f"to {agent_name}."
            ),
        )

        return (
            f"Task #{task['id']} assigned "
            f"to {agent_name}."
        )

    # ------------------------------------------------------------------
    # Task creation
    # ------------------------------------------------------------------

    def _create_task_from_command(
        self,
        command: str,
    ) -> str:

        text = command.strip()

        lower = text.lower()

        if lower.startswith("task "):
            remainder = text[5:].strip()
        elif lower.startswith("assign "):
            remainder = text[7:].strip()
        else:
            remainder = text

        if not remainder:
            return (
                "Task requires an instruction."
            )

        assigned_to = self._detect_agent(
            remainder
        )

        if assigned_to is None:
            return (
                "Specify an agent: "
                "Banker, InfoFarmer or "
                "OpportunityAgent."
            )

        cleaned = remainder

        for name in (
            "OpportunityAgent",
            "InfoFarmer",
            "Banker",
        ):
            cleaned = cleaned.replace(
                name,
                "",
            )

        cleaned = cleaned.strip(
            " :-"
        )

        if not cleaned:
            return (
                "Specify what the agent "
                "should do."
            )

        task = self.memory.add_task(
            title=cleaned[:100],
            description=cleaned,
            assigned_to=assigned_to,
            created_by="Boss",
        )

        return (
            f"Task #{task['id']} created.\n"
            f"Assigned to: {assigned_to}\n"
            f"Instruction: {cleaned}"
        )

    # ------------------------------------------------------------------
    # Status
    # ------------------------------------------------------------------

    def _system_status(
        self,
    ) -> str:

        agents = (
            self.memory.get_all_agent_status()
        )

        pending = self.memory.get_tasks(
            status="pending"
        )

        balance = self.memory.get_balance(
            "Banker"
        )

        return (
            "=== SYSTEM STATUS ===\n"
            f"Agents: {len(agents)}\n"
            f"Pending tasks: {len(pending)}\n"
            f"Bank balance: ${balance:.2f}\n"
            "\n"
            + self._agent_status()
        )

    def _agent_status(
        self,
    ) -> str:

        agents = (
            self.memory.get_all_agent_status()
        )

        if not agents:
            return "No agents registered."

        report = "=== AGENTS ===\n"

        for name, status in agents.items():

            report += (
                f"{name}: "
                f"{status.get('status', 'unknown')}"
            )

            objective = status.get(
                "objective"
            )

            if objective:
                report += (
                    f" | Objective: {objective}"
                )

            report += "\n"

        return report.rstrip()

    # ------------------------------------------------------------------
    # Help
    # ------------------------------------------------------------------

    @staticmethod
    def _help() -> str:

        return (
            "=== BOSS COMMANDS ===\n"
            "\n"
            "status\n"
            "agents\n"
            "balance\n"
            "research <topic>\n"
            "farm <topic>\n"
            "scan opportunities\n"
            "list opportunities\n"
            "economy report\n"
            "simulation mode\n"
            "real mode\n"
            "task <agent> <instruction>\n"
            "\n"
            "Available agents:\n"
            "  Banker\n"
            "  InfoFarmer\n"
            "  OpportunityAgent\n"
            "\n"
            "REAL mode does not bypass Creator "
            "approval. Protected actions remain "
            "blocked until explicitly approved."
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_after_prefix(
        text: str,
        prefixes: List[str],
    ) -> str:

        lowered = text.lower()

        for prefix in sorted(
            prefixes,
            key=len,
            reverse=True,
        ):
            prefix_lower = prefix.lower()

            if lowered.startswith(
                prefix_lower
            ):
                return text[
                    len(prefix):
                ].strip(
                    " :-"
                )

        return ""

    @staticmethod
    def _detect_agent(
        text: str,
    ) -> Any:

        lowered = text.lower()

        if "opportunityagent" in lowered:
            return "OpportunityAgent"

        if "infofarmer" in lowered:
            return "InfoFarmer"

        if "banker" in lowered:
            return "Banker"

        return None
