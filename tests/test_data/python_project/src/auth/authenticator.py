"""User authentication and authorization module."""

import hashlib
import secrets
from datetime import datetime
from typing import Optional


class AuthenticationError(Exception):
    """Raised when authentication fails."""

    pass


class PermissionError(Exception):
    """Raised when user lacks required permissions."""

    pass


class User:
    """Represents a user in the system."""

    def __init__(self, username: str, email: str, password_hash: str):
        self.username = username
        self.email = email
        self.password_hash = password_hash
        self.created_at = datetime.now()
        self.last_login = None
        self.is_active = True
        self.permissions = set()

    def check_password(self, password: str) -> bool:
        """Verify password against stored hash."""
        return self.password_hash == hash_password(password)

    def has_permission(self, permission: str) -> bool:
        """Check if user has specific permission."""
        return permission in self.permissions

    def add_permission(self, permission: str) -> None:
        """Grant permission to user."""
        self.permissions.add(permission)


def hash_password(password: str) -> str:
    """Hash password using secure algorithm."""
    salt = secrets.token_hex(16)
    password_hash = hashlib.pbkdf2_hmac(
        "sha256", password.encode(), salt.encode(), 100000
    )
    return f"{salt}:{password_hash.hex()}"


def verify_password(password: str, password_hash: str) -> bool:
    """Verify password against hash."""
    try:
        salt, hash_hex = password_hash.split(":")
        password_bytes = hashlib.pbkdf2_hmac(
            "sha256", password.encode(), salt.encode(), 100000
        )
        return password_bytes.hex() == hash_hex
    except ValueError:
        return False


def authenticate_user(username: str, password: str, user_database) -> Optional[User]:
    """Authenticate user with username and password."""
    user = user_database.get_user(username)
    if not user:
        raise AuthenticationError("User not found")

    if not user.is_active:
        raise AuthenticationError("Account is disabled")

    if not user.check_password(password):
        raise AuthenticationError("Invalid password")

    user.last_login = datetime.now()
    return user


def create_session_token(user: User) -> str:
    """Create secure session token for user."""
    token_data = f"{user.username}:{datetime.now().isoformat()}:{secrets.token_hex(16)}"
    return hashlib.sha256(token_data.encode()).hexdigest()


def check_permissions(user: User, required_permissions: list) -> bool:
    """Check if user has all required permissions."""
    if not user.is_active:
        return False

    for permission in required_permissions:
        if not user.has_permission(permission):
            raise PermissionError(f"Missing permission: {permission}")

    return True
