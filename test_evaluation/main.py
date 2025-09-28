"""Main application entry point."""

import logging
import signal
import sys
from pathlib import Path
from typing import Optional

# Add project modules to path
sys.path.insert(0, str(Path(__file__).parent))

from api.handlers import APIHandler
from auth import AuthManager
from config.settings import ConfigurationManager, setup_logging
from database.connection import DatabaseConnection
from models.user import UserManager


class Application:
    """Main application class."""

    def __init__(self, config_path: Optional[str] = None):
        """Initialize application.

        Args:
            config_path: Optional configuration file path
        """
        self.config_manager = ConfigurationManager(config_path)
        self.config = None
        self.db_connection = None
        self.api_handler = None
        self.auth_manager = None
        self.user_manager = None
        self.logger = None
        self._shutdown_requested = False

    def setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown."""

        def signal_handler(signum, frame):
            self.logger.info(f"Received signal {signum}, initiating shutdown...")
            self._shutdown_requested = True

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

    def initialize(self) -> bool:
        """Initialize application components.

        Returns:
            bool: True if initialization successful
        """
        try:
            # Load configuration
            self.config = self.config_manager.load_config()

            # Setup logging
            setup_logging(self.config.logging)
            self.logger = logging.getLogger(__name__)

            self.logger.info("Starting application initialization")
            self.logger.info(f"Environment: {self.config.environment}")
            self.logger.info(f"Debug mode: {self.config.debug}")

            # Setup signal handlers
            self.setup_signal_handlers()

            # Initialize database connection
            self.db_connection = DatabaseConnection(
                db_path=f"{self.config.database.database}.db"
            )
            self.db_connection.initialize_database()
            self.logger.info("Database initialized")

            # Initialize managers
            self.auth_manager = AuthManager()
            self.user_manager = UserManager()
            self.logger.info("Authentication and user managers initialized")

            # Initialize API handler
            self.api_handler = APIHandler(self.db_connection)
            self.logger.info("API handler initialized")

            # Create default admin user if needed
            self._create_default_users()

            self.logger.info("Application initialization completed successfully")
            return True

        except Exception as e:
            if self.logger:
                self.logger.error(
                    f"Application initialization failed: {e}", exc_info=True
                )
            else:
                print(f"Failed to initialize application: {e}")
            return False

    def _create_default_users(self):
        """Create default users for development."""
        try:
            # Create admin user
            admin_user = self.auth_manager.register_user("admin", "admin@example.com")
            if admin_user:
                self.logger.info("Default admin user created")

            # Create test user
            test_user = self.auth_manager.register_user("testuser", "test@example.com")
            if test_user:
                self.logger.info("Default test user created")

        except Exception as e:
            self.logger.warning(f"Failed to create default users: {e}")

    def run_demo(self):
        """Run application demonstration."""
        if not self.initialize():
            return 1

        self.logger.info("=" * 50)
        self.logger.info("APPLICATION DEMO STARTING")
        self.logger.info("=" * 50)

        try:
            # Demo authentication
            self._demo_authentication()

            # Demo API calls
            self._demo_api_calls()

            # Demo user management
            self._demo_user_management()

            # Demo database operations
            self._demo_database_operations()

            # Demo configuration
            self._demo_configuration()

            self.logger.info("=" * 50)
            self.logger.info("APPLICATION DEMO COMPLETED SUCCESSFULLY")
            self.logger.info("=" * 50)

            return 0

        except Exception as e:
            self.logger.error(f"Demo failed: {e}", exc_info=True)
            return 1

        finally:
            self.cleanup()

    def _demo_authentication(self):
        """Demonstrate authentication functionality."""
        self.logger.info("--- Authentication Demo ---")

        # Test authentication
        user = self.auth_manager.authenticate("admin", "secure_password")
        if user:
            self.logger.info(f"Authentication successful for user: {user.username}")
        else:
            self.logger.warning("Authentication failed")

        # Test invalid authentication
        invalid_user = self.auth_manager.authenticate("admin", "wrong_password")
        if not invalid_user:
            self.logger.info("Invalid authentication correctly rejected")

    def _demo_api_calls(self):
        """Demonstrate API functionality."""
        self.logger.info("--- API Demo ---")

        # Test health check
        health_response = self.api_handler.handle_health({})
        self.logger.info(f"Health check: {health_response['status']}")

        # Test login
        login_data = {
            "username": "admin",
            "password": "admin123",  # This should work with mock auth
        }
        login_response = self.api_handler.handle_login(login_data)
        self.logger.info(f"Login response: {login_response['status']}")

        # Test registration
        register_data = {
            "username": "newuser",
            "email": "newuser@example.com",
            "password": "secure_password123",
        }
        register_response = self.api_handler.handle_register(register_data)
        self.logger.info(f"Registration response: {register_response['status']}")

    def _demo_user_management(self):
        """Demonstrate user management functionality."""
        self.logger.info("--- User Management Demo ---")

        # Create users
        try:
            user1 = self.user_manager.create_user(
                "demouser1", "demo1@example.com", "hashed_password"
            )
            self.logger.info(f"Created user: {user1}")

            user2 = self.user_manager.create_user(
                "demouser2", "demo2@example.com", "hashed_password"
            )
            self.logger.info(f"Created user: {user2}")

        except ValueError as e:
            self.logger.info(f"User creation handled: {e}")

        # Search users
        results = self.user_manager.search_users("demo")
        self.logger.info(f"Search results for 'demo': {len(results)} users found")

        # Get statistics
        stats = self.user_manager.get_user_statistics()
        self.logger.info(f"User statistics: {stats}")

    def _demo_database_operations(self):
        """Demonstrate database operations."""
        self.logger.info("--- Database Demo ---")

        try:
            # Test query execution
            results = self.db_connection.execute_query(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
            table_names = [row[0] for row in results]
            self.logger.info(f"Database tables: {table_names}")

            # Test user insertion
            user_id = self.db_connection.insert_user(
                "dbuser", "dbuser@example.com", "hashed_password"
            )
            self.logger.info(f"Inserted user with ID: {user_id}")

            # Test session cleanup
            self.db_connection.cleanup_expired_sessions()
            self.logger.info("Session cleanup completed")

        except Exception as e:
            self.logger.warning(f"Database operation failed: {e}")

    def _demo_configuration(self):
        """Demonstrate configuration functionality."""
        self.logger.info("--- Configuration Demo ---")

        self.logger.info(f"Environment: {self.config.environment}")
        self.logger.info(f"Database host: {self.config.database.host}")
        self.logger.info(f"API port: {self.config.api.port}")
        self.logger.info(f"Debug mode: {self.config.debug}")
        self.logger.info(f"Log level: {self.config.logging.level}")

    def cleanup(self):
        """Cleanup application resources."""
        if self.logger:
            self.logger.info("Cleaning up application resources...")

        # Close database connection
        if self.db_connection:
            # Database connections are closed automatically via context manager
            pass

        if self.logger:
            self.logger.info("Cleanup completed")

    def run_interactive_shell(self):
        """Run interactive shell for testing."""
        if not self.initialize():
            return 1

        self.logger.info("Interactive shell started. Type 'help' for commands.")

        while not self._shutdown_requested:
            try:
                command = input(">>> ").strip()

                if command == "help":
                    print("Available commands:")
                    print("  auth <username> <password> - Test authentication")
                    print("  users - List all users")
                    print("  stats - Show user statistics")
                    print("  health - Check application health")
                    print("  config - Show configuration")
                    print("  quit - Exit application")

                elif command == "quit":
                    break

                elif command.startswith("auth "):
                    parts = command.split()
                    if len(parts) == 3:
                        username, password = parts[1], parts[2]
                        user = self.auth_manager.authenticate(username, password)
                        if user:
                            print(f"Authentication successful: {user.username}")
                        else:
                            print("Authentication failed")
                    else:
                        print("Usage: auth <username> <password>")

                elif command == "users":
                    users = list(self.user_manager.users.values())
                    print(f"Total users: {len(users)}")
                    for user in users[:5]:  # Show first 5
                        print(f"  {user}")

                elif command == "stats":
                    stats = self.user_manager.get_user_statistics()
                    for key, value in stats.items():
                        print(f"  {key}: {value}")

                elif command == "health":
                    response = self.api_handler.handle_health({})
                    print(f"Health: {response['status']}")

                elif command == "config":
                    print(f"Environment: {self.config.environment}")
                    print(f"Debug: {self.config.debug}")
                    print(f"API Port: {self.config.api.port}")

                else:
                    print("Unknown command. Type 'help' for available commands.")

            except KeyboardInterrupt:
                break
            except EOFError:
                break
            except Exception as e:
                print(f"Error: {e}")

        self.cleanup()
        return 0


def main():
    """Application entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Application Demo")
    parser.add_argument("--config", "-c", help="Configuration file path")
    parser.add_argument(
        "--mode",
        "-m",
        choices=["demo", "interactive"],
        default="demo",
        help="Run mode (default: demo)",
    )

    args = parser.parse_args()

    # Create application
    app = Application(args.config)

    # Run based on mode
    if args.mode == "interactive":
        return app.run_interactive_shell()
    else:
        return app.run_demo()


if __name__ == "__main__":
    sys.exit(main())
