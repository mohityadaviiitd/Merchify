"""
Management command to set up and manage database shards.

Usage:
    python manage.py setup_shards              # Initial setup
    python manage.py setup_shards --migrate    # Migrate all shards
    python manage.py setup_shards --stats      # Show shard statistics
"""

from django.core.management.base import BaseCommand, CommandError
from django.core.management import call_command
from django.db import connection, connections
from api.sharding import SHARD_NAMES, REPLICA_NAMES, get_shard_id
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Set up and manage database shards'

    def add_arguments(self, parser):
        parser.add_argument(
            '--migrate',
            action='store_true',
            help='Run migrations on all shards',
        )
        parser.add_argument(
            '--stats',
            action='store_true',
            help='Show shard statistics',
        )
        parser.add_argument(
            '--check',
            action='store_true',
            help='Check shard database connections',
        )
        parser.add_argument(
            '--create-dbs',
            action='store_true',
            help='Create shard databases (requires superuser privileges)',
        )

    def handle(self, *args, **options):
        if options['migrate']:
            self.migrate_shards()
        elif options['stats']:
            self.show_stats()
        elif options['check']:
            self.check_connections()
        elif options['create_dbs']:
            self.create_shard_databases()
        else:
            self.setup_initial()

    def setup_initial(self):
        """Initial setup of all shards."""
        self.stdout.write(self.style.SUCCESS('Starting shard setup...'))
        
        # Check connections
        self.check_connections()
        
        # Create databases if needed
        self.stdout.write('\nCreating shard databases...')
        self.create_shard_databases()
        
        # Run migrations
        self.stdout.write('\nRunning migrations on all shards...')
        self.migrate_shards()
        
        self.stdout.write(self.style.SUCCESS('\n✓ Shard setup completed successfully!'))

    def migrate_shards(self):
        """Run migrations on all shard databases."""
        all_dbs = ['default'] + SHARD_NAMES + list(REPLICA_NAMES.values())
        
        for db in all_dbs:
            try:
                self.stdout.write(f'  Migrating {db}...', ending=' ')
                call_command('migrate', database=db, verbosity=0)
                self.stdout.write(self.style.SUCCESS('✓'))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'✗ Error: {str(e)}'))

    def check_connections(self):
        """Check database connections for all shards."""
        self.stdout.write('Checking database connections...')
        
        all_dbs = ['default'] + SHARD_NAMES + list(REPLICA_NAMES.values())
        
        for db_alias in all_dbs:
            try:
                conn = connections[db_alias]
                conn.ensure_connection()
                db_name = conn.settings_dict.get('NAME', 'unknown')
                db_host = conn.settings_dict.get('HOST', 'unknown')
                self.stdout.write(
                    f'  ✓ {db_alias:20} → {db_host}/{db_name}'
                )
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'  ✗ {db_alias:20} → Error: {str(e)}')
                )

    def show_stats(self):
        """Display shard statistics."""
        self.stdout.write('Shard Configuration:')
        self.stdout.write('=' * 60)
        
        self.stdout.write('\nShard Distribution Strategy:')
        self.stdout.write('  • Shard 0: user_id % 2 == 0 (even user IDs)')
        self.stdout.write('  • Shard 1: user_id % 2 == 1 (odd user IDs)')
        
        self.stdout.write('\nShard Structure:')
        for i, shard in enumerate(SHARD_NAMES):
            replica = REPLICA_NAMES.get(shard)
            self.stdout.write(f'\n  Shard {i} ({shard}):')
            self.stdout.write(f'    Primary:  {shard}')
            self.stdout.write(f'    Replica:  {replica}')

    def create_shard_databases(self):
        """
        Create shard databases.
        
        Note: This requires superuser/admin privileges on PostgreSQL.
        For RDS, you may need to use AWS RDS console or aws-cli.
        """
        self.stdout.write(self.style.WARNING(
            '\nNote: Database creation for RDS requires AWS credentials/console.'
        ))
        self.stdout.write('\nTo create shard databases on RDS:')
        self.stdout.write('  1. Use AWS Management Console → RDS')
        self.stdout.write('  2. Create 2 DB instances for primary shards')
        self.stdout.write('  3. Create read replicas for each shard')
        self.stdout.write('  4. Update environment variables with connection details')
        self.stdout.write('  5. Run: python manage.py migrate --database=shard_0')
        self.stdout.write('  6. Run: python manage.py migrate --database=shard_1')
        
        # If using local PostgreSQL (not RDS), attempt creation
        try:
            with connection.cursor() as cursor:
                for shard_name in SHARD_NAMES:
                    db_name = f'merchify_{shard_name}'
                    try:
                        cursor.execute(f'CREATE DATABASE "{db_name}";')
                        self.stdout.write(self.style.SUCCESS(f'  ✓ Created {db_name}'))
                    except Exception as e:
                        if 'already exists' in str(e):
                            self.stdout.write(f'  ℹ {db_name} already exists')
                        else:
                            self.stdout.write(self.style.ERROR(f'  ✗ {db_name}: {str(e)}'))
        except Exception as e:
            self.stdout.write(self.style.WARNING(
                f'  ℹ Could not create local databases: {str(e)}\n'
                '  If using RDS, please create databases through AWS console.'
            ))
