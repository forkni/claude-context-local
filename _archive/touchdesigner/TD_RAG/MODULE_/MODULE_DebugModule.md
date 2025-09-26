---
title: "debug module"
category: MODULE
document_type: reference
difficulty: intermediate
time_estimate: 10-15 minutes
user_personas: ["script_developer"]
operators: []
concepts: ["debugging", "scripting", "logging"]
prerequisites: ["Python_fundamentals"]
workflows: ["debugging_scripts", "custom_logging"]
keywords: ["debug", "print", "log", "traceback", "error"]
tags: ["python", "api", "core", "debug", "utility"]
related_docs:
- MODULE_Tdu
---

# debug module

## Content

- [Introduction](#introduction)
- [Members](#members)
- [Methods](#methods)

## Introduction

The `debug` module provides tools for use with TouchDesigner's builtin `debug` statement. It also contains utilities for customizing those statements and building customized debug output. This module is a member of the [MODULE_Tdu].

You can use the `debugControl` component in the palette to set up debug behavior without using Python.

## Members

### style

`style` → `types.SimpleNamespace`:

> A namespace containing information about how to process debug statements. This data is not meant to be changed directly. Instead, use the `setStyle` function below.

## Methods

### debug()

`debug(*args)`→ `None`:

> Print all args and extra debug info (default is DAT and line number) to texport. To change behavior, use the `debugControl` component or `setStyle` function (below).
> TIP: Use `debug` instead of `print` when debugging Python scripts in order to see object types and the source of the output.

### setStyle()

`setStyle(printStyle=None, showDAT=None, showFunction=None, showLineNo=None, timeStamp=' ', suppress=None, formatOverride=None, functionOverride=None)`→ `None`:

> Set the style for the built in TD debug function. Any arguments passed as `None` will leave that feature unchanged.
>
> - `printStyle`:
>   - `'pprint'`=convert non-string args to `pprint.pformat(arg, indent=4, sort_dicts=False)`. Makes lists, dicts, etc. easily readable
>   - `'pprint_sorted'`=convert non-string args to `pprint.pformat(arg, indent=4)`. Makes lists, dicts, etc. easily readable. Dict keys will be alphabetized
>   - `'repr'`=convert non-string args to `repr(arg)`
>   - otherwise, convert non-string args to `str(arg)`
> - `showDAT`: in debug message, show the DAT where debug was called
> - `showFunction`: in debug message, show function where debug was called
> - `showLineNo`: in debug message, show line number where debug was called
> - `suppress`: if True, suppress (don't print) any debug calls
> - `timeStamp`: Python time format code.
> - `formatOverride`: overrides the default message that debug prints. You can use `{0}`, `{1}`, and `{2}` for DAT, function, and line number
> - `functionOverride`: overrides the builtin TD debug function. This function will be called with all arguments from any debug calls in your project. Set to `False` to remove override.

### debugs()

`debugs(*args)`→ `str`:

> Return the string that would be printed by the debug function. To change behavior, use the `debugControl` component or `setStyle` function (above). This is a utility function for building custom debug systems.

### info()

`info(*args, stackOffset=0)`→ `list`:

> Return all args and extra debug info as processed by the debug function. To change behavior, use the `debugControl` component or `setStyle` function (above). This is a utility function for building custom debug systems.
