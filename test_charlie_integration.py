"""Test file to verify Charlie AI integration."""
import os
import sys

def calculate_sum(a, b):
    return a + b

def very_long_function_name_that_exceeds_line_length_limit_and_should_trigger_linting_warnings(parameter_one, parameter_two, parameter_three):
    result = parameter_one + parameter_two + parameter_three
    return result

class TestClass:
    def method_without_docstring(self, x, y):
        return x * y

if __name__ == "__main__":
    print(calculate_sum(5, 10))
    print(very_long_function_name_that_exceeds_line_length_limit_and_should_trigger_linting_warnings(1, 2, 3))
