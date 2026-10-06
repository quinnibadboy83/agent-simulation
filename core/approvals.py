"""
Creator Approval Gate
---------------------

Controls consequential actions.

Every protected action requires:
- exact agent
- exact tool
- exact parameters
- explicit Creator approval
- single-use consumption
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
import copy

from .memory import SharedMemory


class ApprovalGate:
    def __init__(
        self,
        memory: SharedMemory,
    ):
        self.memory = memory

        self.memory.data.setdefault(
            "approvals",
            [],
        )

        self.memory.save()

    def request(
        self,
        tool_name: str,
        reason: str,
        payload: Optional[
            Dict[str, Any]
        ] = None,
        agent: str = "Unknown",
        risk: str = "high",
        plan: Optional[list] = None,
    ) -> Dict[str, Any]:

        approvals = self.memory.data[
            "approvals"
        ]

        next_id = 1

        if approvals:
            ids = []

            for item in approvals:
                try:
                    ids.append(
                        int(
                            item.get(
                                "id",
                                0,
                            )
                        )
                    )
                except (
                    TypeError,
                    ValueError,
                ):
                    continue

            if ids:
                next_id = max(ids) + 1

        item = {
            "id": next_id,
            "agent": agent,
            "tool": tool_name,
            "action": tool_name,
            "reason": reason,
            "description": reason,
            "risk": risk,
            "payload": copy.deepcopy(
                payload or {}
            ),
            "parameters": copy.deepcopy(
                payload or {}
            ),
            "plan": copy.deepcopy(
                plan or []
            ),
            "status": "pending",
            "created_at": self._timestamp(),
            "decided_at": None,
            "consumed_at": None,
            "execution_started": False,
            "execution_result": None,
        }

        approvals.append(item)

        self.memory.save()

        self.memory.log(
            "ApprovalGate",
            (
                "Creator approval requested: "
                f"#{next_id} "
                f"{agent} -> {tool_name}"
            ),
        )

        return copy.deepcopy(
            item
        )

    def get(
        self,
        approval_id: int,
    ) -> Optional[
        Dict[str, Any]
    ]:

        for item in self.memory.data.get(
            "approvals",
            [],
        ):

            try:
                current_id = int(
                    item.get(
                        "id",
                        -1,
                    )
                )
            except (
                TypeError,
                ValueError,
            ):
                continue

            if current_id == int(
                approval_id
            ):
                return copy.deepcopy(
                    item
                )

        return None

    def list_pending(
        self,
    ) -> List[Dict[str, Any]]:

        return [
            copy.deepcopy(item)
            for item in self.memory.data.get(
                "approvals",
                [],
            )
            if item.get("status")
            == "pending"
        ]

    def list_all(
        self,
    ) -> List[Dict[str, Any]]:

        return [
            copy.deepcopy(item)
            for item in self.memory.data.get(
                "approvals",
                [],
            )
        ]

    def decide(
        self,
        approval_id: int,
        allow: bool,
    ) -> str:

        for item in self.memory.data.get(
            "approvals",
            [],
        ):

            try:
                current_id = int(
                    item.get(
                        "id",
                        -1,
                    )
                )
            except (
                TypeError,
                ValueError,
            ):
                continue

            if current_id != int(
                approval_id
            ):
                continue

            if item.get("status") != "pending":
                return (
                    f"Approval #{approval_id} "
                    f"has already been "
                    f"{item.get('status')}."
                )

            item["status"] = (
                "approved"
                if allow
                else "denied"
            )

            item["decided_at"] = (
                self._timestamp()
            )

            self.memory.save()

            self.memory.log(
                "ApprovalGate",
                (
                    "Creator "
                    + (
                        "approved "
                        if allow
                        else "denied "
                    )
                    + f"#{approval_id}"
                ),
            )

            return (
                f"Approval #{approval_id} "
                + (
                    "approved."
                    if allow
                    else "denied."
                )
            )

        return (
            f"No pending approval "
            f"#{approval_id}."
        )

    def validate(
        self,
        approval_id: int,
        tool_name: str,
        agent: str,
        payload: Dict[str, Any],
    ) -> bool:

        item = self.get(
            approval_id
        )

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

        return (
            approved_payload
            == payload
        )

    def consume(
        self,
        approval_id: int,
        tool_name: str,
        agent: str,
        payload: Dict[str, Any],
    ) -> bool:

        for item in self.memory.data.get(
            "approvals",
            [],
        ):

            try:
                current_id = int(
                    item.get(
                        "id",
                        -1,
                    )
                )
            except (
                TypeError,
                ValueError,
            ):
                continue

            if current_id != int(
                approval_id
            ):
                continue

            if item.get("status") != "approved":
                return False

            if item.get("tool") != tool_name:
                return False

            if item.get("agent") != agent:
                return False

            if item.get(
                "payload",
                {},
            ) != payload:
                return False

            if item.get(
                "execution_started",
                False,
            ):
                return False

            item[
                "execution_started"
            ] = True

            item["status"] = "consumed"

            item["consumed_at"] = (
                self._timestamp()
            )

            self.memory.save()

            self.memory.log(
                "ApprovalGate",
                (
                    "Consumed Creator approval "
                    f"#{approval_id} "
                    f"for {tool_name}"
                ),
            )

            return True

        return False

    def mark_execution_result(
        self,
        approval_id: int,
        success: bool,
        result: Any = None,
        error: Optional[str] = None,
    ) -> bool:

        for item in self.memory.data.get(
            "approvals",
            [],
        ):

            try:
                current_id = int(
                    item.get(
                        "id",
                        -1,
                    )
                )
            except (
                TypeError,
                ValueError,
            ):
                continue

            if current_id != int(
                approval_id
            ):
                continue

            item[
                "execution_result"
            ] = {
                "success": bool(
                    success
                ),
                "result": result,
                "error": error,
                "recorded_at": (
                    self._timestamp()
                ),
            }

            self.memory.save()

            return True

        return False

    @staticmethod
    def _timestamp() -> str:
        return datetime.utcnow().isoformat()
