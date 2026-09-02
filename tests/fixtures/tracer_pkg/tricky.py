"""Decorator wrapper, multi-line signature, exception unwinding, thread, dataclass,
and a callback routed through a Python-level external frame (contextlib)."""

from __future__ import annotations

import contextlib
import threading
from dataclasses import dataclass

from tests.fixtures.tracer_pkg.basic import leaf


def deco(fn):
    def wrapper(*args, **kwargs):
        return fn(*args, **kwargs)

    return wrapper


@deco
def decorated(x: int) -> int:
    return leaf(x)


def call_decorated() -> int:
    return decorated(5)


def multi_line_sig(
    a: int,
    b: int,
) -> int:
    return leaf(a + b)


def raiser() -> None:
    raise ValueError("boom")


def middle() -> None:
    raiser()


def catcher() -> int:
    try:
        middle()
    except ValueError:
        return leaf(0)
    return -1


def thread_target() -> None:
    leaf(9)


def run_thread() -> None:
    t = threading.Thread(target=thread_target)
    t.start()
    t.join()


@dataclass
class Point:
    x: int
    y: int


def make_point() -> Point:
    return Point(1, 2)


@contextlib.contextmanager
def managed():
    yield leaf(3)


def via_external() -> int:
    with managed() as value:
        return value
