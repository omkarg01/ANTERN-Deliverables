#!/usr/bin/env python3
"""Apply versioned SQL migrations to CMIS Postgres database."""

from __future__ import annotations

import sys
from pathlib import Path

import psycopg

from cmis.config import get_database_url, load_dotenv_file

MIGRATIONS_DIR = Path(__file__).resolve().parent.parent / "migrations"


def ensure_migration_table(conn: psycopg.Connection) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                filename TEXT PRIMARY KEY,
                applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """
        )
    conn.commit()


def get_applied_migrations(conn: psycopg.Connection) -> set[str]:
    with conn.cursor() as cur:
        cur.execute("SELECT filename FROM schema_migrations")
        rows = cur.fetchall()
    return {row[0] for row in rows}


def bootstrap_legacy_database(conn: psycopg.Connection, applied: set[str]) -> set[str]:
    """Mark 001 applied when memory table exists but migration table was empty."""
    if "001_initial.sql" in applied:
        return applied
    with conn.cursor() as cur:
        cur.execute("SELECT to_regclass('public.memory')")
        if cur.fetchone()[0] is None:
            return applied
        cur.execute(
            "INSERT INTO schema_migrations (filename) VALUES (%s) ON CONFLICT DO NOTHING",
            ("001_initial.sql",),
        )
    conn.commit()
    return get_applied_migrations(conn)


def apply_migrations(conn: psycopg.Connection) -> None:
    ensure_migration_table(conn)
    applied = bootstrap_legacy_database(conn, get_applied_migrations(conn))

    migration_files = sorted(MIGRATIONS_DIR.glob("*.sql"))
    if not migration_files:
        raise SystemExit(f"No migrations found in {MIGRATIONS_DIR}")

    for path in migration_files:
        if path.name in applied:
            print(f"Skipping {path.name} (already applied)")
            continue
        sql = path.read_text(encoding="utf-8")
        print(f"Applying {path.name}...")
        with conn.cursor() as cur:
            cur.execute(sql)
            cur.execute(
                "INSERT INTO schema_migrations (filename) VALUES (%s)",
                (path.name,),
            )
        conn.commit()
        print(f"  OK: {path.name}")


def main() -> None:
    load_dotenv_file()
    url = get_database_url()
    print(f"Connecting to {url.split('@')[-1]}...")
    try:
        with psycopg.connect(url, autocommit=False, connect_timeout=5) as conn:
            apply_migrations(conn)
    except psycopg.OperationalError as exc:
        print(f"ERROR: cannot connect — {exc}", file=sys.stderr)
        print("Start Postgres: docker compose -f implementation/docker-compose.yml up -d", file=sys.stderr)
        raise SystemExit(1) from exc
    print("Migrations complete.")


if __name__ == "__main__":
    main()
