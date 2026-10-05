"""
Creator Approval Gate
---------------------

Controls consequential actions in the agent system.

Rules:

- Agents may request an approval.
- The Creator decides whether it is allowed.
- Approval is tied to the exact agent, tool and parameters.
- An approval can only be consumed once.
- Approvals cannot be reused for a different action.
- Simulation-safe actions do not need Creator approval.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
import copy

from .memory import SharedMemory


class ApprovalGate:
    """
    Central Creator approval system.

    This class deliberately does not execute tools.

    It only manages:
        REQUEST
        APPROVE
        DENY
        CONSUME

    Tool execution remains the responsibility of ToolRegistry.
    """

    def __init__(self, memory: SharedMemory):
        self.memory = memory

        self.memory.data.setdefault(
            "approvals",
            [],
        )

        self.memory.save()

    # ------------------------------------------------------------------
    # REQUEST
    # ------------------------------------------------------------------

    def request(
        self,
        tool_name: str,
        reason: str,
        payload: Optional[Dict[str, Any]] = None,
        agent: str = "Unknown",
        risk: str = "high",
    ) -> Dict[str, Any]:
        """
        Create a new pending Creator approval.

        Every request receives its own immutable snapshot of the
        requested action parameters.
        """

        approvals = self.memory.data["approvals"]

        next_id = 1

        if approvals:
            next_id = max(
                int(item.get("id", 0))
                for item in approvals
            ) + 1

        item = {
            "id": next_id,
            "agent": agent,
            "tool": tool_name,
            "reason": reason,
            "risk": risk,
            "payload": copy.deepcopy(payload or {}),
            "status": "pending",
            "created_at": self._timestamp(),
            "decided_at": None,
            "consumed_at": None,
            "execution_started": False,
        }

        approvals.append(item)

        self.memory.save()

        self.memory.log(
            "ApprovalGate",
            (
                f"Creator approval requested: "
                f"#{next_id} "
                f"{agent} -> {tool_name}"
            ),
        )

        return copy.deepcopy(item)

    # ------------------------------------------------------------------
    # READ
    # ------------------------------------------------------------------

    def get(
        self,
        approval_id: int,
    ) -> Optional[Dict[str, Any]]:
        for item in self.memory.data.get(
            "approvals",
            [],
        ):
            if int(item.get("id", -1)) == int(approval_id):
                return copy.deepcopy(item)

        return None

    def list_pending(self) -> List[Dict[str, Any]]:
        return [
            copy.deepcopy(item)
            for item in self.memory.data.get(
                "approvals",
                [],
            )
            if item.get("status") == "pending"
        ]

    def list_all(self) -> List[Dict[str, Any]]:
        return [
            copy.deepcopy(item)
            for item in self.memory.data.get(
                "approvals",
                [],
            )
        ]

    # ------------------------------------------------------------------
    # DECISION
    # ------------------------------------------------------------------

    def decide(
        self,
        approval_id: int,
        allow: bool,
    ) -> str:
        """
        Approve or deny a pending request.

        An already decided request cannot be changed.
        """

        for item in self.memory.data.get(
            "approvals",
            [],
        ):
            if int(item.get("id", -1)) != int(approval_id):
                continue

            if item.get("status") != "pending":
                return (
                    f"Approval #{approval_id} has already been "
                    f"{item.get('status')}."
                )

            item["status"] = (
                "approved"
                if allow
                else "denied"
            )

            item["decided_at"] = self._timestamp()

            self.memory.save()

            self.memory.log(
                "ApprovalGate",
                (
                    f"Creator "
                    f"{'approved' if allow else 'denied'} "
                    f"#{approval_id}"
                ),
            )

            return (
                f"Approval #{approval_id} "
                f"{'approved' if allow else 'denied'}."
            )

        return f"No pending approval #{approval_id}."

    # ------------------------------------------------------------------
    # VALIDATION
    # ------------------------------------------------------------------

    def validate(
        self,
        approval_id: int,
        tool_name: str,
        agent: str,
        payload: Dict[str, Any],
    ) -> bool:
        """
        Check that an approval exactly matches the action attempting
        to consume it.

        This prevents an approval for one action being substituted
        for another action.
        """

        item = self.get(approval_id)

        if not item:
            return False

        if item.get("status") != "approved":
            return False

        if item.get("tool") != tool_name:
            return False

        if item.get("agent") != agent:
            return False

        approved_payload = item.get(
            "payload",
            {},
        )

        return approved_payload == payload

    # ------------------------------------------------------------------
    # CONSUME
    # ------------------------------------------------------------------

    def consume(
        self,
        approval_id: int,
        tool_name: str,
        agent: str,
        payload: Dict[str, Any],
    ) -> bool:
        """
        Consume an approved action.

        Consumption happens BEFORE the protected tool executes.

        This is intentional.

        If the external action subsequently fails, the approval is
        still consumed and cannot silently be reused.
        """

        for item in self.memory.data.get(
            "approvals",
            [],
        ):
            if int(item.get("id", -1)) != int(approval_id):
                continue

            if item.get("status") != "approved":
                return False

            if item.get("tool") != tool_name:
                return False

            if item.get("agent") != agent:
                return False

            if item.get("payload", {}) != payload:
                return False

            if item.get("execution_started"):
                return False

            item["execution_started"] = True
            item["status"] = "consumed"
            item["consumed_at"] = self._timestamp()

            self.memory.save()

            self.memory.log(
                "ApprovalGate",
                (
                    f"Consumed Creator approval "
                    f"#{approval_id} for {tool_name}"
                ),
            )

            return True

        return False

    # ------------------------------------------------------------------
    # EXECUTION RESULT
    # ------------------------------------------------------------------

    def mark_execution_result(
        self,
        approval_id: int,
        success: bool,
        result: Any = None,
        error: Optional[str] = None,
    ) -> bool:
        """
        Record the result of an action whose approval has already
        been consumed.

        The approval itself remains consumed regardless of success.
        """

        for item in self.memory.data.get(
            "approvals",
            [],
        ):
            if int(item.get("id", -1)) != int(approval_id):
                continue

            item["execution_result"] = {
                "success": bool(success),
                "result": result,
                "error": error,
                "recorded_at": self._timestamp(),
            }

            self.memory.save()

            return True

        return False

    # ------------------------------------------------------------------
    # INTERNAL
    # ------------------------------------------------------------------

    @staticmethod
    def _timestamp() -> str:
        return datetime.utcnow().isoformat()
