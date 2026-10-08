from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .experience_memory import ExperienceMemory
from .knowledge_store import KnowledgeStore
from .memory_retrieval import (
    MemoryMatch,
    MemoryRetrieval,
    RetrievalResult,
)


class CognitiveContextError(Exception):
    """Raised when cognitive context cannot be constructed."""


@dataclass
class CognitiveContext:
    """
    Structured context available to an agent during reasoning.

    This object deliberately separates:

        current task
        agent identity
        retrieved memory
        learned knowledge
        guidance

    from the raw model prompt.

    This gives the application control over what information reaches
    the model.
    """

    agent_name: str

    task: str

    memory: RetrievalResult

    guidance: List[str] = field(
        default_factory=list
    )

    system_context: str = ""

    metadata: Dict[str, Any] = field(
        default_factory=dict
    )


class CognitiveContextBuilder:
    """
    Builds model-ready cognitive context.

    This is the first explicit boundary between:

        persistent memory

    and:

        model reasoning.

    The builder does not execute tools, approve actions, or make
    decisions on behalf of an agent.
    """

    def __init__(
        self,
        experience_memory: ExperienceMemory,
        knowledge_store: KnowledgeStore,
        retrieval: Optional[
            MemoryRetrieval
        ] = None,
    ):
        if not isinstance(
            experience_memory,
            ExperienceMemory,
        ):
            raise CognitiveContextError(
                "experience_memory must be an ExperienceMemory instance."
            )

        if not isinstance(
            knowledge_store,
            KnowledgeStore,
        ):
            raise CognitiveContextError(
                "knowledge_store must be a KnowledgeStore instance."
            )

        self.experience_memory = (
            experience_memory
        )

        self.knowledge_store = (
            knowledge_store
        )

        self.retrieval = (
            retrieval
            if retrieval is not None
            else MemoryRetrieval(
                experience_memory=(
                    experience_memory
                ),
                knowledge_store=(
                    knowledge_store
                ),
            )
        )

    def build(
        self,
        agent_name: str,
        task: str,
        limit: int = 10,
        include_guidance: bool = True,
    ) -> CognitiveContext:
        """
        Build cognitive context for an agent and task.
        """

        agent_name = (
            agent_name or ""
        ).strip()

        task = (
            task or ""
        ).strip()

        if not agent_name:
            raise CognitiveContextError(
                "agent_name cannot be empty."
            )

        if not task:
            raise CognitiveContextError(
                "task cannot be empty."
            )

        memory = self.retrieval.retrieve(
            query=task,
            agent_name=agent_name,
            limit=limit,
        )

        guidance: List[str] = []

        if include_guidance:
            guidance = self._build_guidance(
                memory
            )

        system_context = (
            self._build_system_context(
                agent_name=agent_name,
                task=task,
                memory=memory,
                guidance=guidance,
            )
        )

        metadata = {
            "agent_name": agent_name,
            "task": task,
            "retrieved_memory_count": len(
                memory.matches
            ),
            "retrieved_experience_count": len(
                memory.experiences
            ),
            "retrieved_knowledge_count": len(
                memory.knowledge
            ),
        }

        return CognitiveContext(
            agent_name=agent_name,
            task=task,
            memory=memory,
            guidance=guidance,
            system_context=system_context,
            metadata=metadata,
        )

    def build_for_planning(
        self,
        agent_name: str,
        goal: str,
        limit: int = 10,
    ) -> CognitiveContext:
        """
        Build context specifically for planning.

        The method is kept separate because later planning can use
        different retrieval policies from ordinary conversation.
        """

        return self.build(
            agent_name=agent_name,
            task=goal,
            limit=limit,
            include_guidance=True,
        )

    def build_for_decision(
        self,
        agent_name: str,
        decision: str,
        limit: int = 10,
    ) -> CognitiveContext:
        """
        Build context for a specific decision.
        """

        return self.build(
            agent_name=agent_name,
            task=decision,
            limit=limit,
            include_guidance=True,
        )

    def build_for_learning(
        self,
        agent_name: str,
        learning_question: str,
        limit: int = 20,
    ) -> CognitiveContext:
        """
        Build context for a learning/evaluation cycle.
        """

        return self.build(
            agent_name=agent_name,
            task=learning_question,
            limit=limit,
            include_guidance=True,
        )

    def format_memory(
        self,
        memory: RetrievalResult,
        max_items: int = 10,
    ) -> str:
        """
        Format retrieved memory for inclusion in a model prompt.
        """

        if not memory.matches:
            return (
                "No relevant previous experience or "
                "knowledge was retrieved."
            )

        lines: List[str] = []

        for index, match in enumerate(
            memory.matches[:max_items],
            start=1,
        ):
            lines.append(
                self._format_match(
                    index,
                    match,
                )
            )

        return "\n".join(
            lines
        )

    def format_guidance(
        self,
        guidance: List[str],
    ) -> str:
        """
        Format learned guidance.
        """

        if not guidance:
            return (
                "No additional learned guidance "
                "is currently available."
            )

        lines = [
            "LEARNED GUIDANCE:"
        ]

        for item in guidance:
            lines.append(
                f"- {item}"
            )

        return "\n".join(
            lines
        )

    def _build_guidance(
        self,
        memory: RetrievalResult,
    ) -> List[str]:
        """
        Extract conservative guidance from retrieved memory.

        This does not invent new conclusions.

        It only exposes information already present in retrieved
        knowledge and successful/failed experiences.
        """

        guidance: List[str] = []

        successful_actions: List[str] = []
        failed_actions: List[str] = []

        successful_decisions: List[str] = []
        failed_decisions: List[str] = []

        for experience in memory.experiences:

            if experience.success is True:

                if experience.action:
                    self._append_unique(
                        successful_actions,
                        experience.action,
                    )

                if experience.decision:
                    self._append_unique(
                        successful_decisions,
                        experience.decision,
                    )

            elif experience.success is False:

                if experience.action:
                    self._append_unique(
                        failed_actions,
                        experience.action,
                    )

                if experience.decision:
                    self._append_unique(
                        failed_decisions,
                        experience.decision,
                    )

        for knowledge in memory.knowledge:

            statement = (
                knowledge.statement.strip()
            )

            if not statement:
                continue

            prefix = (
                "Learned knowledge "
                f"(confidence "
                f"{knowledge.confidence:.2f}): "
            )

            self._append_unique(
                guidance,
                prefix + statement,
            )

        if successful_actions:
            guidance.append(
                "Previously successful actions: "
                + "; ".join(
                    successful_actions[:5]
                )
            )

        if failed_actions:
            guidance.append(
                "Previously unsuccessful actions: "
                + "; ".join(
                    failed_actions[:5]
                )
            )

        if successful_decisions:
            guidance.append(
                "Previously successful decisions: "
                + "; ".join(
                    successful_decisions[:5]
                )
            )

        if failed_decisions:
            guidance.append(
                "Previously unsuccessful decisions: "
                + "; ".join(
                    failed_decisions[:5]
                )
            )

        return guidance

    def _build_system_context(
        self,
        agent_name: str,
        task: str,
        memory: RetrievalResult,
        guidance: List[str],
    ) -> str:
        """
        Construct the model-facing cognitive context.

        This is intentionally explicit so future versions can add
        additional cognitive layers without hiding them inside the
        LLM client.
        """

        memory_text = self.format_memory(
            memory
        )

        guidance_text = (
            self.format_guidance(
                guidance
            )
        )

        return (
            "COGNITIVE CONTEXT\n"
            "\n"
            f"AGENT: {agent_name}\n"
            f"CURRENT TASK: {task}\n"
            "\n"
            "RELEVANT MEMORY:\n"
            f"{memory_text}\n"
            "\n"
            f"{guidance_text}\n"
            "\n"
            "MEMORY RULES:\n"
            "- Retrieved memory is evidence, not authority.\n"
            "- Previous success does not guarantee future success.\n"
            "- Previous failure does not prove an approach can never work.\n"
            "- Conflicting evidence must remain visible.\n"
            "- The agent must reason about current circumstances.\n"
            "- Memory does not grant permission to execute actions.\n"
        )

    @staticmethod
    def _format_match(
        index: int,
        match: MemoryMatch,
    ) -> str:
        confidence = (
            match.metadata.get(
                "confidence"
            )
        )

        confidence_text = ""

        if isinstance(
            confidence,
            (int, float),
        ):
            confidence_text = (
                f" | confidence={float(confidence):.2f}"
            )

        return (
            f"{index}. "
            f"[{match.memory_type}] "
            f"score={match.score:.2f}"
            f"{confidence_text} | "
            f"{match.content}"
        )

    @staticmethod
    def _append_unique(
        values: List[str],
        value: str,
    ) -> None:
        cleaned = (
            value or ""
        ).strip()

        if not cleaned:
            return

        if cleaned not in values:
            values.append(
                cleaned
            )