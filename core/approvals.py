"""
Creator Approval System
-----------------------

Controls real-world actions that require explicit approval from the
Creator before an agent is allowed to execute them.

Agents may think, research, plan and prepare actions autonomously.

Consequential external actions must pass through this gate.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional


class ApprovalGate:
    """
    Persistent Creator approval queue.

    The gate deliberately separates:
        1. Agent planning
        2. Creator approval
        3. Actual tool execution

    An approval request is never considered approved merely because
    the agent requested it.
    """

    def __init__(self, memory):
        self.memory = memory

        if "approvals" not in self.memory.data:
            self.memory.data["approvals"] = []

        self._normalise_existing_requests()

    def _normalise_existing_requests(self) -> None:
        """
        Keep older/incomplete approval records compatible with the
        current system.
        """
        for item in self.memory.data.get("approvals", []):
            item.setdefault("status", "pending")
            item.setdefault("created_at", item.get("timestamp", datetime.utcnow().isoformat()))
            item.setdefault("updated_at", item.get("created_at"))
            item.setdefault("decision", None)
            item.setdefault("decided_by", None)
            item.setdefault("decision_reason", None)

    def request(
        self,
        action: str,
        description: str,
        parameters: Optional[Dict[str, Any]] = None,
        agent: str = "Unknown",
        plan: Optional[List[str]] = None,
        risk: str = "medium",
    ) -> Dict[str, Any]:
        """
        Create a new pending Creator approval request.
        """

        approvals = self.memory.data.setdefault("approvals", [])

        next_id = 1
        if approvals:
            next_id = max(
                int(item.get("id", 0))
                for item in approvals
            ) + 1

        item = {
            "id": next_id,
            "action": action,
            "description": description,
            "parameters": parameters or {},
            "agent": agent,
            "plan": plan or [],
            "risk": risk,
            "status": "pending",
            "decision": None,
            "decided_by": None,
            "decision_reason": None,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
        }

        approvals.append(item)

        # Keep the queue bounded.
        self.memory.data["approvals"] = approvals[-200:]

        self.memory.log(
            "ApprovalGate",
            f"Approval requested #{next_id}: {action} by {agent}",
        )

        self.memory.save()

        return item

    def get_pending(self) -> List[Dict[str, Any]]:
        """
        Return all requests currently waiting for Creator approval.
        """
        return [
            item
            for item in self.memory.data.get("approvals", [])
            if item.get("status") == "pending"
        ]

    def get(self, approval_id: int) -> Optional[Dict[str, Any]]:
        """
        Find an approval request by ID.
        """
        for item in self.memory.data.get("approvals", []):
            if int(item.get("id", 0)) == int(approval_id):
                return item

        return None

    def approve(
        self,
        approval_id: int,
        decided_by: str = "Creator",
        reason: str = "",
    ) -> Optional[Dict[str, Any]]:
        """
        Approve one specific request.
        """
        item = self.get(approval_id)

        if item is None:
            return None

        if item.get("status") != "pending":
            return item

        item["status"] = "approved"
        item["decision"] = "approved"
        item["decided_by"] = decided_by
        item["decision_reason"] = reason
        item["updated_at"] = datetime.utcnow().isoformat()

        self.memory.log(
            "Creator",
            f"APPROVED action #{approval_id}: {item.get('action')}",
        )

        self.memory.save()

        return item

    def deny(
        self,
        approval_id: int,
        decided_by: str = "Creator",
        reason: str = "",
    ) -> Optional[Dict[str, Any]]:
        """
        Deny one specific request.
        """
        item = self.get(approval_id)

        if item is None:
            return None

        if item.get("status") != "pending":
            return item

        item["status"] = "denied"
        item["decision"] = "denied"
        item["decided_by"] = decided_by
        item["decision_reason"] = reason
        item["updated_at"] = datetime.utcnow().isoformat()

        self.memory.log(
            "Creator",
            f"DENIED action #{approval_id}: {item.get('action')}",
        )

        self.memory.save()

        return item

    def consume_approval(self, approval_id: int) -> bool:
        """
        Consume an approved request immediately before execution.

        This prevents the same approval from being reused indefinitely.
        """
        item = self.get(approval_id)

        if item is None:
            return False

        if item.get("status") != "approved":
            return False

        item["status"] = "consumed"
        item["updated_at"] = datetime.utcnow().isoformat()

        self.memory.log(
            "ApprovalGate",
            f"Consumed approval #{approval_id}",
        )

        self.memory.save()

        return True

    def reject_execution(self, approval_id: int) -> bool:
        """
        Mark an approved request as rejected if execution failed or
        was otherwise prevented.
        """
        item = self.get(approval_id)

        if item is None:
            return False

        item["status"] = "execution_failed"
        item["updated_at"] = datetime.utcnow().isoformat()

        self.memory.save()

        return True



