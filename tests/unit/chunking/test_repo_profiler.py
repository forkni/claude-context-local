"""Unit tests for chunking.repo_profiler — the full-index profiling pass that
drives adaptive chunk sizing (sizing_mode == "adaptive").

Written test-first ahead of the ParsedSource seam extraction (issue #15 /
architecture review: repo_profiler and the chunker each independently
tree-sitter-parse every file). Tests exercise profile_repository() through
its PUBLIC interface only (project_path, supported_files) so they keep
passing unchanged once the internal _scan_tree traversal is renamed to
profile_parsed() and routed through TreeSitterChunker.parse_file().

The reference computation below (_reference_function_stats) independently
parses each fixture with a plain PythonChunker — not via repo_profiler's
internals — so it stays a valid oracle across that refactor.
"""

import logging
import re
from pathlib import Path

import pytest

from chunking.languages.base import estimate_characters
from chunking.languages.python import PythonChunker
from chunking.repo_profiler import (
    MIN_FUNCTIONS_FOR_PROFILE,
    RepoProfile,
    profile_parsed,
    profile_repository,
)


def _reference_function_stats(content: str) -> tuple[list[int], list[int]]:
    """Independently compute expected (sizes, complexities) for top-level
    functions in `content`, without going through repo_profiler at all."""
    chunker = PythonChunker()
    source_bytes = content.encode("utf-8")
    tree = chunker.parser.parse(source_bytes)

    sizes: list[int] = []
    complexities: list[int] = []
    for node in tree.root_node.children:
        if node.type != "function_definition":
            continue
        text = source_bytes[node.start_byte : node.end_byte].decode("utf-8")
        sizes.append(estimate_characters(text, count_whitespace=False))
        cc = chunker.get_node_complexity(node)
        if cc > 1:
            complexities.append(cc)
    return sizes, complexities


def _make_source(bodies: list[str]) -> str:
    """Build a valid Python module with one top-level function per body."""
    parts = [f"def func_{i}():\n{body}\n" for i, body in enumerate(bodies)]
    return "\n".join(parts)


def _write(tmp_path: Path, filename: str, content: str) -> str:
    """Write `content` under tmp_path; return the path relative to tmp_path,
    matching profile_repository's `supported_files` contract."""
    (tmp_path / filename).write_text(content, encoding="utf-8")
    return filename


# A mix of straight-line and branching bodies so sizes are non-uniform and
# max_complexity is meaningfully > 1.
_MIXED_BODIES = [
    "    return 0",
    "    x = 1\n    return x",
    "    if True:\n        return 1\n    return 0",
    "    for i in range(3):\n        pass",
    "    while False:\n        pass",
    "    if 1:\n        return 1\n    elif 2:\n        return 2\n    else:\n        return 3",
    "    return [i for i in range(10) if i % 2 == 0]",
    "    try:\n        pass\n    except ValueError:\n        pass",
    "    a = 1\n    b = 2\n    c = 3\n    return a + b + c",
    "    return 1 if True else 0",
    "    x = True and False\n    return x",
    "    return 42",
]


class TestProfileRepositoryStatistics:
    """profile_repository() over a real multi-function fixture."""

    def test_returns_profile_matching_independent_parse(self, tmp_path):
        content = _make_source(_MIXED_BODIES)
        rel_path = _write(tmp_path, "sample.py", content)
        expected_sizes, expected_complexities = _reference_function_stats(content)

        profile = profile_repository(str(tmp_path), [rel_path])

        assert isinstance(profile, RepoProfile)
        assert profile.function_count == len(expected_sizes) == len(_MIXED_BODIES)
        assert profile.max_complexity == max(expected_complexities)
        # Percentiles are monotonic and mean sits within the observed range.
        assert (
            profile.p25_chars
            <= profile.p50_chars
            <= profile.p75_chars
            <= profile.p90_chars
        )
        assert min(expected_sizes) <= profile.mean_chars <= max(expected_sizes)

    def test_returns_none_below_min_functions(self, tmp_path):
        bodies = _MIXED_BODIES[: MIN_FUNCTIONS_FOR_PROFILE - 1]
        content = _make_source(bodies)
        rel_path = _write(tmp_path, "small.py", content)

        profile = profile_repository(str(tmp_path), [rel_path])

        assert profile is None

    def test_only_counts_top_level_functions_not_nested(self, tmp_path):
        """Matches _scan_tree's documented contract: a nested function inside
        a top-level function must not be counted separately (avoids
        double-counting)."""
        bodies = list(_MIXED_BODIES)
        bodies[0] = "    def inner():\n        return 1\n    return inner()"
        content = _make_source(bodies)
        rel_path = _write(tmp_path, "nested.py", content)

        profile = profile_repository(str(tmp_path), [rel_path])

        assert profile is not None
        assert profile.function_count == len(_MIXED_BODIES)

    def test_skips_file_over_max_size(self, tmp_path, monkeypatch):
        """Files over MAX_FILE_SIZE_BYTES are skipped entirely — verified by
        lowering the cap rather than writing a real 5 MB fixture."""
        import chunking.repo_profiler as repo_profiler_module

        content = _make_source(_MIXED_BODIES)
        rel_path = _write(tmp_path, "big.py", content)
        monkeypatch.setattr(repo_profiler_module, "MAX_FILE_SIZE_BYTES", 1)

        profile = profile_repository(str(tmp_path), [rel_path])

        assert profile is None  # the only file was skipped -> 0 functions found

    def test_missing_file_is_skipped_not_raised(self, tmp_path):
        content = _make_source(_MIXED_BODIES)
        rel_path = _write(tmp_path, "sample.py", content)

        profile = profile_repository(str(tmp_path), [rel_path, "does_not_exist.py"])

        assert profile is not None
        assert profile.function_count == len(_MIXED_BODIES)

    def test_counters_sum_to_total_supported_files(self, tmp_path, monkeypatch, caplog):
        """scanned + skipped + empty must equal len(supported_files) (item C).
        Two `continue` paths in profile_repository -- parse_file returning
        None, and empty/whitespace-only content -- previously incremented
        neither counter, so `Scanned N files (M skipped)` silently
        under-reported against the file count the indexer said it would
        profile."""
        import chunking.repo_profiler as repo_profiler_module

        monkeypatch.setattr(repo_profiler_module, "MAX_FILE_SIZE_BYTES", 100)

        oversized_rel = _write(
            tmp_path, "oversized.py", _make_source(_MIXED_BODIES)
        )  # well over 100 bytes -> skipped
        empty_rel = _write(tmp_path, "empty.py", "")  # -> empty
        normal_rel = _write(
            tmp_path, "normal.py", "def f():\n    return 1\n"
        )  # under 100 bytes -> scanned
        supported_files = [oversized_rel, empty_rel, normal_rel]

        with caplog.at_level(logging.INFO, logger="chunking.repo_profiler"):
            profile_repository(str(tmp_path), supported_files)

        scan_lines = [
            r.message
            for r in caplog.records
            if r.message.startswith("[PROFILER] Scanned")
        ]
        assert len(scan_lines) == 1
        match = re.search(
            r"Scanned (\d+) files \((\d+) skipped, (\d+) empty\)", scan_lines[0]
        )
        assert match is not None, scan_lines[0]
        scanned, skipped, empty = (int(g) for g in match.groups())
        assert scanned + skipped + empty == len(supported_files)
        assert scanned == 1  # normal.py
        assert skipped == 1  # oversized.py
        assert empty == 1  # empty.py


# GLSL panel-shader fixture: 2 real functions plus a dozen non-function
# splittable nodes (uniform declarations, a struct, a const array, macros,
# a #version directive) — every one of which is in GLSLChunker's
# splittable_node_types (chunk-granularity set) but none of which is a
# function. Item E's regression target.
_GLSL_PANEL_SHADER = """\
#version 330 core

#define PI 3.14159
#define TAU (2.0 * PI)

uniform mat4 uModel;
uniform mat4 uView;
uniform mat4 uProjection;
uniform vec3 uLightPos;
uniform vec3 uViewPos;
uniform float uRoughness;
uniform int uSampleCount;

struct Material {
    vec3 albedo;
    float roughness;
};

const vec3 COLORS[3] = vec3[3](vec3(1.0), vec3(0.5), vec3(0.0));

float roundedBoxSDF(vec3 p, vec3 b, float r) {
    vec3 q = abs(p) - b;
    return length(max(q, 0.0)) + min(max(q.x, max(q.y, q.z)), 0.0) - r;
}

void main() {
    vec3 col = uLightPos + uViewPos;
    gl_FragColor = vec4(col, 1.0);
}
"""


class TestProfileParsedFunctionNodeTypes:
    """profile_parsed() must measure only real functions for GLSL (item E).

    Before item E, repo_profiler derived "function" node types as
    splittable_node_types minus a fixed class-type blacklist — a derivation
    duplicated ad hoc for every chunker. GLSL's splittable set (chunk
    granularity) is deliberately much wider than "functions" (it also
    includes top-level declarations, structs, and preprocessor directives,
    each a meaningful standalone chunk), so that derivation measured every
    uniform/macro/struct as if it were a function, polluting the P25/P50/P75
    baseline the adaptive-sizing algorithm computes from function sizes.
    """

    def test_glsl_panel_shader_counts_only_the_two_functions(self, tmp_path):
        import chunking.tree_sitter as tsf
        from chunking.tree_sitter import TreeSitterChunker

        if "glsl" not in tsf.AVAILABLE_LANGUAGES:
            pytest.skip("tree-sitter-glsl not installed")

        file_path = tmp_path / "panel.frag"
        file_path.write_text(_GLSL_PANEL_SHADER, encoding="utf-8")

        parsed_source = TreeSitterChunker().parse_file(str(file_path))
        assert parsed_source is not None

        sizes: list[int] = []
        complexities: list[int] = []
        profile_parsed(parsed_source, sizes, complexities)

        assert len(sizes) == 2  # roundedBoxSDF + main only
