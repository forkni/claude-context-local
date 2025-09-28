"""User management and authentication module."""


class User:
    """User class for managing user data and authentication."""

    def __init__(self, username, email):
        self.username = username
        self.email = email
        self.is_authenticated = False

    def login(self, password):
        """Authenticate user with password."""
        # Simple authentication logic
        if password == "secure_password":
            self.is_authenticated = True
            return True
        return False

    def logout(self):
        """Log out the user."""
        self.is_authenticated = False

    def is_active(self):
        """Check if user is active."""
        return self.is_authenticated


class AuthManager:
    """Authentication manager for handling user sessions."""

    def __init__(self):
        self.users = {}
        self.active_sessions = set()

    def register_user(self, username, email):
        """Register a new user."""
        user = User(username, email)
        self.users[username] = user
        return user

    def authenticate(self, username, password):
        """Authenticate user and create session."""
        if username in self.users:
            user = self.users[username]
            if user.login(password):
                self.active_sessions.add(username)
                return user
        return None
