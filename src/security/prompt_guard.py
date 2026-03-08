"""Prompt injection guard – detect and block adversarial prompts."""

import re
from dataclasses import dataclass, field
from typing import List

# ---------------------------------------------------------------------------
# Known injection patterns (regex)
# ---------------------------------------------------------------------------
_INJECTION_PATTERNS: list[str] = [
    # Direct instruction overrides
    r"ignore\s+(all\s+)?previous\s+instructions?",
    r"disregard\s+(all\s+)?previous\s+instructions?",
    r"forget\s+(all\s+)?previous\s+instructions?",
    r"override\s+(all\s+)?previous\s+instructions?",
    r"do\s+not\s+follow\s+(previous|your)\s+instructions?",
    # Role / system prompt hijacking
    r"you\s+are\s+now\s+(a\s+)?(?:jailbroken|DAN|evil|unrestricted)",
    r"act\s+as\s+(if\s+you\s+(are|were)\s+)?(?:a\s+)?(?:jailbroken|DAN|evil|unrestricted)",
    r"pretend\s+(you\s+(are|have\s+no)\s+)?(?:restrictions?|guidelines?|rules?)",
    r"you\s+have\s+no\s+(ethical\s+)?restrictions?",
    r"(your|all)\s+(ethical\s+)?(?:constraints?|guidelines?|rules?)\s+(are\s+)?(?:removed|disabled|off)",
    # Prompt-leak attempts
    r"reveal\s+(your\s+)?(system\s+)?prompt",
    r"show\s+me\s+(your\s+)?(system\s+)?prompt",
    r"print\s+(your\s+)?(system\s+)?prompt",
    r"repeat\s+(your\s+)?(initial|system|above)\s+(instructions?|prompt)",
    # Token / delimiter smuggling
    r"</?(system|user|assistant|human|ai)>",
    r"\[INST\]|\[/INST\]",
    r"<\|im_start\|>|<\|im_end\|>",
    # Classic jailbreak keywords
    r"\bDAN\b",
    r"jailbreak",
    r"do\s+anything\s+now",
    r"no\s+longer\s+bound\s+by",
    # Manipulation via instructions embedded in content
    r"translate\s+the\s+above\s+to\s+.*and\s+then\s+ignore",
    r"summarize\s+the\s+above\s+and\s+then\s+ignore",
]

_COMPILED_PATTERNS: list[re.Pattern] = [
    re.compile(p, re.IGNORECASE | re.DOTALL) for p in _INJECTION_PATTERNS
]


@dataclass
class GuardResult:
    """Result of a prompt-injection check.

    Attributes:
        safe: True if no injection was detected.
        confidence: Injection likelihood score in [0, 1].
        matched_patterns: List of pattern descriptions that triggered.
        reason: Human-readable explanation.
    """

    safe: bool
    confidence: float
    matched_patterns: List[str] = field(default_factory=list)
    reason: str = ""

    def to_dict(self) -> dict:
        """Serialise to a plain dict."""
        return {
            "safe": self.safe,
            "confidence": self.confidence,
            "matched_patterns": self.matched_patterns,
            "reason": self.reason,
        }


class PromptGuard:
    """Detect prompt-injection attempts in user inputs.

    A lightweight, rule-based guard that computes a confidence score from
    the number and severity of matching patterns.  For production use you
    may augment this with a fine-tuned classifier.

    Attributes:
        threshold: Confidence threshold above which a prompt is blocked.
    """

    def __init__(self, threshold: float = 0.5) -> None:
        """Initialise the guard.

        Args:
            threshold: Confidence value (0–1) above which the query is
                considered unsafe.  Defaults to 0.5.
        """
        self.threshold = threshold

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def check(self, text: str) -> dict:
        """Analyse *text* for prompt-injection patterns.

        Args:
            text: Sanitized user input to inspect.

        Returns:
            A dict with keys ``safe`` (bool), ``confidence`` (float),
            ``matched_patterns`` (list), and ``reason`` (str).
        """
        matched: list[str] = []

        for i, pattern in enumerate(_COMPILED_PATTERNS):
            if pattern.search(text):
                matched.append(_INJECTION_PATTERNS[i])

        # Any single match is treated as a strong signal; additional matches
        # increase confidence further, capped at 1.0.
        confidence = min(len(matched) * 0.6, 1.0)
        safe = confidence < self.threshold

        reason = (
            "No injection patterns detected."
            if safe
            else f"Detected {len(matched)} injection pattern(s)."
        )

        return GuardResult(
            safe=safe,
            confidence=confidence,
            matched_patterns=matched,
            reason=reason,
        ).to_dict()
