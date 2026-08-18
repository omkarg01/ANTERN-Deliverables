# CMIS Implementation



Runnable source for the **Conversational Memory Intelligence System** (D6).



**Stack:** PostgreSQL 16 + pgvector (D5-001)  

**Governed by:** `.genesis/` · **Designed in:** `design/` · **Verified in:** `verification/`



## Status



| Milestone | Status | Demo |

|-----------|--------|------|

| M1 Foundation | **L4 APPROVE** (6/6 tests) | `pytest tests/test_m1_foundation.py` |

| M2 Admission + PII | **L4 APPROVE** (5/5 tests) | `pytest tests/test_m2_admission.py` |

| M3 Ranking + context | **L4 APPROVE** (5/5 tests) | `pytest tests/test_m3_ranking.py` |

| M4 Conflict + lifecycle | **complete** | `tests/test_m4_conflict_lifecycle.py` (5 tests) |

| M5 Observability + security | **complete** | `tests/test_m5_observability.py` (6 tests) |



## Prerequisites



- Docker Desktop (or Docker Engine)

- Python 3.10+



## Setup



```bash

# From project root

docker compose -f implementation/docker-compose.yml up -d

python implementation/scripts/migrate.py



cd implementation

pip install -e ".[dev]"

export DATABASE_URL=postgresql://cmis:cmis@localhost:5433/cmis   # Windows: set DATABASE_URL=...

```



## Run tests



```bash

cd implementation

# M1–M3 full regression (16 tests)

python -m pytest tests/test_m1_foundation.py tests/test_m2_admission.py tests/test_m3_ranking.py -q -v

```



## Run HTTP API + frontend



```bash

# Terminal 1 — API (from implementation/)

pip install -e ".[dev,api,embeddings]"
cp .env.example .env   # or edit the existing .env
python scripts/migrate.py
python scripts/reembed_memories.py
python scripts/serve_api.py

```



```bash

# Terminal 2 — UI (from project root)

cd frontend

npm install

npm run dev

```



Open **http://localhost:5173**. Vite proxies `/api` and `/health` to `http://127.0.0.1:8000`.

### JWT auth (M6)

Auth is **on by default**. Set `CMIS_JWT_SECRET` in `.env`, then mint a dev token:

```bash
python scripts/mint_dev_token.py demo-tenant alice
```

Paste the token into the **Bearer token** field in the UI (or set `VITE_CMIS_AUTH_TOKEN` for the frontend).

For legacy scope-in-body mode (no JWT): `CMIS_AUTH_DISABLED=1` in `.env` (pytest uses this automatically when testing gateway paths).

API endpoints:

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/health` | DB connectivity |
| GET | `/api/memories` | List active memories (`tenant_id`, `user_id`) |
| POST | `/api/memories` | Admit memory |
| POST | `/api/context` | Build ranked context for a query |
| POST | `/api/chat` | End-to-end chat with memory (M7) |
| DELETE | `/api/memories/{id}` | GDPR hard delete |



Save verification evidence:



```bash

python -m pytest tests/ -q 2>&1 | tee ../verification/results/pytest_latest.txt

```



## Architecture (M1–M3)



```

cmis/

├── models.py              # Memory, MemoryEvent, ContextBlock, ranking types

├── embedder.py            # DeterministicEmbedder (tests) + BGEEmbedder (API via CMIS_EMBEDDER=bge)

├── config.py              # DATABASE_URL, embedding dim

├── storage/

│   └── repository.py      # Postgres dual-write (Memory + MemoryEvent)

├── retrieval/

│   └── service.py         # pgvector search + tenant filters + Layer 2 privacy

├── formation/

│   ├── extraction.py      # Query/filler rejection, memory type classification

│   └── admission.py       # Admit orchestration (extract → PII → create_memory)

├── privacy/

│   └── pii.py             # Regex PII scan; confidential retrieval intent

├── ranking/

│   └── ranker.py          # Multi-signal rank + threshold abstention (ADR-002)

└── context/

    ├── builder.py         # Token/char budget packing + Layer 3 failsafe

    └── service.py         # Retrieval → ranking → context pipeline

```



**Invariants:** Every query filters `tenant_id` + `user_id`. Every insert appends `memory_event` (ADR-001). CONFIDENTIAL excluded from general context (ADR-004).



## Environment

Copy `implementation/.env.example` to `implementation/.env` (or use the generated `.env`).  
`serve_api.py`, `migrate.py`, and `reembed_memories.py` load it when `python-dotenv` is installed (`pip install -e ".[api]"`).

| Variable | Default | Purpose |
|----------|---------|---------|
| `DATABASE_URL` | `postgresql://cmis:cmis@localhost:5433/cmis` | Postgres connection |
| `CMIS_EMBEDDER` | `deterministic` (tests) / `bge` in `.env` | Embedding backend |
| `CMIS_RELEVANCE_THRESHOLD` | `0.62` with BGE, `0.3` deterministic | Min `combined_rank` to inject |
| `CMIS_MAX_INJECT_COUNT` | `5` with BGE, unlimited in tests | Top-K cap after threshold |
| `CMIS_QUERY_NORMALIZE` | `1` | Stage 1 fuzzy query/memory normalize (I4) |
| `CMIS_HYBRID_RETRIEVAL` | `1` | BM25 + pgvector RRF (I4) |
| `CMIS_RRF_K` | `60` | RRF constant (I4) |
| `CMIS_RETRIEVAL_POOL` | `50` | Hybrid candidate pool (I4) |
| `CMIS_RERANKER` | `stub` (tests) / `local` (BGE API) | Cross-encoder rerank (I4) |
| `CMIS_RERANK_TOP_K` | `10` | Candidates into M3 ranker (I4) |
| `CMIS_API_HOST` | `127.0.0.1` | API bind host |
| `CMIS_API_PORT` | `8000` | API bind port |
| `CMIS_API_RELOAD` | `0` | Set `1` for uvicorn auto-reload |
| `CMIS_CORS_ORIGINS` | `http://localhost:5173` | Comma-separated CORS origins |
| `CMIS_AUTH_DISABLED` | `0` (set `1` for legacy scope-in-body) | Skip JWT; use query/body tenant/user |
| `CMIS_JWT_SECRET` | *(required when auth on)* | HS256 signing secret |
| `CMIS_JWT_ISSUER` | `cmis` | JWT `iss` claim |
| `CMIS_JWT_AUDIENCE` | `cmis-api` | JWT `aud` claim |
| `CMIS_LLM_PROVIDER` | `mock` | `mock` (tests) or `openai` (Groq/OpenAI-compatible) |
| `LLM_API_KEY` | — | Required when provider is not `mock` |
| `LLM_BASE_URL` | `https://api.groq.com/openai/v1` | OpenAI-compatible API base |
| `LLM_MODEL` | `llama-3.3-70b-versatile` | Chat completion model |
| `CMIS_USE_TEMPORAL` | `0` | `1` to dispatch background jobs via Temporal |
| `CMIS_TEMPORAL_HOST` | `localhost:7233` | Temporal frontend address |
| `CMIS_TEMPORAL_NAMESPACE` | `default` | Temporal namespace |
| `CMIS_TEMPORAL_TASK_QUEUE` | `cmis-background` | Worker task queue |



## Background workers (M9)



Decay, expiration, and conflict LLM jobs run asynchronously via **Temporal** (or in-process when Temporal is off).



### Local dev (no Temporal)



```bash
cd implementation
# CMIS_USE_TEMPORAL=0 in .env (default)
python -m pytest tests/test_m9_temporal.py -q -v
```



Jobs run synchronously in the API process via `WorkflowDispatcher` in-process fallback.



### Full stack (Docker Compose — deploy-shaped)



```bash
cd implementation
docker compose up -d --build
python scripts/migrate.py
```



Services: `postgres` (5433), `temporal` (7233), `api` (8000), `worker`.



Trigger lifecycle decay for a user:



```bash
curl -X POST http://localhost:8000/api/admin/workflows/lifecycle \
  -H "Content-Type: application/json" \
  -d "{\"tenant_id\":\"acme\",\"user_id\":\"alice\"}"
```



Run the worker standalone (when Temporal is already up):



```bash
python scripts/run_worker.py
```



## Next milestones



See `.genesis/plan.md`, `checkpoints/CURRENT.md`, and `design/sprint_plan.md`. Next: **M4** conflict resolution + lifecycle.


