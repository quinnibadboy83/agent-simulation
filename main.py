"""
Agent Simulation
----------------
Main FastAPI application.
"""

from pathlib import Path
from typing import Any, Dict
import json
import os
import traceback

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


# ============================================================
# APPLICATION
# ============================================================

app = FastAPI(
    title="Agent Simulation",
    version="2.0.0",
)

BASE_DIR = Path(__file__).resolve().parent

TEMPLATES_DIR = (
    BASE_DIR / "ui" / "templates"
)

templates = Jinja2Templates(
    directory=str(TEMPLATES_DIR)
)


# ============================================================
# CORE SERVICES
# ============================================================

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


# ============================================================
# AGENTS
# ============================================================

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


# ============================================================
# CONNECT AGENTS TO BOSS
# ============================================================

# Boss is the Creator-facing coordinator.
# Give Boss access to all specialist agents.
boss.register_agents(
    agents
)


# ============================================================
# ORCHESTRATOR
# ============================================================

orchestrator = Orchestrator(
    memory=memory,
    tools=tools,
    agents=agents,
    world=world,
    economy=economy,
)


# ============================================================
# HELPERS
# ============================================================

def serialise(value: Any) -> Any:

    if value is None:
        return None

    if isinstance(
        value,
        (
            str,
            int,
            float,
            bool,
        ),
    ):
        return value

    if isinstance(value, dict):

        return {
            str(key): serialise(item)
            for key, item in value.items()
        }

    if isinstance(
        value,
        (
            list,
            tuple,
            set,
        ),
    ):

        return [
            serialise(item)
            for item in value
        ]

    if hasattr(
        value,
        "model_dump",
    ):

        try:

            return serialise(
                value.model_dump()
            )

        except Exception:
            pass

    if hasattr(
        value,
        "dict",
    ):

        try:

            return serialise(
                value.dict()
            )

        except Exception:
            pass

    if hasattr(
        value,
        "__dict__",
    ):

        try:

            return serialise(
                vars(value)
            )

        except Exception:
            pass

    return str(value)


def readable_response(
    value: Any,
) -> str:

    value = serialise(value)

    if isinstance(
        value,
        str,
    ):
        return value

    if isinstance(
        value,
        dict,
    ):

        for key in (
            "response",
            "message",
            "text",
            "output",
            "content",
        ):

            item = value.get(key)

            if isinstance(
                item,
                str,
            ):
                return item

        if "result" in value:

            return readable_response(
                value["result"]
            )

        if "error" in value:

            return (
                f"ERROR: {value['error']}"
            )

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


def current_mode() -> str:

    try:

        return economy.get_mode()

    except Exception:

        try:

            state = world.state

            return state.get(
                "economy_mode",
                "simulation",
            )

        except Exception:

            return "simulation"


def get_agent_status(
    agent: Any,
) -> Dict[str, Any]:

    try:

        return serialise(
            agent.get_status_report()
        )

    except Exception as exc:

        return {
            "name": getattr(
                agent,
                "name",
                "Unknown",
            ),
            "status": "error",
            "error": str(exc),
        }


def all_agent_status() -> Dict[str, Any]:

    result = {}

    for name, agent in agents.items():

        result[name] = get_agent_status(
            agent
        )

    return result


# ============================================================
# STARTUP
# ============================================================

@app.on_event("startup")
async def startup_event():

    try:

        memory.log(
            "System",
            "Agent Simulation started.",
        )

        memory.log(
            "System",
            "Agents registered: "
            + ", ".join(
                agents.keys()
            ),
        )

        memory.log(
            "System",
            "Boss connected to specialist agents: "
            + ", ".join(
                boss.agents.keys()
            ),
        )

    except Exception:
        pass


# ============================================================
# DASHBOARD
# ============================================================

@app.get(
    "/",
    response_class=HTMLResponse,
)
async def home(
    request: Request,
):

    try:

        return templates.TemplateResponse(
            "index.html",
            {
                "request": request,
                "world": serialise(
                    world.get_summary()
                ),
                "agents": all_agent_status(),
                "logs": serialise(
                    memory.get_logs(30)
                ),
                "balance": memory.get_balance(
                    "Banker"
                ),
                "knowledge_count": len(
                    memory.data.get(
                        "knowledge",
                        [],
                    )
                ),
                "pending_tasks": serialise(
                    memory.get_tasks(
                        status="pending"
                    )
                ),
                "economy": serialise(
                    economy.get_economy_report()
                ),
            },
        )

    except Exception as exc:

        return HTMLResponse(
            "<h1>Dashboard Error</h1>"
            f"<pre>{exc}</pre>",
            status_code=500,
        )


# ============================================================
# CREATOR COMMAND
# ============================================================

@app.post("/command")
async def send_command(
    command: str = Form(...),
):

    command = (
        command or ""
    ).strip()

    if not command:

        return JSONResponse({
            "success": False,
            "response": "Empty command.",
        })

    try:

        result = boss.process_order(
            command
        )

        result = serialise(
            result
        )

        response = readable_response(
            result
        )

        return JSONResponse({
            "success": True,
            "response": response,
            "result": result,
            "balance": memory.get_balance(
                "Banker"
            ),
            "knowledge_count": len(
                memory.data.get(
                    "knowledge",
                    [],
                )
            ),
            "economy_mode": current_mode(),
        })

    except Exception as exc:

        error_text = traceback.format_exc()

        try:

            memory.log(
                "System",
                error_text,
                level="error",
            )

        except Exception:
            pass

        return JSONResponse(
            {
                "success": False,
                "response": (
                    f"COMMAND ERROR: {exc}"
                ),
                "error": str(exc),
                "traceback": error_text,
            },
            status_code=500,
        )


# ============================================================
# HEALTH
# ============================================================

@app.get("/health")
async def health():

    return {
        "status": "ok",
        "service": "agent-simulation",
        "agents": list(
            agents.keys()
        ),
        "boss_agents": list(
            boss.agents.keys()
        ),
        "mode": current_mode(),
    }


# ============================================================
# SYSTEM STATUS
# ============================================================

@app.get("/api/status")
async def api_status():

    return {
        "status": "ok",
        "world": serialise(
            world.get_summary()
        ),
        "agents": all_agent_status(),
        "agent_names": list(
            agents.keys()
        ),
        "boss_agents": list(
            boss.agents.keys()
        ),
        "balance": memory.get_balance(
            "Banker"
        ),
        "knowledge_count": len(
            memory.data.get(
                "knowledge",
                [],
            )
        ),
        "pending_tasks": serialise(
            memory.get_tasks(
                status="pending"
            )
        ),
        "logs": serialise(
            memory.get_logs(30)
        ),
        "economy": serialise(
            economy.get_economy_report()
        ),
        "mode": current_mode(),
        "orchestrator": serialise(
            orchestrator.status()
        ),
    }


# ============================================================
# AGENTS
# ============================================================

@app.get("/api/agents")
async def api_agents():

    return {
        "count": len(agents),
        "agents": all_agent_status(),
    }


@app.get("/api/agents/{name}")
async def api_agent(
    name: str,
):

    agent = agents.get(
        name
    )

    if agent is None:

        raise HTTPException(
            status_code=404,
            detail=(
                f"Agent '{name}' not found."
            ),
        )

    return get_agent_status(
        agent
    )


@app.get(
    "/api/agents/{name}/cognitive"
)
async def api_agent_cognitive(
    name: str,
):

    agent = agents.get(
        name
    )

    if agent is None:

        raise HTTPException(
            status_code=404,
            detail=(
                f"Agent '{name}' not found."
            ),
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


# ============================================================
# TOOLS
# ============================================================

@app.get("/api/tools")
async def api_tools():

    try:

        tool_list = tools.list_tools()

        return {
            "count": len(tool_list),
            "tools": serialise(
                tool_list
            ),
        }

    except Exception as exc:

        return {
            "count": 0,
            "tools": [],
            "error": str(exc),
        }


# ============================================================
# ORCHESTRATOR
# ============================================================

@app.get("/api/orchestrator")
async def api_orchestrator():

    return serialise(
        orchestrator.status()
    )


@app.post(
    "/api/orchestrator/start"
)
async def api_orchestrator_start():

    try:

        result = orchestrator.start()

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
            },
            status_code=500,
        )


@app.post(
    "/api/orchestrator/stop"
)
async def api_orchestrator_stop():

    try:

        result = orchestrator.stop()

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
            },
            status_code=500,
        )


@app.post(
    "/api/orchestrator/cycle"
)
async def api_orchestrator_cycle():

    try:

        result = orchestrator.run_cycle()

        return {
            "success": True,
            "result": serialise(
                result
            ),
        }

    except Exception as exc:

        error_text = traceback.format_exc()

        try:

            memory.log(
                "System",
                error_text,
                level="error",
            )

        except Exception:
            pass

        return JSONResponse(
            {
                "success": False,
                "error": str(exc),
                "traceback": error_text,
            },
            status_code=500,
        )


@app.post(
    "/api/orchestrator/task"
)
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


@app.post(
    "/api/orchestrator/broadcast"
)
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


# ============================================================
# ECONOMY MODE
# ============================================================

@app.get("/api/mode")
async def api_get_mode():

    mode = current_mode()

    return {
        "mode": mode,
        "simulation": (
            mode == "simulation"
        ),
        "real": (
            mode == "real"
        ),
    }


@app.post("/api/mode")
async def api_set_mode(
    mode: str = Form(...),
):

    requested = (
        mode or ""
    ).strip().lower()

    if requested == "live":
        requested = "real"

    if requested not in {
        "simulation",
        "real",
    }:

        return JSONResponse(
            {
                "success": False,
                "error": (
                    "Invalid mode. "
                    "Use simulation or real."
                ),
            },
            status_code=400,
        )

    if requested == "real":

        return JSONResponse(
            {
                "success": False,
                "error": (
                    "Real mode requires "
                    "Creator authentication "
                    "and approval."
                ),
            },
            status_code=403,
        )

    try:

        result = economy.set_mode(
            requested
        )

        return {
            "success": True,
            "mode": economy.get_mode(),
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


# ============================================================
# APPROVAL QUEUE
# ============================================================

@app.get("/api/approvals")
async def api_approvals():

    try:

        pending = approvals.list_pending()

        all_items = approvals.list_all()

        return {
            "success": True,
            "pending": serialise(
                pending
            ),
            "all": serialise(
                all_items
            ),
            "count": len(pending),
        }

    except Exception as exc:

        error_text = traceback.format_exc()

        try:

            memory.log(
                "System",
                error_text,
                level="error",
            )

        except Exception:
            pass

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


@app.post(
    "/api/approvals/{approval_id}/approve"
)
async def approve_approval(
    approval_id: str,
):

    try:

        result = approvals.decide(
            approval_id,
            approved=True,
            decided_by="Creator",
        )

        return {
            "success": True,
            "approval": serialise(
                result
            ),
        }

    except Exception as exc:

        error_text = traceback.format_exc()

        try:

            memory.log(
                "System",
                error_text,
                level="error",
            )

        except Exception:
            pass

        return JSONResponse(
            {
                "success": False,
                "error": str(exc),
                "traceback": error_text,
            },
            status_code=500,
        )


@app.post(
    "/api/approvals/{approval_id}/deny"
)
async def deny_approval(
    approval_id: str,
):

    try:

        result = approvals.decide(
            approval_id,
            approved=False,
            decided_by="Creator",
        )

        return {
            "success": True,
            "approval": serialise(
                result
            ),
        }

    except Exception as exc:

        error_text = traceback.format_exc()

        try:

            memory.log(
                "System",
                error_text,
                level="error",
            )

        except Exception:
            pass

        return JSONResponse(
            {
                "success": False,
                "error": str(exc),
                "traceback": error_text,
            },
            status_code=500,
        )


# ============================================================
# WORLD
# ============================================================

@app.get("/api/world")
async def api_world():

    return serialise(
        world.get_summary()
    )


@app.post("/api/advance_time")
async def advance_time():

    try:

        result = world.advance_time()

        return {
            "success": True,
            "world": serialise(
                world.get_summary()
            ),
            "result": serialise(
                result
            ),
        }

    except Exception as exc:

        return JSONResponse(
            {
                "success": False,
                "error": str(exc),
            },
            status_code=500,
        )


# ============================================================
# ECONOMY
# ============================================================

@app.get("/api/economy")
async def api_economy():

    return serialise(
        economy.get_economy_report()
    )


@app.get(
    "/api/economy/vault"
)
async def api_economy_vault():

    return {
        "balance": memory.get_balance(
            "Banker"
        ),
        "economy": serialise(
            economy.get_economy_report()
        ),
        "transactions": serialise(
            memory.data.get(
                "transactions",
                [],
            )
        ),
    }


# ============================================================
# INFOFARMER NOTES
# ============================================================

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

    return {
        "success": True,
        "message": "Note updated.",
    }


# ============================================================
# GLOBAL ERROR HANDLER
# ============================================================

@app.exception_handler(Exception)
async def global_exception_handler(
    request: Request,
    exc: Exception,
):

    error_text = traceback.format_exc()

    try:

        memory.log(
            "System",
            (
                f"Unhandled error on "
                f"{request.url.path}\n"
                f"{error_text}"
            ),
            level="error",
        )

    except Exception:
        pass

    return JSONResponse(
        {
            "success": False,
            "error": str(exc),
            "path": request.url.path,
            "traceback": error_text,
        },
        status_code=500,
    )


# ============================================================
# LOCAL RUNNER
# ============================================================

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
