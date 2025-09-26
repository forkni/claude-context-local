---
title: "SudoMagic Style Guide: Python Local Modules"
category: STYLEGUIDES
document_type: "guide"
difficulty: "intermediate"
time_estimate: "10-15 minutes"
user_personas: ["script_developer", "technical_artist"]
operators: ["baseCOMP", "textDAT"]
concepts: ["style_guide", "best_practices", "python", "modules", "local_modules", "namespace", "code_organization", "search_path"]
prerequisites: ["Python_fundamentals", "TouchDesigner_basics", "PY_Extensions"]
workflows: ["code_style", "project_organization", "library_development", "component_development"]
keywords: ["style guide", "coding standards", "touchdesigner", "python", "modules", "local modules", "namespace", "mod", "search path"]
tags: ["guide", "style", "python", "modules", "organization", "local"]
related_docs: ["PY_Extensions", "CLASS_MOD_Class", "PY_Python_Classes_and_Modules"]
---

# SudoMagic Style Guide: Python Local Modules

This guide covers best practices for using local Python modules in TouchDesigner, focusing on search path hierarchy and common usage patterns.

## Search Path Hierarchy

In TouchDesigner, you can create local Python modules that are easily importable from child components by organizing them in a specific folder structure. This utilizes TouchDesigner's built-in Python search path.

When you use the `import` keyword, TouchDesigner searches for the specified module (a Text DAT) in the following order:
1.  The current component.
2.  The `local/modules` component of the current component.
3.  The `local/modules` component of each parent, moving up the hierarchy.
4.  If not found, `None` is returned.

## How to Use Local Modules

To make a Python module available to its sibling and child operators, you should place it inside a `modules` Base COMP, which itself is inside a `local` Base COMP.

**Structure:**

```
local
└── modules
    └── yourModuleNameDAT
```

## Common Patterns

This feature is often used in two main ways within a project:

1.  **Project-Wide Library:** A `local/modules` structure at the root of the project (e.g., `/local/modules/MyLibrary`) makes a set of functions and classes available everywhere in the project.
2.  **Component-Specific Library:** A `local/modules` structure within a specific component (e.g., `/my_component/local/modules/ComponentSpecificCode`) provides helper functions that are only relevant to that part of the network.
