"""
InfoFarmer Agent
----------------
Research and information-gathering specialist.

The InfoFarmer can autonomously perform read-only research through the
registered research tools. It does not perform consequential external
actions.
"""

from typing import Any, Dict

from .base_agent import BaseAgent


class InfoFarmer(BaseAgent):
    def __init__(self, memory, tools):
        super().__init__(
            name="InfoFarmer",
            role="Research and Intelligence",
            memory=memory,
            tools=tools,
            description=(
                "Researches public information, gathers useful knowledge, "
                "summarises findings, and feeds intelligence back into "
                "shared memory."
            ),
        )

    def process_order(self, order: str) -> Dict[str, Any]:
        command = (order or "").strip()

        if not command:
            return {
                "status": "error",
                "agent": self.name,
                "message": "No research order supplied.",
            }

        lowered = command.lower()

        if lowered in {"help", "?", "commands"}:
            return self.get_help()

        if lowered.startswith("search "):
            query = command[7:].strip()

            if not query:
                return {
                    "status": "error",
                    "agent": self.name,
                    "message": "Search query is required.",
                }

            return self.execute_tool(
                "web_search",
                query=query,
            )

        if lowered.startswith("research "):
            query = command[9:].strip()

            if not query:
                return {
                    "status": "error",
                    "agent": self.name,
                    "message": "Research topic is required.",
                }

            result = self.execute_tool(
                "web_search",
                query=query,
            )

            self.observe_result(result)

            return {
                "status": "success",
                "agent": self.name,
                "operation": "research",
                "query": query,
                "result": result,
            }

        if lowered.startswith("read "):
            url = command[5:].strip()

            if not url:
                return {
                    "status": "error",
                    "agent": self.name,
                    "message": "URL is required.",
                }

            return self.execute_tool(
                "read_webpage",
                url=url,
            )

        if lowered.startswith("open "):
            url = command[5:].strip()

            if not url:
                return {
                    "status": "error",
                    "agent": self.name,
                    "message": "URL is required.",
                }

            return self.execute_tool(
                "read_webpage",
                url=url,
            )

        if lowered.startswith("farm "):
            topic = command[5:].strip()

            if not topic:
                return {
                    "status": "error",
                    "agent": self.name,
                    "message": "Information topic is required.",
                }

            return self.execute_tool(
                "farm_info",
                topic=topic,
            )

        if lowered.startswith("find information about "):
            topic = command[len("find information about "):].strip()

            if not topic:
                return {
                    "status": "error",
                    "agent": self.name,
                    "message": "Information topic is required.",
                }

            return self.execute_tool(
                "farm_info",
                topic=topic,
            )

        if lowered.startswith("find info about "):
            topic = command[len("find info about "):].strip()

            if not topic:
                return {
                    "status": "error",
                    "agent": self.name,
                    "message": "Information topic is required.",
                }

            return self.execute_tool(
                "farm_info",
                topic=topic,
            )

        if lowered in {"status", "agent status"}:
            return self.get_status_report()

        if lowered in {"run", "cycle", "run cycle"}:
            return self.run_cycle()

        return {
            "status": "error",
            "agent": self.name,
            "message": f"Unknown InfoFarmer command: {command}",
            "help": self.get_help(),
        }

    def research(self, query: str) -> Dict[str, Any]:
        result = self.execute_tool(
            "web_search",
            query=query,
        )

        self.observe_result(result)

        return result

    def read_url(self, url: str) -> Dict[str, Any]:
        result = self.execute_tool(
            "read_webpage",
            url=url,
        )

        self.observe_result(result)

        return result

    def farm_information(self, topic: str) -> Dict[str, Any]:
        result = self.execute_tool(
            "farm_info",
            topic=topic,
        )

        self.observe_result(result)

        return result

    def get_help(self) -> Dict[str, Any]:
        return {
            "status": "success",
            "agent": self.name,
            "role": self.role,
            "commands": [
                "search <query>",
                "research <topic>",
                "read <url>",
                "open <url>",
                "farm <topic>",
                "find information about <topic>",
                "status",
                "run",
                "help",
            ],
            "capabilities": [
                "Public web research",
                "Webpage reading",
                "Information farming",
                "Knowledge gathering",
                "Shared-memory intelligence",
            ],
            "safety": (
                "InfoFarmer performs read-only research and cannot "
                "independently perform consequential external actions."
            ),
        }
