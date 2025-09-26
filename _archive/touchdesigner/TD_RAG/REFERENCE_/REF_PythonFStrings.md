---
title: "Python f-strings"
category: REFERENCE
document_type: tutorial
difficulty: beginner
time_estimate: 5-10 minutes
user_personas: ["script_developer", "beginner_user"]
operators: ["textCOMP", "lister"]
concepts: ["f-strings", "string_formatting", "python_scripting"]
prerequisites: ["Python_fundamentals"]
workflows: ["dynamic_text_generation", "ui_development"]
keywords: ["f-string", "format", "string", "python"]
tags: ["python", "api", "core", "scripting"]
related_docs:
- MODULE_TDFunctions
---

# Python f-strings

## Contents

- [f-strings](#f-strings)
- [f-strings in TouchDesigner](#f-strings-in-touchdesigner)
- [Examples](#examples)
- [Using f-string Formatting in Your Scripts](#using-f-string-formatting-in-your-scripts)

## f-strings

Python f-strings are a powerful new way to format strings in Python. In general, they look like this:

```python
f'This string includes {expression}'
```

Anything inside the curly-braces is evaluated as a Python expression. You can find full details by searching "Python f-strings" online. This is a good place to start.

## f-strings in TouchDesigner

Some TouchDesigner operators allow you to use f-string formatting in various ways. Examples include `textCOMP` in the parameters and `lister` in the `colDefine` table. Different variables will be provided to the f-string for use in expressions. These will be documented in the individual operator pages.

## Examples

- `{text}!` - yields the string held in `text` followed by an exclamation point
- `{val + 1}` - yields `val` + 1 (works when `val` is a numeric type only)
- `${val:.2f}` - yields `val` as a float with two decimal places and a dollar sign before it (works when `val` is a float only)
- `{me.path}: {text}` - yields the operator path where this is being evaluated, followed by a colon, followed by the string held in `text`

## Using f-string Formatting in Your Scripts

To use f-string formatting in your custom scripts, parameters, and components, use the utility function `formatString` in [MODULE_TDFunctions].
