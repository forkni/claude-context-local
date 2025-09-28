"""Application configuration management."""

import json
import logging
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, Optional


class ConfigurationError(Exception):
    """Configuration loading or validation error."""

    pass


@dataclass
class DatabaseConfig:
    """Database configuration settings."""

    host: str = "localhost"
    port: int = 5432
    database: str = "app_db"
    username: str = "app_user"
    password: str = ""
    pool_size: int = 10
    timeout: int = 30


@dataclass
class APIConfig:
    """API server configuration settings."""

    host: str = "localhost"
    port: int = 8000
    debug: bool = False
    cors_enabled: bool = True
    rate_limit: int = 100
    session_timeout: int = 3600  # 1 hour in seconds


@dataclass
class LoggingConfig:
    """Logging configuration settings."""

    level: str = "INFO"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    file_path: Optional[str] = "app.log"
    max_file_size: int = 10485760  # 10MB
    backup_count: int = 5


@dataclass
class SecurityConfig:
    """Security configuration settings."""

    secret_key: str = ""
    jwt_algorithm: str = "HS256"
    password_min_length: int = 8
    session_cookie_secure: bool = True
    csrf_protection: bool = True
    max_login_attempts: int = 5
    lockout_duration: int = 300  # 5 minutes


@dataclass
class AppConfig:
    """Main application configuration."""

    environment: str = "development"
    debug: bool = False
    database: DatabaseConfig = None
    api: APIConfig = None
    logging: LoggingConfig = None
    security: SecurityConfig = None

    def __post_init__(self):
        """Initialize nested configurations if not provided."""
        if self.database is None:
            self.database = DatabaseConfig()
        if self.api is None:
            self.api = APIConfig()
        if self.logging is None:
            self.logging = LoggingConfig()
        if self.security is None:
            self.security = SecurityConfig()


class ConfigurationManager:
    """Manages application configuration loading and validation."""

    def __init__(self, config_path: Optional[str] = None):
        """Initialize configuration manager.

        Args:
            config_path: Path to configuration file
        """
        self.config_path = config_path or self._find_config_file()
        self.config = None
        self.logger = logging.getLogger(__name__)

    def _find_config_file(self) -> Optional[str]:
        """Find configuration file in standard locations."""
        possible_paths = [
            "config.json",
            "config/config.json",
            "app_config.json",
            os.path.expanduser("~/.app_config.json"),
            "/etc/app/config.json",
        ]

        for path in possible_paths:
            if Path(path).exists():
                return path

        return None

    def load_config(self) -> AppConfig:
        """Load configuration from file and environment variables.

        Returns:
            AppConfig: Loaded application configuration

        Raises:
            ConfigurationError: If configuration cannot be loaded
        """
        try:
            # Start with default configuration
            config_data = {}

            # Load from file if available
            if self.config_path and Path(self.config_path).exists():
                config_data = self._load_config_file(self.config_path)
                self.logger.info(f"Loaded configuration from {self.config_path}")

            # Override with environment variables
            env_overrides = self._load_environment_variables()
            config_data = self._merge_configs(config_data, env_overrides)

            # Create configuration object
            self.config = self._create_config_object(config_data)

            # Validate configuration
            self._validate_config(self.config)

            self.logger.info("Configuration loaded successfully")
            return self.config

        except Exception as e:
            self.logger.error(f"Failed to load configuration: {e}")
            raise ConfigurationError(f"Configuration loading failed: {e}")

    def _load_config_file(self, file_path: str) -> Dict[str, Any]:
        """Load configuration from JSON file.

        Args:
            file_path: Path to configuration file

        Returns:
            Dict: Configuration data
        """
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            raise ConfigurationError(f"Failed to load config file {file_path}: {e}")

    def _load_environment_variables(self) -> Dict[str, Any]:
        """Load configuration from environment variables.

        Returns:
            Dict: Environment variable overrides
        """
        env_config = {}

        # Database configuration
        if os.getenv("DB_HOST"):
            env_config.setdefault("database", {})["host"] = os.getenv("DB_HOST")
        if os.getenv("DB_PORT"):
            env_config.setdefault("database", {})["port"] = int(os.getenv("DB_PORT"))
        if os.getenv("DB_NAME"):
            env_config.setdefault("database", {})["database"] = os.getenv("DB_NAME")
        if os.getenv("DB_USER"):
            env_config.setdefault("database", {})["username"] = os.getenv("DB_USER")
        if os.getenv("DB_PASSWORD"):
            env_config.setdefault("database", {})["password"] = os.getenv("DB_PASSWORD")

        # API configuration
        if os.getenv("API_HOST"):
            env_config.setdefault("api", {})["host"] = os.getenv("API_HOST")
        if os.getenv("API_PORT"):
            env_config.setdefault("api", {})["port"] = int(os.getenv("API_PORT"))
        if os.getenv("API_DEBUG"):
            env_config.setdefault("api", {})["debug"] = (
                os.getenv("API_DEBUG").lower() == "true"
            )

        # Security configuration
        if os.getenv("SECRET_KEY"):
            env_config.setdefault("security", {})["secret_key"] = os.getenv(
                "SECRET_KEY"
            )
        if os.getenv("JWT_ALGORITHM"):
            env_config.setdefault("security", {})["jwt_algorithm"] = os.getenv(
                "JWT_ALGORITHM"
            )

        # Logging configuration
        if os.getenv("LOG_LEVEL"):
            env_config.setdefault("logging", {})["level"] = os.getenv("LOG_LEVEL")
        if os.getenv("LOG_FILE"):
            env_config.setdefault("logging", {})["file_path"] = os.getenv("LOG_FILE")

        # Application environment
        if os.getenv("ENVIRONMENT"):
            env_config["environment"] = os.getenv("ENVIRONMENT")
        if os.getenv("DEBUG"):
            env_config["debug"] = os.getenv("DEBUG").lower() == "true"

        return env_config

    def _merge_configs(
        self, base_config: Dict[str, Any], override_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Merge configuration dictionaries with override taking precedence.

        Args:
            base_config: Base configuration
            override_config: Override configuration

        Returns:
            Dict: Merged configuration
        """
        merged = base_config.copy()

        for key, value in override_config.items():
            if (
                key in merged
                and isinstance(merged[key], dict)
                and isinstance(value, dict)
            ):
                merged[key] = self._merge_configs(merged[key], value)
            else:
                merged[key] = value

        return merged

    def _create_config_object(self, config_data: Dict[str, Any]) -> AppConfig:
        """Create AppConfig object from configuration data.

        Args:
            config_data: Configuration data dictionary

        Returns:
            AppConfig: Application configuration object
        """
        # Extract nested configurations
        db_config = DatabaseConfig(**config_data.get("database", {}))
        api_config = APIConfig(**config_data.get("api", {}))
        logging_config = LoggingConfig(**config_data.get("logging", {}))
        security_config = SecurityConfig(**config_data.get("security", {}))

        # Create main configuration
        app_config = AppConfig(
            environment=config_data.get("environment", "development"),
            debug=config_data.get("debug", False),
            database=db_config,
            api=api_config,
            logging=logging_config,
            security=security_config,
        )

        return app_config

    def _validate_config(self, config: AppConfig) -> None:
        """Validate configuration values.

        Args:
            config: Configuration to validate

        Raises:
            ConfigurationError: If configuration is invalid
        """
        errors = []

        # Validate database configuration
        if config.database.port < 1 or config.database.port > 65535:
            errors.append("Database port must be between 1 and 65535")

        if not config.database.database:
            errors.append("Database name is required")

        # Validate API configuration
        if config.api.port < 1 or config.api.port > 65535:
            errors.append("API port must be between 1 and 65535")

        if config.api.rate_limit < 1:
            errors.append("API rate limit must be positive")

        # Validate security configuration
        if not config.security.secret_key:
            errors.append("Secret key is required for security")

        if config.security.password_min_length < 1:
            errors.append("Password minimum length must be positive")

        # Validate logging configuration
        valid_log_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if config.logging.level.upper() not in valid_log_levels:
            errors.append(f"Log level must be one of: {', '.join(valid_log_levels)}")

        if errors:
            raise ConfigurationError(
                f"Configuration validation failed: {'; '.join(errors)}"
            )

    def save_config(self, config: AppConfig, file_path: Optional[str] = None) -> None:
        """Save configuration to file.

        Args:
            config: Configuration to save
            file_path: Optional file path (defaults to current config path)
        """
        output_path = file_path or self.config_path or "config.json"

        try:
            config_dict = asdict(config)
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(config_dict, f, indent=2)

            self.logger.info(f"Configuration saved to {output_path}")

        except Exception as e:
            raise ConfigurationError(f"Failed to save configuration: {e}")

    def get_config(self) -> Optional[AppConfig]:
        """Get current configuration.

        Returns:
            AppConfig: Current configuration or None if not loaded
        """
        return self.config

    def reload_config(self) -> AppConfig:
        """Reload configuration from file and environment.

        Returns:
            AppConfig: Reloaded configuration
        """
        self.logger.info("Reloading configuration")
        return self.load_config()


def setup_logging(config: LoggingConfig) -> None:
    """Setup logging based on configuration.

    Args:
        config: Logging configuration
    """
    import logging.handlers

    # Create logger
    logger = logging.getLogger()
    logger.setLevel(getattr(logging, config.level.upper()))

    # Clear existing handlers
    logger.handlers.clear()

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(getattr(logging, config.level.upper()))
    console_formatter = logging.Formatter(config.format)
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    # File handler (if configured)
    if config.file_path:
        file_handler = logging.handlers.RotatingFileHandler(
            config.file_path,
            maxBytes=config.max_file_size,
            backupCount=config.backup_count,
        )
        file_handler.setLevel(getattr(logging, config.level.upper()))
        file_formatter = logging.Formatter(config.format)
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)


def load_configuration(config_path: Optional[str] = None) -> AppConfig:
    """Convenience function to load application configuration.

    Args:
        config_path: Optional path to configuration file

    Returns:
        AppConfig: Loaded configuration
    """
    manager = ConfigurationManager(config_path)
    return manager.load_config()
