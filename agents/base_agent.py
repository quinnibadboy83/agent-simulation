"""
Base Agent class. All agents inherit from this.
"""

from typing import Dict, Any, Optional
from core.memory import SharedMemory
from core.tools import ToolRegistry


class BaseAgent:
    def __init__(
        self,
        name: str,
        role: str,
        memory: SharedMemory,
        tools: ToolRegistry,
        description: str = "",
    ):
        self.name = name
        self.role = role
        self.memory = memory
        self.tools = tools
        self.description = description
        self.status = "idle"
        self.current_task = None

        self.memory.set_agent_status(self.name, {
            "role": self.role,
            "status": self.status,
            "description": self.description,
        })

    def think(self, input_text: str) -> str:
        input_lower = input_text.lower()

        if "status" in input_lower or "report" in input_lower:
            return self.get_status_report()
        
        if "help" in input_lower:
            return self.get_help()

        return f"{self.name} received: '{input_text}'. Awaiting clearer orders from Boss."

    def get_status_report(self) -> str:
        status = self.memory.get_agent_status(self.name)
        tasks = self.memory.get_tasks(assigned_to=self.name)
        pending = [t for t in tasks if t["status"] == "pending"]
        
        report = f"**{self.name}** ({self.role})\n"
        report += f"Status: {status.get('status', 'unknown')}\n"
        report += f"Pending tasks: {len(pending)}\n"
        if pending:
            report += "Next task: " + pending[0]["title"]
        return report

    def get_help(self) -> str:
        return f"I am {self.name}, the {self.role}. Give me clear orders and I will execute them."

    def execute_tool(self, tool_name: str, **kwargs) -> Dict[str, Any]:
        return self.tools.execute(tool_name, **kwargs)

    def update_status(self, new_status: str):
        self.status = new_status
        self.memory.set_agent_status(self.name, {
            "role": self.role,
            "status": self.status,
            "description": self.description,
        })
        self.memory.log(self.name, f"Status changed to: {new_status}")
