from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID


@dataclass(frozen=True)
class ErrorResponse:
    code: str
    message: str
    status: int
    trace_id: str | None = None
    field: str | None = None
    remediation: str | None = None

    def to_dict(self) -> dict[str, Any]:
        error: dict[str, Any] = {
            "code": self.code,
            "message": self.message,
        }
        if self.field is not None:
            error["field"] = self.field
        if self.trace_id is not None:
            error["trace_id"] = self.trace_id
        if self.remediation is not None:
            error["remediation"] = self.remediation
        return {"error": error}


class CMISError(Exception):
    code = "INTERNAL_ERROR"
    status = 500
    remediation: str | None = None

    def __init__(
        self,
        message: str,
        *,
        field: str | None = None,
        trace_id: str | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.field = field
        self.trace_id = trace_id

    def to_response(self) -> ErrorResponse:
        return ErrorResponse(
            code=self.code,
            message=self.message,
            status=self.status,
            field=self.field,
            trace_id=self.trace_id,
            remediation=self.remediation,
        )


class InvalidMemoryTypeError(CMISError):
    code = "INVALID_MEMORY_TYPE"
    status = 400
    remediation = "Use one of: preference, fact, constraint, context, reflection, episodic"


class ContentTooLongError(CMISError):
    code = "CONTENT_TOO_LONG"
    status = 400
    remediation = "Shorten content to 10,000 characters or fewer"


class PIIBlockedError(CMISError):
    code = "PII_BLOCKED"
    status = 403
    remediation = "Remove sensitive PII or request admin scope for confidential storage"


class MemoryNotFoundError(CMISError):
    code = "MEMORY_NOT_FOUND"
    status = 404
    remediation = "Verify memory_id, tenant_id, and user_id scope"


class UnauthorizedError(CMISError):
    code = "UNAUTHORIZED"
    status = 401
    remediation = "Provide a valid bearer token"


class ForbiddenError(CMISError):
    code = "FORBIDDEN"
    status = 403
    remediation = "Request the required OAuth scope for this operation"


class TenantIsolationViolationError(CMISError):
    code = "TENANT_ISOLATION_VIOLATION"
    status = 403
    remediation = "Access memories only within your tenant and user scope"


class RateLimitExceededError(CMISError):
    code = "RATE_LIMIT_EXCEEDED"
    status = 429
    remediation = "Retry after the rate limit window resets"


class IndexUnavailableError(CMISError):
    code = "INDEX_UNAVAILABLE"
    status = 503
    remediation = "Retry retrieval after the vector index recovers"


ERROR_CODE_MAP: dict[str, type[CMISError]] = {
    cls.code: cls
    for cls in (
        InvalidMemoryTypeError,
        ContentTooLongError,
        PIIBlockedError,
        MemoryNotFoundError,
        UnauthorizedError,
        ForbiddenError,
        TenantIsolationViolationError,
        RateLimitExceededError,
        CMISError,
        IndexUnavailableError,
    )
}
