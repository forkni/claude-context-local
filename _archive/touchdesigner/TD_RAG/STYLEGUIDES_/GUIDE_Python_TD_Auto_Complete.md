---
title: "SudoMagic Style Guide: Python Auto-Complete in External Editors"
category: STYLEGUIDES
document_type: "guide"
difficulty: "advanced"
time_estimate: "20-25 minutes"
user_personas: ["script_developer", "technical_artist"]
operators: ["baseCOMP", "textDAT"]
concepts: ["style_guide", "best_practices", "python", "extensions", "modules", "autocomplete", "ide_integration", "vs_code"]
prerequisites: ["Python_fundamentals", "TouchDesigner_basics", "PY_Extensions", "PY_Python_in_Touchdesigner"]
workflows: ["code_style", "project_organization", "development_environment", "ide_setup"]
keywords: ["style guide", "coding standards", "touchdesigner", "python", "extensions", "modules", "autocomplete", "intellisense", "vs code", "ide"]
tags: ["guide", "style", "python", "extensions", "modules", "ide", "vscode"]
related_docs: ["PY_Extensions", "PY_Python_in_Touchdesigner", "PY_Python_Classes_and_Modules"]
---

# SudoMagic Style Guide: Python Auto-Complete in External Editors

This guide explains how to set up Python auto-completion for TouchDesigner development in an external code editor like Visual Studio Code. This enhances development speed and reduces errors by making the editor aware of custom methods in extensions and modules.

## The Core Problem

Visual Studio Code's auto-complete relies on the standard Python `import` system, which works with `.py` files on your computer. TouchDesigner, however, has a unique environment where any DAT operator can be treated as a Python module, accessed via `op.shortcut` or the `mod()` class. VS Code does not understand this TouchDesigner-specific context.

## The Solution: A "Bridge" Module

The guide proposes a method to bridge the gap between how VS Code and TouchDesigner interpret your code. This involves a specific project structure and a special "bridge" module.

### 1. Project Structure:
*   **Externalize Code:** All Python extensions must be saved as external `.py` files.
*   **Centralize Extensions:** In TouchDesigner, keep all extensions in a dedicated `base` COMP (e.g., `base_ext_manager`).
*   **Directory Naming:** On your file system, each extension should have its own directory containing an `__init__.py` file and the extension's `.py` file. For example, an extension named `Project` would live in a folder named `Project/` containing `Project.py` and `__init__.py`.

### 2. The `lookup.py` Module:
A special module, which the guide names `lookup.py`, is created to act as a bridge. It uses a `try...except` block and Python's type hinting feature.

```python
from __future__ import annotations

# This block is for VS Code. It imports the actual Python files,
# allowing the editor to understand the code and provide auto-completion.
# This will fail in TouchDesigner, which is why it's in a 'try' block.
try:
    import Project
    import Data
    import Output
except:
    pass

# This line works for both environments:
# - For VS Code: The type hint `Project.Project` tells the editor that the
#   'PROJECT' variable is an instance of the 'Project' class.
# - For TouchDesigner: It executes `PROJECT = op.PROJECT`, assigning the
#   global operator shortcut to the variable.
PROJECT:Project.Project = op.PROJECT
DATA:Data.Data = op.DATA
OUTPUT:Output.Output = op.OUTPUT
```

By using `import lookup` in your other extensions, you can then access your extensions via `lookup.PROJECT` or `lookup.DATA`, and you will get full auto-completion in VS Code while the code remains functional in TouchDesigner.

### Using Local Modules for Reusable Code

The guide also recommends using TouchDesigner's `local/modules` feature. Any Python modules placed in a `COMP` named `modules` inside a `COMP` named `local` are automatically added to Python's search path. This is ideal for creating shared, reusable libraries (e.g., a `projectTools` module with time functions) that can be imported directly into any extension without redundant code.

This setup, while complex, allows for a more seamless and professional development workflow that combines the power of TouchDesigner with the advanced features of modern code editors.
