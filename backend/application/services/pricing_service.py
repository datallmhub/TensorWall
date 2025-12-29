"""Pricing Service - Stub for legacy compatibility.

This module provides cost estimation for LLM requests.
"""

from typing import Dict

# Pricing per 1K tokens (USD) - simplified
MODEL_PRICING: Dict[str, Dict[str, float]] = {
    "gpt-4": {"input": 0.03, "output": 0.06},
    "gpt-4-turbo": {"input": 0.01, "output": 0.03},
    "gpt-4o": {"input": 0.005, "output": 0.015},
    "gpt-4o-mini": {"input": 0.00015, "output": 0.0006},
    "gpt-3.5-turbo": {"input": 0.0005, "output": 0.0015},
    "claude-3-opus": {"input": 0.015, "output": 0.075},
    "claude-3-sonnet": {"input": 0.003, "output": 0.015},
    "claude-3-haiku": {"input": 0.00025, "output": 0.00125},
    "claude-3.5-sonnet": {"input": 0.003, "output": 0.015},
    "mistral-large": {"input": 0.004, "output": 0.012},
    "mistral-medium": {"input": 0.0027, "output": 0.0081},
    "mistral-small": {"input": 0.001, "output": 0.003},
}

DEFAULT_PRICING = {"input": 0.001, "output": 0.002}


def estimate_cost_sync(model: str, input_tokens: int, output_tokens: int) -> float:
    """Estimate cost in USD (sync version)."""
    pricing = MODEL_PRICING.get(model, DEFAULT_PRICING)

    input_cost = (input_tokens / 1000) * pricing["input"]
    output_cost = (output_tokens / 1000) * pricing["output"]

    return input_cost + output_cost


async def estimate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    """Estimate cost in USD (async version)."""
    return estimate_cost_sync(model, input_tokens, output_tokens)


class PricingService:
    """Service for pricing calculations."""

    def __init__(self):
        self.pricing = MODEL_PRICING

    def get_pricing(self, model: str) -> Dict[str, float]:
        """Get pricing for a model."""
        return self.pricing.get(model, DEFAULT_PRICING)

    def estimate_cost(self, model: str, input_tokens: int, output_tokens: int) -> float:
        """Estimate cost for a request."""
        return estimate_cost_sync(model, input_tokens, output_tokens)


# Singleton
pricing_service = PricingService()
