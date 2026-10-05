"""
Tool Registry
-------------

Central execution gateway for agent tools.

Every agent executes tools through this registry.

The registry enforces:

    - tool discovery
    - simulation mode
    - real mode
    - Creator approval
    - exact action matching
    - single-use approvals
    - execution logging
"""

from typing import Any, Callable, Dict, List, Optional

from .approvals import ApprovalGate
from .economy import Economy
from .memory import SharedMemory
from .research import WebResearch


class ToolRegistry:

    VALID_MODES = {
        "simulation",
        "real",
    }

    def __init__(
        self,
        memory: SharedMemory,
        economy: Optional[
            Economy
        ] = None,
        research: Optional[
            WebResearch
        ] = None,
    ):
        self.memory = memory
        self.economy = economy
        self.research = research

        self.tools: Dict[
            str,
            Dict[str, Any],
        ] = {}

        self.approvals = ApprovalGate(
            memory
        )

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register(
        self,
        name: str,
        description: str,
        func: Callable,
        requires_approval: bool = False,
        live_capable: bool = False,
        simulation_safe: bool = True,
    ) -> None:
        self.tools[name] = {
            "name": name,
            "description": description,
            "func": func,
            "requires_approval": requires_approval,
            "live_capable": live_capable,
            "simulation_safe": simulation_safe,
        }

    # ------------------------------------------------------------------
    # Discovery
    # ------------------------------------------------------------------

    def get_tool(
        self,
        name: str,
    ) -> Optional[
        Dict[str, Any]
    ]:
        return self.tools.get(
            name
        )

    def list_tools(
        self,
    ) -> List[Dict[str, Any]]:
        return [
            {
                "name": tool["name"],
                "description": tool["description"],
                "requires_approval": tool[
                    "requires_approval"
                ],
                "live_capable": tool[
                    "live_capable"
                ],
                "simulation_safe": tool[
                    "simulation_safe"
                ],
            }
            for tool in self.tools.values()
        ]

    def get_capabilities(
        self,
    ) -> List[Dict[str, Any]]:
        return self.list_tools()

    # ------------------------------------------------------------------
    # Mode
    # ------------------------------------------------------------------

    def get_mode(
        self,
    ) -> str:
        if self.economy is None:
            return "simulation"

        try:
            return self.economy.get_mode()
        except Exception:
            try:
                if self.economy.is_real():
                    return "real"

                return "simulation"

            except Exception:
                return "simulation"

    def is_real_mode(
        self,
    ) -> bool:
        return self.get_mode() == "real"

    def is_simulation_mode(
        self,
    ) -> bool:
        return self.get_mode() == "simulation"

    # ------------------------------------------------------------------
    # Approval matching
    # ------------------------------------------------------------------

    @staticmethod
    def _parameters_match(
        requested: Dict[str, Any],
        approved: Dict[str, Any],
    ) -> bool:
        return requested == approved

    def _find_matching_approval(
        self,
        tool_name: str,
        agent: str,
        parameters: Dict[str, Any],
    ) -> Optional[
        Dict[str, Any]
    ]:
        for approval in self.approvals.get_pending():
            if approval.get(
                "action"
            ) != tool_name:
                continue

            if approval.get(
                "agent"
            ) != agent:
                continue

            if not self._parameters_match(
                parameters,
                approval.get(
                    "parameters",
                    {},
                ),
            ):
                continue

            return approval

        return None

    # ------------------------------------------------------------------
    # Approval request
    # ------------------------------------------------------------------

    def request_approval(
        self,
        tool_name: str,
        agent: str,
        parameters: Dict[str, Any],
        description: Optional[str] = None,
        plan: Optional[
            List[str]
        ] = None,
        risk: str = "high",
    ) -> Dict[str, Any]:

        tool = self.get_tool(
            tool_name
        )

        if tool is None:
            return {
                "success": False,
                "error": (
                    f"Tool '{tool_name}' "
                    "not found."
                ),
            }

        approval = self.approvals.request(
            action=tool_name,
            description=(
                description
                or tool["description"]
            ),
            parameters=parameters,
            agent=agent,
            plan=plan or [],
            risk=risk,
        )

        return {
            "success": False,
            "requires_approval": True,
            "approval_id": approval["id"],
            "approval": approval,
            "message": (
                f"Creator approval required "
                f"for '{tool_name}'. "
                f"Request #{approval['id']}."
            ),
        }

    # ------------------------------------------------------------------
    # Execute
    # ------------------------------------------------------------------

    def execute(
        self,
        name: str,
        agent: str = "Unknown",
        approval_id: Optional[int] = None,
        approved: bool = False,
        **kwargs: Any,
    ) -> Dict[str, Any]:

        tool = self.get_tool(
            name
        )

        if tool is None:
            return {
                "success": False,
                "error": (
                    f"Tool '{name}' "
                    "not found."
                ),
            }

        mode = self.get_mode()

        # --------------------------------------------------------------
        # Simulation restrictions
        # --------------------------------------------------------------

        if (
            mode == "simulation"
            and not tool.get(
                "simulation_safe",
                True,
            )
        ):
            return {
                "success": False,
                "blocked": True,
                "error": (
                    f"Tool '{name}' is not "
                    "permitted in simulation mode."
                ),
            }

        # --------------------------------------------------------------
        # REAL mode approval
        # --------------------------------------------------------------

        if (
            mode == "real"
            and tool.get(
                "requires_approval",
                False,
            )
        ):

            approval = None

            if approval_id is not None:
                approval = self.approvals.get(
                    approval_id
                )

                if approval is None:
                    return {
                        "success": False,
                        "blocked": True,
                        "error": (
                            f"Approval #{approval_id} "
                            "does not exist."
                        ),
                    }

                if approval.get(
                    "status"
                ) != "approved":
                    return {
                        "success": False,
                        "blocked": True,
                        "requires_approval": True,
                        "error": (
                            f"Approval #{approval_id} "
                            "is not approved."
                        ),
                    }

            else:
                approval = (
                    self._find_matching_approval(
                        tool_name=name,
                        agent=agent,
                        parameters=kwargs,
                    )
                )

            if approval is None:

                return self.request_approval(
                    tool_name=name,
                    agent=agent,
                    parameters=kwargs,
                    description=(
                        f"REAL mode action "
                        f"'{name}' requires "
                        "Creator approval."
                    ),
                )

            if approval.get(
                "action"
            ) != name:
                return {
                    "success": False,
                    "blocked": True,
                    "error": (
                        "Approval action does "
                        "not match requested tool."
                    ),
                }

            if approval.get(
                "agent"
            ) != agent:
                return {
                    "success": False,
                    "blocked": True,
                    "error": (
                        "Approval belongs to "
                        "another agent."
                    ),
                }

            if not self._parameters_match(
                kwargs,
                approval.get(
                    "parameters",
                    {},
                ),
            ):
                return {
                    "success": False,
                    "blocked": True,
                    "error": (
                        "Approval parameters "
                        "do not match."
                    ),
                }

            consumed = (
                self.approvals.consume_approval(
                    approval["id"]
                )
            )

            if not consumed:
                return {
                    "success": False,
                    "blocked": True,
                    "error": (
                        "Approval could not "
                        "be consumed."
                    ),
                }

        # --------------------------------------------------------------
        # Execute
        # --------------------------------------------------------------

        self.memory.log(
            "ToolSystem",
            (
                f"Executing '{name}' "
                f"for {agent} "
                f"in {mode.upper()} mode."
            ),
        )

        try:
            result = tool["func"](
                **kwargs
            )

            self.memory.log(
                "ToolSystem",
                (
                    f"Tool '{name}' "
                    f"completed for {agent}."
                ),
            )

            return {
                "success": True,
                "tool": name,
                "agent": agent,
                "mode": mode,
                "result": result,
            }

        except Exception as exc:

            self.memory.log(
                "ToolSystem",
                (
                    f"Tool '{name}' failed: "
                    f"{exc}"
                ),
                level="error",
            )

            return {
                "success": False,
                "tool": name,
                "agent": agent,
                "mode": mode,
                "error": str(exc),
            }


# ======================================================================
# DEFAULT TOOLS
# ======================================================================

def create_default_tools(
    memory: SharedMemory,
    world,
    economy: Optional[
        Economy
    ] = None,
    research: Optional[
        WebResearch
    ] = None,
) -> ToolRegistry:

    registry = ToolRegistry(
        memory=memory,
        economy=economy,
        research=research,
    )

    # ------------------------------------------------------------------
    # Internal tools
    # ------------------------------------------------------------------

    def log_message(
        agent: str,
        message: str,
    ):
        memory.log(
            agent,
            message,
        )

        return (
            f"Logged: {message}"
        )

    def farm_info(
        topic: str,
        agent: str = "InfoFarmer",
    ):
        content = (
            f"Gathered basic information "
            f"about '{topic}'."
        )

        entry = memory.add_knowledge(
            source=agent,
            content=content,
            tags=[
                topic.lower(),
                "farmed",
            ],
        )

        world.add_resource(
            "info_points",
            5,
        )

        memory.log(
            agent,
            f"Farmed info on: {topic}",
        )

        return entry

    def check_balance():
        return {
            "balance": memory.get_balance(
                "Banker"
            )
        }

    def create_task(
        title: str,
        description: str,
        assigned_to: str,
    ):
        return memory.add_task(
            title,
            description,
            assigned_to,
        )

    registry.register(
        "log",
        "Write a log message.",
        log_message,
    )

    registry.register(
        "farm_info",
        "Farm information on a topic.",
        farm_info,
    )

    registry.register(
        "check_balance",
        "Check current money balance.",
        check_balance,
    )

    registry.register(
        "create_task",
        "Create a new task for an agent.",
        create_task,
    )

    # ------------------------------------------------------------------
    # Economy tools
    # ------------------------------------------------------------------

    if economy:

        def money_mode(
            mode: Optional[str] = None,
        ):
            if mode is None:
                return (
                    f"Current economy mode: "
                    f"{economy.get_mode().upper()}"
                )

            return economy.set_mode(
                mode
            )

        def find_opportunity(
            name: str,
            description: str,
            startup_cost: float = 50,
            expected_expenses: float = 20,
            expected_revenue: float = 150,
            risk: str = "medium",
        ):
            return economy.create_opportunity(
                name=name,
                description=description,
                startup_cost=startup_cost,
                expected_expenses=expected_expenses,
                expected_revenue=expected_revenue,
                risk=risk,
            )

        def analyse_opportunity(
            opp_id: int,
        ):
            return economy.analyse_opportunity(
                opp_id
            )

        def list_opportunities(
            status: Optional[str] = None,
        ):
            return economy.list_opportunities(
                status
            )

        def create_experiment(
            opp_id: int,
            budget: float,
            notes: str = "",
        ):
            return economy.create_experiment(
                opp_id,
                budget,
                notes,
            )

        def complete_experiment(
            exp_id: int,
            revenue: float,
            extra_expenses: float = 0.0,
            notes: str = "",
        ):
            return economy.complete_experiment(
                exp_id,
                revenue,
                extra_expenses,
                notes,
            )

        def economy_report():
            return economy.get_economy_report()

        registry.register(
            "money_mode",
            "Get or set economy mode.",
            money_mode,
        )

        registry.register(
            "find_opportunity",
            "Create a new opportunity.",
            find_opportunity,
        )

        registry.register(
            "analyse_opportunity",
            "Analyse an opportunity.",
            analyse_opportunity,
        )

        registry.register(
            "list_opportunities",
            "List economic opportunities.",
            list_opportunities,
        )

        registry.register(
            "create_experiment",
            "Start an economic experiment.",
            create_experiment,
            requires_approval=True,
            live_capable=True,
            simulation_safe=True,
        )

        registry.register(
            "complete_experiment",
            "Complete an economic experiment.",
            complete_experiment,
            requires_approval=True,
            live_capable=True,
            simulation_safe=True,
        )

        registry.register(
            "economy_report",
            "Generate an economy report.",
            economy_report,
        )

    # ------------------------------------------------------------------
    # Research tools
    # ------------------------------------------------------------------

    if research:

        def web_search(
            query: str,
            max_results: int = 5,
        ):
            return research.search(
                query,
                max_results,
            )

        def read_webpage(
            url: str,
        ):
            return research.read_page(
                url
            )

        registry.register(
            "web_search",
            "Search the public web.",
            web_search,
            live_capable=False,
            simulation_safe=True,
        )

        registry.register(
            "read_webpage",
            "Read a public webpage.",
            read_webpage,
            live_capable=False,
            simulation_safe=True,
        )

    return registry
