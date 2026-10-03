"""
OpportunityAgent - Module 2
Responsible for: FIND → ANALYSE → VALIDATE → TEST → REPORT
Works in both simulation and real modes.
Does not control the money — Banker remains the financial authority.
"""

from .base_agent import BaseAgent
from core.memory import SharedMemory
from core.tools import ToolRegistry
from core.economy import Economy


class OpportunityAgent(BaseAgent):
    def __init__(self, memory: SharedMemory, tools: ToolRegistry, economy: Economy):
        super().__init__(
            name="OpportunityAgent",
            role="Economic Scout & Analyst",
            memory=memory,
            tools=tools,
            description="Finds, analyses, tests and reports on opportunities. Works in simulation or real mode.",
        )
        self.economy = economy
        self.update_status("ready")

    def process_order(self, order: str) -> str:
        """Main entry for orders coming from the Boss."""
        self.memory.log("OpportunityAgent", f"Received order: {order}")
        order_lower = order.lower().strip()

        # Mode commands
        if "mode" in order_lower:
            if "simulation" in order_lower:
                return self.tools.execute("money_mode", mode="simulation")["result"]
            if "real" in order_lower:
                return self.tools.execute("money_mode", mode="real")["result"]
            return self.tools.execute("money_mode")["result"]

        # Scan / find new opportunities (simple simulated discovery for now)
        if any(word in order_lower for word in ["scan", "find", "discover", "search"]):
            return self._scan_opportunities()

        # List opportunities
        if "opportunities" in order_lower or "list" in order_lower:
            return self._list_opportunities()

        # Analyse specific opportunity
        if "analyse" in order_lower or "analyze" in order_lower:
            try:
                opp_id = int(''.join(filter(str.isdigit, order)))
                result = self.tools.execute("analyse_opportunity", opp_id=opp_id)
                if result["success"]:
                    analysis = result["result"]
                    return (
                        f"Analysis of Opportunity #{opp_id}:\n"
                        f"Potential Profit: ${analysis['potential_profit']}\n"
                        f"Estimated ROI: {analysis['estimated_roi_percent']}%\n"
                        f"Risk: {analysis['risk_level']}\n"
                        f"Recommendation: {analysis['recommendation']}"
                    )
                return f"Failed to analyse: {result.get('error')}"
            except:
                return "Please specify an opportunity ID, e.g. 'analyse 1'"

        # Start a test / experiment
        if "test" in order_lower or "experiment" in order_lower:
            try:
                opp_id = int(''.join(filter(str.isdigit, order)))
                # Default small budget for simulation
                budget = 50.0 if self.economy.is_simulation() else 10.0
                result = self.tools.execute("create_experiment", opp_id=opp_id, budget=budget)
                if result["success"]:
                    exp = result["result"]
                    return f"Experiment #{exp['id']} started for Opportunity #{opp_id} with budget ${budget}"
                return f"Could not start experiment: {result.get('error')}"
            except:
                return "Please specify an opportunity ID, e.g. 'test 1'"

        # Full report
        if "report" in order_lower:
            report = self.tools.execute("economy_report")["result"]
            return (
                f"=== ECONOMY REPORT ({report['mode']}) ===\n"
                f"Opportunities: {report['opportunities_total']}\n"
                f"  DISCOVERED: {report['opportunities_by_status']['DISCOVERED']}\n"
                f"  ANALYSED:   {report['opportunities_by_status']['ANALYSED']}\n"
                f"  TESTING:    {report['opportunities_by_status']['TESTING']}\n"
                f"  VALIDATED:  {report['opportunities_by_status']['VALIDATED']}\n"
                f"  REJECTED:   {report['opportunities_by_status']['REJECTED']}\n"
                f"Total Revenue:  ${report['total_revenue']}\n"
                f"Total Expenses: ${report['total_expenses']}\n"
                f"Total Profit:   ${report['total_profit']}\n"
                f"Active Experiments: {report['active_experiments']}"
            )

        return f"OpportunityAgent received: '{order}'. Try: scan, opportunities, analyse <id>, test <id>, report, mode"

    def _scan_opportunities(self) -> str:
        """Simple simulated opportunity discovery (will be replaced with real research later)."""
        ideas = [
            {
                "name": "AI Research Summary Service",
                "description": "Sell short AI-generated research summaries on trending topics",
                "startup_cost": 30,
                "expected_expenses": 15,
                "expected_revenue": 120,
                "risk": "low",
            },
            {
                "name": "Digital Template Pack",
                "description": "Create and sell Notion / Canva / spreadsheet templates",
                "startup_cost": 20,
                "expected_expenses": 10,
                "expected_revenue": 90,
                "risk": "low",
            },
            {
                "name": "Automated Lead Finder",
                "description": "Simple service that finds potential customers for small businesses",
                "startup_cost": 80,
                "expected_expenses": 40,
                "expected_revenue": 250,
                "risk": "medium",
            },
        ]

        created = []
        for idea in ideas:
            result = self.tools.execute("find_opportunity", **idea)
            if result["success"]:
                created.append(result["result"])

        if not created:
            return "No new opportunities found."

        msg = f"Opportunity scan complete. Found {len(created)} ideas:\n\n"
        for opp in created:
            msg += f"[{opp['id']}] {opp['name']} (Risk: {opp['risk']})\n"
        msg += "\nUse 'analyse <id>' or 'test <id>' next."
        return msg

    def _list_opportunities(self) -> str:
        opps = self.tools.execute("list_opportunities")["result"]
        if not opps:
            return "No opportunities yet. Try 'scan'."

        msg = "Current Opportunities:\n\n"
        for opp in opps:
            msg += f"[{opp['id']}] {opp['name']} — {opp['status']} (Risk: {opp['risk']})\n"
        return msg
