#!/usr/bin/env python3
"""
Basic functionality test for mindiv.
Tests configuration loading, provider registration, and basic imports.
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def test_imports():
    """Test that all modules can be imported."""
    print("Testing imports...")
    
    try:
        from mindiv.config import Config, load_config, get_config, set_config
        print("✓ Config module imported")
    except Exception as e:
        print(f"✗ Failed to import config: {e}")
        return False
    
    try:
        from mindiv.providers.registry import ProviderRegistry, register_builtin_providers
        print("✓ Provider registry imported")
    except Exception as e:
        print(f"✗ Failed to import provider registry: {e}")
        return False
    
    try:
        from mindiv.providers.openai import OpenAIProvider
        from mindiv.providers.anthropic import AnthropicProvider
        from mindiv.providers.gemini import GeminiProvider
        print("✓ Provider adapters imported")
    except Exception as e:
        print(f"✗ Failed to import providers: {e}")
        return False
    
    try:
        from mindiv.engine.deep_think import DeepThinkEngine
        from mindiv.engine.ultra_think import UltraThinkEngine
        print("✓ Engines imported")
    except Exception as e:
        print(f"✗ Failed to import engines: {e}")
        return False
    
    try:
        from mindiv.utils.token_meter import TokenMeter
        from mindiv.utils.cache import PrefixCache
        from mindiv.utils.messages import normalize_messages, extract_text
        print("✓ Utilities imported")
    except Exception as e:
        print(f"✗ Failed to import utilities: {e}")
        return False
    
    return True


def test_config():
    """Test configuration loading."""
    print("\nTesting configuration...")
    
    try:
        from mindiv.config import Config, ProviderConfig, ModelConfig
        
        # Test creating empty config
        config = Config()
        print("✓ Created empty config")
        
        # Test creating provider config
        provider_config = ProviderConfig(
            provider_id="test",
            base_url="https://api.test.com",
            api_key="test-key",
        )
        print("✓ Created provider config")
        
        # Test creating model config
        model_config = ModelConfig(
            model_id="test-model",
            name="Test Model",
            provider="test",
            model="test-model-v1",
            level="deepthink",
        )
        print("✓ Created model config")
        
        return True
    except Exception as e:
        print(f"✗ Config test failed: {e}")
        return False


def test_providers():
    """Test provider registration."""
    print("\nTesting provider registration...")
    
    try:
        from mindiv.providers.registry import ProviderRegistry, register_builtin_providers
        
        # Register providers
        register_builtin_providers()
        print("✓ Registered built-in providers")
        
        # Check registered providers
        providers = ProviderRegistry.list_providers()
        print(f"✓ Registered providers: {providers}")
        
        if "openai" not in providers:
            print("✗ OpenAI provider not registered")
            return False
        
        if "anthropic" not in providers:
            print("✗ Anthropic provider not registered")
            return False
        
        if "gemini" not in providers:
            print("✗ Gemini provider not registered")
            return False
        
        return True
    except Exception as e:
        print(f"✗ Provider registration test failed: {e}")
        return False


def test_token_meter():
    """Test token metering."""
    print("\nTesting token meter...")
    
    try:
        from mindiv.utils.token_meter import TokenMeter, UsageStats
        
        # Create meter
        meter = TokenMeter()
        print("✓ Created token meter")
        
        # Record usage
        meter.record(
            provider="openai",
            model="gpt-4o",
            usage={
                "input_tokens": 100,
                "output_tokens": 50,
            },
        )
        print("✓ Recorded usage")
        
        # Get summary
        summary = meter.summary()
        print(f"✓ Got summary: {summary['total_usage']}")
        
        return True
    except Exception as e:
        print(f"✗ Token meter test failed: {e}")
        return False


def main():
    """Run all tests."""
    print("=" * 60)
    print("mindiv Basic Functionality Tests")
    print("=" * 60)
    
    tests = [
        ("Imports", test_imports),
        ("Configuration", test_config),
        ("Providers", test_providers),
        ("Token Meter", test_token_meter),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n✗ Test '{name}' crashed: {e}")
            results.append((name, False))
    
    print("\n" + "=" * 60)
    print("Test Results")
    print("=" * 60)
    
    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {name}")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    print(f"\nPassed: {passed}/{total}")
    
    if passed == total:
        print("\n✓ All tests passed!")
        return 0
    else:
        print(f"\n✗ {total - passed} test(s) failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())

