"""Shrink-only ratchet: scripts/benchmark/*.py must not re-grow the
hand-rolled bootstrap/loader duplication evaluation.probe_harness (Step 3,
docs/adr/0040-probe-harness-seam.md) exists to replace.

Two counts are pinned, mirroring the module docstring's own tally at the
time this test was written:

- BASELINE_SYS_PATH_BOOTSTRAP_COUNT: files still doing their own
  ``sys.path.insert(0, ...)`` instead of running as ``python -m
  scripts.benchmark.foo`` or importing ``evaluation.probe_harness``.
- BASELINE_LOCAL_LOAD_QUERIES_COUNT: files still defining their own
  ``load_queries``/``load_golden_queries`` instead of calling
  ``evaluation.probe_harness.load_golden_queries``.

Both baselines only ever move down, one probe at a time, as Step 5 migrates
each of the four beachhead probes (``probe_tm2c2_fusion.py``,
``probe_final_pool_reserve.py``, ``probe_leg_depth_fusion.py``,
``probe_stable_misses.py``) onto the harness -- see MIGRATED_PROBES below,
populated as each migration lands. ``probe_duplicate_crowding.py`` is
explicitly excluded from migration (untracked, actively-changing WIP; "two
hats" -- see the plan) and must never appear in MIGRATED_PROBES.
``probe_rerank_window.py`` is a third, out-of-scope instrumentation adapter
(``probe_leg_depth_fusion.py``'s ``fidelity_check`` depends on its own,
richer ``Instrumentation`` API) and also never migrates.

If this test goes red because you added a *new* script with its own
sys.path.insert or load_queries, fix the script (route it through
probe_harness) instead of raising the baseline -- that is the ratchet.
"""

from __future__ import annotations

import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
BENCHMARK_DIR = REPO_ROOT / "scripts" / "benchmark"

SYS_PATH_INSERT_RE = re.compile(r"^\s*sys\.path\.insert\(", re.MULTILINE)
LOAD_QUERIES_DEF_RE = re.compile(r"^def load_(queries|golden_queries)\(", re.MULTILINE)

BASELINE_SYS_PATH_BOOTSTRAP_COUNT = 23
BASELINE_LOCAL_LOAD_QUERIES_COUNT = 5

# Populated one filename at a time as Step 5 lands each migration.
# probe_duplicate_crowding.py and probe_rerank_window.py never join this set
# (see module docstring).
MIGRATED_PROBES: frozenset[str] = frozenset()

NEVER_MIGRATE = frozenset({"probe_duplicate_crowding.py", "probe_rerank_window.py"})


def _benchmark_scripts() -> list[Path]:
    scripts = sorted(BENCHMARK_DIR.glob("*.py"))
    assert scripts, f"no scripts found under {BENCHMARK_DIR} - path wrong?"
    return scripts


def _files_matching(pattern: re.Pattern) -> list[str]:
    return [
        script.name
        for script in _benchmark_scripts()
        if pattern.search(script.read_text(encoding="utf-8"))
    ]


def test_sys_path_bootstrap_count_does_not_exceed_baseline():
    offenders = _files_matching(SYS_PATH_INSERT_RE)
    assert len(offenders) <= BASELINE_SYS_PATH_BOOTSTRAP_COUNT, (
        f"{len(offenders)} scripts/benchmark/*.py files hand-roll "
        f"sys.path.insert, baseline is {BASELINE_SYS_PATH_BOOTSTRAP_COUNT}: "
        f"{sorted(offenders)}. Route new scripts through evaluation.probe_harness "
        "instead of adding a bootstrap."
    )


def test_local_load_queries_count_does_not_exceed_baseline():
    offenders = _files_matching(LOAD_QUERIES_DEF_RE)
    assert len(offenders) <= BASELINE_LOCAL_LOAD_QUERIES_COUNT, (
        f"{len(offenders)} scripts/benchmark/*.py files define their own "
        f"load_queries/load_golden_queries, baseline is "
        f"{BASELINE_LOCAL_LOAD_QUERIES_COUNT}: {sorted(offenders)}. Call "
        "evaluation.probe_harness.load_golden_queries instead of adding a "
        "new loader."
    )


def test_migrated_probes_have_no_sys_path_bootstrap():
    bootstrapped = set(_files_matching(SYS_PATH_INSERT_RE))
    for name in MIGRATED_PROBES:
        assert name not in bootstrapped, (
            f"{name} is listed in MIGRATED_PROBES but still has a "
            "sys.path.insert bootstrap"
        )


def test_migrated_probes_define_no_local_load_queries():
    local_loaders = set(_files_matching(LOAD_QUERIES_DEF_RE))
    for name in MIGRATED_PROBES:
        assert name not in local_loaders, (
            f"{name} is listed in MIGRATED_PROBES but still defines its own "
            "load_queries"
        )


def test_migrated_probes_import_probe_harness():
    for name in MIGRATED_PROBES:
        text = (BENCHMARK_DIR / name).read_text(encoding="utf-8")
        assert "probe_harness" in text, (
            f"{name} is listed in MIGRATED_PROBES but never references "
            "evaluation.probe_harness"
        )


def test_never_migrate_probes_are_not_claimed_as_migrated():
    """Guards the two-hats exclusion: probe_duplicate_crowding.py stays
    untracked WIP, probe_rerank_window.py stays an out-of-scope third
    instrumentation adapter -- neither may ever be marked migrated."""
    assert not (MIGRATED_PROBES & NEVER_MIGRATE)


def test_never_migrate_probes_still_exist():
    """If either file is deleted or renamed, the exclusion above is dead --
    this must go red so NEVER_MIGRATE gets updated deliberately, not
    silently stop meaning anything."""
    existing = {p.name for p in _benchmark_scripts()}
    for name in NEVER_MIGRATE:
        assert name in existing, f"{name} no longer exists under {BENCHMARK_DIR}"


def test_ratchet_bites_on_a_reintroduced_bootstrap(tmp_path):
    """Sanity-check the ratchet mechanism itself: point BENCHMARK_DIR-style
    scanning at a scratch dir seeded past the baseline, confirm it goes red.

    Mirrors this module's own scanning logic rather than importing it, since
    _files_matching is hardwired to the real BENCHMARK_DIR by design (a
    ratchet that could be redirected at an empty dir isn't a ratchet)."""
    scratch = tmp_path
    for i in range(BASELINE_SYS_PATH_BOOTSTRAP_COUNT + 1):
        (scratch / f"probe_{i}.py").write_text(
            "import sys\nsys.path.insert(0, '.')\n", encoding="utf-8"
        )
    offenders = [
        p.name
        for p in scratch.glob("*.py")
        if SYS_PATH_INSERT_RE.search(p.read_text(encoding="utf-8"))
    ]
    assert len(offenders) > BASELINE_SYS_PATH_BOOTSTRAP_COUNT
