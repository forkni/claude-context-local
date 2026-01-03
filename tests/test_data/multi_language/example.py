# Python test file for comparison
def calculate_sum(a, b):
    """Calculate sum of two numbers."""
    return a + b


class Calculator:
    """A simple calculator class."""

    def __init__(self):
        self.result = 0

    def add(self, value):
        """Add a value to the result."""
        self.result += value
        return self

    def multiply(self, value):
        """Multiply the result by a value."""
        self.result *= value
        return self


async def async_function():
    """An async function example."""
    import asyncio

    await asyncio.sleep(1)
    return {"data": "example"}
