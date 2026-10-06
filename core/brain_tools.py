from __future__ import annotations

from typing import Any, Dict, List, Optional


class BrainToolAdapter:
    """
    Converts the application's ToolRegistry into the function/tool
    definitions understood by an LLM.

    The model sees capabilities, not Python implementation details.
    """

    def __init__(
        self,
        tools=None,
    ):
        self.tools = tools

    def definitions(self) -> List[Dict[str, Any]]:
        if self.tools is None:
            return []

        names = self._tool_names()

        definitions: List[Dict[str, Any]] = []

        for name in names:
            definition = self._definition_for(name)

            if definition:
                definitions.append(definition)

        return definitions

    def _tool_names(self) -> List[str]:
        if hasattr(self.tools, "list_tools"):
            try:
                result = self.tools.list_tools()

                if isinstance(result, list):
                    names = []

                    for item in result:
                        if isinstance(item, str):
                            names.append(item)

                        elif isinstance(item, dict):
                            name = item.get("name")

                            if name:
                                names.append(str(name))

                    return names

            except Exception:
                pass

        return []

    def _definition_for(
        self,
        name: str,
    ) -> Optional[Dict[str, Any]]:

        known = {
            "log": {
                "description": (
                    "Write a message to shared agent memory."
                ),
                "properties": {
                    "message": {
                        "type": "string",
                    },
                    "level": {
                        "type": "string",
                    },
                },
                "required": [
                    "message",
                ],
            },

            "farm_info": {
                "description": (
                    "Gather information using the research system."
                ),
                "properties": {
                    "query": {
                        "type": "string",
                    },
                },
                "required": [
                    "query",
                ],
            },

            "check_balance": {
                "description": (
                    "Inspect the current simulated financial balance."
                ),
                "properties": {},
                "required": [],
            },

            "create_task": {
                "description": (
                    "Create a task for an agent to work on."
                ),
                "properties": {
                    "title": {
                        "type": "string",
                    },
                    "description": {
                        "type": "string",
                    },
                    "priority": {
                        "type": "integer",
                    },
                    "agent": {
                        "type": "string",
                    },
                },
                "required": [
                    "title",
                    "description",
                ],
            },

            "find_opportunity": {
                "description": (
                    "Find potential revenue opportunities."
                ),
                "properties": {
                    "category": {
                        "type": "string",
                    },
                },
                "required": [],
            },

            "analyse_opportunity": {
                "description": (
                    "Analyse a previously discovered opportunity."
                ),
                "properties": {
                    "opportunity_id": {
                        "type": "string",
                    },
                },
                "required": [
                    "opportunity_id",
                ],
            },

            "list_opportunities": {
                "description": (
                    "List known revenue opportunities."
                ),
                "properties": {},
                "required": [],
            },

            "economy_report": {
                "description": (
                    "Inspect the current simulated economy."
                ),
                "properties": {},
                "required": [],
            },

            "web_search": {
                "description": (
                    "Search public web information."
                ),
                "properties": {
                    "query": {
                        "type": "string",
                    },
                    "limit": {
                        "type": "integer",
                    },
                },
                "required": [
                    "query",
                ],
            },

            "read_webpage": {
                "description": (
                    "Read a public webpage."
                ),
                "properties": {
                    "url": {
                        "type": "string",
                    },
                    "max_chars": {
                        "type": "integer",
                    },
                },
                "required": [
                    "url",
                ],
            },

            "money_mode": {
                "description": (
                    "Read the current economy operating mode."
                ),
                "properties": {},
                "required": [],
            },

            "create_experiment": {
                "description": (
                    "Create a simulated experiment proposal. "
                    "This does not perform live external actions."
                ),
                "properties": {
                    "opportunity_id": {
                        "type": "string",
                    },
                    "budget": {
                        "type": "number",
                    },
                    "duration_days": {
                        "type": "integer",
                    },
                },
                "required": [
                    "opportunity_id",
                ],
            },

            "complete_experiment": {
                "description": (
                    "Record the result of a simulated experiment."
                ),
                "properties": {
                    "experiment_id": {
                        "type": "string",
                    },
                    "result": {
                        "type": "string",
                    },
                },
                "required": [
                    "experiment_id",
                    "result",
                ],
            },
        }

        item = known.get(name)

        if item is None:
            return None

        return {
            "type": "function",
            "function": {
                "name": name,
                "description": item["description"],
                "parameters": {
                    "type": "object",
                    "properties": item["properties"],
                    "required": item["required"],
                },
            },
        }
