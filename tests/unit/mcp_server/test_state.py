"""Unit tests for ApplicationState's global mutation lock (P3-A Phase 1) and
the per-project reindex reader-writer lock (Part 2b, docs/adr/0008).

Covers mcp_server.state.ApplicationState.get_mutation_lock() in isolation —
the with_mutation_lock decorator that consumes it is exercised separately in
test_decorators.py.
"""

import asyncio

from mcp_server.state import ApplicationState, _AsyncRWLock


# Generous but still-fast margin for the "did the other task get a chance to
# run" checks below. asyncio is single-threaded/cooperative, so these sleeps
# aren't racing real parallelism — they just yield enough ticks for pending
# tasks to reach their next await point deterministically.
_TICK = 0.02


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


class TestAsyncRWLock:
    """Direct tests of _AsyncRWLock's reader/writer semantics.

    Verifies the three guarantees from the plan's Verification section:
    multiple readers run concurrently, a writer waits for readers to drain,
    and writer-preference means a new reader queues behind a waiting writer.
    """

    async def test_multiple_readers_run_concurrently(self):
        lock = _AsyncRWLock()
        entered: list[str] = []
        release = asyncio.Event()

        async def reader(name: str) -> None:
            async with lock.read():
                entered.append(name)
                await release.wait()

        t1 = asyncio.create_task(reader("a"))
        t2 = asyncio.create_task(reader("b"))
        await asyncio.sleep(_TICK)

        # Both readers hold the lock at once — neither blocked the other.
        assert set(entered) == {"a", "b"}

        release.set()
        await asyncio.wait_for(asyncio.gather(t1, t2), timeout=1)

    async def test_writer_blocks_until_readers_drain(self):
        lock = _AsyncRWLock()
        reader_release = asyncio.Event()
        events: list[str] = []

        async def reader() -> None:
            async with lock.read():
                events.append("reader_in")
                await reader_release.wait()
            events.append("reader_out")

        async def writer() -> None:
            async with lock.write():
                events.append("writer_in")

        r = asyncio.create_task(reader())
        await asyncio.sleep(_TICK)  # reader is inside the critical section
        w = asyncio.create_task(writer())
        await asyncio.sleep(_TICK)

        # Writer must still be waiting — the reader hasn't released yet.
        assert "writer_in" not in events

        reader_release.set()
        await asyncio.wait_for(asyncio.gather(r, w), timeout=1)

        assert events.index("reader_out") < events.index("writer_in")

    async def test_writer_preference_blocks_new_readers(self):
        lock = _AsyncRWLock()
        first_reader_release = asyncio.Event()
        events: list[str] = []

        async def first_reader() -> None:
            async with lock.read():
                events.append("r1_in")
                await first_reader_release.wait()
            events.append("r1_out")

        async def writer() -> None:
            async with lock.write():
                events.append("writer_in")
            events.append("writer_out")

        async def second_reader() -> None:
            async with lock.read():
                events.append("r2_in")

        r1 = asyncio.create_task(first_reader())
        await asyncio.sleep(_TICK)  # r1 is inside the critical section
        w = asyncio.create_task(writer())
        await asyncio.sleep(_TICK)  # writer is now waiting (writers_waiting == 1)
        r2 = asyncio.create_task(second_reader())
        await asyncio.sleep(_TICK)

        # A brand-new reader must queue behind the waiting writer, not jump ahead.
        assert "r2_in" not in events

        first_reader_release.set()
        await asyncio.wait_for(asyncio.gather(r1, w, r2), timeout=1)

        assert events.index("writer_in") < events.index("r2_in")

    async def test_write_is_exclusive_against_write(self):
        lock = _AsyncRWLock()
        active = 0
        max_active = 0
        events: list[str] = []

        async def writer(name: str) -> None:
            nonlocal active, max_active
            async with lock.write():
                active += 1
                max_active = max(max_active, active)
                events.append(f"{name}_in")
                await asyncio.sleep(_TICK)
                active -= 1
                events.append(f"{name}_out")

        await asyncio.wait_for(asyncio.gather(writer("a"), writer("b")), timeout=1)

        assert max_active == 1
        # One writer must fully finish (in, then out) before the other starts.
        assert events in (
            ["a_in", "a_out", "b_in", "b_out"],
            ["b_in", "b_out", "a_in", "a_out"],
        )


class TestGetReindexRwlock:
    """ApplicationState.get_reindex_rwlock() — per-project lazy _AsyncRWLock."""

    async def test_returns_async_rwlock(self):
        state = ApplicationState()
        assert isinstance(state.get_reindex_rwlock("/proj"), _AsyncRWLock)

    async def test_same_project_returns_same_instance(self):
        state = ApplicationState()
        lock1 = state.get_reindex_rwlock("/proj")
        lock2 = state.get_reindex_rwlock("/proj")
        assert lock1 is lock2

    async def test_different_projects_get_independent_locks(self):
        state = ApplicationState()
        lock_a = state.get_reindex_rwlock("/proj-a")
        lock_b = state.get_reindex_rwlock("/proj-b")
        assert lock_a is not lock_b

    async def test_reset_replaces_all_project_locks(self):
        state = ApplicationState()
        original = state.get_reindex_rwlock("/proj")

        state.reset()

        assert state.get_reindex_rwlock("/proj") is not original
