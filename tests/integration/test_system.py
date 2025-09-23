#!/usr/bin/env python3
"""Test the core functionality without dependencies that might not be installed yet."""

import os
import sys
import tempfile
from pathlib import Path

# Add the package to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


def test_chunking():
    """Test AST-based chunking."""
    print("Testing AST-based chunking...")

    from chunking.multi_language_chunker import MultiLanguageChunker

    # Create a more complex test Python file
    test_code = '''
import os
import json
from typing import Dict, List, Optional

# Configuration constants
API_VERSION = "v1"
DEFAULT_TIMEOUT = 30

class DatabaseManager:
    """Manages database connections and operations."""
    
    def __init__(self, connection_string: str):
        """Initialize database manager."""
        self.connection_string = connection_string
        self.connection = None
    
    def connect(self) -> bool:
        """Establish database connection."""
        try:
            # Connection logic here
            self.connection = create_connection(self.connection_string)
            return True
        except Exception as e:
            logger.error(f"Database connection failed: {e}")
            return False
    
    def execute_query(self, query: str, params: Dict = None) -> List[Dict]:
        """Execute SQL query with parameters."""
        if not self.connection:
            raise ConnectionError("Not connected to database")
        
        try:
            cursor = self.connection.cursor()
            cursor.execute(query, params or {})
            return cursor.fetchall()
        except Exception as e:
            logger.error(f"Query execution failed: {e}")
            raise

def authenticate_user(username: str, password: str) -> Optional[Dict]:
    """Authenticate user with username and password."""
    if not username or not password:
        raise ValueError("Username and password required")
    
    # Hash password for comparison
    password_hash = hash_password(password)
    
    # Database lookup
    db = DatabaseManager(DATABASE_URL)
    if not db.connect():
        raise ConnectionError("Database unavailable")
    
    query = "SELECT * FROM users WHERE username = ? AND password_hash = ?"
    results = db.execute_query(query, {"username": username, "password_hash": password_hash})
    
    if results:
        return results[0]
    return None

@login_required
def get_user_profile(user_id: int) -> Dict:
    """Get user profile data."""
    db = DatabaseManager(DATABASE_URL)
    db.connect()
    
    query = "SELECT * FROM user_profiles WHERE user_id = ?"
    profiles = db.execute_query(query, {"user_id": user_id})
    
    if not profiles:
        raise ValueError(f"Profile not found for user {user_id}")
    
    return profiles[0]
'''

    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(test_code)
        f.flush()

        # Test chunking
        chunker = MultiLanguageChunker(os.path.dirname(f.name))
        chunks = chunker.chunk_file(f.name)

        print(f"\n[OK] Generated {len(chunks)} chunks from test file:")

        for i, chunk in enumerate(chunks, 1):
            print(f"\n{i}. {chunk.chunk_type.upper()}: {chunk.name or 'unnamed'}")
            print(f"   [LOC] Lines: {chunk.start_line}-{chunk.end_line}")
            print(f"   [TAGS] Tags: {chunk.tags}")
            print(f"   [DOC] Docstring: {'[OK]' if chunk.docstring else '[NONE]'}")
            print(f"   [DEC] Decorators: {chunk.decorators}")
            if chunk.parent_name:
                print(f"   [PARENT] Parent: {chunk.parent_name}")

            # Show content preview
            content_preview = chunk.content.replace("\n", " ").strip()
            if len(content_preview) > 100:
                content_preview = content_preview[:100] + "..."
            print(f"   [PREVIEW] Preview: {content_preview}")

        print("\n[OK] Chunking test completed successfully!")

    os.unlink(f.name)
    return True


def test_metadata_richness():
    """Test the richness of metadata extraction."""
    print("\n" + "=" * 60)
    print("Testing metadata extraction richness...")

    from chunking.multi_language_chunker import MultiLanguageChunker

    # Create a test file in a nested directory structure
    test_dir = tempfile.mkdtemp()
    project_dir = Path(test_dir) / "test_project"
    src_dir = project_dir / "src" / "auth"
    src_dir.mkdir(parents=True)

    test_file = src_dir / "user_auth.py"
    test_code = '''
from typing import Optional
import hashlib
import logging

logger = logging.getLogger(__name__)

class AuthenticationError(Exception):
    """Custom authentication error."""
    pass

class UserAuthenticator:
    """Handles user authentication and authorization."""
    
    def __init__(self, secret_key: str):
        """Initialize authenticator with secret key."""
        self.secret_key = secret_key
        self.failed_attempts = {}
    
    @property
    def max_attempts(self) -> int:
        """Maximum login attempts allowed."""
        return 3
    
    def authenticate(self, username: str, password: str) -> bool:
        """Authenticate user credentials."""
        try:
            if self._is_account_locked(username):
                raise AuthenticationError("Account locked due to too many failed attempts")
            
            # Verify credentials
            if self._verify_password(username, password):
                self._reset_failed_attempts(username)
                logger.info(f"User {username} authenticated successfully")
                return True
            else:
                self._record_failed_attempt(username)
                return False
                
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            raise
'''

    test_file.write_text(test_code)

    # Test chunking with the nested structure
    chunker = MultiLanguageChunker(str(project_dir))
    chunks = chunker.chunk_file(str(test_file))

    print(f"\n[OK] Generated {len(chunks)} chunks from nested project structure:")
    print(f"   [DIR] Project root: {project_dir}")
    print(f"   [FILE] Test file: {test_file.relative_to(project_dir)}")

    for i, chunk in enumerate(chunks, 1):
        print(f"\n{i}. {chunk.chunk_type.upper()}: {chunk.name or 'unnamed'}")
        print(
            f"   [LOC] Location: {chunk.relative_path}:{chunk.start_line}-{chunk.end_line}"
        )
        print(
            f"   [DIR] Folders: {' -> '.join(chunk.folder_structure) if chunk.folder_structure else 'root'}"
        )
        print(f"   [TAGS] Tags: {chunk.tags}")
        print(f"   [IMPORTS] Imports: {len(chunk.imports)} import(s)")
        print(
            f"   [DOC] Docstring: {'[OK] ' + chunk.docstring[:50] + '...' if chunk.docstring else '[NONE]'}"
        )
        print(
            f"   [DEC] Decorators: {chunk.decorators if chunk.decorators else 'None'}"
        )
        print(f"   [COMPLEX] Complexity: {chunk.complexity_score}")

        if chunk.parent_name:
            print(f"   [PARENT] Parent class: {chunk.parent_name}")

    # Cleanup
    import shutil

    shutil.rmtree(test_dir)

    print("\n[OK] Metadata extraction test completed successfully!")
    return True


def main():
    """Run all tests."""
    print("[TEST] Testing Claude Code Embedding Search System")
    print("=" * 60)

    try:
        # Test basic chunking
        test_chunking()

        # Test metadata richness
        test_metadata_richness()

        print("\n" + "=" * 60)
        print("[SUCCESS] ALL TESTS PASSED!")
        print("=" * 60)
        print("\n[INFO] Next steps:")
        print(
            "1. Wait for dependencies to finish installing (uv add sentence-transformers faiss-cpu mcp fastmcp)"
        )
        print(
            "2. Index your first codebase: ./scripts/index_codebase.py /path/to/python/project"
        )
        print(
            "3. Add MCP server to Claude Code: claude mcp add code-search -- python mcp_server/server.py"
        )
        print("4. Start using semantic search in Claude Code!")

        return True

    except Exception as e:
        print(f"\n[ERROR] Test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
