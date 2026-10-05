"""
Creator Approval Gate
---------------------

Controls consequential actions in REAL mode.

Agents may:

    - research
    - reason
    - plan
    - prepare
    - communicate internally

Protected consequential actions require an explicit Creator
approval before execution.

Approvals are:

    - persistent
    - tied to an agent
    - tied to a specific action
    - tied to exact parameters
    - single-use
"""

from datetime import datetime
from typing import Any, Dict, List, Optional


class ApprovalGate:
    def __init__(
        self,
        memory,
    ):
        self.memory = memory

        if "approvals" not in self.memory.data:
            self.memory.data[
                "approvals"
            ] = []

            self.memory.save()

        self._normalise()

    # ------------------------------------------------------------------
    # Normalisation
    # ------------------------------------------------------------------

    def _normalise(self) -> None:
        for item in self.memory.data.get(
            "approvals",
            [],
        ):
            item.setdefault(
                "status",
                "pending",
            )

            item.setdefault(
                "created_at",
                item.get(
                    "timestamp",
                    datetime.utcnow().isoformat(),
                ),
            )

            item.setdefault(
                "updated_at",
                item.get(
                    "created_at"
                ),
            )

            item.setdefault(
                "decision",
                None,
            )

            item.setdefault(
                "decided_by",
                None,
            )

            item.setdefault(
                "decision_reason",
                None,
            )

    # ------------------------------------------------------------------
    # Create request
    # ------------------------------------------------------------------

    def request(
        self,
        action: str,
        description: str,
        parameters: Optional[
            Dict[str, Any]
        ] = None,
        agent: str = "Unknown",
        plan: Optional[
            List[str]
        ] = None,
        risk: str = "medium",
    ) -> Dict[str, Any]:

        approvals = self.memory.data.setdefault(
            "approvals",
            [],
        )

        next_id = 1

        if approvals:
            next_id = max(
                int(
                    item.get(
                        "id",
                        0,
                    )
                )
                for item in approvals
            ) + 1

        now = datetime.utcnow().isoformat()

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
            "created_at": now,
            "updated_at": now,
        }

        approvals.append(
            item
        )

        self.memory.data[
            "approvals"
        ] = approvals[-200:]

        self.memory.log(
            "ApprovalGate",
            (
                f"Approval requested "
                f"#{next_id}: {action} "
                f"by {agent}"
            ),
        )

        self.memory.save()

        return item

    # ------------------------------------------------------------------
    # Query
    # ------------------------------------------------------------------

    def get_pending(
        self,
    ) -> List[Dict[str, Any]]:
        return [
            item
            for item in self.memory.data.get(
                "approvals",
                [],
            )
            if item.get(
                "status"
            ) == "pending"
        ]

    def list_pending(
        self,
    ) -> List[Dict[str, Any]]:
        return self.get_pending()

    def get(
        self,
        approval_id: int,
    ) -> Optional[Dict[str, Any]]:
        for item in self.memory.data.get(
            "approvals",
            [],
        ):
            if int(
                item.get(
                    "id",
                    0,
                )
            ) == int(
                approval_id
            ):
                return item

        return None

    # ------------------------------------------------------------------
    # Decisions
    # ------------------------------------------------------------------

    def approve(
        self,
        approval_id: int,
        decided_by: str = "Creator",
        reason: str = "",
    ) -> Optional[
        Dict[str, Any]
    ]:
        item = self.get(
            approval_id
        )

        if item is None:
            return None

        if item.get(
            "status"
        ) != "pending":
            return item

        item["status"] = "approved"
        item["decision"] = "approved"
        item["decided_by"] = decided_by
        item["decision_reason"] = reason
        item["updated_at"] = (
            datetime.utcnow().isoformat()
        )

        self.memory.log(
            "Creator",
            (
                f"APPROVED action "
                f"#{approval_id}: "
                f"{item.get('action')}"
            ),
        )

        self.memory.save()

        return item

    def deny(
        self,
        approval_id: int,
        decided_by: str = "Creator",
        reason: str = "",
    ) -> Optional[
        Dict[str, Any]
    ]:
        item = self.get(
            approval_id
        )

        if item is None:
            return None

        if item.get(
            "status"
        ) != "pending":
            return item

        item["status"] = "denied"
        item["decision"] = "denied"
        item["decided_by"] = decided_by
        item["decision_reason"] = reason
        item["updated_at"] = (
            datetime.utcnow().isoformat()
        )

        self.memory.log(
            "Creator",
            (
                f"DENIED action "
                f"#{approval_id}: "
                f"{item.get('action')}"
            ),
        )

        self.memory.save()

        return item

    # Backwards-compatible interface.
    def decide(
        self,
        approval_id: int,
        allow: bool,
    ) -> str:
        if allow:
            result = self.approve(
                approval_id
            )
        else:
            result = self.deny(
                approval_id
            )

        if result is None:
            return (
                f"No approval #{approval_id}."
            )

        return (
            f"Approval #{approval_id} "
            f"{result.get('status')}."
        )

    # ------------------------------------------------------------------
    # Single-use execution
    # ------------------------------------------------------------------

    def consume_approval(
        self,
        approval_id: int,
    ) -> bool:
        item = self.get(
            approval_id
        )

        if item is None:
            return False

        if item.get(
            "status"
        ) != "approved":
            return False

        item["status"] = "consumed"
        item["updated_at"] = (
            datetime.utcnow().isoformat()
        )

        self.memory.log(
            "ApprovalGate",
            (
                f"Consumed approval "
                f"#{approval_id}"
            ),
        )

        self.memory.save()

        return True

    def reject_execution(
        self,
        approval_id: int,
    ) -> bool:
        item = self.get(
            approval_id
        )

        if item is None:
            return False

        item["status"] = "execution_failed"
        item["updated_at"] = (
            datetime.utcnow().isoformat()
        )

        self.memory.save()

        return True
