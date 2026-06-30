# Database Sharding Implementation Guide

## Overview

This guide explains how the database sharding system works in the Merchify backend. The system implements **horizontal database partitioning** with 2 shards, each with a read replica.

### Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Application                              │
│                    (Django REST API)                            │
└────────────────────────────┬────────────────────────────────────┘
                             │
                    ┌────────▼─────────┐
                    │ ShardingRouter   │
                    │  & Middleware    │
                    └────────┬─────────┘
                             │
                ┌────────────┴────────────┐
                │                         │
        ┌───────▼────────┐      ┌────────▼────────┐
        │   Shard 0      │      │   Shard 1       │
        ├────────────────┤      ├─────────────────┤
        │ Primary (RW)   │      │ Primary (RW)    │
        │ ↓              │      │ ↓               │
        │ Replica (R)    │      │ Replica (R)     │
        └────────────────┘      └─────────────────┘
        (user_id % 2==0)        (user_id % 2==1)
```

## Sharding Strategy

### Distribution
- **Shard 0**: User IDs where `user_id % 2 == 0` (even)
- **Shard 1**: User IDs where `user_id % 2 == 1` (odd)

### Each Shard Has
- **Primary**: For read and write operations
- **Read Replica**: For read-heavy operations (scaling reads)

## Database Configuration

### Environment Variables Required

Create a `.env` file with the following configuration:

```env
# Default database (for auth/user tables)
POSTGRES_DB=merchify
POSTGRES_USER=merchifyuser
POSTGRES_PASSWORD=your_secure_password
DB_HOST=your-rds-endpoint.rds.amazonaws.com
DB_PORT=5432

# Shard 0 - Primary
SHARD_0_DB=merchify_shard_0
SHARD_0_USER=merchifyuser
SHARD_0_PASSWORD=your_secure_password
SHARD_0_HOST=shard-0-primary.rds.amazonaws.com
SHARD_0_PORT=5432

# Shard 0 - Read Replica
SHARD_0_REPLICA_DB=merchify_shard_0
SHARD_0_REPLICA_USER=merchifyuser
SHARD_0_REPLICA_PASSWORD=your_secure_password
SHARD_0_REPLICA_HOST=shard-0-replica.rds.amazonaws.com
SHARD_0_REPLICA_PORT=5432

# Shard 1 - Primary
SHARD_1_DB=merchify_shard_1
SHARD_1_USER=merchifyuser
SHARD_1_PASSWORD=your_secure_password
SHARD_1_HOST=shard-1-primary.rds.amazonaws.com
SHARD_1_PORT=5432

# Shard 1 - Read Replica
SHARD_1_REPLICA_DB=merchify_shard_1
SHARD_1_REPLICA_USER=merchifyuser
SHARD_1_REPLICA_PASSWORD=your_secure_password
SHARD_1_REPLICA_HOST=shard-1-replica.rds.amazonaws.com
SHARD_1_REPLICA_PORT=5432
```

## AWS RDS Setup Steps

### 1. Create Primary RDS Instances

For each shard, create a DB instance:

**Shard 0 (Primary):**
- DB Identifier: `shard-0-primary`
- Engine: PostgreSQL
- DB Name: `merchify_shard_0`
- Master username: `merchifyuser`
- Password: Use a strong password

**Shard 1 (Primary):**
- DB Identifier: `shard-1-primary`
- Engine: PostgreSQL
- DB Name: `merchify_shard_1`
- Master username: `merchifyuser`
- Password: Use a strong password

### 2. Create Read Replicas

For each primary shard, create a read replica in a different availability zone:

**Shard 0 Replica:**
- Source: `shard-0-primary`
- DB Identifier: `shard-0-replica`
- Multi-AZ: Yes (recommended)

**Shard 1 Replica:**
- Source: `shard-1-primary`
- DB Identifier: `shard-1-replica`
- Multi-AZ: Yes (recommended)

### 3. Configure Security Groups

Ensure all RDS instances can communicate with your application:
- Allow inbound traffic on port 5432 from your app's security group
- Configure VPC and subnet groups as needed

## Usage in Views

### Basic Usage

```python
from django.contrib.auth.decorators import login_required
from rest_framework.decorators import api_view
from rest_framework.response import Response
from api.models import Order
from api.sharding import ShardingContext, get_shard_name

@api_view(['GET'])
@login_required
def get_user_orders(request):
    """
    Automatically uses the correct shard based on request.user.id
    (ShardingMiddleware sets context automatically)
    """
    user_id = request.user.id
    orders = Order.objects.filter(user_id=user_id)
    
    # Query automatically routes to the correct shard
    return Response({
        'shard': get_shard_name(user_id),
        'orders': orders.values('id', 'total_price', 'status'),
    })
```

### Explicit Shard Context

```python
from api.sharding import ShardingContext, get_shard_name

def process_order(user_id):
    """Process order for a specific user"""
    with ShardingContext():
        ShardingContext.set_user_id(user_id)
        
        # All ORM queries in this block use the correct shard
        order = Order.objects.create(
            user_id=user_id,
            total_price=100.00,
            status='pending'
        )
        
        # Read operations automatically use replica
        stats = Order.objects.filter(user_id=user_id).count()
        
    # Context automatically cleared after `with` block
    return order
```

### QuerySet Hints (Optional)

```python
from api.models import Order

def search_orders(user_id):
    """Explicit shard hint (optional, usually not needed)"""
    # Middleware usually handles this, but can be explicit:
    orders = Order.objects.using('shard_0').filter(user_id=user_id)
    # or let the router decide:
    orders = Order.objects.filter(user_id=user_id)
```

## Initial Setup

### Step 1: Create Shard Databases

For **AWS RDS**: Use the AWS Management Console to create the instances (as shown above).

For **Local PostgreSQL**:
```bash
python manage.py setup_shards --create-dbs
```

### Step 2: Check Connections

```bash
python manage.py setup_shards --check
```

Expected output:
```
Checking database connections...
  ✓ default               → your-db.rds.amazonaws.com/merchify
  ✓ shard_0               → shard-0-primary.rds.amazonaws.com/merchify_shard_0
  ✓ shard_0_replica       → shard-0-replica.rds.amazonaws.com/merchify_shard_0
  ✓ shard_1               → shard-1-primary.rds.amazonaws.com/merchify_shard_1
  ✓ shard_1_replica       → shard-1-replica.rds.amazonaws.com/merchify_shard_1
```

### Step 3: Run Migrations

```bash
python manage.py setup_shards --migrate
```

This runs Django migrations on all shard databases.

### Step 4: Verify Setup

```bash
python manage.py setup_shards --stats
```

## Key Components

### 1. ShardingContext (`api/sharding.py`)

Thread-local context manager for tracking the current user's shard:

```python
from api.sharding import ShardingContext, get_shard_name

# Set context
ShardingContext.set_user_id(user_id)

# Get shard name
shard = get_shard_name(user_id)  # 'shard_0' or 'shard_1'

# Clear context
ShardingContext.clear()
```

### 2. ShardRouter (`api/routers.py`)

Django database router that:
- Routes **writes** to primary shards only
- Routes **reads** to replicas when available
- Handles migrations on all shards
- Ensures cross-shard relations are prevented

### 3. ShardingMiddleware (`api/middleware.py`)

Automatically sets sharding context for authenticated requests:
- Extracts `user_id` from request.user
- Sets ShardingContext for the request
- Clears context after response

### 4. Management Command (`api/management/commands/setup_shards.py`)

Utilities for shard management:
- `--check`: Verify all shard connections
- `--migrate`: Run migrations on all shards
- `--stats`: Show shard configuration
- `--create-dbs`: Create shard databases (local only)

## Monitoring & Troubleshooting

### Debugging Shard Assignment

```python
from api.sharding import get_shard_name, get_shard_id

user_id = 42
shard_id = get_shard_id(user_id)  # 0
shard_name = get_shard_name(user_id)  # 'shard_0'
print(f"User {user_id} → Shard {shard_id} ({shard_name})")
```

### Common Issues

#### Issue: "No user_id in sharding context"
**Cause**: Trying to access sharded data outside of a request context or without setting user_id.

**Solution**:
```python
from api.sharding import ShardingContext

# Always set context first
ShardingContext.set_user_id(user_id)
# Now do queries
order = Order.objects.filter(user_id=user_id).first()
ShardingContext.clear()
```

#### Issue: Cross-shard query failures
**Cause**: Trying to query data from multiple users (shards) in one query.

**Solution**: Query one user (shard) at a time:
```python
# ✗ Wrong: queries both shards
Order.objects.filter(user_id__in=[1, 2, 3])

# ✓ Correct: query one shard
user_id = 1
ShardingContext.set_user_id(user_id)
Order.objects.filter(user_id=user_id)
```

### Monitoring Shard Health

```python
from django.db import connections

# Check shard 0 primary
conn = connections['shard_0']
with conn.cursor() as cursor:
    cursor.execute('SELECT 1')
    print("Shard 0 Primary: OK")

# Check shard 0 replica
conn = connections['shard_0_replica']
with conn.cursor() as cursor:
    cursor.execute('SELECT 1')
    print("Shard 0 Replica: OK")
```

## Migration Strategy

### Adding New Tables

1. Create model in `api/models.py`
2. Create and apply migrations to all shards:
   ```bash
   python manage.py makemigrations
   python manage.py setup_shards --migrate
   ```

### Scaling to More Shards

If you need more than 2 shards:

1. Update `SHARD_COUNT` in `api/sharding.py`
2. Update `SHARD_NAMES` and `REPLICA_NAMES`
3. Add new database configurations to settings.py
4. Create new RDS instances
5. Run migrations on new shards

### Re-sharding (Moving Data)

For data migration between shards:
1. Create a management command that reads from one shard, writes to another
2. Implement verification logic
3. Run during low-traffic periods
4. Update shard configuration once migration is complete

## Performance Tips

1. **Index user_id**: Add indexes on `user_id` in all sharded tables
   ```python
   class Order(models.Model):
       user = models.ForeignKey(User, db_index=True, ...)
   ```

2. **Batch operations**: Use `bulk_create()` for multiple records
   ```python
   ShardingContext.set_user_id(user_id)
   Order.objects.bulk_create(orders)
   ```

3. **Connection pooling**: Configure PgBouncer or AWS RDS Proxy
   - Reduces connection overhead
   - Improves throughput

4. **Read replicas**: Use read replicas for reporting/analytics
   - Write to primary, read from replica
   - Reduces load on primary

## Testing

### Unit Tests

```python
from django.test import TestCase
from api.models import Order
from api.sharding import ShardingContext, get_shard_name

class ShardingTestCase(TestCase):
    databases = {'shard_0', 'shard_1', 'default'}

    def test_order_sharding(self):
        user_id = 42
        ShardingContext.set_user_id(user_id)
        
        shard = get_shard_name(user_id)
        self.assertEqual(shard, 'shard_0')  # 42 % 2 == 0
        
        order = Order.objects.create(
            user_id=user_id,
            total_price=100.00
        )
        
        # Should be able to retrieve from same shard
        retrieved = Order.objects.filter(user_id=user_id).first()
        self.assertEqual(retrieved.id, order.id)
```

## Additional Resources

- [Django Multiple Databases](https://docs.djangoproject.com/en/5.2/topics/db/multi-db/)
- [AWS RDS Best Practices](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/CHAP_BestPractices.html)
- [Database Sharding Patterns](https://en.wikipedia.org/wiki/Shard_(database_architecture))
