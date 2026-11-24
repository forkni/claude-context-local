"""Rust crate and module layout for use-path call resolution (ADR-0091, "D").

The tree-sitter Rust tier (ADR-0070) resolves calls by bare name plus one
``Type::m`` lookup; it never reads ``use`` imports, so ``Arc::new()`` imported
from ``std`` can land on a project ``Arc::new``, and an imported ``mix()``
fans out to every project ``mix``. File-root ``use`` statements never reach
chunk metadata at all (``module_preamble`` chunks skip ``extract_metadata``),
so this module reads the layout from disk instead:

- **Crates** come from the Cargo workspace: every member ``Cargo.toml`` gives a
  package, every target (lib, bins, tests, examples, benches, build script) is
  its own crate with its own root file. Dependencies are split into project
  crates (path or ``workspace = true`` deps that are workspace members) and
  external ones.
- **Modules** follow the 2018 rules from each root: ``mod x;`` loads ``x.rs``
  or ``x/mod.rs``, ``#[path = "..."]`` overrides that, ``mod x { }`` is an
  inline module inside the same file. A file mounted by two targets keeps
  every mount.
- **Scopes** per module: named, aliased, grouped and glob imports (with
  ``self``/``super``/``crate``/``::`` prefixes), ``pub use`` re-exports,
  local items, ``type`` aliases, and block-level ``use`` inside function
  bodies.

:meth:`RustModuleIndex.resolve` turns a call path seen at a file line into a
:class:`Resolution`: *internal* (a project crate, module and item), *external*
(``std``/``core``/``alloc``, the std prelude, or a declared non-workspace
dependency) or *unknown* (anything else: today's resolution applies).
Everything is built lazily and cached for the lifetime of one index object.
"""

from __future__ import annotations

import logging
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal


logger = logging.getLogger(__name__)

try:
    import tree_sitter_rust
    from tree_sitter import Language, Parser, Query, QueryCursor

    _LANGUAGE = Language(tree_sitter_rust.language())
    _PARSER: Parser | None = Parser(_LANGUAGE)
    # `use` inside a function body (or any block): scoped to that block's lines.
    _BLOCK_USE = Query(_LANGUAGE, "(block (use_declaration) @use)")
except ImportError:  # pragma: no cover - the grammar is a core dependency
    _PARSER = None

_STD_CRATES = frozenset({"std", "core", "alloc"})

# Names the std prelude puts in every module's scope (Rust 2021 prelude, the
# types and traits a call path can start with). A path starting with one of
# them, and not shadowed by a local item or import, is a std call.
_STD_PRELUDE = frozenset(
    {
        "Box", "String", "Vec", "Option", "Some", "None", "Result", "Ok", "Err",
        "ToString", "ToOwned", "Default", "Clone", "Copy", "Send", "Sync",
        "Sized", "Drop", "Fn", "FnMut", "FnOnce", "From", "Into", "TryFrom",
        "TryInto", "AsRef", "AsMut", "Iterator", "IntoIterator", "Extend",
        "FromIterator", "DoubleEndedIterator", "ExactSizeIterator",
        "PartialEq", "Eq", "PartialOrd", "Ord", "drop",
    }
)  # fmt: skip

_DEP_TABLES = ("dependencies", "dev-dependencies", "build-dependencies")
_ITEM_NODES = frozenset(
    {
        "function_item", "struct_item", "enum_item", "union_item", "trait_item",
        "const_item", "static_item", "type_item", "function_signature_item",
    }
)  # fmt: skip
_MAX_DEPTH = 8  # import/re-export hops before a path is given up as unknown

Segs = tuple[str, ...]


@dataclass(frozen=True)
class Span:
    """Lines of one file where a module's own items live.

    ``holes`` are the line ranges of inline child modules inside the span,
    whose items belong to the child, not to this module.
    """

    file: Path
    start: int
    end: int
    holes: tuple[tuple[int, int], ...] = ()


@dataclass(frozen=True)
class Resolution:
    """Where a call path points.

    For ``internal``, ``crate``/``module`` name the target module, ``item`` the
    first path segment after it (a function or a type), and ``rest`` whatever
    follows the item (``("new",)`` for ``Mixer::new``). For ``external``,
    ``crate`` is the outside crate's name as written in the code.
    """

    kind: Literal["internal", "external", "unknown"]
    crate: str | None = None
    module: Segs = ()
    item: str | None = None
    rest: Segs = ()
    unit: str | None = field(default=None, compare=False)


UNKNOWN = Resolution("unknown")


@dataclass(eq=False)
class _Module:
    unit: _Unit
    path: Segs
    file: Path
    spans: list[Span]
    child_dir: Path
    parent: _Module | None
    children: dict[str, _Module] = field(default_factory=dict)
    items: set[str] = field(default_factory=set)
    imports: dict[str, Segs] = field(default_factory=dict)
    aliases: dict[str, Segs] = field(default_factory=dict)
    globs: list[Segs] = field(default_factory=list)
    # Names imported twice from different paths (``#[cfg]`` twins): undecidable.
    conflicts: set[str] = field(default_factory=set)


@dataclass(eq=False)
class _Unit:
    key: str
    crate: str
    package: _Package
    root_file: Path
    is_lib: bool
    root: _Module | None = None
    files: set[Path] = field(default_factory=set)
    built: bool = False


@dataclass(eq=False)
class _Package:
    manifest: Path
    name: str
    workspace: _Workspace
    units: list[_Unit] = field(default_factory=list)
    internal_deps: dict[str, str] = field(default_factory=dict)  # ident -> package name
    external_deps: set[str] = field(default_factory=set)
    built: bool = False

    @property
    def lib(self) -> _Unit | None:
        return next((u for u in self.units if u.is_lib), None)


@dataclass(eq=False)
class _Workspace:
    root: Path
    packages: dict[str, _Package] = field(default_factory=dict)  # by package name


def _ident(name: str) -> str:
    return name.replace("-", "_")


def _read_toml(path: Path) -> dict[str, Any] | None:
    try:
        return tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError) as exc:
        logger.debug("[RUST_USE] unreadable manifest %s: %s", path, exc)
        return None


def _segs(text: str) -> Segs:
    return tuple(part.strip() for part in text.split("::"))


def _norm(path: Path) -> Path:
    """Resolve ``..`` without touching the filesystem's case or links."""
    return Path(*_collapse(path.parts)) if path.parts else path


def _collapse(parts: tuple[str, ...]) -> list[str]:
    out: list[str] = []
    for part in parts:
        if part == ".." and out and out[-1] not in ("..",) and len(out) > 1:
            out.pop()
        elif part != ".":
            out.append(part)
    return out


class RustModuleIndex:
    """Lazily built Cargo workspace / module / scope tables for Rust files."""

    def __init__(self) -> None:
        self._workspaces: dict[Path, _Workspace] = {}
        self._package_by_manifest: dict[Path, _Package] = {}
        self._package_by_dir: dict[Path, _Package | None] = {}
        self._package_by_file: dict[Path, _Package | None] = {}
        self._file_mounts: dict[Path, list[_Module]] = {}
        self._parsed: dict[Path, tuple[Any, bytes] | None] = {}
        self._units: dict[str, _Unit] = {}
        self._file_blocks: dict[Path, list[tuple[int, int, dict[str, Segs]]]] = {}
        self._norm_cache: dict[str, Path] = {}
        self.files_parsed = 0

    # ------------------------------------------------------------------ API

    def resolve(
        self, caller_file: str | Path, line: int, segments: list[str] | Segs
    ) -> Resolution:
        """Resolve a call path written at ``caller_file:line``.

        Args:
            caller_file: Absolute path of the file holding the call.
            line: 1-based file line of the call.
            segments: The call path split on ``::`` (``["Mixer", "new"]``);
                generic arguments already stripped by the caller.

        Returns:
            The :class:`Resolution`; :data:`UNKNOWN` when the file belongs to
            no crate or the path cannot be decided.
        """
        segs = tuple(s for s in segments if s is not None)
        if not segs or _PARSER is None:
            return UNKNOWN
        modules = self._modules_at(self.normalize(caller_file), line)
        if not modules:
            return UNKNOWN
        results = [self._resolve_path(m, segs, line, 0) for m in modules]
        first = results[0]
        if len(results) == 1:
            return first
        # A file mounted by several targets agrees only if every mount points
        # at the same code: same module files for internal, same crate for
        # external (crate::util can be a different file in each target).
        keys = {self._agreement_key(r) for r in results}
        return first if len(keys) == 1 else UNKNOWN

    def _agreement_key(self, r: Resolution) -> tuple[Any, ...]:
        if r.kind == "internal":
            return (r.kind, r.module, r.item, r.rest, tuple(self.module_spans(r)))
        return (r.kind, r.crate, r.module, r.item, r.rest)

    def normalize(self, path: str | Path) -> Path:
        """The path form :class:`Span` and the file sets use (cached)."""
        key = str(path)
        file = self._norm_cache.get(key)
        if file is None:
            file = self._norm_cache[key] = _norm(Path(path))
        return file

    def module_spans(self, resolution: Resolution) -> list[Span]:
        """Line spans where the target module of an internal resolution lives."""
        module = self._module_of(resolution)
        return list(module.spans) if module is not None else []

    def crate_files(self, resolution: Resolution) -> frozenset[Path]:
        """Files of the crate (target) an internal resolution points into."""
        unit = self._units.get(resolution.unit or "")
        return frozenset(unit.files) if unit is not None else frozenset()

    def impl_crate_files(self, resolution: Resolution) -> frozenset[Path]:
        """Files that may hold an ``impl`` for a type in the resolved crate.

        Rust's orphan rule allows inherent impls only in the type's crate, but
        trait impls also in crates that depend on it: the resolved crate, the
        other targets of its package, and every workspace package that
        depends on its package.
        """
        unit = self._units.get(resolution.unit or "")
        if unit is None:
            return frozenset()
        package = unit.package
        files: set[Path] = set()
        for pkg in package.workspace.packages.values():
            if pkg is package or package.name in pkg.internal_deps.values():
                for other in pkg.units:
                    self._build_unit(other)
                    files |= other.files
        return frozenset(files)

    # ------------------------------------------------------------ resolving

    def _resolve_path(
        self,
        mod: _Module,
        segs: Segs,
        line: int | None,
        depth: int,
        skip: str | None = None,
    ) -> Resolution:
        """Resolve ``segs`` from the scope of ``mod``.

        ``skip`` is the name of the import being resolved: ``use x::x;`` reads
        its first ``x`` from the child modules and the extern crates, never
        from the import itself.
        """
        if depth > _MAX_DEPTH or not segs:
            return UNKNOWN
        head, rest = segs[0], segs[1:]
        if head == "crate":
            root = mod.unit.root
            return self._walk(root, rest, depth) if root is not None else UNKNOWN
        if head == "self":
            return self._walk(mod, rest, depth)
        if head == "super":
            cur: _Module | None = mod.parent
            while rest and rest[0] == "super" and cur is not None:
                cur, rest = cur.parent, rest[1:]
            return self._walk(cur, rest, depth) if cur is not None else UNKNOWN
        if head == "":
            return self._extern(mod, rest, depth) if rest else UNKNOWN
        if head == "Self":
            return UNKNOWN

        hit = self._lookup(mod, head, line, depth, skip=skip, final=not rest)
        if hit is not None:
            kind, value = hit
            if kind == "unknown":
                return UNKNOWN
            if kind == "module":
                return self._walk(value, rest, depth)
            if kind == "item":
                return self._internal(value, head, rest)
            ctx, target = value
            own = kind == "import" and target[:1] == (head,)
            return self._resolve_path(
                ctx, target + rest, None, depth + 1, skip=head if own else None
            )
        return self._extern(mod, segs, depth)

    def _extern(self, mod: _Module, segs: Segs, depth: int) -> Resolution:
        head, rest = segs[0], segs[1:]
        package = mod.unit.package
        lib_unit: _Unit | None = None
        own_lib = package.lib
        if own_lib is not None and own_lib is not mod.unit and own_lib.crate == head:
            lib_unit = own_lib
        elif head in package.internal_deps:
            dep = package.workspace.packages.get(package.internal_deps[head])
            lib_unit = dep.lib if dep is not None else None
            if lib_unit is None:
                return UNKNOWN
        elif head in package.external_deps or head in _STD_CRATES:
            # Checked after the project crates: a dependency named `core` is
            # the project crate, not the sysroot one.
            return Resolution("external", crate=head)
        elif head in _STD_PRELUDE:
            return Resolution("external", crate="std")
        if lib_unit is None:
            return UNKNOWN
        self._build_unit(lib_unit)
        if lib_unit.root is None:
            return UNKNOWN
        return self._walk(lib_unit.root, rest, depth)

    def _walk(self, cur: _Module, rest: Segs, depth: int) -> Resolution:
        while rest:
            seg = rest[0]
            if seg in cur.conflicts:
                return UNKNOWN
            target = cur.aliases.get(seg) or cur.imports.get(seg)
            # A module and a function can share a name (`mod x; pub use x::x;`):
            # the last segment of a call names the function.
            last_is_value = len(rest) == 1 and (target is not None or seg in cur.items)
            if seg in cur.children and not last_is_value:
                cur, rest = cur.children[seg], rest[1:]
                continue
            if target is not None:
                own = target[:1] == (seg,)
                return self._resolve_path(
                    cur, target + rest[1:], None, depth + 1, skip=seg if own else None
                )
            if seg not in cur.items:
                via_glob = self._glob_hit(cur, seg, depth)
                if via_glob is not None:
                    return self._resolve_path(via_glob, rest, None, depth + 1)
            return self._internal(cur, seg, rest[1:])
        return UNKNOWN  # the path names a module, not something callable

    def _lookup(
        self,
        mod: _Module,
        name: str,
        line: int | None,
        depth: int,
        *,
        skip: str | None = None,
        final: bool = False,
    ) -> tuple[str, Any] | None:
        """Find ``name`` in the scope of ``mod``, by Rust precedence.

        Returns ``("module", m)``, ``("item", m)``, ``("import", (ctx, segs))``
        for an import of ``mod`` itself, ``("path", (ctx, segs))`` for a name a
        glob supplies, or ``("unknown", None)`` for a name imported twice from
        different paths; ``None`` when only the extern or std prelude could
        still supply it. ``skip`` hides one import name (see
        :meth:`_resolve_path`). ``final`` means ``name`` is the last segment
        of a call, so a function wins over a module of the same name.
        """
        if line is not None:
            scoped = [
                b
                for b in self._file_blocks.get(mod.file, ())
                if b[0] <= line <= b[1] and name in b[2]
            ]
            if scoped:
                innermost = min(scoped, key=lambda b: b[1] - b[0])
                return "import", (mod, innermost[2][name])
        if name != skip:
            if name in mod.conflicts:
                return "unknown", None
            if name in mod.aliases:
                return "import", (mod, mod.aliases[name])
            if name in mod.imports:
                return "import", (mod, mod.imports[name])
        if final and name in mod.items:
            return "item", mod
        if name in mod.children:
            return "module", mod.children[name]
        if name in mod.items:
            return "item", mod
        holder = self._glob_hit(mod, name, depth)
        if holder is not None:
            return "path", (holder, (name,))
        return None

    def _glob_hit(self, mod: _Module, name: str, depth: int) -> _Module | None:
        """The internal module a glob import of ``mod`` supplies ``name`` from."""
        seen: set[int] = {id(mod)}
        frontier = [mod]
        while frontier and depth <= _MAX_DEPTH:
            depth += 1
            nxt: list[_Module] = []
            for cur in frontier:
                for glob in cur.globs:
                    target = self._module_for_path(cur, glob, depth)
                    if target is None or id(target) in seen:
                        continue
                    seen.add(id(target))
                    if (
                        name in target.items
                        or name in target.children
                        or name in target.imports
                        or name in target.aliases
                    ):
                        return target
                    nxt.append(target)  # a glob re-exporting another glob
            frontier = nxt
        return None

    def _module_for_path(self, mod: _Module, segs: Segs, depth: int) -> _Module | None:
        """Resolve a glob's path to a project module (None if external/unknown)."""
        if depth > _MAX_DEPTH or not segs:
            return None
        head, rest = segs[0], segs[1:]
        cur: _Module | None
        if head == "crate":
            cur = mod.unit.root
        elif head == "self":
            cur = mod
        elif head == "super":
            cur = mod.parent
            while rest and rest[0] == "super" and cur is not None:
                cur, rest = cur.parent, rest[1:]
        elif head in mod.children:
            cur = mod.children[head]
        elif head in mod.imports:
            return self._module_for_path(mod, mod.imports[head] + rest, depth + 1)
        else:
            package = mod.unit.package
            unit: _Unit | None = None
            own_lib = package.lib
            if (
                own_lib is not None
                and own_lib is not mod.unit
                and own_lib.crate == head
            ):
                unit = own_lib
            elif head in package.internal_deps:
                dep = package.workspace.packages.get(package.internal_deps[head])
                unit = dep.lib if dep is not None else None
            if unit is None:
                return None
            self._build_unit(unit)
            cur = unit.root
        for seg in rest:
            if cur is None:
                return None
            if seg in cur.children:
                cur = cur.children[seg]
            elif seg in cur.imports:
                return self._module_for_path(cur, cur.imports[seg], depth + 1)
            else:
                return None
        return cur

    @staticmethod
    def _internal(mod: _Module, item: str, rest: Segs) -> Resolution:
        return Resolution(
            "internal",
            crate=mod.unit.crate,
            module=mod.path,
            item=item,
            rest=tuple(rest),
            unit=mod.unit.key,
        )

    def _module_of(self, resolution: Resolution) -> _Module | None:
        unit = self._units.get(resolution.unit or "")
        if unit is None or unit.root is None:
            return None
        cur = unit.root
        for seg in resolution.module:
            nxt = cur.children.get(seg)
            if nxt is None:
                return None
            cur = nxt
        return cur

    # ---------------------------------------------------- caller's module

    def _modules_at(self, file: Path, line: int) -> list[_Module]:
        package = self._package_for(file)
        if package is None:
            return []
        if not package.built:
            for unit in package.units:
                self._build_unit(unit)
            package.built = True
        found: list[_Module] = []
        for mount in self._file_mounts.get(file, []):
            cur = mount
            descended = True
            while descended:
                descended = False
                for child in cur.children.values():
                    # Inline children share the mount's Path object; file-loaded
                    # children never contain the caller's line in this file.
                    if child.file is mount.file and any(
                        s.start <= line <= s.end for s in child.spans
                    ):
                        cur, descended = child, True
                        break
            found.append(cur)
        return found

    # ------------------------------------------------------- cargo layout

    def _package_for(self, file: Path) -> _Package | None:
        if file in self._package_by_file:
            return self._package_by_file[file]
        package = self._package_for_dir(file.parent)
        self._package_by_file[file] = package
        return package

    def _package_for_dir(self, directory: Path) -> _Package | None:
        if directory not in self._package_by_dir:
            self._package_by_dir[directory] = self._find_package(directory)
        return self._package_by_dir[directory]

    def _find_package(self, directory: Path) -> _Package | None:
        manifest = None
        for parent in (directory, *directory.parents):
            if parent in self._package_by_dir:
                cached = self._package_by_dir[parent]
                return cached  # every directory below was already checked
            candidate = parent / "Cargo.toml"
            if candidate.is_file():
                data = _read_toml(candidate)
                if data is not None and "package" in data:
                    manifest = candidate
                    break
        if manifest is None:
            return None
        if manifest in self._package_by_manifest:
            return self._package_by_manifest[manifest]
        workspace = self._workspace_for(manifest)
        package = self._package_by_manifest.get(manifest)
        if package is None:  # not listed as a member: index it on its own
            package = self._load_package(manifest, workspace)
            if package is not None:
                # Not a member, so no `workspace = true` inheritance; path
                # dependencies can still point at members.
                member_dirs = {
                    p.manifest.parent: p.name for p in workspace.packages.values()
                }
                self._load_deps(manifest, workspace, member_dirs, {})
        return package

    def _workspace_for(self, manifest: Path) -> _Workspace:
        root_manifest = manifest
        own = _read_toml(manifest) or {}
        # A package that declares its own [workspace] is that workspace root,
        # even below another workspace (vendored crates, samples).
        parents = () if "workspace" in own else manifest.parent.parents
        for parent in parents:
            candidate = parent / "Cargo.toml"
            if candidate.is_file():
                data = _read_toml(candidate)
                if data is not None and "workspace" in data:
                    root_manifest = candidate
                    break
        root = root_manifest.parent
        if root in self._workspaces:
            return self._workspaces[root]
        workspace = _Workspace(root=root)
        self._workspaces[root] = workspace
        data = _read_toml(root_manifest) or {}
        ws_table = data.get("workspace", {})
        members: set[Path] = set()
        for pattern in ws_table.get("members", []):
            for match in root.glob(pattern):
                if (match / "Cargo.toml").is_file():
                    members.add(_norm(match / "Cargo.toml"))
        excluded = {_norm(root / p / "Cargo.toml") for p in ws_table.get("exclude", [])}
        if "package" in data:
            members.add(root_manifest)
        members.add(manifest)
        for member in sorted(members - excluded):
            self._load_package(member, workspace)
        member_dirs = {p.manifest.parent: p.name for p in workspace.packages.values()}
        for member in sorted(members - excluded):
            self._load_deps(
                member, workspace, member_dirs, ws_table.get("dependencies", {})
            )
        return workspace

    def _load_package(self, manifest: Path, workspace: _Workspace) -> _Package | None:
        if manifest in self._package_by_manifest:
            return self._package_by_manifest[manifest]
        data = _read_toml(manifest)
        if data is None or "package" not in data:
            return None
        name = str(data["package"].get("name", manifest.parent.name))
        package = _Package(manifest=manifest, name=name, workspace=workspace)
        workspace.packages[name] = package
        self._package_by_manifest[manifest] = package
        self._add_units(package, data)
        return package

    def _load_deps(
        self,
        manifest: Path,
        workspace: _Workspace,
        member_dirs: dict[Path, str],
        ws_deps: dict[str, Any],
    ) -> None:
        package = self._package_by_manifest.get(manifest)
        data = _read_toml(manifest)
        if package is None or data is None:
            return
        tables: list[dict[str, Any]] = [data.get(t, {}) for t in _DEP_TABLES]
        for target in data.get("target", {}).values():
            tables.extend(target.get(t, {}) for t in _DEP_TABLES)
        for table in tables:
            for key, spec in table.items():
                ident = _ident(key)
                real = key
                path: Path | None = None
                if isinstance(spec, dict):
                    if spec.get("workspace"):
                        ws_spec = ws_deps.get(key, {})
                        if isinstance(ws_spec, dict):
                            real = ws_spec.get("package", real)
                            if "path" in ws_spec:
                                path = _norm(workspace.root / ws_spec["path"])
                    real = spec.get("package", real)
                    if "path" in spec:
                        path = _norm(manifest.parent / spec["path"])
                member = member_dirs.get(path) if path is not None else None
                if member is None and path is None and real in workspace.packages:
                    member = real
                if member is not None:
                    package.internal_deps[ident] = member
                else:
                    package.external_deps.add(ident)

    def _add_units(self, package: _Package, data: dict[str, Any]) -> None:
        base = package.manifest.parent
        seen: set[Path] = set()

        def add(kind: str, name: str, root: Path, is_lib: bool = False) -> None:
            root = _norm(root)
            if root in seen or not root.is_file():
                return
            seen.add(root)
            key = f"{package.manifest}::{kind}:{name}"
            unit = _Unit(
                key=key,
                crate=_ident(name),
                package=package,
                root_file=root,
                is_lib=is_lib,
            )
            package.units.append(unit)
            self._units[key] = unit

        lib = data.get("lib", {})
        add(
            "lib",
            lib.get("name", package.name),
            base / lib.get("path", "src/lib.rs"),
            is_lib=True,
        )
        for kind, table, auto_dir in (
            ("bin", "bin", "src/bin"),
            ("test", "test", "tests"),
            ("example", "example", "examples"),
            ("bench", "bench", "benches"),
        ):
            for entry in data.get(table, []):
                name = entry.get("name", package.name)
                default = (
                    "src/main.rs"
                    if kind == "bin" and name == package.name
                    else f"{auto_dir}/{name}.rs"
                )
                add(kind, name, base / entry.get("path", default))
            if kind == "bin":
                add(kind, package.name, base / "src/main.rs")
            auto = base / auto_dir
            if auto.is_dir():
                for path in sorted(auto.glob("*.rs")):
                    add(kind, path.stem, path)
                for path in sorted(auto.glob("*/main.rs")):
                    add(kind, path.parent.name, path)
        build = data["package"].get("build", "build.rs")
        if isinstance(build, str):
            add("build", "build_script_build", base / build)

    # -------------------------------------------------------- module tree

    def _build_unit(self, unit: _Unit) -> None:
        if unit.built:
            return
        unit.built = True
        root = self._load_file_module(
            unit, (), unit.root_file, None, mod_rs=True, stack=set()
        )
        unit.root = root

    def _parse(self, file: Path) -> tuple[Any, bytes] | None:
        if file not in self._parsed:
            try:
                src = file.read_bytes()
            except OSError:
                self._parsed[file] = None
            else:
                assert _PARSER is not None
                tree = _PARSER.parse(src)
                self._parsed[file] = (tree, src)
                self._file_blocks[file] = self._block_imports(tree, src)
                self.files_parsed += 1
        return self._parsed[file]

    def _load_file_module(
        self,
        unit: _Unit,
        path: Segs,
        file: Path,
        parent: _Module | None,
        *,
        mod_rs: bool,
        stack: set[Path],
    ) -> _Module | None:
        if file in stack:
            return None
        parsed = self._parse(file)
        if parsed is None:
            return None
        tree, src = parsed
        root_node = tree.root_node
        child_dir = file.parent if mod_rs else file.parent / file.stem
        module = _Module(
            unit=unit,
            path=path,
            file=file,
            spans=[],
            child_dir=child_dir,
            parent=parent,
        )
        unit.files.add(file)
        self._file_mounts.setdefault(file, []).append(module)
        holes = self._fill(
            module, root_node, src, file_level=True, stack=stack | {file}
        )
        module.spans.append(Span(file, 1, root_node.end_point[0] + 1, tuple(holes)))
        return module

    def _fill(
        self,
        module: _Module,
        container: Any,
        src: bytes,
        *,
        file_level: bool,
        stack: set[Path],
    ) -> list[tuple[int, int]]:
        """Read one module body: items, imports, child modules. Returns holes."""
        holes: list[tuple[int, int]] = []
        pending_path: str | None = None
        for node in container.named_children:
            kind = node.type
            if kind == "attribute_item":
                pending_path = _path_attribute(node, src) or pending_path
                continue
            if kind in ("line_comment", "block_comment"):
                continue  # a comment between `#[path]` and `mod x;` keeps the path
            if kind == "mod_item":
                self._child_module(
                    module, node, src, pending_path, file_level, stack, holes
                )
            elif kind == "use_declaration":
                argument = node.child_by_field_name("argument")
                if argument is not None:
                    found: dict[str, Segs] = {}
                    _flatten_use(argument, src, (), found, module.globs)
                    for name, target in found.items():
                        previous = module.imports.get(name)
                        if previous is not None and previous != target:
                            module.conflicts.add(name)
                        module.imports[name] = target
            elif kind in _ITEM_NODES:
                name_node = node.child_by_field_name("name")
                if name_node is not None:
                    module.items.add(_text(name_node, src))
                if kind == "type_item":
                    target = _type_path(node.child_by_field_name("type"), src)
                    if target and name_node is not None:
                        module.aliases[_text(name_node, src)] = target
            elif kind == "foreign_mod_item":
                for sig in _descendants(node, "function_signature_item"):
                    name_node = sig.child_by_field_name("name")
                    if name_node is not None:
                        module.items.add(_text(name_node, src))
            pending_path = None
        return holes

    def _child_module(
        self,
        module: _Module,
        node: Any,
        src: bytes,
        path_attr: str | None,
        file_level: bool,
        stack: set[Path],
        holes: list[tuple[int, int]],
    ) -> None:
        name_node = node.child_by_field_name("name")
        if name_node is None:
            return
        name = _text(name_node, src)
        body = node.child_by_field_name("body")
        unit = module.unit
        if body is not None:  # inline `mod name { ... }`
            start, end = node.start_point[0] + 1, node.end_point[0] + 1
            holes.append((start, end))
            child = _Module(
                unit=unit,
                path=module.path + (name,),
                file=module.file,
                spans=[],
                child_dir=module.child_dir / name,
                parent=module,
            )
            module.children[name] = child
            inner_holes = self._fill(child, body, src, file_level=False, stack=stack)
            child.spans.append(Span(module.file, start, end, tuple(inner_holes)))
            return
        if path_attr is not None:
            base = module.file.parent if file_level else module.child_dir
            target = _norm(base / path_attr)
            mod_rs = (
                True  # files loaded through #[path] place children like mod.rs files
            )
        else:
            target = _norm(module.child_dir / f"{name}.rs")
            mod_rs = False
            if not target.is_file():
                target = _norm(module.child_dir / name / "mod.rs")
                mod_rs = True
        if not target.is_file():
            return
        child = self._load_file_module(
            unit, module.path + (name,), target, module, mod_rs=mod_rs, stack=stack
        )
        if child is not None:
            module.children[name] = child

    @staticmethod
    def _block_imports(tree: Any, src: bytes) -> list[tuple[int, int, dict[str, Segs]]]:
        """`use` declarations inside blocks, with the block's line range.

        Keyed by file, not module: a block's lines sit inside exactly one
        innermost module, which is the module :meth:`resolve` starts from.
        """
        blocks: list[tuple[int, int, dict[str, Segs]]] = []
        for use in QueryCursor(_BLOCK_USE).captures(tree.root_node).get("use", []):
            block = use.parent
            argument = use.child_by_field_name("argument")
            if block is None or argument is None:
                continue
            imports: dict[str, Segs] = {}
            _flatten_use(argument, src, (), imports, [])
            if imports:
                blocks.append(
                    (block.start_point[0] + 1, block.end_point[0] + 1, imports)
                )
        return blocks


# ---------------------------------------------------------------- helpers


def _text(node: Any, src: bytes) -> str:
    return src[node.start_byte : node.end_byte].decode("utf-8", "replace")


def _descendants(node: Any, kind: str, stop: set[str] | None = None) -> list[Any]:
    out: list[Any] = []
    stack = list(node.named_children)
    while stack:
        cur = stack.pop()
        if cur.type == kind:
            out.append(cur)
            continue
        if stop and cur.type in stop:
            continue
        stack.extend(cur.named_children)
    return out


def _path_attribute(node: Any, src: bytes) -> str | None:
    """`#[path = "x.rs"]` -> `x.rs`; None for any other attribute."""
    attribute = next((c for c in node.named_children if c.type == "attribute"), None)
    if attribute is None:
        return None
    ident = next((c for c in attribute.named_children if c.type == "identifier"), None)
    if ident is None or _text(ident, src) != "path":
        return None
    for lit in _descendants(attribute, "string_content"):
        return _text(lit, src)
    return None


def _type_path(node: Any, src: bytes) -> Segs | None:
    """`a::B<T>` -> ("a", "B"); None for primitives, references and tuples."""
    if node is None:
        return None
    if node.type == "generic_type":
        node = node.child_by_field_name("type")
        if node is None:
            return None
    if node.type in ("type_identifier", "scoped_type_identifier"):
        return _segs(_text(node, src))
    return None


def _flatten_use(
    node: Any, src: bytes, prefix: Segs, out: dict[str, Segs], globs: list[Segs]
) -> None:
    """Flatten one use tree into ``alias -> path`` and glob paths."""
    kind = node.type
    if kind in ("identifier", "scoped_identifier", "crate", "self", "super"):
        segs = prefix + _segs(_text(node, src))
        if segs and segs[-1] == "self":
            segs = segs[:-1]
        if segs and segs[-1] not in ("crate", "super", "self", ""):
            out[segs[-1]] = segs
    elif kind == "use_as_clause":
        path = node.child_by_field_name("path")
        alias = node.child_by_field_name("alias")
        if path is not None and alias is not None and _text(alias, src) != "_":
            segs = prefix + _segs(_text(path, src))
            if segs and segs[-1] == "self":
                segs = segs[:-1]
            out[_text(alias, src)] = segs
    elif kind == "scoped_use_list":
        path = node.child_by_field_name("path")
        listing = node.child_by_field_name("list")
        new_prefix = prefix + (_segs(_text(path, src)) if path is not None else ())
        if listing is not None:
            _flatten_use(listing, src, new_prefix, out, globs)
    elif kind == "use_list":
        for child in node.named_children:
            _flatten_use(child, src, prefix, out, globs)
    elif kind == "use_wildcard":
        inner = next(iter(node.named_children), None)
        globs.append(prefix + (_segs(_text(inner, src)) if inner is not None else ()))
