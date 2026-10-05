"""
Boss Agent
----------

Primary commander of the agent simulation.

The Boss:

    - receives Creator commands
    - coordinates other agents
    - performs research
    - manages tasks
    - monitors the economy
    - creates content drafts
    - uses the central ToolRegistry
"""

from .base_agent import BaseAgent
from core.memory import SharedMemory
from core.tools import ToolRegistry


class BossAgent(BaseAgent):

    def __init__(
        self,
        memory: SharedMemory,
        tools: ToolRegistry,
    ):
        super().__init__(
            name="Boss",
            role="Super Overseer",
            memory=memory,
            tools=tools,
            description=(
                "The main commander. "
                "You control this agent."
            ),
        )

        self.update_status(
            "awaiting_orders"
        )

    # ------------------------------------------------------------------
    # Commands
    # ------------------------------------------------------------------

    def process_command(
        self,
        command: str,
    ) -> str:

        command = str(
            command or ""
        ).strip()

        if not command:
            return (
                "Boss is awaiting a command."
            )

        cmd = command.lower()

        self.memory.log(
            "Boss",
            f"Received command: {command}",
        )

        if cmd in {
            "status",
            "report",
            "overview",
        }:
            return self.full_status_report()

        if (
            cmd.startswith("assign ")
            or cmd.startswith("task ")
        ):
            return self._handle_assign(
                command
            )

        if cmd in {
            "balance",
            "funds",
        }:
            result = self.execute_tool(
                "check_balance"
            )

            balance = result.get(
                "result",
                {},
            ).get(
                "balance",
                0,
            )

            return (
                f"Current balance: "
                f"${balance:.2f}"
            )

        if cmd in {
            "help",
            "?",
        }:
            return self.get_command_help()

        if cmd.startswith(
            "say "
        ):
            message = command[
                4:
            ].strip()

            self.memory.log(
                "Boss",
                f"Announcement: {message}",
            )

            return (
                f"Announcement logged: "
                f"{message}"
            )

        if cmd.startswith(
            "make post"
        ):
            topic = command[
                9:
            ].strip()

            topic = topic.replace(
                "about",
                "",
                1,
            ).strip()

            if not topic:
                return (
                    "Usage: make post about <topic>"
                )

            return self.make_post(
                topic
            )

        if (
            cmd.startswith("search ")
            or cmd.startswith("web ")
        ):
            query = command.split(
                " ",
                1,
            )[1]

            return self._format_search(
                query
            )

        if cmd.startswith(
            "read "
        ):
            url = command.split(
                " ",
                1,
            )[1]

            if not url.startswith(
                "http"
            ):
                return (
                    "Please provide a full URL "
                    "starting with http."
                )

            result = self.execute_tool(
                "read_webpage",
                url=url,
            )

            if not result.get(
                "success"
            ):
                return (
                    "Failed to read page: "
                    f"{result.get('error')}"
                )

            page = result.get(
                "result",
                {},
            )

            return (
                f"Page: "
                f"{page.get('title', '')}\n\n"
                f"{str(page.get('content', ''))[:2500]}"
            )

        if (
            cmd.startswith("farm ")
            or cmd.startswith("research ")
        ):
            topic = command.split(
                " ",
                1,
            )[1].strip()

            return self.order_info_farmer(
                topic
            )

        if (
            cmd.startswith("money")
            or cmd in {
                "scan",
                "opportunities",
            }
        ):
            return self._handle_money_command(
                command
            )

        return self._brain_reason(
            command
        )

    # ------------------------------------------------------------------
    # Brain
    # ------------------------------------------------------------------

    def _brain_reason(
        self,
        command: str,
    ) -> str:

        try:
            from core.brain import ask_brain

            result = ask_brain(
                command
            )

            self.remember(
                str(result),
                "reasoning",
            )

            return str(
                result
            )

        except Exception as exc:
            self.memory.log(
                "Boss",
                f"Brain unavailable: {exc}",
                level="warning",
            )

            return (
                f"Boss received: '{command}'.\n"
                "No external brain is currently "
                "configured, so no autonomous "
                "LLM reasoning was performed."
            )

    # ------------------------------------------------------------------
    # Content
    # ------------------------------------------------------------------

    def make_post(
        self,
        topic: str,
    ) -> str:

        result = self.execute_tool(
            "web_search",
            query=topic,
            max_results=3,
        )

        points = []

        if result.get(
            "success"
        ):
            for item in result.get(
                "result",
                [],
            )[:3]:

                title = item.get(
                    "title",
                    "",
                )

                snippet = item.get(
                    "snippet",
                    "",
                )

                if title:
                    points.append(
                        f"- {title}: "
                        f"{snippet[:160]}"
                    )

        if not points:
            points.append(
                f"- Research point about {topic}"
            )

        caption = (
            f"{topic.title()}\n\n"
            "A few useful points:\n"
            + "\n".join(points)
            + "\n\n"
            "This is a draft only. "
            "Nothing has been published."
        )

        self.memory.add_knowledge(
            source="Boss",
            content=caption,
            tags=[
                "content",
                "draft",
                topic.lower(),
            ],
        )

        return (
            "CONTENT DRAFT\n\n"
            f"{caption}"
        )

    # ------------------------------------------------------------------
    # Research
    # ------------------------------------------------------------------

    def _format_search(
        self,
        query: str,
    ) -> str:

        result = self.execute_tool(
            "web_search",
            query=query,
            max_results=5,
        )

        if not result.get(
            "success"
        ):
            return (
                "Search failed: "
                f"{result.get('error')}"
            )

        results = result.get(
            "result",
            [],
        )

        if not results:
            return (
                "No search results found."
            )

        response = (
            f"Search results for "
            f"'{query}':\n\n"
        )

        for index, item in enumerate(
            results,
            1,
        ):
            response += (
                f"{index}. "
                f"{item.get('title', '')}\n"
                f"   {item.get('url', '')}\n"
                f"   {item.get('snippet', '')[:180]}\n\n"
            )

        return response

    # ------------------------------------------------------------------
    # Economy
    # ------------------------------------------------------------------

    def _handle_money_command(
        self,
        command: str,
    ) -> str:

        cmd = command.lower().strip()

        if cmd in {
            "money",
            "money help",
        }:
            return self.get_money_help()

        if "mode" in cmd:

            if "simulation" in cmd:
                result = self.execute_tool(
                    "money_mode",
                    mode="simulation",
                )

            elif "real" in cmd:
                result = self.execute_tool(
                    "money_mode",
                    mode="real",
                )

            else:
                result = self.execute_tool(
                    "money_mode"
                )

            return str(
                result.get(
                    "result",
                    result,
                )
            )

        if "report" in cmd:

            result = self.execute_tool(
                "economy_report"
            )

            if not result.get(
                "success"
            ):
                return str(
                    result
                )

            report = result[
                "result"
            ]

            return (
                f"=== ECONOMY REPORT "
                f"({report['mode']}) ===\n"
                f"Opportunities: "
                f"{report['opportunities_total']}\n"
                f"Total Revenue: "
                f"${report['total_revenue']}\n"
                f"Total Expenses: "
                f"${report['total_expenses']}\n"
                f"Total Profit: "
                f"${report['total_profit']}\n"
                f"Active Experiments: "
                f"{report['active_experiments']}"
            )

        if (
            "opportunities" in cmd
            or "list" in cmd
        ):
            result = self.execute_tool(
                "list_opportunities"
            )

            if not result.get(
                "success"
            ):
                return str(
                    result
                )

            opportunities = result[
                "result"
            ]

            if not opportunities:
                return (
                    "No opportunities yet."
                )

            response = (
                "Current Opportunities:\n\n"
            )

            for opportunity in opportunities:
                response += (
                    f"[{opportunity['id']}] "
                    f"{opportunity['name']} "
                    f"— {opportunity['status']}\n"
                )

            return response

        return self.get_money_help()

    # ------------------------------------------------------------------
    # Status
    # ------------------------------------------------------------------

    def full_status_report(
        self,
    ) -> str:

        agents = (
            self.memory.get_all_agent_status()
        )

        pending = self.memory.get_tasks(
            status="pending"
        )

        balance = (
            self.memory.get_balance(
                "Banker"
            )
        )

        knowledge = len(
            self.memory.data.get(
                "knowledge",
                [],
            )
        )

        response = (
            "=== BOSS STATUS REPORT ===\n\n"
            f"Bank Balance: ${balance:.2f}\n"
            f"Knowledge entries: {knowledge}\n"
            f"Pending tasks: {len(pending)}\n\n"
            "Agents:\n"
        )

        for name, info in agents.items():
            response += (
                f"  - {name}: "
                f"{info.get('status', 'unknown')}\n"
            )

        return response

    # ------------------------------------------------------------------
    # InfoFarmer
    # ------------------------------------------------------------------

    def order_info_farmer(
        self,
        topic: str,
    ) -> str:

        task = self.memory.add_task(
            title=f"Farm info: {topic}",
            description=(
                f"Gather useful information "
                f"about {topic}"
            ),
            assigned_to="InfoFarmer",
            created_by="Boss",
        )

        result = self.execute_tool(
            "farm_info",
            topic=topic,
            agent="InfoFarmer",
        )

        self.memory.update_task(
            task["id"],
            "completed",
            "Research executed.",
        )

        if result.get(
            "success"
        ):
            return (
                f"InfoFarmer research completed "
                f"for '{topic}'."
            )

        return (
            "InfoFarmer research failed: "
            f"{result.get('error')}"
        )

    # ------------------------------------------------------------------
    # Tasks
    # ------------------------------------------------------------------

    def _handle_assign(
        self,
        command: str,
    ) -> str:

        parts = command.split()

        if len(parts) < 3:
            return (
                "Usage: assign "
                "<agent> <task>"
            )

        agent_name = parts[1]
        description = " ".join(
            parts[2:]
        )

        task = self.memory.add_task(
            title=description[:60],
            description=description,
            assigned_to=agent_name,
            created_by="Boss",
        )

        return (
            f"Task #{task['id']} assigned "
            f"to {agent_name}."
        )

    # ------------------------------------------------------------------
    # Help
    # ------------------------------------------------------------------

    def get_command_help(
        self,
    ) -> str:
        return """
status
report
balance
help
search <query>
read <url>
make post about <topic>
farm <topic>
research <topic>
assign <agent> <task>
money mode
money mode simulation
money mode real
money report
money opportunities
"""
    
    def get_money_help(
        self,
    ) -> str:
        return """
money mode
money mode simulation
money mode real
money report
money opportunities
"""
