"""
Agent Simulation - Main Application
-----------------------------------

FastAPI entry point for the autonomous agent simulation.

Provides:

- web dashboard
- Creator command interface
- agent status
- economy status
- world state
- Creator approval management
- task visibility
- InfoFarmer knowledge management

Safety model:

SIMULATION
    Safe simulation actions can execute normally.

REAL
    Public research can operate autonomously.

    Consequential protected actions require a specific
    Creator approval tied to the exact agent, tool and
    parameters.

REAL mode does NOT mean unrestricted execution.
"""

from pathlib import Path
import os

from fastapi import (
    FastAPI,
    Form,
    Request,
)
from fastapi.responses import (
    HTMLResponse,
    JSONResponse,
)
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

import uvicorn

from core.memory import SharedMemory
from core.world import World
from core.economy import Economy
from core.research import WebResearch
from core.tools import create_default_tools

from agents.boss import BossAgent
from agents.banker import BankerAgent
from agents.info_farmer import InfoFarmerAgent
from agents.opportunity_agent import (
    OpportunityAgent,
)


# ======================================================================
# APPLICATION
# ======================================================================

app = FastAPI(
    title="Agent Simulation",
    version="1.0.0",
)


BASE_DIR = Path(__file__).parent

STATIC_DIR = (
    BASE_DIR
    / "ui"
    / "static"
)

TEMPLATE_DIR = (
    BASE_DIR
    / "ui"
    / "templates"
)


# Only mount static files if the directory exists.
# This prevents deployment failure caused by a missing UI directory.
if STATIC_DIR.exists():
    app.mount(
        "/static",
        StaticFiles(
            directory=STATIC_DIR
        ),
        name="static",
    )


templates = Jinja2Templates(
    directory=TEMPLATE_DIR
)


# ======================================================================
# CORE SYSTEMS
# ======================================================================

memory = SharedMemory()

world = World(
    memory
)

economy = Economy(
    memory
)

research = WebResearch(
    memory
)

tools = create_default_tools(
    memory=memory,
    world=world,
    economy=economy,
    research=research,
)


# ======================================================================
# AGENTS
# ======================================================================

boss = BossAgent(
    memory,
    tools,
)

banker = BankerAgent(
    memory,
    tools,
)

info_farmer = InfoFarmerAgent(
    memory,
    tools,
)

opportunity_agent = OpportunityAgent(
    memory,
    tools,
    economy,
)


agents = {
    "Boss": boss,
    "Banker": banker,
    "InfoFarmer": info_farmer,
    "OpportunityAgent": opportunity_agent,
}


# ======================================================================
# AGENT DISPLAY SHEETS
# ======================================================================

SHEETS = {
    "Boss": {
        "role": "Overseer",
        "voice": (
            "Short orders. Checks the others."
        ),
        "trait": (
            "Won't spend without approval"
        ),
        "stats": {
            "Perception": 7,
            "Intelligence": 8,
            "Charisma": 6,
            "Endurance": 7,
            "Luck": 5,
        },
    },
    "Banker": {
        "role": "Ledger",
        "voice": (
            "Counts twice. Refuses vague spend."
        ),
        "trait": (
            "Guards the balance"
        ),
        "stats": {
            "Perception": 6,
            "Intelligence": 8,
            "Charisma": 3,
            "Endurance": 9,
            "Luck": 4,
        },
    },
    "InfoFarmer": {
        "role": "Research",
        "voice": (
            "Keeps clippings. "
            "Hates losing a source."
        ),
        "trait": (
            "Hoards notes"
        ),
        "stats": {
            "Perception": 9,
            "Intelligence": 8,
            "Charisma": 4,
            "Endurance": 6,
            "Luck": 5,
        },
    },
    "OpportunityAgent": {
        "role": "Scout",
        "voice": (
            "Looks for a small test, "
            "not a fantasy."
        ),
        "trait": (
            "Scores before suggesting"
        ),
        "stats": {
            "Perception": 8,
            "Intelligence": 7,
            "Charisma": 5,
            "Endurance": 6,
            "Luck": 6,
        },
    },
}


# ======================================================================
# DASHBOARD
# ======================================================================

@app.get(
    "/",
    response_class=HTMLResponse,
)
async def home(
    request: Request,
):

    context = {
        "request": request,
        "world": world.get_summary(),
        "agents": (
            memory.get_all_agent_status()
        ),
        "logs": memory.get_logs(30),
        "balance": memory.get_balance(
            "Banker"
        ),
        "knowledge_count": len(
            memory.data.get(
                "knowledge",
                [],
            )
        ),
        "pending_tasks": (
            memory.get_tasks(
                status="pending"
            )
        ),
        "economy": (
            economy.get_economy_report()
        ),
        "approvals": (
            memory.get_approvals(
                status="pending"
            )
        ),
    }

    return templates.TemplateResponse(
        "index.html",
        context,
    )


# ======================================================================
# CREATOR COMMAND
# ======================================================================

@app.post("/command")
async def send_command(
    command: str = Form(...),
):

    if not command.strip():
        return JSONResponse(
            {
                "success": False,
                "response": (
                    "Empty command."
                ),
            }
        )

    try:
        response = boss.process_command(
            command
        )

        return JSONResponse(
            {
                "success": True,
                "response": response,
                "balance": (
                    memory.get_balance(
                        "Banker"
                    )
                ),
                "knowledge_count": len(
                    memory.data.get(
                        "knowledge",
                        [],
                    )
                ),
                "economy_mode": (
                    economy.get_mode()
                ),
                "pending_approvals": len(
                    memory.get_approvals(
                        status="pending"
                    )
                ),
            }
        )

    except Exception as exc:

        memory.log(
            "System",
            (
                "Command failed: "
                f"{str(exc)}"
            ),
            level="error",
        )

        return JSONResponse(
            {
                "success": False,
                "response": (
                    "Command failed: "
                    f"{str(exc)}"
                ),
            },
            status_code=500,
        )


# ======================================================================
# SYSTEM STATUS API
# ======================================================================

@app.get("/api/status")
async def api_status():

    return {
        "world": world.get_summary(),
        "agents": (
            memory.get_all_agent_status()
        ),
        "balance": (
            memory.get_balance(
                "Banker"
            )
        ),
        "knowledge_count": len(
            memory.data.get(
                "knowledge",
                [],
            )
        ),
        "pending_tasks": (
            memory.get_tasks(
                status="pending"
            )
        ),
        "logs": memory.get_logs(20),
        "economy": (
            economy.get_economy_report()
        ),
        "mode": economy.get_mode(),
        "approvals": (
            memory.get_approvals()
        ),
        "pending_approvals": (
            memory.get_approvals(
                status="pending"
            )
        ),
    }


# ======================================================================
# AGENT STATUS
# ======================================================================

@app.get("/api/agents")
async def api_agents():

    return {
        "agents": (
            memory.get_all_agent_status()
        )
    }


# ======================================================================
# COGNITIVE STATE
# ======================================================================

@app.get("/api/agents/{name}/cognitive")
async def api_agent_cognitive(
    name: str,
):

    agent = agents.get(name)

    if agent is None:
        return JSONResponse(
            {
                "success": False,
                "error": (
                    f"Unknown agent: {name}"
                ),
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


# ======================================================================
# TOOLS
# ======================================================================

@app.get("/api/tools")
async def api_tools():

    return {
        "mode": economy.get_mode(),
        "tools": (
            tools.list_tools()
        ),
    }


# ======================================================================
# APPROVALS
# ======================================================================

@app.get("/api/approvals")
async def api_approvals():

    return {
        "approvals": (
            memory.get_approvals()
        ),
        "pending": (
            memory.get_approvals(
                status="pending"
            )
        ),
    }


@app.post("/api/approvals/{approval_id}/decide")
async def decide_approval(
    approval_id: int,
    allow: bool = Form(...),
):

    result = tools.approvals.decide(
        approval_id=approval_id,
        allow=allow,
    )

    return {
        "success": True,
        "result": result,
        "approval": (
            tools.approvals.get(
                approval_id
            )
        ),
    }


# ======================================================================
# WORLD
# ======================================================================

@app.post("/api/advance_time")
async def advance_time():

    world.advance_time()

    return {
        "message": "Time advanced",
        "world": world.get_summary(),
    }


# ======================================================================
# VAULT
# ======================================================================

@app.get(
    "/vault",
    response_class=HTMLResponse,
)
async def vault(
    request: Request,
):

    rooms = {
        "Boss office": [
            "Boss"
        ],
        "Bank": [
            "Banker"
        ],
        "Research floor": [
            "InfoFarmer"
        ],
        "Planning room": [
            "OpportunityAgent"
        ],
    }

    return templates.TemplateResponse(
        "vault.html",
        {
            "request": request,
            "rooms": rooms,
            "approvals": (
                memory.get_approvals(
                    status="pending"
                )
            ),
        },
    )


# ======================================================================
# AGENT PAGE
# ======================================================================

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
        .get(
            name,
            {},
        )
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
            )
        ):

            if "id" not in item:
                item["id"] = (
                    index + 1
                )

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

    agent = agents[name]

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
                agent.get_cognitive_state()
            ),
        },
    )


# ======================================================================
# INFOFARMER NOTES
# ======================================================================

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

        if (
            item.get("id") == note_id
            and action == "restore"
        ):
            item["archived"] = False

        kept.append(item)

    memory.data["knowledge"] = kept

    memory.save()

    return HTMLResponse(
        "<script>"
        "location='/agent/InfoFarmer'"
        "</script>"
    )


# ======================================================================
# HEALTH CHECK
# ======================================================================

@app.get("/health")
async def health():

    return {
        "status": "ok",
        "service": "agent-simulation",
        "mode": economy.get_mode(),
        "agents": len(agents),
        "tools": len(
            tools.list_tools()
        ),
    }


# ======================================================================
# STARTUP
# ======================================================================

@app.on_event("startup")
async def startup_event():

    memory.log(
        "System",
        (
            "Agent Simulation started. "
            f"Mode: {economy.get_mode().upper()}"
        ),
    )


# ======================================================================
# LOCAL ENTRY POINT
# ======================================================================

if __name__ == "__main__":

    port = int(
        os.environ.get(
            "PORT",
            8000,
        )
    )

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=False,
)
