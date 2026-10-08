from __future__ import annotations

import json
import sqlite3
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


class KnowledgeStoreError(Exception):
    """Raised when the knowledge store cannot complete an operation."""


@dataclass
class Knowledge:
    """
    Persistent piece of learned knowledge.

    Knowledge is more durable than an individual experience.

    An experience says:

        "This happened."

    Knowledge says:

        "Based on repeated evidence, this appears to be useful."
    """

    agent_name: str

    topic: str

    statement: str

    knowledge_type: str = "lesson"

    confidence: float = 0.5

    evidence_count: int = 1

    positive_evidence: int = 0

    negative_evidence: int = 0

    source_experience_ids: List[str] = field(
        default_factory=list
    )

    context: Dict[str, Any] = field(
        default_factory=dict
    )

    knowledge_id: str = field(
        default_factory=lambda: str(
            uuid.uuid4()
        )
    )

    created_at: str = field(
        default_factory=lambda: datetime.now(
            timezone.utc
        ).isoformat()
    )

    updated_at: str = field(
        default_factory=lambda: datetime.now(
            timezone.utc
        ).isoformat()
    )


class KnowledgeStore:
    """
    Persistent SQLite-backed knowledge store.

    This module sits above ExperienceMemory.

    ExperienceMemory records what happened.

    KnowledgeStore records what the system currently believes it
    has learned from repeated evidence.

    No external authority is granted to stored knowledge.

    Knowledge is advisory information for future reasoning.
    """

    VALID_TYPES = {
        "lesson",
        "strategy",
        "fact",
        "pattern",
        "warning",
        "preference",
        "hypothesis",
    }

    def __init__(
        self,
        database_path: Optional[str] = None,
    ):
        configured_path = (
            database_path
            or "data/agent_memory.db"
        )

        self.database_path = Path(
            configured_path
        )

        self.database_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        self._lock = threading.RLock()

        self._connection = sqlite3.connect(
            str(self.database_path),
            check_same_thread=False,
        )

        self._connection.row_factory = (
            sqlite3.Row
        )

        self._initialise()

    def _initialise(self) -> None:
        """
        Create the knowledge schema.
        """

        with self._lock:
            cursor = self._connection.cursor()

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS knowledge (
                    knowledge_id TEXT PRIMARY KEY,

                    agent_name TEXT NOT NULL,

                    topic TEXT NOT NULL,

                    statement TEXT NOT NULL,

                    knowledge_type TEXT NOT NULL,

                    confidence REAL NOT NULL,

                    evidence_count INTEGER NOT NULL,

                    positive_evidence INTEGER NOT NULL,

                    negative_evidence INTEGER NOT NULL,

                    source_experience_ids_json TEXT NOT NULL,

                    context_json TEXT NOT NULL,

                    created_at TEXT NOT NULL,

                    updated_at TEXT NOT NULL
                )
                """
            )

            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS
                idx_knowledge_agent
                ON knowledge(agent_name)
                """
            )

            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS
                idx_knowledge_topic
                ON knowledge(topic)
                """
            )

            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS
                idx_knowledge_type
                ON knowledge(knowledge_type)
                """
            )

            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS
                idx_knowledge_confidence
                ON knowledge(confidence)
                """
            )

            self._connection.commit()

    def close(self) -> None:
        """
        Close the database connection.
        """

        with self._lock:
            self._connection.close()

    def save(
        self,
        knowledge: Knowledge,
    ) -> str:
        """
        Save or replace a knowledge record.
        """

        if not isinstance(
            knowledge,
            Knowledge,
        ):
            raise KnowledgeStoreError(
                "save() requires a Knowledge object."
            )

        self._validate(
            knowledge
        )

        source_ids_json = json.dumps(
            knowledge.source_experience_ids,
            ensure_ascii=False,
        )

        context_json = json.dumps(
            knowledge.context,
            ensure_ascii=False,
            default=str,
        )

        with self._lock:
            try:
                self._connection.execute(
                    """
                    INSERT OR REPLACE INTO
                    knowledge (
                        knowledge_id,
                        agent_name,
                        topic,
                        statement,
                        knowledge_type,
                        confidence,
                        evidence_count,
                        positive_evidence,
                        negative_evidence,
                        source_experience_ids_json,
                        context_json,
                        created_at,
                        updated_at
                    )
                    VALUES (
                        ?, ?, ?, ?, ?, ?, ?, ?,
                        ?, ?, ?, ?, ?
                    )
                    """,
                    (
                        knowledge.knowledge_id,
                        knowledge.agent_name,
                        knowledge.topic,
                        knowledge.statement,
                        knowledge.knowledge_type,
                        knowledge.confidence,
                        knowledge.evidence_count,
                        knowledge.positive_evidence,
                        knowledge.negative_evidence,
                        source_ids_json,
                        context_json,
                        knowledge.created_at,
                        knowledge.updated_at,
                    ),
                )

                self._connection.commit()

            except sqlite3.Error as exc:
                self._connection.rollback()

                raise KnowledgeStoreError(
                    "Failed to save knowledge: "
                    f"{exc}"
                ) from exc

        return knowledge.knowledge_id

    def add(
        self,
        agent_name: str,
        topic: str,
        statement: str,
        knowledge_type: str = "lesson",
        confidence: float = 0.5,
        evidence_count: int = 1,
        positive_evidence: int = 0,
        negative_evidence: int = 0,
        source_experience_ids: Optional[
            List[str]
        ] = None,
        context: Optional[
            Dict[str, Any]
        ] = None,
    ) -> Knowledge:
        """
        Create and persist knowledge.
        """

        knowledge = Knowledge(
            agent_name=agent_name,
            topic=topic,
            statement=statement,
            knowledge_type=knowledge_type,
            confidence=confidence,
            evidence_count=evidence_count,
            positive_evidence=positive_evidence,
            negative_evidence=negative_evidence,
            source_experience_ids=(
                list(source_experience_ids)
                if source_experience_ids
                else []
            ),
            context=(
                dict(context)
                if context
                else {}
            ),
        )

        self.save(
            knowledge
        )

        return knowledge

    def get(
        self,
        knowledge_id: str,
    ) -> Optional[Knowledge]:
        """
        Retrieve knowledge by ID.
        """

        if not knowledge_id:
            return None

        with self._lock:
            row = self._connection.execute(
                """
                SELECT *
                FROM knowledge
                WHERE knowledge_id = ?
                """,
                (
                    knowledge_id,
                ),
            ).fetchone()

        if row is None:
            return None

        return self._row_to_knowledge(
            row
        )

    def search(
        self,
        query: str,
        limit: int = 20,
        agent_name: Optional[str] = None,
        knowledge_type: Optional[str] = None,
    ) -> List[Knowledge]:
        """
        Search knowledge using SQLite text matching.
        """

        query = (
            query or ""
        ).strip()

        if not query:
            return []

        limit = self._normalise_limit(
            limit
        )

        pattern = (
            "%"
            + query
            + "%"
        )

        clauses = [
            """
            (
                topic LIKE ?
                OR statement LIKE ?
            )
            """
        ]

        parameters: List[Any] = [
            pattern,
            pattern,
        ]

        if agent_name:
            clauses.append(
                "agent_name = ?"
            )
            parameters.append(
                agent_name
            )

        if knowledge_type:
            clauses.append(
                "knowledge_type = ?"
            )
            parameters.append(
                knowledge_type
            )

        parameters.append(
            limit
        )

        where_clause = " AND ".join(
            clauses
        )

        sql = f"""
            SELECT *
            FROM knowledge
            WHERE {where_clause}
            ORDER BY
                confidence DESC,
                evidence_count DESC,
                updated_at DESC
            LIMIT ?
        """

        with self._lock:
            rows = self._connection.execute(
                sql,
                tuple(parameters),
            ).fetchall()

        return [
            self._row_to_knowledge(row)
            for row in rows
        ]

    def recent(
        self,
        limit: int = 20,
        agent_name: Optional[str] = None,
    ) -> List[Knowledge]:
        """
        Return recently updated knowledge.
        """

        limit = self._normalise_limit(
            limit
        )

        with self._lock:
            if agent_name:
                rows = self._connection.execute(
                    """
                    SELECT *
                    FROM knowledge
                    WHERE agent_name = ?
                    ORDER BY updated_at DESC
                    LIMIT ?
                    """,
                    (
                        agent_name,
                        limit,
                    ),
                ).fetchall()

            else:
                rows = self._connection.execute(
                    """
                    SELECT *
                    FROM knowledge
                    ORDER BY updated_at DESC
                    LIMIT ?
                    """,
                    (
                        limit,
                    ),
                ).fetchall()

        return [
            self._row_to_knowledge(row)
            for row in rows
        ]

    def reinforce(
        self,
        knowledge_id: str,
        positive: bool,
        experience_id: Optional[str] = None,
        confidence_delta: Optional[float] = None,
    ) -> Optional[Knowledge]:
        """
        Reinforce or weaken an existing knowledge item.

        Positive evidence increases confidence.

        Negative evidence decreases confidence.

        This is the beginning of evidence-based adaptation.
        """

        knowledge = self.get(
            knowledge_id
        )

        if knowledge is None:
            return None

        knowledge.evidence_count += 1

        if positive:
            knowledge.positive_evidence += 1
        else:
            knowledge.negative_evidence += 1

        if experience_id:
            if (
                experience_id
                not in knowledge.source_experience_ids
            ):
                knowledge.source_experience_ids.append(
                    experience_id
                )

        if confidence_delta is None:
            confidence_delta = (
                0.05
                if positive
                else -0.05
            )

        knowledge.confidence = self._clamp(
            knowledge.confidence
            + confidence_delta
        )

        knowledge.updated_at = (
            datetime.now(
                timezone.utc
            ).isoformat()
        )

        self.save(
            knowledge
        )

        return knowledge

    def find_or_create(
        self,
        agent_name: str,
        topic: str,
        statement: str,
        knowledge_type: str = "lesson",
        confidence: float = 0.5,
        positive: bool = True,
        experience_id: Optional[str] = None,
        context: Optional[
            Dict[str, Any]
        ] = None,
    ) -> Knowledge:
        """
        Find an existing matching knowledge item or create one.

        Matching is intentionally conservative.

        Exact topic + statement + agent must match.
        """

        with self._lock:
            row = self._connection.execute(
                """
                SELECT *
                FROM knowledge
                WHERE agent_name = ?
                  AND topic = ?
                  AND statement = ?
                  AND knowledge_type = ?
                LIMIT 1
                """,
                (
                    agent_name,
                    topic,
                    statement,
                    knowledge_type,
                ),
            ).fetchone()

        if row is not None:
            knowledge = (
                self._row_to_knowledge(
                    row
                )
            )

            self._reinforce_in_memory(
                knowledge,
                positive=positive,
                experience_id=experience_id,
                confidence_delta=None,
            )

            self.save(
                knowledge
            )

            return knowledge

        initial_positive = (
            1
            if positive
            else 0
        )

        initial_negative = (
            0
            if positive
            else 1
        )

        return self.add(
            agent_name=agent_name,
            topic=topic,
            statement=statement,
            knowledge_type=knowledge_type,
            confidence=confidence,
            evidence_count=1,
            positive_evidence=(
                initial_positive
            ),
            negative_evidence=(
                initial_negative
            ),
            source_experience_ids=(
                [experience_id]
                if experience_id
                else []
            ),
            context=context,
        )

    def best(
        self,
        agent_name: Optional[str] = None,
        topic: Optional[str] = None,
        limit: int = 20,
    ) -> List[Knowledge]:
        """
        Return the strongest available knowledge.
        """

        limit = self._normalise_limit(
            limit
        )

        clauses: List[str] = []
        parameters: List[Any] = []

        if agent_name:
            clauses.append(
                "agent_name = ?"
            )
            parameters.append(
                agent_name
            )

        if topic:
            clauses.append(
                "topic = ?"
            )
            parameters.append(
                topic
            )

        where_clause = (
            "WHERE "
            + " AND ".join(
                clauses
            )
            if clauses
            else ""
        )

        parameters.append(
            limit
        )

        sql = f"""
            SELECT *
            FROM knowledge
            {where_clause}
            ORDER BY
                confidence DESC,
                evidence_count DESC,
                positive_evidence DESC,
                updated_at DESC
            LIMIT ?
        """

        with self._lock:
            rows = self._connection.execute(
                sql,
                tuple(parameters),
            ).fetchall()

        return [
            self._row_to_knowledge(row)
            for row in rows
        ]

    def count(
        self,
        agent_name: Optional[str] = None,
    ) -> int:
        """
        Count stored knowledge records.
        """

        with self._lock:
            if agent_name:
                row = self._connection.execute(
                    """
                    SELECT COUNT(*) AS count
                    FROM knowledge
                    WHERE agent_name = ?
                    """,
                    (
                        agent_name,
                    ),
                ).fetchone()

            else:
                row = self._connection.execute(
                    """
                    SELECT COUNT(*) AS count
                    FROM knowledge
                    """
                ).fetchone()

        if row is None:
            return 0

        return int(
            row["count"]
        )

    def statistics(
        self,
        agent_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Return knowledge statistics.
        """

        with self._lock:
            if agent_name:
                total_row = self._connection.execute(
                    """
                    SELECT COUNT(*) AS count
                    FROM knowledge
                    WHERE agent_name = ?
                    """,
                    (
                        agent_name,
                    ),
                ).fetchone()

                high_confidence_row = (
                    self._connection.execute(
                        """
                        SELECT COUNT(*) AS count
                        FROM knowledge
                        WHERE agent_name = ?
                          AND confidence >= 0.75
                        """,
                        (
                            agent_name,
                        ),
                    ).fetchone()
                )

            else:
                total_row = self._connection.execute(
                    """
                    SELECT COUNT(*) AS count
                    FROM knowledge
                    """
                ).fetchone()

                high_confidence_row = (
                    self._connection.execute(
                        """
                        SELECT COUNT(*) AS count
                        FROM knowledge
                        WHERE confidence >= 0.75
                        """
                    ).fetchone()
                )

        total = int(
            total_row["count"]
        ) if total_row else 0

        high_confidence = int(
            high_confidence_row["count"]
        ) if high_confidence_row else 0

        return {
            "agent_name": agent_name,
            "knowledge_count": total,
            "high_confidence_count": (
                high_confidence
            ),
            "database": str(
                self.database_path
            ),
        }

    @staticmethod
    def _reinforce_in_memory(
        knowledge: Knowledge,
        positive: bool,
        experience_id: Optional[str],
        confidence_delta: Optional[float],
    ) -> None:
        knowledge.evidence_count += 1

        if positive:
            knowledge.positive_evidence += 1
        else:
            knowledge.negative_evidence += 1

        if experience_id:
            if (
                experience_id
                not in knowledge.source_experience_ids
            ):
                knowledge.source_experience_ids.append(
                    experience_id
                )

        if confidence_delta is None:
            confidence_delta = (
                0.05
                if positive
                else -0.05
            )

        knowledge.confidence = KnowledgeStore._clamp(
            knowledge.confidence
            + confidence_delta
        )

        knowledge.updated_at = (
            datetime.now(
                timezone.utc
            ).isoformat()
        )

    @staticmethod
    def _validate(
        knowledge: Knowledge,
    ) -> None:
        if not knowledge.agent_name.strip():
            raise KnowledgeStoreError(
                "Knowledge agent_name cannot be empty."
            )

        if not knowledge.topic.strip():
            raise KnowledgeStoreError(
                "Knowledge topic cannot be empty."
            )

        if not knowledge.statement.strip():
            raise KnowledgeStoreError(
                "Knowledge statement cannot be empty."
            )

        if (
            knowledge.knowledge_type
            not in KnowledgeStore.VALID_TYPES
        ):
            raise KnowledgeStoreError(
                "Invalid knowledge_type: "
                f"{knowledge.knowledge_type}"
            )

        if not 0.0 <= knowledge.confidence <= 1.0:
            raise KnowledgeStoreError(
                "Knowledge confidence must be "
                "between 0.0 and 1.0."
            )

        if knowledge.evidence_count < 1:
            raise KnowledgeStoreError(
                "Knowledge evidence_count must "
                "be at least 1."
            )

        if (
            knowledge.positive_evidence < 0
            or knowledge.negative_evidence < 0
        ):
            raise KnowledgeStoreError(
                "Knowledge evidence counters "
                "cannot be negative."
            )

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
            raise KnowledgeStoreError(
                "Knowledge result limit must be an integer."
            ) from exc

        if value <= 0:
            raise KnowledgeStoreError(
                "Knowledge result limit must be greater than zero."
            )

        return min(
            value,
            1000,
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

    @staticmethod
    def _row_to_knowledge(
        row: sqlite3.Row,
    ) -> Knowledge:
        try:
            source_ids = json.loads(
                row[
                    "source_experience_ids_json"
                ]
            )
        except (
            TypeError,
            ValueError,
            json.JSONDecodeError,
        ):
            source_ids = []

        try:
            context = json.loads(
                row[
                    "context_json"
                ]
            )
        except (
            TypeError,
            ValueError,
            json.JSONDecodeError,
        ):
            context = {}

        if not isinstance(
            source_ids,
            list,
        ):
            source_ids = []

        if not isinstance(
            context,
            dict,
        ):
            context = {}

        return Knowledge(
            knowledge_id=row[
                "knowledge_id"
            ],
            agent_name=row[
                "agent_name"
            ],
            topic=row[
                "topic"
            ],
            statement=row[
                "statement"
            ],
            knowledge_type=row[
                "knowledge_type"
            ],
            confidence=float(
                row[
                    "confidence"
                ]
            ),
            evidence_count=int(
                row[
                    "evidence_count"
                ]
            ),
            positive_evidence=int(
                row[
                    "positive_evidence"
                ]
            ),
            negative_evidence=int(
                row[
                    "negative_evidence"
                ]
            ),
            source_experience_ids=[
                str(value)
                for value in source_ids
            ],
            context=context,
            created_at=row[
                "created_at"
            ],
            updated_at=row[
                "updated_at"
            ],
        )

    def __enter__(
        self,
    ) -> "KnowledgeStore":
        return self

    def __exit__(
        self,
        exc_type: Any,
        exc_value: Any,
        traceback: Any,
    ) -> None:
        self.close()