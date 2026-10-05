"""
Agent Simulation - terminal, economy, research, vault, dossiers
----------------------------------------------------------------

The application supports two operating modes:

    SIMULATION
        Agents operate against the simulated world/economy.
        No protected real-world action is executed.

    LIVE
        Agents may access live-capable tools, but consequential
        actions still require explicit Creator approval.

The Creator Approval Gate is deliberately separate from the
simulation/live switch.

LIVE does NOT mean unrestricted.

LIVE means:
    "Live-capable tools are available, subject to their individual
     safety and approval requirements."
"""

from fastapi import FastAPI, Request, Form
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, JSONResponse

import uvicorn
from pathlib import Path
import os

from core.memory import SharedMemory
from core.world import World
from core.economy import Economy
from core.research import WebResearch
from core.tools import create_default_tools

from agents.boss import BossAgent
from agents.banker import BankerAgent
from agents.info_farmer import InfoFarmerAgent
from agents.opportunity_agent import OpportunityAgent


# ----------------------------------------------------------------------
# APPLICATION
# ----------------------------------------------------------------------

app = FastAPI(
    title="Agent Simulation",
    version="0.2.0",
    description=(
        "Autonomous agent simulation with Creator approval controls "
        "and simulation/live operating modes."
    ),
)


# ----------------------------------------------------------------------
# PATHS / STATIC FILES / TEMPLATES
# ----------------------------------------------------------------------

BASE_DIR = Path(__file__).parent

app.mount(
    "/static",
    StaticFiles(
        directory=BASE_DIR / "ui" / "static"
    ),
    name="static",
)

templates = Jinja2Templates(
    directory=BASE_DIR / "ui" / "templates"
)


# ----------------------------------------------------------------------
# CORE SYSTEMS
# ----------------------------------------------------------------------

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


# ----------------------------------------------------------------------
# AGENTS
# ----------------------------------------------------------------------

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


# ----------------------------------------------------------------------
# AGENT SHEETS
# ----------------------------------------------------------------------

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
# CREATOR / SAFETY HELPERS
# ======================================================================

def get_operating_mode() -> str:
    """
    Return the current economy/operating mode.

    The Economy class is currently the authoritative owner of the
    simulation/live mode.
    """
    return economy.get_mode()


def creator_safety_status() -> dict:
    """
    Return a clear machine-readable description of the current
    safety state.

    This is intentionally explicit so the UI can display exactly
    what the system believes its operating state to be.
    """

    mode = get_operating_mode()

    is_live = str(mode).lower() == "real"

    pending = tools.approvals.get_pending()

    return {
        "mode": mode,
        "simulation": not is_live,
        "live": is_live,
        "creator_approval_required_for_protected_actions": True,
        "pending_approvals": len(pending),
    }


# ======================================================================
# HOME
# ======================================================================

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
                status="pending"
            ),
            "economy": economy.get_economy_report(),
            "safety": creator_safety_status(),
            "approvals": tools.approvals.get_pending(),
        },
    )


# ======================================================================
# COMMAND
# ======================================================================

@app.post("/command")
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
            "economy_mode": economy.get_mode(),
            "safety": creator_safety_status(),
            "pending_approvals": tools.approvals.get_pending(),
        }
    )


# ======================================================================
# STATUS API
# ======================================================================

@app.get("/api/status")
async def api_status():

    return {
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
            status="pending"
        ),
        "logs": memory.get_logs(20),
        "economy": economy.get_economy_report(),
        "safety": creator_safety_status(),
        "approvals": tools.approvals.get_pending(),
    }


# ======================================================================
# SAFETY / OPERATING MODE
# ======================================================================

@app.get("/api/safety")
async def api_safety():

    return creator_safety_status()


@app.post("/api/mode")
async def set_mode(
    mode: str = Form(...),
):
    """
    Creator-controlled operating mode.

    Accepted values:

        simulation
        sim
        real
        live

    SIMULATION is the safer default.

    Switching to LIVE does not approve any pending action.
    """

    requested = mode.strip().lower()

    if requested in {
        "simulation",
        "sim",
    }:

        result = economy.set_mode(
            "simulation"
        )

    elif requested in {
        "real",
        "live",
    }:

        result = economy.set_mode(
            "real"
        )

    else:

        return JSONResponse(
            {
                "success": False,
                "error": (
                    "Invalid mode. Use "
                    "'simulation' or 'live'."
                ),
            },
            status_code=400,
        )

    return JSONResponse(
        {
            "success": True,
            "result": result,
            "safety": creator_safety_status(),
        }
    )


@app.post("/api/mode/{mode}")
async def set_mode_path(
    mode: str,
):
    """
    Path-based version of the operating mode switch.

    Example:

        POST /api/mode/simulation
        POST /api/mode/live
    """

    requested = mode.strip().lower()

    if requested in {
        "simulation",
        "sim",
    }:

        result = economy.set_mode(
            "simulation"
        )

    elif requested in {
        "real",
        "live",
    }:

        result = economy.set_mode(
            "real"
        )

    else:

        return JSONResponse(
            {
                "success": False,
                "error": (
                    "Invalid mode. Use "
                    "'simulation' or 'live'."
                ),
            },
            status_code=400,
        )

    return JSONResponse(
        {
            "success": True,
            "result": result,
            "safety": creator_safety_status(),
        }
    )


# ======================================================================
# CREATOR APPROVAL QUEUE
# ======================================================================

@app.get("/api/approvals")
async def get_approvals():

    return {
        "pending": tools.approvals.get_pending(),
        "count": len(
            tools.approvals.get_pending()
        ),
    }


@app.get("/api/approvals/{approval_id}")
async def get_approval(
    approval_id: int,
):

    approval = tools.approvals.get(
        approval_id
    )

    if approval is None:

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

    return {
        "success": True,
        "approval": approval,
    }


@app.post("/api/approvals/{approval_id}/approve")
async def approve_action(
    approval_id: int,
    reason: str = Form(""),
):

    approval = tools.approvals.approve(
        approval_id=approval_id,
        decided_by="Creator",
        reason=reason,
    )

    if approval is None:

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

    return {
        "success": True,
        "message": (
            f"Approval #{approval_id} approved."
        ),
        "approval": approval,
    }


@app.post("/api/approvals/{approval_id}/deny")
async def deny_action(
    approval_id: int,
    reason: str = Form(""),
):

    approval = tools.approvals.deny(
        approval_id=approval_id,
        decided_by="Creator",
        reason=reason,
    )

    if approval is None:

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

    return {
        "success": True,
        "message": (
            f"Approval #{approval_id} denied."
        ),
        "approval": approval,
    }


# ======================================================================
# TIME
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
            "safety": creator_safety_status(),
            "approvals": tools.approvals.get_pending(),
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

        for i, item in enumerate(
            memory.data.get(
                "knowledge",
                [],
            )
        ):

            if "id" not in item:

                item["id"] = i + 1

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
            "safety": creator_safety_status(),
            "approvals": tools.approvals.get_pending(),
        },
    )


# ======================================================================
# INFO FARMER NOTES
# ======================================================================

@app.post("/agent/InfoFarmer/note")
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


# ======================================================================
# APPLICATION START
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
