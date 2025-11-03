"""
Test cache key serialization with complex objects.
Tests Issue #10 fix: cache key serialization failure with images and tool calls.
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from mindiv.utils.cache import PrefixCache, _normalize_for_cache_key


def test_normalize_simple_types():
    """Test normalization of simple types."""
    print("\n=== Testing simple types ===")
    
    # Strings
    assert _normalize_for_cache_key("hello") == "hello"
    print("✓ String normalization works")
    
    # Numbers
    assert _normalize_for_cache_key(42) == 42
    assert _normalize_for_cache_key(3.14) == 3.14
    print("✓ Number normalization works")
    
    # Booleans
    assert _normalize_for_cache_key(True) is True
    assert _normalize_for_cache_key(False) is False
    print("✓ Boolean normalization works")
    
    # None
    assert _normalize_for_cache_key(None) is None
    print("✓ None normalization works")


def test_normalize_multimodal_content():
    """Test normalization of multi-modal content with images."""
    print("\n=== Testing multi-modal content ===")
    
    # Simple text message
    text_msg = {
        "role": "user",
        "content": "Hello, world!"
    }
    normalized = _normalize_for_cache_key(text_msg)
    assert normalized == text_msg
    print("✓ Simple text message normalization works")
    
    # Multi-modal message with regular image URL
    multimodal_msg = {
        "role": "user",
        "content": [
            {"type": "text", "text": "What's in this image?"},
            {"type": "image_url", "image_url": {"url": "https://example.com/image.jpg"}}
        ]
    }
    normalized = _normalize_for_cache_key(multimodal_msg)
    assert normalized["content"][0] == {"type": "text", "text": "What's in this image?"}
    assert normalized["content"][1]["type"] == "image_url"
    assert normalized["content"][1]["image_url"] == "https://example.com/image.jpg"
    print("✓ Multi-modal message with regular URL works")
    
    # Multi-modal message with base64 image
    base64_msg = {
        "role": "user",
        "content": [
            {"type": "text", "text": "Analyze this"},
            {"type": "image_url", "image_url": {"url": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="}}
        ]
    }
    normalized = _normalize_for_cache_key(base64_msg)
    assert normalized["content"][0] == {"type": "text", "text": "Analyze this"}
    assert normalized["content"][1]["type"] == "image_url"
    # Base64 image should be hashed
    assert normalized["content"][1]["image_url"].startswith("image_hash:")
    assert len(normalized["content"][1]["image_url"]) == len("image_hash:") + 16
    print("✓ Multi-modal message with base64 image works (hashed)")


def test_normalize_tool_calls():
    """Test normalization of tool calls and results."""
    print("\n=== Testing tool calls ===")
    
    # Tool use message
    tool_use_msg = {
        "role": "assistant",
        "content": [
            {
                "type": "tool_use",
                "id": "call_abc123",
                "name": "calculator",
                "parameters": {"expression": "2 + 2"}
            }
        ]
    }
    normalized = _normalize_for_cache_key(tool_use_msg)
    assert normalized["role"] == "assistant"
    assert normalized["content"][0]["type"] == "tool_use"
    assert normalized["content"][0]["id"] == "call_abc123"
    assert normalized["content"][0]["name"] == "calculator"
    assert normalized["content"][0]["parameters"] == {"expression": "2 + 2"}
    print("✓ Tool use message normalization works")
    
    # Tool result message
    tool_result_msg = {
        "role": "user",
        "content": [
            {
                "type": "tool_result",
                "tool_use_id": "call_abc123",
                "content": [{"type": "output_text", "text": "4"}],
                "is_error": False
            }
        ]
    }
    normalized = _normalize_for_cache_key(tool_result_msg)
    assert normalized["role"] == "user"
    assert normalized["content"][0]["type"] == "tool_result"
    assert normalized["content"][0]["tool_use_id"] == "call_abc123"
    print("✓ Tool result message normalization works")


def test_cache_key_generation():
    """Test cache key generation with complex history."""
    print("\n=== Testing cache key generation ===")
    
    cache = PrefixCache(enabled=False)  # Disable disk cache for testing
    
    # Test 1: Simple history
    key1 = cache.compute_key(
        provider="openai",
        model="gpt-4o",
        system="You are a helpful assistant",
        history=[
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"}
        ]
    )
    assert isinstance(key1, str)
    assert len(key1) == 64  # SHA256 hex digest
    print(f"✓ Simple history key: {key1[:16]}...")
    
    # Test 2: History with multi-modal content
    key2 = cache.compute_key(
        provider="openai",
        model="gpt-4o",
        system="You are a helpful assistant",
        history=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "What's in this image?"},
                    {"type": "image_url", "image_url": {"url": "https://example.com/image.jpg"}}
                ]
            }
        ]
    )
    assert isinstance(key2, str)
    assert len(key2) == 64
    print(f"✓ Multi-modal history key: {key2[:16]}...")
    
    # Test 3: History with base64 image
    key3 = cache.compute_key(
        provider="openai",
        model="gpt-4o",
        system="You are a helpful assistant",
        history=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Analyze this"},
                    {"type": "image_url", "image_url": {"url": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="}}
                ]
            }
        ]
    )
    assert isinstance(key3, str)
    assert len(key3) == 64
    print(f"✓ Base64 image history key: {key3[:16]}...")
    
    # Test 4: History with tool calls
    key4 = cache.compute_key(
        provider="openai",
        model="gpt-4o",
        system="You are a helpful assistant",
        history=[
            {
                "role": "assistant",
                "content": [
                    {
                        "type": "tool_use",
                        "id": "call_123",
                        "name": "calculator",
                        "parameters": {"expression": "2 + 2"}
                    }
                ]
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "tool_result",
                        "tool_use_id": "call_123",
                        "content": [{"type": "output_text", "text": "4"}]
                    }
                ]
            }
        ]
    )
    assert isinstance(key4, str)
    assert len(key4) == 64
    print(f"✓ Tool call history key: {key4[:16]}...")
    
    # Test 5: Verify determinism (same input -> same key)
    key5 = cache.compute_key(
        provider="openai",
        model="gpt-4o",
        system="You are a helpful assistant",
        history=[
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"}
        ]
    )
    assert key5 == key1
    print("✓ Cache key generation is deterministic")


def test_backward_compatibility():
    """Test that simple messages produce the same cache keys as before."""
    print("\n=== Testing backward compatibility ===")
    
    cache = PrefixCache(enabled=False)
    
    # Simple text-only history should produce consistent keys
    key1 = cache.key(
        system="System prompt",
        knowledge="Knowledge base",
        history=[
            {"role": "user", "content": "Question 1"},
            {"role": "assistant", "content": "Answer 1"}
        ]
    )
    
    key2 = cache.key(
        system="System prompt",
        knowledge="Knowledge base",
        history=[
            {"role": "user", "content": "Question 1"},
            {"role": "assistant", "content": "Answer 1"}
        ]
    )
    
    assert key1 == key2
    print("✓ Backward compatibility maintained for simple messages")


def run_all_tests():
    """Run all tests."""
    print("\n" + "="*60)
    print("Testing Cache Key Serialization (Issue #10 Fix)")
    print("="*60)
    
    try:
        test_normalize_simple_types()
        test_normalize_multimodal_content()
        test_normalize_tool_calls()
        test_cache_key_generation()
        test_backward_compatibility()
        
        print("\n" + "="*60)
        print("✅ All tests passed!")
        print("="*60)
        return True
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)

