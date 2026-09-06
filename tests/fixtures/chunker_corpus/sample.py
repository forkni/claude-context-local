"""Tiny Python fixture: function, class+method, decorated function/class."""

from dataclasses import dataclass


def add(x: int, y: int) -> int:
    """Add two numbers."""
    return x + y


class Greeter:
    """A simple greeter class."""

    def greet(self, name: str) -> str:
        """Return a greeting string."""
        return f"Hello, {name}"


def _passthrough(f):
    return f


@_passthrough
def decorated_fn() -> None:
    """A decorated no-op function."""
    pass


@dataclass
class Boxed:
    """A decorated (dataclass) class with one method."""

    value: int = 0

    def unwrap(self) -> int:
        """Return the boxed value."""
        return self.value
