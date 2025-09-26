---
category: PY
document_type: guide
difficulty: intermediate
time_estimate: 15-25 minutes
operators:
- Rename_CHOP
- Select_CHOP
- Parameter_CHOP
- Script_CHOP
- Evaluate_DAT
- Table_DAT
- Expression_CHOP
- File_In_CHOP
concepts:
- pattern_replacement
- string_manipulation
- procedural_renaming
- channel_renaming
- back_referencing
- capture_groups
prerequisites:
- PY_Pattern_Matching
- PY_Pattern_Expansion
workflows:
- batch_renaming
- procedural_channel_management
- dynamic_data_routing
- automated_naming_systems
keywords:
- rename
- replace
- string manipulation
- wildcard
- back-reference
- capture group
- '*(0)'
- procedural naming
- pattern replacement
- dynamic renaming
tags:
- python
- string
- pattern
- procedural
- naming
- replacement
- fundamentals
- automation
relationships:
  PY_Pattern_Matching: strong
  PY_Pattern_Expansion: strong
  PY_Python_Tips: medium
related_docs:
- PY_Pattern_Matching
- PY_Pattern_Expansion
- PY_Python_Tips
hierarchy:
  secondary: pattern_system
  tertiary: pattern_replacement
question_patterns:
- Python scripting in TouchDesigner?
- How to use Python API?
- Scripting best practices?
- Python integration examples?
common_use_cases:
- batch_renaming
- procedural_channel_management
- dynamic_data_routing
- automated_naming_systems
---

# Pattern Replacement

<!-- TD-META
category: PY
document_type: guide
operators: [Rename_CHOP, Select_CHOP, Parameter_CHOP, Script_CHOP, Evaluate_DAT, Table_DAT, Expression_CHOP, File_In_CHOP]
concepts: [pattern_replacement, string_manipulation, procedural_renaming, channel_renaming, back_referencing, capture_groups]
prerequisites: [PY_Pattern_Matching, PY_Pattern_Expansion]
workflows: [batch_renaming, procedural_channel_management, dynamic_data_routing, automated_naming_systems]
related: [PY_Pattern_Matching, PY_Pattern_Expansion, PY_Python_Tips]
relationships: {
  "PY_Pattern_Matching": "strong",
  "PY_Pattern_Expansion": "strong",
  "PY_Python_Tips": "medium"
}
hierarchy:
  primary: "fundamentals"
  secondary: "pattern_system"
  tertiary: "pattern_replacement"
keywords: [rename, replace, string manipulation, wildcard, back-reference, capture group, *(0), procedural naming, pattern replacement, dynamic renaming]
tags: [python, string, pattern, procedural, naming, replacement, fundamentals, automation]
TD-META -->

## 🎯 Quick Reference

**Purpose**: Python scripting guide for TouchDesigner automation
**Difficulty**: Intermediate
**Time to read**: 15-25 minutes
**Use for**: batch_renaming, procedural_channel_management, dynamic_data_routing

**Common Questions Answered**:

- "Python scripting in TouchDesigner?" → [See relevant section]
- "How to use Python API?" → [See relevant section]
- "Scripting best practices?" → [See relevant section]
- "Python integration examples?" → [See relevant section]

## 🔗 Learning Path

**Prerequisites**: [Py Pattern Matching] → [Py Pattern Expansion]
**This document**: PY reference/guide
**Next steps**: [PY Pattern Matching] → [PY Pattern Expansion] → [PY Python Tips]

**Related Topics**: batch renaming, procedural channel management, dynamic data routing

## Summary

PSpecialized guide explaining pattern replacement syntax for advanced text manipulation and renaming workflows. Builds on pattern matching to provide dynamic replacement capabilities with back-references.

## Relationship Justification

Forms a trio with the [PY_Pattern_Matching](PY_Pattern_Matching.md) and [PY_Pattern_Expansion](PY_Pattern_Expansion.md) classes, which provide access to the pattern matching and pattern expansion features of TouchDesigner.

## Content

- [Introduction](#introduction)
- [Usage](#usage)
- [Members Overview](#members-overview)

## Introduction

Pattern Replacement takes place in a 2nd parameter after certain Pattern Matching parameters, for example in the Rename CHOP. It builds up the new names to replace the matched names using both the features of Pattern Expansion, as well as extra syntax specific to Pattern Replacement. The extra syntax allows for pulling out wildcards matched during the Pattern Matching.

The synxtax is either a *or a ?, followed by (wildcardIndex). Where wildcardIndex is an integer which is the index of the wildcard in the Pattern Matching parameter. For example if there are three* wildcards, you would reference them using *(0)*(1) and *(2). Similarly if there are 2 ? wildcard, they would be referenced using ?(0) and ?(1).

For example if a CHOP has 3 channels named

 left_side_monitor
 right_side_projector
 top_side_led
And the 'Rename From' has

 **side**
as it's entry. You can pull out what was matched by the first *and the second* by using *(0) and*(1).

A pattern replacement of

 *(1)*floor**(0)

Will result in the channel names

 monitor_floor_left
 projector_floor_right
 led_floor_top
Pattern Replacement occurs in:

Rename CHOP, Select CHOP, File In CHOP, Parameter CHOP

## See also

[CLASS_Script_CHOP_Class.md](CLASS_Script_CHOP_Class.md) where you can re-create channel names.
[PY_Pattern_Matching.md](PY_Pattern_Matching.md) for the matching syntax.
[PY_Pattern_Expansion.md](PY_Pattern_Expansion.md) for the expansion syntax.
