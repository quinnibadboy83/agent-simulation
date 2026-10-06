"""
OpportunityAgent
----------------

Economic Scout & Analyst.

Responsibilities:

    FIND
    ANALYSE
    VALIDATE
    TEST
    REPORT

The OpportunityAgent does not directly control money.

Financial state remains under the Banker/shared economy system.

Important:
    REAL mode does not bypass Creator approval.

Economic experiments are protected actions and therefore
pass through the ToolRegistry approval system.
"""

from typing import Any, Dict, List, Optional

from .base_agent import BaseAgent
from core.memory import SharedMemory
from core.tools import ToolRegistry
from core.economy import Economy


class OpportunityAgent(BaseAgent):

    def __init__(
        self,
        memory: SharedMemory,
        tools: ToolRegistry,
        economy: Economy,
    ):
        super().__init__(
            name="OpportunityAgent",
            role="Economic Scout & Analyst",
            memory=memory,
            tools=tools,
            description=(
                "Finds, analyses, tests and reports "
                "on economic opportunities. "
                "Works in simulation or real mode "
                "while respecting Creator approval."
            ),
        )

        self.economy = economy

        self.update_status("ready")

    # ------------------------------------------------------------------
    # Orders
    # ------------------------------------------------------------------

    def process_order(
        self,
        order: str,
    ) -> str:

        self.memory.log(
            "OpportunityAgent",
            f"Received order: {order}",
        )

        order_text = order.strip()
        order_lower = order_text.lower()

        if not order_text:
            return (
                "OpportunityAgent needs an objective."
            )

        # --------------------------------------------------------------
        # Economy mode
        # --------------------------------------------------------------

        if "mode" in order_lower:

            if "simulation" in order_lower:
                result = self.execute_tool(
                    "money_mode",
                    mode="simulation",
                )

            elif (
                "real" in order_lower
                or "live" in order_lower
            ):
                result = self.execute_tool(
                    "money_mode",
                    mode="real",
                )

            else:
                result = self.execute_tool(
                    "money_mode"
                )

            return self._tool_message(
                result
            )

        # --------------------------------------------------------------
        # Scan
        # --------------------------------------------------------------

        if any(
            word in order_lower
            for word in (
                "scan",
                "find",
                "discover",
            )
        ):
            return self._scan_opportunities()

        # --------------------------------------------------------------
        # List
        # --------------------------------------------------------------

        if (
            "opportunities" in order_lower
            or order_lower == "list"
            or "list opportunities"
            in order_lower
        ):
            return self._list_opportunities()

        # --------------------------------------------------------------
        # Analyse
        # --------------------------------------------------------------

        if (
            "analyse" in order_lower
            or "analyze" in order_lower
        ):
            opp_id = self._extract_id(
                order_text
            )

            if opp_id is None:
                return (
                    "Please specify an opportunity "
                    "ID, e.g. 'analyse 1'."
                )

            return self._analyse_opportunity(
                opp_id
            )

        # --------------------------------------------------------------
        # Test / experiment
        # --------------------------------------------------------------

        if (
            "test" in order_lower
            or "experiment" in order_lower
        ):
            opp_id = self._extract_id(
                order_text
            )

            if opp_id is None:
                return (
                    "Please specify an opportunity "
                    "ID, e.g. 'test 1'."
                )

            return self._test_opportunity(
                opp_id
            )

        # --------------------------------------------------------------
        # Economy report
        # --------------------------------------------------------------

        if (
            "report" in order_lower
            or "economy report"
            in order_lower
        ):
            return self._economy_report()

        return (
            "OpportunityAgent received: "
            f"'{order_text}'.\n\n"
            "Available commands:\n"
            "  scan\n"
            "  opportunities\n"
            "  analyse <id>\n"
            "  test <id>\n"
            "  report\n"
            "  mode\n"
            "  mode simulation\n"
            "  mode real"
        )

    # ------------------------------------------------------------------
    # Scan
    # ------------------------------------------------------------------

    def _scan_opportunities(
        self,
    ) -> str:

        ideas = [
            {
                "name": (
                    "AI Research Summary Service"
                ),
                "description": (
                    "Sell short AI-generated "
                    "research summaries on "
                    "legitimate trending topics."
                ),
                "startup_cost": 30,
                "expected_expenses": 15,
                "expected_revenue": 120,
                "risk": "low",
            },
            {
                "name": (
                    "Digital Template Pack"
                ),
                "description": (
                    "Create and sell original "
                    "Notion, Canva or spreadsheet "
                    "templates."
                ),
                "startup_cost": 20,
                "expected_expenses": 10,
                "expected_revenue": 90,
                "risk": "low",
            },
            {
                "name": (
                    "Automated Lead Finder"
                ),
                "description": (
                    "Provide a legitimate service "
                    "that identifies potential "
                    "customers for small businesses."
                ),
                "startup_cost": 80,
                "expected_expenses": 40,
                "expected_revenue": 250,
                "risk": "medium",
            },
        ]

        created = []

        for idea in ideas:

            result = self.execute_tool(
                "find_opportunity",
                **idea,
            )

            if result.get("success"):
                created.append(
                    result.get("result")
                )

        if not created:
            return (
                "No new opportunities found."
            )

        message = (
            "Opportunity scan complete. "
            f"Found {len(created)} ideas:\n\n"
        )

        for opportunity in created:

            if not isinstance(
                opportunity,
                dict,
            ):
                continue

            message += (
                f"[{opportunity.get('id', '?')}] "
                f"{opportunity.get('name', 'Unnamed')} "
                f"(Risk: "
                f"{opportunity.get('risk', 'unknown')})\n"
            )

        message += (
            "\nUse "
            "'analyse <id>' "
            "or "
            "'test <id>' "
            "next."
        )

        return message

    # ------------------------------------------------------------------
    # List
    # ------------------------------------------------------------------

    def _list_opportunities(
        self,
    ) -> str:

        result = self.execute_tool(
            "list_opportunities"
        )

        if not result.get("success"):
            return (
                "Could not list opportunities: "
                + str(
                    result.get(
                        "error",
                        "Unknown error.",
                    )
                )
            )

        opportunities = result.get(
            "result",
            [],
        )

        if not opportunities:
            return (
                "No opportunities yet. "
                "Try 'scan'."
            )

        message = (
            "Current Opportunities:\n\n"
        )

        for opportunity in opportunities:

            message += (
                f"[{opportunity.get('id', '?')}] "
                f"{opportunity.get('name', 'Unnamed')} "
                f"— "
                f"{opportunity.get('status', 'UNKNOWN')} "
                f"(Risk: "
                f"{opportunity.get('risk', 'unknown')})\n"
            )

        return message

    # ------------------------------------------------------------------
    # Analyse
    # ------------------------------------------------------------------

    def _analyse_opportunity(
        self,
        opp_id: int,
    ) -> str:

        result = self.execute_tool(
            "analyse_opportunity",
            opp_id=opp_id,
        )

        if not result.get("success"):
            return (
                f"Failed to analyse "
                f"Opportunity #{opp_id}: "
                + str(
                    result.get(
                        "error",
                        "Unknown error.",
                    )
                )
            )

        analysis = result.get(
            "result",
            {},
        )

        if not isinstance(
            analysis,
            dict,
        ):
            return (
                f"Opportunity #{opp_id} "
                "returned an invalid analysis."
            )

        return (
            f"Analysis of Opportunity #{opp_id}:\n"
            f"Potential Profit: "
            f"${analysis.get('potential_profit', 0)}\n"
            f"Estimated ROI: "
            f"{analysis.get('estimated_roi_percent', 0)}%\n"
            f"Risk: "
            f"{analysis.get('risk_level', 'unknown')}\n"
            f"Recommendation: "
            f"{analysis.get('recommendation', 'No recommendation')}"
        )

    # ------------------------------------------------------------------
    # Test
    # ------------------------------------------------------------------

    def _test_opportunity(
        self,
        opp_id: int,
    ) -> str:

        mode = self.economy.get_mode()

        # Keep the simulation test inexpensive.
        # REAL mode uses the same approval-protected tool,
        # but with a smaller default budget.
        if mode == "simulation":
            budget = 50.0
        else:
            budget = 10.0

        result = self.execute_tool(
            "create_experiment",
            opp_id=opp_id,
            budget=budget,
        )

        if not result.get("success"):

            if result.get(
                "requires_approval"
            ):
                approval_id = result.get(
                    "approval_id"
                )

                return (
                    "Experiment requires "
                    "Creator approval before it "
                    "can run.\n"
                    f"Opportunity: #{opp_id}\n"
                    f"Budget: ${budget:.2f}\n"
                    f"Approval request: "
                    f"#{approval_id}"
                )

            return (
                "Could not start experiment: "
                + str(
                    result.get(
                        "error",
                        "Unknown error.",
                    )
                )
            )

        experiment = result.get(
            "result",
            {},
        )

        if not isinstance(
            experiment,
            dict,
        ):
            return (
                "Experiment started, but the "
                "economy returned an unexpected result."
            )

        return (
            f"Experiment "
            f"#{experiment.get('id', '?')} "
            f"started for Opportunity "
            f"#{opp_id} "
            f"with budget "
            f"${budget:.2f}."
        )

    # ------------------------------------------------------------------
    # Economy report
    # ------------------------------------------------------------------

    def _economy_report(
        self,
    ) -> str:

        result = self.execute_tool(
            "economy_report"
        )

        if not result.get("success"):
            return (
                "Could not generate economy report: "
                + str(
                    result.get(
                        "error",
                        "Unknown error.",
                    )
                )
            )

        report = result.get(
            "result",
            {},
        )

        if not isinstance(
            report,
            dict,
        ):
            return (
                "Economy returned an invalid report."
            )

        statuses = report.get(
            "opportunities_by_status",
            {},
        )

        return (
            "=== ECONOMY REPORT "
            f"({report.get('mode', 'UNKNOWN')}) ===\n"
            f"Opportunities: "
            f"{report.get('opportunities_total', 0)}\n"
            f"  DISCOVERED: "
            f"{statuses.get('DISCOVERED', 0)}\n"
            f"  ANALYSED:   "
            f"{statuses.get('ANALYSED', 0)}\n"
            f"  TESTING:    "
            f"{statuses.get('TESTING', 0)}\n"
            f"  VALIDATED:  "
            f"{statuses.get('VALIDATED', 0)}\n"
            f"  REJECTED:   "
            f"{statuses.get('REJECTED', 0)}\n"
            f"Total Revenue:  "
            f"${report.get('total_revenue', 0)}\n"
            f"Total Expenses: "
            f"${report.get('total_expenses', 0)}\n"
            f"Total Profit:   "
            f"${report.get('total_profit', 0)}\n"
            f"Active Experiments: "
            f"{report.get('active_experiments', 0)}"
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_id(
        text: str,
    ) -> Optional[int]:

        digits = ""

        for character in text:
            if character.isdigit():
                digits += character
            elif digits:
                break

        if not digits:
            return None

        try:
            return int(digits)
        except ValueError:
            return None

    @staticmethod
    def _tool_message(
        result: Dict[str, Any],
    ) -> str:

        if result.get("success"):
            return str(
                result.get(
                    "result",
                    "Action completed.",
                )
            )

        if result.get(
            "requires_approval"
        ):
            approval_id = result.get(
                "approval_id"
            )

            return (
                "Creator approval required.\n"
                f"Approval request: #{approval_id}"
            )

        return (
            "Tool failed: "
            + str(
                result.get(
                    "error",
                    "Unknown error.",
                )
            )
        )
