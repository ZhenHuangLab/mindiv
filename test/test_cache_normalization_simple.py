"""
Simple test for cache key normalization function.
Tests Issue #10 fix without requiring external dependencies.
"""
import hashlib
import json
from typing import Any


def _normalize_for_cache_key(obj: Any) -> Any:
    """
    Normalize complex objects for cache key serialization.
    (Copy of the function from mindiv/utils/cache.py for testing)
    """
    # Base types - return as-is
    if obj is None or isinstance(obj, (str, int, float, bool)):
        return obj
    
    # Dictionary - recursively normalize
    if isinstance(obj, dict):
        normalized = {}
        for k, v in obj.items():
            # Special handling for image URLs (base64 or regular)
            if k in ("image_url", "url") and isinstance(v, (str, dict)):
                if isinstance(v, dict):
                    url = v.get("url", "")
                else:
                    url = v
                
                # Hash base64 images to reduce size while maintaining uniqueness
                if isinstance(url, str) and url.startswith("data:image"):
                    # Use first 16 chars of hash for readability
                    normalized[k] = f"image_hash:{hashlib.sha256(url.encode()).hexdigest()[:16]}"
                else:
                    normalized[k] = url
            else:
                normalized[k] = _normalize_for_cache_key(v)
        return normalized
    
    # List/tuple - recursively normalize
    if isinstance(obj, (list, tuple)):
        return [_normalize_for_cache_key(item) for item in obj]
    
    # Fallback for unknown types - convert to string representation
    return str(obj)


def test_simple_types():
    """Test normalization of simple types."""
    print("Testing simple types...")
    assert _normalize_for_cache_key("hello") == "hello"
    assert _normalize_for_cache_key(42) == 42
    assert _normalize_for_cache_key(3.14) == 3.14
    assert _normalize_for_cache_key(True) is True
    assert _normalize_for_cache_key(None) is None
    print("✓ Simple types work")


def test_multimodal_content():
    """Test normalization of multi-modal content."""
    print("\nTesting multi-modal content...")
    
    # Regular image URL
    msg1 = {
        "role": "user",
        "content": [
            {"type": "text", "text": "What's in this image?"},
            {"type": "image_url", "image_url": {"url": "https://example.com/image.jpg"}}
        ]
    }
    normalized1 = _normalize_for_cache_key(msg1)
    assert normalized1["content"][1]["image_url"] == "https://example.com/image.jpg"
    print("✓ Regular image URL preserved")
    
    # Base64 image
    base64_url = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
    msg2 = {
        "role": "user",
        "content": [
            {"type": "image_url", "image_url": {"url": base64_url}}
        ]
    }
    normalized2 = _normalize_for_cache_key(msg2)
    hashed_url = normalized2["content"][0]["image_url"]
    assert hashed_url.startswith("image_hash:")
    assert len(hashed_url) == len("image_hash:") + 16
    print(f"✓ Base64 image hashed: {hashed_url}")


def test_tool_calls():
    """Test normalization of tool calls."""
    print("\nTesting tool calls...")
    
    tool_msg = {
        "role": "assistant",
        "content": [
            {
                "type": "tool_use",
                "id": "call_abc123",
                "name": "calculator",
                "parameters": {"expression": "2 + 2", "nested": {"value": 42}}
            }
        ]
    }
    normalized = _normalize_for_cache_key(tool_msg)
    assert normalized["content"][0]["type"] == "tool_use"
    assert normalized["content"][0]["parameters"]["expression"] == "2 + 2"
    assert normalized["content"][0]["parameters"]["nested"]["value"] == 42
    print("✓ Tool calls work")


def test_json_serialization():
    """Test that normalized objects can be JSON serialized."""
    print("\nTesting JSON serialization...")
    
    # Complex history with images and tool calls
    history = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "Analyze this image"},
                {"type": "image_url", "image_url": {"url": "data:image/png;base64,ABC123..."}}
            ]
        },
        {
            "role": "assistant",
            "content": [
                {
                    "type": "tool_use",
                    "id": "call_1",
                    "name": "image_analyzer",
                    "parameters": {"mode": "detailed"}
                }
            ]
        },
        {
            "role": "user",
            "content": [
                {
                    "type": "tool_result",
                    "tool_use_id": "call_1",
                    "content": [{"type": "output_text", "text": "Analysis complete"}]
                }
            ]
        }
    ]
    
    # Normalize
    normalized = _normalize_for_cache_key(history)
    
    # Try to serialize
    try:
        serialized = json.dumps(normalized, sort_keys=True)
        print(f"✓ JSON serialization successful ({len(serialized)} bytes)")
        
        # Verify it can be hashed
        hash_value = hashlib.sha256(serialized.encode()).hexdigest()
        print(f"✓ Hash generated: {hash_value[:16]}...")
        
    except (TypeError, ValueError) as e:
        print(f"✗ JSON serialization failed: {e}")
        raise


def test_determinism():
    """Test that normalization is deterministic."""
    print("\nTesting determinism...")
    
    obj = {
        "history": [
            {"role": "user", "content": "Hello"},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Image"},
                    {"type": "image_url", "image_url": {"url": "data:image/png;base64,XYZ"}}
                ]
            }
        ]
    }
    
    # Normalize twice
    norm1 = _normalize_for_cache_key(obj)
    norm2 = _normalize_for_cache_key(obj)
    
    # Serialize and hash
    json1 = json.dumps(norm1, sort_keys=True)
    json2 = json.dumps(norm2, sort_keys=True)
    hash1 = hashlib.sha256(json1.encode()).hexdigest()
    hash2 = hashlib.sha256(json2.encode()).hexdigest()
    
    assert hash1 == hash2
    print(f"✓ Deterministic: {hash1[:16]}...")


def run_all_tests():
    """Run all tests."""
    print("="*60)
    print("Testing Cache Key Normalization (Issue #10 Fix)")
    print("="*60)
    
    try:
        test_simple_types()
        test_multimodal_content()
        test_tool_calls()
        test_json_serialization()
        test_determinism()
        
        print("\n" + "="*60)
        print("✅ All tests passed!")
        print("="*60)
        return True
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    import sys
    success = run_all_tests()
    sys.exit(0 if success else 1)

