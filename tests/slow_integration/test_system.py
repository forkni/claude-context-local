#!/usr/bin/env python3
"""Test the core functionality without dependencies that might not be installed yet."""

import importlib
import os
import sys
import tempfile
from pathlib import Path

import pytest


def test_critical_imports():
    """Test importing all critical modules (merged from test_imports.py)."""
    modules_to_test = [
        "chunking.multi_language_chunker",
        "embeddings.embedder",
        "search.indexer",
        "search.searcher",
        "sentence_transformers",
        "faiss",
        "tree_sitter",
        "sqlitedict",
        "mcp",
        "rich",
        "click",
    ]

    results = []
    success_count = 0

    print(f"Testing Python {sys.version}")
    print("=" * 50)

    for module_name in modules_to_test:
        try:
            importlib.import_module(module_name)
            results.append(f"OK {module_name}")
            success_count += 1
        except Exception as e:
            results.append(f"FAIL {module_name}: {e}")

    print("\n".join(results))
    print("=" * 50)
    print(
        f"Success: {success_count}/{len(modules_to_test)} modules imported successfully"
    )

    assert success_count == len(modules_to_test), (
        f"Only {success_count}/{len(modules_to_test)} modules imported successfully: "
        f"{results}"
    )
    print("All dependencies installed correctly!")


@pytest.mark.slow
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

    # Verify the chunker actually found the real structure of the test file,
    # rather than merely completing without raising.
    assert len(chunks) > 0, "Chunker should produce at least one chunk"
    chunk_names = {chunk.name for chunk in chunks if chunk.name}
    assert "DatabaseManager" in chunk_names
    assert "authenticate_user" in chunk_names
    assert "get_user_profile" in chunk_names

    db_chunk = next(c for c in chunks if c.name == "DatabaseManager")
    assert db_chunk.chunk_type == "class"
    assert db_chunk.docstring and "database" in db_chunk.docstring.lower()

    method_names = {c.name for c in chunks if c.parent_name == "DatabaseManager"}
    assert {"__init__", "connect", "execute_query"} <= method_names

    profile_chunk = next(c for c in chunks if c.name == "get_user_profile")
    assert profile_chunk.decorators, "Decorated function should capture its decorator"
    assert any("login_required" in d for d in profile_chunk.decorators)


@pytest.mark.slow
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

    # Verify the extracted metadata actually reflects the nested project
    # structure and the source file's real content.
    assert len(chunks) > 0, "Chunker should produce at least one chunk"
    class_names = {c.name for c in chunks if c.chunk_type == "class"}
    assert "AuthenticationError" in class_names
    assert "UserAuthenticator" in class_names

    assert any(c.folder_structure == ["src", "auth"] for c in chunks), (
        "Chunks should record the nested src/auth folder structure"
    )

    authenticate_chunk = next(c for c in chunks if c.name == "authenticate")
    assert authenticate_chunk.parent_name == "UserAuthenticator"
    assert authenticate_chunk.complexity_score > 1, (
        "authenticate() has branching try/except/if-else and should score "
        "above the trivial-method baseline"
    )

    max_attempts_chunk = next(c for c in chunks if c.name == "max_attempts")
    assert max_attempts_chunk.parent_name == "UserAuthenticator"
    assert any("property" in d for d in max_attempts_chunk.decorators), (
        "max_attempts should retain its @property decorator"
    )


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
            "1. Wait for dependencies to finish installing (uv add sentence-transformers faiss-cpu mcp)"
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
