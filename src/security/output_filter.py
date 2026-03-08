"""Output safety filter – inspect LLM responses before returning to the client."""

import re
from typing import List, Tuple

from src.security.pii_filter import PIIFilter

# ---------------------------------------------------------------------------
# Harmful / toxic content patterns
# ---------------------------------------------------------------------------
_HARMFUL_PATTERNS: List[Tuple[str, str]] = [
    # Explicit violence instructions
    (r"\bhow\s+to\s+(?:make|build|create)\s+(?:a\s+)?(?:bomb|explosive|weapon)", "weapons instructions"),
    (r"\bstep[s]?\s+to\s+(?:kill|murder|harm|poison)\b", "violence instructions"),
    # Illegal activities
    (r"\bhow\s+to\s+(?:hack|crack|bypass)\s+(?:a\s+)?(?:bank|account|system|password)\b", "hacking instructions"),
    (r"\bsynthesiz(?:e|ing)\s+(?:illegal\s+)?(?:drug|fentanyl|meth|cocaine)\b", "drug synthesis"),
    # Self-harm
    (r"\b(?:methods?\s+of\s+)?self[\s\-]harm\b", "self-harm content"),
    (r"\bsuicide\s+(?:method|instruction|how[\s\-]to)\b", "suicide instructions"),
]

_COMPILED_HARMFUL = [(re.compile(p, re.IGNORECASE), label) for p, label in _HARMFUL_PATTERNS]


class OutputFilter:
    """Filter LLM outputs for harmful or sensitive content.

    Applies two checks:
    1. Regex-based harmful-content detection.
    2. PII detection via :class:`~src.security.pii_filter.PIIFilter`.

    Attributes:
        pii_filter: PIIFilter instance used for output PII redaction.
    """

    def __init__(self) -> None:
        """Initialise the output filter."""
        self.pii_filter = PIIFilter()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def is_safe(self, text: str) -> Tuple[bool, List[str]]:
        """Check whether *text* passes all safety rules.

        Args:
            text: LLM-generated text to evaluate.

        Returns:
            A tuple ``(safe: bool, violations: List[str])``.  *violations*
            is an empty list when *safe* is True.
        """
        violations: List[str] = []
        for pattern, label in _COMPILED_HARMFUL:
            if pattern.search(text):
                violations.append(label)
        return (len(violations) == 0), violations

    def filter(self, text: str) -> str:
        """Sanitize *text* by removing harmful content and redacting PII.

        If harmful content is detected the offending sentences are replaced
        with a content-policy notice.  PII is redacted using the PII filter.

        Args:
            text: Raw LLM output text.

        Returns:
            Filtered and PII-redacted text.
        """
        safe, violations = self.is_safe(text)
        if not safe:
            # Replace entire output to avoid partial leakage
            text = (
                "[Content removed by safety filter: "
                + ", ".join(violations)
                + "]"
            )

        # Also redact any accidental PII in the output
        text = self.pii_filter.redact(text)
        return text
