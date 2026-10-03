"""
Agent Simulation - Module 1 + Module 2 (Dual Mode Economy)
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
from core.tools import create_default_tools
from agents.boss import BossAgent
from agents.banker import BankerAgent
from agents.info_farmer import InfoFarmerAgent
from agents.opportunity_agent import OpportunityAgent

# ---------- Setup ----------
app = FastAPI(title="Agent Simulation - Module 2")

BASE_DIR = Path(__file__).parent
app.mount("/static", StaticFiles(directory=BASE_DIR / "ui" / "static"), name="static")
templates = Jinja2Templates(directory=BASE_DIR / "ui" / "templates")

# Global systems
memory = SharedMemory()
world = World(memory)
economy = Economy(memory)
tools = create_default_tools(memory, world, economy)

boss = BossAgent(memory, tools)
banker = BankerAgent(memory, tools)
info_farmer = InfoFarmerAgent(memory, tools)
opportunity_agent = OpportunityAgent(memory, tools, economy)

agents = {
    "Boss": boss,
    "Banker": banker,
    "InfoFarmer": info_farmer,
    "OpportunityAgent": opportunity_agent,
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
    economy_report = economy.get_economy_report()

    return templates.TemplateResponse("index.html", {
        "request": request,
        "world": world_summary,
        "agents": agent_status,
        "logs": recent_logs,
        "balance": balance,
        "knowledge_count": knowledge_count,
        "pending_tasks": pending_tasks,
        "economy": economy_report,
    })


@app.post("/command")
async def send_command(command: str = Form(...)):
    if not command.strip():
        return JSONResponse({"response": "Empty command."})

    response = boss.process_command(command)
    
    return JSONResponse({
        "response": response,
        "balance": memory.get_balance("Banker"),
        "knowledge_count": len(memory.data
