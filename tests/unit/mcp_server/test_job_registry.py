"""Unit tests for the background-job registry (P2-A: async index job + poll).

Covers the JobRegistry lifecycle in isolation (running -> done, running ->
error, unknown job_id) — the index_directory(wait=False) wiring is exercised
separately in test_index_handlers.py / test_tool_handlers.py.
"""

import asyncio

from mcp_server.tools.job_registry import JobRegistry, get_job_registry


class TestJobLifecycle:
    async def test_create_returns_running_job(self):
        registry = JobRegistry()
        job = await registry.create(kind="index_directory", target="/some/project")

        assert job.status == "running"
        assert job.kind == "index_directory"
        assert job.target == "/some/project"
        assert job.job_id  # non-empty

    async def test_mark_done_transitions_status_and_stores_result(self):
        registry = JobRegistry()
        job = await registry.create(kind="index_directory", target="/proj")

        await registry.mark_done(job.job_id, {"success": True, "files_added": 3})

        fetched = await registry.get(job.job_id)
        assert fetched is not None
        assert fetched.status == "done"
        assert fetched.result == {"success": True, "files_added": 3}
        assert fetched.finished_at is not None

    async def test_mark_error_transitions_status_and_stores_message(self):
        registry = JobRegistry()
        job = await registry.create(kind="index_directory", target="/proj")

        await registry.mark_error(job.job_id, "boom")

        fetched = await registry.get(job.job_id)
        assert fetched is not None
        assert fetched.status == "error"
        assert fetched.error == "boom"

    async def test_get_unknown_job_id_returns_none(self):
        registry = JobRegistry()
        assert await registry.get("does-not-exist") is None

    async def test_latest_for_target_picks_most_recent(self):
        registry = JobRegistry()
        older = await registry.create(kind="index_directory", target="/proj")
        await registry.mark_done(older.job_id, {})
        newer = await registry.create(kind="index_directory", target="/proj")

        latest = await registry.latest_for_target("/proj")
        assert latest is not None
        assert latest.job_id == newer.job_id

    async def test_latest_for_target_no_jobs_returns_none(self):
        registry = JobRegistry()
        assert await registry.latest_for_target("/never-indexed") is None


class TestJobToStatusDict:
    async def test_running_job_has_no_result_or_error_key(self):
        registry = JobRegistry()
        job = await registry.create(kind="index_directory", target="/proj")

        d = job.to_status_dict()

        assert d["status"] == "running"
        assert d["job_id"] == job.job_id
        assert "result" not in d
        assert "error" not in d
        assert "elapsed_seconds" in d

    async def test_done_job_includes_result(self):
        registry = JobRegistry()
        job = await registry.create(kind="index_directory", target="/proj")
        await registry.mark_done(job.job_id, {"chunks_added": 10})

        d = (await registry.get(job.job_id)).to_status_dict()

        assert d["status"] == "done"
        assert d["result"] == {"chunks_added": 10}

    async def test_error_job_includes_error(self):
        registry = JobRegistry()
        job = await registry.create(kind="index_directory", target="/proj")
        await registry.mark_error(job.job_id, "disk full")

        d = (await registry.get(job.job_id)).to_status_dict()

        assert d["status"] == "error"
        assert d["error"] == "disk full"


class TestTrackBackgroundTask:
    async def test_task_reference_is_dropped_after_completion(self):
        registry = JobRegistry()

        async def _noop():
            return None

        task = asyncio.create_task(_noop())
        registry.track_background_task(task)
        assert task in registry._background_tasks

        await task
        # add_done_callback runs on the next loop iteration; yield once.
        await asyncio.sleep(0)

        assert task not in registry._background_tasks


class TestGetJobRegistrySingleton:
    def test_returns_same_instance(self):
        assert get_job_registry() is get_job_registry()
