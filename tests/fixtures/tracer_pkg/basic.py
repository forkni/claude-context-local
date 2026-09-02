"""Plain, method, instantiation, recursion, comprehension, closure, lambda, generator."""

from __future__ import annotations


def leaf(x: int) -> int:
    return x + 1


def plain_caller(x: int) -> int:
    return leaf(x)


class Widget:
    def __init__(self, n: int) -> None:
        self.n = leaf(n)

    def method(self) -> int:
        return leaf(self.n)


def instantiate() -> int:
    return Widget(1).method()


def recurse(n: int) -> int:
    return 0 if n <= 0 else 1 + recurse(n - 1)


def comprehension() -> list[int]:
    return [leaf(i) for i in range(3)]


def closure_user() -> int:
    def inner(v: int) -> int:
        return leaf(v)

    return inner(2)


def sort_with_key() -> list[int]:
    return sorted([3, 1, 2], key=lambda v: leaf(v))


def gen():
    yield leaf(1)
    yield leaf(2)


def consume_gen_twice() -> list[int]:
    return list(gen()) + list(gen())
