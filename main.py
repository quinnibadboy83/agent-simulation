"""
Agent Simulation - Module 1 + 2 + 3 (Web Research)
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

app = FastAPI(title="Agent Simulation - Module 3")

BASE_DIR = Path(__file__).parent
app.mount("/static", StaticFiles(directory=BASE_DIR / "ui" / "static"), name="static")
templates = Jinja2Templates(directory=BASE_DIR / "ui" / "templates")

memory = SharedMemory()
world = World(memory)
economy = Economy(memory)
research = WebResearch(memory)
tools = create_default_tools(memory, world, economy, research)

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
        "knowledge_count": len(memory.data.get("knowledge", [])),
        "economy_mode": economy.get_mode(),
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
        "economy": economy.get_economy_report(),
    }


@app.post("/api/advance_time")
async def advance_time():
    world.advance_time()
    return {"message": "Time advanced", "world": world.get_summary()}


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)
