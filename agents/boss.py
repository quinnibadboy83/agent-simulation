"""
Boss Agent - Super Overseer
Supports Module 2 (Economy) + Module 3 (Web Research)
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
            description="The main commander. You control this agent.",
        )
        self.update_status("awaiting_orders")

    def process_command(self, command: str) -> str:
        cmd = command.strip().lower()
        self.memory.log("Boss", f"Received command: {command}")

        # ---------- Basic commands ----------
        if cmd in ["status", "report", "overview"]:
            return self.full_status_report()

        if cmd.startswith("assign ") or cmd.startswith("task "):
            return self._handle_assign(command)

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

        # ---------- Web Research commands ----------
        if cmd.startswith("search ") or cmd.startswith("web "):
            query = command.split(" ", 1)[1] if " " in command else ""
            if not query:
                return "Usage: search <your query>"
            result = self.execute_tool("web_search", query=query, max_results=5)
            if result.get("success"):
                results = result["result"]
                if not results:
                    return "No results found."
                msg = f"Search results for '{query}':\n\n"
                for i, r in enumerate(results, 1):
                    msg += f"{i}. {r['title']}\n   {r['url']}\n   {r['snippet'][:150]}...\n\n"
                return msg
            return f"Search failed: {result.get('error')}"

        if cmd.startswith("read "):
            url = command.split(" ", 1)[1] if " " in command else ""
            if not url.startswith("http"):
                return "Please provide a full URL starting with http"
            result = self.execute_tool("read_webpage", url=url)
            if result.get("success"):
                page = result["result"]
                return f"Page: {page['title']}\n\n{page['content'][:2000]}"
            return f"Failed to read page: {result.get('error')}"

        # ---------- Farm / Research ----------
        if cmd.startswith("farm ") or "research" in cmd:
            topic = command.replace("farm", "").replace("research", "").strip()
            if not topic:
                topic = "general opportunities"
            return self.order_info_farmer(topic)

        # ---------- Money commands ----------
        if cmd.startswith("money") or cmd in ["scan", "opportunities"]:
            return self._handle_money_command(command)

        return self.think(command)

    def _handle_money_command(self, command: str) -> str:
        cmd = command.lower().strip()

        if cmd in ["money", "money help"]:
            return self.get_money_help()

        if "mode" in cmd:
            if "simulation" in cmd:
                result = self.execute_tool("money_mode", mode="simulation")
                return result.get("result", str(result))
            if "real" in cmd:
                result = self.execute_tool("money_mode", mode="real")
                return result.get("result", str(result))
            result = self.execute_tool("money_mode")
            return result.get("result", str(result))

        if "report" in cmd:
            result = self.execute_tool("economy_report")
            if result.get("success"):
                r = result["result"]
                return (
                    f"=== ECONOMY REPORT ({r['mode']}) ===\n"
                    f"Opportunities: {r['opportunities_total']}\n"
                    f"Total Revenue:  ${r['total_revenue']}\n"
                    f"Total Expenses: ${r['total_expenses']}\n"
                    f"Total Profit:   ${r['total_profit']}\n"
                    f"Active Experiments: {r['active_experiments']}"
                )
            return str(result)

        if "opportunities" in cmd or "list" in cmd:
            result = self.execute_tool("list_opportunities")
            if result.get("success"):
                opps = result["result"]
                if not opps:
                    return "No opportunities yet."
                msg = "Current Opportunities:\n"
                for o in opps:
                    msg += f"[{o['id']}] {o['name']} — {o['status']}\n"
                return msg
            return str(result)

        return self.get_money_help()

    def full_status
