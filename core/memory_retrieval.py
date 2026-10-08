from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .experience_memory import (
    Experience,
    ExperienceMemory,
)
from .knowledge_store import (
    Knowledge,
    KnowledgeStore,
)


class MemoryRetrievalError(Exception):
    """Raised when memory retrieval cannot complete."""


@dataclass
class MemoryMatch:
    """
    A retrieved memory item.

    score is normalised to the range 0.0 - 1.0.

    Higher scores indicate stronger relevance.
    """

    memory_type: str

    score: float

    content: str

    source_id: str

    agent_name: str

    metadata: Dict[str, Any] = field(
        default_factory=dict
    )


@dataclass
class RetrievalResult:
    """
    Combined result returned by the retrieval engine.
    """

    query: str

    matches: List[MemoryMatch] = field(
        default_factory=list
    )

    experiences: List[Experience] = field(
        default_factory=list
    )

    knowledge: List[Knowledge] = field(
        default_factory=list
    )

    context: str = ""


class MemoryRetrieval:
    """
    Memory retrieval abstraction.

    Version 1 uses local lexical retrieval.

    The interface is intentionally designed so that a future version
    can replace or extend the scoring mechanism with:

        - embeddings
        - vector databases
        - local embedding models
        - hybrid lexical + semantic retrieval
        - reranking models

    The rest of the agent architecture will not need to change.
    """

    def __init__(
        self,
        experience_memory: ExperienceMemory,
        knowledge_store: KnowledgeStore,
    ):
        if not isinstance(
            experience_memory,
            ExperienceMemory,
        ):
            raise MemoryRetrievalError(
                "experience_memory must be an ExperienceMemory instance."
            )

        if not isinstance(
            knowledge_store,
            KnowledgeStore,
        ):
            raise MemoryRetrievalError(
                "knowledge_store must be a KnowledgeStore instance."
            )

        self.experience_memory = (
            experience_memory
        )

        self.knowledge_store = (
            knowledge_store
        )

    def retrieve(
        self,
        query: str,
        agent_name: Optional[str] = None,
        limit: int = 10,
    ) -> RetrievalResult:
        """
        Retrieve relevant experiences and knowledge.

        Results are merged into one ranked list.
        """

        query = (
            query or ""
        ).strip()

        if not query:
            raise MemoryRetrievalError(
                "Memory retrieval query cannot be empty."
            )

        limit = self._normalise_limit(
            limit
        )

        experience_matches = (
            self._retrieve_experiences(
                query=query,
                agent_name=agent_name,
                limit=limit,
            )
        )

        knowledge_matches = (
            self._retrieve_knowledge(
                query=query,
                agent_name=agent_name,
                limit=limit,
            )
        )

        matches = (
            experience_matches
            + knowledge_matches
        )

        matches.sort(
            key=lambda item: item.score,
            reverse=True,
        )

        matches = matches[:limit]

        experiences = [
            item
            for item in self._experiences_from_matches(
                matches,
                query=query,
                agent_name=agent_name,
            )
        ]

        knowledge = [
            item
            for item in self._knowledge_from_matches(
                matches,
                query=query,
                agent_name=agent_name,
            )
        ]

        context = self.build_context(
            matches
        )

        return RetrievalResult(
            query=query,
            matches=matches,
            experiences=experiences,
            knowledge=knowledge,
            context=context,
        )

    def retrieve_experiences(
        self,
        query: str,
        agent_name: Optional[str] = None,
        limit: int = 10,
    ) -> List[Experience]:
        """
        Retrieve only experiences.
        """

        query = (
            query or ""
        ).strip()

        if not query:
            return []

        limit = self._normalise_limit(
            limit
        )

        candidates = (
            self.experience_memory.search(
                query=query,
                limit=limit,
                agent_name=agent_name,
            )
        )

        scored = [
            (
                experience,
                self._score_experience(
                    query,
                    experience,
                ),
            )
            for experience in candidates
        ]

        scored.sort(
            key=lambda item: item[1],
            reverse=True,
        )

        return [
            experience
            for experience, score in scored[:limit]
            if score > 0.0
        ]

    def retrieve_knowledge(
        self,
        query: str,
        agent_name: Optional[str] = None,
        limit: int = 10,
    ) -> List[Knowledge]:
        """
        Retrieve only knowledge.
        """

        query = (
            query or ""
        ).strip()

        if not query:
            return []

        limit = self._normalise_limit(
            limit
        )

        candidates = (
            self.knowledge_store.search(
                query=query,
                limit=limit,
                agent_name=agent_name,
            )
        )

        scored = [
            (
                knowledge,
                self._score_knowledge(
                    query,
                    knowledge,
                ),
            )
            for knowledge in candidates
        ]

        scored.sort(
            key=lambda item: item[1],
            reverse=True,
        )

        return [
            knowledge
            for knowledge, score in scored[:limit]
            if score > 0.0
        ]

    def build_context(
        self,
        matches: List[MemoryMatch],
        max_items: int = 10,
    ) -> str:
        """
        Convert retrieved memory into compact context for a model.

        This is intentionally plain text for compatibility with any
        local or remote model runtime.
        """

        if not matches:
            return (
                "No relevant previous memory was found."
            )

        lines: List[str] = [
            "RELEVANT PREVIOUS MEMORY:"
        ]

        for index, match in enumerate(
            matches[:max_items],
            start=1,
        ):
            lines.append(
                f"{index}. "
                f"[{match.memory_type}] "
                f"{match.content}"
            )

        return "\n".join(
            lines
        )

    def build_prompt_context(
        self,
        query: str,
        agent_name: Optional[str] = None,
        limit: int = 10,
    ) -> str:
        """
        Retrieve memory and immediately produce model-ready context.
        """

        result = self.retrieve(
            query=query,
            agent_name=agent_name,
            limit=limit,
        )

        return result.context

    def _retrieve_experiences(
        self,
        query: str,
        agent_name: Optional[str],
        limit: int,
    ) -> List[MemoryMatch]:
        candidates = (
            self.experience_memory.search(
                query=query,
                limit=limit,
                agent_name=agent_name,
            )
        )

        matches: List[MemoryMatch] = []

        for experience in candidates:
            score = self._score_experience(
                query,
                experience,
            )

            if score <= 0.0:
                continue

            content = (
                self._experience_content(
                    experience
                )
            )

            matches.append(
                MemoryMatch(
                    memory_type="experience",
                    score=score,
                    content=content,
                    source_id=(
                        experience.experience_id
                    ),
                    agent_name=(
                        experience.agent_name
                    ),
                    metadata={
                        "success": (
                            experience.success
                        ),
                        "goal": (
                            experience.goal
                        ),
                        "action": (
                            experience.action
                        ),
                    },
                )
            )

        return matches

    def _retrieve_knowledge(
        self,
        query: str,
        agent_name: Optional[str],
        limit: int,
    ) -> List[MemoryMatch]:
        candidates = (
            self.knowledge_store.search(
                query=query,
                limit=limit,
                agent_name=agent_name,
            )
        )

        matches: List[MemoryMatch] = []

        for knowledge in candidates:
            score = self._score_knowledge(
                query,
                knowledge,
            )

            if score <= 0.0:
                continue

            content = (
                self._knowledge_content(
                    knowledge
                )
            )

            matches.append(
                MemoryMatch(
                    memory_type="knowledge",
                    score=score,
                    content=content,
                    source_id=(
                        knowledge.knowledge_id
                    ),
                    agent_name=(
                        knowledge.agent_name
                    ),
                    metadata={
                        "topic": (
                            knowledge.topic
                        ),
                        "knowledge_type": (
                            knowledge.knowledge_type
                        ),
                        "confidence": (
                            knowledge.confidence
                        ),
                        "evidence_count": (
                            knowledge.evidence_count
                        ),
                    },
                )
            )

        return matches

    @staticmethod
    def _score_experience(
        query: str,
        experience: Experience,
    ) -> float:
        """
        Basic lexical relevance scoring.

        The scoring is deliberately deterministic and transparent.
        """

        query_tokens = (
            MemoryRetrieval._tokenise(
                query
            )
        )

        if not query_tokens:
            return 0.0

        fields = [
            (
                experience.goal,
                1.0,
            ),
            (
                experience.decision,
                0.8,
            ),
            (
                experience.action,
                0.8,
            ),
            (
                experience.result,
                0.7,
            ),
            (
                experience.lesson,
                1.0,
            ),
        ]

        score = 0.0
        maximum = 0.0

        for text, weight in fields:
            if not text:
                continue

            maximum += weight

            tokens = (
                MemoryRetrieval._tokenise(
                    text
                )
            )

            if not tokens:
                continue

            overlap = (
                query_tokens
                & tokens
            )

            if not overlap:
                continue

            ratio = (
                len(overlap)
                / len(query_tokens)
            )

            score += (
                ratio
                * weight
            )

        if maximum <= 0.0:
            return 0.0

        return MemoryRetrieval._clamp(
            score / maximum
        )

    @staticmethod
    def _score_knowledge(
        query: str,
        knowledge: Knowledge,
    ) -> float:
        """
        Score knowledge using lexical relevance plus confidence.

        High-confidence knowledge receives a modest ranking boost.
        """

        query_tokens = (
            MemoryRetrieval._tokenise(
                query
            )
        )

        if not query_tokens:
            return 0.0

        topic_tokens = (
            MemoryRetrieval._tokenise(
                knowledge.topic
            )
        )

        statement_tokens = (
            MemoryRetrieval._tokenise(
                knowledge.statement
            )
        )

        topic_overlap = (
            query_tokens
            & topic_tokens
        )

        statement_overlap = (
            query_tokens
            & statement_tokens
        )

        topic_score = (
            len(topic_overlap)
            / len(query_tokens)
            if query_tokens
            else 0.0
        )

        statement_score = (
            len(statement_overlap)
            / len(query_tokens)
            if query_tokens
            else 0.0
        )

        relevance = (
            topic_score * 0.6
            + statement_score * 0.4
        )

        confidence_bonus = (
            knowledge.confidence
            * 0.15
        )

        return MemoryRetrieval._clamp(
            relevance
            + confidence_bonus
        )

    @staticmethod
    def _experience_content(
        experience: Experience,
    ) -> str:
        parts: List[str] = []

        parts.append(
            f"Goal: {experience.goal}"
        )

        if experience.decision:
            parts.append(
                f"Decision: {experience.decision}"
            )

        if experience.action:
            parts.append(
                f"Action: {experience.action}"
            )

        if experience.result:
            parts.append(
                f"Result: {experience.result}"
            )

        if experience.success is not None:
            parts.append(
                "Outcome: "
                + (
                    "successful"
                    if experience.success
                    else "failed"
                )
            )

        if experience.lesson:
            parts.append(
                f"Lesson: {experience.lesson}"
            )

        return " | ".join(
            parts
        )

    @staticmethod
    def _knowledge_content(
        knowledge: Knowledge,
    ) -> str:
        return (
            f"Topic: {knowledge.topic} | "
            f"{knowledge.statement} | "
            f"Confidence: "
            f"{knowledge.confidence:.2f} | "
            f"Evidence: "
            f"{knowledge.evidence_count}"
        )

    @staticmethod
    def _tokenise(
        value: str,
    ) -> set[str]:
        """
        Small deterministic tokenizer.

        Stop-word removal is deliberately avoided in v1 so that the
        retrieval behaviour remains transparent and dependency-free.
        """

        if not value:
            return set()

        cleaned = (
            value.lower()
            .replace(",", " ")
            .replace(".", " ")
            .replace(":", " ")
            .replace(";", " ")
            .replace("!", " ")
            .replace("?", " ")
            .replace("(", " ")
            .replace(")", " ")
            .replace("/", " ")
            .replace("\\", " ")
            .replace("-", " ")
            .replace("_", " ")
        )

        return {
            token
            for token in cleaned.split()
            if token
        }

    def _experiences_from_matches(
        self,
        matches: List[MemoryMatch],
        query: str,
        agent_name: Optional[str],
    ) -> List[Experience]:
        ids = [
            match.source_id
            for match in matches
            if match.memory_type
            == "experience"
        ]

        output: List[Experience] = []

        for experience_id in ids:
            experience = (
                self.experience_memory.get(
                    experience_id
                )
            )

            if experience is not None:
                output.append(
                    experience
                )

        return output

    def _knowledge_from_matches(
        self,
        matches: List[MemoryMatch],
        query: str,
        agent_name: Optional[str],
    ) -> List[Knowledge]:
        ids = [
            match.source_id
            for match in matches
            if match.memory_type
            == "knowledge"
        ]

        output: List[Knowledge] = []

        for knowledge_id in ids:
            knowledge = (
                self.knowledge_store.get(
                    knowledge_id
                )
            )

            if knowledge is not None:
                output.append(
                    knowledge
                )

        return output

    @staticmethod
    def _normalise_limit(
        limit: int,
    ) -> int:
        try:
            value = int(limit)
        except (
            TypeError,
            ValueError,
        ) as exc:
            raise MemoryRetrievalError(
                "Retrieval limit must be an integer."
            ) from exc

        if value <= 0:
            raise MemoryRetrievalError(
                "Retrieval limit must be greater than zero."
            )

        return min(
            value,
            100,
        )

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