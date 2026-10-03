"""
Base Tool System + Economic Tools + Web Research Tools
"""

from typing import Dict, Any, Callable, Optional
from .memory import SharedMemory
from .economy import Economy
from .research import WebResearch


class ToolRegistry:
    def __init__(self, memory: SharedMemory, economy: Economy = None, research: WebResearch = None):
        self.memory = memory
        self.economy = economy
        self.research = research
        self.tools: Dict[str, Dict[str, Any]] = {}

    def register(self, name: str, description: str, func: Callable, requires_approval: bool = False):
        self.tools[name] = {
            "name": name,
            "description": description,
            "func": func,
            "requires_approval": requires_approval,
        }

    def get_tool(self, name: str) -> Optional[Dict]:
        return self.tools.get(name)

    def list_tools(self) -> list:
        return [
            {
                "name": t["name"],
                "description": t["description"],
                "requires_approval": t["requires_approval"]
            }
            for t in self.tools.values()
        ]

    def execute(self, name: str, **kwargs) -> Dict[str, Any]:
        tool = self.get_tool(name)
        if not tool:
            return {"success": False, "error": f"Tool '{name}' not found"}

        if tool["requires_approval"] and self.economy and self.economy.is_real():
            return {
                "success": False,
                "error": f"Tool '{name}' requires approval in REAL mode."
            }

        try:
            result = tool["func"](**kwargs)
            self.memory.log("ToolSystem", f"Executed tool: {name}")
            return {"success": True, "result": result}
        except Exception as e:
            self.memory.log("ToolSystem", f"Tool {name} failed: {str(e)}", level="error")
            return {"success": False, "error": str(e)}


def create_default_tools(memory: SharedMemory, world, economy: Economy = None, research: WebResearch = None) -> ToolRegistry:
    registry = ToolRegistry(memory, economy, research)

    # ---------- Original tools ----------
    def log_message(agent: str, message: str):
        memory.log(agent, message)
        return f"Logged: {message}"

    def farm_info(topic: str, agent: str = "InfoFarmer"):
        content = f"Gathered basic information about '{topic}'."
        entry = memory.add_knowledge(source=agent, content=content, tags=[topic.lower(), "farmed"])
        world.add_resource("info_points", 5)
        memory.log(agent, f"Farmed info on: {topic}")
        return entry

    def check_balance():
        return {"balance": memory.get_balance("Banker")}

    def create_task(title: str, description: str, assigned_to: str):
        return memory.add_task(title, description, assigned_to)

    registry.register("log", "Write a log message", log_message)
    registry.register("farm_info", "Farm information on a topic", farm_info)
    registry.register("check_balance", "Check current money balance", check_balance)
    registry.register("create_task", "Create a new task for an agent", create_task)

    # ---------- Economic Tools ----------
    if economy:
        def money_mode(mode: str = None):
            if mode is None:
                return f"Current economy mode: {economy.get_mode().upper()}"
            return economy.set_mode(mode)

        def find_opportunity(name: str, description: str, startup_cost: float = 50, expected_expenses: float = 20, expected_revenue: float = 150, risk: str = "medium"):
            return economy.create_opportunity(
                name=name,
                description=description,
                startup_cost=startup_cost,
                expected_expenses=expected_expenses,
                expected_revenue=expected_revenue,
                risk=risk
            )

        def analyse_opportunity(opp_id: int):
            return economy.analyse_opportunity(opp_id)

        def list_opportunities(status: str = None):
            return economy.list_opportunities(status)

        def create_experiment(opp_id: int, budget: float, notes: str = ""):
            return economy.create_experiment(opp_id, budget, notes)

        def complete_experiment(exp_id: int, revenue: float, extra_expenses: float = 0.0, notes: str = ""):
            return economy.complete_experiment(exp_id, revenue, extra_expenses, notes)

        def economy_report():
            return economy.get_economy_report()

        registry.register("money_mode", "Get or set economy mode (simulation/real)", money_mode)
        registry.register("find_opportunity", "Create a new opportunity", find_opportunity)
        registry.register("analyse_opportunity", "Analyse an opportunity by ID", analyse_opportunity)
        registry.register("list_opportunities", "List opportunities", list_opportunities)
        registry.register("create_experiment", "Start an experiment", create_experiment, requires_approval=True)
        registry.register("complete_experiment", "Complete an experiment", complete_experiment, requires_approval=True)
        registry.register("economy_report", "Full economy report", economy_report)

    # ---------- Web Research Tools ----------
    if research:
        def web_search(query: str, max_results: int = 5):
            return research.search(query, max_results)

        def read_webpage(url: str):
            return research.read_page(url)

        registry.register("web_search", "
