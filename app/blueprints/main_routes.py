import ipaddress
import logging
import os

from flask import Blueprint, current_app, flash, redirect, render_template, request, url_for

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


@main_bp.route("/docker_health_check")
def docker_health_check():
    """Simple health check endpoint for Docker that doesn't require database access"""
    return "OK", 200


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

        # Get blocks, containers, and subnets using the service
        blocks = DatabaseService.get_all_blocks()
        containers = DatabaseService.get_all_containers()
        subnets = DatabaseService.get_all_subnets()

        # Convert blocks to dictionaries
        blocks_dict = [block.to_dict() for block in blocks]

        # Group containers by block_id and convert to dictionaries
        containers_by_block = {}
        for container in containers:
            container_dict = container.to_dict()
            containers_by_block.setdefault(container.block_id, []).append(container_dict)

        # Group subnets by block_id and convert to dictionaries
        subnets_by_block = {}
        for subnet in subnets:
            subnet_dict = subnet.to_dict()
            subnets_by_block.setdefault(subnet.block_id, []).append(subnet_dict)

        # Create hierarchical network structure for each block
        hierarchical_networks_by_block = {}
        for block in blocks_dict:
            block_id = block["id"]
            block_containers = containers_by_block.get(block_id, [])
            block_subnets = subnets_by_block.get(block_id, [])

            # Create hierarchical structure
            hierarchical_networks = []

            # First, add all containers as top-level entries
            for container in block_containers:
                try:
                    container_net = ipaddress.ip_network(container["base_network"], strict=False)
                    container_entry = {
                        "type": "container",
                        "container": container,
                        "subnets": [],
                        "sort_key": container_net,
                    }

                    # Find subnets that belong to this container
                    for subnet in block_subnets:
                        try:
                            subnet_net = ipaddress.ip_network(subnet["cidr"], strict=False)
                            if subnet_net.subnet_of(container_net):
                                container_entry["subnets"].append(subnet)
                        except ValueError:
                            continue

                    hierarchical_networks.append(container_entry)
                except ValueError:
                    continue

            # Then, add orphaned subnets (subnets not in any container)
            for subnet in block_subnets:
                is_orphaned = True
                try:
                    subnet_net = ipaddress.ip_network(subnet["cidr"], strict=False)
                    for container in block_containers:
                        try:
                            container_net = ipaddress.ip_network(container["base_network"], strict=False)
                            if subnet_net.subnet_of(container_net):
                                is_orphaned = False
                                break
                        except ValueError:
                            continue

                    if is_orphaned:
                        hierarchical_networks.append({"type": "subnet", "subnet": subnet, "sort_key": subnet_net})
                except ValueError:
                    # Add invalid CIDRs as orphaned subnets
                    hierarchical_networks.append({"type": "subnet", "subnet": subnet, "sort_key": None})

            # Sort hierarchical networks by IP address
            hierarchical_networks.sort(
                key=lambda x: x["sort_key"] if x["sort_key"] else ipaddress.ip_network("255.255.255.255/32")
            )

            hierarchical_networks_by_block[block_id] = hierarchical_networks

        # Get edit parameter from request args
        edit_id = request.args.get("edit")

        return render_template(
            "ipam_main.html",
            blocks=blocks_dict,
            containers_by_block=containers_by_block,
            subnets_by_block=subnets_by_block,
            hierarchical_networks_by_block=hierarchical_networks_by_block,
            edit_id=edit_id,
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


# Add additional routes for Swagger documentation.  The /swagger route is
# created in api_routes.py as part of the API creation. These routes must exist
# in main_routes.py as subsequent routes defined in api_routes.py are prefixed
# with /api/*.
@main_bp.route("/docs")
@main_bp.route("/api/")
@main_bp.route("/api/swagger")
def swagger_redirects():
    """Redirect alternative paths to Swagger documentation"""
    return redirect("/swagger/")


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
