"""
Boss Agent - Super Overseer


The Boss is the primary orchestrator for the agent system.


The Boss combines:


- command handling
- cognitive state
- memory
- observations
- planning
- tool selection
- tool execution through ToolRegistry
- post-action learning
- agent coordination



Cognitive cycle:


PERCEIVE
    ↓
REMEMBER
    ↓
REASON
    ↓
PLAN
    ↓
SELECT TOOL
    ↓
EXECUTE THROUGH TOOL REGISTRY
    ↓
OBSERVE RESULT
    ↓
LEARN



Important:


The Boss never executes external actions directly.

All actions must pass through ToolRegistry.

ToolRegistry remains responsible for individual tool policy,
including Creator approval requirements.

LIVE mode does not give the Boss unrestricted authority.



"""


from typing import Any, Dict, List, Optional


from .base_agent import BaseAgent
from core.memory import SharedMemory
from core.tools import ToolRegistry
from core.cognitive_room import CognitiveRoom


class BossAgent(BaseAgent):
"""
Super Overseer agent.


The Boss has a private CognitiveRoom containing its current
objective, thoughts, observations, messages, memory and plan.

SharedMemory remains the shared world/blackboard.

This separation is important:

    CognitiveRoom
        = Boss private working state

    SharedMemory
        = shared world state
"""

def __init__(
    self,
    memory: SharedMemory,
    tools: ToolRegistry,
):
    super().__init__(
        name="Boss",
        role="Super Overseer",
        memory=memory,
        tools=tools,
        description=(
            "The main commander. You control this agent."
        ),
    )

    self.room = CognitiveRoom(
        agent_name="Boss",
        role="Super Overseer",
        description=(
            "The main commander and orchestration agent."
        ),
        identity=(
            "You are Boss, the Super Overseer of an "
            "autonomous multi-agent system. "
            "You coordinate agents, research information, "
            "evaluate opportunities, make plans and "
            "control permitted tools."
        ),
    )

    self.update_status("awaiting_orders")

    self.room.remember(
        (
            "Boss cognitive room initialized. "
            "External consequential actions remain subject "
            "to ToolRegistry policy and Creator approval."
        ),
        category="system",
    )

# ==================================================================
# MAIN COGNITIVE CYCLE
# ==================================================================

def run_cognitive_cycle(
    self,
    input_text: str,
    objective: Optional[str] = None,
) -> str:
    """
    Run one complete cognitive cycle.

    This is the main entry point for future autonomous operation.

    The cycle deliberately separates thinking from execution.

    The reasoning system may propose actions, but actual execution
    is always performed through ToolRegistry.
    """

    input_text = str(input_text).strip()

    if not input_text:
        return "No input supplied."

    self.update_status("perceiving")

    # --------------------------------------------------------------
    # 1. PERCEIVE
    # --------------------------------------------------------------

    self.room.observe(
        input_text,
        source="creator_or_system",
    )

    # --------------------------------------------------------------
    # 2. REMEMBER
    # --------------------------------------------------------------

    self.room.remember(
        input_text,
        category="input",
    )

    if objective:
        self.room.set_objective(objective)
    elif self.room.objective is None:
        self.room.set_objective(input_text)

    # --------------------------------------------------------------
    # 3. READ CURRENT WORLD STATE
    # --------------------------------------------------------------

    context = self._build_cognitive_context()

    self.room.think(
        (
            "Perception complete. "
            f"Current objective: {self.room.objective}"
        ),
        kind="perception",
    )

    # --------------------------------------------------------------
    # 4. REASON
    # --------------------------------------------------------------

    self.update_status("reasoning")

    reasoning_prompt = self._build_reasoning_prompt(
        input_text,
        context,
    )

    reasoning = self._ask_brain(
        reasoning_prompt
    )

    self.room.think(
        reasoning,
        kind="reasoning",
    )

    # --------------------------------------------------------------
    # 5. PLAN
    # --------------------------------------------------------------

    self.update_status("planning")

    plan = self._extract_plan_from_reasoning(
        reasoning
    )

    if plan:
        self.room.set_plan(plan)

    self.room.think(
        (
            f"Generated plan with "
            f"{len(plan)} step(s)."
        ),
        kind="planning",
    )

    # --------------------------------------------------------------
    # 6. DECIDE WHETHER THIS CYCLE HAS AN EXECUTABLE ACTION
    # --------------------------------------------------------------

    action = self._identify_action(
        input_text,
        reasoning,
    )

    if action is None:
        self.update_status("awaiting_orders")

        return self._format_cognitive_response(
            reasoning=reasoning,
            plan=plan,
            action=None,
        )

    # --------------------------------------------------------------
    # 7. SELECT TOOL
    # --------------------------------------------------------------

    tool_name = action.get("tool")

    if not tool_name:
        self.update_status("awaiting_orders")

        return self._format_cognitive_response(
            reasoning=reasoning,
            plan=plan,
            action=action,
        )

    tool = self.tools.get_tool(tool_name)

    if tool is None:
        self.room.observe(
            f"Requested tool does not exist: {tool_name}",
            source="tool_registry",
        )

        self.room.remember(
            f"Tool unavailable: {tool_name}",
            category="tool_error",
        )

        self.update_status("awaiting_orders")

        return (
            f"Reasoning complete, but the requested tool "
            f"'{tool_name}' is not available."
        )

    self.room.think(
        (
            f"Selected tool '{tool_name}'. "
            f"Approval required by tool policy: "
            f"{tool.get('requires_approval', False)}"
        ),
        kind="tool_selection",
    )

    # --------------------------------------------------------------
    # 8. EXECUTE THROUGH TOOL REGISTRY
    # --------------------------------------------------------------

    self.update_status("executing")

    parameters = action.get(
        "parameters",
        {},
    )

    result = self.execute_tool(
        tool_name,
        **parameters,
    )

    # --------------------------------------------------------------
    # 9. OBSERVE RESULT
    # --------------------------------------------------------------

    result_text = self._safe_result_text(result)

    self.room.observe(
        result_text,
        source=f"tool:{tool_name}",
    )

    if result.get("success"):
        self.room.remember(
            (
                f"Tool '{tool_name}' succeeded. "
                f"Result: {result_text}"
            ),
            category="tool_result",
        )

        self.room.think(
            (
                f"Tool '{tool_name}' completed successfully."
            ),
            kind="observation",
        )

        # Mark first pending plan step as completed.
        self._complete_next_plan_step()

        self.update_status("learning")

        self._learn_from_result(
            tool_name,
            parameters,
            result,
        )

    else:
        self.room.remember(
            (
                f"Tool '{tool_name}' did not execute "
                f"successfully. Result: {result_text}"
            ),
            category="tool_error",
        )

        self.room.think(
            (
                f"Tool '{tool_name}' did not complete. "
                f"The result must be evaluated before retrying."
            ),
            kind="observation",
        )

        self.update_status("awaiting_orders")

    return self._format_cognitive_response(
        reasoning=reasoning,
        plan=plan,
        action=action,
        tool_result=result,
    )

# ==================================================================
# COMMAND INTERFACE
# ==================================================================

def process_command(
    self,
    command: str,
) -> str:
    """
    Process a Creator command.

    Existing explicit commands remain deterministic so the current
    UI continues to work.

    Anything not recognised by the command router enters the
    cognitive cycle.
    """

    command = command.strip()

    if not command:
        return "Empty command."

    self.memory.log(
        "Boss",
        f"Received command: {command}",
    )

    cmd = command.lower()

    # --------------------------------------------------------------
    # STATUS
    # --------------------------------------------------------------

    if cmd in [
        "status",
        "report",
        "overview",
    ]:
        return self.full_status_report()

    # --------------------------------------------------------------
    # TASK ASSIGNMENT
    # --------------------------------------------------------------

    if (
        cmd.startswith("assign ")
        or cmd.startswith("task ")
    ):
        return self._handle_assign(command)

    # --------------------------------------------------------------
    # BALANCE
    # --------------------------------------------------------------

    if cmd in [
        "balance",
        "funds",
    ]:
        result = self.execute_tool(
            "check_balance"
        )

        balance = (
            result
            .get("result", {})
            .get("balance", 0)
        )

        return (
            f"Current balance under Banker: "
            f"${balance:.2f}"
        )

    # --------------------------------------------------------------
    # HELP
    # --------------------------------------------------------------

    if cmd in [
        "help",
        "?",
    ]:
        return self.get_command_help()

    # --------------------------------------------------------------
    # ANNOUNCEMENT
    # --------------------------------------------------------------

    if cmd.startswith("say "):
        message = command[4:].strip()

        self.room.observe(
            message,
            source="creator",
        )

        self.memory.log(
            "Boss",
            f"Announcement: {message}",
        )

        return (
            f"Announcement logged: {message}"
        )

    # --------------------------------------------------------------
    # CONTENT DRAFT
    # --------------------------------------------------------------

    if cmd.startswith("make post"):
        topic = command[9:].strip()

        topic = topic.replace(
            "about",
            "",
            1,
        ).strip()

        if not topic:
            return (
                "Usage: make post about <topic>"
            )

        return self.make_post(topic)

    # --------------------------------------------------------------
    # WEB SEARCH
    # --------------------------------------------------------------

    if (
        cmd.startswith("search ")
        or cmd.startswith("web ")
    ):
        query = (
            command.split(
                " ",
                1,
            )[1]
            if " " in command
            else ""
        )

        if not query:
            return (
                "Usage: search <your query>"
            )

        return self._format_search(query)

    # --------------------------------------------------------------
    # WEB PAGE READING
    # --------------------------------------------------------------

    if cmd.startswith("read "):
        url = (
            command.split(
                " ",
                1,
            )[1]
            if " " in command
            else ""
        )

        if not url.startswith("http"):
            return (
                "Please provide a full URL "
                "starting with http"
            )

        result = self.execute_tool(
            "read_webpage",
            url=url,
        )

        if result.get("success"):
            page = result["result"]

            return (
                f"Page: {page.get('title')}\n\n"
                f"{str(page.get('content', ''))[:2000]}"
            )

        return (
            f"Failed to read page: "
            f"{result.get('error')}"
        )

    # --------------------------------------------------------------
    # INFORMATION FARMING
    # --------------------------------------------------------------

    if (
        cmd.startswith("farm ")
        or cmd.startswith("research ")
    ):
        topic = (
            command.split(
                " ",
                1,
            )[1].strip()
        )

        if not topic:
            topic = "general opportunities"

        return self.order_info_farmer(
            topic
        )

    # --------------------------------------------------------------
    # MONEY / ECONOMY
    # --------------------------------------------------------------

    if (
        cmd.startswith("money")
        or cmd in [
            "scan",
            "opportunities",
        ]
    ):
        return self._handle_money_command(
            command
        )

    # --------------------------------------------------------------
    # UNKNOWN COMMAND → COGNITIVE SYSTEM
    # --------------------------------------------------------------

    return self.run_cognitive_cycle(
        command
    )

# ==================================================================
# BRAIN INTERFACE
# ==================================================================

def _ask_brain(
    self,
    prompt: str,
) -> str:
    """
    Ask the current reasoning backend.

    The current project uses core.brain.ask_brain.

    A future DeepSeek/Gemini/local model can be placed behind this
    interface without changing the Boss orchestration layer.

    Crucially, the returned text is treated as reasoning data.

    It is NOT granted direct execution authority.
    """

    from core.brain import ask_brain

    try:
        response = ask_brain(prompt)

        if response is None:
            return "No reasoning response was returned."

        return str(response)

    except Exception as exc:
        self.memory.log(
            "Boss",
            f"Brain error: {exc}",
            level="error",
        )

        return (
            "Reasoning backend unavailable. "
            f"Error: {exc}"
        )

# ==================================================================
# COGNITIVE CONTEXT
# ==================================================================

def _build_cognitive_context(
    self,
) -> Dict[str, Any]:
    """
    Build the information supplied to the reasoning layer.

    This gives the brain situational awareness without giving it
    direct access to tool execution.
    """

    agent_status = (
        self.memory.get_all_agent_status()
    )

    pending_tasks = self.memory.get_tasks(
        status="pending"
    )

    recent_logs = self.memory.get_logs(
        limit=10
    )

    available_tools = []

    try:
        available_tools = (
            self.tools.list_tools()
        )
    except Exception:
        available_tools = []

    economy = {}

    if "economy" in self.memory.data:
        economy = {
            "mode": self.memory.data[
                "economy"
            ].get(
                "mode",
                "simulation",
            ),
        }

    return {
        "identity": self.room.identity,
        "objective": self.room.objective,
        "status": self.room.status,
        "recent_memory": self.room.memory[-10:],
        "recent_thoughts": self.room.thoughts[-10:],
        "recent_observations": (
            self.room.observations[-10:]
        ),
        "unread_messages": (
            self.room.unread_messages()
        ),
        "shared_agent_status": agent_status,
        "pending_tasks": pending_tasks[-10:],
        "recent_logs": recent_logs,
        "available_tools": available_tools,
        "economy": economy,
    }

def _build_reasoning_prompt(
    self,
    input_text: str,
    context: Dict[str, Any],
) -> str:
    """
    Construct a structured reasoning request.

    The model is instructed to reason about actions rather than
    directly perform them.
    """

    return f"""



You are the reasoning layer for the Boss agent.


IDENTITY:
{context["identity"]}


CURRENT OBJECTIVE:
{context["objective"]}


USER / SYSTEM INPUT:
{input_text}


CURRENT STATUS:
{context["status"]}


ECONOMY:
{context["economy"]}


AVAILABLE TOOLS:
{context["available_tools"]}


PENDING TASKS:
{context["pending_tasks"]}


OTHER AGENT STATUS:
{context["shared_agent_status"]}


RECENT MEMORY:
{context["recent_memory"]}


RECENT OBSERVATIONS:
{context["recent_observations"]}


UNREAD MESSAGES:
{context["unread_messages"]}


REASONING RULES:




Understand the objective before acting.


Separate research/read-only actions from consequential actions.


Produce a practical plan before execution.


Never assume that LIVE mode means unrestricted authority.


Never bypass ToolRegistry.


Never invent successful external actions.


If an action requires Creator approval, treat approval as a
separate control decision.


Prefer research, analysis and preparation before consequential
execution.


If information is missing, identify what needs to be researched.


Explain what should happen next.




Return a concise analysis containing:


REASONING:



PLAN:





















NEXT ACTION:



Do not pretend that an external action has happened unless a tool
result explicitly confirms it.
"""


# ==================================================================
# PLAN HANDLING
# ==================================================================

def _extract_plan_from_reasoning(
    self,
    reasoning: str,
) -> List[str]:
    """
    Extract simple numbered plan steps from brain output.

    This intentionally uses lightweight parsing rather than
    requiring a particular LLM response format.
    """

    if not reasoning:
        return []

    lines = reasoning.splitlines()

    plan: List[str] = []

    in_plan = False

    for raw_line in lines:
        line = raw_line.strip()

        if not line:
            continue

        upper = line.upper()

        if upper.startswith("PLAN:"):
            in_plan = True
            continue

        if in_plan:
            if upper.startswith(
                "NEXT ACTION:"
            ):
                break

            if (
                len(line) >= 2
                and line[0].isdigit()
                and "." in line[:4]
            ):
                cleaned = line.split(
                    ".",
                    1,
                )[1].strip()

                if cleaned:
                    plan.append(
                        cleaned
                    )

            elif (
                line.startswith("-")
                or line.startswith("*")
            ):
                cleaned = line[1:].strip()

                if cleaned:
                    plan.append(
                        cleaned
                    )

    return plan[:10]

# ==================================================================
# ACTION IDENTIFICATION
# ==================================================================

def _identify_action(
    self,
    input_text: str,
    reasoning: str,
) -> Optional[Dict[str, Any]]:
    """
    Identify a directly executable tool action.

    This deliberately remains conservative.

    We do NOT attempt to turn arbitrary natural-language brain
    output into arbitrary tool calls.

    Known safe/read operations can be recognised.

    More advanced structured tool selection will be added to the
    ToolRegistry/brain interface later.
    """

    text = input_text.strip()

    lower = text.lower()

    # --------------------------------------------------------------
    # Explicit web search
    # --------------------------------------------------------------

    if (
        lower.startswith("search ")
        or lower.startswith("web ")
    ):
        query = (
            text.split(
                " ",
                1,
            )[1].strip()
        )

        if query:
            return {
                "tool": "web_search",
                "parameters": {
                    "query": query,
                    "max_results": 5,
                },
                "reason": (
                    "Explicit Creator web-search request."
                ),
            }

    # --------------------------------------------------------------
    # Explicit public webpage read
    # --------------------------------------------------------------

    if lower.startswith("read "):
        url = (
            text.split(
                " ",
                1,
            )[1].strip()
        )

        if url.startswith("http"):
            return {
                "tool": "read_webpage",
                "parameters": {
                    "url": url,
                },
                "reason": (
                    "Explicit Creator webpage-read request."
                ),
            }

    # --------------------------------------------------------------
    # No automatic arbitrary tool execution yet.
    #
    # This is intentional.
    #
    # The next ToolRegistry/brain patch will introduce structured
    # tool selection with explicit approval metadata.
    # --------------------------------------------------------------

    return None

# ==================================================================
# LEARNING
# ==================================================================

def _learn_from_result(
    self,
    tool_name: str,
    parameters: Dict[str, Any],
    result: Dict[str, Any],
) -> None:
    """
    Store a compact learning record after a successful tool call.
    """

    result_summary = self._safe_result_text(
        result
    )

    self.room.remember(
        (
            f"Action completed: {tool_name}. "
            f"Parameters: {parameters}. "
            f"Result: {result_summary}"
        ),
        category="learning",
    )

    self.memory.log(
        "Boss",
        (
            f"Cognitive cycle learned from "
            f"tool: {tool_name}"
        ),
    )

# ==================================================================
# PLAN PROGRESS
# ==================================================================

def _complete_next_plan_step(
    self,
) -> None:
    """
    Mark the first pending plan step complete.
    """

    for item in self.room.plan:
        if item.get("status") == "pending":
            self.room.complete_plan_step(
                item["step"]
            )
            return

# ==================================================================
# RESPONSE FORMATTING
# ==================================================================

def _format_cognitive_response(
    self,
    reasoning: str,
    plan: List[str],
    action: Optional[Dict[str, Any]],
    tool_result: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Produce a readable response for the current dashboard.

    This exposes enough cognitive state to the Creator without
    dumping the entire private working room.
    """

    response = (
        "=== BOSS COGNITIVE CYCLE ===\n\n"
    )

    response += (
        "REASONING\n"
        f"{reasoning}\n\n"
    )

    if plan:
        response += "PLAN\n"

        for index, step in enumerate(
            plan,
            start=1,
        ):
            response += (
                f"{index}. {step}\n"
            )

        response += "\n"

    if action:
        response += (
            "ACTION\n"
            f"Tool: {action.get('tool', 'none')}\n"
            f"Reason: {action.get('reason', '')}\n"
        )

        if action.get("parameters"):
            response += (
                f"Parameters: "
                f"{action['parameters']}\n"
            )

        response += "\n"

    if tool_result is not None:
        response += "RESULT\n"

        if tool_result.get("success"):
            response += (
                "SUCCESS\n"
                f"{self._safe_result_text(tool_result)}\n"
            )
        else:
            response += (
                "NOT EXECUTED / FAILED\n"
                f"{tool_result.get('error', tool_result)}\n"
            )

    else:
        response += (
            "NEXT STATE\n"
            "No tool action was executed during this cycle."
        )

    return response

# ==================================================================
# RESULT SAFETY
# ==================================================================

def _safe_result_text(
    self,
    result: Any,
    limit: int = 3000,
) -> str:
    """
    Convert a tool result into readable bounded text.

    Prevents enormous webpage/tool responses from being dumped
    into the cognitive room or dashboard.
    """

    try:
        text = str(result)
    except Exception:
        text = "<unprintable result>"

    return text[:limit]

# ==================================================================
# CONTENT
# ==================================================================

def make_post(
    self,
    topic: str,
) -> str:
    """
    Research a topic and prepare a content draft.

    Nothing is published.

    This remains a preparation-only operation.
    """

    self.room.set_objective(
        f"Prepare a useful content draft about {topic}"
    )

    self.room.set_plan(
        [
            "Research the topic.",
            "Extract useful information.",
            "Prepare a concise draft.",
            "Store the draft for Creator review.",
        ]
    )

    search = self.execute_tool(
        "web_search",
        query=topic,
        max_results=3,
    )

    points = []

    if search.get("success"):
        for item in search.get(
            "result",
            [],
        )[:3]:
            title = item.get(
                "title",
                "",
            )

            snippet = item.get(
                "snippet",
                "",
            )

            if title and title != "Error":
                points.append(
                    f"- {title}: "
                    f"{snippet[:140]}"
                )

    if not points:
        points = [
            f"- Simple idea about {topic}"
        ]

    caption = (
        f"{topic.title()} in plain words.\n\n"
        f"3 things worth knowing:\n"
        + "\n".join(points)
        + (
            "\n\nSave this if it is useful. "
            "What would you add?"
        )
    )

    image_prompt = (
        f"Clean mobile-friendly graphic about "
        f"{topic}, simple icons, dark green and "
        f"amber colours, no tiny text"
    )

    self.memory.add_knowledge(
        source="Boss",
        content=(
            f"Draft post about {topic}\n"
            f"{caption}"
        ),
        tags=[
            "content",
            "draft",
            topic.lower(),
        ],
    )

    self.room.remember(
        (
            f"Prepared content draft about {topic}."
        ),
        category="content",
    )

    self.memory.log(
        "Boss",
        f"Drafted post about {topic}",
    )

    return (
        f"CONTENT DRAFT\n"
        f"Topic: {topic}\n\n"
        f"CAPTION\n"
        f"{caption}\n\n"
        f"IMAGE IDEA\n"
        f"{image_prompt}\n\n"
        "Nothing has been posted. "
        "Copy the caption, make the image, "
        "then post it yourself."
    )

# ==================================================================
# WEB SEARCH
# ==================================================================

def _format_search(
    self,
    query: str,
) -> str:
    result = self.execute_tool(
        "web_search",
        query=query,
        max_results=5,
    )

    if not result.get("success"):
        return (
            f"Search failed: "
            f"{result.get('error')}"
        )

    results = result.get(
        "result",
        [],
    )

    if not results:
        return "No results found."

    msg = (
        f"Search results for "
        f"'{query}':\n\n"
    )

    for index, item in enumerate(
        results,
        1,
    ):
        msg += (
            f"{index}. "
            f"{item.get('title', '')}\n"
            f"   {item.get('url', '')}\n"
            f"   {item.get('snippet', '')[:150]}\n\n"
        )

    self.room.remember(
        (
            f"Web search completed for: "
            f"{query}"
        ),
        category="research",
    )

    return msg

# ==================================================================
# ECONOMY
# ==================================================================

def _handle_money_command(
    self,
    command: str,
) -> str:
    cmd = command.lower().strip()

    if cmd in [
        "money",
        "money help",
    ]:
        return self.get_money_help()

    if "mode" in cmd:
        if "simulation" in cmd:
            result = self.execute_tool(
                "money_mode",
                mode="simulation",
            )

            return result.get(
                "result",
                str(result),
            )

        if "real" in cmd:
            result = self.execute_tool(
                "money_mode",
                mode="real",
            )

            return result.get(
                "result",
                str(result),
            )

        result = self.execute_tool(
            "money_mode"
        )

        return result.get(
            "result",
            str(result),
        )

    if "report" in cmd:
        result = self.execute_tool(
            "economy_report"
        )

        if result.get("success"):
            report = result["result"]

            return (
                f"=== ECONOMY REPORT "
                f"({report['mode']}) ===\n"
                f"Opportunities: "
                f"{report['opportunities_total']}\n"
                f"Total Revenue:  "
                f"${report['total_revenue']}\n"
                f"Total Expenses: "
                f"${report['total_expenses']}\n"
                f"Total Profit:   "
                f"${report['total_profit']}\n"
                f"Active Experiments: "
                f"{report['active_experiments']}"
            )

        return str(result)

    if (
        "opportunities" in cmd
        or "list" in cmd
    ):
        result = self.execute_tool(
            "list_opportunities"
        )

        if result.get("success"):
            opportunities = result[
                "result"
            ]

            if not opportunities:
                return (
                    "No opportunities yet."
                )

            msg = (
                "Current Opportunities:\n"
            )

            for opportunity in opportunities:
                msg += (
                    f"[{opportunity['id']}] "
                    f"{opportunity['name']} "
                    f"— "
                    f"{opportunity['status']}\n"
                )

            return msg

        return str(result)

    return self.get_money_help()

# ==================================================================
# STATUS
# ==================================================================

def full_status_report(
    self,
) -> str:
    agents = (
        self.memory.get_all_agent_status()
    )

    pending = [
        task
        for task in self.memory.get_tasks()
        if task["status"] == "pending"
    ]

    balance = self.memory.get_balance(
        "Banker"
    )

    knowledge_count = len(
        self.memory.data.get(
            "knowledge",
            [],
        )
    )

    report = (
        "=== BOSS STATUS REPORT ===\n\n"
    )

    report += (
        f"Bank Balance: "
        f"${balance:.2f}\n"
    )

    report += (
        f"Knowledge entries: "
        f"{knowledge_count}\n"
    )

    report += (
        f"Pending tasks: "
        f"{len(pending)}\n"
    )

    report += (
        f"Cognitive status: "
        f"{self.room.status}\n"
    )

    report += (
        f"Current objective: "
        f"{self.room.objective or 'None'}\n"
    )

    report += (
        f"Plan steps: "
        f"{len(self.room.plan)}\n"
    )

    report += "\nAgents:\n"

    for name, info in agents.items():
        report += (
            f"  - {name} "
            f"({info.get('role')}) "
            f"- {info.get('status')}\n"
        )

    return report

# ==================================================================
# INFO FARMER
# ==================================================================

def order_info_farmer(
    self,
    topic: str,
) -> str:
    self.room.set_objective(
        f"Research useful information about {topic}"
    )

    self.room.set_plan(
        [
            f"Create a research task for InfoFarmer about {topic}.",
            "Execute the research task.",
            "Store the resulting knowledge.",
            "Evaluate the result.",
        ]
    )

    task = self.memory.add_task(
        title=f"Farm info: {topic}",
        description=(
            f"Gather useful information about: "
            f"{topic}"
        ),
        assigned_to="InfoFarmer",
        created_by="Boss",
    )

    result = self.execute_tool(
        "farm_info",
        topic=topic,
        agent="InfoFarmer",
    )

    if result.get("success"):
        self.memory.update_task(
            task["id"],
            "completed",
            notes="Auto-executed",
        )

        self.room.remember(
            (
                f"InfoFarmer completed research "
                f"request: {topic}"
            ),
            category="delegation",
        )

    else:
        self.memory.update_task(
            task["id"],
            "failed",
            notes=str(
                result.get(
                    "error",
                    "Unknown error",
                )
            ),
        )

    return (
        f"Ordered InfoFarmer to research "
        f"'{topic}'.\n"
        f"Result: "
        f"{result.get('result', result)}"
    )

# ==================================================================
# TASK ASSIGNMENT
# ==================================================================

def _handle_assign(
    self,
    command: str,
) -> str:
    parts = command.split()

    if len(parts) < 3:
        return (
            "Usage: "
            "assign <AgentName> "
            "<task description>"
        )

    agent_name = parts[1]

    task_desc = " ".join(
        parts[2:]
    )

    task = self.memory.add_task(
        title=task_desc[:50],
        description=task_desc,
        assigned_to=agent_name,
        created_by="Boss",
    )

    self.room.remember(
        (
            f"Created task #{task['id']} "
            f"for {agent_name}: "
            f"{task_desc}"
        ),
        category="delegation",
    )

    return (
        f"Task created and assigned "
        f"to {agent_name}:\n"
        f"[{task['id']}] "
        f"{task['title']}"
    )

# ==================================================================
# HELP
# ==================================================================

def get_command_help(
    self,
) -> str:
    return """



status                  -> System overview
help                    -> This help
search           -> Search the web
read               -> Read a public page
make post about  -> Draft content; do not post
money mode              -> Show economy mode
money report            -> Economy summary
farm             -> InfoFarmer research
assign     -> Create an agent task


Anything else
-> Enter the Boss cognitive cycle.


Cognitive cycle:
Perceive
Remember
Reason
Plan
Select
Execute through ToolRegistry
Observe
Learn
"""


def get_money_help(
    self,
) -> str:
    return self.get_command_help()



