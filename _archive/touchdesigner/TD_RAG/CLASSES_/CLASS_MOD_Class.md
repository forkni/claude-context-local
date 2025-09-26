---
category: CLASS
document_type: reference
difficulty: intermediate
time_estimate: 10-15 minutes
operators:
- Text_DAT
- Script_DAT
- Execute_DAT
concepts:
- module_on_demand
- python_scripting
- module_importing
- dynamic_import
- code_organization
- search_path_resolution
- dat_modules
prerequisites:
- Python_fundamentals
- DAT_basics
- MODULE_td_Module
- import_systems
workflows:
- code_organization
- building_reusable_tools
- library_management
- advanced_scripting
- modular_development
keywords:
- module on demand
- import dat
- python module
- code library
- dynamic import
- script organization
- mod object
- search path
- local/modules
- dat import
- module system
- code reuse
- library management
tags:
- python
- module
- import
- scripting
- dynamic
- dat
- organization
- reusable
relationships:
  MODULE_td_Module: strong
  CLASS_DAT_Class: strong
  PY_Python_in_Touchdesigner: medium
  PY_Python_Tips: medium
related_docs:
- MODULE_td_Module
- CLASS_DAT_Class
- PY_Python_in_Touchdesigner
- PY_Python_Tips
hierarchy:
  secondary: module_management
  tertiary: module_on_demand
question_patterns:
- How to use CLASS class?
- What methods are available?
- How to access properties?
- Python API reference?
common_use_cases:
- code_organization
- building_reusable_tools
- library_management
- advanced_scripting
---

# MOD Class

<!-- TD-META
category: CLASS
document_type: reference
operators: [Text_DAT, Script_DAT, Execute_DAT]
concepts: [module_on_demand, python_scripting, module_importing, dynamic_import, code_organization, search_path_resolution, dat_modules]
prerequisites: [Python_fundamentals, DAT_basics, MODULE_td_Module, import_systems]
workflows: [code_organization, building_reusable_tools, library_management, advanced_scripting, modular_development]
related: [MODULE_td_Module, CLASS_DAT_Class, PY_Python_in_Touchdesigner, PY_Python_Tips]
relationships: {
  "MODULE_td_Module": "strong",
  "CLASS_DAT_Class": "strong",
  "PY_Python_in_Touchdesigner": "medium",
  "PY_Python_Tips": "medium"
}
hierarchy:
  "primary": "scripting"
  "secondary": "module_management"
  "tertiary": "module_on_demand"
keywords: [module on demand, import dat, python module, code library, dynamic import, script organization, mod object, search path, local/modules, dat import, module system, code reuse, library management]
tags: [python, module, import, scripting, dynamic, dat, organization, reusable]
TD-META -->

## 🎯 Quick Reference

**Purpose**: Python class reference for TouchDesigner API development
**Difficulty**: Intermediate
**Time to read**: 10-15 minutes
**Use for**: code_organization, building_reusable_tools, library_management

**Common Questions Answered**:

- "How to use CLASS class?" → [See relevant section]
- "What methods are available?" → [See relevant section]
- "How to access properties?" → [See relevant section]
- "Python API reference?" → [See relevant section]

## 🔗 Learning Path

**Prerequisites**: [Python Fundamentals] → [Dat Basics] → [Module Td Module]
**This document**: CLASS reference/guide
**Next steps**: [MODULE td Module] → [CLASS DAT Class] → [PY Python in Touchdesigner]

**Related Topics**: code organization, building reusable tools, library management

## Summary

Module On Demand (MOD) class provides access to Module On Demand object, which allows [CLASS_DAT] to be dynamically imported as modules. It can be accessed with the `mod` object, found in the automatically imported [PY_td] module. Alternatively, one can use the regular python statement: `import`. Use of the `import` statement is limited to modules in the search path, where as the `mod` format allows complete statements in one line, which is more useful for entering expressions. Also note that [CLASS_DAT] modules cannot be organized into packages as regular file system based python modules can be.

## Relationship Justification

Core component of td module's functionality, strongly connected for module access patterns. Essential for DAT-based Python development. Links to Python environment guide and tips for practical usage examples and troubleshooting.

## Content

- [Introduction](#introduction)
- [Members](#members)
- [Methods](#methods)
- [Usage](#usage)
  - [import datName](#import-datname)
  - [m = mod.datName](#m--moddatname)
  - [m = mod(pathToDat)](#m--modpathtod)
- [Comparing Usage](#comparing-usage)
- [Search Path](#search-path)

## Introduction

The MOD class provides access to Module On Demand object, which allows [CLASS_DAT] to be dynamically imported as modules. It can be accessed with the `mod` object, found in the automatically imported [PY_td] module. Alternatively, one can use the regular python statement: `import`. Use of the `import` statement is limited to modules in the search path, where as the `mod` format allows complete statements in one line, which is more useful for entering expressions. Also note that [CLASS_DAT] modules cannot be organized into packages as regular file system based python modules can be.

## Members

No operator specific members.

## Methods

No operator specific methods.

## Usage

There are three methods to import [CLASS_DAT] as modules in a script.

### import datName

`import datName` Import the module defined by the [CLASS_DAT] named `datName`. All regular import options are supported (`from`, `as`, etc). If a [CLASS_DAT] is not found, the regular file system search path is then used.

```python
# import a DAT named addMonth
import addMonths
```

### m = mod.datName

`m = mod.datName` Import the module defined by the [CLASS_DAT] named `datName`.

```python
m = mod.addMonths(1,2,3)
```

### m = mod(pathToDat)

`m = mod(pathToDat)` Similar to above, except a path to the [CLASS_DAT] can be used.

```python
m = mod('myMods/adders').addMonths(1,2,3)
```

## Comparing Usage

Example using `import`:

```python
import myUtils
a = myUtils.add(5,6)
```

Same example using `mod`:

```python
a = mod.myUtils.add(5,6)
```

Example using `mod` outside the search path:

```python
a = mod('/projects/utils/utilsA').add(5,6)
```

Notice however, that a single `import` statement will be faster than the case of multiple identical `mod` statements:

```python
import myUtils
a = myUtils.add(5,6)
b = myUtils.add(5,6)
c = myUtils.add(5,6)
```

will execute faster than:

```python
a = mod.myUtils.add(5,6)
b = mod.myUtils.add(5,6)
c = mod.myUtils.add(5,6)
```

However the above could be rewritten more efficiently like this, which would then execute at the same speed as the `import` statement:

```python
m = mod.myUtils
a = m.add(5,6)
b = m.add(5,6)
c = m.add(5,6)
```

## Search Path

The current component is searched first.

If the [CLASS_DAT] is not found, the `local/modules` component of the current component is then searched.

Next the `local/modules` component of each parent is successively searched.

If the [CLASS_DAT] is still not found, `None` is returned.
