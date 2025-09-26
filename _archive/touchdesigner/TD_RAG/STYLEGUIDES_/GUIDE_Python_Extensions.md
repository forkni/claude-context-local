---
title: "SudoMagic Style Guide: Python Extensions"
category: STYLEGUIDES
document_type: "guide"
difficulty: "intermediate"
time_estimate: "15-20 minutes"
user_personas: ["script_developer", "technical_artist"]
operators: ["baseCOMP", "containerCOMP"]
concepts: ["style_guide", "best_practices", "python", "extensions", "classes", "naming_conventions", "documentation"]
prerequisites: ["Python_fundamentals", "TouchDesigner_basics", "PY_Extensions"]
workflows: ["code_style", "project_organization", "component_development"]
keywords: ["style guide", "coding standards", "touchdesigner", "python", "extensions", "classes", "methods", "naming", "docstrings", "type hinting"]
tags: ["guide", "style", "python", "extensions", "oop"]
related_docs: ["PY_Extensions", "PY_CallbacksExtExtension"]
---

# SudoMagic Style Guide: Python Extensions

This guide outlines best practices for writing Python Extensions in TouchDesigner, focusing on class structure, method naming, and documentation.

## Custom Class Objects

### Type Hinting
It is highly recommended to use Python's type hints for function arguments and return values. This improves code clarity, helps prevent bugs from incorrect argument types, and enables better autocompletion in code editors like VS Code.

### Docstrings
Functions should include comprehensive docstrings that describe:
*   The function's purpose.
*   **Args**: Each argument, its type, and a description.
*   **Returns**: The return value, its type, and a description.
*   **Raises**: Any errors the function might raise.

## Method Naming Conventions

The naming convention of a method indicates its intended use:

*   **Promoted Methods (`Promoted_method`)**: Use `PascalCase` for methods that are intended to be promoted to operator parameters.
    ```python
    class Foo:
        def Promoted_method(self, some_int_arg:int) -> None:
            pass
    ```
*   **Internal Methods (`internal_method`)**: Use `snake_case` for regular methods used within the extension class.
    ```python
    class Foo:
        def internal_method(self, some_int_arg:int) -> None:
            pass
    ```
*   **Private Methods (`_private_method`)**: Use a leading underscore (`_`) for methods that should be treated as private and not accessed from outside the class.
    ```python
    class Foo:
        def _private_method(self, some_int_arg:int) -> None:
            pass
    ```

## Singletons

Singletons are classes that belong to a single, unique operator instance. A common characteristic is an `__init__` method that stores the owner operator and standard TouchDesigner callback methods like `Touch_start`.

```python
class Output:
    def __init__(self, owner_op):
        self.Owner_op = owner_op

    def Touch_start(self):
        print('Running Touch Start | Output')
```
