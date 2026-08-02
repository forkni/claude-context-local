"""Config field liveness ratchet (ADR-0022).

Freezes ADR-0020's manually-verified liveness result rather than reproducing
it - that audit verified each field with three independent methods (semantic
search, find_connections zero-caller confirmation, exhaustive grep) agreeing
before pronouncing a field dead. A name-match cannot stand in for that: bare
field-name matching finds a "hit" for every one of the 124 fields, including
all 13 fields ADR-0020 proved dead, so it is not an audit.

What this test *does* catch: the declared reader file being deleted or
renamed, and a field surviving the removal of the code that consumed it -
exactly the drift that accumulated ADR-0020's 13 dead fields between audits.
"""

import dataclasses
from pathlib import Path

from search.config import SearchConfig


REPO_ROOT = Path(__file__).resolve().parents[3]


def _iter_fields():
    for _section_name, section_cls in SearchConfig._SUBCONFIG_TYPES.items():
        for f in dataclasses.fields(section_cls):
            yield section_cls.__name__, f


def test_every_field_declares_reader_or_is_schema_only():
    """Each field must opt into liveness tracking via reader=, or explicitly
    opt out via schema_only=True - there is no silent third option."""
    missing = [
        f"{cls_name}.{f.name}"
        for cls_name, f in _iter_fields()
        if not f.metadata.get("schema_only") and f.metadata.get("reader") is None
    ]
    assert not missing, (
        "Field(s) with neither spec(reader=...) nor spec(schema_only=True) "
        "(see ADR-0022): " + ", ".join(missing)
    )


def test_reader_files_exist():
    missing_files = [
        f"{cls_name}.{f.name} -> {reader}"
        for cls_name, f in _iter_fields()
        if (reader := f.metadata.get("reader")) is not None
        and not (REPO_ROOT / reader).exists()
    ]
    assert not missing_files, (
        "Declared reader file(s) do not exist (renamed/deleted?):\n  "
        + "\n  ".join(missing_files)
    )


def test_reader_files_mention_field_name():
    missing_mentions = []
    for cls_name, f in _iter_fields():
        reader = f.metadata.get("reader")
        if reader is None:
            continue
        text = (REPO_ROOT / reader).read_text(encoding="utf-8")
        if f.name not in text:
            missing_mentions.append(f"{cls_name}.{f.name} -> {reader}")
    assert not missing_mentions, (
        "Field name not found anywhere in its declared reader file (field "
        "may no longer be live - see ADR-0020/ADR-0022):\n  "
        + "\n  ".join(missing_mentions)
    )
