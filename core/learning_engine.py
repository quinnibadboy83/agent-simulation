from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .experience_memory import (
    Experience,
    ExperienceMemory,
    ExperienceMemoryError,
)


class LearningEngineError(Exception):
    """Raised when the learning engine cannot complete an operation."""


@dataclass
class Lesson:
    """
    A reusable lesson extracted from one or more experiences.

    Lessons are application-level knowledge.

    They do not modify the underlying neural model.
    """

    agent_name: str

    lesson: str

    evidence_count: int = 1

    confidence: float = 0.5

    positive: bool = True

    source_experience_ids: List[str] = field(
        default_factory=list
    )

    context: Dict[str, Any] = field(
        default_factory=dict
    )

    created_at: str = field(
        default_factory=lambda: datetime.now(
            timezone.utc
        ).isoformat()
    )


class LearningEngine:
    """
    First-generation learning and evaluation system.

    Responsibilities:

        1. Evaluate previous experiences.
        2. Identify useful lessons.
        3. Compare successful and failed approaches.
        4. Produce reusable guidance.
        5. Store learned lessons in memory.

    This is intentionally deterministic in the first version.

    A future version can use the ModelRuntime to perform deeper
    semantic evaluation without changing this public interface.
    """

    def __init__(
        self,
        memory: ExperienceMemory,
    ):
        if not isinstance(
            memory,
            ExperienceMemory,
        ):
            raise LearningEngineError(
                "LearningEngine requires an ExperienceMemory instance."
            )

        self.memory = memory

    def evaluate_experience(
        self,
        experience: Experience,
    ) -> Optional[Lesson]:
        """
        Evaluate one experience and create a lesson when enough
        information exists.

        The evaluator currently uses explicit success/failure and
        supplied lesson text.

        It deliberately does not invent facts about an outcome.
        """

        if not isinstance(
            experience,
            Experience,
        ):
            raise LearningEngineError(
                "evaluate_experience() requires an Experience object."
            )

        if experience.success is None:
            return None

        lesson_text = (
            experience.lesson
            or self._derive_basic_lesson(
                experience
            )
        )

        if not lesson_text:
            return None

        confidence = (
            experience.confidence
            if experience.confidence is not None
            else (
                0.75
                if experience.success
                else 0.80
            )
        )

        return Lesson(
            agent_name=experience.agent_name,
            lesson=lesson_text,
            evidence_count=1,
            confidence=self._clamp(
                confidence
            ),
            positive=experience.success,
            source_experience_ids=[
                experience.experience_id
            ],
            context={
                "goal": experience.goal,
                "decision": experience.decision,
                "action": experience.action,
                "result": experience.result,
            },
        )

    def learn_from_recent(
        self,
        limit: int = 20,
        agent_name: Optional[str] = None,
    ) -> List[Lesson]:
        """
        Evaluate recent experiences.

        Lessons are not automatically duplicated into memory as new
        experiences. Instead, they are returned to the caller.

        Module 4 will introduce a dedicated knowledge/lesson store.
        """

        experiences = self.memory.recent(
            limit=limit,
            agent_name=agent_name,
        )

        lessons: List[Lesson] = []

        for experience in experiences:
            lesson = self.evaluate_experience(
                experience
            )

            if lesson is not None:
                lessons.append(
                    lesson
                )

        return lessons

    def analyse_agent(
        self,
        agent_name: str,
        limit: int = 100,
    ) -> Dict[str, Any]:
        """
        Analyse an agent's recent performance.

        The result is suitable for feeding into future planning.
        """

        experiences = self.memory.recent(
            limit=limit,
            agent_name=agent_name,
        )

        if not experiences:
            return {
                "agent_name": agent_name,
                "experience_count": 0,
                "evaluated_count": 0,
                "successful_count": 0,
                "failed_count": 0,
                "success_rate": None,
                "lessons": [],
            }

        successful = [
            experience
            for experience in experiences
            if experience.success is True
        ]

        failed = [
            experience
            for experience in experiences
            if experience.success is False
        ]

        evaluated_count = (
            len(successful)
            + len(failed)
        )

        success_rate = (
            len(successful)
            / evaluated_count
            if evaluated_count
            else None
        )

        lessons = self.learn_from_recent(
            limit=limit,
            agent_name=agent_name,
        )

        return {
            "agent_name": agent_name,
            "experience_count": len(
                experiences
            ),
            "evaluated_count": evaluated_count,
            "successful_count": len(
                successful
            ),
            "failed_count": len(
                failed
            ),
            "success_rate": success_rate,
            "lessons": [
                self.lesson_to_dict(
                    lesson
                )
                for lesson in lessons
            ],
        }

    def compare_strategies(
        self,
        agent_name: str,
        query: str,
        limit: int = 50,
    ) -> Dict[str, Any]:
        """
        Compare previous experiences related to a query.

        This provides the planner with evidence about which approaches
        have worked or failed previously.
        """

        matches = self.memory.search(
            query=query,
            limit=limit,
            agent_name=agent_name,
        )

        successful = [
            experience
            for experience in matches
            if experience.success is True
        ]

        failed = [
            experience
            for experience in matches
            if experience.success is False
        ]

        successful_actions = self._unique_values(
            [
                experience.action
                for experience in successful
            ]
        )

        failed_actions = self._unique_values(
            [
                experience.action
                for experience in failed
            ]
        )

        successful_decisions = self._unique_values(
            [
                experience.decision
                for experience in successful
            ]
        )

        failed_decisions = self._unique_values(
            [
                experience.decision
                for experience in failed
            ]
        )

        return {
            "agent_name": agent_name,
            "query": query,
            "matches": len(matches),
            "successful": len(successful),
            "failed": len(failed),
            "successful_actions": successful_actions,
            "failed_actions": failed_actions,
            "successful_decisions": successful_decisions,
            "failed_decisions": failed_decisions,
            "success_rate": (
                len(successful)
                / (
                    len(successful)
                    + len(failed)
                )
                if (
                    len(successful)
                    + len(failed)
                )
                else None
            ),
        }

    def generate_guidance(
        self,
        agent_name: str,
        query: str,
        limit: int = 50,
    ) -> Dict[str, Any]:
        """
        Produce concise guidance for a future planning cycle.

        This is the bridge between memory and decision-making.
        """

        comparison = self.compare_strategies(
            agent_name=agent_name,
            query=query,
            limit=limit,
        )

        guidance: List[str] = []

        successful_actions = comparison[
            "successful_actions"
        ]

        failed_actions = comparison[
            "failed_actions"
        ]

        successful_decisions = comparison[
            "successful_decisions"
        ]

        failed_decisions = comparison[
            "failed_decisions"
        ]

        if successful_actions:
            guidance.append(
                "Previously successful actions: "
                + "; ".join(
                    successful_actions[:10]
                )
            )

        if failed_actions:
            guidance.append(
                "Previously unsuccessful actions: "
                + "; ".join(
                    failed_actions[:10]
                )
            )

        if successful_decisions:
            guidance.append(
                "Previously successful decisions: "
                + "; ".join(
                    successful_decisions[:10]
                )
            )

        if failed_decisions:
            guidance.append(
                "Previously unsuccessful decisions: "
                + "; ".join(
                    failed_decisions[:10]
                )
            )

        if not guidance:
            guidance.append(
                "No previous experience provides "
                "reliable guidance for this query."
            )

        return {
            **comparison,
            "guidance": guidance,
        }

    def reinforce(
        self,
        experience: Experience,
    ) -> Optional[Experience]:
        """
        Record an explicit learning reinforcement.

        The original experience is preserved.

        A second experience records that the result has been evaluated
        and converted into reusable knowledge.

        This creates an auditable learning trail.
        """

        lesson = self.evaluate_experience(
            experience
        )

        if lesson is None:
            return None

        reinforcement = self.memory.record(
            agent_name=experience.agent_name,
            goal=(
                "Learn from previous experience: "
                + experience.goal
            ),
            decision=(
                "Extract reusable lesson"
            ),
            action=(
                "Reinforce learned experience"
            ),
            result=lesson.lesson,
            success=True,
            lesson=lesson.lesson,
            confidence=lesson.confidence,
            context={
                "source_experience_id": (
                    experience.experience_id
                ),
                "positive": lesson.positive,
            },
            metadata={
                "learning_event": True,
                "learning_version": "1",
            },
        )

        return reinforcement

    @staticmethod
    def lesson_to_dict(
        lesson: Lesson,
    ) -> Dict[str, Any]:
        return {
            "agent_name": lesson.agent_name,
            "lesson": lesson.lesson,
            "evidence_count": (
                lesson.evidence_count
            ),
            "confidence": lesson.confidence,
            "positive": lesson.positive,
            "source_experience_ids": list(
                lesson.source_experience_ids
            ),
            "context": dict(
                lesson.context
            ),
            "created_at": lesson.created_at,
        }

    @staticmethod
    def _derive_basic_lesson(
        experience: Experience,
    ) -> Optional[str]:
        """
        Derive a conservative lesson from explicit outcome data.

        No unsupported claims are generated.
        """

        action = (
            experience.action
            or "the recorded action"
        )

        if experience.success:
            return (
                f"The recorded approach succeeded: "
                f"{action}."
            )

        return (
            f"The recorded approach failed: "
            f"{action}. Avoid repeating it "
            f"without modification."
        )

    @staticmethod
    def _unique_values(
        values: List[Optional[str]],
    ) -> List[str]:
        output: List[str] = []

        seen = set()

        for value in values:
            if not value:
                continue

            cleaned = value.strip()

            if not cleaned:
                continue

            if cleaned in seen:
                continue

            seen.add(cleaned)
            output.append(cleaned)

        return output

    @staticmethod
    def _clamp(
        value: float,
    ) -> float:
        return max(
            0.0,
            min(
                1.0,
                float(value),
            ),
        )