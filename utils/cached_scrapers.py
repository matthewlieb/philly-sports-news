"""
Cached wrapper functions for scrapers to reduce redundant requests.

This module provides cached versions of scraping functions that store
results in memory for a specified duration, reducing load on source websites
and improving response times.
"""

from functools import wraps
from flask_caching import Cache
from typing import Callable, Any
import hashlib
import json


def create_cache_key(func_name: str, *args, **kwargs) -> str:
    """
    Create a unique cache key from function name and arguments.
    
    Args:
        func_name: Name of the function
        *args: Positional arguments
        **kwargs: Keyword arguments
        
    Returns:
        Unique cache key string
    """
    # Create a hash of the arguments
    key_data = f"{func_name}:{json.dumps(args, sort_keys=True)}:{json.dumps(kwargs, sort_keys=True)}"
    key_hash = hashlib.md5(key_data.encode()).hexdigest()
    return f"scraper_{func_name}_{key_hash}"


def cached_scraper(cache: Cache, timeout: int = 3600):
    """
    Decorator to cache scraper function results.
    
    Args:
        cache: Flask-Caching Cache instance
        timeout: Cache timeout in seconds (default: 1 hour)
        
    Returns:
        Decorated function with caching
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Create cache key
            cache_key = create_cache_key(func.__name__, *args, **kwargs)
            
            # Try to get from cache
            cached_result = cache.get(cache_key)
            if cached_result is not None:
                print(f"✅ Cache hit for {func.__name__}")
                return cached_result
            
            # Cache miss - execute function
            print(f"⏳ Cache miss for {func.__name__}, fetching fresh data...")
            result = func(*args, **kwargs)
            
            # Store in cache
            cache.set(cache_key, result, timeout=timeout)
            print(f"💾 Cached result for {func.__name__} (expires in {timeout}s)")
            
            return result
        
        return wrapper
    return decorator


def clear_scraper_cache(cache: Cache, pattern: str = "scraper_*"):
    """
    Clear all scraper-related cache entries.
    
    Args:
        cache: Flask-Caching Cache instance
        pattern: Pattern to match cache keys (default: "scraper_*")
    """
    try:
        cache.clear()
        print(f"✅ Cleared all cache entries matching '{pattern}'")
    except Exception as e:
        print(f"⚠️  Error clearing cache: {e}")

