"""
Custom database router for sharded database operations.

This router directs read/write operations to the appropriate shard
based on the sharding context (user_id).
"""

from api.sharding import ShardingContext, get_shard_name, get_replica_name


class ShardRouter:
    """
    Database router that routes ORM operations to appropriate shard databases.
    
    Uses the user_id from ShardingContext to determine which shard to use.
    Supports read/write splitting with replicas.
    """

    def db_for_read(self, model, **hints):
        """
        Route read operations to read replicas if available.
        Falls back to primary shard if no context.
        """
        # Try to get user_id from hints (passed explicitly)
        user_id = hints.get('user_id')
        
        # If not in hints, try to get from context
        if user_id is None:
            user_id = ShardingContext.get_user_id()
        
        if user_id is None:
            return None  # Use default database
        
        # Route to replica for read operations (read scaling)
        # replica = get_replica_name(user_id)
        # return replica if replica else None
        shard = get_shard_name(user_id)
        return shard if shard else None

    def db_for_write(self, model, **hints):
        """
        Route write operations to primary shard only.
        Never write to replicas.
        """
        # Try to get user_id from hints
        user_id = hints.get('user_id')
        
        # If not in hints, try to get from context
        if user_id is None:
            user_id = ShardingContext.get_user_id()
        
        if user_id is None:
            return None  # Use default database
        
        # Always write to primary shard
        shard = get_shard_name(user_id)
        return shard if shard else None

    def allow_relation(self, obj1, obj2, **hints):
        """
        Allow relations if both objects are in the same shard.
        """
        user_id_1 = getattr(obj1, 'user_id', None) or ShardingContext.get_user_id()
        user_id_2 = getattr(obj2, 'user_id', None) or ShardingContext.get_user_id()
        
        if user_id_1 and user_id_2:
            return get_shard_name(user_id_1) == get_shard_name(user_id_2)
        
        return None  # Allow if we can't determine

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        """
        Allow migrations on all shard databases.
        Migrations should run on all shards to keep schema in sync.
        """
        # Allow migrations on all shard databases
        if db in ['shard_0', 'shard_1', 'shard_0_replica', 'shard_1_replica', 'default']:
            return True
        return None
