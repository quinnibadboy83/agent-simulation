"""
Agent Simulation API
--------------------
FastAPI entry point for the autonomous multi-agent system.

Architecture:

Creator
   ↓
Action Gate
   ↓
Orchestrator
   ↓
Agents
   ↓
Cognitive Rooms / Shared Memory
   ↓
Tools / Research / Economy
   ↓
Results

Consequential external actions remain approval-gated.
"""

from datetime import datetime
from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi import Request
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


# ---------------------------------------------------------------------
# Application
# ---------------------------------------------------------------------

app = FastAPI(
    title="Autonomous Agent Simulation",
    description=(
        "Multi-agent cognitive simulation with shared memory, "
        "research, economy, orchestration, and Creator approval."
    ),
    version="1.0.0",
)

templates = Jinja2Templates(directory="ui/templates")


# ---------------------------------------------------------------------
# Core systems
# ---------------------------------------------------------------------

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
    "Boss": boss,
    "Banker": banker,
    "InfoFarmer": info_farmer,
    "OpportunityAgent": opportunity_agent,
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
    agent: str = ""


class ModeRequest(BaseModel):
    mode: str


class ApprovalRequest(BaseModel):
    reason: str = ""


class TaskRequest(BaseModel):
    agent: str
    task: str
    priority: str = "normal"


class NoteRequest(BaseModel):
    topic: str
    content: str


# ---------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
        },
    )


# ---------------------------------------------------------------------
# Command API
# ---------------------------------------------------------------------

@app.post("/command")
async def command_endpoint(request: CommandRequest):
    command = request.command.strip()

    if not command:
        raise HTTPException(
            status_code=400,
            detail="Command cannot be empty.",
        )

    result = orchestrator.route_command(
        command=command,
        agent_name=request.agent.strip(),
    )

    return result


# ---------------------------------------------------------------------
# System status
# ---------------------------------------------------------------------

@app.get("/api/status")
async def api_status():
    return {
        "status": "online",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "mode": economy.get_mode(),
        "orchestrator": orchestrator.status(),
        "world": world.get_summary(),
        "economy": economy.get_economy_report(),
        "agents": {
            name: agent.get_status_report()
            for name, agent in agents.items()
        },
        "pending_approvals": len(
            tools.approval_gate.list_pending()
        ),
    }


# ---------------------------------------------------------------------
# Agents
# ---------------------------------------------------------------------

@app.get("/api/agents")
async def api_agents():
    return {
        name: agent.get_status_report()
        for name, agent in agents.items()
    }


@app.get("/api/agents/{name}")
async def api_agent(name: str):
    if name not in agents:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown agent: {name}",
        )

    return agents[name].get_status_report()


@app.get("/api/agents/{name}/cognitive")
async def api_agent_cognitive(name: str):
    if name not in agents:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown agent: {name}",
        )

    return agents[name].get_cognitive_state()


# ---------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------

@app.get("/api/tools")
async def api_tools():
    return {
        "tools": tools.list_tools(),
        "capabilities": tools.capabilities(),
        "mode": tools.get_mode(),
    }


# ---------------------------------------------------------------------
# Orchestrator API
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
    request: Optional[CommandRequest] = None,
):
    if request is None:
        return orchestrator.run_cycle()

    return orchestrator.run_cycle(
        command=request.command,
        agent_name=request.agent,
    )


@app.post("/api/orchestrator/task")
async def api_orchestrator_task(request: TaskRequest):
    return orchestrator.assign_task(
        agent_name=request.agent,
        task=request.task,
        priority=request.priority,
    )


@app.post("/api/orchestrator/broadcast")
async def api_orchestrator_broadcast(
    request: CommandRequest,
):
    return orchestrator.broadcast(
        request.command,
    )


# ---------------------------------------------------------------------
# Operating mode
# ---------------------------------------------------------------------

@app.get("/api/mode")
async def api_mode():
    return {
        "mode": economy.get_mode(),
        "policy": economy.get_mode_policy(),
        "live_tools_enabled": economy.can_use_live_tools(),
        "creator_approval_required": (
            economy.requires_creator_approval()
        ),
    }


@app.post("/api/mode")
async def api_set_mode(request: ModeRequest):
    requested_mode = request.mode.strip().lower()

    if requested_mode in {"real", "live"}:
        return {
            "status": "blocked",
            "mode": economy.get_mode(),
            "message": (
                "Real/live mode cannot be enabled through this "
                "endpoint. Creator authentication and explicit "
                "authorization are required."
            ),
            "creator_approval_required": True,
        }

    if requested_mode != "simulation":
        raise HTTPException(
            status_code=400,
            detail=(
                "Invalid mode. Use 'simulation'. "
                "Real/live mode requires Creator authorization."
            ),
        )

    economy.set_mode("simulation")

    return {
        "status": "success",
        "mode": economy.get_mode(),
        "message": "Simulation mode enabled.",
    }


# ---------------------------------------------------------------------
# Approval API
# ---------------------------------------------------------------------

@app.get("/api/approvals")
async def api_approvals():
    return {
        "pending": tools.approval_gate.list_pending(),
        "all": tools.approval_gate.list_all(),
    }


@app.post("/api/approvals/{approval_id}/approve")
async def approve_action(
    approval_id: str,
    request: ApprovalRequest,
):
    result = tools.approval_gate.decide(
        approval_id=approval_id,
        decision="approved",
        reason=request.reason,
    )

    if result.get("status") == "error":
        raise HTTPException(
            status_code=400,
            detail=result,
        )

    return result


@app.post("/api/approvals/{approval_id}/deny")
async def deny_action(
    approval_id: str,
    request: ApprovalRequest,
):
    result = tools.approval_gate.decide(
        approval_id=approval_id,
        decision="denied",
        reason=request.reason,
    )

    if result.get("status") == "error":
        raise HTTPException(
            status_code=400,
            detail=result,
        )

    return result


# ---------------------------------------------------------------------
# World
# ---------------------------------------------------------------------

@app.get("/api/world")
async def api_world():
    return world.get_summary()


@app.post("/api/advance_time")
async def api_advance_time():
    return world.advance_time()


# ---------------------------------------------------------------------
# Economy
# ---------------------------------------------------------------------

@app.get("/api/economy")
async def api_economy():
    return economy.get_economy_report()


@app.get("/api/economy/vault")
async def api_vault():
    return {
        "balance": memory.get_balance(),
        "mode": economy.get_mode(),
    }


# ---------------------------------------------------------------------
# InfoFarmer
# ---------------------------------------------------------------------

@app.post("/agent/InfoFarmer/note")
async def info_farmer_note(request: NoteRequest):
    if not request.topic.strip():
        raise HTTPException(
            status_code=400,
            detail="Topic is required.",
        )

    if not request.content.strip():
        raise HTTPException(
            status_code=400,
            detail="Content is required.",
        )

    result = memory.add_knowledge(
        key=request.topic.strip(),
        value={
            "content": request.content.strip(),
            "source": "Creator",
            "timestamp": datetime.utcnow().isoformat() + "Z",
        },
    )

    return {
        "status": "success",
        "topic": request.topic.strip(),
        "result": result,
    }


# ---------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "service": "agent-simulation",
        "mode": economy.get_mode(),
        "agents": len(agents),
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }


# ---------------------------------------------------------------------
# Startup
# ---------------------------------------------------------------------

@app.on_event("startup")
async def startup_event():
    print("=" * 60)
    print("AUTONOMOUS AGENT SIMULATION")
    print("=" * 60)
    print(f"Mode: {economy.get_mode()}")
    print(f"Agents: {', '.join(agents.keys())}")
    print("Orchestrator: READY")
    print("Creator Approval Gate: READY")
    print("Research System: READY")
    print("Economy System: READY")
    print("=" * 60)


# ---------------------------------------------------------------------
# Local execution
# ---------------------------------------------------------------------

if __name__ == "__main__":
    import os
    import uvicorn

    port = int(os.environ.get("PORT", "8000"))

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=False,
    )
