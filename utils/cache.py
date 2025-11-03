"""
Prefix caching for prompt reuse.
Supports both provider-side caching (OpenAI responses) and local disk caching.
"""
import hashlib
import json
from typing import Any, Optional, Dict
from pathlib import Path
import diskcache


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
            history: Conversation history
            params: Additional parameters (temperature, etc.)

        Returns:
            Cache key (hex digest)
        """
        components = {
            "provider": provider,
            "model": model,
            "system": system or "",
            "knowledge": knowledge or "",
            "history": history or [],
            "params": params or {},
        }

        # Serialize to JSON and hash
        serialized = json.dumps(components, sort_keys=True)
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
            history: Conversation history

        Returns:
            Cache key (hex digest)
        """
        components = {
            "system": system or "",
            "knowledge": knowledge or "",
            "history": history or [],
        }

        serialized = json.dumps(components, sort_keys=True)
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

