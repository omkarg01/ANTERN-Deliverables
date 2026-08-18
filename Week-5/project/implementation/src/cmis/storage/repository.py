from __future__ import annotations

import json
from typing import Any
from datetime import datetime, timedelta
from uuid import UUID, uuid4

import psycopg
from psycopg.rows import dict_row

from cmis.embedder import Embedder
from cmis.models import (
    ActorType,
    EpisodeRelation,
    EventType,
    HardDeleteResult,
    MemoryCreate,
    MemoryEventRecord,
    MemoryRecord,
    MemoryStatus,
    MemoryType,
    SensitivityLevel,
)


def _vector_literal(values: list[float]) -> str:
    return "[" + ",".join(f"{v:.8f}" for v in values) + "]"


def _metadata_payload(**fields: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    for key, value in fields.items():
        if value is None:
            continue
        if isinstance(value, UUID):
            payload[key] = str(value)
        else:
            payload[key] = value
    return payload


def _row_to_memory(row: dict[str, Any]) -> MemoryRecord:
    return MemoryRecord(
        memory_id=row["memory_id"],
        tenant_id=row["tenant_id"],
        user_id=row["user_id"],
        content=row["content"],
        memory_type=MemoryType(row["memory_type"]),
        status=MemoryStatus(row["status"]),
        importance=float(row["importance"]),
        confidence=float(row["confidence"]),
        embedding_model=row["embedding_model"],
        contains_pii=row["contains_pii"],
        sensitivity_level=SensitivityLevel(row["sensitivity_level"]),
        created_at=row["created_at"],
        updated_at=row.get("updated_at"),
        valid_until=row.get("valid_until"),
        source_turn_id=row["source_turn_id"],
        created_by=ActorType(row["created_by"]),
        similarity=float(row["similarity"]) if row.get("similarity") is not None else None,
    )


class MemoryRepository:
    """Postgres persistence with dual-write to memory_event (ADR-001)."""

    def __init__(self, conn: psycopg.Connection, embedder: Embedder) -> None:
        self._conn = conn
        self._embedder = embedder

    def create_memory(self, data: MemoryCreate) -> MemoryRecord:
        memory_id = uuid4()
        event_id = uuid4()
        embedding = (
            data.embedding if data.embedding is not None else self._embedder.embed(data.content)
        )

        with self._conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                INSERT INTO memory (
                    memory_id, tenant_id, user_id, content, memory_type,
                    source_turn_id, created_by, status, importance, confidence,
                    embedding, embedding_model, contains_pii, sensitivity_level
                ) VALUES (
                    %(memory_id)s, %(tenant_id)s, %(user_id)s, %(content)s, %(memory_type)s,
                    %(source_turn_id)s, %(created_by)s, 'active', %(importance)s, %(confidence)s,
                    %(embedding)s::vector, %(embedding_model)s,
                    %(contains_pii)s, %(sensitivity_level)s
                )
                RETURNING *
                """,
                {
                    "memory_id": memory_id,
                    "tenant_id": data.tenant_id,
                    "user_id": data.user_id,
                    "content": data.content,
                    "memory_type": data.memory_type.value,
                    "source_turn_id": data.source_turn_id,
                    "created_by": data.created_by.value,
                    "importance": data.importance,
                    "confidence": data.confidence,
                    "embedding": _vector_literal(embedding),
                    "embedding_model": self._embedder.model_name,
                    "contains_pii": data.contains_pii,
                    "sensitivity_level": data.sensitivity_level.value,
                },
            )
            memory_row = cur.fetchone()
            assert memory_row is not None

            cur.execute(
                """
                INSERT INTO memory_event (
                    event_id, memory_id, tenant_id, user_id,
                    event_type, actor, status_after, content_after, reason, metadata
                ) VALUES (
                    %(event_id)s, %(memory_id)s, %(tenant_id)s, %(user_id)s,
                    'created', %(actor)s, 'active', %(content)s, %(reason)s, %(metadata)s::jsonb
                )
                """,
                {
                    "event_id": event_id,
                    "memory_id": memory_id,
                    "tenant_id": data.tenant_id,
                    "user_id": data.user_id,
                    "actor": data.created_by.value,
                    "content": data.content,
                    "reason": "Memory admitted",
                    "metadata": json.dumps(
                        _metadata_payload(
                            trace_id=data.trace_id,
                            source_turn_id=data.source_turn_id,
                            operation="admit",
                        )
                    ),
                },
            )
        self._conn.commit()
        return _row_to_memory(memory_row)

    def get_memory(
        self,
        memory_id: UUID,
        *,
        tenant_id: str,
        user_id: str,
    ) -> MemoryRecord | None:
        with self._conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                SELECT * FROM memory
                WHERE memory_id = %(memory_id)s
                  AND tenant_id = %(tenant_id)s
                  AND user_id = %(user_id)s
                """,
                {"memory_id": memory_id, "tenant_id": tenant_id, "user_id": user_id},
            )
            row = cur.fetchone()
        return _row_to_memory(row) if row else None

    def list_events_for_memory(self, memory_id: UUID) -> list[MemoryEventRecord]:
        with self._conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                SELECT * FROM memory_event
                WHERE memory_id = %(memory_id)s
                ORDER BY event_time ASC
                """,
                {"memory_id": memory_id},
            )
            rows = cur.fetchall()
        return [
            MemoryEventRecord(
                event_id=row["event_id"],
                memory_id=row["memory_id"],
                tenant_id=row["tenant_id"],
                user_id=row["user_id"],
                event_type=EventType(row["event_type"]),
                status_after=MemoryStatus(row["status_after"]),
                actor=ActorType(row["actor"]),
                event_time=row["event_time"],
                content_before=row["content_before"],
                content_after=row["content_after"],
                reason=row["reason"],
                metadata=row["metadata"],
            )
            for row in rows
        ]

    def search_by_embedding(
        self,
        *,
        tenant_id: str,
        user_id: str,
        query_embedding: list[float],
        top_k: int = 10,
        status: MemoryStatus = MemoryStatus.ACTIVE,
    ) -> list[MemoryRecord]:
        vec = _vector_literal(query_embedding)
        with self._conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                SELECT *,
                       1 - (embedding <=> %(embedding)s::vector) AS similarity
                FROM memory
                WHERE tenant_id = %(tenant_id)s
                  AND user_id = %(user_id)s
                  AND status = %(status)s
                  AND embedding IS NOT NULL
                ORDER BY embedding <=> %(embedding)s::vector
                LIMIT %(top_k)s
                """,
                {
                    "embedding": vec,
                    "tenant_id": tenant_id,
                    "user_id": user_id,
                    "status": status.value,
                    "top_k": top_k,
                },
            )
            rows = cur.fetchall()
        return [_row_to_memory(row) for row in rows]

    def search_by_fts(
        self,
        *,
        tenant_id: str,
        user_id: str,
        query: str,
        top_k: int = 10,
        status: MemoryStatus = MemoryStatus.ACTIVE,
    ) -> list[MemoryRecord]:
        with self._conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                SELECT *,
                       ts_rank_cd(content_tsv, websearch_to_tsquery('english', %(query)s)) AS similarity
                FROM memory
                WHERE tenant_id = %(tenant_id)s
                  AND user_id = %(user_id)s
                  AND status = %(status)s
                  AND content_tsv @@ websearch_to_tsquery('english', %(query)s)
                ORDER BY similarity DESC
                LIMIT %(top_k)s
                """,
                {
                    "query": query,
                    "tenant_id": tenant_id,
                    "user_id": user_id,
                    "status": status.value,
                    "top_k": top_k,
                },
            )
            rows = cur.fetchall()
        return [_row_to_memory(row) for row in rows]

    def count_for_scope(
        self,
        *,
        tenant_id: str,
        user_id: str | None = None,
        status: MemoryStatus | None = MemoryStatus.ACTIVE,
    ) -> int:
        clauses = ["tenant_id = %(tenant_id)s"]
        params: dict[str, Any] = {"tenant_id": tenant_id}
        if user_id is not None:
            clauses.append("user_id = %(user_id)s")
            params["user_id"] = user_id
        if status is not None:
            clauses.append("status = %(status)s")
            params["status"] = status.value
        where = " AND ".join(clauses)
        with self._conn.cursor() as cur:
            cur.execute(f"SELECT COUNT(*) FROM memory WHERE {where}", params)
            row = cur.fetchone()
        return int(row[0]) if row else 0

    def truncate_all(self) -> None:
        """Test helper — clear all rows."""
        with self._conn.cursor() as cur:
            cur.execute(
                "TRUNCATE memory_canonical_state, memory_episode_link, memory_event, memory CASCADE"
            )
        self._conn.commit()

    def list_active_memories(
        self,
        *,
        tenant_id: str,
        user_id: str,
        memory_type: MemoryType | None = None,
    ) -> list[MemoryRecord]:
        clauses = [
            "tenant_id = %(tenant_id)s",
            "user_id = %(user_id)s",
            "status = %(status)s",
        ]
        params: dict[str, Any] = {
            "tenant_id": tenant_id,
            "user_id": user_id,
            "status": MemoryStatus.ACTIVE.value,
        }
        if memory_type is not None:
            clauses.append("memory_type = %(memory_type)s")
            params["memory_type"] = memory_type.value
        where = " AND ".join(clauses)
        with self._conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                f"SELECT * FROM memory WHERE {where} ORDER BY created_at ASC",
                params,
            )
            rows = cur.fetchall()
        return [_row_to_memory(row) for row in rows]

    def create_episode_link(
        self,
        *,
        from_memory_id: UUID,
        to_memory_id: UUID,
        relation: EpisodeRelation,
        tenant_id: str,
        user_id: str,
    ) -> UUID:
        link_id = uuid4()
        with self._conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO memory_episode_link (
                    link_id, tenant_id, user_id,
                    from_memory_id, to_memory_id, relation
                ) VALUES (
                    %(link_id)s, %(tenant_id)s, %(user_id)s,
                    %(from_memory_id)s, %(to_memory_id)s, %(relation)s
                )
                ON CONFLICT (from_memory_id, to_memory_id, relation) DO NOTHING
                """,
                {
                    "link_id": link_id,
                    "tenant_id": tenant_id,
                    "user_id": user_id,
                    "from_memory_id": from_memory_id,
                    "to_memory_id": to_memory_id,
                    "relation": relation.value,
                },
            )
        self._conn.commit()
        return link_id

    def get_episode_predecessors(
        self,
        memory_id: UUID,
        *,
        tenant_id: str,
        user_id: str,
    ) -> list[MemoryRecord]:
        return self.get_linked_predecessors(
            memory_id,
            tenant_id=tenant_id,
            user_id=user_id,
        )

    def get_linked_predecessors(
        self,
        memory_id: UUID,
        *,
        tenant_id: str,
        user_id: str,
    ) -> list[MemoryRecord]:
        with self._conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                SELECT m.*
                FROM memory_episode_link l
                JOIN memory m ON m.memory_id = l.from_memory_id
                WHERE l.to_memory_id = %(memory_id)s
                  AND l.relation IN ('before', 'replaces')
                  AND l.tenant_id = %(tenant_id)s
                  AND l.user_id = %(user_id)s
                  AND m.status = 'active'
                ORDER BY m.created_at ASC
                """,
                {
                    "memory_id": memory_id,
                    "tenant_id": tenant_id,
                    "user_id": user_id,
                },
            )
            rows = cur.fetchall()
        return [_row_to_memory(row) for row in rows]

    def upsert_canonical_state(
        self,
        *,
        tenant_id: str,
        user_id: str,
        state_key: str,
        memory_id: UUID,
    ) -> None:
        with self._conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO memory_canonical_state (
                    tenant_id, user_id, state_key, memory_id
                ) VALUES (
                    %(tenant_id)s, %(user_id)s, %(state_key)s, %(memory_id)s
                )
                ON CONFLICT (tenant_id, user_id, state_key)
                DO UPDATE SET
                    memory_id = EXCLUDED.memory_id,
                    updated_at = NOW()
                """,
                {
                    "tenant_id": tenant_id,
                    "user_id": user_id,
                    "state_key": state_key,
                    "memory_id": memory_id,
                },
            )
        self._conn.commit()

    def upsert_canonical_state_if_absent(
        self,
        *,
        tenant_id: str,
        user_id: str,
        state_key: str,
        memory_id: UUID,
    ) -> None:
        with self._conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO memory_canonical_state (
                    tenant_id, user_id, state_key, memory_id
                ) VALUES (
                    %(tenant_id)s, %(user_id)s, %(state_key)s, %(memory_id)s
                )
                ON CONFLICT (tenant_id, user_id, state_key) DO NOTHING
                """,
                {
                    "tenant_id": tenant_id,
                    "user_id": user_id,
                    "state_key": state_key,
                    "memory_id": memory_id,
                },
            )
        self._conn.commit()

    def get_canonical_states(
        self,
        *,
        tenant_id: str,
        user_id: str,
        state_keys: tuple[str, ...] | list[str] | None = None,
    ) -> list[MemoryRecord]:
        clauses = [
            "c.tenant_id = %(tenant_id)s",
            "c.user_id = %(user_id)s",
            "m.status = 'active'",
        ]
        params: dict[str, Any] = {
            "tenant_id": tenant_id,
            "user_id": user_id,
        }
        if state_keys:
            clauses.append("c.state_key = ANY(%(state_keys)s)")
            params["state_keys"] = list(state_keys)
        where = " AND ".join(clauses)
        with self._conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                f"""
                SELECT m.*
                FROM memory_canonical_state c
                JOIN memory m ON m.memory_id = c.memory_id
                WHERE {where}
                ORDER BY c.updated_at DESC
                """,
                params,
            )
            rows = cur.fetchall()
        return [_row_to_memory(row) for row in rows]

    def supersede_memories(
        self,
        *,
        memory_ids: list[UUID],
        superseded_by: UUID,
        tenant_id: str,
        user_id: str,
        reason: str,
        actor: ActorType = ActorType.SYSTEM,
    ) -> None:
        if not memory_ids:
            return
        with self._conn.cursor(row_factory=dict_row) as cur:
            for memory_id in memory_ids:
                cur.execute(
                    """
                    UPDATE memory
                    SET status = 'superseded',
                        superseded_by = %(superseded_by)s,
                        updated_at = NOW()
                    WHERE memory_id = %(memory_id)s
                      AND tenant_id = %(tenant_id)s
                      AND user_id = %(user_id)s
                    RETURNING content
                    """,
                    {
                        "memory_id": memory_id,
                        "superseded_by": superseded_by,
                        "tenant_id": tenant_id,
                        "user_id": user_id,
                    },
                )
                row = cur.fetchone()
                if row is None:
                    continue
                cur.execute(
                    """
                    INSERT INTO memory_event (
                        event_id, memory_id, tenant_id, user_id,
                        event_type, actor, status_before, status_after,
                        content_before, reason
                    ) VALUES (
                        %(event_id)s, %(memory_id)s, %(tenant_id)s, %(user_id)s,
                        'superseded', %(actor)s, 'active', 'superseded',
                        %(content)s, %(reason)s
                    )
                    """,
                    {
                        "event_id": uuid4(),
                        "memory_id": memory_id,
                        "tenant_id": tenant_id,
                        "user_id": user_id,
                        "actor": actor.value,
                        "content": row["content"],
                        "reason": reason,
                    },
                )
            cur.execute(
                """
                UPDATE memory
                SET supersedes = %(first_id)s
                WHERE memory_id = %(superseded_by)s
                  AND tenant_id = %(tenant_id)s
                  AND user_id = %(user_id)s
                  AND supersedes IS NULL
                """,
                {
                    "first_id": memory_ids[0],
                    "superseded_by": superseded_by,
                    "tenant_id": tenant_id,
                    "user_id": user_id,
                },
            )
        self._conn.commit()

    def archive_memories(
        self,
        *,
        memory_ids: list[UUID],
        tenant_id: str,
        user_id: str,
        reason: str,
        actor: ActorType = ActorType.SYSTEM,
    ) -> int:
        archived = 0
        with self._conn.cursor(row_factory=dict_row) as cur:
            for memory_id in memory_ids:
                cur.execute(
                    """
                    UPDATE memory
                    SET status = 'archived', updated_at = NOW()
                    WHERE memory_id = %(memory_id)s
                      AND tenant_id = %(tenant_id)s
                      AND user_id = %(user_id)s
                      AND status = 'active'
                    RETURNING content
                    """,
                    {
                        "memory_id": memory_id,
                        "tenant_id": tenant_id,
                        "user_id": user_id,
                    },
                )
                row = cur.fetchone()
                if row is None:
                    continue
                archived += 1
                cur.execute(
                    """
                    INSERT INTO memory_event (
                        event_id, memory_id, tenant_id, user_id,
                        event_type, actor, status_before, status_after,
                        content_before, reason
                    ) VALUES (
                        %(event_id)s, %(memory_id)s, %(tenant_id)s, %(user_id)s,
                        'archived', %(actor)s, 'active', 'archived',
                        %(content)s, %(reason)s
                    )
                    """,
                    {
                        "event_id": uuid4(),
                        "memory_id": memory_id,
                        "tenant_id": tenant_id,
                        "user_id": user_id,
                        "actor": actor.value,
                        "content": row["content"],
                        "reason": reason,
                    },
                )
        self._conn.commit()
        return archived

    def expire_memories(self, *, as_of: datetime) -> int:
        expired = 0
        with self._conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                SELECT memory_id, tenant_id, user_id, content
                FROM memory
                WHERE status = 'active'
                  AND valid_until IS NOT NULL
                  AND valid_until <= %(as_of)s
                """,
                {"as_of": as_of},
            )
            rows = cur.fetchall()
            for row in rows:
                cur.execute(
                    """
                    UPDATE memory
                    SET status = 'superseded', updated_at = NOW()
                    WHERE memory_id = %(memory_id)s
                    """,
                    {"memory_id": row["memory_id"]},
                )
                cur.execute(
                    """
                    INSERT INTO memory_event (
                        event_id, memory_id, tenant_id, user_id,
                        event_type, actor, status_before, status_after,
                        content_before, reason
                    ) VALUES (
                        %(event_id)s, %(memory_id)s, %(tenant_id)s, %(user_id)s,
                        'superseded', 'system', 'active', 'superseded',
                        %(content)s, 'Lifecycle expiration: valid_until elapsed'
                    )
                    """,
                    {
                        "event_id": uuid4(),
                        "memory_id": row["memory_id"],
                        "tenant_id": row["tenant_id"],
                        "user_id": row["user_id"],
                        "content": row["content"],
                    },
                )
                expired += 1
        self._conn.commit()
        return expired

    def find_memories_for_decay(
        self,
        *,
        tenant_id: str,
        user_id: str,
        as_of: datetime,
        min_age_days: int = 365,
        max_importance: float = 0.5,
    ) -> list[MemoryRecord]:
        with self._conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                SELECT *
                FROM memory
                WHERE tenant_id = %(tenant_id)s
                  AND user_id = %(user_id)s
                  AND status = 'active'
                  AND importance < %(max_importance)s
                  AND created_at <= %(cutoff)s
                ORDER BY created_at ASC
                """,
                {
                    "tenant_id": tenant_id,
                    "user_id": user_id,
                    "max_importance": max_importance,
                    "cutoff": as_of - timedelta(days=min_age_days),
                },
            )
            rows = cur.fetchall()
        return [_row_to_memory(row) for row in rows]

    def set_memory_created_at(self, memory_id: UUID, created_at: datetime) -> None:
        """Test helper — backdate created_at for lifecycle tests."""
        with self._conn.cursor() as cur:
            cur.execute(
                """
                UPDATE memory
                SET created_at = %(created_at)s, updated_at = %(created_at)s
                WHERE memory_id = %(memory_id)s
                """,
                {"memory_id": memory_id, "created_at": created_at},
            )
        self._conn.commit()

    def append_audit_event(
        self,
        *,
        memory_id: UUID,
        tenant_id: str,
        user_id: str,
        event_type: EventType,
        reason: str,
        metadata: dict[str, Any] | None = None,
        actor: ActorType = ActorType.SYSTEM,
    ) -> None:
        with self._conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO memory_event (
                    event_id, memory_id, tenant_id, user_id,
                    event_type, actor, status_after, reason, metadata
                ) VALUES (
                    %(event_id)s, %(memory_id)s, %(tenant_id)s, %(user_id)s,
                    %(event_type)s, %(actor)s, 'active', %(reason)s, %(metadata)s::jsonb
                )
                """,
                {
                    "event_id": uuid4(),
                    "memory_id": memory_id,
                    "tenant_id": tenant_id,
                    "user_id": user_id,
                    "event_type": event_type.value,
                    "actor": actor.value,
                    "reason": reason,
                    "metadata": json.dumps(metadata or {}),
                },
            )
        self._conn.commit()

    def memory_exists(self, memory_id: UUID) -> bool:
        with self._conn.cursor() as cur:
            cur.execute("SELECT 1 FROM memory WHERE memory_id = %s", (memory_id,))
            return cur.fetchone() is not None

    def count_with_embedding(
        self,
        *,
        tenant_id: str,
        user_id: str,
    ) -> int:
        with self._conn.cursor() as cur:
            cur.execute(
                """
                SELECT COUNT(*)
                FROM memory
                WHERE tenant_id = %s
                  AND user_id = %s
                  AND embedding IS NOT NULL
                """,
                (tenant_id, user_id),
            )
            row = cur.fetchone()
        return int(row[0]) if row else 0

    def hard_delete_memory(
        self,
        *,
        memory_id: UUID,
        tenant_id: str,
        user_id: str,
        actor: ActorType = ActorType.ADMIN,
        trace_id: str | None = None,
    ) -> HardDeleteResult:
        with self._conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                SELECT memory_id FROM memory
                WHERE tenant_id = %(tenant_id)s
                  AND user_id = %(user_id)s
                  AND (supersedes = %(memory_id)s OR superseded_by = %(memory_id)s)
                """,
                {
                    "memory_id": memory_id,
                    "tenant_id": tenant_id,
                    "user_id": user_id,
                },
            )
            cascaded_ids = [row["memory_id"] for row in cur.fetchall()]
            all_ids = [memory_id, *cascaded_ids]

            cur.execute(
                """
                SELECT COUNT(*) AS event_count
                FROM memory_event
                WHERE memory_id = ANY(%(memory_ids)s)
                """,
                {"memory_ids": all_ids},
            )
            event_count_row = cur.fetchone()
            events_erased = int(event_count_row["event_count"]) if event_count_row else 0

            for mid in all_ids:
                cur.execute(
                    """
                    DELETE FROM memory
                    WHERE memory_id = %(memory_id)s
                      AND tenant_id = %(tenant_id)s
                      AND user_id = %(user_id)s
                    """,
                    {
                        "memory_id": mid,
                        "tenant_id": tenant_id,
                        "user_id": user_id,
                    },
                )

        self._conn.commit()
        return HardDeleteResult(
            events_erased=events_erased,
            cascaded_memory_ids=tuple(cascaded_ids),
        )
