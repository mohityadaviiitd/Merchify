# Database Sharding Implementation Summary

## What's Been Implemented

Your Merchify backend now has a complete database sharding infrastructure with support for 2 shards and 1 read replica per shard. Here's what was set up:

### Core Components

#### 1. **Sharding Utilities** (`api/sharding.py`)
- `ShardingContext`: Thread-local context manager for tracking current user's shard
- `get_shard_id()`: Determines shard ID using modulo strategy (user_id % 2)
- `get_shard_name()`: Gets the database alias for a user's shard
- `get_replica_name()`: Gets the read replica database alias
- Helper functions for shard distribution tracking

#### 2. **Database Router** (`api/routers.py`)
- `ShardRouter`: Custom Django database router that:
  - Routes **writes** to primary shards only
  - Routes **reads** to read replicas for scalability
  - Enforces cross-shard constraints
  - Enables migrations on all shards

#### 3. **Middleware** (`api/middleware.py`)
- `ShardingMiddleware`: Automatically sets sharding context for authenticated requests
  - Extracts user_id from request.user
  - Sets ShardingContext at request start
  - Clears context at request end
  - Prevents context leakage between requests

#### 4. **Settings Configuration** (`merchify_backend/settings.py`)
- Added 5 database configurations:
  - `default`: For auth/system tables
  - `shard_0`: Primary for even user IDs
  - `shard_0_replica`: Read replica for shard 0
  - `shard_1`: Primary for odd user IDs
  - `shard_1_replica`: Read replica for shard 1
- Registered `ShardRouter` in `DATABASE_ROUTERS`
- Registered `ShardingMiddleware` in `MIDDLEWARE`

#### 5. **Utility Functions** (`api/utils.py`)
- Decorators: `@require_shard_context`, `@with_shard_context`
- Helper functions for shard operations
- Cross-shard access validation
- `ShardAwareQuerySet` for simplified queries

#### 6. **Management Command** (`api/management/commands/setup_shards.py`)
- `python manage.py setup_shards`: Initial setup
- `--check`: Verify all shard connections
- `--migrate`: Run migrations on all shards
- `--stats`: Show shard configuration
- `--create-dbs`: Create local PostgreSQL databases

#### 7. **Examples** (`api/examples.py`)
- Real-world examples of using sharding in views
- ViewSet implementations with sharding
- Order and Cart management examples
- Cross-shard aggregation patterns

#### 8. **Comprehensive Tests** (`api/test_sharding.py`)
- Unit tests for sharding utilities
- Context management tests
- Router behavior tests
- Middleware tests
- Model-level sharding tests
- Cross-shard constraint tests
- Distribution tests

### Documentation Files

#### 1. **SHARDING.md** - Complete Reference
- Architecture overview with diagrams
- Sharding strategy explanation
- AWS RDS setup steps
- Usage examples in views
- Management commands documentation
- Monitoring and troubleshooting guide
- Migration strategies
- Performance tips

#### 2. **SHARDING_QUICKSTART.md** - Quick Setup Guide
- Step-by-step AWS RDS setup (10 minutes)
- Environment variable configuration
- Migration steps
- Testing instructions
- Quick troubleshooting

#### 3. **SHARDING_LOCAL_SETUP.md** - Local Development
- Docker Compose setup for all 5 databases
- PgAdmin access for local database management
- Testing with local databases
- Debugging and monitoring
- Port mappings and connection strings

#### 4. **.env.sharding.example** - Environment Configuration Template
- All required environment variables
- Placeholders for your AWS RDS endpoints
- AWS S3, Stripe, and CORS configurations

#### 5. **docker-compose.sharding.yml** - Docker Setup
- 5 PostgreSQL services (default + 2 shards + 2 replicas)
- PgAdmin container for database management
- Health checks for all services
- Volume management for persistent data

## Architecture

```
┌──────────────────────────────────────────────────────┐
│              Django REST API                         │
│                                                      │
│  ┌────────────────────────────────────────────────┐  │
│  │     ShardingMiddleware                         │  │
│  │     (Sets user_id in ShardingContext)          │  │
│  └────────────────┬─────────────────────────────┘  │
│                   │                                 │
│  ┌────────────────▼─────────────────────────────┐  │
│  │     ShardRouter                              │  │
│  │     (Routes queries to correct shard)        │  │
│  └────────────────┬─────────────────────────────┘  │
└─────────────────┼──────────────────────────────────┘
                  │
        ┌─────────┴──────────┐
        │                    │
   ┌────▼──────┐      ┌──────▼────┐
   │ SHARD 0    │      │ SHARD 1    │
   ├────────────┤      ├────────────┤
   │Primary (RW)│      │Primary (RW)│
   │  → Writes  │      │  → Writes  │
   │            │      │            │
   │Replica (R) │      │Replica (R) │
   │ → Reads    │      │ → Reads    │
   └────────────┘      └────────────┘

Shard Assignment:
- Shard 0: user_id % 2 == 0 (even IDs)
- Shard 1: user_id % 2 == 1 (odd IDs)
```

## Database Distribution

For 1000 users:
- Shard 0: ~500 users (even IDs)
- Shard 1: ~500 users (odd IDs)

This ensures balanced distribution as the system scales.

## Key Features

✅ **Automatic Shard Selection**: ShardingMiddleware automatically routes requests to the correct shard based on user_id

✅ **Read Scaling**: Read operations automatically use read replicas, scaling read capacity

✅ **Write Safety**: All writes go to primary shards only, ensuring data consistency

✅ **Thread-Safe Context**: Uses thread-local storage to prevent context leakage between requests

✅ **Easy Integration**: Minimal changes needed to existing views - just use normal ORM operations

✅ **Comprehensive Testing**: Full test suite for all sharding components

✅ **Local Development**: Docker Compose setup lets you test sharding locally before AWS

✅ **Production Ready**: Complete AWS RDS setup guide and best practices

## Usage Patterns

### In Django Views
```python
@api_view(['GET'])
def get_orders(request):
    # ShardingMiddleware automatically sets context
    orders = Order.objects.filter(user=request.user)
    return Response(orders)
```

### In Management Commands
```python
ShardingContext.set_user_id(user_id)
try:
    orders = Order.objects.filter(user_id=user_id)
finally:
    ShardingContext.clear()
```

### With Context Manager
```python
with with_shard_context(user_id):
    order = Order.objects.create(user_id=user_id, ...)
```

## Setup Steps

### Option 1: Local Testing with Docker (Recommended First)

1. `docker-compose -f docker-compose.sharding.yml up -d`
2. Create `.env.local` with localhost settings
3. `python manage.py setup_shards --migrate`
4. `python manage.py test api.test_sharding`

### Option 2: AWS RDS Production Setup

1. Create 4 RDS instances (2 primary + 2 replicas)
2. Create `.env` with RDS endpoints
3. `python manage.py setup_shards --check`
4. `python manage.py setup_shards --migrate`

## Testing

```bash
# Run all sharding tests
python manage.py test api.test_sharding -v 2

# Check shard connections
python manage.py setup_shards --check

# View shard configuration
python manage.py setup_shards --stats
```

## Performance Impact

### Before Sharding
- All data in single database
- Single database becomes bottleneck
- Read/write contention increases with users
- Scaling limited by single server capacity

### After Sharding
- Data distributed across 2 databases
- 2x write capacity (writes go to separate shards)
- Read replicas handle read-heavy workloads
- Can scale horizontally by adding more shards

### Expected Benefits
- **2x write throughput** (2 shards)
- **Unlimited read scaling** (via replicas)
- **Lower latency** (data locality)
- **Independent failure domains** (one shard doesn't affect others)

## Migration Path

1. **Phase 1**: Deploy sharding code (no changes to databases yet)
2. **Phase 2**: Set up AWS RDS instances
3. **Phase 3**: Test with Docker locally
4. **Phase 4**: Point to AWS RDS and run migrations
5. **Phase 5**: Monitor and optimize

## Important Notes

⚠️ **Cross-Shard Queries**: Not supported directly. Always query within a user's shard.

⚠️ **Data Integrity**: Cross-shard foreign keys are prevented by the router.

⚠️ **Migrations**: Must be run on all shards. Use `python manage.py setup_shards --migrate`.

✅ **Thread Safety**: ShardingContext is thread-local and safe for concurrent requests.

✅ **Backwards Compatible**: Existing code works with minimal or no changes.

## File Structure

```
Merchify/
├── api/
│   ├── sharding.py           # Core sharding utilities
│   ├── routers.py            # Database router
│   ├── middleware.py         # Request middleware
│   ├── utils.py              # Helper functions & decorators
│   ├── examples.py           # Usage examples
│   ├── test_sharding.py      # Comprehensive test suite
│   ├── models.py             # (existing models)
│   ├── views.py              # (existing views)
│   └── management/
│       └── commands/
│           └── setup_shards.py     # Setup command
├── merchify_backend/
│   └── settings.py           # (updated with sharding config)
├── docker-compose.sharding.yml    # Local development setup
├── SHARDING.md               # Complete reference guide
├── SHARDING_QUICKSTART.md    # Quick setup for AWS
├── SHARDING_LOCAL_SETUP.md   # Local development guide
└── .env.sharding.example     # Environment template
```

## Next Steps

1. **Choose Setup Method**:
   - For local testing: Follow `SHARDING_LOCAL_SETUP.md`
   - For AWS production: Follow `SHARDING_QUICKSTART.md`

2. **Test Locally First**:
   - `docker-compose -f docker-compose.sharding.yml up -d`
   - `python manage.py test api.test_sharding`

3. **Deploy to AWS**:
   - Create RDS instances following `SHARDING_QUICKSTART.md`
   - Update `.env` with RDS endpoints
   - Run migrations on all shards

4. **Monitor Production**:
   - Set up CloudWatch alarms
   - Monitor query performance
   - Track shard distribution

## Support & Resources

- **Full Guide**: Read [SHARDING.md](SHARDING.md)
- **Quick Setup**: Read [SHARDING_QUICKSTART.md](SHARDING_QUICKSTART.md)
- **Local Dev**: Read [SHARDING_LOCAL_SETUP.md](SHARDING_LOCAL_SETUP.md)
- **Code Examples**: See `api/examples.py`
- **Tests**: See `api/test_sharding.py`

## Questions?

Refer to the troubleshooting section in [SHARDING.md](SHARDING.md) or the local setup guide in [SHARDING_LOCAL_SETUP.md](SHARDING_LOCAL_SETUP.md).
