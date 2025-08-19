import os

from flask import Flask, redirect

from .blueprints.api_routes import api_bp
from .blueprints.audit_routes import audit_bp
from .blueprints.import_export_routes import import_export_bp
from .blueprints.ipam import blocks_bp, containers_bp, exports_bp, subnets_bp
from .blueprints.main_routes import main_bp
from .blueprints.segment_routes import segment_bp
from .config import get_db_path, get_secret_key
from .models import db


def get_version():
    """Read version from VERSION file.

    Returns:
        str: Application version string, or '0.1.0' fallback if file not found
    """
    try:
        version_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), "VERSION")
        with open(version_file, "r") as f:
            return f.read().strip()
    except (FileNotFoundError, IOError):
        return "0.1.0"  # Fallback version


def create_app():
    """Create and configure Flask application instance.

    This factory function creates the Flask app, configures the database,
    registers blueprints, and configures the application.

    Returns:
        Flask: Configured Flask application instance
    """
    app = Flask(__name__)
    app.config["SECRET_KEY"] = get_secret_key()

    # Configure SQLAlchemy
    app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{get_db_path()}"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    # Initialize extensions
    db.init_app(app)

    # Set version as app attribute
    app.version = get_version()

    # Register blueprints
    app.register_blueprint(main_bp)
    app.register_blueprint(exports_bp)
    app.register_blueprint(containers_bp)
    app.register_blueprint(blocks_bp)
    app.register_blueprint(subnets_bp)
    app.register_blueprint(audit_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(segment_bp)
    app.register_blueprint(import_export_bp)

    # Add additional routes for Swagger documentation
    @app.route("/docs")
    @app.route("/api/")
    @app.route("/api/swagger")
    def swagger_redirects():
        """Redirect alternative paths to Swagger documentation"""
        return redirect("/swagger/")

    return app
