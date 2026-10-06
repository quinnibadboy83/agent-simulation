"""
Agent Simulation
----------------
Application entry point.

Creator
   ↓
BrainRouter
   ↓
AutonomousBrain
   ↓
Tools / Specialist Agents
   ↓
Observation / Memory
   ↓
Creator

The legacy Boss command system remains available as a fallback, but
natural-language Creator requests are routed through the brain first.
"""

from __future__ import annotations

import inspect
import os
import traceback
from pathlib import Path
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
from core.approvals import ApprovalGate
from core.tools import create_default_tools
from core.orchestrator import Orchestrator

from core.agent_brain_manager import AgentBrainManager
from core.brain_router import BrainRouter

from agents.boss import Boss
from agents.banker import Banker
from agents.info_farmer import InfoFarmer
from agents.opportunity_agent import OpportunityAgent


# ---------------------------------------------------------------------
# Application
# ---------------------------------------------------------------------

app = FastAPI(
    title="Autonomous Agent Simulation",
    version="0.3.0",
)


BASE_DIR = Path(__file__).parent

TEMPLATE_DIR = BASE_DIR / "ui" / "templates"
STATIC_DIR = BASE_DIR / "ui" / "static"

if STATIC_DIR.exists():
    app.mount(
        "/static",
        StaticFiles(directory=STATIC_DIR),
        name="static",
    )

templates = Jinja2Templates(
    directory=TEMPLATE_DIR
)


# ---------------------------------------------------------------------
# Core systems
# ---------------------------------------------------------------------

memory = SharedMemory()

world = World(memory)

economy = Economy(memory)

research = WebResearch(memory)

approvals = ApprovalGate(memory)

tools = create_default_tools(
    memory=memory,
    world=world,
    economy=economy,
    research=research,
)


# ---------------------------------------------------------------------
# Agents
# ---------------------------------------------------------------------

boss = Boss(
    memory=memory,
    tools=tools,
)

banker = Banker(
    memory=memory,
    tools=tools,
)

info_farmer = InfoFarmer(
    memory=memory,
    tools=tools,
)

opportunity_agent = OpportunityAgent(
    memory=memory,
    tools=tools,
    economy=economy,
)


agents: Dict[str, Any] = {
    "Boss": boss,
    "Banker": banker,
    "InfoFarmer": info_farmer,
    "OpportunityAgent": opportunity_agent,
}


# ---------------------------------------------------------------------
# Register specialist agents with Boss
# ---------------------------------------------------------------------

try:
    boss.register_agents(agents)
except Exception:
    try:
        for name, agent in agents.items():
            if name != "Boss":
                boss.register_agent(agent)
    except Exception:
        pass


# ---------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------

orchestrator = Orchestrator(
    memory=memory,
    tools=tools,
    agents=agents,
    world=world,
    economy=economy,
)


# ---------------------------------------------------------------------
# Brain manager
# ---------------------------------------------------------------------

brain_manager = AgentBrainManager(
    memory=memory,
    world=world,
    tools=tools,
)


# ---------------------------------------------------------------------
# Brain router
# ---------------------------------------------------------------------

brain_router = None

brain_initialisation: Dict[str, Any] = {}

try:
    brain_manager.attach_all(agents)

    brain_router = BrainRouter(
        brain_manager=brain_manager,
        agents=agents,
        boss=boss,
        memory=memory,
        tools=tools,
        world=world,
        economy=economy,
    )

    brain_initialisation = {
        "status": "ready",
        "brains": brain_manager.status(),
    }

except TypeError:
    try:
        brain_router = BrainRouter(
            brain_manager=brain_manager,
            agents=agents,
        )

        brain_initialisation = {
            "status": "ready",
            "brains": brain_manager.status(),
        }

    except Exception as exc:
        brain_initialisation = {
            "status": "error",
            "error": str(exc),
        }

except Exception as exc:
    brain_initialisation = {
        "status": "error",
        "error": str(exc),
    }


# ---------------------------------------------------------------------
# Agent profiles
# ---------------------------------------------------------------------

SHEETS = {
    "Boss": {
        "role": "Coordinator",
        "voice": "Understands the Creator objective and coordinates the system.",
        "trait": "Delegates work and protects the approval boundary.",
        "stats": {
            "Perception": 8,
            "Intelligence": 9,
            "Charisma": 7,
            "Endurance": 7,
            "Luck": 5,
        },
    },
    "Banker": {
        "role": "Financial Analyst",
        "voice": "Counts twice and challenges weak financial assumptions.",
        "trait": "Guards the balance.",
        "stats": {
            "Perception": 7,
            "Intelligence": 9,
            "Charisma": 4,
            "Endurance": 9,
            "Luck": 4,
        },
    },
    "InfoFarmer": {
        "role": "Research Intelligence",
        "voice": "Finds evidence and keeps useful information.",
        "trait": "Hates losing a source.",
        "stats": {
            "Perception": 9,
            "Intelligence": 9,
            "Charisma": 4,
            "Endurance": 6,
            "Luck": 5,
        },
    },
    "OpportunityAgent": {
        "role": "Opportunity Scout",
        "voice": "Looks for realistic opportunities and small tests.",
        "trait": "Scores before suggesting.",
        "stats": {
            "Perception": 9,
            "Intelligence": 8,
            "Charisma": 5,
            "Endurance": 6,
            "Luck": 6,
        },
    },
}


# ---------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------

def serialise(value: Any) -> Any:
    """
    Convert internal Python objects into JSON-safe values.
    """

    if value is None:
        return None

    if isinstance(value, (str, int, float, bool)):
        return value

    if isinstance(value, dict):
        return {
            str(key): serialise(item)
            for key, item in value.items()
        }

    if isinstance(value, (list, tuple, set)):
        return [
            serialise(item)
            for item in value
        ]

    if hasattr(value, "model_dump"):
        try:
            return serialise(value.model_dump())
        except Exception:
            pass

    if hasattr(value, "dict"):
        try:
            return serialise(value.dict())
        except Exception:
            pass

    if hasattr(value, "__dict__"):
        try:
            return serialise(vars(value))
        except Exception:
            pass

    return str(value)


def normalise_response(result: Any) -> Any:
    """
    Make brain/router responses safe for FastAPI.
    """

    return serialise(result)


async def maybe_await(value: Any) -> Any:
    if inspect.isawaitable(value):
        return await value

    return value


def current_mode() -> str:
    try:
        return economy.get_mode()
    except Exception:
        return "simulation"


def agent_status() -> Dict[str, Any]:
    try:
        status = memory.get_all_agent_status()

        if isinstance(status, dict):
            return status
    except Exception:
        pass

    output = {}

    for name, agent in agents.items():
        output[name] = {
            "status": "registered",
            "agent": name,
            "brain_attached": bool(
                getattr(agent, "brain", None)
            ),
        }

    return output


def knowledge_count() -> int:
    try:
        return len(
            memory.data.get(
                "knowledge",
                [],
            )
        )
    except Exception:
        return 0


def pending_approvals() -> list:
    try:
        return approvals.list_pending()
    except Exception:
        try:
            return memory.data.get(
                "approvals",
                []
            )
        except Exception:
            return []


async def route_to_brain(command: str) -> Any:
    """
    Send arbitrary Creator language through the autonomous brain.

    Several compatible BrainRouter APIs are supported so that the
    application remains resilient while the brain subsystem evolves.
    """

    if brain_router is None:
        raise RuntimeError(
            "BrainRouter is not initialised."
        )

    methods = (
        "route",
        "process",
        "handle",
        "run",
        "dispatch",
        "route_command",
    )

    for method_name in methods:
        method = getattr(
            brain_router,
            method_name,
            None,
        )

        if not callable(method):
            continue

        attempts = [
            lambda: method(command),
            lambda: method(
                command=command
            ),
            lambda: method(
                request=command
            ),
            lambda: method(
                objective=command
            ),
        ]

        for attempt in attempts:
            try:
                result = attempt()
                result = await maybe_await(result)

                return result

            except TypeError:
                continue

    raise RuntimeError(
        "BrainRouter does not expose a compatible routing method."
    )


async def brain_command(command: str) -> Any:
    """
    Primary Creator command path.

    Brain first.

    Legacy Boss routing is only used if the brain subsystem is
    unavailable, preventing a broken brain from taking down the UI.
    """

    try:
        return await route_to_brain(command)

    except Exception as brain_error:

        # Record the failure but keep the system usable.
        try:
            memory.log(
                message=(
                    "Brain routing failed: "
                    + str(brain_error)
                ),
                level="error",
            )
        except Exception:
            pass

        # Legacy fallback.
        try:
            if hasattr(boss, "process_order"):
                result = boss.process_order(command)
            else:
                result = boss.process_command(command)

            result = await maybe_await(result)

            return {
                "brain": {
                    "status": "failed",
                    "error": str(brain_error),
                },
                "fallback": {
                    "status": "used",
                },
                "result": result,
            }

        except Exception as fallback_error:
            raise RuntimeError(
                "Both autonomous brain routing and "
                "legacy Boss routing failed. "
                f"Brain error: {brain_error}. "
                f"Fallback error: {fallback_error}."
            )


# ---------------------------------------------------------------------
# Startup
# ---------------------------------------------------------------------

@app.on_event("startup")
async def startup_event():
    """
    Initialise and report the autonomous system.
    """

    try:
        boss.register_agents(agents)
    except Exception:
        pass

    try:
        brain_manager.attach_all(agents)
    except Exception as exc:
        brain_initialisation["attach_error"] = str(exc)

    try:
        memory.log(
            message=(
                "Autonomous agent system initialised. "
                f"Agents: {', '.join(agents.keys())}"
            ),
            level="info",
        )
    except Exception:
        pass


# ---------------------------------------------------------------------
# Home
# ---------------------------------------------------------------------

@app.get(
    "/",
    response_class=HTMLResponse,
)
async def home(request: Request):

    context = {
        "request": request,
        "world": world.get_summary(),
        "agents": agent_status(),
        "logs": memory.get_logs(30),
        "balance": memory.get_balance("Banker"),
        "knowledge_count": knowledge_count(),
        "pending_tasks": memory.get_tasks(
            status="pending"
        ),
        "economy": economy.get_economy_report(),
    }

    return templates.TemplateResponse(
        "index.html",
        context,
    )


# ---------------------------------------------------------------------
# Creator command
# ---------------------------------------------------------------------

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
            }
        )

    try:

        result = await brain_command(command)

        return JSONResponse(
            {
                "success": True,
                "response": normalise_response(result),
                "result": normalise_response(result),
                "balance": memory.get_balance("Banker"),
                "knowledge_count": knowledge_count(),
                "economy_mode": current_mode(),
                "brain": (
                    brain_manager.status()
                    if brain_manager
                    else {}
                ),
            }
        )

    except Exception as exc:

        error = {
            "status": "error",
            "message": str(exc),
            "command": command,
        }

        try:
            error["traceback"] = traceback.format_exc()
        except Exception:
            pass

        return JSONResponse(
            {
                "success": False,
                "response": error,
                "result": error,
                "balance": memory.get_balance("Banker"),
                "knowledge_count": knowledge_count(),
                "economy_mode": current_mode(),
            },
            status_code=500,
        )


# ---------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------

@app.get("/health")
async def health():

    return {
        "status": "ok",
        "service": "agent-simulation",
        "brain": (
            "ready"
            if brain_router is not None
            else "unavailable"
        ),
        "agents": list(agents.keys()),
        "mode": current_mode(),
    }


# ---------------------------------------------------------------------
# System status
# ---------------------------------------------------------------------

@app.get("/api/status")
async def api_status():

    return {
        "success": True,
        "world": serialise(
            world.get_summary()
        ),
        "agents": serialise(
            agent_status()
        ),
        "agent_names": list(
            agents.keys()
        ),
        "boss_agents": list(
            getattr(
                boss,
                "agents",
                {}
            ).keys()
        ),
        "balance": memory.get_balance(
            "Banker"
        ),
        "knowledge_count": knowledge_count(),
        "pending_tasks": serialise(
            memory.get_tasks(
                status="pending"
            )
        ),
        "logs": serialise(
            memory.get_logs(20)
        ),
        "economy": serialise(
            economy.get_economy_report()
        ),
        "economy_mode": current_mode(),
        "brain": serialise(
            brain_manager.status()
        ),
        "brain_initialisation": serialise(
            brain_initialisation
        ),
        "pending_approvals": serialise(
            pending_approvals()
        ),
    }


# ---------------------------------------------------------------------
# Agents
# ---------------------------------------------------------------------

@app.get("/api/agents")
async def api_agents():

    result = {}

    statuses = agent_status()

    for name, agent in agents.items():

        result[name] = {
            "name": name,
            "role": SHEETS.get(
                name,
                {}
            ).get(
                "role",
                "Agent",
            ),
            "status": statuses.get(
                name,
                {
                    "status": "registered"
                },
            ),
            "brain_attached": (
                name in brain_manager.brains
            ),
            "brain": serialise(
                brain_manager.get_brain(name)
            )
            if name in brain_manager.brains
            else None,
        }

    return {
        "success": True,
        "agents": serialise(result),
        "count": len(result),
    }


# ---------------------------------------------------------------------
# Brain status
# ---------------------------------------------------------------------

@app.get("/api/brain")
async def api_brain():

    return {
        "success": True,
        "router_available": (
            brain_router is not None
        ),
        "manager": serialise(
            brain_manager.status()
        ),
        "initialisation": serialise(
            brain_initialisation
        ),
    }


# ---------------------------------------------------------------------
# Brain command endpoint
# ---------------------------------------------------------------------

@app.post("/api/brain/command")
async def api_brain_command(
    command: str = Form(...),
):

    command = command.strip()

    if not command:
        return JSONResponse(
            {
                "success": False,
                "error": "Empty command.",
            },
            status_code=400,
        )

    try:

        result = await route_to_brain(
            command
        )

        return {
            "success": True,
            "command": command,
            "result": normalise_response(result),
        }

    except Exception as exc:

        return JSONResponse(
            {
                "success": False,
                "command": command,
                "error": str(exc),
                "traceback": traceback.format_exc(),
            },
            status_code=500,
        )


# ---------------------------------------------------------------------
# Brain reset
# ---------------------------------------------------------------------

@app.post("/api/brain/reset/{agent_name}")
async def reset_agent_brain(
    agent_name: str,
):

    if agent_name not in agents:
        return JSONResponse(
            {
                "success": False,
                "error": (
                    f"Unknown agent '{agent_name}'."
                ),
            },
            status_code=404,
        )

    success = brain_manager.reset_brain(
        agent_name
    )

    return {
        "success": success,
        "agent": agent_name,
        "brain": serialise(
            brain_manager.get_brain(
                agent_name
            )
        ),
    }


# ---------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------

@app.get("/api/tools")
async def api_tools():

    try:
        capabilities = tools.capabilities()

        return {
            "success": True,
            "tools": serialise(
                capabilities
            ),
        }

    except Exception as exc:

        try:
            tool_list = tools.list_tools()
        except Exception:
            tool_list = []

        return {
            "success": True,
            "tools": serialise(
                tool_list
            ),
            "error": str(exc),
        }


# ---------------------------------------------------------------------
# Approvals
# ---------------------------------------------------------------------

@app.get("/api/approvals")
async def api_approvals():

    return {
        "success": True,
        "pending": serialise(
            pending_approvals()
        ),
        "all": serialise(
            memory.data.get(
                "approvals",
                []
            )
        ),
    }


@app.post(
    "/api/approvals/{approval_id}/approve"
)
async def approve_action(
    approval_id: str,
):

    try:

        result = approvals.decide(
            approval_id=approval_id,
            decision="approved",
        )

        return {
            "success": True,
            "result": serialise(result),
        }

    except Exception as exc:

        return JSONResponse(
            {
                "success": False,
                "error": str(exc),
            },
            status_code=500,
        )


@app.post(
    "/api/approvals/{approval_id}/deny"
)
async def deny_action(
    approval_id: str,
):

    try:

        result = approvals.decide(
            approval_id=approval_id,
            decision="denied",
        )

        return {
            "success": True,
            "result": serialise(result),
        }

    except Exception as exc:

        return JSONResponse(
            {
                "success": False,
                "error": str(exc),
            },
            status_code=500,
        )


# ---------------------------------------------------------------------
# Economy
# ---------------------------------------------------------------------

@app.get("/api/economy")
async def api_economy():

    return {
        "success": True,
        "mode": current_mode(),
        "report": serialise(
            economy.get_economy_report()
        ),
    }


@app.post("/api/mode")
async def set_mode(
    mode: str = Form(...),
):

    mode = mode.strip().lower()

    if mode not in {
        "simulation",
        "real",
        "live",
    }:
        return JSONResponse(
            {
                "success": False,
                "error": (
                    "Mode must be simulation, "
                    "real, or live."
                ),
            },
            status_code=400,
        )

    # The economy object controls the active mode.
    setter = getattr(
        economy,
        "set_mode",
        None,
    )

    if not callable(setter):
        setter = getattr(
            economy,
            "change_mode",
            None,
        )

    if callable(setter):
        try:
            result = setter(mode)

            return {
                "success": True,
                "mode": current_mode(),
                "result": serialise(result),
            }

        except Exception as exc:

            return JSONResponse(
                {
                    "success": False,
                    "error": str(exc),
                },
                status_code=500,
            )

    return JSONResponse(
        {
            "success": False,
            "error": (
                "Economy mode control is not "
                "available in this build."
            ),
        },
        status_code=501,
    )


# ---------------------------------------------------------------------
# World
# ---------------------------------------------------------------------

@app.get("/api/world")
async def api_world():

    return {
        "success": True,
        "world": serialise(
            world.get_summary()
        ),
    }


@app.post("/api/advance_time")
async def advance_time():

    result = world.advance_time()

    return {
        "success": True,
        "message": "Time advanced.",
        "world": serialise(
            result
            if result is not None
            else world.get_summary()
        ),
    }


# ---------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------

@app.get("/api/orchestrator")
async def api_orchestrator():

    try:
        status = orchestrator.status()
    except Exception as exc:
        status = {
            "status": "error",
            "error": str(exc),
        }

    return {
        "success": True,
        "status": serialise(status),
    }


@app.post("/api/orchestrator/cycle")
async def orchestrator_cycle():

    try:

        method = getattr(
            orchestrator,
            "run_autonomous_cycle",
            None,
        )

        if not callable(method):
            method = getattr(
                orchestrator,
                "run_cycle",
                None,
            )

        if not callable(method):
            method = getattr(
                orchestrator,
                "run_once",
                None,
            )

        if not callable(method):
            raise RuntimeError(
                "No orchestrator cycle method available."
            )

        result = method()

        result = await maybe_await(
            result
        )

        return {
            "success": True,
            "result": serialise(
                result
            ),
        }

    except Exception as exc:

        return JSONResponse(
            {
                "success": False,
                "error": str(exc),
                "traceback": traceback.format_exc(),
            },
            status_code=500,
        )


# ---------------------------------------------------------------------
# Agent pages
# ---------------------------------------------------------------------

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

    statuses = agent_status()

    status = statuses.get(
        name,
        {},
    )

    if isinstance(status, dict):
        status = status.get(
            "status",
            "registered",
        )

    logs = []

    try:
        for item in memory.get_logs(40):

            if item.get("agent") == name:
                logs.append(
                    item.get(
                        "message",
                        str(item),
                    )
                )
    except Exception:
        pass

    notes = []

    if name == "InfoFarmer":

        try:
            for i, item in enumerate(
                memory.data.get(
                    "knowledge",
                    []
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

        except Exception:
            pass

    return templates.TemplateResponse(
        "agent.html",
        {
            "request": request,
            "name": name,
            "sheet": SHEETS[name],
            "status": status,
            "logs": logs[:10],
            "notes": notes,
            "brain": (
                brain_manager.get_brain(name)
            ),
        },
    )


# ---------------------------------------------------------------------
# InfoFarmer note management
# ---------------------------------------------------------------------

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
        "<script>location='/agent/InfoFarmer'</script>"
    )


# ---------------------------------------------------------------------
# Error handler
# ---------------------------------------------------------------------

@app.exception_handler(Exception)
async def global_exception_handler(
    request: Request,
    exc: Exception,
):

    return JSONResponse(
        {
            "success": False,
            "error": str(exc),
            "path": str(
                request.url.path
            ),
            "traceback": traceback.format_exc(),
        },
        status_code=500,
    )


# ---------------------------------------------------------------------
# Local execution
# ---------------------------------------------------------------------

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
