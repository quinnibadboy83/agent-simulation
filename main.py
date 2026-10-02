"""
Agent Simulation - Module 1 Core
Mobile-first web interface + multi-agent system
"""

from fastapi import FastAPI, Request, Form
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, JSONResponse
import uvicorn
from pathlib import Path

from core.memory import SharedMemory
from core.world import World
from core.tools import create_default_tools
from agents.boss import BossAgent
from agents.banker import BankerAgent
from agents.info_farmer import InfoFarmerAgent

# ---------- Setup ----------
app = FastAPI(title="Agent Simulation - Module 1")

BASE_DIR = Path(__file__).parent
app.mount("/static", StaticFiles(directory=BASE_DIR / "ui" / "static"), name="static")
templates = Jinja2Templates(directory=BASE_DIR / "ui" / "templates")

# Global systems (in real production we would use proper dependency injection)
memory = SharedMemory()
world = World(memory)
tools = create_default_tools(memory, world)

boss = BossAgent(memory, tools)
banker = BankerAgent(memory, tools)
info_farmer = InfoFarmerAgent(memory, tools)

agents = {
    "Boss": boss,
    "Banker": banker,
    "InfoFarmer": info_farmer,
}


# ---------- Routes ----------
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    world_summary = world.get_summary()
    agent_status = memory.get_all_agent_status()
    recent_logs = memory.get_logs(30)
    balance = memory.get_balance("Banker")
    knowledge_count = len(memory.data.get("knowledge", []))
    pending_tasks = memory.get_tasks(status="pending")

    return templates.TemplateResponse("index.html", {
        "request": request,
        "world": world_summary,
        "agents": agent_status,
        "logs": recent_logs,
        "balance": balance,
        "knowledge_count": knowledge_count,
        "pending_tasks": pending_tasks,
    })


@app.post("/command")
async def send_command(command: str = Form(...)):
    """Player types a command → Boss processes it."""
    if not command.strip():
        return JSONResponse({"response": "Empty command."})

    response = boss.process_command(command)
    
    # Also give the relevant agent a chance to react if it was a direct order
    return JSONResponse({
        "response": response,
        "balance": memory.get_balance("Banker"),
        "knowledge_count": len(memory.data.get("knowledge", [])),
    })


@app.get("/api/status")
async def api_status():
    return {
        "world": world.get_summary(),
        "agents": memory.get_all_agent_status(),
        "balance": memory.get_balance("Banker"),
        "knowledge_count": len(memory.data.get("knowledge", [])),
        "pending_tasks": memory.get_tasks(status="pending"),
        "logs": memory.get_logs(20),
    }


@app.post("/api/advance_time")
async def advance_time():
    world.advance_time()
    return {"message": "Time advanced", "world": world.get_summary()}


if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 8000))
    print("\n" + "="*50)
    print("  AGENT SIMULATION - MODULE 1")
    print(f"  Running on port {port}")
    print("="*50 + "\n")
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)
