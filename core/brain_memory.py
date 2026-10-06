from __future__ import annotations

from typing import Any, Dict, List, Optional


class BrainMemory:
    """
    Cognitive-memory adapter.

    Keeps the LLM context separate from the underlying SharedMemory
    implementation so the brain can evolve without rewriting the
    persistence layer.
    """

    def __init__(
        self,
        memory=None,
        room=None,
        max_items: int = 20,
    ):
        self.memory = memory
        self.room = room
        self.max_items = max_items

    def system_context(
        self,
        agent_name: str,
        objective: Optional[str] = None,
    ) -> str:

        sections: List[str] = []

        sections.append(
            f"Agent identity: {agent_name}"
        )

        if objective:
            sections.append(
                f"Current objective: {objective}"
            )

        sections.append(
            "Operating rules:"
        )

        sections.append(
            "- Reason independently about the objective."
        )

        sections.append(
            "- Use tools when information is missing."
        )

        sections.append(
            "- Delegate when another specialist is better suited."
        )

        sections.append(
            "- Do not invent tool results."
        )

        sections.append(
            "- Do not claim an action happened unless the tool confirms it."
        )

        sections.append(
            "- Consequential live actions require Creator approval."
        )

        sections.append(
            "- Research and analysis may be performed autonomously."
        )

        sections.append(
            "- Continue working when additional information is useful."
        )

        context = self.recent_context()

        if context:
            sections.append(
                "Recent cognitive context:"
            )

            sections.extend(context)

        return "\n".join(sections)

    def recent_context(self) -> List[str]:
        items: List[str] = []

        if self.room is not None:
            snapshot = self._room_snapshot()

            if snapshot:
                items.append(
                    "Private cognitive room:\n"
                    + self._compact(snapshot)
                )

        if self.memory is not None:
            knowledge = self._knowledge()

            if knowledge:
                items.append(
                    "Shared knowledge:\n"
                    + self._compact(knowledge)
                )

            tasks = self._tasks()

            if tasks:
                items.append(
                    "Known tasks:\n"
                    + self._compact(tasks)
                )

            logs = self._logs()

            if logs:
                items.append(
                    "Recent system observations:\n"
                    + self._compact(logs)
                )

        return items[-self.max_items:]

    def remember(
        self,
        content: Any,
    ) -> None:

        if self.room is not None:
            method = getattr(
                self.room,
                "remember",
                None,
            )

            if callable(method):
                try:
                    method(content)
                    return
                except Exception:
                    pass

        if self.memory is not None:
            method = getattr(
                self.memory,
                "add_knowledge",
                None,
            )

            if callable(method):
                try:
                    method(
                        topic="brain",
                        content=str(content),
                    )
                except TypeError:
                    try:
                        method(
                            "brain",
                            str(content),
                        )
                    except Exception:
                        pass
                except Exception:
                    pass

    def observe(
        self,
        observation: Any,
    ) -> None:

        if self.room is not None:
            method = getattr(
                self.room,
                "observe",
                None,
            )

            if callable(method):
                try:
                    method(observation)
                    return
                except Exception:
                    pass

        self.remember(
            f"Observation: {observation}"
        )

    def _room_snapshot(self) -> Any:
        method = getattr(
            self.room,
            "snapshot",
            None,
        )

        if callable(method):
            try:
                return method()
            except Exception:
                return None

        return None

    def _knowledge(self) -> Any:
        method = getattr(
            self.memory,
            "get_knowledge",
            None,
        )

        if not callable(method):
            return None

        try:
            return method()
        except TypeError:
            try:
                return method(
                    topic="brain"
                )
            except Exception:
                return None
        except Exception:
            return None

    def _tasks(self) -> Any:
        method = getattr(
            self.memory,
            "get_tasks",
            None,
        )

        if not callable(method):
            return None

        try:
            return method()
        except Exception:
            return None

    def _logs(self) -> Any:
        method = getattr(
            self.memory,
            "get_logs",
            None,
        )

        if not callable(method):
            return None

        try:
            return method(
                limit=self.max_items
            )
        except TypeError:
            try:
                return method()
            except Exception:
                return None
        except Exception:
            return None

    @staticmethod
    def _compact(
        value: Any,
        max_chars: int = 6000,
    ) -> str:

        text = str(value)

        if len(text) <= max_chars:
            return text

        return text[:max_chars] + "\n...[truncated]"
