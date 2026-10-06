"""
Boss Agent
----------
Creator-facing coordinator for the agent simulation.

Boss receives Creator commands, understands the request, and delegates
work to the appropriate specialist agent when required.
"""

from typing import Any, Dict, Optional

from .base_agent import BaseAgent


class Boss(BaseAgent):
    def __init__(self, memory, tools):

        super().__init__(
            name="Boss",
            role="Coordinator",
            memory=memory,
            tools=tools,
            description=(
                "Coordinates the agent system, interprets Creator commands, "
                "delegates work to specialist agents, monitors the system, "
                "and coordinates revenue and research activities."
            ),
        )

        self.agents: Dict[str, Any] = {}

    # ============================================================
    # CREATOR COMMAND ENTRY POINT
    # ============================================================

    def process_order(
        self,
        order: str,
    ) -> Dict[str, Any]:
        """
        Primary command interface.

        This is the method used by main.py.
        """

        return self.process_command(order)

    # ============================================================
    # COMMAND PROCESSOR
    # ============================================================

    def process_command(
        self,
        command: str,
    ) -> Dict[str, Any]:

        command = (command or "").strip()

        if not command:

            return {
                "status": "error",
                "agent": self.name,
                "message": "No command supplied.",
            }

        lowered = command.lower()

        # --------------------------------------------------------
        # HELP
        # --------------------------------------------------------

        if lowered in {
            "help",
            "?",
            "commands",
        }:

            return self.get_help()

        # --------------------------------------------------------
        # STATUS
        # --------------------------------------------------------

        if lowered in {
            "status",
            "system status",
            "system",
        }:

            return self._system_status()

        # --------------------------------------------------------
        # AGENT STATUS
        # --------------------------------------------------------

        if lowered in {
            "agents",
            "agent status",
            "agents status",
            "list agents",
        }:

            return self._agent_status()

        # --------------------------------------------------------
        # BALANCE
        # --------------------------------------------------------

        if lowered in {
            "balance",
            "money",
            "bank balance",
            "vault",
        }:

            try:

                balance = self.memory.get_balance(
                    "Banker"
                )

            except Exception:

                balance = 0.0

            return {
                "status": "success",
                "agent": self.name,
                "operation": "balance",
                "balance": balance,
                "message": (
                    f"Current simulated balance: "
                    f"{balance}"
                ),
            }

        # --------------------------------------------------------
        # RESEARCH / SEARCH
        # --------------------------------------------------------

        if lowered.startswith("search "):

            query = command[7:].strip()

            if not query:

                return {
                    "status": "error",
                    "agent": self.name,
                    "message": (
                        "Search query is required."
                    ),
                }

            return self._delegate_to_agent(
                "InfoFarmer",
                f"search {query}",
            )

        if lowered.startswith("research "):

            topic = command[9:].strip()

            if not topic:

                return {
                    "status": "error",
                    "agent": self.name,
                    "message": (
                        "Research topic is required."
                    ),
                }

            return self._delegate_to_agent(
                "InfoFarmer",
                f"research {topic}",
            )

        if lowered.startswith(
            "find information about "
        ):

            topic = command[
                len("find information about "):
            ].strip()

            return self._delegate_to_agent(
                "InfoFarmer",
                f"farm {topic}",
            )

        if lowered.startswith(
            "find info about "
        ):

            topic = command[
                len("find info about "):
            ].strip()

            return self._delegate_to_agent(
                "InfoFarmer",
                f"farm {topic}",
            )

        # --------------------------------------------------------
        # READ WEB PAGE
        # --------------------------------------------------------

        if lowered.startswith("read "):

            url = command[5:].strip()

            if not url:

                return {
                    "status": "error",
                    "agent": self.name,
                    "message": (
                        "URL is required."
                    ),
                }

            return self._delegate_to_agent(
                "InfoFarmer",
                f"read {url}",
            )

        if lowered.startswith("open "):

            url = command[5:].strip()

            if not url:

                return {
                    "status": "error",
                    "agent": self.name,
                    "message": (
                        "URL is required."
                    ),
                }

            return self._delegate_to_agent(
                "InfoFarmer",
                f"open {url}",
            )

        # --------------------------------------------------------
        # INFORMATION FARMING
        # --------------------------------------------------------

        if lowered.startswith("farm "):

            topic = command[5:].strip()

            if not topic:

                return {
                    "status": "error",
                    "agent": self.name,
                    "message": (
                        "Information topic is required."
                    ),
                }

            return self._delegate_to_agent(
                "InfoFarmer",
                f"farm {topic}",
            )

        # --------------------------------------------------------
        # OPPORTUNITY SCANNING
        # --------------------------------------------------------

        if lowered in {
            "scan",
            "opportunities",
            "find opportunities",
            "scan opportunities",
        }:

            return self._delegate_to_agent(
                "OpportunityAgent",
                "scan",
            )

        if lowered.startswith(
            "scan "
        ):

            category = command[5:].strip()

            return self._delegate_to_agent(
                "OpportunityAgent",
                f"scan {category}",
            )

        if lowered.startswith(
            "find opportunities "
        ):

            category = command[
                len("find opportunities "):
            ].strip()

            return self._delegate_to_agent(
                "OpportunityAgent",
                f"scan {category}",
            )

        # --------------------------------------------------------
        # OPPORTUNITY LIST
        # --------------------------------------------------------

        if lowered in {
            "list opportunities",
            "opportunity list",
            "show opportunities",
        }:

            return self._delegate_to_agent(
                "OpportunityAgent",
                "opportunities",
            )

        # --------------------------------------------------------
        # OPPORTUNITY ANALYSIS
        # --------------------------------------------------------

        if lowered.startswith(
            "analyse "
        ):

            opportunity_id = command[
                len("analyse "):
            ].strip()

            return self._delegate_to_agent(
                "OpportunityAgent",
                f"analyse {opportunity_id}",
            )

        if lowered.startswith(
            "analyze "
        ):

            opportunity_id = command[
                len("analyze "):
            ].strip()

            return self._delegate_to_agent(
                "OpportunityAgent",
                f"analyse {opportunity_id}",
            )

        # --------------------------------------------------------
        # EXPERIMENTS
        # --------------------------------------------------------

        if lowered.startswith(
            "test "
        ):

            opportunity_id = command[
                len("test "):
            ].strip()

            return self._delegate_to_agent(
                "OpportunityAgent",
                f"test {opportunity_id}",
            )

        if lowered.startswith(
            "experiment "
        ):

            opportunity_id = command[
                len("experiment "):
            ].strip()

            return self._delegate_to_agent(
                "OpportunityAgent",
                f"test {opportunity_id}",
            )

        # --------------------------------------------------------
        # ECONOMY
        # --------------------------------------------------------

        if lowered in {
            "economy",
            "economy report",
            "financial report",
        }:

            return self._delegate_to_agent(
                "OpportunityAgent",
                "report",
            )

        # --------------------------------------------------------
        # MONEY-MAKING IDEAS
        # --------------------------------------------------------

        if lowered in {
            "ideas",
            "money ideas",
            "revenue ideas",
            "make money",
            "make money ideas",
        }:

            return self._delegate_to_agent(
                "OpportunityAgent",
                "ideas",
            )

        if lowered.startswith(
            "ideas "
        ):

            category = command[6:].strip()

            return self._delegate_to_agent(
                "OpportunityAgent",
                f"ideas {category}",
            )

        # --------------------------------------------------------
        # SOCIAL MEDIA PLANNING
        # --------------------------------------------------------

        social_platforms = [
            "instagram",
            "facebook",
            "linkedin",
            "youtube",
            "tiktok",
            "reddit",
            "threads",
            "twitter",
            "x",
        ]

        for platform in social_platforms:

            if lowered.startswith(
                platform + " "
            ):

                topic = command[
                    len(platform) + 1:
                ].strip()

                return self._delegate_to_agent(
                    "OpportunityAgent",
                    f"social {platform} {topic}",
                )

        # --------------------------------------------------------
        # BANKER
        # --------------------------------------------------------

        if lowered in {
            "banker",
            "banker status",
            "financial status",
            "transactions",
            "allowance",
        }:

            return self._delegate_to_agent(
                "Banker",
                command,
            )

        if lowered.startswith(
            "banker "
        ):

            banker_command = command[
                len("banker "):
            ].strip()

            return self._delegate_to_agent(
                "Banker",
                banker_command,
            )

        # --------------------------------------------------------
        # DIRECT AGENT COMMAND
        # --------------------------------------------------------

        detected_agent = self._detect_agent(
            command
        )

        if detected_agent:

            remaining = self._remove_agent_name(
                command,
                detected_agent,
            )

            if remaining:

                return self._delegate_to_agent(
                    detected_agent,
                    remaining,
                )

        # --------------------------------------------------------
        # TASK / DELEGATION
        # --------------------------------------------------------

        if lowered.startswith(
            "delegate "
        ):

            return self._delegate_command(
                command[
                    len("delegate "):
                ].strip()
            )

        if lowered.startswith(
            "assign "
        ):

            return self._create_task_from_command(
                command[
                    len("assign "):
                ].strip()
            )

        if lowered.startswith(
            "task "
        ):

            return self._create_task_from_command(
                command[
                    len("task "):
                ].strip()
            )

        # --------------------------------------------------------
        # RUN
        # --------------------------------------------------------

        if lowered in {
            "run",
            "cycle",
            "run cycle",
            "autonomous cycle",
        }:

            return self.run_cycle()

        # --------------------------------------------------------
        # FALLBACK
        # --------------------------------------------------------

        return {
            "status": "error",
            "agent": self.name,
            "message": (
                f"I don't recognise that command yet: "
                f"{command}"
            ),
            "suggestion": (
                "Try 'help', 'status', 'agents', "
                "'search <topic>', 'scan', "
                "'ideas', or 'economy'."
            ),
            "help": self.get_help(),
        }

    # ============================================================
    # AGENT REGISTRATION
    # ============================================================

    def register_agent(
        self,
        agent: Any,
    ) -> None:

        if agent is None:
            return

        name = getattr(
            agent,
            "name",
            None,
        )

        if not name:
            return

        self.agents[name] = agent

    def register_agents(
        self,
        agents: Dict[str, Any],
    ) -> None:

        if not agents:
            return

        for name, agent in agents.items():

            if name == self.name:
                continue

            self.register_agent(agent)

    # ============================================================
    # DELEGATION
    # ============================================================

    def _delegate_to_agent(
        self,
        agent_name: str,
        command: str,
    ) -> Dict[str, Any]:

        agent = self._find_agent(
            agent_name
        )

        if agent is None:

            return {
                "status": "error",
                "agent": self.name,
                "message": (
                    f"Agent '{agent_name}' "
                    "is not registered with Boss."
                ),
                "available_agents": list(
                    self.agents.keys()
                ),
            }

        try:

            if hasattr(
                agent,
                "process_order",
            ):

                result = agent.process_order(
                    command
                )

            elif hasattr(
                agent,
                "process_command",
            ):

                result = agent.process_command(
                    command
                )

            else:

                return {
                    "status": "error",
                    "agent": self.name,
                    "message": (
                        f"Agent '{agent_name}' "
                        "has no command interface."
                    ),
                }

            result = self._normalise_result(
                result
            )

            return {
                "status": "success",
                "agent": self.name,
                "delegated_to": agent_name,
                "command": command,
                "result": result,
            }

        except Exception as exc:

            return {
                "status": "error",
                "agent": self.name,
                "delegated_to": agent_name,
                "command": command,
                "message": (
                    f"{agent_name} failed: {exc}"
                ),
            }

    def _find_agent(
        self,
        name: str,
    ) -> Optional[Any]:

        if not name:
            return None

        if name in self.agents:
            return self.agents[name]

        lowered = name.lower()

        for agent_name, agent in self.agents.items():

            if agent_name.lower() == lowered:
                return agent

        return None

    def _detect_agent(
        self,
        command: str,
    ) -> Optional[str]:

        lowered = command.lower()

        names = sorted(
            self.agents.keys(),
            key=len,
            reverse=True,
        )

        for name in names:

            if lowered.startswith(
                name.lower() + " "
            ):

                return name

            if lowered == name.lower():

                return name

        return None

    def _remove_agent_name(
        self,
        command: str,
        agent_name: str,
    ) -> str:

        lowered = command.lower()
        prefix = agent_name.lower()

        if lowered.startswith(
            prefix + " "
        ):

            return command[
                len(agent_name):
            ].strip()

        if lowered == prefix:

            return ""

        return command

    # ============================================================
    # DELEGATION COMMAND
    # ============================================================

    def _delegate_command(
        self,
        command: str,
    ) -> Dict[str, Any]:

        parts = command.split(
            " ",
            1,
        )

        if len(parts) < 2:

            return {
                "status": "error",
                "agent": self.name,
                "message": (
                    "Use: delegate "
                    "<AgentName> <command>"
                ),
            }

        agent_name = parts[0]
        agent_command = parts[1].strip()

        return self._delegate_to_agent(
            agent_name,
            agent_command,
        )

    # ============================================================
    # TASK CREATION
    # ============================================================

    def _create_task_from_command(
        self,
        command: str,
    ) -> Dict[str, Any]:

        if not command:

            return {
                "status": "error",
                "agent": self.name,
                "message": (
                    "Task description is required."
                ),
            }

        try:

            task = self.create_task(
                title=command,
                description=command,
                priority="normal",
            )

            return {
                "status": "success",
                "agent": self.name,
                "operation": "create_task",
                "task": task,
                "message": (
                    f"Task created: {command}"
                ),
            }

        except Exception as exc:

            return {
                "status": "error",
                "agent": self.name,
                "message": (
                    f"Could not create task: {exc}"
                ),
            }

    # ============================================================
    # SYSTEM STATUS
    # ============================================================

    def _system_status(
        self,
    ) -> Dict[str, Any]:

        try:

            world = self.memory.get_world_state()

        except Exception:

            world = {}

        try:

            balance = self.memory.get_balance(
                "Banker"
            )

        except Exception:

            balance = 0.0

        return {
            "status": "success",
            "agent": self.name,
            "operation": "system_status",
            "message": "System operational.",
            "mode": self._get_mode(),
            "agents_registered": list(
                self.agents.keys()
            ),
            "balance": balance,
            "world": world,
        }

    # ============================================================
    # AGENT STATUS
    # ============================================================

    def _agent_status(
        self,
    ) -> Dict[str, Any]:

        result = {}

        for name, agent in self.agents.items():

            try:

                if hasattr(
                    agent,
                    "get_status_report",
                ):

                    result[name] = (
                        agent.get_status_report()
                    )

                else:

                    result[name] = {
                        "name": name,
                        "status": "registered",
                    }

            except Exception as exc:

                result[name] = {
                    "name": name,
                    "status": "error",
                    "error": str(exc),
                }

        return {
            "status": "success",
            "agent": self.name,
            "operation": "agent_status",
            "agents": result,
            "count": len(result),
        }

    # ============================================================
    # MODE
    # ============================================================

    def _get_mode(
        self,
    ) -> str:

        try:

            if hasattr(
                self.tools,
                "get_mode",
            ):

                return self.tools.get_mode()

        except Exception:
            pass

        try:

            if hasattr(
                self.memory,
                "get_world_state",
            ):

                state = (
                    self.memory.get_world_state()
                )

                return state.get(
                    "economy_mode",
                    "simulation",
                )

        except Exception:
            pass

        return "simulation"

    # ============================================================
    # RESULT NORMALISATION
    # ============================================================

    def _normalise_result(
        self,
        result: Any,
    ) -> Any:

        if result is None:
            return None

        if isinstance(
            result,
            (
                str,
                int,
                float,
                bool,
            ),
        ):
            return result

        if isinstance(
            result,
            dict,
        ):

            return {
                str(key): self._normalise_result(
                    value
                )
                for key, value in result.items()
            }

        if isinstance(
            result,
            (
                list,
                tuple,
            ),
        ):

            return [
                self._normalise_result(
                    item
                )
                for item in result
            ]

        if hasattr(
            result,
            "model_dump",
        ):

            try:

                return self._normalise_result(
                    result.model_dump()
                )

            except Exception:
                pass

        if hasattr(
            result,
            "__dict__",
        ):

            try:

                return self._normalise_result(
                    vars(result)
                )

            except Exception:
                pass

        return str(result)

    # ============================================================
    # HELP
    # ============================================================

    def get_help(
        self,
    ) -> Dict[str, Any]:

        return {
            "status": "success",
            "agent": self.name,
            "role": self.role,
            "message": (
                "Boss is the Creator-facing "
                "coordinator."
            ),
            "commands": [
                "help",
                "status",
                "agents",
                "balance",
                "search <query>",
                "research <topic>",
                "read <url>",
                "open <url>",
                "farm <topic>",
                "scan",
                "scan <category>",
                "opportunities",
                "list opportunities",
                "analyse <opportunity_id>",
                "analyze <opportunity_id>",
                "test <opportunity_id>",
                "experiment <opportunity_id>",
                "economy",
                "ideas",
                "ideas <category>",
                "instagram <topic>",
                "facebook <topic>",
                "linkedin <topic>",
                "youtube <topic>",
                "tiktok <topic>",
                "reddit <topic>",
                "delegate <agent> <command>",
                "assign <task>",
                "task <task>",
                "run",
            ],
            "agents": list(
                self.agents.keys()
            ),
            "safety": (
                "Boss coordinates the system but "
                "does not bypass the Creator "
                "approval gate for consequential "
                "actions."
            ),
            }
