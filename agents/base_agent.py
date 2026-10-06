"""
Base Agent
----------
Shared cognitive and task-management foundation for all agents.

Agent lifecycle:

Perceive
    ↓
Remember
    ↓
Reason
    ↓
Plan
    ↓
Select Tool
    ↓
Execute / Request Approval
    ↓
Observe
    ↓
Learn
    ↓
Repeat
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from core.cognitive_room import CognitiveRoom


class BaseAgent:
    def __init__(
        self,
        name: str,
        role: str,
        memory,
        tools,
        description: str = "",
    ):
        self.name = name
        self.role = role
        self.memory = memory
        self.tools = tools
        self.description = description

        self.identity = {
            "name": name,
            "role": role,
            "description": description,
        }

        self.room = CognitiveRoom(
            agent_name=name,
            role=role,
            description=description,
        )

        self.current_task: Optional[Dict[str, Any]] = None
        self.status = "idle"

        self._publish_status()

    # -----------------------------------------------------------------
    # Cognitive lifecycle
    # -----------------------------------------------------------------

    def perceive(
        self,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        if context is None:
            context = {}

        observation = {
            "timestamp": self._timestamp(),
            "agent": self.name,
            "context": context,
        }

        self.room.observe(
            observation
        )

        return observation

    def remember(
        self,
        information: Any,
        key: str = "",
    ) -> Dict[str, Any]:
        if key:
            self.memory.add_knowledge(
                key=key,
                value=information,
            )
        else:
            self.room.remember(
                information
            )

        return {
            "status": "success",
            "agent": self.name,
            "remembered": information,
        }

    def think(
        self,
        thought: str,
    ) -> Dict[str, Any]:
        thought = (thought or "").strip()

        if not thought:
            return {
                "status": "error",
                "agent": self.name,
                "message": "Thought is required.",
            }

        self.room.think(
            thought
        )

        return {
            "status": "success",
            "agent": self.name,
            "thought": thought,
        }

    def plan(
        self,
        steps: List[str],
    ) -> Dict[str, Any]:
        if not isinstance(
            steps,
            list,
        ):
            return {
                "status": "error",
                "agent": self.name,
                "message": "Plan steps must be a list.",
            }

        clean_steps = [
            str(step).strip()
            for step in steps
            if str(step).strip()
        ]

        self.room.set_plan(
            clean_steps
        )

        return {
            "status": "success",
            "agent": self.name,
            "plan": clean_steps,
        }

    # -----------------------------------------------------------------
    # Tool execution
    # -----------------------------------------------------------------

    def execute_tool(
        self,
        tool_name: str,
        approval_id: str = "",
        **kwargs,
    ) -> Dict[str, Any]:
        self.status = "working"
        self._publish_status()

        try:
            result = self.tools.execute(
                tool_name=tool_name,
                agent=self.name,
                approval_id=approval_id,
                **kwargs,
            )

            self.observe_result(
                result
            )

            return result

        finally:
            self.status = "idle"
            self._publish_status()

    def request_tool_approval(
        self,
        tool_name: str,
        reason: str,
        payload: Optional[Dict[str, Any]] = None,
        risk: str = "medium",
        plan: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        if payload is None:
            payload = {}

        if plan is None:
            plan = []

        return self.tools.request_approval(
            agent=self.name,
            tool=tool_name,
            reason=reason,
            payload=payload,
            risk=risk,
            plan=plan,
        )

    def observe_result(
        self,
        result: Any,
    ) -> Dict[str, Any]:
        observation = {
            "timestamp": self._timestamp(),
            "agent": self.name,
            "result": result,
        }

        self.room.observe(
            observation
        )

        return observation

    # -----------------------------------------------------------------
    # Task management
    # -----------------------------------------------------------------

    def create_task(
        self,
        description: str,
        priority: str = "normal",
    ) -> Dict[str, Any]:
        description = (
            description or ""
        ).strip()

        if not description:
            return {
                "status": "error",
                "agent": self.name,
                "message": "Task description is required.",
            }

        priority = (
            priority or "normal"
        ).strip().lower()

        try:
            task_id = self.memory.add_task(
                self.name,
                description,
                priority=priority,
            )
        except TypeError:
            task_id = self.memory.add_task(
                {
                    "agent": self.name,
                    "description": description,
                    "priority": priority,
                    "status": "pending",
                }
            )

        return {
            "status": "success",
            "agent": self.name,
            "task_id": task_id,
            "description": description,
            "priority": priority,
        }

    def get_tasks(
        self,
    ) -> List[Dict[str, Any]]:
        try:
            tasks = self.memory.get_tasks()

        except Exception:
            return []

        if not isinstance(
            tasks,
            list,
        ):
            return []

        return [
            task
            for task in tasks
            if self._task_belongs_to_agent(task)
        ]

    def get_pending_tasks(
        self,
    ) -> List[Dict[str, Any]]:
        pending = []

        for task in self.get_tasks():
            status = str(
                task.get(
                    "status",
                    "pending",
                )
            ).lower()

            if status in {
                "pending",
                "queued",
                "assigned",
                "in_progress",
            }:
                pending.append(task)

        return pending

    def set_current_task(
        self,
        task: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        self.current_task = task

        if task is None:
            self.status = "idle"
            self._publish_status()

            return {
                "status": "success",
                "agent": self.name,
                "current_task": None,
            }

        self.status = "working"

        self._publish_status()

        return {
            "status": "success",
            "agent": self.name,
            "current_task": task,
        }

    def complete_current_task(
        self,
        result: Any = None,
    ) -> Dict[str, Any]:
        if self.current_task is None:
            return {
                "status": "error",
                "agent": self.name,
                "message": "No current task.",
            }

        task_id = self.current_task.get(
            "id",
            self.current_task.get(
                "task_id"
            ),
        )

        if task_id:
            try:
                self.memory.update_task(
                    task_id,
                    {
                        "status": "completed",
                        "result": result,
                        "completed_at": self._timestamp(),
                    },
                )
            except TypeError:
                try:
                    self.memory.update_task(
                        task_id,
                        status="completed",
                        result=result,
                        completed_at=self._timestamp(),
                    )
                except Exception:
                    pass
            except Exception:
                pass

        completed = self.current_task

        self.current_task = None
        self.status = "idle"
        self._publish_status()

        return {
            "status": "success",
            "agent": self.name,
            "task": completed,
            "result": result,
        }

    def fail_current_task(
        self,
        reason: str,
    ) -> Dict[str, Any]:
        reason = (
            reason or "Unknown failure"
        ).strip()

        if self.current_task is None:
            return {
                "status": "error",
                "agent": self.name,
                "message": "No current task.",
            }

        task_id = self.current_task.get(
            "id",
            self.current_task.get(
                "task_id"
            ),
        )

        if task_id:
            try:
                self.memory.update_task(
                    task_id,
                    {
                        "status": "failed",
                        "error": reason,
                        "failed_at": self._timestamp(),
                    },
                )
            except Exception:
                pass

        failed = self.current_task

        self.current_task = None
        self.status = "idle"
        self._publish_status()

        return {
            "status": "error",
            "agent": self.name,
            "task": failed,
            "message": reason,
        }

    # -----------------------------------------------------------------
    # Objectives
    # -----------------------------------------------------------------

    def set_objective(
        self,
        objective: str,
    ) -> Dict[str, Any]:
        objective = (
            objective or ""
        ).strip()

        if not objective:
            return {
                "status": "error",
                "agent": self.name,
                "message": "Objective is required.",
            }

        self.room.set_objective(
            objective
        )

        return {
            "status": "success",
            "agent": self.name,
            "objective": objective,
        }

    def get_objective(self) -> str:
        return self.room.objective

    def clear_objective(self) -> Dict[str, Any]:
        self.room.clear_objective()

        return {
            "status": "success",
            "agent": self.name,
            "objective": "",
        }

    # -----------------------------------------------------------------
    # Messages
    # -----------------------------------------------------------------

    def receive_message(
        self,
        message: str,
        sender: str = "System",
    ) -> Dict[str, Any]:
        message = (
            message or ""
        ).strip()

        if not message:
            return {
                "status": "error",
                "agent": self.name,
                "message": "Message is required.",
            }

        self.room.receive_message(
            message=message,
            sender=sender,
        )

        return {
            "status": "success",
            "agent": self.name,
            "sender": sender,
            "message": message,
        }

    def unread_messages(
        self,
    ) -> List[Dict[str, Any]]:
        try:
            return self.room.unread_messages()
        except Exception:
            return []

    # -----------------------------------------------------------------
    # Status
    # -----------------------------------------------------------------

    def update_status(
        self,
        status: str,
    ) -> Dict[str, Any]:
        status = (
            status or "idle"
        ).strip().lower()

        self.status = status
        self._publish_status()

        return {
            "status": "success",
            "agent": self.name,
            "state": status,
        }

    def _publish_status(self):
        try:
            self.memory.set_agent_status(
                self.name,
                {
                    "status": self.status,
                    "role": self.role,
                    "current_task": self.current_task,
                    "updated_at": self._timestamp(),
                },
            )
        except TypeError:
            try:
                self.memory.set_agent_status(
                    self.name,
                    self.status,
                )
            except Exception:
                pass
        except Exception:
            pass

    def get_status_report(
        self,
    ) -> Dict[str, Any]:
        return {
            "status": "success",
            "agent": self.name,
            "role": self.role,
            "description": self.description,
            "state": self.status,
            "current_task": self.current_task,
            "objective": self.get_objective(),
            "pending_tasks": len(
                self.get_pending_tasks()
            ),
            "unread_messages": len(
                self.unread_messages()
            ),
        }

    def get_help(self) -> Dict[str, Any]:
        return {
            "status": "success",
            "agent": self.name,
            "role": self.role,
            "description": self.description,
            "commands": [
                "status",
                "run",
                "help",
            ],
        }

    def get_cognitive_state(
        self,
    ) -> Dict[str, Any]:
        try:
            return self.room.snapshot()
        except Exception:
            return {
                "agent": self.name,
                "role": self.role,
                "status": self.status,
                "objective": self.get_objective(),
            }

    # -----------------------------------------------------------------
    # Autonomous cycle
    # -----------------------------------------------------------------

    def run_cycle(self) -> Dict[str, Any]:
        started = self._timestamp()

        self.status = "thinking"
        self._publish_status()

        try:
            context = {
                "agent": self.name,
                "role": self.role,
                "status": self.status,
                "current_task": self.current_task,
                "pending_tasks": self.get_pending_tasks(),
                "unread_messages": self.unread_messages(),
                "objective": self.get_objective(),
            }

            self.perceive(
                context
            )

            pending = self.get_pending_tasks()

            if pending and self.current_task is None:
                self.set_current_task(
                    pending[0]
                )

            self.think(
                (
                    f"Autonomous cycle started. "
                    f"Pending tasks: {len(pending)}."
                )
            )

            if self.current_task is not None:
                plan = self._default_task_plan(
                    self.current_task
                )

                self.plan(
                    plan
                )

            result = {
                "status": "success",
                "agent": self.name,
                "operation": "cycle",
                "started_at": started,
                "completed_at": self._timestamp(),
                "pending_tasks": len(
                    self.get_pending_tasks()
                ),
                "current_task": self.current_task,
                "message": (
                    "Cognitive cycle completed. "
                    "No consequential action was "
                    "performed automatically."
                ),
            }

            self.observe_result(
                result
            )

            return result

        except Exception as exc:
            self.memory.log(
                self.name,
                (
                    f"Autonomous cycle error: "
                    f"{exc}"
                ),
            )

            return {
                "status": "error",
                "agent": self.name,
                "message": str(exc),
            }

        finally:
            self.status = "idle"
            self._publish_status()

    # -----------------------------------------------------------------
    # Internal helpers
    # -----------------------------------------------------------------

    def _task_belongs_to_agent(
        self,
        task: Dict[str, Any],
    ) -> bool:
        if not isinstance(
            task,
            dict,
        ):
            return False

        owner = task.get(
            "agent",
            task.get(
                "assigned_to",
                task.get(
                    "owner"
                ),
            ),
        )

        return owner == self.name

    def _default_task_plan(
        self,
        task: Dict[str, Any],
    ) -> List[str]:
        description = task.get(
            "description",
            task.get(
                "task",
                "Complete assigned task.",
            ),
        )

        return [
            f"Understand task: {description}",
            "Gather relevant information.",
            "Evaluate available options.",
            "Prepare a safe action plan.",
            "Execute only permitted operations.",
            "Record the result.",
        ]

    @staticmethod
    def _timestamp() -> str:
        return datetime.utcnow().isoformat()
