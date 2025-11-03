"""
Memory Folding Usage Examples

This file demonstrates how to use Memory Folding in different scenarios.
"""

from mindiv.utils.memory_folding import MemoryFoldingConfig
from mindiv.engine.deep_think import DeepThinkEngine
from mindiv.engine.ultra_think import UltraThinkEngine
from mindiv.providers.registry import ProviderRegistry
from mindiv.utils.token_meter import TokenMeter
from mindiv.utils.cache import PrefixCache


# ============================================================================
# Example 1: Basic Usage (Default Settings)
# ============================================================================

async def example_basic():
    """
    Enable Memory Folding with default settings.
    Uses main model for distillation.
    """
    # Create provider
    registry = ProviderRegistry()
    provider = registry.create_provider(
        provider_type="openai",
        api_key="sk-...",
        base_url="https://api.openai.com/v1",
    )
    
    # Enable Memory Folding with defaults
    memory_config = MemoryFoldingConfig(
        enabled=True,  # Enable Memory Folding
        # All other parameters use defaults:
        # - hot_layer_size=5
        # - warm_layer_size=10
        # - warm_strategy="consolidate"
        # - cold_strategy="distill"
        # - distill_provider=None (use main provider)
        # - distill_model=None (use main model)
    )
    
    # Create engine with Memory Folding
    engine = DeepThinkEngine(
        provider=provider,
        model="gpt-4o",
        problem_statement="Solve this complex problem...",
        conversation_history=[
            {"role": "user", "content": "Previous question 1"},
            {"role": "assistant", "content": "Previous answer 1"},
            # ... many more messages ...
        ],
        memory_folding_config=memory_config,
    )
    
    # Run - Memory Folding will automatically compress history
    result = await engine.run()
    
    # Check statistics
    stats = engine.meter.summary()
    print(f"Original tokens: {stats['total']['original_context_tokens']}")
    print(f"Compressed tokens: {stats['total']['compressed_context_tokens']}")
    print(f"Saved tokens: {stats['total']['saved_tokens']}")
    print(f"Net saved: {stats['total']['net_saved_tokens']}")


# ============================================================================
# Example 2: Use Cheaper Distillation Model
# ============================================================================

async def example_cheap_distill():
    """
    Use a cheaper model (gpt-4o-mini) for distillation to save costs.
    Main model is gpt-4o, distillation uses gpt-4o-mini.
    """
    registry = ProviderRegistry()
    provider = registry.create_provider(
        provider_type="openai",
        api_key="sk-...",
    )
    
    # Configure Memory Folding with cheaper distill model
    memory_config = MemoryFoldingConfig(
        enabled=True,
        distill_provider="openai",  # Same provider
        distill_model="gpt-4o-mini",  # Cheaper model for distillation
        distill_temperature=0.2,  # Lower temperature for more deterministic output
    )
    
    engine = DeepThinkEngine(
        provider=provider,
        model="gpt-4o",  # Main model
        problem_statement="Complex reasoning task...",
        conversation_history=[...],
        memory_folding_config=memory_config,
    )
    
    result = await engine.run()


# ============================================================================
# Example 3: Use Local/Custom Model for Distillation
# ============================================================================

async def example_local_distill():
    """
    Use a local model for distillation (e.g., Ollama, vLLM).
    Main model is cloud-based, distillation uses local model.
    """
    registry = ProviderRegistry()
    
    # Main provider (cloud)
    provider = registry.create_provider(
        provider_type="openai",
        api_key="sk-...",
        base_url="https://api.openai.com/v1",
    )
    
    # Configure Memory Folding with local distill model
    memory_config = MemoryFoldingConfig(
        enabled=True,
        distill_provider="openai",  # Use OpenAI-compatible API
        distill_model="qwen-plus",  # Local model name
        distill_base_url="http://localhost:8000/v1",  # Local endpoint
        distill_api_key="sk-local-key",  # Local API key
        distill_temperature=0.3,
    )
    
    engine = DeepThinkEngine(
        provider=provider,
        model="gpt-4o",  # Cloud model for main reasoning
        problem_statement="Problem...",
        conversation_history=[...],
        memory_folding_config=memory_config,
    )
    
    result = await engine.run()


# ============================================================================
# Example 4: Aggressive Compression
# ============================================================================

async def example_aggressive():
    """
    More aggressive compression for very long conversations.
    Smaller hot/warm layers, distillation for warm layer too.
    """
    registry = ProviderRegistry()
    provider = registry.create_provider(
        provider_type="anthropic",
        api_key="sk-ant-...",
    )
    
    # Aggressive compression settings
    memory_config = MemoryFoldingConfig(
        enabled=True,
        hot_layer_size=3,  # Keep only last 3 turns uncompressed
        warm_layer_size=7,  # Smaller warm layer
        warm_strategy="distill",  # Use distillation for warm layer (more compression)
        cold_strategy="distill",
        distill_model="claude-3-haiku-20240307",  # Fast, cheap model
        auto_compress_threshold=0.7,  # Trigger compression earlier (at 70%)
    )
    
    engine = DeepThinkEngine(
        provider=provider,
        model="claude-3-5-sonnet-20241022",
        problem_statement="Problem...",
        conversation_history=[...],  # Very long history
        memory_folding_config=memory_config,
    )
    
    result = await engine.run()


# ============================================================================
# Example 5: Conservative Compression
# ============================================================================

async def example_conservative():
    """
    Conservative compression for maximum information retention.
    Larger hot/warm layers, consolidation only (no distillation).
    """
    registry = ProviderRegistry()
    provider = registry.create_provider(
        provider_type="openai",
        api_key="sk-...",
    )
    
    # Conservative settings
    memory_config = MemoryFoldingConfig(
        enabled=True,
        hot_layer_size=10,  # Keep more turns uncompressed
        warm_layer_size=20,  # Larger warm layer
        warm_strategy="consolidate",  # Fast, rule-based (minimal compression)
        cold_strategy="summarize",  # Summarization instead of distillation
        auto_compress_threshold=0.9,  # Only compress when very close to limit
    )
    
    engine = DeepThinkEngine(
        provider=provider,
        model="gpt-4o",
        problem_statement="Problem...",
        conversation_history=[...],
        memory_folding_config=memory_config,
    )
    
    result = await engine.run()


# ============================================================================
# Example 6: UltraThink with Memory Folding
# ============================================================================

async def example_ultra_think():
    """
    Use Memory Folding with UltraThink (multi-agent).
    All child agents inherit the same Memory Folding config.
    """
    registry = ProviderRegistry()
    provider = registry.create_provider(
        provider_type="openai",
        api_key="sk-...",
    )
    
    # Memory Folding config (shared by all agents)
    memory_config = MemoryFoldingConfig(
        enabled=True,
        distill_model="gpt-4o-mini",
    )
    
    # Create UltraThink engine
    engine = UltraThinkEngine(
        provider=provider,
        model="gpt-4o",
        problem_statement="Complex multi-faceted problem...",
        conversation_history=[...],  # Long conversation history
        num_agents=3,  # 3 parallel agents
        memory_folding_config=memory_config,  # All agents use Memory Folding
    )
    
    result = await engine.run()
    
    # Each agent's statistics are tracked separately
    stats = engine.meter.summary()
    print(stats)


# ============================================================================
# Example 7: Disable Memory Folding (Default)
# ============================================================================

async def example_disabled():
    """
    Memory Folding is disabled by default.
    No need to pass config if you don't want to use it.
    """
    registry = ProviderRegistry()
    provider = registry.create_provider(
        provider_type="openai",
        api_key="sk-...",
    )
    
    # No memory_folding_config parameter = disabled
    engine = DeepThinkEngine(
        provider=provider,
        model="gpt-4o",
        problem_statement="Problem...",
        conversation_history=[...],
        # memory_folding_config not specified = disabled
    )
    
    result = await engine.run()


# ============================================================================
# Example 8: Custom Cache Settings
# ============================================================================

async def example_custom_cache():
    """
    Customize caching behavior for compressed results.
    """
    registry = ProviderRegistry()
    provider = registry.create_provider(
        provider_type="openai",
        api_key="sk-...",
    )
    
    memory_config = MemoryFoldingConfig(
        enabled=True,
        cache_compressed=True,  # Cache distillation results (default)
        cache_ttl_seconds=7200,  # Cache for 2 hours (default: 1 hour)
        max_distill_retries=3,  # Retry distillation up to 3 times on failure
    )
    
    engine = DeepThinkEngine(
        provider=provider,
        model="gpt-4o",
        problem_statement="Problem...",
        conversation_history=[...],
        memory_folding_config=memory_config,
    )
    
    result = await engine.run()


# ============================================================================
# Example 9: Monitoring Memory Folding Statistics
# ============================================================================

async def example_monitoring():
    """
    Monitor Memory Folding performance and statistics.
    """
    registry = ProviderRegistry()
    provider = registry.create_provider(
        provider_type="openai",
        api_key="sk-...",
    )
    
    # Create shared token meter for tracking
    meter = TokenMeter()
    
    memory_config = MemoryFoldingConfig(
        enabled=True,
        distill_model="gpt-4o-mini",
    )
    
    engine = DeepThinkEngine(
        provider=provider,
        model="gpt-4o",
        problem_statement="Problem...",
        conversation_history=[...],
        token_meter=meter,  # Shared meter
        memory_folding_config=memory_config,
    )
    
    result = await engine.run()
    
    # Get detailed statistics
    summary = meter.summary()
    
    # Total statistics
    total = summary["total"]
    print(f"Total input tokens: {total['input_tokens']}")
    print(f"Total output tokens: {total['output_tokens']}")
    print(f"Total cached tokens: {total['cached_tokens']}")
    
    # Memory Folding statistics
    if "original_context_tokens" in total:
        print(f"\nMemory Folding Statistics:")
        print(f"Original context: {total['original_context_tokens']} tokens")
        print(f"Compressed context: {total['compressed_context_tokens']} tokens")
        print(f"Distillation cost: {total['distillation_tokens']} tokens")
        print(f"Gross saved: {total['saved_tokens']} tokens")
        print(f"Net saved: {total['net_saved_tokens']} tokens")
        
        # Calculate compression ratio
        if total['original_context_tokens'] > 0:
            ratio = total['compressed_context_tokens'] / total['original_context_tokens']
            print(f"Compression ratio: {ratio:.2%}")
    
    # Per-provider statistics
    for provider_name, models in summary["by_provider"].items():
        print(f"\n{provider_name}:")
        for model_name, stats in models.items():
            print(f"  {model_name}: {stats}")

