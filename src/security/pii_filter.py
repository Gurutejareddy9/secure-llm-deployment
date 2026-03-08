"""PII (Personally Identifiable Information) detection and redaction."""

import re
from enum import Enum
from typing import Dict, List, Tuple


class RedactionMode(str, Enum):
    """Supported PII redaction modes."""

    MASK = "mask"      # Replace characters with asterisks, keep length hint
    REMOVE = "remove"  # Delete the PII entity entirely
    REPLACE = "replace"  # Replace with a labelled placeholder, e.g. [EMAIL]


# ---------------------------------------------------------------------------
# PII Regex patterns
# ---------------------------------------------------------------------------
_PATTERNS: Dict[str, re.Pattern] = {
    "EMAIL": re.compile(
        r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b",
        re.IGNORECASE,
    ),
    "PHONE": re.compile(
        r"(\+?1[\s\-.]?)?\(?\d{3}\)?[\s\-.]?\d{3}[\s\-.]?\d{4}\b",
    ),
    "SSN": re.compile(
        r"\b(?!000|666|9\d{2})\d{3}[- ](?!00)\d{2}[- ](?!0000)\d{4}\b",
    ),
    "CREDIT_CARD": re.compile(
        r"\b(?:4\d{12}(?:\d{3})?|5[1-5]\d{14}|3[47]\d{13}|3(?:0[0-5]|[68]\d)\d{11}|6(?:011|5\d{2})\d{12})\b",
    ),
    "IP_ADDRESS": re.compile(
        r"\b(?:(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\.){3}(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\b",
    ),
    "DATE_OF_BIRTH": re.compile(
        r"\b(?:0?[1-9]|1[0-2])[\/-](?:0?[1-9]|[12]\d|3[01])[\/-](?:19|20)\d{2}\b",
    ),
}


class PIIFilter:
    """Detect and redact PII entities from text.

    Attributes:
        mode: Redaction mode (``mask``, ``remove``, or ``replace``).
        enabled_types: Set of PII types to detect.  Defaults to all types.
    """

    def __init__(
        self,
        mode: RedactionMode = RedactionMode.REPLACE,
        enabled_types: List[str] | None = None,
    ) -> None:
        """Initialise the PII filter.

        Args:
            mode: How detected PII should be redacted.
            enabled_types: List of PII type keys to enable.  Pass ``None``
                to enable all built-in types.
        """
        self.mode = mode
        self.enabled_types = set(enabled_types) if enabled_types else set(_PATTERNS.keys())

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def detect(self, text: str) -> List[Tuple[str, str]]:
        """Return a list of ``(pii_type, matched_value)`` tuples found in *text*.

        Args:
            text: Text to scan for PII.

        Returns:
            List of tuples where the first element is the PII type label
            (e.g. ``"EMAIL"``) and the second is the matched string.
        """
        findings: List[Tuple[str, str]] = []
        for pii_type, pattern in _PATTERNS.items():
            if pii_type not in self.enabled_types:
                continue
            for match in pattern.finditer(text):
                findings.append((pii_type, match.group()))
        return findings

    def redact(self, text: str) -> str:
        """Replace PII entities in *text* according to ``self.mode``.

        Args:
            text: Text that may contain PII.

        Returns:
            Text with PII redacted.
        """
        for pii_type, pattern in _PATTERNS.items():
            if pii_type not in self.enabled_types:
                continue

            if self.mode == RedactionMode.REPLACE:
                text = pattern.sub(f"[{pii_type}]", text)
            elif self.mode == RedactionMode.MASK:
                text = pattern.sub(lambda m: "*" * len(m.group()), text)
            elif self.mode == RedactionMode.REMOVE:
                text = pattern.sub("", text)

        return text

    def has_pii(self, text: str) -> bool:
        """Return True if any PII is detected in *text*.

        Args:
            text: Text to scan.
        """
        return bool(self.detect(text))
