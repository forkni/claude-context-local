"""Unit tests for ApplicationState's global mutation lock (P3-A Phase 1).

Covers mcp_server.state.ApplicationState.get_mutation_lock() in isolation —
the with_mutation_lock decorator that consumes it is exercised separately in
test_decorators.py.
"""

import asyncio

from mcp_server.state import ApplicationState


class TestMutationLock:
    def test_returns_asyncio_lock(self):
        state = ApplicationState()
        assert isinstance(state.get_mutation_lock(), asyncio.Lock)

    def test_returns_same_instance_across_calls(self):
        state = ApplicationState()
        lock1 = state.get_mutation_lock()
        lock2 = state.get_mutation_lock()
        assert lock1 is lock2

    def test_distinct_instances_have_independent_locks(self):
        a = ApplicationState()
        b = ApplicationState()
        assert a.get_mutation_lock() is not b.get_mutation_lock()

    def test_reset_replaces_the_lock(self):
        state = ApplicationState()
        original = state.get_mutation_lock()

        state.reset()

        assert state.get_mutation_lock() is not original

    async def test_lock_is_actually_lockable(self):
        state = ApplicationState()
        lock = state.get_mutation_lock()

        async with lock:
            assert lock.locked()
        assert not lock.locked()
