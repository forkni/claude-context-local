"""Sample code fixtures for testing."""

# Sample authentication module
SAMPLE_AUTH_MODULE = '''
import hashlib
import logging
from typing import Optional, Dict, List
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# Configuration constants
MAX_LOGIN_ATTEMPTS = 3
LOCKOUT_DURATION = 300  # 5 minutes

class AuthenticationError(Exception):
    """Custom authentication error."""

    def __init__(self, message: str, error_code: int = None):
        """Initialize authentication error."""
        super().__init__(message)
        self.error_code = error_code
        self.timestamp = datetime.now()

class RateLimiter:
    """Rate limiting for authentication attempts."""

    def __init__(self, max_attempts: int = MAX_LOGIN_ATTEMPTS):
        """Initialize rate limiter."""
        self.max_attempts = max_attempts
        self.attempts = {}
        self.lockouts = {}

    def is_locked(self, identifier: str) -> bool:
        """Check if identifier is currently locked out."""
        if identifier not in self.lockouts:
            return False

        lockout_time = self.lockouts[identifier]
        if datetime.now() - lockout_time > timedelta(seconds=LOCKOUT_DURATION):
            del self.lockouts[identifier]
            return False

        return True

    def record_attempt(self, identifier: str, success: bool = False):
        """Record an authentication attempt."""
        if success:
            # Reset on successful login
            if identifier in self.attempts:
                del self.attempts[identifier]
            return

        # Increment failed attempts
        self.attempts[identifier] = self.attempts.get(identifier, 0) + 1

        if self.attempts[identifier] >= self.max_attempts:
            self.lockouts[identifier] = datetime.now()
            logger.warning(f"Account locked due to too many failed attempts: {identifier}")

def hash_password(password: str, salt: str = None) -> str:
    """Hash password with salt using SHA-256."""
    if not salt:
        salt = "default_salt"

    combined = f"{password}{salt}"
    return hashlib.sha256(combined.encode()).hexdigest()

def verify_password(password: str, hashed: str, salt: str = None) -> bool:
    """Verify password against hash."""
    return hash_password(password, salt) == hashed

class UserAuthenticator:
    """Main authentication class."""

    def __init__(self, database_manager, rate_limiter: RateLimiter = None):
        """Initialize authenticator."""
        self.db = database_manager
        self.rate_limiter = rate_limiter or RateLimiter()
        self.active_sessions = {}

    async def authenticate(self, username: str, password: str) -> Optional[Dict]:
        """Authenticate user with username and password."""
        try:
            # Check rate limiting
            if self.rate_limiter.is_locked(username):
                raise AuthenticationError("Account temporarily locked", 429)

            if not username or not password:
                self.rate_limiter.record_attempt(username, False)
                raise AuthenticationError("Username and password required", 400)

            # Get user from database
            user = await self.db.get_user_by_username(username)
            if not user:
                self.rate_limiter.record_attempt(username, False)
                raise AuthenticationError("Invalid credentials", 401)

            # Verify password
            if not verify_password(password, user['password_hash'], user['salt']):
                self.rate_limiter.record_attempt(username, False)
                raise AuthenticationError("Invalid credentials", 401)

            # Check if user is active
            if not user.get('is_active', False):
                raise AuthenticationError("Account disabled", 403)

            # Success - record and return user info
            self.rate_limiter.record_attempt(username, True)
            logger.info(f"User authenticated successfully: {username}")

            return {
                'user_id': user['id'],
                'username': user['username'],
                'email': user['email'],
                'roles': user.get('roles', []),
                'last_login': datetime.now().isoformat()
            }

        except AuthenticationError:
            raise
        except Exception as e:
            logger.error(f"Authentication failed for {username}: {e}")
            raise AuthenticationError("Authentication system error", 500)

    @property
    def session_count(self) -> int:
        """Get number of active sessions."""
        return len(self.active_sessions)

    def create_session(self, user_info: Dict) -> str:
        """Create a new session for authenticated user."""
        import uuid
        session_id = str(uuid.uuid4())

        self.active_sessions[session_id] = {
            'user_info': user_info,
            'created_at': datetime.now(),
            'last_accessed': datetime.now()
        }

        return session_id

    def validate_session(self, session_id: str) -> Optional[Dict]:
        """Validate and refresh a session."""
        if session_id not in self.active_sessions:
            return None

        session = self.active_sessions[session_id]
        session['last_accessed'] = datetime.now()

        return session['user_info']

    def logout(self, session_id: str) -> bool:
        """Logout and invalidate session."""
        if session_id in self.active_sessions:
            user_info = self.active_sessions[session_id]['user_info']
            del self.active_sessions[session_id]
            logger.info(f"User logged out: {user_info['username']}")
            return True

        return False
'''

# Sample database module
SAMPLE_DATABASE_MODULE = '''
import sqlite3
import asyncio
import logging
from typing import Dict, List, Optional, Any
from contextlib import asynccontextmanager
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class DatabaseConfig:
    """Database configuration."""
    host: str = "localhost"
    port: int = 5432
    database: str = "app_db"
    username: str = "app_user"
    password: str = "secret"
    pool_size: int = 10
    timeout: int = 30

class DatabaseError(Exception):
    """Database operation error."""
    pass

class ConnectionPool:
    """Database connection pool."""

    def __init__(self, config: DatabaseConfig):
        """Initialize connection pool."""
        self.config = config
        self.pool = None
        self._initialized = False

    async def initialize(self):
        """Initialize the connection pool."""
        if self._initialized:
            return

        try:
            # In real implementation, would create actual connection pool
            self.pool = f"pool_{self.config.database}"
            self._initialized = True
            logger.info("Database connection pool initialized")
        except Exception as e:
            logger.error(f"Failed to initialize connection pool: {e}")
            raise DatabaseError(f"Pool initialization failed: {e}")

    async def close(self):
        """Close all connections in the pool."""
        if self.pool:
            # In real implementation, would close all connections
            logger.info("Connection pool closed")
            self.pool = None
            self._initialized = False

    @asynccontextmanager
    async def get_connection(self):
        """Get a connection from the pool."""
        if not self._initialized:
            await self.initialize()

        try:
            # Mock connection
            connection = f"conn_{id(self)}"
            logger.debug(f"Retrieved connection: {connection}")
            yield connection
        finally:
            logger.debug("Connection returned to pool")

class QueryBuilder:
    """SQL query builder."""

    def __init__(self):
        """Initialize query builder."""
        self.reset()

    def reset(self):
        """Reset builder state."""
        self._select = []
        self._from = None
        self._where = []
        self._joins = []
        self._order = []
        self._limit = None
        self._params = {}

    def select(self, *columns):
        """Add SELECT columns."""
        self._select.extend(columns)
        return self

    def from_table(self, table):
        """Set FROM table."""
        self._from = table
        return self

    def where(self, condition, **params):
        """Add WHERE condition."""
        self._where.append(condition)
        self._params.update(params)
        return self

    def join(self, table, on_condition):
        """Add JOIN clause."""
        self._joins.append(f"JOIN {table} ON {on_condition}")
        return self

    def order_by(self, column, direction="ASC"):
        """Add ORDER BY clause."""
        self._order.append(f"{column} {direction}")
        return self

    def limit(self, count, offset=0):
        """Add LIMIT clause."""
        self._limit = f"LIMIT {count}"
        if offset > 0:
            self._limit += f" OFFSET {offset}"
        return self

    def build(self) -> tuple[str, Dict[str, Any]]:
        """Build the final query."""
        if not self._select or not self._from:
            raise ValueError("SELECT and FROM are required")

        query_parts = [
            f"SELECT {', '.join(self._select)}",
            f"FROM {self._from}"
        ]

        if self._joins:
            query_parts.extend(self._joins)

        if self._where:
            query_parts.append(f"WHERE {' AND '.join(self._where)}")

        if self._order:
            query_parts.append(f"ORDER BY {', '.join(self._order)}")

        if self._limit:
            query_parts.append(self._limit)

        query = " ".join(query_parts)
        return query, self._params

class DatabaseManager:
    """Main database manager."""

    def __init__(self, config: DatabaseConfig = None):
        """Initialize database manager."""
        self.config = config or DatabaseConfig()
        self.pool = ConnectionPool(self.config)
        self.query_builder = QueryBuilder()

    async def execute_query(
        self,
        query: str,
        params: Dict[str, Any] = None
    ) -> List[Dict[str, Any]]:
        """Execute a SELECT query."""
        async with self.pool.get_connection() as conn:
            try:
                # Mock query execution
                logger.debug(f"Executing query: {query}")
                logger.debug(f"Parameters: {params}")

                # Simulate query results
                if "users" in query.lower():
                    return [
                        {
                            'id': 1,
                            'username': 'testuser',
                            'email': 'test@example.com',
                            'password_hash': 'hashed_password',
                            'salt': 'random_salt',
                            'is_active': True,
                            'roles': ['user']
                        }
                    ]

                return []

            except Exception as e:
                logger.error(f"Query execution failed: {e}")
                raise DatabaseError(f"Query failed: {e}")

    async def execute_command(
        self,
        command: str,
        params: Dict[str, Any] = None
    ) -> int:
        """Execute an INSERT/UPDATE/DELETE command."""
        async with self.pool.get_connection() as conn:
            try:
                logger.debug(f"Executing command: {command}")
                logger.debug(f"Parameters: {params}")

                # Mock affected rows
                return 1

            except Exception as e:
                logger.error(f"Command execution failed: {e}")
                raise DatabaseError(f"Command failed: {e}")

    async def get_user_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        """Get user by username."""
        query, params = (self.query_builder
                        .reset()
                        .select("*")
                        .from_table("users")
                        .where("username = :username", username=username)
                        .build())

        results = await self.execute_query(query, params)
        return results[0] if results else None

    async def create_user(self, user_data: Dict[str, Any]) -> int:
        """Create a new user."""
        command = """
        INSERT INTO users (username, email, password_hash, salt, is_active)
        VALUES (:username, :email, :password_hash, :salt, :is_active)
        """

        return await self.execute_command(command, user_data)

    async def close(self):
        """Close database connections."""
        await self.pool.close()
'''

# Sample API module
SAMPLE_API_MODULE = '''
from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr
from typing import Optional, Dict, List
import logging

logger = logging.getLogger(__name__)

# Pydantic models
class UserLogin(BaseModel):
    """User login request."""
    username: str
    password: str

class UserResponse(BaseModel):
    """User response model."""
    user_id: int
    username: str
    email: EmailStr
    roles: List[str] = []

class ErrorResponse(BaseModel):
    """Error response model."""
    error: str
    message: str
    status_code: int

# Security
security = HTTPBearer()

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict:
    """Get current authenticated user."""
    # Mock authentication - in real app would validate JWT token
    token = credentials.credentials

    if not token or token == "invalid":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )

    # Mock user data
    return {
        'user_id': 1,
        'username': 'testuser',
        'email': 'test@example.com',
        'roles': ['user']
    }

# FastAPI app
app = FastAPI(
    title="Authentication API",
    description="User authentication and management API",
    version="1.0.0"
)

class AuthAPI:
    """Authentication API endpoints."""

    def __init__(self, authenticator, database_manager):
        """Initialize API with dependencies."""
        self.auth = authenticator
        self.db = database_manager
        self.setup_routes()

    def setup_routes(self):
        """Setup API routes."""

        @app.post("/auth/login", response_model=UserResponse)
        async def login(user_login: UserLogin):
            """User login endpoint."""
            try:
                user_info = await self.auth.authenticate(
                    user_login.username,
                    user_login.password
                )

                if not user_info:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Invalid credentials"
                    )

                # Create session
                session_id = self.auth.create_session(user_info)

                # Return user info (in real app would return JWT token)
                return UserResponse(
                    user_id=user_info['user_id'],
                    username=user_info['username'],
                    email=user_info['email'],
                    roles=user_info['roles']
                )

            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Login failed: {e}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Authentication system error"
                )

        @app.post("/auth/logout")
        async def logout(current_user: Dict = Depends(get_current_user)):
            """User logout endpoint."""
            try:
                # In real app, would get session_id from token
                session_id = "mock_session"
                success = self.auth.logout(session_id)

                return {"message": "Logged out successfully", "success": success}

            except Exception as e:
                logger.error(f"Logout failed: {e}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Logout failed"
                )

        @app.get("/auth/profile", response_model=UserResponse)
        async def get_profile(current_user: Dict = Depends(get_current_user)):
            """Get current user profile."""
            return UserResponse(
                user_id=current_user['user_id'],
                username=current_user['username'],
                email=current_user['email'],
                roles=current_user['roles']
            )

        @app.get("/auth/sessions")
        async def get_sessions(current_user: Dict = Depends(get_current_user)):
            """Get active session count (admin only)."""
            if 'admin' not in current_user.get('roles', []):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Admin access required"
                )

            return {
                "active_sessions": self.auth.session_count,
                "total_users": await self._get_user_count()
            }

        async def _get_user_count(self) -> int:
            """Get total user count from database."""
            try:
                query = "SELECT COUNT(*) as count FROM users WHERE is_active = true"
                result = await self.db.execute_query(query)
                return result[0]['count'] if result else 0
            except Exception as e:
                logger.error(f"Failed to get user count: {e}")
                return 0

# Exception handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Handle HTTP exceptions."""
    return ErrorResponse(
        error=exc.detail,
        message=f"HTTP {exc.status_code}: {exc.detail}",
        status_code=exc.status_code
    )
'''

# Simple utility module
SAMPLE_UTILS_MODULE = r'''
import re
import hashlib
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone

def validate_email(email: str) -> bool:
    """Validate email format."""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def sanitize_input(text: str) -> str:
    """Sanitize user input."""
    if not text:
        return ""

    # Remove dangerous characters
    dangerous_chars = ['<', '>', '"', "'", '&', '\x00']
    for char in dangerous_chars:
        text = text.replace(char, '')

    return text.strip()

def format_datetime(dt: datetime) -> str:
    """Format datetime for API responses."""
    return dt.replace(tzinfo=timezone.utc).isoformat()

class ConfigManager:
    """Simple configuration manager."""

    _config = {
        'debug': False,
        'max_login_attempts': 3,
        'session_timeout': 3600,
        'log_level': 'INFO'
    }

    @classmethod
    def get(cls, key: str, default: Any = None) -> Any:
        """Get configuration value."""
        return cls._config.get(key, default)

    @classmethod
    def set(cls, key: str, value: Any) -> None:
        """Set configuration value."""
        cls._config[key] = value

    @classmethod
    def get_all(cls) -> Dict[str, Any]:
        """Get all configuration."""
        return cls._config.copy()
'''
