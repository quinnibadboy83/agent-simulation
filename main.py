"""
Agent Simulation
----------------

Main application entry point.

Provides:

- FastAPI web application
- Creator dashboard
- Boss command interface
- Agent status
- Cognitive state
- Economy reporting
- Creator approval queue
- Creator-controlled operating mode
- World/time controls
- Health endpoint

Architecture:

Creator
    ↓
Dashboard / API
    ↓
Boss / Agents
    ↓
CognitiveRoom + SharedMemory
    ↓
ToolRegistry
    ↓
Simulation or protected live-capable tools
"""

from pathlib import Path
import os
from typing import Any, Dict

import uvicorn
from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from core.memory import SharedMemory
from core.world import World
from core.economy import Economy
from core.research import WebResearch
from core.tools import create_default_tools

from agents.boss import BossAgent
from agents.banker import BankerAgent
from agents.info_farmer import InfoFarmerAgent
from agents.opportunity_agent import OpportunityAgent


# ================================================================
# APPLICATION
# ================================================================

app = FastAPI(
    title="Agent Simulation",
    description=(
        "Autonomous multi-agent system with "
        "Creator-controlled consequential actions."
    ),
    version="2.0.0",
)


BASE_DIR = Path(__file__).resolve().parent

STATIC_DIR = BASE_DIR / "ui" / "static"
TEMPLATE_DIR = BASE_DIR / "ui" / "templates"


if STATIC_DIR.exists():
    app.mount(
        "/static",
        StaticFiles(directory=STATIC_DIR),
        name="static",
    )


templates = Jinja2Templates(
    directory=TEMPLATE_DIR
)


# ================================================================
# CORE SERVICES
# ================================================================

memory = SharedMemory()

world = World(memory)

economy = Economy(memory)

research = WebResearch(memory)

tools = create_default_tools(
    memory=memory,
    economy=economy,
    research=research,
)


# ================================================================
# AGENTS
# ================================================================

boss = BossAgent(
    memory=memory,
    tools=tools,
)

banker = BankerAgent(
    memory=memory,
    tools=tools,
)

info_farmer = InfoFarmerAgent(
    memory=memory,
    tools=tools,
)

opportunity_agent = OpportunityAgent(
    memory=memory,
    tools=tools,
    economy=economy,
)


agents = {
    "Boss": boss,
    "Banker": banker,
    "InfoFarmer": info_farmer,
    "OpportunityAgent": opportunity_agent,
}


# ================================================================
# AGENT DISPLAY DATA
# ================================================================

SHEETS = {
    "Boss": {
        "role": "Overseer",
        "voice": "Coordinates the other agents.",
        "trait": "Does not bypass Creator approval.",
        "stats": {
            "Perception": 7,
            "Intelligence": 8,
            "Charisma": 6,
            "Endurance": 7,
            "Luck": 5,
        },
    },
    "Banker": {
        "role": "Financial Controller",
        "voice": "Tracks the ledger and financial state.",
        "trait": "Guards financial activity.",
        "stats": {
            "Perception": 6,
            "Intelligence": 8,
            "Charisma": 3,
            "Endurance": 9,
            "Luck": 4,
        },
    },
    "InfoFarmer": {
        "role": "Research Specialist",
        "voice": "Collects and preserves useful information.",
        "trait": "Builds the knowledge base.",
        "stats": {
            "Perception": 9,
            "Intelligence": 8,
            "Charisma": 4,
            "Endurance": 6,
            "Luck": 5,
        },
    },
    "OpportunityAgent": {
        "role": "Opportunity Analyst",
        "voice": "Looks for realistic opportunities and tests.",
        "trait": "Analyses before recommending action.",
        "stats": {
            "Perception": 8,
            "Intelligence": 7,
            "Charisma": 5,
            "Endurance": 6,
            "Luck": 6,
        },
    },
}


# ================================================================
# HELPERS
# ================================================================

def get_safety_state() -> Dict[str, Any]:
    """
    Return the current Creator safety state.
    """

    policy = economy.get_mode_policy()

    return {
        "mode": policy["mode"],
        "label": policy["label"],
        "simulation": policy["simulation"],
        "live": policy["live"],
        "live_tools_available": policy[
            "live_tools_available"
        ],
        "protected_actions_allowed": policy[
            "protected_actions_allowed"
        ],
        "creator_approval_required": policy[
            "creator_approval_required"
        ],
        "description": policy["description"],
    }


def format_approval(approval: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert the internal ApprovalGate representation into a
    dashboard-friendly representation.

    Internal names remain authoritative:

        tool
        reason
        payload

    The UI receives compatible aliases:

        action
        description
        parameters
    """

    payload = approval.get("payload") or {}

    return {
        **approval,
        "action": approval.get(
            "tool",
            "Unknown",
        ),
        "description": approval.get(
            "reason",
            "",
        ),
        "parameters": payload,
        "tool": approval.get(
            "tool",
            "Unknown",
        ),
        "payload": payload,
    }


def get_pending_approvals():
    """
    Return pending Creator approvals in dashboard format.
    """

    return [
        format_approval(item)
        for item in tools.approval_gate.list_pending()
    ]


def get_all_approvals():
    """
    Return all Creator approvals in dashboard format.
    """

    return [
        format_approval(item)
        for item in tools.approval_gate.list_all()
    ]


# ================================================================
# HOME
# ================================================================

@app.get(
    "/",
    response_class=HTMLResponse,
)
async def home(request: Request):

    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "world": world.get_summary(),
            "agents": memory.get_all_agent_status(),
            "logs": memory.get_logs(30),
            "balance": memory.get_balance("Banker"),
            "knowledge_count": len(
                memory.data.get(
                    "knowledge",
                    [],
                )
            ),
            "pending_tasks": memory.get_tasks(
                status="pending",
            ),
            "economy": economy.get_economy_report(),
            "safety": get_safety_state(),
            "approvals": get_pending_approvals(),
        },
    )


# ================================================================
# BOSS COMMAND
# ================================================================

@app.post("/command")
async def send_command(
    command: str = Form(...),
):

    command = command.strip()

    if not command:
        return JSONResponse(
            {
                "success": False,
                "response": "Empty command.",
            },
            status_code=400,
        )

    try:
        response = boss.process_command(
            command
        )

        return {
            "success": True,
            "response": response,
            "balance": memory.get_balance(
                "Banker"
            ),
            "knowledge_count": len(
                memory.data.get(
                    "knowledge",
                    [],
                )
            ),
            "economy_mode": economy.get_mode(),
            "safety": get_safety_state(),
            "pending_approvals": get_pending_approvals(),
        }

    except Exception as exc:

        memory.log(
            "System",
            f"Command failed: {exc}",
            level="error",
        )

        return JSONResponse(
            {
                "success": False,
                "response": (
                    "Command failed: "
                    + str(exc)
                ),
            },
            status_code=500,
        )


# ================================================================
# STATUS
# ================================================================

@app.get("/api/status")
async def api_status():

    return {
        "success": True,
        "world": world.get_summary(),
        "agents": memory.get_all_agent_status(),
        "balance": memory.get_balance("Banker"),
        "knowledge_count": len(
            memory.data.get(
                "knowledge",
                [],
            )
        ),
        "pending_tasks": memory.get_tasks(
            status="pending",
        ),
        "economy": economy.get_economy_report(),
        "safety": get_safety_state(),
        "approvals": get_pending_approvals(),
    }


# ================================================================
# AGENTS
# ================================================================

@app.get("/api/agents")
async def api_agents():

    return {
        "success": True,
        "agents": memory.get_all_agent_status(),
    }


@app.get("/api/agents/{name}/cognitive")
async def api_agent_cognitive(name: str):

    agent = agents.get(name)

    if not agent:
        return JSONResponse(
            {
                "success": False,
                "error": f"Unknown agent: {name}",
            },
            status_code=404,
        )

    return {
        "success": True,
        "agent": name,
        "cognitive_state": (
            agent.get_cognitive_state()
        ),
    }


# ================================================================
# TOOLS
# ================================================================

@app.get("/api/tools")
async def api_tools():

    return {
        "success": True,
        "mode": economy.get_mode(),
        "safety": get_safety_state(),
        "tools": tools.list_tools(),
        "capabilities": tools.get_capabilities(),
    }


# ================================================================
# CREATOR MODE CONTROL
# ================================================================

@app.post("/api/mode")
async def set_mode(
    mode: str = Form(...),
):

    requested_mode = (
        str(mode)
        .strip()
        .lower()
    )

    if requested_mode == "live":
        requested_mode = "real"

    if requested_mode == "sim":
        requested_mode = "simulation"

    if requested_mode not in {
        "simulation",
        "real",
    }:

        return JSONResponse(
            {
                "success": False,
                "error": (
                    "Invalid mode. "
                    "Use simulation or live."
                ),
            },
            status_code=400,
        )

    old_mode = economy.get_mode()

    result = economy.set_mode(
        requested_mode
    )

    new_mode = economy.get_mode()

    memory.log(
        "Creator",
        (
            f"Creator changed operating mode: "
            f"{old_mode} -> {new_mode}"
        ),
    )

    return {
        "success": True,
        "message": result,
        "old_mode": old_mode,
        "mode": new_mode,
        "safety": get_safety_state(),
    }


# ================================================================
# CREATOR APPROVALS
# ================================================================

@app.get("/api/approvals")
async def api_approvals():

    return {
        "success": True,
        "pending": get_pending_approvals(),
        "all": get_all_approvals(),
    }


@app.post(
    "/api/approvals/{approval_id}/decide"
)
async def decide_approval(
    approval_id: int,
    allow: bool = Form(...),
    reason: str = Form(
        "Creator decision from dashboard"
    ),
):

    approval = tools.approval_gate.get(
        approval_id
    )

    if not approval:

        return JSONResponse(
            {
                "success": False,
                "error": (
                    f"Approval #{approval_id} "
                    "does not exist."
                ),
            },
            status_code=404,
        )

    if approval.get("status") != "pending":

        return JSONResponse(
            {
                "success": False,
                "error": (
                    f"Approval #{approval_id} "
                    f"is already "
                    f"{approval.get('status')}."
                ),
            },
            status_code=409,
        )

    message = tools.approval_gate.decide(
        approval_id,
        allow,
    )

    memory.log(
        "Creator",
        (
            f"Creator decision for approval "
            f"#{approval_id}: "
            f"{'APPROVED' if allow else 'DENIED'}"
            f" | {reason}"
        ),
    )

    return {
        "success": True,
        "approval_id": approval_id,
        "decision": (
            "approved"
            if allow
            else "denied"
        ),
        "message": message,
        "approval": format_approval(
            tools.approval_gate.get(
                approval_id
            )
        ),
        "pending": get_pending_approvals(),
    }


# ================================================================
# DASHBOARD COMPATIBILITY ENDPOINTS
# ================================================================

@app.post(
    "/api/approvals/{approval_id}/approve"
)
async def approve_approval(
    approval_id: int,
    reason: str = Form(
        "Creator approved from dashboard"
    ),
):

    return await decide_approval(
        approval_id=approval_id,
        allow=True,
        reason=reason,
    )


@app.post(
    "/api/approvals/{approval_id}/deny"
)
async def deny_approval(
    approval_id: int,
    reason: str = Form(
        "Creator denied from dashboard"
    ),
):

    return await decide_approval(
        approval_id=approval_id,
        allow=False,
        reason=reason,
    )


# ================================================================
# TIME
# ================================================================

@app.post("/api/advance_time")
async def advance_time():

    world.advance_time()

    return {
        "success": True,
        "message": "Time advanced.",
        "world": world.get_summary(),
    }


# ================================================================
# VAULT
# ================================================================

@app.get(
    "/vault",
    response_class=HTMLResponse,
)
async def vault(request: Request):

    rooms = {
        "Boss office": ["Boss"],
        "Bank": ["Banker"],
        "Research floor": ["InfoFarmer"],
        "Planning room": [
            "OpportunityAgent"
        ],
    }

    return templates.TemplateResponse(
        "vault.html",
        {
            "request": request,
            "rooms": rooms,
            "world": world.get_summary(),
            "economy": economy.get_economy_report(),
        },
    )


# ================================================================
# AGENT PAGE
# ================================================================

@app.get(
    "/agent/{name}",
    response_class=HTMLResponse,
)
async def agent_page(
    request: Request,
    name: str,
    archived: int = 0,
):

    if name not in SHEETS:

        return HTMLResponse(
            "No such agent",
            status_code=404,
        )

    status = (
        memory
        .get_all_agent_status()
        .get(name, {})
        .get(
            "status",
            "unknown",
        )
    )

    logs = []

    for item in memory.get_logs(40):

        if item.get("agent") == name:

            logs.append(
                item.get(
                    "message",
                    str(item),
                )
            )

    notes = []

    if name == "InfoFarmer":

        for index, item in enumerate(
            memory.data.get(
                "knowledge",
                [],
            ),
            start=1,
        ):

            if "id" not in item:
                item["id"] = index

            if (
                bool(archived)
                == bool(
                    item.get(
                        "archived",
                        False,
                    )
                )
            ):
                notes.append(item)

    return templates.TemplateResponse(
        "agent.html",
        {
            "request": request,
            "name": name,
            "sheet": SHEETS[name],
            "status": status,
            "logs": logs[:10],
            "notes": notes,
            "cognitive_state": (
                agents[name]
                .get_cognitive_state()
            ),
        },
    )


# ================================================================
# INFOFARMER NOTES
# ================================================================

@app.post(
    "/agent/InfoFarmer/note"
)
async def note_action(
    note_id: int = Form(...),
    action: str = Form(...),
):

    kept = []

    for item in memory.data.get(
        "knowledge",
        [],
    ):

        if (
            item.get("id") == note_id
            and action == "delete"
        ):
            continue

        if (
            item.get("id") == note_id
            and action == "archive"
        ):
            item["archived"] = True

        kept.append(item)

    memory.data["knowledge"] = kept

    memory.save()

    return HTMLResponse(
        "<script>"
        "location='/agent/InfoFarmer'"
        "</script>"
    )


# ================================================================
# HEALTH
# ================================================================

@app.get("/health")
async def health():

    return {
        "status": "ok",
        "application": "agent-simulation",
        "version": "2.0.0",
        "mode": economy.get_mode(),
        "agents": list(
            agents.keys()
        ),
        "pending_approvals": len(
            get_pending_approvals()
        ),
    }


# ================================================================
# STARTUP
# ================================================================

@app.on_event("startup")
async def startup_event():

    memory.log(
        "System",
        "Agent Simulation started.",
    )

    memory.log(
        "System",
        (
            "Operating mode: "
            + economy.get_mode()
        ),
    )

    memory.log(
        "System",
        (
            "Creator Approval Gate active. "
            "Protected consequential actions "
            "require explicit approval."
        ),
    )


# ================================================================
# LOCAL ENTRY POINT
# ================================================================

if __name__ == "__main__":

    port = int(
        os.environ.get(
            "PORT",
            "8000",
        )
    )

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=False,
    )
