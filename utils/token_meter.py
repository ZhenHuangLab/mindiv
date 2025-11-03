"""
Token usage metering and cost estimation.
Tracks input, output, cached, and reasoning tokens across API calls.
"""
from typing import Dict, Any, Optional
from dataclasses import dataclass, field
import logging

logger = logging.getLogger(__name__)


@dataclass
class UsageStats:
    """
    Token usage statistics.

    Token counting assumptions (based on OpenAI API documentation):
    - cached_tokens: Subset of input_tokens representing cached prompt tokens.
      These are already included in input_tokens count.
    - reasoning_tokens: Subset of output_tokens representing reasoning tokens
      (for models like o1). These are already included in output_tokens count.

    This means:
    - Uncached input tokens = input_tokens - cached_tokens
    - Regular output tokens = output_tokens - reasoning_tokens
    """

    input_tokens: int = 0
    output_tokens: int = 0
    cached_tokens: int = 0
    reasoning_tokens: int = 0

    @property
    def total_tokens(self) -> int:
        """Total tokens (input + output, excluding cached)."""
        return self.input_tokens + self.output_tokens

    def validate(self) -> None:
        """
        Validate token counting assumptions.

        Logs warnings if the assumptions are violated:
        - cached_tokens should be <= input_tokens
        - reasoning_tokens should be <= output_tokens
        """
        if self.cached_tokens > self.input_tokens:
            logger.warning(
                f"Invalid token counts: cached_tokens ({self.cached_tokens}) > "
                f"input_tokens ({self.input_tokens}). This violates the assumption "
                f"that cached tokens are included in input tokens."
            )

        if self.reasoning_tokens > self.output_tokens:
            logger.warning(
                f"Invalid token counts: reasoning_tokens ({self.reasoning_tokens}) > "
                f"output_tokens ({self.output_tokens}). This violates the assumption "
                f"that reasoning tokens are included in output tokens."
            )

    def to_dict(self) -> Dict[str, int]:
        """Convert to dictionary."""
        return {
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "cached_tokens": self.cached_tokens,
            "reasoning_tokens": self.reasoning_tokens,
            "total_tokens": self.total_tokens,
        }


class TokenMeter:
    """
    Tracks token usage and estimates costs across multiple API calls.
    """
    
    def __init__(self, pricing: Optional[Dict[str, Dict[str, Any]]] = None):
        """
        Initialize token meter.
        
        Args:
            pricing: Pricing data dictionary (provider -> model -> rates)
        """
        self.pricing = pricing or {}
        self._usage_by_provider: Dict[str, Dict[str, UsageStats]] = {}
        self._total_usage = UsageStats()
    
    def record(
        self,
        provider: str,
        model: str,
        usage: Dict[str, Any],
    ) -> None:
        """
        Record token usage from an API call.
        
        Args:
            provider: Provider name (e.g., 'openai')
            model: Model name (e.g., 'gpt-4o')
            usage: Usage dictionary from API response
        """
        # Extract token counts
        input_tokens = usage.get("input_tokens", 0) or usage.get("prompt_tokens", 0)
        output_tokens = usage.get("output_tokens", 0) or usage.get("completion_tokens", 0)
        
        # Extract cached tokens (OpenAI-specific)
        input_details = usage.get("input_tokens_details", {})
        cached_tokens = input_details.get("cached_tokens", 0)
        
        # Extract reasoning tokens (OpenAI responses API)
        output_details = usage.get("output_tokens_details", {})
        reasoning_tokens = output_details.get("reasoning_tokens", 0)
        
        # Update provider-specific usage
        if provider not in self._usage_by_provider:
            self._usage_by_provider[provider] = {}
        
        if model not in self._usage_by_provider[provider]:
            self._usage_by_provider[provider][model] = UsageStats()
        
        stats = self._usage_by_provider[provider][model]
        stats.input_tokens += input_tokens
        stats.output_tokens += output_tokens
        stats.cached_tokens += cached_tokens
        stats.reasoning_tokens += reasoning_tokens
        
        # Update total usage
        self._total_usage.input_tokens += input_tokens
        self._total_usage.output_tokens += output_tokens
        self._total_usage.cached_tokens += cached_tokens
        self._total_usage.reasoning_tokens += reasoning_tokens
    
    def get_usage(
        self,
        provider: Optional[str] = None,
        model: Optional[str] = None,
    ) -> UsageStats:
        """
        Get usage statistics.
        
        Args:
            provider: Optional provider filter
            model: Optional model filter (requires provider)
        
        Returns:
            UsageStats for the specified scope
        """
        if provider is None:
            return self._total_usage
        
        if provider not in self._usage_by_provider:
            return UsageStats()
        
        if model is None:
            # Sum all models for this provider
            total = UsageStats()
            for stats in self._usage_by_provider[provider].values():
                total.input_tokens += stats.input_tokens
                total.output_tokens += stats.output_tokens
                total.cached_tokens += stats.cached_tokens
                total.reasoning_tokens += stats.reasoning_tokens
            return total
        
        return self._usage_by_provider[provider].get(model, UsageStats())
    
    def estimate_cost(
        self,
        provider: Optional[str] = None,
        model: Optional[str] = None,
    ) -> float:
        """
        Estimate cost in USD based on pricing data.

        Cost calculation logic:
        - Uncached input tokens: (input_tokens - cached_tokens) * prompt_price
        - Cached input tokens: cached_tokens * cached_prompt_price
        - Regular output tokens: (output_tokens - reasoning_tokens) * completion_price
        - Reasoning tokens: reasoning_tokens * reasoning_price

        This assumes (verified via validate()):
        - cached_tokens is already included in input_tokens
        - reasoning_tokens is already included in output_tokens

        Args:
            provider: Optional provider filter
            model: Optional model filter (requires provider)

        Returns:
            Estimated cost in USD
        """
        if provider is None:
            # Sum costs for all providers
            total_cost = 0.0
            for prov in self._usage_by_provider:
                total_cost += self.estimate_cost(provider=prov)
            return total_cost

        if model is None:
            # Sum costs for all models in this provider
            total_cost = 0.0
            for mdl in self._usage_by_provider.get(provider, {}):
                total_cost += self.estimate_cost(provider=provider, model=mdl)
            return total_cost

        # Get usage and pricing for specific provider/model
        usage = self.get_usage(provider, model)
        pricing = self.pricing.get(provider, {}).get(model)

        if not pricing:
            return 0.0

        # Validate token counting assumptions
        usage.validate()

        # Calculate cost per token type (prices are per 1M tokens)
        cost = 0.0

        # Regular input tokens (uncached)
        # Assumption: cached_tokens is already included in input_tokens
        uncached_input = usage.input_tokens - usage.cached_tokens
        if uncached_input > 0:
            cost += (uncached_input / 1_000_000) * pricing.get("prompt", 0.0)

        # Cached input tokens (discounted pricing)
        if usage.cached_tokens > 0:
            cost += (usage.cached_tokens / 1_000_000) * pricing.get("cached_prompt", 0.0)

        # Regular output tokens (non-reasoning)
        # Assumption: reasoning_tokens is already included in output_tokens
        regular_output = usage.output_tokens - usage.reasoning_tokens
        if regular_output > 0:
            cost += (regular_output / 1_000_000) * pricing.get("completion", 0.0)

        # Reasoning tokens (special pricing for o1/responses API)
        if usage.reasoning_tokens > 0:
            cost += (usage.reasoning_tokens / 1_000_000) * pricing.get("reasoning", 0.0)

        return cost
    
    def summary(self) -> Dict[str, Any]:
        """
        Get a complete summary of usage and costs.
        
        Returns:
            Dictionary with usage stats and cost estimates
        """
        return {
            "total_usage": self._total_usage.to_dict(),
            "total_cost_usd": self.estimate_cost(),
            "by_provider": {
                provider: {
                    "usage": self.get_usage(provider).to_dict(),
                    "cost_usd": self.estimate_cost(provider),
                    "by_model": {
                        model: {
                            "usage": stats.to_dict(),
                            "cost_usd": self.estimate_cost(provider, model),
                        }
                        for model, stats in models.items()
                    },
                }
                for provider, models in self._usage_by_provider.items()
            },
        }
    
    def reset(self) -> None:
        """Reset all usage statistics."""
        self._usage_by_provider.clear()
        self._total_usage = UsageStats()

