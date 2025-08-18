import logging
import sqlite3

from app.config import get_db_path
from app.models import ChangeLog, NetworkBlock, Subnet, db

logger = logging.getLogger(__name__)


def migrate_old_database():
    """Migrate data from old SQLite database to new SQLAlchemy models.

    This function handles migration from legacy database structures to the current
    SQLAlchemy-based models. It preserves existing data while updating the schema.

    Returns:
        bool: True if migration successful or no migration needed, False on error
    """
    try:
        old_db_path = get_db_path()

        # Check if old database exists
        try:
            old_conn = sqlite3.connect(old_db_path)
            old_conn.row_factory = sqlite3.Row
        except Exception as e:
            logger.info(f"No existing database found at {old_db_path}: {e}")
            return True

        # Check if tables exist in old database
        cursor = old_conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        existing_tables = [row[0] for row in cursor.fetchall()]

        if not existing_tables:
            logger.info("No existing tables found, skipping migration")
            old_conn.close()
            return True

        logger.info(f"Found existing tables: {existing_tables}")

        # Migrate network_blocks
        if "network_blocks" in existing_tables:
            logger.info("Migrating network_blocks...")
            blocks = old_conn.execute("SELECT * FROM network_blocks").fetchall()

            for block_data in blocks:
                # Check if block already exists
                existing_block = NetworkBlock.query.get(block_data["id"])
                if not existing_block:
                    block = NetworkBlock(
                        id=block_data["id"],
                        name=block_data["name"],
                        position=block_data.get("position", 0),
                        collapsed=bool(block_data.get("collapsed", 0)),
                    )
                    db.session.add(block)
                    logger.info(f"Migrated block: {block.name}")

        # Migrate subnets
        if "subnets" in existing_tables:
            logger.info("Migrating subnets...")
            subnets = old_conn.execute("SELECT * FROM subnets").fetchall()

            for subnet_data in subnets:
                # Check if subnet already exists
                existing_subnet = Subnet.query.get(subnet_data["id"])
                if not existing_subnet:
                    subnet = Subnet(
                        id=subnet_data["id"],
                        block_id=subnet_data["block_id"],
                        name=subnet_data["name"],
                        vlan_id=subnet_data.get("vlan_id"),
                        cidr=subnet_data["cidr"],
                    )
                    db.session.add(subnet)
                    logger.info(f"Migrated subnet: {subnet.name} ({subnet.cidr})")

        # Migrate change_log
        if "change_log" in existing_tables:
            logger.info("Migrating change_log...")
            changes = old_conn.execute("SELECT * FROM change_log").fetchall()

            for change_data in changes:
                # Check if change already exists
                existing_change = ChangeLog.query.get(change_data["id"])
                if not existing_change:
                    change = ChangeLog(
                        id=change_data["id"],
                        timestamp=change_data["timestamp"],
                        action=change_data["action"],
                        block=change_data.get("block"),
                        details=change_data.get("details"),
                        content=change_data.get("content"),
                    )
                    db.session.add(change)
                    logger.info(f"Migrated change log entry: {change.action}")

        # Commit all changes
        db.session.commit()
        old_conn.close()

        logger.info("Database migration completed successfully")
        return True

    except Exception as e:
        logger.error(f"Error during migration: {str(e)}", exc_info=True)
        db.session.rollback()
        return False


def create_initial_snapshot():
    """Create initial snapshot if no snapshots exist.

    This creates a baseline snapshot of the database for audit/restore purposes.
    Only creates a snapshot if none exist to avoid duplicates.

    Returns:
        bool: True if snapshot created successfully or already exists, False on error
    """
    try:
        # Check if any snapshots exist
        existing_snapshots = ChangeLog.query.filter_by(action="SNAPSHOT").first()
        if existing_snapshots:
            logger.info("Snapshots already exist, skipping initial snapshot creation")
            return True

        # Create initial snapshot
        from app.utils import DatabaseService

        content = DatabaseService.export_all_data()

        snapshot = ChangeLog(action="SNAPSHOT", block="-", details="Initial snapshot after migration", content=content)
        db.session.add(snapshot)
        db.session.commit()

        logger.info("Created initial snapshot")
        return True

    except Exception as e:
        logger.error(f"Error creating initial snapshot: {str(e)}", exc_info=True)
        db.session.rollback()
        return False
