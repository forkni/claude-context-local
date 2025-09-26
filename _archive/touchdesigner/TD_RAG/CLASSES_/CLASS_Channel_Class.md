---
title: "Channel Class"
category: CLASS
document_type: reference
difficulty: intermediate
time_estimate: 10-15 minutes

# Enhanced metadata
user_personas: ["script_developer", "intermediate_user", "automation_specialist", "technical_artist"]
completion_signals: ["can_access_channel_data", "understands_chop_data_access", "can_implement_channel_evaluation", "manages_real_time_data"]

operators:
- Pattern_CHOP
- Constant_CHOP
- Script_CHOP
- Math_CHOP
- OSC_In_CHOP
- Audio_File_In_CHOP
concepts:
- chop_data_access
- channel_evaluation
- numpy_integration
- python_scripting
- sample_access
- parameter_exports
- real_time_data
prerequisites:
- CHOP_basics
- Python_fundamentals
- MODULE_td_Module
workflows:
- chop_data_access
- python_scripting
- channel_evaluation
- data_processing
- parameter_expressions
- real_time_control
keywords:
- channel access
- chop python
- channel evaluation
- numpy integration
- sample access
- frame evaluation
- time evaluation
- channel subscript
- channel indexing
- real-time data
- vals property
tags:
- python
- api_reference
- chop
- channel
- numpy_support
- real_time
- data_access
- scripting
relationships:
  PY_Working_with_CHOPs_in_Python: strong
  MODULE_td_Module: strong
  PY_Python_Reference: medium
  PY_Optimized_Python_Expressions: medium
related_docs:
- PY_Working_with_CHOPs_in_Python
- MODULE_td_Module
- PY_Python_Reference
- PY_Optimized_Python_Expressions
# Enhanced search optimization
search_optimization:
  primary_keywords: ["channel", "chop", "data", "sample"]
  semantic_clusters: ["data_access", "channel_processing", "real_time_data"]
  user_intent_mapping:
    beginner: ["what is channel class", "basic chop access", "how to get channel data"]
    intermediate: ["channel evaluation", "data processing", "sample access"]
    advanced: ["numpy integration", "real-time control", "advanced data manipulation"]

hierarchy:
  secondary: data_manipulation
  tertiary: channel_access
question_patterns:
- How to use CLASS class?
- What methods are available?
- How to access properties?
- Python API reference?
common_use_cases:
- chop_data_access
- python_scripting
- channel_evaluation
- data_processing
---

# Channel Class

<!-- TD-META
category: CLASS
document_type: reference
operators: [Pattern_CHOP, Constant_CHOP, Script_CHOP, Math_CHOP, OSC_In_CHOP, Audio_File_In_CHOP]
concepts: [chop_data_access, channel_evaluation, numpy_integration, python_scripting, sample_access, parameter_exports, real_time_data]
prerequisites: [CHOP_basics, Python_fundamentals, MODULE_td_Module]
workflows: [chop_data_access, python_scripting, channel_evaluation, data_processing, parameter_expressions, real_time_control]
related: [PY_Working_with_CHOPs_in_Python, MODULE_td_Module, PY_Python_Reference, PY_Optimized_Python_Expressions]
relationships: {
  "PY_Working_with_CHOPs_in_Python": "strong",
  "MODULE_td_Module": "strong",
  "PY_Python_Reference": "medium",
  "PY_Optimized_Python_Expressions": "medium"
}
hierarchy:
  primary: "scripting"
  secondary: "data_manipulation"
  tertiary: "channel_access"
keywords: [channel access, chop python, channel evaluation, numpy integration, sample access, frame evaluation, time evaluation, channel subscript, channel indexing, real-time data, vals property]
tags: [python, api_reference, chop, channel, numpy_support, real_time, data_access, scripting]
TD-META -->

## 🎯 Quick Reference

**Purpose**: Python class reference for TouchDesigner API development
**Difficulty**: Intermediate
**Time to read**: 10-15 minutes
**Use for**: chop_data_access, python_scripting, channel_evaluation

**Common Questions Answered**:

- "How to use CLASS class?" → [See relevant section]
- "What methods are available?" → [See relevant section]
- "How to access properties?" → [See relevant section]
- "Python API reference?" → [See relevant section]

## 🔗 Learning Path

**Prerequisites**: [Chop Basics] → [Python Fundamentals] → [Module Td Module]
**This document**: CLASS reference/guide
**Next steps**: [PY Working with CHOPs in Python] → [MODULE td Module] → [PY Python Reference]

**Related Topics**: chop data access, python scripting, channel evaluation

## Summary

Essential class for accessing individual channel data from CHOPs. Provides the fundamental interface for reading channel values, samples, and properties in Python scripts. Critical for real-time data processing workflows.

## Relationship Justification

Strong connection to CHOP working guide and td module as foundational knowledge. Links to Python reference and optimized expressions since channel access is frequently used in expressions.

## Content

- [Introduction](#introduction)
- [Members](#members)
  - [valid](#valid)
  - [index](#index)
  - [name](#name)
  - [owner](#owner)
  - [exports](#exports)
  - [vals](#vals)
- [Methods Overview](#methods-overview)
  - [[index]](#index-1)
  - [eval()](#eval)
  - [evalFrame()](#evalframe)
  - [evalSeconds()](#evalseconds)
  - [numpyArray()](#numpyarray)
  - [destroy()](#destroy)
  - [average()](#average)
  - [min()](#min)
  - [max()](#max)
  - [copyNumpyArray()](#copynumpyarray)
- [Casting to a Value](#casting-to-a-value)

## Introduction

A Channel object describes a single channel from a CHOP. The [CLASS_CHOP] provides many ways of accessing its individual channels. See [PY_Working_with_CHOPs_in_Python](PY_Working_with_CHOPs_in_Python.md) for more examples of how to use this class.

## Members

### valid

`valid` → `bool` **(Read Only)**:

True if the referenced channel value currently exists, False if it has been deleted.

### index

`index` → `int` **(Read Only)**:

The numeric index of the channel.

### name

`name` → `str` **(Read Only)**:

The name of the channel.

### owner

`owner` → `OP` **(Read Only)**:

The [CLASS_OP] to which this object belongs.

### exports

`exports` → `list` **(Read Only)**:

The (possibly empty) list of parameters this channel currently exports to.

### vals

`vals` → `list`:

Get or set the full list of Channel values. Modifying Channel values can only be done in Python within a [CLASS_scriptCHOP](CLASS_scriptCHOP.md).

## Methods Overview

### [index]

`[index]` → `float`:

Sample values may be easily accessed from a Channel using the [] subscript operator.

- `index` - Must be a numeric sample index. Wildcards are not supported.

To get the third sample from the channel, assuming the channel has 3 or more samples:

```python
n = op('pattern1')
c = n['chan1'][2] # the third sample
l = len(n['chan2']) # the total number of samples in the channel
```

### eval()

`eval(index)` → `float`:

Evaluate the channel at the specified index sample index. If no index is given, the current index based on the current time is used.

- `index` - (Optional) The sample index to evaluate at.

### evalFrame()

`evalFrame(frame)` → `float`:

Evaluate the channel at the specified frame. If no frame is given, the current frame is used.

- `frame` - (Optional) The frame to evaluate at.

### evalSeconds()

`evalSeconds(secs)` → `float`:

Evaluate the channel at the specified seconds. If no time is given, the current time is used.

- `secs` - (Optional) The time in seconds to evaluate at.

### numpyArray()

`numpyArray()` → `numpy.ndarray`:

Returns this channels data as a NumPy array with a length equal to the track length.

### destroy()

`destroy()` → `None`:

Destroy and remove the actual Channel this object refers to. This operation is only valid when the channel belongs to a [CLASS_scriptCHOP](CLASS_scriptCHOP.md) or [CLASS_OSCInCHOP](CLASS_OSCInCHOP.md). **Note:** after this call, other existing Channel objects in this CHOP may no longer be valid.

### average()

`average()` → `float`:

Returns the average value of all the channel samples.

### min()

`min()` → `float`:

Returns the minimum value of all the channel samples.

### max()

`max()` → `float`:

Returns the maximum value of all the channel samples.

### copyNumpyArray()

`copyNumpyArray(numpyArray)` → `None`:

Copies the contents of the numpyArray into the Channel sample values.

- `numpyArray` - The NumPy Array to copy. Must be shape(n), where n is the sample length of the CHOP. The data type must be float32. Modifying Channel values can only be done in Python within a [CLASS_scriptCHOP](CLASS_scriptCHOP.md).

## Casting to a Value

The Channel Class implements all necessary methods to be treated as a number, which in this case evaluates its current value. Therefore, an explicit call to `eval()` is unnecessary when used in a parameter, or in a numeric expression.

For example, the following are equivalent in a channel:

```python
(float)n['chan1']
n['chan1'].eval()
```

The following are also equivalent, because the + 1 will implicitly cast the channel to a number:

```python
n['chan1'].eval() + 1
n['chan1'] + 1
```
