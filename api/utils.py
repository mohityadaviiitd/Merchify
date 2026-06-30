"""
Decorators and utilities for simplified sharding usage.

Provides convenient decorators and helper functions for working with
sharded databases in views, tasks, and management commands.
"""

from functools import wraps
from typing import Callable, Any
from api.sharding import ShardingContext
import logging

logger = logging.getLogger(__name__)


def require_shard_context(view_func: Callable) -> Callable:
    """
    Decorator for views that require sharding context.
    
    Automatically sets up ShardingContext for authenticated users.
    Raises ValueError if user is not authenticated.
    
    Usage:
        @api_view(['GET'])
        @require_shard_context
        def my_view(request):
            order = Order.objects.filter(user_id=request.user.id).first()
            return Response(order)
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user or not request.user.is_authenticated:
            raise ValueError("User must be authenticated for sharded operations")
        
        user_id = request.user.id
        ShardingContext.set_user_id(user_id)
        
        try:
            return view_func(request, *args, **kwargs)
        finally:
            ShardingContext.clear()
    
    return wrapper


def with_shard_context(user_id: int) -> Callable:
    """
    Context decorator for any function that needs sharding.
    
    Usage:
        @with_shard_context(user_id=42)
        def process_user_data():
            orders = Order.objects.filter(user_id=42)
            return process_orders(orders)
    
    Or as a context manager:
        with with_shard_context(42):
            order = Order.objects.create(...)
    """
    class ShardContextDecorator:
        def __init__(self, uid: int):
            self.user_id = uid

        def __call__(self, func: Callable) -> Callable:
            @wraps(func)
            def wrapper(*args, **kwargs):
                ShardingContext.set_user_id(self.user_id)
                try:
                    return func(*args, **kwargs)
                finally:
                    ShardingContext.clear()
            return wrapper

        def __enter__(self):
            ShardingContext.set_user_id(self.user_id)
            return self

        def __exit__(self, exc_type, exc_val, exc_tb):
            ShardingContext.clear()

    return ShardContextDecorator(user_id)


def get_user_shard_info(user_id: int) -> dict:
    """
    Get comprehensive shard information for a user.
    
    Args:
        user_id: The user ID
        
    Returns:
        dict with shard details
    """
    from api.sharding import (
        get_shard_id, get_shard_name, get_replica_name
    )
    
    shard_id = get_shard_id(user_id)
    shard_name = get_shard_name(user_id)
    replica_name = get_replica_name(user_id)
    
    return {
        'user_id': user_id,
        'shard_id': shard_id,
        'primary': shard_name,
        'replica': replica_name,
        'read_from': replica_name,  # Prefer replica for reads
        'write_to': shard_name,      # Always write to primary
    }


def log_shard_operation(operation_type: str, model_name: str, user_id: int):
    """
    Log database operations for monitoring and debugging.
    
    Usage:
        from api.utils import log_shard_operation
        
        log_shard_operation('create', 'Order', user_id=42)
        order = Order.objects.create(user_id=42, ...)
    """
    from api.sharding import get_shard_name
    
    shard = get_shard_name(user_id)
    logger.info(
        f"[SHARD] {operation_type.upper()} {model_name} user={user_id} shard={shard}"
    )


def validate_user_access(user_id: int, target_user_id: int) -> bool:
    """
    Validate that a user can only access their own shard.
    
    Usage:
        if not validate_user_access(request.user.id, target_user_id):
            return Response({'error': 'Access denied'}, status=403)
    """
    from api.sharding import get_shard_name
    
    user_shard = get_shard_name(user_id)
    target_shard = get_shard_name(target_user_id)
    
    is_valid = user_shard == target_shard and user_id == target_user_id
    
    if not is_valid:
        logger.warning(
            f"Unauthorized cross-shard access attempt: "
            f"user={user_id} (shard={user_shard}) "
            f"target={target_user_id} (shard={target_shard})"
        )
    
    return is_valid


class ShardAwareQuerySet:
    """
    Helper for building queries that respect sharding constraints.
    
    Usage:
        sq = ShardAwareQuerySet(Order)
        order = sq.get(user_id=42, id=order_id)
        
        # Equivalent to:
        # with ShardingContext():
        #     ShardingContext.set_user_id(42)
        #     order = Order.objects.get(id=order_id, user_id=42)
    """
    
    def __init__(self, model_class):
        self.model = model_class
        
    def filter(self, **kwargs):
        """Filter with automatic shard context."""
        user_id = kwargs.get('user_id')
        if user_id is None:
            raise ValueError("user_id is required for sharded queries")
        
        ShardingContext.set_user_id(user_id)
        return self.model.objects.filter(**kwargs)
    
    def get(self, **kwargs):
        """Get with automatic shard context."""
        user_id = kwargs.get('user_id')
        if user_id is None:
            raise ValueError("user_id is required for sharded queries")
        
        ShardingContext.set_user_id(user_id)
        try:
            return self.model.objects.get(**kwargs)
        finally:
            ShardingContext.clear()
    
    def create(self, **kwargs):
        """Create with automatic shard context."""
        user_id = kwargs.get('user_id')
        if user_id is None:
            raise ValueError("user_id is required for sharded operations")
        
        ShardingContext.set_user_id(user_id)
        try:
            return self.model.objects.create(**kwargs)
        finally:
            ShardingContext.clear()
    
    def bulk_create(self, objects, **kwargs):
        """Bulk create with automatic shard context."""
        if not objects:
            return []
        
        # Ensure all objects have same user_id
        user_ids = set(getattr(obj, 'user_id', None) for obj in objects)
        if len(user_ids) > 1 or None in user_ids:
            raise ValueError("All objects must have same user_id for bulk operations")
        
        user_id = user_ids.pop()
        ShardingContext.set_user_id(user_id)
        try:
            return self.model.objects.bulk_create(objects, **kwargs)
        finally:
            ShardingContext.clear()
