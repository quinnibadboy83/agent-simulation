"""
Agent Simulation
----------------
Main FastAPI application.

Creates the shared simulation services, registers all agents with the
orchestrator, exposes the command API, agent API, approval API,
economy/world API, and dashboard.
"""

from pathlib import Path
from typing import Any, Dict, Optional
import os

from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

from core.memory import SharedMemory
from core.world import World
from core.economy import Economy
from core.research import WebResearch
from core.tools import create_default_tools
from core.orchestrator import Orchestrator
from core.approvals import ApprovalGate

from agents.boss import Boss
from agents.banker import Banker
from agents.info_farmer import InfoFarmer
from agents.opportunity_agent import OpportunityAgent


# ---------------------------------------------------------------------------
# APPLICATION
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Agent Simulation",
    version="2.0",
)

BASE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = BASE_DIR / "ui" / "templates"

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


# ---------------------------------------------------------------------------
# CORE SERVICES
# ---------------------------------------------------------------------------

memory = SharedMemory()

world = World(memory)

economy = Economy(memory)

research = WebResearch(memory)

tools = create_default_tools(
    memory=memory,
    world=world,
    economy=economy,
    research=research,
)

approvals = ApprovalGate(memory)


# ---------------------------------------------------------------------------
# AGENTS
# ---------------------------------------------------------------------------

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


agents = {
    "Boss": boss,
    "Banker": banker,
    "InfoFarmer": info_farmer,
    "OpportunityAgent": opportunity_agent,
}


# ---------------------------------------------------------------------------
# ORCHESTRATOR
# ---------------------------------------------------------------------------

orchestrator = Orchestrator(
    memory=memory,
    tools=tools,
    agents=agents,
    world=world,
    economy=economy,
)


# ---------------------------------------------------------------------------
# HELPERS
# ---------------------------------------------------------------------------

def serialise(value: Any) -> Any:
    """
    Convert arbitrary agent/tool output into something FastAPI can return
    safely as JSON.
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
        return [serialise(item) for item in value]

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


def command_text(value: Any) -> str:
    """
    Convert an agent response into a human-readable command response.

    This prevents the frontend from displaying:
        [object Object]
    """

    value = serialise(value)

    if isinstance(value, str):
        return value

    if isinstance(value, dict):

        # Prefer normal response/message fields.
        for key in (
            "response",
            "message",
            "text",
            "output",
            "content",
        ):
            item = value.get(key)

            if isinstance(item, str):
                return item

        # Tool result wrapper.
        if "result" in value:
            result = value["result"]

            if isinstance(result, str):
                return result

            if isinstance(result, dict):
                return command_text(result)

            return str(result)

        # Error wrapper.
        if "error" in value:
            return f"ERROR: {value['error']}"

        # Status wrapper.
        if value.get("status") and len(value) <= 5:
            parts = []

            for key, item in value.items():
                parts.append(f"{key}: {item}")

            return "\n".join(parts)

        # Last resort: readable JSON-like output.
        import json

        try:
            return json.dumps(
                value,
                indent=2,
                ensure_ascii=False,
                default=str,
            )
        except Exception:
            return str(value)

    return str(value)


def safe_agent_status() -> Dict[str, Any]:
    result = {}

    for name, agent in agents.items():
        try:
            result[name] = serialise(agent.get_status_report())
        except Exception as exc:
            result[name] = {
                "status": "error",
                "error": str(exc),
            }

    return result


def current_mode() -> str:
    try:
        return economy.get_mode()
    except Exception:
        try:
            return world.get_state("economy_mode")
        except Exception:
            return "simulation"


# ---------------------------------------------------------------------------
# STARTUP
# ---------------------------------------------------------------------------

@app.on_event("startup")
async def startup_event():
    memory.log(
        "System",
        "Agent Simulation started.",
    )

    memory.log(
        "System",
        "Registered agents: " + ", ".join(agents.keys()),
    )


# ---------------------------------------------------------------------------
# DASHBOARD
# ---------------------------------------------------------------------------

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):

    try:
        return templates.TemplateResponse(
            "index.html",
            {
                "request": request,
                "world": serialise(world.get_summary()),
                "agents": safe_agent_status(),
                "logs": serialise(memory.get_logs(30)),
                "balance": memory.get_balance("Banker"),
                "knowledge_count": len(
                    memory.data.get("knowledge", [])
                ),
                "pending_tasks": serialise(
                    memory.get_tasks(status="pending")
                ),
                "economy": serialise(
                    economy.get_economy_report()
                ),
            },
        )

    except Exception as exc:
        return HTMLResponse(
            f"<h1>Dashboard error</h1><pre>{exc}</pre>",
            status_code=500,
        )


# ---------------------------------------------------------------------------
# COMMAND API
# ---------------------------------------------------------------------------

@app.post("/command")
async def send_command(
    command: str = Form(...)
):

    command = (command or "").strip()

    if not command:
        return JSONResponse(
            {
                "success": False,
                "response": "Empty command.",
            }
        )

    try:

        result = orchestrator.route_command(
            command=command,
            source="Creator",
        )

        response = command_text(result)

        return JSONResponse(
            {
                "success": True,
                "response": response,
                "raw": serialise(result),
                "balance": memory.get_balance("Banker"),
                "knowledge_count": len(
                    memory.data.get("knowledge", [])
                ),
                "economy_mode": current_mode(),
            }
        )

    except Exception as exc:

        memory.log(
            "System",
            f"Command failed: {exc}",
            level="error",
        )

        return JSONResponse(
            {
                "success": False,
                "response": f"COMMAND ERROR: {exc}",
            },
            status_code=500,
        )


# ---------------------------------------------------------------------------
# STATUS
# ---------------------------------------------------------------------------

@app.get("/health")
async def health():
    return {
        "status": "ok",
        "service": "agent-simulation",
    }


@app.get("/api/status")
async def api_status():

    return {
        "status": "ok",
        "world": serialise(world.get_summary()),
        "agents": safe_agent_status(),
        "agent_names": list(agents.keys()),
        "balance": memory.get_balance("Banker"),
        "knowledge_count": len(
            memory.data.get("knowledge", [])
        ),
        "pending_tasks": serialise(
            memory.get_tasks(status="pending")
        ),
        "logs": serialise(
            memory.get_logs(20)
        ),
        "economy": serialise(
            economy.get_economy_report()
        ),
        "mode": current_mode(),
        "orchestrator": serialise(
            orchestrator.status()
        ),
    }


# ---------------------------------------------------------------------------
# AGENTS
# ---------------------------------------------------------------------------

@app.get("/api/agents")
async def api_agents():

    output = {}

    for name, agent in agents.items():

        try:
            output[name] = serialise(
                agent.get_status_report()
            )

        except Exception as exc:

            output[name] = {
                "name": name,
                "status": "error",
                "error": str(exc),
            }

    return {
        "count": len(output),
        "agents": output,
    }


@app.get("/api/agents/{name}")
async def api_agent(name: str):

    agent = agents.get(name)

    if agent is None:
        raise HTTPException(
            status_code=404,
            detail=f"Agent '{name}' not found.",
        )

    try:
        return serialise(
            agent.get_status_report()
        )

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=str(exc),
        )


@app.get("/api/agents/{name}/cognitive")
async def api_agent_cognitive(name: str):

    agent = agents.get(name)

    if agent is None:
        raise HTTPException(
            status_code=404,
            detail=f"Agent '{name}' not found.",
        )

    try:
        return serialise(
            agent.get_cognitive_state()
        )

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=str(exc),
        )


# ---------------------------------------------------------------------------
# TOOLS
# ---------------------------------------------------------------------------

@app.get("/api/tools")
async def api_tools():

    try:
        return {
            "count": len(tools.list_tools()),
            "tools": serialise(
                tools.list_tools()
            ),
        }

    except Exception as exc:
        return {
            "count": 0,
            "tools": [],
            "error": str(exc),
        }


# ---------------------------------------------------------------------------
# ORCHESTRATOR
# ---------------------------------------------------------------------------

@app.get("/api/orchestrator")
async def api_orchestrator():

    return serialise(
        orchestrator.status()
    )


@app.post("/api/orchestrator/start")
async def api_orchestrator_start():

    result = orchestrator.start()

    return {
        "success": True,
        "result": serialise(result),
    }


@app.post("/api/orchestrator/stop")
async def api_orchestrator_stop():

    result = orchestrator.stop()

    return {
        "success": True,
        "result": serialise(result),
    }


@app.post("/api/orchestrator/cycle")
async def api_orchestrator_cycle():

    try:

        result = orchestrator.run_cycle()

        return {
            "success": True,
            "result": serialise(result),
        }

    except Exception as exc:

        memory.log(
            "System",
            f"Orchestrator cycle failed: {exc}",
            level="error",
        )

        return JSONResponse(
            {
                "success": False,
                "error": str(exc),
            },
            status_code=500,
        )


@app.post("/api/orchestrator/task")
async def api_orchestrator_task(
    agent: str = Form(...),
    title: str = Form(...),
    description: str = Form(""),
    priority: str = Form("normal"),
):

    try:

        result = orchestrator.assign_task(
            agent_name=agent,
            title=title,
            description=description,
            priority=priority,
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


@app.post("/api/orchestrator/broadcast")
async def api_orchestrator_broadcast(
    message: str = Form(...),
    sender: str = Form("Creator"),
):

    try:

        result = orchestrator.broadcast(
            message=message,
            sender=sender,
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


# ---------------------------------------------------------------------------
# ECONOMY MODE
# ---------------------------------------------------------------------------

@app.get("/api/mode")
async def api_get_mode():

    return {
        "mode": current_mode(),
        "simulation": current_mode() == "simulation",
        "real": current_mode() == "real",
    }


@app.post("/api/mode")
async def api_set_mode(
    mode: str = Form(...)
):

    requested = (mode or "").strip().lower()

    if requested == "live":
        requested = "real"

    if requested not in {"simulation", "real"}:
        return JSONResponse(
            {
                "success": False,
                "error": (
                    "Invalid mode. Use 'simulation' or 'real'."
                ),
            },
            status_code=400,
        )

    # Agents/tools must never silently promote themselves into
    # consequential real-world mode.
    if requested == "real":

        return JSONResponse(
            {
                "success": False,
                "error": (
                    "Real mode cannot be enabled through this endpoint. "
                    "Creator authentication/approval is required."
                ),
            },
            status_code=403,
        )

    try:

        result = economy.set_mode(requested)

        return {
            "success": True,
            "mode": economy.get_mode(),
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


# ---------------------------------------------------------------------------
# CREATOR APPROVAL QUEUE
# ---------------------------------------------------------------------------

@app.get("/api/approvals")
async def api_approvals():

    try:

        pending = approvals.list_pending()
        all_items = approvals.list_all()

        return {
            "success": True,
            "pending": serialise(pending),
            "all": serialise(all_items),
            "count": len(pending),
        }

    except Exception as exc:

        memory.log(
            "System",
            f"Approval queue error: {exc}",
            level="error",
        )

        return JSONResponse(
            {
                "success": False,
                "error": str(exc),
                "pending": [],
                "all": [],
                "count": 0,
            },
            status_code=500,
        )


@app.post("/api/approvals/{approval_id}/approve")
async def approve_approval(
    approval_id: str
):

    try:

        result = approvals.decide(
            approval_id,
            approved=True,
            decided_by="Creator",
        )

        return {
            "success": True,
            "approval": serialise(result),
        }

    except Exception as exc:

        memory.log(
            "System",
            f"Approval failed: {exc}",
            level="error",
        )

        return JSONResponse(
            {
                "success": False,
                "error": str(exc),
            },
            status_code=500,
        )


@app.post("/api/approvals/{approval_id}/deny")
async def deny_approval(
    approval_id: str
):

    try:

        result = approvals.decide(
            approval_id,
            approved=False,
            decided_by="Creator",
        )

        return {
            "success": True,
            "approval": serialise(result),
        }

    except Exception as exc:

        memory.log(
            "System",
            f"Approval denial failed: {exc}",
            level="error",
        )

        return JSONResponse(
            {
                "success": False,
                "error": str(exc),
            },
            status_code=500,
        )


# ---------------------------------------------------------------------------
# WORLD
# ---------------------------------------------------------------------------

@app.get("/api/world")
async def api_world():

    return serialise(
        world.get_summary()
    )


@app.post("/api/advance_time")
async def advance_time():

    result = world.advance_time()

    return {
        "success": True,
        "world": serialise(
            world.get_summary()
        ),
        "result": serialise(result),
    }


# ---------------------------------------------------------------------------
# ECONOMY
# ---------------------------------------------------------------------------

@app.get("/api/economy")
async def api_economy():

    return serialise(
        economy.get_economy_report()
    )


@app.get("/api/economy/vault")
async def api_economy_vault():

    return {
        "balance": memory.get_balance("Banker"),
        "economy": serialise(
            economy.get_economy_report()
        ),
        "transactions": serialise(
            memory.data.get("transactions", [])
        ),
    }


# ---------------------------------------------------------------------------
# INFOFARMER NOTES
# ---------------------------------------------------------------------------

@app.post("/agent/InfoFarmer/note")
async def note_action(
    note_id: int = Form(...),
    action: str = Form(...),
):

    kept = []

    for item in memory.data.get("knowledge", []):

        if item.get("id") == note_id and action == "delete":
            continue

        if item.get("id") == note_id and action == "archive":
            item["archived"] = True

        kept.append(item)

    memory.data["knowledge"] = kept
    memory.save()

    return {
        "success": True,
        "message": "Note updated.",
    }


# ---------------------------------------------------------------------------
# ERROR HANDLER
# ---------------------------------------------------------------------------

@app.exception_handler(Exception)
async def global_exception_handler(
    request: Request,
    exc: Exception,
):

    memory.log(
        "System",
        f"Unhandled API error on {request.url.path}: {exc}",
        level="error",
    )

    return JSONResponse(
        {
            "success": False,
            "error": str(exc),
            "path": request.url.path,
        },
        status_code=500,
    )


# ---------------------------------------------------------------------------
# LOCAL RUNNER
# ---------------------------------------------------------------------------

if __name__ == "__main__":

    import uvicorn

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
