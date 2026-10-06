"""
Agent Simulation API
--------------------
FastAPI application for the autonomous multi-agent system.

Creator-controlled safety model:
- Simulation mode is the default.
- Research and analysis may run autonomously.
- Consequential external actions require exact Creator approval.
- Approved actions are single-use.
"""

import os
from typing import Any, Dict

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from agents import (
    Banker,
    Boss,
    InfoFarmer,
    OpportunityAgent,
)
from core import (
    Economy,
    Orchestrator,
    SharedMemory,
    WebResearch,
    World,
    create_default_tools,
)


app = FastAPI(
    title="Agent Simulation",
    version="2.0.0",
    description=(
        "Autonomous multi-agent simulation with "
        "Creator-controlled consequential actions."
    ),
)


# ---------------------------------------------------------------------
# Core services
# ---------------------------------------------------------------------

memory = SharedMemory()
world = World(memory)
economy = Economy(memory)
research = WebResearch(memory)

tools = create_default_tools(
    memory=memory,
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


agents = {
    boss.name: boss,
    banker.name: banker,
    info_farmer.name: info_farmer,
    opportunity_agent.name: opportunity_agent,
}


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
# Request models
# ---------------------------------------------------------------------

class CommandRequest(BaseModel):
    command: str


class ModeRequest(BaseModel):
    mode: str


class ApprovalRequest(BaseModel):
    reason: str = ""


class TaskRequest(BaseModel):
    agent: str
    task: str
    priority: str = "normal"


class NoteRequest(BaseModel):
    note: str


# ---------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------

def get_safety_state() -> Dict[str, Any]:
    try:
        policy = economy.get_mode_policy()
    except Exception:
        policy = {
            "mode": "simulation",
            "live_tools_enabled": False,
            "creator_approval_required": True,
        }

    return {
        "mode": policy.get(
            "mode",
            "simulation",
        ),
        "live_tools_enabled": policy.get(
            "live_tools_enabled",
            False,
        ),
        "creator_approval_required": True,
        "exact_approval_required": True,
        "single_use_approvals": True,
    }


def approval_response(item: Dict[str, Any]) -> Dict[str, Any]:
    payload = item.get(
        "payload",
        item.get("parameters", {}),
    )

    return {
        **item,
        "action": item.get(
            "action",
            item.get("tool", ""),
        ),
        "description": item.get(
            "description",
            item.get("reason", ""),
        ),
        "parameters": payload,
    }


def serialise_result(result: Any) -> Any:
    if isinstance(result, dict):
        return result

    if isinstance(result, list):
        return result

    return {
        "status": "success",
        "result": result,
    }


# ---------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------

@app.get(
    "/",
    response_class=HTMLResponse,
)
async def dashboard():
    html_path = os.path.join(
        "ui",
        "templates",
        "index.html",
    )

    if not os.path.exists(html_path):
        return HTMLResponse(
            """
            <html>
                <body>
                    <h1>Agent Simulation</h1>
                    <p>Dashboard template not found.</p>
                </body>
            </html>
            """
        )

    with open(
        html_path,
        "r",
        encoding="utf-8",
    ) as file:
        return HTMLResponse(
            file.read()
        )


# ---------------------------------------------------------------------
# Command interface
# ---------------------------------------------------------------------

@app.post("/command")
async def command_endpoint(
    request: CommandRequest,
):
    command = request.command.strip()

    if not command:
        raise HTTPException(
            status_code=400,
            detail="Command is required.",
        )

    result = orchestrator.route_command(
        command
    )

    return serialise_result(result)


# ---------------------------------------------------------------------
# System status
# ---------------------------------------------------------------------

@app.get("/api/status")
async def api_status():
    try:
        logs = memory.get_logs(
            limit=50
        )
    except Exception:
        logs = []

    try:
        balance = memory.get_balance()
    except Exception:
        balance = 0.0

    try:
        world_summary = world.get_summary()
    except Exception:
        world_summary = {}

    try:
        economy_report = (
            economy.get_economy_report()
        )
    except Exception:
        economy_report = {}

    try:
        pending = tools.approval_gate.list_pending()
    except Exception:
        pending = []

    return {
        "status": "online",
        "system": {
            "name": "Agent Simulation",
            "version": "2.0.0",
        },
        "safety": get_safety_state(),
        "world": world_summary,
        "economy": economy_report,
        "balance": balance,
        "agents": orchestrator.get_agents(),
        "orchestrator": orchestrator.status(),
        "pending_approvals": len(
            pending
        ),
        "logs": logs,
    }


# ---------------------------------------------------------------------
# Agent endpoints
# ---------------------------------------------------------------------

@app.get("/api/agents")
async def api_agents():
    result = {}

    for name, agent in agents.items():
        try:
            result[name] = (
                agent.get_status_report()
            )
        except Exception as exc:
            result[name] = {
                "status": "error",
                "agent": name,
                "message": str(exc),
            }

    return {
        "status": "success",
        "agents": result,
    }


@app.get("/api/agents/{name}")
async def api_agent(name: str):
    agent = agents.get(name)

    if agent is None:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown agent: {name}",
        )

    return agent.get_status_report()


@app.get("/api/agents/{name}/cognitive")
async def api_agent_cognitive(name: str):
    agent = agents.get(name)

    if agent is None:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown agent: {name}",
        )

    try:
        return {
            "status": "success",
            "agent": name,
            "cognitive": agent.get_cognitive_state(),
        }
    except Exception as exc:
        return {
            "status": "error",
            "agent": name,
            "message": str(exc),
        }


# ---------------------------------------------------------------------
# Tool endpoints
# ---------------------------------------------------------------------

@app.get("/api/tools")
async def api_tools():
    try:
        return {
            "status": "success",
            "tools": tools.list_tools(),
            "capabilities": tools.capabilities(),
        }
    except Exception as exc:
        return {
            "status": "error",
            "message": str(exc),
        }


# ---------------------------------------------------------------------
# Orchestrator endpoints
# ---------------------------------------------------------------------

@app.get("/api/orchestrator")
async def api_orchestrator():
    return orchestrator.status()


@app.post("/api/orchestrator/start")
async def api_orchestrator_start():
    return orchestrator.start()


@app.post("/api/orchestrator/stop")
async def api_orchestrator_stop():
    return orchestrator.stop()


@app.post("/api/orchestrator/cycle")
async def api_orchestrator_cycle(
    request: CommandRequest | None = None,
):
    command = ""

    if request is not None:
        command = request.command.strip()

    return orchestrator.run_cycle(
        command=command
    )


@app.post("/api/orchestrator/task")
async def api_orchestrator_task(
    request: TaskRequest,
):
    return orchestrator.assign_task(
        agent_name=request.agent,
        task=request.task,
        priority=request.priority,
    )


# ---------------------------------------------------------------------
# Mode control
# ---------------------------------------------------------------------

@app.get("/api/mode")
async def api_mode():
    return get_safety_state()


@app.post("/api/mode")
async def api_set_mode(
    request: ModeRequest,
):
    requested = (
        request.mode or ""
    ).strip().lower()

    if requested == "live":
        requested = "real"

    if requested not in {
        "simulation",
        "real",
    }:
        raise HTTPException(
            status_code=400,
            detail=(
                "Mode must be 'simulation' "
                "or 'real'."
            ),
        )

    if requested == "real":
        return {
            "status": "blocked",
            "message": (
                "Real mode cannot be enabled "
                "by an autonomous agent or "
                "ordinary dashboard request. "
                "Creator authentication and "
                "explicit authorization are "
                "required before live operation."
            ),
            "current_mode": economy.get_mode(),
            "safety": get_safety_state(),
        }

    try:
        economy.set_mode(
            "simulation"
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=str(exc),
        )

    memory.log(
        "Creator",
        "Operating mode set to simulation.",
    )

    return {
        "status": "success",
        "message": (
            "Simulation mode enabled."
        ),
        "safety": get_safety_state(),
    }


# ---------------------------------------------------------------------
# Approval endpoints
# ---------------------------------------------------------------------

@app.get("/api/approvals")
async def api_approvals():
    try:
        approvals = (
            tools.approval_gate.list_all()
        )
    except Exception:
        approvals = (
            memory.get_approvals()
        )

    return {
        "status": "success",
        "approvals": [
            approval_response(item)
            for item in approvals
        ],
    }


@app.post(
    "/api/approvals/{approval_id}/approve"
)
async def approve_action(
    approval_id: str,
):
    result = tools.approval_gate.decide(
        approval_id=approval_id,
        decision="approved",
    )

    if not result:
        raise HTTPException(
            status_code=404,
            detail=(
                f"Approval not found: "
                f"{approval_id}"
            ),
        )

    return {
        "status": "success",
        "approval": approval_response(
            result
        ),
        "message": (
            "Exact action approved. "
            "Approval is single-use."
        ),
    }


@app.post(
    "/api/approvals/{approval_id}/deny"
)
async def deny_action(
    approval_id: str,
):
    result = tools.approval_gate.decide(
        approval_id=approval_id,
        decision="denied",
    )

    if not result:
        raise HTTPException(
            status_code=404,
            detail=(
                f"Approval not found: "
                f"{approval_id}"
            ),
        )

    return {
        "status": "success",
        "approval": approval_response(
            result
        ),
        "message": "Action denied.",
    }


# ---------------------------------------------------------------------
# World
# ---------------------------------------------------------------------

@app.get("/api/world")
async def api_world():
    return {
        "status": "success",
        "world": world.get_summary(),
    }


@app.post("/api/advance_time")
async def api_advance_time():
    return world.advance_time()


# ---------------------------------------------------------------------
# Economy
# ---------------------------------------------------------------------

@app.get("/api/economy")
async def api_economy():
    return {
        "status": "success",
        "economy": (
            economy.get_economy_report()
        ),
    }


@app.get("/vault")
async def vault():
    try:
        balance = memory.get_balance()
    except Exception:
        balance = 0.0

    try:
        transactions = (
            memory.get_transactions()
        )
    except Exception:
        transactions = []

    return {
        "status": "success",
        "balance": balance,
        "transactions": transactions,
        "mode": economy.get_mode(),
    }


# ---------------------------------------------------------------------
# InfoFarmer compatibility endpoint
# ---------------------------------------------------------------------

@app.post("/agent/InfoFarmer/note")
async def info_farmer_note(
    request: NoteRequest,
):
    note = request.note.strip()

    if not note:
        raise HTTPException(
            status_code=400,
            detail="Note is required.",
        )

    memory.add_knowledge(
        key=f"manual_note:{datetime_now()}",
        value={
            "source": "Creator",
            "note": note,
        },
    )

    memory.log(
        "InfoFarmer",
        f"Creator note stored: {note}",
    )

    return {
        "status": "success",
        "message": "Note stored.",
        "note": note,
    }


# ---------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------

@app.get("/health")
async def health():
    return {
        "status": "ok",
        "mode": economy.get_mode(),
        "agents": len(agents),
        "orchestrator_running": (
            orchestrator.running
        ),
    }


# ---------------------------------------------------------------------
# Startup
# ---------------------------------------------------------------------

@app.on_event("startup")
async def startup_event():
    memory.log(
        "System",
        "Agent Simulation started.",
    )

    memory.log(
        "System",
        (
            "Creator approval gate active "
            "for consequential actions."
        ),
    )

    memory.log(
        "System",
        (
            f"Registered agents: "
            f"{', '.join(orchestrator.get_agents())}"
        ),
    )


def datetime_now() -> str:
    from datetime import datetime

    return datetime.utcnow().isoformat()


# ---------------------------------------------------------------------
# Server
# ---------------------------------------------------------------------

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
