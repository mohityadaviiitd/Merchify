# Local Development Setup for Sharding

## Prerequisites

- Docker Desktop (for Windows)
- Python 3.9+
- Virtual environment activated

## Quick Start (5 minutes)

### 1. Start Docker Containers

```bash
# Start all PostgreSQL shards + PgAdmin
docker-compose -f docker-compose.sharding.yml up -d

# Verify all containers are running
docker-compose -f docker-compose.sharding.yml ps

# Expected output:
# NAME                           STATUS
# merchify_default               running
# merchify_shard_0               running
# merchify_shard_0_replica       running
# merchify_shard_1               running
# merchify_shard_1_replica       running
# merchify_pgadmin               running
```

### 2. Create Local .env File

```bash
# Copy the sharding example config
cp .env.sharding.example .env.local

# Or manually create .env.local with:
cat > .env.local << 'EOF'
# Django
DEBUG=True
SECRET_KEY=django-insecure-dev-key-change-in-production

# Default Database
POSTGRES_DB=merchify
POSTGRES_USER=merchifyuser
POSTGRES_PASSWORD=strongpassword
DB_HOST=localhost
DB_PORT=5432

# Shard 0 - Primary
SHARD_0_DB=merchify_shard_0
SHARD_0_USER=merchifyuser
SHARD_0_PASSWORD=strongpassword
SHARD_0_HOST=localhost
SHARD_0_PORT=5433

# Shard 0 - Read Replica
SHARD_0_REPLICA_DB=merchify_shard_0
SHARD_0_REPLICA_USER=merchifyuser
SHARD_0_REPLICA_PASSWORD=strongpassword
SHARD_0_REPLICA_HOST=localhost
SHARD_0_REPLICA_PORT=5434

# Shard 1 - Primary
SHARD_1_DB=merchify_shard_1
SHARD_1_USER=merchifyuser
SHARD_1_PASSWORD=strongpassword
SHARD_1_HOST=localhost
SHARD_1_PORT=5435

# Shard 1 - Read Replica
SHARD_1_REPLICA_DB=merchify_shard_1
SHARD_1_REPLICA_USER=merchifyuser
SHARD_1_REPLICA_PASSWORD=strongpassword
SHARD_1_REPLICA_HOST=localhost
SHARD_1_REPLICA_PORT=5436

# AWS (optional, leave blank for local dev)
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
AWS_STORAGE_BUCKET_NAME=

# CORS
CORS_ALLOWED_ORIGINS=http://localhost:3000,http://localhost:8000

# Stripe (optional)
STRIPE_SECRET_KEY=
STRIPE_PUBLISHABLE_KEY=
STRIPE_WEBHOOK_SECRET=

# Frontend
FRONTEND_BASE_URL=http://localhost:3000
EOF
```

### 3. Run Migrations

```bash
# Activate virtual environment
backend_env\Scripts\Activate.ps1

# Check connections
python manage.py setup_shards --check

# Run all migrations
python manage.py setup_shards --migrate

# Or migrate individually
python manage.py migrate --database=shard_0
python manage.py migrate --database=shard_1
```

### 4. Create Admin User

```bash
python manage.py createsuperuser
```

### 5. Run Development Server

```bash
python manage.py runserver 0.0.0.0:8000
```

Server is now running at: `http://localhost:8000`

## Testing Sharding Locally

### Run Sharding Tests

```bash
python manage.py test api.test_sharding -v 2
```

### Create Test Users and Orders

```bash
python manage.py shell

# In the Python shell:
from django.contrib.auth.models import User
from api.models import Order
from api.sharding import ShardingContext, get_shard_name

# Create user 1 (odd - goes to shard_1)
user1 = User.objects.create_user(username='user1', password='pass')
print(f"User {user1.id} → Shard: {get_shard_name(user1.id)}")

# Create user 2 (even - goes to shard_0)
user2 = User.objects.create_user(username='user2', password='pass')
print(f"User {user2.id} → Shard: {get_shard_name(user2.id)}")

# Create order for user 1
ShardingContext.set_user_id(user1.id)
order1 = Order.objects.create(user=user1, total_price=100.00, status='pending')
print(f"Order {order1.id} created for user {user1.id}")

# Create order for user 2
ShardingContext.set_user_id(user2.id)
order2 = Order.objects.create(user=user2, total_price=200.00, status='pending')
print(f"Order {order2.id} created for user {user2.id}")

ShardingContext.clear()

# Verify orders are retrievable
ShardingContext.set_user_id(user1.id)
orders_user1 = Order.objects.filter(user=user1)
print(f"\nUser 1 orders: {list(orders_user1.values('id', 'total_price'))}")

ShardingContext.set_user_id(user2.id)
orders_user2 = Order.objects.filter(user=user2)
print(f"User 2 orders: {list(orders_user2.values('id', 'total_price'))}")

ShardingContext.clear()

exit()
```

## Accessing Databases Locally

### Using PgAdmin

1. Open browser: `http://localhost:5050`
2. Login:
   - Email: `admin@merchify.com`
   - Password: `admin`

3. Add servers:
   - Name: `Default`
   - Host: `postgres_default`
   - Port: `5432`
   - User: `merchifyuser`
   - Password: `strongpassword`

4. Repeat for:
   - Shard 0: Host `postgres_shard_0`, Port `5432`
   - Shard 0 Replica: Host `postgres_shard_0_replica`, Port `5432`
   - Shard 1: Host `postgres_shard_1`, Port `5432`
   - Shard 1 Replica: Host `postgres_shard_1_replica`, Port `5432`

### Using psql CLI

```bash
# Connect to default database
psql -h localhost -U merchifyuser -d merchify -W
# Password: strongpassword

# Connect to shard 0
psql -h localhost -p 5433 -U merchifyuser -d merchify_shard_0 -W

# Connect to shard 1
psql -h localhost -p 5435 -U merchifyuser -d merchify_shard_1 -W
```

## Monitoring

### Docker Logs

```bash
# View all logs
docker-compose -f docker-compose.sharding.yml logs -f

# View specific service
docker-compose -f docker-compose.sharding.yml logs -f postgres_shard_0
```

### Database Activity

```bash
# In psql, run:
SELECT pid, usename, application_name, state 
FROM pg_stat_activity;
```

## Cleanup

### Stop Containers (keep data)

```bash
docker-compose -f docker-compose.sharding.yml stop
```

### Remove Containers and Data

```bash
docker-compose -f docker-compose.sharding.yml down -v
```

### Restart Clean

```bash
docker-compose -f docker-compose.sharding.yml down -v
docker-compose -f docker-compose.sharding.yml up -d
python manage.py setup_shards --migrate
```

## Troubleshooting

### "Port 5432 already in use"

```bash
# Find what's using the port
netstat -ano | findstr :5432

# Or use Docker to see port mappings
docker-compose -f docker-compose.sharding.yml ps
```

### Containers Won't Start

```bash
# Check logs
docker-compose -f docker-compose.sharding.yml logs

# Try removing and rebuilding
docker-compose -f docker-compose.sharding.yml down -v
docker-compose -f docker-compose.sharding.yml up -d
```

### Connection Refused

```bash
# Verify containers are running
docker ps | grep merchify

# Wait a bit longer (containers may still be starting)
# Check if they're healthy
docker-compose -f docker-compose.sharding.yml ps

# Check container logs
docker logs merchify_shard_0
```

## Next Steps

1. **Test API Endpoints:** Run your Django app and test orders through API
2. **Load Testing:** Use Locust or Apache Bench to test with multiple users
3. **Monitor Performance:** Watch database query times in Django Debug Toolbar
4. **Deploy to AWS:** Once working locally, follow SHARDING_QUICKSTART.md to deploy to AWS RDS

## Environment Variables for Different Setups

### Local Development (.env.local)
- DB_HOST: `localhost`
- SHARD_0_HOST: `localhost`
- Ports: 5432, 5433, 5434, 5435, 5436

### Docker (docker-compose)
- DB_HOST: `postgres_default`
- SHARD_0_HOST: `postgres_shard_0`
- Ports: 5432 (internal)

### AWS RDS (Production)
- DB_HOST: `your-db.xxxxx.rds.amazonaws.com`
- SHARD_0_HOST: `shard-0-primary.xxxxx.rds.amazonaws.com`
- Port: 5432 (for all)
