---
title: "callbacksExt Extension"
category: PY
document_type: reference
difficulty: intermediate
time_estimate: 15-20 minutes
user_personas: ["script_developer", "component_builder"]
operators: []
concepts: ["callbacks", "extensions", "custom_components"]
prerequisites: ["Python_fundamentals", "component_scripting"]
workflows: ["creating_custom_components", "event_handling"]
keywords: ["callbacks", "extension", "callbackdat", "docallback"]
tags: ["python", "api", "core", "extension", "callbacks"]
related_docs:
- MODULE_TDModules
- CLASS_OP
---

# callbacksExt Extension

## Content

- [Introduction](#introduction)
- [Python Callback System](#python-callback-system)
- [Adding CallbackExt to a Component](#adding-callbackext-to-a-component)
- [Methods](#methods)
- [Members](#members)

## Introduction

The `callbacksExt` extension provides Python callback functionality to custom components.

## Python Callback System

All callbacks will be passed a single argument containing an `info` dictionary. Callbacks can be defined in the DAT named in the `Callback DAT` parameter. To report all callbacks to the textport, turn on the `Print Callbacks` toggle parameter. The `Callback DAT` and `Print Callbacks` parameters are often found on the `Callbacks` parameter page, but their location can be customized.

The `info` dictionary always contains an `"ownerComp"` key. It will also have a `"callbackName"` key holding the callback name. It will sometimes contain an `"about"` key, describing the callback, and should always contain this key if a return value is expected. Generally, callbacks are called AFTER the internal method they are associated with, to allow over-riding of whatever that method does.

TouchDesigner's Python callback system uses the `CallbacksExt` Extension.

## Adding CallbackExt to a Component

The standard way to add `CallbackExt` to a component is to add a `Select DAT` inside that component and rename it `"CallbacksExt"`. Change the `DAT` parameter of `CallbacksExt` to expression mode and enter the expression:

```python
op.TDModules.op('TDCallbacksExt')
```

Next, set one of the component's Extension Object parameters to:

```python
op('./CallbacksExt').module.CallbacksExt(me)
```

If you want to access the callback functionality directly via the component, toggle the "Promote Extension" parameter for that extension.

To implement a system allowing a user callback DAT, you will want to add a custom "Callbackdat" DAT parameter. For testing you will usually want a custom "Printcallbacks" toggle parameter. Adding these parameters is generally done with the Component Editor.

## Methods

### DoCallback()

`DoCallback(callbackName, callbackInfo=None, callbackOrDat=None)` → `callbackInfo`:

> If it exists, call the named callback in `ownerComp.par.Callbackdat` and return `callbackInfo` with the callback's return value placed in `callbackInfo['returnValue']`. If no callback is found, returns `None`. If a callback is found, the info dictionary is returned with the addition of a `retValue` key containing the returned value.
> If `ownerComp` has a parameter called `Printcallbacks`, and that parameter is True, callback debug info will be printed to textport.
>
> - `callbackName` - Name of callback to be called
> - `callbackInfo` - (Optional) Dictionary of info to be passed to callback. `callbackInfo['ownerComp']` is automatically set to `ownerComp`. If callback needs special instructions, put them in `callbackInfo['about']`.
> - `callbackOrDat` - (Optional) Used to redirect callback to a DAT or specific function. Note: This is an expert feature, not for general use.

### SetAssignedCallback()

`SetAssignedCallback(self, callbackName, callback, details=None)`

> Note: This is an expert feature, not for general use.
> An assigned callback is a python function assigned to a particlar callback name. When `doCallback` is called with `callbackName`, `callback` will be invoked instead of searching `CallbackDat`
>
> - `callbackName` - Name of callback to be called
> - `callback` - The callback or `None` to remove the assigned callback
> - `details` - Optional extra info to be passed in the `['details']` key of `infoDict` when callback is called.

### PassCallbacksTo()

`PassCallbacksTo(self, passTarget)`

> Note: This is an expert feature, not for general use.
> Set a target DAT or function for passing on unfound callbacks to.
>
> - `passTarget` - a DAT or function

### PassOnCallback()

`PassOnCallback(self, info)`

> Note: This is an expert feature, not for general use.
> Pass this callback (as named in `info`) to the callback stored in extension's `PassTarget` member. Use `PassCallbacksTo` to set target
>
> - `info` - the callback's info dict

## Members

### CallbackDat

> Get or set the dat containing user callbacks. This will set the value of the `Callbackdat` parameter as well, if it exists.

### PrintCallbacks

> Get or set whether to print callback info to the Textport
