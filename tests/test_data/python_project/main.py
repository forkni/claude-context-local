"""Main application entry point."""

import logging

from src.api.handlers import UserHandler
from src.auth.authenticator import User, authenticate_user
from src.database.connection import DatabaseConnection
from src.utils.helpers import ConfigManager


def setup_logging():
    """Configure application logging."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )


def main():
    """Main application function."""
    setup_logging()
    logger = logging.getLogger(__name__)
    
    logger.info("Starting application")
    
    # Initialize configuration
    config = ConfigManager('config.json')
    
    # Setup database
    db = DatabaseConnection(config.get('database_path', 'app.db'))
    db.connect()
    
    # Create services
    user_handler = UserHandler(None)  # Would inject real service
    
    logger.info("Application initialized successfully")


if __name__ == "__main__":
    main()