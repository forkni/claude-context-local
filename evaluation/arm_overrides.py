"""One override seam for SSCG benchmark A/B arms (ADR-0018 Part 2 / C1).

Before this module, ``scripts/benchmark/run_sscg_benchmark.py`` carried eleven
near-identical ``_apply_*_override()`` functions, each doing the same four
things: guard on ``None``, import ``get_search_config``, assign one dotted
field, swallow into a ``[WARN]`` print. A new arm meant hand-writing a twin of
one of those functions. This module collapses that pattern into shared,
reusable, *validated* machinery, built entirely from what ``search/config.py``
already provides (ADR-0022's ``spec()`` metadata, ``_deep_merge``,
``validate_field_value``) rather than reimplementing any of it:

- :func:`normalize_overrides` — accept a flat dotted-key dict or a
  nested-by-section dict (or a mix) and return the flat dotted-key shape.
- :func:`merge_overrides` — fold N override dicts into one via ``_deep_merge``.
- :func:`validate_overrides` — reject an unknown field or an out-of-range/
  choices-violating value via ``validate_field_value``, raising
  :class:`ArmOverrideError` instead of the eleven originals' bare
  ``except Exception: print("[WARN] ...")`` swallow. A bad arm now fails
  before it burns a benchmark run, not silently mid-run.
- :func:`requires_rebuild` — derived from ``SearchConfig._CONSTRUCTION_BAKED_FIELDS``
  (itself derived from each field's ``spec(construction_baked=True)``, see
  ADR-0022) instead of the original ``_maybe_reset_for_construction_overrides``'s
  hand-written six-argument ``None``-check.
- :func:`apply_overrides` — the one call site that ties the above together:
  normalize, merge, validate, then mutate.
- :func:`parse_set_flag` / :func:`parse_set_flags` — parse the ``--set
  section.field=value`` CLI flag (repeatable) into typed values, coerced per
  the field's declared dataclass type (the same ``type_converters`` idiom
  ``search.config._derive_env_mapping`` uses for ``CLAUDE_*`` env vars).

Mutation mechanism — in-place attribute assignment, deliberately.
``apply_overrides`` mutates the *existing* sub-config objects on whatever
``SearchConfig`` instance it is given (``setattr(getattr(cfg, section),
field, value)``) — same object identity, no file write, no config-object
swap. This is the same in-place-mutation pattern the eleven original
functions already used safely (per their own docstrings), and is
deliberately **not** the pattern that destroyed the deployed index on
2026-08-01: that incident was an *unsaved config-OBJECT swap* racing a later
disk reload via ``invalidate_config_caches()``, a different failure mode
from mutating one object's attributes in place. See
``search/config.py``'s ``spec()`` docstring and ADR-0018.

Scope note. The plan's stated preference is to hand an arm's config as an
object to ``search(config=...)`` now that ADR-0018 Part 1 (C2) threads one
through ``RerankingEngine``, falling back to singleton mutation only when a
field is construction-baked. That preferred path is not available to this
module's only caller today: ``run_sscg_benchmark.py`` routes searches through
``SearchOrchestrator.run(arguments: dict)`` (ADR-0023), whose signature has
no config-injection parameter — confirmed empty by grep, not an oversight in
this design. So ``apply_overrides`` always mutates the config object it is
given in place; when that object is the process singleton, the caller is
responsible for also rebuilding any collaborator (e.g. a cached
``HybridSearcher``) that read a ``requires_rebuild``-flagged field once at
construction (mirroring the original ``_maybe_reset_for_construction_overrides``).
A future caller that constructs its own ``HybridSearcher`` directly (e.g. a
``probe_*.py`` script) can instead build a scratch ``SearchConfig`` and pass
it straight to ``search(config=...)`` without ever touching the singleton —
``apply_overrides`` works identically either way, since it only cares about
the object it is handed.
"""

from __future__ import annotations

import dataclasses
from collections.abc import Callable, Sequence
from typing import Any, cast

from search.config import SearchConfig, _deep_merge, validate_field_value


class ArmOverrideError(ValueError):
    """Raised when an arm's override dict or a ``--set`` value is invalid.

    Covers: an unrecognized top-level key (neither a dotted ``section.field``
    path nor a known section name), an unknown field on a known section, a
    malformed ``--set`` string, or a value rejected by
    ``validate_field_value`` (out of ``range``/not in ``choices``).
    """


def _split_dotted_key(key: str) -> tuple[str, str]:
    """Split ``"reranker.top_k_candidates"`` into ``("reranker", "top_k_candidates")``.

    Raises :class:`ArmOverrideError` if *key* is not a dotted path or its
    section is not one of ``SearchConfig``'s sub-configs.
    """
    section, sep, field_name = key.partition(".")
    if not sep or section not in SearchConfig._SUBCONFIG_TYPES:
        raise ArmOverrideError(
            f"Unrecognized override key {key!r} - expected 'section.field' "
            f"where section is one of {sorted(SearchConfig._SUBCONFIG_TYPES)}"
        )
    return section, field_name


def normalize_overrides(overrides: dict[str, Any]) -> dict[str, Any]:
    """Return *overrides* as a flat dotted-key dict — ``_dotted_keys``'s
    value-carrying sibling.

    Two input shapes are both legal, so callers can pick whichever reads more
    naturally for a given arm (e.g. the four related ``ego_graph.*`` fields
    grouped under one section key, versus one unrelated flag expressed as a
    single dotted key):

    - flat dotted-key:   ``{"reranker.top_k_candidates": 50}``
    - nested-by-section: ``{"reranker": {"top_k_candidates": 50}}``
    - a mix of both in the same dict

    One level of nesting only, matching ``_deep_merge``/``_dotted_keys``'s own
    assumption that ``SearchConfig``'s sub-config dicts are flat.
    """
    flat: dict[str, Any] = {}
    for key, value in overrides.items():
        if "." in key:
            flat[key] = value
        elif key in SearchConfig._SUBCONFIG_NAMES:
            if not isinstance(value, dict):
                raise ArmOverrideError(
                    f"Override section {key!r} must map to a dict of "
                    f"field: value, got {value!r}"
                )
            for field_name, field_value in value.items():
                flat[f"{key}.{field_name}"] = field_value
        else:
            raise ArmOverrideError(
                f"Unrecognized override key {key!r} - expected a dotted "
                f"'section.field' path or a known section name "
                f"({sorted(SearchConfig._SUBCONFIG_NAMES)})"
            )
    return flat


def merge_overrides(*sources: dict[str, Any]) -> dict[str, Any]:
    """Fold N override dicts into one, later sources winning on conflicts.

    Built directly on ``search.config._deep_merge`` applied left-to-right, so
    a later source that touches only one field of a section (flat or nested)
    does not wipe out sibling fields an earlier source set in that same
    section — the same "don't wipe out the rest" guarantee ``_deep_merge``
    gives ``SearchConfigManager.load_config()`` when layering
    ``search_overrides.json`` over the file-based config.
    """
    merged: dict[str, Any] = {}
    for source in sources:
        _deep_merge(merged, source)
    return merged


def validate_overrides(flat: dict[str, Any]) -> None:
    """Raise :class:`ArmOverrideError` on the first invalid entry in *flat*.

    *flat* must already be in the dotted-key shape :func:`normalize_overrides`
    returns. Checks the field exists on its section's dataclass, then defers
    to ``validate_field_value`` against the real section dataclass (never
    ``type(mock)``) for ``spec(range=...)``/``spec(choices=...)`` violations.
    """
    for key, value in flat.items():
        section, field_name = _split_dotted_key(key)
        section_cls = SearchConfig._SUBCONFIG_TYPES[section]
        known_fields = {f.name for f in dataclasses.fields(section_cls)}
        if field_name not in known_fields:
            raise ArmOverrideError(f"Unknown field {key!r} on {section_cls.__name__}")
        error = validate_field_value(section_cls, field_name, value)
        if error is not None:
            raise ArmOverrideError(f"{key}: {error}")


def requires_rebuild(flat: dict[str, Any]) -> bool:
    """True if any override in *flat* touches a ``spec(construction_baked=True)``
    field.

    Such a field is read once into a collaborator (a cached ``HybridSearcher``/
    reranker) at construction rather than live per search call, so mutating
    it on a config object already in use is a no-op until that collaborator
    is rebuilt. Derived from ``SearchConfig._CONSTRUCTION_BAKED_FIELDS``
    instead of the original ``_maybe_reset_for_construction_overrides``'s
    hand-written six-argument ``None``-check — see ADR-0022.
    """
    touched = {_split_dotted_key(key) for key in flat}
    return bool(touched & SearchConfig._CONSTRUCTION_BAKED_FIELDS)


def apply_overrides(cfg: SearchConfig, *sources: dict[str, Any]) -> bool:
    """Apply *sources* (flat dotted-key and/or nested-by-section, merged and
    validated) to *cfg* in place. Returns whether a rebuild is required.

    Mutates *cfg*'s existing sub-config objects' attributes — same object
    identity, no file write, no config-object swap (see module docstring).
    Raises :class:`ArmOverrideError` — not silently warned-and-skipped — if
    any override is malformed, targets an unknown field, or violates its
    ``spec(range=...)``/``spec(choices=...)``.

    Returns ``True`` if any touched field is construction-baked (see
    :func:`requires_rebuild`): the caller must then rebuild whatever
    collaborator reads that field once at construction before the override
    takes effect. Returns ``False`` (and touches nothing) if *sources* is
    empty or every source is empty — the common case where an arm doesn't
    override that particular knob, matching the original functions'
    all-``None``-means-no-op guard.
    """
    combined = merge_overrides(*sources)
    if not combined:
        return False
    flat = normalize_overrides(combined)
    validate_overrides(flat)
    rebuild = requires_rebuild(flat)
    for key, value in flat.items():
        section, field_name = _split_dotted_key(key)
        setattr(getattr(cfg, section), field_name, value)
    return rebuild


_SET_FLAG_CONVERTERS: dict[type, Callable[[str], Any]] = {
    str: str,
    int: int,
    float: float,
    # Same tolerance as SearchConfigManager._bool_from_env — bool("false") is
    # truthy, so the raw type is never usable directly for a CLI string.
    bool: lambda raw: raw.lower() in ("true", "1", "yes", "on", "enabled"),
}


def parse_set_flag(raw: str) -> tuple[str, Any]:
    """Parse one ``--set 'section.field=value'`` CLI argument into a
    ``(dotted_key, typed_value)`` pair.

    *value* is coerced per the field's declared dataclass type — the same
    ``type_converters`` idiom ``search.config._derive_env_mapping`` uses for
    ``CLAUDE_*`` env vars — so ``--set search_mode.rrf_k_parameter=150``
    yields the ``int`` ``150``, not the string ``"150"``.
    """
    key, sep, raw_value = raw.partition("=")
    if not sep:
        raise ArmOverrideError(f"--set value {raw!r} must be 'section.field=value'")
    section, field_name = _split_dotted_key(key)
    section_cls = SearchConfig._SUBCONFIG_TYPES[section]
    for f in dataclasses.fields(section_cls):
        if f.name != field_name:
            continue
        converter = _SET_FLAG_CONVERTERS.get(cast(type, f.type), str)
        try:
            value = converter(raw_value)
        except ValueError as exc:
            raise ArmOverrideError(f"--set {raw!r}: {exc}") from exc
        return key, value
    raise ArmOverrideError(f"Unknown field {key!r} on {section_cls.__name__}")


def parse_set_flags(raw_values: Sequence[str] | None) -> dict[str, Any]:
    """Parse a list of ``--set 'section.field=value'`` arguments (argparse
    ``action="append"`` output) into one flat dotted-key overrides dict,
    ready for :func:`apply_overrides`. Later duplicates of the same key win.
    """
    if not raw_values:
        return {}
    flat: dict[str, Any] = {}
    for raw in raw_values:
        key, value = parse_set_flag(raw)
        flat[key] = value
    return flat
