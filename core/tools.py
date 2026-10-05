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
    - exact agent matching
    - exact parameter matching
    - single-use approvals
    - execution logging

Important:

REAL mode does not mean unrestricted execution.

Public research tools can operate autonomously.

Consequential/protected tools require an explicit Creator
approval tied to the exact action.
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
        economy: Optional[Economy] = None,
        research: Optional[WebResearch] = None,
    ):
        self.memory = memory
        self.economy = economy
        self.research = research

        self.tools: Dict[str, Dict[str, Any]] = {}

        self.approvals = ApprovalGate(memory)

    # ------------------------------------------------------------------
    # REGISTRATION
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
        Register a tool with the central registry.
        """

        if not name:
            raise ValueError(
                "Tool name cannot be empty."
            )

        if not callable(func):
            raise TypeError(
                f"Tool '{name}' must have a callable function."
            )

        self.tools[name] = {
            "name": name,
            "description": description,
            "func": func,
            "requires_approval": bool(
                requires_approval
            ),
            "live_capable": bool(
                live_capable
            ),
            "simulation_safe": bool(
                simulation_safe
            ),
        }

    # ------------------------------------------------------------------
    # DISCOVERY
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

    def get_capabilities(self) -> List[Dict[str, Any]]:
        return self.list_tools()

    # ------------------------------------------------------------------
    # MODE
    # ------------------------------------------------------------------

    def get_mode(self) -> str:
        """
        Return the current economy/system mode.

        If no economy object exists, default to simulation.
        """

        if self.economy is None:
            return "simulation"

        try:
            mode = self.economy.get_mode()

            if mode in self.VALID_MODES:
                return mode

        except Exception:
            pass

        try:
            if self.economy.is_real():
                return "real"

        except Exception:
            pass

        return "simulation"

    def is_real_mode(self) -> bool:
        return self.get_mode() == "real"

    def is_simulation_mode(self) -> bool:
        return self.get_mode() == "simulation"

    # ------------------------------------------------------------------
    # APPROVAL MATCHING
    # ------------------------------------------------------------------

    @staticmethod
    def _parameters_match(
        requested: Dict[str, Any],
        approved: Dict[str, Any],
    ) -> bool:
        """
        Exact parameter comparison.

        We deliberately do not perform fuzzy matching.

        An approval for one action must not authorize a different
        action.
        """

        return requested == approved

    def _find_matching_approval(
        self,
        tool_name: str,
        agent: str,
        parameters: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        """
        Find an already-approved request matching the exact action.

        Only approved requests are considered.

        Consumed requests are never returned.
        """

        approvals = self.approvals.list_all()

        for approval in approvals:

            if approval.get("status") != "approved":
                continue

            if approval.get("tool") != tool_name:
                continue

            if approval.get("agent") != agent:
                continue

            approved_payload = approval.get(
                "payload",
                {},
            )

            if not self._parameters_match(
                parameters,
                approved_payload,
            ):
                continue

            return approval

        return None

    # ------------------------------------------------------------------
    # REQUEST CREATOR APPROVAL
    # ------------------------------------------------------------------

    def request_approval(
        self,
        tool_name: str,
        agent: str,
        parameters: Dict[str, Any],
        description: Optional[str] = None,
        plan: Optional[List[str]] = None,
        risk: str = "high",
    ) -> Dict[str, Any]:
        """
        Create a Creator approval request.

        The request contains an exact snapshot of the parameters
        that the agent wants to use.
        """

        tool = self.get_tool(tool_name)

        if tool is None:
            return {
                "success": False,
                "error": (
                    f"Tool '{tool_name}' not found."
                ),
            }

        approval = self.approvals.request(
            tool_name=tool_name,
            reason=(
                description
                or tool["description"]
            ),
            payload=parameters,
            agent=agent,
            risk=risk,
        )

        # Store the plan as additional metadata so the Creator
        # can understand why the agent wants the action.
        if plan:
            for item in self.memory.data.get(
                "approvals",
                [],
            ):
                if item.get("id") == approval["id"]:
                    item["plan"] = list(plan)
                    break

            self.memory.save()

            approval["plan"] = list(plan)

        return {
            "success": False,
            "blocked": True,
            "requires_approval": True,
            "approval_id": approval["id"],
            "approval": approval,
            "message": (
                f"Creator approval required for "
                f"'{tool_name}'. "
                f"Request #{approval['id']}."
            ),
        }

    # ------------------------------------------------------------------
    # EXECUTION
    # ------------------------------------------------------------------

    def execute(
        self,
        name: str,
        agent: str = "Unknown",
        approval_id: Optional[int] = None,
        approved: bool = False,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """
        Execute a registered tool.

        Protected tools in REAL mode require an exact Creator
        approval before execution.

        The approval is consumed BEFORE the tool is called.
        """

        tool = self.get_tool(name)

        if tool is None:
            return {
                "success": False,
                "error": (
                    f"Tool '{name}' not found."
                ),
            }

        mode = self.get_mode()

        # --------------------------------------------------------------
        # SIMULATION SAFETY
        # --------------------------------------------------------------

        if (
            mode == "simulation"
            and not tool.get(
                "simulation_safe",
                True,
            )
        ):
            self.memory.log(
                "ToolSystem",
                (
                    f"Blocked '{name}' for {agent}: "
                    "not simulation-safe."
                ),
                level="warning",
            )

            return {
                "success": False,
                "blocked": True,
                "tool": name,
                "agent": agent,
                "mode": mode,
                "error": (
                    f"Tool '{name}' is not permitted "
                    "in simulation mode."
                ),
            }

        # --------------------------------------------------------------
        # LIVE CAPABILITY
        # --------------------------------------------------------------

        if (
            mode == "real"
            and not tool.get(
                "live_capable",
                False,
            )
            and tool.get(
                "requires_approval",
                False,
            )
        ):
            return {
                "success": False,
                "blocked": True,
                "tool": name,
                "agent": agent,
                "mode": mode,
                "error": (
                    f"Tool '{name}' is marked as protected "
                    "but is not declared live-capable."
                ),
            }

        # --------------------------------------------------------------
        # REAL MODE CREATOR APPROVAL
        # --------------------------------------------------------------

        approval = None

        if (
            mode == "real"
            and tool.get(
                "requires_approval",
                False,
            )
        ):

            # ----------------------------------------------------------
            # Locate approval
            # ----------------------------------------------------------

            if approval_id is not None:
                approval = self.approvals.get(
                    approval_id
                )

                if approval is None:
                    return {
                        "success": False,
                        "blocked": True,
                        "requires_approval": True,
                        "error": (
                            f"Approval #{approval_id} "
                            "does not exist."
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

            # ----------------------------------------------------------
            # No approval
            # ----------------------------------------------------------

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

            # ----------------------------------------------------------
            # Approval status
            # ----------------------------------------------------------

            if approval.get("status") != "approved":
                return {
                    "success": False,
                    "blocked": True,
                    "requires_approval": True,
                    "approval_id": approval.get(
                        "id"
                    ),
                    "error": (
                        f"Approval #{approval.get('id')} "
                        f"is {approval.get('status')}, "
                        "not approved."
                    ),
                }

            # ----------------------------------------------------------
            # Exact tool match
            # ----------------------------------------------------------

            if approval.get("tool") != name:
                return {
                    "success": False,
                    "blocked": True,
                    "error": (
                        "Approval tool does not "
                        "match requested tool."
                    ),
                }

            # ----------------------------------------------------------
            # Exact agent match
            # ----------------------------------------------------------

            if approval.get("agent") != agent:
                return {
                    "success": False,
                    "blocked": True,
                    "error": (
                        "Approval belongs to "
                        "another agent."
                    ),
                }

            # ----------------------------------------------------------
            # Exact parameters
            # ----------------------------------------------------------

            approved_payload = approval.get(
                "payload",
                {},
            )

            if not self._parameters_match(
                kwargs,
                approved_payload,
            ):
                return {
                    "success": False,
                    "blocked": True,
                    "error": (
                        "Approval parameters do not "
                        "match the requested action."
                    ),
                }

            # ----------------------------------------------------------
            # CONSUME BEFORE EXECUTION
            # ----------------------------------------------------------

            consumed = self.approvals.consume(
                approval_id=approval["id"],
                tool_name=name,
                agent=agent,
                payload=kwargs,
            )

            if not consumed:
                return {
                    "success": False,
                    "blocked": True,
                    "error": (
                        "Creator approval could not "
                        "be consumed. The action was not executed."
                    ),
                }

        # --------------------------------------------------------------
        # EXECUTE TOOL
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

            # Record result against the consumed approval.
            if approval is not None:
                self.approvals.mark_execution_result(
                    approval_id=approval["id"],
                    success=True,
                    result=result,
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

            error_message = str(exc)

            if approval is not None:
                self.approvals.mark_execution_result(
                    approval_id=approval["id"],
                    success=False,
                    error=error_message,
                )

            self.memory.log(
                "ToolSystem",
                (
                    f"Tool '{name}' failed: "
                    f"{error_message}"
                ),
                level="error",
            )

            return {
                "success": False,
                "tool": name,
                "agent": agent,
                "mode": mode,
                "error": error_message,
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
    Build the default ToolRegistry used by the application.
    """

    registry = ToolRegistry(
        memory=memory,
        economy=economy,
        research=research,
    )

    # ------------------------------------------------------------------
    # INTERNAL TOOLS
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
        "Check the current money balance.",
        check_balance,
    )

    registry.register(
        "create_task",
        "Create a task for another agent.",
        create_task,
    )

    # ------------------------------------------------------------------
    # ECONOMY TOOLS
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
            "Create a new economic opportunity.",
            find_opportunity,
        )

        registry.register(
            "analyse_opportunity",
            "Analyse an economic opportunity.",
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
            "Generate a complete economy report.",
            economy_report,
        )

    # ------------------------------------------------------------------
    # PUBLIC RESEARCH TOOLS
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

        # Public research does not require Creator approval.
        # It is read-only and does not itself create a consequential
        # external-world action.

        registry.register(
            "web_search",
            "Search the public web for information.",
            web_search,
            requires_approval=False,
            live_capable=False,
            simulation_safe=True,
        )

        registry.register(
            "read_webpage",
            "Read a public webpage.",
            read_webpage,
            requires_approval=False,
            live_capable=False,
            simulation_safe=True,
        )

    return registry
