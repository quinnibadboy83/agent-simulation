"""
Boss Agent - Super Overseer
---------------------------

The Boss is the primary commander of the agent simulation.

Responsibilities include:

    - receiving Creator commands
    - checking system status
    - assigning tasks
    - requesting research
    - using approved tools
    - managing economy commands
    - drafting content
    - coordinating other agents

The Boss does not bypass ToolRegistry.
All tool execution goes through the central tool gateway.
"""

from typing import Any, Dict

from .base_agent import BaseAgent
from core.memory import SharedMemory
from core.tools import ToolRegistry


class BossAgent(BaseAgent):
    """
    Main commander / overseer agent.
    """

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
    # Command processing
    # ------------------------------------------------------------------

    def process_command(
        self,
        command: str,
    ) -> str:
        command = str(command or "").strip()

        if not command:
            return (
                "Boss is awaiting a command."
            )

        cmd = command.lower()

        self.memory.log(
            "Boss",
            f"Received command: {command}",
        )

        if cmd in [
            "status",
            "report",
            "overview",
        ]:
            return self.full_status_report()

        if (
            cmd.startswith("assign ")
            or cmd.startswith("task ")
        ):
            return self._handle_assign(
                command
            )

        if cmd in [
            "balance",
            "funds",
        ]:
            result = self.execute_tool(
                "check_balance"
            )

            balance = (
                result.get("result", {})
                .get("balance", 0)
            )

            return (
                f"Current balance under Banker: "
                f"${balance:.2f}"
            )

        if cmd in [
            "help",
            "?",
        ]:
            return self.get_command_help()

        if cmd.startswith("say "):
            message = command[4:].strip()

            self.memory.log(
                "Boss",
                f"Announcement: {message}",
            )

            return (
                f"Announcement logged: "
                f"{message}"
            )

        if cmd.startswith("make post"):
            topic = command[9:].strip()

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
            query = (
                command.split(
                    " ",
                    1,
                )[1]
                if " " in command
                else ""
            )

            if not query:
                return (
                    "Usage: search <your query>"
                )

            return self._format_search(
                query
            )

        if cmd.startswith("read "):
            url = (
                command.split(
                    " ",
                    1,
                )[1]
                if " " in command
                else ""
            )

            if not url.startswith(
                "http"
            ):
                return (
                    "Please provide a full URL "
                    "starting with http"
                )

            result = self.execute_tool(
                "read_webpage",
                url=url,
            )

            if result.get("success"):
                page = result.get(
                    "result",
                    {},
                )

                return (
                    f"Page: "
                    f"{page.get('title', '')}\n\n"
                    f"{str(page.get('content', ''))[:2000]}"
                )

            return (
                "Failed to read page: "
                f"{result.get('error')}"
            )

        if (
            cmd.startswith("farm ")
            or cmd.startswith("research ")
        ):
            topic = (
                command.split(
                    " ",
                    1,
                )[1].strip()
            )

            if not topic:
                topic = (
                    "general opportunities"
                )

            return self.order_info_farmer(
                topic
            )

        if (
            cmd.startswith("money")
            or cmd in [
                "scan",
                "opportunities",
            ]
        ):
            return self._handle_money_command(
                command
            )

        return self.think(
            command
        )

    # ------------------------------------------------------------------
    # Cognitive response
    # ------------------------------------------------------------------

    def think(
        self,
        command: str,
    ) -> str:
        """
        Send general reasoning requests to the configured brain.

        The brain response does not directly execute tools.
        """

        try:
            from core.brain import ask_brain

            result = ask_brain(
                command
            )

            self.remember(
                f"Brain response: {result}",
                category="reasoning",
            )

            return str(
                result
            )

        except Exception as exc:
            self.memory.log(
                "Boss",
                f"Brain request failed: {exc}",
                level="error",
            )

            return (
                "The reasoning system is currently "
                f"unavailable: {exc}"
            )

    # ------------------------------------------------------------------
    # Content
    # ------------------------------------------------------------------

    def make_post(
        self,
        topic: str,
    ) -> str:
        """
        Create a content draft.

        This does NOT publish anything externally.
        """

        search = self.execute_tool(
            "web_search",
            query=topic,
            max_results=3,
        )

        points = []

        if search.get("success"):
            for item in (
                search.get(
                    "result",
                    [],
                )[:3]
            ):
                title = item.get(
                    "title",
                    "",
                )

                snippet = item.get(
                    "snippet",
                    "",
                )

                if (
                    title
                    and title != "Error"
                ):
                    points.append(
                        f"- {title}: "
                        f"{snippet[:140]}"
                    )

        if not points:
            points = [
                f"- Simple idea about {topic}"
            ]

        caption = (
            f"{topic.title()} in plain words.\n\n"
            f"3 things worth knowing:\n"
            + "\n".join(points)
            + "\n\n"
            "Save this if it is useful. "
            "What would you add?"
        )

        image_prompt = (
            f"Clean mobile-friendly graphic about "
            f"{topic}, simple icons, dark green "
            "and amber colours, no tiny text"
        )

        self.memory.add_knowledge(
            source="Boss",
            content=(
                f"Draft post about {topic}\n"
                f"{caption}"
            ),
            tags=[
                "content",
                "draft",
                topic.lower(),
            ],
        )

        self.memory.log(
            "Boss",
            f"Drafted post about {topic}",
        )

        return (
            "CONTENT DRAFT\n"
            f"Topic: {topic}\n\n"
            f"CAPTION\n{caption}\n\n"
            f"IMAGE IDEA\n{image_prompt}\n\n"
            "Nothing has been posted. "
            "Copy the caption, make the image, "
            "then post it yourself."
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

        if not result.get("success"):
            return (
                f"Search failed: "
                f"{result.get('error')}"
            )

        results = result.get(
            "result",
            [],
        )

        if not results:
            return (
                "No results found."
            )

        message = (
            f"Search results for "
            f"'{query}':\n\n"
        )

        for index, item in enumerate(
            results,
            1,
        ):
            message += (
                f"{index}. "
                f"{item.get('title', '')}\n"
                f"   {item.get('url', '')}\n"
                f"   {item.get('snippet', '')[:150]}"
                "\n\n"
            )

        return message

    # ------------------------------------------------------------------
    # Economy
    # ------------------------------------------------------------------

    def _handle_money_command(
        self,
        command: str,
    ) -> str:
        cmd = (
            command
            .lower()
            .strip()
        )

        if cmd in [
            "money",
            "money help",
        ]:
            return self.get_money_help()

        if "mode" in cmd:

            if "simulation" in cmd:
                result = self.execute_tool(
                    "money_mode",
                    mode="simulation",
                )

                return result.get(
                    "result",
                    str(result),
                )

            if "real" in cmd:
                result = self.execute_tool(
                    "money_mode",
                    mode="real",
                )

                return result.get(
                    "result",
                    str(result),
                )

            result = self.execute_tool(
                "money_mode"
            )

            return result.get(
                "result",
                str(result),
            )

        if "report" in cmd:
            result = self.execute_tool(
                "economy_report"
            )

            if result.get("success"):
                report = result.get(
                    "result",
                    {},
                )

                return (
                    f"=== ECONOMY REPORT "
                    f"({report.get('mode', 'unknown')}) "
                    "===\n"
                    f"Opportunities: "
                    f"{report.get('opportunities_total', 0)}\n"
                    f"Total Revenue:  "
                    f"${report.get('total_revenue', 0)}\n"
                    f"Total Expenses: "
                    f"${report.get('total_expenses', 0)}\n"
                    f"Total Profit:   "
                    f"${report.get('total_profit', 0)}\n"
                    f"Active Experiments: "
                    f"{report.get('active_experiments', 0)}"
                )

            return str(
                result
            )

        if (
            "opportunities" in cmd
            or "list" in cmd
        ):
            result = self.execute_tool(
                "list_opportunities"
            )

            if result.get("success"):
                opportunities = result.get(
                    "result",
                    [],
                )

                if not opportunities:
                    return (
                        "No opportunities yet."
                    )

                message = (
                    "Current Opportunities:\n"
                )

                for opportunity in opportunities:
                    message += (
                        f"[{opportunity['id']}] "
                        f"{opportunity['name']} "
                        f"— {opportunity['status']}\n"
                    )

                return message

            return str(
                result
            )

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

        pending = [
            task
            for task in self.memory.get_tasks()
            if task.get("status") == "pending"
        ]

        balance = self.memory.get_balance(
            "Banker"
        )

        knowledge_count = len(
            self.memory.data.get(
                "knowledge",
                [],
            )
        )

        report = (
            "=== BOSS STATUS REPORT ===\n\n"
        )

        report += (
            f"Bank Balance: "
            f"${balance:.2f}\n"
        )

        report += (
            f"Knowledge entries: "
            f"{knowledge_count}\n"
        )

        report += (
            f"Pending tasks: "
            f"{len(pending)}\n\n"
        )

        report += "Agents:\n"

        for name, info in agents.items():
            report += (
                f"  - {name} "
                f"({info.get('role')}) "
                f"- {info.get('status')}\n"
            )

        return report

    # ------------------------------------------------------------------
    # InfoFarmer
    # ------------------------------------------------------------------

    def order_info_farmer(
        self,
        topic: str,
    ) -> str:
        task = self.memory.add_task(
            title=(
                f"Farm info: {topic}"
            ),
            description=(
                f"Gather useful information "
                f"about: {topic}"
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
            notes="Auto-executed",
        )

        return (
            f"Ordered InfoFarmer to research "
            f"'{topic}'.\n"
            f"Result: "
            f"{result.get('result', result)}"
        )

    # ------------------------------------------------------------------
    # Task assignment
    # ------------------------------------------------------------------

    def _handle_assign(
        self,
        command: str,
    ) -> str:
        parts = command.split()

        if len(parts) < 3:
            return (
                "Usage: assign "
                "<AgentName> "
                "<task description>"
            )

        agent_name = parts[1]

        task_description = " ".join(
            parts[2:]
        )

        task = self.memory.add_task(
            title=task_description[:50],
            description=task_description,
            assigned_to=agent_name,
            created_by="Boss",
        )

        return (
            f"Task created and assigned "
            f"to {agent_name}:\n"
            f"[{task['id']}] "
            f"{task['title']}"
        )

    # ------------------------------------------------------------------
    # Help
    # ------------------------------------------------------------------

    def get_command_help(
        self,
    ) -> str:
        return """
status                  -> System overview
help                    -> This help
search <query>          -> Search the public web
read <url>              -> Read a public page
make post about <topic> -> Draft content, do not publish it
money mode              -> Show economy mode
money report            -> Economy summary
farm <topic>            -> InfoFarmer research
assign <agent> <task>   -> Assign a task
Anything else           -> Brain reasoning
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
money list
"""
