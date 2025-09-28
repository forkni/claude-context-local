"""User data models and related functionality."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class UserRole(Enum):
    """User role enumeration."""

    ADMIN = "admin"
    USER = "user"
    MODERATOR = "moderator"
    GUEST = "guest"


class UserStatus(Enum):
    """User status enumeration."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    PENDING = "pending"


@dataclass
class UserProfile:
    """User profile information."""

    first_name: str = ""
    last_name: str = ""
    bio: str = ""
    avatar_url: str = ""
    phone_number: str = ""
    date_of_birth: Optional[datetime] = None
    location: str = ""
    website: str = ""
    social_links: Dict[str, str] = field(default_factory=dict)

    @property
    def full_name(self) -> str:
        """Get user's full name."""
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.first_name or self.last_name or ""

    @property
    def display_name(self) -> str:
        """Get display name (full name or fallback)."""
        return self.full_name or "Anonymous User"


@dataclass
class UserPreferences:
    """User preferences and settings."""

    language: str = "en"
    timezone: str = "UTC"
    email_notifications: bool = True
    push_notifications: bool = True
    theme: str = "light"
    items_per_page: int = 25
    auto_save: bool = True
    privacy_level: str = "public"


@dataclass
class UserStatistics:
    """User activity statistics."""

    login_count: int = 0
    last_login_at: Optional[datetime] = None
    posts_count: int = 0
    comments_count: int = 0
    likes_given: int = 0
    likes_received: int = 0
    followers_count: int = 0
    following_count: int = 0
    reputation_score: int = 0

    def calculate_activity_score(self) -> float:
        """Calculate user activity score based on statistics."""
        score = 0.0
        score += self.posts_count * 2.0
        score += self.comments_count * 1.0
        score += self.likes_given * 0.5
        score += self.likes_received * 1.5
        score += self.reputation_score * 0.1
        return min(score, 100.0)  # Cap at 100


class User:
    """Comprehensive user model."""

    def __init__(
        self,
        user_id: int,
        username: str,
        email: str,
        password_hash: str = "",
        role: UserRole = UserRole.USER,
        status: UserStatus = UserStatus.ACTIVE,
    ):
        """Initialize user instance.

        Args:
            user_id: Unique user identifier
            username: Username
            email: Email address
            password_hash: Hashed password
            role: User role
            status: User status
        """
        self.user_id = user_id
        self.username = username
        self.email = email
        self.password_hash = password_hash
        self.role = role
        self.status = status
        self.created_at = datetime.now()
        self.updated_at = datetime.now()
        self.last_active_at = datetime.now()

        # Related data
        self.profile = UserProfile()
        self.preferences = UserPreferences()
        self.statistics = UserStatistics()
        self.permissions = set()
        self.groups = []

    @property
    def is_active(self) -> bool:
        """Check if user is active."""
        return self.status == UserStatus.ACTIVE

    @property
    def is_admin(self) -> bool:
        """Check if user is admin."""
        return self.role == UserRole.ADMIN

    @property
    def is_moderator(self) -> bool:
        """Check if user is moderator or admin."""
        return self.role in [UserRole.ADMIN, UserRole.MODERATOR]

    @property
    def display_name(self) -> str:
        """Get user display name."""
        return self.profile.display_name or self.username

    def has_permission(self, permission: str) -> bool:
        """Check if user has specific permission.

        Args:
            permission: Permission to check

        Returns:
            bool: True if user has permission
        """
        if self.is_admin:
            return True  # Admins have all permissions

        return permission in self.permissions

    def add_permission(self, permission: str) -> None:
        """Add permission to user.

        Args:
            permission: Permission to add
        """
        self.permissions.add(permission)
        self.updated_at = datetime.now()

    def remove_permission(self, permission: str) -> None:
        """Remove permission from user.

        Args:
            permission: Permission to remove
        """
        self.permissions.discard(permission)
        self.updated_at = datetime.now()

    def update_last_active(self) -> None:
        """Update last active timestamp."""
        self.last_active_at = datetime.now()
        self.statistics.last_login_at = datetime.now()
        self.statistics.login_count += 1

    def update_profile(self, profile_data: Dict[str, Any]) -> None:
        """Update user profile.

        Args:
            profile_data: Profile data to update
        """
        for key, value in profile_data.items():
            if hasattr(self.profile, key):
                setattr(self.profile, key, value)

        self.updated_at = datetime.now()

    def update_preferences(self, preferences_data: Dict[str, Any]) -> None:
        """Update user preferences.

        Args:
            preferences_data: Preferences data to update
        """
        for key, value in preferences_data.items():
            if hasattr(self.preferences, key):
                setattr(self.preferences, key, value)

        self.updated_at = datetime.now()

    def suspend(self, reason: str = "") -> None:
        """Suspend user account.

        Args:
            reason: Reason for suspension
        """
        self.status = UserStatus.SUSPENDED
        self.updated_at = datetime.now()

    def activate(self) -> None:
        """Activate user account."""
        self.status = UserStatus.ACTIVE
        self.updated_at = datetime.now()

    def to_dict(self, include_sensitive: bool = False) -> Dict[str, Any]:
        """Convert user to dictionary.

        Args:
            include_sensitive: Whether to include sensitive data

        Returns:
            Dict: User data
        """
        data = {
            "user_id": self.user_id,
            "username": self.username,
            "email": self.email,
            "role": self.role.value,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "last_active_at": self.last_active_at.isoformat(),
            "profile": {
                "first_name": self.profile.first_name,
                "last_name": self.profile.last_name,
                "bio": self.profile.bio,
                "avatar_url": self.profile.avatar_url,
                "full_name": self.profile.full_name,
                "display_name": self.profile.display_name,
            },
            "preferences": {
                "language": self.preferences.language,
                "timezone": self.preferences.timezone,
                "theme": self.preferences.theme,
            },
            "statistics": {
                "login_count": self.statistics.login_count,
                "activity_score": self.statistics.calculate_activity_score(),
                "reputation_score": self.statistics.reputation_score,
            },
        }

        if include_sensitive:
            data.update(
                {
                    "password_hash": self.password_hash,
                    "permissions": list(self.permissions),
                    "groups": self.groups,
                }
            )

        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "User":
        """Create user from dictionary.

        Args:
            data: User data dictionary

        Returns:
            User: User instance
        """
        user = cls(
            user_id=data["user_id"],
            username=data["username"],
            email=data["email"],
            password_hash=data.get("password_hash", ""),
            role=UserRole(data.get("role", "user")),
            status=UserStatus(data.get("status", "active")),
        )

        # Update timestamps if provided
        if "created_at" in data:
            user.created_at = datetime.fromisoformat(data["created_at"])
        if "updated_at" in data:
            user.updated_at = datetime.fromisoformat(data["updated_at"])
        if "last_active_at" in data:
            user.last_active_at = datetime.fromisoformat(data["last_active_at"])

        # Update profile if provided
        if "profile" in data:
            user.update_profile(data["profile"])

        # Update preferences if provided
        if "preferences" in data:
            user.update_preferences(data["preferences"])

        # Update permissions if provided
        if "permissions" in data:
            user.permissions = set(data["permissions"])

        return user

    def __str__(self) -> str:
        """String representation of user."""
        return f"User(id={self.user_id}, username='{self.username}', role={self.role.value})"

    def __repr__(self) -> str:
        """Detailed string representation of user."""
        return (
            f"User(user_id={self.user_id}, username='{self.username}', "
            f"email='{self.email}', role={self.role.value}, status={self.status.value})"
        )


class UserManager:
    """User management functionality."""

    def __init__(self):
        """Initialize user manager."""
        self.users = {}  # In-memory storage for demo
        self._next_id = 1

    def create_user(
        self,
        username: str,
        email: str,
        password_hash: str,
        role: UserRole = UserRole.USER,
    ) -> User:
        """Create new user.

        Args:
            username: Username
            email: Email address
            password_hash: Hashed password
            role: User role

        Returns:
            User: Created user

        Raises:
            ValueError: If username or email already exists
        """
        # Check for duplicates
        if self.get_user_by_username(username):
            raise ValueError(f"Username '{username}' already exists")

        if self.get_user_by_email(email):
            raise ValueError(f"Email '{email}' already exists")

        # Create user
        user = User(
            user_id=self._next_id,
            username=username,
            email=email,
            password_hash=password_hash,
            role=role,
        )

        self.users[user.user_id] = user
        self._next_id += 1

        return user

    def get_user_by_id(self, user_id: int) -> Optional[User]:
        """Get user by ID.

        Args:
            user_id: User ID

        Returns:
            User: User instance or None
        """
        return self.users.get(user_id)

    def get_user_by_username(self, username: str) -> Optional[User]:
        """Get user by username.

        Args:
            username: Username

        Returns:
            User: User instance or None
        """
        for user in self.users.values():
            if user.username == username:
                return user
        return None

    def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email.

        Args:
            email: Email address

        Returns:
            User: User instance or None
        """
        for user in self.users.values():
            if user.email == email:
                return user
        return None

    def get_users_by_role(self, role: UserRole) -> List[User]:
        """Get users by role.

        Args:
            role: User role

        Returns:
            List[User]: List of users with specified role
        """
        return [user for user in self.users.values() if user.role == role]

    def get_active_users(self) -> List[User]:
        """Get all active users.

        Returns:
            List[User]: List of active users
        """
        return [user for user in self.users.values() if user.is_active]

    def search_users(self, query: str) -> List[User]:
        """Search users by username, email, or profile name.

        Args:
            query: Search query

        Returns:
            List[User]: List of matching users
        """
        query = query.lower()
        results = []

        for user in self.users.values():
            if (
                query in user.username.lower()
                or query in user.email.lower()
                or query in user.profile.full_name.lower()
            ):
                results.append(user)

        return results

    def update_user(self, user_id: int, updates: Dict[str, Any]) -> bool:
        """Update user data.

        Args:
            user_id: User ID
            updates: Updates to apply

        Returns:
            bool: True if user was updated
        """
        user = self.get_user_by_id(user_id)
        if not user:
            return False

        for key, value in updates.items():
            if hasattr(user, key):
                setattr(user, key, value)

        user.updated_at = datetime.now()
        return True

    def delete_user(self, user_id: int) -> bool:
        """Delete user.

        Args:
            user_id: User ID to delete

        Returns:
            bool: True if user was deleted
        """
        if user_id in self.users:
            del self.users[user_id]
            return True
        return False

    def get_user_count(self) -> int:
        """Get total user count.

        Returns:
            int: Number of users
        """
        return len(self.users)

    def get_user_statistics(self) -> Dict[str, Any]:
        """Get user statistics.

        Returns:
            Dict: User statistics
        """
        total_users = len(self.users)
        active_users = len(self.get_active_users())
        admin_users = len(self.get_users_by_role(UserRole.ADMIN))

        return {
            "total_users": total_users,
            "active_users": active_users,
            "admin_users": admin_users,
            "inactive_users": total_users - active_users,
        }
