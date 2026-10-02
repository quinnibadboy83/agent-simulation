"""
Base Tool System.
"""

from typing import Dict, Any, Callable, Optional
from .memory import SharedMemory


class ToolRegistry:
    def __init__(self, memory: SharedMemory):
        self.memory = memory
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
            {"name": t["name"], "description": t["description"], "requires_approval": t["requires_approval"]}
            for t in self.tools.values()
        ]

    def execute(self, name: str, **kwargs) -> Dict[str, Any]:
        tool = self.get_tool(name)
        if not tool:
            return {"success": False, "error": f"Tool '{name}' not found"}
        
        try:
            result = tool["func"](**kwargs)
            self.memory.log("ToolSystem", f"Executed tool: {name}")
            return {"success": True, "result": result}
        except Exception as e:
            self.memory.log("ToolSystem", f"Tool {name} failed: {str(e)}", level="error")
            return {"success": False, "error": str(e)}


def create_default_tools(memory: SharedMemory, world) -> ToolRegistry:
    registry = ToolRegistry(memory)

    def log_message(agent: str, message: str):
        memory.log(agent, message)
        return f"Logged: {message}"

    def farm_info(topic: str, agent: str = "InfoFarmer"):
        content = f"Gathered basic information about '{topic}'. (Real web tools coming in next module)"
        entry = memory.add_knowledge(source=agent, content=content, tags=[topic.lower(), "farmed"])
        world.add_resource("info_points", 5)
        memory.log(agent, f"Farmed info on: {topic}")
        return entry

    def check_balance():
        return {"balance": memory.get_balance("Banker")}

    def create_task(title: str, description: str, assigned_to: str):
        return memory.add_task(title, description, assigned_to)

    registry.register("log", "Write a log message", log_message)
    registry.register("farm_info", "Farm information on a topic (simulated for now)", farm_info)
    registry.register("check_balance", "Check current money balance", check_balance)
    registry.register("create_task", "Create a new task for an agent", create_task)

    return registry
