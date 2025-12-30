"""
Caching utility for scraped article data.

This module provides a simple in-memory cache to reduce redundant HTTP requests
and improve application performance. Cache entries expire after a specified time.
"""

from typing import Optional, Any, Dict, Tuple
import time
from datetime import datetime, timedelta


class ArticleCache:
    """
    Simple in-memory cache for article data with time-based expiration.
    
    This cache stores scraped article data to avoid redundant requests to news sources.
    Cache entries automatically expire after a specified duration (default: 1 hour).
    """
    
    def __init__(self, default_ttl_seconds: int = 3600):
        """
        Initialize the cache.
        
        Args:
            default_ttl_seconds: Default time-to-live for cache entries in seconds (default: 1 hour)
        """
        self._cache: Dict[str, Tuple[Any, float]] = {}
        self.default_ttl = default_ttl_seconds
    
    def get(self, key: str) -> Optional[Any]:
        """
        Retrieve a value from the cache.
        
        Args:
            key: Cache key to look up
            
        Returns:
            Cached value if found and not expired, None otherwise
        """
        if key not in self._cache:
            return None
        
        value, expiry_time = self._cache[key]
        
        # Check if entry has expired
        if time.time() > expiry_time:
            del self._cache[key]
            return None
        
        return value
    
    def set(self, key: str, value: Any, ttl_seconds: Optional[int] = None) -> None:
        """
        Store a value in the cache.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl_seconds: Time-to-live in seconds (uses default if None)
        """
        ttl = ttl_seconds if ttl_seconds is not None else self.default_ttl
        expiry_time = time.time() + ttl
        self._cache[key] = (value, expiry_time)
    
    def clear(self) -> None:
        """Clear all cache entries."""
        self._cache.clear()
    
    def remove(self, key: str) -> None:
        """
        Remove a specific cache entry.
        
        Args:
            key: Cache key to remove
        """
        if key in self._cache:
            del self._cache[key]
    
    def size(self) -> int:
        """
        Get the number of entries in the cache.
        
        Returns:
            Number of cache entries
        """
        # Clean up expired entries first
        current_time = time.time()
        expired_keys = [
            key for key, (_, expiry) in self._cache.items()
            if current_time > expiry
        ]
        for key in expired_keys:
            del self._cache[key]
        
        return len(self._cache)
    
    def __repr__(self) -> str:
        """String representation of the cache."""
        return f"ArticleCache(size={self.size()}, default_ttl={self.default_ttl}s)"


# Global cache instance
_global_cache: Optional[ArticleCache] = None


def get_cache() -> ArticleCache:
    """
    Get the global cache instance (singleton pattern).
    
    Returns:
        Global ArticleCache instance
    """
    global _global_cache
    if _global_cache is None:
        _global_cache = ArticleCache()
    return _global_cache

