#!/usr/bin/env python3
"""Performance benchmarking script for the LLM Gateway.

Measures end-to-end latency, throughput, cache hit rate,
and routing distribution across a sample query set.
"""

import asyncio
import statistics
import time
from typing import List

import httpx

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
BASE_URL = "http://localhost:8000"
USERNAME = "admin"
PASSWORD = "secret"
CONCURRENCY = 10
TOTAL_REQUESTS = 100

SAMPLE_QUERIES: List[str] = [
    "What is machine learning?",
    "Explain neural networks.",
    "What is Python?",
    "How does GPT work?",
    "What is machine learning?",  # duplicate to test cache
    "Analyze the pros and cons of transformer architectures in detail.",
    "Write a comprehensive report on LLM deployment security.",
    "What is 2 + 2?",
    "What is the capital of France?",
    "Explain the difference between supervised and unsupervised learning.",
]


async def get_token(client: httpx.AsyncClient) -> str:
    """Obtain a JWT access token."""
    response = await client.post(
        f"{BASE_URL}/api/v1/token",
        data={"username": USERNAME, "password": PASSWORD},
    )
    response.raise_for_status()
    return response.json()["access_token"]


async def send_query(
    client: httpx.AsyncClient,
    token: str,
    query: str,
) -> dict:
    """Send a single query and return timing + response metadata."""
    start = time.perf_counter()
    response = await client.post(
        f"{BASE_URL}/api/v1/query",
        headers={"Authorization": f"Bearer {token}"},
        json={"query": query},
        timeout=60.0,
    )
    elapsed = time.perf_counter() - start
    return {
        "status_code": response.status_code,
        "latency_ms": elapsed * 1000,
        "cached": response.json().get("cached", False) if response.status_code == 200 else False,
        "model": response.json().get("model_used", "N/A") if response.status_code == 200 else "N/A",
    }


async def run_benchmark() -> None:
    """Run the full benchmark suite."""
    print(f"\n{'='*60}")
    print("  Secure LLM Gateway – Performance Benchmark")
    print(f"{'='*60}")
    print(f"  Target: {BASE_URL}")
    print(f"  Concurrency: {CONCURRENCY}")
    print(f"  Total requests: {TOTAL_REQUESTS}")
    print(f"{'='*60}\n")

    async with httpx.AsyncClient() as client:
        # Obtain token
        try:
            token = await get_token(client)
            print("✅ Token obtained successfully.\n")
        except Exception as e:
            print(f"❌ Failed to obtain token: {e}")
            return

        # Build query list (cycle through samples)
        queries = [SAMPLE_QUERIES[i % len(SAMPLE_QUERIES)] for i in range(TOTAL_REQUESTS)]

        # Run concurrent requests in batches
        results = []
        semaphore = asyncio.Semaphore(CONCURRENCY)

        async def bounded_query(q: str) -> dict:
            async with semaphore:
                return await send_query(client, token, q)

        start_total = time.perf_counter()
        tasks = [bounded_query(q) for q in queries]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        total_time = time.perf_counter() - start_total

    # Aggregate results
    successes = [r for r in results if isinstance(r, dict) and r["status_code"] == 200]
    failures = [r for r in results if not isinstance(r, dict) or r["status_code"] != 200]
    latencies = [r["latency_ms"] for r in successes]
    cached = [r for r in successes if r["cached"]]

    model_counts: dict = {}
    for r in successes:
        m = r.get("model", "unknown")
        model_counts[m] = model_counts.get(m, 0) + 1

    print(f"{'Results':^60}")
    print("-" * 60)
    print(f"  Total requests:     {TOTAL_REQUESTS}")
    print(f"  Successful:         {len(successes)}")
    print(f"  Failed:             {len(failures)}")
    print(f"  Throughput:         {len(successes) / total_time:.1f} req/s")
    print()
    if latencies:
        print(f"  Latency (ms):")
        print(f"    Min:  {min(latencies):.1f}")
        print(f"    Max:  {max(latencies):.1f}")
        print(f"    Mean: {statistics.mean(latencies):.1f}")
        print(f"    p50:  {statistics.median(latencies):.1f}")
        print(f"    p95:  {sorted(latencies)[int(len(latencies) * 0.95)]:.1f}")
    print()
    print(f"  Cache hit rate:     {len(cached) / max(len(successes), 1) * 100:.1f}%")
    print()
    print(f"  Model distribution:")
    for model, count in model_counts.items():
        pct = count / max(len(successes), 1) * 100
        print(f"    {model}: {count} ({pct:.1f}%)")
    print("-" * 60)
    print(f"  Total wall time:    {total_time:.2f}s")
    print()


if __name__ == "__main__":
    asyncio.run(run_benchmark())
