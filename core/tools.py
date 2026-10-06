"""
Tool Registry
-------------
Central capability layer for all agents.

Every tool declares:
- whether it is safe in simulation
- whether it can operate in real mode
- whether Creator approval is required

Consequential actions can never bypass the registry approval gate.
"""

from typing import Any, Callable, Dict, List, Optional

from .approvals import ApprovalGate


class ToolRegistry:
    def __init__(
        self,
        memory,
        economy=None,
    ):
        self.memory = memory
        self.economy = economy
        self.approval_gate = ApprovalGate(memory)
        self._tools: Dict[str, Dict[str, Any]] = {}

    # -----------------------------------------------------------------
    # Registration
    # -----------------------------------------------------------------

    def register(
        self,
        name: str,
        function: Callable,
        description: str = "",
        simulation_safe: bool = True,
        live_capable: bool = False,
        protected: bool = False,
    ) -> Dict[str, Any]:
        name = (name or "").strip()

        if not name:
            raise ValueError(
                "Tool name is required."
            )

        if not callable(function):
            raise TypeError(
                f"Tool '{name}' must be callable."
            )

        self._tools[name] = {
            "name": name,
            "function": function,
            "description": description,
            "simulation_safe": bool(
                simulation_safe
            ),
            "live_capable": bool(
                live_capable
            ),
            "protected": bool(
                protected
            ),
        }

        return {
            "status": "success",
            "tool": name,
        }

    def unregister(
        self,
        name: str,
    ) -> Dict[str, Any]:
        if name not in self._tools:
            return {
                "status": "error",
                "message": f"Unknown tool: {name}",
            }

        del self._tools[name]

        return {
            "status": "success",
            "tool": name,
        }

    # -----------------------------------------------------------------
    # Discovery
    # -----------------------------------------------------------------

    def get(
        self,
        name: str,
    ) -> Optional[Dict[str, Any]]:
        return self._tools.get(name)

    def list_tools(self) -> List[Dict[str, Any]]:
        result = []

        for name, tool in sorted(
            self._tools.items()
        ):
            result.append(
                self._public_tool(tool)
            )

        return result

    def capabilities(self) -> Dict[str, Any]:
        return {
            "status": "success",
            "tools": self.list_tools(),
            "simulation": [
                name
                for name, tool in self._tools.items()
                if tool["simulation_safe"]
            ],
            "live_capable": [
                name
                for name, tool in self._tools.items()
                if tool["live_capable"]
            ],
            "protected": [
                name
                for name, tool in self._tools.items()
                if tool["protected"]
            ],
        }

    # -----------------------------------------------------------------
    # Mode
    # -----------------------------------------------------------------

    def get_mode(self) -> str:
        if self.economy is not None:
            try:
                return self.economy.get_mode()
            except Exception:
                pass

        try:
            state = self.memory.get_world_state()
            return state.get(
                "economy_mode",
                "simulation",
            )
        except Exception:
            return "simulation"

    def is_simulation(self) -> bool:
        return self.get_mode() == "simulation"

    def is_real(self) -> bool:
        return self.get_mode() == "real"

    # -----------------------------------------------------------------
    # Approval
    # -----------------------------------------------------------------

    def request_approval(
        self,
        agent: str,
        tool: str,
        reason: str,
        payload: Optional[Dict[str, Any]] = None,
        risk: str = "medium",
        plan: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        if payload is None:
            payload = {}

        if plan is None:
            plan = []

        result = self.approval_gate.request(
            agent=agent,
            tool=tool,
            reason=reason,
            risk=risk,
            payload=payload,
            plan=plan,
        )

        return {
            "status": "approval_required",
            "approval_id": result.get(
                "id"
            ),
            "agent": agent,
            "tool": tool,
            "reason": reason,
            "risk": risk,
            "parameters": payload,
            "message": (
                "Creator approval is required "
                "before this exact action can "
                "execute."
            ),
        }

    # -----------------------------------------------------------------
    # Execution
    # -----------------------------------------------------------------

    def execute(
        self,
        tool_name: str,
        agent: str = "System",
        approval_id: str = "",
        **kwargs,
    ) -> Dict[str, Any]:
        tool = self._tools.get(tool_name)

        if tool is None:
            return {
                "status": "error",
                "tool": tool_name,
                "message": (
                    f"Unknown tool: {tool_name}"
                ),
            }

        mode = self.get_mode()

        # -------------------------------------------------------------
        # Simulation protection
        # -------------------------------------------------------------

        if (
            mode == "simulation"
            and not tool["simulation_safe"]
        ):
            return {
                "status": "blocked",
                "tool": tool_name,
                "agent": agent,
                "message": (
                    "This tool is not available "
                    "in simulation mode."
                ),
                "mode": mode,
            }

        # -------------------------------------------------------------
        # Real-mode capability protection
        # -------------------------------------------------------------

        if (
            mode == "real"
            and not tool["live_capable"]
        ):
            return {
                "status": "blocked",
                "tool": tool_name,
                "agent": agent,
                "message": (
                    "This tool is not enabled "
                    "for real mode."
                ),
                "mode": mode,
            }

        # -------------------------------------------------------------
        # Protected action
        # -------------------------------------------------------------

        if tool["protected"]:
            if not approval_id:
                return self.request_approval(
                    agent=agent,
                    tool=tool_name,
                    reason=(
                        f"Agent requested protected "
                        f"tool '{tool_name}'."
                    ),
                    payload=kwargs,
                    risk="high",
                    plan=[
                        "Validate requested action.",
                        "Obtain exact Creator approval.",
                        "Execute approved action once.",
                        "Record execution result.",
                    ],
                )

            validation = (
                self.approval_gate.validate(
                    approval_id=approval_id,
                    agent=agent,
                    tool=tool_name,
                    payload=kwargs,
                )
            )

            if not validation.get(
                "valid",
                False,
            ):
                return {
                    "status": "blocked",
                    "tool": tool_name,
                    "agent": agent,
                    "approval_id": approval_id,
                    "message": validation.get(
                        "message",
                        "Approval validation failed.",
                    ),
                }

            consumed = (
                self.approval_gate.consume(
                    approval_id=approval_id,
                    agent=agent,
                    tool=tool_name,
                    payload=kwargs,
                )
            )

            if not consumed.get(
                "valid",
                False,
            ):
                return {
                    "status": "blocked",
                    "tool": tool_name,
                    "agent": agent,
                    "approval_id": approval_id,
                    "message": consumed.get(
                        "message",
                        "Approval could not be consumed.",
                    ),
                }

        # -------------------------------------------------------------
        # Execute
        # -------------------------------------------------------------

        try:
            result = tool["function"](
                **kwargs
            )

            if not isinstance(
                result,
                dict,
            ):
                result = {
                    "status": "success",
                    "result": result,
                }

            result.setdefault(
                "status",
                "success",
            )

            result["tool"] = tool_name
            result["agent"] = agent

            if approval_id:
                result["approval_id"] = (
                    approval_id
                )

            self.memory.log(
                "ToolRegistry",
                (
                    f"Executed tool '{tool_name}' "
                    f"for agent '{agent}'."
                ),
            )

            if approval_id:
                self.approval_gate.mark_execution_result(
                    approval_id,
                    result,
                )

            return result

        except Exception as exc:
            error = {
                "status": "error",
                "tool": tool_name,
                "agent": agent,
                "message": str(exc),
            }

            if approval_id:
                error["approval_id"] = (
                    approval_id
                )

                self.approval_gate.mark_execution_result(
                    approval_id,
                    error,
                )

            self.memory.log(
                "ToolRegistry",
                (
                    f"Tool '{tool_name}' failed: "
                    f"{exc}"
                ),
            )

            return error

    # -----------------------------------------------------------------
    # Public metadata
    # -----------------------------------------------------------------

    @staticmethod
    def _public_tool(
        tool: Dict[str, Any],
    ) -> Dict[str, Any]:
        return {
            "name": tool["name"],
            "description": tool[
                "description"
            ],
            "simulation_safe": tool[
                "simulation_safe"
            ],
            "live_capable": tool[
                "live_capable"
            ],
            "protected": tool[
                "protected"
            ],
        }


# ---------------------------------------------------------------------
# Default tools
# ---------------------------------------------------------------------

def create_default_tools(
    memory,
    economy=None,
    research=None,
) -> ToolRegistry:
    registry = ToolRegistry(
        memory=memory,
        economy=economy,
    )

    # ---------------------------------------------------------------
    # Basic logging
    # ---------------------------------------------------------------

    def log_message(
        message: str = "",
        source: str = "Agent",
    ):
        message = (message or "").strip()

        if not message:
            return {
                "status": "error",
                "message": "Message is required.",
            }

        memory.log(
            source,
            message,
        )

        return {
            "status": "success",
            "message": message,
            "source": source,
        }

    registry.register(
        name="log",
        function=log_message,
        description="Write a message to shared system memory.",
        simulation_safe=True,
        live_capable=True,
        protected=False,
    )

    # ---------------------------------------------------------------
    # Information farming
    # ---------------------------------------------------------------

    def farm_info(
        topic: str = "",
    ):
        topic = (topic or "").strip()

        if not topic:
            return {
                "status": "error",
                "message": "Topic is required.",
            }

        if research is None:
            return {
                "status": "error",
                "message": "Research service unavailable.",
            }

        result = research.research_topic(
            topic
        )

        return {
            "status": "success",
            "topic": topic,
            "research": result,
        }

    registry.register(
        name="farm_info",
        function=farm_info,
        description="Research a public information topic.",
        simulation_safe=True,
        live_capable=True,
        protected=False,
    )

    # ---------------------------------------------------------------
    # Balance
    # ---------------------------------------------------------------

    def check_balance():
        try:
            balance = memory.get_balance()
        except Exception:
            balance = 0.0

        return {
            "status": "success",
            "balance": balance,
        }

    registry.register(
        name="check_balance",
        function=check_balance,
        description="Check the current simulated balance.",
        simulation_safe=True,
        live_capable=False,
        protected=False,
    )

    # ---------------------------------------------------------------
    # Tasks
    # ---------------------------------------------------------------

    def create_task(
        agent: str = "",
        description: str = "",
        priority: str = "normal",
    ):
        agent = (agent or "").strip()
        description = (
            description or ""
        ).strip()

        if not agent:
            return {
                "status": "error",
                "message": "Agent is required.",
            }

        if not description:
            return {
                "status": "error",
                "message": "Task description is required.",
            }

        try:
            task_id = memory.add_task(
                agent,
                description,
                priority=priority,
            )
        except TypeError:
            task_id = memory.add_task(
                {
                    "agent": agent,
                    "description": description,
                    "priority": priority,
                }
            )

        return {
            "status": "success",
            "task_id": task_id,
            "agent": agent,
            "description": description,
            "priority": priority,
        }

    registry.register(
        name="create_task",
        function=create_task,
        description="Create a task in shared memory.",
        simulation_safe=True,
        live_capable=True,
        protected=False,
    )

    # ---------------------------------------------------------------
    # Economy mode information
    # ---------------------------------------------------------------

    def money_mode():
        mode = (
            economy.get_mode()
            if economy is not None
            else "simulation"
        )

        return {
            "status": "success",
            "mode": mode,
            "message": (
                "Operating mode is controlled by "
                "the Creator. Agents cannot change "
                "the mode."
            ),
        }

    registry.register(
        name="money_mode",
        function=money_mode,
        description="Read the current economy operating mode.",
        simulation_safe=True,
        live_capable=True,
        protected=False,
    )

    # ---------------------------------------------------------------
    # Opportunities
    # ---------------------------------------------------------------

    def find_opportunity(
        category: str = "",
        budget: float = 0.0,
    ):
        if economy is None:
            return {
                "status": "error",
                "message": "Economy service unavailable.",
            }

        return economy.create_opportunity(
            category=category,
            budget=budget,
        )

    registry.register(
        name="find_opportunity",
        function=find_opportunity,
        description="Generate a potential revenue opportunity.",
        simulation_safe=True,
        live_capable=True,
        protected=False,
    )

    def analyse_opportunity(
        opportunity_id: str = "",
    ):
        if economy is None:
            return {
                "status": "error",
                "message": "Economy service unavailable.",
            }

        return economy.analyse_opportunity(
            opportunity_id
        )

    registry.register(
        name="analyse_opportunity",
        function=analyse_opportunity,
        description="Analyse a revenue opportunity.",
        simulation_safe=True,
        live_capable=True,
        protected=False,
    )

    def list_opportunities():
        if economy is None:
            return {
                "status": "error",
                "message": "Economy service unavailable.",
            }

        return economy.list_opportunities()

    registry.register(
        name="list_opportunities",
        function=list_opportunities,
        description="List discovered revenue opportunities.",
        simulation_safe=True,
        live_capable=True,
        protected=False,
    )

    # ---------------------------------------------------------------
    # Experiments
    # ---------------------------------------------------------------

    def create_experiment(
        opportunity_id: str = "",
        budget: float = 0.0,
        duration_days: int = 7,
    ):
        if economy is None:
            return {
                "status": "error",
                "message": "Economy service unavailable.",
            }

        return economy.create_experiment(
            opportunity_id=opportunity_id,
            budget=budget,
            duration_days=duration_days,
        )

    registry.register(
        name="create_experiment",
        function=create_experiment,
        description=(
            "Create a proposed revenue experiment. "
            "Consequential execution requires Creator approval."
        ),
        simulation_safe=False,
        live_capable=True,
        protected=True,
    )

    def complete_experiment(
        experiment_id: str = "",
        result: str = "",
        revenue: float = 0.0,
    ):
        if economy is None:
            return {
                "status": "error",
                "message": "Economy service unavailable.",
            }

        return economy.complete_experiment(
            experiment_id=experiment_id,
            result=result,
            revenue=revenue,
        )

    registry.register(
        name="complete_experiment",
        function=complete_experiment,
        description=(
            "Record completion of a revenue experiment."
        ),
        simulation_safe=False,
        live_capable=True,
        protected=True,
    )

    def economy_report():
        if economy is None:
            return {
                "status": "error",
                "message": "Economy service unavailable.",
            }

        return economy.get_economy_report()

    registry.register(
        name="economy_report",
        function=economy_report,
        description="Generate an economy report.",
        simulation_safe=True,
        live_capable=True,
        protected=False,
    )

    # ---------------------------------------------------------------
    # Web research
    # ---------------------------------------------------------------

    def web_search(
        query: str = "",
        limit: int = 5,
    ):
        if research is None:
            return {
                "status": "error",
                "message": "Research service unavailable.",
            }

        return research.search(
            query=query,
            limit=limit,
        )

    registry.register(
        name="web_search",
        function=web_search,
        description="Search public web information.",
        simulation_safe=True,
        live_capable=True,
        protected=False,
    )

    def read_webpage(
        url: str = "",
        max_chars: int = 12000,
    ):
        if research is None:
            return {
                "status": "error",
                "message": "Research service unavailable.",
            }

        return research.read_page(
            url=url,
            max_chars=max_chars,
        )

    registry.register(
        name="read_webpage",
        function=read_webpage,
        description="Read a public webpage.",
        simulation_safe=True,
        live_capable=True,
        protected=False,
    )

    return registry
