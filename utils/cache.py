"""
Prefix caching for prompt reuse.
Supports both provider-side caching (OpenAI responses) and local disk caching.
"""
import hashlib
import json
from typing import Any, Optional, Dict
from pathlib import Path
import diskcache


def _normalize_for_cache_key(obj: Any) -> Any:
    """
    Normalize complex objects for cache key serialization.

    Handles multi-modal content (images, tool calls), nested structures,
    and base64-encoded images by hashing them instead of including full content.
    This ensures that complex objects like images and tool calls can be safely
    serialized to JSON for cache key generation.

    Args:
        obj: Object to normalize (can be dict, list, or primitive type)

    Returns:
        Normalized object that is JSON-serializable

    Examples:
        >>> _normalize_for_cache_key("simple string")
        "simple string"

        >>> _normalize_for_cache_key({"type": "text", "text": "hello"})
        {"type": "text", "text": "hello"}

        >>> _normalize_for_cache_key({"image_url": "data:image/png;base64,..."})
        {"image_url": "image_hash:a1b2c3d4e5f6..."}
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
    # This ensures we don't fail on unexpected types while maintaining determinism
    return str(obj)


class PrefixCache:
    """
    Manages prefix caching for prompts and responses.
    
    Supports two caching strategies:
    1. Provider-side caching (OpenAI responses with previous_response_id)
    2. Local disk caching (for all providers)
    """
    
    def __init__(
        self,
        cache_dir: Optional[Path] = None,
        ttl: int = 86400,  # 24 hours
        enabled: bool = True,
    ):
        """
        Initialize prefix cache.
        
        Args:
            cache_dir: Directory for disk cache (defaults to ~/.mindiv/cache)
            ttl: Time-to-live for cache entries in seconds
            enabled: Whether caching is enabled
        """
        self.enabled = enabled
        self.ttl = ttl
        
        if cache_dir is None:
            cache_dir = Path.home() / ".mindiv" / "cache"
        
        cache_dir.mkdir(parents=True, exist_ok=True)
        self._disk_cache = diskcache.Cache(str(cache_dir))
    
    def compute_key(
        self,
        provider: str,
        model: str,
        system: Optional[str] = None,
        knowledge: Optional[str] = None,
        history: Optional[list] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Compute cache key from prompt components.

        Args:
            provider: Provider name
            model: Model name
            system: System prompt
            knowledge: Knowledge context
            history: Conversation history (may contain multi-modal content)
            params: Additional parameters (temperature, etc.)

        Returns:
            Cache key (hex digest)

        Raises:
            TypeError: If components cannot be serialized to JSON after normalization
        """
        components = {
            "provider": provider,
            "model": model,
            "system": system or "",
            "knowledge": knowledge or "",
            "history": history or [],
            "params": params or {},
        }

        # Normalize complex objects (images, tool calls, etc.) before serialization
        normalized_components = _normalize_for_cache_key(components)

        # Serialize to JSON and hash
        # If this fails, it indicates an unexpected object type that needs handling
        try:
            serialized = json.dumps(normalized_components, sort_keys=True)
        except (TypeError, ValueError) as e:
            raise TypeError(
                f"Failed to serialize cache key components after normalization. "
                f"This indicates an unexpected object type in the input. "
                f"Error: {e}"
            ) from e

        return hashlib.sha256(serialized.encode()).hexdigest()

    def key(
        self,
        system: Optional[str] = None,
        knowledge: Optional[str] = None,
        history: Optional[list] = None,
    ) -> str:
        """
        Simplified key computation for common use case.

        Args:
            system: System prompt
            knowledge: Knowledge context
            history: Conversation history (may contain multi-modal content)

        Returns:
            Cache key (hex digest)

        Raises:
            TypeError: If components cannot be serialized to JSON after normalization
        """
        components = {
            "system": system or "",
            "knowledge": knowledge or "",
            "history": history or [],
        }

        # Normalize complex objects (images, tool calls, etc.) before serialization
        normalized_components = _normalize_for_cache_key(components)

        # Serialize to JSON and hash
        try:
            serialized = json.dumps(normalized_components, sort_keys=True)
        except (TypeError, ValueError) as e:
            raise TypeError(
                f"Failed to serialize cache key components after normalization. "
                f"This indicates an unexpected object type in the input. "
                f"Error: {e}"
            ) from e

        return hashlib.sha256(serialized.encode()).hexdigest()
    
    def get(self, key: str) -> Optional[Any]:
        """
        Get cached value by key.
        
        Args:
            key: Cache key
        
        Returns:
            Cached value or None if not found/expired
        """
        if not self.enabled:
            return None
        
        return self._disk_cache.get(key)
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """
        Set cached value.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Optional TTL override (uses default if None)
        """
        if not self.enabled:
            return
        
        self._disk_cache.set(key, value, expire=ttl or self.ttl)
    
    def get_response_id(self, prefix_key: str) -> Optional[str]:
        """
        Get cached response ID for provider-side caching (OpenAI).

        Response IDs are persisted to disk cache to survive service restarts.

        Args:
            prefix_key: Prefix cache key

        Returns:
            Response ID or None if not found/expired
        """
        if not self.enabled:
            return None

        # Store response IDs with a prefix to avoid key collisions
        cache_key = f"response_id:{prefix_key}"
        return self._disk_cache.get(cache_key)
    
    def set_response_id(self, prefix_key: str, response_id: str) -> None:
        """
        Store response ID for provider-side caching.

        Response IDs are persisted to disk cache to survive service restarts.

        Args:
            prefix_key: Prefix cache key
            response_id: Response ID from provider
        """
        if not self.enabled:
            return

        # Store response IDs with a prefix to avoid key collisions
        cache_key = f"response_id:{prefix_key}"
        self._disk_cache.set(cache_key, response_id, expire=self.ttl)
    
    def clear(self) -> None:
        """Clear all cached data including response IDs."""
        self._disk_cache.clear()
    
    def close(self) -> None:
        """Close the cache."""
        self._disk_cache.close()

