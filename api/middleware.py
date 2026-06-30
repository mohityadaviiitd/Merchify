"""
Middleware for managing sharding context across requests.

Automatically sets the user_id in ShardingContext for authenticated users,
ensuring all database operations route to the correct shard.
"""

from api.sharding import ShardingContext


class ShardingMiddleware:
    """
    Middleware that sets the sharding context (user_id) for each request.
    
    This ensures that:
    1. Authenticated requests automatically use the user's shard
    2. Unsharded tables use the default database
    3. The context is cleared after the request completes
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Set sharding context if user is authenticated
        if request.user and request.user.is_authenticated:
            ShardingContext.set_user_id(request.user.id)

        try:
            response = self.get_response(request)
        finally:
            # Always clear context after request
            ShardingContext.clear()

        return response
