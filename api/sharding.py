"""
Database sharding utilities for Merchify backend.

This module provides utilities for managing database shards:
- 2 shards (shard_0, shard_1)
- Each shard has a primary (write) and read replica

Sharding strategy: User-based sharding using user_id % 2
"""

from django.core.cache import cache
from functools import lru_cache

# Shard configuration
SHARD_COUNT = 2
SHARD_NAMES = ['shard_0', 'shard_1']
REPLICA_NAMES = {
    'shard_0': 'shard_0_replica',
    'shard_1': 'shard_1_replica',
}


class ShardingContext:
    """
    Context manager to track the current shard for a user.
    Stores shard info in thread-local storage.
    """
    _context = {}

    @classmethod
    def set_user_id(cls, user_id: int):
        """Set the current user_id for shard selection."""
        import threading
        thread_id = threading.get_ident()
        cls._context[thread_id] = {'user_id': user_id}

    @classmethod
    def get_user_id(cls) -> int:
        """Get the current user_id."""
        import threading
        thread_id = threading.get_ident()
        return cls._context.get(thread_id, {}).get('user_id')

    @classmethod
    def clear(cls):
        """Clear the context."""
        import threading
        thread_id = threading.get_ident()
        if thread_id in cls._context:
            del cls._context[thread_id]

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.clear()


def get_shard_id(user_id: int) -> int:
    """
    Determine shard ID based on user_id using modulo strategy.
    
    Args:
        user_id: The user ID to shard
        
    Returns:
        int: Shard ID (0 or 1)
    """
    if user_id is None:
        raise ValueError("user_id cannot be None for sharding")
    return user_id % SHARD_COUNT


def get_shard_name(user_id: int) -> str:
    """
    Get the shard database name for a given user_id.
    
    Args:
        user_id: The user ID
        
    Returns:
        str: Database alias (e.g., 'shard_0', 'shard_1')
    """
    shard_id = get_shard_id(user_id)
    return SHARD_NAMES[shard_id]


def get_replica_name(user_id: int) -> str:
    """
    Get the read replica database name for a given user_id.
    
    Args:
        user_id: The user ID
        
    Returns:
        str: Read replica database alias
    """
    shard_name = get_shard_name(user_id)
    return REPLICA_NAMES.get(shard_name)


def get_current_shard_name() -> str:
    """
    Get the shard name from the current context.
    
    Returns:
        str: Database alias for the current shard
        
    Raises:
        ValueError: If user_id not set in context
    """
    user_id = ShardingContext.get_user_id()
    if user_id is None:
        raise ValueError("No user_id in sharding context. Use ShardingContext.set_user_id() first.")
    return get_shard_name(user_id)


@lru_cache(maxsize=1024)
def get_shard_distribution():
    """
    Get cache key for shard distribution stats.
    Useful for monitoring shard balance.
    """
    return cache.get('shard_distribution', {})


def cache_shard_distribution(stats: dict):
    """Cache shard distribution statistics."""
    cache.set('shard_distribution', stats, 3600)  # 1 hour TTL


# Shard mapping documentation
"""
SHARD CONFIGURATION:

Shard 0 (Even user IDs):
  Primary:   shard_0 (user_id % 2 == 0)
  Replica:   shard_0_replica

Shard 1 (Odd user IDs):
  Primary:   shard_1 (user_id % 2 == 1)
  Replica:   shard_1_replica

USAGE EXAMPLES:

# In views or business logic
from api.sharding import ShardingContext, get_shard_name

user_id = request.user.id
shard = get_shard_name(user_id)

# With context manager
with ShardingContext() as ctx:
    ctx.set_user_id(user_id)
    # All queries will use the correct shard
    order = Order.objects.filter(user_id=user_id).first()

# Or set directly
ShardingContext.set_user_id(user_id)
# All queries use the correct shard
order = Order.objects.filter(user_id=user_id).first()
ShardingContext.clear()
"""
