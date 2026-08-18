from __future__ import annotations

import re
from dataclasses import dataclass

from cmis.models import SensitivityLevel

_SSN_RE = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
_CC_RE = re.compile(r"\b(?:\d{4}[-\s]?){3}\d{4}\b")
_EMAIL_RE = re.compile(r"\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b")
_PHONE_RE = re.compile(r"\b\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b")

_SECRET_QUERY_KEYWORDS = (
    "ssn",
    "social security",
    "password",
    "credit card",
    "passport number",
    "bank account",
)


@dataclass(frozen=True)
class PiiScanResult:
    contains_pii: bool
    sensitivity_level: SensitivityLevel
    matched_patterns: tuple[str, ...]


def scan_pii(content: str) -> PiiScanResult:
    patterns: list[str] = []
    if _SSN_RE.search(content):
        patterns.append("ssn")
    if _CC_RE.search(content):
        patterns.append("credit_card")
    if _EMAIL_RE.search(content):
        patterns.append("email")
    if _PHONE_RE.search(content):
        patterns.append("phone")

    if patterns:
        return PiiScanResult(
            contains_pii=True,
            sensitivity_level=SensitivityLevel.CONFIDENTIAL,
            matched_patterns=tuple(patterns),
        )
    return PiiScanResult(
        contains_pii=False,
        sensitivity_level=SensitivityLevel.INTERNAL,
        matched_patterns=(),
    )


def allows_confidential_retrieval(query: str) -> bool:
    """Layer 2: explicit secret intent required to retrieve CONFIDENTIAL memories."""
    lowered = query.strip().lower()
    return any(keyword in lowered for keyword in _SECRET_QUERY_KEYWORDS)
