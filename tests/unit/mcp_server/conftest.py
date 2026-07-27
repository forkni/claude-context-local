"""Shared fixtures for mcp_server unit tests.

Phase 8 (test-suite hardening): the _no_real_storage_pollution guard that used
to live here (autouse, mcp_server-only) has been promoted to tests/conftest.py
and now applies to every test, not just this directory — see that file for the
current implementation and the CODE_SEARCH_STORAGE redirect it pairs with.
"""
