#!/usr/bin/env python3
"""
Menu/Config Parity Drift Guard

Statically scans ``start_mcp_server.cmd`` and asserts it stays in sync with the
live ``SearchConfig`` schema and with itself:

1. Every ``cfg.<section>.<field>`` / ``config.<section>.<field>`` reference in the
   file must resolve against ``SearchConfig().to_dict()`` - catches the class of
   bug where a config field is renamed/removed (ADR-0015, ADR-0020) but the menu
   script keeps referencing the old name, which silently truncates status panels
   or reports false success on writes (see docs/adr/0020-config-field-liveness-audit.md).
2. Every ``set /p ... "Select option (X-Y)"`` prompt's declared range must agree
   with the choice letters/digits actually dispatched in that menu block, and
   with that block's "Invalid choice" guard message - catches a dangling/missing
   handler reference (e.g. a menu advertising ``0-9, A, B`` but only wiring up
   ``0-9, A``).
"""

import re
from pathlib import Path

from search.config import SearchConfig


_ALIAS_COUNT = len(SearchConfig._FLAT_KEY_ALIASES)
_SECTION_COUNT = len(SearchConfig._SUBCONFIG_FIELDS)


CMD_PATH = Path(__file__).resolve().parents[2] / "start_mcp_server.cmd"

# Matches `cfg.section.field` / `config.section.field` (python -c one-liners
# embedded in the .cmd file all bind the loaded/loading config to one of these
# two names).
FIELD_REF_RE = re.compile(r"(?:cfg|config)\.(\w+)\.(\w+)")

PROMPT_RE = re.compile(r'set /p (\w+)="Select option \(([^)]+)\): "')
GUARD_RE = re.compile(r"\[ERROR\].*Please select ([^.\n]+)\.")


def _parse_range_spec(spec: str) -> set[str]:
    """Normalize a human-readable choice range into a set of tokens.

    Handles both the terse prompt style (``"0-9, A, B"``) and the guard-message
    style that spells out the last item with "or" (``"0-9, A, or B"``). Digit
    ranges (``"0-6"``) expand to individual digit strings; everything else is
    a literal choice token, upper-cased so letter comparisons are
    case-insensitive (menus dispatch letter choices via `if /i`).
    """
    spec = spec.strip().replace(", or ", ", ").replace(" or ", ", ")
    tokens = [t.strip() for t in spec.split(",") if t.strip()]
    result: set[str] = set()
    for token in tokens:
        range_match = re.match(r"^(\d+)-(\d+)$", token)
        if range_match:
            lo, hi = int(range_match.group(1)), int(range_match.group(2))
            result.update(str(i) for i in range(lo, hi + 1))
        else:
            result.add(token.upper())
    return result


def test_config_field_references_resolve_against_schema() -> None:
    """Every cfg.<section>.<field> / config.<section>.<field> reference in the
    .cmd file must exist in the live SearchConfig schema."""
    lines = CMD_PATH.read_text(encoding="utf-8").splitlines()
    schema = SearchConfig().to_dict()

    unknown: list[str] = []
    match_count = 0
    for line_no, line in enumerate(lines, start=1):
        for match in FIELD_REF_RE.finditer(line):
            match_count += 1
            section, field = match.group(1), match.group(2)
            if section not in schema:
                unknown.append(
                    f"  line {line_no}: cfg.{section}.{field} - unknown section '{section}'"
                )
            elif field not in schema[section]:
                unknown.append(
                    f"  line {line_no}: cfg.{section}.{field} - "
                    f"'{section}' has no field '{field}'"
                )

    # Sanity check that the regex is actually finding real references - a guard
    # that matches nothing is vacuously true, not a guard. The floor is tied to
    # the spec table (ADR-0022, len(_FLAT_KEY_ALIASES)) rather than a hardcoded
    # magic number, since aliased fields are exactly the ones exposed at the
    # flat/env/menu surface the .cmd file manages - it tightens automatically
    # as more fields gain a flat alias.
    assert match_count > _ALIAS_COUNT, (
        f"Expected more than {_ALIAS_COUNT} (flat-alias count) cfg./config. "
        f"field references in {CMD_PATH.name}, found {match_count}. The scan "
        "pattern may be broken."
    )

    assert not unknown, (
        f"{len(unknown)} config field reference(s) in {CMD_PATH.name} do not "
        "resolve against SearchConfig's live schema:\n" + "\n".join(unknown)
    )


def test_menu_choice_ranges_match_handlers_and_guards() -> None:
    """Every 'Select option (X-Y)' prompt must agree with the choices actually
    dispatched in that block, and with its 'Invalid choice' guard message."""
    text = CMD_PATH.read_text(encoding="utf-8")
    lines = text.splitlines()

    prompts = []
    for i, line in enumerate(lines):
        match = PROMPT_RE.search(line)
        if match:
            prompts.append((i, match.group(1), match.group(2)))

    # One menu per config section, plus the top-level main menu (ADR-0022) -
    # tied to SearchConfig._SUBCONFIG_FIELDS rather than a hardcoded floor, so
    # it grows if a new config section is added.
    expected_min_prompts = _SECTION_COUNT + 1
    assert len(prompts) >= expected_min_prompts, (
        f"Expected {expected_min_prompts}+ (section count + main menu) "
        f"'Select option' menu prompts in {CMD_PATH.name}, found "
        f"{len(prompts)}. The scan pattern may be broken."
    )

    problems: list[str] = []
    for idx, (line_no, var, range_spec) in enumerate(prompts):
        start = line_no
        end = prompts[idx + 1][0] if idx + 1 < len(prompts) else len(lines)
        window = "\n".join(lines[start:end])

        expected = _parse_range_spec(range_spec)

        handler_re = re.compile(
            r'if\s+(?:/i\s+)?"!' + re.escape(var) + r'!"=="([^"]+)"'
        )
        handled = {
            token.upper() if not token.isdigit() else token
            for token in handler_re.findall(window)
        }

        location = f"line {start + 1} (var={var}, prompt range={range_spec!r})"

        if handled != expected:
            missing = expected - handled
            extra = handled - expected
            detail = []
            if missing:
                detail.append(f"missing handlers for {sorted(missing)}")
            if extra:
                detail.append(f"handlers for undeclared choices {sorted(extra)}")
            problems.append(f"  {location}: {'; '.join(detail)}")
            continue

        guard_match = GUARD_RE.search(window)
        if guard_match is None:
            problems.append(f"  {location}: no 'Invalid choice' guard found")
            continue

        guard_set = _parse_range_spec(guard_match.group(1))
        if guard_set != expected:
            problems.append(
                f"  {location}: guard message range {sorted(guard_set)} "
                f"disagrees with prompt range {sorted(expected)}"
            )

    assert not problems, (
        f"{len(problems)} menu prompt/handler/guard mismatch(es) in "
        f"{CMD_PATH.name}:\n" + "\n".join(problems)
    )
