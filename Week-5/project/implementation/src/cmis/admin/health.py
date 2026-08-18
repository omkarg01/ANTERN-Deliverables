from __future__ import annotations

import psycopg


def check_health(conn: psycopg.Connection) -> dict[str, str]:
    with conn.cursor() as cur:
        cur.execute("SELECT 1")
    return {"status": "ok", "database": "connected"}
