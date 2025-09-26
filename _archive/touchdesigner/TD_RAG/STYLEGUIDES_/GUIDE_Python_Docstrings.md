---
title: "SudoMagic Style Guide: Python Docstrings and Comments"
category: STYLEGUIDES
document_type: "guide"
difficulty: "beginner"
time_estimate: "10-15 minutes"
user_personas: ["script_developer", "technical_artist"]
operators: []
concepts: ["style_guide", "best_practices", "python", "docstrings", "comments", "documentation"]
prerequisites: ["Python_fundamentals"]
workflows: ["code_style", "project_organization", "documentation"]
keywords: ["style guide", "coding standards", "touchdesigner", "python", "docstrings", "comments"]
tags: ["guide", "style", "python", "documentation", "docstrings"]
related_docs: ["PY_Python_in_Touchdesigner", "PY_Extensions"]
---

# SudoMagic Style Guide: Python Docstrings and Comments

Doc strings and comments are crucial for code readability and long-term maintenance. They serve as notes for your future self and other collaborators. Well-documented code is easier to reuse and understand months after it's written, preventing the need to rewrite complex logic from scratch.

---

## Examples

### Function

**Practical Example**
```python
def To_rgb_from_hex(value:str) -> tuple:
    """Returns a color as a float tuple (rgb) converted
    from HEX
    
    Args
    ---------------
    value (`str`)
    > hex string to be converted into rgb 

    Returns
    ---------------
    color (`tuple`)
    > normalized color expressed as (r, g, b) tuple
    """
```

**Boiler Plate**
```python
def Foo_bar(arg1:int) -> None:
    """Single line description of function.

    Any additional comments or operational considerations you'd like
    to add about the function in question.
    
    Args
    ---------------
    arg1 (`int`)
    > description of arg's role 

    Returns
    ---------------
    None
    """
```

**Short Form**
This is acceptable when type hints are present for all arguments and return values. The docstring can be shortened to a brief description.

```python
def Foo_bar(arg1:str) -> None:
    """One line description

    Any additional comments or operational considerations you'd like
    to add about the method in question.
    """
```

---

### Header

**Practical Example**
```python
"""
SudoMagic | sudomagic.com
Authors | Matthew Ragan, Ian Shelanskey
Contact | contact@sudomagic.com
"""

# td python mods
import SudoMagic
import Lookup

# pure python
import json
import sys
import socket
import logging
```

**Boiler Plate**
```python
"""
SudoMagic | sudomagic.com
Authors | Matthew Ragan, Ian Shelanskey
Contact | contact@sudomagic.com
"""

# td python mods
import SudoMagic
import Lookup

# pure python
```

---

### Class

**Practical Example**
```python
class Project(SudoMagic.Types.abstract_component_singleton):
    """Project Class

    The project class is responsible for the construction and distribution
    of all extensions. _setup() constructs extensions in order, allowing
    for a reliable and consistent start-up sequence for all python extensions

    Additionally the Project class is responsible for start-up functions
    that include loading settings from file.
    """
```

**Boiler Plate**
```python
class Foo:
    """Foo Class one line description

    Any additional comments or operational considerations you'd like
    to add about the class in question.
    """
```

---

### Method

**Practical Example**
```python
def Set_process(self, override_role:str) -> None:
    """sets process from available processes in config
    
    overrides provided env var and runs Touch_start()
    
    Args
    ---------------
    override_role (`str`)
    > new string to set for role 

    Returns
    ---------------
    None
    """
```

**Boiler Plate**
```python
def Bar(self, arg1:str) -> None:
    """One line description

    Any additional comments or operational considerations you'd like
    to add about the method in question.

    Args
    ---------------
    self (`callable`)
    > new string to set for role 

    arg1 (`str`)
    > some argument description 

    Returns
    ---------------
    None
    """
```

**Short Form**
Similar to functions, this is acceptable when type hints are present.

```python
def Bar(self, arg1:str) -> None:
    """One line description

    Any additional comments or operational considerations you'd like
    to add about the method in question.
    """
```
