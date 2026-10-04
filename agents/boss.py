"""
Boss Agent - Super Overseer
Supports economy, web research, and content drafts.
"""

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

        if cmd in ["status", "report", "overview"]:
            return self.full_status_report()

        if cmd.startswith("assign ") or cmd.startswith("task "):
            return self._handle_assign(command)

        if cmd in ["balance", "funds"]:
            result = self.execute_tool("check_balance")
            balance = result.get("result", {}).get("balance", 0)
            return f"Current balance under Banker: ${balance:.2f}"

        if cmd in ["help", "?"]:
            return self.get_command_help()

        if cmd.startswith("say "):
            message = command[4:].strip()
            self.memory.log("Boss", f"Announcement: {message}")
            return f"Announcement logged: {message}"

        if cmd.startswith("make post"):
            topic = command[9:].strip()
            topic = topic.replace("about", "", 1).strip()
            if not topic:
                return "Usage: make post about <topic>"
            return self.make_post(topic)

        if cmd.startswith("search ") or cmd.startswith("web "):
            query = command.split(" ", 1)[1] if " " in command else ""
            if not query:
                return "Usage: search <your query>"
            return self._format_search(query)

        if cmd.startswith("read "):
            url = command.split(" ", 1)[1] if " " in command else ""
            if not url.startswith("http"):
                return "Please provide a full URL starting with http"
            result = self.execute_tool("read_webpage", url=url)
            if result.get("success"):
                page = result["result"]
                return f"Page: {page.get('title')}\n\n{str(page.get('content', ''))[:2000]}"
            return f"Failed to read page: {result.get('error')}"

        if cmd.startswith("farm ") or cmd.startswith("research "):
            topic = command.split(" ", 1)[1].strip()
            if not topic:
                topic = "general opportunities"
            return self.order_info_farmer(topic)

        if cmd.startswith("money") or cmd in ["scan", "opportunities"]:
            return self._handle_money_command(command)

        return self.think(command)

    def make_post(self, topic: str) -> str:
        search = self.execute_tool("web_search", query=topic, max_results=3)
        points = []
        if search.get("success"):
            for item in search.get("result", [])[:3]:
                title = item.get("title", "")
                snippet = item.get("snippet", "")
                if title and title != "Error":
                    points.append(f"- {title}: {snippet[:140]}")

        if not points:
            points = [f"- Simple idea about {topic}"]

        caption = (
            f"{topic.title()} in plain words.\n\n"
            f"3 things worth knowing:\n"
            + "\n".join(points)
            + "\n\nSave this if it is useful. What would you add?"
        )
        image_prompt = (
            f"Clean mobile-friendly graphic about {topic}, "
            "simple icons, dark green and amber colours, no tiny text"
        )

        self.memory.add_knowledge(
            source="Boss",
            content=f"Draft post about {topic}\n{caption}",
            tags=["content", "draft", topic.lower()],
        )
        self.memory.log("Boss", f"Drafted post about {topic}")

        return (
            f"CONTENT DRAFT\n"
            f"Topic: {topic}\n\n"
            f"CAPTION\n{caption}\n\n"
            f"IMAGE IDEA\n{image_prompt}\n\n"
            f"Nothing has been posted. Copy the caption, make the image, then post it yourself."
        )

    def _format_search(self, query: str) -> str:
        result = self.execute_tool("web_search", query=query, max_results=5)
        if not result.get("success"):
            return f"Search failed: {result.get('error')}"
        results = result.get("result", [])
        if not results:
            return "No results found."
        msg = f"Search results for '{query}':\n\n"
        for i, r in enumerate(results, 1):
            msg += f"{i}. {r.get('title', '')}\n   {r.get('url', '')}\n   {r.get('snippet', '')[:150]}\n\n"
        return msg

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

    def full_status_report(self) -> str:
        agents = self.memory.get_all_agent_status()
        pending = [t for t in self.memory.get_tasks() if t["status"] == "pending"]
        balance = self.memory.get_balance("Banker")
        knowledge_count = len(self.memory.data.get("knowledge", []))
        report = "=== BOSS STATUS REPORT ===\n\n"
        report += f"Bank Balance: ${balance:.2f}\n"
        report += f"Knowledge entries: {knowledge_count}\n"
        report += f"Pending tasks: {len(pending)}\n\nAgents:\n"
        for name, info in agents.items():
            report += f"  - {name} ({info.get('role')}) - {info.get('status')}\n"
        return report

    def order_info_farmer(self, topic: str) -> str:
        task = self.memory.add_task(
            title=f"Farm info: {topic}",
            description=f"Gather useful information about: {topic}",
            assigned_to="InfoFarmer",
            created_by="Boss",
        )
        result = self.execute_tool("farm_info", topic=topic, agent="InfoFarmer")
        self.memory.update_task(task["id"], "completed", notes="Auto-executed")
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
status                 -> System overview
help                   -> This help
search <query>         -> Search Wikipedia
read <url>             -> Read a public page
make post about <topic> -> Draft a caption, do not post it
money mode             -> Show economy mode
money report           -> Economy summary
farm <topic>           -> InfoFarmer note
"""

    def get_money_help(self) -> str:
        return self.get_command_help()
