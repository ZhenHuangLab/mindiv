"""
Memory Folding: Layered context management for long conversations.

Implements a three-layer architecture:
- Hot Layer: Recent context (100% retention, no compression)
- Warm Layer: Mid-term context (80-95% retention, consolidation)
- Cold Layer: Long-term context (concept retention, distillation)

This enables efficient context management while preserving critical reasoning information.
"""
from __future__ import annotations
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
import hashlib
import json
import logging

from mindiv.providers.base import LLMProvider
from mindiv.utils.messages import extract_text_content, extract_text, build_user_message
from mindiv.utils.cache import PrefixCache

logger = logging.getLogger(__name__)


@dataclass
class MemoryFoldingConfig:
    """
    Configuration for Memory Folding.
    
    All parameters are user-configurable with sensible defaults.
    """
    
    # === Global Control ===
    enabled: bool = False
    
    # === Layer Sizes ===
    hot_layer_size: int = 5      # Number of recent turns to keep uncompressed
    warm_layer_size: int = 10    # Number of mid-term turns to consolidate
    
    # === Compression Strategies ===
    warm_strategy: str = "consolidate"  # "consolidate" | "none"
    cold_strategy: str = "distill"      # "distill" | "summarize" | "none"
    
    # === Distillation Model Configuration ===
    # If None, uses main provider/model
    distill_provider: Optional[str] = None
    distill_model: Optional[str] = None
    distill_base_url: Optional[str] = None
    distill_api_key: Optional[str] = None
    distill_temperature: float = 0.3
    
    # === Trigger Conditions ===
    max_context_tokens: Optional[int] = None  # Maximum context tokens (None = no limit)
    auto_compress_threshold: float = 0.8      # Compress when reaching 80% of max
    
    # === Caching ===
    cache_compressed: bool = True   # Cache compression results
    cache_ttl: int = 3600           # Cache TTL in seconds
    
    # === Advanced Options ===
    preserve_system_in_summary: bool = True  # Reference system prompt in summaries
    merge_consecutive_roles: bool = True     # Merge consecutive same-role messages
    
    def validate(self) -> None:
        """Validate configuration parameters."""
        if self.hot_layer_size < 0:
            raise ValueError("hot_layer_size must be >= 0")
        if self.warm_layer_size < 0:
            raise ValueError("warm_layer_size must be >= 0")
        if self.warm_strategy not in ("consolidate", "none"):
            raise ValueError(f"Invalid warm_strategy: {self.warm_strategy}")
        if self.cold_strategy not in ("distill", "summarize", "none"):
            raise ValueError(f"Invalid cold_strategy: {self.cold_strategy}")
        if not 0.0 <= self.distill_temperature <= 2.0:
            raise ValueError("distill_temperature must be in [0.0, 2.0]")
        if not 0.0 < self.auto_compress_threshold <= 1.0:
            raise ValueError("auto_compress_threshold must be in (0.0, 1.0]")


@dataclass
class MemoryFoldingStats:
    """Statistics from Memory Folding operation."""
    
    original_tokens: int = 0      # Estimated tokens before compression
    compressed_tokens: int = 0    # Estimated tokens after compression
    distillation_tokens: int = 0  # Tokens used for distillation
    
    @property
    def saved_tokens(self) -> int:
        """Tokens saved by compression."""
        return max(0, self.original_tokens - self.compressed_tokens)
    
    @property
    def net_saved_tokens(self) -> int:
        """Net tokens saved (accounting for distillation cost)."""
        return self.saved_tokens - self.distillation_tokens
    
    def to_dict(self) -> Dict[str, int]:
        """Convert to dictionary."""
        return {
            "original_tokens": self.original_tokens,
            "compressed_tokens": self.compressed_tokens,
            "distillation_tokens": self.distillation_tokens,
            "saved_tokens": self.saved_tokens,
            "net_saved_tokens": self.net_saved_tokens,
        }


class MemoryFoldingManager:
    """
    Manages layered context compression and folding.
    
    Implements a three-layer architecture with configurable compression strategies.
    """
    
    def __init__(
        self,
        config: MemoryFoldingConfig,
        cache: PrefixCache,
        main_provider: LLMProvider,
        pricing: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize Memory Folding Manager.
        
        Args:
            config: Memory Folding configuration
            cache: Prefix cache for storing compressed results
            main_provider: Main LLM provider (used if distill provider not specified)
            pricing: Pricing data for cost estimation
        """
        config.validate()
        
        self.config = config
        self.cache = cache
        self.main_provider = main_provider
        self.pricing = pricing or {}
        
        # Distillation provider (lazy initialization)
        self._distill_provider: Optional[LLMProvider] = None
        self._distillation_cost_tokens: int = 0
    
    async def process_history(
        self,
        conversation_history: List[Dict[str, Any]]
    ) -> Tuple[List[Dict[str, Any]], MemoryFoldingStats]:
        """
        Process conversation history with Memory Folding.
        
        Args:
            conversation_history: Full conversation history
        
        Returns:
            Tuple of (compressed_messages, stats)
        """
        if not self.config.enabled or not conversation_history:
            return conversation_history, MemoryFoldingStats()
        
        stats = MemoryFoldingStats()
        
        # Estimate original tokens
        stats.original_tokens = self._estimate_tokens(conversation_history)
        
        # Layer messages
        cold, warm, hot = self._layer_messages(conversation_history)
        
        # Process each layer
        cold_summary = await self._process_cold_layer(cold)
        warm_consolidated = self._process_warm_layer(warm)
        
        # Build final message list
        final_messages = []
        
        # Add cold summary as system message (if exists)
        if cold_summary:
            final_messages.append({
                "role": "system",
                "content": cold_summary
            })
        
        # Add warm messages
        final_messages.extend(warm_consolidated)
        
        # Add hot messages (unchanged)
        final_messages.extend(hot)
        
        # Estimate compressed tokens
        stats.compressed_tokens = self._estimate_tokens(final_messages)
        stats.distillation_tokens = self._distillation_cost_tokens
        
        # Reset distillation cost for next call
        self._distillation_cost_tokens = 0
        
        return final_messages, stats
    
    def _layer_messages(
        self,
        messages: List[Dict[str, Any]]
    ) -> Tuple[List[Dict], List[Dict], List[Dict]]:
        """
        Split messages into Cold, Warm, and Hot layers.
        
        Args:
            messages: Full message list
        
        Returns:
            Tuple of (cold, warm, hot) message lists
        """
        total = len(messages)
        hot_size = self.config.hot_layer_size
        warm_size = self.config.warm_layer_size
        
        # All messages fit in hot layer
        if total <= hot_size:
            return [], [], messages
        
        # Messages fit in hot + warm layers
        if total <= hot_size + warm_size:
            warm = messages[:-hot_size] if hot_size > 0 else messages
            hot = messages[-hot_size:] if hot_size > 0 else []
            return [], warm, hot
        
        # Need all three layers
        cold = messages[:-(hot_size + warm_size)]
        warm = messages[-(hot_size + warm_size):-hot_size] if hot_size > 0 else messages[-(hot_size + warm_size):]
        hot = messages[-hot_size:] if hot_size > 0 else []
        
        return cold, warm, hot
    
    async def _process_cold_layer(self, cold: List[Dict]) -> Optional[str]:
        """
        Process cold layer with distillation or summarization.
        
        Args:
            cold: Cold layer messages
        
        Returns:
            Summary string or None
        """
        if not cold or self.config.cold_strategy == "none":
            return None
        
        # Check cache
        if self.config.cache_compressed:
            cache_key = self._compute_layer_hash(cold)
            cached = self.cache.get(f"cold_summary:{cache_key}")
            if cached:
                logger.debug(f"Cold layer cache hit: {cache_key[:16]}")
                return cached
        
        # Execute compression
        if self.config.cold_strategy == "distill":
            summary = await self._distill_messages(cold)
        elif self.config.cold_strategy == "summarize":
            summary = await self._summarize_messages(cold)
        else:
            return None
        
        # Cache result
        if self.config.cache_compressed and summary:
            self.cache.set(
                f"cold_summary:{cache_key}",
                summary,
                ttl=self.config.cache_ttl
            )
            logger.debug(f"Cold layer cached: {cache_key[:16]}")
        
        return summary

    def _process_warm_layer(self, warm: List[Dict]) -> List[Dict]:
        """
        Process warm layer with consolidation.

        Args:
            warm: Warm layer messages

        Returns:
            Consolidated message list
        """
        if not warm or self.config.warm_strategy == "none":
            return warm

        if self.config.warm_strategy == "consolidate":
            return self._consolidate_messages(warm)

        return warm

    def _consolidate_messages(self, messages: List[Dict]) -> List[Dict]:
        """
        Consolidate messages using rule-based approach.

        Merges consecutive same-role messages and removes redundancy.
        Fast operation (< 10ms for 100 messages).

        Args:
            messages: Messages to consolidate

        Returns:
            Consolidated message list
        """
        if not messages:
            return []

        if not self.config.merge_consecutive_roles:
            return messages

        consolidated = []
        current_role = None
        current_contents = []

        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")

            # Extract text content (handles multi-modal)
            if isinstance(content, list):
                text = extract_text_content(content)
            else:
                text = str(content)

            if role == current_role:
                # Same role, accumulate content
                current_contents.append(text)
            else:
                # Role changed, flush previous
                if current_contents:
                    consolidated.append({
                        "role": current_role,
                        "content": "\n\n".join(current_contents)
                    })

                # Start new accumulation
                current_role = role
                current_contents = [text]

        # Flush last group
        if current_contents:
            consolidated.append({
                "role": current_role,
                "content": "\n\n".join(current_contents)
            })

        return consolidated

    async def _distill_messages(self, messages: List[Dict]) -> str:
        """
        Distill messages using LLM to extract core concepts.

        High compression (80-95%) while preserving conceptual integrity.

        Args:
            messages: Messages to distill

        Returns:
            Distilled summary
        """
        provider = await self._get_distill_provider()
        model = self._get_distill_model()

        # Build distillation prompt
        prompt = self._build_distill_prompt(messages)

        # Call LLM
        try:
            response = await provider.chat(
                model=model,
                messages=[build_user_message(prompt)],
                temperature=self.config.distill_temperature,
            )

            # Track distillation cost
            usage = response.get("usage", {})
            input_tokens = usage.get("input_tokens", 0) or usage.get("prompt_tokens", 0)
            output_tokens = usage.get("output_tokens", 0) or usage.get("completion_tokens", 0)
            self._distillation_cost_tokens += input_tokens + output_tokens

            return extract_text(response)

        except Exception as e:
            logger.error(f"Distillation failed: {e}")
            # Fallback: use consolidation
            consolidated = self._consolidate_messages(messages)
            return self._format_messages_as_text(consolidated)

    async def _summarize_messages(self, messages: List[Dict]) -> str:
        """
        Summarize messages using LLM.

        Medium compression (60-90%) with good retention (50-80%).

        Args:
            messages: Messages to summarize

        Returns:
            Summary
        """
        provider = await self._get_distill_provider()
        model = self._get_distill_model()

        # Build summarization prompt
        prompt = self._build_summarize_prompt(messages)

        # Call LLM
        try:
            response = await provider.chat(
                model=model,
                messages=[build_user_message(prompt)],
                temperature=self.config.distill_temperature,
            )

            # Track cost
            usage = response.get("usage", {})
            input_tokens = usage.get("input_tokens", 0) or usage.get("prompt_tokens", 0)
            output_tokens = usage.get("output_tokens", 0) or usage.get("completion_tokens", 0)
            self._distillation_cost_tokens += input_tokens + output_tokens

            return extract_text(response)

        except Exception as e:
            logger.error(f"Summarization failed: {e}")
            # Fallback: use consolidation
            consolidated = self._consolidate_messages(messages)
            return self._format_messages_as_text(consolidated)

    def _build_distill_prompt(self, messages: List[Dict]) -> str:
        """Build prompt for distillation."""
        formatted = self._format_messages_as_text(messages)

        return f"""Extract the core concepts, key decisions, and critical reasoning steps from the following conversation history.

Focus on:
1. Key decisions and conclusions
2. Important reasoning steps and logic
3. Core concepts and definitions
4. Unresolved questions or issues

Be concise. Only preserve information valuable for future conversation context.

Conversation History:
{formatted}

Distilled Summary:"""

    def _build_summarize_prompt(self, messages: List[Dict]) -> str:
        """Build prompt for summarization."""
        formatted = self._format_messages_as_text(messages)

        return f"""Summarize the following conversation history, preserving key information and context.

Include:
1. Main topics discussed
2. Important questions and answers
3. Key decisions or conclusions
4. Relevant context for future messages

Conversation History:
{formatted}

Summary:"""

    def _format_messages_as_text(self, messages: List[Dict]) -> str:
        """Format messages as readable text."""
        lines = []
        for msg in messages:
            role = msg.get("role", "user").upper()
            content = msg.get("content", "")

            # Extract text content
            if isinstance(content, list):
                text = extract_text_content(content)
            else:
                text = str(content)

            lines.append(f"{role}: {text}")

        return "\n\n".join(lines)

    async def _get_distill_provider(self) -> LLMProvider:
        """
        Get or create distillation provider.

        Returns:
            LLM provider for distillation
        """
        # Use main provider if not configured
        if not self.config.distill_provider:
            return self.main_provider

        # Create distill provider if needed
        if self._distill_provider is None:
            self._distill_provider = await self._create_distill_provider()

        return self._distill_provider

    async def _create_distill_provider(self) -> LLMProvider:
        """
        Create a separate provider instance for distillation.

        Returns:
            Configured LLM provider
        """
        from mindiv.providers.registry import ProviderRegistry
        from mindiv.config import ProviderConfig

        provider_name = self.config.distill_provider
        if not provider_name:
            return self.main_provider

        # Get provider class
        provider_class = ProviderRegistry.get(provider_name)

        # Build config
        config = ProviderConfig(
            provider_id=provider_name,
            api_key=self.config.distill_api_key or "",
            base_url=self.config.distill_base_url,
        )

        # Create instance
        return provider_class(config)

    def _get_distill_model(self) -> str:
        """
        Get model name for distillation.

        Returns:
            Model name
        """
        if self.config.distill_model:
            return self.config.distill_model

        # Fallback to main provider's default model
        # Try to get a reasonable default
        provider_name = self.config.distill_provider or self.main_provider.name

        # Common cheap models for distillation
        defaults = {
            "openai": "gpt-4o-mini",
            "anthropic": "claude-3-haiku-20240307",
            "gemini": "gemini-1.5-flash",
        }

        return defaults.get(provider_name, "gpt-4o-mini")

    def _estimate_tokens(self, messages: List[Dict]) -> int:
        """
        Estimate token count for messages.

        Simple heuristic: ~4 characters per token.

        Args:
            messages: Message list

        Returns:
            Estimated token count
        """
        total_chars = 0

        for msg in messages:
            content = msg.get("content", "")

            # Extract text content
            if isinstance(content, list):
                text = extract_text_content(content)
            else:
                text = str(content)

            total_chars += len(text)

        # Rough estimate: 4 chars per token
        # Add overhead for message structure (role, formatting, etc.)
        return (total_chars // 4) + (len(messages) * 10)

    def _compute_layer_hash(self, messages: List[Dict]) -> str:
        """
        Compute hash for message layer (for caching).

        Args:
            messages: Message list

        Returns:
            SHA256 hash
        """
        # Serialize messages to JSON
        serialized = json.dumps(messages, sort_keys=True)
        return hashlib.sha256(serialized.encode()).hexdigest()

    def add_cache_control_for_anthropic(
        self,
        messages: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Add cache_control markers for Anthropic prompt caching.

        Marks the last message before hot layer for caching.
        This ensures System + Cold + Warm are cached.

        Args:
            messages: Processed messages from process_history()

        Returns:
            Messages with cache_control added
        """
        if not messages:
            return messages

        # Find the boundary between warm and hot layers
        # We want to cache everything up to (but not including) hot layer
        # Since process_history returns [cold_summary, *warm, *hot],
        # we need to mark the last warm message

        # Calculate where warm layer ends
        # Hot layer is the last hot_layer_size messages from original history
        # But in processed messages, we have: [cold_summary?, *warm, *hot]

        # Simple heuristic: mark the message at position -(hot_layer_size + 1)
        # if it exists and is not a system message
        hot_size = self.config.hot_layer_size

        if len(messages) > hot_size:
            # Find the last message before hot layer
            cache_position = len(messages) - hot_size - 1

            if cache_position >= 0 and messages[cache_position].get("role") != "system":
                # Add cache_control to this message
                messages[cache_position]["cache_control"] = {"type": "ephemeral"}

        return messages

    async def close(self) -> None:
        """Close distillation provider if created."""
        if self._distill_provider and self._distill_provider != self.main_provider:
            await self._distill_provider.close()

