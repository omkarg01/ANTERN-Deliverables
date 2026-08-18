from __future__ import annotations



import base64
import os
import secrets

from contextlib import asynccontextmanager

from typing import Any

from uuid import UUID



import psycopg

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.responses import PlainTextResponse

from fastapi.middleware.cors import CORSMiddleware

from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from pydantic import BaseModel, Field



from cmis.admin.errors import CMISError

from cmis.admin.gateway import CMISGateway

from cmis.api.auth import (
    READ_SCOPES,
    WRITE_SCOPES,
    resolve_scope,
)

from cmis.api.serializers import (

    admission_to_dict,

    chat_response_to_dict,

    context_block_to_dict,

    erasure_to_dict,

    memory_list_to_dict,

)

from cmis.config import get_database_url, get_metrics_scrape_token, load_dotenv_file
from cmis.admin.rate_limit import create_rate_limiter
from cmis.embedder import create_embedder



load_dotenv_file()



bearer_scheme = HTTPBearer(auto_error=False)





class ScopeBody(BaseModel):

    tenant_id: str | None = Field(default=None, min_length=1, max_length=128)

    user_id: str | None = Field(default=None, min_length=1, max_length=128)





class AdmitRequest(ScopeBody):

    content: str = Field(min_length=1, max_length=10_000)





class ContextRequest(ScopeBody):

    query: str = Field(min_length=1, max_length=2_000)

    max_tokens: int = Field(default=2000, ge=100, le=8000)





class ChatRequest(ScopeBody):

    query: str = Field(min_length=1, max_length=2_000)

    max_tokens: int = Field(default=2000, ge=100, le=8000)


class WorkflowLifecycleRequest(ScopeBody):
    pass





def _raise_cmis_error(exc: CMISError) -> None:

    raise HTTPException(status_code=exc.status, detail=exc.to_response().to_dict())


PROMETHEUS_CONTENT_TYPE = "text/plain; version=0.0.4; charset=utf-8"


def _extract_metrics_secret(request: Request) -> str:
    header = request.headers.get("authorization", "")
    scheme, _, remainder = header.partition(" ")
    if scheme.lower() == "bearer":
        return remainder.strip()
    if scheme.lower() == "basic":
        try:
            decoded = base64.b64decode(remainder.strip()).decode("utf-8")
        except (ValueError, UnicodeDecodeError):
            return ""
        _user, separator, password = decoded.partition(":")
        return password if separator else decoded
    return ""


def _require_metrics_scrape_auth(request: Request) -> None:
    """Grafana Cloud Metrics Endpoint probes without Authorization first and requires 401."""
    provided = _extract_metrics_secret(request)
    if not provided:
        raise HTTPException(
            status_code=401,
            detail="Metrics scrape credentials required",
            headers={"WWW-Authenticate": 'Basic realm="metrics"'},
        )
    expected = get_metrics_scrape_token()
    if expected and not secrets.compare_digest(provided, expected):
        raise HTTPException(
            status_code=401,
            detail="Invalid metrics scrape credentials",
            headers={"WWW-Authenticate": 'Basic realm="metrics"'},
        )





def _get_scope(
    credentials: HTTPAuthorizationCredentials | None,
    *,
    query_tenant: str | None = None,
    query_user: str | None = None,
    body_tenant: str | None = None,
    body_user: str | None = None,
    required_scopes: frozenset[str] | None = None,
):

    try:

        return resolve_scope(

            credentials,

            query_tenant=query_tenant,

            query_user=query_user,

            body_tenant=body_tenant,

            body_user=body_user,

            required_scopes=required_scopes,

        )

    except CMISError as exc:

        _raise_cmis_error(exc)





@asynccontextmanager

async def lifespan(app: FastAPI):

    url = get_database_url()

    conn = psycopg.connect(url, autocommit=False)

    app.state.gateway = CMISGateway(
        conn,
        create_embedder(),
        rate_limiter=create_rate_limiter(limit=100, window_seconds=60),
    )

    try:

        yield

    finally:

        conn.close()





def create_app() -> FastAPI:

    app = FastAPI(

        title="CMIS API",

        description="Conversational Memory Intelligence System HTTP API",

        version="0.1.0",

        lifespan=lifespan,

    )



    origins = os.environ.get("CMIS_CORS_ORIGINS", "http://localhost:5173").split(",")

    app.add_middleware(

        CORSMiddleware,

        allow_origins=[origin.strip() for origin in origins if origin.strip()],

        allow_credentials=True,

        allow_methods=["*"],

        allow_headers=["*"],

    )



    @app.get("/health")

    def health() -> dict[str, str]:

        gateway: CMISGateway = app.state.gateway

        return gateway.health()



    @app.get("/metrics")

    def metrics(request: Request) -> PlainTextResponse:

        _require_metrics_scrape_auth(request)

        gateway: CMISGateway = app.state.gateway

        return PlainTextResponse(
            gateway.metrics_prometheus(),
            media_type=PROMETHEUS_CONTENT_TYPE,
        )



    @app.get("/api/memories")

    def list_memories(

        credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),

        tenant_id: str | None = Query(None, min_length=1, max_length=128),

        user_id: str | None = Query(None, min_length=1, max_length=128),

    ) -> dict[str, Any]:

        scope = _get_scope(

            credentials,

            query_tenant=tenant_id,

            query_user=user_id,

            required_scopes=READ_SCOPES,

        )

        gateway: CMISGateway = app.state.gateway

        memories = gateway.admission.repository.list_active_memories(

            tenant_id=scope.tenant_id,

            user_id=scope.user_id,

        )

        return memory_list_to_dict(memories)



    @app.post("/api/memories")

    def admit_memory(

        body: AdmitRequest,

        credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),

    ) -> dict[str, Any]:

        scope = _get_scope(

            credentials,

            body_tenant=body.tenant_id,

            body_user=body.user_id,

            required_scopes=WRITE_SCOPES,

        )

        gateway: CMISGateway = app.state.gateway

        try:

            result = gateway.admit(

                tenant_id=scope.tenant_id,

                user_id=scope.user_id,

                content=body.content,

            )

        except CMISError as exc:

            _raise_cmis_error(exc)

        return admission_to_dict(result)



    @app.post("/api/context")

    def build_context(

        body: ContextRequest,

        credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),

    ) -> dict[str, Any]:

        scope = _get_scope(

            credentials,

            body_tenant=body.tenant_id,

            body_user=body.user_id,

            required_scopes=READ_SCOPES,

        )

        gateway: CMISGateway = app.state.gateway

        try:

            block = gateway.build_context(

                query=body.query,

                tenant_id=scope.tenant_id,

                user_id=scope.user_id,

                max_tokens=body.max_tokens,

            )

        except CMISError as exc:

            _raise_cmis_error(exc)

        return context_block_to_dict(block)



    @app.post("/api/chat")

    def chat(

        body: ChatRequest,

        credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),

    ) -> dict[str, Any]:

        scope = _get_scope(

            credentials,

            body_tenant=body.tenant_id,

            body_user=body.user_id,

            required_scopes=READ_SCOPES,

        )

        gateway: CMISGateway = app.state.gateway

        try:

            response = gateway.chat(

                query=body.query,

                tenant_id=scope.tenant_id,

                user_id=scope.user_id,

                max_tokens=body.max_tokens,

            )

        except CMISError as exc:

            _raise_cmis_error(exc)

        return chat_response_to_dict(response)



    @app.post("/api/admin/workflows/lifecycle")

    def trigger_lifecycle_workflow(

        body: WorkflowLifecycleRequest,

        credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),

    ) -> dict[str, Any]:

        scope = _get_scope(

            credentials,

            body_tenant=body.tenant_id,

            body_user=body.user_id,

            required_scopes=WRITE_SCOPES,

        )

        gateway: CMISGateway = app.state.gateway

        try:

            result = gateway.trigger_lifecycle_workflow(

                tenant_id=scope.tenant_id,

                user_id=scope.user_id,

            )

        except CMISError as exc:

            _raise_cmis_error(exc)

        return {

            "workflow_id": result.workflow_id,

            "run_id": result.run_id,

            "backend": result.backend,

        }



    @app.delete("/api/memories/{memory_id}")

    def delete_memory(

        memory_id: UUID,

        credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),

        tenant_id: str | None = Query(None, min_length=1, max_length=128),

        user_id: str | None = Query(None, min_length=1, max_length=128),

    ) -> dict[str, Any]:

        scope = _get_scope(

            credentials,

            query_tenant=tenant_id,

            query_user=user_id,

            required_scopes=WRITE_SCOPES,

        )

        gateway: CMISGateway = app.state.gateway

        try:

            result = gateway.hard_delete(

                memory_id=memory_id,

                tenant_id=scope.tenant_id,

                user_id=scope.user_id,

            )

        except CMISError as exc:

            _raise_cmis_error(exc)

        return erasure_to_dict(

            memory_id=result.memory_id,

            events_erased=result.events_erased,

            cascaded_memory_ids=result.cascaded_memory_ids,

        )



    return app





app = create_app()


