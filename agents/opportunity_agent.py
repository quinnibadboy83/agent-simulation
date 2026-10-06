"""
Opportunity Agent
-----------------
Finds, evaluates, and develops potential revenue opportunities.

The agent can research and analyse opportunities autonomously.
Consequential financial actions require Creator approval through the
central ToolRegistry.
"""

from typing import Any, Dict

from .base_agent import BaseAgent


class OpportunityAgent(BaseAgent):
    def __init__(self, memory, tools):
        super().__init__(
            name="OpportunityAgent",
            role="Opportunity Discovery and Revenue Strategy",
            memory=memory,
            tools=tools,
            description=(
                "Discovers potential opportunities, researches them, "
                "scores their viability, designs experiments, and "
                "reports findings to the Boss."
            ),
        )

    def process_order(self, order: str) -> Dict[str, Any]:
        command = (order or "").strip()

        if not command:
            return {
                "status": "error",
                "agent": self.name,
                "message": "No opportunity order supplied.",
            }

        lowered = command.lower()

        if lowered in {"help", "?", "commands"}:
            return self.get_help()

        if lowered in {"mode", "money mode", "operating mode"}:
            return self.execute_tool("money_mode")

        if lowered in {
            "scan",
            "scan opportunities",
            "find opportunities",
            "find opportunity",
        }:
            return self.execute_tool("find_opportunity")

        if lowered.startswith("scan "):
            criteria = command[5:].strip()

            if not criteria:
                return self.execute_tool("find_opportunity")

            return self.execute_tool(
                "find_opportunity",
                criteria=criteria,
            )

        if lowered.startswith("find "):
            criteria = command[5:].strip()

            if not criteria:
                return {
                    "status": "error",
                    "agent": self.name,
                    "message": "Opportunity criteria are required.",
                }

            return self.execute_tool(
                "find_opportunity",
                criteria=criteria,
            )

        if lowered in {"opportunities", "list opportunities", "list"}:
            return self.execute_tool("list_opportunities")

        if lowered.startswith("analyse "):
            target = command[8:].strip()

            if not target:
                return {
                    "status": "error",
                    "agent": self.name,
                    "message": "Opportunity ID or description is required.",
                }

            return self._analyse(target)

        if lowered.startswith("analyze "):
            target = command[8:].strip()

            if not target:
                return {
                    "status": "error",
                    "agent": self.name,
                    "message": "Opportunity ID or description is required.",
                }

            return self._analyse(target)

        if lowered in {"analyse", "analyze"}:
            return {
                "status": "error",
                "agent": self.name,
                "message": "Opportunity ID or description is required.",
            }

        if lowered.startswith("test "):
            description = command[5:].strip()

            if not description:
                return {
                    "status": "error",
                    "agent": self.name,
                    "message": "Experiment description is required.",
                }

            return self._create_experiment(description)

        if lowered.startswith("experiment "):
            description = command[11:].strip()

            if not description:
                return {
                    "status": "error",
                    "agent": self.name,
                    "message": "Experiment description is required.",
                }

            return self._create_experiment(description)

        if lowered in {"test", "experiment"}:
            return {
                "status": "error",
                "agent": self.name,
                "message": "Experiment description is required.",
            }

        if lowered in {
            "report",
            "economy report",
            "revenue report",
            "financial report",
        }:
            return self.execute_tool("economy_report")

        if lowered in {"status", "agent status"}:
            return self.get_status_report()

        if lowered in {"run", "cycle", "run cycle"}:
            return self.run_cycle()

        return {
            "status": "error",
            "agent": self.name,
            "message": f"Unknown OpportunityAgent command: {command}",
            "help": self.get_help(),
        }

    def _analyse(self, target: str) -> Dict[str, Any]:
        result = self.execute_tool(
            "analyse_opportunity",
            opportunity_id=target,
        )

        self.observe_result(result)

        return result

    def _create_experiment(self, description: str) -> Dict[str, Any]:
        result = self.execute_tool(
            "create_experiment",
            description=description,
        )

        self.observe_result(result)

        return result

    def scan(self, criteria: str = "") -> Dict[str, Any]:
        kwargs = {}

        if criteria:
            kwargs["criteria"] = criteria

        result = self.execute_tool(
            "find_opportunity",
            **kwargs,
        )

        self.observe_result(result)

        return result

    def list_opportunities(self) -> Dict[str, Any]:
        result = self.execute_tool("list_opportunities")

        self.observe_result(result)

        return result

    def analyse(self, opportunity_id: str) -> Dict[str, Any]:
        result = self.execute_tool(
            "analyse_opportunity",
            opportunity_id=opportunity_id,
        )

        self.observe_result(result)

        return result

    def create_experiment(self, description: str) -> Dict[str, Any]:
        result = self.execute_tool(
            "create_experiment",
            description=description,
        )

        self.observe_result(result)

        return result

    def economy_report(self) -> Dict[str, Any]:
        result = self.execute_tool("economy_report")

        self.observe_result(result)

        return result

    def get_help(self) -> Dict[str, Any]:
        return {
            "status": "success",
            "agent": self.name,
            "role": self.role,
            "commands": [
                "mode",
                "scan",
                "scan <criteria>",
                "find <criteria>",
                "opportunities",
                "analyse <opportunity_id>",
                "analyze <opportunity_id>",
                "test <experiment description>",
                "experiment <experiment description>",
                "report",
                "status",
                "run",
                "help",
            ],
            "capabilities": [
                "Opportunity discovery",
                "Opportunity analysis",
                "Revenue strategy",
                "Experiment design",
                "Economic reporting",
                "Opportunity prioritisation",
            ],
            "safety": (
                "Research and analysis may run autonomously. "
                "Consequential financial or external actions require "
                "Creator approval."
            ),
        }
