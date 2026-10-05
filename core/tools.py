"""
Tool Registry and Capability Control

The ToolRegistry is the security boundary between autonomous agents
and executable capabilities.

Agents may reason, research, plan and propose actions autonomously.

Every actual tool execution passes through this registry.

Capability classes:

INTERNAL
    Local simulation/application functionality.

RESEARCH
    Public internet read/search functionality.
    Research does not require Creator approval.

LIVE
    Tools capable of affecting external systems.

PROTECTED
    Consequential live actions requiring explicit Creator approval.

Operating modes:

SIMULATION
    Simulation-safe tools may execute.
    Non-simulation-safe tools are blocked.

LIVE
    Research/internal tools may execute autonomously.
    Protected consequential tools require Creator approval.

IMPORTANT:

LIVE does NOT mean unrestricted.

The Creator approval is tied to:
    - specific tool
    - specific agent
    - specific parameters
    - specific approval request

An approval is consumed before execution and cannot be reused.
"""

from typing import (
    Any,
    Callable,
    Dict,
    List,
    Optional,
)

from datetime import datetime

from .memory import SharedMemory
from .economy import Economy
from .research import WebResearch
from .approvals import ApprovalGate


class ToolRegistry:
    """
    Central capability registry and execution boundary.

    The cognitive layer can inspect this registry and propose tool
    usage, but it cannot bypass this class to execute tools.
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

        self.tools: Dict[
            str,
            Dict[str, Any],
        ] = {}

        self.approvals = ApprovalGate(
            self.memory
        )

    # ==================================================================
    # TOOL REGISTRATION
    # ==================================================================

    def register(
        self,
        name: str,
        description: str,
        func: Callable,
        requires_approval: bool = False,
        live_capable: bool = False,
        simulation_safe: bool = True,
        category: str = "general",
        risk: str = "low",
        autonomous: bool = True,
        parameter_names: Optional[
            List[str]
        ] = None,
    ) -> None:
        """
        Register a capability.

        Parameters
        ----------
        name:
            Unique tool identifier.

        description:
            Human/machine-readable explanation.

        func:
            Actual Python callable.

        requires_approval:
            Whether consequential LIVE execution requires Creator
            approval.

        live_capable:
            Whether the tool can affect/interact with the external
            world.

        simulation_safe:
            Whether the tool may execute while in SIMULATION mode.

        category:
            Capability category.

        risk:
            Default risk classification.

        autonomous:
            Whether agents may call the tool without an external
            human initiating the operation.

        parameter_names:
            Optional description of accepted parameters for future
            structured reasoning/tool selection.
        """

        if not name:
            raise ValueError(
                "Tool name cannot be empty."
            )

        if not callable(func):
            raise TypeError(
                f"Tool '{name}' must provide a callable."
            )

        # A protected action must be live-capable.
        if requires_approval:
            live_capable = True

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
            "category": category,
            "risk": risk,
            "autonomous": bool(
                autonomous
            ),
            "parameter_names": (
                parameter_names or []
            ),
        }

    # ==================================================================
    # TOOL LOOKUP
    # ==================================================================

    def get_tool(
        self,
        name: str,
    ) -> Optional[Dict[str, Any]]:
        return self.tools.get(name)

    def list_tools(
        self,
    ) -> List[Dict[str, Any]]:
        """
        Return safe/public tool definitions.

        The executable Python callable is deliberately omitted.
        """

        definitions = []

        for tool in self.tools.values():
            definitions.append(
                {
                    "name": tool["name"],
                    "description": tool[
                        "description"
                    ],
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
                    "risk": tool[
                        "risk"
                    ],
                    "autonomous": tool[
                        "autonomous"
                    ],
                    "parameter_names": tool[
                        "parameter_names"
                    ],
                }
            )

        return definitions

    def get_capabilities(
        self,
    ) -> List[Dict[str, Any]]:
        """
        Return the public capability map.

        This is intended for:
            - agent reasoning
            - future LLM tool selection
            - UI inspection
            - diagnostics
        """

        return self.list_tools()

    # ==================================================================
    # MODE / CAPABILITY POLICY
    # ==================================================================

    def get_current_mode(
        self,
    ) -> str:
        """
        Return the current operating mode.
        """

        if self.economy is None:
            return "simulation"

        try:
            return self.economy.get_mode()
        except Exception:
            return "simulation"

    def can_execute_in_current_mode(
        self,
        tool: Dict[str, Any],
    ) -> bool:
        """
        Determine whether the tool is permitted by operating mode.

        This does NOT grant Creator approval.

        It only answers:

            "Is this capability allowed to operate in this mode?"
        """

        mode = self.get_current_mode()

        if mode == "simulation":
            return bool(
                tool.get(
                    "simulation_safe",
                    True,
                )
            )

        if mode == "real":
            return True

        return False

    # ==================================================================
    # APPROVAL HELPERS
    # ==================================================================

    @staticmethod
    def _normalise_parameters(
        parameters: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Normalise action parameters for comparison/storage.

        The approval system needs to know exactly what the Creator
        approved.
        """

        if not parameters:
            return {}

        return dict(parameters)

    def _parameters_match(
        self,
        approved: Optional[Dict[str, Any]],
        requested: Optional[Dict[str, Any]],
    ) -> bool:
        """
        Verify that execution parameters exactly match the parameters
        presented to the Creator.

        This prevents:

            approved action A
                  ↓
            modified action B
                  ↓
            reuse of approval
        """

        approved = self._normalise_parameters(
            approved
        )

        requested = self._normalise_parameters(
            requested
        )

        return approved == requested

    def _create_approval_request(
        self,
        name: str,
        agent: str,
        parameters: Dict[str, Any],
        action_description: Optional[str],
        plan: Optional[List[str]],
        risk: str,
    ) -> Dict[str, Any]:
        """
        Create a Creator approval request.
        """

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
            parameters=parameters,
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

        return approval

    # ==================================================================
    # TOOL EXECUTION
    # ==================================================================

    def execute(
        self,
        name: str,
        approval_id: Optional[int] = None,
        agent: str = "Unknown",
        action_description: Optional[str] = None,
        plan: Optional[List[str]] = None,
        risk: Optional[str] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Execute a registered capability.

        Policy:

        SIMULATION
        ----------
        simulation_safe=True:
            Execute.

        simulation_safe=False:
            Block.

        LIVE
        ----
        normal/internal/research tool:
            Execute.

        protected live tool:
            No approval supplied:
                Create pending Creator approval.

            Approved approval:
                Verify tool, agent and parameters.
                Consume approval.
                Execute once.

            Any other state:
                Block.

        Approval is never reusable.
        """

        tool = self.get_tool(name)

        if tool is None:
            return {
                "success": False,
                "blocked": True,
                "error": (
                    f"Tool '{name}' not found."
                ),
            }

        mode = self.get_current_mode()

        simulation_mode = (
            mode == "simulation"
        )

        live_mode = (
            mode == "real"
        )

        parameters = (
            self._normalise_parameters(
                kwargs
            )
        )

        effective_risk = (
            risk
            or tool.get(
                "risk",
                "low",
            )
        )

        simulation_safe = bool(
            tool.get(
                "simulation_safe",
                True,
            )
        )

        live_capable = bool(
            tool.get(
                "live_capable",
                False,
            )
        )

        requires_approval = bool(
            tool.get(
                "requires_approval",
                False,
            )
        )

        # --------------------------------------------------------------
        # VALID OPERATING MODE
        # --------------------------------------------------------------

        if mode not in {
            "simulation",
            "real",
        }:

            self.memory.log(
                "ToolSystem",
                (
                    f"Blocked {name}: "
                    "invalid operating mode."
                ),
                level="warning",
            )

            return {
                "success": False,
                "blocked": True,
                "reason": "invalid_mode",
                "error": (
                    "No valid operating mode is active."
                ),
            }

        # --------------------------------------------------------------
        # SIMULATION MODE
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

            self.memory.log(
                "ToolSystem",
                (
                    f"Simulation execution: "
                    f"{name} by {agent}"
                ),
            )

        # --------------------------------------------------------------
        # LIVE MODE
        # --------------------------------------------------------------

        if live_mode:

            # ----------------------------------------------------------
            # Non-live-capable tools
            # ----------------------------------------------------------

            if not live_capable:

                self.memory.log(
                    "ToolSystem",
                    (
                        f"Live execution of autonomous "
                        f"non-live tool: {name} "
                        f"by {agent}"
                    ),
                )

            # ----------------------------------------------------------
            # LIVE-CAPABLE TOOL
            # ----------------------------------------------------------

            if live_capable:

                # ------------------------------------------------------
                # UNPROTECTED LIVE CAPABILITY
                # ------------------------------------------------------

                if not requires_approval:

                    self.memory.log(
                        "ToolSystem",
                        (
                            f"Live-capable autonomous tool: "
                            f"{name} by {agent}"
                        ),
                    )

                # ------------------------------------------------------
                # CREATOR-PROTECTED ACTION
                # ------------------------------------------------------

                else:

                    # ==================================================
                    # CREATE APPROVAL
                    # ==================================================

                    if approval_id is None:

                        approval = (
                            self._create_approval_request(
                                name=name,
                                agent=agent,
                                parameters=parameters,
                                action_description=(
                                    action_description
                                ),
                                plan=plan,
                                risk=effective_risk,
                            )
                        )

                        return {
                            "success": False,
                            "requires_approval": True,
                            "approval_id": (
                                approval["id"]
                            ),
                            "status": "pending",
                            "message": (
                                f"Creator approval required "
                                f"for '{name}'. "
                                f"Pending approval "
                                f"#{approval['id']}."
                            ),
                            "approval": approval,
                        }

                    # ==================================================
                    # LOOK UP APPROVAL
                    # ==================================================

                    approval = (
                        self.approvals.get(
                            approval_id
                        )
                    )

                    if approval is None:

                        self.memory.log(
                            "ToolSystem",
                            (
                                f"Rejected invalid "
                                f"approval #{approval_id} "
                                f"for {name}"
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

                    # ==================================================
                    # TOOL MATCH
                    # ==================================================

                    if approval.get(
                        "action"
                    ) != name:

                        self.memory.log(
                            "ToolSystem",
                            (
                                f"Rejected approval "
                                f"#{approval_id}: "
                                "tool mismatch"
                            ),
                            level="warning",
                        )

                        return {
                            "success": False,
                            "requires_approval": True,
                            "error": (
                                f"Approval #{approval_id} "
                                f"is for "
                                f"'{approval.get('action')}', "
                                f"not '{name}'."
                            ),
                        }

                    # ==================================================
                    # AGENT MATCH
                    # ==================================================

                    approved_agent = (
                        approval.get(
                            "agent"
                        )
                    )

                    if (
                        approved_agent
                        and approved_agent != agent
                    ):

                        self.memory.log(
                            "ToolSystem",
                            (
                                f"Rejected approval "
                                f"#{approval_id}: "
                                f"agent mismatch "
                                f"({agent} != "
                                f"{approved_agent})"
                            ),
                            level="warning",
                        )

                        return {
                            "success": False,
                            "requires_approval": True,
                            "error": (
                                f"Approval #{approval_id} "
                                f"belongs to agent "
                                f"'{approved_agent}', "
                                f"not '{agent}'."
                            ),
                        }

                    # ==================================================
                    # PARAMETER MATCH
                    # ==================================================

                    approved_parameters = (
                        approval.get(
                            "parameters",
                            {},
                        )
                    )

                    if not self._parameters_match(
                        approved_parameters,
                        parameters,
                    ):

                        self.memory.log(
                            "ToolSystem",
                            (
                                f"Rejected approval "
                                f"#{approval_id}: "
                                "parameter mismatch"
                            ),
                            level="warning",
                        )

                        return {
                            "success": False,
                            "requires_approval": True,
                            "error": (
                                f"Approval #{approval_id} "
                                "does not match the "
                                "requested action parameters."
                            ),
                            "approved_parameters": (
                                approved_parameters
                            ),
                            "requested_parameters": (
                                parameters
                            ),
                        }

                    # ==================================================
                    # RISK MATCH
                    # ==================================================

                    approved_risk = (
                        approval.get(
                            "risk",
                            "medium",
                        )
                    )

                    if (
                        approved_risk
                        != effective_risk
                    ):

                        self.memory.log(
                            "ToolSystem",
                            (
                                f"Rejected approval "
                                f"#{approval_id}: "
                                "risk mismatch"
                            ),
                            level="warning",
                        )

                        return {
                            "success": False,
                            "requires_approval": True,
                            "error": (
                                f"Approval #{approval_id} "
                                "does not match the "
                                "requested risk level."
                            ),
                        }

                    # ==================================================
                    # APPROVAL STATUS
                    # ==================================================

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

                    # ==================================================
                    # CONSUME APPROVAL
                    # ==================================================

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
        # EXECUTE
        # --------------------------------------------------------------

        execution_started = False

        try:

            execution_started = True

            result = tool["func"](
                **parameters
            )

            self.memory.log(
                "ToolSystem",
                (
                    f"Executed tool '{name}' "
                    f"by {agent} "
                    f"[{mode.upper()}]"
                ),
            )

            return {
                "success": True,
                "result": result,
                "tool": name,
                "agent": agent,
                "mode": mode,
                "live_capable": live_capable,
                "requires_approval": (
                    requires_approval
                ),
                "executed_at": (
                    datetime.utcnow().isoformat()
                ),
            }

        except Exception as exc:

            error_message = str(exc)

            self.memory.log(
                "ToolSystem",
                (
                    f"Tool '{name}' failed: "
                    f"{error_message}"
                ),
                level="error",
            )

            # An approved protected action has already consumed its
            # approval. Record that the execution attempt failed.
            if (
                execution_started
                and requires_approval
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
                "mode": mode,
            }


# ==================================================================
# DEFAULT TOOLS
# ==================================================================

def create_default_tools(
    memory: SharedMemory,
    world,
    economy: Economy = None,
    research: WebResearch = None,
) -> ToolRegistry:
    """
    Construct the default ToolRegistry.

    Existing project functionality is preserved.

    New external capabilities can be registered here later.
    """

    registry = ToolRegistry(
        memory=memory,
        economy=economy,
        research=research,
    )

    # ================================================================
    # INTERNAL / COORDINATION TOOLS
    # ================================================================

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
        name="log",
        description="Write a system log message",
        func=log_message,
        simulation_safe=True,
        category="internal",
        risk="low",
        autonomous=True,
        parameter_names=[
            "agent",
            "message",
        ],
    )

    registry.register(
        name="farm_info",
        description="Research and store information on a topic",
        func=farm_info,
        simulation_safe=True,
        category="research",
        risk="low",
        autonomous=True,
        parameter_names=[
            "topic",
            "agent",
        ],
    )

    registry.register(
        name="check_balance",
        description="Read the current Banker balance",
        func=check_balance,
        simulation_safe=True,
        category="finance",
        risk="low",
        autonomous=True,
        parameter_names=[],
    )

    registry.register(
        name="create_task",
        description="Create a task for another agent",
        func=create_task,
        simulation_safe=True,
        category="coordination",
        risk="low",
        autonomous=True,
        parameter_names=[
            "title",
            "description",
            "assigned_to",
        ],
    )

    # ================================================================
    # ECONOMY
    # ================================================================

    if economy:

        def money_mode(
            mode: str = None,
        ):
            """
            Read economy mode.

            Agent processes cannot change operating mode.

            The Creator control/API layer owns this decision.
            """

            if mode is not None:

                memory.log(
                    "ToolSystem",
                    (
                        "Blocked agent attempt to "
                        f"change operating mode "
                        f"to '{mode}'."
                    ),
                    level="warning",
                )

                return {
                    "success": False,
                    "blocked": True,
                    "reason": "creator_controlled",
                    "error": (
                        "Operating mode is "
                        "Creator-controlled. "
                        "Use the Creator control "
                        "panel/API."
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
            name="money_mode",
            description=(
                "Read the current economy operating mode "
                "and policy"
            ),
            func=money_mode,
            simulation_safe=True,
            category="system",
            risk="low",
            autonomous=True,
            parameter_names=[
                "mode",
            ],
        )

        registry.register(
            name="find_opportunity",
            description=(
                "Create a simulated or recorded "
                "business opportunity"
            ),
            func=find_opportunity,
            simulation_safe=True,
            category="economy",
            risk="low",
            autonomous=True,
            parameter_names=[
                "name",
                "description",
                "startup_cost",
                "expected_expenses",
                "expected_revenue",
                "risk",
            ],
        )

        registry.register(
            name="analyse_opportunity",
            description="Analyse an economic opportunity",
            func=analyse_opportunity,
            simulation_safe=True,
            category="analysis",
            risk="low",
            autonomous=True,
            parameter_names=[
                "opp_id",
            ],
        )

        registry.register(
            name="list_opportunities",
            description="List known economic opportunities",
            func=list_opportunities,
            simulation_safe=True,
            category="economy",
            risk="low",
            autonomous=True,
            parameter_names=[
                "status",
            ],
        )

        # ------------------------------------------------------------
        # Protected financial operation.
        #
        # Simulation:
        #     allowed without approval.
        #
        # LIVE:
        #     Creator approval required.
        # ------------------------------------------------------------

        registry.register(
            name="create_experiment",
            description=(
                "Start an economic experiment that may "
                "consume a financial budget"
            ),
            func=create_experiment,
            requires_approval=True,
            live_capable=True,
            simulation_safe=True,
            category="financial",
            risk="medium",
            autonomous=True,
            parameter_names=[
                "opp_id",
                "budget",
                "notes",
            ],
        )

        registry.register(
            name="complete_experiment",
            description=(
                "Complete an economic experiment and "
                "record revenue and expenses"
            ),
            func=complete_experiment,
            requires_approval=True,
            live_capable=True,
            simulation_safe=True,
            category="financial",
            risk="medium",
            autonomous=True,
            parameter_names=[
                "exp_id",
                "revenue",
                "extra_expenses",
                "notes",
            ],
        )

        registry.register(
            name="economy_report",
            description="Read the complete economy report",
            func=economy_report,
            simulation_safe=True,
            category="economy",
            risk="low",
            autonomous=True,
            parameter_names=[],
        )

    # ================================================================
    # PUBLIC INTERNET RESEARCH
    # ================================================================

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

        # ------------------------------------------------------------
        # PUBLIC RESEARCH IS AUTONOMOUS.
        #
        # These capabilities:
        #
        #   search
        #   read
        #   investigate
        #   compare
        #   gather evidence
        #
        # do not themselves create external side effects.
        #
        # They therefore do not require Creator approval.
        # ------------------------------------------------------------

        registry.register(
            name="web_search",
            description=(
                "Search the public internet for "
                "information and research"
            ),
            func=web_search,
            requires_approval=False,
            live_capable=False,
            simulation_safe=True,
            category="research",
            risk="low",
            autonomous=True,
            parameter_names=[
                "query",
                "max_results",
            ],
        )

        registry.register(
            name="read_webpage",
            description=(
                "Read publicly accessible webpage "
                "content"
            ),
            func=read_webpage,
            requires_approval=False,
            live_capable=False,
            simulation_safe=True,
            category="research",
            risk="low",
            autonomous=True,
            parameter_names=[
                "url",
            ],
        )

    return registry
