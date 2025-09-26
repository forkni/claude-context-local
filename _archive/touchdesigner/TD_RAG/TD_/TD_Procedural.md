---
title: "Procedural"
category: "TD_"
document_type: "guide"
difficulty: "beginner"
time_estimate: "5 minutes"
user_personas: ["script_developer", "visual_programmer", "beginner"]
completion_signals: ["understands_pull_vs_push", "understands_dependency_basics"]
operators: []
concepts: ["procedural", "dependency", "pull_system", "push_system", "events", "cooking"]
prerequisites: []
workflows: ["realtime_systems", "interactive_design"]
keywords: ["procedural", "dependency", "cook", "pull", "push", "event"]
tags: ["core", "concept", "dependency", "system_information"]
related_docs:
- "CLASS_Dependency_Class"
- "TD_Event"
- "REF_DeeplyDependableCollections"
---

# Procedural

## Content
- [Introduction](#introduction)
- [Automatic Dependency](#automatic-dependency)
- [Python Data Dependency](#python-data-dependency)
- [See Also](#see-also)

## Introduction

Procedural means the automatic generation of outputs based on live inputs and the current state of TouchDesigner. Dependency is the procedural mechanism in TouchDesigner, where if one piece of data changes, it automatically causes other operators and expressions to re-Cook. This assures all data is consistent in a TouchDesigner process, and causes all the output displays, UIs, devices and protocols to update in realtime.

TouchDesigner is both a "pull system" and a "push system". The pull system is the procedural part, as data is generated, modified and pulled toward the outputs such as displays, audio devices, network streams and devices. The push system is based on Events coming from user inputs, external devices and software, and internally-generated events. Events usually cause changes to parameters, DAT tables and python data structures, which then affects the procedural data being generated when pulls happen, usually once per timeline frame.

## Automatic Dependency

If there is a change in an operator's output data or parameter value, it causes other operators downstream from it to cook. Downstream means operators that are connected to the output of a changed node, and operators (or their parameters) that refer to the changed operator (often visible as the dashed-lines in a network).

## Python Data Dependency

Because Python does not inherently have a procedural mechanism, `Dependency Objects` in TouchDesigner allow python data to cause downstream cooking when that data is changed.

See [CLASS_Dependency_Class] for how to set up Python Dependency. To create recursively dependable Python collections, see [REF_DeeplyDependableCollections].

## See Also

- [TD_Event]
