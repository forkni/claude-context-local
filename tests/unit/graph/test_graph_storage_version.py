"""
AST completeness guard for CodeGraphStorage's version-bump invariant.

P3-3 (search-latency plan): every method on CodeGraphStorage that mutates
``self.graph`` must also call ``self._bump_version()``, or the storage-level
centrality memo (CentralityRanker.get_centrality_scores via
get_cached_centrality/set_cached_centrality) can serve stale scores after a
mutation.

test_graph_storage.py has one test per known mutator (add_node, add_call_edge,
upgrade_call_edge, add_relationship_edge, load, clear, remove_file_nodes, plus
construction). Those tests only catch a *regression* in a mutator that already
exists and already calls _bump_version() — they cannot catch a 9th mutator
added later that forgets to call it. This test parses the source of
graph_storage.py itself, finds every method on CodeGraphStorage whose body
assigns to ``self.graph`` or calls a known graph-mutating method on it
(``add_node``, ``add_edge``, ``remove_node``, ``clear``, the in-place
``self.graph.edges[...].update(...)`` pattern used by upgrade_call_edge, etc.),
and asserts each one also calls ``self._bump_version()`` somewhere in its body.
"""

import ast
import inspect

import graph.graph_storage as graph_storage_module


_MUTATING_GRAPH_METHODS = {
    "add_node",
    "add_edge",
    "add_nodes_from",
    "add_edges_from",
    "remove_node",
    "remove_edge",
    "remove_nodes_from",
    "remove_edges_from",
    "clear",
    "update",
}

# Methods allowed to touch self.graph without bumping — the bump primitive
# itself, and read-only accessors misidentified by the heuristic (none known
# today; kept as an explicit, reviewable escape hatch rather than a silent one).
_EXEMPT_METHODS: set[str] = {"_bump_version"}


def _is_self_graph_attr(node: ast.AST) -> bool:
    """True for the AST node `self.graph`."""
    return (
        isinstance(node, ast.Attribute)
        and node.attr == "graph"
        and isinstance(node.value, ast.Name)
        and node.value.id == "self"
    )


def _is_self_graph_subscript(node: ast.AST) -> bool:
    """True for `self.graph.edges[...]` / `self.graph.nodes[...]` (in-place update target)."""
    return (
        isinstance(node, ast.Subscript)
        and isinstance(node.value, ast.Attribute)
        and node.value.attr in ("edges", "nodes")
        and _is_self_graph_attr(node.value.value)
    )


def _touches_self_graph(func: ast.FunctionDef) -> bool:
    """True if *func*'s body assigns to self.graph or mutates it in place."""
    for child in ast.walk(func):
        if isinstance(child, ast.Assign) and any(
            _is_self_graph_attr(target) for target in child.targets
        ):
            return True
        if isinstance(child, ast.Call) and isinstance(child.func, ast.Attribute):
            method_name = child.func.attr
            owner = child.func.value
            if method_name not in _MUTATING_GRAPH_METHODS:
                continue
            if _is_self_graph_attr(owner) or _is_self_graph_subscript(owner):
                return True
    return False


def _calls_bump_version(func: ast.FunctionDef) -> bool:
    for child in ast.walk(func):
        if (
            isinstance(child, ast.Call)
            and isinstance(child.func, ast.Attribute)
            and child.func.attr == "_bump_version"
        ):
            return True
    return False


def test_every_graph_mutating_method_calls_bump_version():
    source = inspect.getsource(graph_storage_module)
    tree = ast.parse(source)

    class_node = next(
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.ClassDef) and node.name == "CodeGraphStorage"
    )

    offenders = [
        item.name
        for item in class_node.body
        if isinstance(item, ast.FunctionDef)
        and item.name not in _EXEMPT_METHODS
        and _touches_self_graph(item)
        and not _calls_bump_version(item)
    ]

    assert offenders == [], (
        "Method(s) on CodeGraphStorage mutate self.graph without calling "
        f"self._bump_version(): {offenders}. Every mutator must bump the "
        "version counter so CentralityRanker's storage-level centrality memo "
        "(get_cached_centrality/set_cached_centrality) invalidates correctly "
        "— see _bump_version()'s docstring in graph/graph_storage.py."
    )


def test_heuristic_detects_known_mutators():
    """Sanity check on the AST heuristic itself: it must actually find the 8
    known mutators, not silently match zero methods and vacuously pass above."""
    source = inspect.getsource(graph_storage_module)
    tree = ast.parse(source)

    class_node = next(
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.ClassDef) and node.name == "CodeGraphStorage"
    )

    detected = {
        item.name
        for item in class_node.body
        if isinstance(item, ast.FunctionDef) and _touches_self_graph(item)
    }

    expected = {
        "__init__",
        "add_node",
        "add_call_edge",
        "upgrade_call_edge",
        "add_relationship_edge",
        "load",
        "clear",
        "remove_file_nodes",
    }
    assert expected <= detected, (
        f"AST heuristic failed to detect known mutator(s): {expected - detected}"
    )
