"""Tests for the LLM inference engine and batch processor."""

import asyncio

import pytest

from src.inference.engine import LLMEngine, MockEngine, MODEL_COST_TABLE
from src.inference.batch_processor import BatchProcessor, Priority


# ---------------------------------------------------------------------------
# MockEngine tests
# ---------------------------------------------------------------------------


class TestMockEngine:
    """Tests for the MockEngine backend."""

    @pytest.mark.asyncio
    async def test_returns_response(self):
        engine = MockEngine()
        result = await engine.infer("Hello", model="gpt-3.5-turbo")
        assert "response" in result
        assert len(result["response"]) > 0

    @pytest.mark.asyncio
    async def test_returns_tokens_used(self):
        engine = MockEngine()
        result = await engine.infer("Hello", model="gpt-3.5-turbo")
        assert "tokens_used" in result
        assert result["tokens_used"] > 0

    @pytest.mark.asyncio
    async def test_returns_cost_usd(self):
        engine = MockEngine()
        result = await engine.infer("Hello", model="gpt-3.5-turbo")
        assert "cost_usd" in result
        assert result["cost_usd"] >= 0.0

    @pytest.mark.asyncio
    async def test_prompt_echoed_in_response(self):
        engine = MockEngine()
        result = await engine.infer("What is Python?", model="gpt-3.5-turbo")
        assert "What is Python?" in result["response"]

    @pytest.mark.asyncio
    async def test_large_model_costs_more(self):
        engine = MockEngine()
        prompt = "Explain deep learning."
        small = await engine.infer(prompt, model="gpt-3.5-turbo")
        large = await engine.infer(prompt, model="gpt-4")
        assert large["cost_usd"] > small["cost_usd"]


# ---------------------------------------------------------------------------
# LLMEngine facade tests
# ---------------------------------------------------------------------------


class TestLLMEngine:
    """Tests for the LLMEngine facade."""

    @pytest.mark.asyncio
    async def test_infer_returns_response(self):
        engine = LLMEngine()
        result = await engine.infer("Hello!")
        assert "response" in result

    @pytest.mark.asyncio
    async def test_latency_ms_present(self):
        engine = LLMEngine()
        result = await engine.infer("Hello!")
        assert "latency_ms" in result
        assert result["latency_ms"] >= 0

    @pytest.mark.asyncio
    async def test_default_model_is_small(self):
        engine = LLMEngine()
        result = await engine.infer("Hello!")
        # MockEngine includes model name in response
        assert "small" in result["response"]


# ---------------------------------------------------------------------------
# Model cost table tests
# ---------------------------------------------------------------------------


class TestModelCostTable:
    def test_gpt35_cheaper_than_gpt4(self):
        assert MODEL_COST_TABLE["gpt-3.5-turbo"] < MODEL_COST_TABLE["gpt-4"]

    def test_all_costs_positive(self):
        for model, cost in MODEL_COST_TABLE.items():
            assert cost > 0, f"Cost for {model} should be positive"


# ---------------------------------------------------------------------------
# BatchProcessor tests
# ---------------------------------------------------------------------------


class TestBatchProcessor:
    """Tests for the BatchProcessor."""

    @pytest.mark.asyncio
    async def test_submit_returns_result(self):
        engine = MockEngine()
        processor = BatchProcessor(batch_size=4, wait_time=0.05, engine=engine)
        await processor.start()
        result = await processor.submit("Hello batch")
        await processor.stop()
        assert "response" in result

    @pytest.mark.asyncio
    async def test_metrics_increment_after_processing(self):
        engine = MockEngine()
        processor = BatchProcessor(batch_size=4, wait_time=0.05, engine=engine)
        await processor.start()
        await processor.submit("Hello")
        await processor.stop()
        assert processor.metrics["total_processed"] >= 1

    @pytest.mark.asyncio
    async def test_priority_high_processed(self):
        engine = MockEngine()
        processor = BatchProcessor(batch_size=4, wait_time=0.05, engine=engine)
        await processor.start()
        result = await processor.submit("Urgent query", priority=Priority.HIGH)
        await processor.stop()
        assert result is not None
