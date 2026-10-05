"""
Agent Simulation
----------------

FastAPI application entry point.

Architecture:

    Creator
       |
       v
    FastAPI UI
       |
       v
    Agents
       |
       v
    Cognitive Rooms
       |
       v
    Tool Registry
       |
       +---- Simulation
       |
       +---- REAL
                |
                v
          Creator Approval
"""

from pathlib import Path
import os

from fastapi import (
    FastAPI,
    Request,
    Form,
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
from core.approvals import ApprovalGate

from agents.boss import BossAgent
from agents.banker import BankerAgent
from agents.info_farmer import InfoFarmerAgent
from agents.opportunity_agent import OpportunityAgent


# ======================================================================
# APPLICATION
# ======================================================================

app = FastAPI(
    title="Agent Simulation",
)


BASE_DIR = Path(
    __file__
).parent


app.mount(
    "/static",
    StaticFiles(
        directory=(
            BASE_DIR
            / "ui"
            / "static"
        )
    ),
    name="static",
)


templates = Jinja2Templates(
    directory=(
        BASE_DIR
        / "ui"
        / "templates"
    )
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
    memory,
    world,
    economy,
    research,
)

approvals = ApprovalGate(
    memory
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
# CREATOR UI DATA
# ======================================================================

SHEETS = {
    "Boss": {
        "role": "Overseer",
        "voice": "Short orders. Checks the others.",
        "trait": "Won't spend without approval",
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
        "voice": "Counts twice. Refuses vague spend.",
        "trait": "Guards the balance",
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
        "voice": "Keeps clippings. Hates losing a source.",
        "trait": "Hoards notes",
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
        "voice": "Looks for a small test, not a fantasy.",
        "trait": "Scores before suggesting",
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
# HELPERS
# ======================================================================

def get_mode() -> str:
    try:
        return economy.get_mode()
    except Exception:
        try:
            if economy.is_real():
                return "real"

            return "simulation"

        except Exception:
            return "simulation"


def set_mode(
    mode: str,
):
    mode = (
        str(mode)
        .strip()
        .lower()
    )

    if mode == "sim":
        mode = "simulation"

    if mode == "live":
        mode = "real"

    if mode not in {
        "simulation",
        "real",
    }:
        return {
            "success": False,
            "error": (
                "Mode must be "
                "simulation or real."
            ),
        }

    try:
        result = economy.set_mode(
            mode
        )

        return {
            "success": True,
            "mode": mode,
            "result": result,
        }

    except Exception as exc:
        return {
            "success": False,
            "error": str(exc),
        }


# ======================================================================
# HOME
# ======================================================================

@app.get(
    "/",
    response_class=HTMLResponse,
)
async def home(
    request: Request,
):

    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "world": world.get_summary(),
            "agents": memory.get_all_agent_status(),
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
            "pending_tasks": memory.get_tasks(
                status="pending"
            ),
            "economy": economy.get_economy_report(),
            "mode": get_mode(),
            "approvals": approvals.get_pending(),
        },
    )


# ======================================================================
# COMMAND
# ======================================================================

@app.post(
    "/command"
)
async def send_command(
    command: str = Form(...),
):

    if not command.strip():
        return JSONResponse(
            {
                "response": "Empty command."
            }
        )

    response = boss.process_command(
        command
    )

    return JSONResponse(
        {
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
            "economy_mode": get_mode(),
        }
    )


# ======================================================================
# STATUS
# ======================================================================

@app.get(
    "/api/status"
)
async def api_status():

    return {
        "world": world.get_summary(),
        "agents": memory.get_all_agent_status(),
        "balance": memory.get_balance(
            "Banker"
        ),
        "knowledge_count": len(
            memory.data.get(
                "knowledge",
                [],
            )
        ),
        "pending_tasks": memory.get_tasks(
            status="pending"
        ),
        "logs": memory.get_logs(20),
        "economy": economy.get_economy_report(),
        "mode": get_mode(),
        "approvals": approvals.get_pending(),
    }


# ======================================================================
# SAFETY / MODE
# ======================================================================

@app.get(
    "/api/safety"
)
async def api_safety():

    return {
        "mode": get_mode(),
        "simulation": get_mode() == "simulation",
        "real": get_mode() == "real",
        "creator_approval_required_for_protected_actions": True,
        "pending_approvals": len(
            approvals.get_pending()
        ),
    }


@app.get(
    "/api/mode"
)
async def api_mode():

    return {
        "mode": get_mode()
    }


@app.post(
    "/api/mode/{mode}"
)
async def api_set_mode(
    mode: str,
):

    return set_mode(
        mode
    )


# ======================================================================
# APPROVALS
# ======================================================================

@app.get(
    "/api/approvals"
)
async def api_approvals():

    return {
        "approvals": approvals.get_pending()
    }


@app.post(
    "/api/approvals/{approval_id}/approve"
)
async def approve_action(
    approval_id: int,
):

    result = approvals.approve(
        approval_id,
        decided_by="Creator",
    )

    if result is None:
        return JSONResponse(
            {
                "success": False,
                "error": (
                    "Approval not found."
                ),
            },
            status_code=404,
        )

    return {
        "success": True,
        "approval": result,
    }


@app.post(
    "/api/approvals/{approval_id}/deny"
)
async def deny_action(
    approval_id: int,
):

    result = approvals.deny(
        approval_id,
        decided_by="Creator",
    )

    if result is None:
        return JSONResponse(
            {
                "success": False,
                "error": (
                    "Approval not found."
                ),
            },
            status_code=404,
        )

    return {
        "success": True,
        "approval": result,
    }


# ======================================================================
# WORLD
# ======================================================================

@app.post(
    "/api/advance_time"
)
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
        memory.get_all_agent_status()
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

    for item in memory.get_logs(
        40
    ):
        if item.get(
            "agent"
        ) == name:
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
                item["id"] = index + 1

            if (
                bool(archived)
                == bool(
                    item.get(
                        "archived",
                        False,
                    )
                )
            ):
                notes.append(
                    item
                )

    return templates.TemplateResponse(
        "agent.html",
        {
            "request": request,
            "name": name,
            "sheet": SHEETS[name],
            "status": status,
            "logs": logs[:10],
            "notes": notes,
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

        kept.append(
            item
        )

    memory.data[
        "knowledge"
    ] = kept

    memory.save()

    return HTMLResponse(
        "<script>location='/agent/InfoFarmer'</script>"
    )


# ======================================================================
# STARTUP
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
