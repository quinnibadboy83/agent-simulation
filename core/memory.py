"""
Shared Memory / Blackboard System
---------------------------------

Central persistent state shared by all agents.

Stores:
- world state
- agent status
- knowledge
- tasks
- transactions
- logs
- Creator approvals

The memory layer is deliberately simple and persistent so the
simulation can recover its state after a restart.
"""

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
import json


class SharedMemory:
    def __init__(
        self,
        persist_path: str = "data/memory.json",
    ):
        self.persist_path = Path(persist_path)

        self.persist_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        self.data: Dict[str, Any] = {
            "world_state": {},
            "agent_status": {},
            "knowledge": [],
            "tasks": [],
            "transactions": [],
            "logs": [],
            "approvals": [],
        }

        self._load()
        self._ensure_structure()

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _load(self) -> None:
        if not self.persist_path.exists():
            return

        try:
            with open(
                self.persist_path,
                "r",
                encoding="utf-8",
            ) as file:
                loaded = json.load(file)

            if isinstance(loaded, dict):
                self.data = loaded

        except (
            OSError,
            json.JSONDecodeError,
            TypeError,
            ValueError,
        ):
            # Do not allow a corrupt persistence file to prevent
            # the application from starting.
            self.data = {}

    def _ensure_structure(self) -> None:
        defaults = {
            "world_state": {},
            "agent_status": {},
            "knowledge": [],
            "tasks": [],
            "transactions": [],
            "logs": [],
            "approvals": [],
        }

        for key, default in defaults.items():
            if key not in self.data:
                self.data[key] = default

            elif not isinstance(
                self.data[key],
                type(default),
            ):
                self.data[key] = default

    def save(self) -> None:
        self.persist_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        temporary_path = self.persist_path.with_suffix(
            ".tmp"
        )

        with open(
            temporary_path,
            "w",
            encoding="utf-8",
        ) as file:
            json.dump(
                self.data,
                file,
                indent=2,
                default=str,
            )

        temporary_path.replace(
            self.persist_path
        )

    # ------------------------------------------------------------------
    # World State
    # ------------------------------------------------------------------

    def set_world_state(
        self,
        key: str,
        value: Any,
    ) -> None:
        self.data["world_state"][key] = value
        self.save()

    def get_world_state(
        self,
        key: Optional[str] = None,
        default: Any = None,
    ) -> Any:
        if key is None:
            return self.data["world_state"]

        return self.data["world_state"].get(
            key,
            default,
        )

    # ------------------------------------------------------------------
    # Knowledge
    # ------------------------------------------------------------------

    def add_knowledge(
        self,
        source: str,
        content: str,
        tags: Optional[List[str]] = None,
    ) -> Dict[str, Any]:

        existing_ids = [
            int(item.get("id", 0))
            for item in self.data["knowledge"]
            if str(item.get("id", "")).isdigit()
        ]

        next_id = (
            max(existing_ids) + 1
            if existing_ids
            else 1
        )

        entry = {
            "id": next_id,
            "timestamp": self._timestamp(),
            "source": source,
            "content": content,
            "tags": tags or [],
        }

        self.data["knowledge"].append(entry)

        self.save()

        return entry

    def get_knowledge(
        self,
        tags: Optional[List[str]] = None,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:

        items = self.data["knowledge"]

        if tags:
            items = [
                item
                for item in items
                if any(
                    tag in item.get("tags", [])
                    for tag in tags
                )
            ]

        return items[-limit:]

    # ------------------------------------------------------------------
    # Tasks
    # ------------------------------------------------------------------

    def add_task(
        self,
        title: str,
        description: str,
        assigned_to: str,
        created_by: str = "Boss",
    ) -> Dict[str, Any]:

        existing_ids = [
            int(item.get("id", 0))
            for item in self.data["tasks"]
            if str(item.get("id", "")).isdigit()
        ]

        next_id = (
            max(existing_ids) + 1
            if existing_ids
            else 1
        )

        now = self._timestamp()

        task = {
            "id": next_id,
            "title": title,
            "description": description,
            "assigned_to": assigned_to,
            "created_by": created_by,
            "status": "pending",
            "created_at": now,
            "updated_at": now,
        }

        self.data["tasks"].append(task)

        self.save()

        return task

    def update_task(
        self,
        task_id: int,
        status: str,
        notes: str = "",
    ) -> Optional[Dict[str, Any]]:

        for task in self.data["tasks"]:
            try:
                current_id = int(
                    task.get("id", -1)
                )
            except (
                TypeError,
                ValueError,
            ):
                continue

            if current_id != int(task_id):
                continue

            task["status"] = status
            task["updated_at"] = self._timestamp()

            if notes:
                task["notes"] = notes

            self.save()

            return task

        return None

    def get_tasks(
        self,
        assigned_to: Optional[str] = None,
        status: Optional[str] = None,
    ) -> List[Dict[str, Any]]:

        tasks = self.data["tasks"]

        if assigned_to:
            tasks = [
                task
                for task in tasks
                if task.get("assigned_to")
                == assigned_to
            ]

        if status:
            tasks = [
                task
                for task in tasks
                if task.get("status")
                == status
            ]

        return tasks

    # ------------------------------------------------------------------
    # Agent Status
    # ------------------------------------------------------------------

    def set_agent_status(
        self,
        agent_name: str,
        status: Dict[str, Any],
    ) -> None:

        self.data["agent_status"][agent_name] = {
            **status,
            "last_updated": self._timestamp(),
        }

        self.save()

    def get_agent_status(
        self,
        agent_name: str,
    ) -> Dict[str, Any]:

        return self.data["agent_status"].get(
            agent_name,
            {},
        )

    def get_all_agent_status(
        self,
    ) -> Dict[str, Any]:

        return self.data["agent_status"]

    # ------------------------------------------------------------------
    # Transactions / Money
    # ------------------------------------------------------------------

    def add_transaction(
        self,
        amount: float,
        from_agent: str,
        to_agent: str,
        reason: str,
    ) -> Dict[str, Any]:

        existing_ids = [
            int(item.get("id", 0))
            for item in self.data["transactions"]
            if str(item.get("id", "")).isdigit()
        ]

        next_id = (
            max(existing_ids) + 1
            if existing_ids
            else 1
        )

        transaction = {
            "id": next_id,
            "timestamp": self._timestamp(),
            "amount": float(amount),
            "from": from_agent,
            "to": to_agent,
            "reason": reason,
        }

        self.data["transactions"].append(
            transaction
        )

        self.save()

        return transaction

    def get_balance(
        self,
        agent_name: str = "Banker",
    ) -> float:

        balance = 0.0

        for transaction in self.data[
            "transactions"
        ]:
            if transaction.get("to") == agent_name:
                balance += float(
                    transaction.get(
                        "amount",
                        0.0,
                    )
                )

            if transaction.get("from") == agent_name:
                balance -= float(
                    transaction.get(
                        "amount",
                        0.0,
                    )
                )

        return balance

    # ------------------------------------------------------------------
    # Logs
    # ------------------------------------------------------------------

    def log(
        self,
        agent: str,
        message: str,
        level: str = "info",
    ) -> Dict[str, Any]:

        entry = {
            "timestamp": self._timestamp(),
            "agent": agent,
            "level": level,
            "message": message,
        }

        self.data["logs"].append(entry)

        self.data["logs"] = (
            self.data["logs"][-200:]
        )

        self.save()

        return entry

    def get_logs(
        self,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:

        return self.data["logs"][-limit:]

    # ------------------------------------------------------------------
    # Creator Approval Helpers
    # ------------------------------------------------------------------

    def get_approvals(
        self,
        status: Optional[str] = None,
    ) -> List[Dict[str, Any]]:

        approvals = self.data.get(
            "approvals",
            [],
        )

        if status is None:
            return approvals

        return [
            approval
            for approval in approvals
            if approval.get("status")
            == status
        ]

    # ------------------------------------------------------------------
    # Utility
    # ------------------------------------------------------------------

    @staticmethod
    def _timestamp() -> str:
        return datetime.utcnow().isoformat()
