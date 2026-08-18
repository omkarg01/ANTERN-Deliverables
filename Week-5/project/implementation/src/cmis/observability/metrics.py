from __future__ import annotations

from dataclasses import dataclass, field
from threading import Lock


@dataclass
class MetricsRegistry:
    """In-process Prometheus-style counters for CMIS operations."""

    admissions_total: int = 0
    retrievals_total: int = 0
    context_builds_total: int = 0
    hard_deletes_total: int = 0
    rate_limit_rejections_total: int = 0
    cache_hits_total: int = 0
    cache_misses_total: int = 0
    errors_total: int = 0
    _lock: Lock = field(default_factory=Lock, repr=False)

    def inc(self, metric: str, amount: int = 1) -> None:
        with self._lock:
            current = getattr(self, metric, 0)
            setattr(self, metric, current + amount)

    def render_prometheus(self) -> str:
        lines = [
            "# HELP cmis_admissions_total Total memory admissions",
            "# TYPE cmis_admissions_total counter",
            f"cmis_admissions_total {self.admissions_total}",
            "# HELP cmis_retrievals_total Total semantic retrievals",
            "# TYPE cmis_retrievals_total counter",
            f"cmis_retrievals_total {self.retrievals_total}",
            "# HELP cmis_context_builds_total Total context builds",
            "# TYPE cmis_context_builds_total counter",
            f"cmis_context_builds_total {self.context_builds_total}",
            "# HELP cmis_hard_deletes_total Total GDPR hard deletes",
            "# TYPE cmis_hard_deletes_total counter",
            f"cmis_hard_deletes_total {self.hard_deletes_total}",
            "# HELP cmis_rate_limit_rejections_total Rate limit rejections",
            "# TYPE cmis_rate_limit_rejections_total counter",
            f"cmis_rate_limit_rejections_total {self.rate_limit_rejections_total}",
            "# HELP cmis_cache_hits_total Context cache hits",
            "# TYPE cmis_cache_hits_total counter",
            f"cmis_cache_hits_total {self.cache_hits_total}",
            "# HELP cmis_cache_misses_total Context cache misses",
            "# TYPE cmis_cache_misses_total counter",
            f"cmis_cache_misses_total {self.cache_misses_total}",
            "# HELP cmis_errors_total Structured API errors",
            "# TYPE cmis_errors_total counter",
            f"cmis_errors_total {self.errors_total}",
        ]
        return "\n".join(lines) + "\n"
