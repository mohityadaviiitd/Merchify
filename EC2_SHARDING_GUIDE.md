# EC2-Based Sharding and Replica Guide for Merchify

This guide is written for PostgreSQL 16 on an EC2 instance and shows how to expose the same shard and replica endpoints that your Django app expects.

You do not need to change application code. The app already reads shard and replica connection details from environment variables in [merchify_backend/settings.py](merchify_backend/settings.py), so the only change is to point those variables to your EC2 host and ports.

## What you will create

On one EC2 instance, you can create:

- 1 PostgreSQL cluster for the default database on port 5432
- 1 PostgreSQL cluster for shard 0 on port 5433
- 1 PostgreSQL cluster for shard 0 replica on port 5434
- 1 PostgreSQL cluster for shard 1 on port 5435
- 1 PostgreSQL cluster for shard 1 replica on port 5436

This is enough to test the app’s shard routing behavior in a realistic way.

---

## 1. Launch the EC2 instance

Use an Ubuntu 22.04/24.04 instance or any Linux distribution where PostgreSQL 16 is available.

Recommended settings:
- Instance type: t3.small or larger
- Storage: 20 GB+
- Security group: allow inbound TCP on:
  - 22 from your IP
  - 5432, 5433, 5434, 5435, 5436 from your IP or from your security group

If you use a public IP, attach an Elastic IP if you want it to remain stable.

---

## 2. Connect to the instance

```bash
ssh -i your-key.pem ubuntu@YOUR_EC2_PUBLIC_IP
```

If you use Amazon Linux, replace `ubuntu` with `ec2-user`.

---

## 3. Install PostgreSQL 16

On Ubuntu/Debian:

```bash
sudo apt update
sudo apt install -y wget gnupg lsb-release
sudo sh -c 'echo "deb http://apt.postgresql.org/pub/repos/apt $(lsb_release -cs)-pgdg main" > /etc/apt/sources.list.d/pgdg.list'
wget --quiet -O - https://www.postgresql.org/media/keys/ACCC4CF8.asc | sudo apt-key add -
sudo apt update
sudo apt install -y postgresql-16 postgresql-client-16
```

Verify the version:

```bash
psql --version
```

You should see PostgreSQL 16.x.

---

## 4. Configure the EC2 firewall and security group

### Security group

In AWS, open these inbound TCP ports:
- 22
- 5432
- 5433
- 5434
- 5435
- 5436

### Ubuntu firewall

If UFW is enabled:

```bash
sudo ufw allow 22/tcp
sudo ufw allow 5432/tcp
sudo ufw allow 5433/tcp
sudo ufw allow 5434/tcp
sudo ufw allow 5435/tcp
sudo ufw allow 5436/tcp
sudo ufw reload
```

---

## 5. Create PostgreSQL clusters on the required ports

The easiest learning setup is to use separate PostgreSQL clusters on different ports.

### Check the current cluster

```bash
sudo pg_lsclusters
```

You will usually see a default cluster on port 5432.

### Create additional clusters for shards and replicas

Run these commands:

```bash
sudo pg_createcluster 16 shard0 --start --port 5433
sudo pg_createcluster 16 shard0_replica --start --port 5434
sudo pg_createcluster 16 shard1 --start --port 5435
sudo pg_createcluster 16 shard1_replica --start --port 5436
```

Verify them:

```bash
sudo pg_lsclusters
```

You should now have clusters listening on ports 5432, 5433, 5434, 5435, and 5436.

---

## 6. Make the clusters listen on all interfaces

Each cluster uses its own configuration file.

For each cluster, update the config:

```bash
sudo sed -i "s/^#listen_addresses = 'localhost'/listen_addresses = '*' /" /etc/postgresql/16/main/postgresql.conf
sudo sed -i "s/^#listen_addresses = 'localhost'/listen_addresses = '*' /" /etc/postgresql/16/shard0/postgresql.conf
sudo sed -i "s/^#listen_addresses = 'localhost'/listen_addresses = '*' /" /etc/postgresql/16/shard0_replica/postgresql.conf
sudo sed -i "s/^#listen_addresses = 'localhost'/listen_addresses = '*' /" /etc/postgresql/16/shard1/postgresql.conf
sudo sed -i "s/^#listen_addresses = 'localhost'/listen_addresses = '*' /" /etc/postgresql/16/shard1_replica/postgresql.conf
```

If your file uses a different formatting, open the file and ensure the line is:

```conf
listen_addresses = '*'
```

Restart the clusters:

```bash
sudo pg_ctlcluster 16 main restart
sudo pg_ctlcluster 16 shard0 restart
sudo pg_ctlcluster 16 shard0_replica restart
sudo pg_ctlcluster 16 shard1 restart
sudo pg_ctlcluster 16 shard1_replica restart
```

---

## 7. Allow remote connections

Edit the host-based authentication file for each cluster if needed.

```bash
sudo nano /etc/postgresql/16/main/pg_hba.conf
```

Add this line at the end:

```conf
host all all 0.0.0.0/0 scram-sha-256
```

Repeat the same change for the other cluster config files if you want to connect from outside the instance.

Then restart the clusters again:

```bash
sudo pg_ctlcluster 16 main restart
sudo pg_ctlcluster 16 shard0 restart
sudo pg_ctlcluster 16 shard0_replica restart
sudo pg_ctlcluster 16 shard1 restart
sudo pg_ctlcluster 16 shard1_replica restart
```

---

## 8. Create the databases and user

Create a user and the databases for each endpoint.

```bash
sudo -u postgres psql <<'SQL'
CREATE USER merchifyuser WITH PASSWORD 'strongpassword';
ALTER USER merchifyuser WITH SUPERUSER;
CREATE DATABASE merchify OWNER merchifyuser;
CREATE DATABASE merchify_shard_0 OWNER merchifyuser;
CREATE DATABASE merchify_shard_1 OWNER merchifyuser;
SQL
```

You can also create them per port if you want to be explicit:

```bash
sudo -u postgres psql -p 5432 -c "CREATE DATABASE merchify OWNER merchifyuser;"
sudo -u postgres psql -p 5433 -c "CREATE DATABASE merchify_shard_0 OWNER merchifyuser;"
sudo -u postgres psql -p 5434 -c "CREATE DATABASE merchify_shard_0 OWNER merchifyuser;"
sudo -u postgres psql -p 5435 -c "CREATE DATABASE merchify_shard_1 OWNER merchifyuser;"
sudo -u postgres psql -p 5436 -c "CREATE DATABASE merchify_shard_1 OWNER merchifyuser;"
```

If `merchifyuser` already exists, you can skip the create user step.

---

## 9. Verify the ports from the EC2 instance

Test each port locally:

```bash
psql -h 127.0.0.1 -p 5432 -U merchifyuser -d merchify -c "SELECT current_database();"
psql -h 127.0.0.1 -p 5433 -U merchifyuser -d merchify_shard_0 -c "SELECT current_database();"
psql -h 127.0.0.1 -p 5434 -U merchifyuser -d merchify_shard_0 -c "SELECT current_database();"
psql -h 127.0.0.1 -p 5435 -U merchifyuser -d merchify_shard_1 -c "SELECT current_database();"
psql -h 127.0.0.1 -p 5436 -U merchifyuser -d merchify_shard_1 -c "SELECT current_database();"
```

You should get a successful connection for each port.

---

## 10. Update the application environment variables

In your project, point the app to the EC2 host and these ports.

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

## 11. Run the Django setup commands

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

## 12. Test the sharding behavior

```bash
python manage.py shell
```

```python
from api.sharding import get_shard_name
print(get_shard_name(1))
print(get_shard_name(2))
```

You should see:
- odd user IDs → shard 1
- even user IDs → shard 0

---

## 13. Useful troubleshooting commands

### Check PostgreSQL status

```bash
sudo pg_lsclusters
sudo systemctl status postgresql
```

### Check listening ports

```bash
ss -ltnp | grep postgres
```

### Test from your local machine

```bash
psql -h YOUR_EC2_PUBLIC_IP -p 5433 -U merchifyuser -d merchify_shard_0
```

### If a cluster fails to start

```bash
sudo journalctl -u postgresql
```

---

## Notes

This setup uses separate PostgreSQL clusters on different ports as a practical learning environment. It is enough to test the app’s routing logic and replica endpoint configuration without needing RDS.

If you want, I can also give you a follow-up guide for true streaming replication from one PostgreSQL 16 primary to a replica on EC2.
