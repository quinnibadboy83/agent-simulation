"""Approval gate. High-risk tools wait for you."""

from datetime import datetime
from typing import Any, Dict, Optional
from .memory import SharedMemory


class ApprovalGate:
    def __init__(self, memory: SharedMemory):
        self.memory = memory
        if "approvals" not in self.memory.data:
            self.memory.data["approvals"] = []
            self.memory.save()

    def request(self, tool_name: str, reason: str, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        item = {
            "id": len(self.memory.data["approvals"]) + 1,
            "tool": tool_name,
            "reason": reason,
            "payload": payload or {},
            "status": "pending",
            "created_at": datetime.utcnow().isoformat(),
        }
        self.memory.data["approvals"].append(item)
        self.memory.save()
        self.memory.log("ApprovalGate", f"Pending #{item['id']} for {tool_name}")
        return item

    def list_pending(self):
        return [a for a in self.memory.data.get("approvals", []) if a["status"] == "pending"]

    def decide(self, approval_id: int, allow: bool) -> str:
        for item in self.memory.data.get("approvals", []):
            if item["id"] == approval_id and item["status"] == "pending":
                item["status"] = "approved" if allow else "denied"
                item["decided_at"] = datetime.utcnow().isoformat()
                self.memory.save()
                self.memory.log("ApprovalGate", f"#{approval_id} {item['status']}")
                return f"Approval #{approval_id} {item['status']}."
        return f"No pending approval #{approval_id}."
