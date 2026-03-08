"""Smart query router – route queries to appropriate model tiers."""

import re
from dataclasses import dataclass
from typing import Dict, List

# ---------------------------------------------------------------------------
# Complexity signals
# ---------------------------------------------------------------------------

# Keywords that indicate a query is likely *complex* and needs the large model
COMPLEX_KEYWORDS: List[str] = [
    "analyze", "analyse", "summarize", "summarise", "compare", "evaluate",
    "research", "explain in detail", "write a report", "write an essay",
    "pros and cons", "advantages and disadvantages", "deep dive",
    "comprehensive", "thorough", "exhaustive", "step by step",
    "code review", "debug", "architecture", "design pattern",
    "legal", "medical", "financial advice", "diagnosis",
    "translate", "rewrite", "paraphrase",
]

_COMPLEX_RE = re.compile(
    r"\b(" + "|".join(re.escape(kw) for kw in COMPLEX_KEYWORDS) + r")\b",
    re.IGNORECASE,
)

# Simple, cheap model for short/straightforward queries
SMALL_MODEL = "gpt-3.5-turbo"
LARGE_MODEL = "gpt-4"

# Cost per 1 000 tokens (USD)
COST_TABLE: Dict[str, float] = {
    SMALL_MODEL: 0.002,
    LARGE_MODEL: 0.060,
}

# Length thresholds
SHORT_QUERY_THRESHOLD = 80    # characters
LONG_QUERY_THRESHOLD = 500    # characters

# Token estimation constants (used for cost approximation only)
_TOKENS_PER_WORD: int = 2       # rough estimate: ~2 LLM tokens per English word
_AVG_RESPONSE_TOKENS: int = 200  # assumed average response length in tokens


@dataclass
class RoutingDecision:
    """Result of a routing decision.

    Attributes:
        model: Model identifier to use.
        reason: Human-readable explanation for the choice.
        complexity_score: Numeric complexity estimate (0–1).
        estimated_cost_usd: Rough cost estimate based on query length.
    """

    model: str
    reason: str
    complexity_score: float
    estimated_cost_usd: float

    def to_dict(self) -> dict:
        """Serialise to a plain dict."""
        return {
            "model": self.model,
            "reason": self.reason,
            "complexity_score": self.complexity_score,
            "estimated_cost_usd": self.estimated_cost_usd,
        }


class QueryRouter:
    """Route queries to the cheapest model capable of handling them.

    The routing heuristic considers:
    - Query length (very short → small model)
    - Presence of complexity keywords
    - Number of sentences / questions

    Attributes:
        small_model: Model identifier for the small/cheap tier.
        large_model: Model identifier for the large/powerful tier.
    """

    def __init__(
        self,
        small_model: str = SMALL_MODEL,
        large_model: str = LARGE_MODEL,
    ) -> None:
        """Initialise the router.

        Args:
            small_model: Model identifier for simple queries.
            large_model: Model identifier for complex queries.
        """
        self.small_model = small_model
        self.large_model = large_model

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def route(self, query: str) -> dict:
        """Determine which model should handle *query*.

        Args:
            query: Sanitized and PII-redacted user query.

        Returns:
            A dict with keys ``model``, ``reason``, ``complexity_score``,
            and ``estimated_cost_usd``.
        """
        score = self._complexity_score(query)

        if score >= 0.5:
            model = self.large_model
            reason = f"Complex query (score={score:.2f}); routing to large model."
        else:
            model = self.small_model
            reason = f"Simple query (score={score:.2f}); routing to small model."

        # Rough cost: approx _TOKENS_PER_WORD tokens per word plus avg response length
        approx_tokens = len(query.split()) * _TOKENS_PER_WORD + _AVG_RESPONSE_TOKENS
        cost = (approx_tokens / 1000) * COST_TABLE.get(model, 0.002)

        return RoutingDecision(
            model=model,
            reason=reason,
            complexity_score=score,
            estimated_cost_usd=round(cost, 6),
        ).to_dict()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _complexity_score(self, query: str) -> float:
        """Compute a complexity score for *query* in [0, 1].

        Args:
            query: User query string.

        Returns:
            Float in [0, 1] where higher values indicate greater complexity.
        """
        score = 0.0

        # Length signal
        if len(query) >= LONG_QUERY_THRESHOLD:
            score += 0.3
        elif len(query) >= SHORT_QUERY_THRESHOLD:
            score += 0.1

        # Complexity keywords – each adds 0.3 to the score, capped at 0.6
        keyword_matches = len(_COMPLEX_RE.findall(query))
        score += min(keyword_matches * 0.3, 0.6)

        # Multi-sentence / multi-question signal
        sentence_count = max(1, query.count(".") + query.count("?") + query.count("!"))
        if sentence_count >= 3:
            score += 0.2
        elif sentence_count >= 2:
            score += 0.1

        return min(score, 1.0)
