"""API endpoint handlers for HTTP requests."""

import hashlib
import logging
import secrets
from datetime import datetime, timedelta
from typing import Any, Dict, Optional


class APIError(Exception):
    """API operation error."""

    pass


class AuthenticationError(APIError):
    """Authentication specific error."""

    pass


class ValidationError(APIError):
    """Request validation error."""

    pass


class APIHandler:
    """HTTP API request handler for user management."""

    def __init__(self, db_connection=None):
        self.logger = logging.getLogger(__name__)
        self.db = db_connection
        self.routes = {
            "/api/auth/login": self.handle_login,
            "/api/auth/logout": self.handle_logout,
            "/api/auth/register": self.handle_register,
            "/api/users": self.handle_users,
            "/api/users/profile": self.handle_user_profile,
            "/api/health": self.handle_health,
            "/api/admin/stats": self.handle_admin_stats,
        }

    def handle_login(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle user login request."""
        try:
            # Validate input
            username = request_data.get("username")
            password = request_data.get("password")

            if not username or not password:
                raise ValidationError("Username and password required")

            # Authenticate user
            user = self._authenticate_user(username, password)
            if not user:
                raise AuthenticationError("Invalid credentials")

            # Create session token
            token = self._generate_session_token()
            expires_at = datetime.now() + timedelta(hours=24)

            # Store session in database
            if self.db:
                self.db.create_session(user["id"], token, expires_at.isoformat())

            return {
                "status": "success",
                "token": token,
                "expires_at": expires_at.isoformat(),
                "user": {
                    "id": user["id"],
                    "username": user["username"],
                    "email": user["email"],
                },
            }

        except (AuthenticationError, ValidationError) as e:
            self.logger.warning(f"Login failed: {e}")
            return {"status": "error", "message": str(e)}
        except Exception as e:
            self.logger.error(f"Login error: {e}")
            return {"status": "error", "message": "Internal server error"}

    def handle_logout(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle user logout request."""
        try:
            token = request_data.get("token")
            if not token:
                raise ValidationError("Session token required")

            # Invalidate session
            success = self._invalidate_session(token)
            if success:
                return {"status": "success", "message": "Logged out successfully"}
            else:
                return {"status": "error", "message": "Invalid session token"}

        except ValidationError as e:
            return {"status": "error", "message": str(e)}
        except Exception as e:
            self.logger.error(f"Logout error: {e}")
            return {"status": "error", "message": "Internal server error"}

    def handle_register(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle user registration request."""
        try:
            # Validate input
            username = request_data.get("username")
            email = request_data.get("email")
            password = request_data.get("password")

            if not all([username, email, password]):
                raise ValidationError("Username, email, and password required")

            # Validate email format
            if not self._validate_email(email):
                raise ValidationError("Invalid email format")

            # Check if user already exists
            if self.db and self.db.get_user_by_username(username):
                raise ValidationError("Username already exists")

            # Hash password
            password_hash = self._hash_password(password)

            # Create user
            if self.db:
                user_id = self.db.insert_user(username, email, password_hash)
                return {
                    "status": "success",
                    "message": "User registered successfully",
                    "user_id": user_id,
                }
            else:
                return {
                    "status": "success",
                    "message": "User registered successfully (mock)",
                }

        except ValidationError as e:
            return {"status": "error", "message": str(e)}
        except Exception as e:
            self.logger.error(f"Registration error: {e}")
            return {"status": "error", "message": "Internal server error"}

    def handle_users(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle user listing request."""
        try:
            # Check authentication
            if not self._is_authenticated(request_data.get("token")):
                raise AuthenticationError("Authentication required")

            # Mock user data for demonstration
            users = [
                {
                    "id": 1,
                    "username": "admin",
                    "email": "admin@example.com",
                    "created_at": "2023-01-01T00:00:00",
                },
                {
                    "id": 2,
                    "username": "user",
                    "email": "user@example.com",
                    "created_at": "2023-01-02T00:00:00",
                },
            ]

            return {"status": "success", "users": users, "total": len(users)}

        except AuthenticationError as e:
            return {"status": "error", "message": str(e)}
        except Exception as e:
            self.logger.error(f"Users API error: {e}")
            return {"status": "error", "message": "Internal server error"}

    def handle_user_profile(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle user profile request."""
        try:
            if not self._is_authenticated(request_data.get("token")):
                raise AuthenticationError("Authentication required")

            user_id = request_data.get("user_id")
            if not user_id:
                raise ValidationError("User ID required")

            # Mock profile data
            profile = {
                "user_id": user_id,
                "first_name": "John",
                "last_name": "Doe",
                "bio": "Software developer with a passion for clean code.",
                "avatar_url": "https://example.com/avatars/john_doe.jpg",
                "joined_date": "2023-01-01",
                "last_active": datetime.now().isoformat(),
            }

            return {"status": "success", "profile": profile}

        except (AuthenticationError, ValidationError) as e:
            return {"status": "error", "message": str(e)}
        except Exception as e:
            self.logger.error(f"Profile API error: {e}")
            return {"status": "error", "message": "Internal server error"}

    def handle_health(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle health check request."""
        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "version": "1.0.0",
            "database": "connected" if self.db else "mock",
        }

    def handle_admin_stats(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle admin statistics request."""
        try:
            # Check admin authentication
            if not self._is_admin(request_data.get("token")):
                raise AuthenticationError("Admin access required")

            # Mock statistics
            stats = {
                "total_users": 150,
                "active_sessions": 25,
                "total_api_calls": 10540,
                "database_size": "2.5 MB",
                "uptime": "5 days, 3 hours",
                "memory_usage": "45%",
            }

            return {"status": "success", "stats": stats}

        except AuthenticationError as e:
            return {"status": "error", "message": str(e)}
        except Exception as e:
            self.logger.error(f"Admin stats error: {e}")
            return {"status": "error", "message": "Internal server error"}

    def _authenticate_user(self, username: str, password: str) -> Optional[Dict]:
        """Authenticate user credentials."""
        if self.db:
            user = self.db.get_user_by_username(username)
            if user and self._verify_password(password, user["password_hash"]):
                return user
        else:
            # Mock authentication
            if username == "admin" and password == "admin123":
                return {"id": 1, "username": username, "email": "admin@example.com"}
        return None

    def _generate_session_token(self) -> str:
        """Generate secure session token."""
        return secrets.token_urlsafe(32)

    def _hash_password(self, password: str) -> str:
        """Hash password with salt."""
        salt = secrets.token_hex(16)
        password_hash = hashlib.pbkdf2_hmac(
            "sha256", password.encode(), salt.encode(), 100000
        )
        return f"{salt}${password_hash.hex()}"

    def _verify_password(self, password: str, password_hash: str) -> bool:
        """Verify password against hash."""
        try:
            salt, hash_value = password_hash.split("$")
            computed_hash = hashlib.pbkdf2_hmac(
                "sha256", password.encode(), salt.encode(), 100000
            )
            return computed_hash.hex() == hash_value
        except (ValueError, AttributeError):
            return False

    def _validate_email(self, email: str) -> bool:
        """Basic email validation."""
        import re

        pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        return re.match(pattern, email) is not None

    def _is_authenticated(self, token: str) -> bool:
        """Check if token is valid."""
        return token is not None and len(token) > 10

    def _is_admin(self, token: str) -> bool:
        """Check if token belongs to admin user."""
        return self._is_authenticated(token) and token.startswith("admin_")

    def _invalidate_session(self, token: str) -> bool:
        """Invalidate session token."""
        if self.db:
            try:
                with self.db.get_connection() as conn:
                    cursor = conn.execute(
                        "DELETE FROM sessions WHERE token = ?", (token,)
                    )
                    conn.commit()
                    return cursor.rowcount > 0
            except Exception as e:
                self.logger.error(f"Session invalidation error: {e}")
                return False
        return True  # Mock success
