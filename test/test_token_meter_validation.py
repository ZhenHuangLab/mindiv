#!/usr/bin/env python3
"""
Test for TokenMeter validation logic (Issue #8 fix).
Verifies that token counting assumptions are validated correctly.
"""
import sys
from pathlib import Path
import logging

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from mindiv.utils.token_meter import TokenMeter, UsageStats


def test_usage_stats_validation():
    """Test UsageStats validation method."""
    print("Testing UsageStats validation...")
    
    # Configure logging to capture warnings
    logging.basicConfig(level=logging.WARNING, format='%(levelname)s: %(message)s')
    
    # Test 1: Valid token counts
    print("\n1. Testing valid token counts...")
    stats = UsageStats(
        input_tokens=1000,
        output_tokens=500,
        cached_tokens=200,  # <= input_tokens ✓
        reasoning_tokens=100,  # <= output_tokens ✓
    )
    stats.validate()
    print("✓ Valid token counts passed validation")
    
    # Test 2: Invalid cached_tokens
    print("\n2. Testing invalid cached_tokens (should log warning)...")
    stats_invalid_cached = UsageStats(
        input_tokens=100,
        output_tokens=50,
        cached_tokens=150,  # > input_tokens ✗
        reasoning_tokens=10,
    )
    stats_invalid_cached.validate()
    print("✓ Invalid cached_tokens triggered warning")
    
    # Test 3: Invalid reasoning_tokens
    print("\n3. Testing invalid reasoning_tokens (should log warning)...")
    stats_invalid_reasoning = UsageStats(
        input_tokens=100,
        output_tokens=50,
        cached_tokens=20,
        reasoning_tokens=100,  # > output_tokens ✗
    )
    stats_invalid_reasoning.validate()
    print("✓ Invalid reasoning_tokens triggered warning")
    
    # Test 4: Both invalid
    print("\n4. Testing both invalid (should log two warnings)...")
    stats_both_invalid = UsageStats(
        input_tokens=100,
        output_tokens=50,
        cached_tokens=200,  # > input_tokens ✗
        reasoning_tokens=100,  # > output_tokens ✗
    )
    stats_both_invalid.validate()
    print("✓ Both invalid triggered two warnings")
    
    return True


def test_token_meter_cost_calculation():
    """Test TokenMeter cost calculation with validation."""
    print("\n\nTesting TokenMeter cost calculation with validation...")
    
    # Create pricing data
    pricing = {
        "openai": {
            "gpt-4o": {
                "prompt": 2.50,
                "completion": 10.00,
                "reasoning": 60.00,
                "cached_prompt": 1.25,
            }
        }
    }
    
    meter = TokenMeter(pricing=pricing)
    
    # Test 1: Record valid usage
    print("\n1. Recording valid usage...")
    meter.record(
        provider="openai",
        model="gpt-4o",
        usage={
            "input_tokens": 1000,
            "output_tokens": 500,
            "input_tokens_details": {"cached_tokens": 200},
            "output_tokens_details": {"reasoning_tokens": 100},
        }
    )
    
    # Calculate cost (should validate internally)
    cost = meter.estimate_cost(provider="openai", model="gpt-4o")
    
    # Expected cost calculation:
    # Uncached input: (1000 - 200) * 2.50 / 1M = 800 * 2.50 / 1M = 0.002
    # Cached input: 200 * 1.25 / 1M = 0.00025
    # Regular output: (500 - 100) * 10.00 / 1M = 400 * 10.00 / 1M = 0.004
    # Reasoning output: 100 * 60.00 / 1M = 0.006
    # Total: 0.002 + 0.00025 + 0.004 + 0.006 = 0.01225
    expected_cost = 0.01225
    
    print(f"✓ Calculated cost: ${cost:.6f}")
    print(f"  Expected cost: ${expected_cost:.6f}")
    
    if abs(cost - expected_cost) < 0.000001:
        print("✓ Cost calculation is correct")
    else:
        print(f"✗ Cost mismatch: got ${cost:.6f}, expected ${expected_cost:.6f}")
        return False
    
    # Test 2: Get summary
    print("\n2. Getting summary...")
    summary = meter.summary()
    print(f"✓ Total usage: {summary['total_usage']}")
    print(f"✓ Total cost: ${summary['total_cost_usd']:.6f}")
    
    return True


def test_edge_cases():
    """Test edge cases."""
    print("\n\nTesting edge cases...")
    
    # Test 1: Zero tokens
    print("\n1. Testing zero tokens...")
    stats = UsageStats()
    stats.validate()
    print("✓ Zero tokens passed validation")
    
    # Test 2: Equal tokens (cached = input, reasoning = output)
    print("\n2. Testing equal tokens...")
    stats_equal = UsageStats(
        input_tokens=100,
        output_tokens=50,
        cached_tokens=100,  # = input_tokens (edge case)
        reasoning_tokens=50,  # = output_tokens (edge case)
    )
    stats_equal.validate()
    print("✓ Equal tokens passed validation")
    
    return True


def main():
    """Run all tests."""
    print("=" * 60)
    print("TokenMeter Validation Tests (Issue #8 Fix)")
    print("=" * 60)
    
    tests = [
        ("UsageStats Validation", test_usage_stats_validation),
        ("TokenMeter Cost Calculation", test_token_meter_cost_calculation),
        ("Edge Cases", test_edge_cases),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n✗ Test '{name}' crashed: {e}")
            import traceback
            traceback.print_exc()
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

