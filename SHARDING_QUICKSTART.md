# Quick Start Guide: Database Sharding Setup

This guide will help you get database sharding up and running in minutes.

## Step 1: AWS RDS Setup (10 minutes)

### Create Primary Shard Databases

1. **Go to AWS Management Console → RDS → Databases → Create Database**

2. **Create Shard 0 Primary:**
   - Database creation method: Standard create
   - Engine: PostgreSQL (15 or higher)
   - DB Instance Identifier: `shard-0-primary`
   - Master username: `merchifyuser`
   - Master password: (generate a strong password)
   - Initial database name: `merchify_shard_0`
   - Publicly accessible: Yes (or configure security group)
   - Click Create

3. **Create Shard 1 Primary:**
   - Repeat above with DB Instance Identifier: `shard-1-primary`
   - Initial database name: `merchify_shard_1`

### Create Read Replicas

4. **Create Shard 0 Read Replica:**
   - Go to RDS → Databases → shard-0-primary
   - Actions → Create read replica
   - DB Instance Identifier: `shard-0-replica`
   - Click Create read replica

5. **Create Shard 1 Read Replica:**
   - Go to RDS → Databases → shard-1-primary
   - Actions → Create read replica
   - DB Instance Identifier: `shard-1-replica`
   - Click Create read replica

**Wait for all instances to finish creating (~5 minutes per instance)**

## Step 2: Get Connection Details

1. Go to RDS → Databases
2. For each database, click on it and note:
   - **Endpoint** (copy this as HOST)
   - **Port** (usually 5432)
   - **DB name** (already set in code)
   - **Username** (merchifyuser)

You should have endpoints for:
- shard-0-primary
- shard-0-replica
- shard-1-primary
- shard-1-replica

## Step 3: Update Environment Variables

1. Copy the `.env.sharding.example` file:
   ```bash
   cp .env.sharding.example .env
   ```

2. Edit `.env` and fill in all the RDS endpoints you collected:
   ```env
   SHARD_0_HOST=shard-0-primary.xxxxx.rds.amazonaws.com
   SHARD_0_REPLICA_HOST=shard-0-replica.xxxxx.rds.amazonaws.com
   SHARD_1_HOST=shard-1-primary.xxxxx.rds.amazonaws.com
   SHARD_1_REPLICA_HOST=shard-1-replica.xxxxx.rds.amazonaws.com
   ```

## Step 4: Run Migrations

1. Activate your virtual environment:
   ```bash
   cd c:\Users\mohit\Downloads\Merchify
   backend_env\Scripts\Activate.ps1
   ```

2. Test database connections:
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

3. Run initial setup (creates tables on all shards):
   ```bash
   python manage.py setup_shards
   ```

   Or run migrations manually on each shard:
   ```bash
   python manage.py migrate --database=shard_0
   python manage.py migrate --database=shard_1
   ```

## Step 5: Test Sharding

Run the test suite to verify everything works:

```bash
python manage.py test api.test_sharding -v 2
```

## Step 6: Use Sharding in Your Code

### In Views (Automatic via Middleware)

```python
from rest_framework.decorators import api_view
from rest_framework.response import Response
from api.models import Order

@api_view(['GET'])
def get_orders(request):
    """
    ShardingMiddleware automatically sets the correct shard
    based on request.user.id
    """
    user = request.user
    orders = Order.objects.filter(user=user)
    return Response({'orders': list(orders.values())})
```

### In Management Commands

```python
from django.core.management.base import BaseCommand
from api.sharding import ShardingContext
from api.models import Order

class Command(BaseCommand):
    def handle(self, *args, **options):
        user_id = 42
        
        # Set sharding context
        ShardingContext.set_user_id(user_id)
        
        try:
            # Query uses correct shard automatically
            orders = Order.objects.filter(user_id=user_id)
            self.stdout.write(f"Found {orders.count()} orders")
        finally:
            ShardingContext.clear()
```

### In Background Tasks (Celery)

```python
from celery import shared_task
from api.sharding import ShardingContext, with_shard_context
from api.models import Order

@shared_task
@with_shard_context(user_id=42)
def process_user_orders():
    """
    @with_shard_context decorator automatically sets up
    and cleans up the sharding context
    """
    orders = Order.objects.filter(user_id=42)
    return process_orders(orders)
```

## Troubleshooting

### "Connection refused" Error

**Solution:**
1. Verify RDS endpoint is accessible:
   ```bash
   Test-NetConnection shard-0-primary.xxxxx.rds.amazonaws.com -Port 5432
   ```

2. Check security group allows inbound on port 5432

3. Verify credentials in `.env`

### "Database doesn't exist" Error

**Solution:**
1. Verify database names are correct in AWS RDS
2. Manually create databases if needed:
   ```bash
   python manage.py setup_shards --create-dbs
   ```

### "No user_id in sharding context" Error

**Solution:**
Always set context before querying:

```python
from api.sharding import ShardingContext

ShardingContext.set_user_id(user_id)
try:
    order = Order.objects.filter(user_id=user_id).first()
finally:
    ShardingContext.clear()
```

## Next Steps

1. **Monitoring:** Set up CloudWatch alarms for RDS instances
2. **Backups:** Enable automated backups in RDS console
3. **Performance:** Use AWS Performance Insights to monitor queries
4. **Scaling:** Add more shards if needed (see SHARDING.md)

## Documentation

- Full documentation: See `SHARDING.md`
- Code examples: See `api/examples.py`
- Tests: See `api/test_sharding.py`

## Support

For issues or questions:
1. Check `SHARDING.md` troubleshooting section
2. Review RDS CloudWatch logs
3. Test connections with: `python manage.py setup_shards --check`
