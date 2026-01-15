"""Smart dedentation utilities for code parsing.

Provides dedentation logic for decorated definitions and nested code.
Uses the Scrapy first-line baseline approach for handling flush-left content.

References:
    - Scrapy GitHub issue #4477 (flush-left docstring fix)
    - Scrapy PR #4935 (first-line baseline approach)
"""

import ast
import logging

logger = logging.getLogger(__name__)


def _basic_dedent_only(code: str) -> str:
    """Dedent code without AST validation.

    Used for split blocks which are syntactically incomplete by design.
    Just normalizes indentation without trying to parse.

    Args:
        code: Source code string with potential leading indentation

    Returns:
        Dedented code without AST validation
    """
    # Normalize line endings and tabs
    code = code.replace("\r\n", "\n").replace("\r", "\n")
    code = code.expandtabs(4)

    lines = code.split("\n")

    # Strip leading/trailing blank lines
    while lines and not lines[0].strip():
        lines.pop(0)
    while lines and not lines[-1].strip():
        lines.pop()

    if not lines:
        return code

    # Find baseline indentation from first non-blank line
    first_line = lines[0]
    baseline_indent = len(first_line) - len(first_line.lstrip())

    if baseline_indent == 0:
        return "\n".join(lines)

    # Remove baseline indentation from all lines
    dedented_lines = []
    for line in lines:
        if not line.strip():
            dedented_lines.append("")
        elif len(line) >= baseline_indent and line[:baseline_indent].strip() == "":
            dedented_lines.append(line[baseline_indent:])
        else:
            dedented_lines.append(line.lstrip())

    return "\n".join(dedented_lines)


def smart_dedent(code: str) -> str:
    """Dedent code by removing the indentation of the first non-blank line.

    Uses first-line baseline approach (Scrapy method) which handles:
    - Flush-left string continuations (docstrings with flush-left text)
    - Mixed tabs/spaces (tabs normalized to 4 spaces)
    - Blank lines without whitespace
    - Decorators and nested structures

    This solves the textwrap.dedent() failure for decorated definitions.

    Args:
        code: Source code string with potential leading indentation

    Returns:
        Dedented code that can be parsed by ast.parse()

    References:
        Scrapy GitHub issue #4477, PR #4935
    """
    if not code or not code.strip():
        return code

    # Early exit for split blocks - they're syntactically incomplete by design
    # Split blocks contain the marker "# ... (split block)" and cannot be parsed
    if "# ... (split block)" in code:
        return _basic_dedent_only(code)

    # Normalize line endings (CRLF → LF, CR → LF)
    # This handles Windows files and mixed line endings
    code = code.replace("\r\n", "\n").replace("\r", "\n")

    # Normalize tabs to 4 spaces for consistent handling
    code = code.expandtabs(4)

    lines = code.split("\n")

    # Strip leading/trailing blank lines
    while lines and not lines[0].strip():
        lines.pop(0)
    while lines and not lines[-1].strip():
        lines.pop()

    if not lines:
        return code

    # Find indentation of first non-blank line (baseline)
    first_line = lines[0]
    baseline_indent = len(first_line) - len(first_line.lstrip())

    if baseline_indent == 0:
        # First line is flush-left, try parsing directly
        dedented = "\n".join(lines)
        try:
            ast.parse(dedented)
            return dedented
        except SyntaxError:
            # First line is at column 0 but subsequent lines may be indented
            # (common with decorated definitions extracted by tree-sitter)
            # Find minimum indent from subsequent lines
            subsequent_indents = []
            for line in lines[1:]:  # Skip first line
                if line.strip():  # Non-blank line
                    indent = len(line) - len(line.lstrip())
                    if indent > 0:
                        subsequent_indents.append(indent)

            if subsequent_indents:
                # Dedent subsequent lines by their minimum common indent
                min_indent = min(subsequent_indents)
                dedented_lines = [lines[0]]  # Keep first line as-is
                for line in lines[1:]:
                    if not line.strip():
                        dedented_lines.append("")
                    elif len(line) >= min_indent and line[:min_indent].strip() == "":
                        dedented_lines.append(line[min_indent:])
                    else:
                        dedented_lines.append(line.lstrip())

                dedented = "\n".join(dedented_lines)
                try:
                    ast.parse(dedented)
                    return dedented
                except SyntaxError:
                    pass  # Fall through to wrap_with_if_true

            return wrap_with_if_true(dedented)

    # Remove baseline indentation from all lines
    dedented_lines = []
    for line in lines:
        if not line.strip():
            # Preserve blank lines as empty
            dedented_lines.append("")
        elif len(line) >= baseline_indent and line[:baseline_indent].strip() == "":
            # Line has at least baseline_indent spaces, remove them
            dedented_lines.append(line[baseline_indent:])
        else:
            # Line has less indentation than baseline (flush-left content)
            # This happens with multi-line string continuations
            dedented_lines.append(line.lstrip())

    dedented = "\n".join(dedented_lines)

    try:
        ast.parse(dedented)
        return dedented
    except SyntaxError:
        return wrap_with_if_true(dedented)


def wrap_with_if_true(code: str) -> str:
    """Wrap code with 'if True:' block as fallback for flush-left content.

    This is the industry-standard fallback (used by Scrapy, Numba) for handling
    code with flush-left content that can't be dedented normally.

    Args:
        code: Dedented code that may still have parsing issues

    Returns:
        Wrapped code or original if wrapping fails
    """
    # Indent all lines by 4 spaces
    indented_lines = []
    for line in code.split("\n"):
        if line.strip():
            indented_lines.append("    " + line)
        else:
            indented_lines.append("")

    wrapped = "if True:\n" + "\n".join(indented_lines)

    try:
        ast.parse(wrapped)
        return wrapped
    except SyntaxError as e:
        # If even wrapping fails, return original code
        # Log for debugging - helps identify edge cases not handled
        logger.debug(
            f"_smart_dedent: Both dedent and wrap failed. "
            f"Error: {e}. First 100 chars: {repr(code[:100])}"
        )
        # Let the caller handle the syntax error
        return code


# Backward compatibility aliases
_smart_dedent = smart_dedent
_wrap_with_if_true = wrap_with_if_true
