---
title: "SudoMagic Style Guide: Python Modules"
category: STYLEGUIDES
document_type: "guide"
difficulty: "intermediate"
time_estimate: "10-15 minutes"
user_personas: ["script_developer", "technical_artist"]
operators: ["textDAT"]
concepts: ["style_guide", "best_practices", "python", "modules", "namespace", "code_organization"]
prerequisites: ["Python_fundamentals", "TouchDesigner_basics"]
workflows: ["code_style", "project_organization", "library_development"]
keywords: ["style guide", "coding standards", "touchdesigner", "python", "modules", "namespace", "mod"]
tags: ["guide", "style", "python", "modules", "organization"]
related_docs: ["CLASS_MOD_Class", "PY_Python_Classes_and_Modules"]
---

# SudoMagic Style Guide: Python Modules

This guide covers best practices for using Python modules in TouchDesigner, focusing on avoiding namespace collisions and understanding the appropriate use cases for modules.

## Namespace Collisions

In TouchDesigner, Text DATs can function as Python modules, allowing you to import and reuse code across your project using the `mod` class. However, this approach presents unique challenges, primarily concerning namespace collisions.

A significant risk is creating a namespace collision by naming a Text DAT the same as a standard Python library. For example, if you create a Text DAT named `datetime` to act as a custom wrapper for the `datetime` library, importing it will override the standard Python `datetime` library within that scope. This makes it impossible to access the original library's functions and creates a confusing and error-prone environment.

**Recommendation:** To prevent this, adopt a specific naming convention. The guide suggests appending `MOD` to any Text DAT intended to be used as a module (e.g., name your custom datetime wrapper `datetimeMOD`).

## When to Use Modules

Modules are excellent for creating libraries of reusable functions that can be called from multiple places, such as various Execute DATs.

However, they have limitations. It is difficult to maintain persistent objects or variables between script executions because each Text DAT has an independent scope. While using global variables is a possible workaround, it is strongly discouraged as it significantly increases the risk of namespace collisions and can lead to messy, unmanageable code.

## Official Documentation Links

*   [MOD Class](https://docs.derivative.ca/MOD_Class)
*   [Python Classes and Modules](https://docs.derivative.ca/Python_Classes_and_Modules)
