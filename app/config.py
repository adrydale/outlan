import configparser
import os
from typing import Any, Optional

# Default configuration values
DEFAULT_DB_PATH = "/app/data/ipam.db"
DEFAULT_DB_TIMEOUT = 10
DEFAULT_SORT_FIELD = "VLAN"
DEFAULT_SNAPSHOT_LIMIT = 200
DEFAULT_LOG_LEVEL = "INFO"
DEFAULT_LOG_MAX_SIZE_MB = 5
DEFAULT_LOG_BACKUP_COUNT = 5
DEFAULT_TIMEZONE = "Etc/GMT"
DEFAULT_THEME = "dark"
DEFAULT_SECRET_KEY = "your-secret-key-change-in-production"


class Config:
    """Configuration management with INI file and environment variable
    support"""

    def __init__(self, config_file: str = "config/settings.ini"):
        self.config = configparser.ConfigParser()
        self.config_file = config_file
        self._load_config()

    def _load_config(self):
        """Load configuration from INI file"""
        if os.path.exists(self.config_file):
            self.config.read(self.config_file)
        else:
            # Create default config if file doesn't exist
            self._create_default_config()

    def _create_default_config(self):
        """Create default configuration with comments"""
        # Create config directory if it doesn't exist
        os.makedirs(os.path.dirname(self.config_file), exist_ok=True)

        # Write default config with comments
        default_config_content = f"""[database]
# Database file path (can be overridden with DB_PATH env var)
path = {DEFAULT_DB_PATH}
# Database connection timeout in seconds (can be overridden with DB_TIMEOUT env
# var)
timeout = {DEFAULT_DB_TIMEOUT}

[display]
# Default sort field for network tables: Network, VLAN, or Name (can be
# overridden with DEFAULT_SORT env var)
# Case insensitive - will be converted to proper case
default_sort = {DEFAULT_SORT_FIELD}
# Default theme: light, dark, or midnight (can be overridden with THEME env var)
theme = {DEFAULT_THEME}

[snapshots]
# Maximum number of snapshots to keep (can be overridden with SNAPSHOT_LIMIT env
# var)
limit = {DEFAULT_SNAPSHOT_LIMIT}

[security]
# Flask secret key for session management and flash messages (can be overridden
# with SECRET_KEY env var)
# Generate a random key for production use
secret_key = {DEFAULT_SECRET_KEY}

[logging]
# Log level for console output: DEBUG, INFO, WARNING, ERROR (can be overridden
# with LOG_LEVEL env var)
level = {DEFAULT_LOG_LEVEL}
# Maximum size for access log files in MB (can be overridden with
# LOG_MAX_SIZE_MB env var)
max_size_mb = {DEFAULT_LOG_MAX_SIZE_MB}
# Number of rotated log files to keep (can be overridden with LOG_BACKUP_COUNT
# env var)
backup_count = {DEFAULT_LOG_BACKUP_COUNT}
# Timezone for logging (can be overridden with TZ env var, default is Etc/GMT)
timezone = {DEFAULT_TIMEZONE}
"""

        with open(self.config_file, "w") as f:
            f.write(default_config_content)

        # Also load it into the configparser for immediate use
        self.config.read(self.config_file)

    def get(self, section: str, key: str, default: Any = None, env_var: Optional[str] = None) -> Any:
        """Get configuration value with environment variable override"""
        # Check environment variable first
        if env_var and env_var in os.environ:
            return os.environ[env_var]

        # Fall back to INI file
        try:
            return self.config.get(section, key)
        except (configparser.NoSectionError, configparser.NoOptionError):
            return default

    def getint(self, section: str, key: str, default: int = 0, env_var: Optional[str] = None) -> int:
        """Get integer configuration value"""
        value = self.get(section, key, str(default), env_var)
        try:
            return int(value)
        except (ValueError, TypeError):
            return default

    def getfloat(self, section: str, key: str, default: float = 0.0, env_var: Optional[str] = None) -> float:
        """Get float configuration value"""
        value = self.get(section, key, str(default), env_var)
        try:
            return float(value)
        except (ValueError, TypeError):
            return default

    def get_enum(self, section: str, key: str, valid_options: list, default: str, env_var: Optional[str] = None) -> str:
        """Get enum configuration value with case-insensitive matching"""
        value = self.get(section, key, default, env_var)

        # Case-insensitive matching
        for option in valid_options:
            if value.upper() == option.upper():
                return option

        # Return default if no match found
        return default


# Global configuration instance
config = Config()


# Convenience functions for common settings
def get_db_path() -> str:
    """Get database file path from configuration."""
    return config.get("database", "path", DEFAULT_DB_PATH, "DB_PATH")


def get_db_timeout() -> int:
    """Get database connection timeout in seconds."""
    return config.getint("database", "timeout", DEFAULT_DB_TIMEOUT, "DB_TIMEOUT")


def get_default_sort() -> str:
    """Get default sort field for network tables."""
    valid_options = ["Network", "VLAN", "Name"]
    return config.get_enum("display", "default_sort", valid_options, DEFAULT_SORT_FIELD, "DEFAULT_SORT")


def get_snapshot_limit() -> int:
    """Get maximum number of snapshots to keep."""
    return config.getint("snapshots", "limit", DEFAULT_SNAPSHOT_LIMIT, "SNAPSHOT_LIMIT")


def get_log_level() -> str:
    """Get logging level configuration."""
    valid_options = ["DEBUG", "INFO", "WARNING", "ERROR"]
    return config.get_enum("logging", "level", valid_options, DEFAULT_LOG_LEVEL, "LOG_LEVEL")


def get_log_max_size_mb() -> int:
    return config.getint("logging", "max_size_mb", DEFAULT_LOG_MAX_SIZE_MB, "LOG_MAX_SIZE_MB")


def get_log_backup_count() -> int:
    return config.getint("logging", "backup_count", DEFAULT_LOG_BACKUP_COUNT, "LOG_BACKUP_COUNT")


def get_timezone() -> str:
    """Get timezone configuration"""
    return config.get("logging", "timezone", DEFAULT_TIMEZONE, "TZ")


def get_theme() -> str:
    """Get theme configuration"""
    valid_options = ["light", "dark", "midnight"]
    return config.get_enum("display", "theme", valid_options, DEFAULT_THEME, "THEME")


def get_secret_key() -> str:
    """Get Flask secret key configuration"""
    return config.get("security", "secret_key", DEFAULT_SECRET_KEY, "SECRET_KEY")
