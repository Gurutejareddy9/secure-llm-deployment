"""Input sanitizer – validate and clean user text before processing."""

import re
from typing import Optional

import bleach

# Maximum allowed input length (characters)
MAX_INPUT_LENGTH: int = 4096

# Characters we never allow regardless of context
BLOCKLIST_PATTERN: re.Pattern = re.compile(
    r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]"  # non-printable ASCII
)

# Suspicious SQL injection keywords (basic blocklist)
SQL_PATTERNS: list[str] = [
    r"\bDROP\s+TABLE\b",
    r"\bDELETE\s+FROM\b",
    r"\bINSERT\s+INTO\b",
    r"\bSELECT\s+\*\s+FROM\b",
    r"--\s*$",
    r";\s*--",
]
_SQL_RE = re.compile("|".join(SQL_PATTERNS), re.IGNORECASE)


class InputSanitizer:
    """Sanitize and validate text inputs before they reach the LLM pipeline.

    Attributes:
        max_length: Maximum number of characters allowed per input.
    """

    def __init__(self, max_length: int = MAX_INPUT_LENGTH) -> None:
        """Initialise the sanitizer.

        Args:
            max_length: Maximum allowed input length in characters.
        """
        self.max_length = max_length

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def sanitize(self, text: str) -> str:
        """Sanitize *text* and return the cleaned version.

        Steps applied (in order):
        1. Truncate to ``max_length``.
        2. Strip HTML / script tags using *bleach*.
        3. Remove non-printable control characters.
        4. Collapse excessive whitespace.

        Args:
            text: Raw user input string.

        Returns:
            Sanitized string, safe to pass to downstream components.

        Raises:
            ValueError: If *text* is empty after sanitization.
        """
        if not isinstance(text, str):
            raise TypeError(f"Expected str, got {type(text).__name__}")

        # Step 1 – truncate
        text = text[: self.max_length]

        # Step 2 – strip HTML/scripts
        text = bleach.clean(text, tags=[], attributes={}, strip=True)

        # Step 3 – remove non-printable characters
        text = BLOCKLIST_PATTERN.sub("", text)

        # Step 4 – normalise whitespace
        text = " ".join(text.split())

        if not text:
            raise ValueError("Input is empty after sanitization.")

        return text

    def is_valid(self, text: str) -> tuple[bool, Optional[str]]:
        """Check whether *text* passes all validation rules.

        Args:
            text: Input text to validate.

        Returns:
            A tuple ``(valid: bool, reason: Optional[str])``.  *reason* is
            ``None`` when the input is valid.
        """
        if not text or not text.strip():
            return False, "Input must not be empty."
        if len(text) > self.max_length:
            return False, f"Input exceeds maximum length of {self.max_length} characters."
        if _SQL_RE.search(text):
            return False, "Input contains potentially dangerous SQL patterns."
        return True, None
