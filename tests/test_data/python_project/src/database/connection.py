"""Database connection and management utilities."""

import logging
import sqlite3
from contextlib import contextmanager
from typing import Any, Dict, List


class DatabaseError(Exception):
    """Base exception for database operations."""
    pass


class ConnectionError(DatabaseError):
    """Raised when database connection fails."""
    pass


class QueryError(DatabaseError):
    """Raised when SQL query fails."""
    pass


class DatabaseConnection:
    """Manages SQLite database connections."""
    
    def __init__(self, database_path: str):
        self.database_path = database_path
        self.connection = None
        self.logger = logging.getLogger(__name__)
    
    def connect(self) -> None:
        """Establish database connection."""
        try:
            self.connection = sqlite3.connect(self.database_path)
            self.connection.row_factory = sqlite3.Row
            self.logger.info(f"Connected to database: {self.database_path}")
        except sqlite3.Error as e:
            raise ConnectionError(f"Failed to connect to database: {e}")
    
    def disconnect(self) -> None:
        """Close database connection."""
        if self.connection:
            self.connection.close()
            self.connection = None
            self.logger.info("Database connection closed")
    
    @contextmanager
    def transaction(self):
        """Context manager for database transactions."""
        if not self.connection:
            raise ConnectionError("No active database connection")
        
        try:
            yield self.connection
            self.connection.commit()
        except Exception as e:
            self.connection.rollback()
            self.logger.error(f"Transaction rolled back: {e}")
            raise QueryError(f"Transaction failed: {e}")
    
    def execute_query(self, query: str, params: tuple = ()) -> List[Dict[str, Any]]:
        """Execute SQL query and return results."""
        if not self.connection:
            raise ConnectionError("No active database connection")
        
        try:
            cursor = self.connection.cursor()
            cursor.execute(query, params)
            
            if query.strip().upper().startswith('SELECT'):
                results = [dict(row) for row in cursor.fetchall()]
                self.logger.debug(f"Query returned {len(results)} rows")
                return results
            else:
                self.connection.commit()
                self.logger.debug(f"Query affected {cursor.rowcount} rows")
                return []
                
        except sqlite3.Error as e:
            self.logger.error(f"Query failed: {query} - Error: {e}")
            raise QueryError(f"SQL query failed: {e}")
    
    def execute_many(self, query: str, params_list: List[tuple]) -> None:
        """Execute query multiple times with different parameters."""
        if not self.connection:
            raise ConnectionError("No active database connection")
        
        try:
            cursor = self.connection.cursor()
            cursor.executemany(query, params_list)
            self.connection.commit()
            self.logger.debug(f"Batch query affected {cursor.rowcount} rows")
        except sqlite3.Error as e:
            raise QueryError(f"Batch query failed: {e}")


def create_connection_pool(database_path: str, pool_size: int = 5) -> List[DatabaseConnection]:
    """Create a pool of database connections."""
    pool = []
    for i in range(pool_size):
        conn = DatabaseConnection(database_path)
        try:
            conn.connect()
            pool.append(conn)
        except ConnectionError:
            logging.error(f"Failed to create connection {i} in pool")
    
    return pool


def migrate_database(connection: DatabaseConnection, migration_scripts: List[str]) -> None:
    """Run database migration scripts."""
    for script in migration_scripts:
        try:
            connection.execute_query(script)
            logging.info(f"Migration completed: {script[:50]}...")
        except QueryError as e:
            logging.error(f"Migration failed: {e}")
            raise