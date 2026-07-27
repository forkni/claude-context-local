# Centrality memo invalidation: version counter, not node/edge counts

Status: accepted
Date: 2026-07-27

## Context

`CentralityRanker.__init__` already held a cache — `self._cache`, keyed on
`self._cache_key = (node_count, edge_count)` — but it never hit. `search/
graph_scoring_stage.py` constructs a fresh `GraphQueryEngine` +
`CentralityRanker` on every query, so the instance-level cache was born empty
every time; PageRank (`nx.pagerank` plus its `nx.DiGraph(...)` parity copy)
was recomputed on every single query regardless, at a measured 53.4ms on this
repo and 71.1ms on a larger project (search-latency plan, Fix 3).

Fixing the "never hits" defect requires moving the cache to a long-lived
object — `CodeGraphStorage`, one instance per project, alive across every
search. That immediately raises the second defect the existing key already
had, now consequential instead of moot: node/edge counts are unsound as a
cache key on anything long-lived. Two mutation patterns defeat it silently:

- **Equal-count churn.** `remove_file_nodes` followed by re-adding the same
  file (a body-only edit during incremental reindex) removes and re-adds the
  same number of nodes and edges. Node/edge counts end up identical to the
  pre-edit graph, but the topology — and therefore centrality — can differ.
- **Attribute-only mutation.** `upgrade_call_edge` changes edge attributes
  (`resolver_source`, `resolver_confidence`, `is_resolved`, `line`, and
  anything else a future caller passes via `**attrs`) in place via
  `self.graph.edges[...].update(attrs)` — zero node/edge count delta, by
  construction. A counts-based key cannot see this mutation at all.

## Decision

Move the memo onto `CodeGraphStorage` and key it on a monotonic version
counter instead of counts: `_centrality_cache: dict[str, tuple[int,
dict[str, float]]]` mapping `method -> (version_at_computation, scores)`.
`_bump_version()` is called by every one of the 8 methods that mutate
`self.graph`: construction, `add_node`, `add_call_edge`, `upgrade_call_edge`,
`add_relationship_edge`, `load`, `clear`, `remove_file_nodes` — an explicit,
manually-maintained list rather than something structurally guaranteed by
the type (see Considered Options).

Because that list is manual, it is enforced two ways, not one:

- One test per known mutator (`test_graph_storage.py`) — catches a
  *regression* in a mutator that already bumps.
- An **AST completeness test**
  (`tests/unit/graph/test_graph_storage_version.py`) that parses
  `graph_storage.py` itself, finds every method whose body touches
  `self.graph` (assignment, or a call to a known graph-mutating method, or
  the in-place `self.graph.edges[...].update(...)` pattern), and asserts each
  one also calls `_bump_version()`. Only this test can catch a 9th mutator
  someone adds later and forgets to wire up — the actual risk this design
  introduces, and the one the per-mutator tests are structurally blind to.

**Atomicity.** The counter advances via `next()` on an `itertools.count()`,
not a plain `+= 1`. `next()` on `itertools.count()` is a single bytecode-level
operation, atomic in CPython; a plain increment could lose an update under
concurrent bumps, letting two *distinct* graph states share a version
number — the one way this cache could serve stale scores.

**Race safety without a lock.** The caller
(`CentralityRanker.get_centrality_scores`) captures `storage.version` *before*
computing, and stores the result under that captured value, not the version
at storage time. If a mutation lands mid-computation, `storage.version` has
already advanced past the captured value, so the entry is filed under a
version number that can never be current again — the next read misses and
recomputes. Worst case is one duplicated computation; never a stale read.

**Always returns a copy.** `get_cached_centrality` returns `dict(scores)`,
never the cached dict itself. `CentralityRanker.get_centrality_scores` hands
its return value onward into shared, long-lived state
(`ego_graph_retriever.set_centrality_scores`), and the existing comment at
`graph_scoring_stage.py` declares that downstream race benign specifically
*because* every query injects its own dict object. A shared cache without the
copy would silently invalidate that reasoning by making every query alias the
same object. The copy costs ~1ms against the 53-71ms a cache hit saves.

## Considered Options

- **Keep node/edge counts as the key, just move the cache** — rejected per
  Context above: misses equal-count churn and is blind to attribute-only
  mutation entirely.
- **A `MultiDiGraph` subclass overriding `add_*`/`remove_*`** — rejected.
  This looks structural (every add/remove call site is automatically
  covered, no manual list to maintain) but is blind to exactly the trickiest
  mutator: `upgrade_call_edge` doesn't call `add_edge` or `remove_edge` at
  all — it mutates an existing edge's attribute dict in place. A subclass
  override on the add/remove methods would silently miss it, the same class
  of bug this design is meant to eliminate, just moved one level down.
- **Plain integer increment instead of `itertools.count()`** — rejected for
  the atomicity reason given above.

## Consequences

- Every future method that mutates `self.graph` must remember to call
  `self._bump_version()`. This is the one manual-maintenance surface the
  design introduces, and it is closed by the AST completeness test rather
  than left to code review discipline.
- `CentralityRanker` instances are still constructed fresh per query
  (`graph_scoring_stage.py` is unchanged in this respect) — that's now
  harmless rather than wasteful, because the actual memo lives on the
  long-lived `CodeGraphStorage` object each fresh ranker reads through, not
  on the short-lived ranker itself.
- A concurrent reindex mutating the graph mid-search-assembly can still race
  a read of `storage.version` / `_centrality_cache` on the event loop; this
  ADR only makes the memo itself correct under that race (worst case: a
  miss, never a stale hit). The read/write ordering guarantee — that
  `_assemble` cannot observe a graph mid-rewrite — is the reindex read lock,
  covered separately (ADR-0008's 2026-07-27 amendment).
