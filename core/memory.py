"""
Shared Memory / Blackboard system.
All agents read and write here.
"""

from typing import Any, Dict, List, Optional
from datetime import datetime
import json
from pathlib import Path


class SharedMemory:
    def __init__(self, persist_path: str = "data/memory.json"):
        self.persist_path = Path(persist_path)
        self.persist_path.parent.mkdir(parents=True, exist_ok=True)
        
        self.data: Dict[str, Any] = {
            "world_state": {},
            "agent_status": {},
            "knowledge": [],
            "tasks": [],
            "transactions": [],
            "logs": [],
        }
        
        self._load()

    def _load(self):
        if self.persist_path.exists():
            try:
                with open(self.persist_path, "r", encoding="utf-8") as f:
                    self.data = json.load(f)
            except Exception:
                pass

    def save(self):
        with open(self.persist_path, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=2, default=str)

    def add_knowledge(self, source: str, content: str, tags: Optional[List[str]] = None):
        entry = {
            "id": len(self.data["knowledge"]) + 1,
            "timestamp": datetime.utcnow().isoformat(),
            "source": source,
            "content": content,
            "tags": tags or [],
        }
        self.data["knowledge"].append(entry)
        self.save()
        return entry

    def get_knowledge(self, tags: Optional[List[str]] = None, limit: int = 20) -> List[Dict]:
        items = self.data["knowledge"]
        if tags:
            items = [k for k in items if any(t in k.get("tags", []) for t in tags)]
        return items[-limit:]

    def add_task(self, title: str, description: str, assigned_to: str, created_by: str = "Boss"):
        task = {
            "id": len(self.data["tasks"]) + 1,
            "title": title,
            "description": description,
            "assigned_to": assigned_to,
            "created_by": created_by,
            "status": "pending",
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
        }
        self.data["tasks"].append(task)
        self.save()
        return task

    def update_task(self, task_id: int, status: str, notes: str = ""):
        for task in self.data["tasks"]:
            if task["id"] == task_id:
                task["status"] = status
                task["updated_at"] = datetime.utcnow().isoformat()
                if notes:
                    task["notes"] = notes
                self.save()
                return task
        return None

    def get_tasks(self, assigned_to: Optional[str] = None, status: Optional[str] = None):
        tasks = self.data["tasks"]
        if assigned_to:
            tasks = [t for t in tasks if t["assigned_to"] == assigned_to]
        if status:
            tasks = [t for t in tasks if t["status"] == status]
        return tasks

    def set_agent_status(self, agent_name: str, status: Dict[str, Any]):
        self.data["agent_status"][agent_name] = {
            **status,
            "last_updated": datetime.utcnow().isoformat()
        }
        self.save()

    def get_agent_status(self, agent_name: str) -> Dict[str, Any]:
        return self.data["agent_status"].get(agent_name, {})

    def get_all_agent_status(self) -> Dict[str, Any]:
        return self.data["agent_status"]

    def add_transaction(self, amount: float, from_agent: str, to_agent: str, reason: str):
        tx = {
            "id": len(self.data["transactions"]) + 1,
            "timestamp": datetime.utcnow().isoformat(),
            "amount": amount,
            "from": from_agent,
            "to": to_agent,
            "reason": reason,
        }
        self.data["transactions"].append(tx)
        self.save()
        return tx

    def get_balance(self, agent_name: str = "Banker") -> float:
        balance = 0.0
        for tx in self.data["transactions"]:
            if tx["to"] == agent_name:
                balance += tx["amount"]
            if tx["from"] == agent_name:
                balance -= tx["amount"]
        return balance

    def log(self, agent: str, message: str, level: str = "info"):
        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "agent": agent,
            "level": level,
            "message": message,
        }
        self.data["logs"].append(entry)
        self.data["logs"] = self.data["logs"][-200:]
        self.save()
        return entry

    def get_logs(self, limit: int = 50) -> List[Dict]:
        return self.data["logs"][-limit:]
