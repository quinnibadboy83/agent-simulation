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
        self.persist_path = Path(
            persist_path
        )

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

        self.save()

    # =========================================================
    # STORAGE
    # =========================================================

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

            if isinstance(
                loaded,
                dict,
            ):
                self.data = loaded

        except (
            OSError,
            json.JSONDecodeError,
            TypeError,
            ValueError,
        ):
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
                continue

            if not isinstance(
                self.data[key],
                type(default),
            ):
                self.data[key] = default

    def save(self) -> None:
        self.persist_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        temporary_path = (
            self.persist_path.with_suffix(
                ".tmp"
            )
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

    # =========================================================
    # WORLD STATE
    # =========================================================

    def set_world_state(
        self,
        key: str,
        value: Any,
    ):
        self.data[
            "world_state"
        ][key] = value

        self.save()

        return value

    def get_world_state(
        self,
        key: Optional[str] = None,
        default: Any = None,
    ):
        if key is None:
            return self.data[
                "world_state"
            ]

        return self.data[
            "world_state"
        ].get(
            key,
            default,
        )

    # =========================================================
    # KNOWLEDGE
    # =========================================================

    def add_knowledge(
        self,
        source: str,
        content: str,
        tags: Optional[List[str]] = None,
    ):

        existing_ids = []

        for item in self.data[
            "knowledge"
        ]:
            try:
                existing_ids.append(
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

        next_id = (
            max(existing_ids) + 1
            if existing_ids
            else 1
        )

        entry = {
            "id": next_id,
            "timestamp": (
                self._timestamp()
            ),
            "source": source,
            "content": content,
            "tags": tags or [],
            "archived": False,
        }

        self.data[
            "knowledge"
        ].append(entry)

        self.save()

        return entry

    def get_knowledge(
        self,
        tags: Optional[List[str]] = None,
        limit: int = 20,
    ):

        items = self.data[
            "knowledge"
        ]

        if tags:
            items = [
                item
                for item in items
                if any(
                    tag
                    in item.get(
                        "tags",
                        [],
                    )
                    for tag in tags
                )
            ]

        return items[-limit:]

    # =========================================================
    # TASKS
    # =========================================================

    def add_task(
        self,
        title: str,
        description: str,
        assigned_to: str,
        created_by: str = "Boss",
    ):

        existing_ids = []

        for item in self.data[
            "tasks"
        ]:
            try:
                existing_ids.append(
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
            "notes": "",
        }

        self.data[
            "tasks"
        ].append(task)

        self.save()

        self.log(
            created_by,
            (
                f"Created task #{next_id} "
                f"for {assigned_to}: {title}"
            ),
        )

        return task

    def update_task(
        self,
        task_id: int,
        status: str,
        notes: str = "",
    ):

        for task in self.data[
            "tasks"
        ]:

            try:
                current_id = int(
                    task.get(
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
                task_id
            ):
                continue

            task["status"] = status
            task["updated_at"] = (
                self._timestamp()
            )

            if notes:
                task["notes"] = notes

            self.save()

            self.log(
                "TaskSystem",
                (
                    f"Task #{task_id} "
                    f"changed to {status}"
                ),
            )

            return task

        return None

    def get_tasks(
        self,
        assigned_to: Optional[str] = None,
        status: Optional[str] = None,
    ):

        tasks = self.data[
            "tasks"
        ]

        if assigned_to:
            tasks = [
                task
                for task in tasks
                if task.get(
                    "assigned_to"
                )
                == assigned_to
            ]

        if status:
            tasks = [
                task
                for task in tasks
                if task.get(
                    "status"
                )
                == status
            ]

        return tasks

    def get_task(
        self,
        task_id: int,
    ):

        for task in self.data[
            "tasks"
        ]:
            try:
                current_id = int(
                    task.get(
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
                task_id
            ):
                return task

        return None

    # =========================================================
    # AGENT STATUS
    # =========================================================

    def set_agent_status(
        self,
        agent_name: str,
        status: Dict[str, Any],
    ):

        self.data[
            "agent_status"
        ][agent_name] = {
            **status,
            "last_updated": (
                self._timestamp()
            ),
        }

        self.save()

    def get_agent_status(
        self,
        agent_name: str,
    ):

        return self.data[
            "agent_status"
        ].get(
            agent_name,
            {},
        )

    def get_all_agent_status(
        self,
    ):

        return self.data[
            "agent_status"
        ]

    # =========================================================
    # TRANSACTIONS
    # =========================================================

    def add_transaction(
        self,
        amount: float,
        from_agent: str,
        to_agent: str,
        reason: str,
    ):

        existing_ids = []

        for item in self.data[
            "transactions"
        ]:
            try:
                existing_ids.append(
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

        next_id = (
            max(existing_ids) + 1
            if existing_ids
            else 1
        )

        transaction = {
            "id": next_id,
            "timestamp": (
                self._timestamp()
            ),
            "amount": float(amount),
            "from": from_agent,
            "to": to_agent,
            "reason": reason,
        }

        self.data[
            "transactions"
        ].append(transaction)

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

            if transaction.get(
                "to"
            ) == agent_name:
                balance += float(
                    transaction.get(
                        "amount",
                        0.0,
                    )
                )

            if transaction.get(
                "from"
            ) == agent_name:
                balance -= float(
                    transaction.get(
                        "amount",
                        0.0,
                    )
                )

        return balance

    # =========================================================
    # LOGGING
    # =========================================================

    def log(
        self,
        agent: str,
        message: str,
        level: str = "info",
    ):

        entry = {
            "timestamp": (
                self._timestamp()
            ),
            "agent": agent,
            "level": level,
            "message": message,
        }

        self.data[
            "logs"
        ].append(entry)

        self.data[
            "logs"
        ] = self.data[
            "logs"
        ][-200:]

        self.save()

        return entry

    def get_logs(
        self,
        limit: int = 50,
    ):

        return self.data[
            "logs"
        ][-limit:]

    # =========================================================
    # APPROVALS
    # =========================================================

    def get_approvals(
        self,
        status: Optional[str] = None,
    ):

        approvals = self.data.get(
            "approvals",
            [],
        )

        if status is None:
            return approvals

        return [
            approval
            for approval in approvals
            if approval.get(
                "status"
            )
            == status
        ]

    # =========================================================
    # UTILITY
    # =========================================================

    def clear_runtime_logs(self):
        self.data["logs"] = []
        self.save()

    @staticmethod
    def _timestamp():
        return datetime.utcnow().isoformat()
