from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .experience_memory import ExperienceMemory
from .learning_coordinator import LearningCoordinator
from .knowledge_store import KnowledgeStore


class LearningCycleError(Exception):
    """Raised when a learning cycle cannot be completed."""


class LearningCycle:
    """
    Controlled learning-cycle manager.

    The learning cycle sits above the individual learning components.

    It provides a stable application-level interface for:

        experiences
            ↓
        evaluation
            ↓
        lessons
            ↓
        knowledge consolidation

    It deliberately does not invoke the LLM.

    This keeps learning deterministic and safe while the underlying
    model-runtime architecture continues to evolve.
    """

    def __init__(
        self,
        experience_memory: ExperienceMemory,
        knowledge_store: Optional[
            KnowledgeStore
        ] = None,
        learning_coordinator: Optional[
            LearningCoordinator
        ] = None,
    ):
        if not isinstance(
            experience_memory,
            ExperienceMemory,
        ):
            raise LearningCycleError(
                "experience_memory must be an "
                "ExperienceMemory instance."
            )

        self.experience_memory = (
            experience_memory
        )

        self.knowledge_store = (
            knowledge_store
            if knowledge_store is not None
            else KnowledgeStore()
        )

        self.learning_coordinator = (
            learning_coordinator
            if learning_coordinator is not None
            else LearningCoordinator(
                experience_memory=(
                    self.experience_memory
                ),
                knowledge_store=(
                    self.knowledge_store
                ),
            )
        )

        self.cycle_count = 0

        self.last_cycle_at: Optional[str] = None

        self.last_result: Optional[
            Dict[str, Any]
        ] = None

    # ------------------------------------------------------------------
    # Single-agent learning
    # ------------------------------------------------------------------

    def run_agent(
        self,
        agent_name: str,
        limit: int = 50,
    ) -> Dict[str, Any]:
        """
        Run a learning cycle for one agent.
        """

        agent_name = (
            agent_name or ""
        ).strip()

        if not agent_name:
            raise LearningCycleError(
                "agent_name cannot be empty."
            )

        started_at = (
            datetime.now(
                timezone.utc
            ).isoformat()
        )

        try:
            result = (
                self.learning_coordinator.learn_agent(
                    agent_name=agent_name,
                    limit=limit,
                )
            )

            result = {
                **result,
                "status": "success",
                "started_at": started_at,
                "completed_at": (
                    datetime.now(
                        timezone.utc
                    ).isoformat()
                ),
            }

        except Exception as exc:
            result = {
                "status": "error",
                "agent_name": agent_name,
                "started_at": started_at,
                "completed_at": (
                    datetime.now(
                        timezone.utc
                    ).isoformat()
                ),
                "message": str(exc),
            }

        self.cycle_count += 1

        self.last_cycle_at = (
            datetime.now(
                timezone.utc
            ).isoformat()
        )

        self.last_result = result

        return result

    # ------------------------------------------------------------------
    # Multiple agents
    # ------------------------------------------------------------------

    def run_agents(
        self,
        agent_names: List[str],
        limit: int = 50,
    ) -> Dict[str, Any]:
        """
        Run learning cycles for multiple agents.

        One agent failing does not prevent the remaining agents from
        being processed.
        """

        if not isinstance(
            agent_names,
            list,
        ):
            raise LearningCycleError(
                "agent_names must be a list."
            )

        results: List[
            Dict[str, Any]
        ] = []

        for agent_name in agent_names:
            cleaned = (
                str(agent_name or "").strip()
            )

            if not cleaned:
                continue

            result = self.run_agent(
                agent_name=cleaned,
                limit=limit,
            )

            results.append(
                result
            )

        return {
            "status": "success",
            "agents_requested": len(
                agent_names
            ),
            "agents_processed": len(
                results
            ),
            "results": results,
            "completed_at": (
                datetime.now(
                    timezone.utc
                ).isoformat()
            ),
        }

    # ------------------------------------------------------------------
    # All-agent learning
    # ------------------------------------------------------------------

    def run_all(
        self,
        limit: int = 50,
    ) -> Dict[str, Any]:
        """
        Discover agents from stored experience and run learning for
        each one.

        This allows the eventual Orchestrator to trigger learning
        without needing to maintain a separate hard-coded agent list.
        """

        agents = (
            self._discover_agents()
        )

        if not agents:
            result = {
                "status": "success",
                "agents_requested": 0,
                "agents_processed": 0,
                "results": [],
                "message": (
                    "No agents with stored experiences "
                    "were found."
                ),
                "completed_at": (
                    datetime.now(
                        timezone.utc
                    ).isoformat()
                ),
            }

            self.last_result = result

            return result

        return self.run_agents(
            agent_names=agents,
            limit=limit,
        )

    # ------------------------------------------------------------------
    # Discovery
    # ------------------------------------------------------------------

    def _discover_agents(self) -> List[str]:
        """
        Discover distinct agents from recent experiences.

        ExperienceMemory intentionally remains the source of truth
        for experience discovery.
        """

        try:
            experiences = (
                self.experience_memory.recent(
                    limit=1000
                )
            )

        except Exception as exc:
            raise LearningCycleError(
                "Unable to discover agents from "
                f"experience memory: {exc}"
            ) from exc

        agents: List[str] = []

        for experience in experiences:
            agent_name = (
                experience.agent_name
                or ""
            ).strip()

            if not agent_name:
                continue

            if agent_name not in agents:
                agents.append(
                    agent_name
                )

        return agents

    # ------------------------------------------------------------------
    # Statistics
    # ------------------------------------------------------------------

    def statistics(
        self,
        agent_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Return learning-system statistics.
        """

        experience_stats = (
            self.experience_memory.statistics(
                agent_name=agent_name
            )
        )

        knowledge_stats = (
            self.knowledge_store.statistics(
                agent_name=agent_name
            )
        )

        return {
            "agent_name": agent_name,
            "cycle_count": self.cycle_count,
            "last_cycle_at": (
                self.last_cycle_at
            ),
            "experience": experience_stats,
            "knowledge": knowledge_stats,
            "last_result": self.last_result,
        }

    # ------------------------------------------------------------------
    # Reset runtime state
    # ------------------------------------------------------------------

    def reset_runtime_state(self) -> None:
        """
        Reset cycle-manager runtime statistics.

        Persistent experiences and knowledge are deliberately preserved.
        """

        self.cycle_count = 0
        self.last_cycle_at = None
        self.last_result = None