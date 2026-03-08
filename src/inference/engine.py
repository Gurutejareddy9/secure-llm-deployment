"""Core LLM inference engine supporting multiple backends."""

import asyncio
import os
import time
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

# ---------------------------------------------------------------------------
# Cost table (USD per 1 000 tokens)
# ---------------------------------------------------------------------------
MODEL_COST_TABLE: Dict[str, float] = {
    "gpt-3.5-turbo": 0.002,
    "gpt-4": 0.06,
    "gpt-4-turbo": 0.03,
    "small": 0.002,   # alias
    "large": 0.06,    # alias
}

DEFAULT_TIMEOUT: float = 30.0  # seconds
DEFAULT_MAX_RETRIES: int = 3


# ---------------------------------------------------------------------------
# Abstract base
# ---------------------------------------------------------------------------


class BaseInferenceEngine(ABC):
    """Abstract interface for LLM inference backends."""

    @abstractmethod
    async def infer(self, prompt: str, model: str, **kwargs: Any) -> Dict[str, Any]:
        """Run inference on *prompt* using *model*.

        Args:
            prompt: The user prompt / query text.
            model: Model identifier string.
            **kwargs: Backend-specific parameters.

        Returns:
            Dict with at minimum ``response`` (str), ``tokens_used`` (int),
            and ``cost_usd`` (float).
        """


# ---------------------------------------------------------------------------
# OpenAI backend (real requests when OPENAI_API_KEY is set)
# ---------------------------------------------------------------------------


class OpenAIEngine(BaseInferenceEngine):
    """OpenAI API backend.

    Attributes:
        timeout: Request timeout in seconds.
        max_retries: Number of retry attempts on transient failures.
    """

    def __init__(
        self,
        timeout: float = DEFAULT_TIMEOUT,
        max_retries: int = DEFAULT_MAX_RETRIES,
    ) -> None:
        """Initialise the OpenAI engine.

        Args:
            timeout: HTTP request timeout in seconds.
            max_retries: Maximum retry attempts on failure.
        """
        self.timeout = timeout
        self.max_retries = max_retries
        self._client: Optional[Any] = None

    def _get_client(self) -> Any:
        """Lazily create the OpenAI AsyncOpenAI client."""
        if self._client is None:
            try:
                from openai import AsyncOpenAI  # type: ignore[import]

                self._client = AsyncOpenAI(
                    api_key=os.getenv("OPENAI_API_KEY", ""),
                    timeout=self.timeout,
                )
            except ImportError as exc:
                raise RuntimeError("openai package is not installed.") from exc
        return self._client

    async def infer(self, prompt: str, model: str = "gpt-3.5-turbo", **kwargs: Any) -> Dict[str, Any]:
        """Call the OpenAI Chat Completions API.

        Args:
            prompt: User prompt string.
            model: OpenAI model name.
            **kwargs: Additional parameters forwarded to the API.

        Returns:
            Dict with ``response``, ``tokens_used``, and ``cost_usd``.

        Raises:
            RuntimeError: After exhausting all retries.
        """
        # Resolve aliases
        model_name = {"small": "gpt-3.5-turbo", "large": "gpt-4"}.get(model, model)
        client = self._get_client()

        for attempt in range(self.max_retries):
            try:
                completion = await client.chat.completions.create(
                    model=model_name,
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=kwargs.get("max_tokens", 1024),
                )
                tokens_used = completion.usage.total_tokens if completion.usage else 0
                cost_usd = (tokens_used / 1000) * MODEL_COST_TABLE.get(model_name, 0.002)
                return {
                    "response": completion.choices[0].message.content or "",
                    "tokens_used": tokens_used,
                    "cost_usd": cost_usd,
                }
            except Exception as exc:  # noqa: BLE001
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(2 ** attempt)
                else:
                    raise RuntimeError(f"OpenAI inference failed after {self.max_retries} retries.") from exc
        # Unreachable, satisfies type checker
        return {"response": "", "tokens_used": 0, "cost_usd": 0.0}


# ---------------------------------------------------------------------------
# Mock backend (used when no API key is configured / for testing)
# ---------------------------------------------------------------------------


class MockEngine(BaseInferenceEngine):
    """Deterministic mock engine for testing and demo purposes."""

    async def infer(self, prompt: str, model: str = "gpt-3.5-turbo", **kwargs: Any) -> Dict[str, Any]:
        """Return a canned response without making any external calls.

        Args:
            prompt: User prompt (echoed back in the response).
            model: Model identifier (included in metadata).
            **kwargs: Ignored.

        Returns:
            Dict with a mock ``response``, ``tokens_used``, and ``cost_usd``.
        """
        await asyncio.sleep(0)  # yield to event loop
        tokens = len(prompt.split()) + 20
        cost = (tokens / 1000) * MODEL_COST_TABLE.get(model, 0.002)
        return {
            "response": f"[Mock response for model={model}] You asked: {prompt[:80]}",
            "tokens_used": tokens,
            "cost_usd": cost,
        }


# ---------------------------------------------------------------------------
# Facade – picks backend based on environment
# ---------------------------------------------------------------------------


class LLMEngine:
    """High-level LLM inference facade.

    Selects between :class:`OpenAIEngine` and :class:`MockEngine` based on
    whether ``OPENAI_API_KEY`` is available in the environment.

    Attributes:
        _backend: The active inference backend instance.
    """

    def __init__(self) -> None:
        """Initialise the engine and select the appropriate backend."""
        if os.getenv("OPENAI_API_KEY"):
            self._backend: BaseInferenceEngine = OpenAIEngine()
        else:
            self._backend = MockEngine()

    async def infer(self, prompt: str, model: str = "small", **kwargs: Any) -> Dict[str, Any]:
        """Run inference with automatic timing.

        Args:
            prompt: Sanitized user prompt.
            model: Target model identifier.
            **kwargs: Forwarded to the backend.

        Returns:
            Backend response dict including ``response``, ``tokens_used``,
            ``cost_usd``, and ``latency_ms``.
        """
        start = time.perf_counter()
        result = await self._backend.infer(prompt, model=model, **kwargs)
        result["latency_ms"] = (time.perf_counter() - start) * 1000
        return result
