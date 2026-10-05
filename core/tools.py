"""
Base Tool System + Economic Tools + Web Research Tools
-------------------------------------------------------

The ToolRegistry provides a controlled interface between autonomous
agents and the capabilities available to them.

Tool capability classes:

    1. Autonomous / simulation-safe
       Can run without Creator approval.

    2. Live-capable
       Can only run while the system is in LIVE mode.

    3. Creator-protected
       Can run in LIVE mode only after the Creator explicitly approves
       that specific action.

Internet research is intentionally different from external actions.

Agents may research the public internet autonomously.

Researching information does NOT grant permission to:
    - publish
    - send messages
    - purchase
    - spend money
    - modify accounts
    - create listings
    - post to social platforms
    - perform other consequential external actions

The Creator remains the authority for consequential live actions.
"""

from typing import Dict, Any, Callable, Optional, List

from .memory import SharedMemory
from .economy import Economy
from .research import WebResearch
from .approvals import ApprovalGate


class ToolRegistry:
    """
    Central capability and execution registry.

    This is the boundary between autonomous agent reasoning and
    actual tool execution.
    """

    def __init__(
        self,
        memory: SharedMemory,
        economy: Economy = None,
        research: WebResearch = None,
    ):
        self.memory = memory
        self.economy = economy
        self.research = research

        self.tools: Dict[str, Dict[str, Any]] = {}

        # Central Creator approval gate.
        self.approvals = ApprovalGate(
            self.memory
        )

    # ------------------------------------------------------------------
    # TOOL REGISTRATION
    # ------------------------------------------------------------------

    def register(
        self,
        name: str,
        description: str,
        func: Callable,
        requires_approval: bool = False,
        live_capable: bool = False,
        simulation_safe: bool = True,
        category: str = "general",
    ):
        """
        Register a tool.

        Parameters
        ----------
        requires_approval:
            The tool performs a consequential action and requires
            explicit Creator approval when operating in LIVE mode.

        live_capable:
            The tool can interact with or affect the real world.

        simulation_safe:
            The tool is safe to execute inside SIMULATION mode.

        category:
            Human/machine-readable category for the tool.

        Examples
        --------
        Public research:

            live_capable=False
            simulation_safe=True
            requires_approval=False

        Real-world external action:

            live_capable=True
            simulation_safe=False
            requires_approval=True
        """

        # A tool requiring approval must be live-capable.
        if requires_approval:
            live_capable = True

        self.tools[name] = {
            "name": name,
            "description": description,
            "func": func,
            "requires_approval": requires_approval,
            "live_capable": live_capable,
            "simulation_safe": simulation_safe,
            "category": category,
        }

    def get_tool(
        self,
        name: str,
    ) -> Optional[Dict]:
        return self.tools.get(name)

    def list_tools(self) -> List[Dict[str, Any]]:
        """
        Return public tool definitions.

        The callable itself is deliberately not exposed.
        """

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
                "category": tool[
                    "category"
                ],
            }
            for tool in self.tools.values()
        ]

    # ------------------------------------------------------------------
    # CAPABILITY INSPECTION
    # ------------------------------------------------------------------

    def get_capabilities(self) -> List[Dict[str, Any]]:
        """
        Return a simplified capability map.

        Useful for agent reasoning and future UI.
        """

        return self.list_tools()

    def can_execute_in_current_mode(
        self,
        tool: Dict[str, Any],
    ) -> bool:
        """
        Determine whether the tool is permitted by the current
        operating mode.

        This is only a mode/capability check.

        It does NOT grant Creator approval.
        """

        if self.economy is None:
            return tool.get(
                "simulation_safe",
                True,
            )

        if self.economy.is_simulation():
            return tool.get(
                "simulation_safe",
                True,
            )

        # LIVE mode.
        #
        # Normal autonomous tools remain available.
        # Live-capable tools are also available in principle, but
        # protected ones must subsequently pass the approval gate.
        return True

    # ------------------------------------------------------------------
    # TOOL EXECUTION
    # ------------------------------------------------------------------

    def execute(
        self,
        name: str,
        approval_id: Optional[int] = None,
        agent: str = "Unknown",
        action_description: Optional[str] = None,
        plan: Optional[List[str]] = None,
        risk: str = "medium",
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Execute a registered tool.

        Execution policy:

        SIMULATION
        -----------
        simulation_safe=True:
            Execute normally.

        simulation_safe=False:
            Refuse execution.

        LIVE
        ----
        normal tool:
            Execute normally.

        protected live tool:
            Create an approval request if no approval exists.

            Approved request:
                Consume approval.
                Execute exactly once.

            Pending / denied / consumed:
                Refuse execution.

        An approval cannot be reused.
        """

        tool = self.get_tool(name)

        if not tool:
            return {
                "success": False,
                "error": (
                    f"Tool '{name}' not found"
                ),
            }

        simulation_mode = bool(
            self.economy
            and self.economy.is_simulation()
        )

        live_mode = bool(
            self.economy
            and self.economy.is_real()
        )

        simulation_safe = tool.get(
            "simulation_safe",
            True,
        )

        live_capable = tool.get(
            "live_capable",
            False,
        )

        needs_approval = tool.get(
            "requires_approval",
            False,
        )

        # --------------------------------------------------------------
        # SIMULATION MODE GATE
        # --------------------------------------------------------------

        if simulation_mode:

            if not simulation_safe:

                self.memory.log(
                    "ToolSystem",
                    (
                        f"BLOCKED simulation execution: "
                        f"{name} requested by {agent}"
                    ),
                    level="warning",
                )

                return {
                    "success": False,
                    "blocked": True,
                    "reason": "simulation_mode",
                    "error": (
                        f"Tool '{name}' is not permitted "
                        "in SIMULATION mode."
                    ),
                }

            # Simulation-safe tools execute without Creator approval.
            #
            # This includes research and simulated economy operations.
            if needs_approval:

                self.memory.log(
                    "ToolSystem",
                    (
                        f"Simulation execution: "
                        f"{name} by {agent}"
                    ),
                )

            else:

                self.memory.log(
                    "ToolSystem",
                    (
                        f"Simulation execution: "
                        f"{name} by {agent}"
                    ),
                )

        # --------------------------------------------------------------
        # LIVE MODE GATE
        # --------------------------------------------------------------

        if live_mode:

            # A tool that is explicitly live-capable is allowed to be
            # considered in LIVE mode.
            #
            # Approval is checked below if required.
            pass

        # --------------------------------------------------------------
        # NO ECONOMY / OPERATING MODE
        # --------------------------------------------------------------

        if (
            self.economy is not None
            and not simulation_mode
            and not live_mode
        ):
            return {
                "success": False,
                "blocked": True,
                "error": (
                    "No valid operating mode is active."
                ),
            }

        # --------------------------------------------------------------
        # LIVE-CAPABLE TOOL PROTECTION
        # --------------------------------------------------------------

        if live_mode and live_capable:

            # ----------------------------------------------------------
            # CREATOR APPROVAL REQUIRED
            # ----------------------------------------------------------

            if needs_approval:

                # ------------------------------------------------------
                # No approval supplied.
                #
                # Create a request instead of executing.
                # ------------------------------------------------------

                if approval_id is None:

                    description = (
                        action_description
                        or (
                            f"Agent '{agent}' requested "
                            f"execution of tool '{name}'."
                        )
                    )

                    approval = self.approvals.request(
                        action=name,
                        description=description,
                        parameters=kwargs,
                        agent=agent,
                        plan=plan or [],
                        risk=risk,
                    )

                    self.memory.log(
                        "ToolSystem",
                        (
                            f"Creator approval required: "
                            f"{name} by {agent} "
                            f"→ approval #{approval['id']}"
                        ),
                    )

                    return {
                        "success": False,
                        "requires_approval": True,
                        "approval_id": approval[
                            "id"
                        ],
                        "status": "pending",
                        "message": (
                            f"Creator approval required "
                            f"for '{name}'. "
                            f"Pending approval "
                            f"#{approval['id']}."
                        ),
                        "approval": approval,
                    }

                # ------------------------------------------------------
                # Approval ID supplied.
                # ------------------------------------------------------

                approval = self.approvals.get(
                    approval_id
                )

                if approval is None:

                    self.memory.log(
                        "ToolSystem",
                        (
                            f"Rejected invalid approval "
                            f"#{approval_id} for {name}"
                        ),
                        level="warning",
                    )

                    return {
                        "success": False,
                        "requires_approval": True,
                        "error": (
                            f"Approval #{approval_id} "
                            "does not exist."
                        ),
                    }

                # ------------------------------------------------------
                # Exact tool matching.
                # ------------------------------------------------------

                if approval.get(
                    "action"
                ) != name:

                    self.memory.log(
                        "ToolSystem",
                        (
                            f"Rejected approval "
                            f"#{approval_id}: tool mismatch"
                        ),
                        level="warning",
                    )

                    return {
                        "success": False,
                        "requires_approval": True,
                        "error": (
                            f"Approval #{approval_id} is for "
                            f"'{approval.get('action')}', "
                            f"not '{name}'."
                        ),
                    }

                # ------------------------------------------------------
                # Agent identity matching.
                #
                # An approval created for one agent cannot simply be
                # presented by another agent.
                # ------------------------------------------------------

                approved_agent = approval.get(
                    "agent"
                )

                if (
                    approved_agent
                    and approved_agent != agent
                ):

                    self.memory.log(
                        "ToolSystem",
                        (
                            f"Rejected approval "
                            f"#{approval_id}: agent mismatch "
                            f"({agent} != {approved_agent})"
                        ),
                        level="warning",
                    )

                    return {
                        "success": False,
                        "requires_approval": True,
                        "error": (
                            f"Approval #{approval_id} belongs "
                            f"to agent '{approved_agent}', "
                            f"not '{agent}'."
                        ),
                    }

                # ------------------------------------------------------
                # Approval status.
                # ------------------------------------------------------

                if approval.get(
                    "status"
                ) != "approved":

                    return {
                        "success": False,
                        "requires_approval": True,
                        "approval_id": approval_id,
                        "status": approval.get(
                            "status"
                        ),
                        "error": (
                            f"Approval #{approval_id} "
                            "is not approved."
                        ),
                    }

                # ------------------------------------------------------
                # Consume BEFORE execution.
                #
                # This is deliberately before the actual operation.
                # If the operation is attempted twice, the second
                # attempt cannot reuse the same approval.
                # ------------------------------------------------------

                consumed = (
                    self.approvals.consume_approval(
                        approval_id
                    )
                )

                if not consumed:

                    return {
                        "success": False,
                        "requires_approval": True,
                        "approval_id": approval_id,
                        "error": (
                            f"Approval #{approval_id} "
                            "could not be consumed."
                        ),
                    }

                self.memory.log(
                    "ToolSystem",
                    (
                        f"Consumed Creator approval "
                        f"#{approval_id} for {name}"
                    ),
                )

        # --------------------------------------------------------------
        # LIVE MODE + NON-LIVE-CAPABLE TOOL
        # --------------------------------------------------------------

        if live_mode and not live_capable:

            # Normal internal/research tools are allowed.
            #
            # A tool does not need to be marked live-capable merely
            # because the application itself is running in LIVE mode.
            pass

        # --------------------------------------------------------------
        # EXECUTE TOOL
        # --------------------------------------------------------------

        try:

            result = tool["func"](
                **kwargs
            )

            self.memory.log(
                "ToolSystem",
                (
                    f"Executed tool: {name} "
                    f"by {agent}"
                ),
            )

            return {
                "success": True,
                "result": result,
                "tool": name,
                "agent": agent,
                "mode": (
                    self.economy.get_mode()
                    if self.economy
                    else "unknown"
                ),
            }

        except Exception as e:

            error_message = str(e)

            self.memory.log(
                "ToolSystem",
                (
                    f"Tool {name} failed: "
                    f"{error_message}"
                ),
                level="error",
            )

            # If a Creator-approved real-world action failed after
            # approval was consumed, permanently record that execution
            # attempt as failed.
            if (
                needs_approval
                and live_mode
                and approval_id is not None
            ):

                self.approvals.reject_execution(
                    approval_id
                )

            return {
                "success": False,
                "error": error_message,
                "tool": name,
                "agent": agent,
            }


# ----------------------------------------------------------------------
# DEFAULT TOOL SET
# ----------------------------------------------------------------------

def create_default_tools(
    memory: SharedMemory,
    world,
    economy: Economy = None,
    research: WebResearch = None,
) -> ToolRegistry:
    """
    Build the default ToolRegistry.

    Existing functionality is preserved.

    New capabilities can be registered here later without changing
    the agent architecture.
    """

    registry = ToolRegistry(
        memory=memory,
        economy=economy,
        research=research,
    )

    # ------------------------------------------------------------------
    # BASIC MEMORY / WORLD TOOLS
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
        "Write a log message",
        log_message,
        simulation_safe=True,
        category="internal",
    )

    registry.register(
        "farm_info",
        "Farm information on a topic",
        farm_info,
        simulation_safe=True,
        category="research",
    )

    registry.register(
        "check_balance",
        "Check current money balance",
        check_balance,
        simulation_safe=True,
        category="finance",
    )

    registry.register(
        "create_task",
        "Create a new task for an agent",
        create_task,
        simulation_safe=True,
        category="coordination",
    )

    # ------------------------------------------------------------------
    # ECONOMY TOOLS
    # ------------------------------------------------------------------

    if economy:

        def money_mode(
            mode: str = None,
        ):
            """
            Return the current mode.

            Agents are NOT permitted to change the operating mode.

            Mode changes belong to the Creator control/API layer.
            """

            if mode is not None:

                memory.log(
                    "ToolSystem",
                    (
                        "Blocked agent attempt to "
                        f"change operating mode to '{mode}'."
                    ),
                    level="warning",
                )

                return {
                    "success": False,
                    "blocked": True,
                    "reason": "creator_controlled",
                    "error": (
                        "Operating mode is Creator-controlled. "
                        "Use the Creator control panel/API "
                        "to change SIMULATION or LIVE mode."
                    ),
                    "current_mode": (
                        economy.get_mode()
                    ),
                }

            return {
                "mode": economy.get_mode(),
                "policy": (
                    economy.get_mode_policy()
                    if hasattr(
                        economy,
                        "get_mode_policy",
                    )
                    else {}
                ),
            }

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
            status: str = None,
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
            "Read the current economy mode and safety policy",
            money_mode,
            simulation_safe=True,
            category="system",
        )

        registry.register(
            "find_opportunity",
            "Create a new simulated or recorded business opportunity",
            find_opportunity,
            simulation_safe=True,
            category="economy",
        )

        registry.register(
            "analyse_opportunity",
            "Analyse an opportunity",
            analyse_opportunity,
            simulation_safe=True,
            category="analysis",
        )

        registry.register(
            "list_opportunities",
            "List opportunities",
            list_opportunities,
            simulation_safe=True,
            category="economy",
        )

        # Starting an experiment may eventually represent a real
        # financial commitment. It therefore remains protected when
        # the system is operating in LIVE mode.
        #
        # In SIMULATION mode it is allowed because the Economy
        # performs a simulated experiment.
        registry.register(
            "create_experiment",
            "Start an economic experiment",
            create_experiment,
            requires_approval=True,
            live_capable=True,
            simulation_safe=True,
            category="financial",
        )

        # Completing an experiment can record real-world revenue or
        # expenses, therefore it remains protected in LIVE mode.
        registry.register(
            "complete_experiment",
            "Complete an economic experiment",
            complete_experiment,
            requires_approval=True,
            live_capable=True,
            simulation_safe=True,
            category="financial",
        )

        registry.register(
            "economy_report",
            "Full economy report",
            economy_report,
            simulation_safe=True,
            category="economy",
        )

    # ------------------------------------------------------------------
    # WEB RESEARCH TOOLS
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

        # --------------------------------------------------------------
        # PUBLIC INTERNET RESEARCH
        # --------------------------------------------------------------
        #
        # These tools intentionally DO NOT require Creator approval.
        #
        # The agents need broad research capability so they can:
        #
        #   research
        #   compare
        #   investigate
        #   analyse
        #   discover opportunities
        #   gather evidence
        #   prepare plans
        #
        # Research is read-only.
        #
        # It does not grant permission to perform external actions.
        # --------------------------------------------------------------

        registry.register(
            "web_search",
            "Search the public internet for information",
            web_search,
            requires_approval=False,
            live_capable=False,
            simulation_safe=True,
            category="research",
        )

        registry.register(
            "read_webpage",
            "Read publicly accessible webpage content",
            read_webpage,
            requires_approval=False,
            live_capable=False,
            simulation_safe=True,
            category="research",
        )

    return registry
