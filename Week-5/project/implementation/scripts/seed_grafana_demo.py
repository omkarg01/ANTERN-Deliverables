#!/usr/bin/env python3
"""Generate varied CMIS metrics on a deployed API for Grafana demos."""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request

DEFAULT_BASE = "https://antern-deliverables.onrender.com"
TENANT = "demo-tenant"
USER = "alice"


def request(
    method: str,
    path: str,
    *,
    base: str,
    body: dict | None = None,
) -> tuple[int, object]:
    url = f"{base.rstrip('/')}{path}"
    data = None if body is None else json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as response:
            raw = response.read().decode("utf-8")
            return response.status, json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            payload = {"raw": raw[:200]}
        return exc.code, payload


def admit(base: str, content: str) -> tuple[int, object]:
    return request(
        "POST",
        "/api/memories",
        base=base,
        body={"tenant_id": TENANT, "user_id": USER, "content": content},
    )


def context(base: str, query: str) -> tuple[int, object]:
    return request(
        "POST",
        "/api/context",
        base=base,
        body={"tenant_id": TENANT, "user_id": USER, "query": query},
    )


def list_memories(base: str) -> tuple[int, object]:
    return request(
        "GET",
        f"/api/memories?tenant_id={TENANT}&user_id={USER}",
        base=base,
    )


def delete_memory(base: str, memory_id: str) -> tuple[int, object]:
    return request(
        "DELETE",
        f"/api/memories/{memory_id}?tenant_id={TENANT}&user_id={USER}",
        base=base,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", default=DEFAULT_BASE)
    parser.add_argument("--delay-seconds", type=float, default=8.0)
    parser.add_argument("--skip-rate-limit", action="store_true")
    args = parser.parse_args()

    plan: list[tuple[str, str]] = []

    print(f"Target: {args.base}")
    status, health = request("GET", "/health", base=args.base)
    print(f"health {status}: {health}")

    admits = [
        "I prefer espresso after lunch",
        "My favorite color is teal",
        "I work in Pacific timezone",
        "I always take notes in markdown",
        "I avoid meetings before 10am",
        "I read sci-fi before bed",
        "I use a standing desk",
        "I drink green tea in the afternoon",
    ]
    for content in admits:
        status, payload = admit(args.base, content)
        plan.append(("admit", content[:40]))
        print(f"admit {status}: {payload.get('decision', payload)}")
        time.sleep(args.delay_seconds)

    queries_match = [
        "What do I drink in the morning?",
        "What is my favorite color?",
        "When do I avoid meetings?",
    ]
    for query in queries_match:
        status, payload = context(args.base, query)
        plan.append(("context_match", query))
        print(f"context {status}: injected={payload.get('injected_count', payload)}")
        time.sleep(args.delay_seconds)

    queries_abstain = [
        "What is the capital of Mars?",
        "Who won the 1896 Olympics?",
        "What is the weather on Jupiter?",
        "Tell me about quantum knitting",
    ]
    for query in queries_abstain:
        status, payload = context(args.base, query)
        plan.append(("context_abstain", query))
        print(f"abstain-query {status}: {payload.get('abstention_reason', payload)}")
        time.sleep(args.delay_seconds)

    status, listed = list_memories(args.base)
    memories = listed.get("memories", []) if isinstance(listed, dict) else []
    if memories:
        mid = memories[0]["memory_id"]
        status, deleted = delete_memory(args.base, mid)
        plan.append(("delete", mid))
        print(f"delete {status}: {deleted}")

    status, payload = admit(args.base, "x" * 10_001)
    plan.append(("error_too_long", "content>10000"))
    print(f"oversized admit {status}: {payload}")

    if not args.skip_rate_limit:
        print("hammering rate limit (101 admit attempts)...")
        blocked = 0
        for index in range(101):
            status, _payload = admit(args.base, f"rate limit probe {index}")
            if status == 429:
                blocked += 1
        plan.append(("rate_limit", f"blocked={blocked}"))
        print(f"rate limit probes done; 429 count={blocked}")

    print(f"Completed {len(plan)} demo steps.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
