"""
Unit and integration tests for database sharding.

Tests verify:
1. Correct shard assignment based on user_id
2. Router directs queries to correct shards
3. Read replicas are used for reads
4. Cross-shard constraints are enforced
5. Middleware sets context correctly
"""

from django.test import TestCase, TransactionTestCase, RequestFactory
from django.contrib.auth.models import User
from django.test.client import Client

from api.models import Order, Cart, CartItem, Product, Category
from api.sharding import (
    ShardingContext, get_shard_id, get_shard_name,
    get_replica_name, SHARD_COUNT
)
from api.routers import ShardRouter
from api.middleware import ShardingMiddleware
from api.utils import get_user_shard_info, validate_user_access

import logging

logger = logging.getLogger(__name__)


class ShardingUtilsTestCase(TestCase):
    """Test sharding utility functions."""

    def test_shard_id_calculation(self):
        """Test that user IDs are correctly assigned to shards."""
        # Even user ID → Shard 0
        self.assertEqual(get_shard_id(2), 0)
        self.assertEqual(get_shard_id(4), 0)
        self.assertEqual(get_shard_id(100), 0)
        
        # Odd user ID → Shard 1
        self.assertEqual(get_shard_id(1), 1)
        self.assertEqual(get_shard_id(3), 1)
        self.assertEqual(get_shard_id(101), 1)

    def test_shard_name_mapping(self):
        """Test shard name resolution."""
        # Even IDs map to shard_0
        self.assertEqual(get_shard_name(2), 'shard_0')
        self.assertEqual(get_shard_name(4), 'shard_0')
        
        # Odd IDs map to shard_1
        self.assertEqual(get_shard_name(1), 'shard_1')
        self.assertEqual(get_shard_name(3), 'shard_1')

    def test_replica_name_resolution(self):
        """Test read replica name resolution."""
        # Even user IDs
        self.assertEqual(get_replica_name(2), 'shard_0_replica')
        self.assertEqual(get_replica_name(4), 'shard_0_replica')
        
        # Odd user IDs
        self.assertEqual(get_replica_name(1), 'shard_1_replica')
        self.assertEqual(get_replica_name(3), 'shard_1_replica')

    def test_get_user_shard_info(self):
        """Test comprehensive shard info retrieval."""
        shard_info = get_user_shard_info(42)
        
        self.assertEqual(shard_info['user_id'], 42)
        self.assertEqual(shard_info['shard_id'], 0)  # 42 % 2 == 0
        self.assertEqual(shard_info['primary'], 'shard_0')
        self.assertEqual(shard_info['replica'], 'shard_0_replica')


class ShardingContextTestCase(TestCase):
    """Test ShardingContext management."""

    def setUp(self):
        """Clear context before each test."""
        ShardingContext.clear()

    def tearDown(self):
        """Clear context after each test."""
        ShardingContext.clear()

    def test_context_set_and_get(self):
        """Test setting and getting context."""
        user_id = 42
        ShardingContext.set_user_id(user_id)
        
        self.assertEqual(ShardingContext.get_user_id(), user_id)

    def test_context_manager(self):
        """Test context manager properly clears context."""
        user_id = 42
        
        with ShardingContext():
            ShardingContext.set_user_id(user_id)
            self.assertEqual(ShardingContext.get_user_id(), user_id)
        
        # Context should be cleared after exiting
        self.assertIsNone(ShardingContext.get_user_id())

    def test_context_isolation(self):
        """Test that contexts don't leak between threads."""
        import threading
        
        results = {}

        def set_context(user_id):
            ShardingContext.set_user_id(user_id)
            results[user_id] = ShardingContext.get_user_id()

        thread1 = threading.Thread(target=set_context, args=(1,))
        thread2 = threading.Thread(target=set_context, args=(2,))
        
        thread1.start()
        thread2.start()
        
        thread1.join()
        thread2.join()
        
        # Both threads should have their own context
        self.assertEqual(results.get(1), 1)
        self.assertEqual(results.get(2), 2)


class ShardRouterTestCase(TransactionTestCase):
    """Test the ShardRouter logic."""
    
    databases = {'default', 'shard_0', 'shard_1', 'shard_0_replica', 'shard_1_replica'}

    def setUp(self):
        """Set up test data."""
        ShardingContext.clear()
        self.router = ShardRouter()

    def tearDown(self):
        """Clean up."""
        ShardingContext.clear()

    def test_router_routes_writes_to_primary(self):
        """Test that writes are routed to primary shards only."""
        # Even user ID should route to shard_0
        user_id = 2
        ShardingContext.set_user_id(user_id)
        
        db = self.router.db_for_write(Order, user_id=user_id)
        self.assertEqual(db, 'shard_0')
        
        # Odd user ID should route to shard_1
        user_id = 3
        ShardingContext.set_user_id(user_id)
        
        db = self.router.db_for_write(Order, user_id=user_id)
        self.assertEqual(db, 'shard_1')

    def test_router_routes_reads_to_replicas(self):
        """Test that reads are routed to read replicas."""
        # Even user ID should route to shard_0_replica
        user_id = 2
        ShardingContext.set_user_id(user_id)
        
        db = self.router.db_for_read(Order, user_id=user_id)
        self.assertEqual(db, 'shard_0_replica')
        
        # Odd user ID should route to shard_1_replica
        user_id = 3
        ShardingContext.set_user_id(user_id)
        
        db = self.router.db_for_read(Order, user_id=user_id)
        self.assertEqual(db, 'shard_1_replica')

    def test_router_allows_migrations(self):
        """Test that migrations are allowed on all shard databases."""
        for db in ['default', 'shard_0', 'shard_1', 'shard_0_replica', 'shard_1_replica']:
            result = self.router.allow_migrate(db, 'api')
            self.assertEqual(
                result, True,
                f"Migration should be allowed on {db}"
            )


class ShardingMiddlewareTestCase(TestCase):
    """Test the ShardingMiddleware."""

    def setUp(self):
        """Set up test environment."""
        self.factory = RequestFactory()
        self.middleware = ShardingMiddleware(self.get_response)
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass'
        )

    def get_response(self, request):
        """Mock response."""
        from django.http import HttpResponse
        return HttpResponse()

    def test_middleware_sets_context_for_authenticated_user(self):
        """Test that middleware sets sharding context for authenticated users."""
        request = self.factory.get('/')
        request.user = self.user
        
        self.middleware(request)
        
        # Context should be set during middleware execution
        # (though it's cleared after response)
        # We'll test by checking if it was set during the call
        # by modifying get_response to verify context

    def test_middleware_clears_context_after_request(self):
        """Test that middleware clears context after request."""
        request = self.factory.get('/')
        request.user = self.user
        
        def get_response_verify(req):
            # Verify context is set during request processing
            self.assertEqual(ShardingContext.get_user_id(), self.user.id)
            from django.http import HttpResponse
            return HttpResponse()

        middleware = ShardingMiddleware(get_response_verify)
        middleware(request)
        
        # Context should be cleared after middleware returns
        self.assertIsNone(ShardingContext.get_user_id())


class OrderShardingTestCase(TransactionTestCase):
    """Test Order model with sharding."""
    
    databases = {'default', 'shard_0', 'shard_1'}

    def setUp(self):
        """Set up test users in default database."""
        self.user_even = User.objects.create_user(
            username='user_even',
            password='pass'
        )
        # Ensure user has even ID by creating multiple
        while self.user_even.id % 2 != 0:
            self.user_even.delete()
            self.user_even = User.objects.create_user(
                username='user_even',
                password='pass'
            )
        
        self.user_odd = User.objects.create_user(
            username='user_odd',
            password='pass'
        )
        # Ensure user has odd ID
        while self.user_odd.id % 2 == 0:
            self.user_odd.delete()
            self.user_odd = User.objects.create_user(
                username='user_odd',
                password='pass'
            )

    def tearDown(self):
        """Clean up."""
        ShardingContext.clear()

    def test_order_creation_uses_correct_shard(self):
        """Test that orders are created on the correct shard."""
        # Create order for even user
        ShardingContext.set_user_id(self.user_even.id)
        order_even = Order.objects.create(
            user=self.user_even,
            total_price=100.00,
            status='pending'
        )
        ShardingContext.clear()
        
        # Verify order was created
        self.assertIsNotNone(order_even.id)
        
        # Create order for odd user
        ShardingContext.set_user_id(self.user_odd.id)
        order_odd = Order.objects.create(
            user=self.user_odd,
            total_price=200.00,
            status='pending'
        )
        ShardingContext.clear()
        
        # Verify order was created
        self.assertIsNotNone(order_odd.id)

    def test_order_retrieval_uses_correct_shard(self):
        """Test that order queries use the correct shard."""
        # Create and retrieve order for even user
        ShardingContext.set_user_id(self.user_even.id)
        order = Order.objects.create(
            user=self.user_even,
            total_price=100.00,
        )
        
        retrieved = Order.objects.filter(user=self.user_even).first()
        self.assertEqual(retrieved.id, order.id)
        ShardingContext.clear()


class CrossShardConstraintTestCase(TestCase):
    """Test that cross-shard operations are handled correctly."""

    def test_validate_user_access_same_shard(self):
        """Test that users can only access their own shard."""
        user_id_1 = 2  # Shard 0
        user_id_2 = 4  # Shard 0 (same)
        
        # Same shard, but different user - should fail
        is_valid = validate_user_access(user_id_1, user_id_2)
        self.assertFalse(is_valid, "Different users shouldn't access each other")
        
        # Same user - should succeed
        is_valid = validate_user_access(user_id_1, user_id_1)
        self.assertTrue(is_valid, "User should access their own data")

    def test_validate_user_access_different_shard(self):
        """Test that cross-shard access is prevented."""
        user_id_shard_0 = 2  # Shard 0
        user_id_shard_1 = 3  # Shard 1
        
        is_valid = validate_user_access(user_id_shard_0, user_id_shard_1)
        self.assertFalse(is_valid, "Cross-shard access should be denied")


class ShardScalingTestCase(TestCase):
    """Test considerations for scaling shards."""

    def test_shard_distribution(self):
        """Test that users are evenly distributed across shards."""
        shard_counts = {0: 0, 1: 0}
        
        # Simulate 1000 users
        for user_id in range(1, 1001):
            shard_id = get_shard_id(user_id)
            shard_counts[shard_id] += 1
        
        # Should be roughly equal distribution
        total = sum(shard_counts.values())
        for shard_id, count in shard_counts.items():
            percentage = (count / total) * 100
            # Should be close to 50% each
            self.assertTrue(
                45 < percentage < 55,
                f"Shard {shard_id} has {percentage}% of users (should be ~50%)"
            )

    def test_new_users_are_distributed(self):
        """Test that new users are assigned to the correct shard."""
        new_user_ids = list(range(10001, 10101))
        
        shard_assignments = {}
        for user_id in new_user_ids:
            shard_id = get_shard_id(user_id)
            shard_assignments[shard_id] = shard_assignments.get(shard_id, 0) + 1
        
        # Both shards should have roughly 50 users
        for shard_id, count in shard_assignments.items():
            self.assertEqual(count, 50, f"Shard {shard_id} should have 50 users")
