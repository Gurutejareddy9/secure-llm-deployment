"""Queue-based batch inference processor for throughput efficiency."""

import asyncio
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Any, Dict, List, Optional

from src.inference.engine import LLMEngine
from src.monitoring.logger import get_logger

logger = get_logger(__name__)


class Priority(IntEnum):
    """Request priority levels."""

    HIGH = 0    # premium / low-latency
    STANDARD = 1


@dataclass(order=True)
class BatchItem:
    """A single item in the processing queue.

    Attributes:
        priority: Processing priority (lower = higher priority).
        prompt: The user prompt to process.
        model: Target model identifier.
        future: asyncio.Future resolved when inference completes.
        metadata: Arbitrary metadata for tracking.
    """

    priority: int
    prompt: str = field(compare=False)
    model: str = field(compare=False, default="small")
    future: Optional[asyncio.Future] = field(compare=False, default=None)
    metadata: Dict[str, Any] = field(compare=False, default_factory=dict)


class BatchProcessor:
    """Collect requests into micro-batches and process them together.

    Using batched inference reduces per-token overhead for local models and
    allows grouping of API calls to stay within rate limits.

    Attributes:
        batch_size: Maximum number of items per batch.
        wait_time: Maximum seconds to wait before flushing an incomplete batch.
        engine: LLM inference engine used to process batches.
    """

    def __init__(
        self,
        batch_size: int = 8,
        wait_time: float = 0.1,
        engine: Optional[LLMEngine] = None,
    ) -> None:
        """Initialise the batch processor.

        Args:
            batch_size: Maximum items per batch flush.
            wait_time: Time (seconds) to wait before flushing a partial batch.
            engine: Inference engine to use.  Creates a new one if not provided.
        """
        self.batch_size = batch_size
        self.wait_time = wait_time
        self.engine = engine or LLMEngine()
        self._queue: asyncio.PriorityQueue = asyncio.PriorityQueue()
        self._running = False
        self._total_processed: int = 0
        self._total_cost_usd: float = 0.0

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def submit(
        self,
        prompt: str,
        model: str = "small",
        priority: Priority = Priority.STANDARD,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Submit a prompt for batched processing.

        Args:
            prompt: User prompt text.
            model: Target model identifier.
            priority: Queue priority.
            metadata: Optional tracking metadata.

        Returns:
            Inference result dict from :meth:`~src.inference.engine.LLMEngine.infer`.
        """
        loop = asyncio.get_event_loop()
        future: asyncio.Future = loop.create_future()
        item = BatchItem(
            priority=priority.value,
            prompt=prompt,
            model=model,
            future=future,
            metadata=metadata or {},
        )
        await self._queue.put(item)
        return await future

    async def start(self) -> None:
        """Start the background batch-processing loop."""
        self._running = True
        asyncio.create_task(self._process_loop())

    async def stop(self) -> None:
        """Signal the processing loop to stop after draining the queue."""
        self._running = False
        await self._queue.join()

    @property
    def metrics(self) -> Dict[str, Any]:
        """Return current throughput and cost metrics."""
        return {
            "total_processed": self._total_processed,
            "total_cost_usd": round(self._total_cost_usd, 6),
            "queue_size": self._queue.qsize(),
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _process_loop(self) -> None:
        """Continuously drain the priority queue in batches."""
        while self._running:
            batch: List[BatchItem] = []

            try:
                # Block until at least one item is available
                first = await asyncio.wait_for(
                    self._queue.get(), timeout=self.wait_time
                )
                batch.append(first)
            except asyncio.TimeoutError:
                continue

            # Collect additional items up to batch_size without blocking
            while len(batch) < self.batch_size:
                try:
                    item = self._queue.get_nowait()
                    batch.append(item)
                except asyncio.QueueEmpty:
                    break

            await self._flush_batch(batch)

    async def _flush_batch(self, batch: List[BatchItem]) -> None:
        """Process a batch of items concurrently and resolve their futures.

        Args:
            batch: List of :class:`BatchItem` objects to process.
        """
        tasks = [
            asyncio.create_task(self.engine.infer(item.prompt, model=item.model))
            for item in batch
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for item, result in zip(batch, results):
            self._queue.task_done()
            if isinstance(result, Exception):
                item.future.set_exception(result)
            else:
                self._total_processed += 1
                self._total_cost_usd += result.get("cost_usd", 0.0)
                item.future.set_result(result)

        logger.info("Batch flushed", batch_size=len(batch))
