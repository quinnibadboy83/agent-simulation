from __future__ import annotations

from typing import Any, Dict, Optional

from .base_agent import BaseAgent


class InfoFarmer(BaseAgent):
    """
    Information-research specialist.

    Handles read-only web research and stores useful findings in shared
    memory. All research operations are simulation-safe and do not perform
    consequential external actions.
    """

    def __init__(
        self,
        memory,
        tools,
        research=None,
        name: str = "InfoFarmer",
        role: str = "Information Research Specialist",
        description: str = (
            "Researches public information, gathers facts, reads webpages, "
            "and returns structured findings to the agent system."
        ),
    ):
        super().__init__(
            name=name,
            role=role,
            memory=memory,
            tools=tools,
            description=description,
        )

        self.research = research

    # ------------------------------------------------------------------
    # Main command interface
    # ------------------------------------------------------------------

    def process_order(self, command: str) -> Dict[str, Any]:
        command = str(command or "").strip()

        if not command:
            return {
                "status": "error",
                "agent": self.name,
                "message": "No research command supplied.",
            }

        lowered = command.lower()

        try:
            if lowered in {"help", "infofarmer help", "research help"}:
                return self.get_help()

            if lowered in {"status", "info status", "research status"}:
                return self.get_status_report()

            if lowered.startswith("search "):
                query = command[7:].strip()
                return self.research_topic(query)

            if lowered.startswith("research "):
                query = command[9:].strip()
                return self.research_topic(query)

            if lowered.startswith("find information about "):
                query = command[len("find information about "):].strip()
                return self.research_topic(query)

            if lowered.startswith("find info about "):
                query = command[len("find info about "):].strip()
                return self.research_topic(query)

            if lowered.startswith("farm "):
                query = command[5:].strip()
                return self.farm_information(query)

            if lowered.startswith("read "):
                url = command[5:].strip()
                return self.read_url(url)

            if lowered.startswith("open "):
                url = command[5:].strip()
                return self.read_url(url)

            if lowered.startswith("run "):
                query = command[4:].strip()
                return self.research_topic(query)

            return self.research_topic(command)

        except Exception as exc:
            self.update_status("error")

            return {
                "status": "error",
                "agent": self.name,
                "message": f"{self.name} failed: {exc}",
                "command": command,
            }

    # ------------------------------------------------------------------
    # Research
    # ------------------------------------------------------------------

    def research_topic(self, query: str) -> Dict[str, Any]:
        query = str(query or "").strip()

        if not query:
            return {
                "status": "error",
                "agent": self.name,
                "message": "Research query is empty.",
            }

        self.update_status("working")

        try:
            # Preferred path: use the WebResearch service directly.
            #
            # This avoids coupling the agent to a particular ToolRegistry
            # calling convention and gives us a stable research interface.
            if self.research is not None:
                result = self.research.research_topic(query)

                normalised = self._normalise_result(
                    result,
                    operation="research",
                    query=query,
                )

                self.remember(
                    f"Research completed for: {query}"
                )

                self.observe(normalised)

                self.update_status("idle")

                return normalised

            # Fallback: use the registered web_search tool.
            result = self._execute_registered_tool(
                "web_search",
                query=query,
            )

            normalised = self._normalise_result(
                result,
                operation="search",
                query=query,
            )

            self.remember(
                f"Web search completed for: {query}"
            )

            self.observe(normalised)

            self.update_status("idle")

            return normalised

        except Exception as exc:
            self.update_status("error")

            return {
                "status": "error",
                "agent": self.name,
                "operation": "research",
                "query": query,
                "message": f"Research failed: {exc}",
            }

    def read_url(self, url: str) -> Dict[str, Any]:
        url = str(url or "").strip()

        if not url:
            return {
                "status": "error",
                "agent": self.name,
                "message": "URL is empty.",
            }

        self.update_status("working")

        try:
            if self.research is not None:
                result = self.research.read_page(url)

                normalised = self._normalise_result(
                    result,
                    operation="read",
                    url=url,
                )

                self.remember(
                    f"Read webpage: {url}"
                )

                self.observe(normalised)

                self.update_status("idle")

                return normalised

            result = self._execute_registered_tool(
                "read_webpage",
                url=url,
            )

            normalised = self._normalise_result(
                result,
                operation="read",
                url=url,
            )

            self.remember(
                f"Read webpage: {url}"
            )

            self.observe(normalised)

            self.update_status("idle")

            return normalised

        except Exception as exc:
            self.update_status("error")

            return {
                "status": "error",
                "agent": self.name,
                "operation": "read",
                "url": url,
                "message": f"Reading webpage failed: {exc}",
            }

    def farm_information(self, query: str) -> Dict[str, Any]:
        """
        Run a broader information-gathering operation.

        This is still read-only. It does not post, purchase, message,
        create accounts, or perform other consequential actions.
        """

        query = str(query or "").strip()

        if not query:
            return {
                "status": "error",
                "agent": self.name,
                "message": "Information-farming query is empty.",
            }

        self.update_status("working")

        try:
            if self.research is not None:
                result = self.research.research_topic(query)

                normalised = self._normalise_result(
                    result,
                    operation="farm",
                    query=query,
                )

                normalised["mode"] = "read_only_information_gathering"

                self.remember(
                    f"Information farming completed for: {query}"
                )

                self.observe(normalised)

                self.update_status("idle")

                return normalised

            search_result = self._execute_registered_tool(
                "web_search",
                query=query,
            )

            normalised = self._normalise_result(
                search_result,
                operation="farm",
                query=query,
            )

            normalised["mode"] = "read_only_information_gathering"

            self.remember(
                f"Information farming completed for: {query}"
            )

            self.observe(normalised)

            self.update_status("idle")

            return normalised

        except Exception as exc:
            self.update_status("error")

            return {
                "status": "error",
                "agent": self.name,
                "operation": "farm",
                "query": query,
                "message": f"Information farming failed: {exc}",
            }

    # ------------------------------------------------------------------
    # ToolRegistry compatibility
    # ------------------------------------------------------------------

    def _execute_registered_tool(
        self,
        tool_name: str,
        **parameters: Any,
    ) -> Any:
        """
        Execute a registered tool while supporting the ToolRegistry
        interface used by this project.

        The current ToolRegistry signature is:

            execute(agent, tool, parameters)

        Older agent code incorrectly called:

            execute(tool, parameters)

        This method always uses the current interface.
        """

        if self.tools is None:
            raise RuntimeError("ToolRegistry is not available.")

        execute = getattr(self.tools, "execute", None)

        if execute is None:
            raise RuntimeError(
                "ToolRegistry does not provide an execute method."
            )

        return execute(
            self.name,
            tool_name,
            parameters,
        )

    # ------------------------------------------------------------------
    # Result handling
    # ------------------------------------------------------------------

    def _normalise_result(
        self,
        result: Any,
        operation: str,
        query: Optional[str] = None,
        url: Optional[str] = None,
    ) -> Dict[str, Any]:
        if isinstance(result, dict):
            output = dict(result)

            output.setdefault("agent", self.name)
            output.setdefault("operation", operation)

            if query is not None:
                output.setdefault("query", query)

            if url is not None:
                output.setdefault("url", url)

            return output

        return {
            "status": "success",
            "agent": self.name,
            "operation": operation,
            "query": query,
            "url": url,
            "result": result,
        }

    # ------------------------------------------------------------------
    # Help
    # ------------------------------------------------------------------

    def get_help(self) -> Dict[str, Any]:
        return {
            "status": "success",
            "agent": self.name,
            "role": self.role,
            "capabilities": [
                "search public information",
                "research topics",
                "read webpages",
                "farm information",
                "store research findings",
                "return structured research results",
            ],
            "commands": [
                "search <topic>",
                "research <topic>",
                "find information about <topic>",
                "find info about <topic>",
                "farm <topic>",
                "read <url>",
                "open <url>",
                "status",
                "help",
            ],
            "safety": {
                "read_only": True,
                "simulation_safe": True,
                "consequential_external_actions": False,
                "creator_approval_required_for_live_actions": True,
            },
            }
