"""Unit tests for ``utils/deprecation.py`` (Phase 13.3).

A single decorator, zero collaborators, previously 0% covered (16/16
statements missed in the Phase 13.1 term-missing report) -- no caller in the
production tree currently applies ``@deprecated`` to anything, so nothing
exercised it. This project's suite runs with ``filterwarnings = ["error",
...]`` (see ``pyproject.toml``), so every call into a decorated function must
be wrapped in ``pytest.warns`` -- an uncaught ``DeprecationWarning`` would
otherwise fail the test that triggered it, not just the code under test.
"""

import pytest

from utils.deprecation import deprecated


class TestDeprecated:
    def test_wrapped_function_still_returns_its_value(self):
        @deprecated()
        def old_function():
            return "still works"

        with pytest.warns(DeprecationWarning):
            assert old_function() == "still works"

    def test_wrapped_function_forwards_args_and_kwargs(self):
        @deprecated()
        def add(a, b, *, c=0):
            return a + b + c

        with pytest.warns(DeprecationWarning):
            assert add(1, 2, c=3) == 6

    def test_default_message_has_no_replacement_clause(self):
        @deprecated()
        def old_function():
            pass

        with pytest.warns(DeprecationWarning) as record:
            old_function()

        msg = str(record[0].message)
        assert "old_function is deprecated since v0.7.0" in msg
        assert "Will be removed in v0.8.0." in msg
        assert "Use" not in msg

    def test_replacement_and_versions_are_interpolated(self):
        @deprecated(
            replacement="new_method()", version="1.2.0", removal_version="2.0.0"
        )
        def old_method():
            pass

        with pytest.warns(DeprecationWarning) as record:
            old_method()

        msg = str(record[0].message)
        assert "old_method is deprecated since v1.2.0" in msg
        assert "Use new_method() instead" in msg
        assert "Will be removed in v2.0.0." in msg

    def test_functools_wraps_preserves_identity(self):
        @deprecated()
        def old_function():
            """Original docstring."""

        assert old_function.__name__ == "old_function"
        assert old_function.__doc__ == "Original docstring."

    def test_wrapper_is_marked_deprecated_for_introspection(self):
        @deprecated()
        def old_function():
            pass

        assert old_function.__deprecated__ is True

    def test_qualname_used_for_methods(self):
        class Foo:
            @deprecated()
            def old_method(self):
                return "ok"

        with pytest.warns(DeprecationWarning) as record:
            Foo().old_method()

        assert "Foo.old_method is deprecated" in str(record[0].message)
