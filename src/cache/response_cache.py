"""Redis-based semantic response cache."""

import asyncio
import hashlib
import json
import os
from typing import Any, Dict, List, Optional, Tuple

from src.monitoring.logger import get_logger
from src.monitoring.metrics import CACHE_HITS

logger = get_logger(__name__)

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", "") or None
DEFAULT_TTL = 3600  # seconds
SIMILARITY_THRESHOLD = 0.95


class ResponseCache:
    """Async semantic cache backed by Redis.

    On a cache *miss* the query embeddings are compared against stored
    query embeddings using cosine similarity.  A hit is returned when the
    similarity exceeds ``similarity_threshold``.

    When the ``sentence-transformers`` package or Redis are unavailable
    the cache degrades gracefully to a simple exact-match in-memory dict.

    Attributes:
        ttl: Time-to-live for cached entries in seconds.
        similarity_threshold: Minimum cosine similarity for a cache hit.
    """

    def __init__(
        self,
        ttl: int = DEFAULT_TTL,
        similarity_threshold: float = SIMILARITY_THRESHOLD,
    ) -> None:
        """Initialise the cache.

        Args:
            ttl: Entry time-to-live in seconds.
            similarity_threshold: Cosine similarity threshold for semantic hits.
        """
        self.ttl = ttl
        self.similarity_threshold = similarity_threshold
        self._redis: Optional[Any] = None
        self._encoder: Optional[Any] = None
        self._memory_cache: Dict[str, Any] = {}  # fallback

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def get(self, query: str) -> Optional[Dict[str, Any]]:
        """Look up *query* in the cache.

        First performs an exact-key match; if that misses, performs a
        semantic similarity search over stored embeddings.

        Args:
            query: Sanitized user query string.

        Returns:
            Cached response dict, or ``None`` on a miss.
        """
        # Exact key lookup
        key = self._make_key(query)
        exact = await self._get_by_key(key)
        if exact is not None:
            logger.debug("Cache exact hit", key=key)
            return exact

        # Semantic similarity search
        similar = await self._semantic_lookup(query)
        if similar is not None:
            logger.debug("Cache semantic hit", query=query[:50])
            return similar

        return None

    async def set(self, query: str, response: Dict[str, Any]) -> None:
        """Store *response* in the cache keyed by *query*.

        Also persists the query embedding for future semantic lookups.

        Args:
            query: Sanitized user query string.
            response: Response dict to cache.
        """
        key = self._make_key(query)
        await self._set_by_key(key, response)

        # Store embedding for semantic search
        embedding = self._embed(query)
        if embedding is not None:
            emb_key = f"emb:{key}"
            emb_entry = {"query": query, "key": key, "embedding": embedding}
            await self._set_raw(emb_key, json.dumps(emb_entry))
            # Track embedding keys
            index_key = "cache:embedding_index"
            await self._list_push(index_key, emb_key)

        logger.debug("Cache set", key=key)

    async def invalidate(self, query: str) -> None:
        """Remove the cache entry for *query*.

        Args:
            query: Query whose cache entry should be removed.
        """
        key = self._make_key(query)
        await self._delete(key)

    async def clear(self) -> None:
        """Clear the entire in-memory fallback cache."""
        self._memory_cache.clear()

    @property
    def stats(self) -> Dict[str, Any]:
        """Return basic cache statistics."""
        return {"memory_entries": len(self._memory_cache)}

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _make_key(query: str) -> str:
        """Hash *query* into a cache key using the full SHA-256 digest.

        Args:
            query: Query string to hash.
        """
        return "cache:" + hashlib.sha256(query.strip().lower().encode()).hexdigest()

    async def _get_by_key(self, key: str) -> Optional[Dict[str, Any]]:
        redis = await self._get_redis()
        if redis:
            try:
                raw = await redis.get(key)
                if raw:
                    return json.loads(raw)
            except Exception:  # noqa: BLE001
                pass
        return self._memory_cache.get(key)

    async def _set_by_key(self, key: str, value: Dict[str, Any]) -> None:
        redis = await self._get_redis()
        serialized = json.dumps(value)
        if redis:
            try:
                await redis.set(key, serialized, ex=self.ttl)
                return
            except Exception:  # noqa: BLE001
                pass
        self._memory_cache[key] = value

    async def _set_raw(self, key: str, value: str) -> None:
        redis = await self._get_redis()
        if redis:
            try:
                await redis.set(key, value, ex=self.ttl)
                return
            except Exception:  # noqa: BLE001
                pass
        self._memory_cache[key] = value

    async def _delete(self, key: str) -> None:
        redis = await self._get_redis()
        if redis:
            try:
                await redis.delete(key)
                return
            except Exception:  # noqa: BLE001
                pass
        self._memory_cache.pop(key, None)

    async def _list_push(self, key: str, value: str) -> None:
        redis = await self._get_redis()
        if redis:
            try:
                await redis.lpush(key, value)
                await redis.expire(key, self.ttl)
                return
            except Exception:  # noqa: BLE001
                pass

    async def _get_embedding_keys(self) -> List[str]:
        redis = await self._get_redis()
        if redis:
            try:
                raw = await redis.lrange("cache:embedding_index", 0, -1)
                return [r.decode() if isinstance(r, bytes) else r for r in raw]
            except Exception:  # noqa: BLE001
                pass
        return [k for k in self._memory_cache if k.startswith("emb:")]

    async def _semantic_lookup(self, query: str) -> Optional[Dict[str, Any]]:
        """Find a cached response semantically similar to *query*."""
        embedding = self._embed(query)
        if embedding is None:
            return None

        emb_keys = await self._get_embedding_keys()
        best_score: float = 0.0
        best_key: Optional[str] = None

        for emb_key in emb_keys:
            raw = await self._get_by_key(emb_key)
            if not raw or not isinstance(raw, dict):
                # Try raw string stored in memory cache
                raw_str = self._memory_cache.get(emb_key)
                if raw_str and isinstance(raw_str, str):
                    try:
                        raw = json.loads(raw_str)
                    except Exception:  # noqa: BLE001
                        continue
                else:
                    continue

            stored_emb = raw.get("embedding")
            if stored_emb is None:
                continue

            score = self._cosine(embedding, stored_emb)
            if score > best_score:
                best_score = score
                best_key = raw.get("key")

        if best_score >= self.similarity_threshold and best_key:
            return await self._get_by_key(best_key)
        return None

    def _embed(self, text: str) -> Optional[List[float]]:
        """Return a sentence embedding for *text*, or ``None`` on failure."""
        if self._encoder is None:
            try:
                from sentence_transformers import SentenceTransformer  # type: ignore[import]

                self._encoder = SentenceTransformer("all-MiniLM-L6-v2")
            except (ImportError, Exception):  # noqa: BLE001
                return None

        try:
            vector = self._encoder.encode(text, convert_to_numpy=True)
            return vector.tolist()
        except Exception:  # noqa: BLE001
            return None

    @staticmethod
    def _cosine(a: List[float], b: List[float]) -> float:
        """Compute cosine similarity between two vectors."""
        try:
            import numpy as np  # type: ignore[import]

            va = np.array(a, dtype=float)
            vb = np.array(b, dtype=float)
            denom = np.linalg.norm(va) * np.linalg.norm(vb)
            if denom == 0:
                return 0.0
            return float(np.dot(va, vb) / denom)
        except ImportError:
            # Fallback pure Python
            dot = sum(x * y for x, y in zip(a, b))
            norm_a = sum(x * x for x in a) ** 0.5
            norm_b = sum(x * x for x in b) ** 0.5
            return dot / (norm_a * norm_b) if norm_a and norm_b else 0.0

    async def _get_redis(self) -> Optional[Any]:
        """Lazily create (and cache) a Redis connection.

        Returns ``None`` if Redis is unavailable so the caller can fall back
        to the in-memory dict.
        """
        if self._redis is not None:
            return self._redis
        try:
            import redis.asyncio as aioredis  # type: ignore[import]

            client = aioredis.Redis(
                host=REDIS_HOST,
                port=REDIS_PORT,
                password=REDIS_PASSWORD,
                decode_responses=False,
            )
            await asyncio.wait_for(client.ping(), timeout=2.0)
            self._redis = client
            logger.info("Connected to Redis", host=REDIS_HOST, port=REDIS_PORT)
        except Exception:  # noqa: BLE001
            logger.warning("Redis unavailable; using in-memory cache fallback.")
            self._redis = None
        return self._redis
