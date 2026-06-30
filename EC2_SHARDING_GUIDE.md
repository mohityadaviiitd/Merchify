# EC2-Based Sharding and Replica Guide for Merchify

This guide shows how to mimic the sharding setup on an EC2 instance when RDS free tier is not available.

You do not need to change application code. The app already reads shard and replica connection details from environment variables in [merchify_backend/settings.py](merchify_backend/settings.py), so the only change is to point those variables to your EC2 host and ports.

## What you will create

On one EC2 instance, you can run:

- 1 PostgreSQL instance for the default database
- 1 PostgreSQL primary for shard 0
- 1 PostgreSQL replica for shard 0
- 1 PostgreSQL primary for shard 1
- 1 PostgreSQL replica for shard 1

This is enough to test the app's shard routing behavior in a realistic way.

---

## 1. Launch an EC2 instance

Use any Ubuntu 22.04/24.04 or Amazon Linux 2023 instance.

Recommended settings:
- Instance type: t3.small or larger
- Storage: 20 GB+
- Security group: allow inbound TCP on:
  - 22 from your IP
  - 5432, 5433, 5434, 5435, 5436 from your IP (or from your security group)

If you are using a public IP, note that it may change unless you attach an Elastic IP.

---

## 2. Connect to the EC2 instance

```bash
ssh -i your-key.pem ubuntu@YOUR_EC2_PUBLIC_IP
```

If you are using Amazon Linux, replace `ubuntu` with `ec2-user`.

---

## 3. Install PostgreSQL

For Ubuntu:

```bash
sudo apt update
sudo apt install -y postgresql postgresql-contrib
```

For Amazon Linux:

```bash
sudo dnf install -y postgresql-server postgresql-contrib
sudo postgresql-setup initdb
sudo systemctl enable --now postgresql
```

---

## 4. Create the PostgreSQL clusters

The simplest learning setup is to run separate PostgreSQL instances on different ports.

### Port plan

- Default DB: 5432
- Shard 0 primary: 5433
- Shard 0 replica: 5434
- Shard 1 primary: 5435
- Shard 1 replica: 5436

### Create the main cluster for the default DB

Ubuntu usually already has a cluster on port 5432. You can reuse it for the default database.

```bash
sudo -u postgres psql <<'SQL'
CREATE USER merchifyuser WITH PASSWORD 'strongpassword';
CREATE DATABASE merchify OWNER merchifyuser;
ALTER USER merchifyuser WITH SUPERUSER;
SQL
```

### Create the shard databases

```bash
sudo -u postgres psql <<'SQL'
CREATE DATABASE merchify_shard_0 OWNER merchifyuser;
CREATE DATABASE merchify_shard_1 OWNER merchifyuser;
SQL
```

---

## 5. Create a primary-replica pair for shard 0

This example creates a real streaming replica for shard 0.

### Step A: Configure the primary

Edit the primary configuration:

```bash
sudo nano /etc/postgresql/15/main/postgresql.conf
```

Add or update:

```conf
listen_addresses = '*'
wal_level = replica
max_wal_senders = 10
wal_keep_size = 64
archive_mode = off
```

Save and restart:

```bash
sudo systemctl restart postgresql
```

### Step B: Allow replica to connect

Edit the client authentication rules:

```bash
sudo nano /etc/postgresql/15/main/pg_hba.conf
```

Add this line at the end:

```conf
host replication replicator 0.0.0.0/0 scram-sha-256
```

Then create the replication user:

```bash
sudo -u postgres psql <<'SQL'
CREATE ROLE replicator WITH REPLICATION LOGIN PASSWORD 'replicatorpass';
SQL
```

### Step C: Create the replica

On the same EC2 instance, create a new data directory for the replica:

```bash
sudo mkdir -p /var/lib/postgresql/15/replica0
sudo chown -R postgres:postgres /var/lib/postgresql/15/replica0
```

Run the base backup:

```bash
sudo -u postgres pg_basebackup -D /var/lib/postgresql/15/replica0 -Fp -X stream -R -S replica0 -C -h 127.0.0.1 -p 5432 -U replicator
```

Create a recovery file:

```bash
sudo sh -c 'echo "primary_conninfo = ''user=replicator password=replicatorpass host=127.0.0.1 port=5432''" > /var/lib/postgresql/15/replica0/postgresql.auto.conf'
sudo sh -c 'touch /var/lib/postgresql/15/replica0/standby.signal'
sudo chown -R postgres:postgres /var/lib/postgresql/15/replica0
```

Start the replica:

```bash
sudo -u postgres pg_ctl -D /var/lib/postgresql/15/replica0 -l /var/log/postgresql/replica0.log start
```

You now have a replica that can be reached on the same host using a different port if you configure it separately. For a learning setup, the easiest path is to keep the replica on the same EC2 machine and point the app to the replica's host and port.

> If you want a more straightforward setup, you can skip full replication and simply use a second PostgreSQL server instance on a different port. That is enough for learning and testing the app’s routing.

---

## 6. Repeat the same pattern for shard 1

Repeat the same process for shard 1, using a second replica and a different port.

Suggested mapping:

- Shard 0 primary: host = EC2 IP, port = 5433
- Shard 0 replica: host = EC2 IP, port = 5434
- Shard 1 primary: host = EC2 IP, port = 5435
- Shard 1 replica: host = EC2 IP, port = 5436

---

## 7. Update the app environment variables

In your project, update the environment values so the app points to the EC2 instance.

Example:

```env
POSTGRES_DB=merchify
POSTGRES_USER=merchifyuser
POSTGRES_PASSWORD=strongpassword
DB_HOST=YOUR_EC2_PUBLIC_IP
DB_PORT=5432

SHARD_0_DB=merchify_shard_0
SHARD_0_USER=merchifyuser
SHARD_0_PASSWORD=strongpassword
SHARD_0_HOST=YOUR_EC2_PUBLIC_IP
SHARD_0_PORT=5433

SHARD_0_REPLICA_DB=merchify_shard_0
SHARD_0_REPLICA_USER=merchifyuser
SHARD_0_REPLICA_PASSWORD=strongpassword
SHARD_0_REPLICA_HOST=YOUR_EC2_PUBLIC_IP
SHARD_0_REPLICA_PORT=5434

SHARD_1_DB=merchify_shard_1
SHARD_1_USER=merchifyuser
SHARD_1_PASSWORD=strongpassword
SHARD_1_HOST=YOUR_EC2_PUBLIC_IP
SHARD_1_PORT=5435

SHARD_1_REPLICA_DB=merchify_shard_1
SHARD_1_REPLICA_USER=merchifyuser
SHARD_1_REPLICA_PASSWORD=strongpassword
SHARD_1_REPLICA_HOST=YOUR_EC2_PUBLIC_IP
SHARD_1_REPLICA_PORT=5436
```

No other code changes are required.

---

## 8. Run the setup commands

From the project root:

```bash
python manage.py setup_shards --check
python manage.py setup_shards --migrate
```

If needed, run migrations per database:

```bash
python manage.py migrate --database=shard_0
python manage.py migrate --database=shard_1
```

---

## 9. Test the behavior

You can verify that user IDs are routed to different shards:

```bash
python manage.py shell
```

```python
from api.sharding import get_shard_name, ShardingContext
print(get_shard_name(1))
print(get_shard_name(2))
```

You should see:
- odd user IDs → shard 1
- even user IDs → shard 0

---

## 10. Useful troubleshooting tips

### Check PostgreSQL status

```bash
sudo systemctl status postgresql
```

### Check connections

```bash
sudo -u postgres psql -c "SELECT version();"
```

### Check if the replica is streaming

```bash
sudo -u postgres psql -c "SELECT * FROM pg_stat_wal_receiver;"
```

### Test from your local machine

```bash
psql -h YOUR_EC2_PUBLIC_IP -p 5433 -U merchifyuser -d merchify_shard_0
```

---

## Recommended learning path

If you are just learning, the easiest path is:

1. Start with one EC2 instance
2. Use one host and different ports for each database endpoint
3. Point the env variables to those ports
4. Verify sharding and replica routing with simple inserts and reads

That gives you a realistic environment without needing RDS.
