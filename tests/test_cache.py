"""Tests for the ResponseCache (using the in-memory fallback, no Redis required)."""

import pytest

from src.cache.response_cache import ResponseCache


class TestResponseCache:
    """Tests for ResponseCache with in-memory fallback."""

    @pytest.mark.asyncio
    async def test_miss_on_empty_cache(self):
        cache = ResponseCache()
        result = await cache.get("What is Python?")
        assert result is None

    @pytest.mark.asyncio
    async def test_set_and_exact_get(self):
        cache = ResponseCache()
        response = {"response": "Python is a programming language.", "model_used": "small", "tokens_used": 10}
        await cache.set("What is Python?", response)
        result = await cache.get("What is Python?")
        assert result is not None
        assert result["response"] == "Python is a programming language."

    @pytest.mark.asyncio
    async def test_different_query_is_miss(self):
        cache = ResponseCache()
        await cache.set("What is Python?", {"response": "Python ...", "model_used": "small"})
        result = await cache.get("What is JavaScript?")
        assert result is None

    @pytest.mark.asyncio
    async def test_invalidate_removes_entry(self):
        cache = ResponseCache()
        await cache.set("What is Python?", {"response": "Python ...", "model_used": "small"})
        await cache.invalidate("What is Python?")
        result = await cache.get("What is Python?")
        assert result is None

    @pytest.mark.asyncio
    async def test_clear_empties_cache(self):
        cache = ResponseCache()
        await cache.set("Query 1", {"response": "A", "model_used": "small"})
        await cache.set("Query 2", {"response": "B", "model_used": "small"})
        await cache.clear()
        assert cache.stats["memory_entries"] == 0

    @pytest.mark.asyncio
    async def test_stats_reflect_entries(self):
        cache = ResponseCache()
        assert cache.stats["memory_entries"] == 0
        await cache.set("Q1", {"response": "R1", "model_used": "small"})
        # After set, at least one entry exists
        assert cache.stats["memory_entries"] >= 1

    def test_make_key_is_deterministic(self):
        key1 = ResponseCache._make_key("hello world")
        key2 = ResponseCache._make_key("hello world")
        assert key1 == key2

    def test_make_key_differs_for_different_queries(self):
        key1 = ResponseCache._make_key("hello")
        key2 = ResponseCache._make_key("world")
        assert key1 != key2

    def test_cosine_identical_vectors(self):
        vec = [1.0, 0.0, 0.0]
        score = ResponseCache._cosine(vec, vec)
        assert abs(score - 1.0) < 1e-6

    def test_cosine_orthogonal_vectors(self):
        a = [1.0, 0.0]
        b = [0.0, 1.0]
        score = ResponseCache._cosine(a, b)
        assert abs(score) < 1e-6
