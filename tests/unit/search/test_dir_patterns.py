"""Unit tests for the gitignore-style include/exclude pattern engine.

Covers `parse_dir_pattern`, `match_pattern`, and the `PathFilter`
precedence resolver in `search/filters.py` — the fix for the reported bug
where `include_dirs` pointed at a directory under a default-ignored
ancestor (e.g. `venv/Lib/site-packages/<pkg>`) and silently indexed
ancestor files instead of the requested target.
"""

import tempfile
from pathlib import Path
from unittest import TestCase

from search.filters import (
    ALWAYS_IGNORED_DIRS,
    DEFAULT_IGNORED_DIRS,
    MatchKind,
    PathFilter,
    match_pattern,
    parse_dir_pattern,
)


class TestParseDirPattern(TestCase):
    """Parsing raw user strings into DirPattern."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_none_and_empty_drop(self):
        assert parse_dir_pattern(None, self.root) is None
        assert parse_dir_pattern("", self.root) is None
        assert parse_dir_pattern("   ", self.root) is None

    def test_whitespace_is_stripped(self):
        pat = parse_dir_pattern("  src  ", self.root)
        assert pat is not None
        assert pat.segments == ("src",)
        assert pat.anchored is False

    def test_leading_dot_slash_is_stripped(self):
        pat = parse_dir_pattern("./src/pkg", self.root)
        assert pat is not None
        assert pat.segments == ("src", "pkg")
        assert pat.anchored is True

    def test_trailing_slash_is_stripped_but_stays_unanchored(self):
        # A bare basename with a trailing slash has no interior separator,
        # so — despite looking root-anchored — it still matches at any
        # depth. Documented gitignore-style quirk: the anchored check runs
        # against the post-rstrip string.
        pat = parse_dir_pattern("src/", self.root)
        assert pat is not None
        assert pat.segments == ("src",)
        assert pat.anchored is False

    def test_leading_slash_anchors_single_segment(self):
        # A bare "/src" is caught earlier by the absolute-POSIX-path branch
        # (and dropped, since it doesn't resolve under a Windows temp root)
        # — ".//src" reaches the leading-slash-anchors branch after the
        # "./" stripping loop leaves a literal leading "/" behind.
        pat = parse_dir_pattern(".//src", self.root)
        assert pat is not None
        assert pat.segments == ("src",)
        assert pat.anchored is True

    def test_multi_segment_is_anchored(self):
        pat = parse_dir_pattern("src/pkg", self.root)
        assert pat is not None
        assert pat.anchored is True
        assert pat.segments == ("src", "pkg")

    def test_backslashes_normalize_to_segments(self):
        pat = parse_dir_pattern("src\\pkg\\mod", self.root)
        assert pat is not None
        assert pat.segments == ("src", "pkg", "mod")
        assert pat.anchored is True

    def test_mcp_double_escaped_backslashes(self):
        # The MCP JSON transport sometimes double-escapes backslashes.
        pat = parse_dir_pattern("src\\\\pkg\\\\mod", self.root)
        assert pat is not None
        assert pat.segments == ("src", "pkg", "mod")

    def test_wildcard_detection(self):
        assert parse_dir_pattern("site-packages/*", self.root).has_wildcard is True
        assert parse_dir_pattern("foo?bar", self.root).has_wildcard is True
        assert parse_dir_pattern("[abc]dir", self.root).has_wildcard is True
        assert parse_dir_pattern("plain", self.root).has_wildcard is False

    def test_absolute_windows_path_under_root_resolves_relative(self):
        target = self.root / "StreamDiffusion" / "venv" / "Lib" / "site-packages"
        target.mkdir(parents=True)
        pat = parse_dir_pattern(str(target), self.root)
        assert pat is not None
        assert pat.anchored is True
        assert pat.segments == ("StreamDiffusion", "venv", "Lib", "site-packages")

    def test_absolute_path_outside_root_drops_with_none(self):
        with tempfile.TemporaryDirectory() as other:
            pat = parse_dir_pattern(other, self.root)
        assert pat is None

    def test_absolute_pattern_without_root_drops_with_none(self):
        pat = parse_dir_pattern("C:/some/where", None)
        assert pat is None

    def test_pattern_normalizing_to_empty_drops(self):
        # A lone slash normalizes away to nothing.
        pat = parse_dir_pattern("/", self.root)
        assert pat is None

    def test_raw_is_preserved_for_diagnostics(self):
        pat = parse_dir_pattern("  ./src/pkg/  ", self.root)
        assert pat.raw == "  ./src/pkg/  "


class TestMatchPattern(TestCase):
    """Matching parsed patterns against relative path segments."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def _pat(self, raw):
        pat = parse_dir_pattern(raw, self.root)
        assert pat is not None, f"pattern {raw!r} unexpectedly dropped"
        return pat

    def test_anchored_inside(self):
        pat = self._pat("src/pkg")
        assert match_pattern(pat, ("src", "pkg", "mod.py")) is MatchKind.INSIDE
        assert match_pattern(pat, ("src", "pkg")) is MatchKind.INSIDE

    def test_anchored_ancestor(self):
        pat = self._pat("src/pkg")
        assert match_pattern(pat, ("src",)) is MatchKind.ANCESTOR
        assert match_pattern(pat, ()) is MatchKind.ANCESTOR

    def test_anchored_none(self):
        pat = self._pat("src/pkg")
        assert match_pattern(pat, ("lib", "pkg")) is MatchKind.NONE
        assert match_pattern(pat, ("src", "other")) is MatchKind.NONE

    def test_unanchored_matches_any_depth(self):
        pat = self._pat("pkg")
        assert match_pattern(pat, ("pkg",)) is MatchKind.INSIDE
        assert match_pattern(pat, ("a", "b", "pkg")) is MatchKind.INSIDE
        assert match_pattern(pat, ("a", "pkg", "mod.py")) is MatchKind.INSIDE

    def test_unanchored_ancestor_when_not_yet_matched(self):
        pat = self._pat("pkg")
        assert match_pattern(pat, ("a", "b")) is MatchKind.ANCESTOR

    def test_double_star_matches_zero_or_more_segments(self):
        pat = self._pat("src/**/mod.py")
        assert match_pattern(pat, ("src", "mod.py")) is MatchKind.INSIDE
        assert match_pattern(pat, ("src", "a", "mod.py")) is MatchKind.INSIDE
        assert match_pattern(pat, ("src", "a", "b", "mod.py")) is MatchKind.INSIDE
        assert match_pattern(pat, ("src", "a")) is MatchKind.ANCESTOR

    def test_question_mark_wildcard(self):
        pat = self._pat("fo?")
        assert match_pattern(pat, ("foo",)) is MatchKind.INSIDE
        # Unanchored matching is conservative for a single, still-unmatched
        # segment — it can't rule out a deeper descendant matching, so it
        # reports ANCESTOR rather than NONE (see _match_unanchored). A file
        # gate (should_index_file) still rejects it since only INSIDE
        # satisfies the file requirement.
        assert match_pattern(pat, ("fooo",)) is MatchKind.ANCESTOR

    def test_bracket_wildcard(self):
        pat = self._pat("[abc]dir")
        assert match_pattern(pat, ("adir",)) is MatchKind.INSIDE
        assert match_pattern(pat, ("bdir",)) is MatchKind.INSIDE
        assert match_pattern(pat, ("zdir",)) is MatchKind.ANCESTOR

    def test_star_wildcard_any_depth(self):
        pat = self._pat("site-packages/diffusers*")
        assert (
            match_pattern(pat, ("site-packages", "diffusers_ipadapter", "mod.py"))
            is MatchKind.INSIDE
        )
        assert match_pattern(pat, ("site-packages", "diffusers")) is MatchKind.INSIDE
        assert match_pattern(pat, ("site-packages", "torch")) is MatchKind.NONE


class TestWindowsCaseInsensitivity(TestCase):
    """fnmatch case-folds via os.path.normcase — case-insensitive on Windows."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_case_insensitive_match_on_windows(self):
        pat = parse_dir_pattern("Site-Packages/Diffusers", self.root)
        result = match_pattern(pat, ("site-packages", "diffusers", "mod.py"))
        # os.name is 'nt' in this repo's target environment (Windows host).
        import os

        if os.name == "nt":
            assert result is MatchKind.INSIDE
        else:
            assert result is MatchKind.NONE


class TestPathFilterPrecedence(TestCase):
    """The single precedence-ordered resolver: exclude > include > defaults."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_no_filters_accepts_everything_not_default_ignored(self):
        pf = PathFilter(None, None, self.root)
        assert pf.should_index_file("src/main.py") is True
        assert pf.should_index_file("__pycache__/x.pyc") is False

    def test_include_rescues_default_ignored_dir(self):
        pf = PathFilter(["venv/Lib/site-packages/pkg"], None, self.root)
        assert pf.should_index_file("venv/Lib/site-packages/pkg/mod.py") is True
        # A different default-ignored dir the include didn't name stays out.
        assert pf.should_index_file("__pycache__/cache.pyc") is False
        # Files outside the include target are excluded once include_dirs
        # is non-empty.
        assert pf.should_index_file("README.md") is False

    def test_include_admits_only_its_own_target_not_ancestors(self):
        pf = PathFilter(["A/venv/Lib/site-packages"], None, self.root)
        assert pf.should_index_file("A/top_level.py") is False
        assert pf.should_index_file("root_file.py") is False
        assert pf.should_index_file("A/venv/Lib/site-packages/pkg/mod.py") is True
        # But traversal must still be allowed to descend through ancestors
        # to reach the target.
        assert pf.should_traverse_dir("A") is True
        assert pf.should_traverse_dir("A/venv") is True
        assert pf.should_traverse_dir("A/venv/Lib/site-packages") is True

    def test_exclude_beats_include(self):
        pf = PathFilter(
            ["site-packages/diffusers"], ["site-packages/diffusers/skip"], self.root
        )
        assert pf.should_index_file("site-packages/diffusers/mod.py") is True
        assert pf.should_index_file("site-packages/diffusers/skip/bad.py") is False

    def test_git_is_never_rescued_by_include(self):
        pf = PathFilter([".git/hooks"], None, self.root)
        assert pf.should_index_file(".git/hooks/pre-commit.py") is False
        assert pf.should_traverse_dir(".git") is False

    def test_always_ignored_checked_across_all_segments(self):
        pf = PathFilter(None, None, self.root)
        # .git nested unusually deep is still rejected.
        assert pf.should_index_file("a/b/.git/c/mod.py") is False

    def test_unmatched_pattern_reported(self):
        pf = PathFilter(
            ["site-packages/diffusers", "site-packages/compel"], None, self.root
        )
        pf.should_index_file("site-packages/diffusers/mod.py")
        # compel never matched anything -> must surface as unmatched, never
        # silently dropped.
        assert "site-packages/compel" in pf.unmatched_patterns()
        assert "site-packages/diffusers" not in pf.unmatched_patterns()

    def test_all_includes_unmatched_true_only_when_all_zero(self):
        pf = PathFilter(["a", "b"], None, self.root)
        assert pf.all_includes_unmatched() is True  # nothing indexed yet
        pf.should_index_file("a/mod.py")
        assert pf.all_includes_unmatched() is False

    def test_all_includes_unmatched_false_when_no_includes_configured(self):
        pf = PathFilter(None, None, self.root)
        assert pf.all_includes_unmatched() is False

    def test_exclude_unmatched_pattern_also_reported(self):
        pf = PathFilter(None, ["does/not/exist"], self.root)
        pf.should_index_file("src/main.py")
        assert "does/not/exist" in pf.unmatched_patterns()

    def test_dropped_absolute_pattern_outside_root_never_matches(self):
        with tempfile.TemporaryDirectory() as other:
            pf = PathFilter([other], None, self.root)
        # The pattern was dropped at parse time (logged as a warning); with
        # zero surviving include patterns, PathFilter falls back to
        # "no include filter configured" behavior rather than "match
        # nothing" — but the dropped raw pattern is not silently treated as
        # a phantom include, so nothing about it is falsely reported as
        # matched. Confirm indexing still proceeds using only defaults.
        assert pf.include_patterns == []
        assert pf.should_index_file("src/main.py") is True

    def test_wildcard_include_matches_multiple_targets(self):
        pf = PathFilter(["site-packages/diffusers*"], None, self.root)
        assert pf.should_index_file("site-packages/diffusers/mod.py") is True
        assert pf.should_index_file("site-packages/diffusers_ipadapter/mod.py") is True
        assert pf.should_index_file("site-packages/torch/mod.py") is False


class TestPathFilterRegression(TestCase):
    """Direct regression test for the originally reported bug: files at the
    project root and in ancestor directories of the include target must
    never be selected, and the target's own files must be."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_only_target_subtree_is_selected(self):
        pf = PathFilter(
            ["StreamDiffusion/venv/Lib/site-packages/diffusers"], None, self.root
        )

        # Root-level files (the "14 files" from the report).
        for f in ("README.md", "setup.py", ".upstream_builder_dotsimulate.py"):
            assert pf.should_index_file(f) is False, f

        # StreamDiffusion top-level files (the "17 files" from the report).
        assert pf.should_index_file("StreamDiffusion/setup.py") is False

        # The actually-requested target.
        assert (
            pf.should_index_file(
                "StreamDiffusion/venv/Lib/site-packages/diffusers/__init__.py"
            )
            is True
        )

        # A sibling package under the same doubly-default-ignored prefix
        # that was NOT named in include_dirs stays excluded.
        assert (
            pf.should_index_file(
                "StreamDiffusion/venv/Lib/site-packages/torch/__init__.py"
            )
            is False
        )

    def test_never_matching_pattern_surfaces_as_unmatched_not_silent(self):
        # 'compel' is absent from the real tree in the reported scenario —
        # confirm it shows up loudly rather than just shrinking the index.
        pf = PathFilter(
            [
                "StreamDiffusion/venv/Lib/site-packages/diffusers",
                "StreamDiffusion/venv/Lib/site-packages/compel",
            ],
            None,
            self.root,
        )
        pf.should_index_file(
            "StreamDiffusion/venv/Lib/site-packages/diffusers/__init__.py"
        )
        assert (
            "StreamDiffusion/venv/Lib/site-packages/compel" in pf.unmatched_patterns()
        )
        assert pf.all_includes_unmatched() is False


class TestConstants(TestCase):
    """Sanity checks on the module-level ignore sets used by PathFilter."""

    def test_always_ignored_is_a_strict_subset_of_default_ignored(self):
        assert ALWAYS_IGNORED_DIRS <= DEFAULT_IGNORED_DIRS

    def test_venv_and_site_packages_are_overridable_defaults(self):
        assert "venv" in DEFAULT_IGNORED_DIRS
        assert "site-packages" in DEFAULT_IGNORED_DIRS
        # Overridable defaults must NOT be in the never-rescuable set.
        assert "venv" not in ALWAYS_IGNORED_DIRS
        assert "site-packages" not in ALWAYS_IGNORED_DIRS
