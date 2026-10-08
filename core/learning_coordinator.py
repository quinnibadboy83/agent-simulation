from __future__ import annotations

from typing import Any, Dict, List, Optional

from .experience_memory import (
    Experience,
    ExperienceMemory,
)

from .learning_engine import (
    LearningEngine,
    Lesson,
)

from .knowledge_store import (
    KnowledgeStore,
    Knowledge,
)


class LearningCoordinatorError(Exception):
    """Raised when learning coordination fails."""


class LearningCoordinator:
    """
    Coordinates the transition from:

        experience
            ↓
        evaluation
            ↓
        lesson
            ↓
        persistent knowledge

    ExperienceMemory records what happened.

    LearningEngine evaluates what happened.

    KnowledgeStore preserves reusable knowledge.

    The coordinator connects those stages without coupling them to
    the LLM provider or model runtime.
    """

    def __init__(
        self,
        experience_memory: ExperienceMemory,
        learning_engine: Optional[
            LearningEngine
        ] = None,
        knowledge_store: Optional[
            KnowledgeStore
        ] = None,
    ):
        if not isinstance(
            experience_memory,
            ExperienceMemory,
        ):
            raise LearningCoordinatorError(
                "experience_memory must be an "
                "ExperienceMemory instance."
            )

        self.experience_memory = (
            experience_memory
        )

        self.learning_engine = (
            learning_engine
            if learning_engine is not None
            else LearningEngine(
                memory=experience_memory
            )
        )

        self.knowledge_store = (
            knowledge_store
            if knowledge_store is not None
            else KnowledgeStore()
        )

    # ------------------------------------------------------------------
    # Single experience
    # ------------------------------------------------------------------

    def process_experience(
        self,
        experience: Experience,
    ) -> Optional[Knowledge]:
        """
        Evaluate one experience and convert the resulting lesson into
        persistent knowledge.

        Returns None when the experience does not contain enough
        information to produce a lesson.
        """

        if not isinstance(
            experience,
            Experience,
        ):
            raise LearningCoordinatorError(
                "process_experience() requires an Experience object."
            )

        lesson = (
            self.learning_engine.evaluate_experience(
                experience
            )
        )

        if lesson is None:
            return None

        return self._store_lesson(
            lesson
        )

    # ------------------------------------------------------------------
    # Experience ID
    # ------------------------------------------------------------------

    def process_experience_id(
        self,
        experience_id: str,
    ) -> Optional[Knowledge]:
        """
        Retrieve an experience by ID and process it.
        """

        if not experience_id:
            return None

        experience = (
            self.experience_memory.get(
                experience_id
            )
        )

        if experience is None:
            return None

        return self.process_experience(
            experience
        )

    # ------------------------------------------------------------------
    # Recent learning
    # ------------------------------------------------------------------

    def learn_recent(
        self,
        limit: int = 20,
        agent_name: Optional[str] = None,
    ) -> List[Knowledge]:
        """
        Evaluate recent experiences and persist the resulting lessons.
        """

        lessons = (
            self.learning_engine.learn_from_recent(
                limit=limit,
                agent_name=agent_name,
            )
        )

        knowledge_items: List[Knowledge] = []

        for lesson in lessons:
            knowledge = self._store_lesson(
                lesson
            )

            if knowledge is not None:
                knowledge_items.append(
                    knowledge
                )

        return knowledge_items

    # ------------------------------------------------------------------
    # Agent learning cycle
    # ------------------------------------------------------------------

    def learn_agent(
        self,
        agent_name: str,
        limit: int = 50,
    ) -> Dict[str, Any]:
        """
        Run a complete learning cycle for one agent.
        """

        if not agent_name:
            raise LearningCoordinatorError(
                "agent_name cannot be empty."
            )

        lessons = (
            self.learning_engine.learn_from_recent(
                limit=limit,
                agent_name=agent_name,
            )
        )

        stored: List[Knowledge] = []

        for lesson in lessons:
            knowledge = self._store_lesson(
                lesson
            )

            if knowledge is not None:
                stored.append(
                    knowledge
                )

        analysis = (
            self.learning_engine.analyse_agent(
                agent_name=agent_name,
                limit=limit,
            )
        )

        return {
            "agent_name": agent_name,
            "experiences_evaluated": len(
                lessons
            ),
            "knowledge_created_or_updated": len(
                stored
            ),
            "analysis": analysis,
        }

    # ------------------------------------------------------------------
    # Knowledge storage
    # ------------------------------------------------------------------

    def _store_lesson(
        self,
        lesson: Lesson,
    ) -> Optional[Knowledge]:
        """
        Convert a Lesson into KnowledgeStore data.

        Existing matching knowledge is reinforced with the correct
        positive/negative evidence.

        The original experience ID is preserved as evidence.
        """

        statement = (
            lesson.lesson or ""
        ).strip()

        if not statement:
            return None

        topic = self._derive_topic(
            lesson
        )

        source_experience_id = None

        if lesson.source_experience_ids:
            source_experience_id = (
                lesson.source_experience_ids[0]
            )

        knowledge = (
            self.knowledge_store.find_or_create(
                agent_name=lesson.agent_name,
                topic=topic,
                statement=statement,
                knowledge_type="lesson",
                confidence=lesson.confidence,
                positive=lesson.positive,
                experience_id=source_experience_id,
                context=lesson.context,
            )
        )

        return knowledge

    # ------------------------------------------------------------------
    # Topic generation
    # ------------------------------------------------------------------

    @staticmethod
    def _derive_topic(
        lesson: Lesson,
    ) -> str:
        """
        Derive a stable topic from lesson context.

        The topic is deliberately conservative.
        """

        context = (
            lesson.context
            if isinstance(
                lesson.context,
                dict,
            )
            else {}
        )

        goal = str(
            context.get(
                "goal",
                "",
            )
            or ""
        ).strip()

        action = str(
            context.get(
                "action",
                "",
            )
            or ""
        ).strip()

        if goal:
            words = goal.split()

            if len(words) > 8:
                goal = " ".join(
                    words[:8]
                )

            return goal

        if action:
            return action

        return "general"

    # ------------------------------------------------------------------
    # Diagnostics
    # ------------------------------------------------------------------

    def status(
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
            "experience": experience_stats,
            "knowledge": knowledge_stats,
            "learning_engine": True,
            "automatic_consolidation": True,
        }