"""Shared fixtures/helpers for chunking unit tests."""


def assert_length_and_newline_invariants(original: bytes, rewritten: bytes) -> None:
    """Assert a rewrite preserves total length and every newline's byte offset.

    Shared contract of `blank_preserving_layout`, `_blank_macro_wrapper`, and
    the CUDA blankers: downstream chunk `start_line`/`end_line` are computed
    against the rewritten buffer, so any shift would silently mis-attribute
    line numbers.
    """
    assert len(rewritten) == len(original)
    original_newlines = [i for i, b in enumerate(original) if b == 0x0A]
    rewritten_newlines = [i for i, b in enumerate(rewritten) if b == 0x0A]
    assert rewritten_newlines == original_newlines
