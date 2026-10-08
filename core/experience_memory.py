from __future__ import annotations

import json
import os
import sqlite3
import threading
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


class ExperienceMemoryError(Exception):
    """Raised when the experience memory system cannot operate."""


@dataclass
class Experience:
    """
    A single piece of experience produced by an agent.

    Experiences are deliberately structured rather than storing only
    raw conversation text.

    This allows the future learning system to evaluate:

        goal -> decision -> action -> result -> lesson
    """

    agent_name: str
    goal: str

    decision: Optional[str] = None
    action: Optional[str] = None
    result: Optional[str] = None

    success: Optional[bool] = None

    lesson: Optional[str] = None

    confidence: Optional[float] = None

    context: Dict[str, Any] = field(
        default_factory=dict
    )

    metadata: Dict[str, Any] = field(
        default_factory=dict
    )

    experience_id: str = field(
        default_factory=lambda: str(
            uuid.uuid4()
        )
    )

    created_at: str = field(
        default_factory=lambda: datetime.now(
            timezone.utc
        ).isoformat()
    )


class ExperienceMemory:
    """
    Persistent local experience store.

    SQLite is used because it is:

        - local
        - portable
        - dependency-light
        - durable
        - suitable for mobile and desktop
        - easy to back up
        - easy to migrate later

    The memory system does not decide what an agent is allowed to do.

    It only records experience and retrieves previous experience.

    Authority remains with the existing orchestration and approval
    architecture.
    """

    def __init__(
        self,
        database_path: Optional[str] = None,
    ):
        configured_path = (
            database_path
            or os.getenv(
                "AGENT_MEMORY_DB"
            )
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
        Create the memory schema if it does not already exist.
        """

        with self._lock:
            cursor = self._connection.cursor()

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS experiences (
                    experience_id TEXT PRIMARY KEY,
                    agent_name TEXT NOT NULL,
                    goal TEXT NOT NULL,

                    decision TEXT,
                    action TEXT,
                    result TEXT,

                    success INTEGER,

                    lesson TEXT,

                    confidence REAL,

                    context_json TEXT NOT NULL,
                    metadata_json TEXT NOT NULL,

                    created_at TEXT NOT NULL
                )
                """
            )

            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS
                idx_experiences_agent
                ON experiences(agent_name)
                """
            )

            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS
                idx_experiences_created
                ON experiences(created_at)
                """
            )

            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS
                idx_experiences_success
                ON experiences(success)
                """
            )

            self._connection.commit()

    def close(self) -> None:
        """
        Close the underlying database connection.
        """

        with self._lock:
            self._connection.close()

    def save(
        self,
        experience: Experience,
    ) -> str:
        """
        Persist an experience.

        Returns the experience ID.
        """

        if not isinstance(
            experience,
            Experience,
        ):
            raise ExperienceMemoryError(
                "save() requires an Experience object."
            )

        self._validate_experience(
            experience
        )

        context_json = json.dumps(
            experience.context,
            ensure_ascii=False,
            default=str,
        )

        metadata_json = json.dumps(
            experience.metadata,
            ensure_ascii=False,
            default=str,
        )

        success_value: Optional[int]

        if experience.success is None:
            success_value = None
        else:
            success_value = (
                1
                if experience.success
                else 0
            )

        with self._lock:
            try:
                self._connection.execute(
                    """
                    INSERT OR REPLACE INTO
                    experiences (
                        experience_id,
                        agent_name,
                        goal,
                        decision,
                        action,
                        result,
                        success,
                        lesson,
                        confidence,
                        context_json,
                        metadata_json,
                        created_at
                    )
                    VALUES (
                        ?, ?, ?, ?, ?, ?, ?,
                        ?, ?, ?, ?, ?
                    )
                    """,
                    (
                        experience.experience_id,
                        experience.agent_name,
                        experience.goal,
                        experience.decision,
                        experience.action,
                        experience.result,
                        success_value,
                        experience.lesson,
                        experience.confidence,
                        context_json,
                        metadata_json,
                        experience.created_at,
                    ),
                )

                self._connection.commit()

            except sqlite3.Error as exc:
                self._connection.rollback()

                raise ExperienceMemoryError(
                    "Failed to save experience: "
                    f"{exc}"
                ) from exc

        return experience.experience_id

    def record(
        self,
        agent_name: str,
        goal: str,
        decision: Optional[str] = None,
        action: Optional[str] = None,
        result: Optional[str] = None,
        success: Optional[bool] = None,
        lesson: Optional[str] = None,
        confidence: Optional[float] = None,
        context: Optional[
            Dict[str, Any]
        ] = None,
        metadata: Optional[
            Dict[str, Any]
        ] = None,
    ) -> Experience:
        """
        Convenience method for creating and saving an experience.
        """

        experience = Experience(
            agent_name=agent_name,
            goal=goal,
            decision=decision,
            action=action,
            result=result,
            success=success,
            lesson=lesson,
            confidence=confidence,
            context=(
                context
                if context is not None
                else {}
            ),
            metadata=(
                metadata
                if metadata is not None
                else {}
            ),
        )

        self.save(experience)

        return experience

    def get(
        self,
        experience_id: str,
    ) -> Optional[Experience]:
        """
        Retrieve one experience by ID.
        """

        if not experience_id:
            return None

        with self._lock:
            row = self._connection.execute(
                """
                SELECT *
                FROM experiences
                WHERE experience_id = ?
                """,
                (
                    experience_id,
                ),
            ).fetchone()

        if row is None:
            return None

        return self._row_to_experience(
            row
        )

    def recent(
        self,
        limit: int = 20,
        agent_name: Optional[str] = None,
    ) -> List[Experience]:
        """
        Return the most recent experiences.
        """

        limit = self._normalise_limit(
            limit
        )

        with self._lock:
            if agent_name:
                rows = self._connection.execute(
                    """
                    SELECT *
                    FROM experiences
                    WHERE agent_name = ?
                    ORDER BY created_at DESC
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
                    FROM experiences
                    ORDER BY created_at DESC
                    LIMIT ?
                    """,
                    (
                        limit,
                    ),
                ).fetchall()

        return [
            self._row_to_experience(row)
            for row in rows
        ]

    def successful(
        self,
        limit: int = 20,
        agent_name: Optional[str] = None,
    ) -> List[Experience]:
        """
        Return recent successful experiences.
        """

        limit = self._normalise_limit(
            limit
        )

        with self._lock:
            if agent_name:
                rows = self._connection.execute(
                    """
                    SELECT *
                    FROM experiences
                    WHERE success = 1
                      AND agent_name = ?
                    ORDER BY created_at DESC
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
                    FROM experiences
                    WHERE success = 1
                    ORDER BY created_at DESC
                    LIMIT ?
                    """,
                    (
                        limit,
                    ),
                ).fetchall()

        return [
            self._row_to_experience(row)
            for row in rows
        ]

    def failures(
        self,
        limit: int = 20,
        agent_name: Optional[str] = None,
    ) -> List[Experience]:
        """
        Return recent failed experiences.

        Failures are important because future learning will use them
        to identify strategies that should be avoided or changed.
        """

        limit = self._normalise_limit(
            limit
        )

        with self._lock:
            if agent_name:
                rows = self._connection.execute(
                    """
                    SELECT *
                    FROM experiences
                    WHERE success = 0
                      AND agent_name = ?
                    ORDER BY created_at DESC
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
                    FROM experiences
                    WHERE success = 0
                    ORDER BY created_at DESC
                    LIMIT ?
                    """,
                    (
                        limit,
                    ),
                ).fetchall()

        return [
            self._row_to_experience(row)
            for row in rows
        ]

    def search(
        self,
        query: str,
        limit: int = 20,
        agent_name: Optional[str] = None,
    ) -> List[Experience]:
        """
        Search previous experience using SQLite text matching.

        This is intentionally simple for the first memory module.

        A future module can add semantic/vector retrieval without
        changing the Experience data model.
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

        with self._lock:
            if agent_name:
                rows = self._connection.execute(
                    """
                    SELECT *
                    FROM experiences
                    WHERE agent_name = ?
                      AND (
                          goal LIKE ?
                          OR decision LIKE ?
                          OR action LIKE ?
                          OR result LIKE ?
                          OR lesson LIKE ?
                      )
                    ORDER BY created_at DESC
                    LIMIT ?
                    """,
                    (
                        agent_name,
                        pattern,
                        pattern,
                        pattern,
                        pattern,
                        pattern,
                        limit,
                    ),
                ).fetchall()

            else:
                rows = self._connection.execute(
                    """
                    SELECT *
                    FROM experiences
                    WHERE
                        goal LIKE ?
                        OR decision LIKE ?
                        OR action LIKE ?
                        OR result LIKE ?
                        OR lesson LIKE ?
                    ORDER BY created_at DESC
                    LIMIT ?
                    """,
                    (
                        pattern,
                        pattern,
                        pattern,
                        pattern,
                        pattern,
                        limit,
                    ),
                ).fetchall()

        return [
            self._row_to_experience(row)
            for row in rows
        ]

    def count(
        self,
        agent_name: Optional[str] = None,
    ) -> int:
        """
        Return the number of stored experiences.
        """

        with self._lock:
            if agent_name:
                row = self._connection.execute(
                    """
                    SELECT COUNT(*)
                    AS count
                    FROM experiences
                    WHERE agent_name = ?
                    """,
                    (
                        agent_name,
                    ),
                ).fetchone()

            else:
                row = self._connection.execute(
                    """
                    SELECT COUNT(*)
                    AS count
                    FROM experiences
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
        Return basic memory statistics.

        These statistics will later become inputs to the learning and
        evaluation systems.
        """

        with self._lock:
            if agent_name:
                total_row = self._connection.execute(
                    """
                    SELECT COUNT(*) AS count
                    FROM experiences
                    WHERE agent_name = ?
                    """,
                    (
                        agent_name,
                    ),
                ).fetchone()

                success_row = self._connection.execute(
                    """
                    SELECT COUNT(*) AS count
                    FROM experiences
                    WHERE agent_name = ?
                      AND success = 1
                    """,
                    (
                        agent_name,
                    ),
                ).fetchone()

                failure_row = self._connection.execute(
                    """
                    SELECT COUNT(*) AS count
                    FROM experiences
                    WHERE agent_name = ?
                      AND success = 0
                    """,
                    (
                        agent_name,
                    ),
                ).fetchone()

            else:
                total_row = self._connection.execute(
                    """
                    SELECT COUNT(*) AS count
                    FROM experiences
                    """
                ).fetchone()

                success_row = self._connection.execute(
                    """
                    SELECT COUNT(*) AS count
                    FROM experiences
                    WHERE success = 1
                    """
                ).fetchone()

                failure_row = self._connection.execute(
                    """
                    SELECT COUNT(*) AS count
                    FROM experiences
                    WHERE success = 0
                    """
                ).fetchone()

        total = int(
            total_row["count"]
        ) if total_row else 0

        successes = int(
            success_row["count"]
        ) if success_row else 0

        failures = int(
            failure_row["count"]
        ) if failure_row else 0

        evaluated = (
            successes
            + failures
        )

        success_rate: Optional[float]

        if evaluated:
            success_rate = (
                successes
                / evaluated
            )
        else:
            success_rate = None

        return {
            "total_experiences": total,
            "successful_experiences": successes,
            "failed_experiences": failures,
            "evaluated_experiences": evaluated,
            "success_rate": success_rate,
            "agent_name": agent_name,
            "database": str(
                self.database_path
            ),
        }

    def export_json(
        self,
        limit: Optional[int] = None,
        agent_name: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Export experiences as JSON-compatible dictionaries.

        This will make future backup, migration and model-learning
        workflows easier.
        """

        if limit is None:
            experiences = self.recent(
                limit=1000000,
                agent_name=agent_name,
            )
        else:
            experiences = self.recent(
                limit=limit,
                agent_name=agent_name,
            )

        return [
            asdict(experience)
            for experience in experiences
        ]

    @staticmethod
    def _validate_experience(
        experience: Experience,
    ) -> None:
        if not experience.agent_name.strip():
            raise ExperienceMemoryError(
                "Experience agent_name cannot be empty."
            )

        if not experience.goal.strip():
            raise ExperienceMemoryError(
                "Experience goal cannot be empty."
            )

        if experience.confidence is not None:
            if not 0.0 <= experience.confidence <= 1.0:
                raise ExperienceMemoryError(
                    "Experience confidence must be "
                    "between 0.0 and 1.0."
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
            raise ExperienceMemoryError(
                "Memory result limit must be an integer."
            ) from exc

        if value <= 0:
            raise ExperienceMemoryError(
                "Memory result limit must be greater than zero."
            )

        return min(
            value,
            1000,
        )

    @staticmethod
    def _row_to_experience(
        row: sqlite3.Row,
    ) -> Experience:
        try:
            context = json.loads(
                row["context_json"]
            )
        except (
            TypeError,
            ValueError,
            json.JSONDecodeError,
        ):
            context = {}

        try:
            metadata = json.loads(
                row["metadata_json"]
            )
        except (
            TypeError,
            ValueError,
            json.JSONDecodeError,
        ):
            metadata = {}

        success_value = row[
            "success"
        ]

        if success_value is None:
            success = None
        else:
            success = bool(
                success_value
            )

        confidence_value = row[
            "confidence"
        ]

        confidence = (
            float(confidence_value)
            if confidence_value is not None
            else None
        )

        return Experience(
            experience_id=row[
                "experience_id"
            ],
            agent_name=row[
                "agent_name"
            ],
            goal=row[
                "goal"
            ],
            decision=row[
                "decision"
            ],
            action=row[
                "action"
            ],
            result=row[
                "result"
            ],
            success=success,
            lesson=row[
                "lesson"
            ],
            confidence=confidence,
            context=(
                context
                if isinstance(
                    context,
                    dict,
                )
                else {}
            ),
            metadata=(
                metadata
                if isinstance(
                    metadata,
                    dict,
                )
                else {}
            ),
            created_at=row[
                "created_at"
            ],
        )

    def __enter__(
        self,
    ) -> "ExperienceMemory":
        return self

    def __exit__(
        self,
        exc_type: Any,
        exc_value: Any,
        traceback: Any,
    ) -> None:
        self.close()