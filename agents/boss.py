"""
Boss Agent - The Super Boss you control.
"""

from typing import Dict, Any
from .base_agent import BaseAgent
from core.memory import SharedMemory
from core.tools import ToolRegistry


class BossAgent(BaseAgent):
    def __init__(self, memory: SharedMemory, tools: ToolRegistry):
        super().__init__(
            name="Boss",
            role="Super Overseer",
            memory=memory,
            tools=tools,
            description="The main commander. You control this agent. Issues orders and keeps everyone in line.",
        )
        self.update_status("awaiting_orders")

    def process_command(self, command: str) -> str:
        cmd = command.strip().lower()
        self.memory.log("Boss", f"Received command: {command}")

        if cmd in ["status", "report", "overview"]:
            return self.full_status_report()

        if cmd.startswith("assign ") or cmd.startswith("task "):
            return self._handle_assign(command)

        if cmd.startswith("farm ") or "research" in cmd:
            topic = command.replace("farm", "").replace("research", "").strip()
            if not topic:
                topic = "general opportunities"
            return self.order_info_farmer(topic)

        if cmd in ["balance", "money", "funds"]:
            result = self.execute_tool("check_balance")
            balance = result.get("result", {}).get("balance", 0)
            return f"Current balance under Banker: ${balance:.2f}"

        if cmd in ["help", "?"]:
            return self.get_command_help()

        if cmd.startswith("say "):
            message = command[4:].strip()
            self.memory.log("Boss", f"Announcement: {message}")
            return f"Announcement logged: {message}"

        return self.think(command)

    def full_status_report(self) -> str:
        agents = self.memory.get_all_agent_status()
        tasks = self.memory.get_tasks()
        pending = [t for t in tasks if t["status"] == "pending"]
        balance = self.memory.get_balance("Banker")
        knowledge_count = len(self.memory.data.get("knowledge", []))

        report = "=== BOSS STATUS REPORT ===\n\n"
        report += f"Bank Balance: ${balance:.2f}\n"
        report += f"Knowledge entries: {knowledge_count}\n"
        report += f"Pending tasks: {len(pending)}\n\n"

        report += "Agents:\n"
        for name, info in agents.items():
            report += f"  • {name} ({info.get('role')}) - {info.get('status')}\n"

        if pending:
            report += "\nActive Orders:\n"
            for t in pending[:5]:
                report += f"  • [{t['id']}] {t['title']} → {t['assigned_to']}\n"

        return report

    def order_info_farmer(self, topic: str) -> str:
        task = self.memory.add_task(
            title=f"Farm info: {topic}",
            description=f"Gather useful information about: {topic}",
            assigned_to="InfoFarmer",
            created_by="Boss",
        )
        result = self.execute_tool("farm_info", topic=topic, agent="InfoFarmer")
        self.memory.update_task(task["id"], "completed", notes="Auto-executed basic farm")
        
        return f"Ordered InfoFarmer to research '{topic}'.\nResult: {result.get('result', result)}"

    def _handle_assign(self, command: str) -> str:
        parts = command.split()
        if len(parts) < 3:
            return "Usage: assign <AgentName> <task description>"
        
        agent_name = parts[1]
        task_desc = " ".join(parts[2:])
        
        task = self.memory.add_task(
            title=task_desc[:50],
            description=task_desc,
            assigned_to=agent_name,
            created_by="Boss",
        )
        return f"Task created and assigned to {agent_name}:\n[{task['id']}] {task['title']}"

    def get_command_help(self) -> str:
        return """
=== BOSS COMMANDS ===

status / report     → Full overview
balance / money     → Check funds
farm <topic>        → Order InfoFarmer to research something
assign <Agent> <task> → Create a task for an agent
say <message>       → Make an announcement
help                → Show this help
"""
