# Database Sharding Implementation Checklist

## Pre-Implementation

- [ ] Read `SHARDING.md` to understand the architecture
- [ ] Read `SHARDING_IMPLEMENTATION.md` for overview
- [ ] Decide on deployment approach (local testing first vs. direct to AWS)

## Installation & Configuration

### Step 1: Code Integration
- [ ] Verify all new files are created:
  - [ ] `api/sharding.py` - Sharding utilities
  - [ ] `api/routers.py` - Database router
  - [ ] `api/middleware.py` - Sharding middleware
  - [ ] `api/utils.py` - Helper functions
  - [ ] `api/examples.py` - Usage examples
  - [ ] `api/test_sharding.py` - Test suite
  - [ ] `api/management/commands/setup_shards.py` - Setup command

### Step 2: Settings Configuration
- [ ] Verify `merchify_backend/settings.py` is updated:
  - [ ] `DATABASES` contains 5 configurations (default + 4 shards)
  - [ ] `DATABASE_ROUTERS = ['api.routers.ShardRouter']` is set
  - [ ] `ShardingMiddleware` is added to `MIDDLEWARE`

### Step 3: Environment Configuration
- [ ] Copy `.env.sharding.example` to `.env` or `.env.local`
- [ ] Fill in database connection details:
  - [ ] Default database credentials
  - [ ] Shard 0 primary credentials
  - [ ] Shard 0 replica credentials
  - [ ] Shard 1 primary credentials
  - [ ] Shard 1 replica credentials

## Local Testing Setup

### Option A: Docker Compose (Recommended First)

- [ ] Install Docker Desktop
- [ ] Start databases: `docker-compose -f docker-compose.sharding.yml up -d`
- [ ] Verify all containers running: `docker-compose -f docker-compose.sharding.yml ps`
- [ ] Verify connections: `python manage.py setup_shards --check`
- [ ] Run migrations: `python manage.py setup_shards --migrate`

### Option B: Local PostgreSQL Instances

- [ ] Install PostgreSQL 13+ locally
- [ ] Create 5 databases manually
- [ ] Update `.env.local` with local connection details
- [ ] Run: `python manage.py setup_shards --check`
- [ ] Run: `python manage.py setup_shards --migrate`

## Testing

### Unit Tests
- [ ] Run sharding tests: `python manage.py test api.test_sharding -v 2`
- [ ] All tests should PASS
- [ ] Expected: ~20+ tests

### Manual Testing
- [ ] Create a test user: `python manage.py createsuperuser`
- [ ] Create test orders via shell:
  ```bash
  python manage.py shell
  # Create users and orders, verify they go to correct shards
  ```
- [ ] Test API endpoints with curl or Postman
- [ ] Verify orders are accessible via API

### Connection Tests
- [ ] `python manage.py setup_shards --check`
- [ ] Should show all 5 databases connected
- [ ] Expected output:
  ```
  ✓ default
  ✓ shard_0
  ✓ shard_0_replica
  ✓ shard_1
  ✓ shard_1_replica
  ```

## Verification

### Data Verification

- [ ] User 1 (odd) orders are in shard_1
- [ ] User 2 (even) orders are in shard_0
- [ ] User 3 (odd) orders are in shard_1
- [ ] User 4 (even) orders are in shard_0

You can verify this in PgAdmin by:
1. Connect to each shard database
2. Query: `SELECT * FROM api_order WHERE user_id = 1;`
3. Verify it only returns results in the correct shard

### Router Verification

- [ ] Run tests specifically for router: `python manage.py test api.test_sharding.ShardRouterTestCase -v 2`
- [ ] Verify writes go to primary: Test passes
- [ ] Verify reads go to replica: Test passes

### Middleware Verification

- [ ] Run middleware tests: `python manage.py test api.test_sharding.ShardingMiddlewareTestCase -v 2`
- [ ] Context is set for authenticated users: Test passes
- [ ] Context is cleared after request: Test passes

## Production AWS Setup

### RDS Instance Creation

- [ ] Create 4 RDS PostgreSQL instances:
  - [ ] shard-0-primary (on-demand)
  - [ ] shard-0-replica (read replica of primary)
  - [ ] shard-1-primary (on-demand)
  - [ ] shard-1-replica (read replica of primary)

### Security Configuration

- [ ] Configure security groups to allow port 5432 inbound
- [ ] Create database: `merchify_shard_0` on shard-0-primary
- [ ] Create database: `merchify_shard_1` on shard-1-primary
- [ ] Verify replication is working

### Environment Setup

- [ ] Update production `.env` with RDS endpoints:
  - [ ] SHARD_0_HOST=shard-0-primary.xxxxx.rds.amazonaws.com
  - [ ] SHARD_0_REPLICA_HOST=shard-0-replica.xxxxx.rds.amazonaws.com
  - [ ] SHARD_1_HOST=shard-1-primary.xxxxx.rds.amazonaws.com
  - [ ] SHARD_1_REPLICA_HOST=shard-1-replica.xxxxx.rds.amazonaws.com

### Deploy to AWS

- [ ] Deploy Django app to AWS (EC2/ECS/Lambda)
- [ ] Verify connection to RDS: `python manage.py setup_shards --check`
- [ ] Run migrations: `python manage.py setup_shards --migrate`
- [ ] Create admin user: `python manage.py createsuperuser`

### Monitoring Setup

- [ ] Enable CloudWatch for all RDS instances
- [ ] Set up alarms for:
  - [ ] High CPU usage (> 80%)
  - [ ] High connections (> 80% max)
  - [ ] Replication lag (> 1 second)
  - [ ] Database errors

## Post-Deployment

### Day 1 - Verification

- [ ] Monitor logs for errors
- [ ] Check database connection health
- [ ] Test a few orders through the API
- [ ] Verify orders are going to correct shards
- [ ] Check CloudWatch metrics

### Week 1 - Monitoring

- [ ] Monitor query performance
- [ ] Check for any slow queries
- [ ] Verify read replicas are being used
- [ ] Monitor shard distribution
- [ ] Check backup status

### Ongoing - Maintenance

- [ ] Monitor shard sizes
- [ ] Plan for future scaling (adding more shards)
- [ ] Review performance metrics monthly
- [ ] Update replica lag monitoring
- [ ] Test failover procedures

## Troubleshooting

### Connection Issues

- [ ] Verify database credentials in `.env`
- [ ] Check security groups allow port 5432
- [ ] Check database is running: `python manage.py setup_shards --check`
- [ ] Test connection manually: `psql -h HOST -U USER -d DB`

### Migration Issues

- [ ] Verify all databases are accessible
- [ ] Check for missing migrations: `python manage.py showmigrations`
- [ ] Run migrations manually per shard if needed:
  ```bash
  python manage.py migrate --database=shard_0
  python manage.py migrate --database=shard_1
  ```

### Sharding Logic Issues

- [ ] Verify ShardingContext is being set:
  ```bash
  python manage.py shell
  from api.sharding import ShardingContext, get_shard_name
  ShardingContext.set_user_id(42)
  print(get_shard_name(42))  # Should print 'shard_0'
  ```

- [ ] Check if middleware is being called:
  - Add print statement to middleware
  - Make authenticated request
  - Check logs for output

### Test Failures

- [ ] Ensure all databases are running
- [ ] Clear context between tests: `ShardingContext.clear()`
- [ ] Run individual test: `python manage.py test api.test_sharding.TestClassName -v 2`

## Documentation

- [ ] Read `SHARDING.md` for complete reference
- [ ] Share `SHARDING_QUICKSTART.md` with team
- [ ] Share `SHARDING_LOCAL_SETUP.md` for local development
- [ ] Update team wiki/documentation

## Code Review

- [ ] Code review of sharding implementation
- [ ] Verify no hardcoded database references
- [ ] Check error handling in router
- [ ] Review middleware for thread safety
- [ ] Verify test coverage (run with coverage)

## Performance Testing

- [ ] Load test with single user: 1000 requests/sec
- [ ] Load test with multiple users: 100 users × 10 requests each
- [ ] Monitor database CPU, memory, connections
- [ ] Measure query response times
- [ ] Identify any bottlenecks

## Scaling Preparation

- [ ] Document adding new shards (SHARDING.md has guide)
- [ ] Create runbook for shard failover
- [ ] Plan for data re-sharding if needed
- [ ] Set up monitoring for shard imbalance

## Final Checklist

- [ ] All code changes deployed
- [ ] All tests passing
- [ ] Databases verified working
- [ ] Monitoring in place
- [ ] Documentation updated
- [ ] Team trained on new system
- [ ] Backup strategy verified
- [ ] Disaster recovery plan created
- [ ] Performance baseline established
- [ ] Ready for production traffic

## Rollback Plan (If Needed)

- [ ] Single database backup taken
- [ ] Rollback procedure documented
- [ ] Database migration scripts created
- [ ] Team knows rollback steps

## Sign-Off

- [ ] Database Team Sign-Off: _______________
- [ ] DevOps Team Sign-Off: _______________
- [ ] Application Team Sign-Off: _______________
- [ ] Security Team Sign-Off: _______________

---

**Note**: This checklist ensures a smooth implementation. Each item should be verified before moving to the next phase. Address any issues before progressing.
