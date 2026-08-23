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

from chunking.language_registry import DEPENDENCY_TREE_DIRS
from search.filters import (
    ALWAYS_IGNORED_DIRS,
    DEFAULT_IGNORED_DIRS,
    MatchKind,
    PathFilter,
    is_dependency_pattern,
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
        # venv/site-packages is a dependency-tree pattern -> additive by
        # default: the target is re-admitted on top of the normal
        # root-down scope, other first-party files are NOT discarded.
        pf = PathFilter(["venv/Lib/site-packages/pkg"], None, self.root)
        assert pf.should_index_file("venv/Lib/site-packages/pkg/mod.py") is True
        # A different default-ignored dir the include didn't name stays out.
        assert pf.should_index_file("__pycache__/cache.pyc") is False
        # First-party files survive -- this is the whole point of additive.
        assert pf.should_index_file("README.md") is True

    def test_include_exclusive_disables_additive_rescue(self):
        # The escape hatch forces the same dependency-tree pattern back to
        # narrowing -- today's pre-additive whitelist-only behavior.
        pf = PathFilter(
            ["venv/Lib/site-packages/pkg"], None, self.root, include_exclusive=True
        )
        assert pf.should_index_file("venv/Lib/site-packages/pkg/mod.py") is True
        assert pf.should_index_file("__pycache__/cache.pyc") is False
        assert pf.should_index_file("README.md") is False

    def test_include_exclusive_admits_only_its_own_target_not_ancestors(self):
        pf = PathFilter(
            ["A/venv/Lib/site-packages"], None, self.root, include_exclusive=True
        )
        assert pf.should_index_file("A/top_level.py") is False
        assert pf.should_index_file("root_file.py") is False
        assert pf.should_index_file("A/venv/Lib/site-packages/pkg/mod.py") is True
        # But traversal must still be allowed to descend through ancestors
        # to reach the target.
        assert pf.should_traverse_dir("A") is True
        assert pf.should_traverse_dir("A/venv") is True
        assert pf.should_traverse_dir("A/venv/Lib/site-packages") is True

    def test_dependency_include_admits_target_plus_normal_scope(self):
        # Same pattern, default (additive) semantics: the target is
        # admitted AND the rest of the project's normal root-down scope
        # survives -- this is the fix for the reported incident.
        pf = PathFilter(["A/venv/Lib/site-packages"], None, self.root)
        assert pf.should_index_file("A/top_level.py") is True
        assert pf.should_index_file("root_file.py") is True
        assert pf.should_index_file("A/venv/Lib/site-packages/pkg/mod.py") is True

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
    """Direct regression test for the originally reported ancestor-leak bug
    (files at the project root and in ancestor directories of the include
    target selected instead of just the target) -- pinned via
    include_exclusive=True, which reproduces that whitelist-only behavior
    exactly. The companion test below covers the *later* incident this
    module's additive-by-default change fixes: the same dependency-tree
    pattern must NOT discard first-party source once include_exclusive is
    no longer forced."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_only_target_subtree_is_selected_with_include_exclusive(self):
        pf = PathFilter(
            ["StreamDiffusion/venv/Lib/site-packages/diffusers"],
            None,
            self.root,
            include_exclusive=True,
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

    def test_dependency_pattern_is_additive_by_default(self):
        # Same pattern, no include_exclusive: this is the actual incident
        # shape (D:\dev\SDTD_040_Beta, 8 site-packages-only include
        # patterns). First-party source at the root and under
        # StreamDiffusion/ is indexed as usual, on top of the requested
        # target -- nothing about the project is silently discarded.
        pf = PathFilter(
            ["StreamDiffusion/venv/Lib/site-packages/diffusers"], None, self.root
        )

        for f in ("README.md", "setup.py", ".upstream_builder_dotsimulate.py"):
            assert pf.should_index_file(f) is True, f

        assert pf.should_index_file("StreamDiffusion/setup.py") is True

        assert (
            pf.should_index_file(
                "StreamDiffusion/venv/Lib/site-packages/diffusers/__init__.py"
            )
            is True
        )

        # A sibling package under the same dependency tree that was NOT
        # named in include_dirs still stays excluded -- additive widens
        # scope to the normal source tree plus the named target(s), it
        # does not turn into "index everything under site-packages".
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


class TestPatternClassification(TestCase):
    """Additive-vs-narrowing classification (is_dependency_pattern) and its
    effect through PathFilter -- the fix for the D:\\dev\\SDTD_040_Beta
    incident: 8 include patterns, all pointing into
    StreamDiffusion/venv/Lib/site-packages, silently discarded every
    first-party file (IPAdapterModule, engine_manager.py, wrapper.py, ...)
    because a whitelist-only include_dirs treated re-admission and
    narrowing as the same operation."""

    INCIDENT_PATTERNS = [
        "StreamDiffusion/venv/Lib/site-packages/diffusers*",
        "StreamDiffusion/venv/Lib/site-packages/insightface",
        "StreamDiffusion/venv/Lib/site-packages/huggingface_hub",
        "StreamDiffusion/venv/Lib/site-packages/polygraphy",
        "StreamDiffusion/venv/Lib/site-packages/onnx*",
        "StreamDiffusion/venv/Lib/site-packages/accelerate",
        "StreamDiffusion/venv/Lib/site-packages/peft",
        "StreamDiffusion/venv/Lib/site-packages/controlnet_aux",
    ]

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_incident_patterns_all_classify_additive(self):
        pf = PathFilter(self.INCIDENT_PATTERNS, None, self.root)
        assert len(pf.additive_patterns) == len(self.INCIDENT_PATTERNS)
        assert pf.narrowing_patterns == []
        for pat in pf.include_patterns:
            assert is_dependency_pattern(pat) is True

    def test_incident_patterns_admit_first_party_source(self):
        pf = PathFilter(self.INCIDENT_PATTERNS, None, self.root)
        # The exact symbols from the report that went unsearchable.
        assert pf.should_index_file("StreamDiffusion/src/wrapper.py") is True
        assert pf.should_index_file("StreamDiffusionTD/engine_manager.py") is True
        assert pf.should_index_file("Scripts/build.py") is True
        # The requested libraries are still admitted.
        assert (
            pf.should_index_file(
                "StreamDiffusion/venv/Lib/site-packages/diffusers_ipadapter/mod.py"
            )
            is True
        )
        # A library NOT in the 8 patterns stays excluded.
        assert (
            pf.should_index_file("StreamDiffusion/venv/Lib/site-packages/torch/mod.py")
            is False
        )

    def test_incident_patterns_with_include_exclusive_restores_whitelist(self):
        # The escape hatch reproduces the ORIGINAL incident exactly: only
        # the 8 named libraries survive, first-party source is discarded.
        pf = PathFilter(self.INCIDENT_PATTERNS, None, self.root, include_exclusive=True)
        assert pf.narrowing_patterns == pf.include_patterns
        assert pf.additive_patterns == []
        assert pf.should_index_file("StreamDiffusion/src/wrapper.py") is False
        assert (
            pf.should_index_file(
                "StreamDiffusion/venv/Lib/site-packages/diffusers_ipadapter/mod.py"
            )
            is True
        )

    def test_plain_source_pattern_stays_narrowing(self):
        pat = parse_dir_pattern("src/core", self.root)
        assert is_dependency_pattern(pat) is False
        pf = PathFilter(["src/core"], None, self.root)
        assert pf.narrowing_patterns == pf.include_patterns
        assert pf.additive_patterns == []
        assert pf.should_index_file("src/core/mod.py") is True
        assert pf.should_index_file("src/other/mod.py") is False
        assert pf.should_index_file("README.md") is False

    def test_mixed_list_unions_narrowing_and_additive(self):
        pf = PathFilter(["src/core", "venv/Lib/site-packages/torch"], None, self.root)
        assert len(pf.narrowing_patterns) == 1
        assert len(pf.additive_patterns) == 1
        # src/core: narrowing pattern's own target.
        assert pf.should_index_file("src/core/mod.py") is True
        # torch: additive pattern's own target.
        assert pf.should_index_file("venv/Lib/site-packages/torch/mod.py") is True
        # A source file outside src/core is excluded -- the narrowing
        # pattern still restricts the non-dependency portion of the scope.
        assert pf.should_index_file("src/other/mod.py") is False
        # An unnamed dependency stays excluded too.
        assert pf.should_index_file("venv/Lib/site-packages/numpy/mod.py") is False

    def test_build_output_dirs_are_not_treated_as_dependency_trees(self):
        # "out" and "src" are both plausible source-directory names --
        # DEPENDENCY_TREE_DIRS deliberately excludes build/dist/out/public
        # so a pattern naming them stays narrowing and never silently
        # widens back out to the whole project.
        pat = parse_dir_pattern("out/src", self.root)
        assert is_dependency_pattern(pat) is False
        pf = PathFilter(["out/src"], None, self.root)
        assert pf.narrowing_patterns == pf.include_patterns
        assert pf.should_index_file("out/src/mod.py") is True
        assert pf.should_index_file("README.md") is False

    def test_backslash_pattern_classifies_additive(self):
        # Windows-native separators must resolve to the same segments as
        # forward slashes -- parse_dir_pattern normalizes both, and
        # is_dependency_pattern must see the normalized segments, not the
        # raw backslash-joined string (which would never match a
        # DEPENDENCY_TREE_DIRS member).
        pat = parse_dir_pattern(
            "StreamDiffusion\\venv\\Lib\\site-packages\\diffusers", self.root
        )
        assert is_dependency_pattern(pat) is True
        pf = PathFilter(
            ["StreamDiffusion\\venv\\Lib\\site-packages\\diffusers"], None, self.root
        )
        assert pf.should_index_file("StreamDiffusion/src/wrapper.py") is True
        assert (
            pf.should_index_file(
                "StreamDiffusion/venv/Lib/site-packages/diffusers/mod.py"
            )
            is True
        )


class TestVendoringDirectoryDefaults(TestCase):
    """Workstream B1 -- vendored/third-party C/C++ dependency-tree names.

    Verified impact (see the plan): `third_party/` holds `json.hpp` (35.6%
    of one project's indexed lines) and a project can also vendor under
    `vendor/`. Both sets get the *same* names so include_dirs re-admission
    stays additive (ADR-0036), matching the existing `venv`/`site-packages`
    behavior exercised above -- these are just new members of the same
    mechanism, not a new code path.
    """

    VENDOR_NAMES = (
        "third_party",
        "thirdparty",
        "third-party",
        "3rdparty",
        "vendor",
        "vendored",
        "extern",
        "deps",
        "_deps",
        "subprojects",
        "submodules",
    )

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_vendor_names_are_default_ignored(self):
        for name in self.VENDOR_NAMES:
            assert name in DEFAULT_IGNORED_DIRS, name

    def test_vendor_names_are_dependency_tree_dirs(self):
        # Same name set in both -- keeps DEPENDENCY_TREE_DIRS <=
        # DEFAULT_IGNORED_DIRS satisfied and makes an include pattern that
        # names one of these additive rather than narrowing.
        for name in self.VENDOR_NAMES:
            assert name in DEPENDENCY_TREE_DIRS, name

    def test_external_deliberately_held_back(self):
        # The plan's one explicitly-contestable name: plausible as a
        # first-party directory, so it stays a normal (narrowing-only, not
        # auto-ignored) name rather than risking the
        # only_dependency_paths_matched abort path for a project whose real
        # source lives under external/.
        assert "external" not in DEFAULT_IGNORED_DIRS
        assert "external" not in DEPENDENCY_TREE_DIRS

    def test_vendor_pattern_classifies_additive(self):
        pat = parse_dir_pattern("third_party/foo", self.root)
        assert is_dependency_pattern(pat) is True

    def test_include_rescues_vendored_dir_and_admits_first_party_source(self):
        # Mirrors test_include_rescues_default_ignored_dir above, for the
        # new vendoring names: additive re-admission of one vendored
        # subtree, first-party source is not discarded.
        pf = PathFilter(["third_party/foo"], None, self.root)
        assert pf.should_index_file("third_party/foo/mod.cpp") is True
        # A sibling vendored library NOT named in include_dirs stays
        # excluded -- additive widens scope to the target plus normal
        # source, not "index everything under third_party".
        assert pf.should_index_file("third_party/bar/mod.cpp") is False
        assert pf.should_index_file("src/engine.cpp") is True

    def test_vendored_dir_excluded_by_default_with_no_filters(self):
        pf = PathFilter(None, None, self.root)
        for name in self.VENDOR_NAMES:
            assert pf.should_index_file(f"{name}/mod.cpp") is False, name

    def test_deps_cmake_fetchcontent_dir_excluded_by_default(self):
        # The most likely real-world collision: CMake FetchContent's
        # default download/build directory nested under build/.
        pf = PathFilter(None, None, self.root)
        assert pf.should_index_file("build/_deps/googletest-src/gtest.cc") is False
