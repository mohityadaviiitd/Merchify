# Quick Verification Checklist

**After running this checklist, your sharding implementation will be verified as production-ready.**

---

## Pre-Test Setup (5 minutes)

- [ ] Ensure PostgreSQL is installed or Docker is running
- [ ] Verify all 7 core files exist:
  - [ ] `api/sharding.py`
  - [ ] `api/routers.py`
  - [ ] `api/middleware.py`
  - [ ] `api/utils.py`
  - [ ] `api/views.py` (with dashboard fix)
  - [ ] `api/models.py`
  - [ ] `merchify_backend/settings.py`

---

## Syntax Verification (2 minutes)

Run this command to verify no syntax errors:

```bash
python manage.py check
```

Expected result:
```
System check identified no issues (0 silenced).
```

- [ ] Command runs without errors
- [ ] 0 issues reported

---

## Unit Tests (5 minutes)

Run the comprehensive test suite:

```bash
python manage.py test api.test_sharding -v 2
```

Expected result: **All tests pass**

Tests covered:
- [ ] Shard ID calculation
- [ ] Shard name resolution
- [ ] Replica name resolution
- [ ] ShardingContext get/set/clear
- [ ] Database router read routing
- [ ] Database router write routing
- [ ] allow_migrate() functionality
- [ ] allow_relation() constraints
- [ ] Order distribution (even/odd users)

---

## Configuration Verification (2 minutes)

Check database configuration:

```bash
python manage.py setup_shards --check
```

Expected: Shows all 5 database connections

- [ ] default database: ✅
- [ ] shard_0 database: ✅
- [ ] shard_0_replica database: ✅
- [ ] shard_1 database: ✅
- [ ] shard_1_replica database: ✅

---

## Migrations Verification (3 minutes)

Run migrations on all shards:

```bash
python manage.py setup_shards --migrate
```

Expected: Migrations applied to all 5 databases

- [ ] Migrations run without errors
- [ ] All models created in all databases

---

## Dashboard Dashboard Stats Verification (2 minutes)

Test the fixed dashboard function:

```bash
python manage.py shell
```

```python
# In Django shell:
from api.models import Order
from api.sharding import SHARD_NAMES

# Check each shard
for shard in SHARD_NAMES:
    count = Order.objects.using(shard).count()
    print(f"{shard}: {count} orders")

# Exit shell
exit()
```

Expected: Shows order counts from all shards

- [ ] Script runs without errors
- [ ] Shows count for shard_0
- [ ] Shows count for shard_1

---

## Start Server (2 minutes)

Start the development server:

```bash
python manage.py runserver
```

Expected: Server starts on `http://127.0.0.1:8000/`

- [ ] No errors on startup
- [ ] Server running and accepting requests
- [ ] Middleware initialized

---

## API Testing (10 minutes)

### Register a User

```bash
POST http://localhost:8000/api/register/
Content-Type: application/json

{
  "username": "testuser1",
  "password": "testpass123",
  "email": "test@example.com"
}
```

Expected: User created

- [ ] Status 201 Created
- [ ] User ID returned (let's say 5)

### Check Shard Assignment

User 5: 5 % 2 = 1 → shard_1 ✅

```bash
python manage.py shell
```

```python
from django.contrib.auth.models import User
from api.models import Cart

user = User.objects.get(username="testuser1")
print(f"User ID: {user.id}, Shard: {user.id % 2}")

# Try to create a cart (should go to shard_1)
from api.sharding import ShardingContext

ShardingContext.set_user_id(user.id)
# cart = Cart.objects.create(user=user)
# Should be created in shard_1
ShardingContext.clear()
```

- [ ] User ID verified
- [ ] Shard assignment correct (id % 2)

### Test Cart Operations

```bash
# Login
POST http://localhost:8000/api/login/
{
  "username": "testuser1",
  "password": "testpass123"
}

# Copy the token from response

# Get cart
GET http://localhost:8000/api/cart/my-cart/
Authorization: Token YOUR_TOKEN_HERE

# Expected: Empty cart (first time)
```

- [ ] Login successful
- [ ] Cart retrieved
- [ ] Proper shard used

### Test Admin Dashboard

```bash
# Create a staff user first
python manage.py shell
```

```python
from django.contrib.auth.models import User
admin = User.objects.create_user(
    username='admin',
    password='admin123',
    is_staff=True
)
exit()
```

```bash
# Login as admin
POST http://localhost:8000/api/login/
{
  "username": "admin",
  "password": "admin123"
}

# Copy token

# Get dashboard stats
GET http://localhost:8000/api/dashboard-stats/
Authorization: Token YOUR_TOKEN_HERE

# Expected: Statistics with data from all shards
```

- [ ] Admin login successful
- [ ] Dashboard stats endpoint responds
- [ ] Stats show data (not all zeros)
- [ ] No errors in response

---

## Docker Local Testing (15 minutes)

Optional: Test with full Docker Compose setup

```bash
# Start all databases
docker-compose -f docker-compose.sharding.yml up -d

# Verify containers running
docker ps

# Check logs
docker-compose -f docker-compose.sharding.yml logs -f

# Stop all
docker-compose -f docker-compose.sharding.yml down
```

- [ ] All 5 PostgreSQL containers running
- [ ] PgAdmin accessible at http://localhost:5050
- [ ] All databases created
- [ ] No connection errors

---

## Production Readiness Sign-Off

After completing all checks above, initial these items:

**Code Quality**
- [ ] All syntax verified (0 errors)
- [ ] All imports working
- [ ] No circular dependencies
- [ ] Proper error handling

**Database Configuration**
- [ ] 5 databases configured
- [ ] Router registered
- [ ] Middleware configured
- [ ] Environment variables supported

**API Endpoints**
- [ ] Cart operations working
- [ ] Order operations working
- [ ] Dashboard stats working
- [ ] Webhook compatible

**Testing**
- [ ] Unit tests pass
- [ ] Configuration verified
- [ ] Migrations apply
- [ ] API endpoints respond

**Documentation**
- [ ] 6 guides available
- [ ] Code examples provided
- [ ] Deployment checklist ready
- [ ] Quick start available

---

## Final Sign-Off

```
Date: _______________
Tested By: _______________
Status: ☐ READY FOR PRODUCTION

Comments:
_________________________________
_________________________________
_________________________________
```

---

## Troubleshooting

### Issue: "shard_0 database does not exist"

**Fix**: Run migrations
```bash
python manage.py setup_shards --migrate
```

### Issue: "No module named 'api.sharding'"

**Fix**: Verify file exists
```bash
ls api/sharding.py
python manage.py check
```

### Issue: Dashboard shows all zeros

**Fix**: Verify fix was applied
```bash
grep -n "SHARD_NAMES" api/views.py
# Should show SHARD_NAMES import
```

### Issue: Orders not being created

**Fix**: Check ShardingContext
```bash
python manage.py shell
from api.sharding import ShardingContext
ShardingContext.set_user_id(1)
print(ShardingContext.get_user_id())  # Should print 1
```

---

## Next Steps After Verification

1. **Deploy to AWS** (30 minutes)
   - Follow SHARDING_QUICKSTART.md
   - Create 5 RDS PostgreSQL databases
   - Update environment variables

2. **Monitor Production** (Ongoing)
   - Set up CloudWatch alerts
   - Monitor database connections per shard
   - Track query performance
   - Monitor cross-shard lookups

3. **Load Test** (Optional)
   - Create 1000+ test users
   - Verify even distribution
   - Monitor performance
   - Identify bottlenecks

---

**Verification Status**: Ready to begin testing  
**Last Updated**: 2026-06-30
