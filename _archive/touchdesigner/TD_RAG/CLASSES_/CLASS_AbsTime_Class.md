---
title: "absTime Class"
category: CLASS
document_type: reference
difficulty: beginner
time_estimate: 5-10 minutes
user_personas: ["script_developer", "beginner_user"]
operators: []
concepts: ["absolute_time", "timing", "scripting"]
prerequisites: ["Python_fundamentals"]
workflows: ["timing_and_synchronization"]
keywords: ["absTime", "time", "absolute", "frame", "seconds"]
tags: ["python", "api", "core", "time"]
related_docs:
- MODULE_td
---

# absTime Class

## Content

- [Introduction](#introduction)
- [Members](#members)
- [Methods](#methods)

## Introduction

This class contains information on the "absolute time", the time TouchDesigner has been running since the process started. It can be accessed with the `abstime` object, found in the automatically imported [MODULE_td]. It is paused only with the power on/off button at the top of the UI, or with the `power()` method in the [MODULE_td]. Absolute time is the same for all nodes and is not affected by the pausing any component's timeline. See also: `absolute time`.

## Members

### frame

`frame` → `float` (Read Only):

Absolute total number of frames played since the application started. Paused only with the power On/Off or with `power()`.

Example:

```python
absTime.frame
tdu.rand(absTime.frame + .1) # a unique random number that is consistent across all nodes, changing every frame
```

### seconds

`seconds` → `float` (Read Only):

Absolute total seconds played since the application started. Paused only with the power On/Off or with `power()`.

### step

`step` → `float` (Read Only):

Number of absolute frames elapsed between start of previous and current frame. When this value is greater than 1, the system is dropping frames.

### stepSeconds

`stepSeconds` → `float` (Read Only):

Absolute time elapsed between start of previous and current frame.

## Methods

No operator specific methods.
