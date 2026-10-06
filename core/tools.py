"""
Tool Registry
-------------
Central tool system for the agent simulation.

Tools are registered with explicit safety metadata. Simulation-safe tools
may run autonomously. Consequential tools require Creator approval and,
when live mode is enabled, must also be explicitly marked live-capable.
"""

from __future__ import annotations

from typing import Any, Callable, Dict, Optional

from .approvals import ApprovalGate


class ToolRegistry:
    def __init__(
        self,
        memory,
        world=None,
        economy=None,
        research=None,
    ):
        self.memory = memory
        self.world = world
        self.economy = economy
        self.research = research
        self._tools: Dict[str, Dict[str, Any]] = {}
        self.approvals = ApprovalGate(memory)

    def register(
        self,
        name: str,
        handler: Callable[..., Any],
        description: str = "",
        simulation_safe: bool = True,
        live_capable: bool = False,
        protected: bool = False,
        category: str = "general",
    ) -> Dict[str, Any]:
        if not name or not callable(handler):
            raise ValueError("Tool name and callable handler are required.")

        self._tools[name] = {
            "name": name,
            "handler": handler,
            "description": description,
            "simulation_safe": bool(simulation_safe),
            "live_capable": bool(live_capable),
            "protected": bool(protected),
            "category": category,
        }

        return self._public_tool(self._tools[name])

    def unregister(self, name: str) -> bool:
        return self._tools.pop(name, None) is not None

    def get(self, name: str) -> Optional[Dict[str, Any]]:
        return self._tools.get(name)

    def list_tools(self) -> list[Dict[str, Any]]:
        return [
            self._public_tool(tool)
            for tool in self._tools.values()
        ]

    def capabilities(self) -> Dict[str, Any]:
        tools = self.list_tools()

        return {
            "count": len(tools),
            "simulation_safe": [
                tool["name"]
                for tool in tools
                if tool["simulation_safe"]
            ],
            "live_capable": [
                tool["name"]
                for tool in tools
                if tool["live_capable"]
            ],
            "protected": [
                tool["name"]
                for tool in tools
                if tool["protected"]
            ],
            "tools": tools,
        }

    def get_mode(self) -> str:
        if self.economy is not None:
            try:
                return self.economy.get_mode()
            except Exception:
                pass

        if self.memory is not None:
            try:
                return str(
                    self.memory.get_world_state().get(
                        "economy_mode",
                        "simulation",
                    )
                )
            except Exception:
                pass

        return "simulation"

    def is_simulation(self) -> bool:
        return self.get_mode() == "simulation"

    def is_real(self) -> bool:
        return self.get_mode() in {"real", "live"}

    def request_approval(
        self,
        agent: str,
        tool: str,
        reason: str = "",
        parameters: Optional[Dict[str, Any]] = None,
        risk: str = "medium",
        plan: Optional[Any] = None,
    ) -> Dict[str, Any]:
        tool_info = self.get(tool)

        if tool_info is None:
            return {
                "status": "error",
                "message": f"Unknown tool: {tool}",
            }

        return self.approvals.request(
            agent=agent,
            tool=tool,
            reason=reason,
            parameters=parameters or {},
            risk=risk,
            plan=plan,
        )

    def execute(
        self,
        tool: str,
        agent: str = "unknown",
        approval_id: Optional[str] = None,
        **parameters: Any,
    ) -> Dict[str, Any]:
        tool_info = self.get(tool)

        if tool_info is None:
            return {
                "status": "error",
                "tool": tool,
                "message": f"Unknown tool: {tool}",
            }

        mode = self.get_mode()

        if mode == "simulation":
            if not tool_info["simulation_safe"]:
                return {
                    "status": "blocked",
                    "tool": tool,
                    "agent": agent,
                    "mode": mode,
                    "message": (
                        "This tool is not simulation-safe and cannot "
                        "run in simulation mode."
                    ),
                }

        elif mode in {"real", "live"}:
            if not tool_info["live_capable"]:
                return {
                    "status": "blocked",
                    "tool": tool,
                    "agent": agent,
                    "mode": mode,
                    "message": (
                        "This tool is not enabled for live execution."
                    ),
                }

        else:
            return {
                "status": "error",
                "tool": tool,
                "agent": agent,
                "message": f"Unknown economy mode: {mode}",
            }

        if tool_info["protected"]:
            if not approval_id:
                return {
                    "status": "approval_required",
                    "tool": tool,
                    "agent": agent,
                    "mode": mode,
                    "message": (
                        "Creator approval is required before this "
                        "protected action can execute."
                    ),
                }

            validation = self.approvals.validate(
                approval_id=approval_id,
                agent=agent,
                tool=tool,
                parameters=parameters,
            )

            if not validation.get("valid"):
                return {
                    "status": "approval_invalid",
                    "tool": tool,
                    "agent": agent,
                    "approval_id": approval_id,
                    "message": validation.get(
                        "message",
                        "Approval is invalid.",
                    ),
                }

            consumed = self.approvals.consume(
                approval_id=approval_id,
                agent=agent,
                tool=tool,
                parameters=parameters,
            )

            if not consumed.get("valid"):
                return {
                    "status": "approval_invalid",
                    "tool": tool,
                    "agent": agent,
                    "approval_id": approval_id,
                    "message": consumed.get(
                        "message",
                        "Approval could not be consumed.",
                    ),
                }

        try:
            result = tool_info["handler"](**parameters)

            response = {
                "status": "success",
                "tool": tool,
                "agent": agent,
                "mode": mode,
                "result": result,
            }

            if tool_info["protected"] and approval_id:
                self.approvals.mark_execution_result(
                    approval_id,
                    response,
                )

            return response

        except Exception as exc:
            error = {
                "status": "error",
                "tool": tool,
                "agent": agent,
                "mode": mode,
                "message": str(exc),
            }

            if tool_info["protected"] and approval_id:
                self.approvals.mark_execution_result(
                    approval_id,
                    error,
                )

            return error

    def _public_tool(
        self,
        tool: Dict[str, Any],
    ) -> Dict[str, Any]:
        return {
            "name": tool["name"],
            "description": tool["description"],
            "simulation_safe": tool["simulation_safe"],
            "live_capable": tool["live_capable"],
            "protected": tool["protected"],
            "category": tool["category"],
        }


def create_default_tools(
    memory,
    world=None,
    economy=None,
    research=None,
) -> ToolRegistry:
    """
    Create the standard tool registry.

    The arguments are intentionally compatible with main.py and allow
    tools to share the same World, Economy, WebResearch, and memory
    instances used by the rest of the application.
    """

    registry = ToolRegistry(
        memory=memory,
        world=world,
        economy=economy,
        research=research,
    )

    def log_tool(
        message: str,
        level: str = "info",
    ) -> Dict[str, Any]:
        memory.log(
            message=message,
            level=level,
        )

        return {
            "logged": True,
            "level": level,
            "message": message,
        }

    def farm_info_tool(
        topic: str,
    ) -> Dict[str, Any]:
        if research is None:
            return {
                "status": "error",
                "message": "Research service is unavailable.",
            }

        return research.research_topic(topic)

    def check_balance_tool() -> Dict[str, Any]:
        try:
            balance = memory.get_balance()
        except Exception:
            balance = 0.0

        return {
            "balance": balance,
            "currency": "SIM",
            "mode": (
                economy.get_mode()
                if economy is not None
                else "simulation"
            ),
        }

    def create_task_tool(
        title: str,
        description: str = "",
        priority: str = "normal",
        agent: str = "system",
    ) -> Dict[str, Any]:
        task = memory.add_task(
            title=title,
            description=description,
            priority=priority,
            agent=agent,
        )

        return task

    def money_mode_tool() -> Dict[str, Any]:
        mode = (
            economy.get_mode()
            if economy is not None
            else "simulation"
        )

        return {
            "mode": mode,
            "simulation": mode == "simulation",
            "real": mode in {"real", "live"},
            "creator_approval_required": True,
        }

    def find_opportunity_tool(
        category: str = "",
        budget: float = 0.0,
    ) -> Dict[str, Any]:
        if economy is None:
            return {
                "status": "error",
                "message": "Economy service is unavailable.",
            }

        opportunities = economy.list_opportunities(
            category=category
        )

        if not opportunities and hasattr(economy, "create_opportunity"):
            created = economy.create_opportunity(
                title=(
                    f"Research opportunity: "
                    f"{category or 'general'}"
                ),
                category=category or "general",
                description=(
                    "Automatically identified opportunity for "
                    "further analysis."
                ),
                estimated_cost=budget,
            )

            opportunities = [created]

        return {
            "status": "success",
            "category": category,
            "budget": budget,
            "opportunities": opportunities,
        }

    def analyse_opportunity_tool(
        opportunity_id: str,
    ) -> Dict[str, Any]:
        if economy is None:
            return {
                "status": "error",
                "message": "Economy service is unavailable.",
            }

        return economy.analyse_opportunity(
            opportunity_id
        )

    def list_opportunities_tool(
        category: str = "",
    ) -> Dict[str, Any]:
        if economy is None:
            return {
                "status": "error",
                "message": "Economy service is unavailable.",
            }

        return {
            "status": "success",
            "opportunities": economy.list_opportunities(
                category=category
            ),
        }

    def create_experiment_tool(
        opportunity_id: str,
        title: str = "",
        description: str = "",
        budget: float = 0.0,
        duration_days: int = 7,
    ) -> Dict[str, Any]:
        if economy is None:
            return {
                "status": "error",
                "message": "Economy service is unavailable.",
            }

        return economy.create_experiment(
            opportunity_id=opportunity_id,
            title=title,
            description=description,
            budget=budget,
            duration_days=duration_days,
        )

    def complete_experiment_tool(
        experiment_id: str,
        result: str = "",
        revenue: float = 0.0,
        expenses: float = 0.0,
        success: bool = False,
    ) -> Dict[str, Any]:
        if economy is None:
            return {
                "status": "error",
                "message": "Economy service is unavailable.",
            }

        return economy.complete_experiment(
            experiment_id=experiment_id,
            result=result,
            revenue=revenue,
            expenses=expenses,
            success=success,
        )

    def economy_report_tool() -> Dict[str, Any]:
        if economy is None:
            return {
                "status": "error",
                "message": "Economy service is unavailable.",
            }

        return economy.get_economy_report()

    def web_search_tool(
        query: str,
        limit: int = 5,
    ) -> Dict[str, Any]:
        if research is None:
            return {
                "status": "error",
                "message": "Research service is unavailable.",
            }

        return research.search(
            query=query,
            limit=limit,
        )

    def read_webpage_tool(
        url: str,
        max_chars: int = 12000,
    ) -> Dict[str, Any]:
        if research is None:
            return {
                "status": "error",
                "message": "Research service is unavailable.",
            }

        return research.read_page(
            url=url,
            max_chars=max_chars,
        )

    registry.register(
        "log",
        log_tool,
        description="Write a message to shared system logs.",
        simulation_safe=True,
        live_capable=True,
        protected=False,
        category="system",
    )

    registry.register(
        "farm_info",
        farm_info_tool,
        description="Research and store public information.",
        simulation_safe=True,
        live_capable=True,
        protected=False,
        category="research",
    )

    registry.register(
        "check_balance",
        check_balance_tool,
        description="Read the current simulated economy balance.",
        simulation_safe=True,
        live_capable=True,
        protected=False,
        category="finance",
    )

    registry.register(
        "create_task",
        create_task_tool,
        description="Create a task in shared memory.",
        simulation_safe=True,
        live_capable=True,
        protected=False,
        category="orchestration",
    )

    registry.register(
        "money_mode",
        money_mode_tool,
        description="Read the current economy execution mode.",
        simulation_safe=True,
        live_capable=True,
        protected=False,
        category="finance",
    )

    registry.register(
        "find_opportunity",
        find_opportunity_tool,
        description="Find or identify revenue opportunities.",
        simulation_safe=True,
        live_capable=True,
        protected=False,
        category="revenue",
    )

    registry.register(
        "analyse_opportunity",
        analyse_opportunity_tool,
        description="Analyse a revenue opportunity.",
        simulation_safe=True,
        live_capable=True,
        protected=False,
        category="revenue",
    )

    registry.register(
        "list_opportunities",
        list_opportunities_tool,
        description="List known revenue opportunities.",
        simulation_safe=True,
        live_capable=True,
        protected=False,
        category="revenue",
    )

    registry.register(
        "create_experiment",
        create_experiment_tool,
        description=(
            "Create a revenue experiment. Consequential execution "
            "requires Creator approval."
        ),
        simulation_safe=False,
        live_capable=True,
        protected=True,
        category="revenue",
    )

    registry.register(
        "complete_experiment",
        complete_experiment_tool,
        description=(
            "Complete a revenue experiment and record its outcome. "
            "Consequential execution requires Creator approval."
        ),
        simulation_safe=False,
        live_capable=True,
        protected=True,
        category="revenue",
    )

    registry.register(
        "economy_report",
        economy_report_tool,
        description="Generate an economy report.",
        simulation_safe=True,
        live_capable=True,
        protected=False,
        category="finance",
    )

    registry.register(
        "web_search",
        web_search_tool,
        description="Search public web information.",
        simulation_safe=True,
        live_capable=True,
        protected=False,
        category="research",
    )

    registry.register(
        "read_webpage",
        read_webpage_tool,
        description="Read a public webpage.",
        simulation_safe=True,
        live_capable=True,
        protected=False,
        category="research",
    )

    return registry



