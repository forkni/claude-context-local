"""Unit tests for ``mcp_server/guidance.py`` (Phase 13.3).

One import (``typing.Any``), four pure functions, zero collaborators, zero
I/O -- previously untested at the unit level (only exercised indirectly
through handler-level assertions in ``test_search_orchestrator.py`` and
``test_find_path_handler.py``, neither of which pins the branch boundaries
inside ``generate_search_message``/``generate_impact_message`` directly).
``TESTING_GUIDE.md:2063-2065`` had lumped this module in with four others as
needing "async/process-boundary mocking to test properly" -- wrong for this
file specifically, which is a textbook ``@pytest.mark.parametrize`` target.
"""

import pytest

from mcp_server.guidance import (
    add_system_message,
    generate_impact_message,
    generate_index_message,
    generate_search_message,
)


class TestGenerateSearchMessage:
    def test_chunk_id_lookup_found(self):
        msg = generate_search_message([{"chunk_id": "a"}], chunk_id="a")
        assert msg == "Direct lookup successful. Use related chunk_ids for navigation."

    def test_chunk_id_lookup_not_found(self):
        msg = generate_search_message([], chunk_id="missing")
        assert msg == "Chunk 'missing' not found in index."

    def test_zero_results(self):
        msg = generate_search_message([])
        assert "No" in msg or "no" in msg  # _NO_RESULTS_MSG

    def test_one_result_without_graph(self):
        msg = generate_search_message([{"chunk_id": "x1"}])
        assert "Found 1 result." in msg
        assert "chunk_id='x1'" in msg
        assert "graph" not in msg.lower()

    def test_one_result_with_graph(self):
        msg = generate_search_message([{"chunk_id": "x1", "graph": {"callers": []}}])
        assert "Found 1 result." in msg
        assert "chunk_id='x1'" in msg
        # the graph hint text is appended when graph data is truthy
        assert len(msg) > len("Found 1 result. Use chunk_id='x1' for direct access.")

    def test_one_result_with_empty_graph_dict_no_hint(self):
        # "graph" in result and result["graph"] -- an empty dict is falsy,
        # so the graph hint must NOT be appended
        msg = generate_search_message([{"chunk_id": "x1", "graph": {}}])
        assert msg == "Found 1 result. Use chunk_id='x1' for direct access."

    @pytest.mark.parametrize("count", [2, 5])
    def test_few_results_no_graph(self, count):
        results = [{"chunk_id": f"c{i}"} for i in range(count)]
        msg = generate_search_message(results)
        assert f"Found {count} results." in msg
        assert "Use chunk_id from results for precise follow-up." in msg

    def test_few_results_with_graph(self):
        results = [{"chunk_id": "c0", "graph": {"x": 1}}, {"chunk_id": "c1"}]
        msg = generate_search_message(results)
        assert "Found 2 results." in msg

    def test_many_results_over_five(self):
        results = [{"chunk_id": f"c{i}"} for i in range(6)]
        msg = generate_search_message(results)
        assert "Found 6 results." in msg
        assert "chunk_id='c0'" in msg
        assert "find_similar_code" in msg


class TestGenerateIndexMessage:
    def test_error_result(self):
        msg = generate_index_message({"error": "boom"})
        assert "Indexing failed" in msg

    def test_incremental_mode(self):
        msg = generate_index_message(
            {
                "mode": "incremental",
                "total_files_added": 3,
                "total_chunks_added": 12,
                "files_modified": 2,
            }
        )
        assert "Incremental index updated: +3 files, +12 chunks." in msg
        assert "Modified 2 files detected." in msg

    def test_full_index_uses_total_keys(self):
        msg = generate_index_message(
            {"total_chunks_added": 100, "total_files_added": 10}
        )
        assert "Indexed 100 chunks from 10 files." in msg

    def test_full_index_falls_back_to_legacy_keys(self):
        msg = generate_index_message({"chunks_indexed": 50, "files_indexed": 5})
        assert "Indexed 50 chunks from 5 files." in msg

    def test_full_index_missing_all_keys_defaults_to_zero(self):
        msg = generate_index_message({})
        assert "Indexed 0 chunks from 0 files." in msg


class TestGenerateImpactMessage:
    def test_zero_impacted(self):
        msg = generate_impact_message(0)
        assert (
            msg
            == "No connections found. This appears to be unused or entry-point code."
        )

    def test_one_impacted(self):
        msg = generate_impact_message(1)
        assert msg == "Minimal connections: 1 link found. Isolated code."

    @pytest.mark.parametrize("total", [2, 10])
    def test_moderate_impact(self, total):
        msg = generate_impact_message(total)
        assert f"Found {total} connected symbols." in msg

    def test_high_impact_with_file_count(self):
        msg = generate_impact_message(11, file_count=4)
        assert "High connectivity: 11 symbols connected across 4 files." in msg

    def test_high_impact_without_file_count_uses_placeholder(self):
        msg = generate_impact_message(20, file_count=None)
        assert "across ? files" in msg


class TestAddSystemMessage:
    def test_search_code_populates_message(self):
        response = {"results": [{"chunk_id": "a"}]}
        out = add_system_message(response, "search_code", query="q")
        assert "system_message" in out
        assert out is response  # mutates and returns the same dict

    def test_index_directory_populates_message(self):
        response = {"total_chunks_added": 1, "total_files_added": 1}
        out = add_system_message(response, "index_directory")
        assert "Indexed 1 chunks from 1 files." in out["system_message"]

    def test_find_connections_populates_message(self):
        response = {"total_impacted": 0}
        out = add_system_message(response, "find_connections")
        assert out["system_message"] == (
            "No connections found. This appears to be unused or entry-point code."
        )

    def test_unknown_tool_name_leaves_response_unchanged(self):
        response = {"foo": "bar"}
        out = add_system_message(response, "some_other_tool")
        assert "system_message" not in out
        assert out == {"foo": "bar"}
