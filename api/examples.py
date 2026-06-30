"""
Example of implementing sharding in views.

This file demonstrates best practices for using database sharding
in Django REST Framework views.
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from api.models import Order, OrderItem, Cart
from api.serializers import OrderSerializer, CartSerializer
from api.sharding import ShardingContext, get_shard_name
from api.utils import (
    require_shard_context, log_shard_operation,
    validate_user_access, get_user_shard_info
)

import logging

logger = logging.getLogger(__name__)


class ShardedOrderViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Order operations with database sharding.
    
    Automatically routes queries to the correct shard based on user_id.
    The ShardingMiddleware sets the context for authenticated requests.
    """
    
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """
        Get queryset for authenticated user's shard.
        
        ShardingMiddleware automatically sets user_id in ShardingContext,
        so the router directs this query to the correct shard.
        """
        user = self.request.user
        ShardingContext.set_user_id(user.id)
        
        # All queries automatically go to user's shard
        return Order.objects.filter(user=user)

    def perform_create(self, serializer):
        """Create order in user's shard."""
        user = self.request.user
        log_shard_operation('create', 'Order', user.id)
        
        ShardingContext.set_user_id(user.id)
        serializer.save(user=user)

    def perform_update(self, serializer):
        """Update order in user's shard."""
        user = self.request.user
        order_id = self.kwargs.get('pk')
        
        log_shard_operation('update', 'Order', user.id)
        ShardingContext.set_user_id(user.id)
        
        serializer.save()

    @action(detail=True, methods=['get'])
    def shard_info(self, request, pk=None):
        """Get shard information for this user."""
        user_id = request.user.id
        shard_info = get_user_shard_info(user_id)
        
        return Response(shard_info)

    @action(detail=False, methods=['get'])
    def my_orders(self, request):
        """
        Get all orders for the authenticated user.
        
        This is simpler than list() and explicitly shows shard usage.
        """
        user_id = request.user.id
        ShardingContext.set_user_id(user_id)
        
        try:
            orders = Order.objects.filter(user_id=user_id)
            serializer = self.get_serializer(orders, many=True)
            return Response(serializer.data)
        finally:
            ShardingContext.clear()


class ShardedCartViewSet(viewsets.ViewSet):
    """
    ViewSet for Cart operations with sharding.
    
    Demonstrates simple sharding patterns for cart management.
    """
    
    permission_classes = [IsAuthenticated]

    def list(self, request):
        """Get user's cart."""
        user = request.user
        ShardingContext.set_user_id(user.id)
        
        try:
            cart = Cart.objects.get(user=user)
            serializer = CartSerializer(cart)
            return Response(serializer.data)
        except Cart.DoesNotExist:
            return Response(
                {'error': 'Cart not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        finally:
            ShardingContext.clear()

    def create(self, request):
        """Add item to user's cart."""
        user = request.user
        user_id = user.id
        
        ShardingContext.set_user_id(user_id)
        
        try:
            log_shard_operation('create', 'CartItem', user_id)
            
            cart, _ = Cart.objects.get_or_create(user=user)
            
            product_id = request.data.get('product_id')
            quantity = request.data.get('quantity', 1)
            
            from api.models import Product
            product = Product.objects.get(id=product_id)
            
            cart_item, created = cart.items.update_or_create(
                product=product,
                defaults={'quantity': quantity}
            )
            
            return Response(
                {'message': 'Item added to cart'},
                status=status.HTTP_201_CREATED
            )
        finally:
            ShardingContext.clear()

    def destroy(self, request, pk=None):
        """Remove item from user's cart."""
        user = request.user
        user_id = user.id
        
        ShardingContext.set_user_id(user_id)
        
        try:
            log_shard_operation('delete', 'CartItem', user_id)
            
            cart = Cart.objects.get(user=user)
            cart.items.get(id=pk).delete()
            
            return Response(status=status.HTTP_204_NO_CONTENT)
        finally:
            ShardingContext.clear()


# Advanced example: Cross-shard aggregation
class OrderStatsViewSet(viewsets.ViewSet):
    """
    Example of querying across all shards for statistics.
    
    This demonstrates how to aggregate data from multiple shards
    when needed (e.g., admin dashboard).
    """
    
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['get'])
    def user_stats(self, request):
        """
        Get statistics for authenticated user.
        
        This queries only the user's shard, avoiding cross-shard complexity.
        """
        user = request.user
        user_id = user.id
        
        ShardingContext.set_user_id(user_id)
        
        try:
            orders = Order.objects.filter(user=user)
            
            total_orders = orders.count()
            total_spent = orders.aggregate(
                total=sum('total_price')
            )['total'] or 0
            
            shard_name = get_shard_name(user_id)
            
            return Response({
                'user_id': user_id,
                'shard': shard_name,
                'total_orders': total_orders,
                'total_spent': total_spent,
            })
        finally:
            ShardingContext.clear()

    @action(detail=False, methods=['get'])
    def all_users_stats(self, request):
        """
        Get aggregated statistics across all shards.
        
        This is an admin-only operation that queries all shards.
        """
        if not request.user.is_staff:
            return Response(
                {'error': 'Admin access required'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        from api.sharding import SHARD_NAMES
        from django.db import connections
        
        total_stats = {'all_orders': 0, 'all_spent': 0}
        
        for shard_name in SHARD_NAMES:
            ShardingContext.set_user_id(1)  # Dummy to select shard
            
            try:
                orders = Order.objects.using(shard_name).all()
                total_stats['all_orders'] += orders.count()
                total_stats['all_spent'] += orders.aggregate(
                    total=sum('total_price')
                )['total'] or 0
            except Exception as e:
                logger.error(f"Error querying {shard_name}: {e}")
        
        return Response(total_stats)


# Helper function example
def get_user_order_details(user_id: int, order_id: int):
    """
    Helper function showing sharding in business logic.
    
    Usage:
        order_details = get_user_order_details(user_id=42, order_id=123)
    """
    ShardingContext.set_user_id(user_id)
    
    try:
        order = Order.objects.get(id=order_id, user_id=user_id)
        
        items = OrderItem.objects.filter(order=order)
        
        return {
            'order': order,
            'items': items,
            'shard': get_shard_name(user_id),
        }
    except Order.DoesNotExist:
        return None
    finally:
        ShardingContext.clear()


# Example: Using with bulk operations
def create_orders_for_user(user_id: int, orders_data: list):
    """
    Create multiple orders for a user.
    
    All orders go to the same shard since they're for the same user.
    """
    from django.contrib.auth.models import User
    from api.models import Order
    
    user = User.objects.get(id=user_id)
    ShardingContext.set_user_id(user_id)
    
    try:
        orders_to_create = [
            Order(
                user=user,
                total_price=order_data['total_price'],
                status=order_data.get('status', 'pending')
            )
            for order_data in orders_data
        ]
        
        log_shard_operation('bulk_create', 'Order', user_id)
        created_orders = Order.objects.bulk_create(orders_to_create)
        
        return created_orders
    finally:
        ShardingContext.clear()
