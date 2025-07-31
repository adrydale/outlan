import os

from flask import Flask
from flask_wtf.csrf import CSRFProtect

from .blueprints.api_routes import api_bp
from .blueprints.audit_routes import audit_bp
from .blueprints.ipam_routes import ipam_bp
from .blueprints.main_routes import main_bp
from .config import get_db_path, get_secret_key
from .models import db


def get_version():
    """Read version from VERSION file"""
    try:
        version_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), "VERSION")
        with open(version_file, "r") as f:
            return f.read().strip()
    except (FileNotFoundError, IOError):
        return "0.1.0"  # Fallback version


def create_app():
    app = Flask(__name__)
    app.config["SECRET_KEY"] = get_secret_key()

    # Configure SQLAlchemy
    app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{get_db_path()}"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    # Initialize extensions
    db.init_app(app)
    CSRFProtect(app)

    # Set version as app attribute
    app.version = get_version()

    # Register blueprints
    app.register_blueprint(main_bp)
    app.register_blueprint(ipam_bp)
    app.register_blueprint(audit_bp)
    app.register_blueprint(api_bp)

    return app
