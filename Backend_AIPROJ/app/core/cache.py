"""
In-memory LRU cache for RAG answers, embeddings, and ML predictions.
Provides production-grade caching with TTL and observability.
"""

import time
import hashlib
from typing import Any, Optional, Dict
from collections import OrderedDict
from app.core.logging import setup_logger

logger = setup_logger()

# Cache configuration
DEFAULT_CACHE_SIZE = 1000
DEFAULT_TTL_SECONDS = 3600  # 1 hour


class LRUCache:
    """
    Thread-safe LRU cache with TTL support.
    """
    
    def __init__(self, max_size: int = DEFAULT_CACHE_SIZE, ttl: int = DEFAULT_TTL_SECONDS):
        """
        Initialize LRU cache.
        
        Args:
            max_size: Maximum number of items in cache
            ttl: Time-to-live in seconds
        """
        self.cache: OrderedDict[str, Dict[str, Any]] = OrderedDict()
        self.max_size = max_size
        self.ttl = ttl
        self.hits = 0
        self.misses = 0
    
    def _is_expired(self, entry: Dict[str, Any]) -> bool:
        """Check if cache entry is expired."""
        if self.ttl <= 0:
            return False
        return time.time() - entry["timestamp"] > self.ttl
    
    def get(self, key: str) -> Optional[Any]:
        """
        Retrieve value from cache.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None if not found/expired
        """
        if key not in self.cache:
            self.misses += 1
            logger.debug(f"cache_status=miss key={key[:50]}")
            return None
        
        entry = self.cache[key]
        
        # Check if expired
        if self._is_expired(entry):
            del self.cache[key]
            self.misses += 1
            logger.debug(f"cache_status=expired key={key[:50]}")
            return None
        
        # Move to end (most recently used)
        self.cache.move_to_end(key)
        self.hits += 1
        logger.debug(f"cache_status=hit key={key[:50]}")
        return entry["value"]
    
    def set(self, key: str, value: Any) -> None:
        """
        Store value in cache.
        
        Args:
            key: Cache key
            value: Value to cache
        """
        # If key exists, update it
        if key in self.cache:
            self.cache.move_to_end(key)
        
        # Add new entry
        self.cache[key] = {
            "value": value,
            "timestamp": time.time()
        }
        
        # Evict oldest if over capacity
        if len(self.cache) > self.max_size:
            oldest_key = next(iter(self.cache))
            del self.cache[oldest_key]
            logger.debug(f"cache_eviction=lru key={oldest_key[:50]}")
    
    def clear(self) -> None:
        """Clear all cache entries."""
        self.cache.clear()
        self.hits = 0
        self.misses = 0
        logger.info("cache_cleared=true")
    
    def stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.
        
        Returns:
            Dict with hit rate and other metrics
        """
        total = self.hits + self.misses
        hit_rate = (self.hits / total * 100) if total > 0 else 0
        
        return {
            "size": len(self.cache),
            "max_size": self.max_size,
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": round(hit_rate, 2),
            "ttl": self.ttl
        }


def generate_cache_key(input_data: str, tool_name: str = "") -> str:
    """
    Generate normalized cache key from input.
    
    Args:
        input_data: Input string (question, features, etc.)
        tool_name: Name of the tool (for namespacing)
        
    Returns:
        Cache key (hash)
    """
    # Normalize input (lowercase, strip whitespace)
    normalized = input_data.lower().strip()
    
    # Create key with namespace
    key_string = f"{tool_name}:{normalized}"
    
    # Generate hash
    return hashlib.sha256(key_string.encode()).hexdigest()


# Global cache instances
_rag_cache: Optional[LRUCache] = None
_embedding_cache: Optional[LRUCache] = None
_ml_cache: Optional[LRUCache] = None


def get_rag_cache() -> LRUCache:
    """Get or create RAG answer cache."""
    global _rag_cache
    if _rag_cache is None:
        _rag_cache = LRUCache(max_size=500, ttl=3600)
        logger.info("RAG cache initialized: max_size=500, ttl=3600s")
    return _rag_cache


def get_embedding_cache() -> LRUCache:
    """Get or create embedding vector cache."""
    global _embedding_cache
    if _embedding_cache is None:
        _embedding_cache = LRUCache(max_size=1000, ttl=7200)
        logger.info("Embedding cache initialized: max_size=1000, ttl=7200s")
    return _embedding_cache


def get_ml_cache() -> LRUCache:
    """Get or create ML prediction cache."""
    global _ml_cache
    if _ml_cache is None:
        _ml_cache = LRUCache(max_size=200, ttl=1800)
        logger.info("ML cache initialized: max_size=200, ttl=1800s")
    return _ml_cache
