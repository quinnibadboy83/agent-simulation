"""
OpportunityAgent
----------------
Revenue and opportunity-development specialist.

The agent can autonomously research, discover, compare, analyse, and
plan opportunities. Consequential external execution remains behind
the central ToolRegistry and Creator approval system.
"""

from typing import Any, Dict, List

from .base_agent import BaseAgent
from modules.revenue import RevenueStrategy
from modules.social import SocialStrategy


class OpportunityAgent(BaseAgent):
    def __init__(
        self,
        memory,
        tools,
        economy=None,
    ):
        super().__init__(
            name="OpportunityAgent",
            role="Revenue and Opportunity Development",
            memory=memory,
            tools=tools,
            description=(
                "Finds legitimate revenue opportunities, researches "
                "markets, evaluates business ideas, creates safe "
                "experiments, and prepares actionable plans."
            ),
        )

        self.economy = economy
        self.revenue_strategy = RevenueStrategy(
            memory=memory
        )
        self.social_strategy = SocialStrategy(
            memory=memory
        )

    # -----------------------------------------------------------------
    # Command processing
    # -----------------------------------------------------------------

    def process_order(
        self,
        order: str,
    ) -> Dict[str, Any]:
        command = (order or "").strip()

        if not command:
            return {
                "status": "error",
                "agent": self.name,
                "message": "No opportunity order supplied.",
            }

        lowered = command.lower()

        if lowered in {
            "help",
            "?",
            "commands",
        }:
            return self.get_help()

        if lowered in {
            "mode",
            "money mode",
            "economy mode",
        }:
            return self.execute_tool(
                "money_mode"
            )

        if lowered in {
            "scan",
            "scan opportunities",
            "find opportunities",
            "find",
        }:
            return self.scan()

        if lowered in {
            "opportunities",
            "list opportunities",
            "list",
        }:
            return self.list_opportunities()

        if lowered.startswith("scan "):
            category = command[5:].strip()
            return self.scan(
                category=category
            )

        if lowered.startswith("find "):
            category = command[5:].strip()
            return self.scan(
                category=category
            )

        if lowered.startswith("analyse "):
            opportunity_id = command[8:].strip()

            if not opportunity_id:
                return {
                    "status": "error",
                    "agent": self.name,
                    "message": (
                        "Opportunity ID is required."
                    ),
                }

            return self.analyse(
                opportunity_id
            )

        if lowered.startswith("analyze "):
            opportunity_id = command[8:].strip()

            if not opportunity_id:
                return {
                    "status": "error",
                    "agent": self.name,
                    "message": (
                        "Opportunity ID is required."
                    ),
                }

            return self.analyse(
                opportunity_id
            )

        if lowered.startswith("test "):
            opportunity_id = command[5:].strip()

            if not opportunity_id:
                return {
                    "status": "error",
                    "agent": self.name,
                    "message": (
                        "Opportunity ID is required."
                    ),
                }

            return self.create_experiment(
                opportunity_id
            )

        if lowered.startswith("experiment "):
            opportunity_id = command[11:].strip()

            if not opportunity_id:
                return {
                    "status": "error",
                    "agent": self.name,
                    "message": (
                        "Opportunity ID is required."
                    ),
                }

            return self.create_experiment(
                opportunity_id
            )

        if lowered in {
            "report",
            "economy report",
            "revenue report",
        }:
            return self.economy_report()

        if lowered.startswith("ideas"):
            category = ""

            if " " in command:
                category = command.split(
                    " ",
                    1,
                )[1].strip()

            return self.generate_ideas(
                category=category
            )

        if lowered.startswith("social "):
            return self.social_plan(
                command[7:].strip()
            )

        if lowered.startswith("content "):
            return self.social_plan(
                command[8:].strip()
            )

        if lowered in {
            "status",
            "agent status",
        }:
            return self.get_status_report()

        if lowered in {
            "run",
            "cycle",
            "run cycle",
        }:
            return self.run_cycle()

        return {
            "status": "error",
            "agent": self.name,
            "message": (
                f"Unknown OpportunityAgent command: "
                f"{command}"
            ),
            "help": self.get_help(),
        }

    # -----------------------------------------------------------------
    # Opportunity discovery
    # -----------------------------------------------------------------

    def scan(
        self,
        category: str = "",
        budget: float = 0.0,
    ) -> Dict[str, Any]:
        result = self.execute_tool(
            "find_opportunity",
            category=category,
            budget=budget,
        )

        self.observe_result(result)

        return result

    def list_opportunities(
        self,
    ) -> Dict[str, Any]:
        result = self.execute_tool(
            "list_opportunities"
        )

        self.observe_result(result)

        return result

    def analyse(
        self,
        opportunity_id: str,
    ) -> Dict[str, Any]:
        result = self.execute_tool(
            "analyse_opportunity",
            opportunity_id=opportunity_id,
        )

        self.observe_result(result)

        return result

    # -----------------------------------------------------------------
    # Experiment planning
    # -----------------------------------------------------------------

    def create_experiment(
        self,
        opportunity_id: str,
        budget: float = 0.0,
        duration_days: int = 7,
    ) -> Dict[str, Any]:
        result = self.execute_tool(
            "create_experiment",
            opportunity_id=opportunity_id,
            budget=budget,
            duration_days=duration_days,
        )

        self.observe_result(result)

        return result

    # -----------------------------------------------------------------
    # Revenue strategy
    # -----------------------------------------------------------------

    def generate_ideas(
        self,
        category: str = "",
        budget: float = 0.0,
        skill_level: str = "general",
    ) -> Dict[str, Any]:
        try:
            ideas = self.revenue_strategy.generate_ideas(
                category=category,
                budget=budget,
                skill_level=skill_level,
            )

            self.remember(
                {
                    "type": "revenue_ideas",
                    "category": category,
                    "count": len(ideas),
                }
            )

            return {
                "status": "success",
                "agent": self.name,
                "category": category or "all",
                "ideas": ideas,
            }

        except Exception as exc:
            return {
                "status": "error",
                "agent": self.name,
                "message": str(exc),
            }

    def rank_ideas(
        self,
        ideas: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        if not isinstance(ideas, list):
            return {
                "status": "error",
                "agent": self.name,
                "message": "Ideas must be supplied as a list.",
            }

        try:
            ranked = self.revenue_strategy.rank_opportunities(
                ideas
            )

            return {
                "status": "success",
                "agent": self.name,
                "ranked": ranked,
            }

        except Exception as exc:
            return {
                "status": "error",
                "agent": self.name,
                "message": str(exc),
            }

    # -----------------------------------------------------------------
    # Social strategy
    # -----------------------------------------------------------------

    def social_plan(
        self,
        request: str,
    ) -> Dict[str, Any]:
        """
        Create a non-publishing social strategy.

        Accepted formats include:

            social instagram topic
            social linkedin topic
            social youtube topic

        The module only prepares a plan. Publishing remains
        approval-controlled.
        """

        request = (request or "").strip()

        if not request:
            return {
                "status": "error",
                "agent": self.name,
                "message": (
                    "Social platform and topic are required."
                ),
            }

        parts = request.split(
            " ",
            1,
        )

        platform = parts[0].strip()

        if len(parts) > 1:
            topic = parts[1].strip()
        else:
            topic = ""

        if not topic:
            return {
                "status": "error",
                "agent": self.name,
                "message": "Social topic is required.",
            }

        result = (
            self.social_strategy.create_content_plan(
                platform=platform,
                topic=topic,
            )
        )

        self.observe_result(result)

        return {
            "status": result.get(
                "status",
                "success",
            ),
            "agent": self.name,
            "social": result,
        }

    # -----------------------------------------------------------------
    # Reporting
    # -----------------------------------------------------------------

    def economy_report(
        self,
    ) -> Dict[str, Any]:
        result = self.execute_tool(
            "economy_report"
        )

        self.observe_result(result)

        return result

    # -----------------------------------------------------------------
    # Direct helper methods
    # -----------------------------------------------------------------

    def find(
        self,
        category: str = "",
        budget: float = 0.0,
    ) -> Dict[str, Any]:
        return self.scan(
            category=category,
            budget=budget,
        )

    def analyse_opportunity(
        self,
        opportunity_id: str,
    ) -> Dict[str, Any]:
        return self.analyse(
            opportunity_id
        )

    def plan_experiment(
        self,
        opportunity_id: str,
        budget: float = 0.0,
        duration_days: int = 7,
    ) -> Dict[str, Any]:
        return self.create_experiment(
            opportunity_id=opportunity_id,
            budget=budget,
            duration_days=duration_days,
        )

    # -----------------------------------------------------------------
    # Help
    # -----------------------------------------------------------------

    def get_help(self) -> Dict[str, Any]:
        return {
            "status": "success",
            "agent": self.name,
            "role": self.role,
            "commands": [
                "scan",
                "scan <category>",
                "find <category>",
                "opportunities",
                "analyse <opportunity_id>",
                "analyze <opportunity_id>",
                "test <opportunity_id>",
                "experiment <opportunity_id>",
                "ideas",
                "ideas <category>",
                "social <platform> <topic>",
                "content <platform> <topic>",
                "report",
                "mode",
                "status",
                "run",
                "help",
            ],
            "capabilities": [
                "Revenue opportunity discovery",
                "Opportunity analysis",
                "Revenue idea generation",
                "Opportunity ranking",
                "Experiment planning",
                "Social content strategy",
                "Market research",
                "Economic reporting",
            ],
            "safety": {
                "autonomous_research": True,
                "autonomous_analysis": True,
                "autonomous_planning": True,
                "direct_social_publishing": False,
                "direct_external_messaging": False,
                "financial_transactions": False,
                "creator_approval_required_for_consequential_actions": True,
            },
        }
