"""Utility functions for mathematical operations."""


def add(a, b):
    """Calculate sum of two numbers."""
    return a + b


def subtract(a, b):
    """Calculate difference of two numbers."""
    return a - b


def multiply(a, b):
    """Calculate product of two numbers."""
    return a * b


def divide(a, b):
    """Calculate division of two numbers."""
    if b == 0:
        raise ValueError("Cannot divide by zero")
    return a / b
