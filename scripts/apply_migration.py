#!/usr/bin/env python3
"""
Database Migration Script for Platform Coordination Service

This script applies database migrations to add performance indexes.
It supports both forward and rollback operations.

Usage:
    python scripts/apply_migration.py --forward                    # Apply migration
    python scripts/apply_migration.py --rollback                  # Rollback migration
    python scripts/apply_migration.py --status                    # Check migration status
    python scripts/apply_migration.py --help                      # Show help

Environment Variables:
    DATABASE_URL: PostgreSQL connection string (optional)
    MIGRATION_TIMEOUT: Timeout for migration operations in seconds (default: 3600)
"""

import argparse
import logging
import os
import sys
from pathlib import Path
from typing import Optional

import psycopg2
from psycopg2 import sql
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

# Add the src directory to Python path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class MigrationError(Exception):
    """Custom exception for migration-related errors."""
    pass


class DatabaseMigrator:
    """Handles database migration operations."""
    
    def __init__(self, database_url: Optional[str] = None, timeout: int = 3600):
        """
        Initialize the migrator.
        
        Args:
            database_url: PostgreSQL connection string
            timeout: Timeout for migration operations in seconds
        """
        self.database_url = database_url or self._get_default_database_url()
        self.timeout = timeout
        self.migration_dir = Path(__file__).parent.parent / "migrations"
        
        # Migration files
        self.forward_migration = self.migration_dir / "001_add_performance_indexes.sql"
        self.rollback_migration = self.migration_dir / "001_add_performance_indexes_rollback.sql"
        
    def _get_default_database_url(self) -> str:
        """Get the default database URL from environment or config."""
        # Try environment variable first
        db_url = os.getenv("DATABASE_URL")
        if db_url:
            # Convert asyncpg URL to psycopg2 URL if needed
            if "postgresql+asyncpg://" in db_url:
                db_url = db_url.replace("postgresql+asyncpg://", "postgresql://")
            return db_url
            
        # Fallback to default development URL
        return "postgresql://coordination_user:coordination_dev_password@localhost:5432/platform_coordination"
    
    def _get_connection(self):
        """Create a database connection."""
        try:
            conn = psycopg2.connect(self.database_url)
            conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
            return conn
        except psycopg2.Error as e:
            raise MigrationError(f"Failed to connect to database: {e}")
    
    def _create_migration_table(self, cursor):
        """Create the migration tracking table if it doesn't exist."""
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            id SERIAL PRIMARY KEY,
            migration_name VARCHAR(255) NOT NULL UNIQUE,
            applied_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
            rollback_sql TEXT,
            checksum VARCHAR(64)
        );
        
        COMMENT ON TABLE schema_migrations IS 'Tracks database migrations for the platform coordination service';
        """
        
        try:
            cursor.execute(create_table_sql)
            logger.info("Migration tracking table ready")
        except psycopg2.Error as e:
            raise MigrationError(f"Failed to create migration table: {e}")
    
    def _is_migration_applied(self, cursor, migration_name: str) -> bool:
        """Check if a migration has been applied."""
        try:
            cursor.execute(
                "SELECT 1 FROM schema_migrations WHERE migration_name = %s",
                (migration_name,)
            )
            return cursor.fetchone() is not None
        except psycopg2.Error as e:
            raise MigrationError(f"Failed to check migration status: {e}")
    
    def _record_migration(self, cursor, migration_name: str, rollback_file: Optional[Path] = None):
        """Record a successful migration."""
        rollback_sql = None
        if rollback_file and rollback_file.exists():
            rollback_sql = rollback_file.read_text()
        
        try:
            cursor.execute(
                """
                INSERT INTO schema_migrations (migration_name, rollback_sql)
                VALUES (%s, %s)
                ON CONFLICT (migration_name) DO UPDATE SET
                    applied_at = CURRENT_TIMESTAMP,
                    rollback_sql = EXCLUDED.rollback_sql
                """,
                (migration_name, rollback_sql)
            )
            logger.info(f"Recorded migration: {migration_name}")
        except psycopg2.Error as e:
            raise MigrationError(f"Failed to record migration: {e}")
    
    def _remove_migration_record(self, cursor, migration_name: str):
        """Remove a migration record after rollback."""
        try:
            cursor.execute(
                "DELETE FROM schema_migrations WHERE migration_name = %s",
                (migration_name,)
            )
            logger.info(f"Removed migration record: {migration_name}")
        except psycopg2.Error as e:
            raise MigrationError(f"Failed to remove migration record: {e}")
    
    def _execute_sql_file(self, cursor, sql_file: Path):
        """Execute SQL commands from a file."""
        if not sql_file.exists():
            raise MigrationError(f"Migration file not found: {sql_file}")
        
        try:
            sql_content = sql_file.read_text()
            # Split on semicolons but be careful with function definitions
            statements = []
            current_statement = ""
            in_function = False
            
            for line in sql_content.split('\n'):
                line = line.strip()
                if not line or line.startswith('--'):
                    continue
                
                if 'CREATE OR REPLACE FUNCTION' in line.upper() or 'CREATE FUNCTION' in line.upper():
                    in_function = True
                
                current_statement += line + '\n'
                
                if line.endswith(';'):
                    if in_function and ('END;' in line.upper() or '$$ language' in line.lower()):
                        in_function = False
                        statements.append(current_statement.strip())
                        current_statement = ""
                    elif not in_function:
                        statements.append(current_statement.strip())
                        current_statement = ""
            
            # Execute each statement
            for i, statement in enumerate(statements):
                if statement:
                    logger.info(f"Executing statement {i+1}/{len(statements)}")
                    cursor.execute(statement)
                    
        except psycopg2.Error as e:
            raise MigrationError(f"Failed to execute SQL file {sql_file}: {e}")
        except Exception as e:
            raise MigrationError(f"Error processing SQL file {sql_file}: {e}")
    
    def apply_forward_migration(self):
        """Apply the forward migration (add indexes)."""
        migration_name = "001_add_performance_indexes"
        
        with self._get_connection() as conn:
            with conn.cursor() as cursor:
                self._create_migration_table(cursor)
                
                if self._is_migration_applied(cursor, migration_name):
                    logger.info(f"Migration {migration_name} already applied")
                    return
                
                logger.info(f"Applying migration: {migration_name}")
                logger.info("This may take several minutes for large tables...")
                
                # Set statement timeout for long-running index creation
                cursor.execute(f"SET statement_timeout = '{self.timeout * 1000}ms'")
                
                self._execute_sql_file(cursor, self.forward_migration)
                self._record_migration(cursor, migration_name, self.rollback_migration)
                
                logger.info(f"Successfully applied migration: {migration_name}")
    
    def apply_rollback_migration(self):
        """Apply the rollback migration (remove indexes)."""
        migration_name = "001_add_performance_indexes"
        
        with self._get_connection() as conn:
            with conn.cursor() as cursor:
                self._create_migration_table(cursor)
                
                if not self._is_migration_applied(cursor, migration_name):
                    logger.info(f"Migration {migration_name} not applied, nothing to rollback")
                    return
                
                logger.info(f"Rolling back migration: {migration_name}")
                logger.info("This may take several minutes for large tables...")
                
                # Set statement timeout for long-running index removal
                cursor.execute(f"SET statement_timeout = '{self.timeout * 1000}ms'")
                
                self._execute_sql_file(cursor, self.rollback_migration)
                self._remove_migration_record(cursor, migration_name)
                
                logger.info(f"Successfully rolled back migration: {migration_name}")
    
    def check_migration_status(self):
        """Check the status of migrations."""
        migration_name = "001_add_performance_indexes"
        
        with self._get_connection() as conn:
            with conn.cursor() as cursor:
                self._create_migration_table(cursor)
                
                # Check migration status
                cursor.execute(
                    "SELECT applied_at FROM schema_migrations WHERE migration_name = %s",
                    (migration_name,)
                )
                result = cursor.fetchone()
                
                if result:
                    logger.info(f"Migration {migration_name} is APPLIED (applied at: {result[0]})")
                else:
                    logger.info(f"Migration {migration_name} is NOT APPLIED")
                
                # Check if migration files exist
                logger.info(f"Forward migration file exists: {self.forward_migration.exists()}")
                logger.info(f"Rollback migration file exists: {self.rollback_migration.exists()}")
                
                # Check current indexes
                cursor.execute("""
                    SELECT indexname, indexdef 
                    FROM pg_indexes 
                    WHERE tablename IN ('services', 'service_events')
                        AND schemaname = 'public'
                        AND indexname LIKE 'idx_%'
                    ORDER BY tablename, indexname
                """)
                
                indexes = cursor.fetchall()
                logger.info(f"Current indexes found: {len(indexes)}")
                for idx_name, idx_def in indexes:
                    logger.info(f"  - {idx_name}")


def main():
    """Main entry point for the migration script."""
    parser = argparse.ArgumentParser(
        description="Database Migration Script for Platform Coordination Service",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--forward",
        action="store_true",
        help="Apply the forward migration (add performance indexes)"
    )
    group.add_argument(
        "--rollback",
        action="store_true",
        help="Apply the rollback migration (remove performance indexes)"
    )
    group.add_argument(
        "--status",
        action="store_true",
        help="Check migration status"
    )
    
    parser.add_argument(
        "--database-url",
        help="PostgreSQL connection string (overrides environment variable)"
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=3600,
        help="Timeout for migration operations in seconds (default: 3600)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without executing (status check only)"
    )
    
    args = parser.parse_args()
    
    try:
        # Get timeout from environment if not provided
        timeout = args.timeout
        if not timeout:
            timeout = int(os.getenv("MIGRATION_TIMEOUT", "3600"))
        
        migrator = DatabaseMigrator(args.database_url, timeout)
        
        if args.forward:
            if args.dry_run:
                logger.info("DRY RUN: Would apply forward migration")
                return
            migrator.apply_forward_migration()
        elif args.rollback:
            if args.dry_run:
                logger.info("DRY RUN: Would apply rollback migration")
                return
            migrator.apply_rollback_migration()
        elif args.status:
            migrator.check_migration_status()
            
    except MigrationError as e:
        logger.error(f"Migration failed: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        logger.warning("Migration interrupted by user")
        sys.exit(130)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()