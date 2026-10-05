"""
Base Tool System + Economic Tools + Web Research Tools
-------------------------------------------------------

The ToolRegistry provides a controlled interface between autonomous
agents and the capabilities available to them.

Tools may be:

    - Fully autonomous
    - Creator approval required

For approval-required tools operating in real economy mode, the agent
must first create an approval request. The Creator then approves or
denies that specific request.

An approval cannot be reused after execution begins.
"""

from typing import Dict, Any, Callable, Optional, List

from .memory import SharedMemory
from .economy import Economy
from .research import WebResearch
from .approvals import ApprovalGate


class ToolRegistry:
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
        self.approvals = ApprovalGate(self.memory)

    # ------------------------------------------------------------------
    # TOOL REGISTRATION
    # ------------------------------------------------------------------

    def register(
        self,
        name: str,
        description: str,
        func: Callable,
        requires_approval: bool = False,
    ):
        """
        Register a tool.

        requires_approval=True means the tool is considered a
        consequential action when running in real economy mode.
        """

        self.tools[name] = {
            "name": name,
            "description": description,
            "func": func,
            "requires_approval": requires_approval,
        }

    def get_tool(
        self,
        name: str,
    ) -> Optional[Dict]:
        return self.tools.get(name)

    def list_tools(self) -> List[Dict[str, Any]]:
        """
        Return the public tool definitions.

        The callable itself is deliberately not exposed.
        """

        return [
            {
                "name": tool["name"],
                "description": tool["description"],
                "requires_approval": tool["requires_approval"],
            }
            for tool in self.tools.values()
        ]

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

        For approval-required tools in real economy mode:

            1. No approval ID -> create a pending approval request.
            2. Pending approval -> refuse execution.
            3. Denied approval -> refuse execution.
            4. Approved approval -> consume approval and execute once.
            5. Consumed approval -> refuse reuse.

        This prevents an agent from bypassing Creator approval by simply
        setting a boolean flag.
        """

        tool = self.get_tool(name)

        if not tool:
            return {
                "success": False,
                "error": f"Tool '{name}' not found",
            }

        needs_approval = tool["requires_approval"]

        real_mode = bool(
            self.economy
            and self.economy.is_real()
        )

        # --------------------------------------------------------------
        # CREATOR APPROVAL GATE
        # --------------------------------------------------------------

        if needs_approval and real_mode:

            # No approval supplied.
            #
            # Create a request for the Creator instead of executing.
            if approval_id is None:

                description = (
                    action_description
                    or f"Agent '{agent}' requested execution of tool '{name}'."
                )

                approval = self.approvals.request(
                    action=name,
                    description=description,
                    parameters=kwargs,
                    agent=agent,
                    plan=plan or [],
                    risk=risk,
                )

                return {
                    "success": False,
                    "requires_approval": True,
                    "approval_id": approval["id"],
                    "status": "pending",
                    "message": (
                        f"Creator approval required for '{name}'. "
                        f"Pending approval #{approval['id']}."
                    ),
                    "approval": approval,
                }

            # ----------------------------------------------------------
            # APPROVAL ID PROVIDED
            # ----------------------------------------------------------

            approval = self.approvals.get(approval_id)

            if approval is None:
                return {
                    "success": False,
                    "requires_approval": True,
                    "error": (
                        f"Approval #{approval_id} does not exist."
                    ),
                }

            # Make sure the approval belongs to this exact tool.
            if approval.get("action") != name:
                return {
                    "success": False,
                    "requires_approval": True,
                    "error": (
                        f"Approval #{approval_id} is for "
                        f"'{approval.get('action')}', not '{name}'."
                    ),
                }

            # The Creator has not approved it.
            if approval.get("status") != "approved":
                return {
                    "success": False,
                    "requires_approval": True,
                    "approval_id": approval_id,
                    "status": approval.get("status"),
                    "error": (
                        f"Approval #{approval_id} is not approved."
                    ),
                }

            # Consume the approval BEFORE executing the real-world
            # operation so the same approval cannot be reused.
            consumed = self.approvals.consume_approval(
                approval_id
            )

            if not consumed:
                return {
                    "success": False,
                    "requires_approval": True,
                    "approval_id": approval_id,
                    "error": (
                        f"Approval #{approval_id} could not be consumed."
                    ),
                }

        # --------------------------------------------------------------
        # EXECUTE TOOL
        # --------------------------------------------------------------

        try:
            result = tool["func"](**kwargs)

            self.memory.log(
                "ToolSystem",
                f"Executed tool: {name}",
            )

            return {
                "success": True,
                "result": result,
            }

        except Exception as e:

            error_message = str(e)

            self.memory.log(
                "ToolSystem",
                f"Tool {name} failed: {error_message}",
                level="error",
            )

            # If a Creator-approved real-world action failed after its
            # approval was consumed, record the failed execution.
            if (
                needs_approval
                and real_mode
                and approval_id is not None
            ):
                self.approvals.reject_execution(
                    approval_id
                )

            return {
                "success": False,
                "error": error_message,
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
    Build the default ToolRegistry used by the simulation.

    Existing functionality is preserved here. New capabilities can be
    registered later without changing the agent architecture.
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

        return f"Logged: {message}"

    def farm_info(
        topic: str,
        agent: str = "InfoFarmer",
    ):
        content = (
            f"Gathered basic information about '{topic}'."
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
    )

    registry.register(
        "farm_info",
        "Farm information on a topic",
        farm_info,
    )

    registry.register(
        "check_balance",
        "Check current money balance",
        check_balance,
    )

    registry.register(
        "create_task",
        "Create a new task for an agent",
        create_task,
    )

    # ------------------------------------------------------------------
    # ECONOMY TOOLS
    # ------------------------------------------------------------------

    if economy:

        def money_mode(
            mode: str = None,
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
            "Get or set economy mode",
            money_mode,
        )

        registry.register(
            "find_opportunity",
            "Create a new opportunity",
            find_opportunity,
        )

        registry.register(
            "analyse_opportunity",
            "Analyse an opportunity",
            analyse_opportunity,
        )

        registry.register(
            "list_opportunities",
            "List opportunities",
            list_opportunities,
        )

        # Starting an experiment can potentially involve real money,
        # therefore it remains protected.
        registry.register(
            "create_experiment",
            "Start an experiment",
            create_experiment,
            requires_approval=True,
        )

        # Completing an experiment can record real-world revenue or
        # expenses, therefore it remains protected.
        registry.register(
            "complete_experiment",
            "Complete an experiment",
            complete_experiment,
            requires_approval=True,
        )

        registry.register(
            "economy_report",
            "Full economy report",
            economy_report,
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

        # Public research does not require Creator approval.
        #
        # Agents need to be able to research independently before
        # presenting a real-world action plan to the Creator.
        registry.register(
            "web_search",
            "Search the web for information",
            web_search,
        )

        registry.register(
            "read_webpage",
            "Read the content of a public webpage",
            read_webpage,
        )

    return registry



