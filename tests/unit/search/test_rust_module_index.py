"""Unit tests for search.rust_module_index (ADR-0091 D: Rust use-path resolution).

One tmp Cargo workspace covers every scope rule the graph build relies on:
two crates, `#[path]`, a file mounted by two targets, inline modules, named /
grouped / aliased / glob / `self` / `super` / `crate` imports, a `pub use`
chain, `use super::*` in a test module, std and crates.io imports, a `type`
alias and a renamed dependency.
"""

from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import pytest

from search.rust_module_index import RustModuleIndex


pytest.importorskip("tree_sitter_rust")

_FILES = {
    "Cargo.toml": """
        [workspace]
        members = ["crates/*"]

        [workspace.dependencies]
        serde_json = "1"
        core-lib = { path = "crates/core-lib" }
    """,
    "crates/core-lib/Cargo.toml": """
        [package]
        name = "core-lib"

        [dependencies]
        serde_json = { workspace = true }
        json = { package = "serde_json", version = "1" }
    """,
    "crates/core-lib/src/lib.rs": """
        pub mod audio;
        #[path = "weird/place.rs"]
        pub mod place;
        pub use audio::mix as mix_alias;

        pub mod prelude {
            pub use crate::audio::Mixer;
        }

        #[derive(Default)]
        pub struct Node;

        pub fn top() {}

        mod inner {
            pub fn deep() {}
        }

        pub fn uses_inner() {
            inner::deep(); // MARK lib-inner
            json::to_string(&1); // MARK lib-json
        }
    """,
    "crates/core-lib/src/audio.rs": """
        mod helpers;

        pub fn mix() {}

        pub struct Mixer;

        impl Mixer {
            pub fn new() -> Self {
                helpers::help(); // MARK audio-helpers
                Mixer
            }
        }
    """,
    "crates/core-lib/src/audio/helpers.rs": """
        use super::*;

        pub fn help() {}

        #[cfg(test)]
        mod tests {
            use super::*;

            fn t() {
                Mixer::new(); // MARK helpers-tests-chain
            }
        }
    """,
    "crates/core-lib/src/weird/place.rs": """
        pub fn placed() {}
    """,
    "crates/app/Cargo.toml": """
        [package]
        name = "app"

        [dependencies]
        core-lib = { workspace = true }
        tempfile = "3"
    """,
    "crates/app/src/main.rs": """
        use core_lib::{audio::{self, mix}, prelude::*, place::placed as pl};
        use std::sync::Arc;
        use tempfile::tempdir;

        type Fx = core_lib::audio::Mixer;

        mod shared;

        fn main() {
            mix(); // MARK main-mix
            audio::mix(); // MARK main-audio-mix
            Mixer::new(); // MARK main-mixer-new
            pl(); // MARK main-pl
            Arc::new(1); // MARK main-arc
            tempdir(); // MARK main-tempdir
            Fx::new(); // MARK main-fx
            Vec::<u8>::new(); // MARK main-vec
            local(); // MARK main-local
            core_lib::top(); // MARK main-top
            core_lib::mix_alias(); // MARK main-reexport
            core_lib::Node::default(); // MARK main-node-default
            thing::run(); // MARK main-unknown
            {
                use core_lib::place::placed;
                placed(); // MARK main-block-use
            }
        }

        fn local() {}

        #[cfg(test)]
        mod tests {
            use super::*;

            fn t() {
                mix(); // MARK tests-mix
                local(); // MARK tests-local
            }
        }
    """,
    "crates/app/src/shared.rs": """
        pub fn shared_fn() {}

        pub fn calls_shared() {
            shared_fn(); // MARK shared-local
        }
    """,
    "crates/app/examples/probe.rs": """
        #[path = "../src/shared.rs"]
        mod shared;

        fn main() {}
    """,
}


@pytest.fixture(scope="module")
def ws(tmp_path_factory: pytest.TempPathFactory) -> Path:
    root = tmp_path_factory.mktemp("rustws")
    for rel, text in _FILES.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(dedent(text).lstrip("\n"), encoding="utf-8")
    return root


@pytest.fixture(scope="module")
def index() -> RustModuleIndex:
    return RustModuleIndex()


def _at(ws: Path, rel: str, mark: str) -> tuple[Path, int]:
    path = ws / rel
    for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if f"MARK {mark}" in line:
            return path, n
    raise AssertionError(f"marker {mark!r} not in {rel}")


MAIN = "crates/app/src/main.rs"


@pytest.mark.parametrize(
    ("mark", "segments", "expected"),
    [
        ("main-mix", ["mix"], ("internal", "core_lib", ("audio",), "mix", ())),
        (
            "main-audio-mix",
            ["audio", "mix"],
            ("internal", "core_lib", ("audio",), "mix", ()),
        ),
        (
            "main-mixer-new",
            ["Mixer", "new"],
            ("internal", "core_lib", ("audio",), "Mixer", ("new",)),
        ),
        ("main-pl", ["pl"], ("internal", "core_lib", ("place",), "placed", ())),
        (
            "main-fx",
            ["Fx", "new"],
            ("internal", "core_lib", ("audio",), "Mixer", ("new",)),
        ),
        ("main-local", ["local"], ("internal", "app", (), "local", ())),
        ("main-top", ["core_lib", "top"], ("internal", "core_lib", (), "top", ())),
        (
            "main-reexport",
            ["core_lib", "mix_alias"],
            ("internal", "core_lib", ("audio",), "mix", ()),
        ),
        (
            "main-node-default",
            ["core_lib", "Node", "default"],
            ("internal", "core_lib", (), "Node", ("default",)),
        ),
        (
            "main-block-use",
            ["placed"],
            ("internal", "core_lib", ("place",), "placed", ()),
        ),
    ],
    ids=lambda v: v if isinstance(v, str) else None,
)
def test_internal_paths_from_the_binary(ws, index, mark, segments, expected) -> None:
    file, line = _at(ws, MAIN, mark)
    r = index.resolve(file, line, segments)
    assert (r.kind, r.crate, r.module, r.item, r.rest) == expected


@pytest.mark.parametrize(
    ("mark", "segments", "crate"),
    [
        ("main-arc", ["Arc", "new"], "std"),
        ("main-tempdir", ["tempdir"], "tempfile"),
        ("main-vec", ["Vec", "new"], "std"),
    ],
    ids=["std-import", "crates-io-dep", "std-prelude"],
)
def test_external_paths_from_the_binary(ws, index, mark, segments, crate) -> None:
    file, line = _at(ws, MAIN, mark)
    r = index.resolve(file, line, segments)
    assert (r.kind, r.crate) == ("external", crate)


def test_unmatched_first_segment_is_unknown(ws, index) -> None:
    file, line = _at(ws, MAIN, "main-unknown")
    assert index.resolve(file, line, ["thing", "run"]).kind == "unknown"


def test_glob_super_in_test_module_sees_parent_imports_and_items(ws, index) -> None:
    file, line = _at(ws, MAIN, "tests-mix")
    r = index.resolve(file, line, ["mix"])
    assert (r.kind, r.crate, r.module, r.item) == (
        "internal",
        "core_lib",
        ("audio",),
        "mix",
    )
    file, line = _at(ws, MAIN, "tests-local")
    r = index.resolve(file, line, ["local"])
    assert (r.kind, r.crate, r.module, r.item) == ("internal", "app", (), "local")


def test_glob_chain_reaches_grandparent_items(ws, index) -> None:
    file, line = _at(ws, "crates/core-lib/src/audio/helpers.rs", "helpers-tests-chain")
    r = index.resolve(file, line, ["Mixer", "new"])
    assert (r.kind, r.module, r.item, r.rest) == (
        "internal",
        ("audio",),
        "Mixer",
        ("new",),
    )


def test_prelude_function_is_external(ws, index) -> None:
    file, line = _at(ws, MAIN, "main-local")
    assert (index.resolve(file, line, ["drop"]).kind) == "external"


def test_renamed_dependency_is_external(ws, index) -> None:
    file, line = _at(ws, "crates/core-lib/src/lib.rs", "lib-json")
    r = index.resolve(file, line, ["json", "to_string"])
    assert (r.kind, r.crate) == ("external", "json")


def test_inline_module_resolves_inside_its_file(ws, index) -> None:
    file, line = _at(ws, "crates/core-lib/src/lib.rs", "lib-inner")
    r = index.resolve(file, line, ["inner", "deep"])
    assert (r.kind, r.module, r.item) == ("internal", ("inner",), "deep")
    [span] = index.module_spans(r)
    assert span.file == ws / "crates/core-lib/src/lib.rs"
    text = span.file.read_text(encoding="utf-8").splitlines()
    assert "mod inner" in text[span.start - 1]
    assert span.start < span.end < len(text)


def test_nested_file_module_from_non_mod_rs_parent(ws, index) -> None:
    file, line = _at(ws, "crates/core-lib/src/audio.rs", "audio-helpers")
    r = index.resolve(file, line, ["helpers", "help"])
    assert (r.kind, r.module, r.item) == ("internal", ("audio", "helpers"), "help")
    assert [s.file for s in index.module_spans(r)] == [
        ws / "crates/core-lib/src/audio/helpers.rs"
    ]


def test_path_attribute_maps_module_to_its_file(ws, index) -> None:
    file, line = _at(ws, MAIN, "main-pl")
    r = index.resolve(file, line, ["pl"])
    assert [s.file for s in index.module_spans(r)] == [
        ws / "crates/core-lib/src/weird/place.rs"
    ]


def test_root_module_span_excludes_inline_children(ws, index) -> None:
    file, line = _at(ws, MAIN, "main-top")
    r = index.resolve(file, line, ["core_lib", "top"])
    [span] = index.module_spans(r)
    assert span.file == ws / "crates/core-lib/src/lib.rs"
    assert span.holes, (
        "inline `mod prelude` / `mod inner` must be holes of the root span"
    )


def test_file_mounted_by_two_targets_resolves_local_items(ws, index) -> None:
    file, line = _at(ws, "crates/app/src/shared.rs", "shared-local")
    r = index.resolve(file, line, ["shared_fn"])
    assert (r.kind, r.module, r.item) == ("internal", ("shared",), "shared_fn")
    assert {s.file for s in index.module_spans(r)} == {ws / "crates/app/src/shared.rs"}


def test_impl_crate_files_include_dependent_crates(ws, index) -> None:
    file, line = _at(ws, MAIN, "main-mixer-new")
    r = index.resolve(file, line, ["Mixer", "new"])
    own = index.crate_files(r)
    assert ws / "crates/core-lib/src/audio.rs" in own
    assert ws / MAIN not in own
    assert ws / MAIN in index.impl_crate_files(r)


def test_file_outside_any_crate_is_unknown(tmp_path, index) -> None:
    stray = tmp_path / "loose.rs"
    stray.write_text("fn f() { g(); }\n", encoding="utf-8")
    assert index.resolve(stray, 1, ["g"]).kind == "unknown"
