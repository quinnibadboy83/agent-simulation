"""
Tool Registry
-------------

Central execution layer for all agent tools.

All agents must use this registry when executing tools.

The registry controls:

    - tool registration
    - tool discovery
    - simulation/real mode
    - Creator approval requirements
    - approval consumption
    - exact parameter matching
    - execution logging
    - error handling
"""

from typing import Any, Callable, Dict, List, Optional

from .approvals import ApprovalGate
from .economy import Economy
from .memory import SharedMemory
from .research import WebResearch


class ToolRegistry:
    """
    Central registry and execution gateway for agent tools.
    """

    VALID_MODES = {"simulation", "real"}

    def __init__(
        self,
        memory: SharedMemory,
        economy: Optional[Economy] = None,
        research: Optional[WebResearch] = None,
    ):
        self.memory = memory
        self.economy = economy
        self.research = research

        self.tools: Dict[str, Dict[str, Any]] = {}

        self.approvals = ApprovalGate(self.memory)

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
        """
        Register a tool.

        requires_approval:
            The tool requires Creator approval when operating in REAL mode.

        live_capable:
            The tool can potentially affect or communicate with the
            external/live world.

        simulation_safe:
            The tool is allowed to execute in SIMULATION mode.
        """

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
    ) -> Optional[Dict[str, Any]]:
        return self.tools.get(name)

    def list_tools(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": tool["name"],
                "description": tool["description"],
                "requires_approval": tool["requires_approval"],
                "live_capable": tool["live_capable"],
                "simulation_safe": tool["simulation_safe"],
            }
            for tool in self.tools.values()
        ]

    def get_capabilities(self) -> List[Dict[str, Any]]:
        return self.list_tools()

    # ------------------------------------------------------------------
    # Mode helpers
    # ------------------------------------------------------------------

    def get_mode(self) -> str:
        if self.economy is None:
            return "simulation"

        try:
            return self.economy.get_mode()
        except Exception:
            return "simulation"

    def is_real_mode(self) -> bool:
        return self.get_mode() == "real"

    def is_simulation_mode(self) -> bool:
        return self.get_mode() == "simulation"

    # ------------------------------------------------------------------
    # Parameter helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _parameters_match(
        requested: Dict[str, Any],
        approved: Dict[str, Any],
    ) -> bool:
        """
        Require exact parameter matching.

        An approval for one set of parameters cannot be reused for
        another action.
        """

        return requested == approved

    def _find_matching_approval(
        self,
        tool_name: str,
        agent: str,
        parameters: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        for item in self.approvals.get_pending():
            if item.get("action") != tool_name:
                continue

            if item.get("agent") != agent:
                continue

            approved_parameters = item.get(
                "parameters",
                {},
            )

            if self._parameters_match(
                parameters,
                approved_parameters,
            ):
                return item

        return None

    # ------------------------------------------------------------------
    # Approval requests
    # ------------------------------------------------------------------

    def request_approval(
        self,
        tool_name: str,
        agent: str,
        parameters: Dict[str, Any],
        description: Optional[str] = None,
        plan: Optional[List[str]] = None,
        risk: str = "medium",
    ) -> Dict[str, Any]:
        tool = self.get_tool(tool_name)

        if tool is None:
            return {
                "success": False,
                "error": f"Tool '{tool_name}' not found.",
            }

        request = self.approvals.request(
            action=tool_name,
            description=(
                description
                or tool.get("description", "")
            ),
            parameters=parameters,
            agent=agent,
            plan=plan or [],
            risk=risk,
        )

        return {
            "success": False,
            "requires_approval": True,
            "approval_id": request["id"],
            "approval": request,
            "message": (
                f"Creator approval required for "
                f"'{tool_name}'. "
                f"Approval request #{request['id']} "
                "has been created."
            ),
        }

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------

    def execute(
        self,
        name: str,
        agent: str = "Unknown",
        approval_id: Optional[int] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """
        Execute a registered tool.

        Protected tools in REAL mode require an approval belonging to:
            - the same tool
            - the same agent
            - the exact same parameters

        The approval is consumed BEFORE execution begins.

        Therefore an approval cannot be reused.
        """

        tool = self.get_tool(name)

        if tool is None:
            return {
                "success": False,
                "error": f"Tool '{name}' not found.",
            }

        simulation = self.is_simulation_mode()
        real = self.is_real_mode()

        # --------------------------------------------------------------
        # Simulation safety
        # --------------------------------------------------------------

        if simulation and not tool.get(
            "simulation_safe",
            True,
        ):
            self.memory.log(
                "ToolSystem",
                (
                    f"Blocked tool '{name}' because it is "
                    "not permitted in simulation mode."
                ),
                level="warning",
            )

            return {
                "success": False,
                "blocked": True,
                "error": (
                    f"Tool '{name}' is not permitted "
                    "in simulation mode."
                ),
            }

        # --------------------------------------------------------------
        # Real-mode approval
        # --------------------------------------------------------------

        if (
            real
            and tool.get("requires_approval", False)
        ):
            approval = None

            # Explicit approval ID supplied by caller.
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

                if approval.get("status") != "approved":
                    return {
                        "success": False,
                        "blocked": True,
                        "requires_approval": True,
                        "error": (
                            f"Approval #{approval_id} "
                            "is not approved."
                        ),
                    }

                if approval.get("action") != name:
                    return {
                        "success": False,
                        "blocked": True,
                        "error": (
                            "Approval does not match "
                            f"tool '{name}'."
                        ),
                    }

                if approval.get("agent") != agent:
                    return {
                        "success": False,
                        "blocked": True,
                        "error": (
                            "Approval does not belong "
                            f"to agent '{agent}'."
                        ),
                    }

                if not self._parameters_match(
                    kwargs,
                    approval.get("parameters", {}),
                ):
                    return {
                        "success": False,
                        "blocked": True,
                        "error": (
                            "Approval parameters do not "
                            "match the requested action."
                        ),
                    }

            # No explicit approval supplied.
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
                            f"REAL mode action '{name}' "
                            "requires Creator approval."
                        ),
                        risk="high",
                    )

            # ----------------------------------------------------------
            # Consume approval BEFORE execution.
            # ----------------------------------------------------------

            consumed = self.approvals.consume_approval(
                int(approval["id"])
            )

            if not consumed:
                return {
                    "success": False,
                    "blocked": True,
                    "error": (
                        "Approval could not be consumed. "
                        "Execution blocked."
                    ),
                }

        # --------------------------------------------------------------
        # Execute tool
        # --------------------------------------------------------------

        self.memory.log(
            "ToolSystem",
            (
                f"Executing tool '{name}' "
                f"for agent '{agent}' "
                f"in {self.get_mode().upper()} mode."
            ),
        )

        try:
            result = tool["func"](
                **kwargs
            )

            self.memory.log(
                "ToolSystem",
                (
                    f"Tool '{name}' completed successfully "
                    f"for '{agent}'."
                ),
            )

            return {
                "success": True,
                "tool": name,
                "agent": agent,
                "mode": self.get_mode(),
                "result": result,
            }

        except Exception as exc:
            self.memory.log(
                "ToolSystem",
                (
                    f"Tool '{name}' failed for "
                    f"'{agent}': {exc}"
                ),
                level="error",
            )

            return {
                "success": False,
                "tool": name,
                "agent": agent,
                "mode": self.get_mode(),
                "error": str(exc),
            }


# ======================================================================
# DEFAULT TOOLS
# ======================================================================

def create_default_tools(
    memory: SharedMemory,
    world,
    economy: Optional[Economy] = None,
    research: Optional[WebResearch] = None,
) -> ToolRegistry:
    """
    Create the default ToolRegistry used by the application.
    """

    registry = ToolRegistry(
        memory=memory,
        economy=economy,
        research=research,
    )

    # ------------------------------------------------------------------
    # Basic internal tools
    # ------------------------------------------------------------------

    def log_message(
        agent: str,
        message: str,
    ):
        memory.log(
            agent,
            message,
        )

        return f"Logged: {message}"

    def farm_info(
        topic: str,
        agent: str = "InfoFarmer",
    ):
        content = (
            f"Gathered basic information about "
            f"'{topic}'."
        )

        entry = memory.add_knowledge(
            source=agent,
            content=content,
            tags=[
                topic.lower(),
                "farmed",
            ],
        )

        if world is not None:
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
            title=title,
            description=description,
            assigned_to=assigned_to,
            created_by="Boss",
        )

    registry.register(
        name="log",
        description="Write a log message.",
        func=log_message,
    )

    registry.register(
        name="farm_info",
        description="Farm information on a topic.",
        func=farm_info,
    )

    registry.register(
        name="check_balance",
        description="Check the current Banker balance.",
        func=check_balance,
    )

    registry.register(
        name="create_task",
        description="Create a new task for an agent.",
        func=create_task,
    )

    # ------------------------------------------------------------------
    # Economy tools
    # ------------------------------------------------------------------

    if economy is not None:

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
            name="money_mode",
            description="Get or set economy mode.",
            func=money_mode,
        )

        registry.register(
            name="find_opportunity",
            description="Create a new economic opportunity.",
            func=find_opportunity,
        )

        registry.register(
            name="analyse_opportunity",
            description="Analyse an economic opportunity.",
            func=analyse_opportunity,
        )

        registry.register(
            name="list_opportunities",
            description="List available economic opportunities.",
            func=list_opportunities,
        )

        registry.register(
            name="create_experiment",
            description=(
                "Start an economic experiment. "
                "REAL mode requires Creator approval."
            ),
            func=create_experiment,
            requires_approval=True,
            live_capable=True,
            simulation_safe=True,
        )

        registry.register(
            name="complete_experiment",
            description=(
                "Complete an economic experiment. "
                "REAL mode requires Creator approval."
            ),
            func=complete_experiment,
            requires_approval=True,
            live_capable=True,
            simulation_safe=True,
        )

        registry.register(
            name="economy_report",
            description="Generate the full economy report.",
            func=economy_report,
        )

    # ------------------------------------------------------------------
    # Web research tools
    # ------------------------------------------------------------------

    if research is not None:

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
            name="web_search",
            description="Search the public web for information.",
            func=web_search,
            live_capable=False,
            simulation_safe=True,
        )

        registry.register(
            name="read_webpage",
            description="Read a public webpage.",
            func=read_webpage,
            live_capable=False,
            simulation_safe=True,
        )

    return registry
