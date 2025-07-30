import logging
import os

from flask import Blueprint, current_app, flash, redirect, render_template, url_for

from app.config import get_theme
from app.models import db
from app.utils import DatabaseService
from app.utils.migration import create_initial_snapshot, migrate_old_database

logger = logging.getLogger(__name__)
main_bp = Blueprint("main", __name__)


@main_bp.route("/init")
def show_init():
    db_path = current_app.config.get("DATABASE", "data/ipam.db")
    if not os.path.exists(db_path):
        return render_template("ipam_init.html", version=current_app.version, theme=get_theme())

    # Check if SQLAlchemy tables exist by trying to query them
    try:
        with current_app.app_context():
            # Try to create tables if they don't exist
            db.create_all()

            # Try to access the database to see if it works
            blocks = DatabaseService.get_all_blocks()
            logger.info(f"Database is properly initialized with {len(blocks)} blocks")
            return redirect(url_for("main.index"))

    except Exception as e:
        logger.error(f"Database not properly initialized: {str(e)}")
        return render_template("ipam_init.html", version=current_app.version, theme=get_theme())


@main_bp.route("/init_db", methods=["POST"])
def initialize():
    try:
        # Create database tables
        with current_app.app_context():
            db.create_all()

            # Migrate existing data if any
            if migrate_old_database():
                logger.info("Database migration completed")

                # Create initial snapshot if needed
                create_initial_snapshot()
            else:
                logger.warning("Database migration failed")

        flash("Database initialized successfully! You can now start using IPAM.", "success")
        return redirect(url_for("main.index"))
    except Exception as e:
        logger.error(f"Error initializing DB: {str(e)}", exc_info=True)
        return (
            render_template(
                "error.html",
                message="Failed to initialize database. Please check the logs for details.",
                attempted={"cidr": None, "vlan": None, "name": None},
                version=current_app.version,
            ),
            500,
        )


@main_bp.route("/db_exists")
def db_exists():
    return render_template("db_exists.html", version=current_app.version, theme=get_theme())


@main_bp.route("/")
def index():
    try:
        # Check if database exists and is accessible
        db_path = current_app.config.get("DATABASE", "data/ipam.db")
        if not os.path.exists(db_path):
            return redirect(url_for("main.show_init"))

        # Check if SQLAlchemy tables exist by trying to query them
        try:
            with current_app.app_context():
                # Try to create tables if they don't exist
                db.create_all()

                # Try to access the database to see if it works
                blocks = DatabaseService.get_all_blocks()
                logger.info(f"Successfully connected to database, found {len(blocks)} blocks")

        except Exception as e:
            logger.error(f"Database connection failed: {str(e)}")
            return redirect(url_for("main.show_init"))

        # Get blocks and subnets using the service
        blocks = DatabaseService.get_all_blocks()
        subnets = DatabaseService.get_all_subnets()

        # Convert blocks to dictionaries
        blocks_dict = [block.to_dict() for block in blocks]

        # Group subnets by block_id and convert to dictionaries
        subnets_by_block = {}
        for subnet in subnets:
            subnet_dict = subnet.to_dict()
            subnets_by_block.setdefault(subnet.block_id, []).append(subnet_dict)

        return render_template(
            "ipam_main.html",
            blocks=blocks_dict,
            subnets_by_block=subnets_by_block,
            version=current_app.version,
            theme=get_theme(),
        )
    except Exception as e:
        logger.error(f"Error loading dashboard: {str(e)}", exc_info=True)
        return (
            render_template(
                "error.html",
                message="Error loading dashboard",
                attempted=None,
                traceback=str(e),
                version=current_app.version,
            ),
            500,
        )


@main_bp.route("/settings")
def settings():
    """Display all configuration settings and their sources"""
    try:
        from app.config import (
            get_db_path,
            get_db_timeout,
            get_default_sort,
            get_log_backup_count,
            get_log_level,
            get_log_max_size_mb,
            get_secret_key,
            get_snapshot_limit,
            get_theme,
            get_timezone,
        )

        # Get secret key status
        secret_key = get_secret_key()
        secret_key_status = "CUSTOM" if secret_key != "your-secret-key-change-in-production" else "DEFAULT"
        secret_key_valid = len(secret_key) >= 16  # Basic validation

        # Create flat list of all settings
        settings_list = [
            {"setting": "DB_PATH", "value": get_db_path(), "source": "ENV" if os.environ.get("DB_PATH") else "INI"},
            {
                "setting": "DB_TIMEOUT",
                "value": str(get_db_timeout()),
                "source": "ENV" if os.environ.get("DB_TIMEOUT") else "INI",
            },
            {
                "setting": "DEFAULT_SORT",
                "value": get_default_sort(),
                "source": "ENV" if os.environ.get("DEFAULT_SORT") else "INI",
            },
            {
                "setting": "THEME",
                "value": get_theme(),
                "source": "ENV" if os.environ.get("THEME") else "INI",
                "has_localstorage": True,
            },
            {
                "setting": "SNAPSHOT_LIMIT",
                "value": str(get_snapshot_limit()),
                "source": "ENV" if os.environ.get("SNAPSHOT_LIMIT") else "INI",
            },
            {
                "setting": "SECRET_KEY",
                "value": f"{secret_key_status} ({'VALID' if secret_key_valid else 'INVALID'})",
                "source": "ENV" if os.environ.get("SECRET_KEY") else "INI",
            },
            {
                "setting": "LOG_LEVEL",
                "value": get_log_level(),
                "source": "ENV" if os.environ.get("LOG_LEVEL") else "INI",
            },
            {
                "setting": "LOG_MAX_SIZE_MB",
                "value": str(get_log_max_size_mb()),
                "source": "ENV" if os.environ.get("LOG_MAX_SIZE_MB") else "INI",
            },
            {
                "setting": "LOG_BACKUP_COUNT",
                "value": str(get_log_backup_count()),
                "source": "ENV" if os.environ.get("LOG_BACKUP_COUNT") else "INI",
            },
            {"setting": "TZ", "value": get_timezone(), "source": "ENV" if os.environ.get("TZ") else "INI"},
        ]

        return render_template("settings.html", settings=settings_list, version=current_app.version, theme=get_theme())
    except Exception as e:
        logger.error(f"Error loading settings: {str(e)}", exc_info=True)
        return (
            render_template(
                "error.html",
                message="Error loading settings",
                attempted=None,
                traceback=str(e),
                version=current_app.version,
            ),
            500,
        )
