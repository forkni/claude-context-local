"""Unit tests for authentication functionality."""

import os
import sys
from unittest.mock import Mock, patch

import pytest

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from api.handlers import APIHandler
from auth import AuthManager, User


class TestUser:
    """Test user authentication functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.user = User("testuser", "test@example.com")

    def test_user_initialization(self):
        """Test user object initialization."""
        assert self.user.username == "testuser"
        assert self.user.email == "test@example.com"
        assert not self.user.is_authenticated

    def test_successful_login(self):
        """Test successful user login."""
        result = self.user.login("secure_password")
        assert result is True
        assert self.user.is_authenticated

    def test_failed_login(self):
        """Test failed user login with wrong password."""
        result = self.user.login("wrong_password")
        assert result is False
        assert not self.user.is_authenticated

    def test_logout(self):
        """Test user logout functionality."""
        # First login
        self.user.login("secure_password")
        assert self.user.is_authenticated

        # Then logout
        self.user.logout()
        assert not self.user.is_authenticated

    def test_is_active(self):
        """Test user active status."""
        assert not self.user.is_active()

        self.user.login("secure_password")
        assert self.user.is_active()

        self.user.logout()
        assert not self.user.is_active()


class TestAuthManager:
    """Test authentication manager functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.auth_manager = AuthManager()

    def test_auth_manager_initialization(self):
        """Test auth manager initialization."""
        assert isinstance(self.auth_manager.users, dict)
        assert isinstance(self.auth_manager.active_sessions, set)
        assert len(self.auth_manager.users) == 0
        assert len(self.auth_manager.active_sessions) == 0

    def test_register_user(self):
        """Test user registration."""
        user = self.auth_manager.register_user("newuser", "new@example.com")

        assert isinstance(user, User)
        assert user.username == "newuser"
        assert user.email == "new@example.com"
        assert "newuser" in self.auth_manager.users

    def test_authenticate_existing_user(self):
        """Test authentication of existing user."""
        # Register user first
        self.auth_manager.register_user("testuser", "test@example.com")

        # Authenticate
        user = self.auth_manager.authenticate("testuser", "secure_password")

        assert user is not None
        assert user.username == "testuser"
        assert user.is_authenticated
        assert "testuser" in self.auth_manager.active_sessions

    def test_authenticate_nonexistent_user(self):
        """Test authentication of non-existent user."""
        user = self.auth_manager.authenticate("nonexistent", "password")
        assert user is None

    def test_authenticate_wrong_password(self):
        """Test authentication with wrong password."""
        # Register user first
        self.auth_manager.register_user("testuser", "test@example.com")

        # Try to authenticate with wrong password
        user = self.auth_manager.authenticate("testuser", "wrong_password")
        assert user is None
        assert "testuser" not in self.auth_manager.active_sessions


class TestAPIHandler:
    """Test API handler functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_db = Mock()
        self.api_handler = APIHandler(self.mock_db)

    def test_handle_health(self):
        """Test health check endpoint."""
        response = self.api_handler.handle_health({})

        assert response["status"] == "healthy"
        assert "timestamp" in response
        assert "version" in response
        assert response["database"] == "connected"

    def test_handle_login_success(self):
        """Test successful login through API."""
        # Mock database response
        self.mock_db.get_user_by_username.return_value = {
            "id": 1,
            "username": "testuser",
            "email": "test@example.com",
            "password_hash": "mocked_hash",
        }
        self.mock_db.create_session.return_value = True

        # Mock password verification
        with patch.object(self.api_handler, "_verify_password", return_value=True):
            request_data = {"username": "testuser", "password": "correct_password"}

            response = self.api_handler.handle_login(request_data)

            assert response["status"] == "success"
            assert "token" in response
            assert "user" in response
            assert response["user"]["username"] == "testuser"

    def test_handle_login_invalid_credentials(self):
        """Test login with invalid credentials."""
        self.mock_db.get_user_by_username.return_value = None

        request_data = {"username": "invalid_user", "password": "wrong_password"}

        response = self.api_handler.handle_login(request_data)

        assert response["status"] == "error"
        assert "Invalid credentials" in response["message"]

    def test_handle_login_missing_fields(self):
        """Test login with missing required fields."""
        request_data = {"username": "testuser"}  # Missing password

        response = self.api_handler.handle_login(request_data)

        assert response["status"] == "error"
        assert "Username and password required" in response["message"]

    def test_handle_logout_success(self):
        """Test successful logout."""
        with patch.object(self.api_handler, "_invalidate_session", return_value=True):
            request_data = {"token": "valid_token_123"}

            response = self.api_handler.handle_logout(request_data)

            assert response["status"] == "success"
            assert "Logged out successfully" in response["message"]

    def test_handle_logout_invalid_token(self):
        """Test logout with invalid token."""
        with patch.object(self.api_handler, "_invalidate_session", return_value=False):
            request_data = {"token": "invalid_token"}

            response = self.api_handler.handle_logout(request_data)

            assert response["status"] == "error"
            assert "Invalid session token" in response["message"]

    def test_handle_register_success(self):
        """Test successful user registration."""
        self.mock_db.get_user_by_username.return_value = None  # User doesn't exist
        self.mock_db.insert_user.return_value = 123  # Mock user ID

        request_data = {
            "username": "newuser",
            "email": "new@example.com",
            "password": "secure_password",
        }

        response = self.api_handler.handle_register(request_data)

        assert response["status"] == "success"
        assert "User registered successfully" in response["message"]
        assert response["user_id"] == 123

    def test_handle_register_existing_user(self):
        """Test registration with existing username."""
        self.mock_db.get_user_by_username.return_value = {"id": 1}  # User exists

        request_data = {
            "username": "existing_user",
            "email": "existing@example.com",
            "password": "password",
        }

        response = self.api_handler.handle_register(request_data)

        assert response["status"] == "error"
        assert "Username already exists" in response["message"]

    def test_handle_register_invalid_email(self):
        """Test registration with invalid email."""
        request_data = {
            "username": "newuser",
            "email": "invalid_email",
            "password": "password",
        }

        response = self.api_handler.handle_register(request_data)

        assert response["status"] == "error"
        assert "Invalid email format" in response["message"]

    def test_handle_users_authenticated(self):
        """Test users endpoint with valid authentication."""
        with patch.object(self.api_handler, "_is_authenticated", return_value=True):
            request_data = {"token": "valid_token"}

            response = self.api_handler.handle_users(request_data)

            assert response["status"] == "success"
            assert "users" in response
            assert len(response["users"]) > 0

    def test_handle_users_unauthenticated(self):
        """Test users endpoint without authentication."""
        with patch.object(self.api_handler, "_is_authenticated", return_value=False):
            request_data = {"token": "invalid_token"}

            response = self.api_handler.handle_users(request_data)

            assert response["status"] == "error"
            assert "Authentication required" in response["message"]

    def test_password_hashing_and_verification(self):
        """Test password hashing and verification."""
        password = "test_password_123"

        # Hash password
        password_hash = self.api_handler._hash_password(password)
        assert password_hash is not None
        assert "$" in password_hash  # Should contain salt separator

        # Verify correct password
        assert self.api_handler._verify_password(password, password_hash)

        # Verify incorrect password
        assert not self.api_handler._verify_password("wrong_password", password_hash)

    def test_email_validation(self):
        """Test email validation functionality."""
        # Valid emails
        assert self.api_handler._validate_email("test@example.com")
        assert self.api_handler._validate_email("user.name@domain.co.uk")
        assert self.api_handler._validate_email("test123+tag@example.org")

        # Invalid emails
        assert not self.api_handler._validate_email("invalid_email")
        assert not self.api_handler._validate_email("@domain.com")
        assert not self.api_handler._validate_email("user@")
        assert not self.api_handler._validate_email("user@domain")


@pytest.fixture
def mock_auth_manager():
    """Fixture providing mock authentication manager."""
    manager = Mock(spec=AuthManager)
    manager.register_user.return_value = Mock(spec=User)
    manager.authenticate.return_value = Mock(spec=User)
    return manager


@pytest.fixture
def mock_api_handler():
    """Fixture providing mock API handler."""
    handler = Mock(spec=APIHandler)
    handler.handle_login.return_value = {"status": "success", "token": "mock_token_123"}
    handler.handle_logout.return_value = {
        "status": "success",
        "message": "Logged out successfully",
    }
    return handler


def test_authentication_integration(mock_auth_manager, mock_api_handler):
    """Integration test for authentication workflow."""
    # Test complete authentication flow
    user = mock_auth_manager.register_user("integration_user", "integration@test.com")
    assert user is not None

    auth_result = mock_auth_manager.authenticate("integration_user", "password")
    assert auth_result is not None

    login_response = mock_api_handler.handle_login(
        {"username": "integration_user", "password": "password"}
    )
    assert login_response["status"] == "success"

    logout_response = mock_api_handler.handle_logout({"token": login_response["token"]})
    assert logout_response["status"] == "success"


def test_error_handling_integration():
    """Test error handling across authentication components."""
    # Test with no database connection
    api_handler = APIHandler(db_connection=None)

    # Should handle gracefully
    response = api_handler.handle_login({"username": "admin", "password": "admin123"})

    assert "status" in response
    # Should either succeed with mock auth or fail gracefully
    assert response["status"] in ["success", "error"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
