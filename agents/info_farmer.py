"""
InfoFarmer Agent
----------------

Responsible for researching, collecting and storing useful
information for the rest of the agent system.

The InfoFarmer can operate autonomously in simulation mode
and can use public research tools when they are registered.
"""

from .base_agent import BaseAgent
from core.memory import SharedMemory
from core.tools import ToolRegistry


class InfoFarmerAgent(BaseAgent):

    def __init__(
        self,
        memory: SharedMemory,
        tools: ToolRegistry,
    ):
        super().__init__(
            name="InfoFarmer",
            role="Information Specialist",
            memory=memory,
            tools=tools,
            description=(
                "Researches useful information, "
                "stores knowledge and supplies "
                "other agents with relevant findings."
            ),
        )

        self.update_status("ready")

    # ------------------------------------------------------------------
    # Orders
    # ------------------------------------------------------------------

    def process_order(
        self,
        order: str,
    ) -> str:

        self.memory.log(
            "InfoFarmer",
            f"Received order: {order}",
        )

        order_text = order.strip()

        if not order_text:
            return (
                "InfoFarmer needs a research topic."
            )

        order_lower = order_text.lower()

        # --------------------------------------------------------------
        # Direct web research
        # --------------------------------------------------------------

        if (
            "web search" in order_lower
            or "search web" in order_lower
            or "search the web" in order_lower
        ):
            query = self._extract_topic(
                order_text,
                [
                    "web search",
                    "search web",
                    "search the web",
                ],
            )

            if not query:
                return (
                    "Please provide a search topic."
                )

            result = self.execute_tool(
                "web_search",
                query=query,
            )

            return self._format_research_result(
                result
            )

        # --------------------------------------------------------------
        # Read webpage
        # --------------------------------------------------------------

        if (
            order_lower.startswith("read ")
            and (
                "http://" in order_lower
                or "https://" in order_lower
            )
        ):
            url = order_text[5:].strip()

            result = self.execute_tool(
                "read_webpage",
                url=url,
            )

            return self._format_research_result(
                result
            )

        # --------------------------------------------------------------
        # Basic farming
        # --------------------------------------------------------------

        topic = self._extract_topic(
            order_text,
            [
                "farm",
                "research",
                "find",
                "gather",
                "info",
                "information",
                "about",
                "on",
                "search",
            ],
        )

        if not topic:
            topic = (
                "general market opportunities"
            )

        result = self.execute_tool(
            "farm_info",
            topic=topic,
        )

        if not result.get("success"):
            return (
                "InfoFarmer failed: "
                + str(
                    result.get(
                        "error",
                        "Unknown error.",
                    )
                )
            )

        entry = result.get(
            "result",
            {},
        )

        if not isinstance(entry, dict):
            return (
                "InfoFarmer completed the task "
                "but received an unexpected result."
            )

        entry_id = entry.get(
            "id",
            "?",
        )

        content = entry.get(
            "content",
            "No content recorded.",
        )

        return (
            "InfoFarmer completed task.\n"
            f"Farmed knowledge #{entry_id}:\n"
            f"{content}"
        )

    # ------------------------------------------------------------------
    # Topic extraction
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_topic(
        text: str,
        prefixes,
    ) -> str:

        topic = text.strip()

        lowered = topic.lower()

        # Remove the longest phrases first so that
        # "search the web" is not partially reduced
        # by "search".
        ordered = sorted(
            prefixes,
            key=len,
            reverse=True,
        )

        for prefix in ordered:
            prefix_lower = prefix.lower()

            if lowered.startswith(
                prefix_lower
            ):
                topic = topic[
                    len(prefix):
                ].strip()

                lowered = topic.lower()

        # Remove common leading connector words.
        while True:
            changed = False

            for word in (
                "for",
                "about",
                "on",
                "into",
                "regarding",
            ):
                prefix = word + " "

                if topic.lower().startswith(
                    prefix
                ):
                    topic = topic[
                        len(prefix):
                    ].strip()

                    changed = True
                    break

            if not changed:
                break

        return topic.strip(
            " :,-"
        )

    # ------------------------------------------------------------------
    # Research result formatting
    # ------------------------------------------------------------------

    @staticmethod
    def _format_research_result(
        result,
    ) -> str:

        if not result.get("success"):
            return (
                "Research failed: "
                + str(
                    result.get(
                        "error",
                        "Unknown error.",
                    )
                )
            )

        payload = result.get(
            "result"
        )

        if payload is None:
            return (
                "Research completed, "
                "but returned no data."
            )

        return (
            "Research completed.\n\n"
            + str(payload)
        )
