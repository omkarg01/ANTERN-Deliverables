#!/usr/bin/env python3
"""Re-embed all memory rows using the configured production embedder (I1)."""

from __future__ import annotations

import os
import sys

import psycopg

from cmis.config import get_database_url, load_dotenv_file
from cmis.embedder import BGEEmbedder


def _vector_literal(values: list[float]) -> str:
    return "[" + ",".join(f"{v:.8f}" for v in values) + "]"


def main() -> None:
    load_dotenv_file()
    kind = os.environ.get("CMIS_EMBEDDER", "bge").strip().lower()
    if kind != "bge":
        print("Set CMIS_EMBEDDER=bge before running re-embed.", file=sys.stderr)
        raise SystemExit(1)

    embedder = BGEEmbedder()
    url = get_database_url()
    print(f"Re-embedding with {embedder.model_name} ...")

    with psycopg.connect(url, autocommit=False, connect_timeout=10) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT memory_id, content FROM memory ORDER BY created_at")
            rows = cur.fetchall()

        if not rows:
            print("No memory rows to re-embed.")
            return

        updated = 0
        for memory_id, content in rows:
            vector = embedder.embed(content)
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE memory
                    SET embedding = %s::vector,
                        embedding_model = %s,
                        updated_at = NOW()
                    WHERE memory_id = %s
                    """,
                    (_vector_literal(vector), embedder.model_name, memory_id),
                )
            updated += 1
            if updated % 25 == 0:
                conn.commit()
                print(f"  {updated}/{len(rows)} ...")

        conn.commit()

    print(f"Re-embedded {updated} memories.")


if __name__ == "__main__":
    main()
