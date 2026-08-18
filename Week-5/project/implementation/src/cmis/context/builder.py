from __future__ import annotations

from cmis.models import ContextBlock, RankedMemory, SensitivityLevel
from cmis.privacy.pii import allows_confidential_retrieval, scan_pii


def estimate_tokens(text: str) -> int:
    return max(1, len(text) // 4)


class ContextBuilder:
    """Pack ranked memories into a bounded context block (ADR-002, D3 D-01)."""

    WRAPPER_OVERHEAD_TOKENS = 25

    def build(
        self,
        ranked: list[RankedMemory],
        *,
        max_tokens: int = 2000,
        max_chars: int | None = None,
        query: str = "",
        retrieval_count: int = 0,
        abstention_reason: str | None = None,
    ) -> ContextBlock:
        safe_ranked = self._apply_failsafe_filter(ranked, query)

        if abstention_reason or not safe_ranked:
            return ContextBlock(
                memories=[],
                formatted_block="<memories>\n</memories>",
                total_tokens=0,
                overflow_truncated=False,
                abstention_reason=abstention_reason,
                retrieval_count=retrieval_count,
                ranking_count=0,
                injected_count=0,
                dropped_count=0,
            )

        ranking_count = len(safe_ranked)
        lines: list[str] = []
        included: list[RankedMemory] = []
        included_chars = 0
        overflow = False

        if max_chars is not None:
            budget = max_chars
            for item in safe_ranked:
                line = self._format_line(item)
                extra = len(line) + (1 if lines else 0)
                if included_chars + extra > budget:
                    overflow = True
                    break
                lines.append(line)
                included.append(item)
                included_chars += extra
        else:
            available = max(0, max_tokens - self.WRAPPER_OVERHEAD_TOKENS)
            running_tokens = 0
            for item in safe_ranked:
                line = self._format_line(item)
                line_tokens = estimate_tokens(line)
                if running_tokens + line_tokens > available:
                    overflow = True
                    break
                lines.append(line)
                included.append(item)
                running_tokens += line_tokens
            included_chars = sum(len(line) for line in lines)

        formatted = self._format_block(lines)
        total_tokens = estimate_tokens(formatted)
        injected_count = len(included)

        return ContextBlock(
            memories=included,
            formatted_block=formatted,
            total_tokens=total_tokens,
            overflow_truncated=overflow,
            abstention_reason=None,
            retrieval_count=retrieval_count,
            ranking_count=ranking_count,
            injected_count=injected_count,
            dropped_count=ranking_count - injected_count,
        )

    @staticmethod
    def _format_line(item: RankedMemory) -> str:
        return (
            f"- (rank={item.combined_rank:.3f}, importance={item.memory.importance:.1f}) "
            f"{item.memory.content}"
        )

    @staticmethod
    def _format_block(lines: list[str]) -> str:
        if not lines:
            return "<memories>\n</memories>"
        return "<memories>\n" + "\n".join(lines) + "\n</memories>"

    @staticmethod
    def _apply_failsafe_filter(
        ranked: list[RankedMemory],
        query: str,
    ) -> list[RankedMemory]:
        """Layer 3: re-scan and drop sensitive content unless explicitly requested."""
        if allows_confidential_retrieval(query):
            return ranked

        safe: list[RankedMemory] = []
        for item in ranked:
            if item.memory.contains_pii:
                continue
            if item.memory.sensitivity_level == SensitivityLevel.CONFIDENTIAL:
                continue
            if scan_pii(item.memory.content).contains_pii:
                continue
            safe.append(item)
        return safe
