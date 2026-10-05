"""
Shared Memory / Blackboard
--------------------------

Persistent shared state used by every agent.

The memory system stores:

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

        self.data.setdefault(
            "world_state",
            {},
        )

        self.data.setdefault(
            "agent_status",
            {},
        )

        self.data.setdefault(
            "knowledge",
            [],
        )

        self.data.setdefault(
            "tasks",
            [],
        )

        self.data.setdefault(
            "transactions",
            [],
        )

        self.data.setdefault(
            "logs",
            [],
        )

        self.data.setdefault(
            "approvals",
            [])

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

            if isinstance(
                loaded,
                dict,
            ):
                self.data = loaded

        except Exception:
            # A corrupted memory file should not prevent the application
            # from starting.
            self.data = {
                "world_state": {},
                "agent_status": {},
                "knowledge": [],
                "tasks": [],
                "transactions": [],
                "logs": [],
                "approvals": [],
            }

    def save(self) -> None:
        with open(
            self.persist_path,
            "w",
            encoding="utf-8",
        ) as file:
            json.dump(
                self.data,
                file,
                indent=2,
                default=str,
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
        entry = {
            "id": len(
                self.data["knowledge"]
            ) + 1,
            "timestamp": datetime.utcnow().isoformat(),
            "source": source,
            "content": content,
            "tags": tags or [],
        }

        self.data["knowledge"].append(
            entry
        )

        self.save()

        return entry

    def get_knowledge(
        self,
        tags: Optional[List[str]] = None,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        items = self.data[
            "knowledge"
        ]

        if tags:
            items = [
                item
                for item in items
                if any(
                    tag in item.get(
                        "tags",
                        [],
                    )
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
        task = {
            "id": len(
                self.data["tasks"]
            ) + 1,
            "title": title,
            "description": description,
            "assigned_to": assigned_to,
            "created_by": created_by,
            "status": "pending",
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
        }

        self.data["tasks"].append(
            task
        )

        self.save()

        return task

    def update_task(
        self,
        task_id: int,
        status: str,
        notes: str = "",
    ) -> Optional[Dict[str, Any]]:
        for task in self.data[
            "tasks"
        ]:
            if task["id"] == task_id:
                task["status"] = status
                task["updated_at"] = (
                    datetime.utcnow().isoformat()
                )

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
        tasks = self.data[
            "tasks"
        ]

        if assigned_to:
            tasks = [
                task
                for task in tasks
                if task.get(
                    "assigned_to"
                ) == assigned_to
            ]

        if status:
            tasks = [
                task
                for task in tasks
                if task.get(
                    "status"
                ) == status
            ]

        return tasks

    # ------------------------------------------------------------------
    # Agent status
    # ------------------------------------------------------------------

    def set_agent_status(
        self,
        agent_name: str,
        status: Dict[str, Any],
    ) -> None:
        self.data[
            "agent_status"
        ][agent_name] = {
            **status,
            "last_updated": (
                datetime.utcnow().isoformat()
            ),
        }

        self.save()

    def get_agent_status(
        self,
        agent_name: str,
    ) -> Dict[str, Any]:
        return self.data[
            "agent_status"
        ].get(
            agent_name,
            {},
        )

    def get_all_agent_status(
        self,
    ) -> Dict[str, Any]:
        return self.data[
            "agent_status"
        ]

    # ------------------------------------------------------------------
    # Transactions
    # ------------------------------------------------------------------

    def add_transaction(
        self,
        amount: float,
        from_agent: str,
        to_agent: str,
        reason: str,
    ) -> Dict[str, Any]:
        transaction = {
            "id": len(
                self.data["transactions"]
            ) + 1,
            "timestamp": datetime.utcnow().isoformat(),
            "amount": amount,
            "from": from_agent,
            "to": to_agent,
            "reason": reason,
        }

        self.data[
            "transactions"
        ].append(
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
            if transaction[
                "to"
            ] == agent_name:
                balance += transaction[
                    "amount"
                ]

            if transaction[
                "from"
            ] == agent_name:
                balance -= transaction[
                    "amount"
                ]

        return balance

    # ------------------------------------------------------------------
    # Logging
    # ------------------------------------------------------------------

    def log(
        self,
        agent: str,
        message: str,
        level: str = "info",
    ) -> Dict[str, Any]:
        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "agent": agent,
            "level": level,
            "message": message,
        }

        self.data[
            "logs"
        ].append(
            entry
        )

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
    ) -> List[Dict[str, Any]]:
        return self.data[
            "logs"
        ][-limit:]
