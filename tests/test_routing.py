"""Tests for the query router."""

import pytest

from src.routing.query_router import QueryRouter, SMALL_MODEL, LARGE_MODEL


class TestQueryRouter:
    """Tests for QueryRouter."""

    def setup_method(self):
        self.router = QueryRouter()

    def test_short_simple_routes_to_small(self):
        result = self.router.route("What time is it?")
        assert result["model"] == SMALL_MODEL

    def test_long_complex_routes_to_large(self):
        long_query = (
            "Please provide a comprehensive analysis of the advantages and "
            "disadvantages of transformer-based language models versus recurrent "
            "neural networks, covering performance, scalability, and deployment "
            "cost considerations in a thorough step by step manner."
        )
        result = self.router.route(long_query)
        assert result["model"] == LARGE_MODEL

    def test_complexity_keyword_bumps_to_large(self):
        result = self.router.route("Analyze the performance of GPT-4 in legal document review.")
        assert result["model"] == LARGE_MODEL

    def test_result_has_required_fields(self):
        result = self.router.route("Hello")
        assert "model" in result
        assert "reason" in result
        assert "complexity_score" in result
        assert "estimated_cost_usd" in result

    def test_complexity_score_in_range(self):
        for query in ["Hi", "Summarize this long document about AI.", "x" * 600]:
            result = self.router.route(query)
            assert 0.0 <= result["complexity_score"] <= 1.0

    def test_estimated_cost_positive(self):
        result = self.router.route("What is 2+2?")
        assert result["estimated_cost_usd"] > 0

    def test_large_model_costs_more_than_small(self):
        simple = self.router.route("Hi")
        complex_q = self.router.route(
            "Analyze and compare the detailed legal and financial implications "
            "of deploying AI systems in healthcare versus finance sectors."
        )
        assert complex_q["estimated_cost_usd"] >= simple["estimated_cost_usd"]

    def test_multi_sentence_increases_complexity(self):
        single = self.router._complexity_score("What is AI?")
        multi = self.router._complexity_score(
            "What is AI? How does it work? What are the implications?"
        )
        assert multi >= single

    def test_very_long_query_gets_max_length_bonus(self):
        long_query = "word " * 150  # ~750 chars
        score = self.router._complexity_score(long_query)
        assert score > 0.2
