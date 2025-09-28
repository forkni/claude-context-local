"""Database connection and configuration module."""

import logging
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Dict, Optional


class DatabaseError(Exception):
    """Database operation error."""

    pass


class DatabaseConnection:
    """Manages database connections and operations."""

    def __init__(self, db_path: str = "app.db"):
        self.db_path = Path(db_path)
        self.logger = logging.getLogger(__name__)
        self._connection = None

    def initialize_database(self):
        """Initialize database schema."""
        try:
            with self.get_connection() as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS users (
                        id INTEGER PRIMARY KEY,
                        username TEXT UNIQUE NOT NULL,
                        email TEXT,
                        password_hash TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS sessions (
                        token TEXT PRIMARY KEY,
                        user_id INTEGER,
                        expires_at TIMESTAMP,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users (id)
                    )
                """)
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS user_profiles (
                        user_id INTEGER PRIMARY KEY,
                        first_name TEXT,
                        last_name TEXT,
                        bio TEXT,
                        avatar_url TEXT,
                        FOREIGN KEY (user_id) REFERENCES users (id)
                    )
                """)
                conn.commit()
                self.logger.info("Database initialized successfully")
        except sqlite3.Error as e:
            self.logger.error(f"Database initialization error: {e}")
            raise DatabaseError(f"Failed to initialize database: {e}")

    @contextmanager
    def get_connection(self):
        """Get database connection context manager."""
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            yield conn
        except sqlite3.Error as e:
            if conn:
                conn.rollback()
            self.logger.error(f"Database connection error: {e}")
            raise DatabaseError(f"Database operation failed: {e}")
        finally:
            if conn:
                conn.close()

    def execute_query(self, query: str, params: Optional[Dict] = None) -> list:
        """Execute database query and return results."""
        try:
            with self.get_connection() as conn:
                cursor = conn.execute(query, params or {})
                return cursor.fetchall()
        except sqlite3.Error as e:
            self.logger.error(f"Query execution error: {e}")
            raise DatabaseError(f"Query failed: {e}")

    def insert_user(self, username: str, email: str, password_hash: str) -> int:
        """Insert new user and return user ID."""
        try:
            with self.get_connection() as conn:
                cursor = conn.execute(
                    "INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)",
                    (username, email, password_hash),
                )
                conn.commit()
                return cursor.lastrowid
        except sqlite3.Error as e:
            self.logger.error(f"User insertion error: {e}")
            raise DatabaseError(f"Failed to insert user: {e}")

    def get_user_by_username(self, username: str) -> Optional[Dict]:
        """Get user by username."""
        result = self.execute_query(
            "SELECT * FROM users WHERE username = ?", (username,)
        )
        return dict(result[0]) if result else None

    def create_session(self, user_id: int, token: str, expires_at: str) -> bool:
        """Create user session."""
        try:
            with self.get_connection() as conn:
                conn.execute(
                    "INSERT INTO sessions (token, user_id, expires_at) VALUES (?, ?, ?)",
                    (token, user_id, expires_at),
                )
                conn.commit()
                return True
        except sqlite3.Error as e:
            self.logger.error(f"Session creation error: {e}")
            return False

    def cleanup_expired_sessions(self):
        """Remove expired sessions from database."""
        try:
            with self.get_connection() as conn:
                cursor = conn.execute(
                    "DELETE FROM sessions WHERE expires_at < datetime('now')"
                )
                conn.commit()
                self.logger.info(f"Cleaned up {cursor.rowcount} expired sessions")
        except sqlite3.Error as e:
            self.logger.error(f"Session cleanup error: {e}")
            raise DatabaseError(f"Failed to cleanup sessions: {e}")
